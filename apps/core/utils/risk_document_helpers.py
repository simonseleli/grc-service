"""
Risk Management — DRS upload & stamp helpers.

Non-blocking, idempotent helpers that generate PDFs, upload to DRS, and
trigger the digital-signature stamp. Each function follows the same pattern
established by the Declaration of Independence flow (GAP-9) and the
legal module stamp utility (GAP-10).

Rules:
  - Never store file bytes — only document_id (UUID) and stamped_document_url.
  - Upload is non-blocking: exceptions are logged and swallowed.
  - Stamp calls must happen OUTSIDE transaction.atomic() blocks.
  - Rewrite internal Docker URLs to DOCUMENT_SERVICE_PUBLIC_URL before saving.
"""

import io
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


# ── Upload helpers ─────────────────────────────────────────────────────────


def _upload_appointment_letter_pdf_to_drs(appointment, auth_token=None):
    """
    Generate appointment letter PDF and upload to DRS.
    Works for both RiskChampionAppointment and QualityAuditorAppointment.
    Idempotent: skips if document_id is already set.
    """
    if appointment.document_id:
        return

    from apps.infrastructure.external.document_service_client import DocumentServiceClient
    from apps.core.utils.pdf_generators import generate_appointment_letter_pdf

    is_rc = hasattr(appointment, 'risk_champion')
    entity_type = 'risk_champion_appointment' if is_rc else 'quality_auditor_appointment'
    role = 'Risk Champion' if is_rc else 'Quality Auditor'

    try:
        pdf_bytes = generate_appointment_letter_pdf(appointment)
        client = DocumentServiceClient(auth_token=auth_token)
        doc = client.create_document_with_file(
            title=f"{role} Appointment Letter — {appointment.id}",
            description=f"Formal appointment letter for {role}",
            document_type='risk_appointment_letter',
            classification='confidential',
            retention_period=2555,
            file_data=io.BytesIO(pdf_bytes),
            file_name=f"appointment_letter_{appointment.id}.pdf",
            metadata={
                'source_service': 'grc',
                'entity_type': entity_type,
                'entity_id': str(appointment.id),
            },
        )
        appointment.document_id = doc['id']
        appointment.save(update_fields=['document_id'])
        logger.info(
            "Risk PDF: %s appointment %s uploaded to DRS as document %s",
            role, appointment.id, doc['id'],
        )
    except Exception as exc:
        logger.warning(
            "Risk PDF: Failed to upload %s appointment letter %s: %s",
            role, appointment.id, exc,
        )


def _reupload_appointment_letter_pdf(appointment, auth_token=None):
    """Re-generate and overwrite the existing DRS file (e.g. after approval)."""
    if not appointment.document_id:
        return

    from apps.infrastructure.external.document_service_client import DocumentServiceClient
    from apps.core.utils.pdf_generators import generate_appointment_letter_pdf

    try:
        pdf_bytes = generate_appointment_letter_pdf(appointment)
        DocumentServiceClient(auth_token=auth_token).upload_file(
            document_id=str(appointment.document_id),
            file_data=io.BytesIO(pdf_bytes),
            file_name=f"appointment_letter_{appointment.id}.pdf",
        )
        logger.info("Risk PDF: Re-uploaded appointment letter %s", appointment.id)
    except Exception as exc:
        logger.warning("Risk PDF: Re-upload failed for appointment %s: %s", appointment.id, exc)


def _upload_risk_register_pdf_to_drs(register, auth_token=None):
    """
    Generate IRR PDF and upload to DRS.
    Idempotent: skips if document_id already set.
    On re-submit, overwrites existing file.
    """
    from apps.infrastructure.external.document_service_client import DocumentServiceClient
    from apps.core.utils.pdf_generators import generate_risk_register_pdf

    try:
        pdf_bytes = generate_risk_register_pdf(register)
        client = DocumentServiceClient(auth_token=auth_token)

        if register.document_id:
            client.upload_file(
                document_id=str(register.document_id),
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"institutional_risk_register_{register.id}.pdf",
            )
            logger.info("Risk PDF: Re-uploaded IRR %s", register.id)
        else:
            doc = client.create_document_with_file(
                title=f"Institutional Risk Register — FY {register.fiscal_year_id}",
                description="Organisation-wide Risk Register",
                document_type='risk_register',
                classification='confidential',
                retention_period=2555,
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"institutional_risk_register_{register.id}.pdf",
                metadata={
                    'source_service': 'grc',
                    'entity_type': 'institutional_risk_register',
                    'entity_id': str(register.id),
                    'fiscal_year_id': str(register.fiscal_year_id),
                },
            )
            register.document_id = doc['id']
            register.save(update_fields=['document_id'])
            logger.info("Risk PDF: IRR %s uploaded to DRS as document %s", register.id, doc['id'])
    except Exception as exc:
        logger.warning("Risk PDF: Failed to upload IRR %s: %s", register.id, exc)


def _upload_rtap_pdf_to_drs(rtap, auth_token=None):
    """
    Generate RTAP PDF and upload to DRS.
    Idempotent on first upload; overwrites on re-submit.
    """
    from apps.infrastructure.external.document_service_client import DocumentServiceClient
    from apps.core.utils.pdf_generators import generate_rtap_pdf

    try:
        pdf_bytes = generate_rtap_pdf(rtap)
        client = DocumentServiceClient(auth_token=auth_token)

        if rtap.document_id:
            client.upload_file(
                document_id=str(rtap.document_id),
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"rtap_{rtap.id}.pdf",
            )
            logger.info("Risk PDF: Re-uploaded RTAP %s", rtap.id)
        else:
            doc = client.create_document_with_file(
                title=f"Risk Treatment Action Plan — FY {rtap.fiscal_year_id}",
                description="Risk Treatment Action Plan",
                document_type='risk_rtap',
                classification='confidential',
                retention_period=2555,
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"rtap_{rtap.id}.pdf",
                metadata={
                    'source_service': 'grc',
                    'entity_type': 'risk_treatment_action_plan',
                    'entity_id': str(rtap.id),
                    'fiscal_year_id': str(rtap.fiscal_year_id),
                },
            )
            rtap.document_id = doc['id']
            rtap.save(update_fields=['document_id'])
            logger.info("Risk PDF: RTAP %s uploaded to DRS as document %s", rtap.id, doc['id'])
    except Exception as exc:
        logger.warning("Risk PDF: Failed to upload RTAP %s: %s", rtap.id, exc)


def _upload_quarterly_report_pdf_to_drs(report, auth_token=None):
    """
    Generate Quarterly Performance Report PDF and upload to DRS.
    Idempotent on first upload; overwrites on re-submit.
    """
    from apps.infrastructure.external.document_service_client import DocumentServiceClient
    from apps.core.utils.pdf_generators import generate_quarterly_report_pdf

    try:
        pdf_bytes = generate_quarterly_report_pdf(report)
        client = DocumentServiceClient(auth_token=auth_token)

        if report.document_id:
            client.upload_file(
                document_id=str(report.document_id),
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"quarterly_report_{report.id}.pdf",
            )
            logger.info("Risk PDF: Re-uploaded QPR %s", report.id)
        else:
            doc = client.create_document_with_file(
                title=f"Quarterly Risk Report — FY {report.fiscal_year_id} Q{report.quarter_id}",
                description="Quarterly Risk Management Performance Report",
                document_type='risk_quarterly_report',
                classification='confidential',
                retention_period=2555,
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"quarterly_report_{report.id}.pdf",
                metadata={
                    'source_service': 'grc',
                    'entity_type': 'quarterly_performance_report',
                    'entity_id': str(report.id),
                    'fiscal_year_id': str(report.fiscal_year_id),
                    'quarter_id': str(report.quarter_id),
                },
            )
            report.document_id = doc['id']
            report.save(update_fields=['document_id'])
            logger.info("Risk PDF: QPR %s uploaded to DRS as document %s", report.id, doc['id'])
    except Exception as exc:
        logger.warning("Risk PDF: Failed to upload QPR %s: %s", report.id, exc)


def _upload_qms_audit_report_pdf_to_drs(audit_report, auth_token=None):
    """
    Generate QMS Audit Report PDF and upload to DRS.
    Idempotent on first upload; overwrites after signing.
    """
    from apps.infrastructure.external.document_service_client import DocumentServiceClient
    from apps.core.utils.pdf_generators import generate_qms_audit_report_pdf

    try:
        pdf_bytes = generate_qms_audit_report_pdf(audit_report)
        client = DocumentServiceClient(auth_token=auth_token)

        if audit_report.document_id:
            client.upload_file(
                document_id=str(audit_report.document_id),
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"qms_audit_report_{audit_report.id}.pdf",
            )
            logger.info("Risk PDF: Re-uploaded QMS Audit Report %s", audit_report.id)
        else:
            doc = client.create_document_with_file(
                title=f"QMS Audit Report — {audit_report.report_title}",
                description="QMS Internal Audit Report",
                document_type='risk_qms_audit_report',
                classification='confidential',
                retention_period=2555,
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"qms_audit_report_{audit_report.id}.pdf",
                metadata={
                    'source_service': 'grc',
                    'entity_type': 'qms_audit_report',
                    'entity_id': str(audit_report.id),
                    'audit_plan_id': str(audit_report.audit_plan_id),
                },
            )
            audit_report.document_id = doc['id']
            audit_report.save(update_fields=['document_id'])
            logger.info(
                "Risk PDF: QMS Audit Report %s uploaded to DRS as document %s",
                audit_report.id, doc['id'],
            )
    except Exception as exc:
        logger.warning("Risk PDF: Failed to upload QMS Audit Report %s: %s", audit_report.id, exc)


# ── Stamp helpers ──────────────────────────────────────────────────────────


def stamp_risk_document(entity, approver_id, entity_type, auth_token=None):
    """
    Apply DRS digital-signature stamp to a risk management entity's document.

    Parameters
    ----------
    entity : Model instance
        Must have ``document_id`` and ``stamped_document_url`` fields.
    approver_id : str
        UUID of the approver whose signature appears on the stamp.
    entity_type : str
        Entity type string for the QR verification URL.
    auth_token : str | None
        Bearer JWT forwarded to DRS.

    Returns
    -------
    bool
        True if stamp applied successfully; False otherwise.
    """
    if not entity.document_id:
        logger.info(
            "Risk Stamp: Skipping stamp for %s %s — no document_id set.",
            entity_type, entity.id,
        )
        return False

    try:
        from apps.infrastructure.external.document_service_client import DocumentServiceClient

        client = DocumentServiceClient(auth_token=auth_token)
        result = client.generate_approved_stamp(
            document_id=str(entity.document_id),
            approver_id=str(approver_id),
            entity_type=entity_type,
            entity_id=str(entity.id),
        )

        stamped_url = result.get('stamped_document_url')
        if stamped_url:
            internal_base = settings.DOCUMENT_SERVICE_URL.rstrip('/')
            public_base = getattr(settings, 'DOCUMENT_SERVICE_PUBLIC_URL', '').rstrip('/')
            if public_base and stamped_url.startswith(internal_base):
                stamped_url = public_base + stamped_url[len(internal_base):]
            entity.stamped_document_url = stamped_url
            entity.save(update_fields=['stamped_document_url'])

        logger.info("Risk Stamp: Stamped %s %s", entity_type, entity.id)
        return True

    except Exception as exc:
        logger.warning("Risk Stamp: Failed for %s %s: %s", entity_type, entity.id, exc)
        return False
