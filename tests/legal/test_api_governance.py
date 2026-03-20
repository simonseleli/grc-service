"""
Legal Module — API endpoint tests for Governance entities.

Covers CRUD + response shape for:
  - CommitteeType (list only)
  - GoverningBody (list, create, detail, update, delete)
  - Member (list, create, detail, update, delete)
  - SubmissionForDetermination (list, create, detail)
"""

import pytest
from django.urls import reverse

from tests.legal.conftest import LEGAL_USER_ID, SYSTEM_USER_ID, SECRETARY_ID


# ═══════════════════════════════════════════════════════════════════════════════
# CommitteeType — list only, no GRC permission required
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommitteeTypeListAPI:

    @pytest.mark.django_db
    def test_list_returns_200(self, legal_user_client, committee_type):
        url = reverse("legal-committee-type-list")
        response = legal_user_client.get(url)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert len(body["data"]) >= 1

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, committee_type):
        url = reverse("legal-committee-type-list")
        response = anon_client.get(url)
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GoverningBody — CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoverningBodyListCreateAPI:

    @pytest.mark.django_db
    def test_list_returns_200(self, legal_user_client, governing_body, allow_all_permissions):
        url = reverse("legal-governing-body-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True

    @pytest.mark.django_db
    def test_create_returns_201(self, legal_user_client, committee_type, allow_all_permissions):
        url = reverse("legal-governing-body-list-create")
        payload = {
            "committee_type_id": str(committee_type.id),
            "name": "Audit Committee",
            "description": "Oversees audit operations",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["name"] == "Audit Committee"

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        url = reverse("legal-governing-body-list-create")
        response = anon_client.get(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_permission_denied_returns_403(self, legal_user_client, deny_all_permissions):
        url = reverse("legal-governing-body-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 403


class TestGoverningBodyDetailAPI:

    @pytest.mark.django_db
    def test_detail_returns_200(self, legal_user_client, governing_body, allow_all_permissions):
        url = reverse("legal-governing-body-detail", args=[governing_body.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["name"] == "Finance Committee"

    @pytest.mark.django_db
    def test_update_returns_200(self, legal_user_client, governing_body, allow_all_permissions):
        url = reverse("legal-governing-body-detail", args=[governing_body.id])
        response = legal_user_client.patch(url, {"name": "Updated Name"}, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Name"

    @pytest.mark.django_db
    def test_delete_returns_200(self, legal_user_client, governing_body, allow_all_permissions):
        url = reverse("legal-governing-body-detail", args=[governing_body.id])
        response = legal_user_client.delete(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_nonexistent_returns_404(self, legal_user_client, allow_all_permissions):
        import uuid
        url = reverse("legal-governing-body-detail", args=[uuid.uuid4()])
        response = legal_user_client.get(url)
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Member — CRUD nested under governing body
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemberListCreateAPI:

    @pytest.mark.django_db
    def test_list_returns_200(self, legal_user_client, governing_body, member, allow_all_permissions):
        url = reverse("legal-governing-body-member-list", args=[governing_body.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True

    @pytest.mark.django_db
    def test_create_returns_201(self, legal_user_client, governing_body, allow_all_permissions):
        import uuid
        url = reverse("legal-governing-body-member-list", args=[governing_body.id])
        payload = {
            "governing_body_id": str(governing_body.id),
            "user_id": str(uuid.uuid4()),
            "position": "chairman",
            "member_type": "committee_member",
            "email": "chairperson@test.org",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        body = response.json()
        assert body["success"] is True


class TestMemberDetailAPI:

    @pytest.mark.django_db
    def test_detail_returns_200(self, legal_user_client, member, allow_all_permissions):
        url = reverse("legal-member-detail", args=[member.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_update_returns_200(self, legal_user_client, member, allow_all_permissions):
        url = reverse("legal-member-detail", args=[member.id])
        response = legal_user_client.patch(url, {"position": "secretary"}, format="json")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_returns_200(self, legal_user_client, member, allow_all_permissions):
        url = reverse("legal-member-detail", args=[member.id])
        response = legal_user_client.delete(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# SubmissionForDetermination — CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestSubmissionListCreateAPI:

    @pytest.mark.django_db
    def test_list_returns_200(self, legal_user_client, submission, allow_all_permissions):
        url = reverse("legal-submission-list-create")
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_returns_201(self, legal_user_client, governing_body, allow_all_permissions):
        url = reverse("legal-submission-list-create")
        payload = {
            "title": "New Submission",
            "description": "Testing submission creation",
            "submitter_user_id": str(LEGAL_USER_ID),
            "target_body_id": str(governing_body.id),
            "submission_date": "2026-04-01",
        }
        response = legal_user_client.post(url, payload, format="json")
        assert response.status_code == 201


class TestSubmissionDetailAPI:

    @pytest.mark.django_db
    def test_detail_returns_200(self, legal_user_client, submission, allow_all_permissions):
        url = reverse("legal-submission-detail", args=[submission.id])
        response = legal_user_client.get(url)
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Budget Approval Request"
