"""
Celery Tasks Package
Organizes tasks by domain
"""

from apps.core.tasks.organizational_sync import (
    sync_organizational_data,
    daily_organizational_sync,
    hourly_directorate_sync,
    cleanup_old_sync_logs,
)

from apps.core.tasks.report_generation import (
    generate_engagement_report_pdf,
    generate_quarterly_report_pdf,
    generate_report_docx,
    send_report_distribution_email,
)

from apps.core.tasks.monitoring_deadlines import (
    check_monitoring_deadlines,
)

__all__ = [
    # Organizational sync tasks
    'sync_organizational_data',
    'daily_organizational_sync',
    'hourly_directorate_sync',
    'cleanup_old_sync_logs',
    
    # Report generation tasks (Phase 2)
    'generate_engagement_report_pdf',
    'generate_quarterly_report_pdf',
    'generate_report_docx',
    'send_report_distribution_email',

    # Monitoring deadline enforcement (GAP 7)
    'check_monitoring_deadlines',
]
