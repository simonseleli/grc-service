"""
Legal Module — RBAC / Permission tests.

Verifies that:
  - Unauthenticated requests → 401
  - Authenticated without grc_permissions → 403  (deny_all_permissions fixture)
  - Correct permission codes grant access (mocked specific codes)

Tests one representative endpoint per entity group to avoid redundancy.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse

from tests.legal.conftest import LEGAL_USER_ID


def _mock_permission(request, code):
    """Allow only specific legal permission codes."""
    allowed = {
        'grc:legal_meeting:view',
        'grc:legal_meeting:manage',
    }
    return code in allowed


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting permissions — representative group
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingPermissions:

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, meeting):
        url = reverse("legal-meeting-list-create")
        assert anon_client.get(url).status_code == 401

    @pytest.mark.django_db
    def test_no_permissions_returns_403(self, legal_user_client, meeting, deny_all_permissions):
        url = reverse("legal-meeting-list-create")
        assert legal_user_client.get(url).status_code == 403

    @pytest.mark.django_db
    def test_view_permission_allows_get(self, legal_user_client, meeting):
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_mock_permission,
        ):
            url = reverse("legal-meeting-list-create")
            response = legal_user_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_manage_permission_allows_create(
        self, legal_user_client, governing_body, meeting_mode, meeting_type,
    ):
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_mock_permission,
        ):
            url = reverse("legal-meeting-list-create")
            payload = {
                "governing_body_id": str(governing_body.id),
                "title": "Permission Test Meeting",
                "meeting_mode_id": str(meeting_mode.id),
                "meeting_type_id": str(meeting_type.id),
                "scheduled_start": "2026-06-01T09:00:00Z",
                "scheduled_end": "2026-06-01T12:00:00Z",
                "secretary_id": str(LEGAL_USER_ID),
            }
            response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════════
# Governing Body permissions
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoverningBodyPermissions:

    @pytest.mark.django_db
    def test_no_permissions_returns_403(
        self, legal_user_client, governing_body, deny_all_permissions,
    ):
        url = reverse("legal-governing-body-list-create")
        assert legal_user_client.get(url).status_code == 403

    @pytest.mark.django_db
    def test_no_permissions_detail_returns_403(
        self, legal_user_client, governing_body, deny_all_permissions,
    ):
        url = reverse("legal-governing-body-detail", args=[governing_body.id])
        assert legal_user_client.get(url).status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Case permissions
# ═══════════════════════════════════════════════════════════════════════════════

class TestCasePermissions:

    @pytest.mark.django_db
    def test_defendant_no_permissions_returns_403(
        self, legal_user_client, case_defendant, deny_all_permissions,
    ):
        url = reverse("legal-case-defendant-list-create")
        assert legal_user_client.get(url).status_code == 403

    @pytest.mark.django_db
    def test_plaintiff_no_permissions_returns_403(
        self, legal_user_client, case_plaintiff, deny_all_permissions,
    ):
        url = reverse("legal-case-plaintiff-list-create")
        assert legal_user_client.get(url).status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Notice permissions
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoticePermissions:

    @pytest.mark.django_db
    def test_no_permissions_returns_403(
        self, legal_user_client, legal_notice, deny_all_permissions,
    ):
        url = reverse("legal-notice-list-create")
        assert legal_user_client.get(url).status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Directive / Task permissions
# ═══════════════════════════════════════════════════════════════════════════════

class TestDirectivePermissions:

    @pytest.mark.django_db
    def test_meeting_directive_no_permissions_returns_403(
        self, legal_user_client, meeting_directive, deny_all_permissions,
    ):
        url = reverse("legal-directive-list-create")
        assert legal_user_client.get(url).status_code == 403

    @pytest.mark.django_db
    def test_task_no_permissions_returns_403(
        self, legal_user_client, task_litigation, deny_all_permissions,
    ):
        url = reverse("legal-task-list-create")
        assert legal_user_client.get(url).status_code == 403
