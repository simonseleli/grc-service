"""
GAP-13 — Activity Log API Endpoint tests.

Tests the LegalActivityLogView read-only paginated timeline endpoint.
"""

import uuid

import pytest
from django.urls import reverse

from apps.core.models import LegalAuditLog


SYSTEM_USER_ID = uuid.UUID("77777777-7777-7777-7777-777777777777")
ACTOR_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def audit_logs(db, case_defendant):
    """Create several audit log entries for a case_defendant."""
    logs = []
    for i, action in enumerate(['created', 'submitted', 'approved']):
        logs.append(LegalAuditLog.objects.create(
            entity_type='case_defendant',
            entity_id=case_defendant.id,
            action=action,
            actor_id=ACTOR_ID,
            previous_status='new' if i > 0 else '',
            new_status=action,
            stage_name=f'stage_{i}',
            comment=f'Action {action} performed',
            metadata={'step': i},
        ))
    return logs


class TestLegalActivityLog:

    @pytest.mark.django_db
    def test_returns_logs_for_entity(
        self, legal_user_client, case_defendant, audit_logs, allow_all_permissions,
    ):
        url = reverse(
            "legal-activity-log",
            kwargs={
                'entity_type': 'case_defendant',
                'entity_id': str(case_defendant.id),
            },
        )
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert resp.data['meta']['total'] == 3
        # Reverse chronological
        actions = [item['action'] for item in resp.data['data']]
        assert actions == ['approved', 'submitted', 'created']

    @pytest.mark.django_db
    def test_returns_empty_for_no_logs(
        self, legal_user_client, case_defendant, allow_all_permissions,
    ):
        url = reverse(
            "legal-activity-log",
            kwargs={
                'entity_type': 'case_defendant',
                'entity_id': str(case_defendant.id),
            },
        )
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert resp.data['meta']['total'] == 0
        assert resp.data['data'] == []

    @pytest.mark.django_db
    def test_does_not_leak_other_entities(
        self, legal_user_client, case_defendant, case_plaintiff,
        audit_logs, allow_all_permissions,
    ):
        # Create a log for a different entity
        LegalAuditLog.objects.create(
            entity_type='case_plaintiff',
            entity_id=case_plaintiff.id,
            action='created',
            actor_id=ACTOR_ID,
        )
        url = reverse(
            "legal-activity-log",
            kwargs={
                'entity_type': 'case_defendant',
                'entity_id': str(case_defendant.id),
            },
        )
        resp = legal_user_client.get(url)
        assert resp.data['meta']['total'] == 3  # only case_defendant logs

    @pytest.mark.django_db
    def test_invalid_entity_type_returns_400(
        self, legal_user_client, allow_all_permissions,
    ):
        url = reverse(
            "legal-activity-log",
            kwargs={
                'entity_type': 'invalid_type',
                'entity_id': str(uuid.uuid4()),
            },
        )
        resp = legal_user_client.get(url)
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_serializer_fields_present(
        self, legal_user_client, case_defendant, audit_logs, allow_all_permissions,
    ):
        url = reverse(
            "legal-activity-log",
            kwargs={
                'entity_type': 'case_defendant',
                'entity_id': str(case_defendant.id),
            },
        )
        resp = legal_user_client.get(url)
        entry = resp.data['data'][0]
        for field in [
            'id', 'entity_type', 'entity_id', 'action', 'actor_id',
            'previous_status', 'new_status', 'stage_name',
            'comment', 'metadata', 'created_at',
        ]:
            assert field in entry, f"Missing field: {field}"

    @pytest.mark.django_db
    def test_requires_authentication(self, anon_client):
        url = reverse(
            "legal-activity-log",
            kwargs={
                'entity_type': 'case_defendant',
                'entity_id': str(uuid.uuid4()),
            },
        )
        resp = anon_client.get(url)
        assert resp.status_code in (401, 403)

    @pytest.mark.django_db
    def test_requires_permission(
        self, legal_user_client, deny_all_permissions,
    ):
        url = reverse(
            "legal-activity-log",
            kwargs={
                'entity_type': 'case_defendant',
                'entity_id': str(uuid.uuid4()),
            },
        )
        resp = legal_user_client.get(url)
        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_works_for_plaintiff_entity(
        self, legal_user_client, case_plaintiff, allow_all_permissions,
    ):
        LegalAuditLog.objects.create(
            entity_type='case_plaintiff',
            entity_id=case_plaintiff.id,
            action='created',
            actor_id=ACTOR_ID,
        )
        url = reverse(
            "legal-activity-log",
            kwargs={
                'entity_type': 'case_plaintiff',
                'entity_id': str(case_plaintiff.id),
            },
        )
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert resp.data['meta']['total'] == 1
