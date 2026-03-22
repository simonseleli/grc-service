"""
Service for Institutional Risk Register workflow integration (FIMS pattern).

Template: grc.institutional_risk_register_approval
  (4-stage: rmqam_review → management_discussion → committee_review → commission_approval)
"""
import logging
from django.db import transaction
from apps.core.models import InstitutionalRiskRegister
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class InstitutionalRiskRegisterService:

    WORKFLOW_TEMPLATE_CODE = "grc.institutional_risk_register_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(self, register_id: str, submitter_id: str):
        """Submit an Institutional Risk Register to Work Orchestration Service."""
        entity = InstitutionalRiskRegister.objects.select_for_update().get(id=register_id)

        if entity.workflow_plan_id:
            logger.info(
                "InstitutionalRiskRegister %s already has workflow plan %s — skipping",
                entity.id, entity.workflow_plan_id,
            )
            return entity

        context = entity.get_workflow_context()
        context['applicant_id'] = submitter_id

        metadata = entity.get_workflow_metadata()

        result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(entity.id),
            metadata=metadata,
        )

        if result and result.plan_id:
            entity.start_workflow(
                plan_id=result.plan_id,
                initial_stage=result.current_stage_name or '',
                stage_id=result.current_stage_id,
            )
            entity.status = "rmqam_review"
            entity.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for InstitutionalRiskRegister %s (stage: %s)",
                result.plan_id, entity.id, result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for InstitutionalRiskRegister %s", entity.id)

        return entity

    def get_workflow_status(self, register_id: str):
        """Get current workflow status."""
        entity = InstitutionalRiskRegister.objects.get(id=register_id)
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

    def get_workflow_history(self, register_id: str):
        """Get workflow activity history."""
        entity = InstitutionalRiskRegister.objects.get(id=register_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

    @transaction.atomic
    def advance_workflow_stage(self, register_id: str, action: str, actor_id: str, comment: str = '') -> dict:
        """Execute a workflow action."""
        entity = InstitutionalRiskRegister.objects.select_for_update().get(id=register_id)

        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this InstitutionalRiskRegister")

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
    def cancel_workflow_plan(self, register_id: str, actor_id: str, reason: str = '') -> InstitutionalRiskRegister:
        """Cancel the active workflow."""
        entity = InstitutionalRiskRegister.objects.select_for_update().get(id=register_id)

        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this InstitutionalRiskRegister")

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
