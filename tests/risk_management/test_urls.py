"""
Phase 8 — URL Configuration Tests for Risk Management module.

Tests verify:
1. Every URL name resolves correctly
2. Every URL resolves to the correct path
3. Every URL pattern count matches expected total
"""
import uuid

import pytest
from django.urls import NoReverseMatch, resolve, reverse


# ── Stable test UUID ───────────────────────────────────────────────────────
PK = "11111111-1111-1111-1111-111111111111"


# ═══════════════════════════════════════════════════════════════════════════
# 1. URL Resolution — name → path
# ═══════════════════════════════════════════════════════════════════════════


class TestDashboardURLs:
    def test_dashboard(self):
        assert reverse("risk-dashboard") == "/api/v1/grc/risk/dashboard/"

    def test_dashboard_comparative(self):
        assert reverse("risk-dashboard-comparative") == "/api/v1/grc/risk/dashboard/comparative-analysis/"


class TestRiskChampionURLs:
    def test_list_create(self):
        assert reverse("risk-champion-list-create") == "/api/v1/grc/risk/champions/"

    def test_detail(self):
        url = reverse("risk-champion-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/champions/{PK}/"

    def test_appointment_list_create(self):
        url = reverse("risk-champion-appointment-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/champions/{PK}/appointments/"

    def test_appointment_detail(self):
        url = reverse("risk-champion-appointment-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/champions/appointments/{PK}/"

    @pytest.mark.parametrize("action", ["start", "status", "history", "advance", "cancel", "recall"])
    def test_appointment_workflow(self, action):
        url = reverse(f"rc-appointment-workflow-{action}", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/champions/appointments/{PK}/workflow/{action}/"


class TestRiskAssessmentSheetURLs:
    def test_list_create(self):
        assert reverse("risk-assessment-sheet-list-create") == "/api/v1/grc/risk/assessments/"

    def test_detail(self):
        url = reverse("risk-assessment-sheet-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/assessments/{PK}/"


class TestDeptRiskRegisterURLs:
    def test_list_create(self):
        assert reverse("dept-risk-register-list-create") == "/api/v1/grc/risk/dept-registers/"

    def test_detail(self):
        url = reverse("dept-risk-register-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/dept-registers/{PK}/"

    def test_entry_list_create(self):
        url = reverse("dept-register-entry-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/dept-registers/{PK}/entries/"

    def test_entry_detail(self):
        url = reverse("dept-register-entry-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/dept-registers/entries/{PK}/"

    @pytest.mark.parametrize("action", ["start", "status", "history", "advance", "cancel", "recall"])
    def test_workflow(self, action):
        url = reverse(f"dept-register-workflow-{action}", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/dept-registers/{PK}/workflow/{action}/"


class TestInstitutionalRiskRegisterURLs:
    def test_list_create(self):
        assert reverse("inst-risk-register-list-create") == "/api/v1/grc/risk/institutional-registers/"

    def test_detail(self):
        url = reverse("inst-risk-register-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/institutional-registers/{PK}/"

    def test_entry_list_create(self):
        url = reverse("inst-risk-entry-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/institutional-registers/{PK}/entries/"

    def test_entry_detail(self):
        url = reverse("inst-risk-entry-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/institutional-registers/entries/{PK}/"

    def test_activity_report_list_create(self):
        url = reverse("inst-activity-report-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/institutional-registers/{PK}/activity-reports/"

    def test_activity_report_detail(self):
        url = reverse("inst-activity-report-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/institutional-registers/activity-reports/{PK}/"

    @pytest.mark.parametrize("action", ["start", "status", "history", "advance", "cancel", "recall"])
    def test_workflow(self, action):
        url = reverse(f"inst-register-workflow-{action}", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/institutional-registers/{PK}/workflow/{action}/"


class TestRTAPURLs:
    def test_list_create(self):
        assert reverse("rtap-list-create") == "/api/v1/grc/risk/rtap/"

    def test_detail(self):
        url = reverse("rtap-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/rtap/{PK}/"

    @pytest.mark.parametrize("action", ["start", "status", "history", "advance", "cancel", "recall"])
    def test_workflow(self, action):
        url = reverse(f"rtap-workflow-{action}", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/rtap/{PK}/workflow/{action}/"


class TestRTAPItemURLs:
    def test_list_create(self):
        assert reverse("rtap-item-list-create") == "/api/v1/grc/risk/rtap-items/"

    def test_detail(self):
        url = reverse("rtap-item-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/rtap-items/{PK}/"

    def test_quarterly_update_list_create(self):
        url = reverse("rtap-quarterly-update-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/rtap-items/{PK}/quarterly-updates/"

    def test_quarterly_update_detail(self):
        url = reverse("rtap-quarterly-update-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/rtap-items/quarterly-updates/{PK}/"


class TestQuarterlyReportURLs:
    def test_list_create(self):
        assert reverse("quarterly-report-list-create") == "/api/v1/grc/risk/quarterly-reports/"

    def test_detail(self):
        url = reverse("quarterly-report-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/quarterly-reports/{PK}/"

    @pytest.mark.parametrize("action", ["start", "status", "history", "advance", "cancel", "recall"])
    def test_workflow(self, action):
        url = reverse(f"quarterly-report-workflow-{action}", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/quarterly-reports/{PK}/workflow/{action}/"


class TestQualityAuditorURLs:
    def test_list_create(self):
        assert reverse("quality-auditor-list-create") == "/api/v1/grc/risk/quality-auditors/"

    def test_detail(self):
        url = reverse("quality-auditor-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/quality-auditors/{PK}/"

    def test_appointment_list_create(self):
        url = reverse("quality-auditor-appointment-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/quality-auditors/{PK}/appointments/"

    def test_appointment_detail(self):
        url = reverse("quality-auditor-appointment-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/quality-auditors/appointments/{PK}/"

    @pytest.mark.parametrize("action", ["start", "status", "history", "advance", "cancel", "recall"])
    def test_qa_appointment_workflow(self, action):
        url = reverse(f"qa-appointment-workflow-{action}", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/quality-auditors/appointments/{PK}/workflow/{action}/"


class TestQMSAuditProgramURLs:
    def test_list_create(self):
        assert reverse("qms-audit-program-list-create") == "/api/v1/grc/risk/qms-programs/"

    def test_detail(self):
        url = reverse("qms-audit-program-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-programs/{PK}/"

    @pytest.mark.parametrize("action", ["start", "status", "history", "advance", "cancel", "recall"])
    def test_workflow(self, action):
        url = reverse(f"qms-program-workflow-{action}", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-programs/{PK}/workflow/{action}/"


class TestQMSAuditPlanURLs:
    def test_list_create(self):
        assert reverse("qms-audit-plan-list-create") == "/api/v1/grc/risk/qms-plans/"

    def test_detail(self):
        url = reverse("qms-audit-plan-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-plans/{PK}/"

    def test_team_assignment_list_create(self):
        url = reverse("qms-team-assignment-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-plans/{PK}/team/"

    def test_team_assignment_detail(self):
        url = reverse("qms-team-assignment-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-plans/team/{PK}/"

    @pytest.mark.parametrize("action", ["start", "status", "history", "advance", "cancel", "recall"])
    def test_workflow(self, action):
        url = reverse(f"qms-plan-workflow-{action}", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-plans/{PK}/workflow/{action}/"


class TestQMSAuditChecklistURLs:
    def test_list_create(self):
        assert reverse("audit-checklist-list-create") == "/api/v1/grc/risk/qms-checklists/"

    def test_detail(self):
        url = reverse("audit-checklist-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-checklists/{PK}/"


class TestQMSAuditReportURLs:
    def test_list_create(self):
        assert reverse("qms-audit-report-list-create") == "/api/v1/grc/risk/qms-reports/"

    def test_detail(self):
        url = reverse("qms-audit-report-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-reports/{PK}/"

    def test_sign_tl(self):
        url = reverse("qms-audit-report-sign-tl", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-reports/{PK}/sign-tl/"

    def test_sign_auditee(self):
        url = reverse("qms-audit-report-sign-auditee", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-reports/{PK}/sign-auditee/"


class TestNonConformanceURLs:
    def test_list_create(self):
        assert reverse("non-conformance-list-create") == "/api/v1/grc/risk/non-conformances/"

    def test_detail(self):
        url = reverse("non-conformance-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/non-conformances/{PK}/"


class TestRiskMeetingURLs:
    def test_list_create(self):
        assert reverse("risk-meeting-list-create") == "/api/v1/grc/risk/meetings/"

    def test_detail(self):
        url = reverse("risk-meeting-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/meetings/{PK}/"

    def test_attendance_list_create(self):
        url = reverse("meeting-attendance-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/meetings/{PK}/attendance/"

    def test_attendance_detail(self):
        url = reverse("meeting-attendance-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/meetings/attendance/{PK}/"


class TestQATrainingURLs:
    def test_list_create(self):
        assert reverse("qa-training-session-list-create") == "/api/v1/grc/risk/qa-training/"

    def test_detail(self):
        url = reverse("qa-training-session-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qa-training/{PK}/"

    def test_attendee_list_create(self):
        url = reverse("qa-training-attendee-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qa-training/{PK}/attendees/"

    def test_attendee_detail(self):
        url = reverse("qa-training-attendee-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qa-training/attendees/{PK}/"


class TestQMSAuditSupportURLs:
    def test_audit_meeting_list_create(self):
        url = reverse("qms-audit-meeting-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-plans/{PK}/audit-meetings/"

    def test_audit_meeting_detail(self):
        url = reverse("qms-audit-meeting-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-plans/audit-meetings/{PK}/"

    def test_timetable_list_create(self):
        url = reverse("qms-timetable-entry-list-create", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-plans/{PK}/timetable/"

    def test_timetable_detail(self):
        url = reverse("qms-timetable-entry-detail", kwargs={"pk": PK})
        assert url == f"/api/v1/grc/risk/qms-plans/timetable/{PK}/"


# ═══════════════════════════════════════════════════════════════════════════
# 2. URL Resolve — path → view class
# ═══════════════════════════════════════════════════════════════════════════


class TestURLResolve:
    """Verify that each URL path resolves to the expected view class."""

    @pytest.mark.parametrize(
        "path_suffix, view_name",
        [
            ("dashboard/", "RiskDashboardView"),
            ("dashboard/comparative-analysis/", "RiskDashboardComparativeAnalysisView"),
            (f"champions/", "RiskChampionListCreateView"),
            (f"champions/{PK}/", "RiskChampionDetailView"),
            (f"assessments/", "RiskAssessmentSheetListCreateView"),
            (f"assessments/{PK}/", "RiskAssessmentSheetDetailView"),
            (f"dept-registers/", "DeptRiskRegisterListCreateView"),
            (f"dept-registers/{PK}/", "DeptRiskRegisterDetailView"),
            (f"institutional-registers/", "InstitutionalRiskRegisterListCreateView"),
            (f"institutional-registers/{PK}/", "InstitutionalRiskRegisterDetailView"),
            (f"rtap/", "RTAPListCreateView"),
            (f"rtap/{PK}/", "RTAPDetailView"),
            (f"rtap-items/", "RTAPItemListCreateView"),
            (f"rtap-items/{PK}/", "RTAPItemDetailView"),
            (f"quarterly-reports/", "QuarterlyReportListCreateView"),
            (f"quarterly-reports/{PK}/", "QuarterlyReportDetailView"),
            (f"quality-auditors/", "QualityAuditorListCreateView"),
            (f"quality-auditors/{PK}/", "QualityAuditorDetailView"),
            (f"qms-programs/", "QMSAuditProgramListCreateView"),
            (f"qms-programs/{PK}/", "QMSAuditProgramDetailView"),
            (f"qms-plans/", "QMSAuditPlanListCreateView"),
            (f"qms-plans/{PK}/", "QMSAuditPlanDetailView"),
            (f"qms-checklists/", "AuditChecklistListCreateView"),
            (f"qms-checklists/{PK}/", "AuditChecklistDetailView"),
            (f"qms-reports/", "QMSAuditReportListCreateView"),
            (f"qms-reports/{PK}/", "QMSAuditReportDetailView"),
            (f"non-conformances/", "NonConformanceListCreateView"),
            (f"non-conformances/{PK}/", "NonConformanceDetailView"),
            (f"meetings/", "RiskMeetingListCreateView"),
            (f"meetings/{PK}/", "RiskMeetingDetailView"),
            (f"qa-training/", "QATrainingSessionListCreateView"),
            (f"qa-training/{PK}/", "QATrainingSessionDetailView"),
        ],
    )
    def test_resolve_view(self, path_suffix, view_name):
        match = resolve(f"/api/v1/grc/risk/{path_suffix}")
        assert match.func.view_class.__name__ == view_name


# ═══════════════════════════════════════════════════════════════════════════
# 3. URL Pattern Count
# ═══════════════════════════════════════════════════════════════════════════


class TestURLPatternCount:
    """Verify total number of URL patterns matches expected count."""

    def test_total_url_count(self):
        from apps.api.urls.risk import urlpatterns

        # Current risk URL registry total, including Phase 1-4 workflow/action routes.
        assert len(urlpatterns) == 130


# ═══════════════════════════════════════════════════════════════════════════
# 4. Complete URL Name Registry — all listed names resolve
# ═══════════════════════════════════════════════════════════════════════════


ALL_URL_NAMES_WITH_PK = [
    "risk-champion-detail",
    "risk-champion-appointment-list-create",
    "risk-champion-appointment-detail",
    "rc-appointment-workflow-start",
    "rc-appointment-workflow-status",
    "rc-appointment-workflow-history",
    "rc-appointment-workflow-advance",
    "rc-appointment-workflow-cancel",
    "rc-appointment-workflow-recall",
    "risk-assessment-sheet-detail",
    "dept-risk-register-detail",
    "dept-register-entry-list-create",
    "dept-register-entry-detail",
    "dept-register-workflow-start",
    "dept-register-workflow-status",
    "dept-register-workflow-history",
    "dept-register-workflow-advance",
    "dept-register-workflow-cancel",
    "dept-register-workflow-recall",
    "inst-risk-register-detail",
    "inst-risk-entry-list-create",
    "inst-risk-entry-detail",
    "inst-activity-report-list-create",
    "inst-activity-report-detail",
    "inst-register-workflow-start",
    "inst-register-workflow-status",
    "inst-register-workflow-history",
    "inst-register-workflow-advance",
    "inst-register-workflow-cancel",
    "inst-register-workflow-recall",
    "rtap-detail",
    "rtap-workflow-start",
    "rtap-workflow-status",
    "rtap-workflow-history",
    "rtap-workflow-advance",
    "rtap-workflow-cancel",
    "rtap-workflow-recall",
    "rtap-item-detail",
    "rtap-quarterly-update-list-create",
    "rtap-quarterly-update-detail",
    "quarterly-report-detail",
    "quarterly-report-workflow-start",
    "quarterly-report-workflow-status",
    "quarterly-report-workflow-history",
    "quarterly-report-workflow-advance",
    "quarterly-report-workflow-cancel",
    "quarterly-report-workflow-recall",
    "quality-auditor-detail",
    "quality-auditor-appointment-list-create",
    "quality-auditor-appointment-detail",
    "qa-appointment-workflow-start",
    "qa-appointment-workflow-status",
    "qa-appointment-workflow-history",
    "qa-appointment-workflow-advance",
    "qa-appointment-workflow-cancel",
    "qa-appointment-workflow-recall",
    "qms-audit-program-detail",
    "qms-program-workflow-start",
    "qms-program-workflow-status",
    "qms-program-workflow-history",
    "qms-program-workflow-advance",
    "qms-program-workflow-cancel",
    "qms-program-workflow-recall",
    "qms-audit-plan-detail",
    "qms-team-assignment-list-create",
    "qms-team-assignment-detail",
    "qms-plan-workflow-start",
    "qms-plan-workflow-status",
    "qms-plan-workflow-history",
    "qms-plan-workflow-advance",
    "qms-plan-workflow-cancel",
    "qms-plan-workflow-recall",
    "audit-checklist-detail",
    "qms-audit-report-detail",
    "qms-audit-report-sign-tl",
    "qms-audit-report-sign-auditee",
    "non-conformance-detail",
    "risk-meeting-detail",
    "meeting-attendance-list-create",
    "meeting-attendance-detail",
    "qa-training-session-detail",
    "qa-training-attendee-list-create",
    "qa-training-attendee-detail",
    "qms-audit-meeting-list-create",
    "qms-audit-meeting-detail",
    "qms-timetable-entry-list-create",
    "qms-timetable-entry-detail",
]

ALL_URL_NAMES_WITHOUT_PK = [
    "risk-dashboard",
    "risk-dashboard-comparative",
    "risk-champion-list-create",
    "risk-assessment-sheet-list-create",
    "dept-risk-register-list-create",
    "inst-risk-register-list-create",
    "rtap-list-create",
    "rtap-item-list-create",
    "quarterly-report-list-create",
    "quality-auditor-list-create",
    "qms-audit-program-list-create",
    "qms-audit-plan-list-create",
    "audit-checklist-list-create",
    "qms-audit-report-list-create",
    "non-conformance-list-create",
    "risk-meeting-list-create",
    "qa-training-session-list-create",
]


class TestAllURLNamesResolve:
    @pytest.mark.parametrize("url_name", ALL_URL_NAMES_WITH_PK)
    def test_url_with_pk_resolves(self, url_name):
        url = reverse(url_name, kwargs={"pk": PK})
        assert url.startswith("/api/v1/grc/risk/")

    @pytest.mark.parametrize("url_name", ALL_URL_NAMES_WITHOUT_PK)
    def test_url_without_pk_resolves(self, url_name):
        url = reverse(url_name)
        assert url.startswith("/api/v1/grc/risk/")
