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



