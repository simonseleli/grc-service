"""
Risk Management Module — Domain Events
Events related to risk champions, risk registers, RTAP, quarterly reports,
quality auditors, and QMS audits.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from . import GRCDomainEvent


# ── Risk Champion Events ───────────────────────────────────────────────

@dataclass
class RiskChampionAppointedEvent(GRCDomainEvent):
    """A risk champion appointment was approved (DG signed)"""

    champion_id: str = field(default='')
    appointment_id: str = field(default='')
    champion_user_id: str = field(default='')
    org_unit_id: str = field(default='')
    org_unit_type: str = field(default='')
    appointed_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.risk.champion.appointed'
        self.aggregate_id = self.appointment_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'champion_id': self.champion_id,
            'appointment_id': self.appointment_id,
            'champion_user_id': self.champion_user_id,
            'org_unit_id': self.org_unit_id,
            'org_unit_type': self.org_unit_type,
            'appointed_by': self.appointed_by,
        }


# ── Risk Register Events ──────────────────────────────────────────────

@dataclass
class DeptRiskRegisterApprovedEvent(GRCDomainEvent):
    """A departmental risk register was approved"""

    register_id: str = field(default='')
    org_unit_id: str = field(default='')
    fiscal_year_code: str = field(default='')
    approved_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.risk.register.departmental.approved'
        self.aggregate_id = self.register_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'register_id': self.register_id,
            'register_type': 'departmental',
            'org_unit_id': self.org_unit_id,
            'fiscal_year_code': self.fiscal_year_code,
            'approved_by': self.approved_by,
        }


@dataclass
class InstitutionalRiskRegisterSubmittedEvent(GRCDomainEvent):
    """An institutional risk register was submitted for approval"""

    register_id: str = field(default='')
    fiscal_year_code: str = field(default='')
    submitted_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.risk.register.institutional.submitted'
        self.aggregate_id = self.register_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'register_id': self.register_id,
            'register_type': 'institutional',
            'fiscal_year_code': self.fiscal_year_code,
            'submitted_by': self.submitted_by,
        }


# ── RTAP Events ───────────────────────────────────────────────────────

@dataclass
class RTAPApprovedEvent(GRCDomainEvent):
    """A Risk Treatment Action Plan was approved"""

    rtap_id: str = field(default='')
    fiscal_year_code: str = field(default='')
    approved_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.risk.rtap.approved'
        self.aggregate_id = self.rtap_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'rtap_id': self.rtap_id,
            'fiscal_year_code': self.fiscal_year_code,
            'approved_by': self.approved_by,
        }


@dataclass
class RTAPUpdatedEvent(GRCDomainEvent):
    """An RTAP quarterly update was submitted"""

    rtap_id: str = field(default='')
    rtap_item_id: str = field(default='')
    quarter: str = field(default='')
    new_status: str = field(default='')
    updated_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.risk.rtap.updated'
        self.aggregate_id = self.rtap_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'rtap_id': self.rtap_id,
            'rtap_item_id': self.rtap_item_id,
            'quarter': self.quarter,
            'new_status': self.new_status,
            'updated_by': self.updated_by,
        }


# ── Quarterly Risk Report Events ──────────────────────────────────────

@dataclass
class QuarterlyRiskReportSubmittedEvent(GRCDomainEvent):
    """A quarterly performance report was submitted"""

    report_id: str = field(default='')
    fiscal_year_code: str = field(default='')
    quarter: str = field(default='')
    submitted_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.risk.quarterly_report.submitted'
        self.aggregate_id = self.report_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'fiscal_year_code': self.fiscal_year_code,
            'quarter': self.quarter,
            'submitted_by': self.submitted_by,
        }


# ── Quality Auditor Events ────────────────────────────────────────────

@dataclass
class QualityAuditorAppointedEvent(GRCDomainEvent):
    """A quality auditor appointment was approved (DG signed)"""

    auditor_id: str = field(default='')
    appointment_id: str = field(default='')
    auditor_user_id: str = field(default='')
    org_unit_id: str = field(default='')
    appointed_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.risk.qa.appointed'
        self.aggregate_id = self.appointment_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'auditor_id': self.auditor_id,
            'appointment_id': self.appointment_id,
            'auditor_user_id': self.auditor_user_id,
            'org_unit_id': self.org_unit_id,
            'appointed_by': self.appointed_by,
        }


# ── QMS Audit Events ──────────────────────────────────────────────────

@dataclass
class NonConformanceRaisedEvent(GRCDomainEvent):
    """A non-conformance was raised from a QMS audit"""

    nc_id: str = field(default='')
    audit_report_id: str = field(default='')
    iso_clause: str = field(default='')
    nc_type: str = field(default='')
    description: str = field(default='')
    raised_by: str = field(default='')
    responsible_officer: Optional[str] = field(default=None)

    def __post_init__(self):
        self.event_type = 'grc.qms.audit.nc.raised'
        self.aggregate_id = self.nc_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'nc_id': self.nc_id,
            'audit_report_id': self.audit_report_id,
            'iso_clause': self.iso_clause,
            'nc_type': self.nc_type,
            'description': self.description,
            'raised_by': self.raised_by,
            'responsible_officer': self.responsible_officer,
        }


@dataclass
class QMSAuditReportSignedEvent(GRCDomainEvent):
    """A QMS audit report was signed (Team Leader or Auditee)"""

    report_id: str = field(default='')
    audit_plan_id: str = field(default='')
    signed_by: str = field(default='')
    signature_type: str = field(default='')  # 'team_leader' | 'auditee'

    def __post_init__(self):
        self.event_type = 'grc.qms.audit.report.signed'
        self.aggregate_id = self.report_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'audit_plan_id': self.audit_plan_id,
            'signed_by': self.signed_by,
            'signature_type': self.signature_type,
        }
