"""
Service for managing WorkingPaper with workflow integration (FIMS pattern).

Follows workflow-integration-guide.md §4.2 / §4.3 exactly:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata)  → guide §4.3 signature

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
        context['applicant_id'] = submitter_id  # FIMS pattern: set at service layer

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = wp.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(wp.id),
            metadata=metadata,
        )

        if result and result.plan_id:
            wp.start_workflow(

                plan_id=result.plan_id,

                initial_stage=result.current_stage_name or '',

                stage_id=result.current_stage_id,

            )
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

    def get_workflow_status(self, paper_id: str):
        """Get current workflow status. Follows corporate FIMS pattern."""
        entity = WorkingPaper.objects.get(id=paper_id)
        if not entity.workflow_plan_id:
            return None
        plan = self.workflow_client.get_plan(str(entity.workflow_plan_id))
        if not plan:
            return {
                'has_workflow': True,
                'workflow_plan_id': str(entity.workflow_plan_id),
                'status': 'unknown',
            }
        current_stage_data = next(
            (s for s in plan.stages if s.get('id') == plan.current_stage_id), None
        )
        return {
            'has_workflow': True,
            'plan_id': plan.plan_id,
            'workflow_plan_id': plan.plan_id,
            'status': plan.status,
            'current_stage': plan.current_stage_name,
            'current_stage_id': plan.current_stage_id,
            'current_stage_data': current_stage_data,
            'available_actions': current_stage_data.get('actions', []) if current_stage_data else [],
            'stages': plan.stages,
            'metadata': plan.metadata,
            'is_completed': plan.status in ('completed', 'cancelled'),
        }

    def get_workflow_history(self, paper_id: str):
        """Get workflow activity history. Follows corporate FIMS pattern."""
        entity = WorkingPaper.objects.get(id=paper_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

    @transaction.atomic
    def advance_workflow_stage(self, paper_id: str, action: str, actor_id: str, comment: str = '') -> dict:
        """
        Execute a workflow action (approve, reject, return, etc.).
        Matches corporate-service _execute_workflow_action pattern.
        """
        entity = WorkingPaper.objects.select_for_update().get(id=paper_id)

        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this WorkingPaper")

        plan = self.workflow_client.get_plan(str(entity.workflow_plan_id))
        if not plan:
            raise ValueError("Could not fetch workflow plan")

        stage_id = getattr(entity, 'workflow_stage_id', None) or plan.current_stage_id
        if not stage_id:
            raise ValueError("Could not determine current workflow stage")

        result = self.workflow_client.advance_stage(
            plan_id=str(entity.workflow_plan_id),
            stage_id=str(stage_id),
            action=action,
            actor_id=actor_id,
            comment=comment,
        )

        if not result:
            raise ValueError("Failed to execute workflow action")

        if result.next_stage_id:
            entity.update_workflow_stage(
                stage_name=result.next_stage_name or '',
                stage_id=result.next_stage_id,
            )

        if result.plan_status in ('completed', 'cancelled'):
            entity.complete_workflow()

        entity.save()

        return {
            'action': action,
            'new_stage_status': result.new_status,
            'plan_status': result.plan_status,
            'next_stage': result.next_stage_name,
            'next_stage_id': result.next_stage_id,
        }

    @transaction.atomic
    def cancel_workflow_plan(self, paper_id: str, actor_id: str, reason: str = '') -> WorkingPaper:
        """
        Cancel the active workflow for a working paper.
        Matches corporate-service cancel_memo_workflow pattern.
        """
        entity = WorkingPaper.objects.select_for_update().get(id=paper_id)

        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this WorkingPaper")

        success = self.workflow_client.cancel_plan(
            plan_id=str(entity.workflow_plan_id),
            actor_id=actor_id,
            reason=reason,
        )

        if not success:
            raise ValueError("Failed to cancel workflow")

        entity.cancel_workflow()
        entity.save()

        return entity

