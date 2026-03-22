"""
Phase 3 Gap Fix Tests — Backend Gap Support Analysis, Phase 3

Covers:
  - GAP-3:  QATrainingAttendee per-session exam fields
  - GAP-5:  NonConformance.last_reviewed_at + NCMonthlySummaryView
  - GAP-6:  RiskMeeting management_review meeting type
  - GAP-10: QualityAuditor qualifications / experience_summary
  - GAP-13: is_certified gate on QA appointment creation
  - GAP-23: QATrainingApproveView + QATrainingNotifyAttendeesView
  - GAP-29: NonConformanceType seeded records
"""
import uuid
import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.models.risk_entities import (
    QATrainingSession,
    QATrainingAttendee,
    QualityAuditor,
    NonConformance,
    RiskMeeting,
)
from apps.core.models.lookups import NonConformanceType
from tests.risk_management.conftest import (
    RMQAM_USER_ID, RC_USER_ID, QA_USER_ID, TL_USER_ID,
    SYSTEM_USER_ID, ORG_UNIT_UUID, HEAD_USER_ID,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-3 — QATrainingAttendee per-session exam fields
# ═══════════════════════════════════════════════════════════════════════════════

class TestQATrainingAttendeeExamFields:
    """QATrainingAttendee model has per-session exam tracking fields."""

    @pytest.mark.django_db
    def test_attendee_exam_fields_default_to_none(self, training_session, quality_auditor):
        attendee = QATrainingAttendee.objects.create(
            training_session=training_session,
            quality_auditor=quality_auditor,
            attended=False,
            created_by=SYSTEM_USER_ID,
        )
        assert attendee.exam_score is None
        assert attendee.exam_attempt_number is None
        assert attendee.exam_date is None
        assert attendee.passed is None

    @pytest.mark.django_db
    def test_attendee_exam_fields_can_be_set(self, training_session, quality_auditor):
        today = datetime.date(2026, 3, 10)
        attendee = QATrainingAttendee.objects.create(
            training_session=training_session,
            quality_auditor=quality_auditor,
            attended=True,
            exam_score=Decimal('82.50'),
            exam_attempt_number=1,
            exam_date=today,
            passed=True,
            created_by=SYSTEM_USER_ID,
        )
        attendee.refresh_from_db()
        assert attendee.exam_score == Decimal('82.50')
        assert attendee.exam_attempt_number == 1
        assert attendee.exam_date == today
        assert attendee.passed is True

    @pytest.mark.django_db
    def test_attendee_serializer_includes_exam_fields(
        self, rmqam_client, training_session, training_attendee, allow_all_permissions
    ):
        url = reverse("qa-training-attendee-detail", args=[training_attendee.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "exam_score" in data
        assert "exam_attempt_number" in data
        assert "exam_date" in data
        assert "passed" in data

    @pytest.mark.django_db
    def test_attendee_patch_updates_exam_fields(
        self, rmqam_client, training_attendee, allow_all_permissions
    ):
        url = reverse("qa-training-attendee-detail", args=[training_attendee.id])
        payload = {
            "exam_score": "78.00",
            "exam_attempt_number": 1,
            "exam_date": "2026-03-15",
            "passed": False,
        }
        response = rmqam_client.patch(url, payload, format="json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["exam_score"] == "78.00"
        assert data["exam_attempt_number"] == 1
        assert data["passed"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-5 — NonConformance.last_reviewed_at + NCMonthlySummaryView
# ═══════════════════════════════════════════════════════════════════════════════

class TestNCLastReviewedAt:
    """NonConformance has last_reviewed_at field."""

    @pytest.mark.django_db
    def test_nc_last_reviewed_at_defaults_to_none(self, nonconformance):
        assert nonconformance.last_reviewed_at is None

    @pytest.mark.django_db
    def test_nc_serializer_includes_last_reviewed_at(
        self, rmqam_client, nonconformance, allow_all_permissions
    ):
        url = reverse("non-conformance-detail", args=[nonconformance.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        assert "last_reviewed_at" in response.json()["data"]

    @pytest.mark.django_db
    def test_nc_patch_sets_last_reviewed_at(
        self, rmqam_client, nonconformance, allow_all_permissions
    ):
        url = reverse("non-conformance-detail", args=[nonconformance.id])
        payload = {"last_reviewed_at": "2026-03-21T09:00:00Z"}
        response = rmqam_client.patch(url, payload, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["last_reviewed_at"] is not None


class TestNCMonthlySummaryView:
    """GET /risk/non-conformances/monthly-summary/ returns aggregated NC stats."""

    @pytest.mark.django_db
    def test_monthly_summary_returns_success(
        self, rmqam_client, nonconformance, allow_all_permissions
    ):
        url = reverse("non-conformance-monthly-summary")
        response = rmqam_client.get(url)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert "total" in data
        assert "overdue" in data
        assert "breakdown" in data

    @pytest.mark.django_db
    def test_monthly_summary_counts_total(
        self, rmqam_client, nonconformance, allow_all_permissions
    ):
        url = reverse("non-conformance-monthly-summary")
        response = rmqam_client.get(url)
        data = response.json()["data"]
        assert data["total"] >= 1

    @pytest.mark.django_db
    def test_monthly_summary_breakdown_includes_raised_status(
        self, rmqam_client, nonconformance, allow_all_permissions
    ):
        url = reverse("non-conformance-monthly-summary")
        response = rmqam_client.get(url)
        breakdown = response.json()["data"]["breakdown"]
        assert "raised" in breakdown
        assert breakdown["raised"] >= 1

    @pytest.mark.django_db
    def test_monthly_summary_overdue_counts_past_due_ncs(
        self, rmqam_client, qms_report, iso_clause, nc_type_major, allow_all_permissions
    ):
        # Create NC with due_date in the past and status 'raised'
        past_due_nc = NonConformance.objects.create(
            audit_report=qms_report,
            iso_clause=iso_clause,
            nc_type=nc_type_major,
            description='Overdue NC',
            objective_evidence='Past the deadline.',
            raised_by=QA_USER_ID,
            status='raised',
            due_date=datetime.date(2000, 1, 1),  # far in the past
            created_by=SYSTEM_USER_ID,
        )
        url = reverse("non-conformance-monthly-summary")
        response = rmqam_client.get(url)
        data = response.json()["data"]
        assert data["overdue"] >= 1

    @pytest.mark.django_db
    def test_monthly_summary_requires_auth(self, anon_client):
        url = reverse("non-conformance-monthly-summary")
        response = anon_client.get(url)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_monthly_summary_filter_by_audit_plan(
        self, rmqam_client, nonconformance, allow_all_permissions
    ):
        plan_id = nonconformance.audit_report.audit_plan_id
        url = reverse("non-conformance-monthly-summary") + f"?audit_plan={plan_id}"
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-6 — RiskMeeting management_review meeting type
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskMeetingManagementReviewType:
    """RiskMeeting supports management_review as a valid meeting_type."""

    @pytest.mark.django_db
    def test_management_review_in_choices(self):
        choices = [c[0] for c in RiskMeeting.MEETING_TYPE_CHOICES]
        assert 'management_review' in choices

    @pytest.mark.django_db
    def test_create_management_review_meeting(self, fiscal_year):
        meeting = RiskMeeting.objects.create(
            meeting_type='management_review',
            organized_by=RMQAM_USER_ID,
            org_unit_id=ORG_UNIT_UUID,
            fiscal_year=fiscal_year,
            title='Q1 Management Review Meeting',
            meeting_date=datetime.datetime(2026, 3, 20, 10, 0, tzinfo=datetime.timezone.utc),
            venue='Board Room A',
            status='scheduled',
            created_by=SYSTEM_USER_ID,
        )
        assert meeting.meeting_type == 'management_review'

    @pytest.mark.django_db
    def test_create_management_review_via_api(
        self, rmqam_client, fiscal_year, allow_all_permissions
    ):
        url = reverse("risk-meeting-list-create")
        payload = {
            "meeting_type": "management_review",
            "organized_by": str(RMQAM_USER_ID),
            "fiscal_year_id": str(fiscal_year.id),
            "title": "Management Review – Q1 2026",
            "meeting_date": "2026-03-20T10:00:00Z",
            "venue": "Board Room",
        }
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.json()["data"]["meeting_type"] == "management_review"


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-10 — QualityAuditor qualifications / experience_summary
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityAuditorQualificationsFields:
    """QualityAuditor has qualifications and experience_summary fields."""

    @pytest.mark.django_db
    def test_quality_auditor_has_qualifications_field(self, quality_auditor):
        quality_auditor.qualifications = "BSc Computer Science, CISA certified"
        quality_auditor.experience_summary = "8 years in IT audit"
        quality_auditor.save()
        quality_auditor.refresh_from_db()
        assert quality_auditor.qualifications == "BSc Computer Science, CISA certified"
        assert quality_auditor.experience_summary == "8 years in IT audit"

    @pytest.mark.django_db
    def test_quality_auditor_serializer_includes_qualifications(
        self, rmqam_client, quality_auditor, allow_all_permissions
    ):
        url = reverse("quality-auditor-detail", args=[quality_auditor.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "qualifications" in data
        assert "experience_summary" in data

    @pytest.mark.django_db
    def test_create_quality_auditor_with_qualifications(
        self, rmqam_client, training_session, allow_all_permissions
    ):
        url = reverse("quality-auditor-list-create")
        payload = {
            "user_id": str(uuid.uuid4()),
            "nominated_by": str(HEAD_USER_ID),
            "org_unit_id": str(ORG_UNIT_UUID),
            "org_unit_type": "directorate",
            "training_session_id": str(training_session.id),
            "qualifications": "MSc Risk Management",
            "experience_summary": "5 years in quality assurance",
        }
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["qualifications"] == "MSc Risk Management"
        assert data["experience_summary"] == "5 years in quality assurance"

    @pytest.mark.django_db
    def test_patch_qualifications_on_existing_auditor(
        self, rmqam_client, quality_auditor, allow_all_permissions
    ):
        url = reverse("quality-auditor-detail", args=[quality_auditor.id])
        payload = {
            "qualifications": "Updated qualification",
            "experience_summary": "Updated experience",
        }
        response = rmqam_client.patch(url, payload, format="json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["qualifications"] == "Updated qualification"
        assert data["experience_summary"] == "Updated experience"


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-13 — is_certified gate on QA appointment creation
# ═══════════════════════════════════════════════════════════════════════════════

class TestQAAppointmentCertifiedGate:
    """POST /quality-auditors/:id/appointments/ is blocked for uncertified auditors."""

    @pytest.mark.django_db
    def test_create_appointment_blocked_when_not_certified(
        self, rmqam_client, training_session, allow_all_permissions
    ):
        uncertified_auditor = QualityAuditor.objects.create(
            user_id=uuid.uuid4(),
            nominated_by=HEAD_USER_ID,
            org_unit_id=ORG_UNIT_UUID,
            org_unit_type='directorate',
            exam_attempt=0,
            is_certified=False,
            training_session=training_session,
            created_by=SYSTEM_USER_ID,
        )
        url = reverse("quality-auditor-appointment-list-create", args=[uncertified_auditor.id])
        payload = {"appointment_date": "2026-04-01"}
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "NOT_CERTIFIED"

    @pytest.mark.django_db
    def test_create_appointment_succeeds_when_certified(
        self, rmqam_client, quality_auditor, allow_all_permissions
    ):
        assert quality_auditor.is_certified is True
        url = reverse("quality-auditor-appointment-list-create", args=[quality_auditor.id])
        # quality_auditor_id is required by the serializer even though auditor is set from URL
        payload = {
            "appointment_date": "2026-04-01",
            "quality_auditor_id": str(quality_auditor.id),
        }
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_gate_returns_not_certified_error_code(
        self, rmqam_client, training_session, allow_all_permissions
    ):
        auditor = QualityAuditor.objects.create(
            user_id=uuid.uuid4(),
            nominated_by=HEAD_USER_ID,
            org_unit_id=ORG_UNIT_UUID,
            org_unit_type='directorate',
            exam_attempt=2,
            exam_score=Decimal('60.00'),
            is_certified=False,
            training_session=training_session,
            created_by=SYSTEM_USER_ID,
        )
        url = reverse("quality-auditor-appointment-list-create", args=[auditor.id])
        response = rmqam_client.post(url, {"appointment_date": "2026-04-01"}, format="json")
        assert response.status_code == 400
        assert "NOT_CERTIFIED" in response.json()["error"]["code"]


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-23 — QATrainingApproveView + QATrainingNotifyAttendeesView
# ═══════════════════════════════════════════════════════════════════════════════

class TestQATrainingApproveView:
    """POST /qa-training/:id/approve/ approves or rejects a proposed session."""

    @pytest.fixture
    def proposed_session(self, db):
        return QATrainingSession.objects.create(
            title='Proposed ISO Training',
            trainer_name='Dr. Trainer',
            training_date=datetime.date(2026, 5, 10),
            approval_status='proposed',
            created_by=SYSTEM_USER_ID,
        )

    @pytest.mark.django_db
    def test_approve_proposed_session(
        self, rmqam_client, proposed_session, allow_all_permissions
    ):
        url = reverse("qa-training-approve", args=[proposed_session.id])
        response = rmqam_client.post(url, {"action": "approve"}, format="json")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        proposed_session.refresh_from_db()
        assert proposed_session.approval_status == 'approved'
        assert proposed_session.approved_by == RMQAM_USER_ID
        assert proposed_session.approval_date is not None

    @pytest.mark.django_db
    def test_reject_proposed_session_with_notes(
        self, rmqam_client, proposed_session, allow_all_permissions
    ):
        url = reverse("qa-training-approve", args=[proposed_session.id])
        payload = {"action": "reject", "rejection_notes": "Trainer not qualified."}
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 200
        proposed_session.refresh_from_db()
        assert proposed_session.approval_status == 'cancelled'
        assert proposed_session.rejection_notes == "Trainer not qualified."

    @pytest.mark.django_db
    def test_approve_invalid_action_returns_400(
        self, rmqam_client, proposed_session, allow_all_permissions
    ):
        url = reverse("qa-training-approve", args=[proposed_session.id])
        response = rmqam_client.post(url, {"action": "delete"}, format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_ACTION"

    @pytest.mark.django_db
    def test_approve_already_approved_session_returns_400(
        self, rmqam_client, training_session, allow_all_permissions
    ):
        # training_session fixture has approval_status='approved'
        url = reverse("qa-training-approve", args=[training_session.id])
        response = rmqam_client.post(url, {"action": "approve"}, format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_STATUS"

    @pytest.mark.django_db
    def test_approve_requires_auth(self, anon_client, proposed_session):
        url = reverse("qa-training-approve", args=[proposed_session.id])
        response = anon_client.post(url, {"action": "approve"}, format="json")
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_rejection_notes_included_in_serializer_response(
        self, rmqam_client, proposed_session, allow_all_permissions
    ):
        url = reverse("qa-training-approve", args=[proposed_session.id])
        payload = {"action": "reject", "rejection_notes": "Budget unavailable."}
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "rejection_notes" in data
        assert data["rejection_notes"] == "Budget unavailable."


class TestQATrainingNotifyAttendeesView:
    """POST /qa-training/:id/notify-attendees/ returns notified_count."""

    @pytest.mark.django_db
    def test_notify_attendees_returns_count(
        self, rmqam_client, training_session, training_attendee, allow_all_permissions
    ):
        url = reverse("qa-training-notify-attendees", args=[training_session.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "notified_count" in body["data"]
        assert body["data"]["notified_count"] >= 1

    @pytest.mark.django_db
    def test_notify_attendees_zero_when_no_attendees(
        self, rmqam_client, training_session, allow_all_permissions
    ):
        # training_session fixture has no attendees attached in this scope
        # delete any leftover attendees to ensure isolation
        from apps.core.models.risk_entities import QATrainingAttendee
        QATrainingAttendee.objects.filter(training_session=training_session).update(is_active=False)
        url = reverse("qa-training-notify-attendees", args=[training_session.id])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["notified_count"] == 0

    @pytest.mark.django_db
    def test_notify_attendees_requires_auth(self, anon_client, training_session):
        url = reverse("qa-training-notify-attendees", args=[training_session.id])
        response = anon_client.post(url, format="json")
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_notify_attendees_404_for_unknown_session(
        self, rmqam_client, allow_all_permissions
    ):
        url = reverse("qa-training-notify-attendees", args=[uuid.uuid4()])
        response = rmqam_client.post(url, format="json")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# GAP-29 — NonConformanceType seeded records
# ═══════════════════════════════════════════════════════════════════════════════

class TestNonConformanceTypeSeedData:
    """NonConformanceType lookup records with correct codes are accessible."""

    @pytest.mark.django_db
    def test_nc_type_major_nc_exists(self, nc_type_major):
        assert nc_type_major.code == 'major_nc'
        assert nc_type_major.name == 'Major Non-Conformance'

    @pytest.mark.django_db
    def test_nc_type_minor_nc_exists(self, nc_type_minor):
        assert nc_type_minor.code == 'minor_nc'

    @pytest.mark.django_db
    def test_nc_type_can_be_created_with_all_standard_codes(self, db):
        codes = ['major_nc', 'minor_nc', 'observation', 'opportunity_for_improvement']
        for i, code in enumerate(codes):
            NonConformanceType.objects.get_or_create(
                code=code,
                defaults={
                    'name': code.replace('_', ' ').title(),
                    'description': f'Test {code}',
                    'sort_order': i + 1,
                    'created_by': SYSTEM_USER_ID,
                },
            )
        assert NonConformanceType.objects.filter(code__in=codes).count() == 4

    @pytest.mark.django_db
    def test_nc_type_lookup_endpoint_returns_records(
        self, rmqam_client, nc_type_major, nc_type_minor, allow_all_permissions
    ):
        # The lookup endpoint is under /audit/lookups/non-conformance-types/
        from django.urls import reverse as _rev
        url = _rev("non-conformance-type-list")
        response = rmqam_client.get(url)
        assert response.status_code == 200
        codes = [item["code"] for item in response.json()["data"]]
        assert "major_nc" in codes
        assert "minor_nc" in codes
