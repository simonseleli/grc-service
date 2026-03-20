# Risk Management Module — Architecture Overview & Directory Structure

**Service:** `grc-service`  
**Module:** Risk Management (RMQAU — Risk Management and Quality Assurance Unit)  
**Stack:** Django 4.x · DRF · PostgreSQL · Celery · Kafka  
**Purpose:** This document defines the architecture of the Risk Management module within `grc-service`, its integration with FIMS platform services, and the full directory and file layout used during implementation.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
   - 1.1 [Module Boundaries](#11-module-boundaries)
   - 1.2 [IAM Service Integration](#12-iam-service-integration)
   - 1.3 [Work Orchestration Service Integration](#13-work-orchestration-service-integration)
   - 1.4 [Document Records Service Integration](#14-document-records-service-integration)
   - 1.5 [Kafka Integration](#15-kafka-integration)
   - 1.6 [Corporate Service Integration](#16-corporate-service-integration)
   - 1.7 [Integration Summary Table](#17-integration-summary-table)
2. [Directory Structure](#2-directory-structure)
   - 2.1 [Full Layout](#21-full-layout)
   - 2.2 [Directory and File Explanation](#22-directory-and-file-explanation)

---

## 1. Architecture Overview

### 1.1 Module Boundaries

The Risk Management module is one domain within `grc-service`. It does **not** run as a separate service — it shares the grc-service process, database, and infrastructure with the Internal Audit module and any future GRC modules.

#### What the Risk Management Module owns

| Responsibility | Description |
|---|---|
| Risk Champion & Quality Auditor lifecycle | Nomination tracking, appointment letter workflow, active roster per Directorate/Unit/Zone |
| Risk Identification & Assessment | Risk Assessment Sheets — likelihood, impact, inherent/residual ratings, controls |
| Departmental Risk Register | Consolidation of approved Risk Assessment Sheets per Directorate/Unit/Zone; approval lifecycle |
| Institutional Risk Register | Aggregated organisation-wide register; threshold filtering, multi-step governance approval |
| Risk Treatment Action Plan (RTAP) | Per-risk control definitions, responsible officers, timelines, quarterly status tracking |
| Quarterly Performance Report | Consolidated quarterly control-implementation status, comparative analysis, governance submission |
| QMS Audit Program & Audit Plan | Annual audit scope, team assignment, plan approval workflows |
| QMS Audit Execution | Checklists, field audit, NC recording, audit report signing |
| Non-Conformance tracking | NC lifecycle from raised to closed, corrective action follow-up |
| Risk scoring & rating logic | Likelihood × impact computation, residual risk calculations |
| Governance routing | State machine for approvals through RMQAM → Management → Risk & Governance Committee → Commission |

#### What the Risk Management Module does NOT own

| Responsibility | Delegated To |
|---|---|
| User authentication and JWT issuance | **IAM Service** |
| Role assignment (RMQAM, RMO, RC, QA, DG, etc.) | **IAM Service** |
| Permission code enforcement | **IAM Service** (codes defined here, enforced locally via JWT claims) |
| Audit log of who accessed what | **IAM Service** |
| Appointment letter PDF storage and versioning | **Document Records Service** |
| RTAP and Risk Register document archiving | **Document Records Service** |
| Audit report PDF storage | **Document Records Service** |
| Multi-step approval workflow engine | **Work Orchestration Service** |
| Reminder scheduling (quarterly report deadlines, RC submission reminders) | **Work Orchestration Service** (via Kafka notification events) |
| Email/SMS/in-app notification delivery | **Work Orchestration Service** (via Kafka) |
| Organisational structure (Directorate, Department, Unit) | **Corporate Service** (synced locally as read-only replicas) |

---

### 1.2 IAM Service Integration

**Mechanism:** JWT-based shared trust (no runtime HTTP calls for authentication).

#### How it works
1. IAM issues JWTs containing `user_id`, `permissions_flat`, and `services` claims.
2. `JWTPermissionMiddleware` in `grc-service` decodes the token locally using the shared `JWT_SECRET_KEY`.
3. Middleware sets `request.user_id`, `request.user_email`, and `request.grc_permissions` on every request.
4. View-level permission classes check `request.grc_permissions` against named permission codes — no IAM HTTP call at runtime.

#### What is delegated to IAM
- User profile resolution (name, email) — via `IAMClient.get_user_profile(user_id)` at read time only.
- Permission catalog registration — Risk Management permission codes are declared in `config/permissions/grc-service.json` and published to IAM on startup via Kafka topic `service.permission.registry`.
- Role binding (RMQAM, RMO, Risk Champion, Quality Auditor, DG roles) — defined in IAM; permission codes are assigned per role in the IAM console.

#### Key constraint
- All user references in Risk Management models store **only UUID values** (e.g., `risk_owner`, `nominated_by`, `appointed_by`). Names and emails are never persisted.

---

### 1.3 Work Orchestration Service Integration

**Mechanism:** REST (HTTP) for workflow plan creation and stage advancement; Kafka for notifications.

#### Workflows integrated with WO

The following Risk Management entities will have approval workflows managed by the Work Orchestration Service:

| Entity | Workflow Template Code | Governance Chain |
|---|---|---|
| `RiskChampionAppointment` | `grc.risk_champion_appointment` | RMO draft → RMQAM review → DG signature |
| `DepartmentalRiskRegister` | `grc.dept_risk_register_approval` | RC submit → RMQAM approve |
| `InstitutionalRiskRegister` | `grc.institutional_risk_register_approval` | RMQAM → Management → Risk & Governance Committee → Commission |
| `RiskTreatmentActionPlan` | `grc.rtap_approval` | Paired with Institutional Risk Register — same chain |
| `QualityAuditorAppointment` | `grc.qa_appointment` | RMO draft → RMQAM review → DG signature |
| `QMSAuditProgram` | `grc.qms_audit_program_approval` | RMO submit → RMQAM approve |
| `QMSAuditPlan` | `grc.qms_audit_plan_approval` | RMO submit → RMQAM approve |
| `QuarterlyPerformanceReport` | `grc.quarterly_risk_report_approval` | RMQAM → LSM → Management → Risk & Governance Committee → Commission |

#### How WO is used
- `OrchestrationClient` (existing in `apps/infrastructure/external/`) makes HTTP calls with `X-Service-Token` auth.
- Each workflow entity includes `WorkflowMixin` fields (`workflow_plan_id`, `workflow_stage`, etc.).
- Service classes in `apps/core/services/` wrap WO calls following the Internal Audit service pattern exactly.

#### Notifications via WO (Kafka)
- Reminder to RCs for quarterly status submission → `notifications-normal` topic
- Escalation to RMQAM when RC is non-responsive → `notifications-high` topic
- Governance submission notifications (7-day pre-meeting rule) → `notifications-high` topic
- DG signature request for appointment letters → `notifications-urgent` topic

All notification events are published via the existing `NotificationPublisher` in `apps/core/notifications/publisher.py`.

---

### 1.4 Document Records Service Integration

**Mechanism:** REST (HTTP) via `DocumentServiceClient` for upload and retrieval.

#### Documents stored in DRS by this module

| Document | When Stored | Field on Model |
|---|---|---|
| RC Appointment Letter (PDF) | After DG signature workflow completes | `document_id` (UUID), `stamped_document_url` |
| QA Appointment Letter (PDF) | After DG signature workflow completes | `document_id`, `stamped_document_url` |
| Institutional Risk Register (PDF export) | After Commission approval | `document_id`, `stamped_document_url` |
| Risk Treatment Action Plan (PDF export) | After Commission approval | `document_id`, `stamped_document_url` |
| QMS Audit Report (signed PDF) | After TL and Auditee sign | `document_id`, `stamped_document_url` |
| Quarterly Performance Report (PDF) | After final governance submission | `document_id`, `stamped_document_url` |

#### Pattern used (same as Internal Audit)
- PDFs generated locally via **WeasyPrint** using Django HTML templates in `templates/grc/risk/`.
- Generated PDFs are uploaded to DRS via `DocumentServiceClient.upload_document()`.
- DRS returns a `document_id` (UUID) and `stamped_document_url` (DRS QR + signature stamped PDF).
- Both references are stored directly on the generating model.

---

### 1.5 Kafka Integration

**Mechanism:** Kafka producer for outbound events; Kafka consumer already running in `grc-service` for org sync and WO events.

#### Events published by this module

| Event Type | Trigger | Topic |
|---|---|---|
| `grc.risk.register.departmental.approved` | Departmental Risk Register approved by RMQAM | `notifications-normal` |
| `grc.risk.register.institutional.submitted` | Institutional Risk Register submitted to Commission | `notifications-high` |
| `grc.risk.rtap.updated` | RTAP quarterly status updated | `notifications-normal` |
| `grc.risk.champion.appointed` | RC appointment letter signed by DG | `notifications-normal` |
| `grc.risk.qa.appointed` | QA appointment letter signed by DG | `notifications-normal` |
| `grc.risk.quarterly_report.submitted` | Quarterly Performance Report submitted to Commission | `notifications-high` |
| `grc.qms.audit.nc.raised` | Non-Conformance raised during QMS audit | `notifications-normal` |

#### Reuse of existing infrastructure
- Events are published via the existing `messaging_service` in `apps/infrastructure/services/messaging_service.py`.
- New event type constants are added to `shared/constants/event_types.py`.
- Event dataclasses are added to `apps/core/events/` (new file: `risk_events.py`).
- The existing Kafka consumer (`apps/infrastructure/messaging/kafka_consumer.py`) already handles org-sync events — no new consumer process needed.

---

### 1.6 Corporate Service Integration

**Mechanism:** Kafka consumer (org sync, already implemented).

The Risk Management module uses the same **Organisational Data Sync** pattern as Internal Audit:
- `Directorate`, `Department`, `Unit`, `Section` models in `apps/core/models/organizational.py` are **read-only replicas** synced from Corporate Service via Kafka.
- Risk Champions are assigned to these org units using FK to the local replica models — never a live HTTP call to Corporate Service.
- `RiskAssessmentSheet` and `DepartmentalRiskRegister` reference `Directorate` / `Unit` by FK to the local copies.
- The existing `OrganizationalSyncService` in `apps/core/services/corporate_sync.py` handles all updates.

#### No additional Corporate Service integration is required.

---

### 1.7 Integration Summary Table

| Integration Point | Mechanism | Direction | Purpose |
|---|---|---|---|
| IAM — authentication | JWT (shared secret, local decode) | Inbound | `JWTPermissionMiddleware` validates every request |
| IAM — user profile | REST via `IAMClient` | Outbound (read-time only) | Resolve UUID → name/email for display |
| IAM — permission registry | Kafka `service.permission.registry` | Outbound (startup) | Register risk module permission codes |
| Work Orchestration — workflow plans | REST via `OrchestrationClient` | Outbound | Start/advance/cancel approval workflows |
| Work Orchestration — notifications | Kafka `notifications-*` topics | Outbound | RC reminders, governance submissions, escalations |
| Document Records — document storage | REST via `DocumentServiceClient` | Outbound | Upload/retrieve appointment letters, register PDFs, audit reports |
| Corporate Service — org structure | Kafka consumer (org-sync, already running) | Inbound | Sync Directorate/Unit replicas |
| Kafka — domain events | Kafka producer (`messaging_service`) | Outbound | Publish risk module domain events |

---

## 2. Directory Structure

### 2.1 Full Layout

The structure below shows **only the additions** required for the Risk Management module inside the existing `grc-service` layout. Files shared with Internal Audit (base models, pagination helpers, response helpers, org models, Kafka infrastructure) are already in place and are reused without modification.

```
grc-service/
│
├── apps/
│   │
│   ├── api/
│   │   ├── serializers/
│   │   │   └── risk_serializers.py              # All Risk Management entity serializers
│   │   │
│   │   ├── urls/
│   │   │   └── risk.py                          # All Risk Management URL patterns
│   │   │
│   │   └── views/
│   │       ├── risk_champion_views.py           # RiskChampion CRUD + appointment workflow
│   │       ├── risk_assessment_sheet_views.py   # RiskAssessmentSheet CRUD
│   │       ├── dept_risk_register_views.py      # DepartmentalRiskRegister CRUD + workflow
│   │       ├── institutional_risk_register_views.py  # InstitutionalRiskRegister CRUD + workflow
│   │       ├── risk_treatment_plan_views.py     # RiskTreatmentActionPlan CRUD + workflow
│   │       ├── rtap_item_views.py               # RTAPItem CRUD (per-risk control status)
│   │       ├── quarterly_risk_report_views.py   # QuarterlyPerformanceReport CRUD + workflow
│   │       ├── quality_auditor_views.py         # QualityAuditor CRUD + appointment workflow
│   │       ├── qms_audit_program_views.py       # QMSAuditProgram CRUD + workflow
│   │       ├── qms_audit_plan_views.py          # QMSAuditPlan CRUD + workflow
│   │       ├── qms_audit_checklist_views.py     # AuditChecklist CRUD
│   │       ├── qms_audit_report_views.py        # QMSAuditReport CRUD + sign-off action
│   │       ├── non_conformance_views.py         # NonConformance CRUD + closure workflow
│   │       └── risk_dashboard_views.py          # Dashboard aggregate stats
│   │
│   ├── core/
│   │   ├── models/
│   │   │   └── risk_entities.py                 # All Risk Management business models
│   │   │
│   │   ├── services/
│   │   │   ├── risk_champion_service.py         # RiskChampionAppointment workflow service
│   │   │   ├── dept_risk_register_service.py    # DepartmentalRiskRegister workflow service
│   │   │   ├── institutional_risk_register_service.py  # InstitutionalRiskRegister workflow service
│   │   │   ├── rtap_service.py                  # RiskTreatmentActionPlan workflow service
│   │   │   ├── quarterly_risk_report_service.py  # QuarterlyPerformanceReport workflow service
│   │   │   ├── quality_auditor_service.py       # QualityAuditorAppointment workflow service
│   │   │   ├── qms_audit_program_service.py     # QMSAuditProgram workflow service
│   │   │   └── qms_audit_plan_service.py        # QMSAuditPlan workflow service
│   │   │
│   │   ├── tasks/
│   │   │   └── risk_monitoring_deadlines.py     # Celery task: flag overdue RTAP items, send RC reminders
│   │   │
│   │   ├── events/
│   │   │   └── risk_events.py                   # Risk Management domain event dataclasses
│   │   │
│   │   ├── utils/
│   │   │   └── pdf_generators.py                # EXTEND: add generate_appointment_letter_pdf(),
│   │   │                                        #   generate_risk_register_pdf(),
│   │   │                                        #   generate_rtap_pdf(),
│   │   │                                        #   generate_quarterly_report_pdf(),
│   │   │                                        #   generate_audit_report_pdf()
│   │   │
│   │   └── workflows/
│   │       └── workflows.yaml                   # EXTEND: append all 8 risk module workflow templates
│   │
│   └── infrastructure/
│       └── services/
│           └── messaging_service.py             # EXTEND: add publish_risk_*_event() methods
│
├── config/
│   └── permissions/
│       └── grc-service.json                     # EXTEND: add all grc:risk_* permission codes
│
├── shared/
│   └── constants/
│       └── event_types.py                       # EXTEND: add RISK_CHAMPION_EVENTS,
│                                                #   RISK_REGISTER_EVENTS, RTAP_EVENTS,
│                                                #   QMS_AUDIT_EVENTS, QUARTERLY_REPORT_EVENTS
│
└── templates/
    └── grc/
        └── risk/                                # NEW: WeasyPrint HTML templates for Risk module PDFs
            ├── appointment_letter.html          # RC and QA appointment letter PDF template
            ├── institutional_risk_register.html # Institutional Risk Register PDF template
            ├── risk_treatment_action_plan.html  # RTAP PDF template
            ├── quarterly_performance_report.html # Quarterly Performance Report PDF
            └── qms_audit_report.html            # QMS Audit Report PDF template
```

---

### 2.2 Directory and File Explanation

#### `apps/api/serializers/risk_serializers.py`
Contains all DRF serializers for Risk Management entities. Follows the FK dual-field pattern:
`FK = NestedSerializer(read_only=True)` + `FK_id = UUIDField(write_only=True)`.
All user UUID fields (e.g., `risk_owner`, `nominated_by`) are plain `UUIDField`, not FK serializers.
Computed/derived fields (e.g., `inherent_risk_level`, `residual_risk_level`) use `SerializerMethodField` or `read_only=True` with `source=`.

---

#### `apps/api/urls/risk.py`
Declares all URL patterns for the Risk Management module. Mounted under `/api/v1/grc/risk/` via `apps/api/urls/urls.py`.

URL groupings:
- `/risk/champions/` — Risk Champion CRUD + appointment endpoints
- `/risk/assessments/` — Risk Assessment Sheet CRUD
- `/risk/dept-registers/` — Departmental Risk Register CRUD + approval workflow
- `/risk/institutional-registers/` — Institutional Risk Register CRUD + governance workflow
- `/risk/rtap/` — Risk Treatment Action Plan CRUD + approval workflow
- `/risk/rtap-items/` — Per-risk RTAP control item status updates
- `/risk/quarterly-reports/` — Quarterly Performance Report CRUD + submission workflow
- `/risk/quality-auditors/` — Quality Auditor CRUD + appointment workflow
- `/risk/qms-programs/` — QMS Audit Program CRUD + approval workflow
- `/risk/qms-plans/` — QMS Audit Plan CRUD + approval workflow
- `/risk/qms-checklists/` — Audit Checklist CRUD
- `/risk/qms-reports/` — QMS Audit Report CRUD + sign-off
- `/risk/non-conformances/` — Non-Conformance CRUD
- `/risk/dashboard/` — Dashboard stats

Static segment routes are always declared **before** `<uuid:pk>/` routes.

---

#### `apps/api/views/risk_champion_views.py`
CRUD views for `RiskChampion` entity plus appointment workflow actions (`submit/`, `workflow-status/`, `workflow-history/`, `workflow-action/`, `cancel-workflow/`). Enforces `grc:risk_champion:manage` and `grc:risk_champion:view` permission codes.

#### `apps/api/views/risk_assessment_sheet_views.py`
CRUD for `RiskAssessmentSheet`. Inherent and residual risk levels are auto-computed by the model on `save()` from likelihood and impact scores. Read-only computed fields are exposed via serializer. Enforces `grc:risk_assessment:conduct` and `grc:risk_assessment:review`.

#### `apps/api/views/dept_risk_register_views.py`
CRUD + approval workflow for `DepartmentalRiskRegister`. Business rule: register cannot be submitted unless at least one `RiskAssessmentSheet` is linked and approved. Enforces `grc:dept_risk_register:manage` and `grc:dept_risk_register:approve`.

#### `apps/api/views/institutional_risk_register_views.py`
CRUD + multi-stage governance workflow for `InstitutionalRiskRegister`. Business rule: only risks exceeding the institutional risk appetite threshold are included. Enforces `grc:institutional_risk_register:manage` and `grc:institutional_risk_register:approve`.

#### `apps/api/views/risk_treatment_plan_views.py`
CRUD + approval workflow for `RiskTreatmentActionPlan`. The RTAP is always paired 1:1 with an `InstitutionalRiskRegister`. Created automatically when the Institutional Risk Register is created. Enforces `grc:rtap:manage` and `grc:rtap:approve`.

#### `apps/api/views/rtap_item_views.py`
CRUD for `RTAPItem` — the individual per-risk control entries within an RTAP. Handles quarterly status updates (`Not Started` / `In Progress` / `Completed`) submitted by RCs. Enforces `grc:rtap:respond` (for RCs) and `grc:rtap:manage` (for RMQAM/RMO).

#### `apps/api/views/quarterly_risk_report_views.py`
CRUD + governance submission workflow for `QuarterlyPerformanceReport`. Includes comparative analysis views (current vs. previous quarter implementation rates). PDF generation triggered on approval. Enforces `grc:quarterly_risk_report:manage` and `grc:quarterly_risk_report:approve`.

#### `apps/api/views/quality_auditor_views.py`
CRUD + appointment workflow for `QualityAuditor`. Tracks exam score, pass/fail status (threshold: 75%), and ISO training attendance before appointment letter workflow is available. Enforces `grc:quality_auditor:manage`.

#### `apps/api/views/qms_audit_program_views.py`
CRUD + approval workflow for `QMSAuditProgram`. Business rule: an active program may not be replaced until it is archived. Enforces `grc:qms_audit_program:manage` and `grc:qms_audit_program:approve`.

#### `apps/api/views/qms_audit_plan_views.py`
CRUD + approval workflow for `QMSAuditPlan`. Business rule: plan requires an approved `QMSAuditProgram`. Distribution endpoint triggers notification to assigned QAs. Enforces `grc:qms_audit_plan:manage` and `grc:qms_audit_plan:approve`.

#### `apps/api/views/qms_audit_checklist_views.py`
CRUD for `AuditChecklist`. One checklist per QA per process within an engagement. Enforces `grc:qms_checklist:manage`.

#### `apps/api/views/qms_audit_report_views.py`
CRUD + sign-off endpoints for `QMSAuditReport`. Endpoints: `sign-tl/` (Team Leader signature), `sign-auditee/` (Auditee signature). PDF generated and stored in DRS on final sign-off. Enforces `grc:qms_audit_report:manage` and `grc:qms_audit_report:sign`.

#### `apps/api/views/non_conformance_views.py`
CRUD for `NonConformance`. Tracks lifecycle from `raised → acknowledged → in_progress → closed`. Status transitions enforced via view-layer validation. Enforces `grc:non_conformance:manage` and `grc:non_conformance:respond`.

#### `apps/api/views/risk_dashboard_views.py`
Read-only aggregate endpoint providing summary statistics:
- Total active risks by likelihood/impact quadrant
- RTAP implementation rate (current and previous quarter)
- Overdue RTAP items
- Active RC and QA counts per Directorate/Unit/Zone
Enforces `grc:risk_dashboard:view`.

---

#### `apps/core/models/risk_entities.py`
Contains all 20+ Risk Management business model classes. All inherit from `TimestampedModel + StatusMixin`; workflow-enabled entities also inherit `WorkflowMixin`. All `db_table` values use the `grc_risk_*` prefix. Full model list:

| Class | `db_table` | Inherits `WorkflowMixin` |
|---|---|---|
| `RiskChampion` | `grc_risk_champion` | — |
| `RiskChampionAppointment` | `grc_risk_champion_appointment` | ✓ |
| `RiskAssessmentSheet` | `grc_risk_assessment_sheet` | — |
| `DepartmentalRiskRegister` | `grc_risk_dept_register` | ✓ |
| `DeptRegisterEntry` | `grc_risk_dept_register_entry` | — |
| `InstitutionalRiskRegister` | `grc_risk_institutional_register` | ✓ |
| `InstitutionalRiskEntry` | `grc_risk_institutional_entry` | — |
| `RiskTreatmentActionPlan` | `grc_risk_rtap` | ✓ |
| `RTAPItem` | `grc_risk_rtap_item` | — |
| `RTAPQuarterlyUpdate` | `grc_risk_rtap_quarterly_update` | — |
| `QuarterlyPerformanceReport` | `grc_risk_quarterly_report` | ✓ |
| `QualityAuditor` | `grc_risk_quality_auditor` | — |
| `QualityAuditorAppointment` | `grc_risk_qa_appointment` | ✓ |
| `QMSAuditProgram` | `grc_risk_qms_program` | ✓ |
| `QMSAuditPlan` | `grc_risk_qms_plan` | ✓ |
| `QMSAuditTeamAssignment` | `grc_risk_qms_team_assignment` | — |
| `AuditChecklist` | `grc_risk_audit_checklist` | — |
| `QMSAuditReport` | `grc_risk_qms_report` | — |
| `NonConformance` | `grc_risk_non_conformance` | — |
| `ActivityReport` | `grc_risk_activity_report` | — |

---

#### `apps/core/services/` — Risk Service Classes

One service class per workflow-enabled entity. All follow the five-method standard pattern from Internal Audit:
`submit_for_approval`, `get_workflow_status`, `get_workflow_history`, `advance_workflow_stage`, `cancel_workflow_plan`.

| File | Service Class | Template Code |
|---|---|---|
| `risk_champion_service.py` | `RiskChampionAppointmentService` | `grc.risk_champion_appointment` |
| `dept_risk_register_service.py` | `DeptRiskRegisterService` | `grc.dept_risk_register_approval` |
| `institutional_risk_register_service.py` | `InstitutionalRiskRegisterService` | `grc.institutional_risk_register_approval` |
| `rtap_service.py` | `RTAPService` | `grc.rtap_approval` |
| `quarterly_risk_report_service.py` | `QuarterlyRiskReportService` | `grc.quarterly_risk_report_approval` |
| `quality_auditor_service.py` | `QualityAuditorAppointmentService` | `grc.qa_appointment` |
| `qms_audit_program_service.py` | `QMSAuditProgramService` | `grc.qms_audit_program_approval` |
| `qms_audit_plan_service.py` | `QMSAuditPlanService` | `grc.qms_audit_plan_approval` |

---

#### `apps/core/tasks/risk_monitoring_deadlines.py`
Celery periodic task (daily). Responsibilities:
- Flag `RTAPItem` entries past their `target_implementation_date` as overdue.
- Send reminder notifications to RCs when quarterly status submission deadline approaches (3 days before).
- Escalate to RMQAM when an RC has not submitted status updates within 7 days of the reminder.
- Uses `IAMClient.get_user_profile()` for name/email resolution (with safe fallbacks).
- Registered in `CELERY_BEAT_SCHEDULE` under key `grc.check_risk_monitoring_deadlines`.

---

#### `apps/core/events/risk_events.py`
Dataclass definitions for all Risk Management domain events, inheriting `GRCDomainEvent`.
Event types published:
- `grc.risk.champion.appointed`
- `grc.risk.register.departmental.approved`
- `grc.risk.register.institutional.submitted`
- `grc.risk.rtap.updated`
- `grc.risk.quarterly_report.submitted`
- `grc.risk.qa.appointed`
- `grc.qms.audit.nc.raised`

---

#### `apps/core/utils/pdf_generators.py` (extended)
Five new generator functions added to the existing file:

| Function | Output Document |
|---|---|
| `generate_appointment_letter_pdf(appointment)` | RC or QA appointment letter PDF |
| `generate_risk_register_pdf(register)` | Institutional Risk Register PDF |
| `generate_rtap_pdf(rtap)` | Risk Treatment Action Plan PDF |
| `generate_quarterly_report_pdf(report)` | Quarterly Performance Report PDF |
| `generate_qms_audit_report_pdf(audit_report)` | QMS Audit Report PDF |

All use `django.template.loader.render_to_string()` + WeasyPrint. HTML templates are in `templates/grc/risk/`.

---

#### `apps/core/workflows/workflows.yaml` (extended)
Eight new workflow template blocks appended to the existing `templates:` list:

| Template Code | Stages |
|---|---|
| `grc.risk_champion_appointment` | `rmo_draft → rmqam_review → dg_signature` |
| `grc.dept_risk_register_approval` | `rc_submit → rmqam_approve` |
| `grc.institutional_risk_register_approval` | `rmqam_review → management_discussion → committee_review → commission_approval` |
| `grc.rtap_approval` | `rmqam_review → management_discussion → committee_review → commission_approval` |
| `grc.quarterly_risk_report_approval` | `rmqam_prepare → lsm_submit → management_discussion → committee_review → commission_submit` |
| `grc.qa_appointment` | `rmo_draft → rmqam_review → dg_signature` |
| `grc.qms_audit_program_approval` | `rmo_submit → rmqam_approve` |
| `grc.qms_audit_plan_approval` | `rmo_submit → rmqam_approve` |

---

#### `apps/infrastructure/services/messaging_service.py` (extended)
New publish methods added alongside existing `publish_audit_*_event()` methods:
- `publish_risk_champion_event(event_type, champion_id, additional_data)`
- `publish_risk_register_event(event_type, register_id, additional_data)`
- `publish_rtap_event(event_type, rtap_id, additional_data)`
- `publish_quarterly_report_event(event_type, report_id, additional_data)`
- `publish_qms_audit_event(event_type, audit_id, additional_data)`

---

#### `config/permissions/grc-service.json` (extended)
New permission codes added to the existing JSON catalog:

```
grc:risk_champion:view
grc:risk_champion:manage

grc:risk_assessment:conduct
grc:risk_assessment:review

grc:dept_risk_register:manage
grc:dept_risk_register:approve

grc:institutional_risk_register:manage
grc:institutional_risk_register:approve

grc:rtap:manage
grc:rtap:approve
grc:rtap:respond

grc:quarterly_risk_report:manage
grc:quarterly_risk_report:approve

grc:quality_auditor:manage

grc:qms_audit_program:manage
grc:qms_audit_program:approve

grc:qms_audit_plan:manage
grc:qms_audit_plan:approve

grc:qms_checklist:manage

grc:qms_audit_report:manage
grc:qms_audit_report:sign

grc:non_conformance:manage
grc:non_conformance:respond

grc:risk_dashboard:view
```

---

#### `shared/constants/event_types.py` (extended)
New event type constant dictionaries added:

```python
RISK_CHAMPION_EVENTS = {
    'APPOINTED': 'grc.risk.champion.appointed',
}

RISK_REGISTER_EVENTS = {
    'DEPARTMENTAL_APPROVED': 'grc.risk.register.departmental.approved',
    'INSTITUTIONAL_SUBMITTED': 'grc.risk.register.institutional.submitted',
}

RTAP_EVENTS = {
    'APPROVED': 'grc.risk.rtap.approved',
    'UPDATED': 'grc.risk.rtap.updated',
}

QUARTERLY_RISK_REPORT_EVENTS = {
    'SUBMITTED': 'grc.risk.quarterly_report.submitted',
}

QMS_AUDIT_EVENTS = {
    'NC_RAISED': 'grc.qms.audit.nc.raised',
    'REPORT_SIGNED': 'grc.qms.audit.report.signed',
}
```

---

#### `templates/grc/risk/` — PDF HTML Templates

| File | Document |
|---|---|
| `appointment_letter.html` | Formal appointment letter for Risk Champions and Quality Auditors. Includes nominee name, role, directorate/unit, effective period, and DG signature block. |
| `institutional_risk_register.html` | Tabular PDF of all institutional-level risks. Columns: risk description, category, likelihood, impact, inherent level, controls, residual level, owner. |
| `risk_treatment_action_plan.html` | Per-risk control table. Columns: risk ID, control description, responsible officer, target date, implementation status. |
| `quarterly_performance_report.html` | Consolidated quarterly update with implementation rate table, comparative bar data narrative, and RMQA plan progress section. |
| `qms_audit_report.html` | Formal QMS audit report layout. Includes engagement details, NC table (with ISO clause references), areas for improvement, TL signature block, and auditee acknowledgment block. |

---

### Reuse of Internal Audit Patterns

The following components are shared with the Internal Audit module without modification:

| Component | Location | Reused For |
|---|---|---|
| `BaseModel`, `TimestampedModel`, `StatusMixin`, `WorkflowMixin` | `apps/core/models/base.py` | All Risk Management models |
| `FiscalYear`, `Quarter` lookup models | `apps/core/models/lookups.py` | Period anchoring for RTAP items, quarterly reports |
| `Directorate`, `Department`, `Unit`, `Section` org models | `apps/core/models/organizational.py` | Org unit references on all risk-side entities |
| `OrchestrationClient` | `apps/infrastructure/external/orchestration_client.py` | All 8 workflow service classes |
| `DocumentServiceClient` | `apps/infrastructure/external/document_service_client.py` | PDF upload for appointment letters, registers, reports |
| `IAMClient` | `apps/infrastructure/external/iam_client.py` | User profile resolution in Celery tasks and notifications |
| `NotificationPublisher` | `apps/core/notifications/publisher.py` | All risk module notifications |
| `paginate_queryset`, `get_ordering_param` | `apps/api/utils/pagination.py` | All list endpoints |
| Response helper functions | `apps/api/utils/response_helpers.py` | All view responses |
| `GRCKafkaConsumer` | `apps/infrastructure/messaging/kafka_consumer.py` | No change needed — org sync already handled |
| `JWTPermissionMiddleware` | `apps/core/permission_middleware.py` | No change needed |
| `_check_grc_permission_locally()` | `apps/api/permissions_jwt.py` | Base for all new named permission classes |
