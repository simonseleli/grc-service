# Legal Module — Base Models & Mixins
**Service:** `grc-service`
**Module:** Legal
**Phase:** 5A — Base Models & Mixins
**File:** `apps/core/models/base.py` (shared), `apps/core/models/legal_entities.py` (legal models), `apps/core/models/lookups.py` (lookup additions)

---

## Table of Contents

1. [Overview](#1-overview)
2. [BaseModel](#2-basemodel)
3. [TimestampedModel](#3-timestampedmodel)
4. [StatusMixin](#4-statusmixin)
5. [WorkflowMixin](#5-workflowmixin)
6. [Composition Rules](#6-composition-rules)
7. [Lookup Model Pattern](#7-lookup-model-pattern)
8. [Legal Lookup Models](#8-legal-lookup-models)
9. [Pagination Helpers](#9-pagination-helpers)
10. [Response Helpers](#10-response-helpers)
11. [Quick Reference: Legal Model Compositions](#11-quick-reference-legal-model-compositions)

---

## 1. Overview

The Legal module inherits the **same four base classes** used by the Internal Audit module. These classes live in `apps/core/models/base.py` and are **not modified** for the Legal module. Legal models import and compose them exactly as Internal Audit does.

### The four base classes at a glance

| Class | Layer | Purpose |
|---|---|---|
| `BaseModel` | Abstract | UUID PK, `created_at`, `updated_at` — all models |
| `TimestampedModel` | Abstract | Extends `BaseModel` + `created_by`, `modified_by` UUID fields — all business entities |
| `StatusMixin` | Abstract mixin | `is_active` BooleanField — all entities that support soft-delete |
| `WorkflowMixin` | Abstract mixin | Five WO workflow fields + helper methods — entities that enter a WO workflow plan |

**Rule:** `base.py` is touched by the Legal module **only to import from** — no new classes are added there. Legal-specific base extensions (if any arise) go into `legal_entities.py` as private base classes scoped to that file.

---

## 2. BaseModel

### Source (unchanged)

```python
# apps/core/models/base.py

import uuid
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base model with common fields used across all GRC entities.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### Rules for Legal models

- **All** Legal models derive — directly or indirectly — from `BaseModel`.
- `id` is always a UUID. Never use integer PKs.
- `created_at` is indexed (`db_index=True`) — list endpoints always sort on it.
- `updated_at` is cursor-style; never filter on it in application logic.
- `editable=False` on `id` — never expose in write serializers.

### What Legal models do NOT add to BaseModel

| Anti-pattern | Why forbidden |
|---|---|
| Adding `slug` fields | URL keys are always UUIDs |
| Overriding `id` field | UUID PK is non-negotiable |
| Adding `deleted_at` soft-delete | Soft-delete uses `is_active` from `StatusMixin` |
| Making `id` editable | `editable=False` is a platform constraint |

---

## 3. TimestampedModel

### Source (unchanged)

```python
# apps/core/models/base.py

class TimestampedModel(BaseModel):
    """
    Extended base model with created_by tracking.
    """
    created_by = models.UUIDField(
        help_text="User ID from IAM service who created this record"
    )
    modified_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID from IAM service who last modified this record"
    )

    class Meta:
        abstract = True
```

### Rules for Legal models

- **All** Legal *business entity* models inherit `TimestampedModel` (not bare `BaseModel`).
- `created_by` is set in the view from `request.user_id` (extracted by `JWTPermissionMiddleware`). It is **never** set in `save()`.
- `modified_by` is set in the view on every `PUT`/`PATCH` call. Never None after first modification.
- Both fields store **UUID only**. Display names are resolved at read time via `IAMClient.get_user_profile()` with Redis caching — never stored here.

### Setting created_by / modified_by in Legal views

```python
# Pattern used in ALL Legal create views
def post(self, request):
    serializer = MeetingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    with transaction.atomic():
        meeting = serializer.save(
            created_by=request.user_id,    # from JWTPermissionMiddleware
        )
    return created_response(...)

# Pattern used in ALL Legal update views
def put(self, request, pk):
    # ...
    with transaction.atomic():
        instance = serializer.save(
            modified_by=request.user_id,
        )
```

### What Legal serializers declare for these fields

```python
class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'
        extra_kwargs = {
            'created_by': {'required': False},   # set by view, not client
            'modified_by': {'required': False},  # set by view, not client
            'id': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }
```

---

## 4. StatusMixin

### Source (unchanged)

```python
# apps/core/models/base.py

class StatusMixin(models.Model):
    """
    Mixin for entities that have an active/soft-deleted flag.
    """
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this record is active and available for use"
    )

    class Meta:
        abstract = True
```

### Rules for Legal models

- **All** Legal business entities include `StatusMixin`.
- Hard deletes (`DELETE` SQL) are **prohibited**. Setting `is_active = False` is the only way to "delete" a record.
- Default queryset in views **always** filters `is_active=True`:

```python
# All Legal list views follow this pattern
queryset = Meeting.objects.filter(is_active=True).order_by('-created_at')
```

- `is_active` is exposed in serializers as **read-only** for non-admin roles. Only a specific `deactivate` endpoint (or admin action) sets it to `False`.
- `is_active` participates in partial `UniqueConstraint` — see §6 Composition Rules.

### Soft-delete pattern for Legal entities

```python
# Deactivation (never hard delete)
instance.is_active = False
instance.modified_by = request.user_id
instance.save(update_fields=['is_active', 'modified_by', 'updated_at'])
```

- Passing `update_fields` is mandatory to prevent unintended side-effects in override `save()` methods that perform auto-calculations.

---

## 5. WorkflowMixin

### Source (unchanged)

```python
# apps/core/models/base.py

class WorkflowMixin(models.Model):
    """
    Mixin for entities that integrate with Work Orchestration Service.
    """
    workflow_plan_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID of the workflow plan in Work Orchestration Service"
    )
    workflow_stage = models.CharField(
        max_length=255, blank=True, default='',
        help_text="Current stage name in Work Orchestration Service"
    )
    workflow_stage_id = models.UUIDField(
        null=True, blank=True,
        help_text="UUID of the current stage in Work Orchestration Service"
    )
    workflow_started_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the workflow plan was started"
    )
    workflow_completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the workflow plan reached a terminal state"
    )

    class Meta:
        abstract = True

    @property
    def has_workflow(self) -> bool:
        return self.workflow_plan_id is not None

    @property
    def has_active_workflow(self) -> bool:
        return self.workflow_plan_id is not None and self.workflow_completed_at is None

    @property
    def is_workflow_completed(self) -> bool:
        return self.workflow_completed_at is not None

    def start_workflow(self, plan_id, initial_stage='', stage_id=None) -> None:
        self.workflow_plan_id = plan_id
        self.workflow_stage = initial_stage
        self.workflow_stage_id = stage_id
        self.workflow_started_at = timezone.now()
        self.workflow_completed_at = None

    def update_workflow_stage(self, stage_name, stage_id=None) -> None:
        self.workflow_stage = stage_name
        if stage_id:
            self.workflow_stage_id = stage_id

    def complete_workflow(self) -> None:
        self.workflow_completed_at = timezone.now()

    def cancel_workflow(self) -> None:
        self.workflow_completed_at = timezone.now()

    def clear_workflow(self) -> None:
        self.workflow_plan_id = None
        self.workflow_stage = ''
        self.workflow_stage_id = None
        self.workflow_started_at = None
        self.workflow_completed_at = None

    def get_workflow_context(self) -> dict:
        """Override in subclass to provide entity-specific WO context vars."""
        return {
            'entity_type': self._meta.model_name,
            'entity_id': str(self.pk),
        }

    def get_workflow_metadata(self) -> dict:
        """Override in subclass to provide entity-specific WO plan metadata."""
        return {
            'entity_type': self._meta.model_name,
            'entity_id': str(self.pk),
            'entity_repr': str(self),
        }

    def log_workflow_action(self, action, actor_id, stage_name, comment='', metadata=None) -> None:
        """Override in subclass to persist per-action audit records."""
        pass
```

### Which Legal entities include WorkflowMixin

| Entity | Workflow Template Code | Trigger |
|---|---|---|
| `FilingDefendant` | `grc.legal_filing_approval` | Legal Officer submits filing for approval |
| `FilingPlaintiff` | `grc.legal_filing_approval` | Legal Officer submits filing for approval |
| `Minutes` | `grc.legal_minutes_approval` | Secretary submits minutes for approval |
| `SettlementDefendant` | `grc.legal_settlement_approval` | Legal Officer submits settlement for DG |
| `SettlementPlaintiff` | `grc.legal_settlement_approval` | Legal Officer submits settlement for DG |
| `JudgmentDefendant` | `grc.legal_judgment_decision` | Judgment recorded; DG decision required |
| `JudgmentPlaintiff` | `grc.legal_judgment_decision` | Judgment recorded; DG decision required |
| `CaseDefendant` | `grc.legal_case_closure` | Legal Manager initiates closure |
| `CasePlaintiff` | `grc.legal_case_closure` | Legal Manager initiates closure |

All other Legal entities do **not** include `WorkflowMixin` — they have internal status fields only.

### Required method overrides for Legal entities

Every Legal entity that includes `WorkflowMixin` **must** override three methods. The base class default implementations are stubs — they will not produce meaningful WO context or audit trails without overrides.

#### `get_workflow_context()`

Returns the variable map used by Work Orchestration Service to resolve stage assignees. The keys must match the variable names configured in the workflow template.

```python
# In FilingDefendant model
def get_workflow_context(self) -> dict:
    return {
        'filing_id':     str(self.id),
        'case_id':       str(self.case_id),
        'case_ref':      self.case.reference_number,
        'legal_officer': str(self.assigned_legal_officer_id),
    }
```

```python
# In Minutes model
def get_workflow_context(self) -> dict:
    return {
        'minutes_id':  str(self.id),
        'meeting_id':  str(self.meeting_id),
        'meeting_ref': self.meeting.reference_number,
        'secretary':   str(self.created_by),
    }
```

#### `get_workflow_metadata()`

Returns display metadata stored with the WO plan. Shown in the WO console and notification templates.

```python
# In FilingDefendant model
def get_workflow_metadata(self) -> dict:
    meta = {
        'entity_type':  'filing_defendant',
        'entity_id':    str(self.id),
        'case_ref':     self.case.reference_number,
        'filing_type':  self.filing_type,
        'filed_date':   str(self.filed_date) if self.filed_date else None,
        'status':       self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, 'filing_defendant')
```

#### `log_workflow_action()`

Persists an immutable `LegalAuditLog` record on each WO stage action (approve, reject, return, escalate).

```python
# In FilingDefendant model
def log_workflow_action(self, action, actor_id, stage_name, comment='', metadata=None) -> None:
    from apps.core.models.legal_entities import LegalAuditLog
    LegalAuditLog.objects.create(
        entity_type='filing_defendant',
        entity_id=self.id,
        action=action,
        actor_id=actor_id,
        stage_name=stage_name,
        comment=comment or '',
        metadata=metadata or {},
    )
```

### Workflow fields in serializers (read-only)

All five `WorkflowMixin` fields are always **read-only** in serializers. They are set programmatically by the service layer — never written by the client.

```python
class FilingDefendantSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilingDefendant
        fields = '__all__'
        extra_kwargs = {
            'workflow_plan_id':      {'read_only': True},
            'workflow_stage':        {'read_only': True},
            'workflow_stage_id':     {'read_only': True},
            'workflow_started_at':   {'read_only': True},
            'workflow_completed_at': {'read_only': True},
            # ... other auto-set fields
        }
```

---

## 6. Composition Rules

### Rule 1 — Always compose, never inherit a single over-large base

Legal models use Python multiple inheritance to compose only the mixins they need:

```python
# Correct: business entity that enters WO workflow
class FilingDefendant(TimestampedModel, StatusMixin, WorkflowMixin):
    ...

# Correct: business entity with no workflow
class MeetingParticipant(TimestampedModel, StatusMixin):
    ...

# Correct: lookup table (no created_by/modified_by needed)
class CourtLevel(BaseModel, StatusMixin):
    ...

# WRONG: lookup table should never include WorkflowMixin
class CourtLevel(BaseModel, StatusMixin, WorkflowMixin):  # prohibited
    ...

# WRONG: business entity missing StatusMixin (hard-delete risk)
class Meeting(TimestampedModel, WorkflowMixin):  # prohibited — missing StatusMixin
    ...
```

### Rule 2 — MRO and Meta.abstract

Python MRO (Method Resolution Order) applies to composed bases. All four base classes declare `class Meta: abstract = True`, so Django does not create a DB table for any of them. The concrete Legal model's `Meta` **must** always declare `db_table`.

```python
class Meeting(TimestampedModel, StatusMixin):
    ...
    class Meta:
        db_table = 'legal_meeting'      # required — always prefix legal_
        ordering = ['-created_at']
        verbose_name = 'Meeting'
        verbose_name_plural = 'Meetings'
```

### Rule 3 — db_table naming convention

All Legal module models use `legal_` as table prefix:

| Entity | db_table |
|---|---|
| `CommitteeType` | `legal_committee_type` |
| `GoverningBody` | `legal_governing_body` |
| `Member` | `legal_member` |
| `SubmissionForDetermination` | `legal_submission_for_determination` |
| `Meeting` | `legal_meeting` |
| `MeetingAgenda` | `legal_meeting_agenda` |
| `ConflictDeclaration` | `legal_conflict_declaration` |
| `MeetingParticipant` | `legal_meeting_participant` |
| `MeetingDirective` | `legal_meeting_directive` |
| `Minutes` | `legal_minutes` |
| `Resolution` | `legal_resolution` |
| `CaseDefendant` | `legal_case_defendant` |
| `CasePlaintiff` | `legal_case_plaintiff` |
| `LitigationDirective` | `legal_litigation_directive` |
| `FilingDefendant` | `legal_filing_defendant` |
| `FilingPlaintiff` | `legal_filing_plaintiff` |
| `ResponseDefendant` | `legal_response_defendant` |
| `ResponsePlaintiff` | `legal_response_plaintiff` |
| `Hearing` | `legal_hearing` |
| `HearingReport` | `legal_hearing_report` |
| `SettlementDefendant` | `legal_settlement_defendant` |
| `SettlementPlaintiff` | `legal_settlement_plaintiff` |
| `JudgmentDefendant` | `legal_judgment_defendant` |
| `JudgmentPlaintiff` | `legal_judgment_plaintiff` |
| `FinancialDefendant` | `legal_financial_defendant` |
| `FinancialPlaintiff` | `legal_financial_plaintiff` |
| `TaskLitigation` | `legal_task_litigation` |
| `PublicDecision` | `legal_public_decision` |
| `LegalAuditLog` | `legal_audit_log` |

### Rule 4 — Partial UniqueConstraint with is_active

When a business rule requires uniqueness (e.g., "one active case per reference number"), use a `partial` constraint scoped to `is_active=True`. This allows logically deleted duplicates to exist without violating the constraint.

```python
class Meta:
    db_table = 'legal_case_defendant'
    constraints = [
        models.UniqueConstraint(
            fields=['reference_number'],
            condition=models.Q(is_active=True),
            name='legal_case_defendant_active_ref_uniq',
        )
    ]
```

Constraint name convention: `{db_table}_{field(s)}_{suffix}` where suffix is `uniq`, `together_uniq`, or `partial_uniq`.

### Rule 5 — save() overrides

Use `save()` overrides only for **auto-calculated fields** — fields whose value is always derived from other fields (e.g., `quorum_met`, `case_age_days`, `total_amount_claimed`). Never put business logic or workflow transitions in `save()`.

The override must:
1. Check `update_fields` to skip recalculation for status-only saves.
2. Extend `update_fields` with the computed field names so they are persisted when `update_fields` is passed.
3. Call `super().save(*args, **kwargs)` unconditionally at the end.

```python
# Pattern for auto-calculated fields in Legal models
def save(self, *args, **kwargs):
    update_fields = kwargs.get('update_fields')
    trigger_fields = {'rsvp_yes_count', 'rsvp_no_count', 'rsvp_pending_count', 'quorum_threshold'}
    should_calc = update_fields is None or bool(set(update_fields) & trigger_fields)

    if should_calc:
        self.quorum_met = (
            self.rsvp_yes_count >= self.quorum_threshold
            if self.quorum_threshold
            else False
        )
        if update_fields is not None:
            kwargs['update_fields'] = list(set(update_fields) | {'quorum_met'})

    super().save(*args, **kwargs)
```

### Rule 6 — FK user references are UUID only

FKs to IAM users are **always** plain `UUIDField` — never `ForeignKey` to a User model (there is no User model in grc-service).

```python
# Correct
assigned_legal_officer_id = models.UUIDField(
    help_text="UUID of the Legal Officer assigned (from IAM)"
)

# WRONG — no User model exists in grc-service
assigned_legal_officer = models.ForeignKey('auth.User', ...)  # prohibited
```

### Rule 7 — document_id fields are UUID only

Document attachments are stored as UUIDs pointing to Document Records Service. Never store file content locally.

```python
# Single document
document_id = models.UUIDField(
    null=True, blank=True,
    help_text="UUID of document in Document Records Service"
)

# Multiple documents
supporting_documents = models.JSONField(
    default=list, blank=True,
    help_text="List of document UUIDs from Document Records Service"
)
```

### Rule 8 — Use lookup tables, not choices= for user-visible categories

Database-configurable lookups (court levels, urgency levels, risk levels, etc.) use `ForeignKey` to a lookup model, **not** inline `choices=`. Internal workflow status enums use `choices=` because they are domain-state, not user-configurable.

```python
# Correct — user-visible category resolved via FK to lookup table
court_level = models.ForeignKey(
    'CourtLevel',
    on_delete=models.PROTECT,
    related_name='cases_defendant',
)

# Correct — internal domain status uses choices=
STATUS_CHOICES = [
    ('registered', 'Registered'),
    ('dg_review', 'DG Review'),
    ('active', 'Active'),
    ('closed', 'Closed'),
]
status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered', db_index=True)
```

---

## 7. Lookup Model Pattern

Legal lookup models are added to `apps/core/models/lookups.py` alongside the existing audit lookup models. They follow the same structure:

- Inherit `BaseModel, StatusMixin` (no `TimestampedModel` — lookups are system-managed, not user-created records).
- Have a `name` CharField, optional `code` CharField, optional `description` TextField.
- `is_active = True` by default; deactivated lookups are hidden from dropdowns but retained for existing records.
- `db_table` uses `grc_` prefix (keeping consistency with other lookup tables in this file) **not** `legal_`.

```python
# Template for all Legal lookup models

class CourtLevel(BaseModel, StatusMixin):
    """
    Court hierarchy levels for litigation case classification.
    Examples: High Court, Court of Appeal, Supreme Court.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display sort order (lower = higher court)"
    )

    class Meta:
        db_table = 'grc_court_level'
        ordering = ['order', 'name']
        verbose_name = 'Court Level'
        verbose_name_plural = 'Court Levels'

    def __str__(self):
        return self.name
```

---

## 8. Legal Lookup Models

The following lookup models are **added to `apps/core/models/lookups.py`**:

### CourtLevel

```python
class CourtLevel(BaseModel, StatusMixin):
    """
    Court hierarchy levels for FCC litigation cases.
    Examples: High Court, Court of Appeal, Supreme Court.
    Seed values: loaded via management command `seed_lookup_data`.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'grc_court_level'
        ordering = ['order', 'name']
        verbose_name = 'Court Level'
        verbose_name_plural = 'Court Levels'

    def __str__(self):
        return self.name
```

### LitigationUrgencyLevel

```python
class LitigationUrgencyLevel(BaseModel, StatusMixin):
    """
    Urgency classification for litigation cases.
    Examples: Critical, High, Medium, Low.
    Drives Kafka notification priority topic selection.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    notification_priority = models.CharField(
        max_length=20,
        choices=[
            ('urgent', 'Urgent'),
            ('high', 'High'),
            ('normal', 'Normal'),
            ('low', 'Low'),
        ],
        default='normal',
        help_text="Kafka notification topic to use for this urgency level"
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'grc_litigation_urgency_level'
        ordering = ['order']
        verbose_name = 'Litigation Urgency Level'
        verbose_name_plural = 'Litigation Urgency Levels'

    def __str__(self):
        return self.name
```

### LitigationRiskLevel

```python
class LitigationRiskLevel(BaseModel, StatusMixin):
    """
    Risk level classification for litigation cases and directives.
    Examples: High Risk, Medium Risk, Low Risk.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'grc_litigation_risk_level'
        ordering = ['order']
        verbose_name = 'Litigation Risk Level'
        verbose_name_plural = 'Litigation Risk Levels'

    def __str__(self):
        return self.name
```

### MeetingMode

```python
class MeetingMode(BaseModel, StatusMixin):
    """
    Physical attendance mode for a meeting.
    Examples: Physical, Virtual, Hybrid.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'grc_meeting_mode'
        ordering = ['name']
        verbose_name = 'Meeting Mode'
        verbose_name_plural = 'Meeting Modes'

    def __str__(self):
        return self.name
```

### MeetingType

```python
class MeetingType(BaseModel, StatusMixin):
    """
    Classification of meeting formality.
    Examples: Ordinary, Extraordinary, Special.
    Determines quorum rules and validity conditions.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    quorum_percentage = models.PositiveSmallIntegerField(
        default=50,
        help_text="Minimum percentage of members required for quorum (e.g., 51 = majority)"
    )

    class Meta:
        db_table = 'grc_meeting_type'
        ordering = ['name']
        verbose_name = 'Meeting Type'
        verbose_name_plural = 'Meeting Types'

    def __str__(self):
        return self.name
```

### DirectivePriority

```python
class DirectivePriority(BaseModel, StatusMixin):
    """
    Priority classification for meeting and litigation directives.
    Examples: Critical, High, Medium, Low.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'grc_directive_priority'
        ordering = ['order']
        verbose_name = 'Directive Priority'
        verbose_name_plural = 'Directive Priorities'

    def __str__(self):
        return self.name
```

### DirectiveCategory

```python
class DirectiveCategory(BaseModel, StatusMixin):
    """
    Thematic category for meeting and litigation directives.
    Admin-configurable. Examples: Legal Compliance, Corporate Governance, Finance.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_directive_category'
        ordering = ['name']
        verbose_name = 'Directive Category'
        verbose_name_plural = 'Directive Categories'

    def __str__(self):
        return self.name
```

### Seed values for Legal lookups

These models are loaded via the existing `seed_lookup_data` management command. The command is extended (not replaced) to include Legal seed data:

| Model | Seed values |
|---|---|
| `CourtLevel` | High Court, Court of Appeal, Supreme Court, Labour Court, Commercial Division |
| `LitigationUrgencyLevel` | Critical (urgent), High (high), Medium (normal), Low (low) |
| `LitigationRiskLevel` | High Risk, Medium Risk, Low Risk |
| `MeetingMode` | Physical, Virtual, Hybrid |
| `MeetingType` | Ordinary (quorum: 51%), Extraordinary (quorum: 51%), Special (quorum: 67%) |
| `DirectivePriority` | Critical, High, Medium, Low |
| `DirectiveCategory` | Legal Compliance, Corporate Governance, Finance, Operations, HR (extensible) |

---

## 9. Pagination Helpers

The pagination utilities in `apps/api/utils/pagination.py` are shared and **not modified** for the Legal module. All Legal list views call these helpers directly.

### paginate_queryset()

```python
from apps.api.utils.pagination import paginate_queryset

def get(self, request):
    queryset = Meeting.objects.filter(is_active=True).order_by('-created_at')

    # Optional: apply ordering from query param
    ordering = get_ordering_param(
        request,
        default='-created_at',
        allowed_fields=['created_at', 'scheduled_date', 'status', 'reference_number'],
    )
    queryset = queryset.order_by(ordering)

    page_data = paginate_queryset(queryset, request)
    serializer = MeetingSerializer(page_data['queryset'], many=True)

    return paginated_list_response(
        items=serializer.data,
        count=page_data['total'],
        page=page_data['page'],
        page_size=page_data['page_size'],
        resource='meetings',
    )
```

### paginate_queryset() return value

| Key | Type | Description |
|---|---|---|
| `queryset` | Sliced QuerySet | The page of results (already sliced — do not re-slice) |
| `page` | int | Current page number (1-based) |
| `page_size` | int | Items per page (default: 20, max: 100) |
| `total` | int | Total record count across all pages |
| `total_pages` | int | Number of pages |

### get_ordering_param()

```python
from apps.api.utils.pagination import get_ordering_param

ordering = get_ordering_param(
    request,
    default='-created_at',
    allowed_fields=[
        'created_at',
        'reference_number',
        'status',
        'scheduled_date',
        'due_date',
    ],
)
```

**Security rule:** `allowed_fields` **must always be specified** for Legal views. Omitting it allows unrestricted field names in the `ordering` query parameter, which is a potential information-disclosure vector. The list must include only fields that exist on the model and are safe to expose.

Do not include:
- `created_by`, `modified_by` — UUID-only fields; ordering by them is meaningless
- `workflow_plan_id`, `workflow_stage_id` — internal WO references
- Any field not visible in the list response serializer

### parse_boolean_param()

Used for filter parameters on Legal list endpoints:

```python
from apps.api.utils.pagination import parse_boolean_param

# Example: GET /legal/directives/?is_overdue=true
is_overdue = parse_boolean_param(request.query_params.get('is_overdue'))
if is_overdue:
    queryset = queryset.filter(status='overdue')
```

### parse_uuid_list()

Used for multi-value UUID filter parameters:

```python
from apps.api.utils.pagination import parse_uuid_list

# Example: GET /legal/meetings/?governing_body_ids=uuid1,uuid2
body_ids = parse_uuid_list(request.query_params.get('governing_body_ids'))
if body_ids:
    queryset = queryset.filter(governing_body_id__in=body_ids)
```

### Platform defaults (from REST_FRAMEWORK settings)

| Setting | Value |
|---|---|
| `PAGE_SIZE` | 20 |
| `MAX_PAGE_SIZE` | 100 |

These are defined in `config/settings.py` under `REST_FRAMEWORK` and consumed by `pagination.py` at import time. Legal views do not override them.

---

## 10. Response Helpers

The response helpers in `apps/api/utils/response_helpers.py` are shared and **not modified** for the Legal module. All Legal views use these exclusively.

### Envelope format

```json
// Single-item success
{
    "success": true,
    "data": { ... },
    "message": "Meeting retrieved successfully"
}

// List with pagination
{
    "success": true,
    "data": [ ... ],
    "meta": {
        "page": 1,
        "page_size": 20,
        "total": 137,
        "total_pages": 7
    }
}

// Error
{
    "success": false,
    "error": {
        "code": "MEETING_NOT_FOUND",
        "message": "Meeting not found",
        "details": null
    }
}
```

### Function reference

| Helper | HTTP Status | Use in Legal views |
|---|---|---|
| `success_response(data, message=...)` | 200 | Detail GET, Update, status-only action |
| `created_response(data, message=...)` | 201 | All POST create endpoints |
| `paginated_list_response(items, count, page, page_size, resource)` | 200 | All list GET endpoints |
| `no_content_response()` | 204 | Deactivate/delete (no body needed) |
| `not_found_response(message)` | 404 | `get_object_or_404` replacement |
| `validation_error_response(message, details=...)` | 400 | Serializer error, business rule violation |
| `permission_denied_response(message)` | 403 | `check_permissions` failure |
| `conflict_response(message)` | 409 | Duplicate unique field |

### Standard view skeleton for Legal

```python
class MeetingDetailView(APIView):
    authentication_classes = [IAMJWTAuthentication, ServiceAuthentication]

    def get_permissions(self):
        return []  # Permissions checked manually via check_permissions()

    def get(self, request, pk):
        self.check_permissions(request)
        if not request.grc_permissions.get('grc:legal:meeting:view'):
            return permission_denied_response("You do not have permission to view meetings.")
        try:
            meeting = Meeting.objects.get(pk=pk, is_active=True)
        except Meeting.DoesNotExist:
            return not_found_response("Meeting not found.")
        serializer = MeetingSerializer(meeting)
        return success_response(serializer.data)

    def put(self, request, pk):
        self.check_permissions(request)
        if not request.grc_permissions.get('grc:legal:meeting:manage'):
            return permission_denied_response("You do not have permission to update meetings.")
        try:
            meeting = Meeting.objects.select_for_update().get(pk=pk, is_active=True)
        except Meeting.DoesNotExist:
            return not_found_response("Meeting not found.")
        serializer = MeetingSerializer(meeting, data=request.data, partial=True)
        if not serializer.is_valid():
            return validation_error_response("Invalid input.", serializer.errors)
        with transaction.atomic():
            instance = serializer.save(modified_by=request.user_id)
        return success_response(MeetingSerializer(instance).data, message="Meeting updated successfully.")
```

---

## 11. Quick Reference: Legal Model Compositions

Use this table to choose the correct base class combination for each Legal entity.

| Entity | BaseModel | TimestampedModel | StatusMixin | WorkflowMixin | Rationale |
|---|:---:|:---:|:---:|:---:|---|
| **Lookup models** | | | | | |
| `CourtLevel` | via | ✗ | ✓ | ✗ | System data — no user audit trail |
| `LitigationUrgencyLevel` | via | ✗ | ✓ | ✗ | System data — no user audit trail |
| `LitigationRiskLevel` | via | ✗ | ✓ | ✗ | System data |
| `MeetingMode` | via | ✗ | ✓ | ✗ | System data |
| `MeetingType` | via | ✗ | ✓ | ✗ | System data — carries quorum_percentage |
| `DirectivePriority` | via | ✗ | ✓ | ✗ | System data |
| `DirectiveCategory` | via | ✗ | ✓ | ✗ | System data |
| **Governance** | | | | | |
| `CommitteeType` | via | ✗ | ✓ | ✗ | Config data — admin-managed |
| `GoverningBody` | via | ✓ | ✓ | ✗ | User-created; no workflow |
| `Member` | via | ✓ | ✓ | ✗ | User-created snapshot; no workflow |
| **Determination** | | | | | |
| `SubmissionForDetermination` | via | ✓ | ✓ | ✗ | Internal status machine (no WO workflow) |
| **Meeting** | | | | | |
| `Meeting` | via | ✓ | ✓ | ✗ | Internal status machine |
| `MeetingAgenda` | via | ✓ | ✓ | ✗ | No workflow |
| `ConflictDeclaration` | via | ✓ | ✓ | ✗ | Declaration record — immutable after create |
| `MeetingParticipant` | via | ✓ | ✓ | ✗ | RSVP state — internal status |
| `MeetingDirective` | via | ✓ | ✓ | ✗ | Two-actor closure — internal status |
| `Minutes` | via | ✓ | ✓ | ✓ | Multi-signoff WO workflow |
| `Resolution` | via | ✓ | ✓ | ✗ | Auto-created from approved minutes — read-only |
| **Litigation common** | | | | | |
| `Hearing` | via | ✓ | ✓ | ✗ | No workflow |
| `HearingReport` | via | ✓ | ✓ | ✗ | No workflow |
| `TaskLitigation` | via | ✓ | ✓ | ✗ | Due-date monitoring only — no WO workflow |
| **Litigation — FCC Sued** | | | | | |
| `CaseDefendant` | via | ✓ | ✓ | ✓ | Closure workflow |
| `LitigationDirective` | via | ✓ | ✓ | ✗ | DG-issued; internal status |
| `FilingDefendant` | via | ✓ | ✓ | ✓ | 2-stage approval workflow |
| `ResponseDefendant` | via | ✓ | ✓ | ✗ | No workflow |
| `SettlementDefendant` | via | ✓ | ✓ | ✓ | 2-stage DG approval |
| `JudgmentDefendant` | via | ✓ | ✓ | ✓ | DG decision required |
| `FinancialDefendant` | via | ✓ | ✓ | ✗ | 1:1 record; no workflow |
| **Litigation — FCC Suing** | | | | | |
| `CasePlaintiff` | via | ✓ | ✓ | ✓ | Closure workflow |
| `FilingPlaintiff` | via | ✓ | ✓ | ✓ | 2-stage approval workflow |
| `ResponsePlaintiff` | via | ✓ | ✓ | ✗ | No workflow |
| `SettlementPlaintiff` | via | ✓ | ✓ | ✓ | 2-stage DG approval |
| `JudgmentPlaintiff` | via | ✓ | ✓ | ✓ | DG decision required |
| `FinancialPlaintiff` | via | ✓ | ✓ | ✗ | 1:1 record; no workflow |
| **Public Register** | | | | | |
| `PublicDecision` | via | ✓ | ✓ | ✗ | Internal publish status |
| **Cross-cutting** | | | | | |
| `LegalAuditLog` | via | ✗ | ✗ | ✗ | Immutable event log — no mixin pollution |

**"via"** in BaseModel column means: inherited transitively through `TimestampedModel` (which extends `BaseModel`) or directly.

### LegalAuditLog — special case

`LegalAuditLog` intentionally does **not** inherit `StatusMixin` or `TimestampedModel`. It is an immutable append-only record. There is no `is_active` because audit logs are never soft-deleted. There is no `created_by`/`modified_by` in the mixin sense — the actor is part of the log payload.

```python
class LegalAuditLog(BaseModel):
    """
    Immutable domain-level audit trail for all Legal module workflow actions.
    Append-only: never updated or deactivated.
    """
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id   = models.UUIDField(db_index=True)
    action      = models.CharField(max_length=100)
    actor_id    = models.UUIDField(db_index=True)
    stage_name  = models.CharField(max_length=255, blank=True)
    comment     = models.TextField(blank=True)
    metadata    = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'legal_audit_log'
        ordering = ['-created_at']
        verbose_name = 'Legal Audit Log'
        verbose_name_plural = 'Legal Audit Logs'
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['actor_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.entity_type}/{self.entity_id} — {self.action} at {self.created_at}"
```

---

*End of Phase 5A — Base Models & Mixins*
*Next: Phase 5B — Legal Module Data Models (`legal_entities.py`)*
