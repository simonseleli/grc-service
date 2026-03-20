"""
Legal Module — Model Tests

Coverage:
  - Lookup model creation and uniqueness constraints
  - Governance model creation (CommitteeType, GoverningBody, Member)
  - Meeting model creation and auto-calculated fields (quorum)
  - Litigation model creation and XOR constraints (Hearing, LitigationDirective, TaskLitigation)
  - OneToOne constraints (Minutes→Meeting, AppealDefendant→JudgmentDefendant)
  - WorkflowMixin model methods (get_workflow_context, get_workflow_metadata)
  - Status field defaults and choices
  - Soft delete (is_active flag)
  - __str__ representations
"""
import uuid
import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.core.models import (
    CommitteeType, GoverningBody, Member,
    SubmissionForDetermination,
    Meeting, MeetingAgenda, ConflictDeclaration, MeetingParticipant,
    MeetingDirective, Minutes, Resolution,
    CaseDefendant, CasePlaintiff,
    Hearing, HearingReport,
    FilingDefendant, FilingPlaintiff,
    SettlementDefendant, SettlementPlaintiff,
    JudgmentDefendant, JudgmentPlaintiff,
    AppealDefendant, AppealPlaintiff,
    LitigationDirective, TaskLitigation,
    LegalNotice, LegalAuditLog,
)
from apps.core.models.lookups import (
    CourtLevel, LitigationUrgencyLevel, LitigationRiskLevel,
    MeetingMode, MeetingType, DirectivePriority, DirectiveCategory,
)
from tests.legal.conftest import (
    SYSTEM_USER_ID, LEGAL_USER_ID, LEGAL_OFFICER_ID,
    LEGAL_MANAGER_ID, SECRETARY_ID, MEMBER_USER_ID,
    DOCUMENT_UUID, PLAN_UUID,
)


# ===========================================================================
# Lookup Model Tests
# ===========================================================================

class TestLookupModels:

    @pytest.mark.django_db
    def test_court_level_creation(self, court_level):
        assert court_level.code == 'high_court'
        assert court_level.name == 'High Court'
        assert court_level.is_active is True
        assert str(court_level) == 'High Court'

    @pytest.mark.django_db
    def test_court_level_unique_code(self, court_level):
        with pytest.raises(IntegrityError):
            CourtLevel.objects.create(code='high_court', name='Duplicate')

    @pytest.mark.django_db
    def test_urgency_level_creation(self, urgency_level):
        assert urgency_level.code == 'high'
        assert urgency_level.color_code == '#FD7E14'

    @pytest.mark.django_db
    def test_risk_level_creation(self, risk_level):
        assert risk_level.code == 'medium'
        assert risk_level.name == 'Medium'

    @pytest.mark.django_db
    def test_meeting_mode_creation(self, meeting_mode):
        assert meeting_mode.code == 'in_person'
        assert meeting_mode.requires_venue_link is False

    @pytest.mark.django_db
    def test_meeting_type_creation(self, meeting_type):
        assert meeting_type.code == 'ordinary'
        assert meeting_type.quorum_percentage == 51

    @pytest.mark.django_db
    def test_directive_priority_creation(self, directive_priority):
        assert directive_priority.code == 'high'

    @pytest.mark.django_db
    def test_directive_category_creation(self, directive_category):
        assert directive_category.code == 'compliance'
        assert directive_category.name == 'Compliance'


# ===========================================================================
# Governance Model Tests
# ===========================================================================

class TestGovernanceModels:

    @pytest.mark.django_db
    def test_committee_type_creation(self, committee_type):
        assert committee_type.code == 'board'
        assert committee_type.is_active is True

    @pytest.mark.django_db
    def test_governing_body_creation(self, governing_body):
        assert governing_body.name == 'Finance Committee'
        assert len(governing_body.secretary_user_ids) == 1
        assert governing_body.committee_type is not None

    @pytest.mark.django_db
    def test_governing_body_is_secretary(self, governing_body):
        assert governing_body.is_secretary(str(SECRETARY_ID)) is True
        assert governing_body.is_secretary(str(LEGAL_USER_ID)) is False

    @pytest.mark.django_db
    def test_member_creation(self, member, governing_body):
        assert member.governing_body == governing_body
        assert member.position == 'member'
        assert member.member_type == 'committee_member'
        assert str(member.user_id) == str(MEMBER_USER_ID)

    @pytest.mark.django_db
    def test_member_unique_per_governing_body(self, member, governing_body):
        """Cannot add same user_id to same governing_body when is_active=True."""
        with pytest.raises(IntegrityError):
            Member.objects.create(
                governing_body=governing_body,
                user_id=MEMBER_USER_ID,
                position='secretary',
                created_by=SYSTEM_USER_ID,
            )


# ===========================================================================
# Meeting Model Tests
# ===========================================================================

class TestMeetingModels:

    @pytest.mark.django_db
    def test_meeting_creation(self, meeting):
        assert meeting.status == 'draft'
        assert meeting.meeting_number == 'MTG-001'
        assert meeting.is_active is True

    @pytest.mark.django_db
    def test_meeting_default_quorum_fields(self, meeting):
        assert meeting.total_member_count == 0
        assert meeting.rsvp_yes_count == 0
        assert meeting.quorum_met is False

    @pytest.mark.django_db
    def test_meeting_has_workflow_mixin_fields(self, meeting):
        assert meeting.workflow_plan_id is None
        assert meeting.workflow_stage == ''
        assert meeting.workflow_stage_id is None
        assert meeting.workflow_started_at is None
        assert meeting.workflow_completed_at is None

    @pytest.mark.django_db
    def test_meeting_workflow_context(self, meeting):
        ctx = meeting.get_workflow_context()
        assert 'meeting_id' in ctx or 'entity_id' in ctx
        assert ctx.get('meeting_id', ctx.get('entity_id')) == str(meeting.id)

    @pytest.mark.django_db
    def test_meeting_workflow_metadata(self, meeting):
        meta = meeting.get_workflow_metadata()
        assert meta.get('entity_type') == 'meeting'
        assert meta.get('entity_id') == str(meeting.id)

    @pytest.mark.django_db
    def test_meeting_agenda_creation(self, meeting_agenda, meeting, submission):
        assert meeting_agenda.meeting == meeting
        assert meeting_agenda.submission == submission
        assert meeting_agenda.order == 1

    @pytest.mark.django_db
    def test_meeting_participant_creation(self, meeting_participant, meeting):
        assert meeting_participant.meeting == meeting
        assert meeting_participant.invitation_status == 'pending'
        assert meeting_participant.attendance_marked is False

    @pytest.mark.django_db
    def test_meeting_directive_creation(self, meeting_directive, meeting):
        assert meeting_directive.meeting == meeting
        assert meeting_directive.status == 'open'
        assert meeting_directive.fully_closed is False

    @pytest.mark.django_db
    def test_minutes_creation(self, minutes, meeting_closed):
        assert minutes.meeting == meeting_closed
        assert minutes.status == 'draft'

    @pytest.mark.django_db
    def test_minutes_has_workflow_mixin(self, minutes):
        assert hasattr(minutes, 'workflow_plan_id')
        assert hasattr(minutes, 'get_workflow_context')

    @pytest.mark.django_db
    def test_minutes_one_to_one_with_meeting(self, minutes, meeting_closed):
        """Minutes is a OneToOneField: a second minutes for the same meeting should fail."""
        with pytest.raises(IntegrityError):
            Minutes.objects.create(
                meeting=meeting_closed,
                title='Duplicate Minutes',
                content='This should fail.',
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_resolution_creation(self, resolution):
        assert resolution.status == 'approved'
        assert 'TZS 500M' in resolution.resolution_text


# ===========================================================================
# Litigation Model Tests — Defendant
# ===========================================================================

class TestCaseDefendantModels:

    @pytest.mark.django_db
    def test_case_defendant_creation(self, case_defendant):
        assert case_defendant.reference_number == 'FCC/SUED/2026/001'
        assert case_defendant.status == 'new'
        assert case_defendant.claim_amount == Decimal('50000000.00')

    @pytest.mark.django_db
    def test_case_defendant_has_workflow_mixin(self, case_defendant):
        assert hasattr(case_defendant, 'workflow_plan_id')
        ctx = case_defendant.get_workflow_context()
        assert ctx is not None

    @pytest.mark.django_db
    def test_case_defendant_workflow_metadata(self, case_defendant):
        meta = case_defendant.get_workflow_metadata()
        assert meta.get('entity_type') == 'case_defendant'
        assert meta.get('entity_id') == str(case_defendant.id)
        assert meta.get('reference_number') == 'FCC/SUED/2026/001'

    @pytest.mark.django_db
    def test_filing_defendant_creation(self, filing_defendant, case_defendant):
        assert filing_defendant.case_defendant == case_defendant
        assert filing_defendant.filing_type == 'statement_of_defence'
        assert filing_defendant.status == 'draft'

    @pytest.mark.django_db
    def test_response_defendant_creation(self, response_defendant, case_defendant):
        assert response_defendant.case_defendant == case_defendant
        assert response_defendant.response_type == 'preliminary_objections'

    @pytest.mark.django_db
    def test_settlement_defendant_creation(self, settlement_defendant, case_defendant_active):
        assert settlement_defendant.case_defendant == case_defendant_active
        assert settlement_defendant.status == 'proposed'
        assert settlement_defendant.payment_amount == Decimal('25000000.00')

    @pytest.mark.django_db
    def test_judgment_defendant_creation(self, judgment_defendant, case_defendant_active):
        assert judgment_defendant.outcome == 'lost'
        assert judgment_defendant.amount_awarded == Decimal('30000000.00')

    @pytest.mark.django_db
    def test_appeal_defendant_creation(self, appeal_defendant, judgment_defendant):
        assert appeal_defendant.judgment == judgment_defendant
        assert appeal_defendant.status == 'pending'
        assert appeal_defendant.grounds == 'Errors in law'

    @pytest.mark.django_db
    def test_appeal_defendant_one_to_one(self, appeal_defendant, judgment_defendant, court_level_appeal):
        """Only one appeal per judgment."""
        with pytest.raises(IntegrityError):
            AppealDefendant.objects.create(
                judgment=judgment_defendant,
                appeal_date=datetime.date(2026, 9, 15),
                grounds='Second appeal attempt',
                court_level=court_level_appeal,
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_financial_defendant_creation(self, financial_defendant, case_defendant):
        assert financial_defendant.case_defendant == case_defendant
        assert financial_defendant.claim_amount == Decimal('50000000.00')


# ===========================================================================
# Litigation Model Tests — Plaintiff
# ===========================================================================

class TestCasePlaintiffModels:

    @pytest.mark.django_db
    def test_case_plaintiff_creation(self, case_plaintiff):
        assert case_plaintiff.reference_number == 'FCC/SUING/2026/001'
        assert case_plaintiff.status == 'new'
        assert case_plaintiff.registration_type == 'full'
        assert case_plaintiff.respondent_name == 'ABC Corporation'

    @pytest.mark.django_db
    def test_case_plaintiff_has_workflow(self, case_plaintiff):
        assert hasattr(case_plaintiff, 'workflow_plan_id')
        meta = case_plaintiff.get_workflow_metadata()
        assert meta.get('entity_type') == 'case_plaintiff'

    @pytest.mark.django_db
    def test_filing_plaintiff_creation(self, filing_plaintiff, case_plaintiff):
        assert filing_plaintiff.case_plaintiff == case_plaintiff
        assert filing_plaintiff.filing_type == 'plaint'

    @pytest.mark.django_db
    def test_settlement_plaintiff_creation(self, settlement_plaintiff, case_plaintiff_active):
        assert settlement_plaintiff.case_plaintiff == case_plaintiff_active
        assert settlement_plaintiff.status == 'proposed'

    @pytest.mark.django_db
    def test_judgment_plaintiff_creation(self, judgment_plaintiff, case_plaintiff_active):
        assert judgment_plaintiff.outcome == 'won'
        assert judgment_plaintiff.case_plaintiff == case_plaintiff_active

    @pytest.mark.django_db
    def test_appeal_plaintiff_creation(self, appeal_plaintiff, judgment_plaintiff):
        assert appeal_plaintiff.judgment == judgment_plaintiff
        assert appeal_plaintiff.status == 'pending'


# ===========================================================================
# Shared Discriminator (XOR) Models
# ===========================================================================

class TestXORConstraintModels:

    @pytest.mark.django_db
    def test_hearing_defendant_only(self, hearing_defendant):
        assert hearing_defendant.case_defendant is not None
        assert hearing_defendant.case_plaintiff is None
        assert hearing_defendant.status == 'scheduled'

    @pytest.mark.django_db
    def test_hearing_plaintiff_only(self, hearing_plaintiff):
        assert hearing_plaintiff.case_defendant is None
        assert hearing_plaintiff.case_plaintiff is not None

    @pytest.mark.django_db
    def test_hearing_both_cases_raises(self, case_defendant, case_plaintiff):
        """Hearing must belong to exactly one case type (XOR constraint)."""
        with pytest.raises(IntegrityError):
            Hearing.objects.create(
                case_defendant=case_defendant,
                case_plaintiff=case_plaintiff,
                hearing_date=datetime.date(2026, 7, 1),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_hearing_no_case_raises(self):
        """Hearing must belong to at least one case type."""
        with pytest.raises(IntegrityError):
            Hearing.objects.create(
                case_defendant=None,
                case_plaintiff=None,
                hearing_date=datetime.date(2026, 7, 1),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_litigation_directive_defendant_only(self, litigation_directive):
        assert litigation_directive.case_defendant is not None
        assert litigation_directive.case_plaintiff is None

    @pytest.mark.django_db
    def test_litigation_directive_both_raises(self, case_defendant, case_plaintiff):
        with pytest.raises(IntegrityError):
            LitigationDirective.objects.create(
                case_defendant=case_defendant,
                case_plaintiff=case_plaintiff,
                issued_by_user_id=LEGAL_MANAGER_ID,
                issue_date=datetime.date.today(),
                instruction='Both cases set',
                due_date=datetime.date.today(),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_task_litigation_defendant_only(self, task_litigation):
        assert task_litigation.case_defendant is not None
        assert task_litigation.case_plaintiff is None

    @pytest.mark.django_db
    def test_task_litigation_both_raises(self, case_defendant, case_plaintiff):
        with pytest.raises(IntegrityError):
            TaskLitigation.objects.create(
                case_defendant=case_defendant,
                case_plaintiff=case_plaintiff,
                title='Both cases set',
                due_date=datetime.date.today(),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_hearing_report_creation(self, hearing_report, hearing_defendant):
        assert hearing_report.hearing == hearing_defendant
        assert hearing_report.report_type == 'proceedings'


# ===========================================================================
# Legal Notice Tests
# ===========================================================================

class TestLegalNoticeModels:

    @pytest.mark.django_db
    def test_legal_notice_creation(self, legal_notice, case_defendant):
        assert legal_notice.related_case_defendant == case_defendant
        assert legal_notice.status == 'draft'
        assert legal_notice.notice_type == 'demand_notice'

    @pytest.mark.django_db
    def test_legal_notice_standalone(self, db):
        """Legal notices can be created without a linked case."""
        notice = LegalNotice.objects.create(
            notice_type='general',
            title='Standalone Notice',
            content='No case attached.',
            issued_date=datetime.date.today(),
            status='draft',
            created_by=SYSTEM_USER_ID,
        )
        assert notice.related_case_defendant is None
        assert notice.related_case_plaintiff is None


# ===========================================================================
# Audit Log Tests
# ===========================================================================

class TestLegalAuditLog:

    @pytest.mark.django_db
    def test_audit_log_creation(self, db):
        log = LegalAuditLog.objects.create(
            entity_type='meeting',
            entity_id=uuid.uuid4(),
            action='status_changed',
            actor_id=LEGAL_USER_ID,
            previous_status='draft',
            new_status='registered',
        )
        assert log.entity_type == 'meeting'
        assert log.action == 'status_changed'


# ===========================================================================
# Soft Delete Tests
# ===========================================================================

class TestSoftDelete:

    @pytest.mark.django_db
    def test_governing_body_soft_delete(self, governing_body):
        governing_body.is_active = False
        governing_body.save(update_fields=['is_active'])
        governing_body.refresh_from_db()
        assert governing_body.is_active is False

    @pytest.mark.django_db
    def test_case_defendant_soft_delete(self, case_defendant):
        case_defendant.is_active = False
        case_defendant.save(update_fields=['is_active'])
        # Should not appear in active filter
        assert CaseDefendant.objects.filter(
            id=case_defendant.id, is_active=True
        ).count() == 0

    @pytest.mark.django_db
    def test_meeting_soft_delete(self, meeting):
        meeting.is_active = False
        meeting.save(update_fields=['is_active'])
        assert Meeting.objects.filter(id=meeting.id, is_active=True).count() == 0
