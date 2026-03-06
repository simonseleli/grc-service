"""
Core audit entity models for GRC Audit Service.
These models implement the main audit business logic with lookup table references.
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Abs
from .base import BaseModel, TimestampedModel, StatusMixin, WorkflowMixin
from .lookups import FiscalYear, Quarter, AuditSeverity, FindingType, RiskRating, AuditOpinion
from .organizational import Directorate, Unit


class AuditUniverse(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Represents the complete scope of potential auditable activities.
    Updated to use FiscalYear lookup instead of free text.
    """
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.PROTECT,
        related_name='audit_universes',
        help_text="Reference to fiscal year lookup table"
    )
    description = models.TextField(
        help_text="Overall scope description of the audit universe"
    )
    
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
        help_text="Current status of the audit universe"
    )
    
    reviewed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="CIA user ID who reviewed this universe"
    )
    approved_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="CIA user ID who approved this universe"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when universe was approved"
    )
    
    class Meta:
        db_table = 'grc_audit_universe'
        ordering = ['-fiscal_year__start_date']
        unique_together = [['fiscal_year']]
        verbose_name = 'Audit Universe'
        verbose_name_plural = 'Audit Universes'
        
    def __str__(self):
        return f"Audit Universe - {self.fiscal_year.year_code}"

    def get_workflow_context(self) -> dict:
        """
        Returns context variables for workflow assignee resolution (FIMS pattern).
        """
        return {
            "audit_universe_id": str(self.id),
            "fiscal_year_id": str(self.fiscal_year_id),
        }

    def get_workflow_metadata(self) -> dict:
        """
        Returns metadata for workflow plan display (FIMS pattern).
        Stored with the plan in Work Orchestration Service.
        """
        meta = {
            "entity_type": "audit_universe",
            "entity_id": str(self.id),
            "fiscal_year": self.fiscal_year.year_code,
            "description": (self.description or "")[:200],
            "status": self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, "audit_universe")

    def get_workflow_stages(self) -> list:
        """
        Returns inline stage definitions for Work Orchestration Service plan creation.
        Single-stage CIA review for audit universe approval.
        """
        return [
            {
                "definition_key": "cia_review",
                "name": "CIA Review",
                "order": 0,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve",  "next_state": "completed"},
                    {"name": "return",  "label": "Return",   "next_state": "rejected"},
                ],
                "form_schema": {
                    "fields": [
                        {"name": "comments", "type": "textarea", "required": False},
                    ]
                },
                "sla": {"targetHours": 72},
            }
        ]


class AuditableEntity(TimestampedModel, StatusMixin):
    """
    Individual units/departments that can be audited.
    Enhanced with organizational structure references.
    """
    audit_universe = models.ForeignKey(
        AuditUniverse,
        on_delete=models.CASCADE,
        related_name='auditable_entities',
        help_text="Parent audit universe"
    )
    
    ENTITY_TYPE_CHOICES = [
        ('directorate', 'Directorate'),
        ('unit', 'Unit'),
        ('zone', 'Zone'),
        ('process', 'Process'),
        ('system', 'System'),
        ('project', 'Project'),
    ]
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPE_CHOICES,
        help_text="Type of auditable entity"
    )
    
    # Organizational structure references (optional based on entity type)
    directorate = models.ForeignKey(
        Directorate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditable_entities',
        help_text="Reference to directorate (if applicable)"
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditable_entities',
        help_text="Reference to unit (if applicable)"
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the auditable entity"
    )
    code = models.CharField(
        max_length=50,
        help_text="Unique entity code"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the entity"
    )
    head_of_entity = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the entity head from IAM service"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional entity attributes and properties"
    )
    
    class Meta:
        db_table = 'grc_auditable_entity'
        ordering = ['name']
        unique_together = [['audit_universe', 'code']]
        verbose_name = 'Auditable Entity'
        verbose_name_plural = 'Auditable Entities'
        
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def organizational_path(self):
        """Get the full organizational path for this entity."""
        if self.unit:
            return f"{self.unit.directorate.name} > {self.unit.name}"
        elif self.directorate:
            return self.directorate.name
        return "No organizational structure"


class RiskAssessment(TimestampedModel, StatusMixin):
    """
    Risk evaluation for auditable entities using standardized ratings.
    """
    auditable_entity = models.ForeignKey(
        AuditableEntity,
        on_delete=models.CASCADE,
        related_name='risk_assessments',
        help_text="Entity being assessed"
    )
    assessment_period = models.CharField(
        max_length=50,
        help_text="Period for which this assessment applies"
    )
    
    # Risk scoring using lookup table references
    inherent_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Inherent risk score (0-10 scale)"
    )
    control_effectiveness_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Control effectiveness score (0-10 scale)"
    )
    financial_exposure_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Financial exposure risk score"
    )
    compliance_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Compliance risk score"
    )
    operational_impact_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Operational impact score"
    )
    reputational_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Reputational risk score"
    )
    
    overall_risk_rating = models.ForeignKey(
        RiskRating,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='overall_assessments',
        help_text="Overall risk rating from lookup table (auto-populated by scoring)"
    )
    residual_risk_rating = models.ForeignKey(
        RiskRating,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='residual_assessments',
        help_text="Post-control risk rating (auto-populated by scoring)"
    )

    # Auto-calculated fields (GAP 6 — SRS: auto-calculate weighted risk scores)
    calculated_weighted_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Auto-calculated weighted risk score"
    )
    calculated_residual_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Auto-calculated residual risk score after control adjustment"
    )
    auto_overall_rating = models.ForeignKey(
        RiskRating,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auto_overall_assessments',
        help_text="System-calculated overall risk rating based on weighted score"
    )
    auto_residual_rating = models.ForeignKey(
        RiskRating,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auto_residual_assessments',
        help_text="System-calculated residual risk rating"
    )
    rating_overridden = models.BooleanField(
        default=False,
        help_text="Whether the user has manually overridden the auto-calculated rating"
    )
    
    justification = models.TextField(
        help_text="Rationale for the risk scoring and ratings"
    )
    evidence_attachments = models.JSONField(
        default=list,
        blank=True,
        help_text="List of supporting document references"
    )
    
    assessed_by = models.UUIDField(
        help_text="User ID of the assessor from IAM service"
    )
    reviewed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the reviewer from IAM service"
    )
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Review'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the risk assessment"
    )
    
    class Meta:
        db_table = 'grc_risk_assessment'
        ordering = ['-created_at']
        verbose_name = 'Risk Assessment'
        verbose_name_plural = 'Risk Assessments'
        
    def __str__(self):
        return f"Risk Assessment - {self.auditable_entity.name} ({self.assessment_period})"

    # ── Risk Weight Configuration (GAP 6) ──────────────────────────────────
    # Configurable weights for each score dimension — sum should equal 1.0
    DEFAULT_WEIGHTS = {
        'inherent_risk': 0.25,
        'control_effectiveness': 0.20,
        'financial_exposure': 0.15,
        'compliance_risk': 0.15,
        'operational_impact': 0.15,
        'reputational_risk': 0.10,
    }

    def calculate_weighted_score(self, weights=None):
        """Calculate weighted composite risk score from the 6 dimensions."""
        w = weights or self.DEFAULT_WEIGHTS
        scores = {
            'inherent_risk': self.inherent_risk_score,
            'control_effectiveness': self.control_effectiveness_score,
            'financial_exposure': self.financial_exposure_score,
            'compliance_risk': self.compliance_risk_score,
            'operational_impact': self.operational_impact_score,
            'reputational_risk': self.reputational_risk_score,
        }
        # If any score is None, skip calculation
        if any(v is None for v in scores.values()):
            return None
        from decimal import Decimal
        total = sum(Decimal(str(v)) * Decimal(str(w[k])) for k, v in scores.items())
        return round(total, 2)

    def calculate_residual_score(self, weighted_score=None):
        """Calculate residual risk: weighted_score * (1 - control_effectiveness / 10)."""
        ws = weighted_score if weighted_score is not None else self.calculated_weighted_score
        if ws is None or self.control_effectiveness_score is None:
            return None
        from decimal import Decimal
        ce = Decimal(str(self.control_effectiveness_score))
        adjustment = Decimal('1') - (ce / Decimal('10'))
        return round(Decimal(str(ws)) * adjustment, 2)

    @staticmethod
    def classify_score(score):
        """Map a numeric score to a RiskRating using threshold ranges.

        Looks up RiskRating records that have min_score/max_score set.
        Falls back to nearest numerical_value if no thresholds configured.
        """
        if score is None:
            return None
        from decimal import Decimal
        score = Decimal(str(score))
        # Try threshold-based classification first
        rating = RiskRating.objects.filter(
            min_score__isnull=False,
            max_score__isnull=False,
            min_score__lte=score,
            max_score__gte=score,
            is_active=True,
        ).first()
        if rating:
            return rating
        # Fallback: closest numerical_value
        rating = RiskRating.objects.filter(
            is_active=True,
        ).order_by(
            Abs(models.F('numerical_value') - score)
        ).first()
        return rating

    def save(self, *args, **kwargs):
        """Auto-calculate scores and ratings on every save.

        Skips auto-calculation when ``update_fields`` is provided and does
        not include any score field (e.g. status-only transitions).
        """
        update_fields = kwargs.get('update_fields')
        score_fields = {
            'inherent_risk_score', 'control_effectiveness_score',
            'financial_exposure_score', 'compliance_risk_score',
            'operational_impact_score', 'reputational_risk_score',
            'calculated_weighted_score', 'calculated_residual_score',
            'auto_overall_rating', 'auto_residual_rating',
            'overall_risk_rating', 'residual_risk_rating',
            'rating_overridden',
        }
        should_calc = update_fields is None or bool(set(update_fields) & score_fields)

        if should_calc:
            ws = self.calculate_weighted_score()
            if ws is not None:
                self.calculated_weighted_score = ws
                self.calculated_residual_score = self.calculate_residual_score(ws)
                self.auto_overall_rating = self.classify_score(ws)
                self.auto_residual_rating = self.classify_score(self.calculated_residual_score)
                # Auto-populate the manual FK fields if not overridden
                if not self.rating_overridden:
                    if self.auto_overall_rating:
                        self.overall_risk_rating = self.auto_overall_rating
                    if self.auto_residual_rating:
                        self.residual_risk_rating = self.auto_residual_rating
                # Extend update_fields so computed values are persisted
                if update_fields is not None:
                    extra = [
                        'calculated_weighted_score', 'calculated_residual_score',
                        'auto_overall_rating', 'auto_residual_rating',
                        'overall_risk_rating', 'residual_risk_rating',
                    ]
                    kwargs['update_fields'] = list(set(update_fields) | set(extra))
        super().save(*args, **kwargs)


class AuditPlan(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Risk-Based Internal Audit Annual Plan (RBIAP).
    Updated to use FiscalYear lookup reference.
    """
    reference_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique plan reference number"
    )
    title = models.CharField(
        max_length=500,
        help_text="Descriptive title of the audit plan"
    )
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.PROTECT,
        related_name='audit_plans',
        help_text="Target fiscal year from lookup table"
    )
    
    PLAN_TYPE_CHOICES = [
        ('annual', 'Annual Plan'),
        ('special', 'Special Investigation Plan'),
        ('follow_up', 'Follow-up Plan'),
    ]
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE_CHOICES,
        default='annual',
        help_text="Type of audit plan"
    )
    
    audit_universe = models.ForeignKey(
        AuditUniverse,
        on_delete=models.CASCADE,
        related_name='audit_plans',
        help_text="Associated audit universe"
    )
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('management_review', 'Management Review'),
        ('committee_review', 'Committee Review'),
        ('approved', 'Approved'),
        ('implementation', 'Under Implementation'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the audit plan"
    )
    
    priority_areas = models.JSONField(
        default=list,
        blank=True,
        help_text="List of high-priority audit areas"
    )
    resource_allocation = models.JSONField(
        default=dict,
        blank=True,
        help_text="Auditor assignments and resource planning"
    )
    
    # Approval workflow tracking
    prepared_by = models.UUIDField(
        help_text="User ID of the preparing auditor"
    )
    reviewed_by_cia = models.UUIDField(
        null=True,
        blank=True,
        help_text="CIA user ID who reviewed the plan"
    )
    management_adopted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When management adopted the plan"
    )
    management_comments = models.TextField(
        blank=True,
        help_text="Management feedback on the plan"
    )
    committee_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When audit committee approved the plan"
    )
    committee_comments = models.TextField(
        blank=True,
        help_text="Audit committee feedback on the plan"
    )
    implementation_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When plan implementation began"
    )
    
    class Meta:
        db_table = 'grc_audit_plan'
        ordering = ['-fiscal_year__start_date']
        verbose_name = 'Audit Plan'
        verbose_name_plural = 'Audit Plans'
        
    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def get_workflow_context(self) -> dict:
        """
        Returns context variables for workflow assignee resolution (FIMS pattern).
        """
        return {
            "audit_plan_id": str(self.id),
            "prepared_by": str(self.prepared_by),
            "fiscal_year_id": str(self.fiscal_year_id),
            "plan_type": self.plan_type,
        }

    def get_workflow_metadata(self) -> dict:
        """
        Returns metadata for workflow plan display (FIMS pattern).
        Stored with the plan in Work Orchestration Service.
        """
        meta = {
            "entity_type": "audit_plan",
            "entity_id": str(self.id),
            "reference_number": self.reference_number,
            "title": self.title,
            "plan_type": self.plan_type,
            "fiscal_year": self.fiscal_year.year_code,
            "prepared_by": str(self.prepared_by),
            "status": self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, "audit_plan")

    def get_workflow_stages(self) -> list:
        """
        Returns inline stage definitions for the RBIAP approval workflow.
        4 stages: cia_review → management_review → committee_review → commission_noting.
        Mirrors the RBIAP Approval definition in GRC_AUDIT_SERVICE_DESIGN.md §6.1.
        """
        return [
            {
                "definition_key": "cia_review",
                "name": "CIA Review",
                "order": 0,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve",           "next_state": "completed"},
                    {"name": "return",  "label": "Return to Auditor",  "next_state": "rejected"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 72},
            },
            {
                "definition_key": "management_review",
                "name": "Management Review",
                "order": 1,
                "assignees": [],
                "actions": [
                    {"name": "adopt",           "label": "Adopt",           "next_state": "completed"},
                    {"name": "request_changes", "label": "Request Changes", "next_state": "pending"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 168},
            },
            {
                "definition_key": "committee_review",
                "name": "Audit Committee Review",
                "order": 2,
                "assignees": [],
                "actions": [
                    {"name": "approve",             "label": "Approve",             "next_state": "completed"},
                    {"name": "request_improvement", "label": "Request Improvement", "next_state": "pending"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 240},
            },
            {
                "definition_key": "commission_noting",
                "name": "Commission Noting",
                "order": 3,
                "assignees": [],
                "actions": [
                    {"name": "note", "label": "Note", "next_state": "completed"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 168},
            },
        ]


class AuditEngagement(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Individual audit assignments from the audit plan.
    """
    reference_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique engagement reference number"
    )
    audit_plan = models.ForeignKey(
        AuditPlan,
        on_delete=models.CASCADE,
        related_name='engagements',
        help_text="Parent audit plan"
    )
    auditable_entity = models.ForeignKey(
        AuditableEntity,
        on_delete=models.CASCADE,
        related_name='engagements',
        help_text="Entity being audited"
    )
    title = models.CharField(
        max_length=500,
        help_text="Descriptive title of the engagement"
    )
    
    ENGAGEMENT_TYPE_CHOICES = [
        ('planned', 'Planned Engagement'),
        ('unplanned', 'Unplanned Engagement'),
        ('special_investigation', 'Special Investigation'),
        ('follow_up', 'Follow-up Engagement'),
    ]
    engagement_type = models.CharField(
        max_length=25,
        choices=ENGAGEMENT_TYPE_CHOICES,
        default='planned',
        help_text="Type of audit engagement"
    )
    
    STATUS_CHOICES = [
        ('planning', 'Planning Phase'),
        ('fieldwork', 'Fieldwork Phase'),
        ('reporting', 'Reporting Phase'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planning',
        db_index=True,
        help_text="Current phase of the engagement"
    )
    
    lead_auditor = models.UUIDField(
        help_text="User ID of the lead auditor from IAM service"
    )
    audit_team = models.JSONField(
        default=list,
        blank=True,
        help_text="List of audit team member user IDs"
    )
    scope = models.TextField(
        blank=True,
        help_text="Detailed scope of the audit engagement"
    )
    objectives = models.JSONField(
        default=list,
        blank=True,
        help_text="List of audit objectives"
    )
    methodology = models.TextField(
        blank=True,
        help_text="Audit approach and methodology"
    )
    
    # Timeline tracking
    planned_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned start date for the engagement"
    )
    planned_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned completion date"
    )
    actual_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual start date"
    )
    actual_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual completion date"
    )
    
    # Meeting scheduling
    entry_meeting_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled entry meeting date and time"
    )
    exit_meeting_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled exit meeting date and time"
    )
    
    class Meta:
        db_table = 'grc_audit_engagement'
        ordering = ['-created_at']
        verbose_name = 'Audit Engagement'
        verbose_name_plural = 'Audit Engagements'
        
    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def get_workflow_context(self) -> dict:
        """
        Returns context variables for workflow assignee resolution (FIMS pattern).
        """
        return {
            "audit_engagement_id": str(self.id),
            "lead_auditor": str(self.lead_auditor),
            "audit_plan_id": str(self.audit_plan_id),
        }

    def get_workflow_metadata(self) -> dict:
        """
        Returns metadata for workflow plan display (FIMS pattern).
        Stored with the plan in Work Orchestration Service.
        """
        meta = {
            "entity_type": "audit_engagement",
            "entity_id": str(self.id),
            "reference_number": self.reference_number,
            "title": self.title,
            "engagement_type": self.engagement_type,
            "lead_auditor": str(self.lead_auditor),
            "status": self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, "audit_engagement")

    def get_workflow_stages(self) -> list:
        """
        Returns inline stage definitions for the engagement lifecycle workflow.
        3 phases: planning → fieldwork → reporting, then terminal completion.
        Matches STATUS_CHOICES and GRC_AUDIT_SERVICE_DESIGN.md §6.2 (simplified).
        """
        return [
            {
                "definition_key": "planning",
                "name": "Audit Planning",
                "order": 0,
                "assignees": ["{{lead_auditor}}"],
                "actions": [
                    {"name": "start_fieldwork", "label": "Start Fieldwork", "next_state": "completed"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 120},
            },
            {
                "definition_key": "fieldwork",
                "name": "Fieldwork",
                "order": 1,
                "assignees": ["{{lead_auditor}}"],
                "actions": [
                    {"name": "start_reporting", "label": "Start Reporting", "next_state": "completed"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 480},
            },
            {
                "definition_key": "reporting",
                "name": "Reporting",
                "order": 2,
                "assignees": ["{{lead_auditor}}"],
                "actions": [
                    {"name": "complete", "label": "Mark Complete", "next_state": "completed"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 240},
            },
        ]


class AuditFinding(TimestampedModel, StatusMixin):
    """
    Issues identified during audit engagements.
    Enhanced with lookup table references and quarter tracking.
    """
    engagement = models.ForeignKey(
        AuditEngagement,
        on_delete=models.CASCADE,
        related_name='findings',
        help_text="Parent audit engagement"
    )
    working_paper = models.ForeignKey(
        'WorkingPaper',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='findings',
        help_text="Source working paper for this finding"
    )
    reference_number = models.CharField(
        max_length=100,
        help_text="Finding reference (e.g., '125 of Q2 2023/2024')"
    )
    
    # Lookup table references for standardization
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.PROTECT,
        related_name='findings',
        help_text="Fiscal year when finding was identified"
    )
    quarter = models.ForeignKey(
        Quarter,
        on_delete=models.PROTECT,
        related_name='findings',
        help_text="Quarter when finding was identified"
    )
    finding_type = models.ForeignKey(
        FindingType,
        on_delete=models.PROTECT,
        related_name='findings',
        help_text="Type of finding from lookup table"
    )
    severity = models.ForeignKey(
        AuditSeverity,
        on_delete=models.PROTECT,
        related_name='findings',
        help_text="Severity level from lookup table"
    )
    
    title = models.CharField(
        max_length=500,
        help_text="Descriptive title of the finding"
    )
    condition = models.TextField(
        help_text="What was found - the actual situation observed"
    )
    criteria = models.TextField(
        help_text="What should be - the standard or expectation"
    )
    cause = models.TextField(
        help_text="Why it happened - root cause analysis"
    )
    effect = models.TextField(
        help_text="Impact and consequences of the finding"
    )
    
    risk_rating = models.ForeignKey(
        RiskRating,
        on_delete=models.PROTECT,
        related_name='findings',
        help_text="Associated risk level"
    )
    
    auditee_response = models.TextField(
        blank=True,
        help_text="Response from the auditee"
    )
    management_response = models.TextField(
        blank=True,
        help_text="Management's response to the finding"
    )
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('discussed', 'Discussed with Auditee'),
        ('final', 'Final'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the finding"
    )
    
    class Meta:
        db_table = 'grc_audit_finding'
        ordering = ['-created_at']
        unique_together = [['engagement', 'reference_number']]
        verbose_name = 'Audit Finding'
        verbose_name_plural = 'Audit Findings'
        
    def __str__(self):
        return f"{self.reference_number} - {self.title}"


class AuditRecommendation(TimestampedModel, StatusMixin):
    """
    Improvement suggestions from audit findings.
    """
    finding = models.ForeignKey(
        AuditFinding,
        on_delete=models.CASCADE,
        related_name='recommendations',
        help_text="Parent audit finding"
    )
    reference_number = models.CharField(
        max_length=100,
        help_text="Unique recommendation reference"
    )
    title = models.CharField(
        max_length=500,
        help_text="Descriptive title of the recommendation"
    )
    description = models.TextField(
        help_text="Detailed recommendation text"
    )
    
    PRIORITY_CHOICES = [
        ('high', 'High Priority'),
        ('medium', 'Medium Priority'),
        ('low', 'Low Priority'),
    ]
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        db_index=True,
        help_text="Implementation priority"
    )
    
    responsible_party = models.UUIDField(
        help_text="User ID of the person responsible for implementation"
    )
    agreed_action = models.TextField(
        help_text="Agreed corrective action plan"
    )
    target_date = models.DateField(
        help_text="Target implementation date"
    )
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('implemented', 'Implemented'),
        ('verified', 'Verified'),
        ('closed', 'Closed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        db_index=True,
        help_text="Current implementation status"
    )
    
    class Meta:
        db_table = 'grc_audit_recommendation'
        ordering = ['-created_at']
        unique_together = [['finding', 'reference_number']]
        verbose_name = 'Audit Recommendation'
        verbose_name_plural = 'Audit Recommendations'
        
    def __str__(self):
        return f"{self.reference_number} - {self.title}"


class ImplementationMonitoring(TimestampedModel, StatusMixin):
    """
    Tracks recommendation implementation follow-up.
    """
    recommendation = models.OneToOneField(
        AuditRecommendation,
        on_delete=models.CASCADE,
        related_name='monitoring',
        help_text="Recommendation being monitored"
    )
    
    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last implementation review"
    )
    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )
    implementation_progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Implementation progress percentage (0-100)"
    )
    progress_notes = models.TextField(
        blank=True,
        help_text="Notes on implementation progress"
    )
    evidence_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="List of supporting document references"
    )
    
    reviewed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the reviewer"
    )

    # Deadline enforcement fields (GAP 7 — SRS: 5-day response window)
    notification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the implementation list was shared with auditee"
    )
    response_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Auto-calculated: notification_sent_at + 5 business days"
    )
    auditee_responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the auditee submitted their response"
    )
    is_overdue = models.BooleanField(
        default=False,
        help_text="Whether the response deadline has passed without response"
    )
    escalated = models.BooleanField(
        default=False,
        help_text="Whether this record has been escalated to CIA"
    )
    
    class Meta:
        db_table = 'grc_implementation_monitoring'
        ordering = ['-last_review_date']
        verbose_name = 'Implementation Monitoring'
        verbose_name_plural = 'Implementation Monitoring'
        
    def __str__(self):
        return f"Monitoring: {self.recommendation.reference_number}"


class WorkingPaper(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Audit evidence and documentation.
    """
    engagement = models.ForeignKey(
        AuditEngagement,
        on_delete=models.CASCADE,
        related_name='working_papers',
        help_text="Parent audit engagement"
    )
    reference_number = models.CharField(
        max_length=100,
        help_text="Working paper reference number"
    )
    title = models.CharField(
        max_length=500,
        help_text="Descriptive title of the working paper"
    )
    
    PAPER_TYPE_CHOICES = [
        ('planning', 'Planning Documentation'),
        ('fieldwork', 'Fieldwork Documentation'),
        ('analysis', 'Analysis and Evaluation'),
        ('conclusion', 'Conclusions and Opinions'),
        ('other', 'Other Documentation'),
    ]
    paper_type = models.CharField(
        max_length=20,
        choices=PAPER_TYPE_CHOICES,
        help_text="Type of working paper"
    )
    
    # Document Storage - FIMS Integration
    # Primary working paper document stored in Document Records Service
    document_id = models.UUIDField(
        help_text="Primary document ID in Document Records Service"
    )
    
    # Supporting evidence documents (additional attachments)
    evidence_document_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of document IDs for supporting evidence in Document Records Service"
    )
    
    prepared_by = models.UUIDField(
        help_text="User ID of the preparer"
    )
    reviewed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the reviewer"
    )
    
    REVIEW_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
    ]
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Review status of the working paper"
    )
    
    review_comments = models.TextField(
        blank=True,
        help_text="Reviewer comments and feedback"
    )
    
    class Meta:
        db_table = 'grc_working_paper'
        ordering = ['-created_at']
        unique_together = [['engagement', 'reference_number']]
        verbose_name = 'Working Paper'
        verbose_name_plural = 'Working Papers'
        
    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def get_workflow_context(self) -> dict:
        """
        Returns context variables for workflow assignee resolution (FIMS pattern)
        """
        return {
            "prepared_by": str(self.prepared_by),
            "engagement_id": str(self.engagement_id) if hasattr(self, 'engagement_id') else str(self.engagement.id),
            "working_paper_id": str(self.id),
            "paper_type": self.paper_type,
            # Add more as needed for template assignees
        }

    def get_workflow_metadata(self) -> dict:
        """
        Returns metadata for workflow plan display (FIMS pattern).
        Stored with the plan in Work Orchestration Service.
        """
        meta = {
            "entity_type": "working_paper",
            "entity_id": str(self.id),
            "reference_number": self.reference_number,
            "title": self.title,
            "paper_type": self.paper_type,
            "engagement_id": str(self.engagement_id) if hasattr(self, 'engagement_id') else str(self.engagement.id),
            "prepared_by": str(self.prepared_by),
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'working_paper')

    def get_workflow_stages(self) -> list:
        """
        Returns inline stage definitions for Work Orchestration Service plan creation.

        Used when no pre-seeded template_id is available.
        Mirrors the YAML template in apps/core/workflows/workflows.yaml.

        Verified field names from WorkflowStartRequestSerializer > StageInputSerializer
        in work-orchestration-service.
        """
        return [
            {
                "definition_key": "working_paper_review",
                "name": "Working Paper Review",
                "order": 0,
                "assignees": [],               # Reviewer assigned at runtime
                "actions": [
                    {"name": "approve",         "label": "Approve",         "next_state": "completed"},
                    {"name": "reject",          "label": "Reject",          "next_state": "rejected"},
                    {"name": "request_changes", "label": "Request Changes", "next_state": "pending"},
                ],
                "metadata": {
                    "description": "Review and approve the working paper before finalisation.",
                },
                "form_schema": {
                    "fields": [
                        {"name": "comments", "type": "textarea", "required": False},
                    ]
                },
                "sla": {"targetHours": 48},
            },
            {
                "definition_key": "working_paper_approval",
                "name": "Working Paper Approval",
                "order": 1,
                "assignees": [],               # Head of Audit assigned at runtime
                "actions": [
                    {"name": "approve", "label": "Final Approve", "next_state": "completed"},
                    {"name": "reject",  "label": "Reject",        "next_state": "rejected"},
                ],
                "metadata": {
                    "description": "Final approval by Head of Audit.",
                },
                "form_schema": {
                    "fields": [
                        {"name": "comments", "type": "textarea", "required": False},
                    ]
                },
                "sla": {"targetHours": 24},
            },
        ]


class AuditReport(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Final audit engagement reports.
    """
    engagement = models.OneToOneField(
        AuditEngagement,
        on_delete=models.CASCADE,
        related_name='report',
        help_text="Parent audit engagement"
    )
    reference_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique report reference number"
    )
    
    REPORT_TYPE_CHOICES = [
        ('draft', 'Draft Report'),
        ('final', 'Final Report'),
    ]
    report_type = models.CharField(
        max_length=10,
        choices=REPORT_TYPE_CHOICES,
        default='draft',
        help_text="Type of report"
    )
    
    title = models.CharField(
        max_length=500,
        help_text="Report title"
    )
    executive_summary = models.TextField(
        help_text="Executive summary of the audit"
    )
    scope_and_objectives = models.TextField(
        help_text="Scope and objectives section"
    )
    methodology = models.TextField(
        help_text="Methodology section"
    )
    findings_summary = models.JSONField(
        default=list,
        blank=True,
        help_text="Summary of key findings"
    )
    recommendations_summary = models.JSONField(
        default=list,
        blank=True,
        help_text="Summary of key recommendations"
    )
    conclusion = models.TextField(
        help_text="Audit conclusion"
    )
    
    opinion = models.ForeignKey(
        AuditOpinion,
        on_delete=models.PROTECT,
        related_name='reports',
        help_text="Audit opinion from lookup table"
    )
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('distributed', 'Distributed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the report"
    )
    
    prepared_by = models.UUIDField(
        help_text="User ID of the report preparer"
    )
    reviewed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the reviewer"
    )
    approved_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the approver (CIA)"
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of approval"
    )
    
    distribution_list = models.JSONField(
        default=list,
        blank=True,
        help_text="List of report recipients"
    )
    distributed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when report was distributed"
    )
    document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Generated document reference from Document Service"
    )
    stamped_document_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to approved PDF with embedded CIA signature and QR code (GAP 9)"
    )

    class Meta:
        db_table = 'grc_audit_report'
        ordering = ['-created_at']
        verbose_name = 'Audit Report'
        verbose_name_plural = 'Audit Reports'
        
    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def get_workflow_context(self) -> dict:
        """
        Returns context variables for workflow assignee resolution (FIMS pattern).
        """
        return {
            "audit_report_id": str(self.id),
            "prepared_by": str(self.prepared_by),
            "engagement_id": str(self.engagement_id),
            "report_type": self.report_type,
        }

    def get_workflow_metadata(self) -> dict:
        """
        Returns metadata for workflow plan display (FIMS pattern).
        Stored with the plan in Work Orchestration Service.
        """
        meta = {
            "entity_type": "audit_report",
            "entity_id": str(self.id),
            "reference_number": self.reference_number,
            "title": self.title,
            "report_type": self.report_type,
            "prepared_by": str(self.prepared_by),
            "engagement_id": str(self.engagement_id),
            "status": self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, "audit_report")

    def get_workflow_stages(self) -> list:
        """
        Returns inline stage definitions for the audit report approval workflow.
        Stages: cia_review → approved (2-stage: review then distribution).
        """
        return [
            {
                "definition_key": "cia_review",
                "name": "CIA Review",
                "order": 0,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve", "next_state": "completed"},
                    {"name": "return",  "label": "Return",  "next_state": "rejected"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 72},
            },
            {
                "definition_key": "distribution",
                "name": "Report Distribution",
                "order": 1,
                "assignees": [],
                "actions": [
                    {"name": "distribute", "label": "Distribute", "next_state": "completed"},
                ],
                "form_schema": {
                    "fields": [{"name": "distribution_notes", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 48},
            },
        ]


class AuditMeeting(TimestampedModel, StatusMixin):
    """
    Audit meeting records — entry, pre-exit, audit-team, and exit meetings.
    SRS 1.8.3 Steps 14, 17, 20, 24.

    Tracks meeting scheduling, attendance, minutes, and action items
    for all meeting types during an audit engagement lifecycle.
    """
    engagement = models.ForeignKey(
        AuditEngagement,
        on_delete=models.CASCADE,
        related_name='meetings',
        help_text="Parent audit engagement"
    )
    reference_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique meeting reference (auto-generated)"
    )

    MEETING_TYPE_CHOICES = [
        ('entry', 'Entry Meeting'),
        ('pre_exit', 'Pre-Exit Meeting'),
        ('team', 'Audit Team Meeting'),
        ('exit', 'Exit Meeting'),
    ]
    meeting_type = models.CharField(
        max_length=20,
        choices=MEETING_TYPE_CHOICES,
        help_text="Type of meeting"
    )

    title = models.CharField(
        max_length=500,
        help_text="Meeting title"
    )
    scheduled_date = models.DateTimeField(
        help_text="Scheduled date and time of the meeting"
    )
    actual_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual date and time the meeting took place"
    )
    location = models.CharField(
        max_length=300,
        blank=True,
        default='',
        help_text="Meeting venue or location"
    )

    # Participants — stored as JSON list of attendee objects
    # Format: [{"user_id": "uuid-or-null", "name": "Full Name", "title": "Position",
    #            "role": "auditor|auditee|observer|management", "present": true}]
    attendees = models.JSONField(
        default=list,
        blank=True,
        help_text="List of meeting attendees with roles and attendance status"
    )

    agenda = models.TextField(
        blank=True,
        default='',
        help_text="Meeting agenda items"
    )
    minutes = models.TextField(
        blank=True,
        default='',
        help_text="Meeting minutes / proceedings"
    )
    key_discussions = models.TextField(
        blank=True,
        default='',
        help_text="Summary of key discussion points"
    )

    # Action items — stored as JSON list
    # Format: [{"description": "...", "responsible": "uuid", "responsible_name": "...",
    #            "due_date": "YYYY-MM-DD", "status": "open|completed"}]
    action_items = models.JSONField(
        default=list,
        blank=True,
        help_text="Action items arising from the meeting"
    )

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        db_index=True,
        help_text="Current meeting status"
    )

    organized_by = models.UUIDField(
        help_text="User ID of the meeting organizer (typically LA)"
    )

    minutes_document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Minutes document reference from Document Records Service"
    )
    attendance_document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Attendance sheet document reference from Document Records Service"
    )

    class Meta:
        db_table = 'grc_audit_meeting'
        ordering = ['-scheduled_date']
        verbose_name = 'Audit Meeting'
        verbose_name_plural = 'Audit Meetings'

    def __str__(self):
        return f"{self.reference_number} - {self.title}"


class QuarterlyAuditReport(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Quarterly Internal Audit Progress Report.

    Consolidates all engagement-level audit reports within a fiscal quarter
    into a single summary report submitted to audit committee / commission.
    SRS 1.8.3 — Quarterly reporting obligation.

    Reference format: QTR-{FY}-Q{num}-{seq:03d}  e.g. QTR-2024/2025-Q3-001
    Workflow: draft → cia_review → management_review → committee_review
              → improvement_required → approved → submitted_to_commission
    """

    # ── Identification ────────────────────────────────────────────────────────
    reference_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique report reference — QTR-{FY}-Q{num}-{seq} (auto-generated)"
    )
    title = models.CharField(
        max_length=500,
        help_text="Report title"
    )

    # ── Period ────────────────────────────────────────────────────────────────
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.PROTECT,
        related_name='quarterly_reports',
        help_text="Fiscal year this report covers"
    )
    quarter = models.ForeignKey(
        Quarter,
        on_delete=models.PROTECT,
        related_name='quarterly_reports',
        help_text="Fiscal quarter this report covers"
    )
    reporting_period_start = models.DateField(
        help_text="Start date of the reporting period"
    )
    reporting_period_end = models.DateField(
        help_text="End date of the reporting period"
    )

    # ── Narrative Sections ────────────────────────────────────────────────────
    executive_summary = models.TextField(
        blank=True,
        default='',
        help_text="High-level summary for senior management / committee"
    )
    audit_activities_summary = models.TextField(
        blank=True,
        default='',
        help_text="Summary of all audit activities conducted during the quarter"
    )
    findings_overview = models.TextField(
        blank=True,
        default='',
        help_text="Narrative overview of key findings across all engagements"
    )
    risk_themes = models.JSONField(
        default=list,
        blank=True,
        help_text="Identified risk themes/trends — [{\"theme\": \"...\", \"severity\": \"...\"}]"
    )
    recommendations_overview = models.TextField(
        blank=True,
        default='',
        help_text="Aggregated recommendations narrative"
    )
    implementation_status_summary = models.TextField(
        blank=True,
        default='',
        help_text="Status of prior recommendations implementation"
    )
    key_achievements = models.TextField(
        blank=True,
        default='',
        help_text="Significant achievements and milestones during the quarter"
    )
    challenges_and_constraints = models.TextField(
        blank=True,
        default='',
        help_text="Challenges, resource constraints, or obstacles encountered"
    )
    next_quarter_plan = models.TextField(
        blank=True,
        default='',
        help_text="Planned audit activities for the next quarter"
    )
    conclusion = models.TextField(
        blank=True,
        default='',
        help_text="Overall conclusion and audit opinion for the quarter"
    )
    management_notes = models.TextField(
        blank=True,
        default='',
        help_text="Management deliberation notes added during management_review stage"
    )
    committee_notes = models.TextField(
        blank=True,
        default='',
        help_text="Audit Committee review notes added during committee_review stage"
    )

    # ── Aggregated Statistics ─────────────────────────────────────────────────
    total_engagements = models.IntegerField(
        default=0,
        help_text="Total number of audit engagements covered this quarter"
    )
    total_findings = models.IntegerField(
        default=0,
        help_text="Total number of audit findings across all engagements"
    )
    critical_findings = models.IntegerField(
        default=0,
        help_text="Number of critical / high-severity findings"
    )
    total_recommendations = models.IntegerField(
        default=0,
        help_text="Total recommendations issued across all engagements"
    )
    implementation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage of prior recommendations implemented (0–100)"
    )

    # ── Structured Data ───────────────────────────────────────────────────────
    # Format: [{"plan_id": "...", "title": "...", "planned": 5, "completed": 4, "variance": -1}]
    planned_vs_actual = models.JSONField(
        default=dict,
        blank=True,
        help_text="Planned vs actual audit activities summary"
    )
    # Format: [{"severity": "high", "count": 3, "description": "..."}]
    findings_summary = models.JSONField(
        default=list,
        blank=True,
        help_text="Aggregated findings summary across all engagements"
    )
    # Format: [{"status": "implemented", "count": 10, "description": "..."}]
    recommendations_summary = models.JSONField(
        default=list,
        blank=True,
        help_text="Aggregated recommendations implementation status"
    )
    # Format: [{"metric": "...", "value": "...", "target": "..."}]
    resource_utilization = models.JSONField(
        default=dict,
        blank=True,
        help_text="Staffing days used, budget utilization summary"
    )

    # ── Audit Report Links (M2M to AuditReport, not AuditEngagement) ─────────
    engagement_reports = models.ManyToManyField(
        'AuditReport',
        blank=True,
        related_name='quarterly_reports',
        help_text="Individual audit reports (from engagements) consolidated in this quarterly report"
    )

    # ── Status ────────────────────────────────────────────────────────────────
    STATUS_CHOICES = [
        ('draft',                   'Draft'),
        ('cia_review',              'CIA Review'),
        ('management_review',       'Management Review'),
        ('committee_review',        'Audit Committee Review'),
        ('improvement_required',    'Improvement Required'),
        ('approved',                'Approved'),
        ('submitted_to_commission', 'Submitted to Commission'),
    ]
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current workflow status of the quarterly report"
    )

    # ── Signatories ───────────────────────────────────────────────────────────
    instructed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the CIA who instructed preparation of this report"
    )
    prepared_by = models.UUIDField(
        help_text="User ID of the report preparer (typically CIA or senior auditor)"
    )
    reviewed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the reviewer"
    )
    approved_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the approver"
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the report was formally approved"
    )
    submitted_to = models.CharField(
        max_length=300,
        blank=True,
        default='',
        help_text="Name / title of the committee or authority the report was submitted to"
    )
    submission_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the report was formally submitted"
    )

    # ── Document Reference ────────────────────────────────────────────────────
    document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Reference to uploaded report document in Document Records Service"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'grc_quarterly_audit_report'
        ordering = ['-reporting_period_end']
        unique_together = [['fiscal_year', 'quarter']]
        verbose_name = 'Quarterly Audit Report'
        verbose_name_plural = 'Quarterly Audit Reports'

    def __str__(self):
        return f"{self.reference_number} - {self.title}"


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 1 — Internal Audit Memo (SRS Req 10-14, 18)
# ═══════════════════════════════════════════════════════════════════════════════

class AuditMemo(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Internal Audit Memo — formal document prepared by an LA after CIA appointment.
    Goes through 3-stage approval: LA → CIA Review → DG Approval → Transmitted.
    SRS Requirements: 10, 11, 12, 13, 14, 18.
    """
    reference_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique memo reference (auto: MEMO-{plan_ref}-{seq})"
    )
    audit_plan = models.ForeignKey(
        AuditPlan,
        on_delete=models.CASCADE,
        related_name='memos',
        help_text="Parent audit plan (must be approved)"
    )
    auditable_entity = models.ForeignKey(
        AuditableEntity,
        on_delete=models.CASCADE,
        related_name='memos',
        help_text="Entity this memo addresses"
    )
    title = models.CharField(
        max_length=500,
        help_text="Memo title / subject line"
    )
    lead_auditor = models.UUIDField(
        help_text="Appointed Lead Auditor (user ID from IAM)"
    )
    audit_team = models.JSONField(
        default=list,
        blank=True,
        help_text="List of audit team member user IDs"
    )
    purpose = models.TextField(
        help_text="Why this audit is being conducted"
    )
    scope_summary = models.TextField(
        blank=True,
        help_text="Brief scope outline before full engagement plan"
    )
    timeline_start = models.DateField(
        null=True,
        blank=True,
        help_text="Planned audit start date"
    )
    timeline_end = models.DateField(
        null=True,
        blank=True,
        help_text="Planned audit end date"
    )

    # Approval tracking
    prepared_by = models.UUIDField(
        help_text="LA who prepared this memo"
    )
    reviewed_by_cia = models.UUIDField(
        null=True,
        blank=True,
        help_text="CIA user ID who reviewed the memo"
    )
    approved_by_dg = models.UUIDField(
        null=True,
        blank=True,
        help_text="DG user ID who approved the memo"
    )
    cia_review_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When CIA completed review"
    )
    dg_approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When DG approved the memo"
    )
    document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="DRS document UUID — set when memo is uploaded as a PDF document"
    )
    stamped_document_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to approved PDF with embedded CIA signature and QR code (GAP 9)"
    )

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('cia_review', 'CIA Review'),
        ('dg_review', 'DG Review'),
        ('approved', 'Approved'),
        ('transmitted', 'Transmitted to LA'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the audit memo"
    )

    class Meta:
        db_table = 'grc_audit_memo'
        ordering = ['-created_at']
        verbose_name = 'Audit Memo'
        verbose_name_plural = 'Audit Memos'

    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def get_workflow_context(self) -> dict:
        return {
            "audit_memo_id": str(self.id),
            "prepared_by": str(self.prepared_by),
            "lead_auditor": str(self.lead_auditor),
            "audit_plan_id": str(self.audit_plan_id),
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            "entity_type": "audit_memo",
            "entity_id": str(self.id),
            "reference_number": self.reference_number,
            "title": self.title,
            "lead_auditor": str(self.lead_auditor),
            "status": self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, "audit_memo")

    def get_workflow_stages(self) -> list:
        """
        3-stage approval: CIA Review → DG Approval → Transmission.
        """
        return [
            {
                "definition_key": "cia_review",
                "name": "CIA Review",
                "order": 0,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve", "next_state": "completed"},
                    {"name": "return", "label": "Return to LA", "next_state": "rejected"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 48},
            },
            {
                "definition_key": "dg_approval",
                "name": "DG Approval",
                "order": 1,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve", "next_state": "completed"},
                    {"name": "return", "label": "Return to CIA", "next_state": "rejected"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 72},
            },
            {
                "definition_key": "transmission",
                "name": "Transmit to Lead Auditor",
                "order": 2,
                "assignees": [],
                "actions": [
                    {"name": "transmit", "label": "Transmit", "next_state": "completed"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 24},
            },
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 2 — Declaration of Independence (SRS Req 16, 18, 38)
# ═══════════════════════════════════════════════════════════════════════════════

class DeclarationOfIndependence(TimestampedModel, StatusMixin):
    """
    Per-team-member, per-engagement declaration of no conflict of interest.
    Must be signed before engagement moves to fieldwork.
    SRS Requirements: 16, 18, 38.
    """
    audit_engagement = models.ForeignKey(
        AuditEngagement,
        on_delete=models.CASCADE,
        related_name='declarations',
        help_text="Engagement this declaration belongs to"
    )
    audit_memo = models.ForeignKey(
        AuditMemo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='declarations',
        help_text="Related audit memo (if exists)"
    )
    declarant_user_id = models.UUIDField(
        help_text="Team member user ID from IAM"
    )
    declarant_name = models.CharField(
        max_length=300,
        help_text="Cached display name of the declarant"
    )
    ROLE_CHOICES = [
        ('lead_auditor', 'Lead Auditor'),
        ('team_member', 'Team Member'),
    ]
    declarant_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Role in the audit team"
    )
    declaration_text = models.TextField(
        default=(
            "I hereby declare that I have no personal, financial, or professional "
            "interest that could influence, or could be perceived to influence, my "
            "objectivity and independence in the conduct of this audit engagement. "
            "I will immediately disclose any conflict of interest that may arise "
            "during the course of this audit."
        ),
        help_text="Standard declaration statement"
    )
    has_conflict = models.BooleanField(
        default=False,
        help_text="Whether the declarant has a conflict of interest"
    )
    conflict_details = models.TextField(
        blank=True,
        help_text="Details of conflict (required if has_conflict=True)"
    )
    is_signed = models.BooleanField(
        default=False,
        help_text="Whether the declaration has been signed/acknowledged"
    )
    signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the declaration was signed"
    )

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('signed', 'Signed'),
        ('waived', 'Waived'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Current status of the declaration"
    )
    document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="DRS document UUID for the signed declaration PDF (GAP 9)"
    )
    stamped_document_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to the signed + QR-stamped declaration PDF (GAP 9)"
    )

    class Meta:
        db_table = 'grc_declaration_of_independence'
        ordering = ['-created_at']
        unique_together = [['audit_engagement', 'declarant_user_id']]
        verbose_name = 'Declaration of Independence'
        verbose_name_plural = 'Declarations of Independence'

    def __str__(self):
        return f"Declaration: {self.declarant_name} - {self.audit_engagement.reference_number}"


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 3 — Audit Survey & Fraud Risk Assessment (SRS Req 19-21)
# ═══════════════════════════════════════════════════════════════════════════════

class AuditSurvey(TimestampedModel, StatusMixin):
    """
    Preliminary survey including Fraud Risk Assessment.
    Conducted before fieldwork to understand the control environment.
    SRS Requirements: 19, 20, 21.
    """
    audit_engagement = models.OneToOneField(
        AuditEngagement,
        on_delete=models.CASCADE,
        related_name='survey',
        help_text="Engagement this survey belongs to (one per engagement)"
    )
    surveyed_by = models.UUIDField(
        help_text="Team member who conducted the survey (user ID from IAM)"
    )
    survey_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the survey was conducted"
    )
    process_description = models.TextField(
        blank=True,
        help_text="Documented understanding of the audited process"
    )
    control_environment_notes = models.TextField(
        blank=True,
        help_text="Assessment of the overall control environment"
    )
    prior_audit_history = models.TextField(
        blank=True,
        help_text="Reference to previous audit results, if any"
    )
    fraud_risk_assessment = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Structured list of fraud risk factors assessed. "
            'Format: [{"risk_factor": "...", "likelihood": "low|medium|high", '
            '"impact": "low|medium|high", "notes": "..."}]'
        )
    )
    control_assessments = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of controls assessed for design adequacy. "
            'Format: [{"control_name": "...", "control_owner": "...", '
            '"design_adequate": true/false, "notes": "...", '
            '"test_strategy": "effectiveness"|"impact"}]'
        )
    )
    preliminary_findings = models.TextField(
        blank=True,
        help_text="Summary of preliminary findings from the survey"
    )

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Survey status"
    )

    class Meta:
        db_table = 'grc_audit_survey'
        ordering = ['-created_at']
        verbose_name = 'Audit Survey'
        verbose_name_plural = 'Audit Surveys'

    def __str__(self):
        return f"Survey: {self.audit_engagement.reference_number}"


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 4 — Risk and Control Matrix (SRS Req 22)
# ═══════════════════════════════════════════════════════════════════════════════

class RiskControlMatrix(TimestampedModel, StatusMixin):
    """
    Risk and Control Matrix (RCM) — parent container.
    One per engagement, maps risks to controls for audit scope prioritisation.
    SRS Requirements: 22 (1.8.3 Step 8).
    """
    audit_engagement = models.OneToOneField(
        AuditEngagement,
        on_delete=models.CASCADE,
        related_name='risk_control_matrix',
        help_text="Engagement this RCM belongs to"
    )
    prepared_by = models.UUIDField(
        help_text="Lead Auditor who prepared the matrix (user ID from IAM)"
    )

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Review'),
        ('approved', 'Approved'),
    ]
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="RCM status"
    )

    class Meta:
        db_table = 'grc_risk_control_matrix'
        ordering = ['-created_at']
        verbose_name = 'Risk Control Matrix'
        verbose_name_plural = 'Risk Control Matrices'

    def __str__(self):
        return f"RCM: {self.audit_engagement.reference_number}"


class RCMEntry(TimestampedModel):
    """
    Individual row in the Risk and Control Matrix.
    Each entry maps a risk to a control with adequacy assessment.
    """
    risk_control_matrix = models.ForeignKey(
        RiskControlMatrix,
        on_delete=models.CASCADE,
        related_name='entries',
        help_text="Parent RCM"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display ordering within the matrix"
    )
    process_area = models.CharField(
        max_length=300,
        help_text="Business process/area being assessed"
    )
    risk_description = models.TextField(
        help_text="What could go wrong in this process area"
    )
    risk_rating = models.ForeignKey(
        RiskRating,
        on_delete=models.PROTECT,
        related_name='rcm_entries',
        help_text="Risk rating from config lookups"
    )
    control_description = models.TextField(
        help_text="Existing control that mitigates the risk"
    )
    control_owner = models.CharField(
        max_length=300,
        help_text="Person/role responsible for this control"
    )
    CONTROL_TYPE_CHOICES = [
        ('preventive', 'Preventive'),
        ('detective', 'Detective'),
        ('corrective', 'Corrective'),
    ]
    control_type = models.CharField(
        max_length=15,
        choices=CONTROL_TYPE_CHOICES,
        help_text="Type of control"
    )
    design_adequate = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether the control design is adequate"
    )
    design_assessment_notes = models.TextField(
        blank=True,
        help_text="Notes on design adequacy assessment"
    )
    TEST_APPROACH_CHOICES = [
        ('effectiveness_test', 'Effectiveness Test'),
        ('impact_test', 'Impact Test'),
        ('not_applicable', 'Not Applicable'),
    ]
    test_approach = models.CharField(
        max_length=20,
        choices=TEST_APPROACH_CHOICES,
        default='effectiveness_test',
        help_text="Audit test approach for this control"
    )
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="Audit priority for this risk-control pair"
    )
    in_scope = models.BooleanField(
        default=True,
        help_text="Whether this item is included in audit scope"
    )
    exclusion_justification = models.TextField(
        blank=True,
        help_text="Justification for excluding from scope (required if in_scope=False)"
    )

    class Meta:
        db_table = 'grc_rcm_entry'
        ordering = ['risk_control_matrix', 'order']
        verbose_name = 'RCM Entry'
        verbose_name_plural = 'RCM Entries'

    def __str__(self):
        return f"RCM Entry: {self.process_area} (#{self.order})"


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 5 — Audit Program (SRS Req 22, 23; 1.8.3 Step 9)
# ═══════════════════════════════════════════════════════════════════════════════

class AuditProgram(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Formal Audit Program document — defines objectives, test procedures,
    sample sizes, and criteria. Approved by CIA before EN is sent.
    SRS Requirements: 22, 23.
    """
    audit_engagement = models.OneToOneField(
        AuditEngagement,
        on_delete=models.CASCADE,
        related_name='audit_program',
        help_text="Engagement this program belongs to"
    )
    reference_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique program reference (auto: PROG-{engagement_ref}-{seq})"
    )
    title = models.CharField(
        max_length=500,
        help_text="Audit program title"
    )
    risk_control_matrix = models.ForeignKey(
        RiskControlMatrix,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_programs',
        help_text="Linked RCM (optional)"
    )
    objectives = models.JSONField(
        default=list,
        blank=True,
        help_text="List of audit objectives"
    )
    procedures = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of test procedures linked to RCM entries. "
            'Format: [{"rcm_entry_id": "uuid", "procedure": "...", '
            '"sample_size": 25, "criteria": "..."}]'
        )
    )
    prepared_by = models.UUIDField(
        help_text="LA who prepared the program (user ID from IAM)"
    )
    reviewed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="IA reviewer (user ID from IAM)"
    )
    approved_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="CIA who approved (user ID from IAM)"
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the program was approved"
    )
    document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="DRS document UUID — set when program is uploaded as a PDF document"
    )
    stamped_document_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to approved PDF with embedded CIA signature and QR code (GAP 9)"
    )

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
    ]
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the audit program"
    )

    class Meta:
        db_table = 'grc_audit_program'
        ordering = ['-created_at']
        verbose_name = 'Audit Program'
        verbose_name_plural = 'Audit Programs'

    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def get_workflow_context(self) -> dict:
        return {
            "audit_program_id": str(self.id),
            "prepared_by": str(self.prepared_by),
            "audit_engagement_id": str(self.audit_engagement_id),
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            "entity_type": "audit_program",
            "entity_id": str(self.id),
            "reference_number": self.reference_number,
            "title": self.title,
            "prepared_by": str(self.prepared_by),
            "status": self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, "audit_program")

    def get_workflow_stages(self) -> list:
        """
        2-stage approval: IA Review → CIA Approval.
        """
        return [
            {
                "definition_key": "ia_review",
                "name": "IA Review",
                "order": 0,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve", "next_state": "completed"},
                    {"name": "return", "label": "Return to LA", "next_state": "rejected"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 48},
            },
            {
                "definition_key": "cia_approval",
                "name": "CIA Approval",
                "order": 1,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve", "next_state": "completed"},
                    {"name": "return", "label": "Return to IA", "next_state": "rejected"},
                ],
                "form_schema": {
                    "fields": [{"name": "comments", "type": "textarea", "required": False}]
                },
                "sla": {"targetHours": 72},
            },
        ]

