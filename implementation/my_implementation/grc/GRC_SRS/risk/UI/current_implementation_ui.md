# Risk Management & Quality Assurance — Current Implementation UI
## (Actual Code State — Staff Portal)

> This document describes the **current actual implementation** of the Risk Management and Quality
> Assurance sections of the GRC module, derived directly from the frontend code.
>
> For the originally-intended/design-target UI, see `corrected_UI_design.md`.
>
> **Key differences from design**: The actual implementation uses a flat card-based layout on
> detail pages instead of the tabbed interface that was designed. Several additional pages exist
> that were not in the design (QA Training, standalone QMS Audit Reports list, Risk Meetings).
> RTAP has a Create button (the design said no create button). Risk Settings live in the shared
> GRC Configuration Management page, not a dedicated risk settings page.
>
> **March 2026 restructure — QA sidebar reduced from 7 → 5 items:**
> - **QMS Audit Plans** removed from sidebar — now an embedded section inside `QMSProgramDetailPage`
> - **QMS Checklists** removed from sidebar — now an embedded section inside `QMSPlanDetailPage`
> - All routes remain registered; deep links are unaffected. This mirrors the Working Papers
>   embedding pattern already established in the Internal Audit module.

---

## SIDEBAR NAVIGATION (servicesConfig.ts)

```
├── [Risk Management]  (8 items — unchanged)
│   ├── Risk Dashboard              /service/grc/risk-dashboard
│   ├── Risk Champions              /service/grc/risk-champions
│   ├── Risk Assessment Sheets      /service/grc/risk-assessment-sheets
│   ├── Departmental Risks          /service/grc/departmental-risks
│   ├── Institutional Risks         /service/grc/institutional-risks
│   ├── Risk Treatment Plans        /service/grc/risk-treatment
│   ├── Performance Reports         /service/grc/risk-performance-reports
│   └── Risk Meetings               /service/grc/risk-meetings
│
├── [Quality Assurance]  (5 items — reduced from 7)
│   ├── Quality Auditors            /service/grc/quality-auditors
│   ├── QA Training                 /service/grc/qa-training
│   ├── QMS Programs                /service/grc/qms-programs
│   │     └── [embedded in QMSProgramDetailPage]
│   │           └── QMS Audit Plans   ("Audit Plans" card section)
│   │                 └── [embedded in QMSPlanDetailPage]
│   │                       └── QMS Checklists  ("Checklists" card section)
│   ├── QMS Audit Reports           /service/grc/quality-audits
│   └── Non-Conformances            /service/grc/non-conformances
```

> **Access paths for embedded entities (post-restructure):**
>
> | Entity | How to access | Route (unchanged) |
> |--------|---------------|-------------------|
> | QMS Audit Plans list | Sidebar → QMS Programs → click a Program → "Audit Plans" section | — |
> | QMS Audit Plan detail | Above, then click a plan row | `/service/grc/qms-plans/:planId` |
> | QMS Checklists list | QMS Program → Plan → "Checklists" section | — |
> | Create QMS Audit Plan | "Add Plan" button in Program detail (visible when program is `approved` + `canManageQMSPlans`) — program pre-selected | — |
> | Create QMS Checklist | "Add Checklist" button in Plan detail (visible when plan is `approved` + `canManageQMSChecklists`) — plan pre-selected | — |

Risk Management

Risk Settings
Risk Champions
Departmental Risks
Institutional Risks
Risk Treatment Plans


Quality Assurance

Quality Auditors
Quality Audits


> **Note**: Risk Settings (risk categories, likelihoods, impacts, levels, sectors, etc.) live
> under the shared GRC Configuration Management page (`/service/grc/configuration`), NOT as a
> dedicated Risk Management menu item. The design proposed a separate Risk Settings entry.

---

## ROUTE DEFINITIONS (App.tsx)

All routes are under `<ServiceProtectedRoute serviceKey="grc">`:

```
/service/grc/risk-dashboard                         → RiskDashboardPage
/service/grc/risk-champions                         → RiskChampionsPage
/service/grc/risk-champions/:championId             → RiskChampionDetailPage
/service/grc/risk-assessment-sheets                 → RiskAssessmentSheetsPage
/service/grc/risk-assessment-sheets/:sheetId        → RiskAssessmentSheetDetailPage
/service/grc/departmental-risks                     → DepartmentalRisksPage
/service/grc/departmental-risks/:registerId         → DeptRiskRegisterDetailPage
/service/grc/institutional-risks                    → InstitutionalRisksPage
/service/grc/institutional-risks/:registerId        → InstitutionalRiskDetailPage
/service/grc/risk-treatment                         → RiskTreatmentPlansPage
/service/grc/risk-treatment/:rtapId                 → RTAPDetailPage
/service/grc/risk-performance-reports               → RiskPerformanceReportsPage
/service/grc/risk-performance-reports/:reportId     → RiskPerformanceReportDetailPage
/service/grc/risk-meetings                          → RiskMeetingsPage

/service/grc/quality-auditors                       → QualityAuditorsPage
/service/grc/quality-auditors/:auditorId            → QualityAuditorDetailPage
/service/grc/qa-training                            → QATrainingPage
/service/grc/qa-training/:sessionId                 → QATrainingDetailPage
/service/grc/qms-programs                           → QMSProgramsPage
/service/grc/qms-programs/:programId                → QMSProgramDetailPage  ← contains embedded "Audit Plans" section
/service/grc/qms-plans                              → QMSPlansPage           (route retained; not in sidebar)
/service/grc/qms-plans/:planId                      → QMSPlanDetailPage      ← contains embedded "Checklists" section
/service/grc/qms-checklists                         → QMSChecklistsPage      (route retained; not in sidebar)
/service/grc/quality-audits                         → QMSAuditReportsPage
/service/grc/quality-audits/:reportId               → QMSAuditReportDetailPage
/service/grc/non-conformances                       → NonConformancesPage
/service/grc/non-conformances/:ncId                 → NonConformanceDetailPage
```

> **Note**: QMS Audit Reports are accessed via `/quality-audits` (not `/qms-audit-reports`).

---

## FILE STRUCTURE

```
pages/grc/
  RiskDashboardPage.tsx
  RiskChampionsPage.tsx
  RiskChampionDetailPage.tsx
  RiskAssessmentSheetsPage.tsx
  RiskAssessmentSheetDetailPage.tsx
  DepartmentalRisksPage.tsx
  DeptRiskRegisterDetailPage.tsx
  InstitutionalRisksPage.tsx
  InstitutionalRiskDetailPage.tsx
  RiskTreatmentPlansPage.tsx
  RTAPDetailPage.tsx
  RiskPerformanceReportsPage.tsx
  RiskPerformanceReportDetailPage.tsx
  RiskMeetingsPage.tsx
  QualityAuditorsPage.tsx
  QualityAuditorDetailPage.tsx
  QATrainingPage.tsx
  QATrainingDetailPage.tsx
  QMSProgramsPage.tsx
  QMSProgramDetailPage.tsx
  QMSPlansPage.tsx
  QMSPlanDetailPage.tsx
  QMSChecklistsPage.tsx
  QMSAuditReportsPage.tsx
  QMSAuditReportDetailPage.tsx
  NonConformancesPage.tsx
  NonConformanceDetailPage.tsx

components/grc/
  CreateRiskChampionDialog.tsx
  RCAppointmentSection.tsx
  CreateRiskAssessmentSheetDialog.tsx
  CreateDeptRiskRegisterDialog.tsx
  DeptRegisterEntriesSection.tsx
  CreateInstitutionalRiskRegisterDialog.tsx
  IRREntriesSection.tsx
  IRRActivityReportsSection.tsx
  IRRDistributeButton.tsx
  IRRWorkshopNotifyButtons.tsx
  CreateRTAPDialog.tsx
  RTAPItemsSection.tsx
  RTAPDistributeButton.tsx
  RTAPSendReminderButton.tsx
  CreateQuarterlyPerformanceReportDialog.tsx
  CreateRiskMeetingDialog.tsx
  CreateQualityAuditorDialog.tsx
  QAAppointmentSection.tsx
  CreateQATrainingDialog.tsx
  QATrainingAttendeesSection.tsx
  QATrainingApprovalButtons.tsx
  CreateQMSProgramDialog.tsx
  CreateQMSAuditPlanDialog.tsx
  QMSTeamAssignmentSection.tsx
  QMSTimetableSection.tsx
  CreateQMSChecklistDialog.tsx
  CreateQMSAuditReportDialog.tsx
  QMSReportGovernanceButtons.tsx
  CreateNonConformanceDialog.tsx
  NCDisputeDialog.tsx
  NCResolveDisputeDialog.tsx

hooks/ (grc-scoped, file: useGRCPermissions.tsx + individual files)
  useRiskDashboard.ts
  useRiskChampions.ts
  useRiskAssessmentSheets.ts
  useDeptRiskRegisters.ts
  useInstitutionalRiskRegisters.ts
  useRTAP.ts
  useRiskPerformanceReports (useRiskQPR)
  useRiskMeetings.ts
  useQualityAuditors.ts
  useQATraining.ts
  useQMSAuditPlans.ts
  useQMSAuditReports.ts
  useNonConformances.ts

services/grcService.ts     — all API calls
types/grc.ts               — all TypeScript types
hooks/useGRCPermissions.tsx — permission flags
```

---

## PERMISSIONS HOOK (useGRCPermissions.tsx)

```ts
// Risk Management permissions
canManageRiskChampions:   'grc:risk_champion:manage'
canViewRiskChampions:     'grc:risk_champion:view' OR manage
canConductRiskAssessments:'grc:risk_assessment_sheet:conduct'
canReviewRiskAssessments: (derived — used in RAS detail page)
canManageDeptRegisters:   'grc:dept_risk_register:manage'
canManageIRR:             'grc:institutional_risk_register:manage'
canManageRTAP:            'grc:rtap:manage'
canRespondRTAP:           'grc:rtap:respond'
canManageQPR:             'grc:quarterly_risk_report:manage'
canManageRiskMeetings:    'grc:risk_meeting:manage'
canViewRiskMeetings:      'grc:risk_meeting:view'
canViewRiskDashboard:     'grc:risk_dashboard:view'

// Quality Assurance permissions
canManageQualityAuditors: 'grc:quality_auditor:manage'
canManageQATraining:      'grc:qa_training:manage'
canManageQMSPrograms:     'grc:qms_audit_program:manage'
canManageQMSPlans:        'grc:qms_audit_plan:manage'
canManageQMSChecklists:   'grc:qms_checklist:manage'
canManageQMSReports:      'grc:qms_audit_report:manage'
canSignQMSReports:        'grc:qms_audit_report:sign'
canManageNCs:             'grc:non_conformance:manage'
canRespondNCs:            'grc:non_conformance:respond'
```

---

## STATUS BADGE COLOUR MAPS

### Risk Assessment Sheet (RAS)
```ts
draft:               'bg-gray-100 text-gray-700'
submitted_to_head:   'bg-blue-100 text-blue-800'
head_endorsed:       'bg-teal-100 text-teal-800'
submitted_to_rmqam:  'bg-indigo-100 text-indigo-800'
approved:            'bg-green-100 text-green-800'
returned_for_rework: 'bg-red-100 text-red-800'
```

### Risk Champion
```ts
pending:             'bg-gray-100 text-gray-700'
nominated:           'bg-blue-100 text-blue-800'
under_review:        'bg-yellow-100 text-yellow-800'
letter_drafted:      'bg-purple-100 text-purple-800'
letter_reviewed:     'bg-indigo-100 text-indigo-800'
training_scheduled:  'bg-cyan-100 text-cyan-800'
exam_pending:        'bg-orange-100 text-orange-800'
passed:              'bg-lime-100 text-lime-800'
failed:              'bg-red-100 text-red-800'
appointed:           'bg-teal-100 text-teal-800'
active:              'bg-green-100 text-green-800'
inactive:            'bg-gray-100 text-gray-500'
```

### Dept Risk Register / IRR / RTAP / QPR
```ts
in_progress / draft / compiled:  'bg-gray-100 text-gray-800'  (or blue)
submitted:                        'bg-yellow-100 text-yellow-800'
approved:                         'bg-green-100 text-green-800'
rejected:                         'bg-red-100 text-red-800'
active:                           'bg-blue-100 text-blue-800'  (RTAP only)
```

### QMS Audit Report (most complex)
```ts
draft:                          'bg-gray-100 text-gray-800'
tl_signed:                      'bg-blue-100 text-blue-800'
auditee_acknowledged:           'bg-indigo-100 text-indigo-800'
finalised:                      'bg-cyan-100 text-cyan-800'
submitted_to_rmqam:             'bg-yellow-100 text-yellow-800'
returned_for_revision:          'bg-orange-100 text-orange-800'
presented_at_mrm:               'bg-purple-100 text-purple-800'
directives_received:            'bg-teal-100 text-teal-800'
submitted_to_audit_committee:   'bg-amber-100 text-amber-800'
audit_committee_reviewed:       'bg-lime-100 text-lime-800'
adopted_by_commission:          'bg-green-100 text-green-800'
```

### Non-Conformance
```ts
disputed: 'bg-orange-100 text-orange-800'
resolved: 'bg-blue-100 text-blue-800'
(others from closure_status field — raised/in_progress/closed pattern assumed)
```

---

## API ENDPOINTS (grcService.ts — paths relative to GRC service base URL)

```
risk/champions/                         GET (list), POST (create)
risk/champions/:id/                     GET, PATCH
risk/champions/appointments/            GET, POST
risk/assessments/                       GET, POST
risk/assessments/:id/                   GET, PATCH
risk/dept-registers/                    GET, POST
risk/dept-registers/:id/                GET, PATCH, DELETE
risk/dept-registers/entries/            GET, POST
risk/institutional-registers/           GET, POST
risk/institutional-registers/:id/       GET, PATCH, DELETE
risk/institutional-registers/entries/              GET, POST
risk/institutional-registers/activity-reports/     GET, POST
risk/rtap/                              GET, POST (RTAP has create in actual code)
risk/rtap/:id/                          GET, PATCH
risk/rtap-items/                        GET, POST
risk/rtap-items/quarterly-updates/      GET, POST
risk/quarterly-reports/                 GET, POST
risk/quarterly-reports/:id/             GET, PATCH
risk/meetings/                          GET, POST
risk/meetings/attendance/               GET, POST
risk/dashboard/                         GET
risk/dashboard/comparative-analysis/    GET

risk/quality-auditors/                  GET, POST
risk/quality-auditors/:id/              GET, PATCH
risk/quality-auditors/appointments/     GET, POST
risk/qa-training/                       GET, POST
risk/qa-training/:id/                   GET, PATCH
risk/qa-training/attendees/             GET, POST
risk/qms-programs/                      GET, POST
risk/qms-programs/:id/                  GET, PATCH
risk/qms-plans/                         GET, POST
risk/qms-plans/:id/                     GET, PATCH
risk/qms-plans/team/                    GET, POST
risk/qms-plans/audit-meetings/          GET, POST
risk/qms-plans/timetable/               GET, POST
risk/qms-checklists/                    GET, POST
risk/qms-checklists/:id/                GET, PATCH
risk/qms-reports/                       GET, POST
risk/qms-reports/:id/                   GET, PATCH
risk/non-conformances/                  GET, POST
risk/non-conformances/:id/              GET, PATCH
risk/non-conformances/monthly-summary/  GET
```

> Workflow endpoints follow the pattern (via EmbeddedWorkflowConsole):
> `POST /risk/:entityType/:id/workflow/start/`
> `POST /risk/:entityType/:id/workflow/recall/`
> `GET  /risk/:entityType/:id/workflow/status/`

---

---

## 1. RISK DASHBOARD
URL: /service/grc/risk-dashboard
File: RiskDashboardPage.tsx

Risk Management Dashboard
Overview of risk assessments, registers, treatment plans, and quality assurance metrics

[Live Data badge]

---
ROW 1 — Summary Stat Cards (clickable, navigate to respective page):
[Risk Assessments: N]   [Dept. Registers: N]   [Institutional Registers: N]   [Treatment Plans: N]   [Non-Conformances: N]
(5 cards in a responsive grid: md:grid-cols-2 lg:grid-cols-5)
---

---
ROW 2 — Status Breakdown Cards (clickable, navigate to respective page):
[Dept. Risk Registers — by status breakdown]
[Institutional Registers — by status breakdown]
[Treatment Plans — by status breakdown]
[Non-Conformances — by status breakdown]
(4 cards in a responsive grid: md:grid-cols-2 lg:grid-cols-4)

Each breakdown card shows:
  Entity count total (large number top-right)
  Per-status rows: status label (capitalised) | count badge
---

---
ROW 3 — Comparative Analysis Chart (Recharts BarChart):
Title: "Comparative Analysis — Risk Registers by Status"
X-axis: org_unit_id or fiscal_year (auto-detected from data shape)
Y-axis: counts
Bars: one bar per status key, colour-coded via CHART_COLORS array
Source: GET risk/dashboard/comparative-analysis/
---

---
ROW 4 — Quick Link Cards (clickable, navigate to page):
[Risk Champions]   [Performance Reports]   [QMS Audit Reports]   [Risk Meetings]
(4 cards: md:grid-cols-3 lg:grid-cols-4)
---

API:
  GET /api/v1/grc/risk/dashboard/              → summary stats + status breakdowns
  GET /api/v1/grc/risk/dashboard/comparative-analysis/  → chart data

> Design difference: Design had a "Quick Links" section and "Active Workflows" panel + risk
> distribution bar chart. Actual has stat cards + status breakdown cards + comparative chart +
> quick links. No active workflows panel. No "Risk Settings" config link on dashboard.

---

---

## 2. RISK CHAMPIONS
URL: /service/grc/risk-champions
File: RiskChampionsPage.tsx

Risk Champions

[+ New Risk Champion]   (visible when canManageRiskChampions)
[Search risk champions...]   [All Statuses ▼]

---
| Nominee Name | Directorate/Unit/Zone | Status | Updated |
|              |                       | [badge]|         |
---
Pagination: page selector + rows per page
Filters: search (text), status (pending/nominated/under_review/appointed/active/inactive)
Delete guard: only pending or inactive champions can be deleted.

CreateRiskChampionDialog:
> Fields defined in CreateRiskChampionDialog.tsx (nominee user, directorate/unit/zone, etc.)

---

On clicking [View] for a champion:
URL: /service/grc/risk-champions/:championId
File: RiskChampionDetailPage.tsx

Risk Champion
[Nominee full name]
Status: [badge]

--- Champion Details Card ---
  Nominee:              [UserDisplay — resolved from IAM]
  Status:               [badge]
  Directorate/Unit/Zone:[text]
  Active:               Yes / No

--- RC Appointments Section (RCAppointmentSection component) ---
  Lists appointments for this champion.
  [+ Create Appointment]  (canManageRiskChampions)
  Appointment workflow: grc.risk_champion_appointment

> Design difference: Design had 3 tabs (Profile, Appointments, Activity Log).
> Actual uses flat card layout — Champion Details card + RCAppointmentSection below it.
> No "Activity Log" tab is implemented.

---

---

## 3. RISK ASSESSMENT SHEETS
URL: /service/grc/risk-assessment-sheets
File: RiskAssessmentSheetsPage.tsx

Risk Assessment Sheets

[+ New Assessment Sheet]   (visible when canConductRiskAssessments)
[Search assessment sheets...]   [All Statuses ▼]   [Filter by directorate... (text input)]

---
| Reference No. | Risk Description (truncated 60 chars) | Category | Risk Owner | Likelihood | Impact | Inherent Risk | Status |
---
Pagination: page selector + rows per page
Delete guard: only draft sheets can be deleted.

Status filter options: draft | submitted_to_head | head_endorsed | submitted_to_rmqam | approved | returned_for_rework

CreateRiskAssessmentSheetDialog:
> Fields defined in CreateRiskAssessmentSheetDialog.tsx

---

On clicking [View]:
URL: /service/grc/risk-assessment-sheets/:sheetId
File: RiskAssessmentSheetDetailPage.tsx

Risk Assessment Sheet
Ref: [reference_number monospace]
Status: [badge]

Action buttons (contextual — at top header area):
  draft               → [Submit to Head]  (canConductRiskAssessments)
  submitted_to_head   → [Endorse]         (canReviewRiskAssessments)
  head_endorsed       → [Submit to RMQAM] (canConductRiskAssessments)
  submitted_to_rmqam  → [Approve]         (canReviewRiskAssessments)
                      → [Return for Rework] (canReviewRiskAssessments) → opens dialog
  returned_for_rework → [Resubmit]        (canConductRiskAssessments)

--- Risk Details Card ---
  Risk Description      [full text]
  Risk Category         [text]
  Risk Owner            [UserDisplay — IAM UUID]
  Directorate/Unit/Zone [text]
  Likelihood Rating     [value]
  Impact Rating         [value]
  Inherent Risk Level   [value]
  Residual Risk Level   [value or —]

--- Controls Card (conditional — shown only if existing_controls OR proposed_controls present) ---
  Existing Controls    [text block]
  Proposed Controls    [text block]

Return for Rework Dialog:
  Review Comments *    [Textarea — feedback for risk champion]
  [Cancel]  [Return]
  Note: [Return] disabled if review_comments is empty.

> Design difference: Design had a single read-only detail page without workflow progression.
> Actual has multi-stage inline workflow (no EmbeddedWorkflowConsole — uses direct mutation calls).
> Design did not show Residual Risk or Controls section.
> No tabs. Flat card layout.

---

---

## 4. DEPARTMENTAL RISKS (Departmental Risk Registers)
URL: /service/grc/departmental-risks
File: DepartmentalRisksPage.tsx

Departmental Risk Registers

[+ New Register]   (visible when canManageDeptRegisters)
[Search...]   [All Statuses ▼]

---
| Reference No. | Directorate/Unit/Zone | Reporting Period | Status | Updated |
---
Pagination: page selector + rows per page
Status: in_progress | submitted | approved | rejected
Delete guard: only certain statuses can be deleted.

CreateDeptRiskRegisterDialog:
> Fields: directorate_unit_zone, reporting_period (and other fields per dialog)

---

On clicking [View]:
URL: /service/grc/departmental-risks/:registerId
File: DeptRiskRegisterDetailPage.tsx

Departmental Risk Register
Ref: [reference_number monospace]
Status: [badge]

Action buttons:
  in_progress + no workflow  → [Submit to RMQAM]  (canManageDeptRegisters)
  in workflow + not completed → [Recall]           (canManageDeptRegisters)

--- Register Details Card ---
  Reference Number    [monospace]
  Status              [badge]
  Directorate/Unit/Zone [text]
  Reporting Period    [text]

--- Dept Register Entries Section (DeptRegisterEntriesSection component) ---
  Lists risk entries in this register.
  [+ Add Entry]  (visible when isModifiable AND canManageDeptRegisters)
  Component: CreateDeptRegisterEntryDialog

--- Workflow Console (EmbeddedWorkflowConsole) ---
  entityType="dept-risk-register"
  entityId={registerId}
  entityTitle="Departmental Risk Register"
  entityReference={register.reference_number}

> Design difference: Design had 3 tabs (Risk Entries, Workflow, Audit Log).
> Actual uses flat card layout — Details card → Entries section → Workflow console stacked.
> No "Audit Log" tab. Modifiable when status=in_progress.

---

---

## 5. INSTITUTIONAL RISKS (Institutional Risk Registers)
URL: /service/grc/institutional-risks
File: InstitutionalRisksPage.tsx

Institutional Risk Registers

[+ New Register]   (visible when canManageIRR)
[Search...]   [All Statuses ▼]

---
| Reference No. | Reporting Period | Status | Updated |
---
Status: draft | compiled | submitted | approved | rejected

CreateInstitutionalRiskRegisterDialog:
> Fields: reporting_period, workshop_date, workshop_venue, committee_meeting_date (and others)

---

On clicking [View]:
URL: /service/grc/institutional-risks/:registerId
File: InstitutionalRiskDetailPage.tsx

Institutional Risk Register
Ref: [reference_number monospace]
Status: [badge]

Action buttons:
  compiled + no workflow    → [Submit for Governance]  (canManageIRR)
  in workflow + uncompleted → [Recall]                 (canManageIRR)

--- Register Details Card ---
  Reference Number     [monospace]
  Reporting Period     [text]
  Status               [badge]
  Workshop Date        [if set]
  Workshop Venue       [if set]
  Committee Meeting Date [if set]

--- Notifications & Distribution Card (canManageIRR only) ---
  [Notify Directors]       (if not yet notified, shows button)
                           (if notified, shows badge "Directors notified on {date}")
  [Notify Risk Champions]  (if not yet notified, shows button)
                           (if notified, shows badge "RCs notified on {date}")
  [Distribute to Directorates] (if status=approved AND not yet distributed)
                               (if distributed, shows badge with date + distribution_reference)

--- IRR Entries Section (IRREntriesSection component) ---
  Lists institutional risk entries.
  [+ Add from Departmental Registers]  (visible when isModifiable AND canManageIRR)
  isModifiable = status=draft OR status=compiled

--- IRR Activity Reports Section (IRRActivityReportsSection component) ---
  Lists activity reports submitted by Risk Champions for this IRR.
  [+ Submit Activity Report]  (canManageIRR — or RC with permission)

--- Workflow Console (EmbeddedWorkflowConsole) ---
  entityType="institutional-risk-register"
  entityId={registerId}
  entityTitle="Institutional Risk Register"
  entityReference={register.reference_number}

> Design difference: Design had 4 tabs (Risk Entries, Activity Reports, Workflow, Audit Log).
> Actual uses flat card layout. No "Audit Log" tab. Additional "Notifications & Distribution"
> card not in design. Status includes "compiled" (design had "draft" only).

---

---

## 6. RISK TREATMENT PLANS (RTAP)
URL: /service/grc/risk-treatment
File: RiskTreatmentPlansPage.tsx

Risk Treatment Action Plans

[+ New RTAP]   (visible when canManageRTAP)
[Search...]   [All Statuses ▼]

---
| Reference No. | IRR Reference | Period | Status | Updated |
---
Status: draft | submitted | approved | rejected | active

> IMPORTANT DESIGN DEVIATION: The design document stated "RTAP is auto-created when an IRR
> is approved — NO [+ Create] button on this page." The actual implementation HAS a Create
> button (CreateRTAPDialog). This means manual RTAP creation is allowed in the actual code.

CreateRTAPDialog:
> Fields: institutional_risk_register (link), period, and other fields

---

On clicking [View]:
URL: /service/grc/risk-treatment/:rtapId
File: RTAPDetailPage.tsx

Risk Treatment Action Plan
Ref: [reference_number monospace]
Status: [badge]

Action buttons:
  draft + no workflow  → [Submit RTAP]              (canManageRTAP)
  in workflow          → [Recall]                   (canManageRTAP)
  active               → [Send Reminder to RCs]     (canManageRTAP)
  approved + not distributed → [Distribute to Directorates] (canManageRTAP)

--- Plan Details Card ---
  Reference Number                [monospace]
  Period                          [text]
  Institutional Risk Register     [text — linked IRR]
  Distributed [date + ref]        [if distributed]

--- RTAP Items Section (RTAPItemsSection component) ---
  Lists treatment items.
  [+ Add Treatment Item]  (visible when isModifiable AND canManageRTAP)
  isModifiable = status=draft
  Component: CreateRTAPItemDialog

--- Workflow Console (EmbeddedWorkflowConsole) ---
  entityType="rtap"
  entityId={rtapId}
  entityTitle="Risk Treatment Action Plan"
  entityReference={rtap.reference_number}

> Design difference: Design had 4 tabs (Treatment Items, Quarterly Updates, Workflow, Audit Log).
> Actual uses flat card layout. No Quarterly Updates tab implemented as separate section.
> No "Audit Log" tab. Send Reminder to RCs button not in design.

---

---

## 7. PERFORMANCE REPORTS (Quarterly Performance Reports)
URL: /service/grc/risk-performance-reports
File: RiskPerformanceReportsPage.tsx

Quarterly Performance Reports

[+ New Report]   (visible when canManageQPR)
[Search...]   [All Statuses ▼]

---
| Reference No. | Quarter | Fiscal Year | Implementation Rate | Status | Updated |
---
Status: (per created statuses)

CreateQuarterlyPerformanceReportDialog:
> Fields: quarter, fiscal_year, implementation_rate (and others)

---

On clicking [View]:
URL: /service/grc/risk-performance-reports/:reportId
File: RiskPerformanceReportDetailPage.tsx

Performance Report
Ref: [reference_number monospace]
Status: [badge]

Action buttons:
  draft + no workflow  → [Submit]  (canManageQPR)
  in workflow          → [Recall]  (canManageQPR)

--- Report Details Card ---
  Reference Number    [monospace]
  Quarter             [text]
  Fiscal Year         [text]
  Implementation Rate [text]
  (and other fields)

--- Additional content card (conditional) ---
  (if report has additional content)

--- Workflow Console (EmbeddedWorkflowConsole) ---
  entityType="quarterly-risk-report"  (inferred from hook names)
  entityTitle="Performance Report"

> Design difference: Design called this "Quarterly Performance Reports" (QPR/2025/Q1 format).
> Actual sidebar label is "Performance Reports". Detail page title is "Performance Report".
> Design had 4 tabs. Actual uses flat cards + workflow console. No Activity Reports tab.

---

---

## 8. RISK MEETINGS
URL: /service/grc/risk-meetings
File: RiskMeetingsPage.tsx

Risk Meetings

[+ New Meeting]   (visible when canManageRiskMeetings)
[Search...]

---
| Title | Type (badge: risk_assessment / management_review / workshop / training / committee) | Scheduled Date | Venue |
---
Pagination: page selector + rows per page

Meeting type badge colours:
  risk_assessment:    'bg-blue-100 text-blue-800'
  management_review:  'bg-purple-100 text-purple-800'
  workshop:           'bg-cyan-100 text-cyan-800'
  training:           'bg-green-100 text-green-800'
  committee:          'bg-indigo-100 text-indigo-800'

CreateRiskMeetingDialog:
> Fields: title, meeting_type, scheduled_date, venue (and others)

> Note on View: clicking [View] opens a modal/inline view (viewingItem state),
> NOT a separate route/detail page for Risk Meetings.

> DESIGN DEVIATION: This page was NOT in corrected_UI_design.md at all.
> It is an additional page in the actual implementation for scheduling and tracking
> Risk & Governance Committee meetings, workshops, and management reviews.

---

---

## 9. QUALITY AUDITORS
URL: /service/grc/quality-auditors
File: QualityAuditorsPage.tsx

Quality Auditors

[+ New Auditor]   (visible when canManageQualityAuditors)
[Search auditors...]   [All Statuses ▼]

---
| Nominee Name | Directorate/Unit/Zone | Cert. Date | Exam Score | Status |
---
Pagination: page selector + rows per page

CreateQualityAuditorDialog:
> Fields: nominee (IAM user), directorate_unit_zone, notes (and others per dialog)

---

On clicking [View]:
URL: /service/grc/quality-auditors/:auditorId
File: QualityAuditorDetailPage.tsx

Quality Auditor
Status: [badge]

--- Auditor Details Card ---
  Auditor (nominee)    [UserDisplay — IAM UUID]
  org / unit           [text]
  Is Certified         [boolean display]
  (exam_score, attempt_count shown in conditional cards)

--- Exam Status Card(s) (conditional — based on certification/exam state) ---
  Exam score card displayed when exam results exist
  Certification date displayed when is_certified = true

--- QA Appointments Section (QAAppointmentSection component) ---
  Lists QA appointments for this auditor.
  [+ Create Appointment]  (canManageQualityAuditors and is_certified = true)
  Appointment workflow: grc.qa_appointment

> Design difference: Design had 5 tabs (Profile, Exam Results, Appointments, Audit History,
> Activity Log) with complex exam attempt banners. Actual uses flat card layout with
> QAAppointmentSection below. No separate Exam Results tab — exam info in detail cards.
> No Audit History tab. No Activity Log tab.
> Exam status banners (not certified / re-sit needed / max attempts reached / certified) may
> be implemented in the cards area but specific state rendering is in QualityAuditorDetailPage.

---

---

## 10. QA TRAINING
URL: /service/grc/qa-training
File: QATrainingPage.tsx

QA Training Sessions

[+ New Training Session]   (visible when canManageQATraining)
[Search...]

---
| Trainer | Date | Venue | Status |
---
Pagination: page selector + rows per page

CreateQATrainingDialog:
> Fields: trainer (IAM user), training_date, venue, description (and others)

---

On clicking [View]:
URL: /service/grc/qa-training/:sessionId
File: QATrainingDetailPage.tsx

QA Training Session
Status: [approval_status badge]

Action buttons (contextual on approval_status):
  proposed → [Approve]  (canManageQATraining)
            → [Reject]  (canManageQATraining) → opens Reject dialog with reason textarea
  approved → [Notify Attendees]  (canManageQATraining)

--- Training Session Details Card ---
  Trainer      [UserDisplay]
  Date         [text]
  Venue        [text]
  Description  [text]
  (other fields from session model)

--- Attendees Section (QATrainingAttendeesSection component) ---
  Lists registered attendees.
  [+ Add Attendee]  (canManageQATraining)

Reject Dialog:
  Reason *   [Textarea]
  [Cancel]   [Reject]

> DESIGN DEVIATION: QA Training is entirely new — not in corrected_UI_design.md.
> This manages ISO lead auditor training sessions before the exam stage. It connects to
> the QA certification lifecycle (training → exam → appointment).

---

---

## 11. QMS AUDIT PROGRAMS
URL: /service/grc/qms-programs
File: QMSProgramsPage.tsx

QMS Audit Programs

[+ New Program]   (visible when canManageQMSPrograms)
[Search...]   [All Statuses ▼]

---
| Reference No. | Audit Year | Scope (truncated) | Status | Updated |
---
Pagination: page selector + rows per page

CreateQMSProgramDialog:
> Fields: audit_year, scope, objectives (and others)

---

On clicking [View]:
URL: /service/grc/qms-programs/:programId
File: QMSProgramDetailPage.tsx

QMS Audit Program
Ref: [reference_number monospace]
Status: [badge]

--- Program Details Card ---
  Reference Number    [monospace]
  Audit Year          [text]
  Scope               [text]
  Objectives          [text]
  (other fields)

--- Workflow Console (EmbeddedWorkflowConsole) ---
  entityTitle="QMS Audit Program"
  Workflow: grc.qms_audit_program_approval

> Design difference: Design had 3 tabs (Audit Plans, Workflow, Audit Log).
> Actual uses flat cards. Audit Plans are NOT embedded in the program detail — they have their
> own standalone list page (QMSPlansPage). The program detail page does NOT show a list of
> audit plans under this program (only program details + workflow).
> Note: This may mean the audit plans filtering by program is done from the QMS Audit Plans page.

---

---

## 12. QMS AUDIT PLANS
URL: /service/grc/qms-plans
File: QMSPlansPage.tsx

QMS Audit Plans

[+ New Audit Plan]   (visible when canManageQMSPlans)
[Search...]   [All Statuses ▼]

---
| Reference No. | Program | Start Date | End Date | Team Leader | Status | Updated |
---
Pagination: page selector + rows per page

CreateQMSAuditPlanDialog:
> Fields: qms_program (linked program), auditee_unit, start_date, end_date, scope (and others)

> DESIGN DEVIATION: The design had QMS Audit Plans only accessible via a Program's Audit Plans
> tab (no standalone list page). The actual implementation has a full standalone list page for
> all plans across all programs.

---

On clicking [View]:
URL: /service/grc/qms-plans/:planId
File: QMSPlanDetailPage.tsx

QMS Audit Plan
Ref: [reference_number monospace]
Status: [badge]

Action buttons:
  draft → [Submit Audit Plan]  (canManageQMSPlans)

--- Plan Details Card ---
  Reference Number    [monospace]
  Parent Program      [text — linked program]
  Auditee Unit        [text]
  Audit Start Date    [text]
  Audit End Date      [text]
  Scope               [text]
  (other fields)

--- Team Assignment Section (QMSTeamAssignmentSection component) ---
  Lists assigned QA team members with roles.
  [+ Assign Auditor]  (canManageQMSPlans)

--- Timetable Section (QMSTimetableSection component) ---
  Audit schedule / timetable entries.
  [+ Add Timetable Entry]

--- Workflow Console (EmbeddedWorkflowConsole) ---
  entityTitle="QMS Audit Plan"
  Workflow: grc.qms_audit_plan_approval

> Design difference: Design for the QMS Plan Detail had 6 tabs (Team, Checklists, Audit Report,
> Non-Conformances, Workflow, Audit Log). Actual uses flat card layout with Team + Timetable
> sections + Workflow console. Checklists, Audit Report, and Non-Conformances are NOT embedded
> inside the Plan detail — they have their own standalone list pages.

---

---

## 13. QMS AUDIT CHECKLISTS
URL: /service/grc/qms-checklists
File: QMSChecklistsPage.tsx

QMS Audit Checklists

[+ New Checklist]   (visible when canManageQMSChecklists)
[Search...]

---
| Plan Reference | QA | Process | ISO Clauses | Status | Updated |
---

CreateQMSChecklistDialog:
> Fields: qms_plan (linked plan), assigned_qa (IAM user), assigned_process, iso_clauses (multi-select)

> DESIGN DEVIATION: The design had checklists embedded inside the Audit Plan's "Checklists"
> tab. The actual implementation has a full standalone list page for all checklists.
> This enables organisation-wide checklist management across all audit plans.

---

No detail page for QMS Checklists. All management (view, edit) done inline in the list.

---

---

## 14. QMS AUDIT REPORTS
URL: /service/grc/quality-audits
File: QMSAuditReportsPage.tsx

QMS Audit Reports

[+ New Audit Report]   (visible when canManageQMSReports)
[Search...]   [All Statuses ▼]

---
| Reference No. | Plan | Auditee Directorate | Audit Date | QA | Status | Updated |
---
Pagination: page selector + rows per page

CreateQMSAuditReportDialog:
> Fields: qms_plan (linked plan), auditee_directorate, audit_date, qa (IAM user) (and others)

> DESIGN DEVIATION: Design had audit reports accessible only from inside a Plan's "Audit Report"
> tab with ONE report per plan. Actual has a standalone list page with Create button, meaning
> multiple reports per plan may be possible, or this is the primary management interface.

---

On clicking [View]:
URL: /service/grc/quality-audits/:reportId  
File: QMSAuditReportDetailPage.tsx

QMS Audit Report
Ref: [reference_number monospace]
Status: [badge]

Action buttons — COMPLEX MULTI-STAGE GOVERNANCE WORKFLOW:
  draft                        → [Sign as TL]                   (canSignQMSReports)
  tl_signed                    → [Sign as Auditee]              (canSignQMSReports)
  finalised                    → [Submit to RMQAM]              (canManageQMSReports)
  submitted_to_rmqam           → [Present at MRM]               (canManageQMSReports)
                               → [Return for Revision]          (canManageQMSReports) → dialog
  presented_at_mrm             → [Record Directives]            (canManageQMSReports) → dialog
  directives_received          → [Submit to Audit Committee]    (canManageQMSReports)
  submitted_to_audit_committee → [Audit Committee Reviewed]     (canManageQMSReports)
  audit_committee_reviewed     → [Adopt by Commission]          (canManageQMSReports)

Status lifecycle:
  draft → tl_signed → auditee_acknowledged → finalised
  → submitted_to_rmqam → (returned_for_revision → draft loop)
  → presented_at_mrm → directives_received
  → submitted_to_audit_committee → audit_committee_reviewed → adopted_by_commission

--- Report Details Card ---
  Reference Number            [monospace]
  QMS Plan                    [linked plan ref]
  Auditee Directorate         [text]
  Audit Date                  [date]
  Status                      [badge]
  TL Signed At                [if set]
  Auditee Signed At           [if set]

--- RMQAM Review Comments Card (conditional — if rmqam_review_comments set) ---
  Review comments             [pre-wrapped text]
  Returned at                 [returned_for_revision_at date]

--- MRM Directives Card (conditional — if mrm_directives set) ---
  MRM Directives              [pre-wrapped text]
  Communicated at             [mrm_directives_communicated_at date]

Return for Revision Dialog:
  RMQAM review comments *    [Textarea]
  [Cancel]   [Return for Revision]

Record MRM Directives Dialog:
  MRM Directives *           [Textarea]
  [Cancel]   [Record Directives]

> Design difference: Design had the audit report inside the Audit Plan detail page as a single
> child object with a simpler status flow (draft → tl_signed → auditee_acknowledged → finalised).
> Actual has a far richer governance lifecycle going through RMQAM, MRM presentation, directives,
> Audit Committee, and Commission adoption. Standalone page not in design.

---

---

## 15. NON-CONFORMANCES
URL: /service/grc/non-conformances
File: NonConformancesPage.tsx

Non-Conformances

[+ New Non-Conformance]   (visible when canManageNCs)
[Search NCs...]   [All Statuses ▼]   [All Types ▼]

---
| Reference No. | Audit Report | ISO Clause | Responsible Party | Target Date | Status | Updated |
---
Pagination: page selector + rows per page

Status: raised | in_progress | closed | disputed | resolved (inferred from statusColors + action buttons)

CreateNonConformanceDialog:
> Fields: audit_report (linked report), iso_clause_violated, responsible_party (IAM user),
>         description, target_date, nc_type (and others)

> DESIGN DEVIATION: The design said [+ Raise NC] is ONLY available from inside an Audit Plan's
> Non-Conformances tab. The actual implementation has [+ New Non-Conformance] on the standalone
> list page (canManageNCs), allowing direct creation.

---

On clicking [View]:
URL: /service/grc/non-conformances/:ncId
File: NonConformanceDetailPage.tsx

Non-Conformance
Ref: [reference_number monospace] (inferred)
Status: [badge]

Action buttons (contextual on closure_status):
  raised     → [Dispute]         (canRespondNCs)   → opens Dispute dialog
  disputed   → [Resolve Dispute] (canManageNCs)    → opens Resolve dialog

--- NC Details Card ---
  Audit Report             [linked report ref]
  NC Type                  [text]
  ISO Clause Violated      [text]
  Description              [text]
  Responsible Party        [UserDisplay]
  Target Date              [date]
  Status                   [badge]
  (other fields: raised_by, raised_date, etc.)

--- Dispute Details Card (conditional — if dispute_reason set) ---
  Dispute Reason           [pre-wrapped text]
  Disputed At              [date]
  (disputed_by and other dispute fields)

Dispute Dialog:
  Reason *                 [Textarea]
  [Cancel]   [Dispute]
  Note: triggered by responsible party (canRespondNCs) when they dispute the finding.

Resolve Dispute Dialog:
  Resolution Notes         [Textarea]
  [Cancel]   [Resolve]
  Note: triggered by RMQAM (canManageNCs) after reviewing the dispute.

> Design difference: Design had a side drawer/modal, no separate route.
> Actual has a full detail page at /non-conformances/:ncId.
> Design had [Log Progress Update] + [Mark as Closed] pattern.
> Actual has [Dispute] / [Resolve Dispute] pattern — dispute lifecycle rather than progress log.
> Design had Progress Notes section with history. Actual does not (or it's not visible).

---

---

## CROSS-CUTTING NOTES

---

### A. Layout Pattern (ALL Detail Pages)

Unlike the design which proposed tabbed interfaces, all detail pages use a **flat card-based layout**:

```
[Back button] [Page Title + Ref] [Action Buttons] [Status Badge]
[Card: Primary Details]
[Section Component (entries/items/reports/etc.)]
[Optional conditional Card(s)]
[EmbeddedWorkflowConsole (if applicable)]
```

Pages WITHOUT EmbeddedWorkflowConsole (use direct mutation calls):
- RiskAssessmentSheetDetailPage — inline status transitions via direct mutations
- QATrainingDetailPage — approve/reject via direct mutations
- QMSAuditReportDetailPage — complex multi-stage via direct mutations (no workflow console)
- NonConformanceDetailPage — dispute/resolve via direct mutations

Pages WITH EmbeddedWorkflowConsole:
- DeptRiskRegisterDetailPage
- InstitutionalRiskDetailPage
- RTAPDetailPage
- RiskPerformanceReportDetailPage
- QMSProgramDetailPage
- QMSPlanDetailPage

---

### B. API Client Pattern

```ts
// services/grcService.ts
// All Risk Management calls go through the GRC service client
// Base URL: /api/v1/grc/

// Endpoint paths reference (from ENDPOINTS const in grcService.ts):
riskChampions:               'risk/champions/'
rcAppointments:              'risk/champions/appointments/'
riskAssessmentSheets:        'risk/assessments/'
deptRiskRegisters:           'risk/dept-registers/'
deptRegisterEntries:         'risk/dept-registers/entries/'
institutionalRiskRegisters:  'risk/institutional-registers/'
irrEntries:                  'risk/institutional-registers/entries/'
irrActivityReports:          'risk/institutional-registers/activity-reports/'
rtap:                        'risk/rtap/'
rtapItems:                   'risk/rtap-items/'
rtapQuarterlyUpdates:        'risk/rtap-items/quarterly-updates/'
quarterlyPerfReports:        'risk/quarterly-reports/'
riskMeetings:                'risk/meetings/'
meetingAttendance:           'risk/meetings/attendance/'
riskDashboard:               'risk/dashboard/'
riskDashboardComparative:    'risk/dashboard/comparative-analysis/'

qualityAuditors:             'risk/quality-auditors/'
qaAppointments:              'risk/quality-auditors/appointments/'
qaTrainingSessions:          'risk/qa-training/'
qaTrainingAttendees:         'risk/qa-training/attendees/'
qmsPrograms:                 'risk/qms-programs/'
qmsPlans:                    'risk/qms-plans/'
qmsTeamAssignments:          'risk/qms-plans/team/'
qmsMeetings:                 'risk/qms-plans/audit-meetings/'
qmsTimetable:                'risk/qms-plans/timetable/'
qmsChecklists:               'risk/qms-checklists/'
qmsAuditReports:             'risk/qms-reports/'
nonConformances:             'risk/non-conformances/'
ncMonthlySummary:            'risk/non-conformances/monthly-summary/'
```

---

### C. Workflow Integration

```tsx
// All workflow-bearing entities use EmbeddedWorkflowConsole
import { EmbeddedWorkflowConsole } from '@staff/components/work-orchestration/EmbeddedWorkflowConsole';

<EmbeddedWorkflowConsole
  entityType="dept-risk-register"         // or "institutional-risk-register" | "rtap" | etc.
  entityId={registerId!}
  entityTitle="Departmental Risk Register"
  entityReference={register.reference_number}
  entityStatus={register.status}
  hasWorkflow={workflowStatus?.has_workflow ?? false}
  workflowPlanId={workflowPlanId}
  onSubmit={handleSubmit}
  isLoading={workflowLoading}
  isDraft={isDraft}
  isSubmitting={submitMutation.isPending}
/>
```

Workflow hooks used per entity:
| Entity                   | Hooks                                                       |
|--------------------------|-------------------------------------------------------------|
| DeptRiskRegister         | useDeptRiskRegisterWorkflowStatus, useStartDeptRiskRegisterWorkflow, useRecallDeptRiskRegisterWorkflow |
| InstitutionalRiskRegister| useIRRWorkflowStatus, useStartIRRWorkflow, useRecallIRRWorkflow |
| RTAP                     | useRTAPWorkflowStatus, useStartRTAPWorkflow, useRecallRTAPWorkflow |
| QuarterlyPerfReport      | useQPRWorkflowStatus, useStartQPRWorkflow, useRecallQPRWorkflow |
| QMSAuditProgram          | (EmbeddedWorkflowConsole direct)                            |
| QMSAuditPlan             | (EmbeddedWorkflowConsole direct)                            |

---

### D. Key Differences from Design (corrected_UI_design.md)

| Feature | Design | Actual |
|---------|--------|--------|
| Detail page layout | Tabbed (3–6 tabs) | Flat card/section stack |
| Audit Log tab | Present on most detail pages | NOT implemented anywhere |
| Risk Settings menu item | Dedicated Risk Management entry | Lives in shared GRC Configuration |
| RTAP creation | No Create button (auto-created with IRR) | Has Create button (CreateRTAPDialog) |
| QMS Audit Plans | Embedded in Program detail tab | Standalone list page |
| QMS Checklists | Embedded in Audit Plan tab | Standalone list page |
| QMS Audit Reports | Embedded in Audit Plan tab (1 per plan) | Standalone list page |
| Non-Conformance view | Side drawer/modal (no route) | Full standalone detail page |
| NC lifecycle | Progress log + close pattern | Dispute/resolve dispute pattern |
| QMS Report lifecycle | draft → tl_signed → finalised | draft → ... → adopted_by_commission (10 stages) |
| Risk Dashboard chart | Risk distribution bar chart | Comparative Analysis bar chart (by status) |
| Risk Meetings | Not in design | Standalone page (Type: risk_assessment/management_review/workshop/training/committee) |
| QA Training | Not in design | Standalone page with attendees + approve/reject workflow |
| Quality Auditor detail | 5-tab page with complex exam banners | Flat cards with QAAppointmentSection |
| QPR section in IRR | Activity Reports tab in IRR detail | IRRActivityReportsSection component (not QPR) |
| Dashboard active workflows | Present | Not implemented |
| Quarterly Updates in RTAP | Quarterly Updates tab | Not implemented as separate section |

---

### E. Generic List Page Pattern

All list pages use `GenericListPage` from `@shared/components/GenericListPage`:

```tsx
<GenericListPage
  title="Risk Champions"
  items={transformedItems}
  columns={columns}            // [{ key, label, sortable, render? }]
  userRole="admin"
  onView={handleView}
  onEdit={canManage ? handleEdit : undefined}
  onDelete={canManage ? handleDelete : undefined}
  showCreateButton={false}     // custom [+ New] button in page header
  pagination={...}
  currentPage={page}
  pageSize={pageSize}
  onPageChange={setPage}
  onPageSizeChange={(s) => { setPageSize(s); setPage(1); }}
  itemType="risk champion"
/>
```

---

### F. Permission Gate Usage

```tsx
// Permissions are NOT wrapped in a <PermissionGate> component on risk pages.
// Instead they use conditional rendering with destructured booleans from useGRCPermissions():

const { canManageRiskChampions } = useGRCPermissions();

{canManageRiskChampions && (
  <Button onClick={() => setIsCreateOpen(true)}>
    <Plus className="mr-2 h-4 w-4" /> New Risk Champion
  </Button>
)}
```

> Design proposed `<PermissionGate permission="...">` wrapper components.
> Actual uses direct boolean checks from `useGRCPermissions()` hook.

---

### G. Business Rules Implemented

| Rule | Entity | Enforcement |
|------|--------|-------------|
| Only pending/inactive RC can be deleted | RiskChampion | toast.error on client before delete |
| Only draft sheets can be deleted | RiskAssessmentSheet | toast.error on client before delete |
| RAS status progression locked | RiskAssessmentSheet | Buttons shown only for valid next state |
| IRR modifiable only when draft/compiled | InstitutionalRiskRegister | isModifiable computed from status |
| RTAP modifiable only when draft | RTAP | isModifiable = status === 'draft' |
| Distribute IRR only when approved | InstitutionalRiskRegister | Button only shown when status=approved AND not yet distributed |
| Send RC Reminder only when RTAP active | RTAP | Button only shown when status=active |
| QA exam approve/reject controls | QATrainingDetailPage | Buttons shown only when approval_status=proposed |
| NC Dispute only when raised | NonConformance | Button shown when closure_status=raised, canRespondNCs |
| NC Resolve only when disputed | NonConformance | Button shown when closure_status=disputed, canManageNCs |
| QMS Report TL sign only from draft | QMSAuditReport | Button shown when status=draft, canSignQMSReports |
| QMS Report full governance chain | QMSAuditReport | Multi-stage status with contextual action buttons |

---

*End of Current Implementation UI Document*
*(Source: frontend/apps/staff-portal/src — pages/grc/, components/grc/, hooks/, services/grcService.ts, packages/shared/src/config/servicesConfig.ts, App.tsx)*
