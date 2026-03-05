"""
Service for Audit Plan (RBIAP) workflow integration (FIMS pattern).

Follows working_paper_service.py pattern exactly:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...)  → guide §4.3 signature

Template: grc.rbiap_approval (4-stage: cia_review → management_review →
          committee_review → commission_noting)
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.core.models import AuditPlan
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class AuditPlanService:

    # Guide §4.2: WORKFLOW_TEMPLATE_CODE identifies the process
    WORKFLOW_TEMPLATE_CODE = "grc.rbiap_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(
        self,
        plan_id: str,
        submitter_id: str,
        auth_token: str | None = None,
    ):
        """
        Submit an audit plan to the Work Orchestration Service for RBIAP approval.

        Follows guide §4.2 exactly:
          1. Build workflow context  (get_workflow_context → assignee resolution)
          2. Build metadata          (get_workflow_metadata → UI display)
          3. Start workflow          (guide §4.3 signature — context embedded in metadata)
          4. Save all 5 WorkflowMixin fields on the model
        """
        plan = AuditPlan.objects.select_for_update().get(id=plan_id)

        if plan.workflow_plan_id:
            logger.info(
                "AuditPlan %s already has workflow plan %s — skipping",
                plan.id,
                plan.workflow_plan_id,
            )
            return plan

        # Step 1 – context: variables used by WO to resolve stage assignees
        context = plan.get_workflow_context()

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = plan.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(plan.id),
            metadata=metadata,
            stages=plan.get_workflow_stages(),
            auth_token=auth_token,
        )

        if result and result.plan_id:
            plan.workflow_plan_id = result.plan_id
            plan.workflow_stage = result.current_stage_name or ""
            plan.workflow_stage_id = result.current_stage_id or None
            plan.workflow_started_at = timezone.now()
            plan.reviewed_by_cia = submitter_id
            plan.status = "management_review"
            plan.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "reviewed_by_cia",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for AuditPlan %s (stage: %s)",
                result.plan_id,
                plan.id,
                result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for AuditPlan %s", plan.id)

        return plan
