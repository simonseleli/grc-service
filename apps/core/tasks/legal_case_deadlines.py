"""
Celery task for legal task (TaskLitigation) deadline enforcement.

Runs daily at 07:15 to:
  - Send 7-day, 2-day, and 1-day reminder notifications for approaching due dates
  - Mark overdue when due_date < today and status not in ('closed', 'overdue')

Pattern: mirrors apps/core/tasks/monitoring_deadlines.py
"""

import logging
from datetime import date, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="grc.check_legal_task_deadlines")
def check_legal_task_deadlines():
    """Daily task: send reminders and mark overdue for TaskLitigation records.

    - 7-day reminder: due_date = today + 7 days
    - 2-day reminder: due_date = today + 2 days
    - 1-day reminder: due_date = today + 1 day
    - Mark overdue: due_date < today, status not in ('closed', 'overdue')
    """
    from apps.core.models import TaskLitigation

    today = date.today()
    reminders_sent = 0
    overdue_marked = 0

    # ── 1. Reminder notifications ──────────────────────────────────
    reminder_windows = [
        (7, 'normal'),
        (2, 'high'),
        (1, 'high'),
    ]
    for days_ahead, priority in reminder_windows:
        target_date = today + timedelta(days=days_ahead)
        tasks_due = TaskLitigation.objects.filter(
            is_active=True,
            due_date=target_date,
        ).exclude(
            status__in=('closed', 'overdue'),
        )
        for task in tasks_due:
            _send_task_reminder(task, days_ahead, priority)
            reminders_sent += 1

    # ── 2. Mark overdue ────────────────────────────────────────────
    newly_overdue = TaskLitigation.objects.filter(
        is_active=True,
        due_date__lt=today,
    ).exclude(
        status__in=('closed', 'overdue'),
    )

    for task in newly_overdue:
        task.status = 'overdue'
        task.save(update_fields=['status'])
        _send_task_overdue_notification(task)
        overdue_marked += 1

    logger.info(
        "Legal task deadline check complete: %d reminders sent, %d tasks marked overdue",
        reminders_sent, overdue_marked,
    )
    return {
        'reminders_sent': reminders_sent,
        'overdue_marked': overdue_marked,
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


def _build_task_url(task):
    """Build staff portal URL for the litigation task."""
    try:
        from django.conf import settings
        base = getattr(settings, 'STAFF_PORTAL_BASE_URL', 'https://portal.fcc.go.tz')
        return '{}/legal/tasks/{}/'.format(base, task.id)
    except Exception:
        return ''


def _send_task_reminder(task, days_remaining, priority):
    """Send a deadline reminder for an approaching task."""
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        user_id = str(task.assigned_to_user_id) if task.assigned_to_user_id else None
        user = _resolve_user(iam, user_id, 'Assigned User')

        if not user.get('email'):
            logger.warning(
                "Cannot send reminder for task %s: assignee email missing", task.id,
            )
            return

        context = {
            'assignee': {
                'first_name': user['first_name'],
                'email': user['email'],
            },
            'task': {
                'id': str(task.id),
                'title': task.title[:200],
                'due_date': task.due_date.strftime('%Y-%m-%d'),
                'priority': task.priority,
                'days_remaining': days_remaining,
            },
            'detail_url': _build_task_url(task),
        }

        publisher.send_notification(
            template_code='grc.legal.task.deadline_reminder',
            recipients={
                'email': [user['email']],
                'user_ids': [user_id] if user_id else [],
            },
            context=context,
            priority=priority,
            metadata={
                'task_id': str(task.id),
                'days_remaining': days_remaining,
            },
        )
        logger.info(
            "Reminder sent for task %s (%d days remaining)", task.id, days_remaining,
        )
    except Exception as e:
        logger.error("Failed to send reminder for task %s: %s", task.id, e)


def _send_task_overdue_notification(task):
    """Send overdue notification for a task."""
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        user_id = str(task.assigned_to_user_id) if task.assigned_to_user_id else None
        user = _resolve_user(iam, user_id, 'Assigned User')

        if not user.get('email'):
            logger.warning(
                "Cannot send overdue notification for task %s: assignee email missing",
                task.id,
            )
            return

        days_overdue = (date.today() - task.due_date).days

        context = {
            'assignee': {
                'first_name': user['first_name'],
                'email': user['email'],
            },
            'task': {
                'id': str(task.id),
                'title': task.title[:200],
                'due_date': task.due_date.strftime('%Y-%m-%d'),
                'priority': task.priority,
                'days_overdue': days_overdue,
            },
            'detail_url': _build_task_url(task),
        }

        publisher.send_notification(
            template_code='grc.legal.task.overdue',
            recipients={
                'email': [user['email']],
                'user_ids': [user_id] if user_id else [],
            },
            context=context,
            priority='high',
            metadata={
                'task_id': str(task.id),
                'days_overdue': days_overdue,
            },
        )
        logger.info(
            "Overdue notification sent for task %s (%d days overdue)",
            task.id, days_overdue,
        )
    except Exception as e:
        logger.error(
            "Failed to send overdue notification for task %s: %s", task.id, e,
        )
