"""
Service for Audit Program workflow integration (FIMS pattern).

Follows audit_universe_service.py pattern:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...)  → guide §4.3 signature

Template: grc.audit_program_approval (2-stage: IA program review → CIA program approval)
SRS Requirements: 22, 23.
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.core.models import AuditProgram
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class AuditProgramService:

    # Guide §4.2: WORKFLOW_TEMPLATE_CODE identifies the process
    WORKFLOW_TEMPLATE_CODE = "grc.audit_program_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(
        self,
        program_id: str,
        submitter_id: str,
        auth_token: str | None = None,
    ):
        """
        Submit an audit program to the Work Orchestration Service for IA/CIA approval.

        Follows guide §4.2 exactly:
          1. Build workflow context  (get_workflow_context → assignee resolution)
          2. Build metadata          (get_workflow_metadata → UI display)
          3. Start workflow          (guide §4.3 signature — context embedded in metadata)
          4. Save all 5 WorkflowMixin fields on the model
        """
        program = AuditProgram.objects.select_for_update().get(id=program_id)

        if program.workflow_plan_id:
            logger.info(
                "AuditProgram %s already has workflow plan %s — skipping",
                program.id,
                program.workflow_plan_id,
            )
            return program

        # Step 1 – context: variables used by WO to resolve stage assignees
        context = program.get_workflow_context()

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = program.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(program.id),
            metadata=metadata,
            stages=program.get_workflow_stages(),
            auth_token=auth_token,
        )

        if result and result.plan_id:
            program.workflow_plan_id = result.plan_id
            program.workflow_stage = result.current_stage_name or ""
            program.workflow_stage_id = result.current_stage_id or None
            program.workflow_started_at = timezone.now()
            program.status = "under_review"
            program.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for AuditProgram %s (stage: %s)",
                result.plan_id,
                program.id,
                result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for AuditProgram %s", program.id)

        return program
