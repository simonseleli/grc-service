"""
Risk Management Module — View / API endpoint tests (Phase 7).

Tests all 17 view files covering CRUD, workflow, sub-resources,
special endpoints (sign-tl, sign-auditee, dashboard).

Pattern: mirrors tests/legal/test_api_cases.py
"""
import uuid
from unittest.mock import patch, MagicMock

import pytest
from django.urls import reverse

from tests.risk_management.conftest import (
    RMQAM_USER_ID, RC_USER_ID, QA_USER_ID, TL_USER_ID,
    ORG_UNIT_UUID, PLAN_UUID,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Risk Champion Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskChampionListCreateAPI:

    @pytest.mark.django_db
    def test_list_champions_success(self, rmqam_client, risk_champion, allow_all_permissions):
        url = reverse("risk-champion-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_champion_success(self, rmqam_client, allow_all_permissions):
        url = reverse("risk-champion-list-create")
        payload = {
            "org_unit_id": str(ORG_UNIT_UUID),
            "org_unit_type": "directorate",
            "user_id": str(RC_USER_ID),
            "nominated_by": str(RMQAM_USER_ID),
            "term_start": "2025-07-01",
            "term_end": "2026-06-30",
        }
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_list_champions_anon_401(self, anon_client):
        url = reverse("risk-champion-list-create")
        response = anon_client.get(url)
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_list_champions_denied_403(self, rmqam_client, deny_all_permissions):
        url = reverse("risk-champion-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 403


class TestRiskChampionDetailAPI:

    @pytest.mark.django_db
    def test_get_champion(self, rmqam_client, risk_champion, allow_all_permissions):
        url = reverse("risk-champion-detail", args=[risk_champion.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_patch_champion(self, rmqam_client, risk_champion, allow_all_permissions):
        url = reverse("risk-champion-detail", args=[risk_champion.id])
        response = rmqam_client.patch(url, {"qualifications": "Updated"}, format="json")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_champion(self, rmqam_client, risk_champion, allow_all_permissions):
        url = reverse("risk-champion-detail", args=[risk_champion.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 200
        risk_champion.refresh_from_db()
        assert risk_champion.is_active is False

    @pytest.mark.django_db
    def test_get_nonexistent_404(self, rmqam_client, allow_all_permissions):
        url = reverse("risk-champion-detail", args=[uuid.uuid4()])
        response = rmqam_client.get(url)
        assert response.status_code == 404


class TestRiskChampionAppointmentAPI:

    @pytest.mark.django_db
    def test_list_appointments(self, rmqam_client, risk_champion, rc_appointment, allow_all_permissions):
        url = reverse("risk-champion-appointment-list-create", args=[risk_champion.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_create_appointment(self, rmqam_client, risk_champion, allow_all_permissions):
        url = reverse("risk-champion-appointment-list-create", args=[risk_champion.id])
        payload = {"risk_champion_id": str(risk_champion.id), "appointment_date": "2025-08-01", "status": "draft"}
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_get_appointment_detail(self, rmqam_client, rc_appointment, allow_all_permissions):
        url = reverse("risk-champion-appointment-detail", args=[rc_appointment.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestRCAppointmentWorkflowAPI:

    @pytest.mark.django_db
    def test_workflow_start(self, rmqam_client, rc_appointment, allow_all_permissions):
        url = reverse("rc-appointment-workflow-start", args=[rc_appointment.id])
        with patch("apps.api.views.risk_champion_views.RiskChampionAppointmentService") as MockSvc:
            MockSvc.return_value.submit_for_approval.return_value = rc_appointment
            response = rmqam_client.post(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_workflow_status(self, rmqam_client, rc_appointment_with_workflow, allow_all_permissions):
        url = reverse("rc-appointment-workflow-status", args=[rc_appointment_with_workflow.id])
        with patch("apps.api.views.risk_champion_views.RiskChampionAppointmentService") as MockSvc:
            MockSvc.return_value.get_workflow_status.return_value = {"status": "active"}
            response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_workflow_history(self, rmqam_client, rc_appointment_with_workflow, allow_all_permissions):
        url = reverse("rc-appointment-workflow-history", args=[rc_appointment_with_workflow.id])
        with patch("apps.api.views.risk_champion_views.RiskChampionAppointmentService") as MockSvc:
            MockSvc.return_value.get_workflow_history.return_value = []
            response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_workflow_advance(self, rmqam_client, rc_appointment_with_workflow, allow_all_permissions):
        url = reverse("rc-appointment-workflow-advance", args=[rc_appointment_with_workflow.id])
        with patch("apps.api.views.risk_champion_views.RiskChampionAppointmentService") as MockSvc:
            MockSvc.return_value.advance_workflow_stage.return_value = {"status": "completed"}
            response = rmqam_client.post(url, {"action": "approve", "comment": "ok"}, format="json")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_workflow_advance_missing_action_400(self, rmqam_client, rc_appointment_with_workflow, allow_all_permissions):
        url = reverse("rc-appointment-workflow-advance", args=[rc_appointment_with_workflow.id])
        response = rmqam_client.post(url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_workflow_cancel(self, rmqam_client, rc_appointment_with_workflow, allow_all_permissions):
        url = reverse("rc-appointment-workflow-cancel", args=[rc_appointment_with_workflow.id])
        with patch("apps.api.views.risk_champion_views.RiskChampionAppointmentService") as MockSvc:
            MockSvc.return_value.cancel_workflow_plan.return_value = None
            response = rmqam_client.post(url, {"reason": "test"}, format="json")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Risk Assessment Sheet Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskAssessmentSheetAPI:

    @pytest.mark.django_db
    def test_list_sheets(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("risk-assessment-sheet-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.django_db
    def test_get_sheet_detail(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("risk-assessment-sheet-detail", args=[risk_assessment_sheet.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_sheet(self, rmqam_client, risk_assessment_sheet, allow_all_permissions):
        url = reverse("risk-assessment-sheet-detail", args=[risk_assessment_sheet.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 200
        risk_assessment_sheet.refresh_from_db()
        assert risk_assessment_sheet.is_active is False


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Departmental Risk Register Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeptRiskRegisterAPI:

    @pytest.mark.django_db
    def test_list_registers(self, rmqam_client, dept_register, allow_all_permissions):
        url = reverse("dept-risk-register-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_create_register(self, rmqam_client, fiscal_year, allow_all_permissions):
        url = reverse("dept-risk-register-list-create")
        payload = {
            "org_unit_id": str(ORG_UNIT_UUID),
            "org_unit_type": "directorate",
            "fiscal_year_id": str(fiscal_year.id),
            "status": "draft",
        }
        response = rmqam_client.post(url, payload, format="json")
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_get_register_detail(self, rmqam_client, dept_register, allow_all_permissions):
        url = reverse("dept-risk-register-detail", args=[dept_register.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_register(self, rmqam_client, dept_register, allow_all_permissions):
        url = reverse("dept-risk-register-detail", args=[dept_register.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 200


class TestDeptRegisterEntryAPI:

    @pytest.mark.django_db
    def test_list_entries(self, rmqam_client, dept_register, dept_register_entry, allow_all_permissions):
        url = reverse("dept-register-entry-list-create", args=[dept_register.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_entry_detail(self, rmqam_client, dept_register_entry, allow_all_permissions):
        url = reverse("dept-register-entry-detail", args=[dept_register_entry.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestDeptRegisterWorkflowAPI:

    @pytest.mark.django_db
    def test_workflow_start_requires_entries(self, rmqam_client, dept_register, allow_all_permissions):
        url = reverse("dept-register-workflow-start", args=[dept_register.id])
        response = rmqam_client.post(url)
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_workflow_start_with_entry(self, rmqam_client, dept_register, dept_register_entry, allow_all_permissions):
        url = reverse("dept-register-workflow-start", args=[dept_register.id])
        with patch("apps.api.views.dept_risk_register_views.DeptRiskRegisterService") as MockSvc:
            MockSvc.return_value.submit_for_approval.return_value = dept_register
            response = rmqam_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Institutional Risk Register Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstitutionalRiskRegisterAPI:

    @pytest.mark.django_db
    def test_list_registers(self, rmqam_client, inst_register, allow_all_permissions):
        url = reverse("inst-risk-register-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_register_detail(self, rmqam_client, inst_register, allow_all_permissions):
        url = reverse("inst-risk-register-detail", args=[inst_register.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestInstitutionalRiskEntryAPI:

    @pytest.mark.django_db
    def test_list_entries(self, rmqam_client, inst_register, inst_entry, allow_all_permissions):
        url = reverse("inst-risk-entry-list-create", args=[inst_register.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_entry_detail(self, rmqam_client, inst_entry, allow_all_permissions):
        url = reverse("inst-risk-entry-detail", args=[inst_entry.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestActivityReportAPI:

    @pytest.mark.django_db
    def test_list_activity_reports(self, rmqam_client, inst_register, activity_report, allow_all_permissions):
        url = reverse("inst-activity-report-list-create", args=[inst_register.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_activity_report_detail(self, rmqam_client, activity_report, allow_all_permissions):
        url = reverse("inst-activity-report-detail", args=[activity_report.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 5. RTAP Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestRTAPAPI:

    @pytest.mark.django_db
    def test_list_rtaps(self, rmqam_client, rtap, allow_all_permissions):
        url = reverse("rtap-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_rtap_detail(self, rmqam_client, rtap, allow_all_permissions):
        url = reverse("rtap-detail", args=[rtap.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_rtap_with_items_blocked(self, rmqam_client, rtap, rtap_item, allow_all_permissions):
        url = reverse("rtap-detail", args=[rtap.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 400


class TestRTAPWorkflowAPI:

    @pytest.mark.django_db
    def test_workflow_start(self, rmqam_client, rtap, allow_all_permissions):
        url = reverse("rtap-workflow-start", args=[rtap.id])
        with patch("apps.api.views.risk_treatment_plan_views.RTAPService") as MockSvc:
            MockSvc.return_value.submit_for_approval.return_value = rtap
            response = rmqam_client.post(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_workflow_status(self, rmqam_client, rtap_with_workflow, allow_all_permissions):
        url = reverse("rtap-workflow-status", args=[rtap_with_workflow.id])
        with patch("apps.api.views.risk_treatment_plan_views.RTAPService") as MockSvc:
            MockSvc.return_value.get_workflow_status.return_value = {"status": "active"}
            response = rmqam_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 6. RTAP Item Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestRTAPItemAPI:

    @pytest.mark.django_db
    def test_list_rtap_items(self, rmqam_client, rtap_item, allow_all_permissions):
        url = reverse("rtap-item-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_item_detail(self, rmqam_client, rtap_item, allow_all_permissions):
        url = reverse("rtap-item-detail", args=[rtap_item.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_item(self, rmqam_client, rtap_item, allow_all_permissions):
        url = reverse("rtap-item-detail", args=[rtap_item.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 200


class TestRTAPQuarterlyUpdateAPI:

    @pytest.mark.django_db
    def test_list_updates(self, rmqam_client, rtap_item, rtap_quarterly_update, allow_all_permissions):
        url = reverse("rtap-quarterly-update-list-create", args=[rtap_item.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_update_detail(self, rmqam_client, rtap_quarterly_update, allow_all_permissions):
        url = reverse("rtap-quarterly-update-detail", args=[rtap_quarterly_update.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Quarterly Performance Report Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuarterlyReportAPI:

    @pytest.mark.django_db
    def test_list_reports(self, rmqam_client, quarterly_report, allow_all_permissions):
        url = reverse("quarterly-report-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_report_detail(self, rmqam_client, quarterly_report, allow_all_permissions):
        url = reverse("quarterly-report-detail", args=[quarterly_report.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_workflow_start(self, rmqam_client, quarterly_report, allow_all_permissions):
        url = reverse("quarterly-report-workflow-start", args=[quarterly_report.id])
        with patch("apps.api.views.quarterly_risk_report_views.QuarterlyRiskReportService") as MockSvc:
            MockSvc.return_value.submit_for_approval.return_value = quarterly_report
            response = rmqam_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Quality Auditor Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityAuditorAPI:

    @pytest.mark.django_db
    def test_list_auditors(self, rmqam_client, quality_auditor, allow_all_permissions):
        url = reverse("quality-auditor-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_auditor_detail(self, rmqam_client, quality_auditor, allow_all_permissions):
        url = reverse("quality-auditor-detail", args=[quality_auditor.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_auditor(self, rmqam_client, quality_auditor, allow_all_permissions):
        url = reverse("quality-auditor-detail", args=[quality_auditor.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 200


class TestQAAppointmentAPI:

    @pytest.mark.django_db
    def test_list_appointments(self, rmqam_client, quality_auditor, qa_appointment, allow_all_permissions):
        url = reverse("quality-auditor-appointment-list-create", args=[quality_auditor.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_appointment_detail(self, rmqam_client, qa_appointment, allow_all_permissions):
        url = reverse("quality-auditor-appointment-detail", args=[qa_appointment.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestQAAppointmentWorkflowAPI:

    @pytest.mark.django_db
    def test_workflow_start(self, rmqam_client, qa_appointment, allow_all_permissions):
        url = reverse("qa-appointment-workflow-start", args=[qa_appointment.id])
        with patch("apps.api.views.quality_auditor_views.QualityAuditorAppointmentService") as MockSvc:
            MockSvc.return_value.submit_for_approval.return_value = qa_appointment
            response = rmqam_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 9. QMS Audit Program Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestQMSAuditProgramAPI:

    @pytest.mark.django_db
    def test_list_programs(self, rmqam_client, qms_program, allow_all_permissions):
        url = reverse("qms-audit-program-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_program_detail(self, rmqam_client, qms_program, allow_all_permissions):
        url = reverse("qms-audit-program-detail", args=[qms_program.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_program(self, rmqam_client, qms_program, allow_all_permissions):
        url = reverse("qms-audit-program-detail", args=[qms_program.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 200


class TestQMSAuditProgramWorkflowAPI:

    @pytest.mark.django_db
    def test_workflow_start(self, rmqam_client, qms_program_draft, allow_all_permissions):
        url = reverse("qms-program-workflow-start", args=[qms_program_draft.id])
        with patch("apps.api.views.qms_audit_program_views.QMSAuditProgramService") as MockSvc:
            MockSvc.return_value.submit_for_approval.return_value = qms_program_draft
            response = rmqam_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 10. QMS Audit Plan Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestQMSAuditPlanAPI:

    @pytest.mark.django_db
    def test_list_plans(self, rmqam_client, qms_plan, allow_all_permissions):
        url = reverse("qms-audit-plan-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_plan_detail(self, rmqam_client, qms_plan, allow_all_permissions):
        url = reverse("qms-audit-plan-detail", args=[qms_plan.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestQMSTeamAssignmentAPI:

    @pytest.mark.django_db
    def test_list_assignments(self, rmqam_client, qms_plan, team_assignment, allow_all_permissions):
        url = reverse("qms-team-assignment-list-create", args=[qms_plan.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_assignment_detail(self, rmqam_client, team_assignment, allow_all_permissions):
        url = reverse("qms-team-assignment-detail", args=[team_assignment.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestQMSAuditPlanWorkflowAPI:

    @pytest.mark.django_db
    def test_workflow_start_requires_team(self, rmqam_client, qms_plan_draft, allow_all_permissions):
        url = reverse("qms-plan-workflow-start", args=[qms_plan_draft.id])
        response = rmqam_client.post(url)
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_workflow_start_with_team(self, rmqam_client, qms_plan_draft, allow_all_permissions):
        from apps.core.models.risk_entities import QMSAuditTeamAssignment
        QMSAuditTeamAssignment.objects.create(
            audit_plan=qms_plan_draft, auditor_id=QA_USER_ID,
            role='team_leader', created_by=RMQAM_USER_ID,
        )
        url = reverse("qms-plan-workflow-start", args=[qms_plan_draft.id])
        with patch("apps.api.views.qms_audit_plan_views.QMSAuditPlanService") as MockSvc:
            MockSvc.return_value.submit_for_approval.return_value = qms_plan_draft
            response = rmqam_client.post(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Audit Checklist Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditChecklistAPI:

    @pytest.mark.django_db
    def test_list_checklists(self, rmqam_client, audit_checklist, allow_all_permissions):
        url = reverse("audit-checklist-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_checklist_detail(self, rmqam_client, audit_checklist, allow_all_permissions):
        url = reverse("audit-checklist-detail", args=[audit_checklist.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 12. QMS Audit Report + Signing Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestQMSAuditReportAPI:

    @pytest.mark.django_db
    def test_list_reports(self, rmqam_client, qms_report, allow_all_permissions):
        url = reverse("qms-audit-report-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_report_detail(self, rmqam_client, qms_report, allow_all_permissions):
        url = reverse("qms-audit-report-detail", args=[qms_report.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestQMSAuditReportSigningAPI:

    @pytest.mark.django_db
    def test_sign_tl(self, rmqam_client, qms_report, allow_all_permissions):
        url = reverse("qms-audit-report-sign-tl", args=[qms_report.id])
        response = rmqam_client.post(url)
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.tl_signed_by is not None

    @pytest.mark.django_db
    def test_sign_tl_double_sign_400(self, rmqam_client, qms_report, allow_all_permissions):
        qms_report.tl_signed_by = str(TL_USER_ID)
        qms_report.save()
        url = reverse("qms-audit-report-sign-tl", args=[qms_report.id])
        response = rmqam_client.post(url)
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_sign_auditee(self, rmqam_client, qms_report, allow_all_permissions):
        url = reverse("qms-audit-report-sign-auditee", args=[qms_report.id])
        response = rmqam_client.post(url)
        assert response.status_code == 200
        qms_report.refresh_from_db()
        assert qms_report.auditee_signed_by is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Non-Conformance Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestNonConformanceAPI:

    @pytest.mark.django_db
    def test_list_ncs(self, rmqam_client, nonconformance, allow_all_permissions):
        url = reverse("non-conformance-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_nc_detail(self, rmqam_client, nonconformance, allow_all_permissions):
        url = reverse("non-conformance-detail", args=[nonconformance.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_invalid_status_transition_400(self, rmqam_client, nonconformance, allow_all_permissions):
        nonconformance.status = 'closed'
        nonconformance.save()
        url = reverse("non-conformance-detail", args=[nonconformance.id])
        response = rmqam_client.patch(url, {"status": "open"}, format="json")
        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Risk Dashboard Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskDashboardAPI:

    @pytest.mark.django_db
    def test_dashboard(self, rmqam_client, allow_all_permissions):
        url = reverse("risk-dashboard")
        response = rmqam_client.get(url)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "assessments" in response.json()["data"]

    @pytest.mark.django_db
    def test_comparative_analysis(self, rmqam_client, allow_all_permissions):
        url = reverse("risk-dashboard-comparative")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_dashboard_denied_403(self, rmqam_client, deny_all_permissions):
        url = reverse("risk-dashboard")
        response = rmqam_client.get(url)
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Risk Meeting Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskMeetingAPI:

    @pytest.mark.django_db
    def test_list_meetings(self, rmqam_client, risk_meeting, allow_all_permissions):
        url = reverse("risk-meeting-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_meeting_detail(self, rmqam_client, risk_meeting, allow_all_permissions):
        url = reverse("risk-meeting-detail", args=[risk_meeting.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_meeting(self, rmqam_client, risk_meeting, allow_all_permissions):
        url = reverse("risk-meeting-detail", args=[risk_meeting.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 200


class TestMeetingAttendanceAPI:

    @pytest.mark.django_db
    def test_list_attendance(self, rmqam_client, risk_meeting, meeting_attendance, allow_all_permissions):
        url = reverse("meeting-attendance-list-create", args=[risk_meeting.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_attendance_detail(self, rmqam_client, meeting_attendance, allow_all_permissions):
        url = reverse("meeting-attendance-detail", args=[meeting_attendance.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 16. QA Training Views
# ═══════════════════════════════════════════════════════════════════════════════

class TestQATrainingAPI:

    @pytest.mark.django_db
    def test_list_sessions(self, rmqam_client, training_session, allow_all_permissions):
        url = reverse("qa-training-session-list-create")
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_session_detail(self, rmqam_client, training_session, allow_all_permissions):
        url = reverse("qa-training-session-detail", args=[training_session.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_session(self, rmqam_client, training_session, allow_all_permissions):
        url = reverse("qa-training-session-detail", args=[training_session.id])
        response = rmqam_client.delete(url)
        assert response.status_code == 200


class TestQATrainingAttendeeAPI:

    @pytest.mark.django_db
    def test_list_attendees(self, rmqam_client, training_session, training_attendee, allow_all_permissions):
        url = reverse("qa-training-attendee-list-create", args=[training_session.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 17. QMS Audit Support Views (Meetings + Timetable)
# ═══════════════════════════════════════════════════════════════════════════════

class TestQMSAuditMeetingAPI:

    @pytest.mark.django_db
    def test_list_audit_meetings(self, rmqam_client, qms_plan, qms_audit_meeting, allow_all_permissions):
        url = reverse("qms-audit-meeting-list-create", args=[qms_plan.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_audit_meeting_detail(self, rmqam_client, qms_audit_meeting, allow_all_permissions):
        url = reverse("qms-audit-meeting-detail", args=[qms_audit_meeting.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200


class TestQMSAuditTimetableAPI:

    @pytest.mark.django_db
    def test_list_timetable_entries(self, rmqam_client, qms_plan, timetable_entry, allow_all_permissions):
        url = reverse("qms-timetable-entry-list-create", args=[qms_plan.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_timetable_entry_detail(self, rmqam_client, timetable_entry, allow_all_permissions):
        url = reverse("qms-timetable-entry-detail", args=[timetable_entry.id])
        response = rmqam_client.get(url)
        assert response.status_code == 200
