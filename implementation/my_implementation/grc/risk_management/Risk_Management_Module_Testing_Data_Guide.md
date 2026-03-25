# Risk Management & Quality Assurance Module — End-to-End Testing Data Guide

> **Date:** 2026-03-24
> **Base URL:** `http://localhost:3001` (Staff Portal)
> **GRC API Base:** `http://localhost:8006/api/v1/grc/`
> **Database:** Cleaned — all transactional data wiped, lookup data preserved

---

## 1. Overview

### Purpose
This guide provides step-by-step browser-based testing flows for the **Risk Management and Quality Assurance (RMQA) Module** of the FIMS GRC Service. It covers all major user roles, workflows, status transitions, approval chains, and edge cases as defined in the SRS (`FCC_SBP_RMQA_01` through `FCC_SBP_RMQA_07`).

### Scope

| Module Area | SRS Reference | Frontend Path |
|---|---|---|
| Risk Champion Appointment | FCC_SBP_RMQA_01 | `/service/grc/risk-champions` |
| Risk Assessment Sheets | FCC_SBP_RMQA_03 | `/service/grc/risk-assessment-sheets` |
| Departmental Risk Register | FCC_SBP_RMQA_03 | `/service/grc/departmental-risks` |
| Institutional Risk Register | FCC_SBP_RMQA_04 | `/service/grc/institutional-risks` |
| Risk Treatment Action Plan (RTAP) | FCC_SBP_RMQA_05 | `/service/grc/risk-treatment` |
| Quarterly Performance Report (QPR) | FCC_SBP_RMQA_05 | `/service/grc/risk-performance-reports` |
| Risk Meetings & Workshops | FCC_SBP_RMQA_03 / 04 | `/service/grc/risk-meetings` |
| Risk Surveys | SRS §4.11.1.1 req 3 | `/service/grc/risk-surveys` |
| Risk Knowledge Base | SRS §4.11.1.1 req 4 | `/service/grc/risk-knowledge-base` |
| Quality Auditor Appointment | FCC_SBP_RMQA_06 | `/service/grc/quality-auditors` |
| QA Training Sessions | FCC_SBP_RMQA_06 | `/service/grc/qa-training` |
| QMS Audit Programme | FCC_SBP_RMQA_07 | `/service/grc/qms-programs` |
| QMS Audit Plan | FCC_SBP_RMQA_07 | `/service/grc/qms-plans` |
| QMS Audit Checklists | FCC_SBP_RMQA_07 | `/service/grc/qms-checklists` |
| QMS Audit Reports | FCC_SBP_RMQA_07 | `/service/grc/qms-plans` (Reports tab) |
| Non-Conformances | FCC_SBP_RMQA_07 | `/service/grc/non-conformances` |
| Risk Dashboard | SRS §4.11.1.1 | `/service/grc/risk-dashboard` |

---

## 2. Test Users

> **Password for all test users:** `Pass@1234`
> **DG user already exists from Internal Audit setup** — password: `Pass@1234`

| Email | Name | Role | SRS Actor |
|---|---|---|---|
| `rmqam@fcc.go.tz` | Sarah Mwalimu | Risk Management & QA Manager (RMQAM) | RMQAM — approves everything |
| `rmo@fcc.go.tz` | Peter Kileo | Risk Management Officer (RMO) | RMO — drafts, submits workflows |
| `riskchampion@fcc.go.tz` | Anna Mushi | Risk Champion (RC) | RC — conducts risk assessments, manages dept registers |
| `qualityauditor@fcc.go.tz` | Frank Lupembe | Quality Auditor (QA) | QA — conducts QMS audits |
| `lsm@fcc.go.tz` | Hawa Kondo | Legal Service Manager (LSM) | LSM — approves IRR, RTAP, QPR before committee |
| `dg@fcc.go.tz` | Director General | Director General | DG — signs appointments, approves IRR/QPR finality |

### Role Permission Summary

| Role | Key Permissions |
|---|---|
| RMQAM | Full manage/approve on: champions, RAS, DRR, IRR, RTAP, QPR, QA training, QMS programs, plans, reports, NCs |
| RMO | Full manage (no approve) on most items; can submit workflows |
| Risk Champion | Conduct RAS, manage DRR, respond to RTAP items, manage/view meetings |
| Quality Auditor | Manage QMS checklists, audit reports, non-conformances; view meetings |
| LSM | Approve IRR, RTAP, QPR at Committee stage |
| DG | Sign RC/QA appointments; approve IRR/QPR at final stage |

---

## 3. Sample Data

### §3.1 Fiscal Year (Pre-Seeded — use as-is)

| Name | Period |
|---|---|
| Fiscal Year 2025/2026 | 2025-07-01 → 2026-06-30 |

### §3.2 Risk Configuration Lookups (Pre-Seeded)

Verify these exist under **GRC → Configuration** before testing:

| Lookup Type | Expected Values |
|---|---|
| Risk Categories | Operational, Financial, Strategic, Compliance, Reputational, IT/Technology |
| Risk Likelihoods | Rare (1), Unlikely (2), Possible (3), Likely (4), Almost Certain (5) |
| Risk Impacts | Negligible (1), Minor (2), Moderate (3), Major (4), Critical (5) |
| Risk Levels | Low, Medium, High, Very High |
| Risk Sectors | Telecommunications, Media, Broadcasting, Postal Services |
| Non-Conformance Types | Major NC, Minor NC, Observation, Area for Improvement |
| ISO Clauses | Clause 4 to Clause 10 (ISO 9001:2015) |
| Strategic Objectives | Promote competition, Protect consumers (from seed command) |

> **If lookups are missing**, run: `docker compose exec grc-service python manage.py seed_risk_lookups`

### §3.3 Risk Champion Sample Record

| Field | Value |
|---|---|
| Nominee | Anna Mushi (`riskchampion@fcc.go.tz`) |
| Directorate / Unit | Operations Directorate |
| Org Unit Type | `directorate` |
| Term Start | 2026-01-01 |
| Term End | 2029-01-01 |
| Justification | Experienced officer with thorough knowledge of operational risks; proposed by Director of Operations |

### §3.4 RC Appointment Letter

| Field | Value |
|---|---|
| Appointment Reference | RC-APPT-2026-001 |
| Effective Date | 2026-01-15 |
| Letter Content | "You are hereby appointed as Risk Champion for the Operations Directorate effective 15 January 2026 for a period of three (3) years." |

### §3.5 Risk Assessment Sheet

| Field | Value |
|---|---|
| Title | Operations Directorate Risk Assessment Sheet — Q3 FY2025/2026 |
| Department / Org Unit | Operations Directorate |
| Period | Q3 (Jan 2026 – Mar 2026) |
| Fiscal Year | FY 2025/2026 |

**Risk Entries (one RAS record per risk — each is created separately):**

> **Important:** Each risk is a *separate* `RiskAssessmentSheet` record. The table below lists the 4 individual RAS records to create. Create each using "New Risk Assessment Sheet"; the DRR (Flow 9) will link these approved records.

| # | Risk Title | Category | Likelihood | Impact | Existing Controls | Risk Owner | Inherent Level | Residual Level | Causes | Consequences | Risk Indicator | Strategic Objective | Risk Sector |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | IT systems downtime disrupts complaint processing | IT/Technology | Likely (4) | Major (4) | Backup servers, UPS systems | IT Manager | High | Medium | Aging server infrastructure; single UPS point of failure | Complaint processing halted; SLA breaches; regulatory penalties | Number of unplanned outages per quarter | Protect consumers | Telecommunications |
| 2 | Unauthorised access to consumer complaint records | IT/Technology | Possible (3) | Critical (5) | Firewall, access control policy | IT Security Officer | Very High | High | Weak access-control policies; no MFA; insufficient audit logging | Data breach; loss of public trust; regulatory sanction | Number of unauthorised access attempts detected | Protect consumers | Telecommunications |
| 3 | High staff turnover reduces institutional knowledge | Operational | Likely (4) | Moderate (3) | Succession planning programme | HR Manager | High | Medium | Unattractive remuneration; limited career advancement | Knowledge gaps in critical functions; project delays | Staff turnover rate per directorate per year | Promote competition | Telecommunications |
| 4 | Non-compliance with FCA 2003 data protection provisions | Compliance | Unlikely (2) | Major (4) | Legal compliance reviews, staff training | Legal Officer | Medium | Low | Insufficient data-handling training; outdated SOP | Regulatory investigation; fines; reputational damage | Number of data-handling complaints received | Protect consumers | Postal Services |

> **Tip:** `Strategic Objective` and `Risk Sector` are FK dropdowns populated from Configuration lookups. Confirm these values are seeded (§3.2) before creating RAS records.

### §3.6 Departmental Risk Register

| Field | Value |
|---|---|
| Title | Operations Directorate Risk Register — FY 2025/2026 |
| Org Unit Type | `directorate` |
| Org Unit ID | Operations Directorate |
| Fiscal Year | FY 2025/2026 |
| Prepared By | Anna Mushi (RC) |

**DRR Entries** (same rows as RAS entries above, with treatment notes added)

### §3.7 Institutional Risk Register

| Field | Value |
|---|---|
| Title | FCC Institutional Risk Register — FY 2025/2026 |
| Fiscal Year | FY 2025/2026 |
| Workshop Date | 2026-02-15 |
| Workshop Venue | FCC Boardroom, Sam Nujoma Road, Dar es Salaam |
| Committee Meeting Date | 2026-04-01 |
| LSM Submission Date | 2026-03-25 |

**IRR Entries (risks exceeding institutional risk appetite):**

| # | Risk Description | Source Directorate | Risk Owner | Proposed Control | Implementation Deadline |
|---|---|---|---|---|---|
| 1 | Unauthorised access to consumer complaint records | Operations | IT Security Officer | Deploy MFA on all systems, enhanced audit logging | 2026-06-30 |
| 2 | Regulatory enforcement gaps due to staff shortages | Legal | Director of Legal | Recruit 3 enforcement officers; cross-train existing staff | 2026-09-30 |
| 3 | Budget underfunding of enforcement operations | Finance | Director General | Submit supplementary budget request to MoF | 2026-05-31 |

### §3.8 Risk Treatment Action Plan (RTAP)

| Field | Value |
|---|---|
| Title | Risk Treatment Action Plan — FY 2025/2026 |
| Fiscal Year | FY 2025/2026 |
| Overall Progress | 0% (initial) |

**RTAP Items:**

| # | Risk Description | Control Action | Responsible (RC) | Priority | Status | Target Date |
|---|---|---|---|---|---|---|
| 1 | Unauthorised access to records | Deploy MFA and enhanced logging | Anna Mushi | High | Not Started | 2026-06-30 |
| 2 | Enforcement staff shortages | Submit recruitment request to HR | Anna Mushi | Medium | Not Started | 2026-05-31 |
| 3 | Budget underfunding | Draft supplementary budget memo | Anna Mushi | High | Not Started | 2026-04-30 |

### §3.9 Quarterly Performance Report

| Field | Value |
|---|---|
| Title | Quarterly Risk Management Performance Report — Q3 FY 2025/2026 |
| Fiscal Year | FY 2025/2026 |
| Reporting Quarter | Q3 (Jan – Mar 2026) |
| Reporting Period | 2026-01-01 → 2026-03-31 |
| Executive Summary | Overall risk control implementation rate stands at 33% for Q3 2025/2026, an improvement of 10% over Q2. Three controls remain in progress pending budget allocation. |
| Management Review Date | 2026-03-20 |
| Committee Meeting Date | 2026-04-05 |
| IAGO Reference | IAGO/RPT/2026/Q3/001 |
| IAGO Submission Date | 2026-04-30 |

> **IAGO submission:** After the QPR is approved, the RMQAM must mark it as submitted to the Internal Auditor General Office (IAGO). The fields `iago_submitted`, `iago_submission_date`, and `iago_reference` are required. See Flow 22b.

### §3.10 Risk Meeting

| Field | Value |
|---|---|
| Title | Operations Directorate Risk Brainstorming Session |
| Meeting Type | `brainstorming` |
| Meeting Date | 2026-02-10 10:00 AM |
| Venue | FCC Conference Room B |
| Agenda | Review and update risk register for Q3; identify emerging risks |
| Fiscal Year | FY 2025/2026 |

### §3.11 Risk Survey

| Field | Value |
|---|---|
| Title | Staff Risk Awareness Survey — Q3 2026 |
| Description | Quarterly survey to assess staff understanding of the risk management framework and their awareness of key departmental risks |
| Target Respondents | All Operations Directorate staff |
| Status | `draft` → `open` |

**Survey Questions:**

| # | Question | Type |
|---|---|---|
| 1 | How familiar are you with the FCC Risk Management Framework? | `rating` |
| 2 | Have you identified any new risks in your area of work this quarter? | `yes_no` |
| 3 | Please describe the most significant risk you are aware of in your directorate. | `text` |

### §3.12 Risk Knowledge Base Entry

| Field | Value |
|---|---|
| Title | IT System Downtime — Lessons Learned |
| Source Type | `lesson_learned` |
| Content | During Q2 2025/2026, IT system downtime impacted complaint processing for 8 hours. Root cause was a failed UPS. Mitigation: redundant UPS systems procured and tested. |
| Date | 2026-01-15 |

> **Source Type choices** (exact values): `lesson_learned` · `audit_finding` · `industry_best_practice` · `external_report`

### §3.13 Quality Auditor Sample Record

| Field | Value |
|---|---|
| Nominee | Frank Lupembe (`qualityauditor@fcc.go.tz`) |
| Org Unit Type | `directorate` |
| Directorate / Unit | Risk Management Unit |
| Qualifications | ISO 9001:2015 Lead Auditor Certificate (TBS, Dec 2025) |
| Experience Summary | 4 years internal quality audit experience; participated in 3 ISO certification audits |

### §3.14 QA Appointment Letter

| Field | Value |
|---|---|
| Appointment Reference | QA-APPT-2026-001 |
| Effective Date | 2026-01-20 |
| Letter Content | "You are hereby appointed as Quality Auditor/Champion for the Risk Management Unit effective 20 January 2026 for a period of three (3) years. You are expected to conduct QMS audits for all processes excluding those under your directorate." |

### §3.15 QA Training Session

| Field | Value |
|---|---|
| Title | ISO 9001:2015 QMS Audit Examination — Batch 1 |
| Training Date | 2026-01-10 |
| Venue | FCC Training Room, Dar es Salaam |
| Trainer | TBS Certified Trainer (Mr. James Mwita) |
| Trainer Organisation | Tanzania Bureau of Standards (TBS) |
| Pass Threshold | 75% |

> **`approval_status` choices** (exact values): `proposed` · `approved` · `completed` · `cancelled` — there is no `rejected` status.

### §3.16 QMS Audit Programme

| Field | Value |
|---|---|
| Title | FCC QMS Audit Programme — FY 2025/2026 |
| Fiscal Year | FY 2025/2026 |
| Audit Scope | All QMS processes except those under Risk Management Unit |
| Objectives | Verify conformity with ISO 9001:2015 requirements; identify non-conformances and areas for improvement |
| Assigned QAs | Frank Lupembe (Quality Auditor, Team Leader) |

### §3.17 QMS Audit Plan

| Field | Value |
|---|---|
| Title | Customer Complaints Management Process Audit |
| Audit Start Date | 2026-03-10 |
| Audit End Date | 2026-03-14 |
| Notification Date | 2026-02-28 |
| Audit Scope | Customer complaints handling process from receipt to resolution |
| Auditee | Consumer Affairs Directorate |
| Team Leader | Frank Lupembe |
| ISO Clauses | Clause 8.2 — Customer-related processes, Clause 9.1 — Monitoring/measurement |

> **`notification_date` constraint (Rule E.7):** Must be ≥ 10 working days before `audit_start_date`. 2026-02-28 → 2026-03-10 = 10 days — valid. Testing the violation: enter `2026-03-05` (< 10 days) → expect a `ValidationError`.

**Team Assignments:**

| Auditor | Role |
|---|---|
| Frank Lupembe | Team Leader |

**Timetable Entries:**

| Date | Time | Process | Auditee | Auditor |
|---|---|---|---|---|
| 2026-03-10 | 09:00–10:00 | Entry Meeting | Consumer Affairs Director | Frank Lupembe |
| 2026-03-10 | 10:00–12:00 | Document Review | Consumer Affairs Records Officer | Frank Lupembe |
| 2026-03-11 | 09:00–11:00 | Customer Complaints Register Review | Complaints Manager | Frank Lupembe |
| 2026-03-14 | 10:00–11:00 | Exit Meeting | Consumer Affairs Director | Frank Lupembe |

### §3.18 QMS Audit Checklist Entries

| # | Process Area | ISO Clause | Checklist Question | Conformity |
|---|---|---|---|---|
| 1 | Customer Complaints Register | 8.2.1 | Is a customer complaints register maintained and updated? | `conforming` |
| 2 | Complaint Resolution Timeline | 8.2.2 | Are complaint resolution timelines documented and tracked? | `minor_nc` |
| 3 | Customer Feedback Analysis | 9.1.2 | Is customer feedback analysed and used to drive improvement? | `major_nc` |
| 4 | Management Review of Complaints | 9.3 | Are complaint trends reviewed at Management Review Meetings? | `observation` |

### §3.19 QMS Audit Report

| Field | Value |
|---|---|
| Report Title | QMS Audit Report — Customer Complaints Management Process |
| Audit Period | 2026-03-10 → 2026-03-14 |
| Summary | Two NCs identified: complaint resolution timelines not documented (Minor NC) and customer feedback not analysed for improvement (Major NC). Corrective actions required within 30 days. |

### §3.20 Non-Conformances

**NC 1 (Minor):**

| Field | Value |
|---|---|
| NC Type | Minor NC |
| ISO Clause | Clause 8.2.2 |
| Description | Complaint resolution timelines are not documented in the Consumer Affairs Standard Operating Procedure, violating ISO 9001:2015 Clause 8.2.2. |
| Objective Evidence | Consumer Affairs SOP reviewed; Section 4.2 (Complaint Handling) contains no defined timelines or escalation periods. Staff confirmed timelines are managed informally. |
| Corrective Action Required | Update SOP to include defined complaint resolution timelines; train all Consumer Affairs staff |
| Due Date | 2026-04-14 |

**NC 2 (Major):**

| Field | Value |
|---|---|
| NC Type | Major NC |
| ISO Clause | Clause 9.1.2 |
| Description | Customer feedback data is not systematically analysed to identify trends and drive improvement activities, violating ISO 9001:2015 Clause 9.1.2. |
| Objective Evidence | Customer feedback forms reviewed; no documented analysis procedure found. Department head confirmed feedback is discussed verbally but no records maintained. |
| Corrective Action Required | Develop customer feedback analysis procedure; implement quarterly reporting to management |
| Due Date | 2026-04-14 |

> **Note:** `iso_clause` and `objective_evidence` are **required** fields on the `NonConformance` model. A save attempt without them will fail validation.

---

## 4. Test Flows

---

### Part A — Risk Champion Appointment

---

#### Flow 1: Register a Risk Champion (RMQAM)

> Register a user in the system as a Risk Champion before initiating their formal appointment process.

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-champions`
3. Click **"New Risk Champion"** (or **"Add Champion"**)
4. Enter data (from §3.3):
   - **Nominee User:** Select `Anna Mushi (riskchampion@fcc.go.tz)` from the user lookup
   - **Org Unit Type:** `Directorate`
   - **Directorate / Unit:** `Operations Directorate`
   - **Term Start:** `2026-01-01`
   - **Term End:** `2029-01-01`
   - **Justification:** `Experienced officer with thorough knowledge of operational risks; proposed by Director of Operations`
5. Click **Save**

**Expected Result:**
- Risk Champion record created with status `Active`
- Anna Mushi appears in the Risk Champions list with her directorate
- Record shows term dates and org unit

---

#### Flow 2: Create RC Appointment Letter and Process Workflow (RMO → RMQAM → DG → Dispatch)

> After registering the champion, the formal DG-signed appointment letter is drafted and processed through the appointment workflow.

**Precondition:** Risk Champion from Flow 1 exists.

**Step 2a — RMO Drafts Appointment Letter:**

**User:** RMO (`rmo@fcc.go.tz`)

1. Log in as `rmo@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-champions`
3. Open the risk champion record for Anna Mushi
4. Click **"Appointments"** tab → **"New Appointment Letter"**
5. Enter data (from §3.4):
   - **Reference:** `RC-APPT-2026-001`
   - **Effective Date:** `2026-01-15`
   - **Letter Content:** `You are hereby appointed as Risk Champion for the Operations Directorate effective 15 January 2026 for a period of three (3) years.`
6. Click **Save** — status: `DRAFT`
7. Click **"Submit for Review"** (start WO workflow) — status: `DRAFT → SUBMITTED`

**Expected Result:** Appointment letter created in `Draft` status; after submit: `Submitted`

**Step 2b — RMQAM Reviews and Approves:**

**User:** RMQAM (`rmqam@fcc.go.tz`)

8. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
9. Navigate to the champion appointment record
10. Click **"Advance Workflow"** to approve at the RMQAM stage
11. Verify status advances toward DG approval stage

**Expected Result:** Workflow advances; RMQAM review complete

**Step 2c — DG Signs the Appointment Letter:**

**User:** DG (`dg@fcc.go.tz`)

12. Log in as `dg@fcc.go.tz` / `Pass@1234`
13. Navigate to the appointment letter (via Workflow tasks or direct link)
14. Click **"Advance Workflow"** to approve (DG signature stage) — status: `→ SIGNED`

**Expected Result:** Appointment status: `Signed`; `dispatched = false`

**Step 2d — Mark as Dispatched (RMO):**

**User:** RMO (`rmo@fcc.go.tz`)

15. Log in as `rmo@fcc.go.tz` / `Pass@1234`
16. Open the signed appointment letter
17. Fill in dispatch fields:
    - **Dispatch Reference:** `REG-2026-RC-001`
    - **Dispatch Date:** `2026-01-16`
18. Check **"Dispatched"** and click **Save**

**Expected Result:**
- `dispatched = true`, `dispatch_date = 2026-01-16`
- Appointment letter shows full lifecycle: Draft → Submitted → Approved → Signed → Dispatched
- `rework_count` remains 0 (no rework needed)

---

#### Flow 3: RC Appointment Return for Rework (Edge Case)

> Tests the rework path when RMQAM rejects the draft appointment letter.

**Precondition:** A second appointment letter in `Submitted` status.

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Open the submitted appointment letter
2. Instead of approving, click **"Return for Rework"** and add a comment:
   - Review Comments: `Appointment reference number format incorrect. Please use FCC/RC/APPT/2026/001 format.`
3. Confirm

**User (switch to RMO):** `rmo@fcc.go.tz`

4. Log in, open the returned appointment letter — status should be `DRAFT` (returned)
5. Verify `rework_count` incremented to 1
6. Correct the reference number and re-submit

**Expected Result:**
- Status returns to `Draft` after return; `rework_count = 1`
- After RMO's correction and resubmit, workflow resumes from Submitted stage

---

### Part B — Risk Assessment Sheets (Departmental Risk Register Development)

---

#### Flow 4: Risk Champion Creates and Submits a Risk Assessment Sheet

> RC fills in the RAS following a risk identification meeting, then submits to their Head for endorsement.

**Precondition:** A risk meeting has been held (can be created informally; see Flow 22).

**User:** Risk Champion (`riskchampion@fcc.go.tz`)

**Steps:**
1. Log in as `riskchampion@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-assessment-sheets`
3. Click **"New Risk Assessment Sheet"**
4. Enter data (from §3.5):
   - **Title:** `Operations Directorate Risk Assessment Sheet — Q3 FY2025/2026`
   - **Org Unit:** `Operations Directorate`
   - **Fiscal Year:** `FY 2025/2026`
   - **Reporting Period:** `Q3 (Jan – Mar 2026)`
5. Click **Save** — status: `DRAFT`
6. Fill in the risk detail fields for this individual risk (see §3.5 Risk Entries table — create **four separate RAS records**, one per risk):
   - **Risk Title**, **Category**, **Likelihood**, **Impact**, **Existing Controls**, **Risk Owner**, **Residual Level**
   - **Causes**, **Consequences**, **Risk Indicator**
   - **Strategic Objective** (select from Configuration dropdown)
   - **Risk Sector** (select from Configuration dropdown)
7. Click **"Submit to Head"** — status: `DRAFT → SUBMITTED_TO_HEAD`

> **Repeat for all 4 risks.** Each RAS is one risk. After all 4 are approved (Flows 5–7), the DRR will link to them.

**Expected Result:**
- RAS created for one risk (repeat Flows 4–7 for each of the 4 risks)
- Status progresses to `Submitted to Head`
- Activity log shows RC submitted with timestamp

---

#### Flow 5: Head Endorses the Risk Assessment Sheet

> The Directorate Head (can be RMQAM in test environment) endorses the RAS after RC submission.

**Precondition:** RAS in `Submitted to Head` status (from Flow 4).

**User:** RMQAM (`rmqam@fcc.go.tz`) *(acting as Directorate Head in test env)*

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-assessment-sheets`
3. Open the RAS from Flow 4
4. Click **"Endorse"** — status: `SUBMITTED_TO_HEAD → HEAD_ENDORSED`

**Expected Result:**
- Status: `Head Endorsed`
- Endorsement date and endorsed_by user recorded
- RC can now submit to RMQAM

---

#### Flow 6: RC Submits RAS to RMQAM for Review

**User:** Risk Champion (`riskchampion@fcc.go.tz`)

**Steps:**
1. Log in as `riskchampion@fcc.go.tz` / `Pass@1234`
2. Open the endorsed RAS
3. Click **"Submit to RMQAM"** — status: `HEAD_ENDORSED → SUBMITTED_TO_RMQAM`

**Expected Result:** Status: `Submitted to RMQAM`; RMQAM now sees it in their queue

---

#### Flow 7: RMQAM Approves the Risk Assessment Sheet

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to the RAS in `Submitted to RMQAM` status
3. Review the risk entries
4. Click **"Approve"** — status: `SUBMITTED_TO_RMQAM → APPROVED`

**Expected Result:**
- RAS status: `Approved`
- RAS ready for consolidation into Departmental Risk Register
- Activity log records RMQAM approval

---

#### Flow 8: RMQAM Returns RAS for Rework (Edge Case)

> When risk entries are incomplete or incorrect.

**Precondition:** A separate RAS in `Submitted to RMQAM` status.

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Open the submitted RAS
2. Click **"Return for Rework"**
3. Enter review comments: `Impact ratings for IT risks appear understated. Please review against the FCC Risk Impact Matrix and revise accordingly.`
4. Click **Confirm**

**Expected Result:**
- Status: `Returned for Rework`
- `review_comments` field populated
- RC logs in and can see the return reason, edit the RAS entries, and resubmit

---

#### Flow 9: Create Departmental Risk Register with Entries

> After RAS is approved, RC/RMO creates the formal Departmental Risk Register.

**Precondition:** Approved RAS from Flow 7.

**User:** Risk Champion (`riskchampion@fcc.go.tz`)

**Steps:**
1. Log in as `riskchampion@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/departmental-risks`
3. Click **"New Departmental Risk Register"**
4. Enter data (from §3.6):
   - **Title:** `Operations Directorate Risk Register — FY 2025/2026`
   - **Org Unit Type:** `Directorate`
   - **Fiscal Year:** `FY 2025/2026`
5. Click **Save** — status: `DRAFT`
6. Navigate to **Entries** tab — click **"Add Entry"** to link each of the 4 **approved RAS records** (from Flows 4–7):

   > **Important:** DRR entries are **links to existing approved RAS records** (`DeptRegisterEntry.risk_sheet` FK). You are not re-entering risk descriptions here — you select from the approved RAS list. For each entry, the system pulls the risk data from the RAS.

   - For each linked entry, add:
     - Proposed treatment action
     - Treatment deadline
7. When all 4 entries are linked, click **"Submit for Approval"** (start workflow) — status: `DRAFT → SUBMITTED`

**Expected Result:**
- DRR created with 4 entries
- Status: `Submitted`

---

#### Flow 10: RMQAM Approves the Departmental Risk Register

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/departmental-risks`
3. Open the submitted DRR
4. Click **"Advance Workflow"** → Approve — status: `SUBMITTED → APPROVED`

**Expected Result:**
- DRR status: `Approved`
- Ready for use as input to Institutional Risk Register workshop

---

### Part C — Institutional Risk Register

---

#### Flow 11: Create Institutional Risk Register and Notify Stakeholders

> RMO creates the IRR consolidating risks from all approved departmental registers.

**Precondition:** At least one approved Departmental Risk Register (Flow 10).

**User:** RMO (`rmo@fcc.go.tz`)

**Step 11a — Create IRR:**

1. Log in as `rmo@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/institutional-risks`
3. Click **"New Institutional Risk Register"**
4. Enter data (from §3.7):
   - **Title:** `FCC Institutional Risk Register — FY 2025/2026`
   - **Fiscal Year:** `FY 2025/2026`
   - **Workshop Date:** `2026-02-15`
   - **Workshop Venue:** `FCC Boardroom, Sam Nujoma Road, Dar es Salaam`
   - **Committee Meeting Date:** `2026-04-01`
   - **LSM Submission Date:** `2026-03-25`
5. Click **Save** — status: `DRAFT`

**Expected Result:** IRR created in Draft status

**Step 11b — Add IRR Entries (Risks Exceeding Threshold):**

6. Navigate to **Entries** tab
7. Click **"Add Entry"** to link risks from approved DRRs that exceed the institutional risk threshold:

   > **Important:** `InstitutionalRiskEntry` records reference existing **approved `RiskAssessmentSheet` records** via FK. You select from the list of approved RASes that came from multiple directorate DRRs. You are NOT re-typing risk descriptions — you select the approved RAS and add proposed control/deadline.

8. Link 3 risks (from §3.7 IRR Entries), selecting:
   - Source RAS (from approved DRRs)
   - Proposed Control
   - Implementation Deadline
   - Risk Owner (confirm from RAS)

**Expected Result:** 3 IRR entries visible

**Step 11c — Notify Directors to Grant RC Attendance Permission:**

9. Click **"Notify Directors"** button → `POST institutional-registers/{id}/notify-directors/`

**Expected Result:** `directors_notified_at` timestamp recorded; notification sent

**Step 11d — Notify RCs of Workshop Details:**

10. Click **"Notify RCs"** button → `POST institutional-registers/{id}/notify-rcs/`

**Expected Result:** `rcs_notified_at` timestamp recorded

---

#### Flow 12: Submit IRR Through Approval Workflow

> IRR passes through RMQAM review → Management review → Committee → Commission → Approved

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Open the IRR created in Flow 11
2. Click **"Submit Workflow"** (start) — status: `DRAFT → RMQAM_REVIEW`

**User:** RMQAM (`rmqam@fcc.go.tz`)

3. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
4. Open the IRR
5. Click **"Advance Workflow"** (RMQAM review complete) — status: `RMQAM_REVIEW → MANAGEMENT_REVIEW`

6. Continue advancing workflow stages:
   - **Management Review → Committee Review** (RMQAM advances)
   - **Committee Review → Commission Review** (LSM logs in and advances)

**User:** LSM (`lsm@fcc.go.tz`)

7. Log in as `lsm@fcc.go.tz` / `Pass@1234`, advance at Committee stage

**User:** DG (`dg@fcc.go.tz`)

8. Log in as `dg@fcc.go.tz` / `Pass@1234`
9. Advance at Commission Review stage — status: `COMMISSION_REVIEW → APPROVED`

**Expected Result:**
- IRR status progression: `Draft → RMQAM Review → Management Review → Committee Review → Commission Review → Approved`
- Each stage transition recorded in workflow history with actor and timestamp

---

#### Flow 13: Create Activity Report and DG Notes It

**Precondition:** IRR created in Flow 11.

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Log in as `rmo@fcc.go.tz` / `Pass@1234`
2. Navigate to the IRR detail page → **Activity Reports** tab
3. Click **"Add Activity Report"**
4. Enter:
   - **Report Title:** `IRR Workshop Activity Report — FY 2025/2026`
   - **Quarter:** Select `Q3 (Jan – Mar 2026)` from the Quarter FK dropdown
   - **Content:** `Risk Management Workshop conducted on 15 February 2026. 12 Risk Champions attended. 3 risks were escalated to institutional level. Risk Treatment Action Plan has been initiated.`
   - **Date:** `2026-02-20`
5. Click **Save**

   > **Note:** `ActivityReport.quarter` is a required FK to `core.Quarter`. Select the Q3 Quarter record from the dropdown; do not type the text directly.

**User:** RMQAM (`rmqam@fcc.go.tz`)

6. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
7. Open the Activity Report
8. Click **"Submit to DG"** / **"DG Note"** action

**User:** DG (`dg@fcc.go.tz`)

9. Log in as `dg@fcc.go.tz` / `Pass@1234`
10. Open the Activity Report
11. Click **"DG Note"** — marks DG as having noted the report

**Expected Result:**
- Activity Report linked to IRR
- DG noting recorded with timestamp

---

#### Flow 14: Distribute IRR to Directorates

**Precondition:** Approved IRR (from Flow 12).

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Open the Approved IRR
2. Click **"Distribute"** button → `POST institutional-registers/{id}/distribute/`
3. Enter distribution details if prompted:
   - **Distribution Reference:** `IRR-DIST-2026-001`

**Expected Result:**
- `distributed_to_directorates_at` timestamp set
- IRR is marked as distributed
- Distribution reference recorded

---

### Part D — Risk Treatment Action Plan (RTAP)

---

#### Flow 15: Create RTAP with Items

> RMO creates the RTAP based on the approved IRR, with items assigned to Risk Champions.

**Precondition:** Approved IRR from Flow 12.

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Log in as `rmo@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-treatment`
3. Click **"New Risk Treatment Action Plan"**
4. Enter data (from §3.8):
   - **Title:** `Risk Treatment Action Plan — FY 2025/2026`
   - **Fiscal Year:** `FY 2025/2026`
   - **Institutional Risk Register:** Select the approved IRR from Flow 12

   > **Constraint:** `RiskTreatmentActionPlan` has a `OneToOneField` relationship with `InstitutionalRiskRegister`. Only **one RTAP per IRR** is allowed. Attempting to create a second RTAP for the same IRR will raise a unique violation error.

5. Click **Save** — status: `DRAFT`
6. Navigate to **RTAP Items** tab
7. Add each item from §3.8 RTAP Items table (3 items). For each item:
   - **IRR Entry:** Select from the linked IRR entries (each item must reference an `InstitutionalRiskEntry` FK)
   - **Control Action** — treatment measure
   - **Responsible RC** (Anna Mushi)
   - **Target Date**
   - **Priority**

   > **Constraint:** `RTAPItem.inst_entry` is a foreign key to `InstitutionalRiskEntry`. You cannot create a standalone item without selecting an existing IRR entry.

**Expected Result:**
- RTAP created in Draft with 3 items
- Each item status: `not_started`

---

#### Flow 16: RTAP Approval Workflow

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Open the RTAP from Flow 15
2. Click **"Submit Workflow"** — status: `DRAFT → RMQAM_REVIEW`

**User:** RMQAM (`rmqam@fcc.go.tz`)

3. Advance workflow — status: `RMQAM_REVIEW → MANAGEMENT_REVIEW`
4. Continue advancing:
   - **Management Review → Committee Review**
   - **Committee Review → Commission Review**

**User:** LSM (`lsm@fcc.go.tz`)

5. Log in, approve at Committee stage

**User:** DG (`dg@fcc.go.tz`)

6. Advance at Commission Review — status: `COMMISSION_REVIEW → APPROVED`

**Expected Result:**
- RTAP status: `Approved` — same workflow stages as IRR
- Full governance chain recorded

---

#### Flow 17: RC Updates RTAP Item Status (Quarterly Update)

> After receiving the RTAP, the Risk Champion provides quarterly implementation status updates.

**Precondition:** Approved RTAP from Flow 16.

**User:** Risk Champion (`riskchampion@fcc.go.tz`)

**Steps:**
1. Log in as `riskchampion@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-treatment`
3. Open the RTAP and navigate to **Items** tab
4. Click on RTAP Item 1 (MFA deployment)
5. Navigate to **Quarterly Updates** tab
6. Click **"Add Quarterly Update"**
7. Enter:
   - **Quarter:** Select `Q3 (Jan – Mar 2026)` from the Quarter FK dropdown
   - **Implementation Status:** `in_progress`
   - **Progress Notes:** `MFA vendor selected and contract signed. System deployment scheduled for April 2026. Training plan prepared for IT staff.`
   - **Supporting Evidence:** (attach a PDF report if available)
8. Click **Save**

   > **Note:** `RTAPQuarterlyUpdate.quarter` is a required FK to `core.Quarter`. Select the seeded Q3 Quarter record from the dropdown.

**Expected Result:**
- Quarterly update recorded for RTAP Item 1
- Item status updated to `in_progress`
- Overall RTAP progress percentage auto-computed

---

#### Flow 18: RMO Returns an RTAP Item for Rework (Edge Case)

> When an RC's quarterly update is insufficient or unclear.

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Open an RTAP item quarterly update
2. Click **"Return for Rework"** on the update
3. Enter reason: `Progress notes are vague. Please provide specific milestones achieved, percentage completion, and attach supporting documentation.`
4. Click **Confirm**

**User:** Risk Champion (`riskchampion@fcc.go.tz`)

5. Log in, open the returned item
6. Verify `RETURNED_FOR_REWORK` status on the item
7. Update the progress notes with specific details
8. Click **"Resubmit"** — `POST risk/rtap-items/{id}/resubmit/`

**Expected Result:**
- Item returns to `in_progress` after resubmit
- Rework history visible in item activity log

---

#### Flow 19: RMO Sends Reminder to Risk Champions

> RTAP "Send Reminder" action to prompt RCs for overdue quarterly updates.

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Open the RTAP from Flow 15
2. Click **"Send Reminder to RCs"** button → `POST risk/rtap/{id}/send-reminder/`

**Expected Result:**
- Confirmation displayed: "Reminder sent to associated Risk Champions"
- Notification dispatched to Risk Champion users

---

#### Flow 20: Distribute RTAP to Directorates

**Precondition:** Approved RTAP from Flow 16.

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Open the Approved RTAP
2. Click **"Distribute"** → `POST risk/rtap/{id}/distribute/`

**Expected Result:**
- `distributed_to_directorates_at` timestamp set
- Distribution reference recorded

---

### Part E — Quarterly Performance Report (QPR)

---

#### Flow 21: Create Quarterly Performance Report

> RMQAM creates and submits the QPR documenting control implementation progress for Q3.

**Precondition:** RTAP with at least one updated item (from Flow 17).

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-performance-reports`
3. Click **"New Quarterly Performance Report"**
4. Enter data (from §3.9):
   - **Title:** `Quarterly Risk Management Performance Report — Q3 FY 2025/2026`
   - **Fiscal Year:** `FY 2025/2026`
   - **Reporting Quarter:** `Q3`
   - **Reporting Period:** `2026-01-01 → 2026-03-31`
   - **Executive Summary:** `Overall risk control implementation rate stands at 33% for Q3 2025/2026, an improvement of 10% over Q2.`
   - **Management Review Date:** `2026-03-20`
   - **Committee Meeting Date:** `2026-04-05`
5. Click **Save** — status: `DRAFT`

**Expected Result:** QPR created in Draft status

---

#### Flow 22: QPR Approval Workflow (Full Chain)

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Open the QPR from Flow 21
2. Click **"Submit Workflow"** — status: `DRAFT → RMQAM_PREPARE`

3. Advance: `RMQAM_PREPARE → LSM_SUBMIT` (RMQAM advances to LSM)

**User:** LSM (`lsm@fcc.go.tz`)

4. Log in, advance: `LSM_SUBMIT → MANAGEMENT_REVIEW`

**User:** RMQAM (`rmqam@fcc.go.tz`)

5. Advance: `MANAGEMENT_REVIEW → COMMITTEE_REVIEW`
6. Advance: `COMMITTEE_REVIEW → COMMISSION_SUBMIT`

**User:** DG (`dg@fcc.go.tz`)

7. Advance: `COMMISSION_SUBMIT → APPROVED`

**Expected Result:**
- QPR status: `Approved`
- Full 7-stage workflow recorded: Draft → RMQAM Preparing → LSM Submission → Management Review → Committee Review → Commission Submission → Approved

---

#### Flow 22b: Submit Approved QPR to IAGO (SRS §4.11.1.1 Req 14)

> After the QPR is approved, the RMQAM must record that it has been formally submitted to the Internal Auditor General Office (IAGO). The model tracks this separately via `iago_submitted`, `iago_submission_date`, and `iago_reference`.

**Precondition:** Approved QPR from Flow 22.

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Open the Approved QPR from Flow 21
3. Navigate to the **IAGO Submission** section (or look for the "Mark as Submitted to IAGO" button)
4. Enter:
   - **IAGO Reference:** `IAGO/RPT/2026/Q3/001`
   - **IAGO Submission Date:** `2026-04-30`
   - **IAGO Submitted:** `true` (tick/check)
5. Click **Save**

**Expected Result:**
- `iago_submitted = true`
- `iago_submission_date = 2026-04-30`
- `iago_reference = IAGO/RPT/2026/Q3/001`
- QPR record shows IAGO submission record alongside the regular Audit Committee approval
- Fulfils SRS §4.11.1.1 Requirement 14: quarterly report submitted to both Audit Committee AND IAGO

---

#### Flow 23: Export QPR (Dashboard Export)

**User:** RMQAM (`rmqam@fcc.go.tz`)
3. Verify the file downloads (PDF or CSV)

**Expected Result:** QPR exported; file contains performance data, RTAP implementation rates, comparative analysis

---

#### Flow 24: View Comparative Analysis on Risk Dashboard

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Navigate to `http://localhost:3001/service/grc/risk-dashboard`
2. Review KPI summary cards (Total Risks, Approved Registers, RTAP Progress %)
3. Click on **"Comparative Analysis"** tab/section → `GET risk/dashboard/comparative-analysis/`
4. Verify Q2 vs Q3 implementation rate comparison is displayed

**Expected Result:**
- Dashboard shows risk metrics and status counts
- Comparative analysis shows quarter-on-quarter trend data
- Export from dashboard available (PDF/CSV)

---

### Part F — Risk Meetings, Surveys & Knowledge Base

---

#### Flow 25: Create and Record a Risk Meeting

> Meetings include risk discussion sessions, brainstorming workshops, and awareness sessions.

**User:** Risk Champion (`riskchampion@fcc.go.tz`)

**Steps:**
1. Log in as `riskchampion@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-meetings`
3. Click **"New Meeting"**
4. Enter data (from §3.10):
   - **Title:** `Operations Directorate Risk Brainstorming Session`
   - **Meeting Type:** `Brainstorming`
   - **Meeting Date:** `2026-02-10 10:00 AM`
   - **Venue:** `FCC Conference Room B`
   - **Fiscal Year:** `FY 2025/2026`
   - **Agenda:** `Review and update risk register for Q3; identify emerging risks`
5. Click **Save** — status: `Scheduled`
6. Navigate to **Attendance** tab
7. Click **"Add Attendee"** and add 3 participants (use any user IDs available)
8. After the meeting, return and update:
   - **Status:** `Completed`
   - **Minutes:** `Meeting held on 10 Feb 2026. 4 new risks identified. IT downtime risk rated as High. All risks documented in draft RAS. Next meeting: 15 Mar 2026.`
   - **Outcomes:** (add as JSON list or text field)

**Expected Result:**
- Meeting created and transitioned from `Scheduled → In Progress → Completed`
- Attendance records linked to the meeting
- Minutes and outcomes stored

---

#### Flow 25b: Create an Awareness Session Meeting (SRS §4.11.1.1 Req 1)

> The RMQAM must conduct awareness sessions for Risk Champions, Risk Owners, and staff to build risk management capacity. These use `meeting_type: awareness_session`.

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-meetings`
3. Click **"New Meeting"**
4. Enter:
   - **Title:** `Risk Management Framework Awareness Session — Operations Directorate`
   - **Meeting Type:** `awareness_session`
   - **Meeting Date:** `2026-01-20 09:00 AM`
   - **Venue:** `FCC Main Boardroom, Dar es Salaam`
   - **Fiscal Year:** `FY 2025/2026`
   - **Agenda:** `Introduction to the FCC Risk Management Framework; roles and responsibilities of Risk Champions; overview of the Risk Assessment Sheet process`
5. Click **Save** — status: `Scheduled`
6. Add 10+ attendees (all Operations Directorate staff from the user lookup)
7. After the session, update status to `Completed` and add minutes

**Expected Result:**
- Awareness session meeting created with type `awareness_session`
- Distinct from `brainstorming` meeting (different type)
- Fulfils SRS §4.11.1.1 Requirement 1: periodic awareness sessions for all staff

---

> Surveys are used to gather staff input on risk awareness and identification (SRS §4.11.1.1 req 3).

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-surveys`
3. Click **"New Survey"**
4. Enter data (from §3.11):
   - **Title:** `Staff Risk Awareness Survey — Q3 2026`
   - **Description:** `Quarterly survey to assess staff understanding of the risk management framework and their awareness of key departmental risks`
5. Click **Save** — status: `DRAFT`
6. Navigate to **Questions** tab and add 3 questions from §3.11 Survey Questions
7. Click **"Open Survey"** — status: `DRAFT → OPEN`

**Open state — RC submits a response:**

**User:** Risk Champion (`riskchampion@fcc.go.tz`)

8. Log in, navigate to the survey
9. Click **"Respond"**
10. Fill in answers:
    - Q1 Rating: `4`
    - Q2 Yes/No: `Yes`
    - Q3 Text: `The most significant risk I am aware of is the risk of IT system downtime during peak complaint-processing periods.`
11. Click **Submit Response**

**User:** RMQAM (`rmqam@fcc.go.tz`)

12. Navigate to the survey, click **"Close Survey"** — status: `OPEN → CLOSED`

**Expected Result:**
- Survey created, opened, response recorded, then closed
- Closed survey shows response count

---

#### Flow 27: Add a Risk Knowledge Base Entry

> Historical data and lessons learned captured for future risk identification (SRS §4.11.1.1 req 4).

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Navigate to `http://localhost:3001/service/grc/risk-knowledge-base`
2. Click **"New Entry"**
3. Enter data (from §3.12):
   - **Title:** `IT System Downtime — Lessons Learned`
   - **Source Type:** `Lessons Learned`
   - **Content:** `During Q2 2025/2026, IT system downtime impacted complaint processing for 8 hours. Root cause was a failed UPS. Mitigation: redundant UPS systems procured and tested.`
   - **Date:** `2026-01-15`
4. Click **Save**

**Expected Result:**
- Knowledge base entry created and visible in the list
- Searchable by title and source type

---

### Part G — Quality Auditor Appointment

---

#### Flow 28: Register a Quality Auditor

> RMQAM nominates a staff member as Quality Auditor/Quality Champion.

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/quality-auditors`
3. Click **"New Quality Auditor"**
4. Enter data (from §3.13):
   - **Nominee:** Frank Lupembe (`qualityauditor@fcc.go.tz`)
   - **Org Unit Type:** `Directorate`
   - **Directorate / Unit:** `Risk Management Unit`
   - **Qualifications:** `ISO 9001:2015 Lead Auditor Certificate (TBS, Dec 2025)`
   - **Experience Summary:** `4 years internal quality audit experience; participated in 3 ISO certification audits`
5. Click **Save**

**Expected Result:**
- Quality Auditor record created
- Auditor visible in Quality Auditors list
- Nomination status: `Active`

---

#### Flow 29: Create QA Training Session and Add Attendees

> ISO 9001:2015 training is arranged for proposed Quality Auditors before their appointment.

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Log in as `rmo@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/qa-training`
3. Click **"New Training Session"**
4. Enter data (from §3.15):
   - **Title:** `ISO 9001:2015 QMS Audit Examination — Batch 1`
   - **Training Date:** `2026-01-10`
   - **Venue:** `FCC Training Room, Dar es Salaam`
   - **Trainer:** `Mr. James Mwita`
   - **Pass Threshold:** `75`
5. Click **Save** — approval_status: `Proposed`
6. Navigate to **Attendees** tab → **"Add Attendee"**
7. Add Frank Lupembe (`qualityauditor@fcc.go.tz`) as attendee:
   - **Exam Score:** `82` (pass ≥75%)
   - **Pass/Fail:** `Passed`

**Approve the training session (RMQAM):**

**User:** RMQAM (`rmqam@fcc.go.tz`)

8. Log in, open the training session
9. Click **"Approve Training"** → `POST risk/qa-training/{id}/approve/`

**Expected Result:**
- Training session created and approved
- Attendee exam result recorded: `82%` — Passed
- `approval_status: approved` (model choices: `proposed` / `approved` / `completed` / `cancelled` — no `rejected`)

**Notify attendees:**

10. Click **"Notify Attendees"** → `POST risk/qa-training/{id}/notify-attendees/`

**Expected Result:** `notified_count` returned; attendees receive confirmation notification

---

#### Flow 29b: QA Exam Failure — Max 2 Attempts Rule (Edge Case)

> SRS §1.9.8 Rule E.3: A proposed QA is allowed a maximum of 2 exam re-sits. Failure after the 2nd attempt triggers a replacement nomination by the Head of Department.

**Precondition:** A NEW `QualityAuditor` nominee (not Frank Lupembe — he already passed). Nominate a second candidate, e.g. a staff member who scores below 75%.

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**

**Attempt 1 — Fail:**
1. Create a QA training session for the second nominee
2. Add the nominee as an attendee with:
   - **Exam Score:** `55` (fail — below 75%)
   - `exam_attempt = 1`
3. Save — attendee status: `Failed`
4. Verify `nomination_status` on the QualityAuditor record remains `proposed` (not blocked yet)

**Attempt 2 — Fail again:**
5. Create a second training session (same nominee added)
6. Exam Score: `60` (still fail)
   - `exam_attempt` increments to `2`
7. Save — attendee status: `Failed`
8. Verify `nomination_status` on the QualityAuditor record updates to `replacement_needed`

**Expected Result:**
- After 2nd fail: `QualityAuditor.nomination_status = replacement_needed`
- System should surface this to RMQAM — a notification that a replacement must be nominated by the Head
- The model field `exam_attempt` is capped at 2 (no further attempts allowed)
- Head of Department must submit a new nominee name to RMQAM to restart the process

---

#### Flow 30: Create QA Appointment Letter and Process Workflow

> Formal DG-signed appointment letter for Quality Auditor.

**Precondition:** Quality Auditor from Flow 28, training confirmed from Flow 29.

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Navigate to Frank Lupembe's Quality Auditor record
2. Click **"Appointments"** tab → **"New Appointment Letter"**
3. Enter data (from §3.14):
   - **Reference:** `QA-APPT-2026-001`
   - **Effective Date:** `2026-01-20`
   - **Letter Content:** `You are hereby appointed as Quality Auditor/Champion for the Risk Management Unit effective 20 January 2026 for a period of three (3) years.`
4. Click **Save** — status: `DRAFT`
5. Click **"Submit for Review"** (start workflow) — status: `SUBMITTED`

**User:** RMQAM (`rmqam@fcc.go.tz`)

6. Open the QA appointment, advance workflow (RMQAM approval)

**User:** DG (`dg@fcc.go.tz`)

7. Advance workflow to sign — status: `SIGNED`

**User:** RMO (`rmo@fcc.go.tz`)

8. Set `dispatched = true`, enter `dispatch_date = 2026-01-21`, `dispatch_reference = REG-2026-QA-001`

**Expected Result:**
- QA appointment letter: Draft → Submitted → Approved → Signed → Dispatched
- Same lifecycle pattern as RC appointment

---

### Part H — QMS Audit Programme & Audit Plan

---

#### Flow 31: Create and Approve QMS Audit Programme

> Annual QMS audit programme developed by RMO in collaboration with QAs.

**User:** RMO (`rmo@fcc.go.tz`)

**Steps:**
1. Log in as `rmo@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/qms-programs`
3. Click **"New QMS Audit Programme"**
4. Enter data (from §3.16):
   - **Title:** `FCC QMS Audit Programme — FY 2025/2026`
   - **Fiscal Year:** `FY 2025/2026`
   - **Audit Scope:** `All QMS processes excluding those under Risk Management Unit`
   - **Objectives:** `Verify conformity with ISO 9001:2015 requirements; identify NCs and areas for improvement`
5. Click **Save** — status: `DRAFT`
6. Click **"Submit for Approval"** (start workflow) — status: `SUBMITTED`

**User:** RMQAM (`rmqam@fcc.go.tz`)

7. Log in, open the Programme
8. Click **"Advance Workflow"** → Approve — status: `APPROVED`

**Expected Result:**
- QMS Programme: `Draft → Submitted → Approved`
- Approved programme is prerequisite for creating Audit Plans

---

#### Flow 32: Create and Approve QMS Audit Plan

> Detailed audit plan for a specific QMS process.

**Precondition:** Approved QMS Programme from Flow 31.

**User:** RMO (`rmo@fcc.go.tz`)

**Step 32a — Create the Plan:**

1. Log in as `rmo@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/qms-plans`
3. Click **"New QMS Audit Plan"**
4. Enter data (from §3.17):
   - **Title:** `Customer Complaints Management Process Audit`
   - **QMS Programme:** Link to programme from Flow 31
   - **Audit Start Date:** `2026-03-10`
   - **Audit End Date:** `2026-03-14`
   - **Notification Date:** `2026-02-28` (10 working days before audit start — required by Rule E.7)
   - **Audit Scope:** `Customer complaints handling process from receipt to resolution`
   - **Auditee:** `Consumer Affairs Directorate`
5. Click **Save** — status: `DRAFT`

   > **Constraint test:** Try entering `Notification Date: 2026-03-05` (< 10 days before 2026-03-10) — expect a `ValidationError`: *"Notification date must be at least 10 working days before the audit start date."* Then correct to `2026-02-28`.
6. Navigate to **Team** tab → **"Add Team Member"**
7. Add Frank Lupembe as `Team Leader`
8. Navigate to **Timetable** tab → add 4 timetable entries (from §3.17 Timetable Entries)
9. Click **"Submit for Approval"** (start workflow) — status: `SUBMITTED`

**User:** RMQAM (`rmqam@fcc.go.tz`)

10. Approve the plan — status: `APPROVED`

**Expected Result:**
- QMS Plan: `Draft → Submitted → Approved`
- Team assignment shows Frank Lupembe as Team Leader
- 4 timetable entries visible

---

#### Flow 33: Record QMS Audit Meetings (Entry and Exit)

**Precondition:** Approved QMS Audit Plan from Flow 32.

**User:** Quality Auditor (`qualityauditor@fcc.go.tz`)

**Step 33a — Record Entry Meeting:**

1. Log in as `qualityauditor@fcc.go.tz` / `Pass@1234`
2. Open the QMS Audit Plan detail page
3. Navigate to **Audit Meetings** tab → **"Add Audit Meeting"**
4. Enter:
   - **Meeting Type:** `entry_meeting`
   - **Date:** `2026-03-10`
   - **Time:** `09:00`
   - **Notes:** `Entry meeting held with Consumer Affairs Director. Audit scope confirmed. Timetable agreed. Non-disclosure forms signed by all parties.`
   - **NDA Signed:** `Yes` (tick)
5. Click **Save**

**Step 33b — Record Exit Meeting:**

6. Click **"Add Audit Meeting"** again
7. Enter:
   - **Meeting Type:** `exit_meeting`
   - **Date:** `2026-03-14`
   - **Time:** `10:00`
   - **Notes:** `Exit meeting held. 2 NCs presented to auditee. Minor NC on complaint timelines acknowledged. Major NC on feedback analysis disputed initially but agreed after review. Audit report signed.`
8. Click **Save**

**Step 33c — Record Pre-Audit Meeting (SRS §1.9.9 Step 12):**

> The Team Leader and QA team conduct a **pre-audit meeting** to review relevant documentation before commencing fieldwork: ISO 9001:2015 standard requirements, applicable policies, SOPs, and any previous audit reports.

9. Click **"Add Audit Meeting"** again
10. Enter:
    - **Meeting Type:** `pre_audit`
    - **Date:** `2026-03-09`
    - **Time:** `14:00`
    - **Notes:** `Pre-audit meeting held. Team reviewed ISO 9001:2015 Clauses 8.2 and 9.1. Previous audit report (FY 2024/2025) reviewed — 1 previous observation now resolved. Audit checklist prepared and assigned. Document request list submitted to Consumer Affairs Records Officer.`
11. Click **Save**

> **Constraint:** `QMSAuditMeeting.unique_together = ['audit_plan', 'meeting_type']` — only one of each meeting type (`pre_audit`, `entry`, `exit`) per plan. Attempting to add a second entry meeting will raise a unique constraint error.

**Expected Result:**
- All three audit meeting types recorded: `pre_audit` (2026-03-09) → `entry` (2026-03-10) → `exit` (2026-03-14)
- `nda_signed = true` on the plan after entry meeting recorded
- Pre-audit meeting fulfils SRS §1.9.9 Steps 12–15 document review requirement

---

#### Flow 34: Create QMS Audit Checklist

> Quality Auditor prepares and populates audit checklists during fieldwork.

**Precondition:** Approved QMS Audit Plan from Flow 32.

**User:** Quality Auditor (`qualityauditor@fcc.go.tz`)

**Steps:**
1. Log in as `qualityauditor@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/qms-checklists`
3. Click **"New Checklist"**
4. Link to the QMS Plan from Flow 32
5. Add 4 checklist entries from §3.18:
   - For each: Process Area, ISO Clause, Question, Conformity Status
6. Set conformity:
   - Entry 1: `Conforming`
   - Entry 2: `Minor NC`
   - Entry 3: `Major NC`
   - Entry 4: `Observation`
7. Click **Save**

**Expected Result:**
- Checklist created with 4 entries and correct conformity statuses
- Major NC and Minor NC entries flagged for Non-Conformance creation

---

### Part I — QMS Audit Reports & Non-Conformances

---

#### Flow 35: Create QMS Audit Report

**Precondition:** Completed checklist (Flow 34); exit meeting held (Flow 33).

**User:** Quality Auditor (`qualityauditor@fcc.go.tz`)

**Steps:**
1. Log in as `qualityauditor@fcc.go.tz` / `Pass@1234`
2. Open the QMS Audit Plan detail → navigate to **Reports** tab (or navigate to `http://localhost:3001/service/grc/qms-plans/{planId}`)
3. Click **"New Audit Report"**
4. Enter data (from §3.19):
   - **Report Title:** `QMS Audit Report — Customer Complaints Management Process`
   - **Audit Period:** `2026-03-10 → 2026-03-14`
   - **Summary:** `Two NCs identified: complaint resolution timelines not documented (Minor NC) and customer feedback not analysed for improvement (Major NC). Corrective actions required within 30 days.`
5. Click **Save** — status: `DRAFT`

**Expected Result:** QMS Audit Report created in Draft status

---

#### Flow 36: Team Leader Signs, Auditee Acknowledges

**User:** Quality Auditor (acting as Team Leader) (`qualityauditor@fcc.go.tz`)

**Steps:**
1. Open the QMS Report from Flow 35
2. Click **"Sign as Team Leader"** → `POST risk/qms-reports/{id}/sign-tl/` — status: `DRAFT → TL_SIGNED`

**User:** RMQAM (`rmqam@fcc.go.tz`) *(acting as auditee representative in test env)*

3. Log in
4. Click **"Auditee Acknowledge"** → `POST risk/qms-reports/{id}/sign-auditee/` — status: `TL_SIGNED → AUDITEE_ACKNOWLEDGED`

> In production, the actual auditee (Consumer Affairs Director) would log in to acknowledge.

**Expected Result:**
- Status progression: `Draft → TL Signed → Auditee Acknowledged`
- Both signatures with timestamps recorded

---

#### Flow 37: QMS Report Governance Chain (Full Post-Finalisation Chain)

> After auditee acknowledgement, the report passes through RMQAM review → MRM → Audit Committee → Commission.

**User:** Quality Auditor (`qualityauditor@fcc.go.tz`)

**Steps:**
1. From `Auditee Acknowledged` status, click **"Finalise Report"** → `POST risk/qms-reports/{id}/finalise/` — status: `AUDITEE_ACKNOWLEDGED → FINALISED`
2. Click **"Submit to RMQAM"** → `POST risk/qms-reports/{id}/submit-to-rmqam/` — status: `FINALISED → SUBMITTED_TO_RMQAM`

> **Important:** The `finalised` status is a required intermediate step between `auditee_acknowledged` and `submitted_to_rmqam`. You cannot submit directly to RMQAM from `auditee_acknowledged`.

**User:** RMQAM (`rmqam@fcc.go.tz`)

3. Log in, open report
4. Review and click **"Present at MRM"** → `POST risk/qms-reports/{id}/present-at-mrm/` — status: `→ PRESENTED_AT_MRM`
5. Record MRM directives: click **"Record Directives"** → `POST risk/qms-reports/{id}/record-directives/`
   - **MRM Directives:** `Management directed that corrective actions be completed within 30 days. Monthly progress updates to be submitted to RMQAM.`
   — status: `→ DIRECTIVES_RECEIVED`
6. Click **"Submit to Audit Committee"** → `POST risk/qms-reports/{id}/submit-to-audit-committee/` — status: `→ SUBMITTED_TO_AUDIT_COMMITTEE`
7. Click **"Audit Committee Review"** → `POST risk/qms-reports/{id}/audit-committee-review/` — status: `→ AUDIT_COMMITTEE_REVIEWED`
8. Click **"Adopt by Commission"** → `POST risk/qms-reports/{id}/adopt-by-commission/` — status: `→ ADOPTED_BY_COMMISSION`

**Expected Result:**
- Full governance chain recorded:
  `Draft → TL Signed → Auditee Acknowledged → Finalised → Submitted to RMQAM → Presented at MRM → Directives Received → Submitted to Audit Committee → Audit Committee Reviewed → Adopted by Commission`
- MRM directives captured with timestamp

---

#### Flow 38: RMQAM Returns Report for Revision (Edge Case)

> When RMQAM requires changes before MRM presentation.

**Precondition:** A second report in `Submitted to RMQAM` status.

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Open the submitted QMS report
2. Click **"Return for Revision"** → `POST risk/qms-reports/{id}/return-for-revision/`
3. Enter:
   - **Review Comments:** `Audit findings section lacks sufficient evidence references. Please attach checklist references for each NC before resubmission.`
4. Click **Confirm** — status: `SUBMITTED_TO_RMQAM → RETURNED_FOR_REVISION`

**Expected Result:**
- Status: `Returned for Revision`
- `rmqam_review_comments` stored
- `returned_for_revision_at` timestamp set

**Step 38b — QA Corrects and Resubmits (SRS §4.11.1.4 Req 10):**

**User:** Quality Auditor (`qualityauditor@fcc.go.tz`)

5. Log in, open the report in `Returned for Revision` status
6. Update the findings section to add checklist references for each NC
7. Click **"Submit to RMQAM"** again → `POST risk/qms-reports/{id}/submit-to-rmqam/` — status: `RETURNED_FOR_REVISION → SUBMITTED_TO_RMQAM`

**Expected Result:**
- Report status returns to `Submitted to RMQAM`
- RMQAM can now proceed to present at MRM
- The revision cycle is recorded in the activity log

---

#### Flow 39: Create and Manage Non-Conformances

**Precondition:** QMS Audit Report created (Flow 35). Checklist entries with Minor NC and Major NC conformity (Flow 34).

**User:** Quality Auditor (`qualityauditor@fcc.go.tz`)

**Steps (create NC 1 — Minor):**
1. Log in as `qualityauditor@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/non-conformances`
3. Click **"New Non-Conformance"**
4. Enter NC 1 data (from §3.20):
   - **NC Type:** Minor NC
   - **ISO Clause:** Select `Clause 8.2.2` from the ISO Clause FK dropdown
   - **Description:** `Complaint resolution timelines are not documented in the Consumer Affairs Standard Operating Procedure, violating ISO 9001:2015 Clause 8.2.2.`
   - **Objective Evidence:** `Consumer Affairs SOP reviewed; Section 4.2 (Complaint Handling) contains no defined timelines or escalation periods. Staff confirmed timelines are managed informally.`
   - **Corrective Action Required:** `Update SOP to include defined complaint resolution timelines; train all Consumer Affairs staff`
   - **Due Date:** `2026-04-14`
   - **Linked Audit Report:** Link to the QMS Audit Report from Flow 35
5. Click **Save** — status: `RAISED`

   > **Note:** `iso_clause` (FK, required) and `objective_evidence` (text, required) are mandatory — the form will not save without both fields.

**Repeat steps 3-5 for NC 2 (Major)** using data from §3.20 (ISO Clause: `Clause 9.1.2`).

**Expected Result:**
- 2 NCs created in `Raised` status
- Both linked to the QMS Report/Plan

---

#### Flow 40: NC Lifecycle — Raised → Acknowledged → In Progress → Closed

**Preconditions:** NCs from Flow 39.

**Step 40a — Acknowledge NC (Auditee):**

**User:** RMQAM (`rmqam@fcc.go.tz`) *(representing auditee in test env)*

1. Open NC 1 (Minor NC)
2. Update status to **Acknowledged** — status: `RAISED → ACKNOWLEDGED`

**Step 40b — Start Corrective Action:**

3. Update status to **In Progress**, add progress note:
   - `SOP revision in progress. Draft circulated to Consumer Affairs Director for review.`
   — status: `ACKNOWLEDGED → IN_PROGRESS`

**Step 40c — Close NC:**

4. Update status to **Closed**, add closure notes:
   - `SOP updated and approved on 2026-04-10. All Consumer Affairs staff trained on 2026-04-12. Evidence: Updated SOP v2.1, Training attendance register.`
5. Set `closed_at` date

**Expected Result:**
- NC status: `Raised → Acknowledged → In Progress → Closed`
- `closed_at` timestamp set; `closure_notes` recorded

---

#### Flow 41: Dispute a Non-Conformance and Resolve (Edge Case)

> Auditee disagrees with an NC finding — allows the TL to correct or amend.

**Precondition:** NC 2 (Major NC) in `Raised` or `Acknowledged` status.

**User:** RMQAM (`rmqam@fcc.go.tz`) *(representing disputing auditee)*

**Steps:**
1. Open NC 2 (Major NC)
2. Click **"Dispute"** → `POST risk/non-conformances/{id}/dispute/`
3. Enter dispute reason:
   - `We dispute the Major NC classification. Customer feedback is reviewed informally at department meetings; the absence of a documented procedure should be classified as a Minor NC, not Major NC.`
4. Confirm — status: `→ DISPUTED`

**Step 41b — Team Leader Resolves the Dispute:**

**User:** Quality Auditor (`qualityauditor@fcc.go.tz`)

5. Open the Disputed NC
6. Click **"Resolve Dispute"** → `POST risk/non-conformances/{id}/resolve-dispute/`
7. Enter:
   - **Resolution Action:** `After review of the evidence, the NC classification is maintained as Major NC. Informal review at departmental meetings does not constitute a documented monitoring and measurement system as required by ISO 9001:2015 Clause 9.1.2.`
   - **New Status:** `in_progress` (dispute resolved; NC retained)
8. Confirm

**Expected Result:**
- NC status: `Disputed → In Progress` (or to `Acknowledged` if TL amends the finding)
- `dispute_reason` and resolution action both recorded with timestamps

---

#### Flow 42: View NC Monthly Summary

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Navigate to `http://localhost:3001/service/grc/non-conformances`
2. Click on **"Monthly Summary"** tab or section → `GET risk/non-conformances/monthly-summary/`
3. Review:
   - NCs by status this month
   - NCs by type (Major / Minor)
   - Overdue NCs

**Expected Result:**
- Monthly summary displays aggregated NC data
- Overdue NCs (past due date and not closed) highlighted

---

### Part J — Risk Dashboard

---

#### Flow 43: Verify Risk Dashboard KPIs

**User:** RMQAM (`rmqam@fcc.go.tz`)

**Steps:**
1. Log in as `rmqam@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/risk-dashboard`
3. Verify the following KPI cards are visible and populated:
   - **Total Risks Registered** (from approved DRRs and IRR)
   - **Total Risk Champions** (from champion records)
   - **RTAP Items — Not Started / In Progress / Completed**
   - **Approved Registers** (DRR and IRR counts)
   - **Quarterly Reports** — current quarter status
   - **Active NCs** — open non-conformances count
   - **QMS Programmes / Plans** — status breakdown
4. Click **"Export Dashboard"** → `GET risk/dashboard/export/`
5. Verify file downloads

**Expected Result:**
- Dashboard populated with data from all completed flows above
- Export produces a file with dashboard data (PDF or CSV)

---

#### Flow 44: View Risk Dashboard as Different Roles (Role Boundary Test)

> Verify each role sees only what they are permitted to see.

**Sub-flow 44a — Risk Champion view:**

**User:** Risk Champion (`riskchampion@fcc.go.tz`)

1. Log in, navigate to `http://localhost:3001/service/grc/risk-dashboard`
2. Verify: Can see dashboard but limited to their directorate's data
3. Verify: Cannot access QMS Programs, Quality Auditors, QPR creation buttons

**Sub-flow 44b — Quality Auditor view:**

**User:** Quality Auditor (`qualityauditor@fcc.go.tz`)

4. Log in, navigate to dashboard
5. Verify: Can view dashboard KPIs
6. Verify: Can access QMS checklists and non-conformances
7. Verify: Cannot see RTAP, IRR, or QPR management options

**Sub-flow 44c — LSM view:**

**User:** LSM (`lsm@fcc.go.tz`)

8. Log in, navigate to dashboard
9. Verify: Can see dashboard (read-only)
10. Verify: IRR, RTAP, QPR in `Committee Review` stage show "Advance" button
11. Verify: Cannot create/edit Risk Champions, RAS, or QMS content

**Expected Result:**
- Role boundaries enforced: each user sees only their permitted features
- Unauthorized action buttons hidden or disabled per role permissions

---

## 5. Additional Notes

### §5.1 Workflow Stages Summary

| Document | Draft → | Stage 1 → | Stage 2 → | Final |
|---|---|---|---|---|
| RC/QA Appointment | Draft | Submitted | Approved | Signed / Dispatched |
| RAS | Draft | Submitted to Head | Head Endorsed → Submitted to RMQAM | Approved |
| DRR / IRR / RTAP | Draft | RMQAM Review | Management Review → Committee Review → Commission Review | Approved |
| QPR | Draft | RMQAM Preparing | LSM Submission → Management Review → Committee Review → Commission Submission | Approved |
| QMS Programme/Plan | Draft | Submitted | — | Approved |
| QMS Audit Report | Draft | TL Signed | Auditee Acknowledged → **Finalised** → Submitted to RMQAM → Presented at MRM → Directives Received → Audit Committee → | Adopted by Commission |
| Non-Conformance | Raised | Acknowledged | In Progress | Closed |

### §5.2 Role Boundaries

| Action | RMQAM | RMO | Risk Champion | Quality Auditor | LSM | DG |
|---|---|---|---|---|---|---|
| Approve RAS | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Submit DRR workflow | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Approve IRR/RTAP | ✅ | ❌ | ❌ | ❌ | ✅ (Committee) | ✅ (Commission) |
| Approve QPR | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Submit QPR to IAGO | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Sign RC/QA appointment | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Create/manage NCs | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Conduct Risk Assessment | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Create QMS Checklist | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Present audit report at MRM | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Approve/Reject QA Training | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Finalise QMS Audit Report | ❌ | ❌ | ❌ | ✅ (TL) | ❌ | ❌ |

### §5.3 Known Test Environment Constraints

- **DG user** (`dg@fcc.go.tz`) was created during Internal Audit setup. If the risk management role `director_general` was not assigned, re-run the setup script from §16 of `grc_notes.md`.
- **LSM user** (`lsm@fcc.go.tz`) must be assigned the `lsm` GRC role and granted WO permissions (§17 of `grc_notes.md`) before they can advance workflow stages.
- **Self-approval guard:** The same user cannot advance a workflow stage they submitted. Use separate accounts for submit vs. approve steps.
- **Fiscal Year must exist and match:** All records require a valid `FiscalYear` entry. Use FY 2025/2026.
- **Quarter FK:** `ActivityReport.quarter` and `RTAPQuarterlyUpdate.quarter` are FK fields to `core.Quarter`. Q3 must be seeded before creating these records.
- **Rework counter:** `rework_count` increments per return-for-rework action. Check this field to verify rework cycles are tracked.
- **NDA signed flag:** The `nda_signed` flag on QMS Plans is set when an Entry Meeting is recorded with NDA confirmation. Verify this before advancing to audit fieldwork.
- **`distributed_to_directorates_at`** is set on IRR and RTAP only after clicking "Distribute". It does not auto-set on workflow approval.

#### Business Rule Constraints (Model-Level Validations)

| Rule | Source | Constraint | Expected Error |
|---|---|---|---|
| BR1 | SRS §1.9.8 Rule E.3 | Maximum 2 exam attempts for QA nominees (see Flow 29b) | After 2nd fail: `nomination_status = replacement_needed` |
| BR2 | `QMSAuditTeamAssignment.clean()` | QA auditor cannot audit their own organisational unit | `ValidationError: A quality auditor cannot audit their own unit` |
| BR3 | `QMSAuditPlan.clean()` Rule E.7 | Notification date must be ≥ 10 working days before audit start | `ValidationError: Notification date must be at least 10 working days before audit start date` |
| BR4 | `InstitutionalRiskRegister.clean()` | LSM submission date must be ≥ 7 days before Committee meeting date | `ValidationError: LSM submission date must be at least 7 days before committee meeting date` |
| BR4a | `RiskTreatmentActionPlan.clean()` | Same 7-day rule applies to RTAP | Same `ValidationError` |
| BR4b | `QuarterlyPerformanceReport.clean()` | Same 7-day rule applies to QPR | Same `ValidationError` |
| BR5 | `RiskChampion` unique constraint | Only one **active** RC per organisational unit at a time | `IntegrityError: unique_active_rc_per_org_unit` (attempt to create second active RC for Operations Directorate) |
| BR6 | `RiskTreatmentActionPlan` unique constraint | Only one active RTAP per fiscal year | `IntegrityError: unique_active_rtap_per_fiscal_year` |
| BR7 | `InstitutionalRiskRegister` unique constraint | Only one active IRR per fiscal year | `IntegrityError: unique_active_irr_per_fiscal_year` |
| BR8 | `QMSAuditMeeting.unique_together` | Only one of each meeting type (`pre_audit`, `entry`, `exit`) per QMS Audit Plan | `IntegrityError: unique_together constraint` when adding a second entry meeting to the same plan |
| BR9 | `AuditChecklist.unique_together` | One checklist entry per ISO clause, per auditor, per plan | `IntegrityError` when adding a duplicate clause+auditor combination to the same plan |
| BR10 | `RiskTreatmentActionPlan.inst_register` | RTAP is `OneToOneField` with IRR — only one RTAP per IRR | `IntegrityError` when creating a second RTAP for the same IRR |

### §5.4 Data Reset

To reset all Risk Management transactional data without touching lookup configuration, from the `grc-service` container:

```python
# Run in Django shell: docker compose exec grc-service python manage.py shell
from apps.core.models.risk_entities import (
    RiskChampion, RiskChampionAppointment, RiskAssessmentSheet,
    DepartmentalRiskRegister, InstitutionalRiskRegister, RiskTreatmentActionPlan,
    RTAPItem, RTAPQuarterlyUpdate, QuarterlyPerformanceReport, ActivityReport,
    QualityAuditor, QualityAuditorAppointment, QATrainingSession,
    QMSAuditProgram, QMSAuditPlan, AuditChecklist, QMSAuditReport,
    NonConformance, RiskMeeting, RiskSurvey, RiskKnowledgeBase,
)

models_to_clear = [
    NonConformance, QMSAuditReport, AuditChecklist, QMSAuditPlan, QMSAuditProgram,
    QATrainingSession, QualityAuditorAppointment, QualityAuditor,
    ActivityReport, QuarterlyPerformanceReport, RTAPQuarterlyUpdate, RTAPItem,
    RiskTreatmentActionPlan, InstitutionalRiskRegister, DepartmentalRiskRegister,
    RiskAssessmentSheet, RiskChampionAppointment, RiskChampion,
    RiskMeeting, RiskSurvey, RiskKnowledgeBase,
]

for model in models_to_clear:
    count, _ = model.objects.all().delete()
    print(f"Deleted {count} {model.__name__}")
```
