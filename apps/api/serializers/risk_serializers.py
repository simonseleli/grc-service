"""
DRF Serializers for Risk Management Module (RMQAU).
FK dual-field pattern: read nested (read_only=True), write UUID (write_only=True).
"""

from rest_framework import serializers
from apps.core.models.risk_entities import (
    # Group 7 — QA Training (defined first in models due to FK order)
    QATrainingSession,
    QATrainingAttendee,
    # Group 1 — Risk Champion & QA Appointment
    RiskChampion,
    RiskChampionAppointment,
    QualityAuditor,
    QualityAuditorAppointment,
    # Group 2 — Risk Assessment & Departmental Register
    RiskAssessmentSheet,
    DepartmentalRiskRegister,
    DeptRegisterEntry,
    # Group 3 — Institutional Register & RTAP
    InstitutionalRiskRegister,
    InstitutionalRiskEntry,
    RiskTreatmentActionPlan,
    RTAPItem,
    RTAPQuarterlyUpdate,
    # Group 4 — Quarterly Reporting
    QuarterlyPerformanceReport,
    ActivityReport,
    # Group 5 — QMS Audit
    QMSAuditProgram,
    QMSAuditPlan,
    QMSAuditTeamAssignment,
    AuditChecklist,
    QMSAuditReport,
    NonConformance,
    # Group 6 — Meeting & Workshop
    RiskMeeting,
    MeetingAttendance,
    # Group 8 — QMS Audit Support
    QMSAuditMeeting,
    QMSAuditTimetableEntry,
    # Group 9 — Knowledge Base & Surveys [SRS-FIX G-01, G-02]
    RiskKnowledgeBase,
    RiskSurvey,
    RiskSurveyQuestion,
    RiskSurveyResponse,
)
from .lookup_serializers import (
    FiscalYearSerializer,
    QuarterSerializer,
    RiskCategorySerializer,
    RiskLikelihoodSerializer,
    RiskImpactSerializer,
    RiskLevelSerializer,
    RiskSectorSerializer,
    StrategicObjectiveSerializer,
    ISOClauseSerializer,
    NonConformanceTypeSerializer,
)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — QA Training Management [GAP-02]
# ══════════════════════════════════════════════════════════════════════════════

class QATrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QATrainingSession
        fields = [
            'id', 'title', 'trainer_name', 'trainer_organization',
            'training_date', 'training_time', 'venue',
            'approval_status', 'approved_by', 'approval_date', 'notes', 'rejection_notes',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'approved_by': {'required': False},
            'approval_date': {'required': False},
            'rejection_notes': {'required': False},
        }


class QATrainingAttendeeSerializer(serializers.ModelSerializer):
    training_session = QATrainingSessionSerializer(read_only=True)
    training_session_id = serializers.UUIDField(write_only=True)
    quality_auditor_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = QATrainingAttendee
        fields = [
            'id', 'training_session', 'training_session_id',
            'quality_auditor_id', 'attended',
            'exam_score', 'exam_attempt_number', 'exam_date', 'passed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'exam_score': {'required': False},
            'exam_attempt_number': {'required': False},
            'exam_date': {'required': False},
            'passed': {'required': False},
        }


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — Risk Champion & QA Appointment
# ══════════════════════════════════════════════════════════════════════════════

class RiskChampionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskChampion
        fields = [
            'id', 'org_unit_id', 'org_unit_type', 'user_id', 'nominated_by',
            'term_start', 'term_end', 'notes',
            'qualifications', 'experience_summary', 'justification',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
        }


class RiskChampionAppointmentSerializer(serializers.ModelSerializer):
    risk_champion = RiskChampionSerializer(read_only=True)
    risk_champion_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RiskChampionAppointment
        fields = [
            'id', 'risk_champion', 'risk_champion_id', 'appointment_date',
            'document_id', 'stamped_document_url', 'remarks', 'status',
            # GAP-06: Dispatch tracking
            'dispatched', 'dispatch_date', 'dispatch_reference',
            'recipient_confirmed', 'recipient_confirmed_date',
            # GAP-14
            'rework_count',
            # GAP-17
            'last_review_comment', 'last_reviewed_by', 'last_reviewed_at',
            # WorkflowMixin fields
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'rework_count', 'last_reviewed_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'status': {'required': False},
            'dispatched': {'required': False},
            'dispatch_date': {'required': False},
            'dispatch_reference': {'required': False},
            'recipient_confirmed': {'required': False},
            'recipient_confirmed_date': {'required': False},
            'last_review_comment': {'required': False},
            'last_reviewed_by': {'required': False},
        }

    # Expose WorkflowMixin properties
    has_workflow = serializers.BooleanField(read_only=True)
    has_active_workflow = serializers.BooleanField(read_only=True)
    is_workflow_completed = serializers.BooleanField(read_only=True)


class QualityAuditorSerializer(serializers.ModelSerializer):
    training_session = QATrainingSessionSerializer(read_only=True)
    training_session_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = QualityAuditor
        fields = [
            'id', 'user_id', 'nominated_by', 'org_unit_id', 'org_unit_type',
            'exam_attempt', 'exam_score', 'is_certified', 'certification_date',
            'term_start', 'term_end', 'notes', 'qualifications', 'experience_summary',
            'training_session', 'training_session_id',
            'nomination_status',  # SRS-FIX G-08
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'exam_score': {'required': False},
            'certification_date': {'required': False},
            'nomination_status': {'required': False},
        }


class QualityAuditorAppointmentSerializer(serializers.ModelSerializer):
    quality_auditor = QualityAuditorSerializer(read_only=True)
    quality_auditor_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = QualityAuditorAppointment
        fields = [
            'id', 'quality_auditor', 'quality_auditor_id', 'appointment_date',
            'document_id', 'stamped_document_url', 'remarks', 'status',
            # GAP-06: Dispatch tracking
            'dispatched', 'dispatch_date', 'dispatch_reference',
            'recipient_confirmed', 'recipient_confirmed_date',
            # GAP-14
            'rework_count',
            # GAP-17
            'last_review_comment', 'last_reviewed_by', 'last_reviewed_at',
            # WorkflowMixin fields
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'rework_count', 'last_reviewed_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'status': {'required': False},
            'dispatched': {'required': False},
            'dispatch_date': {'required': False},
            'dispatch_reference': {'required': False},
            'recipient_confirmed': {'required': False},
            'recipient_confirmed_date': {'required': False},
            'last_review_comment': {'required': False},
            'last_reviewed_by': {'required': False},
        }

    has_workflow = serializers.BooleanField(read_only=True)
    has_active_workflow = serializers.BooleanField(read_only=True)
    is_workflow_completed = serializers.BooleanField(read_only=True)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — Risk Assessment & Departmental Register
# ══════════════════════════════════════════════════════════════════════════════

class RiskAssessmentSheetSerializer(serializers.ModelSerializer):
    # FK dual-fields
    risk_champion = RiskChampionSerializer(read_only=True)
    risk_champion_id = serializers.UUIDField(write_only=True)
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)
    risk_category = RiskCategorySerializer(read_only=True)
    risk_category_id = serializers.UUIDField(write_only=True)
    risk_sector = RiskSectorSerializer(read_only=True)
    risk_sector_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    strategic_objective = StrategicObjectiveSerializer(read_only=True)
    strategic_objective_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    likelihood = RiskLikelihoodSerializer(read_only=True)
    likelihood_id = serializers.UUIDField(write_only=True)
    impact = RiskImpactSerializer(read_only=True)
    impact_id = serializers.UUIDField(write_only=True)
    # Computed read-only
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
        fields = [
            'id',
            'risk_champion', 'risk_champion_id',
            'org_unit_id',
            'fiscal_year', 'fiscal_year_id',
            'risk_category', 'risk_category_id',
            'risk_sector', 'risk_sector_id',
            'strategic_objective', 'strategic_objective_id',
            'risk_title', 'risk_description',
            'causes', 'consequences', 'risk_indicator',
            'risk_owner', 'supporting_owners',
            'likelihood', 'likelihood_id',
            'impact', 'impact_id',
            'inherent_risk_score', 'inherent_risk_level',
            'existing_controls', 'control_assessment', 'further_action',
            'residual_likelihood', 'residual_likelihood_id',
            'residual_impact', 'residual_impact_id',
            'residual_risk_score', 'residual_risk_level',
            'references',
            'status', 'review_comments', 'rejected_at', 'resubmitted_at',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'inherent_risk_score', 'inherent_risk_level',
            'residual_risk_score', 'residual_risk_level',
            'rejected_at', 'resubmitted_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'existing_controls': {'required': False},
            'control_assessment': {'required': False},
            'further_action': {'required': False},
            'references': {'required': False},
            'status': {'required': False},
            'review_comments': {'required': False},
            'causes': {'required': False},
            'consequences': {'required': False},
            'risk_indicator': {'required': False},
            'supporting_owners': {'required': False},
        }


class DepartmentalRiskRegisterSerializer(serializers.ModelSerializer):
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)

    has_workflow = serializers.BooleanField(read_only=True)
    has_active_workflow = serializers.BooleanField(read_only=True)
    is_workflow_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = DepartmentalRiskRegister
        fields = [
            'id', 'org_unit_id', 'org_unit_type',
            'fiscal_year', 'fiscal_year_id',
            'submitted_by', 'submission_date',
            'rmqam_reviewer', 'review_date', 'remarks', 'status',
            # GAP-18
            'endorsed_by', 'endorsement_date', 'endorsement_document_id',
            # GAP-14
            'rework_count',
            # GAP-17
            'last_review_comment', 'last_reviewed_by', 'last_reviewed_at',
            # WorkflowMixin
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'rework_count', 'last_reviewed_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'status': {'required': False},
            'submitted_by': {'required': False},
            'submission_date': {'required': False},
            'rmqam_reviewer': {'required': False},
            'review_date': {'required': False},
            'endorsed_by': {'required': False},
            'endorsement_date': {'required': False},
            'endorsement_document_id': {'required': False},
            'last_review_comment': {'required': False},
            'last_reviewed_by': {'required': False},
        }


class DeptRegisterEntrySerializer(serializers.ModelSerializer):
    risk_sheet = RiskAssessmentSheetSerializer(read_only=True)
    risk_sheet_id = serializers.UUIDField(write_only=True)
    dept_register_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = DeptRegisterEntry
        fields = [
            'id', 'dept_register_id',
            'risk_sheet', 'risk_sheet_id', 'sort_order',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
        }


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — Institutional Register & RTAP
# ══════════════════════════════════════════════════════════════════════════════

class InstitutionalRiskRegisterSerializer(serializers.ModelSerializer):
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)

    has_workflow = serializers.BooleanField(read_only=True)
    has_active_workflow = serializers.BooleanField(read_only=True)
    is_workflow_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = InstitutionalRiskRegister
        fields = [
            'id', 'fiscal_year', 'fiscal_year_id',
            'prepared_by', 'preparation_date',
            'document_id', 'stamped_document_url', 'remarks', 'status',
            # GAP-03
            'committee_meeting_date', 'lsm_submission_date',
            # GAP-14
            'rework_count',
            # GAP-17
            'last_review_comment', 'last_reviewed_by', 'last_reviewed_at',
            # GAP-8: workshop + notifications
            'workshop_date', 'workshop_venue',
            'directors_notified_at', 'rcs_notified_at',
            # GAP-24: distribution
            'distributed_to_directorates_at', 'distribution_reference',
            # WorkflowMixin
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'rework_count', 'last_reviewed_at',
            'directors_notified_at', 'rcs_notified_at',
            'distributed_to_directorates_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'status': {'required': False},
            'preparation_date': {'required': False},
            'committee_meeting_date': {'required': False},
            'lsm_submission_date': {'required': False},
            'last_review_comment': {'required': False},
            'last_reviewed_by': {'required': False},
            'workshop_date': {'required': False},
            'workshop_venue': {'required': False},
            'distribution_reference': {'required': False},
        }


class InstitutionalRiskEntrySerializer(serializers.ModelSerializer):
    risk_sheet = RiskAssessmentSheetSerializer(read_only=True)
    risk_sheet_id = serializers.UUIDField(write_only=True)
    inst_register_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = InstitutionalRiskEntry
        fields = [
            'id', 'inst_register_id',
            'risk_sheet', 'risk_sheet_id',
            'risk_ranking', 'notes',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
        }

    def validate_risk_sheet_id(self, value):
        """SRS-FIX G-11 + G-06: Validate DRR membership and threshold."""
        # G-11: Risk must come from an approved Departmental Risk Register
        if not DeptRegisterEntry.objects.filter(
            risk_sheet_id=value, is_active=True
        ).exists():
            raise serializers.ValidationError(
                "Risk must be sourced from an active Departmental Risk Register "
                "before inclusion in the IRR."
            )
        # G-06: Risk must meet institutional threshold
        try:
            sheet = RiskAssessmentSheet.objects.select_related('residual_risk_level').get(pk=value)
        except RiskAssessmentSheet.DoesNotExist:
            raise serializers.ValidationError("Risk assessment sheet not found.")
        if sheet.residual_risk_level and hasattr(sheet.residual_risk_level, 'is_institutional_threshold'):
            if not sheet.residual_risk_level.is_institutional_threshold:
                raise serializers.ValidationError(
                    "Only risks at or above the institutional risk appetite threshold "
                    "may be added to the IRR."
                )
        return value


class RiskTreatmentActionPlanSerializer(serializers.ModelSerializer):
    inst_register = InstitutionalRiskRegisterSerializer(read_only=True)
    inst_register_id = serializers.UUIDField(write_only=True, source='inst_register.id', required=False)
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)

    has_workflow = serializers.BooleanField(read_only=True)
    has_active_workflow = serializers.BooleanField(read_only=True)
    is_workflow_completed = serializers.BooleanField(read_only=True)
    overall_progress = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = RiskTreatmentActionPlan
        fields = [
            'id', 'inst_register', 'inst_register_id',
            'fiscal_year', 'fiscal_year_id',
            'prepared_by',
            'document_id', 'stamped_document_url', 'remarks', 'status',
            'overall_progress',
            # GAP-03
            'committee_meeting_date', 'lsm_submission_date',
            # GAP-14
            'rework_count',
            # GAP-17
            'last_review_comment', 'last_reviewed_by', 'last_reviewed_at',
            # GAP-24: distribution
            'distributed_to_directorates_at', 'distribution_reference',
            # WorkflowMixin
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'overall_progress',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'rework_count', 'last_reviewed_at',
            'distributed_to_directorates_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'status': {'required': False},
            'committee_meeting_date': {'required': False},
            'lsm_submission_date': {'required': False},
            'last_review_comment': {'required': False},
            'last_reviewed_by': {'required': False},
            'distribution_reference': {'required': False},
        }


class RTAPItemSerializer(serializers.ModelSerializer):
    inst_entry = InstitutionalRiskEntrySerializer(read_only=True)
    inst_entry_id = serializers.UUIDField(write_only=True)
    rtap_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RTAPItem
        fields = [
            'id', 'rtap_id',
            'inst_entry', 'inst_entry_id',
            'treatment_description', 'responsible_officer',
            'target_date', 'status', 'sort_order',
            'kci', 'preventive_effectiveness', 'preventive_rating',
            'corrective_effectiveness', 'corrective_rating',
            'resources_required',
            'review_comments', 'returned_at', 'resubmitted_at',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'returned_at', 'resubmitted_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'status': {'required': False},
            'review_comments': {'required': False},
            'kci': {'required': False},
            'preventive_effectiveness': {'required': False},
            'preventive_rating': {'required': False},
            'corrective_effectiveness': {'required': False},
            'corrective_rating': {'required': False},
            'resources_required': {'required': False},
        }


class RTAPQuarterlyUpdateSerializer(serializers.ModelSerializer):
    quarter = QuarterSerializer(read_only=True)
    quarter_id = serializers.UUIDField(write_only=True)
    rtap_item_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RTAPQuarterlyUpdate
        fields = [
            'id', 'rtap_item_id',
            'quarter', 'quarter_id',
            'reported_by', 'update_date', 'status',
            'progress_notes', 'evidence',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
        }


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — Quarterly Reporting
# ══════════════════════════════════════════════════════════════════════════════

class QuarterlyPerformanceReportSerializer(serializers.ModelSerializer):
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)
    quarter = QuarterSerializer(read_only=True)
    quarter_id = serializers.UUIDField(write_only=True)

    has_workflow = serializers.BooleanField(read_only=True)
    has_active_workflow = serializers.BooleanField(read_only=True)
    is_workflow_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = QuarterlyPerformanceReport
        fields = [
            'id', 'fiscal_year', 'fiscal_year_id',
            'quarter', 'quarter_id',
            'prepared_by', 'preparation_date',
            # Snapshot metrics
            'total_risks', 'high_risks', 'medium_risks', 'low_risks',
            'rtap_completed', 'rtap_in_progress', 'rtap_not_started',
            'report_body',
            'document_id', 'stamped_document_url', 'status',
            # GAP-03
            'committee_meeting_date', 'lsm_submission_date',
            # GAP-12
            'iago_submitted', 'iago_submission_date', 'iago_reference',
            # GAP-14
            'rework_count',
            # GAP-17
            'last_review_comment', 'last_reviewed_by', 'last_reviewed_at',
            # WorkflowMixin
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'rework_count', 'last_reviewed_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'status': {'required': False},
            'preparation_date': {'required': False},
            'committee_meeting_date': {'required': False},
            'lsm_submission_date': {'required': False},
            'iago_submitted': {'required': False},
            'iago_submission_date': {'required': False},
            'iago_reference': {'required': False},
            'last_review_comment': {'required': False},
            'last_reviewed_by': {'required': False},
        }


class ActivityReportSerializer(serializers.ModelSerializer):
    inst_register = InstitutionalRiskRegisterSerializer(read_only=True)
    inst_register_id = serializers.UUIDField(write_only=True)
    quarter = QuarterSerializer(read_only=True)
    quarter_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ActivityReport
        fields = [
            'id', 'inst_register', 'inst_register_id',
            'quarter', 'quarter_id',
            'reported_by', 'submission_date',
            'activities_summary', 'issues_raised', 'recommendations',
            'attachments',
            # SRS-FIX G-03: DG noting
            'dg_noted', 'dg_noted_by', 'dg_noted_at',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'dg_noted', 'dg_noted_by', 'dg_noted_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'issues_raised': {'required': False},
            'recommendations': {'required': False},
            'attachments': {'required': False},
        }


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — QMS Audit
# ══════════════════════════════════════════════════════════════════════════════

class QMSAuditProgramSerializer(serializers.ModelSerializer):
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)

    has_workflow = serializers.BooleanField(read_only=True)
    has_active_workflow = serializers.BooleanField(read_only=True)
    is_workflow_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = QMSAuditProgram
        fields = [
            'id', 'fiscal_year', 'fiscal_year_id',
            'program_title', 'objective', 'scope',
            'prepared_by', 'approved_by', 'approval_date', 'status',
            # WorkflowMixin
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'approved_by': {'required': False},
            'approval_date': {'required': False},
            'status': {'required': False},
        }


class QMSAuditPlanSerializer(serializers.ModelSerializer):
    audit_program = QMSAuditProgramSerializer(read_only=True)
    audit_program_id = serializers.UUIDField(write_only=True)

    has_workflow = serializers.BooleanField(read_only=True)
    has_active_workflow = serializers.BooleanField(read_only=True)
    is_workflow_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = QMSAuditPlan
        fields = [
            'id', 'audit_program', 'audit_program_id',
            'plan_title', 'auditee_unit_id', 'lead_team_leader',
            'audit_start_date', 'audit_end_date', 'notification_date',
            'scope', 'criteria',
            'document_id', 'stamped_document_url', 'status',
            # GAP-04
            'nda_signed', 'nda_signed_date', 'nda_document_id',
            # GAP-10
            'timetable_agreed',
            # GAP-14
            'rework_count',
            # GAP-17
            'last_review_comment', 'last_reviewed_by', 'last_reviewed_at',
            # WorkflowMixin
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'has_workflow', 'has_active_workflow', 'is_workflow_completed',
            'rework_count', 'last_reviewed_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'status': {'required': False},
            'notification_date': {'required': False},
            'criteria': {'required': False},
            'nda_signed': {'required': False},
            'nda_signed_date': {'required': False},
            'nda_document_id': {'required': False},
            'timetable_agreed': {'required': False},
            'last_review_comment': {'required': False},
            'last_reviewed_by': {'required': False},
        }


class QMSAuditTeamAssignmentSerializer(serializers.ModelSerializer):
    audit_plan_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = QMSAuditTeamAssignment
        fields = [
            'id', 'audit_plan_id',
            'auditor_id', 'role',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
        }

    def validate(self, attrs):
        """SRS-FIX G-07: Enforce Rule E.2 — QA cannot audit own unit."""
        attrs = super().validate(attrs)
        auditor_id = attrs.get('auditor_id')
        audit_plan_id = attrs.get('audit_plan_id')
        if auditor_id and audit_plan_id:
            qa = QualityAuditor.objects.filter(user_id=auditor_id, is_active=True).first()
            plan = QMSAuditPlan.objects.filter(pk=audit_plan_id).first()
            if qa and plan and qa.org_unit_id == plan.auditee_unit_id:
                raise serializers.ValidationError(
                    "QA cannot audit their own unit (conflict of interest — Rule E.2)."
                )
        return attrs


class AuditChecklistSerializer(serializers.ModelSerializer):
    iso_clause = ISOClauseSerializer(read_only=True)
    iso_clause_id = serializers.UUIDField(write_only=True)
    audit_plan_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = AuditChecklist
        fields = [
            'id', 'audit_plan_id',
            'iso_clause', 'iso_clause_id',
            'auditor_id', 'conformity', 'findings_detail',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'findings_detail': {'required': False},
        }


class QMSAuditReportSerializer(serializers.ModelSerializer):
    audit_plan = QMSAuditPlanSerializer(read_only=True)
    audit_plan_id = serializers.UUIDField(write_only=True, source='audit_plan.id', required=False)

    class Meta:
        model = QMSAuditReport
        fields = [
            'id', 'audit_plan', 'audit_plan_id',
            'report_title', 'executive_summary', 'scope_summary',
            'tl_signed_by', 'tl_signed_at',
            'auditee_signed_by', 'auditee_signed_at',
            'document_id', 'stamped_document_url', 'status',
            'mrm_directives', 'mrm_directives_communicated_at',
            'rmqam_review_comments', 'returned_for_revision_at',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'tl_signed_at', 'auditee_signed_at',
            'mrm_directives_communicated_at', 'returned_for_revision_at',
        ]
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'stamped_document_url': {'required': False},
            'tl_signed_by': {'required': False},
            'auditee_signed_by': {'required': False},
            'status': {'required': False},
            'executive_summary': {'required': False},
            'scope_summary': {'required': False},
            'mrm_directives': {'required': False},
            'rmqam_review_comments': {'required': False},
        }


class NonConformanceSerializer(serializers.ModelSerializer):
    iso_clause = ISOClauseSerializer(read_only=True)
    iso_clause_id = serializers.UUIDField(write_only=True)
    nc_type = NonConformanceTypeSerializer(read_only=True)
    nc_type_id = serializers.UUIDField(write_only=True)
    audit_report_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = NonConformance
        fields = [
            'id', 'audit_report_id',
            'iso_clause', 'iso_clause_id',
            'nc_type', 'nc_type_id',
            'description', 'objective_evidence', 'raised_by',
            'corrective_action', 'responsible_officer', 'due_date',
            'status', 'closed_at', 'closure_notes',
            'dispute_reason', 'disputed_at', 'disputed_by',
            'last_reviewed_at',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'closed_at', 'disputed_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'corrective_action': {'required': False},
            'responsible_officer': {'required': False},
            'due_date': {'required': False},
            'closure_notes': {'required': False},
            'status': {'required': False},
            'dispute_reason': {'required': False},
            'disputed_by': {'required': False},
            'last_reviewed_at': {'required': False},
        }


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — Meeting & Workshop Management [GAP-01, GAP-08]
# ══════════════════════════════════════════════════════════════════════════════

class RiskMeetingSerializer(serializers.ModelSerializer):
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RiskMeeting
        fields = [
            'id', 'meeting_type', 'organized_by', 'org_unit_id',
            'fiscal_year', 'fiscal_year_id',
            'title', 'agenda', 'meeting_date', 'venue', 'virtual_link',
            'status', 'minutes', 'outcomes',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'org_unit_id': {'required': False},
            'agenda': {'required': False},
            'venue': {'required': False},
            'virtual_link': {'required': False},
            'minutes': {'required': False},
            'outcomes': {'required': False},
            'status': {'required': False},
        }


class MeetingAttendanceSerializer(serializers.ModelSerializer):
    meeting_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = MeetingAttendance
        fields = [
            'id', 'meeting_id',
            'user_id', 'attended',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
        }


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 8 — QMS Audit Support [GAP-05, GAP-10]
# ══════════════════════════════════════════════════════════════════════════════

class QMSAuditMeetingSerializer(serializers.ModelSerializer):
    audit_plan_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = QMSAuditMeeting
        fields = [
            'id', 'audit_plan_id',
            'meeting_type', 'meeting_date', 'minutes',
            'attendance', 'timetable_agreed', 'timetable_revised',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'minutes': {'required': False},
            'attendance': {'required': False},
            'timetable_agreed': {'required': False},
            'timetable_revised': {'required': False},
        }


class QMSAuditTimetableEntrySerializer(serializers.ModelSerializer):
    audit_plan_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = QMSAuditTimetableEntry
        fields = [
            'id', 'audit_plan_id',
            'date', 'start_time', 'end_time',
            'process_or_area', 'assigned_auditor', 'auditee_unit_id',
            'sort_order',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
        }


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 9 — Knowledge Base & Surveys [SRS-FIX G-01, G-02]
# ══════════════════════════════════════════════════════════════════════════════

class RiskKnowledgeBaseSerializer(serializers.ModelSerializer):
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = RiskKnowledgeBase
        fields = [
            'id', 'source_type', 'title', 'description',
            'fiscal_year', 'fiscal_year_id',
            'document_id', 'tags', 'contributed_by',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'document_id': {'required': False},
            'tags': {'required': False},
        }


class RiskSurveyQuestionSerializer(serializers.ModelSerializer):
    survey_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RiskSurveyQuestion
        fields = [
            'id', 'survey_id',
            'question_type', 'question_text', 'choices', 'sort_order',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'choices': {'required': False},
        }


class RiskSurveySerializer(serializers.ModelSerializer):
    fiscal_year = FiscalYearSerializer(read_only=True)
    fiscal_year_id = serializers.UUIDField(write_only=True)
    questions = RiskSurveyQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = RiskSurvey
        fields = [
            'id', 'title', 'description',
            'fiscal_year', 'fiscal_year_id',
            'org_unit_id', 'created_by_user', 'status',
            'opens_at', 'closes_at',
            'questions',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'description': {'required': False},
            'org_unit_id': {'required': False},
            'status': {'required': False},
            'opens_at': {'required': False},
            'closes_at': {'required': False},
        }


class RiskSurveyResponseSerializer(serializers.ModelSerializer):
    survey_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = RiskSurveyResponse
        fields = [
            'id', 'survey_id',
            'respondent_id', 'submitted_at', 'answers',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False},
            'submitted_at': {'required': False},
        }
