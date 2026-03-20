"""
Service for Minutes workflow integration (FIMS pattern).
Template: grc.legal_minutes_approval
  Stages: minutes_draft_review → minutes_committee_approval
"""
import logging
from django.db import transaction
from apps.core.models import Minutes
from apps.infrastructure.external.orchestration_client import OrchestrationClient
from shared.constants.event_types import LEGAL_MINUTES_EVENTS

logger = logging.getLogger(__name__)


def _publish_minutes_event(event_type, minutes, actor_id):
    """Best-effort Kafka domain event for minutes lifecycle."""
    try:
        from apps.infrastructure.services.messaging_service import messaging_service
        messaging_service.publish_legal_minutes_event(
            event_type=event_type,
            minutes_id=minutes.id,
            additional_data={
                'meeting_id': str(minutes.meeting_id) if minutes.meeting_id else '',
                'reference_number': getattr(minutes, 'reference_number', ''),
                'approved_by': actor_id,
                'user_id': actor_id,
            },
        )
    except Exception as exc:
        logger.warning("Failed to publish %s event for minutes %s: %s", event_type, minutes.id, exc)


class LegalMinutesService:

    WORKFLOW_TEMPLATE_CODE = "grc.legal_minutes_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(self, minutes_id: str, submitter_id: str) -> Minutes:
        minutes = Minutes.objects.select_for_update().get(id=minutes_id)

        if minutes.workflow_plan_id:
            logger.info(
                "Minutes %s already has workflow plan %s — skipping",
                minutes.id, minutes.workflow_plan_id,
            )
            return minutes

        context = minutes.get_workflow_context()
        context['applicant_id'] = submitter_id

        metadata = minutes.get_workflow_metadata()

        result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(minutes.id),
            metadata=metadata,
        )

        if result and result.plan_id:
            minutes.start_workflow(
                plan_id=result.plan_id,
                initial_stage=result.current_stage_name or '',
                stage_id=result.current_stage_id,
            )
            minutes.status = "pending_approval"
            minutes.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for Minutes %s (stage: %s)",
                result.plan_id, minutes.id, result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for Minutes %s", minutes.id)

        return minutes

    def get_workflow_status(self, minutes_id: str) -> dict | None:
        entity = Minutes.objects.get(id=minutes_id)
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

    def get_workflow_history(self, minutes_id: str) -> list:
        entity = Minutes.objects.get(id=minutes_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

    @transaction.atomic
    def advance_workflow_stage(
        self, minutes_id: str, action: str, actor_id: str, comment: str = ''
    ) -> dict:
        entity = Minutes.objects.select_for_update().get(id=minutes_id)
        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this Minutes")

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

        if result.plan_status == 'completed':
            _publish_minutes_event(LEGAL_MINUTES_EVENTS['MINUTES_APPROVED'], entity, actor_id)

        return {
            'action': action,
            'new_stage_status': result.new_status,
            'plan_status': result.plan_status,
            'next_stage': result.next_stage_name,
            'next_stage_id': result.next_stage_id,
        }

    @transaction.atomic
    def cancel_workflow_plan(self, minutes_id: str, actor_id: str, reason: str = '') -> Minutes:
        entity = Minutes.objects.select_for_update().get(id=minutes_id)
        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this Minutes")

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
