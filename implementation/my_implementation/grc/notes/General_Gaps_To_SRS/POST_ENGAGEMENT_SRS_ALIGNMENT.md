# Post-Engagement Modules — SRS Alignment Analysis

**SRS Reference:** `AUDT2_ext.md`  
**Relevant SRS Sections:** §1.8.3 Conducting Internal Audit, §1.8.5 Reporting, §1.8.6 Monitoring, §4.10.1.4 Audit Implementation, General Requirements  
**Modules Covered:** Audit Findings · Audit Recommendations · Meetings · Audit Monitoring · Audit Reports · Quarterly Reports  
**Date:** 2026-03-16

---

## Modules Overview

| Module | Backend Model | View Files | Frontend Components | SRS Reference |
|--------|--------------|------------|---------------------|---------------|
| Audit Findings | `AuditFinding` | `audit_finding_views.py` | `AuditFindingDetailDialog`, `CreateAuditFindingDialog`, `FindingLifecycleDialog` | §1.8.3 Steps 7, 15, 18; Req 21, 28, 31-32 |
| Audit Recommendations | `AuditRecommendation` | `audit_recommendation_views.py` | `AuditRecommendationDetailDialog`, `CreateAuditRecommendationDialog` | §1.8.3 Steps 20, 25; Req 35, 38 |
| Meetings | `AuditMeeting` | `audit_meeting_views.py` | `AuditMeetingDetailDialog`, `CreateAuditMeetingDialog` | §1.8.3 Steps 14, 17, 20, 23-24; Req 27, 29-30, 33-34 |
| Implementation Monitoring | `ImplementationMonitoring` + `AuditeeFollowUpResponse` | `implementation_monitoring_views.py` | `AuditMonitoringDetailDialog`, `CreateAuditMonitoringDialog` | §1.8.6 Steps 1-7 |
| Audit Reports | `AuditReport` | `audit_report_views.py` | `AuditReportDetailDialog`, `CreateAuditReportDialog` | §1.8.3 Steps 21-26; Req 35-38 |
| Quarterly Reports | `QuarterlyAuditReport` | `audit_quarterly_report_views.py` | `QuarterlyReportDetailDialog`, `CreateQuarterlyReportDialog` | §1.8.5 Steps 1-7; Req 39 |

---

## Module 1: Audit Findings

### SRS Requirements

| Step/Req | SRS Text | Actor |
|----------|----------|-------|
| Step 7 | If controls are inadequate → include as audit finding; design impact tests | Audit Team |
| Step 15 | Team members perform tests, collect evidence, document in Working Paper, submit to LA | Audit Team |
| Step 18 | LA consolidates working paper forms (findings, results, observations) and submits for vetting | LA |
| Req 21 | System allows team members to include inadequate controls as findings, design impact tests | System |
| Req 28 | System enables team to perform tests, collect evidence, document in Working Papers, submit to LA | System |
| Req 31 | System allows team to prepare working paper forms and submit to LA for review | System |
| Req 32 | System facilitates CIA review and approval of working paper forms | CIA |
| Req 35a | System allows LA to set Risk scoring on findings | LA |

### ✅ Implemented and Aligned

| # | Feature | Notes |
|---|---------|-------|
| 1 | `AuditFinding` model — condition, criteria, cause, effect, risk_rating | Full 5-element finding structure |
| 2 | finding_type, severity FKs from lookup tables | Standardized classification |
| 3 | fiscal_year, quarter FKs | Quarter-scoped tracking |
| 4 | auditee_response, management_response fields | Records feedback from auditee |
| 5 | Status flow: `draft → discussed → final` | Simple lifecycle matching "discussed with auditee" step |
| 6 | Precondition: engagement must be in `fieldwork` or `reporting` phase | Prevents premature finding creation |
| 7 | Finalization blocked unless `auditee_response` is present | Enforces response before final |
| 8 | `working_paper` FK (optional) | Can link finding to its evidence working paper |
| 9 | `AuditFindingResponseView` — record auditee response separately | Dedicated endpoint |
| 10 | Risk scoring via `risk_rating` FK | Satisfies Req 35a |
| 11 | Frontend: Create, Edit, Detail, Finalize dialogs | Full CRUD |

### ❌ Gaps

#### GAP F1 — No WO Workflow for Findings/Working Papers CIA Approval (Req 31-32) 🔴 High

**SRS Requirement:**  
> *"The system shall allow the Audit Committee [team] to prepare working paper forms and submit to LA for review. The system shall facilitate the review and approval of working paper forms by the CIA."*

**What's implemented:** `WorkingPaper` has a WO workflow (`working_paper_review` → `working_paper_approval`). However, `AuditFinding` does **not** have a `WorkflowMixin` — findings have no WO integration. The approval chain exists for the **container** (WorkingPaper) but not for **individual findings**.

**Impact:** CIA formally approves the working paper document, but there's no granular per-finding CIA review step. If a finding is linked to an approved working paper, that implicitly satisfies the requirement — but this linkage is **optional**, not enforced.

**Gap detail:** A finding can be created and finalized (`draft → discussed → final`) entirely without being linked to any working paper. This means findings can exist without formal CIA-approved evidentiary backing.

**Fix:** Make `working_paper` FK on findings **required** (or at least add a validation that a `final` finding must have a linked `approved` working paper).

---

#### GAP F2 — Entry Meeting / EN Transmitted Not Checked Before Fieldwork Findings (Req 27) 🟡 Medium

**SRS Requirement:**  
> *"Dependencies: EN issued"* (before entry meeting and fieldwork begin)

**What's implemented:** Findings require `engagement.status in ['fieldwork', 'reporting']`. Engagement moves to `fieldwork` when EN is transmitted (this IS enforced via `EngagementNotificationService.transmit()`).

**Status:** Actually largely correct as-is — EN transmission is what moves engagement to `fieldwork`. But this is only safe if the EN transmission requirement is respected end-to-end. If the engagement phase is manually moved to `fieldwork` without EN, this check would pass incorrectly.

**Fix:** Ensure there is no direct `fieldwork` phase transition except via EN transmission (no shortcut manual transition allowed in `AuditEngagementPhaseTransitionView`). — **Verify this**.

---

## Module 2: Audit Recommendations

### SRS Requirements

| Step/Req | SRS Text | Actor |
|----------|----------|-------|
| Step 20 | LA arranges audit team meeting to consolidate deviations and recommendations | LA |
| Step 25 (Step 12 in reporting table) | LA prepares final report incorporating written responses from auditee | LA |
| Req 35 | LA prepares draft IAR and incorporates written responses from auditee | LA |
| Req 38 | System generates approved Audit Report and distributes to stakeholders | System |
| §1.8.6 | Monitoring of previous audit recommendations is ongoing | IA |

### ✅ Implemented and Aligned

| # | Feature | Notes |
|---|---------|-------|
| 1 | `AuditRecommendation` model — title, description, priority, agreed_action, target_date | Full structure |
| 2 | `responsible_party` UUID field | Tracks who is responsible |
| 3 | Status flow: `open → in_progress → implemented → verified → closed` | Full lifecycle |
| 4 | Precondition: finding must be `final` before recommendation can be created | Enforces proper ordering |
| 5 | `AuditRecommendationStatusUpdateView` — validates transitions | Prevents invalid jumps |
| 6 | `AuditRecommendationOverdueView` — lists overdue recommendations | Dashboard support |
| 7 | `ImplementationMonitoring` OneToOne links recommendation to monitoring cycles | Clean tracking model |
| 8 | Frontend: Create, Detail, Status Update dialogs | Full CRUD |

### ❌ Gaps

#### GAP R1 — No Formal Auditee Agreement on Recommendation 🟡 Medium

**SRS Requirement:**  
> *"Agreed corrective action plan"* — the `agreed_action` field exists, but there is no formal mechanism for the auditee to **accept/reject/dispute** a recommendation.

**What's missing:** During exit meeting, the auditee should formally agree to or dispute the recommendation. This agreement is currently just a free-text field (`agreed_action`) filled in by the auditor. There is no structured auditee acceptance step.

**Fix:** Add a `auditee_accepted` boolean + `auditee_accepted_date` field, and a dedicated endpoint for the auditee to formally accept/dispute. Or at minimum, note this is captured via meeting minutes (exit meeting `action_items`).

---

#### GAP R2 — No CIA Review Step on Recommendations Before Exit Meeting 🟠 Medium

**SRS Requirement:**  
> *Req 32: "The system shall facilitate the review and approval of working paper forms [containing findings/recommendations] by the CIA."*  
> *Step 22: "LA review the draft report, forward report to CIA for review and approval"*

**What's missing:** After LA consolidates findings and recommendations, CIA should review before the exit meeting. This is partially covered by the `AuditReport` CIA review step (CIA approves the report), but there is no **pre-report CIA review of raw recommendations**. If the Working Paper WO approval covers this, ensure the working paper must include a finding-recommendation linkage (which it currently doesn't enforce).

---

## Module 3: Meetings (AuditMeeting)

### SRS Requirements

| Step/Req | SRS Text | Actor |
|----------|----------|-------|
| Step 14 / Req 27 | LA arranges and conducts entry meeting; records attendance and proceedings | LA |
| Step 17 / Req 29-30 | LA and team conduct pre-exit meeting for clarification; document | LA |
| Step 20 / Req 33 | LA arranges audit team meeting prior to exit meeting | LA |
| Step 23 | LA arranges exit meeting — sends exit meeting notification with draft audit report | LA |
| Step 24 / Req 34 | LA conducts exit meeting, documents exit meeting minutes and attendance sheet | LA |
| Req 13 | System allows LA to schedule and record entry meetings, capture attendance and minutes | System |
| Entry Meeting Dep. | **Dependencies: EN issued** | — |
| Pre-exit Meeting Dep. | **Dependencies: Working papers reviewed** | — |

### ✅ Implemented and Aligned

| # | Feature | Notes |
|---|---------|-------|
| 1 | `AuditMeeting` with meeting types: `entry`, `pre_exit`, `team`, `exit` | All 4 SRS meeting types covered |
| 2 | `attendees` JSON field — user_id, name, title, role, present | Attendance register per SRS |
| 3 | `minutes`, `key_discussions` text fields | Meeting proceedings |
| 4 | `action_items` JSON field | Post-meeting actions tracked |
| 5 | `minutes_document_id`, `attendance_document_id` | DRS document references for signed sheets |
| 6 | `organized_by` UUID (typically LA) | Organizer tracking |
| 7 | Status flow: `scheduled → in_progress → completed → cancelled` | Lifecycle management |
| 8 | Phase preconditions per meeting type:<br>- entry: `planning\|fieldwork`<br>- pre_exit: `fieldwork\|reporting`<br>- exit: `reporting\|completed` | Prevents scheduling outside valid phases |
| 9 | Kafka event published on meeting scheduled | `MEETING_SCHEDULED` event |
| 10 | Frontend: Create, Detail, Status Update dialogs | Full CRUD + status management |

### ❌ Gaps

#### GAP MT1 — Entry Meeting Does Not Check EN Transmitted (Req 27, Dep. "EN issued") 🔴 High

**SRS Requirement:**  
> *"Dependencies: EN issued"* — entry meeting can only happen after the Engagement Notification has been formally sent to the auditee.

**What's implemented:** Entry meeting creation checks `engagement.status in ('planning', 'fieldwork')`. Since EN transmission moves engagement to `fieldwork`, this is partially correct.

**Why still a gap:** The `planning` phase is also allowed for entry meetings. A user could schedule an entry meeting while the engagement is still in `planning` (before EN is sent). 

**Fix:** Change entry meeting precondition to only allow `engagement.status == 'fieldwork'` (which is only set after EN is transmitted). This would be a 1-line fix in `MEETING_TYPE_ENGAGEMENT_PHASES`:

```python
# In audit_meeting_views.py
MEETING_TYPE_ENGAGEMENT_PHASES = {
    'entry':    ('fieldwork',),           # MUST be fieldwork (EN transmitted)
    'pre_exit': ('fieldwork', 'reporting'),
    'team':     ('fieldwork', 'reporting'),
    'exit':     ('reporting', 'completed'),
}
```

---

#### GAP MT2 — Exit Meeting Notification with Draft Report Not Sent (Step 23) 🔴 High

**SRS Requirement:**  
> *"LA arranges exit meeting by sending Exit meeting Notification including draft audit report to auditee, auditors and other personnel responsible for the finding."*

**What's implemented:** The `AuditMeeting` can be created (type=`exit`) and a Kafka `MEETING_SCHEDULED` event is published — but there is no attachment of the draft audit report to this notification, and there is no mechanism to send the draft report to the auditee.

**Impact:** Auditee has no formal advance notice with the draft findings before the exit meeting.

**Fix:** When scheduling an exit meeting (`meeting_type='exit'`), the view should:
1. Require an `audit_report_id` in the request (draft report to attach)
2. Publish a Kafka event `exit_meeting.notification_sent` that includes the draft report `document_id`
3. Optionally store `draft_report_id` on the meeting record

---

#### GAP MT3 — Pre-Exit Meeting Does Not Check Working Papers Reviewed (Req 29) 🟡 Medium

**SRS Requirement:**  
> *"Dependencies: Working papers reviewed"*

**What's implemented:** Pre-exit meeting allows `fieldwork` or `reporting` phase — no check on whether working papers have been reviewed/approved.

**Fix:** Add a check in the pre-exit meeting creation view: at least one `WorkingPaper` linked to the engagement must have `review_status='approved'` before a pre-exit meeting can be scheduled.

---

#### GAP MT4 — Meeting Minutes/Attendance Not Auto-Generated as PDF 🟡 Medium

**SRS Output:** Entry Meeting Minutes, Exit Meeting Minutes (listed under Process Output in §1.8.3).

**What's implemented:** `minutes_document_id` and `attendance_document_id` fields exist but must be manually set by uploading documents to DRS. There is no auto-generation of minutes as a PDF from the meeting record fields (minutes, attendees).

**Fix (lower priority):** On meeting status = `completed`, trigger DRS to generate a PDF from the meeting's `minutes`, `attendees`, and `key_discussions` fields, then store the returned `document_id`.

---

## Module 4: Implementation Monitoring

### SRS Requirements (§1.8.6 Steps 1–7)

| Step | SRS Text | Actor |
|------|----------|-------|
| 1 | IA identifies list of unimplemented previous audit recommendations | IA |
| 2 | IA shares list with auditee for updating status; sends notification | IA |
| 3 | Auditee responds within 5 days with evidence | Auditee |
| 4 | IA compiles implementation status from all auditees | IA |
| 5 | IA conducts review and analysis | IA |
| 6 | IA submits consolidated status report to CIA for final review | IA |
| 7 | CIA presents implementation status to Management Meeting for discussion and adoption | CIA |

### ✅ Implemented and Aligned

| # | Feature | Notes |
|---|---------|-------|
| 1 | `ImplementationMonitoring` header model (1:1 with recommendation) | Clean tracking entity |
| 2 | `AuditeeFollowUpResponse` cycle model (multiple cycles per monitoring) | Full cycle history |
| 3 | Cycle flow: open → notify → auditee submits → IA verifies → close/re-open | SRS Steps 2-5 |
| 4 | `ImplementationMonitoringNotifyAuditeeView` — sets 5-business-day deadline | SRS Step 2 / "five working days" ✅ |
| 5 | `response_deadline` computed using business-day math (`_add_business_days`) | SRS "five days" ✅ |
| 6 | `is_overdue` flag on both header and cycle | Deadline tracking |
| 7 | `escalated` boolean on header | CIA escalation hook |
| 8 | Kafka event `monitoring.auditee_notified` → delivers via event system | Email/in-app delivery |
| 9 | `ImplementationMonitoringNonResponsiveView` — lists non-responsive auditees | SRS "highlight late non-responsive auditees" |
| 10 | `AuditeeFollowUpResponseVerifyView` — IA verifies submitted evidence | SRS Step 5 |
| 11 | `implementation_progress` percent field per cycle | Quantitative tracking |
| 12 | `evidence_documents` JSON field on cycle | SRS "upload supporting evidence" |
| 13 | Frontend: Create monitoring, detail dialog with cycle management | Most of the UI is present |

### ❌ Gaps

#### GAP MON1 — No "IA Submits to CIA" Step (SRS Step 6) 🔴 High

**SRS Requirement:**  
> *"The system/process shall allow the Internal Auditor to: Submit the consolidated and analyzed implementation status report to the CIA."*

**What's implemented:** After verifying auditee responses, the IA can close the cycle. But there is no formal **"submit consolidated status to CIA"** action. The monitoring lifecycle ends at IA verification — there is no next step that hands off to CIA for final review.

**Fix:** Add a status field to `ImplementationMonitoring` with a transition `analysis_complete → submitted_to_cia`. Add `ImplementationMonitoringSubmitToCIAView` that records `submitted_to_cia_at` and publishes a Kafka event to notify CIA.

---

#### GAP MON2 — No CIA → Management Presentation Step (SRS Step 7) 🔴 High

**SRS Requirement:**  
> *"The system/process shall enable the CIA to: Present the implementation status report to the Management Meeting. Capture management discussions, decisions, and directives."*

**What's implemented:** Nothing. After CIA review, there is no "Management meeting" record for monitoring outcomes.

**Fix:** Either:
1. Link monitoring summaries to the Quarterly Report (which has a management review stage) — this is the simplest path, as the Quarterly Report's management review stage already captures management decisions.
2. Or add a dedicated `MonitoringManagementPresentation` record / extend the closest management meeting model.

**Recommendation:** Use option 1 — in the Quarterly Report's `implementation_status_summary` field, CIA fills in the monitoring outcomes. The management review of the quarterly report effectively covers SRS Step 7 for monitoring.

---

#### GAP MON3 — No Auto-Identification of "Outstanding Recommendations" from Approved Quarterly Reports 🟡 Medium

**SRS Requirement:**  
> *"The system shall allow Internal Auditors to identify and generate a list of unimplemented and partially implemented audit recommendations from previous audit reports."*  
> *"The system shall automatically filter recommendations based on implementation status."*

**What's implemented:** `ImplementationMonitoringListView` lists existing monitoring records, but the IA must **manually create** an `ImplementationMonitoring` record for each recommendation. There is no auto-scan that says: "here are all `open` or `in_progress` recommendations from **approved quarterly reports**" that don't yet have a monitoring record.

**Fix:** Add an endpoint `GET /implementation-monitoring/outstanding/` that returns all recommendations with `status in ['open', 'in_progress']` that have **no** linked `ImplementationMonitoring` record. This list becomes the IA's starting point for creating monitoring records.

---

#### GAP MON4 — Auditee Has No Portal to Submit Evidence 🔴 High (Architecture)

**SRS Requirement:**  
> *"The system/process shall enable auditees to: Update the status of each recommendation. Upload supporting evidence. Submit responses within five days."*

**What's implemented:** `AuditeeFollowUpResponseSubmitView` exists to record a submission — but who calls it? The staff portal is for internal users only. There is no **auditee-facing portal** where the auditee can log in and submit evidence.

**Current state:** This endpoint can only be called by an authenticated staff user on behalf of the auditee, which defeats the purpose of having the auditee self-report.

**Fix options:**
1. **Short-term:** Auditor submits on behalf of auditee (manual facilitation) — document this as a manual workaround.
2. **Long-term:** Expose a limited auditee-facing endpoint via the API Gateway that allows auditee users (from client-service) to submit monitoring responses. This requires cross-service authentication.

---

## Module 5: Audit Reports

### SRS Requirements

| Step/Req | SRS Text | Actor |
|----------|----------|-------|
| Step 21 | IA documents draft Internal Audit Report and submits to LA for review | IA |
| Step 22 | LA reviews draft, forwards to CIA for review and approval; authorizes LA for exit meeting | LA |
| Step 23 | LA arranges exit meeting — sends exit meeting notification with draft report | LA |
| Step 24 | LA conducts exit meeting, documents minutes | LA |
| Step 25 (12 in table) | LA prepares final report incorporating written auditee responses | LA |
| Step 26 (13 in table) | CIA reviews and approves final report for distribution | CIA |
| Req 35 | System allows preparation and review of draft audit reports | System |
| Req 36 | System enables IA and CIA review/approval of draft report | System |
| Req 37 | Upon approval, system facilitates printing, submittal letter, distribution | System |
| Req 38 | System generates Approved Internal Audit Report + Signed Declaration; distributes to stakeholders | System |

### ✅ Implemented and Aligned

| # | Feature | Notes |
|---|---------|-------|
| 1 | `AuditReport` model — executive_summary, scope_and_objectives, methodology, conclusion | Full narrative structure |
| 2 | `opinion` FK (`AuditOpinion` lookup) | Standardized audit opinion |
| 3 | `findings_summary`, `recommendations_summary` JSON fields | Aggregated content |
| 4 | Status flow: `draft → under_review → approved → distributed` | Matches SRS steps |
| 5 | `approved_by`, `approval_date` — CIA approval tracked | SRS Step 26 |
| 6 | `AuditReportDistributeView` — marks report as distributed with recipient list | SRS Req 37 |
| 7 | `distribution_list` field — JSON list of recipients | Req 38 distribution |
| 8 | `document_id`, `stamped_document_url` fields — DRS integration hooks | Future PDF generation |
| 9 | Precondition: engagement must be in `reporting` or `completed` phase | Correct ordering |
| 10 | `report_type` field (`draft` / `final`) | Tracks report maturity |
| 11 | Report locked in `approved` and `distributed` statuses — no further edits | Data integrity |
| 12 | Frontend: CreateAuditReportDialog, AuditReportDetailDialog | Full CRUD |

### ❌ Gaps

#### GAP AR1 — No WO Workflow Integration for Report Approval (Req 36) 🔴 High

**SRS Requirement:**  
> *"The system shall enable the review and approval of the draft report by the Internal Auditor and CIA."*

**What's implemented:** `AuditReport` has `WorkflowMixin` and `get_workflow_stages()` defining a 2-stage workflow (`ia_report_review` → `cia_report_approval`), but there is **no `submit-for-approval` URL endpoint** and no WO service integration. Status changes are via a simple manual `/update-status/` endpoint with no SLA tracking, no formal task assignment, and no audit trail in WO.

**Compare:** Quarterly reports have `QuarterlyReportSubmitView` → calls WO service. Audit reports do not.

**Fix:** Add `AuditReportSubmitView` that calls `PlanService.start_workflow()` with `report.get_workflow_stages()`, stores `workflow_plan_id` on the report, and blocks direct status transitions (as quarterly reports do).

---

#### GAP AR2 — No PDF Generation / DRS Stamping for Audit Report 🔴 High

**SRS Requirement:**  
> *"Upon approval, the system shall facilitate the arrangement of the final audit report."*  
> *"The system shall generate the Approved Internal Audit Report."* (Req 38)

**What's implemented:** `document_id` and `stamped_document_url` fields exist but are never populated automatically. There is no auto-generation of a PDF from report data, and no CIA signature + QR stamping on CIA approval (unlike Declaration and EN which both have this process).

**Fix:** Mirror the Declaration/EN pattern:
1. When report is submitted for approval → auto-generate a PDF in DRS from report fields → store `document_id`
2. When CIA approves → trigger DRS stamp (signature + QR) → store `stamped_document_url`
3. Add a "Download Report" button in frontend using `document_id` + DRS download endpoint

---

#### GAP AR3 — Exit Meeting Not Required Before Report Distribution (Step 23-24) 🟡 Medium

**SRS Requirement:**  
> *"Step 23-24: LA conducts exit meeting, documents minutes"* — this must happen before final report distribution.

**What's implemented:** `AuditReportDistributeView` checks `report.status == 'approved'` but does **not** check whether an exit meeting (type=`exit`, status=`completed`) exists for the engagement.

**Fix:** In `AuditReportDistributeView`, add a check:
```python
exit_meeting_exists = AuditMeeting.objects.filter(
    engagement=report.engagement,
    meeting_type='exit',
    status='completed'
).exists()
if not exit_meeting_exists:
    return Response({"error": "Exit meeting must be completed before report distribution"}, 400)
```

---

#### GAP AR4 — Auditee Written Response Not Formally Incorporated into Final Report (Step 25) 🟡 Medium

**SRS Requirement:**  
> *"LA prepares final report incorporating written responses from auditee."*

**What's implemented:** Individual `AuditFinding` records have `auditee_response` text fields. The `AuditReport` has `report_type` (`draft` / `final`) but no dedicated field for the consolidated auditee written response incorporated into the final report.

**Why matters:** The SRS process is: draft report → exit meeting → auditee sends written response → LA incorporates into final report. There is no formal "auditee written response received" gate before moving `report_type` from `draft` to `final`.

**Fix:** Add `auditee_response_incorporated` boolean + `auditee_response_date` field to `AuditReport`. When `report_type` is set to `final`, require confirmation that auditee responses have been incorporated.

---

## Module 6: Quarterly Reports

### SRS Requirements (§1.8.5)

| Step | SRS Text | Actor |
|------|----------|-------|
| 1 | CIA instructs Principal Internal Auditor (PIA) to consolidate engagement reports | CIA |
| 2 | PIA consolidates engagement reports into Quarterly reports, submits to CIA | PIA |
| 3 | CIA approves and submits quarterly report to Management for deliberation | CIA |
| 4 | Management adopts quarterly report | Management |
| 5 | CIA submits to Audit Committee for review and deliberation | CIA |
| 6 | If Audit Committee recommends improvement → CIA revises and resubmits | CIA |
| 7 | Audit Committee recommends to Commission for approval | Audit Committee |

### ✅ Implemented and Aligned

| # | Feature | Notes |
|---|---------|-------|
| 1 | `QuarterlyAuditReport` model with all narrative sections | Full content model |
| 2 | Status flow: `draft → cia_review → management_review → committee_review → improvement_required → approved → submitted_to_commission` | All 7 SRS steps mapped ✅ |
| 3 | `engagement_reports` M2M links to `AuditReport` records | Formal link to constituent reports |
| 4 | WO integration via `QuarterlyReportSubmitView` → WO service | Proper workflow tracking |
| 5 | `WO_MANAGED_TRANSITIONS` — blocks direct draft→cia_review without WO | Enforces WO path |
| 6 | `QuarterlyReportConsolidateView` — auto-populates stats from linked reports | `total_engagements`, `total_findings`, `implementation_rate` |
| 7 | `management_notes`, `committee_notes` fields | Records deliberation notes |
| 8 | `instructed_by` field — tracks CIA who initiated | |
| 9 | Preconditions before management review: linked reports + executive summary required | Data quality gate |
| 10 | `submission_date` required when submitting to commission | |
| 11 | Frontend: CreateQuarterlyReportDialog, QuarterlyReportDetailDialog, status controls | Full UI |
| 12 | Aggregated statistics: `total_engagements`, `total_findings`, `critical_findings`, `implementation_rate` | |
| 13 | `risk_themes` JSON field | Trend analysis |

### ❌ Gaps

#### GAP QR1 — No Formal CIA Instruction Record to PIA (SRS Step 1) 🟡 Medium

**SRS Requirement:**  
> *"The system/process shall allow the CIA to: Issue a formal instruction to the Principal Internal Auditor (PIA) to consolidate Engagement Audit Reports. Define the reporting period (quarter)."*

**What's implemented:** `instructed_by` field captures which CIA initiated the report, but any user can create a quarterly report. There is no explicit "CIA issues formal instruction" step before report creation — it's just creation.

**Fix:** Add a permission check on `QuarterlyReportListCreateView.post()` requiring the creator to have `grc:quarterly_report:approve` (CIA permission). This ensures only CIA can create/initiate quarterly reports, which implicitly enforces CIA instruction.

---

#### GAP QR2 — No PIA Role Distinction (SRS Step 2) 🟠 Medium

**SRS Requirement:**  
> *"Principal Internal Auditor (PIA) consolidates engagement reports into Quarterly reports and submits to CIA."*

**What's implemented:** No PIA role in the system — any auditor (or CIA) can prepare quarterly reports.

**Status:** This is partly an IAM/role-configuration issue. The SRS PIA role needs to be mapped to a system permission (e.g., `grc:quarterly_report:prepare`) that distinguishes PIA from regular auditors.

**Fix:** Define a `principal_internal_auditor` role in IAM and restrict quarterly report creation/edit to users with this role.

---

#### GAP QR3 — Management Meeting Not Formally Linked (SRS Step 4) 🟡 Medium

**SRS Requirement:**  
> *"The system/process shall: Record Management discussions and decisions. Capture adoption or required actions arising from Management deliberation."*

**What's implemented:** `management_notes` text field captures notes entered during `management_review` stage. No formal Management Meeting record (like `AuditMeeting`) associated with the quarterly report review.

**Status:** The `management_notes` field is a reasonable workaround. A fully SRS-compliant implementation would link to a formal meeting record. This is **low priority** unless the client specifically requests meeting-level traceability for management review.

---

#### GAP QR4 — Commission Submission Not Integrated with Commission Management Service 🟠 Medium

**SRS Requirement:**  
> *"Audit Committee recommends the approved report to the Commission."*

**What's implemented:** Quarterly report reaches `submitted_to_commission` status and `submitted_to` / `submission_date` fields are recorded. But there is **no API call to the Commission Management microservice** to formally submit the report there.

**Fix:** When transitioning to `submitted_to_commission`, publish a Kafka event `quarterly_report.submitted_to_commission` that the Commission Management service can consume to create a Commission agenda item.

---

## Cross-Module Communication Gaps

These gaps span multiple modules and affect the overall audit lifecycle flow.

### GAP CROSS1 — Findings/Recommendations Not Linked to Quarterly Report Aggregation 🟡 Medium

**What's expected:** Quarterly Report stats (`total_findings`, `critical_findings`, `total_recommendations`) should auto-calculate from all findings and recommendations of constituent engagement reports.

**What's implemented:** `QuarterlyReportConsolidateView` attempts to populate stats from linked `AuditReport.findings_summary` and `recommendations_summary` JSON fields — but these JSON fields are manually written by the preparer, not auto-populated from the actual `AuditFinding` and `AuditRecommendation` model records.

**Fix:** In `QuarterlyReportConsolidateView`, query `AuditFinding` and `AuditRecommendation` directly through the linked engagement reports chain:
```
QuarterlyReport → AuditReport.engagement_reports → AuditEngagement → AuditFinding → AuditRecommendation
```
Auto-populate counts from actual model records, not from manual JSON summaries.

---

### GAP CROSS2 — Monitoring Not Formally Linked to Quarterly Reports 🟡 Medium

**SRS §1.8.6:**  
> *"Pre-Conditions: Approved previous quarterly report."* — monitoring should operate on recommendations from approved quarterly reports specifically.

**What's implemented:** `ImplementationMonitoring` is linked to `AuditRecommendation` → `AuditFinding` → `AuditEngagement`, but there is no direct link to the specific `QuarterlyAuditReport` from which those recommendations came.

**Impact:** The monitoring module cannot easily answer "which quarterly report do these monitored recommendations belong to?" — which breaks the SRS traceability requirement.

**Fix:** Add a `quarterly_report` FK (nullable) to `ImplementationMonitoring` populated when monitoring is created from a specific quarterly report context.

---

### GAP CROSS3 — Working Paper Must Link to Finding Must Link to Report (Chain Integrity) 🟡 Medium

**SRS flow:**  
Working Paper submitted → CIA approved → Finding becomes final → Included in Draft Report → Exit meeting → Final Report → Quarterly Report

**Current issue:** Each linkage in this chain is **optional** or weakly enforced:
- `AuditFinding.working_paper` — optional FK
- `AuditReport.findings_summary` — manually populated JSON, not auto-linked from `AuditFinding`
- `QuarterlyAuditReport.engagement_reports` — manually linked M2M

**Fix:** At each status gate, add precondition checks for the chain:
1. Finding can only be `final` if its `working_paper` is `approved` (or working paper is explicitly waived)
2. `AuditReport` "Submit for approval" should require at least one `final` finding linked to the engagement
3. `QuarterlyReport` "Submit for approval" should require all linked `AuditReport` records to be `approved`

---

## Summary Table: All Gaps by Priority

| Gap ID | Module | Gap Description | Priority | Fix Complexity |
|--------|--------|-----------------|----------|----------------|
| GAP AR1 | Audit Reports | No WO workflow integration (no submit-for-approval) | 🔴 High | Medium |
| GAP AR2 | Audit Reports | No PDF generation / DRS stamping | 🔴 High | High |
| GAP MT1 | Meetings | Entry meeting allows `planning` phase (before EN transmitted) | 🔴 High | Low (1 line) |
| GAP MT2 | Meetings | Exit meeting notification with draft report not sent | 🔴 High | Medium |
| GAP MON1 | Monitoring | No "IA submits to CIA" step | 🔴 High | Medium |
| GAP MON2 | Monitoring | No CIA → Management presentation step | 🔴 High | Low (use QR) |
| GAP MON4 | Monitoring | Auditee has no portal to submit evidence | 🔴 High | High (architecture) |
| GAP F1 | Findings | Working paper link not enforced before finalization | 🟡 Medium | Low |
| GAP F2 | Findings | Manual phase bypass risk (fieldwork without EN) | 🟡 Medium | Low |
| GAP R1 | Recommendations | No formal auditee agreement on recommendation | 🟡 Medium | Low |
| GAP R2 | Recommendations | No pre-report CIA review of raw recommendations | 🟡 Medium | Low |
| GAP MT3 | Meetings | Pre-exit meeting doesn't check working papers reviewed | 🟡 Medium | Low |
| GAP MT4 | Meetings | Meeting minutes not auto-generated as PDF | 🟡 Medium | Medium |
| GAP AR3 | Audit Reports | Exit meeting not required before distribution | 🟡 Medium | Low |
| GAP AR4 | Audit Reports | Auditee written response not formally incorporated | 🟡 Medium | Low |
| GAP QR1 | Quarterly Reports | No formal CIA instruction to PIA | 🟡 Medium | Low (permission check) |
| GAP QR2 | Quarterly Reports | No PIA role distinction | 🟠 Medium | IAM config |
| GAP QR3 | Quarterly Reports | Management meeting not formally linked | 🟡 Medium | Low (workaround acceptable) |
| GAP QR4 | Quarterly Reports | Commission submission not integrated | 🟠 Medium | Medium |
| GAP MON3 | Monitoring | No auto-scan for "outstanding recommendations" | 🟡 Medium | Low |
| GAP CROSS1 | Cross | Findings/Recs not auto-linked to QR stats | 🟡 Medium | Medium |
| GAP CROSS2 | Cross | Monitoring not linked to Quarterly Reports | 🟡 Medium | Low |
| GAP CROSS3 | Cross | Working paper → finding → report chain not enforced | 🟡 Medium | Low-Medium |

---

## Recommended Fix Order

### Phase 1: Quick Wins (1-line fixes + low effort)

1. **GAP MT1** — Change entry meeting allowed phase from `planning|fieldwork` to `fieldwork` only (1 line in `audit_meeting_views.py`)
2. **GAP AR3** — Add exit meeting check in `AuditReportDistributeView` (5 lines)
3. **GAP F1** — Require `working_paper` to be linked and approved before finding can be `final` (few lines in `AuditFindingFinalizeView`)
4. **GAP QR1** — Add CIA permission check on quarterly report creation
5. **GAP MON3** — Add `GET /implementation-monitoring/outstanding/` endpoint

### Phase 2: Workflow Completeness

6. **GAP AR1** — Add WO workflow integration for Audit Reports (clone from quarterly report pattern)
7. **GAP MON1** — Add `submit_to_cia` action on `ImplementationMonitoring`
8. **GAP MON2** — Link monitoring CIA presentation to Quarterly Report management review (document as formal process)
9. **GAP MT2** — Exit meeting notification: require draft audit report attachment; publish enriched Kafka event
10. **GAP MT3** — Pre-exit meeting: require at least one approved working paper

### Phase 3: Document Generation

11. **GAP AR2** — PDF auto-generation for Audit Report (clone from EN/Declaration pattern via DRS)
12. **GAP MT4** — Meeting minutes PDF auto-generation

### Phase 4: Cross-Module Integrity

13. **GAP CROSS1** — Fix quarterly report consolidation to pull from actual model records
14. **GAP CROSS2** — Add `quarterly_report` FK to `ImplementationMonitoring`
15. **GAP CROSS3** — Enforce chain integrity gates at key status transitions

### Phase 5: Architecture (Long-term)

16. **GAP MON4** — Auditee submission portal (cross-service authentication)
17. **GAP QR2** — PIA role in IAM
18. **GAP QR4** — Commission Management service integration

---

## What's Correctly Implemented (Overall Summary)

Despite the gaps above, the following is correctly and fully implemented across all 6 modules:

- ✅ All 6 core models with appropriate fields, FKs, and status flows
- ✅ Full CRUD API endpoints for all modules
- ✅ Role-based permission checks on all write operations
- ✅ Status transition validation (no invalid jumps)
- ✅ Phase preconditions linking modules together (engagement phase gates)
- ✅ Kafka event publishing for most state changes
- ✅ WO integration for: Audit Universe, Audit Plan, Audit Engagement, Working Papers, Quarterly Reports
- ✅ Implementation monitoring with 5-day deadline enforcement and cycle-based tracking
- ✅ All 4 meeting types with proper phase gates
- ✅ Full frontend coverage (Create + Detail + Status dialogs for all modules)
- ✅ Audit findings properly linked to Working Papers (optional but available)
- ✅ Recommendation → Monitoring → FollowUp cycle chain fully implemented
- ✅ Quarterly report consolidation with stats aggregation
- ✅ Report distribution to recipient list

---

## Actor Flow Analysis — Who Starts, Who Follows (SRS vs. Implementation)

This section maps the complete SRS actor sequence to what is actually enforced in the system. Use this as your checklist when implementing fixes.

### Full Audit Lifecycle Flow Table

| # | Phase | SRS Actor | SRS Action | Permission Used | Correct? |
|---|-------|-----------|------------|-----------------|----------|
| 1 | Planning | IA | Creates Audit Universe → submits to CIA | `grc:audit_universe:manage` | ✅ |
| 2 | Planning | CIA | Reviews and approves Audit Universe | `grc:audit_universe:approve` | ✅ |
| 3 | Planning | IA | Conducts Risk Assessment, scores risks | `grc:risk_assessment:conduct` | ✅ |
| 4 | Planning | CIA | Reviews Risk Assessment | `grc:risk_assessment:review` | ✅ |
| 5 | Planning | IA | Drafts Audit Plan → submits to CIA | `grc:audit_plan:manage` | ✅ |
| 6 | Planning | CIA → Mgmt → Committee → Commission | 4-stage RBIAP approval | WO 4-stage workflow | ✅ |
| 7 | Engagement | CIA | Appoints LA + team via Audit Memo | `grc:audit_memo:manage` (CIA initiates) | ✅ |
| 8 | Engagement | LA | Prepares Audit Memo → submits (CIA reviews → DG approves) | 2-stage WO: CIA review → DG approval | ✅ |
| 9 | Engagement | Each team member | Reviews plan → signs Declaration of Independence | Each member signs individually | ✅ |
| 10 | Survey | Audit Team | Preliminary survey + Fraud Risk Assessment | `AuditSurvey` by team | ✅ |
| 11 | Survey | LA | Develops Risk and Control Matrix | `RiskControlMatrix` + `RCMEntry` | ✅ |
| 12 | Survey | LA | Prepares Audit Program → submits for approval | WO 2-stage: IA review → CIA approval | ✅ |
| 13 | Survey | LA | Prepares EN → CIA approves → LA transmits | WO 1-stage CIA approval; LA transmits | ✅ |
| 14 | Fieldwork | LA | Arranges Entry Meeting **after EN transmitted** | Entry meeting allows `planning` OR `fieldwork` | ⚠️ **Too early — see FIX-1** |
| 15 | Fieldwork | Audit Team | Performs tests → documents in Working Papers → submits to LA | `grc:audit_working_paper:manage` | ✅ |
| 16 | Fieldwork | LA | Reviews Working Papers → arranges Pre-Exit Meeting | LA has `working_paper:review` | ✅ |
| 17 | Fieldwork | LA → CIA | Consolidates WP forms → CIA approves | WO 2-stage: LA review → CIA approval | ✅ |
| 18 | Fieldwork | LA | Arranges Audit Team Meeting (internal, before exit) | `AuditMeeting(type=team)` | ✅ |
| 19 | Reporting | IA | Documents Draft Internal Audit Report | `grc:audit_report:view` (too broad — see FIX-2) | ⚠️ **Wrong perm** |
| 20 | Reporting | LA → CIA | Draft report: LA reviews → CIA approves | Workflow defined in model but **WO never invoked** | ❌ **No WO — FIX-2** |
| 21 | Reporting | LA | Sends Exit Meeting notification **with draft report** | Exit meeting scheduled, **no draft report attached** | ❌ **Missing — FIX-3** |
| 22 | Reporting | LA | Conducts Exit Meeting; records minutes + attendance | `AuditMeeting(type=exit)` | ✅ |
| 23 | Reporting | LA | Prepares Final Report (incorporating auditee responses) | `report_type: final` field exists | ⚠️ **Not enforced — see FIX-2** |
| 24 | Reporting | CIA | Approves Final Report → distributes to stakeholders | `grc:audit_report:approve` for approve + distribute | ✅ |
| 25 | Quarterly | CIA | Instructs PIA to consolidate reports | `grc:quarterly_report:manage` — any manager can create | ⚠️ **No CIA-only gate — FIX-4** |
| 26 | Quarterly | PIA/CIA | Consolidates engagement reports → submits to CIA | `QuarterlyReportConsolidateView` | ✅ (PIA role unenforced) |
| 27 | Quarterly | CIA → Mgmt → Committee → Commission | 4-stage WO workflow | Full WO integration | ✅ |
| 28 | Monitoring | IA | Identifies outstanding recs → opens cycle → notifies auditee | `grc:audit_monitoring:update`, 5-day deadline | ✅ |
| 29 | Monitoring | Auditee | Responds within 5 days with evidence | API endpoint exists but **no auditee portal** | ❌ **Architecture — FIX-5** |
| 30 | Monitoring | IA | Compiles, analyzes, verifies evidence | `AuditeeFollowUpResponseVerifyView` | ✅ |
| 31 | Monitoring | IA → CIA | IA submits consolidated status report **to CIA** | ❌ Flow ends at IA — no handoff to CIA | ❌ **Missing — FIX-6** |
| 32 | Monitoring | CIA | Presents implementation status to Management Meeting | ❌ Not implemented | ❌ **Missing — FIX-7** |

---

### The 4 Critical Flow Breaks

#### FIX-1 — Entry Meeting Phase Gate (Step 14) 🔴 One-Line Fix

**Problem:** `MEETING_TYPE_ENGAGEMENT_PHASES['entry']` allows both `('planning', 'fieldwork')`. The SRS dependency is *"EN issued"*, and EN transmission is precisely what moves engagement to `fieldwork`. Allowing `planning` means an entry meeting can be scheduled before EN is sent.

**File:** `grc-service/apps/api/views/audit_meeting_views.py`

```python
# CURRENT (wrong — allows before EN is sent):
MEETING_TYPE_ENGAGEMENT_PHASES = {
    'entry':    ('planning', 'fieldwork'),
    ...
}

# CORRECT (fixes to SRS — fieldwork only = EN has been transmitted):
MEETING_TYPE_ENGAGEMENT_PHASES = {
    'entry':    ('fieldwork',),
    ...
}
```

---

#### FIX-2 — Audit Report Has No WO Workflow + Wrong Creation Permission (Steps 19-20) 🔴

**Problem 1 — Wrong creation permission:**  
Report creation requires `grc:audit_report:view`. This means any user who can view reports can create one. SRS says IA/LA creates the draft. Needs a dedicated `grc:audit_report:manage` permission for creating/editing, and `grc:audit_report:approve` only for approve + distribute.

**Problem 2 — No WO integration:**  
`AuditReport` has `WorkflowMixin` and `get_workflow_stages()` (2-stage: `ia_report_review` → `cia_report_approval`) but there is **no** `/submit-for-approval/` endpoint and no WO service call. Status transitions happen via a simple manual `/update-status/` call with no SLA, no task assignment, no WO audit trail. Compare with `QuarterlyReport` which has `QuarterlyReportSubmitView`.

**Files to change:**
- `grc-service/apps/api/views/audit_report_views.py` — add `AuditReportSubmitView`, add WO-managed transition block
- `grc-service/apps/api/permissions_jwt.py` — add `CanManageAuditReport` class
- `grc-service/apps/api/urls/audit.py` — register new submit URL

**Pattern to follow:** Copy `QuarterlyReportSubmitView` from `audit_quarterly_report_views.py` — it is identical in structure.

---

#### FIX-3 — Exit Meeting Must Carry Draft Report (Step 21) 🔴

**Problem:** SRS Step 21/23:
> *"LA arranges exit meeting by sending Exit meeting Notification including draft audit report to auditee."*

When scheduling an exit meeting (`meeting_type='exit'`), the system publishes `MEETING_SCHEDULED` but does not:
1. Require a draft `AuditReport` to be linked
2. Attach the report to the notification payload
3. Send the draft to the auditee

**File:** `grc-service/apps/api/views/audit_meeting_views.py`

**What to add in the `post()` method when `meeting_type == 'exit'`:**
```python
# Require a draft audit report to be linked when scheduling exit meeting
if meeting_type == 'exit':
    audit_report_id = request.data.get('audit_report_id')
    if not audit_report_id:
        return Response({"error": "audit_report_id is required for exit meetings"}, 400)
    # Validate report exists and belongs to this engagement + is in draft/under_review
    # Store on meeting record (add audit_report FK field to AuditMeeting model)
    # Include document_id in Kafka payload so notification service attaches it
```

Also add `audit_report` FK (nullable) to `AuditMeeting` model.

---

#### FIX-4 — Quarterly Report: Only CIA Should Create/Initiate (Step 25) 🟡

**Problem:** Any user with `grc:quarterly_report:manage` can create a quarterly report. SRS says CIA formally instructs the process. The `instructed_by` field exists but is not enforced.

**File:** `grc-service/apps/api/views/audit_quarterly_report_views.py`

```python
# In QuarterlyReportListCreateView.post():
# Change: from CanManageQuarterlyReport to CanApproveQuarterlyReport for creation
if not CanApproveQuarterlyReport().has_permission(request, self):
    self.permission_denied(request, message='Only CIA (grc:quarterly_report:approve) can initiate quarterly reports.')
```

---

#### FIX-5 — Auditee Submission Portal (Step 29) 🔴 Architecture

**Problem:** `AuditeeFollowUpResponseSubmitView` exists to record auditee evidence submission, but the staff portal is for internal users only. No auditee-facing access.

**Short-term workaround:** Internal auditor submits on behalf of auditee (manual facilitation). Document this as accepted behavior.

**Long-term fix:** Expose a limited API Gateway route for auditee users (from `client-service`) to authenticate and call the follow-up response endpoint. Requires cross-service JWT validation using the IAM service.

---

#### FIX-6 + FIX-7 — Monitoring CIA Handoff + Management Presentation (Steps 31-32) 🔴

**Problem:** After IA verifies implementation evidence, the monitoring cycle just closes. No formal CIA review step. No Management presentation record.

**What to add:**

**FIX-6 — IA → CIA handoff:**  
Add status transition to `ImplementationMonitoring`:
- New status: `submitted_to_cia` (after IA analysis is complete)
- New view: `ImplementationMonitoringSubmitToCIAView` — IA calls this to hand off; publishes Kafka event to notify CIA
- CIA acknowledges via existing monitoring update endpoint

**FIX-7 — CIA → Management (via Quarterly Report):**  
The simplest correct approach: the `QuarterlyAuditReport.implementation_status_summary` field is where CIA records the monitoring outcomes before management review. The 4-stage quarterly report workflow (which includes management review) **already covers** SRS Step 32 if CIA fills this field correctly.

Add a precondition to `QuarterlyReport` management review stage: require `implementation_status_summary` to be non-empty before advancing to `management_review`.

---

### Correct Flow After All Fixes

```
IA → AuditUniverse → CIA approves
IA → RiskAssessment → CIA reviews
IA → AuditPlan → [CIA → Mgmt → Committee → Commission] (WO)
CIA → AuditMemo (appoints LA) → [CIA → DG approves] (WO)
Team → Declaration of Independence (each signs)
Team → AuditSurvey + RCM
LA → AuditProgram → [IA review → CIA approves] (WO)
LA → EN → [CIA approves] (WO) → LA transmits EN
                ↓
        engagement → fieldwork phase
                ↓
LA → Entry Meeting (type=entry, fieldwork phase only) ← FIX-1
Team → WorkingPapers → [LA review → CIA approves] (WO)
LA + Team → Pre-Exit Meeting (requires at least 1 approved WP)
LA → Audit Team Meeting (internal)
IA → Draft AuditReport
LA reviews → CIA approves (WO — submit-for-approval) ← FIX-2
                ↓
LA → Exit Meeting notification (draft report attached) ← FIX-3
LA → Exit Meeting (type=exit, reporting phase)
LA → Final AuditReport → CIA approves → CIA distributes
                         ↓
CIA → QuarterlyReport (CIA initiates only) ← FIX-4
[CIA → Mgmt (+ implementation_status_summary) → Committee → Commission] (WO)
                ↓
IA → ImplementationMonitoring → auditee notified (5 days)
Auditee → submits evidence ← FIX-5 (portal needed)
IA → verifies → IA submits to CIA ← FIX-6
CIA → fills implementation_status_summary in QuarterlyReport ← FIX-7
```

---

### Fix Priority Order (Start Here)

| Order | Fix | File | Effort | Impact |
|-------|-----|------|--------|--------|
| 1 | **FIX-1** Entry meeting phase gate | `audit_meeting_views.py` | 1 line | High |
| 2 | **FIX-4** Quarterly report CIA-only creation | `audit_quarterly_report_views.py` | 2 lines | Medium |
| 3 | **FIX-2** Audit Report WO integration | `audit_report_views.py` + `permissions_jwt.py` + `urls/audit.py` | ~80 lines | High |
| 4 | **FIX-6** Monitoring IA→CIA submit step | `implementation_monitoring_views.py` | Medium | High |
| 5 | **FIX-3** Exit meeting + draft report | `audit_meeting_views.py` + `AuditMeeting` model | Medium | High |
| 6 | **FIX-7** Quarterly report implementation_status_summary gate | `audit_quarterly_report_views.py` | Low | Medium |
| 7 | **FIX-5** Auditee portal | Cross-service architecture | Very High | High |
