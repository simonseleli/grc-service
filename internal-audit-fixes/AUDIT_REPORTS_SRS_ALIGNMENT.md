# Audit Reports — SRS Alignment Checklist

**Document Purpose:** Track implementation gaps between SRS requirements and current codebase for Audit Reports (SRS 1.8.3 Steps 20–24).

**Model:** `AuditReport` (apps/core/models/audit_entities.py)  
**Views:** `apps/api/views/audit_report_views.py`  
**Serializers:** `apps/api/serializers/audit_serializers.py`  

---

## ✅ IMPLEMENTED REQUIREMENTS

### Data Model
- [x] OneToOne link to `AuditEngagement` (field: `engagement`)
- [x] Auto-generated reference number (format: `RPT-{engagement-ref}-{seq:03d}`)
- [x] Report type: `draft` or `final`
- [x] Title and narrative sections:
  - [x] Executive summary
  - [x] Scope and objectives
  - [x] Methodology
  - [x] Findings summary (JSON list, auto-populated from AuditFinding)
  - [x] Recommendations summary (JSON list, auto-populated from AuditRecommendation)
  - [x] Conclusion
- [x] Opinion FK link to `AuditOpinion` lookup table

### Workflow & Status
- [x] Status progression: `draft` → `under_review` → `approved` → `distributed`
- [x] Valid transitions enforced via `VALID_REPORT_TRANSITIONS` map
- [x] Ability to return report for revision (`under_review` → `draft`)
- [x] Terminal state: `distributed` (no further transitions)
- [x] CIA can edit during `under_review` (reviewer exception)
- [x] Draft-only reports can be deleted (soft-delete via `is_active=False`)

### Signatory & Audit Trail
- [x] `prepared_by` — User ID of report preparer (IA/LA)
- [x] `reviewed_by` — User ID of reviewer (set when moving to under_review)
- [x] `approved_by` — User ID of approver (CIA, set when moving to approved)
- [x] `approval_date` — Timestamp of CIA approval
- [x] Distribution tracking:
  - [x] `distribution_list` — JSON array of recipients
  - [x] `distributed_at` — Timestamp when distributed
  - [x] Report marked as `final` on distribution

### API Endpoints
- [x] List reports — GET `/api/v1/grc/audit/reports/` with filtering (engagement, status, report_type, is_active)
- [x] Create report — POST `/api/v1/grc/audit/reports/` (restricted to reporting/completed engagement)
- [x] Retrieve detail — GET `/api/v1/grc/audit/reports/{pk}/`
- [x] Update (full) — PUT `/api/v1/grc/audit/reports/{pk}/` (draft & under_review with CIA exception)
- [x] Partial update — PATCH `/api/v1/grc/audit/reports/{pk}/` (same restrictions)
- [x] Soft delete — DELETE `/api/v1/grc/audit/reports/{pk}/` (draft only)
- [x] Status transitions — POST `/api/v1/grc/audit/reports/{pk}/update-status/`
- [x] Distribute report — POST `/api/v1/grc/audit/reports/{pk}/distribute/`

### Automation & Integration
- [x] Auto-populate `findings_summary` from linked AuditFinding objects on creation
- [x] Auto-populate `recommendations_summary` from linked AuditRecommendation objects on creation
- [x] OneToOne constraint — max one report per engagement
- [x] Restriction: can only create report when engagement in `reporting` or `completed` status
- [x] Auto-generate reference number if not provided
- [x] Document reference field for linking to Document Records Service

### Permissions & Access Control
- [x] Permission `grc:audit_report:view` — required to create, view, edit reports
- [x] Permission `grc:audit_report:approve` — required to approve and distribute reports
- [x] Enforce view permission on list, create, detail, update views
- [x] Enforce approve permission when transitioning to `approved` or `distributed`

### System Integration
- [x] Publish audit events on creation, approval, distribution
- [x] Event types: `audit_report.generated`, `audit_report.approved`, `audit_report.published`
- [x] Messaging service integration via `apps/infrastructure/services/messaging_service.py`

---

## ⚠️ MISSING / INCOMPLETE REQUIREMENTS

### 1. Auditee Responses Integration
**SRS Requirement:** "Final audit reports shall incorporate auditee responses and be formally approved."  
"The system/process shall enable LA to: Incorporate written responses from auditees."

**Current Status:**
- No field to capture/link auditee responses in the report
- No workflow stage for "awaiting auditee responses"
- Findings and recommendations are auto-populated but no structured inclusion of auditee responses

**What's Missing:**
- [ ] `auditee_responses` field — text area or document reference for written responses
- [ ] `auditee_response_due_date` — deadline for auditee responses
- [ ] `auditee_response_received_date` — when responses were received
- [ ] Status flag or workflow stage: `awaiting_auditee_responses` between under_review and approved
- [ ] Requirement: final report must include evidence that auditee responses have been reviewed before approval
- [ ] Notification sent to auditees requesting responses with deadline

---

### 2. Exit Meeting Integration
**SRS Requirement:** "Exit Meeting — IA arranges exit meeting by sending Exit meeting notification… conducts Exit meeting with auditee management… record attendance and minutes."  
"Data Requirements: Exit meeting minutes"

**Current Status:**
- Model has no link to `AuditMeeting` for exit meeting records
- Report does not reference which AuditMeeting (if any) was the exit meeting
- Minutes/attendance not included in report data

**What's Missing:**
- [ ] FK link to `AuditMeeting` with meeting_type='exit' (field: `exit_meeting`)
- [ ] Business rule: require exit meeting to be recorded before report can move past under_review
- [ ] Validation: exit meeting must occur before or concurrent with report submission for approval
- [ ] Include exit meeting data in report:
  - [ ] Meeting date/time
  - [ ] Attendees list
  - [ ] Meeting minutes content
  - [ ] Key discussion points
  - [ ] Action items from meeting
- [ ] Field to capture "Exit Meeting Notification" status/date

---

### 3. Pre-Exit Meeting & Audit Team Meeting References
**SRS Requirement:** "Review of Working Papers and Pre-Exit Meeting… Arrange and conduct a pre-exit meeting with auditees."  
"Conduct an internal audit team meeting to consolidate deviations and recommendations."

**Current Status:**
- No structured linkage to pre-exit or audit team meetings
- No audit team meeting consolidation tracking

**What's Missing:**
- [ ] FK link to pre-exit meeting — `AuditMeeting(meeting_type='pre_exit')`
- [ ] FK link to audit team meeting — `AuditMeeting(meeting_type='team')`
- [ ] Business rule: audit team meeting must be conducted before draft report is submitted
- [ ] Include audit team meeting summary in report narrative (via findings/recommendations consolidation)
- [ ] Field to track: "Findings discussed and consolidated with IA team on [date]"

---

### 4. Prior Audit Recommendations Tracking
**SRS Requirement:** "Identification of Outstanding Recommendations: The system shall allow Internal Auditors to identify and generate a list of unimplemented and partially implemented audit recommendations from previous audit reports."  
"Filter recommendations based on implementation status."

**Current Status:**
- No field linking to prior audit reports or prior recommendations
- No automated filtering of prior outstanding recommendations
- No "Prior Findings & Recommendations" section in report

**What's Missing:**
- [ ] Field: `prior_outstanding_recommendations` — reference to unresolved recommendations from previous reports
- [ ] Validation: IA must review and acknowledge outstanding recommendations before finalizing report
- [ ] Summary section: "Status of Prior Audit Recommendations" with breakdown by implementation status
- [ ] Query endpoint: `/reports/{id}/prior-recommendations/` to list outstanding items
- [ ] Link to prior AuditReport instances if engagement is recurring audit of same entity

---

### 5. Report Sections & Narrative Structure
**SRS Requirement:** "Draft Internal Audit Report" should consolidate deviations, findings, recommendations, and auditee responses.

**Current Status:**
- Core sections exist (executive summary, scope, methodology, findings, recommendations, conclusion)
- Missing specialized sections per SRS process

**What's Missing:**
- [ ] `audit_deviations` section — formal listing of identified deviations/exceptions
- [ ] `key_observations` section — significant facts/trends observed
- [ ] `management_responses` section — structured recording of auditee management responses
- [ ] `follow_up_actions` section — required actions based on findings
- [ ] `compliance_assessment` section — statements on whether operations are in compliance
- [ ] Structured data for each finding: {description, severity, recommendation, auditee_response, management_action_plan}

---

### 6. Entry Meeting Reference
**SRS Requirement:** "Outputs of the Process: Entry Meeting Minutes"

**Current Status:**
- AuditEngagement has `entry_meeting_date` but no link to AuditMeeting record
- Report does not reference entry meeting

**What's Missing:**
- [ ] FK link: `AuditEngagement.entry_meeting` → `AuditMeeting(meeting_type='entry')`
- [ ] Report should include reference to entry meeting and scope agreement confirmed
- [ ] Data Requirements: Entry meeting minutes included in audit file

---

### 7. PDF Generation & Report Distribution
**SRS Requirement:** Implied — reports must be formally distributed to stakeholders with proper formatting and archival.

**Current Status:**
- Celery task stub exists: `generate_engagement_report_pdf()` in `apps/core/tasks/report_generation.py`
- No implementation; marked as "Week 3 deliverable"
- Distribution list only stores recipient metadata, not evidence of delivery

**What's Missing:**
- [ ] Implement PDF generation using HTML template + WeasyPrint
- [ ] Include all narrative sections, findings/recommendations, opinion, signatures
- [ ] Generate QR code for verification/authenticity
- [ ] Embed CIA signature/approval seal
- [ ] Generate formal distribution letter
- [ ] Save PDF to media directory and link to `document_id`
- [ ] Trigger PDF generation on approval (or option to generate before distribution)
- [ ] Track delivery confirmation for each recipient (beyond just list storage)

---

### 8. Tests for Report Workflow
**SRS Requirement:** Implied — ensure status workflow, data validations, and business rules work correctly.

**Current Status:**
- No tests found for audit report creation/workflow/distribution
- No tests for findings/recommendations auto-population
- No tests for engagement status restriction

**What's Missing:**
- [ ] Test: Can only create report when engagement in reporting/completed
- [ ] Test: Findings/recommendations auto-populated correctly
- [ ] Test: OneToOne constraint prevents duplicate reports
- [ ] Test: Status transitions follow allowed workflow map
- [ ] Test: Draft reports can be deleted, others cannot
- [ ] Test: CIA can edit during under_review, IA cannot
- [ ] Test: Only CIA can approve; view-only users cannot
- [ ] Test: Distribute endpoint requires approved status
- [ ] Test: Reference number auto-generated with correct format
- [ ] Test: Events published correctly on status changes

---

### 9. Workflow Integration with Work Orchestration Service
**SRS Requirement:** Implied — Audit Report approval workflow should be managed as a formal stage-based process.

**Current Status:**
- AuditReport extends `WorkflowMixin` but workflow stages not fully defined
- `get_workflow_context()` method exists but implementation incomplete
- No integration with Work Orchestration Service for multi-stage approval

**What's Missing:**
- [ ] Define formal workflow with stages: draft → submitted_for_review → under_review → approved → distributed
- [ ] Implement `get_workflow_context()` to return assignees (IA, CIA)
- [ ] Link to Work Orchestration Service workflow plan (store workflow_plan_id)
- [ ] Advance workflow stages via orchestration service lifecycle events (not just status field)
- [ ] Support for parallel approvals (e.g., ILA and CIA review simultaneously)
- [ ] SLA/due dates for each stage

---

### 10. CIA Role Enforcement
**SRS Requirement:** "The system/process shall enable CIA to: Review and approve the final report. Authorize distribution to relevant stakeholders."

**Current Status:**
- Permission `grc:audit_report:approve` exists but may not be strictly CIA-only
- No explicit role validation that approver is CIA

**What's Missing:**
- [ ] Explicit role check for CIA-only actions (approve, distribute)
- [ ] Business rule: only CIA can transition to approved or initiated distribution
- [ ] Reject attempts by non-CIA users to approve reports
- [ ] Optional: link to CIA designation/role from IAM service

---

### 11. Audit File Completeness
**SRS Requirement:** Implied — audit file should contain all required documentation.

**Current Status:**
- Report model links to engagement but not to individual working papers, findings, recommendations, meetings
- No validation that required components are complete before finalization

**What's Missing:**
- [ ] Validation before approval: all required working papers are reviewed
- [ ] Validation: all findings have recommendations
- [ ] Validation: all recommendations have priority/management action plans
- [ ] Checklist: entry meeting minutes, exit meeting minutes, working papers, findings summary data available
- [ ] Report cannot be approved until all components have been properly documented

---

### 12. Intermediate Reviewer (ILA) Support
**SRS Requirement:** "Submit the draft to Intermediate LA (ILA) and CIA for review."

**Current Status:**
- Workflow only has one reviewer step (under_review)
- No distinction between ILA and CIA review

**What's Missing:**
- [ ] Support for two-tier review: ILA (intermediate lead auditor) then CIA
- [ ] Additional status: `ila_review` between draft and `under_review` (CIA review)
- [ ] Two separate reviewer fields: `ila_reviewed_by` and `reviewed_by` (CIA)
- [ ] Business rule: report must be reviewed by ILA before CIA sees it
- [ ] Routing logic to ensure proper sequence of reviews

---

## Summary of Gaps by Priority

### High Priority (Critical for SRS Compliance)
1. **Auditee Responses Integration** — core SRS requirement for final report
2. **Exit Meeting Link** — required input to finalize report with management
3. **Entry Meeting Reference** — required audit file component
4. **Prior Recommendations Tracking** — requirement 1.8.3 step for context on ongoing issues
5. **Tests** — verify workflow and business rules work as specified

### Medium Priority (Important for Full Process Support)
6. **Pre-Exit & Audit Team Meeting References** — document consolidation step
7. **Report Sections Expansion** — structured capture of management responses, deviations
8. **PDF Generation** — report distribution implementation
9. **Workflow Orchestration** — formal stage-based management
10. **Intermediate Reviewer (ILA) Support** — multi-tier approval process

### Lower Priority (Enhancement / Quality of Life)
11. **CIA Role Enforcement** — stricter role validation
12. **Audit File Completeness Validation** — checklist requirements

---

## Implementation Readiness

| Gap # | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| 1 | Auditee Responses Integration | Small | UI form for response capture |
| 2 | Exit Meeting Link | Small | AuditMeeting model |
| 3 | Entry Meeting Reference | Small | AuditMeeting model, AuditEngagement update |
| 4 | Prior Recommendations Tracking | Medium | Historical report data, query filters |
| 5 | Tests | Medium | Existing models |
| 6 | Pre-Exit & Audit Team Meeting | Small | AuditMeeting model |
| 7 | Report Sections Expansion | Small | New fields/JSON schema |
| 8 | PDF Generation | Large | WeasyPrint, templates, Document Service |
| 9 | Workflow Orchestration | Medium | Work Orchestration Service integration |
| 10 | ILA Support | Small | New status, workflow logic |
| 11 | CIA Role Enforcement | Small | Role/permission model |
| 12 | Audit File Validation | Small | Pre-approval checklist |

---

## Process Flow: Current vs. SRS Expectation

### Current Implementation (Simplified)
```
IA creates draft report
    ↓
IA submits for review (under_review status)
    ↓ 
CIA reviews & approves (approved status)
    ↓
CIA distributes (distributed status = final)
```

### SRS Expected Flow (Full)
```
IA conducts entry meeting
    ↓
IA conducts audit procedures
    ↓
IA conducts audit team meeting (consolidate findings/recommendations)
    ↓
IA conducts pre-exit meeting with auditee
    ↓
IA creates draft report (incorporates discussion from meetings)
    ↓
IA submits draft to ILA for review
    ↓
ILA reviews & returns for revisions OR approves for CIA
    ↓
CIA reviews & approves OR returns for revision
    ↓
Auditees submitted written responses (response deadline)
    ↓
IA conducts exit meeting with auditee management
    ↓
IA incorporates auditee responses into final report
    ↓
CIA approves final report
    ↓
CIA authorizes distribution to stakeholders
    ↓
Report formally distributed with delivery confirmation
```

---

## Notes

- The current implementation covers the basic approval workflow well but lacks integration with pre-report meetings and post-report stakeholder engagement.
- Most gaps are around capturing and referencing the full audit lifecycle (entry → fieldwork → pre-exit → exit) rather than the report document itself.
- PDF generation is a blocking item if reports need to be formally distributed (non-negotiable for real-world use).
- Prior recommendations tracking is critical for recurring/related audits to show continuous improvement monitoring.

