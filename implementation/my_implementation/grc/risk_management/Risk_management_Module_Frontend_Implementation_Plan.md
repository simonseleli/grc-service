# Risk Management & Quality Assurance — Frontend Implementation Plan

**Module:** Risk Management and Quality Assurance (RMQAU)
**Service:** `grc-service` (frontend in `frontend/apps/staff-portal/`)
**Stack:** React 18 · TypeScript · TanStack Query v5 · Tailwind CSS · shadcn/ui · sonner
**Standards:** `frontend_core_patterns.md` · `frontend_component_patterns.md` · `NEW_DETAIL_PAGE_REFERENCE.md`
**Backend:** 100% implemented — all SRS gaps resolved (Phases 1–4 backend fixes applied). All endpoints live at `/api/v1/risk/...`
**Gap Analysis Reference:** `Backend_Gap_Support_Analysis.md` — all 29 gaps fully resolved in backend

---

## Table of Contents

1. [Setup & Module Initialization](#1-setup--module-initialization)
2. [Page Structure Definition](#2-page-structure-definition)
3. [API Integration Layer](#3-api-integration-layer)
4. [Core UI Implementation — List Pages](#4-core-ui-implementation--list-pages)
5. [Detail Pages — Workflow-Enabled](#5-detail-pages--workflow-enabled)
6. [Forms & Modals](#6-forms--modals)
7. [RBAC Enforcement](#7-rbac-enforcement)
8. [Notifications](#8-notifications)
9. [State & Async Handling](#9-state--async-handling)
10. [Navigation & UX Consistency](#10-navigation--ux-consistency)
11. [Integration with Workflow Service](#11-integration-with-workflow-service)
12. [Testing & Validation](#12-testing--validation)
13. [Implementation Order](#13-implementation-order)

---

## 1. Setup & Module Initialization

### 1.1 Folder Structure

Create the following new directories and files. Existing placeholder/mock files are noted with `← REPLACE`.

```
frontend/apps/staff-portal/src/
│
├── pages/grc/                            ← all pages flat in /pages/grc/
│   │
│   │  ── RISK MANAGEMENT ──
│   ├── RiskChampionsPage.tsx             ← REPLACE (currently uses mock data)
│   ├── RiskChampionDetailPage.tsx        ← NEW
│   ├── RiskAssessmentSheetsPage.tsx      ← NEW (Risk Mgmt assessment sheets, NOT internal audit)
│   ├── RiskAssessmentSheetDetailPage.tsx  ← NEW (hosts status-transition actions: submit/endorse/approve/return — Gap 15/28)
│   ├── DepartmentalRisksPage.tsx         ← REPLACE (currently ServicePlaceholder)
│   ├── DeptRiskRegisterDetailPage.tsx    ← NEW
│   ├── InstitutionalRisksPage.tsx        ← REPLACE (currently ServicePlaceholder)
│   ├── InstitutionalRiskDetailPage.tsx   ← NEW
│   ├── RiskTreatmentPlansPage.tsx        ← REPLACE (currently ServicePlaceholder) — becomes RTAP list
│   ├── RTAPDetailPage.tsx                ← NEW
│   ├── RiskPerformanceReportsPage.tsx    ← NEW (Quarterly Performance Reports / QPR)
│   ├── RiskPerformanceReportDetailPage.tsx ← NEW
│   ├── RiskMeetingsPage.tsx              ← NEW
│   │
│   │  ── QUALITY ASSURANCE ──
│   ├── QualityAuditorsPage.tsx           ← REPLACE (currently ServicePlaceholder)
│   ├── QualityAuditorDetailPage.tsx      ← NEW
│   ├── QATrainingPage.tsx                ← NEW
│   ├── QATrainingDetailPage.tsx          ← NEW  (non-workflow detail; hosts QATrainingAttendeesSection)
│   ├── QMSProgramsPage.tsx               ← NEW
│   ├── QMSProgramDetailPage.tsx          ← NEW
│   ├── QMSPlansPage.tsx                  ← NEW
│   ├── QMSPlanDetailPage.tsx             ← NEW
│   ├── QMSChecklistsPage.tsx             ← NEW
│   ├── QMSAuditReportsPage.tsx           ← RENAME: `mv QualityAuditsPage.tsx QMSAuditReportsPage.tsx` then update App.tsx import and component name
│   ├── QMSAuditReportDetailPage.tsx      ← NEW (sign + governance actions — Gaps 12/25/26)
│   ├── NonConformancesPage.tsx           ← NEW
│   └── NonConformanceDetailPage.tsx      ← NEW (dispute/resolve actions — Gap 4; overdue indicator — Gap 5)
│
├── components/grc/
│   ├── risk/                             ← NEW subfolder
│   │   ├── CreateRiskChampionDialog.tsx
│   │   ├── RCAppointmentSection.tsx
│   │   ├── CreateRCAppointmentDialog.tsx
│   │   ├── CreateRiskAssessmentSheetDialog.tsx
│   │   ├── CreateDeptRiskRegisterDialog.tsx
│   │   ├── DeptRegisterEntriesSection.tsx
│   │   ├── CreateDeptRegisterEntryDialog.tsx
│   │   ├── CreateInstitutionalRiskRegisterDialog.tsx
│   │   ├── IRREntriesSection.tsx
│   │   ├── IRRActivityReportsSection.tsx
│   │   ├── IRRWorkshopNotifyButtons.tsx   ← NEW (Gap 8: notify directors/RCs buttons)
│   │   ├── IRRDistributeButton.tsx        ← NEW (Gap 24: distribute to directorates)
│   │   ├── CreateRTAPDialog.tsx
│   │   ├── RTAPItemsSection.tsx
│   │   ├── CreateRTAPItemDialog.tsx
│   │   ├── RTAPSendReminderButton.tsx     ← NEW (Gap 7: send reminder to RCs)
│   │   ├── RTAPDistributeButton.tsx       ← NEW (Gap 24: distribute to directorates)
│   │   ├── RASStatusActionButtons.tsx     ← NEW (Gap 15/28: submit/endorse/approve/return)
│   │   ├── CreateQuarterlyPerformanceReportDialog.tsx
│   │   └── CreateRiskMeetingDialog.tsx
│   │
│   └── quality/                          ← NEW subfolder
│       ├── CreateQualityAuditorDialog.tsx
│       ├── QAAppointmentSection.tsx
│       ├── CreateQAAppointmentDialog.tsx
│       ├── CreateQATrainingDialog.tsx
│       ├── QATrainingAttendeesSection.tsx
│       ├── QATrainingApprovalButtons.tsx   ← NEW (Gap 23: approve/reject/notify-attendees)
│       ├── CreateQMSProgramDialog.tsx
│       ├── CreateQMSAuditPlanDialog.tsx
│       ├── QMSTeamAssignmentSection.tsx
│       ├── QMSTimetableSection.tsx
│       ├── CreateQMSChecklistDialog.tsx
│       ├── CreateQMSAuditReportDialog.tsx
│       ├── SignReportButtons.tsx
│       ├── QMSReportGovernanceButtons.tsx  ← NEW (Gap 12/25/26: governance chain action buttons)
│       ├── CreateNonConformanceDialog.tsx
│       ├── NCDisputeDialog.tsx             ← NEW (Gap 4: dispute NC with reason)
│       └── NCResolveDisputeDialog.tsx      ← NEW (Gap 4: TL resolves dispute)
│
├── hooks/
│   │  ── RISK MANAGEMENT HOOKS (new files) ──
│   ├── useRiskChampions.ts
│   ├── useRCAppointments.ts
│   ├── useRiskAssessmentSheets.ts
│   ├── useDeptRiskRegisters.ts
│   ├── useInstitutionalRiskRegisters.ts
│   ├── useIRRActivityReports.ts
│   ├── useRTAP.ts
│   ├── useRTAPItems.ts
│   ├── useRiskPerformanceReports.ts
│   ├── useRiskMeetings.ts
│   │  ── QUALITY ASSURANCE HOOKS (new files) ──
│   ├── useQualityAuditors.ts
│   ├── useQAAppointments.ts
│   ├── useQATraining.ts
│   ├── useQMSPrograms.ts
│   ├── useQMSAuditPlans.ts
│   ├── useQMSChecklists.ts
│   ├── useQMSAuditReports.ts
│   ├── useNonConformances.ts
│   └── useRiskDashboard.ts
│
└── types/
    └── grc.ts                            ← EXTEND (add risk management type definitions)
```

---

### 1.2 Routing Setup

**File:** `frontend/apps/staff-portal/src/App.tsx`

**Action:** Replace all `<ServicePlaceholder>` elements for Risk Management and Quality Assurance with real page components AND add new routes for missing pages.

#### Replace existing placeholders:

```tsx
// Replace ServicePlaceholder for risk-champions:
<Route path="risk-champions" element={<RiskChampionsPage />} />
<Route path="risk-champions/:championId" element={<RiskChampionDetailPage />} />

// Replace ServicePlaceholder for departmental-risks:
<Route path="departmental-risks" element={<DepartmentalRisksPage />} />
<Route path="departmental-risks/:registerId" element={<DeptRiskRegisterDetailPage />} />

// Replace ServicePlaceholder for institutional-risks:
<Route path="institutional-risks" element={<InstitutionalRisksPage />} />
<Route path="institutional-risks/:registerId" element={<InstitutionalRiskDetailPage />} />

// Replace ServicePlaceholder for risk-treatment:
<Route path="risk-treatment" element={<RiskTreatmentPlansPage />} />
<Route path="risk-treatment/:rtapId" element={<RTAPDetailPage />} />

// Replace ServicePlaceholder for quality-auditors:
<Route path="quality-auditors" element={<QualityAuditorsPage />} />
<Route path="quality-auditors/:auditorId" element={<QualityAuditorDetailPage />} />

// Replace ServicePlaceholder for quality-audits → now QMSAuditReportsPage:
<Route path="quality-audits" element={<QMSAuditReportsPage />} />
<Route path="quality-audits/:reportId" element={<QMSAuditReportDetailPage />} />
```

#### Add new routes (not yet in App.tsx):

```tsx
<Route path="risk-assessment-sheets" element={<RiskAssessmentSheetsPage />} />
<Route path="risk-assessment-sheets/:sheetId" element={<RiskAssessmentSheetDetailPage />} />
<Route path="risk-performance-reports" element={<RiskPerformanceReportsPage />} />
<Route path="risk-performance-reports/:reportId" element={<RiskPerformanceReportDetailPage />} />
<Route path="risk-meetings" element={<RiskMeetingsPage />} />
<Route path="qa-training" element={<QATrainingPage />} />
<Route path="qa-training/:sessionId" element={<QATrainingDetailPage />} />
<Route path="qms-programs" element={<QMSProgramsPage />} />
<Route path="qms-programs/:programId" element={<QMSProgramDetailPage />} />
<Route path="qms-plans" element={<QMSPlansPage />} />
<Route path="qms-plans/:planId" element={<QMSPlanDetailPage />} />
<Route path="qms-checklists" element={<QMSChecklistsPage />} />
<Route path="non-conformances" element={<NonConformancesPage />} />
<Route path="non-conformances/:ncId" element={<NonConformanceDetailPage />} />
```

#### Add all new imports to App.tsx top:

```tsx
// Risk Management pages
import { RiskChampionsPage }                 from '@staff/pages/grc/RiskChampionsPage';
import { RiskChampionDetailPage }            from '@staff/pages/grc/RiskChampionDetailPage';
import { RiskAssessmentSheetsPage }          from '@staff/pages/grc/RiskAssessmentSheetsPage';
import { RiskAssessmentSheetDetailPage }     from '@staff/pages/grc/RiskAssessmentSheetDetailPage';
import { DepartmentalRisksPage }             from '@staff/pages/grc/DepartmentalRisksPage';
import { DeptRiskRegisterDetailPage }        from '@staff/pages/grc/DeptRiskRegisterDetailPage';
import { InstitutionalRisksPage }            from '@staff/pages/grc/InstitutionalRisksPage';
import { InstitutionalRiskDetailPage }       from '@staff/pages/grc/InstitutionalRiskDetailPage';
import { RiskTreatmentPlansPage }            from '@staff/pages/grc/RiskTreatmentPlansPage';
import { RTAPDetailPage }                    from '@staff/pages/grc/RTAPDetailPage';
import { RiskPerformanceReportsPage }        from '@staff/pages/grc/RiskPerformanceReportsPage';
import { RiskPerformanceReportDetailPage }   from '@staff/pages/grc/RiskPerformanceReportDetailPage';
import { RiskMeetingsPage }                  from '@staff/pages/grc/RiskMeetingsPage';
// Quality Assurance pages
import { QualityAuditorsPage }               from '@staff/pages/grc/QualityAuditorsPage';
import { QualityAuditorDetailPage }          from '@staff/pages/grc/QualityAuditorDetailPage';
import { QATrainingPage }                    from '@staff/pages/grc/QATrainingPage';
import { QATrainingDetailPage }              from '@staff/pages/grc/QATrainingDetailPage';
import { QMSProgramsPage }                   from '@staff/pages/grc/QMSProgramsPage';
import { QMSProgramDetailPage }              from '@staff/pages/grc/QMSProgramDetailPage';
import { QMSPlansPage }                      from '@staff/pages/grc/QMSPlansPage';
import { QMSPlanDetailPage }                 from '@staff/pages/grc/QMSPlanDetailPage';
import { QMSChecklistsPage }                 from '@staff/pages/grc/QMSChecklistsPage';
import { QMSAuditReportsPage }               from '@staff/pages/grc/QMSAuditReportsPage';
import { QMSAuditReportDetailPage }          from '@staff/pages/grc/QMSAuditReportDetailPage';
import { NonConformancesPage }               from '@staff/pages/grc/NonConformancesPage';
import { NonConformanceDetailPage }          from '@staff/pages/grc/NonConformanceDetailPage';
```

---

### 1.3 Navigation / Sidebar Integration

**File:** `frontend/packages/shared/src/config/servicesConfig.ts`

**Action:** Extend the `grc.items` array. The current Risk Management group has 4 items and Quality Assurance has 2. Add the missing entries.

#### Add to Risk Management group:

```ts
{ title: 'Risk Assessment Sheets', url: '/service/grc/risk-assessment-sheets', icon: ClipboardCheck, group: 'Risk Management' },
{ title: 'Performance Reports',    url: '/service/grc/risk-performance-reports', icon: BarChart3, group: 'Risk Management' },  // BarChart3 already imported
{ title: 'Risk Meetings',          url: '/service/grc/risk-meetings', icon: Users2, group: 'Risk Management' },
```

#### Add to Quality Assurance group:

```ts
{ title: 'QA Training',            url: '/service/grc/qa-training', icon: GraduationCap, group: 'Quality Assurance' },
{ title: 'QMS Programs',           url: '/service/grc/qms-programs', icon: ListChecks, group: 'Quality Assurance' },
{ title: 'QMS Audit Plans',        url: '/service/grc/qms-plans', icon: CalendarCheck, group: 'Quality Assurance' },
{ title: 'QMS Checklists',         url: '/service/grc/qms-checklists', icon: CheckSquare, group: 'Quality Assurance' },
{ title: 'Non-Conformances',       url: '/service/grc/non-conformances', icon: AlertOctagon, group: 'Quality Assurance' },
```

#### Update existing Quality Assurance item:

```ts
// Change title of quality-audits item (it now points to QMS Audit Reports):
{ title: 'QMS Audit Reports', url: '/service/grc/quality-audits', icon: FileCheck, group: 'Quality Assurance' },
```

#### Add required icon imports to the existing lucide-react import in servicesConfig.ts:

> **Note:** `GraduationCap`, `ListChecks`, `CheckSquare`, `FileCheck`, `BarChart3`, and `ClipboardList` are **already imported** — do NOT duplicate them.

```ts
// Add ONLY these new icons to the existing lucide-react import block:
ClipboardCheck, Users2, CalendarCheck, AlertOctagon,
```

#### Final complete GRC sidebar order (Risk Management + Quality Assurance groups):

```ts
// ── RISK MANAGEMENT ──
{ title: 'Risk Champions',         url: '/service/grc/risk-champions',           icon: Shield,          group: 'Risk Management' },
{ title: 'Risk Assessment Sheets', url: '/service/grc/risk-assessment-sheets',   icon: ClipboardCheck,  group: 'Risk Management' },
{ title: 'Departmental Risks',     url: '/service/grc/departmental-risks',       icon: Building2,       group: 'Risk Management' },
{ title: 'Institutional Risks',    url: '/service/grc/institutional-risks',      icon: ShieldCheck,     group: 'Risk Management' },
{ title: 'Risk Treatment Plans',   url: '/service/grc/risk-treatment',           icon: ClipboardList,   group: 'Risk Management' },
{ title: 'Performance Reports',    url: '/service/grc/risk-performance-reports', icon: BarChart3,       group: 'Risk Management' },
{ title: 'Risk Meetings',          url: '/service/grc/risk-meetings',            icon: Users2,          group: 'Risk Management' },

// ── QUALITY ASSURANCE ──
{ title: 'Quality Auditors',       url: '/service/grc/quality-auditors',         icon: Users,           group: 'Quality Assurance' },
{ title: 'QA Training',            url: '/service/grc/qa-training',              icon: GraduationCap,   group: 'Quality Assurance' },
{ title: 'QMS Programs',           url: '/service/grc/qms-programs',             icon: ListChecks,      group: 'Quality Assurance' },
{ title: 'QMS Audit Plans',        url: '/service/grc/qms-plans',                icon: CalendarCheck,   group: 'Quality Assurance' },
{ title: 'QMS Checklists',         url: '/service/grc/qms-checklists',           icon: CheckSquare,     group: 'Quality Assurance' },
{ title: 'QMS Audit Reports',      url: '/service/grc/quality-audits',           icon: FileCheck,       group: 'Quality Assurance' },
{ title: 'Non-Conformances',       url: '/service/grc/non-conformances',         icon: AlertOctagon,    group: 'Quality Assurance' },
```

---

## 2. Page Structure Definition

### 2.1 Risk Management Pages

| Page | Route | Type | Workflow |
|------|-------|------|----------|
| `RiskChampionsPage` | `/service/grc/risk-champions` | List | No |
| `RiskChampionDetailPage` | `/service/grc/risk-champions/:championId` | Detail | Yes — RC Appointment workflow |
| `RiskAssessmentSheetsPage` | `/service/grc/risk-assessment-sheets` | List | No |
| `RiskAssessmentSheetDetailPage` | `/service/grc/risk-assessment-sheets/:sheetId` | Detail | No — uses status-transition action endpoints (Gap 15/28) |
| `DepartmentalRisksPage` | `/service/grc/departmental-risks` | List | No |
| `DeptRiskRegisterDetailPage` | `/service/grc/departmental-risks/:registerId` | Detail | Yes — DRR Approval workflow |
| `InstitutionalRisksPage` | `/service/grc/institutional-risks` | List | No |
| `InstitutionalRiskDetailPage` | `/service/grc/institutional-risks/:registerId` | Detail | Yes — IRR Governance workflow |
| `RiskTreatmentPlansPage` (RTAP list) | `/service/grc/risk-treatment` | List | No |
| `RTAPDetailPage` | `/service/grc/risk-treatment/:rtapId` | Detail | Yes — RTAP Governance workflow |
| `RiskPerformanceReportsPage` | `/service/grc/risk-performance-reports` | List | No |
| `RiskPerformanceReportDetailPage` | `/service/grc/risk-performance-reports/:reportId` | Detail | Yes — QPR Governance workflow |
| `RiskMeetingsPage` | `/service/grc/risk-meetings` | List | No |

### 2.2 Quality Assurance Pages

| Page | Route | Type | Workflow |
|------|-------|------|----------|
| `QualityAuditorsPage` | `/service/grc/quality-auditors` | List | No |
| `QualityAuditorDetailPage` | `/service/grc/quality-auditors/:auditorId` | Detail | Yes — QA Appointment workflow |
| `QATrainingPage` | `/service/grc/qa-training` | List | No |
| `QATrainingDetailPage` | `/service/grc/qa-training/:sessionId` | Detail | No (hosts QATrainingAttendeesSection) |
| `QMSProgramsPage` | `/service/grc/qms-programs` | List | No |
| `QMSProgramDetailPage` | `/service/grc/qms-programs/:programId` | Detail | Yes — QMS Program Approval workflow |
| `QMSPlansPage` | `/service/grc/qms-plans` | List | No |
| `QMSPlanDetailPage` | `/service/grc/qms-plans/:planId` | Detail | Yes — QMS Audit Plan Approval workflow |
| `QMSChecklistsPage` | `/service/grc/qms-checklists` | List | No |
| `QMSAuditReportsPage` | `/service/grc/quality-audits` | List | No |
| `QMSAuditReportDetailPage` | `/service/grc/quality-audits/:reportId` | Detail | No — uses sign + governance action endpoints (Gaps 12/25/26) |
| `NonConformancesPage` | `/service/grc/non-conformances` | List | No |
| `NonConformanceDetailPage` | `/service/grc/non-conformances/:ncId` | Detail | No — hosts dispute/resolve actions (Gap 4) + overdue tracking (Gap 5) |

### 2.3 Non-Workflow Page Behavior

Entities without a Detail Page (all "No workflow" + no child sections + no action endpoints) use **view/edit dialogs directly from the list page** — no navigation away. This follows the same pattern as `AuditFindingsPage.tsx`:

| Entity | Has Detail Page? | View/Edit Pattern |
|--------|------------------|-------------------|
| Risk Meeting | No | `<RiskMeetingViewDialog>` opened on row click |
| QMS Checklist | No | `<QMSChecklistViewDialog>` opened on row click |

> **Detail pages exist for entities with workflow, status-transition actions, OR child tables:**
> - `RiskAssessmentSheetDetailPage` → hosts status transition buttons (submit/endorse/approve/return-for-rework) per Gap 15/28
> - `QATrainingDetailPage` → hosts `QATrainingAttendeesSection` + approve/reject/notify buttons per Gap 23
> - `QMSAuditReportDetailPage` → hosts sign buttons + governance action chain per Gaps 12/25/26
> - `NonConformanceDetailPage` → hosts dispute/resolve-dispute actions per Gap 4 + overdue badge per Gap 5

---

## 3. API Integration Layer

### 3.1 API Path Constants

**File:** `frontend/apps/staff-portal/src/services/grcService.ts`

Add to `API_PATHS` constant:

```ts
// ── Risk Management ──────────────────────────────────────────────────────────
riskChampions:               'risk/champions/',
rcAppointments:              'risk/champions/appointments/',       // detail by appointment UUID
riskAssessmentSheets:        'risk/assessments/',
deptRiskRegisters:           'risk/dept-registers/',
deptRegisterEntries:         'risk/dept-registers/entries/',       // detail by entry UUID
institutionalRiskRegisters:  'risk/institutional-registers/',
irrEntries:                  'risk/institutional-registers/entries/',
irrActivityReports:          'risk/institutional-registers/activity-reports/',
rtap:                        'risk/rtap/',
rtapItems:                   'risk/rtap-items/',
rtapQuarterlyUpdates:        'risk/rtap-items/quarterly-updates/',
quarterlyPerfReports:        'risk/quarterly-reports/',
riskMeetings:                'risk/meetings/',
meetingAttendance:           'risk/meetings/attendance/',
riskDashboard:               'risk/dashboard/',
riskDashboardComparative:    'risk/dashboard/comparative-analysis/',

// ── Quality Assurance ────────────────────────────────────────────────────────
qualityAuditors:             'risk/quality-auditors/',
qaAppointments:              'risk/quality-auditors/appointments/',
qaTrainingSessions:          'risk/qa-training/',
qaTrainingAttendees:         'risk/qa-training/attendees/',
qmsPrograms:                 'risk/qms-programs/',
qmsPlans:                    'risk/qms-plans/',
qmsTeamAssignments:          'risk/qms-plans/team/',
qmsMeetings:                 'risk/qms-plans/audit-meetings/',     // nested under plan
qmsTimetable:                'risk/qms-plans/timetable/',          // nested under plan
qmsChecklists:               'risk/qms-checklists/',
qmsAuditReports:             'risk/qms-reports/',
nonConformances:             'risk/non-conformances/',
ncMonthlySummary:            'risk/non-conformances/monthly-summary/',   // Gap 5

// ── Gap-Resolved Action Endpoints (Phase 1–4 backend fixes) ──────────────────
// Gap 4 — NC Dispute / Resolve
// Built inline: `risk/non-conformances/${id}/dispute/`
// Built inline: `risk/non-conformances/${id}/resolve-dispute/`

// Gap 7 — RTAP Send Reminder
// Built inline: `risk/rtap/${id}/send-reminder/`

// Gap 8 — IRR Workshop Notifications
// Built inline: `risk/institutional-registers/${id}/notify-directors/`
// Built inline: `risk/institutional-registers/${id}/notify-rcs/`

// Gap 12/15/28 — RAS Status Transition Actions
// Built inline: `risk/assessments/${id}/submit/`
// Built inline: `risk/assessments/${id}/endorse/`
// Built inline: `risk/assessments/${id}/submit-to-rmqam/`
// Built inline: `risk/assessments/${id}/approve/`
// Built inline: `risk/assessments/${id}/return-for-rework/`

// Gap 12/25/26 — QMS Audit Report Governance Actions
// Built inline: `risk/qms-reports/${id}/submit-to-rmqam/`
// Built inline: `risk/qms-reports/${id}/return-for-revision/`
// Built inline: `risk/qms-reports/${id}/present-at-mrm/`
// Built inline: `risk/qms-reports/${id}/receive-directives/`
// Built inline: `risk/qms-reports/${id}/submit-to-audit-committee/`
// Built inline: `risk/qms-reports/${id}/audit-committee-review/`
// Built inline: `risk/qms-reports/${id}/adopt-by-commission/`

// Gap 23 — QA Training Approve / Reject / Notify
// Built inline: `risk/qa-training/${id}/approve/`
// Built inline: `risk/qa-training/${id}/reject/`
// Built inline: `risk/qa-training/${id}/notify-attendees/`

// Gap 24 — IRR / RTAP Distribution
// Built inline: `risk/institutional-registers/${id}/distribute/`
// Built inline: `risk/rtap/${id}/distribute/`
```

> **Nested endpoint pattern:** `API_PATHS` constants only define the **flat detail-by-UUID path** for nested resources (e.g., `rcAppointments: 'risk/champions/appointments/'`). The **nested list** URL is built inline in service functions using the parent ID — exactly like `fetchEngagementWorkingPapers(engagementId)` in the existing `grcService.ts`:
> ```ts
> // nested list  → built inline:  `risk/champions/${championId}/appointments/`
> // nested detail → uses constant: `risk/champions/appointments/${appointmentId}/`
> ```
> Apply this same two-path pattern to every nested resource.

### 3.2 Service Functions

**File:** `frontend/apps/staff-portal/src/services/grcService.ts`

Implement all CRUD + workflow functions using the same patterns as existing audit functions. For each entity, implement:

- `fetch<Entity>s(params: GRCListParams)` → `AuditCollectionResult<Entity>` — uses `fetchCollection<T>`
- `fetch<Entity>(id: string)` → `Entity` — uses `unwrap<T>`
- `create<Entity>(data: EntityFormData)` → `Entity` — uses `unwrap<T>`
- `update<Entity>(id: string, data: Partial<EntityFormData>)` → `Entity`
- `delete<Entity>(id: string)` → `void`
- For workflow entities: `start<Entity>Workflow(id)`, `get<Entity>WorkflowStatus(id)`, `get<Entity>WorkflowHistory(id)`, `advance<Entity>Workflow(id, data)`, `cancel<Entity>Workflow(id)`, `recall<Entity>Workflow(id)`

**Endpoint pattern reference:**

```ts
// List
GET  /api/v1/risk/champions/                           → list Risk Champions
GET  /api/v1/risk/champions/:id/appointments/          → list RC Appointments for a champion
GET  /api/v1/risk/assessments/                         → list Risk Assessment Sheets
GET  /api/v1/risk/dept-registers/                      → list Departmental Risk Registers
GET  /api/v1/risk/dept-registers/:id/entries/          → list DRR entries
GET  /api/v1/risk/institutional-registers/             → list IRRs
GET  /api/v1/risk/institutional-registers/:id/entries/ → list IRR entries
GET  /api/v1/risk/institutional-registers/:id/activity-reports/ → activity reports
GET  /api/v1/risk/rtap/                                → list RTAPs
GET  /api/v1/risk/rtap-items/                          → list RTAP items
GET  /api/v1/risk/rtap-items/:id/quarterly-updates/    → quarterly updates for an item
GET  /api/v1/risk/quarterly-reports/                   → list QPRs
GET  /api/v1/risk/meetings/                            → list Risk Meetings
GET  /api/v1/risk/meetings/:id/attendance/             → attendance for a meeting
GET  /api/v1/risk/quality-auditors/                    → list QA records
GET  /api/v1/risk/quality-auditors/:id/appointments/   → list QA Appointments
GET  /api/v1/risk/qa-training/                         → list QA Training Sessions
GET  /api/v1/risk/qa-training/:id/attendees/           → attendees for a session
GET  /api/v1/risk/qms-programs/                        → list QMS Programs
GET  /api/v1/risk/qms-plans/                           → list QMS Audit Plans
GET  /api/v1/risk/qms-plans/:id/team/                  → team assignments
GET  /api/v1/risk/qms-plans/:id/audit-meetings/        → audit meetings for a plan
GET  /api/v1/risk/qms-plans/:id/timetable/             → timetable entries for a plan
GET  /api/v1/risk/qms-checklists/                      → list QMS Checklists
GET  /api/v1/risk/qms-reports/                         → list QMS Audit Reports
POST /api/v1/risk/qms-reports/:id/sign-tl/             → TL signs the report
POST /api/v1/risk/qms-reports/:id/sign-auditee/        → Auditee signs the report
GET  /api/v1/risk/non-conformances/                    → list Non-Conformances
GET  /api/v1/risk/dashboard/                           → Risk dashboard summary
GET  /api/v1/risk/dashboard/comparative-analysis/      → comparative analysis data

// Workflow (pattern, same for all workflow entities):
POST /api/v1/risk/<entity>/:id/workflow/start/
GET  /api/v1/risk/<entity>/:id/workflow/status/
GET  /api/v1/risk/<entity>/:id/workflow/history/
POST /api/v1/risk/<entity>/:id/workflow/advance/
POST /api/v1/risk/<entity>/:id/workflow/cancel/
POST /api/v1/risk/<entity>/:id/workflow/recall/
```

#### 3.2.1 Nested-List Service Function Pattern

Mirror `fetchEngagementWorkingPapers` from the existing `grcService.ts` for ALL parent→child list calls:

```ts
// ── RC Appointments (nested under champion) ──────────────────────────────────
export async function fetchRCAppointments(
  championId: string, params?: GRCListParams
): Promise<AuditCollectionResult<RCAppointment>> {
  const response = await grcClient.get(
    `risk/champions/${championId}/appointments/`,
    { params: { page: params?.page ?? 1, page_size: params?.page_size ?? 20 } }
  );
  return mapPaginatedResponse<RCAppointment>(response, params?.page ?? 1, params?.page_size ?? 20);
}
export async function fetchRCAppointment(id: string): Promise<RCAppointment> {
  const response = await grcClient.get(`${ensureTrailingSlash(API_PATHS.rcAppointments)}${id}/`);
  return unwrap(response);
}
export async function createRCAppointment(
  championId: string, data: RCAppointmentFormData
): Promise<RCAppointment> {
  const response = await grcClient.post(`risk/champions/${championId}/appointments/`, data);
  return unwrap(response);
}
```

Apply the identical pattern to every nested resource:

| Parent | Child | Nested list URL pattern |
|--------|-------|------------------------|
| `champions/:id` | RC Appointments | `risk/champions/${championId}/appointments/` |
| `quality-auditors/:id` | QA Appointments | `risk/quality-auditors/${auditorId}/appointments/` |
| `dept-registers/:id` | DRR Entries | `risk/dept-registers/${registerId}/entries/` |
| `institutional-registers/:id` | IRR Entries | `risk/institutional-registers/${registerId}/entries/` |
| `institutional-registers/:id` | Activity Reports | `risk/institutional-registers/${registerId}/activity-reports/` |
| `rtap-items/:id` | Quarterly Updates | `risk/rtap-items/${itemId}/quarterly-updates/` |
| `meetings/:id` | Attendance | `risk/meetings/${meetingId}/attendance/` |
| `qa-training/:id` | Training Attendees | `risk/qa-training/${sessionId}/attendees/` |
| `qms-plans/:id` | Team Assignments | `risk/qms-plans/${planId}/team/` |
| `qms-plans/:id` | Audit Meetings | `risk/qms-plans/${planId}/audit-meetings/` |
| `qms-plans/:id` | Timetable Entries | `risk/qms-plans/${planId}/timetable/` |

#### 3.2.2 Special Action Functions (sign + dashboard + gap-resolved actions)

```ts
// QMS Report signing
export async function signQMSReportTL(reportId: string): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/sign-tl/`);
  return unwrap(response);
}
export async function signQMSReportAuditee(reportId: string): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/sign-auditee/`);
  return unwrap(response);
}

// Risk Dashboard
export async function fetchRiskDashboard(): Promise<RiskDashboard> {
  const response = await grcClient.get(API_PATHS.riskDashboard);
  return unwrap(response);
}
export async function fetchRiskDashboardComparativeAnalysis(): Promise<RiskDashboardComparative> {
  const response = await grcClient.get(API_PATHS.riskDashboardComparative);
  return unwrap(response);
}

// ── Gap 4 — NC Dispute Actions ──────────────────────────────────────────────
export async function disputeNonConformance(
  ncId: string, data: { dispute_reason: string }
): Promise<NonConformance> {
  const response = await grcClient.post(`risk/non-conformances/${ncId}/dispute/`, data);
  return unwrap(response);
}
export async function resolveNCDispute(
  ncId: string, data: { resolution_action: string; new_status: NCStatus }
): Promise<NonConformance> {
  const response = await grcClient.post(`risk/non-conformances/${ncId}/resolve-dispute/`, data);
  return unwrap(response);
}

// ── Gap 5 — NC Monthly Summary ──────────────────────────────────────────────
export async function fetchNCMonthlySummary(
  params?: { fiscal_year?: string }
): Promise<any> {
  const response = await grcClient.get(API_PATHS.ncMonthlySummary, { params });
  return unwrap(response);
}

// ── Gap 7 — RTAP Send Reminder to RCs ───────────────────────────────────────
export async function sendRTAPReminder(
  rtapId: string
): Promise<{ notified_count: number }> {
  const response = await grcClient.post(`risk/rtap/${rtapId}/send-reminder/`);
  return unwrap(response);
}

// ── Gap 8 — IRR Workshop Notification Actions ───────────────────────────────
export async function notifyIRRDirectors(irrId: string): Promise<{ notified_count: number }> {
  const response = await grcClient.post(`risk/institutional-registers/${irrId}/notify-directors/`);
  return unwrap(response);
}
export async function notifyIRRRiskChampions(irrId: string): Promise<{ notified_count: number }> {
  const response = await grcClient.post(`risk/institutional-registers/${irrId}/notify-rcs/`);
  return unwrap(response);
}

// ── Gap 15/28 — RAS Status Transition Actions ───────────────────────────────
export async function submitRAS(rasId: string): Promise<RiskAssessmentSheet> {
  const response = await grcClient.post(`risk/assessments/${rasId}/submit/`);
  return unwrap(response);
}
export async function endorseRAS(rasId: string): Promise<RiskAssessmentSheet> {
  const response = await grcClient.post(`risk/assessments/${rasId}/endorse/`);
  return unwrap(response);
}
export async function submitRASToRMQAM(rasId: string): Promise<RiskAssessmentSheet> {
  const response = await grcClient.post(`risk/assessments/${rasId}/submit-to-rmqam/`);
  return unwrap(response);
}
export async function approveRAS(rasId: string): Promise<RiskAssessmentSheet> {
  const response = await grcClient.post(`risk/assessments/${rasId}/approve/`);
  return unwrap(response);
}
export async function returnRASForRework(
  rasId: string, data: { review_comments: string }
): Promise<RiskAssessmentSheet> {
  const response = await grcClient.post(`risk/assessments/${rasId}/return-for-rework/`, data);
  return unwrap(response);
}

// ── Gap 12/25/26 — QMS Audit Report Governance Actions ──────────────────────
export async function submitQMSReportToRMQAM(reportId: string): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/submit-to-rmqam/`);
  return unwrap(response);
}
export async function returnQMSReportForRevision(
  reportId: string, data: { rmqam_review_comments: string }
): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/return-for-revision/`, data);
  return unwrap(response);
}
export async function presentQMSReportAtMRM(reportId: string): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/present-at-mrm/`);
  return unwrap(response);
}
export async function receiveQMSReportDirectives(
  reportId: string, data: { mrm_directives: string }
): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/receive-directives/`, data);
  return unwrap(response);
}
export async function submitQMSReportToAuditCommittee(reportId: string): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/submit-to-audit-committee/`);
  return unwrap(response);
}
export async function auditCommitteeReviewQMSReport(reportId: string): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/audit-committee-review/`);
  return unwrap(response);
}
export async function adoptQMSReportByCommission(reportId: string): Promise<QMSAuditReport> {
  const response = await grcClient.post(`risk/qms-reports/${reportId}/adopt-by-commission/`);
  return unwrap(response);
}

// ── Gap 23 — QA Training Approval Actions ───────────────────────────────────
export async function approveQATraining(sessionId: string): Promise<QATrainingSession> {
  const response = await grcClient.post(`risk/qa-training/${sessionId}/approve/`);
  return unwrap(response);
}
export async function rejectQATraining(
  sessionId: string, data: { rejection_notes: string }
): Promise<QATrainingSession> {
  const response = await grcClient.post(`risk/qa-training/${sessionId}/reject/`, data);
  return unwrap(response);
}
export async function notifyQATrainingAttendees(sessionId: string): Promise<{ notified_count: number }> {
  const response = await grcClient.post(`risk/qa-training/${sessionId}/notify-attendees/`);
  return unwrap(response);
}

// ── Gap 24 — IRR / RTAP Distribution ────────────────────────────────────────
export async function distributeIRR(irrId: string): Promise<InstitutionalRiskRegister> {
  const response = await grcClient.post(`risk/institutional-registers/${irrId}/distribute/`);
  return unwrap(response);
}
export async function distributeRTAP(rtapId: string): Promise<RTAP> {
  const response = await grcClient.post(`risk/rtap/${rtapId}/distribute/`);
  return unwrap(response);
}
```

**File:** `frontend/apps/staff-portal/src/types/grc.ts`

Append the following type blocks to the end of the file:

#### Status types:

```ts
// ── Risk Management — Status Types ──────────────────────────────────────────

export type RCStatus =
  | 'pending' | 'nominated' | 'under_review' | 'letter_drafted'
  | 'letter_reviewed' | 'appointed' | 'active' | 'inactive';

export type RASStatus =
  | 'draft' | 'submitted_to_head' | 'head_endorsed'
  | 'submitted_to_rmqam' | 'approved' | 'returned_for_rework';

export type DRRStatus =
  | 'in_progress' | 'submitted_to_rmqam' | 'approved' | 'returned_for_rework';

export type IRRStatus =
  | 'draft' | 'workshop_held' | 'compiled' | 'under_rmqam_review'
  | 'submitted_to_dg' | 'submitted_to_management' | 'management_reviewed'
  | 'submitted_to_committee' | 'committee_reviewed' | 'approved' | 'returned';

export type RTAPStatus =
  | 'draft' | 'active' | 'under_review'
  | 'submitted_to_management' | 'management_reviewed'
  | 'submitted_to_committee' | 'committee_reviewed'
  | 'submitted_to_commission' | 'approved';

export type RTAPItemStatus = 'not_started' | 'in_progress' | 'completed' | 'returned_for_rework';

export type QPRStatus =
  | 'draft' | 'submitted_to_management' | 'management_reviewed'
  | 'submitted_to_committee' | 'committee_reviewed'
  | 'committee_directives_actioned' | 'submitted_to_commission';

export type QMSProgramStatus = 'draft' | 'under_rmqam_review' | 'approved' | 'returned_for_rework';
export type QMSPlanStatus    = 'draft' | 'under_rmqam_review' | 'approved' | 'returned_for_rework';
export type QMSReportStatus  = 'draft' | 'tl_signed' | 'auditee_acknowledged' | 'finalised' | 'submitted_to_rmqam' | 'returned_for_revision' | 'presented_at_mrm' | 'directives_received' | 'submitted_to_audit_committee' | 'audit_committee_reviewed' | 'adopted_by_commission';
export type NCStatus         = 'raised' | 'acknowledged' | 'in_progress' | 'closed' | 'disputed' | 'withdrawn';
export type QAStatus         = 'pending' | 'nominated' | 'training_scheduled' | 'exam_pending' | 'passed' | 'failed' | 'appointed' | 'active' | 'inactive';
```

#### Entity interfaces:

```ts
// ── Risk Champion ────────────────────────────────────────────────────────────
export interface RiskChampion {
  id: string;
  nominee_user_id: string;
  directorate_unit_zone: string;       // display name
  directorate_unit_zone_id: string;
  status: RCStatus;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RCAppointment {
  id: string;
  risk_champion: string;               // parent UUID
  appointment_letter_doc_uuid?: string;
  effective_date?: string;
  term_end_date?: string;
  status: RCStatus;
  workflow_plan_id?: string;
  workflow_stage?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskChampionFormData {
  nominee_user_id: string;
  directorate_unit_zone_id: string;
  notes?: string;
}

// ── Risk Assessment Sheet ────────────────────────────────────────────────────
export interface RiskAssessmentSheet {
  id: string;
  reference_number: string;
  risk_description: string;
  risk_category: string;
  risk_owner_id: string;
  directorate_unit_zone: string;
  directorate_unit_zone_id: string;
  likelihood_rating: number;
  impact_rating: number;
  inherent_risk_level: string;
  existing_controls: string;
  residual_risk_level: string;
  proposed_controls: string;
  status: RASStatus;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskAssessmentSheetFormData {
  risk_description: string;
  risk_category: string;
  risk_owner_id: string;
  directorate_unit_zone_id: string;
  likelihood_rating: number;
  impact_rating: number;
  existing_controls: string;
  proposed_controls: string;
}

// ── Departmental Risk Register ────────────────────────────────────────────────
export interface DeptRiskRegister {
  id: string;
  reference_number: string;
  directorate_unit_zone: string;
  directorate_unit_zone_id: string;
  reporting_period: string;
  status: DRRStatus;
  workflow_plan_id?: string;
  workflow_stage?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeptRegisterEntry {
  id: string;
  dept_risk_register: string;
  risk_assessment_sheet: string;
  risk_assessment_sheet_id: string;
  notes?: string;
  created_at: string;
}

export interface DeptRiskRegisterFormData {
  directorate_unit_zone_id: string;
  reporting_period: string;
  notes?: string;
}

// ── Institutional Risk Register ──────────────────────────────────────────────
export interface InstitutionalRiskRegister {
  id: string;
  reference_number: string;
  reporting_period: string;
  status: IRRStatus;
  workflow_plan_id?: string;
  workflow_stage?: string;
  // Gap 8 — IRR Workshop fields (Phase 4 backend fix)
  workshop_date?: string;
  workshop_venue?: string;
  directors_notified_at?: string;
  rcs_notified_at?: string;
  // Gap 24 — Distribution fields (Phase 4 backend fix)
  distributed_to_directorates_at?: string;
  distribution_reference?: string;
  committee_meeting_date?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface IRREntry {
  id: string;
  institutional_risk_register: string;
  risk_description: string;
  risk_category: string;
  likelihood_rating: number;
  impact_rating: number;
  inherent_risk_level: string;
  proposed_controls: string;
  directorate_unit_zone: string;
  created_at: string;
}

// ── Risk Treatment Action Plan ────────────────────────────────────────────────
export interface RTAP {
  id: string;
  reference_number: string;
  institutional_risk_register: string;
  institutional_risk_register_id: string;
  period: string;
  status: RTAPStatus;
  workflow_plan_id?: string;
  workflow_stage?: string;
  // Gap 24 — Distribution fields (Phase 4 backend fix)
  distributed_to_directorates_at?: string;
  distribution_reference?: string;
  committee_meeting_date?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RTAPItem {
  id: string;
  rtap: string;
  irr_entry: string;
  irr_entry_id: string;
  control_description: string;
  responsible_officer_id: string;
  target_date: string;
  implementation_status: RTAPItemStatus;
  evidence?: string;
  completion_percentage: number;
  // Gap 22 — RTAP Item Return-for-Rework (Phase 4 backend fix)
  review_comments?: string;
  returned_at?: string;
  resubmitted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface RTAPFormData {
  institutional_risk_register_id: string;
  period: string;
}

// ── Quarterly Performance Report ─────────────────────────────────────────────
export interface QuarterlyPerformanceReport {
  id: string;
  reference_number: string;
  quarter: string;
  fiscal_year: string;
  implementation_rate_current: number;
  implementation_rate_previous: number;
  variance: number;
  status: QPRStatus;
  workflow_plan_id?: string;
  workflow_stage?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QPRFormData {
  quarter: string;
  fiscal_year: string;
  notes?: string;
}

// ── Risk Meeting ─────────────────────────────────────────────────────────────
export interface RiskMeeting {
  id: string;
  title: string;
  meeting_type: string;                 // includes 'management_review' (Gap 6 Phase 3 fix)
  scheduled_date: string;
  venue: string;
  convened_by_id: string;
  directorate_unit_zone?: string;
  dept_register?: string;               // Gap 6 — optional FK to DepartmentalRiskRegister
  minutes?: string;
  outcomes?: string[];                  // JSON array
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Quality Auditor ──────────────────────────────────────────────────────────
export interface QualityAuditor {
  id: string;
  nominee_user_id: string;
  directorate_unit_zone: string;
  directorate_unit_zone_id: string;
  certification_date?: string;
  exam_score?: number;
  exam_attempt?: number;
  is_certified?: boolean;
  // Gap 10 — Qualifications/Experience (Phase 3 backend fix)
  qualifications?: string;
  experience_summary?: string;
  status: QAStatus;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QAAppointment {
  id: string;
  quality_auditor: string;
  appointment_letter_doc_uuid?: string;
  effective_date?: string;
  term_end_date?: string;
  status: QAStatus;
  workflow_plan_id?: string;
  workflow_stage?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── QA Training ──────────────────────────────────────────────────────────────
export interface QATrainingSession {
  id: string;
  trainer_name: string;
  training_date: string;
  venue: string;
  approval_status: string;              // 'proposed' | 'approved' | 'rejected' | 'completed' | 'cancelled'
  approved_by?: string;
  approval_date?: string;
  // Gap 23 — Rejection notes + approval flow (Phase 3 backend fix)
  rejection_notes?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── QMS Audit Program ────────────────────────────────────────────────────────
export interface QMSAuditProgram {
  id: string;
  reference_number: string;
  audit_year: string;
  scope: string;
  objectives: string;
  status: QMSProgramStatus;
  workflow_plan_id?: string;
  workflow_stage?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QMSAuditProgramFormData {
  audit_year: string;
  scope: string;
  objectives: string;
}

// ── QMS Audit Plan ───────────────────────────────────────────────────────────
export interface QMSAuditPlan {
  id: string;
  reference_number: string;
  qms_program: string;
  qms_program_id: string;
  audit_start_date: string;
  audit_end_date: string;
  team_leader_id: string;
  status: QMSPlanStatus;
  workflow_plan_id?: string;
  workflow_stage?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── QMS Audit Checklist ──────────────────────────────────────────────────────
export interface QMSAuditChecklist {
  id: string;
  qms_plan: string;
  qms_plan_id: string;
  assigned_qa_id: string;
  assigned_process: string;
  iso_clauses: string;
  checklist_items: ChecklistItem[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChecklistItem {
  id: string;
  description: string;
  conformity_status: string;
  evidence_reference?: string;
}

// ── QMS Audit Report ─────────────────────────────────────────────────────────
export interface QMSAuditReport {
  id: string;
  reference_number: string;
  qms_plan: string;
  qms_plan_id: string;
  auditee_directorate: string;
  audit_date: string;
  qa_id: string;
  tl_id?: string;
  tl_signed_at?: string;
  auditee_signed_at?: string;
  status: QMSReportStatus;
  // Gap 12/25/26 — Extended governance fields (Phase 1 backend fix)
  mrm_directives?: string;
  mrm_directives_communicated_at?: string;
  rmqam_review_comments?: string;
  returned_for_revision_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Non-Conformance ──────────────────────────────────────────────────────────
export interface NonConformance {
  id: string;
  reference_number: string;
  audit_report: string;
  audit_report_id: string;
  nc_description: string;
  nc_type?: string;                     // FK to NonConformanceType (major_nc, minor_nc, observation, area_for_improvement)
  iso_clause_violated: string;
  evidence: string;
  responsible_party_id: string;
  proposed_corrective_action: string;
  target_closure_date: string;
  due_date?: string;
  closure_status: NCStatus;
  // Gap 4 — NC Dispute fields (Phase 1 backend fix)
  dispute_reason?: string;
  disputed_at?: string;
  disputed_by?: string;
  // Gap 5 — NC Monthly Monitoring (Phase 3 backend fix)
  last_reviewed_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Missing FormData interfaces ───────────────────────────────────────────────
export interface RCAppointmentFormData {
  effective_date: string;
  term_end_date: string;
  appointment_letter_doc_uuid?: string;
}

export interface QAAppointmentFormData {
  effective_date: string;
  term_end_date: string;
  certification_date?: string;
  exam_score?: number;
  appointment_letter_doc_uuid?: string;
}

export interface DeptRegisterEntryFormData {
  risk_assessment_sheet_id: string;   // must be from approved RAS list
  notes?: string;
}

export interface IRREntryFormData {
  risk_description: string;
  risk_category: string;
  likelihood_rating: number;
  impact_rating: number;
  existing_controls: string;
  proposed_controls: string;
  directorate_unit_zone_id: string;
}

export interface RTAPItemFormData {
  irr_entry_id: string;
  control_description: string;
  responsible_officer_id: string;
  target_date: string;
}

export interface RiskMeetingFormData {
  title: string;
  meeting_type: string;
  scheduled_date: string;
  venue: string;
  directorate_unit_zone_id?: string;
  notes?: string;
}

export interface QATrainingSessionFormData {
  trainer_name: string;
  training_date: string;
  venue: string;
  notes?: string;
}

export interface QMSAuditPlanFormData {
  qms_program_id: string;
  audit_start_date: string;
  audit_end_date: string;
  team_leader_id: string;
}

export interface QMSAuditChecklistFormData {
  qms_plan_id: string;
  assigned_qa_id: string;
  assigned_process: string;
  iso_clauses: string;
  checklist_items: Omit<ChecklistItem, 'id'>[];
}

export interface QMSAuditReportFormData {
  qms_plan_id: string;
  auditee_directorate: string;
  audit_date: string;
  qa_id: string;
}

export interface NonConformanceFormData {
  audit_report_id: string;
  nc_description: string;
  iso_clause_violated: string;
  evidence: string;
  responsible_party_id: string;
  proposed_corrective_action: string;
  target_closure_date: string;
}

// ── Support/nested entity interfaces ─────────────────────────────────────────
export interface IRRActivityReport {
  id: string;
  institutional_risk_register: string;
  reporting_period: string;
  implementation_rate: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface RTAPQuarterlyUpdate {
  id: string;
  rtap_item: string;
  quarter: string;
  progress_update: string;
  completion_percentage: number;
  created_at: string;
  updated_at: string;
}

export interface MeetingAttendance {
  id: string;
  meeting: string;
  attendee_id: string;
  attended: boolean;
  created_at: string;
}

export interface QATrainingAttendee {
  id: string;
  training_session: string;
  attendee_id: string;
  attendance_confirmed: boolean;
  // Gap 3 — Per-session exam tracking (Phase 3 backend fix)
  exam_score?: number;
  exam_attempt_number?: number;
  passed?: boolean;
  created_at: string;
}

export interface QMSTeamAssignment {
  id: string;
  qms_plan: string;
  assigned_qa_id: string;
  role: string;
  created_at: string;
}

export interface QMSAuditMeeting {
  id: string;
  qms_plan: string;
  meeting_type: string;       // e.g. 'opening' | 'closing'
  scheduled_date: string;
  venue: string;
  notes?: string;
  created_at: string;
}

export interface QMSTimetableEntry {
  id: string;
  qms_plan: string;
  process: string;
  scheduled_date: string;
  assigned_qa_id: string;
  created_at: string;
}

// ── Dashboard response types ──────────────────────────────────────────────────
export interface RiskDashboard {
  total_risk_champions: number;
  active_risk_champions: number;
  total_risks: number;
  open_risks: number;
  rtap_completion_rate: number;
  qpr_summary: {
    current_quarter: string;
    implementation_rate: number;
  };
  qa_summary: {
    total_quality_auditors: number;
    active_quality_auditors: number;
    pending_nc_closures: number;
  };
}

export interface RiskDashboardComparative {
  quarters: string[];
  implementation_rates: number[];
  risk_counts: number[];
}
```

#### Update `GRCPermissions` interface in `grc.ts`:

```ts
// Append to GRCPermissions interface:
// Risk Management
'grc:risk_champion:manage':                  boolean;
'grc:risk_champion:view':                    boolean;
'grc:risk_assessment:conduct':               boolean;   // RC drafts/edits RAS
'grc:risk_assessment:review':                boolean;   // RMQAM reviews RAS
'grc:dept_risk_register:manage':             boolean;
'grc:dept_risk_register:approve':            boolean;
'grc:institutional_risk_register:manage':    boolean;
'grc:institutional_risk_register:approve':   boolean;
'grc:rtap:manage':                           boolean;
'grc:rtap:approve':                          boolean;
'grc:rtap:respond':                          boolean;   // RC updates RTAP item status
'grc:quarterly_risk_report:manage':          boolean;
'grc:quarterly_risk_report:approve':         boolean;
'grc:risk_meeting:manage':                   boolean;
'grc:risk_meeting:view':                     boolean;
'grc:risk_dashboard:view':                   boolean;
// Quality Assurance
'grc:quality_auditor:manage':                boolean;
'grc:qa_training:manage':                    boolean;
'grc:qms_audit_program:manage':              boolean;
'grc:qms_audit_program:approve':             boolean;
'grc:qms_audit_plan:manage':                 boolean;
'grc:qms_audit_plan:approve':                boolean;
'grc:qms_checklist:manage':                  boolean;
'grc:qms_audit_report:manage':               boolean;
'grc:qms_audit_report:sign':                 boolean;
'grc:non_conformance:manage':                boolean;
'grc:non_conformance:respond':               boolean;  // responsible officer responds/closes NC
```

### 3.4 Data Fetching Structure

- All list hooks accept `(page: number, pageSize: number, filters?: Record<string, unknown>)`.
- All detail hooks accept `(id: string)`.
- All nested/child list hooks (e.g., appointment list for a champion) accept `(parentId: string, page, pageSize)`.
- Use `staleTime: 5 * 60 * 1000` for entity data hooks.
- Use `staleTime: 30_000` for workflow status/history hooks.
- All workflow hooks are per-entity and follow the same shape as `useGRCWorkflows.ts`.

#### Nested hook pattern (follow for all parent→child hooks):

```ts
// hooks/useRCAppointments.ts
export function useRCAppointments(
  championId: string,
  page: number,
  pageSize: number
) {
  return useQuery({
    queryKey: rcAppointmentKeys.list(championId, page, pageSize),
    queryFn: () => fetchRCAppointments(championId, { page, page_size: pageSize }),
    enabled: !!championId,
    staleTime: 5 * 60 * 1000,
  });
}
```

> `enabled: !!parentId` is mandatory — prevents the query running before the parent is loaded.

---

## 4. Core UI Implementation — List Pages

> **Bulk actions / Smart selection:** NOT USED. `GenericListPage` does not support row checkboxes or bulk operations. All actions (view, edit, delete) are per-row only. Do not implement bulk selection.

### 4.1 Query Key Factory (one per entity hook file)

Every entity must export a query key factory **in its hook file** following this exact shape:

```ts
// hooks/useRiskChampions.ts — top of file, before any function
import { serializeFilters } from '@staff/hooks/grcKeys';

export const riskChampionKeys = {
  all:     ['risk-champions'] as const,
  lists:   () => [...riskChampionKeys.all, 'list'] as const,
  list:    (page: number, pageSize: number, filterKey: string) =>
             [...riskChampionKeys.lists(), page, pageSize, filterKey] as const,
  details: () => [...riskChampionKeys.all, 'detail'] as const,
  detail:  (id: string) => [...riskChampionKeys.details(), id] as const,
  workflowStatus:  (id: string) => [...riskChampionKeys.detail(id), 'workflow-status'] as const,
  workflowHistory: (id: string) => [...riskChampionKeys.detail(id), 'workflow-history'] as const,
};
```

Use `serializeFilters(filters)` from `@staff/hooks/grcKeys` as the `filterKey` argument.  
**Required key factories for this module:** `riskChampionKeys`, `rcAppointmentKeys`, `rasKeys`, `deptRiskRegisterKeys`, `irrKeys`, `rtapKeys`, `rtapItemKeys`, `qprKeys`, `riskMeetingKeys`, `qualityAuditorKeys`, `qaAppointmentKeys`, `qaTrainingKeys`, `qmsProgramKeys`, `qmsPlanKeys`, `qmsChecklistKeys`, `qmsAuditReportKeys`, `nonConformanceKeys`.

### 4.2 Data Transform Pattern (one per entity, module scope)

Define `transform<Entity>ForList` at **module scope** (outside component), before `const columns`. Must include all required `ListItem` keys plus `_original`:

```ts
// Required ListItem keys: id, title, status, createdAt, updatedAt, _original
function transformRiskChampionForList(item: RiskChampion) {
  return {
    id:            item.id,
    title:         item.nominee_user_id,             // display name resolved by IAM lookup
    status:        item.status,
    directorate:   item.directorate_unit_zone,
    updatedAt:     new Date(item.updated_at).toLocaleDateString(),
    createdAt:     new Date(item.created_at).toLocaleDateString(),
    _original:     item as any,                      // ← REQUIRED: used by handleEdit/handleDelete
  };
}
```

> `_original` stores the raw API object so `handleEdit(id)` can do `items.find(e => e.id === id)?._original` for prefilling edit forms.

### 4.3 List Page Structure (all list pages follow this pattern)

```tsx
// Style B — canonical pattern from AuditPlansPage.tsx

// ── Module-scope: columns + transform (outside component) ───────────────────
const columns = [ /* see §4.5 */ ];
function transformRiskChampionForList(item: RiskChampion) { /* see §4.2 */ }

// ── Component ───────────────────────────────────────────────────────────────
export function RiskChampionsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Pagination & filter state
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  // Dialog state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingItem, setEditingItem]   = useState<RiskChampion | null>(null);
  const [deletingItem, setDeletingItem] = useState<RiskChampion | null>(null);

  // Permissions
  const { canManageRiskChampions } = useGRCPermissions();

  // Data
  const { data, isLoading, error } = useRiskChampions(page, pageSize, {
    search:  searchQuery  || undefined,
    status:  statusFilter || undefined,
  });
  const deleteMutation = useDeleteRiskChampion();

  // Soft-delete filter + transform
  const items = (data?.results ?? []).filter(item => item.is_active !== false);
  const transformedItems = items.map(transformRiskChampionForList);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleView = (id: string) => {
    navigate(`/service/grc/risk-champions/${id}`);
  };

  const handleEdit = (id: string) => {
    const item = items.find(i => i.id === id);
    if (item) setEditingItem(item);
  };

  const handleDelete = (id: string) => {
    const item = items.find(i => i.id === id);
    if (!item) return;
    // Status guard: prevent deleting active/appointed records
    if (item.status === 'active' || item.status === 'appointed') {
      toast.error('Cannot delete this record', {
        description: `Records with status '${item.status}' cannot be deleted.`,
      });
      return;
    }
    setDeletingItem(item);
  };

  const confirmDelete = () => {
    if (deletingItem) {
      deleteMutation.mutate(deletingItem.id, {
        onSettled: () => setDeletingItem(null),
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Risk Champions</h1>
        {canManageRiskChampions && (
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> Add Risk Champion
          </Button>
        )}
      </div>

      {/* ── Filters row ── */}
      <div className="flex gap-2 flex-wrap">
        <Input
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
          className="h-8 w-[200px]"
        />
        <Select value={statusFilter ?? ''} onValueChange={(v) => { setStatusFilter(v || undefined); setPage(1); }}>
          <SelectTrigger className="h-8 w-[160px]"><SelectValue placeholder="All statuses" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All statuses</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ── Loading banner ── */}
      {isLoading && (
        <div className="mb-4 flex items-center rounded-md border border-dashed bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading...
        </div>
      )}

      {/* ── Error banner ── */}
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Unable to load risk champions</AlertTitle>
          <AlertDescription>{error instanceof Error ? error.message : 'Failed to load data'}</AlertDescription>
        </Alert>
      )}

      {/* ── Table ── */}
      <GenericListPage
        title="Risk Champions"
        items={transformedItems}
        columns={columns}
        userRole={user?.role ?? 'staff'}
        onView={handleView}
        onEdit={canManageRiskChampions ? handleEdit : undefined}
        onDelete={canManageRiskChampions ? handleDelete : undefined}
        showCreateButton={false}
        pagination={data ? {
          page:        data.page,
          page_size:   data.page_size,
          total_pages: Math.max(1, Math.ceil(data.count / pageSize)),
          count:       data.count,
        } : undefined}
        currentPage={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(s) => { setPageSize(s); setPage(1); }}
        itemType="risk champion"
      />

      {/* ── Dialogs ── */}
      {isCreateOpen && (
        <CreateRiskChampionDialog open={isCreateOpen} onClose={() => setIsCreateOpen(false)} />
      )}
      {editingItem && (
        <CreateRiskChampionDialog
          open={!!editingItem}
          onClose={() => setEditingItem(null)}
          defaultValues={editingItem}
        />
      )}

      {/* ── Delete confirmation ── */}
      <AlertDialog open={!!deletingItem} onOpenChange={() => setDeletingItem(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Risk Champion</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this record. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
```

**Rules:**
- Always pass `onEdit={undefined}` / `onDelete={undefined}` (not just omit) when user lacks permission — this hides the action buttons.
- Always reset `page` to `1` on `pageSize` change, search change, or filter change.
- `pageSizeOptions` defaults to `[10, 20, 50, 100]` inside `GenericListPage` — do not redefine.
- Delete `handleDelete` must perform a **status guard** before `setDeletingItem` — toast an error and return early for records that cannot be deleted due to status.

### 4.4 Column Definitions per Entity

Define `const columns = [...]` at **module scope** (outside component), before the transform function. Column shape: `{ key: string; label: string; sortable?: boolean; render?: (item: TransformedItem) => ReactNode }`. First data column should have `className="font-medium"`.

Include these standard columns:

| Entity | Essential Columns |
|--------|-------------------|
| Risk Champions | Nominee Name, Directorate/Unit/Zone, Status, Appointed Date, Updated |
| RC Appointments | Reference, Effective Date, Term End, Status, Updated |
| Risk Assessment Sheets | Reference No., Risk Description (truncated), Category, Risk Owner, Likelihood, Impact, Inherent Risk, Status |
| Dept Risk Registers | Reference No., Directorate/Unit/Zone, Reporting Period, Status, Updated |
| Institutional Risk Registers | Reference No., Reporting Period, Status, Updated |
| RTAP | Reference No., IRR Reference, Period, Status, Updated |
| RTAP Items | Control Description (truncated), Responsible Officer, Target Date, Status, Completion % |
| Quarterly Perf. Reports | Reference No., Quarter, Fiscal Year, Implementation Rate (current), Status |
| Risk Meetings | Title, Type, Scheduled Date, Venue, Status |
| Quality Auditors | Nominee Name, Directorate/Unit/Zone, Cert. Date, Exam Score, Status |
| QA Training Sessions | Trainer, Date, Venue, Approval Status |
| QMS Programs | Reference No., Audit Year, Scope (truncated), Status |
| QMS Audit Plans | Reference No., Program, Start Date, End Date, Team Leader, Status |
| QMS Checklists | Plan Reference, QA, Process, ISO Clauses, Updated |
| QMS Audit Reports | Reference No., Plan, Auditee Directorate, Audit Date, QA, Status |
| Non-Conformances | Reference No., Audit Report, ISO Clause, Responsible Party, Target Date, Closure Status |

### 4.5 Status Badge Color Maps (all entity types)

Render the status column with an inline `<span>` using Tailwind — **not** a shadcn `<Badge variant=...>`. Define a `statusColors` map **per entity** at module scope. Below are the complete color maps for every status type in this module:

```ts
// RCStatus / QAStatus (reuse for both Risk Champion and Quality Auditor)
const rcStatusColors: Record<string, string> = {
  pending:          'bg-gray-100 text-gray-700',
  nominated:        'bg-blue-100 text-blue-800',
  under_review:     'bg-yellow-100 text-yellow-800',
  letter_drafted:   'bg-purple-100 text-purple-800',
  letter_reviewed:  'bg-indigo-100 text-indigo-800',
  training_scheduled: 'bg-cyan-100 text-cyan-800',
  exam_pending:     'bg-orange-100 text-orange-800',
  passed:           'bg-lime-100 text-lime-800',
  failed:           'bg-red-100 text-red-800',
  appointed:        'bg-teal-100 text-teal-800',
  active:           'bg-green-100 text-green-800',
  inactive:         'bg-gray-100 text-gray-500',
};

// RASStatus (Risk Assessment Sheet)
const rasStatusColors: Record<string, string> = {
  draft:                 'bg-gray-100 text-gray-700',
  submitted_to_head:     'bg-blue-100 text-blue-800',
  head_endorsed:         'bg-teal-100 text-teal-800',
  submitted_to_rmqam:    'bg-indigo-100 text-indigo-800',
  approved:              'bg-green-100 text-green-800',
  returned_for_rework:   'bg-red-100 text-red-800',
};

// DRRStatus (Departmental Risk Register)
const drrStatusColors: Record<string, string> = {
  in_progress:           'bg-blue-100 text-blue-800',
  submitted_to_rmqam:    'bg-indigo-100 text-indigo-800',
  approved:              'bg-green-100 text-green-800',
  returned_for_rework:   'bg-red-100 text-red-800',
};

// IRRStatus (Institutional Risk Register)
const irrStatusColors: Record<string, string> = {
  draft:                    'bg-gray-100 text-gray-700',
  workshop_held:            'bg-cyan-100 text-cyan-800',
  compiled:                 'bg-blue-100 text-blue-800',
  under_rmqam_review:       'bg-yellow-100 text-yellow-800',
  submitted_to_dg:          'bg-indigo-100 text-indigo-800',
  submitted_to_management:  'bg-violet-100 text-violet-800',
  management_reviewed:      'bg-purple-100 text-purple-800',
  submitted_to_committee:   'bg-pink-100 text-pink-800',
  committee_reviewed:       'bg-rose-100 text-rose-800',
  approved:                 'bg-green-100 text-green-800',
  returned:                 'bg-red-100 text-red-800',
};

// RTAPStatus (Risk Treatment Action Plan)
const rtapStatusColors: Record<string, string> = {
  draft:                    'bg-gray-100 text-gray-700',
  active:                   'bg-green-100 text-green-800',
  under_review:             'bg-yellow-100 text-yellow-800',
  submitted_to_management:  'bg-indigo-100 text-indigo-800',
  management_reviewed:      'bg-purple-100 text-purple-800',
  submitted_to_committee:   'bg-pink-100 text-pink-800',
  committee_reviewed:       'bg-rose-100 text-rose-800',
  submitted_to_commission:  'bg-orange-100 text-orange-800',
  approved:                 'bg-emerald-100 text-emerald-800',
};

// RTAPItemStatus
const rtapItemStatusColors: Record<string, string> = {
  not_started:          'bg-gray-100 text-gray-700',
  in_progress:          'bg-blue-100 text-blue-800',
  completed:            'bg-green-100 text-green-800',
  returned_for_rework:  'bg-red-100 text-red-800',        // Gap 22
};

// QPRStatus (Quarterly Performance Report)
const qprStatusColors: Record<string, string> = {
  draft:                           'bg-gray-100 text-gray-700',
  submitted_to_management:         'bg-indigo-100 text-indigo-800',
  management_reviewed:             'bg-purple-100 text-purple-800',
  submitted_to_committee:          'bg-pink-100 text-pink-800',
  committee_reviewed:              'bg-rose-100 text-rose-800',
  committee_directives_actioned:   'bg-teal-100 text-teal-800',
  submitted_to_commission:         'bg-orange-100 text-orange-800',
};

// QMSProgramStatus / QMSPlanStatus (same map for both)
const qmsProgramStatusColors: Record<string, string> = {
  draft:               'bg-gray-100 text-gray-700',
  under_rmqam_review:  'bg-yellow-100 text-yellow-800',
  approved:            'bg-green-100 text-green-800',
  returned_for_rework: 'bg-red-100 text-red-800',
};

// QMSReportStatus (QMS Audit Report) — Gap 12/25/26: extended governance chain
const qmsReportStatusColors: Record<string, string> = {
  draft:                        'bg-gray-100 text-gray-700',
  tl_signed:                    'bg-cyan-100 text-cyan-800',
  auditee_acknowledged:         'bg-teal-100 text-teal-800',
  finalised:                    'bg-green-100 text-green-800',
  submitted_to_rmqam:           'bg-indigo-100 text-indigo-800',
  returned_for_revision:        'bg-red-100 text-red-800',
  presented_at_mrm:             'bg-purple-100 text-purple-800',
  directives_received:          'bg-orange-100 text-orange-800',
  submitted_to_audit_committee: 'bg-pink-100 text-pink-800',
  audit_committee_reviewed:     'bg-rose-100 text-rose-800',
  adopted_by_commission:        'bg-emerald-100 text-emerald-800',
};

// NCStatus (Non-Conformance) — Gap 4: added disputed/withdrawn
const ncStatusColors: Record<string, string> = {
  raised:           'bg-red-100 text-red-800',
  acknowledged:     'bg-orange-100 text-orange-800',
  in_progress:      'bg-blue-100 text-blue-800',
  closed:           'bg-green-100 text-green-800',
  disputed:         'bg-amber-100 text-amber-800',
  withdrawn:        'bg-gray-100 text-gray-500',
};
```

Render pattern (identical for every entity):
```tsx
render: (item) => {
  const label = item.status?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${statusColors[item.status] ?? 'bg-gray-100 text-gray-700'}`}>
      {label}
    </span>
  );
},
```

### 4.6 Search and Filters

- Search: `<Input>` bound to `searchQuery` state. Call `setPage(1)` in the `onChange` handler.
- Filter dropdowns: each additional filter (`status`, `directorate_unit_zone`, `period`, `quarter`) is a separate `useState<string | undefined>(undefined)`. Always call `setPage(1)` when a filter changes.
- Use `undefined` (not empty string `''`) to omit a filter from query params — the hook skips `undefined` values.
- Place all filters in `<div className="flex gap-2 flex-wrap">` between the header row and the table.
- Pass all active filters into the hook as: `useRiskChampions(page, pageSize, { search: searchQuery || undefined, status: statusFilter || undefined })`.
- The hook must call `serializeFilters(filters)` from `@staff/hooks/grcKeys` to build the `filterKey` for the query key — this ensures cache is keyed to the exact filter combination.

**Per-entity filter dropdowns to implement:**

| List Page | Filters |
|-----------|---------|
| Risk Champions | `status` |
| Risk Assessment Sheets | `status`, `directorate_unit_zone` |
| Departmental Risk Registers | `status`, `reporting_period` |
| Institutional Risk Registers | `status`, `reporting_period` |
| RTAP | `status`, `period` |
| RTAP Items | `implementation_status` |
| Quarterly Performance Reports | `status`, `quarter`, `fiscal_year` |
| Quality Auditors | `status` |
| QMS Programs | `status`, `audit_year` |
| QMS Audit Plans | `status` |
| QMS Audit Reports | `status` |
| Non-Conformances | `closure_status` |

### 4.7 Navigation to Detail Page

```tsx
const handleView = (id: string) => {
  navigate(`/service/grc/<route-path>/${id}`);
};
```

Only use a modal/dialog for view if §2.3 lists that entity as "dialog only" (no detail page). All workflow-enabled entities **must** navigate to a Detail Page, never open a dialog.

---

## 5. Detail Pages — Workflow-Enabled

All workflow-enabled Detail Pages **strictly follow `NEW_DETAIL_PAGE_REFERENCE.md`**.

### 5.1 Standard Detail Page Layout

```
┌──────────────────────────────────────────────────────────────┐
│  ← (back)   {Entity}: {Reference/Title}    [Action Btn] [Badge]│  ← Header row
│             {subtitle}                                        │
├──────────────────────────────────────────────────────────────┤
│  Card: Entity Details (md:grid-cols-2)                       │
├──────────────────────────────────────────────────────────────┤
│  Card: Review/Governance Info (conditional, lg:grid-cols-4)  │
├──────────────────────────────────────────────────────────────┤
│  Card: Description/Notes (conditional — only if present)     │
├──────────────────────────────────────────────────────────────┤
│  Section: Child Records Table (entries, items, appointments) │
├──────────────────────────────────────────────────────────────┤
│  EmbeddedWorkflowConsole (always at bottom, full width)      │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Detail Page Rules

- **Wrapper:** `<div className="space-y-4 p-4">`
- **Back button:** `variant="ghost" size="icon"`, `ChevronLeft` icon only, `aria-label="Back"`
- **Title:** `text-2xl font-semibold`
- **Status badge:** custom Tailwind classes — NOT shadcn `variant=` props
- **Cards:** one card per logical section — NOT one big card with `<Separator>`
- **Card header:** `<CardHeader className="pb-2">` + `<CardTitle className="text-base flex items-center gap-2">` with small icon
- **Value fields:** `<p className="text-sm text-muted-foreground">` label, `<p className="font-medium">` value
- **Conditional cards:** do NOT render empty cards
- **Workflow console:** always at the bottom, full-width `<EmbeddedWorkflowConsole>`

### 5.3 Loading and Error States

```tsx
// Loading:
if (isLoading) {
  return (
    <div className="flex min-h-[300px] items-center justify-center">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}
// Error:
if (error) {
  return (
    <div className="space-y-4 p-4">
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Failed to load</AlertTitle>
        <AlertDescription>Record may not exist or you may not have access.</AlertDescription>
      </Alert>
      {/* Use specific list route — NEVER navigate(-1) */}
      <Button variant="outline" onClick={() => navigate('/service/grc/<entity-list-path>')}>← Go Back</Button>
    </div>
  );
}
```

> **Rule:** Replace `<entity-list-path>` with the actual list path for that entity (e.g., `risk-champions`, `departmental-risks`). Never use `navigate(-1)` — the back destination must be deterministic.

### 5.4 Workflow Status Hook

For every workflow-enabled detail page, fetch workflow status with:

```tsx
const { data: workflowStatus, isLoading: isWorkflowLoading } =
  useRiskChampionWorkflowStatus(appointment.id, {
    staleTime: 30_000,
    refetchInterval: 30_000,  // auto-refresh every 30s
  });

const workflowPlanId = workflowStatus?.workflow_plan_id ?? appointment.workflow_plan_id;
```

### 5.5 EmbeddedWorkflowConsole Props

```tsx
<EmbeddedWorkflowConsole
  workflowPlanId={workflowPlanId}
  entityTitle="RC Appointment — John Doe"
  entityType="rc_appointment"
  isLoading={isWorkflowLoading}
  onSubmit={workflowPlanId ? undefined : handleSubmitWorkflow}
  isDraft={appointment.status === 'pending' || appointment.status === 'nominated'}
/>
```

### 5.6 Submit Workflow Button (header)

```tsx
{canManageRiskChampions && isDraft && !workflowPlanId && (
  <Button onClick={handleSubmitWorkflow} disabled={submitMutation.isPending}>
    {submitMutation.isPending
      ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      : <Send className="mr-2 h-4 w-4" />}
    Submit for Approval
  </Button>
)}
```

### 5.7 Child Sections (nested tables inside Detail Pages)

Each workflow-enabled entity that has child records (entries, items, appointments) renders a self-contained section component below the details cards:

| Detail Page | Child Section Component | Add Button Guard |
|-------------|------------------------|------------------|
| `RiskChampionDetailPage` | `<RCAppointmentSection championId={...} />` | `canManageRiskChampions` |
| `DeptRiskRegisterDetailPage` | `<DeptRegisterEntriesSection registerId={...} registerStatus={...} />` | `status === 'in_progress'` |
| `InstitutionalRiskDetailPage` | `<IRREntriesSection registerId={...} />` + `<IRRActivityReportsSection />` | `canManageIRR` |
| `RTAPDetailPage` | `<RTAPItemsSection rtapId={...} />` | `canManageRTAP` |
| `QualityAuditorDetailPage` | `<QAAppointmentSection auditorId={...} />` | `canManageQualityAuditors` |
| `QMSProgramDetailPage` | — (no child table) | — |
| `QMSPlanDetailPage` | `<QMSTeamAssignmentSection planId={...} />` + `<QMSTimetableSection planId={...} />` | `canManageQMSPlan` |

Child section structure mirrors `AuditableEntitiesSection` in `NEW_DETAIL_PAGE_REFERENCE.md` §7:
- Section header with count + add button
- Loading inline spinner
- Empty dashed-border state
- Populated: `<div className="border rounded-md">` → `<Table>`
- Edit + Delete ghost icon buttons, right-aligned
- Confirmation `<AlertDialog>` for delete

### 5.8 Per-Entity Status Lifecycle + `isDraft` Conditions

Every workflow-enabled Detail Page needs:
1. A `isDraft` boolean used in the **Submit** button guard and the `EmbeddedWorkflowConsole` `isDraft` prop.
2. An `isModifiable` boolean used to gate Add/Edit/Delete actions on child records.

The table below defines these for every workflow-enabled entity in this module.
`isDraft` means "workflow not yet started and entity can still be submitted".
`isModifiable` means "child records can still be added or edited".

| Entity | Detail Page | Status Lifecycle (ordered) | `isDraft` expression | `isModifiable` expression |
|--------|-------------|---------------------------|----------------------|--------------------------|
| RCAppointment | `RCAppointmentDetailPage` | `nominated → pending → submitted → approved → rejected → signed` | `status === 'nominated' \|\| status === 'pending'` | same as `isDraft` |
| QAAppointment | `QAAppointmentDetailPage` | mirrors RC Appointment | `status === 'nominated' \|\| status === 'pending'` | same as `isDraft` |
| DepartmentalRiskRegister | `DeptRiskRegisterDetailPage` | `in_progress → submitted → approved → rejected` | `status === 'in_progress'` | `status === 'in_progress'` |
| InstitutionalRiskRegister | `InstitutionalRiskRegisterDetailPage` | `draft → compiled → submitted → approved → rejected` | `status === 'compiled'` | `status === 'draft' \|\| status === 'compiled'` |
| RiskTreatmentActionPlan | `RTAPDetailPage` | `draft → submitted → approved → rejected` | `status === 'draft'` | `status === 'draft'` |
| QuarterlyPerformanceReport | `QPRDetailPage` | `draft → submitted → approved → rejected` | `status === 'draft'` | `status === 'draft'` |
| QMSAuditProgram | `QMSProgramDetailPage` | `draft → submitted → approved → rejected` | `status === 'draft'` | `status === 'draft'` |
| QMSAuditPlan | `QMSPlanDetailPage` | `draft → submitted → approved → rejected` | `status === 'draft'` | `status === 'draft'` |

#### Status → Workflow Transitions (all workflow-enabled entities)

Every workflow-enabled entity follows the same three WO-triggered transitions:

| User Action | API Endpoint | Result |
|-------------|--------------|--------|
| Submit for approval | `POST workflow/start/` | Status advances to workflow stage 1 value; workflow console becomes active |
| Recall workflow | `POST workflow/recall/` | Workflow cancelled, `entity.status` reset to `draft`; Submit button re-appears |
| Admin cancel | `POST workflow/cancel/` | Workflow terminated; status set to `cancelled` |

When the workflow advances through its stages (approve/reject), the Work Orchestration service pushes status updates to the entity — the frontend reads the current status via the workflow status hook (`refetchInterval: 30_000`).

#### Recall Button Pattern

Show "Recall" only when the workflow has started and is not yet completed:

```tsx
{canManageX && workflowPlanId && !workflowStatus?.workflow_completed_at && (
  <Button variant="outline" onClick={handleRecallWorkflow} disabled={recallMutation.isPending}>
    {recallMutation.isPending
      ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      : <Undo2 className="mr-2 h-4 w-4" />}
    Recall
  </Button>
)}
```

---

### 5.9 Per-Entity Header Buttons (Role-Based)

The header of each workflow-enabled detail page shows different action buttons depending on the entity type. Follow this table exactly when implementing each page — **never** render a button and then disable it for permissions; hide it entirely (see §7.2).

| Detail Page | Button Label | Icon | Permission Guard | Status Guard | Notes |
|-------------|-------------|------|-----------------|--------------|-------|
| **Workflow-enabled entities (Submit / Recall)** | | | | | |
| `RCAppointmentDetailPage` | Submit for Approval | `Send` | `canManageRiskChampions` | `isDraft && !workflowPlanId` | Primary `default` variant |
| `RCAppointmentDetailPage` | Recall | `Undo2` | `canManageRiskChampions` | `workflowPlanId && !workflow_completed_at` | `outline` variant |
| `QAAppointmentDetailPage` | Submit for Approval | `Send` | `canManageQualityAuditors` | `isDraft && !workflowPlanId` | Primary |
| `QAAppointmentDetailPage` | Recall | `Undo2` | `canManageQualityAuditors` | `workflowPlanId && !workflow_completed_at` | `outline` |
| `DeptRiskRegisterDetailPage` | Submit to RMQAM | `Send` | `canManageDeptRegisters` | `isDraft && !workflowPlanId` | Primary |
| `DeptRiskRegisterDetailPage` | Recall | `Undo2` | `canManageDeptRegisters` | `workflowPlanId && !workflow_completed_at` | `outline` |
| `InstitutionalRiskRegisterDetailPage` | Submit for Governance | `Send` | `canManageIRR` | `isDraft && !workflowPlanId` | Primary |
| `InstitutionalRiskRegisterDetailPage` | Recall | `Undo2` | `canManageIRR` | `workflowPlanId && !workflow_completed_at` | `outline` |
| `RTAPDetailPage` | Submit RTAP | `Send` | `canManageRTAP` | `isDraft && !workflowPlanId` | Primary |
| `RTAPDetailPage` | Recall | `Undo2` | `canManageRTAP` | `workflowPlanId && !workflow_completed_at` | `outline` |
| `QPRDetailPage` | Submit Report | `Send` | `canManageQPR` | `isDraft && !workflowPlanId` | Primary |
| `QPRDetailPage` | Recall | `Undo2` | `canManageQPR` | `workflowPlanId && !workflow_completed_at` | `outline` |
| `QMSProgramDetailPage` | Submit for Approval | `Send` | `canManageQMSPrograms` | `isDraft && !workflowPlanId` | Primary |
| `QMSProgramDetailPage` | Recall | `Undo2` | `canManageQMSPrograms` | `workflowPlanId && !workflow_completed_at` | `outline` |
| `QMSPlanDetailPage` | Submit Audit Plan | `Send` | `canManageQMSPlans` | `isDraft && !workflowPlanId` | Primary |
| `QMSPlanDetailPage` | Recall | `Undo2` | `canManageQMSPlans` | `workflowPlanId && !workflow_completed_at` | `outline` |
| **QMS Audit Report — Sign actions (NOT workflow-enabled)** | | | | | |
| `QMSAuditReportDetailPage` | Sign (Team Leader) | `PenLine` | `canSignQMSReports` | user is TL AND `!tl_signed_at` | Calls `sign-tl/` endpoint |
| `QMSAuditReportDetailPage` | Sign (Auditee) | `PenLine` | `canSignQMSReports` | user is auditee rep AND `!auditee_signed_at` | Calls `sign-auditee/` endpoint |
| **QMS Audit Report — Governance chain (Gap 12, 25, 26)** | | | | | |
| `QMSAuditReportDetailPage` | Submit to RMQAM | `Send` | `canManageQMSReports` | `status === 'finalised'` | Appears after both signatures |
| `QMSAuditReportDetailPage` | Return for Revision | `Undo2` | `canManageQMSReports` | `status === 'submitted_to_rmqam'` | Opens dialog for `rmqam_review_comments` |
| `QMSAuditReportDetailPage` | Present at MRM | `Presentation` | `canManageQMSReports` | `status === 'submitted_to_rmqam'` | Mutually exclusive with Return for Revision |
| `QMSAuditReportDetailPage` | Record Directives | `FileText` | `canManageQMSReports` | `status === 'presented_at_mrm'` | Opens dialog for `mrm_directives` input |
| `QMSAuditReportDetailPage` | Submit to Audit Committee | `Send` | `canManageQMSReports` | `status === 'directives_received'` | |
| `QMSAuditReportDetailPage` | Audit Committee Reviewed | `CheckCircle2` | `canManageQMSReports` | `status === 'submitted_to_audit_committee'` | |
| `QMSAuditReportDetailPage` | Adopt by Commission | `Stamp` | `canManageQMSReports` | `status === 'audit_committee_reviewed'` | Terminal status |
| **RAS Status Transitions (Gap 15, 28)** | | | | | |
| `RiskAssessmentSheetDetailPage` | Submit to Head | `Send` | `canConductRiskAssessments` | `status === 'draft'` | Primary |
| `RiskAssessmentSheetDetailPage` | Endorse | `BadgeCheck` | `canReviewRiskAssessments` | `status === 'submitted_to_head'` | Head of Directorate |
| `RiskAssessmentSheetDetailPage` | Submit to RMQAM | `Send` | `canConductRiskAssessments` | `status === 'head_endorsed'` | |
| `RiskAssessmentSheetDetailPage` | Approve | `CheckCircle2` | `canReviewRiskAssessments` | `status === 'submitted_to_rmqam'` | RMQAM officer |
| `RiskAssessmentSheetDetailPage` | Return for Rework | `Undo2` | `canReviewRiskAssessments` | `status === 'submitted_to_rmqam'` | Opens dialog for `review_comments` |
| `RiskAssessmentSheetDetailPage` | Resubmit | `Send` | `canConductRiskAssessments` | `status === 'returned_for_rework'` | Calls same submit endpoint |
| **NC Dispute/Withdrawal (Gap 4)** | | | | | |
| `NonConformanceDetailPage` | Dispute | `Flag` | `canRespondNCs` | `closure_status === 'raised'` | Opens `NCDisputeDialog` |
| `NonConformanceDetailPage` | Resolve Dispute | `Scale` | `canManageNCs` | `closure_status === 'disputed'` | Opens `NCResolveDisputeDialog` |
| **IRR Workshop & Distribution (Gap 8, 24)** | | | | | |
| `InstitutionalRiskRegisterDetailPage` | Notify Directors | `Mail` | `canManageIRR` | `!directors_notified_at` | Shows "Notified on {date}" after |
| `InstitutionalRiskRegisterDetailPage` | Notify Risk Champions | `Mail` | `canManageIRR` | `!rcs_notified_at` | Shows "Notified on {date}" after |
| `InstitutionalRiskRegisterDetailPage` | Distribute to Directorates | `Share2` | `canManageIRR` | `status === 'approved' && !distributed_to_directorates_at` | Shows ref + date after |
| **RTAP Reminder & Distribution (Gap 7, 24)** | | | | | |
| `RTAPDetailPage` | Send Reminder to RCs | `Bell` | `canManageRTAP` | `status === 'active'` | toast shows `notified_count` |
| `RTAPDetailPage` | Distribute to Directorates | `Share2` | `canManageRTAP` | `status === 'approved' && !distributed_to_directorates_at` | Shows ref + date after |
| **QA Training Approval (Gap 23)** | | | | | |
| `QATrainingDetailPage` | Approve | `CheckCircle2` | `canManageQATraining` | `approval_status === 'proposed'` | |
| `QATrainingDetailPage` | Reject | `XCircle` | `canManageQATraining` | `approval_status === 'proposed'` | Opens dialog for `rejection_notes` |
| `QATrainingDetailPage` | Notify Attendees | `Bell` | `canManageQATraining` | `approval_status === 'approved'` | |

> **Note on `QMSAuditReport`:** This entity is NOT workflow-enabled (no `WorkflowMixin`). Its header buttons are sign actions plus the governance chain. The `EmbeddedWorkflowConsole` is NOT rendered on `QMSAuditReportDetailPage`.
>
> **Note on `RiskAssessmentSheetDetailPage` and `NonConformanceDetailPage`:** These are NEW detail pages (Gap-resolved). They are NOT workflow-enabled; their status transitions use custom action endpoints, not the workflow engine.

#### `isDraft` in `EmbeddedWorkflowConsole` — Per-Entity Quick Reference

```tsx
// RCAppointmentDetailPage / QAAppointmentDetailPage:
isDraft={entity.status === 'nominated' || entity.status === 'pending'}

// DeptRiskRegisterDetailPage:
isDraft={entity.status === 'in_progress'}

// InstitutionalRiskRegisterDetailPage:
isDraft={entity.status === 'compiled'}

// RTAPDetailPage / QPRDetailPage / QMSProgramDetailPage / QMSPlanDetailPage:
isDraft={entity.status === 'draft'}
```

---

## 6. Forms & Modals

### 6.1 Dialog Pattern

All create/edit dialogs follow this structure:

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@ui/dialog';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@ui/form';
import { Button } from '@ui/button';
import { Loader2 } from 'lucide-react';

interface CreateRiskChampionDialogProps {
  open: boolean;
  onClose: () => void;
  defaultValues?: Partial<RiskChampionFormData>;  // edit mode
}

const schema = z.object({
  nominee_user_id: z.string().min(1, 'Required'),
  directorate_unit_zone_id: z.string().min(1, 'Required'),
  notes: z.string().optional(),
});

export function CreateRiskChampionDialog({ open, onClose, defaultValues }: CreateRiskChampionDialogProps) {
  const isEditMode = !!defaultValues?.nominee_user_id;
  const form = useForm({ resolver: zodResolver(schema), defaultValues });
  const createMutation = useCreateRiskChampion();

  const onSubmit = form.handleSubmit((data) => {
    createMutation.mutate(data, { onSuccess: () => onClose() });
  });

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditMode ? 'Edit' : 'Add'} Risk Champion</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={onSubmit} className="space-y-4">
            {/* form fields */}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEditMode ? 'Save Changes' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

### 6.2 Form Fields per Entity

| Dialog | Fields |
|--------|--------|
| `CreateRiskChampionDialog` | Nominee (user select from IAM), Directorate/Unit/Zone (select from lookup), Notes |
| `CreateRCAppointmentDialog` | Effective Date, Term End Date, Appointment Letter (file upload) |
| `CreateRiskAssessmentSheetDialog` | Risk Description, Risk Category, Risk Owner (user select), Directorate/Unit/Zone, Likelihood Rating (1-5), Impact Rating (1-5), Existing Controls, Proposed Controls |
| `CreateDeptRiskRegisterDialog` | Directorate/Unit/Zone (select), Reporting Period (select: Q1/Q2), Notes |
| `CreateDeptRegisterEntryDialog` | Risk Assessment Sheet (select from approved RAS list) |
| `CreateInstitutionalRiskRegisterDialog` | Reporting Period, Notes |
| `CreateRTAPDialog` | IRR (select), Period |
| `CreateRTAPItemDialog` | IRR Entry (select), Control Description, Responsible Officer (user select), Target Date |
| `CreateQuarterlyPerformanceReportDialog` | Quarter, Fiscal Year, Notes |
| `CreateRiskMeetingDialog` | Title, Meeting Type, Scheduled Date, Venue, Directorate/Unit/Zone |
| `CreateQualityAuditorDialog` | Nominee (user select), Directorate/Unit/Zone (conflict of interest: cannot be own directorate) |
| `CreateQAAppointmentDialog` | Effective Date, Term End Date, Certification Date, Exam Score, Appointment Letter |
| `CreateQATrainingDialog` | Trainer Name, Training Date, Venue |
| `CreateQMSProgramDialog` | Audit Year, Scope, Objectives |
| `CreateQMSAuditPlanDialog` | QMS Program (select), Start Date, End Date, Team Leader (user select) |
| `CreateQMSChecklistDialog` | QMS Plan (select), Assigned QA (user select), Process, ISO Clauses |
| `CreateQMSAuditReportDialog` | QMS Plan (select), Auditee Directorate, Audit Date, QA (user select) |
| `CreateNonConformanceDialog` | Audit Report (select), NC Description, ISO Clause Violated, Evidence, Responsible Party (user select), Proposed Corrective Action, Target Closure Date |

### 6.3 Validation Rules

- All UUID/select fields: `z.string().uuid()` or `z.string().min(1, 'Required')`
- Date fields: `z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Must be YYYY-MM-DD')`
- Rating fields (likelihood, impact): `z.number().int().min(1).max(5)`
- Exam score: `z.number().min(0).max(100)`
- Conflict of interest (QA): validate that `directorate_unit_zone_id` is not the QA's own unit — validate at submit time and show `toast.error` if violated
- `term_end_date` must be after `effective_date` — add `.refine()` to Zod schema

### 6.4 Lookup Dependencies

Lazy-fetch lookup data with `enabled` flag (only fetch when dialog is open):

```tsx
const [isCreateOpen, setIsCreateOpen] = useState(false);
// In dialog component:
const { data: directorates } = useDirectorateUnitZoneLookup(open);   // open prop
const { data: users }        = useIAMUsersLookup(open);
```

### 6.5 Form Initialization & Reset on Dialog Open

Every create/edit dialog **must** reset the form inside a `useEffect` keyed on `[open, entity, form]`. This prevents stale values from a previous open cycle.

```tsx
// Edit mode defaultValues — always unwrap nested FK objects to their .id string:
const form = useForm<FormValues>({
  resolver: zodResolver(schema),
  defaultValues: entity
    ? {
        // unwrap nested FK → id
        fiscal_year_id: entity.fiscal_year.id,
        // scalar fields direct
        title: entity.title,
        notes: entity.notes || '',
      }
    : {
        fiscal_year_id: '',
        title: '',
        notes: '',
      },
});

// Reset on open:
useEffect(() => {
  if (open && mode === 'edit' && entity) {
    form.reset({
      fiscal_year_id: entity.fiscal_year.id,
      title: entity.title,
      notes: entity.notes || '',
    });
  } else if (open && mode === 'create') {
    form.reset({ fiscal_year_id: '', title: '', notes: '' });
  }
}, [open, mode, entity, form]);
```

**Rules:**
- `undefined` (not `null`) for optional number fields — `z.coerce.number().optional()` treats `undefined` as absent.
- Empty string `''` for optional text fields — avoids uncontrolled/controlled warnings on `<Input>`.
- Never call `form.reset()` inside `onSubmit` before `onSuccess` — it clears state before the mutation confirms.
- Dialog open state is **always owned by the parent page** — never by the dialog itself. Props are `open: boolean` + `onClose: () => void`.

### 6.6 Input Type Selection Guide

| Field Type | Component | Zod Type | Notes |
|------------|-----------|----------|-------|
| Short text | `<Input>` | `z.string().min(1)` | — |
| Long text | `<Textarea rows={4}>` | `z.string().optional()` | notes, descriptions |
| Date | `<Input type="date">` | `z.string().min(1)` | returns `"YYYY-MM-DD"` string |
| Integer | `<Input type="number">` | `z.coerce.number().int().min(0)` | `z.coerce` converts the string value |
| Decimal | `<Input type="number" step="0.01">` | `z.coerce.number().min(0).max(100)` | exam score, risk score |
| Static short enum (≤8 options) | shadcn `<Select>` | `z.string().min(1)` | meeting_type, quarter, org_unit_type |
| Large FK lookup (IAM users, org units) | `<SmartSelect>` | `z.string().min(1)` | `<FormControl>` wraps SmartSelect directly — no `<SelectTrigger>` |
| File upload | `<Input type="file">` | `z.instanceof(File)` | appointment letters — pass as FormData |
| Boolean toggle | `<Checkbox>` or shadcn `<Switch>` | `z.boolean()` | attended, dispatched |

#### `<SmartSelect>` Usage Example

```tsx
<FormField
  control={form.control}
  name="responsible_officer"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Responsible Officer *</FormLabel>
      <FormControl>
        <SmartSelect
          value={field.value}
          onChange={field.onChange}
          options={(users ?? []).map((u) => ({ value: u.id, label: u.full_name }))}
          placeholder="Select officer..."
          isLoading={isLoadingUsers}
        />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

### 6.7 Special Validation Rules (Cross-Field & Business)

Handle these in Zod `.refine()` or at submit time:

| Rule | Where | Implementation |
|------|-------|----------------|
| `term_end_date` after `effective_date` (RC/QA Appointments) | Zod refine | `.refine((d) => new Date(d.term_end_date) > new Date(d.effective_date), { message: 'End date must be after start date', path: ['term_end_date'] })` |
| QMS Plan: `notification_date` ≥ 10 days before `audit_start_date` (Rule E.7) | Zod refine | `.refine((d) => { const diff = new Date(d.audit_start_date).getTime() - new Date(d.notification_date).getTime(); return diff >= 10*86400*1000; }, { message: 'Notification must be at least 10 days before audit start', path: ['notification_date'] })` |
| QMS Plan: requires an **approved** QMS Program to exist | submit-time guard | Check `program.status === 'approved'` before calling create; show `toast.error('No approved QMS Program found for this period.')` |
| QA conflict of interest: auditor cannot be assigned to own directorate | submit-time | Check `auditor.org_unit_id === selectedUnitId` and call `toast.error('Conflict of interest: auditor cannot audit their own unit.')` |
| Unique constraint errors from backend | mutation onError | Extract `error.response?.data?.non_field_errors?.[0]` and display via inline `<Alert>` in dialog (see §6.8) |

#### Cascading Select (QMS Plan — Program dependency)

```tsx
// Watch parent field so child options update reactively:
const selectedProgramId = form.watch('qms_program_id');

// Clear child when parent changes:
useEffect(() => {
  if (mode === 'create') {
    form.setValue('team_leader_id', '');
  }
}, [selectedProgramId, mode, form]);
```

### 6.8 Inline Server Error Inside Dialogs

For server-side validation errors during form submit, display an inline `<Alert>` inside the dialog — do NOT use `toast.error` for form-level failures:

```tsx
const [serverError, setServerError] = useState<string | null>(null);

const onSubmit = form.handleSubmit((data) => {
  setServerError(null);
  mutation.mutate(data, {
    onSuccess: () => onClose(),
    onError: (err) => {
      const msg = err.response?.data?.error
        || err.response?.data?.detail
        || err.message;
      setServerError(msg);
    },
  });
});

// Inside the <form>, above <DialogFooter>:
{serverError && (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>{serverError}</AlertDescription>
  </Alert>
)}
```

Reset `serverError` when `open` changes:
```tsx
useEffect(() => { if (!open) setServerError(null); }, [open]);
```

---

## 7. RBAC Enforcement

### 7.1 New Permission Booleans in `useGRCPermissions`

**File:** `frontend/apps/staff-portal/src/hooks/useGRCPermissions.ts`

Add the following computed booleans (follow the existing pattern):

```ts
// Risk Management
const canManageRiskChampions      = hasPermission('grc:risk_champion:manage');
const canViewRiskChampions        = hasPermission('grc:risk_champion:view') || canManageRiskChampions;
const canConductRiskAssessments   = hasPermission('grc:risk_assessment:conduct');   // RC drafts RAS
const canReviewRiskAssessments    = hasPermission('grc:risk_assessment:review');    // RMQAM reviews RAS
const canManageDeptRegisters      = hasPermission('grc:dept_risk_register:manage');
const canApproveDeptRegisters     = hasPermission('grc:dept_risk_register:approve');
const canManageIRR                = hasPermission('grc:institutional_risk_register:manage');
const canApproveIRR               = hasPermission('grc:institutional_risk_register:approve');
const canManageRTAP               = hasPermission('grc:rtap:manage');
const canApproveRTAP              = hasPermission('grc:rtap:approve');
const canRespondRTAP              = hasPermission('grc:rtap:respond');              // RC updates RTAP item status
const canManageQPR                = hasPermission('grc:quarterly_risk_report:manage');
const canApproveQPR               = hasPermission('grc:quarterly_risk_report:approve');
const canManageRiskMeetings       = hasPermission('grc:risk_meeting:manage');
const canViewRiskMeetings         = hasPermission('grc:risk_meeting:view');
const canViewRiskDashboard        = hasPermission('grc:risk_dashboard:view');
// Quality Assurance
const canManageQualityAuditors    = hasPermission('grc:quality_auditor:manage');
const canManageQATraining         = hasPermission('grc:qa_training:manage');
const canManageQMSPrograms        = hasPermission('grc:qms_audit_program:manage');
const canApproveQMSPrograms       = hasPermission('grc:qms_audit_program:approve');
const canManageQMSPlans           = hasPermission('grc:qms_audit_plan:manage');
const canApproveQMSPlans          = hasPermission('grc:qms_audit_plan:approve');
const canManageQMSChecklists      = hasPermission('grc:qms_checklist:manage');
const canManageQMSReports         = hasPermission('grc:qms_audit_report:manage');
const canSignQMSReports           = hasPermission('grc:qms_audit_report:sign');
const canManageNCs                = hasPermission('grc:non_conformance:manage');
const canRespondNCs               = hasPermission('grc:non_conformance:respond');   // responsible officer responds/closes NC
```

Return all new booleans from the hook.

### 7.2 Button Visibility Rules

- **Never** render a button and then disable it due to permissions — hide it with `{canX && <Button ...>}`.
- A button may be `disabled` for state reasons (mutation pending, wrong status) — but visibility is always permission-driven.

### 7.3 Role-to-Action Mapping

| Action | Permission Required | Status Gate |
|--------|--------------------|----|
| Nominate RC / create RC appointment letter | `canManageRiskChampions` | — |
| Submit RC Appointment for approval | `canManageRiskChampions` | status in `['pending','nominated']` + no workflow started |
| Draft / Edit Risk Assessment Sheet | `canConductRiskAssessments` | — |
| Review / Approve Risk Assessment Sheet | `canReviewRiskAssessments` | — |
| Submit DRR to RMQAM | `canManageDeptRegisters` | status `in_progress` |
| Submit IRR for governance workflow | `canManageIRR` | status `compiled` + no workflow started |
| Submit RTAP | `canManageRTAP` | status `draft` |
| Update RTAP item implementation status (RC responds) | `canRespondRTAP` | item status not `completed` |
| Submit QPR | `canManageQPR` | status `draft` |
| Nominate QA / create QA appointment letter | `canManageQualityAuditors` | — |
| Submit QMS Program for approval | `canManageQMSPrograms` | status `draft` + no workflow |
| Submit QMS Audit Plan | `canManageQMSPlans` | status `draft` + no workflow |
| Sign QMS Report (TL) | `canSignQMSReports` | user is TL for the plan (`tl_signed_at` is null) |
| Sign QMS Report (Auditee) | `canSignQMSReports` | user is auditee rep (`auditee_signed_at` is null) |
| Respond to / Close Non-Conformance | `canRespondNCs` | status not `closed` |

### 7.4 Route-Level Access

- All Risk Management and Quality Assurance routes are nested under `/service/grc` which is already protected by `<ServiceProtectedRoute serviceKey="grc">`.
- Do **not** add additional service-level guards inside page components.

### 7.5 Always Use Approach A (Inline Conditional)

The codebase has two approaches to permission-gated rendering. **All new Risk Management pages MUST use Approach A:**

**Approach A — Inline conditional (REQUIRED for all new pages):**
```tsx
const { canManageRiskChampions } = useGRCPermissions();

{canManageRiskChampions && (
  <Button onClick={() => setIsCreateOpen(true)}>
    <Plus className="mr-2 h-4 w-4" />
    Nominate Risk Champion
  </Button>
)}
```

**Approach B — `<ProtectedComponent>` wrapper (LEGACY — do NOT use):**
```tsx
// ❌ Do NOT use for Risk Management pages
<ProtectedComponent service="grc" resource="risk_champion" action="manage">
  <Button>Nominate Risk Champion</Button>
</ProtectedComponent>
```

Approach B is only present in legacy pages (`AuditUniversePage`). All Risk Management pages use Approach A exclusively.

### 7.6 Permission-Gated Table Action Columns

For list page tables, gate `onEdit` and `onDelete` callbacks by passing `undefined` when the user lacks permission or the entity status doesn't allow modifications:

```tsx
onEdit={canManageRiskChampions ? handleEdit : undefined}
onDelete={canManageRiskChampions ? handleDelete : undefined}
```

When `onEdit` or `onDelete` is `undefined`, the table column renders no button for that action — do not render a disabled button.

For status-gated edits (e.g., only editable when `draft`):

```tsx
const handleEdit = (id: string) => {
  const item = items.find((p) => p.id === id);
  if (!item) return;
  // Gate on BOTH permission AND status:
  const canEdit = canManageRTAP && item.status === 'draft';
  if (canEdit) setEditingItem(item);
};

onEdit={canManageRTAP ? handleEdit : undefined}
```

### 7.7 Triple-Gate Submit Button Pattern

Every workflow submit button in this module requires three conditions:
1. **Permission** — user has the manage permission
2. **Status** — entity is in a submittable state (`isDraft`)
3. **Workflow** — no workflow has been started yet (`!workflowPlanId`)

```tsx
const isDraft = entity.status === 'draft'; // adjust per entity (see §5.8)
const workflowPlanId = workflowStatus?.workflow_plan_id ?? entity.workflow_plan_id;

{canManageRTAP && isDraft && !workflowPlanId && (
  <Button onClick={handleSubmitWorkflow} disabled={submitMutation.isPending}>
    {submitMutation.isPending
      ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      : <Send className="mr-2 h-4 w-4" />}
    Submit RTAP
  </Button>
)}
```

Never omit any of the three gates — a missing workflow guard causes a double-submit bug; a missing status gate allows submission at wrong state.

### 7.8 `<PermissionGate>` Component

In addition to inline conditionals (Approach A), there is a GRC-specific `<PermissionGate>` component from `@staff/components/grc/PermissionGate`. Use it for **page-level content gating** where you want to show a proper "Access Restricted" message rather than rendering an empty page.

```tsx
import { PermissionGate } from '@staff/components/grc/PermissionGate';

// Wrap entire page content — shows denied message if permission missing:
<PermissionGate
  permission="grc:institutional_risk_register:manage"
  showDeniedMessage
  fallback={
    <div className="flex items-center justify-center min-h-[400px]">
      <p className="text-muted-foreground">Access Restricted</p>
    </div>
  }
>
  {/* page content */}
</PermissionGate>

// Silently hide an element (no fallback):
<PermissionGate permission="grc:rtap:manage">
  <Button>Create RTAP</Button>
</PermissionGate>

// Multiple permissions — any one is sufficient:
<PermissionGate permission={['grc:rtap:manage', 'grc:rtap:approve']}>
  <RTAPDetailPanel />
</PermissionGate>

// Multiple permissions — ALL required:
<PermissionGate permission={['grc:qms_audit_plan:manage', 'grc:qms_audit_program:manage']} requireAll>
  <AdvancedQMSForm />
</PermissionGate>
```

**When to use which approach:**

| Situation | Approach |
|-----------|----------|
| Button/icon visibility in a page or table | Inline `{canX && <Button>}` |
| Entire page blocked if permission missing (with denied message) | `<PermissionGate showDeniedMessage>` |
| Silently hide a section/component (no message) | `<PermissionGate>` without `showDeniedMessage` |
| Legacy shared components (service/resource/action format) | `<ProtectedComponent>` (do not add new uses) |

**Most Risk Management pages use inline conditionals.** `<PermissionGate showDeniedMessage>` is appropriate for pages where a whole category of users should never land — e.g., the IRR management page should gate on `grc:institutional_risk_register:manage` at the page level, since RCs have no business reaching it.

---

## 8. Notifications

**Library:** `sonner` only. Import: `import { toast } from 'sonner';`

### 8.1 Success Toasts (all inside mutation hooks, not in page components)

```ts
// Create success
toast.success('Risk champion added successfully');

// Workflow submit success
toast.success('Submitted for approval via Work Orchestration');

// Status update
toast.success('RTAP item updated', { description: 'Implementation status changed to In Progress.' });

// Appointment
toast.success('Risk Champion appointed', { description: `Appointment letter has been dispatched.` });

// Workflow advance
toast.success('Workflow advanced', { description: `Stage: ${newStage}` });

// Delete
toast.success('Record deleted successfully');
```

### 8.2 Error Toasts (inside mutation hooks)

```ts
toast.error('Failed to create risk champion', {
  description: error.response?.data?.error || error.message,
});

toast.error('Conflict of interest violation', {
  description: 'Quality Auditor cannot be assigned to audit their own directorate.',
});
```

### 8.3 Page-Level Persistent Errors

For list and detail page load errors, use the `<Alert variant="destructive">` pattern — do not use toasts for read failures.

### 8.4 Warning Toasts

Use `toast.warning()` for non-critical issues that the user should know about but that don't block flow:

```ts
// Workflow already started:
toast.warning('Workflow already in progress', {
  description: 'This record has an active workflow. Recall it first to make changes.',
});

// Conflict of interest detected before submit:
toast.warning('Conflict of interest', {
  description: 'This quality auditor is from the unit being audited.',
});

// Duplicate entry attempt:
toast.warning('Already exists', {
  description: 'A risk register entry for this assessment sheet already exists.',
});
```

### 8.5 Confirm Dialogs for Destructive Actions

Use `<AlertDialog>` (shadcn) for all irreversible actions. This is a UI confirmation pattern — not a toast — but belongs in the notification section as it is part of the feedback/safety layer.

**Pattern (delete confirmation):**
```tsx
<AlertDialog open={!!deletingItem} onOpenChange={(v) => !v && setDeletingItem(null)}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Delete Risk Champion?</AlertDialogTitle>
      <AlertDialogDescription>
        This will permanently remove{' '}
        <span className="font-medium">{deletingItem?.name}</span> from the system.
        This action cannot be undone.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction
        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
        onClick={() => deleteMutation.mutate(deletingItem!.id)}
        disabled={deleteMutation.isPending}
      >
        {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Delete
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

**Pattern (recall workflow confirmation):**
```tsx
<AlertDialog open={showRecallConfirm} onOpenChange={setShowRecallConfirm}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Recall Workflow?</AlertDialogTitle>
      <AlertDialogDescription>
        This will cancel the active approval workflow and reset this record to
        draft status. You can then amend and resubmit.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction onClick={handleConfirmRecall}>
        Yes, Recall
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

> All `<AlertDialog>` components are placed **outside** the main page `<div>`, inside the root fragment `<>...</>` — same as dialogs (see §5.2 of `frontend_core_patterns.md`).

### 8.6 Inline Alert in Dialogs (Server Errors)

When a create/edit form mutation fails with a server validation error, display an inline `<Alert variant="destructive">` inside the dialog body — NOT a toast. See §6.8 for the full pattern.

This distinction is important:
- **Toast** = background result the user does not need to act on immediately (success, async failure)
- **Inline Alert in dialog** = form-submit failure the user must fix before proceeding

### 8.7 Domain-Specific Toast Examples

All toasts are fired inside mutation hooks (`onSuccess` / `onError` callbacks), never in page components.

```ts
// RC/QA Appointment workflow submitted:
toast.success('Appointment submitted for approval', {
  description: `Work Orchestration workflow started.`,
});

// Workflow recalled:
toast.success('Workflow recalled', {
  description: 'Record reset to draft. You can now amend and resubmit.',
});

// RTAP item status updated:
toast.success('RTAP item updated', {
  description: `Implementation status: ${newStatus.replace(/_/g, ' ')}.`,
});

// QMS Report signed (TL or Auditee):
toast.success('Audit report signed', {
  description: 'Your signature has been recorded on the QMS Audit Report.',
});

// Non-Conformance closed:
toast.success('Non-conformance closed', {
  description: 'The NC has been marked as closed with closure notes recorded.',
});

// DRR submitted to RMQAM:
toast.success('Risk register submitted', {
  description: 'The departmental risk register has been forwarded to RMQAM.',
});

// Generic delete:
toast.success('Deleted successfully');

// Generic create with description:
toast.success('Risk champion nominated', {
  description: `${nomineeFullName} has been added as Risk Champion.`,
});
```

---

## 9. State & Async Handling

### 9.1 Loading States

- **List pages:** inline loading banner (dashed border, `Loader2` spin) — never block full page.
- **Detail pages:** centered spinner at `min-h-[300px]` — no text, spinner only.
- **Child sections:** inline spinner with text (e.g., "Loading appointments…").
- **Dialogs:** disable submit button + spinner in button while `mutation.isPending`.
- **Sign buttons (QMS Reports):** replace button icon with `Loader2` while signing mutation is pending.

### 9.2 Query Cache Invalidation After Mutations

```ts
// After create/update/delete — invalidate the list:
queryClient.invalidateQueries({ queryKey: riskChampionKeys.lists() });

// After workflow start/advance — invalidate workflow status + entity detail:
queryClient.invalidateQueries({ queryKey: riskChampionKeys.workflowStatus(id) });
queryClient.invalidateQueries({ queryKey: riskChampionKeys.detail(id) });
```

Do NOT invalidate `riskChampionKeys.all` — this would bust detail caches unnecessarily.

### 9.3 Refetch Intervals

- Workflow status hooks: `refetchInterval: 30_000` (30 seconds) while a workflow is in progress.
- Set `refetchInterval` to `false` once `workflowStatus?.workflow_completed_at` is set.

```ts
const { data: workflowStatus } = useRCAppointmentWorkflowStatus(appointmentId, {
  refetchInterval: workflowStatus?.workflow_completed_at ? false : 30_000,
});
```

### 9.4 Optimistic UI

- Do NOT implement optimistic updates for risk management entities — workflow state is complex.
- Let mutations complete before reflecting state changes.

---

## 10. Navigation & UX Consistency

### 10.1 Breadcrumbs

- Not used in GRC pages — follow existing Internal Audit pattern (no breadcrumbs).
- Use back button on detail pages only: `variant="ghost" size="icon"`, `ChevronLeft` icon (NOT `ArrowLeft`), `aria-label="Back"`.

### 10.2 Navigate to Detail

Use `useNavigate()` from `react-router-dom`. Navigate on row view click:

```tsx
const navigate = useNavigate();
const handleView = (id: string) => navigate(`/service/grc/<entity-path>/${id}`);
```

### 10.2a Detail → List (Back button)

```tsx
// ALWAYS navigate to the specific list route — NEVER use navigate(-1)
const handleBack = () => navigate('/service/grc/risk-champions');

// In JSX:
<Button variant="ghost" size="icon" aria-label="Back" onClick={handleBack}>
  <ChevronLeft className="h-4 w-4" />
</Button>
```

> **Rule (core_patterns §7.2):** Do NOT use `navigate(-1)` on detail pages — the back destination must be deterministic. Apply this rule for both the header back button and the error-state "Go Back" button.

### 10.3 Layout

- All pages render inside `ServiceLayout` automatically via nested `<Route>` structure in `App.tsx`.
- Use `<div className="space-y-4">` as root wrapper on list pages (matches Internal Audit Style B).
- Use `<div className="space-y-4 p-4">` on detail pages (matches `NEW_DETAIL_PAGE_REFERENCE.md`).
- No additional outer padding on list pages.
- Service-level access is enforced by `<ServiceProtectedRoute serviceKey="grc">` in `App.tsx`. Do **not** re-implement service-level guards inside page components.

### 10.4 Empty States

- List pages: handled internally by `GenericListPage` via `itemType` prop.
- Child table sections: use dashed border box (`border border-dashed rounded-md py-8`) with centered text.

### 10.5 Page Titles

Follow naming convention from sidebar config (`servicesConfig.ts`) — use exact same label text as `<h1>` title.

**`<h1>` typography rules:**
- List pages: `<h1 className="text-2xl font-bold">` (matches `space-y-4` flat layout)
- Detail pages: `<h1 className="text-2xl font-semibold">` (matches `flex items-center gap-4` header row)

These differ — do not mix them.

---

## 11. Integration with Workflow Service

### 11.1 Entities with Workflow

| Entity | Workflow Type Key |
|--------|------------------|
| RC Appointment | `risk.rc_appointment` |
| QA Appointment | `risk.qa_appointment` |
| Dept Risk Register | `risk.dept_register_approval` |
| Institutional Risk Register | `risk.institutional_register_governance` |
| RTAP | `risk.quarterly_report_governance` |
| Quarterly Performance Report | `risk.quarterly_report_governance` |
| QMS Audit Program | `risk.qms_audit_program_approval` |
| QMS Audit Plan | `risk.audit_plan_approval` |

### 11.2 Triggering Workflow Start

```ts
// In handleSubmitWorkflow on detail page:
const submitMutation = useStartRCAppointmentWorkflow();

const handleSubmitWorkflow = () => {
  submitMutation.mutate(appointment.id, {
    onSuccess: () => {
      // hook fires success toast internally
      // no UI side effect needed beyond this
    },
  });
};
```

### 11.3 EmbeddedWorkflowConsole States

Three states rendered by `<EmbeddedWorkflowConsole>` (follow `NEW_DETAIL_PAGE_REFERENCE.md` §8):

- **State A — Loading:** `<Card>` with centered spinner and `"Loading workflow status…"` (`text-sm text-muted-foreground`) while workflow status is being fetched.
- **State B — Workflow Active:** iframe to Work Orchestration Django HTML console. Console card header shows: title "Workflow Console", plan ID chip, status `<Badge variant="outline" className="capitalize text-xs">`, and an "Open in New Tab" outline button (`ExternalLink` icon). While iframe loads: overlay spinner `"Loading workflow console…"` with `bg-background/80`. On iframe error: destructive `<Alert>` with `"Failed to load workflow console"`.
- **State C — No Workflow:** faded `GitBranch` icon + `"No workflow started"` label + optional Submit button.
  - **Submit button condition in State C:** The `onSubmit` button renders whenever the `onSubmit` prop is provided. Because State C is only reached when there is no `workflowPlanId`, `noWorkflow` is always `true` here — so passing `onSubmit={undefined}` effectively hides the button regardless of `isDraft`. In practice: pass `onSubmit={workflowPlanId ? undefined : handleSubmitWorkflow}` (as shown in §5.5).

### 11.4 Reflecting Status After Workflow Events

- Workflow state-change webhooks update the backend domain record.
- Frontend polls workflow status (`refetchInterval: 30_000`) on detail page.
- When workflow status changes, `workflowStatus.current_stage` updates → `<EmbeddedWorkflowConsole>` re-renders with new iframe state.
- The entity record's `status` field also changes (driven by backend signal handlers). Re-fetch entity on workflow status change:

```ts
// In useEffect when workflowStatus.current_stage changes:
useEffect(() => {
  if (workflowStatus?.current_stage) {
    queryClient.invalidateQueries({ queryKey: riskChampionKeys.detail(id) });
  }
}, [workflowStatus?.current_stage]);
```

### 11.5 Recall Workflow Flow

All workflow-enabled entities support a **Recall** action that cancels the running workflow and resets the entity back to `draft`.

**Trigger:** Recall button visible when `workflowPlanId && !workflowStatus?.workflow_completed_at` (see §5.6 table).

**Hook naming pattern:** `useRecall[Entity]Workflow()` — mirrors `useStart[Entity]Workflow()`.

**On success:**
```ts
const recallMutation = useRecallRCAppointmentWorkflow();

const handleRecall = () => {
  recallMutation.mutate(appointment.id, {
    onSuccess: () => {
      // Backend signal resets entity.status → 'draft' and clears workflow_plan_id
      // Invalidate BOTH the entity detail AND the workflow status queries:
      queryClient.invalidateQueries({ queryKey: riskChampionKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: riskChampionKeys.workflowStatus(id) });
      // After re-fetch:
      // - workflowPlanId becomes null → EmbeddedWorkflowConsole switches to State C
      // - isDraft becomes true → Submit button re-appears in State C
    },
  });
};
```

**Result in UI:** After recall, `EmbeddedWorkflowConsole` transitions from State B → State C, and the Submit for Approval button re-appears in the page header (triple-gate resolves: `canManageX && isDraft && !workflowPlanId`).

---

## 12. Testing & Validation

### 12.1 UI Behavior Checks

#### List Pages (all entities)
- [ ] Page loads with correct title matching sidebar label (`<h1 className="text-2xl font-bold">` on list pages)
- [ ] Loading banner (dashed, full-width) renders while data is fetching
- [ ] Error alert renders when API returns 4xx/5xx
- [ ] Empty state renders when API returns empty results (`itemType` prop text matches entity name)
- [ ] All table columns display correct data from API response fields
- [ ] Clicking a row on **workflow entities** navigates to the detail page at `/service/grc/<path>/:id`
- [ ] Clicking a row on **non-workflow entities** opens the view dialog (no navigation away)
- [ ] Status badge displays correct color for every possible status value per entity type
- [ ] Pagination controls: next/previous page, page size change, page resets to 1 on page size change
- [ ] Search filter: typing updates results, page resets to 1 on new search
- [ ] Create button is visible/hidden correctly for current user's permission set

#### Detail Pages (workflow entities)
- [ ] Initial load: centered spinner only (no text, no partial data) while `isLoading` is `true`
- [ ] Page title uses `<h1 className="text-2xl font-semibold">` (not `font-bold`)
- [ ] Header row: back button uses `variant="ghost" size="icon"` with `ChevronLeft` icon
- [ ] Back button navigates to the correct **specific list route** (not browser history back)
- [ ] Error state: destructive `<Alert>` + "Go Back" outline button that navigates to specific list route
- [ ] `EmbeddedWorkflowConsole` **State A** (loading): `<Card>` with centered spinner + `"Loading workflow status…"` text
- [ ] `EmbeddedWorkflowConsole` **State B** (active): iframe renders; console header shows plan ID chip, status badge, "Open in New Tab" button; while iframe loads shows overlay spinner; on iframe error shows destructive `<Alert>`
- [ ] `EmbeddedWorkflowConsole` **State C** (no workflow): `GitBranch` icon + `"No workflow started"` label + Submit button (visible when `onSubmit` is passed)
- [ ] Workflow status auto-polls every 30 seconds (`refetchInterval: 30_000`)
- [ ] Workflow polling **stops** once `workflowStatus.workflow_completed_at` is set
- [ ] Entity detail re-fetches when `workflowStatus.current_stage` changes
- [ ] After **Recall**: entity status resets to `draft`, Submit button re-appears in header, console transitions to State C
- [ ] Child sections (e.g., RC Appointments, RTAP Items): render correctly; add/edit/delete buttons visible per status gate
- [ ] **QMS Plan cascading select**: changing `qms_program_id` clears the dependent plan field in create mode

### 12.2 API Integration Checks

#### CRUD
- [ ] Create: form submits correctly, list refreshes (query invalidated), success toast fires
- [ ] Update: form pre-fills with existing data; update saves; success toast fires
- [ ] Delete: confirm `AlertDialog` shown; on confirm, delete succeeds, list refreshes
- [ ] **File upload** (RC/QA appointment letter): form submits as `multipart/form-data`; document UUID returned and stored on entity; no plain JSON submit

#### Workflow
- [ ] Workflow start: Submit for Approval button triggers `start<Entity>Workflow()` mutation; `EmbeddedWorkflowConsole` transitions to State B
- [ ] Workflow advance: iframe reflects new stage after polling refetch
- [ ] **Workflow recall**: Recall button triggers `recall<Entity>Workflow()` mutation; both entity detail AND workflow status queries invalidated; entity returns to `draft`; console transitions to State C; Submit button re-appears

#### Special Endpoints
- [ ] **QMS Report sign (TL)**: `POST /risk/qms-reports/:id/sign-tl/` — report updates `tl_signed_at`; status advances
- [ ] **QMS Report sign (Auditee)**: `POST /risk/qms-reports/:id/sign-auditee/` — report updates `auditee_signed_at`; status advances
- [ ] **RTAP quarterly updates**: add/edit quarterly update records within `RTAPItemsSection` works correctly
- [ ] **QMS team assignments**: add/edit/delete team rows within `QMSTeamAssignmentSection` works correctly

#### Non-Workflow Entities
- [ ] Row click opens view dialog (no navigation); close returns to list with no state loss
- [ ] Edit dialog pre-fills all fields from the existing record
- [ ] Non-workflow entities without a detail page: all CRUD via dialogs only (no `/entity/:id` route)

#### Error Handling
- [ ] API 403 → `toast.error` fires (inside mutation hook) with a descriptive message
- [ ] API 4xx form validation error → inline `<Alert variant="destructive">` inside dialog body (NOT a toast)
- [ ] API 5xx → same inline alert pattern; user can retry

### 12.3 RBAC Validation

Verify with different permission set users for each applicable page:

#### Button Visibility
- [ ] Create button hidden when user lacks `manage` permission
- [ ] Edit action hidden in table rows when user lacks `manage` permission
- [ ] Delete action hidden in table rows when user lacks `manage` permission
- [ ] Submit for Approval button hidden when **any** of these is true: user lacks permission, wrong status, workflow already started (`workflowPlanId` is set) — all three gates must pass
- [ ] Recall button hidden when: no workflow has been started (`!workflowPlanId`) OR workflow is already complete (`workflow_completed_at` is set)

#### QMS Report Signing
- [ ] Sign TL button visible only when: `tl_signed_at` is null AND user has `grc:qms_audit_report:sign`
- [ ] Sign Auditee button visible only when: `auditee_signed_at` is null AND user has `grc:qms_audit_report:sign`
- [ ] Once a sign action is completed, the corresponding sign button disappears (signed field is set)

#### Non-Conformances
- [ ] Respond/Close NC button only visible to users with `grc:non_conformance:respond`

#### Business Rule Guards (submit-time)
- [ ] **QMS Plan creation guard**: if no approved QMS Program exists, `toast.error('No approved QMS Program found for this period.')` fires and form never submits
- [ ] **QA conflict of interest**: if selected auditor belongs to the same directorate being audited, `toast.error('Conflict of interest: auditor cannot audit their own unit.')` fires and form never submits

#### Status Guards (child sections)
- [ ] Add/Edit/Delete buttons inside child sections (e.g., RTAP Items, RC Appointments) are hidden when the parent entity is not in a modifiable status — this is a status gate, NOT a permission gate

#### Server-Side Validation
- [ ] Form mutation server errors render as inline `<Alert variant="destructive">` inside the dialog (not toast)
- [ ] Inline error clears when dialog is closed and reopened

---

## 13. Gap-Resolved Features — Frontend Implementation Details

All 29 gaps identified in `Backend_Gap_Support_Analysis.md` have been resolved on the backend (Phases 1–4). This section documents the frontend implementation requirements for each gap category.

### 13.1 NC Dispute & Withdrawal (Gap 4)

**Backend:** `POST /risk/non-conformances/:id/dispute/` + `POST /risk/non-conformances/:id/resolve-dispute/`
**New statuses:** `disputed`, `withdrawn`
**New fields:** `dispute_reason`, `disputed_at`, `disputed_by`

**Frontend components:**

1. **`NonConformanceDetailPage.tsx`** — NEW detail page (row click navigates from list)
   - Shows NC details, ISO clause, evidence, corrective action
   - Overdue indicator (Gap 5): `const isOverdue = nc.due_date && new Date(nc.due_date) < new Date() && nc.closure_status !== 'closed';` → render red badge
   - **Dispute button:** visible when `canRespondNCs && nc.closure_status === 'raised'`
   - **Resolve Dispute button:** visible when `canManageNCs && nc.closure_status === 'disputed'`

2. **`NCDisputeDialog.tsx`** — dialog for disputing an NC
   ```tsx
   // Fields: dispute_reason (required textarea)
   // On submit: calls disputeNonConformance(ncId, { dispute_reason })
   // On success: toast.success('Non-conformance disputed'), invalidate detail query
   ```

3. **`NCResolveDisputeDialog.tsx`** — dialog for TL to resolve dispute
   ```tsx
   // Fields: resolution_action (textarea), new_status (select: 'acknowledged', 'withdrawn')
   // On submit: calls resolveNCDispute(ncId, data)
   // On success: toast.success('Dispute resolved'), invalidate detail query
   ```

4. **List page status filter:** Add `'disputed'` and `'withdrawn'` to `NonConformancesPage` filter dropdown

### 13.2 RAS Status Transitions (Gaps 15, 28)

**Backend:** 5 action endpoints on `RiskAssessmentSheet` — submit, endorse, submit-to-rmqam, approve, return-for-rework
**Status flow:** `draft → submitted_to_head → head_endorsed → submitted_to_rmqam → approved` (or `→ returned_for_rework → draft`)

**Frontend components:**

1. **`RiskAssessmentSheetDetailPage.tsx`** — NEW detail page
   - Shows risk details: description, category, owner, likelihood/impact, inherent risk, existing controls, residual risk, proposed controls
   - **Review Comments card:** conditional — only when `status === 'returned_for_rework'` and `review_comments` is non-empty
   - Status transition buttons in header (see `RASStatusActionButtons.tsx`)

2. **`RASStatusActionButtons.tsx`** — renders the correct action button based on current status + user role:

   | Status | Button | Permission | Service Function |
   |--------|--------|-----------|-----------------|
   | `draft` | Submit to Head | `canConductRiskAssessments` | `submitRAS(id)` |
   | `submitted_to_head` | Endorse | `canReviewRiskAssessments` (Head) | `endorseRAS(id)` |
   | `head_endorsed` | Submit to RMQAM | `canConductRiskAssessments` | `submitRASToRMQAM(id)` |
   | `submitted_to_rmqam` | Approve | `canReviewRiskAssessments` | `approveRAS(id)` |
   | `submitted_to_rmqam` | Return for Rework | `canReviewRiskAssessments` | `returnRASForRework(id, { review_comments })` |
   | `returned_for_rework` | Resubmit | `canConductRiskAssessments` | `submitRAS(id)` |

   Return-for-Rework opens a confirmation dialog requiring `review_comments` input.

3. **`RiskAssessmentSheetsPage.tsx`** list page: row click navigates to detail (not dialog)

### 13.3 QMS Audit Report Governance Chain (Gaps 12, 25, 26)

**Backend:** 7 governance action endpoints beyond sign-tl/sign-auditee
**Status flow:** `draft → tl_signed → auditee_acknowledged → finalised → submitted_to_rmqam → (returned_for_revision | presented_at_mrm) → directives_received → submitted_to_audit_committee → audit_committee_reviewed → adopted_by_commission`

**Frontend components:**

1. **`QMSReportGovernanceButtons.tsx`** — renders governance action button(s) based on current status:

   | Status | Button | Permission | Service Function |
   |--------|--------|-----------|-----------------|
   | `finalised` | Submit to RMQAM | `canManageQMSReports` | `submitQMSReportToRMQAM(id)` |
   | `submitted_to_rmqam` | Return for Revision | `canManageQMSReports` | `returnQMSReportForRevision(id, { rmqam_review_comments })` |
   | `submitted_to_rmqam` | Present at MRM | `canManageQMSReports` | `presentQMSReportAtMRM(id)` |
   | `presented_at_mrm` | Record Directives | `canManageQMSReports` | `receiveQMSReportDirectives(id, { mrm_directives })` |
   | `directives_received` | Submit to Audit Committee | `canManageQMSReports` | `submitQMSReportToAuditCommittee(id)` |
   | `submitted_to_audit_committee` | Audit Committee Reviewed | `canManageQMSReports` | `auditCommitteeReviewQMSReport(id)` |
   | `audit_committee_reviewed` | Adopt by Commission | `canManageQMSReports` | `adoptQMSReportByCommission(id)` |

2. **`QMSAuditReportDetailPage.tsx`** updated layout:
   - Existing: sign buttons (TL + Auditee)
   - NEW: governance buttons below signs (only appear once `status >= finalised`)
   - NEW: MRM Directives card — shows `mrm_directives` text + `mrm_directives_communicated_at` date
   - NEW: Review Comments card — shows `rmqam_review_comments` when `returned_for_revision`

### 13.4 RTAP Send Reminder to RCs (Gap 7)

**Backend:** `POST /risk/rtap/:id/send-reminder/` → `{ notified_count: N }`

**Frontend:**

1. **`RTAPSendReminderButton.tsx`** — renders on `RTAPDetailPage` header:
   ```tsx
   {canManageRTAP && rtap.status === 'active' && (
     <Button variant="outline" onClick={handleSendReminder} disabled={isSending}>
       {isSending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Bell className="mr-2 h-4 w-4" />}
       Send Reminder to RCs
     </Button>
   )}
   // On success: toast.success(`Reminder sent to ${data.notified_count} Risk Champion(s)`)
   ```

### 13.5 IRR Workshop Notifications (Gap 8)

**Backend:** `POST .../notify-directors/` + `POST .../notify-rcs/`
**New fields:** `workshop_date`, `workshop_venue`, `directors_notified_at`, `rcs_notified_at`

**Frontend:**

1. **`IRRWorkshopNotifyButtons.tsx`** — renders on `InstitutionalRiskDetailPage`:
   - **Notify Directors** button: visible when `canManageIRR && !irr.directors_notified_at`
   - **Notify RCs** button: visible when `canManageIRR && !irr.rcs_notified_at`
   - Show timestamp badges when already notified: "Directors notified on {date}" / "RCs notified on {date}"

2. **Workshop Details card** on `InstitutionalRiskDetailPage`:
   - Displays `workshop_date` and `workshop_venue` fields
   - Editable via PATCH when `canManageIRR && irr.status === 'draft'`

### 13.6 RTAP Item Return-for-Rework (Gap 22)

**Backend:** `RTAPItem` now has `returned_for_rework` status + `review_comments`, `returned_at`, `resubmitted_at`

**Frontend:**

1. **`RTAPItemsSection.tsx`** updated:
   - Status column includes `returned_for_rework` badge (red)
   - RMO action: "Return for Rework" button on each item row — visible when `canManageRTAP && item.implementation_status === 'in_progress'`
   - Opens inline dialog for `review_comments` input
   - RC action: "Resubmit" button — visible when `canRespondRTAP && item.implementation_status === 'returned_for_rework'`

### 13.7 Post-Approval Distribution (Gap 24)

**Backend:** `POST .../distribute/` endpoints on both IRR and RTAP
**New fields:** `distributed_to_directorates_at`, `distribution_reference`

**Frontend:**

1. **`IRRDistributeButton.tsx`** — renders on `InstitutionalRiskDetailPage`:
   ```tsx
   {canManageIRR && irr.status === 'approved' && !irr.distributed_to_directorates_at && (
     <Button onClick={handleDistribute} disabled={isDistributing}>
       <Share2 className="mr-2 h-4 w-4" /> Distribute to Directorates
     </Button>
   )}
   // After distribution: show "Distributed on {date}" + distribution_reference
   ```

2. **`RTAPDistributeButton.tsx`** — same pattern for RTAP

### 13.8 QA Training Approval Flow (Gap 23)

**Backend:** `POST .../approve/`, `POST .../reject/`, `POST .../notify-attendees/`
**New field:** `rejection_notes`

**Frontend:**

1. **`QATrainingApprovalButtons.tsx`** — renders on `QATrainingDetailPage`:

   | Button | Permission | Status Guard | Service Function |
   |--------|-----------|-------------|-----------------|
   | Approve | `canManageQATraining` | `approval_status === 'proposed'` | `approveQATraining(id)` |
   | Reject | `canManageQATraining` | `approval_status === 'proposed'` | `rejectQATraining(id, { rejection_notes })` |
   | Notify Attendees | `canManageQATraining` | `approval_status === 'approved'` | `notifyQATrainingAttendees(id)` |

   Reject opens a dialog requiring `rejection_notes`.

2. **`QATrainingAttendeesSection.tsx`** updated:
   - Show `exam_score`, `exam_attempt_number`, `passed` columns for each attendee (Gap 3)
   - 75% threshold: render `passed` badge green if `exam_score >= 75`, red otherwise
   - Show re-sit indicator when `exam_attempt_number === 2 && !passed`

### 13.9 QA Appointment Certification Gate (Gap 13)

**Backend enforcement:** `POST /risk/quality-auditors/:id/appointments/` returns 400 if `!auditor.is_certified`

**Frontend:**

1. **`QAAppointmentSection.tsx`** — hide "Create Appointment" button when `!auditor.is_certified`:
   ```tsx
   const canCreateAppointment = canManageQualityAuditors && qualityAuditor.is_certified;
   // Show info message when gate fails:
   {canManageQualityAuditors && !qualityAuditor.is_certified && (
     <Alert>
       <AlertDescription>
         QA must pass the ISO audit exam (≥75%) before an appointment can be created.
       </AlertDescription>
     </Alert>
   )}
   ```

### 13.10 QA Qualifications & Experience (Gap 10)

**Backend:** `QualityAuditor` now has `qualifications` and `experience_summary` fields

**Frontend:**
- `CreateQualityAuditorDialog.tsx`: Add `qualifications` textarea and `experience_summary` textarea
- `QualityAuditorDetailPage.tsx`: Display qualifications and experience in a dedicated card

### 13.11 Risk Meeting Management Review Type (Gap 6)

**Backend:** `RiskMeeting.MEETING_TYPE_CHOICES` now includes `('management_review', 'Management Review')`; optional `dept_register` FK

**Frontend:**
- `CreateRiskMeetingDialog.tsx`: Add `management_review` to meeting type select options
- `RiskMeetingViewDialog.tsx`: Display linked DRR when `meeting_type === 'management_review'` and `dept_register` is set

### 13.12 NC Monthly Summary & Overdue (Gap 5)

**Backend:** `GET /risk/non-conformances/monthly-summary/` + `last_reviewed_at` field

**Frontend:**
- `NonConformancesPage.tsx`: Add overdue filter chip and badge on overdue items in list
- Overdue logic: `nc.due_date && new Date(nc.due_date) < today && nc.closure_status !== 'closed'`
- Optional: monthly summary card above the list table (fetched via `fetchNCMonthlySummary()`)

### 13.13 NC Finding Type Seed Data (Gap 29)

**Backend:** `NonConformanceType` records seeded: `major_nc`, `minor_nc`, `observation`, `area_for_improvement`

**Frontend:**
- `CreateNonConformanceDialog.tsx`: Populate `nc_type` select from available NC types (fetch via `/config/` or inline from constants)
- `NonConformancesPage.tsx`: Add `nc_type` filter dropdown

### 13.14 Additional Gap-Resolved Updates

**Gap 9 — One-Active-RC-Per-Unit (already supported):**
- Handle 409 conflict in `CreateRiskChampionDialog` with specific error message

**Gap 11 — QMS Plan NDA (already supported):**
- Read NDA fields from `plan.nda_signed` + `plan.nda_document_id` in `QMSPlanDetailPage`

**Gap 14 — Dispatch Tracking (already supported):**
- "Mark as Dispatched" button on RC/QA appointment detail sections
- PATCH `dispatched=true` + `dispatch_date`

**Gap 16 — 7-day Committee Warning (already supported):**
- Compute `daysUntil(committee_meeting_date) < 7` in workflow submit handler
- Show `toast.warning('Committee meeting is in less than 7 days')` (non-blocking)

**Gap 17 — QPR Submit to IAGO (already supported):**
- "Submit to IAGO" button on QPR detail page when `status >= committee_reviewed`
- PATCH `iago_submitted=true` + `iago_submission_date`

**Gap 18 — Role Assignment Acknowledgment (already supported):**
- Listen for `workflow_completed_at` becoming non-null
- Show `toast.success('Risk Champion Appointed — permissions now active')`

**Gap 19 — QMS Audit Meeting Types (already supported):**
- `QMSAuditMeetingsSection` on `QMSPlanDetailPage` with pre_audit/entry/exit cards

**Gap 20 — Export/Print (deferred P4):**
- Not implemented in this phase — documented as future enhancement

**Gap 21 — RC/QA Nomination Request (offline workaround):**
- Nomination managed offline; RMQAM enters nominee directly in `CreateRiskChampionDialog`

**Gap 27 — Risk Meeting Minutes + Attendance (already supported):**
- `RiskMeetingViewDialog` shows minutes textarea + attendance sub-table

### 13.15 New Hooks Required for Gap Features

Add these mutation hooks to existing hook files:

```ts
// hooks/useNonConformances.ts — add:
export function useDisputeNC() { /* calls disputeNonConformance */ }
export function useResolveNCDispute() { /* calls resolveNCDispute */ }
export function useFetchNCMonthlySummary() { /* calls fetchNCMonthlySummary */ }

// hooks/useRiskAssessmentSheets.ts — add:
export function useSubmitRAS() { /* calls submitRAS */ }
export function useEndorseRAS() { /* calls endorseRAS */ }
export function useSubmitRASToRMQAM() { /* calls submitRASToRMQAM */ }
export function useApproveRAS() { /* calls approveRAS */ }
export function useReturnRASForRework() { /* calls returnRASForRework */ }

// hooks/useQMSAuditReports.ts — add:
export function useSubmitQMSReportToRMQAM() { /* calls submitQMSReportToRMQAM */ }
export function useReturnQMSReportForRevision() { /* calls returnQMSReportForRevision */ }
export function usePresentQMSReportAtMRM() { /* calls presentQMSReportAtMRM */ }
export function useReceiveQMSReportDirectives() { /* calls receiveQMSReportDirectives */ }
export function useSubmitQMSReportToAuditCommittee() { /* calls submitQMSReportToAuditCommittee */ }
export function useAuditCommitteeReviewQMSReport() { /* calls auditCommitteeReviewQMSReport */ }
export function useAdoptQMSReportByCommission() { /* calls adoptQMSReportByCommission */ }

// hooks/useRTAP.ts — add:
export function useSendRTAPReminder() { /* calls sendRTAPReminder */ }
export function useDistributeRTAP() { /* calls distributeRTAP */ }

// hooks/useInstitutionalRiskRegisters.ts — add:
export function useNotifyIRRDirectors() { /* calls notifyIRRDirectors */ }
export function useNotifyIRRRiskChampions() { /* calls notifyIRRRiskChampions */ }
export function useDistributeIRR() { /* calls distributeIRR */ }

// hooks/useQATraining.ts — add:
export function useApproveQATraining() { /* calls approveQATraining */ }
export function useRejectQATraining() { /* calls rejectQATraining */ }
export function useNotifyQATrainingAttendees() { /* calls notifyQATrainingAttendees */ }
```

All mutation hooks follow the standard pattern:
```ts
export function useDisputeNC() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ncId, data }: { ncId: string; data: { dispute_reason: string } }) =>
      disputeNonConformance(ncId, data),
    onSuccess: (_, { ncId }) => {
      queryClient.invalidateQueries({ queryKey: nonConformanceKeys.detail(ncId) });
      queryClient.invalidateQueries({ queryKey: nonConformanceKeys.lists() });
      toast.success('Non-conformance disputed');
    },
    onError: (err: any) => {
      toast.error('Failed to dispute non-conformance', {
        description: err.response?.data?.error || err.message,
      });
    },
  });
}
```

---

## 14. Implementation Order

> **Note:** All backend gaps (Phases 1–4) are fully resolved. No backend work is blocking frontend implementation. All 29 gaps from `Backend_Gap_Support_Analysis.md` have been addressed. The phases below cover pure frontend work.

Execute phases in this sequence. Each phase must be complete before starting the next.

### Phase A — Foundation (Day 1)
1. Add/update TypeScript types to `types/grc.ts` — including all gap-resolved fields (§13 entity interfaces)
2. Add API path constants to `grcService.ts` — including gap-resolved action endpoints (§3.1)
3. Implement all service functions in `grcService.ts` — including gap-resolved action functions (§3.2.2)
4. Add new permission codes to `GRCPermissions` interface in `grc.ts`

### Phase B — RBAC & Query Keys (Day 1)
5. Add risk management permission booleans to `useGRCPermissions.ts`
6. Create query key factories (add to `grcKeys.ts`)

### Phase C — Hooks (Day 2)
7. Implement all data hooks (list + detail + mutations) — one file per entity group:
   - `useRiskChampions.ts` + `useRCAppointments.ts`
   - `useRiskAssessmentSheets.ts` — include RAS status-transition mutation hooks (§13.15)
   - `useDeptRiskRegisters.ts`
   - `useInstitutionalRiskRegisters.ts` — include notify + distribute mutation hooks (§13.15)
   - `useRTAP.ts` + `useRTAPItems.ts` — include send-reminder + distribute mutation hooks (§13.15)
   - `useRiskPerformanceReports.ts`
   - `useRiskMeetings.ts`
   - `useQualityAuditors.ts` + `useQAAppointments.ts`
   - `useQATraining.ts` — include approve/reject/notify mutation hooks (§13.15)
   - `useQMSPrograms.ts`
   - `useQMSAuditPlans.ts`
   - `useQMSChecklists.ts`
   - `useQMSAuditReports.ts` — include governance chain mutation hooks (§13.15)
   - `useNonConformances.ts` — include dispute/resolve mutation hooks (§13.15)

### Phase D — List Pages (Day 3–4)
8. `RiskAssessmentSheetsPage.tsx` — row click navigates to detail (not dialog)
9. `RiskMeetingsPage.tsx` — row click opens view dialog
10. `QATrainingPage.tsx` — row click navigates to detail
11. `QMSChecklistsPage.tsx` — row click opens view dialog
12. `NonConformancesPage.tsx` — row click navigates to detail (not dialog; Gap 4 actions live here)
13. `RiskChampionsPage.tsx` (replace mock, add navigate to detail)
14. `DepartmentalRisksPage.tsx` (replace placeholder)
15. `InstitutionalRisksPage.tsx` (replace placeholder)
16. `RiskTreatmentPlansPage.tsx` (replace placeholder, now RTAP list)
17. `RiskPerformanceReportsPage.tsx`
18. `QualityAuditorsPage.tsx` (replace placeholder)
19. `QMSProgramsPage.tsx`
20. `QMSPlansPage.tsx`
21. `QMSAuditReportsPage.tsx` (replace QualityAuditsPage.tsx content)
22. Update routing in `App.tsx` for all new pages + detail routes

### Phase E — Detail Pages (Days 5–7)
23. `RiskChampionDetailPage.tsx` + `RCAppointmentSection.tsx` + `CreateRCAppointmentDialog.tsx`
24. `RiskAssessmentSheetDetailPage.tsx` + `RASStatusActionButtons.tsx` (Gap 15/28)
25. `DeptRiskRegisterDetailPage.tsx` + `DeptRegisterEntriesSection.tsx` + `CreateDeptRegisterEntryDialog.tsx`
26. `InstitutionalRiskDetailPage.tsx` + `IRREntriesSection.tsx` + `IRRActivityReportsSection.tsx` + `IRRWorkshopNotifyButtons.tsx` (Gap 8) + `IRRDistributeButton.tsx` (Gap 24)
27. `RTAPDetailPage.tsx` + `RTAPItemsSection.tsx` + `CreateRTAPItemDialog.tsx` + `RTAPSendReminderButton.tsx` (Gap 7) + `RTAPDistributeButton.tsx` (Gap 24)
28. `RiskPerformanceReportDetailPage.tsx`
29. `QualityAuditorDetailPage.tsx` + `QAAppointmentSection.tsx` + `CreateQAAppointmentDialog.tsx` (with is_certified gate — Gap 13)
30. `QATrainingDetailPage.tsx` + `QATrainingAttendeesSection.tsx` + `QATrainingApprovalButtons.tsx` (Gap 23) — attendees show exam fields (Gap 3)
31. `QMSProgramDetailPage.tsx`
32. `QMSPlanDetailPage.tsx` + `QMSTeamAssignmentSection.tsx` + `QMSTimetableSection.tsx`
33. `QMSAuditReportDetailPage.tsx` + `SignReportButtons.tsx` + `QMSReportGovernanceButtons.tsx` (Gap 12/25/26)
34. `NonConformanceDetailPage.tsx` + `NCDisputeDialog.tsx` + `NCResolveDisputeDialog.tsx` (Gap 4) — overdue indicator (Gap 5)

### Phase F — Create/Edit Dialogs (Day 7–8)
35. All Create dialogs not yet implemented in Phase E
36. Implement edit mode for existing dialogs (pass `defaultValues`)
37. `CreateQualityAuditorDialog.tsx` — include `qualifications` + `experience_summary` fields (Gap 10)
38. `CreateRiskMeetingDialog.tsx` — include `management_review` type + optional `dept_register` FK (Gap 6)
39. `CreateNonConformanceDialog.tsx` — include `nc_type` select populated from seeded types (Gap 29)

### Phase G — Navigation & Sidebar (Day 8)
40. Update `servicesConfig.ts` with all new sidebar items (add missing routes)
41. Update `App.tsx` to replace all remaining `<ServicePlaceholder>` elements with real pages

### Phase H — Dashboard (Day 8)
42. `RiskDashboardPage.tsx` — summary cards + comparative analysis chart (Gap 1 + Gap 2)

### Phase I — Final QA (Day 9)
43. Run UI behavior checks (§12.1) on all pages
44. Run API integration checks (§12.2) on all entities — including gap-resolved action endpoints
45. Run RBAC validation (§12.3) with test users of different roles
46. Verify all gap-resolved features:
    - [ ] NC dispute/resolve workflow (Gap 4)
    - [ ] NC overdue badge + monthly summary (Gap 5)
    - [ ] RAS status transitions (Gaps 15/28)
    - [ ] QMS Report governance chain (Gaps 12/25/26)
    - [ ] RTAP send reminder (Gap 7)
    - [ ] IRR notify directors/RCs (Gap 8)
    - [ ] RTAP item return-for-rework (Gap 22)
    - [ ] QA training approve/reject/notify (Gap 23)
    - [ ] IRR/RTAP distribution (Gap 24)
    - [ ] QA qualifications display (Gap 10)
    - [ ] QA certification gate (Gap 13)
    - [ ] Management review meeting type (Gap 6)
    - [ ] QA exam tracking per attendee (Gap 3)
    - [ ] NC type filter from seeded data (Gap 29)
47. Fix any issues found

---

*End of Frontend Implementation Plan — Risk Management and Quality Assurance Module*
*Updated: March 2026 — All 29 backend gaps resolved, plan updated for complete frontend implementation*
