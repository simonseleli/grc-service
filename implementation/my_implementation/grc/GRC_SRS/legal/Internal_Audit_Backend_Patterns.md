# Internal Audit — Backend Implementation Patterns
**Extracted from:** `grc-service/docs/GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md`
**Purpose:** Reusable pattern guide for implementing new modules (e.g., Legal) inside `grc-service`.
**Scope:** Patterns only — no redesign, no new features.

---

## Table of Contents

1. [Directory Structure Patterns](#1-directory-structure-patterns)
2. [Model Design Patterns](#2-model-design-patterns)
3. [Service Layer Patterns](#3-service-layer-patterns)
4. [Workflow Integration Approach](#4-workflow-integration-approach)
5. [API Layer Patterns](#5-api-layer-patterns)
6. [Serializer Patterns](#6-serializer-patterns)
7. [Pagination Approach](#7-pagination-approach)
8. [Response Format Structure](#8-response-format-structure)
9. [RBAC and Permission Enforcement](#9-rbac-and-permission-enforcement)
10. [Naming Conventions](#10-naming-conventions)
11. [Module Implementation Checklist](#11-module-implementation-checklist)

---

## 1. Directory Structure Patterns

### 1.1 Three-Layer Root Structure

Every module's code lives across three top-level app packages:

```
apps/
├── api/            ← HTTP interface layer only (views, serializers, URLs, auth, permissions)
├── core/           ← All business and domain logic (models, services, tasks, events, workflows)
└── infrastructure/ ← All external service adapters (HTTP clients, Kafka)
```

**Rule:** No business logic in `apps/api/`. No HTTP calls in `apps/core/`. Infrastructure code never imports from `apps/api/`.

---

### 1.2 `apps/api/` Sub-structure

```
apps/api/
├── apps.py                         # AppConfig (label: "api")
├── authentication.py               # IAMJWTAuthentication + ServiceAuthentication
├── exceptions.py                   # Custom DRF exception handler
├── permissions_jwt.py              # Named DRF permission class per permission code
│
├── decorators/
│   └── permissions.py              # @require_grc_permission(code) if needed
│
├── serializers/
│   ├── <module>_serializers.py     # One serializer file per module
│   ├── lookup_serializers.py       # All lookup table serializers
│   └── organizational_serializers.py
│
├── urls/
│   ├── urls.py                     # Root router — mounts each module's URL file
│   ├── <module>.py                 # All URL patterns for the module
│   ├── config_urls.py              # Admin config/lookup management
│   ├── organizational_urls.py
│   └── health.py
│
├── utils/
│   ├── pagination.py               # paginate_queryset(), get_ordering_param()
│   └── response_helpers.py        # All response envelope helpers
│
└── views/
    ├── <entity>_views.py           # One file per entity (or functional group)
    ├── config_views.py
    ├── lookup_views.py
    └── health_view.py
```

**Naming rule for view files:** `{entity_name}_views.py` — one file per entity or functional group.

---

### 1.3 `apps/core/` Sub-structure

```
apps/core/
├── apps.py
│
├── models/
│   ├── base.py                     # BaseModel, TimestampedModel, StatusMixin, WorkflowMixin
│   ├── lookups.py                  # All lookup/reference data models
│   ├── organizational.py           # Org-structure snapshot models
│   └── <module>_entities.py       # All business models for the module
│
├── migrations/                     # Auto-generated; never hand-edit
│
├── services/
│   └── <entity>_service.py        # One service file per workflow-enabled entity
│
├── tasks/
│   └── <purpose>.py               # One Celery task file per functional area
│
├── management/
│   └── commands/
│       ├── seed_lookup_data.py
│       ├── register_workflow_templates.py
│       ├── consume_grc_events.py
│       └── sync_organizational_data.py
│
├── events/
│   └── <module>_events.py         # Domain event dataclasses
│
├── notifications/
│   └── publisher.py               # NotificationPublisher (Kafka wrapper)
│
├── workflows/
│   ├── workflows.yaml             # YAML definitions for all workflow templates
│   └── registry.py               # WorkflowTemplateRegistry
│
├── templates/
│   ├── notifications.yaml         # Notification message templates
│   └── registry.py               # NotificationTemplateRegistry
│
├── utils/
│   └── pdf_generators.py          # WeasyPrint PDF generators (if needed)
│
├── kafka_producer.py              # GrcServiceKafkaProducer (lazily initialized)
├── kafka_permission_publisher.py  # Publishes permission catalog to IAM via Kafka
├── permission_middleware.py       # JWTPermissionMiddleware
├── permissions.py                 # GrcServicePermissions (loads grc-service.json)
└── workflow_entity_paths.py       # Maps entity type → frontend URL path
```

---

### 1.4 `apps/infrastructure/` Sub-structure

```
apps/infrastructure/
├── external/
│   ├── orchestration_client.py    # OrchestrationClient (Work Orchestration HTTP client)
│   ├── iam_client.py              # IAMClient (user profile resolution)
│   └── document_service_client.py # DocumentServiceClient
│
├── messaging/
│   ├── kafka_producer.py          # FIMSKafkaProducer base class
│   ├── kafka_consumer.py          # GRCKafkaConsumer
│   └── event_publisher.py         # publish_event() thin wrapper
│
└── services/
    └── messaging_service.py       # KafkaMessagingService (domain event publisher)
```

---

### 1.5 Supporting Top-Level Directories

```
config/
├── settings.py                    # All Django settings
├── celery.py                      # Celery app instance + beat schedule
├── urls.py                        # Root URL conf — mounts /api/v1/grc/
└── permissions/
    └── grc-service.json           # RBAC permission catalog (all permission codes)

shared/
├── constants/
│   └── event_types.py             # Kafka event type string constants
└── common/
    └── messaging/
        └── kafka_producer.py      # FIMSKafkaProducer base class (shared)

templates/
└── grc/
    └── *.html                     # WeasyPrint HTML templates (PDF output)

tests/
├── api/                           # API-level tests
├── infrastructure/                # Client integration tests
└── e2e/                           # End-to-end workflow tests
```

---

## 2. Model Design Patterns

### 2.1 Four Base Classes

**Source:** `apps/core/models/base.py`

All models inherit from one or more of these — never directly from `django.db.models.Model`.

#### `BaseModel`
```python
class BaseModel(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
```
- UUID primary keys — never auto-increment integers.
- `created_at` always indexed for `ORDER BY` performance.
- `updated_at` never set manually.

#### `TimestampedModel(BaseModel)`
```python
class TimestampedModel(BaseModel):
    created_by  = models.UUIDField()                       # required — IAM user UUID
    modified_by = models.UUIDField(null=True, blank=True)  # nullable
    class Meta:
        abstract = True
```
- Always store IAM user UUID — never names or emails.
- `created_by` is required (always set from `request.user_id` in the view before saving).
- Display data (names, emails) resolved at read time via `IAMClient`.

#### `StatusMixin`
```python
class StatusMixin(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)
    class Meta:
        abstract = True
```
- Soft-delete mechanism for every entity.
- Hard deletes are never performed.
- All default querysets include `.filter(is_active=True)`.

#### `WorkflowMixin`
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
- Mixed into entities managed by Work Orchestration Service.
- Mirrors WO plan state locally so basic status can be read without a WO round-trip.
- Provides properties: `has_workflow`, `has_active_workflow`, `is_workflow_completed`.
- Provides mutating methods: `start_workflow()`, `update_workflow_stage()`, `complete_workflow()`, `cancel_workflow()`, `clear_workflow()`.

**Override hooks** (`must be implemented on every concrete workflow entity:`):
- `get_workflow_context()` — all `{{variable}}` values used in YAML `assignees`
- `get_workflow_metadata()` — display data stored on the WO plan (reference, title, status, detail path)

---

### 2.2 Composition Pattern

```python
# Entity with a workflow (most common)
class MyEntity(TimestampedModel, StatusMixin, WorkflowMixin):
    ...

# Entity without a workflow
class MyChildEntity(TimestampedModel, StatusMixin):
    ...

# Write-once log table (no user tracking, no soft-delete)
class MySyncLog(BaseModel):
    ...
```

**Minimum base:** `TimestampedModel + StatusMixin`.
**Add `WorkflowMixin`** only when the entity participates in a WO workflow.
**Exception:** A child entity whose lifecycle is entirely controlled by its parent may omit `StatusMixin` (example: `RCMEntry` is governed by `RiskControlMatrix`).

---

### 2.3 Status State Machine Pattern

- Every entity with a lifecycle has an explicit `STATUS_CHOICES` tuple — never free text.
- The `status` field carries `db_index=True`.
- Status transitions are enforced in the view layer (not model `clean()` or `save()`).

```python
class MyEntity(TimestampedModel, StatusMixin, WorkflowMixin):
    STATUS_CHOICES = [
        ('draft',          'Draft'),
        ('under_review',   'Under Review'),
        ('approved',       'Approved'),
        ('archived',       'Archived'),
    ]
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
    )
```

---

### 2.4 FK vs OneToOneField Rule

Use `OneToOneField` (not `ForeignKey`) when exactly one child record can and must exist per parent. Django enforces DB uniqueness and enables direct reverse access (`parent.child`):

```python
# 1:1 — use OneToOneField
class AuditReport(TimestampedModel, StatusMixin, WorkflowMixin):
    engagement = models.OneToOneField(
        AuditEngagement, on_delete=models.CASCADE, related_name='report'
    )

# Many children per parent — use ForeignKey
class WorkingPaper(TimestampedModel, StatusMixin, WorkflowMixin):
    engagement = models.ForeignKey(
        AuditEngagement, on_delete=models.CASCADE, related_name='working_papers'
    )
```

---

### 2.5 Lookup Tables Over `choices=`

Standardized values (severity, status types, opinion types, periods, etc.) are always **separate FK-referenced models**, never `CharField(choices=…)`:

```python
# WRONG
severity = models.CharField(choices=[('critical', 'Critical'), ...])

# CORRECT
severity = models.ForeignKey(AuditSeverity, on_delete=models.PROTECT, null=True)
```

Lookup models follow this pattern:
- Inherit `TimestampedModel + StatusMixin`
- Have a unique `code` slug field (e.g., `'critical'`, `'control_weakness'`)
- Have `name` (display label) and optional `description`
- Have `sort_order` for UI ordering
- Have `is_active` inherited from `StatusMixin`
- May carry extra attributes (e.g., `color_code`, `numerical_value`, score thresholds)

---

### 2.6 UUID-Only IAM References

All references to users in any model are UUIDs only:

```python
created_by         = models.UUIDField()                    # from TimestampedModel
lead_auditor       = models.UUIDField(null=True)
responsible_party  = models.UUIDField(null=True)
declarant_user_id  = models.UUIDField()
```

**Rule:** Never store `user_name`, `user_email`, or `user_department` as persistent model fields. Resolve at read time via `IAMClient.get_user_profile(uuid)`.

---

### 2.7 JSONField for Flexible List/Dict Data

Use `JSONField` instead of join tables for list or dict data not requiring independent querying:

```python
audit_team          = models.JSONField(default=list)   # list of UUIDs
objectives          = models.JSONField(default=list)   # list of strings
evidence_documents  = models.JSONField(default=list)   # list of document_id UUIDs
form_schema         = models.JSONField(default=dict)
```

**Rule:** Include a comment block on each `JSONField` documenting the expected element schema.

---

### 2.8 Partial Unique Constraint Pattern (Conditional Uniqueness)

For "one active record per parent" constraints, use `UniqueConstraint` with `condition=Q(is_active=True)`:

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['fiscal_year'],
            condition=models.Q(is_active=True),
            name='grc_audit_universe_active_fiscal_year_uniq',
        )
    ]
```

Soft-deleting (`is_active=False`) releases the constraint and allows a new record.

---

### 2.9 Document Reference Pattern (DRS Integration)

Models that attach documents from the Document Records Service store only UUID references:

```python
document_id         = models.UUIDField(null=True, blank=True)    # DRS UUID after upload
stamped_document_url = models.URLField(blank=True, default='')   # DRS-stamped PDF URL
```

The combination of `document_id` + `stamped_document_url` is used for entities that generate formal PDF output (e.g., after approval).

---

### 2.10 `db_table` Convention

Every model explicitly sets `db_table` to avoid naming collisions:

```python
class Meta:
    db_table = 'grc_{entity_name}'   # e.g., 'grc_audit_plan', 'grc_audit_finding'
```

For the Legal module, use: `legal_{entity_name}` (e.g., `legal_meeting`, `legal_case_defendant`).

---

### 2.11 Auto-Calculation on `save()`

For entities requiring computed derived fields, override `save()`:

```python
def save(self, *args, **kwargs):
    # Skip if only updating unrelated fields
    update_fields = kwargs.get('update_fields')
    if update_fields and not (score_fields & set(update_fields)):
        super().save(*args, **kwargs)
        return

    # Re-calculate derived fields
    self.calculated_score = self._compute_score()
    super().save(*args, **kwargs)
```

`update_fields` optimization: callers can pass `update_fields` to skip heavy re-calculations on status-only saves.

---

### 2.12 Denormalized Header Pattern

When a parent entity has many child cycles and performance matters for dashboards, denormalize the "latest" state onto the parent header:

```python
class ImplementationMonitoring(TimestampedModel, StatusMixin):
    recommendation = models.OneToOneField(...)
    latest_progress = models.CharField(...)    # denormalized from latest child
    is_overdue      = models.BooleanField(default=False)  # denormalized flag
    auditee_responded_at = models.DateTimeField(null=True)
```

The child record (e.g., `AuditeeFollowUpResponse`) updates the parent header on each verification.

---

## 3. Service Layer Patterns

### 3.1 Service Class Scope

Service classes in `apps/core/services/` contain **workflow integration logic only** — one service class per workflow-enabled entity.

They are **not** general-purpose business logic containers. There is no generic `MyEntityService`. Only entities with WO workflows have a service class.

Business rule validation (e.g., "parent must be approved") lives in the **view layer**, not the service.

---

### 3.2 Service Class Template

```python
class MyEntityService:
    WORKFLOW_TEMPLATE_CODE = "grc.my_entity_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    def submit_for_approval(self, entity_id: str, submitter_id: str) -> dict:
        with transaction.atomic():
            entity = MyEntity.objects.select_for_update().get(id=entity_id)
            context = entity.get_workflow_context()
            context['applicant_id'] = submitter_id
            metadata = entity.get_workflow_metadata()
            result = self.workflow_client.start_workflow(
                template_code=self.WORKFLOW_TEMPLATE_CODE,
                context=context,
                initiator_id=submitter_id,
                subject_ref=str(entity.id),
                metadata=metadata,
            )
            if result and result.plan_id:
                entity.start_workflow(
                    plan_id=result.plan_id,
                    initial_stage=result.current_stage_name,
                    stage_id=result.current_stage_id,
                )
                entity.status = "under_review"   # first workflow status
                entity.save(update_fields=[
                    "workflow_plan_id", "workflow_stage",
                    "workflow_stage_id", "workflow_started_at", "status"
                ])
        return {"success": True}

    def advance_workflow_stage(self, entity_id: str, action: str, actor_id: str, comment: str = '') -> dict:
        ...  # calls workflow_client.advance_stage(), then entity.update_workflow_stage()

    def get_workflow_status(self, entity_id: str) -> dict:
        ...  # returns dict with stages, current stage, available actions

    def get_workflow_history(self, entity_id: str) -> list:
        ...  # returns list of WO activity log entries

    def cancel_workflow_plan(self, entity_id: str, actor_id: str, reason: str = '') -> dict:
        ...  # calls workflow_client.cancel_plan(), then entity.cancel_workflow()
```

---

### 3.3 Required Service Methods

Every service class exposes exactly these five methods:

| Method | Purpose |
|---|---|
| `submit_for_approval(entity_id, submitter_id)` | Starts the WO workflow plan |
| `get_workflow_status(entity_id)` | Fetches current WO plan state + available actions |
| `get_workflow_history(entity_id)` | Fetches WO activity log |
| `advance_workflow_stage(entity_id, action, actor_id, comment)` | Executes a WO stage action |
| `cancel_workflow_plan(entity_id, actor_id, reason)` | Cancels active WO plan |

---

### 3.4 `select_for_update()` Rule

All workflow-modifying service methods must acquire a row lock before reading the entity:

```python
entity = MyEntity.objects.select_for_update().get(id=entity_id)
```

This prevents concurrent workflow submissions on the same entity.

---

### 3.5 Business Rule Validation in Views (not Services)

View-layer validation pattern (before `.save()`):

```python
# Check parent state before saving child
parent = get_object_or_404(ParentEntity, id=serializer.validated_data['parent_id'])
if parent.status not in ('approved', 'active'):
    return error_response(
        message="Parent must be approved before creating this entity.",
        code="PARENT_NOT_APPROVED"
    )
```

---

### 3.6 Auto-Reference Number Generation in Views

Reference numbers are auto-generated in the view layer if not provided by the caller:

```python
reference_number = serializer.validated_data.get('reference_number')
if not reference_number:
    count = MyEntity.objects.filter(parent=parent).count()
    reference_number = f"ENT-{parent.year_code.replace('/', '')}-{count + 1:03d}"

# Always check for duplicates
if MyEntity.objects.filter(reference_number=reference_number).exists():
    return conflict_response(message="Reference number already exists")
```

---

## 4. Workflow Integration Approach

### 4.1 Workflow Template Definition (YAML)

All templates are defined in `apps/core/workflows/workflows.yaml`. Each template entry must include:

```yaml
- code: "grc.my_entity_approval"          # unique identifier
  name: "My Entity Approval"
  workflow_type: "grc"
  version: 2
  definition:
    description: "…"
    sla:
      targetMinutes: 10080              # overall SLA
      breachStrategy: "escalate"
    metadata:
      module: "grc"
      category: "my_entity"
    stages:
      - definitionKey: "reviewer_check"  # snake_case
        name: "Reviewer Check"
        order: 1
        assignees: ["role:some_role"]    # or "{{context_variable}}"
        actions:
          - name: "approve"
            label: "Approve"
            nextState: "completed"       # camelCase in YAML
          - name: "return"
            label: "Return"
            nextState: "rejected"
        sla:
          durationMinutes: 4320
          breachStrategy: "notify"
        metadata:
          status_on_complete: "approved"  # local entity status to set
```

**Convention rules:**
- `definitionKey`: always snake_case
- `nextState`: always camelCase in YAML (`completed`, `rejected`, `pending`)
- `assignees`: use `"role:role_code"` or `"{{variable_from_context}}"`
- `metadata.status_on_complete`: exact string matching the entity's `STATUS_CHOICES` value

> **Strict rule:** Inline fallback stages (`get_workflow_stages()`) are strictly prohibited per FIMS architecture. All workflows must be pre-registered in Work Orchestration console via the YAML file.

---

### 4.2 Workflow Context and Metadata Methods

Every workflow entity must override both hooks:

```python
class MyEntity(TimestampedModel, StatusMixin, WorkflowMixin):

    def get_workflow_context(self):
        """Variables for resolving {{variable}} assignees in the YAML template."""
        return {
            "entity_id":    str(self.id),
            "prepared_by":  str(self.created_by),
            # Add any {{variable}} referenced in the template's assignees
        }

    def get_workflow_metadata(self):
        """Display data stored on the WO plan."""
        meta = {
            "entity_type":        "my_entity",
            "entity_id":          str(self.id),
            "reference_number":   self.reference_number,
            "title":              self.title,
            "status":             self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, "my_entity")
```

---

### 4.3 Entity Path Registration

After adding a new workflow entity, register it in `apps/core/workflow_entity_paths.py`:

```python
ENTITY_PATHS = {
    "audit_plan":        "/audit/plans/{id}",
    "audit_engagement":  "/audit/engagements/{id}",
    # Add new entity here:
    "my_entity":         "/my-module/entities/{id}",
}
```

---

### 4.4 Workflow Management Command

Create a management command `register_workflow_templates.py` that verifies WO has the GRC templates. This command runs on deployment to ensure templates exist before any entity is submitted for approval.

---

### 4.5 Five Standard Workflow Endpoints Per Entity

```python
# In the module's URL file
path("my-entities/<uuid:pk>/submit/",           MyEntitySubmitView.as_view()),
path("my-entities/<uuid:pk>/workflow-status/",  MyEntityWorkflowStatusView.as_view()),
path("my-entities/<uuid:pk>/workflow-history/", MyEntityWorkflowHistoryView.as_view()),
path("my-entities/<uuid:pk>/workflow-action/",  MyEntityWorkflowActionView.as_view()),
path("my-entities/<uuid:pk>/cancel-workflow/",  MyEntityCancelWorkflowView.as_view()),
```

---

## 5. API Layer Patterns

### 5.1 View Base Class — Always Use `APIView`

```python
from rest_framework.views import APIView

class MyEntityListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    ...
```

**Never use:** `GenericAPIView`, `ModelViewSet`, `ListCreateAPIView`, or any `mixins`. Raw `APIView` is the FIMS standard for fine-grained control.

---

### 5.2 Permission Check Pattern

Permission checks go in `check_permissions()` with method-specific branching:

```python
def check_permissions(self, request):
    super().check_permissions(request)   # enforces IsAuthenticated first
    if request.method == 'GET':
        if not CanViewMyEntity().has_permission(request, self):
            self.permission_denied(request, message='grc:my_entity:view required.')
    elif request.method == 'POST':
        if not CanManageMyEntity().has_permission(request, self):
            self.permission_denied(request, message='grc:my_entity:manage required.')
```

---

### 5.3 Standard List View Pattern

```python
def get(self, request):
    try:
        # 1. Parse filter params
        status_filter = request.query_params.get('status')
        parent_id     = request.query_params.get('parent_id')

        # 2. Build queryset with select_related
        queryset = MyEntity.objects.select_related(
            'parent', 'fiscal_year'
        ).filter(is_active=True)

        # 3. Apply filters
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)

        # 4. Apply ordering (validated against whitelist)
        ordering = get_ordering_param(
            request,
            default='-created_at',
            allowed_fields=['created_at', 'status', 'reference_number']
        )
        queryset = queryset.order_by(ordering)

        # 5. Paginate
        page_data = paginate_queryset(queryset, request)

        # 6. Serialize
        serializer = MyEntitySerializer(page_data["queryset"], many=True)

        # 7. Return
        return paginated_list_response(
            items=serializer.data,
            count=page_data["total"],
            page=page_data["page"],
            page_size=page_data["page_size"],
        )
    except Exception as e:
        logger.exception("Failed to retrieve my entities")
        return server_error_response(
            message="Failed to retrieve my entities",
            details=str(e) if settings.DEBUG else None,
        )
```

---

### 5.4 Standard Create View Pattern

```python
def post(self, request):
    try:
        serializer = MyEntitySerializer(data=request.data)
        if serializer.is_valid():
            # Business rule checks (before save)
            parent = get_object_or_404(ParentEntity, id=serializer.validated_data['parent_id'])
            if parent.status != 'approved':
                return error_response(
                    message="Parent must be approved.",
                    code="PARENT_NOT_APPROVED"
                )

            # Auto-generate reference number
            ref = f"ENT-{parent.year_code}-{MyEntity.objects.count() + 1:03d}"
            if MyEntity.objects.filter(reference_number=ref).exists():
                return conflict_response(message="Reference number already exists")

            with transaction.atomic():
                entity = serializer.save(
                    reference_number=ref,
                    created_by=request.user_id
                )

            # Publish Kafka domain event
            messaging_service.publish_event(
                ENTITY_EVENTS['CREATED'],
                {'entity_id': str(entity.id), 'created_by': str(request.user_id)}
            )

            return created_response(data=MyEntitySerializer(entity).data)

        return validation_error_response(errors=serializer.errors)
    except Exception as e:
        logger.exception("Failed to create entity")
        return server_error_response(
            message="Failed to create entity",
            details=str(e) if settings.DEBUG else None,
        )
```

---

### 5.5 Exception Handling Rule

- **All** view handlers wrap the entire body in `try/except Exception`.
- Use `logger.exception(…)` — this captures the full traceback.
- Return `server_error_response()` with `details=str(e) if settings.DEBUG else None`.
- Specific handled errors (validation, not found, conflict) return appropriate response helpers before the catch-all.
- Never return raw exception messages in production.

---

### 5.6 `transaction.atomic()` Placement

Wrap create/update operations in `transaction.atomic()`:

```python
with transaction.atomic():
    entity = serializer.save(created_by=request.user_id)
```

Publish Kafka events **after** the `with` block (not inside) — do not roll back after a successful save because of a failed Kafka publish.

---

### 5.7 `select_related()` Rule

Always use `select_related()` on querysets to avoid N+1 queries:

```python
queryset = MyEntity.objects.select_related('fiscal_year', 'parent', 'created_by_role').all()
```

For many-to-many, use `prefetch_related()` instead.

---

## 6. Serializer Patterns

### 6.1 FK Dual-Field Pattern (Read + Write)

Every foreign key relationship uses a dual-field pattern:

```python
class MyEntitySerializer(serializers.ModelSerializer):
    # Read: nested serializer — returned in GET responses
    fiscal_year    = FiscalYearSerializer(read_only=True)
    parent         = ParentEntitySerializer(read_only=True)

    # Write: flat UUID — accepted in POST/PATCH requests
    fiscal_year_id = serializers.UUIDField(write_only=True)
    parent_id      = serializers.UUIDField(write_only=True)

    class Meta:
        model  = MyEntity
        fields = '__all__'
```

This lets the frontend receive full nested objects on reads while sending simple UUIDs on writes.

---

### 6.2 Auto-Set Fields Pattern

Fields set programmatically in the view (not from request data) use `required=False`:

```python
class Meta:
    model = MyEntity
    fields = '__all__'
    extra_kwargs = {
        'reference_number': {'required': False, 'allow_blank': True},  # auto-generated in view
        'created_by':       {'required': False},                        # set from request.user_id
        'modified_by':      {'required': False},                        # set in update views
    }
```

---

### 6.3 Computed / Display-Only Fields

Use `SerializerMethodField` for derived read-only values:

```python
parent_reference = serializers.SerializerMethodField()

def get_parent_reference(self, obj):
    if not obj.parent_id:
        return None
    return obj.parent.reference_number
```

---

### 6.4 Field Aliasing with `source=`

To expose a model field under a different API name:

```python
auto_risk_score = serializers.DecimalField(
    source='calculated_weighted_score',
    max_digits=7, decimal_places=2, read_only=True
)
```

---

### 6.5 Serializer File Organization

- One serializer file per module: `apps/api/serializers/<module>_serializers.py`
- All entity serializers for the module in this single file
- Lookup serializers stay in `lookup_serializers.py` (shared across all modules)
- Organizational structure serializers stay in `organizational_serializers.py`

---

## 7. Pagination Approach

### 7.1 Manual Pagination Helpers

Since all views use raw `APIView`, DRF's automatic pagination does not apply. Use the helpers from `apps/api/utils/pagination.py` on **every** list endpoint:

```python
from apps.api.utils.pagination import paginate_queryset, get_ordering_param

# Step 1: Validate and get ordering
ordering = get_ordering_param(
    request,
    default='-created_at',
    allowed_fields=['created_at', 'status', 'reference_number', 'title']
)
queryset = queryset.order_by(ordering)

# Step 2: Paginate
page_data = paginate_queryset(queryset, request)
# Returns dict: { queryset, page, page_size, total, total_pages }

# Step 3: Serialize the paginated slice
serializer = MyEntitySerializer(page_data["queryset"], many=True)

# Step 4: Return standard envelope
return paginated_list_response(
    items=serializer.data,
    count=page_data["total"],
    page=page_data["page"],
    page_size=page_data["page_size"],
)
```

---

### 7.2 Query Parameters

Every list endpoint accepts:

| Parameter | Type | Default | Max | Description |
|---|---|---|---|---|
| `page` | int | 1 | — | Page number (1-based) |
| `page_size` | int | 20 | 100 | Items per page |
| `ordering` | string | `-created_at` | — | Field name; prefix `-` for descending |

---

### 7.3 Ordering Validation (Security)

`get_ordering_param()` validates the `ordering` value against an explicit `allowed_fields` whitelist. This **prevents arbitrary field injection** (a potential information-disclosure vulnerability):

```python
ordering = get_ordering_param(
    request,
    default='-created_at',
    allowed_fields=['created_at', 'status', 'reference_number', 'title', 'due_date']
)
```

If the requested ordering field is not in the whitelist, the default is used silently.

---

### 7.4 Settings

```python
# config/settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
}
```

---

## 8. Response Format Structure

### 8.1 Standard Response Envelope

All responses use the envelope format from `apps/api/utils/response_helpers.py`. Never return raw serializer data directly.

#### Single item (GET / POST / PATCH)
```json
{
  "success": true,
  "data": { "id": "uuid", "title": "...", "status": "draft" },
  "message": "Created successfully"
}
```

#### Paginated list
```json
{
  "success": true,
  "data": [ { "id": "..." }, { "id": "..." } ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 87,
    "total_pages": 5
  }
}
```

#### Error (client)
```json
{
  "success": false,
  "error": {
    "code":    "PARENT_NOT_APPROVED",
    "message": "Parent entity must be approved before creating this record.",
    "details": null
  }
}
```

#### Error (server)
```json
{
  "success": false,
  "error": {
    "code":    "INTERNAL_SERVER_ERROR",
    "message": "Failed to create entity",
    "details": "KeyError: 'fiscal_year_id'"   // only in DEBUG mode
  }
}
```

---

### 8.2 Response Helper Functions

Import from `apps/api/utils/response_helpers.py` — use the correct helper for each case:

| Helper | HTTP Status | Use Case |
|---|---|---|
| `success_response(data, message=None)` | 200 | Single item GET, status update |
| `created_response(data)` | 201 | Resource creation (POST) |
| `updated_response(data)` | 200 | Resource update (PUT/PATCH) |
| `deleted_response()` | 200 | Soft delete |
| `paginated_list_response(items, count, page, page_size)` | 200 | List endpoints |
| `error_response(message, code, details=None)` | 400 | Generic client error |
| `not_found_response(message)` | 404 | Resource not found |
| `validation_error_response(errors)` | 400 | DRF serializer `.errors` |
| `conflict_response(message)` | 409 | Duplicates, business rule conflicts |
| `server_error_response(message, details=None)` | 500 | Unhandled exceptions |

**Never** return `Response(data, status=...)` directly. Always use one of these helpers.

---

### 8.3 Error Code Convention

Error `code` values are UPPER_SNAKE_CASE strings describing the specific problem:

- `PARENT_NOT_APPROVED`
- `REFERENCE_NUMBER_EXISTS`
- `WORKFLOW_ALREADY_ACTIVE`
- `QUORUM_NOT_MET`
- `INVALID_STATUS_TRANSITION`

These codes are used by the frontend for programmatic error handling.

---

## 9. RBAC and Permission Enforcement

### 9.1 Permission Code Convention

All permission codes follow the pattern: `grc:{resource}:{action}`

```
grc:my_entity:view
grc:my_entity:manage
grc:my_entity:approve
```

Declared in `config/permissions/grc-service.json` — the single source of truth.

---

### 9.2 `grc-service.json` Permission Entry Structure

```json
{
  "permission_code": "grc:my_entity:manage",
  "name": "Manage My Entity",
  "description": "Can create, edit, and submit my entity records",
  "resource_type": "my_entity",
  "action": "manage",
  "category": "my_module"
}
```

---

### 9.3 Named Permission Class Per Code

Each permission code has a dedicated Python class in `apps/api/permissions_jwt.py`:

```python
class CanViewMyEntity(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:my_entity:view')

class CanManageMyEntity(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:my_entity:manage')
```

`_check_grc_permission_locally()` reads `request.grc_permissions` — **no HTTP calls**. Superusers pass automatically (`grc_permissions == ['*']`).

---

### 9.4 Generic Permission Utilities (Ad-hoc)

```python
# Single code
HasPermission('grc:my_entity:approve')

# Any one of several
HasAnyPermission(['grc:my_entity:view', 'grc:other_entity:view'])

# All required simultaneously
HasAllPermissions(['grc:my_entity:view', 'grc:my_entity:approve'])
```

---

### 9.5 View-Level Enforcement Pattern

```python
class MyEntityListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewMyEntity().has_permission(request, self):
                self.permission_denied(request, message='grc:my_entity:view required.')
        elif request.method == 'POST':
            if not CanManageMyEntity().has_permission(request, self):
                self.permission_denied(request, message='grc:my_entity:manage required.')

class MyEntityDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageMyEntity().has_permission(request, self):
                self.permission_denied(request, message='grc:my_entity:manage required.')
        elif request.method == 'GET':
            if not CanViewMyEntity().has_permission(request, self):
                self.permission_denied(request, message='grc:my_entity:view required.')
```

---

### 9.6 Middleware — How Permissions Reach the View

`JWTPermissionMiddleware` (`apps/core/permission_middleware.py`) runs on every authenticated request:

1. Decodes Bearer JWT using shared `JWT_SECRET_KEY`
2. Validates the user has `'grc-service'` or `'grc'` in `services` claim
3. Extracts `grc:*` codes → stores on `request.grc_permissions`
4. Sets `request.user_id`, `request.user_email`, `request.is_superuser`

Skipped paths: `/health/`, `/admin/`, `/static/`, `/media/`, `/api/v1/auth/`, `/api/v1/token/`, `/api/schema/`, `/api/docs/`.

---

### 9.7 Permission Publishing to IAM

On service startup (via management command or `post_migrate` signal):

```python
from apps.core.kafka_permission_publisher import PermissionPublisher
PermissionPublisher().publish()  # sends grc-service.json to 'service.permission.registry' topic
```

IAM consumes this and upserts `ServicePermission` records — the JWT then carries the codes in `permissions_flat`.

---

## 10. Naming Conventions

### 10.1 Model Naming

| Scope | Convention | Example |
|---|---|---|
| Model class | PascalCase noun | `CaseDefendant`, `MeetingDirective` |
| `db_table` | `{module}_{entity}` snake_case | `legal_case_defendant`, `legal_meeting` |
| Status choices | lowercase_snake_case | `'under_review'`, `'fully_closed'` |
| Status choice constant | All uppercase | `STATUS_CHOICES` |
| Lookup model | PascalCase noun (descriptive) | `RiskRating`, `FindingType` |

---

### 10.2 File Naming

| File Type | Convention | Example |
|---|---|---|
| View file | `{entity}_views.py` | `audit_plan_views.py`, `case_defendant_views.py` |
| Serializer file | `{module}_serializers.py` | `legal_serializers.py` |
| Service file | `{entity}_service.py` | `audit_plan_service.py`, `meeting_service.py` |
| URL file | module name or `{module}.py` | `legal.py`, `audit.py` |
| Event file | `{module}_events.py` | `legal_events.py` |
| Task file | descriptive purpose | `monitoring_deadlines.py`, `sync_organizational_data.py` |

---

### 10.3 Endpoint URL Naming

| Convention | Example |
|---|---|
| Plural kebab-case nouns | `audit/plans/`, `legal/cases/`, `legal/meetings/` |
| Actions as sub-paths after `<pk>/` | `plans/<pk>/submit/`, `cases/<pk>/close/` |
| Workflow endpoints follow the 5-endpoint standard | `<pk>/submit/`, `<pk>/workflow-status/`, etc. |
| Static segments before `<uuid:pk>/` in `urlpatterns` | `overdue/` before `<uuid:pk>/` |

---

### 10.4 Permission Code Naming

```
grc:{module_or_resource}:{action}
```

| Resource | Actions |
|---|---|
| Entity resources | `view`, `manage`, `approve` |
| Special operations | `conduct`, `respond`, `finalize`, `publish` |
| Dashboard | `view` |
| Lookup / config | `manage` |

---

### 10.5 Workflow Template Code Naming

```
grc.{module}_{entity}_approval
```

Examples: `grc.rbiap_approval`, `grc.working_paper_approval`, `grc.legal_filing_approval`, `grc.legal_minutes_approval`

---

### 10.6 Kafka Event Type Naming

```
grc.{module}.{entity}.{past_tense_verb}
```

Examples: `grc.audit.engagement.created`, `grc.audit.finding.finalized`, `grc.legal.case.registered`, `grc.legal.meeting.closed`

---

### 10.7 `db_table` Naming

For the Legal module: `legal_{entity_snake_case}`

| Entity | `db_table` |
|---|---|
| `Meeting` | `legal_meeting` |
| `CaseDefendant` | `legal_case_defendant` |
| `FilingDefendant` | `legal_filing_defendant` |
| `MeetingDirective` | `legal_meeting_directive` |
| `LitigationDirective` | `legal_litigation_directive` |

---

### 10.8 Service Class Naming

```
{EntityName}Service
```

Examples: `AuditPlanService`, `MeetingService`, `CaseDefendantService`, `FilingService`

---

## 11. Module Implementation Checklist

Use this checklist when starting any new module in grc-service:

### Step 1 — Models
- [ ] Create `apps/core/models/{module}_entities.py`
- [ ] Inherit `TimestampedModel + StatusMixin` for every entity
- [ ] Add `WorkflowMixin` only if the entity participates in a WO workflow
- [ ] Set `db_table = 'legal_{entity}'` on every model's `Meta`
- [ ] Use `UUIDField` for all IAM user references (never names/emails)
- [ ] Use FK to lookup tables — never `CharField(choices=…)` for standardized values
- [ ] Define `STATUS_CHOICES` + `status` field with `db_index=True` for all lifecycle entities
- [ ] Override `get_workflow_context()` and `get_workflow_metadata()` on workflow entities
- [ ] Register entity path in `workflow_entity_paths.py`
- [ ] Use `JSONField(default=list)` for list attributes not requiring independent querying
- [ ] Add `UniqueConstraint(condition=Q(is_active=True))` for conditional uniqueness rules

### Step 2 — Lookup Tables
- [ ] Add lookup models to `apps/core/models/lookups.py`
- [ ] Include: `code`, `name`, `description`, `sort_order`, `is_active`
- [ ] Add serializers to `apps/api/serializers/lookup_serializers.py`
- [ ] Add read-only list endpoints to `apps/api/urls/config_urls.py`

### Step 3 — Migrations
- [ ] Run `python manage.py makemigrations core`
- [ ] Verify migration file before applying

### Step 4 — Serializers
- [ ] Create `apps/api/serializers/legal_serializers.py`
- [ ] Use `FK = NestedSerializer(read_only=True)` + `FK_id = UUIDField(write_only=True)` on every FK
- [ ] Mark auto-generated/view-set fields as `required=False` in `extra_kwargs`

### Step 5 — Permissions
- [ ] Define permission codes in `config/permissions/grc-service.json`
- [ ] Add `category: "legal"` to all Legal module permissions
- [ ] Create one named permission class per code in `apps/api/permissions_jwt.py`

### Step 6 — Views
- [ ] Create `apps/api/views/{entity}_views.py` per entity (or logical group)
- [ ] Use `APIView` base class (never viewsets)
- [ ] Implement `check_permissions()` with method-specific branching
- [ ] Follow list/create/detail view patterns from §5
- [ ] Use `paginate_queryset()` + `paginated_list_response()` on all list views
- [ ] Use `select_related()` on all queryset fetches
- [ ] Only use response helpers from `response_helpers.py`
- [ ] Wrap entire handler in `try/except Exception` with `logger.exception()` + `server_error_response()`

### Step 7 — Workflow (if applicable)
- [ ] Add YAML template entry to `apps/core/workflows/workflows.yaml`
- [ ] Create service class in `apps/core/services/{entity}_service.py`
- [ ] Add the 5 standard workflow URL endpoints

### Step 8 — URLs
- [ ] Create `apps/api/urls/legal.py` (all Legal URL patterns)
- [ ] Place static routes before `<uuid:pk>/` routes
- [ ] Mount `legal.py` in `apps/api/urls/urls.py`

### Step 9 — Domain Events (if applicable)
- [ ] Define event dataclasses in `apps/core/events/legal_events.py` (inherit `GRCDomainEvent`)
- [ ] Add event type constants to `shared/constants/event_types.py`
- [ ] Publish events from views after successful saves (outside `transaction.atomic()`)

### Step 10 — Background Tasks (if applicable)
- [ ] Create Celery task file in `apps/core/tasks/`
- [ ] Register in `CELERY_BEAT_SCHEDULE` in `config/settings.py`
- [ ] Use `NotificationPublisher.send_notification()` for user-facing alerts

### Step 11 — Tests
- [ ] Create `tests/api/test_{module}.py`
- [ ] Cover: permission denied (403), happy path (201/200), validation errors (400), business rule violations, workflow transitions

---

*End of Pattern Guide*
*Source: GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md*
*Next use: Legal Module backend implementation*
