# Quarterly Internal Audit Reporting — SRS Alignment Checklist

**Document Purpose:** Track implementation gaps between SRS requirements and current codebase for Quarterly Internal Audit Reports (SRS 1.8.5).

**Model:** `QuarterlyAuditReport` (apps/core/models/audit_entities.py)  
**Views:** `apps/api/views/audit_quarterly_report_views.py`  
**Serializers:** `apps/api/serializers/audit_serializers.py`  

---

## ✅ IMPLEMENTED REQUIREMENTS

### Process & Workflow
- [x] CIA review stage — workflow status `cia_review`
- [x] Management review stage — workflow status `management_review`
- [x] Committee review stage — workflow status `committee_review`
- [x] Improvement required stage — workflow status `improvement_required`
- [x] Approved stage — workflow status `approved`
- [x] Submitted to Commission stage — workflow status `submitted_to_commission`
- [x] Valid transitions between stages enforced via `VALID_QUARTERLY_TRANSITIONS` map
- [x] Ability to return report for improvement (transition `improvement_required → cia_review`)

### Data & Consolidation
- [x] Unique constraint on `(fiscal_year, quarter)` — one report per quarter
- [x] Many-to-many link to `AuditReport` objects (field: `engagement_reports`)
- [x] Consolidation endpoint gathers approved engagement reports within reporting period
- [x] Auto-calculation of aggregated statistics:
  - [x] `total_engagements` — distinct count of engagement IDs from linked reports
  - [x] `total_findings` — sum across all linked engagement reports
  - [x] `critical_findings` — count of high/critical severity findings
  - [x] `total_recommendations` — sum of recommendations across engagements
  - [x] `implementation_rate` — percentage of prior recommendations implemented
- [x] Structured JSON summaries:
  - [x] `planned_vs_actual` — engagement plan vs completion variance
  - [x] `findings_summary` — aggregated findings by severity
  - [x] `recommendations_summary` — aggregated recommendations by status
  - [x] `resource_utilization` — staffing and budget metrics

### Narrative Sections
- [x] `executive_summary` — High-level overview for leadership
- [x] `audit_activities_summary` — Summary of activities conducted
- [x] `findings_overview` — Narrative of key findings
- [x] `risk_themes` — Identified risk themes/trends (JSON)
- [x] `recommendations_overview` — Aggregated recommendations narrative
- [x] `implementation_status_summary` — Status of prior recommendations
- [x] `key_achievements` — Significant milestones during quarter
- [x] `challenges_and_constraints` — Resource/operational obstacles
- [x] `next_quarter_plan` — Planned audit activities for next quarter
- [x] `conclusion` — Overall conclusion and audit opinion

### Review & Approval Tracking
- [x] `instructed_by` field — User ID of CIA who instructed preparation
- [x] `prepared_by` field — User ID of report preparer
- [x] `reviewed_by` field — User ID of reviewer
- [x] `approved_by` field — User ID of approver
- [x] `approval_date` field — Timestamp of approval
- [x] `management_notes` field — Management deliberation notes
- [x] `committee_notes` field — Committee review notes
- [x] `submission_date` field — Date report was submitted
- [x] `submitted_to` field — Name/title of recipient (e.g., "Audit Commission")
- [x] `document_id` field — Reference to uploaded document in Document Records Service

### API Endpoints
- [x] List quarterly reports — GET `/api/v1/grc/audit/quarterly-reports/`
- [x] Create quarterly report — POST `/api/v1/grc/audit/quarterly-reports/`
- [x] Retrieve detail — GET `/api/v1/grc/audit/quarterly-reports/{pk}/`
- [x] Update (full) — PUT `/api/v1/grc/audit/quarterly-reports/{pk}/`
- [x] Partial update — PATCH `/api/v1/grc/audit/quarterly-reports/{pk}/`
- [x] Soft-delete (draft only) — DELETE `/api/v1/grc/audit/quarterly-reports/{pk}/`
- [x] Status transitions — POST `/api/v1/grc/audit/quarterly-reports/{pk}/update-status/`
- [x] Consolidate reports — POST `/api/v1/grc/audit/quarterly-reports/{pk}/consolidate/`
- [x] Manual link engagement reports — POST `/api/v1/grc/audit/quarterly-reports/{pk}/engagement-reports/`
- [x] Manual unlink engagement reports — DELETE `/api/v1/grc/audit/quarterly-reports/{pk}/engagement-reports/`

### Permissions & Access Control
- [x] Permission `grc:quarterly_report:manage` — required to create, update, manage reports
- [x] Permission `grc:quarterly_report:approve` — required to approve and submit to commission
- [x] Enforce manage permission on list, create, detail, update views
- [x] Enforce approve permission when transitioning to `approved` or `submitted_to_commission`

### Business Rules
- [x] Report locked after submission to commission (cannot update)
- [x] Draft-only reports can be deleted (soft-delete via `is_active=False`)
- [x] Require at least one linked engagement report before advancing to management_review
- [x] Require executive summary before advancing to management_review
- [x] Require `submission_date` when transitioning to submitted_to_commission
- [x] Capture notes/reasons during workflow transitions

### System Integration
- [x] Publish audit events on create, update, status change, approval, submission
- [x] Event types: `quarterly_report.created`, `quarterly_report.updated`, `quarterly_report.approved`, `quarterly_report.submitted`
- [x] Messaging service integration via `apps/infrastructure/services/messaging_service.py`

---

## ⚠️ MISSING / INCOMPLETE REQUIREMENTS

### 1. Formal Instruction Process
**SRS Requirement:** "CIA issues a formal instruction to the Principal Internal Auditor (PIA) to consolidate Engagement Audit Reports."

**Current Status:** 
- Model has `instructed_by` field but it is only set during report creation (no dedicated instruction action).
- No separate workflow step for "instruction" before PIA begins consolidation.
- No enforcement that `instructed_by` is populated by a user with CIA role.

**What's Missing:**
- [ ] Dedicated API endpoint for CIA to issue consolidation instruction (e.g., POST `.../issue-instruction/`)
- [ ] Separate status for "instruction issued" if needed (or explicit business rule that only CIA-issued reports can proceed)
- [ ] Validation that `instructed_by` is set and is a CIA user before consolidation is allowed
- [ ] Notification/event sent to PIA when instruction is issued

---

### 2. Reporting Period Validation
**SRS Requirement:** "Define the reporting period (quarter)" — system should validate that supplied dates align with the selected quarter.

**Current Status:**
- `reporting_period_start` and `reporting_period_end` are accepted from user without validation against the selected quarter.
- No automatic generation of period dates from quarter lookup table.

**What's Missing:**
- [ ] Validate that `reporting_period_start` matches quarter start date (or is within valid range)
- [ ] Validate that `reporting_period_end` matches quarter end date (or is within valid range)
- [ ] Auto-populate `reporting_period_start` and `reporting_period_end` from `quarter` object when report is created
- [ ] Reject reports with mismatched period dates

---

### 3. Structured Meeting Minutes & Audit Committee Meeting Link
**SRS Requirement:** "Record Management discussions and decisions" and "Track review status and committee feedback."

**Current Status:**
- Only free-text `management_notes` and `committee_notes` fields exist
- No structured data for attendees, resolutions, action items
- No explicit link to `AuditMeeting` model for documented proceedings

**What's Missing:**
- [ ] Link to `AuditMeeting` for management deliberation meeting (FK or M2M)
- [ ] Link to `AuditMeeting` for committee review meeting
- [ ] Structured meeting data (attendees, date, resolutions) captured via meeting minutes
- [ ] Business rule requiring meeting minutes before notes can be recorded
- [ ] Audit trail of who recorded notes and when

---

### 4. Engagement Report Status Filtering
**SRS Requirement:** "All completed engagement reports within the reporting period shall be consolidated into a single quarterly report."

**Current Status:**
- Consolidation includes reports with status `approved` (and optionally `distributed`)
- No explicit check that underlying `engagement` is in a "completed" state
- Query filters by `engagement__planned_start_date` and `engagement__planned_end_date` but not actual completion dates

**What's Missing:**
- [ ] Define and validate "completed" state for engagements (currently depends on AuditReport status alone)
- [ ] Consider filtering by `engagement__actual_end_date` if available
- [ ] Validate that linked AuditReport is truly in approved state before consolidation includes it
- [ ] Add business rule: exclude draft, in-progress, or rejected reports

---

### 5. PDF Generation
**SRS Requirement:** Reports should be available for distribution and archival (implied — standard audit report practice).

**Current Status:**
- Celery task stub exists: `generate_quarterly_report_pdf()` in `apps/core/tasks/report_generation.py`
- No implementation; marked as "Week 4 deliverable"

**What's Missing:**
- [ ] Implement PDF generation using HTML template + WeasyPrint
- [ ] Include narrative sections, aggregated statistics, charts (findings by severity, implementation trend)
- [ ] Generate QR code for verification
- [ ] Embed CIA signature if available
- [ ] Save to media directory and link to `document_id`
- [ ] Trigger PDF generation on approval (or via manual action)

---

### 6. Tests for Consolidation & Workflow
**SRS Requirement:** Implied — ensure consolidation logic and workflow transitions work as specified.

**Current Status:**
- No tests found for quarterly report consolidation
- No tests for workflow state machine (`VALID_QUARTERLY_TRANSITIONS`)
- No tests for business rules (linked reports, executive summary requirement, etc.)

**What's Missing:**
- [ ] Test consolidation with multiple approved engagement reports
- [ ] Test consolidation excludes draft/in-progress reports
- [ ] Test aggregation calculations (totals, implementation rate)
- [ ] Test invalid transitions are rejected
- [ ] Test permission enforcement for approve/manage actions
- [ ] Test locking of submitted reports
- [ ] Test auto-generation of reference number

---

### 7. Audit Trail & Approval Log
**SRS Requirement:** "Approved quarterly reports shall be recommended to the Commission for final approval" — implies full audit trail.

**Current Status:**
- Timestamps exist for key actions (`created_at`, `updated_at`, `approval_date`, `submission_date`)
- No separate audit log or history model tracking all state changes
- No tracking of reasons/comments per transition beyond free-text notes fields

**What's Missing:**
- [ ] Audit log model or table tracking every status transition with user, timestamp, reason
- [ ] Query endpoint to retrieve full audit trail for a report
- [ ] Structured feedback/approval log (e.g., committee recommendations as separate records)

---

### 8. Integration with Document Records Service
**SRS Requirement:** Reports should be available as uploaded documents for archival.

**Current Status:**
- `document_id` field exists to reference external document
- No endpoint or workflow to upload report to Document Records Service
- No automatic linking after PDF generation

**What's Missing:**
- [ ] Endpoint to upload quarterly report document
- [ ] Automatic upload trigger after PDF generation (or on approval)
- [ ] Retrieve document metadata/access from Document Records Service
- [ ] Version control if report is revised

---

### 9. CIA Role Enforcement
**SRS Requirement:** "The system/process shall allow the CIA to…" — only CIA should perform certain actions.

**Current Status:**
- Permission `grc:quarterly_report:manage` is generic; not restricted to CIA role
- No validation that `instructed_by`, `reviewed_by`, or `approved_by` are CIA users

**What's Missing:**
- [ ] Explicit role check for CIA-only actions (instruction, CIA review, approval to submit)
- [ ] Business rule: only CIA can set `instructed_by`, perform CIA review, or approve/submit
- [ ] Reject reports created by non-CIA if that's a requirement

---

### 10. Improvement Tracking
**SRS Requirement:** "The system/process shall enable the CIA to… revise the report based on Audit Committee recommendations… [and] resubmit the improved report to the Audit Committee for determination."

**Current Status:**
- Workflow supports `improvement_required → cia_review` cycle
- Free-text `committee_notes` capture recommendations
- No structured "improvement log" or tracking of what changed

**What's Missing:**
- [ ] Log or comments model tracking specific improvements made in each revision
- [ ] Diff or change summary when report transitions from `improvement_required` back to `cia_review`
- [ ] Version numbering or revision tracking (e.g., v1.0, v1.1, v1.2)

---

### 11. Commission Submission Acknowledgment
**SRS Requirement:** "The system/process shall allow the Audit Committee to recommend the approved report to the Commission."

**Current Status:**
- Status `submitted_to_commission` exists
- Fields `submission_date` and `submitted_to` capture where it was sent
- No workflow step for Commission's receipt or final determination

**What's Missing:**
- [ ] Track Commission's response/determination (acknowledge, reject, request info)
- [ ] Status extension: `commission_acknowledged`, `commission_approved`, `commission_rejected`
- [ ] Integration point for Commission's feedback (if Commission system exists)

---

## Summary of Gaps by Priority

### High Priority (Critical for SRS Compliance)
1. **Reporting period validation** — ensure dates align with quarter
2. **Engagement report status filtering** — verify reports are truly approved/completed
3. **CIA role enforcement** — restrict sensitive actions to CIA
4. **Consolidation tests** — verify aggregation logic is correct

### Medium Priority (Important for Full Process Support)
5. **Formal instruction process** — separate/explicit instruction step and notification
6. **Structured meeting minutes** — link to AuditMeeting for documented proceedings
7. **Audit trail** — full history of all state changes and approvals
8. **Improvement tracking** — log of revisions and what changed

### Lower Priority (Enhancement / Quality of Life)
9. **PDF generation** — implementation of report document creation
10. **Document Records Service integration** — archival of reports
11. **Commission feedback workflow** — final handoff to oversight body

---

## Implementation Readiness

| Gap # | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| 1 | Formal Instruction Process | Small | Permission model |
| 2 | Reporting Period Validation | Small | Quarter model |
| 3 | Meeting Minutes Link | Medium | AuditMeeting model |
| 4 | Engagement Status Filtering | Small | AuditEngagement/Report models |
| 5 | PDF Generation | Large | WeasyPrint, templates |
| 6 | Tests | Medium | Existing models |
| 7 | Audit Trail | Medium | New model/views |
| 8 | Document Service | Medium | External service |
| 9 | CIA Role Enforcement | Small | IAM service/permissions |
| 10 | Improvement Tracking | Small | New model/versioning |
| 11 | Commission Workflow | Small | Future workflow model |

