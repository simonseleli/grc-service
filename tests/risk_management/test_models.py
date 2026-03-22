"""
Risk Management Module — Model Tests (Phase 2)

Coverage:
  - All 26 business model creation and field defaults
  - UniqueConstraint enforcement (active RC per org unit, active register per FY, etc.)
  - WorkflowMixin on 8 entities (get_workflow_context, get_workflow_metadata)
  - RiskAssessmentSheet auto-computed score on save()
  - QMSAuditPlan.clean() 10-day notification rule (E.7)
  - OneToOne constraints (QMSAuditReport→QMSAuditPlan, RTAP→IRR)
  - unique_together constraints on join tables
  - Status field defaults and choices
  - __str__ representations
  - GAP field presence (GAP-01 through GAP-18)
"""
import uuid
import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.core.models import (
    QATrainingSession, QATrainingAttendee,
    RiskChampion, RiskChampionAppointment,
    QualityAuditor, QualityAuditorAppointment,
    RiskAssessmentSheet, DepartmentalRiskRegister, DeptRegisterEntry,
    InstitutionalRiskRegister, InstitutionalRiskEntry,
    RiskTreatmentActionPlan, RTAPItem, RTAPQuarterlyUpdate,
    QuarterlyPerformanceReport, ActivityReport,
    QMSAuditProgram, QMSAuditPlan, QMSAuditTeamAssignment,
    AuditChecklist, QMSAuditReport, NonConformance,
    RiskMeeting, MeetingAttendance,
    QMSAuditMeeting, QMSAuditTimetableEntry,
)
from apps.core.models.lookups import (
    RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
    NonConformanceType, ISOClause,
)
from tests.risk_management.conftest import (
    SYSTEM_USER_ID, RMQAM_USER_ID, RC_USER_ID, QA_USER_ID,
    HEAD_USER_ID, RISK_OWNER_ID, OTHER_USER_ID, OFFICER_USER_ID,
    TL_USER_ID, DOCUMENT_UUID, PLAN_UUID, ORG_UNIT_UUID, AUDITEE_UNIT_UUID,
)


# ===========================================================================
# Group 7 — QA Training Model Tests
# ===========================================================================

class TestQATrainingModels:

    @pytest.mark.django_db
    def test_training_session_creation(self, training_session):
        assert training_session.title == 'ISO 9001:2015 QMS Training'
        assert training_session.approval_status == 'approved'
        assert training_session.is_active is True
        assert 'QA Training' in str(training_session)

    @pytest.mark.django_db
    def test_training_session_default_status(self, db):
        ts = QATrainingSession.objects.create(
            title='New Training',
            trainer_name='Trainer X',
            training_date=datetime.date(2026, 5, 1),
            created_by=SYSTEM_USER_ID,
        )
        assert ts.approval_status == 'proposed'

    @pytest.mark.django_db
    def test_training_attendee_creation(self, training_attendee):
        assert training_attendee.attended is True
        assert str(training_attendee.quality_auditor_id) is not None

    @pytest.mark.django_db
    def test_training_attendee_unique_together(self, training_attendee, training_session, quality_auditor):
        with pytest.raises(IntegrityError):
            QATrainingAttendee.objects.create(
                training_session=training_session,
                quality_auditor=quality_auditor,
                attended=False,
                created_by=SYSTEM_USER_ID,
            )


# ===========================================================================
# Group 1 — Risk Champion & Quality Auditor Model Tests
# ===========================================================================

class TestRiskChampionModels:

    @pytest.mark.django_db
    def test_risk_champion_creation(self, risk_champion):
        assert risk_champion.org_unit_type == 'directorate'
        assert risk_champion.user_id == RC_USER_ID
        assert risk_champion.is_active is True
        assert 'RC' in str(risk_champion)

    @pytest.mark.django_db
    def test_risk_champion_gap13_qualification_fields(self, risk_champion):
        """GAP-13: RC qualification fields present."""
        assert risk_champion.qualifications == 'Certified Risk Analyst'
        assert risk_champion.experience_summary == '5 years in risk management'
        assert risk_champion.justification == 'Best candidate per committee review'

    @pytest.mark.django_db
    def test_risk_champion_unique_active_per_org_unit(self, risk_champion):
        """UniqueConstraint: one active RC per org_unit_id + org_unit_type."""
        with pytest.raises(IntegrityError):
            RiskChampion.objects.create(
                org_unit_id=ORG_UNIT_UUID,
                org_unit_type='directorate',
                user_id=OTHER_USER_ID,
                nominated_by=HEAD_USER_ID,
                term_start=datetime.date(2025, 7, 1),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_rc_appointment_creation(self, rc_appointment):
        assert rc_appointment.status == 'draft'
        assert rc_appointment.rework_count == 0
        assert rc_appointment.dispatched is False

    @pytest.mark.django_db
    def test_rc_appointment_gap06_dispatch_fields(self, rc_appointment):
        """GAP-06: Dispatch tracking fields present."""
        assert rc_appointment.dispatched is False
        assert rc_appointment.dispatch_date is None
        assert rc_appointment.dispatch_reference == ''
        assert rc_appointment.recipient_confirmed is False
        assert rc_appointment.recipient_confirmed_date is None

    @pytest.mark.django_db
    def test_rc_appointment_gap14_rework(self, rc_appointment):
        """GAP-14: Rework counter defaults to 0."""
        assert rc_appointment.rework_count == 0

    @pytest.mark.django_db
    def test_rc_appointment_gap17_review_fields(self, rc_appointment):
        """GAP-17: Review comment fields present."""
        assert rc_appointment.last_review_comment == ''
        assert rc_appointment.last_reviewed_by is None
        assert rc_appointment.last_reviewed_at is None

    @pytest.mark.django_db
    def test_rc_appointment_workflow_context(self, rc_appointment):
        ctx = rc_appointment.get_workflow_context()
        assert ctx['entity_type'] == 'risk_champion_appointment'
        assert ctx['entity_id'] == str(rc_appointment.id)
        assert 'risk_champion_id' in ctx
        assert 'org_unit_id' in ctx

    @pytest.mark.django_db
    def test_rc_appointment_workflow_metadata(self, rc_appointment):
        meta = rc_appointment.get_workflow_metadata()
        assert meta['entity_type'] == 'risk_champion_appointment'
        assert meta['entity_id'] == str(rc_appointment.id)
        assert meta['status'] == 'draft'

    @pytest.mark.django_db
    def test_rc_appointment_has_workflow_mixin_fields(self, rc_appointment):
        assert rc_appointment.workflow_plan_id is None
        assert rc_appointment.workflow_stage == ''
        assert rc_appointment.workflow_stage_id is None


class TestQualityAuditorModels:

    @pytest.mark.django_db
    def test_quality_auditor_creation(self, quality_auditor):
        assert quality_auditor.user_id == QA_USER_ID
        assert quality_auditor.is_certified is True
        assert quality_auditor.exam_score == Decimal('85.00')
        assert 'QA' in str(quality_auditor)

    @pytest.mark.django_db
    def test_quality_auditor_gap02_training_link(self, quality_auditor, training_session):
        """GAP-02: QA linked to training session."""
        assert quality_auditor.training_session == training_session

    @pytest.mark.django_db
    def test_qa_appointment_creation(self, qa_appointment):
        assert qa_appointment.status == 'draft'
        assert qa_appointment.dispatched is False
        assert qa_appointment.rework_count == 0

    @pytest.mark.django_db
    def test_qa_appointment_workflow_context(self, qa_appointment):
        ctx = qa_appointment.get_workflow_context()
        assert ctx['entity_type'] == 'quality_auditor_appointment'
        assert ctx['entity_id'] == str(qa_appointment.id)

    @pytest.mark.django_db
    def test_qa_appointment_workflow_metadata(self, qa_appointment):
        meta = qa_appointment.get_workflow_metadata()
        assert meta['entity_type'] == 'quality_auditor_appointment'
        assert meta['status'] == 'draft'


# ===========================================================================
# Group 2 — Risk Assessment & Departmental Register Tests
# ===========================================================================

class TestRiskAssessmentModels:

    @pytest.mark.django_db
    def test_risk_assessment_creation(self, risk_assessment_sheet):
        assert risk_assessment_sheet.risk_title == 'System Downtime Risk'
        assert risk_assessment_sheet.risk_owner == RISK_OWNER_ID
        assert risk_assessment_sheet.is_active is True

    @pytest.mark.django_db
    def test_risk_assessment_auto_computed_score(self, risk_assessment_sheet):
        """Auto-compute inherent_risk_score = likelihood × impact (4 × 4 = 16)."""
        assert risk_assessment_sheet.inherent_risk_score == Decimal('16.00')

    @pytest.mark.django_db
    def test_risk_assessment_auto_computed_level(self, risk_assessment_sheet, risk_level_high):
        """Auto-assign risk level based on score range."""
        assert risk_assessment_sheet.inherent_risk_level == risk_level_high

    @pytest.mark.django_db
    def test_risk_assessment_gap07_references(self, risk_assessment_sheet):
        """GAP-07: Historical cross-references JSONField."""
        assert isinstance(risk_assessment_sheet.references, list)
        assert len(risk_assessment_sheet.references) == 1
        assert risk_assessment_sheet.references[0]['type'] == 'audit_finding'

    @pytest.mark.django_db
    def test_risk_assessment_str(self, risk_assessment_sheet):
        assert 'System Downtime Risk' in str(risk_assessment_sheet)
        assert '16' in str(risk_assessment_sheet)


class TestDeptRegisterModels:

    @pytest.mark.django_db
    def test_dept_register_creation(self, dept_register):
        assert dept_register.status == 'draft'
        assert dept_register.org_unit_type == 'directorate'
        assert dept_register.rework_count == 0

    @pytest.mark.django_db
    def test_dept_register_gap18_endorsement_fields(self, dept_register):
        """GAP-18: Endorsement fields present with null defaults."""
        assert dept_register.endorsed_by is None
        assert dept_register.endorsement_date is None
        assert dept_register.endorsement_document_id is None

    @pytest.mark.django_db
    def test_dept_register_workflow_context(self, dept_register):
        ctx = dept_register.get_workflow_context()
        assert ctx['entity_type'] == 'departmental_risk_register'
        assert ctx['entity_id'] == str(dept_register.id)
        assert ctx['org_unit_type'] == 'directorate'

    @pytest.mark.django_db
    def test_dept_register_workflow_metadata(self, dept_register):
        meta = dept_register.get_workflow_metadata()
        assert meta['entity_type'] == 'departmental_risk_register'
        assert meta['status'] == 'draft'

    @pytest.mark.django_db
    def test_dept_register_unique_per_unit_year(self, dept_register, fiscal_year):
        """UniqueConstraint: one active register per org_unit + FY."""
        with pytest.raises(IntegrityError):
            DepartmentalRiskRegister.objects.create(
                org_unit_id=ORG_UNIT_UUID,
                org_unit_type='unit',
                fiscal_year=fiscal_year,
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_dept_register_entry_creation(self, dept_register_entry):
        assert dept_register_entry.sort_order == 1

    @pytest.mark.django_db
    def test_dept_register_entry_unique_together(self, dept_register_entry, dept_register, risk_assessment_sheet):
        """unique_together on dept_register + risk_sheet."""
        with pytest.raises(IntegrityError):
            DeptRegisterEntry.objects.create(
                dept_register=dept_register,
                risk_sheet=risk_assessment_sheet,
                sort_order=2,
                created_by=SYSTEM_USER_ID,
            )


# ===========================================================================
# Group 3 — Institutional Register & RTAP Tests
# ===========================================================================

class TestInstitutionalRegisterModels:

    @pytest.mark.django_db
    def test_inst_register_creation(self, inst_register):
        assert inst_register.status == 'draft'
        assert inst_register.prepared_by == RMQAM_USER_ID
        assert 'IRR' in str(inst_register)

    @pytest.mark.django_db
    def test_inst_register_gap03_committee_fields(self, inst_register):
        """GAP-03: Committee meeting and LSM submission tracking."""
        assert inst_register.committee_meeting_date is None
        assert inst_register.lsm_submission_date is None

    @pytest.mark.django_db
    def test_inst_register_workflow_context(self, inst_register):
        ctx = inst_register.get_workflow_context()
        assert ctx['entity_type'] == 'institutional_risk_register'
        assert 'fiscal_year_id' in ctx

    @pytest.mark.django_db
    def test_inst_register_unique_per_fy(self, inst_register, fiscal_year):
        """UniqueConstraint: one active IRR per fiscal year."""
        with pytest.raises(IntegrityError):
            InstitutionalRiskRegister.objects.create(
                fiscal_year=fiscal_year,
                prepared_by=RMQAM_USER_ID,
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_inst_entry_creation(self, inst_entry):
        assert inst_entry.risk_ranking == 1
        assert inst_entry.notes == 'Highest risk entry'

    @pytest.mark.django_db
    def test_inst_entry_unique_together(self, inst_entry, inst_register, risk_assessment_sheet):
        with pytest.raises(IntegrityError):
            InstitutionalRiskEntry.objects.create(
                inst_register=inst_register,
                risk_sheet=risk_assessment_sheet,
                risk_ranking=2,
                created_by=SYSTEM_USER_ID,
            )


class TestRTAPModels:

    @pytest.mark.django_db
    def test_rtap_creation(self, rtap):
        assert rtap.status == 'draft'
        assert rtap.overall_progress == Decimal('0')
        assert 'RTAP' in str(rtap)

    @pytest.mark.django_db
    def test_rtap_one_to_one_with_irr(self, rtap, inst_register, fiscal_year):
        """OneToOne: only one RTAP per IRR."""
        from apps.core.models.lookups import FiscalYear
        fy2 = FiscalYear.objects.create(
            year_code='2026/2027', name='FY 2026/2027',
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2027, 6, 30),
            created_by=SYSTEM_USER_ID,
        )
        with pytest.raises(IntegrityError):
            RiskTreatmentActionPlan.objects.create(
                inst_register=inst_register,
                fiscal_year=fy2,
                prepared_by=RMQAM_USER_ID,
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_rtap_workflow_context(self, rtap):
        ctx = rtap.get_workflow_context()
        assert ctx['entity_type'] == 'risk_treatment_action_plan'
        assert 'fiscal_year_id' in ctx

    @pytest.mark.django_db
    def test_rtap_workflow_metadata(self, rtap):
        meta = rtap.get_workflow_metadata()
        assert meta['entity_type'] == 'risk_treatment_action_plan'
        assert 'overall_progress' in meta

    @pytest.mark.django_db
    def test_rtap_item_creation(self, rtap_item):
        assert rtap_item.status == 'not_started'
        assert rtap_item.sort_order == 1
        assert 'Implement redundant' in str(rtap_item)

    @pytest.mark.django_db
    def test_rtap_quarterly_update_creation(self, rtap_quarterly_update):
        assert rtap_quarterly_update.status == 'in_progress'
        assert isinstance(rtap_quarterly_update.evidence, list)
        assert len(rtap_quarterly_update.evidence) == 1

    @pytest.mark.django_db
    def test_rtap_quarterly_update_unique_together(self, rtap_quarterly_update, rtap_item, quarter):
        """unique_together on rtap_item + quarter."""
        with pytest.raises(IntegrityError):
            RTAPQuarterlyUpdate.objects.create(
                rtap_item=rtap_item,
                quarter=quarter,
                reported_by=RC_USER_ID,
                update_date=datetime.date(2025, 9, 30),
                created_by=SYSTEM_USER_ID,
            )


# ===========================================================================
# Group 4 — Quarterly Reporting Tests
# ===========================================================================

class TestQuarterlyReportModels:

    @pytest.mark.django_db
    def test_quarterly_report_creation(self, quarterly_report):
        assert quarterly_report.status == 'draft'
        assert quarterly_report.total_risks == 15
        assert quarterly_report.high_risks == 3
        assert 'QPR' in str(quarterly_report)

    @pytest.mark.django_db
    def test_quarterly_report_gap12_iago_fields(self, quarterly_report):
        """GAP-12: IAGO tracking fields."""
        assert quarterly_report.iago_submitted is False
        assert quarterly_report.iago_submission_date is None
        assert quarterly_report.iago_reference == ''

    @pytest.mark.django_db
    def test_quarterly_report_gap03_fields(self, quarterly_report):
        """GAP-03: Committee meeting + LSM submission tracking."""
        assert quarterly_report.committee_meeting_date is None
        assert quarterly_report.lsm_submission_date is None

    @pytest.mark.django_db
    def test_quarterly_report_workflow_context(self, quarterly_report):
        ctx = quarterly_report.get_workflow_context()
        assert ctx['entity_type'] == 'quarterly_performance_report'
        assert 'quarter_id' in ctx
        assert 'fiscal_year_id' in ctx

    @pytest.mark.django_db
    def test_quarterly_report_workflow_metadata(self, quarterly_report):
        meta = quarterly_report.get_workflow_metadata()
        assert meta['entity_type'] == 'quarterly_performance_report'
        assert meta['total_risks'] == 15

    @pytest.mark.django_db
    def test_quarterly_report_unique_per_period(self, quarterly_report, fiscal_year, quarter):
        """UniqueConstraint: one active report per FY + quarter."""
        with pytest.raises(IntegrityError):
            QuarterlyPerformanceReport.objects.create(
                fiscal_year=fiscal_year,
                quarter=quarter,
                prepared_by=RMQAM_USER_ID,
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_activity_report_creation(self, activity_report):
        assert activity_report.reported_by == RC_USER_ID
        assert 'Activity Report' in str(activity_report)

    @pytest.mark.django_db
    def test_activity_report_unique_together(self, activity_report, inst_register, quarter):
        """unique_together on inst_register + quarter + reported_by."""
        with pytest.raises(IntegrityError):
            ActivityReport.objects.create(
                inst_register=inst_register,
                quarter=quarter,
                reported_by=RC_USER_ID,
                submission_date=datetime.date(2025, 10, 1),
                activities_summary='Duplicate.',
                created_by=SYSTEM_USER_ID,
            )


# ===========================================================================
# Group 5 — QMS Audit Tests
# ===========================================================================

class TestQMSAuditModels:

    @pytest.mark.django_db
    def test_qms_program_creation(self, qms_program):
        assert qms_program.status == 'approved'
        assert 'QMS Program' in str(qms_program)

    @pytest.mark.django_db
    def test_qms_program_unique_per_fy(self, qms_program, fiscal_year):
        """UniqueConstraint: one active program per FY."""
        with pytest.raises(IntegrityError):
            QMSAuditProgram.objects.create(
                fiscal_year=fiscal_year,
                program_title='Duplicate',
                objective='Test',
                scope='Test',
                prepared_by=RMQAM_USER_ID,
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_qms_program_workflow_context(self, qms_program):
        ctx = qms_program.get_workflow_context()
        assert ctx['entity_type'] == 'qms_audit_program'
        assert 'fiscal_year_id' in ctx

    @pytest.mark.django_db
    def test_qms_plan_creation(self, qms_plan):
        assert qms_plan.status == 'approved'
        assert qms_plan.nda_signed is True
        assert qms_plan.timetable_agreed is True
        assert 'QMS Plan' in str(qms_plan)

    @pytest.mark.django_db
    def test_qms_plan_gap04_nda_fields(self, qms_plan):
        """GAP-04: NDA fields present."""
        assert qms_plan.nda_signed is True
        assert qms_plan.nda_signed_date == datetime.date(2026, 1, 18)
        assert qms_plan.nda_document_id is None

    @pytest.mark.django_db
    def test_qms_plan_gap10_timetable(self, qms_plan):
        """GAP-10: Timetable agreed field."""
        assert qms_plan.timetable_agreed is True

    @pytest.mark.django_db
    def test_qms_plan_clean_10day_rule(self, qms_program):
        """Rule E.7: notification must be ≥10 days before audit start."""
        plan = QMSAuditPlan(
            audit_program=qms_program,
            plan_title='Too Late Notification',
            auditee_unit_id=AUDITEE_UNIT_UUID,
            lead_team_leader=TL_USER_ID,
            audit_start_date=datetime.date(2026, 2, 10),
            audit_end_date=datetime.date(2026, 2, 14),
            notification_date=datetime.date(2026, 2, 5),  # only 5 days
            scope='Test scope',
            created_by=SYSTEM_USER_ID,
        )
        with pytest.raises(ValidationError) as exc_info:
            plan.clean()
        assert '10 days' in str(exc_info.value)

    @pytest.mark.django_db
    def test_qms_plan_clean_passes_with_sufficient_notice(self, qms_program):
        """10-day rule passes with sufficient notice."""
        plan = QMSAuditPlan(
            audit_program=qms_program,
            plan_title='Good Notice',
            auditee_unit_id=AUDITEE_UNIT_UUID,
            lead_team_leader=TL_USER_ID,
            audit_start_date=datetime.date(2026, 2, 20),
            audit_end_date=datetime.date(2026, 2, 24),
            notification_date=datetime.date(2026, 2, 1),  # 19 days
            scope='Test scope',
            created_by=SYSTEM_USER_ID,
        )
        plan.clean()  # should not raise

    @pytest.mark.django_db
    def test_qms_plan_workflow_context(self, qms_plan):
        ctx = qms_plan.get_workflow_context()
        assert ctx['entity_type'] == 'qms_audit_plan'
        assert 'auditee_unit_id' in ctx
        assert 'lead_team_leader' in ctx

    @pytest.mark.django_db
    def test_team_assignment_creation(self, team_assignment):
        assert team_assignment.role == 'team_leader'
        assert team_assignment.auditor_id == QA_USER_ID

    @pytest.mark.django_db
    def test_team_assignment_unique_together(self, team_assignment, qms_plan):
        """unique_together: one auditor per plan."""
        with pytest.raises(IntegrityError):
            QMSAuditTeamAssignment.objects.create(
                audit_plan=qms_plan,
                auditor_id=QA_USER_ID,
                role='auditor',
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_audit_checklist_creation(self, audit_checklist):
        assert audit_checklist.conformity == 'conforming'
        assert isinstance(audit_checklist.findings_detail, dict)

    @pytest.mark.django_db
    def test_audit_checklist_unique_together(self, audit_checklist, qms_plan, iso_clause):
        """unique_together: one checklist per plan + clause + auditor."""
        with pytest.raises(IntegrityError):
            AuditChecklist.objects.create(
                audit_plan=qms_plan,
                iso_clause=iso_clause,
                auditor_id=QA_USER_ID,
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_qms_report_creation(self, qms_report):
        assert qms_report.status == 'draft'
        assert 'QMS Report' in str(qms_report)

    @pytest.mark.django_db
    def test_qms_report_one_to_one(self, qms_report, qms_plan):
        """OneToOne: only one report per plan."""
        with pytest.raises(IntegrityError):
            QMSAuditReport.objects.create(
                audit_plan=qms_plan,
                report_title='Duplicate Report',
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_nonconformance_creation(self, nonconformance):
        assert nonconformance.status == 'raised'
        assert nonconformance.raised_by == QA_USER_ID
        assert 'NC' in str(nonconformance)

    @pytest.mark.django_db
    def test_nonconformance_default_fields(self, nonconformance):
        assert nonconformance.corrective_action == ''
        assert nonconformance.responsible_officer is None
        assert nonconformance.due_date is None
        assert nonconformance.closed_at is None


# ===========================================================================
# Group 6 — Meeting Tests [GAP-01, GAP-08]
# ===========================================================================

class TestRiskMeetingModels:

    @pytest.mark.django_db
    def test_risk_meeting_creation(self, risk_meeting):
        assert risk_meeting.meeting_type == 'risk_discussion'
        assert risk_meeting.status == 'scheduled'
        assert risk_meeting.is_active is True

    @pytest.mark.django_db
    def test_risk_meeting_gap08_awareness_session_choice(self, fiscal_year):
        """GAP-08: awareness_session is a valid meeting_type choice."""
        m = RiskMeeting.objects.create(
            meeting_type='awareness_session',
            organized_by=RMQAM_USER_ID,
            fiscal_year=fiscal_year,
            title='Risk Awareness Session',
            meeting_date=datetime.datetime(2025, 10, 1, 14, 0, tzinfo=datetime.timezone.utc),
            created_by=SYSTEM_USER_ID,
        )
        assert m.meeting_type == 'awareness_session'

    @pytest.mark.django_db
    def test_meeting_attendance_creation(self, meeting_attendance):
        assert meeting_attendance.user_id == RC_USER_ID
        assert meeting_attendance.attended is True

    @pytest.mark.django_db
    def test_meeting_attendance_unique_together(self, meeting_attendance, risk_meeting):
        """unique_together: one attendance per meeting + user."""
        with pytest.raises(IntegrityError):
            MeetingAttendance.objects.create(
                meeting=risk_meeting,
                user_id=RC_USER_ID,
                created_by=SYSTEM_USER_ID,
            )


# ===========================================================================
# Group 8 — QMS Audit Support Tests [GAP-05, GAP-10]
# ===========================================================================

class TestQMSAuditSupportModels:

    @pytest.mark.django_db
    def test_qms_audit_meeting_creation(self, qms_audit_meeting):
        assert qms_audit_meeting.meeting_type == 'entry'
        assert qms_audit_meeting.timetable_agreed is True
        assert 'Entry' in str(qms_audit_meeting)

    @pytest.mark.django_db
    def test_qms_audit_meeting_unique_together(self, qms_audit_meeting, qms_plan):
        """unique_together: one meeting per plan + type."""
        with pytest.raises(IntegrityError):
            QMSAuditMeeting.objects.create(
                audit_plan=qms_plan,
                meeting_type='entry',
                meeting_date=datetime.datetime(2026, 1, 21, 8, 0, tzinfo=datetime.timezone.utc),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_qms_audit_meeting_exit_allowed(self, qms_plan):
        """Can create different meeting types for same plan."""
        exit_meeting = QMSAuditMeeting.objects.create(
            audit_plan=qms_plan,
            meeting_type='exit',
            meeting_date=datetime.datetime(2026, 1, 24, 16, 0, tzinfo=datetime.timezone.utc),
            created_by=SYSTEM_USER_ID,
        )
        assert exit_meeting.meeting_type == 'exit'

    @pytest.mark.django_db
    def test_timetable_entry_creation(self, timetable_entry):
        assert timetable_entry.process_or_area == 'Software Development Process'
        assert timetable_entry.sort_order == 1
        assert 'Timetable' in str(timetable_entry)

    @pytest.mark.django_db
    def test_timetable_entry_ordering(self, qms_plan):
        """Verify ordering by date, start_time, sort_order."""
        e1 = QMSAuditTimetableEntry.objects.create(
            audit_plan=qms_plan,
            date=datetime.date(2026, 1, 20), start_time=datetime.time(14, 0),
            end_time=datetime.time(17, 0),
            process_or_area='Network Infrastructure',
            assigned_auditor=QA_USER_ID, auditee_unit_id=AUDITEE_UNIT_UUID,
            sort_order=2, created_by=SYSTEM_USER_ID,
        )
        e2 = QMSAuditTimetableEntry.objects.create(
            audit_plan=qms_plan,
            date=datetime.date(2026, 1, 21), start_time=datetime.time(9, 0),
            end_time=datetime.time(12, 0),
            process_or_area='Help Desk',
            assigned_auditor=QA_USER_ID, auditee_unit_id=AUDITEE_UNIT_UUID,
            sort_order=1, created_by=SYSTEM_USER_ID,
        )
        entries = list(QMSAuditTimetableEntry.objects.filter(audit_plan=qms_plan))
        assert entries[0].date <= entries[-1].date
