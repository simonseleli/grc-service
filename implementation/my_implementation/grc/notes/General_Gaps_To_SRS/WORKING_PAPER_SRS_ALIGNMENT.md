# Working Paper — SRS Alignment Analysis & Migration Plan

---

## 1. What the SRS Requires

SRS §1.8.3 Steps 15–19 define three distinct activities:

| SRS Step | Actor | What happens |
|---|---|---|
| Step 15 | Audit Team Members | Perform tests, collect evidence, **document results in Working Papers**, submit to LA for review |
| Step 16 | LA | **Reviews** each working paper for completeness and quality |
| Step 18 | LA | **Consolidates** all working papers (findings, observations, results) and submits for CIA approval |
| Step 19 | CIA | **Reviews and approves the consolidated set**, returns approved papers to LA for further action |

**Key SRS intent:**
- The audit team prepares each paper individually
- LA reviews them one by one (quality check)
- At the end of fieldwork, LA does a **single consolidation action** — submitting all papers together as a package to CIA
- CIA approves the **whole set** at once, not paper by paper

---

## 2. What Is Currently Implemented

### Model — `WorkingPaper` (`apps/core/models/audit_entities.py`)

```
review_status: draft → pending → reviewed → approved
reviewed_by: UUID (whoever approved)
review_comments: text
document_id: UUID (main paper in DRS)
evidence_document_ids: list of UUIDs (supporting evidence in DRS)
workflow_plan_id: UUID (WO plan for this individual paper)
```

### Workflow — `grc.working_paper_approval` (2-stage WO plan per paper)

```
Stage 1: working_paper_review   → Assigned to: lead_auditor
         Actions: Approve / Reject / Request Changes

Stage 2: working_paper_approval → Assigned to: head_of_audit (CIA)
         Actions: Final Approve / Reject
```

### Endpoints

| Endpoint | What it does |
|---|---|
| `POST /engagements/{id}/working-papers/` | Create, upload to DRS, `review_status=draft` |
| `POST /working-papers/{id}/review/` | Submit to WO, `review_status=pending`, starts 2-stage WO workflow |
| `POST /working-papers/{id}/workflow-action/` | LA or CIA takes action on WO stage |
| `PATCH /working-papers/{id}/review/` | Internal — Kafka consumer calls this to update status after WO event |
| `GET /working-papers/{id}/workflow-status/` | Returns live WO plan state |
| `POST /working-papers/{id}/evidence/` | Upload additional evidence files to DRS |

### Kafka Consumer (`apps/infrastructure/messaging/kafka_consumer.py`)

- Listens for `grc.working_paper_approval` WO completion events
- `approved` → sets `review_status = approved`
- `rejected` → sets `review_status = reviewed` (LA must rework and resubmit)
- `cancelled` → resets `review_status = draft`

### Current Flow (per paper)

```
Audit Team creates WP → review_status=draft
    ↓
Audit Team clicks "Submit for Approval" on WP Detail page
    → POST /working-papers/{id}/review/ (WorkingPaperReviewView.post())
    → WorkingPaperService.submit_for_approval() → starts WO plan
    → review_status=pending
    ↓
LA approves Stage 1 (working_paper_review) via WO Console on WP Detail page
    ↓
CIA approves Stage 2 (working_paper_approval) via WO Console on WP Detail page
    ↓
WO sends Kafka completion event → grc_kafka_consumer._handle_working_paper_completion()
    → review_status=approved
```

**Each paper has its own independent 2-stage WO workflow running inside `WorkingPaperDetailPage.tsx`.**

### Frontend components involved (currently)

| File | What it does |
|---|---|
| `WorkingPaperDetailPage.tsx` | Full detail page with Submit button + EmbeddedWorkflowConsole + EvidenceAttachmentSection |
| `CreateWorkingPaperDialog.tsx` | Create dialog (called from EngagementDetailPage) |
| `EvidenceAttachmentSection.tsx` | Evidence upload/view section (reusable component) |
| `EmbeddedWorkflowConsole.tsx` | WO console shown per paper (shared component) |
| `useWorkingPapers.ts` | All hooks: useWorkingPaper, useCreateWorkingPaper, useSubmitWorkingPaperForApproval, useReviewWorkingPaper, useDeleteWorkingPaper |
| `types/grc.ts` | WorkingPaper interface: includes `review_status`, `workflow_plan_id`, `evidence_document_ids` |

---

## 3. The Gap — Current vs SRS

| Aspect | Current Implementation | SRS Requirement |
|---|---|---|
| LA review | LA approves Stage 1 of each paper's WO workflow individually | LA reviews each paper, then at the end **consolidates** |
| CIA approval | CIA approves Stage 2 of each paper's WO workflow individually | CIA gets **one review session** for the full consolidated set |
| Trigger for CIA review | Each paper individually submitted → each gets its own WO plan | LA does a **single "Consolidate & Submit all papers"** action when all are ready |
| CIA sees | Papers one at a time, in different WO plans | All papers together, in one WO plan |

---

## 4. Migration Plan — How to Shift to SRS-Aligned Approach

### Concept

Introduce a **two-phase model** for working papers:

- **Phase A (per-paper):** Audit team creates paper + uploads evidence. LA reviews each paper individually. This is an **internal LA review**, not a CIA-visible WO workflow. LA marks each paper as `reviewed` when satisfied.
- **Phase B (consolidated):** When all papers are reviewed, LA triggers a **single "Consolidate" action** on the engagement. This creates ONE WO plan for CIA to review and approve all papers at once.

### Status Flow Change

**Current:**
```
draft → pending → reviewed → approved  (per paper, with full WO workflow each)
```

**New (SRS-aligned):**
```
draft → under_la_review → la_reviewed        (Phase A — LA internal, no WO)
                                ↓
                        [LA clicks "Consolidate All"] — when all papers are la_reviewed
                                ↓
pending_cia → cia_approved                   (Phase B — single WO plan on the engagement)
```

### What Changes

#### A. `WorkingPaper` model
- Add status choices: `la_reviewed`, `pending_cia`, `cia_approved`
- Remove per-paper `workflow_plan_id` (or keep for records but stop using it for CIA approval)
- Keep `evidence_document_ids` — no change needed here

#### B. New endpoint: `POST /engagements/{id}/consolidate-working-papers/`
- Validates: all working papers for this engagement are `la_reviewed`
- Creates a **single** WO workflow plan (template: `grc.working_paper_consolidated_approval`, 1 stage: CIA approval)
- Sets all papers' status → `pending_cia`
- Stores `consolidated_workflow_plan_id` on the `AuditEngagement` model (new field)
- Permission: `CanManageWorkingPaper` (LA only)

#### C. Existing endpoints that change
| Endpoint | What changes |
|---|---|
| `POST /working-papers/{id}/review/` | Strip WO call from `WorkingPaperService.submit_for_approval()`. Just sets `review_status = la_reviewed`. No `workflow_plan_id` set. |
| `POST /working-papers/{id}/workflow-action/` | No longer used for CIA approval per-paper. Keep for backward compat but guard with status check. |

> **⚠️ Evidence endpoints are NOT changed** — `POST /working-papers/{id}/evidence/` and `DELETE /working-papers/{id}/evidence/{doc_id}/` remain exactly as-is. Evidence is per-paper and has nothing to do with the consolidation workflow.

#### D. New WO template: `grc.working_paper_consolidated_approval`
```
Stage 1: consolidated_working_paper_approval
  Assigned to: CIA (head_of_audit)
  Actions: Approve All / Return to LA
```

#### E. Kafka consumer change
- Listen for `grc.working_paper_consolidated_approval` WO completion
- On `approved` → set all `pending_cia` papers for that engagement → `cia_approved`
- On `rejected/returned` → set all papers back to `la_reviewed`, clear `consolidated_workflow_plan_id` on engagement

#### F. Frontend changes

| File | What changes |
|---|---|
| `WorkingPaperDetailPage.tsx` | Remove `EmbeddedWorkflowConsole` import and usage. Replace "Submit for Approval" button with "Submit for LA Review" button. Show status badge only. |
| `EngagementDetailPage.tsx` | Add **"Consolidate All Working Papers"** button on Working Papers card — visible to LA when ALL papers are `la_reviewed`. Add WO console widget for consolidated plan. |
| `useWorkingPapers.ts` | Rename `useSubmitWorkingPaperForApproval` → `useSubmitWorkingPaperForLAReview` (calls same endpoint, cleaner name). Add `useConsolidateWorkingPapers` mutation. |
| `types/grc.ts` | Extend `review_status` union: add `'la_reviewed' \| 'pending_cia' \| 'cia_approved'`. |
| `EvidenceAttachmentSection.tsx` | **No change needed** — stays on WP detail page as-is. |

### Migration Steps (in order)

1. **DB migration**: add new `review_status` choices (`la_reviewed`, `pending_cia`, `cia_approved`) to `WorkingPaper`
2. **DB migration**: add `consolidated_workflow_plan_id = UUIDField(null=True, blank=True)` to `AuditEngagement`
3. **WO seed**: add `grc.working_paper_consolidated_approval` template to `work-orchestration-service/apps/core/management/commands/seed_workflow_templates.py`
4. **Backend**: add `ConsolidateWorkingPapersView` at `POST /api/v1/grc/audit/engagements/{id}/consolidate-working-papers/` — register in `apps/api/urls/audit.py`
5. **Backend**: modify `WorkingPaperService.submit_for_approval()` — remove WO `start_workflow()` call, just set `review_status = la_reviewed`; rename service method to `submit_for_la_review()`
6. **Backend**: update `WorkingPaperReviewView.post()` to call renamed service method
7. **Backend**: update `grc_kafka_consumer._handle_working_paper_completion()` — add handler for `grc.working_paper_consolidated_approval` that bulk-updates all `pending_cia` papers for the engagement
8. **Backend**: update `apps/api/urls/audit.py` — register new consolidate endpoint
9. **Frontend**: `types/grc.ts` — extend `review_status` union type
10. **Frontend**: `useWorkingPapers.ts` — rename hook, add `useConsolidateWorkingPapers`
11. **Frontend**: `WorkingPaperDetailPage.tsx` — remove `EmbeddedWorkflowConsole`, replace submit button label
12. **Frontend**: `EngagementDetailPage.tsx` — add Consolidate button + consolidated WO console widget

> **Existing evidence functionality (steps ±0):** `EvidenceAttachmentSection`, evidence endpoints, `evidence_document_ids` — **zero changes needed**.

---

## 5. What Does NOT Change

| Item | Files | Notes |
|---|---|---|
| `WorkingPaper.document_id` | model | Main paper document in DRS ✅ keep |
| `WorkingPaper.evidence_document_ids` | model | Supporting evidence list in DRS ✅ keep |
| Evidence upload endpoints | `working_paper_views.py` — `WorkingPaperEvidenceView`, `WorkingPaperEvidenceDetailView` | ✅ keep exactly as-is |
| `EvidenceAttachmentSection.tsx` | frontend component | ✅ keep exactly as-is |
| `WorkingPaper.prepared_by`, `reviewed_by`, `review_comments` | model | ✅ keep |
| Per-paper create/edit/delete endpoints | `working_paper_views.py` | ✅ keep |
| DRS document storage pattern | views + service | ✅ keep |
| `WorkingPaperSerializer`, `WorkingPaperListSerializer` | serializers | Add new status values to `review_status` choices; all other fields unchanged |
| Permissions `CanManageWorkingPaper`, `CanReviewWorkingPaper` | `permissions_jwt.py` | ✅ keep — consolidate endpoint reuses `CanManageWorkingPaper` |

---

## 6. Complexity Assessment

| # | Item | Files touched | Effort |
|---|---|---|---|
| 1 | DB migration — new status choices | `audit_entities.py` + new migration file | Low |
| 2 | DB migration — `consolidated_workflow_plan_id` on engagement | `audit_entities.py` + new migration file | Low |
| 3 | WO template seed | `seed_workflow_templates.py` (WO service) | Low |
| 4 | New `ConsolidateWorkingPapersView` | `working_paper_views.py`, `audit.py` (urls) | Medium |
| 5 | Modify `WorkingPaperService.submit_for_la_review()` | `working_paper_service.py` | Low |
| 6 | Modify `WorkingPaperReviewView.post()` | `working_paper_views.py` | Low |
| 7 | Kafka consumer — consolidated handler | `kafka_consumer.py` (infrastructure) | Low |
| 8 | Frontend types | `types/grc.ts` | Low |
| 9 | Frontend hooks | `useWorkingPapers.ts` | Low |
| 10 | Frontend WP detail page | `WorkingPaperDetailPage.tsx` | Low |
| 11 | Frontend engagement detail page | `EngagementDetailPage.tsx` | Medium |
| — | Evidence (all) | No files touched | Zero |
| | **Total** | **11 files** | **~2–3 days** |

---

## 7. Recommendation

> ⏸️ **Do not migrate now.** The current per-paper approach works functionally — the outcome is the same (CIA approves each paper). The consolidation model is a **UX and process fidelity** improvement, not a blocker.

**When to migrate:**
- After all other SRS gaps are fixed and the system is stable
- Before formal UAT or handover to the client
- When the SRS consolidation flow is explicitly requested by the CIA or senior team

**Document for later:** This file is the complete specification. When the time comes, follow Steps 1–7 in Section 5 in order.
