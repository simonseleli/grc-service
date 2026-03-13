from django.urls import path

from apps.api.views.audit_universe_views import (
    AuditUniverseListCreateView,
    AuditUniverseDetailView,
    AuditUniverseApprovalView,
    AuditUniverseWorkflowStatusView,
    AuditUniverseWorkflowHistoryView,
    AuditUniverseWorkflowActionView,
    AuditUniverseCancelWorkflowView,
)
from apps.api.views.audit_plan_views import (
    AuditPlanListCreateView,
    AuditPlanDetailView,
    AuditPlanSubmitView,
    AuditPlanApprovalView,
    AuditPlanWorkflowStatusView,
    AuditPlanWorkflowHistoryView,
    AuditPlanWorkflowActionView,
    AuditPlanCancelWorkflowView,
    AuditPlanGenerateDraftView,
)
from apps.api.views.auditable_entity_views import (
    AuditableEntityListCreateView,
    AuditableEntityDetailView
)
from apps.api.views.risk_assessment_views import (
    RiskAssessmentListCreateView,
    RiskAssessmentDetailView,
    RiskAssessmentSubmitView,
    RiskAssessmentReviewView,
    RiskAssessmentEvidenceView,
    RiskAssessmentEvidenceDetailView,
)
from apps.api.views.audit_engagement_views import (
    AuditEngagementListCreateView,
    AuditEngagementDetailView,
    AuditEngagementPhaseTransitionView,
    AuditEngagementTeamView,
    AuditEngagementWorkflowStatusView,
    AuditEngagementWorkflowHistoryView,
    AuditEngagementWorkflowActionView,
    AuditEngagementCancelWorkflowView,
)
from apps.api.views.audit_finding_views import (
    AuditFindingListCreateView,
    AuditFindingDetailView,
    AuditFindingFinalizeView,
    AuditFindingStatusUpdateView,
    AuditFindingResponseView
)
from apps.api.views.audit_recommendation_views import (
    AuditRecommendationListCreateView,
    AuditRecommendationDetailView,
    AuditRecommendationStatusUpdateView,
    AuditRecommendationOverdueView
)
from apps.api.views.implementation_monitoring_views import (
    ImplementationMonitoringListCreateView,
    ImplementationMonitoringDetailView,
    ImplementationMonitoringReviewView,
    ImplementationMonitoringDueReviewsView,
    ImplementationMonitoringNotifyAuditeeView,
    ImplementationMonitoringNonResponsiveView,
    AuditeeFollowUpResponseListCreateView,
    AuditeeFollowUpResponseDetailView,
    AuditeeFollowUpResponseSubmitView,
    AuditeeFollowUpResponseVerifyView,
    AuditeeFollowUpResponseOverdueView,
)
from apps.api.views.working_paper_views import (
    EngagementWorkingPapersView,
    WorkingPaperDetailView,
    WorkingPaperReviewView,
    WorkingPaperWorkflowStatusView,
    WorkingPaperWorkflowHistoryView,
    WorkingPaperWorkflowActionView,
    WorkingPaperCancelWorkflowView,
    WorkingPaperEvidenceView,
    WorkingPaperEvidenceDetailView,
)
from apps.api.views.audit_monitoring_views import AuditMonitoringListView
from apps.api.views.audit_dashboard_views import AuditDashboardStatsView
from apps.api.views.audit_report_views import (
    AuditReportListCreateView,
    AuditReportDetailView,
    AuditReportStatusUpdateView,
    AuditReportDistributeView,
)
from apps.api.views.audit_meeting_views import (
    AuditMeetingListCreateView,
    AuditMeetingDetailView,
    AuditMeetingStatusUpdateView,
)
from apps.api.views.audit_quarterly_report_views import (
    QuarterlyReportListCreateView,
    QuarterlyReportDetailView,
    QuarterlyReportStatusUpdateView,
    QuarterlyReportConsolidateView,
    QuarterlyReportEngagementReportsView,
    QuarterlyReportSubmitView,
    QuarterlyReportWorkflowStatusView,
    QuarterlyReportWorkflowActionView,
    QuarterlyReportCancelWorkflowView,
)
from apps.api.views.audit_memo_views import (
    AuditMemoListCreateView,
    AuditMemoDetailView,
    AuditMemoSubmitView,
    AuditMemoWorkflowStatusView,
    AuditMemoWorkflowActionView,
    AuditMemoCancelWorkflowView,
)
from apps.api.views.declaration_views import (
    DeclarationListCreateView,
    DeclarationDetailView,
    DeclarationSignView,
    EngagementDeclarationsView,
)
from apps.api.views.audit_survey_views import (
    AuditSurveyListCreateView,
    AuditSurveyDetailView,
    AuditSurveyCompleteView,
    EngagementSurveyView,
)
from apps.api.views.rcm_views import (
    RCMListCreateView,
    RCMDetailView,
    RCMSubmitView,
    RCMApproveView,
    RCMEntryListCreateView,
    RCMEntryDetailView,
)
from apps.api.views.audit_program_views import (
    AuditProgramListCreateView,
    AuditProgramDetailView,
    AuditProgramSubmitView,
    AuditProgramApproveView,
    AuditProgramWorkflowStatusView,
    AuditProgramWorkflowActionView,
    AuditProgramCancelWorkflowView,
)
from apps.api.views.engagement_notification_views import (   # P2-GAP 1
    EngagementNotificationListCreateView,
    EngagementNotificationDetailView,
    EngagementNotificationSubmitView,
    EngagementNotificationTransmitView,
    EngagementNotificationWorkflowStatusView,
    EngagementNotificationWorkflowActionView,
    EngagementNotificationCancelWorkflowView,
)
from apps.api.views.lookup_views import (
    LookupDataView, FiscalYearListView, QuarterListView,
    AuditSeverityListView, FindingTypeListView, RiskRatingListView,
    AuditOpinionListView, GRCUsersByRoleView
)

urlpatterns = [
    # Audit Universe endpoints
    path("universe/", AuditUniverseListCreateView.as_view(), name="audit-universe-list-create"),
    path("universe/<uuid:pk>/", AuditUniverseDetailView.as_view(), name="audit-universe-detail"),
    path("universe/<uuid:pk>/approve/", AuditUniverseApprovalView.as_view(), name="audit-universe-approve"),
    path("universe/<uuid:pk>/workflow-status/", AuditUniverseWorkflowStatusView.as_view(), name="audit-universe-workflow-status"),
    path("universe/<uuid:pk>/workflow-history/", AuditUniverseWorkflowHistoryView.as_view(), name="audit-universe-workflow-history"),
    path("universe/<uuid:pk>/workflow-action/", AuditUniverseWorkflowActionView.as_view(), name="audit-universe-workflow-action"),
    path("universe/<uuid:pk>/cancel-workflow/", AuditUniverseCancelWorkflowView.as_view(), name="audit-universe-cancel-workflow"),

    # Audit Plan endpoints
    path("plans/", AuditPlanListCreateView.as_view(), name="audit-plan-list-create"),
    path("plans/<uuid:pk>/", AuditPlanDetailView.as_view(), name="audit-plan-detail"),
    path("plans/<uuid:pk>/submit/", AuditPlanSubmitView.as_view(), name="audit-plan-submit"),
    path("plans/<uuid:pk>/approve/", AuditPlanApprovalView.as_view(), name="audit-plan-approve"),
    path("plans/<uuid:pk>/workflow-status/", AuditPlanWorkflowStatusView.as_view(), name="audit-plan-workflow-status"),
    path("plans/<uuid:pk>/workflow-history/", AuditPlanWorkflowHistoryView.as_view(), name="audit-plan-workflow-history"),
    path("plans/<uuid:pk>/workflow-action/", AuditPlanWorkflowActionView.as_view(), name="audit-plan-workflow-action"),
    path("plans/<uuid:pk>/cancel-workflow/", AuditPlanCancelWorkflowView.as_view(), name="audit-plan-cancel-workflow"),
    path("plans/generate-draft/", AuditPlanGenerateDraftView.as_view(), name="audit-plan-generate-draft"),
    
    # Auditable Entity endpoints
    path("entities/", AuditableEntityListCreateView.as_view(), name="auditable-entity-list-create"),
    path("entities/<uuid:pk>/", AuditableEntityDetailView.as_view(), name="auditable-entity-detail"),
    
    # Risk Assessment endpoints
    path("risk-assessments/", RiskAssessmentListCreateView.as_view(), name="risk-assessment-list-create"),
    path("risk-assessments/<uuid:pk>/", RiskAssessmentDetailView.as_view(), name="risk-assessment-detail"),
    path("risk-assessments/<uuid:pk>/submit/", RiskAssessmentSubmitView.as_view(), name="risk-assessment-submit"),
    path("risk-assessments/<uuid:pk>/review/", RiskAssessmentReviewView.as_view(), name="risk-assessment-review"),
    path("risk-assessments/<uuid:pk>/evidence/", RiskAssessmentEvidenceView.as_view(), name="risk-assessment-evidence"),
    path("risk-assessments/<uuid:pk>/evidence/<uuid:document_id>/", RiskAssessmentEvidenceDetailView.as_view(), name="risk-assessment-evidence-detail"),
    
    # Audit Engagement endpoints
    path("engagements/", AuditEngagementListCreateView.as_view(), name="audit-engagement-list-create"),
    path("engagements/<uuid:pk>/", AuditEngagementDetailView.as_view(), name="audit-engagement-detail"),
    path("engagements/<uuid:pk>/transition/", AuditEngagementPhaseTransitionView.as_view(), name="audit-engagement-transition"),
    path("engagements/<uuid:pk>/team/", AuditEngagementTeamView.as_view(), name="audit-engagement-team"),
    path("engagements/<uuid:pk>/workflow-status/", AuditEngagementWorkflowStatusView.as_view(), name="audit-engagement-workflow-status"),
    path("engagements/<uuid:pk>/workflow-history/", AuditEngagementWorkflowHistoryView.as_view(), name="audit-engagement-workflow-history"),
    path("engagements/<uuid:pk>/workflow-action/", AuditEngagementWorkflowActionView.as_view(), name="audit-engagement-workflow-action"),
    path("engagements/<uuid:pk>/cancel-workflow/", AuditEngagementCancelWorkflowView.as_view(), name="audit-engagement-cancel-workflow"),
    
    # Audit Finding endpoints
    path("findings/", AuditFindingListCreateView.as_view(), name="audit-finding-list-create"),
    path("findings/<uuid:pk>/", AuditFindingDetailView.as_view(), name="audit-finding-detail"),
    path("findings/<uuid:pk>/finalize/", AuditFindingFinalizeView.as_view(), name="audit-finding-finalize"),
    path("findings/<uuid:pk>/update-status/", AuditFindingStatusUpdateView.as_view(), name="audit-finding-update-status"),
    path("findings/<uuid:pk>/responses/", AuditFindingResponseView.as_view(), name="audit-finding-responses"),
    
    # Audit Recommendation endpoints
    path("recommendations/", AuditRecommendationListCreateView.as_view(), name="audit-recommendation-list-create"),
    path("recommendations/<uuid:pk>/", AuditRecommendationDetailView.as_view(), name="audit-recommendation-detail"),
    path("recommendations/<uuid:pk>/status/", AuditRecommendationStatusUpdateView.as_view(), name="audit-recommendation-status"),
    path("recommendations/overdue/", AuditRecommendationOverdueView.as_view(), name="audit-recommendation-overdue"),
    
    # Implementation Monitoring endpoints
    path("implementation-monitoring/", ImplementationMonitoringListCreateView.as_view(), name="implementation-monitoring-list-create"),
    path("implementation-monitoring/<uuid:pk>/", ImplementationMonitoringDetailView.as_view(), name="implementation-monitoring-detail"),
    path("implementation-monitoring/<uuid:pk>/review/", ImplementationMonitoringReviewView.as_view(), name="implementation-monitoring-review"),
    path("implementation-monitoring/due-reviews/", ImplementationMonitoringDueReviewsView.as_view(), name="implementation-monitoring-due-reviews"),
    path("implementation-monitoring/<uuid:pk>/notify-auditee/", ImplementationMonitoringNotifyAuditeeView.as_view(), name="implementation-monitoring-notify-auditee"),
    path("implementation-monitoring/non-responsive/", ImplementationMonitoringNonResponsiveView.as_view(), name="implementation-monitoring-non-responsive"),

    # Follow-up Response endpoints (P2-GAP 4 — one row per review cycle)
    # NOTE: static segments (overdue/) must come before <uuid:pk>/ to avoid UUID matching
    path("follow-up-responses/overdue/", AuditeeFollowUpResponseOverdueView.as_view(), name="follow-up-response-overdue"),
    path("follow-up-responses/", AuditeeFollowUpResponseListCreateView.as_view(), name="follow-up-response-list-create"),
    path("follow-up-responses/<uuid:pk>/", AuditeeFollowUpResponseDetailView.as_view(), name="follow-up-response-detail"),
    path("follow-up-responses/<uuid:pk>/submit/", AuditeeFollowUpResponseSubmitView.as_view(), name="follow-up-response-submit"),
    path("follow-up-responses/<uuid:pk>/verify/", AuditeeFollowUpResponseVerifyView.as_view(), name="follow-up-response-verify"),
    # Nested: all cycles for a single monitoring header
    path("implementation-monitoring/<uuid:monitoring_id>/responses/", AuditeeFollowUpResponseListCreateView.as_view(), name="monitoring-responses-list"),
    
    # Working Paper endpoints - Phase 2 Week 1
    path("engagements/<uuid:engagement_id>/working-papers/", EngagementWorkingPapersView.as_view(), name="engagement-working-papers"),
    path("working-papers/<uuid:paper_id>/", WorkingPaperDetailView.as_view(), name="working-paper-detail"),
    path("working-papers/<uuid:paper_id>/review/", WorkingPaperReviewView.as_view(), name="working-paper-review"),
    path("working-papers/<uuid:paper_id>/workflow-status/", WorkingPaperWorkflowStatusView.as_view(), name="working-paper-workflow-status"),
    path("working-papers/<uuid:paper_id>/workflow-history/", WorkingPaperWorkflowHistoryView.as_view(), name="working-paper-workflow-history"),
    path("working-papers/<uuid:paper_id>/workflow-action/", WorkingPaperWorkflowActionView.as_view(), name="working-paper-workflow-action"),
    path("working-papers/<uuid:paper_id>/cancel-workflow/", WorkingPaperCancelWorkflowView.as_view(), name="working-paper-cancel-workflow"),
    path("working-papers/<uuid:paper_id>/evidence/", WorkingPaperEvidenceView.as_view(), name="working-paper-evidence"),
    path("working-papers/<uuid:paper_id>/evidence/<uuid:document_id>/", WorkingPaperEvidenceDetailView.as_view(), name="working-paper-evidence-detail"),
    
    # Audit Report endpoints
    path("reports/", AuditReportListCreateView.as_view(), name="audit-report-list-create"),
    path("reports/<uuid:pk>/", AuditReportDetailView.as_view(), name="audit-report-detail"),
    path("reports/<uuid:pk>/update-status/", AuditReportStatusUpdateView.as_view(), name="audit-report-update-status"),
    path("reports/<uuid:pk>/distribute/", AuditReportDistributeView.as_view(), name="audit-report-distribute"),

    # Audit Meeting endpoints
    path("meetings/", AuditMeetingListCreateView.as_view(), name="audit-meeting-list-create"),
    path("meetings/<uuid:pk>/", AuditMeetingDetailView.as_view(), name="audit-meeting-detail"),
    path("meetings/<uuid:pk>/update-status/", AuditMeetingStatusUpdateView.as_view(), name="audit-meeting-update-status"),

    # Quarterly Audit Report endpoints
    path("quarterly-reports/", QuarterlyReportListCreateView.as_view(), name="quarterly-report-list-create"),
    path("quarterly-reports/<uuid:pk>/", QuarterlyReportDetailView.as_view(), name="quarterly-report-detail"),
    path("quarterly-reports/<uuid:pk>/update-status/", QuarterlyReportStatusUpdateView.as_view(), name="quarterly-report-update-status"),
    path("quarterly-reports/<uuid:pk>/consolidate/", QuarterlyReportConsolidateView.as_view(), name="quarterly-report-consolidate"),
    path("quarterly-reports/<uuid:pk>/engagement-reports/", QuarterlyReportEngagementReportsView.as_view(), name="quarterly-report-engagement-reports"),
    # P2-GAP 3 — WO integration
    path("quarterly-reports/<uuid:pk>/submit-for-approval/", QuarterlyReportSubmitView.as_view(), name="quarterly-report-submit"),
    path("quarterly-reports/<uuid:pk>/workflow-status/", QuarterlyReportWorkflowStatusView.as_view(), name="quarterly-report-workflow-status"),
    path("quarterly-reports/<uuid:pk>/workflow-action/", QuarterlyReportWorkflowActionView.as_view(), name="quarterly-report-workflow-action"),
    path("quarterly-reports/<uuid:pk>/cancel-workflow/", QuarterlyReportCancelWorkflowView.as_view(), name="quarterly-report-cancel-workflow"),

    # Legacy monitoring endpoint (read-only recommendations with monitoring data)
    path("monitoring/", AuditMonitoringListView.as_view(), name="audit-monitoring-list"),
    
    # Dashboard stats endpoint
    path("dashboard/stats/", AuditDashboardStatsView.as_view(), name="audit-dashboard-stats"),

    # Audit Memo endpoints (GAP 1)
    path("memos/", AuditMemoListCreateView.as_view(), name="audit-memo-list-create"),
    path("memos/<uuid:pk>/", AuditMemoDetailView.as_view(), name="audit-memo-detail"),
    path("memos/<uuid:pk>/submit/", AuditMemoSubmitView.as_view(), name="audit-memo-submit"),
    path("memos/<uuid:pk>/workflow-status/", AuditMemoWorkflowStatusView.as_view(), name="audit-memo-workflow-status"),
    path("memos/<uuid:pk>/workflow-action/", AuditMemoWorkflowActionView.as_view(), name="audit-memo-workflow-action"),
    path("memos/<uuid:pk>/cancel-workflow/", AuditMemoCancelWorkflowView.as_view(), name="audit-memo-cancel-workflow"),

    # Declaration of Independence endpoints (GAP 2)
    path("declarations/", DeclarationListCreateView.as_view(), name="declaration-list-create"),
    path("declarations/<uuid:pk>/", DeclarationDetailView.as_view(), name="declaration-detail"),
    path("declarations/<uuid:pk>/sign/", DeclarationSignView.as_view(), name="declaration-sign"),
    path("engagements/<uuid:engagement_id>/declarations/", EngagementDeclarationsView.as_view(), name="engagement-declarations"),

    # Audit Survey endpoints (GAP 3)
    path("surveys/", AuditSurveyListCreateView.as_view(), name="audit-survey-list-create"),
    path("surveys/<uuid:pk>/", AuditSurveyDetailView.as_view(), name="audit-survey-detail"),
    path("surveys/<uuid:pk>/complete/", AuditSurveyCompleteView.as_view(), name="audit-survey-complete"),
    path("engagements/<uuid:engagement_id>/survey/", EngagementSurveyView.as_view(), name="engagement-survey"),

    # Risk Control Matrix endpoints (GAP 4)
    path("rcm/", RCMListCreateView.as_view(), name="rcm-list-create"),
    path("rcm/<uuid:pk>/", RCMDetailView.as_view(), name="rcm-detail"),
    path("rcm/<uuid:pk>/submit/", RCMSubmitView.as_view(), name="rcm-submit"),
    path("rcm/<uuid:pk>/approve/", RCMApproveView.as_view(), name="rcm-approve"),
    path("rcm/<uuid:rcm_id>/entries/", RCMEntryListCreateView.as_view(), name="rcm-entry-list-create"),
    path("rcm-entries/<uuid:pk>/", RCMEntryDetailView.as_view(), name="rcm-entry-detail"),

    # Audit Program endpoints (GAP 5)
    path("programs/", AuditProgramListCreateView.as_view(), name="audit-program-list-create"),
    path("programs/<uuid:pk>/", AuditProgramDetailView.as_view(), name="audit-program-detail"),
    path("programs/<uuid:pk>/submit/", AuditProgramSubmitView.as_view(), name="audit-program-submit"),
    path("programs/<uuid:pk>/approve/", AuditProgramApproveView.as_view(), name="audit-program-approve"),
    path("programs/<uuid:pk>/workflow-status/", AuditProgramWorkflowStatusView.as_view(), name="audit-program-workflow-status"),
    path("programs/<uuid:pk>/workflow-action/", AuditProgramWorkflowActionView.as_view(), name="audit-program-workflow-action"),
    path("programs/<uuid:pk>/cancel-workflow/", AuditProgramCancelWorkflowView.as_view(), name="audit-program-cancel-workflow"),

    # Engagement Notification endpoints (P2-GAP 1 — SRS Req 24, 25, 26)
    path("engagement-notifications/", EngagementNotificationListCreateView.as_view(), name="engagement-notification-list-create"),
    path("engagement-notifications/<uuid:pk>/", EngagementNotificationDetailView.as_view(), name="engagement-notification-detail"),
    path("engagement-notifications/<uuid:pk>/submit/", EngagementNotificationSubmitView.as_view(), name="engagement-notification-submit"),
    path("engagement-notifications/<uuid:pk>/transmit/", EngagementNotificationTransmitView.as_view(), name="engagement-notification-transmit"),
    path("engagement-notifications/<uuid:pk>/workflow-status/", EngagementNotificationWorkflowStatusView.as_view(), name="engagement-notification-workflow-status"),
    path("engagement-notifications/<uuid:pk>/workflow-action/", EngagementNotificationWorkflowActionView.as_view(), name="engagement-notification-workflow-action"),
    path("engagement-notifications/<uuid:pk>/cancel-workflow/", EngagementNotificationCancelWorkflowView.as_view(), name="engagement-notification-cancel-workflow"),
    
    # Lookup table endpoints (these might be duplicates of /config/* endpoints)
    path("lookups/", LookupDataView.as_view(), name="lookup-data-all"),
    path("lookups/fiscal-years/", FiscalYearListView.as_view(), name="fiscal-year-list"),
    path("lookups/quarters/", QuarterListView.as_view(), name="quarter-list"),
    path("lookups/audit-severities/", AuditSeverityListView.as_view(), name="audit-severity-list"),
    path("lookups/finding-types/", FindingTypeListView.as_view(), name="finding-type-list"),
    path("lookups/risk-ratings/", RiskRatingListView.as_view(), name="risk-rating-list"),
    path("lookups/audit-opinions/", AuditOpinionListView.as_view(), name="audit-opinion-list"),
    path("lookups/users/", GRCUsersByRoleView.as_view(), name="grc-users-by-role"),
]

