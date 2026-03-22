# Risk Management — Implementation Plan vs SRS Gap Analysis

**Date:** 2026-03-20
**SRS Document:** `GRC_SRS/risk/RISK_MANAGEMENT.md`
**Implementation Plan:** `risk_management/Risk_Management_Implementation_Plan.md`

---

## Executive Summary

**Verdict: ❌ The Implementation Plan requires corrections before it can be followed with full confidence.**

The plan provides a **strong foundational architecture** — 20 business models, 6 lookup tables, 8 workflow templates, 24 RBAC permission codes, 80+ API views, and a well-structured 13-phase implementation sequence. It covers the core data entities and primary workflows correctly.

However, **20 gaps** were identified across functional requirements, process coverage, and non-functional requirements. Of these:

- **5 are Critical** — represent entirely missing functional areas required by the SRS
- **8 are Significant** — partially covered but need additional models, fields, or logic
- **7 are Minor** — addressable through configuration, documentation, or small additions

---

## Gap Analysis — Functional Requirements

### GAP-01: Missing Meeting/Workshop Management (CRITICAL)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.5 Process Flow Steps 1–2; §1.9.6 Process Flow Steps 1–3; §4.11.1.1 #3, #9; Detailed Requirements ("Scheduling and documentation of risk review meetings") |
| **SRS Requirement** | The system shall support: (a) RC scheduling and notifying staff about risk discussion meetings with virtual meeting links; (b) Recording attendance and meeting outcomes; (c) Organizing workshops with all RCs for Institutional Risk Register development; (d) Brainstorming sessions, workshops, interviews, and surveys for risk identification. |
| **Implementation Coverage** | **Not covered.** No model, serializer, view, or endpoint exists for meetings, workshops, attendance, or meeting minutes. The plan jumps directly from Risk Champions to Risk Assessment Sheets without modeling the collaborative identification process. |
| **Impact** | Multiple SRS process flows depend on meeting notification and documentation. Without this, the system cannot track when risk discussion meetings occurred, who attended, or what was discussed. |
| **Recommended Fix** | Add a `RiskMeeting` model and supporting infrastructure: |

**Proposed additions:**
```
Model: RiskMeeting
  - meeting_type: choices (risk_discussion, workshop, brainstorming, institutional_workshop)
  - organized_by: UUIDField (user_id)
  - org_unit_id: UUIDField (nullable for cross-unit workshops)
  - fiscal_year: FK to FiscalYear
  - title: CharField
  - agenda: TextField
  - meeting_date: DateTimeField
  - venue: CharField (physical location)
  - virtual_link: URLField (nullable — for clickable join links per SRS)
  - status: choices (scheduled, in_progress, completed, cancelled)
  - minutes: TextField (nullable)
  - outcomes: JSONField (default=list)

Model: MeetingAttendance
  - meeting: FK to RiskMeeting
  - user_id: UUIDField
  - attended: BooleanField (default=False)
  - unique_together: [['meeting', 'user_id']]

New view files: risk_meeting_views.py
New URL paths under: /api/v1/grc/risk/meetings/
New permissions: grc:risk_meeting:manage, grc:risk_meeting:view
```

---

### GAP-02: Missing QA Training Management (CRITICAL)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.8 Process Flow Steps 2–5; Detailed Requirements ("Arrangement and Approval of ISO 9001:2015 Training", "QMS Audit Examination") |
| **SRS Requirement** | The system shall: (a) Track ISO 9001:2015 training arrangements (trainer details, date/time/venue, RMQAM approval); (b) Notify trainees of approved training schedule; (c) Administer and record QMS Audit examination results; (d) Allow re-sit (max 2 attempts); (e) Trigger replacement nomination on second failure. |
| **Implementation Coverage** | **Partially covered.** The `QualityAuditor` model captures `exam_attempt` (max 2), `exam_score`, `is_certified`, and `certification_date`. However, there is **no model** for training sessions, trainer details, training attendance, or training approval workflow. |
| **Impact** | The SRS describes an elaborate training pipeline that precedes QA appointment. Without tracking training, the system cannot enforce the prerequisite that QAs must complete ISO 9001:2015 training before examination. |
| **Recommended Fix** | Add a `QATrainingSession` model: |

**Proposed additions:**
```
Model: QATrainingSession
  - title: CharField
  - trainer_name: CharField
  - trainer_organization: CharField (blank)
  - training_date: DateField
  - training_time: TimeField
  - venue: CharField
  - approval_status: choices (proposed, approved, completed, cancelled)
  - approved_by: UUIDField (nullable — RMQAM)
  - approval_date: DateField (nullable)
  - notes: TextField (blank)

Model: QATrainingAttendee
  - training_session: FK to QATrainingSession
  - quality_auditor: FK to QualityAuditor
  - attended: BooleanField (default=False)
  - unique_together: [['training_session', 'quality_auditor']]

Add to QualityAuditor model:
  - training_session: FK to QATrainingSession (nullable)

New permissions: grc:qa_training:manage
```

---

### GAP-03: Missing Legal Service Manager (LSM) Role and 7-Day Submission Rule (CRITICAL)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.6 Process Flow Step 10; §1.9.7 Process Flow Steps 8, 10, 11; Detailed Requirements (multiple "submit to LSM" references, "seven days before the Committee meeting") |
| **SRS Requirement** | (a) The LSM is a key actor who receives documents for onward submission to the Risk and Governance Committee and Commission; (b) Submissions to Committee members must occur at least 7 days before the meeting date; (c) The system must track LSM submission dates and distribution records. |
| **Implementation Coverage** | **Partially covered.** Workflow template `grc.quarterly_risk_report_approval` includes an `lsm_submit` stage. However: (1) The RBAC roles in Phase 6 do **not** define an `lsm` role; (2) The 7-day advance submission rule is **not enforced** anywhere; (3) No model tracks committee meeting dates against submission dates. |
| **Impact** | LSM is referenced in 3 of 5 major process flows. Without the role and rule enforcement, a critical governance checkpoint is missing. |
| **Recommended Fix** | |

1. **Add LSM role to RBAC** in `grc-service.json`:
```json
{
  "code": "lsm",
  "name": "Legal Service Manager",
  "permissions": ["grc:institutional_risk_register:approve", "grc:rtap:approve",
                   "grc:quarterly_risk_report:approve", "grc:risk_dashboard:view"]
}
```

2. **Add committee meeting date tracking** — extend workflow-enabled models (`InstitutionalRiskRegister`, `RiskTreatmentActionPlan`, `QuarterlyPerformanceReport`) with:
```
  - committee_meeting_date: DateField (nullable)
  - lsm_submission_date: DateField (nullable)
```

3. **Add validation** in the LSM submission workflow stage: validate `lsm_submission_date` is at least 7 calendar days before `committee_meeting_date`.

---

### GAP-04: Missing Non-Disclosure Form Management for QMS Audit (SIGNIFICANT)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.9 Process Flow Step 11; Detailed Requirements ("Facilitate signing of non-disclosure/confidentiality forms") |
| **SRS Requirement** | The system shall support signing of non-disclosure forms during entry meetings, with copies retained by TL and given to auditees. |
| **Implementation Coverage** | **Not covered.** No field or model exists for non-disclosure forms. |
| **Recommended Fix** | Add to `QMSAuditPlan` model: |
```
  - nda_signed: BooleanField (default=False)
  - nda_signed_date: DateField (nullable)
  - nda_document_id: UUIDField (nullable — DRS reference)
```

---

### GAP-05: Missing Entry/Exit Meeting Records for QMS Audit (SIGNIFICANT)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.9 Process Flow Steps 9–11 (Entry), Steps 15–17 (Exit); Detailed Requirements ("Entry meeting minutes", "Exit meeting minutes", "Attendance list") |
| **SRS Requirement** | The system shall support: (a) Conducting entry meetings (record minutes, agreed timetable, attendance); (b) Conducting exit meetings (discuss findings, resolve disagreements, record revised observations). |
| **Implementation Coverage** | **Not covered.** `QMSAuditPlan` has `audit_start_date` and `audit_end_date`, but no entry/exit meeting records. |
| **Recommended Fix** | Add an `AuditMeeting` model: |
```
Model: AuditMeeting
  - audit_plan: FK to QMSAuditPlan
  - meeting_type: choices (entry, exit, pre_audit)
  - meeting_date: DateTimeField
  - minutes: TextField (blank)
  - attendance: JSONField (default=list)  # list of user_ids
  - timetable_agreed: BooleanField (default=False)
  - timetable_revised: BooleanField (default=False)
  - unique_together: [['audit_plan', 'meeting_type']]
```

---

### GAP-06: Missing Document Dispatch/Distribution Tracking (SIGNIFICANT)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.3 Process Output ("Dispatched Appointment Letter"); §1.9.8 ("Dispatch signed appointment letters through the Registry Office", "Track delivery status") |
| **SRS Requirement** | The system shall track dispatch of signed appointment letters through the Registry Office, including dispatch reference, date, and recipient confirmation. |
| **Implementation Coverage** | **Not covered.** `RiskChampionAppointment` and `QualityAuditorAppointment` have `document_id` and `stamped_document_url` for DRS storage, but no dispatch tracking fields. |
| **Recommended Fix** | Extend appointment models with: |
```
  - dispatched: BooleanField (default=False)
  - dispatch_date: DateField (nullable)
  - dispatch_reference: CharField (max_length=100, blank)
  - recipient_confirmed: BooleanField (default=False)
  - recipient_confirmed_date: DateField (nullable)
```

---

### GAP-07: Missing Historical Data / Cross-Reference Support (SIGNIFICANT)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §4.11.1.1 #4 ("Review of historical data, lessons learned, internal and external audit reports, and industry best practices") |
| **SRS Requirement** | The system shall facilitate the review of historical data, lessons learned, and audit reports during risk identification. |
| **Implementation Coverage** | **Not covered.** No mechanism links Risk Assessment Sheets to previous risk registers, audit findings, or lessons learned. |
| **Recommended Fix** | Add an optional `JSONField` to `RiskAssessmentSheet`: |
```
  - references: JSONField(default=list)
  # Stores: [{"type": "audit_finding", "id": "uuid", "title": "..."}, ...]
```
And/or add a `RiskReference` model:
```
Model: RiskReference
  - risk_sheet: FK to RiskAssessmentSheet
  - reference_type: choices (audit_finding, previous_risk, lesson_learned, external_report)
  - reference_id: UUIDField (nullable — internal entity link)
  - reference_title: CharField
  - reference_url: URLField (blank)
  - notes: TextField (blank)
```

---

### GAP-08: Missing Risk Awareness Session Tracking (SIGNIFICANT)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §4.11.1.1 #1 ("Conduct awareness sessions for Risk Champions, Risk Owners, and staff on Risk Management Principles and processes") |
| **SRS Requirement** | The system shall enable RMQAU to conduct and track awareness sessions on risk management principles for RC, Risk Owners, and staff. |
| **Implementation Coverage** | **Not covered.** No model for awareness sessions. Could potentially reuse the `RiskMeeting` model proposed in GAP-01 with a `meeting_type` of `awareness_session`. |
| **Recommended Fix** | Extend GAP-01's `RiskMeeting.meeting_type` choices to include `awareness_session`, or create a separate lightweight `AwarenessSession` model. |

---

### GAP-09: Incomplete Notification Strategy (SIGNIFICANT)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.5 Step 1 ("RC sends an email to staff"); §1.9.6 Steps 1–2 ("RMQAM sends e-mail", "RMO send notification"); §1.9.7 Step 1 ("RMO sends e-mail to RCs reminding"); §1.9.9 Step 8 ("send email notification and timetable to auditees 10 working days prior"); Multiple detailed requirements referencing email notifications |
| **SRS Requirement** | Every major workflow step triggers specific email/in-app notifications to named actors. Notification includes contextual details (meeting links, deadlines, document references). |
| **Implementation Coverage** | **Partially covered.** The plan references `NotificationPublisher` and Celery tasks for deadline reminders. The `QMSAuditPlan.clean()` validates the 10-day rule. However: (1) No notification template definitions per workflow step; (2) No explicit mapping of "which event triggers which notification to whom"; (3) The plan for Phase 9 (Kafka events) publishes events but doesn't map them to specific notification actions. |
| **Recommended Fix** | Add a **Notification Mapping Table** to Phase 9 or Phase 10: |

```
| Trigger Event                        | Recipient(s)           | Notification Content                     |
|--------------------------------------|------------------------|------------------------------------------|
| RC Appointment workflow started       | RC, Head of Unit       | "Appointment letter drafted for review"  |
| Dept Register submitted to RMQAM     | RMQAM                  | "New departmental register for review"   |
| Risk Assessment returned for rework   | RC                     | "Risk assessment returned with comments" |
| RTAP quarterly update due (3 days)    | RC                     | "Quarterly update due in 3 days"         |
| QMS Audit Plan approved               | Assigned QAs           | "Prepare audit checklists"               |
| Audit notification to auditee         | Auditee unit head      | "Audit scheduled in 10 days" + timetable |
| NC raised                             | Auditee, responsible   | "Non-conformance raised for your unit"   |
| Workflow stage advanced               | Next stage assignee    | "Action required: [stage name]"          |
```

Also define notification templates in the implementation plan.

---

### GAP-10: Missing Audit Timetable Entity (SIGNIFICANT)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.9 Steps 8, 10, 11 ("timetable to auditees", "adjust the timetable", "agreed timetable") |
| **SRS Requirement** | The audit timetable is a distinct document that can be adjusted, agreed upon, and sent to auditees. It includes per-day/per-session scheduling for the audit team. |
| **Implementation Coverage** | **Not covered.** `QMSAuditPlan` has overall dates (`audit_start_date`, `audit_end_date`, `notification_date`) but no structured timetable (daily agenda, session assignments). |
| **Recommended Fix** | Add a `QMSAuditTimetableEntry` model: |
```
Model: QMSAuditTimetableEntry
  - audit_plan: FK to QMSAuditPlan
  - date: DateField
  - start_time: TimeField
  - end_time: TimeField
  - process_or_area: CharField
  - assigned_auditor: UUIDField
  - auditee_unit_id: UUIDField
  - sort_order: IntegerField (default=0)
```
Add a `timetable_agreed` BooleanField to `QMSAuditPlan`.

---

### GAP-11: Missing Comparative Analysis API Endpoint (SIGNIFICANT)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.7 Process Flow Step 6 ("comparative analysis of implementation rate between current and previous quarters"); Detailed Requirements ("Compare current quarter implementation rates against previous quarters", "Identify trends, delays, and improvement areas") |
| **SRS Requirement** | The system shall enable RMQAM to perform and view comparative analysis of risk control implementation rates across quarters, including variance and trend analysis. |
| **Implementation Coverage** | **Partially covered.** `RiskDashboardView` returns aggregate stats, but no explicit comparative/trend analysis endpoint is defined. `QuarterlyPerformanceReport` has snapshot metrics but no quarter-over-quarter comparison logic. |
| **Recommended Fix** | Add a dedicated endpoint to the dashboard or quarterly reports views: |
```
GET /api/v1/grc/risk/dashboard/comparative-analysis/
  Query params: fiscal_year_id, current_quarter_id
  Response: {
    "current_quarter": { "total_risks": N, "rtap_completed": N, ... },
    "previous_quarter": { "total_risks": N, "rtap_completed": N, ... },
    "variance": { "rtap_completed_delta": N, "rtap_completed_pct_change": N, ... },
    "trend": [{ "quarter": "Q1", "completion_rate": 0.45 }, ...]
  }
```

---

### GAP-12: Missing IAGO Submission Tracking (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §4.11.1.1 #14 ("Generate Quarterly Risk Management Implementation Report for submission to the Audit Committee and Internal Auditor General Office (IAGO)") |
| **SRS Requirement** | Quarterly reports must be tracked for submission to both the Audit Committee and IAGO. |
| **Implementation Coverage** | **Not covered.** `QuarterlyPerformanceReport` workflow goes through Management → Committee → Commission, but IAGO is not mentioned. |
| **Recommended Fix** | Add to `QuarterlyPerformanceReport`: |
```
  - iago_submitted: BooleanField (default=False)
  - iago_submission_date: DateField (nullable)
  - iago_reference: CharField (max_length=100, blank)
```

---

### GAP-13: RC Nominee Qualification Fields (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §4.11.1.2 #3 ("Capture relevant details such as the nominee's qualifications and experience") |
| **SRS Requirement** | The recommendation process shall include capturing nominee's qualifications and experience. |
| **Implementation Coverage** | **Partially covered.** `RiskChampion` model has a `notes` field but no dedicated qualification/experience fields. |
| **Recommended Fix** | Add to `RiskChampion`: |
```
  - qualifications: TextField (blank)
  - experience_summary: TextField (blank)
  - justification: TextField (blank)  # endorsement/justification for nomination
```

---

### GAP-14: Rework Cycle Tracking (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | Multiple process flows ("Track rework cycles and resubmissions", "Track resubmission cycles") |
| **SRS Requirement** | The system shall track how many times a document was returned for rework and resubmitted. |
| **Implementation Coverage** | **Partially covered.** The `workflow/recall/` endpoint resets to draft for resubmission. Workflow history (via WO service) captures stage transitions. However, there's no explicit counter or log at the entity level. |
| **Recommended Fix** | Add to all WorkflowMixin entities: |
```
  - rework_count: IntegerField (default=0)  # incremented on each recall
```
Increment in `clear_workflow()` or in the recall view.

---

### GAP-15: Missing MRM Integration/Directives Tracking (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.9.9 Steps 18–19 ("Management Review Meeting", "RMQAM receives all directives") |
| **SRS Requirement** | After QMS audit report presentation at MRM, the system shall track MRM directives and their communication to responsible parties. |
| **Implementation Coverage** | **Not covered.** Workflows advance through management stages but MRM directives are not tracked as discrete items. |
| **Recommended Fix** | This could be handled via the `ActivityReport` model (already exists) or by adding a `directive` field to workflow stage comments. Alternatively, consider a lightweight `Directive` model if directives need independent tracking across multiple entity types. |

---

### GAP-16: Missing Monthly NC Closure Monitoring (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §4.11.1.4 #14 ("Monitor the closure status of corrective actions monthly and report to the Commission quarterly") |
| **SRS Requirement** | NC corrective action closure status shall be monitored monthly. |
| **Implementation Coverage** | **Partially covered.** Celery task `check_risk_monitoring_deadlines` runs daily for RTAP items, but no task monitors NC closure status monthly. |
| **Recommended Fix** | Add a Celery task in Phase 10: |
```python
@shared_task(name='grc.check_nc_closure_status')
def check_nc_closure_status():
    """Monthly task: Check open NCs past due_date, escalate to RMQAM."""
    ...

# In celery beat schedule:
'grc.check_nc_closure_status': {
    'task': 'grc.check_nc_closure_status',
    'schedule': crontab(day_of_month=1, hour=8, minute=0),  # 1st of each month
},
```

---

### GAP-17: Missing Review Comments/Feedback Fields (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | Multiple detailed requirements ("Review comments", "Review status", "Rejection reason", "Clarification requests") |
| **SRS Requirement** | At every review/approval step, reviewers' comments, rejection reasons, and feedback must be captured. |
| **Implementation Coverage** | **Partially covered.** Workflow advance actions accept a `comment` parameter, and WO service logs these. However, at the entity level, there's no field to display the latest review comment or rejection reason without querying the WO service. |
| **Recommended Fix** | Add to all WorkflowMixin entities: |
```
  - last_review_comment: TextField (blank)
  - last_reviewed_by: UUIDField (nullable)
  - last_reviewed_at: DateTimeField (nullable)
```
Populate these in `advance_workflow_stage()` when the action is `reject` or `return`.

---

### GAP-18: Missing Endorsement Confirmation Field (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | Detailed Requirements for Dept Register ("Attach evidence of departmental approval", "Endorsement confirmation") |
| **SRS Requirement** | When RC forwards risk assessment sheets to RMQAM, evidence of departmental endorsement must be attached. |
| **Implementation Coverage** | **Not covered.** `DepartmentalRiskRegister` and `RiskAssessmentSheet` have no endorsement fields. |
| **Recommended Fix** | Add to `DepartmentalRiskRegister`: |
```
  - endorsed_by: UUIDField (nullable)  # Director/Unit Manager who endorsed
  - endorsement_date: DateField (nullable)
  - endorsement_document_id: UUIDField (nullable)  # DRS reference for evidence
```

---

## Gap Analysis — Non-Functional Requirements

### GAP-NF-01: Missing Caching Strategy for Risk Data (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.5.6 #2 ("Caching mechanisms for frequently accessed compliance and audit data") |
| **Implementation Coverage** | Redis is mentioned for IAM client user profile lookups, but no caching strategy is defined for risk-specific data (e.g., lookup tables, dashboard aggregations). |
| **Recommended Fix** | Add a note to Phase 1 or Phase 7: Use Django cache framework with Redis backend for lookup table responses (`RiskCategory`, `RiskLikelihood`, `RiskImpact`, `RiskLevel`) and dashboard aggregation queries. Set TTL of 5–15 minutes. |

---

### GAP-NF-02: Missing Retry Mechanism for External Service Calls (MINOR)

| Attribute | Detail |
|---|---|
| **SRS Reference** | §1.5.8 #2 ("Retry mechanisms for failed risk assessments, audit reports, or meeting coordination") |
| **Implementation Coverage** | Kafka event publishing uses `try/except` with logging but no retry. DRS uploads and WO client calls have no retry mechanism. |
| **Recommended Fix** | Add retry decorators or implement retry logic for: (a) `KafkaMessagingService` — use Celery retry on publish failure; (b) `DocumentServiceClient` — use `requests` retry adapter with exponential backoff; (c) `OrchestrationClient` — same retry adapter. |

---

## Summary Table

| Gap ID | Severity | SRS Section | Gap Description | Plan Phase Affected |
|--------|----------|-------------|-----------------|---------------------|
| GAP-01 | **CRITICAL** | §1.9.5, §1.9.6, §4.11.1.1 | Missing meeting/workshop management | Phase 2, 5, 7, 8 |
| GAP-02 | **CRITICAL** | §1.9.8 | Missing QA training management | Phase 2, 5, 7, 8 |
| GAP-03 | **CRITICAL** | §1.9.6, §1.9.7 | Missing LSM role and 7-day rule | Phase 2, 6, 7 |
| GAP-04 | SIGNIFICANT | §1.9.9 | Missing non-disclosure form fields | Phase 2 |
| GAP-05 | SIGNIFICANT | §1.9.9 | Missing entry/exit meeting records | Phase 2, 5, 7, 8 |
| GAP-06 | SIGNIFICANT | §1.9.3, §1.9.8 | Missing dispatch/distribution tracking | Phase 2 |
| GAP-07 | SIGNIFICANT | §4.11.1.1 #4 | Missing historical data cross-refs | Phase 2 |
| GAP-08 | SIGNIFICANT | §4.11.1.1 #1 | Missing risk awareness sessions | Phase 2 (via GAP-01) |
| GAP-09 | SIGNIFICANT | Multiple | Incomplete notification mapping | Phase 9, 10 |
| GAP-10 | SIGNIFICANT | §1.9.9 | Missing audit timetable entity | Phase 2, 5, 7, 8 |
| GAP-11 | SIGNIFICANT | §1.9.7 | Missing comparative analysis API | Phase 7 |
| GAP-12 | MINOR | §4.11.1.1 #14 | Missing IAGO submission tracking | Phase 2 |
| GAP-13 | MINOR | §4.11.1.2 #3 | Missing RC qualification fields | Phase 2 |
| GAP-14 | MINOR | Multiple | Missing rework cycle counter | Phase 2 |
| GAP-15 | MINOR | §1.9.9 | Missing MRM directives tracking | Phase 2 or Phase 4 |
| GAP-16 | MINOR | §4.11.1.4 #14 | Missing monthly NC monitoring task | Phase 10 |
| GAP-17 | MINOR | Multiple | Missing review comment fields | Phase 2 |
| GAP-18 | MINOR | §1.9.5 | Missing endorsement confirmation | Phase 2 |
| GAP-NF-01 | MINOR | §1.5.6 | Missing caching strategy | Phase 1, 7 |
| GAP-NF-02 | MINOR | §1.5.8 | Missing retry mechanisms | Phase 4, 9 |

---

## Impact on Implementation Plan Totals

If all gaps are addressed, the revised plan totals would be:

| Metric | Current Plan | After Fix | Delta |
|--------|-------------|-----------|-------|
| Business Models | 20 | 26–28 | +6–8 |
| Lookup Tables | 6 | 6 | 0 |
| Service Classes | 8 | 8 | 0 |
| View Files | 14 | 17–18 | +3–4 |
| View Classes | ~80+ | ~95+ | +15 |
| Permission Classes | 24 | 27–28 | +3–4 |
| RBAC Roles | 5 | 6 | +1 (LSM) |
| Workflow Templates | 8 | 8 | 0 |
| API Endpoints | ~85+ | ~100+ | +15 |
| Celery Tasks | 1 | 2 | +1 |
| New Fields on Existing Models | 0 | ~20 | +20 |

---

## Recommended Action Plan

### Priority 1 — Critical Gaps (Address before implementation starts)
1. **GAP-01:** Design and add `RiskMeeting` + `MeetingAttendance` models with full CRUD
2. **GAP-02:** Design and add `QATrainingSession` + `QATrainingAttendee` models
3. **GAP-03:** Add LSM role to RBAC, add committee meeting date fields, implement 7-day validation

### Priority 2 — Significant Gaps (Address during Phase 2–7 implementation)
4. **GAP-04, GAP-05:** Add NDA fields and `AuditMeeting` model during QMS Audit model implementation
5. **GAP-06:** Add dispatch tracking fields to appointment models
6. **GAP-07:** Add `RiskReference` model or `references` JSONField to `RiskAssessmentSheet`
7. **GAP-08:** Extend `RiskMeeting` type choices from GAP-01
8. **GAP-09:** Create notification mapping table and define notification templates
9. **GAP-10:** Add `QMSAuditTimetableEntry` model
10. **GAP-11:** Add comparative analysis endpoint to dashboard views

### Priority 3 — Minor Gaps (Address during respective phase implementation)
11. **GAP-12 through GAP-18:** Add fields/tasks as described
12. **GAP-NF-01, GAP-NF-02:** Add caching and retry notes to Phase 1 and relevant service classes

---

*Once all Critical and Significant gaps are incorporated into the Implementation Plan, the plan will be fully aligned with the SRS and ready for confident execution.*
