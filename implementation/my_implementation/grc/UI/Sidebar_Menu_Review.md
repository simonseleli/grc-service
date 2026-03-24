# Sidebar Menu Structure Review & Optimization
## Risk Management & Quality Assurance — GRC Module

**Review Date:** March 24, 2026
**Source of Truth:** `grc-service/implementation/my_implementation/grc/GRC_SRS/risk/RISK_MANAGEMENT.md`
**Current Implementation Reference:** `grc-service/implementation/my_implementation/grc/GRC_SRS/risk/UI/current_implementation_ui.md`
**Config File:** `frontend/packages/shared/src/config/servicesConfig.ts`

---

## Section 1: Current State Analysis

### 1.1 Existing Sidebar Menu Structure

The GRC module currently has two groups relevant to this review:

**Group: Risk Management (8 items)**

| # | Menu Item | Route | SRS Process |
|---|-----------|-------|-------------|
| 1 | Risk Dashboard | `/service/grc/risk-dashboard` | Cross-process overview |
| 2 | Risk Champions | `/service/grc/risk-champions` | FCC_SBP_RMQA_01 — Appointment of Risk Champions |
| 3 | Risk Assessment Sheets | `/service/grc/risk-assessment-sheets` | FCC_SBP_RMQA_03 — Input to Departmental Register |
| 4 | Departmental Risks | `/service/grc/departmental-risks` | FCC_SBP_RMQA_03 — Development of Departmental Risk Registers |
| 5 | Institutional Risks | `/service/grc/institutional-risks` | FCC_SBP_RMQA_04 — Preparation of Institutional Risk Register |
| 6 | Risk Treatment Plans | `/service/grc/risk-treatment` | FCC_SBP_RMQA_05 — Implementation of Proposed Controls |
| 7 | Performance Reports | `/service/grc/risk-performance-reports` | FCC_SBP_RMQA_05 — Quarterly Performance Report |
| 8 | Risk Meetings | `/service/grc/risk-meetings` | Risk & Governance Committee governance |

**Group: Quality Assurance (7 items)**

| # | Menu Item | Route | SRS Process |
|---|-----------|-------|-------------|
| 1 | Quality Auditors | `/service/grc/quality-auditors` | FCC_SBP_RMQA_06 — Appointment of QA/Champions |
| 2 | QA Training | `/service/grc/qa-training` | Training of QA Champions |
| 3 | QMS Programs | `/service/grc/qms-programs` | QA Planning — annual audit programme |
| 4 | QMS Audit Plans | `/service/grc/qms-plans` | QA Planning — per-programme audit plan |
| 5 | QMS Checklists | `/service/grc/qms-checklists` | QA Execution — checklist used during fieldwork |
| 6 | QMS Audit Reports | `/service/grc/quality-audits` | QA Reporting — report produced from plan execution |
| 7 | Non-Conformances | `/service/grc/non-conformances` | QA Monitoring — NC raised and tracked |

**Total: 15 sidebar items across 2 groups.**

The GRC module as a whole has additional groups — Overview, Commission, Legal, Internal Audit, System — bringing its total sidebar item count significantly higher. The 15 items being reviewed are concentrated in the two domain groups above.

---

### 1.2 Identified Issues

#### Issue 1 — Cognitive Load from Flat QMS Hierarchy
The Quality Assurance group exposes 5 items (QMS Programs, QMS Audit Plans, QMS Checklists, QMS Audit Reports, Non-Conformances) that form a strict sequential process chain. Showing them all as equal sidebar entries implies they are independent entities when in reality:

```
QMS Program
  └── QMS Audit Plan  (belongs to one Program — 1:many)
       ├── QMS Checklists  (scoped to one Plan — 1:many)
       └── QMS Audit Report  (produced from one Plan — 1:1 per plan cycle)
            └── Non-Conformances  (raised from one Report — 1:many)
```

A flat sidebar does not communicate this hierarchy. Users unfamiliar with the process must learn the dependency order through trial and error.

#### Issue 2 — Orphan Navigation Risk
The sidebar entries for QMS Audit Plans, QMS Checklists do not contextually advertise which Program or Plan they belong to. Creating a Plan without first opening a Program creates data entry ambiguity unless the create dialog forces a Program selection.

#### Issue 3 — Risk Management Items are SRS-Sequential but Architecturally Independent
The 8 Risk Management items map to distinct SRS-governed processes with separate actors, separate lifecycles, and separate data stores. Their flat structure does NOT present the same problem as QA because:
- Risk Assessment Sheets are submitted by individual staff — wide access needed
- Each step (RAS → DeptRisk → IRR → RTAP → QPR) involves different actors and workflows
- Cross-process views (e.g., "all RTAP items across all departments") are the primary access pattern, not nested drill-down

The Risk Management structure **does not have a usability issue**; it is appropriately flat.

---

## Section 2: Best Practice Evaluation

### 2.1 Sidebar Design Principles

| Principle | Description | Current Compliance |
|-----------|-------------|-------------------|
| **7 ± 2 Rule** | Each navigation group should ideally contain 5–9 items | ✅ Risk Management: 8 / QA: 7 — both within range |
| **Mental Model Alignment** | Navigation should mirror the user's conceptual model of the domain | ⚠️ QA: flat list does not mirror the hierarchical QMS process |
| **Top-Down Visibility** | Users should be able to start from the highest-level entity and drill down | ⚠️ QA: user can start from a child entity (Plan, Checklist) without seeing its parent Program |
| **Grouping Cohesion** | Items in a group should be strongly related and operable in isolation | ✅ Risk Management: all items are independently operable. ⚠️ QA: Plans/Checklists are not independently operable — they require a parent |
| **Established Precedent** | Follow patterns already in use within the same application | ✅ Internal Audit module uses the embedded (Working Papers-in-Engagement) pattern |
| **SRS Preservation** | Restructuring must not remove access to any SRS-mandated function | MUST comply — see Section 4 |

### 2.2 Comparison with Internal Audit Embedded Pattern

The Internal Audit module demonstrates the reference embedding pattern: **Working Papers are NOT a sidebar item.** They are accessible exclusively as a section embedded in the `EngagementDetailPage`.

Key mechanics of that pattern:
1. `servicesConfig.ts` has NO entry for Working Papers under `Internal Audit`
2. `EngagementDetailPage.tsx` fetches working papers via `useEngagementWorkingPapers(engagementId)`
3. A "Working Papers" card is rendered inline with `+ Add Working Paper` button controlled by `canManageWorkingPapers` and engagement status
4. The route `/service/grc/engagements/:engagementId/working-papers/:paperId` still exists and deep-links to `WorkingPaperDetailPage`
5. The **list** is only visible from within an Engagement; the **detail** page is directly navigable by URL

This pattern works because Working Papers have no meaningful standalone use — they always belong to an engagement. The same reasoning applies to QMS Checklists and, to a slightly lesser degree, QMS Audit Plans.

---

## Section 3: Proposed Structure

### 3.1 Assessment Summary

| Menu Item | Embedding Candidate? | Reasoning |
|-----------|---------------------|-----------|
| Risk Dashboard | ❌ No | Cross-process hub; standalone is correct |
| Risk Champions | ❌ No | SRS FCC_SBP_RMQA_01; distinct appointment process |
| Risk Assessment Sheets | ❌ No | Submitted by individual staff across all departments; wide access required |
| Departmental Risks | ❌ No | Primary lifecycle entity; manages entries + activity reports |
| Institutional Risks | ❌ No | Compiled from dept registers; distinct management scope |
| Risk Treatment Plans | ❌ No | Independent lifecycle; accessed by all RCs for status updates |
| Performance Reports | ❌ No | Quarterly governance output; submitted to Commission level |
| Risk Meetings | ❌ No | Risk & Governance Committee governance; standalone |
| Quality Auditors | ❌ No | Appointment process; standalone |
| QA Training | ❌ No | Training management; standalone |
| QMS Programs | ❌ No | Top-level QA entity; anchor point for the QMS cycle |
| **QMS Audit Plans** | ✅ **YES** | Each plan belongs to exactly one Program; no standalone use outside a Program context |
| **QMS Checklists** | ✅ **YES** | Each checklist is scoped to one Plan; no meaningful use outside a Plan |
| QMS Audit Reports | ❌ No | Final governance output; 10-stage approval chain; needs to be independently browsable by RMQAM and management |
| Non-Conformances | ❌ No | Own dispute/resolve lifecycle; cross-report tracking needed |

**Net effect: 2 items removed from sidebar (QMS Audit Plans, QMS Checklists), reducing QA from 7 to 5 items and the total from 15 to 13.**

---

### 3.2 Proposed Sidebar Structure

#### Risk Management Group — NO CHANGE

```
├── [Risk Management]  (8 items — unchanged)
│   ├── Risk Dashboard
│   ├── Risk Champions
│   ├── Risk Assessment Sheets
│   ├── Departmental Risks
│   ├── Institutional Risks
│   ├── Risk Treatment Plans
│   ├── Performance Reports
│   └── Risk Meetings
```

**Rationale:** Each item is SRS-mandated as a distinct process step with a different primary actor. Flat structure is correct.

---

#### Quality Assurance Group — PARTIAL RESTRUCTURE

```
├── [Quality Assurance]  (5 items — reduced from 7)
│   ├── Quality Auditors
│   ├── QA Training
│   ├── QMS Programs          ← anchor (Programs list QMS Audit Plans as embedded sections)
│   ├── QMS Audit Reports     ← still standalone (governance chain; needs broad visibility)
│   └── Non-Conformances      ← still standalone (cross-report dispute workflow)
│
│   REMOVED from sidebar (embedded instead):
│   ✗ QMS Audit Plans         → embedded section in QMSProgramDetailPage
│   ✗ QMS Checklists          → embedded section in QMSPlanDetailPage
```

---

### 3.3 Old → Proposed Mapping

| Old Access Path | New Access Path | Change |
|-----------------|-----------------|--------|
| Sidebar → QMS Audit Plans → List of all plans | Sidebar → QMS Programs → click a Program → "Audit Plans" section | Plans now scoped to their Program |
| Sidebar → QMS Audit Plans → click a plan → `/qms-plans/:planId` | QMS Program detail → Audit Plans section → click a plan → `/qms-plans/:planId` | Route unchanged; entry point changes |
| Sidebar → QMS Checklists → List of all checklists | QMS Program → Plan → `/qms-plans/:planId` → "Checklists" section | Checklists now scoped to their Plan |
| Sidebar → QMS Checklists → click a checklist → `/qms-checklists/:id` | QMS Plan detail → Checklists section → click a checklist | Route unchanged; entry point changes |

---

### 3.4 Required Implementation Changes

**1. `servicesConfig.ts` (config-only change):**

Remove the two entries:
```ts
// REMOVE:
{ title: 'QMS Audit Plans', url: '/service/grc/qms-plans', icon: CalendarCheck, group: 'Quality Assurance' },
{ title: 'QMS Checklists', url: '/service/grc/qms-checklists', icon: CheckSquare, group: 'Quality Assurance' },
```

---

**2. `QMSProgramDetailPage.tsx` — add Audit Plans embedded section:**

Following the exact pattern of `EngagementDetailPage.tsx → Working Papers`:

```tsx
// Add to QMSProgramDetailPage:
// - Fetch plans scoped to this programId: useQMSAuditPlans({ program: programId })
// - Render "Audit Plans" card with a table/list of plans
// - Show "+ Create Audit Plan" button when canManageQMSPlans && program.status allows
// - Each plan row links to /service/grc/qms-plans/:planId
```

---

**3. `QMSPlanDetailPage.tsx` — add Checklists embedded section:**

Following the same pattern:

```tsx
// Add to QMSPlanDetailPage:
// - Fetch checklists scoped to this planId: useQMSChecklists({ plan: planId })
// - Render "Checklists" card with a list of checklists
// - Show "+ Add Checklist" button when canManageQMSChecklists && plan is in applicable status
// - Each checklist links to its detail (or expands inline)
```

---

**4. Routes (`App.tsx`) — NO CHANGE NEEDED:**

The routes `/service/grc/qms-plans/:planId` and `/service/grc/qms-checklists/:id` remain registered and continue to work. Deep links and external navigation (e.g., from dashboard quick links, email notifications) are unaffected.

---

## Section 4: Impact Analysis

### 4.1 UX Impact

| Aspect | Before | After | Assessment |
|--------|--------|-------|------------|
| Sidebar item count (QA) | 7 | 5 | ✅ Reduced cognitive load |
| QMS Audit Plan discoverability | Sidebar direct | Via QMS Program | ⚠️ One extra click for Plans |
| Context when creating a Plan | Must select Program from dropdown | Auto-scoped to current Program | ✅ Clearer context |
| Checklist visibility | Standalone list (all checklists, all plans) | Scoped to one Plan | ✅ Reduces confusion |
| Access for QMS Audit Reports | Unchanged (standalone sidebar) | Unchanged | ✅ No impact |
| Access for Non-Conformances | Unchanged (standalone sidebar) | Unchanged | ✅ No impact |
| Deep link support | Full | Full (routes unchanged) | ✅ No regression |

**Net UX assessment: Moderate improvement in the QA section with no regression elsewhere.**

---

### 4.2 Maintainability Impact

| Aspect | Impact |
|--------|--------|
| servicesConfig.ts | 2 lines removed — simpler |
| QMSProgramDetailPage.tsx | Moderate addition: 1 new section component |
| QMSPlanDetailPage.tsx | Moderate addition: 1 new section component |
| API (grcService.ts) | No change — existing list endpoints support filtering by foreign key |
| Permissions (useGRCPermissions.tsx) | No change — `canManageQMSPlans` and `canManageQMSChecklists` flags still apply |
| Routes (App.tsx) | No change |

**Overall: Low-to-moderate implementation effort. Follows an established pattern already in the codebase.**

---

### 4.3 SRS Compliance Check

| SRS Requirement | Status After Restructure |
|-----------------|--------------------------|
| QA Planning — QMS Programs | ✅ Standalone sidebar entry unchanged |
| QA Planning — QMS Audit Plans | ✅ Accessible via QMS Program detail; route still valid |
| QA Execution — QMS Checklists | ✅ Accessible via QMS Plan detail; route still valid |
| QA Reporting — QMS Audit Reports | ✅ Standalone sidebar entry unchanged |
| QA Monitoring — Non-Conformances | ✅ Standalone sidebar entry unchanged |
| QA Appointment — Quality Auditors | ✅ Unchanged |
| QA Training | ✅ Unchanged |
| All Risk Management processes | ✅ Fully unchanged — 8 items retained |

**SRS compliance: FULLY MAINTAINED.** No process is removed or made inaccessible. The restructuring changes the entry point, not the capability.

---

### 4.4 Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Users cannot find QMS Audit Plans after change | Low | Onboarding note; QMS Program detail makes Plans prominent |
| Breaking existing direct URLs / bookmarks | None | Routes are unchanged |
| Permission model breaks | None | Permission hooks unchanged |
| Data integrity issues during transition | None | No data model changes; purely frontend config + UI |
| Confusion if Plans need cross-program browsing | Medium | For management views that need ALL plans: a "cross-program plan list" can be added to the Risk Dashboard quick links if ever needed |

---

## Section 5: Final Recommendation

### Decision: 🔄 Partial Restructure — QA Group Only

**Recommended Action:**

| Group | Action | Reason |
|-------|--------|--------|
| Risk Management | ✅ **Keep current structure** | All 8 items are SRS-distinctly mandated processes with independent lifecycles and different actors. Flat structure is semantically correct. |
| Quality Assurance | 🔄 **Embed QMS Audit Plans + QMS Checklists** | They are child entities with no standalone lifecycle. Embedding mirrors the established Working Papers pattern and matches the QA process hierarchy. |

---

### Proposed Final Sidebar (QA Group)

```
[Quality Assurance]
├── Quality Auditors              /service/grc/quality-auditors
├── QA Training                   /service/grc/qa-training
├── QMS Programs                  /service/grc/qms-programs
│   └── [embedded in Program detail page:]
│       └── QMS Audit Plans  (section in QMSProgramDetailPage)
│           └── [embedded in Plan detail page:]
│               └── QMS Checklists  (section in QMSPlanDetailPage)
├── QMS Audit Reports             /service/grc/quality-audits
└── Non-Conformances              /service/grc/non-conformances
```

---

### Implementation Priority

| Phase | Item | Effort | Impact |
|-------|------|--------|--------|
| Phase 1 | Add Audit Plans section to `QMSProgramDetailPage.tsx` | Medium | High |
| Phase 1 | Remove `QMS Audit Plans` from `servicesConfig.ts` | Trivial | — |
| Phase 2 | Add Checklists section to `QMSPlanDetailPage.tsx` | Medium | High |
| Phase 2 | Remove `QMS Checklists` from `servicesConfig.ts` | Trivial | — |
| Out of scope | Risk Management sidebar changes | — | Not recommended |

---

### Design Decisions Log

| Decision | Choice | Date | Rationale |
|----------|--------|------|-----------|
| Risk Management sidebar structure | Keep flat (8 items, no nesting) | Mar 24, 2026 | SRS processes are independent; different actors; flat is semantically correct |
| QMS Audit Plans sidebar entry | Remove — embed in QMSProgramDetailPage | Mar 24, 2026 | Child entity scoped to one Program; mirrors Working Papers pattern |
| QMS Checklists sidebar entry | Remove — embed in QMSPlanDetailPage | Mar 24, 2026 | Execution artifact scoped to one Plan; no standalone use case |
| QMS Audit Reports sidebar entry | Keep standalone | Mar 24, 2026 | 10-stage governance output; RMQAM needs cross-plan browsing |
| Non-Conformances sidebar entry | Keep standalone | Mar 24, 2026 | Own dispute/resolve lifecycle; cross-report management required |

---

## Appendix A: Side-by-Side Comparison

### Current Structure (15 sidebar items in Risk + QA)

```
Risk Management (8)               Quality Assurance (7)
─────────────────                 ─────────────────────
Risk Dashboard                    Quality Auditors
Risk Champions                    QA Training
Risk Assessment Sheets            QMS Programs
Departmental Risks                QMS Audit Plans        ← remove from sidebar
Institutional Risks               QMS Checklists         ← remove from sidebar
Risk Treatment Plans              QMS Audit Reports
Performance Reports               Non-Conformances
Risk Meetings
```

### Proposed Structure (13 sidebar items in Risk + QA)

```
Risk Management (8)               Quality Assurance (5)
─────────────────                 ─────────────────────
Risk Dashboard                    Quality Auditors
Risk Champions                    QA Training
Risk Assessment Sheets            QMS Programs
Departmental Risks                  └── [Plans embedded in Program detail]
Institutional Risks                       └── [Checklists in Plan detail]
Risk Treatment Plans              QMS Audit Reports
Performance Reports               Non-Conformances
Risk Meetings
```

---

## Appendix B: Precedent Reference — Working Papers in Audit Engagements

The embedded pattern this proposal follows is live in the codebase:

| Attribute | Working Papers (IA) | QMS Audit Plans (Proposed) | QMS Checklists (Proposed) |
|-----------|--------------------|-----------------------------|---------------------------|
| Parent entity | Audit Engagement | QMS Program | QMS Audit Plan |
| Sidebar entry | None | None (to be removed) | None (to be removed) |
| List UI location | `EngagementDetailPage.tsx` — "Working Papers" card | `QMSProgramDetailPage.tsx` — "Audit Plans" section | `QMSPlanDetailPage.tsx` — "Checklists" section |
| Detail route | `/engagements/:id/working-papers/:paperId` | `/qms-plans/:planId` (unchanged) | `/qms-checklists/:id` (unchanged) |
| Create button | Condition-gated (status + permission) | Condition-gated (status + permission) | Condition-gated (status + permission) |
| Data fetch | `useEngagementWorkingPapers(engagementId)` | `useQMSAuditPlans({ program: programId })` | `useQMSChecklists({ plan: planId })` |
