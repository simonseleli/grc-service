# GRC Service — Internal Audit Module: Backend Developer Reference

**Service:** `grc-service`
**Module:** Internal Audit
**Stack:** Django 4.x · Django REST Framework · PostgreSQL · Celery · Kafka
**Purpose:** This document is the single authoritative reference for how the Internal Audit module backend is designed and implemented. Any developer building a new module in this service must follow the same patterns described here.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Directory Structure](#2-directory-structure)
3. [Base Models and Mixins](#3-base-models-and-mixins)
4. [Data Models and Relationships](#4-data-models-and-relationships)
5. [Lookup Tables](#5-lookup-tables)
6. [Workflow Integration](#6-workflow-integration)
7. [API Layer Design Patterns](#7-api-layer-design-patterns)
8. [Serializers](#8-serializers)
9. [Pagination](#9-pagination)
10. [Response Envelope Standard](#10-response-envelope-standard)
11. [Authentication and JWT](#11-authentication-and-jwt)
12. [Roles and Permissions (RBAC)](#12-roles-and-permissions-rbac)
13. [URL Structure](#13-url-structure)
14. [Service Layer (Business Logic)](#14-service-layer-business-logic)
15. [Domain Events (Kafka)](#15-domain-events-kafka)
16. [Notification System](#16-notification-system)
17. [Celery Background Tasks](#17-celery-background-tasks)
18. [External Service Clients](#18-external-service-clients)
19. [Organizational Data Sync](#19-organizational-data-sync)
20. [Auto-generated Reference Numbers](#20-auto-generated-reference-numbers)
21. [Business Logic Rules Summary](#21-business-logic-rules-summary)
22. [Module Implementation Checklist](#22-module-implementation-checklist)

---

## 1. Architecture Overview

The GRC service follows the **FIMS microservices pattern**. Each module is self-contained within the service and integrates with the broader platform through:

| Integration Point | Mechanism |
|---|---|
| Authentication | Shared JWT secret with IAM service |
| Permissions | JWT-embedded permission codes, validated locally by `JWTPermissionMiddleware` |
| Workflow approvals | HTTP calls to `work-orchestration-service` via `OrchestrationClient` |
| Notifications | Kafka events published to priority-tiered topics (`notifications-high`, `notifications-normal`, etc.) |
| Document storage | HTTP calls to `document-records-service` via `DocumentServiceClient` |
| Organizational data | Kafka consumer syncs from `corporate-service` into local `Directorate`, `Department`, `Unit` tables |
| User profiles | HTTP calls to `iam-service` via `IAMClient` (for name/email resolution) |

```
┌────────────┐     JWT      ┌───────────────┐
│ Frontend   │◄────────────►│   IAM Service │
│            │              └───────────────┘
│            │  REST (Bearer)        │  Kafka: org sync
│            │◄────────────►┌────────┴──────┐
│            │              │  GRC Service  │
└────────────┘              │               │
                            │  apps/        │
                            │  ├─ api/      │  HTTP ►  Work Orchestration
                            │  ├─ core/     │  HTTP ►  Document Records
                            │  └─ infra/    │  HTTP ►  IAM Client
                            │               │  Kafka ► Notifications
                            └───────────────┘
```

The service runs on **port 8003** (Docker service name: `grc-service`). All paths under `/api/v1/grc/` are routed from the API Gateway.

---

## 2. Directory Structure

The tree below lists every significant file and directory that exists in the service at the time of writing. Files and directories that are runtime-generated or are standard Django boilerplate (`__pycache__/`, `__init__.py`) are omitted for readability.

```
grc-service/
│
│   # ── Top-level entry points & configuration ──────────────────────────────
├── manage.py                           # Django CLI entry point
├── conftest.py                         # Root pytest fixtures (shared across all tests)
├── pytest.ini                          # pytest configuration
├── requirements.txt                    # Python dependency list
├── Dockerfile                          # Production container image
├── docker-compose.yml                  # Local development compose
├── docker-compose.prod.yml             # Production compose
├── docker-entrypoint.sh                # Container startup script
├── env.example                         # Environment variable template
│
│   # ── Application source ───────────────────────────────────────────────────
├── apps/
│   │
│   ├── api/                            # HTTP interface layer (DRF views, serializers, URLs)
│   │   ├── apps.py                     # Django AppConfig (AppLabel: "api")
│   │   ├── authentication.py           # IAMJWTAuthentication + ServiceAuthentication classes
│   │   ├── exceptions.py               # Custom DRF exception handler (maps exceptions → envelope)
│   │   ├── permissions_jwt.py          # Named DRF permission classes, one class per permission code
│   │   │
│   │   ├── decorators/
│   │   │   └── permissions.py          # @require_grc_permission(code) view decorator
│   │   │
│   │   ├── serializers/
│   │   │   ├── audit_serializers.py    # All Internal Audit entity serializers
│   │   │   ├── lookup_serializers.py   # FiscalYear, Quarter, AuditSeverity, etc. serializers
│   │   │   └── organizational_serializers.py  # Directorate/Department/Unit serializers
│   │   │
│   │   ├── urls/
│   │   │   ├── urls.py                 # Root URL router — mounts audit/, config/, organizational/
│   │   │   ├── audit.py                # All Internal Audit URL patterns (CRUD + workflow endpoints)
│   │   │   ├── config_urls.py          # Admin config/lookup management endpoints
│   │   │   ├── organizational_urls.py  # Org-structure read endpoints
│   │   │   └── health.py               # GET /health/ liveness probe endpoint
│   │   │
│   │   ├── utils/
│   │   │   ├── pagination.py           # paginate_queryset(), get_ordering_param()
│   │   │   └── response_helpers.py     # success_response(), paginated_list_response(), etc.
│   │   │
│   │   └── views/                      # One module per entity or functional group
│   │       ├── audit_dashboard_views.py          # Dashboard aggregate stats
│   │       ├── audit_engagement_views.py         # AuditEngagement CRUD + workflow actions
│   │       ├── audit_finding_views.py            # AuditFinding CRUD
│   │       ├── audit_meeting_views.py            # AuditMeeting CRUD
│   │       ├── audit_memo_views.py               # AuditMemo CRUD + workflow actions
│   │       ├── audit_monitoring_views.py         # Monitoring summary views
│   │       ├── audit_plan_views.py               # AuditPlan CRUD + workflow actions
│   │       ├── audit_program_views.py            # AuditProgram CRUD + workflow actions
│   │       ├── audit_quarterly_report_views.py   # QuarterlyAuditReport CRUD + workflow actions
│   │       ├── audit_recommendation_views.py     # AuditRecommendation CRUD
│   │       ├── audit_report_views.py             # AuditReport CRUD + workflow actions
│   │       ├── audit_survey_views.py             # AuditSurvey CRUD
│   │       ├── audit_universe_views.py           # AuditUniverse CRUD + workflow actions
│   │       ├── auditable_entity_views.py         # AuditableEntity CRUD
│   │       ├── config_views.py                   # Lookup admin CRUD (FiscalYear, Quarter, etc.)
│   │       ├── declaration_views.py              # DeclarationOfIndependence CRUD + PDF generation
│   │       ├── engagement_notification_views.py  # EngagementNotification CRUD + workflow actions
│   │       ├── health_view.py                    # Liveness probe handler
│   │       ├── implementation_monitoring_views.py # ImplementationMonitoring CRUD
│   │       ├── lookup_views.py                   # Read-only lookup endpoints (for dropdowns)
│   │       ├── organizational_views.py           # Read-only org structure endpoints
│   │       ├── rcm_views.py                      # RiskControlMatrix + RCMEntry CRUD
│   │       ├── risk_assessment_views.py          # RiskAssessment CRUD
│   │       └── working_paper_views.py            # WorkingPaper CRUD + workflow actions
│   │
│   ├── core/                           # Business logic layer
│   │   ├── apps.py                     # Django AppConfig (AppLabel: "core")
│   │   │
│   │   ├── models/
│   │   │   ├── base.py                 # BaseModel, TimestampedModel, StatusMixin, WorkflowMixin
│   │   │   ├── lookups.py              # FiscalYear, Quarter, AuditSeverity, FindingType, RiskRating, AuditOpinion
│   │   │   ├── organizational.py       # Directorate, Department, Unit (replicated from Corporate Service)
│   │   │   └── audit_entities.py       # All Internal Audit business models (20+ models)
│   │   │
│   │   ├── migrations/                 # Django database migrations (auto-generated)
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_workflow_mixin_fields.py
│   │   │   └── … (0003 through 0020 as of current implementation)
│   │   │
│   │   ├── services/                   # Workflow and business-logic service classes
│   │   │   ├── audit_engagement_service.py       # AuditEngagement workflow orchestration
│   │   │   ├── audit_memo_service.py             # AuditMemo workflow orchestration
│   │   │   ├── audit_plan_service.py             # AuditPlan workflow orchestration
│   │   │   ├── audit_program_service.py          # AuditProgram workflow orchestration
│   │   │   ├── audit_report_service.py           # AuditReport workflow orchestration
│   │   │   ├── audit_universe_service.py         # AuditUniverse workflow orchestration
│   │   │   ├── corporate_sync.py                 # OrganizationalSyncService (pulls org data from Corporate)
│   │   │   ├── engagement_notification_service.py # EngagementNotification workflow orchestration
│   │   │   ├── quarterly_report_service.py       # QuarterlyAuditReport workflow orchestration
│   │   │   └── working_paper_service.py          # WorkingPaper workflow orchestration
│   │   │
│   │   ├── tasks/                      # Celery beat periodic tasks
│   │   │   ├── monitoring_deadlines.py # Flags overdue ImplementationMonitoring records
│   │   │   ├── organizational_sync.py  # Periodic re-sync of org structure from Corporate
│   │   │   └── report_generation.py    # Scheduled report generation helpers
│   │   │
│   │   ├── management/
│   │   │   └── commands/               # Django management commands (runnable via manage.py)
│   │   │       ├── seed_lookup_data.py           # Populates FiscalYear, Quarter, severity/type tables
│   │   │       ├── register_workflow_templates.py # Verifies WO has the GRC workflow templates
│   │   │       ├── consume_grc_events.py         # Starts the long-running Kafka consumer process
│   │   │       └── sync_organizational_data.py   # Manual trigger for org-structure sync
│   │   │
│   │   ├── events/
│   │   │   └── audit_events.py         # Domain event dataclasses (AuditPlanCreatedEvent, etc.)
│   │   │
│   │   ├── notifications/
│   │   │   └── publisher.py            # NotificationPublisher — wraps Kafka for notification events
│   │   │
│   │   ├── workflows/
│   │   │   ├── workflows.yaml          # YAML definitions for all 9 GRC workflow templates
│   │   │   └── registry.py             # WorkflowTemplateRegistry — loads & provides templates by code
│   │   │
│   │   ├── templates/
│   │   │   ├── notifications.yaml      # Notification message templates (subject + body per event type)
│   │   │   └── registry.py             # NotificationTemplateRegistry — loads templates by event code
│   │   │
│   │   ├── utils/
│   │   │   └── pdf_generators.py       # WeasyPrint PDF generators for formal output documents
│   │   │                               #   generate_declaration_pdf(), generate_engagement_notification_pdf(),
│   │   │                               #   generate_meeting_minutes_pdf(), generate_attendance_register_pdf()
│   │   │
│   │   ├── kafka_producer.py           # GrcServiceKafkaProducer — lazily-initialized Kafka producer
│   │   ├── kafka_permission_publisher.py # PermissionPublisher — publishes permission catalog to IAM via Kafka
│   │   ├── permission_middleware.py    # JWTPermissionMiddleware — validates permission codes from JWT claims
│   │   ├── permissions.py              # GrcServicePermissions — loads grc-service.json, hashes catalog
│   │   ├── sample_data.py              # Development-only fixture constants (not seeded to DB)
│   │   └── workflow_entity_paths.py    # Maps entity type → frontend detail URL path
│   │
│   └── infrastructure/                 # External service adapters
│       ├── external/
│       │   ├── orchestration_client.py  # OrchestrationClient — HTTP client for work-orchestration-service
│       │   ├── iam_client.py            # IAMClient — HTTP client for iam-service (user profile lookup)
│       │   └── document_service_client.py # DocumentServiceClient — HTTP client for document-records-service
│       │
│       ├── messaging/
│       │   ├── kafka_producer.py        # FIMSKafkaProducer — shared/base Kafka producer
│       │   ├── kafka_consumer.py        # GRCKafkaConsumer — consumes events from IAM, Corporate, WO
│       │   └── event_publisher.py       # publish_event() — thin wrapper used by MessagingService
│       │
│       └── services/
│           └── messaging_service.py     # KafkaMessagingService — publishes domain events (engagement, plan, finding, WP)
│
│   # ── Django project configuration ─────────────────────────────────────────
├── config/
│   ├── settings.py                     # All Django settings (DB, Kafka, Celery, JWT, DRF, etc.)
│   ├── celery.py                        # Celery application instance + beat schedule
│   ├── urls.py                          # Root URL conf — mounts /api/v1/grc/ and /health/
│   ├── asgi.py                          # ASGI entrypoint
│   ├── wsgi.py                          # WSGI entrypoint
│   └── permissions/
│       └── grc-service.json             # Declarative RBAC catalog — all permission codes for this service
│
│   # ── Shared cross-cutting utilities ──────────────────────────────────────
├── shared/
│   ├── constants/
│   │   └── event_types.py               # Kafka event type string constants (AUDIT_PLAN_EVENTS, etc.)
│   └── common/
│       └── messaging/
│           └── kafka_producer.py        # FIMSKafkaProducer base class (shared across FIMS services)
│
│   # ── Django HTML templates (WeasyPrint / PDF output) ─────────────────────
├── templates/
│   └── grc/
│       ├── attendance_register.html     # PDF: Meeting attendance register
│       ├── declaration_of_independence.html  # PDF: Declaration of Independence sign-off
│       ├── engagement_notification.html # PDF: Formal engagement notification letter
│       └── meeting_minutes.html         # PDF: Formal meeting minutes
│
│   # ── Tests ─────────────────────────────────────────────────────────────────
├── tests/
│   ├── conftest.py                      # (inherited from root conftest.py)
│   ├── api/
│   │   ├── test_audit_report_auditee_responses.py  # API-level tests for auditee follow-up cycle
│   │   └── test_working_paper_workflow.py          # Working paper workflow API tests
│   ├── infrastructure/
│   │   └── test_orchestration_client.py           # OrchestrationClient integration tests
│   └── e2e/
│       └── test_working_paper_workflow_e2e.py      # End-to-end workflow test
│
│   # ── Operational ───────────────────────────────────────────────────────────
├── scripts/
│   └── e2e_check.py                     # Manual end-to-end connectivity smoke-test script
├── docs/                                # Developer reference documentation
├── logs/                                # Runtime log output (volume-mounted)
├── media/                               # Uploaded media files (volume-mounted)
├── static/                              # Collected static assets
└── staticfiles/                         # Django collectstatic output
```

---

### Layer Summary

| Layer | Path | Responsibility |
|---|---|---|
| **API** | `apps/api/` | DRF views, serializers, URL routing, auth, permission classes, response helpers, pagination |
| **Core** | `apps/core/` | All business models, migration history, workflow services, Celery tasks, domain events, notification publishing, management commands, PDF generators |
| **Infrastructure** | `apps/infrastructure/` | HTTP clients (IAM, WO, DRS), Kafka producer/consumer, domain event publisher |
| **Config** | `config/` | Django project settings, Celery config, root URL conf, RBAC permission catalog |
| **Shared** | `shared/` | Cross-cutting constants and base utilities reused across FIMS services |
| **Templates** | `templates/` | Django HTML templates rendered by WeasyPrint into PDFs for formal output documents |
| **Tests** | `tests/` | API, infrastructure and end-to-end tests |

---

### Key File Cross-References

| File | Where Used | Related Section |
|---|---|---|
| `apps/api/authentication.py` | Applied as `DEFAULT_AUTHENTICATION_CLASSES` in `config/settings.py` | §11 Authentication and JWT |
| `apps/api/permissions_jwt.py` | Referenced in every `APIView.check_permissions()` | §12 Roles and Permissions |
| `apps/api/utils/pagination.py` | Called in every list view | §9 Pagination |
| `apps/api/utils/response_helpers.py` | Called in every view handler | §10 Response Envelope Standard |
| `apps/core/models/base.py` | Inherited by all models | §3 Base Models and Mixins |
| `apps/core/models/audit_entities.py` | All 20+ audit entity models | §4 Data Models and Relationships |
| `apps/core/models/lookups.py` | FiscalYear, Quarter, RiskRating, etc. | §5 Lookup Tables |
| `apps/core/workflows/workflows.yaml` | Loaded by `WorkflowTemplateRegistry`; templates registered in WO | §6 Workflow Integration |
| `apps/core/services/` | Called from views for all workflow operations | §6 Workflow Integration, §14 Service Layer |
| `apps/core/utils/pdf_generators.py` | Called from `declaration_views.py`, `engagement_notification_views.py`, etc. | PDF generation pattern — see §14 |
| `apps/core/kafka_permission_publisher.py` | Publishes `service.permission.registry` Kafka topic on startup | §12 Roles and Permissions |
| `apps/core/permission_middleware.py` | Registered as `MIDDLEWARE` in `config/settings.py` | §12 Roles and Permissions |
| `apps/core/management/commands/seed_lookup_data.py` | Run once during first deployment to populate lookup tables | §5 Lookup Tables |
| `apps/core/management/commands/register_workflow_templates.py` | Verifies WO has GRC templates; templates owned/seeded by WO | §6 Workflow Integration |
| `apps/infrastructure/external/orchestration_client.py` | Used by all workflow service classes | §18 External Service Clients |
| `apps/infrastructure/messaging/kafka_consumer.py` | Started by `manage.py consume_grc_events` | §19 Organizational Data Sync |
| `config/permissions/grc-service.json` | Loaded by `GrcServicePermissions`; published to IAM and validated by middleware | §12 Roles and Permissions |
| `shared/constants/event_types.py` | Imported by `apps/infrastructure/services/messaging_service.py` | §15 Domain Events |
| `templates/grc/*.html` | Rendered with WeasyPrint in `apps/core/utils/pdf_generators.py` | PDF generation pattern |

---

## 3. Base Models and Mixins

**Source file:** `apps/core/models/base.py`

Every concrete model in the service inherits from one or more of the four base classes below. No concrete model inherits directly from `django.db.models.Model`.

---

### `BaseModel`

```python
class BaseModel(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

- All GRC entities use **UUID primary keys** — never auto-increment integers.
- `created_at` carries `db_index=True` for fast `ORDER BY created_at` queries.
- `updated_at` is set automatically on every `save()` — never set manually.

---

### `TimestampedModel(BaseModel)`

```python
class TimestampedModel(BaseModel):
    created_by  = models.UUIDField()                          # required — IAM user ID
    modified_by = models.UUIDField(null=True, blank=True)     # nullable — IAM user ID

    class Meta:
        abstract = True
```

- `created_by` is **required** (no `null=True`). Views must always set it from `request.user_id` before saving.
- `modified_by` is nullable because a record may not have been edited since creation.
- Both fields store **IAM user UUIDs only** — never Django auth user IDs, never user names or emails.
- User display data (name, email) is resolved at read time via `IAMClient.get_user_profile()`.

---

### `StatusMixin`

```python
class StatusMixin(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True
```

- Provides the **soft-delete flag** for every entity.
- `is_active=False` is the only supported deletion mechanism. Hard deletes are never performed.
- `db_index=True` ensures `filter(is_active=True)` queries are efficient.
- All default querysets should include `.filter(is_active=True)` unless explicitly retrieving deleted records.

---

### `WorkflowMixin`

```python
class WorkflowMixin(models.Model):
    workflow_plan_id      = models.UUIDField(null=True, blank=True, db_index=True)
    workflow_stage        = models.CharField(max_length=255, blank=True, default='')
    workflow_stage_id     = models.UUIDField(null=True, blank=True)
    workflow_started_at   = models.DateTimeField(null=True, blank=True)
    workflow_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
```

Mixed into any entity whose lifecycle is managed by the Work Orchestration Service (WO). The 5 fields mirror the WO plan state directly in the GRC database so that basic status can be read without a WO round-trip.

#### Properties

| Property | Returns | Meaning |
|---|---|---|
| `has_workflow` | `bool` | `True` if `workflow_plan_id` is set |
| `has_active_workflow` | `bool` | `True` if plan is set **and** not yet completed |
| `is_workflow_completed` | `bool` | `True` if `workflow_completed_at` is set |

#### Mutating Methods

| Method | Signature | What it does |
|---|---|---|
| `start_workflow()` | `(plan_id, initial_stage='', stage_id=None)` | Sets all 5 workflow fields; stamps `workflow_started_at = now()`. Call after WO returns a plan ID. |
| `update_workflow_stage()` | `(stage_name, stage_id=None)` | Updates `workflow_stage` and optionally `workflow_stage_id`. Call after WO advances a stage. |
| `complete_workflow()` | `()` | Sets `workflow_completed_at = now()`. Call when WO reaches a terminal state (approved / noted). |
| `cancel_workflow()` | `()` | Also sets `workflow_completed_at = now()`. Semantically distinct from `complete_workflow()` — use when the plan is cancelled rather than approved. |
| `clear_workflow()` | `()` | Resets all 5 workflow fields to their defaults (nulls / empty string). Use if a workflow needs to be re-started from scratch. |

#### Override Hooks

These two methods have base implementations on `WorkflowMixin` but **must be overridden** on every concrete workflow entity to supply entity-specific data:

| Method | Base Returns | Override Must Supply |
|---|---|---|
| `get_workflow_context()` | `{'entity_type': …, 'entity_id': …}` | All `{{variable}}` values referenced in `assignees` in the YAML template (e.g., `prepared_by`, `fiscal_year_id`). See §6.4. |
| `get_workflow_metadata()` | `{'entity_type': …, 'entity_id': …, 'entity_repr': …}` | Display fields stored on the WO plan (`reference_number`, `title`, `status`, `entity_detail_path`). See §6.4. |

A third hook, `log_workflow_action()`, is a stub that can be overridden to persist per-action audit records. The base implementation is a no-op.

---

### Composition Pattern

All concrete models compose from the above three classes (note: `StatusMixin` and `WorkflowMixin` both inherit `models.Model` themselves, so they do **not** inherit `BaseModel` — `TimestampedModel` provides `BaseModel` through its own inheritance chain):

```python
# Entity with a workflow
class AuditPlan(TimestampedModel, StatusMixin, WorkflowMixin):
    …

# Entity without a workflow
class AuditFinding(TimestampedModel, StatusMixin):
    …
```

#### Full Composition Reference

| Entity | `TimestampedModel` | `StatusMixin` | `WorkflowMixin` |
|---|:---:|:---:|:---:|
| **Audit entities** (`audit_entities.py`) | | | |
| `AuditUniverse` | ✓ | ✓ | ✓ |
| `AuditableEntity` | ✓ | ✓ | |
| `RiskAssessment` | ✓ | ✓ | |
| `AuditPlan` | ✓ | ✓ | ✓ |
| `AuditEngagement` | ✓ | ✓ | ✓ |
| `DeclarationOfIndependence` | ✓ | ✓ | |
| `EngagementNotification` | ✓ | ✓ | ✓ |
| `AuditMemo` | ✓ | ✓ | ✓ |
| `AuditSurvey` | ✓ | ✓ | |
| `AuditProgram` | ✓ | ✓ | ✓ |
| `RiskControlMatrix` | ✓ | ✓ | |
| `RCMEntry` | ✓ | | |
| `AuditMeeting` | ✓ | ✓ | |
| `WorkingPaper` | ✓ | ✓ | ✓ |
| `AuditFinding` | ✓ | ✓ | |
| `AuditRecommendation` | ✓ | ✓ | |
| `ImplementationMonitoring` | ✓ | ✓ | |
| `AuditeeFollowUpResponse` | ✓ | ✓ | |
| `AuditReport` | ✓ | ✓ | ✓ |
| `QuarterlyAuditReport` | ✓ | ✓ | ✓ |
| **Lookup tables** (`lookups.py`) | | | |
| `FiscalYear` | ✓ | ✓ | |
| `Quarter` | ✓ | ✓ | |
| `AuditSeverity` | ✓ | ✓ | |
| `FindingType` | ✓ | ✓ | |
| `RiskRating` | ✓ | ✓ | |
| `AuditOpinion` | ✓ | ✓ | |
| **Organizational** (`organizational.py`) | | | |
| `Directorate` | ✓ | ✓ | |
| `Department` | ✓ | ✓ | |
| `Unit` | ✓ | ✓ | |
| `Section` | ✓ | ✓ | |
| `OrganizationalSyncLog` ¹ | — | — | — |

> ¹ `OrganizationalSyncLog` inherits directly from `BaseModel` only (no `TimestampedModel`, no `StatusMixin`). It is a write-once log table for org-sync audit trails.

> **Rule:** If an entity has a workflow, add `WorkflowMixin`. `RCMEntry` is the only model that omits `StatusMixin` — its lifecycle is governed entirely by its parent `RiskControlMatrix`. Everything else uses `TimestampedModel + StatusMixin` as the minimum base.

---

## 4. Data Models and Relationships

**Source file:** `apps/core/models/audit_entities.py`

---

### 4.1 Entity Hierarchy

The tree below reflects the actual FK/OneToOne relationships in the code. Relationship cardinality is noted inline.

```
FiscalYear (lookup)
├── AuditUniverse  (FK; partial unique: 1 active universe per FY)
│   └── AuditableEntity  (FK; many per universe)
│       └── RiskAssessment  (FK; many per entity)
│
└── AuditPlan  (FK to FiscalYear AND AuditUniverse)
    ├── AuditMemo  (FK to AuditPlan + AuditableEntity — issued before engagement exists)
    │   └── DeclarationOfIndependence  (optional FK to AuditMemo)
    │
    └── AuditEngagement  (FK to AuditPlan + AuditableEntity; many per plan)
        │
        ├── DeclarationOfIndependence  (FK to AuditEngagement; unique per [engagement, declarant])
        ├── AuditSurvey  (OneToOneField — 1:1)
        ├── RiskControlMatrix  (OneToOneField — 1:1)
        │   └── RCMEntry  (FK; many per RCM)
        ├── AuditProgram  (OneToOneField — 1:1; optional FK to RiskControlMatrix)
        ├── EngagementNotification  (OneToOneField — 1:1; optional FK to AuditProgram)
        ├── AuditMeeting  (FK; many per engagement — types: entry/pre_exit/team/exit)
        ├── WorkingPaper  (FK; many per engagement)
        │   └── AuditFinding  (FK to engagement; optional FK to WorkingPaper)
        │       └── AuditRecommendation  (FK to finding; many per finding)
        │           └── ImplementationMonitoring  (OneToOneField — 1:1 with recommendation)
        │               └── AuditeeFollowUpResponse  (FK; one row per review cycle)
        └── AuditReport  (OneToOneField — 1:1)

Quarter (lookup)
└── QuarterlyAuditReport  (FK to FiscalYear + Quarter; unique per [fiscal_year, quarter])
    └── M2M → AuditReport  (engagement_reports — many audit reports per quarterly report)
```

> **Important:** `AuditMemo` is attached to `AuditPlan + AuditableEntity`, **not** to `AuditEngagement`. The memo is the formal instrument that precedes engagement creation — it authorises the audit. Once the memo is approved, an `AuditEngagement` is created separately.

---

### 4.2 Complete Table Reference

| Model Class | `db_table` | Relationship Type | Primary Purpose |
|---|---|---|---|
| **Lookup tables** (`lookups.py`) | | | |
| `FiscalYear` | `grc_fiscal_year` | — | Period anchoring for all activity |
| `Quarter` | `grc_quarter` | FK → `FiscalYear` | Sub-period (Q1–Q4) within a fiscal year |
| `AuditSeverity` | `grc_audit_severity` | — | Standardized severity levels for findings |
| `FindingType` | `grc_finding_type` | — | Classification codes for finding types |
| `RiskRating` | `grc_risk_rating` | — | Risk levels with numerical score thresholds |
| `AuditOpinion` | `grc_audit_opinion` | — | Report opinion types (e.g., Satisfactory) |
| **Organizational** (`organizational.py`) | | | |
| `Directorate` | `grc_directorate` | — | Top-level org unit, synced from Corporate Service |
| `Department` | `grc_department` | FK → `Directorate` | Mid-level org unit |
| `Unit` | `grc_unit` | FK → `Department` | Operational unit |
| `Section` | `grc_section` | FK → `Unit` | Sub-unit within an operational unit |
| `OrganizationalSyncLog` | `grc_organizational_sync_log` | — | Write-once log of each org-sync operation |
| **Audit entities** (`audit_entities.py`) | | | |
| `AuditUniverse` | `grc_audit_universe` | FK → `FiscalYear` | Top-level audit scope definition; 1 active per FY (partial unique) |
| `AuditableEntity` | `grc_auditable_entity` | FK → `AuditUniverse`; optional FK → `Directorate`, `Unit` | Individual unit/process within the universe |
| `RiskAssessment` | `grc_risk_assessment` | FK → `AuditableEntity` | Scored risk evaluation; auto-calculates weighted scores on `save()` |
| `AuditPlan` | `grc_audit_plan` | FK → `FiscalYear`, `AuditUniverse` | RBIAP — Risk-Based Internal Audit Plan |
| `AuditMemo` | `grc_audit_memo` | FK → `AuditPlan`, `AuditableEntity` | Formal memo authorising an audit (issued before engagement) |
| `AuditEngagement` | `grc_audit_engagement` | FK → `AuditPlan`, `AuditableEntity` | Individual audit assignment |
| `DeclarationOfIndependence` | `grc_declaration_of_independence` | FK → `AuditEngagement`; optional FK → `AuditMemo` | Per-team-member independence declaration; unique per `[engagement, declarant]` |
| `AuditSurvey` | `grc_audit_survey` | OneToOneField → `AuditEngagement` | Preliminary survey + Fraud Risk Assessment (1:1) |
| `RiskControlMatrix` | `grc_risk_control_matrix` | OneToOneField → `AuditEngagement` | RCM header — maps risks to controls (1:1) |
| `RCMEntry` | `grc_rcm_entry` | FK → `RiskControlMatrix`; FK → `RiskRating` | Individual risk/control row in the RCM |
| `AuditProgram` | `grc_audit_program` | OneToOneField → `AuditEngagement`; optional FK → `RiskControlMatrix` | Formal audit program — objectives, procedures, scope (1:1) |
| `EngagementNotification` | `grc_engagement_notification` | OneToOneField → `AuditEngagement`; optional FK → `AuditProgram` | Formal notice issued to auditee before fieldwork (1:1) |
| `AuditMeeting` | `grc_audit_meeting` | FK → `AuditEngagement` | Meeting record — types: entry / pre_exit / team / exit |
| `WorkingPaper` | `grc_working_paper` | FK → `AuditEngagement` | Evidence/documentation during fieldwork; stores `document_id` in DRS |
| `AuditFinding` | `grc_audit_finding` | FK → `AuditEngagement`; optional FK → `WorkingPaper`; FK → `FiscalYear`, `Quarter`, `FindingType`, `AuditSeverity`, `RiskRating` | Issue identified during engagement; unique per `[engagement, reference_number]` |
| `AuditRecommendation` | `grc_audit_recommendation` | FK → `AuditFinding` | Corrective action; unique per `[finding, reference_number]` |
| `ImplementationMonitoring` | `grc_implementation_monitoring` | OneToOneField → `AuditRecommendation` | Follow-up header; denormalizes `latest_progress` + `is_overdue` for dashboards (1:1) |
| `AuditeeFollowUpResponse` | `grc_auditee_follow_up_response` | FK → `ImplementationMonitoring` | One row per review cycle; unique per `[monitoring, cycle_number]` |
| `AuditReport` | `grc_audit_report` | OneToOneField → `AuditEngagement`; FK → `AuditOpinion` | Final engagement report (1:1); stores `document_id` + `stamped_document_url` |
| `QuarterlyAuditReport` | `grc_quarterly_audit_report` | FK → `FiscalYear`, `Quarter`; M2M → `AuditReport` | Quarterly consolidated report; unique per `[fiscal_year, quarter]` |

---

### 4.3 Key Design Decisions

#### UUID-only foreign keys to IAM users

Fields like `lead_auditor`, `prepared_by`, `responsible_party`, `declarant_user_id` store only a UUID. The service **never** stores names or emails in model fields. User display data is resolved at read time via `IAMClient.get_user_profile()`. This is also true for `created_by` / `modified_by` inherited from `TimestampedModel`.

#### Lookup tables instead of `choices=` constants

Severity, finding type, risk rating, audit opinion, fiscal year, and quarter are all separate FK-referenced models — **not** `CharField(choices=…)`. This makes values admin-configurable without a code deployment, enables cross-entity analytics (e.g., aggregate findings by severity), and allows lookup values to carry extra attributes (e.g., `RiskRating.numerical_value`, `AuditSeverity.color_code`).

#### JSONField for flexible list data

`audit_team`, `objectives`, `attendees`, `action_items`, `evidence_document_ids`, `procedures`, `fraud_risk_assessment`, `control_assessments`, `risk_themes` etc. all use `JSONField(default=list)` or `JSONField(default=dict)`. This avoids separate join tables for simple list/dict data that does not require independent querying. The comment block on each field documents the expected element schema.

#### 1:1 relationship pattern

Several entities are always exactly one-per-engagement. These use `OneToOneField` (not `ForeignKey`) so that Django enforces DB uniqueness and enables direct reverse access (`engagement.report`, `engagement.survey`, etc.):

| OneToOneField | Parent | `related_name` |
|---|---|---|
| `AuditSurvey.audit_engagement` | `AuditEngagement` | `survey` |
| `RiskControlMatrix.audit_engagement` | `AuditEngagement` | `risk_control_matrix` |
| `AuditProgram.audit_engagement` | `AuditEngagement` | `audit_program` |
| `EngagementNotification.audit_engagement` | `AuditEngagement` | `engagement_notification` |
| `AuditReport.engagement` | `AuditEngagement` | `report` |
| `ImplementationMonitoring.recommendation` | `AuditRecommendation` | `monitoring` |

#### ImplementationMonitoring / AuditeeFollowUpResponse cycle pattern

`ImplementationMonitoring` acts as the **header** (1:1 with `AuditRecommendation`). Follow-up cycles are separate `AuditeeFollowUpResponse` rows with `cycle_number` auto-incremented in the view layer. The header denormalizes `latest_progress` and `is_overdue` for fast dashboard reads.

The documented cycle flow (from the model docstring):
1. **Auditor creates cycle** → `cycle_number` auto-incremented, `status='pending'`
2. **Auditor notifies auditee** → `notified_at` + `response_deadline` set on the cycle row; mirrored to header
3. **Auditee submits** → `submitted_by`, `submitted_at`, `implementation_progress`, `evidence_documents`; `status='submitted'`; header `auditee_responded_at` updated
4. **Auditor verifies** → `status='verified'` or `'rejected'`; if verified: header `latest_progress` updated; if rejected: new cycle starts from step 1
5. **Final closure** → header `status='closed'`

#### RiskAssessment auto-scoring

`RiskAssessment.save()` automatically calculates two composite scores from 6 input dimensions (`inherent_risk`, `control_effectiveness`, `financial_exposure`, `compliance_risk`, `operational_impact`, `reputational_risk`) using configurable weights defined in `DEFAULT_WEIGHTS`. Auto-populated fields:

| Field | How populated |
|---|---|
| `calculated_weighted_score` | Weighted sum of 6 score dimensions |
| `calculated_residual_score` | `weighted_score × (1 − control_effectiveness / 10)` |
| `auto_overall_rating` (FK) | `classify_score()` — threshold range lookup or nearest `numerical_value` |
| `auto_residual_rating` (FK) | Same via residual score |

Manual override is supported: setting `rating_overridden=True` prevents `save()` from updating `overall_risk_rating` / `residual_risk_rating` even when scores change.

When `save()` is called with `update_fields`, auto-calculation is skipped unless the `update_fields` set intersects any score-related field (so status-only saves do not trigger re-scoring).

#### DRS document + stamped PDF pattern

Several workflow-approved entities generate formal PDF output via WeasyPrint, upload to Document Records Service, and store two document references:

| Field | Meaning |
|---|---|
| `document_id` (UUIDField) | DRS document UUID — set by `DocumentServiceClient` after upload |
| `stamped_document_url` (URLField) | URL to the DRS-stamped PDF (CIA signature + QR code embedded) |

Models that carry this pair: `AuditMemo`, `DeclarationOfIndependence`, `AuditProgram`, `EngagementNotification`, `AuditReport`. PDF generation lives in `apps/core/utils/pdf_generators.py`; HTML templates live in `templates/grc/`.

#### `AuditMemo` precedes `AuditEngagement`

The audit initiation sequence is: `AuditPlan → AuditMemo (approved) → AuditEngagement`. The memo (FK to `AuditPlan + AuditableEntity`) is the formal authorisation instrument, not a child of the engagement. An engagement only comes into existence **after** the memo is approved. `DeclarationOfIndependence` has an optional FK to `AuditMemo` to preserve this link.

#### Partial unique constraint on `AuditUniverse`

Only one `AuditUniverse` may be active per `FiscalYear`:
```python
models.UniqueConstraint(
    fields=['fiscal_year'],
    condition=models.Q(is_active=True),
    name='grc_audit_universe_active_fiscal_year_uniq',
)
```
Soft-deleting (setting `is_active=False`) releases the constraint and allows a new universe to be created.

#### Status state machines

Every entity with a `status` field uses an explicit `STATUS_CHOICES` list — a closed set of values rather than free text. The full sets for all entities:

| Entity | Status Choices |
|---|---|
| `AuditUniverse` | `draft → under_review → approved → archived` |
| `RiskAssessment` | `draft → submitted → reviewed → approved` |
| `AuditPlan` | `draft → management_review → committee_review → approved → implementation` |
| `AuditEngagement` | `planning → fieldwork → reporting → completed` |
| `AuditMemo` | `draft → cia_review → dg_review → approved → transmitted` |
| `WorkingPaper` (`review_status`) | `draft → pending → reviewed → approved` |
| `AuditFinding` | `draft → discussed → final` |
| `AuditRecommendation` | `open → in_progress → implemented → verified → closed` |
| `ImplementationMonitoring` | `active → closed` |
| `AuditeeFollowUpResponse` | `pending → submitted → verified → rejected` |
| `AuditReport` | `draft → under_review → approved → distributed` |
| `AuditMeeting` | `scheduled → in_progress → completed → cancelled` |
| `QuarterlyAuditReport` | `draft → cia_review → management_review → committee_review → improvement_required → approved → submitted_to_commission` |
| `DeclarationOfIndependence` | `pending → signed → waived` |
| `AuditSurvey` | `draft → completed` |
| `RiskControlMatrix` | `draft → submitted → approved` |
| `AuditProgram` | `draft → under_review → approved` |
| `EngagementNotification` | `draft → under_review → approved → transmitted` |

---

## 5. Lookup Tables

Lookup tables are managed by admins and consumed by all entities. They all follow the same pattern:
- Inherit `TimestampedModel + StatusMixin`
- Have a unique `code` field (slug-style, e.g., `'critical'`, `'control_weakness'`)
- Have a `name` field (display label)
- Have `sort_order` for UI ordering
- Have `is_active` for soft-disabling

### FiscalYear
- `year_code`: `'2024/2025'` — unique key
- `start_date` / `end_date`: actual date boundaries
- `get_current_fiscal_year()`: classmethod returns active year for today's date

### Quarter
- FK to `FiscalYear`
- `quarter_number`: 1–4 (validated)
- `get_current_quarter()`: classmethod returns active quarter for today's date

### RiskRating
- Has `numerical_value` for score sorting/comparison
- Has `min_score` / `max_score` for threshold-based auto-classification
- `classify_score(score)`: static method on `RiskAssessment` — maps a decimal score to the correct `RiskRating` by threshold range, with fallback to nearest `numerical_value`

### AuditSeverity / FindingType / AuditOpinion
- Standard code/name/description lookup with `color_code` for UI badge styling

---

## 6. Workflow Integration

### 6.1 How Workflows Work

Six entity types carry `WorkflowMixin` and integrate with the external Work Orchestration Service:

| Entity | Workflow Template Code | Stages |
|---|---|---|
| `AuditUniverse` | `grc.audit_universe_approval` | `cia_review` (1 stage) |
| `AuditPlan` | `grc.rbiap_approval` | `cia_review → management_review → committee_review → commission_noting` (4 stages) |
| `AuditEngagement` | `grc.engagement_lifecycle` | `planning → fieldwork → reporting` (3 stages) |
| `WorkingPaper` | `grc.working_paper_approval` | `working_paper_review → working_paper_approval` (2 stages) |
| `AuditMemo` | `grc.audit_memo_approval` | `cia_memo_review → dg_memo_approval` (2 stages) |
| `AuditProgram` | `grc.audit_program_approval` | `ia_program_review → cia_program_approval` (2 stages) |
| `AuditReport` | `grc.audit_report_approval` | `ia_report_review → cia_report_approval` (2 stages) |
| `EngagementNotification` | `grc.engagement_notification_approval` | `cia_approval` (1 stage) |
| `QuarterlyAuditReport` | `grc.quarterly_report_approval` | `cia_qr_review → management_qr_review → committee_qr_review → commission_qr_noting` (4 stages) |

### 6.2 Workflow YAML Templates

All templates are defined in `apps/core/workflows/workflows.yaml`. Every template uses consistent field naming per the Work Orchestration Service contract:

```yaml
- code: "grc.rbiap_approval"
  name: "RBIAP Approval"
  workflow_type: "grc"
  version: 2
  definition:
    description: "…"
    sla:
      targetMinutes: 40320
      breachStrategy: "escalate"
    metadata:
      module: "grc"
      category: "audit_plan"
    stages:
      - definitionKey: "cia_review"      # snake_case
        name: "CIA Review"
        order: 1
        assignees: ["role:chief_internal_auditor"]
        actions:
          - name: "approve"
            label: "Approve"
            nextState: "completed"     # camelCase
        sla:
          durationMinutes: 4320
          breachStrategy: "notify"
        metadata:
          status_on_complete: "management_review"  # GRC local status update
```

**Key conventions:**
- `definitionKey`: snake_case string
- `nextState`: camelCase (`"completed"`, `"rejected"`, `"pending"`)
- `assignees`: uses `"role:role_name"` or `"{{context_variable}}"` template syntax
- `metadata.status_on_complete`: the local `status` value to set on the GRC entity when this stage completes

### 6.3 Inline Stage Definitions (Fallback)

# NOTE
#### Currently there is inline stage defined, but ccording to FIMS, Inline fallback are strictly Prohibited, All workflow will must done in Work-orchestration Console.


Each workflow entity also defines `get_workflow_stages()` on the model itself as a fallback when no pre-seeded YAML template exists in WO:

```python
class AuditPlan(TimestampedModel, StatusMixin, WorkflowMixin):
    def get_workflow_stages(self) -> list:
        return [
            {
                "definition_key": "cia_review",
                "name": "CIA Review",
                "order": 0,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve", "next_state": "completed"},
                    {"name": "return",  "label": "Return to Auditor", "next_state": "rejected"},
                ],
                "form_schema": {"fields": [{"name": "comments", "type": "textarea", "required": False}]},
                "sla": {"targetHours": 72},
            },
            …
        ]
```

> **Note:** In inline stages use `"next_state"` (snake_case). In YAML use `"nextState"` (camelCase). This matches the separate serializer contracts on the WO side.

### 6.4 Workflow Context and Metadata

Each workflow entity defines two methods:

**`get_workflow_context()`** — Variables passed to WO for resolving dynamic `{{variable}}` assignees:
```python
def get_workflow_context(self):
    return {
        "audit_plan_id": str(self.id),
        "prepared_by": str(self.prepared_by),
        "fiscal_year_id": str(self.fiscal_year_id),
    }
```

**`get_workflow_metadata()`** — Display data stored in the WO plan:
```python
def get_workflow_metadata(self):
    meta = {
        "entity_type": "audit_plan",
        "entity_id": str(self.id),
        "reference_number": self.reference_number,
        "title": self.title,
        "status": self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, "audit_plan")
```

`add_entity_detail_path_to_metadata()` appends `"entity_detail_path"` which is the frontend URL path for this entity type (defined in `workflow_entity_paths.py`).

### 6.5 Service Layer Workflow Methods

Each workflow-enabled entity has a corresponding service class in `apps/core/services/`:

```python
class AuditPlanService:
    WORKFLOW_TEMPLATE_CODE = "grc.rbiap_approval"

    def submit_for_approval(self, plan_id, submitter_id):
        plan = AuditPlan.objects.select_for_update().get(id=plan_id)
        context = plan.get_workflow_context()
        context['applicant_id'] = submitter_id  # FIMS pattern: set at service layer
        metadata = plan.get_workflow_metadata()
        result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(plan.id),
            metadata=metadata,
        )
        if result and result.plan_id:
            plan.start_workflow(plan_id=result.plan_id, initial_stage=result.current_stage_name, stage_id=result.current_stage_id)
            plan.status = "management_review"
            plan.save(update_fields=["workflow_plan_id", "workflow_stage", "workflow_stage_id", "workflow_started_at", "status"])

    def advance_workflow_stage(self, plan_id, action, actor_id, comment=''):
        …  # calls workflow_client.advance_stage(), then updates WorkflowMixin fields

    def get_workflow_status(self, plan_id):
        …  # returns dict with stages, current stage, available actions

    def get_workflow_history(self, plan_id):
        …  # returns list of workflow activity log entries

    def cancel_workflow_plan(self, plan_id, actor_id, reason=''):
        …  # calls workflow_client.cancel_plan(), marks entity complete_workflow()
```

### 6.6 Workflow-Related Endpoints (Per Workflow Entity)

Every workflow entity gets these 4 standard endpoints in addition to its CRUD endpoints:

| Endpoint | View | Purpose |
|---|---|---|
| `POST /<entity>/<pk>/submit/` | `*SubmitView` | Starts the WO workflow plan |
| `GET /<entity>/<pk>/workflow-status/` | `*WorkflowStatusView` | Returns current WO plan status + available actions |
| `GET /<entity>/<pk>/workflow-history/` | `*WorkflowHistoryView` | Returns WO activity log |
| `POST /<entity>/<pk>/workflow-action/` | `*WorkflowActionView` | Executes a WO stage action (approve, reject, etc.) |
| `POST /<entity>/<pk>/cancel-workflow/` | `*CancelWorkflowView` | Cancels the active WO plan |

---

## 7. API Layer Design Patterns

### 7.1 View Base Class

All views use **DRF `APIView`** directly — not `GenericAPIView`, `ModelViewSet`, or `ListCreateAPIView`. This is the FIMS standard for fine-grained control.

```python
from rest_framework.views import APIView

class AuditPlanListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_plan:view required.')
        elif request.method == 'POST':
            if not CanManageAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_plan:manage required.')
```

### 7.2 Standard List Endpoint Pattern

```python
def get(self, request):
    try:
        # 1. Parse query params for filtering
        fiscal_year_id = request.query_params.get('fiscal_year')
        status_filter = request.query_params.get('status')

        # 2. Build queryset with select_related
        queryset = AuditPlan.objects.select_related(
            'audit_universe', 'fiscal_year'
        ).all()

        # 3. Apply filters
        if fiscal_year_id:
            queryset = queryset.filter(fiscal_year_id=fiscal_year_id)

        # 4. Apply ordering (FIMS standard helper)
        ordering = get_ordering_param(
            request,
            default='-fiscal_year__start_date',
            allowed_fields=['created_at', 'status', 'reference_number']
        )
        queryset = queryset.order_by(ordering)

        # 5. Paginate (FIMS standard helper)
        page_data = paginate_queryset(queryset, request)

        # 6. Serialize
        serializer = AuditPlanSerializer(page_data["queryset"], many=True)

        # 7. Return standard paginated response
        return paginated_list_response(
            items=serializer.data,
            count=page_data["total"],
            page=page_data["page"],
            page_size=page_data["page_size"],
        )
    except Exception as e:
        logger.exception("Failed to retrieve audit plans")
        return server_error_response(
            message="Failed to retrieve audit plans",
            details=str(e) if settings.DEBUG else None,
        )
```

### 7.3 Standard Create Endpoint Pattern

```python
def post(self, request):
    try:
        serializer = AuditPlanSerializer(data=request.data)
        if serializer.is_valid():
            # Business rule validations BEFORE save
            audit_universe = get_object_or_404(AuditUniverse, id=serializer.validated_data['audit_universe_id'])
            if audit_universe.status != 'approved':
                return Response({"success": False, "error": {"message": "…", "code": "UNIVERSE_NOT_APPROVED"}}, status=400)

            # Auto-generate reference number if not provided
            reference_number = serializer.validated_data.get('reference_number')
            if not reference_number:
                year_code = fiscal_year.year_code.replace('/', '')
                count = AuditPlan.objects.filter(fiscal_year=fiscal_year).count()
                reference_number = f"RBIAP-{year_code}-{count + 1:03d}"

            # Duplicate check
            if AuditPlan.objects.filter(reference_number=reference_number).exists():
                return conflict_response(message="Reference number already exists")

            with transaction.atomic():
                plan = serializer.save(reference_number=reference_number, prepared_by=request.user_id)

            # Publish Kafka event
            messaging_service.publish_audit_plan_event(
                AUDIT_PLAN_EVENTS['CREATED'],
                {'audit_plan_id': str(plan.id), 'created_by': request.user_id}
            )

            return created_response(data=AuditPlanSerializer(plan).data)
        return validation_error_response(errors=serializer.errors)
    except Exception as e:
        logger.exception("Failed to create audit plan")
        return server_error_response(message="Failed to create audit plan", details=str(e) if settings.DEBUG else None)
```

### 7.4 Exception Handling Strategy

- All views wrap the entire handler in `try/except Exception`.
- Use `logger.exception(…)` to capture full tracebacks.
- Return `server_error_response()` with `details=str(e) if settings.DEBUG else None`.
- Specific handled errors (validation, not found, conflict) use the appropriate response helper before the catch-all.

---

## 8. Serializers

### 8.1 FK Pattern (Read + Write)

All foreign key fields follow a standard dual-field pattern:

```python
class AuditPlanSerializer(serializers.ModelSerializer):
    # Read: nested object returned in GET responses
    fiscal_year = FiscalYearSerializer(read_only=True)
    # Write: flat UUID accepted in POST/PATCH requests
    fiscal_year_id = serializers.UUIDField(write_only=True)
```

This allows the frontend to receive full nested objects on reads while sending simple UUIDs on writes — no extra round-trips required.

### 8.2 Auto-set Fields

Fields set programmatically in the view (not from request data) use `required=False` + `extra_kwargs`:

```python
class Meta:
    extra_kwargs = {
        'reference_number': {'required': False, 'allow_blank': True},  # Auto-generated in view
        'prepared_by': {'required': False}  # Set from request.user_id in view
    }
```

### 8.3 Computed Fields

Display-only computed fields use `SerializerMethodField`:
```python
working_paper_reference = serializers.SerializerMethodField()

def get_working_paper_reference(self, obj):
    if not obj.working_paper_id:
        return None
    return obj.working_paper.reference_number
```

### 8.4 Score Field Aliasing

For `RiskAssessment`, model fields `calculated_weighted_score` / `calculated_residual_score` are exposed to the frontend under aliases `auto_risk_score` / `auto_residual_score` using `source=`:
```python
auto_risk_score = serializers.DecimalField(
    source='calculated_weighted_score', max_digits=7, decimal_places=2, read_only=True
)
```

---

## 9. Pagination

Since all views use raw `APIView`, DRF's automatic pagination does not apply. Pagination is handled manually using helpers from `apps/api/utils/pagination.py`.

**Settings (from `config/settings.py`):**
- Default page size: `20`
- Maximum page size: `100`

**Query parameters accepted on every list endpoint:**
- `page` (int, 1-based, default: 1)
- `page_size` (int, default: 20, max: 100)
- `ordering` (string, prefix `-` for descending, e.g., `-created_at`)

**Usage:**
```python
from apps.api.utils.pagination import paginate_queryset, get_ordering_param

page_data = paginate_queryset(queryset, request)
# page_data keys: queryset, page, page_size, total, total_pages
```

**`get_ordering_param()`** validates the `ordering` query param against an `allowed_fields` whitelist to prevent arbitrary field injection:
```python
ordering = get_ordering_param(
    request,
    default='-created_at',
    allowed_fields=['created_at', 'status', 'reference_number', 'planned_start_date']
)
```

---

## 10. Response Envelope Standard

All API responses use a consistent envelope format from `apps/api/utils/response_helpers.py`.

### Success (single item)
```json
{
  "success": true,
  "data": { "id": "…", "title": "…" },
  "message": "Created successfully"
}
```

### Success (paginated list)
```json
{
  "success": true,
  "data": [ { "id": "…" }, { "id": "…" } ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 87,
    "total_pages": 5
  }
}
```

### Error
```json
{
  "success": false,
  "error": {
    "code": "UNIVERSE_NOT_APPROVED",
    "message": "Cannot create plan for unapproved audit universe",
    "details": null
  }
}
```

### Response Helper Functions

| Function | HTTP Status | Use Case |
|---|---|---|
| `success_response(data)` | 200 | Single item GET, status updates |
| `created_response(data)` | 201 | Resource creation |
| `updated_response(data)` | 200 | Resource updates |
| `deleted_response()` | 200 | Soft delete |
| `paginated_list_response(items, count, page, page_size)` | 200 | List endpoints |
| `error_response(message, code, details)` | 400 | Generic client errors |
| `not_found_response(message)` | 404 | Resource not found |
| `validation_error_response(errors)` | 400 | Serializer validation failures |
| `conflict_response(message)` | 409 | Duplicate / business rule conflict |
| `server_error_response(message, details)` | 500 | Unhandled exceptions |

---

## 11. Authentication and JWT

### 11.1 JWT Authentication Classes

Defined in `apps/api/authentication.py`:

**`IAMJWTAuthentication`** (extends `JWTAuthentication`):
- Validates tokens signed with the shared `JWT_SECRET_KEY` (same key used by IAM service).
- Creates an in-memory `User` object from JWT claims — no database call.
- Stores JWT claims on the user: `_jwt_permissions`, `_jwt_permissions_flat`, `_jwt_services`.

**`ServiceAuthentication`**:
- For service-to-service calls. Checks `X-Service-Token` header first.
- Falls back to `JWTAuthentication` if no service token present.

### 11.2 JWTPermissionMiddleware

Runs on every authenticated request (`apps/core/permission_middleware.py`):

1. Decodes the Bearer JWT using `settings.JWT_SECRET_KEY`
2. Checks the user has `'grc-service'` or `'grc'` in their `services` claim
3. Extracts `grc:*` permission codes and stores them on `request.grc_permissions`
4. Sets convenience attributes: `request.user_id`, `request.user_email`, `request.is_superuser`

Superusers get `request.grc_permissions = ['*']`.

Paths that skip the middleware: `/health/`, `/admin/`, `/static/`, `/media/`, `/api/v1/auth/`, `/api/v1/token/`, `/api/schema/`, `/api/docs/`.

---

## 12. Roles and Permissions (RBAC)

### 12.1 Permission Code Convention

All permission codes follow the pattern: `grc:{resource}:{action}`

They are declared in `config/permissions/grc-service.json` and are the single source of truth for all RBAC in this service.

### 12.2 Implemented Permission Codes

```
grc:audit_universe:view
grc:audit_universe:manage
grc:audit_universe:approve

grc:risk_assessment:conduct
grc:risk_assessment:review

grc:audit_plan:view
grc:audit_plan:manage
grc:audit_plan:approve

grc:audit_engagement:manage
grc:audit_engagement:view

grc:audit_finding:manage
grc:audit_finding:finalize

grc:audit_recommendation:manage

grc:implementation_monitoring:manage
grc:implementation_monitoring:respond       # auditee submits follow-up

grc:working_paper:manage
grc:audit_report:manage
grc:audit_report:approve

grc:audit_meeting:manage

grc:quarterly_report:manage
grc:quarterly_report:approve

grc:audit_memo:manage
grc:declaration:manage
grc:survey:manage
grc:rcm:manage
grc:audit_program:manage
grc:engagement_notification:manage

grc:audit_dashboard:view
grc:lookup:manage
```

### 12.3 Permission Class Structure

Each permission code has a dedicated Python class in `apps/api/permissions_jwt.py`:

```python
class CanManageAuditPlan(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_plan:manage')
```

`_check_grc_permission_locally()` checks `request.grc_permissions` (set by middleware) — **no HTTP calls**. If `request.grc_permissions == ['*']` the check always passes (superuser).

### 12.4 Generic Permission Classes

Three generic classes are available for ad-hoc use:
- `HasPermission('grc:audit_plan:approve')` — single code
- `HasAnyPermission(['grc:audit_plan:view', 'grc:audit_report:view'])` — any one
- `HasAllPermissions(['grc:audit_plan:view', 'grc:audit_plan:approve'])` — all required

### 12.5 RBAC in Views

Permission checks are done inside `check_permissions()` using method-specific branching:

```python
def check_permissions(self, request):
    super().check_permissions(request)  # enforces IsAuthenticated
    if request.method == 'GET':
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_plan:view required.')
    elif request.method == 'POST':
        if not CanManageAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_plan:manage required.')
```

---

## 13. URL Structure

All URLs are under `/api/v1/grc/audit/` (registered in `config/urls.py` and `apps/api/urls.py`).

### 13.1 URL Patterns Reference

```
# Universe
GET/POST  audit/universe/
GET/PUT/PATCH/DELETE  audit/universe/<pk>/
POST  audit/universe/<pk>/approve/
GET   audit/universe/<pk>/workflow-status/
GET   audit/universe/<pk>/workflow-history/
POST  audit/universe/<pk>/workflow-action/
POST  audit/universe/<pk>/cancel-workflow/

# Plans
GET/POST  audit/plans/
GET/PUT/PATCH/DELETE  audit/plans/<pk>/
POST  audit/plans/<pk>/submit/
POST  audit/plans/<pk>/approve/
GET   audit/plans/<pk>/workflow-status/
GET   audit/plans/<pk>/workflow-history/
POST  audit/plans/<pk>/workflow-action/
POST  audit/plans/<pk>/cancel-workflow/
POST  audit/plans/generate-draft/

# Entities
GET/POST  audit/entities/
GET/PUT/PATCH/DELETE  audit/entities/<pk>/

# Risk Assessments
GET/POST  audit/risk-assessments/
GET/PUT/PATCH/DELETE  audit/risk-assessments/<pk>/
POST  audit/risk-assessments/<pk>/submit/
POST  audit/risk-assessments/<pk>/review/
GET/DELETE  audit/risk-assessments/<pk>/evidence/
DELETE  audit/risk-assessments/<pk>/evidence/<document_id>/

# Engagements
GET/POST  audit/engagements/
GET/PUT/PATCH/DELETE  audit/engagements/<pk>/
POST  audit/engagements/<pk>/transition/
GET/PUT  audit/engagements/<pk>/team/
GET   audit/engagements/<pk>/workflow-status/
GET   audit/engagements/<pk>/workflow-history/
POST  audit/engagements/<pk>/workflow-action/
POST  audit/engagements/<pk>/cancel-workflow/

# Findings
GET/POST  audit/findings/
GET/PUT/PATCH/DELETE  audit/findings/<pk>/
POST  audit/findings/<pk>/finalize/
POST  audit/findings/<pk>/responses/

# Recommendations
GET/POST  audit/recommendations/
GET/PUT/PATCH/DELETE  audit/recommendations/<pk>/
POST  audit/recommendations/<pk>/status/
GET   audit/recommendations/overdue/

# Implementation Monitoring
GET/POST  audit/implementation-monitoring/
GET/PUT  audit/implementation-monitoring/<pk>/
POST  audit/implementation-monitoring/<pk>/review/
GET   audit/implementation-monitoring/due-reviews/
POST  audit/implementation-monitoring/<pk>/notify-auditee/
GET   audit/implementation-monitoring/non-responsive/
GET   audit/implementation-monitoring/<monitoring_id>/responses/

# Follow-up Responses
GET   audit/follow-up-responses/overdue/    # MUST come before <pk>/ route
GET/POST  audit/follow-up-responses/
GET/PUT  audit/follow-up-responses/<pk>/
POST  audit/follow-up-responses/<pk>/submit/
POST  audit/follow-up-responses/<pk>/verify/

# Working Papers
GET/POST  audit/engagements/<engagement_id>/working-papers/
GET/PUT/PATCH/DELETE  audit/working-papers/<paper_id>/
POST  audit/working-papers/<paper_id>/review/
… (workflow + evidence endpoints)

# Reports, Meetings, Quarterly Reports, Memos, Declarations, Surveys, RCM, Programs, EN
# (same CRUD + action pattern)

# Dashboard
GET  audit/dashboard/stats/

# Lookups
GET  audit/lookups/
GET  audit/fiscal-years/
GET  audit/quarters/
GET  audit/severities/
GET  audit/finding-types/
GET  audit/risk-ratings/
GET  audit/audit-opinions/
GET  audit/users-by-role/?role=chief_internal_auditor
```

### 13.2 Static vs. UUID Route Ordering

When a static segment and a `<uuid:pk>/` pattern share the same prefix, declare the static route first:
```python
# CORRECT — static 'overdue/' before UUID capture
path("follow-up-responses/overdue/", …),
path("follow-up-responses/", …),
path("follow-up-responses/<uuid:pk>/", …),
```

---

## 14. Service Layer (Business Logic)

### 14.1 Service Class Responsibilities

Service classes in `apps/core/services/` contain **workflow integration logic only**. They are not general-purpose business logic containers. A service class is created per workflow entity.

Standard methods on every service class:
- `submit_for_approval(entity_id, submitter_id)` — starts WO plan
- `get_workflow_status(entity_id)` — fetches current WO plan state
- `get_workflow_history(entity_id)` — fetches WO activity log
- `advance_workflow_stage(entity_id, action, actor_id, comment)` — executes WO action
- `cancel_workflow_plan(entity_id, actor_id, reason)` — cancels active WO plan

All workflow-modifying methods use `@transaction.atomic` and `select_for_update()` on the entity.

### 14.2 Business Rule Validations

Business rule checks (not serializer validation) live in the **view layer**, prior to calling `.save()`. Examples:
- Cannot create `AuditEngagement` unless parent `AuditPlan` is `approved` or `implementation`
- Cannot create `AuditPlan` unless parent `AuditUniverse` is `approved`
- Cannot finalize a `WorkingPaper` unless all required fields are complete
- Cannot submit `AuditReport` unless engagement is in `reporting` phase

### 14.3 Auto-Calculation on Save

`RiskAssessment.save()` automatically calculates weighted and residual risk scores on every save that touches score fields, using `DEFAULT_WEIGHTS`:

```python
DEFAULT_WEIGHTS = {
    'inherent_risk': 0.25,
    'control_effectiveness': 0.20,
    'financial_exposure': 0.15,
    'compliance_risk': 0.15,
    'operational_impact': 0.15,
    'reputational_risk': 0.10,
}
```

Residual score formula: `weighted_score × (1 − control_effectiveness / 10)`

The auto-calculated ratings populate `auto_overall_rating` and `auto_residual_rating`. If `rating_overridden=False`, these also populate the manual FK fields `overall_risk_rating` and `residual_risk_rating`. Callers can pass `update_fields` to skip score recalculation on status-only saves.

---

## 15. Domain Events (Kafka)

### 15.1 Event Class Pattern

All events are dataclasses in `apps/core/events/audit_events.py`, inheriting `GRCDomainEvent`:

```python
@dataclass
class AuditEngagementCreatedEvent(GRCDomainEvent):
    engagement_id: str = field(default='')
    engagement_title: str = field(default='')
    created_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.audit.engagement.created'
        self.aggregate_id = self.engagement_id

    def _get_event_data(self) -> dict:
        return {'engagement_id': self.engagement_id, …}
```

### 15.2 Event Types Published

| Event Type | Trigger |
|---|---|
| `grc.audit.engagement.created` | New engagement created |
| `grc.audit.engagement.updated` | Engagement updated |
| `grc.working.paper.created` | Working paper created |
| `grc.working.paper.submitted` | WP submitted for review |
| `grc.working.paper.approved` | WP approved |
| `grc.working.paper.rejected` | WP rejected |
| `grc.audit.finding.created` | Finding created |
| `grc.audit.finding.finalized` | Finding finalized (consumed by Risk Management) |

### 15.3 Publishing Pattern

Events are published via `messaging_service` from the view, after successful `.save()`:

```python
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_ENGAGEMENT_EVENTS

messaging_service.publish_audit_engagement_event(
    AUDIT_ENGAGEMENT_EVENTS['CREATED'],
    {'engagement_id': str(engagement.id), 'created_by': request.user_id}
)
```

---

## 16. Notification System

### 16.1 Architecture

GRC publishes notification events to Kafka. Work Orchestration Service consumes these events and delivers them through email/in-app channels after resolving user profiles from IAM.

Priority-based Kafka topics:
- `notifications-urgent` — for SLA breaches, security events
- `notifications-high` — for overdue follow-ups, escalations
- `notifications-normal` — for standard workflow notifications
- `notifications-low` — for informational updates

### 16.2 `NotificationPublisher.send_notification()`

```python
publisher.send_notification(
    template_code='grc.monitoring.overdue_response',
    recipients={
        'email': ['auditee@example.com'],
        'user_ids': ['uuid-of-auditee'],
    },
    context={
        'auditee': {'first_name': 'John', 'email': 'john@example.com'},
        'recommendation': {'reference_number': 'REC-001', 'title': '…'},
        'response_deadline': '2025-03-15 17:00',
        'detail_url': 'https://portal.fcc.go.tz/audit/…',
    },
    priority='high',
)
```

### 16.3 Idempotency

The publisher generates an idempotency key from `(template_code, recipient, entity_id, timestamp_to_minute)` to prevent duplicate notifications when tasks re-run.

### 16.4 Notification Template Definitions

Templates are defined in `apps/core/templates/notifications.yaml`. Each template has a `code`, `subject`, `body` (HTML), and supported `channels`.

---

## 17. Celery Background Tasks

Celery is configured in `config/celery.py` using `app.autodiscover_tasks()`. The Django settings namespace is `CELERY_`.

### 17.1 `grc.check_monitoring_deadlines`

File: `apps/core/tasks/monitoring_deadlines.py`
Schedule: Daily at 07:00
Purpose: Enforce the 5-day response window on implementation follow-up cycles.

**Logic:**
1. **Mark overdue:** `AuditeeFollowUpResponse` records past `response_deadline` with `is_overdue=False` → set `is_overdue=True`, send overdue notification to auditee
2. **Day-3 reminder:** Cycles notified ~3 days ago, not yet submitted → send reminder
3. **Day-7 escalation:** Cycles notified 7+ days ago, still pending + monitor not yet escalated → send escalation to CIA, set `monitoring.escalated=True`

User resolution for notifications is done via `IAMClient.get_user_profile(uuid)`. Safe fallback names are used if IAM is unavailable.

### 17.2 `grc.sync_organizational_data`

File: `apps/core/tasks/organizational_sync.py`
Triggered by Kafka consumer when Corporate Service publishes org changes.
Updates local `Directorate`, `Department`, `Unit` records.

### 17.3 `grc.generate_report`

File: `apps/core/tasks/report_generation.py`
Triggered when an `AuditReport` is approved.
Generates a PDF via Document Records Service and stores the `document_id` on the report.

---

## 18. External Service Clients

### 18.1 `OrchestrationClient`

File: `apps/infrastructure/external/orchestration_client.py`

All HTTP calls to Work Orchestration Service. Uses `X-Service-Token` header (never the user's JWT) for service-to-service auth. Actor identity is passed as `X-Actor-ID` for audit trail only.

Key methods:
- `start_workflow(template_code, context, initiator_id, subject_ref, metadata)` — looks up template by code, creates plan
- `get_plan(plan_id)` → `WorkflowPlanResult`
- `advance_stage(plan_id, stage_id, action, actor_id, comment)` → `StageActionResult`
- `get_plan_activity(plan_id)` → list of activity log entries
- `cancel_plan(plan_id, actor_id, reason)`

All methods return `None`/empty on error — they never raise exceptions to callers. Errors are logged.

### 18.2 `IAMClient`

File: `apps/infrastructure/external/iam_client.py`

Used for resolving user UUIDs to name/email for notifications. Key method:
- `get_user_profile(user_id)` → `{'first_name', 'last_name', 'email', …}` or `None`

### 18.3 `DocumentServiceClient`

File: `apps/infrastructure/external/document_service_client.py`

Used for submitting documents to Document Records Service and retrieving document URLs. Working papers store `document_id` (UUID) referencing a record in this service.

---

## 19. Organizational Data Sync

`Directorate`, `Department`, and `Unit` models in GRC are **cached copies** of data from Corporate Service. They are never edited directly in GRC.

Each has:
- `external_id` (UUID): the primary key in Corporate Service
- `last_sync` (DateTimeField auto_now): tracks freshness
- Org hierarchy: `Unit → Department → Directorate`

`AuditableEntity` can optionally FK to `Directorate` or `Unit` for organizational context. The `organizational_path` property returns a human-readable path string: `"Finance Directorate > Treasury Unit"`.

---

## 20. Auto-generated Reference Numbers

Reference numbers are auto-generated in view layer when not provided by the caller.

### Patterns

| Entity | Pattern | Example |
|---|---|---|
| `AuditPlan` | `RBIAP-{FYCODE}-{seq:03d}` | `RBIAP-20242025-001` |
| `AuditEngagement` | `ENG-{FYCODE}-{seq:03d}` | `ENG-20242025-007` |
| `AuditFinding` | `{seq} of Q{n} {FY}` | `125 of Q2 2023/2024` |
| `AuditRecommendation` | Business rule in view | — |
| `QuarterlyAuditReport` | `QTR-{FY}-Q{n}-{seq:03d}` | `QTR-2024/2025-Q3-001` |
| `AuditMeeting` | Auto-generated | — |

The fiscal year code is sanitized before embedding: `fiscal_year.year_code.replace('/', '')` to avoid slashes in the reference string.

Duplicate check is always performed before saving:
```python
if AuditPlan.objects.filter(reference_number=reference_number).exists():
    return conflict_response(message="Reference number already exists")
```

---

## 21. Business Logic Rules Summary

| Rule | Location |
|---|---|
| `AuditUniverse`: one active per `FiscalYear` | `UniqueConstraint` on model with `condition=Q(is_active=True)` |
| `AuditPlan` requires approved universe | View-layer validation |
| `AuditEngagement` requires approved/implementation plan | View-layer validation |
| `RiskAssessment` scores auto-calculated on save | `RiskAssessment.save()` override |
| `RiskRating` auto-classified by threshold ranges | `RiskAssessment.classify_score()` |
| `WorkingPaper` primary doc stored in Document Service | `document_id` UUID FK pattern |
| Finding `discussed_at`/`finalized_at` set on status transition | Action views |
| Follow-up cycle `response_deadline` = `notified_at` + 5 business days | `notify-auditee` view |
| Follow-up `is_overdue` set by Celery task | `check_monitoring_deadlines` |
| Escalation to CIA after 7 days non-response | `check_monitoring_deadlines` |
| Monitoring `latest_progress` denormalized on verify | `verify` view |
| Audit report `stamped_document_url` set after CIA approval | Report approval view |
| `AuditFinding` published as `grc.audit.finding.finalized` on report approval | Report service / Kafka |

---

## 22. Module Implementation Checklist

When implementing a **new module** in this service, follow this sequence:

### Step 1 — Models
- [ ] Inherit `TimestampedModel + StatusMixin` for every entity
- [ ] Add `WorkflowMixin` if the entity participates in a workflow
- [ ] Use `UUIDField` for all references to IAM users
- [ ] Use FK to lookup tables instead of `CharField(choices=…)` for standardized values
- [ ] Define `db_table` (`mod_{entity}` pattern)
- [ ] Define `STATUS_CHOICES` and `status` field if the entity has a lifecycle
- [ ] Add `db_index=True` on `status` field
- [ ] Add `get_workflow_context()`, `get_workflow_metadata()`, `get_workflow_stages()` if workflow
- [ ] Register entity path in `workflow_entity_paths.py`

### Step 2 — Lookup Tables
- [ ] Create lookup models in `lookups.py` following `FiscalYear` pattern
- [ ] Add serializers to `lookup_serializers.py`
- [ ] Add list endpoints to `config_urls.py`

### Step 3 — Serializers
- [ ] Create serializer in `audit_serializers.py`
- [ ] Use `FK = NestedSerializer(read_only=True)` + `FK_id = UUIDField(write_only=True)` pattern
- [ ] Mark auto-generated/programmatic fields as `required=False` in `extra_kwargs`

### Step 4 — Permissions
- [ ] Define permission codes in `config/permissions/grc-service.json`
- [ ] Create named permission classes in `permissions_jwt.py`

### Step 5 — Views
- [ ] Use `APIView` base class
- [ ] Implement `check_permissions()` with method-specific branching
- [ ] Follow the standard list/create/detail patterns
- [ ] Use `paginate_queryset()` + `paginated_list_response()` for all list views
- [ ] Use `select_related()` on all queryset fetches
- [ ] Use only the response helpers from `response_helpers.py`
- [ ] Wrap everything in `try/except`, use `logger.exception()`, return `server_error_response()`

### Step 6 — Workflow (if applicable)
- [ ] Add YAML template to `workflows.yaml`
- [ ] Create service class in `apps/core/services/` extending the standard pattern
- [ ] Add workflow endpoints (`submit`, `workflow-status`, `workflow-history`, `workflow-action`, `cancel-workflow`)

### Step 7 — URLs
- [ ] Add URL patterns to the appropriate `urls/` file
- [ ] Place static segment routes before `<uuid:pk>/` routes
- [ ] Register the URL file in `apps/api/urls.py`

### Step 8 — Events (if applicable)
- [ ] Define event dataclasses in `apps/core/events/`
- [ ] Add event type constants to `shared/constants/event_types.py`
- [ ] Publish events from views after successful operations

### Step 9 — Background Tasks (if applicable)
- [ ] Create Celery task in `apps/core/tasks/`
- [ ] Register in `config/settings.py` `CELERY_BEAT_SCHEDULE`
- [ ] Use `publisher.send_notification()` (not raw Kafka) for user-facing alerts

### Step 10 — Tests
- [ ] Add test file in `tests/`
- [ ] Cover: permission denied, happy path, validation errors, business rule violations
