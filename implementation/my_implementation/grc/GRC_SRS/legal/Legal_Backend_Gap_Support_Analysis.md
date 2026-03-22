# Legal Module — Backend Support Analysis for Frontend SRS Gaps

**Reference (Frontend Gap Source):** `Legal_Frontend_SRS_Gap_Analysis.md` (35 gaps)  
**Reference (Backend Plan):** `Legal_Module_Implementation_Plan.md`  
**Backend Code Verified:** `grc-service/apps/api/views/legal_*.py`, `grc-service/apps/core/models/legal_entities.py`, `grc-service/apps/api/permissions_jwt.py`  
**Analysis Date:** 2026-03-21  
**Analyst:** Backend code audit (automated)

---

## Purpose

For every gap identified in the frontend SRS gap analysis (35 gaps across CRITICAL / SIGNIFICANT / MINOR / OVER-SCOPE categories), this document answers the question:

> **Does the backend already have the API, model fields, permission codes, or endpoint needed to fix this frontend gap? Or does the backend have the same gap — requiring backend changes before the frontend can be fixed?**

This analysis **must be read before beginning frontend implementation** of any gap fix. Backend-only or dual-layer gaps are blockers.

---

## Summary Table

| Gap ID | Category | Gap Title | Backend Status | Backend Change Needed? |
|--------|----------|-----------|---------------|----------------------|
| CRIT-01 | Critical | Submission creation permission gated | ❌ Backend Also Has Gap | YES — new API permission or any-user access |
| CRIT-02 | Critical | Registry Officer role not mapped | ❌ Backend Also Has Gap | YES — new permission code required |
| CRIT-03 | Critical | CASE_STAGES enum mismatch | ✅ Backend Supports Fix | No — correct enum in backend; only frontend fix |
| CRIT-04 | Critical | `closure_pending` used but undefined | ✅ Backend Supports Fix | No — confirmed NOT a backend stage |
| CRIT-05 | Critical | Breach report intake permission wrong | ❌ Backend Also Has Gap | YES — new permission or any-user access |
| SIG-01 | Significant | Case archiving UI completely missing | ✅ Backend Fully Supports | No — full archive API + model exists |
| SIG-02 | Significant | Meeting invitee directive access | ⚠️ Backend Partial Support | Partial — data model exists; API filtering missing |
| SIG-03 | Significant | Litigation directive DG approval (configurable) | ❌ Backend Also Has Gap | YES — `requires_dg_approval` field missing from model |
| SIG-04 | Significant | In-app notification center not addressed | ⚠️ Backend Partial Support | Partial — Kafka event infra exists; WO has NotificationModel |
| SIG-05 | Significant | Data-level access control (My Cases) | ⚠️ Backend Partial Support | Partial — `assigned_legal_officer_ids` stored but not enforced in list filter |
| SIG-06 | Significant | Response types (defendant) incomplete | ✅ Backend Fully Supports | No — complete type lists in model; frontend needs alignment |
| SIG-07 | Significant | Recovered Amount not in plaintiff financials section | ✅ Backend Fully Supports | No — `recovered_amount` field confirmed on `FinancialPlaintiff` |
| SIG-08 | Significant | Member data sync from Corporate Service | ✅ Backend Fully Supports | No — `email` and `department` fields stored on `Member` |
| SIG-09 | Significant | `On Hold` stage has no CTAs | ⚠️ Backend Partial Support | Partial — status value exists; no dedicated hold/resume endpoints |
| SIG-10 | Significant | RescheduleMeetingDialog missing | ⚠️ Backend Partial Support | Partial — PATCH exists; no dedicated reschedule endpoint or reason storage |
| SIG-11 | Significant | Settlement/Judgment approval workflow UI missing | ✅ Backend Fully Supports | No — submit + DG decision endpoints fully implemented |
| MIN-01 | Minor | Quorum not met → reschedule flow | ✅ Backend Supports Fix | No — `can_start` enforces quorum; frontend UX improvement only |
| MIN-02 | Minor | Minutes approval type (configurable) | ✅ Backend Supports Fix | No — workflow templates control this; frontend doc note only |
| MIN-03 | Minor | Task `auto_created` field missing | ❌ Backend Also Has Gap | YES — `auto_created` field absent from `TaskLitigation` model |
| MIN-04 | Minor | Secretary multi-body assignment UI | ✅ Backend Fully Supports | No — `secretary_user_ids` JSONField exists on `GoverningBody` |
| MIN-05 | Minor | Public Register future portal note | ✅ Backend Supports Fix | No — documentation-only gap; backend fully supports publish state |
| MIN-06 | Minor | Conflict of interest not persisting across meetings | ✅ Backend Fully Supports | No — `ConflictDeclaration` scoped to `agenda_item`; data model correct |
| MIN-07 | Minor | `canManageMembers` invalid permission ref | ✅ Backend Supports Fix | No — correct class is `CanManageLegalGoverningBody`; frontend var name fix only |
| MIN-08 | Minor | Task reminder schedule undocumented | ✅ Backend Supports Fix | No — Celery Beat handles reminders; frontend doc note only |
| MIN-09 | Minor | Member.position vs MeetingParticipant.role confusion | ✅ Backend Supports Fix | No — both properly modeled separately; frontend TypeScript comments needed |
| MIN-10 | Minor | Approval chain `actor_name` vs audit log | ✅ Backend Supports Fix | No — `approval_chain` JSONField on filings stores `actor_name`; `LegalAuditLog` does not |
| MIN-11 | Minor | `DG_REVIEW_STATUS` values not in Phase 2.2 | ✅ Backend Supports Fix | No — `dg_review_status` field exists on both case models |
| MIN-12 | Minor | Resolution Detail Page missing | ✅ Backend Fully Supports | No — `Resolution` model complete; data accessible |
| MIN-13 | Minor | PlaintiffAdvocate column missing from list | ✅ Backend Supports Fix | No — `plaintiff_advocate` field on `CaseDefendant`; frontend list spec update only |
| MIN-14 | Minor | Activity log status transitions not displayed | ✅ Backend Supports Fix | No — `metadata.from_status`/`to_status` stored; frontend just not reading it |
| MIN-15 | Minor | Start Meeting CTA missing time-window guard | ✅ Backend Enforces | No — `Meeting.can_start` enforces `scheduled_start <= now`; frontend UX guard only |
| MIN-16 | Minor | DirectiveDetailPage assigned-user check undocumented | ✅ Backend Supports Fix | No — `assigned_user_id` field exists; frontend identity check pattern needed |
| MIN-17 | Minor | `CreateResolutionDialog` contradicts auto-creation rule | ✅ Backend Supports Fix | No — `Resolution.OneToOneField(MeetingAgenda)` confirms auto-creation; remove dialog |
| MIN-18 | Minor | GoverningBody missing meeting number prefix config | ❌ Backend Also Has Gap | YES — model has NO `meeting_number_prefix` or `meeting_number_format` fields |
| OVER-01 | Over-Scope | Legal Notices feature not in SRS | 🔵 Backend Has Full Implementation | No backend change needed; scope decision only |

**Result counts:**
| Status | Count |
|--------|-------|
| ❌ Backend Also Has Gap (backend blocker) | **6** |
| ⚠️ Backend Partial Support | **4** |
| ✅ Backend Fully Supports / Supports Fix | **24** |
| 🔵 Backend Has Implementation (out of SRS scope) | **1** |

---

## Section 1 — ❌ Gaps Where Backend Also Has the Same Issue (Backend Blockers)

These gaps **cannot be fixed by frontend changes alone**. Backend development is required first.

---

### CRIT-01 — Submission Creation: Any-User Access Not Enforced

**Gap:** SRS §1.1 states any authenticated user can create a `SubmissionForDetermination`. The frontend plan incorrectly gates this on `canManageGoverningBody`.

**Backend Verification:**
- File: `apps/api/views/legal_governing_body_views.py`
- Class: `SubmissionForDeterminationListCreateView`
- `POST` permission check: **`CanManageLegalGoverningBody`** — same restrictive permission as the frontend gap
- No bypass path or secondary permission check for `POST`

**Backend Verdict:** ❌ Backend ALSO incorrectly restricts. The API rejects requests from any user not holding `grc:legal_governing_body:manage`. Department Users and standard staff cannot create submissions via the API.

**Required Backend Work:**
1. Add a new permission code (e.g., `grc:legal_submission:create`) in `permissions_jwt.py`, OR
2. Change `SubmissionForDeterminationListCreateView.post()` to require only `IsAuthenticated` (JWT token presence), with the `CanManageLegalGoverningBody` gate moved to `PUT/PATCH/DELETE` only.
3. Update `grc-service.json` service manifest with the new permission code.
4. Backend fix must be deployed before the frontend `SubmissionsPage` create button can be opened to all authenticated users.

---

### CRIT-02 — Registry Officer Role: No Backend Permission Code

**Gap:** SRS §4.1 defines a Registry Officer as a distinct role that can register cases. No such permission exists in the frontend plan (28 permission codes).

**Backend Verification:**
- File: `apps/api/permissions_jwt.py`
- Full permission class list verified: `CanViewLegalCase`, `CanManageLegalCase`, `CanCloseLegalCase`, `CanViewLegalGoverningBody`, `CanManageLegalGoverningBody`, `CanViewLegalMeeting`, `CanManageLegalMeeting`, `CanApproveLegalMeeting`, `CanViewLegalSettlement`, `CanManageLegalSettlement`, `CanApproveLegalSettlement`, `CanViewLegalJudgment`, `CanManageLegalJudgment`, `CanRecordLegalJudgment`, `CanViewLegalDirective`, `CanManageLegalDirective`, `CanViewLegalAppeal`, `CanManageLegalAppeal`, `CanViewLegalNotice`, `CanManageLegalNotice`, `CanViewPublicDecision`, `CanManagePublicDecision`
- **No `CanRegistryOfficer` or `grc:legal_case:register` permission class exists.**

**Backend Verdict:** ❌ The Registry Officer role is completely absent from the backend permission system. Case creation requires `CanManageLegalCase` — a permission the SRS suggests should be separate from Registry Officer capability.

**Required Backend Work:**
1. Decide with the Legal team whether Registry Officer has the same access as Legal Officer (i.e., `CanManageLegalCase` covers the role), or whether a separate `grc:legal_case:register` code is needed.
2. If separate: add `CanRegistryOfficer` (or `CanRegisterLegalCase`) permission class to `permissions_jwt.py` and register in `grc-service.json`.
3. Frontend RBAC matrix (Phase 5.1, Phase A.8.2) cannot be corrected until backend decision is made.

---

### CRIT-05 — Breach Report Intake: Department User Access Not Supported by API

**Gap:** SRS §5.1 specifies that Department Users can initiate a simplified breach report intake. The frontend plan incorrectly gates the "Raise Breach Report" button on `canManageCases`.

**Backend Verification:**
- File: `apps/api/views/legal_case_views.py`
- Class: `CasePlaintiffListCreateView`
- `POST` permission check: **`CanManageLegalCase`** — restricts to Legal Officers and Legal Managers only
- No differentiated path for simplified breach report intake exists
- `CasePlaintiff.REGISTRATION_TYPE_CHOICES` = `[('simplified', 'Breach Report Intake'), ('full', 'Full Breach Report')]` — model supports both types, but the API gate prevents Department Users from reaching the endpoint

**Backend Verdict:** ❌ The model has `registration_type = 'simplified'` for breach intake, but the API view enforces `CanManageLegalCase` for ALL POST requests to `/legal/cases/plaintiff/`. Department Users are blocked at the API level.

**Required Backend Work:**
1. Add a dedicated endpoint or branched permission check in `CasePlaintiffListCreateView.post()` for `registration_type == 'simplified'` that allows any authenticated user to call the simplified intake path.
2. Alternatively, add a new permission code `grc:legal_case:intake` and grant it to Department User role in the IAM service.
3. Backend fix must be deployed before the breach report intake CTA can be shown to Department Users in the UI.

---

### SIG-03 — Litigation Directive DG Approval: Configurable Flag Not in Model

**Gap:** SRS §4.2 states closure of litigation directives may require DG approval (configurable). The frontend plan doesn't address this conditional workflow.

**Backend Verification:**
- File: `apps/core/models/legal_entities.py`
- Class: `LitigationDirective`
- Fields confirmed: `issued_by_user_id`, `issue_date`, `instruction`, `due_date`, `status`, `completion_summary`, `completion_date`, `attachments`
- `STATUS_CHOICES`: `[('open', 'Open'), ('in_progress', 'In Progress'), ('closed', 'Closed')]`
- **No `requires_dg_approval_for_closure` field exists.**
- **No `requires_dg_approval_for_closure` field exists in any system config model either (searched entire `legal_entities.py`).**

**Backend Verdict:** ❌ The configurable DG approval gate for litigation directive closure is completely absent from the backend model. There is no mechanism to enable/disable DG approval for this workflow. The `closed` status is set directly without any approval gate.

**Required Backend Work:**
1. Add `requires_dg_approval_for_closure: BooleanField(default=False)` to the `LitigationDirective` model (or to a system configuration model).
2. If approval is required: add a new workflow trigger and an intermediate `pending_dg_approval` status to `LitigationDirective.STATUS_CHOICES`.
3. Add corresponding API endpoint for DG to approve/reject litigation directive closure.
4. Frontend cannot implement the conditional closure flow (SIG-03) until backend model and endpoint are available.

**Notes:**
- This is an SRS requirement but the entire feature is missing from `Legal_Module_Implementation_Plan.md` as well — the backend plan does not mention this configurable behavior.
- Both the backend plan and the implementation were written without this requirement being captured.

---

### MIN-03 — TaskLitigation: `auto_created` Field Absent from Model

**Gap:** SRS §4.10 Business Rule 1 states tasks are auto-created for appeal deadlines, filing approvals, etc. The frontend plan has no `auto_created: boolean` indicator on tasks.

**Backend Verification:**
- File: `apps/core/models/legal_entities.py`
- Class: `TaskLitigation`
- Fields confirmed: `case_defendant`, `case_plaintiff`, `title`, `assigned_to_user_id`, `due_date`, `status`, `priority`, `related_entity_type`, `related_entity_id`
- **No `auto_created: BooleanField` or `source: CharField` field exists.**
- `related_entity_type` and `related_entity_id` exist but are generic link fields, not an explicit auto-creation flag.

**Backend Verdict:** ❌ The backend model does not distinguish system-generated tasks from manually created ones. All tasks are stored identically regardless of creation origin. A frontend "System" badge cannot be shown because no source indicator is stored.

**Required Backend Work:**
1. Add `auto_created: BooleanField(default=False)` to `TaskLitigation` model.
2. Set `auto_created=True` in all programmatic task creation paths (e.g., when DG decides to appeal a judgment, when a filing is sent for review).
3. Add migration for the new field.
4. Consider also adding `source_entity_type` and `source_entity_id` for traceability (maps `related_entity_type`/`related_entity_id` purpose more clearly), but at minimum `auto_created` boolean is needed.
5. Frontend `CaseTasksSection` can then add the "System" badge AFTER this backend field is available.

---

### MIN-18 — GoverningBody: Meeting Number Prefix Config Fields Absent from Model

**Gap:** SRS §1.2.1 and §6.2 require meeting numbers to be prefixed per governing body with a configurable format (sequential or financial year). The frontend plan's `GoverningBody` type has no such config fields.

**Backend Verification:**
- File: `apps/core/models/legal_entities.py`
- Class: `GoverningBody`
- Fields confirmed: `committee_type`, `name`, `description`, `secretary_user_ids`, `is_active`, `created_by/at`, `updated_by/at`
- **No `meeting_number_prefix` field exists.**
- **No `meeting_number_format` field exists.**
- Meeting number generation found in `legal_meeting_views.py` (`MeetingListCreateView.post()`): format is hardcoded as `MTG-{YYYYMM}-{NNN}` with no per-body prefix configuration.

**Backend Verdict:** ❌ The SRS requirement for per-body configurable meeting number prefix and format is **not implemented in the backend at all**. The `GoverningBody` model is missing these fields and the meeting number generation logic uses a fixed global format.

**Required Backend Work:**
1. Add `meeting_number_prefix: CharField(max_length=20, blank=True)` to `GoverningBody` model.
2. Add `meeting_number_format: CharField(max_length=20, choices=[('sequential', 'Sequential'), ('financial_year', 'Financial Year')], default='sequential')` to `GoverningBody` model.
3. Update `LegalMeetingService.create_meeting()` (or `MeetingListCreateView.post()`) to read the body's prefix and format when generating the meeting number, replacing the hardcoded `MTG-{YYYYMM}-{NNN}` pattern.
4. Add a `MeetingCounter` migration if the sequence logic needs to be per-body-per-prefix.
5. This is a **critical system configuration gap** — existing meeting numbers will not have the correct format until this is implemented.
6. Frontend `CreateGoverningBodyDialog` can show the prefix/format fields ONLY after backend model is updated.

---

## Section 2 — ⚠️ Gaps Where Backend Partially Supports the Fix

These gaps have backend *infrastructure* but are missing a specific endpoint, field, or enforcement. The frontend can partially implement the UI, but full functionality requires backend collaboration.

---

### SIG-02 — Meeting Invitee Access to Directives (Data-Level Filtering)

**Frontend Gap:** Non-Legal staff who are meeting invitees should see directives in read-only mode. The standalone `DirectivesPage` gates access on `grc:legal_directive:view` only, excluding Department User invitees.

**Backend Verification:**
- `MeetingParticipant` model has `user_id`, `role` (`member|invitee|secretary`), `invitation_status` — invitee records exist.
- `MeetingDirective` model has `assigned_user_id` — individual assignment exists.
- Directive list views: permission check is `CanViewLegalDirective` only — **no invitee cross-check** in the view.
- There is no query that returns directives filtered by `MeetingParticipant.user_id`.

**Assessment:** ⚠️ The data exists (participant records link users to meetings; meeting has directives), but the API does not currently filter directive results by invitee participation. An invitee without `CanViewLegalDirective` would get a 403 on the directive list.

**Backend Work Needed:**
- Add invitee-based access path to directive list views: if `request.user_id` is in `MeetingParticipant` records for a meeting that has directives, include those directives in the response (filtered to read-only, meeting-scoped).
- OR: expose `GET /legal/meetings/{pk}/directives/` sub-resource endpoint that checks participant status instead of the permission code.

**Frontend Action Now:** Document the dual-access pattern in Phase 10; show an appropriate empty state for invitee-role users. Full fix requires backend update.

---

### SIG-04 — In-App Notification Center (Received Notifications)

**Frontend Gap:** SRS §6.4 requires push notifications to DG, Legal Officers, etc. The plan only covers action-toast notifications (user's own actions). No notification inbox or bell exists.

**Backend Verification:**
- GRC service publishes notification events to Kafka `notification-templates` topic on workflow state changes (confirmed in `grc-service/apps/core/templates/registry.py` pattern).
- Work Orchestration Service has `NotificationModel` (confirmed in `wo/apps/core/migrations/0020_notificationmodel_and_more.py`).
- `shared/constants/event_types.py` has `MEETING_NOTIFICATION_SENT` event type.
- **No in-app notification API endpoint exists within GRC service** — notification delivery is handled by WO service.

**Assessment:** ⚠️ The event publishing infrastructure exists (Kafka-based). WO service stores notifications. But the frontend needs an API endpoint to **query received notifications** for the current user — this endpoint should be on the WO service, not GRC service.

**Backend Work Needed:**
- Confirm WO service exposes `GET /notifications/?user_id=<UUID>&unread=true` or similar endpoint.
- If not: add a notification query endpoint to WO service.
- GRC service does not need changes — it already publishes events.

**Frontend Action Now:** If WO notification endpoint already exists (check WO service API), wire up the Legal module to the platform's existing notification bell component. If not, this remains blocked on WO service development. Document as Phase 2 scope.

---

### SIG-05 — Data-Level Access Control: Legal Officer "My Cases" Filtering

**Frontend Gap:** SRS §6.6 requires users to see only cases they are assigned to. The plan documents permission-level RBAC but not row-level assignment filtering.

**Backend Verification:**
- `CaseDefendant` has `assigned_legal_officer_ids: JSONField` (list of UUIDs).
- `CasePlaintiff` has `assigned_legal_officer_ids: JSONField` (list of UUIDs).
- **`CaseDefendantListCreateView.get()` does NOT filter by the requesting user's ID** within `assigned_legal_officer_ids`. All cases matching `CanViewLegalCase` permission are returned.
- Legal Managers and DG users will see all cases correctly, but Legal Officers can currently see cases not assigned to them.

**Assessment:** ⚠️ The assignment storage exists in the model, but the API doesn't enforce row-level filtering. Legal Officers receive all accessible cases, not just their assigned ones.

**Backend Work Needed:**
- In `CaseDefendantListCreateView.get()` and `CasePlaintiffListCreateView.get()`: if the requesting user has `CanViewLegalCase` but NOT `CanManageLegalCase` (i.e., is a Legal Officer, not a manager), add a filter: `Q(assigned_legal_officer_ids__contains=str(request.user_id))`.
- Preserve full visibility for Legal Managers, DG (senior roles).

**Frontend Action Now:** The frontend can add a "My Cases" / "All Cases" toggle filter for Legal Officers while the backend enforcement is pending. After backend fix, remove the toggle (filtering becomes automatic server-side).

---

### SIG-09 — `On Hold` Stage: No Dedicated Place/Resume Endpoints

**Frontend Gap:** SRS §4.1 includes `on_hold` as a valid case stage. No CTAs or service functions exist to transition to/from it.

**Backend Verification:**
- `CaseDefendant.STATUS_CHOICES` confirmed includes `('on_hold', 'On Hold')`.
- `CasePlaintiff.STATUS_CHOICES` confirmed includes `('on_hold', 'On Hold')`.
- Searched `legal_case_views.py` and `legal_directive_views.py` for `on_hold`, `place_on_hold`, `resume_from_hold`: **no dedicated action endpoints found**.
- The only way to set `on_hold` status is via a PATCH request on the case with `{"status": "on_hold"}`.

**Assessment:** ⚠️ The status value exists in the model. However, there are no named action endpoints (like the `archive/unarchive` pattern) for `on_hold`. No `hold_reason` or `hold_notes` field exists either.

**Backend Work Needed:**
- Add `POST /legal/cases/defendant/<pk>/hold/` and `POST /legal/cases/defendant/<pk>/resume/` endpoints (same pattern as `archive/unarchive`).
- These endpoints should enforce the correct permission (Legal Manager) and create an audit log entry.
- Add `hold_reason: TextField(blank=True)` to both `CaseDefendant` and `CasePlaintiff` models if the SRS requires a reason for the hold.
- Discuss with Legal team: which stages can transition to `on_hold` (e.g., `hearing_stage`, `directive_issued`)? The backend workflow config defines valid transitions.

**Frontend Action Now:**  
- Show "Place On Hold" CTA (visible for active stages, gated on `isLegalManager`) that calls `PATCH /legal/cases/<side>/<pk>/` with `{ "status": "on_hold" }` as a temporary measure.
- Show "Resume from Hold" CTA when `status === 'on_hold'`, gated on `isLegalManager`.
- Once dedicated backend endpoints exist, switch to those (they will add audit logging and reason support).

---

### SIG-10 — Reschedule Meeting: No Dedicated Endpoint, No `reschedule_reason` Storage

**Frontend Gap:** A `RescheduleMeetingDialog` is planned but no dialog or fields are defined to collect new schedule data.

**Backend Verification:**
- `Meeting.STATUS_CHOICES` includes `('rescheduled', 'Rescheduled')` — status value exists.
- Searched `legal_meeting_views.py` for `MeetingRescheduleView`, `reschedule`, `RescheduleView`: **no dedicated reschedule endpoint found**.
- `Meeting` model fields: `scheduled_start`, `scheduled_end` — these can be PATCHed with new values.
- **No `reschedule_reason: TextField` field exists on the `Meeting` model.**
- Rescheduling currently requires: PATCH `{ "scheduled_start": ..., "scheduled_end": ..., "status": "rescheduled" }`.

**Assessment:** ⚠️ Rescheduling can be accomplished via PATCH (datetime update + status set). However, there is no dedicated endpoint and no storage for a `reschedule_reason`.

**Backend Work Needed (Optional Enhancement):**
- Add `reschedule_reason: TextField(blank=True)` to `Meeting` model if the SRS or Legal team requires a reason field.
- Add `POST /legal/meetings/<pk>/reschedule/` endpoint (pattern: validates new dates, sets status to `rescheduled`, stores reason, creates audit log) for consistency with other action endpoints.

**Frontend Action Now (Unblocked):**  
- Implement `RescheduleMeetingDialog` with fields: `start_datetime` (required), `end_datetime` (required), `reschedule_reason` (optional, text).
- On submit: call PATCH `/legal/meetings/<pk>/` with `{ "scheduled_start": ..., "scheduled_end": ..., "status": "rescheduled" }`.
- Omit `reschedule_reason` from the PATCH payload until the backend field is added.
- The frontend fix for SIG-10 is largely **not blocked** — dialog implementation can proceed now.

---

## Section 3 — ✅ Gaps Where Backend Fully Supports the Fix (Frontend-Only Changes)

For these gaps, **all required backend infrastructure exists**. Only frontend changes are needed.

---

### CRIT-03 — CASE_STAGES Enum: Backend Defines the Correct Values

**Backend Evidence:**
```python
# CaseDefendant.STATUS_CHOICES (legal_entities.py)
[('new', 'New'), ('under_dg_review', 'Under DG Review'), ('directive_issued', 'Directive Issued'),
 ('hearing_stage', 'Hearing Stage'), ('judgment_received', 'Judgment Received'),
 ('appeal_filed', 'Appeal Filed'), ('closed', 'Closed'), ('on_hold', 'On Hold')]
```
Same values confirmed on `CasePlaintiff.STATUS_CHOICES`.

**Frontend Fix:** Remove `settlement`, `judgment`, `appealed` from badge table. Rename `appealed` → `appeal_filed`. `CASE_STAGES` Phase 2.2 const already correct.

---

### CRIT-04 — `closure_pending`: Confirmed NOT a Backend Stage

**Backend Evidence:** `closure_pending` is absent from both `CaseDefendant.STATUS_CHOICES` and `CasePlaintiff.STATUS_CHOICES`. Not used in any view or model file. The case closure workflow uses `closed` as the final state directly.

**Frontend Fix:** Remove `closure_pending` from badge color table entirely. No backend stage for this value.

---

### SIG-01 — Case Archive/Unarchive: Full Backend Support

**Backend Evidence:**
- `CaseArchiveView` at `POST /legal/cases/defendant/<pk>/archive/` and `POST /legal/cases/plaintiff/<pk>/archive/` — **confirmed in `legal_case_views.py`**.
- `CaseUnarchiveView` at `POST /legal/cases/defendant/<pk>/unarchive/` and `POST /legal/cases/plaintiff/<pk>/unarchive/` — **confirmed**.
- `CaseDefendant.is_archived: BooleanField`, `archived_at: DateTimeField`, `archived_by: UUIDField` — **confirmed**.
- `CasePlaintiff.is_archived`, `archived_at`, `archived_by` — **confirmed** (with GAP-14 comment in model source).
- `GET /legal/cases/<side>/?include_archived=true` query param supported — **confirmed**.

**Frontend Fix:**
- Add "Archive" CTA to both case detail pages when `stage === 'closed'`, gated on `canCloseCases`.
- Add "Unarchive" CTA for archived cases, gated on `canCloseCases`.
- Add `is_archived: boolean`, `archived_at: string | null`, `archived_by: string | null` to `CaseDefendant` and `CasePlaintiff` TypeScript types.
- Add archived filter toggle to both case list pages.
- Update Phase 10.6 RBAC matrix with archive/unarchive actions.

---

### SIG-06 — Response Types: Backend Defines Complete Lists

**Backend Evidence (`legal_entities.py`):**
```python
# ResponseDefendant.RESPONSE_TYPE_CHOICES
[('preliminary_objections', 'Preliminary Objections'), ('counter_claim', 'Counter Claim'),
 ('reply_to_defence', 'Reply to Defence'), ('other', 'Other')]

# ResponsePlaintiff.RESPONSE_TYPE_CHOICES  
[('preliminary_objections', 'Preliminary Objections'), ('response_to_ruling', 'Response to Ruling'),
 ('response_to_orders', 'Response to Orders'), ('response_to_affidavits', 'Response to Affidavits'),
 ('counter_claim', 'Counter Claim'), ('initial_response', 'Initial Response'), ('other', 'Other')]
```

**Frontend Fix:** Update `useResponseTypes` in Phase 6 to exactly match these backend-defined lists. Do not use the truncated list currently in the plan. The two sides (defendant vs plaintiff) have different type sets — this is by design.

---

### SIG-07 — `recovered_amount` Field: Confirmed on FinancialPlaintiff

**Backend Evidence:**
```python
# FinancialPlaintiff (legal_entities.py ~line 1470)
recovered_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
```
`FinancialDefendant` does NOT have this field — the distinction is intentional and matches the SRS.

**Frontend Fix:** Add `recovered_amount: number` to `FinancialPlaintiff` TypeScript type. Add conditional Recovered Amount card in `CaseFinancialsSection` when `caseType === 'plaintiff'`.

---

### SIG-08 — Member Corporate Sync Fields: Stored by Backend

**Backend Evidence:**
```python
# Member model (legal_entities.py)
email = models.EmailField(blank=True)
department = models.CharField(max_length=255, blank=True)
```
These are populated on member creation from Corporate Service; they are not user-editable.

**Frontend Fix:** In `CreateMemberDialog`, show `email` and `department` as read-only preview fields populated when `user_id` is selected (SmartSelect resolves the user). Explicitly mark them as not form inputs. Show `department` column in member list.

---

### SIG-11 — Settlement/Judgment Approval Workflows: Full Backend Support

**Backend Evidence:**
- `POST /legal/settlements/defendant/<pk>/submit/` (`SettlementDefendantSubmitView`) — **confirmed**.
- `POST /legal/settlements/plaintiff/<pk>/submit/` (`SettlementPlaintiffSubmitView`) — **confirmed**.
- `POST /legal/judgments/defendant/<pk>/dg-decision/` (`JudgmentDefendantDGDecisionView`) — **confirmed**.
- `POST /legal/judgments/plaintiff/<pk>/dg-decision/` (`JudgmentPlaintiffDGDecisionView`) — **confirmed**.
- `VALID_DG_DECISIONS = ('accept', 'appeal')` — confirmed decision values.
- `JudgmentDefendant.DG_DECISION_CHOICES = [('accept', 'Accept'), ('appeal', 'Appeal')]` — **confirmed in model**.

**Frontend Fix:**
- `CaseSettlementSection`: Add "Submit for Approval" CTA when `settlement.status === 'proposed'` and `isLegalOfficer`. Call `submitSettlementForApproval(id)`.
- `CaseJudgmentSection`: Add "Submit for LM Review" CTA for Legal Officer. Add `DGJudgmentDecisionDialog` (fields: `dg_decision` radio / select — `accept|appeal`; `appeal_due_date` DatePicker shown only when `dg_decision === 'appeal'`).
- Add `EmbeddedWorkflowConsole` for both settlement and judgment sections.
- Update Phase 8.2 CTA tables and Phase 8.3 workflow classification table.

---

### MIN-01 — Quorum Not Met Reschedule: Backend `can_start` Enforces It

**Backend Evidence:**
```python
# Meeting.can_start property
def can_start(self) -> bool:
    now = timezone.now()
    return (
        self.quorum_met
        and self.status == 'quorum_ready'
        and self.scheduled_start <= now <= self.scheduled_end
    )
```
Backend will reject "Start Meeting" if quorum is not met. **Frontend change is UX improvement only.**

**Frontend Fix:** Add quorum warning banner on `LegalMeetingDetailPage` when `status === 'quorum_ready'` but `quorum_met === false` and the meeting's scheduled start has passed. Document the quorum-fail → reschedule flow as a note in Phase 8.2.

---

### MIN-02 — Minutes Approval Type: Controlled by WO Workflow Templates

**Backend Evidence:** `Minutes` model uses `WorkflowMixin`; approval type (majority vote vs sign-off) is configured in the `grc.legal_minutes_approval` workflow template in the Work Orchestration Service YAML. The `EmbeddedWorkflowConsole` renders whatever the template specifies.

**Frontend Fix:** Documentation-only. Add a note in `MinutesDetailPage` spec: approval mechanism is driven by workflow template configuration; no frontend-specific code needed.

---

### MIN-04 — Secretary Multi-Body Assignment: Supported by `secretary_user_ids`

**Backend Evidence:**
```python
# GoverningBody model
secretary_user_ids = models.JSONField(default=list, blank=True)
```
Array allows multiple secretaries per body and a user can appear in multiple bodies' arrays.

**Frontend Fix:** In `MembersPage`, add a column/view showing all governing bodies where each secretary is assigned. Confirm `GoverningBodyDetailPage` "Secretaries" card resolves UUIDs via `<UserDisplay />`. Add note that secretary assignment is via `UpdateGoverningBodyDialog`.

---

### MIN-05 — Public Register Portal Note: Documentation Only

**Backend Evidence:** `PublicDecision` model has `status`, `published_date` fields. Publish workflow managed by `PublicDecisionWorkflowView`. All fields needed for future CRM integration are stored.

**Frontend Fix:** Add note in `PublicDecisionDetailPage` and `PublicRegisterPage` specs: published decisions are intended for the future public portal / FCC CRM integration.

---

### MIN-06 — Conflict of Interest Scoping: Model Enforces Meeting Scope

**Backend Evidence:**
```python
# ConflictDeclaration model
agenda_item = models.ForeignKey(MeetingAgenda, on_delete=models.CASCADE, ...)
```
Declarations are linked to `MeetingAgenda`, which is linked to `Meeting`. Queries must use `agenda.meeting_id === currentMeeting.id` to scope correctly.

**Frontend Fix:** In `MeetingAgendaSection` / A.6.4 conflict display, explicitly filter conflicts by `agenda_item.meeting_id === currentMeeting.id`. Add this as a development note.

---

### MIN-07 — `canManageMembers`: Wrong Variable Name in A.15.1

**Backend Evidence:** `CanManageLegalGoverningBody` is the correct permission class in `permissions_jwt.py`. Permission code: `grc:legal_governing_body:manage`. No `CanManageMembers` class exists.

**Frontend Fix:** Replace `canManageMembers` → `canManageGoverningBody` in Addendum A.15.1 and Phase 10.6 RBAC matrix `MembersPage` row.

---

### MIN-08 — Task Reminder Schedule: Backend Celery Beat Handles It

**Backend Evidence:** `TaskLitigation` overdue transitions handled by Celery Beat scheduled task. Reminder notifications published via Kafka to WO service at 7/2/1 days before due date.

**Frontend Fix:** Add documentation note in `CaseTasksSection` and Phase 11: task reminders are delivered via the notification engine (SIG-04); due date badges on the task list derived from `task.due_date` client-side.

---

### MIN-09 — Member.position vs MeetingParticipant.role: Properly Separated in Backend

**Backend Evidence:**
```python
# Member.POSITION_CHOICES
[('member', 'Member'), ('secretary', 'Secretary'), ('chairman', 'Chairman')]

# MeetingParticipant.ROLE_CHOICES  
[('member', 'Member'), ('invitee', 'Invitee'), ('secretary', 'Secretary')]
```
Both are separate model choices. Note: `secretary` appears in both but with different semantics.

**Frontend Fix:** Add TypeScript comments distinguishing the two enums. Add `MEMBER_POSITIONS` and `PARTICIPANT_ROLES` as separate const maps in Phase 2.2.

---

### MIN-10 — Approval Chain `actor_name` vs Audit Log: Different Structures

**Backend Evidence:**
- `FilingDefendant.approval_chain: JSONField` — stores audit/approval chain entries at approval time; each entry may include `actor_name` (stored string, not a FK).
- `LegalAuditLog` has `actor_id: UUIDField` — no `actor_name` stored (must be resolved via `<UserDisplay />`).

**Frontend Fix:** Document the two patterns clearly. In `ApprovalChainDisplay` component: render `entry.actor_name` directly. In `LegalActivityLog` component: always render `<UserDisplay userId={entry.actor_id} />`. Do NOT use `UserDisplay` in approval chain display.

---

### MIN-11 — `DG_REVIEW_STATUS` Values: Field Exists in Both Case Models

**Backend Evidence:**
```python
# CaseDefendant
dg_review_status = models.CharField(max_length=30, blank=True, default='pending',
    help_text="Pending/Reviewed/Directive Issued")
```
Same field on `CasePlaintiff`. Values: `pending`, `reviewed`, `directive_issued` (from docstring/usage).

**Frontend Fix:** Add `DG_REVIEW_STATUSES = ['pending', 'reviewed', 'directive_issued']` to Phase 2.2 status enum maps. Add `dg_review_status: string` to both case TypeScript types.

---

### MIN-12 — Resolution Detail Page: Data Available

**Backend Evidence:** `Resolution` model fully defined: `resolution_text`, `date_adopted`, `status`, `responsible_person_id`, `effective_date`, `attachments`. `GET /legal/resolutions/<pk>/` or sub-resource endpoint accessible.

**Frontend Fix:** Add `ResolutionDetailPage` or a detail drawer/panel from `ResolutionsPage` showing full `resolution_text` and all resolution fields. This is a pure frontend addition.

---

### MIN-13 — PlaintiffAdvocate Column: Field Available

**Backend Evidence:** `CaseDefendant.plaintiff_advocate: CharField(max_length=255, blank=True)` confirmed in model.

**Frontend Fix:** Add `plaintiff_advocate` as a column to `FCCSuedCasesPage` list spec (with A.17.4 columns already including Claim Amount, Risk Level, Next Hearing). Clarify that `CaseDefendant.status` and `CaseDefendant.stage` refer to the same `status` field (single field serves both roles in the model).

---

### MIN-14 — Activity Log Status Transitions: Metadata Contains the Data

**Backend Evidence:**
- `LegalActivityLogView` returns raw `LegalAuditLog` objects including `metadata: JSONField`.
- When `action === 'status_changed'`, `metadata` is populated with `{ "from_status": "...", "to_status": "..." }` by `log_workflow_action()` calls throughout the views (confirmed in multiple `log_workflow_action` call sites).
- The data is already there — frontend just isn't reading it.

**Frontend Fix:**
```tsx
const getActionDetail = (entry: LegalAuditLog) => {
  if (entry.action === 'status_changed' && entry.metadata?.from_status) {
    return `${entry.action}: ${entry.metadata.from_status} → ${entry.metadata.to_status}`;
  }
  return `${entry.action}${entry.comment ? ` — ${entry.comment}` : ''}`;
};
```
Add metadata contract documentation to Phase 3 (API Integration). Each action type's `metadata` keys should be specified as a contract so frontend knows what to read.

---

### MIN-15 — Start Meeting Time Guard: Backend `can_start` Enforces the Rule

**Backend Evidence:**
```python
@property
def can_start(self) -> bool:
    now = timezone.now()
    return (
        self.quorum_met
        and self.status == 'quorum_ready'
        and self.scheduled_start <= now <= self.scheduled_end
    )
```
Backend will return an error if Secretary attempts to start a meeting outside the scheduled window. **Frontend guard is UX improvement to prevent requests that will fail.**

**Frontend Fix:** Add client-side time check to "Start Meeting" guard:
```tsx
const now = new Date();
const canStartMeeting = 
  meeting.status === 'quorum_ready' &&
  meeting.quorum_met &&
  isSecretary &&
  now >= new Date(meeting.scheduled_start);
```
Show informational alert when quorum is met but scheduled start hasn't arrived yet.

---

### MIN-16 — DirectiveDetailPage Assigned-User Check Pattern

**Backend Evidence:** `MeetingDirective.assigned_user_id: UUIDField(null=True, blank=True)` — field exists. Access control (only assigned user can close) is enforced in the directive update views.

**Frontend Fix:** Add explicit identity check pattern to Phase 8.2 `DirectiveDetailPage`:
```tsx
const isAssignedUser = directive.assigned_user_id === currentUser?.id;
```
CTAs ("Mark In Progress", "Close Directive") should be shown only when `isAssignedUser === true`. "Fully Close" remains Secretary-only. Reference this pattern from Phase 10.3 (Action Restrictions).

---

### MIN-17 — `CreateResolutionDialog`: Backend Confirms Auto-Creation via OneToOne

**Backend Evidence:**
```python
# Resolution model
agenda_item = models.OneToOneField(MeetingAgenda, on_delete=models.CASCADE, related_name='resolution')
```
The OneToOneField enforces that each `MeetingAgenda` item has exactly one `Resolution`. This database constraint confirms the auto-creation pattern (a resolution is created for each agenda item outcome, not manually).

**Frontend Fix:** Remove `CreateResolutionDialog` from Phase 9.2 dialog inventory. Remove the corresponding `POST legal/minutes/{pk}/resolutions/` endpoint reference from Phase 9.6. If resolution text finalization is needed, use an `EditResolutionDialog` (PATCH existing auto-created resolution). Add to Phase 15 checklist: "Verify resolutions are auto-created from agenda outcomes; no manual creation path exists."

---

## Section 4 — 🔵 Backend-Implemented Feature Outside SRS Scope

### OVER-01 — Legal Notices: Full Backend Implementation Exists

**Backend Evidence:**
- `LegalNoticeListCreateView` (GET/POST) at `/legal/notices/` — **confirmed in `legal_notice_views.py`**.
- `LegalNoticeDetailView` (GET/PUT/PATCH/DELETE) at `/legal/notices/<pk>/` — **confirmed**.
- `CanViewLegalNotice` and `CanManageLegalNotice` permission classes — **confirmed in `permissions_jwt.py`**.
- `grc:legal_notice:view` and `grc:legal_notice:manage` permission codes exist in `grc-service.json`.

**Assessment:** 🔵 The Legal Notices feature is fully implemented in the backend but has **no specification in the SRS** (`Legal_Service.md`). This feature originated from backend design decisions or a separate requirements document not available here.

**Action Required:**
- **Do NOT implement Legal Notices in this frontend implementation sprint.** The SRS is the authoritative scope document.
- The `canViewNotices` and `canManageNotices` booleans in `useLegalPermissions.ts` may remain (they map to existing permission codes) but should not be connected to any UI components in this phase.
- Remove `CreateLegalNoticeDialog` from Phase 9.2 scope for this sprint; move to a "Future / Out of Scope" section.
- If Legal Notices are a confirmed feature from another specification document, obtain that specification before including in frontend scope.

---

## Section 5 — Required Backend Changes Summary

The following **6 backend changes are blockers** — frontend gap fixes depend on them. They should be prioritized by the backend team before the frontend implementations for their respective gaps are scheduled.

| Priority | Change | Affected Gap | Backend File(s) |
|----------|--------|-------------|-----------------|
| 🔴 HIGH | Allow any-user access to POST `/legal/submissions/` | CRIT-01 | `legal_governing_body_views.py` + `permissions_jwt.py` |
| 🔴 HIGH | Add `CanRegistryOfficer` / `grc:legal_case:register` permission code | CRIT-02 | `permissions_jwt.py` + `grc-service.json` + IAM config |
| 🔴 HIGH | Allow Department User access to POST `/legal/cases/plaintiff/` (simplified intake) | CRIT-05 | `legal_case_views.py` + `permissions_jwt.py` |
| 🟠 MEDIUM | Add `requires_dg_approval_for_closure: BooleanField` to `LitigationDirective` model | SIG-03 | `legal_entities.py` + migration + views |
| 🟡 LOW | Add `auto_created: BooleanField` to `TaskLitigation` model | MIN-03 | `legal_entities.py` + migration |
| 🟡 LOW | Add `meeting_number_prefix` + `meeting_number_format` to `GoverningBody` model | MIN-18 | `legal_entities.py` + migration + meeting creation logic |

---

## Section 6 — Backend Implementation Order

Backend work must be completed in dependency order before the frontend phases that depend on it can begin. Changes are grouped by what they touch: **view-layer only** (no migration), **model additions** (migration required), **new endpoints**, and **cross-service coordination**.

> **Rule:** Complete each backend phase and redeploy `grc-service` before beginning the frontend phase that depends on it.

---

### Backend Phase 1 — View-Layer Permission Changes (no migrations, no new models)

These are the fastest fixes — only permission class references or queryset logic in existing view files. No database migration required.

| Order | Gap | File | Change |
|-------|-----|------|--------|
| B1-1 | CRIT-01 | `legal_governing_body_views.py` | Change `SubmissionForDeterminationListCreateView.post()` to use `IsAuthenticated` instead of `CanManageLegalGoverningBody`. Move `CanManageLegalGoverningBody` guard to `PUT/PATCH/DELETE` only. |
| B1-2 | CRIT-05 | `legal_case_views.py` | In `CasePlaintiffListCreateView.post()`: if `request.data.get('registration_type') == 'simplified'`, require only `IsAuthenticated`. Otherwise keep `CanManageLegalCase`. |
| B1-3 | SIG-05 | `legal_case_views.py` | In `CaseDefendantListCreateView.get()` and `CasePlaintiffListCreateView.get()`: if user has `CanViewLegalCase` but NOT `CanManageLegalCase`, filter queryset to `assigned_legal_officer_ids__contains=str(request.user_id)`. |

**Unblocks frontend:** CRIT-01 fix, CRIT-05 fix, SIG-05 My-Cases filtering.

**Deployment:** Restart `grc-service` container. No migration needed.

---

### Backend Phase 2 — New Permission Codes (requires IAM coordination)

These require adding permission classes to `grc-service` AND registering the codes in `grc-service.json` AND coordinating with the IAM service to assign the new codes to the correct roles.

| Order | Gap | File | Change |
|-------|-----|------|--------|
| B2-1 | CRIT-02 | `permissions_jwt.py` + `grc-service.json` | Decide (with Legal team) whether Registry Officer = `CanManageLegalCase` scope or separate. If separate: add `CanRegistryOfficer` class checking `grc:legal_case:register` code. Register code in `grc-service.json`. Coordinate IAM role assignment. |

**Unblocks frontend:** CRIT-02 RBAC matrix correction (Phase C-23 in frontend sequence).

**Deployment:** Restart `grc-service`. IAM service role-permission mapping must also be updated.

---

### Backend Phase 3 — Model Field Additions (migrations required)

Each item requires a new model field + `makemigrations` + `migrate`. Group these into a **single migration batch** where possible (one `apps/core/migrations/XXXX_legal_phase3.py`) to minimise migration count.

| Order | Gap | Model | Field(s) to Add |
|-------|-----|-------|----------------|
| B3-1 | SIG-03 | `LitigationDirective` | `requires_dg_approval_for_closure = BooleanField(default=False)` + add `'pending_dg_approval'` to `STATUS_CHOICES`. |
| B3-2 | SIG-09 | `CaseDefendant`, `CasePlaintiff` | `hold_reason = TextField(blank=True)` (optional but needed for dedicated hold/resume endpoints to be useful). |
| B3-3 | SIG-10 | `Meeting` | `reschedule_reason = TextField(blank=True)`. |
| B3-4 | MIN-03 | `TaskLitigation` | `auto_created = BooleanField(default=False)`. Set `auto_created=True` in all programmatic task-creation paths (e.g., appeal deadline task, filing-review task). |
| B3-5 | MIN-18 | `GoverningBody` | `meeting_number_prefix = CharField(max_length=20, blank=True)` + `meeting_number_format = CharField(max_length=20, choices=[('sequential','Sequential'),('financial_year','Financial Year')], default='sequential')`. |

**Recommended command sequence (in `grc-service` container):**
```bash
python manage.py makemigrations core --name legal_phase3_model_additions
python manage.py migrate
```

**Unblocks frontend:** SIG-03 conditional closure flow, SIG-09 hold reason field, SIG-10 RescheduleMeetingDialog reason storage, MIN-03 auto_created task badge, MIN-18 GoverningBody config fields.

---

### Backend Phase 4 — New Action Endpoints (depends on Phase 3 for SIG-03 and SIG-09)

Add named action endpoints following the existing `archive/unarchive` pattern. Each endpoint: validates permissions, validates state transition, updates the model, writes an audit log entry.

| Order | Gap | New Endpoint | View File | Depends On |
|-------|-----|-------------|-----------|-----------|
| B4-1 | SIG-09 | `POST /legal/cases/defendant/<pk>/hold/` + `POST /legal/cases/defendant/<pk>/resume/` | `legal_case_views.py` | B3-2 (`hold_reason` field) |
| B4-2 | SIG-09 | `POST /legal/cases/plaintiff/<pk>/hold/` + `POST /legal/cases/plaintiff/<pk>/resume/` | `legal_case_views.py` | B3-2 |
| B4-3 | SIG-03 | `POST /legal/directives/litigation/<pk>/submit-for-dg-approval/` + `POST /legal/directives/litigation/<pk>/dg-decision/` | `legal_directive_views.py` | B3-1 (`requires_dg_approval_for_closure`, `pending_dg_approval` status) |
| B4-4 | SIG-02 | `GET /legal/meetings/<pk>/directives/` (invitee-scoped sub-resource) | `legal_meeting_views.py` | No prior backend phase (data model already exists) |
| B4-5 | MIN-18 | Update `MeetingListCreateView.post()` meeting-number generation to read `governing_body.meeting_number_prefix` and `meeting_number_format` instead of the hardcoded `MTG-{YYYYMM}-{NNN}` pattern | `legal_meeting_views.py` | B3-5 |

**Permission guards for new endpoints:**
- `hold/` + `resume/`: `CanManageLegalCase` (Legal Manager role)
- `submit-for-dg-approval/`: `CanManageLegalDirective`
- `dg-decision/`: requires DG-level permission (add `CanApproveDirectiveClosure` to `permissions_jwt.py`, or reuse `CanManageLegalCase` + DG-role check)
- `GET /meetings/<pk>/directives/`: `IsAuthenticated` + participant membership check (no permission code gate)

**Unblocks frontend:** SIG-09 dedicated hold/resume CTAs, SIG-03 conditional closure flow, SIG-02 invitee directive access, MIN-18 correct meeting numbers.

---

### Backend Phase 5 — Cross-Service Coordination (WO service + IAM service)

These items are outside the `grc-service` codebase and require coordination with other service owners.

| Order | Gap | Service | Action |
|-------|-----|---------|--------|
| B5-1 | SIG-04 | Work Orchestration Service | Confirm `GET /notifications/?user_id=<UUID>&unread=true` endpoint exists (or equivalent). If not, add it to the WO service. GRC service already publishes events via Kafka — no GRC changes needed. |
| B5-2 | CRIT-02 | IAM Service | Register new `grc:legal_case:register` permission code (or confirm `CanManageLegalCase` covers Registry Officer). Assign to Registry Officer role in IAM role-permission config. |

**Unblocks frontend:** SIG-04 notification bell/inbox, CRIT-02 Registry Officer RBAC matrix.

---

### Backend Phase Summary — Dependency Map

```
Backend Phase 1 (view-layer) ─────────────────────► Frontend Phase A (immediately unblocked)
      │
      ├── B1-1 (CRIT-01) ──────────────────────────► Frontend: Submissions create button open to all
      ├── B1-2 (CRIT-05) ──────────────────────────► Frontend: Breach intake CTA for Dept Users
      └── B1-3 (SIG-05) ───────────────────────────► Frontend: My Cases server-side filter

Backend Phase 2 (permission codes) ───────────────► Frontend Phase C-23 (Registry Officer RBAC)

Backend Phase 3 (migrations) ─────────────────────►
      ├── B3-1 (SIG-03) ──► Backend Phase 4 B4-3 ──► Frontend: Directive DG approval UI
      ├── B3-2 (SIG-09) ──► Backend Phase 4 B4-1/2 ► Frontend: Dedicated hold/resume CTAs
      ├── B3-3 (SIG-10) ───────────────────────────► Frontend: reschedule_reason field in dialog
      ├── B3-4 (MIN-03) ───────────────────────────► Frontend: auto_created "System" badge on tasks
      └── B3-5 (MIN-18) ──► Backend Phase 4 B4-5 ──► Frontend: GoverningBody prefix/format fields

Backend Phase 4 (new endpoints) ──────────────────►
      ├── B4-4 (SIG-02) ───────────────────────────► Frontend: Invitee directive read-only view
      └── B4-5 (MIN-18) ───────────────────────────► Frontend: Correct meeting numbers generated

Backend Phase 5 (cross-service) ──────────────────►
      ├── B5-1 (SIG-04) ───────────────────────────► Frontend: Notification bell/inbox
      └── B5-2 (CRIT-02) ─────────────────────────► Frontend: Registry Officer RBAC (alt path)
```

---

## Section 7 — Recommended Frontend Implementation Sequence

> **✅ STATUS UPDATE (March 2026):** Backend Phases 1–5 are **fully implemented and deployed**. All Phase A, B, and C items are now unblocked. See `Legal_Module_Frontend_Implementation_Plan.md` Addendum A.18 for complete integration specs.

Based on backend readiness:

### Phase A — Can implement immediately (no backend changes needed)

These gap fixes are **unblocked** right now:

1. **CRIT-03** — Fix CASE_STAGES badge table (remove `settlement`, `judgment`, `appealed`)
2. **CRIT-04** — Remove `closure_pending` from badge colors
3. **SIG-01** — Add Archive/Unarchive CTAs + archived case filter (full backend support exists)
4. **SIG-06** — Update response types dropdown to exact backend values
5. **SIG-07** — Add `recovered_amount` card to plaintiff financials section
6. **SIG-08** — Update `CreateMemberDialog` for read-only Corporate Service fields
7. **SIG-10** — Add `RescheduleMeetingDialog` ~~(PATCH-based; no reschedule_reason storage yet)~~ ✅ `reschedule_reason` field now available (B3-3)
8. **SIG-11** — Add Settlement/Judgment approval CTAs, `DGJudgmentDecisionDialog`, EWC placement
9. **SIG-09** ~~(partial)~~ ✅ **(full)** — Add "Place On Hold" / "Resume from Hold" CTAs ~~(via PATCH; dedicated endpoints pending)~~ → dedicated `hold/` and `resume/` endpoints available (B4-1/2)
10. **MIN-07** — Fix `canManageMembers` → `canManageGoverningBody`
11. **MIN-09** — Add separate const maps for member positions vs participant roles
12. **MIN-11** — Add `DG_REVIEW_STATUSES` to Phase 2.2
13. **MIN-14** — Update activity log to read `metadata.from_status`/`to_status`
14. **MIN-15** — Add time-window guard to "Start Meeting" CTA
15. **MIN-16** — Document and implement assigned-user identity check pattern
16. **MIN-17** — Remove `CreateResolutionDialog`; use `EditResolutionDialog` for resolution text

### Phase B — ~~Implement after backend confirmation/investigation~~ ✅ ALL UNBLOCKED

> **All backend work complete.** Implement alongside Phase A items.

17. **CRIT-01** — Fix submission permission ✅ Backend B1-1 done (`SubmissionForDeterminationListCreateView.post()` now uses `IsAuthenticated`)
18. **CRIT-05** — Fix breach report intake button ✅ Backend B1-2 done (`registration_type == 'simplified'` skips permission check)
19. **SIG-02** — Implement invitee directive access ✅ Backend B4-4 done (`GET /legal/meetings/{id}/directives/` with participant membership check)
20. **SIG-04** — Implement notification bell/inbox ✅ WO API confirmed (B5-1: `GET /api/v1/wo/notifications/` with `?unread=true`)
21. **SIG-05** — My Cases row-level filtering ✅ Backend B1-3 done (`assigned_legal_officer_ids__contains` auto-filter for view-only users)
22. **SIG-09** (full) — Use dedicated hold/resume endpoints ✅ Backend B4-1/2 done (`POST /legal/cases/<side>/<pk>/hold/` and `/resume/`)

### Phase C — ~~Blocked on confirmed backend model additions~~ ✅ ALL UNBLOCKED

> **All backend model additions + migrations + endpoints complete.** Implement alongside Phase A items.

23. **CRIT-02** — Registry Officer RBAC ✅ Backend B2-1 done (`grc:legal_case:register` + `CanRegisterLegalCase` + IAM role configured)
24. **SIG-03** — Configurable DG approval for directive closure ✅ Backend B3-1 + B4-3 done (`requires_dg_approval_for_closure` field + `pending_dg_approval` status + `submit-for-dg-approval/` and `dg-decision/` endpoints)
25. **MIN-03** — Auto-created task badge ✅ Backend B3-4 done (`auto_created = BooleanField` on `TaskLitigation`)
26. **MIN-18** — Meeting number prefix config ✅ Backend B3-5 + B4-5 done (`meeting_number_prefix` + `meeting_number_format` fields + `_generate_meeting_number()` logic)

---

## Appendix A — Backend Files Audited

| File | Purpose | Verification Status |
|------|---------|---------------------|
| `apps/api/views/legal_case_views.py` | CaseDefendant/Plaintiff CRUD, archive/unarchive, workflow, report | ✅ Fully read |
| `apps/api/views/legal_governing_body_views.py` | GoverningBody, Member, SubmissionForDetermination | ✅ Fully read |
| `apps/api/views/legal_meeting_views.py` | Meeting CRUD, workflow, agenda, participants | ✅ Fully read |
| `apps/api/views/legal_settlement_views.py` | Settlement + Financial views | ✅ Fully read |
| `apps/api/views/legal_judgment_views.py` | Judgment + DG Decision + Appeal | ✅ Fully read |
| `apps/api/views/legal_directive_views.py` | Meeting/Litigation directives + Tasks | ✅ Grepped (on_hold/invitee checks) |
| `apps/api/views/legal_activity_log_views.py` | Activity log | ✅ Fully read |
| `apps/api/views/legal_notice_views.py` | Legal notices | ✅ Fully read |
| `apps/api/views/legal_public_register_views.py` | Public decisions | ✅ Identified |
| `apps/api/permissions_jwt.py` | All RBAC permission classes | ✅ Fully read |
| `apps/core/models/legal_entities.py` | All legal models | ✅ Fully read (all models) |
| `shared/constants/event_types.py` | Kafka event type constants | ✅ Grepped |

---

## Appendix B — Key Backend Model Fields Quick Reference

### CaseDefendant STATUS_CHOICES (exact backend values)
```
new | under_dg_review | directive_issued | hearing_stage | judgment_received | appeal_filed | closed | on_hold
```

### CasePlaintiff STATUS_CHOICES (exact backend values, same as defendant)
```
new | under_dg_review | directive_issued | hearing_stage | judgment_received | appeal_filed | closed | on_hold
```

### Meeting STATUS_CHOICES
```
draft | registered | invitations_sent | agenda_shared | quorum_ready | ongoing | postponed | closed | cancelled | rescheduled
```

### SettlementDefendant / SettlementPlaintiff STATUS_CHOICES
```
proposed | agreed | rejected
```

### JudgmentDefendant / JudgmentPlaintiff DG_DECISION_CHOICES
```
accept | appeal
```

### FilingDefendant STATUS_CHOICES
```
draft | under_review_lm | approved_lm | under_review_dg | approved | filed
```

### LitigationDirective STATUS_CHOICES
```
open | in_progress | closed
```

### TaskLitigation STATUS_CHOICES
```
open | in_progress | overdue | closed
```

### ResponseDefendant RESPONSE_TYPE_CHOICES
```
preliminary_objections | counter_claim | reply_to_defence | other
```

### ResponsePlaintiff RESPONSE_TYPE_CHOICES
```
preliminary_objections | response_to_ruling | response_to_orders | response_to_affidavits | counter_claim | initial_response | other
```

### SubmissionForDetermination STATUS_CHOICES
```
submitted | under_review | determined | withdrawn
```

### Minutes STATUS_CHOICES
```
draft | pending_approval | approved
```

### MeetingDirective STATUS_CHOICES
```
open | in_progress | overdue | closed | fully_closed
```

### Member POSITION_CHOICES (separate from MeetingParticipant.role)
```
member | secretary | chairman
```

### MeetingParticipant ROLE_CHOICES (distinct from Member.position)
```
member | invitee | secretary
```

