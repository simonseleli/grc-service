"""
Celery task for monthly Non-Conformance closure monitoring [GAP-16].

Runs on the 1st of each month at 08:00. Responsibilities:
  1. Find open NCs (status != 'closed') whose due_date has passed.
  2. Publish overdue notification to responsible_officer and RMQAM.
  3. Log escalation for RMQAM quarterly Commission reporting.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="grc.check_nc_closure_status")
def check_nc_closure_status():
    """Monthly task: flag overdue non-conformances and notify stakeholders."""
    from apps.core.models.risk_entities import NonConformance

    today = timezone.now().date()
    overdue_ncs = NonConformance.objects.filter(
        is_active=True,
        due_date__lt=today,
    ).exclude(
        status='closed',
    ).select_related('audit_report', 'iso_clause', 'nc_type')

    notified = 0
    for nc in overdue_ncs:
        _send_nc_overdue_notification(nc, today)
        notified += 1

    logger.info("NC closure check complete. Overdue NCs: %d", notified)
    return {'overdue_ncs_notified': notified}


# ── Helpers ────────────────────────────────────────────────────────────────


def _resolve_user(iam, user_id, fallback_name='User'):
    """Resolve IAM user profile."""
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


def _build_nc_url(nc_id):
    """Build portal URL for an NC detail page."""
    try:
        from django.conf import settings
        base = getattr(settings, 'STAFF_PORTAL_BASE_URL', 'https://portal.fcc.go.tz')
        return '{}/risk/non-conformance/{}/'.format(base, nc_id)
    except Exception:
        return ''


def _send_nc_overdue_notification(nc, today):
    """Notify responsible officer and RMQAM about an overdue NC."""
    try:
        from apps.core.notifications.publisher import get_notification_publisher
        from apps.infrastructure.external.iam_client import IAMClient

        iam = IAMClient()
        publisher = get_notification_publisher()

        days_overdue = (today - nc.due_date).days

        # Collect recipient IDs
        recipient_user_ids = []
        recipient_emails = []

        # Responsible officer
        if nc.responsible_officer:
            officer_id = str(nc.responsible_officer)
            officer = _resolve_user(iam, officer_id, 'Responsible Officer')
            recipient_user_ids.append(officer_id)
            if officer.get('email'):
                recipient_emails.append(officer['email'])

        # Raiser (QA who raised the NC)
        if nc.raised_by:
            raiser_id = str(nc.raised_by)
            raiser = _resolve_user(iam, raiser_id, 'Quality Auditor')
            if raiser_id not in recipient_user_ids:
                recipient_user_ids.append(raiser_id)
            if raiser.get('email') and raiser['email'] not in recipient_emails:
                recipient_emails.append(raiser['email'])

        iso_clause_str = ''
        if nc.iso_clause:
            iso_clause_str = str(nc.iso_clause)

        context = {
            'nc': {
                'id': str(nc.id),
                'description': nc.description[:100],
                'iso_clause': iso_clause_str,
                'nc_type': str(nc.nc_type) if nc.nc_type else '',
                'due_date': str(nc.due_date),
                'status': nc.status,
            },
            'days_overdue': days_overdue,
            'detail_url': _build_nc_url(nc.id),
        }

        publisher.send_notification(
            template_code='grc.qms.nc.overdue',
            recipients={
                'email': recipient_emails,
                'user_ids': recipient_user_ids,
                'roles': ['grc.rmqam'],
            },
            context=context,
            priority='high',
            metadata={
                'nc_id': str(nc.id),
                'audit_report_id': str(nc.audit_report_id),
                'days_overdue': days_overdue,
            },
        )
        logger.info(
            "Overdue NC notification sent for NC %s (%d days overdue)",
            nc.id, days_overdue,
        )
    except Exception as e:
        logger.error("Failed to send overdue notification for NC %s: %s", nc.id, e)
