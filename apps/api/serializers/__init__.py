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

from .risk_serializers import (
    # Group 7 — QA Training
    QATrainingSessionSerializer,
    QATrainingAttendeeSerializer,
    # Group 1 — Risk Champion & QA Appointment
    RiskChampionSerializer,
    RiskChampionAppointmentSerializer,
    QualityAuditorSerializer,
    QualityAuditorAppointmentSerializer,
    # Group 2 — Risk Assessment & Departmental Register
    RiskAssessmentSheetSerializer,
    DepartmentalRiskRegisterSerializer,
    DeptRegisterEntrySerializer,
    # Group 3 — Institutional Register & RTAP
    InstitutionalRiskRegisterSerializer,
    InstitutionalRiskEntrySerializer,
    RiskTreatmentActionPlanSerializer,
    RTAPItemSerializer,
    RTAPQuarterlyUpdateSerializer,
    # Group 4 — Quarterly Reporting
    QuarterlyPerformanceReportSerializer,
    ActivityReportSerializer,
    # Group 5 — QMS Audit
    QMSAuditProgramSerializer,
    QMSAuditPlanSerializer,
    QMSAuditTeamAssignmentSerializer,
    AuditChecklistSerializer,
    QMSAuditReportSerializer,
    NonConformanceSerializer,
    # Group 6 — Meeting & Workshop
    RiskMeetingSerializer,
    MeetingAttendanceSerializer,
    # Group 8 — QMS Audit Support
    QMSAuditMeetingSerializer,
    QMSAuditTimetableEntrySerializer,
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

    # Risk Management — QA Training
    'QATrainingSessionSerializer',
    'QATrainingAttendeeSerializer',
    # Risk Management — Risk Champion & QA Appointment
    'RiskChampionSerializer',
    'RiskChampionAppointmentSerializer',
    'QualityAuditorSerializer',
    'QualityAuditorAppointmentSerializer',
    # Risk Management — Risk Assessment & Departmental Register
    'RiskAssessmentSheetSerializer',
    'DepartmentalRiskRegisterSerializer',
    'DeptRegisterEntrySerializer',
    # Risk Management — Institutional Register & RTAP
    'InstitutionalRiskRegisterSerializer',
    'InstitutionalRiskEntrySerializer',
    'RiskTreatmentActionPlanSerializer',
    'RTAPItemSerializer',
    'RTAPQuarterlyUpdateSerializer',
    # Risk Management — Quarterly Reporting
    'QuarterlyPerformanceReportSerializer',
    'ActivityReportSerializer',
    # Risk Management — QMS Audit
    'QMSAuditProgramSerializer',
    'QMSAuditPlanSerializer',
    'QMSAuditTeamAssignmentSerializer',
    'AuditChecklistSerializer',
    'QMSAuditReportSerializer',
    'NonConformanceSerializer',
    # Risk Management — Meeting & Workshop
    'RiskMeetingSerializer',
    'MeetingAttendanceSerializer',
    # Risk Management — QMS Audit Support
    'QMSAuditMeetingSerializer',
    'QMSAuditTimetableEntrySerializer',
]
