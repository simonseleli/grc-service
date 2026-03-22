"""
Phase 1 Gap Fix Tests — Backend Gap Support Analysis, Phase 1

Covers:
  - GAP-15/28: RiskAssessmentSheet status field + transition endpoints
  - GAP-12/25/26: QMSAuditReport extended statuses + governance endpoints
  - GAP-4: NonConformance disputed/withdrawn status + dispute endpoints
"""
import uuid
import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.models.risk_entities import (
    RiskAssessmentSheet,
    QMSAuditReport,
    NonConformance,
)
from tests.risk_management.conftest import (
    RMQAM_USER_ID, RC_USER_ID, QA_USER_ID, TL_USER_ID,
    SYSTEM_USER_ID, ORG_UNIT_UUID,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-15/28 — RiskAssessmentSheet Status Field + Transition Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestRASStatusField:
    """RAS model now has a status field defaulting to 'draft'."""

    @pytest.mark.django_db
    def test_ras_default_status_is_draft(self, risk_assessment_sheet):
        assert risk_assessment_sheet.status == RiskAssessmentSheet.STATUS_DRAFT

    @pytest.mark.django_db
    def test_ras_status_choices_are_complete(self):
        codes = [c[0] for c in RiskAssessmentSheet.RAS_STATUS_CHOICES]
        assert 'draft' in codes
        assert 'submitted_to_head' in codes
        assert 'head_endorsed' in codes
        assert 'submitted_to_rmqam' in codes
        assert 'approved' in codes
        assert 'returned_for_rework' in codes

    @pytest.mark.django_db
    def test_ras_serializer_includes_status(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("risk-assessment-sheet-detail", args=[risk_assessment_sheet.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "status" in data
        assert data["status"] == "draft"

    @pytest.mark.django_db
    def test_ras_serializer_includes_review_comments(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("risk-assessment-sheet-detail", args=[risk_assessment_sheet.id])
        response = rmqam_client.get(url)
        data = response.json()["data"]
        assert "review_comments" in data
        assert "rejected_at" in data
        assert "resubmitted_at" in data


class TestRASSubmitView:
    """RC submits RAS: draft → submitted_to_head."""

    @pytest.mark.django_db
    def test_submit_draft_succeeds(self, rc_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("ras-submit", args=[risk_assessment_sheet.id])
        response = rc_client.post(url, format="json")
        assert response.status_code == 200
        assert response.json()["success"] is True
        risk_assessment_sheet.refresh_from_db()
        assert risk_assessment_sheet.status == RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD

    @pytest.mark.django_db
    def test_submit_returns_for_rework_succeeds(self, rc_client, risk_assessment_sheet, allow_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_RETURNED_FOR_REWORK
        risk_assessment_sheet.save()
        url = reverse("ras-submit", args=[risk_assessment_sheet.id])
        response = rc_client.post(url, format="json")
        assert response.status_code == 200
        risk_assessment_sheet.refresh_from_db()
        assert risk_assessment_sheet.status == RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD

    @pytest.mark.django_db
    def test_submit_from_approved_fails(self, rc_client, risk_assessment_sheet, allow_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_APPROVED
        risk_assessment_sheet.save()
        url = reverse("ras-submit", args=[risk_assessment_sheet.id])
        response = rc_client.post(url, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_submit_anon_is_401(self, anon_client, risk_assessment_sheet):
        url = reverse("ras-submit", args=[risk_assessment_sheet.id])
        response = anon_client.post(url, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_submit_permission_denied_is_403(self, rc_client, risk_assessment_sheet, deny_all_permissions):
        url = reverse("ras-submit", args=[risk_assessment_sheet.id])
        response = rc_client.post(url, format="json")
        assert response.status_code == 403


class TestRASEndorseView:
    """Head endorses: submitted_to_head → head_endorsed."""

    @pytest.mark.django_db
    def test_endorse_succeeds(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD
        risk_assessment_sheet.save()
        url = reverse("ras-endorse", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        risk_assessment_sheet.refresh_from_db()
        assert risk_assessment_sheet.status == RiskAssessmentSheet.STATUS_HEAD_ENDORSED

    @pytest.mark.django_db
    def test_endorse_from_draft_fails(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("ras-endorse", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 400


class TestRASSubmitToRMQAMView:
    """Head submits to RMQAM: head_endorsed → submitted_to_rmqam."""

    @pytest.mark.django_db
    def test_submit_to_rmqam_succeeds(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_HEAD_ENDORSED
        risk_assessment_sheet.save()
        url = reverse("ras-submit-to-rmqam", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        risk_assessment_sheet.refresh_from_db()
        assert risk_assessment_sheet.status == RiskAssessmentSheet.STATUS_SUBMITTED_TO_RMQAM

    @pytest.mark.django_db
    def test_submit_to_rmqam_wrong_status_fails(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("ras-submit-to-rmqam", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 400


class TestRASApproveView:
    """RMQAM approves: submitted_to_rmqam → approved."""

    @pytest.mark.django_db
    def test_approve_succeeds(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_SUBMITTED_TO_RMQAM
        risk_assessment_sheet.save()
        url = reverse("ras-approve", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        risk_assessment_sheet.refresh_from_db()
        assert risk_assessment_sheet.status == RiskAssessmentSheet.STATUS_APPROVED

    @pytest.mark.django_db
    def test_approve_wrong_status_fails(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("ras-approve", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 400


class TestRASReturnForReworkView:
    """RMQAM/Head returns for rework with review comments."""

    @pytest.mark.django_db
    def test_return_for_rework_from_submitted_to_head(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD
        risk_assessment_sheet.save()
        url = reverse("ras-return-for-rework", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, {"review_comments": "Needs more context"}, format="json")
        assert response.status_code == 200
        risk_assessment_sheet.refresh_from_db()
        assert risk_assessment_sheet.status == RiskAssessmentSheet.STATUS_RETURNED_FOR_REWORK
        assert risk_assessment_sheet.review_comments == "Needs more context"
        assert risk_assessment_sheet.rejected_at is not None

    @pytest.mark.django_db
    def test_return_for_rework_from_submitted_to_rmqam(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_SUBMITTED_TO_RMQAM
        risk_assessment_sheet.save()
        url = reverse("ras-return-for-rework", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, {"review_comments": "Revise risk scoring"}, format="json")
        assert response.status_code == 200
        risk_assessment_sheet.refresh_from_db()
        assert risk_assessment_sheet.status == RiskAssessmentSheet.STATUS_RETURNED_FOR_REWORK

    @pytest.mark.django_db
    def test_return_for_rework_missing_comments_fails(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD
        risk_assessment_sheet.save()
        url = reverse("ras-return-for-rework", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_return_for_rework_from_draft_fails(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("ras-return-for-rework", args=[risk_assessment_sheet.id])
        response = rmqam_client.post(url, {"review_comments": "Test"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_return_for_rework_permission_denied(self, rc_client, risk_assessment_sheet, deny_all_permissions):
        risk_assessment_sheet.status = RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD
        risk_assessment_sheet.save()
        url = reverse("ras-return-for-rework", args=[risk_assessment_sheet.id])
        response = rc_client.post(url, {"review_comments": "Test"}, format="json")
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-12/25/26 — QMSAuditReport Extended Statuses
# ═══════════════════════════════════════════════════════════════════════════════

class TestQMSReportExtendedStatusField:
    """QMSAuditReport now has extended STATUS_CHOICES and new fields."""

    @pytest.mark.django_db
    def test_qms_report_extended_choices(self):
        codes = [c[0] for c in QMSAuditReport.STATUS_CHOICES]
        assert 'submitted_to_rmqam' in codes
        assert 'returned_for_revision' in codes
        assert 'presented_at_mrm' in codes
        assert 'directives_received' in codes
        assert 'submitted_to_audit_committee' in codes
        assert 'audit_committee_reviewed' in codes
        assert 'adopted_by_commission' in codes

    @pytest.mark.django_db
    def test_qms_report_serializer_includes_new_fields(
        self, rmqam_client, qms_report, allow_all_permissions
    ):
        url = reverse("qms-audit-report-detail", args=[qms_report.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "mrm_directives" in data
        assert "mrm_directives_communicated_at" in data
        assert "rmqam_review_comments" in data
        assert "returned_for_revision_at" in data


class TestQMSReportSubmitToRMQAMView:

    @pytest.mark.django_db
    def test_submit_to_rmqam_from_finalised(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'finalised'
        qms_report.save()
        url = reverse("qms-report-submit-to-rmqam", args=[qms_report.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.status == 'submitted_to_rmqam'

    @pytest.mark.django_db
    def test_submit_to_rmqam_from_draft_fails(self, rmqam_client, qms_report, allow_all_permissions):
        url = reverse("qms-report-submit-to-rmqam", args=[qms_report.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 400


class TestQMSReportReturnForRevisionView:

    @pytest.mark.django_db
    def test_return_for_revision_requires_comments(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'submitted_to_rmqam'
        qms_report.save()
        url = reverse("qms-report-return-for-revision", args=[qms_report.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_return_for_revision_sets_fields(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'submitted_to_rmqam'
        qms_report.save()
        url = reverse("qms-report-return-for-revision", args=[qms_report.id])
        response = rmqam_client.post(url, {"rmqam_review_comments": "Revise executive summary"}, format="json")
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.status == 'returned_for_revision'
        assert qms_report.rmqam_review_comments == "Revise executive summary"
        assert qms_report.returned_for_revision_at is not None


class TestQMSReportPresentAtMRMView:

    @pytest.mark.django_db
    def test_present_at_mrm_from_submitted(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'submitted_to_rmqam'
        qms_report.save()
        url = reverse("qms-report-present-at-mrm", args=[qms_report.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.status == 'presented_at_mrm'

    @pytest.mark.django_db
    def test_present_at_mrm_from_returned(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'returned_for_revision'
        qms_report.save()
        url = reverse("qms-report-present-at-mrm", args=[qms_report.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.status == 'presented_at_mrm'


class TestQMSReportRecordDirectivesView:

    @pytest.mark.django_db
    def test_record_directives_requires_directives_field(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'presented_at_mrm'
        qms_report.save()
        url = reverse("qms-report-record-directives", args=[qms_report.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_record_directives_sets_fields(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'presented_at_mrm'
        qms_report.save()
        url = reverse("qms-report-record-directives", args=[qms_report.id])
        response = rmqam_client.post(url, {"mrm_directives": "Implement corrective actions within 30 days"}, format="json")
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.status == 'directives_received'
        assert qms_report.mrm_directives == "Implement corrective actions within 30 days"
        assert qms_report.mrm_directives_communicated_at is not None


class TestQMSReportAuditCommitteeAndCommissionViews:

    @pytest.mark.django_db
    def test_submit_to_audit_committee(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'directives_received'
        qms_report.save()
        url = reverse("qms-report-submit-to-audit-committee", args=[qms_report.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.status == 'submitted_to_audit_committee'

    @pytest.mark.django_db
    def test_audit_committee_review(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'submitted_to_audit_committee'
        qms_report.save()
        url = reverse("qms-report-audit-committee-review", args=[qms_report.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.status == 'audit_committee_reviewed'

    @pytest.mark.django_db
    def test_adopt_by_commission(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.status = 'audit_committee_reviewed'
        qms_report.save()
        url = reverse("qms-report-adopt-by-commission", args=[qms_report.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.status == 'adopted_by_commission'

    @pytest.mark.django_db
    def test_adopt_by_commission_wrong_status_fails(self, rmqam_client, qms_report, allow_all_permissions):
        # Draft report cannot skip to adopted
        url = reverse("qms-report-adopt-by-commission", args=[qms_report.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_governance_chain_anon_is_401(self, anon_client, qms_report):
        url = reverse("qms-report-submit-to-rmqam", args=[qms_report.id])
        response = anon_client.post(url, format="json")
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-4 — NonConformance Dispute / Withdrawal
# ═══════════════════════════════════════════════════════════════════════════════

class TestNCDisputeStatusField:

    @pytest.mark.django_db
    def test_nc_has_disputed_status_choice(self):
        codes = [c[0] for c in NonConformance.STATUS_CHOICES]
        assert 'disputed' in codes
        assert 'withdrawn' in codes

    @pytest.mark.django_db
    def test_nc_serializer_includes_dispute_fields(
        self, rmqam_client, nonconformance, allow_all_permissions
    ):
        url = reverse("non-conformance-detail", args=[nonconformance.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "dispute_reason" in data
        assert "disputed_at" in data
        assert "disputed_by" in data


class TestNCDisputeView:

    @pytest.mark.django_db
    def test_dispute_raised_nc(self, rmqam_client, nonconformance, allow_all_permissions):
        url = reverse("non-conformance-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"dispute_reason": "Finding is inaccurate"}, format="json")
        assert response.status_code == 200
        assert response.json()["success"] is True
        nonconformance.refresh_from_db()
        assert nonconformance.status == NonConformance.STATUS_DISPUTED
        assert nonconformance.dispute_reason == "Finding is inaccurate"
        assert nonconformance.disputed_at is not None
        assert nonconformance.disputed_by is not None

    @pytest.mark.django_db
    def test_dispute_in_progress_nc(self, rmqam_client, nonconformance, allow_all_permissions):
        nonconformance.status = NonConformance.STATUS_IN_PROGRESS
        nonconformance.save()
        url = reverse("non-conformance-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"dispute_reason": "Evidence not valid"}, format="json")
        assert response.status_code == 200
        nonconformance.refresh_from_db()
        assert nonconformance.status == NonConformance.STATUS_DISPUTED

    @pytest.mark.django_db
    def test_dispute_closed_nc_fails(self, rmqam_client, nonconformance, allow_all_permissions):
        nonconformance.status = NonConformance.STATUS_CLOSED
        nonconformance.save()
        url = reverse("non-conformance-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"dispute_reason": "Test"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_dispute_already_disputed_fails(self, rmqam_client, nonconformance, allow_all_permissions):
        nonconformance.status = NonConformance.STATUS_DISPUTED
        nonconformance.save()
        url = reverse("non-conformance-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"dispute_reason": "Test"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_dispute_requires_reason(self, rmqam_client, nonconformance, allow_all_permissions):
        url = reverse("non-conformance-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_dispute_anon_is_401(self, anon_client, nonconformance):
        url = reverse("non-conformance-dispute", args=[nonconformance.id])
        response = anon_client.post(url, {"dispute_reason": "Test"}, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_dispute_permission_denied(self, rmqam_client, nonconformance, deny_all_permissions):
        url = reverse("non-conformance-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"dispute_reason": "Test"}, format="json")
        assert response.status_code == 403


class TestNCResolveDisputeView:

    @pytest.mark.django_db
    def test_resolve_dispute_close(self, rmqam_client, nonconformance, allow_all_permissions):
        nonconformance.status = NonConformance.STATUS_DISPUTED
        nonconformance.save()
        url = reverse("non-conformance-resolve-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"resolution": "close", "closure_notes": "Verified and closed"}, format="json")
        assert response.status_code == 200
        nonconformance.refresh_from_db()
        assert nonconformance.status == NonConformance.STATUS_CLOSED
        assert nonconformance.closed_at is not None
        assert nonconformance.closure_notes == "Verified and closed"

    @pytest.mark.django_db
    def test_resolve_dispute_withdraw(self, rmqam_client, nonconformance, allow_all_permissions):
        nonconformance.status = NonConformance.STATUS_DISPUTED
        nonconformance.save()
        url = reverse("non-conformance-resolve-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"resolution": "withdraw"}, format="json")
        assert response.status_code == 200
        nonconformance.refresh_from_db()
        assert nonconformance.status == NonConformance.STATUS_WITHDRAWN

    @pytest.mark.django_db
    def test_resolve_dispute_invalid_resolution(self, rmqam_client, nonconformance, allow_all_permissions):
        nonconformance.status = NonConformance.STATUS_DISPUTED
        nonconformance.save()
        url = reverse("non-conformance-resolve-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"resolution": "ignore"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_resolve_non_disputed_nc_fails(self, rmqam_client, nonconformance, allow_all_permissions):
        url = reverse("non-conformance-resolve-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"resolution": "close"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_resolve_dispute_missing_resolution(self, rmqam_client, nonconformance, allow_all_permissions):
        nonconformance.status = NonConformance.STATUS_DISPUTED
        nonconformance.save()
        url = reverse("non-conformance-resolve-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_resolve_dispute_anon_is_401(self, anon_client, nonconformance):
        url = reverse("non-conformance-resolve-dispute", args=[nonconformance.id])
        response = anon_client.post(url, {"resolution": "close"}, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_resolve_dispute_permission_denied(self, rmqam_client, nonconformance, deny_all_permissions):
        nonconformance.status = NonConformance.STATUS_DISPUTED
        nonconformance.save()
        url = reverse("non-conformance-resolve-dispute", args=[nonconformance.id])
        response = rmqam_client.post(url, {"resolution": "close"}, format="json")
        assert response.status_code == 403
