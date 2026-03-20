# Legal Module — Lookup Tables
**Service:** `grc-service`
**Module:** Legal
**Phase:** 5C — Lookup Tables
**File target:** `apps/core/models/lookups.py` (appended to existing audit lookups)
**References:** 5A (Base Models & Mixins), 5B-1/5B-2/5B-3 (Data Models & Design Decisions)

> All Legal lookup models are appended to the **existing** `apps/core/models/lookups.py` file.
> They are **not** placed in `legal_entities.py`. No existing audit lookup models are modified.

---

## Table of Contents

1. [Overview & Conventions](#1-overview--conventions)
2. [Lookup Model Base Pattern](#2-lookup-model-base-pattern)
3. [CourtLevel](#3-courtlevel)
4. [LitigationUrgencyLevel](#4-litigationurgencylevel)
5. [LitigationRiskLevel](#5-litigationrisklevel)
6. [MeetingMode](#6-meetingmode)
7. [MeetingType](#7-meetingtype)
8. [DirectivePriority](#8-directivepriority)
9. [DirectiveCategory](#9-directivecategory)
10. [Admin Registration](#10-admin-registration)
11. [Serializers for Lookup Tables](#11-serializers-for-lookup-tables)
12. [Seed Data](#12-seed-data)
13. [FK Usage Reference](#13-fk-usage-reference)
14. [Lookup Deactivation Rules](#14-lookup-deactivation-rules)

---

## 1. Overview & Conventions

### What is a Lookup Table in this codebase

A lookup is a **small, admin-seeded reference table** that:

- Supplies dropdown options for a form field.
- Is not created by end users during normal operations.
- May grow via admin configuration (new entries can be added without code changes).
- Carries minimal logic — usually just `code`, `name`, `description`, and `is_active`.
- Is **soft-deactivatable**: `is_active=False` hides it from creation dropdowns but preserves existing FK relationships.

### What is NOT a lookup table

| Entity | Why it is not a lookup |
|---|---|
| `CommitteeType` | Created by admins with a full business lifecycle; managed via its own API endpoint |
| `MeetingParticipant.invitation_status` | Internal workflow state — uses `CharField(choices=)` |
| `JudgmentDefendant.dg_decision` | Binary domain decision — uses `CharField(choices=)` |
| `FilingDefendant.filing_type` | Domain-specific enum with a fixed set — uses `CharField(choices=)` |

### Conventions

| Property | Value |
|---|---|
| Base classes | `BaseModel, StatusMixin` — **no** `TimestampedModel` |
| `db_table` prefix | `grc_` (consistent with all existing lookup tables in this file) |
| File location | `apps/core/models/lookups.py` — appended after existing audit lookups |
| `code` field | `CharField(max_length=50, unique=True)` — machine-readable identifier |
| `name` field | `CharField(max_length=100)` — display label |
| `description` field | `TextField(blank=True)` — optional, for admin documentation |
| `is_active` | Inherited from `StatusMixin`; default `True` |
| `ordering` | `['name']` default; `['order']` for priority/ranked lookups |
| Import path | `from apps.core.models.lookups import CourtLevel, MeetingType, ...` |
| No `TimestampedModel` | Lookups have no `created_by` / `modified_by` — they are not user-submitted records |
| No `WorkflowMixin` | Lookups never enter a WO workflow |

### Difference from Internal Audit lookups

Internal Audit lookups (`AuditSeverity`, `RiskRating`, `FindingType`, `AuditOpinion`, etc.) use `TimestampedModel, StatusMixin` — they were designed with full user authorship tracking. Legal lookups use the **simpler** `BaseModel, StatusMixin` pattern because they are system-seeded reference data, not user-submitted records. Both patterns are valid and coexist in `lookups.py`.

---

## 2. Lookup Model Base Pattern

### Minimal lookup (no extra fields)

```python
class ExampleLookup(BaseModel, StatusMixin):
    """
    One-line description of purpose.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable identifier (e.g., 'high_court')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Human-readable display label"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional notes for admin reference"
    )

    class Meta:
        db_table = 'grc_example_lookup'
        ordering = ['name']
        verbose_name = 'Example Lookup'
        verbose_name_plural = 'Example Lookups'

    def __str__(self) -> str:
        return self.name
```

### Extended lookup (with ranked ordering or extra fields)

Used when order or weighting matters:

```python
class DirectivePriority(BaseModel, StatusMixin):
    code  = models.CharField(max_length=50, unique=True)
    name  = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=0, help_text="Lower = higher priority")

    class Meta:
        db_table  = 'grc_directive_priority'
        ordering  = ['order']
        ...
```

---

## 3. CourtLevel

### Purpose

Hierarchical classification of the court in which a litigation case is heard. Used by both `CaseDefendant` and `CasePlaintiff` to classify the case court.

### Business requirement

- Cases are classified by court level to support escalation rules and reporting segmentation.
- Court levels are admin-seeded; new levels can be added if FCC operates in a new jurisdiction without a code change.
- An existing `CourtLevel` **cannot be deleted** while cases reference it (`PROTECT` FK).

### Model definition

```python
class CourtLevel(BaseModel, StatusMixin):
    """
    Hierarchical classification of courts for litigation case tracking.
    Examples: Magistrate Court, High Court, Court of Appeal, Supreme Court.
    Admin-seeded; not user-created.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable identifier (e.g., 'high_court', 'court_of_appeal')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Full display name of the court level"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional notes for admin reference"
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Hierarchy order: lower = lower court (e.g., Magistrate=1, Supreme=5)"
    )

    class Meta:
        db_table = 'grc_court_level'
        ordering = ['order', 'name']
        verbose_name = 'Court Level'
        verbose_name_plural = 'Court Levels'

    def __str__(self) -> str:
        return self.name
```

### Field notes

| Field | Type | Notes |
|---|---|---|
| `code` | `CharField(unique=True)` | e.g., `'magistrate'`, `'high_court'`, `'court_of_appeal'`, `'supreme_court'` |
| `name` | `CharField` | e.g., `'High Court'` |
| `order` | `PositiveSmallIntegerField` | Ordering for report aggregation; lower = lower court hierarchy |
| `is_active` | `BooleanField` (from `StatusMixin`) | `False` hides from case registration dropdowns |

### FK references

| Entity | Field | on_delete |
|---|---|---|
| `CaseDefendant` | `court_level` | `PROTECT` |
| `CasePlaintiff` | `court_level` | `PROTECT` |

---

## 4. LitigationUrgencyLevel

### Purpose

Classifies how urgent a litigation case is. Drives case prioritisation, dashboard badges, and notification routing.

### Business requirement

- Set at case registration; can be updated by Legal Manager.
- Drives sort order on case dashboards — Critical cases float to the top.
- Not automatically recalculated — manually assigned by the registering officer or Legal Manager.

### Model definition

```python
class LitigationUrgencyLevel(BaseModel, StatusMixin):
    """
    Urgency classification for litigation cases.
    Drives prioritisation and dashboard colouring.
    Examples: Critical, High, Medium, Low.
    Admin-seeded; not user-created.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable code (e.g., 'critical', 'high', 'medium', 'low')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name shown in UI dropdowns and reports"
    )
    description = models.TextField(
        blank=True,
        help_text="Criteria for selecting this urgency level"
    )
    color_code = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Hex colour for UI badge (e.g., '#DC2626' for Critical)"
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Sort order: lower = higher urgency (Critical=1, Low=4)"
    )

    class Meta:
        db_table = 'grc_litigation_urgency_level'
        ordering = ['order']
        verbose_name = 'Litigation Urgency Level'
        verbose_name_plural = 'Litigation Urgency Levels'

    def __str__(self) -> str:
        return self.name
```

### Field notes

| Field | Notes |
|---|---|
| `color_code` | Used by frontend to render urgency badge colour; `#DC2626` (red) for Critical, `#F59E0B` for High, `#3B82F6` for Medium, `#6B7280` for Low |
| `order` | Ascending — `Critical=1` floats highest in sort |

### FK references

| Entity | Field | on_delete |
|---|---|---|
| `CaseDefendant` | `urgency_level` | `PROTECT` |
| `CasePlaintiff` | `urgency_level` | `PROTECT` |

---

## 5. LitigationRiskLevel

### Purpose

Classifies the financial and reputational risk of a litigation case. Used for DG-level reporting and case management prioritisation.

### Business requirement

- **Optional** at registration for the simplified Breach Report Intake (Department User path, E8.3).
- **Required** on the full registration form (Legal Officer / Registry Officer path).
- Distinct from `LitigationUrgencyLevel` — urgency is about timeline; risk is about impact severity.

### Model definition

```python
class LitigationRiskLevel(BaseModel, StatusMixin):
    """
    Financial and reputational impact classification for litigation cases.
    Distinct from urgency: urgency = timeline pressure, risk = impact severity.
    Examples: High Risk, Medium Risk, Low Risk.
    Admin-seeded; not user-created.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable code (e.g., 'high_risk', 'medium_risk', 'low_risk')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name shown in UI dropdowns"
    )
    description = models.TextField(
        blank=True,
        help_text="Criteria for assigning this risk level"
    )
    color_code = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Hex colour for UI badge"
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Sort order for reports: lower = higher risk"
    )

    class Meta:
        db_table = 'grc_litigation_risk_level'
        ordering = ['order']
        verbose_name = 'Litigation Risk Level'
        verbose_name_plural = 'Litigation Risk Levels'

    def __str__(self) -> str:
        return self.name
```

### FK references

| Entity | Field | Nullable | on_delete |
|---|---|---|---|
| `CaseDefendant` | `risk_level` | Yes — null for simplified registration | `PROTECT` |
| `CasePlaintiff` | `risk_level` | Yes — null for simplified registration | `PROTECT` |

---

## 6. MeetingMode

### Purpose

Specifies the physical attendance mode of a meeting. Used by `Meeting` to determine venue requirements and invitation copy.

### Business requirement

- Determines whether a physical venue, virtual link, or both are required fields on `Meeting`.
- When `mode = 'virtual'` or `'hybrid'`, `Meeting.venue_link` becomes a required field in the serializer.
- Admin can add new modes (e.g., `'asynchronous'`) without a code change.

### Model definition

```python
class MeetingMode(BaseModel, StatusMixin):
    """
    Physical attendance mode for a meeting.
    Determines venue/link requirements and UI rendering.
    Examples: Physical, Virtual, Hybrid.
    Admin-seeded; not user-created.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable code (e.g., 'physical', 'virtual', 'hybrid')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Physical', 'Virtual', 'Hybrid')"
    )
    requires_venue_link = models.BooleanField(
        default=False,
        help_text="Whether this mode requires a virtual meeting link"
    )

    class Meta:
        db_table = 'grc_meeting_mode'
        ordering = ['name']
        verbose_name = 'Meeting Mode'
        verbose_name_plural = 'Meeting Modes'

    def __str__(self) -> str:
        return self.name
```

### Field notes

| Field | Notes |
|---|---|
| `requires_venue_link` | Serializer validation reads this flag: if `True`, `venue_link` on `Meeting` must be non-blank |

### FK references

| Entity | Field | on_delete |
|---|---|---|
| `Meeting` | `meeting_mode` | `PROTECT` |

---

## 7. MeetingType

### Purpose

Classifies the formality category of a meeting (e.g., Ordinary, Extraordinary, Special). Carries a `quorum_percentage` field that the `Meeting.save()` override reads to auto-calculate the quorum member count threshold.

### Business requirement

- Each meeting type has a different quorum percentage (E3.5).
- Quorum threshold = `ceil(total_active_members × quorum_percentage / 100)`.
- `MeetingType` is the **only** place where quorum percentage is stored — it is not hardcoded anywhere else.
- Admin can add or adjust quorum percentages without a code change.

### Model definition

```python
class MeetingType(BaseModel, StatusMixin):
    """
    Classification of meeting formality.
    Determines quorum rules and validity conditions.
    Carries quorum_percentage which drives Meeting.calculated_quorum_threshold.
    Examples: Ordinary (51%), Extraordinary (51%), Special (67%).
    Admin-seeded; not user-created.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable code (e.g., 'ordinary', 'extraordinary', 'special')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Ordinary Meeting')"
    )
    quorum_percentage = models.PositiveSmallIntegerField(
        default=51,
        help_text=(
            "Minimum percentage of members required for quorum (e.g., 51 = majority, "
            "67 = two-thirds). Used by Meeting.save() to compute quorum threshold."
        )
    )
    description = models.TextField(
        blank=True,
        help_text="Conditions under which this meeting type is convened"
    )

    class Meta:
        db_table = 'grc_meeting_type'
        ordering = ['name']
        verbose_name = 'Meeting Type'
        verbose_name_plural = 'Meeting Types'

    def __str__(self) -> str:
        return f'{self.name} ({self.quorum_percentage}% quorum)'
```

### `quorum_percentage` usage in `Meeting.save()`

```python
# In Meeting.save() — reads quorum_percentage via FK traversal
try:
    total = self.governing_body.members.filter(is_active=True).count()
    pct   = self.meeting_type.quorum_percentage       # <-- reads from MeetingType
    self.calculated_quorum_threshold = math.ceil(total * pct / 100)
    if update_fields is not None:
        kwargs['update_fields'] = list(update_fields) + [
            'calculated_quorum_threshold', 'updated_at'
        ]
except Exception:
    pass
```

### FK references

| Entity | Field | on_delete |
|---|---|---|
| `Meeting` | `meeting_type` | `PROTECT` |

---

## 8. DirectivePriority

### Purpose

Classifies the urgency of a `MeetingDirective` (action items issued during a meeting). Drives visual ordering and optional SLA enforcement.

### Business requirement

- Assigned when the Secretary creates a directive (E5.7).
- Priority is visible on the Matters Arising list and drives sort order.
- `Critical` directives are flagged for immediate action; `Low` are tracked but not flagged.
- Shared between meeting directives and litigation directives (`LitigationDirective`).

### Model definition

```python
class DirectivePriority(BaseModel, StatusMixin):
    """
    Priority classification for directives (both meeting and litigation).
    Drives visual urgency indicators and Matters Arising sort order.
    Examples: Critical, High, Medium, Low.
    Admin-seeded; not user-created.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable code (e.g., 'critical', 'high', 'medium', 'low')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the priority level"
    )
    color_code = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Hex colour for UI badge (e.g., '#DC2626' for Critical)"
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Sort order: lower = higher priority displayed first (Critical=1)"
    )

    class Meta:
        db_table = 'grc_directive_priority'
        ordering = ['order']
        verbose_name = 'Directive Priority'
        verbose_name_plural = 'Directive Priorities'

    def __str__(self) -> str:
        return self.name
```

### FK references

| Entity | Field | Nullable | on_delete |
|---|---|---|---|
| `MeetingDirective` | `directive_priority` | No — required on directive creation | `PROTECT` |
| `LitigationDirective` | `directive_priority` | Yes — optional on DG directives | `PROTECT` |

---

## 9. DirectiveCategory

### Purpose

Thematic classification for directives (both meeting and litigation). Allows management to group and report on directives by theme.

### Business requirement

- Optional field on all directives — a directive can exist without a category.
- Admin-configurable; new categories can be added without a code change.
- Deactivating a category hides it from new directive forms but does not affect existing directives.
- Shared between `MeetingDirective` and `LitigationDirective`.

### Model definition

```python
class DirectiveCategory(BaseModel, StatusMixin):
    """
    Thematic category for directives (meeting and litigation).
    Allows grouping and reporting by theme.
    Admin-configurable; extensible without code changes.
    Examples: Legal Compliance, Corporate Governance, Finance, Operations, HR.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable category code (e.g., 'legal_compliance', 'finance')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the category"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what directives belong in this category"
    )

    class Meta:
        db_table = 'grc_directive_category'
        ordering = ['name']
        verbose_name = 'Directive Category'
        verbose_name_plural = 'Directive Categories'

    def __str__(self) -> str:
        return self.name
```

### FK references

| Entity | Field | Nullable | on_delete |
|---|---|---|---|
| `MeetingDirective` | `directive_category` | Yes — optional | `SET_NULL` |
| `LitigationDirective` | `directive_category` | Yes — optional | `SET_NULL` |

> `SET_NULL` (not `PROTECT`) — a deactivated or deleted category does not block the directive.

---

## 10. Admin Registration

All seven Legal lookup models must be registered in Django admin. They are added to the **existing** admin module for lookups, not a separate Legal admin file.

### Pattern (follows existing audit lookup admin registrations)

```python
# apps/core/admin.py — append to existing lookup registrations

from django.contrib import admin
from .models.lookups import (
    # ... existing audit lookups ...
    CourtLevel,
    LitigationUrgencyLevel,
    LitigationRiskLevel,
    MeetingMode,
    MeetingType,
    DirectivePriority,
    DirectiveCategory,
)


@admin.register(CourtLevel)
class CourtLevelAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'order', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'code']
    ordering      = ['order', 'name']


@admin.register(LitigationUrgencyLevel)
class LitigationUrgencyLevelAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'color_code', 'order', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'code']
    ordering      = ['order']


@admin.register(LitigationRiskLevel)
class LitigationRiskLevelAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'color_code', 'order', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'code']
    ordering      = ['order']


@admin.register(MeetingMode)
class MeetingModeAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'requires_venue_link', 'is_active']
    list_filter   = ['is_active', 'requires_venue_link']
    search_fields = ['name', 'code']


@admin.register(MeetingType)
class MeetingTypeAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'quorum_percentage', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'code']


@admin.register(DirectivePriority)
class DirectivePriorityAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'color_code', 'order', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'code']
    ordering      = ['order']


@admin.register(DirectiveCategory)
class DirectiveCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'code']
```

---

## 11. Serializers for Lookup Tables

### Placement

Lookup serializers live in `apps/core/serializers/lookup_serializers.py` (or the existing serializer file for lookups if one already exists). They are shared — the same serializer class is used in both list views and as a nested field in business entity serializers.

### Standard lookup serializer pattern

```python
from rest_framework import serializers
from apps.core.models.lookups import (
    CourtLevel,
    LitigationUrgencyLevel,
    LitigationRiskLevel,
    MeetingMode,
    MeetingType,
    DirectivePriority,
    DirectiveCategory,
)


class CourtLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CourtLevel
        fields = ['id', 'code', 'name', 'description', 'order', 'is_active']
        read_only_fields = ['id']


class LitigationUrgencyLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LitigationUrgencyLevel
        fields = ['id', 'code', 'name', 'description', 'color_code', 'order', 'is_active']
        read_only_fields = ['id']


class LitigationRiskLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LitigationRiskLevel
        fields = ['id', 'code', 'name', 'description', 'color_code', 'order', 'is_active']
        read_only_fields = ['id']


class MeetingModeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MeetingMode
        fields = ['id', 'code', 'name', 'requires_venue_link', 'is_active']
        read_only_fields = ['id']


class MeetingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MeetingType
        fields = ['id', 'code', 'name', 'quorum_percentage', 'description', 'is_active']
        read_only_fields = ['id']


class DirectivePrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model  = DirectivePriority
        fields = ['id', 'code', 'name', 'color_code', 'order', 'is_active']
        read_only_fields = ['id']


class DirectiveCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = DirectiveCategory
        fields = ['id', 'code', 'name', 'description', 'is_active']
        read_only_fields = ['id']
```

### How lookup serializers are used in business entity serializers

Two patterns:

**Pattern A — Nested read-only (full object in GET response)**

```python
class MeetingSerializer(serializers.ModelSerializer):
    meeting_mode   = MeetingModeSerializer(read_only=True)
    meeting_type   = MeetingTypeSerializer(read_only=True)
    # write via _id suffix:
    meeting_mode_id = serializers.PrimaryKeyRelatedField(
        queryset=MeetingMode.objects.filter(is_active=True),
        source='meeting_mode',
        write_only=True,
    )
    meeting_type_id = serializers.PrimaryKeyRelatedField(
        queryset=MeetingType.objects.filter(is_active=True),
        source='meeting_type',
        write_only=True,
    )

    class Meta:
        model  = Meeting
        fields = [
            'id', 'title', 'meeting_mode', 'meeting_mode_id',
            'meeting_type', 'meeting_type_id',
            # ...
        ]
```

**Pattern B — ID-only (flat response, lookup resolved by client)**

```python
class CaseDefendantSerializer(serializers.ModelSerializer):
    court_level_id    = serializers.PrimaryKeyRelatedField(
        queryset=CourtLevel.objects.filter(is_active=True),
        source='court_level',
    )
    urgency_level_id  = serializers.PrimaryKeyRelatedField(
        queryset=LitigationUrgencyLevel.objects.filter(is_active=True),
        source='urgency_level',
    )
    risk_level_id     = serializers.PrimaryKeyRelatedField(
        queryset=LitigationRiskLevel.objects.filter(is_active=True),
        source='risk_level',
        required=False, allow_null=True,
    )

    class Meta:
        model  = CaseDefendant
        fields = ['id', 'reference_number', 'court_level_id', 'urgency_level_id', 'risk_level_id', ...]
```

**Rule:** The write field always uses `queryset=<Model>.objects.filter(is_active=True)` — inactive lookups are not selectable via the API.

---

## 12. Seed Data

All lookup models are loaded via the existing `seed_lookup_data` management command. The command is **extended** (not replaced) to include Legal seed data.

### File location

`apps/core/management/commands/seed_lookup_data.py` — append a `_seed_legal_lookups()` private method.

### Seed values

#### CourtLevel

| code | name | order |
|---|---|---|
| `magistrate` | Magistrate Court | 1 |
| `high_court` | High Court | 2 |
| `labour_court` | Labour Court | 2 |
| `commercial_division` | Commercial Division (High Court) | 2 |
| `court_of_appeal` | Court of Appeal | 3 |
| `supreme_court` | Supreme Court | 4 |

#### LitigationUrgencyLevel

| code | name | color_code | order |
|---|---|---|---|
| `critical` | Critical | `#DC2626` | 1 |
| `high` | High | `#F59E0B` | 2 |
| `medium` | Medium | `#3B82F6` | 3 |
| `low` | Low | `#6B7280` | 4 |

#### LitigationRiskLevel

| code | name | color_code | order |
|---|---|---|---|
| `high_risk` | High Risk | `#DC2626` | 1 |
| `medium_risk` | Medium Risk | `#F59E0B` | 2 |
| `low_risk` | Low Risk | `#22C55E` | 3 |

#### MeetingMode

| code | name | requires_venue_link |
|---|---|---|
| `physical` | Physical | `False` |
| `virtual` | Virtual | `True` |
| `hybrid` | Hybrid | `True` |

#### MeetingType

| code | name | quorum_percentage |
|---|---|---|
| `ordinary` | Ordinary Meeting | 51 |
| `extraordinary` | Extraordinary Meeting | 51 |
| `special` | Special Meeting | 67 |

#### DirectivePriority

| code | name | color_code | order |
|---|---|---|---|
| `critical` | Critical | `#DC2626` | 1 |
| `high` | High | `#F59E0B` | 2 |
| `medium` | Medium | `#3B82F6` | 3 |
| `low` | Low | `#6B7280` | 4 |

#### DirectiveCategory (initial set — extensible)

| code | name |
|---|---|
| `legal_compliance` | Legal Compliance |
| `corporate_governance` | Corporate Governance |
| `finance` | Finance |
| `operations` | Operations |
| `human_resources` | Human Resources |
| `procurement` | Procurement |
| `ict` | ICT |

### Management command extension pattern

```python
# apps/core/management/commands/seed_lookup_data.py

class Command(BaseCommand):
    help = 'Seeds all lookup tables with initial data'

    def handle(self, *args, **options):
        self._seed_audit_lookups()    # existing
        self._seed_legal_lookups()    # new — appended

    def _seed_legal_lookups(self):
        from apps.core.models.lookups import (
            CourtLevel, LitigationUrgencyLevel, LitigationRiskLevel,
            MeetingMode, MeetingType, DirectivePriority, DirectiveCategory,
        )

        court_levels = [
            {'code': 'magistrate',         'name': 'Magistrate Court',              'order': 1},
            {'code': 'high_court',         'name': 'High Court',                    'order': 2},
            {'code': 'labour_court',       'name': 'Labour Court',                  'order': 2},
            {'code': 'commercial_division','name': 'Commercial Division (High Court)','order': 2},
            {'code': 'court_of_appeal',    'name': 'Court of Appeal',               'order': 3},
            {'code': 'supreme_court',      'name': 'Supreme Court',                 'order': 4},
        ]
        for item in court_levels:
            CourtLevel.objects.get_or_create(code=item['code'], defaults=item)

        urgency_levels = [
            {'code': 'critical', 'name': 'Critical', 'color_code': '#DC2626', 'order': 1},
            {'code': 'high',     'name': 'High',     'color_code': '#F59E0B', 'order': 2},
            {'code': 'medium',   'name': 'Medium',   'color_code': '#3B82F6', 'order': 3},
            {'code': 'low',      'name': 'Low',      'color_code': '#6B7280', 'order': 4},
        ]
        for item in urgency_levels:
            LitigationUrgencyLevel.objects.get_or_create(code=item['code'], defaults=item)

        risk_levels = [
            {'code': 'high_risk',   'name': 'High Risk',   'color_code': '#DC2626', 'order': 1},
            {'code': 'medium_risk', 'name': 'Medium Risk', 'color_code': '#F59E0B', 'order': 2},
            {'code': 'low_risk',    'name': 'Low Risk',    'color_code': '#22C55E', 'order': 3},
        ]
        for item in risk_levels:
            LitigationRiskLevel.objects.get_or_create(code=item['code'], defaults=item)

        meeting_modes = [
            {'code': 'physical', 'name': 'Physical', 'requires_venue_link': False},
            {'code': 'virtual',  'name': 'Virtual',  'requires_venue_link': True},
            {'code': 'hybrid',   'name': 'Hybrid',   'requires_venue_link': True},
        ]
        for item in meeting_modes:
            MeetingMode.objects.get_or_create(code=item['code'], defaults=item)

        meeting_types = [
            {'code': 'ordinary',       'name': 'Ordinary Meeting',       'quorum_percentage': 51},
            {'code': 'extraordinary',  'name': 'Extraordinary Meeting',  'quorum_percentage': 51},
            {'code': 'special',        'name': 'Special Meeting',        'quorum_percentage': 67},
        ]
        for item in meeting_types:
            MeetingType.objects.get_or_create(code=item['code'], defaults=item)

        priorities = [
            {'code': 'critical', 'name': 'Critical', 'color_code': '#DC2626', 'order': 1},
            {'code': 'high',     'name': 'High',     'color_code': '#F59E0B', 'order': 2},
            {'code': 'medium',   'name': 'Medium',   'color_code': '#3B82F6', 'order': 3},
            {'code': 'low',      'name': 'Low',      'color_code': '#6B7280', 'order': 4},
        ]
        for item in priorities:
            DirectivePriority.objects.get_or_create(code=item['code'], defaults=item)

        categories = [
            {'code': 'legal_compliance',    'name': 'Legal Compliance'},
            {'code': 'corporate_governance','name': 'Corporate Governance'},
            {'code': 'finance',             'name': 'Finance'},
            {'code': 'operations',          'name': 'Operations'},
            {'code': 'human_resources',     'name': 'Human Resources'},
            {'code': 'procurement',         'name': 'Procurement'},
            {'code': 'ict',                 'name': 'ICT'},
        ]
        for item in categories:
            DirectiveCategory.objects.get_or_create(code=item['code'], defaults=item)

        self.stdout.write(self.style.SUCCESS('Legal lookup tables seeded.'))
```

---

## 13. FK Usage Reference

Complete reference mapping every business entity field to its lookup model.

### Meeting domain

| Entity | FK field | Lookup model | Nullable | on_delete |
|---|---|---|---|---|
| `Meeting` | `meeting_mode` | `MeetingMode` | No | `PROTECT` |
| `Meeting` | `meeting_type` | `MeetingType` | No | `PROTECT` |
| `MeetingDirective` | `directive_priority` | `DirectivePriority` | No | `PROTECT` |
| `MeetingDirective` | `directive_category` | `DirectiveCategory` | Yes | `SET_NULL` |

### Litigation domain

| Entity | FK field | Lookup model | Nullable | on_delete |
|---|---|---|---|---|
| `CaseDefendant` | `court_level` | `CourtLevel` | No | `PROTECT` |
| `CaseDefendant` | `urgency_level` | `LitigationUrgencyLevel` | No | `PROTECT` |
| `CaseDefendant` | `risk_level` | `LitigationRiskLevel` | Yes | `PROTECT` |
| `CasePlaintiff` | `court_level` | `CourtLevel` | No | `PROTECT` |
| `CasePlaintiff` | `urgency_level` | `LitigationUrgencyLevel` | No | `PROTECT` |
| `CasePlaintiff` | `risk_level` | `LitigationRiskLevel` | Yes | `PROTECT` |
| `LitigationDirective` | `directive_priority` | `DirectivePriority` | Yes | `PROTECT` |
| `LitigationDirective` | `directive_category` | `DirectiveCategory` | Yes | `SET_NULL` |

### Lookup endpoints

Each lookup table exposes a **read-only list endpoint** for the frontend to populate dropdowns. These are public GET endpoints — no authentication required (or JWT-optional per system policy):

| Lookup | Endpoint |
|---|---|
| `CourtLevel` | `GET /api/v1/lookups/court-levels/` |
| `LitigationUrgencyLevel` | `GET /api/v1/lookups/litigation-urgency-levels/` |
| `LitigationRiskLevel` | `GET /api/v1/lookups/litigation-risk-levels/` |
| `MeetingMode` | `GET /api/v1/lookups/meeting-modes/` |
| `MeetingType` | `GET /api/v1/lookups/meeting-types/` |
| `DirectivePriority` | `GET /api/v1/lookups/directive-priorities/` |
| `DirectiveCategory` | `GET /api/v1/lookups/directive-categories/` |

All endpoints return `is_active=True` records only. The `is_active` field is included in the response so the frontend can handle deactivated values that are already FK-referenced.

---

## 14. Lookup Deactivation Rules

### What deactivation does

Setting `is_active=False` on a lookup:

1. **Hides** the value from all creation dropdowns (serializer `queryset` filter enforces this).
2. **Does NOT affect** existing records that already reference the lookup via FK.
3. **Does NOT cascade** any status change to child entities.
4. **Is reversible** — re-activating restores the value in dropdowns.

### What deactivation does NOT do

- It does not change the `status` of any `CaseDefendant`, `Meeting`, or directive that references it.
- It does not prevent reads — existing records can still be fetched with their deactivated lookup FK fully populated in nested serializer output.

### Deactivation validation in serializers

```python
# Automatically enforced by queryset filter on PrimaryKeyRelatedField
court_level_id = serializers.PrimaryKeyRelatedField(
    queryset=CourtLevel.objects.filter(is_active=True),  # <-- excludes inactive
    source='court_level',
)
```

If a client submits the UUID of an inactive `CourtLevel`, DRF raises a `ValidationError` ("Invalid pk — object does not exist") because the PK is not in the filtered queryset.

### `PROTECT` vs `SET_NULL` deactivation behaviour

| on_delete | Deactivation effect | Use case |
|---|---|---|
| `PROTECT` | Lookup with active FKs cannot be hard-deleted; must deactivate instead | Required lookups (court level, urgency, mode, type, priority) |
| `SET_NULL` | FK field on child set to NULL when lookup is deleted | Optional lookups (directive category) |

> In practice, **hard-delete of any lookup is avoided**. Deactivation (`is_active=False`) is the
> standard operation. `PROTECT` and `SET_NULL` are guards against accidental DB-level deletes only.

### Migration note

When a new lookup value is needed (e.g., a new court level):
1. Admin navigates to `/admin/core/courtlevel/add/`.
2. Fills in `code`, `name`, `order`, saves.
3. Value immediately available in creation dropdowns — **no migration, no deployment required**.

When a lookup value is no longer applicable:
1. Admin sets `is_active=False`.
2. Value disappears from dropdowns — **no migration, no deployment required**.
3. Existing records retain the FK reference and still display the deactivated value (serializer reads it without `is_active` filter).

---

*End of Legal_Module_Lookup_Tables.md*
*Next: Part 5 — Serializers (all Legal entities)*
