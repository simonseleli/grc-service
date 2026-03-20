"""
Service for Meeting workflow integration (FIMS pattern).
Template: grc.legal_meeting_lifecycle
  Stages: meeting_preparation → meeting_execution → meeting_closure
"""
import logging
from django.db import transaction
from apps.core.models import Meeting
from apps.infrastructure.external.orchestration_client import OrchestrationClient
from shared.constants.event_types import LEGAL_MEETING_EVENTS

logger = logging.getLogger(__name__)


def _publish_meeting_event(event_type, meeting, actor_id):
    """Best-effort Kafka domain event for meeting lifecycle."""
    try:
        from apps.infrastructure.services.messaging_service import messaging_service
        messaging_service.publish_legal_meeting_event(
            event_type=event_type,
            meeting_id=meeting.id,
            additional_data={
                'meeting_type': str(meeting.meeting_type_id) if meeting.meeting_type_id else '',
                'governing_body_id': str(meeting.governing_body_id) if meeting.governing_body_id else '',
                'reference_number': getattr(meeting, 'reference_number', ''),
                'completed_by': actor_id,
                'user_id': actor_id,
            },
        )
    except Exception as exc:
        logger.warning("Failed to publish %s event for meeting %s: %s", event_type, meeting.id, exc)


class LegalMeetingService:

    WORKFLOW_TEMPLATE_CODE = "grc.legal_meeting_lifecycle"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(self, meeting_id: str, submitter_id: str) -> Meeting:
        meeting = Meeting.objects.select_for_update().get(id=meeting_id)

        if meeting.workflow_plan_id:
            logger.info(
                "Meeting %s already has workflow plan %s — skipping",
                meeting.id, meeting.workflow_plan_id,
            )
            return meeting

        context = meeting.get_workflow_context()
        context['applicant_id'] = submitter_id

        metadata = meeting.get_workflow_metadata()

        result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(meeting.id),
            metadata=metadata,
        )

        if result and result.plan_id:
            meeting.start_workflow(
                plan_id=result.plan_id,
                initial_stage=result.current_stage_name or '',
                stage_id=result.current_stage_id,
            )
            meeting.status = "registered"
            meeting.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for Meeting %s (stage: %s)",
                result.plan_id, meeting.id, result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for Meeting %s", meeting.id)

        return meeting

    def get_workflow_status(self, meeting_id: str) -> dict | None:
        entity = Meeting.objects.get(id=meeting_id)
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

    def get_workflow_history(self, meeting_id: str) -> list:
        entity = Meeting.objects.get(id=meeting_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

    @transaction.atomic
    def advance_workflow_stage(
        self, meeting_id: str, action: str, actor_id: str, comment: str = ''
    ) -> dict:
        entity = Meeting.objects.select_for_update().get(id=meeting_id)
        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this Meeting")

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
            _publish_meeting_event(LEGAL_MEETING_EVENTS['MEETING_COMPLETED'], entity, actor_id)

        return {
            'action': action,
            'new_stage_status': result.new_status,
            'plan_status': result.plan_status,
            'next_stage': result.next_stage_name,
            'next_stage_id': result.next_stage_id,
        }

    @transaction.atomic
    def cancel_workflow_plan(self, meeting_id: str, actor_id: str, reason: str = '') -> Meeting:
        entity = Meeting.objects.select_for_update().get(id=meeting_id)
        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this Meeting")

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
