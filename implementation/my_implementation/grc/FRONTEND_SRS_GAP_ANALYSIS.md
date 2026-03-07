# FRONTEND SRS GAP ANALYSIS — GRC Module (Staff Portal)

**Scope**: `frontend/apps/staff-portal/` — GRC pages, components, hooks, service layer  
**Reference**: `AUDT2_ext.md` (SRS), `BACKEND_SRS_GAP_ANALYSIS copy.md` (backend baseline)  
**Date**: March 2026  
**Author**: Gap analysis via automated audit

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [SRS Requirements Traceability Matrix](#2-srs-requirements-traceability-matrix)
3. [Audit Method & Scope](#3-audit-method--scope)
4. [What IS Implemented (Frontend Inventory)](#4-what-is-implemented-frontend-inventory)
5. [Gap Registry](#5-gap-registry)
6. [Gap Details — FE-GAP 1: Engagement Notifications](#6-fe-gap-1-engagement-notifications)
7. [Gap Details — FE-GAP 2: Auditee Follow-Up Responses](#7-fe-gap-2-auditee-follow-up-responses)
8. [Gap Details — FE-GAP 3: AuditMonitoringDetailDialog — Stale Progress Field](#8-fe-gap-3-auditmonitoringdetaildialog--stale-progress-field)
9. [Gap Details — FE-GAP 4: RCM Lifecycle Actions Missing](#9-fe-gap-4-rcm-lifecycle-actions-missing)
10. [Gap Details — FE-GAP 5: Quarterly Report WO Submit-for-Approval](#10-fe-gap-5-quarterly-report-wo-submit-for-approval)
11. [Gap Details — FE-GAP 6: Working Paper Review — Lead Auditor Constraint Not Enforced](#11-fe-gap-6-working-paper-review--lead-auditor-constraint-not-enforced)
12. [Gap Details — FE-GAP 7: Escalation Badge Not Shown in Monitoring Detail](#12-fe-gap-7-escalation-badge-not-shown-in-monitoring-detail)
13. [Gap Details — FE-GAP 8: Stamped Document URL Not Displayed](#13-fe-gap-8-stamped-document-url-not-displayed)
14. [Gap Details — FE-GAP 9: EngagementDetailPage Missing Sub-Entity Sections](#14-fe-gap-9-engagementdetailpage-missing-sub-entity-sections)
15. [Gap Details — FE-GAP 10: AuditSurvey Missing Fraud Risk Assessment Field](#15-fe-gap-10-auditsurvey-missing-fraud-risk-assessment-field)
16. [Gap Details — FE-GAP 11: Generate Draft Plan Not Wired](#16-fe-gap-11-generate-draft-plan-not-wired)
17. [Gap Details — FE-GAP 12: Audit Team Member Assignment Not Exposed](#17-fe-gap-12-audit-team-member-assignment-not-exposed)
18. [Gap Details — FE-GAP 13: Evidence File Uploads Not Wired to Any Page](#18-fe-gap-13-evidence-file-uploads-not-wired-to-any-page)
19. [Gap Details — FE-GAP 14: AuditFinding Lifecycle Actions Missing](#19-fe-gap-14-auditfinding-lifecycle-actions-missing)
20. [Gap Details — FE-GAP 15: AuditSurvey Missing Mark Complete Action](#20-fe-gap-15-auditsurvey-missing-mark-complete-action)
21. [Implementation Guide — FE-GAP 1 (Engagement Notifications)](#21-implementation-guide--fe-gap-1-engagement-notifications)
22. [Implementation Guide — FE-GAP 2 (Follow-Up Responses)](#22-implementation-guide--fe-gap-2-follow-up-responses)
23. [Implementation Guide — FE-GAP 3 (Stale Progress Field)](#23-implementation-guide--fe-gap-3-stale-progress-field)
24. [Implementation Guide — FE-GAP 4 (RCM Lifecycle)](#24-implementation-guide--fe-gap-4-rcm-lifecycle)
25. [Implementation Guide — FE-GAP 5 (QR WO Submit)](#25-implementation-guide--fe-gap-5-qr-wo-submit)
26. [Implementation Guide — FE-GAP 6 (WP Review Enforcement)](#26-implementation-guide--fe-gap-6-wp-review-enforcement)
27. [Implementation Guide — FE-GAP 9/10/11](#27-implementation-guide--fe-gap-91011)
28. [File Inventory — What Exists vs. What Must Be Created](#28-file-inventory--what-exists-vs-what-must-be-created)
29. [Priority Implementation Order](#29-priority-implementation-order)

---

## 1. Executive Summary

The GRC staff portal frontend is **~56% SRS-compliant** (backend is ~96%). The core data management CRUD workflow, working paper lifecycle, declarations, surveys, RCM entries, audit programs, memos, and meetings are all present. However, two backend-implemented features are **entirely absent** from the frontend, and eleven features have **incomplete lifecycle actions, missing fields, or structural problems**.

| Category | Count | Status |
|---|---|---|
| Entirely absent features (0% UI coverage) | 2 | 🔴 CRITICAL |
| Missing lifecycle action buttons | 7 | 🟡 HIGH |
| Missing fields / unwired service functions | 4 | 🟡 HIGH |
| Stale/incorrect field references | 1 | 🟡 HIGH |
| Display/cosmetic gaps | 1 | 🟢 LOW |
| **Total gaps** | **15** | |

**The two fully-absent features are:**
- **Engagement Notifications** (FE-GAP 1) — backend fully implemented at `audit/engagement-notifications/**`, zero service calls in frontend, zero TypeScript types, no page, no components
- **Auditee Follow-Up Responses** (FE-GAP 2) — backend fully implemented at `audit/follow-up-responses/**`, zero service calls, no hooks, no UI

**Six additional "service-exists-but-unused" / "type-absent" / "action-missing" gaps:**
- **FE-GAP 11** — `generateDraftPlan()` in `grcService.ts` but no button in any page
- **FE-GAP 10** — `fraud_risk_assessment` JSONField in backend absent from TypeScript type + dialog
- **FE-GAP 12** — `team_members` JSONField on `AuditEngagement`; no type field, no picker in dialog
- **FE-GAP 13** — `uploadEvidence`/`fetchEvidence`/`deleteEvidence` in `grcService.ts`; `EvidenceAttachment` type absent; zero pages call these functions
- **FE-GAP 14** — `findings/<pk>/finalize/` and `findings/<pk>/responses/` both absent from `grcService.ts`; findings are permanently stuck in `draft`
- **FE-GAP 15** — `surveys/<pk>/complete/` absent; surveys never leave `draft` status

---

## 2. SRS Requirements Traceability Matrix

Full mapping of all 41 SRS system requirements (from `AUDT2_ext.md`) to frontend coverage:

| Req # | SRS Section | Description | Frontend Status | Gap(s) |
|---|---|---|---|---|
| 1 | Audit Plan | CIA initiates RBIAP | ✅ `AuditPlansPage` | — |
| 2 | Audit Plan | IA drafts RBIAP, submits to CIA | ✅ Submit button + WO console | — |
| 3 | Audit Plan | CIA reviews, submits to Management | ✅ WO console (Stage 1) | — |
| 4 | Audit Plan | Management reviews | ✅ WO console (Stage 2) | — |
| 5 | Audit Plan | CIA submits to Audit Committee | ✅ WO console (Stage 3) | — |
| 6 | Audit Plan | Committee reviews and determines | ✅ WO task list | — |
| 7 | Audit Plan | Committee requests improvement, CIA revises | ✅ WO pending action flow | — |
| 8 | Audit Plan | Committee approves | ✅ WO Stage 3 approve | — |
| 9 | Audit Plan | Generate approved RBIAP output | ✅ Status → approved shown | — |
| 10 | Engagement | CIA appoints LA + team, prepares Memo | ⚠️ `CreateAuditEngagementDialog` has `lead_auditor` but no `team_members` picker; `EngagementDetailPage` shows no team roster | FE-GAP 12 |
| 11 | Engagement | LA prepares Memo, submits to CIA | ✅ `submitAuditMemo` + WO | — |
| 12 | Engagement | CIA reviews memo, submits to DG | ✅ WO Stage 1 | — |
| 13 | Engagement | DG reviews and approves memo | ✅ WO Stage 2 | — |
| 14 | Engagement | CIA transmits approved memo to LA | ✅ WO completion | — |
| 15 | Engagement | LA prepares engagement plan, checklists | ⚠️ `AuditProgramsPage` (standalone only — not embedded in engagement context) | FE-GAP 9 |
| 16 | Engagement | Team signs Declaration of Independence | ⚠️ `DeclarationsPage` (standalone only — not embedded in engagement context) | FE-GAP 9 |
| 17 | Engagement | LA contacts auditable area | ✅ Covered by engagement notification workflow | FE-GAP 1 (UI absent) |
| 18 | Engagement | Generate Approved Memo + Signed Declaration | ⚠️ Partial — memo/declaration exist but no co-rendering/PDF flow | — |
| 19 | Survey | Preliminary survey + Fraud Risk Assessment | ⚠️ `AuditSurveysPage` present, but `fraud_risk_assessment` JSONField absent from type/UI; "Mark Complete" action absent | FE-GAP 10, FE-GAP 15 |
| 20 | Survey | Review adequacy of controls, develop tests | ⚠️ Survey exists but no structured control adequacy test design UI | FE-GAP 10 |
| 21 | Survey | Inadequate controls → findings + impact tests | ✅ `AuditFindingsPage` + `AuditRecommendationsPage` | — |
| 22 | Survey | LA develops RCM, prepares draft audit program | ⚠️ Both exist as standalone pages; neither is embedded in engagement context | FE-GAP 9 |
| 23 | Survey | IA and CIA review/approve audit program | ✅ Submit + Approve buttons in `AuditProgramsPage` | — |
| 24 | Survey | LA prepares Engagement Notification | ❌ Entirely absent from frontend | FE-GAP 1 |
| 25 | Survey | CIA approves EN | ❌ Entirely absent from frontend | FE-GAP 1 |
| 26 | Survey | Generate Approved EN output / transmit | ❌ Entirely absent from frontend | FE-GAP 1 |
| 27 | Implementation | Entry meeting | ✅ `AuditMeetingsPage` with `meeting_type=entry` | — |
| 28 | Implementation | Fieldwork — Working Papers + Evidence | ⚠️ `WorkingPaperDetailPage` + WO console present; but evidence file upload service unused — no `EvidenceAttachmentSection` component exists | FE-GAP 13 |
| 29 | Implementation | LA reviews WPs, pre-exit | ✅ WP review + `meeting_type=pre_exit` | — |
| 30 | Implementation | Pre-exit meeting | ✅ `AuditMeetingsPage` | — |
| 31 | Implementation | WPs submitted to LA | ✅ Submit + WO Stage 1 | — |
| 32 | Implementation | CIA reviews/approves WPs | ✅ WO Stage 2; UI button gating not enforced | FE-GAP 6 |
| 33 | Implementation | Audit team meeting | ✅ `meeting_type=team` | — |
| 34 | Implementation | Exit meeting minutes + attendance | ✅ `meeting_type=exit` | — |
| 35 | Implementation | Draft audit report + auditee responses | ⚠️ `AuditReportsPage` + `AuditFindingsPage` present; but auditee/management response capture panel and finding finalize action absent | FE-GAP 14 |
| 35a | Implementation | LA sets risk scoring on findings | ✅ `CreateRiskAssessmentDialog` (6 factor scores + `auto_risk_score` display) | — |
| 36 | Implementation | IA + CIA review/approve draft report | ✅ WO console in `AuditReportsPage` | — |
| 37 | Implementation | Print + distribute final report | ⚠️ `distributeAuditReport` present; no letter/PDF generation | — |
| 38 | Implementation | Final report + signed declaration combined | ⚠️ Both exist; no co-rendering | — |
| 39 | Monitoring | Track, escalation, 5-day enforcement | ⚠️ Monitoring page + notify/non-responsive buttons exist; follow-up cycle UI missing | FE-GAP 2, 3, 7 |
| 40 | Risk/Universe | Auto-generate prioritized plan | ⚠️ `generateDraftPlan()` exists in service, no button wired in any page | FE-GAP 11 |
| 41 | Integration | Risk Management System sync | ❌ Deferred (GAP-B, blocked by Risk Mgmt service) | — |

**Frontend coverage: 27/41 fully covered, 10/41 partial, 4/41 absent = ~66% SRS-compliant** *(backend is ~96%; frontend is the gap)*

---

## 3. Audit Method & Scope

### Files Audited

| Layer | Files |
|---|---|
| API service | `apps/staff-portal/src/services/grcService.ts` (1,542 lines) |
| TypeScript types | `apps/staff-portal/src/types/grc.ts` (1,161 lines) |
| Pages | `apps/staff-portal/src/pages/grc/` (32 `.tsx` files) |
| Components | `apps/staff-portal/src/components/grc/` (50+ `.tsx` files) |
| Hooks | `apps/staff-portal/src/hooks/` (28 hook files, 10 GRC-specific) |

### Audit Approach

1. Extracted complete function list from `grcService.ts` (grep on `^export`)
2. Cross-referenced against actual backend URL patterns in `apps/api/urls/audit.py`
3. Read key page/component/hook files for field-level accuracy
4. Compared TypeScript interface definitions against backend model fields

### Backend URL Baseline (complete endpoint inventory)

All endpoints are under the `audit/` prefix routed through `grcClient`:

```
# Universe & Plans
universe/                                   GET, POST
universe/<pk>/                              GET, PUT, PATCH, DELETE
universe/<pk>/submit/                       POST
universe/<pk>/approve/                      POST
universe/<pk>/workflow-status/              GET
plans/                                      GET, POST
plans/<pk>/                                 GET, PUT, PATCH, DELETE
plans/<pk>/submit/                          POST
plans/<pk>/approve/                         POST
plans/<pk>/workflow-status/                 GET

# Engagements
engagements/                                GET, POST
engagements/<pk>/                           GET, PUT, PATCH, DELETE
engagements/<pk>/transition/                POST  ← start workflow
engagements/<pk>/workflow-status/           GET
engagements/<pk>/workflow-history/          GET

# Findings & Recommendations
findings/                                   GET, POST
findings/<pk>/                              GET, PUT, PATCH, DELETE
findings/<pk>/update-status/                POST
recommendations/                            GET, POST
recommendations/<pk>/                       GET, PUT, PATCH, DELETE
recommendations/<pk>/update-status/         POST

# Implementation Monitoring
implementation-monitoring/                  GET, POST
implementation-monitoring/<pk>/             GET, PUT, PATCH, DELETE
implementation-monitoring/<pk>/review/      POST  ✅ wired
implementation-monitoring/due-reviews/      GET
implementation-monitoring/<pk>/notify-auditee/  POST  ✅ wired
implementation-monitoring/non-responsive/   POST  ✅ wired
monitoring/                                 GET (read-only legacy)

# Follow-Up Responses  ← ABSENT FROM FRONTEND
follow-up-responses/overdue/               GET   ✗ missing
follow-up-responses/                        GET, POST  ✗ missing
follow-up-responses/<pk>/                   GET, PUT, PATCH, DELETE  ✗ missing
follow-up-responses/<pk>/submit/            POST  ✗ missing
follow-up-responses/<pk>/verify/            POST  ✗ missing
implementation-monitoring/<id>/responses/   GET   ✗ missing

# Working Papers
working-papers/                             GET, POST
working-papers/<pk>/                        GET, PUT, PATCH, DELETE
working-papers/<paper_id>/review/           POST  ✅ wired
working-papers/<pk>/submit-for-approval/    POST  ✅ wired
working-papers/<pk>/workflow-status/        GET   ✅ wired
working-papers/<pk>/workflow-history/       GET   ✅ wired

# Risk Assessments
risk-assessments/                           GET, POST
risk-assessments/<pk>/                      GET, PUT, PATCH, DELETE
risk-assessments/<pk>/submit/               POST  ✅ wired
risk-assessments/<pk>/review/               POST  ✅ wired

# RCM
rcm/                                        GET, POST
rcm/<pk>/                                   GET, PUT, PATCH, DELETE
rcm/<pk>/submit/                            POST  ✗ ABSENT FROM FRONTEND
rcm/<pk>/approve/                           POST  ✗ ABSENT FROM FRONTEND
rcm/<rcm_id>/entries/                       GET, POST  ✅ wired
rcm-entries/<pk>/                           GET, PUT, PATCH, DELETE  ✅ wired

# Audit Programs
programs/                                   GET, POST
programs/<pk>/                              GET, PUT, PATCH, DELETE
programs/<pk>/submit/                       POST  ✅ wired
programs/<pk>/approve/                      POST  ✅ wired

# Quarterly Reports
quarterly-reports/                          GET, POST
quarterly-reports/<pk>/                     GET, PUT, PATCH, DELETE
quarterly-reports/<pk>/update-status/       POST  ✅ wired
quarterly-reports/<pk>/consolidate/         POST  ✅ wired
quarterly-reports/<pk>/engagement-reports/  GET   ✗ ABSENT FROM FRONTEND
quarterly-reports/<pk>/submit-for-approval/ POST  ✗ ABSENT FROM FRONTEND
quarterly-reports/<pk>/workflow-status/     GET   ✗ ABSENT FROM FRONTEND

# Engagement Notifications  ← ENTIRELY ABSENT FROM FRONTEND
engagement-notifications/                   GET, POST  ✗ missing
engagement-notifications/<pk>/              GET, PUT, PATCH, DELETE  ✗ missing
engagement-notifications/<pk>/submit/       POST  ✗ missing
engagement-notifications/<pk>/transmit/     POST  ✗ missing
engagement-notifications/<pk>/workflow-status/  GET  ✗ missing

# Reference / Config
audit-memos/*, declarations/*, surveys/*    ✅ wired (CRUD + sign/submit/approve)
```

---

## 4. What IS Implemented (Frontend Inventory)

### 3.1 Pages (32 files in `pages/grc/`)

| Page File | Feature |
|---|---|
| `AuditUniversePage.tsx` | Audit Universe list |
| `AuditUniverseDetailPage.tsx` | Audit Universe detail + WO console |
| `AuditPlansPage.tsx` | Audit Plans list + WO actions |
| `AuditPlanDetailPage.tsx` | Audit Plan detail |
| `AuditableEntitiesPage.tsx` | Auditable Entities CRUD |
| `EngagementDetailPage.tsx` | Engagement detail + Working Papers + WO console |
| `AuditProgramsPage.tsx` | Audit Programs CRUD (submit + approve ✅) |
| `RiskAssessmentsPage.tsx` | Risk Assessments CRUD + submit/review ✅ |
| `AuditFindingsPage.tsx` | Audit Findings CRUD + status update |
| `AuditRecommendationsPage.tsx` | Audit Recommendations CRUD + status update |
| `AuditMonitoringPage.tsx` | Implementation Monitoring list + notify/non-responsive ✅ |
| `WorkingPaperDetailPage.tsx` | Working Paper detail + review/submit + WO console |
| `AuditReportsPage.tsx` | Audit Reports CRUD + distribute |
| `AuditMeetingsPage.tsx` | Audit Meetings CRUD |
| `AuditMemosPage.tsx` | Audit Memos CRUD + submit/approve ✅ |
| `QuarterlyReportsPage.tsx` | QR list + consolidate + manual status transitions |
| `DeclarationsPage.tsx` | Declarations CRUD + sign ✅ |
| `AuditSurveysPage.tsx` | Audit Surveys CRUD |
| `RiskControlMatrixPage.tsx` | RCM CRUD + entries (submit/approve **missing**) |
| `EngagementPlansPage.tsx` | Engagement Plans list |

### 3.2 `grcService.ts` — Complete Function Inventory (all present ✅)

| Group | Functions Present |
|---|---|
| Audit Universe | `fetchAuditUniverses`, `fetchAuditUniverse`, `createAuditUniverse`, `updateAuditUniverse`, `deleteAuditUniverse`, `submitAuditUniverseForApproval`, `getAuditUniverseWorkflowStatus`, `getAuditUniverseWorkflowHistory` |
| Auditable Entities | `fetchAuditableEntities`, `createAuditableEntity`, `updateAuditableEntity`, `deleteAuditableEntity` |
| Audit Plans | `fetchAuditPlans`, `fetchAuditPlan`, `createAuditPlan`, `updateAuditPlan`, `deleteAuditPlan`, `submitAuditPlanForApproval`, `getAuditPlanWorkflowStatus`, `getAuditPlanWorkflowHistory` |
| Audit Engagements | `fetchAuditEngagements`, `fetchAuditEngagement`, `createAuditEngagement`, `updateAuditEngagement`, `deleteAuditEngagement`, `startEngagementWorkflow`, `getEngagementWorkflowStatus`, `getEngagementWorkflowHistory` |
| Audit Findings | `fetchAuditFindings`, `createAuditFinding`, `updateAuditFinding`, `deleteAuditFinding`, `updateFindingStatus` |
| Recommendations | `fetchAuditRecommendations`, `createAuditRecommendation`, `updateAuditRecommendation`, `deleteAuditRecommendation`, `updateRecommendationStatus` |
| Implementation Monitoring | `fetchAuditMonitoring`, `createImplementationMonitoring`, `updateImplementationMonitoring`, `deleteImplementationMonitoring`, `restoreImplementationMonitoring`, `recordMonitoringReview`, `notifyAuditeeMonitoring`, `markNonResponsiveMonitoring` |
| Working Papers | `fetchEngagementWorkingPapers`, `fetchWorkingPaper`, `createWorkingPaper`, `updateWorkingPaper`, `deleteWorkingPaper`, `reviewWorkingPaper`, `submitWorkingPaperForApproval`, `getWorkingPaperWorkflowStatus`, `getWorkingPaperWorkflowHistory` |
| Risk Assessments | `fetchRiskAssessments`, `fetchRiskAssessment`, `createRiskAssessment`, `updateRiskAssessment`, `deleteRiskAssessment`, `submitRiskAssessment`, `reviewRiskAssessment` |
| RCM | `fetchRCMs`, `fetchRCM`, `createRCM`, `updateRCM`, `deleteRCM`, `fetchRCMEntries`, `createRCMEntry`, `updateRCMEntry`, `deleteRCMEntry` |
| Audit Programs | `fetchAuditPrograms`, `fetchAuditProgram`, `createAuditProgram`, `updateAuditProgram`, `deleteAuditProgram`, `submitAuditProgram`, `approveAuditProgram` |
| Audit Reports | `fetchAuditReports`, `fetchAuditReport`, `createAuditReport`, `updateAuditReport`, `deleteAuditReport`, `updateAuditReportStatus`, `distributeAuditReport` |
| Audit Meetings | `fetchAuditMeetings`, `fetchAuditMeeting`, `createAuditMeeting`, `updateAuditMeeting`, `deleteAuditMeeting`, `updateAuditMeetingStatus` |
| Audit Memos | `fetchAuditMemos`, `fetchAuditMemo`, `createAuditMemo`, `updateAuditMemo`, `deleteAuditMemo`, `submitAuditMemo`, `approveAuditMemo` |
| Quarterly Reports | `fetchQuarterlyReports`, `fetchQuarterlyReport`, `createQuarterlyReport`, `updateQuarterlyReport`, `deleteQuarterlyReport`, `updateQuarterlyReportStatus`, `consolidateQuarterlyReport` |
| Declarations | `fetchDeclarations`, `fetchDeclaration`, `createDeclaration`, `updateDeclaration`, `deleteDeclaration`, `signDeclaration` |
| Audit Surveys | `fetchAuditSurveys`, `fetchAuditSurvey`, `createAuditSurvey`, `updateAuditSurvey`, `deleteAuditSurvey` |
| Evidence | `fetchEvidence`, `uploadEvidence`, `deleteEvidence` |
| Reference Data | FiscalYears, Quarters, AuditSeverities, FindingTypes, RiskRatings, AuditOpinions, Directorates, Departments, Units, Sections, `triggerOrgSync` |
| Dashboard | `fetchAuditDashboardStats`, `generateDraftPlan` |

### 3.3 Hooks Present

`useAuditMutations.ts`, `useAuditUniverses.ts`, `useImplementationMonitoring.ts`,
`useWorkingPapers.ts`, `useQuarterlyReports.ts`, `useDeclarations.ts`,
`useAuditSurveys.ts`, `useRiskControlMatrix.ts`, `useGRCWorkflows.ts`,
`useQuarterlyReports.ts`

---

## 5. Gap Registry

| ID | Title | Severity | Backend Endpoint(s) | Frontend Missing |
|---|---|---|---|---|
| **FE-GAP 1** | Engagement Notifications — entire feature absent | 🔴 CRITICAL | `engagement-notifications/**` (5 endpoints) | TypeScript type, service functions, hooks, page, components |
| **FE-GAP 2** | Auditee Follow-Up Responses — entire feature absent | 🔴 CRITICAL | `follow-up-responses/**` (6 endpoints) | TypeScript type, service functions, hooks, UI in monitoring detail |
| **FE-GAP 3** | `AuditMonitoringDetailDialog` uses stale `implementation_progress` field | 🟡 HIGH | n/a (field rename) | Must read `latest_progress` from follow-up responses; show cycle history |
| **FE-GAP 4** | RCM lifecycle actions missing (submit/approve) | 🟡 HIGH | `rcm/<pk>/submit/`, `rcm/<pk>/approve/` | 2 service functions, buttons on `RiskControlMatrixPage` |
| **FE-GAP 5** | Quarterly Report WO submit-for-approval absent | 🟡 HIGH | `quarterly-reports/<pk>/submit-for-approval/`, `quarterly-reports/<pk>/workflow-status/` | 2 service functions, Submit button on `QuarterlyReportsPage`, QR WO console |
| **FE-GAP 6** | Working paper review — Lead Auditor constraint not enforced in UI | 🟡 HIGH | n/a | Review button must be gated by `workflowStatus.current_assignees` |
| **FE-GAP 7** | Escalation badge not shown in `AuditMonitoringDetailDialog` | 🟢 MEDIUM | n/a | `escalated` field is in type but not rendered in the dialog |
| **FE-GAP 8** | `stamped_document_url` not displayed anywhere | 🟢 LOW | n/a (blocked by GAP-A) | No UI to render the stamped PDF link even when populated |
| **FE-GAP 9** | `EngagementDetailPage` missing embedded sub-entity sections | 🟡 HIGH | n/a | Declarations, Survey, RCM, Audit Program are standalone-only; no engagement-context drill-down |
| **FE-GAP 10** | `AuditSurvey.fraud_risk_assessment` JSONField absent | 🟡 HIGH | `audit/surveys/` (field exists in backend model) | TypeScript type, form dialog, and display all missing the fraud risk assessment structure |
| **FE-GAP 11** | `generateDraftPlan` not wired to any UI button | 🟡 HIGH | `audit/plans/generate-draft/` | Function exists in `grcService.ts` but no button in `AuditPlansPage` or `AuditUniverseDetailPage` |
| **FE-GAP 12** | Audit team member assignment absent from engagement dialog | 🟡 HIGH | `audit/engagements/<pk>/team/` | `team_members` field missing from `AuditEngagement` type; no team picker in `CreateAuditEngagementDialog`; no team display in `EngagementDetailPage` |
| **FE-GAP 13** | Evidence file uploads not wired to any page | 🟡 HIGH | `audit/risk-assessments/<pk>/evidence/**` | `uploadEvidence`, `fetchEvidence`, `deleteEvidence` exist in `grcService.ts` but unused; `EvidenceAttachment` type missing; only a plain text `verification_evidence` string is used |
| **FE-GAP 14** | `AuditFinding` lifecycle actions missing (respond + finalize) | 🟡 HIGH | `findings/<pk>/responses/`, `findings/<pk>/finalize/` | No auditee/management response panel; no draft→discussed→final transition buttons in `AuditFindingsPage` |
| **FE-GAP 15** | `AuditSurvey` missing "Mark Complete" action | 🟡 HIGH | `surveys/<pk>/complete/` | Status badge shown but no button to transition `draft → completed`; `completeSurvey()` function absent from `grcService.ts` |

---

## 6. FE-GAP 1: Engagement Notifications

### SRS Requirement

**Process 2 — Audit Engagement Lifecycle, Req 23:**  
> The system shall allow the auditors to create an Engagement Notification letter before fieldwork begins. The notification must be transmitted to the auditee and the system shall record the transmittal event.

### Backend Status

**100% implemented.** Five endpoints registered in `apps/api/urls/audit.py`:

```python
path("engagement-notifications/",              EngagementNotificationListCreateView, ...)
path("engagement-notifications/<pk>/",         EngagementNotificationDetailView, ...)
path("engagement-notifications/<pk>/submit/",  EngagementNotificationSubmitView, ...)
path("engagement-notifications/<pk>/transmit/",EngagementNotificationTransmitView, ...)
path("engagement-notifications/<pk>/workflow-status/", EngagementNotificationWorkflowStatusView, ...)
```

The `EngagementNotification` model (`apps/core/models/audit_entities.py`) has fields including `engagement`, `subject`, `body`, `status`, `transmitted_at`, `transmitted_by`, `stamped_document_url`.

### Frontend Status

**0% implemented.** Verified by:

```bash
grep -n "engagementNotif\|engagement-notification\|EngagementNotification" \
  frontend/apps/staff-portal/src/services/grcService.ts
# → 0 results

grep -n "EngagementNotification" \
  frontend/apps/staff-portal/src/types/grc.ts
# → 0 results
```

### What is Missing

| Layer | Item | Status |
|---|---|---|
| `types/grc.ts` | `interface EngagementNotification { ... }` | ✗ ABSENT |
| `types/grc.ts` | `interface EngagementNotificationFormData { ... }` | ✗ ABSENT |
| `grcService.ts` | `fetchEngagementNotifications(engagementId)` | ✗ ABSENT |
| `grcService.ts` | `createEngagementNotification(data)` | ✗ ABSENT |
| `grcService.ts` | `updateEngagementNotification(id, data)` | ✗ ABSENT |
| `grcService.ts` | `deleteEngagementNotification(id)` | ✗ ABSENT |
| `grcService.ts` | `submitEngagementNotification(id)` | ✗ ABSENT |
| `grcService.ts` | `transmitEngagementNotification(id)` | ✗ ABSENT |
| `grcService.ts` | `getEngagementNotificationWorkflowStatus(id)` | ✗ ABSENT |
| Hooks | `useEngagementNotifications.ts` | ✗ ABSENT |
| Pages | `EngagementNotificationsPage.tsx` | ✗ ABSENT |
| Components | `CreateEngagementNotificationDialog.tsx` | ✗ ABSENT |
| Components | `EngagementNotificationDetailDialog.tsx` | ✗ ABSENT |
| Components | `EngagementNotificationTransmitDialog.tsx` | ✗ ABSENT |
| `EngagementDetailPage.tsx` | Embedded EN section (similar to Working Papers section) | ✗ ABSENT |
| Routing | Route to `EngagementNotificationsPage` | ✗ ABSENT |

---

## 7. FE-GAP 2: Auditee Follow-Up Responses

### SRS Requirement

**Process 3 — Recommendation Implementation Monitoring, Req 31–34:**  
> The system shall record the auditee response per monitoring cycle. Each review cycle generates one `AuditeeFollowUpResponse` row. The auditee submits their response; the CIA/Senior Auditor verifies it.

### Backend Status

**100% implemented.** Six endpoints, model with `cycle_number`, `status` (`pending_response`, `response_submitted`, `verified`, `overdue`), plus `submitted_by`, `verified_by`, `response_deadline`.

```python
path("follow-up-responses/overdue/",           AuditeeFollowUpResponseOverdueView, ...)
path("follow-up-responses/",                   AuditeeFollowUpResponseListCreateView, ...)
path("follow-up-responses/<pk>/",              AuditeeFollowUpResponseDetailView, ...)
path("follow-up-responses/<pk>/submit/",       AuditeeFollowUpResponseSubmitView, ...)
path("follow-up-responses/<pk>/verify/",       AuditeeFollowUpResponseVerifyView, ...)
path("implementation-monitoring/<id>/responses/", AuditeeFollowUpResponseListCreateView, ...)
```

### Frontend Status

**0% implemented.** Verified:

```bash
grep -n "follow.up.response\|followUpRespons\|AuditeeFollowUp" \
  frontend/apps/staff-portal/src/services/grcService.ts
# → 0 results
```

### What is Missing

| Layer | Item | Status |
|---|---|---|
| `types/grc.ts` | `interface AuditeeFollowUpResponse { ... }` | ✗ ABSENT |
| `grcService.ts` | `fetchFollowUpResponses(monitoringId)` | ✗ ABSENT |
| `grcService.ts` | `createFollowUpResponse(monitoringId, data)` | ✗ ABSENT |
| `grcService.ts` | `verifyFollowUpResponse(id, data)` | ✗ ABSENT |
| `grcService.ts` | `fetchOverdueFollowUpResponses()` | ✗ ABSENT |
| `useImplementationMonitoring.ts` | `useFollowUpResponses(monitoringId)` query | ✗ ABSENT |
| `useImplementationMonitoring.ts` | `useVerifyFollowUpResponse()` mutation | ✗ ABSENT |
| `AuditMonitoringDetailDialog.tsx` | Follow-up cycle history section | ✗ ABSENT |
| `AuditMonitoringDetailDialog.tsx` | "Verify Response" action button | ✗ ABSENT |
| `AuditMonitoringPage.tsx` | Cycle history tab/expandable row | ✗ ABSENT |

---

## 8. FE-GAP 3: AuditMonitoringDetailDialog — Stale Progress Field

### Issue

`AuditMonitoringDetailDialog.tsx` lines 25–27 read:

```typescript
const progress = item.implementation_progress !== undefined && item.implementation_progress !== null
  ? `${item.implementation_progress}%`
  : '0%';
const status = progress === '0%' ? 'Not started' : progress === '100%' ? 'Completed' : 'In Progress';
```

This references `implementation_progress` — a field that was the **old direct field** on `AuditMonitoringItem`. After the backend's P2-GAP 4 fix, implementation progress is now tracked **per-cycle** through the `AuditeeFollowUpResponse` model. The current progress is returned as `latest_progress` from the monitoring detail endpoint.

### TypeScript Type Issue

`types/grc.ts` line 206:

```typescript
export interface AuditMonitoringItem {
  ...
  implementation_progress?: string | number;    // ← OLD field, may still be serialized by backend
  ...
  escalated?: boolean;                          // ✅ present
  response_deadline?: string | null;            // ✅ present
  // MISSING: latest_progress, follow_up_responses, current_cycle_number
}
```

The type does NOT declare:
- `latest_progress?: string | null` — the most recent follow-up response progress
- `follow_up_responses?: AuditeeFollowUpResponse[]` — nested cycle history
- `current_cycle_number?: number` — how many cycles have run

### Downstream Effect

The Detail Dialog computes status from `0%` / `100%` string comparisons instead of:
1. Checking `item.escalated` for a visual alert
2. Showing latest follow-up cycle's `implementation_progress`
3. Listing all past cycles with status badges

---

## 9. FE-GAP 4: RCM Lifecycle Actions Missing

### SRS Requirement

**Process 2 — Audit Engagement, Req 18 (Risk Control Matrix):**  
> The RCM shall be reviewed and approved by the Lead Auditor before fieldwork proceeds. The status lifecycle is `draft → reviewed → approved`.

### Backend Status

Two endpoints exist:

```
POST  audit/rcm/<pk>/submit/   → RCMSubmitView   → sets status to 'reviewed'
POST  audit/rcm/<pk>/approve/  → RCMApproveView  → sets status to 'approved' (CIA role)
```

The `RiskControlMatrix` type already has `status: 'draft' | 'reviewed' | 'approved'`.

### Frontend Gap

```bash
grep -n "submitRCM\|approveRCM\|rcm.*submit\|rcm.*approve" \
  frontend/apps/staff-portal/src/services/grcService.ts
# → 0 results
```

No `submitRCMForReview(id)` or `approveRCM(id)` service functions exist.
`RiskControlMatrixPage.tsx` has no "Submit for Review" or "Approve" buttons.

### What is Missing

| Item | Detail |
|---|---|
| `grcService.ts` | `submitRCMForReview(id: string): Promise<RiskControlMatrix>` |
| `grcService.ts` | `approveRCM(id: string): Promise<RiskControlMatrix>` |
| Hooks | `useSubmitRCMForReview()` and `useApproveRCM()` mutations in `useRiskControlMatrix.ts` |
| `RiskControlMatrixPage.tsx` | "Submit for Review" button (draft → reviewed) |
| `RiskControlMatrixPage.tsx` | "Approve" button (reviewed → approved, CIA role) |

---

## 10. FE-GAP 5: Quarterly Report WO Submit-for-Approval

### Issue

`QuarterlyReportsPage.tsx` uses a **purely manual status transition** via `updateQuarterlyReportStatus`:

```typescript
const QR_TRANSITIONS: Record<string, string[]> = {
  draft: ['cia_review'],
  cia_review: ['management_review', 'draft'],
  management_review: ['committee_review', 'draft'],
  committee_review: ['approved', 'improvement_required'],
  ...
};
```

This **bypasses** the Work Orchestration engine. The backend has:

```
POST  audit/quarterly-reports/<pk>/submit-for-approval/  → QuarterlyReportSubmitView
GET   audit/quarterly-reports/<pk>/workflow-status/      → QuarterlyReportWorkflowStatusView
```

The `grc.quarterly_report_approval` WO template (if loaded) drives the multi-stage approval chain. The frontend currently hard-codes transitions instead of letting the WO engine drive them.

Additionally, `quarterly-reports/<pk>/engagement-reports/` is never called — this endpoint returns the constituent engagement audit reports that feed into a quarterly rollup.

### What is Missing

| Item | Detail |
|---|---|
| `grcService.ts` | `submitQuarterlyReportForApproval(id)` → `POST quarterly-reports/<pk>/submit-for-approval/` |
| `grcService.ts` | `getQuarterlyReportWorkflowStatus(id)` → `GET quarterly-reports/<pk>/workflow-status/` |
| `grcService.ts` | `fetchQuarterlyReportEngagementReports(id)` → `GET quarterly-reports/<pk>/engagement-reports/` |
| Hooks | `useSubmitQuarterlyReportForApproval()`, `useQuarterlyReportWorkflowStatus()` |
| `QuarterlyReportsPage.tsx` | "Submit for Approval" button (replaces or supplements manual transitions) |
| `QuarterlyReportsPage.tsx` | `EmbeddedWorkflowConsole` for the QR approval chain |
| `QuarterlyReportDetailDialog` | Constituent engagement reports section |

---

## 11. FE-GAP 6: Working Paper Review — Lead Auditor Constraint Not Enforced

### Backend Fix (P2-GAP 6 — resolved)

`grc.working_paper_approval` WO template Stage 1 now assigns to `{{lead_auditor}}` only:

```yaml
stages:
  - id: 1
    name: "Lead Auditor Review"
    assignees: ["{{lead_auditor}}"]
```

Context is injected from `WorkingPaper.get_workflow_context()` which returns `"lead_auditor": str(self.engagement.lead_auditor)`.

### Frontend Gap

`WorkingPaperDetailPage.tsx` (and its parent hooks) calls `reviewWorkingPaper(id, data)` — which POSTs to `working-papers/<paper_id>/review/`. **The UI does not check whether the current user is the WO-assigned reviewer** before showing the "Review" button.

Any authenticated staff user currently sees the review button. After the P2-GAP 6 fix, the backend will reject non-LA reviews (the WO engine enforces this), but the UX is poor — users get an error instead of seeing the button only when they are the assigned reviewer.

### Fix

In `WorkingPaperDetailPage.tsx`, gate the Review button:

```typescript
const { data: workflowStatus } = useGRCWorkflowStatus('working-papers', workingPaperId);
const currentUserId = useCurrentUser()?.id;
const isAssignedReviewer = workflowStatus?.current_stage?.assignees?.includes(currentUserId);

// Only show review button if user is the assigned reviewer
{isAssignedReviewer && (
  <Button onClick={handleReview}>Review Working Paper</Button>
)}
```

---

## 12. FE-GAP 7: Escalation Badge Not Shown in Monitoring Detail

### Issue

- `AuditMonitoringItem` TypeScript type **has** `escalated?: boolean` (line 216 of `types/grc.ts`) ✅
- `AuditMonitoringPage.tsx` line 128 uses `escalated` for **list filtering** ✅
- `AuditMonitoringDetailDialog.tsx` — **does NOT display any escalation badge or alert**

When `monitoring_deadlines.py` escalates a record to the CIA (`escalated = True`), the detail dialog shows no visual indicator. Staff opening the dialog see no sign that the record has been escalated.

### Fix

Add to `AuditMonitoringDetailDialog.tsx` in the header badge section:

```tsx
{item.escalated && (
  <Badge variant="destructive" className="flex items-center gap-1">
    <AlertTriangle className="h-3 w-3" />
    Escalated to CIA
  </Badge>
)}
```

---

## 13. FE-GAP 8: Stamped Document URL Not Displayed

### Issue

- `AuditProgram.stamped_document_url` is typed in `types/grc.ts` line ~1146
- Backend populates this field after CIA approval + DRS PDF stamping (pending GAP-A)
- No UI exists to display a link to the stamped PDF anywhere

This is marked **LOW priority** because the backend GAP-A (PDF stamping hook) is not yet implemented — `stamped_document_url` will always be `null` until GAP-A is resolved. However the UI should be scaffolded now so it auto-activates when GAP-A lands.

### Models with `stamped_document_url`

- `AuditProgram` ✅ typed in frontend
- `RiskControlMatrix` — **not yet typed** in `RiskControlMatrix` interface
- `EngagementNotification` — blocked by FE-GAP 1
- `WorkingPaper` — not yet typed
- `QuarterlyAuditReport` — not yet typed

---

## 14. FE-GAP 9: EngagementDetailPage Missing Sub-Entity Sections

### Issue

The `EngagementDetailPage.tsx` currently embeds **only one sub-entity**: Working Papers (lines 272–356). All other engagement-scoped entities are exclusively accessible via their own standalone pages where the user must manually select the engagement from a dropdown.

The SRS treats the following as belonging **inside** the engagement lifecycle context:

| Entity | SRS Step | Current Access | Should Be |
|---|---|---|---|
| `DeclarationOfIndependence` | Req 16 — team signs before fieldwork | Standalone `DeclarationsPage` | Embedded in `EngagementDetailPage` |
| `AuditSurvey` | Req 19 — preliminary survey per engagement | Standalone `AuditSurveysPage` | Embedded in `EngagementDetailPage` |
| `RiskControlMatrix` | Req 22 — developed per engagement | Standalone `RiskControlMatrixPage` | Embedded in `EngagementDetailPage` |
| `AuditProgram` | Req 15, 23 — per engagement | Standalone `AuditProgramsPage` | Embedded in `EngagementDetailPage` |
| `EngagementNotification` | Req 24–26 | Missing entirely | Embedded in `EngagementDetailPage` (FE-GAP 1) |

This is not just a UX concern — it means auditors must:
1. Leave the engagement detail
2. Navigate to e.g. `DeclarationsPage`
3. Manually re-select the same engagement in the dropdown

This breaks the SRS's implied sequential flow: *Engagement → Memo → Declaration → Survey → RCM → Program → EN → Fieldwork*.

### Fix Pattern

Use the same pattern as the Working Papers section already in `EngagementDetailPage.tsx` (lines 272–356):

```tsx
// 1. Add state and mutations for each entity
const [isDeclarationOpen, setIsDeclarationOpen] = useState(false);

// 2. Query scoped to the engagement
const { data: declarations } = useDeclarations({ engagement_id: engagementId });

// 3. Compact section card (like the WP card)
<Card>
  <CardHeader className="pb-3">
    <CardTitle>Declarations of Independence
      <Badge variant="outline">{declarations?.results?.length ?? 0}</Badge>
    </CardTitle>
  </CardHeader>
  <CardContent>
    {declarations?.results?.map((d) => (
      <div key={d.id} className="flex justify-between p-2 border rounded text-sm">
        <span>{d.reference_number}</span>
        <Badge variant={d.is_signed ? 'secondary' : 'outline'}>
          {d.is_signed ? 'Signed' : 'Unsigned'}
        </Badge>
      </div>
    ))}
    <Button size="sm" onClick={() => setIsDeclarationOpen(true)}>Add Declaration</Button>
  </CardContent>
</Card>
```

---

## 15. FE-GAP 10: AuditSurvey Missing Fraud Risk Assessment Field

### SRS Requirement

**Req 19:** *The system shall support a Preliminary Survey + Fraud Risk Assessment before fieldwork begins.*

### Backend Status

`AuditSurvey` model has `fraud_risk_assessment = JSONField(default=list)` storing structured records:

```python
# Each entry:
{
  "risk_factor": str,
  "likelihood": "low" | "medium" | "high",
  "impact": str,
  "mitigating_controls": str
}
```

### Frontend Gap

The `AuditSurvey` TypeScript interface (`types/grc.ts` lines 1035–1053) does **not** include `fraud_risk_assessment`. Verified:

```typescript
export interface AuditSurvey {
  id: string;
  title: string;
  survey_type: string;
  status: 'draft' | 'active' | 'closed';
  questions?: Record<string, unknown>[];  // generic, not fraud-specific
  // ← NO fraud_risk_assessment field
}
```

The `CreateAuditSurveyDialog` survey types are only `pre_engagement` and `post_engagement` — there is no `fraud_risk_assessment` type option, and no UI to build the structured risk factor list.

### What is Missing

| Item | Detail |
|---|---|
| `types/grc.ts` | Add `fraud_risk_assessment?: FraudRiskFactor[]` to `AuditSurvey` |
| `types/grc.ts` | Add `interface FraudRiskFactor { risk_factor: string; likelihood: 'low'\|'medium'\|'high'; impact: string; mitigating_controls?: string; }` |
| `CreateAuditSurveyDialog.tsx` | Add survey type option `fraud_risk_assessment` |
| `CreateAuditSurveyDialog.tsx` | When `survey_type === 'fraud_risk_assessment'`: show dynamic row-builder for risk factors (risk_factor text, likelihood select, impact text, mitigating_controls text) |
| Survey detail view | Display fraud risk assessment rows in a table |

---

## 16. FE-GAP 11: Generate Draft Plan Not Wired

### SRS Requirement

**Req 40:** *The system shall auto-generate a prioritized RBIAP draft from approved risk assessment scores.*

### Backend Status

Endpoint: `POST audit/plans/generate-draft/` — accepts `{ fiscal_year_id, universe_id? }`, returns a new draft `AuditPlan` populated from risk assessment rankings.

Service function: `generateDraftPlan()` exists in `grcService.ts` line ~1228.

### Frontend Gap

No page calls `generateDraftPlan()`. Verified:

```bash
grep -rn "generateDraftPlan\|generate.draft" apps/staff-portal/src/pages/grc/
# → 0 results
```

The `AuditPlansPage.tsx` and `AuditUniverseDetailPage.tsx` both have "Create Plan" buttons that open `CreateAuditPlanDialog` (manual form fill). There is no "Auto-Generate from Risk Scores" button anywhere.

### Fix

In `AuditPlansPage.tsx` header, add a secondary button next to "Create Plan":

```tsx
<Button variant="outline" onClick={handleGenerateDraft}>
  <Wand2 className="mr-2 h-4 w-4" />
  Auto-Generate from Risk Scores
</Button>
```

With a confirmation dialog to select `fiscal_year_id`:

```typescript
const generateMutation = useMutation({
  mutationFn: (data: { fiscal_year_id: string; universe_id?: string }) =>
    grcService.generateDraftPlan(data),
  onSuccess: (plan) => {
    queryClient.invalidateQueries({ queryKey: ['audit-plans'] });
    toast.success('Draft plan generated', {
      description: `${plan.reference_number} — ${plan.auditable_entities_count} entities ranked`,
    });
  },
});
```

---

## 17. FE-GAP 12: Audit Team Member Assignment Not Exposed

### SRS Requirement

**Req 10:** *The CIA appoints a Lead Auditor and assigns team members to each engagement.*

### Backend Status

`AuditEngagement` model has `team_members` JSONField (format: `[{"user_id": "uuid", "role": "lead_auditor|team_member", "name": "Full Name"}]`).

Endpoint: `PUT/PATCH audit/engagements/<pk>/` accepts `team_members` in the request body.

Backend also exposes `GET/POST/DELETE audit/engagements/<pk>/team/` for fine-grained team management.

### Frontend Gap

1. `AuditEngagement` TypeScript type in `types/grc.ts` does **not** include a `team_members` field. Only `lead_auditor: string` is present.
2. `CreateAuditEngagementDialog.tsx` has no team member picker — only `lead_auditor` (single text/select field).
3. No page shows the engagement team composition (member names + roles).

Verified:
```bash
grep -n "team_members\|TeamMember" apps/staff-portal/src/types/grc.ts
# → Only declarant_role 'team_member' appears — NOT a field on AuditEngagement

grep -rn "team_member\|teamMember" apps/staff-portal/src/components/grc/CreateAuditEngagementDialog.tsx
# → 0 results
```

### Fix

**1. Add `team_members` to the `AuditEngagement` type:**

```typescript
// types/grc.ts
export interface AuditEngagementTeamMember {
  user_id: string;
  role: 'lead_auditor' | 'team_member';
  name: string;
}

export interface AuditEngagement {
  // ...existing fields...
  lead_auditor: string;
  team_members: AuditEngagementTeamMember[];
}
```

**2. Add team member management to `CreateAuditEngagementDialog.tsx`:**

```tsx
// Dynamic list — add/remove team member rows
const [teamMembers, setTeamMembers] = useState<AuditEngagementTeamMember[]>([]);

// In the form JSX:
<div>
  <Label>Team Members</Label>
  {teamMembers.map((member, idx) => (
    <div key={idx} className="flex gap-2 mt-1">
      <Input
        placeholder="Full Name"
        value={member.name}
        onChange={(e) => updateTeamMember(idx, 'name', e.target.value)}
      />
      <Select
        value={member.role}
        onValueChange={(val) => updateTeamMember(idx, 'role', val)}
      >
        <SelectItem value="team_member">Team Member</SelectItem>
        <SelectItem value="lead_auditor">Lead Auditor</SelectItem>
      </Select>
      <Button variant="ghost" size="sm" onClick={() => removeTeamMember(idx)}>
        <X className="h-4 w-4" />
      </Button>
    </div>
  ))}
  <Button variant="outline" size="sm" onClick={addTeamMember} className="mt-2">
    <Plus className="mr-2 h-4 w-4" /> Add Member
  </Button>
</div>
```

**3. Display team in `EngagementDetailPage.tsx`:**

```tsx
<div className="mt-4">
  <h4 className="font-medium">Audit Team</h4>
  <ul className="mt-2 space-y-1">
    {engagement.team_members?.map((m) => (
      <li key={m.user_id} className="flex items-center gap-2 text-sm">
        <Badge variant={m.role === 'lead_auditor' ? 'default' : 'secondary'}>
          {m.role === 'lead_auditor' ? 'Lead Auditor' : 'Team Member'}
        </Badge>
        {m.name}
      </li>
    ))}
  </ul>
</div>
```

**Effort:** ~2h

---

## 18. FE-GAP 13: Evidence File Uploads Not Wired to Any Page

### SRS Requirement

**Req 28:** *Fieldwork — team documents results with evidence (workpapers, risk assessments).*  
**Req 30:** *Working papers collect all supporting documentation.*

### Backend Status

`EvidenceAttachment` model with DRS integration (stores files via document-records-service).

Endpoints:
- `POST   audit/risk-assessments/<pk>/evidence/` — upload file
- `GET    audit/risk-assessments/<pk>/evidence/` — list attachments
- `DELETE audit/risk-assessments/<pk>/evidence/<evid_pk>/` — remove

### Frontend Gap

`grcService.ts` already defines the service functions:

```typescript
// grcService.ts (lines ~1243-1276) — EXISTS but UNUSED
uploadEvidence(riskAssessmentId: string, file: File, description?: string): Promise<EvidenceAttachment>
fetchEvidence(riskAssessmentId: string): Promise<EvidenceAttachment[]>
deleteEvidence(riskAssessmentId: string, evidenceId: string): Promise<void>
```

No GRC page calls any of these functions. `AuditRecommendationsPage.tsx` uses only a plain text field `verification_evidence` (a string summary), not actual file attachments.

Verified:
```bash
grep -rn "uploadEvidence\|fetchEvidence\|EvidenceAttach" apps/staff-portal/src/pages/ apps/staff-portal/src/components/
# → 0 results
```

### The `EvidenceAttachment` type is also absent from `types/grc.ts`

### Fix

**1. Add type to `types/grc.ts`:**

```typescript
export interface EvidenceAttachment {
  id: string;
  risk_assessment: string;
  file_name: string;
  file_url: string;
  description: string;
  uploaded_by: string;
  uploaded_at: string;
  file_size: number;
}
```

**2. Create `components/grc/EvidenceAttachmentSection.tsx`** (reusable component):

```tsx
interface EvidenceAttachmentSectionProps {
  riskAssessmentId: string;
  readonly?: boolean;
}

export function EvidenceAttachmentSection({ riskAssessmentId, readonly }: EvidenceAttachmentSectionProps) {
  const { data: evidence, refetch } = useQuery({
    queryKey: ['evidence', riskAssessmentId],
    queryFn: () => grcService.fetchEvidence(riskAssessmentId),
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, description }: { file: File; description: string }) =>
      grcService.uploadEvidence(riskAssessmentId, file, description),
    onSuccess: () => refetch(),
  });

  return (
    <div>
      <h4 className="font-medium">Supporting Evidence</h4>
      <ul className="mt-2 space-y-1">
        {evidence?.map((e) => (
          <li key={e.id} className="flex items-center justify-between text-sm">
            <a href={e.file_url} target="_blank" rel="noreferrer" className="underline">
              {e.file_name}
            </a>
            {!readonly && (
              <Button variant="ghost" size="sm" onClick={() => grcService.deleteEvidence(riskAssessmentId, e.id)}>
                <Trash2 className="h-3 w-3" />
              </Button>
            )}
          </li>
        ))}
      </ul>
      {!readonly && (
        <EvidenceUploadDropzone onUpload={(file, desc) => uploadMutation.mutate({ file, description: desc })} />
      )}
    </div>
  );
}
```

**3. Use `EvidenceAttachmentSection` in `RiskAssessmentsPage.tsx` detail panel and `WorkingPaperDetailPage.tsx`.**

**Effort:** ~3h

---

## 19. FE-GAP 14: AuditFinding Lifecycle Actions Missing

### SRS Requirement

**Req 35:** *Draft audit report includes findings with auditee responses and management commitment.*  
**Req 29:** *LA reviews working papers for completeness before pre-exit meeting.*

### Backend Status

Two endpoints handle finding lifecycle:
- `POST audit/findings/<pk>/finalize/` — transitions `draft → discussed → final`. The `final` status requires `auditee_response` to be non-empty.
- `PATCH audit/findings/<pk>/responses/` — updates `auditee_response` and `management_response` text fields.

Finding states: `draft` → `discussed` → `final`.

### Frontend Gap

`AuditFindingsPage.tsx` has create/edit/delete CRUD but **no lifecycle action buttons**. Verified:

```bash
grep -n "finalize\|auditee_response\|management_response\|discussed\|FinalizeFind" \
  apps/staff-portal/src/pages/grc/AuditFindingsPage.tsx
# → Only: warning text "This is a finalized finding" in delete dialog
#   No buttons for draft→discussed or discussed→final transitions
#   No response capture form/panel
```

Without these, findings are stuck in `draft` status and cannot be finalized for inclusion in the audit report.

### Fix

**1. Add service functions to `grcService.ts`:**

```typescript
/** POST /findings/{id}/finalize/ */
export async function finalizeFinding(
  id: string,
  targetStatus: 'discussed' | 'final'
): Promise<AuditFinding> {
  return grcClient.post(
    `${ensureTrailingSlash(API_PATHS.findings)}${id}/finalize/`,
    { target_status: targetStatus }
  );
}

/** PATCH /findings/{id}/responses/ */
export async function updateFindingResponses(
  id: string,
  responses: { auditee_response?: string; management_response?: string }
): Promise<AuditFinding> {
  return grcClient.patch(
    `${ensureTrailingSlash(API_PATHS.findings)}${id}/responses/`,
    responses
  );
}
```

**2. Add lifecycle buttons in `AuditFindingsPage.tsx` row actions (or detail panel):**

```tsx
// Status transitions
{finding.status === 'draft' && (
  <Button size="sm" onClick={() => finalizeMutation.mutate({ id: finding.id, targetStatus: 'discussed' })}>
    Mark Discussed
  </Button>
)}
{finding.status === 'discussed' && finding.auditee_response && (
  <Button size="sm" variant="default" onClick={() => finalizeMutation.mutate({ id: finding.id, targetStatus: 'final' })}>
    Finalize
  </Button>
)}

// Auditee / management response panel (collapsible in row detail)
<div>
  <Label>Auditee Response</Label>
  <Textarea
    value={finding.auditee_response || ''}
    onChange={(e) => setResponseDraft(e.target.value)}
    placeholder="Enter auditee management response..."
  />
  <Button size="sm" onClick={() => responsesMutation.mutate({ id: finding.id, auditee_response: responseDraft })}>
    Save Response
  </Button>
</div>
```

**Effort:** ~2.5h

---

## 20. FE-GAP 15: AuditSurvey Missing "Mark Complete" Action

### SRS Requirement

**Req 19:** *The system shall support preliminary survey capturing risk environment and fraud risk assessment.*  
**Req 22:** *LA develops RCM and prepares draft audit program from survey results.*

### Backend Status

`POST audit/surveys/<pk>/complete/` — transitions survey from `draft` → `completed`, publishes `SURVEY_COMPLETED` event that triggers downstream engagement lifecycle logic.

### Frontend Gap

`AuditSurveysPage.tsx` renders a status badge but has no "Mark Complete" button. Verified:

```bash
grep -n "complete\|Complete\|status" apps/staff-portal/src/pages/grc/AuditSurveysPage.tsx
# → Only `getStatusColor(item.status)` and a status badge rendering
# → No action button for completing a survey
```

Without this, surveys remain in `draft` status indefinitely.

### Fix

**1. Add service function to `grcService.ts`:**

```typescript
/** POST /surveys/{id}/complete/ */
export async function completeSurvey(id: string): Promise<AuditSurvey> {
  return grcClient.post(
    `${ensureTrailingSlash(API_PATHS.surveys)}${id}/complete/`
  );
}
```

**2. Add button in `AuditSurveysPage.tsx` row actions:**

```tsx
{survey.status === 'draft' && (
  <Button
    size="sm"
    onClick={() => completeMutation.mutate(survey.id)}
    disabled={completeMutation.isPending}
  >
    <CheckCircle className="mr-2 h-4 w-4" />
    Mark Complete
  </Button>
)}
```

**Effort:** ~1h

---

## 21. Implementation Guide — FE-GAP 1 (Engagement Notifications)

### Step 1: TypeScript Type (`types/grc.ts`)

Add after the existing `AuditEngagement` section:

```typescript
// ========== Engagement Notification ==========

export interface EngagementNotification {
  id: string;
  reference_number: string;
  engagement: {
    id: string;
    reference_number: string;
    title: string;
    auditable_entity?: { id: string; name: string };
  };
  subject: string;
  body: string;
  status: 'draft' | 'submitted' | 'transmitted';
  transmitted_at?: string | null;
  transmitted_by?: string | null;  // UUID
  stamped_document_url?: string | null;
  /** UUID of the WO plan driving this notification */
  workflow_plan_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface EngagementNotificationFormData {
  engagement_id: string;
  subject: string;
  body: string;
}
```

### Step 2: Service functions (`grcService.ts`)

Add after the `startEngagementWorkflow` function block (~line 410):

```typescript
// ─── Engagement Notifications ───────────────────────────────────────────────

export function fetchEngagementNotifications(
  engagementId: string,
  params?: GRCListParams
) {
  return grcClient.get<AuditCollectionResult<EngagementNotification>>(
    `audit/engagement-notifications/`,
    { params: { engagement_id: engagementId, ...params } }
  ).then((r) => r.data);
}

export async function fetchEngagementNotification(id: string): Promise<EngagementNotification> {
  const r = await grcClient.get<EngagementNotification>(`audit/engagement-notifications/${id}/`);
  return r.data;
}

export async function createEngagementNotification(
  data: EngagementNotificationFormData
): Promise<EngagementNotification> {
  const r = await grcClient.post<EngagementNotification>(`audit/engagement-notifications/`, data);
  return r.data;
}

export async function updateEngagementNotification(
  id: string,
  data: Partial<EngagementNotificationFormData>
): Promise<EngagementNotification> {
  const r = await grcClient.patch<EngagementNotification>(`audit/engagement-notifications/${id}/`, data);
  return r.data;
}

export async function deleteEngagementNotification(id: string): Promise<void> {
  await grcClient.delete(`audit/engagement-notifications/${id}/`);
}

export async function submitEngagementNotification(id: string): Promise<EngagementNotification> {
  const r = await grcClient.post<EngagementNotification>(`audit/engagement-notifications/${id}/submit/`);
  return r.data;
}

export async function transmitEngagementNotification(id: string): Promise<EngagementNotification> {
  const r = await grcClient.post<EngagementNotification>(`audit/engagement-notifications/${id}/transmit/`);
  return r.data;
}

export async function getEngagementNotificationWorkflowStatus(
  id: string
): Promise<WorkflowStatusResponse> {
  const r = await grcClient.get<WorkflowStatusResponse>(
    `audit/engagement-notifications/${id}/workflow-status/`
  );
  return r.data;
}
```

### Step 3: Hook file (`hooks/useEngagementNotifications.ts`)

New file following FIMS pattern (`useDeclarations.ts` is the closest model):

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as grcService from '@staff/services/grcService';

export const engagementNotificationKeys = {
  all: ['engagement-notifications'] as const,
  lists: () => [...engagementNotificationKeys.all, 'list'] as const,
  byEngagement: (engagementId: string) =>
    [...engagementNotificationKeys.lists(), 'engagement', engagementId] as const,
  details: () => [...engagementNotificationKeys.all, 'detail'] as const,
  detail: (id: string) => [...engagementNotificationKeys.details(), id] as const,
};

export function useEngagementNotifications(engagementId: string) {
  return useQuery({
    queryKey: engagementNotificationKeys.byEngagement(engagementId),
    queryFn: () => grcService.fetchEngagementNotifications(engagementId),
    enabled: !!engagementId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateEngagementNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => grcService.createEngagementNotification(data),
    onSuccess: (n) => {
      queryClient.invalidateQueries({
        queryKey: engagementNotificationKeys.byEngagement(n.engagement.id),
      });
      toast.success('Engagement notification created');
    },
    onError: (e: any) => toast.error('Failed to create notification', {
      description: e.response?.data?.error || e.message,
    }),
  });
}

export function useSubmitEngagementNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.submitEngagementNotification(id),
    onSuccess: (n) => {
      queryClient.invalidateQueries({ queryKey: engagementNotificationKeys.all });
      toast.success('Notification submitted for approval');
    },
    onError: (e: any) => toast.error('Failed to submit notification', {
      description: e.response?.data?.error || e.message,
    }),
  });
}

export function useTransmitEngagementNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.transmitEngagementNotification(id),
    onSuccess: (n) => {
      queryClient.invalidateQueries({ queryKey: engagementNotificationKeys.all });
      toast.success('Notification transmitted to auditee', {
        description: `Transmitted at ${new Date(n.transmitted_at!).toLocaleString()}`,
      });
    },
    onError: (e: any) => toast.error('Failed to transmit notification', {
      description: e.response?.data?.error || e.message,
    }),
  });
}
```

### Step 4: Components

Create the following components in `components/grc/`:

**`CreateEngagementNotificationDialog.tsx`** — Dialog with `subject` (text), `body` (textarea), `engagement_id` (hidden/prop). Pattern: copy `CreateAuditMemoDialog.tsx`.

**`EngagementNotificationDetailDialog.tsx`** — Shows notification detail. Includes "Submit" button (draft → submitted), "Transmit" button (submitted → transmitted), EmbeddedWorkflowConsole. Pattern: copy `WorkingPaperDetailPage.tsx` layout compressed into dialog.

**`EngagementNotificationsSection.tsx`** — Mini-list for embedding inside `EngagementDetailPage.tsx`, similar to the existing Working Papers section (lines 293–356 of `EngagementDetailPage.tsx`).

### Step 5: Embed in `EngagementDetailPage.tsx`

Import and add below the Working Papers Card:

```tsx
import { EngagementNotificationsSection } from '@staff/components/grc/EngagementNotificationsSection';

// In the left column:
<EngagementNotificationsSection engagementId={engagementId} />
```

---

## 22. Implementation Guide — FE-GAP 2 (Follow-Up Responses)

### Step 1: TypeScript Type (`types/grc.ts`)

Add after `AuditMonitoringItem`:

```typescript
export interface AuditeeFollowUpResponse {
  id: string;
  monitoring_item: string;              // UUID reference
  cycle_number: number;
  status: 'pending_response' | 'response_submitted' | 'verified' | 'overdue';
  implementation_progress: number;      // 0–100
  response_notes?: string;
  supporting_evidence_url?: string | null;
  response_deadline?: string | null;
  submitted_at?: string | null;
  submitted_by?: string | null;         // UUID
  verified_at?: string | null;
  verified_by?: string | null;          // UUID
  verification_notes?: string;
  created_at: string;
}
```

Also update `AuditMonitoringItem` to add:

```typescript
  latest_progress?: number | null;          // from most recent FollowUpResponse
  current_cycle_number?: number;
  follow_up_responses?: AuditeeFollowUpResponse[];
```

### Step 2: Service functions (`grcService.ts`)

Add after the `markNonResponsiveMonitoring` function:

```typescript
// ─── Follow-Up Responses ────────────────────────────────────────────────────

export async function fetchFollowUpResponses(
  monitoringId: string
): Promise<AuditeeFollowUpResponse[]> {
  const r = await grcClient.get<AuditeeFollowUpResponse[]>(
    `audit/implementation-monitoring/${monitoringId}/responses/`
  );
  return r.data;
}

export async function createFollowUpResponse(
  monitoringId: string,
  data: Partial<AuditeeFollowUpResponse>
): Promise<AuditeeFollowUpResponse> {
  const r = await grcClient.post<AuditeeFollowUpResponse>(
    `audit/implementation-monitoring/${monitoringId}/responses/`,
    data
  );
  return r.data;
}

export async function verifyFollowUpResponse(
  id: string,
  data: { verification_notes?: string }
): Promise<AuditeeFollowUpResponse> {
  const r = await grcClient.post<AuditeeFollowUpResponse>(
    `audit/follow-up-responses/${id}/verify/`,
    data
  );
  return r.data;
}

export async function fetchOverdueFollowUpResponses(): Promise<AuditeeFollowUpResponse[]> {
  const r = await grcClient.get<AuditeeFollowUpResponse[]>(`audit/follow-up-responses/overdue/`);
  return r.data;
}
```

### Step 3: Expand `AuditMonitoringDetailDialog.tsx`

Replace the `implementation_progress` calculation (lines 25–27) and add a cycle history section:

```tsx
// Use latest_progress if available, fall back to implementation_progress (legacy)
const latestProgress = item.latest_progress ?? item.implementation_progress;
const progress = latestProgress !== undefined && latestProgress !== null
  ? `${latestProgress}%`
  : '0%';

// Inside the dialog JSX, add after the Separator:
{item.follow_up_responses && item.follow_up_responses.length > 0 && (
  <>
    <Separator />
    <div>
      <p className="text-sm font-medium text-muted-foreground mb-2">
        Follow-Up Cycles ({item.follow_up_responses.length})
      </p>
      <div className="space-y-2">
        {item.follow_up_responses.map((r) => (
          <div key={r.id} className="flex items-center justify-between p-2 rounded border text-sm">
            <span>Cycle {r.cycle_number}</span>
            <span>{r.implementation_progress}%</span>
            <Badge variant={r.status === 'verified' ? 'secondary' : 'default'}>
              {r.status.replace(/_/g, ' ')}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  </>
)}
```

Also add escalation alert at the top of the dialog:

```tsx
{item.escalated && (
  <Alert variant="destructive" className="mb-2">
    <AlertTriangle className="h-4 w-4" />
    <AlertDescription>This record has been escalated to the CIA.</AlertDescription>
  </Alert>
)}
```

---

## 23. Implementation Guide — FE-GAP 3 (Stale Progress Field)

This is largely fixed by following the instructions in §14 above. Summary of direct changes:

1. `types/grc.ts` — add `latest_progress?: number | null` to `AuditMonitoringItem`
2. `AuditMonitoringDetailDialog.tsx` line 25 — replace `item.implementation_progress` with `item.latest_progress ?? item.implementation_progress`
3. The backend serializer must return `latest_progress` in the monitoring list/detail response (verify in `apps/api/serializers/audit_serializers.py` — add `latest_progress = serializers.SerializerMethodField()` if not present)

---

## 24. Implementation Guide — FE-GAP 4 (RCM Lifecycle)

### Service functions (`grcService.ts`)

Add after `deleteRCM`:

```typescript
export async function submitRCMForReview(id: string): Promise<RiskControlMatrix> {
  const r = await grcClient.post<RiskControlMatrix>(`audit/rcm/${id}/submit/`);
  return r.data;
}

export async function approveRCM(id: string): Promise<RiskControlMatrix> {
  const r = await grcClient.post<RiskControlMatrix>(`audit/rcm/${id}/approve/`);
  return r.data;
}
```

### Hook mutations (add to `hooks/useRiskControlMatrix.ts` or equivalent)

```typescript
export function useSubmitRCMForReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.submitRCMForReview(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rcm'] });
      toast.success('RCM submitted for review');
    },
    onError: (e: any) => toast.error('Failed to submit RCM', {
      description: e.response?.data?.error || e.message,
    }),
  });
}

export function useApproveRCM() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.approveRCM(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rcm'] });
      toast.success('RCM approved');
    },
    onError: (e: any) => toast.error('Failed to approve RCM', {
      description: e.response?.data?.error || e.message,
    }),
  });
}
```

### Page buttons (`RiskControlMatrixPage.tsx`)

Add action handlers parallel to `handleConsolidate` in `QuarterlyReportsPage.tsx`:

```tsx
const submitMutation = useSubmitRCMForReview();
const approveMutation = useApproveRCM();

// in the action handlers:
const handleSubmitForReview = (id: string) => submitMutation.mutate(id);
const handleApprove = (id: string) => approveMutation.mutate(id);
```

Add buttons in the `GenericListPage` row action area conditioned on `item.status`:
- "Submit for Review" — visible when `status === 'draft'`
- "Approve" — visible when `status === 'reviewed'` (CIA role check)

---

## 25. Implementation Guide — FE-GAP 5 (QR WO Submit)

### Service functions (`grcService.ts`)

Add after `consolidateQuarterlyReport`:

```typescript
export async function submitQuarterlyReportForApproval(
  id: string
): Promise<QuarterlyAuditReport> {
  const r = await grcClient.post<QuarterlyAuditReport>(
    `audit/quarterly-reports/${id}/submit-for-approval/`
  );
  return r.data;
}

export async function getQuarterlyReportWorkflowStatus(
  id: string
): Promise<WorkflowStatusResponse> {
  const r = await grcClient.get<WorkflowStatusResponse>(
    `audit/quarterly-reports/${id}/workflow-status/`
  );
  return r.data;
}

export async function fetchQuarterlyReportEngagementReports(id: string): Promise<any[]> {
  const r = await grcClient.get<any[]>(`audit/quarterly-reports/${id}/engagement-reports/`);
  return r.data;
}
```

### `QuarterlyReportsPage.tsx` — Add Submit button

In `QuarterlyReportDetailDialog`, add a "Submit for WO Approval" button when:
- `item.is_consolidated === true`
- `item.status === 'draft'`
- No active WO plan

This replaces (or supplements) the current `draft → cia_review` manual transition.

---

## 26. Implementation Guide — FE-GAP 6 (WP Review Enforcement)

In `WorkingPaperDetailPage.tsx`, obtain the workflow status and current user:

```typescript
const { data: workflowStatus } = getWorkingPaperWorkflowStatus(workingPaperId);
// from IAM context:
const currentUserId = useAuthStore((s) => s.user?.id);

const currentAssignees: string[] = workflowStatus?.current_stage?.assignees ?? [];
const isAssignedReviewer = currentUserId
  ? currentAssignees.includes(currentUserId)
  : false;
```

Gate the Review button:

```tsx
{isAssignedReviewer && wp.review_status === 'pending' && (
  <Button onClick={handleReview} variant="outline">
    <CheckSquare className="mr-2 h-4 w-4" />
    Review as Lead Auditor
  </Button>
)}
```

---

## 27. Implementation Guide — FE-GAP 9/10/11

See §14, §15, §16 above for FE-GAP 9, 10, and 11 detail sections respectively.

**FE-GAP 9 summary of changes required in `EngagementDetailPage.tsx`:**
- Import `useDeclarations`, `useAuditSurveys`, `useRCMs`, `useAuditPrograms` with `engagement_id` filter
- Add 4 compact Card sections below Working Papers section, each with: list of items, status badge, link-out button, and an Add button that opens the relevant dialog pre-filled with `engagement_id`
- All dialogs (`CreateDeclarationDialog`, `CreateAuditSurveyDialog`, `CreateRCMDialog`, `CreateAuditProgramDialog`) already accept `engagement_id` so no dialog changes needed — only the page wiring

**FE-GAP 10 summary of changes:**
- Add `FraudRiskFactor` interface to `types/grc.ts`
- Add `fraud_risk_assessment?: FraudRiskFactor[]` to `AuditSurvey` and `AuditSurveyFormData`
- In `CreateAuditSurveyDialog.tsx`, conditionally render a dynamic row-builder when `survey_type === 'fraud_risk_assessment'`

**FE-GAP 11 summary:**
- One new button in `AuditPlansPage.tsx` header
- One mutation hook using the existing `generateDraftPlan()` service function
- Confirm dialog with `fiscal_year_id` selector

---

## 28. File Inventory — What Exists vs. What Must Be Created

### Files That Must Be Created

| File | Gap | Size Estimate |
|---|---|---|
| `types/grc.ts` — adds only | FE-GAP 1, 2, 3, 10 | +80 lines |
| `services/grcService.ts` — adds only | FE-GAP 1, 2, 4, 5, 11 | +140 lines |
| `hooks/useEngagementNotifications.ts` | FE-GAP 1 | ~130 lines |
| `hooks/useImplementationMonitoring.ts` — adds only | FE-GAP 2 | +40 lines |
| `hooks/useRiskControlMatrix.ts` — adds only | FE-GAP 4 | +40 lines |
| `hooks/useQuarterlyReports.ts` — adds only | FE-GAP 5 | +30 lines |
| `components/grc/CreateEngagementNotificationDialog.tsx` | FE-GAP 1 | ~120 lines |
| `components/grc/EngagementNotificationDetailDialog.tsx` | FE-GAP 1 | ~150 lines |
| `components/grc/EngagementNotificationsSection.tsx` | FE-GAP 1 | ~100 lines |
| `pages/grc/EngagementNotificationsPage.tsx` | FE-GAP 1 | ~200 lines |

### Files That Must Be Modified

| File | Gap | Change |
|---|---|---|
| `pages/grc/EngagementDetailPage.tsx` | FE-GAP 1, 9 | Add `EngagementNotificationsSection` + Declarations, Survey, RCM, Program compact sections |
| `components/grc/AuditMonitoringDetailDialog.tsx` | FE-GAP 2, 3, 7 | Add follow-up cycles, fix progress field, add escalation badge |
| `pages/grc/RiskControlMatrixPage.tsx` | FE-GAP 4 | Add submit/approve buttons |
| `pages/grc/QuarterlyReportsPage.tsx` | FE-GAP 5 | Add WO submit button |
| `components/grc/QuarterlyReportDetailDialog.tsx` | FE-GAP 5 | Add WO console + engagement reports list |
| `pages/grc/WorkingPaperDetailPage.tsx` | FE-GAP 6 | Gate review button to assigned LA |
| `components/grc/CreateAuditSurveyDialog.tsx` | FE-GAP 10 | Add fraud_risk_assessment type + dynamic row builder |
| `pages/grc/AuditPlansPage.tsx` | FE-GAP 11 | Add "Auto-Generate from Risk Scores" button |
| `components/grc/CreateAuditEngagementDialog.tsx` | FE-GAP 12 | Add `team_members` dynamic picker rows |
| `pages/grc/EngagementDetailPage.tsx` | FE-GAP 12 | Display team roster (name + role badge) |
| `types/grc.ts` | FE-GAP 12, 13 | Add `AuditEngagementTeamMember` interface; add `team_members` to `AuditEngagement`; add `EvidenceAttachment` interface |
| `components/grc/EvidenceAttachmentSection.tsx` | FE-GAP 13 | New reusable component — file list + upload dropzone + delete |
| `pages/grc/RiskAssessmentsPage.tsx` | FE-GAP 13 | Wire `EvidenceAttachmentSection` into detail panel |
| `pages/grc/WorkingPaperDetailPage.tsx` | FE-GAP 13 | Wire `EvidenceAttachmentSection` as supporting docs panel |
| `services/grcService.ts` | FE-GAP 14, 15 | Add `finalizeFinding()`, `updateFindingResponses()`, `completeSurvey()` |
| `pages/grc/AuditFindingsPage.tsx` | FE-GAP 14 | Add auditee/management response panel + draft→discussed→final action buttons |
| `pages/grc/AuditSurveysPage.tsx` | FE-GAP 15 | Add "Mark Complete" conditional action button |
| Router file (`AppRouter.tsx` or equivalent) | FE-GAP 1 | Add `/grc/engagement-notifications` route |

---

## 29. Priority Implementation Order

| Priority | Gap | Reason | Estimated Effort |
|---|---|---|---|
| 1 | **FE-GAP 2** (Follow-Up Responses) | Core monitoring cycle — data accumulates in backend with no UI to view/act on it | 4h |
| 2 | **FE-GAP 3** (Stale progress field) | Dependent on FE-GAP 2 type additions; simple fix once types are right | 1h |
| 3 | **FE-GAP 7** (Escalation badge) | 5-line change, dependent on FE-GAP 3 types already in place | 0.5h |
| 4 | **FE-GAP 11** (Generate Draft Plan) | Single button; service function already exists | 1h |
| 5 | **FE-GAP 4** (RCM lifecycle) | 2 service functions + 2 buttons | 2h |
| 6 | **FE-GAP 10** (Survey fraud risk assessment) | New type + dynamic row-builder field in existing dialog | 3h |
| 7 | **FE-GAP 5** (QR WO submit) | 3 service functions + WO console in QR detail | 3h |
| 8 | **FE-GAP 6** (WP review enforcement) | Single guard condition, UX improvwement | 1h |
| 9 | **FE-GAP 9** (Engagement detail sub-sections) | Add 4 compact sections to `EngagementDetailPage`; dialogs already exist | 4h |
| 10 | **FE-GAP 1** (Engagement Notifications) | Largest feature; requires 3 new components + page + hook file | 8h |
| 11 | **FE-GAP 12** (Audit Team Assignment) | Add `team_members` type + picker in dialog + display in detail page | 2h |
| 12 | **FE-GAP 13** (Evidence File Uploads) | Service functions already exist; only missing type, reusable component, and wiring in 2 pages | 3h |
| 13 | **FE-GAP 14** (Finding Lifecycle — respond + finalize) | No auditee response panel + no finalize button; 2 new service functions required | 2.5h |
| 14 | **FE-GAP 15** (Survey Mark Complete) | Single service function + conditional button | 1h |
| 15 | **FE-GAP 8** (Stamped document URL) | Low priority — blocked by backend GAP-A | 1h |

**Total estimated effort: ~38 hours of frontend implementation.**

---

## Compliance Summary

| Metric | Value |
|---|---|
| SRS requirements (Req 1–41) — fully covered by frontend | 23 / 41 |
| SRS requirements — partially covered | 14 / 41 |
| SRS requirements — absent from frontend | 4 / 41 |
| **Frontend SRS compliance** | **~56%** |
| Frontend gaps identified | 15 |
| Backend SRS compliance (reference) | ~96% |
| Gap between backend and frontend coverage | ~40% |

---

*End of FRONTEND SRS GAP ANALYSIS*
