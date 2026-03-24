# UI Design Comparison vs SRS Requirements
## Current Implementation vs Demo UI — Risk Management & Quality Assurance

> **Question answered here:** Which UI design is better aligned with implementing all SRS requirements?
>
> **Sources:**
> - `current_implementation_ui.md` — Actual code as implemented in the staff portal frontend
> - `general_demo_UI_design.md` — Demo UI captured from `fcc.ictpack.net`
> - `RISK_MANAGEMENT.md` — SRS business process & system requirements (FCC_SBP_RMQA_01 to 07)

---

## QUICK VERDICT

| | Current Implementation | Demo UI |
|--|--|--|
| **Overall SRS alignment** | ✅ **Stronger** | ⚠️ Simplified/partial |
| **Process coverage** | Full lifecycle | Incomplete |
| **Missing from SRS** | Risk Settings config tables | Risk Assessment Sheets, QA lifecycle, QMS governance |
| **Best choice?** | ✅ YES — keep and extend | Use only as reference for Risk Settings and risk form fields |

> ### DECISIONS MADE
> 1. ✅ **Stick with Current Implementation** — do not adopt the Demo UI structure.
> 2. ✅ **Risk Settings goes in `/service/grc/configuration`** — add the missing risk config tabs (Strategic Objectives, Risk Categories, Risk Sectors, Impact Levels, Likelihood Levels, Risk Rates) to the existing shared GRC Configuration page, **not** as a dedicated `/service/grc/risk-settings` page.
>
> **Rationale for decision 2:**
> - The Configuration page already mixes domain-specific settings (Risk Ratings, Audit Opinions, Finding Types) — adding the missing risk tables is consistent, not a new pattern.
> - Admin UX: one place to configure all GRC settings instead of splitting across two pages.
> - The sidebar already has 15 transactional menu items. Adding "Risk Settings" would clutter it with an admin concern that belongs in Configuration.
> - SRS does not mandate a dedicated page — it only requires these tables to be configurable.
> - The Demo's dedicated page was likely a shortcut in the prototype, not a principled design decision.

---

## 1. MENU STRUCTURE COMPARISON

### 1.1 Risk Management Menu

| Menu Item | Current Implementation | Demo UI | SRS Requires? | Decision |
|-----------|------------------------|---------|---------------|----------|
| Risk Dashboard | ✅ Yes | ❌ No | ✅ Yes (system monitoring overview, comparative analysis) | ✅ Keep as-is |
| **Risk Settings** | ⚠️ In GRC Config (partial) | ✅ Dedicated page (complete) | ✅ Yes (configurable reference tables) | ✅ **Complete in `/service/grc/configuration` — no separate page** |
| Risk Champions | ✅ Yes (full workflow) | ✅ Yes (simplified) | ✅ Yes (FCC_SBP_RMQA_01) | ✅ Keep as-is |
| **Risk Assessment Sheets** | ✅ **Yes (full workflow)** | ❌ **Missing entirely** | ✅ Yes (FCC_SBP_RMQA_03 — the core tool) | ✅ Keep as-is |
| Departmental Risks | ✅ Yes (register+entries) | ✅ Yes (flat list of risks) | ✅ Yes (FCC_SBP_RMQA_03) | ✅ Keep as-is; verify entry dialog fields |
| Institutional Risks | ✅ Yes (full governance) | ✅ Yes (simplified) | ✅ Yes (FCC_SBP_RMQA_04) | ✅ Keep as-is |
| Risk Treatment Plans | ✅ Yes (formal doc) | ✅ Yes (simplified) | ✅ Yes (FCC_SBP_RMQA_05) | ✅ Keep as-is; verify RTAP item fields |
| Performance Reports | ✅ Yes (quarterly) | ❌ No | ✅ Yes (FCC_SBP_RMQA_05 step 7 — Quarterly Performance Report) | ✅ Keep as-is |
| Risk Meetings | ✅ Yes | ❌ No | ✅ Yes (Risk and Governance Committee meetings required) | ✅ Keep as-is |
### 1.2 Quality Assurance Menu

| Menu Item | Current Implementation | Demo UI | SRS Requires? |
|-----------|------------------------|---------|---------------|
| Quality Auditors | ✅ Yes (training→exam→appointment) | ✅ Yes (simplified) | ✅ Yes (FCC_SBP_RMQA_06) |
| **QA Training** | ✅ **Yes** | ❌ **Missing entirely** | ✅ Yes (ISO 9001:2015 training mandatory before exam) |
| QMS Programs | ✅ Yes (with approval workflow) | ❌ No separate page | ✅ Yes (annual QMS Audit Program required) |
| QMS Audit Plans | ✅ Embedded in `QMSProgramDetailPage` (removed from sidebar Mar 2026) | ❌ No separate page | ✅ Yes (each audit needs an Audit Plan) |
| QMS Checklists | ✅ Embedded in `QMSPlanDetailPage` (removed from sidebar Mar 2026) | ❌ No | ✅ Yes (QAs prepare checklists per assigned process) |
| QMS Audit Reports | ✅ Yes (10-stage governance lifecycle) | ✅ Yes ("Quality Audits" — simplified 4 fields) | ✅ Yes (full report chain: MRM → Audit Committee → Commission) |
| Non-Conformances | ✅ Yes (standalone, dispute/resolve) | ❌ No separate page | ✅ Yes (NCs must be tracked, closed, monitored monthly) |

**Score: Current = 14/15 menu items required by SRS. Demo = 7/15.**

---

## 2. RISK SETTINGS — THE CRITICAL GAP

This is where the Demo UI is **better than Current Implementation**.

### 2.1 What Demo UI Has (dedicated Risk Settings page) — FOR REFERENCE ONLY

> **Decision: We are NOT creating a dedicated `/service/grc/risk-settings` page.**
> All risk configuration tables will be added to the existing `/service/grc/configuration` page.

URL: `/service/grc/risk-settings` (demo only — not adopted)

The demo UI has a tabbed settings page with six reference data tables:

| Tab | Description | Demo Fields | SRS Need |
|-----|-------------|-------------|----------|
| **Strategic Objectives** | Org objectives for risk alignment | Code, Objective | ✅ Risk treatment must align to strategic objectives |
| **Risk Category** | Categories for classifying risks | Label | ✅ Risk forms require category (e.g. Strategic, Operational) |
| **Risk Sector** | Sectors for risk classification | Label | ✅ Risk forms require sector (e.g. Health, Services) |
| **Impact** | Impact scoring levels | Score (1-5), Description | ✅ SRS: "capture risk likelihood, impact" — needs configurable scale |
| **Likelihood** | Likelihood scoring levels | Score (1-5), Description | ✅ SRS: "Likelihood rating" data requirement |
| **Risk Rate** | Classifications by score range | Score Range, Description | ✅ SRS: "risk ratings" required for assessment |

### 2.2 Current GRC Configuration page — What Exists and What to Add

**Decision: Extend `/service/grc/configuration` with the missing risk tabs.**

In GRC Configuration (`/service/grc/configuration`) — already exists:
- Fiscal Years
- **Severities** (partial overlap with Risk Rate — verify if same or different)
- Finding Types
- **Risk Ratings** (partial overlap with Risk Rate — verify if same or different)
- Audit Opinions

**To ADD to the configuration page (required by SRS, currently missing):**
- ➕ Risk Categories (needed by Departmental Risk and IRR entry forms)
- ➕ Risk Sectors (needed by Departmental Risk and IRR entry forms)
- ➕ Strategic Objectives (needed for risk alignment tracking)
- ➕ Impact Levels — Score (1–5) + Description (needed for quantitative assessment)
- ➕ Likelihood Levels — Score (1–5) + Description (needed for quantitative assessment)
- ➕ Risk Rates — Score Range (e.g. 1–4) + Description (e.g. Low) — verify vs existing "Risk Ratings" tab first

> **Before implementing Risk Rates:** Check if the existing "Risk Ratings" tab in the config page already covers this (score range → Low/Medium/High/Extreme classification). If yes, extend or rename it rather than creating a duplicate tab.

### 2.3 Why This Matters

Without these config tables:
- The Departmental Risk form cannot offer Category dropdown, Sector dropdown, Likelihood scale, Impact scale
- Users cannot compute `Risk Rate = f(Likelihood score × Impact score)`
- Strategic alignment cannot be tracked
- The entire quantitative risk calculation chain is broken

**These tables must be implemented — in the GRC Configuration page (not a dedicated page).**

---

## 3. PROCESS FLOW ALIGNMENT WITH SRS

### 3.1 Risk Assessment Sheet — CURRENT WINS

**SRS FCC_SBP_RMQA_03 requires:**
> RC coordinates risk assessment using the Risk Assessment Sheet →
> submitted to Director/Manager for review →
> upon agreement, RC forwards to RMQAM →
> RMQAM reviews and approves (or returns for rework) →
> consolidated into Departmental Risk Register

| Step | Current Implementation | Demo UI |
|------|------------------------|---------|
| RC fills Risk Assessment Sheet | ✅ `RiskAssessmentSheetsPage` | ❌ Not present |
| Submit to Head of Dept | ✅ status: `submitted_to_head` → `head_endorsed` | ❌ |
| Submit to RMQAM | ✅ status: `submitted_to_rmqam` | ❌ |
| RMQAM Approve / Return for Rework | ✅ `approved` / `returned_for_rework` + return comments | ❌ |
| Consolidated into Dept Register | ✅ Dept Register contains entries | ✅ (flat list, but no worksheet step) |

**Assessment:** Current implementation correctly enforces the 6-step assessment sheet approval chain required by SRS. The Demo skips directly to risk entries in the register with no intermediate worksheet approval step.

### 3.2 Quality Auditor Appointment — CURRENT WINS

**SRS FCC_SBP_RMQA_06 requires:**
> RMQAM requests nomination →
> Nominees undergo ISO 9001:2015 training →
> Sit for QMS Audit examination (75%+ to pass) →
> Max 2 attempts, else replacement →
> Pass → DG appointment letter

| Step | Current Implementation | Demo UI |
|------|------------------------|---------|
| QA Training (ISO 9001:2015) | ✅ `QATrainingPage` + `QATrainingDetailPage` (trainer, date, venue, attendees, approve/reject) | ❌ Not present |
| Exam result tracking | ✅ `exam_score`, `attempt_count` on auditor detail | ❌ Not tracked |
| Max 2 attempts rule | ✅ `attempt_count` in QualityAuditor model | ❌ |
| Certification flag | ✅ `is_certified` visible on detail page | ✅ `Certification Status: Certified` |
| Appointment section | ✅ `QAAppointmentSection` (only when `is_certified=true`) | ✅ Basic |

**Assessment:** Current SRS compliance is strong. Demo shows only the final appointment with no training/exam lifecycle.

### 3.3 QMS Audit Governance Chain — CURRENT WINS

**SRS FCC_SBP_RMQA_07 and System Req 4.11.1.4 requires 10+ steps including:**
> QA prepares report → TL signs → Auditee signs → Submit to RMQAM →
> Present at MRM → Record MRM directives → Submit to Audit Committee →
> Audit Committee review → Commission adoption

| Governance Stage | Current Implementation | Demo UI |
|-|-|-|
| draft | ✅ | ✅ (Scheduled, In Progress) |
| TL signed | ✅ `tl_signed` + `Sign as TL` button | ❌ |
| Auditee acknowledged | ✅ `auditee_acknowledged` + `Sign as Auditee` button | ❌ |
| Finalised | ✅ `finalised` | ✅ (limited) |
| Submitted to RMQAM | ✅ `submitted_to_rmqam` | ❌ |
| Returned for revision | ✅ `returned_for_revision` + dialog | ❌ |
| Presented at MRM | ✅ `presented_at_mrm` | ❌ |
| MRM Directives recorded | ✅ `directives_received` + dialog | ❌ |
| Submitted to Audit Committee | ✅ `submitted_to_audit_committee` | ❌ |
| Audit Committee reviewed | ✅ `audit_committee_reviewed` | ❌ |
| Adopted by Commission | ✅ `adopted_by_commission` | ❌ |

**Assessment:** Current implementation fully satisfies the SRS requirement to escalate QMS findings from RMQAM → Management → Audit Committee → Commission.

### 3.4 Departmental Risk Register Structure — PARTIAL DIFFERENCE

Both have Departmental Risks, but the structure differs:

| Aspect | Current Implementation | Demo UI | SRS Position |
|--------|------------------------|---------|--------------|
| Record structure | **Register** (container) + **Entries** (individual risks) | **Flat list** of individual risks directly | Either works; SRS calls it "Risk Register" |
| Risk data fields | Entries section (detail not shown in current_implementation_ui.md) | Title, Description, Causes, Consequences, Category, Sector, Likelihood, Impact, Risk Rate, Indicator, Supporting Owners | SRS requires all these fields |
| Reporting period | ✅ Per register | Not explicit | ✅ SRS: semi-annual occurrence |
| Causes field | Unknown (in entry dialog) | ✅ Present | ✅ SRS: data requirement |
| Consequences field | Unknown (in entry dialog) | ✅ Present | ✅ SRS: data requirement |
| Supporting Owners | Unknown | ✅ Multi-select supporting owners | ✅ SRS: mentions multiple stakeholders |

**Note:** The Demo UI's Departmental Risk form fields (Causes, Consequences, Supporting Owners, mapped Category/Sector/Likelihood/Impact dropdowns) are worth adopting into the current implementation's entry creation dialogs, **provided the Risk Settings config tables are implemented first**.

### 3.5 Risk Treatment Plan — PARTIAL DIFFERENCE

| Aspect | Current Implementation | Demo UI | SRS Position |
|--------|------------------------|---------|--------------|
| Linked to IRR | ✅ Yes — RTAP linked to an approved IRR | Per-risk individual RTAP | SRS says RTAP is compiled alongside IRR |
| RTAP Items | ✅ `RTAPItemsSection` per RTAP | No separate items section (fields inline) | SRS: RTAP has individual control measures |
| KCI field | Unknown | ✅ Present | ✅ SRS: Key Control Indicator required |
| Effectiveness % | Unknown | ✅ Preventive + Corrective % ratings | ✅ SRS: "Implementation rate" indicator |
| Quarterly Updates | API exists, no UI section | Not shown | ✅ SRS: quarterly reporting on implementation status |
| Send Reminder to RCs | ✅ Button when status=active | ❌ | ✅ SRS: "RMO sends email to RCs reminding them to submit status" |

---

## 4. FIELD-LEVEL ALIGNMENT WITH SRS DATA REQUIREMENTS

### 4.1 Risk Assessment Sheet — SRS Data Requirements met

**SRS requires:** Risk description, Likelihood rating, Impact rating, Existing controls, Risk owner, Risk level (inherent & residual)

| Field | Current RAS form | Demo (Dept Risk form) |
|-------|------------------|-----------------------|
| Risk Description | ✅ | ✅ (via Risk Title + Description) |
| Likelihood Rating | ✅ | ✅ (dropdown, needs config) |
| Impact Rating | ✅ | ✅ (dropdown, needs config) |
| Existing Controls | ✅ | ❌ Not shown |
| Proposed Controls | ✅ | ❌ Not shown |
| Risk Owner | ✅ | ✅ (Principal Risk Owner) |
| Inherent Risk Level | ✅ | ❌ (shows "Risk Level" computed) |
| Residual Risk Level | ✅ | ❌ |
| Causes | Unknown | ✅ |
| Consequences | Unknown | ✅ |
| Risk Category | ✅ | ✅ |
| Sector | ✅ | ✅ |
| Risk Indicator | Unknown | ✅ |
| Supporting Owners | Unknown | ✅ multi-select |

### 4.2 RTAP Fields — SRS requires implementation tracking

**SRS requires:** Risk ID, Control description, Implementation status (Not Started / In Progress / Completed), Supporting comments or evidence, Responsible officers, Completion status

| Field | Current RTAP | Demo RTAP |
|-------|--------------|-----------|
| Linked risk | ✅ (IRR reference) | ✅ (Select Risk from Dept Risks) |
| Control description | ✅ (RTAP items) | ✅ (Mitigation/Control field) |
| KCI | Unknown | ✅ |
| Preventive effectiveness | Unknown | ✅ (Effective / Partially / Not) |
| Preventive rating (%) | Unknown | ✅ |
| Corrective effectiveness | Unknown | ✅ |
| Corrective rating (%) | Unknown | ✅ |
| Resources Required | Unknown | ✅ |
| Quarterly update tracking | API exists, no UI | ❌ |

---

## 5. SUMMARY: WHAT EACH DESIGN DOES WELL vs SRS

### 5.1 Current Implementation Strengths (SRS-aligned)

1. **Risk Assessment Sheets** — full multi-step approval workflow (RC → Head → RMQAM) matching FCC_SBP_RMQA_03 exactly
2. **IRR governance** — notifications (Directors + RCs), activity reports, distribution to directorates → matches FCC_SBP_RMQA_04 multi-step process
3. **RTAP Send Reminder** — built-in reminder to RCs to submit implementation status → matches FCC_SBP_RMQA_05 step 1
4. **Quarterly Performance Reports** — dedicated page with workflow → matches FCC_SBP_RMQA_05 output requirement
5. **Risk Meetings** — Risk and Governance Committee meetings tracked → SRS references committee meetings throughout
6. **QA Training lifecycle** — training → exam → certification → appointment → matches FCC_SBP_RMQA_06 fully
7. **QMS Audit Programs** — annual QMS audit program with approval workflow → matches conducting quality audit process
8. **QMS Audit Plans** — standalone with team assignment and timetable → maps to SRS audit plan preparation step
9. **QMS Checklists** — QAs prepare checklists per assigned ISO clauses → matches SRS "Preparation of Audit Checklists"
10. **QMS Audit Report 10-stage governance** — TL sign → Auditee sign → RMQAM → MRM → Directives → Audit Committee → Commission → fully matches SRS 4.11.1.4 steps 9–13
11. **Non-Conformances** — standalone tracking with dispute/resolve lifecycle → matches SRS "Implementation of Non-Conformances and Areas for Improvement"
12. **Risk Dashboard** — comparative analysis chart → matches SRS monitoring and reporting requirements

### 5.2 Demo UI Strengths (better than Current for certain things)

1. **Dedicated Risk Settings page** — the only place that has Strategic Objectives, Risk Categories, Risk Sectors, Impact Levels (with score), Likelihood Levels (with score), Risk Rates (with score range) → **these are the reference tables required by all risk assessment forms** — currently MISSING from implementation
2. **Risk form field richness** — Departmental Risk and IRR creation forms include Causes, Consequences, Risk Indicator, Supporting Owners fields that aren't confirmed in current dialogs
3. **RTAP field richness** — KCI, Preventive/Corrective Effectiveness dropdown + percentage explicitly visible — confirm these are in current implementation's dialogs
4. **Simpler navigation for basic risk entry** — for users who just need to add a risk, the demo's flat list approach is lower friction than the current register→entries pattern

### 5.3 Gaps in BOTH Designs vs Full SRS

| Gap | SRS Reference | Status |
|-----|---------------|--------|
| RTAP Item quarterly updates UI section | FCC_SBP_RMQA_05 — quarterly status from RCs | API exists, no UI in either |
| RTAP KCI + effectiveness % fields visible | FCC_SBP_RMQA_05 data requirements | Unknown if in current dialogs |
| Causes + Consequences fields in DeptRisk entries | SRS data requirements | Unknown if in current entry dialog |
| Risk Indicator field | SRS data requirements | Unknown if in current forms |
| Supporting Owners multi-select | SRS mentions multiple responsible parties | Unknown if in current forms |
| Strategic Objectives alignment tracking | SRS: "align with strategic objectives" | Neither fully implements this |
| Non-disclosure form for audit | FCC_SBP_RMQA_07 — entry meeting | Not in either |
| Awareness session management | System req 4.11.1.1 item 1 | Not in either |

---

## 6. FINAL RECOMMENDATION

### Verdict: **Current Implementation is the better SRS-aligned foundation**

The current implementation correctly implements:
- The multi-step approval chain for risk assessment sheets
- The full QA auditor certification lifecycle
- The complete QMS audit governance chain (to Commission adoption)
- All supporting processes (QA Training, QMS Programs, QMS Plans, QMS Checklists, Non-Conformances, Performance Reports, Risk Meetings)
- Proper workflow integration for governance-level entities

The Demo UI is a **simplified version** that skips critical intermediate steps required by SRS.

### What to Add to Current Implementation (from Demo UI learnings)

| Priority | Item | Action |
|----------|------|--------|
| 🔴 **CRITICAL** | Risk Settings configuration tables | Add to **`/service/grc/configuration`**: Risk Categories, Risk Sectors, Strategic Objectives, Impact Levels (score 1–5), Likelihood Levels (score 1–5), Risk Rates (score range → label). **Do NOT create a separate `/service/grc/risk-settings` page.** Verify first whether existing "Risk Ratings" tab already covers Risk Rates to avoid duplication. |
| 🟡 Medium | Verify DeptRisk entry fields | Confirm `CreateDeptRegisterEntryDialog` includes: Risk Title, Description, Causes, Consequences, Category (dropdown from config), Sector (dropdown from config), Likelihood (from config), Impact (from config), Risk Rate (computed), Risk Indicator, Supporting Owners (multi-select) |
| 🟡 Medium | Verify IRR entry fields | Confirm `CreateIRREntryDialog` has same richness of fields as above |
| 🟡 Medium | Verify RTAP item fields | Confirm `CreateRTAPItemDialog` includes: KCI, Effectiveness of Preventive Controls (dropdown), Preventive Rating %, Effectiveness of Corrective Controls, Corrective Rating %, Resources Required |
| 🟠 Low-Medium | RTAP Quarterly Updates UI | Add a "Quarterly Updates" section to `RTAPDetailPage` using existing `risk/rtap-items/quarterly-updates/` API endpoint — SRS FCC_SBP_RMQA_05 requires quarterly status reporting from RCs |
| 🟠 Low | Strategic Objectives in risk forms | Once Strategic Objectives config table exists, link it to Departmental Risk and IRR entries for alignment tracking |

### Do NOT switch to the Demo UI structure because:

1. ❌ Demo has NO Risk Assessment Sheets — this is a core SRS process tool
2. ❌ Demo has NO QA Training — violates mandatory ISO training requirement
3. ❌ Demo has NO QMS Programs or standalone QMS Plans/Checklists
4. ❌ Demo's QMS Audit status lifecycle is severely truncated (SRS requires 10+ stages)
5. ❌ Demo has NO Non-Conformance tracking page
6. ❌ Demo has NO Performance Reports
7. ❌ Demo has NO Risk Meetings
8. ❌ Demo's QA auditor detail has no exam tracking (violates 75%/2-attempt rule in SRS)

---

## 7. IMPLEMENTATION ORDER

Based on the gaps identified in this document, this is the sequenced implementation plan.
Dependencies flow top-down — each phase unlocks the one below it.

### Phase 0 — Configuration Page Redesign (prerequisite for everything)

| # | Task | Details | Blocked By |
|---|------|---------|------------|
| 0.1 | Redesign `/service/grc/configuration` page | Add two-section layout: **Internal Audit** section (existing 5 tabs) + **Risk Management** section (6 new tabs). See Appendix B for design. | Nothing |
| 0.2 | Implement Risk Categories tab | CRUD table: `label` field | 0.1 |
| 0.3 | Implement Risk Sectors tab | CRUD table: `label` field | 0.1 |
| 0.4 | Implement Strategic Objectives tab | CRUD table: `code`, `objective` fields | 0.1 |
| 0.5 | Implement Impact Levels tab | CRUD table: `score` (1–5), `description` fields | 0.1 |
| 0.6 | Implement Likelihood Levels tab | CRUD table: `score` (1–5), `description` fields | 0.1 |
| 0.7 | Verify existing Risk Ratings tab vs Risk Rates | If Risk Ratings already has score-range → label mapping, rename/extend it. If not, add a Risk Rates tab: `min_score`, `max_score`, `description` | 0.1 |

### Phase 1 — Risk Form Field Enrichment (depends on Phase 0)

| # | Task | Details | Blocked By |
|---|------|---------|------------|
| 1.1 | Verify & enrich DeptRisk entry fields | Confirm `CreateDeptRegisterEntryDialog` has: Causes, Consequences, Category (dropdown from 0.2), Sector (dropdown from 0.3), Likelihood (from 0.6), Impact (from 0.5), Risk Rate (computed), Risk Indicator, Supporting Owners (multi-select). Add any missing. | 0.2–0.7 |
| 1.2 | Verify & enrich IRR entry fields | Same field set as 1.1 applied to `CreateIRREntryDialog` | 0.2–0.7 |
| 1.3 | Verify & enrich RTAP item fields | Confirm `CreateRTAPItemDialog` has: KCI, Preventive Effectiveness (dropdown), Preventive Rating %, Corrective Effectiveness, Corrective Rating %, Resources Required. Add any missing. | 0.2–0.7 |
| 1.4 | Strategic Objectives linkage | Add Strategic Objective selector to DeptRisk and IRR entry forms for alignment tracking | 0.4 |

### Phase 2 — Remaining UI Gaps (independent of Phase 1)

| # | Task | Details | Blocked By |
|---|------|---------|------------|
| 2.1 | RTAP Quarterly Updates UI | Add "Quarterly Updates" section to `RTAPDetailPage` using existing `risk/rtap-items/quarterly-updates/` API — SRS FCC_SBP_RMQA_05 requires quarterly status reporting from RCs | Nothing (API exists) |

### Phase 3 — Low Priority / Future

| # | Task | Details | Blocked By |
|---|------|---------|------------|
| 3.1 | Non-disclosure form for audit | FCC_SBP_RMQA_07 — entry meeting artifact | Design needed |
| 3.2 | Awareness session management | System req 4.11.1.1 item 1 | Design needed |

### Implementation Sequence Diagram

```
Phase 0:  Config Page Redesign
            │
            ├── 0.2 Risk Categories
            ├── 0.3 Risk Sectors
            ├── 0.4 Strategic Objectives
            ├── 0.5 Impact Levels
            ├── 0.6 Likelihood Levels
            └── 0.7 Risk Rates (verify vs Risk Ratings)
                    │
                    ▼
Phase 1:  Form Field Enrichment
            ├── 1.1 DeptRisk entry fields
            ├── 1.2 IRR entry fields
            ├── 1.3 RTAP item fields
            └── 1.4 Strategic Objectives linkage
                    │
                    ▼
Phase 2:  RTAP Quarterly Updates UI  (can run in parallel with Phase 1)
                    │
                    ▼
Phase 3:  Future items (non-disclosure form, awareness sessions)
```

---

## APPENDIX A: Side-by-Side Screenshots Summary

### Risk Management Sidebar

```
CURRENT IMPLEMENTATION          DEMO UI
─────────────────────────       ─────────────────────────
[Risk Management]  (8)          [Risk Management]
  Risk Dashboard                  Risk Settings ← better
  Risk Champions                  Risk Champions
  Risk Assessment Sheets ← better (MISSING in demo)
  Departmental Risks              Departmental Risks
  Institutional Risks             Institutional Risks
  Risk Treatment Plans            Risk Treatment Plans
  Performance Reports ← better  (MISSING in demo)
  Risk Meetings ← better        (MISSING in demo)

[Quality Assurance]  (5)        [Quality Assurance]
  Quality Auditors                Quality Auditors
  QA Training ← better          (MISSING in demo)
  QMS Programs ← better         (MISSING in demo)
    └─ Audit Plans (embedded)    (MISSING in demo)
         └─ Checklists (embedded)(MISSING in demo)
  QMS Audit Reports ← better      Quality Audits (simplified)
  Non-Conformances ← better     (MISSING in demo)

  [REMOVED from sidebar — now embedded]
  QMS Audit Plans   → section inside QMSProgramDetailPage
  QMS Checklists    → section inside QMSPlanDetailPage
```

---

## APPENDIX B: Configuration Page Redesign — Two-Section Layout

### The Problem

The current `/service/grc/configuration` page (`ConfigurationManagementPage.tsx`) has:
- A single flat `<Tabs>` bar with `grid-cols-5`
- 5 tabs: Fiscal Years, Severities, Finding Types, Risk Ratings, Audit Opinions
- All tabs are **Internal Audit** settings
- Page subtitle says: "Manage lookup tables and system configuration for **audit operations**"

We need to add 6 **Risk Management** config tabs. Putting 11 tabs in a single flat bar is:
- Visually broken (`grid-cols-11` won't fit)
- Semantically confusing (Internal Audit and Risk Management tabs mixed together)

### The Design: Two-Section Grouped Layout

Replace the single flat tab bar with a **section selector** (top level) + **tabs within each section**.

```
┌─────────────────────────────────────────────────────────────────┐
│  GRC Configuration                                              │
│  Manage lookup tables and system configuration for GRC modules  │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  Internal Audit   │  │ Risk Management  │     ← section btns │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                 │
│  ═══════════════════════════════════════════                     │
│                                                                 │
│  When "Internal Audit" is selected:                              │
│  [Fiscal Years] [Severities] [Finding Types]                    │
│  [Risk Ratings] [Audit Opinions]                                │
│       ↓ tab content renders below                               │
│                                                                 │
│  When "Risk Management" is selected:                             │
│  [Risk Categories] [Risk Sectors] [Strategic Objectives]        │
│  [Impact Levels] [Likelihood Levels] [Risk Rates]               │
│       ↓ tab content renders below                               │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Approach

**State model:**
```tsx
const [activeSection, setActiveSection] = useState<'internal-audit' | 'risk-management'>('internal-audit');
const [activeIATab, setActiveIATab] = useState('fiscal-years');
const [activeRMTab, setActiveRMTab] = useState('risk-categories');
```

**Section selector** — use two `Button` components (or a second `Tabs` component) for the top-level toggle:
```tsx
<div className="flex gap-2 mb-4">
  <Button
    variant={activeSection === 'internal-audit' ? 'default' : 'outline'}
    onClick={() => setActiveSection('internal-audit')}
  >
    Internal Audit
  </Button>
  <Button
    variant={activeSection === 'risk-management' ? 'default' : 'outline'}
    onClick={() => setActiveSection('risk-management')}
  >
    Risk Management
  </Button>
</div>
```

**Conditional tab bar** — render the appropriate `<Tabs>` based on `activeSection`:
```tsx
{activeSection === 'internal-audit' && (
  <Tabs value={activeIATab} onValueChange={setActiveIATab}>
    <TabsList className="grid w-full grid-cols-5">
      {/* Fiscal Years, Severities, Finding Types, Risk Ratings, Audit Opinions */}
    </TabsList>
    {/* existing TabsContent unchanged */}
  </Tabs>
)}

{activeSection === 'risk-management' && (
  <Tabs value={activeRMTab} onValueChange={setActiveRMTab}>
    <TabsList className="grid w-full grid-cols-3 lg:grid-cols-6">
      {/* Risk Categories, Risk Sectors, Strategic Objectives, Impact Levels, Likelihood Levels, Risk Rates */}
    </TabsList>
    {/* new TabsContent for each Risk Management tab */}
  </Tabs>
)}
```

### Changes Required

| File | Change |
|------|--------|
| `ConfigurationManagementPage.tsx` | Add section toggle + conditional tab bars |
| `ConfigurationManagementPage.tsx` | Update subtitle from "audit operations" to "GRC modules" |
| `components/grc/config/RiskCategoriesTab.tsx` | New — CRUD table for risk categories |
| `components/grc/config/RiskSectorsTab.tsx` | New — CRUD table for risk sectors |
| `components/grc/config/StrategicObjectivesTab.tsx` | New — CRUD table (code + objective) |
| `components/grc/config/ImpactLevelsTab.tsx` | New — CRUD table (score 1–5, description) |
| `components/grc/config/LikelihoodLevelsTab.tsx` | New — CRUD table (score 1–5, description) |
| `components/grc/config/RiskRatesTab.tsx` | New OR extend existing `RiskRatingsTab` (verify overlap first) |
| Backend: `grc-service` | Ensure API endpoints exist for each config table (likely under `risk/config/`) |

### Why This Design

| Alternative | Rejected Because |
|-------------|------------------|
| 11 tabs in one flat bar | Won't fit; mixes unrelated domains |
| Separate `/service/grc/risk-settings` page | SRS doesn't mandate it; splits admin UX; adds sidebar clutter (decision already made — see Section 2) |
| Vertical sidebar nav within config page | Over-engineered for 2 sections; doesn't match existing tab-based pattern |
| Accordion/collapsible sections | Hides tabs; less scannable than the toggle approach |
