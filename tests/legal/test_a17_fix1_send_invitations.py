"""
A17-Fix-1 — MeetingSendInvitationsView tests
POST /api/v1/grc/legal/meetings/<uuid:pk>/send-invitations/

SRS §1.2.1: Transition meeting from 'registered' → 'invitations_sent'.
"""
import datetime
import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.core.models import Meeting, MeetingParticipant
from tests.legal.conftest import LEGAL_USER_ID, SECRETARY_ID, SYSTEM_USER_ID, MEMBER_USER_ID

MEETING_VIEW_MODULE = "apps.api.views.legal_meeting_views"
MESSAGING_SVC_PATH = "apps.infrastructure.services.messaging_service.messaging_service"


# ── Fixtures special to this test module ─────────────────────────────────────

@pytest.fixture
def meeting_registered(db, governing_body, meeting_mode, meeting_type):
    """A meeting in 'registered' status — the only valid pre-condition for send-invitations."""
    return Meeting.objects.create(
        governing_body=governing_body,
        meeting_number='MTG-REG-001',
        title='Registered Meeting',
        meeting_mode=meeting_mode,
        meeting_type=meeting_type,
        scheduled_start=datetime.datetime(2026, 6, 1, 9, 0, tzinfo=datetime.timezone.utc),
        scheduled_end=datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.timezone.utc),
        status='registered',
        secretary_id=SECRETARY_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def meeting_registered_with_participants(db, meeting_registered):
    """Registered meeting with two pending participants."""
    MeetingParticipant.objects.create(
        meeting=meeting_registered,
        user_id=MEMBER_USER_ID,
        role='member',
        invitation_status='pending',
        created_by=SYSTEM_USER_ID,
    )
    MeetingParticipant.objects.create(
        meeting=meeting_registered,
        user_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        role='member',
        invitation_status='pending',
        created_by=SYSTEM_USER_ID,
    )
    return meeting_registered


# ═══════════════════════════════════════════════════════════════════════════════
# Happy path
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingSendInvitationsHappyPath:

    @pytest.mark.django_db
    def test_returns_200_for_registered_meeting(
        self, legal_user_client, meeting_registered, allow_all_permissions,
    ):
        url = reverse("legal-meeting-send-invitations", args=[meeting_registered.id])
        with patch(MESSAGING_SVC_PATH) as mock_ms:
            response = legal_user_client.post(url)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True

    @pytest.mark.django_db
    def test_transitions_status_to_invitations_sent(
        self, legal_user_client, meeting_registered, allow_all_permissions,
    ):
        url = reverse("legal-meeting-send-invitations", args=[meeting_registered.id])
        with patch(MESSAGING_SVC_PATH):
            legal_user_client.post(url)
        meeting_registered.refresh_from_db()
        assert meeting_registered.status == 'invitations_sent'

    @pytest.mark.django_db
    def test_response_data_contains_updated_meeting(
        self, legal_user_client, meeting_registered_with_participants, allow_all_permissions,
    ):
        """Response body should include the serialised meeting with new status."""
        meeting = meeting_registered_with_participants
        url = reverse("legal-meeting-send-invitations", args=[meeting.id])
        with patch(MESSAGING_SVC_PATH):
            response = legal_user_client.post(url)
        data = response.json()["data"]
        assert data["status"] == "invitations_sent"
        assert data["id"] == str(meeting.id)

    @pytest.mark.django_db
    def test_publishes_kafka_event(
        self, legal_user_client, meeting_registered_with_participants, allow_all_permissions,
    ):
        """Kafka publish is attempted after the DB transition (non-fatal if it fails)."""
        meeting = meeting_registered_with_participants
        url = reverse("legal-meeting-send-invitations", args=[meeting.id])
        with patch(
            f"{MESSAGING_SVC_PATH}.publish_legal_meeting_event"
        ) as mock_publish:
            legal_user_client.post(url)
        mock_publish.assert_called_once()
        call_kwargs = mock_publish.call_args[1] if mock_publish.call_args[1] else mock_publish.call_args[0]

    @pytest.mark.django_db
    def test_kafka_failure_does_not_roll_back_status(
        self, legal_user_client, meeting_registered, allow_all_permissions,
    ):
        """Kafka publish errors are logged but must NOT revert the DB change (SRS: status must persist)."""
        url = reverse("legal-meeting-send-invitations", args=[meeting_registered.id])
        with patch(
            f"{MESSAGING_SVC_PATH}.publish_legal_meeting_event",
            side_effect=Exception("Kafka broker unavailable"),
        ):
            response = legal_user_client.post(url)
        assert response.status_code == 200
        meeting_registered.refresh_from_db()
        assert meeting_registered.status == 'invitations_sent'


# ═══════════════════════════════════════════════════════════════════════════════
# Invalid status guard
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingSendInvitationsInvalidStatus:

    @pytest.mark.django_db
    @pytest.mark.parametrize("bad_status", [
        'draft', 'invitations_sent', 'agenda_shared', 'quorum_ready',
        'ongoing', 'closed', 'cancelled', 'postponed', 'rescheduled',
    ])
    def test_returns_400_when_not_registered(
        self, legal_user_client, governing_body, meeting_mode, meeting_type,
        allow_all_permissions, bad_status, db,
    ):
        meeting = Meeting.objects.create(
            governing_body=governing_body,
            meeting_number=f'MTG-{bad_status[:4].upper()}-001',
            title=f'Meeting in {bad_status}',
            meeting_mode=meeting_mode,
            meeting_type=meeting_type,
            scheduled_start=datetime.datetime(2026, 6, 1, 9, 0, tzinfo=datetime.timezone.utc),
            scheduled_end=datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.timezone.utc),
            status=bad_status,
            secretary_id=SECRETARY_ID,
            created_by=SYSTEM_USER_ID,
        )
        url = reverse("legal-meeting-send-invitations", args=[meeting.id])
        with patch(MESSAGING_SVC_PATH):
            response = legal_user_client.post(url)
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_STATUS"

    @pytest.mark.django_db
    def test_status_not_changed_when_guard_fails(
        self, legal_user_client, meeting, allow_all_permissions,
    ):
        """meeting fixture is in 'draft' — status must stay draft after failed call."""
        url = reverse("legal-meeting-send-invitations", args=[meeting.id])
        with patch(MESSAGING_SVC_PATH):
            legal_user_client.post(url)
        meeting.refresh_from_db()
        assert meeting.status == 'draft'


# ═══════════════════════════════════════════════════════════════════════════════
# Auth / permission guards
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingSendInvitationsAuthGuards:

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, meeting_registered):
        url = reverse("legal-meeting-send-invitations", args=[meeting_registered.id])
        response = anon_client.post(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_insufficient_permission_returns_403(
        self, legal_user_client, meeting_registered, deny_all_permissions,
    ):
        url = reverse("legal-meeting-send-invitations", args=[meeting_registered.id])
        response = legal_user_client.post(url)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_nonexistent_meeting_returns_404(
        self, legal_user_client, allow_all_permissions,
    ):
        url = reverse("legal-meeting-send-invitations", args=[uuid.uuid4()])
        response = legal_user_client.post(url)
        assert response.status_code == 404
