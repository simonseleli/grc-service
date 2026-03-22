"""
Phase 2 Gap Fix Tests — Backend Gap Support Analysis, Phase 2

Covers:
  - GAP-22: RTAPItem returned_for_rework status + rework/resubmit endpoints
  - GAP-8:  IRR workshop fields + notify-directors / notify-rcs endpoints
  - GAP-7:  RTAP send-reminder endpoint
  - GAP-24: IRR & RTAP distribution fields + distribute endpoints
"""
import pytest
from django.urls import reverse

from apps.core.models.risk_entities import (
    RTAPItem,
    InstitutionalRiskRegister,
    RiskTreatmentActionPlan,
)
from tests.risk_management.conftest import (
    RMQAM_USER_ID, RC_USER_ID, SYSTEM_USER_ID,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-22 — RTAPItem returned_for_rework Status
# ═══════════════════════════════════════════════════════════════════════════════

class TestRTAPItemReturnForReworkStatusField:

    @pytest.mark.django_db
    def test_rtap_item_has_returned_for_rework_choice(self):
        codes = [c[0] for c in RTAPItem.STATUS_CHOICES]
        assert 'returned_for_rework' in codes

    @pytest.mark.django_db
    def test_rtap_item_serializer_includes_rework_fields(
        self, rmqam_client, rtap_item, allow_all_permissions
    ):
        url = reverse("rtap-item-detail", args=[rtap_item.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "review_comments" in data
        assert "returned_at" in data
        assert "resubmitted_at" in data


class TestRTAPItemReturnForReworkView:

    @pytest.mark.django_db
    def test_return_for_rework_from_in_progress(self, rmqam_client, rtap_item, allow_all_permissions):
        rtap_item.status = RTAPItem.STATUS_IN_PROGRESS
        rtap_item.save()
        url = reverse("rtap-item-return-for-rework", args=[rtap_item.id])
        response = rmqam_client.post(url, {"review_comments": "Evidence insufficient"}, format="json")
        assert response.status_code == 200
        assert response.json()["success"] is True
        rtap_item.refresh_from_db()
        assert rtap_item.status == RTAPItem.STATUS_RETURNED_FOR_REWORK
        assert rtap_item.review_comments == "Evidence insufficient"
        assert rtap_item.returned_at is not None

    @pytest.mark.django_db
    def test_return_for_rework_from_not_started(self, rmqam_client, rtap_item, allow_all_permissions):
        url = reverse("rtap-item-return-for-rework", args=[rtap_item.id])
        response = rmqam_client.post(url, {"review_comments": "Needs revision"}, format="json")
        assert response.status_code == 200
        rtap_item.refresh_from_db()
        assert rtap_item.status == RTAPItem.STATUS_RETURNED_FOR_REWORK

    @pytest.mark.django_db
    def test_return_for_rework_from_completed_fails(self, rmqam_client, rtap_item, allow_all_permissions):
        rtap_item.status = RTAPItem.STATUS_COMPLETED
        rtap_item.save()
        url = reverse("rtap-item-return-for-rework", args=[rtap_item.id])
        response = rmqam_client.post(url, {"review_comments": "Needs revision"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_return_for_rework_requires_comment(self, rmqam_client, rtap_item, allow_all_permissions):
        rtap_item.status = RTAPItem.STATUS_IN_PROGRESS
        rtap_item.save()
        url = reverse("rtap-item-return-for-rework", args=[rtap_item.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_return_for_rework_anon_is_401(self, anon_client, rtap_item):
        url = reverse("rtap-item-return-for-rework", args=[rtap_item.id])
        response = anon_client.post(url, {"review_comments": "Test"}, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_return_for_rework_permission_denied(self, rmqam_client, rtap_item, deny_all_permissions):
        rtap_item.status = RTAPItem.STATUS_IN_PROGRESS
        rtap_item.save()
        url = reverse("rtap-item-return-for-rework", args=[rtap_item.id])
        response = rmqam_client.post(url, {"review_comments": "Test"}, format="json")
        assert response.status_code == 403


class TestRTAPItemResubmitView:

    @pytest.mark.django_db
    def test_resubmit_sets_in_progress(self, rmqam_client, rtap_item, allow_all_permissions):
        rtap_item.status = RTAPItem.STATUS_RETURNED_FOR_REWORK
        rtap_item.save()
        url = reverse("rtap-item-resubmit", args=[rtap_item.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        rtap_item.refresh_from_db()
        assert rtap_item.status == RTAPItem.STATUS_IN_PROGRESS
        assert rtap_item.resubmitted_at is not None

    @pytest.mark.django_db
    def test_resubmit_from_in_progress_fails(self, rmqam_client, rtap_item, allow_all_permissions):
        rtap_item.status = RTAPItem.STATUS_IN_PROGRESS
        rtap_item.save()
        url = reverse("rtap-item-resubmit", args=[rtap_item.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_resubmit_from_not_started_fails(self, rmqam_client, rtap_item, allow_all_permissions):
        url = reverse("rtap-item-resubmit", args=[rtap_item.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_resubmit_anon_is_401(self, anon_client, rtap_item):
        url = reverse("rtap-item-resubmit", args=[rtap_item.id])
        response = anon_client.post(url, format="json")
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-8 — IRR Workshop Fields + Notify Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestIRRWorkshopFields:

    @pytest.mark.django_db
    def test_irr_serializer_includes_workshop_fields(
        self, rmqam_client, inst_register, allow_all_permissions
    ):
        url = reverse("inst-risk-register-detail", args=[inst_register.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "workshop_date" in data
        assert "workshop_venue" in data
        assert "directors_notified_at" in data
        assert "rcs_notified_at" in data

    @pytest.mark.django_db
    def test_irr_workshop_date_can_be_patched(self, rmqam_client, inst_register, allow_all_permissions):
        url = reverse("inst-risk-register-detail", args=[inst_register.id])
        response = rmqam_client.patch(
            url,
            {"workshop_date": "2026-05-10", "workshop_venue": "Conference Room A"},
            format="json",
        )
        assert response.status_code == 200
        inst_register.refresh_from_db()
        assert str(inst_register.workshop_date) == "2026-05-10"
        assert inst_register.workshop_venue == "Conference Room A"


class TestIRRNotifyDirectorsView:

    @pytest.mark.django_db
    def test_notify_directors_records_timestamp(self, rmqam_client, inst_register, allow_all_permissions):
        url = reverse("irr-notify-directors", args=[inst_register.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "notified_at" in body["data"]
        assert "notified_count" in body["data"]
        inst_register.refresh_from_db()
        assert inst_register.directors_notified_at is not None

    @pytest.mark.django_db
    def test_notify_directors_anon_is_401(self, anon_client, inst_register):
        url = reverse("irr-notify-directors", args=[inst_register.id])
        response = anon_client.post(url, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_notify_directors_permission_denied(self, rmqam_client, inst_register, deny_all_permissions):
        url = reverse("irr-notify-directors", args=[inst_register.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 403


class TestIRRNotifyRCsView:

    @pytest.mark.django_db
    def test_notify_rcs_records_timestamp(self, rmqam_client, inst_register, allow_all_permissions):
        url = reverse("irr-notify-rcs", args=[inst_register.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "notified_at" in body["data"]
        assert "notified_count" in body["data"]
        inst_register.refresh_from_db()
        assert inst_register.rcs_notified_at is not None

    @pytest.mark.django_db
    def test_notify_rcs_count_matches_entries(
        self, rmqam_client, inst_register, inst_entry, allow_all_permissions
    ):
        url = reverse("irr-notify-rcs", args=[inst_register.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        # inst_entry has one risk_sheet → one RC → notified_count >= 0
        assert response.json()["data"]["notified_count"] >= 0

    @pytest.mark.django_db
    def test_notify_rcs_anon_is_401(self, anon_client, inst_register):
        url = reverse("irr-notify-rcs", args=[inst_register.id])
        response = anon_client.post(url, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_notify_rcs_permission_denied(self, rmqam_client, inst_register, deny_all_permissions):
        url = reverse("irr-notify-rcs", args=[inst_register.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-7 — RTAP Send Reminder Endpoint
# ═══════════════════════════════════════════════════════════════════════════════

class TestRTAPSendReminderView:

    @pytest.mark.django_db
    def test_send_reminder_returns_notified_count(
        self, rmqam_client, rtap, inst_entry, allow_all_permissions
    ):
        url = reverse("rtap-send-reminder", args=[rtap.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "notified_count" in body["data"]
        assert isinstance(body["data"]["notified_count"], int)

    @pytest.mark.django_db
    def test_send_reminder_anon_is_401(self, anon_client, rtap):
        url = reverse("rtap-send-reminder", args=[rtap.id])
        response = anon_client.post(url, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_send_reminder_permission_denied(self, rmqam_client, rtap, deny_all_permissions):
        url = reverse("rtap-send-reminder", args=[rtap.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_send_reminder_404_on_unknown_rtap(self, rmqam_client, allow_all_permissions):
        import uuid
        url = reverse("rtap-send-reminder", args=[uuid.uuid4()])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-24 — IRR/RTAP Distribution Fields + Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestIRRDistributionFields:

    @pytest.mark.django_db
    def test_irr_serializer_includes_distribution_fields(
        self, rmqam_client, inst_register, allow_all_permissions
    ):
        url = reverse("inst-risk-register-detail", args=[inst_register.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "distributed_to_directorates_at" in data
        assert "distribution_reference" in data


class TestIRRDistributeView:

    @pytest.mark.django_db
    def test_distribute_approved_irr(self, rmqam_client, inst_register, allow_all_permissions):
        inst_register.status = 'approved'
        inst_register.save()
        url = reverse("irr-distribute", args=[inst_register.id])
        response = rmqam_client.post(url, {"distribution_reference": "IRR-DIST-2026-001"}, format="json")
        assert response.status_code == 200
        assert response.json()["success"] is True
        inst_register.refresh_from_db()
        assert inst_register.distributed_to_directorates_at is not None
        assert inst_register.distribution_reference == "IRR-DIST-2026-001"

    @pytest.mark.django_db
    def test_distribute_without_reference(self, rmqam_client, inst_register, allow_all_permissions):
        inst_register.status = 'approved'
        inst_register.save()
        url = reverse("irr-distribute", args=[inst_register.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 200
        inst_register.refresh_from_db()
        assert inst_register.distributed_to_directorates_at is not None

    @pytest.mark.django_db
    def test_distribute_draft_irr_fails(self, rmqam_client, inst_register, allow_all_permissions):
        url = reverse("irr-distribute", args=[inst_register.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_distribute_irr_anon_is_401(self, anon_client, inst_register):
        url = reverse("irr-distribute", args=[inst_register.id])
        response = anon_client.post(url, {}, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_distribute_irr_permission_denied(self, rmqam_client, inst_register, deny_all_permissions):
        inst_register.status = 'approved'
        inst_register.save()
        url = reverse("irr-distribute", args=[inst_register.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 403


class TestRTAPDistributionFields:

    @pytest.mark.django_db
    def test_rtap_serializer_includes_distribution_fields(
        self, rmqam_client, rtap, allow_all_permissions
    ):
        url = reverse("rtap-detail", args=[rtap.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "distributed_to_directorates_at" in data
        assert "distribution_reference" in data


class TestRTAPDistributeView:

    @pytest.mark.django_db
    def test_distribute_approved_rtap(self, rmqam_client, rtap, allow_all_permissions):
        rtap.status = 'approved'
        rtap.save()
        url = reverse("rtap-distribute", args=[rtap.id])
        response = rmqam_client.post(url, {"distribution_reference": "RTAP-DIST-2026-001"}, format="json")
        assert response.status_code == 200
        assert response.json()["success"] is True
        rtap.refresh_from_db()
        assert rtap.distributed_to_directorates_at is not None
        assert rtap.distribution_reference == "RTAP-DIST-2026-001"

    @pytest.mark.django_db
    def test_distribute_without_reference(self, rmqam_client, rtap, allow_all_permissions):
        rtap.status = 'approved'
        rtap.save()
        url = reverse("rtap-distribute", args=[rtap.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 200
        rtap.refresh_from_db()
        assert rtap.distributed_to_directorates_at is not None

    @pytest.mark.django_db
    def test_distribute_draft_rtap_fails(self, rmqam_client, rtap, allow_all_permissions):
        url = reverse("rtap-distribute", args=[rtap.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_distribute_rtap_anon_is_401(self, anon_client, rtap):
        url = reverse("rtap-distribute", args=[rtap.id])
        response = anon_client.post(url, {}, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_distribute_rtap_permission_denied(self, rmqam_client, rtap, deny_all_permissions):
        rtap.status = 'approved'
        rtap.save()
        url = reverse("rtap-distribute", args=[rtap.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 403
