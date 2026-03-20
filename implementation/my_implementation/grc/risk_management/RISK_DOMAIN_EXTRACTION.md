# Risk Management Module — Domain Extraction

> **Source SRS:** `grc-service/implementation/my_implementation/grc/GRC_SRS/risk/RISK_MANAGEMENT.md`
> **Unit:** Risk Management and Quality Assurance Unit (RMQAU) — Fair Competition Commission (FCC)
> **Purpose:** Full domain analysis serving as the foundation for backend design.
> **Date:** 2026-03-19

---

## Table of Contents

1. [Core Business Domains](#a-core-business-domains)
2. [Main Entities](#b-main-entities)
3. [Key Workflows / Processes](#c-key-workflows--processes)
4. [Relationships Between Entities](#d-relationships-between-entities)
5. [Important Business Rules / Constraints](#e-important-business-rules--constraints)

---

## A. Core Business Domains

### 1. Risk Champion Management
Management of the full lifecycle of Risk Champions (RCs) — from nomination by Directorate/Unit/Zone Heads to formal appointment by the Director General. RCs serve as the frontline coordinators of risk management activities within their respective organisational units.

### 2. Risk Identification & Assessment
The structured process by which staff and Risk Champions identify potential risks, evaluate their likelihood and impact using designated Risk Assessment Sheets, and record them at departmental level. This forms the raw input for all downstream risk management processes.

### 3. Departmental Risk Register Development
Consolidation of risk assessment sheets at the Directorate/Unit/Zone level into an approved Departmental Risk Register. Involves meetings, review cycles, endorsement by Heads, and RMQAM approval.

### 4. Institutional Risk Register Preparation
Aggregation of all Departmental Risk Registers into a single Institutional Risk Register containing risks that exceed the organisation's risk appetite/threshold. Includes a workshop, consolidation by RMO, RMQAM review, Management discussion, and submission to the Risk and Governance Committee.

### 5. Risk Treatment & Control Planning
Development and documentation of mitigation controls in the Risk Treatment Action Plan (RTAP). Each risk that makes it into the Institutional Risk Register is paired with proposed controls, responsible officers, and implementation timelines.

### 6. Risk Monitoring & Quarterly Reporting
Ongoing, quarterly tracking of the implementation status of approved risk controls. Involves periodic reminders to RCs, consolidation of updates, comparative analysis by RMQAM, and formal reporting to Management, the Risk and Governance Committee, and the Commission.

### 7. Quality Auditor / Champion Appointment
Management of the full lifecycle of Quality Auditors (QAs) / Quality Champions (QCs) — from nomination, through mandatory ISO 9001:2015 training and certification examination (minimum 75% pass mark), to formal DG appointment.

### 8. QMS Audit Planning & Execution
The end-to-end process of planning, executing, and reporting on internal Quality Management System (QMS) audits in accordance with ISO 9001:2015 and ISO 19011:2018. Includes annual program creation, audit plan preparation, checklist development, field audit, report writing, Management Review Meeting (MRM), and corrective action follow-up.

### 9. Governance & Escalation
The multi-tiered governance chain through which all risk and quality assurance outputs are formally reviewed, approved, and acted upon: RMQAM → Management → Risk and Governance Committee → Commission. The Legal Service Manager (LSM) acts as the routing conduit above Management level.

---

## B. Main Entities

### Actors / Roles

#### 1. Risk Management and Quality Assurance Manager (RMQAM)
- **Role:** Primary process owner for all risk management and quality assurance activities.
- **Authority:** Reviews and approves risk registers, audit programs, audit plans, appointment letters, and performance reports before submission to higher governance.
- **Scope:** Sits at the top of operational execution; all submissions from RMO and RCs flow through RMQAM.

#### 2. Risk Management Officer (RMO)
- **Role:** Operational executor under RMQAM.
- **Responsibilities:** Draft appointment letters, send notifications, consolidate risk data, prepare reports, coordinate workshops, distribute audit plans.
- **Sub-role:** PRMO (Principal / Senior RMO) handles trainer engagement for ISO training.

#### 3. Risk Champion (RC)
- **Role:** Designated coordinator of risk management activities within one Directorate/Unit/Zone.
- **Term:** 3 years (may be replaced earlier).
- **Key duties:** Notify staff of risk meetings, coordinate risk assessments, submit Risk Assessment Sheets, report implementation status of controls.
- **Attributes:** name, designation, directorate/unit/zone, appointment date, appointment letter reference, status (active/inactive).

#### 4. Director / Unit Manager / Zonal In-Charge (Head)
- **Role:** Senior line manager within a Directorate, Unit, or Zone.
- **Responsibilities:** Nominates RC and QA candidates, endorses risk assessment sheets, approves RC attendance at workshops.

#### 5. Director General (DG)
- **Role:** The highest executive authority within FCC.
- **Responsibilities:** Signs all appointment letters for RCs and QAs; receives Activity Reports for noting.

#### 6. Legal Service Manager (LSM)
- **Role:** Governance routing officer.
- **Responsibilities:** Receives documents from RMQAM and forwards them to the Risk and Governance Committee (7 days before meetings) and to the Commission.

#### 7. Management (Executive Team)
- **Role:** FCC's senior executive team.
- **Responsibilities:** Discusses and provides recommendations on the Institutional Risk Register, RTAP, and Quarterly Performance Reports before escalation.

#### 8. Risk and Governance Committee
- **Role:** A sub-commission-level governance body.
- **Responsibilities:** Reviews the Institutional Risk Register, RTAP, and Quarterly Performance Reports. Issues directives to RMQAM.

#### 9. Commission
- **Role:** The supreme governing body of the FCC (Board of Commissioners).
- **Responsibilities:** Final approval of the Institutional Risk Register and Risk Treatment Action Plan. Receives the Quarterly Performance Report via LSM.

#### 10. Quality Auditor (QA) / Quality Champion (QC)
- **Role:** Certified staff member who conducts internal QMS audits.
- **Qualification:** Must pass ISO 9001:2015 QMS Audit examination with ≥ 75%.
- **Restriction:** Cannot audit own Directorate/Unit/Zone or any area with a conflict of interest.
- **Attributes:** name, directorate/unit/zone, certification date, exam score, appointment date, status.

#### 11. Team Leader (TL)
- **Role:** A designated QA who leads an audit team for a specific audit engagement.
- **Responsibilities:** Conducts entry and exit meetings, consolidates individual audit reports, submits final report to RMQAM.

#### 12. Auditee
- **Role:** The Directorate/Unit/Zone or its staff being subjected to a QMS audit.
- **Responsibilities:** Participates in entry/exit meetings, acknowledges NCs, signs audit report, implements corrective actions.

#### 13. Risk Owner
- **Role:** The individual within a Directorate/Unit/Zone held accountable for managing a specific risk.
- **Relationship:** Associated with specific risks in the Risk Assessment Sheet and RTAP.

---

### Documents / Artefacts

#### 14. Risk Assessment Sheet
- **Purpose:** The primary form for capturing, analysing, and evaluating individual risks.
- **Used at:** Departmental level (for Departmental Risk Register) and institutional level (for Institutional Risk Register).
- **Key data fields:**
  - Risk description
  - Risk category / type
  - Risk owner
  - Likelihood rating
  - Impact rating
  - Inherent risk level
  - Existing controls
  - Residual risk level
  - Proposed controls

#### 15. Departmental Risk Register
- **Purpose:** Consolidation of approved Risk Assessment Sheets for a single Directorate/Unit/Zone.
- **Lifecycle:** RC → Director/Head (endorsement) → RMQAM (approval) → RMO (consolidation into institutional register).
- **Key data fields:**
  - Directorate/Unit/Zone identifier
  - List of approved risks (from Risk Assessment Sheets)
  - Submission date
  - Approval status and date
  - RMQAM comments

#### 16. Institutional Risk Register
- **Purpose:** Organisation-wide register of risks exceeding the institutional risk appetite/threshold.
- **Lifecycle:** RMO prepares → RMQAM reviews → DG (Activity Report) → Management → LSM → Risk and Governance Committee → Commission (final approval).
- **Key data fields:**
  - All risk data from contributing departmental risk registers
  - Risk threshold status (exceeded / within)
  - Risk owners
  - Proposed controls
  - Reporting period (semi-annual)
  - Approval status

#### 17. Risk Treatment Action Plan (RTAP)
- **Purpose:** Document pairing each institutional-level risk with a specific proposed control, responsible officer, and implementation timeline. Tracked and updated quarterly.
- **Key data fields:**
  - Risk ID (linked to Institutional Risk Register)
  - Control description
  - Responsible officer (risk owner / RC)
  - Target implementation date
  - Implementation status: `Not Started` / `In Progress` / `Completed`
  - Supporting evidence / comments
  - Last updated date

#### 18. Activity Report
- **Purpose:** Summary report of actions taken during the Institutional Risk Register workshop.
- **Submitted to:** DG for noting.
- **Key data fields:**
  - Workshop date
  - Actions taken
  - Responsible officers
  - Completion status

#### 19. Quarterly Performance Report
- **Purpose:** Periodic report on the implementation rate of risk controls, including comparative analysis between current and previous quarters.
- **Frequency:** Quarterly.
- **Submitted to:** Management (via LSM) → Risk and Governance Committee → Commission.
- **Key data fields:**
  - Reporting period (quarter)
  - Per-control implementation status
  - Current quarter implementation rate (%)
  - Previous quarter implementation rate (%)
  - Variance / trend analysis
  - RMQA Plan progress
  - Recommendations / management directives actioned

#### 20. Appointment Letter (RC or QA)
- **Purpose:** Formal letter officially designating a Risk Champion or Quality Auditor.
- **Signed by:** Director General (DG).
- **Dispatched via:** Registry Office.
- **Key data fields:**
  - Nominee name and designation
  - Role being appointed (RC or QA)
  - Directorate/Unit/Zone
  - Appointment date
  - Effective period
  - DG signature date
  - Dispatch reference

#### 21. QMS Audit Program
- **Purpose:** Annual plan defining scope, frequency, processes to be audited, and assigned QAs.
- **Approved by:** RMQAM.
- **Key data fields:**
  - Audit year
  - Scope and objectives
  - List of processes to be audited
  - Assigned QAs per process
  - Audit frequency schedule

#### 22. Audit Plan
- **Purpose:** Detailed operational plan for a specific audit engagement.
- **Approved by:** RMQAM.
- **Key data fields:**
  - Audit engagement reference
  - Audit dates
  - Audit team composition
  - Team Leader (TL) designation
  - Audit timetable
  - Assigned processes per QA

#### 23. Audit Checklist
- **Purpose:** Standardised checklist used by a QA during a field audit for a specific process.
- **Based on:** ISO 9001:2015 clauses and relevant QMS documentation.
- **Key data fields:**
  - Assigned QA
  - Assigned process
  - ISO 9001:2015 clause references
  - Checklist items / questions
  - Conformity status per item
  - Evidence references

#### 24. Audit Report
- **Purpose:** Document recording all findings from a QMS audit engagement, including NCs and Areas for Improvement.
- **Signed by:** Team Leader and Auditee.
- **Key data fields:**
  - Audit reference / ID
  - Auditee (Directorate/Unit/Zone)
  - Audit date
  - Audit team (QAs + TL)
  - List of Non-Conformances (NCs)
  - Areas for Improvement
  - Auditee acknowledgment
  - TL signature
  - Auditee signature
  - Submission date to RMQAM

#### 25. Non-Conformance (NC)
- **Purpose:** A formally recorded failure to comply with ISO 9001:2015 or internal QMS requirements.
- **Origin:** Raised by QA during audit.
- **Key data fields:**
  - NC reference number
  - Audit report reference
  - Audit finding description
  - ISO clause / internal requirement violated
  - Evidence of non-conformance
  - Auditee responsible
  - Proposed corrective action
  - Target closure date
  - Closure status

#### 26. Non-Disclosure Form
- **Purpose:** A confidentiality agreement signed by both the audit team and auditee before the audit commences.
- **Retained by:** Team Leader (original); copy given to auditee.

#### 27. QMS Audit Examination Result
- **Purpose:** Records the outcome of the ISO 9001:2015 certification examination taken by proposed QA candidates.
- **Key data fields:**
  - Candidate name
  - Examination date
  - Score obtained (%)
  - Pass/Fail status (threshold: 75%)
  - Attempt number (max 2)

---

## C. Key Workflows / Processes

---

### Process 1 — Appointment of Risk Champions
**Process Reference:** FCC_SBP_RMQA_01
**Frequency:** Every 3 years or when the need arises

#### Trigger
RMQAU determines the need for Risk Champions (at start of 3-year cycle or vacancy).

#### Actors
RMQAM, RMO, Directors/Unit Managers/Zonal In-Charges (Heads), Director General (DG)

#### Pre-conditions
- Heads have submitted proposed RC names to RMQAM.

#### Process Flow
1. RMQAM submits a written request to Directors/Units/Zones requesting the name of an RC to represent their area.
2. Heads submit proposed RC names to RMQAM.
3. RMQAM acknowledges receipt of proposed names and directs RMO to draft the appointment letter.
4. RMO prepares the appointment letter and submits to RMQAM for review and recommendations.
5. RMQAM reviews, provides comments if necessary, and submits the letter to DG for signature.
6. DG signs the appointment letter.
7. Signed letters are dispatched to RCs through the Registry Office.

#### Outcomes
- Signed appointment letters
- Active Risk Champions officially appointed per Directorate/Unit/Zone

#### Exceptions / Special Cases
- One RC may coordinate more than one Unit.
- An RC may be replaced before the 3-year term ends.

#### Control Points
- Signed appointment letter (confirms DG approval)
- List of Risk Champions (register of all active RCs)

---

### Process 2 — Development of Departmental Risk Register
**Process Reference:** FCC_SBP_RMQA_03
**Frequency:** Semi-annually or when the need arises

#### Trigger
Semi-annual risk review cycle or ad-hoc need.

#### Actors
RC, Director/Unit Manager/Zonal In-Charge, RMQAM, RMO

#### Pre-conditions
- Identified risks exist.
- Risk Assessment Sheets are available.
- Existing risk exposures have been assessed.

#### Process Flow
1. RC sends notification email to staff of the same Directorate/Unit/Zone about an upcoming risk discussion meeting.
2. Director/Unit Manager/Zonal In-Charge (via RC) convenes a risk review meeting to consolidate risks identified by staff.
3. RC coordinates risk assessment using the designated Risk Assessment Sheet (likelihood, impact, controls, ratings).
4. Completed Risk Assessment Sheet is submitted to the Director/Unit Manager/Zonal In-Charge for review and endorsement.
5. After endorsement, RC forwards the sheet to RMQAM for review and approval.
6. **If not approved:** RMQAM (via RMO) returns the sheet to RC with comments for rework and resubmission. *(Loop back to step 5.)*
7. **If approved:** RMQAM instructs RMO to consolidate all approved Risk Assessment Sheets from all Directorates/Units/Zones in preparation for the Institutional Risk Register.

#### Outcomes
- Approved Departmental Risk Registers
- Consolidated Risk Assessment Sheets ready for institutional consolidation

#### Control Points
- Risk Assessment Sheet (evidence of risk data capture)
- Measurable Outcome: Implementation rate of risk controls within the department

---

### Process 3 — Preparation of Institutional Risk Register
**Process Reference:** FCC_SBP_RMQA_04
**Frequency:** Semi-annually or when the need arises

#### Trigger
Completion of Departmental Risk Registers from all Directorates/Units/Zones.

#### Actors
RMQAM, RMO, all RCs, Commission, Directors/Heads, LSM

#### Pre-conditions
- Departmental risk registers have been prepared.

#### Process Flow
1. RMQAM emails Directors/Unit Managers/Zonal In-Charges requesting permission for RC attendance at the Risk Management Workshop.
2. RMO notifies RCs of the workshop date, time, and venue.
3. RCs present their Departmental Risk Registers at the workshop.
4. Following group discussion and brainstorming, RMO consolidates all risks **exceeding the acceptable threshold** into:
   - A Risk Assessment Sheet
   - A Risk Treatment Action Plan Sheet
   - These are compiled into the **Institutional Risk Register** and submitted to RMQAM for review.
5. **If changes required:** RMQAM returns recommendations to RMO for action.
6. RMO reworks the documents and resubmits to RMQAM along with an Activity Report.
7. RMQAM submits the Activity Report to DG for noting.
8. RMQAM reviews and submits the Institutional Risk Register and RTAP to Management for discussion.
9. RMQAM acts upon recommendations provided during the Management meeting.
10. RMQAM submits the Institutional Risk Register and RTAP to LSM for onward submission to Risk and Governance Committee members **at least 7 days before** the meeting.

#### Outcomes
- Approved Institutional Risk Register
- Approved Risk Treatment Action Plan

#### Governance & Performance Requirements
- Compliance with institutional risk appetite
- Coverage of high-impact and high-likelihood risks
- Traceability from departmental to institutional risks

#### Control Points
- Implementation rate of proposed controls

---

### Process 4 — Implementation of Proposed Controls (Risk Treatment Action Plan)
**Process Reference:** FCC_SBP_RMQA_05
**Frequency:** Quarterly or when the need arises

#### Trigger
Quarterly reporting cycle. Distributed RTAP with RCs.

#### Actors
RMO, RCs, RMQAM, LSM, Risk and Governance Committee, Commission

#### Pre-conditions
- RTAP has been distributed to RCs with implementation details.
- Departments have progress to report.

#### Process Flow
1. RMO sends reminder emails to RCs requesting submission of implementation status of proposed controls.
2. RCs submit implementation status updates to RMO.
3. **If status is not in order:** RMO returns to RC with documented feedback for rework and resubmission. *(Loop back to step 2.)*
4. **If status is in order:** RMO consolidates updates from all RCs into the RTAP and forwards to RMQAM for review.
5. **If clarity needed:** RMQAM sends back to RMO for review. *(Loop back to step 4.)*
6. **If satisfactory:** RMQAM conducts comparative analysis of implementation rates (current quarter vs. previous quarters).
7. RMQAM (via RMO) consolidates:
   - Risk control implementation status
   - RMQA Plan progress
   - Comparative analysis results
   → into the **Quarterly Performance Report**.
8. Quarterly Performance Report submitted to LSM → Management for discussion.
9. RMQAM acts upon management recommendations; updates implementation records.
10. RMQAM submits the Quarterly Performance Report to LSM → Risk and Governance Committee (**at least 7 days before** the meeting).
11. RMQAM acts on committee directives → LSM forwards final report to the Commission Meeting.

#### Outcomes
- Updated Risk Treatment Action Plan
- Quarterly Performance Report
- Implementation Status Report of Proposed Controls

#### Performance Indicators
- Implementation rate of proposed controls (%)
- Percentage of completed controls
- Quarter-on-quarter improvement trends

---

### Process 5 — Appointment of Quality Auditors / Champions
**Process Reference:** FCC_SBP_RMQA_06
**Frequency:** Every 3 years or when the need arises

#### Trigger
Start of 3-year cycle or vacancy in QA role.

#### Actors
RMQAM, PRMO/RMO, Directors/Unit Managers/Zonal In-Charges (Heads), DG, Proposed QA candidates

#### Pre-conditions
- Heads have submitted proposed QA names.
- QA must pass ISO 9001:2015 audit examination.

#### Process Flow
1. RMQAM submits a written request to Directors/Units/Zones to propose the name of a Quality Champion (QC).
2. Heads submit proposed QC names to RMQAM.
3. RMQAM acknowledges receipt and instructs PRMO/RMO to arrange ISO 9001:2015 training.
4. PRMO/RMO identifies and engages a qualified ISO 9001:2015 trainer; proposes date, time, and venue to RMQAM.
5. Upon RMQAM approval, PRMO/RMO notifies trainees of training details.
6. Trainees attend ISO 9001:2015 training.
7. After training, proposed QAs sit the QMS Audit examination.
8. **If score < 75% (first attempt):** Candidate is allowed one re-sit.
9. **If score < 75% (second attempt):** Head must nominate a replacement candidate, who follows the same process from step 1.
10. **If score ≥ 75%:** RMQAM (via RMO) prepares appointment letter and submits to DG for signature.
11. DG signs the appointment letter.
12. Signed letters dispatched via the Registry Office to QAs.

#### Outcomes
- Certified Quality Auditors (Quality Champions)
- Signed Appointment Letters

#### Control Points
- Signed appointment letter
- List of Quality Auditors (register)

---

### Process 6 — Conducting Quality Audit (QMS Audit)
**Process Reference:** FCC_SBP_RMQA_07
**Frequency:** Semi-annually or whenever the need arises

#### Trigger
Commencement of the annual audit cycle as per the QMS Audit Program.

#### Actors
RMQAM, RMO, Quality Auditors (QAs), Team Leader (TL), Auditees (Directors/Unit Managers/Zonal In-Charges/Staff)

#### Pre-conditions
- Quality Auditors have been appointed by DG.
- Approval for preparation of QMS Audit Program has been granted.

#### Sub-Process 6a: Planning — Annual QMS Audit Program
1. RMO (in collaboration with appointed QAs) prepares the annual QMS Audit Program (scope, frequency, processes, teams).
2. RMO submits to RMQAM for review and approval.
3. **If not approved:** RMQAM returns to RMO for rework and resubmission.
4. **If approved:** RMQAM approves the program and instructs RMO to prepare the Audit Plan.

#### Sub-Process 6b: Planning — Audit Plan
5. RMO prepares the detailed Audit Plan (dates, team composition, TL, timetable).
6. RMO submits to RMQAM for review and approval.
7. **If not approved:** RMQAM returns to RMO for rework and resubmission.
8. **If approved:** RMO distributes the approved plan to QAs.

#### Sub-Process 6c: Preparation — Checklists
9. Each QA prepares audit checklists for their assigned processes (based on ISO 9001:2015 clauses).

#### Sub-Process 6d: Notification
10. RMQAM sends notification email and timetable to auditees **at least 10 working days** before the audit.

#### Sub-Process 6e: Entry Meeting
11. Audit team arrives; TL (on behalf of RMQAM) conducts the Entry Meeting with auditees.
12. Audit scope, timetable, and methodology are confirmed.
13. **If timetable disagreement:** TL corrects/adjusts the timetable and informs auditee.
14. Non-disclosure / confidentiality forms are signed (TL retains original; auditee keeps copy).

#### Sub-Process 6f: Pre-Audit Meeting
15. TL and QAs conduct a Pre-Audit Meeting, reviewing relevant documentation (ISO 9001:2015 standard, quality manuals, procedures, SOPs, previous audit reports).

#### Sub-Process 6g: Audit Execution
16. QAs conduct the audit and document findings:
    - Non-Conformances (NCs)
    - Areas for Improvement

#### Sub-Process 6h: Reporting
17. QA prepares audit report and presents NCs to auditees for acknowledgment.
18. QA submits report to TL for consolidation.
19. TL presents the full consolidated report to auditee at the Exit Meeting.
20. **If auditee disagrees with a finding:** TL may correct, amend, or delete the observation.
21. **Upon agreement:** TL and auditee sign the final report; a copy is given to the auditee.

#### Sub-Process 6i: Management Review
22. TL submits signed report to RMQAM for review prior to Management Review Meeting (MRM).
23. Report is presented at the MRM.
24. RMQAM receives all MRM directives and communicates them to respective auditees and responsible parties for implementation of NCs and Areas for Improvement.

#### Outcomes
- Approved QMS Audit Program
- Approved Audit Plans
- Signed Non-Disclosure Forms
- Signed Audit Reports
- Documented Non-Conformances and Areas for Improvement
- MRM Directives (corrective actions assigned)

---

## D. Relationships Between Entities

### RMQAU → Risk Champions
- **Type:** One-to-Many
- One RMQAU oversees many RCs (one per Directorate/Unit/Zone across the organisation).

### RC ↔ Directorate / Unit / Zone
- **Type:** One-to-One (with exception)
- Each active RC is assigned to exactly one Directorate/Unit/Zone.
- **Exception:** One RC may cover more than one Unit if the need arises.

### RC → Risk Assessment Sheet
- **Type:** One-to-Many
- One RC submits many Risk Assessment Sheets (one per risk identified within their area).

### Risk Assessment Sheet → Risk
- **Type:** One-to-One
- Each Risk Assessment Sheet captures one identified risk with all its attributes.

### Risk Assessment Sheets → Departmental Risk Register
- **Type:** Many-to-One
- Multiple Risk Assessment Sheets from one Directorate/Unit/Zone are consolidated into one Departmental Risk Register.

### Departmental Risk Registers → Institutional Risk Register
- **Type:** Many-to-One (filtered)
- Multiple Departmental Risk Registers feed into one Institutional Risk Register.
- Only risks **exceeding the institutional risk appetite/threshold** are included.

### Institutional Risk Register ↔ Risk Treatment Action Plan
- **Type:** One-to-One (paired documents)
- Each Institutional Risk Register has exactly one corresponding Risk Treatment Action Plan.

### Risk → Risk Treatment Action Plan Item
- **Type:** One-to-One
- Each risk entry in the Institutional Risk Register has exactly one RTAP entry with its control, responsible officer, and status.

### Risk → Risk Owner
- **Type:** Many-to-One
- Multiple risks may be owned by a single Risk Owner within a Directorate/Unit/Zone.

### RMQAM → RMO
- **Type:** One-to-Many (supervisory)
- RMQAM directs one or more RMOs on operational tasks.

### Head → RC Nomination
- **Type:** One-to-One (per cycle)
- Each Head nominates one RC per appointment cycle for their Directorate/Unit/Zone.

### Head → QA Nomination
- **Type:** One-to-One (per cycle)
- Each Head nominates one QA candidate per appointment cycle.

### DG → Appointment Letter
- **Type:** One-to-Many
- One DG signs many appointment letters (for multiple RCs and QAs).

### Appointment Letter → RC or QA
- **Type:** One-to-One
- Each appointment letter designates exactly one individual (RC or QA).

### QMS Audit Program → Audit Plan
- **Type:** One-to-Many
- One annual QMS Audit Program contains multiple Audit Plans (one per audit engagement).

### Audit Plan → QA
- **Type:** Many-to-Many
- One Audit Plan assigns multiple QAs to multiple processes; one QA can be assigned to multiple audit plans.

### Audit Plan → Team Leader
- **Type:** Many-to-One
- Each Audit Plan has exactly one designated Team Leader from among the assigned QAs.

### QA → Audit Checklist
- **Type:** One-to-Many
- One QA prepares one or more checklists (one per assigned process).

### QA → Audit Report (individual)
- **Type:** One-to-Many
- One QA prepares one report per audit engagement.

### TL → Consolidated Audit Report
- **Type:** One-to-One
- One TL consolidates all individual QA reports into one final audit report per engagement.

### Audit Report → Non-Conformance (NC)
- **Type:** One-to-Many
- One Audit Report may document many NCs.

### Auditee → Non-Conformance
- **Type:** One-to-Many
- One Auditee may have multiple NCs raised against them.

### Auditee → Audit Report
- **Type:** One-to-Many
- One Auditee may be subject to multiple audit reports across different audit engagements.

### RMQAM → Quarterly Performance Report
- **Type:** One-to-Many
- RMQAM produces one Quarterly Performance Report per quarter.

### Risk and Governance Committee → Reports
- **Type:** One-to-Many
- The Committee reviews many reports (Institutional Risk Register, RTAP, Quarterly Performance Reports).

### Commission → Institutional Risk Register
- **Type:** One-to-Many (over time)
- The Commission provides final approval of each semi-annual Institutional Risk Register.

### LSM → (RMQAM ↔ Committee / Commission)
- **Type:** Routing intermediary (One-to-One per routing event)
- LSM is the routing conduit: receives from RMQAM and forwards to both the Risk and Governance Committee and the Commission. LSM has no ownership of the documents.

### Management Review Meeting (MRM) → Directives
- **Type:** One-to-Many
- One MRM session issues multiple directives for corrective action.

---

## E. Important Business Rules / Constraints

### E.1 — Structural Constraints (RC)

- Each Directorate/Unit/Zone **must have only one active RC** at a time.
- **Exception:** One RC may coordinate more than one Unit where the need arises.
- RCs serve a **3-year appointment term** and may be replaced before the term ends.
- Only **authorized Heads** (Directors, Unit Managers, Zonal In-Charges) may submit RC nominations.

### E.2 — Structural Constraints (QA)

- Quality Auditors serve a **3-year appointment term** and may be replaced before the term ends.
- A QA **must not audit their own Directorate/Unit/Zone** or any area where a conflict of interest exists.
- One QA may audit **more than one process** (across different areas, provided no conflict).

### E.3 — Qualification Constraints (QA Certification)

- All proposed QA candidates **must undergo ISO 9001:2015 training** before examination.
- QA candidates **must pass the QMS Audit examination** with a minimum score of **75%**.
- A candidate who fails may **re-sit once only**.
- A candidate who fails the **second attempt** cannot be appointed; the Head **must nominate a replacement** who starts the process from the beginning.

### E.4 — Risk Threshold Rule

- Only risks whose residual or inherent risk level **exceeds the institutional risk appetite/threshold** are included in the Institutional Risk Register.
- Risks below the threshold remain at the Departmental Risk Register level only.

### E.5 — Approval Chain Rules

All documents follow a strict hierarchical approval chain:

| Document | Approval Chain |
|----------|----------------|
| RC Appointment Letter | RMO drafts → RMQAM reviews → DG signs |
| QA Appointment Letter | RMO drafts → RMQAM reviews → DG signs |
| Departmental Risk Register | RC prepares → Director/Head endorses → RMQAM approves |
| Institutional Risk Register | RMO compiles → RMQAM reviews → DG (Activity Report for noting) → Management → LSM → Risk & Governance Committee |
| Risk Treatment Action Plan | Same chain as Institutional Risk Register |
| Quarterly Performance Report | RMQAM prepares → LSM → Management → LSM → Risk & Governance Committee → (directives) → LSM → Commission |
| QMS Audit Program | RMO prepares → RMQAM approves |
| Audit Plan | RMO prepares → RMQAM approves |

### E.6 — Rework Cycles

Any document may be returned for rework at any review stage:
- Risk Assessment Sheets returned by RMQAM → RC for rework and resubmission.
- Institutional Risk Register returned by RMQAM → RMO for rework and resubmission.
- RTAP implementation status returned by RMO → RC for rework.
- Consolidated implementation data returned by RMQAM → RMO for clarification.
- QMS Audit Program returned by RMQAM → RMO for rework.
- Audit Plan returned by RMQAM → RMO for rework.
- **There is no defined maximum rework cycle limit** (except for the QA examination, which is capped at 2 attempts).

### E.7 — Timing / Deadline Rules

| Rule | Deadline |
|------|----------|
| Submission to Risk and Governance Committee | At least **7 calendar days** before the Committee meeting |
| Notification to auditees before a QMS audit | At least **10 working days** before audit commencement |
| Departmental risk review frequency | **Semi-annually** or when the need arises |
| Institutional risk register review frequency | **Semi-annually** or when the need arises |
| Risk control monitoring cycle | **Quarterly** |
| RC and QA appointment term | **3 years** |
| Comparative analysis (RTAP) | **Quarter-on-quarter** (current vs. previous quarter) |

### E.8 — Audit Confidentiality

- A **Non-Disclosure / Confidentiality Form must be signed** by both the audit team and the auditee before field audit work begins.
- The Team Leader retains the original; a copy is given to the auditee.

### E.9 — Audit Finding Dispute Resolution

- If an auditee **disagrees with a finding** during the Exit Meeting, the Team Leader may:
  - Correct the observation, or
  - Amend the observation, or
  - Delete the observation.
- Both the **TL and Auditee must sign the final audit report** before it is submitted to RMQAM.

### E.10 — RTAP Control Status Values

Implementation status of each control in the Risk Treatment Action Plan is tracked as exactly one of three values:
- `Not Started`
- `In Progress`
- `Completed`

### E.11 — Single Active Instance Rules

| Entity | Constraint |
|--------|-----------|
| RC per Directorate/Unit/Zone | Only one **active** RC at a time |
| Institutional Risk Register | Only one **active** (current) register at a time |
| RTAP | Only one **active** plan paired to the current register |

### E.12 — Legal and Regulatory Framework

All processes are governed by and must comply with:

| Framework | Applicability |
|-----------|--------------|
| Fair Competition Act, 2003 | All processes |
| Mergers, Monopolies & Anti-Competitive Practices Act (MMA), 1968 | All processes |
| Guideline for developing and implementing risk management framework in Public Sector Entities, 2023 | Risk management processes |
| Risk Management Framework, 2024 | Risk management processes |
| Risk Management and Quality Assurance Procedure | All processes |
| Risk Management and Quality Assurance Annual Plan | All processes |
| ISO 9001:2015 QMS Requirements | Quality audit processes |
| ISO 19011:2018 — Guidelines for Auditing Management Systems | Quality audit processes |
| Quality Policy | Quality audit processes |
| Quality Audit Procedure | Quality audit processes |
| QMS Manual (Quality Manual) | Quality audit processes |

### E.13 — Permission / Role Constraints

- Only **RMQAM** may submit documents to the DG.
- Only **DG** may sign appointment letters for RCs and QAs.
- Only **LSM** routes documents to the Risk and Governance Committee and Commission; RMQAM does not submit directly.
- Only **authorized Heads** may submit nominations for RCs and QAs.
- Only **appointed QAs** may conduct QMS audits — no ad-hoc auditing.
- **RMQAU** (not individual services) holds the authority to develop the Audit Program and Audit Plan.

### E.14 — System-Level Requirements (Functional Constraints)

The system must support:
- Awareness sessions for RCs, Risk Owners, and general staff on risk management principles.
- Risk identification via brainstorming sessions, workshops, interviews, and surveys.
- Review of historical data, lessons learned, and audit reports for risk identification.
- Risk registration with full detail (nature, impact, likelihood).
- Automated reminders to RCs for status submissions (quarterly).
- Comparative analysis reports automatically generated from historical RTAP data.
- Quarterly Risk Management Implementation Reports for submission to the Audit Committee and Internal Auditor General Office (IAGO).
- Role-based access control for sensitive governance, compliance, and audit data.

### E.15 — External Dependencies

The Risk Management module depends on:

| External Service | Purpose |
|-----------------|---------|
| IAM Service | Assign permissions for RMQAM, RMO, RCs, QAs, and other actors |
| Document Records Service | Store all documents: risk registers, RTAP, appointment letters, audit reports, performance reports |
| Work Orchestration Service | Task tracking, review assignments, notification delivery, meeting coordination, reporting workflows |
| Corporate Services | Access to HR records and operational data relevant to audits and compliance |

---

*This domain extraction was derived from full analysis of the Risk Management SRS (FCC RMQAU). All domains, entities, workflows, relationships, and rules described here are sourced directly from the SRS document — no assumptions or additions have been made.*
