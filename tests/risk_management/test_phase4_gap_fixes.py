"""
Phase 4 Gap Fix Tests — Backend Gap Support Analysis, Phase 4

Covers:
  - GAP-20: RiskDashboardExportView  (GET /risk/dashboard/export/)
  - GAP-20: QPRExportView            (GET /risk/quarterly-reports/:id/export/)
  - generate_risk_dashboard_pdf()    (unit test of PDF generator)
"""
import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse

from tests.risk_management.conftest import (
    RMQAM_USER_ID, RC_USER_ID, SYSTEM_USER_ID,
)

RENDER = "django.template.loader.render_to_string"
WEASY_HTML = "weasyprint.HTML"


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-20 — Risk Dashboard PDF Export
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskDashboardExportView:
    """GET /risk/dashboard/export/ → application/pdf download."""

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>dashboard</html>")
    def test_dashboard_export_returns_pdf(
        self, mock_render, mock_html, allow_all_permissions, rmqam_client
    ):
        mock_html.return_value.write_pdf.return_value = b"%PDF-dash"
        url = reverse("risk-dashboard-export")
        response = rmqam_client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert b"%PDF-dash" in response.content

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>dashboard</html>")
    def test_dashboard_export_content_disposition(
        self, mock_render, mock_html, allow_all_permissions, rmqam_client
    ):
        mock_html.return_value.write_pdf.return_value = b"%PDF-dash"
        url = reverse("risk-dashboard-export")
        response = rmqam_client.get(url)
        assert "attachment" in response["Content-Disposition"]
        assert "risk_dashboard" in response["Content-Disposition"]

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>dashboard</html>")
    def test_dashboard_export_with_fiscal_year_param(
        self, mock_render, mock_html,
        allow_all_permissions, rmqam_client, fiscal_year,
    ):
        mock_html.return_value.write_pdf.return_value = b"%PDF-fy"
        url = reverse("risk-dashboard-export")
        response = rmqam_client.get(url, {"fiscal_year": str(fiscal_year.id)})
        assert response.status_code == 200
        assert str(fiscal_year.id) in response["Content-Disposition"]

    @pytest.mark.django_db
    def test_dashboard_export_requires_auth(self, anon_client):
        url = reverse("risk-dashboard-export")
        response = anon_client.get(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_dashboard_export_permission_denied(
        self, deny_all_permissions, rmqam_client
    ):
        url = reverse("risk-dashboard-export")
        response = rmqam_client.get(url)
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-20 — QPR PDF Export
# ═══════════════════════════════════════════════════════════════════════════════

class TestQPRExportView:
    """GET /risk/quarterly-reports/:id/export/ → application/pdf download."""

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>qpr</html>")
    def test_qpr_export_returns_pdf(
        self, mock_render, mock_html,
        allow_all_permissions, rmqam_client, quarterly_report,
    ):
        mock_html.return_value.write_pdf.return_value = b"%PDF-qpr"
        url = reverse("quarterly-report-export", args=[quarterly_report.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert b"%PDF-qpr" in response.content

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>qpr</html>")
    def test_qpr_export_content_disposition_includes_id(
        self, mock_render, mock_html,
        allow_all_permissions, rmqam_client, quarterly_report,
    ):
        mock_html.return_value.write_pdf.return_value = b"%PDF-qpr"
        url = reverse("quarterly-report-export", args=[quarterly_report.id])
        response = rmqam_client.get(url)
        assert "attachment" in response["Content-Disposition"]
        assert str(quarterly_report.id) in response["Content-Disposition"]

    @pytest.mark.django_db
    def test_qpr_export_404_for_unknown_id(
        self, allow_all_permissions, rmqam_client
    ):
        url = reverse("quarterly-report-export", args=[uuid.uuid4()])
        response = rmqam_client.get(url)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_qpr_export_requires_auth(self, anon_client, quarterly_report):
        url = reverse("quarterly-report-export", args=[quarterly_report.id])
        response = anon_client.get(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_qpr_export_permission_denied(
        self, deny_all_permissions, rmqam_client, quarterly_report
    ):
        url = reverse("quarterly-report-export", args=[quarterly_report.id])
        response = rmqam_client.get(url)
        assert response.status_code == 403

    @pytest.mark.django_db
    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>qpr</html>")
    def test_qpr_export_inactive_report_returns_404(
        self, mock_render, mock_html,
        allow_all_permissions, rmqam_client, quarterly_report,
    ):
        quarterly_report.is_active = False
        quarterly_report.save()
        url = reverse("quarterly-report-export", args=[quarterly_report.id])
        response = rmqam_client.get(url)
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-20 — generate_risk_dashboard_pdf() unit test
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateRiskDashboardPDF:
    """Unit tests for generate_risk_dashboard_pdf() without DB."""

    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>dash</html>")
    def test_returns_pdf_bytes(self, mock_render, mock_html):
        mock_html.return_value.write_pdf.return_value = b"%PDF-1.4"
        from apps.core.utils.pdf_generators import generate_risk_dashboard_pdf
        data = {
            "assessments": {"total": 5},
            "dept_registers": {"draft": 2, "approved": 1},
            "inst_registers": {},
            "rtaps": {},
            "non_conformances": {},
        }
        result = generate_risk_dashboard_pdf(data)
        assert result == b"%PDF-1.4"

    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>dash</html>")
    def test_passes_data_and_fiscal_year_in_context(self, mock_render, mock_html):
        mock_html.return_value.write_pdf.return_value = b"%PDF-ctx"
        from apps.core.utils.pdf_generators import generate_risk_dashboard_pdf

        mock_fy = object()
        data = {"assessments": {"total": 0}}
        generate_risk_dashboard_pdf(data, fiscal_year=mock_fy)

        call_kwargs = mock_render.call_args
        context = call_kwargs[0][1] if call_kwargs[0] else call_kwargs[1].get('context', call_kwargs[0][1])
        # render_to_string called with (template, context)
        rendered_context = mock_render.call_args[0][1]
        assert rendered_context['fiscal_year'] is mock_fy
        assert rendered_context['data'] is data

    @patch(WEASY_HTML)
    @patch(RENDER, return_value="<html>no-fy</html>")
    def test_works_without_fiscal_year(self, mock_render, mock_html):
        mock_html.return_value.write_pdf.return_value = b"%PDF-no-fy"
        from apps.core.utils.pdf_generators import generate_risk_dashboard_pdf
        result = generate_risk_dashboard_pdf({"assessments": {"total": 0}})
        assert result == b"%PDF-no-fy"
