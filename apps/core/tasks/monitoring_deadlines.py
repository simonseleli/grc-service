"""
Celery tasks for 5-day response deadline enforcement (P2-GAP 5 fix).

Runs daily at 07:00 to enforce the SRS-mandated 5-day response window:
  - Day 3 after notification  -> reminder to auditee via WO notification pipeline
  - Day 5+ (past deadline)    -> mark cycle is_overdue, send overdue alert to auditee
  - Day 7+                    -> escalate to CIA (send via WO notification pipeline)

P2-GAP 5 correction:
  BEFORE: called messaging_service.publish_audit_plan_event() -- raw Kafka WO event bus
          (not read by WO notification consumer, so email/in-app never fired)
  AFTER:  calls publisher.send_notification() -- publishes to notifications-high/normal
          topics that WO notification consumer reads; resolves user profiles via IAM.

Queries AuditeeFollowUpResponse (not ImplementationMonitoring) so each follow-up cycle
is tracked independently (P2-GAP 4 model change).
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Main task
# -------------------------------------------------------------------

@shared_task(name="grc.check_monitoring_deadlines")
def check_monitoring_deadlines():
    """Daily task: enforce 5-day response window on implementation follow-up cycles.

    - Day 3 after notification -> reminder event via WO notification pipeline
    - Day 5+ (past deadline)  -> mark is_overdue, send auditee alert
    - Day 7+                  -> escalate to CIA
    """
    from apps.core.models import AuditeeFollowUpResponse

    now = timezone.now()
    updated_overdue = 0
    reminders_sent = 0
    escalations_sent = 0

    # -- 1. Mark overdue + notify auditee --------------------------------
    # Cycles that are past deadline but not yet flagged overdue
    newly_overdue = AuditeeFollowUpResponse.objects.filter(
        status='pending',
        response_deadline__isnull=False,
        response_deadline__lt=now,
        is_overdue=False,
        is_active=True,
    ).select_related(
        'monitoring',
        'monitoring__recommendation',
        'monitoring__recommendation__finding',
        'monitoring__recommendation__finding__engagement',
    )

    for cycle in newly_overdue:
        cycle.is_overdue = True
        cycle.save(update_fields=['is_overdue'])
        _send_overdue_notification(cycle, now)
        updated_overdue += 1

    # -- 2. Day-3 reminders ----------------------------------------------
    # Cycles notified ~3 days ago that have not yet submitted
    day3_window_start = now - timedelta(days=3, hours=12)
    day3_window_end = now - timedelta(days=2, hours=12)
    day3_cycles = AuditeeFollowUpResponse.objects.filter(
        status='pending',
        notified_at__gte=day3_window_start,
        notified_at__lt=day3_window_end,
        is_active=True,
    ).select_related(
        'monitoring',
        'monitoring__recommendation',
        'monitoring__recommendation__finding',
        'monitoring__recommendation__finding__engagement',
    )

    for cycle in day3_cycles:
        _send_reminder_notification(cycle, now)
        reminders_sent += 1

    # -- 3. Day 7+ escalation (to CIA reviewer) --------------------------
    day7_threshold = now - timedelta(days=7)
    escalation_cycles = AuditeeFollowUpResponse.objects.filter(
        status='pending',
        notified_at__isnull=False,
        notified_at__lt=day7_threshold,
        is_overdue=True,
        monitoring__escalated=False,
        is_active=True,
    ).select_related(
        'monitoring',
        'monitoring__recommendation',
        'monitoring__recommendation__finding',
        'monitoring__recommendation__finding__engagement',
    )

    for cycle in escalation_cycles:
        _send_escalation_notification(cycle, now)
        # Mark header escalated so we do not repeat
        monitoring = cycle.monitoring
        monitoring.escalated = True
        monitoring.save(update_fields=['escalated'])
        escalations_sent += 1

    logger.info(
        "Monitoring deadline check complete: %d marked overdue, %d reminders, %d escalations",
        updated_overdue, reminders_sent, escalations_sent,
    )
    return {
        'overdue_marked': updated_overdue,
        'reminders_sent': reminders_sent,
        'escalations_sent': escalations_sent,
    }


# -------------------------------------------------------------------
# Private helpers -- WO notification pipeline
# -------------------------------------------------------------------

def _resolve_user(iam, user_id, fallback_name='User'):
    """
    Resolve a user UUID to a name/email dict via IAMClient.
    Returns safe fallback values if resolution fails.
    """
    if not user_id:
        return {'first_name': fallback_name, 'name': fallback_name, 'email': None}
    try:
        profile = iam.get_user_profile(str(user_id))
        if profile:
            first = profile.get('first_name', '')
            last = profile.get('last_name', '')
            full = '{} {}'.format(first, last).strip() or fallback_name
            email = profile.get('email', None)
            return {'first_name': first or fallback_name, 'name': full, 'email': email}
    except Exception as e:
        logger.warning("IAM resolution failed for user %s: %s", user_id, e)
    return {'first_name': fallback_name, 'name': fallback_name, 'email': None}


def _build_detail_url(cycle):
    """Build staff portal URL for the follow-up response submission page."""
    try:
        from django.conf import settings
        base = getattr(settings, 'STAFF_PORTAL_BASE_URL', 'https://portal.fcc.go.tz')
        monitoring_id = str(cycle.monitoring_id)
        return '{}/audit/implementation-monitoring/{}/responses/{}/'.format(
            base, monitoring_id, cycle.id
        )
    except Exception:
        return ''


def _send_overdue_notification(cycle, now):
    """
    Notify the auditee that their response window has lapsed.
    Publishes to WO notifications-high topic via publisher.send_notification().
    """
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        rec = cycle.monitoring.recommendation
        auditee_id = str(rec.responsible_party) if rec.responsible_party else None
        auditee = _resolve_user(iam, auditee_id, 'Responsible Party')

        if not auditee.get('email'):
            logger.warning(
                "Cannot send overdue notification for cycle %s: auditee email missing",
                cycle.id,
            )
            return

        days_overdue = (
            (now - cycle.response_deadline).days if cycle.response_deadline else 0
        )
        deadline_str = (
            cycle.response_deadline.strftime('%Y-%m-%d %H:%M')
            if cycle.response_deadline else 'N/A'
        )

        context = {
            'auditee': {
                'first_name': auditee['first_name'],
                'email': auditee['email'],
            },
            'recommendation': {
                'reference_number': rec.reference_number,
                'title': rec.title,
            },
            'response_deadline': deadline_str,
            'days_overdue': days_overdue,
            'cycle_number': cycle.cycle_number,
            'detail_url': _build_detail_url(cycle),
        }

        publisher.send_notification(
            template_code='grc.monitoring.overdue',
            recipients={
                'email': [auditee['email']],
                'user_ids': [auditee_id] if auditee_id else [],
            },
            context=context,
            priority='high',
            metadata={
                'monitoring_id': str(cycle.monitoring_id),
                'cycle_id': str(cycle.id),
                'cycle_number': cycle.cycle_number,
                'recommendation_id': str(rec.id),
            },
        )
        logger.info(
            "Overdue notification sent for cycle %s (monitoring %s, rec %s)",
            cycle.id, cycle.monitoring_id, rec.reference_number,
        )
    except Exception as e:
        logger.error(
            "Failed to send overdue notification for cycle %s: %s", cycle.id, e
        )


def _send_reminder_notification(cycle, now):
    """
    Day-3 reminder to auditee: 2 days remaining to submit.
    Publishes to notifications-normal topic.
    """
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        rec = cycle.monitoring.recommendation
        auditee_id = str(rec.responsible_party) if rec.responsible_party else None
        auditee = _resolve_user(iam, auditee_id, 'Responsible Party')

        if not auditee.get('email'):
            logger.warning(
                "Cannot send day-3 reminder for cycle %s: auditee email missing",
                cycle.id,
            )
            return

        deadline_str = (
            cycle.response_deadline.strftime('%Y-%m-%d %H:%M')
            if cycle.response_deadline else 'N/A'
        )

        context = {
            'auditee': {
                'first_name': auditee['first_name'],
                'email': auditee['email'],
            },
            'recommendation': {
                'reference_number': rec.reference_number,
                'title': rec.title,
            },
            'response_deadline': deadline_str,
            'days_remaining': 2,
            'cycle_number': cycle.cycle_number,
            'detail_url': _build_detail_url(cycle),
        }

        publisher.send_notification(
            template_code='grc.monitoring.deadline_reminder',
            recipients={
                'email': [auditee['email']],
                'user_ids': [auditee_id] if auditee_id else [],
            },
            context=context,
            priority='normal',
            metadata={
                'monitoring_id': str(cycle.monitoring_id),
                'cycle_id': str(cycle.id),
                'cycle_number': cycle.cycle_number,
                'recommendation_id': str(rec.id),
            },
        )
        logger.info(
            "Day-3 reminder sent for cycle %s (monitoring %s, rec %s)",
            cycle.id, cycle.monitoring_id, rec.reference_number,
        )
    except Exception as e:
        logger.error("Failed to send day-3 reminder for cycle %s: %s", cycle.id, e)


def _send_escalation_notification(cycle, now):
    """
    Escalate overdue cycle to CIA reviewer (monitoring.reviewed_by).
    Publishes to notifications-high topic via publisher.send_notification().
    """
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        monitoring = cycle.monitoring
        rec = monitoring.recommendation

        # Auditee -- for display in the escalation email
        auditee_id = str(rec.responsible_party) if rec.responsible_party else None
        auditee = _resolve_user(iam, auditee_id, 'Responsible Party')

        # CIA reviewer -- escalation target
        cia_id = str(monitoring.reviewed_by) if monitoring.reviewed_by else None
        cia = _resolve_user(iam, cia_id, 'CIA Reviewer')

        if not cia.get('email'):
            logger.warning(
                "Cannot send escalation for cycle %s: CIA reviewer email missing "
                "(monitoring.reviewed_by=%s)", cycle.id, cia_id,
            )
            return

        days_overdue = (
            (now - cycle.response_deadline).days if cycle.response_deadline else
            (now - cycle.notified_at).days - 7 if cycle.notified_at else 0
        )
        deadline_str = (
            cycle.response_deadline.strftime('%Y-%m-%d %H:%M')
            if cycle.response_deadline else 'N/A'
        )

        context = {
            'cia_reviewer': {
                'first_name': cia['first_name'],
                'email': cia['email'],
            },
            'recommendation': {
                'reference_number': rec.reference_number,
                'title': rec.title,
            },
            'auditee': {
                'name': auditee['name'],
                'email': auditee.get('email', ''),
            },
            'response_deadline': deadline_str,
            'days_overdue': days_overdue,
            'cycle_number': cycle.cycle_number,
            'detail_url': _build_detail_url(cycle),
        }

        publisher.send_notification(
            template_code='grc.monitoring.escalated_to_cia',
            recipients={
                'email': [cia['email']],
                'user_ids': [cia_id] if cia_id else [],
            },
            context=context,
            priority='high',
            metadata={
                'monitoring_id': str(monitoring.id),
                'cycle_id': str(cycle.id),
                'cycle_number': cycle.cycle_number,
                'recommendation_id': str(rec.id),
                'escalated_to': cia_id,
            },
        )
        logger.info(
            "Escalation notification sent for cycle %s to CIA %s (monitoring %s, rec %s)",
            cycle.id, cia_id, monitoring.id, rec.reference_number,
        )
    except Exception as e:
        logger.error(
            "Failed to send escalation notification for cycle %s: %s", cycle.id, e
        )
