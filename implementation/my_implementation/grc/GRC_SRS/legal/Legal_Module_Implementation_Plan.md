# Legal Module — Complete Implementation Plan (Backend + Gap Fixes)
**Service:** `grc-service`
**Phase:** ✅ Backend Complete — Ready for Frontend Implementation
**Document type:** Single authoritative reference — backend implementation record + frontend API guide

> **This document supersedes `Legal_SRS_Gap_Fixes.md`.**  
> All 14 SRS gaps have been identified, fixed, and verified. Additionally, 2 further backend endpoints  
> were added during A.17 frontend plan verification (A17-Fix-1, A17-Fix-2). All fixes are integrated  
> inline into the relevant steps and summarised in Appendix E at the end of this file.  
> When planning the frontend, use **Appendix D** (Complete API Reference) as the primary reference.

**Reference files used throughout this plan:**
- `LEGAL_DOMAIN_EXTRACTION.md` — business entity inventory and domain descriptions
- `Legal_Module_Architecture_Overview.md` — module structure within grc-service
- `Legal_Module_Architecture_Mapping.md` — entity-to-file mapping
- `Internal_Audit_Backend_Patterns.md` — patterns to replicate exactly
- `Legal_Module_Base_Models_Mixins.md` — base class inheritance rules (Phase 5A)
- `Legal_Module_Data_Models_Part1.md` — core entity field definitions (Phase 5B-1)
- `Legal_Module_Data_Models_Part2.md` — entity relationships and FK map (Phase 5B-2)
- `Legal_Module_Data_Models_Part3.md` — DB table registry and design decisions (Phase 5B-3)
- `Legal_Module_Lookup_Tables.md` — 7 lookup model definitions (Phase 5C)
- `Legal_Module_Workflow_Integration.md` — workflow YAML templates and service patterns (Phase 5D)
- `GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md` — canonical backend reference for this service

---

## Table of Contents

1. [Prerequisites & Environment](#1-prerequisites--environment)
2. [Section Overview & Sequence](#2-section-overview--sequence)
3. [Step 1 — Lookup Tables](#3-step-1--lookup-tables)
4. [Step 2 — Business Entity Models](#4-step-2--business-entity-models)
5. [Step 3 — Migrations](#5-step-3--migrations)
6. [Step 4 — Workflow YAML Templates](#6-step-4--workflow-yaml-templates)
7. [Step 5 — Service Layer](#7-step-5--service-layer)
8. [Step 6 — Serializers](#8-step-6--serializers)
9. [Step 7 — RBAC: Permissions](#9-step-7--rbac-permissions)
10. [Step 8 — Views](#10-step-8--views)
11. [Step 9 — URL Registration](#11-step-9--url-registration)
12. [Step 10 — Celery Background Tasks](#12-step-10--celery-background-tasks)
13. [Step 11 — Kafka Events](#13-step-11--kafka-events)
14. [Step 12 — Seed Data & Management Commands](#14-step-12--seed-data--management-commands)
15. [Step 13 — Testing](#15-step-13--testing)
16. [Step 14 — Deployment Checklist](#16-step-14--deployment-checklist)
17. [Appendix A — Complete File Manifest](#appendix-a--complete-file-manifest)
18. [Appendix B — DB Table Registry](#appendix-b--db-table-registry)
19. [Appendix C — Implementation Completion Notes](#appendix-c--implementation-completion-notes)
20. [Appendix D — Complete API Reference for Frontend](#appendix-d--complete-api-reference-for-frontend)
21. [Appendix E — Gap Fixes Record](#appendix-e--gap-fixes-record)

---

## 1. Prerequisites & Environment

### 1.1 Service dependencies that must be running

| Service | Purpose in Legal module |
|---|---|
| `iam-service` | JWT validation, user profile resolution |
| `work-orchestration-service` | Workflow plan lifecycle for 10 Legal entities |
| `corporate-service` | GoverningBody member sync via Kafka |
| `document-records-service` | File storage for attachments (Minutes, Hearing, Filing documents) |
| `message-broker` (Kafka) | Domain event publishing and org-sync consumption |

All of the above must be healthy before running any Legal workflow-related endpoint.

### 1.2 Local dev startup

```bash
# From workspace root — start full stack
docker-compose -f docker-compose.yml up -d

# grc-service only with dependencies
docker-compose -f docker-compose.yml up -d grc-service iam-service work-orchestration-service message-broker

# Verify grc-service health
curl http://localhost:8003/health/
```

### 1.3 Environment variables required

All variables already exist in `env.example`. No new env vars are required for the Legal module. The module reuses:
- `JWT_SECRET_KEY` — used by `IAMJWTAuthentication`
- `WO_SERVICE_URL` + `WO_SERVICE_TOKEN` — used by `OrchestrationClient`
- `IAM_SERVICE_URL` + `IAM_SERVICE_TOKEN` — used by `IAMClient`
- `DRS_SERVICE_URL` + `DRS_SERVICE_TOKEN` — used by `DocumentServiceClient`
- `KAFKA_BOOTSTRAP_SERVERS` — used by Kafka producer/consumer
- `DATABASE_URL` — PostgreSQL connection (Legal tables go into the same DB schema)

### 1.4 Useful quick-check commands

```bash
# Run from inside the grc-service container or a local venv
docker exec -it grc-service python manage.py check
docker exec -it grc-service python manage.py showmigrations core
```

---

## 2. Section Overview & Sequence

Implement in this exact order. Each step has a dependency on the previous one.

```
Step 1  — Lookup Tables   (models only — no migration yet)
Step 2  — Business Entity Models   (models only — no migration yet)
Step 3  — Migrations   (makemigrations + migrate)
Step 4  — Workflow YAML Templates   (extend workflows.yaml)
Step 5  — Service Layer   (6 service classes, one per workflow process)
Step 6  — Serializers   (one file: legal_serializers.py)
Step 7  — RBAC   (extend grc-service.json + permissions_jwt.py)
Step 8  — Views   (~10 view files)
Step 9  — URL Registration   (legal.py + wire into urls.py)
Step 10 — Celery Background Tasks   (2 new task files)
Step 11 — Kafka Events   (event dataclasses + event types)
Step 12 — Seed Data   (extend seed_lookup_data + register_workflow_templates)
Step 13 — Testing
Step 14 — Deployment Checklist
```

**Do not create view or serializer files before running migrations.** Importing models that do not yet have tables will cause errors during container startup.

---

## 3. Step 1 — Lookup Tables

**File to edit:** `apps/core/models/lookups.py`
**Design reference:** `Legal_Module_Lookup_Tables.md` §1–§7

Append the following 7 lookup model classes at the **bottom** of `lookups.py`, after the last existing class. Do not modify any existing class.

All 7 use `BaseModel, StatusMixin` (not `TimestampedModel`) — legal lookups do not require audit fields. Each uses `db_table` in the `legal_` namespace.

### Models to append

```python
# ── Legal Lookup Tables ────────────────────────────────────────────────

class CourtLevel(BaseModel, StatusMixin):
    """Hierarchy of courts: tribunal → high_court → court_of_appeal → supreme_court"""
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table  = 'legal_court_level'
        ordering  = ['sort_order']

    def __str__(self):
        return self.name


class LitigationUrgencyLevel(BaseModel, StatusMixin):
    """Case urgency: low → medium → high → critical"""
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color_code  = models.CharField(max_length=7, blank=True)   # hex, e.g. '#FF0000'
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table  = 'legal_litigation_urgency_level'
        ordering  = ['sort_order']

    def __str__(self):
        return self.name


class LitigationRiskLevel(BaseModel, StatusMixin):
    """Litigation risk exposure: low → medium → high → very_high"""
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color_code  = models.CharField(max_length=7, blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table  = 'legal_litigation_risk_level'
        ordering  = ['sort_order']

    def __str__(self):
        return self.name


class MeetingMode(BaseModel, StatusMixin):
    """in_person | virtual | hybrid"""
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table  = 'legal_meeting_mode'
        ordering  = ['sort_order']

    def __str__(self):
        return self.name


class MeetingType(BaseModel, StatusMixin):
    """ordinary | extraordinary | emergency | annual_general"""
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table  = 'legal_meeting_type'
        ordering  = ['sort_order']

    def __str__(self):
        return self.name


class DirectivePriority(BaseModel, StatusMixin):
    """Priority labels for directives issued from meeting minutes"""
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    color_code  = models.CharField(max_length=7, blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table  = 'legal_directive_priority'
        ordering  = ['sort_order']

    def __str__(self):
        return self.name


class DirectiveCategory(BaseModel, StatusMixin):
    """Category of directive action: administrative | compliance | legal | financial | operational"""
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table  = 'legal_directive_category'
        ordering  = ['sort_order']

    def __str__(self):
        return self.name
```

**DB table names produced:** `legal_court_level`, `legal_litigation_urgency_level`, `legal_litigation_risk_level`, `legal_meeting_mode`, `legal_meeting_type`, `legal_directive_priority`, `legal_directive_category`

---

## 4. Step 2 — Business Entity Models

### 4.1 Create the entity file

**New file:** `apps/core/models/legal_entities.py`
**Design reference:** `Legal_Module_Data_Models_Part1.md`, `Legal_Module_Data_Models_Part2.md`, `Legal_Module_Data_Models_Part3.md`

File header and imports:

```python
"""
Legal Module — Core Entity Models
References:
  Legal_Module_Data_Models_Part1.md  — entity field definitions
  Legal_Module_Data_Models_Part2.md  — FK/relationship map
  Legal_Module_Data_Models_Part3.md  — DB table registry, constraints, design decisions
"""
from django.db import models
from .base import TimestampedModel, StatusMixin, WorkflowMixin
from .lookups import (
    CourtLevel, LitigationUrgencyLevel, LitigationRiskLevel,
    MeetingMode, MeetingType, DirectivePriority, DirectiveCategory,
)
```

### 4.2 Entity groups and their db_table names

The 28 business entities go in this file. Define them in the dependency order below
(parent entity before child entity in every FK relationship).

**Group 1 — Governing Body & Members (no workflow)**

| Class | `db_table` | Key FKs |
|---|---|---|
| `GoverningBody` | `legal_governing_body` | — |
| `GoverningBodyMember` | `legal_governing_body_member` | `GoverningBody` |

`GoverningBody` carries `external_id` (UUID from Corporate Service) and `last_sync`.
`GoverningBodyMember` carries `external_id`, `member_user_id` (UUID — IAM ref), `role`, `term_start`, `term_end`.

**Group 2 — Meeting Management (Meeting has WorkflowMixin)**

| Class | `db_table` | Key FKs |
|---|---|---|
| `Meeting` | `legal_meeting` | `GoverningBody`, `MeetingType`, `MeetingMode` |
| `MeetingAttendance` | `legal_meeting_attendance` | `Meeting` |
| `Minutes` | `legal_minutes` | `Meeting` (OneToOneField), `WorkflowMixin` |
| `MeetingDirective` | `legal_meeting_directive` | `Minutes`, `DirectivePriority`, `DirectiveCategory` |

`Meeting` — `WorkflowMixin` ✓. Status: `draft → registered → invitations_sent → agenda_shared → quorum_ready → ongoing → postponed → closed → cancelled → rescheduled`.
`Minutes` — `WorkflowMixin` ✓. Status: `draft → under_review → approved`.
`MeetingDirective` — no workflow. `responsible_user_id` is UUID (IAM ref). `due_date`, `completion_date`, `is_overdue` (boolean, set by Celery task).

**Group 3 — Litigation Cases (CaseDefendant/CasePlaintiff have WorkflowMixin)**

| Class | `db_table` | Key FKs |
|---|---|---|
| `CaseDefendant` | `legal_case_defendant` | `CourtLevel`, `LitigationUrgencyLevel`, `LitigationRiskLevel` |
| `CasePlaintiff` | `legal_case_plaintiff` | `CourtLevel`, `LitigationUrgencyLevel`, `LitigationRiskLevel` |

Both carry `reference_number` (unique), `case_number`, `parties` (JSONField), `assigned_legal_officer_id` (UUID), `status` (`open → active → closed → appealed`).

**Group 4 — Shared Discriminator Entities (XOR CheckConstraint pattern)**

These 3 entities each attach to EITHER a `CaseDefendant` OR a `CasePlaintiff` — never both.

| Class | `db_table` | FK options |
|---|---|---|
| `Hearing` | `legal_hearing` | `case_defendant` FK or `case_plaintiff` FK (XOR) |
| `LitigationDirective` | `legal_litigation_directive` | `case_defendant` FK or `case_plaintiff` FK (XOR) |
| `TaskLitigation` | `legal_task_litigation` | `case_defendant` FK or `case_plaintiff` FK (XOR) |

Each has a `CheckConstraint` — see §4.3 below.

**Group 5 — Sub-entities per Case (FilingDefendant/Plaintiff, SettlementDefendant/Plaintiff, JudgmentDefendant/Plaintiff — all have WorkflowMixin)**

| Class | `db_table` | Parent FK |
|---|---|---|
| `FilingDefendant` | `legal_filing_defendant` | `CaseDefendant` |
| `FilingPlaintiff` | `legal_filing_plaintiff` | `CasePlaintiff` |
| `SettlementDefendant` | `legal_settlement_defendant` | `CaseDefendant` |
| `SettlementPlaintiff` | `legal_settlement_plaintiff` | `CasePlaintiff` |
| `JudgmentDefendant` | `legal_judgment_defendant` | `CaseDefendant` |
| `JudgmentPlaintiff` | `legal_judgment_plaintiff` | `CasePlaintiff` |

**Group 6 — Appeal (auto-created on final Judgment)**

| Class | `db_table` | FK |
|---|---|---|
| `AppealDefendant` | `legal_appeal_defendant` | `JudgmentDefendant` (OneToOneField) |
| `AppealPlaintiff` | `legal_appeal_plaintiff` | `JudgmentPlaintiff` (OneToOneField) |

Appeals are created inside `transaction.atomic()` at the moment a Judgment is recorded.
Do NOT add `WorkflowMixin` to Appeal — it is a record of an appeal outcome, not a managed process.

**Group 7 — Legal Notices (standalone, no workflow)**

| Class | `db_table` | FK |
|---|---|---|
| `LegalNotice` | `legal_notice` | — (but has `related_case_defendant` and `related_case_plaintiff`, both optional/nullable) |

### 4.3 CheckConstraint: XOR pattern for shared discriminator entities

For `Hearing`, `LitigationDirective`, and `TaskLitigation`, add this constraint inside `Meta`:

```python
class Meta:
    db_table = 'legal_hearing'
    constraints = [
        models.CheckConstraint(
            name='legal_hearing_case_xor',
            check=(
                models.Q(case_defendant__isnull=False, case_plaintiff__isnull=True) |
                models.Q(case_defendant__isnull=True,  case_plaintiff__isnull=False)
            ),
        )
    ]
```

Apply the same pattern for `LitigationDirective` (`legal_litigation_directive_case_xor`) and `TaskLitigation` (`legal_task_litigation_case_xor`).

### 4.4 WorkflowMixin override methods

Every `WorkflowMixin` entity must define `get_workflow_context()` and `get_workflow_metadata()`.
Use the Internal Audit pattern from `GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md §6.4` exactly.

Example for `Meeting`:

```python
def get_workflow_context(self):
    return {
        "meeting_id":        str(self.id),
        "governing_body_id": str(self.governing_body_id),
        "prepared_by":       str(self.created_by),
        "applicant_id":      "",   # overwritten at service layer
    }

def get_workflow_metadata(self):
    meta = {
        "entity_type":     "meeting",
        "entity_id":       str(self.id),
        "reference_number": self.reference_number,
        "title":           str(self),
        "status":          self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, "meeting")
```

Implement equivalent for `Minutes`, `CaseDefendant`, `CasePlaintiff`, `FilingDefendant`, `FilingPlaintiff`, `SettlementDefendant`, `SettlementPlaintiff`, `JudgmentDefendant`, `JudgmentPlaintiff`.

### 4.5 Status choices reference

| Entity | Status choices |
|---|---|
| `Meeting` | `draft → registered → invitations_sent → agenda_shared → quorum_ready → ongoing → postponed → closed → cancelled → rescheduled` |
| `Minutes` | `draft → under_review → approved` |
| `MeetingDirective` | `pending → in_progress → completed → overdue` |
| `CaseDefendant` / `CasePlaintiff` | `open → active → closed → appealed` |
| `Hearing` | `scheduled → completed → adjourned → cancelled` |
| `FilingDefendant` / `FilingPlaintiff` | `draft → submitted → accepted → rejected` |
| `SettlementDefendant` / `SettlementPlaintiff` | `draft → proposed → approved → rejected → executed` |
| `JudgmentDefendant` / `JudgmentPlaintiff` | `pending → partial → final → appealed` |
| `AppealDefendant` / `AppealPlaintiff` | `pending → active → dismissed → upheld → withdrawn` |
| `LitigationDirective` | `open → in_progress → closed` |
| `TaskLitigation` | `pending → in_progress → completed → overdue` |
| `LegalNotice` | `draft → published → acknowledged → expired` |

### 4.6 Reference number patterns

Reference numbers are auto-generated in the view layer (same pattern as Internal Audit):

| Entity | Pattern | Example |
|---|---|---|
| `Meeting` | `MTG-{YYYYMM}-{seq:03d}` | `MTG-202501-001` |
| `CaseDefendant` | `LCD-{YYYY}-{seq:04d}` | `LCD-2025-0001` |
| `CasePlaintiff` | `LCP-{YYYY}-{seq:04d}` | `LCP-2025-0001` |
| `LegalNotice` | `LN-{YYYY}-{seq:03d}` | `LN-2025-001` |

Generate via an atomic DB counter using the same pattern as `grc_audit_reference_counter` (see `Legal_Module_Data_Models_Part3.md §10` for counter model design). Add `LegalCaseCounter` to `apps/core/models/counters.py` if that file exists, otherwise add to `legal_entities.py`.

### 4.7 Export from `__init__.py`

After defining all models, open `apps/core/models/__init__.py` and add:

```python
from .legal_entities import (
    GoverningBody, GoverningBodyMember,
    Meeting, MeetingAttendance, Minutes, MeetingDirective,
    CaseDefendant, CasePlaintiff,
    Hearing, LitigationDirective, TaskLitigation,
    FilingDefendant, FilingPlaintiff,
    SettlementDefendant, SettlementPlaintiff,
    JudgmentDefendant, JudgmentPlaintiff,
    AppealDefendant, AppealPlaintiff,
    LegalNotice,
)
```

Also export the 7 new lookup models from `lookups.py` into the same `__init__.py`:

```python
from .lookups import (
    # ... existing exports ...
    CourtLevel, LitigationUrgencyLevel, LitigationRiskLevel,
    MeetingMode, MeetingType, DirectivePriority, DirectiveCategory,
)
```

### 4.8 Register entity paths for workflow metadata

Open `apps/core/workflow_entity_paths.py` and add entries for every WorkflowMixin entity.
Pattern used by existing audit entities:

```python
ENTITY_PATH_MAP = {
    # ... existing ...
    "meeting":              "/legal/meetings/{entity_id}",
    "minutes":              "/legal/meetings/{entity_id}/minutes",
    "case_defendant":       "/legal/cases/defendant/{entity_id}",
    "case_plaintiff":       "/legal/cases/plaintiff/{entity_id}",
    "filing_defendant":     "/legal/cases/defendant/{entity_id}/filings",
    "filing_plaintiff":     "/legal/cases/plaintiff/{entity_id}/filings",
    "settlement_defendant": "/legal/cases/defendant/{entity_id}/settlements",
    "settlement_plaintiff": "/legal/cases/plaintiff/{entity_id}/settlements",
    "judgment_defendant":   "/legal/cases/defendant/{entity_id}/judgments",
    "judgment_plaintiff":   "/legal/cases/plaintiff/{entity_id}/judgments",
}
```

---

## 5. Step 3 — Migrations

**Run only after completing Steps 1 and 2.**

```bash
# Inside the grc-service container (or local venv with DATABASE_URL set)
python manage.py makemigrations core --name legal_module_initial

# Inspect the generated migration before applying
# Expected: 35 new CreateModel statements (7 lookup + 28 business entities)
python manage.py showmigrations core

# Apply
python manage.py migrate core
```

**If `makemigrations` produces an unexpected split** (two migration files), verify that both `lookups.py` and `legal_entities.py` are in the same Django app (`core`) and that the `__init__.py` imports are correct.

**Expected table count after migration:** 35 new tables with `legal_` prefix + no changes to existing `grc_` tables.

**Verify:**
```bash
python manage.py dbshell
# In psql:
\dt legal_*
# Should list all 35 legal_ tables
\q
```

---

## 6. Step 4 — Workflow YAML Templates

**File to edit:** `apps/core/workflows/workflows.yaml`
**Design reference:** `Legal_Module_Workflow_Integration.md` §4

Append 6 new YAML template blocks at the bottom of `workflows.yaml`. These are the codes the service layer will reference:

| Template code | Used by |
|---|---|
| `grc.legal_meeting_lifecycle` | `Meeting` |
| `grc.legal_minutes_approval` | `Minutes` |
| `grc.legal_case_closure` | `CaseDefendant`, `CasePlaintiff` |
| `grc.legal_filing_approval` | `FilingDefendant`, `FilingPlaintiff` |
| `grc.legal_settlement_approval` | `SettlementDefendant`, `SettlementPlaintiff` |
| `grc.legal_judgment_decision` | `JudgmentDefendant`, `JudgmentPlaintiff` |

Use the template skeleton from `Legal_Module_Workflow_Integration.md §3` exactly.
Stage definitions, assignees, and `status_on_complete` values are fully specified in `Legal_Module_Workflow_Integration.md §4`.

> **Inline fallback stages are strictly prohibited.** Do not add `get_workflow_stages()` to any Legal model. Templates must be loaded via `register_workflow_templates` management command (Step 12).

> **GAP-06 fix applied:** `grc.legal_filing_approval` was extended from 2 stages to 4 stages:  
> `filing_officer_review → legal_manager_review → dg_filing_review → filing_confirmed`.  
> This aligns the workflow with the 6 status choices on `FilingDefendant`/`FilingPlaintiff`:  
> `draft → under_review_lm → approved_lm → under_review_dg → approved → filed`.

After editing `workflows.yaml`, do a quick syntax check:

```bash
python manage.py shell -c "
import yaml
with open('apps/core/workflows/workflows.yaml') as f:
    data = yaml.safe_load(f)
print(f'OK — {len(data)} templates loaded')
"
```

---

## 7. Step 5 — Service Layer

**New files to create (6 files):**

```
apps/core/services/legal_meeting_service.py
apps/core/services/legal_minutes_service.py
apps/core/services/legal_case_service.py
apps/core/services/legal_filing_service.py
apps/core/services/legal_settlement_service.py
apps/core/services/legal_judgment_service.py
```

**Design reference:** `Legal_Module_Workflow_Integration.md` §7–§8

Each service file follows the exact pattern from `GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md §6.5`. The minimum 5 standard methods are:

```python
class LegalMeetingService:
    WORKFLOW_TEMPLATE_CODE = "grc.legal_meeting_lifecycle"

    def submit_for_approval(self, meeting_id: str, submitter_id: str) -> None: ...
    def get_workflow_status(self, meeting_id: str) -> dict: ...
    def get_workflow_history(self, meeting_id: str) -> list: ...
    def advance_workflow_stage(self, meeting_id: str, action: str, actor_id: str, comment: str = '') -> None: ...
    def cancel_workflow_plan(self, meeting_id: str, actor_id: str, reason: str = '') -> None: ...
```

**Critical requirements for every service method that calls WO:**

1. Load entity with `select_for_update()` inside `@transaction.atomic`
2. Set `context['applicant_id'] = submitter_id` at the service layer (not the model)
3. On `start_workflow()` success — call `entity.start_workflow(plan_id=…)` and update `status`
4. Save only the workflow fields using `update_fields=[…]` — never a full `.save()`

See `Legal_Module_Workflow_Integration.md §8` for the full body of each method.

**Special cases:**

- `LegalCaseService`: handles both `CaseDefendant` and `CasePlaintiff` — use a `entity_type` discriminator param to route to the correct model.
- `LegalFilingService`, `LegalSettlementService`, `LegalJudgmentService`: same dual-entity pattern.
- `LegalJudgmentService`: after `submit_for_approval` completes with status `final`, the service must call `_auto_create_appeal()` inside `transaction.atomic()` to create `AppealDefendant` or `AppealPlaintiff`. See `Legal_Module_Data_Models_Part3.md §9` for the atomic appeal-create pattern.

> **GAP-07 fix applied:** `LegalJudgmentService.process_appeal_decision()` was fully implemented.  
> When DG decides "appeal", it atomically:
> 1. Creates a `FilingDefendant`/`FilingPlaintiff` of type `notice_of_appeal`
> 2. Creates a `TaskLitigation` with the appeal deadline
> 3. Creates an `AppealDefendant`/`AppealPlaintiff` record
> 4. Updates parent case status to `appeal_filed`
> 5. Publishes `grc.legal.judgment.appeal_initiated` Kafka event
>
> On DG decision = "accept", no auto-creation occurs.

---

## 8. Step 6 — Serializers

**New file:** `apps/api/serializers/legal_serializers.py`
**Reference:** `GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md §8`; `Legal_Module_Data_Models_Part1.md`

### 8.1 File structure

```python
"""
Legal Module Serializers
Pattern: read FK = nested object, write FK = _id UUID field
"""
from rest_framework import serializers
from apps.core.models.legal_entities import (...)
from apps.core.models.lookups import (
    CourtLevel, LitigationUrgencyLevel, LitigationRiskLevel,
    MeetingMode, MeetingType, DirectivePriority, DirectiveCategory,
)
from .lookup_serializers import (...)  # reuse existing lookup serializer base if available
```

### 8.2 Lookup serializers

Add the 7 legal lookup serializers to `apps/api/serializers/lookup_serializers.py` (append to existing file — do not create a new one):

```python
class CourtLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CourtLevel
        fields = ['id', 'code', 'name', 'description', 'sort_order', 'is_active']


class LitigationUrgencyLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LitigationUrgencyLevel
        fields = ['id', 'code', 'name', 'description', 'color_code', 'sort_order', 'is_active']

# ... repeat for the remaining 5 lookup types
```

### 8.3 Business entity serializer rules

| Rule | How to apply |
|---|---|
| FK read (GET) | `court_level = CourtLevelSerializer(read_only=True)` |
| FK write (POST/PATCH) | `court_level_id = serializers.UUIDField(write_only=True)` |
| Auto-generated fields | `required=False` + `allow_blank=True` in `extra_kwargs` |
| Creator UUID fields | `created_by`, `modified_by`, `assigned_legal_officer_id` — `required=False`, set in view |
| JSONField | `default=list` fields declared as `serializers.ListField(child=..., required=False)` OR pass-through as `serializers.JSONField(required=False)` |
| WorkflowMixin fields | Declare as `read_only=True` in `extra_kwargs` — never written by client |

### 8.4 Serializers to create

One serializer class per entity, grouped as below:

**Lookup serializers (in `lookup_serializers.py`):**
`CourtLevelSerializer`, `LitigationUrgencyLevelSerializer`, `LitigationRiskLevelSerializer`,
`MeetingModeSerializer`, `MeetingTypeSerializer`, `DirectivePrioritySerializer`, `DirectiveCategorySerializer`

**Business entity serializers (in `legal_serializers.py`):**
`GoverningBodySerializer`, `GoverningBodyMemberSerializer`,
`MeetingSerializer`, `MeetingAttendanceSerializer`,
`MinutesSerializer`, `MeetingDirectiveSerializer`,
`CaseDefendantSerializer`, `CasePlaintiffSerializer`,
`HearingSerializer`, `LitigationDirectiveSerializer`, `TaskLitigationSerializer`,
`FilingDefendantSerializer`, `FilingPlaintiffSerializer`,
`SettlementDefendantSerializer`, `SettlementPlaintiffSerializer`,
`JudgmentDefendantSerializer`, `JudgmentPlaintiffSerializer`,
`AppealDefendantSerializer`, `AppealPlaintiffSerializer`,
`LegalNoticeSerializer`

That is 20 business entity serializers + 7 lookup serializers = 27 total.

---

## 9. Step 7 — RBAC: Permissions

### 9.1 Extend `config/permissions/grc-service.json`

Append the Legal permission codes to the JSON file. Keep the same structure as existing audit codes:

```json
{
  "service": "grc-service",
  "permissions": [
    ...existing audit codes...,

    "grc:legal_governing_body:view",
    "grc:legal_governing_body:manage",

    "grc:legal_meeting:view",
    "grc:legal_meeting:manage",
    "grc:legal_meeting:approve",

    "grc:legal_minutes:view",
    "grc:legal_minutes:manage",
    "grc:legal_minutes:approve",

    "grc:legal_directive:view",
    "grc:legal_directive:manage",

    "grc:legal_case:view",
    "grc:legal_case:manage",
    "grc:legal_case:close",

    "grc:legal_hearing:view",
    "grc:legal_hearing:manage",

    "grc:legal_filing:view",
    "grc:legal_filing:manage",
    "grc:legal_filing:approve",

    "grc:legal_settlement:view",
    "grc:legal_settlement:manage",
    "grc:legal_settlement:approve",

    "grc:legal_judgment:view",
    "grc:legal_judgment:manage",
    "grc:legal_judgment:record",

    "grc:legal_appeal:view",
    "grc:legal_appeal:manage",

    "grc:legal_notice:view",
    "grc:legal_notice:manage"
  ]
}
```

**Full permission code list: 24 codes** across 12 resources.

### 9.2 Extend `apps/api/permissions_jwt.py`

Add one named permission class per code, following the pattern of existing classes:

```python
class CanViewLegalCase(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:legal_case:view')

class CanManageLegalCase(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:legal_case:manage')
```

Create classes for all 24 codes (24 classes total in the Legal block).

### 9.3 Re-publish permission catalog to IAM

After updating the JSON file, re-publish so IAM knows about the new codes:

```bash
python manage.py shell -c "
from apps.core.kafka_permission_publisher import publish_permissions
publish_permissions()
print('Published')
"
```

Or use the management command if one exists — check `apps/core/management/commands/` for a `publish_permissions.py` file.

---

## 10. Step 8 — Views

**Design reference:** `GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md §7`, `Legal_Module_Workflow_Integration.md §9`

### 10.1 New view files to create

```
apps/api/views/legal_governing_body_views.py
apps/api/views/legal_meeting_views.py
apps/api/views/legal_minutes_views.py
apps/api/views/legal_directive_views.py
apps/api/views/legal_case_views.py
apps/api/views/legal_hearing_views.py
apps/api/views/legal_filing_views.py
apps/api/views/legal_settlement_views.py
apps/api/views/legal_judgment_views.py
apps/api/views/legal_notice_views.py
```

10 view files. Appeal views are included in `legal_judgment_views.py`.

### 10.2 Every view file must import

```python
import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    success_response, created_response, updated_response, deleted_response,
    paginated_list_response, error_response, not_found_response,
    validation_error_response, conflict_response, server_error_response,
)
from apps.api.permissions_jwt import (
    CanViewLegalCase, CanManageLegalCase, ...  # import all needed for this file
)
from apps.api.serializers.legal_serializers import ...
from apps.core.models.legal_entities import ...

logger = logging.getLogger(__name__)
```

### 10.3 Standard view structure per entity

Every entity needs these view classes:

| Class name pattern | Methods | Permission check |
|---|---|---|
| `{Entity}ListView` | `GET` (list), `POST` (create) | GET→view, POST→manage |
| `{Entity}DetailView` | `GET`, `PUT`, `PATCH`, `DELETE` (soft) | GET→view, PUT/PATCH→manage, DELETE→manage |

Workflow entities additionally need:

| Class name pattern | Method | Purpose |
|---|---|---|
| `{Entity}SubmitView` | `POST` | Start WO workflow |
| `{Entity}WorkflowStatusView` | `GET` | Current WO plan state |
| `{Entity}WorkflowHistoryView` | `GET` | WO activity log |
| `{Entity}WorkflowActionView` | `POST` | Advance WO stage action |
| `{Entity}CancelWorkflowView` | `POST` | Cancel active WO plan |

### 10.4 View-layer business rules to enforce

These checks go in the view `post()` method, **before calling `serializer.save()`**:

| Entity | Business rule |
|---|---|
| `Meeting` | `GoverningBody` must have `is_active=True` |
| `Minutes` | Parent `Meeting` must be `completed` before minutes can be submitted |
| `MeetingDirective` | Parent `Minutes` must be `approved` |
| `FilingDefendant` | Parent `CaseDefendant` must not be `closed` |
| `FilingPlaintiff` | Parent `CasePlaintiff` must not be `closed` |
| `SettlementDefendant` | Parent `CaseDefendant` must be `active` |
| `JudgmentDefendant` | Parent `CaseDefendant` must be `active` |
| `AppealDefendant` | Must NOT be created manually via API — auto-created by service only |
| `MeetingAgenda` (GAP-02) | After saving, if `submission` FK is set and submission.status = `submitted`, auto-transition to `under_review` |
| `ConflictDeclaration` (GAP-05) | On vote/outcome recording, reject if acting user has a `ConflictDeclaration` for the agenda item |

### 10.5 Auto-generation in view layer

Auto-generate `reference_number` in the `POST` handler for `Meeting`, `CaseDefendant`, `CasePlaintiff`, and `LegalNotice` if not provided by the caller. Use the patterns defined in §4.6. Always check for duplicates before saving.

> **GAP-01 fix applied:** Case reference numbers use `FCC/SUED/YYYY/NNN` (defendant) and  
> `FCC/SUING/YYYY/NNN` (plaintiff) — NOT the earlier `CASE-DEF-YYYY-NNNN` format.

### 10.6 Soft delete

All `DELETE` implementations **never hard-delete**. They set `is_active=False` and save:

> **GAP-14 fix applied:** `CaseDefendant` and `CasePlaintiff` additionally carry `is_archived`  
> (BooleanField) and `archived_at` (DateTimeField, nullable). Archived cases are excluded from all  
> default list queries via `.filter(is_archived=False)`. A manual archive endpoint exists:  
> `POST /legal/cases/defendant/<pk>/archive/` and `POST /legal/cases/plaintiff/<pk>/archive/`.  
> A Celery task (`grc.archive_closed_legal_cases`) runs daily to auto-archive cases closed > N days
> (configured in settings as `LEGAL_CASE_AUTO_ARCHIVE_DAYS`, default 365).

```python
def delete(self, request, pk):
    try:
        instance = get_object_or_404(EntityModel, id=pk, is_active=True)
        # permission check ...
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return deleted_response()
    except Exception as e:
        logger.exception("Delete failed")
        return server_error_response(message="Delete failed", details=str(e) if settings.DEBUG else None)
```

### 10.7 Queryset discipline

- Every `objects.filter(...)` on a business entity must include `.filter(is_active=True)` unless explicitly fetching deactivated records.
- Use `select_related()` for every FK used in the serializer response to avoid N+1 queries.
- For list views with parent filtering (e.g., hearings by case), index on the parent FK — all `legal_` FKs should carry `db_index=True` (confirm this is set in the model definition before deploying).

### 10.8 Additional Views from Gap Fixes (all implemented)

These views were added as part of SRS gap resolution. They are included in the URL routes in §11.1.

**GAP-03 — Matters Arising Auto-Populate:**
`MeetingPopulateMattersArisingView` — `POST /legal/meetings/<pk>/populate-matters-arising/`  
Queries unresolved `MeetingDirective` records for the same governing body and creates `MeetingAgenda` items with `is_matters_arising=True`. Avoids duplicates if already on the current meeting's agenda.

**GAP-04 — Auto-Populate Participants on Meeting Create:**
Logic inside `MeetingListCreateView.post()`. After creating the meeting, bulk-creates `MeetingParticipant` records from all active `GoverningBodyMember` records. Sets `total_member_count` and `rsvp_pending_count`.

**GAP-08 — Hearing Report → Update NextHearingDate:**
Logic inside `HearingReportListCreateView.post()`. If `report.next_hearing_date` is set, propagates it to the parent case (`case_defendant` or `case_plaintiff`). Frontend: always display `next_hearing_date` from the case, not from the individual hearing report.

**GAP-09 — Financial Auto-Creation on Case Registration:**
Logic inside `CaseDefendantListCreateView.post()` and `CasePlaintiffListCreateView.post()`. A `FinancialDefendant`/`FinancialPlaintiff` record is automatically created with `claim_amount` from the case. Frontend: financial records always exist for every registered case.

**GAP-11 — Public Register Views (4 views):**  
File: `apps/api/views/legal_public_register_views.py`
- `PublicDecisionListCreateView` — authenticated CRUD for secretariat
- `PublicDecisionDetailView` — authenticated CRUD
- `PublicDecisionPublishView` — POST to transition status → `published`
- `PublicRegisterListView` — **unauthenticated**, returns only `status='published'` records

**GAP-12 — Dashboard KPI Views:**  
File: `apps/api/views/legal_dashboard_views.py`
- `LegalDashboardDefendantView` — returns aggregated defendant KPIs (see §Appendix D for response shape)
- `LegalDashboardPlaintiffView` — returns aggregated plaintiff KPIs (see §Appendix D for response shape)

**GAP-13 — Activity Log View:**  
Added to `apps/api/views/legal_case_views.py`.
- `LegalActivityLogView` — `GET /legal/activity-log/<entity_type>/<entity_id>/` — paginated list of `LegalAuditLog` records for any entity type/ID combination, ordered by `-created_at`.

**SRS §1.2.1 — Meeting Send Invitations Endpoint (A17 Fix 1):**  
File: `apps/api/views/legal_meeting_views.py` — `MeetingSendInvitationsView`  
URL: `POST /api/v1/grc/legal/meetings/<uuid:pk>/send-invitations/`  
Logic: validates `meeting.status == 'registered'`; transitions to `invitations_sent`; notifies all `MeetingParticipant` records with `invitation_status = 'pending'`.  
Permission: `grc:legal_meeting:manage`.

**SRS §4.13 — Case Report / Timeline Endpoint (A17 Fix 2):**  
File: `apps/api/views/legal_case_views.py` — `CaseReportView`  
URL: `GET /api/v1/grc/legal/cases/<str:side>/<uuid:pk>/report/`  
Logic: aggregates milestone events from `Hearing`, `FilingDefendant/Plaintiff`, `SettlementDefendant/Plaintiff`, `JudgmentDefendant/Plaintiff` (with linked `Appeal`), and `LitigationDirective` related to the case. Returns events sorted chronologically. Helper `_to_iso()` normalises `DateField` and `DateTimeField` to ISO 8601 for unified sorting.  
Permission: `grc:legal_case:view` or `grc:legal_case:manage`.

---

## 11. Step 9 — URL Registration

### 11.1 New URL file

**New file:** `apps/api/urls/legal.py`

```python
from django.urls import path
from apps.api.views.legal_governing_body_views import (...)
from apps.api.views.legal_meeting_views import (...)
# ... remaining imports

urlpatterns = [
    # ── Governing Body ──────────────────────────────────────────────────────
    path("legal/governing-bodies/",        GoverningBodyListView.as_view()),
    path("legal/governing-bodies/<uuid:pk>/", GoverningBodyDetailView.as_view()),
    path("legal/governing-bodies/<uuid:pk>/members/", GoverningBodyMemberListView.as_view()),
    path("legal/governing-body-members/<uuid:pk>/",   GoverningBodyMemberDetailView.as_view()),

    # ── Meetings ─────────────────────────────────────────────────────────────
    path("legal/meetings/",               MeetingListView.as_view()),
    path("legal/meetings/<uuid:pk>/",     MeetingDetailView.as_view()),
    path("legal/meetings/<uuid:pk>/submit/",            MeetingSubmitView.as_view()),
    path("legal/meetings/<uuid:pk>/workflow-status/",   MeetingWorkflowStatusView.as_view()),
    path("legal/meetings/<uuid:pk>/workflow-history/",  MeetingWorkflowHistoryView.as_view()),
    path("legal/meetings/<uuid:pk>/workflow-action/",   MeetingWorkflowActionView.as_view()),
    path("legal/meetings/<uuid:pk>/cancel-workflow/",   MeetingCancelWorkflowView.as_view()),
    path("legal/meetings/<uuid:pk>/attendance/",        MeetingAttendanceListView.as_view()),

    # ── Minutes ──────────────────────────────────────────────────────────────
    path("legal/minutes/",             MinutesListView.as_view()),
    path("legal/minutes/<uuid:pk>/",   MinutesDetailView.as_view()),
    path("legal/minutes/<uuid:pk>/submit/",            MinutesSubmitView.as_view()),
    path("legal/minutes/<uuid:pk>/workflow-status/",   MinutesWorkflowStatusView.as_view()),
    path("legal/minutes/<uuid:pk>/workflow-history/",  MinutesWorkflowHistoryView.as_view()),
    path("legal/minutes/<uuid:pk>/workflow-action/",   MinutesWorkflowActionView.as_view()),
    path("legal/minutes/<uuid:pk>/cancel-workflow/",   MinutesCancelWorkflowView.as_view()),
    path("legal/minutes/<uuid:pk>/directives/",        MeetingDirectiveListView.as_view()),

    # ── Meeting Directives ────────────────────────────────────────────────────
    path("legal/directives/overdue/",          MeetingDirectiveOverdueListView.as_view()),
    path("legal/directives/",                  MeetingDirectiveListView.as_view()),
    path("legal/directives/<uuid:pk>/",        MeetingDirectiveDetailView.as_view()),

    # ── Cases — Defendant ────────────────────────────────────────────────────
    path("legal/cases/defendant/",             CaseDefendantListView.as_view()),
    path("legal/cases/defendant/<uuid:pk>/",   CaseDefendantDetailView.as_view()),
    path("legal/cases/defendant/<uuid:pk>/submit/",            CaseDefendantSubmitView.as_view()),
    path("legal/cases/defendant/<uuid:pk>/workflow-status/",   CaseDefendantWorkflowStatusView.as_view()),
    path("legal/cases/defendant/<uuid:pk>/workflow-history/",  CaseDefendantWorkflowHistoryView.as_view()),
    path("legal/cases/defendant/<uuid:pk>/workflow-action/",   CaseDefendantWorkflowActionView.as_view()),
    path("legal/cases/defendant/<uuid:pk>/cancel-workflow/",   CaseDefendantCancelWorkflowView.as_view()),

    # ── Cases — Plaintiff ────────────────────────────────────────────────────
    path("legal/cases/plaintiff/",             CasePlaintiffListView.as_view()),
    path("legal/cases/plaintiff/<uuid:pk>/",   CasePlaintiffDetailView.as_view()),
    path("legal/cases/plaintiff/<uuid:pk>/submit/",            CasePlaintiffSubmitView.as_view()),
    path("legal/cases/plaintiff/<uuid:pk>/workflow-status/",   CasePlaintiffWorkflowStatusView.as_view()),
    path("legal/cases/plaintiff/<uuid:pk>/workflow-history/",  CasePlaintiffWorkflowHistoryView.as_view()),
    path("legal/cases/plaintiff/<uuid:pk>/workflow-action/",   CasePlaintiffWorkflowActionView.as_view()),
    path("legal/cases/plaintiff/<uuid:pk>/cancel-workflow/",   CasePlaintiffCancelWorkflowView.as_view()),

    # ── Hearings ─────────────────────────────────────────────────────────────
    path("legal/hearings/",            HearingListView.as_view()),
    path("legal/hearings/<uuid:pk>/",  HearingDetailView.as_view()),

    # ── Litigation Directives ─────────────────────────────────────────────────
    path("legal/litigation-directives/overdue/",        LitigationDirectiveOverdueListView.as_view()),
    path("legal/litigation-directives/",                LitigationDirectiveListView.as_view()),
    path("legal/litigation-directives/<uuid:pk>/",      LitigationDirectiveDetailView.as_view()),

    # ── Tasks ────────────────────────────────────────────────────────────────
    path("legal/tasks/overdue/",          TaskLitigationOverdueListView.as_view()),
    path("legal/tasks/",                  TaskLitigationListView.as_view()),
    path("legal/tasks/<uuid:pk>/",        TaskLitigationDetailView.as_view()),

    # ── Filings ──────────────────────────────────────────────────────────────
    path("legal/filings/defendant/",           FilingDefendantListView.as_view()),
    path("legal/filings/defendant/<uuid:pk>/", FilingDefendantDetailView.as_view()),
    path("legal/filings/defendant/<uuid:pk>/submit/",            FilingDefendantSubmitView.as_view()),
    path("legal/filings/defendant/<uuid:pk>/workflow-status/",   FilingDefendantWorkflowStatusView.as_view()),
    path("legal/filings/defendant/<uuid:pk>/workflow-history/",  FilingDefendantWorkflowHistoryView.as_view()),
    path("legal/filings/defendant/<uuid:pk>/workflow-action/",   FilingDefendantWorkflowActionView.as_view()),
    path("legal/filings/defendant/<uuid:pk>/cancel-workflow/",   FilingDefendantCancelWorkflowView.as_view()),

    path("legal/filings/plaintiff/",           FilingPlaintiffListView.as_view()),
    path("legal/filings/plaintiff/<uuid:pk>/", FilingPlaintiffDetailView.as_view()),
    path("legal/filings/plaintiff/<uuid:pk>/submit/",            FilingPlaintiffSubmitView.as_view()),
    path("legal/filings/plaintiff/<uuid:pk>/workflow-status/",   FilingPlaintiffWorkflowStatusView.as_view()),
    path("legal/filings/plaintiff/<uuid:pk>/workflow-history/",  FilingPlaintiffWorkflowHistoryView.as_view()),
    path("legal/filings/plaintiff/<uuid:pk>/workflow-action/",   FilingPlaintiffWorkflowActionView.as_view()),
    path("legal/filings/plaintiff/<uuid:pk>/cancel-workflow/",   FilingPlaintiffCancelWorkflowView.as_view()),

    # ── Settlements ──────────────────────────────────────────────────────────
    path("legal/settlements/defendant/",           SettlementDefendantListView.as_view()),
    path("legal/settlements/defendant/<uuid:pk>/", SettlementDefendantDetailView.as_view()),
    path("legal/settlements/defendant/<uuid:pk>/submit/",            SettlementDefendantSubmitView.as_view()),
    path("legal/settlements/defendant/<uuid:pk>/workflow-status/",   SettlementDefendantWorkflowStatusView.as_view()),
    path("legal/settlements/defendant/<uuid:pk>/workflow-history/",  SettlementDefendantWorkflowHistoryView.as_view()),
    path("legal/settlements/defendant/<uuid:pk>/workflow-action/",   SettlementDefendantWorkflowActionView.as_view()),
    path("legal/settlements/defendant/<uuid:pk>/cancel-workflow/",   SettlementDefendantCancelWorkflowView.as_view()),

    path("legal/settlements/plaintiff/",           SettlementPlaintiffListView.as_view()),
    path("legal/settlements/plaintiff/<uuid:pk>/", SettlementPlaintiffDetailView.as_view()),
    path("legal/settlements/plaintiff/<uuid:pk>/submit/",            SettlementPlaintiffSubmitView.as_view()),
    path("legal/settlements/plaintiff/<uuid:pk>/workflow-status/",   SettlementPlaintiffWorkflowStatusView.as_view()),
    path("legal/settlements/plaintiff/<uuid:pk>/workflow-history/",  SettlementPlaintiffWorkflowHistoryView.as_view()),
    path("legal/settlements/plaintiff/<uuid:pk>/workflow-action/",   SettlementPlaintiffWorkflowActionView.as_view()),
    path("legal/settlements/plaintiff/<uuid:pk>/cancel-workflow/",   SettlementPlaintiffCancelWorkflowView.as_view()),

    # ── Judgments ────────────────────────────────────────────────────────────
    path("legal/judgments/defendant/",           JudgmentDefendantListView.as_view()),
    path("legal/judgments/defendant/<uuid:pk>/", JudgmentDefendantDetailView.as_view()),
    path("legal/judgments/defendant/<uuid:pk>/submit/",            JudgmentDefendantSubmitView.as_view()),
    path("legal/judgments/defendant/<uuid:pk>/workflow-status/",   JudgmentDefendantWorkflowStatusView.as_view()),
    path("legal/judgments/defendant/<uuid:pk>/workflow-history/",  JudgmentDefendantWorkflowHistoryView.as_view()),
    path("legal/judgments/defendant/<uuid:pk>/workflow-action/",   JudgmentDefendantWorkflowActionView.as_view()),
    path("legal/judgments/defendant/<uuid:pk>/cancel-workflow/",   JudgmentDefendantCancelWorkflowView.as_view()),

    path("legal/judgments/plaintiff/",           JudgmentPlaintiffListView.as_view()),
    path("legal/judgments/plaintiff/<uuid:pk>/", JudgmentPlaintiffDetailView.as_view()),
    path("legal/judgments/plaintiff/<uuid:pk>/submit/",            JudgmentPlaintiffSubmitView.as_view()),
    path("legal/judgments/plaintiff/<uuid:pk>/workflow-status/",   JudgmentPlaintiffWorkflowStatusView.as_view()),
    path("legal/judgments/plaintiff/<uuid:pk>/workflow-history/",  JudgmentPlaintiffWorkflowHistoryView.as_view()),
    path("legal/judgments/plaintiff/<uuid:pk>/workflow-action/",   JudgmentPlaintiffWorkflowActionView.as_view()),
    path("legal/judgments/plaintiff/<uuid:pk>/cancel-workflow/",   JudgmentPlaintiffCancelWorkflowView.as_view()),

    # ── Appeals ──────────────────────────────────────────────────────────────
    path("legal/appeals/defendant/",           AppealDefendantListView.as_view()),
    path("legal/appeals/defendant/<uuid:pk>/", AppealDefendantDetailView.as_view()),
    path("legal/appeals/plaintiff/",           AppealPlaintiffListView.as_view()),
    path("legal/appeals/plaintiff/<uuid:pk>/", AppealPlaintiffDetailView.as_view()),

    # ── Legal Notices ─────────────────────────────────────────────────────────
    path("legal/notices/",            LegalNoticeListView.as_view()),
    path("legal/notices/<uuid:pk>/",  LegalNoticeDetailView.as_view()),

    # ── Legal Lookups ─────────────────────────────────────────────────────────
    path("legal/lookups/court-levels/",          CourtLevelListView.as_view()),
    path("legal/lookups/urgency-levels/",         LitigationUrgencyLevelListView.as_view()),
    path("legal/lookups/risk-levels/",            LitigationRiskLevelListView.as_view()),
    path("legal/lookups/meeting-modes/",          MeetingModeListView.as_view()),
    path("legal/lookups/meeting-types/",          MeetingTypeListView.as_view()),
    path("legal/lookups/directive-priorities/",   DirectivePriorityListView.as_view()),
    path("legal/lookups/directive-categories/",   DirectiveCategoryListView.as_view()),

    # ── Gap Fix Routes ────────────────────────────────────────────────────────
    # GAP-03: Matters arising auto-populate
    path("legal/meetings/<uuid:pk>/populate-matters-arising/",
         MeetingPopulateMattersArisingView.as_view()),

    # GAP-11: Public Register (unauthenticated endpoint last)
    path("legal/public-decisions/",                PublicDecisionListCreateView.as_view()),
    path("legal/public-decisions/<uuid:pk>/",      PublicDecisionDetailView.as_view()),
    path("legal/public-decisions/<uuid:pk>/publish/", PublicDecisionPublishView.as_view()),
    path("legal/public-register/",                 PublicRegisterListView.as_view()),  # no auth

    # GAP-12: Dashboard KPIs
    path("legal/dashboard/defendant/",  LegalDashboardDefendantView.as_view()),
    path("legal/dashboard/plaintiff/",  LegalDashboardPlaintiffView.as_view()),

    # GAP-13: Activity Log
    path("legal/activity-log/<str:entity_type>/<uuid:entity_id>/",
         LegalActivityLogView.as_view()),

    # GAP-14: Manual archive endpoints
    path("legal/cases/defendant/<uuid:pk>/archive/",  CaseDefendantArchiveView.as_view()),
    path("legal/cases/plaintiff/<uuid:pk>/archive/",  CasePlaintiffArchiveView.as_view()),
]
```

> **Ordering rule (critical):** Static segment routes (`overdue/`) must be declared **before** `<uuid:pk>/` patterns for the same resource prefix. Check `GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md §13.2` for the exact ordering rule.

### 11.2 Register in `apps/api/urls.py`

Open `apps/api/urls.py` and add the legal include alongside the existing `audit` include:

```python
from .urls.legal import urlpatterns as legal_urlpatterns

urlpatterns = [
    *existing_patterns,
    path("", include(legal_urlpatterns)),   # or use path("v1/grc/", include(...))
]
```

Verify the exact include pattern used for the audit URLs and mirror it for legal.

---

## 12. Step 10 — Celery Background Tasks

**New files to create:**

```
apps/core/tasks/legal_directive_deadlines.py
apps/core/tasks/legal_case_deadlines.py
```

**Design reference:** `Legal_Module_Data_Models_Part3.md §16`; `GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md §17`

### 12.1 `legal_directive_deadlines.py`

```python
@shared_task(name='grc.check_legal_directive_deadlines')
def check_legal_directive_deadlines():
    """
    Daily task. Marks MeetingDirective and LitigationDirective records
    as overdue when due_date < today and status not in ('completed',).
    Sends overdue notification to responsible_user_id via NotificationPublisher.
    """
```

Logic:
1. Filter `MeetingDirective.objects.filter(is_active=True, due_date__lt=today, is_overdue=False).exclude(status='completed')`
2. Bulk-update `is_overdue=True`, `status='overdue'`
3. For each: resolve `responsible_user_id` via `IAMClient.get_user_profile()`, send notification via `publisher.send_notification(template_code='grc.legal.directive.overdue', ...)`
4. Repeat for `LitigationDirective`

### 12.2 `legal_case_deadlines.py`

```python
@shared_task(name='grc.check_legal_task_deadlines')
def check_legal_task_deadlines():
    """
    Daily task. Sends 7-day, 2-day, and 1-day reminder notifications
    for TaskLitigation records approaching due_date.
    Marks overdue when due_date < today and status != 'completed'.
    """
```

Logic:
1. For each reminder window (7, 2, 1 days): filter `TaskLitigation` where `due_date = today + N days` and status not `completed`; send reminder
2. Mark overdue: `due_date__lt=today`, status not `completed` → `status='overdue'`, `is_overdue=True`

### 12.3 Register in Celery beat schedule

Open `config/settings.py` and extend `CELERY_BEAT_SCHEDULE`:

```python
CELERY_BEAT_SCHEDULE = {
    ...existing entries...,
    'grc.check_legal_directive_deadlines': {
        'task':     'grc.check_legal_directive_deadlines',
        'schedule': crontab(hour=7, minute=0),
    },
    'grc.check_legal_task_deadlines': {
        'task':     'grc.check_legal_task_deadlines',
        'schedule': crontab(hour=7, minute=15),
    },
    # GAP-14: Auto-archive closed cases
    'grc.archive_closed_legal_cases': {
        'task':     'grc.archive_closed_legal_cases',
        'schedule': crontab(hour=2, minute=0),   # runs at 2am daily
    },
}
```

---

## 13. Step 11 — Kafka Events

**Design reference:** `Legal_Module_Workflow_Integration.md §11`; `GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md §15`

### 13.1 Event dataclasses

Create `apps/core/events/legal_events.py`:

```python
from dataclasses import dataclass, field
from .base import GRCDomainEvent  # same base as audit events

@dataclass
class LegalCaseCreatedEvent(GRCDomainEvent):
    case_id:       str = field(default='')
    case_type:     str = field(default='')  # 'defendant' | 'plaintiff'
    reference_number: str = field(default='')
    created_by:    str = field(default='')

    def __post_init__(self):
        self.event_type  = 'grc.legal.case.created'
        self.aggregate_id = self.case_id

    def _get_event_data(self):
        return {'case_id': self.case_id, 'case_type': self.case_type, ...}
```

Minimum event types to implement:

| Event type | Trigger |
|---|---|
| `grc.legal.case.created` | New `CaseDefendant` or `CasePlaintiff` created |
| `grc.legal.case.closed` | Case status transitions to `closed` |
| `grc.legal.judgment.recorded` | `JudgmentDefendant` or `JudgmentPlaintiff` created |
| `grc.legal.meeting.completed` | `Meeting` transitions to `completed` |
| `grc.legal.minutes.approved` | `Minutes` workflow completes |
| `grc.legal.directive.overdue` | Celery task marks directive overdue |

### 13.2 Event type constants

Add to `shared/constants/event_types.py`:

```python
LEGAL_CASE_EVENTS = {
    'CREATED': 'grc.legal.case.created',
    'CLOSED':  'grc.legal.case.closed',
}
LEGAL_JUDGMENT_EVENTS = {
    'RECORDED': 'grc.legal.judgment.recorded',
}
# ... remaining groups
```

### 13.3 Publishing pattern

Publish from the view layer after a successful `.save()`, same pattern as audit:

```python
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import LEGAL_CASE_EVENTS

messaging_service.publish_event(
    LEGAL_CASE_EVENTS['CREATED'],
    {'case_id': str(case.id), 'created_by': request.user_id}
)
```

### 13.4 Consuming Corporate Service events (GoverningBody sync)

Extend `apps/core/management/commands/consume_grc_events.py` (or the Kafka consumer setup) to handle Corporate Service events for member roster updates. When Corporate Service publishes a member change event:

1. Look up `GoverningBody` by `external_id`
2. Create or update `GoverningBodyMember` records
3. Log the sync operation (consider a `LegalSyncLog` model if high audit fidelity is needed)

---

## 14. Step 12 — Seed Data & Management Commands

### 14.1 Extend `seed_lookup_data` management command

**File to edit:** `apps/core/management/commands/seed_lookup_data.py`

Add a `seed_legal_lookups()` function (or equivalent block) that creates the initial lookup values for all 7 legal lookup tables. Seed data is fully specified in `Legal_Module_Lookup_Tables.md §8`.

Sample:

```python
def seed_legal_lookups():
    CourtLevel.objects.get_or_create(code='tribunal',         defaults={'name': 'Tribunal',          'sort_order': 1})
    CourtLevel.objects.get_or_create(code='resident_magistrate', defaults={'name': 'Resident Magistrate Court', 'sort_order': 2})
    CourtLevel.objects.get_or_create(code='high_court',       defaults={'name': 'High Court',        'sort_order': 3})
    CourtLevel.objects.get_or_create(code='court_of_appeal',  defaults={'name': 'Court of Appeal',   'sort_order': 4})
    CourtLevel.objects.get_or_create(code='supreme_court',    defaults={'name': 'Supreme Court',     'sort_order': 5})

    LitigationUrgencyLevel.objects.get_or_create(code='low',      defaults={'name': 'Low',      'color_code': '#28A745', 'sort_order': 1})
    LitigationUrgencyLevel.objects.get_or_create(code='medium',   defaults={'name': 'Medium',   'color_code': '#FFC107', 'sort_order': 2})
    LitigationUrgencyLevel.objects.get_or_create(code='high',     defaults={'name': 'High',     'color_code': '#FD7E14', 'sort_order': 3})
    LitigationUrgencyLevel.objects.get_or_create(code='critical', defaults={'name': 'Critical', 'color_code': '#DC3545', 'sort_order': 4})

    # ... MeetingMode, MeetingType, DirectivePriority, DirectiveCategory
    # Full values in Legal_Module_Lookup_Tables.md §8
```

Call `seed_legal_lookups()` from the command's `handle()` method.

### 14.2 Extend `register_workflow_templates` management command

**File to edit:** `apps/core/management/commands/register_workflow_templates.py`

The command reads `workflows.yaml` and registers/updates templates in the Work Orchestration Service. Since the 6 new Legal templates were added to `workflows.yaml` in Step 4, this command only needs to be re-run — no code change required.

```bash
# Register all templates (including the 6 new Legal ones)
python manage.py register_workflow_templates
```

Verify in the WO admin console that all 6 `grc.legal_*` templates appear.

### 14.3 Run seed commands

```bash
# Seed lookup data (lookup tables must exist — run after Step 3 migration)
python manage.py seed_lookup_data

# Register workflow templates (WO service must be running)
python manage.py register_workflow_templates
```

---

## 15. Step 13 — Testing

**Test directory:** `tests/`

### 15.1 Test file structure

Create one test file per logical group:

```
tests/legal/test_lookup_models.py
tests/legal/test_governing_body.py
tests/legal/test_meetings.py
tests/legal/test_cases.py
tests/legal/test_workflow_integration.py
tests/legal/test_permissions.py
tests/legal/test_celery_tasks.py
```

### 15.2 Minimum test coverage per entity

Each entity test file must cover:

| Scenario | What to test |
|---|---|
| **Permission denied** | Unauthenticated request → 401; wrong permission code → 403 |
| **Happy path create** | Valid POST → 201, correct fields in response |
| **Validation error** | Missing required field → 400 with `errors` key |
| **Business rule violation** | e.g. creating a Filing on a closed Case → 400 with specific error code |
| **Soft delete** | DELETE → 200, `is_active=False`, subsequent GET → 404 |
| **List filtering** | Filter by status, filter by parent FK ID |
| **Ordering** | `?ordering=-created_at`, `?ordering=reference_number` |

### 15.3 Workflow integration tests

In `test_workflow_integration.py`:

```python
# Mock OrchestrationClient so tests run without WO running
@patch('apps.infrastructure.external.orchestration_client.OrchestrationClient.start_workflow')
def test_meeting_submit_starts_workflow(self, mock_start):
    mock_start.return_value = MockPlanResult(plan_id=uuid4(), current_stage_name='agenda_review')
    # POST to /legal/meetings/<pk>/submit/
    # Assert: meeting.workflow_plan_id is set, status updated correctly
```

### 15.4 Celery task tests

```python
# Test with frozen time to control due_date comparisons
from freezegun import freeze_time

@freeze_time("2025-06-01")
def test_overdue_meeting_directive_is_marked(self):
    directive = MeetingDirective.objects.create(due_date=date(2025, 5, 31), status='in_progress', ...)
    check_legal_directive_deadlines()
    directive.refresh_from_db()
    assert directive.is_overdue is True
    assert directive.status == 'overdue'
```

### 15.5 Sample fixtures

Create `tests/legal/fixtures/legal_lookups.json` with the seed data for use in test setup. Run:

```bash
python manage.py dumpdata core.CourtLevel core.LitigationUrgencyLevel ... --indent 2 > tests/legal/fixtures/legal_lookups.json
```

---

## 16. Step 14 — Deployment Checklist

Run these steps in order when deploying the Legal module to any environment.

### Pre-deployment

- [ ] All Legal model files committed and reviewed: `legal_entities.py`, updated `lookups.py`, updated `__init__.py`, updated `workflow_entity_paths.py`
- [ ] Migration file committed: `apps/core/migrations/XXXX_legal_module_initial.py`
- [ ] `workflows.yaml` committed with 6 new Legal templates
- [ ] `config/permissions/grc-service.json` committed with 24 new Legal permission codes
- [ ] All 6 service files committed
- [ ] All serializers committed: updated `lookup_serializers.py`, new `legal_serializers.py`
- [ ] All 10 view files committed
- [ ] `apps/api/urls/legal.py` committed and wired into `urls.py`
- [ ] 2 Celery task files committed and registered in `settings.py`
- [ ] Event files committed: `legal_events.py`, updated `event_types.py`

### Deployment steps

```bash
# 1. Run migrations
python manage.py migrate

# 2. Seed lookup data
python manage.py seed_lookup_data

# 3. Register Legal workflow templates with WO
python manage.py register_workflow_templates

# 4. Publish updated permission catalog to IAM
python manage.py shell -c "from apps.core.kafka_permission_publisher import publish_permissions; publish_permissions()"

# 5. Restart Celery worker and beat to pick up new tasks
# (Handled by Docker restart or Kubernetes rollout)

# 6. Smoke test
curl -H "Authorization: Bearer <jwt>" http://localhost:8003/api/v1/grc/legal/lookups/court-levels/
# Expected: 200 with list of court level records
```

### Post-deployment verification

```bash
# Verify all 35 legal tables exist
python manage.py dbshell -c "\dt legal_*"

# Verify 6 workflow templates registered in WO
# (check WO admin console or API)

# Verify 24 permission codes published to IAM
# (check IAM admin console or grc:legal_case:view in token)

# Run smoke tests on key endpoints
python manage.py test tests/legal/ --verbosity=2
```

### Rollback procedure

If a migration failure occurs after partial apply:

```bash
# Identify the migration before legal_module_initial
python manage.py showmigrations core | tail -20

# Roll back
python manage.py migrate core <previous_migration_name>

# The legal_ tables will be dropped. No other tables are affected.
# Fix the migration file, then re-apply.
```

---

## Appendix A — Complete File Manifest

### New files to create

```
apps/core/models/legal_entities.py
apps/core/migrations/XXXX_legal_module_initial.py       ← generated, do not edit manually
apps/core/services/legal_meeting_service.py
apps/core/services/legal_minutes_service.py
apps/core/services/legal_case_service.py
apps/core/services/legal_filing_service.py
apps/core/services/legal_settlement_service.py
apps/core/services/legal_judgment_service.py
apps/core/tasks/legal_directive_deadlines.py
apps/core/tasks/legal_case_deadlines.py
apps/core/events/legal_events.py
apps/api/serializers/legal_serializers.py
apps/api/views/legal_governing_body_views.py
apps/api/views/legal_meeting_views.py
apps/api/views/legal_minutes_views.py
apps/api/views/legal_directive_views.py
apps/api/views/legal_case_views.py
apps/api/views/legal_hearing_views.py
apps/api/views/legal_filing_views.py
apps/api/views/legal_settlement_views.py
apps/api/views/legal_judgment_views.py
apps/api/views/legal_notice_views.py
apps/api/urls/legal.py
tests/legal/__init__.py
tests/legal/test_lookup_models.py
tests/legal/test_governing_body.py
tests/legal/test_meetings.py
tests/legal/test_cases.py
tests/legal/test_workflow_integration.py
tests/legal/test_permissions.py
tests/legal/test_celery_tasks.py
tests/legal/fixtures/legal_lookups.json
```

### Files to modify (append only — no changes to existing code)

```
apps/core/models/lookups.py              ← append 7 lookup models
apps/core/models/__init__.py             ← append 28 entity + 7 lookup imports
apps/core/workflow_entity_paths.py       ← append 10 entity path entries
apps/core/workflows/workflows.yaml       ← append 6 YAML workflow templates
apps/core/management/commands/seed_lookup_data.py     ← append legal seed block
apps/api/serializers/lookup_serializers.py            ← append 7 lookup serializers
apps/api/permissions_jwt.py             ← append 24 permission classes
apps/api/urls/__init__.py               ← append legal URL include
config/permissions/grc-service.json    ← append 24 permission codes
config/settings.py                      ← append 2 Celery beat entries
shared/constants/event_types.py        ← append legal event type constants
```

Total: **31 new files** + **11 modified files**

---

## Appendix B — DB Table Registry

| # | Model | `db_table` | `WorkflowMixin` |
|---|---|---|:---:|
| 1 | `CourtLevel` | `legal_court_level` | — |
| 2 | `LitigationUrgencyLevel` | `legal_litigation_urgency_level` | — |
| 3 | `LitigationRiskLevel` | `legal_litigation_risk_level` | — |
| 4 | `MeetingMode` | `legal_meeting_mode` | — |
| 5 | `MeetingType` | `legal_meeting_type` | — |
| 6 | `DirectivePriority` | `legal_directive_priority` | — |
| 7 | `DirectiveCategory` | `legal_directive_category` | — |
| 8 | `GoverningBody` | `legal_governing_body` | — |
| 9 | `GoverningBodyMember` | `legal_governing_body_member` | — |
| 10 | `Meeting` | `legal_meeting` | ✓ |
| 11 | `MeetingAttendance` | `legal_meeting_attendance` | — |
| 12 | `Minutes` | `legal_minutes` | ✓ |
| 13 | `MeetingDirective` | `legal_meeting_directive` | — |
| 14 | `CaseDefendant` | `legal_case_defendant` | ✓ |
| 15 | `CasePlaintiff` | `legal_case_plaintiff` | ✓ |
| 16 | `Hearing` | `legal_hearing` | — |
| 17 | `LitigationDirective` | `legal_litigation_directive` | — |
| 18 | `TaskLitigation` | `legal_task_litigation` | — |
| 19 | `FilingDefendant` | `legal_filing_defendant` | ✓ |
| 20 | `FilingPlaintiff` | `legal_filing_plaintiff` | ✓ |
| 21 | `SettlementDefendant` | `legal_settlement_defendant` | ✓ |
| 22 | `SettlementPlaintiff` | `legal_settlement_plaintiff` | ✓ |
| 23 | `JudgmentDefendant` | `legal_judgment_defendant` | ✓ |
| 24 | `JudgmentPlaintiff` | `legal_judgment_plaintiff` | ✓ |
| 25 | `AppealDefendant` | `legal_appeal_defendant` | — |
| 26 | `AppealPlaintiff` | `legal_appeal_plaintiff` | — |
| 27 | `LegalNotice` | `legal_notice` | — |

Total: **27 tables** (7 lookup + 20 business entities).

> **Note:** `MeetingAttendance` and `GoverningBodyMember` were added after the Part3 count of 28, bringing entity count to 20. Adjust if `Legal_Module_Data_Models_Part3.md §2` lists a different total — that document is authoritative for the final count.

---

## 17. Appendix C — Implementation Completion Notes
## Appendix C — Implementation Completion Notes

> **Status: ALL STEPS COMPLETE — ALL 14 SRS GAPS FIXED**
> **Backend completed:** March 2026  
> **Branch:** `development`

### Step Completion Summary

| Step | Description | Status |
|---|---|:---:|
| Step 1 | Lookup Tables | ✅ Done |
| Step 2 | Business Entity Models | ✅ Done |
| Step 3 | Migrations | ✅ Done |
| Step 4 | Workflow YAML Templates (incl. GAP-06 filing extension) | ✅ Done |
| Step 5 | Service Layer (incl. GAP-07 judgment→appeal) | ✅ Done |
| Step 6 | Serializers (incl. GAP-11, GAP-12, GAP-13 serializers) | ✅ Done |
| Step 7 | RBAC: Permissions | ✅ Done |
| Step 8 | Views (incl. gap-required views) | ✅ Done |
| Step 9 | URL Registration (incl. all gap routes) | ✅ Done |
| Step 10 | Celery Background Tasks (incl. GAP-14 archive task) | ✅ Done |
| Step 11 | Kafka Events | ✅ Done |
| Step 12 | Seed Data & Management Commands | ✅ Done |
| Step 13 | Testing (Automated) | ✅ Done — 208 tests, all passing |
| Step 14 | Deployment Checklist | ✅ Documented — run at deploy time |
| GAP-01 | Case reference number format | ✅ Done |
| GAP-02 | Submission → under_review on agenda add | ✅ Done |
| GAP-03 | Matters Arising auto-populate | ✅ Done |
| GAP-04 | Auto-populate participants from Members | ✅ Done |
| GAP-05 | Conflict of Interest vote exclusion | ✅ Done |
| GAP-06 | Filing workflow — extend to 6 stages | ✅ Done |
| GAP-07 | Judgment → Appeal auto-creation | ✅ Done |
| GAP-08 | HearingReport → update NextHearingDate | ✅ Done |
| GAP-09 | Financial auto-creation on case registration | ✅ Done |
| GAP-10 | Digital Signature Engine | ✅ Done |
| GAP-11 | Public Register views & URLs | ✅ Done |
| GAP-12 | Dashboard KPI views | ✅ Done |
| GAP-13 | Activity Log API endpoint | ✅ Done |
| GAP-14 | Archiving logic | ✅ Done |
| A17-Fix-1 | Meeting Send Invitations endpoint (SRS §1.2.1) | ✅ Done |
| A17-Fix-2 | Case Report / Timeline endpoint (SRS §4.13) | ✅ Done |

### Test Results Reference

**Test command:**

```bash
docker compose exec -T grc-service python -m pytest tests/legal/ -v --tb=short
```

**Last run result:**

```
208 passed, 2 warnings in 8.32s
```

**Test file breakdown:**

| Test File | Tests | Description |
|---|---|---|
| `tests/legal/test_models.py` | 46 | Model creation, field validation, XOR constraints, soft delete |
| `tests/legal/test_services.py` | 38 | Workflow submit/advance/cancel, Kafka event publishing, all 6 service classes |
| `tests/legal/test_api_governance.py` | ~20 | CommitteeType, GoverningBody, Member, Submission CRUD |
| `tests/legal/test_api_meetings.py` | ~25 | Meeting CRUD, Agenda, Participant, workflow actions |
| `tests/legal/test_api_cases.py` | ~25 | CaseDefendant, CasePlaintiff CRUD, workflow, Hearing |
| `tests/legal/test_api_litigation.py` | ~33 | Filing, Settlement, Judgment, Appeal (D/P), Directives, Tasks, Notices |
| `tests/legal/test_permissions.py` | 11 | Permission enforcement: 401/403 for unauthenticated/unauthorized |
| `tests/legal/test_celery_tasks.py` | 9 | Directive deadline checks, case deadline checks with frozen time |
| `tests/legal/conftest.py` | — | ~530 lines: fixtures for all legal entities, mock users, permission bypass |

### Gap Fix Integration Summary

All 14 SRS gaps have been fixed and their effects are reflected throughout this plan. Summary:

| ID | Title | Status | Integrated Into |
|---|---|:---:|---|
| GAP-01 | Case reference number format | ✅ Done | Step 8 §10.5 |
| GAP-02 | Submission → UNDER_REVIEW on agenda add | ✅ Done | Step 8 §10.4 |
| GAP-03 | Matters Arising auto-populate | ✅ Done | Step 8 §10.8, Step 9 |
| GAP-04 | Auto-populate participants from Members | ✅ Done | Step 8 §10.8 |
| GAP-05 | Conflict of Interest vote exclusion | ✅ Done | Step 8 §10.4 |
| GAP-06 | Filing workflow — extend to 6 stages | ✅ Done | Step 4 |
| GAP-07 | Judgment → Appeal auto-creation | ✅ Done | Step 5 |
| GAP-08 | HearingReport → update NextHearingDate | ✅ Done | Step 8 §10.8 |
| GAP-09 | Financial auto-creation on case registration | ✅ Done | Step 8 §10.8 |
| GAP-10 | Digital Signature Engine | ✅ Done | Shared infra utility |
| GAP-11 | Public Register views & URLs | ✅ Done | Step 8 §10.8, Step 9 |
| GAP-12 | Dashboard KPI views | ✅ Done | Step 8 §10.8, Step 9 |
| GAP-13 | Activity Log API endpoint | ✅ Done | Step 8 §10.8, Step 9 |
| GAP-14 | Archiving logic | ✅ Done | Step 8 §10.6, Step 10 §12.3 |
| A17-Fix-1 | Meeting Send Invitations endpoint | ✅ Done | §10.8 GAP notes, Appendix D.3 |
| A17-Fix-2 | Case Report / Timeline endpoint | ✅ Done | §10.8 GAP notes, Appendix D.6 |

Full gap descriptions, implementation notes, and completion checklists are in **Appendix E**.

### What's Next

Backend is **complete**. All 14 SRS gaps have been fixed, and 2 additional A.17 verification fixes have been applied. The next phase is:

- **Frontend Implementation** — Build the Legal module UI in the `frontend/` workspace (Vite + React/TypeScript).
- Use **Appendix D** (Complete API Reference for Frontend) as the authoritative list of available endpoints, their permissions, and response shapes.
- All backend API endpoints are available at `/api/v1/grc/legal/`.

---

## Appendix D — Complete API Reference for Frontend

> Base URL: `GATEWAY_URL/api/v1/grc/`  
> Auth: Bearer JWT in `Authorization` header (all endpoints except Public Register).  
> All dates: ISO 8601. All IDs: UUID v4.

### D.1 Lookup Endpoints (read-only, auth required)

All lookup endpoints: `GET` only, no pagination, returns `{ results: [...] }`.

| Endpoint | Permission | Response fields |
|---|---|---|
| `GET legal/lookups/court-levels/` | `grc:legal_case:view` | `id, code, name, description, sort_order, is_active` |
| `GET legal/lookups/urgency-levels/` | `grc:legal_case:view` | `id, code, name, description, color_code, sort_order, is_active` |
| `GET legal/lookups/risk-levels/` | `grc:legal_case:view` | `id, code, name, description, color_code, sort_order, is_active` |
| `GET legal/lookups/meeting-modes/` | `grc:legal_meeting:view` | `id, code, name, sort_order, is_active` |
| `GET legal/lookups/meeting-types/` | `grc:legal_meeting:view` | `id, code, name, description, sort_order, is_active` |
| `GET legal/lookups/directive-priorities/` | `grc:legal_directive:view` | `id, code, name, color_code, sort_order, is_active` |
| `GET legal/lookups/directive-categories/` | `grc:legal_directive:view` | `id, code, name, description, sort_order, is_active` |

**Seed values available — court levels:** `tribunal`, `resident_magistrate`, `high_court`, `court_of_appeal`, `supreme_court`  
**Urgency/Risk levels:** `low`, `medium`, `high`, `critical`  
**Meeting modes:** `in_person`, `virtual`, `hybrid`  
**Meeting types:** `ordinary`, `extraordinary`, `emergency`, `annual_general`

---

### D.2 Governing Body Endpoints

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/governing-bodies/` | `grc:legal_governing_body:view` | Paginated list |
| `POST` | `legal/governing-bodies/` | `grc:legal_governing_body:manage` | |
| `GET` | `legal/governing-bodies/<id>/` | `grc:legal_governing_body:view` | |
| `PATCH` | `legal/governing-bodies/<id>/` | `grc:legal_governing_body:manage` | |
| `DELETE` | `legal/governing-bodies/<id>/` | `grc:legal_governing_body:manage` | Soft delete |
| `GET` | `legal/governing-bodies/<id>/members/` | `grc:legal_governing_body:view` | Members for one body |
| `POST` | `legal/governing-bodies/<id>/members/` | `grc:legal_governing_body:manage` | |
| `PATCH` | `legal/governing-body-members/<id>/` | `grc:legal_governing_body:manage` | |
| `DELETE` | `legal/governing-body-members/<id>/` | `grc:legal_governing_body:manage` | Soft delete |

**Key fields:** `id`, `name`, `code`, `external_id` (from Corporate Service), `is_active`, `last_sync`, `member_count`  
**Member fields:** `id`, `governing_body`, `member_user_id` (UUID → resolve display name from IAM), `role`, `position`, `term_start`, `term_end`, `is_active`

---

### D.3 Meeting Endpoints

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/meetings/` | `grc:legal_meeting:view` | |
| `POST` | `legal/meetings/` | `grc:legal_meeting:manage` | Auto-creates participants (GAP-04) |
| `GET` | `legal/meetings/<id>/` | `grc:legal_meeting:view` | |
| `PATCH` | `legal/meetings/<id>/` | `grc:legal_meeting:manage` | |
| `DELETE` | `legal/meetings/<id>/` | `grc:legal_meeting:manage` | Soft delete |
| `POST` | `legal/meetings/<id>/submit/` | `grc:legal_meeting:manage` | Starts WO workflow |
| `GET` | `legal/meetings/<id>/workflow-status/` | `grc:legal_meeting:view` | Current WO plan state |
| `GET` | `legal/meetings/<id>/workflow-history/` | `grc:legal_meeting:view` | WO activity log |
| `POST` | `legal/meetings/<id>/workflow-action/` | `grc:legal_meeting:approve` | Advance WO stage |
| `POST` | `legal/meetings/<id>/cancel-workflow/` | `grc:legal_meeting:manage` | Cancel WO plan |
| `GET` | `legal/meetings/<id>/attendance/` | `grc:legal_meeting:view` | Attendance records |
| `POST` | `legal/meetings/<id>/populate-matters-arising/` | `grc:legal_meeting:manage` | GAP-03 |
| `POST` | `legal/meetings/<id>/send-invitations/` | `grc:legal_meeting:manage` | Transition `registered → invitations_sent`; notifies pending participants (SRS §1.2.1) |

**Meeting status flow:** `draft → registered → invitations_sent → agenda_shared → quorum_ready → ongoing → postponed → closed → cancelled → rescheduled`  
**Workflow template:** `grc.legal_meeting_lifecycle`  
**Key fields:** `id`, `reference_number`, `title`, `governing_body`, `meeting_type`, `meeting_mode`, `scheduled_date`, `venue`, `status`, `workflow_plan_id`, `total_member_count`, `rsvp_pending_count`

---

### D.4 Minutes Endpoints

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/minutes/` | `grc:legal_minutes:view` | |
| `POST` | `legal/minutes/` | `grc:legal_minutes:manage` | Parent meeting must be `completed` |
| `GET` | `legal/minutes/<id>/` | `grc:legal_minutes:view` | |
| `PATCH` | `legal/minutes/<id>/` | `grc:legal_minutes:manage` | |
| `DELETE` | `legal/minutes/<id>/` | `grc:legal_minutes:manage` | Soft delete |
| `POST` | `legal/minutes/<id>/submit/` | `grc:legal_minutes:manage` | |
| `GET` | `legal/minutes/<id>/workflow-status/` | `grc:legal_minutes:view` | |
| `GET` | `legal/minutes/<id>/workflow-history/` | `grc:legal_minutes:view` | |
| `POST` | `legal/minutes/<id>/workflow-action/` | `grc:legal_minutes:approve` | |
| `POST` | `legal/minutes/<id>/cancel-workflow/` | `grc:legal_minutes:manage` | |
| `GET` | `legal/minutes/<id>/directives/` | `grc:legal_directive:view` | Directives for these minutes |

**Minutes status flow:** `draft → under_review → approved`  
**Workflow template:** `grc.legal_minutes_approval`

---

### D.5 Meeting Directives Endpoints

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/directives/overdue/` | `grc:legal_directive:view` | Must come before `<id>/` route |
| `GET` | `legal/directives/` | `grc:legal_directive:view` | Filter: `?status=`, `?minutes=` |
| `POST` | `legal/directives/` | `grc:legal_directive:manage` | Parent minutes must be `approved` |
| `GET` | `legal/directives/<id>/` | `grc:legal_directive:view` | |
| `PATCH` | `legal/directives/<id>/` | `grc:legal_directive:manage` | |
| `DELETE` | `legal/directives/<id>/` | `grc:legal_directive:manage` | Soft delete |

**Status flow:** `pending → in_progress → completed → overdue`  
**`is_overdue`** — set by Celery task daily, not by UI.  
**Key fields:** `id`, `minutes`, `description`, `responsible_user_id`, `due_date`, `completion_date`, `is_overdue`, `status`, `priority`, `category`

---

### D.6 Litigation Case Endpoints

The same route pattern exists for both `defendant` and `plaintiff`. Replace `defendant` with `plaintiff` for all plaintiff routes.

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/cases/defendant/` | `grc:legal_case:view` | |
| `POST` | `legal/cases/defendant/` | `grc:legal_case:manage` | Auto-creates `FinancialDefendant` (GAP-09) |
| `GET` | `legal/cases/defendant/<id>/` | `grc:legal_case:view` | |
| `PATCH` | `legal/cases/defendant/<id>/` | `grc:legal_case:manage` | |
| `DELETE` | `legal/cases/defendant/<id>/` | `grc:legal_case:manage` | Soft delete |
| `POST` | `legal/cases/defendant/<id>/submit/` | `grc:legal_case:manage` | |
| `GET` | `legal/cases/defendant/<id>/workflow-status/` | `grc:legal_case:view` | |
| `GET` | `legal/cases/defendant/<id>/workflow-history/` | `grc:legal_case:view` | |
| `POST` | `legal/cases/defendant/<id>/workflow-action/` | `grc:legal_case:close` | |
| `POST` | `legal/cases/defendant/<id>/cancel-workflow/` | `grc:legal_case:manage` | |
| `POST` | `legal/cases/defendant/<id>/archive/` | `grc:legal_case:manage` | GAP-14 |
| `POST` | `legal/cases/<side>/<id>/unarchive/` | `grc:legal_case:manage` | GAP-14; restores archived case |
| `GET` | `legal/cases/<side>/<id>/report/` | `grc:legal_case:view` | Chronological milestone timeline (SRS §4.13) |

**Reference number format:** `FCC/SUED/YYYY/NNN` (defendant), `FCC/SUING/YYYY/NNN` (plaintiff)  
**Case status flow:** `new → under_dg_review → directive_issued → hearing_stage → judgment_received → appeal_filed → closed → on_hold`  
**Workflow template:** `grc.legal_case_closure`  
**Key fields:** `id`, `reference_number`, `court_case_number`, `court_level`, `urgency_level`, `risk_level`, `status`, `dg_review_status`, `claim_amount`, `next_hearing_date`, `is_archived`, `archived_at`

**Case Report endpoint — event types aggregated:**

| Event type | Source model | Timestamp field |
|---|---|---|
| `case_registered` | `CaseDefendant` / `CasePlaintiff` | `created_at` |
| `hearing_held` | `Hearing` | `hearing_date` |
| `filing_submitted` | `FilingDefendant` / `FilingPlaintiff` | `created_at` |
| `settlement_recorded` | `SettlementDefendant` / `SettlementPlaintiff` | `settlement_date` |
| `judgment_recorded` | `JudgmentDefendant` / `JudgmentPlaintiff` | `judgment_date` |
| `appeal_filed` | `AppealDefendant` / `AppealPlaintiff` | `appeal_date` |
| `directive_issued` | `LitigationDirective` | `issue_date` |
| `case_closed` | `CaseDefendant` / `CasePlaintiff` | `updated_at` (when `status == 'closed'`) |

Events are returned sorted chronologically by timestamp. View: `CaseReportView` in `legal_case_views.py`.

---

### D.7 Hearing Endpoints

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/hearings/` | `grc:legal_hearing:view` | Filter: `?case_defendant=`, `?case_plaintiff=` |
| `POST` | `legal/hearings/` | `grc:legal_hearing:manage` | |
| `GET` | `legal/hearings/<id>/` | `grc:legal_hearing:view` | |
| `PATCH` | `legal/hearings/<id>/` | `grc:legal_hearing:manage` | |
| `DELETE` | `legal/hearings/<id>/` | `grc:legal_hearing:manage` | Soft delete |

**HearingReport** (sub-resource on hearing):  
`POST legal/hearings/<id>/reports/` — on save, auto-updates parent case `next_hearing_date` (GAP-08).

**Hearing status flow:** `scheduled → completed → adjourned → cancelled`  
**Key fields:** `id`, `case_defendant` or `case_plaintiff` (XOR), `hearing_date`, `venue`, `judge_name`, `status`, `next_hearing_date`, `outcome_summary`

---

### D.8 Litigation Directives & Tasks

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/litigation-directives/overdue/` | `grc:legal_directive:view` | |
| `GET` | `legal/litigation-directives/` | `grc:legal_directive:view` | |
| `POST` | `legal/litigation-directives/` | `grc:legal_directive:manage` | |
| `GET/PATCH/DELETE` | `legal/litigation-directives/<id>/` | view/manage | |
| `GET` | `legal/tasks/overdue/` | `grc:legal_case:view` | |
| `GET` | `legal/tasks/` | `grc:legal_case:view` | Filter: `?case_defendant=`, `?case_plaintiff=` |
| `POST` | `legal/tasks/` | `grc:legal_case:manage` | |
| `GET/PATCH/DELETE` | `legal/tasks/<id>/` | view/manage | |

---

### D.9 Filing Endpoints

Same pattern for `defendant` and `plaintiff`.

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/filings/defendant/` | `grc:legal_filing:view` | |
| `POST` | `legal/filings/defendant/` | `grc:legal_filing:manage` | Parent case must not be `closed` |
| `GET/PATCH/DELETE` | `legal/filings/defendant/<id>/` | view/manage | |
| `POST` | `legal/filings/defendant/<id>/submit/` | `grc:legal_filing:manage` | |
| `GET` | `legal/filings/defendant/<id>/workflow-status/` | view | |
| `GET` | `legal/filings/defendant/<id>/workflow-history/` | view | |
| `POST` | `legal/filings/defendant/<id>/workflow-action/` | `grc:legal_filing:approve` | |
| `POST` | `legal/filings/defendant/<id>/cancel-workflow/` | manage | |

**Filing status flow (6 stages — GAP-06):** `draft → under_review_lm → approved_lm → under_review_dg → approved → filed`  
**Workflow template:** `grc.legal_filing_approval` (4-stage: officer_review → lm_review → dg_review → filing_confirmed)  
**Filing types:** `notice_of_defense`, `counter_claim`, `notice_of_appeal`, `other`

---

### D.10 Settlement Endpoints

Same pattern for `defendant` and `plaintiff`.

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/settlements/defendant/` | `grc:legal_settlement:view` | |
| `POST` | `legal/settlements/defendant/` | `grc:legal_settlement:manage` | Parent case must be `active` |
| `GET/PATCH/DELETE` | `legal/settlements/defendant/<id>/` | view/manage | |
| Workflow routes | `.../<id>/submit/`, `workflow-status/`, `workflow-history/`, `workflow-action/`, `cancel-workflow/` | manage/approve | |

**Settlement status flow:** `draft → proposed → approved → rejected → executed`  
**Workflow template:** `grc.legal_settlement_approval`

---

### D.11 Judgment Endpoints

Same pattern for `defendant` and `plaintiff`.

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/judgments/defendant/` | `grc:legal_judgment:view` | |
| `POST` | `legal/judgments/defendant/` | `grc:legal_judgment:manage` | Parent case must be `active` |
| `GET/PATCH/DELETE` | `legal/judgments/defendant/<id>/` | view/manage | |
| `POST` | `legal/judgments/defendant/<id>/submit/` | `grc:legal_judgment:manage` | |
| Workflow routes | `workflow-status/`, `workflow-history/`, `workflow-action/`, `cancel-workflow/` | view/`record` | |

**Judgment status flow:** `pending → partial → final → appealed`  
**Workflow template:** `grc.legal_judgment_decision`  
**DG decision field:** `dg_decision` — `accept` or `appeal`. When `appeal`, triggers auto-creation (GAP-07).  
**Key fields:** `id`, `case_defendant/plaintiff`, `judgment_date`, `judge_name`, `outcome`, `awarded_amount`, `dg_decision`, `appeal_due_date`, `appeal_filing` (→ Filing), `appeal_task` (→ Task), `status`

---

### D.12 Appeal Endpoints

Appeals are **auto-created** — no POST via API. Read-only from frontend perspective.

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/appeals/defendant/` | `grc:legal_appeal:view` | |
| `GET` | `legal/appeals/defendant/<id>/` | `grc:legal_appeal:view` | |
| `PATCH` | `legal/appeals/defendant/<id>/` | `grc:legal_appeal:manage` | Limited — status updates only |
| `GET` | `legal/appeals/plaintiff/` | `grc:legal_appeal:view` | |
| `GET` | `legal/appeals/plaintiff/<id>/` | `grc:legal_appeal:view` | |

**Appeal status flow:** `pending → active → dismissed → upheld → withdrawn`  
**Key fields:** `id`, `judgment` (OneToOne), `appeal_date`, `appeal_court`, `appeal_outcome`, `status`

---

### D.13 Legal Notices Endpoints

| Method | Endpoint | Permission | Notes |
|---|---|---|---|
| `GET` | `legal/notices/` | `grc:legal_notice:view` | |
| `POST` | `legal/notices/` | `grc:legal_notice:manage` | |
| `GET/PATCH/DELETE` | `legal/notices/<id>/` | view/manage | |

**Status flow:** `draft → published → acknowledged → expired`  
**Reference format:** `LN-YYYY-NNN`

---

### D.14 Public Register Endpoints (GAP-11)

| Method | Endpoint | Auth | Notes |
|---|---|---|---|
| `GET` | `legal/public-decisions/` | Required | Secretariat CRUD |
| `POST` | `legal/public-decisions/` | `grc:legal_governing_body:manage` | |
| `GET/PATCH/DELETE` | `legal/public-decisions/<id>/` | Required | |
| `POST` | `legal/public-decisions/<id>/publish/` | `grc:legal_governing_body:manage` | Transitions → `published` |
| `GET` | `legal/public-register/` | **None (public)** | Returns only `status='published'` |

**`PublicDecision` key fields:** `id`, `title`, `body`, `decision_date`, `status` (`draft`/`published`), `published_at`

---

### D.15 Dashboard KPI Endpoints (GAP-12)

`GET legal/dashboard/defendant/` — permission: `grc:legal_case:view`

```json
{
  "total_cases": 42,
  "won_loss_ratio": "60:40",
  "cases_on_appeal": 5,
  "high_risk_cases": 8,
  "active_cases": 25,
  "pending_dg_review": 3
}
```

`GET legal/dashboard/plaintiff/` — permission: `grc:legal_case:view`

```json
{
  "total_cases": 30,
  "won_loss_ratio": "70:30",
  "cases_on_appeal": 2,
  "high_risk_cases": 4,
  "active_cases": 18,
  "pending_dg_review": 2,
  "recoverable_amount": "50000000.00",
  "recovered_amount": "12000000.00"
}
```

---

### D.16 Activity Log Endpoint (GAP-13)

`GET legal/activity-log/<entity_type>/<entity_id>/` — permission: any authenticated user

**`entity_type` values:** `meeting`, `minutes`, `case_defendant`, `case_plaintiff`, `filing_defendant`, `filing_plaintiff`, `settlement_defendant`, `settlement_plaintiff`, `judgment_defendant`, `judgment_plaintiff`, `appeal_defendant`, `appeal_plaintiff`

**Response (paginated):**
```json
{
  "count": 12,
  "results": [
    {
      "id": "...",
      "entity_type": "case_defendant",
      "entity_id": "...",
      "action": "status_changed",
      "actor_id": "...",
      "actor_name": "John Doe",
      "details": { "from": "open", "to": "active" },
      "created_at": "2025-06-01T10:30:00Z"
    }
  ]
}
```

---

### D.17 RBAC Permission Codes (Frontend Reference)

All 24 Legal permission codes. The frontend `usePermissions()` hook checks these from the JWT `permissions_flat` claim.

```
grc:legal_governing_body:view
grc:legal_governing_body:manage

grc:legal_meeting:view
grc:legal_meeting:manage
grc:legal_meeting:approve

grc:legal_minutes:view
grc:legal_minutes:manage
grc:legal_minutes:approve

grc:legal_directive:view
grc:legal_directive:manage

grc:legal_case:view
grc:legal_case:manage
grc:legal_case:close

grc:legal_hearing:view
grc:legal_hearing:manage

grc:legal_filing:view
grc:legal_filing:manage
grc:legal_filing:approve

grc:legal_settlement:view
grc:legal_settlement:manage
grc:legal_settlement:approve

grc:legal_judgment:view
grc:legal_judgment:manage
grc:legal_judgment:record

grc:legal_appeal:view
grc:legal_appeal:manage

grc:legal_notice:view
grc:legal_notice:manage
```

---

### D.18 Pagination & Filtering

All list endpoints support:
- `?page=N` — 1-based page number
- `?page_size=N` — default 20, max 100
- `?ordering=-created_at` — prefix `-` for descending
- `?search=text` — full-text search on searchable fields (varies per entity)
- `?status=value` — filter by status
- Entity-specific: `?case_defendant=<uuid>`, `?case_plaintiff=<uuid>`, `?governing_body=<uuid>`, `?meeting=<uuid>`, etc.

Paginated response shape:
```json
{ "count": 150, "page": 1, "page_size": 20, "results": [...] }
```

---

## Appendix E — Gap Fixes Record

> Full implementation notes for each of the 14 SRS gaps identified after initial backend delivery.
> All gaps are **DONE** as of March 2026.

| ID | Description | SRS Section | Severity | Status |
|---|---|---|---|---|
| GAP-01 | Case reference number format (`FCC/SUED/` not `CASE-DEF-`) | §6.2 | Low | ✅ Done |
| GAP-02 | Agenda add → auto-transition submission to `under_review` | §1.2.1 | Medium | ✅ Done |
| GAP-03 | Matters Arising auto-populate endpoint | §1.2.1 | Medium | ✅ Done |
| GAP-04 | Auto-populate meeting participants from governing body members | §1.2.1 | Medium | ✅ Done |
| GAP-05 | Conflict of Interest vote exclusion guard | §6.8 | Low | ✅ Done |
| GAP-06 | Filing workflow extended to 4 WO stages / 6 statuses | §4.3 | Medium | ✅ Done |
| GAP-07 | Judgment → Appeal auto-creation in `process_appeal_decision()` | §4.8 | High | ✅ Done |
| GAP-08 | HearingReport → propagate `next_hearing_date` to parent case | §4.6 | Medium | ✅ Done |
| GAP-09 | Financial record auto-created on case registration | §4.9 | Low | ✅ Done |
| GAP-10 | Digital Signature Engine (shared infra utility) | §6.1 | Low | ✅ Done |
| GAP-11 | Public Register views + unauthenticated public endpoint | §3.1 | Medium | ✅ Done |
| GAP-12 | Dashboard KPI endpoints (defendant + plaintiff) | §4.0, §5.0 | Medium | ✅ Done |
| GAP-13 | Activity Log API endpoint (`LegalAuditLog` per entity) | §4.12 | Low | ✅ Done |
| GAP-14 | Archiving logic — `is_archived` field + Celery task + manual endpoint | §4.15 | Low | ✅ Done |
| A17-Fix-1 | Meeting Send Invitations endpoint — `POST legal/meetings/<id>/send-invitations/` — transitions `registered → invitations_sent`, notifies pending participants | §1.2.1 | High | ✅ Done |
| A17-Fix-2 | Case Report / Timeline endpoint — `GET legal/cases/<side>/<id>/report/` — returns chronological milestone events from Hearings, Filings, Settlements, Judgments, Appeals, Directives | §4.13 | High | ✅ Done |

**Fix detail notes:**
- **GAP-07** was the highest-risk item. It involved `transaction.atomic()` across 4 model creates + case status update + Kafka event. Tested with both defendant and plaintiff sides.  
- **GAP-10** (Digital Signature) was implemented as a shared `SignatureStampingService` in `shared/services/`. It stamps approval events with timestamp, user full name (IAM-resolved), and HMAC-SHA256 hash applied to: filed documents, judgment records, settlement agreements. Not Legal-specific.  
- **GAP-06** required re-running `register_workflow_templates` after editing `workflows.yaml`. The old 2-stage template was replaced atomically — existing active workflow plans were not affected.
