"""
Backend Phase 2 — New Permission Codes (CRIT-02 / B2-1)

Tests:
  TestRegistryOfficerPermissionClass   — CanRegisterLegalCase wiring
  TestCaseDefendantRegisterAccess      — POST /legal/cases/defendant/ accepts :register
  TestCasePlaintiffRegisterAccess      — POST /legal/cases/plaintiff/ (full) accepts :register
"""
import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.permissions_jwt import CanRegisterLegalCase

# ── Shared UUIDs ──────────────────────────────────────────────────────────────
REGISTRY_OFFICER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
LEGAL_USER_ID       = uuid.UUID("11111111-1111-1111-1111-111111111111")

from tests.legal.conftest import (
    LEGAL_OFFICER_ID,
    make_mock_user,
)


# ── Permission side-effects ───────────────────────────────────────────────────

def _only_register_case(request, code):
    """Grant only grc:legal_case:register."""
    return code == 'grc:legal_case:register'


def _register_and_view_case(request, code):
    """Grant grc:legal_case:register + grc:legal_case:view."""
    return code in ('grc:legal_case:register', 'grc:legal_case:view')


def _only_view_case(request, code):
    """Grant only grc:legal_case:view (no manage, no register)."""
    return code == 'grc:legal_case:view'


def _no_permissions(request, code):
    return False


# ── Client fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def registry_officer_client():
    client = APIClient()
    client.force_authenticate(user=make_mock_user(REGISTRY_OFFICER_ID))
    return client


@pytest.fixture
def legal_user_client():
    client = APIClient()
    client.force_authenticate(user=make_mock_user(LEGAL_USER_ID))
    return client


@pytest.fixture
def anon_client():
    return APIClient()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CanRegisterLegalCase permission class unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistryOfficerPermissionClass:
    """Verify the CanRegisterLegalCase class checks the correct permission code."""

    def test_unauthenticated_denied(self):
        from unittest.mock import MagicMock
        permission = CanRegisterLegalCase()
        request = MagicMock()
        request.user = None
        assert permission.has_permission(request, None) is False

    def test_unauthenticated_user_denied(self):
        from unittest.mock import MagicMock
        permission = CanRegisterLegalCase()
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = False
        assert permission.has_permission(request, None) is False

    def test_checks_register_code(self):
        """When _check_grc_permission_locally approves 'grc:legal_case:register', returns True."""
        from unittest.mock import MagicMock
        permission = CanRegisterLegalCase()
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = True
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_register_case,
        ):
            assert permission.has_permission(request, None) is True

    def test_rejects_wrong_code(self):
        """When only 'grc:legal_case:view' is granted, CanRegisterLegalCase returns False."""
        from unittest.mock import MagicMock
        permission = CanRegisterLegalCase()
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = True
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_view_case,
        ):
            assert permission.has_permission(request, None) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 2. POST /legal/cases/defendant/ — Registry Officer access
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseDefendantRegisterAccess:
    """
    POST /legal/cases/defendant/ must be accessible with grc:legal_case:register
    in addition to the existing grc:legal_case:manage requirement.
    """

    @pytest.mark.django_db
    def test_unauthenticated_post_returns_401(self, anon_client):
        url = reverse('legal-case-defendant-list-create')
        response = anon_client.post(url, {}, format='json')
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_no_permissions_returns_403(self, registry_officer_client):
        """No permissions at all → 403."""
        url = reverse('legal-case-defendant-list-create')
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_no_permissions,
        ):
            response = registry_officer_client.post(url, {'title': 'x'}, format='json')
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_register_permission_allows_post(
        self, registry_officer_client,
        court_level, urgency_level, risk_level,
    ):
        """grc:legal_case:register alone is sufficient to reach the POST path (not 403)."""
        url = reverse('legal-case-defendant-list-create')
        payload = {
            'case_title': 'Test Registry Case',
            'plaintiff_name': 'John Doe',
            'court_level_id': str(court_level.id),
            'urgency_level_id': str(urgency_level.id),
            'risk_level_id': str(risk_level.id),
            'claim_amount': '500000.00',
            'currency': 'TZS',
            'filing_date': '2026-01-15',
        }
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_register_case,
        ):
            response = registry_officer_client.post(url, payload, format='json')
        # 201 = created; 400 = validation error (still past the permission gate)
        # Either is acceptable — permission gate was not triggered (not 403)
        assert response.status_code in (201, 400)

    @pytest.mark.django_db
    def test_manage_permission_still_allows_post(
        self, registry_officer_client,
        court_level, urgency_level, risk_level,
    ):
        """grc:legal_case:manage still allows POST (no regression)."""
        url = reverse('legal-case-defendant-list-create')
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            return_value=True,  # all permissions granted
        ):
            response = registry_officer_client.post(url, {}, format='json')
        # Permission gate cleared; payload is empty so 400 expected (not 403)
        assert response.status_code != 403


# ═══════════════════════════════════════════════════════════════════════════════
# 3. POST /legal/cases/plaintiff/ (full) — Registry Officer access
# ═══════════════════════════════════════════════════════════════════════════════

class TestCasePlaintiffRegisterAccess:
    """
    POST /legal/cases/plaintiff/ with registration_type='full' must accept
    grc:legal_case:register (in addition to grc:legal_case:manage).
    Simplified intake is open to all authenticated users (already tested in Phase 1).
    """

    @pytest.mark.django_db
    def test_unauthenticated_post_returns_401(self, anon_client):
        url = reverse('legal-case-plaintiff-list-create')
        response = anon_client.post(url, {}, format='json')
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_full_registration_no_permissions_returns_403(self, registry_officer_client):
        """Full registration with no permissions → 403."""
        url = reverse('legal-case-plaintiff-list-create')
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_no_permissions,
        ):
            response = registry_officer_client.post(
                url, {'registration_type': 'full'}, format='json',
            )
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_full_registration_with_register_permission_not_403(
        self, registry_officer_client,
    ):
        """grc:legal_case:register is sufficient for full registration POST (gets past 403)."""
        url = reverse('legal-case-plaintiff-list-create')
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_only_register_case,
        ):
            response = registry_officer_client.post(
                url, {'registration_type': 'full', 'case_title': 'Breach'}, format='json',
            )
        # Reaches validation — not a permission error
        assert response.status_code in (201, 400)

    @pytest.mark.django_db
    def test_simplified_intake_still_open_to_any_authenticated_user(
        self, legal_user_client,
    ):
        """Simplified intake requires no special permission (B1-2 regression check)."""
        url = reverse('legal-case-plaintiff-list-create')
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_no_permissions,
        ):
            response = legal_user_client.post(
                url, {'registration_type': 'simplified', 'case_title': 'x'}, format='json',
            )
        # Reaches validation (not 403)
        assert response.status_code in (201, 400)

    @pytest.mark.django_db
    def test_full_registration_manage_permission_still_works(self, legal_user_client):
        """grc:legal_case:manage still allows full plaintiff case registration (no regression)."""
        url = reverse('legal-case-plaintiff-list-create')
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            return_value=True,
        ):
            response = legal_user_client.post(
                url, {'registration_type': 'full'}, format='json',
            )
        assert response.status_code != 403
