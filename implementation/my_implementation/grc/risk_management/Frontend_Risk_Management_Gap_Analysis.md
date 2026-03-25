# Risk Management & QA Module — Frontend Gap Analysis

> **Date:** March 24, 2026
> **Scope:** Staff Portal — `frontend/apps/staff-portal/`
> **Based On:** Backend fixes documented in `Risk_Management_SRS_Verification.md` (v3)
> **Revision:** v2 — Second-level validation pass completed
> **Validation status:** All 6 original gaps confirmed. 1 false-positive corrected (G-12). 1 new gap added (FE-G-07).

---

## 1. Overview

After all backend gaps (G-01 through G-12) were confirmed fixed and deployed (SRS Verification Report v3), the frontend staff portal was inspected against the same SRS requirements to identify what the user interface is **missing or showing incorrectly**.

### Methodology

- Full read of all relevant GRC pages under `apps/staff-portal/src/pages/grc/`
- Inspection of `apps/staff-portal/src/types/grc.ts` — all type definitions
- Inspection of `apps/staff-portal/src/services/grcService.ts` — all service API calls
- Inspection of `apps/staff-portal/src/hooks/` — all React Query hook files
- Route inspection in `apps/staff-portal/src/App.tsx`
- Cross-referenced every backend fix (R-01 through R-11) against frontend coverage

### Technology Stack

| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript |
| Data Fetching | TanStack React Query v5 |
| Types | `src/types/grc.ts` |
| Service | `src/services/grcService.ts` |
| Query Keys | `src/hooks/grcKeys.ts` |
| Hooks | `src/hooks/use*.ts` |
| Pages | `src/pages/grc/*.tsx` |
| Routes | `src/App.tsx` |

---

## 2. Frontend Coverage Against Backend Fixes

| Backend Fix | Description | Frontend Page | Frontend Status |
|---|---|---|---|
| R-01/G-06 | IRR threshold check | `InstitutionalRiskDetailPage.tsx` | ✅ No UI change needed — backend validation |
| R-02/G-07 | QA conflict-of-interest | `QualityAuditorDetailPage.tsx` | ✅ No UI change needed — backend validation |
| R-03/G-11 | IRR DRR membership check | `InstitutionalRiskDetailPage.tsx` | ✅ No UI change needed — backend validation |
| R-04/G-03 | Activity Report DG noting | `InstitutionalRiskDetailPage.tsx` | ❌ **FE-G-03** — type missing fields, no action UI |
| R-05/G-04,G-05 | LSM 7-day rule | All IRR/QPR forms | ✅ No UI change needed — backend validation |
| R-06/G-09 | QPR snapshot auto-compute | `RiskPerformanceReportDetailPage.tsx` | ✅ Implementation rate already shown |
| R-07/G-08 | QA replacement trigger | `QualityAuditorDetailPage.tsx` | ❌ **FE-G-04** — `nomination_status` not in type or UI |
| R-08/G-02 | Risk Knowledge Base CRUD | *(no page)* | ❌ **FE-G-02** — zero frontend coverage |
| R-09/G-01 | Risk Surveys CRUD | *(no page)* | ❌ **FE-G-01** — zero frontend coverage |
| R-10/G-10 | Standalone Activity Reports | *(no page)* | ❌ **FE-G-05** — zero frontend coverage |
| R-11 | Dashboard caching | `RiskDashboardPage.tsx` | ❌ **FE-G-06** — type mismatch hides all typed fields |
| G-12 | Interview meeting type | `CreateRiskMeetingDialog.tsx` | ❌ **FE-G-07** — `interview` absent from hardcoded `MEETING_TYPES` constant |

---

## 3. Gap Analysis

### 3.1 Missing Pages (Zero Coverage)

| Gap ID | Description | SRS Reference | Severity |
|---|---|---|---|
| FE-G-01 | **No Risk Surveys page.** `RiskSurveysPage.tsx` does not exist. No `RiskSurvey`, `RiskSurveyQuestion`, or `RiskSurveyResponse` types exist in `grc.ts`. No service functions exist for `/risk/surveys/` endpoints. No route registered in `App.tsx`. The backend CRUD endpoints are live but completely unreachable from the UI. | §4.11.1.1 req 3 | Medium |
| FE-G-02 | **No Risk Knowledge Base page.** `RiskKnowledgeBasePage.tsx` does not exist. No `RiskKnowledgeBase` type exists in `grc.ts`. No service functions for `/risk/knowledge-base/`. No route in `App.tsx`. The backend CRUD endpoints are live but unreachable. | §4.11.1.1 req 4 | Medium |
| FE-G-05 | **No standalone GRC Activity Reports page.** The only `ActivityReportsPage` is at `pages/clients/admin/ActivityReportsPage` for the Client Service — unrelated to IRR activity reports. There is no `GRCActivityReportsPage.tsx` for RMQAM to filter across all IRR activity reports by `quarter` and `fiscal_year`. The backend endpoint `GET /risk/activity-reports/` is live but unreachable from the UI. | §4.11.1.1 req 13–14 | Low |

### 3.2 Missing Fields and Actions in Existing Pages

| Gap ID | Description | SRS Reference | Severity |
|---|---|---|---|
| FE-G-03 | **Activity Report DG noting — zero frontend support.** The `IRRActivityReport` interface (`grc.ts` line 2014) has no `dg_noted`, `dg_noted_by`, or `dg_noted_at` fields. The `IRRActivityReportsSection` embedded in `InstitutionalRiskDetailPage.tsx` is a read-only table with no action buttons. No service function exists for `POST /risk/institutional-registers/activity-reports/<pk>/dg-note/`. RMQAM cannot perform the DG noting governance step from the UI. | FCC_SBP_RMQA_04 R8 | **High** |
| FE-G-04 | **QualityAuditor `nomination_status` not in type or UI.** The `QualityAuditor` interface (`grc.ts` line 1814) has only `status: QAStatus` — no `nomination_status` property. The values `replacement_needed`, `replaced`, `active` do not exist in types, services, or pages. `QualityAuditorDetailPage.tsx` cannot display whether a QA is pending replacement after a second exam failure. `statusColors` map handles only `nominated`, `appointed`, `revoked` — all other values silently fall back to gray. | FCC_SBP_RMQA_06 R6 | Medium |

### 3.3 Incorrect Rendering in Existing Pages

| Gap ID | Description | SRS Reference | Severity |
|---|---|---|---|
| FE-G-06 | **`RiskDashboardPage.tsx` reads wrong key names — type mismatch.** The `RiskDashboard` interface (`grc.ts` line 2095) defines these typed fields: `total_risk_champions`, `active_risk_champions`, `total_risks`, `open_risks`, `rtap_completion_rate`, `qpr_summary`, `qa_summary`. However, `RiskDashboardPage.tsx` casts the response to `Record<string, unknown>` and reads: `d?.assessments`, `d?.dept_registers`, `d?.inst_registers`, `d?.rtaps`, `d?.non_conformances` — **none of which exist in the typed interface or the actual API response**. Result: all StatCards show `0` or `undefined`. `qpr_summary` (QPR snapshot metrics from backend fix R-06/G-09) and `qa_summary` are silently dropped and never rendered. The entire dashboard is non-functional. | §4.11.1.1 req 13–14; §1.5.6 Scalability | **High** |

### 3.4 Corrected Finding — v1 False Positive

| Gap ID | Description | SRS Reference | Severity |
|---|---|---|---|
| FE-G-07 | **`interview` meeting type is not selectable from the create form.** G-12 in the backend fixes added `('interview', 'Interview')` to `RiskMeeting.MEETING_TYPE_CHOICES`. The v1 analysis incorrectly assumed the UI dropdown would reflect this automatically. **That assumption is wrong.** `CreateRiskMeetingDialog.tsx` contains a hardcoded `MEETING_TYPES` constant: `[ risk_committee, risk_review, management_review, workshop, other ]`. The value `interview` is absent. A user cannot schedule a meeting of type "Interview" from the UI. Additionally, `meetingTypeColors` in `RiskMeetingsPage.tsx` has no `interview` entry (display falls back to gray). The SRS §4.11.1.1 req 3 explicitly names "interviews" as one of the required risk identification methods. | §4.11.1.1 req 3; FCC_SBP_RMQA_03 | Low |

---

## 4. Risk & Impact Assessment

| Gap ID | Gap | Impact | Rationale |
|---|---|---|---|
| FE-G-06 | Dashboard type mismatch — all metrics hidden | **HIGH** | The Risk Dashboard is the primary management oversight tool. All StatCards show 0 or undefined values — RMQAM sees no live data. QPR snapshot metrics (backend-fixed) render nothing. |
| FE-G-03 | DG noting has zero UI support | **HIGH** | RMQAM cannot perform the mandatory DG noting governance step from the UI. The backend endpoint exists and is secured, but it is 100% unreachable from the staff portal. |
| FE-G-01 | No Risk Surveys page | **MEDIUM** | Risk identification surveys created via backend API are completely hidden from users. Cannot create, respond to, or review survey results from the UI. |
| FE-G-02 | No Risk Knowledge Base page | **MEDIUM** | The lessons-learned repository is fully implemented in the backend but has zero UI entry point. RMQAM cannot browse or add knowledge base entries. |
| FE-G-04 | `nomination_status` not visible | **MEDIUM** | After a QA fails their 2nd exam, the system auto-sets `nomination_status = 'replacement_needed'` on the backend. This status is invisible in the UI — no user would know a replacement is needed without querying the API directly. |
| FE-G-05 | No standalone Activity Reports page | **LOW** | RMQAM can still view Activity Reports nested under each IRR detail page. The cross-register quarterly filter is missing but it is a convenience gap. |
| FE-G-07 | `interview` not in `CreateRiskMeetingDialog` options | **LOW** | Users cannot schedule Interview-type risk identification meetings from the UI. The backend accepts the value; scheduling requires a direct API call. SRS explicitly names "interviews" as a required risk identification tool. |

---

## 5. Recommendations & Fix Order

### Priority 1 — Critical (Fix Immediately)

**FE-R-01: Fix RiskDashboard type mismatch (FE-G-06)**

Files to change:
1. `src/pages/grc/RiskDashboardPage.tsx` — fix StatCard keys and add QPR/QA summary sections

Steps:
```tsx
// Replace the unsafe cast. The backend returns these keys (per RiskDashboard interface):
//   total_risk_champions, active_risk_champions, total_risks, open_risks,
//   rtap_completion_rate, qpr_summary { current_quarter, implementation_rate },
//   qa_summary { total_quality_auditors, active_quality_auditors, pending_nc_closures }

// Fix StatCard data bindings:
{ label: 'Total Risks',        value: data?.total_risks ?? 0 }
{ label: 'Open Risks',         value: data?.open_risks ?? 0 }
{ label: 'Risk Champions',     value: data?.total_risk_champions ?? 0 }
{ label: 'RTAP Completion',    value: `${data?.rtap_completion_rate ?? 0}%` }

// Add QPR Summary card:
{ label: 'QPR Quarter',         value: data?.qpr_summary?.current_quarter ?? '—' }
{ label: 'Implementation Rate', value: `${data?.qpr_summary?.implementation_rate ?? 0}%` }

// Add QA Summary card:
{ label: 'Total QAs',           value: data?.qa_summary?.total_quality_auditors ?? 0 }
{ label: 'Active QAs',          value: data?.qa_summary?.active_quality_auditors ?? 0 }
{ label: 'Pending NC Closures', value: data?.qa_summary?.pending_nc_closures ?? 0 }
```

**FE-R-02: Add DG noting support to Activity Report (FE-G-03)**

Files to change:
1. `src/types/grc.ts` — add fields to `IRRActivityReport` interface
2. `src/services/grcService.ts` — add `markActivityReportDGNoted(id)` function
3. `src/hooks/useInstitutionalRiskRegisters.ts` — add `useMarkActivityReportDGNoted()` mutation
4. `InstitutionalRiskDetailPage.tsx` or its embedded `IRRActivityReportsSection` component — add "Mark as DG Noted" button (permission-gated to `CanManageInstitutionalRiskRegister`)

```ts
// grc.ts — add to IRRActivityReport interface:
dg_noted: boolean;
dg_noted_by?: string;
dg_noted_at?: string;

// grcService.ts — new function:
export async function markActivityReportDGNoted(id: string): Promise<IRRActivityReport> {
  const response = await grcClient.post<IRRActivityReport>(
    `risk/institutional-registers/activity-reports/${id}/dg-note/`
  );
  return response.data;
}

// UI — in the activity reports table, add per-row action:
// Show green "DG Noted" badge if dg_noted === true + dg_noted_at timestamp
// Show "Mark as DG Noted" button (CanManageInstitutionalRiskRegister) if dg_noted === false
```

---

### Priority 2 — High (Fix in Next Sprint)

**FE-R-03: Add `nomination_status` to QualityAuditor type and detail page (FE-G-04)**

Files to change:
1. `src/types/grc.ts` — add field to `QualityAuditor` interface
2. `src/pages/grc/QualityAuditorDetailPage.tsx` — display field + extend statusColors

```ts
// grc.ts — add to QualityAuditor interface:
nomination_status?: 'active' | 'replacement_needed' | 'replaced';

// QualityAuditorDetailPage.tsx — extend statusColors:
replacement_needed: 'bg-amber-100 text-amber-800 border border-amber-300',
replaced:           'bg-red-100 text-red-700 border border-red-300',
active:             'bg-green-100 text-green-800',

// Add "Nomination Status" row to Auditor Details card:
// Show badge only when nomination_status is 'replacement_needed' or 'replaced'
// e.g., "Replacement Needed — head re-nomination required"
```

---

### Priority 3 — Medium (Backlog)

**FE-R-04: Create Risk Surveys page (FE-G-01)**

Files to create / change:
1. `src/types/grc.ts` — add `RiskSurvey`, `RiskSurveyQuestion`, `RiskSurveyResponse` interfaces
2. `src/services/grcService.ts` — add API path `riskSurveys: 'risk/surveys/'` + CRUD functions
3. `src/hooks/grcKeys.ts` — add `riskSurveyKeys`
4. `src/hooks/useRiskSurveys.ts` — new hook file
5. `src/pages/grc/RiskSurveysPage.tsx` — new page (list + create + detail/questions)
6. `src/App.tsx` — register route `risk-surveys` and `risk-surveys/:surveyId`

```ts
// Types to add (grc.ts):
export type RiskSurveyStatus = 'draft' | 'open' | 'closed';
export type RiskSurveyQuestionType = 'text' | 'rating' | 'yes_no' | 'multiple_choice';

export interface RiskSurvey {
  id: string;
  title: string;
  description?: string;
  fiscal_year: string;
  fiscal_year_id: string;
  org_unit_id?: string;
  status: RiskSurveyStatus;
  opens_at?: string;
  closes_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskSurveyQuestion {
  id: string;
  survey: string;
  survey_id: string;
  question_type: RiskSurveyQuestionType;
  question_text: string;
  choices?: string[];
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskSurveyResponse {
  id: string;
  survey: string;
  survey_id: string;
  respondent_id: string;
  submitted_at: string;
  answers: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
```

**FE-R-05: Create Risk Knowledge Base page (FE-G-02)**

Files to create / change:
1. `src/types/grc.ts` — add `RiskKnowledgeBase` interface
2. `src/services/grcService.ts` — add `riskKnowledgeBase: 'risk/knowledge-base/'` + CRUD functions
3. `src/hooks/grcKeys.ts` — add `riskKnowledgeBaseKeys`
4. `src/hooks/useRiskKnowledgeBase.ts` — new hook file
5. `src/pages/grc/RiskKnowledgeBasePage.tsx` — new page with source_type filter tabs
6. `src/App.tsx` — register route `risk-knowledge-base`

```ts
// Type to add (grc.ts):
export type KnowledgeBaseSourceType =
  | 'lesson_learned'
  | 'audit_finding'
  | 'industry_best_practice'
  | 'external_report';

export interface RiskKnowledgeBase {
  id: string;
  source_type: KnowledgeBaseSourceType;
  title: string;
  description?: string;
  fiscal_year: string;
  fiscal_year_id: string;
  document_id?: string;
  tags?: string[];
  contributed_by?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
```

**FE-R-06: Create standalone GRC Activity Reports page (FE-G-05)**

Files to create / change:
1. `src/services/grcService.ts` — add `fetchStandaloneActivityReports(filters)` pointing to `risk/activity-reports/`
2. `src/hooks/useInstitutionalRiskRegisters.ts` — add `useStandaloneActivityReports(filters)` hook
3. `src/pages/grc/GRCActivityReportsPage.tsx` — new page with `quarter` + `fiscal_year` filter dropdowns
4. `src/App.tsx` — register route `risk-activity-reports`

```ts
// grcService.ts — new function:
export function fetchStandaloneActivityReports(params?: {
  quarter?: string;
  fiscal_year?: string;
  page?: number;
  page_size?: number;
}): Promise<AuditCollectionResult<IRRActivityReport>> {
  return fetchCollection<IRRActivityReport>('risk/activity-reports/', params);
}
```

---

### Priority 3 (continued) — Low

**FE-R-07: Add `interview` to MEETING_TYPES and meetingTypeColors (FE-G-07)**

Files to change:
1. `src/components/grc/CreateRiskMeetingDialog.tsx` — add `interview` to the `MEETING_TYPES` constant
2. `src/pages/grc/RiskMeetingsPage.tsx` — add `interview` to `meetingTypeColors`

```ts
// CreateRiskMeetingDialog.tsx — MEETING_TYPES array (add before 'other'):
{ value: 'interview', label: 'Interview' },

// RiskMeetingsPage.tsx — meetingTypeColors (add entry):
interview: 'bg-orange-100 text-orange-800',
```

---

## 6. File Change Summary

| Fix | Priority | Files Changed | Files Created |
|---|---|---|---|
| FE-R-01 (Dashboard) | 1 — Critical | `pages/grc/RiskDashboardPage.tsx` | None |
| FE-R-02 (DG Note) | 1 — Critical | `types/grc.ts`, `services/grcService.ts`, `hooks/useInstitutionalRiskRegisters.ts`, `pages/grc/InstitutionalRiskDetailPage.tsx` | None |
| FE-R-03 (nomination_status) | 2 — High | `types/grc.ts`, `pages/grc/QualityAuditorDetailPage.tsx` | None |
| FE-R-04 (Risk Surveys) | 3 — Medium | `types/grc.ts`, `services/grcService.ts`, `hooks/grcKeys.ts`, `App.tsx` | `hooks/useRiskSurveys.ts`, `pages/grc/RiskSurveysPage.tsx` |
| FE-R-05 (Knowledge Base) | 3 — Medium | `types/grc.ts`, `services/grcService.ts`, `hooks/grcKeys.ts`, `App.tsx` | `hooks/useRiskKnowledgeBase.ts`, `pages/grc/RiskKnowledgeBasePage.tsx` |
| FE-R-06 (Standalone Activity Reports) | 3 — Low | `services/grcService.ts`, `hooks/useInstitutionalRiskRegisters.ts`, `App.tsx` | `pages/grc/GRCActivityReportsPage.tsx` |
| FE-R-07 (Interview meeting type) | 3 — Low | `components/grc/CreateRiskMeetingDialog.tsx`, `pages/grc/RiskMeetingsPage.tsx` | None |

---

## 7. Implementation Order

```
Phase 1 (Critical — fix before next demo/release):
  FE-R-01  →  Fix RiskDashboardPage key mismatch
  FE-R-02  →  Add DG noting to IRRActivityReport + InstitutionalRiskDetailPage

Phase 2 (High — next sprint):
  FE-R-03  →  Add nomination_status to QualityAuditor type + detail page

Phase 3 (Medium — backlog):
  FE-R-04  →  Risk Surveys page (types → service → keys → hook → page → route)
  FE-R-05  →  Risk Knowledge Base page (types → service → keys → hook → page → route)
  FE-R-06  →  Standalone GRC Activity Reports page (service → hook → page → route)
  FE-R-07  →  Add 'interview' to CreateRiskMeetingDialog.MEETING_TYPES + meetingTypeColors (2-line change)
```

---

## 8. Compliance Score (Frontend)

| Gap | Description | Status |
|---|---|---|
| FE-G-01 | Risk Surveys page | ❌ Not implemented |
| FE-G-02 | Risk Knowledge Base page | ❌ Not implemented |
| FE-G-03 | Activity Report DG noting UI | ❌ Not implemented |
| FE-G-04 | QualityAuditor nomination_status UI | ❌ Not implemented |
| FE-G-05 | Standalone Activity Reports page | ❌ Not implemented |
| FE-G-06 | Dashboard type mismatch — metrics hidden | ❌ Bug — all metrics show 0 |
| FE-G-07 | `interview` absent from `CreateRiskMeetingDialog.MEETING_TYPES` | ❌ Not implemented |

**7 frontend gaps confirmed. 1 false-positive corrected (v1 marked G-12 as safe — incorrect). All 7 gaps directly traceable to SRS requirements.**

---

## 9. Second-Level Validation Audit Log

> **Validation performed:** March 24, 2026  
> **Files directly inspected:** `IRRActivityReportsSection.tsx`, `grc.ts`, `QualityAuditorDetailPage.tsx`, `RiskDashboardPage.tsx`, `AuditSurveysPage.tsx`, `grcService.ts`, `App.tsx`, `CreateRiskMeetingDialog.tsx`, `RiskMeetingsPage.tsx`, `RiskPerformanceReportDetailPage.tsx`

### Corrections made (v1 → v2)

| Change | Details |
|---|---|
| G-12 row — false positive corrected | v1 claimed `✅ UI dropdown will show new option automatically`. **This is wrong.** `CreateRiskMeetingDialog.tsx` has a hardcoded `MEETING_TYPES` array that does not include `interview`. Changed to `❌ FE-G-07`. |
| FE-G-05 SRS reference corrected | Changed from `FCC_SBP_RMQA_04 R7` (that step refers to DG noting, not monitoring reports) to `§4.11.1.1 req 13–14` (monitoring of action plans and quarterly report generation). |
| FE-G-07 added | New gap: `interview` missing from `CreateRiskMeetingDialog.MEETING_TYPES` and `RiskMeetingsPage.meetingTypeColors`. |
| FE-R-07 added | Implementation fix spec added (Priority 3, 2-line change). |
| Compliance score updated | 6 → 7 gaps. |

### Items confirmed NOT gaps (verified against actual code)

| Original claim | Verification result |
|---|---|
| R-05/G-04,G-05: LSM 7-day rule — no UI change needed | ✅ Backend returns 400 with descriptive error message; generic API error toast displays it. No silent swallowing. |
| R-06/G-09: QPR snapshot — implementation rate already shown | ✅ `QuarterlyPerformanceReport` type already has `implementation_rate_current` / `implementation_rate_previous`; both rendered in `RiskPerformanceReportDetailPage.tsx` at lines 144–160. The backend fix auto-computes what was already displayed. |
| R-01/G-06: IRR threshold — no UI change needed | ✅ Backend enforces threshold check; 400 response displayed via toast. No extra UI indicator needed. |
| R-02/G-07: QA conflict-of-interest — no UI change needed | ✅ Backend enforces at assignment time; error message propagates via standard toast. |
| R-03/G-11: IRR DRR membership — no UI change needed | ✅ Serializer validation returns 400; standard API error handling sufficient. |
| `AuditSurveysPage.tsx` overlaps Risk Surveys (FE-G-01) | ✅ Confirmed SEPARATE entity. `AuditSurvey` type is engagement-scoped (internal audit satisfaction surveys). `RiskSurvey` is risk-identification scoped. No overlap. FE-G-01 stands. |
