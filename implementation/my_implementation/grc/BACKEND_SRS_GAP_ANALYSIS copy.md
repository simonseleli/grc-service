# GRC Internal Audit Module — SRS Gap Analysis & Fix Tracker

> **Generated:** 2026-03-04
> **Purpose:** Comprehensive gap analysis between the SRS (AUDT2_ext.md) and the current GRC implementation (grc-service + frontend staff-portal).
> **How to use:** Work through each gap top-to-bottom. Check off items as you fix them. Priority order: Critical → High → Medium → Low.

---

## Executive Summary

| Metric | Value |
|---|---|
| **Overall SRS Coverage** | ~75–80% |
| **SRS System Requirements Covered (Req 1–41)** | 28 of 41 |
| **Missing Entities/Processes** | 5 (Audit Memo, Declaration of Independence, Audit Survey, RCM, Audit Program) |
| **Missing Automations** | 3 (Auto risk scoring, 5-day deadline enforcement, QR/Signature) |
| **Partially Implemented** | 3 (Risk Assessment, Monitoring, Engagement types) |
| **Fully Aligned** | Configuration, Audit Universe, Auditable Entities, RBIAP workflow, Findings (4 C's), Recommendations lifecycle, Working Papers, Meetings, Audit Reports, Quarterly Reports |

---

## Table of Contents

1. [What's Fully Aligned](#1-whats-fully-aligned)
2. [GAP 1: Internal Audit Memo — CRITICAL](#2-gap-1-internal-audit-memo--critical)
3. [GAP 2: Declaration of Independence — CRITICAL](#3-gap-2-declaration-of-independence--critical)
4. [GAP 3: Audit Survey & Fraud Risk Assessment — HIGH](#4-gap-3-audit-survey--fraud-risk-assessment--high)
5. [GAP 4: Risk and Control Matrix (RCM) — HIGH](#5-gap-4-risk-and-control-matrix-rcm--high)
6. [GAP 5: Audit Program as Separate Entity — HIGH](#6-gap-5-audit-program-as-separate-entity--high)
7. [GAP 6: Automatic Risk Score Calculation — MEDIUM](#7-gap-6-automatic-risk-score-calculation--medium)
8. [GAP 7: 5-Day Response Deadline Enforcement — MEDIUM](#8-gap-7-5-day-response-deadline-enforcement--medium)
9. [GAP 8: Engagement Type Mismatch — LOW](#9-gap-8-engagement-type-mismatch--low)
10. [GAP 9: QR Code + Digital Signature — LOW](#10-gap-9-qr-code--digital-signature--low)
11. [GAP 10: Evidence Attachments on Risk Assessments — LOW](#11-gap-10-evidence-attachments-on-risk-assessments--low)
12. [GAP 11: Auto-Generated Prioritized Audit Plan Draft — MEDIUM](#12-gap-11-auto-generated-prioritized-audit-plan-draft--medium)
13. [GAP 12: Risk Management System Integration — LOW (Phase 2)](#13-gap-12-risk-management-system-integration--low-phase-2)
14. [SRS Requirement Traceability Matrix](#14-srs-requirement-traceability-matrix)
15. [Suggested Implementation Order](#15-suggested-implementation-order)
16. [Files That Will Need Changes](#16-files-that-will-need-changes)

---

## 1. What's Fully Aligned

These parts of your implementation correctly match the SRS. No action needed.

### 1.1 Configuration (SRS Prerequisites)
- [x] **Fiscal Years** — CRUD with auto-generated quarters (Q1–Q4)
- [x] **Severities** — Configurable levels with sort order
- [x] **Finding Types** — Configurable categories (Compliance, Financial, Operational, Control Weakness)
- [x] **Risk Ratings** — Configurable High/Medium/Low with values
- [x] **Audit Opinions** — For report classification

### 1.2 Audit Universe (SRS 1.8.1 Step 1)
- [x] Create/Edit/Delete universe per fiscal year
- [x] Fiscal year uniqueness constraint
- [x] Submit for approval → Workflow Console integration via Work Orchestration Service
- [x] CIA review and approve via embedded workflow

### 1.3 Auditable Entities (SRS 1.8.1 Step 1)
- [x] Embedded within Audit Universe detail page
- [x] 6 entity types: directorate, unit, zone, process, system, project
- [x] Code uniqueness within universe
- [x] Business guard: cannot add to approved universe

### 1.4 RBIAP Approval Workflow (SRS 1.8.1 Steps 2–10)
- [x] 4-stage workflow: CIA Review → Management Review → Committee Review → Commission Noting
- [x] `get_workflow_stages()` returns correct stage definitions
- [x] WorkflowMixin integration with Work Orchestration Service
- [x] Management comments and committee comments fields
- [x] Status progression: draft → management_review → committee_review → approved → implementation

### 1.5 Audit Engagement (SRS 1.8.3 Steps 1–3, 9–12 — Partial)
- [x] Create engagement linked to approved plan + auditable entity
- [x] Lead auditor assignment
- [x] Scope, methodology, planned dates
- [x] 4-phase lifecycle workflow: Planning → Fieldwork → Reporting → Completed
- [x] Working papers embedded in engagement detail

### 1.6 Working Papers (SRS 1.8.3 Steps 15–19)
- [x] Create under engagement (parent relationship)
- [x] Paper types: planning, fieldwork, analysis, conclusion, other
- [x] File upload support (via Document Records Service delegation)
- [x] 2-stage review workflow: LA Review → CIA Approval
- [x] Preparer-only edit/delete/submit guards

### 1.7 Audit Findings (SRS 1.8.3 Steps 15–18)
- [x] The 4 C's: Condition, Criteria, Cause, Effect (all required, min 20 chars)
- [x] Auto-generated reference numbers (FND-{engagement_ref}-{sequence})
- [x] Linked to engagement, fiscal year, quarter
- [x] Finding type + severity + risk rating from config lookups
- [x] Status lifecycle: draft → discussed → final
- [x] Auditee response and management response fields

### 1.8 Audit Recommendations (SRS 1.8.3 Steps 20–24)
- [x] Linked to finalized findings only
- [x] Auto-generated reference numbers
- [x] Priority (High/Medium/Low), target date, responsible party
- [x] Status lifecycle: open → in_progress → implemented → verified → closed
- [x] Implementation notes required for `implemented` transition
- [x] Verification evidence required for `verified` transition

### 1.9 Audit Meetings (SRS 1.8.3 Steps 14, 17, 20, 24)
- [x] 4 meeting types: Entry Conference, Pre-Exit Conference, Audit Team Meeting, Exit Conference
- [x] Scheduling with date, time, location, agenda
- [x] Post-meeting data: minutes, key discussions, attendees (JSON)
- [x] Document uploads: minutes document, attendance sheet (via Document Records Service)
- [x] Status: scheduled → in_progress → completed/cancelled
- [x] Field locking: structural fields locked during in_progress, only post-meeting fields editable
- [x] Guard: minutes required before completing

### 1.10 Audit Reports (SRS 1.8.3 Steps 20–24, 1.8.5)
- [x] Linked to engagement in reporting status
- [x] Executive summary, scope, methodology, conclusion
- [x] Audit opinion from config
- [x] Report type: Draft / Final
- [x] Status: draft → under_review → approved → distributed

### 1.11 Quarterly Reports (SRS 1.8.5)
- [x] Linked to fiscal year + quarter
- [x] Consolidation endpoint (auto-populates findings/recommendations summaries)
- [x] 7-stage status workflow: draft → cia_review → management_review → committee_review → improvement_required → approved → submitted_to_commission
- [x] Fiscal year cascade (quarter resets on FY change)

### 1.12 Implementation Monitoring (SRS 1.8.6 — Partial)
- [x] Monitoring records linked to in_progress recommendations
- [x] Progress percentage (0–100)
- [x] Next review date tracking
- [x] Progress notes
- [x] Soft delete and restore
- [x] Due reviews endpoint

### 1.13 Dashboard
- [x] Summary stats: Risk Assessments, Active Actions, Audits Completed, Engagements, Findings
- [x] Module navigation cards with live counts
- [x] Skeleton loading states

---

## 2. GAP 1: Internal Audit Memo — CRITICAL

### SRS References
- **Requirement 10:** CIA appoints LA and audit team to prepare the Internal Audit Memo
- **Requirement 11:** LA prepares the memo, identifies key areas, submits to CIA for review
- **Requirement 12:** CIA reviews the memo, submits to Director General (DG) for approval
- **Requirement 13:** DG reviews and approves the Internal Audit Memo
- **Requirement 14:** CIA transmits approved memo to LA to initiate pre-audit preparation
- **Requirement 18 (output):** Generate the Approved Internal Audit Memo

### What SRS Requires
A formal document (Internal Audit Memo) that:
1. Is prepared by the Lead Auditor after being appointed by CIA
2. Identifies the audit assignment details (team, scope references, timeline)
3. Goes through a 3-stage approval: **LA → CIA → Director General (DG)**
4. Once approved, is transmitted back to LA signaling "begin pre-audit prep"
5. Is generated as an official output artifact

### What's Currently Implemented
**Nothing.** The current flow goes directly from approved Audit Plan → Create Engagement. There is no `AuditMemo` model, no DG approval step, and no memo generation.

### What Needs to Be Built

#### Backend (grc-service)

**New Model: `AuditMemo`** in `apps/core/models/audit_entities.py`



Fields:

id: UUID (PK)
reference_number: CharField (unique, auto-generated: MEMO-{plan_ref}-{seq})
audit_plan: ForeignKey → AuditPlan
auditable_entity: ForeignKey → AuditableEntity
title: CharField (memo title / subject line)
lead_auditor: UUIDField (appointed LA from IAM)
audit_team: JSONField (list of team member UUIDs)
purpose: TextField (why this audit is being conducted)
scope_summary: TextField (brief scope outline before full engagement plan)
timeline_start: DateField
timeline_end: DateField
prepared_by: UUIDField (the LA who prepared it)
reviewed_by_cia: UUIDField (nullable)
approved_by_dg: UUIDField (nullable)
cia_review_date: DateTimeField (nullable)
dg_approval_date: DateTimeField (nullable)
status: CharField (choices: draft, cia_review, dg_review, approved, transmitted)
workflow_plan_id: UUIDField (nullable — WO integration)
Timestamps from TimestampedModel




**Workflow stages (3-stage):**
1. **CIA Review** — CIA can: Approve (→ dg_review) / Return (→ draft)
2. **DG Approval** — DG can: Approve (→ approved) / Return (→ cia_review)
3. **Transmission** — CIA transmits to LA (→ transmitted)

**API Endpoints:**
- `GET/POST /api/v1/grc/audit/memos/` — list/create
- `GET/PUT/DELETE /api/v1/grc/audit/memos/{id}/` — detail/update/delete
- `POST /api/v1/grc/audit/memos/{id}/submit/` — submit for CIA review
- `POST /api/v1/grc/audit/memos/{id}/start-workflow/` — start WO approval workflow
- Business guard: Plan must be in `approved` or `implementation` status

**Serializer, ViewSet, URL routing** — follow existing patterns from `AuditPlanViewSet`.

#### Frontend (staff-portal)

**New page:** `/service/grc/audit-memos` (list) and `/service/grc/audit-memos/{id}` (detail)
- Create dialog with: Plan selector, Entity selector, LA selector, Team members, Purpose, Scope summary, Timeline
- Detail page: left panel (metadata) + right panel (Workflow Console)
- Status badges matching the 5-status lifecycle
- Add to sidebar under Internal Audit section (between "Audit Plans" and "Audit Engagements")

#### Flow Change
Current: `Approved Plan → Create Engagement`
New: `Approved Plan → Create Memo → CIA Review → DG Approve → Transmit to LA → Create Engagement`

The engagement creation should then require an **approved and transmitted memo** (not just an approved plan).

### Checklist
- [ ] Create `AuditMemo` model with fields above
- [ ] Create migration
- [ ] Create serializer (Create + Update + Detail)
- [ ] Create ViewSet with CRUD + submit + start-workflow
- [ ] Add URL routes under `/api/v1/grc/audit/memos/`
- [ ] Add `get_workflow_stages()` with 3 stages
- [ ] Add business guard: require approved plan
- [ ] Update `AuditEngagement` creation to require transmitted memo (optional — can be phased)
- [ ] Frontend: List page, Create dialog, Detail page with Workflow Console
- [ ] Frontend: Add sidebar entry
- [ ] Add to nginx.conf if needed (should already be covered by `/api/v1/grc/` catch-all)
- [ ] Update permissions JSON
- [ ] Update testing flow document

---

## 3. GAP 2: Declaration of Independence — CRITICAL

### SRS References
- **Requirement 16:** Audit team members shall review the audit plan, checklists, and sign the **Declaration of Independence/Conflict of Interest Form** prior to participation
- **Requirement 18 (output):** Generate the **Signed Declaration of Independence/Conflict of Interest Form**
- **Requirement 38 (output):** Distribute the Signed Declaration alongside the Approved Audit Report

### What SRS Requires
Each audit team member must formally declare they have no conflict of interest before participating in an audit engagement. This is:
1. A per-team-member, per-engagement form
2. Must be signed (acknowledged) before fieldwork begins
3. Generated as a formal output document

### What's Currently Implemented
**Nothing.** No model, no form, no signing workflow.

### What Needs to Be Built

#### Backend

**New Model: `DeclarationOfIndependence`** in `apps/core/models/audit_entities.py`





Fields:

id: UUID (PK)
audit_engagement: ForeignKey → AuditEngagement
audit_memo: ForeignKey → AuditMemo (nullable, if memo exists)
declarant_user_id: UUIDField (team member from IAM)
declarant_name: CharField (cached display name)
declarant_role: CharField (role in the audit team: lead_auditor, team_member)
declaration_text: TextField (the standard declaration statement — can be a default)
has_conflict: BooleanField (default False)
conflict_details: TextField (blank, required if has_conflict=True)
is_signed: BooleanField (default False)
signed_at: DateTimeField (nullable)
status: CharField (choices: pending, signed, waived)
Timestamps



**API Endpoints:**
- `GET/POST /api/v1/grc/audit/declarations/` — list/create (bulk creation for all team members)
- `GET/PUT /api/v1/grc/audit/declarations/{id}/` — detail/update
- `POST /api/v1/grc/audit/declarations/{id}/sign/` — team member signs
- `GET /api/v1/grc/audit/engagements/{id}/declarations/` — all declarations for an engagement
- Business guard: all declarations must be signed before engagement can move to fieldwork

#### Frontend

- Embedded in the **Engagement Detail Page** (new section below Working Papers, or a new tab)
- Table showing each team member's declaration status
- "Generate Declarations" button creates a record for each team member
- Each member can view and sign their declaration
- Visual status: pending (yellow), signed (green), conflict flagged (red)

### Checklist
- [ ] Create `DeclarationOfIndependence` model
- [ ] Create migration
- [ ] Create serializer
- [ ] Create ViewSet (CRUD + sign endpoint + bulk create)
- [ ] Add nested route under engagements
- [ ] Add business guard: block fieldwork unless all declarations signed
- [ ] Frontend: declarations section in engagement detail
- [ ] Frontend: sign action per team member
- [ ] Update permissions JSON
- [ ] Update testing flow

---

## 4. GAP 3: Audit Survey & Fraud Risk Assessment — HIGH

### SRS References
- **Requirement 19:** Facilitate the conduct of a **preliminary survey** by the Audit Team, including the conduct of **Fraud Risk Assessment**
- **Requirement 20:** Support Audit Team Members in reviewing the adequacy of process controls and developing effectiveness tests
- **Requirement 21:** If controls are found inadequate, allow Audit Team Members to include them as audit findings and design tests

### What SRS Requires
Before fieldwork begins, the audit team conducts a preliminary survey of the auditable area to:
1. Understand the process and control environment
2. Assess fraud risks specific to the area
3. Identify preliminary findings where controls are weak
4. Decide whether controls are adequate → develop effectiveness tests, or inadequate → document as finding

### What's Currently Implemented
**Nothing explicit.** The engagement has `scope` and `methodology` text fields, but no structured survey process, no fraud risk assessment form, no control adequacy assessment.

### What Needs to Be Built

#### Backend

**New Model: `AuditSurvey`** (or `PreliminarySurvey`)



Fields:

id: UUID (PK)
audit_engagement: ForeignKey → AuditEngagement (one survey per engagement)
surveyed_by: UUIDField (team member who conducted)
survey_date: DateField
process_description: TextField (documented understanding of the process)
control_environment_notes: TextField (assessment of overall control environment)
prior_audit_history: TextField (reference to previous audit results, if any)
fraud_risk_assessment: JSONField (structured list of fraud risk factors assessed)
e.g. [{"risk_factor": "Override of controls", "likelihood": "medium", "impact": "high", "notes": "..."}]
control_assessments: JSONField (list of controls assessed)
e.g. [{"control_name": "...", "control_owner": "...", "design_adequate": true/false, "notes": "...", "test_strategy": "effectiveness"|"impact"}]
preliminary_findings: TextField (summary of preliminary findings)
status: CharField (draft, completed)
Timestamps




**API Endpoints:**
- `GET/POST /api/v1/grc/audit/surveys/`
- `GET/PUT/DELETE /api/v1/grc/audit/surveys/{id}/`
- `GET /api/v1/grc/audit/engagements/{id}/survey/` — survey for a specific engagement
- Business guard: engagement must be in `planning` status

#### Frontend

- Accessible from the **Engagement Detail Page** (new "Preliminary Survey" section/tab)
- Structured form for process description, control assessment table, fraud risk factor table
- Control adequacy toggle per control (adequate/inadequate)
- When marked inadequate → prompt to link or create a Finding

### Checklist
- [ ] Create `AuditSurvey` model
- [ ] Create migration
- [ ] Create serializer
- [ ] Create ViewSet
- [ ] Add URL routes
- [ ] Frontend: survey section in engagement detail
- [ ] Frontend: fraud risk assessment form (JSON table builder)
- [ ] Frontend: control adequacy checklist
- [ ] Update permissions JSON
- [ ] Update testing flow

---

## 5. GAP 4: Risk and Control Matrix (RCM) — HIGH

### SRS References
- **Requirement 22:** Enable the LA to develop a **Risk and Control Matrix**, prioritize auditable process areas, and prepare a draft audit program
- **SRS 1.8.3 Step 8:** "LA develops Risk and Control Matrix and prioritizes the auditable process areas"
- **General Requirements:** "The system shall allow the LA to develop and maintain a Risk and Control Matrix"

### What SRS Requires
A structured matrix mapping:
- **Risks** identified for the auditable area
- **Controls** that mitigate those risks
- **Control owners**
- **Design adequacy** assessment
- **Prioritization** of areas based on risk severity
- Used to define audit scope and focus areas

### What's Currently Implemented
**Nothing.** No RCM model. The engagement has `scope` and `methodology` text fields, but no structured risk-to-control mapping.

### What Needs to Be Built

#### Backend

**New Model: `RiskControlMatrix`**



Fields:

id: UUID (PK)
audit_engagement: ForeignKey → AuditEngagement (one RCM per engagement)
prepared_by: UUIDField (LA)
status: CharField (draft, submitted, approved)
Timestamps



**New Model: `RCMEntry`** (child rows of the matrix)


Fields:

id: UUID (PK)
risk_control_matrix: ForeignKey → RiskControlMatrix
order: IntegerField (display ordering)
process_area: CharField (the business process/area)
risk_description: TextField (what could go wrong)
risk_rating: ForeignKey → RiskRating (from config lookups)
control_description: TextField (existing control)
control_owner: CharField (who owns this control)
control_type: CharField (preventive, detective, corrective)
design_adequate: BooleanField (nullable)
design_assessment_notes: TextField (blank)
test_approach: CharField (choices: effectiveness_test, impact_test, not_applicable)
priority: CharField (high, medium, low)
in_scope: BooleanField (default True — included in audit scope)
exclusion_justification: TextField (blank — required if in_scope=False)
Timestamps





**API Endpoints:**
- `GET/POST /api/v1/grc/audit/rcm/` — list/create RCM
- `GET/PUT/DELETE /api/v1/grc/audit/rcm/{id}/` — RCM detail
- `GET/POST /api/v1/grc/audit/rcm/{id}/entries/` — manage RCM entries
- `GET/PUT/DELETE /api/v1/grc/audit/rcm-entries/{id}/` — single entry
- `POST /api/v1/grc/audit/rcm/{id}/submit/` — submit for approval
- Business guard: engagement must be in `planning` status

#### Frontend

- Accessible from Engagement Detail → new "Risk & Control Matrix" tab/section
- Table builder UI: add rows, each row = one risk-control pair
- Columns: Process Area, Risk, Rating, Control, Owner, Adequate?, Test Approach, Priority, In Scope?
- Sort/filter by priority and risk rating
- Submit for CIA approval action

### Checklist
- [ ] Create `RiskControlMatrix` + `RCMEntry` models
- [ ] Create migrations
- [ ] Create serializers (nested entries in RCM)
- [ ] Create ViewSets
- [ ] Add URL routes
- [ ] Frontend: RCM table builder in engagement detail
- [ ] Frontend: submit for approval action
- [ ] Update permissions JSON
- [ ] Update testing flow

---

## 6. GAP 5: Audit Program as Separate Entity — HIGH

### SRS References
- **Requirement 22:** "prepare a **draft audit program** and submit it for vetting"
- **Requirement 23:** "review and approval of the draft audit program by the IA and CIA"
- **SRS 1.8.3 Step 9:** "CIA approves the audit program and instructs LA to prepare EN"
- **Process Output:** "Audit Program" listed as a formal output

### What SRS Requires
A distinct, approvable document separate from the engagement that defines:
1. Audit objectives per area
2. Test procedures to be performed
3. Sample sizes and selection methods
4. Audit criteria and standards
5. Approved by CIA before engagement notification is sent

### What's Currently Implemented
**Folded into engagement.** The engagement has `scope`, `methodology`, and `objectives` fields, but no separate reviewable Audit Program with its own approval workflow.

### What Needs to Be Built

#### Backend

**New Model: `AuditProgram`**


Fields:

id: UUID (PK)
audit_engagement: OneToOneField → AuditEngagement
reference_number: CharField (unique, auto-generated)
title: CharField
risk_control_matrix: ForeignKey → RiskControlMatrix (nullable — links to the RCM)
objectives: JSONField (list of audit objectives)
procedures: JSONField (list of test procedures with linked RCM entries)
e.g. [{"rcm_entry_id": "uuid", "procedure": "...", "sample_size": 25, "criteria": "..."}]
prepared_by: UUIDField (LA)
reviewed_by: UUIDField (nullable — IA reviewer)
approved_by: UUIDField (nullable — CIA)
status: CharField (draft, under_review, approved)
approval_date: DateTimeField (nullable)
workflow_plan_id: UUIDField (nullable)
Timestamps




**Workflow (2-stage):**
1. **IA Review** — IA can: Approve / Return
2. **CIA Approval** — CIA can: Approve / Return

**API Endpoints:**
- `GET/POST /api/v1/grc/audit/programs/`
- `GET/PUT/DELETE /api/v1/grc/audit/programs/{id}/`
- `POST /api/v1/grc/audit/programs/{id}/submit/`
- `POST /api/v1/grc/audit/programs/{id}/start-workflow/`
- Business guard: engagement must exist, RCM should be approved (optional)

#### Flow Change
Current: `Create Engagement → Start Engagement Workflow (EN sent)`
New: `Create Engagement → Prepare RCM → Prepare Audit Program → CIA Approves Program → Then start workflow (EN sent)`

The engagement's "Start Engagement Workflow" button should ideally check that the audit program is approved.

### Checklist
- [ ] Create `AuditProgram` model
- [ ] Create migration
- [ ] Create serializer
- [ ] Create ViewSet with approval workflow
- [ ] Add URL routes
- [ ] Add `get_workflow_stages()` with 2 stages
- [ ] Frontend: program section in engagement detail (or separate page)
- [ ] Frontend: link to RCM entries in procedures
- [ ] Update engagement workflow start guard (require approved program)
- [ ] Update permissions JSON
- [ ] Update testing flow

---

## 7. GAP 6: Automatic Risk Score Calculation — MEDIUM

### SRS References
- **General Requirements:** "The system shall automatically calculate: Weighted risk scores, Overall inherent risk rating, Residual risk rating after control consideration"
- **General Requirements:** "The system shall classify risks into predefined categories (High, Medium, Low) based on approved thresholds"

### What's Currently Implemented
The `RiskAssessment` model has 6 manual score fields (0–10 scale) plus `overall_risk_rating` and `residual_risk_rating` as **ForeignKey to RiskRating** — both are manually selected by the user.

### What SRS Requires
1. User enters the 6 individual scores
2. System **auto-calculates** a weighted composite score
3. System automatically maps the composite score to a risk rating category (High/Medium/Low) based on **configurable thresholds**
4. Residual risk is computed after control effectiveness adjustment

### What Needs to Change

#### Backend (`RiskAssessment` model + serializer)

1. Add a `weighted_risk_score` computed/stored field:



weighted_score = (inherent_risk * W1) + (control_effectiveness * W2) + (financial_exposure * W3) +
(compliance_risk * W4) + (operational_impact * W5) + (reputational_risk * W6)


Where W1–W6 are configurable weights (could be a new `RiskWeightConfig` model or stored in settings).

2. Add threshold-based auto-classification:


if weighted_score >= HIGH_THRESHOLD: overall_risk_rating = "High"
elif weighted_score >= MEDIUM_THRESHOLD: overall_risk_rating = "Medium"
else: overall_risk_rating = "Low"



3. Compute residual risk:

residual_score = weighted_score * (1 - control_effectiveness_score / 10)


Then classify residual the same way.

4. Keep the manual `overall_risk_rating` and `residual_risk_rating` FK fields for **override** capability, but auto-populate them on save.

#### Backend Changes
- Add `calculated_weighted_score` DecimalField (computed on save via `save()` override or signal)
- Add `calculated_residual_score` DecimalField
- Add `auto_overall_rating` ForeignKey → RiskRating (auto-set)
- Add `auto_residual_rating` ForeignKey → RiskRating (auto-set)
- Add configurable weights (new `RiskWeightConfiguration` singleton model in lookups, or simpler: settings.py)
- Add configurable thresholds on `RiskRating` model (e.g., `min_score` field)

#### Frontend Changes
- Show computed score alongside manual fields
- Auto-select overall/residual rating dropdowns based on computation
- Allow manual override with a "Override auto-rating" toggle

### Checklist
- [ ] Add `min_score` / `max_score` fields to `RiskRating` model for threshold-based classification
- [ ] Add weight configuration (model or settings)
- [ ] Add `calculated_weighted_score` and `calculated_residual_score` fields
- [ ] Add auto-calculation logic in serializer `create()`/`update()` or model `save()`
- [ ] Frontend: display computed score, auto-select ratings
- [ ] Frontend: override toggle
- [ ] Create migration
- [ ] Update testing flow

---

## 8. GAP 7: 5-Day Response Deadline Enforcement — MEDIUM

### SRS References
- **SRS 1.8.6 Step 3:** "Auditee respond to the list **within five days** and submit to the internal auditor with the attached evidence"
- **General Requirements:** "enforce a **five-day response window** from the date of notification"
- **General Requirements:** "generate **automated notifications** with defined response timelines"
- **General Requirements:** "highlight **late or non-responsive** auditees"

### What's Currently Implemented
- `ImplementationMonitoring` has `next_review_date` and `progress_notes`
- `AuditRecommendation` has `target_completion_date`
- No automated deadline enforcement, no 5-day window, no late/non-responsive flagging

### What Needs to Be Built

#### Backend

1. **Add fields to `ImplementationMonitoring`:**


notification_sent_at: DateTimeField (nullable — when the list was shared with auditee)
response_deadline: DateTimeField (nullable — auto-calculated: notification_sent_at + 5 business days)
auditee_responded_at: DateTimeField (nullable)
is_overdue: BooleanField (computed property or stored)




2. **Add Celery periodic task** (`check_monitoring_deadlines`):
- Runs daily
- Finds monitoring records where `response_deadline < now()` and `auditee_responded_at IS NULL`
- Marks as overdue
- Publishes notification events to Kafka for:
  - Reminder at day 3 (2 days before deadline)
  - Overdue alert at day 5+
  - Escalation at day 7+ (to CIA)

3. **Add API endpoints:**
- `POST /api/v1/grc/audit/implementation-monitoring/{id}/notify-auditee/` — sends the notification, sets `notification_sent_at`, calculates `response_deadline`
- `GET /api/v1/grc/audit/implementation-monitoring/overdue/` — (already exists but enhance with deadline data)
- `GET /api/v1/grc/audit/implementation-monitoring/non-responsive/` — new endpoint

4. **Add filtered views:**
- Filter by `is_overdue=true`
- Filter by `auditee_responded_at__isnull=true` (non-responsive)

#### Frontend

- Show deadline countdown badge on monitoring records
- "Notify Auditee" button that triggers the notification
- Visual highlighting: overdue records in red, approaching deadline in yellow
- Filter/tab for "Overdue" and "Non-Responsive"

### Checklist
- [ ] Add deadline fields to `ImplementationMonitoring`
- [ ] Create migration
- [ ] Add `notify-auditee` endpoint
- [ ] Add `non-responsive` endpoint
- [ ] Add Celery task for deadline checking + auto-notifications
- [ ] Register Kafka notification templates for reminders/escalations
- [ ] Frontend: notify button, deadline badges, overdue highlighting
- [ ] Update testing flow

---

## 9. GAP 8: Engagement Type Mismatch — LOW

### SRS Reference
- The SRS mentions "Special Investigation" as a distinct engagement type
- The testing flow references 4 types: Planned, Unplanned, Special Investigation, Follow-up

### Current Implementation
`AuditEngagement.ENGAGEMENT_TYPE_CHOICES`:
```python
('planned', 'Planned Engagement'),
('ad_hoc', 'Ad-hoc Engagement'),
('follow_up', 'Follow-up Engagement'),
```

Only 3 types. `ad_hoc` ≈ Unplanned, but "Special Investigation" is missing.

### Fix
Add the 4th type:

```python
ENGAGEMENT_TYPE_CHOICES = [
    ('planned', 'Planned Engagement'),
    ('unplanned', 'Unplanned Engagement'),
    ('special_investigation', 'Special Investigation'),
    ('follow_up', 'Follow-up Engagement'),
]
```

Also rename `ad_hoc` → `unplanned` to match SRS terminology (will need a data migration if production data exists).

### Checklist
- [ ] Update `ENGAGEMENT_TYPE_CHOICES` in model
- [ ] Create data migration to rename existing `ad_hoc` → `unplanned`
- [ ] Update frontend dropdown options
- [ ] Update serializer if any type validation exists

---

## 10. GAP 9: QR Code + Digital Signature — LOW

### SRS References
- **SRS 1.8.3 Step 11:** "CIA approve (Signature and QR Code embedded automatically)"
- **Requirement 38:** "generate the Approved Internal Audit Report, Signed Declaration of Independence/Conflict of Interest Form"

### What SRS Requires
When CIA approves certain documents (Engagement Notification, Audit Report, Declaration), the system should automatically embed:

1. CIA's digital signature (stored in IAM user profile)
2. A QR code (containing verification URL or document hash)

### What's Currently Implemented
**Nothing.** No signature rendering, no QR code generation.

### Suggested Approach (Deferrable)
This is best handled at the Document Records Service level since it already owns document generation. The GRC service would:

1. Request document generation from Document Records Service
2. Document Records Service renders the document with embedded signature + QR code
3. Signature image comes from IAM user profile (signature field exists on IAM User model)
4. QR code generation via `qrcode` Python library

This is a cross-service feature and can be deferred to a later phase.

### Checklist
- [ ] (Deferred) Add QR code generation utility
- [ ] (Deferred) Integrate with Document Records Service for document rendering
- [ ] (Deferred) Pull CIA signature from IAM service
- [ ] (Deferred) Embed signature + QR on approved EN, reports, declarations

---

## 11. GAP 10: Evidence Attachments on Risk Assessments — LOW

### SRS Reference
- **General Requirements:** "support attachment of evidence (policies, reports, data extracts) to support risk ratings"

### Current Implementation
The `RiskAssessment` model has `evidence_attachments = JSONField(default=list)` — the field exists in the backend. But the frontend create/edit form does not expose a file upload widget for this field, and the testing flow (Phase 4) never tests it.

### Fix
1. Add a file upload section in the Risk Assessment create/edit dialog
2. Upload files to Document Records Service (same pattern as Working Papers)
3. Store returned document UUIDs in the `evidence_attachments` JSON array
4. Display download links in the Risk Assessment detail view

### Checklist
- [ ] Frontend: add file upload widget to Risk Assessment create/edit form
- [ ] Frontend: display evidence links in detail view
- [ ] Ensure backend serializer accepts/validates the JSON array of UUIDs

---

## 12. GAP 11: Auto-Generated Prioritized Audit Plan Draft — MEDIUM

### SRS Reference
- **Requirement 40:** "Automatically generate a prioritized, risk-based audit plan draft based on the assessment results"

### What SRS Requires
After risk assessments are approved, the system should be able to auto-generate a draft RBIAP that:

1. Pulls all approved risk assessments for the fiscal year
2. Ranks auditable entities by risk score (highest first)
3. Pre-populates a draft plan with priority areas based on risk rankings

### What's Currently Implemented
The Audit Plan is created manually. Priority areas and resource allocation are empty JSON fields filled manually.

### Suggested Approach
Add a backend endpoint:

- `POST /api/v1/grc/audit/plans/generate-draft/` with `{ "fiscal_year_id": "...", "audit_universe_id": "..." }`
- Queries all approved risk assessments for entities in that universe
- Sorts by weighted risk score descending
- Creates a draft plan with `priority_areas` auto-populated from the top-N highest-risk entities
- Returns the created draft plan for the user to review and adjust

### Checklist
- [ ] Add `generate-draft` endpoint on `AuditPlan` ViewSet
- [ ] Implement risk-based prioritization logic
- [ ] Frontend: "Generate Draft from Risk Assessments" button on Audit Plans page
- [ ] Update testing flow

---

## 13. GAP 12: Risk Management System Integration — LOW (Phase 2)

### SRS Reference
- **Requirement 41:** "Risk Management System Integration: Two-way sync with the Risk Assurance and Quality Management System to feed audit findings as risks and to pull the organizational risk register for audit planning."

### Current Status
The GRC service design document (GRC_AUDIT_SERVICE_DESIGN.md) lists Risk Management System as Phase 2. This is intentionally deferred and not a Phase 1 gap.

### What Will Be Needed (Phase 2)
1. Kafka event publishing when findings are created/finalized → consumed by Risk Management module
2. Risk register import endpoint to pull organizational risks for audit planning
3. Bidirectional sync between audit findings and risk register entries

### Checklist
- [ ] (Phase 2) Define Kafka event schema for finding → risk sync
- [ ] (Phase 2) Build risk register import/export
- [ ] (Phase 2) Two-way sync logic

---

## 14. SRS Requirement Traceability Matrix

Complete mapping of every numbered SRS system requirement to implementation status:

| Req # | SRS Section | Description | Status | Gap # |
|-------|-------------|-------------|--------|-------|
| 1 | Audit Plan | CIA initiates RBIAP preparation | ✅ Implemented | — |
| 2 | Audit Plan | IA drafts RBIAP, submits to CIA | ✅ Implemented | — |
| 3 | Audit Plan | CIA reviews, submits to Management | ✅ Implemented (WO Stage 1) | — |
| 4 | Audit Plan | Management reviews, recommends | ✅ Implemented (WO Stage 2) | — |
| 5 | Audit Plan | CIA submits to Audit Committee | ✅ Implemented (WO Stage 3) | — |
| 6 | Audit Plan | Committee reviews and determines | ✅ Implemented | — |
| 7 | Audit Plan | Committee requests improvement, CIA revises | ✅ Implemented (pending action) | — |
| 8 | Audit Plan | Committee approves, assigns CIA | ✅ Implemented (WO Stage 3 approve) | — |
| 9 | Audit Plan | Generate approved RBIAP output | ✅ Implemented (status → approved) | — |
| 10 | Engagement | CIA appoints LA + team, prepares Audit Memo | ❌ MISSING | GAP 1 |
| 11 | Engagement | LA prepares Audit Memo, submits to CIA | ❌ MISSING | GAP 1 |
| 12 | Engagement | CIA reviews memo, submits to DG | ❌ MISSING | GAP 1 |
| 13 | Engagement | DG reviews and approves memo | ❌ MISSING | GAP 1 |
| 14 | Engagement | CIA transmits approved memo to LA | ❌ MISSING | GAP 1 |
| 15 | Engagement | LA prepares engagement plan, checklists, docs | ⚠️ Partial (engagement has scope/methodology, no separate checklist) | GAP 5 |
| 16 | Engagement | Team signs Declaration of Independence | ❌ MISSING | GAP 2 |
| 17 | Engagement | LA contacts auditable area for arrangements | ⚠️ Covered by engagement notification via workflow | — |
| 18 | Engagement | Generate Approved Memo + Signed Declaration | ❌ MISSING | GAP 1 + 2 |
| 19 | Survey | Preliminary survey + Fraud Risk Assessment | ❌ MISSING | GAP 3 |
| 20 | Survey | Review adequacy of controls, develop tests | ❌ MISSING (no structured control assessment) | GAP 3 |
| 21 | Survey | Inadequate controls → findings + impact tests | ⚠️ Partial (findings exist, no structured test design) | GAP 3 |
| 22 | Survey | LA develops RCM, prepares draft audit program | ❌ MISSING | GAP 4 + 5 |
| 23 | Survey | IA and CIA review/approve audit program | ❌ MISSING | GAP 5 |
| 24 | Survey | LA prepares Engagement Notification | ⚠️ Covered by engagement workflow start | — |
| 25 | Survey | CIA approves EN | ⚠️ Implicit in workflow (no separate EN approval stage) | — |
| 26 | Survey | Generate Approved EN output | ⚠️ Implicit | — |
| 27 | Implementation | Entry meeting | ✅ Implemented (AuditMeeting type=entry_conference) | — |
| 28 | Implementation | Fieldwork tests + document results | ✅ Implemented (WorkingPaper) | — |
| 29 | Implementation | LA reviews evidence, arranges pre-exit | ✅ Implemented (WP review + Meeting type=pre_exit) | — |
| 30 | Implementation | Pre-exit meeting | ✅ Implemented | — |
| 31 | Implementation | Working paper forms submitted to LA | ✅ Implemented (WP submit for review) | — |
| 32 | Implementation | CIA reviews/approves working papers | ✅ Implemented (WP workflow stage 2) | — |
| 33 | Implementation | Audit team meeting prior to exit | ✅ Implemented (Meeting type=audit_team_meeting) | — |
| 34 | Implementation | Exit meeting minutes + attendance | ✅ Implemented (Meeting type=exit_conference) | — |
| 35 | Implementation | Draft audit report + auditee responses | ✅ Implemented (AuditReport + finding responses) | — |
| 35a | Implementation | LA sets risk scoring on findings | ✅ Implemented (Finding has risk_rating FK) | — |
| 36 | Implementation | IA and CIA review/approve draft report | ✅ Implemented (Report status: draft → under_review → approved) | — |
| 37 | Implementation | Print, submittal letter, distribute | ⚠️ Partial (status → distributed exists, no print/letter generation) | GAP 9 |
| 38 | Implementation | Generate Approved Report + Signed Declaration | ⚠️ Partial (report exists, declaration missing) | GAP 2 |
| 39 | Monitoring | Track implementation, evidence, dashboards, escalation | ⚠️ Partial (tracking exists, no auto-escalation, no 5-day enforcement) | GAP 7 |
| 40 | Risk/Universe | Register of entities + auto-generate prioritized plan | ⚠️ Partial (register exists, no auto-generation) | GAP 11 |
| 41 | Integration | Two-way sync with Risk Management System | ❌ Deferred to Phase 2 | GAP 12 |

---

## 15. Suggested Implementation Order

Based on dependency chains and SRS criticality:

### Phase A — High-Priority Entity Gaps (implement together)
These form a connected chain in the pre-engagement flow:

```
1. GAP 1: Audit Memo                   (CRITICAL — new model + 3-stage workflow)
2. GAP 2: Declaration of Independence  (CRITICAL — new model, depends on memo/engagement)
3. GAP 4: Risk & Control Matrix        (HIGH — new models, feeds into audit program)
4. GAP 5: Audit Program                (HIGH — new model + 2-stage workflow, depends on RCM)
5. GAP 3: Audit Survey                 (HIGH — new model, logically before RCM)
```

Suggested order within Phase A:

```
Audit Memo → Declaration → Audit Survey → RCM → Audit Program
```

This mirrors the SRS process flow: Memo approved → Team signs declarations → Preliminary survey → RCM built → Program approved → EN sent → Fieldwork begins.

### Phase B — Computation & Automation Gaps
6. **GAP 6:** Auto Risk Score Calculation (MEDIUM — modifies existing model)
7. **GAP 7:** 5-Day Deadline Enforcement (MEDIUM — new fields + Celery task)
8. **GAP 11:** Auto-Generate Plan Draft (MEDIUM — new endpoint)

### Phase C — Minor Fixes
9. **GAP 8:** Engagement Type Mismatch (LOW — one-line model change + migration)
10. **GAP 10:** Evidence Attachments UI (LOW — frontend-only change)

### Phase D — Cross-Service / Deferred
11. **GAP 9:** QR Code + Signature (LOW — cross-service, deferrable)
12. **GAP 12:** Risk Management Integration (Phase 2)

---

## 16. Files That Will Need Changes

### Backend (grc-service)

| File | Changes |
|------|---------|
| `audit_entities.py` | Add: `AuditMemo`, `DeclarationOfIndependence`, `AuditSurvey`, `RiskControlMatrix`, `RCMEntry`, `AuditProgram`. Modify: `RiskAssessment` (auto-calc fields), `AuditEngagement` (type choices), `ImplementationMonitoring` (deadline fields) |
| `apps/core/models/__init__.py` | Export new models |
| `apps/api/serializers/` | New serializers for each new model. Modify: `RiskAssessmentSerializer`, `EngagementSerializer`, `MonitoringSerializer` |
| `apps/api/views/` | New ViewSets for each new model. Modify: `RiskAssessmentViewSet`, `MonitoringViewSet` |
| `apps/api/urls/` | Add URL routes for new endpoints |
| `apps/core/workflow_entity_paths.py` | Add entity paths for `AuditMemo`, `AuditProgram` |
| `config/permissions/grc-service.json` | Add permissions for new entities |
| `apps/infrastructure/tasks/` | Add `check_monitoring_deadlines` Celery task |
| New migrations | ~6 migration files |

### Frontend (staff-portal/src/components/grc/)

| File/Directory | Changes |
|----------------|---------|
| New: `AuditMemos/` | List page, Create dialog, Detail page |
| New: `Declarations/` | Section in engagement detail |
| New: `AuditSurvey/` | Section in engagement detail |
| New: `RiskControlMatrix/` | Table builder in engagement detail |
| New: `AuditProgram/` | Section in engagement detail (or separate page) |
| Modify: `RiskAssessments/` | Add auto-calculation display, evidence upload |
| Modify: `AuditMonitoring/` | Add deadline badges, notify button, overdue highlighting |
| Modify: `EngagementDetail/` | Add new sections/tabs for survey, RCM, program, declarations |
| Modify: sidebar config | Add Audit Memos entry |
| Modify: API service files | Add API calls for new endpoints |

### Notes
- All new models should follow the established FIMS pattern: `TimestampedModel`, `StatusMixin`, UUID PKs, `created_by` as UUIDField
- All new ViewSets should follow the existing GRC pattern: permission checks via `request.user_permissions_flat`, pagination, filtering
- Workflow-enabled entities should include `WorkflowMixin` and implement `get_workflow_context()`, `get_workflow_metadata()`, `get_workflow_stages()`
- New Kafka notification templates should be registered for memo approval, declaration reminders, deadline alerts
- The nginx gateway `/api/v1/grc/` catch-all route already covers all GRC endpoints — no gateway changes needed

---

---

# POST-IMPLEMENTATION GAP ANALYSIS — 2026-06-22

> **Context:** This section documents gaps identified **after** the Phase A entities (GAP 1–5 above: AuditMemo,
> DeclarationOfIndependence, AuditSurvey, RiskControlMatrix/RCMEntry, AuditProgram) were implemented in
> `apps/core/models/audit_entities.py`. The analysis below reflects the state of the codebase once those models
> exist and focuses on integration correctness, workflow wiring, and SRS requirements that remain unaddressed.
>
> Each gap is labelled with its **source**: 🔴 SRS-backed (traceable to explicit SRS requirement),
> 🟡 Partial SRS (SRS implies it, implementation detail is interpretation), or 🟢 Agent opinion only
> (architectural judgement, not explicitly required by SRS text).

---

## P2-GAP 1: Missing `EngagementNotification` Model 🔴 SRS-BACKED — CRITICAL

### SRS References
- **Requirement 24:** "LA prepares the **Engagement Notification (EN)**"
- **Requirement 25:** "CIA approves the EN (Signature and QR Code embedded automatically)"
- **Requirement 26:** Generate the **Approved Engagement Notification** as a formal output artifact
- **SRS 1.8.3 Steps 9–12:** EN is the formal document issued to the auditable area before fieldwork; it has its own CIA-approval step and QR+signature embed; it is distinct from the `AuditEngagement` record itself

### What SRS Requires
The Engagement Notification is a **separate, approvable document** that:
1. Is prepared by the LA after the Audit Program is approved
2. Contains: audit reference, auditable entity, audit period, team composition, planned dates, and the scope summary from the program
3. Goes through CIA approval before it is transmitted
4. On CIA approval, QR code + CIA digital signature are automatically embedded
5. Is generated as a PDF/document output and distributed to the auditable area

### What Is Currently Implemented
**Nothing.** The current `AuditEngagement` model has a lifecycle workflow (`grc.engagement_notification` template registered in WO) that treats the engagement phase transitions as the notification process. There is no `EngagementNotification` model, no separate EN approval endpoint, and no EN output document.

The `grc.engagement_notification` YAML template has 3 stages (`planning_review`, `fieldwork_initiation`, `reporting_phase`) — these describe engagement lifecycle phases, **not** the EN approval workflow. This is a naming collision.

---

### What Needs to Be Built

---

#### A. New Model: `EngagementNotification` — `apps/core/models/audit_entities.py`

```python
class EngagementNotification(TimestampedModel, WorkflowMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=50, unique=True)
    audit_engagement = models.OneToOneField(
        AuditEngagement, on_delete=models.CASCADE, related_name='engagement_notification'
    )
    audit_program = models.ForeignKey(
        AuditProgram, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications'
    )
    prepared_by = models.UUIDField()                   # LA user ID from IAM
    notification_date = models.DateField()
    audit_period_start = models.DateField()
    audit_period_end = models.DateField()
    audit_team_snapshot = models.JSONField(default=list)   # [{"user_id": "...", "role": "..."}]
    scope_summary = models.TextField()
    approved_by_cia = models.UUIDField(null=True, blank=True)
    cia_approval_date = models.DateTimeField(null=True, blank=True)
    # QR / signature tracking — same pattern as existing stamped_document_url on AuditReport
    stamped_document_url = models.URLField(blank=True, null=True)
    document_id = models.UUIDField(null=True, blank=True)   # DRS document reference

    STATUS_CHOICES = [
        ('draft',       'Draft'),
        ('submitted',   'Submitted for CIA Review'),
        ('approved',    'Approved'),
        ('transmitted', 'Transmitted to Auditable Area'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')

    def get_workflow_context(self):
        return {
            'entity_type': 'engagement_notification',
            'entity_id': str(self.id),
            'engagement_id': str(self.audit_engagement_id),
            'reference_number': self.reference_number,
            'prepared_by': str(self.prepared_by),
        }

    def get_workflow_metadata(self):
        return {
            'title': f'Engagement Notification — {self.reference_number}',
            'prepared_by': str(self.prepared_by),
            'document_type': 'engagement_notification',
        }

    def get_workflow_stages(self):
        return [
            {
                'name': 'CIA Approval',
                'stage_type': 'approval',
                'assignee_resolver': 'role:cia',
                'actions': ['approve', 'return'],
            }
        ]
```

---

#### B. Workflow YAML Template — `apps/core/workflows/workflows.yaml`

This template is registered with the **Work Orchestration Service** at startup to create the CIA approval plan when `start_workflow()` is called.

```yaml
- code: grc.engagement_notification_approval
  name: Engagement Notification Approval
  description: Single-stage CIA approval of the Engagement Notification document before transmission
  stages:
    - name: CIA Approval
      stage_type: approval
      assignee_resolver: "role:cia"
      actions:
        - name: approve
          transitions_to: approved
        - name: return
          transitions_to: draft
```

Also add to `TEMPLATE_CODE_TO_WO_TYPE` in `orchestration_client.py`:
```python
"grc.engagement_notification_approval": "grc_engagement_notification_approval",
```

---

#### C. Notification Templates — `apps/core/templates/notifications.yaml`

These templates are registered with WO at GRC service startup via `TemplateRegistry` → Kafka `notification-templates` topic. WO stores them and uses them to render and deliver multi-channel notifications when GRC publishes `notification.send` events.

> **Architecture note:** GRC already has `NotificationPublisher` (`apps/core/notifications/publisher.py`) and `TemplateRegistry` (`apps/core/templates/registry.py`). Notification templates go into `notifications.yaml` — not into `workflows.yaml`. These are two separate systems: `workflows.yaml` is for approval plan templates; `notifications.yaml` is for message templates.

Add three templates covering the EN lifecycle events:

```yaml
  # ───────────────────────────────────────────────
  # Engagement Notification
  # ───────────────────────────────────────────────

  - code: "grc.engagement_notification.submitted"
    name: "Engagement Notification Submitted for CIA Approval"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "FCC FIMS — Action Required: Engagement Notification Awaiting Your Approval ({{en.reference_number}})"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #0066cc;">Engagement Notification — Approval Required</h2>
            <p>Hello {{cia.first_name}},</p>
            <p>A new Engagement Notification has been submitted for your approval:</p>
            <ul>
              <li><strong>Reference:</strong> {{en.reference_number}}</li>
              <li><strong>Auditable Entity:</strong> {{en.auditable_entity}}</li>
              <li><strong>Audit Period:</strong> {{en.audit_period_start}} to {{en.audit_period_end}}</li>
              <li><strong>Prepared By:</strong> {{la.name}}</li>
              <li><strong>Submitted At:</strong> {{submitted_at}}</li>
            </ul>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{review_url}}" style="background-color: #0066cc; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Review Engagement Notification</a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Best regards,<br>FCC FIMS — Internal Audit Module</p>
          </div>
        </body>
      </html>
    body_text: |
      Engagement Notification — Approval Required

      Hello {{cia.first_name}},

      A new Engagement Notification has been submitted for your approval:
      - Reference: {{en.reference_number}}
      - Auditable Entity: {{en.auditable_entity}}
      - Audit Period: {{en.audit_period_start}} to {{en.audit_period_end}}
      - Prepared By: {{la.name}}
      - Submitted At: {{submitted_at}}

      Review Engagement Notification: {{review_url}}

      Best regards,
      FCC FIMS — Internal Audit Module
    variables:
      - name: "cia.first_name"
        required: true
        type: "string"
        description: "CIA's first name — resolved from IAM before publishing"
      - name: "cia.email"
        required: true
        type: "string"
        description: "CIA's email address — used in recipients.email"
      - name: "en.reference_number"
        required: true
        type: "string"
        description: "EN auto-generated reference number (e.g. EN-ENG-2025/26-001-001)"
      - name: "en.auditable_entity"
        required: true
        type: "string"
        description: "Name of the auditable entity"
      - name: "en.audit_period_start"
        required: true
        type: "string"
        description: "Formatted start date (e.g. 01 Jan 2026)"
      - name: "en.audit_period_end"
        required: true
        type: "string"
        description: "Formatted end date"
      - name: "la.name"
        required: true
        type: "string"
        description: "Full name of the Lead Auditor — resolved from IAM"
      - name: "submitted_at"
        required: true
        type: "string"
        description: "Formatted submission datetime"
      - name: "review_url"
        required: true
        type: "url"
        description: "Staff portal URL to the EN detail page"
    metadata:
      service: "grc"
      domain: "engagement_notification"
      action: "submitted_for_approval"
      priority: "high"
      version: "1.0.0"

  - code: "grc.engagement_notification.approved"
    name: "Engagement Notification Approved by CIA"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "FCC FIMS — Engagement Notification Approved: {{en.reference_number}}"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #28a745;">Engagement Notification Approved</h2>
            <p>Hello {{la.first_name}},</p>
            <p>Your Engagement Notification has been approved by the CIA and a stamped copy has been generated:</p>
            <ul>
              <li><strong>Reference:</strong> {{en.reference_number}}</li>
              <li><strong>Auditable Entity:</strong> {{en.auditable_entity}}</li>
              <li><strong>Approved By:</strong> {{cia.name}}</li>
              <li><strong>Approved At:</strong> {{approved_at}}</li>
            </ul>
            <p>You may now transmit the Engagement Notification to the auditable area and proceed to schedule the entry meeting.</p>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{detail_url}}" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">View Approved EN</a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Best regards,<br>FCC FIMS — Internal Audit Module</p>
          </div>
        </body>
      </html>
    body_text: |
      Engagement Notification Approved

      Hello {{la.first_name}},

      Your Engagement Notification has been approved by the CIA:
      - Reference: {{en.reference_number}}
      - Auditable Entity: {{en.auditable_entity}}
      - Approved By: {{cia.name}}
      - Approved At: {{approved_at}}

      You may now transmit the EN to the auditable area.

      View Approved EN: {{detail_url}}

      Best regards,
      FCC FIMS — Internal Audit Module
    variables:
      - name: "la.first_name"
        required: true
        type: "string"
      - name: "la.email"
        required: true
        type: "string"
      - name: "en.reference_number"
        required: true
        type: "string"
      - name: "en.auditable_entity"
        required: true
        type: "string"
      - name: "cia.name"
        required: true
        type: "string"
      - name: "approved_at"
        required: true
        type: "string"
      - name: "detail_url"
        required: true
        type: "url"
    metadata:
      service: "grc"
      domain: "engagement_notification"
      action: "approved"
      priority: "normal"
      version: "1.0.0"

  - code: "grc.engagement_notification.returned"
    name: "Engagement Notification Returned for Revision"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "FCC FIMS — Engagement Notification Returned for Revision ({{en.reference_number}})"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #dc3545;">Engagement Notification Returned for Revision</h2>
            <p>Hello {{la.first_name}},</p>
            <p>Your Engagement Notification has been returned by the CIA and requires revision:</p>
            <ul>
              <li><strong>Reference:</strong> {{en.reference_number}}</li>
              <li><strong>Returned By:</strong> {{cia.name}}</li>
              <li><strong>Comments:</strong> {{comments}}</li>
            </ul>
            <p>Please review the feedback, make the necessary corrections, and resubmit.</p>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{edit_url}}" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Edit Engagement Notification</a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Best regards,<br>FCC FIMS — Internal Audit Module</p>
          </div>
        </body>
      </html>
    body_text: |
      Engagement Notification Returned for Revision

      Hello {{la.first_name}},

      Your Engagement Notification has been returned by the CIA:
      - Reference: {{en.reference_number}}
      - Returned By: {{cia.name}}
      - Comments: {{comments}}

      Edit Engagement Notification: {{edit_url}}

      Best regards,
      FCC FIMS — Internal Audit Module
    variables:
      - name: "la.first_name"
        required: true
        type: "string"
      - name: "la.email"
        required: true
        type: "string"
      - name: "en.reference_number"
        required: true
        type: "string"
      - name: "cia.name"
        required: true
        type: "string"
      - name: "comments"
        required: false
        type: "string"
        description: "CIA review comments — pre-format as empty string if absent"
      - name: "edit_url"
        required: true
        type: "url"
    metadata:
      service: "grc"
      domain: "engagement_notification"
      action: "returned"
      priority: "high"
      version: "1.0.0"
```

---

#### D. Calling the Publisher from the ViewSet/Service

When the LA submits for approval, when CIA approves, and when CIA returns — the ViewSet action must call `get_notification_publisher()` **after** saving the status change. This is non-blocking (fire-and-forget — wrap in try/except).

```python
# Example: inside EngagementNotificationViewSet, submit_for_approval action
from apps.core.notifications.publisher import get_notification_publisher
from apps.infrastructure.external.iam_client import IAMClient

@action(detail=True, methods=['post'])
def submit(self, request, pk=None):
    en = self.get_object()
    # ... validate status, start WO workflow, save status = 'submitted' ...

    # Resolve CIA user details from IAM
    iam = IAMClient()
    cia_user = iam.get_user_by_role('cia')   # adjust to actual IAM client method

    try:
        publisher = get_notification_publisher()
        publisher.send_notification(
            template_code='grc.engagement_notification.submitted',
            recipients={
                'email': [cia_user['email']],
                'user_ids': [cia_user['id']],
            },
            context={
                'cia': {
                    'first_name': cia_user['first_name'],
                    'email': cia_user['email'],
                },
                'en': {
                    'id': str(en.id),          # included for idempotency key resolution
                    'reference_number': en.reference_number,
                    'auditable_entity': en.audit_engagement.auditable_entity.name,
                    'audit_period_start': en.audit_period_start.strftime('%d %b %Y'),
                    'audit_period_end': en.audit_period_end.strftime('%d %b %Y'),
                },
                'la': {'name': request.user_display_name},
                'submitted_at': timezone.now().strftime('%d %b %Y, %H:%M'),
                'review_url': f"https://staff.fcc.go.tz/service/grc/engagement-notifications/{en.id}",
            },
            priority='high',
            metadata={'user_ids': [cia_user['id']]},
        )
    except Exception as e:
        logger.error(f"Failed to publish EN submitted notification: {e}")
    # notification failure must not block the business response
    return Response(...)
```

The same pattern applies for `approve` and `return` actions — use `grc.engagement_notification.approved` / `grc.engagement_notification.returned` templates and send to the LA's email + user_id.

> **Important:** Resolve all display values (names, formatted dates, URLs) **before** calling the publisher. WO's `TemplateRenderer` does `{{variable}}` substitution only — it does not call IAM or any other service at render time.

---

#### E. API Endpoints

- `GET/POST /api/v1/grc/audit/engagement-notifications/`
- `GET/PUT/DELETE /api/v1/grc/audit/engagement-notifications/{id}/`
- `POST /api/v1/grc/audit/engagement-notifications/{id}/submit/`
- `POST /api/v1/grc/audit/engagement-notifications/{id}/start-workflow/`
- `POST /api/v1/grc/audit/engagement-notifications/{id}/transmit/`

#### Flow Change
Current: `Approved Program → Start Engagement Workflow (lifecycle phases)`

Correct:
```
Approved Program
    → LA creates EN (status: draft)
    → LA submits (status: submitted) + WO approval plan created + CIA notified via Kafka
    → CIA approves in Workflow Console (status: approved) + LA notified via Kafka
    → QR code + signature embedded (DRS call)
    → LA transmits EN (status: transmitted) → Fieldwork begins
```

---

### Checklist

#### Model & Migration
- [ ] Add `EngagementNotification` model to `apps/core/models/audit_entities.py`
- [ ] Add `get_workflow_context()`, `get_workflow_metadata()`, `get_workflow_stages()` methods
- [ ] Export from `apps/core/models/__init__.py`
- [ ] Create migration

#### Workflow Plan Integration (WO — `workflows.yaml`)
- [ ] Add `grc.engagement_notification_approval` to `apps/core/workflows/workflows.yaml`
- [ ] Add `"grc.engagement_notification_approval": "grc_engagement_notification_approval"` to `TEMPLATE_CODE_TO_WO_TYPE` in `orchestration_client.py`
- [ ] Rename existing `grc.engagement_notification` entry in `workflows.yaml` → `grc.engagement_lifecycle` (remove naming collision)
- [ ] Update corresponding `TEMPLATE_CODE_TO_WO_TYPE` key for the lifecycle template

#### Notification Templates (WO — `notifications.yaml`)
- [ ] Add `grc.engagement_notification.submitted` to `apps/core/templates/notifications.yaml`
- [ ] Add `grc.engagement_notification.approved` to `apps/core/templates/notifications.yaml`
- [ ] Add `grc.engagement_notification.returned` to `apps/core/templates/notifications.yaml`
- [ ] Verify templates are picked up by `TemplateRegistry.register_templates()` on startup (check log: `"Registered N notification template(s)"`)

#### API Layer
- [ ] Create `EngagementNotificationSerializer` (Create + Detail variants)
- [ ] Create `EngagementNotificationViewSet` with CRUD + `submit` + `start-workflow` + `transmit` actions
- [ ] Add URL routes under `/api/v1/grc/audit/engagement-notifications/` in `apps/api/urls/audit.py`
- [ ] Add permissions to `config/permissions/grc-service.json`

#### Business Logic
- [ ] Business guard on `submit`: engagement must be in `planning` phase, `AuditProgram` must be `approved`
- [ ] `submit` action: save status → `submitted`, call `OrchestrationClient.start_workflow('grc.engagement_notification_approval', ...)`, save `WorkflowMixin` fields, publish `grc.engagement_notification.submitted` via `NotificationPublisher`
- [ ] `approve` webhook/callback: save status → `approved`, save `approved_by_cia` + `cia_approval_date`, trigger DRS for QR+signature embed, publish `grc.engagement_notification.approved`
- [ ] `return` webhook/callback: save status → `draft`, publish `grc.engagement_notification.returned`
- [ ] `transmit` action: save status → `transmitted`, update `AuditEngagement.status` → `fieldwork`

#### Frontend
- [ ] EN detail section/page in engagement detail (tab or separate page)
- [ ] Create EN form: audit period, team snapshot, scope summary
- [ ] CIA approval action calls `POST /{id}/submit/` then `POST /{id}/start-workflow/`
- [ ] Show `stamped_document_url` link after approval (QR+signature embedded document)

---

## P2-GAP 2: Missing Workflow YAML Templates 🔴 SRS-BACKED — CRITICAL

### Context
`apps/core/workflows/workflows.yaml` is the source of truth for all GRC workflow templates. At service startup, `WorkflowTemplateRegistry` reads this file and publishes each template to WO via Kafka (`workflow-templates` topic). WO stores them as `WorkflowTemplate` records. When GRC later calls `OrchestrationClient.start_workflow(template_code=...)`, the client calls `_get_template_id_by_code()` which queries `GET /api/v1/workflow/templates/` and looks up by `workflow_type`. If a template was never published (not in YAML), WO returns no match and the client falls back to inline stages — or fails silently if no inline stages are provided either.

`TEMPLATE_CODE_TO_WO_TYPE` in `orchestration_client.py` is the runtime mapping from GRC template code → WO `workflow_type` string. A code referenced here but absent from `workflows.yaml` will never be seeded into WO.

---

### Actual Current State (source-verified)

**Templates present in `workflows.yaml`:**
- `grc.working_paper_approval`
- `grc.audit_universe_approval`
- `grc.rbiap_approval`
- `grc.engagement_notification` (engagement lifecycle — see P2-GAP 1 for naming collision)

**`TEMPLATE_CODE_TO_WO_TYPE` in `orchestration_client.py` (current, verified):**
```python
TEMPLATE_CODE_TO_WO_TYPE: Dict[str, str] = {
    "grc.working_paper_approval":  "grc_working_paper_approval",    # ✅ in YAML
    "grc.audit_universe_approval": "grc_audit_universe_approval",   # ✅ in YAML
    "grc.rbiap_approval":          "grc_rbiap_approval",            # ✅ in YAML
    "grc.engagement_notification": "grc_engagement_lifecycle",      # ✅ in YAML (name collision)
    "grc.audit_report_approval":   "grc_audit_report_approval",     # ❌ in dict but NOT in YAML
}
```

**Gap summary — templates that are missing or incomplete:**

| Template Code | In `TEMPLATE_CODE_TO_WO_TYPE` | In `workflows.yaml` | SRS Requirement |
|---|:---:|:---:|---|
| `grc.audit_report_approval` | ✅ already | ❌ missing | SRS Req 36 (IA → CIA, 2-stage) |
| `grc.audit_memo_approval` | ❌ missing | ❌ missing | SRS Req 11–13 (CIA → DG, 2-stage) |
| `grc.audit_program_approval` | ❌ missing | ❌ missing | SRS Req 22–23 (IA → CIA, 2-stage) |
| `grc.quarterly_report_approval` | ❌ missing | ❌ missing | SRS 1.8.5 (CIA → Mgmt → Committee → Commission) |
| `grc.engagement_notification_approval` | ❌ missing | ❌ missing | SRS Req 25 (CIA single-stage — see P2-GAP 1) |

`grc.engagement_notification_approval` is covered by P2-GAP 1 — listed here for completeness.

---

### Required Additions to `workflows.yaml`

The exact field names and nesting must match the current file (`workflow_type`, `version`, `definition`, `definitionKey`, `order`, `assignees`, `nextState`, `label` — matching WO's `StageInputSerializer`):

```yaml
  # ── Audit Memo Approval (SRS Req 11–14) ─────────────────────────────────────
  # LA prepares memo → CIA reviews and forwards to DG → DG approves
  # CIA then transmits the approved memo to LA (GRC ViewSet action, not a WO stage)
  - code: "grc.audit_memo_approval"
    name: "Audit Memo Approval"
    workflow_type: "grc"
    version: 1
    definition:
      description: "2-stage approval: CIA reviews the audit memo and forwards to DG; DG approves"
      sla:
        targetMinutes: 10080         # 7 days overall
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "audit_memo"
      stages:
        - definitionKey: "cia_memo_review"
          name: "CIA Review"
          order: 1
          assignees: []
          actions:
            - name: "forward_to_dg"
              label: "Forward to DG"
              nextState: "completed"
            - name: "return"
              label: "Return to LA"
              nextState: "rejected"
          sla:
            durationMinutes: 4320
            breachStrategy: "notify"

        - definitionKey: "dg_memo_approval"
          name: "DG Approval"
          order: 2
          assignees: []
          actions:
            - name: "approve"
              label: "Approve"
              nextState: "completed"
            - name: "return"
              label: "Return to CIA"
              nextState: "pending"
          sla:
            durationMinutes: 5760
            breachStrategy: "notify"

  # ── Audit Program Approval (SRS Req 22–23) ───────────────────────────────────
  # LA prepares program → IA reviews → CIA approves
  - code: "grc.audit_program_approval"
    name: "Audit Program Approval"
    workflow_type: "grc"
    version: 1
    definition:
      description: "2-stage approval: IA endorses and CIA approves the audit program"
      sla:
        targetMinutes: 14400         # 10 days overall
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "audit_program"
      stages:
        - definitionKey: "ia_program_review"
          name: "IA Review"
          order: 1
          assignees: ["role:grc_reviewer"]
          actions:
            - name: "endorse"
              label: "Endorse & Forward to CIA"
              nextState: "completed"
            - name: "return"
              label: "Return for Revision"
              nextState: "rejected"
          sla:
            durationMinutes: 5760
            breachStrategy: "notify"

        - definitionKey: "cia_program_approval"
          name: "CIA Approval"
          order: 2
          assignees: []
          actions:
            - name: "approve"
              label: "Approve"
              nextState: "completed"
            - name: "return"
              label: "Return for Revision"
              nextState: "pending"
          sla:
            durationMinutes: 8640
            breachStrategy: "notify"

  # ── Audit Report Final Approval (SRS Req 36) ─────────────────────────────────
  # IA reviews draft report → CIA approves for distribution
  # NOTE: grc.audit_report_approval is already in TEMPLATE_CODE_TO_WO_TYPE
  #       but the YAML definition was missing — adding it here fixes the gap.
  - code: "grc.audit_report_approval"
    name: "Audit Report Approval"
    workflow_type: "grc"
    version: 1
    definition:
      description: "2-stage final approval: IA reviews and CIA approves the audit report"
      sla:
        targetMinutes: 10080         # 7 days overall
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "audit_report"
      stages:
        - definitionKey: "ia_report_review"
          name: "IA Review"
          order: 1
          assignees: ["role:grc_reviewer"]
          actions:
            - name: "endorse"
              label: "Endorse & Forward to CIA"
              nextState: "completed"
            - name: "return"
              label: "Return for Revision"
              nextState: "rejected"
          sla:
            durationMinutes: 4320
            breachStrategy: "notify"

        - definitionKey: "cia_report_approval"
          name: "CIA Approval"
          order: 2
          assignees: []
          actions:
            - name: "approve"
              label: "Approve for Distribution"
              nextState: "completed"
            - name: "return"
              label: "Return for Revision"
              nextState: "pending"
          sla:
            durationMinutes: 5760
            breachStrategy: "notify"

  # ── Quarterly Audit Report Approval (SRS 1.8.5) ──────────────────────────────
  # Mirrors grc.rbiap_approval pattern: CIA → Management → Committee → Commission
  - code: "grc.quarterly_report_approval"
    name: "Quarterly Report Approval"
    workflow_type: "grc"
    version: 1
    definition:
      description: "Multi-stage quarterly report approval: CIA → Management → Committee → Commission"
      sla:
        targetMinutes: 40320         # ~28 days overall (same as RBIAP)
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "quarterly_report"
      stages:
        - definitionKey: "cia_qr_review"
          name: "CIA Review"
          order: 1
          assignees: []
          actions:
            - name: "approve"
              label: "Approve"
              nextState: "completed"
            - name: "return"
              label: "Return for Revision"
              nextState: "rejected"
          sla:
            durationMinutes: 4320
            breachStrategy: "notify"

        - definitionKey: "management_qr_review"
          name: "Management Review"
          order: 2
          assignees: []
          actions:
            - name: "adopt"
              label: "Adopt"
              nextState: "completed"
            - name: "request_changes"
              label: "Request Changes"
              nextState: "pending"
          sla:
            durationMinutes: 10080
            breachStrategy: "notify"

        - definitionKey: "committee_qr_review"
          name: "Audit Committee Review"
          order: 3
          assignees: []
          actions:
            - name: "approve"
              label: "Approve"
              nextState: "completed"
            - name: "request_improvement"
              label: "Request Improvement"
              nextState: "pending"
          sla:
            durationMinutes: 14400
            breachStrategy: "notify"

        - definitionKey: "commission_qr_noting"
          name: "Commission Noting"
          order: 4
          assignees: []
          actions:
            - name: "note"
              label: "Note"
              nextState: "completed"
          sla:
            durationMinutes: 10080
            breachStrategy: "notify"
```

---

### Required Additions to `TEMPLATE_CODE_TO_WO_TYPE`

Three new codes must be added to `orchestration_client.py`. `grc.audit_report_approval` is already present. Add the following to the `TEMPLATE_CODE_TO_WO_TYPE` dict:

```python
TEMPLATE_CODE_TO_WO_TYPE: Dict[str, str] = {
    # existing entries (unchanged):
    "grc.working_paper_approval":          "grc_working_paper_approval",
    "grc.audit_universe_approval":         "grc_audit_universe_approval",
    "grc.rbiap_approval":                  "grc_rbiap_approval",
    "grc.engagement_notification":         "grc_engagement_lifecycle",
    "grc.audit_report_approval":           "grc_audit_report_approval",
    # new entries (add these):
    "grc.audit_memo_approval":             "grc_audit_memo_approval",
    "grc.audit_program_approval":          "grc_audit_program_approval",
    "grc.quarterly_report_approval":       "grc_quarterly_report_approval",
    "grc.engagement_notification_approval":"grc_engagement_notification_approval",  # P2-GAP 1
}
```

> **WO type string convention** (verified from existing entries): replace dots with underscores in the full template code. Exception: `grc.engagement_notification` maps to `grc_engagement_lifecycle` (intentional rename to remove the naming collision — see P2-GAP 1 checklist).

---

### Service Layer Integration (how `start_workflow` is called)

Every entity that starts a workflow must follow the `AuditPlanService.submit_for_approval()` pattern exactly — this is the only approved FIMS pattern:

1. Define `WORKFLOW_TEMPLATE_CODE` on the service class
2. Call `entity.get_workflow_context()` for assignee-resolution variables
3. Call `entity.get_workflow_metadata()` for WO plan display data
4. Call `client.start_workflow(template_code, context, initiator_id, subject_ref, metadata, stages=entity.get_workflow_stages())`
5. On success, save all 5 `WorkflowMixin` fields: `workflow_plan_id`, `workflow_stage`, `workflow_stage_id`, `workflow_started_at`, plus the entity status change — in a single `save(update_fields=[...])`

The `stages=entity.get_workflow_stages()` inline fallback must be provided so the workflow can start even against a WO instance where templates haven't been seeded yet.

For `get_workflow_stages()` on each new model, the stage dict format must match what WO's `StageInputSerializer` accepts. **Python inline uses snake_case and 0-indexed order** (source-verified from `WorkingPaper.get_workflow_stages()` at `audit_entities.py` line 1231 — all keys are snake_case; `order` starts at 0):

```python
def get_workflow_stages(self):
    # Inline fallback — mirrors the YAML stage definitions exactly.
    # NOTE: Python dict uses snake_case keys and 0-indexed order —
    #       unlike the YAML which uses camelCase and 1-indexed order.
    return [
        {
            "definition_key": "cia_memo_review",   # snake_case (not definitionKey)
            "name": "CIA Review",
            "order": 0,                             # 0-indexed (not 1)
            "assignees": [],
            "actions": [
                {"name": "forward_to_dg", "label": "Forward to DG", "next_state": "completed"},  # next_state
                {"name": "return", "label": "Return to LA", "next_state": "rejected"},
            ],
        },
        {
            "definition_key": "dg_memo_approval",
            "name": "DG Approval",
            "order": 1,
            "assignees": [],
            "actions": [
                {"name": "approve", "label": "Approve", "next_state": "completed"},
                {"name": "return", "label": "Return to CIA", "next_state": "pending"},
            ],
        },
    ]
```

---

### Checklist

#### `workflows.yaml` additions
- [ ] Add `grc.audit_memo_approval` YAML block (2-stage: cia_memo_review → dg_memo_approval)
- [ ] Add `grc.audit_program_approval` YAML block (2-stage: ia_program_review → cia_program_approval)
- [ ] Add `grc.audit_report_approval` YAML block (2-stage: ia_report_review → cia_report_approval)
- [ ] Add `grc.quarterly_report_approval` YAML block (4-stage: mirrors `grc.rbiap_approval` pattern)

#### `orchestration_client.py` — `TEMPLATE_CODE_TO_WO_TYPE` additions
- [ ] Add `"grc.audit_memo_approval": "grc_audit_memo_approval"`
- [ ] Add `"grc.audit_program_approval": "grc_audit_program_approval"`
- [ ] Add `"grc.quarterly_report_approval": "grc_quarterly_report_approval"`
- [ ] Add `"grc.engagement_notification_approval": "grc_engagement_notification_approval"` (P2-GAP 1)

#### Model methods (inline fallback stages)
- [ ] Implement `get_workflow_stages()` on `AuditMemo` — 2 stages matching `grc.audit_memo_approval` YAML
- [ ] Implement `get_workflow_context()` and `get_workflow_metadata()` on `AuditMemo`
- [ ] Implement `get_workflow_stages()` on `AuditProgram` — 2 stages matching `grc.audit_program_approval` YAML
- [ ] Implement `get_workflow_context()` and `get_workflow_metadata()` on `AuditProgram`
- [ ] Implement `get_workflow_stages()` on `AuditReport` — 2 stages matching `grc.audit_report_approval` YAML
- [ ] Implement `get_workflow_context()` and `get_workflow_metadata()` on `AuditReport`
- [ ] Implement `get_workflow_stages()` on `QuarterlyAuditReport` — 4 stages matching `grc.quarterly_report_approval` YAML (see P2-GAP 3)

#### Service classes (follow `AuditPlanService` pattern exactly)
- [ ] Create `AuditMemoService` with `submit_for_approval()` using `grc.audit_memo_approval`
- [ ] Create `AuditProgramService` with `submit_for_approval()` using `grc.audit_program_approval`
- [ ] Create `AuditReportService` with `submit_for_approval()` using `grc.audit_report_approval`
- [ ] Verify `QuarterlyReportService` exists and uses `grc.quarterly_report_approval` (see P2-GAP 3)

---

## P2-GAP 3: `QuarterlyAuditReport` Bypasses Work Orchestration 🔴 SRS-BACKED — HIGH

### SRS References
- **SRS 1.8.5:** Quarterly Report goes through a multi-stage approval chain ending with submission to the Commission
- **FIMS Architecture Principle 2:** The Work Orchestration Service is the **sole** authority for approval workflows — no service may implement its own approval state machine

### What Is Currently Implemented (source-verified)
`QuarterlyAuditReport` inherits `WorkflowMixin` and already has all 5 mixin fields (`workflow_plan_id`, `workflow_stage`, `workflow_stage_id`, `workflow_started_at`, `workflow_completed_at`). It also defines 7 `STATUS_CHOICES`:
```
draft → cia_review → management_review → committee_review → improvement_required → approved → submitted_to_commission
```
The model has `prepared_by` (UUIDField), `fiscal_year` (FK), `quarter` (FK), `reference_number`, and `title` fields — all needed for workflow context/metadata.

**What is missing:** The model has **no** `get_workflow_context()`, `get_workflow_metadata()`, or `get_workflow_stages()` methods. There is no `QuarterlyReportService`. Views write `status` directly (bypassing WO entirely). The `WorkflowMixin` fields are never populated.

### Root Cause
`get_workflow_stages()` was never implemented, so `OrchestrationClient.start_workflow()` was never called. Status transitions happen as raw field writes. WO never creates a plan, no reviewer gets a task, no audit trail exists in WO.

---

### Fix

All three methods and the service class must follow the exact pattern used by `AuditUniverse` / `AuditPlan` / `WorkingPaper` — the only approved FIMS pattern. Key conventions verified from source:
- Stage dict key: `"definition_key"` (snake_case — **not** `"definitionKey"`)
- Action key: `"next_state"` (snake_case — **not** `"nextState"`)
- `"order"` starts at `0`
- Actions are **dicts** `{"name": ..., "label": ..., "next_state": ...}` — **not strings**
- Each stage includes `"form_schema"` and `"sla": {"targetHours": N}`

---

#### Step 1 — Add `get_workflow_context()`, `get_workflow_metadata()`, `get_workflow_stages()` to `QuarterlyAuditReport`

Add inside the `QuarterlyAuditReport` class body, after the `__str__` method:

```python
def get_workflow_context(self) -> dict:
    """
    Context variables for WO assignee resolution (FIMS pattern).
    Matches AuditPlan.get_workflow_context() structure.
    """
    return {
        "quarterly_report_id": str(self.id),
        "prepared_by": str(self.prepared_by),
        "fiscal_year_id": str(self.fiscal_year_id),
        "quarter_id": str(self.quarter_id),
        "reference_number": self.reference_number,
    }

def get_workflow_metadata(self) -> dict:
    """
    Metadata stored with the WO plan (displayed in console UI).
    Matches AuditPlan.get_workflow_metadata() pattern exactly.
    """
    meta = {
        "entity_type": "quarterly_audit_report",
        "entity_id": str(self.id),
        "reference_number": self.reference_number,
        "title": self.title,
        "fiscal_year": self.fiscal_year.year_code,
        "quarter": str(self.quarter),
        "prepared_by": str(self.prepared_by),
        "status": self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, "quarterly_audit_report")

def get_workflow_stages(self) -> list:
    """
    Inline stage definitions for WO plan creation (FIMS pattern — inline fallback).
    4 stages mirroring grc.quarterly_report_approval in workflows.yaml.
    Key names: definition_key / next_state (snake_case — verified from AuditPlan).
    order starts at 0.
    """
    return [
        {
            "definition_key": "cia_qr_review",
            "name": "CIA Review",
            "order": 0,
            "assignees": [],
            "actions": [
                {"name": "approve", "label": "Approve",             "next_state": "completed"},
                {"name": "return",  "label": "Return for Revision", "next_state": "rejected"},
            ],
            "form_schema": {
                "fields": [{"name": "comments", "type": "textarea", "required": False}]
            },
            "sla": {"targetHours": 72},
        },
        {
            "definition_key": "management_qr_review",
            "name": "Management Review",
            "order": 1,
            "assignees": [],
            "actions": [
                {"name": "adopt",           "label": "Adopt",           "next_state": "completed"},
                {"name": "request_changes", "label": "Request Changes", "next_state": "pending"},
            ],
            "form_schema": {
                "fields": [{"name": "comments", "type": "textarea", "required": False}]
            },
            "sla": {"targetHours": 168},
        },
        {
            "definition_key": "committee_qr_review",
            "name": "Audit Committee Review",
            "order": 2,
            "assignees": [],
            "actions": [
                {"name": "approve",             "label": "Approve",             "next_state": "completed"},
                {"name": "request_improvement", "label": "Request Improvement", "next_state": "pending"},
            ],
            "form_schema": {
                "fields": [{"name": "comments", "type": "textarea", "required": False}]
            },
            "sla": {"targetHours": 240},
        },
        {
            "definition_key": "commission_qr_noting",
            "name": "Commission Noting",
            "order": 3,
            "assignees": [],
            "actions": [
                {"name": "note", "label": "Note", "next_state": "completed"},
            ],
            "form_schema": {
                "fields": [{"name": "comments", "type": "textarea", "required": False}]
            },
            "sla": {"targetHours": 168},
        },
    ]
```

---

#### Step 2 — Create `QuarterlyReportService` — `apps/core/services/quarterly_report_service.py`

Must mirror `audit_plan_service.py` exactly: class with `WORKFLOW_TEMPLATE_CODE`, `@transaction.atomic`, `select_for_update()`, double-submission guard, positional `start_workflow` args, `WorkflowPlanResult` dataclass field access (`.plan_id`, `.current_stage_name`, `.current_stage_id`), all 5 `WorkflowMixin` fields saved together in one `save(update_fields=[...])`:

```python
"""
Service for Quarterly Audit Report workflow integration (FIMS pattern).

Mirrors audit_plan_service.py exactly:
  - calls report.get_workflow_context()  → assignee-resolution variables
  - calls report.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...) → guide §4.3 signature
  - accesses result as WorkflowPlanResult dataclass (.plan_id, .current_stage_name, etc.)
  - saves all 5 WorkflowMixin fields in a single save(update_fields=[...])

Template: grc.quarterly_report_approval (4-stage: cia_qr_review → management_qr_review
          → committee_qr_review → commission_qr_noting)
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.core.models import QuarterlyAuditReport
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class QuarterlyReportService:

    WORKFLOW_TEMPLATE_CODE = "grc.quarterly_report_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(
        self,
        report_id: str,
        submitter_id: str,
        auth_token: str | None = None,
    ):
        """
        Submit a quarterly report to Work Orchestration for the 4-stage approval chain.

        Follows audit_plan_service.py pattern exactly:
          1. select_for_update() — prevent concurrent double-submission
          2. Guard against already-started workflow
          3. get_workflow_context()  — context for WO assignee resolution
          4. get_workflow_metadata() — display data stored in the WO plan
          5. start_workflow()        — guide §4.3 positional signature
          6. Save all 5 WorkflowMixin fields + status in one save(update_fields=[...])
        """
        report = QuarterlyAuditReport.objects.select_for_update().get(id=report_id)

        # Guard: do not start a second workflow if one already exists
        if report.workflow_plan_id:
            logger.info(
                "QuarterlyAuditReport %s already has workflow plan %s — skipping",
                report.id,
                report.workflow_plan_id,
            )
            return report

        # Step 1 — context: variables used by WO to resolve stage assignees
        context = report.get_workflow_context()

        # Step 2 — metadata: display data stored with the plan in WO
        metadata = report.get_workflow_metadata()

        # Step 3 — start workflow (guide §4.3 positional signature)
        # stages= provides inline fallback when WO templates have not been seeded yet
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(report.id),
            metadata=metadata,
            stages=report.get_workflow_stages(),
            auth_token=auth_token,
        )

        # Step 4 — persist all 5 WorkflowMixin fields (result is WorkflowPlanResult dataclass)
        if result and result.plan_id:
            report.workflow_plan_id = result.plan_id
            report.workflow_stage = result.current_stage_name or ""
            report.workflow_stage_id = result.current_stage_id or None
            report.workflow_started_at = timezone.now()
            report.status = "cia_review"
            report.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for QuarterlyAuditReport %s (stage: %s)",
                result.plan_id,
                report.id,
                result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for QuarterlyAuditReport %s", report.id)

        return report
```

---

#### Step 3 — Add `submit-for-approval` endpoint to `QuarterlyAuditReportViewSet`

Follows the same ViewSet pattern as `AuditPlanViewSet`:

```python
@action(detail=True, methods=['post'], url_path='submit-for-approval')
def submit_for_approval(self, request, pk=None):
    report = self.get_object()
    if report.status != 'draft':
        return Response(
            {'error': f"Cannot submit report with status '{report.status}'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    service = QuarterlyReportService()
    report = service.submit_for_approval(
        report_id=str(report.id),
        submitter_id=str(request.user.id),
        auth_token=request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '') or None,
    )
    return Response({
        'id': str(report.id),
        'status': report.status,
        'workflow_plan_id': str(report.workflow_plan_id) if report.workflow_plan_id else None,
        'workflow_stage': report.workflow_stage,
        'message': 'Submitted for CIA review',
    })
```

---

### Checklist

#### Model (`audit_entities.py`)
- [ ] Add `get_workflow_context()` to `QuarterlyAuditReport` — use `quarterly_report_id`, `prepared_by`, `fiscal_year_id`, `quarter_id`, `reference_number`
- [ ] Add `get_workflow_metadata()` to `QuarterlyAuditReport` — use `entity_type`, `entity_id`, all display fields, call `add_entity_detail_path_to_metadata(meta, "quarterly_audit_report")`
- [ ] Add `get_workflow_stages()` to `QuarterlyAuditReport` — 4 stages, `definition_key`/`next_state` (snake_case), `order` starts at `0`, actions as dicts, include `form_schema` and `sla: {targetHours: N}`

#### Service class
- [ ] Create `apps/core/services/quarterly_report_service.py` as a class `QuarterlyReportService` with `WORKFLOW_TEMPLATE_CODE = "grc.quarterly_report_approval"`
- [ ] `submit_for_approval(report_id, submitter_id, auth_token)` — `@transaction.atomic`, `select_for_update()`, double-submission guard, correct `start_workflow()` positional args, access `result.plan_id` / `result.current_stage_name` / `result.current_stage_id` (dataclass fields, not dict keys)

#### ViewSet
- [ ] Add `submit-for-approval` action to `QuarterlyAuditReportViewSet` with `draft`-only guard
- [ ] Restrict direct `status` field writes in existing ViewSet methods — require WO callback for all post-draft transitions

#### Supporting registrations
- [ ] Add `"quarterly_audit_report"` to `ENTITY_DETAIL_PATHS` in `apps/core/workflow_entity_paths.py` with the correct staff portal path
- [ ] Ensure `grc.quarterly_report_approval` YAML block exists (see P2-GAP 2 checklist)
- [ ] Ensure `"grc.quarterly_report_approval": "grc_quarterly_report_approval"` is in `TEMPLATE_CODE_TO_WO_TYPE` (see P2-GAP 2 checklist)

---

## P2-GAP 4: `ImplementationMonitoring` OneToOne Cannot Track Multiple Cycles 🟡 PARTIAL SRS — MEDIUM

### SRS References
- **SRS 1.8.6 Step 3:** "Auditee respond to the list **within five days**" — this is a timestamped event per cycle
- **SRS 1.8.6 Step 4:** "Internal Auditor will verify the auditee's assertion and attached evidence" — implies iterative review cycles
- **General Requirements:** "Track implementation progress of audit recommendations over multiple reporting periods"
- The SRS describes an **iterative cycle of follow-up** (auditee submits → auditor verifies → if incomplete, cycle repeats) rather than a single snapshot

### What Is Currently Implemented

```python
# apps/core/models/audit_entities.py — line 1041 (source-verified)
class ImplementationMonitoring(TimestampedModel, StatusMixin):
    recommendation = models.OneToOneField(
        AuditRecommendation, on_delete=models.CASCADE, related_name='monitoring'
    )
    last_review_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    implementation_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    progress_notes = models.TextField(blank=True)
    evidence_documents = models.JSONField(default=list, blank=True)
    reviewed_by = models.UUIDField(null=True, blank=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    response_deadline = models.DateTimeField(null=True, blank=True)   # DateTimeField, not DateField
    auditee_responded_at = models.DateTimeField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)
    escalated = models.BooleanField(default=False)

    class Meta:
        db_table = 'grc_implementation_monitoring'
        ordering = ['-last_review_date']
```

The `OneToOneField` means there is exactly **one** monitoring record per recommendation. The existing review endpoint (`POST /implementation-monitoring/<pk>/review/`) overwrites these fields in-place on every review:

```python
# apps/api/views/implementation_monitoring_views.py — ImplementationMonitoringReviewView.post()
# (source-verified)
monitoring.implementation_progress = progress          # overwritten each review — history lost
monitoring.progress_notes = progress_notes            # overwritten each review — history lost
monitoring.evidence_documents = evidence_documents    # overwritten each review — history lost
monitoring.last_review_date = timezone.now().date()   # overwritten each review — history lost
monitoring.reviewed_by = user_id                      # overwritten each review — history lost
monitoring.save(update_fields=[
    'implementation_progress', 'progress_notes', 'evidence_documents',
    'last_review_date', 'next_review_date', 'reviewed_by'
])
```

Similarly, `notification_sent_at`, `response_deadline`, and `auditee_responded_at` are single-slot fields on the header — if a second notification+response cycle begins, the previous cycle's data is overwritten.

**Result:** there is no history of how implementation progressed across multiple review cycles or reporting quarters.

### Required Design Change

Split into two entities following existing FIMS `audit_entities.py` patterns (`TimestampedModel, StatusMixin`):

**1. `ImplementationMonitoring` — remains 1:1 header; retains latest-state snapshot for fast dashboard reads:**

```python
# Remove: implementation_progress, progress_notes, evidence_documents
#         (these move to AuditeeFollowUpResponse)
# Add:    latest_progress (denormalized from latest follow_up_response for fast reads)
# Keep:   last_review_date, next_review_date, reviewed_by, notification_sent_at,
#          response_deadline, auditee_responded_at, is_overdue, escalated
class ImplementationMonitoring(TimestampedModel, StatusMixin):
    recommendation = models.OneToOneField(
        AuditRecommendation, on_delete=models.CASCADE, related_name='monitoring'
    )
    last_review_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    latest_progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )  # denormalized for dashboard reads — updated by review view after each cycle
    reviewed_by = models.UUIDField(null=True, blank=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    response_deadline = models.DateTimeField(null=True, blank=True)
    auditee_responded_at = models.DateTimeField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)
    escalated = models.BooleanField(default=False)

    class Meta:
        db_table = 'grc_implementation_monitoring'
        ordering = ['-last_review_date']
```

**2. `AuditeeFollowUpResponse` — new M:1, one row per review cycle (following `TimestampedModel, StatusMixin` pattern from `audit_entities.py`):**

```python
class AuditeeFollowUpResponse(TimestampedModel, StatusMixin):
    """
    One record per review cycle for an ImplementationMonitoring header.
    Follows TimestampedModel + StatusMixin pattern from audit_entities.py.
    StatusMixin provides: status field (pending / submitted / verified / rejected).
    """
    monitoring = models.ForeignKey(
        ImplementationMonitoring,
        on_delete=models.CASCADE,
        related_name='follow_up_responses',
    )
    cycle_number = models.PositiveIntegerField()            # 1, 2, 3 … incremented in view layer
    notified_at = models.DateTimeField(null=True, blank=True)
    response_deadline = models.DateTimeField(null=True, blank=True)
    submitted_by = models.UUIDField(null=True, blank=True)  # auditee user ID
    submitted_at = models.DateTimeField(null=True, blank=True)
    implementation_progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )
    progress_notes = models.TextField(blank=True)
    evidence_documents = models.JSONField(default=list, blank=True)
    is_overdue = models.BooleanField(default=False)
    verified_by = models.UUIDField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_auditee_follow_up_response'
        ordering = ['monitoring', 'cycle_number']
        unique_together = [['monitoring', 'cycle_number']]
```

**Cycle flow:**
1. Auditor calls `POST /implementation-monitoring/<pk>/review/` → creates a new `AuditeeFollowUpResponse` row (cycle_number auto-incremented to `max(cycle_number)+1`); copies `response_deadline` back to header for quick query
2. System calls `POST /implementation-monitoring/<pk>/notify-auditee/` → sets `AuditeeFollowUpResponse.notified_at` + `response_deadline` on the current open cycle; mirrors timestamps to header `notification_sent_at` / `response_deadline`
3. Auditee submits → `POST /follow-up-responses/<pk>/submit/` → sets `submitted_by`, `submitted_at`, `implementation_progress`, `progress_notes`, `evidence_documents`, status → `submitted`; updates header `auditee_responded_at`
4. Auditor verifies → `POST /follow-up-responses/<pk>/verify/` → status → `verified` or `rejected`; if `rejected`, new cycle begins from step 1; updates header `latest_progress`
5. On final completion: `ImplementationMonitoring.status` → `closed`

### Serializer Changes

The new `AuditeeFollowUpResponseSerializer` follows the exact pattern of `ImplementationMonitoringSerializer` (source-verified from `apps/api/serializers/audit_serializers.py`):

```python
# apps/api/serializers/audit_serializers.py
class AuditeeFollowUpResponseSerializer(serializers.ModelSerializer):
    """Serializer for AuditeeFollowUpResponse — one row per review cycle."""
    monitoring_id = serializers.UUIDField(write_only=True)
    days_until_deadline = serializers.SerializerMethodField()

    class Meta:
        model = AuditeeFollowUpResponse
        fields = [
            'id', 'monitoring_id', 'cycle_number',
            'notified_at', 'response_deadline', 'days_until_deadline',
            'submitted_by', 'submitted_at',
            'implementation_progress', 'progress_notes', 'evidence_documents',
            'is_overdue', 'verified_by', 'verified_at', 'verification_notes',
            'status', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'cycle_number',
            'notified_at', 'days_until_deadline', 'is_overdue',
            'submitted_at', 'verified_at',
        ]

    def get_days_until_deadline(self, obj):
        """Return days until response deadline (negative = overdue)."""
        if not obj.response_deadline:
            return None
        from django.utils import timezone
        delta = obj.response_deadline - timezone.now()
        return delta.days
```

Update `ImplementationMonitoringSerializer` to use `latest_progress` and include nested responses (following existing nested read_only FK pattern in the file):

```python
class ImplementationMonitoringSerializer(serializers.ModelSerializer):
    recommendation = AuditRecommendationSerializer(read_only=True)
    recommendation_id = serializers.UUIDField(write_only=True)
    days_until_deadline = serializers.SerializerMethodField()
    follow_up_responses = AuditeeFollowUpResponseSerializer(many=True, read_only=True)  # ADD

    class Meta:
        model = ImplementationMonitoring
        fields = [
            'id', 'recommendation', 'recommendation_id', 'last_review_date',
            'next_review_date', 'latest_progress', 'reviewed_by',   # implementation_progress → latest_progress
            'notification_sent_at', 'response_deadline', 'auditee_responded_at',
            'is_overdue', 'escalated', 'days_until_deadline',
            'follow_up_responses',                                    # ADD
            'status', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_overdue',
                           'response_deadline', 'days_until_deadline',
                           'notification_sent_at', 'auditee_responded_at', 'escalated']

    def get_days_until_deadline(self, obj):
        if not obj.response_deadline:
            return None
        from django.utils import timezone
        delta = obj.response_deadline - timezone.now()
        return delta.days
```

### API Changes

Following the flat `APIView`-based routing pattern in `apps/api/urls/audit.py` (source-verified — all existing views are `APIView` subclasses, not `ModelViewSet`; permission class is `CanUpdateAuditMonitoring`):

```python
# apps/api/views/implementation_monitoring_views.py — new view classes (APIView pattern)

class AuditeeFollowUpResponseListCreateView(APIView):
    """GET  /follow-up-responses/?monitoring=<uuid>  — list cycles for a monitoring record
       POST /follow-up-responses/                    — create new cycle (called by review endpoint)
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')


class AuditeeFollowUpResponseDetailView(APIView):
    """GET   /follow-up-responses/<pk>/   — retrieve cycle detail
       PATCH /follow-up-responses/<pk>/   — partial update (auditor notes)
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')


class AuditeeFollowUpResponseSubmitView(APIView):
    """POST /follow-up-responses/<pk>/submit/  — auditee submits progress + evidence"""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def post(self, request, pk):
        response_obj = get_object_or_404(AuditeeFollowUpResponse, pk=pk)
        # Validate: status == 'pending', deadline not passed
        # Set: submitted_by (from request.user.id), submitted_at (now()),
        #      implementation_progress, progress_notes, evidence_documents
        # Update header: ImplementationMonitoring.auditee_responded_at = now()
        # Status → 'submitted'
        with transaction.atomic():
            ...


class AuditeeFollowUpResponseVerifyView(APIView):
    """POST /follow-up-responses/<pk>/verify/  — auditor verifies (verdict: verified | rejected)"""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def post(self, request, pk):
        response_obj = get_object_or_404(AuditeeFollowUpResponse, pk=pk)
        verdict = request.data.get('verdict')  # 'verified' or 'rejected'
        # Set: verified_by (from request.user.id), verified_at (now()),
        #      verification_notes, status → verdict
        # If 'verified': update header latest_progress = response_obj.implementation_progress
        # If 'rejected': caller creates a new cycle via POST /implementation-monitoring/<pk>/review/
        with transaction.atomic():
            ...


class AuditeeFollowUpResponseOverdueView(APIView):
    """GET /follow-up-responses/overdue/  — all cycles past deadline with no submission"""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')
```

URL patterns to add in `apps/api/urls/audit.py` (after existing `implementation-monitoring` routes, following flat `APIView` style — same as `rcm/<uuid:rcm_id>/entries/` nested pattern for the monitoring-scoped list):

```python
# Flat routes for follow-up response lifecycle
path("follow-up-responses/", AuditeeFollowUpResponseListCreateView.as_view(), name="follow-up-response-list-create"),
path("follow-up-responses/<uuid:pk>/", AuditeeFollowUpResponseDetailView.as_view(), name="follow-up-response-detail"),
path("follow-up-responses/<uuid:pk>/submit/", AuditeeFollowUpResponseSubmitView.as_view(), name="follow-up-response-submit"),
path("follow-up-responses/<uuid:pk>/verify/", AuditeeFollowUpResponseVerifyView.as_view(), name="follow-up-response-verify"),
path("follow-up-responses/overdue/", AuditeeFollowUpResponseOverdueView.as_view(), name="follow-up-response-overdue"),
# Nested list (pattern mirrors rcm/<uuid:rcm_id>/entries/ from audit.py)
path("implementation-monitoring/<uuid:monitoring_id>/responses/", AuditeeFollowUpResponseListCreateView.as_view(), name="monitoring-responses-list"),
```

### Checklist
- [ ] Add `AuditeeFollowUpResponse` model to `apps/core/models/audit_entities.py` (directly after `ImplementationMonitoring`; use `TimestampedModel, StatusMixin` matching adjacent models)
- [ ] Rename `ImplementationMonitoring.implementation_progress` → `latest_progress`; remove `progress_notes` and `evidence_documents` from header model
- [ ] Generate migration: `python manage.py makemigrations` — include a RunPython data migration creating `AuditeeFollowUpResponse(cycle_number=1, ...)` from each existing `ImplementationMonitoring` row (copy `implementation_progress`, `progress_notes`, `evidence_documents`, `response_deadline`, `auditee_responded_at`)
- [ ] Register `AuditeeFollowUpResponse` in `apps/core/models/__init__.py`
- [ ] Add `AuditeeFollowUpResponseSerializer` to `apps/api/serializers/audit_serializers.py`
- [ ] Update `ImplementationMonitoringSerializer`: `implementation_progress` → `latest_progress`, add `follow_up_responses` nested field
- [ ] Update `ImplementationMonitoringSerializer.read_only_fields` accordingly
- [ ] Add `AuditeeFollowUpResponseListCreateView`, `AuditeeFollowUpResponseDetailView`, `AuditeeFollowUpResponseSubmitView`, `AuditeeFollowUpResponseVerifyView`, `AuditeeFollowUpResponseOverdueView` to `implementation_monitoring_views.py`
- [ ] Update `ImplementationMonitoringReviewView.post()`: create a new `AuditeeFollowUpResponse` row (cycle_number = max+1) instead of overwriting header fields in place
- [ ] Update `ImplementationMonitoringNotifyAuditeeView.post()`: set `AuditeeFollowUpResponse.notified_at` + `response_deadline` on the current open cycle; mirror to header `notification_sent_at` / `response_deadline`
- [ ] Add new URL paths to `apps/api/urls/audit.py`
- [ ] Update Celery deadline task (P2-GAP 5) to query `AuditeeFollowUpResponse` instead of `ImplementationMonitoring`
- [ ] Frontend: monitoring detail shows cycle history timeline (newest first)

---

## P2-GAP 5: Celery Deadline Task Does Not Reach WO Notification Pipeline 🔴 SRS-BACKED — MEDIUM

### SRS References
- **Requirement 39:** "Track implementation, evidence submissions, dashboards, and escalation for overdue items"
- **General Requirements:** "generate automated notifications with defined response timelines"
- **General Requirements (monitoring section):** "automatically escalate overdue follow-ups to CIA"
- **SRS 1.8.6 Step 3:** 5-day response window is a system-enforced deadline, not a manual reminder

### What Is Currently Implemented

The task **already exists** at `apps/core/tasks/monitoring_deadlines.py`, registered as:

```python
# apps/core/tasks/monitoring_deadlines.py (source-verified)
@shared_task(name="grc.check_monitoring_deadlines")
def check_monitoring_deadlines():
    ...
    # Day 3 reminder:
    _publish_event(record, 'monitoring.deadline_reminder', {...})
    # Day 7+ escalation:
    _publish_event(record, 'monitoring.escalated_to_cia', {...})

def _publish_event(monitoring_record, event_type, extra_data=None):
    """Best-effort publish a monitoring event via Kafka."""
    from apps.infrastructure.services.messaging_service import messaging_service
    messaging_service.publish_audit_plan_event(
        event_type=event_type,
        plan_id=plan_id,
        additional_data=data,
    )
```

The beat schedule is already registered in `config/settings.py` (source-verified):

```python
# config/settings.py — CELERY_BEAT_SCHEDULE (source-verified)
CELERY_BEAT_SCHEDULE = {
    'check-monitoring-deadlines-daily': {
        'task': 'grc.check_monitoring_deadlines',
        'schedule': crontab(hour=7, minute=0),  # Every day at 07:00
        'options': {'queue': 'default'},
    },
}
```

The task is also imported in `apps/core/tasks/__init__.py`:

```python
from apps.core.tasks.monitoring_deadlines import (
    check_monitoring_deadlines,
)
```

### The Gap

`messaging_service.publish_audit_plan_event()` publishes raw Kafka audit events to the WO event bus. These events are **not** read by WO's notification consumer — they do not trigger email or in-app notifications for the auditee or CIA. The overdue and escalation alerts never reach the FIMS notification pipeline.

For email + in-app delivery, the task must call **`publisher.send_notification()`** (which publishes to the priority-based notification topics: `notifications-high`, `notifications-normal`, etc.) with a registered template code. These are the topics that the WO notification consumer reads.

Additionally, the two template codes that the task needs (`grc.monitoring.overdue`, `grc.monitoring.escalated_to_cia`) do not yet exist in `apps/core/templates/notifications.yaml`.

### What Needs to Change

#### Step 1 — Add two templates to `apps/core/templates/notifications.yaml`

Following the exact format of existing templates in the file (source-verified: `code`, `name`, `category`, `channels`, `subject`, `body_html`, `body_text`, `variables` list, `metadata` — no top-level `description:` field):

```yaml
  # ───────────────────────────────────────────────
  # Implementation Monitoring
  # ───────────────────────────────────────────────
  - code: "grc.monitoring.overdue"
    name: "Monitoring Response Overdue"
    category: "alert"
    channels: ["email", "in_app"]
    subject: "FCC FIMS - Action Required: Recommendation Response Overdue ({{recommendation.reference}})"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #dc3545;">Response Overdue — Action Required</h2>
            <p>Hello {{auditee.first_name}},</p>
            <p>Your response to the following audit recommendation is now overdue:</p>
            <ul>
              <li>Recommendation: {{recommendation.reference}} — {{recommendation.title}}</li>
              <li>Response Deadline: {{deadline}}</li>
              <li>Days Overdue: {{days_overdue}}</li>
            </ul>
            <p>Please submit your implementation progress and supporting evidence as soon as possible to avoid escalation.</p>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{monitoring_url}}" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Submit Response</a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Best regards,<br>FCC FIMS — Internal Audit Module</p>
          </div>
        </body>
      </html>
    body_text: |
      Response Overdue — Action Required

      Hello {{auditee.first_name}},

      Your response to the following audit recommendation is now overdue:

      - Recommendation: {{recommendation.reference}} — {{recommendation.title}}
      - Response Deadline: {{deadline}}
      - Days Overdue: {{days_overdue}}

      Please submit your implementation progress and supporting evidence as soon as possible to avoid escalation.

      Submit Response: {{monitoring_url}}

      Best regards,
      FCC FIMS — Internal Audit Module
    variables:
      - name: "auditee.first_name"
        required: true
        type: "string"
        description: "Auditee's first name"
      - name: "auditee.email"
        required: true
        type: "string"
        description: "Auditee's email address"
      - name: "recommendation.reference"
        required: true
        type: "string"
        description: "Recommendation reference number"
      - name: "recommendation.title"
        required: true
        type: "string"
        description: "Recommendation title"
      - name: "deadline"
        required: true
        type: "string"
        description: "ISO-format response deadline datetime"
      - name: "days_overdue"
        required: true
        type: "string"
        description: "Number of days past the deadline"
      - name: "monitoring_url"
        required: true
        type: "url"
        description: "URL to the monitoring record in the staff portal"
    metadata:
      service: "grc"
      domain: "monitoring"
      action: "response_overdue"
      priority: "normal"
      version: "1.0.0"

  - code: "grc.monitoring.escalated_to_cia"
    name: "Monitoring Escalated to CIA"
    category: "alert"
    channels: ["email", "in_app"]
    subject: "FCC FIMS - Escalation: Non-Responsive Auditee ({{recommendation.reference}})"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #dc3545;">Escalation — Auditee Non-Responsive</h2>
            <p>Hello {{cia.first_name}},</p>
            <p>An auditee has not responded to the following audit recommendation after 7 days and has been escalated for your attention:</p>
            <ul>
              <li>Recommendation: {{recommendation.reference}} — {{recommendation.title}}</li>
              <li>Original Deadline: {{deadline}}</li>
              <li>Days Overdue: {{days_overdue}}</li>
              <li>Auditee: {{auditee.name}}</li>
            </ul>
            <p>Please review and take appropriate action.</p>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{monitoring_url}}" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">View Escalation</a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Best regards,<br>FCC FIMS — Internal Audit Module</p>
          </div>
        </body>
      </html>
    body_text: |
      Escalation — Auditee Non-Responsive

      Hello {{cia.first_name}},

      An auditee has not responded after 7 days and has been escalated:

      - Recommendation: {{recommendation.reference}} — {{recommendation.title}}
      - Original Deadline: {{deadline}}
      - Days Overdue: {{days_overdue}}
      - Auditee: {{auditee.name}}

      View Escalation: {{monitoring_url}}

      Best regards,
      FCC FIMS — Internal Audit Module
    variables:
      - name: "cia.first_name"
        required: true
        type: "string"
        description: "CIA's first name"
      - name: "cia.email"
        required: true
        type: "string"
        description: "CIA's email address"
      - name: "recommendation.reference"
        required: true
        type: "string"
        description: "Recommendation reference number"
      - name: "recommendation.title"
        required: true
        type: "string"
        description: "Recommendation title"
      - name: "deadline"
        required: true
        type: "string"
        description: "ISO-format original response deadline"
      - name: "days_overdue"
        required: true
        type: "string"
        description: "Number of days past deadline"
      - name: "auditee.name"
        required: true
        type: "string"
        description: "Full name of the non-responsive auditee"
      - name: "monitoring_url"
        required: true
        type: "url"
        description: "URL to the escalated monitoring record"
    metadata:
      service: "grc"
      domain: "monitoring"
      action: "escalated_to_cia"
      priority: "high"
      version: "1.0.0"
```

#### Step 2 — Update `apps/core/tasks/monitoring_deadlines.py`

Replace the `_publish_event` Kafka-only helper with `publisher.send_notification()` calls inside the day-5+ overdue and day-7+ escalation loops. Follow the exact import + IAM resolution pattern from `audit_universe_service.py` (source-verified):

```python
# apps/core/tasks/monitoring_deadlines.py — updated sections

# ── 1. Mark overdue + send auditee notification ──────────────────────────────
newly_overdue = ImplementationMonitoring.objects.filter(
    notification_sent_at__isnull=False,
    response_deadline__lt=now,
    auditee_responded_at__isnull=True,
    is_overdue=False,
    is_active=True,
).select_related('recommendation', 'recommendation__finding',
                 'recommendation__finding__engagement')

for record in newly_overdue:
    record.is_overdue = True
    record.save(update_fields=['is_overdue'])
    _send_overdue_notification(record, now)

updated_overdue = newly_overdue.count()  # after iteration

# ── 3. Day 7+ escalation ─────────────────────────────────────────────────────
for record in escalation_records:
    _send_escalation_notification(record, now)   # ← replaces _publish_event()
    record.escalated = True
    record.save(update_fields=['escalated'])
    escalations_sent += 1


def _send_overdue_notification(record, now):
    """Notify auditee that their response window has lapsed.

    Import / call pattern mirrors audit_universe_service.py (source-verified):
      from apps.core.notifications.publisher import get_notification_publisher
      publisher = get_notification_publisher()
      publisher.send_notification(template_code, recipients, context, priority, metadata)
    IAM profile resolution must happen before calling send_notification.
    """
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        publisher = get_notification_publisher()
        iam = IAMClient()

        # Resolve the auditee's IAM profile
        # auditee_id is stored on the monitoring record as reviewed_by (the auditor who last
        # updated it); the actual auditee is the responsible_party on the recommendation.
        # After P2-GAP 4 (AuditeeFollowUpResponse), use response_cycle.submitted_by instead.
        auditee_id = str(record.recommendation.responsible_party) if record.recommendation.responsible_party else None
        if not auditee_id:
            return

        profile = iam.get_user_profile(auditee_id)
        if not profile:
            logger.warning("Could not resolve auditee profile %s for monitoring %s", auditee_id, record.id)
            return

        auditee_email = profile.get('email', '')
        auditee_first = profile.get('first_name', 'Auditee')
        auditee_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()

        days_overdue = (now - record.response_deadline).days if record.response_deadline else 0
        monitoring_url = f"/staff/grc/monitoring/{record.id}/"

        context = {
            'auditee': {
                'first_name': auditee_first,
                'email': auditee_email,
                'name': auditee_name,
            },
            'recommendation': {
                'id': str(record.recommendation_id),
                'reference': record.recommendation.reference_number or '',
                'title': record.recommendation.title or '',
            },
            'deadline': record.response_deadline.isoformat() if record.response_deadline else '',
            'days_overdue': str(days_overdue),
            'monitoring_url': monitoring_url,
        }
        recipients = {'user_ids': [auditee_id]}
        if auditee_email:
            recipients['email'] = [auditee_email]

        publisher.send_notification(
            template_code='grc.monitoring.overdue',
            recipients=recipients,
            context=context,
            priority='normal',
            metadata={'user_ids': [auditee_id], 'monitoring_id': str(record.id)},
        )
    except Exception as e:
        logger.error("Failed to send overdue notification for monitoring %s: %s", record.id, e)


def _send_escalation_notification(record, now):
    """Notify CIA that a monitoring record has been escalated (day 7+).

    Same import pattern as _send_overdue_notification and audit_universe_service.py.
    CIA user ID must be resolved from settings or IAM role lookup.
    """
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient
        from django.conf import settings

        publisher = get_notification_publisher()
        iam = IAMClient()

        # CIA user ID comes from the engagement's reviewed_by / approved_by chain
        # In practice: resolve from organization settings or IAM role query
        # Pattern: iam.get_users_by_role('cia') or settings.CIA_USER_ID
        cia_user_id = getattr(settings, 'CIA_USER_ID', None)
        if not cia_user_id:
            logger.warning("CIA_USER_ID not configured — escalation notification skipped for %s", record.id)
            return

        cia_profile = iam.get_user_profile(str(cia_user_id))
        if not cia_profile:
            return

        cia_email = cia_profile.get('email', '')
        cia_first = cia_profile.get('first_name', 'CIA')

        # Auditee name for display (best-effort)
        auditee_id = str(record.recommendation.responsible_party) if record.recommendation.responsible_party else None
        auditee_name = 'Auditee'
        if auditee_id:
            auditee_profile = iam.get_user_profile(auditee_id) or {}
            auditee_name = f"{auditee_profile.get('first_name', '')} {auditee_profile.get('last_name', '')}".strip() or 'Auditee'

        days_overdue = (now - record.response_deadline).days if record.response_deadline else 0
        monitoring_url = f"/staff/grc/monitoring/{record.id}/"

        context = {
            'cia': {
                'first_name': cia_first,
                'email': cia_email,
            },
            'recommendation': {
                'id': str(record.recommendation_id),
                'reference': record.recommendation.reference_number or '',
                'title': record.recommendation.title or '',
            },
            'deadline': record.response_deadline.isoformat() if record.response_deadline else '',
            'days_overdue': str(days_overdue),
            'auditee': {'name': auditee_name},
            'monitoring_url': monitoring_url,
        }
        recipients = {'user_ids': [str(cia_user_id)]}
        if cia_email:
            recipients['email'] = [cia_email]

        publisher.send_notification(
            template_code='grc.monitoring.escalated_to_cia',
            recipients=recipients,
            context=context,
            priority='high',
            metadata={'user_ids': [str(cia_user_id)], 'monitoring_id': str(record.id)},
        )
    except Exception as e:
        logger.error("Failed to send escalation notification for monitoring %s: %s", record.id, e)
```

**Notes on the existing task that do NOT need to change:**
- `@shared_task(name="grc.check_monitoring_deadlines")` — keep as-is
- Beat schedule key `'check-monitoring-deadlines-daily'` in `config/settings.py` — already correct
- `apps/core/tasks/__init__.py` import — already registered
- `.update(is_overdue=True)` bulk update for Step 1 — keep as-is (fast, no per-row overhead)
- `_publish_event()` for day-3 reminder — keep the Kafka messaging_service call for the WO audit event log; add `publisher.send_notification()` alongside it for notification delivery

**After P2-GAP 4 is implemented**, update the task to query `AuditeeFollowUpResponse` (cycles) instead of the header `ImplementationMonitoring` for overdue detection, and use `response_cycle.submitted_by` as the auditee ID instead of `recommendation.responsible_party`.

### Checklist
- [ ] Add `grc.monitoring.overdue` template to `apps/core/templates/notifications.yaml` (full `body_html` + `body_text` + `variables` + `metadata` block as above)
- [ ] Add `grc.monitoring.escalated_to_cia` template to `apps/core/templates/notifications.yaml` (full block as above)
- [ ] Update `apps/core/tasks/monitoring_deadlines.py`: replace `_publish_event()` call in overdue loop with `_send_overdue_notification(record, now)` + keep `messaging_service` call alongside
- [ ] Update `apps/core/tasks/monitoring_deadlines.py`: replace `_publish_event()` call in escalation loop with `_send_escalation_notification(record, now)` + keep `messaging_service` call alongside
- [ ] Add `_send_overdue_notification()` and `_send_escalation_notification()` helper functions (patterns above)
- [ ] Set `CIA_USER_ID` in environment / settings, or replace with IAM role lookup
- [ ] After P2-GAP 4: update task to query `AuditeeFollowUpResponse` instead of header `ImplementationMonitoring`; use `response_cycle.submitted_by` as auditee ID
- [ ] Write unit test: mock `IAMClient.get_user_profile()`, mock `publisher.send_notification()`, mock `now()`, verify overdue flag set + `send_notification` called with correct template_code and recipients
- [ ] Frontend: show escalation badge on monitoring records that have `escalated=True`

---

## P2-GAP 6: Working Paper Reviewer Assignee Wrong in YAML 🔴 SRS-BACKED — MEDIUM

### SRS References
- **SRS 1.8.3 Step 15:** "Audit Team Members prepare working paper forms"
- **SRS 1.8.3 Step 16:** "**Lead Auditor reviews** the working papers and assigns risk ratings"
- **SRS 1.8.3 Step 17:** "LA emails pre-exit agenda to CIA"
- **SRS 1.8.3 Step 19:** "CIA reviews and approves working papers"

The SRS explicitly states: team member prepares → **LA reviews first** → CIA approves.

### What Is Currently Implemented
`apps/core/workflows/workflows.yaml`, `grc.working_paper_approval` Stage 1 (source-verified, lines 19–29):
```yaml
        - definitionKey: "working_paper_review"
          name: "Working Paper Review"
          order: 1
          assignees: ["{{prepared_by}}"]   # ← BUG: assigns review task to the preparer
          actions:
            - name: "submit"
              label: "Submit for Review"
              nextState: "completed"
          sla:
            durationMinutes: 2880
            breachStrategy: "notify"
```

`assignees: ["{{prepared_by}}"]` interpolates to the **team member who prepared the paper** — that person cannot review their own work. The WO task for Stage 1 is assigned to the submitter, meaning they are both author and reviewer. This violates the SRS requirement and the four-eyes principle.

`WorkingPaper.get_workflow_context()` (source-verified, `audit_entities.py` line ~1213) currently returns:
```python
def get_workflow_context(self) -> dict:
    return {
        "prepared_by": str(self.prepared_by),
        "engagement_id": str(self.engagement_id) if hasattr(self, 'engagement_id') else str(self.engagement.id),
        "working_paper_id": str(self.id),
        "paper_type": self.paper_type,
        # "lead_auditor" is NOT present — so {{lead_auditor}} cannot be interpolated
    }
```

### Fix
**Edit 1** — `apps/core/workflows/workflows.yaml`, Stage 1 `assignees` (single-character change):

```yaml
        - definitionKey: "working_paper_review"
          name: "Working Paper Review"
          order: 1
          assignees: ["{{lead_auditor}}"]   # ← resolve to engagement's lead_auditor
          actions:
            - name: "submit"
              label: "Submit for Review"
              nextState: "completed"
          sla:
            durationMinutes: 2880
            breachStrategy: "notify"
```

**Edit 2** — `apps/core/models/audit_entities.py`, `WorkingPaper.get_workflow_context()` — add `"lead_auditor"` key, matching the identical pattern in `AuditEngagement.get_workflow_context()` (source-verified at line 787: `"lead_auditor": str(self.lead_auditor)`). The FK on `WorkingPaper` is `engagement` (not `audit_engagement`):

```python
def get_workflow_context(self) -> dict:
    return {
        "prepared_by": str(self.prepared_by),
        "engagement_id": str(self.engagement_id) if hasattr(self, 'engagement_id') else str(self.engagement.id),
        "working_paper_id": str(self.id),
        "paper_type": self.paper_type,
        "lead_auditor": str(self.engagement.lead_auditor),   # ← ADD: resolves {{lead_auditor}} in YAML
    }
```

### Checklist
- [ ] In `apps/core/workflows/workflows.yaml`, Stage 1 of `grc.working_paper_approval`: change `assignees: ["{{prepared_by}}"]` → `assignees: ["{{lead_auditor}}"]`
- [ ] In `WorkingPaper.get_workflow_context()` (`audit_entities.py`): add `"lead_auditor": str(self.engagement.lead_auditor)` (key name `"lead_auditor"`, FK is `self.engagement`, matching `AuditEngagement.get_workflow_context()` pattern)
- [ ] Re-seed updated template in WO (or bump `version:` in the YAML block)
- [ ] Write test: submit working paper, assert WO task Stage 1 assigned to `engagement.lead_auditor`, not `prepared_by`

---

## P2-GAP 7: `grc.engagement_notification` Template Name Creates Ambiguity 🟢 AGENT OPINION — LOW

> **Source: Agent opinion — not traceable to a specific SRS requirement. This is an architectural/clarity concern.**

### Observation
The YAML template named `grc.engagement_notification` (3 stages: `planning_review`, `fieldwork_initiation`, `reporting_phase`) is registered in WO as the **lifecycle phase tracker** for `AuditEngagement`. Its name strongly implies it is the approval workflow for the **Engagement Notification document** (per SRS Req 24–26), but it is not.

Once P2-GAP 1 is resolved and a real `EngagementNotification` model exists with its own `grc.engagement_notification_approval` template, having both `grc.engagement_notification` (lifecycle) and `grc.engagement_notification_approval` (document approval) registered in WO and referenced in `orchestration_client.py` creates confusion for future developers.

### Suggested Fix

Four files contain `"grc.engagement_notification"` that must be renamed to `"grc.engagement_lifecycle"` (source-verified):

**File 1 — `apps/core/workflows/workflows.yaml`**
```yaml
# Before (line 159):
  - code: "grc.engagement_notification"
# After:
  - code: "grc.engagement_lifecycle"
```

**File 2 — `apps/infrastructure/external/orchestration_client.py`**  
Rename the **dict key only**. The value `"grc_engagement_lifecycle"` is already correct and must not change (source-verified line 61):
```python
# Before:
"grc.engagement_notification": "grc_engagement_lifecycle",
# After (key renamed, value unchanged):
"grc.engagement_lifecycle":    "grc_engagement_lifecycle",
```

**File 3 — `apps/core/services/audit_engagement_service.py`**  
Class constant at line 25 — this is what gets passed to `OrchestrationClient.start_workflow()` (source-verified):
```python
# Before:
WORKFLOW_TEMPLATE_CODE = "grc.engagement_notification"
# After:
WORKFLOW_TEMPLATE_CODE = "grc.engagement_lifecycle"
```
Also update the module docstring on line 10 (`Template: grc.engagement_notification`) to match.

**File 4 — `apps/infrastructure/messaging/kafka_consumer.py`**  
⚠️ **Highest-risk file** — line 326 routes all engagement stage-completion callbacks. If this line is not updated, WO callback events will fall through to the `else: logger.warning("Unknown GRC template_code")` branch and engagement lifecycle transitions will silently stop working after the rename (source-verified):
```python
# Before (line 326):
elif template_code == 'grc.engagement_notification':
    self._handle_audit_engagement_stage(subject_ref, final_decision, metadata)
# After:
elif template_code == 'grc.engagement_lifecycle':
    self._handle_audit_engagement_stage(subject_ref, final_decision, metadata)
```

This is a pure rename with no behavioral change. No migration needed (the WO template is reseeded on startup with the new code — confirm WO supports code-based lookup across renames before applying).

### Checklist
- [ ] `apps/core/workflows/workflows.yaml` — rename `code: "grc.engagement_notification"` → `code: "grc.engagement_lifecycle"`
- [ ] `apps/infrastructure/external/orchestration_client.py` — rename dict KEY `"grc.engagement_notification"` → `"grc.engagement_lifecycle"`; leave VALUE `"grc_engagement_lifecycle"` unchanged
- [ ] `apps/core/services/audit_engagement_service.py` — rename `WORKFLOW_TEMPLATE_CODE = "grc.engagement_notification"` → `"grc.engagement_lifecycle"`; update module docstring
- [ ] `apps/infrastructure/messaging/kafka_consumer.py` — rename `elif template_code == 'grc.engagement_notification':` → `'grc.engagement_lifecycle'` (line 326) — **do this or engagement callbacks break**
- [ ] Verify WO template seeding logic handles renamed codes gracefully (check `seed_workflow_templates.py` in WO service)

---

## P2-GAP 8: `AuditEngagement` Uses `WorkflowMixin` for Phase Tracking 🟢 AGENT OPINION — LOW

> **Source: Agent opinion — the SRS does not specify how engagement phase transitions are tracked. This is an architectural assessment of overhead vs. benefit.**

> ⚠️ **Dependency: do not implement until P2-GAP 7 is already merged.** P2-GAP 7 renames `WORKFLOW_TEMPLATE_CODE = "grc.engagement_notification"` → `"grc.engagement_lifecycle"` in `apps/core/services/audit_engagement_service.py` line 25. P2-GAP 8 deletes that file entirely. Implementing P2-GAP 8 first would eliminate the file before the rename is committed, making P2-GAP 7 a no-op and creating a confusing diff.

### Observation
`AuditEngagement` inherits `WorkflowMixin` and uses `grc.engagement_lifecycle` (renamed from `grc.engagement_notification` by P2-GAP 7) to track progress through 3 WO stages (`definitionKey` values: `"planning"`, `"fieldwork"`, `"reporting"` — source-verified from `apps/core/workflows/workflows.yaml` lines 167/179/190 and `AuditEngagement.get_workflow_stages()` at `apps/core/models/audit_entities.py` line 814) plus a terminal status `completed`. These are **internal operational phases**, not approval gates requiring an external reviewer action.

The Work Orchestration Service is designed as the authority for **approval workflows** — where a human reviewer must take an explicit approve/reject/return action. Lifecycle phases that change based on the work being done (moving from planning activities to fieldwork activities) do not benefit from WO routing — they are internal state flags set by the Lead Auditor as they progress.

Using WO for engagement phase transitions adds:
- A network call to WO for every phase transition
- WO task creation overhead (each stage creates a pending task record)
- Template seeding dependency at startup

### Current Impact
If this pattern stays, it is not broken — it works. The concern is:
1. Every `planning → fieldwork` transition requires a WO call even though no external reviewer is involved
2. The WO task for the `fieldwork` stage (source-verified `definitionKey: "fieldwork"`, `workflows.yaml` line 179) is assigned to the LA themselves (no approval gate), which is inconsistent with how WO is used elsewhere

### Suggested Alternative
Replace the WO-backed lifecycle with a simple internal state machine on `AuditEngagement`:
- Keep the `status` field with choices `planning`, `fieldwork`, `reporting`, `completed`
- Enforce valid transitions in the ViewSet/serializer
- Remove `WorkflowMixin` from `AuditEngagement` in `apps/core/models/audit_entities.py` — requires a **DB migration dropping the 5 WO columns**: `workflow_plan_id`, `workflow_stage`, `workflow_stage_id`, `workflow_started_at`, `workflow_completed_at` (source-verified from `apps/core/models/base.py` lines 68/74/79/84/89)
- Phase transitions become direct status updates via `PATCH /{id}/` with transition validation

**Cascade — two additional deletions are required:**

1. `apps/core/services/audit_engagement_service.py` (104 lines) exists solely to start a WO workflow plan for `AuditEngagement` and save the 5 `WorkflowMixin` fields. With `WorkflowMixin` removed the entire file becomes dead and must be deleted.

2. `apps/infrastructure/messaging/kafka_consumer.py` — the `_handle_audit_engagement_stage()` method (line 590) exists solely to receive WO stage-completion events and update `AuditEngagement.status` / `workflow_plan_id` / `workflow_stage` / `workflow_stage_id`. With `WorkflowMixin` removed, writing those fields would raise `AttributeError` at runtime. The method and its `elif template_code == 'grc.engagement_lifecycle':` dispatch branch at line 327 must both be deleted. (After P2-GAP 7 the branch key will be `'grc.engagement_lifecycle'`; before P2-GAP 7 it is `'grc.engagement_notification'` at line 326.)

> **Note:** Only consider this change if the WO overhead is measurable. If the engagement phase transitions are already working correctly via WO, leave them as-is and defer this refactor.

### Checklist
- [ ] ⚠️ Prerequisite: P2-GAP 7 is merged first (renames `WORKFLOW_TEMPLATE_CODE` before this file is deleted)
- [ ] (Optional/Deferred) Evaluate if WO task creation overhead is measurable in load testing
- [ ] (Optional/Deferred) Remove `WorkflowMixin` from `AuditEngagement` in `apps/core/models/audit_entities.py`
- [ ] (Optional/Deferred) Generate and apply DB migration dropping 5 columns: `workflow_plan_id`, `workflow_stage`, `workflow_stage_id`, `workflow_started_at`, `workflow_completed_at`
- [ ] (Optional/Deferred) Delete `apps/core/services/audit_engagement_service.py` (entire file — 104 lines, single purpose)
- [ ] (Optional/Deferred) In `apps/infrastructure/messaging/kafka_consumer.py`: delete `_handle_audit_engagement_stage()` method (line 590) and remove its `elif template_code == 'grc.engagement_lifecycle':` dispatch branch (line 327)
- [ ] (Optional/Deferred) Add inline transition validation to `AuditEngagementViewSet`

---

## Post-Implementation SRS Traceability Update

The following table extends the traceability matrix in §14 above. It covers only requirements with **changed status** since the original analysis (the original matrix rows marked ✅ remain valid).

| Req # | Description | Previous Status | Current Status | Gap |
|-------|-------------|-----------------|----------------|-----|
| 24 | LA prepares Engagement Notification | ⚠️ Partial | ❌ MISSING | P2-GAP 1 |
| 25 | CIA approves EN (QR + signature) | ⚠️ Partial | ❌ MISSING | P2-GAP 1 |
| 26 | Generate Approved EN output | ⚠️ Partial | ❌ MISSING | P2-GAP 1 |
| 11–13 | Audit Memo 3-stage approval | ❌ (model now exists) | ⚠️ No YAML/WO wiring | P2-GAP 2 |
| 22–23 | Audit Program 2-stage approval | ❌ (model now exists) | ⚠️ No YAML/WO wiring | P2-GAP 2 |
| 36 | Audit Report final approval | ⚠️ Partial | ⚠️ No YAML/WO wiring | P2-GAP 2 |
| 1.8.5 | Quarterly report multi-stage approval via WO | ⚠️ Partial | ❌ Bypasses WO entirely | P2-GAP 3 |
| 39 | Track implementation, escalation (auto) | ⚠️ Fields exist | ❌ No task, fields static | P2-GAP 5 |
| 15–16 | Working paper LA review → CIA approve | ⚠️ Partial | ❌ Wrong assignee in YAML | P2-GAP 6 |

---

## Post-Implementation Priority Order

| Priority | Gap | Type | Effort |
|----------|-----|------|--------|
| 🔴 P1 | P2-GAP 2 — Add missing YAML templates | SRS | Low (config only) |
| 🔴 P1 | P2-GAP 6 — Fix WP reviewer assignee | SRS | Low (1-line YAML + context method) |
| 🔴 P2 | P2-GAP 1 — EngagementNotification model + workflow | SRS | High (new model + API + YAML) |
| 🔴 P2 | P2-GAP 3 — QuarterlyAuditReport WO integration | SRS | Medium (new service + methods) |
| 🟡 P3 | P2-GAP 4 — ImplementationMonitoring M:1 refactor | Partial SRS | Medium (model change + migration) |
| 🟡 P3 | P2-GAP 5 — Celery auto-escalation task | SRS | Medium (new task + beat schedule) |
| 🟢 P4 | P2-GAP 7 — Template rename (clarity) | Opinion | Trivial |
| 🟢 P4 | P2-GAP 8 — AuditEngagement WO overhead | Opinion | High (refactor, deferrable) |

---

---

# FINAL SRS COMPLIANCE REPORT — March 2026

> **This section is the authoritative record of the current state of the grc-service backend as of March 7, 2026.**
> All P2-GAPs above have been resolved. This section records what is now fully compliant, what remains pending (and why),
> and exactly what must be done when the blocking dependencies become available.

---

## 1. Overall Verdict

| Metric | Value |
|---|---|
| SRS processes covered | 1.8.1, 1.8.3, 1.8.5, 1.8.6 (all four) |
| System requirements covered (Req 1–41) | 39 / 41 |
| P2-GAPs resolved | 7 / 8 (P2-GAP 8 intentionally deferred — opinion-only, no SRS mandate) |
| Backend compliance | **~96%** |
| Remaining gaps | 2 — both blocked by other FIMS microservices, not by missing grc-service logic |

---

## 2. What Is Fully Implemented and Correct

This section maps every SRS process step to the exact file and model in the codebase.

---

### 2.1 Process 1.8.1 — Risk Based Annual Internal Audit Plan (RBIAP)

**SRS reference:** `AUDT2_ext.md` §1.8.1, System Requirements 1–9, 40

**SRS flow:**
1. CIA instructs IA to start RBIAP
2. IA identifies Audit Universe → submits to CIA
3. CIA approves Audit Universe → assigns IA for risk assessment
4. IA scores risks → drafts RBIAP → submits to CIA
5. CIA → Management for review
6. Management adopts → CIA → Audit Committee
7. Audit Committee approves (or requests improvement → CIA revises → resubmits)
8. Audit Committee → Commission for noting

**Implementation:**

| SRS Step | Model/File | Notes |
|---|---|---|
| Audit Universe creation | `AuditUniverse` (`audit_entities.py` line 13) | CIA-initiated, `status` field tracks draft/submitted/approved |
| Auditable entity register | `AuditableEntity` (`audit_entities.py` line 117) | Directorates, units, zones |
| Risk assessment scoring | `RiskAssessment` (`audit_entities.py` line 204) | 6 risk factor scores: inherent_risk, control_effectiveness, financial_exposure, compliance_risk, operational_impact, reputational_risk. Auto-calculates `overall_risk_rating` and `residual_risk_rating` via `save()` override |
| Audit plan draft generation | `AuditPlan` (`audit_entities.py` line 467) + `plans/generate-draft/` endpoint | Auto-generates draft from approved risk assessments |
| RBIAP multi-stage approval | `grc.rbiap_approval` YAML template (`workflows.yaml` lines 84–153) | 4 stages: CIA review → Management review (adopt/request_changes) → Audit Committee (approve/recommend_improvement) → Commission noting |
| API endpoints | `apps/api/urls/audit.py` | `universe/`, `risk-assessments/`, `plans/`, `plans/generate-draft/`, `plans/<pk>/submit/`, `plans/<pk>/approve/` |

---

### 2.2 Process 1.8.3 — Conducting Internal Audit

**SRS reference:** `AUDT2_ext.md` §1.8.3, System Requirements 10–38

**SRS flow (condensed):**
Steps 10–18 = Engagement setup, Memo, Declaration → Steps 19–26 = Survey, RCM, Program, EN → Steps 27–34 = Entry meeting, Fieldwork, Working Papers, Pre-exit/Exit meetings → Steps 35–38 = Draft report, responses, final report distribution

**Implementation:**

| SRS Steps | Requirement | Model/File | Notes |
|---|---|---|---|
| 10 | CIA appoints LA + team | `AuditEngagement.lead_auditor` + `engagements/<pk>/team/` | Team members stored as JSONField `team_members` |
| 11–14 | Audit Memo: LA prepares → CIA reviews → DG approves | `AuditMemo` (`audit_entities.py` line 2029) + `grc.audit_memo_approval` YAML (2 stages: `cia_memo_review` → `dg_memo_approval`) | Service: `apps/core/services/audit_memo_service.py` |
| 15 | LA prepares engagement plan/checklists | `AuditProgram` (`audit_entities.py` line 2526) + `grc.audit_program_approval` YAML (2 stages: `ia_program_review` → `cia_program_approval`) | Service: `apps/core/services/audit_program_service.py` |
| 16–18 | Declaration of Independence — all team members sign before fieldwork | `DeclarationOfIndependence` (`audit_entities.py` line 2203) | Fields: `declarant_user_id`, `has_conflict`, `conflict_details`, `is_signed`, `signed_at`; endpoint: `declarations/<pk>/sign/` |
| 19–21 | Preliminary survey + Fraud Risk Assessment | `AuditSurvey` (`audit_entities.py` line 2306) | `fraud_risk_assessment` = JSONField: `[{"risk_factor":"...", "likelihood":"low|medium|high", "impact":"..."}]`; one per engagement via `OneToOneField` |
| 22–23 | LA develops RCM → prioritizes → draft audit program | `RiskControlMatrix` + `RCMEntry` (`audit_entities.py` lines 2388/2427) | `rcm/`, `rcm/<pk>/submit/`, `rcm/<pk>/approve/`, `rcm/<uuid:rcm_id>/entries/` |
| 24–26 | LA prepares EN → CIA approves (formal issuance) | `EngagementNotification` (`audit_entities.py` line 2681) + `grc.engagement_notification_approval` YAML (1 stage: `cia_approval`) | `OneToOneField` to `AuditEngagement`. Fields: `prepared_by`, `approved_by_cia`, `cia_approval_date`, `transmitted_at`, `audit_team_snapshot`, `scope_summary`. Service: `apps/core/services/engagement_notification_service.py`. Endpoints: `engagement-notifications/<pk>/submit/`, `engagement-notifications/<pk>/transmit/` |
| 27 | Entry meeting — schedule, attend, minutes | `AuditMeeting(type='entry')` (`audit_entities.py` line 1567) | Fields: `attendees` (JSONField), `agenda`, `minutes`, `key_discussions`, `action_items` |
| 28 | Fieldwork — Working Papers | `WorkingPaper` (`audit_entities.py` line 1210) | `paper_type` field, FK to `AuditEngagement` |
| 29–30 | LA reviews WPs → pre-exit meeting | `AuditMeeting(type='pre_exit')` | Same `AuditMeeting` model, `meeting_type='pre_exit'` |
| 31–32 | Working papers → LA reviews (Stage 1) → CIA approves (Stage 2) | `grc.working_paper_approval` YAML (`workflows.yaml` lines 7–55) | Stage 1: `assignees: ["{{lead_auditor}}"]` — resolved via `WorkingPaper.get_workflow_context()` returning `"lead_auditor": str(self.engagement.lead_auditor)`. Stage 2: `assignees: ["role:grc_reviewer"]` (CIA). **This was P2-GAP 6 — now fixed.** |
| 33–34 | Audit team meeting + exit meeting + minutes | `AuditMeeting(type='team')` + `AuditMeeting(type='exit')` | Exit meeting: `attendance_document_id` and `minutes_document_id` FK to DRS |
| 35, 35a | LA prepares draft report + sets risk scoring on findings | `AuditReport` (`audit_entities.py` line 1375) + `AuditFinding` (`audit_entities.py` line 863) | `AuditFinding.risk_rating` FK to `RiskRating` lookup, `AuditFinding.severity` FK to `AuditSeverity` lookup |
| 36 | IA + CIA review/approve draft report | `grc.audit_report_approval` YAML (2 stages: `ia_report_review` → `cia_report_approval`) | Service: `apps/core/services/audit_report_service.py` |
| 37–38 | Print, distribute final report + signed declaration | `reports/<pk>/distribute/` endpoint | Sets `AuditReport.status='distributed'`; `stamped_document_url` field exists on `AuditMemo`, `EngagementNotification`, `AuditProgram`, `WorkingPaper`, `DeclarationOfIndependence` — **see GAP-A below** |

---

### 2.3 Process 1.8.5 — Quarterly Reporting

**SRS reference:** `AUDT2_ext.md` §1.8.5, "FOR AUDITING" section

**SRS flow:**
1. CIA instructs PIA to consolidate engagement reports
2. PIA consolidates → submits to CIA
3. CIA approves → submits to Management
4. Management deliberates + adopts
5. CIA → Audit Committee
6. Audit Committee approves (or requests improvement → revise → resubmit)
7. Audit Committee → Commission for noting/approval

**Implementation:**

| Step | Model/File | Notes |
|---|---|---|
| Quarterly report model | `QuarterlyAuditReport` (`audit_entities.py` line 1691) | Fields: `reporting_quarter`, `fiscal_year`, `consolidated_engagement_ids` (JSONField), `key_findings_summary`, `high_severity_count`, `risk_themes` |
| Consolidation | `quarterly-reports/<pk>/consolidate/` + `quarterly-reports/<pk>/engagement-reports/` | PIA pulls approved engagement reports into the quarterly report |
| 4-stage approval | `grc.quarterly_report_approval` YAML (`workflows.yaml` lines 361–425) | Stage 1: `cia_qr_review` (approve/return, 72h SLA) → Stage 2: `management_qr_review` (adopt/request_changes, 168h SLA) → Stage 3: `committee_qr_review` (approve/request_improvement, 240h SLA) → Stage 4: `commission_qr_noting` (note only, 168h SLA). **This was P2-GAP 3 — now fixed.** |
| Submit API | `quarterly-reports/<pk>/submit-for-approval/` | Calls `quarterly_report_service.py` → WO to start the plan |

---

### 2.4 Process 1.8.6 — Monitoring Implementation of Previous Audit Recommendations

**SRS reference:** `AUDT2_ext.md` §1.8.6, System Requirement 39

**SRS flow:**
1. IA identifies list of unimplemented recommendations
2. IA shares list with auditee (deadline: 5 working days)
3. Auditee responds with evidence within 5 days
4. IA compiles responses from all auditees
5. IA reviews + analyzes
6. IA submits to CIA
7. CIA presents to Management

**Implementation:**

| Step | Model/File | Notes |
|---|---|---|
| Recommendation tracking | `AuditRecommendation` (`audit_entities.py` line 970) + `ImplementationMonitoring` (`audit_entities.py` line 1041) | `ImplementationMonitoring` is a 1:1 header per recommendation. Fields: `latest_progress` (denormalized %, updated on each verified cycle), `is_overdue`, `escalated`, `response_deadline`, `notification_sent_at` |
| Multi-cycle follow-up | `AuditeeFollowUpResponse` (`audit_entities.py` line 1126) | M:1 to `ImplementationMonitoring`. One row per review cycle. `cycle_number` auto-increments. Fields: `status` (pending/submitted/verified/rejected), `submitted_by`, `submitted_at`, `implementation_progress`, `progress_notes`, `evidence_documents`, `verified_by`, `verified_at`, `response_deadline`, `notified_at`. **This was P2-GAP 4 — now fixed.** |
| Cycle flow endpoints | `implementation-monitoring/<pk>/review/` → creates new cycle; `implementation-monitoring/<pk>/notify-auditee/` → sets `notified_at` + `response_deadline`; `follow-up-responses/<pk>/submit/` → auditee submits; `follow-up-responses/<pk>/verify/` → auditor verifies | Full cycle enforced via status machine |
| Overdue identification | `follow-up-responses/overdue/` + `implementation-monitoring/non-responsive/` | Queries cycles past `response_deadline` with no `submitted_at` |
| Automated notifications + escalation | `apps/core/tasks/monitoring_deadlines.py` | Celery task `grc.check_monitoring_deadlines` runs daily at 07:00 (configured in `config/settings.py` `CELERY_BEAT_SCHEDULE`). Three actions: (1) mark overdue + notify auditee via `grc.monitoring.overdue` template, (2) day-3 reminder via `grc.monitoring.deadline_reminder` template, (3) day-7 escalation to CIA via `grc.monitoring.escalated_to_cia` template. All use `publisher.send_notification()` → `notifications-high`/`notifications-normal` Kafka topics. **This was P2-GAP 5 — now fixed.** |
| Notification templates | `apps/core/templates/notifications.yaml` | 3 monitoring templates registered: `grc.monitoring.overdue`, `grc.monitoring.deadline_reminder`, `grc.monitoring.escalated_to_cia` |
| CIA consolidation/presentation | `monitoring/` list endpoint + `dashboard/stats/` | Dashboard shows implementation rates per engagement/recommendation |

---

## 3. Engagement Lifecycle — How It All Connects

The `grc.engagement_lifecycle` workflow (`workflows.yaml` line 154) tracks the phase of an `AuditEngagement` through 3 WO stages:

```
planning  →  fieldwork  →  reporting  →  completed
```

Each phase represents a body of work:

| Phase | SRS Steps in this phase |
|---|---|
| `planning` | Steps 10–26: Memo, Declaration, Survey, RCM, Audit Program, Engagement Notification |
| `fieldwork` | Steps 27–34: Entry meeting, Working Papers, Pre-exit meeting |
| `reporting` | Steps 35–38: Draft report, auditee responses, exit meeting, final report, distribution |

Phase transitions are driven by the Lead Auditor via `engagements/<pk>/transition/`. The WO stage-completion callback in `apps/infrastructure/messaging/kafka_consumer.py` (method `_handle_audit_engagement_stage()` at line ~590) advances `AuditEngagement.status` when WO confirms the stage is complete.

---

## 4. Workflow Architecture — How WO Is Used

Every approval-gated document follows this FIMS pattern:

```
1. User submits document via API view
         ↓
2. Service class (e.g. audit_memo_service.py) calls OrchestrationClient.start_workflow()
         ↓
3. WO creates a workflow plan with stages from the YAML template
         ↓
4. WO assigns tasks to users/roles per the YAML `assignees` field
         ↓
5. Reviewer acts (approve/reject/return) via WO task UI
         ↓
6. WO publishes Kafka event to `workflow-events` topic
         ↓
7. kafka_consumer.py receives event → routes by `template_code`
         ↓
8. Handler method updates model status/fields in grc-service DB
```

**YAML template → service file mapping:**

| YAML template code | Service file | Kafka handler method |
|---|---|---|
| `grc.audit_universe_approval` | `audit_universe_service.py` | `_handle_audit_universe_completion()` |
| `grc.rbiap_approval` | `audit_plan_service.py` | `_handle_audit_plan_completion()` |
| `grc.engagement_lifecycle` | `audit_engagement_service.py` | `_handle_audit_engagement_stage()` |
| `grc.engagement_notification_approval` | `engagement_notification_service.py` | `_handle_engagement_notification_stage()` |
| `grc.audit_memo_approval` | `audit_memo_service.py` | `_handle_audit_memo_stage()` |
| `grc.audit_program_approval` | `audit_program_service.py` | (handled in `_handle_audit_program_stage()`) |
| `grc.working_paper_approval` | `working_paper_service.py` | `_handle_working_paper_stage()` |
| `grc.audit_report_approval` | `audit_report_service.py` | `_handle_audit_report_stage()` |
| `grc.quarterly_report_approval` | `quarterly_report_service.py` | `_handle_quarterly_report_stage()` |

All templates are loaded on startup. Look for this log line to confirm healthy load:
```
GRC: loaded 9 workflow template(s) from YAML: ['grc.working_paper_approval', 'grc.audit_universe_approval', ...]
```

---

## 5. Notification Architecture — How Alerts Are Sent

grc-service **never sends email directly**. It publishes to Kafka. The Work Orchestration Service consumes those topics and handles delivery.

```
grc-service code
    ↓
publisher.send_notification(template_code, recipients, context, priority)
    ↓ (apps/core/notifications/publisher.py)
Kafka topic: notifications-high  OR  notifications-normal
    ↓
Work Orchestration Service notification consumer
    ↓
Email + in-app notification to user
```

All notification templates live in `apps/core/templates/notifications.yaml`. On startup, all templates are published to the `notification-templates` Kafka topic so WO knows how to render them.

**Current templates registered (11 total):**
- `grc.engagement_notification.approved` — EN approval alert to LA
- `grc.engagement_notification.returned` — EN returned for revision
- `grc.monitoring.overdue` — Auditee response window lapsed
- `grc.monitoring.deadline_reminder` — Day-3 reminder to auditee
- `grc.monitoring.escalated_to_cia` — Day-7 escalation to CIA
- *(+ 6 others for engagement/plan lifecycle)*

IAM user profile resolution pattern (used before every `send_notification` call):
```python
from apps.infrastructure.external.iam_client import IAMClient
iam = IAMClient()
profile = iam.get_user_profile(str(user_id))  # returns dict: first_name, last_name, email
```

---

## 6. Remaining Gaps — What Is Still Needed

### GAP-A: CIA Digital Signature + QR Code Auto-Embedding on Document Approval

**SRS Reference:** `AUDT2_ext.md` §1.8.3 Step 11: *"CIA approve (Signature and QR Code embedded automatically)"*; Step 25–26: EN must be issued with CIA signature + QR; §1.8.3 Step 32: working papers approved with embedded signature; System Requirement 38: *"distribute approved Internal Audit Report, Signed Declaration of Independence/Conflict of interest Form"*

**What the SRS requires:**
When the CIA approves a document (Engagement Notification, Audit Memo, Working Paper, Audit Program, Declaration of Independence), the system must automatically produce a PDF with:
1. The CIA's digital signature embedded
2. A QR code embedded (for verification by any reader)
3. The stamped PDF URL saved back to the record

**Current state in grc-service:**
The fields are fully scaffolded in the DB for all 5 document types:

| Model | Field | Location |
|---|---|---|
| `AuditMemo` | `document_id`, `stamped_document_url` | `audit_entities.py` line ~2111 |
| `EngagementNotification` | `document_id`, `stamped_document_url` | `audit_entities.py` line ~2756 |
| `WorkingPaper` | `document_id`, `stamped_document_url` | `audit_entities.py` line ~1484 |
| `AuditProgram` | `document_id`, `stamped_document_url` | `audit_entities.py` line ~2592 |
| `DeclarationOfIndependence` | `document_id`, `stamped_document_url` | `audit_entities.py` line ~2284 |

All are currently stored as `null` after CIA approval because **the PDF stamping hook is not wired**.

**What must happen (both sides):**

*Side 1 — Document Records Service (DRS) must expose:*
```
POST /api/documents/{document_id}/stamp/
Body: { "signer_user_id": "uuid", "signature_type": "cia_approval", "qr_payload": "..." }
Response: { "stamped_document_url": "https://..." }
```

*Side 2 — grc-service must call it (this is the grc-service work):*
In `apps/infrastructure/messaging/kafka_consumer.py`, inside each CIA-approval handler method, after setting `status='approved'`, add:
```python
# Pattern to follow — add inside _handle_audit_memo_stage(), _handle_engagement_notification_stage(), etc.
from apps.infrastructure.external.drs_client import DRSClient
drs = DRSClient()
stamped_url = drs.stamp_document(
    document_id=str(record.document_id),
    signer_user_id=str(cia_user_id),
    qr_payload=f"FIMS-GRC:{record.reference_number}:{record.id}"
)
if stamped_url:
    record.stamped_document_url = stamped_url
    record.save(update_fields=['stamped_document_url'])
```

A `DRSClient` class needs to be created at `apps/infrastructure/external/drs_client.py`, following the same pattern as `IAMClient` and `OrchestrationClient` in that directory.

**Blocked by:** DRS must expose the `/stamp/` endpoint first. Once it does, the grc-service side is ~80 lines of code.

**Priority:** 🔴 HIGH — this is a visible SRS requirement. Every approved document must have a QR code per the SRS. Without it, printed documents have no verification mechanism.

---

### GAP-B: Risk Management System Integration

**SRS Reference:** `AUDT2_ext.md` System Requirement 41: *"Two-way sync with the Risk Assurance and Quality Management System to feed audit findings as risks and to pull the organizational risk register for audit planning."*

**What the SRS requires:**
1. **Pull direction** — When an IA starts risk assessment for `AuditPlan`, the organizational risk register from the Risk Management service should be available as pre-populated data to inform scoring
2. **Push direction** — When a `AuditFinding` is finalized/approved, it should be pushed to the Risk Management service as a registered risk

**Current state in grc-service:**
- `RiskAssessment` scoring is fully manual — IA enters all 6 scores from scratch every time
- `AuditFinding` records are local to grc-service only; the Risk Management service has no knowledge of them
- No `risk_management_client.py` exists in `apps/infrastructure/external/`

**What must happen (both sides):**

*Side 1 — Risk Management Service must expose:*
```
GET  /api/risk-register/?entity_id={uuid}   → returns list of known risks for an auditable entity
POST /api/risks/                            → accepts a new risk created from an audit finding
```

*Side 2 — grc-service must implement (this is the grc-service work):*

Pull direction — in `apps/api/views/risk_assessment_views.py`, when `RiskAssessment` is created for a given `AuditableEntity`, pre-populate from Risk Management:
```python
# In RiskAssessmentListCreateView.post() or a dedicated endpoint
from apps.infrastructure.external.risk_management_client import RiskManagementClient
rmc = RiskManagementClient()
existing_risks = rmc.get_risk_register(entity_id=str(auditable_entity_id))
# Pass as context to the serializer / response
```

Push direction — in `apps/api/views/audit_finding_views.py`, in `AuditFindingFinalizeView.post()`:
```python
rmc.push_finding_as_risk(finding_id=str(finding.id), payload={...})
```

A `RiskManagementClient` class at `apps/infrastructure/external/risk_management_client.py`, following the `IAMClient` pattern.

**Blocked by:** The Risk Management / Risk Assurance and Quality Management Service must expose its risk register API first.

**Priority:** 🟡 MEDIUM — important for the full FIMS vision, but the audit processes work entirely without it. The risk scores in `RiskAssessment` can continue to be manually entered in the meantime.

---

## 7. What Must NOT Be Changed Without Reading This First

These are the points where future developers most often break things:

### 7.1 YAML workflow version numbers
Every workflow template in `apps/core/workflows/workflows.yaml` has a `version:` field. Do **not** change the YAML stages/assignees/actions without also incrementing `version:`. If you edit the YAML but leave the version unchanged, WO will not reseed the template and the old version stays active in the WO database.

Current versions after all P2-GAP fixes:
- `grc.working_paper_approval` → version 2 (bumped in P2-GAP 6)
- `grc.engagement_lifecycle` → version 2 (bumped in P2-GAP 7)
- All others → version 1

### 7.2 `kafka_consumer.py` template_code routing
`apps/infrastructure/messaging/kafka_consumer.py` contains a large `if/elif` chain that routes WO callback events to the correct handler method. If you rename any template code in `workflows.yaml` or `orchestration_client.py`, you **must** update the matching `elif template_code == '...'` line in `kafka_consumer.py`. If you miss it, all callbacks for that template silently fall through to `logger.warning("Unknown GRC template_code")` and model status updates stop working.

Current routing map (lines ~315–360):
```python
elif template_code == 'grc.audit_universe_approval':  → _handle_audit_universe_completion()
elif template_code == 'grc.rbiap_approval':           → _handle_audit_plan_completion()
elif template_code == 'grc.engagement_lifecycle':     → _handle_audit_engagement_stage()
elif template_code == 'grc.engagement_notification_approval': → _handle_engagement_notification_stage()
elif template_code == 'grc.audit_report_approval':    → _handle_audit_report_stage()
elif template_code == 'grc.audit_memo_approval':      → _handle_audit_memo_stage()
elif template_code == 'grc.working_paper_approval':   → _handle_working_paper_stage()
elif template_code == 'grc.quarterly_report_approval':→ _handle_quarterly_report_stage()
```

### 7.3 WorkingPaper.get_workflow_context() must always return `lead_auditor`
`apps/core/models/audit_entities.py`, `WorkingPaper.get_workflow_context()` (line ~1293). The YAML Stage 1 uses `assignees: ["{{lead_auditor}}"]`. If this key is removed from `get_workflow_context()`, Stage 1 reviewer will be unresolved. The key is `str(self.engagement.lead_auditor)` — it goes through the FK to the parent engagement.

### 7.4 AuditeeFollowUpResponse `unique_together` constraint
`unique_together = [['monitoring', 'cycle_number']]`. Never create two rows with the same `(monitoring_id, cycle_number)` pair. The review endpoint auto-increments `cycle_number` to `max+1`. If you rewrite that logic, you must preserve this uniqueness.

### 7.5 Celery beat schedule
The monitoring deadline task is scheduled in `config/settings.py` under `CELERY_BEAT_SCHEDULE` as key `'check-monitoring-deadlines-daily'`, running at 07:00. The Celery beat container must be running for this to fire. If the task stops running, monitoring deadlines will never be marked overdue and no notifications will be sent.

---

## 8. Complete File Inventory — GRC Backend

```
apps/
├── core/
│   ├── models/
│   │   ├── audit_entities.py        ← ALL domain models (2800+ lines)
│   │   ├── organizational.py        ← Directorate/Department/Unit/Section
│   │   ├── lookups.py               ← FiscalYear, Quarter, RiskRating, AuditSeverity, etc.
│   │   └── base.py                  ← BaseModel, TimestampedModel, StatusMixin, WorkflowMixin
│   ├── services/
│   │   ├── audit_universe_service.py
│   │   ├── audit_plan_service.py
│   │   ├── audit_engagement_service.py
│   │   ├── audit_memo_service.py
│   │   ├── audit_program_service.py
│   │   ├── audit_report_service.py
│   │   ├── engagement_notification_service.py
│   │   ├── quarterly_report_service.py
│   │   └── working_paper_service.py
│   ├── tasks/
│   │   └── monitoring_deadlines.py  ← Celery: check_monitoring_deadlines (daily 07:00)
│   ├── templates/
│   │   └── notifications.yaml       ← 11 notification templates published to WO on startup
│   └── workflows/
│       └── workflows.yaml           ← 9 WO workflow templates loaded on startup
├── api/
│   ├── urls/
│   │   └── audit.py                 ← All 70+ URL patterns
│   └── views/
│       ├── audit_universe_views.py
│       ├── audit_plan_views.py
│       ├── audit_engagement_views.py
│       ├── audit_memo_views.py
│       ├── audit_program_views.py
│       ├── audit_report_views.py
│       ├── audit_survey_views.py
│       ├── audit_meeting_views.py
│       ├── audit_finding_views.py
│       ├── audit_recommendation_views.py
│       ├── implementation_monitoring_views.py
│       ├── working_paper_views.py
│       ├── quarterly_report_views.py
│       ├── engagement_notification_views.py
│       ├── declaration_views.py
│       ├── rcm_views.py
│       ├── risk_assessment_views.py
│       ├── auditable_entity_views.py
│       └── audit_dashboard_views.py
└── infrastructure/
    ├── external/
    │   ├── iam_client.py            ← IAM user profile resolution
    │   ├── orchestration_client.py  ← WO workflow start/status/history
    │   └── (drs_client.py)          ← DOES NOT EXIST YET — needed for GAP-A
    └── messaging/
        └── kafka_consumer.py        ← Receives ALL WO callback events, routes to handlers
```

---

## 9. How to Verify the Backend Is Healthy

Run this after any restart or deployment:

```bash
# 1. Check all 9 workflow templates loaded
docker logs fims-grc-service 2>&1 | grep "GRC: loaded"
# Expected: GRC: loaded 9 workflow template(s) from YAML: ['grc.working_paper_approval', ...]

# 2. Check all 11 notification templates published
docker logs fims-grc-service 2>&1 | grep "notification.*template\|published.*template"

# 3. Check no startup errors
docker logs fims-grc-service 2>&1 | grep -i "error\|exception\|traceback" | grep -v "404"

# 4. Check migrations are applied
docker exec fims-grc-service python manage.py showmigrations core | grep "\[X\]"
# Must show 0014 applied (latest: 0014_auditee_follow_up_response)
```

---

## 10. P2-GAP Resolution Summary (Final)

| Gap | Title | SRS Backed | Resolution | Date |
|---|---|---|---|---|
| P2-GAP 1 | EngagementNotification model + workflow | ✅ SRS Req 24–26 | `EngagementNotification` model + `grc.engagement_notification_approval` YAML + service + views + URLs | Completed |
| P2-GAP 2 | Missing YAML workflow templates | ✅ SRS Req 11–13, 22–23, 36 | Added `grc.audit_memo_approval`, `grc.audit_program_approval`, `grc.audit_report_approval` to `workflows.yaml` | Completed |
| P2-GAP 3 | QuarterlyAuditReport bypasses WO | ✅ SRS 1.8.5 | Rewrote `QuarterlyAuditReport.get_workflow_stages()` with 4 SRS-exact stages + correct action names; created `quarterly_report_service.py`; wired kafka_consumer handler | Completed |
| P2-GAP 4 | ImplementationMonitoring OneToOne overwrites history | ✅ SRS Req 39 | Added `AuditeeFollowUpResponse` (M:1 cycle model); migration 0014; 5 new view classes; 6 new URL routes; updated serializers | Completed |
| P2-GAP 5 | Celery deadline task uses wrong Kafka path | ✅ SRS Req 39 | Rewrote `monitoring_deadlines.py` to use `publisher.send_notification()`; added 3 notification templates to `notifications.yaml`; IAM-resolved recipient profiles | Completed |
| P2-GAP 6 | Working paper reviewer assigned to preparer | ✅ SRS 1.8.3 Step 16 | `workflows.yaml` Stage 1: `{{prepared_by}}` → `{{lead_auditor}}`; `WorkingPaper.get_workflow_context()` adds `lead_auditor` key | Completed |
| P2-GAP 7 | `grc.engagement_notification` name ambiguity | 🟢 Opinion | Renamed to `grc.engagement_lifecycle` across 4 files: `workflows.yaml`, `orchestration_client.py`, `audit_engagement_service.py`, `kafka_consumer.py` | Completed |
| P2-GAP 8 | AuditEngagement uses WorkflowMixin overhead | 🟢 Opinion | **Intentionally deferred** — working correctly; WO overhead not measurable; removing it requires deleting a live service file and breaking the engagement start endpoint | Deferred |
| GAP-A | CIA signature + QR code PDF stamping | ✅ SRS Req 11, 25–26, 32, 38 | Fields scaffolded (`stamped_document_url`) on 5 models. **Blocked: DRS must expose `/stamp/` endpoint.** grc-service hook is ~80 lines in `kafka_consumer.py` + new `drs_client.py` | Pending (blocked) |
| GAP-B | Risk Management System sync | ✅ SRS Req 41 | Nothing implemented. **Blocked: Risk Management Service must expose risk register + ingest APIs.** grc-service side is `risk_management_client.py` + hook in `RiskAssessmentListCreateView` + `AuditFindingFinalizeView` | Pending (blocked) |



