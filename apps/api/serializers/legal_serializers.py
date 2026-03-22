"""
DRF Serializers for GRC Service Legal Module Entities
Following FIMS patterns for data serialization
"""

from rest_framework import serializers
from apps.core.models import (
    CommitteeType,
    GoverningBody,
    Member,
    SubmissionForDetermination,
    Meeting,
    MeetingAgenda,
    ConflictDeclaration,
    MeetingParticipant,
    MeetingDirective,
    Minutes,
    Resolution,
    CaseDefendant,
    FilingDefendant,
    ResponseDefendant,
    Hearing,
    HearingReport,
    SettlementDefendant,
    JudgmentDefendant,
    FinancialDefendant,
    LitigationDirective,
    TaskLitigation,
    CasePlaintiff,
    FilingPlaintiff,
    ResponsePlaintiff,
    SettlementPlaintiff,
    JudgmentPlaintiff,
    FinancialPlaintiff,
    AppealDefendant,
    AppealPlaintiff,
    LegalNotice,
    PublicDecision,
    LegalAuditLog,
)
from .lookup_serializers import (
    CourtLevelSerializer,
    LitigationUrgencyLevelSerializer,
    LitigationRiskLevelSerializer,
    MeetingModeSerializer,
    MeetingTypeSerializer,
    DirectivePrioritySerializer,
    DirectiveCategorySerializer,
)


# ── Governance Structure ──────────────────────────────────────────────────────

class CommitteeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommitteeType
        fields = ['id', 'code', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class GoverningBodySerializer(serializers.ModelSerializer):
    committee_type = CommitteeTypeSerializer(read_only=True)
    committee_type_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = GoverningBody
        fields = [
            'id', 'committee_type', 'committee_type_id', 'name',
            'composite_title', 'description', 'secretary_user_ids',
            'meeting_number_prefix', 'meeting_number_format',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GoverningBodyListSerializer(serializers.ModelSerializer):
    committee_type_name = serializers.CharField(source='committee_type.name', read_only=True)

    class Meta:
        model = GoverningBody
        fields = ['id', 'name', 'composite_title', 'committee_type_name', 'is_active']


class MemberSerializer(serializers.ModelSerializer):
    governing_body = GoverningBodyListSerializer(read_only=True)
    governing_body_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Member
        fields = [
            'id', 'governing_body', 'governing_body_id', 'user_id',
            'position', 'member_type', 'email', 'department',
            'joined_date', 'left_date', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Determinations & Approvals ────────────────────────────────────────────────

class SubmissionForDeterminationSerializer(serializers.ModelSerializer):
    target_body = GoverningBodyListSerializer(read_only=True)
    target_body_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = SubmissionForDetermination
        fields = [
            'id', 'title', 'description', 'submitter_user_id', 'submitter_dept',
            'submission_date', 'target_body', 'target_body_id',
            'supporting_documents', 'status', 'meeting',
            'outcome', 'outcome_notes', 'determination_date',
            'directives_created', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Meeting Governance ────────────────────────────────────────────────────────

class MeetingSerializer(serializers.ModelSerializer):
    governing_body = GoverningBodyListSerializer(read_only=True)
    governing_body_id = serializers.UUIDField(write_only=True)
    meeting_mode = MeetingModeSerializer(read_only=True)
    meeting_mode_id = serializers.UUIDField(write_only=True)
    meeting_type = MeetingTypeSerializer(read_only=True)
    meeting_type_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Meeting
        fields = [
            'id', 'governing_body', 'governing_body_id',
            'meeting_number', 'title', 'location',
            'meeting_mode', 'meeting_mode_id', 'venue_link',
            'scheduled_start', 'scheduled_end',
            'meeting_type', 'meeting_type_id', 'agenda_summary',
            'status', 'secretary_id',
            'total_member_count', 'rsvp_yes_count', 'rsvp_no_count',
            'rsvp_pending_count', 'quorum_met', 'quorum_percentage',
            'reschedule_reason',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'meeting_number', 'workflow_plan_id', 'workflow_stage',
                           'created_at', 'updated_at']


class MeetingListSerializer(serializers.ModelSerializer):
    governing_body_name = serializers.CharField(source='governing_body.name', read_only=True)

    class Meta:
        model = Meeting
        fields = [
            'id', 'meeting_number', 'title', 'governing_body_name',
            'scheduled_start', 'scheduled_end', 'status', 'quorum_met',
        ]


class MeetingAgendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingAgenda
        fields = [
            'id', 'meeting', 'submission', 'source_directive', 'order', 'title', 'description',
            'documents', 'outcome', 'outcome_notes', 'outcome_recorded_at',
            'directives_created', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConflictDeclarationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConflictDeclaration
        fields = [
            'id', 'agenda_item', 'member_user_id', 'declared_at',
            'reason', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'declared_at', 'created_at', 'updated_at']


class MeetingParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingParticipant
        fields = [
            'id', 'meeting', 'user_id', 'role', 'invitation_status',
            'decline_reason', 'attendance_marked', 'responded_at',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MeetingDirectiveSerializer(serializers.ModelSerializer):
    directive_priority = DirectivePrioritySerializer(read_only=True)
    directive_priority_id = serializers.UUIDField(write_only=True)
    directive_category = DirectiveCategorySerializer(read_only=True)
    directive_category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = MeetingDirective
        fields = [
            'id', 'meeting', 'agenda_item',
            'directive_priority', 'directive_priority_id',
            'directive_category', 'directive_category_id',
            'description', 'assigned_org_unit', 'assigned_user_id',
            'due_date', 'status', 'completion_summary', 'completion_date',
            'evidence_document_id', 'fully_closed',
            'finally_closed_in_meeting', 'finally_closed_at', 'finally_closed_by',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MinutesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Minutes
        fields = [
            'id', 'meeting', 'title', 'content', 'attachments',
            'status', 'approved_by', 'approval_date',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'workflow_plan_id', 'workflow_stage',
                           'created_at', 'updated_at']


class ResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resolution
        fields = [
            'id', 'meeting', 'agenda_item', 'resolution_text',
            'date_adopted', 'status', 'responsible_person_id',
            'effective_date', 'attachments',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Litigation — Defendant Cases ──────────────────────────────────────────────

class CaseDefendantSerializer(serializers.ModelSerializer):
    court_level = CourtLevelSerializer(read_only=True)
    court_level_id = serializers.UUIDField(write_only=True)
    urgency_level = LitigationUrgencyLevelSerializer(read_only=True)
    urgency_level_id = serializers.UUIDField(write_only=True)
    risk_level = LitigationRiskLevelSerializer(read_only=True)
    risk_level_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = CaseDefendant
        fields = [
            'id', 'reference_number', 'court_case_number', 'court_registry',
            'court_level', 'court_level_id', 'service_date',
            'plaintiffs', 'plaintiff_advocate', 'claim_amount',
            'nature_of_claim', 'department_affected',
            'urgency_level', 'urgency_level_id',
            'risk_level', 'risk_level_id',
            'initiation_documents', 'status', 'dg_review_status',
            'assigned_legal_officer_ids', 'assigned_legal_manager_id',
            'next_hearing_date',
            'is_archived', 'archived_at', 'archived_by',
            'hold_reason',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'reference_number', 'workflow_plan_id', 'workflow_stage',
                           'is_archived', 'archived_at', 'archived_by',
                           'created_at', 'updated_at']


class CaseDefendantListSerializer(serializers.ModelSerializer):
    court_level_name = serializers.CharField(source='court_level.name', read_only=True)

    class Meta:
        model = CaseDefendant
        fields = [
            'id', 'reference_number', 'court_case_number', 'court_level_name',
            'claim_amount', 'status', 'next_hearing_date', 'is_archived',
        ]


class FilingDefendantSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilingDefendant
        fields = [
            'id', 'case_defendant', 'filing_type', 'title',
            'document_id', 'stamped_document_url', 'version', 'status',
            'submitted_by_user_id', 'approval_chain',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'stamped_document_url', 'workflow_plan_id', 'workflow_stage',
                           'created_at', 'updated_at']


class ResponseDefendantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseDefendant
        fields = [
            'id', 'case_defendant', 'response_type', 'received_date',
            'document_id', 'description',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class HearingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hearing
        fields = [
            'id', 'case_defendant', 'case_plaintiff', 'hearing_date',
            'court', 'judge', 'notes', 'status',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class HearingReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HearingReport
        fields = [
            'id', 'hearing', 'report_type', 'summary', 'remarks',
            'next_hearing_date', 'attachment_id',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SettlementDefendantSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettlementDefendant
        fields = [
            'id', 'case_defendant', 'settlement_date', 'terms',
            'payment_amount', 'agreement_document_id', 'stamped_document_url', 'status',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'stamped_document_url', 'workflow_plan_id', 'workflow_stage',
                           'created_at', 'updated_at']


class JudgmentDefendantSerializer(serializers.ModelSerializer):
    class Meta:
        model = JudgmentDefendant
        fields = [
            'id', 'case_defendant', 'judgment_date', 'outcome',
            'amount_awarded', 'legal_costs_awarded', 'other_costs',
            'document_id', 'stamped_document_url', 'remarks',
            'dg_decision', 'appeal_due_date', 'appeal_filing', 'appeal_task',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'stamped_document_url', 'workflow_plan_id', 'workflow_stage',
                           'created_at', 'updated_at']


class FinancialDefendantSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialDefendant
        fields = [
            'id', 'case_defendant', 'claim_amount', 'legal_costs_incurred',
            'costs_awarded', 'other_costs', 'recoveries', 'payments',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LitigationDirectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LitigationDirective
        fields = [
            'id', 'case_defendant', 'case_plaintiff',
            'issued_by_user_id', 'issue_date', 'instruction',
            'due_date', 'status', 'completion_summary', 'completion_date',
            'attachments', 'requires_dg_approval_for_closure',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaskLitigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskLitigation
        fields = [
            'id', 'case_defendant', 'case_plaintiff',
            'title', 'assigned_to_user_id', 'due_date',
            'status', 'priority', 'related_entity_type', 'related_entity_id',
            'auto_created',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Litigation — Plaintiff Cases ──────────────────────────────────────────────

class CasePlaintiffSerializer(serializers.ModelSerializer):
    court_level = CourtLevelSerializer(read_only=True)
    court_level_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    urgency_level = LitigationUrgencyLevelSerializer(read_only=True)
    urgency_level_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    risk_level = LitigationRiskLevelSerializer(read_only=True)
    risk_level_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = CasePlaintiff
        fields = [
            'id', 'reference_number', 'registration_type',
            'reporting_department', 'nature_of_breach',
            'respondent_name', 'respondent_type',
            'estimated_claim_amount', 'description',
            'court_level', 'court_level_id',
            'urgency_level', 'urgency_level_id',
            'risk_level', 'risk_level_id',
            'initiation_documents', 'status', 'dg_review_status',
            'assigned_legal_officer_ids', 'assigned_legal_manager_id',
            'next_hearing_date',
            'is_archived', 'archived_at', 'archived_by',
            'hold_reason',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'reference_number', 'workflow_plan_id', 'workflow_stage',
                           'is_archived', 'archived_at', 'archived_by',
                           'created_at', 'updated_at']


class CasePlaintiffListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CasePlaintiff
        fields = [
            'id', 'reference_number', 'respondent_name',
            'estimated_claim_amount', 'status', 'next_hearing_date', 'is_archived',
        ]


class FilingPlaintiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilingPlaintiff
        fields = [
            'id', 'case_plaintiff', 'filing_type', 'title',
            'document_id', 'stamped_document_url', 'version', 'status',
            'submitted_by_user_id', 'approval_chain',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'stamped_document_url', 'workflow_plan_id', 'workflow_stage',
                           'created_at', 'updated_at']


class ResponsePlaintiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponsePlaintiff
        fields = [
            'id', 'case_plaintiff', 'response_type', 'received_date',
            'document_id', 'description',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SettlementPlaintiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettlementPlaintiff
        fields = [
            'id', 'case_plaintiff', 'settlement_date', 'terms',
            'payment_amount', 'agreement_document_id', 'stamped_document_url', 'status',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'stamped_document_url', 'workflow_plan_id', 'workflow_stage',
                           'created_at', 'updated_at']


class JudgmentPlaintiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = JudgmentPlaintiff
        fields = [
            'id', 'case_plaintiff', 'judgment_date', 'outcome',
            'amount_awarded', 'legal_costs_awarded', 'other_costs',
            'document_id', 'stamped_document_url', 'remarks',
            'dg_decision', 'appeal_due_date', 'appeal_filing', 'appeal_task',
            'workflow_plan_id', 'workflow_stage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'stamped_document_url', 'workflow_plan_id', 'workflow_stage',
                           'created_at', 'updated_at']


class FinancialPlaintiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialPlaintiff
        fields = [
            'id', 'case_plaintiff', 'claim_amount', 'legal_costs_incurred',
            'costs_awarded', 'other_costs', 'recoveries', 'payments',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Appeals ───────────────────────────────────────────────────────────────────

class AppealDefendantSerializer(serializers.ModelSerializer):
    court_level = CourtLevelSerializer(read_only=True)
    court_level_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = AppealDefendant
        fields = [
            'id', 'judgment', 'appeal_date', 'grounds',
            'court_level', 'court_level_id',
            'status', 'outcome', 'outcome_date',
            'document_id', 'remarks',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppealPlaintiffSerializer(serializers.ModelSerializer):
    court_level = CourtLevelSerializer(read_only=True)
    court_level_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = AppealPlaintiff
        fields = [
            'id', 'judgment', 'appeal_date', 'grounds',
            'court_level', 'court_level_id',
            'status', 'outcome', 'outcome_date',
            'document_id', 'remarks',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Legal Notices ─────────────────────────────────────────────────────────────

class LegalNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalNotice
        fields = [
            'id', 'related_case_defendant', 'related_case_plaintiff',
            'notice_type', 'title', 'content', 'issued_date',
            'served_date', 'recipient_info', 'document_id',
            'status', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Public Decisions / Public Register (GAP-11) ──────────────────────────────

class PublicDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicDecision
        fields = [
            'id', 'title', 'meeting', 'body_text', 'decision_text',
            'decision_date', 'status', 'published_date',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'published_date', 'created_at', 'updated_at']


# ── Activity Log (GAP-13) ─────────────────────────────────────────────────────

class LegalAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalAuditLog
        fields = [
            'id', 'entity_type', 'entity_id', 'action', 'actor_id',
            'previous_status', 'new_status', 'stage_name',
            'comment', 'ip_address', 'metadata', 'created_at',
        ]
        read_only_fields = fields



