"""
Celery task for Risk Management deadline enforcement.

Runs daily at 07:30. Responsibilities:
  1. Flag RTAPItems past target_date that are not 'completed' → notify responsible officer + RMQAM.
  2. Send RC reminder when quarterly submission deadline approaches (≤3 days).
  3. Escalate to RMQAM when RC has not submitted within 7 days of quarter end.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="grc.check_risk_monitoring_deadlines")
def check_risk_monitoring_deadlines():
    """Daily task: enforce RTAP target dates and quarterly submission windows."""
    overdue_flagged = _check_overdue_rtap_items()
    reminders_sent = _send_quarterly_submission_reminders()
    escalations_sent = _escalate_non_responsive_rcs()

    logger.info(
        "Risk monitoring deadline check complete: %d overdue, %d reminders, %d escalations",
        overdue_flagged, reminders_sent, escalations_sent,
    )
    return {
        'overdue_flagged': overdue_flagged,
        'reminders_sent': reminders_sent,
        'escalations_sent': escalations_sent,
    }


# ── Helpers ────────────────────────────────────────────────────────────────


def _resolve_user(iam, user_id, fallback_name='User'):
    """Resolve IAM user profile, returning a dict with first_name, name, email."""
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


def _build_detail_url(entity_type, entity_id):
    """Build portal URL for a risk entity."""
    try:
        from django.conf import settings
        base = getattr(settings, 'STAFF_PORTAL_BASE_URL', 'https://portal.fcc.go.tz')
        return '{}/risk/{}/{}/'.format(base, entity_type, entity_id)
    except Exception:
        return ''


# ── 1. Overdue RTAP Items ─────────────────────────────────────────────────


def _check_overdue_rtap_items():
    """Flag RTAPItems past target_date that are not completed."""
    from apps.core.models.risk_entities import RTAPItem

    today = timezone.now().date()
    overdue_items = RTAPItem.objects.filter(
        is_active=True,
        status__in=['not_started', 'in_progress'],
        target_date__lt=today,
    ).select_related('rtap', 'rtap__fiscal_year')

    flagged = 0
    for item in overdue_items:
        _send_rtap_overdue_notification(item, today)
        flagged += 1

    return flagged


def _send_rtap_overdue_notification(item, today):
    """Notify responsible officer and RMQAM about overdue RTAP item."""
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        officer_id = str(item.responsible_officer)
        officer = _resolve_user(iam, officer_id, 'Responsible Officer')
        days_overdue = (today - item.target_date).days

        recipients_user_ids = [officer_id]
        recipients_emails = []
        if officer.get('email'):
            recipients_emails.append(officer['email'])

        context = {
            'officer': {
                'first_name': officer['first_name'],
                'email': officer.get('email'),
            },
            'rtap_item': {
                'id': str(item.id),
                'treatment_description': item.treatment_description[:100],
                'target_date': str(item.target_date),
                'status': item.status,
            },
            'days_overdue': days_overdue,
            'fiscal_year': str(item.rtap.fiscal_year_id) if item.rtap else '',
            'detail_url': _build_detail_url('rtap-item', item.id),
        }

        publisher.send_notification(
            template_code='grc.risk.rtap_item.overdue',
            recipients={
                'email': recipients_emails,
                'user_ids': recipients_user_ids,
            },
            context=context,
            priority='high',
            metadata={
                'rtap_item_id': str(item.id),
                'rtap_id': str(item.rtap_id),
                'days_overdue': days_overdue,
            },
        )
        logger.info(
            "Overdue notification sent for RTAP item %s (%d days overdue)",
            item.id, days_overdue,
        )
    except Exception as e:
        logger.error("Failed to send overdue notification for RTAP item %s: %s", item.id, e)


# ── 2. Quarterly Submission Reminders ──────────────────────────────────────


def _send_quarterly_submission_reminders():
    """Send reminder to RCs when quarterly submission deadline is ≤3 days away."""
    from apps.core.models.lookups import Quarter
    from apps.core.models.risk_entities import RTAPItem, RTAPQuarterlyUpdate

    current_quarter = Quarter.get_current_quarter()
    if not current_quarter:
        return 0

    today = timezone.now().date()
    days_until_end = (current_quarter.end_date - today).days
    if days_until_end > 3 or days_until_end < 0:
        return 0

    # Find active RTAP items that don't have a quarterly update for the current quarter
    items_without_update = RTAPItem.objects.filter(
        is_active=True,
        status__in=['not_started', 'in_progress'],
    ).exclude(
        quarterly_updates__quarter=current_quarter,
    ).select_related('rtap', 'rtap__fiscal_year')

    # Group by responsible_officer to send one reminder per RC
    rc_items = {}
    for item in items_without_update:
        officer_id = str(item.responsible_officer)
        rc_items.setdefault(officer_id, []).append(item)

    sent = 0
    for officer_id, items in rc_items.items():
        _send_rc_submission_reminder(officer_id, items, current_quarter, days_until_end)
        sent += 1

    return sent


def _send_rc_submission_reminder(officer_id, items, quarter, days_until_end):
    """Send a single reminder to one RC about pending quarterly updates."""
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        officer = _resolve_user(iam, officer_id, 'Risk Champion')
        if not officer.get('email'):
            logger.warning("Cannot send quarterly reminder to RC %s: email missing", officer_id)
            return

        context = {
            'officer': {
                'first_name': officer['first_name'],
                'email': officer['email'],
            },
            'quarter_name': quarter.name,
            'days_remaining': days_until_end,
            'deadline': str(quarter.end_date),
            'pending_items_count': len(items),
            'detail_url': _build_detail_url('rtap', 'pending'),
        }

        publisher.send_notification(
            template_code='grc.risk.quarterly_update.reminder',
            recipients={
                'email': [officer['email']],
                'user_ids': [officer_id],
            },
            context=context,
            priority='high' if days_until_end <= 1 else 'normal',
            metadata={
                'quarter_id': str(quarter.id),
                'officer_id': officer_id,
                'pending_items': len(items),
            },
        )
        logger.info(
            "Quarterly reminder sent to RC %s: %d pending items, %d days remaining",
            officer_id, len(items), days_until_end,
        )
    except Exception as e:
        logger.error("Failed to send quarterly reminder to RC %s: %s", officer_id, e)


# ── 3. Escalation for Non-Responsive RCs ──────────────────────────────────


def _escalate_non_responsive_rcs():
    """Escalate to RMQAM when RCs haven't submitted within 7 days past quarter end."""
    from apps.core.models.lookups import Quarter
    from apps.core.models.risk_entities import RTAPItem

    today = timezone.now().date()

    # Find the most recently ended quarter (ended between 1 and 30 days ago)
    ended_quarter = Quarter.objects.filter(
        is_active=True,
        end_date__lt=today,
        end_date__gte=today - timedelta(days=30),
    ).order_by('-end_date').first()

    if not ended_quarter:
        return 0

    days_past_end = (today - ended_quarter.end_date).days
    if days_past_end < 7:
        return 0

    # Find RTAP items that still lack updates for the ended quarter
    items_without_update = RTAPItem.objects.filter(
        is_active=True,
        status__in=['not_started', 'in_progress'],
    ).exclude(
        quarterly_updates__quarter=ended_quarter,
    ).select_related('rtap', 'rtap__fiscal_year')

    if not items_without_update.exists():
        return 0

    # Group by responsible_officer
    rc_ids = set()
    for item in items_without_update:
        rc_ids.add(str(item.responsible_officer))

    sent = 0
    for rc_id in rc_ids:
        _send_escalation_to_rmqam(rc_id, ended_quarter, days_past_end)
        sent += 1

    return sent


def _send_escalation_to_rmqam(rc_id, quarter, days_past_end):
    """Send escalation notification to RMQAM about non-responsive RC."""
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        rc = _resolve_user(iam, rc_id, 'Risk Champion')

        context = {
            'rc': {
                'name': rc['name'],
                'user_id': rc_id,
            },
            'quarter_name': quarter.name,
            'days_past_deadline': days_past_end,
            'detail_url': _build_detail_url('rtap', 'overdue'),
        }

        # Publish to RMQAM role — WO resolves role-based recipients
        publisher.send_notification(
            template_code='grc.risk.quarterly_update.escalation',
            recipients={
                'roles': ['grc.rmqam'],
                'user_ids': [],
            },
            context=context,
            priority='high',
            metadata={
                'quarter_id': str(quarter.id),
                'rc_user_id': rc_id,
                'days_past_deadline': days_past_end,
            },
        )
        logger.info(
            "Escalation sent to RMQAM for RC %s: %d days past %s end",
            rc_id, days_past_end, quarter.name,
        )
    except Exception as e:
        logger.error("Failed to send escalation for RC %s: %s", rc_id, e)
