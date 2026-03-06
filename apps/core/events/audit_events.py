"""
Audit Engagement Domain Events
Events related to audit engagements and working papers
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from . import GRCDomainEvent


@dataclass
class AuditEngagementCreatedEvent(GRCDomainEvent):
    """Audit engagement was created"""
    
    engagement_id: str = field(default='')
    engagement_title: str = field(default='')
    engagement_type: str = field(default='')
    fiscal_year: str = field(default='')
    auditable_entity_id: str = field(default='')
    created_by: str = field(default='')
    
    def __post_init__(self):
        self.event_type = 'grc.audit.engagement.created'
        self.aggregate_id = self.engagement_id
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'engagement_id': self.engagement_id,
            'title': self.engagement_title,
            'engagement_type': self.engagement_type,
            'fiscal_year': self.fiscal_year,
            'auditable_entity_id': self.auditable_entity_id,
            'created_by': self.created_by
        }


@dataclass
class AuditEngagementUpdatedEvent(GRCDomainEvent):
    """Audit engagement was updated"""
    
    engagement_id: str = field(default='')
    engagement_title: str = field(default='')
    updated_by: str = field(default='')
    changes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.event_type = 'grc.audit.engagement.updated'
        self.aggregate_id = self.engagement_id
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'engagement_id': self.engagement_id,
            'title': self.engagement_title,
            'updated_by': self.updated_by,
            'changes': self.changes
        }


@dataclass
class WorkingPaperCreatedEvent(GRCDomainEvent):
    """Working paper was created"""
    
    working_paper_id: str = field(default='')
    engagement_id: str = field(default='')
    title: str = field(default='')
    paper_type: str = field(default='')
    document_id: Optional[str] = field(default=None)
    created_by: str = field(default='')
    
    def __post_init__(self):
        self.event_type = 'grc.working.paper.created'
        self.aggregate_id = self.working_paper_id
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'working_paper_id': self.working_paper_id,
            'engagement_id': self.engagement_id,
            'title': self.title,
            'paper_type': self.paper_type,
            'document_id': self.document_id,
            'created_by': self.created_by
        }


@dataclass
class WorkingPaperSubmittedEvent(GRCDomainEvent):
    """Working paper was submitted for review"""
    
    working_paper_id: str = field(default='')
    engagement_id: str = field(default='')
    title: str = field(default='')
    submitted_by: str = field(default='')
    reviewer_id: Optional[str] = field(default=None)
    
    def __post_init__(self):
        self.event_type = 'grc.working.paper.submitted'
        self.aggregate_id = self.working_paper_id
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'working_paper_id': self.working_paper_id,
            'engagement_id': self.engagement_id,
            'title': self.title,
            'submitted_by': self.submitted_by,
            'reviewer_id': self.reviewer_id
        }


@dataclass
class WorkingPaperApprovedEvent(GRCDomainEvent):
    """Working paper was approved"""
    
    working_paper_id: str = field(default='')
    engagement_id: str = field(default='')
    title: str = field(default='')
    approved_by: str = field(default='')
    
    def __post_init__(self):
        self.event_type = 'grc.working.paper.approved'
        self.aggregate_id = self.working_paper_id
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'working_paper_id': self.working_paper_id,
            'engagement_id': self.engagement_id,
            'title': self.title,
            'approved_by': self.approved_by
        }


@dataclass
class WorkingPaperRejectedEvent(GRCDomainEvent):
    """Working paper was rejected"""
    
    working_paper_id: str = field(default='')
    engagement_id: str = field(default='')
    title: str = field(default='')
    rejected_by: str = field(default='')
    reason: str = field(default='')
    
    def __post_init__(self):
        self.event_type = 'grc.working.paper.rejected'
        self.aggregate_id = self.working_paper_id
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'working_paper_id': self.working_paper_id,
            'engagement_id': self.engagement_id,
            'title': self.title,
            'rejected_by': self.rejected_by,
            'reason': self.reason
        }


@dataclass
class AuditFindingCreatedEvent(GRCDomainEvent):
    """Audit finding was created"""
    
    finding_id: str = field(default='')
    engagement_id: str = field(default='')
    working_paper_id: Optional[str] = field(default=None)
    title: str = field(default='')
    severity: str = field(default='')
    finding_type: str = field(default='')
    created_by: str = field(default='')
    
    def __post_init__(self):
        self.event_type = 'grc.audit.finding.created'
        self.aggregate_id = self.finding_id
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'finding_id': self.finding_id,
            'engagement_id': self.engagement_id,
            'working_paper_id': self.working_paper_id,
            'title': self.title,
            'severity': self.severity,
            'finding_type': self.finding_type,
            'created_by': self.created_by
        }


@dataclass
class AuditFindingFinalizedEvent(GRCDomainEvent):
    """
    Audit finding was finalized — published when the parent Audit Report is
    approved by CIA (SRS Req 41: Risk Management integration).

    Consumers: Risk Management System (Phase 2) — creates org risk register entries.

    The payload carries enough context for a consumer to register the finding as
    an organisational risk without needing to call back to GRC.
    """

    finding_id: str = field(default='')
    reference_number: str = field(default='')
    title: str = field(default='')
    description: str = field(default='')
    finding_type: str = field(default='')
    severity: str = field(default='')
    risk_rating_id: str = field(default='')
    risk_rating_name: str = field(default='')
    engagement_id: str = field(default='')
    engagement_reference: str = field(default='')
    auditable_entity_id: str = field(default='')
    auditable_entity_name: str = field(default='')
    fiscal_year_id: str = field(default='')
    fiscal_year_code: str = field(default='')
    recommendation_count: int = field(default=0)
    finalized_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.audit.finding.finalized'
        self.aggregate_id = self.finding_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'finding_id': self.finding_id,
            'reference_number': self.reference_number,
            'title': self.title,
            'description': self.description,
            'finding_type': self.finding_type,
            'severity': self.severity,
            'risk_rating_id': self.risk_rating_id,
            'risk_rating_name': self.risk_rating_name,
            'engagement_id': self.engagement_id,
            'engagement_reference': self.engagement_reference,
            'auditable_entity_id': self.auditable_entity_id,
            'auditable_entity_name': self.auditable_entity_name,
            'fiscal_year_id': self.fiscal_year_id,
            'fiscal_year_code': self.fiscal_year_code,
            'recommendation_count': self.recommendation_count,
            'finalized_by': self.finalized_by,
        }


@dataclass
class AuditPlanCreatedEvent(GRCDomainEvent):
    """Audit plan was created"""

    plan_id: str = field(default='')
    fiscal_year: str = field(default='')
    plan_type: str = field(default='')
    created_by: str = field(default='')

    def __post_init__(self):
        self.event_type = 'grc.audit.plan.created'
        self.aggregate_id = self.plan_id

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'plan_id': self.plan_id,
            'fiscal_year': self.fiscal_year,
            'plan_type': self.plan_type,
            'created_by': self.created_by,
        }


@dataclass
class AuditPlanApprovedEvent(GRCDomainEvent):
    """Audit plan was approved"""
    
    plan_id: str = field(default='')
    fiscal_year: str = field(default='')
    approved_by: str = field(default='')
    approval_date: str = field(default='')
    
    def __post_init__(self):
        self.event_type = 'grc.audit.plan.approved'
        self.aggregate_id = self.plan_id
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'plan_id': self.plan_id,
            'fiscal_year': self.fiscal_year,
            'approved_by': self.approved_by,
            'approval_date': self.approval_date
        }
