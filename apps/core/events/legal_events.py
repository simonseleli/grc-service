"""
Legal Module — Domain Events
Events related to legal cases, meetings, minutes, directives, judgments, and filings
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from . import GRCDomainEvent


# ── Case Events ────────────────────────────────────────────────────────

@dataclass
class LegalCaseCreatedEvent(GRCDomainEvent):
    """A litigation case (defendant or plaintiff) was created"""

    case_id: str = field(default='')
    case_type: str = field(default='')          # 'defendant' | 'plaintiff'
    reference_number: str = field(default='')
    case_title: str = field(default='')
    court_level: str = field(default='')
    created_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.case.created'
        self.aggregate_id = self.case_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'case_id': self.case_id,
            'case_type': self.case_type,
            'reference_number': self.reference_number,
            'case_title': self.case_title,
            'court_level': self.court_level,
            'created_by': self.created_by,
        }


@dataclass
class LegalCaseClosedEvent(GRCDomainEvent):
    """A litigation case was closed"""

    case_id: str = field(default='')
    case_type: str = field(default='')
    reference_number: str = field(default='')
    closed_by: str = field(default='')
    closure_reason: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.case.closed'
        self.aggregate_id = self.case_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'case_id': self.case_id,
            'case_type': self.case_type,
            'reference_number': self.reference_number,
            'closed_by': self.closed_by,
            'closure_reason': self.closure_reason,
        }


# ── Judgment Events ────────────────────────────────────────────────────

@dataclass
class LegalJudgmentRecordedEvent(GRCDomainEvent):
    """A judgment (defendant or plaintiff) was recorded"""

    judgment_id: str = field(default='')
    case_id: str = field(default='')
    case_type: str = field(default='')
    judgment_date: str = field(default='')
    outcome: str = field(default='')
    recorded_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.judgment.recorded'
        self.aggregate_id = self.judgment_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'judgment_id': self.judgment_id,
            'case_id': self.case_id,
            'case_type': self.case_type,
            'judgment_date': self.judgment_date,
            'outcome': self.outcome,
            'recorded_by': self.recorded_by,
        }


# ── Meeting Events ─────────────────────────────────────────────────────

@dataclass
class LegalMeetingCompletedEvent(GRCDomainEvent):
    """A legal meeting was completed"""

    meeting_id: str = field(default='')
    meeting_type: str = field(default='')
    governing_body_id: str = field(default='')
    reference_number: str = field(default='')
    completed_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.meeting.completed'
        self.aggregate_id = self.meeting_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'meeting_id': self.meeting_id,
            'meeting_type': self.meeting_type,
            'governing_body_id': self.governing_body_id,
            'reference_number': self.reference_number,
            'completed_by': self.completed_by,
        }


@dataclass
class LegalMeetingInvitationsSentEvent(GRCDomainEvent):
    """Invitations were sent for a legal meeting (status → invitations_sent)"""

    meeting_id: str = field(default='')
    governing_body_id: str = field(default='')
    reference_number: str = field(default='')
    participant_count: int = field(default=0)
    sent_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.meeting.invitations_sent'
        self.aggregate_id = self.meeting_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'meeting_id': self.meeting_id,
            'governing_body_id': self.governing_body_id,
            'reference_number': self.reference_number,
            'participant_count': self.participant_count,
            'sent_by': self.sent_by,
        }


# ── Minutes Events ─────────────────────────────────────────────────────

@dataclass
class LegalMinutesApprovedEvent(GRCDomainEvent):
    """Meeting minutes were approved via workflow"""

    minutes_id: str = field(default='')
    meeting_id: str = field(default='')
    reference_number: str = field(default='')
    approved_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.minutes.approved'
        self.aggregate_id = self.minutes_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'minutes_id': self.minutes_id,
            'meeting_id': self.meeting_id,
            'reference_number': self.reference_number,
            'approved_by': self.approved_by,
        }


# ── Directive Events ───────────────────────────────────────────────────

@dataclass
class LegalDirectiveOverdueEvent(GRCDomainEvent):
    """A meeting directive was marked overdue by Celery task"""

    directive_id: str = field(default='')
    minutes_id: str = field(default='')
    meeting_id: str = field(default='')
    due_date: str = field(default='')
    assigned_to: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.directive.overdue'
        self.aggregate_id = self.directive_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'directive_id': self.directive_id,
            'minutes_id': self.minutes_id,
            'meeting_id': self.meeting_id,
            'due_date': self.due_date,
            'assigned_to': self.assigned_to,
        }


# ── Filing Events ──────────────────────────────────────────────────────

@dataclass
class LegalFilingApprovedEvent(GRCDomainEvent):
    """A court filing was approved via workflow"""

    filing_id: str = field(default='')
    case_id: str = field(default='')
    filing_type: str = field(default='')
    reference_number: str = field(default='')
    approved_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.filing.approved'
        self.aggregate_id = self.filing_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'filing_id': self.filing_id,
            'case_id': self.case_id,
            'filing_type': self.filing_type,
            'reference_number': self.reference_number,
            'approved_by': self.approved_by,
        }


# ── Settlement Events ─────────────────────────────────────────────────

@dataclass
class LegalSettlementApprovedEvent(GRCDomainEvent):
    """A settlement was approved via workflow"""

    settlement_id: str = field(default='')
    case_id: str = field(default='')
    settlement_amount: str = field(default='')
    approved_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.settlement.approved'
        self.aggregate_id = self.settlement_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'settlement_id': self.settlement_id,
            'case_id': self.case_id,
            'settlement_amount': self.settlement_amount,
            'approved_by': self.approved_by,
        }


# ── Legal Notice Events ───────────────────────────────────────────────

@dataclass
class LegalNoticeIssuedEvent(GRCDomainEvent):
    """A legal notice was issued"""

    notice_id: str = field(default='')
    notice_type: str = field(default='')
    reference_number: str = field(default='')
    issued_by: str = field(default='')
    recipient: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.legal.notice.issued'
        self.aggregate_id = self.notice_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'notice_id': self.notice_id,
            'notice_type': self.notice_type,
            'reference_number': self.reference_number,
            'issued_by': self.issued_by,
            'recipient': self.recipient,
        }
