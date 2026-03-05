"""
Comprehensive FIMS-aligned tests for the Working Paper workflow integration.

Each test is mapped to a specific requirement in workflow-integration-guide.md.
Tests are NOT weakened to make them pass — they verify actual FIMS contracts.

Coverage:
  § 4.1  Model method contracts (get_workflow_context, get_workflow_metadata)
  § 4.2  WorkingPaperService.submit_for_approval → start_workflow signature
  § 4.4  API view contracts (status codes, response shapes, auth, error codes)
  § 5.1  Frontend-consumed response fields (has_workflow, workflow_plan_id, etc.)
"""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from conftest import PREPARER_ID, OTHER_USER_ID, PLAN_ID, DOCUMENT_ID

# ---------------------------------------------------------------------------
# Module path shortcuts for patching
# ---------------------------------------------------------------------------
WP_VIEW_MODULE = "apps.api.views.working_paper_views"
WP_SERVICE_MODULE = "apps.core.services.working_paper_service"


# ---------------------------------------------------------------------------
# A proper WorkflowPlanResult stand-in for service-layer mocking.
# The service does   result.plan_id / result.current_stage_name / result.current_stage_id
# so the mock must be an object with those attributes — NOT a plain dict.
# ---------------------------------------------------------------------------

@dataclass
class FakeWorkflowPlanResult:
    plan_id: str
    status: str
    current_stage_id: Optional[str]
    current_stage_name: Optional[str]
    stages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: Optional[str] = None


def make_fake_plan_result(plan_id=None, stage_id=None, stage_name="working_paper_review"):
    return FakeWorkflowPlanResult(
        plan_id=plan_id or str(uuid.uuid4()),
        status="active",
        current_stage_id=stage_id or str(uuid.uuid4()),
        current_stage_name=stage_name,
        stages=[],
        metadata={},
    )


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def url_status(paper_id):
    return reverse("working-paper-workflow-status", args=[paper_id])


def url_history(paper_id):
    return reverse("working-paper-workflow-history", args=[paper_id])


def url_review(paper_id):
    return reverse("working-paper-review", args=[paper_id])


# ===========================================================================
# § 4.1  Model method contracts
# ===========================================================================

class TestWorkingPaperModelMethods:
    """
    guide §4.1 / §4.2: The model must expose get_workflow_context() and
    get_workflow_metadata() with the exact field set that the service passes
    to Work Orchestration.
    """

    @pytest.mark.django_db
    def test_get_workflow_context_contains_required_fields(self, working_paper):
        """
        guide §4.1: context is used by WO to resolve stage assignees.
        Must include prepared_by, engagement_id, working_paper_id, paper_type.
        """
        ctx = working_paper.get_workflow_context()

        assert "prepared_by" in ctx, "prepared_by missing from workflow context"
        assert "engagement_id" in ctx, "engagement_id missing from workflow context"
        assert "working_paper_id" in ctx, "working_paper_id missing from workflow context"
        assert "paper_type" in ctx, "paper_type missing from workflow context"

        assert ctx["prepared_by"] == str(PREPARER_ID)
        assert ctx["working_paper_id"] == str(working_paper.id)
        assert ctx["paper_type"] == "fieldwork"

    @pytest.mark.django_db
    def test_get_workflow_metadata_contains_entity_detail_path(self, working_paper):
        """
        guide §4.1 + §3: metadata must include entity_detail_path so the WO
        console can render a 'View full details' link back to the GRC service UI.
        """
        meta = working_paper.get_workflow_metadata()

        assert "entity_detail_path" in meta, (
            "entity_detail_path missing from workflow metadata — "
            "check add_entity_detail_path_to_metadata() call in get_workflow_metadata()"
        )
        assert meta["entity_detail_path"] == "/service/grc/working-papers"

    @pytest.mark.django_db
    def test_get_workflow_metadata_contains_required_display_fields(self, working_paper):
        """
        guide §4.1: metadata is stored with the WO plan and displayed in the console.
        Must include entity_type, entity_id, reference_number, title.
        """
        meta = working_paper.get_workflow_metadata()

        assert meta.get("entity_type") == "working_paper"
        assert meta.get("entity_id") == str(working_paper.id)
        assert meta.get("reference_number") == working_paper.reference_number
        assert meta.get("title") == working_paper.title


# ===========================================================================
# § 4.2  WorkingPaperService.submit_for_approval — start_workflow signature
# ===========================================================================

class TestWorkingPaperServiceFIMSContract:
    """
    guide §4.2 + §4.3: The service must call OrchestrationClient.start_workflow
    with exactly the signature specified in the guide. Tests verify each argument
    using the actual call args (positional vs keyword as the service uses them).
    """

    @pytest.mark.django_db
    def test_submit_saves_all_five_workflow_mixin_fields(self, working_paper):
        """
        guide §4.1 WorkflowMixin: all 5 fields must be persisted after a
        successful submit_for_approval.
          workflow_plan_id  → from result.plan_id
          workflow_stage    → from result.current_stage_name
          workflow_stage_id → from result.current_stage_id
          workflow_started_at → set to now()
          workflow_completed_at → stays null (plan is just starting)
        """
        fake_plan_id = str(uuid.uuid4())
        fake_stage_id = str(uuid.uuid4())

        # IMPORTANT: mock returns a WorkflowPlanResult-compatible object.
        # Returning a plain dict would cause AttributeError on result.plan_id.
        fake_result = make_fake_plan_result(
            plan_id=fake_plan_id,
            stage_id=fake_stage_id,
            stage_name="working_paper_review",
        )

        with patch(f"{WP_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.working_paper_service import WorkingPaperService
            result = WorkingPaperService().submit_for_approval(
                working_paper_id=str(working_paper.id),
                submitter_id=str(PREPARER_ID),
            )

        result.refresh_from_db()
        assert str(result.workflow_plan_id) == fake_plan_id
        assert result.workflow_stage == "working_paper_review"
        assert str(result.workflow_stage_id) == fake_stage_id
        assert result.workflow_started_at is not None
        assert result.workflow_completed_at is None

    @pytest.mark.django_db
    def test_submit_calls_start_workflow_with_correct_template_code(self, working_paper):
        """
        guide §4.2: WORKFLOW_TEMPLATE_CODE = 'grc.working_paper_approval'.
        This is the first POSITIONAL argument to start_workflow — verified via
        call_args.args[0], NOT call_args.kwargs (which would always return None
        for positional args).
        """
        fake_result = make_fake_plan_result()

        with patch(f"{WP_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.working_paper_service import WorkingPaperService
            WorkingPaperService().submit_for_approval(
                working_paper_id=str(working_paper.id),
                submitter_id=str(PREPARER_ID),
            )

        call_args = MockClient.return_value.start_workflow.call_args
        # template_code is the 1st positional arg (index 0)
        assert call_args.args[0] == "grc.working_paper_approval", (
            f"Expected 'grc.working_paper_approval' at args[0], got {call_args.args}"
        )

    @pytest.mark.django_db
    def test_submit_passes_initiator_id_as_submitter(self, working_paper):
        """
        guide §4.3: initiator_id is the 3rd positional argument to start_workflow.
        It must equal the submitter_id passed to submit_for_approval.
        """
        fake_result = make_fake_plan_result()

        with patch(f"{WP_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.working_paper_service import WorkingPaperService
            WorkingPaperService().submit_for_approval(
                working_paper_id=str(working_paper.id),
                submitter_id=str(PREPARER_ID),
            )

        call_args = MockClient.return_value.start_workflow.call_args
        # initiator_id is the 3rd positional arg (index 2)
        assert call_args.args[2] == str(PREPARER_ID), (
            f"Expected PREPARER_ID at args[2], got {call_args.args}"
        )

    @pytest.mark.django_db
    def test_submit_passes_subject_ref_as_paper_uuid(self, working_paper):
        """
        guide §4.3: subject_ref is a keyword argument that ties the workflow
        plan back to the originating entity. Must be the working paper's UUID.
        """
        fake_result = make_fake_plan_result()

        with patch(f"{WP_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.working_paper_service import WorkingPaperService
            WorkingPaperService().submit_for_approval(
                working_paper_id=str(working_paper.id),
                submitter_id=str(PREPARER_ID),
            )

        call_args = MockClient.return_value.start_workflow.call_args
        # subject_ref is a keyword argument
        assert call_args.kwargs.get("subject_ref") == str(working_paper.id)

    @pytest.mark.django_db
    def test_submit_sets_review_status_to_pending(self, working_paper):
        """
        guide §4.2 step 5: after a successful workflow start the entity's
        local status must be updated. For WorkingPaper, review_status → 'pending'.
        """
        fake_result = make_fake_plan_result()

        with patch(f"{WP_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.working_paper_service import WorkingPaperService
            WorkingPaperService().submit_for_approval(
                working_paper_id=str(working_paper.id),
                submitter_id=str(PREPARER_ID),
            )

        working_paper.refresh_from_db()
        assert working_paper.review_status == "pending"

    @pytest.mark.django_db
    def test_submit_skips_if_plan_already_exists(self, working_paper_with_plan):
        """
        Idempotency guard: if workflow_plan_id is already set, the service must
        exit early without calling start_workflow again.
        """
        with patch(f"{WP_SERVICE_MODULE}.OrchestrationClient") as MockClient:
            from apps.core.services.working_paper_service import WorkingPaperService
            WorkingPaperService().submit_for_approval(
                working_paper_id=str(working_paper_with_plan.id),
                submitter_id=str(PREPARER_ID),
            )

        MockClient.return_value.start_workflow.assert_not_called()


# ===========================================================================
# § 4.4 + § 5.1  WorkingPaperWorkflowStatusView
# ===========================================================================

class TestWorkflowStatusView:
    """
    GET /working-papers/<id>/workflow-status/

    guide §4.4 / §5.1: Frontend reads has_workflow to decide whether to show
    the submit button or the workflow console. This endpoint must NEVER return
    404 — the frontend polls it for all papers regardless of plan state.
    """

    @pytest.mark.django_db
    def test_no_plan_returns_200_with_has_workflow_false(self, preparer_client, working_paper):
        """
        guide §4.4: When no workflow_plan_id, return 200 with has_workflow=false.
        Returning 404 breaks the frontend which unconditionally calls this endpoint.
        """
        response = preparer_client.get(url_status(working_paper.id))

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert data["has_workflow"] is False
        # 'status' exposed so frontend can show current review_status
        assert data["status"] == "draft"

    @pytest.mark.django_db
    def test_with_plan_returns_has_workflow_true_and_all_fields(
        self, preparer_client, working_paper_with_plan
    ):
        """
        guide §5.1 WorkflowStatusResponse: when a plan exists the response must
        include has_workflow=true, workflow_plan_id, workflow_stage,
        workflow_stage_id, status, and the raw plan object for the console.
        """
        fake_plan_detail = {"id": str(PLAN_ID), "status": "active", "stages": []}

        with patch(f"{WP_VIEW_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan_status.return_value = fake_plan_detail
            response = preparer_client.get(url_status(working_paper_with_plan.id))

        assert response.status_code == 200
        data = response.json()["data"]
        # guide §5.1 required fields
        assert data["has_workflow"] is True
        assert data["workflow_plan_id"] == str(PLAN_ID)
        assert data["workflow_stage"] == "working_paper_review"
        assert data["workflow_stage_id"] is not None
        assert data["status"] == "pending"          # entity's own review_status
        assert data["plan"] == fake_plan_detail     # raw WO plan for console

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, working_paper):
        """JWT authentication is required (enforced by middleware, not the view)."""
        response = anon_client.get(url_status(working_paper.id))
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_wo_service_error_returns_502(self, preparer_client, working_paper_with_plan):
        """When Work Orchestration is unreachable the view should return 502."""
        with patch(f"{WP_VIEW_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan_status.side_effect = ConnectionError("WO down")
            response = preparer_client.get(url_status(working_paper_with_plan.id))

        assert response.status_code == 502
        assert response.json()["success"] is False


# ===========================================================================
# § 4.4  WorkingPaperWorkflowHistoryView
# ===========================================================================

class TestWorkflowHistoryView:
    """
    GET /working-papers/<id>/workflow-history/

    Must never return 404. Frontend polls this for activity timeline regardless
    of whether a workflow has been started.
    """

    @pytest.mark.django_db
    def test_no_plan_returns_200_with_empty_activity_list(self, preparer_client, working_paper):
        """
        guide §4.4: When no plan, return 200 with has_workflow=false and activity=[].
        The frontend renders an empty timeline, not an error.
        """
        response = preparer_client.get(url_history(working_paper.id))

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert data["has_workflow"] is False
        assert data["activity"] == []

    @pytest.mark.django_db
    def test_with_plan_returns_has_workflow_true_and_activity(
        self, preparer_client, working_paper_with_plan
    ):
        fake_activity = [
            {
                "event": "stage_started",
                "stage": "working_paper_review",
                "at": "2026-02-19T10:00:00Z",
                "actor_id": str(PREPARER_ID),
            },
        ]

        with patch(f"{WP_VIEW_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan_activity.return_value = fake_activity
            response = preparer_client.get(url_history(working_paper_with_plan.id))

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["has_workflow"] is True
        assert data["workflow_plan_id"] == str(PLAN_ID)
        assert data["activity"] == fake_activity

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, working_paper):
        """JWT authentication is required (enforced by middleware, not the view)."""
        response = anon_client.get(url_history(working_paper.id))
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_wo_service_error_returns_502(self, preparer_client, working_paper_with_plan):
        with patch(f"{WP_VIEW_MODULE}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan_activity.side_effect = RuntimeError("timeout")
            response = preparer_client.get(url_history(working_paper_with_plan.id))

        assert response.status_code == 502
        assert response.json()["success"] is False


# ===========================================================================
# § 4.4  WorkingPaperReviewView  POST — submission
# ===========================================================================

class TestSubmitForApprovalView:
    """
    POST /working-papers/<id>/review/

    guide §4.4: Submit endpoint must guard against non-preparers, non-draft
    papers, and WO failures. On success it must return workflow_plan_id at the
    top level of the response so the frontend can update state immediately.
    """

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, working_paper):
        """JWT authentication is required (enforced by middleware)."""
        response = anon_client.post(url_review(working_paper.id))
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_non_preparer_returns_403_permission_denied(self, other_client, working_paper):
        """
        guide §4.4: Only the user whose UUID matches prepared_by may submit.
        Any other authenticated user must receive 403 PERMISSION_DENIED.
        """
        response = other_client.post(url_review(working_paper.id))
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "PERMISSION_DENIED"

    @pytest.mark.django_db
    def test_non_draft_returns_400_invalid_status(self, preparer_client, working_paper):
        """
        guide §4.4: Submitting a paper that is not in 'draft' status must return
        400 INVALID_STATUS. Prevents double-submission.
        """
        working_paper.review_status = "pending"
        working_paper.save()

        response = preparer_client.post(url_review(working_paper.id))
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_STATUS"

    @pytest.mark.django_db
    def test_wo_failure_returns_500(self, preparer_client, working_paper):
        """When WO is unavailable the view must return 500 (not crash with 500 traceback)."""
        with patch(f"{WP_VIEW_MODULE}.WorkingPaperService") as MockService:
            MockService.return_value.submit_for_approval.side_effect = RuntimeError("WO unavailable")
            response = preparer_client.post(url_review(working_paper.id))

        assert response.status_code == 500
        assert response.json()["success"] is False

    @pytest.mark.django_db
    def test_success_returns_200_with_workflow_plan_id_at_top_level(
        self, preparer_client, working_paper
    ):
        """
        guide §5.1: On success the response body must include workflow_plan_id at
        the TOP LEVEL (not nested inside data) so the frontend can update
        workflowPlanId state without waiting for the next polling cycle.

        We mock OrchestrationClient directly so the real service runs and the
        real WorkingPaper instance (serialisable) is returned — avoiding the
        risk of passing a MagicMock to WorkingPaperSerializer.
        """
        fake_plan_id = str(uuid.uuid4())
        fake_result = make_fake_plan_result(plan_id=fake_plan_id)

        with patch(f"{WP_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(f"{WP_VIEW_MODULE}.messaging_service"):
            MockClient.return_value.start_workflow.return_value = fake_result
            response = preparer_client.post(url_review(working_paper.id))

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        # workflow_plan_id must be at top level per guide
        assert "workflow_plan_id" in body
        assert body["workflow_plan_id"] == fake_plan_id
        # data is the serialized working paper
        assert body["data"] is not None

    @pytest.mark.django_db
    def test_success_publishes_event_with_workflow_plan_id(self, preparer_client, working_paper):
        """
        guide §7 + FIMS event contract: after successful submission the service
        must publish a working_paper.submitted event whose additional_data
        includes workflow_plan_id so downstream consumers can correlate events.
        """
        fake_plan_id = str(uuid.uuid4())
        fake_result = make_fake_plan_result(plan_id=fake_plan_id)

        with patch(f"{WP_SERVICE_MODULE}.OrchestrationClient") as MockClient, \
             patch(f"{WP_VIEW_MODULE}.messaging_service") as mock_msg:
            MockClient.return_value.start_workflow.return_value = fake_result
            preparer_client.post(url_review(working_paper.id))

        mock_msg.publish_working_paper_event.assert_called_once()
        call_kwargs = mock_msg.publish_working_paper_event.call_args.kwargs
        additional_data = call_kwargs.get("additional_data", {})
        assert "workflow_plan_id" in additional_data, (
            "workflow_plan_id missing from event additional_data"
        )
        assert additional_data["workflow_plan_id"] == fake_plan_id


# ===========================================================================
# § 4.4  WorkingPaperReviewView  PATCH — status update callback
# ===========================================================================

class TestReviewStatusUpdateView:
    """
    PATCH /working-papers/<id>/review/

    Internal endpoint called by a Kafka consumer (or directly from WO) when an
    action is taken on the workflow stage. Updates local review_status.
    """

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, working_paper_with_plan):
        """JWT authentication is required (enforced by middleware)."""
        response = anon_client.patch(
            url_review(working_paper_with_plan.id), {"action": "approved"}, format="json"
        )
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_approved_action_sets_review_status_and_reviewer(
        self, preparer_client, working_paper_with_plan
    ):
        """
        guide §7: 'approved' action must set review_status='approved' and
        record the acting user's UUID in reviewed_by.
        """
        response = preparer_client.patch(
            url_review(working_paper_with_plan.id), {"action": "approved"}, format="json"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["review_status"] == "approved"

        # Verify DB is updated — not just the response
        working_paper_with_plan.refresh_from_db()
        assert working_paper_with_plan.review_status == "approved"
        assert str(working_paper_with_plan.reviewed_by) == str(PREPARER_ID)

    @pytest.mark.django_db
    def test_rejected_action_sets_reviewed_status_and_saves_comments(
        self, preparer_client, working_paper_with_plan
    ):
        """
        guide §7: 'rejected' action maps to review_status='reviewed' (not 'rejected'
        — per FIMS model constraints) and must persist review_comments.
        """
        comment = "Evidence is insufficient — please attach bank reconciliation."
        response = preparer_client.patch(
            url_review(working_paper_with_plan.id),
            {"action": "rejected", "review_comments": comment},
            format="json",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        # FIMS model: 'rejected' WO action → review_status='reviewed'
        assert body["data"]["review_status"] == "reviewed"

        working_paper_with_plan.refresh_from_db()
        assert working_paper_with_plan.review_status == "reviewed"
        assert working_paper_with_plan.review_comments == comment

    @pytest.mark.django_db
    def test_invalid_action_returns_400_invalid_action_code(
        self, preparer_client, working_paper_with_plan
    ):
        """Only 'approved' and 'rejected' are valid actions. Others must return 400."""
        response = preparer_client.patch(
            url_review(working_paper_with_plan.id), {"action": "delete"}, format="json"
        )

        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_ACTION"
