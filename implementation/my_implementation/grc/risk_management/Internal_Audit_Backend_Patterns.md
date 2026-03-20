# Internal Audit Backend Patterns

**Service:** `grc-service`  
**Source Module:** Internal Audit  
**Purpose:** Reusable backend patterns extracted from the Internal Audit implementation.  
Any new module in this service (e.g., Risk Management, Legal, Compliance) must follow these patterns exactly.

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

---

## 1. Directory Structure Patterns

### 1.1 Top-Level Service Layout

```
grc-service/
├── apps/
│   ├── api/          # HTTP interface layer (views, serializers, URLs, auth, permissions)
│   ├── core/         # Business domain (models, services, tasks, events, workflows)
│   └── infrastructure/  # External adapters (HTTP clients, Kafka producer/consumer)
├── config/           # Django project settings, Celery, root URL conf, RBAC catalog
├── shared/           # Cross-cutting constants and base utilities
├── templates/        # Django HTML templates for PDF generation (WeasyPrint)
└── tests/            # API, infrastructure, and end-to-end tests
```

### 1.2 `apps/api/` Structure

```
apps/api/
├── apps.py                    # Django AppConfig (AppLabel: "api")
├── authentication.py          # IAMJWTAuthentication + ServiceAuthentication
├── exceptions.py              # Custom DRF exception handler
├── permissions_jwt.py         # Named DRF permission classes (one class per permission code)
├── urls.py                    # Root URL router for the api app
├── decorators/
│   └── permissions.py         # @require_grc_permission(code) decorator
├── serializers/
│   ├── {module}_serializers.py    # All serializers for a module (e.g., audit_serializers.py)
│   ├── lookup_serializers.py      # Lookup table serializers (FiscalYear, severity, etc.)
│   └── organizational_serializers.py  # Org-structure serializers
├── urls/
│   ├── urls.py                # Root URL router — mounts module sub-routers
│   ├── {module}.py            # All URL patterns for one module (e.g., audit.py)
│   ├── config_urls.py         # Admin lookup management endpoints
│   ├── organizational_urls.py # Org-structure read endpoints
│   └── health.py              # GET /health/ liveness probe
├── utils/
│   ├── pagination.py          # paginate_queryset(), get_ordering_param()
│   └── response_helpers.py    # success_response(), paginated_list_response(), etc.
└── views/
    ├── {entity}_views.py      # One file per entity or functional group
    ├── config_views.py        # Lookup CRUD (admin)
    ├── lookup_views.py        # Read-only lookup endpoints (dropdowns)
    ├── organizational_views.py
    └── health_view.py
```

**Key rule:** One view file per entity or tightly related entity group. Never mix unrelated entities in a single view file.

### 1.3 `apps/core/` Structure

```
apps/core/
├── apps.py
├── models/
│   ├── base.py              # BaseModel, TimestampedModel, StatusMixin, WorkflowMixin
│   ├── lookups.py           # Shared lookup tables (FiscalYear, Quarter, severity types, etc.)
│   ├── organizational.py    # Org structure replicas (Directorate, Department, Unit, Section)
│   └── {module}_entities.py # All business models for one module (e.g., audit_entities.py)
├── migrations/              # Auto-generated Django migrations
├── services/
│   └── {entity}_service.py  # One workflow service class per workflow-enabled entity
├── tasks/
│   └── {task_name}.py       # One Celery task file per background concern
├── events/
│   └── {module}_events.py   # Domain event dataclasses
├── notifications/
│   └── publisher.py         # NotificationPublisher — wraps Kafka for notifications
├── workflows/
│   ├── workflows.yaml        # YAML definitions for all workflow templates
│   └── registry.py          # WorkflowTemplateRegistry — loads templates by code
├── templates/
│   ├── notifications.yaml    # Notification message templates
│   └── registry.py          # NotificationTemplateRegistry
├── utils/
│   └── pdf_generators.py    # WeasyPrint PDF generators
├── management/
│   └── commands/            # Django management commands (seed data, register workflows, etc.)
├── kafka_producer.py
├── kafka_permission_publisher.py
├── permission_middleware.py
├── permissions.py
└── workflow_entity_paths.py  # Maps entity type → frontend detail URL path
```

### 1.4 `apps/infrastructure/` Structure

```
apps/infrastructure/
├── external/
│   ├── orchestration_client.py    # HTTP client for work-orchestration-service
│   ├── iam_client.py              # HTTP client for iam-service
│   └── document_service_client.py # HTTP client for document-records-service
├── messaging/
│   ├── kafka_producer.py          # FIMSKafkaProducer base class
│   ├── kafka_consumer.py          # GRCKafkaConsumer
│   └── event_publisher.py         # publish_event() thin wrapper
└── services/
    └── messaging_service.py       # KafkaMessagingService — publishes domain events
```

### 1.5 Folder Naming Rules

| Layer | Naming Rule | Example |
|---|---|---|
| Model file per module | `{module}_entities.py` | `audit_entities.py`, `risk_entities.py` |
| Serializer file per module | `{module}_serializers.py` | `audit_serializers.py` |
| View file per entity | `{entity}_views.py` | `audit_plan_views.py`, `audit_finding_views.py` |
| URL file per module | `{module}.py` (under `urls/`) | `audit.py`, `risk.py` |
| Service file per workflow entity | `{entity}_service.py` | `audit_plan_service.py` |
| Task file per background concern | `{concern}.py` | `monitoring_deadlines.py` |

---

## 2. Model Design Patterns

### 2.1 The Four Base Classes

All base classes are defined in `apps/core/models/base.py`. No concrete model inherits directly from `django.db.models.Model`.

#### `BaseModel`
```python
class BaseModel(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```
- All primary keys are **UUID** — never auto-increment integers.
- `created_at` carries `db_index=True` for efficient `ORDER BY created_at` queries.
- `updated_at` is set automatically; never set it manually.

#### `TimestampedModel(BaseModel)`
```python
class TimestampedModel(BaseModel):
    created_by  = models.UUIDField()                       # required — IAM user UUID
    modified_by = models.UUIDField(null=True, blank=True)  # nullable — IAM user UUID

    class Meta:
        abstract = True
```
- `created_by` is **required** (no `null=True`). Always set from `request.user_id` in the view before saving.
- Both fields store **IAM user UUIDs only** — never Django auth IDs, names, or emails.
- User display data is resolved at read time via `IAMClient.get_user_profile()`.

#### `StatusMixin`
```python
class StatusMixin(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True
```
- Provides the **soft-delete flag**. Hard deletes are never performed.
- All default querysets must include `.filter(is_active=True)` unless explicitly retrieving deleted records.

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
- Mixed in only when the entity's lifecycle is managed by Work Orchestration Service.
- Mirrors WO plan state locally so basic status can be read without a WO round-trip.

### 2.2 Composition Pattern

Concrete models compose from the base classes. `StatusMixin` and `WorkflowMixin` both inherit `models.Model` themselves, so they must not inherit `BaseModel` — `TimestampedModel` provides the `BaseModel` chain.

```python
# Entity that participates in a workflow
class AuditPlan(TimestampedModel, StatusMixin, WorkflowMixin):
    …

# Entity that does not have a workflow
class AuditFinding(TimestampedModel, StatusMixin):
    …

# Rare: write-once log table inheriting only BaseModel
class OrganizationalSyncLog(BaseModel):
    …
```

**Composition rule:** `TimestampedModel + StatusMixin` is the minimum base for every entity. Add `WorkflowMixin` only if the entity participates in a WO workflow. The only exception to omitting `StatusMixin` is when a child entity's lifecycle is fully governed by its parent (e.g., `RCMEntry`).

### 2.3 WorkflowMixin Required Overrides

Every model that mixes in `WorkflowMixin` must override two methods:

```python
def get_workflow_context(self) -> dict:
    """
    Returns variables passed to WO for resolving dynamic {{variable}} assignees.
    Must include all template variable slots declared in workflows.yaml assignees.
    """
    return {
        "entity_type_id": str(self.id),
        "prepared_by": str(self.prepared_by),
        "fiscal_year_id": str(self.fiscal_year_id),
    }

def get_workflow_metadata(self) -> dict:
    """
    Returns display data stored in the WO plan (reference_number, title, status,
    entity_detail_path). Used by the frontend to link back to the entity.
    """
    meta = {
        "entity_type": "entity_snake_name",
        "entity_id": str(self.id),
        "reference_number": self.reference_number,
        "title": self.title,
        "status": self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, "entity_snake_name")
```

Register the entity type → frontend path mapping in `workflow_entity_paths.py`.

### 2.4 WorkflowMixin Mutating Methods (do not reimplement — use as-is)

| Method | Signature | When to Call |
|---|---|---|
| `start_workflow()` | `(plan_id, initial_stage='', stage_id=None)` | After WO returns a plan ID |
| `update_workflow_stage()` | `(stage_name, stage_id=None)` | After WO advances a stage |
| `complete_workflow()` | `()` | When WO plan reaches approved/noted state |
| `cancel_workflow()` | `()` | When WO plan is cancelled |
| `clear_workflow()` | `()` | When a workflow must be fully restarted |

### 2.5 Status State Machines

Every entity with a lifecycle must define a closed `STATUS_CHOICES` list with explicit, snake_case string values.

```python
STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('under_review', 'Under Review'),
    ('approved', 'Approved'),
    ('archived', 'Archived'),
]
status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default='draft',
    db_index=True,
)
```

- Never use free-text status values.
- `db_index=True` on `status` is mandatory for efficient filtering.

### 2.6 Key Design Rules

#### UUID-only user references
Fields referencing IAM users (e.g., `lead_auditor`, `prepared_by`, `responsible_party`) must store **only a UUID**. Never store names or emails in model fields.

#### Lookup tables, not `choices=`
Severity, classification, type codes, fiscal periods, and rating values must be FK-referenced models — not `CharField(choices=…)`. This keeps values admin-configurable without a code deployment.

#### JSONField for flexible list/dict data
Use `JSONField(default=list)` or `JSONField(default=dict)` for arrays and structured objects that do not require independent querying (e.g., team members, objectives, attendees, action items). Include a comment documenting the expected element schema.

#### OneToOneField for strict 1:1 child entities
When a child entity can exist at most once per parent, use `OneToOneField` — not `ForeignKey`. This enforces uniqueness at the database level and enables direct reverse access (`parent.child`).

#### UniqueConstraint with condition for nullable partial uniqueness
Use conditional `UniqueConstraint` (not `unique_together`) when uniqueness must apply only among active records:
```python
models.UniqueConstraint(
    fields=['fiscal_year'],
    condition=models.Q(is_active=True),
    name='mod_entity_active_field_uniq',
)
```

#### Auto-calculation on `save()`
When a model contains computed/derived fields (e.g., weighted scores, ratings), override `save()` to recalculate them automatically. Check `update_fields` to skip recalculation on status-only saves.

#### `db_table` naming
Every model must declare `db_table` using the pattern `grc_{entity_snake_name}` (e.g., `grc_audit_plan`, `grc_risk_register`).

### 2.7 Lookup Table Pattern

All lookup tables follow the same structure:
- Inherit `TimestampedModel + StatusMixin`
- Unique `code` field (slug-style, e.g., `'critical'`, `'control_weakness'`)
- `name` field for display label
- `sort_order` for UI ordering
- `is_active` for soft-disabling (via `StatusMixin`)

```python
class AuditSeverity(TimestampedModel, StatusMixin):
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color_code  = models.CharField(max_length=7, blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_audit_severity'
        ordering = ['sort_order']
```

---

## 3. Service Layer Patterns

### 3.1 Service Class Responsibility

Service classes in `apps/core/services/` contain **workflow integration logic only**. They are not general-purpose business logic containers. Create one service class per entity that has a workflow.

Non-workflow business rule validations (e.g., "AuditPlan requires approved AuditUniverse") belong in the **view layer**, not the service layer.

### 3.2 Standard Service Class Structure

```python
import logging
from django.db import transaction
from apps.core.models import MyEntity
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class MyEntityService:
    WORKFLOW_TEMPLATE_CODE = "grc.my_entity_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(self, entity_id: str, submitter_id: str):
        entity = MyEntity.objects.select_for_update().get(id=entity_id)

        if entity.workflow_plan_id:
            logger.info("MyEntity %s already has workflow — skipping", entity.id)
            return entity

        context = entity.get_workflow_context()
        context['applicant_id'] = submitter_id   # FIMS: always set at service layer

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
                initial_stage=result.current_stage_name or '',
                stage_id=result.current_stage_id,
            )
            entity.status = "under_review"   # first stage's status_on_complete value
            entity.save(update_fields=[
                "workflow_plan_id", "workflow_stage", "workflow_stage_id",
                "workflow_started_at", "status",
            ])
        else:
            logger.error("Failed to start workflow for MyEntity %s", entity.id)

        return entity

    def get_workflow_status(self, entity_id: str):
        entity = MyEntity.objects.get(id=entity_id)
        if not entity.workflow_plan_id:
            return None
        plan = self.workflow_client.get_plan(str(entity.workflow_plan_id))
        if not plan:
            return {'has_workflow': True, 'workflow_plan_id': str(entity.workflow_plan_id), 'status': 'unknown'}
        current_stage_data = next(
            (s for s in plan.stages if s.get('id') == plan.current_stage_id), None
        )
        return {
            'has_workflow': True,
            'plan_id': plan.plan_id,
            'status': plan.status,
            'current_stage': plan.current_stage_name,
            'current_stage_id': plan.current_stage_id,
            'current_stage_data': current_stage_data,
            'available_actions': current_stage_data.get('actions', []) if current_stage_data else [],
            'stages': plan.stages,
            'is_completed': plan.status in ('completed', 'cancelled'),
        }

    def get_workflow_history(self, entity_id: str):
        entity = MyEntity.objects.get(id=entity_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

    @transaction.atomic
    def advance_workflow_stage(self, entity_id: str, action: str, actor_id: str, comment: str = '') -> dict:
        entity = MyEntity.objects.select_for_update().get(id=entity_id)

        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this entity")

        plan = self.workflow_client.get_plan(str(entity.workflow_plan_id))
        stage_id = getattr(entity, 'workflow_stage_id', None) or plan.current_stage_id

        result = self.workflow_client.advance_stage(
            plan_id=str(entity.workflow_plan_id),
            stage_id=str(stage_id),
            action=action,
            actor_id=actor_id,
            comment=comment,
        )

        if not result:
            raise ValueError("Failed to execute workflow action")

        if result.next_stage_id:
            entity.update_workflow_stage(stage_name=result.next_stage_name or '', stage_id=result.next_stage_id)

        if result.plan_status in ('completed', 'cancelled'):
            entity.complete_workflow()

        entity.save()
        return {
            'action': action,
            'new_stage_status': result.new_status,
            'plan_status': result.plan_status,
            'next_stage': result.next_stage_name,
        }

    @transaction.atomic
    def cancel_workflow_plan(self, entity_id: str, actor_id: str, reason: str = ''):
        entity = MyEntity.objects.select_for_update().get(id=entity_id)

        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this entity")

        self.workflow_client.cancel_plan(
            plan_id=str(entity.workflow_plan_id),
            actor_id=actor_id,
            reason=reason,
        )
        entity.cancel_workflow()
        entity.save(update_fields=["workflow_completed_at"])
        return entity
```

### 3.3 Standard Service Methods Summary

| Method | transaction.atomic | select_for_update | Purpose |
|---|:---:|:---:|---|
| `submit_for_approval` | ✓ | ✓ | Start WO workflow plan |
| `get_workflow_status` | — | — | Fetch current WO plan state |
| `get_workflow_history` | — | — | Fetch WO activity log |
| `advance_workflow_stage` | ✓ | ✓ | Execute WO stage action |
| `cancel_workflow_plan` | ✓ | ✓ | Cancel active WO plan |

### 3.4 Business Rule Validation Placement

Business rule checks that are not pure serializer-field validation belong in the **view layer**, between `serializer.is_valid()` and the `.save()` call:

```python
# In the view's post() handler:
if serializer.is_valid():
    parent = get_object_or_404(ParentEntity, id=serializer.validated_data['parent_id'])
    if parent.status != 'approved':
        return error_response(
            message="Cannot create child for unapproved parent",
            code="PARENT_NOT_APPROVED",
        )
    # ... proceed to save
```

### 3.5 Auto-Calculation on Save

When derived fields must be recalculated from input fields, override `save()` on the model. Use `update_fields` to skip recalculation on unrelated saves:

```python
def save(self, *args, **kwargs):
    update_fields = kwargs.get('update_fields')
    score_fields = {'score_a', 'score_b', 'score_c'}
    if update_fields is None or score_fields.intersection(update_fields):
        self.calculated_score = self._compute_score()
        self.auto_rating = self._classify_score(self.calculated_score)
    super().save(*args, **kwargs)
```

---

## 4. Workflow Integration Approach

### 4.1 Workflow Templates (YAML)

All workflow templates live in `apps/core/workflows/workflows.yaml`. Each template follows this structure:

```yaml
templates:
  - code: "grc.entity_approval"
    name: "Entity Approval"
    workflow_type: "grc"
    version: 1
    definition:
      description: "Description of the workflow"
      sla:
        targetMinutes: 4320          # overall SLA in minutes
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "entity_category"
      stages:
        - definitionKey: "stage_one"       # snake_case
          name: "Stage One"
          order: 1
          assignees: ["role:role_name"]    # or ["{{context_variable}}"]
          actions:
            - name: "approve"
              label: "Approve"
              nextState: "completed"       # camelCase
            - name: "return"
              label: "Return"
              nextState: "rejected"
          sla:
            durationMinutes: 2880
            breachStrategy: "notify"
          metadata:
            status_on_complete: "next_status_value"  # GRC local status to set
```

**YAML field conventions:**
- `definitionKey`: always `snake_case`
- Action `nextState`: always `camelCase` (`"completed"`, `"rejected"`, `"pending"`)
- Assignees: `"role:role_name"` for static roles, `"{{variable_name}}"` for dynamic assignees resolved from context
- `metadata.status_on_complete`: the local `status` field value to set on the GRC entity when this stage completes

**Inline fallback (`get_workflow_stages()`) is strictly prohibited by FIMS.** All workflows must be defined in the Work Orchestration Console via the YAML templates.

### 4.2 Stage Management — Lifecycle Flow

1. View calls `service.submit_for_approval(entity_id, submitter_id)`
2. Service calls `entity.get_workflow_context()` to build the context dict
3. Service appends `'applicant_id': submitter_id` to context
4. Service calls `entity.get_workflow_metadata()` to build display data
5. Service calls `OrchestrationClient.start_workflow(template_code, context, initiator_id, subject_ref, metadata)`
6. On success: service calls `entity.start_workflow(plan_id, initial_stage, stage_id)` and updates `entity.status`
7. Service saves with explicit `update_fields=[…workflow fields…, "status"]`

When a stage advances:
1. View calls `service.advance_workflow_stage(entity_id, action, actor_id, comment)`
2. Service calls `OrchestrationClient.advance_stage(plan_id, stage_id, action, actor_id, comment)`
3. If the plan advances: service calls `entity.update_workflow_stage(stage_name, stage_id)`
4. If the plan completes/cancels: service calls `entity.complete_workflow()`
5. Service calls `entity.save()`

### 4.3 Workflow Endpoints Per Entity

Every workflow entity exposes exactly these 5 standard endpoints in addition to its CRUD endpoints:

| HTTP | Endpoint | View Class | Purpose |
|---|---|---|---|
| `POST` | `/<entity>/<pk>/submit/` | `*SubmitView` | Start the WO workflow plan |
| `GET` | `/<entity>/<pk>/workflow-status/` | `*WorkflowStatusView` | Return current WO plan status + available actions |
| `GET` | `/<entity>/<pk>/workflow-history/` | `*WorkflowHistoryView` | Return WO activity log |
| `POST` | `/<entity>/<pk>/workflow-action/` | `*WorkflowActionView` | Execute a WO stage action |
| `POST` | `/<entity>/<pk>/cancel-workflow/` | `*CancelWorkflowView` | Cancel the active WO plan |

### 4.4 Service Integration

- `OrchestrationClient` uses `X-Service-Token` for service-to-service auth (never the user's JWT)
- Actor identity is passed as `X-Actor-ID` header for audit trail only
- All `OrchestrationClient` methods return `None`/empty on error — they never raise exceptions to callers
- Errors are logged with `logger.error` or `logger.exception`

---

## 5. API Layer Patterns

### 5.1 View Base Class

All views use **DRF `APIView`** directly — not `GenericAPIView`, `ModelViewSet`, or `ListCreateAPIView`.

```python
from rest_framework.views import APIView

class EntityListCreateView(APIView):
    permission_classes = [IsAuthenticated]  # always required
```

### 5.2 Permission Enforcement in Views

Permissions are enforced inside `check_permissions()` using method-specific branching. The `IsAuthenticated` base check runs first via `super()`:

```python
def check_permissions(self, request):
    super().check_permissions(request)  # enforces IsAuthenticated first
    if request.method == 'GET':
        if not CanViewEntity().has_permission(request, self):
            self.permission_denied(request, message='grc:entity:view required.')
    elif request.method == 'POST':
        if not CanManageEntity().has_permission(request, self):
            self.permission_denied(request, message='grc:entity:manage required.')
    elif request.method in ('PUT', 'PATCH', 'DELETE'):
        if not CanManageEntity().has_permission(request, self):
            self.permission_denied(request, message='grc:entity:manage required.')
```

### 5.3 Standard List Endpoint Pattern

```python
def get(self, request):
    try:
        # 1. Parse query params for filtering
        filter_param = request.query_params.get('filter_field')
        status_filter = request.query_params.get('status')

        # 2. Build queryset with select_related
        queryset = MyEntity.objects.select_related('related_field', 'other_field').all()

        # 3. Apply filters
        if filter_param:
            queryset = queryset.filter(field=filter_param)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 4. Apply ordering (FIMS standard helper)
        ordering = get_ordering_param(
            request,
            default='-created_at',
            allowed_fields=['created_at', 'status', 'reference_number']
        )
        queryset = queryset.order_by(ordering)

        # 5. Paginate (FIMS standard helper)
        page_data = paginate_queryset(queryset, request)

        # 6. Serialize
        serializer = MyEntitySerializer(page_data["queryset"], many=True)

        # 7. Return standard paginated response
        return paginated_list_response(
            items=serializer.data,
            count=page_data["total"],
            page=page_data["page"],
            page_size=page_data["page_size"],
        )
    except Exception as e:
        logger.exception("Failed to retrieve entities")
        return server_error_response(
            message="Failed to retrieve entities",
            details=str(e) if settings.DEBUG else None,
        )
```

### 5.4 Standard Create Endpoint Pattern

```python
def post(self, request):
    try:
        serializer = MyEntitySerializer(data=request.data)
        if serializer.is_valid():
            # 1. Business rule validations BEFORE save
            parent_id = serializer.validated_data['parent_id']
            parent = get_object_or_404(ParentEntity, id=parent_id)
            if parent.status != 'approved':
                return error_response(
                    message="Parent must be approved",
                    code="PARENT_NOT_APPROVED",
                )

            # 2. Auto-generate reference number if needed
            reference_number = serializer.validated_data.get('reference_number')
            if not reference_number:
                reference_number = _generate_reference(...)

            # 3. Duplicate check
            if MyEntity.objects.filter(reference_number=reference_number).exists():
                return conflict_response(message="Reference number already exists")

            # 4. Get authenticated user
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                      status_code=status.HTTP_401_UNAUTHORIZED)

            # 5. Save inside atomic transaction
            with transaction.atomic():
                entity = serializer.save(
                    created_by=user_id,
                    reference_number=reference_number,
                )

            # 6. Publish Kafka event (best-effort — never fails the request)
            try:
                messaging_service.publish_entity_event(
                    event_type=ENTITY_EVENTS['CREATED'],
                    entity_id=entity.id,
                    additional_data={'created_by': str(user_id)},
                )
            except Exception as event_error:
                logger.error("Error publishing entity created event: %s", event_error)

            return created_response(data=MyEntitySerializer(entity).data)

        return validation_error_response(errors=serializer.errors)
    except Exception as e:
        logger.exception("Failed to create entity")
        return server_error_response(
            message="Failed to create entity",
            details=str(e) if settings.DEBUG else None,
        )
```

### 5.5 Exception Handling Strategy

- All view handlers wrap the entire body in `try/except Exception`.
- Use `logger.exception(…)` (not `logger.error`) to capture full tracebacks.
- Return `server_error_response()` with `details=str(e) if settings.DEBUG else None`.
- Specific handled errors (validation, not found, conflict, business rules) use the appropriate response helper before the catch-all.
- Kafka event publishing is always wrapped in its own inner `try/except` so event failures never fail the HTTP request.

### 5.6 Soft Delete Pattern

```python
def delete(self, request, pk):
    try:
        entity = get_object_or_404(MyEntity, id=pk)
        entity.is_active = False
        entity.modified_by = request.user_id
        entity.save(update_fields=['is_active', 'modified_by', 'updated_at'])
        return deleted_response(message="Entity deleted successfully")
    except Exception as e:
        logger.exception("Failed to delete entity")
        return server_error_response(message="Failed to delete entity",
                                     details=str(e) if settings.DEBUG else None)
```

---

## 6. Serializer Patterns

### 6.1 FK Dual-Field Pattern (Read + Write)

Every foreign key field follows this pattern: a read-only nested serializer for GET responses, and a write-only UUID field for POST/PATCH requests.

```python
class MyEntitySerializer(serializers.ModelSerializer):
    # Read: full nested object returned in GET
    parent_entity = ParentEntitySerializer(read_only=True)
    # Write: flat UUID accepted in POST/PATCH
    parent_entity_id = serializers.UUIDField(write_only=True)

    lookup_type = LookupTypeSerializer(read_only=True)
    lookup_type_id = serializers.UUIDField(write_only=True)
```

This allows the frontend to receive nested objects on reads without extra round-trips, while sending simple UUIDs on writes.

### 6.2 Auto-Set Fields (Programmatically Populated in Views)

Fields set by the view layer (not provided by the caller) must be marked `required=False` in `extra_kwargs`:

```python
class Meta:
    extra_kwargs = {
        'reference_number': {'required': False, 'allow_blank': True},  # Auto-generated in view
        'prepared_by':      {'required': False},                         # Set from request.user_id
        'created_by':       {'required': False},                         # Set from request.user_id
    }
```

### 6.3 Computed / Derived Fields

Use `SerializerMethodField` for display-only values that require computation at read time:

```python
parent_reference = serializers.SerializerMethodField()

def get_parent_reference(self, obj):
    if not obj.parent_id:
        return None
    return obj.parent.reference_number
```

### 6.4 Field Aliasing (source=)

When the model field name differs from the expected API field name, use `source=`:

```python
auto_risk_score = serializers.DecimalField(
    source='calculated_weighted_score',
    max_digits=7, decimal_places=2,
    read_only=True,
)
```

### 6.5 Document UUID List Fields

For fields that store a list of Document Records Service UUIDs:

```python
evidence_document_ids = serializers.ListField(
    child=serializers.UUIDField(),
    required=False,
    default=list,
    help_text="List of Document Records Service document UUIDs",
)
```

### 6.6 Serializer File Organisation

- All entity serializers for a module go in a single `{module}_serializers.py` file.
- Import lookup serializers from `lookup_serializers.py`.
- Import org serializers from `organizational_serializers.py`.
- Serializers referencing other entities within the same module inline the nested serializer directly (re-use imports rather than importing from `audit_serializers` into itself).

---

## 7. Pagination Approach

Since all views use raw `APIView`, DRF's automatic pagination does not apply. Pagination is handled manually using two helpers from `apps/api/utils/pagination.py`.

### 7.1 Settings

Configured in `config/settings.py` under `REST_FRAMEWORK`:
- Default page size: `20`
- Maximum page size: `100`

### 7.2 Query Parameters

Every list endpoint accepts:
- `page` — 1-based page number (default: `1`)
- `page_size` — items per page (default: `20`, max: `100`)
- `ordering` — field name with optional `-` prefix for descending (e.g., `-created_at`)

### 7.3 Usage Pattern

```python
from apps.api.utils.pagination import paginate_queryset, get_ordering_param

# Inside a GET handler:
ordering = get_ordering_param(
    request,
    default='-created_at',
    allowed_fields=['created_at', 'status', 'reference_number', 'planned_start_date']
)
queryset = queryset.order_by(ordering)

page_data = paginate_queryset(queryset, request)
# page_data keys: queryset, page, page_size, total, total_pages

serializer = MyEntitySerializer(page_data["queryset"], many=True)
return paginated_list_response(
    items=serializer.data,
    count=page_data["total"],
    page=page_data["page"],
    page_size=page_data["page_size"],
)
```

### 7.4 `get_ordering_param()` — Security Requirement

Always pass the `allowed_fields` whitelist to `get_ordering_param()`. This prevents arbitrary field injection through the `ordering` query parameter:

```python
ordering = get_ordering_param(
    request,
    default='-created_at',
    allowed_fields=['created_at', 'status', 'reference_number']
    # If the caller passes an unlisted field, the default is returned instead
)
```

### 7.5 Default Ordering Conventions

- Use `-created_at` as the default for most list views.
- Use `-fiscal_year__start_date` or `-planned_start_date` when entities are period-anchored.

---

## 8. Response Format Structure

All responses use helpers from `apps/api/utils/response_helpers.py`. Never construct `Response({…})` dicts inline in view code.

### 8.1 Success — Single Item

```json
{
  "success": true,
  "data": { "id": "uuid", "title": "…" },
  "message": "Created successfully"
}
```

Helpers:
- `success_response(data)` → HTTP 200
- `created_response(data)` → HTTP 201
- `updated_response(data)` → HTTP 200
- `deleted_response()` → HTTP 200

### 8.2 Success — Paginated List

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

Helper: `paginated_list_response(items, count, page, page_size)`

Items go **directly** in `data` — not wrapped inside `{items: [...]}`.  
Total count goes in `meta.total` — not in `data`.

### 8.3 Error

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

### 8.4 Response Helper Reference

| Helper | HTTP Status | Use Case |
|---|---|---|
| `success_response(data)` | 200 | Single item GET, status updates |
| `created_response(data)` | 201 | Resource creation |
| `updated_response(data)` | 200 | Resource updates |
| `deleted_response()` | 200 | Soft delete |
| `paginated_list_response(items, count, page, page_size)` | 200 | All list endpoints |
| `error_response(message, code, details)` | 400 | Generic client errors |
| `not_found_response(message)` | 404 | Resource not found |
| `validation_error_response(errors)` | 400 | Serializer validation failures |
| `conflict_response(message)` | 409 | Duplicate / business rule conflict |
| `server_error_response(message, details)` | 500 | Unhandled exceptions |

### 8.5 Error Code Convention

All `code` values in error responses use `SCREAMING_SNAKE_CASE` and are self-descriptive:
- `UNIVERSE_NOT_APPROVED`
- `DUPLICATE_REFERENCE`
- `PARENT_NOT_FOUND`
- `AUTH_REQUIRED`
- `WORKFLOW_ALREADY_ACTIVE`
- `VALIDATION_ERROR` (reserved for serializer failures via `validation_error_response`)
- `NOT_FOUND` (reserved for 404s via `not_found_response`)

---

## 9. RBAC and Permission Enforcement

### 9.1 Permission Code Convention

All permission codes follow the pattern: `grc:{resource}:{action}`

```
grc:risk_register:view
grc:risk_register:manage
grc:risk_register:approve
grc:risk_assessment:conduct
grc:risk_assessment:review
```

- `resource`: snake_case, matches the entity name
- `action`: `view`, `manage`, `approve`, `conduct`, `respond`, etc.

All codes are declared in `config/permissions/grc-service.json` as the single source of truth.

### 9.2 Named Permission Classes

One `BasePermission` subclass per permission code, defined in `apps/api/permissions_jwt.py`:

```python
class CanViewRiskRegister(BasePermission):
    """Check: grc:risk_register:view"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:risk_register:view')


class CanManageRiskRegister(BasePermission):
    """Check: grc:risk_register:manage"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:risk_register:manage')
```

All checks are **local** — `_check_grc_permission_locally()` reads `request.grc_permissions` (set by `JWTPermissionMiddleware`) with no HTTP calls.

### 9.3 Generic Permission Classes (for ad-hoc use)

Three generic classes are available for ad-hoc checks outside the standard per-entity pattern:

```python
HasPermission('grc:risk_register:approve')
HasAnyPermission(['grc:risk_register:view', 'grc:risk_report:view'])
HasAllPermissions(['grc:risk_register:view', 'grc:risk_register:approve'])
```

### 9.4 Superuser / Wildcard Bypass

If `request.grc_permissions == ['*']`, all permission checks pass automatically. This is for superusers only.

### 9.5 View-Level Enforcement Pattern

```python
class RiskRegisterListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_register:view required.')
        elif request.method == 'POST':
            if not CanManageRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_register:manage required.')
```

- `permission_classes = [IsAuthenticated]` is always required.
- `super().check_permissions(request)` must always be the first line in the override.
- Error message to `permission_denied()` must state the required permission code.

### 9.6 `request` Convenience Attributes (set by JWTPermissionMiddleware)

| Attribute | Type | Content |
|---|---|---|
| `request.user_id` | `str` | IAM user UUID |
| `request.user_email` | `str` | IAM user email |
| `request.grc_permissions` | `list[str]` | GRC permission codes or `['*']` |
| `request.is_superuser` | `bool` | True if wildcard grant |

---

## 10. Naming Conventions

### 10.1 Models

| Subject | Convention | Example |
|---|---|---|
| Class name | `PascalCase`, descriptive noun | `RiskRegister`, `RiskTreatmentPlan` |
| `db_table` | `grc_{entity_snake_name}` | `grc_risk_register`, `grc_risk_treatment_plan` |
| `STATUS_CHOICES` values | `snake_case` strings | `'draft'`, `'under_review'`, `'approved'` |
| FK to IAM user | `{role_name}` (UUID field) | `lead_auditor`, `risk_owner`, `prepared_by` |
| FK to lookup table | `{lookup_name}` with matching `{lookup_name}_id` | `risk_category`, `risk_category_id` |
| Soft delete flag | `is_active` (from `StatusMixin`) | — |
| Composite unique constraint names | `grc_{entity}_{fields}_uniq` | `grc_risk_register_active_fy_uniq` |

### 10.2 Files

| Subject | Convention | Example |
|---|---|---|
| Model file | `{module}_entities.py` | `risk_entities.py` |
| Serializer file | `{module}_serializers.py` | `risk_serializers.py` |
| View file | `{entity}_views.py` | `risk_register_views.py` |
| Service file | `{entity}_service.py` | `risk_register_service.py` |
| URL file | `{module}.py` | `risk.py` |
| Task file | `{concern}.py` | `risk_review_deadlines.py` |
| Event file | `{module}_events.py` | `risk_events.py` |

### 10.3 Services

| Subject | Convention | Example |
|---|---|---|
| Service class | `{EntityName}Service` | `RiskRegisterService` |
| Template code constant | `WORKFLOW_TEMPLATE_CODE = "grc.{entity}_approval"` | `"grc.risk_register_approval"` |
| Submit method | `submit_for_approval(entity_id, submitter_id)` | — |
| Advance method | `advance_workflow_stage(entity_id, action, actor_id, comment)` | — |
| Cancel method | `cancel_workflow_plan(entity_id, actor_id, reason)` | — |

### 10.4 URLs / Endpoints

| Subject | Convention | Example |
|---|---|---|
| Collection endpoint | Kebab-case plural noun | `/risk-registers/` |
| Detail endpoint | `<uuid:pk>/` suffix | `/risk-registers/<uuid:pk>/` |
| Action endpoint | Descriptive verb phrase | `/risk-registers/<pk>/submit/` |
| Workflow endpoints | Standard 5 suffixes (see §4.3) | `/risk-registers/<pk>/workflow-status/` |
| Sub-resource | `/{parent}/{parent_pk}/{child}/` | `/engagements/<id>/working-papers/` |
| Static segments before UUID captures | Required ordering rule | `overdue/` before `<uuid:pk>/` |

### 10.5 Workflow Templates

| Subject | Convention | Example |
|---|---|---|
| Template code | `grc.{entity_snake}_approval` | `grc.risk_register_approval` |
| Stage `definitionKey` | `snake_case` | `cia_review`, `management_review` |
| Action `name` | `snake_case` | `approve`, `reject`, `request_changes` |
| Action `nextState` | `camelCase` | `completed`, `rejected`, `pending` |

### 10.6 Permissions

| Subject | Convention | Example |
|---|---|---|
| Permission code | `grc:{resource}:{action}` | `grc:risk_register:manage` |
| Permission class name | `Can{Action}{Resource}` | `CanManageRiskRegister` |
| Class docstring | `"Check: grc:{resource}:{action}"` | `"Check: grc:risk_register:manage"` |
| Error message in `permission_denied()` | `"{code} required."` | `"grc:risk_register:view required."` |

### 10.7 Kafka / Domain Events

| Subject | Convention | Example |
|---|---|---|
| Event type string | `grc.{module}.{entity}.{past_verb}` | `grc.risk.register.created` |
| Event class name | `{Entity}{PastVerb}Event` | `RiskRegisterCreatedEvent` |
| Event type constant group | `{ENTITY}_EVENTS` dict | `RISK_REGISTER_EVENTS` |
| Kafka topic | Priority tier: `notifications-high`, `notifications-normal`, `notifications-low`, `notifications-urgent` | — |

### 10.8 Reference Numbers

Auto-generated reference numbers follow the pattern `{PREFIX}-{FYCODE}-{seq:03d}`:

```python
year_code = fiscal_year.year_code.replace('/', '')   # "2024/2025" → "20242025"
count = MyEntity.objects.filter(fiscal_year=fiscal_year).count()
reference_number = f"PREFIX-{year_code}-{count + 1:03d}"
```

Always check for duplicate reference numbers before saving and return a `conflict_response` if a duplicate exists.

---

## Appendix: Module Implementation Checklist

Use this sequence when building a new module.

### Step 1 — Models
- [ ] Inherit `TimestampedModel + StatusMixin` for every entity
- [ ] Add `WorkflowMixin` if the entity participates in a workflow
- [ ] Use `UUIDField` for all references to IAM users
- [ ] Use FK to lookup tables, not `CharField(choices=…)`, for standardized values
- [ ] Define `db_table` with `grc_` prefix
- [ ] Define `STATUS_CHOICES` and `status` field with `db_index=True` for all lifecycle entities
- [ ] Override `get_workflow_context()`, `get_workflow_metadata()` if workflow-enabled
- [ ] Register entity path in `workflow_entity_paths.py` if workflow-enabled

### Step 2 — Lookup Tables
- [ ] Create lookup models in `lookups.py` following the standard pattern
- [ ] Add serializers to `lookup_serializers.py`
- [ ] Add read-only list endpoints to `config_urls.py`

### Step 3 — Serializers
- [ ] Create `{module}_serializers.py`
- [ ] Apply FK dual-field pattern (`FK = NestedSerializer(read_only=True)` + `FK_id = UUIDField(write_only=True)`)
- [ ] Mark auto-generated/programmatic fields as `required=False` in `extra_kwargs`

### Step 4 — Permissions
- [ ] Define permission codes in `config/permissions/grc-service.json`
- [ ] Create named `Can{Action}{Resource}` classes in `permissions_jwt.py`

### Step 5 — Views
- [ ] Use `APIView` base class
- [ ] Implement `check_permissions()` with method-specific branching
- [ ] Use `select_related()` on all queryset fetches
- [ ] Use `paginate_queryset()` + `paginated_list_response()` for all list endpoints
- [ ] Use only response helpers from `response_helpers.py`; never inline `Response({…})` dicts
- [ ] Wrap all handlers in `try/except`; use `logger.exception()` and `server_error_response()`

### Step 6 — Workflow (if applicable)
- [ ] Add YAML template to `workflows.yaml`
- [ ] Create service class in `apps/core/services/` following the standard pattern
- [ ] Add 5 standard workflow endpoints (`submit`, `workflow-status`, `workflow-history`, `workflow-action`, `cancel-workflow`)

### Step 7 — URLs
- [ ] Add URL file to `apps/api/urls/`
- [ ] Declare static segment routes before `<uuid:pk>/` routes
- [ ] Mount the URL file in `apps/api/urls.py`

### Step 8 — Events (if applicable)
- [ ] Define event dataclasses in `apps/core/events/`
- [ ] Add event type constants to `shared/constants/event_types.py`
- [ ] Publish events from view layer after successful saves (inside a best-effort `try/except`)

### Step 9 — Background Tasks (if applicable)
- [ ] Create Celery task in `apps/core/tasks/`
- [ ] Register in `config/settings.py` under `CELERY_BEAT_SCHEDULE`
- [ ] Use `NotificationPublisher.send_notification()` for user-facing alerts, not raw Kafka

### Step 10 — Tests
- [ ] Add test files in `tests/`
- [ ] Cover: permission denied, happy path, serializer validation errors, business rule violations
