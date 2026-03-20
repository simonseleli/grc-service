"""
Service for JudgmentDefendant / JudgmentPlaintiff workflow integration (FIMS pattern).
Template: grc.legal_judgment_decision
  Stages: judgment_officer_review → legal_manager_judgment_approval → dg_judgment_noting
Handles both defendant and plaintiff sides via `side` parameter.
Also provides DG appeal-decision processing.
"""
import logging
import uuid
from datetime import date, timedelta

from django.db import transaction
from apps.core.models import (
    JudgmentDefendant, JudgmentPlaintiff,
    FilingDefendant, FilingPlaintiff,
    AppealDefendant, AppealPlaintiff,
    TaskLitigation,
)
from apps.infrastructure.external.orchestration_client import OrchestrationClient
from shared.constants.event_types import LEGAL_JUDGMENT_EVENTS

logger = logging.getLogger(__name__)


def _publish_judgment_event(event_type, entity, side, actor_id):
    """Best-effort Kafka domain event for judgment lifecycle."""
    try:
        from apps.infrastructure.services.messaging_service import messaging_service
        case_field = 'case_defendant_id' if side == 'defendant' else 'case_plaintiff_id'
        messaging_service.publish_legal_judgment_event(
            event_type=event_type,
            judgment_id=entity.id,
            additional_data={
                'case_id': str(getattr(entity, case_field, '') or ''),
                'case_type': side,
                'judgment_date': str(getattr(entity, 'judgment_date', '') or ''),
                'outcome': getattr(entity, 'outcome', '') or getattr(entity, 'judgment_summary', ''),
                'recorded_by': actor_id,
                'user_id': actor_id,
            },
        )
    except Exception as exc:
        logger.warning("Failed to publish %s event for judgment %s: %s", event_type, entity.id, exc)

MODEL_MAP = {
    'defendant': JudgmentDefendant,
    'plaintiff': JudgmentPlaintiff,
}


class LegalJudgmentService:

    WORKFLOW_TEMPLATE_CODE = "grc.legal_judgment_decision"

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
            entity.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
            ])
            logger.info(
                "Started workflow plan %s for %s %s (stage: %s)",
                result.plan_id, model.__name__, entity.id, result.current_stage_name,
            )
            _publish_judgment_event(LEGAL_JUDGMENT_EVENTS['JUDGMENT_RECORDED'], entity, side, submitter_id)
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

        return {
            'action': action,
            'new_stage_status': result.new_status,
            'plan_status': result.plan_status,
            'next_stage': result.next_stage_name,
            'next_stage_id': result.next_stage_id,
        }

    @transaction.atomic
    def process_appeal_decision(
        self, entity_id: str, decision: str, actor_id: str, side: str = 'defendant'
    ):
        """Record DG appeal decision on a judgment (accept / appeal).
        On 'appeal': auto-creates Filing, TaskLitigation, Appeal, updates case status.
        """
        model = self._get_model(side)
        entity = model.objects.select_for_update().get(id=entity_id)
        entity.dg_decision = decision
        entity.save(update_fields=['dg_decision'])
        logger.info(
            "DG appeal decision '%s' recorded for %s %s by %s",
            decision, model.__name__, entity.id, actor_id,
        )

        if decision == 'appeal':
            FilingModel = FilingDefendant if side == 'defendant' else FilingPlaintiff
            AppealModel = AppealDefendant if side == 'defendant' else AppealPlaintiff
            case_fk = 'case_defendant' if side == 'defendant' else 'case_plaintiff'
            case = getattr(entity, case_fk)

            # 1. Create Notice of Appeal filing
            filing = FilingModel.objects.create(
                **{case_fk: case},
                filing_type='notice_of_appeal',
                title=f'Notice of Appeal - {entity}',
                document_id=uuid.uuid4(),
                status='draft',
                submitted_by_user_id=actor_id,
                created_by=actor_id,
            )
            entity.appeal_filing = filing

            # 2. Create appeal deadline task
            appeal_due = entity.appeal_due_date or (date.today() + timedelta(days=30))
            task = TaskLitigation.objects.create(
                **{case_fk: case},
                title=f'File Notice of Appeal by {appeal_due}',
                assigned_to_user_id=actor_id,
                due_date=appeal_due,
                status='open',
                priority='high',
                related_entity_type='judgment',
                related_entity_id=entity.id,
                created_by=actor_id,
            )
            entity.appeal_task = task

            # 3. Create Appeal record
            appeal = AppealModel.objects.create(
                judgment=entity,
                appeal_date=date.today(),
                grounds=f'Appeal of judgment dated {entity.judgment_date}',
                status='pending',
                created_by=actor_id,
            )

            # 4. Update parent case status
            case.status = 'appeal_filed'
            case.save(update_fields=['status', 'updated_at'])

            # 5. Save judgment FK links
            entity.save(update_fields=['appeal_filing', 'appeal_task', 'updated_at'])

            # 6. Publish event
            _publish_judgment_event(
                LEGAL_JUDGMENT_EVENTS['APPEAL_DECISION_RECORDED'],
                entity, side, actor_id,
            )
            logger.info(
                "Appeal auto-created for %s %s: filing=%s, task=%s, appeal=%s",
                model.__name__, entity.id, filing.id, task.id, appeal.id,
            )

        return entity

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
