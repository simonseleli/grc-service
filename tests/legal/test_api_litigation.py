"""
Legal Module — API endpoint tests for Litigation sub-entities.

Covers:
  - FilingDefendant/Plaintiff (CRUD + workflow)
  - SettlementDefendant/Plaintiff (CRUD + workflow)
  - JudgmentDefendant/Plaintiff (CRUD + workflow)
  - AppealDefendant/Plaintiff (list + detail)
  - MeetingDirective (CRUD + overdue)
  - LitigationDirective (CRUD)
  - TaskLitigation (CRUD + overdue)
  - LegalNotice (CRUD)
"""

import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse

FILING_VIEW_MODULE = "apps.api.views.legal_filing_views"
SETTLEMENT_VIEW_MODULE = "apps.api.views.legal_settlement_views"
JUDGMENT_VIEW_MODULE = "apps.api.views.legal_judgment_views"


# ═══════════════════════════════════════════════════════════════════════════════
# Filing — Defendant
# ═══════════════════════════════════════════════════════════════════════════════

class TestFilingDefendantAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, filing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-filing-defendant-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse("legal-filing-defendant-list-create")
        payload = {
            "case_defendant": str(case_defendant.id),
            "filing_type": "affidavit",
            "title": "Witness Statement 1",
            "document_id": str(uuid.uuid4()),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, filing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-filing-defendant-detail", args=[filing_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_submit_returns_200(
        self, legal_user_client, filing_defendant, allow_all_permissions,
    ):
        with patch(f"{FILING_VIEW_MODULE}.LegalFilingService") as MockService:
            filing_defendant.workflow_plan_id = uuid.uuid4()
            MockService.return_value.submit_for_approval.return_value = filing_defendant
            url = reverse("legal-filing-defendant-submit", args=[filing_defendant.id])
            response = legal_user_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Filing — Plaintiff
# ═══════════════════════════════════════════════════════════════════════════════

class TestFilingPlaintiffAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, filing_plaintiff, allow_all_permissions,
    ):
        url = reverse("legal-filing-plaintiff-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, filing_plaintiff, allow_all_permissions,
    ):
        url = reverse("legal-filing-plaintiff-detail", args=[filing_plaintiff.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Settlement — Defendant
# ═══════════════════════════════════════════════════════════════════════════════

class TestSettlementDefendantAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, settlement_defendant, allow_all_permissions,
    ):
        url = reverse("legal-settlement-defendant-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, settlement_defendant, allow_all_permissions,
    ):
        url = reverse("legal-settlement-defendant-detail", args=[settlement_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_submit_returns_200(
        self, legal_user_client, settlement_defendant, allow_all_permissions,
    ):
        with patch(f"{SETTLEMENT_VIEW_MODULE}.LegalSettlementService") as MockService:
            settlement_defendant.workflow_plan_id = uuid.uuid4()
            MockService.return_value.submit_for_approval.return_value = settlement_defendant
            url = reverse("legal-settlement-defendant-submit", args=[settlement_defendant.id])
            response = legal_user_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Settlement — Plaintiff
# ═══════════════════════════════════════════════════════════════════════════════

class TestSettlementPlaintiffAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, settlement_plaintiff, allow_all_permissions,
    ):
        url = reverse("legal-settlement-plaintiff-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Judgment — Defendant
# ═══════════════════════════════════════════════════════════════════════════════

class TestJudgmentDefendantAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        url = reverse("legal-judgment-defendant-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        url = reverse("legal-judgment-defendant-detail", args=[judgment_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_submit_returns_200(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        with patch(f"{JUDGMENT_VIEW_MODULE}.LegalJudgmentService") as MockService:
            judgment_defendant.workflow_plan_id = uuid.uuid4()
            MockService.return_value.submit_for_approval.return_value = judgment_defendant
            url = reverse("legal-judgment-defendant-submit", args=[judgment_defendant.id])
            response = legal_user_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Judgment — Plaintiff
# ═══════════════════════════════════════════════════════════════════════════════

class TestJudgmentPlaintiffAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, judgment_plaintiff, allow_all_permissions,
    ):
        url = reverse("legal-judgment-plaintiff-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Appeal — Defendant / Plaintiff
# ═══════════════════════════════════════════════════════════════════════════════

class TestAppealDefendantAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, appeal_defendant, allow_all_permissions,
    ):
        url = reverse("legal-appeal-defendant-list")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, appeal_defendant, allow_all_permissions,
    ):
        url = reverse("legal-appeal-defendant-detail", args=[appeal_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200


class TestAppealPlaintiffAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, appeal_plaintiff, allow_all_permissions,
    ):
        url = reverse("legal-appeal-plaintiff-list")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, appeal_plaintiff, allow_all_permissions,
    ):
        url = reverse("legal-appeal-plaintiff-detail", args=[appeal_plaintiff.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# DG Decision — Defendant / Plaintiff
# ═══════════════════════════════════════════════════════════════════════════════

class TestDGDecisionDefendantAPI:

    @pytest.mark.django_db
    def test_appeal_decision_returns_200(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        with patch(f"{JUDGMENT_VIEW_MODULE}.LegalJudgmentService") as MockService:
            judgment_defendant.dg_decision = "appeal"
            MockService.return_value.process_appeal_decision.return_value = judgment_defendant
            url = reverse("legal-judgment-defendant-dg-decision", args=[judgment_defendant.id])
            response = legal_user_client.post(url, {"decision": "appeal"}, format="json")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_invalid_decision_returns_400(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        url = reverse("legal-judgment-defendant-dg-decision", args=[judgment_defendant.id])
        response = legal_user_client.post(url, {"decision": "invalid"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_missing_decision_returns_400(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        url = reverse("legal-judgment-defendant-dg-decision", args=[judgment_defendant.id])
        response = legal_user_client.post(url, {}, format="json")
        assert response.status_code == 400


class TestDGDecisionPlaintiffAPI:

    @pytest.mark.django_db
    def test_accept_decision_returns_200(
        self, legal_user_client, judgment_plaintiff, allow_all_permissions,
    ):
        with patch(f"{JUDGMENT_VIEW_MODULE}.LegalJudgmentService") as MockService:
            judgment_plaintiff.dg_decision = "accept"
            MockService.return_value.process_appeal_decision.return_value = judgment_plaintiff
            url = reverse("legal-judgment-plaintiff-dg-decision", args=[judgment_plaintiff.id])
            response = legal_user_client.post(url, {"decision": "accept"}, format="json")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# MeetingDirective
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingDirectiveAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, meeting_directive, allow_all_permissions,
    ):
        url = reverse("legal-directive-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, meeting_directive, allow_all_permissions,
    ):
        url = reverse("legal-directive-detail", args=[meeting_directive.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_overdue_list_returns_200(
        self, legal_user_client, meeting_directive_overdue, allow_all_permissions,
    ):
        url = reverse("legal-directive-overdue")
        response = legal_user_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# LitigationDirective
# ═══════════════════════════════════════════════════════════════════════════════

class TestLitigationDirectiveAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, litigation_directive, allow_all_permissions,
    ):
        url = reverse("legal-litigation-directive-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, litigation_directive, allow_all_permissions,
    ):
        url = reverse("legal-litigation-directive-detail", args=[litigation_directive.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TaskLitigation
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskLitigationAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, task_litigation, allow_all_permissions,
    ):
        url = reverse("legal-task-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, task_litigation, allow_all_permissions,
    ):
        url = reverse("legal-task-detail", args=[task_litigation.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_overdue_list_returns_200(
        self, legal_user_client, task_litigation_overdue, allow_all_permissions,
    ):
        url = reverse("legal-task-overdue")
        response = legal_user_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# LegalNotice
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalNoticeAPI:

    @pytest.mark.django_db
    def test_list_returns_200(
        self, legal_user_client, legal_notice, allow_all_permissions,
    ):
        url = reverse("legal-notice-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_create_returns_201(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse("legal-notice-list-create")
        payload = {
            "related_case_defendant": str(case_defendant.id),
            "notice_type": "statutory_notice",
            "title": "Statutory Notice",
            "content": "Notice content here.",
            "issued_date": "2026-04-01",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_detail_returns_200(
        self, legal_user_client, legal_notice, allow_all_permissions,
    ):
        url = reverse("legal-notice-detail", args=[legal_notice.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        url = reverse("legal-notice-list-create")
        response = anon_client.get(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_permission_denied_returns_403(self, legal_user_client, deny_all_permissions):
        url = reverse("legal-notice-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 403
