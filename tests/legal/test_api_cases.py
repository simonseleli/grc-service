"""
Legal Module — API endpoint tests for Litigation Case entities.

Covers:
  - CaseDefendant (list, create, detail, update)
  - CasePlaintiff (list, create, detail, update)
  - Case workflow endpoints (submit, status, history, action, cancel)
  - Hearing (list, create, detail)
  - HearingReport (list, create, detail)
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse

from tests.legal.conftest import LEGAL_OFFICER_ID, LEGAL_MANAGER_ID

CASE_VIEW_MODULE = "apps.api.views.legal_case_views"


# ═══════════════════════════════════════════════════════════════════════════════
# CaseDefendant CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseDefendantListCreateAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-defendant-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, court_level, urgency_level, risk_level,
        allow_all_permissions,
    ):
        url = reverse("legal-case-defendant-list-create")
        payload = {
            "court_case_number": "CIVIL-2026-999",
            "court_level_id": str(court_level.id),
            "claim_amount": "10000000.00",
            "nature_of_claim": "Negligence",
            "urgency_level_id": str(urgency_level.id),
            "risk_level_id": str(risk_level.id),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_auto_creates_financial_record(
        self, legal_user_client, court_level, urgency_level, risk_level,
        allow_all_permissions,
    ):
        from apps.core.models import FinancialDefendant
        url = reverse("legal-case-defendant-list-create")
        payload = {
            "court_case_number": "CIVIL-2026-FIN-001",
            "court_level_id": str(court_level.id),
            "claim_amount": "5000000.00",
            "nature_of_claim": "Contract breach",
            "urgency_level_id": str(urgency_level.id),
            "risk_level_id": str(risk_level.id),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        case_id = response.json()["data"]["id"]
        assert FinancialDefendant.objects.filter(case_defendant_id=case_id).exists()

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        url = reverse("legal-case-defendant-list-create")
        response = anon_client.get(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_permission_denied_returns_403(self, legal_user_client, deny_all_permissions):
        url = reverse("legal-case-defendant-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 403


class TestCaseDefendantDetailAPI:

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-defendant-detail", args=[case_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert "FCC/SUED/2026/001" in response.json()["data"]["reference_number"]

    @pytest.mark.django_db
    def test_update_returns_200(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-defendant-detail", args=[case_defendant.id])
        response = legal_user_client.patch(
            url, {"nature_of_claim": "Updated claim"}, format="json",
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_nonexistent_returns_404(self, legal_user_client, allow_all_permissions):
        url = reverse("legal-case-defendant-detail", args=[uuid.uuid4()])
        response = legal_user_client.get(url)
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# CasePlaintiff CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestCasePlaintiffListCreateAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, case_plaintiff, allow_all_permissions,
    ):
        url = reverse("legal-case-plaintiff-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, court_level, urgency_level, risk_level,
        allow_all_permissions,
    ):
        url = reverse("legal-case-plaintiff-list-create")
        payload = {
            "registration_type": "full",
            "respondent_name": "Test Corp",
            "court_level_id": str(court_level.id),
            "estimated_claim_amount": "50000000.00",
            "urgency_level_id": str(urgency_level.id),
            "risk_level_id": str(risk_level.id),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_create_auto_creates_financial_record(
        self, legal_user_client, court_level, urgency_level, risk_level,
        allow_all_permissions,
    ):
        from apps.core.models import FinancialPlaintiff
        url = reverse("legal-case-plaintiff-list-create")
        payload = {
            "registration_type": "full",
            "respondent_name": "Corp Ltd",
            "court_level_id": str(court_level.id),
            "estimated_claim_amount": "20000000.00",
            "urgency_level_id": str(urgency_level.id),
            "risk_level_id": str(risk_level.id),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        case_id = response.json()["data"]["id"]
        assert FinancialPlaintiff.objects.filter(case_plaintiff_id=case_id).exists()


# ═══════════════════════════════════════════════════════════════════════════════
# Case Defendant Workflow API
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseDefendantWorkflowAPI:

    @pytest.mark.django_db
    def test_submit_returns_200(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        with patch(f"{CASE_VIEW_MODULE}.LegalCaseService") as MockService:
            case_defendant.workflow_plan_id = uuid.uuid4()
            MockService.return_value.submit_for_approval.return_value = case_defendant
            url = reverse("legal-case-defendant-submit", args=[case_defendant.id])
            response = legal_user_client.post(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_workflow_status_returns_200(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        with patch(f"{CASE_VIEW_MODULE}.LegalCaseService") as MockService:
            MockService.return_value.get_workflow_status.return_value = None
            url = reverse("legal-case-defendant-workflow-status", args=[case_defendant.id])
            response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_workflow_history_returns_200(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        with patch(f"{CASE_VIEW_MODULE}.LegalCaseService") as MockService:
            MockService.return_value.get_workflow_history.return_value = []
            url = reverse("legal-case-defendant-workflow-history", args=[case_defendant.id])
            response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_workflow_action_returns_200(
        self, legal_user_client, case_defendant_active, allow_all_permissions,
    ):
        action_result = {
            "action": "approve",
            "new_stage_status": "completed",
            "plan_status": "active",
            "next_stage": "dg_closure_noting",
            "next_stage_id": str(uuid.uuid4()),
        }
        with patch(f"{CASE_VIEW_MODULE}.LegalCaseService") as MockService:
            MockService.return_value.advance_workflow_stage.return_value = action_result
            url = reverse("legal-case-defendant-workflow-action", args=[case_defendant_active.id])
            response = legal_user_client.post(url, {"action": "approve"}, format="json")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_cancel_workflow_returns_200(
        self, legal_user_client, case_defendant_active, allow_all_permissions,
    ):
        with patch(f"{CASE_VIEW_MODULE}.LegalCaseService") as MockService:
            MockService.return_value.cancel_workflow_plan.return_value = case_defendant_active
            url = reverse("legal-case-defendant-cancel-workflow", args=[case_defendant_active.id])
            response = legal_user_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Case Plaintiff Workflow API
# ═══════════════════════════════════════════════════════════════════════════════

class TestCasePlaintiffWorkflowAPI:

    @pytest.mark.django_db
    def test_submit_returns_200(
        self, legal_user_client, case_plaintiff, allow_all_permissions,
    ):
        with patch(f"{CASE_VIEW_MODULE}.LegalCaseService") as MockService:
            case_plaintiff.workflow_plan_id = uuid.uuid4()
            MockService.return_value.submit_for_approval.return_value = case_plaintiff
            url = reverse("legal-case-plaintiff-submit", args=[case_plaintiff.id])
            response = legal_user_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Hearing / HearingReport
# ═══════════════════════════════════════════════════════════════════════════════

class TestHearingAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, hearing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-hearing-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse("legal-hearing-list-create")
        payload = {
            "case_defendant": str(case_defendant.id),
            "hearing_date": "2026-07-01",
            "court": "High Court Dodoma",
            "status": "scheduled",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, hearing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-hearing-detail", args=[hearing_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200


class TestHearingReportAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, hearing_defendant, hearing_report, allow_all_permissions,
    ):
        url = reverse("legal-hearing-report-list", args=[hearing_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, hearing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-hearing-report-list", args=[hearing_defendant.id])
        payload = {
            "hearing": str(hearing_defendant.id),
            "report_type": "ruling",
            "summary": "Court ruled in favor of defendant",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_create_propagates_next_hearing_date_to_case(
        self, legal_user_client, hearing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-hearing-report-list", args=[hearing_defendant.id])
        payload = {
            "hearing": str(hearing_defendant.id),
            "report_type": "proceedings",
            "summary": "Adjourned to next date",
            "next_hearing_date": "2026-09-01",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        hearing_defendant.case_defendant.refresh_from_db()
        assert str(hearing_defendant.case_defendant.next_hearing_date) == "2026-09-01"

    @pytest.mark.django_db
    def test_create_without_next_hearing_date_does_not_update_case(
        self, legal_user_client, hearing_defendant, allow_all_permissions,
    ):
        original = hearing_defendant.case_defendant.next_hearing_date
        url = reverse("legal-hearing-report-list", args=[hearing_defendant.id])
        payload = {
            "hearing": str(hearing_defendant.id),
            "report_type": "order",
            "summary": "Order issued",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        hearing_defendant.case_defendant.refresh_from_db()
        assert hearing_defendant.case_defendant.next_hearing_date == original
