"""
DRF Serializers for GRC Service Lookup Tables
Following FIMS patterns for data serialization
"""

from rest_framework import serializers
from apps.core.models import (
    FiscalYear, Quarter, AuditSeverity, FindingType, 
    RiskRating, AuditOpinion
)
from apps.core.models.lookups import (
    CourtLevel, LitigationUrgencyLevel, LitigationRiskLevel,
    MeetingMode, MeetingType, DirectivePriority, DirectiveCategory,
    RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
    NonConformanceType, ISOClause,
    RiskSector, StrategicObjective,
)


class FiscalYearSerializer(serializers.ModelSerializer):
    """Serializer for FiscalYear lookup table"""
    
    class Meta:
        model = FiscalYear
        fields = [
            'id', 'year_code', 'name', 'start_date', 'end_date', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class QuarterSerializer(serializers.ModelSerializer):
    """Serializer for Quarter lookup table"""
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Quarter
        fields = [
            'id', 'quarter_number', 'name', 'start_date', 'end_date',
            'fiscal_year', 'fiscal_year_id', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditSeveritySerializer(serializers.ModelSerializer):
    """Serializer for AuditSeverity lookup table"""
    
    class Meta:
        model = AuditSeverity
        fields = [
            'id', 'code', 'name', 'description', 'color_code', 
            'sort_order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FindingTypeSerializer(serializers.ModelSerializer):
    """Serializer for FindingType lookup table"""
    
    class Meta:
        model = FindingType
        fields = [
            'id', 'code', 'name', 'description', 'category',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RiskRatingSerializer(serializers.ModelSerializer):
    """Serializer for RiskRating lookup table"""
    
    class Meta:
        model = RiskRating
        fields = [
            'id', 'code', 'name', 'description', 'numerical_value',
            'color_code', 'sort_order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditOpinionSerializer(serializers.ModelSerializer):
    """Serializer for AuditOpinion lookup table"""
    
    class Meta:
        model = AuditOpinion
        fields = [
            'id', 'code', 'name', 'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Legal Lookup Serializers ─────────────────────────────────────────────────


class CourtLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourtLevel
        fields = ['id', 'code', 'name', 'description', 'order', 'is_active']
        read_only_fields = ['id']


class LitigationUrgencyLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LitigationUrgencyLevel
        fields = ['id', 'code', 'name', 'description', 'color_code', 'order', 'is_active']
        read_only_fields = ['id']


class LitigationRiskLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LitigationRiskLevel
        fields = ['id', 'code', 'name', 'description', 'color_code', 'order', 'is_active']
        read_only_fields = ['id']


class MeetingModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingMode
        fields = ['id', 'code', 'name', 'requires_venue_link', 'is_active']
        read_only_fields = ['id']


class MeetingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingType
        fields = ['id', 'code', 'name', 'quorum_percentage', 'description', 'is_active']
        read_only_fields = ['id']


class DirectivePrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectivePriority
        fields = ['id', 'code', 'name', 'color_code', 'order', 'is_active']
        read_only_fields = ['id']


class DirectiveCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectiveCategory
        fields = ['id', 'code', 'name', 'description', 'is_active']


# ── Risk Management Lookup Serializers ───────────────────────────────────────


class RiskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCategory
        fields = ['id', 'code', 'name', 'description', 'sort_order', 'is_active']
        read_only_fields = ['id']


class RiskLikelihoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskLikelihood
        fields = ['id', 'code', 'name', 'label', 'numerical_value', 'sort_order', 'is_active']
        read_only_fields = ['id']


class RiskImpactSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskImpact
        fields = ['id', 'code', 'name', 'label', 'numerical_value', 'sort_order', 'is_active']
        read_only_fields = ['id']


class RiskLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskLevel
        fields = ['id', 'code', 'name', 'min_score', 'max_score', 'color_code', 'sort_order', 'is_active']
        read_only_fields = ['id']


class NonConformanceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NonConformanceType
        fields = ['id', 'code', 'name', 'description', 'sort_order', 'is_active']
        read_only_fields = ['id']


class ISOClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ISOClause
        fields = ['id', 'code', 'clause_number', 'title', 'description', 'parent_clause', 'sort_order', 'is_active']
        read_only_fields = ['id']


class RiskSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskSector
        fields = ['id', 'code', 'name', 'description', 'sort_order', 'is_active']
        read_only_fields = ['id']


class StrategicObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategicObjective
        fields = ['id', 'code', 'name', 'description', 'sort_order', 'is_active']
        read_only_fields = ['id']
        read_only_fields = ['id']