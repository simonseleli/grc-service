# Internal Audit Module — Sample Data & Testing Flow

> **Date:** 2026-02-26
> **Base URL:** `http://localhost:3001` (Staff Portal)
> **Login:** `admin@fcc.go.tz` / `admin123`
> **Database:** Cleaned — all transactional data wiped, lookup data preserved

---

## Pre-Seeded Reference Data (DO NOT recreate)

### Fiscal Years

| ID | Name | Period |
|---|---|---|
| `67fdfe4b-abd4-4f99-96e0-d1b23270181f` | Fiscal Year 2025/2026 | 2025-07-01 → 2026-06-30 |
| `2aad7be4-038a-4bbe-ab9c-553560be17e3` | Fiscal Year 2024/2025 | 2024-07-01 → 2025-06-30 |
| `72449f6b-6973-468b-9263-13cb1da4b8c5` | Fiscal Year 2023/2024 | 2023-07-01 → 2024-06-30 |

### Quarters (FY 2025/2026 — use these)

| ID | Quarter | Period |
|---|---|---|
| `87729875-37fb-420b-8094-04321a197966` | Q1 | 2025-07-01 → 2025-09-30 |
| `9dc21545-da3e-44b8-ade9-e4b568a81ceb` | Q2 | 2025-10-01 → 2025-12-31 |
| `a60ad4e5-d227-4570-b488-fd219109b408` | Q3 | 2026-01-01 → 2026-03-31 |
| `9e1679de-d62c-498a-985d-42fcaf06afdc` | Q4 | 2026-04-01 → 2026-06-30 |

### Audit Severities

| ID | Name |
|---|---|
| `47b9f368-c1bc-4eed-b936-b47ea6d5d036` | Critical |
| `3f0cc279-00ef-4d9d-80da-c18ca8ed9aed` | High |
| `76f7fe6c-9fef-425e-b3ee-151cb60dfa63` | Medium |
| `e3894da4-e64f-4fa4-b9ac-c5163dad7b7a` | Low |

### Finding Types

| ID | Name |
|---|---|
| `a7b91e1c-f574-4831-8739-e9684f94a416` | Internal Control Deficiency |
| `5ff0cfc5-25fc-4107-8f26-9c539efbf9ea` | Internal Control Weakness |
| `6e8e353e-b108-4537-87f7-d95bd2349846` | Financial Management Issue |
| `fd3960cb-3c2b-4588-a9b3-f25953e960b8` | Operational Inefficiency |
| `84d3acfe-9d39-462c-afe2-65ec2de89814` | Compliance Finding |
| `460e939b-d100-4257-9f33-64142f55cceb` | Fraud Risk Exposure |
| `5a628e75-1904-40bb-a8b9-85d09a871fa1` | Risk Management Gap |
| `7202a1e7-9b06-4b04-8d7b-7d4e7251072a` | IT Governance Issue |

### Risk Ratings

| ID | Name | Value |
|---|---|---|
| `408b04fa-e89c-44bd-a330-ec0a05a1cf56` | Very High Risk | 4.50 |
| `5862f29e-991b-4aad-affd-4dfe758b0b0e` | High Risk | 3.50 |
| `9e2da6aa-c530-4c26-8a63-425cf8cfb4a9` | Medium-High Risk | 3.00 |
| `9b1d98da-f9e3-45b0-aa15-28ea3fc9e01b` | Medium Risk | 2.50 |
| `7530a4c9-182d-45c5-8e8f-c7ba766bb338` | Low-Medium Risk | 2.00 |
| `9dce8fef-6c1b-4640-b620-e9d1437aa79a` | Low Risk | 1.50 |

### Audit Opinions

> Per IIA (Institute of Internal Auditors) standards, internal audit reports use two opinion scales:
> - **Financial audit opinions** — Unqualified, Qualified, Adverse, Disclaimer of Opinion
> - **Performance audit opinions** — Satisfactory, Needs Improvement *(and Unsatisfactory if added)*

| Code | Name | Use When |
|---|---|---|
| `UNQUALIFIED` | Unqualified Opinion | No material issues — controls are effective |
| `QUALIFIED` | Qualified Opinion | Some issues found but overall controls adequate |
| `ADVERSE` | Adverse Opinion | Material control failures or misstatements found |
| `DISCLAIMER` | Disclaimer of Opinion | Insufficient evidence to form an opinion |
| `SATISFACTORY` | Satisfactory | Overall performance meets expectations |
| `NEEDS_IMPROVEMENT` | Needs Improvement | Areas requiring enhancement identified |

> **⚠️ If your dropdown only shows one or two opinions**, the seed command did not fully populate them. Run: `docker compose exec grc-service python manage.py seed_lookup_data` — or add the missing ones manually via **GRC → Configuration → Audit Opinions**.
>
> **For the ICT General Controls Audit (compliance engagement), use `Qualified Opinion`** — findings were identified but the audit was completable.

### Active Users

| ID | Email | Name |
|---|---|---|
| `fb680f30-398b-4b86-865b-455a35c3c8d9` | admin@fcc.go.tz | System Administrator |
| `a91c2a28-dd6e-4a7f-8ae9-82351a2e2ced` | test@fims.local | Test User |

---

## Phase 1 — Configuration Verification

**Page:** Sidebar → GRC → **Configuration**

Simply verify the above lookup data exists. No creation needed — the `seed_lookup_data` management command pre-populated everything.

✅ Expected: Fiscal Years, Quarters, Audit Severities, Finding Types, Risk Ratings, and **6 Audit Opinions** all present.

> **If Audit Opinions are missing or incomplete**, run the seed command:
> ```
> docker compose exec grc-service python manage.py seed_lookup_data
> ```

---

## Phase 2 — Create Audit Universe

**Page:** Sidebar → **Audit Universe** → Click **Create** (+)

| Field | Value |
|---|---|
| **Fiscal Year** | `Fiscal Year 2025/2026` (select from dropdown) |
| **Description** | `Annual Internal Audit Universe for FCC covering all directorates, units, zones, processes, and systems for the 2025/2026 fiscal year` |
| **Reviewed By** | `System Administrator` (select admin@fcc.go.tz from dropdown) |

**Expected result:** Universe created with status `draft`.

**Business rule:** Only one universe per fiscal year. Attempting to create a second for the same FY returns `UNIVERSE_ALREADY_EXISTS`.

> **⚠️ To view universe detail:** On the Audit Universe list page, find the universe row → click the **⋮ (three-dot) action menu** on the right → select **"View"** (Eye icon) → opens the Detail page where you can see Status, Workflow Console, Auditable Entities section, and Submit for Approval button.

---

## Phase 3 — Add Auditable Entities

**Page:** Sidebar → **Audit Universe** → find your universe row → click the **⋮ (three-dot) action menu** on the right → select **"View"** (Eye icon) → this opens the **Universe Detail page** → scroll down to the **Auditable Entities** section → click **Add Entity**

> **⚠️ Navigation note:** Auditable Entities do NOT have their own sidebar entry. They are embedded inside the Audit Universe **Detail** page. You must "View" a universe first to see and manage its entities.

### Entity 1: ICT Directorate

| Field | Value |
|---|---|
| **Entity Type** | `directorate` |
| **Name** | `ICT Directorate` |
| **Code** | `ICT-001` |
| **Description** | `Information and Communication Technology Directorate — manages all ICT infrastructure, systems, and digital services` |

### Entity 2: Finance Unit

| Field | Value |
|---|---|
| **Entity Type** | `unit` |
| **Name** | `Finance Unit` |
| **Code** | `FIN-001` |
| **Description** | `Financial Management Unit — handles budgets, expenditures, procurement payments, and financial reporting` |

### Entity 3: Dar es Salaam Zone

| Field | Value |
|---|---|
| **Entity Type** | `zone` |
| **Name** | `Dar es Salaam Zone` |
| **Code** | `DAR-001` |
| **Description** | `Dar es Salaam Regional Zone — largest regional office handling spectrum licensing and compliance` |

### Entity 4: Procurement Process

| Field | Value |
|---|---|
| **Entity Type** | `process` |
| **Name** | `Procurement Process` |
| **Code** | `PROC-001` |
| **Description** | `Corporate procurement process — covers tender management, vendor selection, and contract administration` |

**Expected:** 4 entities visible in the Audit Universe detail page's embedded table.

---

## Phase 4 — Risk Assessments

**Page:** Sidebar → **Risk Assessments** → Click **Create**

> All 6 risk scores are on a **0–10 scale**.

### Risk Assessment 1: ICT Directorate

| Field | Value |
|---|---|
| **Auditable Entity** | `ICT Directorate (ICT-001)` |
| **Assessment Period** | `2025/2026 Q3` |
| **Inherent Risk** | `8` |
| **Control Effectiveness** | `5` |
| **Financial Exposure** | `6` |
| **Compliance Risk** | `7` |
| **Operational Impact** | `9` |
| **Reputational Risk** | `6` |
| **Overall Risk Rating** | `Very High Risk` |
| **Residual Risk Rating** | `High Risk` |
| **Justification** | `ICT infrastructure is critical to operations. Recent system outages and cybersecurity incidents indicate elevated risk. Current controls are partially effective but need strengthening.` |

### Risk Assessment 2: Finance Unit

| Field | Value |
|---|---|
| **Auditable Entity** | `Finance Unit (FIN-001)` |
| **Assessment Period** | `2025/2026 Q3` |
| **Inherent Risk** | `7` |
| **Control Effectiveness** | `6` |
| **Financial Exposure** | `9` |
| **Compliance Risk** | `8` |
| **Operational Impact** | `5` |
| **Reputational Risk** | `7` |
| **Overall Risk Rating** | `High Risk` |
| **Residual Risk Rating** | `Medium-High Risk` |
| **Justification** | `Finance unit handles significant public funds. External audit findings from prior year identified reconciliation gaps. Internal controls exist but compliance is inconsistent.` |

### Risk Assessment 3: Dar es Salaam Zone

| Field | Value |
|---|---|
| **Auditable Entity** | `Dar es Salaam Zone (DAR-001)` |
| **Assessment Period** | `2025/2026 Q3` |
| **Inherent Risk** | `5` |
| **Control Effectiveness** | `7` |
| **Financial Exposure** | `4` |
| **Compliance Risk** | `6` |
| **Operational Impact** | `5` |
| **Reputational Risk** | `4` |
| **Overall Risk Rating** | `Medium Risk` |
| **Residual Risk Rating** | `Low-Medium Risk` |
| **Justification** | `Zone operations are generally well-controlled. Revenue collection processes are standardized with regular reporting.` |

### Risk Assessment 4: Procurement Process

| Field | Value |
|---|---|
| **Auditable Entity** | `Procurement Process (PROC-001)` |
| **Assessment Period** | `2025/2026 Q3` |
| **Inherent Risk** | `8` |
| **Control Effectiveness** | `4` |
| **Financial Exposure** | `8` |
| **Compliance Risk** | `9` |
| **Operational Impact** | `6` |
| **Reputational Risk** | `8` |
| **Overall Risk Rating** | `Very High Risk` |
| **Residual Risk Rating** | `High Risk` |
| **Justification** | `Procurement involves high-value contracts and regulatory requirements under PPA 2011. Prior audit identified non-compliance with tender procedures and inadequate documentation of evaluation criteria.` |

**Expected:** 4 risk assessments created, each linked to its auditable entity.

### Status Workflow for Risk Assessments:

> **⚠️ 3-step UI flow:** Each action triggers a different backend endpoint and dialog.

| Step | UI Action | Status | Backend endpoint |
|---|---|---|---|
| 1 | Created | `draft` | `POST /risk-assessments/` |
| 2 | ⋮ → **Progress Update** → click **Confirm** | `draft → submitted` | `POST /risk-assessments/{id}/submit/` |
| 3 | ⋮ → **Progress Update** → **Approve** button | `submitted → reviewed` | `POST /risk-assessments/{id}/review/` with `{action:"approve"}` |
| 4 | ⋮ → **Progress Update** → click **Confirm** | `reviewed → approved` | `POST /risk-assessments/{id}/submit/` (same endpoint, second call) |

> **Reject path:** In Step 3, clicking **Reject** instead of Approve returns status to `draft` so the assessor can revise.
> **Terminal state:** `approved` — no further progress updates possible. The ⋮ Progress Update option is hidden for approved assessments.

---

### ✅ GAP 6 — Auto-Score Verification:
After saving each risk assessment, open the detail dialog (click **View**) and verify:

**`auto_risk_score`** (displayed as *Calculated Score* badge) is computed as a **weighted average** of all 6 input scores:

| Dimension | API field | Weight |
|---|---|---|
| Inherent Risk | `inherent_risk_score` | 25% |
| Control Effectiveness | `control_effectiveness_score` | 20% |
| Financial Exposure | `financial_exposure_score` | 15% |
| Compliance Risk | `compliance_risk_score` | 15% |
| Operational Impact | `operational_impact_score` | 15% |
| Reputational Risk | `reputational_risk_score` | 10% |

**`auto_residual_score`** = `auto_risk_score × (1 − control_effectiveness_score / 10)`

> Example — ICT Directorate scores (8, 5, 6, 7, 9, 6):
> `auto_risk_score` = (8×0.25) + (5×0.20) + (6×0.15) + (7×0.15) + (9×0.15) + (6×0.10) = **6.90**
> `auto_residual_score` = 6.90 × (1 − 5/10) = **3.45**

**Auto-rating behavior:**
- `auto_overall_rating` and `auto_residual_rating` are auto-populated using `classify_score()` which matches against `min_score`/`max_score` thresholds on RiskRating records
- The **pre-seeded RiskRatings do not have `min_score`/`max_score` set** → the system falls back to *closest numerical_value* (range: 1.5–4.5). On a 0–10 score scale this means most scores above ~4.0 map to **Very High Risk**
- To get meaningful auto-ratings: go to **GRC → Configuration → Risk Ratings** and set threshold ranges (e.g. Very High = 7–10, High = 5–6.99, Medium-High = 4–4.99, Medium = 3–3.99, Low-Medium = 1.5–2.99, Low = 0–1.49)
- `overall_risk_rating` and `residual_risk_rating` (the fields the user selects in the create form) are **automatically overridden by the auto-calculated values** after save unless `rating_overridden = true`. This means what the user selects in the form dropdowns will be replaced by the system's auto-rating.

**What to verify:**
- `auto_risk_score` field is non-null in the detail dialog ✅
- `auto_residual_score` field is non-null ✅
- `auto_overall_rating` badge is shown ✅
- Backend field aliases: `auto_risk_score` → `calculated_weighted_score`, `auto_residual_score` → `calculated_residual_score`

---

## Phase 5 — Submit Universe for Approval

**Page:** Go back to the **Audit Universe** detail page

1. Click **Submit for Approval**
   - Universe status immediately changes from `draft` → **`under_review`**
   - A 1-stage WO workflow plan is created (template: `grc.audit_universe_approval`)
   - The Workflow Console in the right panel activates and shows the pending CIA Review stage
2. **Stage 1 — CIA Review:** In the Workflow Console → click **Approve**
   - WO fires `grc.workflow.completed` Kafka event with `final_decision=approved`
   - GRC Kafka consumer sets universe status → **`approved`** and records `approved_at` timestamp

**Expected:** Status badge changes to `approved`. Universe is now locked for editing (`UNIVERSE_APPROVED` error code if update is attempted).

> **⚠️ If CIA clicks Return instead of Approve:** Status reverts to `draft`, `workflow_plan_id` is cleared, and the Submit button reappears — you can revise the universe and resubmit.

> **⚠️ Intermediate status:** While awaiting CIA approval, the universe is in `under_review` status. The **Submit for Approval** button disappears and the Workflow Console shows the active stage. Entities can still be added/removed at this stage (entity management is not blocked by `under_review`; only `approved` fully locks the universe).

---

## Phase 6 — Create Audit Plan (RBIAP)

**Page:** Sidebar → **Audit Plans** → Click **Create Audit Plan**

> **Pre-condition:** Audit Universe must be `approved` before creating a plan. The Audit Universe dropdown only shows approved universes.

| Field | Value |
|---|---|
| **Reference Number** | *(optional — leave empty to auto-generate as `RBIAP-{year_code}-{sequence}`)* |
| **Plan Title** | `Risk-Based Internal Audit Plan 2025/2026` |
| **Plan Type** | `annual` *(API value — displayed in the form as "Annual Plan")* |
| **Fiscal Year** | `2025/2026` |
| **Audit Universe** | *(select the approved universe — only approved ones appear)* |
| **Management Comments** | *(leave empty — filled during management review stage)* |
| **Committee Comments** | *(leave empty — filled during committee review stage)* |

> **Note:** Priority Areas and Resource Allocation fields exist in the backend model but are not currently exposed in the Create form. They can be managed via the detail page or API.

**Expected:** Plan created with status `draft`.

### Submit Plan for Approval (4-stage workflow):

1. Click **Submit for Approval**
   - Plan status immediately set to `management_review` by the service (GRC-side)
   - Work Orchestration starts its 4-stage workflow internally at the CIA Review stage
2. In the **WO Workflow Console**, complete each stage in order:

| # | WO stage_key | Stage Name | Action Button | Next Status (WO) |
|---|---|---|---|---|
| 1 | `cia_review` | CIA Review | **Approve** / Return | — |
| 2 | `management_review` | Management Review | **Adopt** / Request Changes | — |
| 3 | `committee_review` | Audit Committee Review | **Approve** / Request Improvement | — |
| 4 | `commission_noting` | Commission Noting | **Note** *(not "Approve")* | Final |

3. After all 4 stages complete → GRC plan status → `approved`

> **Rejection path:** If the plan is rejected or cancelled at any stage, GRC resets plan status to `draft` and clears `workflow_plan_id`. The plan must be resubmitted from scratch.

### ✅ GAP 11 — Generate Draft Plan:

This is **not** an auto-created plan on universe approval. It is a deliberate **"Generate Draft"** button on the Audit Plans list page.

**Steps:**
1. Navigate to GRC → **Audit Plans**
2. Click the **Generate Draft** button (separate from the Create button — opens a dedicated dialog)
3. In the dialog, select:
   - **Fiscal Year** *(required)*
   - **Audit Universe** *(required — must be `approved`)*
4. Click **Generate**

**Pre-conditions enforced by the backend (`POST /audit/plans/generate-draft/`):**
- The selected Audit Universe must have status `approved` → otherwise `UNIVERSE_NOT_APPROVED` error
- There must be no existing plan for the same universe + fiscal year → otherwise `PLAN_EXISTS` conflict
- Approved risk assessments must exist for entities in the universe → otherwise `NO_ASSESSMENTS` error

**What gets auto-generated:**
- `reference_number`: auto-assigned as `RBIAP-{year_code}-{sequence}`
- `priority_areas`: entities sorted descending by `calculated_weighted_score` from the approved risk assessments
- `plan_type`: defaults to `annual`
- `status`: `draft`

5. Review the generated draft, adjust as needed, then submit through the 4-stage approval workflow above.

---

## Phase 7 — Create Audit Engagement

**Page:** Sidebar → GRC → **Audit Engagements** → Click **Create**

> **Pre-condition:** The Audit Plan must be in `approved` or `implementation` status. Engagements cannot be created against plans in any earlier status.

| Field | Value |
|---|---|
| **Title** | `ICT General Controls Audit 2025/2026` |
| **Reference Number** | *(optional — leave empty to auto-generate)* |
| **Engagement Type** | `planned` *(API value; other options: `unplanned`, `special_investigation`, `follow_up`)* |
| **Audit Plan** | `RBIAP-2025-001` (select approved plan) |
| **Auditable Entity** | `ICT Directorate (ICT-001)` |
| **Lead Auditor** | `fb680f30-398b-4b86-865b-455a35c3c8d9` (admin) |
| **Scope** | `Review of ICT general controls including access management, change management, backup and recovery, and network security` |
| **Objectives** | `1. Assess adequacy of ICT access controls\n2. Evaluate change management procedures\n3. Test backup and disaster recovery plans\n4. Review network security configuration` |
| **Methodology** | `Document review, interviews with ICT staff, system walkthrough, control testing using COBIT framework alignment` |
| **Planned Start Date** | `2026-03-01` |
| **Planned End Date** | `2026-04-30` |

**Expected:** Engagement created with status `planning`.

> **⚠️ CRITICAL ORDERING — complete sub-phases 7a through 7e before starting the workflow.**
> The backend enforces `engagement.status == 'planning'` for Survey (7a), RCM (7b), and Audit Program (7c). Clicking **Start Engagement Workflow** sets status to `fieldwork` immediately, which will cause those create forms to reject with `INVALID_ENGAGEMENT_STATUS`. Also, all Declarations must be `signed` before the workflow can start (Phase 7e). Follow the order below exactly:
>
> **7a → Survey → 7b → RCM → 7c → Audit Program → 7d → Engagement Notification → 7e → Declarations → Start Workflow**

---

## Phase 7a — Audit Survey / Preliminary Control Assessment (GAP 3 — SRS Req 19–21)

**Page:** Sidebar → GRC → **Audit Engagements** → click your engagement row → **Engagement Detail page** → scroll to the **Audit Surveys** card → click **Add**

> **SRS §1.8.3 Steps 4–7:** The audit team familiarises themselves with the auditable area (preliminary survey), assesses the design adequacy of controls, and documents fraud risk factors. The survey findings directly inform the RCM and audit program.
> **Model:** `AuditSurvey` is OneToOneField per engagement — only one survey can exist per engagement. There is no `title` or `survey_type` field on the model.

| Field | Value |
|---|---|
| **Engagement** (`audit_engagement_id`) | `ICT General Controls Audit 2025/2026` *(auto-populated from the engagement detail page)* |
| **Surveyed By** (`surveyed_by`) | *(auto-filled from logged-in user UUID)* |
| **Survey Date** (`survey_date`) | `2026-03-05` |
| **Process Description** (`process_description`) | `Preliminary survey covering the ICT General Controls environment. Processes assessed include user access management, IT change management, backup and disaster recovery, and network security configuration.` |
| **Control Environment Notes** (`control_environment_notes`) | `The ICT control environment shows moderate maturity. Formal policies exist for access management and change control but are inconsistently enforced. Management tone is supportive of audit activity.` |
| **Prior Audit History** (`prior_audit_history`) | `Last ICT audit conducted FY 2023/2024. Key findings were: excessive user privileges (partially remediated), incomplete change documentation (open), and backup restoration not tested (open). Prior recommendations 60% implemented.` |
| **Fraud Risk Assessment** (`fraud_risk_assessment`) | `[{"risk_factor": "Unauthorized access via terminated employee accounts", "likelihood": "medium", "impact": "high", "notes": "3 terminated employees had active access; no automated deprovisioning"}, {"risk_factor": "Vendor collusion in change management bypasses", "likelihood": "low", "impact": "medium", "notes": "Emergency changes bypassing approval — low likelihood but notable"}]` *(JSON array — each object must have `risk_factor`, `likelihood`, `impact`, `notes`)* |
| **Control Assessments** (`control_assessments`) | `[{"control_name": "Quarterly Access Reviews", "control_owner": "ICT Director", "design_adequate": false, "notes": "No quarterly reviews performed; access review process not documented", "test_strategy": "effectiveness"}, {"control_name": "Change Management Approval", "control_owner": "IT Operations Manager", "design_adequate": true, "notes": "Process well-designed but inconsistently followed", "test_strategy": "effectiveness"}, {"control_name": "Backup & Recovery", "control_owner": "IT Operations Manager", "design_adequate": false, "notes": "No recent restoration test conducted", "test_strategy": "impact"}]` *(JSON array — each object must have `control_name`, `control_owner`, `design_adequate` (boolean), `notes`, `test_strategy`)* |
| **Preliminary Findings** (`preliminary_findings`) | `Access review process not documented; 15 of 42 accounts had excessive privileges. Change management bypassed for emergency changes. Backup restoration last tested 18 months ago.` |

**Expected result:** Survey created with status `draft`. It appears in the **Audit Surveys** card on the Engagement Detail page.

### Status Workflow:

> **⚠️ Model note:** Only 2 statuses exist: `draft` and `completed`. There is no `active` or `closed` state.

| Step | Action | Status |
|---|---|---|
| 1 | Created | `draft` |
| 2 | Click **Mark Complete** button on the survey row | `completed` — survey finalized |

> **Navigation:** The **Mark Complete** button appears directly on the survey row in the **Audit Surveys** card (only visible when status is `draft`). There is no separate detail page for surveys.

---

## Phase 7b — Risk Control Matrix (GAP 4 — SRS Req 22)

**Page:** Sidebar → GRC → **Audit Engagements** → click your engagement row → **Engagement Detail page** → scroll to the **Risk Control Matrix** card → click **Add**

> **SRS §1.8.3 Step 8:** Based on the preliminary survey, the Lead Auditor develops the RCM documenting all identified risks, associated controls, control design adequacy, and the planned test approach for each control.

### Step 1: Create the RCM Header

> **⚠️ Model note:** `RiskControlMatrix` has no `title` or `description` field. The create form only requires the engagement. `prepared_by` is auto-filled from the logged-in user.

| Field | Value |
|---|---|
| **Engagement** (`audit_engagement_id`) | `ICT General Controls Audit 2025/2026` *(auto-populated from the engagement detail page)* |
| **Prepared By** (`prepared_by`) | *(auto-filled from logged-in user UUID)* |

**Expected:** RCM created with status `draft`. It appears in the **Risk Control Matrix** card on the Engagement Detail page.

### Step 2: Add RCM Entries

**Navigation:** In the **Risk Control Matrix** card, click the RCM row → this navigates to the **RCM Detail page** (`/service/grc/engagements/{id}/rcm/{rcm_id}`) → click **Add Entry** to add each row.

#### RCM Entry 1: Access Management

| Field | Value |
|---|---|
| **Process Area** (`process_area`) | `User Access Management` |
| **Risk Description** (`risk_description`) | `Unauthorized access due to inadequate access review controls — terminated employees may retain active system access, enabling unauthorized system use or data exfiltration.` |
| **Risk Rating** (`risk_rating_id`) | `High Risk` (select from configured Risk Ratings) |
| **Control Description** (`control_description`) | `Quarterly user access reviews to ensure least-privilege access` |
| **Control Owner** (`control_owner`) | `ICT Director` |
| **Control Type** (`control_type`) | `preventive` *(API values: `preventive` \| `detective` \| `corrective` — no other values accepted)* |
| **In Scope** (`in_scope`) | `Yes` (toggle ON) |
| **Design Adequate** (`design_adequate`) | `No` (toggle OFF — control exists but design is flawed) |
| **Design Assessment Notes** (`design_assessment_notes`) | `Access review process is not formally documented. No evidence of execution in the last 12 months. 15 of 42 sampled accounts had excessive privileges.` |
| **Test Approach** (`test_approach`) | `effectiveness_test` *(API values: `effectiveness_test` \| `impact_test` \| `not_applicable` — NOT `walkthrough` or `substantive`)* |
| **Priority** (`priority`) | `high` *(API values: `high` \| `medium` \| `low`)* |

> **⚠️ Note:** There is no `test_result` or `comments` field on `RCMEntry`. Test outcomes are captured in Working Papers and Audit Findings.

#### RCM Entry 2: Change Management

| Field | Value |
|---|---|
| **Process Area** (`process_area`) | `IT Change Management` |
| **Risk Description** (`risk_description`) | `Unauthorized or undocumented production changes due to inconsistent change control enforcement.` |
| **Risk Rating** (`risk_rating_id`) | `Medium Risk` (select from configured Risk Ratings) |
| **Control Description** (`control_description`) | `Formal change request and approval workflow for production changes` |
| **Control Owner** (`control_owner`) | `IT Operations Manager` |
| **Control Type** (`control_type`) | `detective` |
| **In Scope** (`in_scope`) | `Yes` (toggle ON) |
| **Design Adequate** (`design_adequate`) | `Yes` (toggle ON — process is well-designed) |
| **Design Assessment Notes** (`design_assessment_notes`) | `Change management policy exists and is well-designed. However, 7 of 12 sampled changes lacked complete documentation. Emergency change procedures are being bypassed.` |
| **Test Approach** (`test_approach`) | `effectiveness_test` |
| **Priority** (`priority`) | `medium` |

### Step 3: Submit RCM for Approval

> Both buttons are in the **top-right corner** of the RCM Detail page (`/engagements/{id}/rcm/{rcm_id}`). Only one button is visible at a time depending on current status.

| Step | Action | Status | SRS Mapping |
|---|---|---|---|
| 1 | Created | `draft` | LA develops RCM |
| 2 | Click **Submit for Approval** button (top-right) | `submitted` | Submitted to CIA |
| 3 | Click **Approve RCM** button (top-right, appears after submit) | `approved` | CIA approves RCM |

---

## Phase 7c — Audit Program (GAP 5 — SRS Req 22–23)

**Page:** Sidebar → GRC → **Audit Engagements** → click your engagement row → **Engagement Detail page** → scroll to the **Audit Programs** card → click **Add**

> **SRS §1.8.3 Steps 8–9:** The Lead Auditor prepares the draft audit program based on the approved RCM, defining the scope, objectives, and specific audit procedures. The CIA reviews and approves the program before fieldwork begins.
> **GAP 9:** After status reaches `approved`, the program is stamped with QR code + approver signature via DRS.

| Field | Value |
|---|---|
| **Engagement** (`audit_engagement_id`) | `ICT General Controls Audit 2025/2026` *(auto-populated from the engagement detail page)* |
| **Title** (`title`) | `ICT General Controls Audit Program — Q3 2025/2026` |
| **Objectives** (`objectives`) | `["Assess adequacy of user access management controls", "Evaluate change management documentation and approval processes", "Verify backup and disaster recovery procedures", "Review network security configuration and monitoring"]` |
| **Procedures** (`procedures`) | `[{"rcm_entry_id": null, "procedure": "Inspect access review records for 42 sampled user accounts", "sample_size": 42, "criteria": "Quarterly access review must be documented and signed off"}, {"rcm_entry_id": null, "procedure": "Substantive testing of 12 sampled production changes for completeness of documentation", "sample_size": 12, "criteria": "Change request, impact assessment, and approvals must all be present"}, {"rcm_entry_id": null, "procedure": "Review backup restoration test records", "sample_size": null, "criteria": "Restoration test must be conducted at least annually"}]` *(JSON array — each object has `rcm_entry_id` (UUID or null), `procedure`, `sample_size` (int or null), `criteria`)* |

**Expected result:** Program created with status `draft`. It appears in the **Audit Programs** card on the Engagement Detail page.

> **⚠️ Pre-condition:** The audit engagement must be in `planning` status. The create form enforces this.

### Status Workflow (2-stage WO workflow — SRS Steps 22–23):

> **⚠️ Model note:** Status is `draft → under_review → approved`. To submit, click the program row in the **Audit Programs** card → the **Audit Program detail dialog** opens → click **Submit** inside the dialog. This starts the WO workflow.

1. In the **Audit Programs** card, click the program row → **Audit Program detail dialog** opens
2. Click **Submit** in the dialog
   - Backend: `POST /audit-programs/{id}/submit/`
   - Program status immediately set to `under_review` by the service
   - Work Orchestration starts a 2-stage workflow
3. In the **WO Workflow Console**, complete each stage:

| # | WO stage_key | Stage Name | Action Button |
|---|---|---|---|
| 1 | `ia_program_review` | IA Review | **Approve** / Return to Lead Auditor |
| 2 | `cia_program_approval` | CIA Approval | **Approve** / Return to IA |

4. After WO final approval → Kafka event → GRC `program.status = approved`

> **Rejection path:** Rejected/cancelled at any stage → GRC resets `program.status = draft`, clears `workflow_plan_id`.

### ✅ GAP 9 Stamp Verification:
After status → `approved`:
1. Click the program row in the **Audit Programs** card → detail dialog opens
2. A **"Download Approved Program"** button should appear (visible only when `stamped_document_url` is set)
3. Check GRC service logs for: `Stamp triggered for audit_program {id}`

---

## Phase 7d — Engagement Notification (GAP 1 — SRS Req 10–14, 18)

**Page:** Sidebar → GRC → **Audit Engagements** → click your engagement row → **Engagement Detail page** → scroll to the **Engagement Notification** card → click **Add**

> **SRS §1.8.3 Steps 10–12:** After the audit program is approved, the Lead Auditor prepares the Engagement Notification (EN) — a formal notice to the auditable area. The CIA reviews it, the DG approves it, and it is then transmitted to the auditee.
> **Model:** `EngagementNotification` is OneToOneField per engagement — only one EN can exist per engagement. The **Add** button only appears when no EN exists yet; once created, click the EN row to view or manage it.
> **GAP 9:** After the EN reaches `approved` status, it is stamped with QR code + approver signature via DRS. The `stamped_document_url` field is populated automatically.

| Field | Value |
|---|---|
| **Engagement** (`audit_engagement_id`) | `ICT General Controls Audit 2025/2026` *(auto-populated from the engagement detail page)* |
| **Audit Period Start** (`audit_period_start`) | `2026-03-01` |
| **Audit Period End** (`audit_period_end`) | `2026-04-30` |
| **Notification Date** (`notification_date`) | `2026-02-14` *(date the EN is formally issued to the auditee)* |
| **Scope Summary** (`scope_summary`) | `ICT General Controls — access management, change management, backup and recovery, network security configuration.` |
| **Audit Team Snapshot** (`audit_team_snapshot`) | `[]` *(optional JSON array of team members — leave empty or add: `[{"user_id": "uuid", "role": "lead_auditor", "name": "Full Name"}]`)* |

**Expected result:** EN created with status `draft`. It appears in the **Engagement Notification** card on the Engagement Detail page.

### Status Workflow (2-stage WO workflow — SRS Steps 10–14):

> **Note:** The EN detail dialog (opened by clicking the EN row) is read-only — no workflow buttons exist inside it. All workflow progression happens via the **WO Workflow Console** on the right side of the Engagement Detail page.

1. Click **Submit** *(the Submit action is available on the EN detail view or via the WO Console)*
   - Backend: `POST /engagement-notifications/{id}/submit/`
   - EN status immediately set to `under_review` by the service
   - Work Orchestration starts a 2-stage workflow
2. In the **WO Workflow Console**, complete each stage:

| # | WO stage_key | Stage Name | Action Button |
|---|---|---|---|
| 1 | `cia_memo_review` | CIA Review | **Forward to DG** / Return to Lead Auditor |
| 2 | `dg_memo_approval` | DG Approval | **Approve** / Return to CIA |

3. After WO final approval → Kafka event → GRC `notification.status = approved`
4. Click **Transmit** to formally send the EN to the auditee
   - Backend: `POST /engagement-notifications/{id}/transmit/`
   - Status updates to `transmitted`

**Full status progression:**

| Status | Meaning |
|---|---|
| `draft` | EN created, not yet submitted |
| `under_review` | Submitted — WO workflow running (CIA/DG review) |
| `approved` | WO approved — ready to transmit |
| `transmitted` | Formally sent to auditee |

> **Rejection path:** Rejected/cancelled at any WO stage → GRC resets `notification.status = draft`, clears `workflow_plan_id`. The Submit action reappears.

### ✅ GAP 9 Stamp Verification:
After status → `approved`:
1. Click the EN row in the **Engagement Notification** card → detail dialog opens
2. A **"Download Approved Notification"** button should appear (visible only when `stamped_document_url` is set)
3. Check GRC service logs for: `Stamp triggered for engagement_notification {id}`

---

## Phase 7e — Declaration of Independence (GAP 2 — SRS Req 16, 18, 38)

**Page:** Sidebar → GRC → **Audit Engagements** → click your engagement row → **Engagement Detail page** → scroll to the **Declarations** card → click **Add**

> **SRS:** Each audit team member must sign a Declaration of Independence before participating in an engagement. All declarations must be `signed` before the **Start Engagement Workflow** button will succeed — the backend returns `DECLARATIONS_NOT_SIGNED` (400) if any are still `pending`.
> **How it works:** The create form auto-fills `declarant_name`, `declarant_role`, and `declarant_user_id` from the currently logged-in user (via auth context).
> **GAP 9:** After a declaration is signed, it is stamped with QR code + signature via DRS. The `stamped_document_url` field is populated automatically.

### Declaration 1 — No Conflict (Standard Case)

| Field | Value |
|---|---|
| **Engagement** (`audit_engagement_id`) | `ICT General Controls Audit 2025/2026` *(auto-populated from the engagement detail page)* |
| **I am independent** toggle | `ON` (default — has_conflict = false) |
| **Conflict Details** | *(leave empty — only shown when toggle is OFF)* |
| **Declaration Text** | *(pre-filled default text — do not change)* |

**Expected result:** Declaration created with status `pending`, `declarant_name` auto-filled from auth.

### Declaration 2 — With Conflict (Edge Case Test)

| Field | Value |
|---|---|
| **Engagement** (`audit_engagement_id`) | `ICT General Controls Audit 2025/2026` |
| **I am independent** toggle | `OFF` → conflict_details field appears |
| **Conflict Details** | `I have a financial relationship with ICT Solutions Ltd, one of the vendors being reviewed in this engagement. I declare this conflict for CIA awareness and decision.` |

**Expected result:** Declaration created with `has_conflict = true`, conflict_details populated.

### Sign Declaration (SRS: "team member signs"):

1. In the **Declarations** card, click a declaration row → **Declaration detail dialog** opens
2. Click **Sign** inside the dialog
3. Status updates: `pending → signed`, `is_signed = true`, `signed_at` timestamp set

> **⚠️ Sign is inside the detail dialog** — not in a ⋮ menu. Click the declaration row to open the dialog, then click Sign.

### ✅ Verification:
- Each declaration row shows `declarant_name` and `has_conflict` badge (green Independent / red Has Conflict)
- After signing, the row shows a `signed` badge
- `signed_at` timestamp is visible in the detail dialog after signing

### ✅ GAP 9 Stamp Verification:
After signing → open detail dialog → a **"Download Signed Declaration"** button appears if `stamped_document_url` is populated.

---

### Start Engagement Workflow

> **⚠️ Pre-conditions before clicking Start:**
> - All sub-phases 7a through 7e above must be complete
> - All `DeclarationOfIndependence` records for this engagement must have `status = signed` (any `pending` declaration blocks the start with `DECLARATIONS_NOT_SIGNED` error)

The engagement lifecycle is driven entirely by the **Work Orchestration (WO) Workflow Console** on the right side of the Engagement Detail page.

**Step 1 — Start Engagement Workflow:**

1. Open the Engagement Detail page (Sidebar → GRC → **Audit Engagements** → click your engagement)
2. Click the **Start Engagement Workflow** button in the page header
   - This button only appears when `status = planning` AND no workflow is running yet
   - Backend: `POST /engagements/{id}/phase-transition/`
3. On success: GRC engagement status immediately set to `fieldwork` by the service (for UX responsiveness — the WO Kafka event confirms canonically)
4. **WO Workflow Console → Stage 1: Audit Planning → click "Start Fieldwork"**
   - Fires a `grc.stage.completed` Kafka event with `stage_key=planning, action=start_fieldwork`
   - GRC Kafka consumer confirms `status = fieldwork`
   - WO advances to Stage 2: Fieldwork

> **⚠️ Stage 1 must be completed in the WO Console before Stage 2 is accessible.** If you skip clicking "Start Fieldwork", the WO stays on Stage 1 and the "Start Reporting" action will not appear.

**Step 2 — Fieldwork → Reporting:**

5. Complete fieldwork: create working papers (Phase 8), findings (Phase 9), recommendations (Phase 10)
6. **WO Workflow Console → Stage 2: Fieldwork** → click **Start Reporting**
   - GRC consumer updates engagement status to `reporting` ✓

**Step 3 — Reporting → Completed:**

7. *(After audit report created and approved — Phase 13)*
   **WO Workflow Console → Stage 3: Reporting** → click **Mark Complete**
   - GRC consumer updates engagement status to `completed`, sets `actual_end_date` ✓

**Full WO stage sequence:**

| # | WO stage_key | Stage Name | Action Button | GRC Status After |
|---|---|---|---|---|
| 1 | `planning` | Audit Planning | **Start Fieldwork** | `fieldwork` |
| 2 | `fieldwork` | Fieldwork | **Start Reporting** | `reporting` |
| 3 | `reporting` | Reporting | **Mark Complete** | `completed` |

> **Rejection path:** If cancelled at any stage, GRC resets engagement status to `planning` and clears `workflow_plan_id`.

> **⚠️ Important:** You must click **Start Reporting** in WO (Step 2) before attempting Phase 13 (Create Audit Report). The Audit Report create form only shows engagements in `reporting` or `completed` status.

---

## Phase 8 — Create Working Papers

**Page:** Sidebar → **Audit Engagements** → find your engagement row → click the **⋮ (three-dot) action menu** on the right → select **"View"** (Eye icon) → this opens the **Engagement Detail page** → scroll down to the **Working Papers** section → click **Add Working Paper**

> **⚠️ Navigation note:** Working Papers do NOT have their own sidebar entry. They are embedded inside the Audit Engagement **Detail** page. You must "View" an engagement first to see and manage its working papers.

> **Note:** Reference Number is **auto-generated** by the backend (format: `WP-{engagement_ref}-{sequence:03d}`, e.g. `WP-ENG-2025-001-001`). The creation form only accepts Title, Paper Type, and Document — do not attempt to enter a reference number manually.

### Working Paper 1

| Field | Value |
|---|---|
| **Title** | `ICT Access Control Assessment` |
| **Paper Type** | `fieldwork` *(choices: `planning` \| `fieldwork` \| `analysis` \| `conclusion` \| `other`)* |
| **Document** | *(required — upload a document file; stored in DRS; returns a `document_id` UUID)* |

### Working Paper 2

| Field | Value |
|---|---|
| **Title** | `Change Management Procedures Review` |
| **Paper Type** | `fieldwork` |
| **Document** | *(required — upload a document file)* |

> **⚠️ `document_id` is required** — working papers must have a DRS document attached. The file upload is **not optional**.

### Working Paper Approval (per paper):

> The working paper review status field is `review_status` (not `status`). Values: `draft → pending → reviewed → approved`.

1. Click on the working paper → detail page at `/service/grc/working-papers/{id}`
2. Click **Submit for Review**
   - Backend: `POST /working-papers/{id}/review/`
   - Only the `prepared_by` user can submit
   - `review_status` immediately set to `pending`
   - Work Orchestration starts a 2-stage workflow
3. In the **WO Workflow Console**, complete each stage:

| # | WO stage_key | Stage Name | Action Buttons |
|---|---|---|---|
| 1 | `working_paper_review` | Working Paper Review | **Approve** / Reject / Request Changes |
| 2 | `working_paper_approval` | Working Paper Approval | **Final Approve** / Reject |

4. After WO final approval → Kafka event → `review_status = approved`

> **Rejection path:** `final_decision=rejected` → `review_status = reviewed` (with comments); `cancelled` → `review_status = draft`.

---

## Phase 9 — Create Audit Findings

**Page:** Sidebar → **Audit Findings** → Click **Create**

> Findings follow the **4 C's pattern**: Condition, Criteria, Cause, Effect
> **Note:** Reference Number is **auto-generated** by the backend (format: `FND-{engagement_ref}-{sequence}`). Do not enter it manually.
> **Note:** Quarter dropdown **filters by selected Fiscal Year** — selecting a different fiscal year automatically updates the available quarters.

### Finding 1: Inadequate ICT Access Controls

| Field | Value |
|---|---|
| **Title** | `Inadequate ICT Access Controls` |
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **Fiscal Year** | `Fiscal Year 2025/2026` |
| **Quarter** | `Q3 (Jan–Mar 2026)` |
| **Severity** | `High` |
| **Finding Type** | `Internal Control Deficiency` |
| **Risk Rating** | `High Risk` |
| **Condition** | `User access reviews are not performed regularly. 15 out of 42 sampled user accounts had excessive privileges beyond job requirements. 3 terminated employees still had active system access.` |
| **Criteria** | `FCC ICT Policy Section 4.3 requires quarterly access reviews. ISO 27001 A.9.2.5 requires timely removal of access rights upon termination. Best practice requires least-privilege access principle.` |
| **Cause** | `No automated process for periodic access review. HR termination process does not include mandatory IT notification. Access provisioning lacks documented approval workflow.` |
| **Effect** | `Unauthorized access risk to sensitive FCC data and systems. Potential data breach exposure. Non-compliance with information security policy may result in regulatory findings.` |
| **Auditee Response** | *(leave blank — auditee responds later)* |
| **Management Response** | *(leave blank — management responds later)* |

### Finding 2: Missing Change Management Documentation

| Field | Value |
|-------|-------|
| **Title** | `Missing Change Management Documentation` |
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **Fiscal Year** | `Fiscal Year 2025/2026` |
| **Quarter** | `Q3 (Jan–Mar 2026)` |
| **Severity** | `Medium` |
| **Finding Type** | `Operational Inefficiency` |
| **Risk Rating** | `Medium-High Risk` |
| **Condition** | `7 out of 12 system changes in the review period lacked proper change request documentation. No evidence of impact assessment or rollback planning for 4 critical production changes.` |
| **Criteria** | `FCC Change Management Policy requires documented change requests with impact assessment, testing evidence, and approval from system owner before implementation. ITIL best practice mandates complete change records.` |
| **Cause** | `Change management process is manual and paper-based. Emergency change procedures are not clearly defined, leading to bypassing of normal approval workflow. Staff awareness of CM procedures is low.` |
| **Effect** | `Increased risk of system instability from untested changes. Inability to perform root cause analysis when incidents occur. Audit trail gaps for regulatory compliance purposes.` |

**Expected:** 2 findings created with status `draft`. Progress each finding through its lifecycle:

> **⚠️ Finalizing to `final` requires both responses.** The backend (`POST /findings/{id}/finalize/`) enforces that `auditee_response` AND `management_response` must both be non-empty before allowing the `discussed → final` transition. The UI **Finding Lifecycle** dialog (⋮ menu → **Lifecycle**) disables the **Finalize** button until both are saved.

**For each finding:**

| Step | Action | Result |
|------|--------|--------|
| 1 | Created | `draft` |
| 2 | Click ⋮ → **Lifecycle** → **Mark as Discussed** | `discussed` |
| 3 | In the Lifecycle dialog → enter **Auditee Response** → click **Save** | Response saved (✓ shown) |
| 4 | Enter **Management Response** → click **Save** | Response saved; **Finalize** button enabled |
| 5 | Click **Finalize** (target: `final`) | `final` |

**Sample responses for Finding 1 (Inadequate ICT Access Controls):**
- **Auditee Response:** `Management acknowledges the control gap. An immediate access review has been initiated and 15 over-privileged accounts have been identified for remediation. Terminated employee access will be revoked within 5 business days.`
- **Management Response:** `ICT Director to implement quarterly automated access reviews by Q4 2026. HR termination notification process will be revised to include mandatory IT access revocation step.`

**Sample responses for Finding 2 (Missing Change Management Documentation):**
- **Auditee Response:** `IT Operations team acknowledges the documentation deficiency. Retrospective documentation is being prepared for the 7 incomplete change records identified.`
- **Management Response:** `A digital change management tool will be procured by Q3 2026. Emergency change procedures will be formally documented and all IT staff will receive CM training by Q2 2026.`

---

## Phase 10 — Create Audit Recommendations

**Page:** Sidebar → **Audit Recommendations** → Click **Create**

> **Note:** Reference Number is **auto-generated** by the backend (format: `REC-{finding_ref}-{sequence}`). Do not enter it manually.
> **Note:** Responsible Party is a **SmartSelect user picker** — select a user from the dropdown (fetches users from IAM service).

### Recommendation 1: Automated User Access Review

| Field | Value |
|---|---|
| **Title** | `Implement Automated User Access Review Process` |
| **Finding** | Select `Inadequate ICT Access Controls` (must be in `final` status) |
| **Priority** | `high` |
| **Description** | `Implement an automated quarterly user access review process integrated with the HR system for timely access revocation upon staff termination or role change.` |
| **Responsible Party** | `System Administrator` *(select from user dropdown)* |
| **Agreed Action** | `1. Deploy automated access review tool by Q4 2026\n2. Integrate HR termination notifications with IT access management\n3. Implement least-privilege access model across all critical systems\n4. Conduct training for all ICT staff on access management procedures` |
| **Target Date** | `2026-06-30` |

### Recommendation 2: Digitize Change Management

| Field | Value |
|---|---|
| **Title** | `Digitize Change Management Process` |
| **Finding** | Select `Missing Change Management Documentation` (must be in `final` status) |
| **Priority** | `medium` |
| **Description** | `Implement a digital change management system with automated approval workflows, impact assessment templates, and mandatory documentation requirements before production deployment.` |
| **Responsible Party** | `System Administrator` *(select from user dropdown)* |
| **Agreed Action** | `1. Procure and deploy digital change management tool\n2. Define and document emergency change procedures\n3. Conduct CM awareness training for all technical staff\n4. Establish monthly CM compliance reporting` |
| **Target Date** | `2026-09-30` |

**Expected:** 2 recommendations created with status `open`. Progress each through the status update dialog (⋮ → **Progress Update**):

> **⚠️ Some transitions require additional fields.** The status update dialog shows conditional input fields that are mandatory before the **Update Status** button becomes active.

| Step | Transition | Required Field in Dialog |
|------|-----------|-------------------------|
| 1 | `open → in_progress` | *(none)* |
| 2 | `in_progress → implemented` | **Implementation Notes** *(mandatory — describe what was implemented and how)* |
| 3 | `implemented → verified` | **Verification Evidence** *(mandatory — describe verification testing/results/evidence)* |
| 4 | `verified → closed` | *(none)* |

**Sample Implementation Notes (for both recommendations):**
- Rec 1: `Automated access review tool deployed and integrated with HR termination workflow. Quarterly review schedule configured. All 42 over-privileged accounts remediated.`
- Rec 2: `ServiceNow ITSM module activated for change management. All staff trained. Emergency change procedure documented and approved.`

**Sample Verification Evidence (for both recommendations):**
- Rec 1: `Post-implementation review conducted March 2026. Zero terminated employees with active access. Q1 2026 access review completed with 100% coverage. Automated alerts confirmed operational.`
- Rec 2: `Testing of 15 changes post-implementation showed 100% documentation compliance. CM audit report Q1 2026 confirms zero undocumented production changes.`

---

## Phase 11 — Audit Monitoring

**Page:** Sidebar → **Audit Monitoring** → Click **Create**

> **What this is:** `ImplementationMonitoring` is a 1:1 header per recommendation that tracks implementation progress across multiple review cycles. Each cycle is an `AuditeeFollowUpResponse` record.

> **Pre-condition:** The recommendation must be in `in_progress` status or later. Recommendations in `open` status cannot have monitoring created yet.

### Step 1: Create the Monitoring Header

| Field | Value |
|---|---|
| **Recommendation** (`recommendation_id`) | `REC-2025-001` *(select Implement Automated User Access Review)* |
| **Next Review Date** (`next_review_date`) | `2026-06-30` *(optional — target date for first review)* |

**Expected:** Monitoring record created with `status: active`.

> **⚠️ Model note:** The monitoring header status is `active | closed` only. Implementation progress is tracked in the **review cycle** (follow-up responses), not on the header directly.

### Step 2: Create the First Review Cycle

> **⚠️ UI Flow Diverges From Backend Design Here — Read Carefully.**

The backend uses two separate endpoints to create cycles:

- `POST /implementation-monitoring/{pk}/review/` — the "official" cycle-open endpoint. **Requires `implementation_progress` (0–100).** Updates header snapshot fields (`latest_progress`, `last_review_date`) and resets `notification_sent_at` to `null`. Used for cycle 2+.
- `POST /implementation-monitoring/{pk}/responses/` — the raw list-create endpoint. Creates a cycle with `status=pending` without requiring or storing `implementation_progress`. Does not update header snapshots. Used by the **"Add Response" form in the detail dialog**.

**To create the FIRST cycle in the UI:**
1. Click **View** (eye icon) on the monitoring record → the detail dialog opens
2. In the detail dialog, click **Add Response** → submit (no `implementation_progress` stored here)
3. Cycle 1 is created via `POST /implementation-monitoring/{pk}/responses/` with `status=pending`

> **⚠️ BUG — The "Record Review" dialog in Progress Update is broken:** When `notification_sent_at` is set, clicking **Progress Update** shows the "Record Review" form, which calls `POST /review/` — but the form is missing an `implementation_progress` input field. The backend requires it and returns `MISSING_PROGRESS` if absent. This applies to cycle 2+. **Workaround:** Call `POST /implementation-monitoring/{pk}/review/` directly via API with `{ "implementation_progress": 50 }` for subsequent cycles.

### Step 3: Notify the Auditee (GAP 7)

> **⚠️ Pre-condition for Notify:** The **Notify** action (`POST /implementation-monitoring/{pk}/notify-auditee/`) requires a pending cycle to already exist. The UI shows "Notify" whenever `notification_sent_at` is `null` (including on a fresh monitoring record) — but calling Notify before creating a cycle via Step 2 will fail with `"No open review cycle. Call /review/ first"`.
>
> **Correct order:** Complete Step 2 first (create cycle via "Add Response"), then proceed here.

2. Click **Progress Update** on the monitoring record → action shown is **Notify Auditee** (since `notification_sent_at = null`)
   - Backend: `POST /implementation-monitoring/{pk}/notify-auditee/`
   - Sets `notified_at` and a **5-business-day response `response_deadline`** on the current cycle
   - Also mirrors these on the monitoring header

### ✅ GAP 7 — 5-Business-Day Response Window:

GAP 7 is enforced when the **Notify Auditee** action is triggered:
- Backend calculates: `deadline = notified_at + 5 business days`
- The `response_deadline` field on the `AuditeeFollowUpResponse` cycle is set automatically
- If the auditee does not respond by the deadline: `is_overdue = true`
- This is **not** a validation on `next_review_date` — it's a deadline on the auditee's response window after notification

### Step 4: Auditee Submission and Auditor Verification

> **⚠️ BUG — No UI path for Auditee Submit:** The submit endpoint (`POST /follow-up-responses/{pk}/submit/`, which transitions cycle `pending → submitted`) has no corresponding button or form in the UI. To test this step, call the API directly:
> ```json
> POST /follow-up-responses/{cycle_pk}/submit/
> Body: { "implementation_progress": 40, "progress_notes": "Vendor procurement 40% done" }
> ```

3. Auditee submits progress via `POST /follow-up-responses/{pk}/submit/` — **API only (no UI)**:
   - `implementation_progress` (%), `progress_notes`, `evidence_documents`
   - Transitions cycle status: `pending → submitted`
   - Backend requires `cycle.status == 'pending'` — will fail with `CYCLE_NOT_PENDING` otherwise

> **⚠️ BUG — Verify button always fails:** The UI's Verify button calls `POST /follow-up-responses/{pk}/verify/` but sends only `{ verification_notes }`. The backend **requires** `verdict` in `('verified', 'rejected')` — the UI is missing this field entirely and always receives `INVALID_VERDICT`. There is also no "Reject" button — only Verify is shown. **Workaround:** Call the verify API directly:
> ```json
> POST /follow-up-responses/{cycle_pk}/verify/
> Body: { "verdict": "verified", "verification_notes": "Progress confirmed by system screenshot" }
> ```
> Note: verify also requires `cycle.status == 'submitted'` (from Step 3 above) — will fail with `CYCLE_NOT_SUBMITTED` if called before submit.

4. Auditor verifies via `POST /follow-up-responses/{pk}/verify/` — **API only (no UI, bug as above)**:
   - **Required:** `verdict` — must be `"verified"` or `"rejected"`
   - **Optional:** `verification_notes`
   - If `verdict=verified` AND `implementation_progress >= 100` → monitoring header `status` set to `closed`
   - If `verdict=verified` AND progress < 100 → header `latest_progress` updated, header stays `active`
   - If `verdict=rejected` → next cycle starts from Step 2 (call `/review/` again)

---

## Phase 12 — Dashboard Verification

**Page:** Click **GRC** in the sidebar header (navigate to `/service/grc`)

**Verify:**
- All module cards are present and show correct counts
- Clicking each card navigates to the correct list page
- The sidebar shows **15 Internal Audit items** under the "Internal Audit" group: Audit Universe, Risk Assessments, Audit Plans, Audit Engagements, Audit Findings, Audit Recommendations, Audit Monitoring, Meetings, Audit Reports, Quarterly Reports, Audit Memos, Declarations, Audit Surveys, Risk Control Matrix, Audit Programs
- **No "Working Papers" entry in the sidebar navigation** — Working Papers are accessed via the Audit Engagements detail page and via the dashboard card
- **Working Papers card IS present on the GRC Dashboard** (path: `/service/grc/working-papers`)
- **No "Auditable Entities" entry** — this concept exists in the Audit Universe, not as a separate sidebar item

---

## Phase 13 — Create Audit Report

**Page:** Sidebar → GRC → **Audit Reports** → Click **Create**

> **Pre-conditions:**
> 1. The audit engagement must be in `reporting` **or `completed`** status — see Phase 7 Step 3 (click **Start Reporting** in the WO Workflow Console). The backend allows report creation for both statuses: `engagement.status not in ('reporting', 'completed')` returns `INVALID_ENGAGEMENT_PHASE`.
> 2. Findings must be in `final` status
> 3. At least one Audit Opinion must be configured in GRC Configuration (e.g., "Qualified", "Unqualified", "Adverse")

> **💡 How status advances:** Engagement status is controlled by WO stage actions, not by a button in GRC. Go to the engagement detail → Workflow Console → Fieldwork stage → **Start Reporting**. After the Kafka event is processed, the engagement status changes to `reporting` and the engagement will appear in the Audit Report create form.

### Audit Report 1: ICT General Controls Draft Report

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` (select — only `reporting` engagements appear) |
| **Audit Opinion** | `Qualified Opinion` (select — findings were found but audit was completable) |
| **Report Type** | `draft` |
| **Report Title** | `ICT General Controls Audit Report — Q3 2025/2026` |
| **Executive Summary** | `The audit of ICT General Controls for the period January–March 2026 identified significant deficiencies in access control management and change management documentation. Overall, the ICT control environment requires substantial improvement in access governance and change management discipline.` |
| **Scope & Objectives** | `The audit covered ICT general controls including: (1) User access management and quarterly access reviews, (2) Change management documentation and approval workflows, (3) Backup and disaster recovery procedures, and (4) Network security configuration for the ICT Directorate.` |
| **Methodology** | `The audit was conducted using a risk-based approach aligned to COBIT 2019 framework. Procedures included: document review of ICT policies, interviews with 8 ICT staff members, system walkthroughs of the access management and change management modules, and substantive testing of 42 user accounts and 12 system changes.` |
| **Conclusion** | `Based on our audit procedures, we conclude that the ICT General Controls environment carries HIGH risk. Inadequate access control reviews and missing change management documentation expose the organization to unauthorized access and system instability risks. Management should implement the agreed recommendations within the agreed timelines.` |
| **Reviewed By** | *(leave empty or select reviewer from the user dropdown)* |

**Expected result:** Report created with status `draft`. Reference number auto-generated (format: `RPT-{engagement_ref}-{sequence}`).

### Status Workflow for Audit Reports:

| Step | Action | Result |
|---|---|---|
| 1 | Create → status `draft` | Report created |
| 2 | Click **Progress Update** → select `under_review` | Submitted for CIA review |
| 2a | *(Optional revert)* Click **Progress Update** → select `draft` | Returns report to `draft` for revision |
| 3 | Click **Progress Update** → select `approved` | Report approved (triggers GAP 12 inline) |
| 4 | Click **Distribute** button *(separate dedicated action — NOT Progress Update)* | Report distributed to auditee → `distributed`; **`report_type` automatically set to `'final'`** |

> **⚠️ `distributed` is NOT reachable via Progress Update.** A separate **Distribute** button/endpoint (`AuditReportDistributeView`) handles this final step, which can include setting distribution recipients. The Progress Update only covers `draft ↔ under_review ↔ approved` transitions.
>
> **⚠️ `under_review → draft` revert is allowed.** The valid transitions include `under_review → ['approved', 'draft']` — the CIA can return the report to `draft` for revision before approving.
>
> **⚠️ Distribution automatically sets `report_type = 'final'`** regardless of what was set during creation. Even if created as `draft` type, after distribution the `report_type` field will read `final`.
>
> **⚠️ GAP 12 fires immediately** inside `AuditReportStatusUpdateView` when the status transitions to `approved` — it publishes `finding.finalized` Kafka events inline (not from a Kafka consumer). This means the events fire synchronously as part of the approve action.

### ✅ GAP 9 — Audit Report Stamp Verification:
After status → `approved`:
1. Open the audit report detail (click **View**)
2. A **"Download Approved Report"** button should appear if `stamped_document_url` is populated
3. This requires the report to have a `document_id` linked to a DRS document
4. Check GRC service logs for: `Stamp triggered for audit_report {id}`

### ✅ GAP 12 — Finding Finalization Event Verification:
Immediately after the report status transitions to `approved`:
1. Check GRC service logs: look for `GAP 12: published N finding.finalized events`
2. Each active finding linked to the engagement should have triggered a `finding.finalized` Kafka event
3. If using Kafdrop or a Kafka consumer monitor, check the `finding.finalized` topic for messages with:
   - `finding_id` matching your finding IDs
   - `approved_by` matching the approving user's ID
   - `engagement_reference` = `ENG-2025-001`
4. If the report has no active findings, log shows `GAP 12: published 0 finding.finalized events`

---

## Phase 14 — Create Audit Meetings

**Page:** Sidebar → GRC → **Meetings** → Click **Create**

> Audit meetings track the formal discussions between the audit team and the auditee. The SRS defines **four** meeting types across the audit lifecycle:
> - **Entry Conference** (`entry`) — Step 14; engagement must be `planning` or `fieldwork`
> - **Pre-Exit Conference** (`pre_exit`) — Step 17; engagement must be `fieldwork` or `reporting`
> - **Audit Team Meeting** (`team`) — Step 20 (internal team consolidation); engagement must be `fieldwork` or `reporting`
> - **Exit Conference** (`exit`) — Step 24; engagement must be `reporting` or `completed`
>
> This phase creates sample data for the three externally-facing meetings (Steps 14, 17, and 24). Step 20 (`team`) is an optional internal team meeting with the same flow.
>
> Per SRS Requirement 13: *"The system shall capture attendance and minutes."*
> Documents (minutes file, attendance sheet) are uploaded to the **Document Records Service** — the same pattern used by Working Papers.
>
> **⚠️ API note:** The `meeting_type` field uses short API values: `entry`, `pre_exit`, `team`, `exit`. The UI shows display labels: "Entry Conference", "Pre-Exit Conference", "Audit Team Meeting", "Exit Conference".
>
> **⚠️ `scheduled_date`** — The UI shows **two separate inputs**: a **Date** field and a **Time** field. They are combined at submission into a single ISO DateTime (`2026-03-01T09:00:00`). The API field `scheduled_date` is a `DateTimeField` — it expects the combined value.

### Meeting 1: Entry Conference (`entry` type)

#### Step A — Create (Scheduled)

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **Meeting Type** | `entry` *(API value — UI shows "Entry Conference")* |
| **Meeting Title** | `ICT Audit Entry Conference — March 2026` |
| **Scheduled Date** | `2026-03-01` *(enter in the Date field)* |
| **Scheduled Time** | `09:00` *(enter in the separate Time field — UI combines them into `2026-03-01T09:00:00` on submit)* |
| **Location** | `ICT Directorate Board Room, HQ Building, 3rd Floor` |
| **Agenda** | `1. Introduction of audit team members and scope of the engagement\n2. Presentation of audit objectives and methodology\n3. Overview of key risk areas identified during planning\n4. Discussion of audit timeline and key milestones\n5. Logistics: document requests, staff availability, access requirements\n6. Questions from ICT Directorate management` |

**Expected result:** Meeting created with status `scheduled`.

#### Step B — Progress to In Progress
Click **Progress Update** → select `in_progress`.

> **⚠️ Once in-progress, the structural fields (Engagement, Type, Title, Date, Location, Agenda) are LOCKED.** Only post-meeting fields are editable while `in_progress`: **Minutes**, **Key Discussions**, **Action Items**, **Attendees**, and document uploads (Minutes Doc, Attendance Sheet).

#### Step C — Edit to Record Post-Meeting Data
Click **⋮ menu** → **Edit** while meeting is `in_progress`:

| Field | Value |
|---|---|
| **Minutes** | `The entry conference was held on 1 March 2026 at 09:00hrs. The Lead Auditor introduced the audit team and presented the audit scope, objectives and methodology. ICT Directorate management acknowledged the audit timeline and committed to providing requested documents within 5 working days. Key logistics were agreed including room allocation and staff availability schedule.` |
| **Key Discussions** | `1. Audit scope confirmed — access controls, change management, backup and recovery in scope.\n2. ICT Director committed to designating a liaison officer by 3 March 2026.\n3. Document request list to be submitted by audit team within 2 working days.\n4. Audit timeline: fieldwork 1–28 March, preliminary findings 5 April.` |
| **Attendees** | Add the following rows: |

**Attendees to add (click Add Attendee for each):**

| Name | Title/Position | Role | Present |
|---|---|---|---|
| `System Administrator` | `Lead Auditor` | `Auditor` | ✅ Yes |
| `ICT Director` | `Director of ICT` | `Auditee` | ✅ Yes |
| `ICT Systems Manager` | `Systems Manager` | `Auditee` | ✅ Yes |

| **Action Items** | *(optional JSON list — can add action items arising from the meeting: `[{"description": "Designate liaison officer", "responsible_name": "ICT Director", "due_date": "2026-03-03", "status": "open"}]`)* |

| Document Field | Value |
|---|---|
| **Minutes Document** | *(upload a PDF/DOCX file — stored in Document Records Service)* |
| **Attendance Sheet** | *(upload a PDF/DOCX file — stored in Document Records Service)* |

**Click Update Meeting** → saved.

#### Step D — Complete the Meeting
Click **Progress Update** → select `completed`.

> **⚠️ Minutes are required** before marking `completed`. The backend enforces this per SRS.

**Expected result:** Status → `completed`.

---

### Meeting 2: Pre-Exit Conference (`pre_exit` type)

> **SRS Step 17:** Before the exit conference, a pre-exit meeting is held between the audit team to review draft findings and align positions before presenting to the auditee.
> Requires engagement in `fieldwork` or `reporting` phase.

#### Step A — Create (Scheduled)

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **Meeting Type** | `pre_exit` *(API value — UI shows "Pre-Exit Conference")* |
| **Meeting Title** | `ICT Audit Pre-Exit Team Review — April 2026` |
| **Scheduled Date** | `2026-04-20` *(Date field)* |
| **Scheduled Time** | `10:00` *(Time field — UI combines into `2026-04-20T10:00:00`)* |
| **Location** | `Internal Audit Directorate Conference Room` |
| **Agenda** | `1. Review all draft findings for accuracy and completeness\n2. Align team positions on risk ratings\n3. Confirm recommendation wording and responsible parties\n4. Prepare presentation materials for Exit Conference` |

**Expected result:** Second meeting created with status `scheduled`.

#### Steps B–D — Same post-meeting flow as Meeting 1
Progress → `in_progress` → Edit (add minutes, attendees, key discussions, upload docs) → Progress → `completed`.

---

### Meeting 3: Exit Conference (`exit` type)

> **SRS Step 24:** The exit conference presents final findings and recommendations to auditee management. Requires engagement in `reporting` or `completed` phase.

#### Step A — Create (Scheduled)

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **Meeting Type** | `exit` *(API value — UI shows "Exit Conference")* |
| **Meeting Title** | `ICT Audit Exit Conference — April 2026` |
| **Scheduled Date** | `2026-04-25` *(Date field)* |
| **Scheduled Time** | `14:00` *(Time field — UI combines into `2026-04-25T14:00:00`)* |
| **Location** | `ICT Directorate Board Room, HQ Building, 3rd Floor` |
| **Agenda** | `1. Presentation of draft audit findings and recommendations\n2. ICT Directorate management response to each finding\n3. Discussion of agreed action plans and target dates\n4. Confirmation of responsible parties for each recommendation\n5. Next steps: report finalization and distribution timeline` |

**Expected result:** Third meeting created with status `scheduled`.

#### Steps B–D — Same post-meeting flow as Meeting 1
Progress → `in_progress` → Edit (add minutes, attendees, key discussions, upload docs) → Progress → `completed`.

---

### Full Status Workflow:

| Step | Action | Edit Fields Available | Result |
|---|---|---|---|
| 1 | **Create** | Engagement, Type, Title, Date, Time, Location, Agenda | `scheduled` |
| 1a | *(Optional)* **Progress Update** → `cancelled` | — | `cancelled` *(terminal — cannot undo)* |
| 2 | **Progress Update** → `in_progress` | — | `in_progress` |
| 2a | *(Optional)* **Progress Update** → `cancelled` | — | `cancelled` from `in_progress` *(terminal)* |
| 3 | **Edit** (⋮ menu) | Minutes, Key Discussions, **Action Items**, Attendees, Minutes Doc, Attendance Sheet | Post-meeting data saved |
| 4 | **Progress Update** → `completed` | — | `completed` (requires minutes) |

> **⚠️ Backend validation:** Minutes field must be non-empty before `completed` is allowed (`MINUTES_REQUIRED` error otherwise).
> **⚠️ Document uploads** go to the Document Records Service and return a UUID stored as `minutes_document_id` / `attendance_document_id` on the meeting record.
> **⚠️ `cancelled` is terminal** — no transitions out of `cancelled` or `completed` are possible.

---

## Phase 15 — Create Quarterly Audit Report

**Page:** Sidebar → GRC → **Quarterly Reports** → Click **Create**

> Quarterly reports consolidate audit activity findings and recommendations across all engagements for a fiscal quarter. The system can auto-consolidate summary data from individual audit reports.

### Quarterly Report: Q3 2025/2026

| Field | Value |
|---|---|
| **Fiscal Year** | `Fiscal Year 2025/2026` |
| **Quarter** | `Q3 (Jan–Mar 2026)` *(auto-filters when fiscal year is selected)* |
| **Report Title** | `Internal Audit Activity Report — Q3 FY 2025/2026` |
| **Reporting Period Start** | `2026-01-01` |
| **Reporting Period End** | `2026-03-31` |
| **Executive Summary** | `During Q3 FY 2025/2026, the Internal Audit Directorate completed the ICT General Controls Audit and made significant progress on risk assessment activities. Two audit findings were raised, both requiring management attention. Two recommendations with agreed action plans have been issued and are being tracked for implementation.` |
| **Audit Activities Summary** | `Q3 audit activities included: (1) Completion of the ICT General Controls Audit (ENG-2025-001), (2) Working paper preparation and review for 2 working papers, (3) Issuance of 2 audit findings (1 High severity, 1 Medium severity), (4) Issuance of 2 recommendations with agreed action plans and target dates, (5) Follow-up on 1 open recommendation from Q2.` |
| **Resource Utilization** | `Total audit days utilized: 42 of 45 planned (93% utilization). 1 Lead Auditor and 2 Audit Team Members engaged. No significant resource gaps reported.` |
| **Key Achievements** | `1. Successfully completed ICT General Controls Audit within planned timeline.\n2. Identified critical access control weaknesses with agreed remediation plan.\n3. 100% working paper completion rate for the quarter.\n4. Management acceptance rate of 100% for recommendations issued.` |
| **Challenges & Constraints** | `1. Delayed response from ICT Directorate on document provision (3-day delay).\n2. One audit team member on medical leave for 5 days — workload redistributed.` |
| **Planned vs Actual** | `Planned engagements: 1 (ICT Audit). Completed: 1. Planned findings: 3. Actual: 2. Variance in findings reflects fewer control failures than anticipated in planning phase.` |
| **Management Action Status** | `REC-2025-001: Vendor selected for automated access review tool (25% complete).\nREC-2025-002: Digital change management tool procurement on track (0% implementation — planning phase).` |
| **Next Quarter Plan** | `Q4 2026 planned activities: (1) Finance Unit Audit, (2) Follow-up review on ICT recommendations, (3) Quarterly report consolidation review.` |
| **Conclusion** | `The Internal Audit Directorate executed its Q3 audit plan effectively. Key risk areas in ICT were identified and management has committed to timely remediation. Monitoring of recommendation implementation will continue in Q4.` |
| **Reviewed By** | *(leave empty or enter reviewer)* |
| **Submitted To** | `FCC Audit Committee` |

**Expected result:** Quarterly report created with status `draft`.

### Consolidate Data (Auto-Populate Summary):

1. Open the quarterly report detail (click **View** → **⋮** action menu)
2. While in `draft` status, a **Consolidate** button appears
3. Click **Consolidate** — the system finds `AuditReport` records in `approved` status whose engagement's planned date range overlaps with the reporting period (`2026-01-01` – `2026-03-31`). Counts findings/recommendations/implementation_rate — links them via `engagement_reports` M2M.
4. Summary statistics (`total_engagements`, `total_findings`, `critical_findings`, `total_recommendations`, `implementation_rate`) are auto-populated from real data.

> **⚠️ Pre-condition for Consolidate:** The ICT General Controls AuditReport (from Phase 13) **must be in `approved` or `distributed` status** before Consolidate can succeed. If no AuditReports with matching date range and eligible status exist, the backend returns `NO_ELIGIBLE_REPORTS` error. Complete Phase 13 first.
>
> **⚠️ There is NO `is_consolidated` field in the backend model or API response.** The frontend list page shows an "is_consolidated" badge column but the field is **never returned from the API** — it will always display **"No"** regardless of whether consolidation has occurred. This is a known frontend display bug. Verify actual consolidation by inspecting the `engagement_report_count` field (should be ≥ 1) and the `total_findings` / `total_recommendations` values (should be non-zero after consolidate).

### Status Workflow for Quarterly Reports:

> **⚠️ Hybrid model:** The first step uses a dedicated **Submit for Approval** action (starts the 4-stage WO workflow). Subsequent transitions use **Progress Update** (which calls `QuarterlyReportStatusUpdateView` and requires an active `workflow_plan_id`).

| Step | Action | Result |
|---|---|---|
| 1 | Create → status `draft` | Report in draft |
| 2 | *(Optional)* Click **Consolidate** | Auto-fills summary statistics and links engagement reports |
| 3 | Click **Submit for Approval** *(dedicated button — starts WO workflow)* | WO created → `status: cia_review` |
| 3a | *(Optional revert)* Click **Progress Update** → `draft` | CIA returns report to draft for revision |
| 4 | Click **Progress Update** → `management_review` | CIA approves; management reviews |

> **⚠️ Pre-condition for `management_review`:** The backend enforces two checks before this transition is allowed:
> 1. At least one audit report must be linked to this quarterly report (satisfied after Consolidate in Step 2)
> 2. `executive_summary` must be non-empty (satisfied by the data entered during creation)

> **⚠️ BUG — `management_review` transitions are wrong in the UI:** The frontend Progress Update options from `management_review` are `['committee_review', 'draft']`. This is incorrect: the backend only allows `management_review → ['committee_review', 'improvement_required']`.
> - Selecting **`draft`** from `management_review` in the UI → backend returns `INVALID_STATUS_TRANSITION`. *(Frontend bug: shows a transition the backend rejects.)*
> - **`improvement_required`** from `management_review` is NOT offered by the UI dropdown. *(Frontend bug: missing option.)* **Workaround:** call `POST /quarterly-reports/{pk}/update-status/` with `{ "status": "improvement_required" }` directly.

| 5 | Click **Progress Update** → `committee_review` | Management adopts; committee reviews |
| 6a | Click **Progress Update** → `improvement_required` *(from `committee_review`)* | If revisions needed — returns to CIA. Works via UI from `committee_review` only. |
| 6b | Click **Progress Update** → `approved` | Committee approves |
| 7 | Click **Progress Update** → `submitted_to_commission` *(requires `submission_date` in body)* | Submitted to Commission for noting |

> **⚠️ `submitted_to_commission`** requires the request body to include `submission_date` (a date value) **unless already set on the record from creation**. Without it the backend returns `SUBMISSION_DATE_REQUIRED`.
>
> **⚠️ `improvement_required → cia_review`** re-activates the WO for a second iteration; the report restarts the review pipeline.

---

## Status Progression Quick Reference

| Entity | Status Flow |
|---|---|
| **Audit Universe** | `draft` → `under_review` → `approved` |
| **Risk Assessment** | `draft` → `submitted` → `reviewed` → `approved` |
| **Audit Memo** | `draft` → `cia_review` → `dg_review` → `approved` → `transmitted` |
| **Declaration** | `pending` → `signed` |
| **Audit Survey** | `draft` → `completed` |
| **Risk Control Matrix** | `draft` → `submitted` → `approved` |
| **Audit Program** | `draft` → `under_review` → `approved` *(WO 2-stage; submit sets `under_review` immediately)* |
| **Audit Plan** | `draft` → `management_review` → `approved` *(GRC statuses; WO drives the internal review stages)* |
| **Audit Engagement** | `planning` → `fieldwork` → `reporting` → `completed` |
| **Working Paper** | `review_status: draft` → `pending` → `reviewed` → `approved` *(submit sets `pending`; WO 2-stage drives `reviewed`/`approved`)* |
| **Audit Finding** | `draft` → `discussed` → `final` |
| **Audit Recommendation** | `open` → `in_progress` → `implemented` → `verified` → `closed` |
| **Audit Report** | `draft` → `under_review` → `approved` → `distributed` |
| **Audit Meeting** | `scheduled` → `in_progress` → `completed` *(or `cancelled`)* |
| **Quarterly Report** | `draft` → `cia_review` → `management_review` → `committee_review` → `approved` → `submitted_to_commission` |

---

## Execution Order (35 Steps)

```
 1.  Login as admin@fcc.go.tz
 2.  GRC → Configuration → Verify lookups exist
 3.  GRC → Audit Universe → Create universe for FY 2025/2026
 4.  Universe Detail → Add 4 Auditable Entities (ICT, Finance, Zone, Procurement)
 5.  GRC → Risk Assessments → Create 4 assessments (one per entity)
 5a. Risk Assessment Detail → Verify auto_risk_score + auto_residual_score are populated (GAP 6)
 6.  Universe Detail → Submit for Approval → Approve via Workflow Console
 7.  GRC → Audit Plans → Create RBIAP-2025-001 (check for auto-generated draft from GAP 11)
 8.  Plan Detail → Submit → Approve through 4-stage workflow
 9.  GRC → Audit Engagements → Create ENG-2025-001 (ICT audit, type=planned) — status = `planning`
10.  GRC → Audit Memos → Create memo for ENG-2025-001 → Submit (draft → cia_review) → WO Console: Stage 1 = cia_memo_review → Stage 2 = dg_memo_approval → approved (GAP 1) *(no engagement status constraint on memos)*
10a. Audit Memo → Verify GAP 9 stamp: stamped_document_url populated after approved
11.  GRC → Declarations → Create Declaration 1 (no conflict) → Sign it *(engagement still `planning`; signed before workflow start so guard passes)* (GAP 2)
11a. Declaration → Verify GAP 9 stamp: stamped_document_url populated after signed
12.  GRC → Audit Surveys → Create preliminary survey for ENG-2025-001 → Progress: draft → completed *(engagement must be `planning`)* (GAP 3)
13.  GRC → Risk Control Matrix → Create RCM → Add 2 RCM Entries → Progress: draft → submitted → approved *(engagement must be `planning`)* (GAP 4)
14.  GRC → Audit Programs → Create program *(engagement must be `planning`)* → Submit (draft → under_review) → WO Console: Stage 1 = ia_program_review → Stage 2 = cia_program_approval → approved (GAP 5)
14a. Audit Program → Verify GAP 9 stamp: stamped_document_url populated after approved
15.  Engagement Detail → **Start Engagement Workflow** *(Survey + RCM + Program all complete; Declaration 1 signed — all `planning`-locked steps done)* → status immediately `fieldwork` → WO Console: Stage 1 (planning) → click **"Start Fieldwork"** → WO advances to Stage 2
15a. GRC → Declarations → Create Declaration 2 (with conflict, edge case test — declaration creation has no engagement status constraint; engagement now `fieldwork`)
15b. Declaration 2 → note: NOT signed (edge case display only)
16.  GRC → Meetings → Create Entry Conference (type=`entry`, engagement `planning`/`fieldwork`) → scheduled → in_progress → completed
17.  Engagement Detail → Add 2 Working Papers (WP-001, WP-002) → each requires `document_id` (DRS upload)
18.  Working Paper Detail → Submit (review_status: draft → pending) → WO Console: Stage 1 = working_paper_review → Stage 2 = working_paper_approval → approved
19.  GRC → Audit Findings → Create FND-2025-001 (Access Controls)
20.  GRC → Audit Findings → Create FND-2025-002 (Change Management)
21.  Progress findings: draft → discussed → final
22.  GRC → Meetings → Create Pre-Exit Conference (type=`pre_exit`, engagement `fieldwork`/`reporting`) → scheduled → completed
23.  GRC → Meetings → Create Exit Conference (type=`exit`, engagement `reporting`/`completed`) → scheduled → completed
24.  GRC → Audit Recommendations → Create REC-2025-001
25.  GRC → Audit Recommendations → Create REC-2025-002
26.  Progress recommendations: open → in_progress
27.  Workflow Console → Start Reporting (engagement → reporting status)
28.  GRC → Audit Reports → Create draft audit report
29.  Audit Report → Progress: draft → under_review → approved (check GAP 12 logs) → click Distribute button (separate action → distributed)
29a. Audit Report → Verify GAP 9 stamp + verify GAP 12 finding.finalized Kafka events in logs
30.  GRC → Audit Monitoring → Create monitoring for REC-2025-001 (recommendation must be `in_progress`)
30a. Monitoring → POST /{pk}/review/ (progress=25) → POST /{pk}/notify-auditee/ → verify GAP 7 response_deadline set (5 business days)
31.  GRC → Quarterly Reports → Create Q3 2025/2026 quarterly report
32.  Quarterly Report → Click Consolidate (auto-fills stats + M2M links from approved AuditReports)
33.  Quarterly Report → Submit for Approval (draft → cia_review via WO) → Progress Update: management_review → committee_review → approved → submitted_to_commission (with submission_date)
34.  GRC → Dashboard → Verify all cards and navigation
35.  Review GRC service logs for any GAP-related errors or warnings
```

> **Estimated time:** 60–90 minutes for full end-to-end flow
