"""
Risk Management & Quality Assurance Module — Shared pytest fixtures.

Builds the complete model fixture chain required by Risk Management tests:

  Lookups → RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
            NonConformanceType, ISOClause, FiscalYear, Quarter
  Group 7 → QATrainingSession, QATrainingAttendee
  Group 1 → RiskChampion, RiskChampionAppointment,
            QualityAuditor, QualityAuditorAppointment
  Group 2 → RiskAssessmentSheet, DepartmentalRiskRegister, DeptRegisterEntry
  Group 3 → InstitutionalRiskRegister, InstitutionalRiskEntry,
            RiskTreatmentActionPlan, RTAPItem, RTAPQuarterlyUpdate
  Group 4 → QuarterlyPerformanceReport, ActivityReport
  Group 5 → QMSAuditProgram, QMSAuditPlan, QMSAuditTeamAssignment,
            AuditChecklist, QMSAuditReport, NonConformance
  Group 6 → RiskMeeting, MeetingAttendance
  Group 8 → QMSAuditMeeting, QMSAuditTimetableEntry
"""
import uuid
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

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
    FiscalYear, Quarter,
    RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
    NonConformanceType, ISOClause,
    RiskSector, StrategicObjective,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Stable UUIDs used across risk management fixtures
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_USER_ID   = uuid.UUID("a0000000-0000-0000-0000-000000000001")
RMQAM_USER_ID    = uuid.UUID("a0000000-0000-0000-0000-000000000002")
RC_USER_ID       = uuid.UUID("a0000000-0000-0000-0000-000000000003")
QA_USER_ID       = uuid.UUID("a0000000-0000-0000-0000-000000000004")
HEAD_USER_ID     = uuid.UUID("a0000000-0000-0000-0000-000000000005")
RISK_OWNER_ID    = uuid.UUID("a0000000-0000-0000-0000-000000000006")
OTHER_USER_ID    = uuid.UUID("a0000000-0000-0000-0000-000000000007")
OFFICER_USER_ID  = uuid.UUID("a0000000-0000-0000-0000-000000000008")
TL_USER_ID       = uuid.UUID("a0000000-0000-0000-0000-000000000009")
DOCUMENT_UUID    = uuid.UUID("a0000000-0000-0000-0000-00000000000a")
PLAN_UUID        = uuid.UUID("a0000000-0000-0000-0000-00000000000b")
ORG_UNIT_UUID    = uuid.UUID("a0000000-0000-0000-0000-00000000000c")
AUDITEE_UNIT_UUID = uuid.UUID("a0000000-0000-0000-0000-00000000000d")


# ═══════════════════════════════════════════════════════════════════════════════
# Mock user helpers
# ═══════════════════════════════════════════════════════════════════════════════

def make_mock_user(user_id):
    """Return a mock user accepted by force_authenticate."""
    user = MagicMock()
    user.id = str(user_id)
    user.is_authenticated = True
    return user


# ═══════════════════════════════════════════════════════════════════════════════
# Client fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def rmqam_client():
    """Authenticated client for RMQAM (Risk Management & QA Manager)."""
    client = APIClient()
    client.force_authenticate(user=make_mock_user(RMQAM_USER_ID))
    return client


@pytest.fixture
def rc_client():
    """Authenticated client for Risk Champion."""
    client = APIClient()
    client.force_authenticate(user=make_mock_user(RC_USER_ID))
    return client


@pytest.fixture
def qa_client():
    """Authenticated client for Quality Auditor."""
    client = APIClient()
    client.force_authenticate(user=make_mock_user(QA_USER_ID))
    return client


@pytest.fixture
def anon_client():
    """Unauthenticated client."""
    return APIClient()


# ═══════════════════════════════════════════════════════════════════════════════
# Permission bypass fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def allow_all_permissions():
    """Patch _check_grc_permission_locally to always return True."""
    with patch(
        'apps.api.permissions_jwt._check_grc_permission_locally',
        return_value=True,
    ):
        yield


@pytest.fixture
def deny_all_permissions():
    """Patch _check_grc_permission_locally to always return False."""
    with patch(
        'apps.api.permissions_jwt._check_grc_permission_locally',
        return_value=False,
    ):
        yield


# ═══════════════════════════════════════════════════════════════════════════════
# Lookup fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def fiscal_year(db):
    return FiscalYear.objects.create(
        year_code='2025/2026', name='FY 2025/2026',
        start_date=datetime.date(2025, 7, 1),
        end_date=datetime.date(2026, 6, 30),
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def quarter(db, fiscal_year):
    return Quarter.objects.create(
        fiscal_year=fiscal_year, quarter_number=1, name='Q1',
        start_date=datetime.date(2025, 7, 1),
        end_date=datetime.date(2025, 9, 30),
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def quarter_q2(db, fiscal_year):
    return Quarter.objects.create(
        fiscal_year=fiscal_year, quarter_number=2, name='Q2',
        start_date=datetime.date(2025, 10, 1),
        end_date=datetime.date(2025, 12, 31),
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def risk_category(db):
    return RiskCategory.objects.create(
        code='operational', name='Operational',
        description='Risks from internal processes',
        sort_order=1, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def risk_category_financial(db):
    return RiskCategory.objects.create(
        code='financial', name='Financial',
        description='Risks related to financial loss',
        sort_order=2, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def likelihood_low(db):
    return RiskLikelihood.objects.create(
        code='rare', name='Rare', label='Rare',
        numerical_value=Decimal('1'), sort_order=1,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def likelihood_high(db):
    return RiskLikelihood.objects.create(
        code='likely', name='Likely', label='Likely',
        numerical_value=Decimal('4'), sort_order=4,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def impact_low(db):
    return RiskImpact.objects.create(
        code='negligible', name='Negligible', label='Negligible',
        numerical_value=Decimal('1'), sort_order=1,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def impact_high(db):
    return RiskImpact.objects.create(
        code='major', name='Major', label='Major',
        numerical_value=Decimal('4'), sort_order=4,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def risk_level_low(db):
    return RiskLevel.objects.create(
        code='low', name='Low',
        min_score=Decimal('1'), max_score=Decimal('4'),
        color_code='#22C55E', sort_order=1,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def risk_level_high(db):
    return RiskLevel.objects.create(
        code='high', name='High',
        min_score=Decimal('10'), max_score=Decimal('16'),
        color_code='#F97316', sort_order=3,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def nc_type_major(db):
    return NonConformanceType.objects.create(
        code='major_nc', name='Major Non-Conformance',
        description='Absence or total breakdown of a system',
        sort_order=1, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def nc_type_minor(db):
    return NonConformanceType.objects.create(
        code='minor_nc', name='Minor Non-Conformance',
        description='Single observed lapse',
        sort_order=2, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def iso_clause_parent(db):
    return ISOClause.objects.create(
        code='9', clause_number='9', title='Performance Evaluation',
        sort_order=90, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def iso_clause(db, iso_clause_parent):
    return ISOClause.objects.create(
        code='9.2', clause_number='9.2', title='Internal audit',
        parent_clause=iso_clause_parent,
        sort_order=92, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def risk_sector(db):
    return RiskSector.objects.create(
        code='health', name='Health',
        description='Health sector risks',
        sort_order=1, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def risk_sector_finance(db):
    return RiskSector.objects.create(
        code='finance', name='Finance',
        description='Financial sector risks',
        sort_order=2, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def strategic_objective(db):
    return StrategicObjective.objects.create(
        code='SO-01', name='Enhance regulatory compliance across all sectors',
        description='Primary compliance objective',
        sort_order=1, created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def strategic_objective_secondary(db):
    return StrategicObjective.objects.create(
        code='SO-02', name='Strengthen institutional capacity',
        description='Capacity building objective',
        sort_order=2, created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Group 7 — QA Training fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def training_session(db):
    return QATrainingSession.objects.create(
        title='ISO 9001:2015 QMS Training',
        trainer_name='Dr. Mwalimu',
        trainer_organization='TBS',
        training_date=datetime.date(2026, 2, 15),
        venue='Conference Hall A',
        approval_status='approved',
        approved_by=RMQAM_USER_ID,
        approval_date=datetime.date(2026, 2, 1),
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Group 1 — Risk Champion & Quality Auditor fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def risk_champion(db):
    return RiskChampion.objects.create(
        org_unit_id=ORG_UNIT_UUID,
        org_unit_type='directorate',
        user_id=RC_USER_ID,
        nominated_by=HEAD_USER_ID,
        term_start=datetime.date(2025, 7, 1),
        term_end=datetime.date(2026, 6, 30),
        qualifications='Certified Risk Analyst',
        experience_summary='5 years in risk management',
        justification='Best candidate per committee review',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def rc_appointment(db, risk_champion):
    return RiskChampionAppointment.objects.create(
        risk_champion=risk_champion,
        appointment_date=datetime.date(2025, 7, 15),
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def rc_appointment_with_workflow(db, risk_champion):
    """RiskChampionAppointment that already has an active workflow plan."""
    appt = RiskChampionAppointment.objects.create(
        risk_champion=risk_champion,
        appointment_date=datetime.date(2025, 7, 15),
        status='submitted',
        created_by=SYSTEM_USER_ID,
    )
    appt.start_workflow(
        plan_id=str(PLAN_UUID),
        initial_stage='rmo_draft',
        stage_id=str(uuid.uuid4()),
    )
    appt.save()
    return appt


@pytest.fixture
def quality_auditor(db, training_session):
    return QualityAuditor.objects.create(
        user_id=QA_USER_ID,
        nominated_by=HEAD_USER_ID,
        org_unit_id=ORG_UNIT_UUID,
        org_unit_type='directorate',
        exam_attempt=1,
        exam_score=Decimal('85.00'),
        is_certified=True,
        certification_date=datetime.date(2026, 3, 1),
        term_start=datetime.date(2026, 3, 1),
        term_end=datetime.date(2027, 2, 28),
        training_session=training_session,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def qa_appointment(db, quality_auditor):
    return QualityAuditorAppointment.objects.create(
        quality_auditor=quality_auditor,
        appointment_date=datetime.date(2026, 3, 5),
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def qa_appointment_with_workflow(db, quality_auditor):
    """QualityAuditorAppointment that already has an active workflow plan."""
    appt = QualityAuditorAppointment.objects.create(
        quality_auditor=quality_auditor,
        appointment_date=datetime.date(2026, 3, 5),
        status='submitted',
        created_by=SYSTEM_USER_ID,
    )
    appt.start_workflow(
        plan_id=str(PLAN_UUID),
        initial_stage='rmo_draft',
        stage_id=str(uuid.uuid4()),
    )
    appt.save()
    return appt


@pytest.fixture
def training_attendee(db, training_session, quality_auditor):
    return QATrainingAttendee.objects.create(
        training_session=training_session,
        quality_auditor=quality_auditor,
        attended=True,
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Group 2 — Risk Assessment & Departmental Register fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def risk_assessment_sheet(db, risk_champion, fiscal_year, risk_category,
                          likelihood_high, impact_high, risk_level_high):
    return RiskAssessmentSheet.objects.create(
        risk_champion=risk_champion,
        org_unit_id=ORG_UNIT_UUID,
        fiscal_year=fiscal_year,
        risk_category=risk_category,
        risk_title='System Downtime Risk',
        risk_description='Critical system outage impacting operations',
        risk_owner=RISK_OWNER_ID,
        likelihood=likelihood_high,
        impact=impact_high,
        existing_controls='Daily backups, redundant servers',
        references=[{'type': 'audit_finding', 'id': str(uuid.uuid4()), 'title': 'IT Audit 2025'}],
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def dept_register(db, fiscal_year):
    return DepartmentalRiskRegister.objects.create(
        org_unit_id=ORG_UNIT_UUID,
        org_unit_type='directorate',
        fiscal_year=fiscal_year,
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def dept_register_with_workflow(db, fiscal_year):
    """DepartmentalRiskRegister with an active workflow plan."""
    entity = DepartmentalRiskRegister.objects.create(
        org_unit_id=uuid.uuid4(),
        org_unit_type='directorate',
        fiscal_year=fiscal_year,
        status='submitted',
        created_by=SYSTEM_USER_ID,
    )
    entity.start_workflow(
        plan_id=str(PLAN_UUID),
        initial_stage='rc_submit',
        stage_id=str(uuid.uuid4()),
    )
    entity.save()
    return entity


@pytest.fixture
def dept_register_entry(db, dept_register, risk_assessment_sheet):
    return DeptRegisterEntry.objects.create(
        dept_register=dept_register,
        risk_sheet=risk_assessment_sheet,
        sort_order=1,
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Group 3 — Institutional Register & RTAP fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def inst_register(db, fiscal_year):
    return InstitutionalRiskRegister.objects.create(
        fiscal_year=fiscal_year,
        prepared_by=RMQAM_USER_ID,
        preparation_date=datetime.date(2025, 8, 15),
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def inst_register_with_workflow(db):
    """InstitutionalRiskRegister with an active workflow plan."""
    fy = FiscalYear.objects.create(
        year_code='2024/2025', name='FY 2024/2025',
        start_date=datetime.date(2024, 7, 1),
        end_date=datetime.date(2025, 6, 30),
        created_by=SYSTEM_USER_ID,
    )
    entity = InstitutionalRiskRegister.objects.create(
        fiscal_year=fy,
        prepared_by=RMQAM_USER_ID,
        preparation_date=datetime.date(2024, 8, 15),
        status='rmqam_review',
        created_by=SYSTEM_USER_ID,
    )
    entity.start_workflow(
        plan_id=str(PLAN_UUID),
        initial_stage='rmqam_review',
        stage_id=str(uuid.uuid4()),
    )
    entity.save()
    return entity


@pytest.fixture
def inst_entry(db, inst_register, risk_assessment_sheet):
    return InstitutionalRiskEntry.objects.create(
        inst_register=inst_register,
        risk_sheet=risk_assessment_sheet,
        risk_ranking=1,
        notes='Highest risk entry',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def rtap(db, inst_register, fiscal_year):
    return RiskTreatmentActionPlan.objects.create(
        inst_register=inst_register,
        fiscal_year=fiscal_year,
        prepared_by=RMQAM_USER_ID,
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def rtap_with_workflow(db, inst_register_with_workflow):
    """RiskTreatmentActionPlan with an active workflow plan."""
    entity = RiskTreatmentActionPlan.objects.create(
        inst_register=inst_register_with_workflow,
        fiscal_year=inst_register_with_workflow.fiscal_year,
        prepared_by=RMQAM_USER_ID,
        status='rmqam_review',
        created_by=SYSTEM_USER_ID,
    )
    entity.start_workflow(
        plan_id=str(uuid.uuid4()),
        initial_stage='rmqam_review',
        stage_id=str(uuid.uuid4()),
    )
    entity.save()
    return entity


@pytest.fixture
def rtap_item(db, rtap, inst_entry):
    return RTAPItem.objects.create(
        rtap=rtap,
        inst_entry=inst_entry,
        treatment_description='Implement redundant failover system',
        responsible_officer=OFFICER_USER_ID,
        target_date=datetime.date(2026, 3, 31),
        status='not_started',
        sort_order=1,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def rtap_quarterly_update(db, rtap_item, quarter):
    return RTAPQuarterlyUpdate.objects.create(
        rtap_item=rtap_item,
        quarter=quarter,
        reported_by=RC_USER_ID,
        update_date=datetime.date(2025, 9, 25),
        status='in_progress',
        progress_notes='Vendor selected, procurement in progress',
        evidence=[{'type': 'document', 'ref': str(DOCUMENT_UUID), 'label': 'Vendor quote'}],
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Group 4 — Quarterly Reporting fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def quarterly_report(db, fiscal_year, quarter):
    return QuarterlyPerformanceReport.objects.create(
        fiscal_year=fiscal_year,
        quarter=quarter,
        prepared_by=RMQAM_USER_ID,
        preparation_date=datetime.date(2025, 10, 5),
        total_risks=15,
        high_risks=3,
        medium_risks=7,
        low_risks=5,
        rtap_completed=2,
        rtap_in_progress=5,
        rtap_not_started=8,
        report_body='Quarterly risk implementation summary.',
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def quarterly_report_with_workflow(db, fiscal_year, quarter_q2):
    """QuarterlyPerformanceReport with an active workflow plan."""
    entity = QuarterlyPerformanceReport.objects.create(
        fiscal_year=fiscal_year,
        quarter=quarter_q2,
        prepared_by=RMQAM_USER_ID,
        preparation_date=datetime.date(2026, 1, 5),
        total_risks=12,
        high_risks=2,
        medium_risks=5,
        low_risks=5,
        rtap_completed=3,
        rtap_in_progress=4,
        rtap_not_started=5,
        report_body='Q2 summary.',
        status='rmqam_prepare',
        created_by=SYSTEM_USER_ID,
    )
    entity.start_workflow(
        plan_id=str(uuid.uuid4()),
        initial_stage='rmqam_prepare',
        stage_id=str(uuid.uuid4()),
    )
    entity.save()
    return entity


@pytest.fixture
def activity_report(db, inst_register, quarter):
    return ActivityReport.objects.create(
        inst_register=inst_register,
        quarter=quarter,
        reported_by=RC_USER_ID,
        submission_date=datetime.date(2025, 9, 28),
        activities_summary='Conducted departmental risk assessment workshop.',
        issues_raised='Low participation from Zone offices.',
        recommendations='Schedule sessions during non-peak hours.',
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Group 5 — QMS Audit fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def qms_program(db, fiscal_year):
    return QMSAuditProgram.objects.create(
        fiscal_year=fiscal_year,
        program_title='FY 2025/2026 Annual QMS Audit Program',
        objective='Assess QMS effectiveness across all directorates',
        scope='All directorates and units under ISO 9001:2015 scope',
        prepared_by=RMQAM_USER_ID,
        status='approved',
        approved_by=HEAD_USER_ID,
        approval_date=datetime.date(2025, 8, 1),
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def qms_program_draft(db, fiscal_year):
    """QMSAuditProgram in draft status (no workflow yet)."""
    return QMSAuditProgram.objects.create(
        fiscal_year=fiscal_year,
        program_title='Draft QMS Audit Program',
        objective='Assess QMS',
        scope='All directorates',
        prepared_by=RMQAM_USER_ID,
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def qms_program_with_workflow(db):
    """QMSAuditProgram with an active workflow plan."""
    fy = FiscalYear.objects.create(
        year_code='2023/2024', name='FY 2023/2024',
        start_date=datetime.date(2023, 7, 1),
        end_date=datetime.date(2024, 6, 30),
        created_by=SYSTEM_USER_ID,
    )
    entity = QMSAuditProgram.objects.create(
        fiscal_year=fy,
        program_title='WF QMS Audit Program',
        objective='Assess QMS',
        scope='All directorates',
        prepared_by=RMQAM_USER_ID,
        status='submitted',
        created_by=SYSTEM_USER_ID,
    )
    entity.start_workflow(
        plan_id=str(uuid.uuid4()),
        initial_stage='rmo_submit',
        stage_id=str(uuid.uuid4()),
    )
    entity.save()
    return entity


@pytest.fixture
def qms_plan(db, qms_program):
    return QMSAuditPlan.objects.create(
        audit_program=qms_program,
        plan_title='ICT Directorate Audit',
        auditee_unit_id=AUDITEE_UNIT_UUID,
        lead_team_leader=TL_USER_ID,
        audit_start_date=datetime.date(2026, 1, 20),
        audit_end_date=datetime.date(2026, 1, 24),
        notification_date=datetime.date(2026, 1, 5),
        scope='All ICT processes under ISO 9001:2015',
        criteria='ISO 9001:2015 Clauses 4–10',
        status='approved',
        nda_signed=True,
        nda_signed_date=datetime.date(2026, 1, 18),
        timetable_agreed=True,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def qms_plan_draft(db, qms_program):
    """QMSAuditPlan in draft status (no workflow yet)."""
    return QMSAuditPlan.objects.create(
        audit_program=qms_program,
        plan_title='Draft Audit Plan',
        auditee_unit_id=AUDITEE_UNIT_UUID,
        lead_team_leader=TL_USER_ID,
        audit_start_date=datetime.date(2026, 3, 10),
        audit_end_date=datetime.date(2026, 3, 14),
        notification_date=datetime.date(2026, 2, 25),
        scope='HR processes',
        criteria='ISO 9001:2015 Clauses 4–10',
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def qms_plan_with_workflow(db, qms_program):
    """QMSAuditPlan with an active workflow plan."""
    entity = QMSAuditPlan.objects.create(
        audit_program=qms_program,
        plan_title='WF Audit Plan',
        auditee_unit_id=uuid.uuid4(),
        lead_team_leader=TL_USER_ID,
        audit_start_date=datetime.date(2026, 4, 10),
        audit_end_date=datetime.date(2026, 4, 14),
        notification_date=datetime.date(2026, 3, 28),
        scope='Finance processes',
        criteria='ISO 9001:2015',
        status='submitted',
        created_by=SYSTEM_USER_ID,
    )
    entity.start_workflow(
        plan_id=str(uuid.uuid4()),
        initial_stage='rmo_submit',
        stage_id=str(uuid.uuid4()),
    )
    entity.save()
    return entity


@pytest.fixture
def team_assignment(db, qms_plan):
    return QMSAuditTeamAssignment.objects.create(
        audit_plan=qms_plan,
        auditor_id=QA_USER_ID,
        role='team_leader',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def audit_checklist(db, qms_plan, iso_clause):
    return AuditChecklist.objects.create(
        audit_plan=qms_plan,
        iso_clause=iso_clause,
        auditor_id=QA_USER_ID,
        conformity='conforming',
        findings_detail={'evidence': ['Document reviewed'], 'auditor_notes': 'Meets requirements'},
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def qms_report(db, qms_plan):
    return QMSAuditReport.objects.create(
        audit_plan=qms_plan,
        report_title='ICT Directorate QMS Audit Report',
        executive_summary='Audit completed with minor findings.',
        scope_summary='All ICT processes audited per ISO 9001:2015.',
        status='draft',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def nonconformance(db, qms_report, iso_clause, nc_type_major):
    return NonConformance.objects.create(
        audit_report=qms_report,
        iso_clause=iso_clause,
        nc_type=nc_type_major,
        description='No documented procedure for server patching.',
        objective_evidence='Interviewed IT ops team; no SOP found.',
        raised_by=QA_USER_ID,
        status='raised',
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Group 6 — Meeting fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def risk_meeting(db, fiscal_year):
    return RiskMeeting.objects.create(
        meeting_type='risk_discussion',
        organized_by=RMQAM_USER_ID,
        org_unit_id=ORG_UNIT_UUID,
        fiscal_year=fiscal_year,
        title='Q1 Risk Discussion Meeting',
        agenda='Review departmental risk registers.',
        meeting_date=datetime.datetime(2025, 9, 15, 10, 0, tzinfo=datetime.timezone.utc),
        venue='Board Room B',
        status='scheduled',
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def meeting_attendance(db, risk_meeting):
    return MeetingAttendance.objects.create(
        meeting=risk_meeting,
        user_id=RC_USER_ID,
        attended=True,
        created_by=SYSTEM_USER_ID,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Group 8 — QMS Audit Support fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def qms_audit_meeting(db, qms_plan):
    return QMSAuditMeeting.objects.create(
        audit_plan=qms_plan,
        meeting_type='entry',
        meeting_date=datetime.datetime(2026, 1, 20, 8, 0, tzinfo=datetime.timezone.utc),
        minutes='Opening meeting conducted. Scope confirmed.',
        attendance=[str(QA_USER_ID), str(TL_USER_ID)],
        timetable_agreed=True,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def timetable_entry(db, qms_plan):
    return QMSAuditTimetableEntry.objects.create(
        audit_plan=qms_plan,
        date=datetime.date(2026, 1, 20),
        start_time=datetime.time(9, 0),
        end_time=datetime.time(12, 0),
        process_or_area='Software Development Process',
        assigned_auditor=QA_USER_ID,
        auditee_unit_id=AUDITEE_UNIT_UUID,
        sort_order=1,
        created_by=SYSTEM_USER_ID,
    )
