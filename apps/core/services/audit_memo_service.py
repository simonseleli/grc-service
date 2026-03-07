"""
Service for Audit Memo workflow integration (FIMS pattern).

Follows audit_universe_service.py pattern:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...)  → guide §4.3 signature

Template: grc.audit_memo_approval (2-stage: CIA memo review → DG memo approval)
SRS Requirements: 11, 12, 13, 14.
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.core.models import AuditMemo
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class AuditMemoService:

    # Guide §4.2: WORKFLOW_TEMPLATE_CODE identifies the process
    WORKFLOW_TEMPLATE_CODE = "grc.audit_memo_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(
        self,
        memo_id: str,
        submitter_id: str,
        auth_token: str | None = None,
    ):
        """
        Submit an audit memo to the Work Orchestration Service for CIA review
        and subsequent DG approval.

        Follows guide §4.2 exactly:
          1. Build workflow context  (get_workflow_context → assignee resolution)
          2. Build metadata          (get_workflow_metadata → UI display)
          3. Start workflow          (guide §4.3 signature — context embedded in metadata)
          4. Save all 5 WorkflowMixin fields on the model
        """
        memo = AuditMemo.objects.select_for_update().get(id=memo_id)

        if memo.workflow_plan_id:
            logger.info(
                "AuditMemo %s already has workflow plan %s — skipping",
                memo.id,
                memo.workflow_plan_id,
            )
            return memo

        # Step 1 – context: variables used by WO to resolve stage assignees
        context = memo.get_workflow_context()

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = memo.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(memo.id),
            metadata=metadata,
            stages=memo.get_workflow_stages(),
            auth_token=auth_token,
        )

        if result and result.plan_id:
            memo.workflow_plan_id = result.plan_id
            memo.workflow_stage = result.current_stage_name or ""
            memo.workflow_stage_id = result.current_stage_id or None
            memo.workflow_started_at = timezone.now()
            memo.status = "under_review"
            memo.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for AuditMemo %s (stage: %s)",
                result.plan_id,
                memo.id,
                result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for AuditMemo %s", memo.id)

        return memo
