"""
Service for Audit Universe workflow integration (FIMS pattern).

Follows working_paper_service.py pattern exactly:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata)  → guide §4.3 signature

Template: grc.audit_universe_approval (1-stage CIA review)
"""
import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from apps.core.models import AuditUniverse
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class AuditUniverseService:

    # Guide §4.2: WORKFLOW_TEMPLATE_CODE identifies the process
    WORKFLOW_TEMPLATE_CODE = "grc.audit_universe_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    # ── notification helpers ──────────────────────────────────────────

    @staticmethod
    def _build_review_url(universe_id: str) -> str:
        """Build the staff-portal URL for reviewing an audit universe."""
        domain = getattr(settings, 'EXTERNAL_DOMAIN', None) or getattr(
            settings, 'TUNNEL_DOMAIN', 'localhost:3001'
        )
        scheme = 'https' if 'localhost' not in domain else 'http'
        return f"{scheme}://{domain}/service/grc/audit-universe/{universe_id}"

    def _publish_submission_notification(
        self,
        universe: AuditUniverse,
        submitter_id: str,
    ) -> None:
        """
        Publish 'grc.audit_universe.submitted' notification to Kafka.
        Notifies the reviewed_by CIA user (if set) via email + in-app.
        Follows the document-records-service send_approval_notification pattern.
        """
        try:
            from apps.core.notifications.publisher import get_notification_publisher
            from apps.infrastructure.external.iam_client import IAMClient

            publisher = get_notification_publisher()
            iam = IAMClient()

            # Resolve submitter display info
            submitter_profile = iam.get_user_profile(submitter_id)
            submitter_name = 'Internal Auditor'
            submitter_email = ''
            if submitter_profile:
                first = submitter_profile.get('first_name', '')
                last = submitter_profile.get('last_name', '')
                submitter_name = f"{first} {last}".strip() or submitter_profile.get('username', submitter_name)
                submitter_email = submitter_profile.get('email', '')

            fiscal_year = getattr(universe.fiscal_year, 'year_code', 'N/A')
            review_url = self._build_review_url(str(universe.id))
            submitted_at = timezone.now().strftime('%Y-%m-%d %H:%M')

            # Build the shared context for the notification template
            context = {
                'audit_universe': {
                    'id': str(universe.id),
                    'fiscal_year': fiscal_year,
                    'description': (universe.description or '')[:200],
                },
                'submitter': {
                    'id': submitter_id,
                    'name': submitter_name,
                    'first_name': submitter_name.split()[0] if submitter_name else 'User',
                    'email': submitter_email,
                },
                'submitted_at': submitted_at,
                'review_url': review_url,
            }

            metadata = {
                'audit_universe_id': str(universe.id),
                'submitter_id': submitter_id,
                'workflow_plan_id': str(universe.workflow_plan_id) if universe.workflow_plan_id else None,
            }

            # If a specific CIA reviewer is set, notify them directly
            reviewer_id = str(universe.reviewed_by) if universe.reviewed_by else None
            if reviewer_id:
                reviewer_profile = iam.get_user_profile(reviewer_id)
                if reviewer_profile:
                    reviewer_email = reviewer_profile.get('email')
                    reviewer_first = reviewer_profile.get('first_name', 'Reviewer')
                    context['reviewer'] = {
                        'first_name': reviewer_first,
                        'email': reviewer_email or '',
                    }

                    recipients = {'user_ids': [reviewer_id]}
                    if reviewer_email:
                        recipients['email'] = [reviewer_email]

                    publisher.send_notification(
                        template_code='grc.audit_universe.submitted',
                        recipients=recipients,
                        context=context,
                        priority='high',
                        metadata={**metadata, 'user_ids': [reviewer_id]},
                    )
                    logger.info(
                        "Submission notification published for AuditUniverse %s → reviewer %s",
                        universe.id,
                        reviewer_id,
                    )
                    return
                else:
                    logger.warning(
                        "Could not fetch reviewer profile %s for AuditUniverse %s",
                        reviewer_id,
                        universe.id,
                    )

            # No specific reviewer — publish in-app only with submitter as fallback context
            # WO NotificationConsumer will create in-app records for user_ids in metadata
            context['reviewer'] = {
                'first_name': 'CIA Reviewer',
                'email': '',
            }
            publisher.send_notification(
                template_code='grc.audit_universe.submitted',
                recipients={'user_ids': [submitter_id]},
                context=context,
                priority='high',
                metadata={**metadata, 'user_ids': [submitter_id]},
            )
            logger.info(
                "Submission notification published for AuditUniverse %s (no specific reviewer)",
                universe.id,
            )

        except Exception as e:
            # Notification failure must not break the workflow submission
            logger.error(
                "Failed to publish submission notification for AuditUniverse %s: %s",
                universe.id,
                e,
                exc_info=True,
            )

    @transaction.atomic
    def submit_for_approval(
        self,
        universe_id: str,
        submitter_id: str,
    ):
        """
        Submit an audit universe to the Work Orchestration Service for CIA review.

        Follows guide §4.2 exactly:
          1. Build workflow context  (get_workflow_context → assignee resolution)
          2. Build metadata          (get_workflow_metadata → UI display)
          3. Start workflow          (guide §4.3 signature — context embedded in metadata)
          4. Save all 5 WorkflowMixin fields on the model
        """
        universe = AuditUniverse.objects.select_for_update().get(id=universe_id)

        if universe.workflow_plan_id:
            logger.info(
                "AuditUniverse %s already has workflow plan %s — skipping",
                universe.id,
                universe.workflow_plan_id,
            )
            return universe

        # Step 1 – context: variables used by WO to resolve stage assignees
        context = universe.get_workflow_context()
        context['applicant_id'] = submitter_id  # FIMS pattern: set at service layer

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = universe.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(universe.id),
            metadata=metadata,
        )

        if result and result.plan_id:
            universe.start_workflow(

                plan_id=result.plan_id,

                initial_stage=result.current_stage_name or '',

                stage_id=result.current_stage_id,

            )
            universe.status = "under_review"
            universe.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for AuditUniverse %s (stage: %s)",
                result.plan_id,
                universe.id,
                result.current_stage_name,
            )

            # Step 5 – Publish notification to CIA reviewer via Kafka
            # (runs outside the atomic block; failure does not rollback workflow)
            self._publish_submission_notification(universe, submitter_id)
        else:
            logger.error("Failed to start workflow for AuditUniverse %s", universe.id)

        return universe

    def get_workflow_status(self, universe_id: str):
        """Get current workflow status. Follows corporate FIMS pattern."""
        entity = AuditUniverse.objects.get(id=universe_id)
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

    def get_workflow_history(self, universe_id: str):
        """Get workflow activity history. Follows corporate FIMS pattern."""
        entity = AuditUniverse.objects.get(id=universe_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

    @transaction.atomic
    def advance_workflow_stage(self, universe_id: str, action: str, actor_id: str, comment: str = '') -> dict:
        """
        Execute a workflow action (approve, reject, return, etc.).
        Matches corporate-service _execute_workflow_action pattern.
        """
        entity = AuditUniverse.objects.select_for_update().get(id=universe_id)

        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this AuditUniverse")

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
    def cancel_workflow_plan(self, universe_id: str, actor_id: str, reason: str = '') -> AuditUniverse:
        """
        Cancel the active workflow for an audit universe.
        Matches corporate-service cancel_memo_workflow pattern.
        """
        entity = AuditUniverse.objects.select_for_update().get(id=universe_id)

        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this AuditUniverse")

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

