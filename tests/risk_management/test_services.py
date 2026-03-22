"""
Risk Management Module — Service layer tests (Phase 4).

Covers all 8 workflow service classes:
  - RiskChampionAppointmentService   (3-stage: RMO → RMQAM → DG)
  - DeptRiskRegisterService          (2-stage: RC → RMQAM)
  - InstitutionalRiskRegisterService (4-stage governance chain)
  - RTAPService                      (4-stage governance chain)
  - QuarterlyRiskReportService       (5-stage governance chain)
  - QualityAuditorAppointmentService (3-stage: RMO → RMQAM → DG)
  - QMSAuditProgramService           (2-stage: RMO → RMQAM)
  - QMSAuditPlanService              (2-stage: RMO → RMQAM)

Pattern: mirrors tests/legal/test_services.py
"""
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from tests.risk_management.conftest import (
    RMQAM_USER_ID, RC_USER_ID, QA_USER_ID, PLAN_UUID,
)

# ── Module path shortcuts for patching ────────────────────────────────────
RC_APPT_SVC   = "apps.core.services.risk_champion_service"
DEPT_REG_SVC  = "apps.core.services.dept_risk_register_service"
INST_REG_SVC  = "apps.core.services.institutional_risk_register_service"
RTAP_SVC      = "apps.core.services.rtap_service"
QTR_RPT_SVC   = "apps.core.services.quarterly_risk_report_service"
QA_APPT_SVC   = "apps.core.services.quality_auditor_service"
QMS_PROG_SVC  = "apps.core.services.qms_audit_program_service"
QMS_PLAN_SVC  = "apps.core.services.qms_audit_plan_service"


# ── Fake result objects ───────────────────────────────────────────────────

@dataclass
class FakeWorkflowPlanResult:
    plan_id: str
    status: str
    current_stage_id: Optional[str]
    current_stage_name: Optional[str]
    stages: List[Dict[str, Any]]
    metadata: Dict[str, Any]


@dataclass
class FakeAdvanceResult:
    new_status: str
    plan_status: str
    next_stage_id: Optional[str]
    next_stage_name: Optional[str]


def make_fake_plan_result(plan_id=None, stage_id=None, stage_name="stage_one"):
    return FakeWorkflowPlanResult(
        plan_id=plan_id or str(uuid.uuid4()),
        status="active",
        current_stage_id=stage_id or str(uuid.uuid4()),
        current_stage_name=stage_name,
        stages=[],
        metadata={},
    )


def make_fake_advance_result(next_stage_name="stage_two", plan_status="active"):
    return FakeAdvanceResult(
        new_status="completed",
        plan_status=plan_status,
        next_stage_id=str(uuid.uuid4()),
        next_stage_name=next_stage_name,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. RiskChampionAppointmentService
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskChampionAppointmentService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_mixin_fields(self, rc_appointment):
        fake_plan_id = str(uuid.uuid4())
        fake_stage_id = str(uuid.uuid4())
        fake_result = make_fake_plan_result(
            plan_id=fake_plan_id, stage_id=fake_stage_id, stage_name="rmo_draft",
        )
        with patch(f"{RC_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            entity = RiskChampionAppointmentService().submit_for_approval(
                appointment_id=str(rc_appointment.id), submitter_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert str(entity.workflow_plan_id) == fake_plan_id
        assert entity.workflow_stage == "rmo_draft"
        assert str(entity.workflow_stage_id) == fake_stage_id
        assert entity.workflow_started_at is not None
        assert entity.workflow_completed_at is None

    @pytest.mark.django_db
    def test_submit_sets_status_to_submitted(self, rc_appointment):
        fake_result = make_fake_plan_result()
        with patch(f"{RC_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            entity = RiskChampionAppointmentService().submit_for_approval(
                appointment_id=str(rc_appointment.id), submitter_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.status == "submitted"

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, rc_appointment):
        fake_result = make_fake_plan_result()
        with patch(f"{RC_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            RiskChampionAppointmentService().submit_for_approval(
                appointment_id=str(rc_appointment.id), submitter_id=str(RMQAM_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.risk_champion_appointment"

    @pytest.mark.django_db
    def test_submit_idempotent_with_existing_plan(self, rc_appointment_with_workflow):
        with patch(f"{RC_APPT_SVC}.OrchestrationClient") as MockClient:
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            entity = RiskChampionAppointmentService().submit_for_approval(
                appointment_id=str(rc_appointment_with_workflow.id),
                submitter_id=str(RMQAM_USER_ID),
            )
        MockClient.return_value.start_workflow.assert_not_called()
        assert str(entity.workflow_plan_id) == str(PLAN_UUID)

    @pytest.mark.django_db
    def test_get_workflow_status_no_plan(self, rc_appointment):
        with patch(f"{RC_APPT_SVC}.OrchestrationClient"):
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            result = RiskChampionAppointmentService().get_workflow_status(
                appointment_id=str(rc_appointment.id),
            )
        assert result is None

    @pytest.mark.django_db
    def test_get_workflow_status_with_plan(self, rc_appointment_with_workflow):
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        with patch(f"{RC_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            result = RiskChampionAppointmentService().get_workflow_status(
                appointment_id=str(rc_appointment_with_workflow.id),
            )
        assert result["has_workflow"] is True
        assert result["plan_id"] == str(PLAN_UUID)

    @pytest.mark.django_db
    def test_get_workflow_history_no_plan(self, rc_appointment):
        with patch(f"{RC_APPT_SVC}.OrchestrationClient"):
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            result = RiskChampionAppointmentService().get_workflow_history(
                appointment_id=str(rc_appointment.id),
            )
        assert result == []

    @pytest.mark.django_db
    def test_advance_workflow_stage(self, rc_appointment_with_workflow):
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(next_stage_name="rmqam_review")
        with patch(f"{RC_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            result = RiskChampionAppointmentService().advance_workflow_stage(
                appointment_id=str(rc_appointment_with_workflow.id),
                action="submit_for_review", actor_id=str(RMQAM_USER_ID),
            )
        assert result["action"] == "submit_for_review"
        assert result["next_stage"] == "rmqam_review"

    @pytest.mark.django_db
    def test_advance_no_workflow_raises(self, rc_appointment):
        with patch(f"{RC_APPT_SVC}.OrchestrationClient"):
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            with pytest.raises(ValueError, match="No active workflow"):
                RiskChampionAppointmentService().advance_workflow_stage(
                    appointment_id=str(rc_appointment.id),
                    action="approve", actor_id=str(RMQAM_USER_ID),
                )

    @pytest.mark.django_db
    def test_cancel_workflow(self, rc_appointment_with_workflow):
        with patch(f"{RC_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            entity = RiskChampionAppointmentService().cancel_workflow_plan(
                appointment_id=str(rc_appointment_with_workflow.id),
                actor_id=str(RMQAM_USER_ID), reason="Test cancellation",
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None

    @pytest.mark.django_db
    def test_cancel_no_workflow_raises(self, rc_appointment):
        with patch(f"{RC_APPT_SVC}.OrchestrationClient"):
            from apps.core.services.risk_champion_service import RiskChampionAppointmentService
            with pytest.raises(ValueError, match="No active workflow"):
                RiskChampionAppointmentService().cancel_workflow_plan(
                    appointment_id=str(rc_appointment.id),
                    actor_id=str(RMQAM_USER_ID),
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DeptRiskRegisterService
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeptRiskRegisterService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_fields(self, dept_register):
        fake_plan_id = str(uuid.uuid4())
        fake_result = make_fake_plan_result(plan_id=fake_plan_id, stage_name="rc_submit")
        with patch(f"{DEPT_REG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.dept_risk_register_service import DeptRiskRegisterService
            entity = DeptRiskRegisterService().submit_for_approval(
                register_id=str(dept_register.id), submitter_id=str(RC_USER_ID),
            )
        entity.refresh_from_db()
        assert str(entity.workflow_plan_id) == fake_plan_id
        assert entity.status == "submitted"
        assert entity.workflow_started_at is not None

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, dept_register):
        fake_result = make_fake_plan_result()
        with patch(f"{DEPT_REG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.dept_risk_register_service import DeptRiskRegisterService
            DeptRiskRegisterService().submit_for_approval(
                register_id=str(dept_register.id), submitter_id=str(RC_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.dept_risk_register_approval"

    @pytest.mark.django_db
    def test_submit_idempotent(self, dept_register_with_workflow):
        with patch(f"{DEPT_REG_SVC}.OrchestrationClient") as MockClient:
            from apps.core.services.dept_risk_register_service import DeptRiskRegisterService
            DeptRiskRegisterService().submit_for_approval(
                register_id=str(dept_register_with_workflow.id),
                submitter_id=str(RC_USER_ID),
            )
        MockClient.return_value.start_workflow.assert_not_called()

    @pytest.mark.django_db
    def test_advance_workflow(self, dept_register_with_workflow):
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(next_stage_name="rmqam_approve")
        with patch(f"{DEPT_REG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.dept_risk_register_service import DeptRiskRegisterService
            result = DeptRiskRegisterService().advance_workflow_stage(
                register_id=str(dept_register_with_workflow.id),
                action="submit", actor_id=str(RC_USER_ID),
            )
        assert result["next_stage"] == "rmqam_approve"

    @pytest.mark.django_db
    def test_cancel_workflow(self, dept_register_with_workflow):
        with patch(f"{DEPT_REG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.dept_risk_register_service import DeptRiskRegisterService
            entity = DeptRiskRegisterService().cancel_workflow_plan(
                register_id=str(dept_register_with_workflow.id),
                actor_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. InstitutionalRiskRegisterService
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstitutionalRiskRegisterService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_fields(self, inst_register):
        fake_result = make_fake_plan_result(stage_name="rmqam_review")
        with patch(f"{INST_REG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.institutional_risk_register_service import InstitutionalRiskRegisterService
            entity = InstitutionalRiskRegisterService().submit_for_approval(
                register_id=str(inst_register.id), submitter_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.status == "rmqam_review"
        assert entity.workflow_started_at is not None

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, inst_register):
        fake_result = make_fake_plan_result()
        with patch(f"{INST_REG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.institutional_risk_register_service import InstitutionalRiskRegisterService
            InstitutionalRiskRegisterService().submit_for_approval(
                register_id=str(inst_register.id), submitter_id=str(RMQAM_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.institutional_risk_register_approval"

    @pytest.mark.django_db
    def test_advance_4_stage_chain(self, inst_register_with_workflow):
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(next_stage_name="management_discussion")
        with patch(f"{INST_REG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.institutional_risk_register_service import InstitutionalRiskRegisterService
            result = InstitutionalRiskRegisterService().advance_workflow_stage(
                register_id=str(inst_register_with_workflow.id),
                action="forward_management", actor_id=str(RMQAM_USER_ID),
            )
        assert result["next_stage"] == "management_discussion"

    @pytest.mark.django_db
    def test_advance_completes_workflow(self, inst_register_with_workflow):
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(plan_status="completed")
        with patch(f"{INST_REG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.institutional_risk_register_service import InstitutionalRiskRegisterService
            InstitutionalRiskRegisterService().advance_workflow_stage(
                register_id=str(inst_register_with_workflow.id),
                action="approve", actor_id=str(RMQAM_USER_ID),
            )
        inst_register_with_workflow.refresh_from_db()
        assert inst_register_with_workflow.workflow_completed_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RTAPService
# ═══════════════════════════════════════════════════════════════════════════════

class TestRTAPService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_fields(self, rtap):
        fake_result = make_fake_plan_result(stage_name="rmqam_review")
        with patch(f"{RTAP_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.rtap_service import RTAPService
            entity = RTAPService().submit_for_approval(
                rtap_id=str(rtap.id), submitter_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.status == "rmqam_review"
        assert entity.workflow_started_at is not None

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, rtap):
        fake_result = make_fake_plan_result()
        with patch(f"{RTAP_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.rtap_service import RTAPService
            RTAPService().submit_for_approval(
                rtap_id=str(rtap.id), submitter_id=str(RMQAM_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.rtap_approval"

    @pytest.mark.django_db
    def test_advance_workflow(self, rtap_with_workflow):
        fake_plan = make_fake_plan_result()
        fake_advance = make_fake_advance_result(next_stage_name="management_discussion")
        with patch(f"{RTAP_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.rtap_service import RTAPService
            result = RTAPService().advance_workflow_stage(
                rtap_id=str(rtap_with_workflow.id),
                action="forward_management", actor_id=str(RMQAM_USER_ID),
            )
        assert result["next_stage"] == "management_discussion"

    @pytest.mark.django_db
    def test_cancel_workflow(self, rtap_with_workflow):
        with patch(f"{RTAP_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.rtap_service import RTAPService
            entity = RTAPService().cancel_workflow_plan(
                rtap_id=str(rtap_with_workflow.id), actor_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 5. QuarterlyRiskReportService
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuarterlyRiskReportService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_fields(self, quarterly_report):
        fake_result = make_fake_plan_result(stage_name="rmqam_prepare")
        with patch(f"{QTR_RPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.quarterly_risk_report_service import QuarterlyRiskReportService
            entity = QuarterlyRiskReportService().submit_for_approval(
                report_id=str(quarterly_report.id), submitter_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.status == "rmqam_prepare"
        assert entity.workflow_started_at is not None

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, quarterly_report):
        fake_result = make_fake_plan_result()
        with patch(f"{QTR_RPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.quarterly_risk_report_service import QuarterlyRiskReportService
            QuarterlyRiskReportService().submit_for_approval(
                report_id=str(quarterly_report.id), submitter_id=str(RMQAM_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.quarterly_risk_report_approval"

    @pytest.mark.django_db
    def test_advance_5_stage_chain(self, quarterly_report_with_workflow):
        fake_plan = make_fake_plan_result()
        fake_advance = make_fake_advance_result(next_stage_name="lsm_submit")
        with patch(f"{QTR_RPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.quarterly_risk_report_service import QuarterlyRiskReportService
            result = QuarterlyRiskReportService().advance_workflow_stage(
                report_id=str(quarterly_report_with_workflow.id),
                action="submit_lsm", actor_id=str(RMQAM_USER_ID),
            )
        assert result["next_stage"] == "lsm_submit"

    @pytest.mark.django_db
    def test_get_status_no_plan(self, quarterly_report):
        with patch(f"{QTR_RPT_SVC}.OrchestrationClient"):
            from apps.core.services.quarterly_risk_report_service import QuarterlyRiskReportService
            result = QuarterlyRiskReportService().get_workflow_status(
                report_id=str(quarterly_report.id),
            )
        assert result is None

    @pytest.mark.django_db
    def test_cancel_no_workflow_raises(self, quarterly_report):
        with patch(f"{QTR_RPT_SVC}.OrchestrationClient"):
            from apps.core.services.quarterly_risk_report_service import QuarterlyRiskReportService
            with pytest.raises(ValueError, match="No active workflow"):
                QuarterlyRiskReportService().cancel_workflow_plan(
                    report_id=str(quarterly_report.id),
                    actor_id=str(RMQAM_USER_ID),
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. QualityAuditorAppointmentService
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityAuditorAppointmentService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_fields(self, qa_appointment):
        fake_plan_id = str(uuid.uuid4())
        fake_result = make_fake_plan_result(plan_id=fake_plan_id, stage_name="rmo_draft")
        with patch(f"{QA_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.quality_auditor_service import QualityAuditorAppointmentService
            entity = QualityAuditorAppointmentService().submit_for_approval(
                appointment_id=str(qa_appointment.id), submitter_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert str(entity.workflow_plan_id) == fake_plan_id
        assert entity.status == "submitted"

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, qa_appointment):
        fake_result = make_fake_plan_result()
        with patch(f"{QA_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.quality_auditor_service import QualityAuditorAppointmentService
            QualityAuditorAppointmentService().submit_for_approval(
                appointment_id=str(qa_appointment.id), submitter_id=str(RMQAM_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.qa_appointment"

    @pytest.mark.django_db
    def test_submit_idempotent(self, qa_appointment_with_workflow):
        with patch(f"{QA_APPT_SVC}.OrchestrationClient") as MockClient:
            from apps.core.services.quality_auditor_service import QualityAuditorAppointmentService
            QualityAuditorAppointmentService().submit_for_approval(
                appointment_id=str(qa_appointment_with_workflow.id),
                submitter_id=str(RMQAM_USER_ID),
            )
        MockClient.return_value.start_workflow.assert_not_called()

    @pytest.mark.django_db
    def test_advance_workflow(self, qa_appointment_with_workflow):
        fake_plan = make_fake_plan_result(plan_id=str(PLAN_UUID))
        fake_advance = make_fake_advance_result(next_stage_name="rmqam_review")
        with patch(f"{QA_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.quality_auditor_service import QualityAuditorAppointmentService
            result = QualityAuditorAppointmentService().advance_workflow_stage(
                appointment_id=str(qa_appointment_with_workflow.id),
                action="submit_for_review", actor_id=str(RMQAM_USER_ID),
            )
        assert result["next_stage"] == "rmqam_review"

    @pytest.mark.django_db
    def test_cancel_workflow(self, qa_appointment_with_workflow):
        with patch(f"{QA_APPT_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.quality_auditor_service import QualityAuditorAppointmentService
            entity = QualityAuditorAppointmentService().cancel_workflow_plan(
                appointment_id=str(qa_appointment_with_workflow.id),
                actor_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 7. QMSAuditProgramService
# ═══════════════════════════════════════════════════════════════════════════════

class TestQMSAuditProgramService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_fields(self, qms_program_draft):
        fake_result = make_fake_plan_result(stage_name="rmo_submit")
        with patch(f"{QMS_PROG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.qms_audit_program_service import QMSAuditProgramService
            entity = QMSAuditProgramService().submit_for_approval(
                program_id=str(qms_program_draft.id), submitter_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.status == "submitted"
        assert entity.workflow_started_at is not None

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, qms_program_draft):
        fake_result = make_fake_plan_result()
        with patch(f"{QMS_PROG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.qms_audit_program_service import QMSAuditProgramService
            QMSAuditProgramService().submit_for_approval(
                program_id=str(qms_program_draft.id), submitter_id=str(RMQAM_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.qms_audit_program_approval"

    @pytest.mark.django_db
    def test_submit_idempotent(self, qms_program_with_workflow):
        with patch(f"{QMS_PROG_SVC}.OrchestrationClient") as MockClient:
            from apps.core.services.qms_audit_program_service import QMSAuditProgramService
            QMSAuditProgramService().submit_for_approval(
                program_id=str(qms_program_with_workflow.id),
                submitter_id=str(RMQAM_USER_ID),
            )
        MockClient.return_value.start_workflow.assert_not_called()

    @pytest.mark.django_db
    def test_advance_workflow(self, qms_program_with_workflow):
        fake_plan = make_fake_plan_result()
        fake_advance = make_fake_advance_result(next_stage_name="rmqam_approve")
        with patch(f"{QMS_PROG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.qms_audit_program_service import QMSAuditProgramService
            result = QMSAuditProgramService().advance_workflow_stage(
                program_id=str(qms_program_with_workflow.id),
                action="submit", actor_id=str(RMQAM_USER_ID),
            )
        assert result["next_stage"] == "rmqam_approve"

    @pytest.mark.django_db
    def test_cancel_workflow(self, qms_program_with_workflow):
        with patch(f"{QMS_PROG_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.qms_audit_program_service import QMSAuditProgramService
            entity = QMSAuditProgramService().cancel_workflow_plan(
                program_id=str(qms_program_with_workflow.id),
                actor_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 8. QMSAuditPlanService
# ═══════════════════════════════════════════════════════════════════════════════

class TestQMSAuditPlanService:

    @pytest.mark.django_db
    def test_submit_saves_workflow_fields(self, qms_plan_draft):
        fake_result = make_fake_plan_result(stage_name="rmo_submit")
        with patch(f"{QMS_PLAN_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.qms_audit_plan_service import QMSAuditPlanService
            entity = QMSAuditPlanService().submit_for_approval(
                plan_id=str(qms_plan_draft.id), submitter_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.status == "submitted"
        assert entity.workflow_started_at is not None

    @pytest.mark.django_db
    def test_submit_uses_correct_template_code(self, qms_plan_draft):
        fake_result = make_fake_plan_result()
        with patch(f"{QMS_PLAN_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.start_workflow.return_value = fake_result
            from apps.core.services.qms_audit_plan_service import QMSAuditPlanService
            QMSAuditPlanService().submit_for_approval(
                plan_id=str(qms_plan_draft.id), submitter_id=str(RMQAM_USER_ID),
            )
        call_kw = MockClient.return_value.start_workflow.call_args.kwargs
        assert call_kw["template_code"] == "grc.qms_audit_plan_approval"

    @pytest.mark.django_db
    def test_submit_idempotent(self, qms_plan_with_workflow):
        with patch(f"{QMS_PLAN_SVC}.OrchestrationClient") as MockClient:
            from apps.core.services.qms_audit_plan_service import QMSAuditPlanService
            QMSAuditPlanService().submit_for_approval(
                plan_id=str(qms_plan_with_workflow.id),
                submitter_id=str(RMQAM_USER_ID),
            )
        MockClient.return_value.start_workflow.assert_not_called()

    @pytest.mark.django_db
    def test_advance_workflow(self, qms_plan_with_workflow):
        fake_plan = make_fake_plan_result()
        fake_advance = make_fake_advance_result(next_stage_name="rmqam_approve")
        with patch(f"{QMS_PLAN_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.get_plan.return_value = fake_plan
            MockClient.return_value.advance_stage.return_value = fake_advance
            from apps.core.services.qms_audit_plan_service import QMSAuditPlanService
            result = QMSAuditPlanService().advance_workflow_stage(
                plan_id=str(qms_plan_with_workflow.id),
                action="submit", actor_id=str(RMQAM_USER_ID),
            )
        assert result["next_stage"] == "rmqam_approve"

    @pytest.mark.django_db
    def test_cancel_workflow(self, qms_plan_with_workflow):
        with patch(f"{QMS_PLAN_SVC}.OrchestrationClient") as MockClient:
            MockClient.return_value.cancel_plan.return_value = True
            from apps.core.services.qms_audit_plan_service import QMSAuditPlanService
            entity = QMSAuditPlanService().cancel_workflow_plan(
                plan_id=str(qms_plan_with_workflow.id),
                actor_id=str(RMQAM_USER_ID),
            )
        entity.refresh_from_db()
        assert entity.workflow_completed_at is not None

    @pytest.mark.django_db
    def test_advance_no_workflow_raises(self, qms_plan_draft):
        with patch(f"{QMS_PLAN_SVC}.OrchestrationClient"):
            from apps.core.services.qms_audit_plan_service import QMSAuditPlanService
            with pytest.raises(ValueError, match="No active workflow"):
                QMSAuditPlanService().advance_workflow_stage(
                    plan_id=str(qms_plan_draft.id),
                    action="submit", actor_id=str(RMQAM_USER_ID),
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow YAML Template Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowYAMLTemplates:

    @pytest.fixture(autouse=True)
    def load_yaml(self):
        import yaml
        import os
        yaml_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'apps', 'core', 'workflows', 'workflows.yaml'
        )
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        self.templates = {t['code']: t for t in data['templates']}

    def test_risk_champion_appointment_template_exists(self):
        assert 'grc.risk_champion_appointment' in self.templates

    def test_risk_champion_appointment_has_3_stages(self):
        tpl = self.templates['grc.risk_champion_appointment']
        assert len(tpl['definition']['stages']) == 3

    def test_risk_champion_appointment_stage_order(self):
        stages = self.templates['grc.risk_champion_appointment']['definition']['stages']
        keys = [s['definitionKey'] for s in stages]
        assert keys == ['rmo_draft', 'rmqam_review', 'dg_signature']

    def test_dept_register_template_exists(self):
        assert 'grc.dept_risk_register_approval' in self.templates

    def test_dept_register_has_2_stages(self):
        tpl = self.templates['grc.dept_risk_register_approval']
        assert len(tpl['definition']['stages']) == 2

    def test_institutional_register_template_exists(self):
        assert 'grc.institutional_risk_register_approval' in self.templates

    def test_institutional_register_has_4_stages(self):
        tpl = self.templates['grc.institutional_risk_register_approval']
        assert len(tpl['definition']['stages']) == 4

    def test_institutional_register_stage_order(self):
        stages = self.templates['grc.institutional_risk_register_approval']['definition']['stages']
        keys = [s['definitionKey'] for s in stages]
        assert keys == ['rmqam_review', 'management_discussion', 'committee_review', 'commission_approval']

    def test_rtap_template_exists(self):
        assert 'grc.rtap_approval' in self.templates

    def test_rtap_has_4_stages(self):
        tpl = self.templates['grc.rtap_approval']
        assert len(tpl['definition']['stages']) == 4

    def test_quarterly_report_template_exists(self):
        assert 'grc.quarterly_risk_report_approval' in self.templates

    def test_quarterly_report_has_5_stages(self):
        tpl = self.templates['grc.quarterly_risk_report_approval']
        assert len(tpl['definition']['stages']) == 5

    def test_quarterly_report_stage_order(self):
        stages = self.templates['grc.quarterly_risk_report_approval']['definition']['stages']
        keys = [s['definitionKey'] for s in stages]
        assert keys == ['rmqam_prepare', 'lsm_submit', 'management_discussion', 'committee_review', 'commission_submit']

    def test_qa_appointment_template_exists(self):
        assert 'grc.qa_appointment' in self.templates

    def test_qa_appointment_has_3_stages(self):
        tpl = self.templates['grc.qa_appointment']
        assert len(tpl['definition']['stages']) == 3

    def test_qms_audit_program_template_exists(self):
        assert 'grc.qms_audit_program_approval' in self.templates

    def test_qms_audit_program_has_2_stages(self):
        tpl = self.templates['grc.qms_audit_program_approval']
        assert len(tpl['definition']['stages']) == 2

    def test_qms_audit_plan_template_exists(self):
        assert 'grc.qms_audit_plan_approval' in self.templates

    def test_qms_audit_plan_has_2_stages(self):
        tpl = self.templates['grc.qms_audit_plan_approval']
        assert len(tpl['definition']['stages']) == 2

    def test_all_templates_have_sla(self):
        risk_templates = [
            'grc.risk_champion_appointment', 'grc.dept_risk_register_approval',
            'grc.institutional_risk_register_approval', 'grc.rtap_approval',
            'grc.quarterly_risk_report_approval', 'grc.qa_appointment',
            'grc.qms_audit_program_approval', 'grc.qms_audit_plan_approval',
        ]
        for code in risk_templates:
            tpl = self.templates[code]
            for stage in tpl['definition']['stages']:
                assert 'sla' in stage, f"Stage {stage['definitionKey']} in {code} missing SLA"

    def test_all_templates_have_metadata_status_on_complete(self):
        risk_templates = [
            'grc.risk_champion_appointment', 'grc.dept_risk_register_approval',
            'grc.institutional_risk_register_approval', 'grc.rtap_approval',
            'grc.quarterly_risk_report_approval', 'grc.qa_appointment',
            'grc.qms_audit_program_approval', 'grc.qms_audit_plan_approval',
        ]
        for code in risk_templates:
            tpl = self.templates[code]
            for stage in tpl['definition']['stages']:
                assert 'status_on_complete' in stage.get('metadata', {}), \
                    f"Stage {stage['definitionKey']} in {code} missing metadata.status_on_complete"

    def test_all_nextState_values_are_valid(self):
        """nextState must be 'completed', 'pending', or 'rejected' per WO contract."""
        valid_states = {'completed', 'pending', 'rejected'}
        risk_templates = [
            'grc.risk_champion_appointment', 'grc.dept_risk_register_approval',
            'grc.institutional_risk_register_approval', 'grc.rtap_approval',
            'grc.quarterly_risk_report_approval', 'grc.qa_appointment',
            'grc.qms_audit_program_approval', 'grc.qms_audit_plan_approval',
        ]
        for code in risk_templates:
            tpl = self.templates[code]
            for stage in tpl['definition']['stages']:
                for action in stage.get('actions', []):
                    ns = action.get('nextState')
                    assert ns in valid_states, (
                        f"Action '{action['name']}' in stage '{stage['definitionKey']}' "
                        f"of {code} has invalid nextState='{ns}' "
                        f"(must be one of {valid_states})"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow Entity Paths Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowEntityPaths:

    def test_risk_champion_appointment_path(self):
        from apps.core.workflow_entity_paths import get_entity_detail_path
        assert get_entity_detail_path('risk_champion_appointment') == '/service/grc/risk/champions'

    def test_departmental_risk_register_path(self):
        from apps.core.workflow_entity_paths import get_entity_detail_path
        assert get_entity_detail_path('departmental_risk_register') == '/service/grc/risk/dept-registers'

    def test_institutional_risk_register_path(self):
        from apps.core.workflow_entity_paths import get_entity_detail_path
        assert get_entity_detail_path('institutional_risk_register') == '/service/grc/risk/institutional-registers'

    def test_rtap_path(self):
        from apps.core.workflow_entity_paths import get_entity_detail_path
        assert get_entity_detail_path('risk_treatment_action_plan') == '/service/grc/risk/rtap'

    def test_quarterly_report_path(self):
        from apps.core.workflow_entity_paths import get_entity_detail_path
        assert get_entity_detail_path('quarterly_performance_report') == '/service/grc/risk/quarterly-reports'

    def test_qa_appointment_path(self):
        from apps.core.workflow_entity_paths import get_entity_detail_path
        assert get_entity_detail_path('quality_auditor_appointment') == '/service/grc/risk/quality-auditors'

    def test_qms_program_path(self):
        from apps.core.workflow_entity_paths import get_entity_detail_path
        assert get_entity_detail_path('qms_audit_program') == '/service/grc/risk/qms-programs'

    def test_qms_plan_path(self):
        from apps.core.workflow_entity_paths import get_entity_detail_path
        assert get_entity_detail_path('qms_audit_plan') == '/service/grc/risk/qms-plans'

    def test_add_entity_detail_path_to_metadata(self):
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {'entity_type': 'risk_champion_appointment', 'entity_id': '123'}
        result = add_entity_detail_path_to_metadata(meta, 'risk_champion_appointment')
        assert result['entity_detail_path'] == '/service/grc/risk/champions'
        # Original keys preserved
        assert result['entity_type'] == 'risk_champion_appointment'
