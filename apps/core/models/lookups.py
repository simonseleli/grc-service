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