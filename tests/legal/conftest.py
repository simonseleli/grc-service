"""
Legal Module — Shared pytest fixtures.

Builds the complete model fixture chain required by Legal tests:

  Lookups → CommitteeType → GoverningBody → Member
           → Meeting (+ MeetingMode, MeetingType)
           → MeetingAgenda (+ SubmissionForDetermination)
           → Minutes, MeetingDirective, Resolution, MeetingParticipant
           → CaseDefendant / CasePlaintiff (+ CourtLevel, UrgencyLevel, RiskLevel)
           → Hearing, FilingDefendant/Plaintiff, SettlementDefendant/Plaintiff
           → JudgmentDefendant/Plaintiff, AppealDefendant/Plaintiff
           → LitigationDirective, TaskLitigation, LegalNotice
"""
import uuid
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.core.models import (
    CommitteeType, GoverningBody, Member,
    SubmissionForDetermination,
    Meeting, MeetingAgenda, ConflictDeclaration, MeetingParticipant,
    MeetingDirective, Minutes, Resolution,
    CaseDefendant, CasePlaintiff,
    Hearing, HearingReport,
    FilingDefendant, FilingPlaintiff,
    ResponseDefendant, ResponsePlaintiff,
    SettlementDefendant, SettlementPlaintiff,
    JudgmentDefendant, JudgmentPlaintiff,
    FinancialDefendant, FinancialPlaintiff,
    AppealDefendant, AppealPlaintiff,
    LitigationDirective, TaskLitigation,
    LegalNotice, LegalAuditLog,
    PublicDecision,
)
from apps.core.models.lookups import (
    CourtLevel, LitigationUrgencyLevel, LitigationRiskLevel,
    MeetingMode, MeetingType, DirectivePriority, DirectiveCategory,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Stable UUIDs used across legal fixtures
# ═══════════════════════════════════════════════════════════════════════════════

LEGAL_USER_ID    = uuid.UUID("11111111-1111-1111-1111-111111111111")
LEGAL_OFFICER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
LEGAL_MANAGER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
SECRETARY_ID     = uuid.UUID("44444444-4444-4444-4444-444444444444")
MEMBER_USER_ID   = uuid.UUID("55555555-5555-5555-5555-555555555555")
OTHER_USER_ID    = uuid.UUID("66666666-6666-6666-6666-666666666666")
SYSTEM_USER_ID   = uuid.UUID("77777777-7777-7777-7777-777777777777")
DOCUMENT_UUID    = uuid.UUID("88888888-8888-8888-8888-888888888888")
PLAN_UUID        = uuid.UUID("99999999-9999-9999-9999-999999999999")


# ═══════════════════════════════════════════════════════════════════════════════
# Mock user helpers
# ═══════════════════════════════════════════════════════════════════════════════

def make_mock_user(user_id):
    """Return a mock user accepted by force_authenticate."""
    user = MagicMock()
    user.id = str(user_id)
    user.is_authenticated = True
    return user


# ═══════════════════════════════════════════════════════════════════════════════
# Client fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def legal_user_client():
    """Authenticated client with wildcard permissions (legal_user)."""
    client = APIClient()
    client.force_authenticate(user=make_mock_user(LEGAL_USER_ID))
    return client


@pytest.fixture
def legal_officer_client():
    """Authenticated client for legal officer."""
    client = APIClient()
    client.force_authenticate(user=make_mock_user(LEGAL_OFFICER_ID))
    return client


@pytest.fixture
def anon_client():
    """Unauthenticated client."""
    return APIClient()


# ═══════════════════════════════════════════════════════════════════════════════
# Permission bypass fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def allow_all_permissions():
    """Patch _check_grc_permission_locally to always return True."""
    with patch(
        'apps.api.permissions_jwt._check_grc_permission_locally',
        return_value=True,
    ):
        yield


@pytest.fixture
def deny_all_permissions():
    """Patch _check_grc_permission_locally to always return False."""
    with patch(
        'apps.api.permissions_jwt._check_grc_permission_locally',
        return_value=False,
    ):
        yield


# ═══════════════════════════════════════════════════════════════════════════════
# Lookup fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def court_level(db):
    return CourtLevel.objects.create(code='high_court', name='High Court', order=3)


@pytest.fixture
def court_level_appeal(db):
    return CourtLevel.objects.create(code='court_of_appeal', name='Court of Appeal', order=4)


@pytest.fixture
def urgency_level(db):
    return LitigationUrgencyLevel.objects.create(
        code='high', name='High', color_code='#FD7E14', order=3,
    )


@pytest.fixture
def urgency_level_low(db):
    return LitigationUrgencyLevel.objects.create(
        code='low', name='Low', color_code='#28A745', order=1,
    )


@pytest.fixture
def risk_level(db):
    return LitigationRiskLevel.objects.create(
        code='medium', name='Medium', color_code='#FFC107', order=2,
    )


@pytest.fixture
def meeting_mode(db):
    return MeetingMode.objects.create(code='in_person', name='In Person', requires_venue_link=False)


@pytest.fixture
def meeting_mode_virtual(db):
    return MeetingMode.objects.create(code='virtual', name='Virtual', requires_venue_link=True)


@pytest.fixture
def meeting_type(db):
    return MeetingType.objects.create(
        code='ordinary', name='Ordinary Meeting', quorum_percentage=51,
    )


@pytest.fixture
def directive_priority(db):
    return DirectivePriority.objects.create(
        code='high', name='High', color_code='#FD7E14', order=3,
    )


@pytest.fixture
def directive_category(db):
    return DirectiveCategory.objects.create(code='compliance', name='Compliance')


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 1 — Governance fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def committee_type(db):
    return CommitteeType.objects.create(code='board', name='Board of Directors')


@pytest.fixture
def governing_body(db, committee_type):
    return GoverningBody.objects.create(
        committee_type=committee_type,
        name='Finance Committee',
        description='Oversees financial matters',
        secretary_user_ids=[str(SECRETARY_ID)],
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def member(db, governing_body):
    return Member.objects.create(
        governing_body=governing_body,
        user_id=MEMBER_USER_ID,
        position='member',
        member_type='committee_member',
        email='member@test.org',
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 2 — Submission fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def submission(db, governing_body):
    return SubmissionForDetermination.objects.create(
        title='Budget Approval Request',
        description='Request to approve annual budget',
        submitter_user_id=LEGAL_USER_ID,
        submission_date=datetime.date.today(),
        target_body=governing_body,
        status='submitted',
        created_by=LEGAL_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 3 — Meeting fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def meeting(db, governing_body, meeting_mode, meeting_type):
    return Meeting.objects.create(
        governing_body=governing_body,
        meeting_number='MTG-001',
        title='Q1 Finance Committee Meeting',
        location='Boardroom A',
        meeting_mode=meeting_mode,
        meeting_type=meeting_type,
        scheduled_start=datetime.datetime(2026, 4, 1, 9, 0, tzinfo=datetime.timezone.utc),
        scheduled_end=datetime.datetime(2026, 4, 1, 12, 0, tzinfo=datetime.timezone.utc),
        status='draft',
        secretary_id=SECRETARY_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def meeting_closed(db, governing_body, meeting_mode, meeting_type):
    return Meeting.objects.create(
        governing_body=governing_body,
        meeting_number='MTG-002',
        title='Past Meeting',
        meeting_mode=meeting_mode,
        meeting_type=meeting_type,
        scheduled_start=datetime.datetime(2026, 1, 15, 9, 0, tzinfo=datetime.timezone.utc),
        scheduled_end=datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.timezone.utc),
        status='closed',
        secretary_id=SECRETARY_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def meeting_with_workflow(db, governing_body, meeting_mode, meeting_type):
    return Meeting.objects.create(
        governing_body=governing_body,
        meeting_number='MTG-003',
        title='In-Progress Meeting',
        meeting_mode=meeting_mode,
        meeting_type=meeting_type,
        scheduled_start=datetime.datetime(2026, 5, 1, 9, 0, tzinfo=datetime.timezone.utc),
        scheduled_end=datetime.datetime(2026, 5, 1, 12, 0, tzinfo=datetime.timezone.utc),
        status='registered',
        secretary_id=SECRETARY_ID,
        workflow_plan_id=PLAN_UUID,
        workflow_stage='meeting_preparation',
        workflow_stage_id=uuid.uuid4(),
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def meeting_agenda(db, meeting, submission):
    return MeetingAgenda.objects.create(
        meeting=meeting,
        submission=submission,
        order=1,
        title='Budget Discussion',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def meeting_participant(db, meeting):
    return MeetingParticipant.objects.create(
        meeting=meeting,
        user_id=MEMBER_USER_ID,
        role='member',
        invitation_status='pending',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def meeting_directive(db, meeting, directive_priority, directive_category):
    return MeetingDirective.objects.create(
        meeting=meeting,
        directive_priority=directive_priority,
        directive_category=directive_category,
        description='Prepare quarterly financial report',
        assigned_user_id=LEGAL_OFFICER_ID,
        due_date=datetime.date(2026, 5, 15),
        status='open',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def meeting_directive_overdue(db, meeting, directive_priority, directive_category):
    return MeetingDirective.objects.create(
        meeting=meeting,
        directive_priority=directive_priority,
        directive_category=directive_category,
        description='Overdue directive for testing',
        assigned_user_id=LEGAL_OFFICER_ID,
        due_date=datetime.date(2026, 1, 1),
        status='in_progress',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def minutes(db, meeting_closed):
    return Minutes.objects.create(
        meeting=meeting_closed,
        title='Minutes of Past Meeting',
        content='Discussion focused on budget allocation.',
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def minutes_with_workflow(db, meeting):
    m = Minutes.objects.create(
        meeting=meeting,
        title='In-Approval Minutes',
        content='Minutes content pending approval.',
        status='pending_approval',
        workflow_plan_id=uuid.uuid4(),
        workflow_stage='minutes_review',
        workflow_stage_id=uuid.uuid4(),
        created_by=SYSTEM_USER_ID,
    )
    return m


@pytest.fixture
def resolution(db, meeting_closed, meeting_agenda):
    return Resolution.objects.create(
        meeting=meeting_closed,
        agenda_item=meeting_agenda,
        resolution_text='Approved quarterly budget of TZS 500M.',
        date_adopted=datetime.datetime(2026, 1, 15, 11, 0, tzinfo=datetime.timezone.utc),
        status='approved',
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 4 — Litigation (Defendant) fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def case_defendant(db, court_level, urgency_level, risk_level):
    return CaseDefendant.objects.create(
        reference_number='FCC/SUED/2026/001',
        court_case_number='CIVIL-2026-123',
        court_level=court_level,
        claim_amount=Decimal('50000000.00'),
        nature_of_claim='Breach of contract',
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='new',
        assigned_legal_officer_ids=[str(LEGAL_OFFICER_ID)],
        assigned_legal_manager_id=LEGAL_MANAGER_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def case_defendant_active(db, court_level, urgency_level, risk_level):
    return CaseDefendant.objects.create(
        reference_number='FCC/SUED/2026/002',
        court_case_number='CIVIL-2026-456',
        court_level=court_level,
        claim_amount=Decimal('25000000.00'),
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='hearing_stage',
        workflow_plan_id=uuid.uuid4(),
        workflow_stage='case_review',
        workflow_stage_id=uuid.uuid4(),
        assigned_legal_officer_ids=[str(LEGAL_OFFICER_ID)],
        assigned_legal_manager_id=LEGAL_MANAGER_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def case_defendant_closed(db, court_level, urgency_level, risk_level):
    return CaseDefendant.objects.create(
        reference_number='FCC/SUED/2026/003',
        court_case_number='CIVIL-2026-789',
        court_level=court_level,
        claim_amount=Decimal('10000000.00'),
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='closed',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def filing_defendant(db, case_defendant):
    return FilingDefendant.objects.create(
        case_defendant=case_defendant,
        filing_type='statement_of_defence',
        title='Statement of Defence',
        document_id=DOCUMENT_UUID,
        status='draft',
        submitted_by_user_id=LEGAL_OFFICER_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def response_defendant(db, case_defendant):
    return ResponseDefendant.objects.create(
        case_defendant=case_defendant,
        response_type='preliminary_objections',
        received_date=datetime.date(2026, 3, 1),
        document_id=DOCUMENT_UUID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def hearing_defendant(db, case_defendant):
    return Hearing.objects.create(
        case_defendant=case_defendant,
        case_plaintiff=None,
        hearing_date=datetime.date(2026, 6, 15),
        court='High Court Dar es Salaam',
        status='scheduled',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def hearing_report(db, hearing_defendant):
    return HearingReport.objects.create(
        hearing=hearing_defendant,
        report_type='proceedings',
        summary='Court proceedings summary',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def settlement_defendant(db, case_defendant_active):
    return SettlementDefendant.objects.create(
        case_defendant=case_defendant_active,
        settlement_date=datetime.date(2026, 7, 1),
        terms='Agree to pay TZS 25M in 3 installments',
        payment_amount=Decimal('25000000.00'),
        agreement_document_id=DOCUMENT_UUID,
        status='proposed',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def judgment_defendant(db, case_defendant_active):
    return JudgmentDefendant.objects.create(
        case_defendant=case_defendant_active,
        judgment_date=datetime.date(2026, 8, 15),
        outcome='lost',
        amount_awarded=Decimal('30000000.00'),
        document_id=DOCUMENT_UUID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def appeal_defendant(db, judgment_defendant, court_level_appeal):
    return AppealDefendant.objects.create(
        judgment=judgment_defendant,
        appeal_date=datetime.date(2026, 9, 1),
        grounds='Errors in law',
        court_level=court_level_appeal,
        status='pending',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def financial_defendant(db, case_defendant):
    return FinancialDefendant.objects.create(
        case_defendant=case_defendant,
        claim_amount=Decimal('50000000.00'),
        legal_costs_incurred=Decimal('5000000.00'),
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 5 — Litigation (Plaintiff) fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def case_plaintiff(db, court_level, urgency_level, risk_level):
    return CasePlaintiff.objects.create(
        reference_number='FCC/SUING/2026/001',
        registration_type='full',
        respondent_name='ABC Corporation',
        court_level=court_level,
        estimated_claim_amount=Decimal('75000000.00'),
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='new',
        assigned_legal_officer_ids=[str(LEGAL_OFFICER_ID)],
        assigned_legal_manager_id=LEGAL_MANAGER_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def case_plaintiff_active(db, court_level, urgency_level, risk_level):
    return CasePlaintiff.objects.create(
        reference_number='FCC/SUING/2026/002',
        registration_type='full',
        respondent_name='XYZ Ltd',
        court_level=court_level,
        estimated_claim_amount=Decimal('40000000.00'),
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='hearing_stage',
        workflow_plan_id=uuid.uuid4(),
        workflow_stage='case_review',
        workflow_stage_id=uuid.uuid4(),
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def case_plaintiff_closed(db, court_level, urgency_level, risk_level):
    return CasePlaintiff.objects.create(
        reference_number='FCC/SUING/2026/003',
        registration_type='full',
        respondent_name='Closed Corp',
        court_level=court_level,
        estimated_claim_amount=Decimal('10000000.00'),
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='closed',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def filing_plaintiff(db, case_plaintiff):
    return FilingPlaintiff.objects.create(
        case_plaintiff=case_plaintiff,
        filing_type='plaint',
        title='Statement of Claim',
        document_id=DOCUMENT_UUID,
        status='draft',
        submitted_by_user_id=LEGAL_OFFICER_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def settlement_plaintiff(db, case_plaintiff_active):
    return SettlementPlaintiff.objects.create(
        case_plaintiff=case_plaintiff_active,
        settlement_date=datetime.date(2026, 7, 15),
        terms='Full payment of TZS 40M',
        payment_amount=Decimal('40000000.00'),
        agreement_document_id=DOCUMENT_UUID,
        status='proposed',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def judgment_plaintiff(db, case_plaintiff_active):
    return JudgmentPlaintiff.objects.create(
        case_plaintiff=case_plaintiff_active,
        judgment_date=datetime.date(2026, 8, 20),
        outcome='won',
        amount_awarded=Decimal('40000000.00'),
        document_id=DOCUMENT_UUID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def appeal_plaintiff(db, judgment_plaintiff, court_level_appeal):
    return AppealPlaintiff.objects.create(
        judgment=judgment_plaintiff,
        appeal_date=datetime.date(2026, 9, 10),
        grounds='Quantum of damages insufficient',
        court_level=court_level_appeal,
        status='pending',
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Shared: Hearings / Litigation Directives / Tasks
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def hearing_plaintiff(db, case_plaintiff):
    return Hearing.objects.create(
        case_defendant=None,
        case_plaintiff=case_plaintiff,
        hearing_date=datetime.date(2026, 6, 20),
        court='High Court Mwanza',
        status='scheduled',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def litigation_directive(db, case_defendant):
    return LitigationDirective.objects.create(
        case_defendant=case_defendant,
        case_plaintiff=None,
        issued_by_user_id=LEGAL_MANAGER_ID,
        issue_date=datetime.date.today(),
        instruction='File response within 14 days',
        due_date=datetime.date.today() + datetime.timedelta(days=14),
        status='open',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def task_litigation(db, case_defendant):
    return TaskLitigation.objects.create(
        case_defendant=case_defendant,
        case_plaintiff=None,
        title='Prepare witness statements',
        assigned_to_user_id=LEGAL_OFFICER_ID,
        due_date=datetime.date.today() + datetime.timedelta(days=7),
        status='open',
        priority='high',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def task_litigation_overdue(db, case_defendant):
    return TaskLitigation.objects.create(
        case_defendant=case_defendant,
        case_plaintiff=None,
        title='Overdue task for testing',
        assigned_to_user_id=LEGAL_OFFICER_ID,
        due_date=datetime.date(2026, 1, 1),
        status='open',
        priority='critical',
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 8 — Notices / Public Decisions
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def legal_notice(db, case_defendant):
    return LegalNotice.objects.create(
        related_case_defendant=case_defendant,
        notice_type='demand_notice',
        title='Demand Notice to Contractor',
        content='You are hereby demanded to cease and desist.',
        issued_date=datetime.date.today(),
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def public_decision(db, meeting_closed):
    return PublicDecision.objects.create(
        title='Budget Allocation Decision',
        meeting=meeting_closed,
        body_text='The committee deliberated on...',
        decision_text='Resolved to allocate TZS 500M.',
        decision_date=datetime.date(2026, 1, 15),
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-12 — Dashboard helper fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def risk_level_high(db):
    return LitigationRiskLevel.objects.create(
        code='high_risk', name='High Risk', color_code='#DC3545', order=3,
    )


@pytest.fixture
def financial_plaintiff(db, case_plaintiff):
    return FinancialPlaintiff.objects.create(
        case_plaintiff=case_plaintiff,
        claim_amount=Decimal('75000000.00'),
        recovered_amount=Decimal('12000000.00'),
        created_by=SYSTEM_USER_ID,
    )
