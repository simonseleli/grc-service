"""
Legal Module — Service layer tests.

Covers all workflow-related service classes:
  - LegalMeetingService   (Meeting lifecycle)
  - LegalCaseService      (CaseDefendant / CasePlaintiff closure)
  - LegalMinutesService   (Minutes approval)
  - LegalFilingService    (FilingDefendant / FilingPlaintiff approval)
  - LegalSettlementService (SettlementDefendant / SettlementPlaintiff approval)
  - LegalJudgmentService  (JudgmentDefendant / JudgmentPlaintiff decision + appeal)

Pattern: mirrors tests/api/test_working_paper_workflow.py
"""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from tests.legal.conftest import (
    LEGAL_USER_ID, LEGAL_OFFICER_ID, LEGAL_MANAGER_ID, PLAN_UUID,
)

# Path for patching messaging_service in lazy-import publish helpers
MSG_SVC_PATH = "apps.infrastructure.services.messaging_service.messaging_service"

# ── Module path shortcuts for patching ────────────────────────────────────
MEETING_SERVICE_MODULE  = "apps.core.services.legal_meeting_service"
CASE_SERVICE_MODULE     = "apps.core.services.legal_case_service"
MINUTES_SERVICE_MODULE  = "apps.core.services.legal_minutes_service"
FILING_SERVICE_MODULE   = "apps.core.services.legal_filing_service"
SETTLEMENT_SERVICE_MODULE = "apps.core.services.legal_settlement_service"
JUDGMENT_SERVICE_MODULE = "apps.core.services.legal_judgment_service"


# ── Fake result objects ───────────────────────────────────────────────────

@dataclass
class FakeWorkflowPlanResult:
    plan_id: str
    status: str
    current_stage_id: Optional[str]
    current_stage_name: Optional[str]
    stages: List[Dict[str, Any]]
    metadata: Dict[str, Any]


@dataclass
class FakeAdvanceResult:
    new_status: str
    plan_status: str
    next_stage_id: Optional[str]
    next_stage_name: Optional[str]


def make_fake_plan_result(plan_id=None, stage_id=None, stage_name="stage_one"):
    return FakeWorkflowPlanResult(
        plan_id=plan_id or str(uuid.uuid4()),
        status="active",
        current_stage_id=stage_id or str(uuid.uuid4()),
        current_stage_name=stage_name,
        stages=[],
        metadata={},
    )


def make_fake_advance_result(next_stage_name="stage_two", plan_status="active"):
    return FakeAdvanceResult(
        new_status="completed",
        plan_status=plan_status,
        next_stage_id=str(uuid.uuid4()),
        next_stage_name=next_stage_name,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LegalMeetingService
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalMeetingService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_mixin_fields(self, meeting):
        fake_plan_id = str(uuid.uuid4())
        fake_stage_id = str(uuid.uuid4())
        fake_result = make_fake_plan_result(
            plan_id=fake_plan_id, stage_id=fake_stage_id,
            stage_name="meeting_preparation",
        )

        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_meeting_service import LegalMeetingService
            entity = LegalMeetingService().submit_for_approval(
                meeting_id=str(meeting.id), submitter_id=str(LEGAL_USER_ID),
            )

        entity.refresh_from_db()
        assert str(entity.workflow_plan_id) == fake_plan_id
        assert entity.workflow_stage == "meeting_preparation"
        assert str(entity.workflow_stage_id) == fake_stage_id
        assert entity.workflow_started_at is not None
        assert entity.workflow_completed_at is None

    @pytest.mark.django_db
    def test_submit_sets_status_to_registered(self, meeting):
        fake_result = make_fake_plan_result()
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_meeting_service import LegalMeetingService
            entity = LegalMeetingService().submit_for_approval(
                meeting_id=str(meeting.id), submitter_id=str(LEGAL_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.status == "registered"

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, meeting):
        fake_result = make_fake_plan_result()
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_meeting_service import LegalMeetingService
            LegalMeetingService().submit_for_approval(
                meeting_id=str(meeting.id), submitter_id=str(LEGAL_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.legal_meeting_lifecycle"

    @pytest.mark.django_db
    def test_submit_passes_subject_ref(self, meeting):
        fake_result = make_fake_plan_result()
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_meeting_service import LegalMeetingService
            LegalMeetingService().submit_for_approval(
                meeting_id=str(meeting.id), submitter_id=str(LEGAL_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["subject_ref"] == str(meeting.id)

    @pytest.mark.django_db
    def test_submit_idempotent_with_existing_plan(self, meeting_with_workflow):
        """Submitting again when plan already exists should skip."""
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            from apps.core.services.legal_meeting_service import LegalMeetingService
            entity = LegalMeetingService().submit_for_approval(
                meeting_id=str(meeting_with_workflow.id),
                submitter_id=str(LEGAL_USER_ID),
            )
        MockClient.return_value.start_workflow.assert_not_called()
        assert str(entity.workflow_plan_id) == str(PLAN_UUID)

    @pytest.mark.django_db
    def test_get_workflow_status_no_plan(self, meeting):
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient"):
            from apps.core.services.legal_meeting_service import LegalMeetingService
            result = LegalMeetingService().get_workflow_status(
                meeting_id=str(meeting.id),
            )
        assert result is None

    @pytest.mark.django_db
    def test_get_workflow_status_with_plan(self, meeting_with_workflow):
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            from apps.core.services.legal_meeting_service import LegalMeetingService
            result = LegalMeetingService().get_workflow_status(
                meeting_id=str(meeting_with_workflow.id),
            )
        assert result["has_workflow"] is True
        assert result["plan_id"] == str(PLAN_UUID)

    @pytest.mark.django_db
    def test_get_workflow_history_no_plan(self, meeting):
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient"):
            from apps.core.services.legal_meeting_service import LegalMeetingService
            result = LegalMeetingService().get_workflow_history(
                meeting_id=str(meeting.id),
            )
        assert result == []

    @pytest.mark.django_db
    def test_advance_workflow_stage(self, meeting_with_workflow):
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(next_stage_name="meeting_execution")

        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_meeting_service import LegalMeetingService
            result = LegalMeetingService().advance_workflow_stage(
                meeting_id=str(meeting_with_workflow.id),
                action="approve",
                actor_id=str(LEGAL_MANAGER_ID),
            )
        assert result["action"] == "approve"
        assert result["next_stage"] == "meeting_execution"

    @pytest.mark.django_db
    def test_advance_no_workflow_raises(self, meeting):
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient"):
            from apps.core.services.legal_meeting_service import LegalMeetingService
            with pytest.raises(ValueError, match="No active workflow"):
                LegalMeetingService().advance_workflow_stage(
                    meeting_id=str(meeting.id),
                    action="approve",
                    actor_id=str(LEGAL_MANAGER_ID),
                )

    @pytest.mark.django_db
    def test_cancel_workflow(self, meeting_with_workflow):
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.legal_meeting_service import LegalMeetingService
            entity = LegalMeetingService().cancel_workflow_plan(
                meeting_id=str(meeting_with_workflow.id),
                actor_id=str(LEGAL_MANAGER_ID),
                reason="Test cancellation",
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None

    @pytest.mark.django_db
    def test_cancel_no_workflow_raises(self, meeting):
        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient"):
            from apps.core.services.legal_meeting_service import LegalMeetingService
            with pytest.raises(ValueError, match="No active workflow"):
                LegalMeetingService().cancel_workflow_plan(
                    meeting_id=str(meeting.id),
                    actor_id=str(LEGAL_MANAGER_ID),
                )

    @pytest.mark.django_db
    def test_advance_publishes_completed_event(self, meeting_with_workflow):
        """When workflow completes, a MEETING_COMPLETED Kafka event is published."""
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(plan_status="completed")

        with patch(f"{MEETING_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(MSG_SVC_PATH) as mock_msg:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_meeting_service import LegalMeetingService
            LegalMeetingService().advance_workflow_stage(
                meeting_id=str(meeting_with_workflow.id),
                action="approve",
                actor_id=str(LEGAL_MANAGER_ID),
            )
        mock_msg.publish_legal_meeting_event.assert_called_once()
        call_kw = mock_msg.publish_legal_meeting_event.call_args.kwargs
        assert call_kw["event_type"] == "grc.legal.meeting.completed"


# ═══════════════════════════════════════════════════════════════════════════════
# LegalCaseService
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalCaseService:

    @pytest.mark.django_db
    def test_submit_defendant_saves_workflow_fields(self, case_defendant):
        fake_plan_id = str(uuid.uuid4())
        fake_stage_id = str(uuid.uuid4())
        fake_result = make_fake_plan_result(
            plan_id=fake_plan_id, stage_id=fake_stage_id,
            stage_name="case_officer_review",
        )
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_case_service import LegalCaseService
            entity = LegalCaseService().submit_for_approval(
                entity_id=str(case_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="defendant",
            )
        entity.refresh_from_db()
        assert str(entity.workflow_plan_id) == fake_plan_id
        assert entity.workflow_stage == "case_officer_review"
        assert entity.status == "under_dg_review"

    @pytest.mark.django_db
    def test_submit_plaintiff_saves_workflow_fields(self, case_plaintiff):
        fake_result = make_fake_plan_result(stage_name="case_officer_review")
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_case_service import LegalCaseService
            entity = LegalCaseService().submit_for_approval(
                entity_id=str(case_plaintiff.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="plaintiff",
            )
        entity.refresh_from_db()
        assert entity.status == "under_dg_review"
        assert entity.workflow_plan_id is not None

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, case_defendant):
        fake_result = make_fake_plan_result()
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_case_service import LegalCaseService
            LegalCaseService().submit_for_approval(
                entity_id=str(case_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.legal_case_closure"

    @pytest.mark.django_db
    def test_invalid_side_raises(self):
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient"):
            from apps.core.services.legal_case_service import LegalCaseService
            with pytest.raises(ValueError, match="Invalid side"):
                LegalCaseService()._get_model("invalid")

    @pytest.mark.django_db
    def test_advance_defendant_workflow(self, case_defendant_active):
        fake_plan = make_fake_plan_result()
        fake_advance = make_fake_advance_result(next_stage_name="dg_closure_noting")
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_case_service import LegalCaseService
            result = LegalCaseService().advance_workflow_stage(
                entity_id=str(case_defendant_active.id),
                action="approve",
                actor_id=str(LEGAL_MANAGER_ID),
                side="defendant",
            )
        assert result["next_stage"] == "dg_closure_noting"

    @pytest.mark.django_db
    def test_cancel_defendant_workflow(self, case_defendant_active):
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.legal_case_service import LegalCaseService
            entity = LegalCaseService().cancel_workflow_plan(
                entity_id=str(case_defendant_active.id),
                actor_id=str(LEGAL_MANAGER_ID),
                side="defendant",
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None

    @pytest.mark.django_db
    def test_get_status_plaintiff_no_plan(self, case_plaintiff):
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient"):
            from apps.core.services.legal_case_service import LegalCaseService
            result = LegalCaseService().get_workflow_status(
                entity_id=str(case_plaintiff.id), side="plaintiff",
            )
        assert result is None

    @pytest.mark.django_db
    def test_submit_publishes_case_created_event(self, case_defendant):
        """On workflow start, a CASE_CREATED Kafka event is published."""
        fake_result = make_fake_plan_result()
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(MSG_SVC_PATH) as mock_msg:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_case_service import LegalCaseService
            LegalCaseService().submit_for_approval(
                entity_id=str(case_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="defendant",
            )
        mock_msg.publish_legal_case_event.assert_called_once()
        call_kw = mock_msg.publish_legal_case_event.call_args.kwargs
        assert call_kw["event_type"] == "grc.legal.case.created"

    @pytest.mark.django_db
    def test_advance_publishes_case_closed_event(self, case_defendant_active):
        """When workflow completes, a CASE_CLOSED Kafka event is published."""
        fake_plan = make_fake_plan_result()
        fake_advance = make_fake_advance_result(plan_status="completed")
        with patch(f"{CASE_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(MSG_SVC_PATH) as mock_msg:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_case_service import LegalCaseService
            LegalCaseService().advance_workflow_stage(
                entity_id=str(case_defendant_active.id),
                action="approve",
                actor_id=str(LEGAL_MANAGER_ID),
                side="defendant",
            )
        mock_msg.publish_legal_case_event.assert_called_once()
        call_kw = mock_msg.publish_legal_case_event.call_args.kwargs
        assert call_kw["event_type"] == "grc.legal.case.closed"


# ═══════════════════════════════════════════════════════════════════════════════
# LegalMinutesService
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalMinutesService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_fields(self, minutes):
        fake_plan_id = str(uuid.uuid4())
        fake_result = make_fake_plan_result(
            plan_id=fake_plan_id, stage_name="minutes_review",
        )
        with patch(f"{MINUTES_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_minutes_service import LegalMinutesService
            entity = LegalMinutesService().submit_for_approval(
                minutes_id=str(minutes.id),
                submitter_id=str(LEGAL_USER_ID),
            )
        entity.refresh_from_db()
        assert str(entity.workflow_plan_id) == fake_plan_id
        assert entity.status == "pending_approval"

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, minutes):
        fake_result = make_fake_plan_result()
        with patch(f"{MINUTES_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_minutes_service import LegalMinutesService
            LegalMinutesService().submit_for_approval(
                minutes_id=str(minutes.id),
                submitter_id=str(LEGAL_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.legal_minutes_approval"

    @pytest.mark.django_db
    def test_idempotent_with_existing_plan(self, minutes_with_workflow):
        with patch(f"{MINUTES_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            from apps.core.services.legal_minutes_service import LegalMinutesService
            LegalMinutesService().submit_for_approval(
                minutes_id=str(minutes_with_workflow.id),
                submitter_id=str(LEGAL_USER_ID),
            )
        MockClient.return_value.start_workflow.assert_not_called()

    @pytest.mark.django_db
    def test_cancel_workflow(self, minutes_with_workflow):
        with patch(f"{MINUTES_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.legal_minutes_service import LegalMinutesService
            entity = LegalMinutesService().cancel_workflow_plan(
                minutes_id=str(minutes_with_workflow.id),
                actor_id=str(LEGAL_MANAGER_ID),
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None

    @pytest.mark.django_db
    def test_advance_publishes_minutes_approved_event(self, minutes_with_workflow):
        """When workflow completes, a MINUTES_APPROVED Kafka event is published."""
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(plan_status="completed")
        with patch(f"{MINUTES_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(MSG_SVC_PATH) as mock_msg:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_minutes_service import LegalMinutesService
            LegalMinutesService().advance_workflow_stage(
                minutes_id=str(minutes_with_workflow.id),
                action="approve",
                actor_id=str(LEGAL_MANAGER_ID),
            )
        mock_msg.publish_legal_minutes_event.assert_called_once()
        call_kw = mock_msg.publish_legal_minutes_event.call_args.kwargs
        assert call_kw["event_type"] == "grc.legal.minutes.approved"


# ═══════════════════════════════════════════════════════════════════════════════
# LegalFilingService
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalFilingService:

    @pytest.mark.django_db
    def test_submit_defendant_saves_workflow_fields(self, filing_defendant):
        fake_result = make_fake_plan_result(stage_name="filing_review")
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_filing_service import LegalFilingService
            entity = LegalFilingService().submit_for_approval(
                entity_id=str(filing_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="defendant",
            )
        entity.refresh_from_db()
        assert entity.workflow_plan_id is not None
        assert entity.status == "under_review_lm"

    @pytest.mark.django_db
    def test_submit_plaintiff_saves_workflow_fields(self, filing_plaintiff):
        fake_result = make_fake_plan_result(stage_name="filing_review")
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_filing_service import LegalFilingService
            entity = LegalFilingService().submit_for_approval(
                entity_id=str(filing_plaintiff.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="plaintiff",
            )
        entity.refresh_from_db()
        assert entity.status == "under_review_lm"

    @pytest.mark.django_db
    def test_uses_correct_template_code(self, filing_defendant):
        fake_result = make_fake_plan_result()
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_filing_service import LegalFilingService
            LegalFilingService().submit_for_approval(
                entity_id=str(filing_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.legal_filing_approval"

    @pytest.mark.django_db
    def test_advance_publishes_filing_approved_event(self, filing_defendant):
        """When filing workflow completes, a FILING_APPROVED Kafka event is published."""
        # First submit to get a workflow plan assigned
        fake_result = make_fake_plan_result(plan_id=str(PLAN_UUID))
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_filing_service import LegalFilingService
            LegalFilingService().submit_for_approval(
                entity_id=str(filing_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
            )
        filing_defendant.refresh_from_db()
        # Now advance to completion
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(plan_status="completed")
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(MSG_SVC_PATH) as mock_msg:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_filing_service import LegalFilingService
            LegalFilingService().advance_workflow_stage(
                entity_id=str(filing_defendant.id),
                action="approve",
                actor_id=str(LEGAL_MANAGER_ID),
            )
        mock_msg.publish_legal_filing_event.assert_called_once()
        call_kw = mock_msg.publish_legal_filing_event.call_args.kwargs
        assert call_kw["event_type"] == "grc.legal.filing.approved"

    @pytest.mark.parametrize("stage_name,expected_status", [
        ("Filing Officer Review", "approved_lm"),
        ("Legal Manager Review", "under_review_dg"),
        ("DG Filing Review", "approved"),
        ("Filing Confirmation", "filed"),
    ])
    @pytest.mark.django_db
    def test_advance_maps_stage_to_entity_status(
        self, filing_defendant, stage_name, expected_status,
    ):
        """GAP-06: Each completed stage maps to the correct entity status."""
        # Submit first to assign a workflow plan
        fake_result = make_fake_plan_result(
            plan_id=str(PLAN_UUID), stage_name=stage_name,
        )
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_filing_service import LegalFilingService
            LegalFilingService().submit_for_approval(
                entity_id=str(filing_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
            )
        filing_defendant.refresh_from_db()
        # Override workflow_stage to the stage being tested
        filing_defendant.workflow_stage = stage_name
        filing_defendant.save(update_fields=["workflow_stage"])

        # Advance — the completed stage should map to expected_status
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID), stage_name=stage_name)
        fake_advance = make_fake_advance_result(
            next_stage_name="Next Stage", plan_status="active",
        )
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_filing_service import LegalFilingService
            LegalFilingService().advance_workflow_stage(
                entity_id=str(filing_defendant.id),
                action="approve",
                actor_id=str(LEGAL_MANAGER_ID),
            )
        filing_defendant.refresh_from_db()
        assert filing_defendant.status == expected_status

    @pytest.mark.django_db
    def test_advance_rejected_action_does_not_change_status(self, filing_defendant):
        """GAP-06: A rejected (non-completed) action does not update entity status."""
        fake_result = make_fake_plan_result(
            plan_id=str(PLAN_UUID), stage_name="Legal Manager Review",
        )
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_filing_service import LegalFilingService
            LegalFilingService().submit_for_approval(
                entity_id=str(filing_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
            )
        filing_defendant.refresh_from_db()
        filing_defendant.workflow_stage = "Legal Manager Review"
        filing_defendant.save(update_fields=["workflow_stage"])

        # Advance with rejected status (not completed)
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = FakeAdvanceResult(
            new_status="rejected",
            plan_status="active",
            next_stage_id=str(uuid.uuid4()),
            next_stage_name="Legal Manager Review",
        )
        with patch(f"{FILING_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_filing_service import LegalFilingService
            LegalFilingService().advance_workflow_stage(
                entity_id=str(filing_defendant.id),
                action="reject",
                actor_id=str(LEGAL_MANAGER_ID),
            )
        filing_defendant.refresh_from_db()
        # Status should remain under_review_lm (set during submit)
        assert filing_defendant.status == "under_review_lm"


# ═══════════════════════════════════════════════════════════════════════════════
# LegalSettlementService
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalSettlementService:

    @pytest.mark.django_db
    def test_submit_defendant_saves_workflow_fields(self, settlement_defendant):
        fake_result = make_fake_plan_result(stage_name="settlement_review")
        with patch(f"{SETTLEMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_settlement_service import LegalSettlementService
            entity = LegalSettlementService().submit_for_approval(
                entity_id=str(settlement_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="defendant",
            )
        entity.refresh_from_db()
        assert entity.workflow_plan_id is not None
        assert entity.status == "under_review"

    @pytest.mark.django_db
    def test_submit_plaintiff_saves_workflow_fields(self, settlement_plaintiff):
        fake_result = make_fake_plan_result(stage_name="settlement_review")
        with patch(f"{SETTLEMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_settlement_service import LegalSettlementService
            entity = LegalSettlementService().submit_for_approval(
                entity_id=str(settlement_plaintiff.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="plaintiff",
            )
        entity.refresh_from_db()
        assert entity.status == "under_review"

    @pytest.mark.django_db
    def test_uses_correct_template_code(self, settlement_defendant):
        fake_result = make_fake_plan_result()
        with patch(f"{SETTLEMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_settlement_service import LegalSettlementService
            LegalSettlementService().submit_for_approval(
                entity_id=str(settlement_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.legal_settlement_approval"

    @pytest.mark.django_db
    def test_advance_publishes_settlement_approved_event(self, settlement_defendant):
        """When settlement workflow completes, a SETTLEMENT_APPROVED event is published."""
        fake_result = make_fake_plan_result(plan_id=str(PLAN_UUID))
        with patch(f"{SETTLEMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_settlement_service import LegalSettlementService
            LegalSettlementService().submit_for_approval(
                entity_id=str(settlement_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
            )
        settlement_defendant.refresh_from_db()
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(plan_status="completed")
        with patch(f"{SETTLEMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(MSG_SVC_PATH) as mock_msg:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.legal_settlement_service import LegalSettlementService
            LegalSettlementService().advance_workflow_stage(
                entity_id=str(settlement_defendant.id),
                action="approve",
                actor_id=str(LEGAL_MANAGER_ID),
            )
        mock_msg.publish_legal_settlement_event.assert_called_once()
        call_kw = mock_msg.publish_legal_settlement_event.call_args.kwargs
        assert call_kw["event_type"] == "grc.legal.settlement.approved"


# ═══════════════════════════════════════════════════════════════════════════════
# LegalJudgmentService
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalJudgmentService:

    @pytest.mark.django_db
    def test_submit_defendant_saves_workflow_fields(self, judgment_defendant):
        fake_result = make_fake_plan_result(stage_name="judgment_review")
        with patch(f"{JUDGMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_judgment_service import LegalJudgmentService
            entity = LegalJudgmentService().submit_for_approval(
                entity_id=str(judgment_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="defendant",
            )
        entity.refresh_from_db()
        assert entity.workflow_plan_id is not None

    @pytest.mark.django_db
    def test_submit_plaintiff_saves_workflow_fields(self, judgment_plaintiff):
        fake_result = make_fake_plan_result(stage_name="judgment_review")
        with patch(f"{JUDGMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_judgment_service import LegalJudgmentService
            entity = LegalJudgmentService().submit_for_approval(
                entity_id=str(judgment_plaintiff.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="plaintiff",
            )
        entity.refresh_from_db()
        assert entity.workflow_plan_id is not None

    @pytest.mark.django_db
    def test_uses_correct_template_code(self, judgment_defendant):
        fake_result = make_fake_plan_result()
        with patch(f"{JUDGMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_judgment_service import LegalJudgmentService
            LegalJudgmentService().submit_for_approval(
                entity_id=str(judgment_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.legal_judgment_decision"

    @pytest.mark.django_db
    def test_process_appeal_decision(self, judgment_defendant):
        with patch(f"{JUDGMENT_SERVICE_MODULE}.OrchestrationClient"), \
             patch(MSG_SVC_PATH):
            from apps.core.services.legal_judgment_service import LegalJudgmentService
            entity = LegalJudgmentService().process_appeal_decision(
                entity_id=str(judgment_defendant.id),
                decision="appeal",
                actor_id=str(LEGAL_MANAGER_ID),
                side="defendant",
            )
        entity.refresh_from_db()
        assert entity.dg_decision == "appeal"
        # Auto-created records
        assert entity.appeal_filing is not None
        assert entity.appeal_filing.filing_type == "notice_of_appeal"
        assert entity.appeal_task is not None
        assert entity.appeal_task.status == "open"
        assert entity.appeal_task.priority == "high"
        from apps.core.models import AppealDefendant
        appeal = AppealDefendant.objects.get(judgment=entity)
        assert appeal.status == "pending"
        # Case status updated
        entity.case_defendant.refresh_from_db()
        assert entity.case_defendant.status == "appeal_filed"

    @pytest.mark.django_db
    def test_process_appeal_decision_accept(self, judgment_plaintiff):
        with patch(f"{JUDGMENT_SERVICE_MODULE}.OrchestrationClient"):
            from apps.core.services.legal_judgment_service import LegalJudgmentService
            entity = LegalJudgmentService().process_appeal_decision(
                entity_id=str(judgment_plaintiff.id),
                decision="accept",
                actor_id=str(LEGAL_MANAGER_ID),
                side="plaintiff",
            )
        entity.refresh_from_db()
        assert entity.dg_decision == "accept"
        # Accept must NOT create any records
        assert entity.appeal_filing is None
        assert entity.appeal_task is None
        from apps.core.models import AppealPlaintiff
        assert not AppealPlaintiff.objects.filter(judgment=entity).exists()

    @pytest.mark.django_db
    def test_appeal_decision_creates_plaintiff_records(self, judgment_plaintiff):
        with patch(f"{JUDGMENT_SERVICE_MODULE}.OrchestrationClient"), \
             patch(MSG_SVC_PATH):
            from apps.core.services.legal_judgment_service import LegalJudgmentService
            entity = LegalJudgmentService().process_appeal_decision(
                entity_id=str(judgment_plaintiff.id),
                decision="appeal",
                actor_id=str(LEGAL_MANAGER_ID),
                side="plaintiff",
            )
        entity.refresh_from_db()
        assert entity.dg_decision == "appeal"
        assert entity.appeal_filing is not None
        assert entity.appeal_filing.filing_type == "notice_of_appeal"
        assert entity.appeal_task is not None
        from apps.core.models import AppealPlaintiff
        appeal = AppealPlaintiff.objects.get(judgment=entity)
        assert appeal.status == "pending"
        entity.case_plaintiff.refresh_from_db()
        assert entity.case_plaintiff.status == "appeal_filed"

    @pytest.mark.django_db
    def test_appeal_decision_publishes_event(self, judgment_defendant):
        with patch(f"{JUDGMENT_SERVICE_MODULE}.OrchestrationClient"), \
             patch(MSG_SVC_PATH) as mock_msg:
            from apps.core.services.legal_judgment_service import LegalJudgmentService
            LegalJudgmentService().process_appeal_decision(
                entity_id=str(judgment_defendant.id),
                decision="appeal",
                actor_id=str(LEGAL_MANAGER_ID),
                side="defendant",
            )
        mock_msg.publish_legal_judgment_event.assert_called_once()
        call_kw = mock_msg.publish_legal_judgment_event.call_args.kwargs
        assert call_kw["event_type"] == "grc.legal.judgment.appeal_decision"

    @pytest.mark.django_db
    def test_submit_publishes_judgment_recorded_event(self, judgment_defendant):
        """On workflow start, a JUDGMENT_RECORDED Kafka event is published."""
        fake_result = make_fake_plan_result()
        with patch(f"{JUDGMENT_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(MSG_SVC_PATH) as mock_msg:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.legal_judgment_service import LegalJudgmentService
            LegalJudgmentService().submit_for_approval(
                entity_id=str(judgment_defendant.id),
                submitter_id=str(LEGAL_OFFICER_ID),
                side="defendant",
            )
        mock_msg.publish_legal_judgment_event.assert_called_once()
        call_kw = mock_msg.publish_legal_judgment_event.call_args.kwargs
        assert call_kw["event_type"] == "grc.legal.judgment.recorded"
