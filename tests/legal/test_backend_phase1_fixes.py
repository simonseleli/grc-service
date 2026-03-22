"""
Legal Module — Backend Phase 1 Fix Tests

Covers:
  B1-1 (CRIT-01) — SubmissionForDetermination POST open to any authenticated user
  B1-2 (CRIT-05) — CasePlaintiff simplified intake bypasses CanManageLegalCase
  B1-3 (SIG-05)  — CaseDefendant/Plaintiff GET row-level filter for Legal Officers
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.core.models import CaseDefendant, CasePlaintiff, FinancialPlaintiff
from tests.legal.conftest import (
    LEGAL_USER_ID,
    LEGAL_OFFICER_ID,
    LEGAL_MANAGER_ID,
    OTHER_USER_ID,
    SYSTEM_USER_ID,
)

# ─── Shared permission mock helpers ─────────────────────────────────────────

def _only_view_case(request, code):
    """Allows grc:legal_case:view only — simulates Legal Officer (view-only)."""
    return code == 'grc:legal_case:view'


def _only_manage_case(request, code):
    """Allows grc:legal_case:manage only — simulates Legal Manager."""
    return code in ('grc:legal_case:view', 'grc:legal_case:manage')


def _only_view_governing_body(request, code):
    """Allows grc:legal_governing_body:view only."""
    return code == 'grc:legal_governing_body:view'


# ═══════════════════════════════════════════════════════════════════════════════
# B1-1 — SubmissionForDetermination POST: any authenticated user
# ═══════════════════════════════════════════════════════════════════════════════

class TestSubmissionCreateOpenAccess:
    """CRIT-01: POST /legal/submissions/ must succeed for any authenticated user."""

    @pytest.mark.django_db
    def test_unauthenticated_post_returns_401(self, anon_client, governing_body):
        url = reverse("legal-submission-list-create")
        payload = {
            "title": "Test Submission",
            "description": "desc",
            "submission_date": "2026-04-01",
            "target_body_id": str(governing_body.id),
        }
        assert anon_client.post(url, payload, format="json").status_code == 401

    @pytest.mark.django_db
    def test_authenticated_without_manage_permission_can_post(
        self, legal_user_client, governing_body, deny_all_permissions,
    ):
        """No GRC permissions at all — POST must succeed (201) not be blocked (403)."""
        url = reverse("legal-submission-list-create")
        payload = {
            "title": "Budget Submission",
            "description": "Annual budget for approval",
            "submitter_user_id": str(LEGAL_USER_ID),
            "submission_date": "2026-04-01",
            "target_body_id": str(governing_body.id),
        }
        response = legal_user_client.post(url, payload, format="json")
        # Permission gate removed; validation runs so 201 expected with valid payload.
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_authenticated_without_manage_permission_can_post_creates_submission(
        self, legal_user_client, governing_body, deny_all_permissions,
    ):
        """Created submission has submitter_user_id stored correctly."""
        from apps.core.models import SubmissionForDetermination
        url = reverse("legal-submission-list-create")
        payload = {
            "title": "User Submission",
            "description": "Requesting funds",
            "submitter_user_id": str(LEGAL_USER_ID),
            "submission_date": "2026-04-01",
            "target_body_id": str(governing_body.id),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == "User Submission"
        assert str(data["submitter_user_id"]) == str(LEGAL_USER_ID)

    @pytest.mark.django_db
    def test_get_without_permissions_still_returns_403(
        self, legal_user_client, submission, deny_all_permissions,
    ):
        """GET is still gated on view/manage permission."""
        url = reverse("legal-submission-list-create")
        assert legal_user_client.get(url).status_code == 403

    @pytest.mark.django_db
    def test_get_with_view_permission_returns_200(
        self, legal_user_client, submission,
    ):
        """GET still works with view permission."""
        url = reverse("legal-submission-list-create")
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_view_governing_body,
        ):
            response = legal_user_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# B1-2 — CasePlaintiff simplified intake bypasses CanManageLegalCase
# ═══════════════════════════════════════════════════════════════════════════════

class TestCasePlaintiffSimplifiedIntake:
    """CRIT-05: POST /legal/cases/plaintiff/ with registration_type=simplified
    must not be blocked by the CanManageLegalCase gate."""

    @pytest.mark.django_db
    def test_unauthenticated_post_returns_401(
        self, anon_client, court_level, urgency_level, risk_level,
    ):
        url = reverse("legal-case-plaintiff-list-create")
        payload = {
            "registration_type": "simplified",
            "respondent_name": "Test Corp",
            "court_level_id": str(court_level.id),
            "urgency_level_id": str(urgency_level.id),
            "risk_level_id": str(risk_level.id),
        }
        assert anon_client.post(url, payload, format="json").status_code == 401

    @pytest.mark.django_db
    def test_simplified_intake_without_manage_permission_is_not_403(
        self, legal_user_client, court_level, urgency_level, risk_level, deny_all_permissions,
    ):
        """Authenticated user without manage perm can post simplified intake."""
        url = reverse("legal-case-plaintiff-list-create")
        payload = {
            "registration_type": "simplified",
            "respondent_name": "Test Breach Corp",
            "court_level_id": str(court_level.id),
        }
        response = legal_user_client.post(url, payload, format="json")
        # Must NOT be 403 — validation may reject with 400, but permission gate is open.
        assert response.status_code != 403

    @pytest.mark.django_db
    def test_simplified_intake_with_valid_payload_creates_case(
        self, legal_user_client, court_level, urgency_level, risk_level, deny_all_permissions,
    ):
        """Valid simplified payload returns 201 and creates a CasePlaintiff."""
        url = reverse("legal-case-plaintiff-list-create")
        payload = {
            "registration_type": "simplified",
            "respondent_name": "Rapid Breach Report Corp",
            "court_level_id": str(court_level.id),
            "urgency_level_id": str(urgency_level.id),
            "risk_level_id": str(risk_level.id),
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["registration_type"] == "simplified"
        # Financial record auto-created
        case_id = data["id"]
        assert FinancialPlaintiff.objects.filter(case_plaintiff_id=case_id).exists()

    @pytest.mark.django_db
    def test_full_registration_without_manage_permission_returns_403(
        self, legal_user_client, court_level, urgency_level, risk_level, deny_all_permissions,
    ):
        """Full registration (default) still requires CanManageLegalCase."""
        url = reverse("legal-case-plaintiff-list-create")
        payload = {
            "registration_type": "full",
            "respondent_name": "Blocked Corp",
            "court_level_id": str(court_level.id),
            "urgency_level_id": str(urgency_level.id),
            "risk_level_id": str(risk_level.id),
        }
        assert legal_user_client.post(url, payload, format="json").status_code == 403

    @pytest.mark.django_db
    def test_post_without_registration_type_defaults_to_full_and_requires_permission(
        self, legal_user_client, court_level, urgency_level, risk_level, deny_all_permissions,
    ):
        """Omitting registration_type falls back to 'full' → 403 without manage perm."""
        url = reverse("legal-case-plaintiff-list-create")
        payload = {
            "respondent_name": "No Type Corp",
            "court_level_id": str(court_level.id),
        }
        assert legal_user_client.post(url, payload, format="json").status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# B1-3 — Row-level filtering: Legal Officers see only their assigned cases
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def case_defendant_assigned_to_officer(db, court_level, urgency_level, risk_level):
    """Defendant case with LEGAL_OFFICER_ID in assigned_legal_officer_ids."""
    return CaseDefendant.objects.create(
        reference_number='FCC/SUED/ROW/001',
        court_case_number='ROW-2026-001',
        court_level=court_level,
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='new',
        assigned_legal_officer_ids=[str(LEGAL_OFFICER_ID)],
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def case_defendant_not_assigned_to_officer(db, court_level, urgency_level, risk_level):
    """Defendant case with a different officer — not LEGAL_OFFICER_ID."""
    return CaseDefendant.objects.create(
        reference_number='FCC/SUED/ROW/002',
        court_case_number='ROW-2026-002',
        court_level=court_level,
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='new',
        assigned_legal_officer_ids=[str(OTHER_USER_ID)],
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def case_plaintiff_assigned_to_officer(db, court_level, urgency_level, risk_level):
    """Plaintiff case with LEGAL_OFFICER_ID in assigned_legal_officer_ids."""
    return CasePlaintiff.objects.create(
        reference_number='FCC/SUING/ROW/001',
        registration_type='full',
        respondent_name='Row Corp A',
        court_level=court_level,
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='new',
        assigned_legal_officer_ids=[str(LEGAL_OFFICER_ID)],
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def case_plaintiff_not_assigned_to_officer(db, court_level, urgency_level, risk_level):
    """Plaintiff case assigned to a different attorney — not LEGAL_OFFICER_ID."""
    return CasePlaintiff.objects.create(
        reference_number='FCC/SUING/ROW/002',
        registration_type='full',
        respondent_name='Row Corp B',
        court_level=court_level,
        urgency_level=urgency_level,
        risk_level=risk_level,
        status='new',
        assigned_legal_officer_ids=[str(OTHER_USER_ID)],
        created_by=SYSTEM_USER_ID,
    )


class TestCaseDefendantRowLevelFilter:
    """SIG-05: GET /legal/cases/defendant/ filters based on assignment for view-only users."""

    @pytest.mark.django_db
    def test_legal_officer_sees_only_assigned_cases(
        self,
        legal_officer_client,
        case_defendant_assigned_to_officer,
        case_defendant_not_assigned_to_officer,
    ):
        """Legal Officer (view perm only) must see only the case assigned to them."""
        url = reverse("legal-case-defendant-list-create")
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_view_case,
        ):
            response = legal_officer_client.get(url)
        assert response.status_code == 200
        body = response.json()
        # paginated_list_response puts items directly in body["data"] (a list)
        ids_returned = [item["id"] for item in body["data"]]
        assert str(case_defendant_assigned_to_officer.id) in ids_returned
        assert str(case_defendant_not_assigned_to_officer.id) not in ids_returned

    @pytest.mark.django_db
    def test_legal_manager_sees_all_cases(
        self,
        legal_officer_client,
        case_defendant_assigned_to_officer,
        case_defendant_not_assigned_to_officer,
    ):
        """Legal Manager (manage perm) sees all cases regardless of assignment."""
        url = reverse("legal-case-defendant-list-create")
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_manage_case,
        ):
            response = legal_officer_client.get(url)
        assert response.status_code == 200
        body = response.json()
        ids_returned = [item["id"] for item in body["data"]]
        assert str(case_defendant_assigned_to_officer.id) in ids_returned
        assert str(case_defendant_not_assigned_to_officer.id) in ids_returned

    @pytest.mark.django_db
    def test_legal_officer_sees_zero_cases_when_none_assigned(
        self,
        legal_officer_client,
        case_defendant_not_assigned_to_officer,
    ):
        """Legal Officer with no assigned cases sees empty list, not all cases."""
        url = reverse("legal-case-defendant-list-create")
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_view_case,
        ):
            response = legal_officer_client.get(url)
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] == 0


class TestCasePlaintiffRowLevelFilter:
    """SIG-05: GET /legal/cases/plaintiff/ filters based on assignment for view-only users."""

    @pytest.mark.django_db
    def test_legal_officer_sees_only_assigned_cases(
        self,
        legal_officer_client,
        case_plaintiff_assigned_to_officer,
        case_plaintiff_not_assigned_to_officer,
    ):
        """Legal Officer (view perm only) must see only the case assigned to them."""
        url = reverse("legal-case-plaintiff-list-create")
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_view_case,
        ):
            response = legal_officer_client.get(url)
        assert response.status_code == 200
        body = response.json()
        ids_returned = [item["id"] for item in body["data"]]
        assert str(case_plaintiff_assigned_to_officer.id) in ids_returned
        assert str(case_plaintiff_not_assigned_to_officer.id) not in ids_returned

    @pytest.mark.django_db
    def test_legal_manager_sees_all_cases(
        self,
        legal_officer_client,
        case_plaintiff_assigned_to_officer,
        case_plaintiff_not_assigned_to_officer,
    ):
        """Legal Manager (manage perm) sees all cases."""
        url = reverse("legal-case-plaintiff-list-create")
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_manage_case,
        ):
            response = legal_officer_client.get(url)
        assert response.status_code == 200
        body = response.json()
        ids_returned = [item["id"] for item in body["data"]]
        assert str(case_plaintiff_assigned_to_officer.id) in ids_returned
        assert str(case_plaintiff_not_assigned_to_officer.id) in ids_returned

    @pytest.mark.django_db
    def test_legal_officer_sees_zero_cases_when_none_assigned(
        self,
        legal_officer_client,
        case_plaintiff_not_assigned_to_officer,
    ):
        """Legal Officer with no assigned cases sees empty list."""
        url = reverse("legal-case-plaintiff-list-create")
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_view_case,
        ):
            response = legal_officer_client.get(url)
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] == 0
