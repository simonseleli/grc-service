"""
GAP-12 — Dashboard KPIs Views tests.

Tests the defendant and plaintiff dashboard aggregate endpoints.
"""

import datetime
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.core.models import (
    CaseDefendant, CasePlaintiff,
    JudgmentDefendant, JudgmentPlaintiff,
    FinancialPlaintiff,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Defendant Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalDashboardDefendant:

    URL = "legal-dashboard-defendant"

    @pytest.mark.django_db
    def test_returns_all_kpis(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        data = resp.data["data"]
        assert "total_cases" in data
        assert "won_loss_ratio" in data
        assert "cases_on_appeal" in data
        assert "high_risk_cases" in data
        assert "active_cases" in data
        assert "pending_dg_review" in data

    @pytest.mark.django_db
    def test_total_cases_count(
        self, legal_user_client, case_defendant, case_defendant_active,
        case_defendant_closed, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        assert data["total_cases"] == 3

    @pytest.mark.django_db
    def test_active_cases_excludes_closed_and_on_hold(
        self, legal_user_client, case_defendant, case_defendant_active,
        case_defendant_closed, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        # case_defendant (new) + case_defendant_active (hearing_stage) = 2
        # case_defendant_closed (closed) excluded
        assert data["active_cases"] == 2

    @pytest.mark.django_db
    def test_high_risk_cases(
        self, legal_user_client, risk_level_high, court_level, urgency_level,
        allow_all_permissions,
    ):
        CaseDefendant.objects.create(
            reference_number='FCC/SUED/2026/HR1',
            court_level=court_level,
            urgency_level=urgency_level,
            risk_level=risk_level_high,
            status='new',
            created_by=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        )
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        assert data["high_risk_cases"] >= 1

    @pytest.mark.django_db
    def test_won_loss_ratio(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        # judgment_defendant fixture has outcome='lost'
        assert data["won_loss_ratio"] == "0:100"

    @pytest.mark.django_db
    def test_won_loss_ratio_no_judgments(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        assert data["won_loss_ratio"] == "0:0"

    @pytest.mark.django_db
    def test_pending_dg_review(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        # case_defendant has dg_review_status='pending' by default
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        assert data["pending_dg_review"] >= 1

    @pytest.mark.django_db
    def test_requires_authentication(self, anon_client):
        url = reverse(self.URL)
        resp = anon_client.get(url)
        assert resp.status_code in (401, 403)

    @pytest.mark.django_db
    def test_requires_permission(
        self, legal_user_client, deny_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Plaintiff Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalDashboardPlaintiff:

    URL = "legal-dashboard-plaintiff"

    @pytest.mark.django_db
    def test_returns_all_kpis(
        self, legal_user_client, case_plaintiff, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        data = resp.data["data"]
        assert "total_cases" in data
        assert "won_loss_ratio" in data
        assert "cases_on_appeal" in data
        assert "high_risk_cases" in data
        assert "active_cases" in data
        assert "pending_dg_review" in data
        assert "recoverable_amount" in data
        assert "recovered_amount" in data

    @pytest.mark.django_db
    def test_total_cases_count(
        self, legal_user_client, case_plaintiff, case_plaintiff_active,
        allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        assert data["total_cases"] == 2

    @pytest.mark.django_db
    def test_active_cases_excludes_closed(
        self, legal_user_client, case_plaintiff, case_plaintiff_active,
        allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        # both are active (new + hearing_stage)
        assert data["active_cases"] == 2

    @pytest.mark.django_db
    def test_won_loss_ratio(
        self, legal_user_client, judgment_plaintiff, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        # judgment_plaintiff fixture has outcome='won'
        assert data["won_loss_ratio"] == "100:0"

    @pytest.mark.django_db
    def test_recoverable_and_recovered_amounts(
        self, legal_user_client, financial_plaintiff, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        assert Decimal(data["recoverable_amount"]) == Decimal("75000000.00")
        assert Decimal(data["recovered_amount"]) == Decimal("12000000.00")

    @pytest.mark.django_db
    def test_zero_financials_when_none(
        self, legal_user_client, case_plaintiff, allow_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        data = resp.data["data"]
        assert Decimal(data["recoverable_amount"]) == Decimal("0.00")
        assert Decimal(data["recovered_amount"]) == Decimal("0.00")

    @pytest.mark.django_db
    def test_requires_authentication(self, anon_client):
        url = reverse(self.URL)
        resp = anon_client.get(url)
        assert resp.status_code in (401, 403)

    @pytest.mark.django_db
    def test_requires_permission(
        self, legal_user_client, deny_all_permissions,
    ):
        url = reverse(self.URL)
        resp = legal_user_client.get(url)
        assert resp.status_code == 403
