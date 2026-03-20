# Django Models for GRC Audit Service
# Following FIMS patterns with domain-organized models

from .base import BaseModel
from .lookups import *
from .organizational import *
from .audit_entities import *
from .legal_entities import *

__all__ = [
    'BaseModel',
    # Lookup Models
    'FiscalYear', 'Quarter', 'AuditSeverity', 'FindingType', 'RiskRating', 'AuditOpinion',
    # Legal Lookup Models
    'CourtLevel', 'LitigationUrgencyLevel', 'LitigationRiskLevel',
    'MeetingMode', 'MeetingType', 'DirectivePriority', 'DirectiveCategory',
    # Organizational Models  
    'Directorate', 'Department', 'Unit', 'Section', 'OrganizationalSyncLog',
    # Core Audit Models
    'AuditUniverse', 'AuditableEntity', 'RiskAssessment',
    'AuditPlan', 'AuditEngagement', 'WorkingPaper', 'AuditFinding',
    'AuditRecommendation', 'ImplementationMonitoring', 'AuditeeFollowUpResponse', 'AuditReport',
    'AuditMeeting', 'QuarterlyAuditReport',
    # SRS Gap Models (GAP 1–5)
    'AuditMemo', 'DeclarationOfIndependence', 'AuditSurvey',
    'RiskControlMatrix', 'RCMEntry', 'AuditProgram',
    # P2-GAP 1
    'EngagementNotification',
    # P2-GAP 4
    'AuditeeFollowUpResponse',
    # Legal Counter Models
    'LegalCaseCounter', 'MeetingCounter', 'LegalNoticeCounter',
    # Legal Entity Models — Domain 1: Governance Structure
    'CommitteeType', 'GoverningBody', 'Member',
    # Legal Entity Models — Domain 2: Determinations
    'SubmissionForDetermination',
    # Legal Entity Models — Domain 3: Meeting Governance
    'Meeting', 'MeetingAgenda', 'ConflictDeclaration', 'MeetingParticipant',
    'MeetingDirective', 'Minutes', 'Resolution',
    # Legal Entity Models — Domain 4: Litigation (FCC Sued)
    'CaseDefendant', 'FilingDefendant', 'ResponseDefendant',
    'Hearing', 'HearingReport', 'SettlementDefendant', 'JudgmentDefendant',
    'FinancialDefendant', 'LitigationDirective', 'TaskLitigation',
    # Legal Entity Models — Domain 5: Litigation (FCC Suing)
    'CasePlaintiff', 'FilingPlaintiff', 'ResponsePlaintiff',
    'SettlementPlaintiff', 'JudgmentPlaintiff', 'FinancialPlaintiff',
    # Legal Entity Models — Domain 6: Public Register
    'PublicDecision',
    # Legal Entity Models — Domain 7: Appeals
    'AppealDefendant', 'AppealPlaintiff',
    # Legal Entity Models — Domain 8: Notices
    'LegalNotice',
    # Legal Cross-cutting
    'LegalAuditLog',
]