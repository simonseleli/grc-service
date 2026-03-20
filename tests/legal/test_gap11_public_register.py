"""
GAP-11 — Public Register Views & URLs tests.

Tests the PublicDecision CRUD endpoints (authenticated) and the
PublicRegister read-only endpoint (unauthenticated).
"""

import datetime
import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.core.models import PublicDecision


# ═══════════════════════════════════════════════════════════════════════════════
# Authenticated — PublicDecision CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicDecisionListCreate:

    @pytest.mark.django_db
    def test_list_returns_decisions(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        url = reverse("legal-public-decision-list-create")
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert resp.data['meta']['total'] >= 1

    @pytest.mark.django_db
    def test_list_filters_by_status(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        url = reverse("legal-public-decision-list-create")
        resp = legal_user_client.get(url, {'status': 'draft'})
        assert resp.status_code == 200
        titles = [item['title'] for item in resp.data['data']]
        assert public_decision.title in titles

    @pytest.mark.django_db
    def test_create_public_decision(
        self, legal_user_client, meeting_closed, allow_all_permissions,
    ):
        url = reverse("legal-public-decision-list-create")
        payload = {
            'title': 'New Regulation Decision',
            'meeting': str(meeting_closed.id),
            'body_text': 'After deliberation...',
            'decision_text': 'Resolved to approve.',
            'decision_date': '2026-03-15',
        }
        resp = legal_user_client.post(url, payload, format='json')
        assert resp.status_code == 201
        data = resp.data['data']
        assert data['title'] == 'New Regulation Decision'
        assert data['status'] == 'draft'
        assert data['published_date'] is None

    @pytest.mark.django_db
    def test_create_without_meeting(
        self, legal_user_client, allow_all_permissions,
    ):
        url = reverse("legal-public-decision-list-create")
        payload = {
            'title': 'Standalone Decision',
            'body_text': 'No meeting.',
            'decision_text': 'Approved independently.',
            'decision_date': '2026-03-15',
        }
        resp = legal_user_client.post(url, payload, format='json')
        assert resp.status_code == 201

    @pytest.mark.django_db
    def test_list_requires_authentication(self, anon_client):
        url = reverse("legal-public-decision-list-create")
        resp = anon_client.get(url)
        assert resp.status_code in (401, 403)


class TestPublicDecisionDetail:

    @pytest.mark.django_db
    def test_get_detail(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        url = reverse("legal-public-decision-detail", args=[public_decision.id])
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert resp.data['data']['title'] == public_decision.title

    @pytest.mark.django_db
    def test_patch_draft_decision(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        url = reverse("legal-public-decision-detail", args=[public_decision.id])
        resp = legal_user_client.patch(
            url, {'title': 'Updated Title'}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['data']['title'] == 'Updated Title'

    @pytest.mark.django_db
    def test_patch_published_decision_blocked(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        public_decision.status = 'published'
        public_decision.save(update_fields=['status'])

        url = reverse("legal-public-decision-detail", args=[public_decision.id])
        resp = legal_user_client.patch(
            url, {'title': 'Should Fail'}, format='json',
        )
        assert resp.status_code == 400
        assert 'DECISION_PUBLISHED' in str(resp.data)

    @pytest.mark.django_db
    def test_delete_draft_deactivates(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        url = reverse("legal-public-decision-detail", args=[public_decision.id])
        resp = legal_user_client.delete(url)
        assert resp.status_code == 200
        public_decision.refresh_from_db()
        assert public_decision.is_active is False

    @pytest.mark.django_db
    def test_delete_published_blocked(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        public_decision.status = 'published'
        public_decision.save(update_fields=['status'])

        url = reverse("legal-public-decision-detail", args=[public_decision.id])
        resp = legal_user_client.delete(url)
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# Publish endpoint
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicDecisionPublish:

    @pytest.mark.django_db
    def test_publish_draft(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        url = reverse("legal-public-decision-publish", args=[public_decision.id])
        resp = legal_user_client.post(url)
        assert resp.status_code == 200
        data = resp.data['data']
        assert data['status'] == 'published'
        assert data['published_date'] is not None

    @pytest.mark.django_db
    def test_publish_already_published(
        self, legal_user_client, public_decision, allow_all_permissions,
    ):
        public_decision.status = 'published'
        public_decision.save(update_fields=['status'])

        url = reverse("legal-public-decision-publish", args=[public_decision.id])
        resp = legal_user_client.post(url)
        assert resp.status_code == 400
        assert 'ALREADY_PUBLISHED' in str(resp.data)

    @pytest.mark.django_db
    def test_publish_requires_authentication(self, anon_client, public_decision):
        url = reverse("legal-public-decision-publish", args=[public_decision.id])
        resp = anon_client.post(url)
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# Public Register — unauthenticated read-only
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicRegister:

    @pytest.mark.django_db
    def test_public_register_no_auth_required(self, anon_client, public_decision):
        """Draft decisions are NOT visible on public register."""
        url = reverse("legal-public-register")
        resp = anon_client.get(url)
        assert resp.status_code == 200
        # public_decision has status='draft' — must not appear
        assert resp.data['meta']['total'] == 0

    @pytest.mark.django_db
    def test_public_register_shows_published_only(self, anon_client, public_decision):
        """Published decisions appear on the public register."""
        public_decision.status = 'published'
        public_decision.save(update_fields=['status'])

        url = reverse("legal-public-register")
        resp = anon_client.get(url)
        assert resp.status_code == 200
        assert resp.data['meta']['total'] == 1
        assert resp.data['data'][0]['title'] == public_decision.title

    @pytest.mark.django_db
    def test_public_register_search(self, anon_client, public_decision):
        """Search filters by title and decision_text."""
        public_decision.status = 'published'
        public_decision.save(update_fields=['status'])

        url = reverse("legal-public-register")
        resp = anon_client.get(url, {'search': 'Budget'})
        assert resp.status_code == 200
        assert resp.data['meta']['total'] == 1

        resp = anon_client.get(url, {'search': 'nonexistent12345'})
        assert resp.status_code == 200
        assert resp.data['meta']['total'] == 0

    @pytest.mark.django_db
    def test_public_register_excludes_inactive(self, anon_client, public_decision):
        """Deactivated published decisions are excluded."""
        public_decision.status = 'published'
        public_decision.is_active = False
        public_decision.save(update_fields=['status', 'is_active'])

        url = reverse("legal-public-register")
        resp = anon_client.get(url)
        assert resp.status_code == 200
        assert resp.data['meta']['total'] == 0

    @pytest.mark.django_db
    def test_public_register_pagination(self, anon_client, meeting_closed):
        """Public register supports pagination."""
        from apps.core.models import PublicDecision as PD
        for i in range(5):
            PD.objects.create(
                title=f'Decision {i}',
                meeting=meeting_closed,
                body_text='Content',
                decision_text='Resolved',
                decision_date=datetime.date(2026, 1, i + 1),
                status='published',
                created_by=uuid.uuid4(),
            )

        url = reverse("legal-public-register")
        resp = anon_client.get(url, {'page': 1, 'page_size': 2})
        assert resp.status_code == 200
        assert len(resp.data['data']) == 2
        assert resp.data['meta']['total'] == 5
