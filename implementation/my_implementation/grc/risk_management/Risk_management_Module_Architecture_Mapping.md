# Risk Management Module — FIMS Architecture Mapping

> **Module:** Risk Management (within `grc-service`)
> **Phase:** 2 — Architecture Mapping
> **Input:** `RISK_DOMAIN_EXTRACTION.md`
> **Reference:** `FIMS_ARCHITECTURE.md`
> **Date:** 2026-03-19

---

## Table of Contents

1. [Risk Management Module Responsibilities](#1-risk-management-module-responsibilities)
2. [Delegated Responsibilities](#2-delegated-responsibilities)
   - 2.1 IAM Service
   - 2.2 Document Records Service
   - 2.3 Work Orchestration Service
3. [Integration Points](#3-integration-points)
4. [Module Boundaries](#4-module-boundaries)
5. [Potential Overlapping Responsibilities](#5-potential-overlapping-responsibilities)

---

## 1. Risk Management Module Responsibilities

These are capabilities that belong **strictly inside the `grc-service` Risk Management module**.  
The grc-service owns the domain data, business logic, and state machines for all of the following.

---

### 1.1 Organisational Structure Registry

- Store and manage the FCC organisational structure as it relates to risk management:
  - **Directorates**, **Units**, and **Zones** as organisational units.
- Maintain the active list of Directorates/Units/Zones for assignment of Risk Champions and Quality Auditors.
- These are grc-service-local records — they are **not** user records (those belong to IAM), they are structural/organisational entities.

---

### 1.2 Risk Champion (RC) Lifecycle Management

- Record all **nomination requests** submitted by RMQAM to Heads (as grc-service data objects, not IAM roles).
- Record all **RC nominations** submitted by Heads (nominee IAM UUID, supporting details, Directorate/Unit/Zone reference).
- Track nomination **status**: `Pending` → `Nominated` → `Under Review` → `Letter Drafted` → `Letter Reviewed` → `Appointed` → `Active` → `Inactive`.
- Store the **appointment record** (linking IAM user UUID for the RC, their Directorate/Unit/Zone, effective date, term end date, appointment letter document UUID).
- Enforce the **one active RC per Directorate/Unit/Zone** constraint.
- Record **RC replacements** before term end (reason, replacement date, new nominee).
- Maintain the **historical list of all past RCs** per Directorate/Unit/Zone.
- Expose an endpoint to query the current active RC for any Directorate/Unit/Zone.

---

### 1.3 Quality Auditor (QA) / Quality Champion (QC) Lifecycle Management

- Record all **QA nomination requests** and **nominations** (same pattern as RC).
- Track the full QA lifecycle including the **ISO 9001:2015 training and examination** sub-process:
  - Trainer engagement details (trainer name, date, venue, approval status).
  - Trainee (nominee) list per training session.
  - Examination attempt records (attempt number, score, pass/fail).
  - Pass threshold enforcement: **75% minimum**.
  - Replacement nomination trigger on second attempt failure.
- Store the **QA appointment record** (IAM user UUID, Directorate/Unit/Zone, certification date, exam score, term, appointment letter document UUID).
- Enforce the **conflict of interest constraint** (QA cannot be assigned to audit their own Directorate/Unit/Zone).
- Maintain the **historical list of all past QAs** per Directorate/Unit/Zone.

---

### 1.4 Risk Assessment Sheet (RAS) — Data Management

- Store all individual **Risk Assessment Sheet** records:
  - Risk description, risk category, risk owner (IAM user UUID), Directorate/Unit/Zone.
  - Likelihood rating, impact rating.
  - Inherent risk level (computed from likelihood × impact matrix or explicit input).
  - Existing controls (text).
  - Residual risk level.
  - Proposed controls (text).
- Track submission status of each RAS through its lifecycle: `Draft` → `Submitted to Head` → `Head Endorsed` → `Submitted to RMQAM` → `Approved` / `Returned for Rework`.
- Record **review comments** and **rework history** (who returned, when, what comment).
- The data records in the grc-service database are the source of truth for risk data — the actual document file (PDF/Word export) is stored in Document Records Service.

---

### 1.5 Departmental Risk Register (DRR) — Data Management

- Maintain a **Departmental Risk Register record** per Directorate/Unit/Zone per reporting period (semi-annual).
- A DRR is a logical container of multiple approved Risk Assessment Sheets for a given Directorate/Unit/Zone.
- Track the DRR lifecycle status: `In Progress` → `Submitted to RMQAM` → `Approved` / `Returned for Rework`.
- Store RMQAM approval metadata (approver IAM UUID, approval date, comments).
- Maintain rework history.

---

### 1.6 Institutional Risk Register (IRR) — Data Management

- Maintain the **Institutional Risk Register record** per reporting period (semi-annual).
- IRR is built from all approved DRRs; the grc-service owns the logic that:
  - **Filters** risks by risk threshold/appetite: only risks exceeding the threshold are included.
  - **Aggregates** risks from all Directorates/Units/Zones into the IRR.
- Track the IRR lifecycle status: `Draft` → `Workshop Held` → `Compiled` → `Under RMQAM Review` → `Submitted to DG (Activity Report)` → `Submitted to Management` → `Management Reviewed` → `Submitted to Committee` → `Committee Reviewed` → `Approved` / `Returned`.
- Store governance chain metadata at each stage (who submitted, when, comments, directives).
- Enforce: only one **active (current)** IRR at a time.

---

### 1.7 Risk Treatment Action Plan (RTAP) — Data Management & Tracking

- Maintain the **Risk Treatment Action Plan** as a set of control implementation records, one per risk entry in the IRR.
- Each RTAP item owns:
  - Link to the associated risk (IRR risk record UUID).
  - Control description.
  - Responsible officer (IAM user UUID — Risk Owner / RC).
  - Target implementation date.
  - Current implementation status: `Not Started` / `In Progress` / `Completed`.
  - Supporting evidence / comments.
  - Last updated date.
- The grc-service performs the **quarterly consolidation** logic:
  - When RCs submit status updates, the service consolidates them into the RTAP.
- The grc-service owns the **comparative analysis** computation:
  - Calculate current quarter implementation rate (%).
  - Calculate previous quarter implementation rate (%).
  - Compute variance and quarter-on-quarter trend.
- Maintain **per-quarter snapshots** of implementation rates for historic trend data.
- Track **rework cycles**: when RMQAM returns a submission to RMO, or RMO to RC.

---

### 1.8 Quarterly Performance Report — Generation & State

- Own the **generation** of the Quarterly Performance Report (QPR):
  - Consolidating: RTAP implementation status + RMQA Plan progress + comparative analysis results.
- Track the QPR lifecycle status: `Draft` → `Submitted to Management` → `Management Reviewed` → `Submitted to Committee` → `Committee Reviewed` → `Committee Directives Actioned` → `Submitted to Commission`.
- Store all governance metadata at each stage (submission dates, committee directives, actions taken).
- Enforce: QPR submitted to Committee **at least 7 days before** Committee meeting (validation against committee meeting date).

---

### 1.9 QMS Audit Program — Data Management

- Store the **annual QMS Audit Program** record:
  - Audit year, scope, objectives, processes to be audited, assigned QAs per process.
- Track lifecycle: `Draft` → `Under RMQAM Review` → `Approved` / `Returned for Rework`.

---

### 1.10 Audit Plan — Data Management

- Store individual **Audit Plan** records linked to the QMS Audit Program.
- Track per audit engagement: dates, audit team (QA IAM UUIDs), designated Team Leader (TL IAM UUID), audit timetable.
- Track lifecycle: `Draft` → `Under RMQAM Review` → `Approved` / `Returned for Rework`.

---

### 1.11 Audit Checklist — Data Management

- Store **Audit Checklist** records created by QAs for their assigned processes.
- Each checklist is linked to: Audit Plan, assigned QA (IAM UUID), assigned process, ISO 9001:2015 clause references.
- Capture checklist item outcomes (conformity status, evidence references).

---

### 1.12 Audit Report — Data Management

- Store **individual QA Audit Reports** (per QA per engagement):
  - Audit reference, auditee (Directorate/Unit/Zone), audit date, QA (IAM UUID).
  - List of Non-Conformances (NCs) and Areas for Improvement.
  - Auditee acknowledgment status, auditee signature reference.
- Store the **consolidated TL Audit Report** (aggregation of individual reports):
  - TL (IAM UUID), auditee signature, TL signature.
  - Final agreed observation list (after exit meeting dispute resolution).
- Track the report lifecycle:  
  `Draft` → `NCs Presented to Auditee` → `Exit Meeting Held` → `Signed` → `Submitted to RMQAM` → `Presented at MRM` → `MRM Directives Received`.

---

### 1.13 Non-Conformance (NC) — Record Management

- Store individual **Non-Conformance records**:
  - NC reference, audit report reference, description, ISO clause violated, evidence, auditee responsible (IAM UUID).
  - Proposed corrective action, target closure date, closure status.
- Own the **NC lifecycle**: `Open` → `Action Assigned` → `In Progress` → `Closed`.
- Track month-by-month closure status (per SRS requirement: RMQAU monitors closure monthly).

---

### 1.14 Risk Identification Support

- Support **awareness session records** (RMQAU conducts sessions for RCs, Risk Owners, and staff):
  - Session date, participants (IAM UUIDs), topics covered.
- Provide structured data entry for risks identified through brainstorming, workshops, interviews, and surveys.
- Allow import/linkage from historical audit reports and lessons-learned records.

---

### 1.15 Risk Threshold / Risk Appetite Configuration

- Own and expose the **institutional risk appetite/threshold configuration**:
  - Configurable threshold values per risk category.
  - Used by the IRR compilation logic to filter which risks escalate.
- Only RMQAM (or authorised roles) may update the threshold configuration.

---

### 1.16 Permission Registration

- Define and publish all grc-service (Risk Management) permissions to IAM via Kafka:
  - Examples: `risk.champion.create`, `risk.register.approve`, `risk.audit.conduct`, `risk.report.submit`, `risk.threshold.configure`, `risk.nc.manage`, etc.
- A `PermissionPublisher` fires on service startup to register all permissions with IAM.

---

## 2. Delegated Responsibilities

---

### 2.1 → IAM Service

The grc-service **never** manages user authentication, user accounts, roles, or system-wide permission storage. All of the following are delegated to IAM:

| Delegated Responsibility | Details |
|--------------------------|---------|
| **Authentication** | All actors (RMQAM, RMO, RC, QA, Director, DG, LSM, Commission members) authenticate via IAM. JWT is validated locally in grc-service using the shared `JWT_SECRET_KEY`. No runtime calls to IAM per request. |
| **User identity & profile** | The grc-service refers to all users by their IAM UUID. User names, emails, and designations are fetched via `IAMClient` (HTTP with Redis-backed cache) when needed for display/notifications. The grc-service **never stores a user table**. |
| **Role assignment** | Roles such as `RMQAM`, `RMO`, `Risk Champion`, `Quality Auditor`, `Director`, `Director General` are assigned and managed in IAM. |
| **Permission registry** | All grc-service permission codes (e.g., `risk.register.approve`) are registered in IAM via Kafka. IAM aggregates them into the JWT `permissions_flat` payload. Decision on whether a user can perform an action is made locally in grc-service by reading `request.user_permissions_flat`. |
| **Audit logging of auth events** | Login, logout, session management, role changes — all owned by IAM. |

**What grc-service does with IAM:**
- Validates JWT tokens **locally** (no IAM call per request).
- Calls `IAMClient` (cached REST) to resolve IAM user UUID → display name/email for notification context.
- Publishes `grc-service` permissions to Kafka topic `service.permission.registry`.

---

### 2.2 → Document Records Service

The grc-service **never stores files**. All official documents produced by the Risk Management processes are delegated to the Document Records Service. The grc-service stores only the document's UUID as a reference.

| Document / Artefact | When Delegated | grc-service Stores |
|---------------------|---------------|-------------------|
| **RC Appointment Letter** (draft + signed) | After RMO drafts it; after DG signs it | Document UUID reference in RC appointment record |
| **QA Appointment Letter** (draft + signed) | After RMO drafts it; after DG signs it | Document UUID reference in QA appointment record |
| **Risk Assessment Sheet** (official export) | When a RAS is finalised/approved | Document UUID reference in RAS record |
| **Departmental Risk Register** (official export) | When DRR is approved by RMQAM | Document UUID reference in DRR record |
| **Institutional Risk Register** (official export) | At each governance stage requiring a formal copy | Document UUID in IRR record per stage |
| **Risk Treatment Action Plan** (official export) | When RTAP version is finalised per governance stage | Document UUID in RTAP version record |
| **Activity Report** | When RMO prepares it for submission to DG | Document UUID in IRR record |
| **Quarterly Performance Report** | When QPR is prepared and at each submission stage | Document UUID in QPR record per stage |
| **QMS Audit Program** | When approved | Document UUID in QMS Audit Program record |
| **Audit Plan** | When approved | Document UUID in Audit Plan record |
| **Audit Checklist** | When submitted by QA | Document UUID in Audit Checklist record |
| **Audit Report** (individual + consolidated) | When signed and finalised | Document UUID in Audit Report record |
| **Non-Disclosure / Confidentiality Form** | When signed at entry meeting | Document UUID in Audit engagement record |
| **Management Review Meeting (MRM) Minutes** | After MRM is concluded | Document UUID in Audit Report record |

**What grc-service does with Document Records Service:**
- Calls `POST /api/v1/documents/` (multipart) to upload files.
- Stores the returned document UUID locally.
- Provides `GET /api/v1/documents/<id>/` and download links to frontend — by proxy through grc-service API or by exposing the document UUID to the frontend to call Document Records Service directly.
- Never stores file content, binary data, or document version history.

---

### 2.3 → Work Orchestration Service

The grc-service **never** hardcodes multi-step approval chains, sends emails/SMS directly, or manages notification templates. All workflow orchestration and notification delivery are delegated to the Work Orchestration Service.

#### 2.3.1 Workflow Plans (Approval Pipelines)

The grc-service creates workflow plans in Work Orchestration for every multi-step review and approval process:

| Process | Workflow Plan Type | Stages |
|---------|-------------------|--------|
| **RC Appointment Letter** | `risk.rc_appointment` | `RMO: Draft Letter` → `RMQAM: Review` → `DG: Sign` → `Registry: Dispatch` |
| **QA Appointment Letter** | `risk.qa_appointment` | `RMO: Draft Letter` → `RMQAM: Review` → `DG: Sign` → `Registry: Dispatch` |
| **Risk Assessment Sheet Approval** | `risk.assessment_sheet_approval` | `RC: Submit to Head` → `Head: Endorse` → `RC: Forward to RMQAM` → `RMQAM: Approve` / `RMQAM: Return for Rework` |
| **Departmental Risk Register Approval** | `risk.dept_register_approval` | `RC: Submit to RMQAM` → `RMQAM: Approve` / `RMQAM: Return for Rework` |
| **Institutional Risk Register Governance** | `risk.institutional_register_governance` | `RMO: Compile` → `RMQAM: Review` → `RMQAM: Submit to DG (Activity Report)` → `Management: Discuss` → `RMQAM: Action Recommendations` → `LSM: Submit to Committee` → `Committee: Review` → `RMQAM: Act on Directives` → `Commission: Approve` |
| **Quarterly Performance Report Governance** | `risk.quarterly_report_governance` | `RMQAM: Prepare QPR` → `LSM: Submit to Management` → `Management: Discuss` → `RMQAM: Act on Recommendations` → `LSM: Submit to Committee` → `Committee: Directives` → `RMQAM: Act on Directives` → `LSM: Submit to Commission` |
| **QMS Audit Program Approval** | `risk.qms_audit_program_approval` | `RMO: Prepare Program` → `RMQAM: Review` → `RMQAM: Approve` / `RMQAM: Return for Rework` |
| **Audit Plan Approval** | `risk.audit_plan_approval` | `RMO: Prepare Plan` → `RMQAM: Review` → `RMQAM: Approve` / `RMQAM: Return for Rework` |
| **Audit Execution** | `risk.qms_audit_execution` | `QA: Prepare Checklists` → `TL: Entry Meeting` → `QA: Conduct Audit` → `QA: Draft Report` → `TL: Consolidate` → `TL: Exit Meeting` → `Auditee: Sign` → `TL: Sign` → `TL: Submit to RMQAM` → `RMQAM: Present at MRM` → `RMQAM: Communicate Directives` |
| **NC Corrective Action** | `risk.nc_corrective_action` | `Auditee: Submit Corrective Action Plan` → `RMQAM: Review` → `RMQAM: Approve Closure` / `RMQAM: Reject` |

**How grc-service integrates:**
- On business event (e.g., RC nomination received), grc-service calls `WorkOrchestrationClient` → `POST /api/v1/workflow/plans/` (synchronous REST, service-to-service via `X-Service-Token`).
- grc-service listens for workflow state-change events on Kafka topic `workflow-events` and updates its own domain state accordingly (e.g., when DG signs, the grc-service RC record moves to `Appointed`).

#### 2.3.2 Notification Delivery

The grc-service **never** calls SMTP, SMS APIs, or Django's `send_mail`. All notifications are published to Kafka priority topics for Work Orchestration to deliver.

| Notification Event | Priority | Channel | Trigger |
|-------------------|----------|---------|---------|
| RC nomination request to Heads | `normal` | Email, in-app | RMQAM initiates RC appointment process |
| RC appointment letter dispatched | `normal` | Email, in-app | DG signs appointment letter |
| QA nomination request to Heads | `normal` | Email, in-app | RMQAM initiates QA appointment process |
| QA training notification to candidates | `normal` | Email, in-app | RMQAM approves training schedule |
| QA appointment letter dispatched | `normal` | Email, in-app | DG signs appointment letter |
| Risk meeting notification (RC → staff) | `normal` | Email, in-app | RC triggers meeting in system |
| Risk Assessment Sheet returned for rework | `normal` | Email, in-app | RMQAM returns RAS to RC |
| Risk Assessment Sheet approved | `normal` | Email, in-app | RMQAM approves RAS |
| Workshop attendance permission request | `normal` | Email, in-app | RMQAM requests permission from Heads |
| Workshop notification to RCs | `normal` | Email, in-app | RMO notifies RCs of workshop |
| Quarterly RTAP status reminder to RCs | `normal` | Email, in-app | Quarterly Celery Beat trigger |
| RTAP status returned for rework | `normal` | Email, in-app | RMO returns submission to RC |
| Quarterly Performance Report submitted | `normal` | Email, in-app | RMQAM submits to Management |
| Audit notification to auditees | `high` | Email, in-app | RMQAM sends audit notice (10 working days before) |
| Committee submission confirmation | `high` | Email, in-app | 7-day pre-submission reminder |
| NC corrective action assigned | `high` | Email, in-app | RMQAM communicates MRM directives |
| NC closure overdue | `high` | Email, in-app | Celery Beat monthly NC closure check |

**How grc-service integrates:**
- Uses a `NotificationPublisher` (identical pattern to other FIMS services) to publish to Kafka topics: `notifications-high`, `notifications-normal`.
- Registers all notification templates with Work Orchestration via Kafka topic `notification-templates` on service startup.

#### 2.3.3 Reminders

The grc-service publishes reminder requests to Work Orchestration for time-sensitive obligations:

| Reminder | Trigger Logic | Managed By |
|----------|--------------|-----------|
| Quarterly RTAP submission reminder | Celery Beat fires 2 weeks before quarter end; publishes Kafka event | Work Orchestration executes multi-channel delivery |
| 7-day pre-submission to Committee | grc-service computes `committee_meeting_date - 7 days`; publishes reminder event to Kafka | Work Orchestration delivers |
| 10-working-day audit notification | grc-service computes `audit_start_date - 10 working days`; publishes reminder event | Work Orchestration delivers |
| Monthly NC closure check | Celery Beat monthly task; grc-service identifies overdue NCs; publishes notification events | Work Orchestration delivers |

---

## 3. Integration Points

### 3.1 Integration Summary Table

| Integration | Direction | Protocol | Topic / Endpoint | When |
|-------------|-----------|----------|-----------------|------|
| JWT validation | Inbound (all requests) | Local decode | `JWT_SECRET_KEY` shared secret | Every authenticated request |
| User profile lookup | grc-service → IAM | **REST (sync)** | `GET /api/v1/iam/users/<uuid>/` | When rendering notifications / display names (cached via Redis, 5-min TTL) |
| Permission registration | grc-service → IAM | **Kafka (async)** | `service.permission.registry` | Service startup (Celery task or management command) |
| Document upload | grc-service → Doc Records | **REST (sync)** | `POST /api/v1/documents/` | When a document/form is finalised and needs storage |
| Document reference retrieval | grc-service → Doc Records | **REST (sync)** | `GET /api/v1/documents/<uuid>/` | When frontend requests document metadata or download link |
| Workflow plan creation | grc-service → Work Orchestration | **REST (sync)** | `POST /api/v1/workflow/plans/` | On business event requiring a multi-step approval pipeline |
| Workflow stage advancement | grc-service → Work Orchestration | **REST (sync)** | `POST /api/v1/workflow/plans/<id>/stages/<id>/actions/` | When a user performs an action in grc-service that advances a workflow stage |
| Workflow state-change events | Work Orchestration → grc-service | **Kafka (async)** | `workflow-events` | When Work Orchestration advances/completes a workflow stage |
| Notification template registration | grc-service → Work Orchestration | **Kafka (async)** | `notification-templates` | Service startup |
| Notification delivery (normal) | grc-service → Work Orchestration | **Kafka (async)** | `notifications-normal` | When a normal-priority notification is triggered |
| Notification delivery (high) | grc-service → Work Orchestration | **Kafka (async)** | `notifications-high` | When a high-priority notification is triggered (audits, directives) |
| Quarterly reminder trigger | grc-service → Work Orchestration | **Kafka (async)** | `notifications-normal` | Celery Beat quarterly task |
| Domain events (outbound) | grc-service → all consumers | **Kafka (async)** | `grc-service.risk.events` | On significant domain state changes (IRR approved, NC opened/closed, RTAP updated) |

---

### 3.2 REST Integration Details

#### With IAM Service (`IAMClient`)
- All calls use `X-Service-Token: <SERVICE_TO_SERVICE_TOKEN>` for service-to-service auth.
- Responses are cached in Redis with a **5-minute TTL**.
- grc-service **never** makes an IAM call per HTTP request — only for user profile resolution.

#### With Document Records Service
- All calls use `X-Service-Token` header.
- Uploads: multipart form data (`POST /api/v1/documents/`).
- grc-service stores only the returned document UUID. All subsequent file access is via Document Records Service.
- A **circuit breaker** should be implemented on calls to Document Records Service (same pattern as `document-records-service/apps/core/workflow/orchestration_client.py`).

#### With Work Orchestration Service (`WorkOrchestrationClient`)
- All calls use `X-Service-Token` header.
- A **circuit breaker** is implemented to protect against cascading failures.
- On circuit open: grc-service queues the workflow creation request locally and retries via Celery.

---

### 3.3 Kafka Integration Details

#### Outbound Topics Published by grc-service

| Topic | Event Type | Payload Summary |
|-------|-----------|----------------|
| `service.permission.registry` | `service_permission_registration` | Full permissions list for `grc-service` |
| `notification-templates` | `notification_template_registration` | All notification templates for Risk Management module |
| `notifications-normal` | `notification_request` | Notification payload with `template_code`, `recipients`, `context`, `priority: normal` |
| `notifications-high` | `notification_request` | Notification payload with `template_code`, `recipients`, `context`, `priority: high` |
| `grc-service.risk.events` | Various (see below) | Domain event envelope |

**Domain events published to `grc-service.risk.events`:**

| Event Type | Trigger |
|-----------|---------|
| `risk.rc.appointed` | RC appointment letter dispatched |
| `risk.qa.appointed` | QA appointment letter dispatched |
| `risk.assessment_sheet.approved` | RMQAM approves a Risk Assessment Sheet |
| `risk.dept_register.approved` | RMQAM approves a Departmental Risk Register |
| `risk.institutional_register.approved` | Commission approves Institutional Risk Register |
| `risk.rtap.updated` | RTAP implementation status updated by RC |
| `risk.quarterly_report.submitted` | QPR submitted to Management |
| `risk.nc.opened` | New Non-Conformance recorded |
| `risk.nc.closed` | NC closure approved by RMQAM |
| `risk.audit.completed` | QMS Audit signed report submitted to RMQAM |

#### Inbound Topics Consumed by grc-service

| Topic | Event Type | Action |
|-------|-----------|--------|
| `workflow-events` | Stage/plan state changes from Work Orchestration | Update grc-service domain object status (e.g., move RC record to `Appointed`, IRR to `Committee Reviewed`) |

---

## 4. Module Boundaries

### 4.1 Inside the Risk Management Module (grc-service)

| Responsibility | Owned By |
|----------------|----------|
| Organisational unit master data (Directorates/Units/Zones) | grc-service |
| RC appointment records (lifecycle, status, term) | grc-service |
| QA appointment records (lifecycle, certification data) | grc-service |
| QA examination records (attempt, score, pass/fail) | grc-service |
| Risk Assessment Sheet data (all risk fields, status) | grc-service |
| Departmental Risk Register records | grc-service |
| Institutional Risk Register records | grc-service |
| Risk threshold / risk appetite configuration | grc-service |
| Risk filtering logic (threshold comparison) | grc-service |
| Risk Treatment Action Plan data (per-control status) | grc-service |
| RTAP quarterly implementation rate calculation | grc-service |
| RTAP quarter-on-quarter comparative analysis | grc-service |
| Quarterly Performance Report generation and state | grc-service |
| QMS Audit Program records | grc-service |
| Audit Plan records | grc-service |
| Audit Checklist data | grc-service |
| Audit Report data (individual QA + consolidated TL) | grc-service |
| Non-Conformance records and lifecycle | grc-service |
| NC monthly closure monitoring (Celery Beat task) | grc-service |
| Risk awareness session records | grc-service |
| Permission code definitions and publishing | grc-service |
| Domain event publishing (`grc-service.risk.events`) | grc-service |

---

### 4.2 Outside the Risk Management Module

| Responsibility | Belongs To |
|----------------|-----------|
| User authentication and session management | IAM Service |
| User accounts, passwords, MFA | IAM Service |
| Role definitions and permission aggregation | IAM Service |
| JWT token issuance | IAM Service |
| Storing document/file binary data | Document Records Service |
| Document versioning and metadata management | Document Records Service |
| Document access control and classification | Document Records Service |
| Document approval workflows (file-level) | Document Records Service → Work Orchestration Service |
| Multi-step approval pipelines (stages/assignees) | Work Orchestration Service |
| Email delivery configuration (SMTP credentials) | Work Orchestration Service |
| SMS delivery (Infobip or similar) | Work Orchestration Service |
| In-app notification storage | Work Orchestration Service |
| Notification template rendering | Work Orchestration Service |
| Reminder scheduling (final execution) | Work Orchestration Service |
| Meeting scheduling and coordination (Commission meetings) | Work Orchestration Service |
| HR records and employee data | Corporate Service |
| Budget and procurement data (for audit evidence) | Corporate Service |
| CORS handling | API Gateway (NGINX) |
| Rate limiting | API Gateway (NGINX) |

---

## 5. Potential Overlapping Responsibilities

---

### Overlap 1: Document Storage vs. Risk Data Storage

**Issue:**  
The Risk Assessment Sheet, Risk Register, and RTAP are both *structured data records* (owned by grc-service) and *formal documents* (PDFs/Word files stored in Document Records Service).

**Resolution:**
- grc-service owns the **structured data** (fields, status, relationships, business logic).
- Document Records Service stores the **generated document file** (PDF export or uploaded file).
- grc-service stores only the **document UUID** returned by Document Records Service.
- There is **no duplication**: the database record in grc-service and the file in Document Records Service are complementary, not competing.
- The grc-service API exposes the risk data fields; the document UUID is used by the frontend to retrieve/download the formal document from Document Records Service.

---

### Overlap 2: Workflow Steps vs. grc-service Domain State

**Issue:**  
Work Orchestration owns workflow plan stages and task assignments. grc-service also tracks the lifecycle status of its own domain objects (e.g., IRR status, DRR status). These can appear redundant.

**Resolution:**
- **Work Orchestration** is the authoritative source for *workflow task assignment, SLA, and actor action state* (who needs to do what next).
- **grc-service** is the authoritative source for *domain object state* (what is the current status of an IRR, a DRR, an RTAP).
- grc-service updates its domain state by **listening to Kafka `workflow-events`** from Work Orchestration — not by polling Work Orchestration.
- The two state machines operate in parallel and serve different consumers:
  - Task-level state → Work Orchestration → drives task dashboard for users.
  - Domain-level state → grc-service → drives business logic, filtering, reporting, and API responses.

---

### Overlap 3: Notification Timing Logic vs. Work Orchestration Reminders

**Issue:**  
grc-service owns the business rules for *when* notifications must be sent (7-day pre-Committee submission, 10-working-day audit notice, quarterly RC reminders). Work Orchestration owns the *delivery*.

**Resolution:**
- grc-service's **Celery Beat tasks** are responsible for computing the correct trigger time and publishing the notification event to Kafka.
- Work Orchestration is responsible only for *rendering* the notification template and *delivering* it through the right channels.
- grc-service **never** configures SMTP, SMS credentials, or retry logic — those belong exclusively to Work Orchestration.

---

### Overlap 4: QA/RC Role Assignment vs. IAM Roles

**Issue:**  
The RC and QA "roles" exist both in the grc-service (as appointment records with business context) and potentially as RBAC roles in IAM.

**Resolution:**
- **IAM** owns the **RBAC role** (permission set): `Risk Champion`, `Quality Auditor` — these control what API endpoints the user can access.
- **grc-service** owns the **appointment record**: which specific IAM user is the active RC/QA for which Directorate/Unit/Zone, with what term dates and history.
- The IAM role is assigned *after* the grc-service appointment record reaches `Appointed` status (triggered via RMQAU's admin actions through IAM, not automatically by grc-service — grc-service does not call IAM to assign roles).
- These are complementary, not competing: IAM role = access control; grc-service record = domain business context.

---

### Overlap 5: Audit in Risk Management vs. Internal Audit System

**Issue:**  
The SRS mentions both a QMS internal audit process (within RMQAU) and a separate Internal Audit System as a distinct GRC module (`1.5.3.5 Internal Audit System`).

**Resolution:**
- The **QMS Audit** (ISO 9001:2015) within this module is owned by the Risk Management module in grc-service.
- The **Internal Audit System** (described separately in `1.5.3.5`) is a **separate GRC sub-module** with its own entities (`Audit Plan`, `Audit Documentation`, `Audit Report` from a compliance/financial audit perspective).
- The two must **not** share data models — they live in separate Django apps within grc-service.
- Cross-references (e.g., historical internal audit reports informing risk assessment) must occur via UUIDs and API queries, not shared tables.

---

### Overlap 6: LSM as Actor vs. Workflow Routing

**Issue:**  
The Legal Service Manager (LSM) acts as a document-routing intermediary between RMQAM and higher governance bodies. This could be modelled as a workflow stage or as a separate actor with dedicated actions.

**Resolution:**
- LSM routing is modelled as **dedicated workflow stages** in Work Orchestration approval plans (e.g., `LSM: Forward to Committee`, `LSM: Forward to Commission`).
- The grc-service **does not** maintain a separate LSM routing model — it is captured purely as a workflow stage state.
- When the workflow stage `LSM: Forward to Committee` completes, grc-service listens to the `workflow-events` event and updates the IRR/QPR domain status accordingly.

---

*This architecture mapping defines the strict boundaries of the Risk Management module within the FIMS grc-service. All implementation decisions should refer back to this document to ensure no duplication of existing platform services.*
