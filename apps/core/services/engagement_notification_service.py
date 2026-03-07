"""
Service for Engagement Notification workflow integration (FIMS pattern).

Follows audit_universe_service.py pattern exactly:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...)  → guide §4.3 signature

Template : grc.engagement_notification_approval (1-stage CIA approval)
SRS Req  : 24 (provision), 25 (CIA approval + signature), 26 (transmission)
"""
import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from apps.core.models import EngagementNotification
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class EngagementNotificationService:

    WORKFLOW_TEMPLATE_CODE = "grc.engagement_notification_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    # ── URL helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _build_detail_url(en_id: str) -> str:
        """Resolve the staff-portal URL for an Engagement Notification."""
        domain = getattr(settings, 'EXTERNAL_DOMAIN', None) or getattr(
            settings, 'TUNNEL_DOMAIN', 'localhost:3001'
        )
        scheme = 'https' if 'localhost' not in domain else 'http'
        return f"{scheme}://{domain}/service/grc/engagement-notifications/{en_id}"

    # ── notification helpers ──────────────────────────────────────────────────

    def _publish_submitted_notification(
        self,
        en: EngagementNotification,
        submitter_id: str,
    ) -> None:
        """
        Publish 'grc.engagement_notification.submitted' to Kafka.

        Notifies the CIA (approved_by_cia, if pre-set) via email + in-app.
        Notification failure must not block business logic.
        """
        try:
            from apps.core.notifications.publisher import get_notification_publisher
            from apps.infrastructure.external.iam_client import IAMClient

            publisher = get_notification_publisher()
            iam = IAMClient()

            # Resolve submitter display info
            submitter_profile = iam.get_user_profile(submitter_id)
            submitter_name = 'Lead Auditor'
            submitter_email = ''
            if submitter_profile:
                first = submitter_profile.get('first_name', '')
                last = submitter_profile.get('last_name', '')
                submitter_name = f"{first} {last}".strip() or submitter_profile.get('username', submitter_name)
                submitter_email = submitter_profile.get('email', '')

            engagement_reference = getattr(en.audit_engagement, 'reference_number', 'N/A')
            detail_url = self._build_detail_url(str(en.id))
            submitted_at = timezone.now().strftime('%Y-%m-%d %H:%M')

            context = {
                'engagement_notification': {
                    'id': str(en.id),
                    'reference_number': en.reference_number,
                    'engagement_reference': engagement_reference,
                    'audit_period_start': str(en.audit_period_start),
                    'audit_period_end': str(en.audit_period_end),
                },
                'submitter': {
                    'id': submitter_id,
                    'name': submitter_name,
                    'first_name': submitter_name.split()[0] if submitter_name else 'User',
                    'email': submitter_email,
                },
                'submitted_at': submitted_at,
                'review_url': detail_url,
            }

            notification_metadata = {
                'engagement_notification_id': str(en.id),
                'submitter_id': submitter_id,
                'workflow_plan_id': str(en.workflow_plan_id) if en.workflow_plan_id else None,
            }

            # If a CIA approver is already designated, notify them directly
            cia_id = str(en.approved_by_cia) if en.approved_by_cia else None
            if cia_id:
                cia_profile = iam.get_user_profile(cia_id)
                if cia_profile:
                    cia_email = cia_profile.get('email')
                    cia_first = cia_profile.get('first_name', 'CIA')
                    context['reviewer'] = {
                        'first_name': cia_first,
                        'email': cia_email or '',
                    }
                    recipients = {'user_ids': [cia_id]}
                    if cia_email:
                        recipients['email'] = [cia_email]

                    publisher.send_notification(
                        template_code='grc.engagement_notification.submitted',
                        recipients=recipients,
                        context=context,
                        priority='high',
                        metadata={**notification_metadata, 'user_ids': [cia_id]},
                    )
                    logger.info(
                        "Submitted notification published for EngagementNotification %s → CIA %s",
                        en.id, cia_id,
                    )
                    return
                else:
                    logger.warning(
                        "Could not fetch CIA profile %s for EngagementNotification %s",
                        cia_id, en.id,
                    )

            # No designated CIA — publish in-app fallback to submitter
            context['reviewer'] = {'first_name': 'CIA', 'email': ''}
            publisher.send_notification(
                template_code='grc.engagement_notification.submitted',
                recipients={'user_ids': [submitter_id]},
                context=context,
                priority='high',
                metadata={**notification_metadata, 'user_ids': [submitter_id]},
            )
            logger.info(
                "Submitted notification published for EngagementNotification %s (no CIA pre-set)",
                en.id,
            )

        except Exception as exc:
            logger.error(
                "Failed to publish submitted notification for EngagementNotification %s: %s",
                en.id, exc, exc_info=True,
            )

    def _publish_approval_notification(
        self,
        en: EngagementNotification,
        approver_id: str,
        approved: bool,
        comments: str = '',
    ) -> None:
        """
        Publish approved / returned notification to the Lead Auditor.
        Called by the Kafka consumer handler after persisting the decision.
        """
        try:
            from apps.core.notifications.publisher import get_notification_publisher
            from apps.infrastructure.external.iam_client import IAMClient

            publisher = get_notification_publisher()
            iam = IAMClient()

            # Resolve approver display info
            approver_profile = iam.get_user_profile(approver_id)
            approver_name = 'Chief Internal Auditor'
            if approver_profile:
                first = approver_profile.get('first_name', '')
                last = approver_profile.get('last_name', '')
                approver_name = f"{first} {last}".strip() or approver_name

            # Resolve Lead Auditor (prepared_by)
            la_id = str(en.prepared_by)
            la_profile = iam.get_user_profile(la_id)
            la_first = 'Lead Auditor'
            la_email = ''
            if la_profile:
                la_first = la_profile.get('first_name', la_first)
                la_email = la_profile.get('email', '')

            engagement_reference = getattr(en.audit_engagement, 'reference_number', 'N/A')
            detail_url = self._build_detail_url(str(en.id))
            now_str = timezone.now().strftime('%Y-%m-%d %H:%M')

            base_context = {
                'engagement_notification': {
                    'id': str(en.id),
                    'reference_number': en.reference_number,
                    'engagement_reference': engagement_reference,
                },
                'lead_auditor': {'first_name': la_first, 'email': la_email},
                'detail_url': detail_url,
            }

            if approved:
                template_code = 'grc.engagement_notification.approved'
                context = {
                    **base_context,
                    'approver': {'name': approver_name},
                    'approved_at': now_str,
                }
            else:
                template_code = 'grc.engagement_notification.returned'
                context = {
                    **base_context,
                    'reviewer': {'name': approver_name},
                    'returned_at': now_str,
                    'comments': comments,
                }

            notification_metadata = {
                'engagement_notification_id': str(en.id),
                'approver_id': approver_id,
            }

            recipients = {'user_ids': [la_id]}
            if la_email:
                recipients['email'] = [la_email]

            publisher.send_notification(
                template_code=template_code,
                recipients=recipients,
                context=context,
                priority='high' if not approved else 'normal',
                metadata={**notification_metadata, 'user_ids': [la_id]},
            )
            logger.info(
                "Approval notification (%s) published for EngagementNotification %s → LA %s",
                template_code, en.id, la_id,
            )

        except Exception as exc:
            logger.error(
                "Failed to publish approval notification for EngagementNotification %s: %s",
                en.id, exc, exc_info=True,
            )

    # ── business actions ──────────────────────────────────────────────────────

    @transaction.atomic
    def submit_for_approval(
        self,
        en_id: str,
        submitter_id: str,
        auth_token: str | None = None,
    ) -> EngagementNotification:
        """
        Submit an Engagement Notification to the Work Orchestration Service for CIA approval.

        Follows guide §4.2 exactly:
          1. Build workflow context  (entity.get_workflow_context())
          2. Build metadata          (entity.get_workflow_metadata())
          3. Start workflow          (guide §4.3 signature)
          4. Save all 5 WorkflowMixin fields + status → under_review
          5. Publish submission notification (outside atomic; failure does not rollback)
        """
        en = EngagementNotification.objects.select_for_update().get(id=en_id)

        if en.workflow_plan_id:
            logger.info(
                "EngagementNotification %s already has workflow plan %s — skipping",
                en.id, en.workflow_plan_id,
            )
            return en

        # Step 1 — context for WO assignee resolution
        context = en.get_workflow_context()

        # Step 2 — metadata stored with the WO plan
        metadata = en.get_workflow_metadata()

        # Step 3 — start workflow
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(en.id),
            metadata=metadata,
            stages=en.get_workflow_stages(),
            auth_token=auth_token,
        )

        if result and result.plan_id:
            en.workflow_plan_id = result.plan_id
            en.workflow_stage = result.current_stage_name or ""
            en.workflow_stage_id = result.current_stage_id or None
            en.workflow_started_at = timezone.now()
            en.status = "under_review"
            en.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for EngagementNotification %s (stage: %s)",
                result.plan_id, en.id, result.current_stage_name,
            )

            # Step 5 — publish notification outside the atomic block
            self._publish_submitted_notification(en, submitter_id)
        else:
            logger.error(
                "Failed to start workflow for EngagementNotification %s", en.id
            )

        return en

    @transaction.atomic
    def transmit(
        self,
        en_id: str,
        transmitter_id: str,
    ) -> EngagementNotification:
        """
        Mark the approved Engagement Notification as transmitted.

        - EN status → 'transmitted', transmitted_at = now()
        - linked AuditEngagement status → 'fieldwork'
        SRS Req 26.
        """
        en = EngagementNotification.objects.select_for_update().select_related(
            'audit_engagement'
        ).get(id=en_id)

        if en.status != 'approved':
            raise ValueError(
                f"EngagementNotification {en_id} must be 'approved' before transmission "
                f"(current status: {en.status})"
            )

        now = timezone.now()
        en.status = 'transmitted'
        en.transmitted_at = now
        en.save(update_fields=['status', 'transmitted_at'])

        # Advance the parent engagement to fieldwork phase
        engagement = en.audit_engagement
        if engagement.status not in ('fieldwork', 'completed', 'report'):
            engagement.status = 'fieldwork'
            engagement.save(update_fields=['status'])
            logger.info(
                "AuditEngagement %s advanced to 'fieldwork' after EN %s transmission",
                engagement.id, en.id,
            )

        logger.info(
            "EngagementNotification %s transmitted by user %s at %s",
            en.id, transmitter_id, now,
        )
        return en
