# GRC Internal Audit — UI Refactoring Proposal

> **Author:** Copilot analysis
> **Date:** 2026-03-09
> **Scope:** Staff Portal — GRC Internal Audit module UI/navigation restructure
> **Guiding principle:** Follow Audit Universe design pattern; eliminate redundant sidebar entries
> **Non-negotiable constraint:** Every decision below is grounded in `AUDT2_ext.md` (SRS). No SRS requirement is removed or altered.

---

## 1. The Problem: Redundant Navigation

### 1.1 The Good Pattern — Audit Universe

The Audit Universe correctly uses a **parent → embedded children** pattern:

```
Sidebar
└── Audit Universe           → /service/grc/audit-universe        (list page)
    └── Universe Detail      → /service/grc/audit-universe/:id    (detail page)
        └── Auditable Entities section                             (embedded, NO sidebar entry)
            ├── Add Entity   → Dialog (inline)
            ├── Edit Entity  → Dialog (inline)
            └── Delete Entity → Confirm dialog (inline)
```

**Why this is correct per SRS:**
> SRS Process Flow 1 (RBIAP): *"IA identify Audit Universe representing the potential range of all audit activities..."*
>
> Auditable Entities are always seen in the context of their parent Universe. A standalone "Auditable Entities" page with no universe context would be meaningless to the user.

### 1.2 The Problem — Engagement Sub-Entities

The current design violates this pattern. Five entities that belong **exclusively to a single Engagement** (or a single Audit Plan) are exposed as **top-level sidebar items**. Users can:
- Navigate to a standalone **"Declarations of Independence"** page and see declarations from ALL engagements mixed together with no context
- Navigate to **"Audit Surveys"** standalone and see surveys without understanding which engagement they belong to
- Do the same for **Audit Memos**, **Risk Control Matrix**, and **Audit Programs**

This creates two forms of redundancy:
1. **Information redundancy** — the same data is shown in the Engagement detail page AND in a standalone page
2. **Action redundancy** — items can be created from both locations, which is confusing and inconsistent

The `EngagementDetailPage` **already embeds** all of these (Declarations, Surveys, RCM, Programs, Notifications) as cards with `+ Add` buttons. The standalone pages are shadow copies that serve no additional SRS requirement.

---

## 2. SRS Analysis — Entity-to-Parent Mapping

The following table maps each entity to its canonical parent per the SRS, determining where it should live in the UI.

| Entity | SRS Reference | FK Relationship | Canonical Parent | Standalone Sidebar Verdict |
|---|---|---|---|---|
| **Auditable Entities** | SRS Flow 1, Req 1 | `audit_universe_id` | Audit Universe | ❌ No sidebar (already removed in current build) |
| **Audit Memos** | SRS Req 10–14, `FCC_SBP_IA_TB_02-03` | `audit_plan_id` + `auditable_entity_id` | **Audit Plan** | ❌ Remove — embed in Audit Plan detail |
| **Declarations of Independence** | SRS Req 16 | `audit_engagement_id` | **Engagement** | ❌ Remove — embed in Engagement detail |
| **Audit Survey (Preliminary Survey)** | SRS Req 19–21 | `audit_engagement_id` (OneToOne) | **Engagement** | ❌ Remove — embed in Engagement detail |
| **Risk Control Matrix** | SRS Req 22, SRS Flow 8 | `audit_engagement_id` | **Engagement** | ❌ Remove — embed in Engagement detail |
| **RCM Entries** | SRS Req 22 | `rcm_id` | **RCM (via Engagement)** | ❌ No sidebar — sub-detail page only |
| **Audit Programs** | SRS Req 23 | `audit_engagement_id` | **Engagement** | ❌ Remove — embed in Engagement detail |
| **Engagement Notifications** | SRS Req 24–26 | `audit_engagement_id` | **Engagement** | ❌ Remove — already embedded, remove App.tsx route|
| **Audit Findings** | SRS Flow 6–7 | `audit_engagement_id` (but cross-eng. queries) | Cross-engagement | ✅ Keep sidebar — CIA needs cross-engagement view |
| **Working Papers** | SRS Flow 15–19 | `audit_engagement_id` (but deep linking needed) | Engagement + standalone | ✅ Keep sidebar — Working Papers have their own detail page |
| **Audit Reports** | SRS §1.8.5 | Quarterly — aggregates multiple engagements | Cross-engagement | ✅ Keep sidebar |
| **Audit Recommendations** | SRS §1.8.6 | Aggregates across findings/engagements | Cross-engagement | ✅ Keep sidebar |
| **Audit Monitoring** | SRS §1.8.6 | Implementation monitoring across all engagements | Cross-engagement | ✅ Keep sidebar |

### SRS Justification for Each Removal Decision

#### Audit Memos — embed in Audit Plan Detail

> SRS Process `FCC_SBP_IA_TB_02-03` (Preparing Engagement):
> *"CIA appoints Lead Auditor and prepares an internal audit memo"*
> *Process Input:* **Approved Risk Based Annual Internal Audit Plan**

The memo's FK is `audit_plan_id + auditable_entity_id`. The memo is prepared from the approved/implementation-phase Audit Plan. It has NO direct FK to an Engagement at all. A standalone "Audit Memos" page severed from the plan context contradicts the SRS process flow.

**Correct UX:** Open Audit Plan → scroll to "Audit Memos" section → click `+ Prepare Memo` → dialog opens → memo created and managed entirely within the Plan context.

#### Declarations of Independence — embed in Engagement Detail

> SRS Req 16:
> *"Each audit team member must sign a Declaration of Independence before participating in an audit engagement."*

The declaration is tied 1-N to a specific engagement. Viewing declarations without knowing which engagement they belong to is meaningless. The SRS never describes a "Declarations Registry" for CIA-level cross-engagement management.

The Sign action and the "has conflict" flag are engagement-planning gating requirements. They live naturally as a card section in the Engagement detail page — already implemented.

#### Audit Survey — embed in Engagement Detail

> SRS Req 19–21:
> *"LA conducts preliminary survey, assesses control environment, and evaluates fraud risk for the engagement."*

Model: `AuditSurvey` has a **OneToOneField** to `AuditEngagement`. There is only ever **one survey per engagement**. A standalone "Audit Surveys" list page showing one survey per engagement is a redundant list of lists. The survey exists in the planning phase context of its engagement.

#### Risk Control Matrix — embed in Engagement Detail, Add RCM Detail Sub-Page

> SRS Req 22 / SRS Flow 8:
> *"LA develops Risk and Control Matrix and prioritizes the auditable process areas, develops the audit scope from the RCM, prepares draft audit program."*

RCM is an engagement-scoped artifact. However, RCM **Entries** (the individual risk/control rows) require detail management that can't fit in a one-card summary. The solution is:
- RCM card in Engagement detail with `+ Add` button
- Clicking an RCM row opens the **RCM detail sub-page** (existing route pattern, no sidebar entry)

#### Audit Programs — embed in Engagement Detail

> SRS Req 23:
> *"CIA approves the audit program and instructs LA to prepare Engagement Notification."*

The program is designed for a specific engagement's RCM. Its workflow (draft → CIA Approval) is an engagement-internal action. The approval status is gating for the Engagement Notification, which is also engagement-scoped.

#### Engagement Notifications — embed in Engagement Detail (already done)

> SRS Req 24–26:
> *"LA prepares EN and submits for vetting. CIA approves. EN sent to auditee."*

The `EngagementNotificationsSection` component already embeds this in `EngagementDetailPage`. The standalone route `/engagement-notifications` in App.tsx has no corresponding sidebar item in the dashboard and is an orphaned route. Remove it.

---

## 3. Target Information Architecture

The refactored navigation hierarchy mirrors the **Audit Universe → Auditable Entities** pattern at every level:

```
Sidebar (GRC → Internal Audit)
│
├── Audit Universe                    /grc/audit-universe
│   └── Universe Detail               /grc/audit-universe/:id
│       └── [Auditable Entities]      embedded section (dialogs)
│
├── Audit Plans (RBIAP)               /grc/audit-plans
│   └── Plan Detail                   /grc/audit-plans/:planId
│       └── [Audit Memos]             embedded section  ← NEW
│           └── Memo Workflow         shown via WO Console inside Plan detail
│
├── Audit Engagements                 /grc/engagements
│   └── Engagement Detail             /grc/engagements/:engagementId
│       ├── [Declarations]            embedded section (with Sign action)
│       ├── [Audit Survey]            embedded section (1 max)
│       ├── [Risk Control Matrix]     embedded section
│       │   └── RCM Detail           /grc/engagements/:id/rcm/:rcmId  ← NEW route (no sidebar)
│       │       └── RCM Entries      embedded in RCM detail
│       ├── [Audit Programs]          embedded section (with CIA approve action)
│       ├── [Engagement Notifications] embedded section
│       ├── [Working Papers]          embedded section (clickable → WP detail)
│       └── WO Workflow Console       embedded
│
├── Audit Findings                    /grc/audit-findings        (keep — cross-engagement)
├── Working Papers (list)             /grc/working-papers        (keep — CIA cross-eng. browse)
├── Audit Reports                     /grc/audit-reports         (keep — quarterly consolidation)
├── Audit Recommendations             /grc/audit-recommendations (keep — cross-engagement tracking)
├── Audit Monitoring                  /grc/audit-monitoring      (keep — cross-engagement)
└── Configuration                     /grc/configuration         (keep)
```

### What is Removed from the Sidebar

| Removed Item | Route Removed | Reason |
|---|---|---|
| Audit Memos | `/grc/audit-memos` | Embed in Audit Plan detail |
| Declarations of Independence | `/grc/declarations` | Embed in Engagement detail |
| Preliminary Surveys | `/grc/audit-surveys` | Embed in Engagement detail |
| Risk Control Matrix (standalone) | `/grc/risk-control-matrix` | Embed in Engagement detail |
| Audit Programs (standalone) | `/grc/audit-programs` | Embed in Engagement detail |
| Engagement Notifications (standalone) | `/grc/engagement-notifications` | Embed in Engagement detail |

---

## 4. What Already Works vs What Needs Building

### 4.1 Already Correct (no changes needed)

| Component | Status | Notes |
|---|---|---|
| `AuditUniverseDetailPage` → `AuditableEntitiesSection` | ✅ Done | The reference pattern |
| `EngagementDetailPage` — Declarations card | ✅ Done | Already embedded |
| `EngagementDetailPage` — Audit Surveys card | ✅ Done | Already embedded |
| `EngagementDetailPage` — Risk Control Matrix card | ✅ Done | Already embedded (summary only) |
| `EngagementDetailPage` — Audit Programs card | ✅ Done | Already embedded (summary only) |
| `EngagementDetailPage` — Working Papers card | ✅ Done | Clickable rows → detail page |
| `EngagementDetailPage` — Workflow Console | ✅ Done | Embedded WO Console |
| `EngagementNotificationsSection` in Engagement detail | ✅ Done | Already embedded |

### 4.2 Needs to Be Built

#### Priority 1 — Audit Memos Section in Audit Plan Detail

**File:** `AuditPlanDetailPage.tsx`

Add an `AuditMemosSection` component following the exact pattern of `AuditableEntitiesSection`. This section should:
- Load memos filtered by `audit_plan_id`
- Show status badge (draft / cia_review / approved)
- Show `+ Prepare Memo` button when plan is `approved` or `implementation`
- Each memo row shows lead auditor, auditable entity, status
- Clicking a memo row opens a **Memo Detail drawer/dialog** showing:
  - Full memo content (title, purpose, scope_summary)
  - Timeline dates
  - WO Workflow Console for the CIA Review → DG Approval workflow
  - `Submit for Review` action button (when `status = draft`)
  - `Download Approved Memo` button (when `stamped_document_url` populated)

**New Component:** `AuditMemosSection.tsx` (pattern: `AuditableEntitiesSection.tsx`)
**New Dialog:** `AuditMemoDetailDialog.tsx` (with embedded WO Console)

#### Priority 2 — Sign Declaration Action in Engagement Detail

The Declarations card in `EngagementDetailPage` currently shows declaration rows as static display items (no click action). Per SRS Req 16, team members must **sign** the declaration.

**Add to Declarations card:**
- Clicking a declaration row opens a `DeclarationDetailDialog` showing full declaration text + conflict details
- When `status = pending`: show `Sign Declaration` button → confirmation dialog → `POST /declarations/:id/sign/`
- After signing: `status` badge updates to `signed` + `signed_at` timestamp shows
- Show green `Independent` / red `Has Conflict` badge on each row

#### Priority 3 — RCM Detail Sub-Page

The RCM card currently shows a summary row per RCM. But RCM **Entries** (the individual risk/control rows) cannot be managed from a one-line summary.

**Add:**
- Route: `/grc/engagements/:engagementId/rcm/:rcmId` → `RCMDetailPage`
- Clicking an RCM row in the Engagement detail navigates to this page
- `RCMDetailPage` shows:
  - RCM header (title, reference_number, scope, engagement context)
  - Back button → returns to Engagement detail
  - Entries table with `+ Add Entry` button
  - Each entry: risk description, control, test approach, risk rating, residual rating
  - Entry CRUD actions (edit, delete)
  - RCM status + Submit/Approve actions
  - WO Workflow Console (RCM approval workflow if applicable)

#### Priority 4 — Audit Program Status Actions in Engagement Detail

The Audit Program card in Engagement detail shows programs as static rows. Per SRS Req 23 (CIA approves the program), there need to be workflow actions visible from here.

**Add to Audit Program rows:**
- Clicking a program row opens `AuditProgramDetailDialog`:
  - Program content (title, objectives, procedures, scope)
  - `Submit for CIA Approval` button (when `status = draft`)
  - WO Workflow Console for CIA approval workflow
  - `Download Approved Program` button (when approved + stamped)

#### Priority 5 — Remove Standalone Pages from Sidebar + Routes

**GRCDashboard.tsx:** Remove tiles for:
- Audit Memos
- Declarations of Independence
- Preliminary Surveys
- Risk Control Matrix (the tile exists but the current route is a dead link)
- Audit Programs
- (Engagement Notifications has no tile — just remove App.tsx route)

**App.tsx:** Remove or comment out routes:
- `audit-memos` → `AuditMemosPage`
- `declarations` → `DeclarationsPage`
- `audit-surveys` → `AuditSurveysPage`
- `risk-control-matrix` → `RiskControlMatrixPage`
- `audit-programs` → `AuditProgramsPage`
- `engagement-notifications` → `EngagementNotificationsPage`

> ⚠️ **Keep** the standalone page files temporarily — do not delete them yet. Remove router links first and verify UX. The pages can be deleted in a cleanup pass once the embedded components are confirmed working.

---

## 5. Implementation Order

Follow this sequence to avoid breaking existing functionality:

```
Step 1: Build AuditMemosSection + AuditMemoDetailDialog
        → Wire into AuditPlanDetailPage
        → Test: create memo from Plan detail, submit, approve via WO

Step 2: Add Sign Declaration action to Engagement Declarations card
        → Test: create declaration, sign it, verify status change

Step 3: Build RCMDetailPage (route: /engagements/:id/rcm/:rcmId)
        → Make RCM rows in Engagement detail clickable (navigate to detail page)
        → Test: create RCM, navigate to detail, add/edit entries

Step 4: Add AuditProgramDetailDialog with Submit/Approve actions
        → Wire into Audit Programs card in Engagement detail
        → Test: create program, submit for CIA, approve via WO

Step 5: Remove standalone sidebar tiles (GRCDashboard.tsx)
        → Remove App.tsx routes
        → Verify no broken navigation links remain
        → Update INTERNAL_AUDIT_SAMPLE_DATA.md navigation notes
```

---

## 6. SRS Compliance Verification

This refactoring does **not** remove any SRS capability. Every action remains accessible, just through a more logical context:

| SRS Requirement | Current Access | After Refactoring |
|---|---|---|
| Req 10–14: CIA prepares Audit Memo | Via `/grc/audit-memos` standalone page | Via Audit Plan detail → Memos section |
| Req 16: Team signs Declaration | Via `/grc/declarations` standalone page | Via Engagement detail → Declarations card → Sign button |
| Req 19–21: LA conducts preliminary survey | Via `/grc/audit-surveys` standalone page | Via Engagement detail → Audit Survey card |
| Req 22: LA develops RCM with entries | Via `/grc/risk-control-matrix` (dead link) | Via Engagement detail → RCM card → RCM detail page |
| Req 23: CIA approves Audit Program | Via `/grc/audit-programs` standalone page | Via Engagement detail → Programs card → Program detail dialog |
| Req 24–26: LA prepares Engagement Notification | Via `/grc/engagement-notifications` standalone page | Via Engagement detail → Notifications section (already done) |
| Req 5–9: Working Papers + Fieldwork | Via `/grc/working-papers` standalone page | BOTH: Engagement detail card + standalone page (keep both) |
| SRS §1.8.5: Quarterly Reports | Via `/grc/audit-reports` | Keep standalone (consolidates multiple engagements) |
| SRS §1.8.6: Monitoring | Via `/grc/audit-monitoring` | Keep standalone (cross-engagement implementation tracking) |

---

## 7. The Canonical Design Principle (Summary)

> **Rule:** An entity that can only exist in the context of a single parent should NEVER appear as a top-level sidebar item.

| Has own identity / cross-entity use → **Keep sidebar entry** | Context-dependent / single parent → **Embed in parent detail** |
|---|---|
| Audit Universe (FY-level, multi-engagement) | Auditable Entities (always within a Universe) |
| Audit Plans (multi-engagement, 4-stage workflow) | Audit Memos (always within a Plan) |
| Audit Engagements (the main workbench) | Declarations (always within an Engagement) |
| Audit Findings (CIA needs cross-eng. view) | Audit Survey (always within an Engagement; OneToOne) |
| Working Papers (deep links from multiple places) | Risk Control Matrix (always within an Engagement) |
| Audit Reports (quarterly, multi-engagement) | RCM Entries (always within an RCM) |
| Audit Recommendations (cross-eng. tracking) | Audit Programs (always within an Engagement) |
| Audit Monitoring (implementation rate tracking) | Engagement Notifications (always within an Engagement) |
| Configuration (system-wide lookup tables) | |

---

## 8. Files Affected Summary

| File | Action |
|---|---|
| `GRCDashboard.tsx` | Remove 5–6 tile entries from `auditItems` array |
| `App.tsx` | Remove 6 routes (audit-memos, declarations, audit-surveys, risk-control-matrix, audit-programs, engagement-notifications) |
| `AuditPlanDetailPage.tsx` | Add `<AuditMemosSection planId={planId} />` |
| `AuditMemosSection.tsx` | **NEW** — pattern: `AuditableEntitiesSection.tsx` |
| `AuditMemoDetailDialog.tsx` | **NEW** — shows memo detail + WO Console |
| `EngagementDetailPage.tsx` | Add clickable Declaration rows (→ sign), clickable RCM rows (→ navigate), clickable Program rows (→ dialog) |
| `DeclarationDetailDialog.tsx` | **NEW** or extend `CreateDeclarationDialog.tsx` to a "view" mode |
| `RCMDetailPage.tsx` | **NEW** — route `/grc/engagements/:engagementId/rcm/:rcmId` |
| `AuditProgramDetailDialog.tsx` | **NEW** — shows program + submit/approve actions |
| `INTERNAL_AUDIT_SAMPLE_DATA.md` | Update Phase 7a navigation note (Audit Memos accessed from Plan detail, not sidebar) |

---

*This proposal reflects strict adherence to SRS `AUDT2_ext.md` and the established Audit Universe design pattern already present in the codebase.*
