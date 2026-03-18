# Audit Findings — SRS vs Implementation Gap Analysis

> **Date:** 2026-03-18  
> **Analyst:** GitHub Copilot  
> **SRS Reference:** §1.8.3 Conducting Internal Audit (Steps 15–19, 21, 12–13)

---

## SRS Requirements for Audit Findings

| Step | Actor | Requirement |
|---|---|---|
| Step 15 | Audit Team Member | Performs tests, documents outputs in Working Papers — findings emerge from WP evidence |
| Step 16 | Lead Auditor | Reviews WP evidence — each finding must trace to a WP and match the critical elements |
| Step 17 | LA + Auditee | Pre-exit meeting: findings **discussed** with auditee; auditee raises factual clarifications |
| Step 18 | Lead Auditor | Consolidates findings from all WPs; submits package (WPs + findings) for CIA approval |
| Step 19 | CIA | Reviews and approves WPs (and by extension their findings) |
| Step 21 | Internal Auditor | Documents draft Internal Audit Report — findings become report content |
| Steps 12–13 | LA / CIA | Final report incorporates **written auditee responses** to each finding; CIA approves for distribution |

---

## What is Correctly Implemented ✅

| Area | Detail |
|---|---|
| 4 C's structure | Condition, Criteria, Cause, Effect all present as separate required fields |
| Status lifecycle | `draft → discussed → final` correctly modelled |
| Both responses required before `final` | `AuditFindingFinalizeView` enforces `auditee_response` AND `management_response` non-empty |
| `final` is terminal | `put`/`patch`/`delete` all blocked on `status == 'final'` |
| Auto-generated reference number | Format `FND-{engagement_ref}-{sequence:03d}` |
| Engagement phase gate | Finding creation blocked unless `engagement.status in ('fieldwork', 'reporting')` |
| Separate auditee permission | `CanRespondToAuditFinding` permission class exists for `grc:audit_finding:respond` |
| Lookup fields | FY, Quarter, Severity, FindingType, RiskRating all present as FK lookups |
| Kafka domain event | `FINDING_CREATED` event published on creation |
| Delete guard | Cannot delete a finding that has active recommendations |

---

## Gaps Found ❌ / ⚠️

### GAP-F1 — ~~Working Paper Linkage Not Enforced~~ — REVISED / DOWNGRADED

**Original claim:** `working_paper_id` should be mandatory.  
**After re-reading SRS:** **This was wrong.** SRS Step 7 explicitly says: *"If controls are found to be inadequate, Audit Team Members include as audit finding"* — this happens during the preliminary survey, BEFORE any Working Paper exists. Making `working_paper_id` mandatory would break this valid SRS path.

**Actual status:** ✅ `working_paper_id` being optional is **correct per SRS**.

**Real residual gap (merged into GAP-F2):** If a `working_paper_id` IS supplied, there is no check that the WP belongs to the same engagement. See GAP-F2.

---

### GAP-F2 — WP Must Belong to Same Engagement (HIGH)

**SRS says:** Finding traces to a WP — which must be under the same engagement.  
**Implementation:** No cross-check between `finding.engagement_id` and `working_paper.audit_engagement_id`.  
**Effect:** Finding can reference a WP from a completely different engagement.

**Fix:**
```python
# After WP existence check:
wp = get_object_or_404(WorkingPaper, id=working_paper_id)
if str(wp.audit_engagement_id) != str(engagement_id):
    return Response(
        {"success": False, "error": {
            "message": "Working paper does not belong to this engagement",
            "code": "WP_ENGAGEMENT_MISMATCH"
        }},
        status=400
    )
```

---

### GAP-F3 — Role Separation in Responses Not Enforced (HIGH)

**SRS says:** Auditee provides `auditee_response`; Management provides `management_response` — different people with different roles.  
**Implementation:** `PATCH /findings/{id}/responses/` allows any single caller with `grc:audit_finding:respond` OR `grc:audit_finding:manage` to set BOTH fields simultaneously. An auditor or CIA could fabricate the auditee's response.

**Fix — split into two permission checks inside `AuditFindingResponseView.patch()`:**
```python
auditee_response = request.data.get('auditee_response')
management_response = request.data.get('management_response')

is_manager = CanManageAuditFinding().has_permission(request, self)
is_responder = CanRespondToAuditFinding().has_permission(request, self)

# Auditee can only set auditee_response
if auditee_response is not None and not is_manager and is_responder:
    management_response = None  # strip management_response from auditee's request

# Only managers (LA/CIA) can set management_response
if management_response is not None and not is_manager:
    return Response(
        {"success": False, "error": {
            "message": "Only auditors can provide management response",
            "code": "PERMISSION_DENIED"
        }},
        status=403
    )
```

---

### GAP-F4 — `discussed` Not Gated on Pre-Exit Meeting Completion (MEDIUM)

**SRS says:** Step 17 — Pre-exit meeting must happen before findings are marked as `discussed`.  
**Implementation:** No gate — auditor can mark any finding `discussed` before a pre-exit meeting even exists.

**Fix — In `AuditFindingFinalizeView.post()` before `draft → discussed` transition:**
```python
if target_status == 'discussed':
    from apps.core.models.audit_entities import AuditMeeting
    has_completed_preexit = AuditMeeting.objects.filter(
        engagement=finding.engagement,
        meeting_type='pre_exit',
        status='completed'
    ).exists()
    if not has_completed_preexit:
        return Response(
            {"success": False, "error": {
                "message": "A completed Pre-Exit meeting is required before marking a finding as discussed",
                "code": "PRE_EXIT_MEETING_REQUIRED"
            }},
            status=400
        )
```

---

### GAP-F5 — `update-status/` Endpoint Bypasses All Guards (HIGH — worse than originally noted)

**SRS says:** Finding can only be `final` after it was discussed at pre-exit AND both responses are recorded.  
**Implementation:** `AuditFindingStatusUpdateView` (endpoint `update-status/`) has transition table:
```python
'draft': ['discussed', 'final'],   # ← draft→final allowed directly!
'discussed': ['final', 'draft'],
```
This is a **complete backdoor** — it skips:
1. The `discussed` intermediate step (pre-exit meeting requirement from GAP-F4)
2. The auditee + management response requirement (enforced only in `finalize/`)

The `finalize/` endpoint is properly guarded but `update-status/` makes all those guards irrelevant.

**Fix:**
- Remove `'final'` from the `draft` transitions in `AuditFindingStatusUpdateView`
- OR delete `AuditFindingStatusUpdateView` entirely and consolidate to `finalize/` only (see GAP-F8)

---

### GAP-F6 — No Lifecycle Timestamps on Model (LOW)

**SRS says:** Audit trail of when each finding was discussed and finalized.  
**Implementation:** Only `created_at` and `updated_at`. No `discussed_at` or `finalized_at` fields.

**Fix — Add to `AuditFinding` model:**
```python
discussed_at = models.DateTimeField(null=True, blank=True)
finalized_at = models.DateTimeField(null=True, blank=True)
```
And set them in `AuditFindingFinalizeView`:
```python
from django.utils import timezone
if target_status == 'discussed':
    finding.discussed_at = timezone.now()
elif target_status == 'final':
    finding.finalized_at = timezone.now()
```

---

### GAP-F7 — Working Paper Shown as Raw UUID in Detail Dialog (LOW / Frontend)

**SRS says:** Finding must be traceable to a Working Paper.  
**Implementation:** `AuditFindingDetailDialog.tsx` displays `item.working_paper_id` as a raw UUID string.  
**Effect:** User sees `6e00dc91-3fa0-4e9c-ac9d-1d9723bca2e0` instead of `WP-ENG-20252026-001-002 — hjhhh...`.

**File:** `frontend/apps/staff-portal/src/components/grc/AuditFindingDetailDialog.tsx`  
**Fix:** Either expand the type to include a nested `working_paper` object, or fetch the WP title separately using the UUID. Simplest quick fix — display as `WP Ref: {working_paper_id?.slice(0,8)}...` until proper nesting is added.

---

### GAP-F8 — Redundant Status Endpoints (INFO)

Two endpoints both handle `draft → discussed`:
- `POST /findings/{id}/finalize/` — used by the `FindingLifecycleDialog` in frontend
- `POST /findings/{id}/update-status/` — also handles same transitions

**Effect:** No functional bug, but creates confusion about which endpoint to call. The `update-status/` endpoint is stricter (no pre-exit gate being added per GAP-F4 fix). The `finalize/` endpoint has the response requirements.

**Recommendation:** Deprecate `update-status/` and route everything through `finalize/`. Or clearly document in code which endpoint handles what.

---

## Priority Fix Order

| Priority | Gap | Verified? | Impact | Effort |
|---|---|---|---|---|
| 1 | GAP-F5 — `update-status/` backdoor bypasses all guards | ✅ Real | HIGH | Low — remove `'final'` from draft transitions |
| 2 | GAP-F3 — Role separation in responses | ✅ Real | HIGH | Low — backend only |
| 3 | GAP-F2 — WP engagement mismatch (when WP provided) | ✅ Real | MEDIUM | Low — backend only |
| 4 | GAP-F4 — `discussed` gate requires pre-exit meeting | ✅ Real | MEDIUM | Low — backend only |
| 5 | GAP-F7 — UUID shown in UI instead of WP reference | ✅ Real | LOW | Low — frontend only |
| 6 | GAP-F6 — No lifecycle timestamps | ✅ Real | LOW | Medium — model migration |
| 7 | GAP-F8 — Redundant endpoints | ✅ Real | INFO | Low — consolidate to `finalize/` |
| — | GAP-F1 — WP mandatory | ❌ Wrong | N/A | Do not implement |

---

## Endpoints Reference

| Method | URL | Purpose |
|---|---|---|
| `GET/POST` | `/api/v1/grc/audit/findings/` | List findings / Create new finding |
| `GET/PUT/PATCH/DELETE` | `/api/v1/grc/audit/findings/{id}/` | Read/Update/Delete a finding |
| `POST` | `/api/v1/grc/audit/findings/{id}/finalize/` | Status transition: `draft→discussed`, `discussed→final/draft` |
| `POST` | `/api/v1/grc/audit/findings/{id}/update-status/` | Simple status update (redundant — see GAP-F8) |
| `PATCH` | `/api/v1/grc/audit/findings/{id}/responses/` | Set `auditee_response` / `management_response` |

## Key Files

| File | Purpose |
|---|---|
| `grc-service/apps/core/models/audit_entities.py` | `AuditFinding` model (~line 869) |
| `grc-service/apps/api/views/audit_finding_views.py` | All finding views (CRUD + lifecycle) |
| `grc-service/apps/api/serializers/audit_serializers.py` | `AuditFindingSerializer` (~line 153) |
| `grc-service/apps/api/permissions_jwt.py` | `CanManageAuditFinding`, `CanRespondToAuditFinding` |
| `frontend/.../AuditFindingsPage.tsx` | List page with lifecycle action button |
| `frontend/.../AuditFindingDetailDialog.tsx` | Detail view dialog |
| `frontend/.../FindingLifecycleDialog.tsx` | `discussed`/`final` transitions + response entry |
| `frontend/.../useAuditFindings.ts` | React Query hooks for all finding mutations |
