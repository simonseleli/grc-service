from django.urls import path

from apps.api.views import (
    risk_champion_views,
    risk_assessment_sheet_views,
    dept_risk_register_views,
    institutional_risk_register_views,
    risk_treatment_plan_views,
    rtap_item_views,
    quarterly_risk_report_views,
    quality_auditor_views,
    qms_audit_program_views,
    qms_audit_plan_views,
    qms_audit_checklist_views,
    qms_audit_report_views,
    non_conformance_views,
    risk_dashboard_views,
    risk_meeting_views,
    qa_training_views,
    qms_audit_support_views,
)

urlpatterns = [
    # ── Dashboard ──────────────────────────────────────────────────────────
    path("dashboard/", risk_dashboard_views.RiskDashboardView.as_view(), name="risk-dashboard"),

    # ── Risk Champions ─────────────────────────────────────────────────────
    path("champions/", risk_champion_views.RiskChampionListCreateView.as_view(), name="risk-champion-list-create"),
    path("champions/<uuid:pk>/", risk_champion_views.RiskChampionDetailView.as_view(), name="risk-champion-detail"),
    path("champions/<uuid:pk>/appointments/", risk_champion_views.RiskChampionAppointmentListCreateView.as_view(), name="risk-champion-appointment-list-create"),
    path("champions/appointments/<uuid:pk>/", risk_champion_views.RiskChampionAppointmentDetailView.as_view(), name="risk-champion-appointment-detail"),
    path("champions/appointments/<uuid:pk>/workflow/start/", risk_champion_views.RiskChampionAppointmentWorkflowStartView.as_view(), name="rc-appointment-workflow-start"),
    path("champions/appointments/<uuid:pk>/workflow/status/", risk_champion_views.RiskChampionAppointmentWorkflowStatusView.as_view(), name="rc-appointment-workflow-status"),
    path("champions/appointments/<uuid:pk>/workflow/history/", risk_champion_views.RiskChampionAppointmentWorkflowHistoryView.as_view(), name="rc-appointment-workflow-history"),
    path("champions/appointments/<uuid:pk>/workflow/advance/", risk_champion_views.RiskChampionAppointmentWorkflowAdvanceView.as_view(), name="rc-appointment-workflow-advance"),
    path("champions/appointments/<uuid:pk>/workflow/cancel/", risk_champion_views.RiskChampionAppointmentWorkflowCancelView.as_view(), name="rc-appointment-workflow-cancel"),
    path("champions/appointments/<uuid:pk>/workflow/recall/", risk_champion_views.RiskChampionAppointmentWorkflowRecallView.as_view(), name="rc-appointment-workflow-recall"),

    # ── Risk Assessment Sheets ─────────────────────────────────────────────
    path("assessments/", risk_assessment_sheet_views.RiskAssessmentSheetListCreateView.as_view(), name="risk-assessment-sheet-list-create"),
    path("assessments/<uuid:pk>/", risk_assessment_sheet_views.RiskAssessmentSheetDetailView.as_view(), name="risk-assessment-sheet-detail"),
    # GAP-15/28: RAS status transition endpoints
    path("assessments/<uuid:pk>/submit/", risk_assessment_sheet_views.RASSubmitView.as_view(), name="ras-submit"),
    path("assessments/<uuid:pk>/endorse/", risk_assessment_sheet_views.RASEndorseView.as_view(), name="ras-endorse"),
    path("assessments/<uuid:pk>/submit-to-rmqam/", risk_assessment_sheet_views.RASSubmitToRMQAMView.as_view(), name="ras-submit-to-rmqam"),
    path("assessments/<uuid:pk>/approve/", risk_assessment_sheet_views.RASApproveView.as_view(), name="ras-approve"),
    path("assessments/<uuid:pk>/return-for-rework/", risk_assessment_sheet_views.RASReturnForReworkView.as_view(), name="ras-return-for-rework"),

    # ── Departmental Risk Registers ────────────────────────────────────────
    path("dept-registers/", dept_risk_register_views.DeptRiskRegisterListCreateView.as_view(), name="dept-risk-register-list-create"),
    path("dept-registers/<uuid:pk>/", dept_risk_register_views.DeptRiskRegisterDetailView.as_view(), name="dept-risk-register-detail"),
    path("dept-registers/<uuid:pk>/entries/", dept_risk_register_views.DeptRegisterEntryListCreateView.as_view(), name="dept-register-entry-list-create"),
    path("dept-registers/entries/<uuid:pk>/", dept_risk_register_views.DeptRegisterEntryDetailView.as_view(), name="dept-register-entry-detail"),
    path("dept-registers/<uuid:pk>/workflow/start/", dept_risk_register_views.DeptRiskRegisterWorkflowStartView.as_view(), name="dept-register-workflow-start"),
    path("dept-registers/<uuid:pk>/workflow/status/", dept_risk_register_views.DeptRiskRegisterWorkflowStatusView.as_view(), name="dept-register-workflow-status"),
    path("dept-registers/<uuid:pk>/workflow/history/", dept_risk_register_views.DeptRiskRegisterWorkflowHistoryView.as_view(), name="dept-register-workflow-history"),
    path("dept-registers/<uuid:pk>/workflow/advance/", dept_risk_register_views.DeptRiskRegisterWorkflowAdvanceView.as_view(), name="dept-register-workflow-advance"),
    path("dept-registers/<uuid:pk>/workflow/cancel/", dept_risk_register_views.DeptRiskRegisterWorkflowCancelView.as_view(), name="dept-register-workflow-cancel"),
    path("dept-registers/<uuid:pk>/workflow/recall/", dept_risk_register_views.DeptRiskRegisterWorkflowRecallView.as_view(), name="dept-register-workflow-recall"),

    # ── Institutional Risk Registers ───────────────────────────────────────
    path("institutional-registers/", institutional_risk_register_views.InstitutionalRiskRegisterListCreateView.as_view(), name="inst-risk-register-list-create"),
    path("institutional-registers/<uuid:pk>/", institutional_risk_register_views.InstitutionalRiskRegisterDetailView.as_view(), name="inst-risk-register-detail"),
    path("institutional-registers/<uuid:pk>/entries/", institutional_risk_register_views.InstitutionalRiskEntryListCreateView.as_view(), name="inst-risk-entry-list-create"),
    path("institutional-registers/entries/<uuid:pk>/", institutional_risk_register_views.InstitutionalRiskEntryDetailView.as_view(), name="inst-risk-entry-detail"),
    path("institutional-registers/<uuid:pk>/activity-reports/", institutional_risk_register_views.ActivityReportListCreateView.as_view(), name="inst-activity-report-list-create"),
    path("institutional-registers/activity-reports/<uuid:pk>/", institutional_risk_register_views.ActivityReportDetailView.as_view(), name="inst-activity-report-detail"),
    path("institutional-registers/<uuid:pk>/workflow/start/", institutional_risk_register_views.InstitutionalRiskRegisterWorkflowStartView.as_view(), name="inst-register-workflow-start"),
    path("institutional-registers/<uuid:pk>/workflow/status/", institutional_risk_register_views.InstitutionalRiskRegisterWorkflowStatusView.as_view(), name="inst-register-workflow-status"),
    path("institutional-registers/<uuid:pk>/workflow/history/", institutional_risk_register_views.InstitutionalRiskRegisterWorkflowHistoryView.as_view(), name="inst-register-workflow-history"),
    path("institutional-registers/<uuid:pk>/workflow/advance/", institutional_risk_register_views.InstitutionalRiskRegisterWorkflowAdvanceView.as_view(), name="inst-register-workflow-advance"),
    path("institutional-registers/<uuid:pk>/workflow/cancel/", institutional_risk_register_views.InstitutionalRiskRegisterWorkflowCancelView.as_view(), name="inst-register-workflow-cancel"),
    path("institutional-registers/<uuid:pk>/workflow/recall/", institutional_risk_register_views.InstitutionalRiskRegisterWorkflowRecallView.as_view(), name="inst-register-workflow-recall"),
    # GAP-8: Workshop notification endpoints
    path("institutional-registers/<uuid:pk>/notify-directors/", institutional_risk_register_views.IRRNotifyDirectorsView.as_view(), name="irr-notify-directors"),
    path("institutional-registers/<uuid:pk>/notify-rcs/", institutional_risk_register_views.IRRNotifyRCsView.as_view(), name="irr-notify-rcs"),
    # GAP-24: Distribution endpoint
    path("institutional-registers/<uuid:pk>/distribute/", institutional_risk_register_views.IRRDistributeView.as_view(), name="irr-distribute"),

    # ── RTAP ───────────────────────────────────────────────────────────────
    path("rtap/", risk_treatment_plan_views.RTAPListCreateView.as_view(), name="rtap-list-create"),
    path("rtap/<uuid:pk>/", risk_treatment_plan_views.RTAPDetailView.as_view(), name="rtap-detail"),
    path("rtap/<uuid:pk>/workflow/start/", risk_treatment_plan_views.RTAPWorkflowStartView.as_view(), name="rtap-workflow-start"),
    path("rtap/<uuid:pk>/workflow/status/", risk_treatment_plan_views.RTAPWorkflowStatusView.as_view(), name="rtap-workflow-status"),
    path("rtap/<uuid:pk>/workflow/history/", risk_treatment_plan_views.RTAPWorkflowHistoryView.as_view(), name="rtap-workflow-history"),
    path("rtap/<uuid:pk>/workflow/advance/", risk_treatment_plan_views.RTAPWorkflowAdvanceView.as_view(), name="rtap-workflow-advance"),
    path("rtap/<uuid:pk>/workflow/cancel/", risk_treatment_plan_views.RTAPWorkflowCancelView.as_view(), name="rtap-workflow-cancel"),
    path("rtap/<uuid:pk>/workflow/recall/", risk_treatment_plan_views.RTAPWorkflowRecallView.as_view(), name="rtap-workflow-recall"),
    # GAP-7: Send reminder to RCs
    path("rtap/<uuid:pk>/send-reminder/", risk_treatment_plan_views.RTAPSendReminderView.as_view(), name="rtap-send-reminder"),
    # GAP-24: Distribute RTAP
    path("rtap/<uuid:pk>/distribute/", risk_treatment_plan_views.RTAPDistributeView.as_view(), name="rtap-distribute"),

    # ── RTAP Items ─────────────────────────────────────────────────────────
    path("rtap-items/", rtap_item_views.RTAPItemListCreateView.as_view(), name="rtap-item-list-create"),
    path("rtap-items/<uuid:pk>/", rtap_item_views.RTAPItemDetailView.as_view(), name="rtap-item-detail"),
    path("rtap-items/<uuid:pk>/quarterly-updates/", rtap_item_views.RTAPQuarterlyUpdateListCreateView.as_view(), name="rtap-quarterly-update-list-create"),
    path("rtap-items/quarterly-updates/<uuid:pk>/", rtap_item_views.RTAPQuarterlyUpdateDetailView.as_view(), name="rtap-quarterly-update-detail"),
    # GAP-22: RTAP item rework
    path("rtap-items/<uuid:pk>/return-for-rework/", rtap_item_views.RTAPItemReturnForReworkView.as_view(), name="rtap-item-return-for-rework"),
    path("rtap-items/<uuid:pk>/resubmit/", rtap_item_views.RTAPItemResubmitView.as_view(), name="rtap-item-resubmit"),

    # ── Quarterly Performance Reports ──────────────────────────────────────
    path("quarterly-reports/", quarterly_risk_report_views.QuarterlyReportListCreateView.as_view(), name="quarterly-report-list-create"),
    path("quarterly-reports/<uuid:pk>/", quarterly_risk_report_views.QuarterlyReportDetailView.as_view(), name="quarterly-report-detail"),
    path("quarterly-reports/<uuid:pk>/workflow/start/", quarterly_risk_report_views.QuarterlyReportWorkflowStartView.as_view(), name="quarterly-report-workflow-start"),
    path("quarterly-reports/<uuid:pk>/workflow/status/", quarterly_risk_report_views.QuarterlyReportWorkflowStatusView.as_view(), name="quarterly-report-workflow-status"),
    path("quarterly-reports/<uuid:pk>/workflow/history/", quarterly_risk_report_views.QuarterlyReportWorkflowHistoryView.as_view(), name="quarterly-report-workflow-history"),
    path("quarterly-reports/<uuid:pk>/workflow/advance/", quarterly_risk_report_views.QuarterlyReportWorkflowAdvanceView.as_view(), name="quarterly-report-workflow-advance"),
    path("quarterly-reports/<uuid:pk>/workflow/cancel/", quarterly_risk_report_views.QuarterlyReportWorkflowCancelView.as_view(), name="quarterly-report-workflow-cancel"),
    path("quarterly-reports/<uuid:pk>/workflow/recall/", quarterly_risk_report_views.QuarterlyReportWorkflowRecallView.as_view(), name="quarterly-report-workflow-recall"),

    # ── Quality Auditors ───────────────────────────────────────────────────
    path("quality-auditors/", quality_auditor_views.QualityAuditorListCreateView.as_view(), name="quality-auditor-list-create"),
    path("quality-auditors/<uuid:pk>/", quality_auditor_views.QualityAuditorDetailView.as_view(), name="quality-auditor-detail"),
    path("quality-auditors/<uuid:pk>/appointments/", quality_auditor_views.QualityAuditorAppointmentListCreateView.as_view(), name="quality-auditor-appointment-list-create"),
    path("quality-auditors/appointments/<uuid:pk>/", quality_auditor_views.QualityAuditorAppointmentDetailView.as_view(), name="quality-auditor-appointment-detail"),
    path("quality-auditors/appointments/<uuid:pk>/workflow/start/", quality_auditor_views.QAAppointmentWorkflowStartView.as_view(), name="qa-appointment-workflow-start"),
    path("quality-auditors/appointments/<uuid:pk>/workflow/status/", quality_auditor_views.QAAppointmentWorkflowStatusView.as_view(), name="qa-appointment-workflow-status"),
    path("quality-auditors/appointments/<uuid:pk>/workflow/history/", quality_auditor_views.QAAppointmentWorkflowHistoryView.as_view(), name="qa-appointment-workflow-history"),
    path("quality-auditors/appointments/<uuid:pk>/workflow/advance/", quality_auditor_views.QAAppointmentWorkflowAdvanceView.as_view(), name="qa-appointment-workflow-advance"),
    path("quality-auditors/appointments/<uuid:pk>/workflow/cancel/", quality_auditor_views.QAAppointmentWorkflowCancelView.as_view(), name="qa-appointment-workflow-cancel"),
    path("quality-auditors/appointments/<uuid:pk>/workflow/recall/", quality_auditor_views.QAAppointmentWorkflowRecallView.as_view(), name="qa-appointment-workflow-recall"),

    # ── QMS Audit Programs ─────────────────────────────────────────────────
    path("qms-programs/", qms_audit_program_views.QMSAuditProgramListCreateView.as_view(), name="qms-audit-program-list-create"),
    path("qms-programs/<uuid:pk>/", qms_audit_program_views.QMSAuditProgramDetailView.as_view(), name="qms-audit-program-detail"),
    path("qms-programs/<uuid:pk>/workflow/start/", qms_audit_program_views.QMSAuditProgramWorkflowStartView.as_view(), name="qms-program-workflow-start"),
    path("qms-programs/<uuid:pk>/workflow/status/", qms_audit_program_views.QMSAuditProgramWorkflowStatusView.as_view(), name="qms-program-workflow-status"),
    path("qms-programs/<uuid:pk>/workflow/history/", qms_audit_program_views.QMSAuditProgramWorkflowHistoryView.as_view(), name="qms-program-workflow-history"),
    path("qms-programs/<uuid:pk>/workflow/advance/", qms_audit_program_views.QMSAuditProgramWorkflowAdvanceView.as_view(), name="qms-program-workflow-advance"),
    path("qms-programs/<uuid:pk>/workflow/cancel/", qms_audit_program_views.QMSAuditProgramWorkflowCancelView.as_view(), name="qms-program-workflow-cancel"),
    path("qms-programs/<uuid:pk>/workflow/recall/", qms_audit_program_views.QMSAuditProgramWorkflowRecallView.as_view(), name="qms-program-workflow-recall"),

    # ── QMS Audit Plans ────────────────────────────────────────────────────
    path("qms-plans/", qms_audit_plan_views.QMSAuditPlanListCreateView.as_view(), name="qms-audit-plan-list-create"),
    path("qms-plans/<uuid:pk>/", qms_audit_plan_views.QMSAuditPlanDetailView.as_view(), name="qms-audit-plan-detail"),
    path("qms-plans/<uuid:pk>/team/", qms_audit_plan_views.QMSTeamAssignmentListCreateView.as_view(), name="qms-team-assignment-list-create"),
    path("qms-plans/team/<uuid:pk>/", qms_audit_plan_views.QMSTeamAssignmentDetailView.as_view(), name="qms-team-assignment-detail"),
    path("qms-plans/<uuid:pk>/workflow/start/", qms_audit_plan_views.QMSAuditPlanWorkflowStartView.as_view(), name="qms-plan-workflow-start"),
    path("qms-plans/<uuid:pk>/workflow/status/", qms_audit_plan_views.QMSAuditPlanWorkflowStatusView.as_view(), name="qms-plan-workflow-status"),
    path("qms-plans/<uuid:pk>/workflow/history/", qms_audit_plan_views.QMSAuditPlanWorkflowHistoryView.as_view(), name="qms-plan-workflow-history"),
    path("qms-plans/<uuid:pk>/workflow/advance/", qms_audit_plan_views.QMSAuditPlanWorkflowAdvanceView.as_view(), name="qms-plan-workflow-advance"),
    path("qms-plans/<uuid:pk>/workflow/cancel/", qms_audit_plan_views.QMSAuditPlanWorkflowCancelView.as_view(), name="qms-plan-workflow-cancel"),
    path("qms-plans/<uuid:pk>/workflow/recall/", qms_audit_plan_views.QMSAuditPlanWorkflowRecallView.as_view(), name="qms-plan-workflow-recall"),

    # ── QMS Audit Checklists ───────────────────────────────────────────────
    path("qms-checklists/", qms_audit_checklist_views.AuditChecklistListCreateView.as_view(), name="audit-checklist-list-create"),
    path("qms-checklists/<uuid:pk>/", qms_audit_checklist_views.AuditChecklistDetailView.as_view(), name="audit-checklist-detail"),

    # ── QMS Audit Reports ──────────────────────────────────────────────────
    path("qms-reports/", qms_audit_report_views.QMSAuditReportListCreateView.as_view(), name="qms-audit-report-list-create"),
    path("qms-reports/<uuid:pk>/", qms_audit_report_views.QMSAuditReportDetailView.as_view(), name="qms-audit-report-detail"),
    path("qms-reports/<uuid:pk>/sign-tl/", qms_audit_report_views.QMSAuditReportSignTLView.as_view(), name="qms-audit-report-sign-tl"),
    path("qms-reports/<uuid:pk>/sign-auditee/", qms_audit_report_views.QMSAuditReportSignAuditeeView.as_view(), name="qms-audit-report-sign-auditee"),
    # GAP-12/25/26: Post-finalisation governance endpoints
    path("qms-reports/<uuid:pk>/submit-to-rmqam/", qms_audit_report_views.QMSReportSubmitToRMQAMView.as_view(), name="qms-report-submit-to-rmqam"),
    path("qms-reports/<uuid:pk>/return-for-revision/", qms_audit_report_views.QMSReportReturnForRevisionView.as_view(), name="qms-report-return-for-revision"),
    path("qms-reports/<uuid:pk>/present-at-mrm/", qms_audit_report_views.QMSReportPresentAtMRMView.as_view(), name="qms-report-present-at-mrm"),
    path("qms-reports/<uuid:pk>/record-directives/", qms_audit_report_views.QMSReportRecordDirectivesView.as_view(), name="qms-report-record-directives"),
    path("qms-reports/<uuid:pk>/submit-to-audit-committee/", qms_audit_report_views.QMSReportSubmitToAuditCommitteeView.as_view(), name="qms-report-submit-to-audit-committee"),
    path("qms-reports/<uuid:pk>/audit-committee-review/", qms_audit_report_views.QMSReportAuditCommitteeReviewView.as_view(), name="qms-report-audit-committee-review"),
    path("qms-reports/<uuid:pk>/adopt-by-commission/", qms_audit_report_views.QMSReportAdoptByCommissionView.as_view(), name="qms-report-adopt-by-commission"),

    # ── Non-Conformances ───────────────────────────────────────────────────
    path("non-conformances/", non_conformance_views.NonConformanceListCreateView.as_view(), name="non-conformance-list-create"),
    path("non-conformances/monthly-summary/", non_conformance_views.NCMonthlySummaryView.as_view(), name="non-conformance-monthly-summary"),
    path("non-conformances/<uuid:pk>/", non_conformance_views.NonConformanceDetailView.as_view(), name="non-conformance-detail"),
    # GAP-4: NC dispute endpoints
    path("non-conformances/<uuid:pk>/dispute/", non_conformance_views.NCDisputeView.as_view(), name="non-conformance-dispute"),
    path("non-conformances/<uuid:pk>/resolve-dispute/", non_conformance_views.NCResolveDisputeView.as_view(), name="non-conformance-resolve-dispute"),

    # ── Risk Meetings & Workshops [GAP-01, GAP-08] ────────────────────────
    path("meetings/", risk_meeting_views.RiskMeetingListCreateView.as_view(), name="risk-meeting-list-create"),
    path("meetings/<uuid:pk>/", risk_meeting_views.RiskMeetingDetailView.as_view(), name="risk-meeting-detail"),
    path("meetings/<uuid:pk>/attendance/", risk_meeting_views.MeetingAttendanceListCreateView.as_view(), name="meeting-attendance-list-create"),
    path("meetings/attendance/<uuid:pk>/", risk_meeting_views.MeetingAttendanceDetailView.as_view(), name="meeting-attendance-detail"),

    # ── QA Training Sessions [GAP-02] ─────────────────────────────────────
    path("qa-training/", qa_training_views.QATrainingSessionListCreateView.as_view(), name="qa-training-session-list-create"),
    path("qa-training/<uuid:pk>/", qa_training_views.QATrainingSessionDetailView.as_view(), name="qa-training-session-detail"),
    path("qa-training/<uuid:pk>/attendees/", qa_training_views.QATrainingAttendeeListCreateView.as_view(), name="qa-training-attendee-list-create"),
    path("qa-training/attendees/<uuid:pk>/", qa_training_views.QATrainingAttendeeDetailView.as_view(), name="qa-training-attendee-detail"),
    # GAP-23: Approve / notify attendees
    path("qa-training/<uuid:pk>/approve/", qa_training_views.QATrainingApproveView.as_view(), name="qa-training-approve"),
    path("qa-training/<uuid:pk>/notify-attendees/", qa_training_views.QATrainingNotifyAttendeesView.as_view(), name="qa-training-notify-attendees"),

    # ── QMS Audit Support (meetings + timetable) [GAP-05, GAP-10] ─────────
    path("qms-plans/<uuid:pk>/audit-meetings/", qms_audit_support_views.QMSAuditMeetingListCreateView.as_view(), name="qms-audit-meeting-list-create"),
    path("qms-plans/audit-meetings/<uuid:pk>/", qms_audit_support_views.QMSAuditMeetingDetailView.as_view(), name="qms-audit-meeting-detail"),
    path("qms-plans/<uuid:pk>/timetable/", qms_audit_support_views.QMSAuditTimetableEntryListCreateView.as_view(), name="qms-timetable-entry-list-create"),
    path("qms-plans/timetable/<uuid:pk>/", qms_audit_support_views.QMSAuditTimetableEntryDetailView.as_view(), name="qms-timetable-entry-detail"),

    # ── Dashboard — Comparative Analysis [GAP-11] ─────────────────────────
    path("dashboard/comparative-analysis/", risk_dashboard_views.RiskDashboardComparativeAnalysisView.as_view(), name="risk-dashboard-comparative"),

    # ── Dashboard + QPR Export [GAP-20] ───────────────────────────────────
    path("dashboard/export/", risk_dashboard_views.RiskDashboardExportView.as_view(), name="risk-dashboard-export"),
    path("quarterly-reports/<uuid:pk>/export/", quarterly_risk_report_views.QPRExportView.as_view(), name="quarterly-report-export"),
]
