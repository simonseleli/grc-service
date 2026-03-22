"""
Core services for GRC service
"""

"""
Core services for GRC service
"""

from .corporate_sync import CorporateServiceClient, OrganizationalSyncService
from .audit_universe_service import AuditUniverseService
from .audit_plan_service import AuditPlanService
from .audit_engagement_service import AuditEngagementService
from .working_paper_service import WorkingPaperService
from .engagement_notification_service import EngagementNotificationService
# P2-GAP 2
from .audit_memo_service import AuditMemoService
from .audit_program_service import AuditProgramService
from .audit_report_service import AuditReportService
from .quarterly_report_service import QuarterlyReportService

# Legal module services
from .legal_meeting_service import LegalMeetingService
from .legal_minutes_service import LegalMinutesService
from .legal_case_service import LegalCaseService
from .legal_filing_service import LegalFilingService
from .legal_settlement_service import LegalSettlementService
from .legal_judgment_service import LegalJudgmentService

# Risk Management & Quality Assurance module services
from .risk_champion_service import RiskChampionAppointmentService
from .dept_risk_register_service import DeptRiskRegisterService
from .institutional_risk_register_service import InstitutionalRiskRegisterService
from .rtap_service import RTAPService
from .quarterly_risk_report_service import QuarterlyRiskReportService
from .quality_auditor_service import QualityAuditorAppointmentService
from .qms_audit_program_service import QMSAuditProgramService
from .qms_audit_plan_service import QMSAuditPlanService

__all__ = [
    'CorporateServiceClient',
    'OrganizationalSyncService',
    'AuditUniverseService',
    'AuditPlanService',
    'AuditEngagementService',
    'WorkingPaperService',
    'EngagementNotificationService',
    # P2-GAP 2
    'AuditMemoService',
    'AuditProgramService',
    'AuditReportService',
    'QuarterlyReportService',
    # Legal module
    'LegalMeetingService',
    'LegalMinutesService',
    'LegalCaseService',
    'LegalFilingService',
    'LegalSettlementService',
    'LegalJudgmentService',
    # Risk Management & Quality Assurance module
    'RiskChampionAppointmentService',
    'DeptRiskRegisterService',
    'InstitutionalRiskRegisterService',
    'RTAPService',
    'QuarterlyRiskReportService',
    'QualityAuditorAppointmentService',
    'QMSAuditProgramService',
    'QMSAuditPlanService',
]
