"""
Celery tasks for 5-day response deadline enforcement (GAP 7).

Runs daily to:
- Mark overdue monitoring records
- Publish reminder events at day 3 (via Kafka → WO delivers notifications)
- Publish overdue alerts at day 5+
- Publish escalation events at day 7+ (to CIA)
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="grc.check_monitoring_deadlines")
def check_monitoring_deadlines():
    """Daily task: enforce 5-day response window on implementation monitoring records.

    - Day 3 after notification → reminder event
    - Day 5+ (past deadline) → mark is_overdue, publish alert
    - Day 7+ → escalate to CIA
    """
    from apps.core.models import ImplementationMonitoring

    now = timezone.now()
    updated_overdue = 0
    reminders_sent = 0
    escalations_sent = 0

    # ── 1. Mark overdue records ──────────────────────────────────────────
    newly_overdue = ImplementationMonitoring.objects.filter(
        notification_sent_at__isnull=False,
        response_deadline__lt=now,
        auditee_responded_at__isnull=True,
        is_overdue=False,
        is_active=True,
    )
    updated_overdue = newly_overdue.update(is_overdue=True)

    # ── 2. Day 3 reminders ──────────────────────────────────────────────
    # Records notified ~3 days ago that have NOT yet responded
    day3_window_start = now - timedelta(days=3, hours=12)
    day3_window_end = now - timedelta(days=2, hours=12)
    day3_records = ImplementationMonitoring.objects.filter(
        notification_sent_at__gte=day3_window_start,
        notification_sent_at__lt=day3_window_end,
        auditee_responded_at__isnull=True,
        is_active=True,
    ).select_related(
        'recommendation', 'recommendation__finding',
        'recommendation__finding__engagement',
    )

    for record in day3_records:
        _publish_event(record, 'monitoring.deadline_reminder', {
            'days_remaining': 2,
            'deadline': record.response_deadline.isoformat() if record.response_deadline else None,
        })
        reminders_sent += 1

    # ── 3. Day 7+ escalation (to CIA) ───────────────────────────────────
    day7_threshold = now - timedelta(days=7)
    escalation_records = ImplementationMonitoring.objects.filter(
        notification_sent_at__lt=day7_threshold,
        auditee_responded_at__isnull=True,
        escalated=False,
        is_active=True,
    ).select_related(
        'recommendation', 'recommendation__finding',
        'recommendation__finding__engagement',
    )

    for record in escalation_records:
        _publish_event(record, 'monitoring.escalated_to_cia', {
            'days_overdue': (now - record.notification_sent_at).days,
        })
        record.escalated = True
        record.save(update_fields=['escalated'])
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


def _publish_event(monitoring_record, event_type, extra_data=None):
    """Best-effort publish a monitoring event via Kafka."""
    try:
        from apps.infrastructure.services.messaging_service import messaging_service
        plan_id = None
        try:
            plan_id = monitoring_record.recommendation.finding.engagement.audit_plan_id
        except Exception:
            pass

        data = {
            'monitoring_id': str(monitoring_record.id),
            'recommendation_id': str(monitoring_record.recommendation_id),
        }
        if extra_data:
            data.update(extra_data)

        messaging_service.publish_audit_plan_event(
            event_type=event_type,
            plan_id=plan_id,
            additional_data=data,
        )
    except Exception as e:
        logger.error("Failed to publish monitoring event %s: %s", event_type, e)
