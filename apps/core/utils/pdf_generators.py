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


# ══════════════════════════════════════════════════════════════════════════════
# Risk Management PDF Generators
# ══════════════════════════════════════════════════════════════════════════════


def generate_appointment_letter_pdf(appointment) -> bytes:
    """
    Render RC or QA formal appointment letter as PDF bytes.

    Args:
        appointment: RiskChampionAppointment or QualityAuditorAppointment
                     with risk_champion/quality_auditor already select_related.

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    is_rc = hasattr(appointment, 'risk_champion')
    person = appointment.risk_champion if is_rc else appointment.quality_auditor
    context = {
        'appointment': appointment,
        'person': person,
        'is_risk_champion': is_rc,
        'role_title': 'Risk Champion' if is_rc else 'Quality Auditor',
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/risk/appointment_letter.html', context)
    return HTML(string=html_str).write_pdf()


def generate_risk_register_pdf(register) -> bytes:
    """
    Render Institutional Risk Register as PDF bytes.

    Args:
        register: InstitutionalRiskRegister with fiscal_year and
                  entries__risk_sheet select_related/prefetched.

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    entries = register.entries.select_related(
        'risk_sheet__risk_category',
        'risk_sheet__likelihood',
        'risk_sheet__impact',
        'risk_sheet__inherent_risk_level',
        'risk_sheet__residual_risk_level',
    ).filter(is_active=True).order_by('risk_ranking')
    context = {
        'register': register,
        'entries': entries,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/risk/institutional_risk_register.html', context)
    return HTML(string=html_str).write_pdf()


def generate_rtap_pdf(rtap) -> bytes:
    """
    Render Risk Treatment Action Plan as PDF bytes.

    Args:
        rtap: RiskTreatmentActionPlan with inst_register, fiscal_year,
              and items prefetched.

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    items = rtap.items.select_related(
        'inst_entry__risk_sheet__risk_category',
    ).filter(is_active=True).order_by('sort_order')
    context = {
        'rtap': rtap,
        'items': items,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/risk/risk_treatment_action_plan.html', context)
    return HTML(string=html_str).write_pdf()


def generate_quarterly_report_pdf(report) -> bytes:
    """
    Render Quarterly Performance Report as PDF bytes.

    Args:
        report: QuarterlyPerformanceReport with fiscal_year and quarter
                select_related.

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    context = {
        'report': report,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/risk/quarterly_performance_report.html', context)
    return HTML(string=html_str).write_pdf()


def generate_qms_audit_report_pdf(audit_report) -> bytes:
    """
    Render QMS Audit Report as PDF bytes.

    Args:
        audit_report: QMSAuditReport with audit_plan and
                      audit_plan__audit_program select_related.
                      nonconformances prefetched.

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    nonconformances = audit_report.nonconformances.select_related(
        'iso_clause', 'nc_type',
    ).filter(is_active=True)
    checklists = audit_report.audit_plan.checklists.select_related(
        'iso_clause',
    ).filter(is_active=True)
    context = {
        'report': audit_report,
        'plan': audit_report.audit_plan,
        'nonconformances': nonconformances,
        'checklists': checklists,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/risk/qms_audit_report.html', context)
    return HTML(string=html_str).write_pdf()


def generate_risk_dashboard_pdf(data: dict, fiscal_year=None) -> bytes:
    """
    Render Risk Dashboard summary as PDF bytes.  GAP-20.

    Args:
        data: Dashboard stats dict (same shape as RiskDashboardView response).
        fiscal_year: Optional FiscalYear instance for the page header.

    Returns:
        Raw PDF bytes.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    context = {
        'data': data,
        'fiscal_year': fiscal_year,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/risk/risk_dashboard.html', context)
    return HTML(string=html_str).write_pdf()
