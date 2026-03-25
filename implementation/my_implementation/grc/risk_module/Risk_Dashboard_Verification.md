# Risk Management Dashboard — SRS Verification Report

**Date:** 2026-03-24  
**SRS Reference:** `grc-service/implementation/my_implementation/grc/GRC_SRS/risk/RISK_MANAGEMENT.md`

---

## 1. Gaps / Deviations Found

### GAP-D1: Frontend-Backend Data Shape Mismatch (CRITICAL)

**Issue:** The frontend `RiskDashboard` TypeScript interface expected fields (`total_risk_champions`, `open_risks`, `rtap_completion_rate`, `qpr_summary`, `qa_summary`) that did not match the backend response shape (`assessments.total`, `dept_registers.{status: count}`, etc.). The dashboard was effectively showing all zeros.

**SRS Requirement:** The dashboard must show correct, live data from the backend reflecting all risk management processes.

**Fix Applied:**
- **Backend** (`apps/api/views/risk_dashboard_views.py`): Expanded `RiskDashboardView` to return comprehensive aggregated data covering all SRS processes.
- **Frontend types** (`types/grc.ts`): Updated `RiskDashboard` interface to match the new backend response.
- **Frontend dashboard** (`RiskDashboardPage.tsx`): Updated all data bindings to use the new interface fields.

### GAP-D2: Missing Risk Champion Statistics

**Issue:** The backend did not query the `RiskChampion` model. The dashboard had no champion counts.

**SRS Requirement:** SRS Process FCC_SBP_RMQA_01 — Risk Champions are a core SRS entity. Dashboard should show total and active champions.

**Fix Applied:** Backend now queries `RiskChampion` model and returns `risk_champions.total` and `risk_champions.active`.

### GAP-D3: Missing Assessment Sheets Statistics

**Issue:** Backend returned only `assessments.total` without status breakdown. Frontend didn't display assessment stats at all.

**SRS Requirement:** SRS Process FCC_SBP_RMQA_03 — Risk Assessment Sheets are the core artifact for risk identification and evaluation. The dashboard should prominently show assessment counts.

**Fix Applied:**
- Backend returns `assessments.total` and `assessments.by_status` with full status breakdown.
- Frontend now shows "Risk Assessment Sheets" as the first summary stat card, navigating to `/service/grc/risk-assessment-sheets`.

### GAP-D4: Missing RTAP Completion Rate Calculation

**Issue:** Backend returned RTAP status breakdown but not a computed completion rate. Frontend expected `rtap_completion_rate` but received nothing.

**SRS Requirement:** SRS Process FCC_SBP_RMQA_05 — Implementation rate of proposed controls is a key measurable outcome.

**Fix Applied:** Backend now computes `rtaps.completion_rate` from `RTAPItem` model (completed items / total items × 100).

### GAP-D5: Missing QPR Summary Data

**Issue:** No QPR data was returned by the backend. Frontend expected `qpr_summary` but received nothing.

**SRS Requirement:** Quarterly Performance Reports are a core SRS output for monitoring implementation status.

**Fix Applied:** Backend now queries the latest `QuarterlyPerformanceReport` and returns `qpr_summary.current_quarter`, `qpr_summary.implementation_rate`, and `qpr_summary.total_reports`.

### GAP-D6: Missing Quality Assurance Statistics

**Issue:** Backend did not query any QA models. Frontend expected `qa_summary` with auditor counts and NC closures.

**SRS Requirement:** SRS Processes FCC_SBP_RMQA_06 and FCC_SBP_RMQA_07 — Quality Auditors, QMS Audits, and Non-Conformances are core QA processes.

**Fix Applied:** Backend now queries `QualityAuditor`, `QMSAuditProgram`, `QMSAuditPlan`, `QMSAuditReport`, and `NonConformance` models. Returns `qa_summary.total_quality_auditors`, `qa_summary.certified_quality_auditors`, `qa_summary.pending_nc_closures`, `qa_summary.qms_programs`, `qa_summary.qms_plans`, `qa_summary.qms_reports`.

### GAP-D7: Missing Status Breakdown Visualizations

**Issue:** The `StatusBreakdownCard` component was defined in the dashboard but never used in the layout. Status breakdowns for departmental registers, institutional registers, RTAPs, and non-conformances were not visualized.

**SRS Requirement:** SRS defines multi-stage status workflows for all registers and treatment plans. Dashboard should reflect these status distributions.

**Fix Applied:** Dashboard now renders four `StatusBreakdownCard` components for: Departmental Registers, Institutional Registers, Risk Treatment Plans, and Non-Conformances.

### GAP-D8: Missing Risk Meetings & Surveys Data

**Issue:** Backend did not return any meeting or survey statistics. SRS defines workshops, brainstorming sessions, interviews, and surveys as key risk identification tools.

**SRS Requirement:** SRS §4.11.1.1 #3 — The system shall support brainstorming sessions, workshops, interviews, and surveys.

**Fix Applied:** Backend now returns `meetings.total`, `meetings.upcoming`, `surveys.total`, and `surveys.open`. Frontend shows a "Meetings & Surveys" card.

### GAP-D9: Incomplete Quick Links

**Issue:** Dashboard quick links only had 4 items: Risk Champions, Performance Reports, QMS Audit Reports, Risk Meetings.

**SRS Requirement:** SRS defines many more processes/pages that should be accessible from the dashboard.

**Fix Applied:** Quick links now split into two sections with comprehensive coverage:
- **Risk Management** (10 links): Risk Champions, Assessment Sheets, Departmental Registers, Institutional Registers, Treatment Plans, Performance Reports, Risk Meetings, Risk Surveys, Activity Reports, Knowledge Base
- **Quality Assurance** (7 links): Quality Auditors, QA Training, QMS Programs, QMS Plans, QMS Checklists, Audit Reports, Non-Conformances

### GAP-D10: GRC Landing Page Hardcoded Zeros

**Issue:** `GRCDashboard.tsx` had Risk Management and Quality Assurance items with `stats: { total: 0, active: 0 }` hardcoded.

**SRS Requirement:** Dashboard cards should reflect real, live data.

**Fix Applied:** `GRCDashboard.tsx` now imports `useRiskDashboard` hook and populates Risk Management and Quality Assurance card stats with real backend data.

---

## 2. Changes Applied

### Backend (`grc-service`)

| File | Change |
|------|--------|
| `apps/api/views/risk_dashboard_views.py` | Expanded `RiskDashboardView` to query 10 models (RiskChampion, RiskAssessmentSheet, DepartmentalRiskRegister, InstitutionalRiskRegister, RiskTreatmentActionPlan, RTAPItem, QuarterlyPerformanceReport, QualityAuditor, QMSAuditProgram/Plan/Report, NonConformance, RiskMeeting, RiskSurvey) and return comprehensive SRS-aligned response structure |

### Frontend (`frontend`)

| File | Change |
|------|--------|
| `apps/staff-portal/src/types/grc.ts` | Updated `RiskDashboard` interface to match new backend response with nested objects for risk_champions, assessments, dept_registers, inst_registers, rtaps, qpr_summary, qa_summary, non_conformances, meetings, surveys |
| `apps/staff-portal/src/pages/grc/RiskDashboardPage.tsx` | Rewrote dashboard layout: 4 summary StatCards (assessments, champions, RTAP completion, NCs), 4 StatusBreakdownCards (dept/inst registers, RTAPs, NCs), 3 detail cards (QPR, QA, Meetings/Surveys), comparative chart, 17 quick-link cards organized by Risk Management and Quality Assurance sections |
| `apps/staff-portal/src/components/dashboards/GRCDashboard.tsx` | Wired real risk dashboard data into Risk Management (4 items) and Quality Assurance (2 items) cards using `useRiskDashboard` hook |

---

## 3. SRS Alignment Matrix

| SRS Process | Process Code | Dashboard Representation | Status |
|---|---|---|---|
| Appointment of Risk Champions | FCC_SBP_RMQA_01 | Summary card (total/active) + quick link | ✅ Aligned |
| Development of Departmental Risk Register | FCC_SBP_RMQA_03 | Status breakdown card + quick link | ✅ Aligned |
| Preparation of Institutional Risk Register | FCC_SBP_RMQA_04 | Status breakdown card + quick link | ✅ Aligned |
| Implementation of Proposed Controls (RTAP) | FCC_SBP_RMQA_05 | Completion rate stat + status breakdown + quick link | ✅ Aligned |
| Appointment of Quality Auditors | FCC_SBP_RMQA_06 | QA summary card (total/certified) + quick link | ✅ Aligned |
| Conducting Quality Audit | FCC_SBP_RMQA_07 | QA summary (QMS reports) + quick links (programs/plans/checklists/reports) | ✅ Aligned |
| Risk Assessment (§4.11.1.1) | — | Assessment sheets stat card + quick link | ✅ Aligned |
| Risk Profiling (§4.11.1.3) | — | Assessment sheets reflecting risk registration | ✅ Aligned |
| QA Management (§4.11.1.4) | — | QA section with auditors, programs, plans, reports, NCs | ✅ Aligned |
| Quarterly Reporting | — | QPR summary card + quick link | ✅ Aligned |
| Risk Meetings/Workshops | — | Meetings & Surveys card + quick link | ✅ Aligned |
| Risk Surveys | — | Surveys count + quick link | ✅ Aligned |
| Non-Conformances | — | Status breakdown + pending closures + quick link | ✅ Aligned |
| Knowledge Base | — | Quick link | ✅ Aligned |
| Activity Reports | — | Quick link | ✅ Aligned |
| Comparative Analysis | — | Bar chart (dept registers by status across departments/fiscal years) | ✅ Aligned |
| PDF Export | — | Existing `RiskDashboardExportView` endpoint unchanged | ✅ Aligned |

---

## 4. Validation

- **TypeScript compilation:** ✅ Clean (0 errors)
- **Python syntax:** ✅ Clean (py_compile passed)
- **All dashboard cards navigable:** ✅ Every card/quick link maps to an existing route
- **All backend data sources queryable:** ✅ All models imported and queried
- **SRS coverage:** ✅ All 7 SRS processes represented on dashboard
