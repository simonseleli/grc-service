"""
Tests for Legal Module SRS Verification Fixes (Priority 1, 2, 3).

Covers:
  R1  — Agenda outcome → SubmissionForDetermination propagation  (GAP-01)
  R2  — Resolution auto-creation from agenda outcome             (GAP-02)
  R3  — MeetingStartView (quorum + schedule guard)               (GAP-04)
  R5  — CaseFolderURL field on CaseDefendant/CasePlaintiff       (GAP-03)
  R6  — Directive creation guard (meeting.status == 'ongoing')    (GAP-05)
  R7  — Directive closure role enforcement                        (GAP-06)
  R8  — Financial record-recovery / record-payment endpoints      (GAP-10)
  R9  — IP address captured in audit log                          (GAP-08)
  R10 — PreviousStatus/NewStatus populated in audit log           (GAP-09)
  R11 — Global search on case lists                               (GAP-11)
  R12 — ResponseDefendant 'response_to_ruling' type              (GAP-12)
  R15 — DG "Mark Case as Reviewed" endpoint                       (GAP-15)
"""

import uuid
import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    Meeting, MeetingAgenda, MeetingDirective, Resolution,
    SubmissionForDetermination, CaseDefendant, CasePlaintiff,
    FinancialDefendant, FinancialPlaintiff,
    JudgmentDefendant, JudgmentPlaintiff,
    ResponseDefendant, LegalAuditLog,
)

from .conftest import (
    LEGAL_USER_ID, LEGAL_OFFICER_ID, LEGAL_MANAGER_ID,
    SECRETARY_ID, MEMBER_USER_ID, DOCUMENT_UUID,
    make_mock_user,
)

API_BASE = '/api/v1/grc/legal'


# ═══════════════════════════════════════════════════════════════════════════════
# R1 (GAP-01) — Agenda outcome propagation
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR1AgendaOutcomePropagation:
    """When a MeetingAgenda outcome is set, the linked SubmissionForDetermination
    should transition to 'determined' with the outcome and determination_date."""

    def test_outcome_propagates_to_submission(self, legal_user_client, allow_all_permissions,
                                               meeting, submission, meeting_agenda):
        meeting.status = 'ongoing'
        meeting.save()

        url = f'{API_BASE}/meeting-agenda/{meeting_agenda.id}/'
        resp = legal_user_client.patch(url, {
            'outcome': 'approved',
            'outcome_notes': 'Budget approved unanimously',
        }, format='json')

        assert resp.status_code == 200

        submission.refresh_from_db()
        assert submission.status == 'determined'
        assert submission.outcome == 'approved'
        assert submission.outcome_notes == 'Budget approved unanimously'
        assert submission.determination_date is not None

    def test_no_propagation_when_no_submission(self, legal_user_client, allow_all_permissions,
                                                meeting):
        meeting.status = 'ongoing'
        meeting.save()

        agenda_no_sub = MeetingAgenda.objects.create(
            meeting=meeting, order=99, title='Matters Arising item',
            created_by=LEGAL_USER_ID,
        )
        url = f'{API_BASE}/meeting-agenda/{agenda_no_sub.id}/'
        resp = legal_user_client.patch(url, {
            'outcome': 'noted',
        }, format='json')

        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# R2 (GAP-02) — Resolution auto-creation
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR2ResolutionAutoCreation:
    """A Resolution should be auto-created when MeetingAgenda.outcome is saved."""

    def test_resolution_created_on_outcome(self, legal_user_client, allow_all_permissions,
                                            meeting, meeting_agenda):
        meeting.status = 'ongoing'
        meeting.save()

        assert Resolution.objects.filter(agenda_item=meeting_agenda).count() == 0

        url = f'{API_BASE}/meeting-agenda/{meeting_agenda.id}/'
        resp = legal_user_client.patch(url, {
            'outcome': 'approved',
            'outcome_notes': 'Resolution text here',
        }, format='json')

        assert resp.status_code == 200
        resolutions = Resolution.objects.filter(agenda_item=meeting_agenda)
        assert resolutions.count() == 1
        r = resolutions.first()
        assert r.status == 'approved'
        assert r.resolution_text == 'Resolution text here'
        assert r.meeting == meeting

    def test_no_duplicate_resolution_on_resubmit(self, legal_user_client, allow_all_permissions,
                                                   meeting, meeting_agenda):
        meeting.status = 'ongoing'
        meeting.save()

        # First outcome
        url = f'{API_BASE}/meeting-agenda/{meeting_agenda.id}/'
        legal_user_client.patch(url, {'outcome': 'approved', 'outcome_notes': 'First'}, format='json')
        assert Resolution.objects.filter(agenda_item=meeting_agenda).count() == 1

        # Re-patch shouldn't create duplicate (outcome already set)
        legal_user_client.patch(url, {'outcome_notes': 'Updated notes'}, format='json')
        assert Resolution.objects.filter(agenda_item=meeting_agenda).count() == 1


# ═══════════════════════════════════════════════════════════════════════════════
# R3 (GAP-04) — MeetingStartView
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR3MeetingStart:

    def test_start_success(self, legal_user_client, allow_all_permissions, meeting):
        now = timezone.now()
        meeting.status = 'quorum_ready'
        meeting.quorum_met = True
        meeting.scheduled_start = now - datetime.timedelta(minutes=5)
        meeting.scheduled_end = now + datetime.timedelta(hours=2)
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/start/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 200
        meeting.refresh_from_db()
        assert meeting.status == 'ongoing'

    def test_start_fails_no_quorum(self, legal_user_client, allow_all_permissions, meeting):
        now = timezone.now()
        meeting.status = 'registered'
        meeting.quorum_met = False
        meeting.scheduled_start = now - datetime.timedelta(minutes=5)
        meeting.scheduled_end = now + datetime.timedelta(hours=2)
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/start/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 400
        error_msg = resp.json().get('error', {}).get('message', '')
        assert 'quorum' in error_msg.lower()

    def test_start_fails_outside_schedule(self, legal_user_client, allow_all_permissions, meeting):
        meeting.status = 'quorum_ready'
        meeting.quorum_met = True
        meeting.scheduled_start = timezone.now() + datetime.timedelta(hours=5)
        meeting.scheduled_end = timezone.now() + datetime.timedelta(hours=8)
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/start/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 400
        error_msg = resp.json().get('error', {}).get('message', '')
        assert 'schedule' in error_msg.lower() or 'outside' in error_msg.lower()

    def test_start_fails_wrong_status(self, legal_user_client, allow_all_permissions, meeting_closed):
        url = f'{API_BASE}/meetings/{meeting_closed.id}/start/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# R5 (GAP-03) — CaseFolderURL field
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR5CaseFolderURL:

    def test_defendant_case_folder_url_field_exists(self, case_defendant):
        assert hasattr(case_defendant, 'case_folder_url')
        case_defendant.case_folder_url = 'https://drs.example.com/folders/abc'
        case_defendant.save()
        case_defendant.refresh_from_db()
        assert case_defendant.case_folder_url == 'https://drs.example.com/folders/abc'

    def test_plaintiff_case_folder_url_field_exists(self, case_plaintiff):
        assert hasattr(case_plaintiff, 'case_folder_url')
        case_plaintiff.case_folder_url = 'https://drs.example.com/folders/xyz'
        case_plaintiff.save()
        case_plaintiff.refresh_from_db()
        assert case_plaintiff.case_folder_url == 'https://drs.example.com/folders/xyz'

    def test_case_folder_url_in_serializer(self, legal_user_client, allow_all_permissions,
                                            case_defendant):
        url = f'{API_BASE}/cases/defendant/{case_defendant.id}/'
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert 'case_folder_url' in resp.json()['data']


# ═══════════════════════════════════════════════════════════════════════════════
# R6 (GAP-05) — Directive creation requires ongoing meeting
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR6DirectiveCreationGuard:

    def test_directive_creation_succeeds_during_ongoing(
        self, legal_user_client, allow_all_permissions,
        meeting, directive_priority
    ):
        meeting.status = 'ongoing'
        meeting.save()

        url = f'{API_BASE}/directives/'
        resp = legal_user_client.post(url, {
            'meeting': str(meeting.id),
            'directive_priority_id': str(directive_priority.id),
            'description': 'New directive during meeting',
            'assigned_user_id': str(LEGAL_OFFICER_ID),
            'due_date': '2026-06-01',
        }, format='json')

        assert resp.status_code == 201

    def test_directive_creation_blocked_when_not_ongoing(
        self, legal_user_client, allow_all_permissions,
        meeting, directive_priority
    ):
        meeting.status = 'draft'
        meeting.save()

        url = f'{API_BASE}/directives/'
        resp = legal_user_client.post(url, {
            'meeting': str(meeting.id),
            'directive_priority_id': str(directive_priority.id),
            'description': 'Should be blocked',
            'assigned_user_id': str(LEGAL_OFFICER_ID),
            'due_date': '2026-06-01',
        }, format='json')

        assert resp.status_code == 400
        error_msg = resp.json().get('error', {}).get('message', '')
        assert 'ongoing' in error_msg.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# R7 (GAP-06) — Directive closure role enforcement
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR7DirectiveClosureRoles:

    def test_initial_closure_by_assigned_user(self, allow_all_permissions, meeting_directive):
        client = APIClient()
        client.force_authenticate(user=make_mock_user(LEGAL_OFFICER_ID))

        url = f'{API_BASE}/directives/{meeting_directive.id}/'
        resp = client.patch(url, {'status': 'closed'}, format='json')

        assert resp.status_code == 200

    def test_initial_closure_rejected_for_non_assigned(self, allow_all_permissions, meeting_directive):
        client = APIClient()
        client.force_authenticate(user=make_mock_user(LEGAL_MANAGER_ID))

        url = f'{API_BASE}/directives/{meeting_directive.id}/'
        resp = client.patch(url, {'status': 'closed'}, format='json')

        assert resp.status_code == 403

    def test_final_closure_by_secretary(self, allow_all_permissions, meeting_directive):
        meeting_directive.status = 'closed'
        meeting_directive.save()

        client = APIClient()
        client.force_authenticate(user=make_mock_user(SECRETARY_ID))

        url = f'{API_BASE}/directives/{meeting_directive.id}/'
        resp = client.patch(url, {'fully_closed': True}, format='json')

        assert resp.status_code == 200

    def test_final_closure_rejected_for_non_secretary(self, allow_all_permissions, meeting_directive):
        meeting_directive.status = 'closed'
        meeting_directive.save()

        client = APIClient()
        client.force_authenticate(user=make_mock_user(LEGAL_OFFICER_ID))

        url = f'{API_BASE}/directives/{meeting_directive.id}/'
        resp = client.patch(url, {'fully_closed': True}, format='json')

        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# R8 (GAP-10) — Financial action endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR8FinancialActions:

    def test_record_recovery_succeeds_when_won(self, legal_user_client, allow_all_permissions,
                                                case_defendant, financial_defendant):
        JudgmentDefendant.objects.create(
            case_defendant=case_defendant,
            judgment_date=datetime.date(2026, 6, 1),
            outcome='won',
            document_id=DOCUMENT_UUID,
            created_by=LEGAL_USER_ID,
        )

        url = f'{API_BASE}/financials/defendant/{case_defendant.id}/record-recovery/'
        resp = legal_user_client.post(url, {
            'amount': '5000000.00',
            'reference': 'RCV-001',
        }, format='json')

        assert resp.status_code == 200
        financial_defendant.refresh_from_db()
        assert len(financial_defendant.recoveries) == 1
        assert financial_defendant.recoveries[0]['amount'] == '5000000.00'

    def test_record_recovery_fails_when_not_won(self, legal_user_client, allow_all_permissions,
                                                  case_defendant, financial_defendant):
        JudgmentDefendant.objects.create(
            case_defendant=case_defendant,
            judgment_date=datetime.date(2026, 6, 1),
            outcome='lost',
            document_id=DOCUMENT_UUID,
            created_by=LEGAL_USER_ID,
        )

        url = f'{API_BASE}/financials/defendant/{case_defendant.id}/record-recovery/'
        resp = legal_user_client.post(url, {'amount': '5000000.00'}, format='json')

        assert resp.status_code == 400

    def test_record_payment_succeeds_when_lost(self, legal_user_client, allow_all_permissions,
                                                case_defendant, financial_defendant):
        JudgmentDefendant.objects.create(
            case_defendant=case_defendant,
            judgment_date=datetime.date(2026, 6, 1),
            outcome='lost',
            document_id=DOCUMENT_UUID,
            created_by=LEGAL_USER_ID,
        )

        url = f'{API_BASE}/financials/defendant/{case_defendant.id}/record-payment/'
        resp = legal_user_client.post(url, {
            'amount': '3000000.00',
            'reference': 'PAY-001',
        }, format='json')

        assert resp.status_code == 200
        financial_defendant.refresh_from_db()
        assert len(financial_defendant.payments) == 1

    def test_record_payment_fails_when_won(self, legal_user_client, allow_all_permissions,
                                            case_defendant, financial_defendant):
        JudgmentDefendant.objects.create(
            case_defendant=case_defendant,
            judgment_date=datetime.date(2026, 6, 1),
            outcome='won',
            document_id=DOCUMENT_UUID,
            created_by=LEGAL_USER_ID,
        )

        url = f'{API_BASE}/financials/defendant/{case_defendant.id}/record-payment/'
        resp = legal_user_client.post(url, {'amount': '3000000.00'}, format='json')

        assert resp.status_code == 400

    def test_plaintiff_record_recovery(self, legal_user_client, allow_all_permissions,
                                        case_plaintiff, financial_plaintiff):
        JudgmentPlaintiff.objects.create(
            case_plaintiff=case_plaintiff,
            judgment_date=datetime.date(2026, 6, 1),
            outcome='won',
            document_id=DOCUMENT_UUID,
            created_by=LEGAL_USER_ID,
        )

        url = f'{API_BASE}/financials/plaintiff/{case_plaintiff.id}/record-recovery/'
        resp = legal_user_client.post(url, {
            'amount': '10000000.00',
            'reference': 'RCV-P01',
        }, format='json')

        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# R9 (GAP-08) — IP address in audit log
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR9IPAddressAuditLog:

    def test_meeting_start_logs_ip(self, legal_user_client, allow_all_permissions, meeting):
        now = timezone.now()
        meeting.status = 'quorum_ready'
        meeting.quorum_met = True
        meeting.scheduled_start = now - datetime.timedelta(minutes=5)
        meeting.scheduled_end = now + datetime.timedelta(hours=2)
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/start/'
        legal_user_client.post(url)

        log = LegalAuditLog.objects.filter(
            entity_type='meeting', entity_id=meeting.id, action='meeting_started'
        ).first()
        assert log is not None
        # DRF test client sets REMOTE_ADDR to '127.0.0.1'
        assert log.ip_address is not None

    def test_dg_mark_reviewed_logs_ip(self, legal_user_client, allow_all_permissions, case_defendant):
        url = f'{API_BASE}/cases/defendant/{case_defendant.id}/mark-reviewed/'
        legal_user_client.post(url, {'comment': 'Reviewed'}, format='json')

        log = LegalAuditLog.objects.filter(
            entity_type='case_defendant', action='dg_mark_reviewed'
        ).first()
        assert log is not None
        assert log.ip_address is not None


# ═══════════════════════════════════════════════════════════════════════════════
# R10 (GAP-09) — PreviousStatus / NewStatus in audit log
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR10AuditLogStatusFields:

    def test_meeting_start_populates_status_fields(self, legal_user_client, allow_all_permissions, meeting):
        now = timezone.now()
        meeting.status = 'quorum_ready'
        meeting.quorum_met = True
        meeting.scheduled_start = now - datetime.timedelta(minutes=5)
        meeting.scheduled_end = now + datetime.timedelta(hours=2)
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/start/'
        legal_user_client.post(url)

        log = LegalAuditLog.objects.filter(
            entity_type='meeting', entity_id=meeting.id, action='meeting_started'
        ).first()
        assert log is not None
        assert log.previous_status == 'quorum_ready'
        assert log.new_status == 'ongoing'


# ═══════════════════════════════════════════════════════════════════════════════
# R11 (GAP-11) — Global search on case lists
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR11GlobalSearch:

    def test_defendant_search_by_reference(self, legal_user_client, allow_all_permissions,
                                            case_defendant):
        url = f'{API_BASE}/cases/defendant/?q=SUED/2026'
        resp = legal_user_client.get(url)

        assert resp.status_code == 200
        assert resp.json()['meta']['total'] >= 1

    def test_defendant_search_no_results(self, legal_user_client, allow_all_permissions,
                                          case_defendant):
        url = f'{API_BASE}/cases/defendant/?q=NONEXISTENT999'
        resp = legal_user_client.get(url)

        assert resp.status_code == 200
        assert resp.json()['meta']['total'] == 0

    def test_plaintiff_search_by_respondent(self, legal_user_client, allow_all_permissions,
                                             case_plaintiff):
        # Search by respondent name
        url = f'{API_BASE}/cases/plaintiff/?q={case_plaintiff.respondent_name[:5]}'
        resp = legal_user_client.get(url)

        assert resp.status_code == 200
        assert resp.json()['meta']['total'] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# R12 (GAP-12) — ResponseDefendant 'response_to_ruling' type
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR12ResponseToRulingType:

    def test_response_to_ruling_type_exists(self, case_defendant):
        response = ResponseDefendant.objects.create(
            case_defendant=case_defendant,
            response_type='response_to_ruling',
            received_date=datetime.date(2026, 3, 15),
            document_id=DOCUMENT_UUID,
            created_by=LEGAL_USER_ID,
        )
        assert response.response_type == 'response_to_ruling'
        assert response.get_response_type_display() == 'Response to Ruling'


# ═══════════════════════════════════════════════════════════════════════════════
# R15 (GAP-15) — DG Mark Case as Reviewed
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestR15DGMarkReviewed:

    def test_mark_reviewed_defendant(self, legal_user_client, allow_all_permissions, case_defendant):
        assert case_defendant.dg_review_status == 'pending'

        url = f'{API_BASE}/cases/defendant/{case_defendant.id}/mark-reviewed/'
        resp = legal_user_client.post(url, {'comment': 'DG reviewed'}, format='json')

        assert resp.status_code == 200
        case_defendant.refresh_from_db()
        assert case_defendant.dg_review_status == 'reviewed'

    def test_mark_reviewed_plaintiff(self, legal_user_client, allow_all_permissions, case_plaintiff):
        url = f'{API_BASE}/cases/plaintiff/{case_plaintiff.id}/mark-reviewed/'
        resp = legal_user_client.post(url, {}, format='json')

        assert resp.status_code == 200
        case_plaintiff.refresh_from_db()
        assert case_plaintiff.dg_review_status == 'reviewed'

    def test_mark_reviewed_idempotent(self, legal_user_client, allow_all_permissions, case_defendant):
        case_defendant.dg_review_status = 'reviewed'
        case_defendant.save()

        url = f'{API_BASE}/cases/defendant/{case_defendant.id}/mark-reviewed/'
        resp = legal_user_client.post(url, {}, format='json')

        assert resp.status_code == 200

    def test_mark_reviewed_requires_approve_permission(self, legal_user_client, deny_all_permissions,
                                                        case_defendant):
        url = f'{API_BASE}/cases/defendant/{case_defendant.id}/mark-reviewed/'
        resp = legal_user_client.post(url, {}, format='json')

        assert resp.status_code == 403

    def test_dg_review_status_not_patchable_via_case_detail(self, legal_user_client,
                                                             allow_all_permissions, case_defendant):
        """dg_review_status should be read_only in CaseDefendantSerializer."""
        url = f'{API_BASE}/cases/defendant/{case_defendant.id}/'
        resp = legal_user_client.patch(url, {'dg_review_status': 'reviewed'}, format='json')

        # The serializer should ignore the field (read_only)
        case_defendant.refresh_from_db()
        assert case_defendant.dg_review_status == 'pending'

    def test_mark_reviewed_invalid_side(self, legal_user_client, allow_all_permissions):
        fake_id = uuid.uuid4()
        url = f'{API_BASE}/cases/invalid/{fake_id}/mark-reviewed/'
        resp = legal_user_client.post(url, {}, format='json')

        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting Lifecycle Endpoints (R13/GAP-14)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestMeetingLifecycleEndpoints:

    def test_share_agenda(self, legal_user_client, allow_all_permissions, meeting, meeting_agenda):
        meeting.status = 'invitations_sent'
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/share-agenda/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 200
        meeting.refresh_from_db()
        assert meeting.status == 'agenda_shared'

    def test_share_agenda_fails_no_items(self, legal_user_client, allow_all_permissions, meeting):
        meeting.status = 'invitations_sent'
        meeting.save()
        MeetingAgenda.objects.filter(meeting=meeting).delete()

        url = f'{API_BASE}/meetings/{meeting.id}/share-agenda/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 400

    def test_mark_quorum_ready(self, legal_user_client, allow_all_permissions, meeting):
        meeting.status = 'agenda_shared'
        meeting.quorum_met = True
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/mark-quorum-ready/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 200
        meeting.refresh_from_db()
        assert meeting.status == 'quorum_ready'

    def test_postpone(self, legal_user_client, allow_all_permissions, meeting):
        meeting.status = 'registered'
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/postpone/'
        resp = legal_user_client.post(url, {'reason': 'Venue unavailable'}, format='json')

        assert resp.status_code == 200
        meeting.refresh_from_db()
        assert meeting.status == 'postponed'

    def test_close(self, legal_user_client, allow_all_permissions, meeting):
        meeting.status = 'ongoing'
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/close/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 200
        meeting.refresh_from_db()
        assert meeting.status == 'closed'

    def test_close_fails_if_not_ongoing(self, legal_user_client, allow_all_permissions, meeting):
        meeting.status = 'draft'
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/close/'
        resp = legal_user_client.post(url)

        assert resp.status_code == 400

    def test_reschedule(self, legal_user_client, allow_all_permissions, meeting):
        meeting.status = 'registered'
        meeting.save()

        url = f'{API_BASE}/meetings/{meeting.id}/reschedule/'
        resp = legal_user_client.post(url, {
            'scheduled_start': '2026-05-01T09:00:00Z',
            'scheduled_end': '2026-05-01T12:00:00Z',
            'reason': 'Participant conflict',
        }, format='json')

        assert resp.status_code == 200
        meeting.refresh_from_db()
        assert meeting.status == 'rescheduled'
