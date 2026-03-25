# Legal Module — End-to-End Testing Data Guide

> **Date:** 2026-03-24
> **Base URL:** `http://localhost:3001` (Staff Portal)
> **Module:** Legal Services — FCC GRC Platform
> **Database:** Cleaned — all transactional data wiped; lookup data preserved

---

## 1. Overview

### 1.1 Purpose
This guide provides step-by-step instructions for manually testing the Legal Module in the browser. It covers all major SRS-defined features: Governance Structure, Meeting Governance, Determinations & Approvals, Litigation (FCC Sued and FCC Suing), and the Public Register. Each flow specifies the user role performing the action, login credentials, navigation path, sample data, and expected outcome.

### 1.2 Scope

| Module Area | SRS Reference | Covered |
|---|---|---|
| Governance Structure (Committee Types, Governing Bodies, Members) | §2 | ✅ |
| Determinations & Approvals (Submissions) | §1 | ✅ |
| Meeting Governance (Meetings, Agenda, Participants, COI, Minutes, Directives, Resolutions) | §1.2 | ✅ |
| Litigation — FCC Sued (Cases, Filings, Hearings, Judgments, Settlements, Financials) | §4 | ✅ |
| Litigation — FCC Suing (Breach Reports, Cases, Filings, Hearings, Judgments, Settlements) | §5 | ✅ |
| Public Register | §3 | ✅ |
| Litigation Tasks (TaskLitigation) | §4.10 | ✅ |
| Legal Notices (LegalNotice) | §4.11 | ✅ |
| Case Hold / Resume / Archive | §4.12 | ✅ |
| Appeals (Defendant & Plaintiff) | §4.8 | ✅ |
| Meeting Cancel / Postpone / Reschedule | §1.2.3 | ✅ |

### 1.3 Prerequisites
- All services running: `dps` to verify
- Legal roles, users, and permissions provisioned via the setup script in `grc_notes.md §14`
- Admin user (`admin@fcc.go.tz`) usable for committee type and governing body seeding
- Base URL: `http://localhost:3001`

---

## 2. Test Users

> **Password for all legal test users:** `Pass@1234`
> **Admin password:** `admin123`

| # | Email | Name | Role | Key Capabilities |
|---|---|---|---|---|
| 1 | `admin@fcc.go.tz` | System Administrator | Superuser | Configure committee types, governing bodies, members |
| 2 | `legalmanager@fcc.go.tz` | Sarah Mkapa | Legal Manager | All legal permissions — cases, filings, approvals, closures |
| 3 | `legalofficer@fcc.go.tz` | Peter Mushi | Legal Officer | Cases CRUD, filings, hearings, settlements, judgments, appeals, notices, directives |
| 4 | `secretary@fcc.go.tz` | Anna Mollel | Committee Secretary | Governing bodies, meetings, minutes, directives |
| 5 | `chair@fcc.go.tz` | Joseph Massawe | Committee Chair | Approve meetings, approve minutes, view directives |
| 6 | `dg@fcc.go.tz` | James Ndonga | Director General | Review cases, issue litigation directives, approve filings/settlements/closures |

> **Note:** The DG user (`dg@fcc.go.tz`) was created during the Internal Audit setup (`grc_notes.md §7`). No new user is needed — they share the same account. Their Legal Manager must have the `legal_manager` role which includes `grc:legal_case:close` and `grc:legal_filing:approve` and `grc:legal_settlement:approve`.

---

## 3. Sample Data

### 3.1 Committee Types (Pre-configure as Admin)

| # | Name | Description |
|---|---|---|
| 1 | `Management Committee` | Senior management body for policy and strategic decisions |
| 2 | `Audit & Risk Committee` | Oversight committee for audit and risk management |
| 3 | `Procurement Committee` | Evaluates and approves procurement decisions |
| 4 | `Full Commission` | The full Commission of FCC — highest decision-making body |

### 3.2 Governing Bodies

| # | Name | Type | Secretary |
|---|---|---|---|
| 1 | `FCC Management Committee` | Management Committee | `secretary@fcc.go.tz` (Anna Mollel) |
| 2 | `FCC Full Commission` | Full Commission | `secretary@fcc.go.tz` (Anna Mollel) |

### 3.3 Members (for FCC Management Committee)

| # | User / Name | Position | Member Type |
|---|---|---|---|
| 1 | `legalmanager@fcc.go.tz` (Sarah Mkapa) | Chairman | Committee Member |
| 2 | `dg@fcc.go.tz` (James Ndonga) | Member | Management Member |
| 3 | `chair@fcc.go.tz` (Joseph Massawe) | Member | Committee Member |

### 3.4 Submissions for Determination

| # | Title | Description | Target Body |
|---|---|---|---|
| 1 | `Approval of Q1 2025/2026 Procurement Plan` | Request for formal determination of the procurement plan | FCC Management Committee |
| 2 | `Review of ICT Infrastructure Contract` | Determination on renewal of ICT maintenance contract | FCC Management Committee |
| 3 | `Approval of Staff Disciplinary Policy` | New staff disciplinary policy requiring commission determination | FCC Full Commission |

### 3.5 Meeting (Governance)

| Field | Value |
|---|---|
| **Title** | `FCC Management Committee — Q1 Ordinary Meeting` |
| **Governing Body** | `FCC Management Committee` |
| **Type** | `Ordinary` |
| **Mode** | `Physical` |
| **Location** | `FCC Conference Room, Samora Ave, Dar es Salaam` |
| **Start Date/Time** | `2026-04-10 09:00` |
| **End Date/Time** | `2026-04-10 13:00` |
| **Secretary** | `Anna Mollel` |

### 3.6 FCC Sued Cases

| Field | Case 1 | Case 2 |
|---|---|---|
| **Court Case Number** | `HC-CV-2025-001` | `HC-CV-2025-088` |
| **Court Registry** | `High Court of Tanzania — Commercial Division` | `High Court of Tanzania — Main Registry` |
| **Court Level** | `High Court` | `High Court` |
| **Service Date** | `2025-09-15` | `2025-11-03` |
| **Plaintiff Name** | `Julius Makwelo` | `Coastal Telecom Ltd` |
| **Plaintiff Advocate** | `Adv. Peter Kimani` | `Adv. Ruth Ochieng` |
| **Claim Amount** | `TZS 250,000,000` | `TZS 1,500,000,000` |
| **Nature of Claim** | `Unlawful termination of spectrum licence` | `Loss of business due to delayed frequency allocation` |
| **Department Affected** | `Spectrum Management` | `Licensing` |
| **Urgency Level** | `High` | `Critical` |
| **Risk Level** | `High` | `Very High` |

### 3.7 FCC Suing Cases

| Field | Case 1 (Breach Report — Simplified) | Case 2 (Full Registration) |
|---|---|---|
| **Reporting Department** | `Compliance & Enforcement` | `Legal Department` |
| **Nature of Breach** | `Broadcasting without a valid licence` | `Failure to pay spectrum fees — repeated non-compliance` |
| **Respondent Name** | `Star Radio Tanzania Ltd` | `NextWave Communications Ltd` |
| **Respondent Type** | `Company` | `Company` |
| **Estimated Claim Amount** | *(simplified — optional)* | `TZS 800,000,000` |
| **Risk Level** | *(simplified — optional)* | `High` |
| **Urgency Level** | `High` | `High` |
| **Description** | `Star Radio Tanzania Ltd has been broadcasting on FM frequency 101.5 MHz without a valid broadcasting licence since January 2025. Multiple notices issued but no compliance.` | `NextWave Communications Ltd has defaulted on spectrum fee payments for 3 consecutive quarters (Q1–Q3 2025/2026) totalling TZS 800 million. Court enforcement necessary.` |

### 3.8 Filing Sample Data

| Field | Value |
|---|---|
| **Type** | `Statement of Defence` (for FCC Sued) / `Plaint` (for FCC Suing) |
| **Title** | `Statement of Defence — HC-CV-2025-001 Julius Makwelo` |
| **Version** | `1.0` |

### 3.9 Hearing Sample Data

| Field | Value |
|---|---|
| **Hearing Date** | `2026-04-22` |
| **Court** | `High Court of Tanzania — Commercial Division` |
| **Judge** | `Hon. Justice Mary Kisanga` |
| **Notes** | `Preliminary hearing for defence submissions. Parties instructed to file written submissions within 21 days.` |

### 3.10 Judgment Sample Data

| Field | Won Scenario | Lost Scenario |
|---|---|---|
| **Judgment Date** | `2026-05-15` | `2026-05-20` |
| **Outcome** | `Won` | `Lost` |
| **Amount Awarded** | `TZS 0` | `TZS 180,000,000` |
| **Legal Costs Awarded** | `TZS 5,000,000` | `TZS 12,000,000` |
| **Remarks** | `Court upheld FCC's defence. Claim dismissed in its entirety.` | `Court ruled in favour of plaintiff. FCC to pay damages within 60 days.` |

### 3.11 Settlement Sample Data

| Field | Value |
|---|---|
| **Settlement Date** | `2026-04-30` |
| **Terms** | `FCC and Coastal Telecom Ltd agree to settle all claims. FCC to issue revised frequency allocation within 30 days. Coastal Telecom withdraws all monetary claims.` |
| **Payment Amount** | `TZS 0` |
| **Status** | `Proposed` |

### 3.12 Minutes Sample Data

| Field | Value |
|---|---|
| **Title** | `Minutes — FCC Management Committee Q1 Ordinary Meeting — 10 April 2026` |
| **Content** | `1. Opening and confirmation of quorum. The Secretary confirmed quorum was met with 3 of 3 members present. 2. Approval of previous minutes. Minutes of the previous meeting were approved unanimously. 3. Agenda items discussed and determinations made. 4. Any other business. Next meeting scheduled for July 2026. 5. Closure.` |

### 3.13 Public Decision Sample Data

| Field | Value |
|---|---|
| **Title** | `Decision — Approval of Q1 2025/2026 Procurement Plan` |
| **Body Text** | `The FCC Management Committee, having reviewed the Q1 Procurement Plan at its meeting of 10 April 2026, hereby determines as follows:` |
| **Decision Text** | `The Q1 2025/2026 Procurement Plan is approved as presented. The Procurement Unit is directed to proceed with implementation in accordance with the Public Procurement Act, 2011.` |
| **Decision Date** | `2026-04-10` |

### 3.14 Litigation Task Sample Data

| Field | Value |
|---|---|
| **Title** | `File Preliminary Objection Response` |
| **Description** | `Prepare and file FCC's response to plaintiff's preliminary objection by the court-ordered deadline.` |
| **Priority** | `High` |
| **Due Date** | `2026-05-10` |
| **Assigned To** | `Peter Mushi` (`legalofficer@fcc.go.tz`) |
| **Status** | `Open` (auto) |

### 3.15 Legal Notice Sample Data

| Field | Value |
|---|---|
| **Notice Type** | `Demand Notice` |
| **Title** | `Demand Notice — Star Radio Tanzania Ltd — Licence Compliance` |
| **Content** | `Take notice that Star Radio Tanzania Ltd is in breach of the Electronic and Postal Communications Act by operating without a valid broadcasting licence. FCC hereby demands immediate cessation of unlicensed operations and payment of prescribed administrative penalties.` |
| **Issued Date** | `2026-03-01` |
| **Served Date** | `2026-03-05` |
| **Recipient Info** | `Star Radio Tanzania Ltd, P.O. Box 12345, Dar es Salaam` |

---

## 4. Test Flows

---

### PART A: Governance Structure Setup

---

#### Flow 1: Configure Committee Types (Admin)

**User:** System Administrator (`admin@fcc.go.tz`)

**Steps:**
1. Log in as `admin@fcc.go.tz` / `admin123`
2. Navigate to `http://localhost:3001/service/grc/legal/committee-types`
3. Click **"Add Committee Type"** (or the **+** button)
4. Enter data:
   - **Name:** `Management Committee`
   - **Description:** `Senior management body for policy and strategic decisions`
   - **Status:** `Active`
5. Click **Save / Submit**
6. Repeat for the remaining 3 committee types:
   - `Audit & Risk Committee` — `Oversight committee for audit and risk management`
   - `Procurement Committee` — `Evaluates and approves procurement decisions`
   - `Full Commission` — `The full Commission of FCC — highest decision-making body`

**Expected Result:**
- All 4 committee types appear in the list with status `Active`
- Each type shows Name, Description, Status, and action buttons

---

#### Flow 2: Create a Governing Body (Admin)

**User:** System Administrator (`admin@fcc.go.tz`)

**Steps:**
1. Log in as `admin@fcc.go.tz` / `admin123`
2. Navigate to `http://localhost:3001/service/grc/legal/governing-bodies`
3. Click **"Add Governing Body"**
4. Enter data:
   - **Name:** `FCC Management Committee`
   - **Type:** `Management Committee` (select from dropdown)
   - **Description:** `Senior management committee responsible for policy decisions and resource allocation`
   - **Secretary:** `Anna Mollel` (`secretary@fcc.go.tz`)
   - **Status:** `Active`
5. Click **Save**
6. Repeat for `FCC Full Commission`:
   - **Name:** `FCC Full Commission`
   - **Type:** `Full Commission`
   - **Description:** `The highest decision-making body of FCC. Reviews strategic and regulatory matters.`
   - **Secretary:** `Anna Mollel` (`secretary@fcc.go.tz`)

**Expected Result:**
- Both governing bodies appear in the list
- Clicking a body opens its detail page showing name, type, secretary, and status
- Members section is empty (pending Flow 3)

---

#### Flow 3: Add Members to Governing Body (Admin)

**User:** System Administrator (`admin@fcc.go.tz`)

**Steps:**
1. Log in as `admin@fcc.go.tz` / `admin123`
2. Navigate to `http://localhost:3001/service/grc/legal/governing-bodies`
3. Click on **FCC Management Committee** to open its detail page
4. Scroll to the **Members** section → click **"Add Member"**
5. Add first member:
   - **User:** `Sarah Mkapa` (`legalmanager@fcc.go.tz`)
   - **Position:** `Chairman`
   - **Member Type:** `Committee Member`
   - **Joined Date:** `2025-01-01`
6. Add second member:
   - **User:** `James Ndonga` (`dg@fcc.go.tz`)
   - **Position:** `Member`
   - **Member Type:** `Management Member`
   - **Joined Date:** `2025-01-01`
7. Add third member:
   - **User:** `Joseph Massawe` (`chair@fcc.go.tz`)
   - **Position:** `Member`
   - **Member Type:** `Committee Member`
   - **Joined Date:** `2025-01-01`

**Expected Result:**
- Governing body detail page shows 3 active members in the Members section
- Each member displays name, position, member type, and joined date

---

### PART B: Determinations & Approvals

---

#### Flow 4: Create a Submission for Determination (Legal Officer)

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/submissions`
3. Click **"New Submission"** (or **+** button)
4. Enter data:
   - **Title:** `Approval of Q1 2025/2026 Procurement Plan`
   - **Description:** `Request for formal determination of the FCC Q1 Procurement Plan as required by the Public Procurement Act`
   - **Target Governing Body:** `FCC Management Committee`
5. Upload a supporting document (any PDF file)
6. Click **Submit**

**Expected Result:**
- Submission appears in the list with status `SUBMITTED`
- Submission detail page shows title, description, target body, submitter, submission date, and supporting documents
- Status badge shows `Submitted`

---

#### Flow 5: View and Edit a Pending Submission (Legal Officer)

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/submissions`
3. Locate the submission `Approval of Q1 2025/2026 Procurement Plan`
4. Click the **⋮ (action menu)** → **Edit**
5. Update description to: `Request for formal determination of the FCC Q1 2025/2026 Procurement Plan. Estimated value: TZS 2.4 billion. Procurement method: Open Competitive Tender.`
6. Click **Save**

**Expected Result:**
- Submission is updated with the new description
- Status remains `SUBMITTED` (not yet linked to a meeting)

> **Business Rule:** Submissions can only be edited/withdrawn by the originator until they are linked to a meeting agenda.

---

#### Flow 5b: Withdraw a Pending Submission (Legal Officer)

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

> **Precondition:** The submission must NOT yet be linked to a meeting agenda (status: `SUBMITTED`). Withdrawal is blocked once linked.

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/submissions`
3. Locate the submission `Approval of Staff Disciplinary Policy` (status: `SUBMITTED`)
4. Click the **⋮ (action menu)** → **"Withdraw"**
5. Confirm the withdrawal in the dialog

**Expected Result:**
- Submission status changes to `WITHDRAWN`
- Submission becomes read-only and cannot be added to any future meeting agenda
- Activity log records withdrawal with user and timestamp
- Attempting to add this submission to an agenda now yields a validation error

---

### PART C: Meeting Governance

---

#### Flow 6: Schedule a Meeting (Committee Secretary)

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/meetings`
3. Click **"Schedule Meeting"** (or **+** button)
4. Enter data:
   - **Title (Type):** `FCC Management Committee — Q1 Ordinary Meeting`
   - **Governing Body:** `FCC Management Committee`
   - **Meeting Type:** `Ordinary`
   - **Mode:** `Physical`
   - **Location:** `FCC Conference Room, Samora Ave, Dar es Salaam`
   - **Start Date/Time:** `2026-04-10 09:00`
   - **End Date/Time:** `2026-04-10 13:00`
5. Click **Save**

**Expected Result:**
- Meeting is created with an auto-generated **Meeting Number** (e.g. `MC/2025-2026/001`)
- Status is `DRAFT`
- Members section is auto-populated with all 3 active members of the FCC Management Committee
- Meeting detail page shows all fields, members section, and agenda section empty

---

#### Flow 7: Register Meeting and Send Invitations (Committee Secretary)

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/meetings`
3. Open the meeting `FCC Management Committee — Q1 Ordinary Meeting`
4. Click **"Register Meeting"** (status: `DRAFT` → `REGISTERED`)
5. After registration, click **"Send Invitations"** (status: `REGISTERED` → `INVITATIONS_SENT`)

**Expected Result:**
- Status changes to `INVITATIONS_SENT`
- All 3 members receive invitation notifications
- Invitation Status for each member shows `Pending`

---

#### Flow 8: Accept (or Decline) a Meeting Invitation (Member — Legal Manager)

**User:** Legal Manager (`legalmanager@fcc.go.tz`) — acting as Chairman/Member

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/meetings`
3. Find the meeting invitation or navigate to the meeting detail
4. In the **Participants** section, locate the row for `Sarah Mkapa`
5. Click **"Accept"** to accept the invitation

**Repeat for the other two members:**
- Log in as `dg@fcc.go.tz` → Accept invitation
- Log in as `chair@fcc.go.tz` → Accept invitation

**Expected Result:**
- All 3 members show `InvitationStatus: Accepted`
- System calculates quorum: `3/3 = 100% ≥ 51%` → `QuorumMet = true`
- Meeting status can proceed to `AGENDA_SHARED`

**Alternative: Decline an Invitation (edge path)**

To test the decline flow (re-accept afterwards to restore quorum):
1. Log in as `chair@fcc.go.tz` / `Pass@1234`
2. Open the meeting and find the participant row for Joseph Massawe
3. Click **"Decline"** instead of "Accept"
4. Enter decline reason: `Unavailable due to travel commitments on 10 April 2026`
5. Click **Confirm**

**Expected Result (Decline):**
- Invitation status changes to `Declined` for that member
- Quorum count decreases; if quorum falls below 51%, meeting cannot be started
- Secretary receives a notification of the decline
- Re-accept by clicking **"Accept"** to restore quorum before continuing subsequent flows

---

#### Flow 9: Build Agenda — Add Submission to Meeting (Committee Secretary)

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/meetings`
3. Open the meeting `FCC Management Committee — Q1 Ordinary Meeting`
4. In the **Agenda** section, click **"Add Agenda Item"**
5. Select from pending submissions:
   - `Approval of Q1 2025/2026 Procurement Plan`
   - `Review of ICT Infrastructure Contract`
6. Set agenda order (1, 2)
7. Click **"Share Agenda"** (status: `INVITATIONS_SENT` → `AGENDA_SHARED`)

**Expected Result:**
- Both submissions appear as agenda items with their order
- Submissions' status changes to `UNDER_REVIEW`
- Meeting status becomes `AGENDA_SHARED`

---

#### Flow 10: Declare Conflict of Interest (Member)

**User:** Legal Manager (`legalmanager@fcc.go.tz`)

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/meetings`
3. Open the `FCC Management Committee — Q1 Ordinary Meeting`
4. In the **Agenda** section, find `Review of ICT Infrastructure Contract`
5. Click **"Declare Conflict of Interest"** on that agenda item

**Expected Result:**
- Conflict declaration is recorded against Sarah Mkapa for that agenda item
- System notes this member will be excluded from determination on that item
- Other members can still vote/determine on the item

---

#### Flow 11: Mark Quorum Ready and Start Meeting (Committee Secretary)

**User:** Committee Secretary (`secretary@fcc.go.tz`)

> **Meeting status path:** `AGENDA_SHARED` → `QUORUM_READY` → `ONGOING`
> **"Mark Quorum Ready"** is a mandatory explicit step — the system does not auto-transition.

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/meetings`
3. Open the meeting
4. Verify: All members show `Accepted` and `QuorumMet = true` is displayed
5. Click **"Mark Quorum Ready"** (status: `AGENDA_SHARED` → `QUORUM_READY`)
6. Click **"Start Meeting"** (status: `QUORUM_READY` → `ONGOING`)

**Expected Result:**
- After step 5: Status becomes `QUORUM_READY`
- After step 6: Status changes to `ONGOING`
- Secretary can now add directives, record outcomes, and manage the live meeting
- Conflict-of-interest badge appears on affected agenda items

---

#### Flow 12: Record Agenda Outcomes and Add Directive (Committee Secretary)

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Navigate to meeting detail of the ongoing meeting
3. In the **Agenda** section, click on `Approval of Q1 2025/2026 Procurement Plan`
4. Record outcome:
   - **Outcome:** `Approved`
   - **Notes:** `Procurement plan approved unanimously by Management Committee. Proceed with tender process.`
5. Click **"Save Outcome"**
6. Add a directive to this agenda item:
   - **Description:** `Procurement Unit to publish tender document by 30 April 2026`
   - **Assigned To (Org Unit):** `Procurement Unit`
   - **Priority:** `High`
   - **Due Date:** `2026-04-30`
7. Click **"Add Directive"**

**Expected Result:**
- Agenda item shows `Outcome: Approved`
- Original submission status updates to `DETERMINED` (Approved)
- A new `Directive` is created and linked to the agenda item with status `Open`
- Directive appears in the directives list

---

#### Flow 12b: Populate Matters Arising in a New Meeting (Committee Secretary)

> **Context:** At the start of a subsequent meeting, the Secretary must populate the Matters Arising section with any open/unresolved directives from previous meetings of the same governing body.

**Precondition:** Flow 12 completed — at least one open directive exists. A second meeting has been scheduled.

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Create a second meeting: `FCC Management Committee — Q2 Ordinary Meeting` scheduled for `2026-07-10 09:00`
3. Register and send invitations for the new meeting
4. Open the new meeting detail
5. Click **"Populate Matters Arising"**
6. The system queries all open/unresolved directives from prior meetings of `FCC Management Committee`

**Expected Result:**
- Open directives from the Q1 meeting appear in the **Matters Arising** section of the Q2 meeting
- Each directive shows: original agenda item, assignee, due date, current status, and completion evidence (if any)
- The Secretary can now review and finally close completed directives (see Flow 15b)

---

#### Flow 13: Close Meeting and Draft Minutes (Committee Secretary)

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Navigate to meeting detail of the ongoing meeting
3. Click **"Close Meeting"** (status: `ONGOING` → `CLOSED`)
4. Navigate to `http://localhost:3001/service/grc/legal/minutes`
5. Click **"New Minutes"**
6. Enter data:
   - **Meeting:** `FCC Management Committee — Q1 Ordinary Meeting`
   - **Title:** `Minutes — FCC Management Committee Q1 Ordinary Meeting — 10 April 2026`
   - **Content:** *(use sample data from §3.12)*
   - **Status:** `Draft`
7. Click **Save**
8. Click **"Submit for Approval"** (status: `DRAFT` → `PENDING_APPROVAL`)

**Expected Result:**
- Meeting status changes to `CLOSED`. No further actions allowed.
- Minutes record created with status `PENDING_APPROVAL`
- Members who participated receive notification to approve minutes

---

#### Flow 14: Approve Minutes (Committee Chair)

**User:** Committee Chair (`chair@fcc.go.tz`)

**Steps:**
1. Log in as `chair@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/minutes`
3. Find `Minutes — FCC Management Committee Q1 Ordinary Meeting`
4. Click on the minutes record to open detail
5. Click **"Approve"**

**Expected Result:**
- Minutes status changes from `PENDING_APPROVAL` → `APPROVED`
- Minutes are finalised and read-only
- Approval record shows Joseph Massawe's name and timestamp

---

#### Flow 15: Close a Directive (Assigned User)

**User:** Legal Manager (`legalmanager@fcc.go.tz`) — as directive assignee

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/meeting-directives`
3. Find the directive: `Procurement Unit to publish tender document by 30 April 2026`
4. Click on the directive to open its detail page
5. Click **"Update Status"** → Set to `In Progress`
6. Click **"Close Directive"**
7. Enter completion summary: `Tender document published on PPRA portal on 28 April 2026. Accessible at https://ppra.go.tz.`
8. Attach completion evidence (any document)
9. Click **Submit**

**Expected Result:**
- Directive status changes to `Closed`
- Completion summary and date recorded
- Evidence document attached
- Directive remains in the list for Secretary to finally close it in next meeting's Matters Arising

---

#### Flow 15b: Finally Close a Directive via Matters Arising (Committee Secretary)

> **Context:** After the assignee closes a directive (Flow 15), it persists in the Matters Arising of subsequent meetings until the Secretary records final closure. This is a separate and required step.

**Precondition:** Flow 15 completed (directive closed by assignee). Flow 12b completed (Matters Arising populated for Q2 meeting).

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Open the Q2 meeting (`FCC Management Committee — Q2 Ordinary Meeting`) that is now `ONGOING`
3. In the **Matters Arising** section, locate: `Procurement Unit to publish tender document by 30 April 2026`
4. Verify its status shows `Closed` (by assignee, awaiting final Secretary closure)
5. Click **"Finally Close"** on the directive
6. The system records the final closure and links it to this meeting
7. Click **Confirm**

**Expected Result:**
- Directive status changes from `Closed` → `Fully Closed`
- Final closure time, Secretary user, and the Q2 meeting ID are all recorded
- Directive no longer appears in future meetings' Matters Arising sections
- Directive detail shows both: "Closed by [assignee] on [date]" and "Finally closed by [Secretary] at [Q2 meeting]"

---

### PART D: Litigation — FCC Sued

---

#### Flow 16: Register a FCC Sued Case (Legal Officer)

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Click **"Register Case"** (or **+** button)
4. Enter data:
   - **Court Case Number:** `HC-CV-2025-001`
   - **Court Registry:** `High Court of Tanzania — Commercial Division`
   - **Court Level:** `High Court`
   - **Service Date:** `2025-09-15`
   - **Plaintiff Name:** `Julius Makwelo`
   - **Plaintiff Advocate:** `Adv. Peter Kimani`
   - **Claim Amount:** `250000000`
   - **Nature of Claim:** `Unlawful termination of spectrum licence`
   - **Department Affected:** `Spectrum Management`
   - **Urgency Level:** `High`
   - **Risk Level:** `High`
5. Upload at least one initiation document (any PDF)
6. Click **Submit / Register**

**Expected Result:**
- Case created with auto-generated reference: `FCC/SUED/2025/001`
- Stage: `New`
- Case list shows: Case Ref No, Respondent (Julius Makwelo), Court, Claim Amount, Stage, Status
- Case detail page shows all tabs: Overview, Filings, Responses, Hearings, Judgment, Settlement, Financials, Tasks, Activity Log, Report

---

#### Flow 17: Assign Case to Legal Officers (Legal Manager)

**User:** Legal Manager (`legalmanager@fcc.go.tz`)

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Open case `FCC/SUED/2025/001`
4. In the case detail, click **"Assign Legal Officers"** (or edit assignment field)
5. Assign: `Peter Mushi` (`legalofficer@fcc.go.tz`)
6. Assign self (Sarah Mkapa) as **Legal Manager**
7. Click **Save**

**Expected Result:**
- Case shows assigned legal officer and legal manager
- Assigned users see the case in their assigned cases view

---

#### Flow 18: Submit a Court Filing (Legal Officer → Legal Manager → DG)

**User starts:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to case `FCC/SUED/2025/001`
3. Open the **Filings** tab
4. Click **"New Filing"**
5. Enter data:
   - **Type:** `Statement of Defence`
   - **Title:** `Statement of Defence — HC-CV-2025-001 Julius Makwelo v FCC`
   - **Version:** `1.0`
6. Upload document (any PDF)
7. Click **Save** — status: `DRAFT`
8. Click **"Submit for Review"** — status: `DRAFT` → `UNDER_REVIEW_LM`

**Legal Manager Review:**

9. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
10. Navigate to case `FCC/SUED/2025/001` → **Filings** tab
11. Find filing with status `UNDER_REVIEW_LM`
12. Click **"Review"** → **"Approve"** — status: `APPROVED_LM` → `UNDER_REVIEW_DG`

**DG Review:**

13. Log in as `dg@fcc.go.tz` / `Pass@1234`
14. Navigate to case `FCC/SUED/2025/001` → **Filings** tab
15. Find filing with status `UNDER_REVIEW_DG`
16. Click **"Approve"** — status: `APPROVED`

**Mark as Filed:**

17. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
18. Navigate to the filing
19. Click **"Mark as Filed"**
20. Enter the required **Filed Date:** `2026-03-20`
21. Click **Confirm** — status: `APPROVED` → `FILED`

**Expected Result:**
- Filing progresses through all 5 stages of the approval chain
- Each approval notifies the next actor
- Final status: `FILED`
- Activity log shows all transitions with user and timestamp

---

#### Flow 19: Record a Hearing and Hearing Report (Legal Officer)

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to case `FCC/SUED/2025/001`
3. Click the **Hearings** tab
4. Click **"Add Hearing"**
5. Enter data:
   - **Hearing Date:** `2026-04-22`
   - **Court:** `High Court of Tanzania — Commercial Division`
   - **Judge:** `Hon. Justice Mary Kisanga`
   - **Notes:** `Preliminary hearing for defence submissions. Parties instructed to file written submissions within 21 days.`
6. Click **Save**
7. On the hearing record, click **"Add Hearing Report"**
8. Enter data:
   - **Report Type:** `Proceedings`
   - **Summary:** `FCC legal team filed statement of defence. Judge reviewed jurisdiction objection raised by plaintiff's counsel. Will rule on objection at next hearing.`
   - **Remarks:** `Next hearing set for 15 May 2026`
   - **Next Hearing Date:** `2026-05-15`
9. Upload report document (any PDF)
10. Click **Save**

**Expected Result:**
- Hearing record appears in the Hearings tab
- Hearing report linked to the hearing
- Case `NextHearingDate` updates to `2026-05-15`
- Activity log records the hearing addition

---

#### Flow 20: Record a Plaintiff Response (Legal Officer)

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to case `FCC/SUED/2025/001`
3. Click the **Responses** tab (documents received from plaintiff)
4. Click **"Add Response"**
5. Enter data:
   - **Type:** `Preliminary Objections`
   - **Received Date:** `2025-10-01`
   - **Description:** `Plaintiff filed preliminary objections challenging FCC's jurisdiction in spectrum matters.`
6. Upload document (any PDF)
7. Click **Save**

**Expected Result:**
- Response record appears in the Responses tab
- Linked to the case; activity log updated

---

#### Flow 21: Record a Judgment and DG Decision (Legal Manager + DG)

**User:** Legal Officer (`legalofficer@fcc.go.tz`) then Legal Manager then DG

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to case `FCC/SUED/2025/001` → **Judgment** tab
3. Click **"Record Judgment"**
4. Enter data:
   - **Judgment Date:** `2026-05-15`
   - **Outcome:** `Won`
   - **Amount Awarded:** `0`
   - **Legal Costs Awarded:** `5000000`
   - **Remarks:** `Court upheld FCC's defence. Claim dismissed in its entirety. Plaintiff to bear costs.`
5. Upload judgment document
6. Click **Save**
7. Click **"Submit for DG Review"** — submits the judgment for review

**Legal Manager Recommendation:**

8. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
9. Navigate to the judgment record
10. Click **"Recommend to DG"** (adds review notes and forwards to DG)

**DG Decision:**

11. Log in as `dg@fcc.go.tz` / `Pass@1234`
12. Navigate to case `FCC/SUED/2025/001` → **Judgment** tab
13. Click **"Accept"** (DG Decision: Accept — no appeal)

**Expected Result:**
- Judgment recorded with Outcome: `Won`
- DG Decision: `Accept`
- Case stage advances (no appeal filing needed)
- Financial tab shows: Costs Awarded: `TZS 5,000,000`

---

#### Flow 22: Record and Approve a Settlement (Legal Officer → Legal Manager → DG)

**User starts:** Legal Officer (`legalofficer@fcc.go.tz`)

> *Use Case 2 — HC-CV-2025-088 (Coastal Telecom) for this settlement flow.*

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Register Case 2 first (repeat Flow 16 using Coastal Telecom data from §3.6)
3. Navigate to `FCC/SUED/2025/002` → **Settlement** tab
4. Click **"Propose Settlement"**
5. Enter data:
   - **Settlement Date:** `2026-04-30`
   - **Terms:** `FCC and Coastal Telecom agree to settle. FCC to issue revised frequency allocation within 30 days. Coastal Telecom withdraws all monetary claims.`
   - **Payment Amount:** `0`
   - **Status:** `Proposed`
6. Upload settlement agreement document
7. Click **Save**
8. Click **"Submit for Approval"** — submits settlement to Legal Manager for review

**Legal Manager Review:**

9. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
10. Navigate to the settlement → Click **"Review Settlement"** → **"Recommend Approval"**

**DG Approval:**

11. Log in as `dg@fcc.go.tz` / `Pass@1234`
12. Navigate to the settlement → Click **"Approve Settlement"**
13. Settlement status changes to `Agreed`

**Expected Result:**
- Settlement progresses from `Proposed` → `Agreed` via LM review and DG approval
- Digital signature stamped on settlement document at time of DG approval
- Financial tab shows settlement terms; payment amount shown if non-zero

---

#### Flow 23: Issue a DG Litigation Directive (DG)

**User:** Director General (`dg@fcc.go.tz`)

**Steps:**
1. Log in as `dg@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Open case `FCC/SUED/2025/001`
4. Click **"DG Review"** or navigate to the DG review section
5. Click **"Issue Directive"**
6. Enter data:
   - **Instruction:** `Legal team to engage Adv. Kimani for mediation settlement before next hearing. Explore out-of-court resolution within 30 days.`
   - **Due Date:** `2026-05-15`
   - **Status:** `Open`
7. Click **Save**

> **Alternative:** Click **"Mark as Reviewed"** to record DG review without issuing a directive (see Flow 23b).

> **Note on Litigation Directives:** Each `LitigationDirective` created here has its own approval workflow:
> 1. After issuing, the directive may be in `draft` or `pending_dg_approval` state.
> 2. Submit for DG approval: click **"Submit for DG Approval"** on the directive record.
> 3. DG then approves or rejects: click **"Approve"** or **"Reject"** on the directive.
> The directive only becomes active/effective after DG approval.

**Expected Result:**
- Litigation directive created and linked to the case
- Case stage changes to `Directive Issued`
- `DGReviewStatus` = `Directive Issued`
- Activity log records DG action

---

#### Flow 23b: DG Marks Case as Reviewed — No Directive Issued (DG)

> **When to use:** DG has reviewed the case but determines no specific directive is required — legal team can proceed with standard strategy.

**User:** Director General (`dg@fcc.go.tz`)

**Steps:**
1. Log in as `dg@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Open a case in `Under DG Review` stage
4. Click **"Mark as Reviewed"** (instead of "Issue Directive")
5. Optionally enter review notes: `Case reviewed. No directive required at this stage. Legal team to proceed with standard defence strategy.`
6. Click **Confirm**

**Expected Result:**
- `DGReviewStatus` updated to `Reviewed`
- No `LitigationDirective` record is created
- Case stage advances past DG review without a directive
- Activity log records: DG marked case as reviewed, no directive issued

---

#### Flow 24: Initiate Case Closure (Legal Manager → DG)

**User:** Legal Manager (`legalmanager@fcc.go.tz`)

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Open case `FCC/SUED/2025/001`
4. Click **"Initiate Closure"** (case stage: `Judgment Received` or terminal)
5. Enter closure notes: `Case fully resolved. Judgment in favour of FCC. No outstanding appeals. All tasks completed. Recommend closure.`
6. Click **Submit for DG Approval**

**DG Approval:**

7. Log in as `dg@fcc.go.tz` / `Pass@1234`
8. Navigate to the case → Click **"Approve Closure"**

**Expected Result:**
- Case status becomes `Closed` and read-only
- No further modifications permitted
- Activity log records closure with DG approval timestamp

---

### PART E: Litigation — FCC Suing

---

#### Flow 25: Submit Breach Report (Simplified — Department User)

> Uses `legalofficer@fcc.go.tz` to simulate a Department User initiating an intake.

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-suing`
3. Click **"New Breach Report"** → Select **"Simplified Intake"**
4. Enter data:
   - **Reporting Department:** `Compliance & Enforcement`
   - **Nature of Breach:** `Broadcasting without a valid licence`
   - **Respondent Name:** `Star Radio Tanzania Ltd`
   - **Respondent Type:** `Company`
   - **Urgency Level:** `High`
   - **Description:** `Star Radio Tanzania Ltd has been broadcasting on FM 101.5 MHz without a valid broadcasting licence since January 2025. Multiple notices issued but no compliance.`
5. Optionally upload a supporting document
6. Click **Submit**

**Expected Result:**
- Case created with auto-generated reference: `FCC/SUING/2025/001`
- Stage: `New`
- Case appears in FCC Suing list with respondent name, breach type, urgency

---

#### Flow 25b: Create, Update, and Close a Litigation Task (Legal Officer)

> Litigation tasks are ad-hoc action items linked to a case for tracking specific activities (e.g., filing deadlines, court appearances).

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to case `FCC/SUED/2025/001`
3. Click the **Tasks** tab
4. Click **"New Task"**
5. Enter data (from §3.14):
   - **Title:** `File Preliminary Objection Response`
   - **Description:** `Prepare and file FCC's response to plaintiff's preliminary objection by the court-ordered deadline.`
   - **Priority:** `High`
   - **Due Date:** `2026-05-10`
   - **Assigned To:** `Peter Mushi` (`legalofficer@fcc.go.tz`)
6. Click **Save** — Task status: `Open`
7. Click **"Update Status"** → `In Progress`
8. When done, click **"Close Task"**:
   - Enter completion summary: `Response to preliminary objections filed on 8 May 2026. Copy submitted to court registry and plaintiff's counsel.`
   - Click **Submit**

**Expected Result:**
- Task created with status `Open`, linked to the case
- Status transitions: `Open` → `In Progress` → `Closed`
- Completion summary recorded with timestamp
- Overdue tasks (past their due date) appear in the overdue tasks list
- Activity log records task creation and closure

---

#### Flow 26: Register Full Breach Report (Legal Officer)

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-suing`
3. Click **"New Breach Report"** → Select **"Full Registration"**
4. Enter data:
   - **Reporting Department:** `Legal Department`
   - **Nature of Breach:** `Failure to pay spectrum fees — repeated non-compliance`
   - **Respondent Name:** `NextWave Communications Ltd`
   - **Respondent Type:** `Company`
   - **Estimated Claim Amount:** `800000000`
   - **Risk Level:** `High`
   - **Urgency Level:** `High`
   - **Description:** `NextWave Communications Ltd has defaulted on spectrum fee payments for 3 consecutive quarters totalling TZS 800 million.`
5. Upload at least one initiation document (demand notice PDF)
6. Click **Submit**

**Expected Result:**
- Case created with reference: `FCC/SUING/2025/002`
- Stage: `New`
- Dashboard KPI for `Recoverable Amount` reflects `TZS 800,000,000`

---

#### Flow 27: File a Plaint (FCC Suing — Filing Workflow)

**User:** Legal Officer → Legal Manager → DG → Legal Officer

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `FCC/SUING/2025/002` → **Filings** tab
3. Click **"New Filing"**
4. Enter data:
   - **Type:** `Plaint`
   - **Title:** `Plaint — NexWave Communications Ltd — Spectrum Fee Recovery`
   - **Version:** `1.0`
5. Upload plaint document (PDF)
6. Click **Save** → **"Submit for Review"**

> Follow the same two-stage approval as Flow 18 (LM → DG → Filed)

**Expected Result:**
- Filing goes through `DRAFT` → `UNDER_REVIEW_LM` → `APPROVED_LM` → `UNDER_REVIEW_DG` → `APPROVED` → `FILED`
- Each transition notifies the next actor

---

#### Flow 28: Record FCC Suing Judgment — Won Outcome with Recovery

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `FCC/SUING/2025/002` → **Judgment** tab
3. Click **"Record Judgment"**
4. Enter data:
   - **Judgment Date:** `2026-06-01`
   - **Outcome:** `Won`
   - **Amount Awarded:** `800000000`
   - **Legal Costs Awarded:** `15000000`
   - **Remarks:** `Court ruled in FCC's favour. NextWave ordered to pay TZS 800 million plus costs within 30 days.`
5. Upload judgment document
6. Click **Save**

**After DG Accept (repeat DG step from Flow 21):**

7. Navigate to **Financials** tab
8. Click **"Record Recovery"**
9. Enter data:
   - **Date:** `2026-07-01`
   - **Amount:** `800000000`
   - **Reference:** `Bank transfer ref TZS-2026-NW-001`
   - **Status:** `Requested`
10. Click **Save**

**Expected Result:**
- Judgment Outcome: `Won`
- Financials tab shows: Amount Awarded: `TZS 800M`, Recovery record added
- Dashboard KPI `Recovered Amount` updates once recovery is processed

---

#### Flow 28b: Record Payment When FCC Loses a Case (Legal Officer)

> When FCC **loses** a case, the Financial tab is used to record the court-ordered payment to the plaintiff.

**Precondition:** A FCC Sued case with a judgment **Outcome: Lost** (use the Lost scenario from §3.10, or create a separate test case).

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Record a judgment with **Outcome: Lost**, **Amount Awarded: `180000000`** for a FCC Sued case
2. After DG accepts the judgment, navigate to the **Financials** tab of that case
3. Click **"Record Payment"**
4. Enter data:
   - **Date:** `2026-06-15`
   - **Amount:** `180000000`
   - **Reference:** `Bank transfer TZS-2026-JM-002 (payment to Julius Makwelo per court order)`
5. Click **Save**

**Expected Result:**
- Financials tab shows: Court Order Amount: `TZS 180M`, Payment record added with reference and date
- Activity log records the payment action
- Dashboard KPI for liability reflects the payment entry

---

### PART F: Public Register

---

#### Flow 29: Publish a Public Decision (Committee Secretary)

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/resolution-register`
3. Verify `Approval of Q1 2025/2026 Procurement Plan` resolution exists (auto-created from the meeting outcome in Flow 12)
4. Navigate to `http://localhost:3001/service/grc/legal` (Legal Dashboard or Public Register link)
5. Navigate to **Public Register** (sidebar under Legal)
6. Click **"Add Decision"** → **"New Public Decision"**
7. Enter data:
   - **Title:** `Decision — Approval of Q1 2025/2026 Procurement Plan`
   - **Meeting:** `FCC Management Committee — Q1 Ordinary Meeting` (select from dropdown)
   - **Body Text:** `The FCC Management Committee, having reviewed the Q1 Procurement Plan at its meeting of 10 April 2026, hereby determines as follows:`
   - **Decision Text:** `The Q1 2025/2026 Procurement Plan is approved as presented. The Procurement Unit is directed to proceed with implementation in accordance with the Public Procurement Act, 2011.`
   - **Decision Date:** `2026-04-10`
8. Click **Save** (status: `DRAFT`)
9. Click **"Publish"** (status: `DRAFT` → `PUBLISHED`)

**Expected Result:**
- Decision created with status `PUBLISHED`
- Published date recorded
- Decision is visible in the Public Register list

---

### PART G: Edge Cases

---

#### Flow 30: Attempt to Edit a Submission Already Added to Meeting Agenda (Edge Case)

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/submissions`
3. Locate a submission with status `UNDER_REVIEW` (one added to the meeting agenda)
4. Click the **⋮ action menu** → Attempt to click **"Edit"**

**Expected Result:**
- Edit action is disabled or shows a warning: `"Submission cannot be edited once added to a meeting agenda"`
- No changes are saved

---

#### Flow 31: Attempt to Start Meeting Without Quorum (Edge Case)

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Steps:**
1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Create a new meeting for `FCC Full Commission` (no members added yet)
3. Register the meeting and send invitations
4. Attempt to click **"Start Meeting"** before any invitations are accepted

**Expected Result:**
- System blocks the start: `"Meeting cannot be started — quorum not met. At least 51% of members must accept invitations."`
- Status remains `INVITATIONS_SENT` or `AGENDA_SHARED`
- Secretary can reschedule (return to `REGISTERED`)

---

#### Flow 32: Appeal Filing After Lost Judgment (DG)

**User:** Director General (`dg@fcc.go.tz`)

**Steps:**
1. Record a judgment for any open FCC Sued case with **Outcome: Lost**
2. Log in as `dg@fcc.go.tz` / `Pass@1234`
3. Navigate to the judgment → Click **"DG Decision"** → Select **"Appeal"**
4. Set **Appeal Due Date:** `2026-06-30`
5. Click **Save**

**Expected Result:**
- DG Decision recorded as `Appeal`
- System auto-creates a filing of type `Notice of Appeal` linked to the case
- System auto-creates a task for the Legal Officer to file the appeal before the due date
- Case stage changes to `Appeal Filed`
- If appeal due date passes without the filing being marked as `FILED`, task status becomes `Overdue`

---

#### Flow 33: Directive Becomes Overdue (Edge Case)

**Steps:**
1. Create a directive with a past **Due Date** (e.g. `2026-01-01`)
2. Do NOT close the directive
3. Check the directive list

**Expected Result:**
- Directive status automatically changes to `Overdue`
- Notification sent to the assigned user and the Secretary
- Directive badge shows red `Overdue` indicator in the list

---

#### Flow 34: View Dashboard KPIs and Case List Filter (Legal Manager)

**User:** Legal Manager (`legalmanager@fcc.go.tz`)

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal`
3. Verify dashboard KPIs for FCC Sued:
   - `Total Cases Filed`
   - `Won/Loss Ratio`
   - `Cases on Appeal`
   - `High Risk Cases`
   - `Active Cases`
   - `Pending DG Review`
4. Navigate to FCC Sued Case List (`/service/grc/legal/fcc-sued`)
5. Apply filter: **Risk Level = Very High**
6. Verify filtered results
7. Apply global search: `Coastal Telecom`
8. Verify matching case appears

**Expected Result:**
- Dashboard KPIs show correct counts based on test data entered
- Filter returns only High Risk / Very High cases
- Search returns `FCC/SUED/2025/002` — Coastal Telecom Ltd

---

#### Flow 35: Place a Case On Hold and Resume (Legal Manager)

**User:** Legal Manager (`legalmanager@fcc.go.tz`)

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Open case `FCC/SUED/2025/001` (or any active case)
4. Click the **⋮ action menu** → **"Place On Hold"**
5. Enter hold reason: `Case activities suspended pending resolution of related administrative proceedings.`
6. Click **Confirm**

**Resume the case:**

7. Navigate back to the case (status now shows `On Hold`)
8. Click **"Resume Case"**
9. Select target status to resume to: `Hearing Stage` (or the last active stage before hold)
10. Click **Confirm**

**Expected Result:**
- After hold: Case status changes to `on_hold`; editing is frozen during hold
- After resume: Case status returns to the specified stage
- Activity log records both hold and resume with reasons and timestamps

---

#### Flow 36: Archive and Unarchive a Closed Case (Legal Manager)

**Precondition:** A case with status `Closed` (from Flow 24 or similar).

**User:** Legal Manager (`legalmanager@fcc.go.tz`)

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Open a case with status `Closed`
4. Click **"Archive Case"**
5. Confirm the archival

**Unarchive:**

6. Locate the archived case (may be under an "Archived" filter tab)
7. Click **"Unarchive Case"**
8. Confirm

**Expected Result:**
- After archival: Case removed from active list and visible only under Archived filter
- After unarchival: Case returns to the active list with its `Closed` status
- Activity log records both archive and unarchive operations

---

#### Flow 37: Create and Publish a Legal Notice (Legal Officer)

> Legal Notices are formal notices issued to external parties. They follow a `draft → published → acknowledged → expired` lifecycle.

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/notices`
3. Click **"New Legal Notice"**
4. Enter data (from §3.15):
   - **Notice Type:** `Demand Notice`
   - **Title:** `Demand Notice — Star Radio Tanzania Ltd — Licence Compliance`
   - **Content:** `Take notice that Star Radio Tanzania Ltd is in breach of the Electronic and Postal Communications Act by operating without a valid broadcasting licence. FCC hereby demands immediate cessation of unlicensed operations and payment of prescribed administrative penalties.`
   - **Issued Date:** `2026-03-01`
   - **Served Date:** `2026-03-05`
   - **Recipient Info:** `Star Radio Tanzania Ltd, P.O. Box 12345, Dar es Salaam`
5. Attach the formal notice PDF document
6. Click **Save** — status: `DRAFT`
7. Click **"Publish Notice"** — status: `DRAFT` → `PUBLISHED`

**Mark as Acknowledged:**

8. After confirming recipient received the notice, click **"Mark Acknowledged"** — status: `PUBLISHED` → `ACKNOWLEDGED`

**Expected Result:**
- Notice created and published successfully
- `Published` status confirms notice has been officially issued
- `Acknowledged` status confirms receipt by the recipient
- Activity log records all status transitions with actor and timestamp
- Notice links to the associated FCC Suing case (Star Radio Tanzania Ltd) if applicable

---

#### Flow 38: View Case Report Tab — Chronological Timeline (Legal Officer)

> The Report Tab provides an ordered log of all significant events in a case's lifecycle.

**User:** Legal Officer (`legalofficer@fcc.go.tz`)

**Steps:**
1. Log in as `legalofficer@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Open case `FCC/SUED/2025/001` (which has gone through multiple workflow steps)
4. Click the **Report** tab (last or penultimate tab in the case detail page)
5. Review the chronological timeline

**Expected Result:**
- Report tab displays events in reverse-chronological order (most recent first)
- Each event shows: event type, description, actor (user), and timestamp
- Expected events visible: Case registered, Filing submitted, LM approved, DG approved, Filing filed, Hearing added, Judgment recorded, DG accepted, Directive issued
- All actions from Flows 16–24 appear in the Report

---

#### Flow 39: Cancel, Postpone, and Reschedule a Meeting (Committee Secretary)

> Tests the alternative meeting lifecycle paths: cancellation, postponement, and rescheduling.

**User:** Committee Secretary (`secretary@fcc.go.tz`)

**Sub-flow 39a: Cancel a Meeting**

1. Log in as `secretary@fcc.go.tz` / `Pass@1234`
2. Create a new meeting for `FCC Full Commission` (any future date)
3. Register and send invitations
4. Click **"Cancel Meeting"** and confirm

**Expected Result (Cancel):**
- Meeting status changes to `CANCELLED`
- No further actions allowed; the meeting is read-only
- Members receive a cancellation notification

**Sub-flow 39b: Postpone an Ongoing Meeting**

1. Take a meeting through `ONGOING` status (Flows 6–11)
2. During the meeting, click **"Postpone Meeting"** and confirm

**Expected Result (Postpone):**
- Meeting status changes to `POSTPONED`
- The meeting can be rescheduled (see 39c)

**Sub-flow 39c: Reschedule a Postponed Meeting**

1. With a `POSTPONED` meeting, click **"Reschedule Meeting"**
2. Enter new details:
   - **New Start Date/Time:** `(any future date, e.g. 2026-08-10 09:00)`
   - **New End Date/Time:** `(same day + 4 hours)`
   - **Reason:** `Original date conflicted with board member travel schedules.`
3. Click **Save**

**Expected Result (Reschedule):**
- Meeting status changes to `RESCHEDULED`
- New scheduled dates are saved
- Activity log records rescheduling reason and actor

---

#### Flow 40: Verify FCC Suing Dashboard KPIs (Legal Manager)

**User:** Legal Manager (`legalmanager@fcc.go.tz`)

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal`
3. If the dashboard separates "FCC Sued" and "FCC Suing" sections, navigate to the **FCC Suing** metrics
4. Verify the following KPIs are displayed and have correct values:
   - `Total Active Cases` (should include Star Radio and NextWave cases)
   - `Recoverable Amount` (sum of claimed amounts across open FCC Suing cases — expected: at least `TZS 800,000,000` from Flow 26)
   - `Recovered Amount` (sum of recorded recoveries — expected: `TZS 800,000,000` after Flow 28)
   - `Won/Loss Ratio`
   - `Cases at Settlement Stage`
   - `High Risk Cases`
5. Cross-check values against test data entered in Flows 25–28

**Expected Result:**
- Dashboard KPIs reflect the FCC Suing test data
- `Recoverable Amount` ≥ `TZS 800,000,000` (from Flow 26)
- `Recovered Amount` = `TZS 800,000,000` after Flow 28
- Incorrect or zero values indicate a dashboard aggregation bug

---

#### Flow 41: View and Update an Appeal Record (Legal Manager)

> When DG selects "Appeal" as the judgment decision (Flow 32), the system auto-creates an `AppealDefendant` record. This flow tests viewing and updating that appeal record.

**Precondition:** Flow 32 completed — DG selected "Appeal" for a lost judgment; `AppealDefendant` record auto-created.

**User:** Legal Manager (`legalmanager@fcc.go.tz`)

**Steps:**
1. Log in as `legalmanager@fcc.go.tz` / `Pass@1234`
2. Navigate to `http://localhost:3001/service/grc/legal/fcc-sued`
3. Open the case that has been appealed (stage: `Appeal Filed`)
4. Locate the **Appeal** section in the case detail (tab or section)
5. Find the auto-created `Notice of Appeal` appeal record
6. Click **Edit** on the appeal record to update:
   - **Appeal Court:** `Court of Appeal of Tanzania`
   - **Appeal Filing Date:** `2026-06-20`
   - **Appeal Due Date:** `2026-06-30`
   - **Notes:** `Notice of Appeal filed on 20 June 2026. Appeal based on misapplication of the statutory mandate regarding spectrum licensing.`
7. Click **Save**

**Expected Result:**
- Appeal record updated with court name, dates, and notes
- Case detail reflects the current appeal stage
- Activity log records the update

---

## 5. Additional Notes

### 5.1 Login URL
All users must log in at: `http://localhost:3001/login`

Credentials:
- Admin: `admin@fcc.go.tz` / `admin123`
- All other test users: `<email>` / `Pass@1234`

### 5.2 Setup Dependency Order
The following sequence must be followed:

```
1. Admin → Create Committee Types (Flow 1)
2. Admin → Create Governing Bodies (Flow 2)
3. Admin → Add Members to Governing Bodies (Flow 3)
4. Legal Officer → Create Submissions (Flow 4)
5. Secretary → Schedule Meeting, Register, Send Invitations (Flows 6–7)
6. Members → Accept Invitations (Flow 8)
7. Secretary → Build Agenda, Share Agenda (Flow 9)
8. [Optional] Member → Declare Conflict of Interest (Flow 10)
9. Secretary → Start Meeting (Flow 11)
10. Secretary → Record Outcomes + Add Directives (Flow 12)
11. Secretary → Close Meeting + Draft Minutes (Flow 13)
12. Chair → Approve Minutes (Flow 14)
13. Secretary → Populate Matters Arising (Flow 12b) for next meeting
14. Secretary → Finally Close directives via Matters Arising (Flow 15b)
```

Litigation flows (16–28) are independent and can be tested in parallel with Governance flows.

### 5.3 Role Boundaries
| Action | Who CAN do it | Who CANNOT |
|---|---|---|
| Create Committee Types | Admin only | Legal Officer, Secretary |
| Create Governing Bodies | Admin only | Legal Officer, Secretary |
| Schedule Meetings | Committee Secretary | Legal Officer |
| Approve Minutes | Committee Chair | Committee Secretary |
| Register FCC Sued/Suing Case | Legal Officer, Legal Manager | Committee Secretary |
| Approve Filings (LM step) | Legal Manager | Legal Officer |
| Approve Filings (DG step) | DG only | Legal Manager |
| Close Case | DG approve required | Legal Officer cannot self-approve |
| Publish Public Decision | Committee Secretary | Legal Officer |
| Withdraw a Submission | Legal Officer (originator only) | Anyone else; originator once linked to agenda |
| Finally Close a Directive (Matters Arising) | Committee Secretary | Legal Officer, assignee |
| Approve Litigation Directives (DG step) | DG only | Legal Manager |
| Place Case On Hold | Legal Manager | Legal Officer |
| Archive / Unarchive a Closed Case | Legal Manager | Legal Officer |
| Create Legal Notices | Legal Officer, Legal Manager | Committee Secretary |
| Publish / Acknowledge Legal Notices | Legal Manager | Legal Officer |
| Mark Quorum Ready | Committee Secretary | Committee Chair |

### 5.4 Auto-Generated Reference Numbers
- FCC Sued cases: `FCC/SUED/YYYY/NNN` (e.g. `FCC/SUED/2025/001`)
- FCC Suing cases: `FCC/SUING/YYYY/NNN` (e.g. `FCC/SUING/2025/001`)
- Meeting Numbers: prefix-based per governing body (e.g. `MC/2025-2026/001`)

These are auto-generated by the system — do not enter them manually.

### 5.5 Document Attachments
Most entities accept document uploads. Use any small PDF or DOCX file for testing. Documents are stored in the Document Records Service (DRS). GRC only stores a UUID reference.

### 5.6 Known Constraints
- The quorum check is real-time: `(accepted members / total members) × 100 ≥ 51%`.
- A user can only initiate closure of a case if the case has no open tasks or overdue directives (depending on configuration).
- Directives issued during a meeting are not finally closed by the assignee's initial closure — they require the Secretary to finally close them in a subsequent meeting's Matters Arising. Until then, they appear in future meetings' Matters Arising section automatically.
- Digital signatures are applied at DG approval of filings and settlements — verify signature stamp on the downloaded document.
- The `admin@fcc.go.tz` superuser can access all module configuration pages. Regular legal roles will see 403 on configuration-only pages (committee types, governing bodies creation).

### 5.7 Resetting Test Data
To clear all Legal module transactional data for a fresh test run, use the Django shell in grc-service. See `grc_notes.md` for the shell access pattern.
