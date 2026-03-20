"""
Celery task for legal directive deadline enforcement.

Runs daily at 07:00 to mark overdue MeetingDirective and LitigationDirective
records and send notifications to assigned users.

Pattern: mirrors apps/core/tasks/monitoring_deadlines.py
"""

import logging
from datetime import date

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="grc.check_legal_directive_deadlines")
def check_legal_directive_deadlines():
    """Daily task: mark overdue MeetingDirective and LitigationDirective records.

    - MeetingDirective: due_date < today, status not in (closed, fully_closed, overdue)
      → status='overdue', send notification to assigned_user_id
    - LitigationDirective: due_date < today, status not in (closed,)
      → status='closed' is the only terminal, so we log overdue but cannot flip
        to 'overdue' (status choices: open, in_progress, closed).
        Instead we send a warning notification to issued_by_user_id.
    """
    from apps.core.models import MeetingDirective, LitigationDirective

    today = date.today()
    meeting_overdue = 0
    litigation_warned = 0

    # ── 1. MeetingDirective overdue ────────────────────────────────
    newly_overdue = MeetingDirective.objects.filter(
        is_active=True,
        due_date__lt=today,
    ).exclude(
        status__in=('closed', 'fully_closed', 'overdue'),
    )

    for directive in newly_overdue:
        directive.status = 'overdue'
        directive.save(update_fields=['status'])
        _send_directive_overdue_notification(directive, 'meeting')
        meeting_overdue += 1

    # ── 2. LitigationDirective overdue warning ────────────────────
    lit_overdue = LitigationDirective.objects.filter(
        is_active=True,
        due_date__lt=today,
    ).exclude(
        status='closed',
    )

    for directive in lit_overdue:
        _send_directive_overdue_notification(directive, 'litigation')
        litigation_warned += 1

    logger.info(
        "Legal directive deadline check complete: "
        "%d meeting directives marked overdue, %d litigation directives warned",
        meeting_overdue, litigation_warned,
    )
    return {
        'meeting_directives_overdue': meeting_overdue,
        'litigation_directives_warned': litigation_warned,
    }


# ──────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────

def _resolve_user(iam, user_id, fallback_name='User'):
    """Resolve a user UUID to name/email dict via IAMClient."""
    if not user_id:
        return {'first_name': fallback_name, 'name': fallback_name, 'email': None}
    try:
        profile = iam.get_user_profile(str(user_id))
        if profile:
            first = profile.get('first_name', '')
            last = profile.get('last_name', '')
            full = '{} {}'.format(first, last).strip() or fallback_name
            return {'first_name': first or fallback_name, 'name': full, 'email': profile.get('email')}
    except Exception as e:
        logger.warning("IAM resolution failed for user %s: %s", user_id, e)
    return {'first_name': fallback_name, 'name': fallback_name, 'email': None}


def _build_detail_url(directive, directive_type):
    """Build staff portal URL for the directive."""
    try:
        from django.conf import settings
        base = getattr(settings, 'STAFF_PORTAL_BASE_URL', 'https://portal.fcc.go.tz')
        if directive_type == 'meeting':
            return '{}/legal/directives/{}/'.format(base, directive.id)
        return '{}/legal/litigation-directives/{}/'.format(base, directive.id)
    except Exception:
        return ''


def _send_directive_overdue_notification(directive, directive_type):
    """Send overdue notification for a directive via WO notification pipeline."""
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        if directive_type == 'meeting':
            user_id = str(directive.assigned_user_id) if directive.assigned_user_id else None
        else:
            user_id = str(directive.issued_by_user_id) if directive.issued_by_user_id else None

        user = _resolve_user(iam, user_id, 'Assigned User')

        if not user.get('email'):
            logger.warning(
                "Cannot send overdue notification for %s directive %s: email missing",
                directive_type, directive.id,
            )
            return

        days_overdue = (date.today() - directive.due_date).days
        due_date_str = directive.due_date.strftime('%Y-%m-%d') if directive.due_date else 'N/A'

        context = {
            'assignee': {
                'first_name': user['first_name'],
                'email': user['email'],
            },
            'directive': {
                'id': str(directive.id),
                'type': directive_type,
                'description': str(directive.description if directive_type == 'meeting'
                                   else directive.instruction)[:200],
                'due_date': due_date_str,
                'days_overdue': days_overdue,
            },
            'detail_url': _build_detail_url(directive, directive_type),
        }

        publisher.send_notification(
            template_code='grc.legal.directive.overdue',
            recipients={
                'email': [user['email']],
                'user_ids': [user_id] if user_id else [],
            },
            context=context,
            priority='high',
            metadata={
                'directive_id': str(directive.id),
                'directive_type': directive_type,
                'days_overdue': days_overdue,
            },
        )
        logger.info(
            "Overdue notification sent for %s directive %s (%d days overdue)",
            directive_type, directive.id, days_overdue,
        )
    except Exception as e:
        logger.error(
            "Failed to send overdue notification for %s directive %s: %s",
            directive_type, directive.id, e,
        )
