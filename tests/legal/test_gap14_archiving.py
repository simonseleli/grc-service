"""
GAP-14 — Archiving Logic tests.

Covers:
  - Model fields (is_archived, archived_at, archived_by)
  - Manual archive / unarchive endpoints
  - Default list exclusion of archived cases
  - Celery auto-archive task
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.core.models import CaseDefendant, CasePlaintiff


ARCHIVE_TASK_MODULE = "apps.core.tasks.legal_case_archiving"


# ═══════════════════════════════════════════════════════════════════════════════
# Model field tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestArchiveModelFields:

    @pytest.mark.django_db
    def test_defendant_defaults(self, case_defendant):
        assert case_defendant.is_archived is False
        assert case_defendant.archived_at is None
        assert case_defendant.archived_by is None

    @pytest.mark.django_db
    def test_plaintiff_defaults(self, case_plaintiff):
        assert case_plaintiff.is_archived is False
        assert case_plaintiff.archived_at is None
        assert case_plaintiff.archived_by is None

    @pytest.mark.django_db
    def test_can_set_archive_fields(self, case_defendant_closed):
        now = timezone.now()
        user_id = uuid.uuid4()
        case_defendant_closed.is_archived = True
        case_defendant_closed.archived_at = now
        case_defendant_closed.archived_by = user_id
        case_defendant_closed.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
        case_defendant_closed.refresh_from_db()
        assert case_defendant_closed.is_archived is True
        assert case_defendant_closed.archived_at is not None
        assert case_defendant_closed.archived_by == user_id


# ═══════════════════════════════════════════════════════════════════════════════
# Manual archive endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseArchiveEndpoint:

    @pytest.mark.django_db
    def test_archive_closed_defendant(
        self, legal_user_client, case_defendant_closed, allow_all_permissions,
    ):
        url = reverse(
            "legal-case-archive",
            kwargs={'side': 'defendant', 'pk': str(case_defendant_closed.pk)},
        )
        resp = legal_user_client.post(url)
        assert resp.status_code == 200
        assert resp.data['data']['is_archived'] is True
        case_defendant_closed.refresh_from_db()
        assert case_defendant_closed.is_archived is True
        assert case_defendant_closed.archived_at is not None

    @pytest.mark.django_db
    def test_archive_closed_plaintiff(
        self, legal_user_client, case_plaintiff_closed, allow_all_permissions,
    ):
        url = reverse(
            "legal-case-archive",
            kwargs={'side': 'plaintiff', 'pk': str(case_plaintiff_closed.pk)},
        )
        resp = legal_user_client.post(url)
        assert resp.status_code == 200
        assert resp.data['data']['is_archived'] is True

    @pytest.mark.django_db
    def test_archive_non_closed_fails(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        """Only closed cases can be archived."""
        url = reverse(
            "legal-case-archive",
            kwargs={'side': 'defendant', 'pk': str(case_defendant.pk)},
        )
        resp = legal_user_client.post(url)
        assert resp.status_code == 400
        assert 'NOT_CLOSED' in str(resp.data)

    @pytest.mark.django_db
    def test_archive_already_archived_fails(
        self, legal_user_client, case_defendant_closed, allow_all_permissions,
    ):
        case_defendant_closed.is_archived = True
        case_defendant_closed.archived_at = timezone.now()
        case_defendant_closed.save(update_fields=['is_archived', 'archived_at'])

        url = reverse(
            "legal-case-archive",
            kwargs={'side': 'defendant', 'pk': str(case_defendant_closed.pk)},
        )
        resp = legal_user_client.post(url)
        assert resp.status_code == 409

    @pytest.mark.django_db
    def test_archive_invalid_side(
        self, legal_user_client, allow_all_permissions,
    ):
        url = reverse(
            "legal-case-archive",
            kwargs={'side': 'invalid', 'pk': str(uuid.uuid4())},
        )
        resp = legal_user_client.post(url)
        assert resp.status_code == 400
        assert 'INVALID_SIDE' in str(resp.data)

    @pytest.mark.django_db
    def test_archive_requires_permission(
        self, legal_user_client, case_defendant_closed, deny_all_permissions,
    ):
        url = reverse(
            "legal-case-archive",
            kwargs={'side': 'defendant', 'pk': str(case_defendant_closed.pk)},
        )
        resp = legal_user_client.post(url)
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Manual unarchive endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseUnarchiveEndpoint:

    @pytest.mark.django_db
    def test_unarchive_defendant(
        self, legal_user_client, case_defendant_closed, allow_all_permissions,
    ):
        case_defendant_closed.is_archived = True
        case_defendant_closed.archived_at = timezone.now()
        case_defendant_closed.archived_by = uuid.uuid4()
        case_defendant_closed.save(update_fields=['is_archived', 'archived_at', 'archived_by'])

        url = reverse(
            "legal-case-unarchive",
            kwargs={'side': 'defendant', 'pk': str(case_defendant_closed.pk)},
        )
        resp = legal_user_client.post(url)
        assert resp.status_code == 200
        assert resp.data['data']['is_archived'] is False
        case_defendant_closed.refresh_from_db()
        assert case_defendant_closed.is_archived is False
        assert case_defendant_closed.archived_at is None
        assert case_defendant_closed.archived_by is None

    @pytest.mark.django_db
    def test_unarchive_not_archived_fails(
        self, legal_user_client, case_defendant_closed, allow_all_permissions,
    ):
        url = reverse(
            "legal-case-unarchive",
            kwargs={'side': 'defendant', 'pk': str(case_defendant_closed.pk)},
        )
        resp = legal_user_client.post(url)
        assert resp.status_code == 400
        assert 'NOT_ARCHIVED' in str(resp.data)


# ═══════════════════════════════════════════════════════════════════════════════
# List view exclusion tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestArchivedExcludedFromList:

    @pytest.mark.django_db
    def test_archived_defendant_excluded_from_list(
        self, legal_user_client, case_defendant, case_defendant_closed, allow_all_permissions,
    ):
        # Archive the closed case
        case_defendant_closed.is_archived = True
        case_defendant_closed.archived_at = timezone.now()
        case_defendant_closed.save(update_fields=['is_archived', 'archived_at'])

        url = reverse("legal-case-defendant-list-create")
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        ids = [item['id'] for item in resp.data['data']]
        assert str(case_defendant_closed.id) not in ids
        assert str(case_defendant.id) in ids

    @pytest.mark.django_db
    def test_include_archived_param(
        self, legal_user_client, case_defendant, case_defendant_closed, allow_all_permissions,
    ):
        case_defendant_closed.is_archived = True
        case_defendant_closed.archived_at = timezone.now()
        case_defendant_closed.save(update_fields=['is_archived', 'archived_at'])

        url = reverse("legal-case-defendant-list-create") + "?include_archived=true"
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        ids = [item['id'] for item in resp.data['data']]
        assert str(case_defendant_closed.id) in ids
        assert str(case_defendant.id) in ids

    @pytest.mark.django_db
    def test_archived_plaintiff_excluded_from_list(
        self, legal_user_client, case_plaintiff, case_plaintiff_closed, allow_all_permissions,
    ):
        case_plaintiff_closed.is_archived = True
        case_plaintiff_closed.archived_at = timezone.now()
        case_plaintiff_closed.save(update_fields=['is_archived', 'archived_at'])

        url = reverse("legal-case-plaintiff-list-create")
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        ids = [item['id'] for item in resp.data['data']]
        assert str(case_plaintiff_closed.id) not in ids
        assert str(case_plaintiff.id) in ids


# ═══════════════════════════════════════════════════════════════════════════════
# Celery auto-archive task tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestArchiveCeleryTask:

    @pytest.mark.django_db
    def test_archives_old_closed_cases(
        self, case_defendant_closed, case_plaintiff_closed,
    ):
        """Cases closed > 90 days ago should be auto-archived."""
        old_time = timezone.now() - timedelta(days=100)
        CaseDefendant.objects.filter(pk=case_defendant_closed.pk).update(updated_at=old_time)
        CasePlaintiff.objects.filter(pk=case_plaintiff_closed.pk).update(updated_at=old_time)

        from apps.core.tasks.legal_case_archiving import archive_closed_legal_cases
        result = archive_closed_legal_cases()

        assert result['archived'] == 2
        case_defendant_closed.refresh_from_db()
        case_plaintiff_closed.refresh_from_db()
        assert case_defendant_closed.is_archived is True
        assert case_plaintiff_closed.is_archived is True

    @pytest.mark.django_db
    def test_does_not_archive_recent_closed(
        self, case_defendant_closed,
    ):
        """Cases closed < 90 days ago should NOT be auto-archived."""
        from apps.core.tasks.legal_case_archiving import archive_closed_legal_cases
        result = archive_closed_legal_cases()

        assert result['archived'] == 0
        case_defendant_closed.refresh_from_db()
        assert case_defendant_closed.is_archived is False

    @pytest.mark.django_db
    def test_does_not_archive_non_closed(
        self, case_defendant,
    ):
        """Open cases should never be auto-archived."""
        old_time = timezone.now() - timedelta(days=100)
        CaseDefendant.objects.filter(pk=case_defendant.pk).update(updated_at=old_time)

        from apps.core.tasks.legal_case_archiving import archive_closed_legal_cases
        result = archive_closed_legal_cases()

        assert result['archived'] == 0
        case_defendant.refresh_from_db()
        assert case_defendant.is_archived is False

    @pytest.mark.django_db
    def test_skips_already_archived(
        self, case_defendant_closed,
    ):
        """Already-archived cases should not be counted again."""
        old_time = timezone.now() - timedelta(days=100)
        CaseDefendant.objects.filter(pk=case_defendant_closed.pk).update(
            updated_at=old_time, is_archived=True, archived_at=timezone.now(),
        )

        from apps.core.tasks.legal_case_archiving import archive_closed_legal_cases
        result = archive_closed_legal_cases()

        assert result['archived'] == 0

    @pytest.mark.django_db
    @patch('django.conf.settings.LEGAL_ARCHIVE_AFTER_DAYS', 30)
    def test_respects_configurable_threshold(
        self, case_defendant_closed,
    ):
        """Task should use LEGAL_ARCHIVE_AFTER_DAYS setting."""
        old_time = timezone.now() - timedelta(days=35)
        CaseDefendant.objects.filter(pk=case_defendant_closed.pk).update(updated_at=old_time)

        from apps.core.tasks.legal_case_archiving import archive_closed_legal_cases
        result = archive_closed_legal_cases()

        assert result['archived'] == 1
