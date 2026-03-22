"""
Risk Management Module — Domain Events & Kafka Tests

Covers:
  - Event type constants (presence in registry + values)
  - Event dataclass creation, serialization, and topic routing
  - KafkaMessagingService publish methods (happy path + unknown event type)
"""

import uuid
from unittest.mock import patch, MagicMock

import pytest

from apps.core.events import GRCDomainEvent
from apps.core.events.risk_events import (
    RiskChampionAppointedEvent,
    DeptRiskRegisterApprovedEvent,
    InstitutionalRiskRegisterSubmittedEvent,
    RTAPApprovedEvent,
    RTAPUpdatedEvent,
    QuarterlyRiskReportSubmittedEvent,
    QualityAuditorAppointedEvent,
    NonConformanceRaisedEvent,
    QMSAuditReportSignedEvent,
)
from shared.constants.event_types import (
    ALL_GRC_EVENT_TYPES,
    RISK_CHAMPION_EVENTS,
    RISK_REGISTER_EVENTS,
    RTAP_EVENTS,
    QUARTERLY_RISK_REPORT_EVENTS,
    QA_EVENTS,
    QMS_AUDIT_EVENTS,
)

MSG_SVC_MODULE = "apps.infrastructure.services.messaging_service"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Event Type Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventTypeConstants:
    """Verify every risk/QMS constant exists and is aggregated."""

    EXPECTED_EVENT_TYPES = {
        'grc.risk.champion.appointed',
        'grc.risk.register.departmental.approved',
        'grc.risk.register.institutional.submitted',
        'grc.risk.rtap.approved',
        'grc.risk.rtap.updated',
        'grc.risk.quarterly_report.submitted',
        'grc.risk.qa.appointed',
        'grc.qms.audit.nc.raised',
        'grc.qms.audit.report.signed',
    }

    def test_risk_champion_events_values(self):
        assert RISK_CHAMPION_EVENTS['CHAMPION_APPOINTED'] == 'grc.risk.champion.appointed'

    def test_risk_register_events_values(self):
        assert RISK_REGISTER_EVENTS['DEPARTMENTAL_APPROVED'] == 'grc.risk.register.departmental.approved'
        assert RISK_REGISTER_EVENTS['INSTITUTIONAL_SUBMITTED'] == 'grc.risk.register.institutional.submitted'

    def test_rtap_events_values(self):
        assert RTAP_EVENTS['RTAP_APPROVED'] == 'grc.risk.rtap.approved'
        assert RTAP_EVENTS['RTAP_UPDATED'] == 'grc.risk.rtap.updated'

    def test_quarterly_risk_report_events_values(self):
        assert QUARTERLY_RISK_REPORT_EVENTS['RISK_REPORT_SUBMITTED'] == 'grc.risk.quarterly_report.submitted'

    def test_qa_events_values(self):
        assert QA_EVENTS['QA_APPOINTED'] == 'grc.risk.qa.appointed'

    def test_qms_audit_events_values(self):
        assert QMS_AUDIT_EVENTS['NC_RAISED'] == 'grc.qms.audit.nc.raised'
        assert QMS_AUDIT_EVENTS['REPORT_SIGNED'] == 'grc.qms.audit.report.signed'

    def test_all_risk_events_in_aggregate(self):
        aggregate_values = set(ALL_GRC_EVENT_TYPES.values())
        for et in self.EXPECTED_EVENT_TYPES:
            assert et in aggregate_values, f"{et} missing from ALL_GRC_EVENT_TYPES"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Event Dataclass Creation & Serialization
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskChampionAppointedEvent:

    def test_inherits_from_base(self):
        event = RiskChampionAppointedEvent()
        assert isinstance(event, GRCDomainEvent)

    def test_post_init_sets_event_type(self):
        event = RiskChampionAppointedEvent()
        assert event.event_type == 'grc.risk.champion.appointed'

    def test_aggregate_id_is_appointment_id(self):
        event = RiskChampionAppointedEvent(appointment_id='appt-123')
        assert event.aggregate_id == 'appt-123'

    def test_to_dict_contains_event_data(self):
        event = RiskChampionAppointedEvent(
            champion_id='ch-1', appointment_id='appt-1',
            champion_user_id='u-1', org_unit_id='ou-1',
            org_unit_type='department', appointed_by='u-2',
        )
        d = event.to_dict()
        assert d['event_type'] == 'grc.risk.champion.appointed'
        assert d['data']['champion_id'] == 'ch-1'
        assert d['data']['org_unit_type'] == 'department'
        assert d['data']['appointed_by'] == 'u-2'

    def test_topic_follows_fims_convention(self):
        event = RiskChampionAppointedEvent()
        assert event.topic == 'fims.grc.risk.champion.appointed'


class TestDeptRiskRegisterApprovedEvent:

    def test_post_init_sets_event_type(self):
        event = DeptRiskRegisterApprovedEvent()
        assert event.event_type == 'grc.risk.register.departmental.approved'

    def test_aggregate_id_is_register_id(self):
        event = DeptRiskRegisterApprovedEvent(register_id='reg-1')
        assert event.aggregate_id == 'reg-1'

    def test_event_data_includes_register_type(self):
        event = DeptRiskRegisterApprovedEvent(register_id='reg-1', org_unit_id='ou-1')
        data = event._get_event_data()
        assert data['register_type'] == 'departmental'
        assert data['org_unit_id'] == 'ou-1'

    def test_topic(self):
        event = DeptRiskRegisterApprovedEvent()
        assert event.topic == 'fims.grc.risk.register.departmental.approved'


class TestInstitutionalRiskRegisterSubmittedEvent:

    def test_event_type(self):
        event = InstitutionalRiskRegisterSubmittedEvent()
        assert event.event_type == 'grc.risk.register.institutional.submitted'

    def test_event_data_includes_register_type(self):
        event = InstitutionalRiskRegisterSubmittedEvent(register_id='r-1', submitted_by='u-1')
        data = event._get_event_data()
        assert data['register_type'] == 'institutional'
        assert data['submitted_by'] == 'u-1'

    def test_topic(self):
        event = InstitutionalRiskRegisterSubmittedEvent()
        assert event.topic == 'fims.grc.risk.register.institutional.submitted'


class TestRTAPApprovedEvent:

    def test_event_type_and_aggregate(self):
        event = RTAPApprovedEvent(rtap_id='rtap-1')
        assert event.event_type == 'grc.risk.rtap.approved'
        assert event.aggregate_id == 'rtap-1'

    def test_event_data(self):
        event = RTAPApprovedEvent(rtap_id='rtap-1', fiscal_year_code='2025/26', approved_by='u-1')
        data = event._get_event_data()
        assert data['fiscal_year_code'] == '2025/26'

    def test_topic(self):
        assert RTAPApprovedEvent().topic == 'fims.grc.risk.rtap.approved'


class TestRTAPUpdatedEvent:

    def test_event_type(self):
        event = RTAPUpdatedEvent()
        assert event.event_type == 'grc.risk.rtap.updated'

    def test_event_data(self):
        event = RTAPUpdatedEvent(
            rtap_id='r-1', rtap_item_id='ri-1',
            quarter='Q2', new_status='completed', updated_by='u-1',
        )
        data = event._get_event_data()
        assert data['rtap_item_id'] == 'ri-1'
        assert data['quarter'] == 'Q2'
        assert data['new_status'] == 'completed'


class TestQuarterlyRiskReportSubmittedEvent:

    def test_event_type_and_aggregate(self):
        event = QuarterlyRiskReportSubmittedEvent(report_id='rpt-1')
        assert event.event_type == 'grc.risk.quarterly_report.submitted'
        assert event.aggregate_id == 'rpt-1'

    def test_event_data(self):
        event = QuarterlyRiskReportSubmittedEvent(
            report_id='rpt-1', fiscal_year_code='2025/26', quarter='Q1', submitted_by='u-1',
        )
        data = event._get_event_data()
        assert data['quarter'] == 'Q1'
        assert data['submitted_by'] == 'u-1'


class TestQualityAuditorAppointedEvent:

    def test_event_type(self):
        event = QualityAuditorAppointedEvent()
        assert event.event_type == 'grc.risk.qa.appointed'

    def test_aggregate_is_appointment_id(self):
        event = QualityAuditorAppointedEvent(appointment_id='appt-qa-1')
        assert event.aggregate_id == 'appt-qa-1'

    def test_event_data(self):
        event = QualityAuditorAppointedEvent(
            auditor_id='a-1', appointment_id='appt-1',
            auditor_user_id='u-1', org_unit_id='ou-1', appointed_by='u-2',
        )
        data = event._get_event_data()
        assert data['auditor_user_id'] == 'u-1'
        assert data['appointed_by'] == 'u-2'


class TestNonConformanceRaisedEvent:

    def test_event_type(self):
        event = NonConformanceRaisedEvent()
        assert event.event_type == 'grc.qms.audit.nc.raised'

    def test_aggregate_is_nc_id(self):
        event = NonConformanceRaisedEvent(nc_id='nc-1')
        assert event.aggregate_id == 'nc-1'

    def test_event_data_includes_optional_responsible_officer(self):
        event = NonConformanceRaisedEvent(
            nc_id='nc-1', audit_report_id='ar-1', iso_clause='7.1.2',
            nc_type='major', description='Finding X', raised_by='u-1',
            responsible_officer='u-3',
        )
        data = event._get_event_data()
        assert data['nc_type'] == 'major'
        assert data['responsible_officer'] == 'u-3'

    def test_responsible_officer_defaults_to_none(self):
        event = NonConformanceRaisedEvent()
        assert event._get_event_data()['responsible_officer'] is None


class TestQMSAuditReportSignedEvent:

    def test_event_type(self):
        event = QMSAuditReportSignedEvent()
        assert event.event_type == 'grc.qms.audit.report.signed'

    def test_aggregate_is_report_id(self):
        event = QMSAuditReportSignedEvent(report_id='rpt-1')
        assert event.aggregate_id == 'rpt-1'

    def test_event_data(self):
        event = QMSAuditReportSignedEvent(
            report_id='rpt-1', audit_plan_id='ap-1',
            signed_by='u-1', signature_type='team_leader',
        )
        data = event._get_event_data()
        assert data['signature_type'] == 'team_leader'
        assert data['audit_plan_id'] == 'ap-1'


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Messaging Service Publish Methods
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def messaging_svc():
    """Import the messaging service with Kafka producer mocked out."""
    with patch(f"{MSG_SVC_MODULE}.publish_event") as mock_pub:
        from apps.infrastructure.services.messaging_service import KafkaMessagingService
        svc = KafkaMessagingService()
        yield svc, mock_pub


class TestPublishRiskChampionEvent:

    def test_happy_path(self, messaging_svc):
        svc, mock_pub = messaging_svc
        champion_id = uuid.uuid4()
        result = svc.publish_risk_champion_event(
            event_type=RISK_CHAMPION_EVENTS['CHAMPION_APPOINTED'],
            champion_id=champion_id,
            additional_data={
                'appointment_id': 'appt-1',
                'champion_user_id': 'u-1',
                'org_unit_id': 'ou-1',
                'org_unit_type': 'department',
                'appointed_by': 'u-2',
            },
        )
        assert result is True
        mock_pub.assert_called_once()
        event = mock_pub.call_args[0][0]
        assert isinstance(event, RiskChampionAppointedEvent)
        assert event.champion_id == str(champion_id)

    def test_unknown_event_type_returns_false(self, messaging_svc):
        svc, mock_pub = messaging_svc
        result = svc.publish_risk_champion_event(
            event_type='grc.risk.champion.unknown',
            champion_id=uuid.uuid4(),
        )
        assert result is False
        mock_pub.assert_not_called()


class TestPublishRiskRegisterEvent:

    def test_departmental_approved(self, messaging_svc):
        svc, mock_pub = messaging_svc
        reg_id = uuid.uuid4()
        result = svc.publish_risk_register_event(
            event_type=RISK_REGISTER_EVENTS['DEPARTMENTAL_APPROVED'],
            register_id=reg_id,
            additional_data={'org_unit_id': 'ou-1', 'fiscal_year_code': '2025/26', 'approved_by': 'u-1'},
        )
        assert result is True
        event = mock_pub.call_args[0][0]
        assert isinstance(event, DeptRiskRegisterApprovedEvent)

    def test_institutional_submitted(self, messaging_svc):
        svc, mock_pub = messaging_svc
        reg_id = uuid.uuid4()
        result = svc.publish_risk_register_event(
            event_type=RISK_REGISTER_EVENTS['INSTITUTIONAL_SUBMITTED'],
            register_id=reg_id,
            additional_data={'fiscal_year_code': '2025/26', 'submitted_by': 'u-1'},
        )
        assert result is True
        event = mock_pub.call_args[0][0]
        assert isinstance(event, InstitutionalRiskRegisterSubmittedEvent)

    def test_unknown_type_returns_false(self, messaging_svc):
        svc, mock_pub = messaging_svc
        result = svc.publish_risk_register_event(
            event_type='grc.risk.register.unknown',
            register_id=uuid.uuid4(),
        )
        assert result is False
        mock_pub.assert_not_called()


class TestPublishRTAPEvent:

    def test_rtap_approved(self, messaging_svc):
        svc, mock_pub = messaging_svc
        rtap_id = uuid.uuid4()
        result = svc.publish_rtap_event(
            event_type=RTAP_EVENTS['RTAP_APPROVED'],
            rtap_id=rtap_id,
            additional_data={'fiscal_year_code': '2025/26', 'approved_by': 'u-1'},
        )
        assert result is True
        event = mock_pub.call_args[0][0]
        assert isinstance(event, RTAPApprovedEvent)

    def test_rtap_updated(self, messaging_svc):
        svc, mock_pub = messaging_svc
        rtap_id = uuid.uuid4()
        result = svc.publish_rtap_event(
            event_type=RTAP_EVENTS['RTAP_UPDATED'],
            rtap_id=rtap_id,
            additional_data={
                'rtap_item_id': 'ri-1', 'quarter': 'Q2',
                'new_status': 'completed', 'updated_by': 'u-1',
            },
        )
        assert result is True
        event = mock_pub.call_args[0][0]
        assert isinstance(event, RTAPUpdatedEvent)
        assert event.quarter == 'Q2'

    def test_unknown_type_returns_false(self, messaging_svc):
        svc, mock_pub = messaging_svc
        result = svc.publish_rtap_event(
            event_type='grc.risk.rtap.unknown',
            rtap_id=uuid.uuid4(),
        )
        assert result is False


class TestPublishQuarterlyReportEvent:

    def test_report_submitted(self, messaging_svc):
        svc, mock_pub = messaging_svc
        rpt_id = uuid.uuid4()
        result = svc.publish_quarterly_report_event(
            event_type=QUARTERLY_RISK_REPORT_EVENTS['RISK_REPORT_SUBMITTED'],
            report_id=rpt_id,
            additional_data={'fiscal_year_code': '2025/26', 'quarter': 'Q1', 'submitted_by': 'u-1'},
        )
        assert result is True
        event = mock_pub.call_args[0][0]
        assert isinstance(event, QuarterlyRiskReportSubmittedEvent)

    def test_unknown_type_returns_false(self, messaging_svc):
        svc, mock_pub = messaging_svc
        result = svc.publish_quarterly_report_event(
            event_type='grc.risk.quarterly_report.unknown',
            report_id=uuid.uuid4(),
        )
        assert result is False


class TestPublishQAEvent:

    def test_qa_appointed(self, messaging_svc):
        svc, mock_pub = messaging_svc
        auditor_id = uuid.uuid4()
        result = svc.publish_qa_event(
            event_type=QA_EVENTS['QA_APPOINTED'],
            auditor_id=auditor_id,
            additional_data={
                'appointment_id': 'appt-1', 'auditor_user_id': 'u-1',
                'org_unit_id': 'ou-1', 'appointed_by': 'u-2',
            },
        )
        assert result is True
        event = mock_pub.call_args[0][0]
        assert isinstance(event, QualityAuditorAppointedEvent)

    def test_unknown_type_returns_false(self, messaging_svc):
        svc, mock_pub = messaging_svc
        result = svc.publish_qa_event(
            event_type='grc.risk.qa.unknown',
            auditor_id=uuid.uuid4(),
        )
        assert result is False


class TestPublishQMSAuditEvent:

    def test_nc_raised(self, messaging_svc):
        svc, mock_pub = messaging_svc
        nc_id = uuid.uuid4()
        result = svc.publish_qms_audit_event(
            event_type=QMS_AUDIT_EVENTS['NC_RAISED'],
            entity_id=nc_id,
            additional_data={
                'audit_report_id': 'ar-1', 'iso_clause': '7.1.2',
                'nc_type': 'major', 'description': 'Finding X',
                'raised_by': 'u-1', 'responsible_officer': 'u-3',
            },
        )
        assert result is True
        event = mock_pub.call_args[0][0]
        assert isinstance(event, NonConformanceRaisedEvent)
        assert event.nc_type == 'major'

    def test_report_signed(self, messaging_svc):
        svc, mock_pub = messaging_svc
        rpt_id = uuid.uuid4()
        result = svc.publish_qms_audit_event(
            event_type=QMS_AUDIT_EVENTS['REPORT_SIGNED'],
            entity_id=rpt_id,
            additional_data={
                'audit_plan_id': 'ap-1', 'signed_by': 'u-1',
                'signature_type': 'team_leader',
            },
        )
        assert result is True
        event = mock_pub.call_args[0][0]
        assert isinstance(event, QMSAuditReportSignedEvent)
        assert event.signature_type == 'team_leader'

    def test_unknown_type_returns_false(self, messaging_svc):
        svc, mock_pub = messaging_svc
        result = svc.publish_qms_audit_event(
            event_type='grc.qms.audit.unknown',
            entity_id=uuid.uuid4(),
        )
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Serialization Round-Trip
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventSerialization:
    """Ensure to_dict() produces well-formed payloads for all 9 events."""

    ALL_EVENT_CLASSES = [
        (RiskChampionAppointedEvent, {'champion_id': 'c1', 'appointment_id': 'a1'}),
        (DeptRiskRegisterApprovedEvent, {'register_id': 'r1'}),
        (InstitutionalRiskRegisterSubmittedEvent, {'register_id': 'r2'}),
        (RTAPApprovedEvent, {'rtap_id': 'rt1'}),
        (RTAPUpdatedEvent, {'rtap_id': 'rt1', 'rtap_item_id': 'ri1'}),
        (QuarterlyRiskReportSubmittedEvent, {'report_id': 'rp1'}),
        (QualityAuditorAppointedEvent, {'auditor_id': 'qa1', 'appointment_id': 'a2'}),
        (NonConformanceRaisedEvent, {'nc_id': 'nc1'}),
        (QMSAuditReportSignedEvent, {'report_id': 'rp2'}),
    ]

    @pytest.mark.parametrize("cls,kwargs", ALL_EVENT_CLASSES)
    def test_to_dict_has_required_keys(self, cls, kwargs):
        event = cls(**kwargs)
        d = event.to_dict()
        for key in ('event_id', 'event_type', 'timestamp', 'service_name', 'aggregate_id', 'data'):
            assert key in d, f"Missing key '{key}' in {cls.__name__}.to_dict()"

    @pytest.mark.parametrize("cls,kwargs", ALL_EVENT_CLASSES)
    def test_topic_starts_with_fims(self, cls, kwargs):
        event = cls(**kwargs)
        assert event.topic.startswith('fims.grc.')

    @pytest.mark.parametrize("cls,kwargs", ALL_EVENT_CLASSES)
    def test_service_name_is_grc(self, cls, kwargs):
        event = cls(**kwargs)
        assert event.service_name == 'grc-service'
