"""
Service for CaseDefendant / CasePlaintiff workflow integration (FIMS pattern).
Template: grc.legal_case_closure
  Stages: case_officer_review → legal_manager_approval → dg_closure_noting
Handles both defendant and plaintiff sides via `side` parameter.
"""
import logging
from django.db import transaction
from apps.core.models import CaseDefendant, CasePlaintiff
from apps.infrastructure.external.orchestration_client import OrchestrationClient
from shared.constants.event_types import LEGAL_CASE_EVENTS

logger = logging.getLogger(__name__)


def _publish_case_event(event_type, entity, side, actor_id):
    """Best-effort Kafka domain event for case lifecycle."""
    try:
        from apps.infrastructure.services.messaging_service import messaging_service
        messaging_service.publish_legal_case_event(
            event_type=event_type,
            case_id=entity.id,
            additional_data={
                'case_type': side,
                'reference_number': entity.reference_number,
                'case_title': getattr(entity, 'nature_of_claim', '') or getattr(entity, 'nature_of_breach', ''),
                'court_level': str(entity.court_level_id) if entity.court_level_id else '',
                'created_by': actor_id,
                'closed_by': actor_id,
                'closure_reason': '',
                'user_id': actor_id,
            },
        )
    except Exception as exc:
        logger.warning("Failed to publish %s event for case %s: %s", event_type, entity.id, exc)

MODEL_MAP = {
    'defendant': CaseDefendant,
    'plaintiff': CasePlaintiff,
}


class LegalCaseService:

    WORKFLOW_TEMPLATE_CODE = "grc.legal_case_closure"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    def _get_model(self, side: str):
        model = MODEL_MAP.get(side)
        if not model:
            raise ValueError(f"Invalid side '{side}' — must be 'defendant' or 'plaintiff'")
        return model

    @transaction.atomic
    def submit_for_approval(self, entity_id: str, submitter_id: str, side: str = 'defendant'):
        model = self._get_model(side)
        entity = model.objects.select_for_update().get(id=entity_id)

        if entity.workflow_plan_id:
            logger.info(
                "%s %s already has workflow plan %s — skipping",
                model.__name__, entity.id, entity.workflow_plan_id,
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
            entity.status = "under_dg_review"
            entity.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for %s %s (stage: %s)",
                result.plan_id, model.__name__, entity.id, result.current_stage_name,
            )
            _publish_case_event(LEGAL_CASE_EVENTS['CASE_CREATED'], entity, side, submitter_id)
        else:
            logger.error("Failed to start workflow for %s %s", model.__name__, entity.id)

        return entity

    def get_workflow_status(self, entity_id: str, side: str = 'defendant') -> dict | None:
        model = self._get_model(side)
        entity = model.objects.get(id=entity_id)
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

    def get_workflow_history(self, entity_id: str, side: str = 'defendant') -> list:
        model = self._get_model(side)
        entity = model.objects.get(id=entity_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

    @transaction.atomic
    def advance_workflow_stage(
        self, entity_id: str, action: str, actor_id: str, comment: str = '', side: str = 'defendant'
    ) -> dict:
        model = self._get_model(side)
        entity = model.objects.select_for_update().get(id=entity_id)
        if not entity.workflow_plan_id:
            raise ValueError(f"No active workflow for this {model.__name__}")

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
            _publish_case_event(LEGAL_CASE_EVENTS['CASE_CLOSED'], entity, side, actor_id)

        return {
            'action': action,
            'new_stage_status': result.new_status,
            'plan_status': result.plan_status,
            'next_stage': result.next_stage_name,
            'next_stage_id': result.next_stage_id,
        }

    @transaction.atomic
    def cancel_workflow_plan(self, entity_id: str, actor_id: str, reason: str = '', side: str = 'defendant'):
        model = self._get_model(side)
        entity = model.objects.select_for_update().get(id=entity_id)
        if not entity.workflow_plan_id:
            raise ValueError(f"No active workflow for this {model.__name__}")

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
