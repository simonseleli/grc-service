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
