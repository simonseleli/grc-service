"""
Service for Audit Universe workflow integration (FIMS pattern).

Follows working_paper_service.py pattern exactly:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...)  → guide §4.3 signature

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
        auth_token: str | None = None,
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

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = universe.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(universe.id),
            metadata=metadata,
            stages=universe.get_workflow_stages(),
            auth_token=auth_token,
        )

        if result and result.plan_id:
            universe.workflow_plan_id = result.plan_id
            universe.workflow_stage = result.current_stage_name or ""
            universe.workflow_stage_id = result.current_stage_id or None
            universe.workflow_started_at = timezone.now()
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
