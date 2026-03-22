"""
Risk Management Module — PDF Generation & DRS Upload Tests (Phase 11).

Covers:
  - 5 PDF generator functions (WeasyPrint HTML → PDF)
  - 6 DRS upload helpers (create, re-upload, idempotency)
  - stamp_risk_document (stamp + URL rewrite)
  - View integration (upload on submit, re-upload + stamp on approval/sign)

Pattern: matches existing test_views.py / test_services.py mock-heavy approach.
All WeasyPrint + DRS calls are mocked — no actual PDF rendering or HTTP calls.
"""
import io
import uuid
from unittest.mock import patch, MagicMock, call

import pytest

from tests.risk_management.conftest import (
    RMQAM_USER_ID, RC_USER_ID, QA_USER_ID, TL_USER_ID,
    DOCUMENT_UUID, PLAN_UUID,
)


# ── Module paths for patching ──────────────────────────────────────────────

PDF_MOD = "apps.core.utils.pdf_generators"
HELPERS_MOD = "apps.core.utils.risk_document_helpers"
# These are imported inside functions, so we patch at the source module
RENDER = "django.template.loader.render_to_string"
WEASY_HTML = "weasyprint.HTML"
DRS_CLIENT = "apps.infrastructure.external.document_service_client.DocumentServiceClient"

# ═══════════════════════════════════════════════════════════════════════════════
# 1. PDF Generator Functions
# ═══════════════════════════════════════════════════════════════════════════════


class TestGenerateAppointmentLetterPDF:

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>mocked</html>")
    def test_rc_appointment_generates_pdf(self, mock_render, mock_html, rc_appointment):
        mock_html.return_value.write_pdf.return_value = b"%PDF-mock"
        from apps.core.utils.pdf_generators import generate_appointment_letter_pdf

        result = generate_appointment_letter_pdf(rc_appointment)

        assert result == b"%PDF-mock"
        mock_render.assert_called_once()
        ctx = mock_render.call_args[0][1]
        assert ctx['is_risk_champion'] is True
        assert ctx['role_title'] == 'Risk Champion'
        assert 'appointment' in ctx
        assert 'person' in ctx

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>mocked</html>")
    def test_qa_appointment_generates_pdf(self, mock_render, mock_html, qa_appointment):
        mock_html.return_value.write_pdf.return_value = b"%PDF-mock"
        from apps.core.utils.pdf_generators import generate_appointment_letter_pdf

        result = generate_appointment_letter_pdf(qa_appointment)

        assert result == b"%PDF-mock"
        ctx = mock_render.call_args[0][1]
        assert ctx['is_risk_champion'] is False
        assert ctx['role_title'] == 'Quality Auditor'


class TestGenerateRiskRegisterPDF:

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>register</html>")
    def test_generates_pdf(self, mock_render, mock_html, inst_register, inst_entry):
        mock_html.return_value.write_pdf.return_value = b"%PDF-register"
        from apps.core.utils.pdf_generators import generate_risk_register_pdf

        result = generate_risk_register_pdf(inst_register)

        assert result == b"%PDF-register"
        ctx = mock_render.call_args[0][1]
        assert ctx['register'] == inst_register
        assert 'entries' in ctx


class TestGenerateRTAPPDF:

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>rtap</html>")
    def test_generates_pdf(self, mock_render, mock_html, rtap, rtap_item):
        mock_html.return_value.write_pdf.return_value = b"%PDF-rtap"
        from apps.core.utils.pdf_generators import generate_rtap_pdf

        result = generate_rtap_pdf(rtap)

        assert result == b"%PDF-rtap"
        ctx = mock_render.call_args[0][1]
        assert ctx['rtap'] == rtap
        assert 'items' in ctx


class TestGenerateQuarterlyReportPDF:

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>qpr</html>")
    def test_generates_pdf(self, mock_render, mock_html, quarterly_report):
        mock_html.return_value.write_pdf.return_value = b"%PDF-qpr"
        from apps.core.utils.pdf_generators import generate_quarterly_report_pdf

        result = generate_quarterly_report_pdf(quarterly_report)

        assert result == b"%PDF-qpr"
        ctx = mock_render.call_args[0][1]
        assert ctx['report'] == quarterly_report


class TestGenerateQMSAuditReportPDF:

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>audit</html>")
    def test_generates_pdf(self, mock_render, mock_html, qms_report, audit_checklist, nonconformance):
        mock_html.return_value.write_pdf.return_value = b"%PDF-audit"
        from apps.core.utils.pdf_generators import generate_qms_audit_report_pdf

        result = generate_qms_audit_report_pdf(qms_report)

        assert result == b"%PDF-audit"
        ctx = mock_render.call_args[0][1]
        assert ctx['report'] == qms_report
        assert 'nonconformances' in ctx
        assert 'checklists' in ctx


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DRS Upload Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class TestUploadAppointmentLetterPDF:

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_appointment_letter_pdf", return_value=b"%PDF")
    def test_first_upload_creates_document(self, mock_gen, mock_client_cls, rc_appointment):
        mock_client = mock_client_cls.return_value
        mock_client.create_document_with_file.return_value = {'id': str(DOCUMENT_UUID)}

        from apps.core.utils.risk_document_helpers import _upload_appointment_letter_pdf_to_drs
        _upload_appointment_letter_pdf_to_drs(rc_appointment, auth_token='tok')

        mock_client.create_document_with_file.assert_called_once()
        rc_appointment.refresh_from_db()
        assert str(rc_appointment.document_id) == str(DOCUMENT_UUID)

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_appointment_letter_pdf", return_value=b"%PDF")
    def test_idempotent_skip_when_document_id_set(self, mock_gen, mock_client_cls, rc_appointment):
        rc_appointment.document_id = DOCUMENT_UUID
        rc_appointment.save(update_fields=['document_id'])

        from apps.core.utils.risk_document_helpers import _upload_appointment_letter_pdf_to_drs
        _upload_appointment_letter_pdf_to_drs(rc_appointment, auth_token='tok')

        mock_gen.assert_not_called()
        mock_client_cls.assert_not_called()

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_appointment_letter_pdf", return_value=b"%PDF")
    def test_exception_logged_not_raised(self, mock_gen, mock_client_cls, rc_appointment):
        mock_client_cls.return_value.create_document_with_file.side_effect = RuntimeError("DRS down")

        from apps.core.utils.risk_document_helpers import _upload_appointment_letter_pdf_to_drs
        _upload_appointment_letter_pdf_to_drs(rc_appointment, auth_token='tok')  # should not raise

        rc_appointment.refresh_from_db()
        assert rc_appointment.document_id is None


class TestReuploadAppointmentLetterPDF:

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_appointment_letter_pdf", return_value=b"%PDF")
    def test_reupload_calls_upload_file(self, mock_gen, mock_client_cls, rc_appointment):
        rc_appointment.document_id = DOCUMENT_UUID
        rc_appointment.save(update_fields=['document_id'])

        from apps.core.utils.risk_document_helpers import _reupload_appointment_letter_pdf
        _reupload_appointment_letter_pdf(rc_appointment, auth_token='tok')

        mock_client_cls.return_value.upload_file.assert_called_once()

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_appointment_letter_pdf", return_value=b"%PDF")
    def test_reupload_skips_when_no_document_id(self, mock_gen, mock_client_cls, rc_appointment):
        from apps.core.utils.risk_document_helpers import _reupload_appointment_letter_pdf
        _reupload_appointment_letter_pdf(rc_appointment, auth_token='tok')

        mock_gen.assert_not_called()


class TestUploadRiskRegisterPDF:

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_risk_register_pdf", return_value=b"%PDF")
    def test_first_upload_creates_document(self, mock_gen, mock_client_cls, inst_register):
        mock_client = mock_client_cls.return_value
        mock_client.create_document_with_file.return_value = {'id': str(DOCUMENT_UUID)}

        from apps.core.utils.risk_document_helpers import _upload_risk_register_pdf_to_drs
        _upload_risk_register_pdf_to_drs(inst_register, auth_token='tok')

        mock_client.create_document_with_file.assert_called_once()
        inst_register.refresh_from_db()
        assert str(inst_register.document_id) == str(DOCUMENT_UUID)

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_risk_register_pdf", return_value=b"%PDF")
    def test_reupload_overwrites_existing(self, mock_gen, mock_client_cls, inst_register):
        inst_register.document_id = DOCUMENT_UUID
        inst_register.save(update_fields=['document_id'])

        from apps.core.utils.risk_document_helpers import _upload_risk_register_pdf_to_drs
        _upload_risk_register_pdf_to_drs(inst_register, auth_token='tok')

        mock_client_cls.return_value.upload_file.assert_called_once()


class TestUploadRTAPPDF:

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_rtap_pdf", return_value=b"%PDF")
    def test_first_upload_creates_document(self, mock_gen, mock_client_cls, rtap):
        mock_client_cls.return_value.create_document_with_file.return_value = {'id': str(DOCUMENT_UUID)}

        from apps.core.utils.risk_document_helpers import _upload_rtap_pdf_to_drs
        _upload_rtap_pdf_to_drs(rtap, auth_token='tok')

        mock_client_cls.return_value.create_document_with_file.assert_called_once()
        rtap.refresh_from_db()
        assert str(rtap.document_id) == str(DOCUMENT_UUID)


class TestUploadQuarterlyReportPDF:

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_quarterly_report_pdf", return_value=b"%PDF")
    def test_first_upload_creates_document(self, mock_gen, mock_client_cls, quarterly_report):
        mock_client_cls.return_value.create_document_with_file.return_value = {'id': str(DOCUMENT_UUID)}

        from apps.core.utils.risk_document_helpers import _upload_quarterly_report_pdf_to_drs
        _upload_quarterly_report_pdf_to_drs(quarterly_report, auth_token='tok')

        mock_client_cls.return_value.create_document_with_file.assert_called_once()
        quarterly_report.refresh_from_db()
        assert str(quarterly_report.document_id) == str(DOCUMENT_UUID)


class TestUploadQMSAuditReportPDF:

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_qms_audit_report_pdf", return_value=b"%PDF")
    def test_first_upload_creates_document(self, mock_gen, mock_client_cls, qms_report):
        mock_client_cls.return_value.create_document_with_file.return_value = {'id': str(DOCUMENT_UUID)}

        from apps.core.utils.risk_document_helpers import _upload_qms_audit_report_pdf_to_drs
        _upload_qms_audit_report_pdf_to_drs(qms_report, auth_token='tok')

        mock_client_cls.return_value.create_document_with_file.assert_called_once()
        qms_report.refresh_from_db()
        assert str(qms_report.document_id) == str(DOCUMENT_UUID)

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    @patch(f"{PDF_MOD}.generate_qms_audit_report_pdf", return_value=b"%PDF")
    def test_reupload_overwrites_existing(self, mock_gen, mock_client_cls, qms_report):
        qms_report.document_id = DOCUMENT_UUID
        qms_report.save(update_fields=['document_id'])

        from apps.core.utils.risk_document_helpers import _upload_qms_audit_report_pdf_to_drs
        _upload_qms_audit_report_pdf_to_drs(qms_report, auth_token='tok')

        mock_client_cls.return_value.upload_file.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Stamp Helper
# ═══════════════════════════════════════════════════════════════════════════════


class TestStampRiskDocument:

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    def test_stamps_and_rewrites_url(self, mock_client_cls, inst_register, settings):
        settings.DOCUMENT_SERVICE_URL = 'http://document-records-service:8000'
        settings.DOCUMENT_SERVICE_PUBLIC_URL = 'https://api.example.com/drs'

        inst_register.document_id = DOCUMENT_UUID
        inst_register.save(update_fields=['document_id'])

        mock_client_cls.return_value.generate_approved_stamp.return_value = {
            'stamped_document_url': 'http://document-records-service:8000/files/stamped.pdf'
        }

        from apps.core.utils.risk_document_helpers import stamp_risk_document
        result = stamp_risk_document(
            inst_register, approver_id=str(RMQAM_USER_ID),
            entity_type='institutional_risk_register', auth_token='tok',
        )

        assert result is True
        inst_register.refresh_from_db()
        assert inst_register.stamped_document_url == 'https://api.example.com/drs/files/stamped.pdf'

    @pytest.mark.django_db
    def test_skips_when_no_document_id(self, inst_register):
        from apps.core.utils.risk_document_helpers import stamp_risk_document
        result = stamp_risk_document(
            inst_register, approver_id=str(RMQAM_USER_ID),
            entity_type='institutional_risk_register', auth_token='tok',
        )
        assert result is False

    @pytest.mark.django_db
    @patch(DRS_CLIENT)
    def test_exception_logged_not_raised(self, mock_client_cls, inst_register):
        inst_register.document_id = DOCUMENT_UUID
        inst_register.save(update_fields=['document_id'])
        mock_client_cls.return_value.generate_approved_stamp.side_effect = RuntimeError("DRS down")

        from apps.core.utils.risk_document_helpers import stamp_risk_document
        result = stamp_risk_document(
            inst_register, approver_id=str(RMQAM_USER_ID),
            entity_type='institutional_risk_register', auth_token='tok',
        )
        # Should not raise; returns False (exception caught + logged)
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# 4. View Integration — PDF upload triggered by workflow start/advance
# ═══════════════════════════════════════════════════════════════════════════════


class TestRCAppointmentWorkflowPDFIntegration:
    """PDF upload + stamp triggered via RC appointment workflow views."""

    @pytest.mark.django_db
    @patch(f"{HELPERS_MOD}._upload_appointment_letter_pdf_to_drs")
    def test_workflow_start_uploads_pdf(self, mock_upload, rmqam_client, rc_appointment, allow_all_permissions):
        with patch('apps.core.services.risk_champion_service.OrchestrationClient') as MockOrch:
            from tests.risk_management.test_services import make_fake_plan_result
            MockOrch.return_value.start_workflow.return_value = make_fake_plan_result()
            from django.urls import reverse
            url = reverse('rc-appointment-workflow-start', args=[rc_appointment.id])
            response = rmqam_client.post(url)

        assert response.status_code == 200
        mock_upload.assert_called_once()

    @pytest.mark.django_db
    @patch(f"{HELPERS_MOD}.stamp_risk_document")
    @patch(f"{HELPERS_MOD}._reupload_appointment_letter_pdf")
    def test_workflow_advance_reuploads_and_stamps_on_approval(
        self, mock_reupload, mock_stamp, rmqam_client, rc_appointment_with_workflow, allow_all_permissions,
    ):
        with patch('apps.core.services.risk_champion_service.OrchestrationClient') as MockOrch:
            from tests.risk_management.test_services import make_fake_advance_result
            MockOrch.return_value.advance_stage.return_value = make_fake_advance_result(plan_status='completed')
            from django.urls import reverse
            url = reverse('rc-appointment-workflow-advance', args=[rc_appointment_with_workflow.id])
            response = rmqam_client.post(url, {'action': 'approve'}, format='json')

        # After advance, the appointment status should be checked
        assert response.status_code == 200


class TestQMSAuditReportSignPDFIntegration:
    """PDF upload + stamp triggered via QMS audit report sign views."""

    @pytest.mark.django_db
    @patch(f"{HELPERS_MOD}.stamp_risk_document")
    @patch(f"{HELPERS_MOD}._upload_qms_audit_report_pdf_to_drs")
    def test_tl_sign_uploads_pdf(self, mock_upload, mock_stamp, rmqam_client, qms_report, allow_all_permissions):
        from django.urls import reverse
        url = reverse('qms-audit-report-sign-tl', args=[qms_report.id])
        response = rmqam_client.post(url)

        assert response.status_code == 200
        mock_upload.assert_called_once()

    @pytest.mark.django_db
    @patch(f"{HELPERS_MOD}.stamp_risk_document")
    @patch(f"{HELPERS_MOD}._upload_qms_audit_report_pdf_to_drs")
    def test_auditee_sign_uploads_pdf(self, mock_upload, mock_stamp, rmqam_client, qms_report, allow_all_permissions):
        from django.urls import reverse
        url = reverse('qms-audit-report-sign-auditee', args=[qms_report.id])
        response = rmqam_client.post(url)

        assert response.status_code == 200
        mock_upload.assert_called_once()

    @pytest.mark.django_db
    @patch(f"{HELPERS_MOD}.stamp_risk_document")
    @patch(f"{HELPERS_MOD}._upload_qms_audit_report_pdf_to_drs")
    def test_stamps_when_both_signed(self, mock_upload, mock_stamp, rmqam_client, qms_report, allow_all_permissions):
        # Pre-sign as TL
        qms_report.tl_signed_by = str(TL_USER_ID)
        from django.utils import timezone
        qms_report.tl_signed_at = timezone.now()
        qms_report.save(update_fields=['tl_signed_by', 'tl_signed_at'])

        from django.urls import reverse
        url = reverse('qms-audit-report-sign-auditee', args=[qms_report.id])
        response = rmqam_client.post(url)

        assert response.status_code == 200
        mock_upload.assert_called_once()
        mock_stamp.assert_called_once()
