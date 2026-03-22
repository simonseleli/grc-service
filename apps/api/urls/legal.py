"""
Legal Module — URL Registration
Mounted at /api/v1/grc/legal/ via apps.api.urls.__init__
"""
from django.urls import path

# ── Governing Body & Members ─────────────────────────────────────────────────
from apps.api.views.legal_governing_body_views import (
    CommitteeTypeListView,
    GoverningBodyListCreateView,
    GoverningBodyDetailView,
    MemberListCreateView,
    MemberDetailView,
    SubmissionForDeterminationListCreateView,
    SubmissionForDeterminationDetailView,
)

# ── Meetings ─────────────────────────────────────────────────────────────────
from apps.api.views.legal_meeting_views import (
    MeetingListCreateView,
    MeetingDetailView,
    MeetingSendInvitationsView,
    MeetingSubmitView,
    MeetingWorkflowStatusView,
    MeetingWorkflowHistoryView,
    MeetingWorkflowActionView,
    MeetingCancelWorkflowView,
    MeetingAgendaListCreateView,
    MeetingAgendaDetailView,
    ConflictDeclarationListCreateView,
    MeetingParticipantListCreateView,
    MeetingParticipantDetailView,
    MeetingPopulateMattersArisingView,
    MeetingDirectivesSubResourceView,
)

# ── Minutes ──────────────────────────────────────────────────────────────────
from apps.api.views.legal_minutes_views import (
    MinutesListCreateView,
    MinutesDetailView,
    MinutesSubmitView,
    MinutesWorkflowStatusView,
    MinutesWorkflowHistoryView,
    MinutesWorkflowActionView,
    MinutesCancelWorkflowView,
    ResolutionListCreateView,
    ResolutionDetailView,
)

# ── Directives & Tasks ──────────────────────────────────────────────────────
from apps.api.views.legal_directive_views import (
    MeetingDirectiveListCreateView,
    MeetingDirectiveDetailView,
    MeetingDirectiveOverdueListView,
    LitigationDirectiveListCreateView,
    LitigationDirectiveDetailView,
    LitigationDirectiveSubmitForDGApprovalView,
    LitigationDirectiveDGDecisionView,
    TaskLitigationListCreateView,
    TaskLitigationDetailView,
    TaskLitigationOverdueListView,
)

# ── Cases ────────────────────────────────────────────────────────────────────
from apps.api.views.legal_case_views import (
    CaseDefendantListCreateView,
    CaseDefendantDetailView,
    CaseDefendantSubmitView,
    CaseDefendantWorkflowStatusView,
    CaseDefendantWorkflowHistoryView,
    CaseDefendantWorkflowActionView,
    CaseDefendantCancelWorkflowView,
    CasePlaintiffListCreateView,
    CasePlaintiffDetailView,
    CasePlaintiffSubmitView,
    CasePlaintiffWorkflowStatusView,
    CasePlaintiffWorkflowHistoryView,
    CasePlaintiffWorkflowActionView,
    CasePlaintiffCancelWorkflowView,
    CaseArchiveView,
    CaseUnarchiveView,
    CaseHoldView,
    CaseResumeView,
    CaseReportView,
)

# ── Hearings ─────────────────────────────────────────────────────────────────
from apps.api.views.legal_hearing_views import (
    HearingListCreateView,
    HearingDetailView,
    HearingReportListCreateView,
    HearingReportDetailView,
)

# ── Filings ──────────────────────────────────────────────────────────────────
from apps.api.views.legal_filing_views import (
    FilingDefendantListCreateView,
    FilingDefendantDetailView,
    FilingDefendantSubmitView,
    FilingDefendantWorkflowStatusView,
    FilingDefendantWorkflowHistoryView,
    FilingDefendantWorkflowActionView,
    FilingDefendantCancelWorkflowView,
    ResponseDefendantListCreateView,
    ResponseDefendantDetailView,
    FilingPlaintiffListCreateView,
    FilingPlaintiffDetailView,
    FilingPlaintiffSubmitView,
    FilingPlaintiffWorkflowStatusView,
    FilingPlaintiffWorkflowHistoryView,
    FilingPlaintiffWorkflowActionView,
    FilingPlaintiffCancelWorkflowView,
    ResponsePlaintiffListCreateView,
    ResponsePlaintiffDetailView,
)

# ── Settlements ──────────────────────────────────────────────────────────────
from apps.api.views.legal_settlement_views import (
    SettlementDefendantListCreateView,
    SettlementDefendantDetailView,
    SettlementDefendantSubmitView,
    SettlementDefendantWorkflowStatusView,
    SettlementDefendantWorkflowHistoryView,
    SettlementDefendantWorkflowActionView,
    SettlementDefendantCancelWorkflowView,
    SettlementPlaintiffListCreateView,
    SettlementPlaintiffDetailView,
    SettlementPlaintiffSubmitView,
    SettlementPlaintiffWorkflowStatusView,
    SettlementPlaintiffWorkflowHistoryView,
    SettlementPlaintiffWorkflowActionView,
    SettlementPlaintiffCancelWorkflowView,
    FinancialDefendantDetailView,
    FinancialPlaintiffDetailView,
)

# ── Judgments & Appeals ──────────────────────────────────────────────────────
from apps.api.views.legal_judgment_views import (
    JudgmentDefendantListCreateView,
    JudgmentDefendantDetailView,
    JudgmentDefendantSubmitView,
    JudgmentDefendantWorkflowStatusView,
    JudgmentDefendantWorkflowHistoryView,
    JudgmentDefendantWorkflowActionView,
    JudgmentDefendantCancelWorkflowView,
    JudgmentPlaintiffListCreateView,
    JudgmentPlaintiffDetailView,
    JudgmentPlaintiffSubmitView,
    JudgmentPlaintiffWorkflowStatusView,
    JudgmentPlaintiffWorkflowHistoryView,
    JudgmentPlaintiffWorkflowActionView,
    JudgmentPlaintiffCancelWorkflowView,
    AppealDefendantListView,
    AppealDefendantDetailView,
    AppealPlaintiffListView,
    AppealPlaintiffDetailView,
    JudgmentDefendantDGDecisionView,
    JudgmentPlaintiffDGDecisionView,
)

# ── Notices ──────────────────────────────────────────────────────────────────
from apps.api.views.legal_notice_views import (
    LegalNoticeListCreateView,
    LegalNoticeDetailView,
)

# ── Public Decisions / Public Register (GAP-11) ─────────────────────────────
from apps.api.views.legal_public_register_views import (
    PublicDecisionListCreateView,
    PublicDecisionDetailView,
    PublicDecisionPublishView,
    PublicRegisterListView,
)

# ── Dashboard KPIs (GAP-12) ─────────────────────────────────────────────────
from apps.api.views.legal_dashboard_views import (
    LegalDashboardDefendantView,
    LegalDashboardPlaintiffView,
)

# ── Activity Log (GAP-13) ───────────────────────────────────────────────────
from apps.api.views.legal_activity_log_views import LegalActivityLogView

# ── Lookups ──────────────────────────────────────────────────────────────────
from apps.api.views.legal_lookup_views import (
    CourtLevelListView,
    LitigationUrgencyLevelListView,
    LitigationRiskLevelListView,
    MeetingModeListView,
    MeetingTypeListView,
    DirectivePriorityListView,
    DirectiveCategoryListView,
)


urlpatterns = [
    # ── Committee Types ──────────────────────────────────────────────────────
    path("committee-types/", CommitteeTypeListView.as_view(), name="legal-committee-type-list"),

    # ── Governing Bodies ─────────────────────────────────────────────────────
    path("governing-bodies/", GoverningBodyListCreateView.as_view(), name="legal-governing-body-list-create"),
    path("governing-bodies/<uuid:pk>/", GoverningBodyDetailView.as_view(), name="legal-governing-body-detail"),
    path("governing-bodies/<uuid:gb_pk>/members/", MemberListCreateView.as_view(), name="legal-governing-body-member-list"),
    path("members/<uuid:pk>/", MemberDetailView.as_view(), name="legal-member-detail"),

    # ── Submissions for Determination ────────────────────────────────────────
    path("submissions/", SubmissionForDeterminationListCreateView.as_view(), name="legal-submission-list-create"),
    path("submissions/<uuid:pk>/", SubmissionForDeterminationDetailView.as_view(), name="legal-submission-detail"),

    # ── Meetings ─────────────────────────────────────────────────────────────
    path("meetings/", MeetingListCreateView.as_view(), name="legal-meeting-list-create"),
    path("meetings/<uuid:pk>/", MeetingDetailView.as_view(), name="legal-meeting-detail"),
    path("meetings/<uuid:pk>/send-invitations/", MeetingSendInvitationsView.as_view(), name="legal-meeting-send-invitations"),
    path("meetings/<uuid:pk>/submit/", MeetingSubmitView.as_view(), name="legal-meeting-submit"),
    path("meetings/<uuid:pk>/workflow-status/", MeetingWorkflowStatusView.as_view(), name="legal-meeting-workflow-status"),
    path("meetings/<uuid:pk>/workflow-history/", MeetingWorkflowHistoryView.as_view(), name="legal-meeting-workflow-history"),
    path("meetings/<uuid:pk>/workflow-action/", MeetingWorkflowActionView.as_view(), name="legal-meeting-workflow-action"),
    path("meetings/<uuid:pk>/cancel-workflow/", MeetingCancelWorkflowView.as_view(), name="legal-meeting-cancel-workflow"),
    path("meetings/<uuid:meeting_pk>/agenda/", MeetingAgendaListCreateView.as_view(), name="legal-meeting-agenda-list"),
    path("meetings/<uuid:pk>/populate-matters-arising/", MeetingPopulateMattersArisingView.as_view(), name="legal-meeting-populate-matters-arising"),
    path("meetings/<uuid:pk>/directives/", MeetingDirectivesSubResourceView.as_view(), name="legal-meeting-directives-sub"),
    path("meeting-agenda/<uuid:pk>/", MeetingAgendaDetailView.as_view(), name="legal-meeting-agenda-detail"),
    path("meetings/<uuid:meeting_pk>/conflicts/", ConflictDeclarationListCreateView.as_view(), name="legal-meeting-conflict-list"),
    path("meetings/<uuid:meeting_pk>/participants/", MeetingParticipantListCreateView.as_view(), name="legal-meeting-participant-list"),
    path("meeting-participants/<uuid:pk>/", MeetingParticipantDetailView.as_view(), name="legal-meeting-participant-detail"),

    # ── Minutes ──────────────────────────────────────────────────────────────
    path("minutes/", MinutesListCreateView.as_view(), name="legal-minutes-list-create"),
    path("minutes/<uuid:pk>/", MinutesDetailView.as_view(), name="legal-minutes-detail"),
    path("minutes/<uuid:pk>/submit/", MinutesSubmitView.as_view(), name="legal-minutes-submit"),
    path("minutes/<uuid:pk>/workflow-status/", MinutesWorkflowStatusView.as_view(), name="legal-minutes-workflow-status"),
    path("minutes/<uuid:pk>/workflow-history/", MinutesWorkflowHistoryView.as_view(), name="legal-minutes-workflow-history"),
    path("minutes/<uuid:pk>/workflow-action/", MinutesWorkflowActionView.as_view(), name="legal-minutes-workflow-action"),
    path("minutes/<uuid:pk>/cancel-workflow/", MinutesCancelWorkflowView.as_view(), name="legal-minutes-cancel-workflow"),
    path("minutes/<uuid:pk>/resolutions/", ResolutionListCreateView.as_view(), name="legal-minutes-resolution-list"),
    path("resolutions/<uuid:pk>/", ResolutionDetailView.as_view(), name="legal-resolution-detail"),

    # ── Meeting Directives ───────────────────────────────────────────────────
    # NOTE: static segments (overdue/) BEFORE <uuid:pk>/ to avoid UUID matching
    path("directives/overdue/", MeetingDirectiveOverdueListView.as_view(), name="legal-directive-overdue"),
    path("directives/", MeetingDirectiveListCreateView.as_view(), name="legal-directive-list-create"),
    path("directives/<uuid:pk>/", MeetingDirectiveDetailView.as_view(), name="legal-directive-detail"),

    # ── Cases — Defendant ────────────────────────────────────────────────────
    path("cases/defendant/", CaseDefendantListCreateView.as_view(), name="legal-case-defendant-list-create"),
    path("cases/defendant/<uuid:pk>/", CaseDefendantDetailView.as_view(), name="legal-case-defendant-detail"),
    path("cases/defendant/<uuid:pk>/submit/", CaseDefendantSubmitView.as_view(), name="legal-case-defendant-submit"),
    path("cases/defendant/<uuid:pk>/workflow-status/", CaseDefendantWorkflowStatusView.as_view(), name="legal-case-defendant-workflow-status"),
    path("cases/defendant/<uuid:pk>/workflow-history/", CaseDefendantWorkflowHistoryView.as_view(), name="legal-case-defendant-workflow-history"),
    path("cases/defendant/<uuid:pk>/workflow-action/", CaseDefendantWorkflowActionView.as_view(), name="legal-case-defendant-workflow-action"),
    path("cases/defendant/<uuid:pk>/cancel-workflow/", CaseDefendantCancelWorkflowView.as_view(), name="legal-case-defendant-cancel-workflow"),

    # ── Archiving (GAP-14) ───────────────────────────────────────────────────
    path("cases/<str:side>/<uuid:pk>/archive/", CaseArchiveView.as_view(), name="legal-case-archive"),
    path("cases/<str:side>/<uuid:pk>/unarchive/", CaseUnarchiveView.as_view(), name="legal-case-unarchive"),

    # ── Hold / Resume (SIG-09 / B4-1, B4-2) ─────────────────────────────────
    path("cases/<str:side>/<uuid:pk>/hold/", CaseHoldView.as_view(), name="legal-case-hold"),
    path("cases/<str:side>/<uuid:pk>/resume/", CaseResumeView.as_view(), name="legal-case-resume"),

    # ── Case Report / Timeline (SRS §4.13) ───────────────────────────────────
    path("cases/<str:side>/<uuid:pk>/report/", CaseReportView.as_view(), name="legal-case-report"),

    # ── Cases — Plaintiff ────────────────────────────────────────────────────
    path("cases/plaintiff/", CasePlaintiffListCreateView.as_view(), name="legal-case-plaintiff-list-create"),
    path("cases/plaintiff/<uuid:pk>/", CasePlaintiffDetailView.as_view(), name="legal-case-plaintiff-detail"),
    path("cases/plaintiff/<uuid:pk>/submit/", CasePlaintiffSubmitView.as_view(), name="legal-case-plaintiff-submit"),
    path("cases/plaintiff/<uuid:pk>/workflow-status/", CasePlaintiffWorkflowStatusView.as_view(), name="legal-case-plaintiff-workflow-status"),
    path("cases/plaintiff/<uuid:pk>/workflow-history/", CasePlaintiffWorkflowHistoryView.as_view(), name="legal-case-plaintiff-workflow-history"),
    path("cases/plaintiff/<uuid:pk>/workflow-action/", CasePlaintiffWorkflowActionView.as_view(), name="legal-case-plaintiff-workflow-action"),
    path("cases/plaintiff/<uuid:pk>/cancel-workflow/", CasePlaintiffCancelWorkflowView.as_view(), name="legal-case-plaintiff-cancel-workflow"),

    # ── Hearings ─────────────────────────────────────────────────────────────
    path("hearings/", HearingListCreateView.as_view(), name="legal-hearing-list-create"),
    path("hearings/<uuid:pk>/", HearingDetailView.as_view(), name="legal-hearing-detail"),
    path("hearings/<uuid:hearing_pk>/reports/", HearingReportListCreateView.as_view(), name="legal-hearing-report-list"),
    path("hearing-reports/<uuid:pk>/", HearingReportDetailView.as_view(), name="legal-hearing-report-detail"),

    # ── Litigation Directives ────────────────────────────────────────────────
    path("litigation-directives/", LitigationDirectiveListCreateView.as_view(), name="legal-litigation-directive-list-create"),
    path("litigation-directives/<uuid:pk>/", LitigationDirectiveDetailView.as_view(), name="legal-litigation-directive-detail"),
    path("litigation-directives/<uuid:pk>/submit-for-dg-approval/", LitigationDirectiveSubmitForDGApprovalView.as_view(), name="legal-litigation-directive-submit-dg"),
    path("litigation-directives/<uuid:pk>/dg-decision/", LitigationDirectiveDGDecisionView.as_view(), name="legal-litigation-directive-dg-decision"),

    # ── Tasks (Litigation) ───────────────────────────────────────────────────
    # NOTE: static segments (overdue/) BEFORE <uuid:pk>/
    path("tasks/overdue/", TaskLitigationOverdueListView.as_view(), name="legal-task-overdue"),
    path("tasks/", TaskLitigationListCreateView.as_view(), name="legal-task-list-create"),
    path("tasks/<uuid:pk>/", TaskLitigationDetailView.as_view(), name="legal-task-detail"),

    # ── Filings — Defendant ──────────────────────────────────────────────────
    path("filings/defendant/", FilingDefendantListCreateView.as_view(), name="legal-filing-defendant-list-create"),
    path("filings/defendant/<uuid:pk>/", FilingDefendantDetailView.as_view(), name="legal-filing-defendant-detail"),
    path("filings/defendant/<uuid:pk>/submit/", FilingDefendantSubmitView.as_view(), name="legal-filing-defendant-submit"),
    path("filings/defendant/<uuid:pk>/workflow-status/", FilingDefendantWorkflowStatusView.as_view(), name="legal-filing-defendant-workflow-status"),
    path("filings/defendant/<uuid:pk>/workflow-history/", FilingDefendantWorkflowHistoryView.as_view(), name="legal-filing-defendant-workflow-history"),
    path("filings/defendant/<uuid:pk>/workflow-action/", FilingDefendantWorkflowActionView.as_view(), name="legal-filing-defendant-workflow-action"),
    path("filings/defendant/<uuid:pk>/cancel-workflow/", FilingDefendantCancelWorkflowView.as_view(), name="legal-filing-defendant-cancel-workflow"),
    path("filings/defendant/<uuid:pk>/responses/", ResponseDefendantListCreateView.as_view(), name="legal-filing-defendant-response-list"),
    path("filing-responses/defendant/<uuid:pk>/", ResponseDefendantDetailView.as_view(), name="legal-filing-defendant-response-detail"),

    # ── Filings — Plaintiff ──────────────────────────────────────────────────
    path("filings/plaintiff/", FilingPlaintiffListCreateView.as_view(), name="legal-filing-plaintiff-list-create"),
    path("filings/plaintiff/<uuid:pk>/", FilingPlaintiffDetailView.as_view(), name="legal-filing-plaintiff-detail"),
    path("filings/plaintiff/<uuid:pk>/submit/", FilingPlaintiffSubmitView.as_view(), name="legal-filing-plaintiff-submit"),
    path("filings/plaintiff/<uuid:pk>/workflow-status/", FilingPlaintiffWorkflowStatusView.as_view(), name="legal-filing-plaintiff-workflow-status"),
    path("filings/plaintiff/<uuid:pk>/workflow-history/", FilingPlaintiffWorkflowHistoryView.as_view(), name="legal-filing-plaintiff-workflow-history"),
    path("filings/plaintiff/<uuid:pk>/workflow-action/", FilingPlaintiffWorkflowActionView.as_view(), name="legal-filing-plaintiff-workflow-action"),
    path("filings/plaintiff/<uuid:pk>/cancel-workflow/", FilingPlaintiffCancelWorkflowView.as_view(), name="legal-filing-plaintiff-cancel-workflow"),
    path("filings/plaintiff/<uuid:pk>/responses/", ResponsePlaintiffListCreateView.as_view(), name="legal-filing-plaintiff-response-list"),
    path("filing-responses/plaintiff/<uuid:pk>/", ResponsePlaintiffDetailView.as_view(), name="legal-filing-plaintiff-response-detail"),

    # ── Settlements — Defendant ──────────────────────────────────────────────
    path("settlements/defendant/", SettlementDefendantListCreateView.as_view(), name="legal-settlement-defendant-list-create"),
    path("settlements/defendant/<uuid:pk>/", SettlementDefendantDetailView.as_view(), name="legal-settlement-defendant-detail"),
    path("settlements/defendant/<uuid:pk>/submit/", SettlementDefendantSubmitView.as_view(), name="legal-settlement-defendant-submit"),
    path("settlements/defendant/<uuid:pk>/workflow-status/", SettlementDefendantWorkflowStatusView.as_view(), name="legal-settlement-defendant-workflow-status"),
    path("settlements/defendant/<uuid:pk>/workflow-history/", SettlementDefendantWorkflowHistoryView.as_view(), name="legal-settlement-defendant-workflow-history"),
    path("settlements/defendant/<uuid:pk>/workflow-action/", SettlementDefendantWorkflowActionView.as_view(), name="legal-settlement-defendant-workflow-action"),
    path("settlements/defendant/<uuid:pk>/cancel-workflow/", SettlementDefendantCancelWorkflowView.as_view(), name="legal-settlement-defendant-cancel-workflow"),
    path("settlements/defendant/<uuid:pk>/financials/", FinancialDefendantDetailView.as_view(), name="legal-settlement-defendant-financial"),

    # ── Settlements — Plaintiff ──────────────────────────────────────────────
    path("settlements/plaintiff/", SettlementPlaintiffListCreateView.as_view(), name="legal-settlement-plaintiff-list-create"),
    path("settlements/plaintiff/<uuid:pk>/", SettlementPlaintiffDetailView.as_view(), name="legal-settlement-plaintiff-detail"),
    path("settlements/plaintiff/<uuid:pk>/submit/", SettlementPlaintiffSubmitView.as_view(), name="legal-settlement-plaintiff-submit"),
    path("settlements/plaintiff/<uuid:pk>/workflow-status/", SettlementPlaintiffWorkflowStatusView.as_view(), name="legal-settlement-plaintiff-workflow-status"),
    path("settlements/plaintiff/<uuid:pk>/workflow-history/", SettlementPlaintiffWorkflowHistoryView.as_view(), name="legal-settlement-plaintiff-workflow-history"),
    path("settlements/plaintiff/<uuid:pk>/workflow-action/", SettlementPlaintiffWorkflowActionView.as_view(), name="legal-settlement-plaintiff-workflow-action"),
    path("settlements/plaintiff/<uuid:pk>/cancel-workflow/", SettlementPlaintiffCancelWorkflowView.as_view(), name="legal-settlement-plaintiff-cancel-workflow"),
    path("settlements/plaintiff/<uuid:pk>/financials/", FinancialPlaintiffDetailView.as_view(), name="legal-settlement-plaintiff-financial"),

    # ── Judgments — Defendant ────────────────────────────────────────────────
    path("judgments/defendant/", JudgmentDefendantListCreateView.as_view(), name="legal-judgment-defendant-list-create"),
    path("judgments/defendant/<uuid:pk>/", JudgmentDefendantDetailView.as_view(), name="legal-judgment-defendant-detail"),
    path("judgments/defendant/<uuid:pk>/submit/", JudgmentDefendantSubmitView.as_view(), name="legal-judgment-defendant-submit"),
    path("judgments/defendant/<uuid:pk>/workflow-status/", JudgmentDefendantWorkflowStatusView.as_view(), name="legal-judgment-defendant-workflow-status"),
    path("judgments/defendant/<uuid:pk>/workflow-history/", JudgmentDefendantWorkflowHistoryView.as_view(), name="legal-judgment-defendant-workflow-history"),
    path("judgments/defendant/<uuid:pk>/workflow-action/", JudgmentDefendantWorkflowActionView.as_view(), name="legal-judgment-defendant-workflow-action"),
    path("judgments/defendant/<uuid:pk>/cancel-workflow/", JudgmentDefendantCancelWorkflowView.as_view(), name="legal-judgment-defendant-cancel-workflow"),
    path("judgments/defendant/<uuid:pk>/dg-decision/", JudgmentDefendantDGDecisionView.as_view(), name="legal-judgment-defendant-dg-decision"),

    # ── Judgments — Plaintiff ────────────────────────────────────────────────
    path("judgments/plaintiff/", JudgmentPlaintiffListCreateView.as_view(), name="legal-judgment-plaintiff-list-create"),
    path("judgments/plaintiff/<uuid:pk>/", JudgmentPlaintiffDetailView.as_view(), name="legal-judgment-plaintiff-detail"),
    path("judgments/plaintiff/<uuid:pk>/submit/", JudgmentPlaintiffSubmitView.as_view(), name="legal-judgment-plaintiff-submit"),
    path("judgments/plaintiff/<uuid:pk>/workflow-status/", JudgmentPlaintiffWorkflowStatusView.as_view(), name="legal-judgment-plaintiff-workflow-status"),
    path("judgments/plaintiff/<uuid:pk>/workflow-history/", JudgmentPlaintiffWorkflowHistoryView.as_view(), name="legal-judgment-plaintiff-workflow-history"),
    path("judgments/plaintiff/<uuid:pk>/workflow-action/", JudgmentPlaintiffWorkflowActionView.as_view(), name="legal-judgment-plaintiff-workflow-action"),
    path("judgments/plaintiff/<uuid:pk>/cancel-workflow/", JudgmentPlaintiffCancelWorkflowView.as_view(), name="legal-judgment-plaintiff-cancel-workflow"),
    path("judgments/plaintiff/<uuid:pk>/dg-decision/", JudgmentPlaintiffDGDecisionView.as_view(), name="legal-judgment-plaintiff-dg-decision"),

    # ── Appeals ──────────────────────────────────────────────────────────────
    path("appeals/defendant/", AppealDefendantListView.as_view(), name="legal-appeal-defendant-list"),
    path("appeals/defendant/<uuid:pk>/", AppealDefendantDetailView.as_view(), name="legal-appeal-defendant-detail"),
    path("appeals/plaintiff/", AppealPlaintiffListView.as_view(), name="legal-appeal-plaintiff-list"),
    path("appeals/plaintiff/<uuid:pk>/", AppealPlaintiffDetailView.as_view(), name="legal-appeal-plaintiff-detail"),

    # ── Legal Notices ────────────────────────────────────────────────────────
    path("notices/", LegalNoticeListCreateView.as_view(), name="legal-notice-list-create"),
    path("notices/<uuid:pk>/", LegalNoticeDetailView.as_view(), name="legal-notice-detail"),

    # ── Public Decisions / Public Register (GAP-11) ──────────────────────────
    path("public-decisions/", PublicDecisionListCreateView.as_view(), name="legal-public-decision-list-create"),
    path("public-decisions/<uuid:pk>/", PublicDecisionDetailView.as_view(), name="legal-public-decision-detail"),
    path("public-decisions/<uuid:pk>/publish/", PublicDecisionPublishView.as_view(), name="legal-public-decision-publish"),
    path("public-register/", PublicRegisterListView.as_view(), name="legal-public-register"),

    # ── Dashboard KPIs (GAP-12) ──────────────────────────────────────────────
    path("dashboard/defendant/", LegalDashboardDefendantView.as_view(), name="legal-dashboard-defendant"),
    path("dashboard/plaintiff/", LegalDashboardPlaintiffView.as_view(), name="legal-dashboard-plaintiff"),

    # ── Activity Log (GAP-13) ────────────────────────────────────────────────
    path("activity-log/<str:entity_type>/<uuid:entity_id>/", LegalActivityLogView.as_view(), name="legal-activity-log"),

    # ── Lookups ──────────────────────────────────────────────────────────────
    path("lookups/court-levels/", CourtLevelListView.as_view(), name="legal-lookup-court-levels"),
    path("lookups/urgency-levels/", LitigationUrgencyLevelListView.as_view(), name="legal-lookup-urgency-levels"),
    path("lookups/risk-levels/", LitigationRiskLevelListView.as_view(), name="legal-lookup-risk-levels"),
    path("lookups/meeting-modes/", MeetingModeListView.as_view(), name="legal-lookup-meeting-modes"),
    path("lookups/meeting-types/", MeetingTypeListView.as_view(), name="legal-lookup-meeting-types"),
    path("lookups/directive-priorities/", DirectivePriorityListView.as_view(), name="legal-lookup-directive-priorities"),
    path("lookups/directive-categories/", DirectiveCategoryListView.as_view(), name="legal-lookup-directive-categories"),
]
