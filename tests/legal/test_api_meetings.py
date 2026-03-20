"""
Legal Module — API endpoint tests for Meeting entities.

Covers CRUD + workflow endpoints for:
  - Meeting (list, create, detail, update, delete)
  - MeetingAgenda (list, create, detail)
  - MeetingParticipant (list, create, detail)
  - Meeting workflow (submit, status, history, action, cancel)
"""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
from django.urls import reverse

from tests.legal.conftest import LEGAL_USER_ID, LEGAL_MANAGER_ID, PLAN_UUID, MEMBER_USER_ID

from apps.core.models import Member, MeetingParticipant, Meeting, ConflictDeclaration, MeetingAgenda

# ── View module path for mocking ─────────────────────────────────────────
MEETING_VIEW_MODULE = "apps.api.views.legal_meeting_views"


@dataclass
class FakeWorkflowPlanResult:
    plan_id: str
    status: str
    current_stage_id: Optional[str]
    current_stage_name: Optional[str]
    stages: List[Dict[str, Any]]
    metadata: Dict[str, Any]


def _fake_result(plan_id=None, stage_name="meeting_preparation"):
    return FakeWorkflowPlanResult(
        plan_id=plan_id or str(uuid.uuid4()),
        status="active",
        current_stage_id=str(uuid.uuid4()),
        current_stage_name=stage_name,
        stages=[],
        metadata={},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingListCreateAPI:

    @pytest.mark.django_db
    def test_list_returns_200(self, legal_user_client, meeting, allow_all_permissions):
        url = reverse("legal-meeting-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, governing_body, meeting_mode, meeting_type,
        allow_all_permissions,
    ):
        url = reverse("legal-meeting-list-create")
        payload = {
            "governing_body_id": str(governing_body.id),
            "title": "New Meeting",
            "meeting_mode_id": str(meeting_mode.id),
            "meeting_type_id": str(meeting_type.id),
            "scheduled_start": "2026-06-01T09:00:00Z",
            "scheduled_end": "2026-06-01T12:00:00Z",
            "secretary_id": str(LEGAL_USER_ID),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["title"] == "New Meeting"

    @pytest.mark.django_db
    def test_create_auto_populates_participants_from_members(
        self, legal_user_client, governing_body, member, meeting_mode, meeting_type,
        allow_all_permissions,
    ):
        """GAP-04: Creating a meeting auto-populates participants from active members."""
        # Add 2 more members (member fixture already adds 1)
        m2 = Member.objects.create(
            governing_body=governing_body,
            user_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            position='secretary',
            member_type='committee_member',
            created_by=LEGAL_USER_ID,
        )
        m3 = Member.objects.create(
            governing_body=governing_body,
            user_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            position='chairman',
            member_type='committee_member',
            created_by=LEGAL_USER_ID,
        )

        url = reverse("legal-meeting-list-create")
        payload = {
            "governing_body_id": str(governing_body.id),
            "title": "Meeting with Auto Participants",
            "meeting_mode_id": str(meeting_mode.id),
            "meeting_type_id": str(meeting_type.id),
            "scheduled_start": "2026-07-01T09:00:00Z",
            "scheduled_end": "2026-07-01T12:00:00Z",
            "secretary_id": str(LEGAL_USER_ID),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201

        meeting_id = response.json()["data"]["id"]
        participants = MeetingParticipant.objects.filter(meeting_id=meeting_id)
        assert participants.count() == 3

        # Check secretary role assigned correctly
        secretary_p = participants.get(user_id=m2.user_id)
        assert secretary_p.role == 'secretary'

        # Check counts on meeting
        mtg = Meeting.objects.get(pk=meeting_id)
        assert mtg.total_member_count == 3
        assert mtg.rsvp_pending_count == 3

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        url = reverse("legal-meeting-list-create")
        response = anon_client.get(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_permission_denied_returns_403(self, legal_user_client, deny_all_permissions):
        url = reverse("legal-meeting-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 403


class TestMeetingDetailAPI:

    @pytest.mark.django_db
    def test_detail_returns_200(self, legal_user_client, meeting, allow_all_permissions):
        url = reverse("legal-meeting-detail", args=[meeting.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Q1 Finance Committee Meeting"

    @pytest.mark.django_db
    def test_update_returns_200(self, legal_user_client, meeting, allow_all_permissions):
        url = reverse("legal-meeting-detail", args=[meeting.id])
        response = legal_user_client.patch(url, {"title": "Updated Title"}, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Updated Title"

    @pytest.mark.django_db
    def test_update_closed_meeting_returns_400(
        self, legal_user_client, meeting_closed, allow_all_permissions,
    ):
        url = reverse("legal-meeting-detail", args=[meeting_closed.id])
        response = legal_user_client.patch(url, {"title": "Nope"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_delete_returns_200(self, legal_user_client, meeting, allow_all_permissions):
        url = reverse("legal-meeting-detail", args=[meeting.id])
        response = legal_user_client.delete(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# MeetingAgenda
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingAgendaAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, meeting, meeting_agenda, allow_all_permissions,
    ):
        url = reverse("legal-meeting-agenda-list", args=[meeting.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, meeting, submission, allow_all_permissions,
    ):
        url = reverse("legal-meeting-agenda-list", args=[meeting.id])
        payload = {
            "meeting": str(meeting.id),
            "submission": str(submission.id),
            "order": 2,
            "title": "Second Agenda Item",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, meeting_agenda, allow_all_permissions,
    ):
        url = reverse("legal-meeting-agenda-detail", args=[meeting_agenda.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_create_transitions_submission_to_under_review(
        self, legal_user_client, meeting, submission, allow_all_permissions,
    ):
        """GAP-02: Adding agenda item with submission transitions it to under_review."""
        assert submission.status == 'submitted'
        url = reverse("legal-meeting-agenda-list", args=[meeting.id])
        payload = {
            "meeting": str(meeting.id),
            "submission": str(submission.id),
            "order": 1,
            "title": "Review Budget Submission",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        submission.refresh_from_db()
        assert submission.status == 'under_review'

    @pytest.mark.django_db
    def test_create_does_not_transition_non_submitted_submission(
        self, legal_user_client, meeting, submission, allow_all_permissions,
    ):
        """GAP-02: If submission is already under_review, status stays unchanged."""
        submission.status = 'under_review'
        submission.save(update_fields=['status'])
        url = reverse("legal-meeting-agenda-list", args=[meeting.id])
        payload = {
            "meeting": str(meeting.id),
            "submission": str(submission.id),
            "order": 1,
            "title": "Already Reviewed Submission",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        submission.refresh_from_db()
        assert submission.status == 'under_review'


# ═══════════════════════════════════════════════════════════════════════════════
# Conflict of Interest Vote Exclusion (GAP-05)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConflictOfInterestVoteExclusionAPI:

    @pytest.mark.django_db
    def test_conflicted_user_cannot_record_outcome(
        self, legal_user_client, meeting_agenda, allow_all_permissions,
    ):
        """GAP-05: A user who declared a conflict is blocked from recording outcome."""
        ConflictDeclaration.objects.create(
            agenda_item=meeting_agenda,
            member_user_id=LEGAL_USER_ID,
            reason="Financial interest in vendor",
            created_by=LEGAL_USER_ID,
        )
        url = reverse("legal-meeting-agenda-detail", args=[meeting_agenda.id])
        response = legal_user_client.patch(
            url, {"outcome": "approved", "outcome_notes": "All good"}, format="json",
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert "CONFLICT_OF_INTEREST" in str(body)

    @pytest.mark.django_db
    def test_non_conflicted_user_can_record_outcome(
        self, legal_user_client, meeting_agenda, allow_all_permissions,
    ):
        """GAP-05: A user without a conflict can record outcome normally."""
        # Create conflict for a DIFFERENT user — should not block legal_user
        ConflictDeclaration.objects.create(
            agenda_item=meeting_agenda,
            member_user_id=MEMBER_USER_ID,
            reason="Related party",
            created_by=MEMBER_USER_ID,
        )
        url = reverse("legal-meeting-agenda-detail", args=[meeting_agenda.id])
        response = legal_user_client.patch(
            url, {"outcome": "approved", "outcome_notes": "Passed"}, format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["outcome"] == "approved"

    @pytest.mark.django_db
    def test_non_outcome_update_allowed_for_conflicted_user(
        self, legal_user_client, meeting_agenda, allow_all_permissions,
    ):
        """GAP-05: Conflicted user can still update non-outcome fields."""
        ConflictDeclaration.objects.create(
            agenda_item=meeting_agenda,
            member_user_id=LEGAL_USER_ID,
            reason="Owns shares",
            created_by=LEGAL_USER_ID,
        )
        url = reverse("legal-meeting-agenda-detail", args=[meeting_agenda.id])
        response = legal_user_client.patch(
            url, {"title": "Updated Title"}, format="json",
        )
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Updated Title"

    @pytest.mark.django_db
    def test_inactive_conflict_does_not_block(
        self, legal_user_client, meeting_agenda, allow_all_permissions,
    ):
        """GAP-05: A deactivated conflict declaration does not block outcome recording."""
        ConflictDeclaration.objects.create(
            agenda_item=meeting_agenda,
            member_user_id=LEGAL_USER_ID,
            reason="Was conflicted, now resolved",
            is_active=False,
            created_by=LEGAL_USER_ID,
        )
        url = reverse("legal-meeting-agenda-detail", args=[meeting_agenda.id])
        response = legal_user_client.patch(
            url, {"outcome": "noted"}, format="json",
        )
        assert response.status_code == 200
        assert response.json()["data"]["outcome"] == "noted"


# ═══════════════════════════════════════════════════════════════════════════════
# Matters Arising — Auto-Populate (GAP-03)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingPopulateMattersArisingAPI:

    @pytest.mark.django_db
    def test_populate_creates_agenda_items_from_unresolved_directives(
        self, legal_user_client, meeting, meeting_directive,
        meeting_directive_overdue, allow_all_permissions,
    ):
        """GAP-03: POST populates agenda items from unresolved directives."""
        url = reverse("legal-meeting-populate-matters-arising", args=[meeting.id])
        response = legal_user_client.post(url, format="json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["created_count"] == 2
        assert len(data["items"]) == 2
        titles = [item["title"] for item in data["items"]]
        assert any("Prepare quarterly financial report" in t for t in titles)
        assert any("Overdue directive" in t for t in titles)

    @pytest.mark.django_db
    def test_populate_is_idempotent(
        self, legal_user_client, meeting, meeting_directive, allow_all_permissions,
    ):
        """GAP-03: Calling twice does not duplicate agenda items."""
        url = reverse("legal-meeting-populate-matters-arising", args=[meeting.id])
        resp1 = legal_user_client.post(url, format="json")
        assert resp1.status_code == 200
        assert resp1.json()["data"]["created_count"] == 1

        resp2 = legal_user_client.post(url, format="json")
        assert resp2.status_code == 200
        assert resp2.json()["data"]["created_count"] == 0

    @pytest.mark.django_db
    def test_populate_skips_fully_closed_directives(
        self, legal_user_client, meeting, meeting_directive, allow_all_permissions,
    ):
        """GAP-03: Fully closed directives are not added."""
        meeting_directive.fully_closed = True
        meeting_directive.save(update_fields=['fully_closed'])
        url = reverse("legal-meeting-populate-matters-arising", args=[meeting.id])
        response = legal_user_client.post(url, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["created_count"] == 0

    @pytest.mark.django_db
    def test_populate_locked_meeting_returns_400(
        self, legal_user_client, meeting, meeting_directive, allow_all_permissions,
    ):
        """GAP-03: Cannot populate on a closed meeting."""
        meeting.status = 'closed'
        meeting.save(update_fields=['status'])
        url = reverse("legal-meeting-populate-matters-arising", args=[meeting.id])
        response = legal_user_client.post(url, format="json")
        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# MeetingParticipant
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingParticipantAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, meeting, meeting_participant, allow_all_permissions,
    ):
        url = reverse("legal-meeting-participant-list", args=[meeting.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, meeting, allow_all_permissions,
    ):
        url = reverse("legal-meeting-participant-list", args=[meeting.id])
        payload = {
            "meeting": str(meeting.id),
            "user_id": str(uuid.uuid4()),
            "role": "invitee",
            "invitation_status": "pending",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting Workflow API endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingSubmitAPI:

    @pytest.mark.django_db
    def test_submit_returns_200(self, legal_user_client, meeting, allow_all_permissions):
        with patch(f"{MEETING_VIEW_MODULE}.LegalMeetingService") as MockService:
            mock_meeting = meeting
            mock_meeting.workflow_plan_id = uuid.uuid4()
            MockService.return_value.submit_for_approval.return_value = mock_meeting
            url = reverse("legal-meeting-submit", args=[meeting.id])
            response = legal_user_client.post(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_submit_unauthenticated_returns_401(self, anon_client, meeting):
        url = reverse("legal-meeting-submit", args=[meeting.id])
        response = anon_client.post(url)
        assert response.status_code == 401


class TestMeetingWorkflowStatusAPI:

    @pytest.mark.django_db
    def test_status_no_plan_returns_200(
        self, legal_user_client, meeting, allow_all_permissions,
    ):
        with patch(f"{MEETING_VIEW_MODULE}.LegalMeetingService") as MockService:
            MockService.return_value.get_workflow_status.return_value = None
            url = reverse("legal-meeting-workflow-status", args=[meeting.id])
            response = legal_user_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["has_workflow"] is False

    @pytest.mark.django_db
    def test_status_with_plan_returns_200(
        self, legal_user_client, meeting_with_workflow, allow_all_permissions,
    ):
        status_data = {
            "has_workflow": True,
            "plan_id": str(PLAN_UUID),
            "workflow_plan_id": str(PLAN_UUID),
            "status": "active",
            "current_stage": "meeting_preparation",
            "current_stage_id": str(uuid.uuid4()),
            "current_stage_data": None,
            "available_actions": [],
            "stages": [],
            "metadata": {},
            "is_completed": False,
        }
        with patch(f"{MEETING_VIEW_MODULE}.LegalMeetingService") as MockService:
            MockService.return_value.get_workflow_status.return_value = status_data
            url = reverse("legal-meeting-workflow-status", args=[meeting_with_workflow.id])
            response = legal_user_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["has_workflow"] is True


class TestMeetingWorkflowHistoryAPI:

    @pytest.mark.django_db
    def test_history_no_plan_returns_200(
        self, legal_user_client, meeting, allow_all_permissions,
    ):
        with patch(f"{MEETING_VIEW_MODULE}.LegalMeetingService") as MockService:
            MockService.return_value.get_workflow_history.return_value = []
            url = reverse("legal-meeting-workflow-history", args=[meeting.id])
            response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_history_with_plan(
        self, legal_user_client, meeting_with_workflow, allow_all_permissions,
    ):
        activity = [{"event": "started", "at": "2026-01-01T00:00:00Z"}]
        with patch(f"{MEETING_VIEW_MODULE}.LegalMeetingService") as MockService:
            MockService.return_value.get_workflow_history.return_value = activity
            url = reverse("legal-meeting-workflow-history", args=[meeting_with_workflow.id])
            response = legal_user_client.get(url)
        assert response.status_code == 200


class TestMeetingWorkflowActionAPI:

    @pytest.mark.django_db
    def test_action_returns_200(
        self, legal_user_client, meeting_with_workflow, allow_all_permissions,
    ):
        action_result = {
            "action": "approve",
            "new_stage_status": "completed",
            "plan_status": "active",
            "next_stage": "meeting_execution",
            "next_stage_id": str(uuid.uuid4()),
        }
        with patch(f"{MEETING_VIEW_MODULE}.LegalMeetingService") as MockService:
            MockService.return_value.advance_workflow_stage.return_value = action_result
            url = reverse("legal-meeting-workflow-action", args=[meeting_with_workflow.id])
            response = legal_user_client.post(
                url, {"action": "approve"}, format="json",
            )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_action_missing_action_returns_400(
        self, legal_user_client, meeting_with_workflow, allow_all_permissions,
    ):
        url = reverse("legal-meeting-workflow-action", args=[meeting_with_workflow.id])
        response = legal_user_client.post(url, {}, format="json")
        assert response.status_code == 400


class TestMeetingCancelWorkflowAPI:

    @pytest.mark.django_db
    def test_cancel_returns_200(
        self, legal_user_client, meeting_with_workflow, allow_all_permissions,
    ):
        with patch(f"{MEETING_VIEW_MODULE}.LegalMeetingService") as MockService:
            MockService.return_value.cancel_workflow_plan.return_value = meeting_with_workflow
            url = reverse("legal-meeting-cancel-workflow", args=[meeting_with_workflow.id])
            response = legal_user_client.post(url)
        assert response.status_code == 200
