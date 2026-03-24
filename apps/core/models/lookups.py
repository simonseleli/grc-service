"""
Lookup table models for GRC Audit Service.
These models provide standardized values for forms and analytics.
Based on supervisor feedback for configurable lookup tables.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .base import BaseModel, TimestampedModel, StatusMixin


class FiscalYear(TimestampedModel, StatusMixin):
    """
    Fiscal year lookup table.
    Replaces free-text fiscal year fields for better analytics.
    """
    year_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique fiscal year code (e.g., '2024/2025')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the fiscal year"
    )
    start_date = models.DateField(
        help_text="First day of the fiscal year"
    )
    end_date = models.DateField(
        help_text="Last day of the fiscal year"
    )
    
    class Meta:
        db_table = 'grc_fiscal_year'
        ordering = ['-start_date']
        verbose_name = 'Fiscal Year'
        verbose_name_plural = 'Fiscal Years'
        
    def __str__(self):
        return f"{self.year_code} ({self.name})"
    
    @classmethod
    def get_current_fiscal_year(cls):
        """Get the currently active fiscal year."""
        from django.utils import timezone
        current_date = timezone.now().date()
        return cls.objects.filter(
            start_date__lte=current_date,
            end_date__gte=current_date,
            is_active=True
        ).first()


class Quarter(TimestampedModel, StatusMixin):
    """
    Quarterly periods within fiscal years.
    Enables quarter-specific audit finding tracking (e.g., "Q2 2023/2024").
    """
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name='quarters'
    )
    quarter_number = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Quarter number (1-4)"
    )
    name = models.CharField(
        max_length=10,
        help_text="Quarter name (e.g., 'Q1', 'Q2')"
    )
    start_date = models.DateField(
        help_text="First day of the quarter"
    )
    end_date = models.DateField(
        help_text="Last day of the quarter"
    )
    
    class Meta:
        db_table = 'grc_quarter'
        ordering = ['fiscal_year', 'quarter_number']
        unique_together = [['fiscal_year', 'quarter_number']]
        verbose_name = 'Quarter'
        verbose_name_plural = 'Quarters'
        
    def __str__(self):
        return f"{self.name} {self.fiscal_year.year_code}"
    
    @classmethod
    def get_current_quarter(cls):
        """Get the currently active quarter."""
        from django.utils import timezone
        current_date = timezone.now().date()
        return cls.objects.filter(
            start_date__lte=current_date,
            end_date__gte=current_date,
            is_active=True
        ).first()


class AuditSeverity(TimestampedModel, StatusMixin):
    """
    Standardized audit severity levels for findings.
    Configurable lookup table with UI styling support.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique severity code (e.g., 'critical', 'high')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the severity level"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of when to use this severity"
    )
    color_code = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Hex color code for UI display (e.g., '#FF0000')"
    )
    sort_order = models.IntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    
    class Meta:
        db_table = 'grc_audit_severity'
        ordering = ['sort_order', 'name']
        verbose_name = 'Audit Severity'
        verbose_name_plural = 'Audit Severities'
        
    def __str__(self):
        return f"{self.name} ({self.code})"


class FindingType(TimestampedModel, StatusMixin):
    """
    Standardized finding type classifications.
    Replaces free-text finding_type field for better analytics.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique type code (e.g., 'control_weakness')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the finding type"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of this finding type"
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Grouping category for related finding types"
    )
    
    class Meta:
        db_table = 'grc_finding_type'
        ordering = ['category', 'name']
        verbose_name = 'Finding Type'
        verbose_name_plural = 'Finding Types'
        
    def __str__(self):
        return f"{self.name} ({self.code})"


class RiskRating(TimestampedModel, StatusMixin):
    """
    Standardized risk rating levels.
    Used for risk assessments and control effectiveness ratings.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Risk rating code (e.g., 'high', 'medium', 'low')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the risk rating"
    )
    description = models.TextField(
        blank=True,
        help_text="Criteria for applying this risk rating"
    )
    numerical_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Numerical equivalent for calculations (e.g., 5.00 for high risk)"
    )
    color_code = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Hex color code for UI display"
    )
    sort_order = models.IntegerField(
        default=0,
        help_text="Display order"
    )
    min_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum weighted score threshold for this rating (inclusive)"
    )
    max_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum weighted score threshold for this rating (exclusive)"
    )
    
    class Meta:
        db_table = 'grc_risk_rating'
        ordering = ['sort_order', 'numerical_value']
        verbose_name = 'Risk Rating'
        verbose_name_plural = 'Risk Ratings'
        
    def __str__(self):
        return f"{self.name} ({self.numerical_value})"


class AuditOpinion(TimestampedModel, StatusMixin):
    """
    Standardized audit opinion types for reports.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Opinion code (e.g., 'satisfactory', 'needs_improvement')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the audit opinion"
    )
    description = models.TextField(
        blank=True,
        help_text="Criteria for issuing this opinion"
    )
    
    class Meta:
        db_table = 'grc_audit_opinion'
        ordering = ['name']
        verbose_name = 'Audit Opinion'
        verbose_name_plural = 'Audit Opinions'
        
    def __str__(self):
        return f"{self.name} ({self.code})"


# ── Legal Lookup Tables ─────────────────────────────────────────────────────


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

    def __str__(self):
        return self.name


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

    def __str__(self):
        return self.name


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

    def __str__(self):
        return self.name


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

    def __str__(self):
        return self.name


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

    def __str__(self):
        return f'{self.name} ({self.quorum_percentage}% quorum)'


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

    def __str__(self):
        return self.name


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

    def __str__(self):
        return self.name


# ── Risk Management Lookup Tables ────────────────────────────────────────────


class RiskCategory(TimestampedModel, StatusMixin):
    """Risk category classification for risk assessment sheets."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_category'
        ordering = ['sort_order', 'name']
        verbose_name = 'Risk Category'
        verbose_name_plural = 'Risk Categories'

    def __str__(self):
        return f"{self.name} ({self.code})"


class RiskLikelihood(TimestampedModel, StatusMixin):
    """Standardized risk likelihood scale (1–5)."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    numerical_value = models.DecimalField(max_digits=5, decimal_places=2)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_likelihood'
        ordering = ['sort_order', 'numerical_value']
        verbose_name = 'Risk Likelihood'
        verbose_name_plural = 'Risk Likelihoods'

    def __str__(self):
        return f"{self.name} ({self.numerical_value})"


class RiskImpact(TimestampedModel, StatusMixin):
    """Standardized risk impact scale (1–5)."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    numerical_value = models.DecimalField(max_digits=5, decimal_places=2)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_impact'
        ordering = ['sort_order', 'numerical_value']
        verbose_name = 'Risk Impact'
        verbose_name_plural = 'Risk Impacts'

    def __str__(self):
        return f"{self.name} ({self.numerical_value})"


class RiskLevel(TimestampedModel, StatusMixin):
    """Risk level thresholds for auto-classification of risk scores."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    min_score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    color_code = models.CharField(max_length=7, default='#6B7280')
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_level'
        ordering = ['sort_order', 'min_score']
        verbose_name = 'Risk Level'
        verbose_name_plural = 'Risk Levels'

    def __str__(self):
        return f"{self.name} ({self.min_score}–{self.max_score})"


class NonConformanceType(TimestampedModel, StatusMixin):
    """Classification of non-conformances for QMS audits."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_nc_type'
        ordering = ['sort_order', 'name']
        verbose_name = 'Non-Conformance Type'
        verbose_name_plural = 'Non-Conformance Types'

    def __str__(self):
        return f"{self.name} ({self.code})"


class ISOClause(TimestampedModel, StatusMixin):
    """ISO 9001:2015 clause hierarchy for QMS audit checklists."""
    code = models.CharField(max_length=50, unique=True)
    clause_number = models.CharField(max_length=20, help_text="e.g. '4.1', '7.1.5'")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parent_clause = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sub_clauses'
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_iso_clause'
        ordering = ['sort_order', 'clause_number']
        verbose_name = 'ISO Clause'
        verbose_name_plural = 'ISO Clauses'

    def __str__(self):
        return f"{self.clause_number} – {self.title}"


class RiskSector(TimestampedModel, StatusMixin):
    """Risk sector classification (Health, Services, Finance, etc.)"""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_sector'
        ordering = ['sort_order', 'name']
        verbose_name = 'Risk Sector'
        verbose_name_plural = 'Risk Sectors'

    def __str__(self):
        return f"{self.name} ({self.code})"


class StrategicObjective(TimestampedModel, StatusMixin):
    """Organization strategic objectives for risk alignment tracking."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_strategic_objective'
        ordering = ['sort_order', 'name']
        verbose_name = 'Strategic Objective'
        verbose_name_plural = 'Strategic Objectives'

    def __str__(self):
        return f"{self.code} — {self.name}"