"""
Service for Audit Engagement workflow integration (FIMS pattern).

Follows working_paper_service.py pattern exactly:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...)  → guide §4.3 signature

Template: grc.engagement_lifecycle (3-phase lifecycle:
          planning → fieldwork → reporting → completed)
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.core.models import AuditEngagement
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class AuditEngagementService:

    # Guide §4.2: WORKFLOW_TEMPLATE_CODE identifies the process
    WORKFLOW_TEMPLATE_CODE = "grc.engagement_lifecycle"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def start_workflow(
        self,
        engagement_id: str,
        initiator_id: str,
        auth_token: str | None = None,
    ):
        """
        Start the lifecycle workflow for an audit engagement in Work Orchestration Service.

        Follows guide §4.2 exactly:
          1. Build workflow context  (get_workflow_context → assignee resolution)
          2. Build metadata          (get_workflow_metadata → UI display)
          3. Start workflow          (guide §4.3 signature — context embedded in metadata)
          4. Save all 5 WorkflowMixin fields on the model

        The WO workflow manages the 3-phase lifecycle — GRC's engagement status
        is updated by the kafka_consumer when WO fires stage-completion events.
        """
        engagement = AuditEngagement.objects.select_for_update().get(id=engagement_id)

        if engagement.workflow_plan_id:
            logger.info(
                "AuditEngagement %s already has workflow plan %s — skipping",
                engagement.id,
                engagement.workflow_plan_id,
            )
            return engagement

        # Step 1 – context: variables used by WO to resolve stage assignees
        context = engagement.get_workflow_context()

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = engagement.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            initiator_id,
            subject_ref=str(engagement.id),
            metadata=metadata,
            stages=engagement.get_workflow_stages(),
            auth_token=auth_token,
        )

        if result and result.plan_id:
            engagement.workflow_plan_id = result.plan_id
            engagement.workflow_stage = result.current_stage_name or ""
            engagement.workflow_stage_id = result.current_stage_id or None
            engagement.workflow_started_at = timezone.now()
            engagement.status = "fieldwork"
            # Record actual start date when fieldwork begins
            if not engagement.actual_start_date:
                engagement.actual_start_date = timezone.now().date()
            engagement.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
                "actual_start_date",
            ])
            logger.info(
                "Started workflow plan %s for AuditEngagement %s (stage: %s)",
                result.plan_id,
                engagement.id,
                result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for AuditEngagement %s", engagement.id)

        return engagement
