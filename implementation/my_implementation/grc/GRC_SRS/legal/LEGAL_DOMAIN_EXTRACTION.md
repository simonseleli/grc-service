# Legal Module — Domain Extraction
**Source SRS:** `Legal_Service.md`
**Purpose:** Foundation document for backend design — domain understanding only, no implementation code.

---

## A. Core Business Domains

### 1. Governance & Meeting Management
Manages the full lifecycle of formal governance meetings held by recognised governing bodies (e.g., Commission, Audit Committee, Management). Covers meeting creation, agenda building, participant management, quorum verification, conflict of interest handling, minutes drafting and approval, resolution recording, and directive issuance.

### 2. Governance Structure Administration
Manages the organisational structure within which meetings operate. Defines the types of committees, the governing bodies themselves, and their members (both Committee Members and Management Members). Controls secretary assignments and member synchronisation with the Corporate Service.

### 3. Determinations & Approvals
Manages the formal submission pipeline for documents and matters that require a binding decision from a governing body. Any authenticated user can raise a submission; it moves through review, meeting deliberation, and determination, after which directives may be auto-created.

### 4. Litigation — FCC as Defendant (FCC Sued)
Manages end-to-end legal cases where the Fair Competition Commission has been sued. Covers case registration, DG review, assignment of legal officers, court filings (with two-stage approval), plaintiff responses, hearings, settlements, judgments, appeals, financials, tasks, and case closure.

### 5. Litigation — FCC as Plaintiff (FCC Suing)
Manages end-to-end legal cases where the FCC initiates legal action against a respondent. Entry points are: a simplified Breach Report Intake (for Department Users) and a Full Breach Report (for Legal Officers/Registry Officers). Workflow mirrors the Defendant module but with different filing types, response types, and financial card labels.

### 6. Public Register
Manages the official record of finalised commission decisions. Secretariat drafts and publishes decisions; published decisions become publicly visible (future CRM integration).

### 7. Global Cross-Cutting Concerns
- **Digital Signature Engine:** Electronically stamps approval documents with signer identity and timestamp.
- **Audit Trail:** Logs every state transition, modification, and approval across all domains.
- **Notifications Engine:** Triggers email/in-app notifications on relevant events to the correct roles.
- **Role-Based Access Control (RBAC):** Enforces entity-level and action-level permissions per role.
- **Unique Identifier Generation:** Atomic, non-duplicate ID sequences for meetings and cases.

---

## B. Main Entities

### B1 — Governance Structure Domain

#### `CommitteeType`
- **Purpose:** Defines a category/type of governing body (e.g., Audit, Commission, Management).
- **Role:** Master data. Used as a classification for `GoverningBody`.
- **Key Attributes:** TypeID, Name, Description, Status (Active/Inactive).

#### `GoverningBody`
- **Purpose:** Represents a formal committee or governing body within FCC.
- **Role:** The organisational context for meetings, members, and submitted determinations. A meeting always belongs to a governing body.
- **Key Attributes:** BodyID, TypeID, Name, CompositeTitle, Description, Status, SecretaryUserID[] (multiple secretaries allowed).

#### `Member`
- **Purpose:** Represents a person who sits on a governing body.
- **Role:** Participates in meetings, is counted for quorum, can declare conflicts, receives and acts on directives.
- **Key Attributes:** MemberID, UserID, BodyID, Position (Member/Secretary/Chairman), MemberType (Committee Member/Management Member), Email, Department, Status, JoinedDate, LeftDate.

---

### B2 — Determinations & Approvals Domain

#### `SubmissionForDetermination`
- **Purpose:** A formal request by any staff member asking a governing body to make an official decision on a matter.
- **Role:** Feeds the meeting agenda. One submission may be linked to one meeting agenda item. Upon determination, outcome is recorded back on the submission.
- **Key Attributes:** SubmissionID, Title, Description, SubmitterUserID, SubmitterDept, SubmissionDate, TargetBodyID, SupportingDocuments[], Status (Submitted/Under Review/Deferred/Approved/Rejected), OutcomeNotes, MeetingID, DeterminationDate, DirectivesCreated[].
- **Workflow States:** `SUBMITTED → UNDER_REVIEW → DETERMINED`

---

### B3 — Meeting Governance Domain

#### `Meeting`
- **Purpose:** Represents a formal governance meeting of a governing body.
- **Role:** The central entity of the Meeting Governance domain. All agenda items, participants, minutes, resolutions, and directives are children of a meeting.
- **Key Attributes:** MeetingID, Title, MeetingNumber (auto-generated), Location, Mode (Physical/Virtual/Hybrid), VenueLink, StartDateTime, EndDateTime, Type (Ordinary/Extraordinary/Special), GoverningBodyID, AgendaSummary, Status, QuorumMet (boolean), QuorumPercentage, SecretaryID.
- **Workflow States:** `DRAFT → REGISTERED → INVITATIONS_SENT → AGENDA_SHARED → QUORUM_READY → ONGOING → POSTPONED → CLOSED | CANCELLED | RESCHEDULED`

#### `MeetingAgenda`
- **Purpose:** An agenda item within a meeting, sourced from a `SubmissionForDetermination`.
- **Role:** Links a submission to a meeting; records the outcome (determination result) of that item. Conflict declarations are tracked per agenda item.
- **Key Attributes:** AgendaID, MeetingID, SubmissionID, Order, Title, Description, Documents[], ConflictDeclarations[] (list of member IDs), Outcome, DirectivesCreated[].

#### `MeetingParticipant`
- **Purpose:** Records the participation of a person (member or invitee) in a specific meeting.
- **Role:** Tracks invitation status (used for quorum), role in the meeting, and optional attendance marking during the meeting.
- **Key Attributes:** ParticipantID, MeetingID, UserID, Role (Member/Invitee), InvitationStatus (Pending/Accepted/Declined), DeclineReason, AttendanceMarked (boolean).

#### `Directive` (Meeting Directive)
- **Purpose:** A formal action item issued during a meeting, assigned to a person or organisational unit.
- **Role:** Tracks compliance with decisions made in meetings. Persists across meetings via Matters Arising until finally closed by the Secretary.
- **Key Attributes:** DirectiveID, MeetingID, AgendaID (optional), Description, Category, Priority (Critical/High/Medium/Low), AssignedOrgUnit, AssignedUserID, DueDate, Status (Open/In Progress/Overdue/Closed), CompletionSummary, CompletionDate, EvidenceDocumentID, FinallyClosed (boolean), FinallyClosedMeetingID.
- **Workflow States:** `OPEN → IN_PROGRESS (optional) → CLOSED (by assignee) → FULLY_CLOSED (by Secretary)`
- **Note:** This is distinct from `DirectiveLitigation` used in litigation cases.

#### `Minutes`
- **Purpose:** The official written record of a meeting's proceedings.
- **Role:** Drafted after the meeting by the Secretary; submitted to participating members for approval; becomes the legal record once approved.
- **Key Attributes:** MinutesID, MeetingID, Title, Content, Attachments[], Status (Draft/Pending Approval/Approved), CreatedBy, ApprovedBy[], ApprovalDate.
- **Workflow States:** `DRAFT → PENDING_APPROVAL → APPROVED`

#### `Resolution`
- **Purpose:** Formal decision adopted during a meeting on a specific agenda item.
- **Role:** Auto-created from agenda item outcomes. Constitutes the official record of decisions. Visible only to invited participants; searchable within that group.
- **Key Attributes:** ResolutionID, MeetingID, AgendaID, ResolutionText, DateAdopted, Status (Approved/Rejected/Noted), ResponsiblePerson, EffectiveDate, Attachments[].

---

### B4 — Litigation (FCC Sued) Domain

#### `CaseDefendant`
- **Purpose:** Represents a legal case where FCC has been sued by a plaintiff.
- **Role:** Root entity of the FCC Sued domain. All filings, responses, hearings, settlements, judgments, financials, and tasks are children of this entity.
- **Key Attributes:** CaseID (auto `FCC/SUED/YYYY/NNN`), CourtCaseNumber, CourtRegistry, CourtLevel, ServiceDate, Plaintiffs[], PlaintiffAdvocate, ClaimAmount, NatureOfClaim, DepartmentAffected, UrgencyLevel, RiskLevel, InitiationDocuments[], Stage, DGReviewStatus (Pending/Reviewed/Directive Issued), AssignedLegalOfficerID[], AssignedLegalManagerID, NextHearingDate.
- **Stages:** New / Under DG Review / Directive Issued / Hearing Stage / Judgment Received / Appeal Filed / Closed / On Hold

#### `DirectiveLitigation`
- **Purpose:** A directive issued by the DG specifically on a litigation case.
- **Role:** Separate from `Directive` (meeting directives). Issued by DG during or after case review. Legal officers and managers respond to it.
- **Key Attributes:** DirectiveID, CaseID, IssuedByUserID (DG), IssueDate, Instruction, DueDate, Status (Open/In Progress/Closed), CompletionSummary, CompletionDate, Attachments[].

#### `FilingDefendant`
- **Purpose:** A court document filed by FCC in its defence.
- **Role:** Records each filing with its version, approval chain, and final filed status. Subject to two-stage approval (Legal Manager → DG).
- **Key Attributes:** FilingID, CaseID, Type (Statement of Defence/Affidavit/Application/etc.), Title, DocumentID, Version, Status, SubmittedByUserID, ApprovalChain.
- **Workflow States:** `DRAFT → UNDER_REVIEW_LM → APPROVED_LM → UNDER_REVIEW_DG → APPROVED → FILED`

#### `ResponseDefendant`
- **Purpose:** Documents received from the plaintiff during the case.
- **Role:** Records incoming documents (e.g., Preliminary Objections, Counter Claims) for case tracking.
- **Key Attributes:** ResponseID, CaseID, Type, ReceivedDate, DocumentID, Description.

#### `Hearing`
- **Purpose:** A scheduled court session for a case.
- **Role:** Records each hearing event. Has one or more `HearingReport` children.
- **Key Attributes:** HearingID, CaseID, HearingDate, Court, Judge, Notes.

#### `HearingReport`
- **Purpose:** The report of proceedings or outcome from a specific hearing.
- **Role:** Multiple reports can attach to one hearing. The most recent `NextHearingDate` propagates up to update `CaseDefendant.NextHearingDate`.
- **Key Attributes:** ReportID, HearingID, ReportType (Proceedings/Ruling/Order), Summary, Remarks, NextHearingDate, AttachmentID.

#### `SettlementDefendant`
- **Purpose:** Records details of an out-of-court settlement for a defendant case.
- **Role:** Requires DG approval. If payment amount is set, it appears in Financials.
- **Key Attributes:** SettlementID, CaseID, SettlementDate, Terms, PaymentAmount (optional), AgreementDocumentID, Status (Proposed/Agreed/Rejected).

#### `JudgmentDefendant`
- **Purpose:** Records the court's final judgment in a defendant case.
- **Role:** Legal Manager reviews and recommends to DG. DG decides: Accept or Appeal. If Appeal, system auto-creates a `FilingDefendant` (Notice of Appeal) and a `TaskLitigation`.
- **Key Attributes:** JudgmentID, CaseID, JudgmentDate, Outcome (Won/Lost), AmountAwarded, LegalCostsAwarded, OtherCosts[], DocumentID, Remarks, DGDecision (Accept/Appeal), AppealDueDate, AppealFilingID.

#### `FinancialDefendant`
- **Purpose:** Tracks all financial activity related to a defendant case.
- **Role:** Manual tracking (no ERP integration). Shows claim amount, legal costs, court-awarded costs, recoveries (if won) and payments (if lost).
- **Key Attributes:** FinancialID, CaseID, ClaimAmount, LegalCostsIncurred, CostsAwarded, OtherCosts (aggregated), Recoveries[], Payments[].
- **Sub-records:** Each Recovery/Payment has: Date, Amount, Reference, Status (Requested/Approved/Processed).

#### `TaskLitigation`
- **Purpose:** A deadline-driven task associated with a litigation case.
- **Role:** Auto-created system tasks (e.g., file appeal by date, respond to filing approval). Manual tasks also possible. Sends reminders at 7, 2, 1 day before due date.
- **Key Attributes:** TaskID, CaseID, Title, AssignedToUserID, DueDate, Status (Open/In Progress/Overdue/Closed), Priority, RelatedEntityType, RelatedEntityID.

---

### B5 — Litigation (FCC Suing) Domain

#### `CasePlaintiff`
- **Purpose:** Represents a legal case where FCC is the plaintiff, pursuing action against a respondent.
- **Role:** Root entity of the FCC Suing domain. Same child structure as defendant (filings, responses, hearings, settlement, judgment, financials, tasks).
- **Key Attributes:** CaseID (auto `FCC/SUING/YYYY/NNN`), ReportingDepartment, NatureOfBreach, RespondentName, RespondentType, EstimatedClaimAmount, Description, UrgencyLevel, RiskLevel, InitiationDocuments[], Stage, DGReviewStatus, AssignedLegalOfficerID[], AssignedLegalManagerID, NextHearingDate.
- **Two Registration Interfaces:**
  - **Breach Report Intake (simplified):** Department User. Fields: Dept, NatureOfBreach, RespondentName, RespondentType, Description, UrgencyLevel, optional document.
  - **Full Breach Report:** Legal Officer or Registry Officer. All simplified fields plus EstimatedClaimAmount, RiskLevel, full InitiationDocuments[].

#### `FilingPlaintiff`
- **Purpose:** Court documents filed by FCC in its capacity as plaintiff.
- **Filing Types:** Plaint, Petition, Statement of Claim, Application, Chamber Summons, Affidavit, Bill of Cost, Notice of Appeal.
- **Role:** Same two-stage approval workflow as `FilingDefendant`.

#### `ResponsePlaintiff`
- **Purpose:** Documents received from the respondent.
- **Response Types:** Preliminary Objections, Response to Ruling, Response to Orders, Response to Affidavits, Counter Claim, Initial Response, Preliminary Objectives.

#### `SettlementPlaintiff`
- Identical structure and workflow to `SettlementDefendant`.

#### `JudgmentPlaintiff`
- Same fields as `JudgmentDefendant`. DG decides to accept or appeal. If appeal: auto-create `FilingPlaintiff` (Notice of Appeal) + task.

#### `FinancialPlaintiff`
- **Cards:** Claim Amount, Legal Costs Incurred, Amount Awarded, Costs Awarded, Other Costs, Recovered Amount.
- Record Recovery (if won), Record Payment (if lost). Same manual tracking rules.

> **Note on shared entities:** `Hearing`, `HearingReport`, `TaskLitigation`, and `DirectiveLitigation` are logically identical between FCC Sued and FCC Suing. They reference the parent case by `CaseID` with the type (defendant/plaintiff) distinguishable from the case ID prefix or a case-type discriminator field.

---

### B6 — Public Register Domain

#### `PublicDecision`
- **Purpose:** An official public-facing record of a commission decision.
- **Role:** Drafted and published by Secretariat. Future integration will expose published decisions on the public FCC portal.
- **Key Attributes:** DecisionID, Title, MeetingID (link), BodyText, DecisionText, DecisionDate, Status (Draft/Published), PublishedDate, CreatedBy.
- **Workflow States:** `DRAFT → PUBLISHED`

---

## C. Key Workflows / Processes

### C1 — Submission for Determination Workflow

**Trigger:** Any authenticated user creates a submission targeting a governing body.

**Stages:**
1. `SUBMITTED` — Submission created; originator can edit or withdraw.
2. `UNDER_REVIEW` — Secretary selects submission for a meeting agenda; editing/withdrawal locked.
3. `DETERMINED` — Meeting concludes; outcome (Approved/Rejected/Deferred) is recorded and propagated back to submission.

**Outcomes:**
- If Approved: any required directives are auto-created and linked.
- If Deferred: remains for a future meeting agenda.
- If Rejected: submission closed with outcome notes.

---

### C2 — Meeting Lifecycle Workflow

**Trigger:** Secretary creates a new meeting for a governing body they are assigned to.

**Stages:**
1. `DRAFT` — Meeting created with initial fields; no notifications yet.
2. `REGISTERED` — Meeting formally registered; system **automatically** sends invitations to all active members of the governing body.
3. `INVITATIONS_SENT` — Invitations dispatched; members respond (Accept/Decline).
4. `AGENDA_SHARED` — Agenda finalised and shared with participants.
5. `QUORUM_READY` — ≥51% of members have Accepted; meeting can be started.
6. `ONGOING` — Secretary initiates the meeting; business is conducted.
   - During ONGOING: Secretary can add directives to any agenda item or Matters Arising.
7. `POSTPONED` — Secretary postpones; can be resumed.
8. `CLOSED` — Secretary closes; all business concluded; no further actions.
9. `CANCELLED` / `RESCHEDULED` — Alternative terminal/near-terminal states.

**Quorum Rule:** Quorum = (Accepted Members / Total Members) × 100 ≥ 51%. Only calculated from members with `InvitationStatus = Accepted`. If not met by start time, Secretary can reschedule (status → REGISTERED or DRAFT).

**Parallel processes during meeting:**
- Agenda items are determined → outcomes recorded → resolutions auto-created.
- Directives can be added to any item.
- Matters Arising is auto-populated from unresolved directives of the same governing body.

---

### C3 — Meeting Agenda (Determination) Workflow

**Trigger:** Secretary selects a `SubmissionForDetermination` to attach to a meeting agenda.

**Stages:**
1. Secretary attaches submission → `MeetingAgenda` record created; `SubmissionForDetermination.Status` → `UNDER_REVIEW`.
2. Members may declare conflict of interest on any agenda item → excluded from that item's vote.
3. During meeting: item is deliberated → Secretary records outcome (Approved/Rejected/Noted/Deferred).
4. Outcome propagates back to `SubmissionForDetermination`.
5. `Resolution` is auto-created from the outcome.
6. If outcome triggers directives → directives auto-created and linked.

---

### C4 — Conflict of Interest Workflow

**Trigger:** A member identifies a personal/financial conflict with a specific agenda item.

**Process:**
1. Member declares conflict → `ConflictDeclaration` recorded against `AgendaID` and `MemberID`.
2. System excludes the member from any votes or determinations on that agenda item.
3. Conflict does not affect the member's participation in other agenda items.
4. Conflict does not affect future meeting participation.

---

### C5 — Directive Lifecycle Workflow (Meeting Directives)

**Trigger:** Secretary adds a directive during an ONGOING meeting to an agenda item or Matters Arising item.

**Stages:**
1. `OPEN` — Directive created, assigned to a person or org unit.
2. `IN_PROGRESS` — Optional intermediate status.
3. `OVERDUE` — Auto-transition if due date passes without closure. Notification sent.
4. `CLOSED` — **Only the assigned user** can perform initial closure. Must provide CompletionSummary, CompletionDate, and optional evidence document.
5. `FULLY_CLOSED` — **Only the Secretary** can perform final closure, in a subsequent meeting's Matters Arising. Sets `FinallyClosed = true`; directive is removed from future Matters Arising.

**Matters Arising:** Auto-populated in every meeting from all directives where `GoverningBodyID` matches and `FinallyClosed = false`.

---

### C6 — Minutes Approval Workflow

**Trigger:** After a meeting is ONGOING or CLOSED, Secretary drafts minutes.

**Stages:**
1. `DRAFT` — Secretary writes content and attaches supporting documents.
2. `PENDING_APPROVAL` — Secretary submits to participating members for approval.
3. `APPROVED` — Approval threshold reached (majority vote or explicit sign-off, configurable). Minutes become read-only and final.

---

### C7 — Litigation Case Registration Workflow (FCC Sued)

**Trigger:** Registry Officer, Legal Officer, or Legal Manager registers a new case.

**Process:**
1. Court details, plaintiff info, claim details, documents entered.
2. System auto-generates `FCC/SUED/YYYY/NNN` reference number (atomic sequence per year).
3. Stage = `New`. DG notified automatically.

---

### C8 — DG Review Workflow (Both Litigation Modules)

**Trigger:** Case is in `Under DG Review` stage.

**Process:**
1. DG reviews the case.
2. **Option A:** Issue Directive → `DirectiveLitigation` created; Stage → `Directive Issued`.
3. **Option B:** Mark as Reviewed → `DGReviewStatus = Reviewed`; case proceeds without directive.

---

### C9 — Filing Approval Workflow (Both Litigation Modules)

**Trigger:** Legal Officer uploads a filing (draft).

**Stages:**
1. `DRAFT` — Legal Officer creates filing; not yet submitted.
2. `UNDER_REVIEW_LM` — Submitted for Legal Manager review. LM notified.
3. `APPROVED_LM` — Legal Manager approves. DG notified.
4. `UNDER_REVIEW_DG` — DG reviewing.
5. `APPROVED` — DG approves. Legal Officer notified.
6. `FILED` — Legal Officer marks as filed; actual filing date recorded.

**Notifications sent at each transition.**
**Digital signature stamped on approval documents at moment of approval.**

---

### C10 — Judgment & Appeal Workflow (Both Litigation Modules)

**Trigger:** Legal Officer records a court judgment.

**Process:**
1. Judgment recorded (outcome, amounts, costs, document).
2. Submitted to Legal Manager → LM reviews and recommends to DG.
3. DG decides:
   - **Accept:** Case proceeds to financials and closure workflow.
   - **Appeal:** DG sets `AppealDueDate`. System **automatically** creates:
     - A `FilingDefendant`/`FilingPlaintiff` of type `Notice of Appeal` (Status = DRAFT).
     - A `TaskLitigation` with deadline = `AppealDueDate`, assigned to Legal Officer.
4. If `AppealDueDate` passes without filing → Task becomes `OVERDUE`; notification sent.

---

### C11 — Settlement Workflow (Both Litigation Modules)

**Trigger:** Legal Officer registers settlement details.

**Process:**
1. Settlement registered (amount, terms, date, agreement document).
2. Submitted via Legal Manager to DG for approval.
3. DG approves or rejects.
4. If payment amount specified → automatically reflected in Financials tab.

---

### C12 — Case Closure & Archiving Workflow (Both Litigation Modules)

**Trigger:** Legal Manager initiates closure when case is concluded.

**Process:**
1. Legal Manager initiates → submits for DG approval with closure summary.
2. DG approves → case becomes **read-only**; no further edits.
3. After closure: archiving follows configured policy (automatic after set period, or manual by Administrator/Legal Manager).

---

### C13 — Breach Report Intake Workflow (FCC Suing only)

**Trigger A — Simplified (Department User):**
1. Department User fills simplified Breach Report Intake (no Risk Level, no full documents).
2. Case created with Stage = New. DG notified.

**Trigger B — Full (Legal Officer / Registry Officer):**
1. Full Breach Report form completed (all fields including Risk Level and full document set).
2. Case created with Stage = New. DG notified.

Both paths result in a `CasePlaintiff` with auto-generated `FCC/SUING/YYYY/NNN` reference.

---

### C14 — Public Register Publication Workflow

**Trigger:** Secretariat creates a public decision record.

**Stages:**
1. `DRAFT` — Decision drafted (title, background, decision text, linked meeting).
2. `PUBLISHED` — Secretariat publishes. Decision becomes publicly visible (future: via CRM integration).

**Rule:** Only Secretariat can publish.

---

## D. Relationships Between Entities

### D1 — Governance Structure

```
CommitteeType ──< GoverningBody       (one CommitteeType → many GoverningBodies)
GoverningBody ──< Member              (one GoverningBody → many Members)
GoverningBody ──< Meeting             (one GoverningBody → many Meetings)
User (IAM)    ──< Member              (one User → many Members, across multiple bodies)
User (IAM)    ──< GoverningBody       (one User can be Secretary of many bodies [SecretaryUserID[]])
```

### D2 — Determinations & Approvals

```
GoverningBody       ──< SubmissionForDetermination   (one Body → many Submissions targeting it)
SubmissionForDetermination ──0..1── MeetingAgenda    (one Submission → at most one active agenda link)
MeetingAgenda       ──< Resolution                   (one Agenda Item → one Resolution auto-created)
MeetingAgenda       ──< Directive                    (one Agenda Item → many Directives)
```

### D3 — Meeting Governance

```
Meeting     ──< MeetingAgenda        (one Meeting → many Agenda Items)
Meeting     ──< MeetingParticipant   (one Meeting → many Participants)
Meeting     ──1── Minutes            (one Meeting → one Minutes record)
Meeting     ──< Resolution           (one Meeting → many Resolutions)
Meeting     ──< Directive            (one Meeting → many Directives)
MeetingAgenda ──< ConflictDeclaration (one AgendaItem → many Conflict Declarations)
MeetingParticipant references User (from IAM/Corporate Service)
Directive ──0..1── Meeting (FinallyClosedMeetingID — the meeting where it was finally closed)
```

### D4 — Litigation (FCC Sued)

```
CaseDefendant   ──< DirectiveLitigation   (one Case → many DG Directives)
CaseDefendant   ──< FilingDefendant       (one Case → many Filings)
CaseDefendant   ──< ResponseDefendant     (one Case → many Plaintiff Responses)
CaseDefendant   ──< Hearing              (one Case → many Hearings)
Hearing         ──< HearingReport        (one Hearing → many Reports)
CaseDefendant   ──1── SettlementDefendant (one Case → at most one Settlement)
CaseDefendant   ──1── JudgmentDefendant   (one Case → at most one Judgment)
CaseDefendant   ──1── FinancialDefendant  (one Case → one Financial record with child payment/recovery rows)
CaseDefendant   ──< TaskLitigation       (one Case → many Tasks)
JudgmentDefendant ──0..1── FilingDefendant (appeal judgment auto-creates a Notice of Appeal filing)
JudgmentDefendant ──0..1── TaskLitigation  (appeal auto-creates a deadline task)
```

### D5 — Litigation (FCC Suing)

```
CasePlaintiff   ──< DirectiveLitigation   (identical pattern to Defendant)
CasePlaintiff   ──< FilingPlaintiff
CasePlaintiff   ──< ResponsePlaintiff
CasePlaintiff   ──< Hearing
Hearing         ──< HearingReport
CasePlaintiff   ──1── SettlementPlaintiff
CasePlaintiff   ──1── JudgmentPlaintiff
CasePlaintiff   ──1── FinancialPlaintiff
CasePlaintiff   ──< TaskLitigation
JudgmentPlaintiff ──0..1── FilingPlaintiff  (Notice of Appeal on appeal decision)
JudgmentPlaintiff ──0..1── TaskLitigation
```

### D6 — Public Register

```
Meeting ──< PublicDecision   (one Meeting → many Public Decisions can be published from it)
```

### D7 — Document References (Cross-cutting)

```
All document-bearing entities (FilingDefendant, FilingPlaintiff, ResponseDefendant,
ResponsePlaintiff, HearingReport, SettlementDefendant, SettlementPlaintiff,
JudgmentDefendant, JudgmentPlaintiff, Minutes, Directive) reference the
Documents & Records Management Microservice by DocumentID.
Documents are NOT stored in grc-service; only referenced by ID and URL.
```

### D8 — User / Person References (Cross-cutting)

```
All UserID fields (SubmitterUserID, AssignedUserID, SecretaryID, AssignedLegalOfficerID,
IssuedByUserID, etc.) reference the IAM / Corporate Service.
User objects are NOT stored in grc-service; only UserIDs are stored.
```

---

## E. Important Business Rules & Constraints

### E1 — Governance Structure Rules

- **E1.1** Member data is synchronised from the Corporate Service Microservice; grc-service does not own staff records.
- **E1.2** A user can be a member of multiple governing bodies simultaneously.
- **E1.3** A governing body may have multiple secretaries (`SecretaryUserID[]`).
- **E1.4** `MemberType` distinguishes Committee Members from Management Members.
- **E1.5** Administrator can assign a user as Secretary to multiple governing bodies.

### E2 — Submission for Determination Rules

- **E2.1** Any authenticated user can create a Submission for Determination.
- **E2.2** Submissions can only be edited or withdrawn by the originator while `Status = SUBMITTED`.
- **E2.3** Once a submission is linked to a meeting agenda (`Status = UNDER_REVIEW`), it is locked; the originator cannot edit or withdraw it.
- **E2.4** A Secretary can only attach submissions where `TargetBodyID` matches the meeting's `GoverningBodyID`.
- **E2.5** After determination, the outcome and `DeterminationDate` are written back to the submission.

### E3 — Meeting Rules

- **E3.1** Meeting numbers must be auto-generated and unique per governing body using configured prefix and numbering scheme (endless or financial-year). Generation must be atomic to prevent duplicates.
- **E3.2** Secretary can only create meetings for governing bodies to which they are assigned.
- **E3.3** Agenda items must be sourced exclusively from `SubmissionForDetermination` objects; free-text agenda items are not permitted.
- **E3.4** Invitations are sent **automatically** by the system when a meeting is registered (not manually).
- **E3.5** Quorum = (Accepted Members / Total Members) × 100 ≥ 51. Only `InvitationStatus = Accepted` members count. Must be recalculated in real time.
- **E3.6** Meeting can only be initiated (→ ONGOING) when `QuorumMet = true` and current time falls within the meeting schedule.
- **E3.7** Members section is auto-populated when a meeting is created; not manually maintained.
- **E3.8** Invitees (non-members) can view agendas and directives in read-only mode only; they cannot vote.
- **E3.9** Secretary can reschedule if quorum not met; status returns to `REGISTERED` or `DRAFT`.
- **E3.10** A postponed meeting can be resumed within the same instance.
- **E3.11** Once `CLOSED`, no further actions allowed on the meeting.

### E4 — Conflict of Interest Rules

- **E4.1** Members declare conflict at the agenda item level, not at the meeting level.
- **E4.2** A member with a declared conflict on an agenda item is excluded from any vote or determination on that item only.
- **E4.3** Declaring a conflict does not affect the member's participation in other agenda items or future meetings.

### E5 — Directive Rules (Meeting)

- **E5.1** Only the assigned user (person or org unit representative) can perform initial closure of a directive.
- **E5.2** Final closure (`FULLY_CLOSED`) can only be performed by the Secretary in Matters Arising of a **subsequent** meeting.
- **E5.3** Final closure must include a completion summary; evidence document is optional.
- **E5.4** If a directive's due date passes without closure, it auto-transitions to `OVERDUE` and a notification is sent.
- **E5.5** A `FULLY_CLOSED` directive is removed from all future Matters Arising lists.
- **E5.6** All meeting invitees (members and observers) can view directives in read-only mode.
- **E5.7** Directives can be added to any agenda item or Matters Arising item, but only during an ONGOING meeting.

### E6 — Minutes Rules

- **E6.1** Minutes can only be drafted after the meeting is ONGOING or CLOSED; not before.
- **E6.2** Only the Secretary can draft minutes.
- **E6.3** Approval method (majority vote or explicit sign-off) is configurable at the system level.
- **E6.4** Once `APPROVED`, minutes are read-only and final.

### E7 — Resolution Rules

- **E7.1** Resolutions are auto-created by the system from agenda item outcomes; they are not manually created.
- **E7.2** Resolutions are visible only to invited participants (members and invitees) of the respective meeting.
- **E7.3** Resolutions must be searchable within the set of participants who can access them.

### E8 — Case Registration Rules (Litigation)

- **E8.1** FCC Sued case registration can be performed by: Registry Officer, Legal Officer, or Legal Manager.
- **E8.2** Case reference numbers (`FCC/SUED/YYYY/NNN` and `FCC/SUING/YYYY/NNN`) are auto-generated using an atomic sequence per year. No manual entry allowed.
- **E8.3** For FCC Suing: two separate registration forms exist. The simplified form (Department User) does not capture Risk Level or full initiation documents; the full form (Legal Officer/Registry Officer) captures all fields.

### E9 — DG Review Rules (Litigation)

- **E9.1** DG can either issue a directive OR mark the case as reviewed — both are valid outcomes of DG review.
- **E9.2** Issuing a directive transitions the case stage to `Directive Issued`.
- **E9.3** `DirectiveLitigation` is distinct from meeting `Directive` — they are separate entities with separate tracking.

### E10 — Filing Approval Rules (Litigation)

- **E10.1** All filings must go through a two-stage approval: Legal Officer → Legal Manager → DG.
- **E10.2** After DG approval, only the Legal Officer can mark the filing as `FILED` with the actual filing date.
- **E10.3** Digital signatures must be applied at each approval point, stamping the approver's identity and timestamp.
- **E10.4** Notifications are sent at each stage transition.

### E11 — Settlement Rules (Litigation)

- **E11.1** Settlement requires DG approval (via Legal Manager review).
- **E11.2** If a payment amount is specified in a settlement, it automatically appears in the Financials tab.

### E12 — Judgment & Appeal Rules (Litigation)

- **E12.1** After judgment is recorded, Legal Manager reviews and recommends Accept/Appeal to DG.
- **E12.2** DG makes the final decision: Accept or Appeal.
- **E12.3** If DG decides to Appeal, the system **automatically** creates:
  - A Filing of type "Notice of Appeal" (Status = DRAFT), assigned to the Legal Officer.
  - A `TaskLitigation` with the appeal due date as the deadline.
- **E12.4** If the appeal due date passes without the filing being submitted, the task automatically becomes `OVERDUE` and a notification is sent.

### E13 — Financial Rules (Litigation)

- **E13.1** There is NO ERP integration; all financial tracking is manual.
- **E13.2** "Record Recovery" button appears only if judgment outcome = Won.
- **E13.3** "Record Payment" button appears only if judgment outcome = Lost.
- **E13.4** FCC Suing financials include a "Recovered Amount" card not present in FCC Sued.

### E14 — Task Rules (Litigation)

- **E14.1** Reminders are sent automatically at 7, 2, and 1 day before a task's due date.
- **E14.2** If due date passes without closure, task status → `OVERDUE` and notification is sent.
- **E14.3** Tasks may be system-auto-created (e.g., appeal deadlines) or manually created.

### E15 — Case Closure Rules (Litigation)

- **E15.1** Case closure is initiated by the Legal Manager, not the Legal Officer.
- **E15.2** DG must approve closure.
- **E15.3** Once DG approves, the case is read-only; no further editing allowed.
- **E15.4** Archiving occurs after closure, either automatically (after a configurable period) or manually (Administrator or Legal Manager).

### E16 — Public Register Rules

- **E16.1** Only Secretariat can publish a decision.
- **E16.2** Published decisions become visible via the public portal (future CRM integration).

### E17 — Digital Signature Rules

- **E17.1** Signatures must be electronically applied at the point of approval (not deferred).
- **E17.2** The signature stamp must include the approver's full name and timestamp.
- **E17.3** Electronic signature is required for all legally binding approvals (filings, judgments, settlements).

### E18 — Audit Trail Rules

- **E18.1** Every state transition, data modification, conflict declaration, and approval must be logged.
- **E18.2** Audit log fields: EntityID, EntityType, PreviousStatus, NewStatus, ActorID, IPAddress, ActionTimestamp, Comments.
- **E18.3** Audit logs are immutable; no deletion or editing.

### E19 — RBAC & Access Control Rules

- **E19.1** Users can only access cases and meetings they are explicitly assigned to or have role-based permission for.
- **E19.2** Permissions are defined per role per entity/action (full matrix to be designed separately).
- **E19.3** IAM Microservice handles authentication; grc-service enforces authorisation.

### E20 — Integration Constraints

- **E20.1** User/staff data (names, departments, emails) come exclusively from Corporate Service Microservice.
- **E20.2** All documents are stored in the Documents & Records Management Microservice; grc-service stores only DocumentID references and URLs.
- **E20.3** Work Orchestration Service handles cross-service workflow triggers and notification dispatch.
- **E20.4** Corporate Service also provides links to financial processes (Revenue Collection, External Payments under Finance).

---

## F. Summary — Entity Count by Domain

| Domain | Entities |
|---|---|
| Governance Structure | CommitteeType, GoverningBody, Member |
| Determinations & Approvals | SubmissionForDetermination |
| Meeting Governance | Meeting, MeetingAgenda, MeetingParticipant, Directive, Minutes, Resolution |
| Litigation — FCC Sued | CaseDefendant, DirectiveLitigation, FilingDefendant, ResponseDefendant, Hearing, HearingReport, SettlementDefendant, JudgmentDefendant, FinancialDefendant, TaskLitigation |
| Litigation — FCC Suing | CasePlaintiff, FilingPlaintiff, ResponsePlaintiff, SettlementPlaintiff, JudgmentPlaintiff, FinancialPlaintiff *(+ shared: Hearing, HearingReport, DirectiveLitigation, TaskLitigation)* |
| Public Register | PublicDecision |
| **Total distinct entities** | **~22 core entities** |

---

## G. Summary — Workflow Count

| # | Workflow |
|---|---|
| C1 | Submission for Determination lifecycle |
| C2 | Meeting lifecycle (full 9-state machine) |
| C3 | Meeting agenda / determination process |
| C4 | Conflict of interest declaration |
| C5 | Directive lifecycle (Open → Fully Closed, two-actor closure) |
| C6 | Minutes drafting and approval |
| C7 | Litigation case registration (FCC Sued) |
| C8 | DG Review (both modules) |
| C9 | Filing approval (two-stage: LM → DG) |
| C10 | Judgment and appeal (with auto-filing and auto-task creation) |
| C11 | Settlement |
| C12 | Case closure and archiving |
| C13 | Breach report intake — two entry points (FCC Suing) |
| C14 | Public register publication |

---

*End of Domain Extraction*
*Source: Legal_Service.md (Consolidated SRS)*
*This document serves as the sole domain reference for backend design of the Legal Module.*
