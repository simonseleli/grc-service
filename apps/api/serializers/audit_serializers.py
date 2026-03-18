"""
DRF Serializers for GRC Service Main Entities
Following FIMS patterns for data serialization
"""

from rest_framework import serializers
from apps.core.models import (
    AuditUniverse, AuditableEntity, RiskAssessment,
    AuditPlan, AuditEngagement, AuditFinding,
    AuditRecommendation, AuditReport, ImplementationMonitoring, AuditeeFollowUpResponse,
    WorkingPaper, AuditMeeting, QuarterlyAuditReport,
    AuditMemo, DeclarationOfIndependence, AuditSurvey,
    RiskControlMatrix, RCMEntry, AuditProgram,
)
from .lookup_serializers import (
    FiscalYearSerializer, QuarterSerializer, 
    AuditSeveritySerializer, FindingTypeSerializer,
    RiskRatingSerializer, AuditOpinionSerializer
)


class AuditUniverseSerializer(serializers.ModelSerializer):
    """Serializer for AuditUniverse"""
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = AuditUniverse
        fields = [
            'id', 'description', 'status', 'fiscal_year', 'fiscal_year_id',
            'reviewed_by', 'approved_by', 'approved_at', 'workflow_plan_id',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditableEntitySerializer(serializers.ModelSerializer):
    """Serializer for AuditableEntity"""
    audit_universe = AuditUniverseSerializer(read_only=True)
    audit_universe_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = AuditableEntity
        fields = [
            'id', 'entity_type', 'name', 'code', 'description',
            'audit_universe', 'audit_universe_id', 'directorate_id',
            'unit_id', 'head_of_entity', 'metadata',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RiskAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for RiskAssessment"""
    auditable_entity = AuditableEntitySerializer(read_only=True)
    auditable_entity_id = serializers.UUIDField(write_only=True)
    overall_risk_rating = RiskRatingSerializer(read_only=True)
    overall_risk_rating_id = serializers.UUIDField(write_only=True, required=False)
    residual_risk_rating = RiskRatingSerializer(read_only=True)
    residual_risk_rating_id = serializers.UUIDField(write_only=True, required=False)
    auto_overall_rating = RiskRatingSerializer(read_only=True)
    auto_residual_rating = RiskRatingSerializer(read_only=True)
    # Frontend-facing aliases for the calculated score fields (GAP 6 — SRS auto-scoring)
    # The model stores them as calculated_weighted_score / calculated_residual_score;
    # the frontend and detail dialog expect auto_risk_score / auto_residual_score.
    auto_risk_score = serializers.DecimalField(
        source='calculated_weighted_score',
        max_digits=7, decimal_places=2,
        read_only=True, allow_null=True,
    )
    auto_residual_score = serializers.DecimalField(
        source='calculated_residual_score',
        max_digits=7, decimal_places=2,
        read_only=True, allow_null=True,
    )
    evidence_attachments = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        help_text="List of Document Records Service document UUIDs",
    )
    
    class Meta:
        model = RiskAssessment
        fields = [
            'id', 'auditable_entity', 'auditable_entity_id', 'assessment_period',
            'inherent_risk_score', 'control_effectiveness_score', 'financial_exposure_score',
            'compliance_risk_score', 'operational_impact_score', 'reputational_risk_score',
            'calculated_weighted_score', 'calculated_residual_score',
            'auto_risk_score', 'auto_residual_score',
            'overall_risk_rating', 'overall_risk_rating_id',
            'residual_risk_rating', 'residual_risk_rating_id',
            'auto_overall_rating', 'auto_residual_rating', 'rating_overridden',
            'justification', 'evidence_attachments', 'assessed_by', 'reviewed_by',
            'status', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at',
                           'calculated_weighted_score', 'calculated_residual_score',
                           'auto_risk_score', 'auto_residual_score',
                           'auto_overall_rating', 'auto_residual_rating']
        extra_kwargs = {
            'assessed_by': {'required': False}  # Set programmatically in view
        }


class AuditPlanSerializer(serializers.ModelSerializer):
    """Serializer for AuditPlan"""
    audit_universe = AuditUniverseSerializer(read_only=True)
    audit_universe_id = serializers.UUIDField(write_only=True)
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = AuditPlan
        fields = [
            'id', 'reference_number', 'title', 'plan_type', 'status',
            'audit_universe', 'audit_universe_id', 'fiscal_year', 'fiscal_year_id',
            'priority_areas', 'resource_allocation', 'prepared_by',
            'reviewed_by_cia', 'management_adopted_at', 'management_comments',
            'committee_approved_at', 'committee_comments', 'implementation_start_date',
            'workflow_plan_id', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},  # Auto-generated if blank
            'prepared_by': {'required': False}  # Set programmatically in view
        }


class AuditEngagementSerializer(serializers.ModelSerializer):
    """Serializer for AuditEngagement"""
    audit_plan = AuditPlanSerializer(read_only=True)
    audit_plan_id = serializers.UUIDField(write_only=True)
    auditable_entity = AuditableEntitySerializer(read_only=True)
    auditable_entity_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = AuditEngagement
        fields = [
            'id', 'reference_number', 'title', 'engagement_type', 'status',
            'audit_plan', 'audit_plan_id', 'auditable_entity', 'auditable_entity_id',
            'lead_auditor', 'audit_team', 'scope', 'objectives', 'methodology',
            'planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date',
            'entry_meeting_date', 'exit_meeting_date', 'workflow_plan_id',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},  # Auto-generated if blank
        }


class AuditFindingSerializer(serializers.ModelSerializer):
    """Serializer for AuditFinding"""
    engagement = AuditEngagementSerializer(read_only=True)
    engagement_id = serializers.UUIDField(write_only=True)
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)
    quarter = QuarterSerializer(read_only=True)
    quarter_id = serializers.UUIDField(write_only=True)
    severity = AuditSeveritySerializer(read_only=True)
    severity_id = serializers.UUIDField(write_only=True)
    finding_type = FindingTypeSerializer(read_only=True)
    finding_type_id = serializers.UUIDField(write_only=True)
    risk_rating = RiskRatingSerializer(read_only=True)
    risk_rating_id = serializers.UUIDField(write_only=True)
    # Optional WP link — uses same pattern as other FK _id fields (plain UUID, no FK validation;
    # validation that the WP belongs to this engagement is handled in the view)
    working_paper_id = serializers.UUIDField(write_only=False, required=False, allow_null=True)
    working_paper_reference = serializers.SerializerMethodField()

    def get_working_paper_reference(self, obj):
        """Return the WP reference number if a WP is linked."""
        if not obj.working_paper_id:
            return None
        try:
            return obj.working_paper.reference_number
        except Exception:
            return None

    class Meta:
        model = AuditFinding
        fields = [
            'id', 'reference_number', 'title', 'condition', 'criteria',
            'cause', 'effect', 'auditee_response', 'management_response', 'status',
            'engagement', 'engagement_id', 'fiscal_year', 'fiscal_year_id',
            'quarter', 'quarter_id', 'severity', 'severity_id',
            'finding_type', 'finding_type_id', 'risk_rating', 'risk_rating_id',
            'working_paper_id', 'working_paper_reference', 'is_active', 'created_at', 'updated_at',
            'discussed_at', 'finalized_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'discussed_at', 'finalized_at']
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},
        }


class AuditRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for AuditRecommendation"""
    finding = AuditFindingSerializer(read_only=True)
    finding_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = AuditRecommendation
        fields = [
            'id', 'reference_number', 'title', 'description', 'priority',
            'finding', 'finding_id', 'responsible_party', 'agreed_action',
            'target_date', 'status', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},
        }


class AuditeeFollowUpResponseSerializer(serializers.ModelSerializer):
    """Serializer for AuditeeFollowUpResponse — one row per review cycle."""
    monitoring_id = serializers.UUIDField(write_only=True)
    days_until_deadline = serializers.SerializerMethodField()

    class Meta:
        model = AuditeeFollowUpResponse
        fields = [
            'id', 'monitoring_id', 'cycle_number', 'status',
            'notified_at', 'response_deadline', 'days_until_deadline',
            'submitted_by', 'submitted_at',
            'implementation_progress', 'progress_notes', 'evidence_documents',
            'is_overdue', 'verified_by', 'verified_at', 'verification_notes',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'cycle_number', 'created_at', 'updated_at',
            'notified_at', 'days_until_deadline', 'is_overdue',
            'submitted_at', 'verified_at',
        ]

    def get_days_until_deadline(self, obj):
        """Return days until response deadline (negative = overdue)."""
        if not obj.response_deadline:
            return None
        from django.utils import timezone
        delta = obj.response_deadline - timezone.now()
        return delta.days


class ImplementationMonitoringSerializer(serializers.ModelSerializer):
    """Serializer for ImplementationMonitoring header (1:1 per recommendation)."""
    recommendation = AuditRecommendationSerializer(read_only=True)
    recommendation_id = serializers.UUIDField(write_only=True)
    days_until_deadline = serializers.SerializerMethodField()
    follow_up_responses = AuditeeFollowUpResponseSerializer(many=True, read_only=True)

    class Meta:
        model = ImplementationMonitoring
        fields = [
            'id', 'recommendation', 'recommendation_id', 'status',
            'last_review_date', 'next_review_date', 'latest_progress', 'reviewed_by',
            'notification_sent_at', 'response_deadline', 'auditee_responded_at',
            'is_overdue', 'escalated', 'days_until_deadline',
            'follow_up_responses',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'is_overdue',
            'response_deadline', 'days_until_deadline',
            'notification_sent_at', 'auditee_responded_at', 'escalated',
        ]

    def get_days_until_deadline(self, obj):
        """Return number of days until response deadline (negative = overdue)."""
        if not obj.response_deadline:
            return None
        from django.utils import timezone
        delta = obj.response_deadline - timezone.now()
        return delta.days


class AuditReportSerializer(serializers.ModelSerializer):
    """Serializer for AuditReport"""
    engagement = AuditEngagementSerializer(read_only=True)
    engagement_id = serializers.UUIDField(write_only=True)
    opinion = AuditOpinionSerializer(read_only=True)
    opinion_id = serializers.UUIDField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)

    class Meta:
        model = AuditReport
        fields = [
            'id', 'reference_number', 'report_type', 'report_type_display', 'title',
            'executive_summary', 'scope_and_objectives', 'methodology',
            'findings_summary', 'recommendations_summary', 'conclusion',
            'status', 'status_display', 'engagement', 'engagement_id',
            'opinion', 'opinion_id',
            'prepared_by', 'reviewed_by', 'approved_by', 'approval_date',
            'distribution_list', 'distributed_at', 'document_id', 'stamped_document_url',
            'workflow_plan_id', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'stamped_document_url']
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},
            'prepared_by': {'required': False},  # Set programmatically in view
            'reviewed_by': {'required': False},
            'approved_by': {'required': False},
            'approval_date': {'required': False},
            'distributed_at': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'workflow_plan_id': {'required': False},
        }


class WorkingPaperSerializer(serializers.ModelSerializer):
    """Serializer for WorkingPaper - FIMS Document Storage Integration"""
    engagement_title = serializers.CharField(source='engagement.title', read_only=True)
    paper_type_display = serializers.CharField(source='get_paper_type_display', read_only=True)
    review_status_display = serializers.CharField(source='get_review_status_display', read_only=True)
    
    # Document URL helpers (read-only computed fields)
    document_download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkingPaper
        fields = [
            'id', 'engagement', 'engagement_title', 'reference_number', 'title',
            'paper_type', 'paper_type_display', 'document_id', 'document_download_url',
            'evidence_document_ids', 'prepared_by', 'reviewed_by', 'review_status',
            'review_status_display', 'review_comments',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'is_active', 'created_by', 'modified_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'document_download_url',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
        ]
        extra_kwargs = {
            'prepared_by': {'required': False},  # Set programmatically in view
            'created_by': {'required': False},  # Set programmatically in view
            'modified_by': {'required': False},
            'review_comments': {'required': False},
            'reviewed_by': {'required': False},
            'document_id': {'required': False},  # Set after document creation
        }
    
    def get_document_download_url(self, obj):
        """Get download URL for primary document"""
        if obj.document_id:
            return f'/api/v1/documents/{obj.document_id}/download/'
        return None


class WorkingPaperListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing working papers - FIMS Document Storage Integration"""
    engagement_title = serializers.CharField(source='engagement.title', read_only=True)
    paper_type_display = serializers.CharField(source='get_paper_type_display', read_only=True)
    review_status_display = serializers.CharField(source='get_review_status_display', read_only=True)
    evidence_count = serializers.SerializerMethodField()
    has_document = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkingPaper
        fields = [
            'id', 'reference_number', 'title', 'engagement_title', 'paper_type',
            'paper_type_display', 'review_status', 'review_status_display',
            'prepared_by', 'reviewed_by', 'has_document', 'evidence_count', 'created_at'
        ]
    
    def get_evidence_count(self, obj):
        """Count supporting evidence documents"""
        return len(obj.evidence_document_ids) if obj.evidence_document_ids else 0
    
    def get_has_document(self, obj):
        """Check if primary document exists"""
        return obj.document_id is not None


class AuditMeetingSerializer(serializers.ModelSerializer):
    """Serializer for AuditMeeting (SRS 1.8.3 steps 14, 17, 20, 24)."""
    engagement_title = serializers.CharField(
        source='engagement.title', read_only=True
    )
    engagement_reference = serializers.CharField(
        source='engagement.reference_number', read_only=True
    )
    meeting_type_display = serializers.CharField(
        source='get_meeting_type_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    engagement_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = AuditMeeting
        fields = [
            'id', 'engagement', 'engagement_id', 'engagement_title',
            'engagement_reference', 'reference_number', 'meeting_type',
            'meeting_type_display', 'title', 'scheduled_date', 'actual_date',
            'location', 'attendees', 'agenda', 'minutes', 'key_discussions',
            'clarifications', 'agreed_observations',
            'action_items', 'status', 'status_display', 'organized_by',
            'minutes_document_id', 'attendance_document_id',
            'notification_sent', 'notification_date', 'draft_report_id',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'engagement', 'created_at', 'updated_at',
                           'notification_sent', 'notification_date', 'draft_report_id']
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},
            'organized_by': {'required': False},   # Set programmatically in view
            'minutes_document_id': {'required': False},
            'attendance_document_id': {'required': False},
        }


class QuarterlyAuditReportSerializer(serializers.ModelSerializer):
    """Serializer for QuarterlyAuditReport — quarterly progress reports to commission."""

    fiscal_year_id = serializers.UUIDField(write_only=True)
    quarter_id = serializers.UUIDField(write_only=True)

    fiscal_year_code = serializers.CharField(
        source='fiscal_year.year_code', read_only=True
    )
    fiscal_year_name = serializers.CharField(
        source='fiscal_year.name', read_only=True
    )
    quarter_name = serializers.CharField(
        source='quarter.name', read_only=True
    )
    quarter_number = serializers.IntegerField(
        source='quarter.quarter_number', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    engagement_report_ids = serializers.SerializerMethodField()
    engagement_report_count = serializers.SerializerMethodField()

    class Meta:
        model = QuarterlyAuditReport
        fields = [
            'id', 'reference_number', 'title',
            'fiscal_year', 'fiscal_year_id', 'fiscal_year_code', 'fiscal_year_name',
            'quarter', 'quarter_id', 'quarter_name', 'quarter_number',
            'reporting_period_start', 'reporting_period_end',
            # Narrative
            'executive_summary', 'audit_activities_summary',
            'findings_overview', 'risk_themes',
            'recommendations_overview', 'implementation_status_summary',
            'key_achievements', 'challenges_and_constraints',
            'next_quarter_plan', 'conclusion',
            'management_notes', 'committee_notes',
            # Aggregated statistics
            'total_engagements', 'total_findings', 'critical_findings',
            'total_recommendations', 'implementation_rate',
            # Structured JSON
            'planned_vs_actual', 'findings_summary',
            'recommendations_summary', 'resource_utilization',
            # M2M
            'engagement_report_ids', 'engagement_report_count',
            # Status
            'status', 'status_display',
            # Signatories
            'instructed_by', 'prepared_by', 'reviewed_by', 'approved_by',
            'approval_date', 'submitted_to', 'submission_date', 'document_id',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'fiscal_year', 'quarter', 'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},
            'prepared_by':      {'required': False},
            'reviewed_by':      {'required': False},
            'approved_by':      {'required': False},
            'instructed_by':    {'required': False},
            'document_id':      {'required': False},
            'submission_date':  {'required': False},
            'submitted_to':     {'required': False},
            'approval_date':    {'required': False},
        }

    def get_engagement_report_ids(self, obj):
        return [str(r.id) for r in obj.engagement_reports.all()]

    def get_engagement_report_count(self, obj):
        return obj.engagement_reports.count()


class QuarterlyAuditReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing quarterly reports."""

    fiscal_year_code = serializers.CharField(
        source='fiscal_year.year_code', read_only=True
    )
    quarter_name = serializers.CharField(
        source='quarter.name', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    engagement_report_count = serializers.SerializerMethodField()

    class Meta:
        model = QuarterlyAuditReport
        fields = [
            'id', 'reference_number', 'title',
            'fiscal_year_code', 'quarter_name',
            'reporting_period_start', 'reporting_period_end',
            'status', 'status_display',
            'total_engagements', 'total_findings', 'critical_findings',
            'implementation_rate',
            'prepared_by', 'engagement_report_count', 'created_at',
        ]

    def get_engagement_report_count(self, obj):
        return obj.engagement_reports.count()


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 1 — Audit Memo Serializers
# ═══════════════════════════════════════════════════════════════════════════════

class AuditMemoSerializer(serializers.ModelSerializer):
    """Full serializer for AuditMemo — detail and create/update."""
    audit_plan = AuditPlanSerializer(read_only=True)
    audit_plan_id = serializers.UUIDField(write_only=True)
    auditable_entity = AuditableEntitySerializer(read_only=True)
    auditable_entity_id = serializers.UUIDField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AuditMemo
        fields = [
            'id', 'reference_number', 'title', 'status', 'status_display',
            'audit_plan', 'audit_plan_id', 'auditable_entity', 'auditable_entity_id',
            'lead_auditor', 'audit_team', 'purpose', 'scope_summary',
            'timeline_start', 'timeline_end',
            'prepared_by', 'reviewed_by_cia', 'approved_by_dg',
            'cia_review_date', 'dg_approval_date',
            'document_id', 'stamped_document_url',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'stamped_document_url',
        ]
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},
            'prepared_by': {'required': False},
            'reviewed_by_cia': {'required': False},
            'approved_by_dg': {'required': False},
            'cia_review_date': {'required': False},
            'dg_approval_date': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
        }


class AuditMemoListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for Audit Memos."""
    audit_plan_reference = serializers.CharField(source='audit_plan.reference_number', read_only=True)
    entity_name = serializers.CharField(source='auditable_entity.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AuditMemo
        fields = [
            'id', 'reference_number', 'title', 'status', 'status_display',
            'audit_plan_reference', 'entity_name',
            'lead_auditor', 'timeline_start', 'timeline_end',
            'prepared_by', 'created_at',
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 2 — Declaration of Independence Serializers
# ═══════════════════════════════════════════════════════════════════════════════

class DeclarationOfIndependenceSerializer(serializers.ModelSerializer):
    """Full serializer for Declaration of Independence."""
    engagement_reference = serializers.CharField(
        source='audit_engagement.reference_number', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    audit_engagement_id = serializers.UUIDField(write_only=True)
    audit_memo_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = DeclarationOfIndependence
        fields = [
            'id', 'audit_engagement', 'audit_engagement_id', 'engagement_reference',
            'audit_memo', 'audit_memo_id',
            'declarant_user_id', 'declarant_name', 'declarant_role',
            'declaration_text', 'has_conflict', 'conflict_details',
            'is_signed', 'signed_at', 'status', 'status_display',
            'document_id', 'stamped_document_url',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'audit_engagement', 'audit_memo',
            'stamped_document_url',
            'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'signed_at': {'required': False},
            'conflict_details': {'required': False, 'allow_blank': True},
            'document_id': {'required': False},
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 3 — Audit Survey Serializers
# ═══════════════════════════════════════════════════════════════════════════════

class AuditSurveySerializer(serializers.ModelSerializer):
    """Serializer for Audit Survey / Preliminary Survey."""
    engagement_reference = serializers.CharField(
        source='audit_engagement.reference_number', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    audit_engagement_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = AuditSurvey
        fields = [
            'id', 'audit_engagement', 'audit_engagement_id', 'engagement_reference',
            'surveyed_by', 'survey_date',
            'process_description', 'control_environment_notes',
            'prior_audit_history', 'fraud_risk_assessment', 'control_assessments',
            'preliminary_findings', 'status', 'status_display',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'audit_engagement', 'created_at', 'updated_at']
        extra_kwargs = {
            'surveyed_by': {'required': False},
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 4 — Risk Control Matrix Serializers
# ═══════════════════════════════════════════════════════════════════════════════

class RCMEntrySerializer(serializers.ModelSerializer):
    """Serializer for a single RCM entry row."""
    risk_rating_detail = RiskRatingSerializer(source='risk_rating', read_only=True)
    risk_rating_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RCMEntry
        fields = [
            'id', 'risk_control_matrix', 'order', 'process_area',
            'risk_description', 'risk_rating', 'risk_rating_id', 'risk_rating_detail',
            'control_description', 'control_owner', 'control_type',
            'design_adequate', 'design_assessment_notes', 'test_approach',
            'priority', 'in_scope', 'exclusion_justification',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'risk_control_matrix', 'risk_rating', 'created_at', 'updated_at']


class RiskControlMatrixSerializer(serializers.ModelSerializer):
    """Serializer for RCM with nested entries."""
    engagement_reference = serializers.CharField(
        source='audit_engagement.reference_number', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    audit_engagement_id = serializers.UUIDField(write_only=True)
    entries = RCMEntrySerializer(many=True, read_only=True)
    entry_count = serializers.SerializerMethodField()

    class Meta:
        model = RiskControlMatrix
        fields = [
            'id', 'audit_engagement', 'audit_engagement_id', 'engagement_reference',
            'prepared_by', 'status', 'status_display',
            'entries', 'entry_count',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'audit_engagement', 'created_at', 'updated_at']
        extra_kwargs = {
            'prepared_by': {'required': False},
        }

    def get_entry_count(self, obj):
        return obj.entries.count()


# ═══════════════════════════════════════════════════════════════════════════════
# GAP 5 — Audit Program Serializers
# ═══════════════════════════════════════════════════════════════════════════════

class AuditProgramSerializer(serializers.ModelSerializer):
    """Full serializer for Audit Program."""
    engagement_reference = serializers.CharField(
        source='audit_engagement.reference_number', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    audit_engagement_id = serializers.UUIDField(write_only=True)
    risk_control_matrix_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = AuditProgram
        fields = [
            'id', 'audit_engagement', 'audit_engagement_id', 'engagement_reference',
            'reference_number', 'title',
            'risk_control_matrix', 'risk_control_matrix_id',
            'objectives', 'procedures', 'audit_scope',
            'prepared_by', 'reviewed_by', 'approved_by', 'approval_date',
            'document_id', 'stamped_document_url',
            'status', 'status_display',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'audit_engagement', 'risk_control_matrix', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'stamped_document_url',
        ]
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},
            'prepared_by': {'required': False},
            'reviewed_by': {'required': False},
            'approved_by': {'required': False},
            'approval_date': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
        }


class AuditProgramListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for Audit Programs."""
    engagement_reference = serializers.CharField(
        source='audit_engagement.reference_number', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AuditProgram
        fields = [
            'id', 'reference_number', 'title', 'engagement_reference',
            'status', 'status_display', 'prepared_by', 'created_at',
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# P2-GAP 1 — Engagement Notification Serializers (SRS Req 24, 25, 26)
# ═══════════════════════════════════════════════════════════════════════════════

class EngagementNotificationSerializer(serializers.ModelSerializer):
    """Full serializer for Engagement Notification."""
    engagement_reference = serializers.CharField(
        source='audit_engagement.reference_number', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    audit_engagement_id = serializers.UUIDField(write_only=True)
    audit_program_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        from apps.core.models import EngagementNotification
        model = EngagementNotification
        fields = [
            'id',
            'audit_engagement', 'audit_engagement_id', 'engagement_reference',
            'audit_program', 'audit_program_id',
            'reference_number',
            'notification_date',
            'audit_period_start', 'audit_period_end',
            'audit_team_snapshot',
            'scope_summary',
            'prepared_by',
            'approved_by_cia', 'cia_approval_date',
            'transmitted_at',
            'document_id', 'stamped_document_url',
            'status', 'status_display',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'audit_engagement', 'audit_program',
            'engagement_reference', 'status_display',
            'cia_approval_date', 'transmitted_at',
            'stamped_document_url',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'reference_number': {'required': False, 'allow_blank': True},
            'notification_date': {'required': False},
            'audit_team_snapshot': {'required': False},
            'scope_summary': {'required': False, 'allow_blank': True},
            'prepared_by': {'required': False},  # Set programmatically in view (defaults to logged-in user)
            'approved_by_cia': {'required': False},
            'document_id': {'required': False},
        }


class EngagementNotificationListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for Engagement Notifications."""
    engagement_reference = serializers.CharField(
        source='audit_engagement.reference_number', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        from apps.core.models import EngagementNotification
        model = EngagementNotification
        fields = [
            'id', 'reference_number', 'engagement_reference',
            'status', 'status_display',
            'prepared_by', 'notification_date',
            'audit_period_start', 'audit_period_end',
            'scope_summary',
            'workflow_plan_id', 'workflow_stage',
            'approved_by_cia', 'cia_approval_date',
            'transmitted_at', 'document_id', 'stamped_document_url',
            'created_at',
        ]