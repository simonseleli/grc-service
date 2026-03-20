"""
Celery task for automatic archiving of closed legal cases.

Runs daily at 02:00 to archive cases that have been closed
for longer than LEGAL_ARCHIVE_AFTER_DAYS (default 90 days).

Pattern: mirrors apps/core/tasks/legal_case_deadlines.py
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="grc.archive_closed_legal_cases")
def archive_closed_legal_cases():
    """Daily task: auto-archive cases closed longer than the configured threshold."""
    from django.conf import settings
    from apps.core.models import CaseDefendant, CasePlaintiff

    archive_after_days = getattr(settings, 'LEGAL_ARCHIVE_AFTER_DAYS', 90)
    cutoff = timezone.now() - timedelta(days=archive_after_days)
    now = timezone.now()

    archived_count = 0

    for Model, label in [(CaseDefendant, 'defendant'), (CasePlaintiff, 'plaintiff')]:
        qs = Model.objects.filter(
            status='closed',
            is_active=True,
            is_archived=False,
            updated_at__lte=cutoff,
        )
        count = qs.update(is_archived=True, archived_at=now)
        archived_count += count
        if count:
            logger.info("Auto-archived %d %s case(s) closed before %s", count, label, cutoff.date())

    logger.info("archive_closed_legal_cases completed: %d total archived", archived_count)
    return {'archived': archived_count}
