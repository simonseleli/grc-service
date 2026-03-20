"""
Serializers package init
Exports all serializer classes for easy import
"""

from .audit_serializers import (
    AuditUniverseSerializer,
    AuditableEntitySerializer,
    RiskAssessmentSerializer,
    AuditPlanSerializer,
    AuditEngagementSerializer,
    AuditFindingSerializer,
    AuditRecommendationSerializer,
    AuditReportSerializer,
    ImplementationMonitoringSerializer,
    WorkingPaperSerializer,
    WorkingPaperListSerializer,
)

from .lookup_serializers import (
    FiscalYearSerializer,
    QuarterSerializer,
    AuditSeveritySerializer,
    FindingTypeSerializer,
    RiskRatingSerializer,
    AuditOpinionSerializer,
    # Legal lookups
    CourtLevelSerializer,
    LitigationUrgencyLevelSerializer,
    LitigationRiskLevelSerializer,
    MeetingModeSerializer,
    MeetingTypeSerializer,
    DirectivePrioritySerializer,
    DirectiveCategorySerializer,
)

from .organizational_serializers import (
    DirectorateSerializer,
    DepartmentSerializer,
    UnitSerializer,
    SectionSerializer,
)

from .legal_serializers import (
    CommitteeTypeSerializer,
    GoverningBodySerializer,
    GoverningBodyListSerializer,
    MemberSerializer,
    SubmissionForDeterminationSerializer,
    MeetingSerializer,
    MeetingListSerializer,
    MeetingAgendaSerializer,
    ConflictDeclarationSerializer,
    MeetingParticipantSerializer,
    MeetingDirectiveSerializer,
    MinutesSerializer,
    ResolutionSerializer,
    CaseDefendantSerializer,
    CaseDefendantListSerializer,
    FilingDefendantSerializer,
    ResponseDefendantSerializer,
    HearingSerializer,
    HearingReportSerializer,
    SettlementDefendantSerializer,
    JudgmentDefendantSerializer,
    FinancialDefendantSerializer,
    LitigationDirectiveSerializer,
    TaskLitigationSerializer,
    CasePlaintiffSerializer,
    CasePlaintiffListSerializer,
    FilingPlaintiffSerializer,
    ResponsePlaintiffSerializer,
    SettlementPlaintiffSerializer,
    JudgmentPlaintiffSerializer,
    FinancialPlaintiffSerializer,
    AppealDefendantSerializer,
    AppealPlaintiffSerializer,
    LegalNoticeSerializer,
)

__all__ = [
    # Audit entities
    'AuditUniverseSerializer',
    'AuditableEntitySerializer',
    'RiskAssessmentSerializer',
    'AuditPlanSerializer',
    'AuditEngagementSerializer',
    'AuditFindingSerializer',
    'AuditRecommendationSerializer',
    'AuditReportSerializer',
    'ImplementationMonitoringSerializer',
    'WorkingPaperSerializer',
    'WorkingPaperListSerializer',
    
    # Lookups
    'FiscalYearSerializer',
    'QuarterSerializer',
    'AuditSeveritySerializer',
    'FindingTypeSerializer',
    'RiskRatingSerializer',
    'AuditOpinionSerializer',
    
    # Legal lookups
    'CourtLevelSerializer',
    'LitigationUrgencyLevelSerializer',
    'LitigationRiskLevelSerializer',
    'MeetingModeSerializer',
    'MeetingTypeSerializer',
    'DirectivePrioritySerializer',
    'DirectiveCategorySerializer',
    
    # Organizational
    'DirectorateSerializer',
    'DepartmentSerializer',
    'UnitSerializer',
    'SectionSerializer',

    # Legal — Governance
    'CommitteeTypeSerializer',
    'GoverningBodySerializer',
    'GoverningBodyListSerializer',
    'MemberSerializer',
    'SubmissionForDeterminationSerializer',
    'MeetingSerializer',
    'MeetingListSerializer',
    'MeetingAgendaSerializer',
    'ConflictDeclarationSerializer',
    'MeetingParticipantSerializer',
    'MeetingDirectiveSerializer',
    'MinutesSerializer',
    'ResolutionSerializer',

    # Legal — Defendant litigation
    'CaseDefendantSerializer',
    'CaseDefendantListSerializer',
    'FilingDefendantSerializer',
    'ResponseDefendantSerializer',
    'HearingSerializer',
    'HearingReportSerializer',
    'SettlementDefendantSerializer',
    'JudgmentDefendantSerializer',
    'FinancialDefendantSerializer',
    'LitigationDirectiveSerializer',
    'TaskLitigationSerializer',

    # Legal — Plaintiff litigation
    'CasePlaintiffSerializer',
    'CasePlaintiffListSerializer',
    'FilingPlaintiffSerializer',
    'ResponsePlaintiffSerializer',
    'SettlementPlaintiffSerializer',
    'JudgmentPlaintiffSerializer',
    'FinancialPlaintiffSerializer',

    # Legal — Appeals
    'AppealDefendantSerializer',
    'AppealPlaintiffSerializer',

    # Legal — Notices
    'LegalNoticeSerializer',
]
