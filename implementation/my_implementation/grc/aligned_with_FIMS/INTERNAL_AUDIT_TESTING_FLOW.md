# Internal Audit Module — Frontend Testing Flow

> **Purpose:** Step-by-step manual testing guide for the GRC Internal Audit module.
> Maps every SRS requirement (AUDT2_ext.md) to the actual UI pages, forms, and expected behaviors.
> **Base URL:** `http://localhost:3001` (Staff Portal)
> **Login:** `admin@fcc.go.tz` / `admin123` (superuser — sees all permissions)
> **Navigation:** Sidebar → GRC → Internal Audit section
> **Date:** 2026-02-26

---
HINT:
Internal Auditors (IA)
Chief Internal Auditor (CIA)
Lead Auditor (LA)
P            (PIA)


## Table of Contents

1. [Pre-Conditions](#1-pre-conditions)
2. [Phase 1 — Configuration Setup](#2-phase-1--configuration-setup)
3. [Phase 2 — Audit Universe (SRS 1.8.1 Step 1)](#3-phase-2--audit-universe-srs-181-step-1)
4. [Phase 3 — Auditable Entities (SRS 1.8.1 Step 1)](#4-phase-3--auditable-entities-srs-181-step-1)
5. [Phase 4 — Risk Assessment (SRS 1.8.1 Step 3)](#5-phase-4--risk-assessment-srs-181-step-3)
6. [Phase 5 — Audit Plan / RBIAP (SRS 1.8.1 Steps 2–10)](#6-phase-5--audit-plan--rbiap-srs-181-steps-210)
7. [Phase 6 — Audit Engagement (SRS 1.8.3 Steps 1–3, 9–12)](#7-phase-6--audit-engagement-srs-183-steps-13-912)
   - 7a. [Phase 7a — Audit Memo (GAP 1)](#7a-phase-7a--audit-memo-gap-1--srs-req-1014-18)
   - 7b. [Phase 7b — Declaration of Independence (GAP 2)](#7b-phase-7b--declaration-of-independence-gap-2--srs-req-16-18-38)
   - 7c. [Phase 7c — Audit Survey / Fraud Risk Assessment (GAP 3)](#7c-phase-7c--audit-survey--fraud-risk-assessment-gap-3--srs-req-1921)
   - 7d. [Phase 7d — Risk Control Matrix (GAP 4)](#7d-phase-7d--risk-control-matrix-gap-4--srs-req-22)
   - 7e. [Phase 7e — Audit Program (GAP 5)](#7e-phase-7e--audit-program-gap-5--srs-req-2223)
8. [Phase 7 — Working Papers (SRS 1.8.3 Steps 15–19)](#8-phase-7--working-papers-srs-183-steps-1519)
9. [Phase 8 — Audit Findings (SRS 1.8.3 Steps 15–18)](#9-phase-8--audit-findings-srs-183-steps-1518)
10. [Phase 9 — Audit Recommendations (SRS 1.8.3 Steps 20–24)](#10-phase-9--audit-recommendations-srs-183-steps-2024)
11. [Phase 10 — Implementation Monitoring (SRS 1.8.6)](#11-phase-10--implementation-monitoring-srs-186)
12. [Phase 11 — GRC Dashboard](#12-phase-11--grc-dashboard)
13. [End-to-End SRS Process Mapping](#13-end-to-end-srs-process-mapping)
14. [Phase 12 — Audit Reports (SRS 1.8.3 Steps 20–24, 1.8.5)](#14-phase-12--audit-reports-srs-183-steps-2024-185)
15. [Phase 13 — Audit Meetings (SRS 1.8.3 Steps 14, 17, 24)](#15-phase-13--audit-meetings-srs-183-steps-14-17-24)
16. [Phase 14 — Quarterly Reports (SRS 1.8.5)](#16-phase-14--quarterly-reports-srs-185)

---

## 1. Pre-Conditions

Before testing, confirm services are running:

| Service | URL | Expected |
|---|---|---|
| Frontend (Staff Portal) | `http://localhost:3001` | Login page |
| API Gateway | `http://localhost:8080/health` | 200 OK |
| GRC Service | `http://localhost:8080/api/v1/grc/health/` | `{"status": "healthy"}` |
| IAM Service | `http://localhost:8080/api/v1/auth/login/` | Accepts POST |

**Login Steps:**
1. Go to `http://localhost:3001`
2. Enter `admin@fcc.go.tz` / `admin123`
3. You should see the FIMS Staff Portal dashboard
4. Click **GRC** in the sidebar (or navigate to `/service/grc`)

---

## 2. Phase 1 — Configuration Setup

> **SRS Prerequisite:** System shall provide configurable risk assessment criteria, severity levels, finding types.

**Navigate to:** Sidebar → Internal Audit → **Configuration**
**URL:** `/service/grc/configuration`
**Permission Required:** `grc:config:system:manage`

### Test 2.1 — Fiscal Years Tab

| # | Action | Expected Result |
|---|---|---|
| 2.1.1 | Click "Fiscal Years" tab | See table of fiscal years (may be empty) |
| 2.1.2 | Click "Add Fiscal Year" | Create dialog opens |
| 2.1.3 | Fill: Name=`2025/2026`, Start Date=`2025-07-01`, End Date=`2026-06-30` | Fields accept input |
| 2.1.4 | Click "Create" | Row appears in table. Quarters auto-generated (Q1–Q4) |
| 2.1.5 | Try creating duplicate fiscal year | Should show error / prevent duplicate |
| 2.1.6 | Edit the fiscal year | Edit dialog opens, fields pre-filled |
| 2.1.7 | Delete the fiscal year | Confirm dialog → removed from table |

### Test 2.2 — Severities Tab

| # | Action | Expected Result |
|---|---|---|
| 2.2.1 | Click "Severities" tab | See severity levels (may have defaults) |
| 2.2.2 | Create severity: Name=`Critical`, Level=`1` | Added to table |
| 2.2.3 | Create: `High(2)`, `Medium(3)`, `Low(4)` | All four appear in table |

### Test 2.3 — Finding Types Tab

| # | Action | Expected Result |
|---|---|---|
| 2.3.1 | Click "Finding Types" tab | See finding types list |
| 2.3.2 | Create: Name=`Compliance`, Description=`Non-compliance findings` | Added |
| 2.3.3 | Create: `Financial`, `Operational`, `Control Weakness` | All types appear |

### Test 2.4 — Risk Ratings Tab

| # | Action | Expected Result |
|---|---|---|
| 2.4.1 | Click "Risk Ratings" tab | See risk rating levels |
| 2.4.2 | Create: Name=`High`, Value=`3` | Added |
| 2.4.3 | Create: `Medium(2)`, `Low(1)` | All three appear |

> **Why this matters:** These lookup values are used as SmartSelect dropdowns in Risk Assessment, Findings, and Recommendations forms. Without them, those forms will have empty dropdowns.

---

## 3. Phase 2 — Audit Universe (SRS 1.8.1 Step 1)

> **SRS:** "Internal Auditors (IA) identify Audit Universe representing the potential range of all audit activities that can be audited through consultation with Heads of directorates/units/zones and submit to CIA for review and approval."

**Navigate to:** Sidebar → Internal Audit → **Audit Universe**
**URL:** `/service/grc/audit-universe`

### Test 3.1 — Create Audit Universe

| # | Action | Expected Result |
|---|---|---|
| 3.1.1 | Click **Create Universe** button (top right) | Create dialog opens |
| 3.1.2 | **Fiscal Year** — click dropdown | Shows fiscal years created in Phase 1 |
| 3.1.3 | Select the `2025/2026` fiscal year | Selected, displayed in field |
| 3.1.4 | **Description** — enter: `Annual audit universe covering all FCC directorates, units, and zones for the 2025/2026 fiscal year` | Text accepted (must be 10–2000 chars) |
| 3.1.5 | **Reviewed By** — optionally select a user | User picker dropdown works (SmartSelect) |
| 3.1.6 | Click **Create** | ✅ Row appears in table: Fiscal Year=`2025/2026`, Status=`draft`, description shown |
| 3.1.7 | Try creating another universe for same fiscal year | ❌ Should fail — fiscal year uniqueness constraint |

### Test 3.2 — View Audit Universe List

| # | Action | Expected Result |
|---|---|---|
| 3.2.1 | Check table columns | **Fiscal Year**, **Description**, **Status**, **Created** visible |
| 3.2.2 | Status badge shows `Draft` | Badge with correct color (likely yellow/gray) |
| 3.2.3 | Row action menu shows: View, Edit, Delete | All three action options present |

### Test 3.3 — Edit Audit Universe (Draft Only)

| # | Action | Expected Result |
|---|---|---|
| 3.3.1 | Click Edit on the draft universe | Edit dialog opens with pre-filled fields |
| 3.3.2 | Change description text | Description field editable |
| 3.3.3 | Click Save | Changes saved, table refreshes |

### Test 3.4 — View Audit Universe Detail

> **⚠️ How to open the Detail page:** On the list at `/service/grc/audit-universe`, find your universe row → click the **⋮ (three-dot) action menu** on the right side of the row → select **"View"** (Eye icon). This navigates to the Detail page.

| # | Action | Expected Result |
|---|---|---|
| 3.4.1 | Click **⋮** action menu → **View** (Eye icon) on the universe row | Navigates to `/service/grc/audit-universe/{id}` |
| 3.4.2 | **Left panel** shows: Status=`Draft`, Fiscal Year, Reviewed By, Approved By, Created, Description | All details present and correctly formatted |
| 3.4.3 | **Right panel** shows: Embedded Workflow Console | Workflow console area (may show "No workflow started" initially) |
| 3.4.4 | **Bottom section** shows: Auditable Entities table | Table present with "Add Entity" button |
| 3.4.5 | **Submit for Approval** button visible (top right) | Button present (for draft status with no active workflow) |

### Test 3.5 — Delete Audit Universe

| # | Action | Expected Result |
|---|---|---|
| 3.5.1 | Go back to list, click Delete on the draft universe | Confirmation dialog appears |
| 3.5.2 | Confirm deletion | Universe removed from list |
| 3.5.3 | Re-create it (same steps as 3.1) | Fresh universe ready for next phases |

---


## 4. Phase 3 — Auditable Entities (SRS 1.8.1 Step 1)

> **SRS:** "The system shall allow Internal Auditors (IA) to create, update, and maintain an Audit Universe covering all potential auditable entities (directorates, units, zones, processes, systems, projects)."

**Navigate to:**
1. Sidebar → **Audit Universe** (list page)
2. Find your universe row → click the **⋮ (three-dot) action menu** on the right side of the row
3. Select **"View"** (Eye icon) → opens the **Universe Detail page**
4. Scroll down to the **Auditable Entities** section → click **Add Entity**

> **⚠️ Navigation note:** Auditable Entities do **NOT** have their own sidebar entry. They are **embedded inside the Audit Universe Detail page**. You must "View" a universe first (via the row's ⋮ action menu → View) to see and manage its entities.

### Test 4.1 — Add Entities from Universe Detail Page

| # | Action | Expected Result |
|---|---|---|
| 4.1.1 | On Universe Detail Page, find "Auditable Entities" section | Section visible with table and "Add Entity" button |
| 4.1.2 | Click **Add Entity** | Create dialog opens |
| 4.1.3 | Select Entity Type = `directorate` | Dropdown with: directorate, unit, zone, process, system, project |
| 4.1.4 | Fill: Name=`ICT Directorate`, Code=`ICT-001` | Fields accept input |
| 4.1.5 | Add Description: `Information and Communication Technology Directorate` | Textarea accepts input |
| 4.1.6 | Optionally select Directorate (from org structure) | SmartSelect with Corporate Service org data |
| 4.1.7 | Click Create | ✅ Entity appears in the embedded table |
| 4.1.8 | Add more entities: `Finance Unit (FIN-001, unit)`, `Dar es Salaam Zone (DAR-001, zone)`, `Procurement Process (PROC-001, process)` | Multiple entities in the table |

### Test 4.2 — Entity Type Validation

| # | Action | Expected Result |
|---|---|---|
| 4.2.1 | Try each entity type: directorate, unit, zone, process, system, project | All six types selectable and save correctly |
| 4.2.2 | Try duplicate code within same universe | Should reject duplicate code |
| 4.2.3 | Try adding entity to an `approved` universe | Should be blocked (business guard) |

---

## 5. Phase 4 — Risk Assessment (SRS 1.8.1 Step 3)

> **SRS:** "IA conduct risk assessment, analyze and Score Risks, draft the RBAIP and submit to CIA for review."
> The system shall require IA to select applicable risk factors, assign scores per factor, provide qualitative justifications.

**Navigate to:** Sidebar → Internal Audit → **Risk Assessments**
**URL:** `/service/grc/risk-assessments`

### Test 5.1 — Create Risk Assessment

| # | Action | Expected Result |
|---|---|---|
| 5.1.1 | Click **Create** (+ button) | Create dialog opens |
| 5.1.2 | **Auditable Entity** — SmartSelect dropdown | Shows entities from your universes |
| 5.1.3 | Select `ICT Directorate (ICT-001)` | Entity selected |
| 5.1.4 | **Assessment Period** — enter `2025/2026 Q1` | Text accepted |
| 5.1.5 | **Risk Scores** — fill all 6 categories (0–10 scale): | |
| | Inherent Risk = `7.5` | Number input accepts decimals |
| | Control Effectiveness = `4.0` | |
| | Financial Exposure = `6.0` | |
| | Compliance Risk = `8.0` | |
| | Operational Impact = `5.5` | |
| | Reputational Risk = `3.0` | |
| 5.1.6 | **Overall Risk Rating** — select `High` | SmartSelect from config risk ratings |
| 5.1.7 | **Residual Risk Rating** — select `Medium` | SmartSelect from config risk ratings |
| 5.1.8 | **Justification** — enter: `Based on the review of ICT controls and recent incidents, the inherent risk is high. Existing controls provide moderate mitigation.` (min 20 chars) | Textarea accepts text |
| 5.1.9 | Click **Create** | ✅ Row appears in table: Entity=`ICT Directorate (ICT-001)`, Status=`draft` |

### Test 5.2 — View Risk Assessment Detail

| # | Action | Expected Result |
|---|---|---|
| 5.2.1 | Click **View** on the assessment | Detail dialog opens showing all scores, ratings, justification, personnel |
| 5.2.2 | Verify all 6 risk scores displayed | Each category with its score value |
| 5.2.3 | Overall Rating shows `High`, Residual shows `Medium` | Correctly linked to config data |

### Test 5.3 — Submit Risk Assessment for Review (SRS: "submit to CIA for review")

| # | Action | Expected Result |
|---|---|---|
| 5.3.1 | Click **Progress Update** on the `draft` assessment | Submit/Review dialog opens |
| 5.3.2 | Dialog shows: "Submit for Review" with workflow explanation | Status target: `submitted` |
| 5.3.3 | Click **Submit** | Status changes to `submitted` |
| 5.3.4 | Check table — status badge now shows `Submitted` | ✅ Visual confirmation |

### Test 5.4 — Review Risk Assessment (SRS: "CIA reviews and approves")

> **SRS Note:** The SRS says CIA can "review, comment, approve, or **return** for revision." There is no separate "rejected" status — rejection returns the assessment to `draft` so the IA can revise and resubmit. This follows standard audit practice (reject = return for rework, not a terminal state).

| # | Action | Expected Result |
|---|---|---|
| 5.4.1 | Click **Progress Update** on the `submitted` assessment | Review dialog opens |
| 5.4.2 | Dialog shows: Approve / Reject toggle | Two options visible |
| 5.4.3 | Select **Reject**, enter comment: `Need more justification for compliance risk score` | Comment textarea appears (required for reject) |
| 5.4.4 | Click **Reject** | ✅ Status returns to `draft` (SRS: "return for revision" — IA must revise and resubmit) |
| 5.4.5 | Resubmit: Click **Progress Update** on the `draft` assessment → Submit | Status back to `submitted` |
| 5.4.6 | Click **Progress Update** again → Select **Approve**, no comment required | Review accepted |
| 5.4.7 | Status changes to `reviewed` | ✅ Badge updates |

### Test 5.5 — Approve & Finalize Risk Assessment

| # | Action | Expected Result |
|---|---|---|
| 5.5.1 | Click **Progress Update** on `reviewed` assessment | Approve & Finalize dialog |
| 5.5.2 | Click **Approve** | Status changes to `approved` |
| 5.5.3 | Try editing an `approved` assessment | Should still be possible (no edit lock on approved assessments currently) |

### Test 5.5a — GAP 6: Auto-Calculated Risk Score Verification

> **GAP 6:** The backend calculates two auto-scores from the 6 input fields using configured weights. These are exposed as `auto_risk_score` and `auto_residual_score` in the API response (alias fields for `calculated_weighted_score` and `calculated_residual_score`).

| # | Action | Expected Result |
|---|---|---|
| 5.5a.1 | After creating a risk assessment, click **View** to open the detail dialog | Detail dialog opens |
| 5.5a.2 | Look for **Auto-Calculated Risk Score** badge/field | Should show a non-blank decimal value (e.g. `5.85`) |
| 5.5a.3 | Look for **Auto-Calculated Residual Score** badge/field | Should show a non-blank decimal value |
| 5.5a.4 | Verify API directly: `GET /api/v1/grc/audit/risk-assessments/{id}/` | Response JSON contains `auto_risk_score` and `auto_residual_score` fields |
| 5.5a.5 | Edit the assessment — change `control_effectiveness` from `4.0` to `8.0` → Save | Both auto-scores recalculate automatically on save |
| 5.5a.6 | Reopen detail — verify auto-scores have changed | Scores reflect new input values |
| 5.5a.7 | Enter `0` for all 6 scores | Both auto-scores should be `0.00` |
| 5.5a.8 | Enter `10` for all 6 scores | Both auto-scores should equal the maximum weighted value |

### Test 5.6 — Risk Score Validation

| # | Action | Expected Result |
|---|---|---|
| 5.6.1 | Try creating with score > 10 | Should be rejected (0–10 range) |
| 5.6.2 | Try creating with score < 0 | Should be rejected |
| 5.6.3 | Try submitting without justification (or < 20 chars) | Validation error |
| 5.6.4 | Try submitting without overall risk rating | Validation error |

---

## 6. Phase 5 — Audit Plan / RBIAP (SRS 1.8.1 Steps 2–10)

> **SRS:** The full RBIAP approval workflow:
> - Step 2: CIA reviews and approves the audit universe, assigns IA to conduct risk assessment
> - Step 3: IA drafts the RBAIP and submits to CIA
> - Step 4: CIA reviews and submits to Management
> - Step 5: Management reviews and makes recommendations
> - Step 6: If adopted, CIA submits to Audit Committee
> - Step 7–8: Committee reviews, may request improvement
> - Step 9: Committee approves  
> - Step 10: Committee submits to Commission for noting

**Navigate to:** Sidebar → Internal Audit → **Audit Plans**
**URL:** `/service/grc/audit-plans`

### Test 6.1 — Pre-Condition: Audit Universe Must Be Approved

| # | Action | Expected Result |
|---|---|---|
| 6.1.1 | Go back to Audit Universe, submit your universe for approval | Navigate to universe detail, click "Submit for Approval" |
| 6.1.2 | Workflow starts (WO integration) | Status changes to `under_review`, Workflow Console shows active plan |
| 6.1.3 | In Workflow Console, the CIA Review stage should be active | Stage visible with Approve/Return actions |
| 6.1.4 | Click **Approve** in the workflow console | Universe status → `approved` |

> ⚠️ **If WO service is not fully running:** The workflow console may not show interactive buttons. In that case, you can approve via API: `POST /api/v1/grc/audit/universe/{id}/approve/` with `{"action": "approve"}`.

### Test 6.1a — GAP 11: Auto-Generate Audit Plan Draft

> **GAP 11:** After the universe reaches `approved`, the backend emits a `plan.auto_generated` event. You can also manually trigger plan generation from the Audit Plans page.

| # | Action | Expected Result |
|---|---|---|
| 6.1a.1 | Navigate to Sidebar → **Audit Plans** after approving the universe | Audit Plans list page |
| 6.1a.2 | Check if a plan was **auto-created** in the list (status = `draft`, title includes the fiscal year) | GAP 11 auto-generate hook may have fired on universe approval |
| 6.1a.3 | If no auto-created plan: click **Create Audit Plan** → look for a **"Generate from Universe"** button in the form | Button should be available for approved universes |
| 6.1a.4 | POST directly: `POST /api/v1/grc/audit/plans/generate-draft/` with body `{"audit_universe_id": "<uuid>", "fiscal_year_id": "<uuid>"}` | Response: `{"status": "created", "plan_id": "..."}` — draft plan created |
| 6.1a.5 | Open the generated plan detail | Objectives and scope auto-populated from universe risk assessment data |
| 6.1a.6 | Verify high-risk entities are listed first / prioritised | Entities ordered by `auto_risk_score` descending |
| 6.1a.7 | Check GRC service logs | Should contain: `GAP 11: auto-generated plan draft for universe {id}` |

### Test 6.2 — Create Audit Plan

| # | Action | Expected Result |
|---|---|---|
| 6.2.1 | Navigate to Audit Plans page | List page loads |
| 6.2.2 | Click **Create Audit Plan** | Create dialog opens |
| 6.2.3 | **Reference Number** — leave empty (auto-generated) or enter `RBIAP-2025-001` | Works either way |
| 6.2.4 | **Plan Title** — enter: `Risk Based Annual Internal Audit Plan 2025/2026` (min 5 chars) | Accepted |
| 6.2.5 | **Plan Type** — select `Annual` | Dropdown: Annual, Special Audit, Follow-up |
| 6.2.6 | **Fiscal Year** — select `2025/2026` | SmartSelect |
| 6.2.7 | **Audit Universe** — select the approved universe | SmartSelect (should only show approved universes) |
| 6.2.8 | **Management Comments** — optionally enter text | Optional field |
| 6.2.9 | **Committee Comments** — optionally enter text | Optional field |
| 6.2.10 | Click **Create** | ✅ Plan appears in table: Status=`draft`, Type=`Annual` |

### Test 6.3 — View Audit Plan Detail

> **⚠️ How to open the Detail page:** On the Audit Plans list, find your plan row → click the **⋮ (three-dot) action menu** on the right side of the row → select **"View"** (Eye icon). This navigates to the Detail page.

| # | Action | Expected Result |
|---|---|---|
| 6.3.1 | Click **⋮** action menu → **View** (Eye icon) on the plan row | Navigates to `/service/grc/audit-plans/{id}` |
| 6.3.2 | **Left panel** shows: Status, Plan Type, Fiscal Year, Audit Universe, Prepared By | All details present (read-only) |
| 6.3.3 | If Management/Committee Comments were entered, they appear below | Sections only show when populated |
| 6.3.4 | **Note:** Resource Allocation and Priority Areas sections only appear when populated (these fields exist in the backend model but are not in the Create form — they are for future use) | Sections hidden if empty — this is correct |
| 6.3.5 | **Right panel**: Embedded Workflow Console | Console area present |
| 6.3.6 | **Submit for Approval** button visible (top right, draft status) | Button present |

### Test 6.4 — Submit RBIAP for Approval (SRS Steps 3–10)

The RBIAP approval workflow has **4 stages** matching the SRS process:

| # | Action | Expected Result | SRS Step |
|---|---|---|---|
| 6.4.1 | Click **Submit for Approval** | Workflow starts, status → `management_review` | Step 3: IA submits to CIA |
| 6.4.2 | Workflow Console shows **Stage 1: CIA Review** | CIA can: Approve / Return | Step 4 |
| 6.4.3 | CIA clicks **Approve** in workflow | Stage advances to Stage 2 | Step 4: CIA submits to Management |
| 6.4.4 | Workflow Console shows **Stage 2: Management Review** | Management can: Adopt / Request Changes | Step 5 |
| 6.4.5 | Management clicks **Adopt** | Stage advances to Stage 3 | Step 6: CIA submits to Committee |
| 6.4.6 | Workflow Console shows **Stage 3: Committee Review** | Committee can: Approve / Request Improvement | Step 7 |
| 6.4.7 | (Optional) Committee clicks **Request Improvement** | Stage stays pending, CIA must revise and resubmit | Step 8 |
| 6.4.8 | Committee clicks **Approve** | Stage advances to Stage 4 | Step 9 |
| 6.4.9 | Workflow Console shows **Stage 4: Commission Noting** | Commission can: Note | Step 10 |
| 6.4.10 | Commission clicks **Note** | Workflow complete, plan status → `approved` | Step 10 |

> ⚠️ **Note:** The 4-stage workflow is managed by Work Orchestration Service. The GRC frontend's Embedded Workflow Console renders each stage with its available actions. If WO is not fully running, stages may not progress interactively — but the Submit button and status transition should still work.

### Test 6.5 — Edit/Delete Checks

| # | Action | Expected Result |
|---|---|---|
| 6.5.1 | Try editing a plan in `management_review` | Should be allowed (not in `implementation` yet) |
| 6.5.2 | Try editing a plan in `implementation` status | Should be blocked (business guard) |
| 6.5.3 | Delete a `draft` plan | Allowed |
| 6.5.4 | Try deleting an `approved` plan | Verify behavior — may be blocked |

### Test 6.6 — Plan Type Validation

| # | Action | Expected Result |
|---|---|---|
| 6.6.1 | Create plan with type `Special Audit` | Works — special audits outside the annual cycle |
| 6.6.2 | Create plan with type `Follow-up` | Works — follow-up on previous findings |
| 6.6.3 | Try creating plan without an approved universe | Should fail (business guard: requires approved universe) |

---

## 7. Phase 6 — Audit Engagement (SRS 1.8.3 Steps 1–3, 9–12)

> **SRS 1.8.3:** Conducting Internal Audit — begins with audit team familiarizing with the auditable area, assessing controls, developing audit program, preparing engagement notification.
> - Step 9: CIA approves the audit program and instructs LA to prepare Engagement Notification
> - Step 10–11: LA prepares EN, CIA approves
> - Step 12: EN and notification sent to auditee

**Navigate to:** Sidebar → Internal Audit → **Audit Engagements**
**URL:** `/service/grc/engagements`

### Test 7.1 — Pre-Condition: Plan Must Be Approved

| # | Action | Expected Result |
|---|---|---|
| 7.1.1 | Ensure at least one Audit Plan is in `approved` or `implementation` status | Required for creating engagements |

### Test 7.2 — Create Audit Engagement

| # | Action | Expected Result |
|---|---|---|
| 7.2.1 | Click **Create Engagement** | Create dialog opens |
| 7.2.2 | **Reference Number** — leave empty or enter `ENG-2025-001` | Auto-generated if empty |
| 7.2.3 | **Engagement Title** — enter: `ICT Directorate Systems Audit 2025` (min 5 chars) | Accepted |
| 7.2.4 | **Engagement Type** — select `Planned` | Dropdown: Planned, Unplanned, Special Investigation, Follow-up |
| 7.2.5 | **Audit Plan** — select your approved plan | SmartSelect (only approved/implementation plans) |
| 7.2.6 | **Auditable Entity** — select `ICT Directorate (ICT-001)` | SmartSelect |
| 7.2.7 | **Lead Auditor** — select a user (defaults to current user) | User picker SmartSelect |
| 7.2.8 | **Scope** — enter: `Review of ICT general controls, application controls, and cybersecurity measures` | Textarea |
| 7.2.9 | **Methodology** — enter: `Risk-based approach using COBIT 2019 framework` | Textarea |
| 7.2.10 | **Planned Start Date** — select a future date | Date picker |
| 7.2.11 | **Planned End Date** — select a date after start | Date picker |
| 7.2.12 | Click **Create** | ✅ Engagement appears in table: Status=`planning`, Type=`Planned` |

### Test 7.3 — View Engagement Detail

> **⚠️ How to open the Detail page:** On the Audit Engagements list, find your engagement row → click the **⋮ (three-dot) action menu** on the right side of the row → select **"View"** (Eye icon). This navigates to the Detail page.

| # | Action | Expected Result |
|---|---|---|
| 7.3.1 | Click **⋮** action menu → **View** (Eye icon) on the engagement row | Navigates to `/service/grc/engagements/{id}` |
| 7.3.2 | **Left panel** shows: Status=`Planning`, Type, Audit Plan (title + ref), Auditable Entity, Lead Auditor (display name), Planned Start/End, Scope, Methodology | All correctly populated |
| 7.3.3 | **Right panel**: Embedded Workflow Console | Console area |
| 7.3.4 | **Working Papers** section (bottom) | Empty table with count badge showing `0` |
| 7.3.5 | **Start Engagement Workflow** button (top right) | Visible for `planning` status |

### Test 7.4 — Start Engagement Workflow (SRS: Send Engagement Notification)

The engagement lifecycle workflow has **3 stages**:

| # | Action | Expected Result | SRS Mapping |
|---|---|---|---|
| 7.4.1 | Click **Start Engagement Workflow** | Workflow starts, status → `fieldwork` | EN sent to auditee |
| 7.4.2 | Workflow Console shows **Stage 1: Planning** → completed | First stage auto-completes | SRS Step 12: EN sent |
| 7.4.3 | **Stage 2: Fieldwork** is now active | LA can: Start Reporting | SRS Steps 14–19 |
| 7.4.4 | (After fieldwork done) Click **Start Reporting** in workflow | Stage advances | SRS Step 20 onward |
| 7.4.5 | **Stage 3: Reporting** is now active | LA can: Complete | SRS Steps 20–24 |
| 7.4.6 | Click **Complete** in workflow | Engagement status → `completed` | Final report approved |

> **Note on Notifications (FIMS Architecture):** When the workflow transitions, GRC publishes notification events to Kafka (e.g., `grc.audit_engagement.assigned`) — Work Orchestration Service picks these up and delivers email/in-app notifications to the lead auditor and team members.

### Test 7.5 — Edit/Delete Engagement

| # | Action | Expected Result |
|---|---|---|
| 7.5.1 | Edit engagement in `planning` status | Allowed — all fields editable |
| 7.5.2 | Edit engagement in `fieldwork` status | Allowed (not completed) |
| 7.5.3 | Try editing `completed` engagement | Should be blocked |
| 7.5.4 | Try deleting `completed` engagement | Should be blocked |

---

## 7a. Phase 7a — Audit Memo (GAP 1 — SRS Req 10–14, 18)

> **SRS:** CIA prepares and signs an engagement memo appointing the Lead Auditor and conveying the audit mandate. Goes through CIA → DG review → approval → transmission to Lead Auditor.
> **GAP 9:** After status reaches `approved`, the memo is auto-stamped with QR code + approver signature via DRS (`stamped_document_url` populates).

**Navigate to:** Sidebar → Internal Audit → **Audit Memos** → Click **Create**

### Test 7a.1 — Create Audit Memo

> **⚠️ Model note:** `AuditMemo` links to an **Audit Plan** + **Auditable Entity** — NOT to an Engagement. The engagement is created *after* the memo is approved and transmitted. The memo is essentially the appointment letter that authorises the engagement to start.

| # | Action | Expected Result |
|---|---|---|
| 7a.1.1 | Go to Sidebar → **Audit Memos** | List page loads, empty or existing memos shown |
| 7a.1.2 | Click **Create** | Create dialog opens |
| 7a.1.3 | **Audit Plan** (`audit_plan_id`) — select `RBIAP-2025-001` | SmartSelect — approved/implementation plans only |
| 7a.1.4 | **Auditable Entity** (`auditable_entity_id`) — select `ICT Directorate (ICT-001)` | SmartSelect |
| 7a.1.5 | **Title** (`title`) — enter: `Audit of ICT General Controls — Q3 FY 2025/2026` | Memo subject/title line |
| 7a.1.6 | **Purpose** (`purpose`) — enter memo body text (see SAMPLE_DATA Phase 7a for full text) | Main body TextField |
| 7a.1.7 | **Scope Summary** (`scope_summary`) — enter: `ICT General Controls — access, change management, backup, network security` | Brief scope before full engagement plan (optional) |
| 7a.1.8 | **Lead Auditor** (`lead_auditor`) — leave as current user or enter UUID | Auto-defaults to logged-in user |
| 7a.1.9 | **Audit Team** (`audit_team`) — enter JSON array of team member UUIDs (optional) | e.g. `["uuid1", "uuid2"]` — can leave empty at creation |
| 7a.1.10 | **Timeline Start** (`timeline_start`) — enter: `2026-03-01` | Date picker |
| 7a.1.11 | **Timeline End** (`timeline_end`) — enter: `2026-04-30` | Date picker |
| 7a.1.12 | Click **Create** | ✅ Memo created, status = `draft`, reference auto-generated (e.g. `MEMO-RBIAP-2025-001-001`) |

### Test 7a.2 — View Memo Detail

| # | Action | Expected Result |
|---|---|---|
| 7a.2.1 | Click **View** on the memo row | Detail dialog opens |
| 7a.2.2 | Shows: audit_plan reference, auditable_entity, title, purpose, scope_summary, lead_auditor, timeline_start, timeline_end, prepared_by, status | All fields present |
| 7a.2.3 | `stamped_document_url` is blank at this stage | Download button NOT visible |

### Test 7a.3 — Status Workflow (SRS Steps 10–14)

| # | Action | Expected Result | SRS Mapping |
|---|---|---|---|
| 7a.3.1 | Click **Progress Update** → select `cia_review` | Status → `cia_review` | Step 10: Submitted to CIA |
| 7a.3.2 | Click **Progress Update** → select `dg_review` | Status → `dg_review` | Step 11: CIA submits to DG |
| 7a.3.3 | Click **Progress Update** → select `approved` | Status → `approved` | Step 12: DG approves |
| 7a.3.4 | Click **Progress Update** → select `transmitted` | Status → `transmitted` | Step 14: Transmitted to LA |
| 7a.3.5 | Try reverting to `draft` from `approved` | ❌ Should be blocked (no backward transition) | Business rule |

### Test 7a.4 — GAP 9 Stamp Verification

| # | Action | Expected Result |
|---|---|---|
| 7a.4.1 | After status → `approved`, open detail dialog | Detail dialog shows updated memo |
| 7a.4.2 | If memo has a `document_id` (DRS document linked), check `stamped_document_url` field | Should be populated after stamp hook fires |
| 7a.4.3 | **"Download Approved Memo"** button appears | Only visible when `stamped_document_url` is not null |
| 7a.4.4 | Click download button | Browser downloads/opens the stamped PDF |
| 7a.4.5 | Check GRC service logs | Should contain: `Stamp triggered for audit_memo {id}` |

---

## 7b. Phase 7b — Declaration of Independence (GAP 2 — SRS Req 16, 18, 38)

> **SRS:** Each audit team member must declare independence (or conflicts) before participating in an engagement. CIA reviews declarations with conflicts.
> **How it works:** `declarant_name`, `declarant_role`, and `declarant_user_id` are auto-populated from the logged-in user via auth context (`useAuth`).
> **GAP 9:** After signing, the declaration is auto-stamped via DRS (`stamped_document_url` populates).

**Navigate to:** Sidebar → Internal Audit → **Declarations** → Click **Create**

### Test 7b.1 — Create Declaration (No Conflict)

| # | Action | Expected Result |
|---|---|---|
| 7b.1.1 | Click **Create** | Create dialog opens |
| 7b.1.2 | **Engagement** — select `ICT General Controls Audit 2025/2026` | Dropdown with active engagements |
| 7b.1.3 | **Declarant Name** — auto-filled from logged-in user | Read-only, from `useAuth` context |
| 7b.1.4 | **Declarant Role** — auto-filled (`team_member`) | Pre-filled from auth context |
| 7b.1.5 | **I am independent** toggle — leave **ON** | `has_conflict = false` |
| 7b.1.6 | **Conflict Details** field — NOT shown (toggle is ON) | Conditional field hidden |
| 7b.1.7 | Click **Create** | ✅ Declaration created, status = `pending`, `has_conflict = false` |

### Test 7b.2 — Create Declaration (With Conflict)

| # | Action | Expected Result |
|---|---|---|
| 7b.2.1 | Click **Create** again | New create dialog |
| 7b.2.2 | **Engagement** — select same engagement | Same engagement selected |
| 7b.2.3 | Toggle **I am independent** to **OFF** | `has_conflict = true`, **Conflict Details** field appears |
| 7b.2.4 | **Conflict Details** — enter conflict description (see SAMPLE_DATA Phase 7b) | Required when has_conflict = true |
| 7b.2.5 | Click **Create** | ✅ Declaration created with `has_conflict = true`, conflict_details populated |
| 7b.2.6 | List shows red **"Has Conflict"** badge on that row | Badge visible in list |

### Test 7b.3 — Sign Declaration (SRS: Team Member Signs)

| # | Action | Expected Result |
|---|---|---|
| 7b.3.1 | Find Declaration 1 (no conflict) in list | Row shows status `pending`, green **"Independent"** badge |
| 7b.3.2 | Click **⋮** action menu → **Sign** | Confirmation dialog: *"Are you sure you want to sign?"* |
| 7b.3.3 | Confirm | ✅ Status → `signed`, `is_signed = true`, `signed_at` timestamp set |
| 7b.3.4 | Try signing Declaration 2 (with conflict) | Should be allowed (CIA decision on conflict) |

### Test 7b.4 — List & Detail Verification

| # | Action | Expected Result |
|---|---|---|
| 7b.4.1 | Check list columns | `engagement_reference`, `declarant_name`, `has_conflict` badge, `status` all visible |
| 7b.4.2 | `engagement_reference` shows e.g. `ENG-2025-001` | Not the engagement title — the reference number |
| 7b.4.3 | Click **View** on Declaration 1 | Detail dialog opens |
| 7b.4.4 | Detail shows: `declarant_name`, `declarant_role`, `has_conflict` = No | Correct fields |
| 7b.4.5 | `conflict_details` section NOT shown (has_conflict = false) | Section hidden conditionally |
| 7b.4.6 | `signed_at` timestamp visible | After signing |
| 7b.4.7 | Click **View** on Declaration 2 | Detail dialog shows `conflict_details` section |

### Test 7b.5 — GAP 9 Stamp Verification

| # | Action | Expected Result |
|---|---|---|
| 7b.5.1 | After Declaration 1 is signed, open detail dialog | Detail dialog updated |
| 7b.5.2 | Check `stamped_document_url` field | Populated if `document_id` was linked to DRS document |
| 7b.5.3 | **"Download Signed Declaration"** button appears | Only when `stamped_document_url` is not null |

---

## 7c. Phase 7c — Audit Survey / Fraud Risk Assessment (GAP 3 — SRS Req 19–21)

> **SRS:** LA conducts preliminary survey assessing the control environment, fraud indicators, and scope adequacy. Fraud risk assessment and control assessments inform audit program design.

**Navigate to:** Sidebar → Internal Audit → **Audit Surveys** → Click **Create**

### Test 7c.1 — Create Audit Survey

> **⚠️ Model note:** `AuditSurvey` is **one-per-engagement** (OneToOneField). There is no `title` or `survey_type` field. The survey captures the process assessment, fraud risk, and control assessments via separate structured text and JSON fields.

| # | Action | Expected Result |
|---|---|---|
| 7c.1.1 | Click **Create** | Create dialog opens |
| 7c.1.2 | **Engagement** (`audit_engagement_id`) — select `ICT General Controls Audit 2025/2026` | Engagement dropdown — only one survey allowed per engagement |
| 7c.1.3 | **Surveyed By** (`surveyed_by`) — auto-filled from logged-in user (optional) | UUID field |
| 7c.1.4 | **Survey Date** (`survey_date`) — enter: `2026-03-05` | Date picker |
| 7c.1.5 | **Process Description** (`process_description`) — describe the ICT process area being surveyed | Main description TextField |
| 7c.1.6 | **Control Environment Notes** (`control_environment_notes`) — enter notes on the control environment | TextField |
| 7c.1.7 | **Prior Audit History** (`prior_audit_history`) — enter relevant prior audit findings if any (optional) | TextField |
| 7c.1.8 | **Fraud Risk Assessment** (`fraud_risk_assessment`) — enter narrative risk text (GAP 3 core field) | Free-form TextField |
| 7c.1.9 | **Control Assessments** (`control_assessments`) — enter JSON array of control objects (GAP 3 core field) | JSONField — array of `{control, adequacy, notes}` objects |
| 7c.1.10 | **Preliminary Findings** (`preliminary_findings`) — enter any preliminary observations (optional) | TextField |
| 7c.1.11 | Click **Create** | ✅ Survey created, status = `draft` |

### Test 7c.2 — Fraud Risk Fields (GAP 3 Core Requirements)

| # | Action | Expected Result |
|---|---|---|
| 7c.2.1 | Open survey detail (click **View**) | Detail shows all fields |
| 7c.2.2 | `fraud_risk_assessment` field present and populated | Free-text, no fixed format required |
| 7c.2.3 | `control_assessments` field present | JSON array rendered (or displayed as text) |
| 7c.2.4 | Both fields appear in API response: `GET /api/v1/grc/audit/surveys/{id}/` | GAP 3 fields present in serializer output |

### Test 7c.3 — Status Workflow

> **⚠️ Model note:** `AuditSurvey` has **only 2 statuses**: `draft` and `completed`. There is no `active` or `closed` state.

| # | Action | Expected Result |
|---|---|---|
| 7c.3.1 | Click **Progress Update** → select `completed` | Status → `completed` — survey finalized |
| 7c.3.2 | Try editing a `completed` survey | Should be blocked or restricted |

---

## 7d. Phase 7d — Risk Control Matrix (GAP 4 — SRS Req 22)

> **SRS:** LA documents all identified risks, associated controls, and test plans in a Risk Control Matrix (RCM) before fieldwork begins. The RCM links each risk to a control, assesses design adequacy, and records the test approach.

**Navigate to:** Sidebar → Internal Audit → **Risk Control Matrix** → Click **Create**

### Test 7d.1 — Create RCM

> **⚠️ Model note:** `RiskControlMatrix` is **one-per-engagement** (OneToOneField). It has no `title` or `description` fields — the create form only needs the engagement.

| # | Action | Expected Result |
|---|---|---|
| 7d.1.1 | Click **Create** | Create dialog opens |
| 7d.1.2 | **Engagement** (`audit_engagement_id`) — select `ICT General Controls Audit 2025/2026` | Engagement dropdown — one RCM per engagement |
| 7d.1.3 | **Prepared By** (`prepared_by`) — auto-filled from logged-in user (optional) | UUID field |
| 7d.1.4 | Click **Create** | ✅ RCM created, status = `draft` |

### Test 7d.2 — Add RCM Entries

| # | Action | Expected Result |
|---|---|---|
| 7d.2.1 | Open RCM detail (click **View** or navigate to detail page) | RCM detail page with **RCM Entries** section |
| 7d.2.2 | Click **Add Entry** | Entry create dialog opens |
| 7d.2.3 | **Process Area** (`process_area`) — enter: `User Access Management` | Text field (backend field name — replaces the concept of "Risk Area") |
| 7d.2.4 | **Risk Description** (`risk_description`) — enter: `Unauthorized access due to inadequate access review controls` | Separate risk text field |
| 7d.2.5 | **Risk Rating** (`risk_rating_id`) — select `High Risk` from config | SmartSelect from configured Risk Ratings |
| 7d.2.6 | **Control Description** (`control_description`) — enter: `Quarterly user access reviews to ensure least-privilege access` | Separate control text field |
| 7d.2.7 | **Control Owner** (`control_owner`) — enter: `ICT Director` | Text field |
| 7d.2.8 | **Control Type** (`control_type`) — select `preventive` | Dropdown: `preventive`, `detective`, `corrective` |
| 7d.2.9 | **In Scope** (`in_scope`) — toggle ON | Boolean toggle |
| 7d.2.10 | **Design Adequate** (`design_adequate`) — toggle OFF (control design is flawed) | Boolean toggle |
| 7d.2.11 | **Design Assessment Notes** (`design_assessment_notes`) — enter: `Access review process not formally documented. No evidence of execution in last 12 months. 15 of 42 accounts had excessive privileges.` | Replaces the "Comments" concept — no `test_result` field exists |
| 7d.2.12 | **Test Approach** (`test_approach`) — select `walkthrough` | Dropdown: `walkthrough`, `substantive`, `analytical`, `observation` |
| 7d.2.13 | **Priority** (`priority`) — select `high` | Dropdown: `high`, `medium`, `low` |
| 7d.2.14 | Click **Save** | ✅ RCM Entry created, appears in RCM detail |
| 7d.2.15 | Add a second entry: Process Area = `IT Change Management`, risk_rating = `Medium`, design_adequate = Yes, control_type = `detective`, priority = `medium` | Second entry in table |

### Test 7d.3 — RCM Status Workflow

| # | Action | Expected Result |
|---|---|---|
| 7d.3.1 | Click **Progress Update** → select `submitted` | Status → `submitted` — submitted to CIA |
| 7d.3.2 | Click **Progress Update** → select `approved` | Status → `approved` — CIA approved |
| 7d.3.3 | Try adding entries to an `approved` RCM | Should be blocked after approval |

---

## 7e. Phase 7e — Audit Program (GAP 5 — SRS Req 22–23)

> **SRS:** LA prepares a structured audit program detailing the procedures, objectives, and scope for fieldwork. CIA reviews and approves the program before fieldwork begins.
> **GAP 9:** After status reaches `approved`, the program is auto-stamped via DRS (`stamped_document_url` populates).

**Navigate to:** Sidebar → Internal Audit → **Audit Programs** → Click **Create**

### Test 7e.1 — Create Audit Program

| # | Action | Expected Result |
|---|---|---|
| 7e.1.1 | Click **Create** | Create dialog opens |
| 7e.1.2 | **Engagement** — select `ICT General Controls Audit 2025/2026` | Engagement dropdown |
| 7e.1.3 | **Title** — enter: `ICT General Controls Audit Program — Q3 2025/2026` | Text field |
| 7e.1.4 | **Objectives** (`objectives`) — enter JSON array of objective strings | e.g. `["Assess access controls", "Evaluate change management"]` — JSONField |
| 7e.1.5 | **Procedures** (`procedures`) — enter the audit procedures, methodology, and scope narrative | Single TextField (combines what might be labelled as "description", "scope", or "methodology" in the UI) |
| 7e.1.6 | **Risk Control Matrix** (`risk_control_matrix_id`) — optionally link to the approved RCM | SmartSelect — optional |
| 7e.1.7 | Click **Create** | ✅ Program created, status = `draft`, reference auto-generated |

### Test 7e.2 — Status Workflow (SRS Steps 22–23)

| # | Action | Expected Result | SRS Mapping |
|---|---|---|---|
| 7e.2.1 | Click **Progress Update** → select `under_review` | Status → `under_review` | Step 22: LA submits for CIA review |
| 7e.2.2 | Click **Progress Update** → select `approved` | Status → `approved` | Step 23: CIA approves program |
| 7e.2.3 | Try editing an `approved` program | Should be blocked | Immutable after approval |
| 7e.2.4 | Try adding objectives after approval | Should be blocked | |

### Test 7e.3 — GAP 9 Stamp Verification

| # | Action | Expected Result |
|---|---|---|
| 7e.3.1 | After status → `approved`, open detail dialog | Detail dialog updates |
| 7e.3.2 | Check `stamped_document_url` field | Populated if `document_id` linked to a DRS document |
| 7e.3.3 | **"Download Approved Program"** button appears | Only when `stamped_document_url` is not null |
| 7e.3.4 | Click download | Browser downloads/opens stamped PDF |
| 7e.3.5 | Check GRC service logs | Should contain: `Stamp triggered for audit_program {id}` |

---

## 8. Phase 7 — Working Papers (SRS 1.8.3 Steps 15–19)

> **SRS:**
> - Step 15: Audit Team Members perform tests, document results in Working Papers, submit to LA
> - Step 16: LA reviews working papers for completeness
> - Step 18: LA consolidates working papers, submits for vetting
> - Step 19: CIA reviews and approves working papers

**Navigate to:**
1. Sidebar → **Audit Engagements** (list page)
2. Find your engagement row → click the **⋮ (three-dot) action menu** on the right side of the row
3. Select **"View"** (Eye icon) → opens the **Engagement Detail page**
4. Scroll down to the **Working Papers** section → click **Add Working Paper**

Or via direct URL: `/service/grc/working-papers/{paperId}` (detail page only — no standalone list)

> **⚠️ Navigation note:** Working Papers do **NOT** have their own sidebar entry. They are **embedded inside the Audit Engagement Detail page**. You must "View" an engagement first (via the row's ⋮ action menu → View) to see and manage its working papers.

### Test 8.1 — Create Working Paper

| # | Action | Expected Result |
|---|---|---|
| 8.1.1 | Go to an engagement in `fieldwork` or `reporting` status | Required pre-condition |
| 8.1.2 | On the **Engagement Detail page**, scroll down to the **Working Papers** section | Section with count badge and table |
| 8.1.3 | Click **Add Working Paper** | Create dialog opens |
| 8.1.4 | **Title** — enter: `ICT General Controls Assessment` | Text field |
| 8.1.5 | **Reference Number** — enter: `WP-001` or leave auto | Unique per engagement |
| 8.1.6 | **Paper Type** — select from: `planning`, `fieldwork`, `analysis`, `conclusion`, `other` | Dropdown |
| 8.1.7 | (Optional) **Upload File** — drag or click to attach a document | Supports PDF, Word, Excel, PPT, images (max 25MB) |
| 8.1.8 | Click Create | ✅ Working paper created, appears in engagement's working papers list |

### Test 8.2 — View Working Paper Detail

| # | Action | Expected Result |
|---|---|---|
| 8.2.1 | Click on a working paper link in the engagement detail | Navigates to `/service/grc/working-papers/{id}` |
| 8.2.2 | Shows: Title, Reference Number, Paper Type, Review Status=`draft`, Prepared By, Reviewed By | All details present |
| 8.2.3 | Embedded Workflow Console (right panel) | Console area for WO integration |
| 8.2.4 | **Submit for Approval** button visible (for draft papers) | Only the preparer can submit |

### Test 8.3 — Working Paper Review Workflow (SRS Steps 16, 18–19)

The working paper approval has **2 stages**:

| # | Action | Expected Result | SRS Mapping |
|---|---|---|---|
| 8.3.1 | Click **Submit for Approval** (or POST to `/review/`) | Review status → `pending`, workflow starts | Step 18: Submit for vetting |
| 8.3.2 | Workflow Console shows **Stage 1: Working Paper Review** | Reviewer can: Approve / Reject / Request Changes | Step 16: LA reviews |
| 8.3.3 | Click **Approve** in Stage 1 | Stage advances to Stage 2 | LA approves |
| 8.3.4 | **Stage 2: Working Paper Approval** | Approver (CIA) can: Approve / Reject | Step 19: CIA review |
| 8.3.5 | Click **Approve** in Stage 2 | Review status → `approved`, workflow complete | Step 19: CIA approves |

### Test 8.4 — Working Paper Guards

| # | Action | Expected Result |
|---|---|---|
| 8.4.1 | Only the preparer can edit/delete/submit | Other users cannot perform these actions |
| 8.4.2 | Cannot edit once `approved` | Edit blocked |
| 8.4.3 | Cannot delete once `approved` | Delete blocked |

---


## 9. Phase 8 — Audit Findings (SRS 1.8.3 Steps 15–18)

> **SRS:**
> - Where controls are found inadequate, audit team records as audit findings
> - Finding documentation requires: condition, criteria, cause, effect (The 4 C's)
> - Findings go through: draft → discussed (with auditee) → final

**Navigate to:** Sidebar → Internal Audit → **Audit Findings**
**URL:** `/service/grc/audit-findings`

### Test 9.1 — Pre-Condition: Engagement in Fieldwork or Reporting

| # | Action | Expected Result |
|---|---|---|
| 9.1.1 | Ensure at least one engagement is in `fieldwork` or `reporting` status | Required — findings can only be added during active auditing |

### Test 9.2 — Create Audit Finding

> **Note:** The **Reference Number** is auto-generated by the backend (format: `FND-{engagement_ref}-{sequence}`). There is no reference number field in the create form.

| # | Action | Expected Result |
|---|---|---|
| 9.2.1 | Click **Create** (+ button) | Create dialog opens |
| 9.2.2 | **Audit Engagement** — select your fieldwork engagement | SmartSelect (filters to fieldwork/reporting engagements only) |
| 9.2.3 | **Fiscal Year** — select `2025/2026` | SmartSelect |
| 9.2.4 | **Quarter** — select applicable quarter | SmartSelect (filters by selected fiscal year — changes when fiscal year changes) |
| 9.2.5 | **Finding Title** — enter: `Inadequate Backup and Disaster Recovery Controls` (min 10 chars) | Accepted |
| 9.2.6 | **The 4 C's** (all required, min 20 chars each): | |
| | **Condition:** `The ICT Directorate does not maintain regular offsite backup copies of critical system data. Last verified backup restoration test was conducted over 18 months ago.` | Textarea |
| | **Criteria:** `According to FCC ICT Policy Section 4.2 and ISO 27001 Control A.12.3, organizations shall implement regular backup procedures with periodic restoration testing.` | Textarea |
| | **Cause:** `Absence of a documented backup schedule and restoration testing plan. Budget constraints have delayed procurement of offsite backup infrastructure.` | Textarea |
| | **Effect:** `In the event of a disaster or system failure, critical data may be permanently lost, disrupting FCC regulatory operations for an extended period.` | Textarea |
| 9.2.7 | **Finding Type** — select `Control Weakness` | SmartSelect (from config finding types) |
| 9.2.8 | **Severity** — select `High` | SmartSelect (from config severities) |
| 9.2.9 | **Risk Rating** — select `High` | SmartSelect (from config risk ratings) |
| 9.2.10 | **Auditee Response** — optionally enter text | Optional at draft stage |
| 9.2.11 | **Management Response** — optionally enter text | Optional at draft stage |
| 9.2.12 | Click **Create** | ✅ Finding appears: Status=`draft`, Severity=`High` badge, Reference auto-generated (e.g. `FND-ENG-2026-001-001`) |

### Test 9.3 — View Finding Detail

| # | Action | Expected Result |
|---|---|---|
| 9.3.1 | Click **View** on the finding | Detail dialog opens |
| 9.3.2 | Shows: Reference, Title, Status badge, Severity badge | Header info |
| 9.3.3 | Shows: Engagement reference, Auditable Entity, Finding Type, Fiscal Year, Quarter | Classification |
| 9.3.4 | Shows: Risk Rating, Working Paper ID (if linked) | Scoring |
| 9.3.5 | Shows all 4 C's: Condition, Criteria, Cause, Effect | Full audit finding structure |
| 9.3.6 | Shows: Auditee Response, Management Response (if provided) | Response sections |

### Test 9.4 — Finding Status Transitions

| # | Action | Expected Result | SRS Mapping |
|---|---|---|---|
| 9.4.1 | Click **Progress Update** on `draft` finding | Status dialog opens | |
| 9.4.2 | Select `Discussed` → click Submit | Status → `discussed` | Finding discussed at pre-exit meeting |
| 9.4.3 | Now edit the finding — add Auditee Response and Management Response | Both response fields filled | Auditee provides written response |
| 9.4.4 | Click **Progress Update** on `discussed` finding | Dialog shows: `Final` or `Draft` (revert) | |
| 9.4.5 | Select `Final` → click Submit | Status → `final` | Finding finalized in report |
| 9.4.6 | Try editing a `final` finding | Editing still possible but status cannot go back | Terminal state for workflow |

**Alternative fast path:**
| 9.4.7 | Create a new finding, set status directly to `Final` | `draft` → `final` shortcut available | For retrospective entry |

### Test 9.5 — Finding Validation

| # | Action | Expected Result |
|---|---|---|
| 9.5.1 | Try creating finding for `planning` engagement | Should fail — requires `fieldwork` or `reporting` |
| 9.5.2 | Try creating with title < 10 chars | Validation error |
| 9.5.3 | Try creating with any C field < 20 chars | Validation error |

---

## 10. Phase 9 — Audit Recommendations (SRS 1.8.3 Steps 20–24)

> **SRS:** After audit team meeting, LA consolidates deviations and recommendations. Draft report prepared and submitted. Final report distributed.

**Navigate to:** Sidebar → Internal Audit → **Audit Recommendations**
**URL:** `/service/grc/audit-recommendations`

### Test 10.1 — Pre-Condition: Finding Must Be in Final Status

| # | Action | Expected Result |
|---|---|---|
| 10.1.1 | Ensure at least one finding is `final` | Required — recommendations can only be linked to finalized findings |

### Test 10.2 — Create Audit Recommendation

> **Note:** The **Reference Number** is auto-generated by the backend (format: `REC-{finding_ref}-{sequence}`). There is no reference number field in the create form.

| # | Action | Expected Result |
|---|---|---|
| 10.2.1 | Click **Create** | Create dialog opens |
| 10.2.2 | **Audit Finding** — SmartSelect | Shows only `final` findings |
| 10.2.3 | Select the finalized finding | Finding selected |
| 10.2.4 | **Recommendation Title** — enter: `Implement Automated Backup and Recovery System` (min 10 chars) | Accepted |
| 10.2.5 | **Detailed Recommendation** — enter: `The ICT Directorate should procure and deploy an automated offsite backup solution with daily incremental backups and weekly full backups. Quarterly restoration tests must be conducted and documented. A disaster recovery plan should be formalized and approved within 90 days.` (min 30 chars) | Textarea |
| 10.2.6 | **Priority** — select `High` | SmartSelect: High / Medium / Low |
| 10.2.7 | **Target Completion Date** — select a date at least tomorrow | Date picker (min = tomorrow) |
| 10.2.8 | **Responsible Party** — select a user from dropdown | SmartSelect user picker (fetches users from IAM) |
| 10.2.9 | **Agreed Action Plan** — enter: `Management has agreed to procure backup solution within Q2 2025/2026 and conduct first restoration test by Q3.` (min 10 chars) | Textarea |
| 10.2.10 | Click **Create** | ✅ Recommendation appears: Status=`open`, Priority=`High`, Deadline shown, Reference auto-generated |

### Test 10.3 — Recommendation Status Lifecycle (SRS 1.8.6 Monitoring Flow)

This is the core tracking lifecycle for audit recommendations:

| # | Action | Expected Result | SRS Mapping |
|---|---|---|---|
| 10.3.1 | Click **Progress Update** on `open` recommendation | Status dialog shows target: `In Progress` | IA shares with auditee |
| 10.3.2 | Select `In Progress` → Submit | Status → `in_progress` | Auditee begins implementation |
| 10.3.3 | Click **Progress Update** on `in_progress` | Shows targets: `Implemented` or `Open` (revert) | |
| 10.3.4 | Select `Implemented` | **Implementation Notes** textarea appears (required) | Auditee submits evidence |
| 10.3.5 | Enter notes: `Backup solution deployed. First full backup completed 2025-09-15. Restoration test scheduled for 2025-10-01.` → Submit | Status → `implemented` | Step 3: Auditee responds with evidence |
| 10.3.6 | Click **Progress Update** on `implemented` | Shows targets: `Verified` or `In Progress` (revert) | |
| 10.3.7 | Select `Verified` | **Verification Evidence** textarea appears (required) | IA conducts review |
| 10.3.8 | Enter: `Verified backup logs from 2025-09-15 to 2025-10-01. Restoration test successful per test report dated 2025-10-01.` → Submit | Status → `verified` | Step 5: IA review and analysis |
| 10.3.9 | Click **Progress Update** on `verified` | Shows targets: `Closed` or `In Progress` (revert) | |
| 10.3.10 | Select `Closed` → Submit | Status → `closed` | Final — recommendation fully implemented |
| 10.3.11 | Try any action on `closed` recommendation | No further transitions — locked for audit trail | Terminal state |

### Test 10.4 — Recommendation Guards

| # | Action | Expected Result |
|---|---|---|
| 10.4.1 | Try creating recommendation for `draft` finding | Should fail — requires `final` finding |
| 10.4.2 | Try editing `verified` or `closed` recommendation | Should be blocked |
| 10.4.3 | Try deleting `closed` recommendation | Should be blocked |
| 10.4.4 | Check that `Overdue` endpoint works: recommendations past target date | API: `GET /api/v1/grc/audit/recommendations/overdue/` |

---

## 11. Phase 10 — Implementation Monitoring (SRS 1.8.6)

> **SRS 1.8.6 Monitoring:**
> 1. IA identifies list of unimplemented previous audit recommendations
> 2. IA shares list with auditee for status update
> 3. Auditee responds within 5 days with evidence
> 4. IA compiles implementation status
> 5. IA conducts review and analysis
> 6. IA submits to CIA for final review
> 7. CIA presents to Management

**Navigate to:** Sidebar → Internal Audit → **Audit Monitoring**
**URL:** `/service/grc/audit-monitoring`

### Test 11.1 — Pre-Condition: Recommendation in Progress

| # | Action | Expected Result |
|---|--------|-----------------|
| 11.1.1 | Ensure at least one recommendation is `in_progress` and has no monitoring record | Required |

### Test 11.2 — Create Monitoring Record

| # | Action | Expected Result |
|---|---|---|
| 11.2.1 | Click **Create Monitoring Record** | Create dialog opens |
| 11.2.2 | **Recommendation** — SmartSelect | Shows only `in_progress` recommendations without existing monitoring |
| 11.2.3 | Select the recommendation | Selected |
| 11.2.4 | **Implementation Progress (%)** — enter `25` | Number input (0–100) |
| 11.2.5 | **Next Review Date** — select a date | Date picker |
| 11.2.6 | **Progress Notes** — enter: `Initial procurement process started. RFQ issued to 3 vendors.` | Textarea |
| 11.2.7 | **Reviewed By** — auto-populated with current user | Read-only |
| 11.2.8 | Click **Create** | ✅ Monitoring record appears in table |

### Test 11.3 — View Monitoring Detail

| # | Action | Expected Result |
|---|---|---|
| 11.3.1 | Click **View** on the monitoring record | Detail dialog opens |
| 11.3.2 | Shows: Recommendation title, reference, auditee, priority | Linked recommendation data |
| 11.3.3 | Shows: Engagement reference | Linked back to engagement |
| 11.3.4 | Shows: Progress %, Next Review Date, Last Review Date | Monitoring metrics |
| 11.3.5 | Shows: Progress Notes, Reviewed By, Active status | Details section |

### Test 11.4 — Update Monitoring Progress

| # | Action | Expected Result |
|---|---|---|
| 11.4.1 | Click **Edit** on the monitoring record | Edit dialog opens with pre-filled fields |
| 11.4.2 | Update Progress to `50%` | Slider or number input |
| 11.4.3 | Update Notes: `Vendor selected. Contract signed. Installation scheduled for next month.` | Updated |
| 11.4.4 | Update Next Review Date | New date set |
| 11.4.5 | Click Save | ✅ Record updated in table |

### Test 11.5 — Soft Delete & Restore

| # | Action | Expected Result |
|---|---|---|
| 11.5.1 | Click **Delete** on monitoring record | Confirm dialog → record soft-deleted |
| 11.5.2 | Toggle **Show deleted records** switch | Table shows deleted records (grayed out or marked) |
| 11.5.3 | Click **Restore** on the deleted record | Record restored — visible in main view again |

### Test 11.6 — Due Reviews

| # | Action | Expected Result |
|---|---|---|
| 11.6.1 | API check: `GET /api/v1/grc/audit/implementation-monitoring/due-reviews/` | Returns monitoring records where next_review_date ≤ today |

### Test 11.7 — GAP 7: 5-Day Deadline Enforcement

> **GAP 7:** SRS 1.8.6 Step 3 requires the auditee to respond within **5 days**. The backend enforces this as a minimum `next_review_date` constraint on create/update. The `check_monitoring_deadlines` Celery task auto-flags overdue records daily.

| # | Action | Expected Result |
|---|---|---|
| 11.7.1 | Try creating a monitoring record with `next_review_date` = today | ❌ Validation error: *"Next review date must be at least 5 days from today"* |
| 11.7.2 | Try creating with `next_review_date` = today + 4 days | ❌ Validation error: same message |
| 11.7.3 | Create with `next_review_date` = today + 5 days | ✅ Allowed — minimum gap satisfied |
| 11.7.4 | Create with `next_review_date` = today + 30 days | ✅ Allowed |
| 11.7.5 | Try **editing** an existing record — set `next_review_date` to yesterday | ❌ Validation error on update too |
| 11.7.6 | API: `POST /api/v1/grc/audit/implementation-monitoring/{id}/notify-auditee/` | Response: `{"notification_sent_at": "...", "response_deadline": "<now+5days>", "is_overdue": false}` |
| 11.7.7 | API: `POST /api/v1/grc/audit/implementation-monitoring/{id}/non-responsive/` | Response: `{"is_overdue": true, "escalated": true}` |
| 11.7.8 | After calling non-responsive, reload the list | `is_overdue` badge/indicator visible on that record |
| 11.7.9 | Verify Celery beat schedule: `GET /api/v1/grc/audit/implementation-monitoring/` check `is_overdue` on past-deadline records | Records auto-flagged daily by `check_monitoring_deadlines` task |

---

## 12. Phase 11 — GRC Dashboard

**Navigate to:** Sidebar → **Overview** → Dashboard (or `/service/grc`)

### Test 12.1 — Dashboard Overview

| # | Action | Expected Result |
|---|---|---|
| 12.1.1 | Load the GRC Dashboard | Page loads with summary cards at top (data fetched from `/api/v1/grc/audit/dashboard/stats/`) |
| 12.1.2 | 5 summary stat cards visible | **Total Risk Assessments**, **Active Actions** (open+in_progress recommendations), **Audits Completed**, **Audit Engagements**, **Total Findings** |
| 12.1.3 | Summary cards show **real data** from the database | Values update automatically as you create/modify audit data |
| 12.1.4 | While loading, cards show skeleton placeholders | Brief loading state with animated placeholders |
| 12.1.5 | Click **Internal Audit** tab | Shows navigation cards for all IA modules |
| 12.1.6 | Each module card shows **live counts** | e.g. Audit Plans card shows total + approved count from real data |
| 12.1.7 | Cards present: Risk Based Audit Plans, Audit Universe, Auditable Entities, Engagement Plans, Audit Findings, Internal Audits, Audit Reports, Audit Recommendations, Audit Monitoring, Configuration | All IA module cards visible |
| 12.1.8 | Click any card | Navigates to the respective module page |

---













## 13. End-to-End SRS Process Mapping

This section maps the complete SRS process flow to the sequence of UI actions you should follow during testing:

### 13.1 SRS 1.8.1 — Preparation for Risk Based Annual Internal Audit Plan

| SRS Step | SRS Description | System Page | Test Reference |
|---|---|---|---|
| Pre-condition | Configure system lookups | Configuration | Phase 1 (Tests 2.1–2.4) |
| Step 1 | IA identifies Audit Universe, consults with Heads | **Audit Universe** → Create + **Auditable Entities** → Add | Phases 2–3 (Tests 3.1, 4.1) |
| Step 1 (submit) | IA submits universe to CIA | **Audit Universe Detail** → Submit for Approval | Test 6.1.1 |
| Step 2 | CIA reviews and approves the audit universe | **Audit Universe Detail** → Workflow Console → Approve | Test 6.1.3–6.1.4 |
| Step 2 (assign) | CIA assigns IA to conduct risk assessment | (Manual assignment outside system) | N/A |
| Step 3 | IA conducts risk assessment, scores risks | **Risk Assessments** → Create + Submit | Phase 4 (Tests 5.1–5.5) |
| Step 3 (plan) | IA drafts the RBAIP | **Audit Plans** → Create | Test 6.2 |
| Step 3 (submit) | IA submits RBAIP to CIA | **Audit Plan Detail** → Submit for Approval | Test 6.4.1 |
| Step 4 | CIA reviews RBAIP, submits to Management | WO Stage 1: CIA Review → Approve | Test 6.4.2–6.4.3 |
| Step 5 | Management reviews and recommends | WO Stage 2: Management Review → Adopt | Test 6.4.4–6.4.5 |
| Step 6 | CIA submits to Audit Committee | (Auto-advances to Stage 3) | Test 6.4.5 |
| Step 7 | Audit Committee reviews | WO Stage 3: Committee Review | Test 6.4.6 |
| Step 8 | If improvement needed, CIA revises and resubmits | WO Stage 3: Request Improvement → Revise → Resubmit | Test 6.4.7 |
| Step 9 | Audit Committee approves | WO Stage 3: Approve | Test 6.4.8 |
| Step 10 | Commission noting | WO Stage 4: Commission Noting → Note | Test 6.4.9–6.4.10 |

### 13.2 SRS 1.8.3 — Conducting Internal Audit

| SRS Step | SRS Description | System Page | Test Reference |
|---|---|---|---|
| Steps 1–3 | Team familiarizes, assesses controls, develops audit program | **Audit Engagements** → Create (with scope, methodology) | Test 7.2 |
| Step 8 | LA develops RCM, prioritizes areas, prepares draft audit program | (Represented by Engagement scope/objectives) | Test 7.2.8 |
| Step 9 | CIA approves audit program | Start Engagement Workflow (CIA approval implicit) | Test 7.4.1 |
| Steps 10–11 | LA prepares EN, CIA approves | Engagement workflow start → Notification via Kafka | Test 7.4.1–7.4.2 |
| Step 12 | EN sent to auditee | FIMS notification (grc.audit_engagement.assigned) | Verify in WO/email |
| Step 14 | LA conducts entry meeting | **Meetings** → Create (type: `Entry Conference`) | Phase 13 (Tests 15.1–15.3) |
| Step 15 | Audit team performs tests, documents in Working Papers | **Working Papers** → Create under engagement | Phase 7 (Tests 8.1–8.3) |
| Step 16 | LA reviews working papers | WP Review Workflow Stage 1 | Test 8.3.2–8.3.3 |
| Step 17 | Pre-exit meeting | **Meetings** → Create (type: `Pre-Exit Conference`) | Phase 13 (Tests 15.2–15.3) |
| Step 18 | LA consolidates working papers, submits for vetting | Submit WP for Approval | Test 8.3.1 |
| Step 19 | CIA reviews and approves working papers | WP Review Workflow Stage 2 | Test 8.3.4–8.3.5 |
| Step 20 | LA conducts audit team meeting, prepares draft report | **Meetings** → Create (type: `Audit Team Meeting`) | Phase 13 (Tests 15.2–15.3) |
| Step 21 | IA documents draft audit report | **Audit Reports** → Create (engagement in `reporting`) | Phase 12 (Tests 14.1–14.3) |
| Steps 22–24 | Report review, exit meeting, final report | **Audit Reports** progress: `under_review` → `approved` → `distributed` | Phase 12 (Tests 14.4–14.5) |
| Findings | Document inadequate controls as findings | **Audit Findings** → Create with 4 C's | Phase 8 (Tests 9.1–9.5) |
| Recommendations | Document recommendations for findings | **Audit Recommendations** → Create per finding | Phase 9 (Tests 10.1–10.4) |

### 13.3 SRS 1.8.6 — Monitoring Implementation of Previous Audit Recommendations

| SRS Step | SRS Description | System Page | Test Reference |
|---|---|---|---|
| Step 1 | IA identifies unimplemented recommendations | **Audit Recommendations** → filter by status `open` / `in_progress` | Review recommendations list |
| Step 2 | IA shares list with auditee | (Set recommendation to `in_progress`) | Test 10.3.1–10.3.2 |
| Step 3 | Auditee responds within 5 days with evidence | (Update recommendation status with implementation notes) | Test 10.3.4–10.3.5 |
| Step 4 | IA compiles implementation status | **Audit Monitoring** → Create monitoring records | Tests 11.2 |
| Step 5 | IA conducts review and analysis | **Audit Monitoring** → View/Edit, update progress % | Tests 11.3–11.4 |
| Step 6 | IA submits to CIA for final review | (Progress tracked via monitoring records) | Test 11.4 |
| Step 7 | CIA presents to Management | (Management review tracked via monitoring status) | Dashboard overview |

---













## 14. Phase 12 — Audit Reports (SRS 1.8.3 Steps 20–24, 1.8.5)

> **SRS 1.8.3:**
> - Step 21: IA documents the draft audit report
> - Step 22: CIA reviews the draft report
> - Steps 23–24: Exit conference held, final report issued and distributed to auditee

**Navigate to:** Sidebar → Internal Audit → **Audit Reports**
**URL:** `/service/grc/audit-reports`

### Pre-Condition

| # | Action | Expected Result |
|---|---|---|
| 14.0.1 | Ensure an audit engagement is in `reporting` status | Required — the engagement dropdown filters to `reporting` engagements only |
| 14.0.2 | Ensure at least one Audit Opinion is configured (Configuration page) | Required for the Opinion dropdown |

### Test 14.1 — Create Audit Report

| # | Action | Expected Result |
|---|---|---|
| 14.1.1 | Click **Create** (+ button) | Create dialog opens |
| 14.1.2 | **Engagement** — SmartSelect dropdown | Shows only engagements in `reporting` status |
| 14.1.3 | Select `ICT General Controls Audit 2025/2026` | Engagement selected |
| 14.1.4 | **Audit Opinion** — SmartSelect | Shows configured opinions (Qualified, Unqualified, Adverse, etc.) |
| 14.1.5 | Select an opinion (e.g., `Qualified`) | Opinion selected |
| 14.1.6 | **Report Type** — select `Draft` | Dropdown: Draft / Final |
| 14.1.7 | **Report Title** — enter: `ICT General Controls Audit Report — Q3 2025/2026` | Min 5 chars |
| 14.1.8 | **Executive Summary** — enter a meaningful summary (min 20 chars) | Textarea |
| 14.1.9 | **Scope & Objectives** — enter scope text (min 20 chars) | Textarea |
| 14.1.10 | **Methodology** — enter methodology text (min 20 chars) | Textarea |
| 14.1.11 | **Conclusion** — enter conclusion text (min 20 chars) | Textarea |
| 14.1.12 | **Reviewed By** — leave empty (optional) | Optional field |
| 14.1.13 | Click **Create Report** | ✅ Report appears in table: Status=`draft`, Type=`DRAFT`, Reference auto-generated |

### Test 14.2 — View Report Detail

| # | Action | Expected Result |
|---|---|---|
| 14.2.1 | Click **View** on the report row | Detail dialog opens |
| 14.2.2 | Shows: Reference, Engagement, Opinion, Report Type, Status badges | All present |
| 14.2.3 | Shows: Executive Summary, Scope, Methodology, Conclusion | Content sections visible |
| 14.2.4 | Shows: Prepared By, Approved By (if set), Distribution List (if set) | Metadata section |

### Test 14.3 — Edit Draft Report

| # | Action | Expected Result |
|---|---|---|
| 14.3.1 | Click **Edit** on the `draft` report | Edit dialog opens pre-filled |
| 14.3.2 | Change **Report Type** to `Final` | Type updates |
| 14.3.3 | Update **Conclusion** text | Text updated |
| 14.3.4 | Click **Update Report** | ✅ Changes saved |

### Test 14.4 — Status Workflow

| # | Action | Expected Transition | SRS Mapping |
|---|---|---|---|
| 14.4.1 | Click **Progress Update** on `draft` → select `under_review` | Status → `under_review` | CIA reviews draft report (Step 22) |
| 14.4.2 | Click **Progress Update** on `under_review` → select `approved` | Status → `approved` | Report approved for distribution |
| 14.4.3 | Click **Progress Update** on `approved` → select `distributed` | Status → `distributed` | Report distributed to auditee (Steps 23–24) |
| 14.4.4 | `under_review` → select `draft` (reject/return) | Status → `draft` | Return for revision |

### Test 14.4a — GAP 9: Audit Report Stamp Verification

> **GAP 9:** After the report transitions to `approved`, the backend triggers a DRS stamp request. If the report has a `document_id` (a DRS document linked), `stamped_document_url` is populated automatically.

| # | Action | Expected Result |
|---|---|---|
| 14.4a.1 | After status → `approved`, open the report detail dialog (click **View**) | Detail dialog shows updated report |
| 14.4a.2 | Check `stamped_document_url` field in the detail | Populated if `document_id` was linked to a DRS document |
| 14.4a.3 | **"Download Approved Report"** button visible | Only when `stamped_document_url` is not null |
| 14.4a.4 | Click the download button | Browser downloads/opens the stamped PDF |
| 14.4a.5 | Check GRC service logs | Should contain: `Stamp triggered for audit_report {id}` |
| 14.4a.6 | Verify API: `GET /api/v1/grc/audit/reports/{id}/` | Response includes `stamped_document_url` field |

### Test 14.4b — GAP 12: Finding Finalization Kafka Events

> **GAP 12:** When an audit report transitions to `approved`, the backend iterates over all active (`is_active=True`) findings on the engagement and publishes a `finding.finalized` Kafka event for each one.

| # | Action | Expected Result |
|---|---|---|
| 14.4b.1 | Ensure the engagement has at least 2 findings in `final` status before approving report | Pre-condition for meaningful GAP 12 output |
| 14.4b.2 | Approve the audit report (status → `approved`) | Event publishing triggered immediately on status change |
| 14.4b.3 | Check GRC service logs immediately after approval | Should contain: `GAP 12: published N finding.finalized events for report {id}` |
| 14.4b.4 | Verify event count in logs matches number of active findings | e.g. 2 findings → log says `published 2 finding.finalized events` |
| 14.4b.5 | If Kafdrop is running, check `finding.finalized` topic | Messages present with `finding_id`, `approved_by`, `engagement_reference` fields |
| 14.4b.6 | Shell verification: `docker exec fims-grc-service python manage.py shell -c "from apps.core.models.audit_entities import AuditFinding; print(AuditFinding.objects.filter(is_active=True).count(), 'active findings')"` | Count matches events published |
| 14.4b.7 | If engagement has **no** active findings | Logs show: `GAP 12: published 0 finding.finalized events` — no error |

### Test 14.5 — Guards

| # | Action | Expected Result |
|---|---|---|
| 14.5.1 | Try deleting a `distributed` report | Confirm whether business guard blocks it |
| 14.5.2 | Try editing a `distributed` report | Should be blocked or restricted |
| 14.5.3 | Create report for engagement NOT in `reporting` status | Should reject or not appear in dropdown |

---

## 15. Phase 13 — Audit Meetings (SRS 1.8.3 Steps 14, 17, 24)

> **SRS 1.8.3:**
> - Step 14: LA conducts **Entry Conference** — *"record the attendance and proceedings of the meeting for future reference"*
> - Step 17: LA conducts **Pre-Exit Conference** to discuss preliminary findings
> - Step 20: LA conducts **Audit Team Meeting** prior to exit meeting
> - Step 24: LA conducts **Exit Conference** — *"document exit meeting minutes and attendance sheet"*
>
> **SRS Requirement 13:** *"The system shall capture attendance and minutes."*
> Documents upload to **Document Records Service** (same FIMS pattern as Working Papers).

**Navigate to:** Sidebar → Internal Audit → **Meetings**
**URL:** `/service/grc/meetings`

### Test 15.1 — Create Entry Conference

| # | Action | Expected Result |
|---|---|---|
| 15.1.1 | Click **Create** (+ button) | Create dialog opens |
| 15.1.2 | **Engagement** — SmartSelect | Shows all engagements |
| 15.1.3 | Select the ICT engagement | Engagement set |
| 15.1.4 | **Meeting Type** — select `Entry Conference` | Dropdown: Entry Conference, Pre-Exit Conference, Audit Team Meeting, Exit Conference |
| 15.1.5 | **Meeting Title** — enter: `ICT Audit Entry Conference — March 2026` | Min 5 chars |
| 15.1.6 | **Scheduled Date** — enter: `2026-03-01` | Date input |
| 15.1.7 | **Scheduled Time** — enter: `09:00` | Optional time input |
| 15.1.8 | **Location** — enter: `ICT Directorate Board Room, HQ 3rd Floor` | Optional |
| 15.1.9 | **Agenda** — enter a detailed agenda (min 10 chars) | Textarea |
| 15.1.10 | Click **Schedule Meeting** | ✅ Meeting appears in table: Status=`scheduled`, Type=`ENTRY CONFERENCE` |

### Test 15.2 — Create Exit Conference

| # | Action | Expected Result |
|---|---|---|
| 15.2.1 | Click **Create** again | Create dialog opens |
| 15.2.2 | Select same engagement | Engagement set |
| 15.2.3 | **Meeting Type** → `Exit Conference` | Type selected |
| 15.2.4 | **Title** → `ICT Audit Exit Conference — April 2026` | Title set |
| 15.2.5 | Set **Scheduled Date** → `2026-04-25` | Future date |
| 15.2.6 | **Agenda** → presentation of findings and agreed actions | Text entered |
| 15.2.7 | Click **Schedule Meeting** | ✅ Second meeting in table |

### Test 15.3 — Progress to In-Progress & Locked Fields

| # | Action | Expected Result |
|---|---|---|
| 15.3.1 | Click **Progress Update** → `in_progress` | Status → `in_progress` |
| 15.3.2 | Click **Edit** (⋮ menu) on the in-progress meeting | Edit dialog opens |
| 15.3.3 | Structural fields (Engagement, Type, Title, Date, Location, Agenda) are **disabled/greyed** | Cannot be changed — locked per backend rule |
| 15.3.4 | Yellow info banner visible: *"Meeting in progress — only post-meeting fields editable"* | Banner shown |
| 15.3.5 | **Minutes**, **Key Discussions**, **Attendees**, **Document uploads** are editable | Post-meeting section active |

### Test 15.4 — Record Post-Meeting Data (Edit in-progress meeting)

| # | Action | Expected Result |
|---|---|---|
| 15.4.1 | **Minutes** — enter meeting proceedings text | Textarea accepts input |
| 15.4.2 | **Key Discussions** — enter summary of key points discussed | Textarea accepts input |
| 15.4.3 | **Add Attendee** — click button, enter: Name=`ICT Director`, Title=`Director of ICT`, Role=`Auditee`, Present=✅ | Row added to attendees table |
| 15.4.4 | **Add Attendee** — add: Name=`System Administrator`, Title=`Lead Auditor`, Role=`Auditor`, Present=✅ | Row added |
| 15.4.5 | Add at least one more attendee | Multiple attendees supported |
| 15.4.6 | **Delete Attendee** — click ✕ on a row | Row removed |
| 15.4.7 | **Minutes Document** — click upload area, select a PDF/DOCX file | File staged for upload |
| 15.4.8 | **Attendance Sheet** — click upload area, select a file | File staged for upload |
| 15.4.9 | Click **Update Meeting** | ✅ POST to Document Records Service for each file → UUID stored as `minutes_document_id` / `attendance_document_id` |

### Test 15.5 — View Meeting Detail

| # | Action | Expected Result |
|---|---|---|
| 15.5.1 | Click **View** (⋮ menu) on a completed meeting | Detail dialog opens |
| 15.5.2 | Shows: Status + Type badges, Engagement reference + title, Date/Location | All visible |
| 15.5.3 | **Agenda** section rendered | Pre-formatted text shown |
| 15.5.4 | **Minutes** section (if populated) | Shown with pre-formatted text |
| 15.5.5 | **Key Discussions** section (if populated) | Shown with pre-formatted text |
| 15.5.6 | **Attendees** table — Name, Title, Role, Present columns | Populated from attendees JSON |
| 15.5.7 | **Action Items** table (if populated) | Description, Due Date, Status columns |

### Test 15.6 — Complete the Meeting

| # | Action | Expected Result |
|---|---|---|
| 15.6.1 | Try **Progress Update** → `completed` without minutes | ❌ `MINUTES_REQUIRED` error — backend rejects |
| 15.6.2 | After filling minutes (Test 15.4.1) → **Progress Update** → `completed` | ✅ Status → `completed` |
| 15.6.3 | Cancelled meeting: **Progress Update** → `cancelled` | Status → `cancelled` |
| 15.6.4 | Reschedule: **Progress Update** on `cancelled` → `scheduled` | Status → `scheduled` |

---

## 16. Phase 14 — Quarterly Reports (SRS 1.8.5)

> **SRS 1.8.5:** The CIA prepares quarterly reports on internal audit activities and submits to the Audit Committee. Reports consolidate findings, recommendations, and engagement summaries.

**Navigate to:** Sidebar → Internal Audit → **Quarterly Reports**
**URL:** `/service/grc/quarterly-reports`

### Test 16.1 — Create Quarterly Report

| # | Action | Expected Result |
|---|---|---|
| 16.1.1 | Click **Create** (+ button) | Create dialog opens |
| 16.1.2 | **Fiscal Year** — SmartSelect | Shows active fiscal years |
| 16.1.3 | Select `Fiscal Year 2025/2026` | Fiscal year set |
| 16.1.4 | **Quarter** — SmartSelect (auto-filters by selected fiscal year) | Shows only Q1–Q4 for the selected FY |
| 16.1.5 | Select `Q3` | Quarter set. Changing fiscal year resets this field. |
| 16.1.6 | **Report Title** — enter: `Internal Audit Activity Report — Q3 FY 2025/2026` (min 5 chars) | Text accepted |
| 16.1.7 | **Reporting Period Start** — enter: `2026-01-01` | Date input |
| 16.1.8 | **Reporting Period End** — enter: `2026-03-31` | Date input |
| 16.1.9 | **Executive Summary** — enter meaningful summary (min 20 chars) | Textarea |
| 16.1.10 | **Audit Activities Summary** — enter activities summary (min 20 chars) | Textarea |
| 16.1.11 | **Optional fields** — Resource Utilization, Key Achievements, Challenges, Planned vs Actual, Management Action Status, Next Quarter Plan | All optional — fill any or leave blank |
| 16.1.12 | **Conclusion** — enter conclusion (min 20 chars) | Textarea |
| 16.1.13 | Click **Create Quarterly Report** | ✅ Report appears in table: Status=`draft`, Consolidated=`No`, Ref auto-generated |

### Test 16.2 — View & Consolidate

| # | Action | Expected Result |
|---|---|---|
| 16.2.1 | Click **View** on the report row | Detail dialog opens |
| 16.2.2 | Status badge shows `DRAFT`, Consolidated badge shows `NOT CONSOLIDATED` | Both badges present |
| 16.2.3 | **Consolidate button** visible (appears when `!is_consolidated && status === 'draft'`) | Yellow/info banner with Consolidate button |
| 16.2.4 | Click **Consolidate** | API call to `/api/v1/grc/audit/quarterly-reports/{id}/consolidate/` |
| 16.2.5 | After consolidation: Consolidated badge → `CONSOLIDATED` | `is_consolidated = true`, button disappears |
| 16.2.6 | **Findings Summary** grid shows: Total, Critical, High, Medium, Low counts | 5-column grid pulled from linked engagements |
| 16.2.7 | **Recommendations Summary** grid shows: Total, Open, In Progress, Implemented, Overdue | 5-column grid |
| 16.2.8 | **Engagement Summaries** table shows linked engagements | Table with Reference, Title, Status, Findings count, Recommendations count |

### Test 16.3 — Fiscal Year Cascade (Quarter Reset)

| # | Action | Expected Result |
|---|---|---|
| 16.3.1 | Open Create dialog, select `Fiscal Year 2025/2026`, then select `Q3` | Q3 selected |
| 16.3.2 | Change Fiscal Year to `Fiscal Year 2024/2025` | **Quarter field resets** to empty (Q3 from 2025/2026 is no longer valid) |
| 16.3.3 | Quarter dropdown now shows only Q1–Q4 for 2024/2025 | Correct cascade behaviour |

### Test 16.4 — Status Workflow (7-Stage)

| # | Action | Expected Transition | Note |
|---|---|---|---|
| 16.4.1 | Progress Update → `cia_review` | `draft` → `cia_review` | CIA reviews the quarterly report |
| 16.4.2 | Progress Update → `management_review` | `cia_review` → `management_review` | Sent to management |
| 16.4.3 | Progress Update → `committee_review` | `management_review` → `committee_review` | Audit Committee reviews |
| 16.4.4 | Progress Update → `improvement_required` | `committee_review` → `improvement_required` | Returned for revision |
| 16.4.5 | Progress Update → `cia_review` (from improvement_required) | `improvement_required` → `cia_review` | Resubmit after revision |
| 16.4.6 | Progress Update → `approved` | `committee_review` → `approved` | Committee approves |
| 16.4.7 | Progress Update → `submitted_to_commission` | `approved` → `submitted_to_commission` | Final — submitted to Commission |

### Test 16.5 — Status Badge Colors

| Status | Expected Badge Color |
|---|---|
| `draft` | Gray |
| `cia_review` | Blue |
| `management_review` | Indigo |
| `committee_review` | Purple |
| `improvement_required` | Orange |
| `approved` | Green |
| `submitted_to_commission` | Teal |

### Test 16.6 — Consolidate Guards

| # | Action | Expected Result |
|---|---|---|
| 16.6.1 | Consolidate button visible only when `status === 'draft'` and `!is_consolidated` | Button absent for any other status |
| 16.6.2 | After consolidating, click Consolidate again | Button is gone — cannot consolidate a second time |
| 16.6.3 | Advance status to `cia_review` then view detail | Consolidate button no longer shown (status ≠ `draft`) |

---

## Quick Reference — Complete Test Execution Order

For a full end-to-end test following the SRS business process:

```
 1. Login as admin@fcc.go.tz
 2. GRC → Configuration → Create Fiscal Year, Severities, Finding Types, Risk Ratings, Audit Opinions
 3. GRC → Audit Universe → Create universe for the fiscal year
 4. GRC → Audit Universe Detail → Add Auditable Entities (4+ entities of different types)
 5. GRC → Audit Universe Detail → Submit for Approval → Approve via Workflow Console
 6. GRC → Risk Assessments → Create assessment per entity → Submit → Review → Approve
    6a. [GAP 6] Risk Assessment Detail → Verify auto_risk_score + auto_residual_score populated (Test 5.5a)
 7. GRC → Audit Plans → Check for auto-generated draft plan after universe approval (Test 6.1a — GAP 11)
    7a. [GAP 11] POST /api/v1/grc/audit/plans/generate-draft/ if no auto-draft → verify plan includes risk priorities
 8. GRC → Audit Plan Detail → Progress through 4-stage workflow (CIA → Management → Committee → Commission)
 9. GRC → Audit Engagements → Create engagement (type=planned) against approved plan
10. GRC → Engagement Detail → Start Engagement Workflow (engagement enters fieldwork)
11. GRC → Audit Memos → Create memo for the engagement → Progress: draft → cia_review → dg_review → approved → transmitted  [GAP 1]
    11a. [GAP 9] Audit Memo Detail → verify stamped_document_url + Download button after approved (Test 7a.4)
12. GRC → Declarations → Create Declaration 1 (no conflict, toggle ON) → Sign it  [GAP 2]
    12a. GRC → Declarations → Create Declaration 2 (with conflict, toggle OFF + conflict_details)
    12b. [GAP 9] Declaration Detail → verify stamped_document_url + Download button after signed (Test 7b.5)
13. GRC → Audit Surveys → Create preliminary survey with fraud_risk_assessment + control_assessments  [GAP 3]
    13a. Progress survey: draft → active → closed
14. GRC → Risk Control Matrix → Create RCM → Add 2 entries (access mgmt, change mgmt)  [GAP 4]
    14a. Progress RCM: draft → submitted → approved
15. GRC → Audit Programs → Create audit program → Progress: draft → submitted → approved  [GAP 5]
    15a. [GAP 9] Audit Program Detail → verify stamped_document_url + Download button after approved (Test 7e.3)
16. GRC → Meetings → Create Entry Conference (type: Entry Conference) → scheduled → completed
17. GRC → Engagement → Add Working Papers (WP-001, WP-002)
18. GRC → Working Paper Detail → Submit for Review → Approve through 2-stage workflow
19. GRC → Audit Findings → Create finding with 4 C's against fieldwork engagement
20. GRC → Audit Findings → Progress: draft → discussed → final
21. GRC → Meetings → Create Pre-Exit Conference (type: Pre-Exit Conference) → scheduled → completed
22. GRC → Audit Recommendations → Create recommendation against final finding
23. GRC → Audit Recommendations → Progress: open → in_progress → implemented → verified → closed
24. Workflow Console → Start Reporting (engagement status → reporting)
25. GRC → Audit Reports → Create draft audit report (engagement must be in reporting status)
26. GRC → Audit Reports → Progress: draft → under_review → approved → distributed
    26a. [GAP 9]  Audit Report Detail → verify stamped_document_url + Download button after approved (Test 14.4a)
    26b. [GAP 12] Check GRC logs: "GAP 12: published N finding.finalized events" immediately after approved (Test 14.4b)
27. GRC → Audit Monitoring → Create monitoring record for in-progress recommendation
    27a. [GAP 7]  Test 5-day deadline: next_review_date < today+5 → expect validation error (Test 11.7)
28. GRC → Audit Monitoring → Update progress, review, soft-delete/restore
29. GRC → Meetings → Create Exit Conference (type: Exit Conference) → scheduled → completed
30. GRC → Quarterly Reports → Create Q3 2025/2026 quarterly report
31. GRC → Quarterly Reports → Open detail → click Consolidate (auto-populate summary data)
32. GRC → Quarterly Reports → Progress through 7-stage workflow → submitted_to_commission
33. GRC → Dashboard → Verify all module cards navigate correctly
34. Review GRC service logs for any GAP-related errors or unexpected warnings
```

### GAP Verification Checklist

| GAP | What to Check | Test # |
|-----|---------------|--------|
| GAP 1 | Audit Memo: 5-stage workflow + stamped_document_url after approved | 7a.3, 7a.4 |
| GAP 2 | Declaration: auto-filled declarant from auth + sign flow + stamp | 7b.1–7b.5 |
| GAP 3 | Audit Survey: fraud_risk_assessment + control_assessments fields present | 7c.2 |
| GAP 4 | RCM: entries with control_type, in_scope, design_adequate, test_approach | 7d.2 |
| GAP 5 | Audit Program: approved creates stamped_document_url | 7e.3 |
| GAP 6 | Risk Assessment: auto_risk_score + auto_residual_score calculated on creation | 5.5a |
| GAP 7 | Monitoring: next_review_date < today+5 → validation error on create/update | 11.7 |
| GAP 9 | Memo/Declaration/Program/Report: stamped_document_url + download button after approval | 7a.4, 7b.5, 7e.3, 14.4a |
| GAP 11 | Audit Plan: auto-draft generated after universe approval | 6.1a |
| GAP 12 | Audit Report: finding.finalized Kafka events on report approval | 14.4b |

> **Total estimated testing time:** 90–120 minutes for full end-to-end flow (increased from 60–90 due to 5 new phases)
