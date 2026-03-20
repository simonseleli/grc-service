"""
GAP-10 — Digital Signature Engine tests.

Tests the shared stamp utility and its integration into
Filing, Judgment, and Settlement workflow-action views.
"""

import uuid
from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings

from apps.core.models import (
    FilingDefendant, FilingPlaintiff,
    JudgmentDefendant, JudgmentPlaintiff,
    SettlementDefendant, SettlementPlaintiff,
)
from apps.core.utils.legal_document_stamp import stamp_legal_document

FILING_VIEW_MODULE = "apps.api.views.legal_filing_views"
SETTLEMENT_VIEW_MODULE = "apps.api.views.legal_settlement_views"
JUDGMENT_VIEW_MODULE = "apps.api.views.legal_judgment_views"

STAMP_MODULE = "apps.core.utils.legal_document_stamp"
STAMP_FN = f"{STAMP_MODULE}.stamp_legal_document"
DRS_CLIENT = "apps.infrastructure.external.document_service_client.DocumentServiceClient"

FAKE_STAMPED_URL = "http://document-records-service:8002/api/v1/documents/abcd-1234/download/"
PUBLIC_STAMPED_URL = "http://localhost:8080/api/v1/documents/abcd-1234/download/"


# ═══════════════════════════════════════════════════════════════════════════════
# stamp_legal_document() unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestStampLegalDocument:

    @pytest.mark.django_db
    @override_settings(
        DOCUMENT_SERVICE_URL="http://document-records-service:8002",
        DOCUMENT_SERVICE_PUBLIC_URL="http://localhost:8080",
    )
    def test_stamp_succeeds_and_rewrites_url(self, filing_defendant):
        """When DRS returns a stamped URL, we rewrite and save it."""
        mock_result = {
            'document_id': str(filing_defendant.document_id),
            'stamped_document_url': FAKE_STAMPED_URL,
        }
        with patch(DRS_CLIENT) as MockClient:
            MockClient.return_value.generate_approved_stamp.return_value = mock_result

            ok = stamp_legal_document(
                entity=filing_defendant,
                document_id_field='document_id',
                approver_id=str(uuid.uuid4()),
                entity_type='filing_defendant',
                auth_token='fake-jwt',
            )

        assert ok is True
        filing_defendant.refresh_from_db()
        assert filing_defendant.stamped_document_url == PUBLIC_STAMPED_URL

    @pytest.mark.django_db
    def test_stamp_skips_when_no_document_id(self, filing_defendant):
        """When the entity's document_id field is empty, stamp is skipped."""
        # Simulate an entity where the document_id_field points to a None attribute
        filing_defendant.document_id = None
        # Don't save — just test the utility logic
        ok = stamp_legal_document(
            entity=filing_defendant,
            document_id_field='document_id',
            approver_id=str(uuid.uuid4()),
            entity_type='filing_defendant',
        )
        assert ok is False

    @pytest.mark.django_db
    def test_stamp_returns_false_on_drs_error(self, filing_defendant):
        """DRS errors are caught — returns False, no exception raised."""
        with patch(DRS_CLIENT) as MockClient:
            MockClient.return_value.generate_approved_stamp.side_effect = Exception("DRS down")

            ok = stamp_legal_document(
                entity=filing_defendant,
                document_id_field='document_id',
                approver_id=str(uuid.uuid4()),
                entity_type='filing_defendant',
                auth_token='fake-jwt',
            )

        assert ok is False
        filing_defendant.refresh_from_db()
        assert filing_defendant.stamped_document_url is None

    @pytest.mark.django_db
    @override_settings(
        DOCUMENT_SERVICE_URL="http://document-records-service:8002",
        DOCUMENT_SERVICE_PUBLIC_URL="http://localhost:8080",
    )
    def test_stamp_settlement_uses_agreement_document_id(self, settlement_defendant):
        """Settlement entities use agreement_document_id for stamping."""
        mock_result = {
            'document_id': str(settlement_defendant.agreement_document_id),
            'stamped_document_url': FAKE_STAMPED_URL,
        }
        with patch(DRS_CLIENT) as MockClient:
            MockClient.return_value.generate_approved_stamp.return_value = mock_result

            ok = stamp_legal_document(
                entity=settlement_defendant,
                document_id_field='agreement_document_id',
                approver_id=str(uuid.uuid4()),
                entity_type='settlement_defendant',
                auth_token='fake-jwt',
            )

        assert ok is True
        settlement_defendant.refresh_from_db()
        assert settlement_defendant.stamped_document_url == PUBLIC_STAMPED_URL


# ═══════════════════════════════════════════════════════════════════════════════
# Serializer field exposure tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestStampedUrlInSerializers:

    @pytest.mark.django_db
    def test_filing_defendant_serializer_includes_stamped_url(
        self, legal_user_client, filing_defendant, allow_all_permissions,
    ):
        from django.urls import reverse
        url = reverse("legal-filing-defendant-detail", args=[filing_defendant.id])
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert 'stamped_document_url' in resp.data['data']

    @pytest.mark.django_db
    def test_settlement_defendant_serializer_includes_stamped_url(
        self, legal_user_client, settlement_defendant, allow_all_permissions,
    ):
        from django.urls import reverse
        url = reverse("legal-settlement-defendant-detail", args=[settlement_defendant.id])
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert 'stamped_document_url' in resp.data['data']

    @pytest.mark.django_db
    def test_judgment_defendant_serializer_includes_stamped_url(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        from django.urls import reverse
        url = reverse("legal-judgment-defendant-detail", args=[judgment_defendant.id])
        resp = legal_user_client.get(url)
        assert resp.status_code == 200
        assert 'stamped_document_url' in resp.data['data']


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow-action stamp integration tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFilingDefendantStampOnCompletion:

    @pytest.mark.django_db
    def test_stamp_called_when_workflow_completes(
        self, legal_user_client, filing_defendant, allow_all_permissions,
    ):
        """When advance_workflow_stage returns plan_status=completed, stamp is triggered."""
        filing_defendant.workflow_plan_id = uuid.uuid4()
        filing_defendant.workflow_stage = 'Filing Confirmation'
        filing_defendant.workflow_stage_id = uuid.uuid4()
        filing_defendant.save()

        with patch(
            f"{FILING_VIEW_MODULE}.LegalFilingService"
        ) as MockService, patch(
            STAMP_FN
        ) as mock_stamp:
            MockService.return_value.advance_workflow_stage.return_value = {
                'action': 'approve',
                'new_stage_status': 'completed',
                'plan_status': 'completed',
                'next_stage': None,
                'next_stage_id': None,
            }

            from django.urls import reverse
            url = reverse("legal-filing-defendant-workflow-action", args=[filing_defendant.id])
            resp = legal_user_client.post(url, {"action": "approve"}, format="json")

        assert resp.status_code == 200
        mock_stamp.assert_called_once()

    @pytest.mark.django_db
    def test_stamp_not_called_when_workflow_in_progress(
        self, legal_user_client, filing_defendant, allow_all_permissions,
    ):
        """When workflow advances but is not complete, stamp is NOT triggered."""
        filing_defendant.workflow_plan_id = uuid.uuid4()
        filing_defendant.workflow_stage = 'Filing Officer Review'
        filing_defendant.workflow_stage_id = uuid.uuid4()
        filing_defendant.save()

        with patch(
            f"{FILING_VIEW_MODULE}.LegalFilingService"
        ) as MockService, patch(
            STAMP_FN
        ) as mock_stamp:
            MockService.return_value.advance_workflow_stage.return_value = {
                'action': 'approve',
                'new_stage_status': 'completed',
                'plan_status': 'in_progress',
                'next_stage': 'Legal Manager Review',
                'next_stage_id': str(uuid.uuid4()),
            }

            from django.urls import reverse
            url = reverse("legal-filing-defendant-workflow-action", args=[filing_defendant.id])
            resp = legal_user_client.post(url, {"action": "approve"}, format="json")

        assert resp.status_code == 200
        mock_stamp.assert_not_called()


class TestSettlementDefendantStampOnCompletion:

    @pytest.mark.django_db
    def test_stamp_called_on_settlement_approval(
        self, legal_user_client, settlement_defendant, allow_all_permissions,
    ):
        settlement_defendant.workflow_plan_id = uuid.uuid4()
        settlement_defendant.workflow_stage = 'Legal Manager Settlement Approval'
        settlement_defendant.workflow_stage_id = uuid.uuid4()
        settlement_defendant.save()

        with patch(
            f"{SETTLEMENT_VIEW_MODULE}.LegalSettlementService"
        ) as MockService, patch(
            STAMP_FN
        ) as mock_stamp:
            MockService.return_value.advance_workflow_stage.return_value = {
                'action': 'approve',
                'new_stage_status': 'completed',
                'plan_status': 'completed',
                'next_stage': None,
                'next_stage_id': None,
            }

            from django.urls import reverse
            url = reverse("legal-settlement-defendant-workflow-action", args=[settlement_defendant.id])
            resp = legal_user_client.post(url, {"action": "approve"}, format="json")

        assert resp.status_code == 200
        mock_stamp.assert_called_once()


class TestJudgmentDefendantStampOnCompletion:

    @pytest.mark.django_db
    def test_stamp_called_on_judgment_workflow_complete(
        self, legal_user_client, judgment_defendant, allow_all_permissions,
    ):
        judgment_defendant.workflow_plan_id = uuid.uuid4()
        judgment_defendant.workflow_stage = 'DG Decision Review'
        judgment_defendant.workflow_stage_id = uuid.uuid4()
        judgment_defendant.save()

        with patch(
            f"{JUDGMENT_VIEW_MODULE}.LegalJudgmentService"
        ) as MockService, patch(
            STAMP_FN
        ) as mock_stamp:
            MockService.return_value.advance_workflow_stage.return_value = {
                'action': 'approve',
                'new_stage_status': 'completed',
                'plan_status': 'completed',
                'next_stage': None,
                'next_stage_id': None,
            }

            from django.urls import reverse
            url = reverse("legal-judgment-defendant-workflow-action", args=[judgment_defendant.id])
            resp = legal_user_client.post(url, {"action": "approve"}, format="json")

        assert resp.status_code == 200
        mock_stamp.assert_called_once()
