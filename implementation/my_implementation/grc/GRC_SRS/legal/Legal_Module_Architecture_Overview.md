# Legal Module — Architecture Overview & Directory Structure
**Service:** `grc-service`
**Module:** Legal
**Phase:** 4 — Architecture Overview & Directory Structure
**Stack:** Django 4.x · DRF · PostgreSQL · Celery · Kafka
**Pattern Reference:** Internal Audit implementation (`GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md`)

---

## Table of Contents

1. [Module Purpose & Scope](#1-module-purpose--scope)
2. [Architecture Overview](#2-architecture-overview)
   - 2.1 Integration with IAM Service
   - 2.2 Integration with Work Orchestration Service
   - 2.3 Integration with Document Records Service
   - 2.4 Integration with Kafka
   - 2.5 Integration with Corporate Service
3. [Module Boundaries](#3-module-boundaries)
4. [Reuse of Internal Audit Patterns](#4-reuse-of-internal-audit-patterns)
5. [Full Directory Structure](#5-full-directory-structure)
6. [File-by-File Purpose Reference](#6-file-by-file-purpose-reference)

---

## 1. Module Purpose & Scope

The Legal module manages all formal legal activities of the Fair Competition Commission (FCC), across six functional areas:

| Sub-domain | Core Responsibility |
|---|---|
| **Governance Structure** | Committee types, governing bodies, member management |
| **Determinations & Approvals** | Formal submission pipeline for governing body decisions |
| **Meeting Governance** | Full meeting lifecycle, agendas, participants, directives, minutes, resolutions |
| **Public Register** | Official publication of commission decisions |
| **Litigation — FCC Sued** | Cases where FCC has been sued; DG review, filings, judgments, appeals |
| **Litigation — FCC Suing** | Cases where FCC initiates action; breach reports, filings, judgments, appeals |

All six sub-domains are implemented as a single cohesive module inside `apps/core/models/legal_entities.py`, with shared base classes, services, and infrastructure. The boundary of what grc-service **owns** vs what it **delegates** is defined in §3.

---

## 2. Architecture Overview

### 2.1 Integration with IAM Service

**What IAM owns, what Legal consumes:**

| IAM Capability | Legal Usage | Integration Mode |
|---|---|---|
| JWT issuance and validation | All requests authenticated via shared `JWT_SECRET_KEY` | Local JWT decode — no runtime IAM call |
| `permissions_flat` in JWT payload | Legal permission codes carried in token (`grc:legal:*`) | Read from `request.grc_permissions` (set by `JWTPermissionMiddleware`) |
| User profiles (name, email) | Rendered in API responses; embedded in digital signature metadata | REST → `GET /api/v1/iam/users/<user_id>/` via `IAMClient`, Redis-cached 5 min |
| Permission aggregation (IAM stores all service permissions) | Legal permissions published on startup and picked up by IAM | Kafka → `service.permission.registry` |

**Reuse pattern:** Identical to Internal Audit. The existing `IAMJWTAuthentication`, `JWTPermissionMiddleware`, and `IAMClient` are shared — no new auth infrastructure is needed. Legal module only adds its permission codes to `config/permissions/grc-service.json`.

---

### 2.2 Integration with Work Orchestration Service

**What Work Orchestration owns, what Legal delegates:**

| WO Capability | Legal Usage | Mode |
|---|---|---|
| Multi-stage workflow plans | Filing approval (6-state), Minutes approval, Submission determination workflow | REST via `OrchestrationClient` (`POST /api/v1/workflow/plans/`) |
| Stage progression | Legal Officer/Manager/DG approve filings; Secretary approves minutes | REST via `OrchestrationClient` (`advance_stage`) |
| Task reminders | `TaskLitigation` and `MeetingDirective` due-date reminders (7d/2d/1d before) | REST → `POST /api/v1/workflow/reminders/` at task creation time |
| Reminder cancellation | When task/directive closed before due date | REST → `DELETE /api/v1/workflow/reminders/<id>/` |
| Notification template storage/rendering | Legal notification templates registered via Kafka | Kafka → `notification-templates` |
| Notification delivery (email, in-app) | All Legal module event notifications | Kafka → priority topics (`notifications-urgent/high/normal/low`) |

**Workflow entities in Legal module:**

| Entity | Workflow Template Code | Stages |
|---|---|---|
| `FilingDefendant` / `FilingPlaintiff` | `grc.legal_filing_approval` | `legal_manager_review → dg_approval` (2 stages) |
| `Minutes` | `grc.legal_minutes_approval` | `member_approval` (1 stage — multi-signoff) |
| `SettlementDefendant` / `SettlementPlaintiff` | `grc.legal_settlement_approval` | `legal_manager_review → dg_approval` (2 stages) |
| `JudgmentDefendant` / `JudgmentPlaintiff` | `grc.legal_judgment_decision` | `legal_manager_review → dg_decision` (2 stages) |
| `CaseDefendant` / `CasePlaintiff` (closure) | `grc.legal_case_closure` | `legal_manager_initiate → dg_approval` (2 stages) |

**Ownership boundary:** Work Orchestration delivers notifications and tracks stage progression. grc-service owns all domain state transitions (status fields), business rules, and the meaning of approval outcomes. This is identical to the Internal Audit pattern.

---

### 2.3 Integration with Document Records Service

**What Document Records Service owns, what Legal delegates:**

| DRS Capability | Legal Usage | Mode |
|---|---|---|
| File upload and storage | All document attachments in Legal forms | REST → `POST /api/v1/documents/` via `DocumentServiceClient`; returns `document_id` UUID |
| Document metadata retrieval | Preview filenames, classification, upload date | REST → `GET /api/v1/documents/<id>/` |
| Download URL generation | User clicks download on a filing, minutes attachment, etc. | REST → `GET /api/v1/documents/<id>/download/` |
| Document versioning, retention, disposal | Transparent — DRS handles according to configured document type | DRS-internal |

**What grc-service stores (never the file itself):**

| Entity | `document_id` field(s) |
|---|---|
| `SubmissionForDetermination` | `supporting_documents[]` (JSONField of UUIDs) |
| `MeetingAgenda` | `documents[]` (JSONField of UUIDs) |
| `MeetingDirective` | `evidence_document_id` (UUIDField, nullable) |
| `LitigationDirective` | `attachments[]` (JSONField of UUIDs) |
| `Minutes` | `attachments[]` (JSONField of UUIDs) |
| `FilingDefendant` / `FilingPlaintiff` | `document_id` (UUIDField) |
| `ResponseDefendant` / `ResponsePlaintiff` | `document_id` (UUIDField) |
| `HearingReport` | `attachment_id` (UUIDField, nullable) |
| `SettlementDefendant` / `SettlementPlaintiff` | `agreement_document_id` (UUIDField) |
| `JudgmentDefendant` / `JudgmentPlaintiff` | `document_id` (UUIDField) |
| `CaseDefendant` / `CasePlaintiff` | `initiation_documents[]` (JSONField of UUIDs) |

**Reuse pattern:** Identical to the `WorkingPaper.document_id` pattern in Internal Audit. The existing `DocumentServiceClient` is shared — Legal views call it directly.

---

### 2.4 Integration with Kafka

Legal module participates in three Kafka directions:

#### A) Published by grc-service (Legal produces)

| Topic | Message | When |
|---|---|---|
| `service.permission.registry` | Legal permission definitions | Service startup |
| `notification-templates` | Legal notification template definitions | Service startup |
| `notifications-urgent` | DG review required, appeal deadline imminent | Case registered, `TaskLitigation` appeal deadline |
| `notifications-high` | Filing approval request, judgment recorded, settlement approval, DG directive issued | Each respective action |
| `notifications-normal` | Meeting invitation, directive assigned, minutes pending approval, task assigned | Each respective action |
| `notifications-low` | Quorum update, meeting status changes, case stage transitions | Automatic transitions |
| `grc.legal.events` | Domain events (case registered, meeting closed, decision published) | Post-save, outside `transaction.atomic()` |

#### B) Consumed by grc-service (Legal consumes)

| Topic | Produced By | Legal Action |
|---|---|---|
| `corporate.events` | Corporate Service | Update local `Member` snapshot on `employee.deactivated` / `employee.profile.updated` |
| `fims.documents.events` | Document Records Service | Handle `document.deleted` / `document.archived` — null/flag affected `document_id` fields |
| `fims.iam.user.updated` | IAM Service | Invalidate cached user profile data used in audit display |
| `workflow-events` | Work Orchestration Service | Update filing/settlement/minutes/closure status from WO stage outcomes |

#### C) New Topic (`grc.legal.events`)

Legal module introduces one new Kafka topic:

| Event Type | Trigger |
|---|---|
| `legal.case.defendant.registered` | `CaseDefendant` created |
| `legal.case.plaintiff.registered` | `CasePlaintiff` created |
| `legal.case.closed` | Case closure DG-approved |
| `legal.meeting.closed` | `Meeting` status → CLOSED |
| `legal.public_decision.published` | `PublicDecision` status → PUBLISHED |
| `legal.directive.fully_closed` | `MeetingDirective.fully_closed = True` |
| `legal.filing.filed` | `FilingDefendant` / `FilingPlaintiff` status → FILED |

**Reuse pattern:** The existing `GrcServiceKafkaProducer` (lazy Kafka producer), `NotificationPublisher`, `GRCKafkaConsumer`, and `KafkaMessagingService` are all shared. Legal module adds event type constants to `shared/constants/event_types.py` and adds its handlers to the Kafka consumer routing table.

---

### 2.5 Integration with Corporate Service

**What Corporate Service owns, what Legal delegates:**

| Corporate Capability | Legal Usage | Mode |
|---|---|---|
| Canonical staff/employee records | Populate member selectors in governing body management | REST → `GET /api/v1/corporate/hr/employees/` (Redis-cached 5 min) |
| Department structure | Breach Report Intake `department` field dropdown | REST → `GET /api/v1/corporate/hr/departments/` (Redis-cached 10 min) |
| Employee update events | Sync local `Member` snapshot when staff profile changes or user is deactivated | Kafka → `corporate.events` consumer |

**Local member snapshot:** grc-service stores a lightweight `Member` snapshot per governing body (fields: `UserID`, `BodyID`, `Position`, `MemberType`, `Status`, `JoinedDate`). The snapshot is created from Corporate Service data at member assignment time and kept in sync via the `corporate.events` Kafka consumer.

**Reuse pattern:** Identical to how `Directorate`, `Department`, `Unit` are synced from Corporate Service for Internal Audit. The existing `OrganizationalSyncService` and `GRCKafkaConsumer` are extended — not duplicated.

---

## 3. Module Boundaries

### What grc-service owns (Legal module)

```
CommitteeType               GoverningBody               Member (snapshot)
SubmissionForDetermination
Meeting                     MeetingAgenda               MeetingParticipant
MeetingDirective            Minutes                     Resolution
ConflictDeclaration
CaseDefendant               CasePlaintiff
LitigationDirective
FilingDefendant             FilingPlaintiff
ResponseDefendant           ResponsePlaintiff
Hearing                     HearingReport
SettlementDefendant         SettlementPlaintiff
JudgmentDefendant           JudgmentPlaintiff
FinancialDefendant          FinancialPlaintiff
TaskLitigation
PublicDecision
LegalAuditLog               (domain-scoped, immutable)
```

### What grc-service does NOT own (delegates)

| Concern | Owner |
|---|---|
| User authentication, JWT issuance | IAM Service |
| User profile data (names, emails, dept) | IAM Service (REST + cache) |
| RBAC permission aggregation | IAM Service (Kafka `service.permission.registry`) |
| System-level audit (logins, role changes) | IAM Service |
| File storage, document metadata, versioning | Document Records Service (REST) |
| Notification delivery (email, in-app) | Work Orchestration Service (Kafka) |
| Notification template storage/rendering | Work Orchestration Service (Kafka) |
| Task reminder scheduling and delivery | Work Orchestration Service (REST + Kafka) |
| Canonical staff/employee records | Corporate Service (REST + Kafka `corporate.events`) |

---

## 4. Reuse of Internal Audit Patterns

The Legal module is a new module inside the **same** `grc-service` application. It shares all existing infrastructure and adds only Legal-specific files. The following existing files are reused without modification:

| Existing File | How Legal Module Reuses It |
|---|---|
| `apps/api/authentication.py` | All Legal views use `IAMJWTAuthentication` + `ServiceAuthentication` |
| `apps/api/permissions_jwt.py` | Legal permission classes are **added** to this file |
| `apps/api/exceptions.py` | Custom exception handler applies to all modules |
| `apps/api/utils/pagination.py` | All Legal list views call `paginate_queryset()` + `get_ordering_param()` |
| `apps/api/utils/response_helpers.py` | All Legal views use these response envelope helpers |
| `apps/core/models/base.py` | All Legal models inherit from `TimestampedModel`, `StatusMixin`, `WorkflowMixin` |
| `apps/core/models/lookups.py` | Legal lookup models (e.g., `CourtLevel`, `UrgencyLevel`) are **added** here |
| `apps/core/notifications/publisher.py` | Legal views call `NotificationPublisher.send_notification()` |
| `apps/core/kafka_producer.py` | Legal event publisher uses this shared producer |
| `apps/core/kafka_permission_publisher.py` | Permission publication runs for all codes including Legal on startup |
| `apps/core/permission_middleware.py` | Middleware reads Legal `grc:legal:*` codes from JWT |
| `apps/core/permissions.py` | Loads the single `grc-service.json` (Legal codes added there) |
| `apps/core/workflow_entity_paths.py` | Legal entity paths are **added** to the mapping dict |
| `apps/core/workflows/workflows.yaml` | Legal workflow templates are **added** as new entries |
| `apps/core/templates/notifications.yaml` | Legal notification templates are **added** as new entries |
| `apps/infrastructure/external/orchestration_client.py` | Legal services call `OrchestrationClient` |
| `apps/infrastructure/external/iam_client.py` | Legal views call `IAMClient.get_user_profile()` |
| `apps/infrastructure/external/document_service_client.py` | Legal views call `DocumentServiceClient` |
| `apps/infrastructure/messaging/kafka_consumer.py` | Legal event handlers **added** to consumer routing |
| `apps/infrastructure/services/messaging_service.py` | Legal event publishing methods **added** here |
| `config/permissions/grc-service.json` | Legal permission codes **added** to this file |
| `shared/constants/event_types.py` | `LEGAL_*_EVENTS` constants **added** here |

**Files that are new additions (Legal-specific):**
- `apps/core/models/legal_entities.py`
- `apps/core/events/legal_events.py`
- `apps/core/services/legal_*.py` (one per workflow entity)
- `apps/core/tasks/legal_*.py` (Legal-specific Celery tasks)
- `apps/api/serializers/legal_serializers.py`
- `apps/api/views/legal_*.py` (one per entity group)
- `apps/api/urls/legal.py`

---

## 5. Full Directory Structure

The tree below shows **all files that will exist** for the Legal module. Files marked `[EXISTING]` already exist in the codebase and will be **modified** (not replaced). Files marked `[NEW]` are created fresh. Migration files are generated by Django — listed as placeholders.

```
grc-service/
│
├── apps/
│   │
│   ├── api/                                        [EXISTING layer — extended]
│   │   │
│   │   ├── authentication.py                       [EXISTING] — shared; no changes
│   │   ├── exceptions.py                           [EXISTING] — shared; no changes
│   │   ├── permissions_jwt.py                      [EXISTING — MODIFIED]
│   │   │                                             Legal permission classes added:
│   │   │                                             CanViewGovernanceStructure
│   │   │                                             CanManageGovernanceStructure
│   │   │                                             CanManageMeeting
│   │   │                                             CanViewMeeting
│   │   │                                             CanManageSubmission
│   │   │                                             CanViewSubmission
│   │   │                                             CanManageLitigation
│   │   │                                             CanViewLitigation
│   │   │                                             CanApproveLegalFiling
│   │   │                                             CanManagePublicRegister
│   │   │                                             CanViewLegalDashboard
│   │   │
│   │   ├── serializers/
│   │   │   ├── audit_serializers.py                [EXISTING] — unchanged
│   │   │   ├── lookup_serializers.py               [EXISTING — MODIFIED]
│   │   │   │                                         Legal lookup serializers added:
│   │   │   │                                         CourtLevelSerializer
│   │   │   │                                         UrgencyLevelSerializer
│   │   │   │                                         RiskLevelSerializer
│   │   │   │                                         MeetingTypeSerializer
│   │   │   └── legal_serializers.py                [NEW]
│   │   │                                             All Legal entity serializers:
│   │   │                                             CommitteeTypeSerializer
│   │   │                                             GoverningBodySerializer
│   │   │                                             MemberSerializer
│   │   │                                             SubmissionForDeterminationSerializer
│   │   │                                             MeetingSerializer
│   │   │                                             MeetingAgendaSerializer
│   │   │                                             MeetingParticipantSerializer
│   │   │                                             MeetingDirectiveSerializer
│   │   │                                             MinutesSerializer
│   │   │                                             ResolutionSerializer
│   │   │                                             CaseDefendantSerializer
│   │   │                                             CasePlaintiffSerializer
│   │   │                                             LitigationDirectiveSerializer
│   │   │                                             FilingDefendantSerializer + FilingPlaintiffSerializer
│   │   │                                             ResponseDefendantSerializer + ResponsePlaintiffSerializer
│   │   │                                             HearingSerializer + HearingReportSerializer
│   │   │                                             SettlementDefendantSerializer + SettlementPlaintiffSerializer
│   │   │                                             JudgmentDefendantSerializer + JudgmentPlaintiffSerializer
│   │   │                                             FinancialDefendantSerializer + FinancialPlaintiffSerializer
│   │   │                                             TaskLitigationSerializer
│   │   │                                             PublicDecisionSerializer
│   │   │
│   │   ├── urls/
│   │   │   ├── urls.py                             [EXISTING — MODIFIED]
│   │   │   │                                         Mounts legal.py:
│   │   │   │                                         path('legal/', include('apps.api.urls.legal'))
│   │   │   ├── audit.py                            [EXISTING] — unchanged
│   │   │   └── legal.py                            [NEW]
│   │   │                                             All Legal URL patterns organized by sub-domain:
│   │   │                                             — Governance Structure: /legal/committee-types/, /legal/governing-bodies/, /legal/members/
│   │   │                                             — Submissions: /legal/submissions/
│   │   │                                             — Meetings: /legal/meetings/, /legal/agenda/, /legal/participants/,
│   │   │                                               /legal/directives/, /legal/minutes/, /legal/resolutions/
│   │   │                                             — Litigation Defendant: /legal/cases/defendant/
│   │   │                                             — Litigation Plaintiff: /legal/cases/plaintiff/
│   │   │                                             — Shared litigation sub-entities: /legal/filings/, /legal/responses/,
│   │   │                                               /legal/hearings/, /legal/settlements/, /legal/judgments/,
│   │   │                                               /legal/financials/, /legal/litigation-directives/, /legal/tasks/
│   │   │                                             — Public Register: /legal/public-register/
│   │   │                                             — Dashboard: /legal/dashboard/stats/
│   │   │
│   │   └── views/
│   │       ├── [existing audit views unchanged]
│   │       │
│   │       ├── legal_dashboard_views.py            [NEW]
│   │       │   # Aggregate KPIs across all Legal sub-domains
│   │       │   # LegalDashboardStatsView
│   │       │
│   │       ├── legal_governance_views.py           [NEW]
│   │       │   # CommitteeType CRUD
│   │       │   # GoverningBody CRUD
│   │       │   # Member CRUD + sync trigger
│   │       │
│   │       ├── legal_submission_views.py           [NEW]
│   │       │   # SubmissionForDetermination List/Create/Detail/Update
│   │       │   # Withdraw action endpoint
│   │       │
│   │       ├── legal_meeting_views.py              [NEW]
│   │       │   # Meeting CRUD + lifecycle actions:
│   │       │   #   POST /meetings/<pk>/register/
│   │       │   #   POST /meetings/<pk>/share-agenda/
│   │       │   #   POST /meetings/<pk>/start/      (ONGOING)
│   │       │   #   POST /meetings/<pk>/postpone/
│   │       │   #   POST /meetings/<pk>/close/
│   │       │   #   POST /meetings/<pk>/cancel/
│   │       │   #   GET  /meetings/<pk>/quorum/
│   │       │
│   │       ├── legal_agenda_views.py               [NEW]
│   │       │   # MeetingAgenda CRUD
│   │       │   # ConflictDeclaration create/list per agenda item
│   │       │
│   │       ├── legal_participant_views.py          [NEW]
│   │       │   # MeetingParticipant list per meeting
│   │       │   # RSVP action: POST /participants/<pk>/respond/
│   │       │
│   │       ├── legal_directive_views.py            [NEW]
│   │       │   # MeetingDirective CRUD + workflow actions:
│   │       │   #   POST /directives/<pk>/close/          (assignee initial closure)
│   │       │   #   POST /directives/<pk>/finally-close/  (Secretary final closure)
│   │       │   # Matters Arising list: GET /directives/matters-arising/?body=<id>
│   │       │
│   │       ├── legal_minutes_views.py              [NEW]
│   │       │   # Minutes CRUD + workflow actions:
│   │       │   #   POST /minutes/<pk>/submit/       (Secretary submits for approval)
│   │       │   # Workflow: submit, workflow-status, workflow-history, workflow-action, cancel-workflow
│   │       │
│   │       ├── legal_resolution_views.py           [NEW]
│   │       │   # Resolution list (read-only for meeting participants)
│   │       │   # Resolution detail
│   │       │
│   │       ├── legal_case_defendant_views.py       [NEW]
│   │       │   # CaseDefendant CRUD
│   │       │   # DG review actions:
│   │       │   #   POST /cases/defendant/<pk>/dg-review/
│   │       │   # Case closure: POST /cases/defendant/<pk>/initiate-closure/
│   │       │   # Workflow: closure workflow endpoints
│   │       │
│   │       ├── legal_case_plaintiff_views.py       [NEW]
│   │       │   # CasePlaintiff CRUD (two registration entry points)
│   │       │   # Same DG review + closure actions as defendant
│   │       │
│   │       ├── legal_filing_views.py               [NEW]
│   │       │   # FilingDefendant + FilingPlaintiff (discriminated by query param or separate URLs)
│   │       │   # Workflow: submit, workflow-status, workflow-history, workflow-action, cancel-workflow
│   │       │   # POST /filings/<pk>/mark-as-filed/  (after DG approval)
│   │       │
│   │       ├── legal_response_views.py             [NEW]
│   │       │   # ResponseDefendant + ResponsePlaintiff CRUD
│   │       │
│   │       ├── legal_hearing_views.py              [NEW]
│   │       │   # Hearing CRUD per case
│   │       │   # HearingReport CRUD per hearing
│   │       │
│   │       ├── legal_settlement_views.py           [NEW]
│   │       │   # SettlementDefendant + SettlementPlaintiff CRUD
│   │       │   # Workflow: submit, workflow-status, workflow-history, workflow-action, cancel-workflow
│   │       │
│   │       ├── legal_judgment_views.py             [NEW]
│   │       │   # JudgmentDefendant + JudgmentPlaintiff CRUD
│   │       │   # DG decision action: POST /judgments/<pk>/dg-decision/
│   │       │   #   Triggers auto-create FilingDefendant(Notice of Appeal) + TaskLitigation
│   │       │
│   │       ├── legal_financial_views.py            [NEW]
│   │       │   # FinancialDefendant + FinancialPlaintiff CRUD (1:1 per case, auto-created)
│   │       │   # POST /financials/<pk>/record-recovery/
│   │       │   # POST /financials/<pk>/record-payment/
│   │       │
│   │       ├── legal_task_views.py                 [NEW]
│   │       │   # TaskLitigation CRUD per case
│   │       │   # POST /tasks/<pk>/close/
│   │       │   # GET  /tasks/overdue/
│   │       │
│   │       ├── legal_litigation_directive_views.py [NEW]
│   │       │   # LitigationDirective CRUD (DG directives on cases)
│   │       │   # POST /litigation-directives/<pk>/close/
│   │       │
│   │       └── legal_public_register_views.py      [NEW]
│   │           # PublicDecision CRUD
│   │           # POST /public-register/<pk>/publish/  (Secretariat only)
│   │
│   ├── core/                                       [EXISTING layer — extended]
│   │   │
│   │   ├── models/
│   │   │   ├── base.py                             [EXISTING] — shared; no changes
│   │   │   │                                         BaseModel, TimestampedModel, StatusMixin, WorkflowMixin
│   │   │   ├── lookups.py                          [EXISTING — MODIFIED]
│   │   │   │                                         Legal lookup models added:
│   │   │   │                                         CourtLevel (High Court, Court of Appeal, etc.)
│   │   │   │                                         UrgencyLevel (Critical, High, Normal, Low)
│   │   │   │                                         RiskLevel (High Risk, Medium, Low)
│   │   │   │                                         MeetingMode (Physical, Virtual, Hybrid)
│   │   │   │                                         MeetingType (Ordinary, Extraordinary, Special)
│   │   │   │                                         DirectivePriority (Critical, High, Medium, Low)
│   │   │   │                                         DirectiveCategory (free-text lookup)
│   │   │   └── legal_entities.py                  [NEW]
│   │   │                                             All Legal domain models (~22 entities):
│   │   │                                             — Governance: CommitteeType, GoverningBody, Member
│   │   │                                             — Submission: SubmissionForDetermination
│   │   │                                             — Meeting: Meeting, MeetingAgenda, ConflictDeclaration,
│   │   │                                               MeetingParticipant, MeetingDirective, Minutes, Resolution
│   │   │                                             — Litigation common: Hearing, HearingReport, TaskLitigation
│   │   │                                             — Litigation FCC Sued: CaseDefendant, LitigationDirective,
│   │   │                                               FilingDefendant, ResponseDefendant, SettlementDefendant,
│   │   │                                               JudgmentDefendant, FinancialDefendant
│   │   │                                             — Litigation FCC Suing: CasePlaintiff, FilingPlaintiff,
│   │   │                                               ResponsePlaintiff, SettlementPlaintiff, JudgmentPlaintiff,
│   │   │                                               FinancialPlaintiff
│   │   │                                             — Public Register: PublicDecision
│   │   │                                             — Cross-cutting: LegalAuditLog
│   │   │
│   │   ├── migrations/
│   │   │   └── 0021_legal_module_initial.py        [NEW — auto-generated]
│   │   │       └── (subsequent migrations as Legal schema evolves)
│   │   │
│   │   ├── services/
│   │   │   ├── [existing audit services unchanged]
│   │   │   │
│   │   │   ├── legal_filing_service.py             [NEW]
│   │   │   │   # FilingService — workflow for FilingDefendant + FilingPlaintiff
│   │   │   │   # WORKFLOW_TEMPLATE_CODE = "grc.legal_filing_approval"
│   │   │   │   # submit_for_approval(), advance_workflow_stage(), get_workflow_status()
│   │   │   │   # get_workflow_history(), cancel_workflow_plan()
│   │   │   │
│   │   │   ├── legal_minutes_service.py            [NEW]
│   │   │   │   # MinutesService — workflow for Minutes approval
│   │   │   │   # WORKFLOW_TEMPLATE_CODE = "grc.legal_minutes_approval"
│   │   │   │
│   │   │   ├── legal_settlement_service.py         [NEW]
│   │   │   │   # SettlementService — workflow for SettlementDefendant + SettlementPlaintiff
│   │   │   │   # WORKFLOW_TEMPLATE_CODE = "grc.legal_settlement_approval"
│   │   │   │
│   │   │   ├── legal_judgment_service.py           [NEW]
│   │   │   │   # JudgmentService — workflow for JudgmentDefendant + JudgmentPlaintiff
│   │   │   │   # WORKFLOW_TEMPLATE_CODE = "grc.legal_judgment_decision"
│   │   │   │   # Also handles auto-create of Notice of Appeal filing + TaskLitigation on DG appeal decision
│   │   │   │
│   │   │   └── legal_case_closure_service.py       [NEW]
│   │   │       # CaseClosureService — workflow for case closure (Defendant + Plaintiff)
│   │   │       # WORKFLOW_TEMPLATE_CODE = "grc.legal_case_closure"
│   │   │
│   │   ├── tasks/
│   │   │   ├── [existing audit tasks unchanged]
│   │   │   │
│   │   │   ├── legal_task_deadlines.py             [NEW]
│   │   │   │   # Celery Beat task: detect overdue TaskLitigation records
│   │   │   │   # Runs daily; transitions status → OVERDUE; sends notification
│   │   │   │   # Also handles 7-day/2-day/1-day pre-due reminders for tasks
│   │   │   │
│   │   │   ├── legal_directive_deadlines.py        [NEW]
│   │   │   │   # Celery Beat task: detect overdue MeetingDirective and LitigationDirective records
│   │   │   │   # Runs daily; transitions status → OVERDUE; sends notification
│   │   │   │
│   │   │   └── legal_meeting_quorum.py             [NEW]
│   │   │       # Celery Beat task (or on-demand): recalculate quorum for REGISTERED meetings
│   │   │       # Runs every 15 min or triggered after RSVP update
│   │   │
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── seed_lookup_data.py             [EXISTING — MODIFIED]
│   │   │       │   # Legal lookup seeding added: CourtLevel, UrgencyLevel, RiskLevel,
│   │   │       │   # MeetingMode, MeetingType, DirectivePriority, DirectiveCategory
│   │   │       │
│   │   │       └── register_workflow_templates.py  [EXISTING — MODIFIED]
│   │   │           # Legal workflow templates verified/registered:
│   │   │           # grc.legal_filing_approval, grc.legal_minutes_approval,
│   │   │           # grc.legal_settlement_approval, grc.legal_judgment_decision,
│   │   │           # grc.legal_case_closure
│   │   │
│   │   ├── events/
│   │   │   ├── audit_events.py                     [EXISTING] — unchanged
│   │   │   └── legal_events.py                     [NEW]
│   │   │       # Legal domain event dataclasses (inherit GRCDomainEvent):
│   │   │       # CaseDefendantRegisteredEvent    ('legal.case.defendant.registered')
│   │   │       # CasePlaintiffRegisteredEvent    ('legal.case.plaintiff.registered')
│   │   │       # CaseClosedEvent                 ('legal.case.closed')
│   │   │       # MeetingClosedEvent              ('legal.meeting.closed')
│   │   │       # PublicDecisionPublishedEvent    ('legal.public_decision.published')
│   │   │       # DirectiveFinallyClosedEvent     ('legal.directive.fully_closed')
│   │   │       # FilingFiledEvent                ('legal.filing.filed')
│   │   │
│   │   ├── workflows/
│   │   │   ├── workflows.yaml                      [EXISTING — MODIFIED]
│   │   │   │   # Legal workflow templates appended:
│   │   │   │   # - grc.legal_filing_approval      (2 stages: lm_review → dg_approval)
│   │   │   │   # - grc.legal_minutes_approval     (1 stage: member_approval multi-signoff)
│   │   │   │   # - grc.legal_settlement_approval  (2 stages: lm_review → dg_approval)
│   │   │   │   # - grc.legal_judgment_decision    (2 stages: lm_review → dg_decision)
│   │   │   │   # - grc.legal_case_closure         (2 stages: lm_initiate → dg_approval)
│   │   │   └── registry.py                         [EXISTING] — no changes needed
│   │   │
│   │   ├── templates/
│   │   │   ├── notifications.yaml                  [EXISTING — MODIFIED]
│   │   │   │   # Legal notification templates appended (subject + body per event):
│   │   │   │   # legal.case.registered            — DG: "New case registered for review"
│   │   │   │   # legal.filing.approval.request    — Legal Manager: "Filing requires your review"
│   │   │   │   # legal.filing.approved            — Legal Officer: "Your filing has been approved"
│   │   │   │   # legal.meeting.invitation         — Member: "You have been invited to a meeting"
│   │   │   │   # legal.meeting.quorum.update      — Secretary: "Quorum status has changed"
│   │   │   │   # legal.directive.assigned         — Assignee: "A directive has been assigned to you"
│   │   │   │   # legal.directive.overdue          — Assignee + Secretary: "Directive is overdue"
│   │   │   │   # legal.minutes.pending.approval   — Participants: "Meeting minutes require your approval"
│   │   │   │   # legal.task.assigned              — Assignee: "A case task has been assigned to you"
│   │   │   │   # legal.task.overdue               — Assignee + Manager: "Case task is overdue"
│   │   │   │   # legal.task.appeal.deadline       — Legal Officer + Manager: "Appeal filing deadline approaching"
│   │   │   │   # legal.settlement.dg.approval     — DG: "Settlement requires your approval"
│   │   │   │   # legal.judgment.dg.decision       — DG: "Judgment requires your decision"
│   │   │   │   # legal.dg.directive.issued        — Legal Officer + Manager: "DG directive issued on case"
│   │   │   └── registry.py                         [EXISTING] — no changes needed
│   │   │
│   │   ├── notifications/
│   │   │   └── publisher.py                        [EXISTING] — shared; no changes
│   │   │
│   │   ├── utils/
│   │   │   └── pdf_generators.py                   [EXISTING] — extended if Legal PDFs needed
│   │   │       # (No formal PDF output defined in SRS for Legal module v1)
│   │   │
│   │   ├── workflow_entity_paths.py                [EXISTING — MODIFIED]
│   │   │   # Legal entity routes appended:
│   │   │   # "filing_defendant":     "/legal/filings/defendant/{id}"
│   │   │   # "filing_plaintiff":     "/legal/filings/plaintiff/{id}"
│   │   │   # "minutes":              "/legal/minutes/{id}"
│   │   │   # "settlement_defendant": "/legal/settlements/defendant/{id}"
│   │   │   # "settlement_plaintiff": "/legal/settlements/plaintiff/{id}"
│   │   │   # "judgment_defendant":   "/legal/judgments/defendant/{id}"
│   │   │   # "judgment_plaintiff":   "/legal/judgments/plaintiff/{id}"
│   │   │   # "case_defendant":       "/legal/cases/defendant/{id}"
│   │   │   # "case_plaintiff":       "/legal/cases/plaintiff/{id}"
│   │   │
│   │   ├── kafka_producer.py                       [EXISTING] — shared; no changes
│   │   ├── kafka_permission_publisher.py           [EXISTING] — shared; no changes
│   │   ├── permission_middleware.py                [EXISTING] — shared; no changes
│   │   └── permissions.py                          [EXISTING] — shared; no changes
│   │
│   └── infrastructure/                             [EXISTING layer — extended]
│       │
│       ├── external/
│       │   ├── orchestration_client.py             [EXISTING] — shared; no changes
│       │   ├── iam_client.py                       [EXISTING] — shared; no changes
│       │   └── document_service_client.py          [EXISTING] — shared; no changes
│       │
│       ├── messaging/
│       │   ├── kafka_consumer.py                   [EXISTING — MODIFIED]
│       │   │   # Legal event handlers registered in consumer routing:
│       │   │   # corporate.events → legal member snapshot update (existing handler extended)
│       │   │   # fims.documents.events → null/flag legal document_id references
│       │   │   # workflow-events → update filing/settlement/minutes/closure status
│       │   └── event_publisher.py                  [EXISTING] — shared; no changes
│       │
│       └── services/
│           └── messaging_service.py                [EXISTING — MODIFIED]
│               # Legal publishing methods added:
│               # publish_legal_case_event(event_type, data)
│               # publish_legal_meeting_event(event_type, data)
│               # publish_legal_filing_event(event_type, data)
│               # publish_legal_directive_event(event_type, data)
│
├── config/
│   ├── settings.py                                 [EXISTING — MODIFIED]
│   │   # CELERY_BEAT_SCHEDULE additions:
│   │   # 'grc.check_legal_task_deadlines': daily at 06:00
│   │   # 'grc.check_legal_directive_deadlines': daily at 06:15
│   │   # 'grc.recalculate_meeting_quorum': every 15 min (or event-driven)
│   │
│   └── permissions/
│       └── grc-service.json                        [EXISTING — MODIFIED]
│           # Legal permission codes added (full set in §6 below)
│
└── shared/
    └── constants/
        └── event_types.py                          [EXISTING — MODIFIED]
            # LEGAL_CASE_EVENTS, LEGAL_MEETING_EVENTS,
            # LEGAL_FILING_EVENTS, LEGAL_DIRECTIVE_EVENTS constants added
```

---

## 6. File-by-File Purpose Reference

### 6.1 New Model File

**`apps/core/models/legal_entities.py`**

Contains all 22+ Legal domain models grouped logically:

| Group | Models in This File |
|---|---|
| Governance Structure | `CommitteeType`, `GoverningBody`, `Member` |
| Determinations | `SubmissionForDetermination` |
| Meeting Governance | `Meeting`, `MeetingAgenda`, `ConflictDeclaration`, `MeetingParticipant`, `MeetingDirective`, `Minutes`, `Resolution` |
| Litigation Common | `Hearing`, `HearingReport`, `TaskLitigation` |
| FCC Sued | `CaseDefendant`, `LitigationDirective`, `FilingDefendant`, `ResponseDefendant`, `SettlementDefendant`, `JudgmentDefendant`, `FinancialDefendant`, `FinancialPaymentRecord` |
| FCC Suing | `CasePlaintiff`, `FilingPlaintiff`, `ResponsePlaintiff`, `SettlementPlaintiff`, `JudgmentPlaintiff`, `FinancialPlaintiff` |
| Public Register | `PublicDecision` |
| Cross-cutting | `LegalAuditLog` |

All models follow `db_table = 'legal_{entity}'` convention.

---

### 6.2 New Serializer File

**`apps/api/serializers/legal_serializers.py`**

- One serializer class per model.
- FK dual-field pattern: `FK = NestedSerializer(read_only=True)` + `FK_id = UUIDField(write_only=True)`.
- Auto-set fields (e.g., `created_by`, `reference_number`) marked `required=False` in `extra_kwargs`.
- Computed fields via `SerializerMethodField` (e.g., `quorum_percentage`, `days_until_due`, `case_age_days`).

---

### 6.3 New URL File

**`apps/api/urls/legal.py`**

All Legal URL patterns. Organized by sub-domain section. Key routing rules:
- All under prefix `legal/` (mounted from `urls.py` as `path('legal/', include('apps.api.urls.legal'))`)
- Full path therefore: `/api/v1/grc/legal/`
- Static segments always declared before `<uuid:pk>/` to avoid route shadowing.

---

### 6.4 New View Files (16 files, one per entity group)

| File | Entities/Actions |
|---|---|
| `legal_dashboard_views.py` | Aggregate KPI stats across all Legal sub-domains |
| `legal_governance_views.py` | CommitteeType, GoverningBody, Member |
| `legal_submission_views.py` | SubmissionForDetermination + withdraw action |
| `legal_meeting_views.py` | Meeting CRUD + all 6 lifecycle action endpoints + quorum endpoint |
| `legal_agenda_views.py` | MeetingAgenda CRUD + ConflictDeclaration per item |
| `legal_participant_views.py` | MeetingParticipant list + RSVP response action |
| `legal_directive_views.py` | MeetingDirective CRUD + `close/` + `finally-close/` + Matters Arising list |
| `legal_minutes_views.py` | Minutes CRUD + workflow endpoints (5 standard) |
| `legal_resolution_views.py` | Resolution list/detail (read-only for invited participants) |
| `legal_case_defendant_views.py` | CaseDefendant CRUD + DG review + closure workflow |
| `legal_case_plaintiff_views.py` | CasePlaintiff CRUD (2 registration paths) + DG review + closure workflow |
| `legal_filing_views.py` | FilingDefendant/Plaintiff CRUD + 5 workflow endpoints + `mark-as-filed/` |
| `legal_response_views.py` | ResponseDefendant/Plaintiff CRUD |
| `legal_hearing_views.py` | Hearing CRUD per case + HearingReport CRUD per hearing |
| `legal_settlement_views.py` | Settlement CRUD + 5 workflow endpoints |
| `legal_judgment_views.py` | Judgment CRUD + DG decision action (triggers auto-creates) |
| `legal_financial_views.py` | Financial CRUD (1:1 per case, auto-created) + `record-recovery/` + `record-payment/` |
| `legal_task_views.py` | TaskLitigation CRUD + `close/` + overdue list |
| `legal_litigation_directive_views.py` | LitigationDirective CRUD + `close/` action |
| `legal_public_register_views.py` | PublicDecision CRUD + `publish/` action (Secretariat only) |

---

### 6.5 New Service Files (5 files, one per workflow entity)

| File | Workflow Template Code | Entity |
|---|---|---|
| `legal_filing_service.py` | `grc.legal_filing_approval` | FilingDefendant + FilingPlaintiff |
| `legal_minutes_service.py` | `grc.legal_minutes_approval` | Minutes |
| `legal_settlement_service.py` | `grc.legal_settlement_approval` | SettlementDefendant + SettlementPlaintiff |
| `legal_judgment_service.py` | `grc.legal_judgment_decision` | JudgmentDefendant + JudgmentPlaintiff |
| `legal_case_closure_service.py` | `grc.legal_case_closure` | CaseDefendant + CasePlaintiff |

---

### 6.6 New Celery Task Files (3 files)

| File | Schedule | Purpose |
|---|---|---|
| `legal_task_deadlines.py` | Daily at 06:00 | Detect overdue `TaskLitigation`; send notifications; handle 7d/2d/1d reminders |
| `legal_directive_deadlines.py` | Daily at 06:15 | Detect overdue `MeetingDirective` and `LitigationDirective`; notify assignees + secretaries |
| `legal_meeting_quorum.py` | Every 15 min | Recalculate `Meeting.quorum_met` for all REGISTERED meetings; notify secretary on threshold change |

---

### 6.7 New Event File

**`apps/core/events/legal_events.py`**

Domain event dataclasses inheriting from `GRCDomainEvent`. One class per significant domain event. Each defines `event_type`, `aggregate_id`, and `_get_event_data()`. Published via `KafkaMessagingService` to `grc.legal.events` topic.

---

### 6.8 Required Permission Codes (for `grc-service.json`)

```
# Governance Structure
grc:legal:governance:view
grc:legal:governance:manage

# Submissions for Determination
grc:legal:submission:create         (any authenticated user)
grc:legal:submission:view
grc:legal:submission:manage         (Secretary — attach to agenda)

# Meeting Management
grc:legal:meeting:view
grc:legal:meeting:manage            (Secretary)

# Minutes
grc:legal:minutes:manage            (Secretary)
grc:legal:minutes:approve           (Meeting participants)

# Resolutions & Directives (Meeting)
grc:legal:directive:view
grc:legal:directive:manage          (Secretary)
grc:legal:directive:close           (Assignee — initial closure)
grc:legal:directive:finally_close   (Secretary — final closure)

# Litigation — both modules
grc:legal:litigation:view
grc:legal:litigation:register       (Registry Officer, Legal Officer, Legal Manager)
grc:legal:litigation:manage         (Legal Officer, Legal Manager)
grc:legal:filing:approve            (Legal Manager + DG)
grc:legal:filing:file               (Legal Officer — mark as FILED)
grc:legal:case:close                (Legal Manager initiates; DG approves)
grc:legal:dg:review                 (DG only)

# Public Register
grc:legal:public_register:view
grc:legal:public_register:publish   (Secretariat only)

# Dashboard
grc:legal:dashboard:view
```

---

*End of Architecture Overview & Directory Structure*
*Next phase: Legal Module — Data Model Design*
