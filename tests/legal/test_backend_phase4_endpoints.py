"""
Backend Phase 4 — New Action Endpoint Tests

B4-1/B4-2: Case Defendant/Plaintiff Hold + Resume
B4-3:      Litigation Directive Submit-for-DG-Approval + DG Decision
B4-4:      Meeting Directives Sub-Resource (invitee-scoped)
B4-5:      Meeting Number Generation using GoverningBody prefix/format
"""

import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    CaseDefendant, CasePlaintiff, LitigationDirective,
    Meeting, MeetingDirective, MeetingParticipant,
    GoverningBody, CommitteeType,
    CourtLevel, LitigationUrgencyLevel, LitigationRiskLevel,
    MeetingMode, MeetingType, DirectivePriority,
)
from apps.api.views.legal_meeting_views import _generate_meeting_number


LEGAL_MANAGER_ID = uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
DG_USER_ID = uuid.UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
PARTICIPANT_ID = uuid.UUID('cccccccc-cccc-cccc-cccc-cccccccccccc')

BASE = '/api/v1/grc/legal'


def _mock_user(user_id):
    user = MagicMock()
    user.id = str(user_id)
    user.is_authenticated = True
    return user


def _client(user_id=LEGAL_MANAGER_ID):
    c = APIClient()
    c.force_authenticate(user=_mock_user(user_id))
    return c


# Decorator to auto-approve the CanManageLegalCase permission
_allow_manage_case = patch(
    'apps.api.views.legal_case_views.CanManageLegalCase',
    return_value=MagicMock(has_permission=MagicMock(return_value=True)),
)

_allow_manage_directive = patch(
    'apps.api.views.legal_directive_views.CanManageLegalDirective',
    return_value=MagicMock(has_permission=MagicMock(return_value=True)),
)

_allow_approve_closure = patch(
    'apps.api.views.legal_directive_views.CanApproveDirectiveClosure',
    return_value=MagicMock(has_permission=MagicMock(return_value=True)),
)


# ═══════════════════════════════════════════════════════════════════════════════
# B4-1 / B4-2 — Case Hold + Resume
# ═══════════════════════════════════════════════════════════════════════════════

class CaseHoldResumeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.court_level = CourtLevel.objects.create(name='High Court', code='HC')
        cls.urgency = LitigationUrgencyLevel.objects.create(name='Normal', code='normal')
        cls.risk = LitigationRiskLevel.objects.create(name='Medium', code='medium')
        cls.defendant_case = CaseDefendant.objects.create(
            reference_number='FCC/SUED/2026/P4-001',
            court_level=cls.court_level,
            urgency_level=cls.urgency,
            risk_level=cls.risk,
            status='hearing_stage',
            created_by=LEGAL_MANAGER_ID,
        )
        cls.plaintiff_case = CasePlaintiff.objects.create(
            reference_number='FCC/SUING/2026/P4-001',
            status='hearing_stage',
            created_by=LEGAL_MANAGER_ID,
        )

    @_allow_manage_case
    def test_hold_defendant_success(self, _perm):
        resp = _client().post(
            f'{BASE}/cases/defendant/{self.defendant_case.pk}/hold/',
            {'hold_reason': 'Pending settlement negotiation'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.defendant_case.refresh_from_db()
        self.assertEqual(self.defendant_case.status, 'on_hold')
        self.assertEqual(self.defendant_case.hold_reason, 'Pending settlement negotiation')

    @_allow_manage_case
    def test_hold_plaintiff_success(self, _perm):
        resp = _client().post(
            f'{BASE}/cases/plaintiff/{self.plaintiff_case.pk}/hold/',
            {'hold_reason': 'Awaiting evidence'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.plaintiff_case.refresh_from_db()
        self.assertEqual(self.plaintiff_case.status, 'on_hold')

    @_allow_manage_case
    def test_hold_rejects_already_on_hold(self, _perm):
        self.defendant_case.status = 'on_hold'
        self.defendant_case.save(update_fields=['status'])
        resp = _client().post(
            f'{BASE}/cases/defendant/{self.defendant_case.pk}/hold/',
            {'hold_reason': 'Again'},
            format='json',
        )
        self.assertEqual(resp.status_code, 409)

    @_allow_manage_case
    def test_hold_rejects_closed_case(self, _perm):
        self.defendant_case.status = 'closed'
        self.defendant_case.save(update_fields=['status'])
        resp = _client().post(
            f'{BASE}/cases/defendant/{self.defendant_case.pk}/hold/',
            {},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    @_allow_manage_case
    def test_resume_defendant_success(self, _perm):
        self.defendant_case.status = 'on_hold'
        self.defendant_case.hold_reason = 'some reason'
        self.defendant_case.save(update_fields=['status', 'hold_reason'])
        resp = _client().post(
            f'{BASE}/cases/defendant/{self.defendant_case.pk}/resume/',
            {'resume_to_status': 'hearing_stage'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.defendant_case.refresh_from_db()
        self.assertEqual(self.defendant_case.status, 'hearing_stage')
        self.assertEqual(self.defendant_case.hold_reason, '')

    @_allow_manage_case
    def test_resume_rejects_not_on_hold(self, _perm):
        self.defendant_case.status = 'hearing_stage'
        self.defendant_case.save(update_fields=['status'])
        resp = _client().post(
            f'{BASE}/cases/defendant/{self.defendant_case.pk}/resume/',
            {'resume_to_status': 'new'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    @_allow_manage_case
    def test_hold_invalid_side(self, _perm):
        resp = _client().post(
            f'{BASE}/cases/invalid/{uuid.uuid4()}/hold/',
            {},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)


# ═══════════════════════════════════════════════════════════════════════════════
# B4-3 — Litigation Directive DG Approval
# ═══════════════════════════════════════════════════════════════════════════════

class LitigationDirectiveDGApprovalTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.court_level = CourtLevel.objects.create(name='High Court 2', code='HC2')
        cls.urgency = LitigationUrgencyLevel.objects.create(name='High', code='high')
        cls.defendant_case = CaseDefendant.objects.create(
            reference_number='FCC/SUED/2026/P4-050',
            court_level=cls.court_level,
            urgency_level=cls.urgency,
            status='directive_issued',
            created_by=LEGAL_MANAGER_ID,
        )
        cls.directive_with_dg = LitigationDirective.objects.create(
            case_defendant=cls.defendant_case,
            issued_by_user_id=LEGAL_MANAGER_ID,
            issue_date=timezone.now().date(),
            instruction='Close case after settlement',
            due_date=timezone.now().date(),
            status='in_progress',
            requires_dg_approval_for_closure=True,
            created_by=LEGAL_MANAGER_ID,
        )
        cls.directive_without_dg = LitigationDirective.objects.create(
            case_defendant=cls.defendant_case,
            issued_by_user_id=LEGAL_MANAGER_ID,
            issue_date=timezone.now().date(),
            instruction='Standard directive',
            due_date=timezone.now().date(),
            status='in_progress',
            requires_dg_approval_for_closure=False,
            created_by=LEGAL_MANAGER_ID,
        )

    @_allow_manage_directive
    def test_submit_for_dg_approval_success(self, _perm):
        resp = _client().post(
            f'{BASE}/litigation-directives/{self.directive_with_dg.pk}/submit-for-dg-approval/',
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.directive_with_dg.refresh_from_db()
        self.assertEqual(self.directive_with_dg.status, 'pending_dg_approval')

    @_allow_manage_directive
    def test_submit_rejects_directive_without_dg_requirement(self, _perm):
        resp = _client().post(
            f'{BASE}/litigation-directives/{self.directive_without_dg.pk}/submit-for-dg-approval/',
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    @_allow_manage_directive
    def test_submit_rejects_wrong_status(self, _perm):
        self.directive_with_dg.status = 'closed'
        self.directive_with_dg.save(update_fields=['status'])
        resp = _client().post(
            f'{BASE}/litigation-directives/{self.directive_with_dg.pk}/submit-for-dg-approval/',
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    @_allow_approve_closure
    def test_dg_approve_success(self, _perm):
        self.directive_with_dg.status = 'pending_dg_approval'
        self.directive_with_dg.save(update_fields=['status'])
        resp = _client(DG_USER_ID).post(
            f'{BASE}/litigation-directives/{self.directive_with_dg.pk}/dg-decision/',
            {'decision': 'approve'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.directive_with_dg.refresh_from_db()
        self.assertEqual(self.directive_with_dg.status, 'closed')
        self.assertIsNotNone(self.directive_with_dg.completion_date)

    @_allow_approve_closure
    def test_dg_reject_success(self, _perm):
        self.directive_with_dg.status = 'pending_dg_approval'
        self.directive_with_dg.save(update_fields=['status'])
        resp = _client(DG_USER_ID).post(
            f'{BASE}/litigation-directives/{self.directive_with_dg.pk}/dg-decision/',
            {'decision': 'reject'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.directive_with_dg.refresh_from_db()
        self.assertEqual(self.directive_with_dg.status, 'in_progress')

    @_allow_approve_closure
    def test_dg_decision_invalid_value(self, _perm):
        self.directive_with_dg.status = 'pending_dg_approval'
        self.directive_with_dg.save(update_fields=['status'])
        resp = _client(DG_USER_ID).post(
            f'{BASE}/litigation-directives/{self.directive_with_dg.pk}/dg-decision/',
            {'decision': 'maybe'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    @_allow_approve_closure
    def test_dg_decision_rejects_wrong_status(self, _perm):
        self.directive_with_dg.status = 'in_progress'
        self.directive_with_dg.save(update_fields=['status'])
        resp = _client(DG_USER_ID).post(
            f'{BASE}/litigation-directives/{self.directive_with_dg.pk}/dg-decision/',
            {'decision': 'approve'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)


# ═══════════════════════════════════════════════════════════════════════════════
# B4-4 — Meeting Directives Sub-Resource
# ═══════════════════════════════════════════════════════════════════════════════

def _deny_perm():
    return MagicMock(has_permission=MagicMock(return_value=False))


def _allow_perm():
    return MagicMock(has_permission=MagicMock(return_value=True))


class MeetingDirectivesSubResourceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.committee_type = CommitteeType.objects.create(name='Legal Committee', code='LC')
        cls.governing_body = GoverningBody.objects.create(
            name='Legal Board', committee_type=cls.committee_type,
            created_by=LEGAL_MANAGER_ID,
        )
        cls.meeting_mode = MeetingMode.objects.create(name='Physical', code='physical')
        cls.meeting_type = MeetingType.objects.create(name='Ordinary', code='ordinary')
        cls.directive_priority = DirectivePriority.objects.create(name='High', code='high')

        cls.meeting = Meeting.objects.create(
            governing_body=cls.governing_body,
            title='Q1 Legal Board Meeting',
            meeting_number='MTG-202603-001',
            meeting_mode=cls.meeting_mode,
            meeting_type=cls.meeting_type,
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now(),
            secretary_id=LEGAL_MANAGER_ID,
            status='in_progress',
            created_by=LEGAL_MANAGER_ID,
        )

        cls.participant = MeetingParticipant.objects.create(
            meeting=cls.meeting,
            user_id=PARTICIPANT_ID,
            role='member',
            invitation_status='accepted',
            created_by=LEGAL_MANAGER_ID,
        )

        cls.directive1 = MeetingDirective.objects.create(
            meeting=cls.meeting,
            directive_priority=cls.directive_priority,
            description='Follow up on case X',
            due_date=timezone.now().date(),
            assigned_user_id=PARTICIPANT_ID,
            status='open',
            created_by=LEGAL_MANAGER_ID,
        )
        cls.directive2 = MeetingDirective.objects.create(
            meeting=cls.meeting,
            directive_priority=cls.directive_priority,
            description='Prepare settlement brief',
            due_date=timezone.now().date(),
            status='in_progress',
            created_by=LEGAL_MANAGER_ID,
        )

    @patch('apps.api.views.legal_meeting_views.CanManageLegalMeeting', side_effect=lambda: _deny_perm())
    @patch('apps.api.views.legal_meeting_views.CanViewLegalMeeting', side_effect=lambda: _deny_perm())
    def test_participant_can_view_directives(self, _v, _m):
        resp = _client(PARTICIPANT_ID).get(f'{BASE}/meetings/{self.meeting.pk}/directives/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['meta']['total'], 2)

    @patch('apps.api.views.legal_meeting_views.CanManageLegalMeeting', side_effect=lambda: _allow_perm())
    @patch('apps.api.views.legal_meeting_views.CanViewLegalMeeting', side_effect=lambda: _deny_perm())
    def test_manager_can_view_directives(self, _v, _m):
        resp = _client(LEGAL_MANAGER_ID).get(f'{BASE}/meetings/{self.meeting.pk}/directives/')
        self.assertEqual(resp.status_code, 200)

    @patch('apps.api.views.legal_meeting_views.CanManageLegalMeeting', side_effect=lambda: _deny_perm())
    @patch('apps.api.views.legal_meeting_views.CanViewLegalMeeting', side_effect=lambda: _deny_perm())
    def test_non_participant_denied(self, _v, _m):
        outsider = uuid.UUID('dddddddd-dddd-dddd-dddd-dddddddddddd')
        resp = _client(outsider).get(f'{BASE}/meetings/{self.meeting.pk}/directives/')
        self.assertEqual(resp.status_code, 403)

    @patch('apps.api.views.legal_meeting_views.CanManageLegalMeeting', side_effect=lambda: _deny_perm())
    @patch('apps.api.views.legal_meeting_views.CanViewLegalMeeting', side_effect=lambda: _allow_perm())
    def test_status_filter(self, _v, _m):
        resp = _client(LEGAL_MANAGER_ID).get(
            f'{BASE}/meetings/{self.meeting.pk}/directives/',
            {'status': 'open'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['meta']['total'], 1)


# ═══════════════════════════════════════════════════════════════════════════════
# B4-5 — Meeting Number Generation
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingNumberGenerationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.committee_type = CommitteeType.objects.create(name='Board', code='BD')

    def test_sequential_with_custom_prefix(self):
        gb = GoverningBody(
            name='Test Board', committee_type=self.committee_type,
            meeting_number_prefix='LB', meeting_number_format='sequential',
        )
        result = _generate_meeting_number(gb, 5)
        self.assertTrue(result.startswith('LB-'))
        self.assertTrue(result.endswith('-005'))

    def test_sequential_default_prefix(self):
        gb = GoverningBody(
            name='Test Board', committee_type=self.committee_type,
            meeting_number_prefix='', meeting_number_format='sequential',
        )
        result = _generate_meeting_number(gb, 1)
        self.assertTrue(result.startswith('MTG-'))

    def test_financial_year_format(self):
        gb = GoverningBody(
            name='Test Board', committee_type=self.committee_type,
            meeting_number_prefix='FCC', meeting_number_format='financial_year',
        )
        result = _generate_meeting_number(gb, 12)
        self.assertTrue(result.startswith('FCC-FY'))
        self.assertTrue(result.endswith('-012'))
        self.assertIn('/', result)

    def test_unknown_format_defaults_to_sequential(self):
        gb = GoverningBody(
            name='Test Board', committee_type=self.committee_type,
            meeting_number_prefix='X', meeting_number_format='unknown',
        )
        result = _generate_meeting_number(gb, 3)
        self.assertTrue(result.startswith('X-'))
        self.assertNotIn('FY', result)
