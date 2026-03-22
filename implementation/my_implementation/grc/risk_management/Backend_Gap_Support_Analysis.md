# Backend Gap Support Analysis
# Risk Management & Quality Assurance — Frontend Gaps vs Backend Reality

**Source Gaps File:** `SRS_vs_Frontend_Plan_Gap_Analysis.md` (29 identified gaps)
**Backend Entry Point:** `grc-service/apps/api/views/` + `apps/core/models/risk_entities.py`
**Backend URL Registry:** `grc-service/apps/api/urls/risk.py`
**Analysis Date:** March 2026

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Backend FULLY supports — existing endpoint/field/model is sufficient |
| ⚠️ | Backend PARTIALLY supports — data exists but endpoint or field is missing |
| ❌ | Backend does NOT support — model/endpoint changes required |

---

## Master Summary Table

| Gap # | Title | Backend Support | Notes |
|-------|-------|----------------|-------|
| 1 | Risk Dashboard Page | ✅ FULL | `GET /risk/dashboard/` live |
| 2 | Comparative Analysis View | ✅ FULL | `GET /risk/dashboard/comparative-analysis/` live |
| 3 | QA Exam Tracking (75% threshold + re-sit) | ⚠️ PARTIAL | Auditor fields OK; attendee record missing exam fields |
| 4 | NC Dispute / Finding Amendment | ❌ NONE | Status enum missing; no dispute endpoint |
| 5 | NC Monthly Monitoring / Overdue indicator | ⚠️ PARTIAL | `due_date` field exists; no monthly summary endpoint |
| 6 | Risk Meeting Type Enum & DRR Linkage | ⚠️ PARTIAL | Some types present; DRR linkage FK absent |
| 7 | RTAP "Send Reminder to RCs" | ❌ NONE | No action endpoint exists |
| 8 | IRR Workshop Notification Actions | ❌ NONE | No notify endpoints; missing workshop fields |
| 9 | One-Active-RC-Per-Unit Rule | ✅ FULL | DB unique constraint → 409 enforced |
| 10 | Nominee Qualifications / Experience | ⚠️ PARTIAL | RC has fields; QualityAuditor does not |
| 11 | QMS Plan — NDA Signing | ✅ FULL | `QMSAuditPlan.nda_signed/nda_signed_date/nda_document_id` live |
| 12 | MRM Directives Tracking | ❌ NONE | QMSAuditReport status + field model is too minimal |
| 13 | QA Appointment Pre-condition Gate | ⚠️ PARTIAL | Data available; no backend enforcement |
| 14 | RC / QA Dispatch Tracking | ✅ FULL | `dispatched`, `dispatch_date`, `dispatch_reference` on both models |
| 15 | RAS Rework / Return Cycle | ❌ NONE | `RiskAssessmentSheet` has NO `status` field at all |
| 16 | 7-day Committee Submission Warning | ✅ FULL | `committee_meeting_date` on IRR, RTAP, QPR |
| 17 | QPR Submission to IAGO | ✅ FULL | `iago_submitted`, `iago_submission_date`, `iago_reference` on QPR |
| 18 | Role Assignment UI Acknowledgment | ✅ FULL | Backend signals fire; frontend needs toast only |
| 19 | QMS Audit Meeting Types (pre_audit/entry/exit) | ✅ FULL | `QMSAuditMeeting.MEETING_TYPE_CHOICES` exact match |
| 20 | Export / Print for Risk Reports | ❌ NONE | No export endpoints (P4 — low priority) |
| 21 | RC / QA Nomination Request Flow | ❌ NONE | No nomination request entity or endpoints |
| 22 | RTAP Item — RMO Return-for-Rework | ❌ NONE | `RTAPItem` status choices missing; no rework fields |
| 23 | QA Training — RMQAM Approval Step | ⚠️ PARTIAL | Approval fields exist; no dedicated action endpoints |
| 24 | Post-Approval IRR/RTAP Distribution | ❌ NONE | No distribute endpoints; no `distributed_at` fields |
| 25 | QMS Audit Report — RMQAU Return-for-Revision | ❌ NONE | QMSReport status model ends at `finalised` |
| 26 | QMS Audit Report — Audit Committee + Commission | ❌ NONE | No status values for committee/commission stages |
| 27 | Risk Meeting Minutes + Attendance | ✅ FULL | `RiskMeeting.minutes`, `outcomes` + `/meetings/:id/attendance/` live |
| 28 | RAS Status Transition Actions | ❌ NONE | `RiskAssessmentSheet` has NO `status` field at all |
| 29 | NC Finding Type (NC vs Improvement) | ⚠️ PARTIAL | `nc_type` FK to lookup table covers this; no enum field |

---

## Section 1 — Backend FULLY Supports (10 Gaps)

These 10 gaps require only frontend work. All data, endpoints, and model fields are live.

---

### Gap 1 — Risk Dashboard Page ✅

**Backend endpoint:** `GET /risk/dashboard/`
**View class:** `RiskDashboardView` in `apps/api/views/risk_dashboard_views.py`
**Permission:** `CanViewRiskDashboard`

**What the backend returns:**
```json
{
  "assessments": { "total": 42 },
  "dept_registers": { "draft": 5, "submitted": 12, "approved": 20 },
  "inst_registers": { "draft": 1, "approved": 1 },
  "rtaps": { "draft": 1, "approved": 1 },
  "non_conformances": { "raised": 8, "in_progress": 3, "closed": 15 }
}
```
Supports optional `?fiscal_year=<id>` filter.

**Frontend work required:** Implement `RiskDashboardPage.tsx` + route + sidebar item using `useRiskDashboard` hook (already planned in §3.2 but page component missing).

---

### Gap 2 — Comparative Analysis View ✅

**Backend endpoint:** `GET /risk/dashboard/comparative-analysis/`
**View class:** `RiskDashboardComparativeAnalysisView`

**Query params:** `?compare_by=department|fiscal_year` + optional `?fiscal_year=<id>`

**What it returns:** Array of dept-level or FY-level counts:
```json
[{ "org_unit_id": "...", "total": 10, "draft": 2, "submitted": 4, "approved": 4 }]
```

**Frontend work required:** Implement a bar/line chart component in `RiskDashboardPage` consuming `fetchRiskDashboardComparativeAnalysis()`.

---

### Gap 9 — One-Active-RC-Per-Unit Rule ✅

**Backend enforcement:** Database-level `UniqueConstraint` on `RiskChampion`:
```python
models.UniqueConstraint(
    fields=['org_unit_id', 'org_unit_type'],
    condition=models.Q(is_active=True),
    name='unique_active_rc_per_org_unit',
)
```
Returns **HTTP 400/409 conflict** when a second active RC is created for the same unit.

**Frontend work required:**
- Handle 409 conflict response in `CreateRiskChampionDialog` with specific error message.
- Optional: pre-check using existing data before submitting (client-side guard).

---

### Gap 11 — QMS Plan NDA Signing ✅

**Backend fields on `QMSAuditPlan`:** (serialized)
- `nda_signed: boolean`
- `nda_signed_date: string | null`
- `nda_document_id: UUID | null`

**Note on architecture:** The NDA fields live on `QMSAuditPlan` (plan level), NOT on `QMSAuditMeeting` (entry meeting level). The gap analysis proposed adding NDA fields to `QMSAuditMeeting`, but the backend already models it at plan level. Frontend should read from `plan.nda_signed` rather than `meeting.non_disclosure_signed`.

**Additional `QMSAuditMeeting` fields available:** `timetable_agreed`, `timetable_revised` — these cover the timetable agreement tracking at entry meeting level.

**Frontend work required:** Implement `QMSAuditMeetingsSection` using existing `/qms-plans/:id/audit-meetings/` endpoint. Map NDA display from `plan.nda_signed` + `plan.nda_document_id`.

---

### Gap 14 — RC / QA Dispatch Tracking ✅

**Backend fields on `RiskChampionAppointment`:**
- `dispatched: boolean`
- `dispatch_date: date | null`
- `dispatch_reference: string`
- `recipient_confirmed: boolean`
- `recipient_confirmed_date: date | null`

**Backend fields on `QualityAuditorAppointment`:** Same structure (exact mirror).

**Update via:** `PATCH /risk/champions/appointments/:id/` or `PATCH /risk/quality-auditors/appointments/:id/`

**Frontend work required:** Add "Mark as Dispatched" button in appointment detail sections; PATCH to set `dispatched=true` + `dispatch_date` + optional `dispatch_reference`.

---

### Gap 16 — 7-day Committee Submission Warning ✅

**Backend fields:**
| Model | Field | Serialized |
|-------|-------|-----------|
| `InstitutionalRiskRegister` | `committee_meeting_date` | ✅ |
| `RiskTreatmentActionPlan` | `committee_meeting_date` | ✅ |
| `QuarterlyPerformanceReport` | `committee_meeting_date` | ✅ |

All are nullable `DateField`; included in serializers with `required: False`.

**Frontend work required:** Pure frontend warning logic — check `daysUntil < 7` before submitting to committee workflow stage; show `toast.warning()` (non-blocking).

---

### Gap 17 — QPR Submission to IAGO ✅

**Backend fields on `QuarterlyPerformanceReport`:**
- `iago_submitted: boolean`
- `iago_submission_date: date | null`
- `iago_reference: string`

All serialized + writable via PATCH.

**Frontend work required:** Add "Submit to IAGO" button on `QPRDetailPage` — visible after committee review. PATCHes `iago_submitted=true` + `iago_submission_date`. No separate status value needed (backend treats this as a parallel track to committee submission).

---

### Gap 18 — Role Assignment UI Acknowledgment ✅

**Backend behavior:** Signal handler fires automatically when `RiskChampionAppointment` or `QualityAuditorAppointment` workflow reaches terminal `approved` state — role is assigned in the IAM service.

**Frontend work required:** Watch `workflowStatus.workflow_completed_at` for change (detected via existing 30-second polling); when it becomes non-null and status is `'approved'`, show:
```ts
toast.success('Risk Champion Appointed', {
  description: `${champion.nominee_name} has been appointed and Risk Champion permissions are now active.`
});
```
No API call required — purely reactive.

---

### Gap 19 — QMS Audit Meeting Types ✅

**Backend model `QMSAuditMeeting.MEETING_TYPE_CHOICES`:**
```python
[
  ('pre_audit', 'Pre-Audit'),
  ('entry', 'Entry'),
  ('exit', 'Exit'),
]
```
Exactly matches the SRS terminology (`pre_audit`, entry meeting, exit meeting). The backend also enforces `unique_together = [['audit_plan', 'meeting_type']]` — one of each type per plan.

**Available endpoint:** `POST /qms-plans/:id/audit-meetings/`

**Frontend work required:** Implement `QMSAuditMeetingsSection` in `QMSPlanDetailPage` showing cards for pre-audit, entry (with timetable toggle), and exit meetings.

---

### Gap 27 — Risk Meeting Minutes + Attendance ✅

**Available fields on `RiskMeeting`:**
- `minutes: string` (text field)
- `outcomes: JSON array`

**Available endpoints:**
- `GET/POST /risk/meetings/:id/attendance/` → `MeetingAttendanceListCreateView`
- `PATCH /risk/meetings/attendance/:id/` → update `attended: boolean`

**Serializer:** `MeetingAttendanceSerializer` includes `id`, `meeting`, `user_id`, `attended`.

**Frontend work required:** Document and implement `RiskMeetingViewDialog` to show:
1. Meeting details + `minutes` textarea (editable for `canManageRiskMeetings`)
2. Attendance sub-table with attendees list and `attended` toggle

---

## Section 2 — Backend PARTIALLY Supports (6 Gaps)

These gaps require frontend adjustments to match backend data structure, or require minor additional backend fields.

---

### Gap 3 — QA Exam Tracking (75% threshold + re-sit) ⚠️

**What the backend HAS on `QualityAuditor`:**
| Field | Type | Notes |
|-------|------|-------|
| `exam_attempt` | IntegerField | Number of attempts (0 by default, max 2 per Rule E.3) |
| `exam_score` | DecimalField (5,2) | Latest exam score as percentage |
| `is_certified` | BooleanField | True if score ≥ 75% |
| `certification_date` | DateField | When certification was achieved |

**What is MISSING on `QATrainingAttendee`:**
The model only has:
```python
attended = models.BooleanField(default=False)
```
No `exam_score`, `exam_attempt_number`, `exam_date`, `passed` fields on the attendee record.

**Implication for frontend:** Exam score/attempt data lives on `QualityAuditor` (parent record), NOT on the training attendee record. Frontend should:
1. Read exam data from `qualityAuditor.exam_score` + `qualityAuditor.exam_attempt`
2. The 75% threshold guard is implemented as frontend validation when PATCHING `quality_auditor.exam_score` + `quality_auditor.is_certified`
3. Show 2nd-attempt failure alert based on `exam_attempt === 2 && !is_certified`

**Backend change needed (minor):** If per-session exam tracking is required (tracking score per training session, not just latest), `QATrainingAttendee` needs `exam_score`, `exam_attempt_number`, `passed` fields added. Currently the backend only stores the latest exam data on `QualityAuditor`.

---

### Gap 5 — NC Monthly Monitoring / Overdue Indicator ⚠️

**What the backend HAS on `NonConformance`:**
- `due_date: DateField(null=True)` — target closure date
- `status: CharField` with `raised|acknowledged|in_progress|closed`

**What is MISSING:**
- No `last_reviewed_at` or `monthly_review_date` field
- No dedicated "overdue NCs" endpoint
- No monthly summary aggregation

**Implication for frontend:** The overdue badge can be computed client-side:
```ts
const isOverdue = nc.due_date && new Date(nc.due_date) < new Date() && nc.status !== 'closed';
```
No additional backend call needed for the overdue badge.

**Backend change needed (if monthly review tracking required):** Add `last_reviewed_at: DateTimeField(null=True)` to `NonConformance` and a `GET /risk/non-conformances/monthly-summary/` aggregation endpoint. This is a P2 enhancement.

---

### Gap 6 — Risk Meeting Type Enum & DRR Linkage ⚠️

**What the backend HAS on `RiskMeeting.MEETING_TYPE_CHOICES`:**
```python
('risk_discussion', 'Risk Discussion'),
('workshop', 'Workshop'),
('brainstorming', 'Brainstorming'),
('institutional_workshop', 'Institutional Workshop'),
('awareness_session', 'Awareness Session'),
```

**What is MISSING vs gap analysis expectations:**
- `irr_workshop` — covered by `institutional_workshop` (close enough, different label)
- `management_review` — not present; gap analysis said RTAP management discussion needed this type
- No FK linking `RiskMeeting` to `DepartmentalRiskRegister`

**Implication for frontend:**
- Use `institutional_workshop` instead of `irr_workshop` in frontend type constant
- `management_review` meetings are not distinguishable from `risk_discussion` type; frontend type filter should map accordingly
- The DRR linkage FK is absent — display the linked meeting as an optional text reference rather than a FK relationship

**Backend change needed (minor):** Add `('management_review', 'Management Review')` to `MEETING_TYPE_CHOICES`. Adding a nullable `dept_register = ForeignKey(DepartmentalRiskRegister, null=True)` is optional if DRR linkage is considered important.

---

### Gap 10 — Nominee Qualifications / Experience ⚠️

**RiskChampion model — FULLY SUPPORTED:**
```python
qualifications = models.TextField(blank=True)
experience_summary = models.TextField(blank=True)
justification = models.TextField(blank=True)
```
All three are in `RiskChampionSerializer`.

**QualityAuditor model — MISSING:**
`QualityAuditor` has only a generic `notes = models.TextField(blank=True)` field. It does NOT have dedicated `qualifications` or `experience_summary` fields like `RiskChampion` does.

**Implication for frontend:**
- `CreateRiskChampionDialog` can expose `qualifications` and `experience_summary` directly ✅
- `CreateQualityAuditorDialog` must use `notes` as the qualifications/experience field — add a clarifying label: "Qualifications & Experience" mapping to `notes`

**Backend change needed to align:** Add `qualifications = models.TextField(blank=True)` and `experience_summary = models.TextField(blank=True)` to `QualityAuditor` model (mirrors `RiskChampion` pattern). Until this is added, `notes` serves as the single qualifications capture field.

---

### Gap 13 — QA Appointment Pre-condition Gate ⚠️

**What the backend HAS:**
- `QualityAuditor.is_certified: BooleanField` — `true` when exam passed
- `QualityAuditor.exam_attempt: IntegerField` — 1 or 2 attempts
- `QualityAuditor.exam_score: DecimalField` — latest score

**What is MISSING:**
The backend does NOT enforce that a `QualityAuditorAppointment` can only be created when `qualityAuditor.is_certified === true`. An appointment can be created for an uncertified auditor without backend rejection.

**Implication for frontend:** Implement the gate purely in the UI:
```ts
// In QAAppointmentSection (QualityAuditorDetailPage):
const canCreateAppointment = canManageQualityAuditors && qualityAuditor.is_certified;
```
The "Create QA Appointment" button should be hidden/disabled when `!qualityAuditor.is_certified`.

**Backend change needed (optional):** Add a validator in `QualityAuditorAppointmentListCreateView.post()`:
```python
if not auditor.is_certified:
    return error_response(message="QA must pass the ISO exam before appointment can be created.", code="NOT_CERTIFIED")
```
This is recommended to prevent API-level bypass, but not strictly required if frontend gate is implemented.

---

### Gap 23 — QA Training — RMQAM Approval Step ⚠️

**What the backend HAS on `QATrainingSession`:**
```python
APPROVAL_STATUS_CHOICES = [
    ('proposed', 'Proposed'),
    ('approved', 'Approved'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]
approval_status = CharField(...)
approved_by = UUIDField(null=True)
approval_date = DateField(null=True)
```

**What is MISSING:**
- No dedicated `POST /qa-training/:id/approve/` endpoint — approval is done via `PATCH` with `{ "approval_status": "approved", "approved_by": "...", "approval_date": "..." }`
- No `POST /qa-training/:id/notify-trainees/` endpoint
- No `rejection_notes` field on the model

**Implication for frontend:**
- Implement "Approve" button as `PATCH { approval_status: 'approved' }` — simple status update, no dedicated endpoint needed
- "Reject" button: `PATCH { approval_status: 'cancelled' }` (closest available value; no separate 'rejected' status exists in backend)
- "Notify Trainees" will need to be deferred or handled through a generic notification endpoint; there's no dedicated notify endpoint for this

**Backend change needed (medium):** Either add a dedicated `POST /qa-training/:id/approve/` action view (preferred for auditability), or accept that PATCH suffices. For "Notify Trainees", a `POST /qa-training/:id/notify-attendees/` endpoint is needed to trigger notifications.

---

### Gap 29 — NC Finding Type (NC vs Area for Improvement) ⚠️

**What the backend HAS:**
`NonConformance.nc_type` is a `ForeignKey` to `NonConformanceType` (lookup table in `grc_risk_nc_type`).

The `NonConformanceType` model:
```python
code = CharField(max_length=50)
name = CharField(max_length=100)
description = TextField()
```

The `AuditChecklist.conformity` field separately has:
```python
('minor_nc', 'Minor Non-Conformance'),
('major_nc', 'Major Non-Conformance'),
('observation', 'Observation'),
('conforming', 'Conforming'),
('not_applicable', 'Not Applicable'),
```

**What is MISSING:**
- `NonConformanceType` lookup records with codes `major_nc`, `minor_nc`, `observation`, `area_for_improvement` must be **seeded** in the database — the table exists but seed data is unknown
- `NonConformance` has no standalone `finding_type` enum field; categorization depends entirely on which `NonConformanceType` record is selected
- No `area_for_improvement` conformity value in `AuditChecklist.conformity` choices

**Implication for frontend:**
- `nc_type` FK covers the gap analysis's `finding_type` requirement — frontend calls `GET /config/` to load available NC types and displays them in the form
- No schema changes needed; only **seed data** for `NonConformanceType` records is required
- Filter chips on `NonConformancesPage` filter by `nc_type_id` (FK filter) rather than an enum

**Backend change needed (minor):** Ensure `NonConformanceType` records exist for `major_nc`, `minor_nc`, `observation`, `area_for_improvement`. Add a data migration or management command to seed these values if not present.

---

## Section 3 — Backend Does NOT Support (13 Gaps)

These gaps require **backend model changes + new endpoints** before frontend implementation can proceed.

---

### Gap 4 — NC Dispute / Finding Amendment ❌

**Current backend state:**
```python
NonConformance.STATUS_CHOICES = [
    ('raised', 'Raised'),
    ('acknowledged', 'Acknowledged'),
    ('in_progress', 'In Progress'),
    ('closed', 'Closed'),
]
```
No `disputed` or `withdrawn` values. No dispute endpoint.

**Required backend changes:**
1. Add `('disputed', 'Disputed')` and `('withdrawn', 'Withdrawn')` to `NonConformance.STATUS_CHOICES`
2. Add DB migration
3. Add `dispute_reason = models.TextField(blank=True)` field to `NonConformance`
4. Add `POST /risk/non-conformances/:id/dispute/` — sets status to `disputed`, records `dispute_reason`, actor, timestamp
5. Add `POST /risk/non-conformances/:id/resolve-dispute/` — TL amends/closes the dispute

**Frontend implementation blocked until:** Steps 1–5 are implemented.

---

### Gap 7 — RTAP "Send Reminder to RCs" ❌

**Current backend state:** No `/rtap/:id/send-reminder/` endpoint exists. `RTAPDetailView` only handles GET/PUT/PATCH/DELETE.

**Required backend changes:**
1. Add `RTAPSendReminderView` in `risk_treatment_plan_views.py`
2. Register URL: `path("rtap/<uuid:pk>/send-reminder/", ...)`
3. View logic: Identify RCs linked to this RTAP's IRR entries → dispatch notifications to their user IDs via messaging infrastructure
4. Return: `{"success": true, "data": {"notified_count": N}}`

**Frontend implementation blocked until:** Endpoint is implemented.

---

### Gap 8 — IRR Workshop Notification Actions ❌

**Current backend state:** No notification action endpoints on IRR. `InstitutionalRiskRegister` model has no `workshop_date` or `workshop_venue` fields.

**Required backend changes:**
1. Add to `InstitutionalRiskRegister` model:
   ```python
   workshop_date = models.DateField(null=True, blank=True)
   workshop_venue = models.CharField(max_length=255, blank=True)
   directors_notified_at = models.DateTimeField(null=True, blank=True)
   rcs_notified_at = models.DateTimeField(null=True, blank=True)
   ```
2. Add `POST /risk/institutional-registers/:id/notify-directors/`
3. Add `POST /risk/institutional-registers/:id/notify-rcs/`
4. DB migration for new fields

**Frontend implementation blocked until:** Steps 1–4 are implemented.

---

### Gap 12 — MRM Directives Tracking ❌

**Current backend state:**
```python
QMSAuditReport.STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('tl_signed', 'TL Signed'),
    ('auditee_acknowledged', 'Auditee Acknowledged'),
    ('finalised', 'Finalised'),
]
```
No `presented_at_mrm`, `directives_received` statuses. No `mrm_directives` field. The QMS audit report workflow ends at `finalised` — no post-finalization governance chain.

**Required backend changes:**
1. Extend `QMSAuditReport.STATUS_CHOICES` with:
   - `('submitted_to_rmqam', 'Submitted to RMQAM')`
   - `('returned_for_revision', 'Returned for Revision')`
   - `('presented_at_mrm', 'Presented at MRM')`
   - `('directives_received', 'Directives Received')`
   - `('submitted_to_audit_committee', 'Submitted to Audit Committee')`
   - `('audit_committee_reviewed', 'Audit Committee Reviewed')`
   - `('adopted_by_commission', 'Adopted by Commission')`
2. Add model fields:
   ```python
   mrm_directives = models.TextField(blank=True)
   mrm_directives_communicated_at = models.DateTimeField(null=True, blank=True)
   rmqam_review_comments = models.TextField(blank=True)
   returned_for_revision_at = models.DateTimeField(null=True, blank=True)
   ```
3. Update `QMSAuditReportSerializer` to include new fields
4. DB migration

**Note:** Gaps 12, 25, and 26 all stem from the same root issue — the `QMSAuditReport` model is too minimal. All three should be resolved in a single backend migration.

**Frontend implementation of Gaps 12, 25, 26 ALL BLOCKED until:** Model + migration is complete.

---

### Gap 15 — RAS Rework / Return Cycle ❌

**Current backend state:** `RiskAssessmentSheet` has NO `status` field. It inherits only `is_active` from `StatusMixin`. The serializer fields are:
```
id, risk_champion, org_unit_id, fiscal_year, risk_category, risk_title,
risk_description, risk_owner, likelihood, impact, inherent_risk_score,
inherent_risk_level, existing_controls, control_assessment, further_action,
residual_likelihood, residual_impact, residual_risk_score, residual_risk_level,
references, is_active, created_at, updated_at, created_by
```
**No `status` field exposed.**

**Required backend changes (also resolves Gap 28):**
1. Add a `status` CharField to `RiskAssessmentSheet`:
   ```python
   STATUS_DRAFT = 'draft'
   STATUS_SUBMITTED_TO_HEAD = 'submitted_to_head'
   STATUS_HEAD_ENDORSED = 'head_endorsed'
   STATUS_SUBMITTED_TO_RMQAM = 'submitted_to_rmqam'
   STATUS_APPROVED = 'approved' 
   STATUS_RETURNED_FOR_REWORK = 'returned_for_rework'
   STATUS_CHOICES = [
       (STATUS_DRAFT, 'Draft'),
       (STATUS_SUBMITTED_TO_HEAD, 'Submitted to Head'),
       (STATUS_HEAD_ENDORSED, 'Head Endorsed'),
       (STATUS_SUBMITTED_TO_RMQAM, 'Submitted to RMQAM'),
       (STATUS_APPROVED, 'Approved'),
       (STATUS_RETURNED_FOR_REWORK, 'Returned for Rework'),
   ]
   status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
   ```
2. Add fields for rework tracking:
   ```python
   review_comments = models.TextField(blank=True)
   rejected_at = models.DateTimeField(null=True, blank=True)
   resubmitted_at = models.DateTimeField(null=True, blank=True)
   ```
3. Update `RiskAssessmentSheetSerializer` to include `status`, `review_comments`
4. DB migration
5. Consider adding:
   - `submitted_to_head_at: DateTimeField(null=True)` 
   - `head_endorsed_by: UUIDField(null=True)` — Head who endorsed

**Frontend implementation of Gaps 15 AND 28 BOTH BLOCKED until:** Steps 1–4 are complete.

---

### Gap 20 — Export / Print for Risk Reports ❌

**Current backend state:** No export endpoints exist. Only JSON API responses.

**Required backend changes (P4 — low priority):**
1. `GET /risk/dashboard/export/?format=pdf|xlsx` → DRS-based PDF generation or Django `reportlab`/`openpyxl`
2. `GET /risk/quarterly-reports/:id/export/` → QPR PDF export

**Frontend implementation:** Deferred. Document as out-of-scope for Phase I. Add to future enhancement backlog.

---

### Gap 21 — RC / QA Nomination Request Flow ❌

**Current backend state:** `CreateRiskChampionDialog` creates the RC record directly. No "nomination request" entity or two-phase flow (RMQAM requests → Head responds).

**Required backend changes (if automation desired):**
1. New model: `RCNominationRequest` with fields: `org_unit_id`, `org_unit_type`, `requested_by`, `requested_at`, `head_user_id`, `responded_at`, `nominee_user_id`, `status`
2. Endpoints: `POST /risk/champions/nomination-requests/`, `GET`, `PATCH /:id/respond/`
3. DB migration

**Alternative (accepted workaround):** Document in frontend plan that the nomination process is managed offline, and `CreateRiskChampionDialog` records the Head's response directly (RMQAM enters the nominee name after receiving the Head's nomination offline). This avoids backend changes.

**Frontend implementation:** Unblocked if workaround is accepted. Blocked if full automation is required.

---

### Gap 22 — RTAP Item RMO Return-for-Rework ❌

**Current backend state:**
```python
RTAPItem.STATUS_CHOICES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
]
```
No `returned_for_rework` status. No `review_comments`, `returned_at`, `resubmitted_at` fields.

**Required backend changes:**
1. Add to `RTAPItem.STATUS_CHOICES`:
   ```python
   ('returned_for_rework', 'Returned for Rework'),
   ```
2. Add fields:
   ```python
   review_comments = models.TextField(blank=True)
   returned_at = models.DateTimeField(null=True, blank=True)
   resubmitted_at = models.DateTimeField(null=True, blank=True)
   ```
3. Update `RTAPItemSerializer` to expose `review_comments`
4. DB migration

**Frontend implementation blocked until:** Steps 1–4 are complete.

---

### Gap 24 — Post-Approval IRR/RTAP Distribution to Directorates ❌

**Current backend state:**
- `InstitutionalRiskRegister` has no `distributed_to_directorates_at` or `distribution_reference` fields
- `RiskTreatmentActionPlan` has no such fields either
- No `/distribute/` endpoints in URL config

**Required backend changes:**
1. Add to `InstitutionalRiskRegister`:
   ```python
   distributed_to_directorates_at = models.DateTimeField(null=True, blank=True)
   distribution_reference = models.CharField(max_length=255, blank=True)
   ```
2. Add same fields to `RiskTreatmentActionPlan`
3. Add `POST /risk/institutional-registers/:id/distribute/` (sends notifications to all RCs)
4. Add `POST /risk/rtap/:id/distribute/`
5. DB migration

**Frontend implementation blocked until:** Steps 1–5 are complete.

---

### Gap 25 — QMS Audit Report — RMQAU Return-for-Revision ❌

*See Gap 12 — same root issue. All QMS Report status and field changes are consolidated.*

**Required backend changes:** Same as Gap 12 resolution (model extension + migration).

**Frontend implementation blocked until:** Gap 12 backend changes are complete.

---

### Gap 26 — QMS Audit Report — Audit Committee + Commission Adoption ❌

*See Gap 12 — same root issue. All QMS Report status and field changes are consolidated.*

**Required backend changes:** Same as Gap 12 resolution (model extension + migration).

**Frontend implementation blocked until:** Gap 12 backend changes are complete.

---

### Gap 28 — RAS Status Transition Actions ❌

*See Gap 15 — same root issue. Both Gap 15 and Gap 28 require the `RiskAssessmentSheet.status` field.*

**Required backend changes:** Same as Gap 15 resolution (add `status` field + migration).

**Frontend implementation blocked until:** Gap 15 backend changes are complete.

---

## Section 4 — Backend Change Priority Matrix

| Priority | Gap(s) | Change Required | Effort |
|----------|--------|----------------|--------|
| **P1-CRITICAL** | 15, 28 | Add `status` field to `RiskAssessmentSheet` + migration | Medium |
| **P1-CRITICAL** | 12, 25, 26 | Extend `QMSAuditReport` status choices + MRM/revision fields + migration | Medium |
| **P1-HIGH** | 4 | Add `disputed/withdrawn` to `NonConformance` + dispute endpoints | Medium |
| **P2-HIGH** | 22 | Add `returned_for_rework` to `RTAPItem` + rework fields | Small |
| **P2-HIGH** | 8 | Add workshop fields to IRR + notify endpoints | Medium |
| **P2-HIGH** | 7 | Add RTAP send-reminder endpoint | Small |
| **P2-HIGH** | 24 | Add distribution fields + distribute endpoints (IRR, RTAP) | Medium |
| **P2-MEDIUM** | 3 | Add exam fields to `QATrainingAttendee` | Small |
| **P2-MEDIUM** | 10 | Add `qualifications/experience_summary` to `QualityAuditor` | Small |
| **P2-MEDIUM** | 6 | Add `management_review` meeting type; optional DRR FK | Small |
| **P2-MEDIUM** | 23 | Add dedicated approve/notify training endpoints | Small |
| **P3-LOW** | 13 | Add `is_certified` gate to QA appointment creation endpoint | Tiny |
| **P3-LOW** | 5 | Add `last_reviewed_at` to NonConformance; monthly summary endpoint | Small |
| **P3-LOW** | 29 | Seed `NonConformanceType` records (no schema change) | Tiny |
| **P4-DEFER** | 20 | Export/print endpoints | Large |
| **P4-DEFER** | 21 | Full nomination request flow automation | Large |

---

## Section 5 — Gaps That Are Frontend-Only (No Backend Needed)

These gaps need **zero backend changes** — the data is available; only frontend code is missing.

| Gap # | What to implement in frontend | Backend data available |
|-------|------------------------------|----------------------|
| 1 | `RiskDashboardPage.tsx` + route + sidebar | `GET /risk/dashboard/` |
| 2 | Bar/line chart in `RiskDashboardPage` | `GET /risk/dashboard/comparative-analysis/` |
| 9 | 409 error handler in `CreateRiskChampionDialog` | DB constraint returns 409 |
| 11 | `QMSAuditMeetingsSection` using plan-level NDA fields | `QMSAuditPlan.nda_*` fields |
| 13 | Button visibility gate: `canCreate && auditor.is_certified` | `QualityAuditor.is_certified` |
| 14 | "Mark as Dispatched" PATCH button | `dispatched`, `dispatch_date` fields |
| 16 | 7-day warning toast before workflow submit | `committee_meeting_date` field |
| 17 | "Submit to IAGO" PATCH button | `iago_submitted`, `iago_submission_date` |
| 18 | Role-assigned confirmation toast | `workflow_completed_at` polling trigger |
| 19 | `QMSAuditMeetingsSection` with pre/entry/exit cards | `/qms-plans/:id/audit-meetings/` |
| 27 | `RiskMeetingViewDialog` with minutes + attendance section | `/meetings/:id/attendance/` |

---

## Section 6 — Implementation Order Recommendation

### Phase 1 — Backend-First (Unblock P1 Gaps)
These MUST be done on the backend before any frontend work can start:

1. **RAS status field** (`status` CharField + choices + migration on `RiskAssessmentSheet`) → Unblocks Gaps 15, 28
2. **QMSAuditReport extended statuses** (MRM/revision/committee stages + fields + migration) → Unblocks Gaps 12, 25, 26
3. **NC disputed/withdrawn status** + dispute endpoint → Unblocks Gap 4

### Phase 2 — Backend-First (Unblock P2 Gaps)
4. **RTAP Item rework** (`returned_for_rework` status + fields) → Unblocks Gap 22
5. **IRR workshop fields + notify endpoints** → Unblocks Gap 8
6. **RTAP send-reminder endpoint** → Unblocks Gap 7
7. **IRR/RTAP distribution endpoints + fields** → Unblocks Gap 24

### Phase 3 — Frontend Implementation (all supported gaps)
8. Implement all 10 fully-supported gaps (frontend-only: Gaps 1, 2, 9, 11, 14, 16, 17, 18, 19, 27)
9. Implement all 6 partially-supported gaps after minor backend adjustments (Gaps 3, 5, 6, 10, 13, 23, 29)

### Phase 4 — Backend + Frontend (P2-P3 gaps)
10. Implement remaining unblocked gaps as backend changes land

---

## Section 7 — Verified "Backend 100% Complete" Claims

The original gap analysis header states **"Backend: 100% implemented (all endpoints live)"** — this was accurate for the originally defined backend scope. The newly identified gaps (in Section 3 above) represent **SRS requirements that were NOT in the original backend implementation scope**, rather than regressions. They are new gap discoveries.

### Confirmed Backend Implementations (verified against actual code):
- ✅ All workflow entities: RC Appointment, QA Appointment, DRR, IRR, RTAP, QPR, QMS Program, QMS Plan — all have full workflow start/status/history/advance/cancel/recall endpoints
- ✅ Risk Dashboard + Comparative Analysis endpoints
- ✅ All CRUD endpoints: champions, assessments, registers, RTAP, RTAP items, quarterly updates
- ✅ QMS full chain: programs → plans → checklists → reports → NCs
- ✅ QMS Audit Meetings (pre_audit/entry/exit) + Timetable entries
- ✅ Risk Meetings + Attendance
- ✅ QA Training sessions + Attendees
- ✅ RC/QA Appointment dispatch tracking fields
- ✅ Committee meeting date + IAGO fields on QPR
- ✅ Workshop/IRR LSM submission tracking
- ✅ RC uniqueness DB constraint
- ✅ 10-day audit notification rule validation in `QMSAuditPlan.clean()`
- ✅ Inherent + residual risk score auto-computation in `RiskAssessmentSheet.save()`
- ✅ NDA tracking fields on `QMSAuditPlan`

---

*End of Backend Gap Support Analysis*
*Prepared: March 2026*
*Purpose: Pre-implementation audit before frontend gap-fixing phase begins*

