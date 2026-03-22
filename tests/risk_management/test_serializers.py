"""
Tests for Risk Management serializers — Phase 5.

Verifies:
 - Serialization produces all expected fields
 - FK dual-field pattern: nested read, UUID write
 - WorkflowMixin property fields exposed correctly
 - Read-only / auto-computed fields enforced
 - Deserialization (write) with valid data succeeds
"""
import uuid
import datetime
from decimal import Decimal

import pytest
from apps.api.serializers.risk_serializers import (
    QATrainingSessionSerializer,
    QATrainingAttendeeSerializer,
    RiskChampionSerializer,
    RiskChampionAppointmentSerializer,
    QualityAuditorSerializer,
    QualityAuditorAppointmentSerializer,
    RiskAssessmentSheetSerializer,
    DepartmentalRiskRegisterSerializer,
    DeptRegisterEntrySerializer,
    InstitutionalRiskRegisterSerializer,
    InstitutionalRiskEntrySerializer,
    RiskTreatmentActionPlanSerializer,
    RTAPItemSerializer,
    RTAPQuarterlyUpdateSerializer,
    QuarterlyPerformanceReportSerializer,
    ActivityReportSerializer,
    QMSAuditProgramSerializer,
    QMSAuditPlanSerializer,
    QMSAuditTeamAssignmentSerializer,
    AuditChecklistSerializer,
    QMSAuditReportSerializer,
    NonConformanceSerializer,
    RiskMeetingSerializer,
    MeetingAttendanceSerializer,
    QMSAuditMeetingSerializer,
    QMSAuditTimetableEntrySerializer,
)

from .conftest import (
    SYSTEM_USER_ID, RMQAM_USER_ID, RC_USER_ID, QA_USER_ID,
    HEAD_USER_ID, RISK_OWNER_ID, OFFICER_USER_ID, TL_USER_ID,
    DOCUMENT_UUID, PLAN_UUID, ORG_UNIT_UUID, AUDITEE_UNIT_UUID,
)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — QA Training Serializer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestQATrainingSessionSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, training_session):
        data = QATrainingSessionSerializer(training_session).data
        assert data['id'] == str(training_session.id)
        assert data['title'] == 'ISO 9001:2015 QMS Training'
        assert data['trainer_name'] == 'Dr. Mwalimu'
        assert data['approval_status'] == 'approved'
        assert 'created_at' in data
        assert 'updated_at' in data

    @pytest.mark.django_db
    def test_deserialization_valid(self, db):
        payload = {
            'title': 'New Training',
            'trainer_name': 'Prof. Test',
            'training_date': '2026-05-01',
        }
        s = QATrainingSessionSerializer(data=payload)
        assert s.is_valid(), s.errors
        obj = s.save(created_by=SYSTEM_USER_ID)
        assert obj.title == 'New Training'


class TestQATrainingAttendeeSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, training_attendee):
        data = QATrainingAttendeeSerializer(training_attendee).data
        assert data['id'] == str(training_attendee.id)
        assert data['attended'] is True
        # Nested read: training_session is nested dict
        assert 'title' in data['training_session']

    @pytest.mark.django_db
    def test_deserialization_valid(self, training_session, quality_auditor):
        # Delete existing attendee to avoid unique_together conflict
        from apps.core.models import QATrainingAttendee
        QATrainingAttendee.objects.filter(
            training_session=training_session,
            quality_auditor=quality_auditor,
        ).delete()
        payload = {
            'training_session_id': str(training_session.id),
            'quality_auditor_id': str(quality_auditor.id),
            'attended': False,
        }
        s = QATrainingAttendeeSerializer(data=payload)
        assert s.is_valid(), s.errors


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — Risk Champion & QA Appointment Serializer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskChampionSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, risk_champion):
        data = RiskChampionSerializer(risk_champion).data
        assert data['id'] == str(risk_champion.id)
        assert data['org_unit_id'] == str(ORG_UNIT_UUID)
        assert data['org_unit_type'] == 'directorate'
        assert data['user_id'] == str(RC_USER_ID)
        assert data['qualifications'] == 'Certified Risk Analyst'
        assert data['experience_summary'] == '5 years in risk management'
        assert data['justification'] == 'Best candidate per committee review'

    @pytest.mark.django_db
    def test_deserialization_valid(self, db):
        payload = {
            'org_unit_id': str(uuid.uuid4()),
            'org_unit_type': 'unit',
            'user_id': str(uuid.uuid4()),
            'nominated_by': str(HEAD_USER_ID),
            'term_start': '2026-01-01',
        }
        s = RiskChampionSerializer(data=payload)
        assert s.is_valid(), s.errors


class TestRiskChampionAppointmentSerializer:
    @pytest.mark.django_db
    def test_serialization_with_workflow(self, rc_appointment_with_workflow):
        data = RiskChampionAppointmentSerializer(rc_appointment_with_workflow).data
        assert data['id'] == str(rc_appointment_with_workflow.id)
        assert data['status'] == 'submitted'
        # Nested FK
        assert 'org_unit_id' in data['risk_champion']
        # WorkflowMixin fields
        assert data['workflow_plan_id'] == str(PLAN_UUID)
        assert data['has_workflow'] is True
        assert data['has_active_workflow'] is True
        assert data['is_workflow_completed'] is False
        assert data['workflow_stage'] == 'rmo_draft'

    @pytest.mark.django_db
    def test_serialization_draft_no_workflow(self, rc_appointment):
        data = RiskChampionAppointmentSerializer(rc_appointment).data
        assert data['status'] == 'draft'
        assert data['workflow_plan_id'] is None
        assert data['has_workflow'] is False
        assert data['has_active_workflow'] is False

    @pytest.mark.django_db
    def test_workflow_fields_are_read_only(self, rc_appointment):
        payload = {
            'risk_champion_id': str(rc_appointment.risk_champion_id),
            'appointment_date': '2026-01-01',
            'workflow_plan_id': str(uuid.uuid4()),
        }
        s = RiskChampionAppointmentSerializer(data=payload)
        assert s.is_valid(), s.errors
        # workflow_plan_id should be ignored on write
        assert 'workflow_plan_id' not in s.validated_data

    @pytest.mark.django_db
    def test_gap06_dispatch_fields(self, rc_appointment_with_workflow):
        data = RiskChampionAppointmentSerializer(rc_appointment_with_workflow).data
        assert 'dispatched' in data
        assert 'dispatch_date' in data
        assert 'dispatch_reference' in data
        assert 'recipient_confirmed' in data

    @pytest.mark.django_db
    def test_gap14_rework_count_read_only(self, rc_appointment):
        data = RiskChampionAppointmentSerializer(rc_appointment).data
        assert data['rework_count'] == 0

    @pytest.mark.django_db
    def test_gap17_review_fields(self, rc_appointment):
        data = RiskChampionAppointmentSerializer(rc_appointment).data
        assert 'last_review_comment' in data
        assert 'last_reviewed_by' in data
        assert 'last_reviewed_at' in data


class TestQualityAuditorSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, quality_auditor):
        data = QualityAuditorSerializer(quality_auditor).data
        assert data['user_id'] == str(QA_USER_ID)
        assert data['is_certified'] is True
        assert data['exam_attempt'] == 1
        # Nested training session
        assert 'title' in data['training_session']

    @pytest.mark.django_db
    def test_training_session_fk_dual_field(self, quality_auditor):
        data = QualityAuditorSerializer(quality_auditor).data
        # Read: nested dict
        assert isinstance(data['training_session'], dict)
        # Write field not in output
        assert 'training_session_id' not in data


class TestQualityAuditorAppointmentSerializer:
    @pytest.mark.django_db
    def test_serialization_with_workflow(self, qa_appointment_with_workflow):
        data = QualityAuditorAppointmentSerializer(qa_appointment_with_workflow).data
        assert data['status'] == 'submitted'
        assert data['has_workflow'] is True
        assert 'quality_auditor' in data
        assert isinstance(data['quality_auditor'], dict)

    @pytest.mark.django_db
    def test_serialization_draft(self, qa_appointment):
        data = QualityAuditorAppointmentSerializer(qa_appointment).data
        assert data['status'] == 'draft'
        assert data['has_workflow'] is False


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — Risk Assessment & Departmental Register Serializer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskAssessmentSheetSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, risk_assessment_sheet):
        data = RiskAssessmentSheetSerializer(risk_assessment_sheet).data
        assert data['risk_title'] == 'System Downtime Risk'
        assert data['risk_owner'] == str(RISK_OWNER_ID)
        # Auto-computed inherent score
        assert Decimal(data['inherent_risk_score']) == Decimal('16.00')
        # Nested FK lookups
        assert isinstance(data['risk_champion'], dict)
        assert isinstance(data['risk_category'], dict)
        assert isinstance(data['likelihood'], dict)
        assert isinstance(data['impact'], dict)
        assert isinstance(data['fiscal_year'], dict)
        # GAP-07 references field
        assert isinstance(data['references'], list)

    @pytest.mark.django_db
    def test_computed_fields_read_only(self, risk_assessment_sheet):
        payload = {
            'risk_champion_id': str(risk_assessment_sheet.risk_champion_id),
            'fiscal_year_id': str(risk_assessment_sheet.fiscal_year_id),
            'risk_category_id': str(risk_assessment_sheet.risk_category_id),
            'risk_title': 'New Risk',
            'risk_description': 'Desc',
            'risk_owner': str(RISK_OWNER_ID),
            'likelihood_id': str(risk_assessment_sheet.likelihood_id),
            'impact_id': str(risk_assessment_sheet.impact_id),
            'org_unit_id': str(ORG_UNIT_UUID),
            'inherent_risk_score': '999.00',  # should be ignored
        }
        s = RiskAssessmentSheetSerializer(data=payload)
        assert s.is_valid(), s.errors
        assert 'inherent_risk_score' not in s.validated_data

    @pytest.mark.django_db
    def test_residual_fields_optional(self, risk_assessment_sheet):
        data = RiskAssessmentSheetSerializer(risk_assessment_sheet).data
        # Residual fields can be null
        assert 'residual_likelihood' in data
        assert 'residual_impact' in data
        assert 'residual_risk_score' in data
        assert 'residual_risk_level' in data


class TestDepartmentalRiskRegisterSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, dept_register):
        data = DepartmentalRiskRegisterSerializer(dept_register).data
        assert data['org_unit_id'] == str(ORG_UNIT_UUID)
        assert data['org_unit_type'] == 'directorate'
        assert data['status'] == 'draft'
        assert isinstance(data['fiscal_year'], dict)
        assert data['has_workflow'] is False

    @pytest.mark.django_db
    def test_serialization_with_workflow(self, dept_register_with_workflow):
        data = DepartmentalRiskRegisterSerializer(dept_register_with_workflow).data
        assert data['has_workflow'] is True
        assert data['has_active_workflow'] is True
        assert data['workflow_stage'] == 'rc_submit'

    @pytest.mark.django_db
    def test_gap18_endorsement_fields(self, dept_register):
        data = DepartmentalRiskRegisterSerializer(dept_register).data
        assert 'endorsed_by' in data
        assert 'endorsement_date' in data
        assert 'endorsement_document_id' in data


class TestDeptRegisterEntrySerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, dept_register_entry):
        data = DeptRegisterEntrySerializer(dept_register_entry).data
        assert data['sort_order'] == 1
        # Nested risk_sheet
        assert isinstance(data['risk_sheet'], dict)
        assert data['risk_sheet']['risk_title'] == 'System Downtime Risk'


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — Institutional Register & RTAP Serializer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestInstitutionalRiskRegisterSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, inst_register):
        data = InstitutionalRiskRegisterSerializer(inst_register).data
        assert data['prepared_by'] == str(RMQAM_USER_ID)
        assert data['status'] == 'draft'
        assert isinstance(data['fiscal_year'], dict)
        assert data['has_workflow'] is False

    @pytest.mark.django_db
    def test_gap03_fields(self, inst_register):
        data = InstitutionalRiskRegisterSerializer(inst_register).data
        assert 'committee_meeting_date' in data
        assert 'lsm_submission_date' in data

    @pytest.mark.django_db
    def test_drs_fields(self, inst_register):
        data = InstitutionalRiskRegisterSerializer(inst_register).data
        assert 'document_id' in data
        assert 'stamped_document_url' in data


class TestInstitutionalRiskEntrySerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, inst_entry):
        data = InstitutionalRiskEntrySerializer(inst_entry).data
        assert data['risk_ranking'] == 1
        assert data['notes'] == 'Highest risk entry'
        assert isinstance(data['risk_sheet'], dict)


class TestRiskTreatmentActionPlanSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, rtap):
        data = RiskTreatmentActionPlanSerializer(rtap).data
        assert data['status'] == 'draft'
        assert isinstance(data['inst_register'], dict)
        assert isinstance(data['fiscal_year'], dict)
        assert Decimal(data['overall_progress']) == Decimal('0.00')
        assert data['has_workflow'] is False

    @pytest.mark.django_db
    def test_overall_progress_read_only(self, rtap):
        payload = {
            'fiscal_year_id': str(rtap.fiscal_year_id),
            'prepared_by': str(RMQAM_USER_ID),
            'overall_progress': '99.99',
        }
        s = RiskTreatmentActionPlanSerializer(data=payload)
        assert s.is_valid(), s.errors
        assert 'overall_progress' not in s.validated_data


class TestRTAPItemSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, rtap_item):
        data = RTAPItemSerializer(rtap_item).data
        assert data['treatment_description'] == 'Implement redundant failover system'
        assert data['responsible_officer'] == str(OFFICER_USER_ID)
        assert data['status'] == 'not_started'
        assert isinstance(data['inst_entry'], dict)


class TestRTAPQuarterlyUpdateSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, rtap_quarterly_update):
        data = RTAPQuarterlyUpdateSerializer(rtap_quarterly_update).data
        assert data['status'] == 'in_progress'
        assert isinstance(data['evidence'], list)
        assert len(data['evidence']) == 1
        assert isinstance(data['quarter'], dict)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — Quarterly Reporting Serializer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestQuarterlyPerformanceReportSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, quarterly_report):
        data = QuarterlyPerformanceReportSerializer(quarterly_report).data
        assert data['total_risks'] == 15
        assert data['high_risks'] == 3
        assert data['medium_risks'] == 7
        assert data['low_risks'] == 5
        assert data['rtap_completed'] == 2
        assert data['rtap_in_progress'] == 5
        assert data['rtap_not_started'] == 8
        assert isinstance(data['fiscal_year'], dict)
        assert isinstance(data['quarter'], dict)

    @pytest.mark.django_db
    def test_gap12_iago_fields(self, quarterly_report):
        data = QuarterlyPerformanceReportSerializer(quarterly_report).data
        assert 'iago_submitted' in data
        assert 'iago_submission_date' in data
        assert 'iago_reference' in data

    @pytest.mark.django_db
    def test_workflow_properties(self, quarterly_report_with_workflow):
        data = QuarterlyPerformanceReportSerializer(quarterly_report_with_workflow).data
        assert data['has_workflow'] is True
        assert data['has_active_workflow'] is True
        assert data['workflow_stage'] == 'rmqam_prepare'


class TestActivityReportSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, activity_report):
        data = ActivityReportSerializer(activity_report).data
        assert data['reported_by'] == str(RC_USER_ID)
        assert 'Conducted departmental' in data['activities_summary']
        assert isinstance(data['inst_register'], dict)
        assert isinstance(data['quarter'], dict)
        assert isinstance(data['attachments'], list)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — QMS Audit Serializer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestQMSAuditProgramSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, qms_program):
        data = QMSAuditProgramSerializer(qms_program).data
        assert data['program_title'] == 'FY 2025/2026 Annual QMS Audit Program'
        assert data['status'] == 'approved'
        assert isinstance(data['fiscal_year'], dict)

    @pytest.mark.django_db
    def test_workflow_properties(self, qms_program_with_workflow):
        data = QMSAuditProgramSerializer(qms_program_with_workflow).data
        assert data['has_workflow'] is True
        assert data['workflow_stage'] == 'rmo_submit'


class TestQMSAuditPlanSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, qms_plan):
        data = QMSAuditPlanSerializer(qms_plan).data
        assert data['plan_title'] == 'ICT Directorate Audit'
        assert data['auditee_unit_id'] == str(AUDITEE_UNIT_UUID)
        assert data['status'] == 'approved'
        assert isinstance(data['audit_program'], dict)
        # GAP-04, GAP-10 fields
        assert data['nda_signed'] is True
        assert data['timetable_agreed'] is True

    @pytest.mark.django_db
    def test_gap17_review_fields(self, qms_plan):
        data = QMSAuditPlanSerializer(qms_plan).data
        assert 'last_review_comment' in data
        assert 'last_reviewed_by' in data
        assert 'last_reviewed_at' in data


class TestQMSAuditTeamAssignmentSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, team_assignment):
        data = QMSAuditTeamAssignmentSerializer(team_assignment).data
        assert data['auditor_id'] == str(QA_USER_ID)
        assert data['role'] == 'team_leader'


class TestAuditChecklistSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, audit_checklist):
        data = AuditChecklistSerializer(audit_checklist).data
        assert data['conformity'] == 'conforming'
        assert isinstance(data['findings_detail'], dict)
        assert isinstance(data['iso_clause'], dict)


class TestQMSAuditReportSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, qms_report):
        data = QMSAuditReportSerializer(qms_report).data
        assert data['report_title'] == 'ICT Directorate QMS Audit Report'
        assert data['status'] == 'draft'
        assert isinstance(data['audit_plan'], dict)
        # Signature fields
        assert data['tl_signed_by'] is None
        assert data['tl_signed_at'] is None
        assert data['auditee_signed_by'] is None
        assert data['auditee_signed_at'] is None

    @pytest.mark.django_db
    def test_signature_times_read_only(self, qms_report):
        payload = {
            'report_title': 'Updated Report',
            'tl_signed_at': '2026-01-25T10:00:00Z',
            'auditee_signed_at': '2026-01-26T10:00:00Z',
        }
        s = QMSAuditReportSerializer(qms_report, data=payload, partial=True)
        assert s.is_valid(), s.errors
        assert 'tl_signed_at' not in s.validated_data
        assert 'auditee_signed_at' not in s.validated_data


class TestNonConformanceSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, nonconformance):
        data = NonConformanceSerializer(nonconformance).data
        assert data['status'] == 'raised'
        assert data['raised_by'] == str(QA_USER_ID)
        assert isinstance(data['iso_clause'], dict)
        assert isinstance(data['nc_type'], dict)
        assert 'closed_at' in data
        assert data['closed_at'] is None

    @pytest.mark.django_db
    def test_closed_at_read_only(self, nonconformance):
        payload = {
            'closed_at': '2026-03-01T12:00:00Z',
        }
        s = NonConformanceSerializer(nonconformance, data=payload, partial=True)
        assert s.is_valid(), s.errors
        assert 'closed_at' not in s.validated_data


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — Meeting & Workshop Serializer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskMeetingSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, risk_meeting):
        data = RiskMeetingSerializer(risk_meeting).data
        assert data['meeting_type'] == 'risk_discussion'
        assert data['title'] == 'Q1 Risk Discussion Meeting'
        assert data['status'] == 'scheduled'
        assert isinstance(data['fiscal_year'], dict)
        assert isinstance(data['outcomes'], list)


class TestMeetingAttendanceSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, meeting_attendance):
        data = MeetingAttendanceSerializer(meeting_attendance).data
        assert data['user_id'] == str(RC_USER_ID)
        assert data['attended'] is True


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 8 — QMS Audit Support Serializer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestQMSAuditMeetingSerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, qms_audit_meeting):
        data = QMSAuditMeetingSerializer(qms_audit_meeting).data
        assert data['meeting_type'] == 'entry'
        assert data['timetable_agreed'] is True
        assert isinstance(data['attendance'], list)


class TestQMSAuditTimetableEntrySerializer:
    @pytest.mark.django_db
    def test_serialization_fields(self, timetable_entry):
        data = QMSAuditTimetableEntrySerializer(timetable_entry).data
        assert data['process_or_area'] == 'Software Development Process'
        assert data['assigned_auditor'] == str(QA_USER_ID)
        assert data['sort_order'] == 1
