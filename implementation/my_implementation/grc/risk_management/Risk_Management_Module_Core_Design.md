# Risk Management Module — Core Design

**Service:** `grc-service`
**Module:** Risk Management (RMQAU — Risk Management and Quality Assurance Unit)
**Document purpose:** Sections 3–6 of the full module design — Base Models & Mixins, Data Models & Relationships, Lookup Tables, and Workflow Integration.
**Prerequisite reading:** `Risk_Management_Module_Architecture_Overview.md` (§1 Architecture, §2 Directory Structure) and `Internal_Audit_Backend_Patterns.md`.

---

## Table of Contents

3. [Base Models & Mixins](#3-base-models--mixins)
   - 3.1 [BaseModel](#31-basemodel)
   - 3.2 [TimestampedModel](#32-timestampedmodel)
   - 3.3 [StatusMixin](#33-statusmixin)
   - 3.4 [WorkflowMixin](#34-workflowmixin)
   - 3.5 [Composition Rules](#35-composition-rules)
   - 3.6 [Pagination Helpers](#36-pagination-helpers)
4. [Data Models & Relationships](#4-data-models--relationships)
   - 4.1 [Entity Hierarchy](#41-entity-hierarchy)
   - 4.2 [Model Reference Table](#42-model-reference-table)
   - 4.3 [Group 1 — Risk Champion & QA Appointment](#43-group-1--risk-champion--qa-appointment)
   - 4.4 [Group 2 — Risk Assessment & Departmental Register](#44-group-2--risk-assessment--departmental-register)
   - 4.5 [Group 3 — Institutional Register & RTAP](#45-group-3--institutional-register--rtap)
   - 4.6 [Group 4 — Quarterly Reporting](#46-group-4--quarterly-reporting)
   - 4.7 [Group 5 — QMS Audit](#47-group-5--qms-audit)
   - 4.8 [Cross-Cutting Design Decisions](#48-cross-cutting-design-decisions)
5. [Lookup Tables](#5-lookup-tables)
   - 5.1 [Reused Lookups (Internal Audit)](#51-reused-lookups-internal-audit)
   - 5.2 [New Lookup Tables](#52-new-lookup-tables)
   - 5.3 [Lookup Table Quick Reference](#53-lookup-table-quick-reference)
6. [Workflow Integration](#6-workflow-integration)
   - 6.1 [Workflow Template Definitions (YAML)](#61-workflow-template-definitions-yaml)
   - 6.2 [WorkflowMixin Context Overrides](#62-workflowmixin-context-overrides)
   - 6.3 [Standard Workflow Endpoints (per entity)](#63-standard-workflow-endpoints-per-entity)
   - 6.4 [Service Class Pattern](#64-service-class-pattern)

---

## 3. Base Models & Mixins

All Risk Management models inherit from the shared base classes in `apps/core/models/base.py`. These are never modified for a specific module — they are used as-is.

### 3.1 BaseModel

```python
# apps/core/models/base.py

class BaseModel(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

| Field | Type | Notes |
|-------|------|-------|
| `id` | `UUIDField` | PK, auto-generated `uuid4`, not editable by clients |
| `created_at` | `DateTimeField` | `auto_now_add=True`, indexed for ordered queries |
| `updated_at` | `DateTimeField` | `auto_now=True`, updated on every `save()` |

### 3.2 TimestampedModel

```python
class TimestampedModel(BaseModel):
    created_by  = models.UUIDField(
        help_text="User ID from IAM service who created this record"
    )
    modified_by = models.UUIDField(
        null=True, blank=True,
        help_text="User ID from IAM service who last modified this record"
    )

    class Meta:
        abstract = True
```

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `created_by` | `UUIDField` | No | Set from `request.user_id` on creation; never from request body |
| `modified_by` | `UUIDField` | Yes | Set from `request.user_id` on every update; `null` if untouched |

**Rule: no Django FK to a User model. All user references in Risk Management are raw UUID fields.** Names and emails are resolved at read-time via `IAMClient.get_user_profile(user_id)` and never persisted.

### 3.3 StatusMixin

```python
class StatusMixin(models.Model):
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this record is active and available for use"
    )

    class Meta:
        abstract = True
```

- Soft-delete only — records are never deleted with `DELETE` SQL.
- Deactivating a record (`is_active=False`) removes it from default queryset filters.
- Service methods apply `.filter(is_active=True)` on all read operations unless explicitly retrieving history.
- Business rule E.11 (single active RC/IRR/RTAP per scope) is enforced via `UniqueConstraint` with `condition=Q(is_active=True)`.

### 3.4 WorkflowMixin

Full implementation reference — all 5 fields, 3 properties, 6 mutating methods, 3 override hooks.

```python
class WorkflowMixin(models.Model):
    # ── Fields ─────────────────────────────────────────────────────────────
    workflow_plan_id      = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID of the workflow plan in Work Orchestration Service"
    )
    workflow_stage        = models.CharField(
        max_length=255, blank=True, default='',
        help_text="Current stage name in Work Orchestration Service"
    )
    workflow_stage_id     = models.UUIDField(
        null=True, blank=True,
        help_text="UUID of the current stage record in WO"
    )
    workflow_started_at   = models.DateTimeField(
        null=True, blank=True,
        help_text="When the workflow plan was first created"
    )
    workflow_completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the workflow reached a terminal state"
    )

    class Meta:
        abstract = True

    # ── Properties ─────────────────────────────────────────────────────────
    @property
    def has_workflow(self) -> bool:
        """True if a WO plan has ever been created for this record."""
        return self.workflow_plan_id is not None

    @property
    def has_active_workflow(self) -> bool:
        """True if a WO plan exists and has not yet been completed."""
        return self.workflow_plan_id is not None and self.workflow_completed_at is None

    @property
    def is_workflow_completed(self) -> bool:
        """True if the workflow has reached its terminal state."""
        return self.workflow_plan_id is not None and self.workflow_completed_at is not None

    # ── Mutating Methods ────────────────────────────────────────────────────
    def start_workflow(self, plan_id: uuid.UUID, initial_stage: str = '', stage_id=None):
        """
        Called after WO returns a plan_id. Sets all 5 workflow fields and
        stamps workflow_started_at = timezone.now(). Saves these fields only.
        """

    def update_workflow_stage(self, stage_name: str, stage_id=None):
        """
        Called on each WO stage-advance webhook. Updates workflow_stage
        and workflow_stage_id. Saves these fields only.
        """

    def complete_workflow(self):
        """
        Called when WO reaches the terminal state. Sets
        workflow_completed_at = timezone.now(). Saves this field only.
        """

    def cancel_workflow(self):
        """
        Called when workflow is aborted. Sets workflow_completed_at = now()
        (so is_workflow_completed becomes True — prevents restart).
        """

    def clear_workflow(self):
        """
        Resets all 5 workflow fields to defaults (None / ''). Used when
        a record is recalled for rework before re-submission.
        """

    # ── Override Hooks ──────────────────────────────────────────────────────
    def get_workflow_context(self) -> dict:
        """
        Returns context sent to WO when creating the plan.
        Base returns: {'entity_type': ..., 'entity_id': str(self.id)}
        Each WorkflowMixin model MUST override this with full context.
        """

    def get_workflow_metadata(self) -> dict:
        """
        Returns metadata attached to the WO plan record.
        Base returns: {'entity_type', 'entity_id', 'entity_repr'}
        Each WorkflowMixin model MUST override this with meaningful repr.
        """

    def log_workflow_action(self, action: str, actor_id, notes: str = ''):
        """
        Called at each workflow transition to write an audit entry.
        Override to persist to a module-specific WorkflowAuditLog model.
        """
```

### 3.5 Composition Rules

The composition pattern is identical to the Internal Audit module — apply mixins left-to-right:

```python
# Entity that participates in a WO workflow
class MyEntity(TimestampedModel, StatusMixin, WorkflowMixin):
    ...

# Entity that does NOT have a WO workflow
class MyEntity(TimestampedModel, StatusMixin):
    ...
```

**Rules:**
1. All Risk Management models inherit at minimum from `TimestampedModel` and `StatusMixin`.
2. `WorkflowMixin` is added **only** to entities that create a plan in the Work Orchestration Service.
3. `WorkflowMixin` must always be listed **after** `StatusMixin` in the MRO.
4. Never add `WorkflowMixin` to a lookup table model.

**Entities that get WorkflowMixin (8 total):**

| Model | Workflow Template |
|-------|------------------|
| `RiskChampionAppointment` | `grc.risk_champion_appointment` |
| `DepartmentalRiskRegister` | `grc.dept_risk_register_approval` |
| `InstitutionalRiskRegister` | `grc.institutional_risk_register_approval` |
| `RiskTreatmentActionPlan` | `grc.rtap_approval` |
| `QuarterlyPerformanceReport` | `grc.quarterly_risk_report_approval` |
| `QualityAuditorAppointment` | `grc.qa_appointment` |
| `QMSAuditProgram` | `grc.qms_audit_program_approval` |
| `QMSAuditPlan` | `grc.qms_audit_plan_approval` |

### 3.6 Pagination Helpers

Risk Management views use the shared pagination utilities from `apps/api/utils/pagination.py` — no custom pagination class required.

```python
from apps.api.utils.pagination import paginate_queryset, get_ordering_param

class RiskListView(APIView):
    def get(self, request):
        qs = RiskAssessmentSheet.objects.filter(is_active=True)

        # Ordering: ?ordering=created_at (default) or ?ordering=-inherent_risk_score
        ordering = get_ordering_param(
            request,
            allowed_fields=['created_at', 'updated_at', 'inherent_risk_score'],
            default='-created_at'
        )
        qs = qs.order_by(ordering)

        # Page: ?page=1&page_size=20 (default page_size=20, max=100)
        page_data = paginate_queryset(qs, request, RiskAssessmentSheetSerializer)
        return Response(page_data)
```

---

## 4. Data Models & Relationships

### 4.1 Entity Hierarchy

```
Risk Champion & QA Appointment
├── RiskChampion                       ← appointed person per Directorate/Unit/Zone
│   └── RiskChampionAppointment ✦     ← appointment letter workflow
└── QualityAuditor                    ← certified internal QMS auditor
    └── QualityAuditorAppointment ✦   ← appointment letter workflow

Risk Assessment & Departmental Register
├── RiskAssessmentSheet               ← one risk per RC; scored on save()
└── DepartmentalRiskRegister ✦        ← consolidated register per Directorate/Unit/Zone + FiscalYear
    └── DeptRegisterEntry             ← links DepartmentalRiskRegister ↔ RiskAssessmentSheet

Institutional Register & RTAP
├── InstitutionalRiskRegister ✦       ← org-wide; one active per FiscalYear
│   ├── InstitutionalRiskEntry        ← threshold-filtered entries from dept registers
│   └── ActivityReport               ← quarterly RC activity log
└── RiskTreatmentActionPlan ✦         ← 1:1 with InstitutionalRiskRegister; one active per year
    └── RTAPItem                      ← one control per InstitutionalRiskEntry
        └── RTAPQuarterlyUpdate       ← status update per Quarter

Quarterly Reporting
└── QuarterlyPerformanceReport ✦      ← compiled quarterly report; unique per [FiscalYear, Quarter]

QMS Audit
└── QMSAuditProgram ✦                 ← annual audit scope per FiscalYear
    └── QMSAuditPlan ✦                ← plan per audit (branch/dept); team assignment
        ├── QMSAuditTeamAssignment    ← join table: QMSAuditPlan ↔ QA UUID
        ├── AuditChecklist            ← one entry per ISOClause per QA
        └── QMSAuditReport            ← signed audit report; 1:1 with QMSAuditPlan
            └── NonConformance        ← NCs raised in the audit report

✦ = has WorkflowMixin
```

### 4.2 Model Reference Table

| # | Model | `db_table` | WorkflowMixin | Module File |
|---|-------|-----------|:---:|---------|
| 1 | `RiskChampion` | `grc_risk_champion` | — | `risk_champion.py` |
| 2 | `RiskChampionAppointment` | `grc_risk_champion_appointment` | ✓ | `risk_champion.py` |
| 3 | `QualityAuditor` | `grc_risk_quality_auditor` | — | `quality_auditor.py` |
| 4 | `QualityAuditorAppointment` | `grc_risk_qa_appointment` | ✓ | `quality_auditor.py` |
| 5 | `RiskAssessmentSheet` | `grc_risk_assessment_sheet` | — | `risk_assessment.py` |
| 6 | `DepartmentalRiskRegister` | `grc_risk_dept_register` | ✓ | `risk_register.py` |
| 7 | `DeptRegisterEntry` | `grc_risk_dept_register_entry` | — | `risk_register.py` |
| 8 | `InstitutionalRiskRegister` | `grc_risk_inst_register` | ✓ | `risk_register.py` |
| 9 | `InstitutionalRiskEntry` | `grc_risk_inst_register_entry` | — | `risk_register.py` |
| 10 | `RiskTreatmentActionPlan` | `grc_risk_rtap` | ✓ | `rtap.py` |
| 11 | `RTAPItem` | `grc_risk_rtap_item` | — | `rtap.py` |
| 12 | `RTAPQuarterlyUpdate` | `grc_risk_rtap_quarterly_update` | — | `rtap.py` |
| 13 | `QuarterlyPerformanceReport` | `grc_risk_quarterly_report` | ✓ | `reporting.py` |
| 14 | `ActivityReport` | `grc_risk_activity_report` | — | `reporting.py` |
| 15 | `QMSAuditProgram` | `grc_risk_qms_program` | ✓ | `qms_audit.py` |
| 16 | `QMSAuditPlan` | `grc_risk_qms_plan` | ✓ | `qms_audit.py` |
| 17 | `QMSAuditTeamAssignment` | `grc_risk_qms_team_assignment` | — | `qms_audit.py` |
| 18 | `AuditChecklist` | `grc_risk_qms_checklist` | — | `qms_audit.py` |
| 19 | `QMSAuditReport` | `grc_risk_qms_report` | — | `qms_audit.py` |
| 20 | `NonConformance` | `grc_risk_nonconformance` | — | `qms_audit.py` |

---

### 4.3 Group 1 — Risk Champion & QA Appointment

#### RiskChampion

```python
class RiskChampion(TimestampedModel, StatusMixin):
    """
    Represents an appointed Risk Champion. One active RC is allowed per
    Directorate/Unit/Zone at any time (enforced by partial UniqueConstraint).
    """
    # Org unit reference — UUID only (from Corporate Service)
    org_unit_id   = models.UUIDField(db_index=True, help_text="Directorate / Unit / Zone UUID from Corporate Service")
    org_unit_type = models.CharField(
        max_length=50,
        choices=[('directorate', 'Directorate'), ('unit', 'Unit'), ('zone', 'Zone')],
        help_text="Discriminator for the org unit type"
    )
    # Person reference — UUID only (from IAM Service)
    user_id       = models.UUIDField(db_index=True, help_text="IAM user UUID of the Risk Champion")
    nominated_by  = models.UUIDField(help_text="Head who nominated this RC (IAM user UUID)")
    # Term
    term_start    = models.DateField()
    term_end      = models.DateField(null=True, blank=True, help_text="Null = term end date not yet set")
    notes         = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_risk_champion'
        ordering = ['-created_at']
        constraints = [
            # Business Rule E.1/E.11: only one active RC per org unit
            models.UniqueConstraint(
                fields=['org_unit_id', 'org_unit_type'],
                condition=models.Q(is_active=True),
                name='unique_active_rc_per_org_unit'
            )
        ]
```

#### RiskChampionAppointment

```python
class RiskChampionAppointment(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Appointment letter workflow record for a Risk Champion. The appointment
    letter PDF is stored in DRS; this record carries only references + workflow state.
    """
    risk_champion    = models.ForeignKey(RiskChampion, on_delete=models.CASCADE,
                                         related_name='appointments')
    appointment_date = models.DateField()
    # DRS integration: dual reference pattern
    document_id          = models.UUIDField(null=True, blank=True,
                               help_text="Document UUID in Document Records Service")
    stamped_document_url = models.URLField(blank=True, default='',
                               help_text="Externally accessible URL of the signed/stamped letter from DRS")
    remarks          = models.TextField(blank=True)
    # Status state machine (local, complements WO stage)
    STATUS_DRAFT      = 'draft'
    STATUS_SUBMITTED  = 'submitted'
    STATUS_APPROVED   = 'approved'
    STATUS_REJECTED   = 'rejected'
    STATUS_SIGNED     = 'signed'
    STATUS_CHOICES    = [
        (STATUS_DRAFT,     'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED,  'Approved'),
        (STATUS_REJECTED,  'Rejected'),
        (STATUS_SIGNED,    'Signed'),
    ]
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)

    class Meta:
        db_table = 'grc_risk_champion_appointment'
        ordering = ['-created_at']
```

**Status state machine:**
```
draft → submitted → approved → signed
              ↘ rejected → draft (rework cycle, no limit)
```

---

#### QualityAuditor

```python
class QualityAuditor(TimestampedModel, StatusMixin):
    """
    A person qualified as a Quality Auditor. Records exam scores and
    certification status. Business Rule E.3: ≥75% exam score required, max 2 attempts.
    """
    user_id         = models.UUIDField(db_index=True, help_text="IAM user UUID of the Quality Auditor")
    nominated_by    = models.UUIDField(help_text="Head who nominated this QA (IAM user UUID)")
    org_unit_id     = models.UUIDField(db_index=True, help_text="QA's home unit UUID")
    org_unit_type   = models.CharField(max_length=50,
                          choices=[('directorate', 'Directorate'), ('unit', 'Unit'), ('zone', 'Zone')])
    # Certification
    exam_attempt    = models.IntegerField(default=0, help_text="Number of exam attempts (max 2 per Rule E.3)")
    exam_score      = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                          help_text="Latest exam score as percentage")
    is_certified    = models.BooleanField(default=False, db_index=True,
                          help_text="True when exam_score ≥ 75%")
    certification_date = models.DateField(null=True, blank=True)
    term_start      = models.DateField(null=True, blank=True)
    term_end        = models.DateField(null=True, blank=True)
    notes           = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_risk_quality_auditor'
        ordering = ['-created_at']
```

#### QualityAuditorAppointment

Mirrors `RiskChampionAppointment` exactly — same dual-document pattern, same status state machine, different workflow template.

```python
class QualityAuditorAppointment(TimestampedModel, StatusMixin, WorkflowMixin):
    quality_auditor      = models.ForeignKey(QualityAuditor, on_delete=models.CASCADE,
                                              related_name='appointments')
    appointment_date     = models.DateField()
    document_id          = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    remarks              = models.TextField(blank=True)
    status               = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft',
                               db_index=True)

    class Meta:
        db_table = 'grc_risk_qa_appointment'
        ordering = ['-created_at']
```

**QA conflict rule (E.2):** A QA cannot be assigned to audit their own org_unit. Enforced in service layer, not at DB level.

---

### 4.4 Group 2 — Risk Assessment & Departmental Register

#### RiskAssessmentSheet

```python
class RiskAssessmentSheet(TimestampedModel, StatusMixin):
    """
    One identified risk per Risk Champion per assessment cycle.
    The inherent_risk_score is auto-computed on save() as
    likelihood.numerical_value × impact.numerical_value.
    """
    risk_champion  = models.ForeignKey(RiskChampion, on_delete=models.PROTECT,
                                        related_name='risk_sheets')
    org_unit_id    = models.UUIDField(db_index=True)
    fiscal_year    = models.ForeignKey('core.FiscalYear', on_delete=models.PROTECT,
                                        related_name='risk_sheets')
    # Risk identification
    risk_category  = models.ForeignKey('RiskCategory', on_delete=models.PROTECT,
                                        related_name='risk_sheets')
    risk_title     = models.CharField(max_length=255)
    risk_description = models.TextField()
    risk_owner     = models.UUIDField(help_text="IAM user UUID of the Risk Owner")
    # Scoring inputs (lookup FK)
    likelihood     = models.ForeignKey('RiskLikelihood', on_delete=models.PROTECT)
    impact         = models.ForeignKey('RiskImpact', on_delete=models.PROTECT)
    # Computed score (auto on save)
    inherent_risk_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    inherent_risk_level = models.ForeignKey('RiskLevel', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='inherent_sheets',
                              help_text="Resolved from RiskLevel.min_score / max_score on save()")
    # Controls & residual
    existing_controls  = models.TextField(blank=True)
    residual_likelihood = models.ForeignKey('RiskLikelihood', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='residual_sheets')
    residual_impact     = models.ForeignKey('RiskImpact', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='residual_impact_sheets')
    residual_risk_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    residual_risk_level = models.ForeignKey('RiskLevel', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='residual_sheets')
    # Justification
    control_assessment = models.TextField(blank=True)
    further_action     = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_risk_assessment_sheet'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """Auto-compute inherent and residual risk scores."""
        if self.likelihood_id and self.impact_id:
            self.inherent_risk_score = (
                self.likelihood.numerical_value * self.impact.numerical_value
            )
            self.inherent_risk_level = RiskLevel.objects.filter(
                min_score__lte=self.inherent_risk_score,
                max_score__gte=self.inherent_risk_score,
                is_active=True
            ).first()
        if self.residual_likelihood_id and self.residual_impact_id:
            self.residual_risk_score = (
                self.residual_likelihood.numerical_value * self.residual_impact.numerical_value
            )
            self.residual_risk_level = RiskLevel.objects.filter(
                min_score__lte=self.residual_risk_score,
                max_score__gte=self.residual_risk_score,
                is_active=True
            ).first()
        super().save(*args, **kwargs)
```

#### DepartmentalRiskRegister

```python
class DepartmentalRiskRegister(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Consolidated Risk Register for a Directorate/Unit/Zone per fiscal year.
    One register per org unit per fiscal year; assembles approved RiskAssessmentSheets.
    """
    org_unit_id    = models.UUIDField(db_index=True)
    org_unit_type  = models.CharField(max_length=50,
                         choices=[('directorate', 'Directorate'), ('unit', 'Unit'), ('zone', 'Zone')])
    fiscal_year    = models.ForeignKey('core.FiscalYear', on_delete=models.PROTECT,
                                        related_name='dept_registers')
    submitted_by   = models.UUIDField(null=True, blank=True,
                         help_text="RC UUID who submitted this register")
    submission_date = models.DateField(null=True, blank=True)
    rmqam_reviewer  = models.UUIDField(null=True, blank=True,
                          help_text="RMQAM UUID who reviewed")
    review_date     = models.DateField(null=True, blank=True)
    remarks         = models.TextField(blank=True)
    # Status state machine
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)

    class Meta:
        db_table = 'grc_risk_dept_register'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['org_unit_id', 'fiscal_year'],
                condition=models.Q(is_active=True),
                name='unique_active_dept_register_per_unit_year'
            )
        ]
```

#### DeptRegisterEntry

```python
class DeptRegisterEntry(TimestampedModel, StatusMixin):
    """
    Association between a DepartmentalRiskRegister and a RiskAssessmentSheet.
    Tracks inclusion sequence within the register.
    """
    dept_register  = models.ForeignKey(DepartmentalRiskRegister, on_delete=models.CASCADE,
                                        related_name='entries')
    risk_sheet     = models.ForeignKey(RiskAssessmentSheet, on_delete=models.PROTECT,
                                        related_name='register_entries')
    sort_order     = models.IntegerField(default=0, help_text="Display order within the register")

    class Meta:
        db_table = 'grc_risk_dept_register_entry'
        ordering = ['sort_order']
        unique_together = [['dept_register', 'risk_sheet']]
```

---

### 4.5 Group 3 — Institutional Register & RTAP

#### InstitutionalRiskRegister

```python
class InstitutionalRiskRegister(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Organisation-wide consolidated risk register.
    Business Rule E.11: only one active IRR per fiscal year.
    Entries are threshold-filtered from approved departmental registers.
    4-stage approval: RMQAM → Management → Risk & Governance Committee → Commission.
    """
    fiscal_year        = models.ForeignKey('core.FiscalYear', on_delete=models.PROTECT,
                                            related_name='institutional_registers')
    prepared_by        = models.UUIDField(help_text="RMQAM UUID who compiled this register")
    preparation_date   = models.DateField(null=True, blank=True)
    # Document archiving (DRS dual-reference pattern)
    document_id          = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    remarks              = models.TextField(blank=True)
    # Status state machine
    STATUS_CHOICES = [
        ('draft',              'Draft'),
        ('rmqam_review',       'RMQAM Review'),
        ('management_review',  'Management Review'),
        ('committee_review',   'Committee Review'),
        ('commission_review',  'Commission Review'),
        ('approved',           'Approved'),
        ('rejected',           'Rejected'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True)

    class Meta:
        db_table = 'grc_risk_inst_register'
        ordering = ['-created_at']
        constraints = [
            # E.11: one active IRR per fiscal year
            models.UniqueConstraint(
                fields=['fiscal_year'],
                condition=models.Q(is_active=True),
                name='unique_active_irr_per_fiscal_year'
            )
        ]
```

#### InstitutionalRiskEntry

```python
class InstitutionalRiskEntry(TimestampedModel, StatusMixin):
    """
    A single risk entry within the Institutional Risk Register.
    Sourced from approved DeptRegisterEntries that meet the risk threshold (Rule E.4).
    Threshold is defined as inherent_risk_score >= configured threshold value.
    """
    inst_register  = models.ForeignKey(InstitutionalRiskRegister, on_delete=models.CASCADE,
                                        related_name='entries')
    risk_sheet     = models.ForeignKey(RiskAssessmentSheet, on_delete=models.PROTECT,
                                        related_name='inst_register_entries')
    risk_ranking   = models.IntegerField(default=0, help_text="Ranking order in the institutional register")
    notes          = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_risk_inst_register_entry'
        ordering = ['risk_ranking']
        unique_together = [['inst_register', 'risk_sheet']]
```

#### RiskTreatmentActionPlan

```python
class RiskTreatmentActionPlan(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Risk Treatment Action Plan. Linked 1:1 with an InstitutionalRiskRegister.
    Business Rule E.11: only one active RTAP per year.
    Same 4-stage approval chain as the Institutional Risk Register.
    """
    inst_register  = models.OneToOneField(InstitutionalRiskRegister, on_delete=models.PROTECT,
                                           related_name='rtap')
    fiscal_year    = models.ForeignKey('core.FiscalYear', on_delete=models.PROTECT,
                                        related_name='rtaps')
    prepared_by    = models.UUIDField(help_text="RMQAM UUID who prepared the RTAP")
    # DRS dual-reference
    document_id          = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    remarks              = models.TextField(blank=True)
    STATUS_CHOICES = [
        ('draft',              'Draft'),
        ('rmqam_review',       'RMQAM Review'),
        ('management_review',  'Management Review'),
        ('committee_review',   'Committee Review'),
        ('commission_review',  'Commission Review'),
        ('approved',           'Approved'),
        ('rejected',           'Rejected'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True)
    overall_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                           help_text="Computed percentage of completed RTAP items")

    class Meta:
        db_table = 'grc_risk_rtap'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['fiscal_year'],
                condition=models.Q(is_active=True),
                name='unique_active_rtap_per_fiscal_year'
            )
        ]
```

#### RTAPItem

```python
class RTAPItem(TimestampedModel, StatusMixin):
    """
    One treatment control per risk entry in the RTAP.
    Tracks responsible officer, timeline, and current implementation status.
    Business Rule E.10: status values are Not Started / In Progress / Completed.
    """
    rtap           = models.ForeignKey(RiskTreatmentActionPlan, on_delete=models.CASCADE,
                                        related_name='items')
    inst_entry     = models.ForeignKey(InstitutionalRiskEntry, on_delete=models.PROTECT,
                                        related_name='rtap_items')
    treatment_description = models.TextField()
    responsible_officer   = models.UUIDField(help_text="IAM UUID of the responsible officer")
    target_date           = models.DateField()
    # Status: Rule E.10
    STATUS_NOT_STARTED = 'not_started'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED   = 'completed'
    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, 'Not Started'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED,   'Completed'),
    ]
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES,
                         default=STATUS_NOT_STARTED, db_index=True)
    sort_order     = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_rtap_item'
        ordering = ['sort_order']
```

#### RTAPQuarterlyUpdate

```python
class RTAPQuarterlyUpdate(TimestampedModel, StatusMixin):
    """
    Quarterly implementation status update for a single RTAPItem.
    Business Rule E.7: quarterly monitoring cycle.
    """
    rtap_item      = models.ForeignKey(RTAPItem, on_delete=models.CASCADE,
                                        related_name='quarterly_updates')
    quarter        = models.ForeignKey('core.Quarter', on_delete=models.PROTECT,
                                        related_name='rtap_updates')
    reported_by    = models.UUIDField(help_text="RC UUID who submitted this update")
    update_date    = models.DateField()
    STATUS_CHOICES = RTAPItem.STATUS_CHOICES  # reuse same three values
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES,
                         default='not_started', db_index=True)
    progress_notes = models.TextField(blank=True)
    evidence       = models.JSONField(
        default=list,
        help_text="List of evidence references: [{'type': 'document|url', 'ref': '...', 'label': '...'}]"
    )

    class Meta:
        db_table = 'grc_risk_rtap_quarterly_update'
        ordering = ['quarter__fiscal_year', 'quarter__quarter_number']
        unique_together = [['rtap_item', 'quarter']]
```

---

### 4.6 Group 4 — Quarterly Reporting

#### QuarterlyPerformanceReport

```python
class QuarterlyPerformanceReport(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Quarterly Risk Management Implementation Report.
    One report per fiscal year + quarter (unique constraint).
    5-stage approval: RMQAM → LSM → Management → Committee → Commission.
    Business Rule E.7: submitted quarterly and sent to Audit Committee and IAGO.
    """
    fiscal_year    = models.ForeignKey('core.FiscalYear', on_delete=models.PROTECT,
                                        related_name='quarterly_reports')
    quarter        = models.ForeignKey('core.Quarter', on_delete=models.PROTECT,
                                        related_name='quarterly_reports')
    prepared_by    = models.UUIDField(help_text="RMQAM UUID who prepared this report")
    preparation_date = models.DateField(null=True, blank=True)
    # Snapshot metrics (computed or manually entered)
    total_risks    = models.IntegerField(default=0)
    high_risks     = models.IntegerField(default=0)
    medium_risks   = models.IntegerField(default=0)
    low_risks      = models.IntegerField(default=0)
    rtap_completed = models.IntegerField(default=0, help_text="RTAPItems with status=completed this quarter")
    rtap_in_progress = models.IntegerField(default=0)
    rtap_not_started = models.IntegerField(default=0)
    report_body    = models.TextField(blank=True, help_text="Narrative body of the quarterly report")
    # DRS dual-reference
    document_id          = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    STATUS_CHOICES = [
        ('draft',             'Draft'),
        ('rmqam_prepare',     'RMQAM Preparing'),
        ('lsm_submit',        'LSM Submission'),
        ('management_review', 'Management Review'),
        ('committee_review',  'Committee Review'),
        ('commission_submit', 'Commission Submission'),
        ('approved',          'Approved'),
        ('rejected',          'Rejected'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True)

    class Meta:
        db_table = 'grc_risk_quarterly_report'
        ordering = ['-fiscal_year__start_date', '-quarter__quarter_number']
        constraints = [
            models.UniqueConstraint(
                fields=['fiscal_year', 'quarter'],
                condition=models.Q(is_active=True),
                name='unique_active_quarterly_report_per_period'
            )
        ]
```

#### ActivityReport

```python
class ActivityReport(TimestampedModel, StatusMixin):
    """
    Quarterly RC activity report — submitted by the RC, linked to the
    Institutional Risk Register for the period. Provides evidence for
    the Quarterly Performance Report.
    """
    inst_register  = models.ForeignKey(InstitutionalRiskRegister, on_delete=models.PROTECT,
                                        related_name='activity_reports')
    quarter        = models.ForeignKey('core.Quarter', on_delete=models.PROTECT,
                                        related_name='activity_reports')
    reported_by    = models.UUIDField(help_text="RC UUID who submitted this report")
    submission_date = models.DateField()
    activities_summary = models.TextField()
    issues_raised      = models.TextField(blank=True)
    recommendations    = models.TextField(blank=True)
    attachments        = models.JSONField(
        default=list,
        help_text="DRS document references: [{'document_id': '...', 'title': '...'}]"
    )

    class Meta:
        db_table = 'grc_risk_activity_report'
        ordering = ['-submission_date']
        unique_together = [['inst_register', 'quarter', 'reported_by']]
```

---

### 4.7 Group 5 — QMS Audit

#### QMSAuditProgram

```python
class QMSAuditProgram(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Annual QMS Audit Program — developed by RMQAU, approved by RMQAM.
    One active program per fiscal year.
    """
    fiscal_year    = models.ForeignKey('core.FiscalYear', on_delete=models.PROTECT,
                                        related_name='qms_programs')
    program_title  = models.CharField(max_length=255)
    objective      = models.TextField()
    scope          = models.TextField()
    prepared_by    = models.UUIDField(help_text="RMO/RMQAU UUID who prepared the program")
    approved_by    = models.UUIDField(null=True, blank=True,
                         help_text="RMQAM UUID who approved the program")
    approval_date  = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)

    class Meta:
        db_table = 'grc_risk_qms_program'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['fiscal_year'],
                condition=models.Q(is_active=True),
                name='unique_active_qms_program_per_fiscal_year'
            )
        ]
```

#### QMSAuditPlan

```python
class QMSAuditPlan(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Specific audit plan within an Audit Program — one plan per auditee unit.
    Business Rule E.7: auditee must be notified at least 10 days before audit.
    Business Rule E.2: QAs cannot audit their own unit.
    """
    audit_program       = models.ForeignKey(QMSAuditProgram, on_delete=models.CASCADE,
                                             related_name='audit_plans')
    plan_title          = models.CharField(max_length=255)
    auditee_unit_id     = models.UUIDField(db_index=True, help_text="Corporate Service unit UUID being audited")
    lead_team_leader    = models.UUIDField(help_text="QA UUID of the lead Team Leader")
    audit_start_date    = models.DateField()
    audit_end_date      = models.DateField()
    notification_date   = models.DateField(null=True, blank=True,
                              help_text="Date auditee was notified; must be ≥10 days before audit_start_date")
    scope               = models.TextField()
    criteria            = models.TextField(blank=True)
    # DRS dual-reference
    document_id          = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)

    class Meta:
        db_table = 'grc_risk_qms_plan'
        ordering = ['-created_at']

    def clean(self):
        """Validate auditee notification lead time (Rule E.7)."""
        from django.core.exceptions import ValidationError
        if self.notification_date and self.audit_start_date:
            delta = (self.audit_start_date - self.notification_date).days
            if delta < 10:
                raise ValidationError(
                    "Auditee must be notified at least 10 days before the audit start date."
                )
```

#### QMSAuditTeamAssignment

```python
class QMSAuditTeamAssignment(TimestampedModel, StatusMixin):
    """
    Join table: assigns a Quality Auditor (by UUID) to an Audit Plan.
    Tracks role on the team (team_leader or auditor).
    Business Rule E.2 check — QA org unit must differ from auditee unit — enforced in service layer.
    """
    audit_plan    = models.ForeignKey(QMSAuditPlan, on_delete=models.CASCADE,
                                       related_name='team_assignments')
    auditor_id    = models.UUIDField(db_index=True, help_text="QualityAuditor user UUID")
    ROLE_TEAM_LEADER = 'team_leader'
    ROLE_AUDITOR     = 'auditor'
    ROLE_CHOICES = [
        (ROLE_TEAM_LEADER, 'Team Leader'),
        (ROLE_AUDITOR,     'Auditor'),
    ]
    role          = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_AUDITOR)

    class Meta:
        db_table = 'grc_risk_qms_team_assignment'
        unique_together = [['audit_plan', 'auditor_id']]
```

#### AuditChecklist

```python
class AuditChecklist(TimestampedModel, StatusMixin):
    """
    ISO clause audit checklist item — one per clause per auditor within a plan.
    Conformity details are stored as JSON to accommodate varied clause structures.
    """
    audit_plan    = models.ForeignKey(QMSAuditPlan, on_delete=models.CASCADE,
                                       related_name='checklists')
    iso_clause    = models.ForeignKey('ISOClause', on_delete=models.PROTECT,
                                       related_name='checklist_items')
    auditor_id    = models.UUIDField(db_index=True, help_text="QA UUID who completed this checklist item")
    CONFORMITY_CONFORMING      = 'conforming'
    CONFORMITY_MINOR_NC        = 'minor_nc'
    CONFORMITY_MAJOR_NC        = 'major_nc'
    CONFORMITY_OBSERVATION     = 'observation'
    CONFORMITY_NOT_APPLICABLE  = 'not_applicable'
    CONFORMITY_CHOICES = [
        (CONFORMITY_CONFORMING,     'Conforming'),
        (CONFORMITY_MINOR_NC,       'Minor Non-Conformance'),
        (CONFORMITY_MAJOR_NC,       'Major Non-Conformance'),
        (CONFORMITY_OBSERVATION,    'Observation'),
        (CONFORMITY_NOT_APPLICABLE, 'Not Applicable'),
    ]
    conformity    = models.CharField(max_length=20, choices=CONFORMITY_CHOICES,
                        default=CONFORMITY_NOT_APPLICABLE, db_index=True)
    findings_detail = models.JSONField(
        default=dict,
        help_text=(
            "Free-form object capturing clause-specific findings: "
            "{'evidence': [...], 'objective_evidence': '...', 'auditor_notes': '...'}"
        )
    )

    class Meta:
        db_table = 'grc_risk_qms_checklist'
        unique_together = [['audit_plan', 'iso_clause', 'auditor_id']]
```

#### QMSAuditReport

```python
class QMSAuditReport(TimestampedModel, StatusMixin):
    """
    Final audit report for a QMSAuditPlan. 1:1 with QMSAuditPlan.
    Tracks Team Leader and Auditee signatures separately.
    The report PDF is archived to DRS on signature completion.
    """
    audit_plan          = models.OneToOneField(QMSAuditPlan, on_delete=models.PROTECT,
                                                related_name='report')
    report_title        = models.CharField(max_length=255)
    executive_summary   = models.TextField(blank=True)
    scope_summary       = models.TextField(blank=True)
    # Signatures
    tl_signed_by        = models.UUIDField(null=True, blank=True,
                              help_text="Team Leader UUID who signed the report")
    tl_signed_at        = models.DateTimeField(null=True, blank=True)
    auditee_signed_by   = models.UUIDField(null=True, blank=True,
                              help_text="Auditee representative UUID who acknowledged the report")
    auditee_signed_at   = models.DateTimeField(null=True, blank=True)
    # DRS dual-reference
    document_id          = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    STATUS_CHOICES = [
        ('draft',              'Draft'),
        ('tl_signed',          'TL Signed'),
        ('auditee_acknowledged','Auditee Acknowledged'),
        ('finalised',          'Finalised'),
    ]
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='draft', db_index=True)

    class Meta:
        db_table = 'grc_risk_qms_report'
        ordering = ['-created_at']
```

#### NonConformance

```python
class NonConformance(TimestampedModel, StatusMixin):
    """
    Non-Conformance record raised within a QMS Audit Report.
    Business Rule E.9: TL may correct, amend, or delete findings;
    dispute resolution is handled by TL before finalisation.
    """
    audit_report  = models.ForeignKey(QMSAuditReport, on_delete=models.CASCADE,
                                       related_name='nonconformances')
    iso_clause    = models.ForeignKey('ISOClause', on_delete=models.PROTECT,
                                       related_name='nonconformances')
    nc_type       = models.ForeignKey('NonConformanceType', on_delete=models.PROTECT,
                                       related_name='nonconformances')
    description   = models.TextField()
    objective_evidence = models.TextField()
    raised_by     = models.UUIDField(help_text="QA UUID who raised this NC")
    # Corrective action
    corrective_action   = models.TextField(blank=True)
    responsible_officer = models.UUIDField(null=True, blank=True,
                              help_text="IAM UUID of the officer responsible for corrective action")
    due_date            = models.DateField(null=True, blank=True)
    STATUS_RAISED       = 'raised'
    STATUS_ACKNOWLEDGED = 'acknowledged'
    STATUS_IN_PROGRESS  = 'in_progress'
    STATUS_CLOSED       = 'closed'
    STATUS_CHOICES = [
        (STATUS_RAISED,       'Raised'),
        (STATUS_ACKNOWLEDGED, 'Acknowledged'),
        (STATUS_IN_PROGRESS,  'In Progress'),
        (STATUS_CLOSED,       'Closed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RAISED, db_index=True)
    closed_at      = models.DateTimeField(null=True, blank=True)
    closure_notes  = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_risk_nonconformance'
        ordering = ['-created_at']
```

---

### 4.8 Cross-Cutting Design Decisions

#### 1. UUID-only user references

No `ForeignKey` to a `User` model anywhere. All user references are raw `UUIDField` values:

```python
# Correct
submitted_by = models.UUIDField(help_text="RC UUID who submitted this register")

# Never do this
submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
```

User display names and emails are resolved lazily via `IAMClient.get_user_profile(user_id)` in the serializer layer and never stored.

#### 2. Document dual-reference pattern (DRS)

Every model that produces an archivable document stores two fields:
```python
document_id          = models.UUIDField(null=True, blank=True)
stamped_document_url = models.URLField(blank=True, default='')
```
- `document_id` — UUID returned by DRS on upload; used for internal references and version management.
- `stamped_document_url` — DRS-issued externally accessible URL (signed or public); served directly to the frontend.
- Both are `null` / empty until the DRS upload completes; the workflow service can gate on `document_id IS NOT NULL` for the "submit for signature" step.

Affected models: `RiskChampionAppointment`, `QualityAuditorAppointment`, `InstitutionalRiskRegister`, `RiskTreatmentActionPlan`, `QuarterlyPerformanceReport`, `QMSAuditPlan`, `QMSAuditReport`.

#### 3. Partial UniqueConstraints

Used to implement the "one active instance" business rules without hard-deleting old records:

```python
# One active RC per org unit
models.UniqueConstraint(
    fields=['org_unit_id', 'org_unit_type'],
    condition=models.Q(is_active=True),
    name='unique_active_rc_per_org_unit'
)

# One active IRR per fiscal year
models.UniqueConstraint(
    fields=['fiscal_year'],
    condition=models.Q(is_active=True),
    name='unique_active_irr_per_fiscal_year'
)
```

Deactivating replaces deletion — previous records remain for historical queries.

#### 4. Auto-scoring on `save()`

`RiskAssessmentSheet.save()` computes `inherent_risk_score` and `residual_risk_score` automatically. Service code must **not** accept these fields in the request body — they must be computed server-side only. Serializers must mark these fields `read_only=True`.

#### 5. JSONField usage

Used where structure is clause/evidence-driven and would require excessively wide tables:
- `RTAPQuarterlyUpdate.evidence` — list of evidence references
- `AuditChecklist.findings_detail` — clause-specific findings object
- `ActivityReport.attachments` — DRS document references

JSON schemas are documented in the respective help_text strings.

#### 6. Status state machines

Each workflow-bearing model maintains a `status` field as a local state machine that mirrors (but is separate from) the WO `workflow_stage`. The local `status` is the source of truth for API filtering and business logic. The WO `workflow_stage` is informational — used for display and notification coordination.

State transitions are enforced in the service layer, not at the model level.

---

## 5. Lookup Tables

All lookup tables follow the `code / name / sort_order / is_active` base pattern. All are registered in `apps/risk_management/admin.py` for RMQAM-level population via Django Admin.

### 5.1 Reused Lookups (Internal Audit)

These already exist in `apps/core/models/lookups.py` — no changes required.

| Model | `db_table` | Key fields |
|-------|-----------|-----------|
| `FiscalYear` | `grc_fiscal_year` | `year_code`, `start_date`, `end_date` |
| `Quarter` | `grc_quarter` | `fiscal_year` FK, `quarter_number` (1–4), `start_date`, `end_date` |

Import them in risk management models:
```python
from apps.core.models.lookups import FiscalYear, Quarter
```

### 5.2 New Lookup Tables

All new lookup tables live in `apps/risk_management/models/lookups.py`.

#### RiskCategory

```python
class RiskCategory(TimestampedModel, StatusMixin):
    """
    Risk classification category (e.g., Operational, Financial, Compliance).
    """
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_category'
        ordering = ['sort_order', 'name']
```

#### RiskLikelihood

```python
class RiskLikelihood(TimestampedModel, StatusMixin):
    """
    Likelihood rating for risk scoring. numerical_value is used in the
    likelihood × impact computation on RiskAssessmentSheet.
    """
    code            = models.CharField(max_length=50, unique=True)
    name            = models.CharField(max_length=100)
    label           = models.CharField(max_length=100, blank=True,
                          help_text="Short display label (e.g., 'Rare', 'Likely')")
    numerical_value = models.DecimalField(max_digits=5, decimal_places=2,
                          help_text="Numeric multiplier for risk scoring (e.g., 1, 2, 3, 4, 5)")
    description     = models.TextField(blank=True)
    sort_order      = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_likelihood'
        ordering = ['sort_order']
```

#### RiskImpact

```python
class RiskImpact(TimestampedModel, StatusMixin):
    """
    Impact rating for risk scoring. numerical_value is used in the
    likelihood × impact computation on RiskAssessmentSheet.
    """
    code            = models.CharField(max_length=50, unique=True)
    name            = models.CharField(max_length=100)
    label           = models.CharField(max_length=100, blank=True,
                          help_text="Short display label (e.g., 'Negligible', 'Catastrophic')")
    numerical_value = models.DecimalField(max_digits=5, decimal_places=2,
                          help_text="Numeric multiplier for risk scoring (e.g., 1, 2, 3, 4, 5)")
    description     = models.TextField(blank=True)
    sort_order      = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_impact'
        ordering = ['sort_order']
```

#### RiskLevel

```python
class RiskLevel(TimestampedModel, StatusMixin):
    """
    Risk classification band. Maps a numeric score range to a named level.
    Used on RiskAssessmentSheet to set inherent_risk_level and residual_risk_level.

    Example bands (to be populated via migration data):
        Low    : 1–4
        Medium : 5–9
        High   : 10–16
        Critical: 17–25
    """
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    min_score   = models.DecimalField(max_digits=6, decimal_places=2,
                      help_text="Minimum score (inclusive) for this level")
    max_score   = models.DecimalField(max_digits=6, decimal_places=2,
                      help_text="Maximum score (inclusive) for this level")
    color_code  = models.CharField(max_length=7, default='#6B7280',
                      help_text="Hex color code for UI badge (e.g., '#FF0000' for Critical)")
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_level'
        ordering = ['sort_order']
```

#### NonConformanceType

```python
class NonConformanceType(TimestampedModel, StatusMixin):
    """
    Classification type for QMS audit non-conformances
    (e.g., Major NC, Minor NC, Observation, Opportunity for Improvement).
    """
    code        = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_nc_type'
        ordering = ['sort_order', 'name']
```

#### ISOClause

```python
class ISOClause(TimestampedModel, StatusMixin):
    """
    ISO 9001:2015 clause reference used in QMS audit checklists.
    Organized by clause_number for display ordering.
    """
    code          = models.CharField(max_length=50, unique=True,
                        help_text="Unique code — typically the clause number string (e.g., '7.1.2')")
    clause_number = models.CharField(max_length=20,
                        help_text="ISO clause number for display (e.g., '7.1', '8.4.1')")
    title         = models.CharField(max_length=255,
                        help_text="Full clause title from ISO 9001:2015")
    description   = models.TextField(blank=True)
    parent_clause = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sub_clauses',
        help_text="Parent clause for nested clause structures"
    )
    sort_order    = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_iso_clause'
        ordering = ['sort_order', 'clause_number']
```

### 5.3 Lookup Table Quick Reference

| Model | `db_table` | Extra Fields | Used By |
|-------|-----------|-------------|---------|
| `FiscalYear` | `grc_fiscal_year` | `start_date`, `end_date` | All fiscal-period models |
| `Quarter` | `grc_quarter` | `fiscal_year` FK, `quarter_number` | `RTAPQuarterlyUpdate`, `QuarterlyPerformanceReport`, `ActivityReport` |
| `RiskCategory` | `grc_risk_category` | — | `RiskAssessmentSheet` |
| `RiskLikelihood` | `grc_risk_likelihood` | `numerical_value`, `label` | `RiskAssessmentSheet` (×2) |
| `RiskImpact` | `grc_risk_impact` | `numerical_value`, `label` | `RiskAssessmentSheet` (×2) |
| `RiskLevel` | `grc_risk_level` | `min_score`, `max_score`, `color_code` | `RiskAssessmentSheet` (resolved on `save()`) |
| `NonConformanceType` | `grc_risk_nc_type` | — | `NonConformance` |
| `ISOClause` | `grc_risk_iso_clause` | `clause_number`, `title`, `parent_clause` | `AuditChecklist`, `NonConformance` |

---

## 6. Workflow Integration

### 6.1 Workflow Template Definitions (YAML)

These YAML blocks define the workflow plans registered in the Work Orchestration Service. Each template is stored in `apps/risk_management/workflows/` as an individual YAML file and loaded via the management command `sync_workflow_templates`.

---

#### `grc.risk_champion_appointment.yaml`

```yaml
definitionKey: "grc.risk_champion_appointment"
name: "Risk Champion Appointment"
description: "Approval workflow for Risk Champion appointment letters (3-stage: RMO → RMQAM → DG)"
version: 1
stages:
  - key: "rmo_draft"
    name: "RMO Draft"
    description: "RMO prepares the draft appointment letter and supporting documents"
    assignees:
      roleCode: "grc.rmo"
    actions:
      - key: "submit_for_review"
        label: "Submit for RMQAM Review"
        nextState: "rmqam_review"
        requiresComment: false
      - key: "save_draft"
        label: "Save as Draft"
        nextState: "rmo_draft"
        requiresComment: false
    sla:
      warningDays: 3
      overdueDays: 7
    metadata:
      status_on_complete: "submitted"

  - key: "rmqam_review"
    name: "RMQAM Review"
    description: "RMQAM reviews the appointment letter for compliance and completeness"
    assignees:
      roleCode: "grc.rmqam"
    actions:
      - key: "approve_forward_dg"
        label: "Approve and Forward to DG"
        nextState: "dg_signature"
        requiresComment: false
      - key: "return_rework"
        label: "Return for Rework"
        nextState: "rmo_draft"
        requiresComment: true
    sla:
      warningDays: 2
      overdueDays: 5
    metadata:
      status_on_complete: "approved"

  - key: "dg_signature"
    name: "DG Signature"
    description: "Director General signs the appointment letter"
    assignees:
      roleCode: "grc.dg"
    actions:
      - key: "sign_letter"
        label: "Sign Appointment Letter"
        nextState: null
        requiresComment: false
        terminal: true
      - key: "return_rmqam"
        label: "Return to RMQAM"
        nextState: "rmqam_review"
        requiresComment: true
    sla:
      warningDays: 3
      overdueDays: 7
    metadata:
      status_on_complete: "signed"
```

---

#### `grc.dept_risk_register_approval.yaml`

```yaml
definitionKey: "grc.dept_risk_register_approval"
name: "Departmental Risk Register Approval"
description: "2-stage approval: Risk Champion submits, RMQAM approves"
version: 1
stages:
  - key: "rc_submit"
    name: "RC Submission"
    description: "Risk Champion submits the completed Departmental Risk Register"
    assignees:
      roleCode: "grc.risk_champion"
    actions:
      - key: "submit"
        label: "Submit for Approval"
        nextState: "rmqam_approve"
        requiresComment: false
    sla:
      warningDays: 5
      overdueDays: 10
    metadata:
      status_on_complete: "submitted"

  - key: "rmqam_approve"
    name: "RMQAM Approval"
    description: "RMQAM reviews and approves or returns the register"
    assignees:
      roleCode: "grc.rmqam"
    actions:
      - key: "approve"
        label: "Approve"
        nextState: null
        requiresComment: false
        terminal: true
      - key: "return_rework"
        label: "Return for Rework"
        nextState: "rc_submit"
        requiresComment: true
    sla:
      warningDays: 3
      overdueDays: 7
    metadata:
      status_on_complete: "approved"
```

---

#### `grc.institutional_risk_register_approval.yaml`

```yaml
definitionKey: "grc.institutional_risk_register_approval"
name: "Institutional Risk Register Approval"
description: "4-stage governance approval chain for the organisation-wide risk register"
version: 1
stages:
  - key: "rmqam_review"
    name: "RMQAM Review"
    description: "RMQAM compiles and internally reviews the Institutional Risk Register"
    assignees:
      roleCode: "grc.rmqam"
    actions:
      - key: "forward_management"
        label: "Forward to Management"
        nextState: "management_discussion"
        requiresComment: false
      - key: "return_rework"
        label: "Return for Internal Rework"
        nextState: "rmqam_review"
        requiresComment: true
    sla:
      warningDays: 5
      overdueDays: 10
    metadata:
      status_on_complete: "rmqam_review"

  - key: "management_discussion"
    name: "Management Discussion"
    description: "Management Meeting reviews and endorses the register"
    assignees:
      roleCode: "grc.management"
    actions:
      - key: "endorse_forward_committee"
        label: "Endorse and Forward to Committee"
        nextState: "committee_review"
        requiresComment: false
      - key: "return_rmqam"
        label: "Return to RMQAM"
        nextState: "rmqam_review"
        requiresComment: true
    sla:
      warningDays: 3
      overdueDays: 7
    metadata:
      status_on_complete: "management_review"

  - key: "committee_review"
    name: "Risk & Governance Committee Review"
    description: "Risk and Governance Committee reviews the register. Document must be submitted 7 days before meeting."
    assignees:
      roleCode: "grc.risk_governance_committee"
    actions:
      - key: "recommend_commission"
        label: "Recommend to Commission"
        nextState: "commission_approval"
        requiresComment: false
      - key: "return_management"
        label: "Return to Management"
        nextState: "management_discussion"
        requiresComment: true
    sla:
      warningDays: 5
      overdueDays: 14
    metadata:
      status_on_complete: "committee_review"

  - key: "commission_approval"
    name: "Commission Approval"
    description: "Commission gives final approval to the Institutional Risk Register"
    assignees:
      roleCode: "grc.commission"
    actions:
      - key: "approve"
        label: "Approve"
        nextState: null
        requiresComment: false
        terminal: true
      - key: "defer"
        label: "Defer"
        nextState: "committee_review"
        requiresComment: true
    sla:
      warningDays: 5
      overdueDays: 14
    metadata:
      status_on_complete: "approved"
```

---

#### `grc.rtap_approval.yaml`

```yaml
# Same 4-stage governance chain as Institutional Risk Register
definitionKey: "grc.rtap_approval"
name: "Risk Treatment Action Plan Approval"
description: "4-stage governance approval for the RTAP — mirrors IRR approval chain"
version: 1
# stages: identical structure to grc.institutional_risk_register_approval
# Replace status_on_complete values only:
#   rmqam_review → "rmqam_review"
#   management_discussion → "management_review"
#   committee_review → "committee_review"
#   commission_approval → "approved"
stages:
  - key: "rmqam_review"
    name: "RMQAM Review"
    assignees: { roleCode: "grc.rmqam" }
    actions:
      - { key: "forward_management", label: "Forward to Management", nextState: "management_discussion" }
      - { key: "return_rework", label: "Return for Rework", nextState: "rmqam_review", requiresComment: true }
    sla: { warningDays: 5, overdueDays: 10 }
    metadata: { status_on_complete: "rmqam_review" }

  - key: "management_discussion"
    name: "Management Discussion"
    assignees: { roleCode: "grc.management" }
    actions:
      - { key: "endorse_forward_committee", label: "Endorse and Forward to Committee", nextState: "committee_review" }
      - { key: "return_rmqam", label: "Return to RMQAM", nextState: "rmqam_review", requiresComment: true }
    sla: { warningDays: 3, overdueDays: 7 }
    metadata: { status_on_complete: "management_review" }

  - key: "committee_review"
    name: "Risk & Governance Committee Review"
    assignees: { roleCode: "grc.risk_governance_committee" }
    actions:
      - { key: "recommend_commission", label: "Recommend to Commission", nextState: "commission_approval" }
      - { key: "return_management", label: "Return to Management", nextState: "management_discussion", requiresComment: true }
    sla: { warningDays: 5, overdueDays: 14 }
    metadata: { status_on_complete: "committee_review" }

  - key: "commission_approval"
    name: "Commission Approval"
    assignees: { roleCode: "grc.commission" }
    actions:
      - { key: "approve", label: "Approve", nextState: null, terminal: true }
      - { key: "defer", label: "Defer", nextState: "committee_review", requiresComment: true }
    sla: { warningDays: 5, overdueDays: 14 }
    metadata: { status_on_complete: "approved" }
```

---

#### `grc.quarterly_risk_report_approval.yaml`

```yaml
definitionKey: "grc.quarterly_risk_report_approval"
name: "Quarterly Risk Management Performance Report Approval"
description: "5-stage approval: RMQAM prepares → LSM routes → Management → Committee → Commission"
version: 1
stages:
  - key: "rmqam_prepare"
    name: "RMQAM Preparation"
    assignees: { roleCode: "grc.rmqam" }
    actions:
      - { key: "submit_lsm", label: "Submit to LSM", nextState: "lsm_submit" }
    sla: { warningDays: 5, overdueDays: 10 }
    metadata: { status_on_complete: "rmqam_prepare" }

  - key: "lsm_submit"
    name: "LSM Submission"
    description: "LSM routes the report to the Risk and Governance Committee"
    assignees: { roleCode: "grc.lsm" }
    actions:
      - { key: "route_committee", label: "Route to Committee", nextState: "management_discussion" }
      - { key: "return_rmqam", label: "Return to RMQAM", nextState: "rmqam_prepare", requiresComment: true }
    sla: { warningDays: 2, overdueDays: 5 }
    metadata: { status_on_complete: "lsm_submit" }

  - key: "management_discussion"
    name: "Management Discussion"
    assignees: { roleCode: "grc.management" }
    actions:
      - { key: "endorse", label: "Endorse Report", nextState: "committee_review" }
      - { key: "return_lsm", label: "Return to LSM", nextState: "lsm_submit", requiresComment: true }
    sla: { warningDays: 3, overdueDays: 7 }
    metadata: { status_on_complete: "management_review" }

  - key: "committee_review"
    name: "Risk & Governance Committee Review"
    assignees: { roleCode: "grc.risk_governance_committee" }
    actions:
      - { key: "forward_commission", label: "Forward to Commission", nextState: "commission_submit" }
      - { key: "return_management", label: "Return to Management", nextState: "management_discussion", requiresComment: true }
    sla: { warningDays: 5, overdueDays: 14 }
    metadata: { status_on_complete: "committee_review" }

  - key: "commission_submit"
    name: "Commission Submission"
    assignees: { roleCode: "grc.commission" }
    actions:
      - { key: "acknowledge", label: "Acknowledge Receipt", nextState: null, terminal: true }
    sla: { warningDays: 5, overdueDays: 14 }
    metadata: { status_on_complete: "approved" }
```

---

#### `grc.qa_appointment.yaml`

```yaml
# Mirrors grc.risk_champion_appointment with QA-specific wording
definitionKey: "grc.qa_appointment"
name: "Quality Auditor Appointment"
description: "Approval workflow for Quality Auditor appointment letters (3-stage: RMO → RMQAM → DG)"
version: 1
stages:
  - key: "rmo_draft"
    name: "RMO Draft"
    assignees: { roleCode: "grc.rmo" }
    actions:
      - { key: "submit_for_review", label: "Submit for RMQAM Review", nextState: "rmqam_review" }
    sla: { warningDays: 3, overdueDays: 7 }
    metadata: { status_on_complete: "submitted" }

  - key: "rmqam_review"
    name: "RMQAM Review"
    assignees: { roleCode: "grc.rmqam" }
    actions:
      - { key: "approve_forward_dg", label: "Approve and Forward to DG", nextState: "dg_signature" }
      - { key: "return_rework", label: "Return for Rework", nextState: "rmo_draft", requiresComment: true }
    sla: { warningDays: 2, overdueDays: 5 }
    metadata: { status_on_complete: "approved" }

  - key: "dg_signature"
    name: "DG Signature"
    assignees: { roleCode: "grc.dg" }
    actions:
      - { key: "sign_letter", label: "Sign Appointment Letter", nextState: null, terminal: true }
      - { key: "return_rmqam", label: "Return to RMQAM", nextState: "rmqam_review", requiresComment: true }
    sla: { warningDays: 3, overdueDays: 7 }
    metadata: { status_on_complete: "signed" }
```

---

#### `grc.qms_audit_program_approval.yaml`

```yaml
definitionKey: "grc.qms_audit_program_approval"
name: "QMS Audit Program Approval"
description: "2-stage approval: RMO submits, RMQAM approves the annual audit program"
version: 1
stages:
  - key: "rmo_submit"
    name: "RMO Submission"
    assignees: { roleCode: "grc.rmo" }
    actions:
      - { key: "submit", label: "Submit for Approval", nextState: "rmqam_approve" }
    sla: { warningDays: 5, overdueDays: 14 }
    metadata: { status_on_complete: "submitted" }

  - key: "rmqam_approve"
    name: "RMQAM Approval"
    assignees: { roleCode: "grc.rmqam" }
    actions:
      - { key: "approve", label: "Approve Program", nextState: null, terminal: true }
      - { key: "return_rework", label: "Return for Rework", nextState: "rmo_submit", requiresComment: true }
    sla: { warningDays: 5, overdueDays: 10 }
    metadata: { status_on_complete: "approved" }
```

---

#### `grc.qms_audit_plan_approval.yaml`

```yaml
# Mirrors qms_audit_program_approval
definitionKey: "grc.qms_audit_plan_approval"
name: "QMS Audit Plan Approval"
description: "2-stage approval: RMO submits audit plan, RMQAM approves"
version: 1
stages:
  - key: "rmo_submit"
    name: "RMO Submission"
    assignees: { roleCode: "grc.rmo" }
    actions:
      - { key: "submit", label: "Submit Audit Plan for Approval", nextState: "rmqam_approve" }
    sla: { warningDays: 5, overdueDays: 10 }
    metadata: { status_on_complete: "submitted" }

  - key: "rmqam_approve"
    name: "RMQAM Approval"
    assignees: { roleCode: "grc.rmqam" }
    actions:
      - { key: "approve", label: "Approve Audit Plan", nextState: null, terminal: true }
      - { key: "return_rework", label: "Return for Rework", nextState: "rmo_submit", requiresComment: true }
    sla: { warningDays: 3, overdueDays: 7 }
    metadata: { status_on_complete: "approved" }
```

---

### 6.2 WorkflowMixin Context Overrides

Every `WorkflowMixin` model must override `get_workflow_context()` and `get_workflow_metadata()`. Patterns for each entity:

#### RiskChampionAppointment

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'risk_champion_appointment',
        'entity_id': str(self.id),
        'risk_champion_id': str(self.risk_champion_id),
        'org_unit_id': str(self.risk_champion.org_unit_id),
        'appointment_date': str(self.appointment_date),
    }

def get_workflow_metadata(self) -> dict:
    return {
        'entity_type': 'risk_champion_appointment',
        'entity_id': str(self.id),
        'entity_repr': f"RC Appointment — {self.appointment_date}",
        'document_id': str(self.document_id) if self.document_id else None,
    }
```

#### DepartmentalRiskRegister

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'departmental_risk_register',
        'entity_id': str(self.id),
        'org_unit_id': str(self.org_unit_id),
        'org_unit_type': self.org_unit_type,
        'fiscal_year_id': str(self.fiscal_year_id),
        'fiscal_year_code': self.fiscal_year.year_code,
    }

def get_workflow_metadata(self) -> dict:
    return {
        'entity_type': 'departmental_risk_register',
        'entity_id': str(self.id),
        'entity_repr': f"Dept Register — {self.fiscal_year.year_code}",
    }
```

#### InstitutionalRiskRegister

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'institutional_risk_register',
        'entity_id': str(self.id),
        'fiscal_year_id': str(self.fiscal_year_id),
        'fiscal_year_code': self.fiscal_year.year_code,
        'prepared_by': str(self.prepared_by),
    }

def get_workflow_metadata(self) -> dict:
    return {
        'entity_type': 'institutional_risk_register',
        'entity_id': str(self.id),
        'entity_repr': f"Institutional Risk Register — {self.fiscal_year.year_code}",
        'document_id': str(self.document_id) if self.document_id else None,
    }
```

#### RiskTreatmentActionPlan

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'risk_treatment_action_plan',
        'entity_id': str(self.id),
        'inst_register_id': str(self.inst_register_id),
        'fiscal_year_id': str(self.fiscal_year_id),
        'fiscal_year_code': self.fiscal_year.year_code,
    }

def get_workflow_metadata(self) -> dict:
    return {
        'entity_type': 'risk_treatment_action_plan',
        'entity_id': str(self.id),
        'entity_repr': f"RTAP — {self.fiscal_year.year_code}",
        'document_id': str(self.document_id) if self.document_id else None,
    }
```

#### QuarterlyPerformanceReport

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'quarterly_performance_report',
        'entity_id': str(self.id),
        'fiscal_year_id': str(self.fiscal_year_id),
        'quarter_id': str(self.quarter_id),
        'period': f"{self.fiscal_year.year_code} — {self.quarter.name}",
    }

def get_workflow_metadata(self) -> dict:
    return {
        'entity_type': 'quarterly_performance_report',
        'entity_id': str(self.id),
        'entity_repr': f"Quarterly Report — {self.fiscal_year.year_code} {self.quarter.name}",
        'document_id': str(self.document_id) if self.document_id else None,
    }
```

#### QualityAuditorAppointment

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'quality_auditor_appointment',
        'entity_id': str(self.id),
        'quality_auditor_id': str(self.quality_auditor_id),
        'org_unit_id': str(self.quality_auditor.org_unit_id),
        'appointment_date': str(self.appointment_date),
    }

def get_workflow_metadata(self) -> dict:
    return {
        'entity_type': 'quality_auditor_appointment',
        'entity_id': str(self.id),
        'entity_repr': f"QA Appointment — {self.appointment_date}",
        'document_id': str(self.document_id) if self.document_id else None,
    }
```

#### QMSAuditProgram

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'qms_audit_program',
        'entity_id': str(self.id),
        'fiscal_year_id': str(self.fiscal_year_id),
        'fiscal_year_code': self.fiscal_year.year_code,
        'prepared_by': str(self.prepared_by),
    }

def get_workflow_metadata(self) -> dict:
    return {
        'entity_type': 'qms_audit_program',
        'entity_id': str(self.id),
        'entity_repr': f"QMS Audit Program — {self.fiscal_year.year_code}",
    }
```

#### QMSAuditPlan

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'qms_audit_plan',
        'entity_id': str(self.id),
        'audit_program_id': str(self.audit_program_id),
        'auditee_unit_id': str(self.auditee_unit_id),
        'audit_start_date': str(self.audit_start_date),
        'lead_team_leader': str(self.lead_team_leader),
    }

def get_workflow_metadata(self) -> dict:
    return {
        'entity_type': 'qms_audit_plan',
        'entity_id': str(self.id),
        'entity_repr': f"QMS Audit Plan — {self.plan_title}",
        'document_id': str(self.document_id) if self.document_id else None,
    }
```

---

### 6.3 Standard Workflow Endpoints (per entity)

Each workflow-bearing entity exposes 5 standard endpoint patterns. Use `RiskChampionAppointmentWorkflowView` as the naming model.

```
POST   /api/v1/risk-management/risk-champion-appointments/<id>/workflow/start/
GET    /api/v1/risk-management/risk-champion-appointments/<id>/workflow/status/
POST   /api/v1/risk-management/risk-champion-appointments/<id>/workflow/advance/
POST   /api/v1/risk-management/risk-champion-appointments/<id>/workflow/cancel/
POST   /api/v1/risk-management/risk-champion-appointments/<id>/workflow/recall/
```

Full URL and view name table for all 8 workflow entities:

| Entity | URL prefix | View class prefix |
|--------|-----------|------------------|
| `RiskChampionAppointment` | `risk-champion-appointments/<id>` | `RiskChampionAppointmentWorkflow` |
| `DepartmentalRiskRegister` | `dept-risk-registers/<id>` | `DeptRiskRegisterWorkflow` |
| `InstitutionalRiskRegister` | `institutional-risk-registers/<id>` | `InstitutionalRiskRegisterWorkflow` |
| `RiskTreatmentActionPlan` | `rtaps/<id>` | `RTAPWorkflow` |
| `QuarterlyPerformanceReport` | `quarterly-reports/<id>` | `QuarterlyReportWorkflow` |
| `QualityAuditorAppointment` | `quality-auditor-appointments/<id>` | `QAAppointmentWorkflow` |
| `QMSAuditProgram` | `qms-programs/<id>` | `QMSAuditProgramWorkflow` |
| `QMSAuditPlan` | `qms-plans/<id>` | `QMSAuditPlanWorkflow` |

Each view action:

| Suffix | HTTP | Purpose |
|--------|------|---------|
| `workflow/start/` | `POST` | Call WO to create plan; call `entity.start_workflow(plan_id, initial_stage)` |
| `workflow/status/` | `GET` | Return `workflow_plan_id`, `workflow_stage`, `has_active_workflow`, local `status` |
| `workflow/advance/` | `POST` | Validate action key; call WO advance API; call `entity.update_workflow_stage()` |
| `workflow/cancel/` | `POST` | Call WO cancel; call `entity.cancel_workflow()`; set `entity.status = 'rejected'` |
| `workflow/recall/` | `POST` | Call WO cancel; call `entity.clear_workflow()`; reset `entity.status = 'draft'` |

---

### 6.4 Service Class Pattern

All business logic lives in service classes inside `apps/risk_management/services/`. View classes are thin — they validate permissions, call the service, and return the response. Never put business logic in views.

The service class pattern follows `AuditPlanService` exactly:

```python
# apps/risk_management/services/risk_champion_service.py

from apps.risk_management.models.risk_champion import RiskChampion, RiskChampionAppointment
from apps.core.integrations.work_orchestration import WorkOrchestrationClient
from apps.core.integrations.drs import DocumentRecordsClient


class RiskChampionService:
    """
    Service layer for Risk Champion lifecycle management.
    All methods are static or class methods — no service instance state.
    """

    WORKFLOW_TEMPLATE = 'grc.risk_champion_appointment'

    @staticmethod
    def get_active_risk_champions(org_unit_id=None):
        """Return active Risk Champions, optionally filtered by org unit."""
        qs = RiskChampion.objects.filter(is_active=True).select_related('appointments')
        if org_unit_id:
            qs = qs.filter(org_unit_id=org_unit_id)
        return qs.order_by('-created_at')

    @staticmethod
    def create_risk_champion(user_id, org_unit_id, org_unit_type,
                              nominated_by, term_start, notes=''):
        """
        Create a new Risk Champion record.
        Does not start the appointment workflow — that is a separate step.
        Raises ValidationError if one is already active for this org unit.
        """
        if RiskChampion.objects.filter(
            org_unit_id=org_unit_id,
            org_unit_type=org_unit_type,
            is_active=True
        ).exists():
            from django.core.exceptions import ValidationError
            raise ValidationError(
                "An active Risk Champion already exists for this organisation unit."
            )
        return RiskChampion.objects.create(
            user_id=user_id,
            org_unit_id=org_unit_id,
            org_unit_type=org_unit_type,
            nominated_by=nominated_by,
            term_start=term_start,
            notes=notes,
            created_by=nominated_by,
        )

    @staticmethod
    def start_appointment_workflow(appointment: RiskChampionAppointment, actor_id):
        """
        Create a WO workflow plan for an appointment letter and update the appointment.
        Follows the AuditPlanService.start_workflow() pattern exactly.
        """
        wo_client = WorkOrchestrationClient()
        plan = wo_client.create_plan(
            template_key=RiskChampionService.WORKFLOW_TEMPLATE,
            entity_id=str(appointment.id),
            entity_type='risk_champion_appointment',
            context=appointment.get_workflow_context(),
            metadata=appointment.get_workflow_metadata(),
            initiated_by=str(actor_id),
        )
        appointment.start_workflow(
            plan_id=plan['plan_id'],
            initial_stage=plan['current_stage'],
            stage_id=plan['stage_id'],
        )
        appointment.status = RiskChampionAppointment.STATUS_SUBMITTED
        appointment.modified_by = actor_id
        appointment.save()
        return appointment

    @staticmethod
    def advance_appointment_workflow(appointment: RiskChampionAppointment, action_key: str,
                                      actor_id, comment: str = ''):
        """
        Advance the WO workflow to the next stage and update local record.
        """
        wo_client = WorkOrchestrationClient()
        result = wo_client.advance_stage(
            plan_id=str(appointment.workflow_plan_id),
            action_key=action_key,
            actor_id=str(actor_id),
            comment=comment,
        )
        if result.get('completed'):
            appointment.complete_workflow()
            appointment.status = result.get('metadata', {}).get('status_on_complete', appointment.status)
        else:
            appointment.update_workflow_stage(
                stage_name=result['current_stage'],
                stage_id=result.get('stage_id'),
            )
        appointment.modified_by = actor_id
        appointment.save()
        return appointment
```

**Service class naming convention:**

| Entity group | Service class | File |
|---|---|---|
| Risk Champion & Appointment | `RiskChampionService` | `risk_champion_service.py` |
| Quality Auditor & Appointment | `QualityAuditorService` | `quality_auditor_service.py` |
| Risk Assessment & Dept Register | `RiskAssessmentService` | `risk_assessment_service.py` |
| Institutional Register | `InstitutionalRiskRegisterService` | `risk_register_service.py` |
| RTAP & Quarterly Updates | `RTAPService` | `rtap_service.py` |
| Quarterly Reports | `QuarterlyReportService` | `reporting_service.py` |
| QMS Audit (all 6 models) | `QMSAuditService` | `qms_audit_service.py` |

---

*This document continues in `Risk_Management_Module_API_Design.md` (§7 Serializers, §8 Views, §9 URL Patterns, §10 Permissions).*
