"""
PDF generation utilities for GRC formal output documents.

WeasyPrint (already in requirements.txt) renders an HTML Django template
into PDF bytes, which are then uploaded to DRS.

The bottom page margin in every template MUST be at least 55 mm so that
the DRS stamp (QR code 30×30 mm bottom-left + signature image 65×22 mm
bottom-right) fits without overlapping the document text.
"""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_declaration_pdf(decl) -> bytes:
    """
    Render a Declaration of Independence as PDF bytes.

    Args:
        decl: DeclarationOfIndependence model instance (with audit_engagement
              already select_related so no extra DB hit occurs).

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.

    Raises:
        ImportError: if WeasyPrint is not installed (it is in requirements.txt).
        Exception:   any WeasyPrint rendering error is propagated to the caller,
                     which should catch and log it non-blocking.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    context = {
        'decl': decl,
        'engagement': decl.audit_engagement,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/declaration_of_independence.html', context)
    return HTML(string=html_str).write_pdf()


def generate_engagement_notification_pdf(en) -> bytes:
    """
    Render an Engagement Notification as PDF bytes.

    Args:
        en: EngagementNotification model instance (with audit_engagement and
            audit_engagement__auditable_entity already select_related so no
            extra DB hits occur during template rendering).

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.

    Raises:
        ImportError: if WeasyPrint is not installed (it is in requirements.txt).
        Exception:   any WeasyPrint rendering error is propagated to the caller,
                     which should catch and log it non-blocking.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    context = {
        'en': en,
        'engagement': en.audit_engagement,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/engagement_notification.html', context)
    return HTML(string=html_str).write_pdf()


def generate_meeting_minutes_pdf(meeting) -> bytes:
    """
    Render Audit Meeting Minutes as PDF bytes.

    Applies to: entry, exit (SRS formal Process Outputs), pre_exit (SRS data requirement).
    Not stamped — meeting minutes do not go through a CIA approval workflow.

    Args:
        meeting: AuditMeeting model instance with engagement already select_related.

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    context = {
        'meeting': meeting,
        'engagement': meeting.engagement,
        'auditee_name': meeting.engagement.auditable_entity.name if meeting.engagement.auditable_entity_id else '',
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/meeting_minutes.html', context)
    return HTML(string=html_str).write_pdf()


def generate_attendance_register_pdf(meeting) -> bytes:
    """
    Render Audit Meeting Attendance Register as PDF bytes.

    Applies to: entry, exit meetings only (SRS data requirement — Attendance register).
    Not stamped — attendance registers do not go through a CIA approval workflow.

    Args:
        meeting: AuditMeeting model instance with engagement already select_related.

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    attendees = meeting.attendees or []
    context = {
        'meeting': meeting,
        'engagement': meeting.engagement,
        'auditee_name': meeting.engagement.auditable_entity.name if meeting.engagement.auditable_entity_id else '',
        'generated_at': timezone.now(),
        'present_count': sum(1 for a in attendees if a.get('present')),
    }
    html_str = render_to_string('grc/attendance_register.html', context)
    return HTML(string=html_str).write_pdf()
