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

ME: I DID IT AND PASSED — Universe created successfully with correct fiscal year, description, and reviewer.

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

ME: I DID IT AND PASSED — Universe created successfully with correct fiscal year, description, and reviewer.

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

### ✅ GAP 6 — Auto-Score Verification:
After saving each risk assessment, open the detail dialog and verify:
- `Auto Risk Score` field is populated (calculated from `likelihood × impact × control_effectiveness`)
- `Auto Residual Score` field is populated (calculated from `residual_likelihood × residual_impact × residual_control`)
- These are **read-only** — they update automatically when you change the scoring inputs
- Backend field aliases: `auto_risk_score` → `calculated_weighted_score`, `auto_residual_score` → `calculated_residual_score`

---

## Phase 5 — Submit Universe for Approval

**Page:** Go back to the **Audit Universe** detail page

1. Click **Submit for Approval**
2. Workflow Console activates (right panel)
3. **Stage 1 — CIA Review:** Click **Approve**
4. Universe status → `approved`

**Expected:** Status badge changes to `approved`. Universe is now locked for editing.

---

## Phase 6 — Create Audit Plan (RBIAP)

**Page:** Sidebar → **Audit Plans** → Click **Create Audit Plan**

> **Pre-condition:** Audit Universe must be `approved` before creating a plan. The Audit Universe dropdown only shows approved universes.

| Field | Value |
|---|---|
| **Reference Number** | `RBIAP-2025-001` *(optional — leave empty to auto-generate)* |
| **Plan Title** | `Risk-Based Internal Audit Plan 2025/2026` |
| **Plan Type** | `Annual Plan` |
| **Fiscal Year** | `2025/2026` |
| **Audit Universe** | *(select the approved universe — only approved ones appear)* |
| **Management Comments** | *(leave empty — filled during management review stage)* |
| **Committee Comments** | *(leave empty — filled during committee review stage)* |

> **Note:** Priority Areas and Resource Allocation fields exist in the backend model but are not currently exposed in the Create form. They can be managed via the detail page or API.

**Expected:** Plan created with status `draft`.

### Submit Plan for Approval (4-stage workflow):

1. Click **Submit for Approval**
2. **Stage 1 — CIA Review:** Approve
3. **Stage 2 — Management Adoption:** Approve
4. **Stage 3 — Audit Committee Approval:** Approve
5. **Stage 4 — Commission Approval:** Approve
6. Plan status → `approved`

### ✅ GAP 11 — Auto-Generate Plan Draft:
After the Audit Universe reaches `approved`:
1. Navigate to GRC → **Audit Plans** → Click **Create**
2. The form has a **"Generate from Universe"** button (or equivalent) that auto-drafts plan objectives/scope from the approved universe's auditable entities and risk assessment scores
3. Alternatively, after universe approval, check if a plan draft was **auto-created** in the Audit Plans list (the GAP 11 backend hook fires a `plan.auto_generated` event on universe approval)
4. Either way, review the auto-generated content and adjust as needed before submitting through the 4-stage approval workflow

---

## Phase 7 — Create Audit Engagement

**Page:** Sidebar → **Audit Engagements** → Click **Create**

| Field | Value |
|---|---|
| **Title** | `ICT General Controls Audit 2025/2026` |
| **Reference Number** | `ENG-2025-001` |
| **Engagement Type** | `planned` |
| **Audit Plan** | `RBIAP-2025-001` (select approved plan) |
| **Auditable Entity** | `ICT Directorate (ICT-001)` |
| **Lead Auditor** | `fb680f30-398b-4b86-865b-455a35c3c8d9` (admin) |
| **Scope** | `Review of ICT general controls including access management, change management, backup and recovery, and network security` |
| **Objectives** | `1. Assess adequacy of ICT access controls\n2. Evaluate change management procedures\n3. Test backup and disaster recovery plans\n4. Review network security configuration` |
| **Methodology** | `Document review, interviews with ICT staff, system walkthrough, control testing using COBIT framework alignment` |
| **Planned Start Date** | `2026-03-01` |
| **Planned End Date** | `2026-04-30` |

**Expected:** Engagement created with status `planning`.

### Start Engagement Workflow:

The engagement lifecycle is driven entirely by the **Work Orchestration (WO) Workflow Console**. Each stage action sends a Kafka event to GRC which updates the engagement status (FIMS Architecture Principle 2).

1. Open engagement detail → click **Start Workflow** → Engagement enters `fieldwork`
2. Complete fieldwork: create working papers (Phase 8), findings (Phase 9), recommendations (Phase 10)
3. In the Workflow Console → **Stage 2: Fieldwork** → click **Start Reporting**
   - WO fires a `grc.stage.completed` Kafka event with `stage_key=fieldwork, action=start_reporting`
   - GRC consumer updates engagement status to `reporting` ✓
4. *(After audit report is created and approved — Phase 13)*
   In the Workflow Console → **Stage 3: Reporting** → click **Mark Complete**
   - WO fires a `grc.workflow.completed` event with `final_decision=approved`
   - GRC consumer updates engagement status to `completed` ✓

> **⚠️ Important:** You must complete Step 3 above (click **Start Reporting** in WO) before attempting Phase 13 (Create Audit Report). The Audit Report create form only shows engagements in `reporting` or `completed` status.

---

## Phase 7a — Create Audit Memo (GAP 1 — SRS Req 10–14, 18)

**Page:** Sidebar → GRC → **Audit Memos** → Click **Create**

> **SRS:** CIA appoints Lead Auditor and prepares an engagement memo. It goes through CIA review → DG review → approval → transmission to Lead Auditor.
> **Model:** `AuditMemo` links to an **Audit Plan** + **Auditable Entity** (not an Engagement). The engagement is created *after* the memo is transmitted.
> **GAP 9:** After status reaches `approved`, the memo is stamped with QR code + approver signature via DRS. The `stamped_document_url` field is populated automatically.

| Field | Value |
|---|---|
| **Audit Plan** (`audit_plan_id`) | `RBIAP-2025-001` (select from SmartSelect — approved/implementation plans only) |
| **Auditable Entity** (`auditable_entity_id`) | `ICT Directorate (ICT-001)` |
| **Title** (`title`) | `Audit of ICT General Controls — Q3 FY 2025/2026` |
| **Purpose** (`purpose`) | `This memo appoints the Lead Auditor and audit team for the ICT General Controls Audit scheduled for Q3 FY 2025/2026. The audit scope covers access management, change management, backup and recovery, and network security controls. The team is instructed to proceed as per the approved audit plan RBIAP-2025-001 and report progress weekly.` |
| **Scope Summary** (`scope_summary`) | `ICT General Controls — access management, change management, backup and recovery, network security configuration.` |
| **Lead Auditor** (`lead_auditor`) | *(auto-filled from logged-in user UUID)* |
| **Audit Team** (`audit_team`) | `[]` *(optional JSON array — leave empty or add team member UUIDs)* |
| **Timeline Start** (`timeline_start`) | `2026-03-01` |
| **Timeline End** (`timeline_end`) | `2026-04-30` |

**Expected result:** Memo created with status `draft`.

### Status Workflow (5 stages — SRS Steps 10–14):

| Step | Action | Status | SRS Mapping |
|---|---|---|---|
| 1 | Created | `draft` | IA prepares memo |
| 2 | Click **Progress Update** → `cia_review` | `cia_review` | Submitted to CIA |
| 3 | Click **Progress Update** → `dg_review` | `dg_review` | CIA submits to DG |
| 4 | Click **Progress Update** → `approved` | `approved` | DG approves memo |
| 5 | Click **Progress Update** → `transmitted` | `transmitted` | CIA transmits to LA |

### ✅ GAP 9 Stamp Verification:
After status → `approved`:
1. Open the memo detail dialog (click **View**)
2. A **"Download Approved Memo"** button should appear (visible only when `stamped_document_url` is set)
3. This requires the memo to have a `document_id` (uploaded via DRS first)
4. Check GRC service logs for: `Stamp triggered for audit_memo {id}`

---

## Phase 7b — Declaration of Independence (GAP 2 — SRS Req 16, 18, 38)

**Page:** Sidebar → GRC → **Declarations** → Click **Create**

> **SRS:** Each audit team member must sign a Declaration of Independence before participating in an engagement.
> **How it works:** The create form auto-fills `declarant_name`, `declarant_role`, and `declarant_user_id` from the currently logged-in user (via auth context). The engagement dropdown shows all active engagements.
> **GAP 9:** After a declaration is signed, it is stamped with QR code + signature via DRS. The `stamped_document_url` field is populated automatically.

### Declaration 1 — No Conflict (Standard Case)

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **I am independent** toggle | `ON` (default — has_conflict = false) |
| **Conflict Details** | *(leave empty — only shown when toggle is OFF)* |
| **Declaration Text** | *(pre-filled default text — do not change)* |

**Expected result:** Declaration created with status `pending`, declarant_name auto-filled from auth.

### Declaration 2 — With Conflict (Edge Case Test)

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **I am independent** toggle | `OFF` → conflict_details field appears |
| **Conflict Details** | `I have a financial relationship with ICT Solutions Ltd, one of the vendors being reviewed in this engagement. I declare this conflict for CIA awareness and decision.` |

**Expected result:** Declaration created with `has_conflict = true`, conflict_details populated.

### Sign Declaration (SRS: "team member signs"):

1. Find Declaration 1 in the list → click **⋮** → **Sign**
2. Confirmation dialog: *"Are you sure you want to sign this declaration?"*
3. Confirm → `status: pending → signed`, `is_signed = true`, `signed_at` timestamp set

### ✅ List verification:
- `engagement_reference` column shows engagement ref number (e.g. `ENG-2025-001`)
- `declarant_name` column shows the logged-in user's name
- `has_conflict` badge: green `Independent` or red `Has Conflict`

### ✅ Detail dialog verification (click View):
- Shows `declarant_name`, `declarant_role`, `has_conflict` status
- Shows `conflict_details` section (only if has_conflict = true)
- Shows `signed_at` timestamp (only after signed)

### ✅ GAP 9 Stamp Verification:
After signing → open detail dialog → **"Download Signed Declaration"** button appears if `stamped_document_url` is populated.

---

## Phase 7c — Audit Survey / Fraud Risk Assessment (GAP 3 — SRS Req 19–21)

**Page:** Sidebar → GRC → **Audit Surveys** → Click **Create**

> **SRS:** LA conducts preliminary survey, assesses control environment, and evaluates fraud risk. The fraud risk assessment and control assessments inform the audit program design.
> **Model:** `AuditSurvey` is one-per-engagement (OneToOneField). There is no `title` or `survey_type` field.

| Field | Value |
|---|---|
| **Engagement** (`audit_engagement_id`) | `ICT General Controls Audit 2025/2026` |
| **Surveyed By** (`surveyed_by`) | *(auto-filled from logged-in user UUID)* |
| **Survey Date** (`survey_date`) | `2026-03-05` |
| **Process Description** (`process_description`) | `Preliminary survey covering the ICT General Controls environment. Processes assessed include user access management, IT change management, backup and disaster recovery, and network security configuration.` |
| **Control Environment Notes** (`control_environment_notes`) | `The ICT control environment shows moderate maturity. Formal policies exist for access management and change control but are inconsistently enforced. Management tone is supportive of audit activity.` |
| **Prior Audit History** (`prior_audit_history`) | `Last ICT audit conducted FY 2023/2024. Key findings were: excessive user privileges (partially remediated), incomplete change documentation (open), and backup restoration not tested (open). Prior recommendations 60% implemented.` |
| **Fraud Risk Assessment** (`fraud_risk_assessment`) | `Low-to-medium fraud risk identified. Primary risks relate to access management controls — terminated employees with active access could enable unauthorized system use. No direct evidence of fraud. Recommend extended access control testing.` |
| **Control Assessments** (`control_assessments`) | `[{"control": "Access Management", "adequacy": "inadequate", "notes": "No quarterly reviews performed"}, {"control": "Change Management", "adequacy": "partially adequate", "notes": "Process exists but inconsistently followed"}, {"control": "Backup & Recovery", "adequacy": "inadequate", "notes": "No recent restoration test"}]` |
| **Preliminary Findings** (`preliminary_findings`) | `Access review process not documented; 15 of 42 accounts had excessive privileges. Change management bypassed for emergency changes. Backup restoration last tested 18 months ago.` |

**Expected result:** Survey created with status `draft`.

### Status Workflow:

> **⚠️ Model note:** Only 2 statuses exist: `draft` and `completed`. There is no `active` or `closed` state.

| Step | Action | Status |
|---|---|---|
| 1 | Created | `draft` |
| 2 | Click **Progress Update** → `completed` | `completed` — survey finalized |

---

## Phase 7d — Risk Control Matrix (GAP 4 — SRS Req 22)

**Page:** Sidebar → GRC → **Risk Control Matrix** → Click **Create**

> **SRS:** LA develops an RCM documenting all identified risks, associated controls, control design adequacy, and planned test approach for each control.

### Step 1: Create the RCM Header

> **⚠️ Model note:** `RiskControlMatrix` has no `title` or `description` field. The create form only needs the engagement.

| Field | Value |
|---|---|
| **Engagement** (`audit_engagement_id`) | `ICT General Controls Audit 2025/2026` |
| **Prepared By** (`prepared_by`) | *(auto-filled from logged-in user UUID)* |

**Expected:** RCM created with status `draft`.

### Step 2: Add RCM Entries

> **Navigation:** Open the RCM detail → click **Add Entry** to add each row.

#### RCM Entry 1: Access Management

| Field | Value |
|---|---|
| **Process Area** (`process_area`) | `User Access Management` |
| **Risk Description** (`risk_description`) | `Unauthorized access due to inadequate access review controls — terminated employees may retain active system access, enabling unauthorized system use or data exfiltration.` |
| **Risk Rating** (`risk_rating_id`) | `High Risk` (select from configured Risk Ratings) |
| **Control Description** (`control_description`) | `Quarterly user access reviews to ensure least-privilege access` |
| **Control Owner** (`control_owner`) | `ICT Director` |
| **Control Type** (`control_type`) | `preventive` |
| **In Scope** (`in_scope`) | `Yes` (toggle ON) |
| **Design Adequate** (`design_adequate`) | `No` (toggle OFF — control exists but design is flawed) |
| **Design Assessment Notes** (`design_assessment_notes`) | `Access review process is not formally documented. No evidence of execution in the last 12 months. 15 of 42 sampled accounts had excessive privileges.` |
| **Test Approach** (`test_approach`) | `walkthrough` |
| **Priority** (`priority`) | `high` |

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
| **Test Approach** (`test_approach`) | `substantive` |
| **Priority** (`priority`) | `medium` |

### Step 3: Submit RCM for Approval

| Step | Action | Status | SRS Mapping |
|---|---|---|---|
| 1 | Created | `draft` | LA develops RCM |
| 2 | Click **Progress Update** → `submitted` | `submitted` | Submitted to CIA |
| 3 | Click **Progress Update** → `approved` | `approved` | CIA approves RCM |

---

## Phase 7e — Audit Program (GAP 5 — SRS Req 22–23)

**Page:** Sidebar → GRC → **Audit Programs** → Click **Create**

> **SRS:** LA prepares the draft audit program based on the RCM. CIA reviews and approves the program before fieldwork begins.
> **GAP 9:** After status reaches `approved`, the program is stamped with QR code + approver signature via DRS.

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **Title** | `ICT General Controls Audit Program — Q3 2025/2026` |
| **Objectives** (`objectives`) | `["Assess adequacy of user access management controls", "Evaluate change management documentation and approval processes", "Verify backup and disaster recovery procedures", "Review network security configuration and monitoring"]` |
| **Procedures** (`procedures`) | `ICT General Controls for the period January to March 2026. Procedures cover: (1) user access controls — inspect access review records for 42 sampled accounts; (2) change management — substantive testing of 12 sampled production changes; (3) backup verification — review restoration test records and procedures; (4) network security — walkthrough of firewall configuration and monitoring logs.` |

**Expected result:** Program created with status `draft`.

### Status Workflow (SRS Steps 22–23):

> **⚠️ Model note:** Status is `draft → under_review → approved`. There is no `submitted` status.

| Step | Action | Status | SRS Mapping |
|---|---|---|---|
| 1 | Created | `draft` | LA prepares draft program |
| 2 | Click **Progress Update** → `under_review` | `under_review` | Submitted to CIA for review |
| 3 | Click **Progress Update** → `approved` | `approved` | CIA approves audit program |

### ✅ GAP 9 Stamp Verification:
After status → `approved`:
1. Open program detail dialog (click **View**)
2. A **"Download Approved Program"** button should appear
3. Check GRC service logs for: `Stamp triggered for audit_program {id}`

---

## Phase 8 — Create Working Papers

**Page:** Sidebar → **Audit Engagements** → find your engagement row → click the **⋮ (three-dot) action menu** on the right → select **"View"** (Eye icon) → this opens the **Engagement Detail page** → scroll down to the **Working Papers** section → click **Add Working Paper**

> **⚠️ Navigation note:** Working Papers do NOT have their own sidebar entry. They are embedded inside the Audit Engagement **Detail** page. You must "View" an engagement first to see and manage its working papers.

### Working Paper 1

| Field | Value |
|---|---|
| **Title** | `ICT Access Control Assessment` |
| **Reference Number** | `WP-001` |
| **Paper Type** | `fieldwork` |
| **File Upload** | *(optional — drag or click to attach a document, max 25MB)* |

### Working Paper 2

| Field | Value |
|---|---|
| **Title** | `Change Management Procedures Review` |
| **Reference Number** | `WP-002` |
| **Paper Type** | `fieldwork` |

### Working Paper Approval (per paper):

1. Click on the working paper → detail page at `/service/grc/working-papers/{id}`
2. Click **Submit for Review**
3. **Stage 1 — LA Review:** Approve
4. **Stage 2 — CIA Approval:** Approve
5. Review status → `approved`

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

**Expected:** 2 findings created with status `draft`. Progress them: `draft` → `discussed` → `final`.

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

**Expected:** 2 recommendations created with status `open`. Progress them: `open` → `in_progress` → `implemented` → `verified` → `closed`.

---

## Phase 11 — Audit Monitoring

**Page:** Sidebar → **Audit Monitoring** → Click **Create**

| Field | Value |
|---|---|
| **Recommendation** | `REC-2025-001 (Implement Automated User Access Review)` |
| **Implementation Progress** | `25` (percentage) |
| **Progress Notes** | `Q3 2026 review: Vendor selected for access review tool. RFP issued and evaluation completed. HR-IT integration requirements documented. Implementation timeline on track.` |
| **Next Review Date** | `2026-06-30` |

**Expected:** Monitoring record created. Update progress over time as implementation advances.

### ✅ GAP 7 — 5-Day Deadline Enforcement Verification:
When creating or editing a monitoring record, verify the backend enforces the 5-day review window:
1. Set `next_review_date` to a date in the past (more than 5 days ago)
2. The backend should raise a validation error: *"Next review date must be at least 5 days from today"* (or similar)
3. Set `next_review_date` to today + 4 days → should also fail
4. Set `next_review_date` to today + 5 days → should succeed
5. This enforcement applies to both create and update operations (GAP 7 backend constraint in `AuditMonitoringSerializer`)

---

## Phase 12 — Dashboard Verification

**Page:** Click **GRC** in the sidebar header (navigate to `/service/grc`)

**Verify:**
- All module cards are present and show correct counts
- Clicking each card navigates to the correct list page
- The sidebar shows **10 Internal Audit items** (no Auditable Entities, no Working Papers list)

---

## Phase 13 — Create Audit Report

**Page:** Sidebar → GRC → **Audit Reports** → Click **Create**

> **Pre-conditions:**
> 1. The audit engagement must be in `reporting` status — see Phase 7 Step 3 (click **Start Reporting** in the WO Workflow Console)
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
| 2 | Click **Progress Update** → select `under_review` | CIA reviews the draft |
| 3 | Click **Progress Update** → select `approved` | Report approved |
| 4 | Click **Progress Update** → select `distributed` | Report distributed to auditee |

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

> Audit meetings track the formal discussions between the audit team and the auditee. Three key meetings are required by the SRS process flow: **Entry Conference** (Step 14), **Pre-Exit Conference** (Step 17), and **Exit Conference** (Step 24).
>
> Per SRS Requirement 13: *"The system shall capture attendance and minutes."*
> Documents (minutes file, attendance sheet) are uploaded to the **Document Records Service** — the same pattern used by Working Papers.

### Meeting 1: Entry Conference

#### Step A — Create (Scheduled)

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **Meeting Type** | `Entry Conference` |
| **Meeting Title** | `ICT Audit Entry Conference — March 2026` |
| **Scheduled Date** | `2026-03-01` |
| **Scheduled Time** | `09:00` |
| **Location** | `ICT Directorate Board Room, HQ Building, 3rd Floor` |
| **Agenda** | `1. Introduction of audit team members and scope of the engagement\n2. Presentation of audit objectives and methodology\n3. Overview of key risk areas identified during planning\n4. Discussion of audit timeline and key milestones\n5. Logistics: document requests, staff availability, access requirements\n6. Questions from ICT Directorate management` |

**Expected result:** Meeting created with status `scheduled`.

#### Step B — Progress to In Progress
Click **Progress Update** → select `in_progress`.

> **⚠️ Once in-progress, the structural fields (Engagement, Type, Title, Date, Location, Agenda) are LOCKED.** Only post-meeting fields are editable: Minutes, Key Discussions, Attendees, and document uploads.

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

### Meeting 2: Exit Conference

#### Step A — Create (Scheduled)

| Field | Value |
|---|---|
| **Engagement** | `ICT General Controls Audit 2025/2026` |
| **Meeting Type** | `Exit Conference` |
| **Meeting Title** | `ICT Audit Exit Conference — April 2026` |
| **Scheduled Date** | `2026-04-25` |
| **Scheduled Time** | `14:00` |
| **Location** | `ICT Directorate Board Room, HQ Building, 3rd Floor` |
| **Agenda** | `1. Presentation of draft audit findings and recommendations\n2. ICT Directorate management response to each finding\n3. Discussion of agreed action plans and target dates\n4. Confirmation of responsible parties for each recommendation\n5. Next steps: report finalization and distribution timeline` |

**Expected result:** Second meeting created with status `scheduled`.

#### Steps B–D — Same post-meeting flow as Meeting 1
Progress → `in_progress` → Edit (add minutes, attendees, key discussions, upload docs) → Progress → `completed`.

---

### Full Status Workflow:

| Step | Action | Edit Fields Available | Result |
|---|---|---|---|
| 1 | **Create** | Engagement, Type, Title, Date, Time, Location, Agenda | `scheduled` |
| 2 | **Progress Update** → `in_progress` | — | `in_progress` |
| 3 | **Edit** (⋮ menu) | Minutes, Key Discussions, Attendees, Minutes Doc, Attendance Sheet | Post-meeting data saved |
| 4 | **Progress Update** → `completed` | — | `completed` (requires minutes) |

> **⚠️ Backend validation:** Minutes field must be non-empty before `completed` is allowed (`MINUTES_REQUIRED` error otherwise).
> **⚠️ Document uploads** go to the Document Records Service and return a UUID stored as `minutes_document_id` / `attendance_document_id` on the meeting record.

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
2. While in `draft` status and not yet consolidated, a **Consolidate** button appears
3. Click **Consolidate** — the system pulls findings/recommendations summaries from the Q3 engagements
4. `is_consolidated` badge changes to **Yes**
5. `findings_summary` and `recommendations_summary` are auto-populated from real data

### Status Workflow for Quarterly Reports:

| Step | Action | Result |
|---|---|---|
| 1 | Create → status `draft` | Report in draft |
| 2 | *(Optional)* Click **Consolidate** | Auto-fills summary data |
| 3 | Click **Progress Update** → `cia_review` | CIA reviews the quarterly report |
| 4 | Click **Progress Update** → `management_review` | Management reviews |
| 5 | Click **Progress Update** → `committee_review` | Audit Committee reviews |
| 6a | Click **Progress Update** → `improvement_required` | If revisions needed (returns for rework) |
| 6b | Click **Progress Update** → `approved` | Committee approves |
| 7 | Click **Progress Update** → `submitted_to_commission` | Submitted to Commission for noting |

---

## Status Progression Quick Reference

| Entity | Status Flow |
|---|---|
| **Audit Universe** | `draft` → `under_review` → `approved` |
| **Risk Assessment** | `draft` → `submitted` → `reviewed` → `approved` |
| **Audit Memo** | `draft` → `cia_review` → `dg_review` → `approved` → `transmitted` |
| **Declaration** | `pending` → `signed` |
| **Audit Survey** | `draft` → `active` → `closed` |
| **Risk Control Matrix** | `draft` → `submitted` → `approved` |
| **Audit Program** | `draft` → `submitted` → `approved` |
| **Audit Plan** | `draft` → `cia_review` → `management_review` → `committee_review` → `approved` |
| **Audit Engagement** | `planning` → `fieldwork` → `reporting` → `completed` |
| **Working Paper** | `draft` → `pending` → `approved` |
| **Audit Finding** | `draft` → `discussed` → `final` |
| **Audit Recommendation** | `open` → `in_progress` → `implemented` → `verified` → `closed` |
| **Audit Report** | `draft` → `under_review` → `approved` → `distributed` |
| **Audit Meeting** | `scheduled` → `in_progress` → `completed` *(or `cancelled`)* |
| **Quarterly Report** | `draft` → `cia_review` → `management_review` → `committee_review` → `approved` → `submitted_to_commission` |

---

## Execution Order (34 Steps)

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
 9.  GRC → Audit Engagements → Create ENG-2025-001 (ICT audit, type=planned)
10.  Engagement Detail → Start Engagement Workflow
11.  GRC → Audit Memos → Create memo for ENG-2025-001 → Progress: draft → cia_review → dg_review → approved → transmitted (GAP 1)
11a. Audit Memo → Verify GAP 9 stamp: stamped_document_url populated after approved
12.  GRC → Declarations → Create Declaration 1 (no conflict) → Sign it (GAP 2)
12a. GRC → Declarations → Create Declaration 2 (with conflict) for edge case
12b. Declaration → Verify GAP 9 stamp: stamped_document_url populated after signed
13.  GRC → Audit Surveys → Create preliminary survey for ENG-2025-001 → Progress: draft → active → closed (GAP 3)
14.  GRC → Risk Control Matrix → Create RCM → Add 2 RCM Entries → Progress: draft → submitted → approved (GAP 4)
15.  GRC → Audit Programs → Create program → Progress: draft → submitted → approved (GAP 5)
15a. Audit Program → Verify GAP 9 stamp: stamped_document_url populated after approved
16.  GRC → Meetings → Create Entry Conference meeting (scheduled → in_progress → completed)
17.  Engagement Detail → Add 2 Working Papers (WP-001, WP-002)
18.  Working Paper Detail → Submit → Approve through 2-stage workflow
19.  GRC → Audit Findings → Create FND-2025-001 (Access Controls)
20.  GRC → Audit Findings → Create FND-2025-002 (Change Management)
21.  Progress findings: draft → discussed → final
22.  GRC → Meetings → Create Exit Conference meeting (scheduled → completed)
23.  GRC → Audit Recommendations → Create REC-2025-001
24.  GRC → Audit Recommendations → Create REC-2025-002
25.  Progress recommendations: open → in_progress
26.  Workflow Console → Start Reporting (engagement → reporting status)
27.  GRC → Audit Reports → Create draft audit report
28.  Audit Report → Progress: draft → under_review → approved (check GAP 12 logs) → distributed
28a. Audit Report → Verify GAP 9 stamp + verify GAP 12 finding.finalized Kafka events in logs
29.  GRC → Audit Monitoring → Create monitoring for REC-2025-001
29a. Monitoring → Test GAP 7 deadline: next_review_date < today+5 days should fail validation
30.  GRC → Quarterly Reports → Create Q3 2025/2026 quarterly report
31.  Quarterly Report → Click Consolidate (auto-populate summary from real data)
32.  Quarterly Report → Progress: draft → cia_review → management_review → committee_review → approved → submitted_to_commission
33.  GRC → Dashboard → Verify all cards and navigation
34.  Review GRC service logs for any GAP-related errors or warnings
```

> **Estimated time:** 60–90 minutes for full end-to-end flow
