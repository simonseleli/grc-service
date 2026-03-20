# Risk Management Module — Implementation Plan

**Service:** `grc-service`
**Module:** Risk Management (RMQAU)
**Stack:** Django 4.x · DRF · PostgreSQL · Celery · Kafka
**Branch:** `development`

**Design documents referenced:**
- `RISK_DOMAIN_EXTRACTION.md` — domain extraction
- `Risk_management_Module_Architecture_Mapping.md` — FIMS integration mapping
- `Internal_Audit_Backend_Patterns.md` — reference patterns
- `Risk_Management_Module_Architecture_Overview.md` — module boundaries & directory structure
- `Risk_Management_Module_Core_Design.md` — models, relationships, workflows
- `docs/GRC_INTERNAL_AUDIT_BACKEND_REFERENCE.md` — Internal Audit implementation reference

---

## Table of Contents

1. [Phase 1 — Setup & Environment](#phase-1--setup--environment)
2. [Phase 2 — Models Implementation](#phase-2--models-implementation)
3. [Phase 3 — Lookup Tables](#phase-3--lookup-tables)
4. [Phase 4 — Workflow Integration](#phase-4--workflow-integration)
5. [Phase 5 — Serializers](#phase-5--serializers)
6. [Phase 6 — Permission Classes (RBAC)](#phase-6--permission-classes-rbac)
7. [Phase 7 — Views & API Endpoints](#phase-7--views--api-endpoints)
8. [Phase 8 — URL Configuration](#phase-8--url-configuration)
9. [Phase 9 — Domain Events & Kafka](#phase-9--domain-events--kafka)
10. [Phase 10 — Celery Tasks](#phase-10--celery-tasks)
11. [Phase 11 — PDF Generation](#phase-11--pdf-generation)
12. [Phase 12 — Testing & Validation](#phase-12--testing--validation)
13. [Phase 13 — Data Seeding & Smoke Testing](#phase-13--data-seeding--smoke-testing)
14. [Implementation Order Summary](#implementation-order-summary)

---

## Phase 1 — Setup & Environment

### 1.1 Required Running Services

Before starting Risk Management development, ensure the following microservices are running locally via `docker-compose`:

| Service | Purpose | Required State |
|---------|---------|---------------|
| `grc-service` | Host service — Django dev server | Running on `localhost:8004` |
| `iam-service` | JWT issuance, user profiles | Running — needed for auth tokens |
| `work-orchestration-service` | Workflow plan management | Running — needed for workflow integration testing |
| `document-records-service` | Document storage (DRS) | Running — needed for PDF upload testing |
| `message-broker` (Kafka + Zookeeper) | Async messaging | Running — needed for event publishing |
| `PostgreSQL` | Database for grc-service | Running |
| `Redis` | Cache for IAM client user profile lookups | Running |

**To start the stack:**
```bash
cd /home/simons/Coding/FIMS
./test-start.sh          # or start individual docker-compose files
```

### 1.2 Dependencies

No new Python packages required. The existing `requirements.txt` already includes:
- `djangorestframework` — API layer
- `psycopg2-binary` — PostgreSQL
- `celery[redis]` — background tasks
- `kafka-python` — Kafka producer/consumer
- `WeasyPrint` — PDF generation
- `PyJWT` — JWT decode

### 1.3 Verify Existing Shared Infrastructure

Before writing any Risk Management code, confirm these shared files exist and are functional:

```
apps/core/models/base.py               → BaseModel, TimestampedModel, StatusMixin, WorkflowMixin
apps/core/models/lookups.py            → FiscalYear, Quarter
apps/core/models/organizational.py     → Directorate, Department, Unit, Section
apps/api/utils/pagination.py           → paginate_queryset(), get_ordering_param()
apps/api/utils/response_helpers.py     → success_response(), created_response(), etc.
apps/api/permissions_jwt.py            → _check_grc_permission_locally(), HasPermission, etc.
apps/api/authentication.py             → IAMJWTAuthentication, ServiceAuthentication
apps/infrastructure/external/orchestration_client.py → OrchestrationClient
apps/infrastructure/external/iam_client.py           → IAMClient
apps/infrastructure/external/document_service_client.py → DocumentServiceClient
apps/infrastructure/services/messaging_service.py    → KafkaMessagingService
apps/core/notifications/publisher.py                 → NotificationPublisher
apps/core/permission_middleware.py                   → JWTPermissionMiddleware
apps/core/workflow_entity_paths.py                   → ENTITY_DETAIL_PATHS dict
```

### 1.4 Create Branch

```bash
cd /home/simons/Coding/FIMS/grc-service
git checkout development
git pull origin development
git checkout -b feature/risk-management-module
```

---

## Phase 2 — Models Implementation

### 2.1 Create the Model File

**File:** `apps/core/models/risk_entities.py`

This single file contains all 20 Risk Management business models. Follow the exact structure from `Risk_Management_Module_Core_Design.md` §4.

**Implementation order within the file (top to bottom — respecting FK dependencies):**

```python
# apps/core/models/risk_entities.py

# ── Imports ────────────────────────────────────────────────────────────────
import uuid
from django.db import models
from django.utils import timezone
from .base import TimestampedModel, StatusMixin, WorkflowMixin
```

### 2.2 Implement Group 1 — Risk Champion & QA Appointment (4 models)

**Step 2.2.1:** Implement `RiskChampion`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_champion`
- Key fields: `org_unit_id` (UUIDField), `org_unit_type` (CharField choices), `user_id` (UUIDField), `nominated_by` (UUIDField), `term_start`, `term_end`, `notes`
- Constraint: `UniqueConstraint(fields=['org_unit_id', 'org_unit_type'], condition=Q(is_active=True), name='unique_active_rc_per_org_unit')`
- Source: Core Design §4.3

**Step 2.2.2:** Implement `RiskChampionAppointment`
- Inherit: `TimestampedModel, StatusMixin, WorkflowMixin`
- `db_table`: `grc_risk_champion_appointment`
- Key fields: `risk_champion` (FK), `appointment_date`, `document_id` (UUIDField, null), `stamped_document_url` (URLField), `remarks`, `status` (CharField choices: draft/submitted/approved/rejected/signed)
- Override: `get_workflow_context()`, `get_workflow_metadata()` — see Core Design §6.2
- Source: Core Design §4.3

**Step 2.2.3:** Implement `QualityAuditor`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_quality_auditor`
- Key fields: `user_id`, `nominated_by`, `org_unit_id`, `org_unit_type`, `exam_attempt` (max 2), `exam_score` (DecimalField), `is_certified` (BooleanField), `certification_date`, `term_start`, `term_end`, `notes`
- Source: Core Design §4.3

**Step 2.2.4:** Implement `QualityAuditorAppointment`
- Inherit: `TimestampedModel, StatusMixin, WorkflowMixin`
- `db_table`: `grc_risk_qa_appointment`
- Mirror `RiskChampionAppointment` structure exactly with `quality_auditor` FK instead
- Override: `get_workflow_context()`, `get_workflow_metadata()`
- Source: Core Design §4.3

### 2.3 Implement Group 2 — Risk Assessment & Departmental Register (3 models)

**Step 2.3.1:** Implement `RiskAssessmentSheet`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_assessment_sheet`
- Key fields: `risk_champion` (FK), `org_unit_id`, `fiscal_year` (FK to `core.FiscalYear`), `risk_category` (FK to `RiskCategory`), `risk_title`, `risk_description`, `risk_owner` (UUIDField), `likelihood` (FK to `RiskLikelihood`), `impact` (FK to `RiskImpact`), `inherent_risk_score` (DecimalField, auto), `inherent_risk_level` (FK to `RiskLevel`, auto), residual fields
- Override `save()`: auto-compute `inherent_risk_score = likelihood.numerical_value × impact.numerical_value`, resolve `inherent_risk_level` from `RiskLevel.min_score/max_score`, same for residual
- Source: Core Design §4.4

**Step 2.3.2:** Implement `DepartmentalRiskRegister`
- Inherit: `TimestampedModel, StatusMixin, WorkflowMixin`
- `db_table`: `grc_risk_dept_register`
- Constraint: `UniqueConstraint(fields=['org_unit_id', 'fiscal_year'], condition=Q(is_active=True), name='unique_active_dept_register_per_unit_year')`
- Override: `get_workflow_context()`, `get_workflow_metadata()`
- Source: Core Design §4.4

**Step 2.3.3:** Implement `DeptRegisterEntry`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_dept_register_entry`
- `unique_together`: `[['dept_register', 'risk_sheet']]`
- Source: Core Design §4.4

### 2.4 Implement Group 3 — Institutional Register & RTAP (5 models)

**Step 2.4.1:** Implement `InstitutionalRiskRegister`
- Inherit: `TimestampedModel, StatusMixin, WorkflowMixin`
- `db_table`: `grc_risk_inst_register`
- DRS pattern: `document_id` + `stamped_document_url`
- Constraint: `UniqueConstraint(fields=['fiscal_year'], condition=Q(is_active=True), name='unique_active_irr_per_fiscal_year')`
- Override: `get_workflow_context()`, `get_workflow_metadata()`
- Source: Core Design §4.5

**Step 2.4.2:** Implement `InstitutionalRiskEntry`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_inst_register_entry`
- `unique_together`: `[['inst_register', 'risk_sheet']]`
- Source: Core Design §4.5

**Step 2.4.3:** Implement `RiskTreatmentActionPlan`
- Inherit: `TimestampedModel, StatusMixin, WorkflowMixin`
- `db_table`: `grc_risk_rtap`
- `inst_register`: `OneToOneField(InstitutionalRiskRegister, related_name='rtap')`
- DRS pattern: `document_id` + `stamped_document_url`
- Constraint: `UniqueConstraint(fields=['fiscal_year'], condition=Q(is_active=True), name='unique_active_rtap_per_fiscal_year')`
- Override: `get_workflow_context()`, `get_workflow_metadata()`
- Source: Core Design §4.5

**Step 2.4.4:** Implement `RTAPItem`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_rtap_item`
- Key fields: `rtap` (FK), `inst_entry` (FK to `InstitutionalRiskEntry`), `treatment_description`, `responsible_officer` (UUIDField), `target_date`, `sort_order` (IntegerField, default 0)
- Status choices: `not_started/in_progress/completed` (Rule E.10)
- Source: Core Design §4.5

**Step 2.4.5:** Implement `RTAPQuarterlyUpdate`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_rtap_quarterly_update`
- `evidence`: `JSONField(default=list)`
- `unique_together`: `[['rtap_item', 'quarter']]`
- Source: Core Design §4.5

### 2.5 Implement Group 4 — Quarterly Reporting (2 models)

**Step 2.5.1:** Implement `QuarterlyPerformanceReport`
- Inherit: `TimestampedModel, StatusMixin, WorkflowMixin`
- `db_table`: `grc_risk_quarterly_report`
- Snapshot metrics: `total_risks`, `high_risks`, `medium_risks`, `low_risks`, `rtap_completed`, `rtap_in_progress`, `rtap_not_started`
- DRS pattern: `document_id` + `stamped_document_url`
- Constraint: `UniqueConstraint(fields=['fiscal_year', 'quarter'], condition=Q(is_active=True), name='unique_active_quarterly_report_per_period')`
- Override: `get_workflow_context()`, `get_workflow_metadata()`
- Source: Core Design §4.6

**Step 2.5.2:** Implement `ActivityReport`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_activity_report`
- `attachments`: `JSONField(default=list)`
- `unique_together`: `[['inst_register', 'quarter', 'reported_by']]`
- Source: Core Design §4.6

### 2.6 Implement Group 5 — QMS Audit (6 models)

**Step 2.6.1:** Implement `QMSAuditProgram`
- Inherit: `TimestampedModel, StatusMixin, WorkflowMixin`
- `db_table`: `grc_risk_qms_program`
- Key fields: `fiscal_year` (FK), `program_title`, `objective`, `scope`, `prepared_by` (UUIDField), `approved_by` (UUIDField, null), `approval_date` (DateField, null)
- Status choices: `draft/submitted/approved/rejected`
- Constraint: `UniqueConstraint(fields=['fiscal_year'], condition=Q(is_active=True), name='unique_active_qms_program_per_fiscal_year')`
- Override: `get_workflow_context()`, `get_workflow_metadata()`
- Source: Core Design §4.7

**Step 2.6.2:** Implement `QMSAuditPlan`
- Inherit: `TimestampedModel, StatusMixin, WorkflowMixin`
- `db_table`: `grc_risk_qms_plan`
- DRS pattern: `document_id` + `stamped_document_url`
- `clean()` validation: `notification_date` must be ≥10 days before `audit_start_date` (Rule E.7)
- Override: `get_workflow_context()`, `get_workflow_metadata()`
- Source: Core Design §4.7

**Step 2.6.3:** Implement `QMSAuditTeamAssignment`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_qms_team_assignment`
- `unique_together`: `[['audit_plan', 'auditor_id']]`
- Source: Core Design §4.7

**Step 2.6.4:** Implement `AuditChecklist`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_qms_checklist`
- `findings_detail`: `JSONField(default=dict)`
- `unique_together`: `[['audit_plan', 'iso_clause', 'auditor_id']]`
- Source: Core Design §4.7

**Step 2.6.5:** Implement `QMSAuditReport`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_qms_report`
- `audit_plan`: `OneToOneField(QMSAuditPlan, related_name='report')`
- DRS pattern: `document_id` + `stamped_document_url`
- Source: Core Design §4.7

**Step 2.6.6:** Implement `NonConformance`
- Inherit: `TimestampedModel, StatusMixin`
- `db_table`: `grc_risk_nonconformance`
- Key fields: `audit_report` (FK), `iso_clause` (FK), `nc_type` (FK), `description`, `objective_evidence`, `raised_by` (UUIDField), `corrective_action`, `responsible_officer` (UUIDField, null), `due_date` (DateField, null)
- Status choices: `raised/acknowledged/in_progress/closed`
- Closure fields: `closed_at` (DateTimeField, null), `closure_notes` (TextField, blank) — populated when status transitions to `closed`
- Source: Core Design §4.7

### 2.7 Register Models in `__init__.py`

**File:** `apps/core/models/__init__.py`

Add imports for all 20 Risk Management models so Django picks them up for migrations:

```python
# Risk Management models
from .risk_entities import (
    RiskChampion,
    RiskChampionAppointment,
    QualityAuditor,
    QualityAuditorAppointment,
    RiskAssessmentSheet,
    DepartmentalRiskRegister,
    DeptRegisterEntry,
    InstitutionalRiskRegister,
    InstitutionalRiskEntry,
    RiskTreatmentActionPlan,
    RTAPItem,
    RTAPQuarterlyUpdate,
    QuarterlyPerformanceReport,
    ActivityReport,
    QMSAuditProgram,
    QMSAuditPlan,
    QMSAuditTeamAssignment,
    AuditChecklist,
    QMSAuditReport,
    NonConformance,
)
```

### 2.8 Generate and Run Migrations

```bash
cd /home/simons/Coding/FIMS/grc-service
python manage.py makemigrations core
python manage.py migrate
```

Verify all 20+ tables are created with `grc_risk_*` prefix:
```bash
python manage.py dbshell
\dt grc_risk_*
```

---

## Phase 3 — Lookup Tables

### 3.1 Add Lookup Models

> **Design conflict resolved:** Core Design §5.2 states *"All new lookup tables live in `apps/risk_management/models/lookups.py`"*, but the Architecture Overview §2.1 (the definitive directory specification) shows no `apps/risk_management/` directory anywhere in the project layout. The Architecture Overview supersedes Core Design §5.2 on directory structure. All new lookup tables are therefore added to **`apps/core/models/lookups.py`** to remain consistent with the existing `FiscalYear`, `Quarter`, and `AuditSeverity` lookup models that already live there.

**File:** `apps/core/models/lookups.py` (extend existing file)

Append 6 new lookup models below the existing `FiscalYear`, `Quarter`, `AuditSeverity`, etc. models:

**Step 3.1.1:** `RiskCategory`
```python
class RiskCategory(TimestampedModel, StatusMixin):
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_category'
        ordering = ['sort_order', 'name']
```

**Step 3.1.2:** `RiskLikelihood`
- Extra fields: `label` (CharField), `numerical_value` (DecimalField)
- `db_table`: `grc_risk_likelihood`

**Step 3.1.3:** `RiskImpact`
- Extra fields: `label` (CharField), `numerical_value` (DecimalField)
- `db_table`: `grc_risk_impact`

**Step 3.1.4:** `RiskLevel`
- Extra fields: `min_score` (DecimalField), `max_score` (DecimalField), `color_code` (CharField)
- `db_table`: `grc_risk_level`

**Step 3.1.5:** `NonConformanceType`
- Standard `code/name/description/sort_order` pattern
- `db_table`: `grc_risk_nc_type`

**Step 3.1.6:** `ISOClause`
- Extra fields: `clause_number` (CharField), `title` (CharField), `parent_clause` (self FK, nullable)
- `db_table`: `grc_risk_iso_clause`

Full field definitions: Core Design §5.2

### 3.2 Register Lookup Imports

**File:** `apps/core/models/__init__.py`

Add imports for all 6 new lookup models.

### 3.3 Generate Migrations

```bash
python manage.py makemigrations core
python manage.py migrate
```

### 3.4 Seed Initial Data

**File:** `apps/core/management/commands/seed_risk_lookups.py` (new)

Create a management command that populates initial lookup data:

```python
from django.core.management.base import BaseCommand
from apps.core.models.lookups import (
    RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
    NonConformanceType, ISOClause,
)

class Command(BaseCommand):
    help = "Seed Risk Management lookup tables with initial data"

    def handle(self, *args, **options):
        self._seed_risk_categories()
        self._seed_risk_likelihood()
        self._seed_risk_impact()
        self._seed_risk_levels()
        self._seed_nc_types()
        self._seed_iso_clauses()
        self.stdout.write(self.style.SUCCESS("Risk lookups seeded."))
```

**Seed data:**

| RiskCategory codes | `operational`, `financial`, `strategic`, `compliance`, `reputational`, `technology` |
|---|---|

| RiskLikelihood codes | `rare` (1), `unlikely` (2), `possible` (3), `likely` (4), `almost_certain` (5) |
|---|---|

| RiskImpact codes | `negligible` (1), `minor` (2), `moderate` (3), `major` (4), `catastrophic` (5) |
|---|---|

| RiskLevel codes | `low` (1–4, green), `medium` (5–9, yellow), `high` (10–16, orange), `critical` (17–25, red) |
|---|---|

| NonConformanceType codes | `major_nc`, `minor_nc`, `observation`, `opportunity_for_improvement` |
|---|---|

| ISOClause | Clauses 4–10 of ISO 9001:2015 (Context, Leadership, Planning, Support, Operation, Performance Evaluation, Improvement) with sub-clauses |
|---|---|

Run:
```bash
python manage.py seed_risk_lookups
```

### 3.5 Add Lookup Serializers

**File:** `apps/api/serializers/lookup_serializers.py` (extend existing)

Add serializers for each new lookup model following the existing pattern:

```python
class RiskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCategory
        fields = ['id', 'code', 'name', 'description', 'sort_order', 'is_active']

class RiskLikelihoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskLikelihood
        fields = ['id', 'code', 'name', 'label', 'numerical_value', 'sort_order', 'is_active']

class RiskImpactSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskImpact
        fields = ['id', 'code', 'name', 'label', 'numerical_value', 'sort_order', 'is_active']

class RiskLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskLevel
        fields = ['id', 'code', 'name', 'min_score', 'max_score', 'color_code', 'sort_order', 'is_active']

class NonConformanceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NonConformanceType
        fields = ['id', 'code', 'name', 'description', 'sort_order', 'is_active']

class ISOClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ISOClause
        fields = ['id', 'code', 'clause_number', 'title', 'description', 'parent_clause', 'sort_order', 'is_active']
```

### 3.6 Add Lookup Endpoints

**File:** `apps/api/views/lookup_views.py` (extend existing)

Add read-only list endpoints for each new lookup model. These are used by the frontend for dropdown population.

**File:** `apps/api/urls/config_urls.py` (extend existing)

Add admin CRUD URLs for lookup management.

---

## Phase 4 — Workflow Integration

### 4.1 Append Workflow Templates to YAML

**File:** `apps/core/workflows/workflows.yaml` (extend existing)

Append all 8 Risk Management workflow templates under the existing `templates:` key. Full YAML blocks are defined in Core Design §6.1.

Templates to add:

| # | Template Code | Stages (stage count) |
|---|---|---|
| 1 | `grc.risk_champion_appointment` | `rmo_draft → rmqam_review → dg_signature` (3) |
| 2 | `grc.dept_risk_register_approval` | `rc_submit → rmqam_approve` (2) |
| 3 | `grc.institutional_risk_register_approval` | `rmqam_review → management_discussion → committee_review → commission_approval` (4) |
| 4 | `grc.rtap_approval` | `rmqam_review → management_discussion → committee_review → commission_approval` (4) |
| 5 | `grc.quarterly_risk_report_approval` | `rmqam_prepare → lsm_submit → management_discussion → committee_review → commission_submit` (5) |
| 6 | `grc.qa_appointment` | `rmo_draft → rmqam_review → dg_signature` (3) |
| 7 | `grc.qms_audit_program_approval` | `rmo_submit → rmqam_approve` (2) |
| 8 | `grc.qms_audit_plan_approval` | `rmo_submit → rmqam_approve` (2) |

**YAML conventions to follow:**
- `definitionKey`: `snake_case`
- `assignees`: `["role:grc.rmqam"]` etc.
- `metadata.status_on_complete`: the local status value to set on the model
- `sla`: `warningDays` and `overdueDays` per stage

### 4.2 Register Workflow Entity Paths

**File:** `apps/core/workflow_entity_paths.py` (extend existing)

Add 8 new entries to the `ENTITY_DETAIL_PATHS` dict:

```python
ENTITY_DETAIL_PATHS = {
    # ... existing Internal Audit entries ...

    # Risk Management
    'risk_champion_appointment': '/service/grc/risk/champions',
    'departmental_risk_register': '/service/grc/risk/dept-registers',
    'institutional_risk_register': '/service/grc/risk/institutional-registers',
    'risk_treatment_action_plan': '/service/grc/risk/rtap',
    'quarterly_performance_report': '/service/grc/risk/quarterly-reports',
    'quality_auditor_appointment': '/service/grc/risk/quality-auditors',
    'qms_audit_program': '/service/grc/risk/qms-programs',
    'qms_audit_plan': '/service/grc/risk/qms-plans',
}
```

### 4.3 Create Service Classes (8 files)

Create one service class per workflow-enabled entity in `apps/core/services/`. Each follows the **exact 5-method pattern** from `audit_plan_service.py`:

| # | File | Class | Template Code |
|---|---|---|---|
| 1 | `risk_champion_service.py` | `RiskChampionAppointmentService` | `grc.risk_champion_appointment` |
| 2 | `dept_risk_register_service.py` | `DeptRiskRegisterService` | `grc.dept_risk_register_approval` |
| 3 | `institutional_risk_register_service.py` | `InstitutionalRiskRegisterService` | `grc.institutional_risk_register_approval` |
| 4 | `rtap_service.py` | `RTAPService` | `grc.rtap_approval` |
| 5 | `quarterly_risk_report_service.py` | `QuarterlyRiskReportService` | `grc.quarterly_risk_report_approval` |
| 6 | `quality_auditor_service.py` | `QualityAuditorAppointmentService` | `grc.qa_appointment` |
| 7 | `qms_audit_program_service.py` | `QMSAuditProgramService` | `grc.qms_audit_program_approval` |
| 8 | `qms_audit_plan_service.py` | `QMSAuditPlanService` | `grc.qms_audit_plan_approval` |

**Every service class implements these 5 methods:**

```python
class EntityService:
    WORKFLOW_TEMPLATE_CODE = "grc.template_code"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(self, entity_id: str, submitter_id: str):
        """Start WO workflow plan for the entity."""
        # 1. select_for_update()
        # 2. Guard: if entity.workflow_plan_id already set, skip
        # 3. Build context via entity.get_workflow_context()
        # 4. Build metadata via entity.get_workflow_metadata()
        # 5. Call self.workflow_client.start_workflow(...)
        # 6. Call entity.start_workflow(plan_id, initial_stage, stage_id)
        # 7. Set entity.status = first stage's status_on_complete
        # 8. entity.save(update_fields=[5 workflow fields + 'status'])

    def get_workflow_status(self, entity_id: str):
        """Return WO plan status dict."""

    def get_workflow_history(self, entity_id: str):
        """Return WO activity log list."""

    @transaction.atomic
    def advance_workflow_stage(self, entity_id: str, action: str, actor_id: str, comment: str = ''):
        """Execute a WO stage action and update local entity."""
        # 1. select_for_update()
        # 2. Call self.workflow_client.advance_stage(plan_id, stage_id, action, actor_id, comment)
        # 3. Update entity stage (update_workflow_stage or complete_workflow)
        # 4. entity.save()

    @transaction.atomic
    def cancel_workflow_plan(self, entity_id: str, actor_id: str, reason: str = ''):
        """Cancel active WO plan."""
        # 1. select_for_update()
        # 2. Call self.workflow_client.cancel_plan(...)
        # 3. entity.cancel_workflow()
        # 4. entity.save(update_fields=['workflow_completed_at'])
```

> **Note (Core Design §6.4):** Service classes handle more than just workflow orchestration. Each service class also includes entity-level query helpers (e.g., `get_active_risk_champions(org_unit_id=None)`) and creation helpers (e.g., `create_risk_champion(user_id, org_unit_id, ...)`) that enforce business rules belonging in the service layer rather than in views. For example, `RiskChampionAppointmentService` validates that no other active appointment exists before creating a new one. The 5 workflow methods above are the **minimum required skeleton** — add entity CRUD methods as specified in Core Design §6.4 for each service.

**Implementation steps for each service file:**
1. Copy the structure from `apps/core/services/audit_plan_service.py`
2. Replace model imports, template code constant, and entity-specific field names
3. No additional business logic — keep services focused on workflow only

---

## Phase 5 — Serializers

### 5.1 Create Serializer File

**File:** `apps/api/serializers/risk_serializers.py`

### 5.2 Implement Serializers for All 20 Models

Follow the FK dual-field pattern for every serializer. Implementation order matches the model groups:

#### Group 1 Serializers

**`RiskChampionSerializer`**
```python
class RiskChampionSerializer(serializers.ModelSerializer):
    # No FK to resolve — org_unit_id and user_id are raw UUIDs
    class Meta:
        model = RiskChampion
        fields = [
            'id', 'org_unit_id', 'org_unit_type', 'user_id', 'nominated_by',
            'term_start', 'term_end', 'notes', 'is_active',
            'created_at', 'updated_at', 'created_by',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
        }
```

**`RiskChampionAppointmentSerializer`**
```python
class RiskChampionAppointmentSerializer(serializers.ModelSerializer):
    # FK dual-field: read nested, write UUID
    risk_champion = RiskChampionSerializer(read_only=True)
    risk_champion_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RiskChampionAppointment
        fields = [
            'id', 'risk_champion', 'risk_champion_id', 'appointment_date',
            'document_id', 'stamped_document_url', 'remarks', 'status',
            'workflow_plan_id', 'workflow_stage', 'has_active_workflow', 'is_workflow_completed',
            'created_at', 'updated_at', 'created_by',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'status': {'required': False},
        }
```

Apply the same pattern for `QualityAuditorSerializer` and `QualityAuditorAppointmentSerializer`.

#### Group 2 Serializers

**`RiskAssessmentSheetSerializer`** — most complex serializer:
```python
class RiskAssessmentSheetSerializer(serializers.ModelSerializer):
    # FK dual-fields
    risk_champion = RiskChampionSerializer(read_only=True)
    risk_champion_id = serializers.UUIDField(write_only=True)
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)
    risk_category = RiskCategorySerializer(read_only=True)
    risk_category_id = serializers.UUIDField(write_only=True)
    likelihood = RiskLikelihoodSerializer(read_only=True)
    likelihood_id = serializers.UUIDField(write_only=True)
    impact = RiskImpactSerializer(read_only=True)
    impact_id = serializers.UUIDField(write_only=True)
    # Computed read-only fields
    inherent_risk_level = RiskLevelSerializer(read_only=True)
    inherent_risk_score = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    # Residual FK dual-fields (optional)
    residual_likelihood = RiskLikelihoodSerializer(read_only=True)
    residual_likelihood_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    residual_impact = RiskImpactSerializer(read_only=True)
    residual_impact_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    residual_risk_level = RiskLevelSerializer(read_only=True)
    residual_risk_score = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = RiskAssessmentSheet
        fields = [...]   # all fields above + risk_title, risk_description, risk_owner, etc.
        extra_kwargs = {
            'created_by': {'required': False},
            'inherent_risk_score': {'read_only': True},
            'inherent_risk_level': {'read_only': True},
            'residual_risk_score': {'read_only': True},
            'residual_risk_level': {'read_only': True},
        }
```

**`DepartmentalRiskRegisterSerializer`** and **`DeptRegisterEntrySerializer`** — standard FK dual-field pattern.

#### Group 3 Serializers

- `InstitutionalRiskRegisterSerializer` — includes `document_id`, `stamped_document_url` as optional read/write fields
- `InstitutionalRiskEntrySerializer`
- `RiskTreatmentActionPlanSerializer` — includes `overall_progress` as `read_only=True`
- `RTAPItemSerializer`
- `RTAPQuarterlyUpdateSerializer` — `evidence` as `ListField` or `JSONField`

#### Group 4 Serializers

- `QuarterlyPerformanceReportSerializer` — snapshot metric fields are writable (populated by RMQAM or computed at submission)
- `ActivityReportSerializer` — `attachments` as JSONField

#### Group 5 Serializers

- `QMSAuditProgramSerializer`
- `QMSAuditPlanSerializer`
- `QMSAuditTeamAssignmentSerializer`
- `AuditChecklistSerializer` — `findings_detail` as JSONField
- `QMSAuditReportSerializer` — includes `tl_signed_at`, `auditee_signed_at` as read-only DateTimeFields
- `NonConformanceSerializer`

### 5.3 Serializer Rules Checklist

For every serializer:
- [ ] FK read: `NestedSerializer(read_only=True)`
- [ ] FK write: `UUIDField(write_only=True)`
- [ ] `created_by` in `extra_kwargs` with `required=False`
- [ ] All auto-computed fields: `read_only=True`
- [ ] All 5 `WorkflowMixin` fields exposed as read-only where needed: `workflow_plan_id`, `workflow_stage`, `workflow_stage_id`, `workflow_started_at`, `workflow_completed_at`; plus 3 properties: `has_workflow`, `has_active_workflow`, `is_workflow_completed` (Core Design §3.4)
- [ ] `document_id` and `stamped_document_url`: `required=False`

---

## Phase 6 — Permission Classes (RBAC)

### 6.1 Define Permission Codes

**File:** `config/permissions/grc-service.json` (extend existing)

Add all Risk Management permission codes under a new `"risk_management"` category section. Codes follow the `grc:{resource}:{action}` convention:

```json
{
  "permissions": [
    {"code": "grc:risk_champion:view", "name": "View Risk Champions", "category": "risk_management"},
    {"code": "grc:risk_champion:manage", "name": "Manage Risk Champions", "category": "risk_management"},
    {"code": "grc:risk_assessment:conduct", "name": "Conduct Risk Assessments", "category": "risk_management"},
    {"code": "grc:risk_assessment:review", "name": "Review Risk Assessments", "category": "risk_management"},
    {"code": "grc:dept_risk_register:manage", "name": "Manage Departmental Risk Register", "category": "risk_management"},
    {"code": "grc:dept_risk_register:approve", "name": "Approve Departmental Risk Register", "category": "risk_management"},
    {"code": "grc:institutional_risk_register:manage", "name": "Manage Institutional Risk Register", "category": "risk_management"},
    {"code": "grc:institutional_risk_register:approve", "name": "Approve Institutional Risk Register", "category": "risk_management"},
    {"code": "grc:rtap:manage", "name": "Manage RTAP", "category": "risk_management"},
    {"code": "grc:rtap:approve", "name": "Approve RTAP", "category": "risk_management"},
    {"code": "grc:rtap:respond", "name": "Respond to RTAP Items", "category": "risk_management"},
    {"code": "grc:quarterly_risk_report:manage", "name": "Manage Quarterly Reports", "category": "risk_management"},
    {"code": "grc:quarterly_risk_report:approve", "name": "Approve Quarterly Reports", "category": "risk_management"},
    {"code": "grc:quality_auditor:manage", "name": "Manage Quality Auditors", "category": "risk_management"},
    {"code": "grc:qms_audit_program:manage", "name": "Manage QMS Audit Programs", "category": "risk_management"},
    {"code": "grc:qms_audit_program:approve", "name": "Approve QMS Audit Programs", "category": "risk_management"},
    {"code": "grc:qms_audit_plan:manage", "name": "Manage QMS Audit Plans", "category": "risk_management"},
    {"code": "grc:qms_audit_plan:approve", "name": "Approve QMS Audit Plans", "category": "risk_management"},
    {"code": "grc:qms_checklist:manage", "name": "Manage Audit Checklists", "category": "risk_management"},
    {"code": "grc:qms_audit_report:manage", "name": "Manage QMS Audit Reports", "category": "risk_management"},
    {"code": "grc:qms_audit_report:sign", "name": "Sign QMS Audit Reports", "category": "risk_management"},
    {"code": "grc:non_conformance:manage", "name": "Manage Non-Conformances", "category": "risk_management"},
    {"code": "grc:non_conformance:respond", "name": "Respond to Non-Conformances", "category": "risk_management"},
    {"code": "grc:risk_dashboard:view", "name": "View Risk Dashboard", "category": "risk_management"}
  ]
}
```

Also define roles and their permission assignments:

```json
{
  "roles": [
    {
      "code": "rmqam",
      "name": "Risk Management and Quality Assurance Manager",
      "permissions": ["grc:risk_champion:view", "grc:risk_champion:manage", "grc:risk_assessment:review",
                       "grc:dept_risk_register:manage", "grc:dept_risk_register:approve",
                       "grc:institutional_risk_register:manage", "grc:institutional_risk_register:approve",
                       "grc:rtap:manage", "grc:rtap:approve",
                       "grc:quarterly_risk_report:manage", "grc:quarterly_risk_report:approve",
                       "grc:quality_auditor:manage",
                       "grc:qms_audit_program:manage", "grc:qms_audit_program:approve",
                       "grc:qms_audit_plan:manage", "grc:qms_audit_plan:approve",
                       "grc:qms_checklist:manage", "grc:qms_audit_report:manage", "grc:qms_audit_report:sign",
                       "grc:non_conformance:manage", "grc:risk_dashboard:view"]
    },
    {
      "code": "rmo",
      "name": "Risk Management Officer",
      "permissions": ["grc:risk_champion:view", "grc:risk_champion:manage",
                       "grc:risk_assessment:review", "grc:dept_risk_register:manage",
                       "grc:institutional_risk_register:manage", "grc:rtap:manage",
                       "grc:quarterly_risk_report:manage", "grc:quality_auditor:manage",
                       "grc:qms_audit_program:manage", "grc:qms_audit_plan:manage",
                       "grc:qms_checklist:manage", "grc:qms_audit_report:manage",
                       "grc:non_conformance:manage", "grc:risk_dashboard:view"]
    },
    {
      "code": "risk_champion",
      "name": "Risk Champion",
      "permissions": ["grc:risk_assessment:conduct", "grc:dept_risk_register:manage",
                       "grc:rtap:respond", "grc:risk_dashboard:view"]
    },
    {
      "code": "quality_auditor",
      "name": "Quality Auditor",
      "permissions": ["grc:qms_checklist:manage", "grc:qms_audit_report:manage",
                       "grc:non_conformance:manage"]
    },
    {
      "code": "director_general",
      "name": "Director General",
      "permissions": ["grc:risk_champion:view", "grc:quality_auditor:manage",
                       "grc:risk_dashboard:view"]
    }
  ]
}
```

### 6.2 Create Named Permission Classes

**File:** `apps/api/permissions_jwt.py` (extend existing)

Add one `BasePermission` subclass per permission code. Each follows the exact Internal Audit pattern:

```python
# ── Risk Management Permission Classes ──────────────────────────────────────

class CanViewRiskChampion(BasePermission):
    """Check: grc:risk_champion:view"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:risk_champion:view')

class CanManageRiskChampion(BasePermission):
    """Check: grc:risk_champion:manage"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:risk_champion:manage')

# ... repeat for all 24 permission codes ...
```

Full list of classes to create (24 total):

| Class Name | Permission Code |
|---|---|
| `CanViewRiskChampion` | `grc:risk_champion:view` |
| `CanManageRiskChampion` | `grc:risk_champion:manage` |
| `CanConductRiskAssessment` | `grc:risk_assessment:conduct` |
| `CanReviewRiskAssessment` | `grc:risk_assessment:review` |
| `CanManageDeptRiskRegister` | `grc:dept_risk_register:manage` |
| `CanApproveDeptRiskRegister` | `grc:dept_risk_register:approve` |
| `CanManageInstitutionalRiskRegister` | `grc:institutional_risk_register:manage` |
| `CanApproveInstitutionalRiskRegister` | `grc:institutional_risk_register:approve` |
| `CanManageRTAP` | `grc:rtap:manage` |
| `CanApproveRTAP` | `grc:rtap:approve` |
| `CanRespondRTAP` | `grc:rtap:respond` |
| `CanManageQuarterlyRiskReport` | `grc:quarterly_risk_report:manage` |
| `CanApproveQuarterlyRiskReport` | `grc:quarterly_risk_report:approve` |
| `CanManageQualityAuditor` | `grc:quality_auditor:manage` |
| `CanManageQMSAuditProgram` | `grc:qms_audit_program:manage` |
| `CanApproveQMSAuditProgram` | `grc:qms_audit_program:approve` |
| `CanManageQMSAuditPlan` | `grc:qms_audit_plan:manage` |
| `CanApproveQMSAuditPlan` | `grc:qms_audit_plan:approve` |
| `CanManageQMSChecklist` | `grc:qms_checklist:manage` |
| `CanManageQMSAuditReport` | `grc:qms_audit_report:manage` |
| `CanSignQMSAuditReport` | `grc:qms_audit_report:sign` |
| `CanManageNonConformance` | `grc:non_conformance:manage` |
| `CanRespondNonConformance` | `grc:non_conformance:respond` |
| `CanViewRiskDashboard` | `grc:risk_dashboard:view` |

---

## Phase 7 — Views & API Endpoints

### 7.1 Create View Files (14 files)

Create one view file per entity or tightly-related entity group in `apps/api/views/`:

| # | File | Entities Covered | Key Endpoints |
|---|---|---|---|
| 1 | `risk_champion_views.py` | `RiskChampion`, `RiskChampionAppointment` | CRUD + 6 workflow endpoints |
| 2 | `risk_assessment_sheet_views.py` | `RiskAssessmentSheet` | CRUD |
| 3 | `dept_risk_register_views.py` | `DepartmentalRiskRegister`, `DeptRegisterEntry` | CRUD + 6 workflow + entries sub-resource |
| 4 | `institutional_risk_register_views.py` | `InstitutionalRiskRegister`, `InstitutionalRiskEntry`, `ActivityReport` | CRUD + 6 workflow + entries sub-resource + activity-reports sub-resource |
| 5 | `risk_treatment_plan_views.py` | `RiskTreatmentActionPlan` | CRUD + 6 workflow |
| 6 | `rtap_item_views.py` | `RTAPItem`, `RTAPQuarterlyUpdate` | CRUD + quarterly updates as sub-resource |
| 7 | `quarterly_risk_report_views.py` | `QuarterlyPerformanceReport` | CRUD + 6 workflow |
| 8 | `quality_auditor_views.py` | `QualityAuditor`, `QualityAuditorAppointment` | CRUD + 6 workflow endpoints |
| 9 | `qms_audit_program_views.py` | `QMSAuditProgram` | CRUD + 6 workflow |
| 10 | `qms_audit_plan_views.py` | `QMSAuditPlan`, `QMSAuditTeamAssignment` | CRUD + 6 workflow + team sub-resource |
| 11 | `qms_audit_checklist_views.py` | `AuditChecklist` | CRUD |
| 12 | `qms_audit_report_views.py` | `QMSAuditReport` | CRUD + sign-tl/ + sign-auditee/ |
| 13 | `non_conformance_views.py` | `NonConformance` | CRUD |
| 14 | `risk_dashboard_views.py` | — (aggregations) | GET only |

### 7.2 Standard View Implementation Pattern

Every CRUD view follows this exact template. Example for `RiskChampionListCreateView`:

```python
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    success_response, created_response, updated_response, deleted_response,
    paginated_list_response, error_response, validation_error_response,
    server_error_response, conflict_response,
)
from apps.api.permissions_jwt import CanViewRiskChampion, CanManageRiskChampion
from apps.api.serializers.risk_serializers import RiskChampionSerializer
from apps.core.models.risk_entities import RiskChampion

logger = logging.getLogger(__name__)


class RiskChampionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewRiskChampion().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_champion:view required.')
        elif request.method == 'POST':
            if not CanManageRiskChampion().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_champion:manage required.')

    def get(self, request):
        try:
            org_unit_id = request.query_params.get('org_unit_id')
            status_filter = request.query_params.get('status')

            queryset = RiskChampion.objects.filter(is_active=True)

            if org_unit_id:
                queryset = queryset.filter(org_unit_id=org_unit_id)

            ordering = get_ordering_param(
                request,
                default='-created_at',
                allowed_fields=['created_at', 'term_start', 'org_unit_type']
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = RiskChampionSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk champions")
            return server_error_response(message="Failed to retrieve risk champions")

    def post(self, request):
        try:
            serializer = RiskChampionSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request, 'user_id', None)
                if not user_id:
                    return error_response(message="User not authenticated", code="AUTH_REQUIRED", status_code=401)

                with transaction.atomic():
                    champion = serializer.save(created_by=user_id)

                return created_response(data=RiskChampionSerializer(champion).data)
            return validation_error_response(errors=serializer.errors)
        except Exception as e:
            logger.exception("Failed to create risk champion")
            return server_error_response(message="Failed to create risk champion")
```

### 7.3 Workflow Endpoint Views

For each of the 8 workflow-enabled entities, implement 6 additional view classes. The endpoint suffix naming follows **Core Design §6.3 exactly** — do NOT use the Internal Audit naming (`submit/`, `workflow-action/`, etc.).

Endpoint suffix mapping (Core Design §6.3):

| Suffix | HTTP Method | View Class Suffix | Service Method |
|---|---|---|---|
| `workflow/start/` | POST | `WorkflowStartView` | `submit_for_approval()` |
| `workflow/status/` | GET | `WorkflowStatusView` | `get_workflow_status()` |
| `workflow/advance/` | POST | `WorkflowAdvanceView` | `advance_workflow_stage()` |
| `workflow/cancel/` | POST | `WorkflowCancelView` | `cancel_workflow_plan()` |
| `workflow/recall/` | POST | `WorkflowRecallView` | `recall_workflow()` |
| `workflow/history/` | GET | `WorkflowHistoryView` | `get_workflow_history()` |

> **Recall vs Cancel semantics (Core Design §6.3):** `workflow/cancel/` marks the workflow as terminated (rejected path — maps entity status to `cancelled`). `workflow/recall/` calls WO cancel, then calls `entity.clear_workflow()`, and resets `entity.status = 'draft'` — allowing the submitter to amend and resubmit.

Example for `RiskChampionAppointment`:

**`RiskChampionAppointmentWorkflowStartView`** (POST `workflow/start/`)
```python
class RiskChampionAppointmentWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRiskChampion().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_champion:manage required.')

    def post(self, request, pk):
        try:
            service = RiskChampionAppointmentService()
            entity = service.submit_for_approval(
                entity_id=str(pk),
                submitter_id=str(request.user_id),
            )
            return success_response(
                data=RiskChampionAppointmentSerializer(entity).data,
                message="Appointment submitted for approval."
            )
        except ValueError as e:
            return error_response(message=str(e), code="WORKFLOW_ERROR")
        except Exception as e:
            logger.exception("Failed to start appointment workflow")
            return server_error_response(message="Failed to start appointment workflow")
```

**`RiskChampionAppointmentWorkflowStatusView`** (GET `workflow/status/`)
```python
class RiskChampionAppointmentWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            service = RiskChampionAppointmentService()
            status_data = service.get_workflow_status(entity_id=str(pk))
            if status_data is None:
                return error_response(message="No workflow found", code="NO_WORKFLOW")
            return success_response(data=status_data)
        except Exception as e:
            logger.exception("Failed to get workflow status")
            return server_error_response(message="Failed to get workflow status")
```

**`RiskChampionAppointmentWorkflowHistoryView`** (GET `workflow/history/`)
**`RiskChampionAppointmentWorkflowAdvanceView`** (POST `workflow/advance/`)
**`RiskChampionAppointmentWorkflowCancelView`** (POST `workflow/cancel/`)
**`RiskChampionAppointmentWorkflowRecallView`** (POST `workflow/recall/`) — calls service `recall_workflow()`, which cancels WO plan + calls `entity.clear_workflow()` + resets status to `draft`.

Repeat this 6-view pattern for all 8 workflow entities = 48 workflow views total.

### 7.4 Special Endpoint Views

**`QMSAuditReportSignTLView`** (POST `sign-tl/`)
- Sets `tl_signed_by` and `tl_signed_at`
- Validates report has at least one NC or explicit confirmation of no NCs

**`QMSAuditReportSignAuditeeView`** (POST `sign-auditee/`)
- Sets `auditee_signed_by` and `auditee_signed_at`
- When both signatures present: trigger PDF generation + DRS upload

**`RiskDashboardView`** (GET only)
- Returns aggregated stats: risk count by level, RTAP implementation rate, active RC/QA counts
- Permission: `grc:risk_dashboard:view`

### 7.5 Business Rule Enforcement in Views

All business rules are enforced in the view layer, between `serializer.is_valid()` and `.save()`:

| View | Business Rule | Enforcement |
|---|---|---|
| `DeptRiskRegisterSubmitView` | Register must have ≥1 linked RiskAssessmentSheet | `if not register.entries.exists(): return error_response(...)` |
| `InstitutionalRiskRegisterCreateView` | Only RMQAM can create | Permission-level enforcement |
| `QMSAuditTeamAssignmentCreateView` | QA cannot audit own unit (E.2) | Compare `qa.org_unit_id != plan.auditee_unit_id` |
| `QualityAuditorAppointmentSubmitView` | QA must be certified (E.3) | `if not qa.is_certified: return error_response(...)` |
| `QMSAuditPlanCreateView` | Requires approved QMSAuditProgram | `if program.status != 'approved': return error_response(...)` |
| `RTAPQuarterlyUpdateCreateView` | One update per item per quarter | Caught by `unique_together` constraint |
| `NonConformanceStatusUpdateView` | Status transitions: raised→acknowledged→in_progress→closed | Validate `allowed_transitions[current_status]` |

---

## Phase 8 — URL Configuration

### 8.1 Create URL File

**File:** `apps/api/urls/risk.py`

All Risk Management URLs under the `/api/v1/grc/risk/` prefix:

```python
from django.urls import path
from apps.api.views import (
    risk_champion_views,
    risk_assessment_sheet_views,
    dept_risk_register_views,
    institutional_risk_register_views,
    risk_treatment_plan_views,
    rtap_item_views,
    quarterly_risk_report_views,
    quality_auditor_views,
    qms_audit_program_views,
    qms_audit_plan_views,
    qms_audit_checklist_views,
    qms_audit_report_views,
    non_conformance_views,
    risk_dashboard_views,
)

urlpatterns = [
    # ── Dashboard ──────────────────────────────────────────────────────────
    path("dashboard/", risk_dashboard_views.RiskDashboardView.as_view()),

    # ── Risk Champions ─────────────────────────────────────────────────────
    path("champions/", risk_champion_views.RiskChampionListCreateView.as_view()),
    path("champions/<uuid:pk>/", risk_champion_views.RiskChampionDetailView.as_view()),
    path("champions/<uuid:pk>/appointments/", risk_champion_views.RiskChampionAppointmentListCreateView.as_view()),
    path("champions/appointments/<uuid:pk>/", risk_champion_views.RiskChampionAppointmentDetailView.as_view()),
    path("champions/appointments/<uuid:pk>/workflow/start/",   risk_champion_views.RiskChampionAppointmentWorkflowStartView.as_view()),
    path("champions/appointments/<uuid:pk>/workflow/status/",  risk_champion_views.RiskChampionAppointmentWorkflowStatusView.as_view()),
    path("champions/appointments/<uuid:pk>/workflow/history/", risk_champion_views.RiskChampionAppointmentWorkflowHistoryView.as_view()),
    path("champions/appointments/<uuid:pk>/workflow/advance/", risk_champion_views.RiskChampionAppointmentWorkflowAdvanceView.as_view()),
    path("champions/appointments/<uuid:pk>/workflow/cancel/",  risk_champion_views.RiskChampionAppointmentWorkflowCancelView.as_view()),
    path("champions/appointments/<uuid:pk>/workflow/recall/",  risk_champion_views.RiskChampionAppointmentWorkflowRecallView.as_view()),

    # ── Risk Assessment Sheets ─────────────────────────────────────────────
    path("assessments/", risk_assessment_sheet_views.RiskAssessmentSheetListCreateView.as_view()),
    path("assessments/<uuid:pk>/", risk_assessment_sheet_views.RiskAssessmentSheetDetailView.as_view()),

    # ── Departmental Risk Registers ────────────────────────────────────────
    path("dept-registers/", dept_risk_register_views.DeptRiskRegisterListCreateView.as_view()),
    path("dept-registers/<uuid:pk>/", dept_risk_register_views.DeptRiskRegisterDetailView.as_view()),
    path("dept-registers/<uuid:pk>/entries/", dept_risk_register_views.DeptRegisterEntryListCreateView.as_view()),
    path("dept-registers/entries/<uuid:pk>/", dept_risk_register_views.DeptRegisterEntryDetailView.as_view()),
    path("dept-registers/<uuid:pk>/workflow/start/",   dept_risk_register_views.DeptRiskRegisterWorkflowStartView.as_view()),
    path("dept-registers/<uuid:pk>/workflow/status/",  dept_risk_register_views.DeptRiskRegisterWorkflowStatusView.as_view()),
    path("dept-registers/<uuid:pk>/workflow/history/", dept_risk_register_views.DeptRiskRegisterWorkflowHistoryView.as_view()),
    path("dept-registers/<uuid:pk>/workflow/advance/", dept_risk_register_views.DeptRiskRegisterWorkflowAdvanceView.as_view()),
    path("dept-registers/<uuid:pk>/workflow/cancel/",  dept_risk_register_views.DeptRiskRegisterWorkflowCancelView.as_view()),
    path("dept-registers/<uuid:pk>/workflow/recall/",  dept_risk_register_views.DeptRiskRegisterWorkflowRecallView.as_view()),

    # ── Institutional Risk Registers ───────────────────────────────────────
    path("institutional-registers/", institutional_risk_register_views.InstitutionalRiskRegisterListCreateView.as_view()),
    path("institutional-registers/<uuid:pk>/", institutional_risk_register_views.InstitutionalRiskRegisterDetailView.as_view()),
    path("institutional-registers/<uuid:pk>/entries/", institutional_risk_register_views.InstitutionalRiskEntryListCreateView.as_view()),
    path("institutional-registers/entries/<uuid:pk>/", institutional_risk_register_views.InstitutionalRiskEntryDetailView.as_view()),
    path("institutional-registers/<uuid:pk>/activity-reports/", institutional_risk_register_views.ActivityReportListCreateView.as_view()),
    path("institutional-registers/activity-reports/<uuid:pk>/", institutional_risk_register_views.ActivityReportDetailView.as_view()),
    path("institutional-registers/<uuid:pk>/workflow/start/",   institutional_risk_register_views.InstitutionalRiskRegisterWorkflowStartView.as_view()),
    path("institutional-registers/<uuid:pk>/workflow/status/",  institutional_risk_register_views.InstitutionalRiskRegisterWorkflowStatusView.as_view()),
    path("institutional-registers/<uuid:pk>/workflow/history/", institutional_risk_register_views.InstitutionalRiskRegisterWorkflowHistoryView.as_view()),
    path("institutional-registers/<uuid:pk>/workflow/advance/", institutional_risk_register_views.InstitutionalRiskRegisterWorkflowAdvanceView.as_view()),
    path("institutional-registers/<uuid:pk>/workflow/cancel/",  institutional_risk_register_views.InstitutionalRiskRegisterWorkflowCancelView.as_view()),
    path("institutional-registers/<uuid:pk>/workflow/recall/",  institutional_risk_register_views.InstitutionalRiskRegisterWorkflowRecallView.as_view()),

    # ── RTAP ───────────────────────────────────────────────────────────────
    path("rtap/", risk_treatment_plan_views.RTAPListCreateView.as_view()),
    path("rtap/<uuid:pk>/", risk_treatment_plan_views.RTAPDetailView.as_view()),
    path("rtap/<uuid:pk>/workflow/start/",   risk_treatment_plan_views.RTAPWorkflowStartView.as_view()),
    path("rtap/<uuid:pk>/workflow/status/",  risk_treatment_plan_views.RTAPWorkflowStatusView.as_view()),
    path("rtap/<uuid:pk>/workflow/history/", risk_treatment_plan_views.RTAPWorkflowHistoryView.as_view()),
    path("rtap/<uuid:pk>/workflow/advance/", risk_treatment_plan_views.RTAPWorkflowAdvanceView.as_view()),
    path("rtap/<uuid:pk>/workflow/cancel/",  risk_treatment_plan_views.RTAPWorkflowCancelView.as_view()),
    path("rtap/<uuid:pk>/workflow/recall/",  risk_treatment_plan_views.RTAPWorkflowRecallView.as_view()),

    # ── RTAP Items ─────────────────────────────────────────────────────────
    path("rtap-items/", rtap_item_views.RTAPItemListCreateView.as_view()),
    path("rtap-items/<uuid:pk>/", rtap_item_views.RTAPItemDetailView.as_view()),
    path("rtap-items/<uuid:pk>/quarterly-updates/", rtap_item_views.RTAPQuarterlyUpdateListCreateView.as_view()),
    path("rtap-items/quarterly-updates/<uuid:pk>/", rtap_item_views.RTAPQuarterlyUpdateDetailView.as_view()),

    # ── Quarterly Performance Reports ──────────────────────────────────────
    path("quarterly-reports/", quarterly_risk_report_views.QuarterlyReportListCreateView.as_view()),
    path("quarterly-reports/<uuid:pk>/", quarterly_risk_report_views.QuarterlyReportDetailView.as_view()),
    path("quarterly-reports/<uuid:pk>/workflow/start/",   quarterly_risk_report_views.QuarterlyReportWorkflowStartView.as_view()),
    path("quarterly-reports/<uuid:pk>/workflow/status/",  quarterly_risk_report_views.QuarterlyReportWorkflowStatusView.as_view()),
    path("quarterly-reports/<uuid:pk>/workflow/history/", quarterly_risk_report_views.QuarterlyReportWorkflowHistoryView.as_view()),
    path("quarterly-reports/<uuid:pk>/workflow/advance/", quarterly_risk_report_views.QuarterlyReportWorkflowAdvanceView.as_view()),
    path("quarterly-reports/<uuid:pk>/workflow/cancel/",  quarterly_risk_report_views.QuarterlyReportWorkflowCancelView.as_view()),
    path("quarterly-reports/<uuid:pk>/workflow/recall/",  quarterly_risk_report_views.QuarterlyReportWorkflowRecallView.as_view()),

    # ── Quality Auditors ───────────────────────────────────────────────────
    path("quality-auditors/", quality_auditor_views.QualityAuditorListCreateView.as_view()),
    path("quality-auditors/<uuid:pk>/", quality_auditor_views.QualityAuditorDetailView.as_view()),
    path("quality-auditors/<uuid:pk>/appointments/", quality_auditor_views.QualityAuditorAppointmentListCreateView.as_view()),
    path("quality-auditors/appointments/<uuid:pk>/", quality_auditor_views.QualityAuditorAppointmentDetailView.as_view()),
    path("quality-auditors/appointments/<uuid:pk>/workflow/start/",   quality_auditor_views.QAAppointmentWorkflowStartView.as_view()),
    path("quality-auditors/appointments/<uuid:pk>/workflow/status/",  quality_auditor_views.QAAppointmentWorkflowStatusView.as_view()),
    path("quality-auditors/appointments/<uuid:pk>/workflow/history/", quality_auditor_views.QAAppointmentWorkflowHistoryView.as_view()),
    path("quality-auditors/appointments/<uuid:pk>/workflow/advance/", quality_auditor_views.QAAppointmentWorkflowAdvanceView.as_view()),
    path("quality-auditors/appointments/<uuid:pk>/workflow/cancel/",  quality_auditor_views.QAAppointmentWorkflowCancelView.as_view()),
    path("quality-auditors/appointments/<uuid:pk>/workflow/recall/",  quality_auditor_views.QAAppointmentWorkflowRecallView.as_view()),

    # ── QMS Audit Programs ─────────────────────────────────────────────────
    path("qms-programs/", qms_audit_program_views.QMSAuditProgramListCreateView.as_view()),
    path("qms-programs/<uuid:pk>/", qms_audit_program_views.QMSAuditProgramDetailView.as_view()),
    path("qms-programs/<uuid:pk>/workflow/start/",   qms_audit_program_views.QMSAuditProgramWorkflowStartView.as_view()),
    path("qms-programs/<uuid:pk>/workflow/status/",  qms_audit_program_views.QMSAuditProgramWorkflowStatusView.as_view()),
    path("qms-programs/<uuid:pk>/workflow/history/", qms_audit_program_views.QMSAuditProgramWorkflowHistoryView.as_view()),
    path("qms-programs/<uuid:pk>/workflow/advance/", qms_audit_program_views.QMSAuditProgramWorkflowAdvanceView.as_view()),
    path("qms-programs/<uuid:pk>/workflow/cancel/",  qms_audit_program_views.QMSAuditProgramWorkflowCancelView.as_view()),
    path("qms-programs/<uuid:pk>/workflow/recall/",  qms_audit_program_views.QMSAuditProgramWorkflowRecallView.as_view()),

    # ── QMS Audit Plans ────────────────────────────────────────────────────
    path("qms-plans/", qms_audit_plan_views.QMSAuditPlanListCreateView.as_view()),
    path("qms-plans/<uuid:pk>/", qms_audit_plan_views.QMSAuditPlanDetailView.as_view()),
    path("qms-plans/<uuid:pk>/team/", qms_audit_plan_views.QMSAuditTeamAssignmentListCreateView.as_view()),
    path("qms-plans/team/<uuid:pk>/", qms_audit_plan_views.QMSAuditTeamAssignmentDetailView.as_view()),
    path("qms-plans/<uuid:pk>/workflow/start/",   qms_audit_plan_views.QMSAuditPlanWorkflowStartView.as_view()),
    path("qms-plans/<uuid:pk>/workflow/status/",  qms_audit_plan_views.QMSAuditPlanWorkflowStatusView.as_view()),
    path("qms-plans/<uuid:pk>/workflow/history/", qms_audit_plan_views.QMSAuditPlanWorkflowHistoryView.as_view()),
    path("qms-plans/<uuid:pk>/workflow/advance/", qms_audit_plan_views.QMSAuditPlanWorkflowAdvanceView.as_view()),
    path("qms-plans/<uuid:pk>/workflow/cancel/",  qms_audit_plan_views.QMSAuditPlanWorkflowCancelView.as_view()),
    path("qms-plans/<uuid:pk>/workflow/recall/",  qms_audit_plan_views.QMSAuditPlanWorkflowRecallView.as_view()),

    # ── QMS Audit Checklists ───────────────────────────────────────────────
    path("qms-checklists/", qms_audit_checklist_views.AuditChecklistListCreateView.as_view()),
    path("qms-checklists/<uuid:pk>/", qms_audit_checklist_views.AuditChecklistDetailView.as_view()),

    # ── QMS Audit Reports ──────────────────────────────────────────────────
    path("qms-reports/", qms_audit_report_views.QMSAuditReportListCreateView.as_view()),
    path("qms-reports/<uuid:pk>/", qms_audit_report_views.QMSAuditReportDetailView.as_view()),
    path("qms-reports/<uuid:pk>/sign-tl/", qms_audit_report_views.QMSAuditReportSignTLView.as_view()),
    path("qms-reports/<uuid:pk>/sign-auditee/", qms_audit_report_views.QMSAuditReportSignAuditeeView.as_view()),

    # ── Non-Conformances ───────────────────────────────────────────────────
    path("non-conformances/", non_conformance_views.NonConformanceListCreateView.as_view()),
    path("non-conformances/<uuid:pk>/", non_conformance_views.NonConformanceDetailView.as_view()),
]
```

### 8.2 Mount in Root URL Router

**File:** `apps/api/urls/urls.py` (extend existing)

Add the risk management URL module:

```python
from apps.api.urls import risk

urlpatterns = [
    # ... existing audit patterns ...
    path("api/v1/grc/risk/", include(risk)),
]
```

---

## Phase 9 — Domain Events & Kafka

### 9.1 Define Event Type Constants

**File:** `shared/constants/event_types.py` (extend existing)

```python
# ── Risk Management Events ─────────────────────────────────────────────────

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

QA_EVENTS = {
    'APPOINTED': 'grc.risk.qa.appointed',
}

QMS_AUDIT_EVENTS = {
    'NC_RAISED': 'grc.qms.audit.nc.raised',
    'REPORT_SIGNED': 'grc.qms.audit.report.signed',
}
```

Add all new dictionaries to the `ALL_GRC_EVENT_TYPES` aggregation dict.

### 9.2 Create Event Dataclasses

**File:** `apps/core/events/risk_events.py` (new)

```python
from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class RiskChampionAppointedEvent:
    champion_id: str
    user_id: str
    org_unit_id: str

@dataclass
class RiskRegisterApprovedEvent:
    register_id: str
    register_type: str   # 'departmental' or 'institutional'
    fiscal_year_code: str

# ... similar dataclasses for all event types ...
```

### 9.3 Add Messaging Service Methods

**File:** `apps/infrastructure/services/messaging_service.py` (extend existing)

Add new publish methods following the existing pattern:

```python
def publish_risk_champion_event(self, event_type, champion_id, additional_data=None):
    self._publish_event('grc-service.risk.events', event_type, {
        'champion_id': str(champion_id),
        **(additional_data or {}),
    })

def publish_risk_register_event(self, event_type, register_id, additional_data=None):
    ...

def publish_rtap_event(self, event_type, rtap_id, additional_data=None):
    ...

def publish_quarterly_report_event(self, event_type, report_id, additional_data=None):
    ...

def publish_qms_audit_event(self, event_type, audit_id, additional_data=None):
    ...
```

### 9.4 Integrate Event Publishing in Views

Events are published in views after successful save operations, wrapped in `try/except`:

```python
# In the POST handler, after entity.save():
try:
    messaging_service.publish_risk_register_event(
        event_type=RISK_REGISTER_EVENTS['DEPARTMENTAL_APPROVED'],
        register_id=entity.id,
        additional_data={'approved_by': str(request.user_id)},
    )
except Exception as event_error:
    logger.error("Error publishing risk register event: %s", event_error)
```

---

## Phase 10 — Celery Tasks

### 10.1 Create Monitoring Task

**File:** `apps/core/tasks/risk_monitoring_deadlines.py` (new)

```python
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

@shared_task(name='grc.check_risk_monitoring_deadlines')
def check_risk_monitoring_deadlines():
    """
    Daily task. Responsibilities:
    1. Flag RTAPItems past target_date that are not 'completed'
    2. Send RC reminder when quarterly submission deadline approaches (3 days)
    3. Escalate to RMQAM when RC has not submitted within 7 days of reminder
    """
    _check_overdue_rtap_items()
    _send_quarterly_submission_reminders()
    _escalate_non_responsive_rcs()

def _check_overdue_rtap_items():
    from apps.core.models.risk_entities import RTAPItem
    overdue_items = RTAPItem.objects.filter(
        is_active=True,
        status__in=['not_started', 'in_progress'],
        target_date__lt=timezone.now().date(),
    )
    for item in overdue_items:
        # Publish notification via NotificationPublisher
        ...

def _send_quarterly_submission_reminders():
    from apps.core.models.lookups import Quarter
    current_quarter = Quarter.get_current_quarter()
    if not current_quarter:
        return
    days_until_end = (current_quarter.end_date - timezone.now().date()).days
    if days_until_end <= 3:
        # Find RCs who have not submitted updates for active RTAPItems
        ...

def _escalate_non_responsive_rcs():
    # Find RCs with pending updates older than 7 days past reminder
    ...
```

### 10.2 Register in Celery Beat

**File:** `config/celery.py` (extend existing)

```python
CELERY_BEAT_SCHEDULE = {
    # ... existing tasks ...

    'grc.check_risk_monitoring_deadlines': {
        'task': 'grc.check_risk_monitoring_deadlines',
        'schedule': crontab(hour=7, minute=0),  # daily at 7:00 AM
    },
}
```

---

## Phase 11 — PDF Generation

### 11.1 Create HTML Templates

**Directory:** `templates/grc/risk/` (new)

Create 5 WeasyPrint HTML templates:

| # | File | Document |
|---|---|---|
| 1 | `appointment_letter.html` | RC/QA formal appointment letter |
| 2 | `institutional_risk_register.html` | IRR tabular PDF export |
| 3 | `risk_treatment_action_plan.html` | RTAP tabular PDF export |
| 4 | `quarterly_performance_report.html` | QPR with metrics + narrative |
| 5 | `qms_audit_report.html` | Audit report with NC table |

Each template extends a base layout with FCC letterhead, signature blocks, etc.

### 11.2 Add Generator Functions

**File:** `apps/core/utils/pdf_generators.py` (extend existing)

Add 5 new functions:

```python
def generate_appointment_letter_pdf(appointment):
    """Generate RC or QA appointment letter PDF."""
    from django.template.loader import render_to_string
    from weasyprint import HTML

    context = {
        'appointment': appointment,
        'champion_or_auditor': appointment.risk_champion if hasattr(appointment, 'risk_champion') else appointment.quality_auditor,
    }
    html_string = render_to_string('grc/risk/appointment_letter.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    return pdf_bytes

def generate_risk_register_pdf(register):
    """Generate Institutional Risk Register PDF."""
    ...

def generate_rtap_pdf(rtap):
    """Generate RTAP PDF."""
    ...

def generate_quarterly_report_pdf(report):
    """Generate Quarterly Performance Report PDF."""
    ...

def generate_qms_audit_report_pdf(audit_report):
    """Generate QMS Audit Report PDF."""
    ...
```

### 11.3 Integrate PDF Generation with DRS Upload

In the relevant workflow completion handlers (service layer or view layer), after the terminal workflow stage completes:

```python
# Example: after DG signs appointment letter
from apps.core.utils.pdf_generators import generate_appointment_letter_pdf
from apps.infrastructure.external.document_service_client import DocumentServiceClient

pdf_bytes = generate_appointment_letter_pdf(appointment)
drs_client = DocumentServiceClient()
result = drs_client.upload_document(
    file_bytes=pdf_bytes,
    filename=f"appointment_letter_{appointment.id}.pdf",
    content_type='application/pdf',
    metadata={'entity_type': 'risk_champion_appointment', 'entity_id': str(appointment.id)},
)
if result:
    appointment.document_id = result['document_id']
    appointment.stamped_document_url = result.get('stamped_url', '')
    appointment.save(update_fields=['document_id', 'stamped_document_url'])
```

---

## Phase 12 — Testing & Validation

### 12.1 Test File Structure

```
tests/
├── api/
│   ├── test_risk_champion_views.py
│   ├── test_risk_assessment_views.py
│   ├── test_dept_register_views.py
│   ├── test_institutional_register_views.py
│   ├── test_rtap_views.py
│   ├── test_quarterly_report_views.py
│   ├── test_quality_auditor_views.py
│   ├── test_qms_audit_program_views.py
│   ├── test_qms_audit_plan_views.py
│   ├── test_qms_audit_report_views.py
│   ├── test_non_conformance_views.py
│   └── test_risk_dashboard_views.py
├── models/
│   ├── test_risk_entities.py
│   └── test_risk_lookups.py
├── services/
│   ├── test_risk_champion_service.py
│   ├── test_dept_register_service.py
│   ├── test_institutional_register_service.py
│   ├── test_rtap_service.py
│   ├── test_quarterly_report_service.py
│   ├── test_quality_auditor_service.py
│   ├── test_qms_audit_program_service.py
│   └── test_qms_audit_plan_service.py
└── conftest.py                    # shared fixtures, mock JWT auth
```

### 12.2 Unit Tests — Models

**File:** `tests/models/test_risk_entities.py`

For each model:
- [ ] Test model creation with valid data
- [ ] Test `UniqueConstraint` enforcement (e.g., duplicate active RC for same org unit)
- [ ] Test `save()` auto-computation on `RiskAssessmentSheet`
- [ ] Test `clean()` validation on `QMSAuditPlan` (10-day notification rule)
- [ ] Test soft delete (`is_active=False` does not destroy record)
- [ ] Test WorkflowMixin methods (`start_workflow`, `update_workflow_stage`, `complete_workflow`, `cancel_workflow`, `clear_workflow`)
- [ ] Test `get_workflow_context()` and `get_workflow_metadata()` return correct dicts

### 12.3 Unit Tests — Serializers

For each serializer:
- [ ] Test FK dual-field pattern: write with UUID, read returns nested object
- [ ] Test auto-computed fields are `read_only`
- [ ] Test required vs optional fields
- [ ] Test validation errors for missing required fields

### 12.4 Unit Tests — Views (API Tests)

Use DRF's `APITestCase` with mock JWT authentication:

```python
# tests/conftest.py
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(api_client):
    """Client with mocked JWT auth carrying full risk management permissions."""
    with patch('apps.core.permission_middleware.JWTPermissionMiddleware') as mock_middleware:
        api_client.credentials(HTTP_AUTHORIZATION='Bearer test-token')
        # Set mock request attributes
        api_client.handler._force_user = MagicMock()
        api_client.handler._force_user.id = 'test-user-uuid'
        api_client.handler._force_user.is_authenticated = True
    return api_client
```

For each view:
- [ ] Test `GET /list/` returns paginated response with correct envelope
- [ ] Test `POST /` creates record and returns 201
- [ ] Test `GET /<pk>/` returns detail with nested FK objects
- [ ] Test `PUT /<pk>/` updates record
- [ ] Test `DELETE /<pk>/` soft-deletes (sets `is_active=False`)
- [ ] Test permission enforcement: unauthenticated → 401, missing permission → 403
- [ ] Test business rule validation returns correct error codes

### 12.5 Integration Tests — Workflow

For each workflow-enabled entity:
- [ ] Test `POST /submit/` creates WO plan (mock `OrchestrationClient`)
- [ ] Test `GET /workflow-status/` returns plan status
- [ ] Test `POST /workflow-action/` advances stage
- [ ] Test `POST /cancel-workflow/` cancels plan
- [ ] Test double-submit guard (second submit returns existing plan)

### 12.6 Run Tests

```bash
cd /home/simons/Coding/FIMS/grc-service
pytest tests/ -v --tb=short
```

---

## Phase 13 — Data Seeding & Smoke Testing

### 13.1 Create Sample Data Management Command

**File:** `apps/core/management/commands/seed_risk_sample_data.py`

Populates the database with realistic test records:

- 4 Risk Champions (one per sample directorate)
- 4 Risk Champion Appointments (one per RC)
- 2 Quality Auditors
- 10 Risk Assessment Sheets (across champions)
- 2 Departmental Risk Registers (with entries)
- 1 Institutional Risk Register (with threshold-filtered entries)
- 1 RTAP (with items)
- 2 RTAPQuarterlyUpdates
- 1 QuarterlyPerformanceReport
- 1 QMSAuditProgram
- 1 QMSAuditPlan (with team assignments)
- 3 AuditChecklists
- 1 QMSAuditReport
- 2 NonConformances

Run:
```bash
python manage.py seed_risk_sample_data
```

### 13.2 Smoke Test Checklist

After seeding:

- [ ] `GET /api/v1/grc/risk/champions/` — returns paginated list
- [ ] `GET /api/v1/grc/risk/assessments/` — returns paginated list with nested lookups
- [ ] `POST /api/v1/grc/risk/assessments/` with likelihood + impact → inherent score auto-computed
- [ ] `GET /api/v1/grc/risk/dept-registers/<id>/entries/` — returns entries with nested risk sheet
- [ ] `POST /api/v1/grc/risk/dept-registers/<id>/submit/` — creates WO plan
- [ ] `GET /api/v1/grc/risk/dashboard/` — returns aggregate stats
- [ ] Verify all 20 `grc_risk_*` tables exist in DB
- [ ] Verify lookup tables have seeded data

---

## Implementation Order Summary

This is the recommended implementation sequence. Each phase depends on the preceding phases.

| Phase | What | Files Created/Modified | Dependencies |
|:---:|---|---|---|
| **1** | Setup & environment | — | Running docker stack |
| **2** | Models (20 models) | `risk_entities.py`, `__init__.py` | Phase 1 |
| **3** | Lookup tables (6 new) | `lookups.py` (extend), `seed_risk_lookups.py` | Phase 2 |
| **4** | Workflow integration | `workflows.yaml` (extend), `workflow_entity_paths.py` (extend), 8× service files | Phase 2 |
| **5** | Serializers | `risk_serializers.py`, `lookup_serializers.py` (extend) | Phase 2, 3 |
| **6** | Permission classes | `grc-service.json` (extend), `permissions_jwt.py` (extend) | — |
| **7** | Views (14 files, ~80+ view classes) | 14× view files | Phase 4, 5, 6 |
| **8** | URL configuration | `risk.py`, `urls.py` (extend) | Phase 7 |
| **9** | Domain events & Kafka | `event_types.py` (extend), `risk_events.py`, `messaging_service.py` (extend) | Phase 7 |
| **10** | Celery tasks | `risk_monitoring_deadlines.py`, `celery.py` (extend) | Phase 2 |
| **11** | PDF generation | 5× HTML templates, `pdf_generators.py` (extend) | Phase 2 |
| **12** | Testing | 20+ test files | Phase 1–11 |
| **13** | Data seeding & smoke testing | `seed_risk_sample_data.py` | Phase 1–11 |

**Total new files:** ~40
**Total extended files:** ~10
**Total models:** 20 business + 6 lookup = 26
**Total service classes:** 8
**Total view classes:** ~80+
**Total permission classes:** 24
**Total workflow templates:** 8
**Total API endpoints:** ~85+

---

*This implementation plan is ready for direct execution. Each step references the specific design document section and follows the exact patterns established by the Internal Audit module.*
