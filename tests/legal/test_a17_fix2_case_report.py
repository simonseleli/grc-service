"""
A17-Fix-2 — CaseReportView tests
GET /api/v1/grc/legal/cases/<str:side>/<uuid:pk>/report/

SRS §4.13: Chronological timeline of all case milestone events.
Aggregates from: Hearing, Filing, Settlement, Judgment, Appeal, LitigationDirective.
"""
import datetime
import uuid
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.models import (
    CaseDefendant, CasePlaintiff,
    Hearing, FilingDefendant, FilingPlaintiff,
    SettlementDefendant, SettlementPlaintiff,
    JudgmentDefendant, JudgmentPlaintiff,
    AppealDefendant, AppealPlaintiff,
    LitigationDirective,
)
from tests.legal.conftest import (
    LEGAL_USER_ID, LEGAL_OFFICER_ID, LEGAL_MANAGER_ID,
    SYSTEM_USER_ID, DOCUMENT_UUID,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: extract event types from response
# ═══════════════════════════════════════════════════════════════════════════════

def _event_types(response):
    return [e["event_type"] for e in response.json()["data"]["events"]]


def _events(response):
    return response.json()["data"]["events"]


# ═══════════════════════════════════════════════════════════════════════════════
# Basic structure & empty case
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseReportStructure:

    @pytest.mark.django_db
    def test_returns_200(self, legal_user_client, case_defendant, allow_all_permissions):
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_response_envelope(self, legal_user_client, case_defendant, allow_all_permissions):
        """Response must include case_id, case_type, reference_number, events list."""
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        data = response.json()["data"]
        assert data["case_id"] == str(case_defendant.id)
        assert data["case_type"] == "defendant"
        assert data["reference_number"] == case_defendant.reference_number
        assert isinstance(data["events"], list)

    @pytest.mark.django_db
    def test_fresh_case_has_case_registered_event(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        """Every case must always have at least a 'case_registered' event."""
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        assert "case_registered" in _event_types(response)

    @pytest.mark.django_db
    def test_plaintiff_side_returns_200(
        self, legal_user_client, case_plaintiff, allow_all_permissions,
    ):
        url = reverse("legal-case-report", args=["plaintiff", case_plaintiff.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["case_type"] == "plaintiff"
        assert data["case_id"] == str(case_plaintiff.id)


# ═══════════════════════════════════════════════════════════════════════════════
# Each event type is included
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseReportEventTypes:

    @pytest.mark.django_db
    def test_hearing_held_event_included(
        self, legal_user_client, case_defendant, hearing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        assert "hearing_held" in _event_types(response)

    @pytest.mark.django_db
    def test_filing_submitted_event_included(
        self, legal_user_client, case_defendant, filing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        assert "filing_submitted" in _event_types(response)

    @pytest.mark.django_db
    def test_settlement_recorded_event_included(
        self, legal_user_client, case_defendant_active, settlement_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-report", args=["defendant", case_defendant_active.id])
        response = legal_user_client.get(url)
        assert "settlement_recorded" in _event_types(response)

    @pytest.mark.django_db
    def test_judgment_recorded_event_included(
        self, legal_user_client, case_defendant_active, judgment_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-report", args=["defendant", case_defendant_active.id])
        response = legal_user_client.get(url)
        assert "judgment_recorded" in _event_types(response)

    @pytest.mark.django_db
    def test_appeal_filed_event_included(
        self, legal_user_client, case_defendant_active, appeal_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-report", args=["defendant", case_defendant_active.id])
        response = legal_user_client.get(url)
        assert "appeal_filed" in _event_types(response)

    @pytest.mark.django_db
    def test_directive_issued_event_included(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        LitigationDirective.objects.create(
            case_defendant=case_defendant,
            issued_by_user_id=LEGAL_MANAGER_ID,
            issue_date=datetime.date(2026, 3, 1),
            instruction='Issue directive for test',
            due_date=datetime.date(2026, 4, 1),
            status='open',
            created_by=SYSTEM_USER_ID,
        )
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        assert "directive_issued" in _event_types(response)

    @pytest.mark.django_db
    def test_case_closed_event_included_for_closed_case(
        self, legal_user_client, case_defendant_closed, allow_all_permissions,
    ):
        """'case_closed' event only appears when case.status == 'closed'."""
        url = reverse("legal-case-report", args=["defendant", case_defendant_closed.id])
        response = legal_user_client.get(url)
        assert "case_closed" in _event_types(response)

    @pytest.mark.django_db
    def test_case_closed_not_included_for_active_case(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        """'case_closed' must NOT appear when case is still active (status != 'closed')."""
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        assert "case_closed" not in _event_types(response)


# ═══════════════════════════════════════════════════════════════════════════════
# Plaintiff-side events mirror defendant
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseReportPlaintiffEvents:

    @pytest.fixture
    def case_plaintiff_with_events(
        self, db, court_level, urgency_level, risk_level,
    ):
        case = CasePlaintiff.objects.create(
            reference_number='FCC/SUING/2026/RPT01',
            registration_type='full',
            respondent_name='Test Respondent',
            court_level=court_level,
            estimated_claim_amount=Decimal('40000000.00'),
            urgency_level=urgency_level,
            risk_level=risk_level,
            status='hearing_stage',
            created_by=SYSTEM_USER_ID,
        )
        Hearing.objects.create(
            case_plaintiff=case, case_defendant=None,
            hearing_date=datetime.date(2026, 4, 10),
            status='completed',
            created_by=SYSTEM_USER_ID,
        )
        FilingPlaintiff.objects.create(
            case_plaintiff=case,
            filing_type='plaint',
            title='Plaint Filing',
            document_id=DOCUMENT_UUID,
            status='filed',
            created_by=SYSTEM_USER_ID,
        )
        LitigationDirective.objects.create(
            case_plaintiff=case,
            issued_by_user_id=LEGAL_MANAGER_ID,
            issue_date=datetime.date(2026, 3, 5),
            instruction='Plaintiff directive instruction',
            due_date=datetime.date(2026, 5, 1),
            status='in_progress',
            created_by=SYSTEM_USER_ID,
        )
        return case

    @pytest.mark.django_db
    def test_plaintiff_report_contains_all_expected_event_types(
        self, legal_user_client, case_plaintiff_with_events, allow_all_permissions,
    ):
        url = reverse("legal-case-report", args=["plaintiff", case_plaintiff_with_events.id])
        response = legal_user_client.get(url)
        types = _event_types(response)
        assert "case_registered" in types
        assert "hearing_held" in types
        assert "filing_submitted" in types
        assert "directive_issued" in types


# ═══════════════════════════════════════════════════════════════════════════════
# Chronological ordering
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseReportChronologicalOrder:

    @pytest.mark.django_db
    def test_events_sorted_by_timestamp_ascending(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        # Create events with explicit dates spanning 2025-2026
        Hearing.objects.create(
            case_defendant=case_defendant, case_plaintiff=None,
            hearing_date=datetime.date(2026, 5, 20),
            status='completed',
            created_by=SYSTEM_USER_ID,
        )
        FilingDefendant.objects.create(
            case_defendant=case_defendant,
            filing_type='affidavit',
            title='Affidavit Filing',
            document_id=DOCUMENT_UUID,
            status='filed',
            created_by=SYSTEM_USER_ID,
        )
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        events = _events(response)
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps), "Events are not in chronological order"

    @pytest.mark.django_db
    def test_first_event_is_case_registered(
        self, legal_user_client, case_defendant, hearing_defendant, allow_all_permissions,
    ):
        """case_registered must always be the first event (oldest timestamp = case.created_at)."""
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        events = _events(response)
        assert events[0]["event_type"] == "case_registered"


# ═══════════════════════════════════════════════════════════════════════════════
# Event shape validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseReportEventShape:

    @pytest.mark.django_db
    def test_each_event_has_required_fields(
        self, legal_user_client, case_defendant, hearing_defendant, allow_all_permissions,
    ):
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        for event in _events(response):
            assert "id" in event, f"Missing 'id' in event: {event}"
            assert "event_type" in event, f"Missing 'event_type' in event: {event}"
            assert "title" in event, f"Missing 'title' in event: {event}"
            assert "detail" in event, f"Missing 'detail' in event: {event}"
            assert "timestamp" in event, f"Missing 'timestamp' in event: {event}"

    @pytest.mark.django_db
    def test_hearing_detail_contains_court_info(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        Hearing.objects.create(
            case_defendant=case_defendant, case_plaintiff=None,
            hearing_date=datetime.date(2026, 6, 10),
            court='High Court Dodoma',
            status='completed',
            created_by=SYSTEM_USER_ID,
        )
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        hearing_events = [e for e in _events(response) if e["event_type"] == "hearing_held"]
        assert len(hearing_events) == 1
        assert "High Court Dodoma" in hearing_events[0]["detail"]

    @pytest.mark.django_db
    def test_directive_detail_contains_instruction_text(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        LitigationDirective.objects.create(
            case_defendant=case_defendant,
            issued_by_user_id=LEGAL_MANAGER_ID,
            issue_date=datetime.date(2026, 3, 1),
            instruction='Prepare all court documents by end of month',
            due_date=datetime.date(2026, 4, 1),
            status='open',
            created_by=SYSTEM_USER_ID,
        )
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        directive_events = [e for e in _events(response) if e["event_type"] == "directive_issued"]
        assert len(directive_events) == 1
        assert "Prepare all court documents" in directive_events[0]["detail"]


# ═══════════════════════════════════════════════════════════════════════════════
# Auth / permission / error guards
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseReportGuards:

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, case_defendant):
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = anon_client.get(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_insufficient_permission_returns_403(
        self, legal_user_client, case_defendant, deny_all_permissions,
    ):
        url = reverse("legal-case-report", args=["defendant", case_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_invalid_side_returns_400(self, legal_user_client, case_defendant, allow_all_permissions):
        url = reverse("legal-case-report", args=["invalid_side", case_defendant.id])
        response = legal_user_client.get(url)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_SIDE"

    @pytest.mark.django_db
    def test_nonexistent_case_returns_404(self, legal_user_client, allow_all_permissions):
        url = reverse("legal-case-report", args=["defendant", uuid.uuid4()])
        response = legal_user_client.get(url)
        assert response.status_code == 404
