"""
Service for managing WorkingPaper with workflow integration (FIMS pattern).

Follows workflow-integration-guide.md §4.2 / §4.3 exactly:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...)  → guide §4.3 signature

OrchestrationClient._get_template_id_by_code() resolves the WO template UUID
automatically at runtime (guide §4.3 pattern). Inline stages are passed as
a fallback for when WO templates have not been seeded yet.
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.core.models import WorkingPaper
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class WorkingPaperService:

    # Guide §4.2: WORKFLOW_TEMPLATE_CODE identifies the process
    WORKFLOW_TEMPLATE_CODE = "grc.working_paper_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(
        self,
        working_paper_id: str,
        submitter_id: str,
        auth_token: str | None = None,
    ):
        """
        Submit a working paper to the Work Orchestration Service.

        Follows guide §4.2 exactly:
          1. Build workflow context  (get_workflow_context → assignee resolution)
          2. Build metadata          (get_workflow_metadata → UI display)
          3. Start workflow          (guide §4.3 signature — context embedded in metadata)
          4. Save all 5 WorkflowMixin fields on the model
        """
        wp = WorkingPaper.objects.select_for_update().get(id=working_paper_id)

        if wp.workflow_plan_id:
            logger.info(
                "WorkingPaper %s already has workflow plan %s — skipping",
                wp.id,
                wp.workflow_plan_id,
            )
            return wp

        # Step 1 – context: variables used by WO to resolve stage assignees
        context = wp.get_workflow_context()

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = wp.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(wp.id),
            metadata=metadata,
            stages=wp.get_workflow_stages(),
            auth_token=auth_token,
        )

        if result and result.plan_id:
            wp.workflow_plan_id = result.plan_id
            wp.workflow_stage = result.current_stage_name or ''
            wp.workflow_stage_id = result.current_stage_id or None
            wp.workflow_started_at = timezone.now()
            wp.review_status = "pending"
            wp.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "review_status",
            ])
            logger.info(
                "Started workflow plan %s for WorkingPaper %s (stage: %s)",
                result.plan_id,
                wp.id,
                result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for WorkingPaper %s", wp.id)

        return wp
