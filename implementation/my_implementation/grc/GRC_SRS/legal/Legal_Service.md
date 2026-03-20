# System Requirements Specification (SRS): FCC Legal Services Module
*(Consolidated Technical & Functional Reference)*

## 1. Introduction

### 1.1 Purpose
This document is the consolidated System Requirements Specification (SRS) and Technical Reference for the Fair Competition Commission (FCC) Legal Services module. It defines stakeholder roles, functional requirements, backend logic, workflow states, business rules, and integration points. It serves as the primary reference for designing the API, database schema, and workflow engine.

### 1.2 Scope
The Legal Services module comprises the following functional areas:
- **Meeting Governance:** Full lifecycle of meetings (creation, agenda building from determination submissions, participant management, conflict of interest, quorum, minutes, resolutions, directives).
- **Governance Structures:** Management of committees, governing bodies, members, and secretaries.
- **Determinations & Approvals:** Unified submission process for items requiring formal decision by Management, Commission, or Committee.
- **Litigation – FCC Sued:** End-to-end management of cases where FCC is defendant.
- **Litigation – FCC Suing:** End-to-end management of cases where FCC is plaintiff.
- **Public Register:** Management and publication of finalised decisions.

Cross-cutting capabilities include document management, audit logging, notifications, search/filtering, and integration with Corporate Service, Documents & Records Management, IAM, and Work Orchestration microservices.

---

## Stakeholders & User Roles

| Role | Description |
|---|---|
| System Administrator | Configures master data (committee types, governing bodies, members). Manages access rights and system settings. |
| Secretariat / Governance Officer | Creates meeting packs, schedules meetings, records minutes, resolutions, and directives. Publishes public decisions. Often acts as **Secretary** of a governing body. |
| Management Member / Commissioner / Committee Member | Consumes meeting packs, participates in meetings, receives directives, reviews and approves items. Can declare conflicts of interest. |
| Legal Officer | Manages litigation cases (both FCC sued and suing). Handles filings, hearings, judgments, settlements, tasks, and financials. |
| Legal Manager | Supervises Legal Officers, reviews and recommends filings to DG, manages case assignments, initiates closures. |
| Director General (DG) | Reviews litigation cases, issues directives, approves filings, settlements, and case closures. Decides on appeals. |
| Department User (Submitter) | Creates submissions for determination (breach reports, etc.). Also initiates breach report intake for FCC Suing cases. |
| Registry Officer | Registers new litigation cases (both Sued and Suing). |
| Invitee (Internal Staff) | May be invited to meetings as non-members; can view agendas and directives in read-only mode. |
| Public / External Stakeholder | Accesses the public register of decisions (Integration with FCC CRM). |

---

## 1. Module: Determinations & Approvals (FCC_ SBP_LS_TB_01)
Unified submission process for items requiring formal decision by a governing body.

### 1.1 Object: `SubmissionForDetermination`
- **Attributes:** `SubmissionID`, `Title`, `Description`, `SubmitterUserID`, `SubmitterDept`, `SubmissionDate`, `TargetBodyID` (governing body), `SupportingDocuments[]` (links), `Status` (Submitted/Under Review/Deferred/Approved/Rejected), `OutcomeNotes`, `MeetingID` (where discussed), `DeterminationDate`, `DirectivesCreated[]`.
- **Workflow States:** `SUBMITTED` → `UNDER_REVIEW` (when added to meeting agenda) → `DETERMINED` (after meeting) with outcome (Approved/Rejected/Deferred).
- **Business Rules:**
    1. **Any authenticated user** (Department User, Legal Officer, or any staff member) can create a Submission for Determination.
    2. Submission can be edited/withdrawn by the originator until linked to a meeting agenda.
    3. When added to a meeting agenda, status becomes `UNDER_REVIEW`.
    4. After meeting, outcome recorded and status updated. If approved, any directives are created automatically and linked.

---

### 1.2 Object: Meeting Governance
Manages the complete lifecycle of governance meetings, including agenda creation from determination submissions, participant management, conflict of interest, quorum, minutes, resolutions, and directives.

### 1.2.1 Object: `Meeting`
- **Attributes:** `MeetingID`, `Title` (predefined types), `MeetingNumber` (auto-generated with prefix and numbering scheme), `Location`, `Mode` (Physical/Virtual/Hybrid), `VenueLink`, `StartDateTime`, `EndDateTime`, `Type` (Ordinary/Extraordinary/Special), `GoverningBodyID`, `AgendaSummary`, `Status`, `QuorumMet` (boolean), `QuorumPercentage`, `SecretaryID`, `CreatedAt`, `UpdatedAt`.
- **Workflow States:** `DRAFT` → `REGISTERED` → `INVITATIONS_SENT` → `AGENDA_SHARED` → `QUORUM_READY` → `ONGOING` → `POSTPONED` → `CLOSED` | `CANCELLED` | `RESCHEDULED`.
- **Business Rules:**
    1. **Meeting Number Generation:** Must generate unique numbers per governing body using a configured prefix and either endless sequence (`<PREFIX>-NNN`) or financial year format (`<PREFIX>/YYYY-YYYY/NNN`). Sequence must be atomic to avoid duplicates.
    2. **Agenda Population:** Agenda items are sourced from `SubmissionForDetermination` objects where `TargetBodyID` matches the meeting's `GoverningBodyID` and `Status` is not yet determined. Secretary selects items; selected items become `MeetingAgenda` records.
    3. **Matters Arising:** Automatically populate from unresolved `Directive` records where `GoverningBodyID` matches and `FinallyClosed = false`.
    4. **Quorum Calculation:** Quorum is met when ≥51% of members of the governing body have accepted invitations. Calculation must consider only members with `Accept` response. If quorum not met by `StartDateTime`, Secretary can reschedule (status returns to `REGISTERED` or `DRAFT`).
    5. **Auto-Populate Members:** When a meeting is created for a governing body, the system automatically populates the Members section with all active members of that governing body.
    6. **Invitees:** The Secretary can invite additional internal staff (non-members) via the Invitees section. Invitees can view agendas and directives but cannot vote.
    7. **Conflict of Interest:** Members can declare conflict on specific agenda items. System records conflict and excludes member from any votes/determinations on that item. Conflict record does not affect future meeting participation.
    8. **Meeting Start:** Only allowed if `QuorumMet = true` and current time is within meeting schedule. Secretary triggers start; status becomes `ONGOING`.
    9. **Directives During Meeting:** During an ongoing meeting, the Secretary can add new directives to any agenda item or Matters Arising item, specifying description, assignee (person/org unit), priority (Critical/High/Medium/Low), and due date.
    10. **Postponement:** Secretary can postpone an ongoing meeting; status becomes `POSTPONED`. Meeting can be resumed later within same instance.
    11. **Closure:** Secretary closes meeting when all business concluded; status becomes `CLOSED`. No further actions allowed.

### 1.2.2 Object: `MeetingAgenda`
- **Attributes:** `AgendaID`, `MeetingID`, `SubmissionID` (link to determination submission), `Order`, `Title`, `Description`, `Documents[]` (links), `ConflictDeclarations[]` (list of member IDs), `Outcome` (determination result), `DirectivesCreated[]`.
- **Business Rules:**
    1. Agenda items from submissions: after meeting, outcome is recorded and propagated back to the original `SubmissionForDetermination`.
    2. If a member declares conflict on this agenda, their vote/determination is not counted.

### 1.2.3 Object: `MeetingParticipant`
- **Attributes:** `ParticipantID`, `MeetingID`, `UserID`, `Role` (Member/Invitee), `InvitationStatus` (Pending/Accepted/Declined), `DeclineReason`, `AttendanceMarked` (boolean for actual attendance during ongoing meeting).
- **Business Rules:**
    1. Invitations sent automatically after meeting registration. Responses recorded.
    2. Only members with `InvitationStatus = Accepted` are counted for quorum.
    3. During ongoing meeting, Secretary may mark attendance manually (optional).

### 1.2.4 Object: `Directive`
- **Attributes:** `DirectiveID`, `MeetingID`, `AgendaID` (optional), `Description`, `Category`, `Priority` (Critical/High/Medium/Low), `AssignedOrgUnit`, `AssignedUserID`, `DueDate`, `Status` (Open/In Progress/Overdue/Closed), `CompletionSummary`, `CompletionDate`, `EvidenceDocumentID`, `FinallyClosed` (boolean), `FinallyClosedMeetingID` (meeting where finally closed).
- **Workflow States:** `OPEN` → `IN_PROGRESS` (optional) → `CLOSED` (initial closure by assignee) → `FULLY_CLOSED` (by Secretary in Matters Arising).
- **Business Rules:**
    1. Only the assigned user can perform initial closure (mark as `CLOSED` with summary).
    2. Final closure can only be done by Secretary in a subsequent meeting’s Matters Arising, after reviewing completion. This sets `FinallyClosed = true` and removes from future Matters Arising.
    3. If due date passes without closure, status becomes `OVERDUE` automatically, with notifications.
    4. All meeting invitees can view directives in read-only mode.

### 1.2.5 Object: `Minutes`
- **Attributes:** `MinutesID`, `MeetingID`, `Title`, `Content`, `Attachments[]`, `Status` (Draft/Pending Approval/Approved), `CreatedBy`, `ApprovedBy[]`, `ApprovalDate`.
- **Workflow States:** `DRAFT` → `PENDING_APPROVAL` → `APPROVED`.
- **Business Rules:**
    1. After meeting, Secretary drafts minutes and submits for approval to participating members.
    2. Approval may be by majority vote or explicit sign-off (configurable). Upon approval, status becomes `APPROVED` and minutes are final.

### 1.2.6 Object: `Resolution`
- **Attributes:** `ResolutionID`, `MeetingID`, `AgendaID`, `ResolutionText`, `DateAdopted`, `Status` (Approved/Rejected/Noted), `ResponsiblePerson`, `EffectiveDate`, `Attachments[]`.
- **Business Rules:**
    1. Automatically created from agenda outcomes. Visible only to meeting invitees.
    2. Resolutions are searchable by invited participants.

### 1.2.7 Audit for Meetings
- Every state change, conflict declaration, directive update, minutes approval must be logged in `AuditTrail`.

---

## 2. Module: Governance Structure
Manages committees, governing bodies, and members.

### 2.1 Object: `CommitteeType`
- **Attributes:** `TypeID`, `Name`, `Description`, `Status` (Active/Inactive), `CreatedAt`, `UpdatedAt`.
- **Admin Actions:** Administrator can configure (create, edit, activate/deactivate) Committee Types.

### 2.2 Object: `GoverningBody`
- **Attributes:** `BodyID`, `TypeID` (link to CommitteeType), `Name`, `CompositeTitle`, `Description`, `Status` (Active/Deactivated), `SecretaryUserID[]` (multiple secretaries allowed), `CreatedAt`, `UpdatedAt`.
- **Admin Actions:** Administrator can manage Governing Bodies and assign one or more users as Secretary to each body.

### 2.3 Object: `Member`
- **Attributes:** `MemberID`, `UserID`, `BodyID`, `Position` (Member/Secretary/Chairman), `MemberType` (Committee Member/Management Member), `Email` (sync from HR), `Department`, `Status` (Active/Inactive), `JoinedDate`, `LeftDate`, `CreatedAt`, `UpdatedAt`.
- **Business Rules:**
    1. Member data is synchronized with Corporate Service Microservice.
    2. A user can be a member of multiple bodies.
    3. Administrator manages both **Committee Members** and **Management Members** through this module. `MemberType` distinguishes the two.
    4. Administrator can assign users as Secretary to multiple governing bodies.


---

## 3. Module: Public Register 
Manages published decisions.

### 3.1 Object: `PublicDecision`
- **Attributes:** `DecisionID`, `Title`, `MeetingID` (link), `BodyText`, `DecisionText`, `DecisionDate`, `Status` (Draft/Published), `PublishedDate`, `CreatedBy`, `UpdatedAt`.
- **Workflow States:** `DRAFT` → `PUBLISHED`.
- **Business Rules:**
    1. Only Secretariat can publish.
    2. Published decisions become visible via public portal (future).

---


## 4. Module: Litigation – FCC Sued (FCC_ SBP_LS_TB_02)
Manages cases where FCC is defendant.

### 4.0 Dashboard & Case List
- **Dashboard KPIs:** Total Cases Filed, Won/Loss Ratio, Cases on Appeal, High Risk Cases, Active Cases, Pending DG Review.
- **Case List Columns:** Case Ref No, Respondent, Case Type, Court, Claim Amount, Stage, Status, Risk, Next Hearing, Actions.
- Users can filter the case list and perform a global search.
- Visible to all authorised users.

### 4.1 Object: `CaseDefendant`
- **Attributes:** `CaseID` (auto `FCC/SUED/YYYY/NNN`), `CourtCaseNumber`, `CourtRegistry`, `CourtLevel`, `ServiceDate`, `Plaintiffs[]` (repeatable), `PlaintiffAdvocate`, `ClaimAmount`, `NatureOfClaim`, `DepartmentAffected`, `UrgencyLevel`, `RiskLevel`, `InitiationDocuments[]` (each with Title, Type, DocumentID), `Stage` (New/Under DG Review/Directive Issued/Hearing Stage/Judgment Received/Appeal Filed/Closed/On Hold), `DGReviewStatus` (Pending/Reviewed/Directive Issued), `AssignedLegalOfficerID[]`, `AssignedLegalManagerID`, `NextHearingDate`, `CreatedAt`, `UpdatedAt`.
- **Workflow States:** (as per stage list) – transitions controlled by actions.
- **Business Rules:**
    1. Case registration can be performed by a Registry Officer, Legal Officer, or Legal Manager.

### 4.2 Object: `DirectiveLitigation` (separate from meeting directives)
- **Attributes:** `DirectiveID`, `CaseID`, `IssuedByUserID` (DG), `IssueDate`, `Instruction`, `DueDate`, `Status` (Open/In Progress/Closed), `CompletionSummary`, `CompletionDate`, `Attachments[]`.
- **Business Rules:**
    1. Issued by DG during case review or at any time.
    2. DG can also mark a case as **Reviewed** without issuing a directive — both actions are available during DG review.
    3. Legal Officer/Manager can update status; closure may require DG approval (configurable).

### 4.3 Object: `FilingDefendant`(FCC_ SBP_LS_TB_04)
- **Attributes:** `FilingID`, `CaseID`, `Type` (Statement of Defence/Affidavit/Application/etc.), `Title`, `DocumentID`, `Version`, `Status` (Draft/Under Review (LM)/Approved by LM/Under Review (DG)/Approved/Filed), `SubmittedByUserID`, `ApprovalChain` (logs of reviews).
- **Workflow States:** `DRAFT` → `UNDER_REVIEW_LM` → `APPROVED_LM` → `UNDER_REVIEW_DG` → `APPROVED` → `FILED`.
- **Business Rules:**
    1. Two-stage approval: Legal Officer → Legal Manager → DG. Notifications at each step.
    2. After DG approval, Legal Officer can mark as `FILED` with actual filing date.

### 4.4 Object: `ResponseDefendant` (documents from plaintiff)
- **Attributes:** `ResponseID`, `CaseID`, `Type` (Preliminary Objections/Response to Ruling/Counter Claim/etc.), `ReceivedDate`, `DocumentID`, `Description`.

### 4.5 Object: `Hearing`
- **Attributes:** `HearingID`, `CaseID`, `HearingDate`, `Court`, `Judge`, `Notes`.

### 4.6 Object: `HearingReport`
- **Attributes:** `ReportID`, `HearingID`, `ReportType` (Proceedings/Ruling/Order), `Summary`, `Remarks`, `NextHearingDate`, `AttachmentID`.
- **Business Rules:**
    1. Multiple reports can be attached to one hearing.
    2. The most recent `NextHearingDate` from any report updates the parent case's `NextHearingDate`.

### 4.7 Object: `SettlementDefendant`
- **Attributes:** `SettlementID`, `CaseID`, `SettlementDate`, `Terms` (text), `PaymentAmount` (optional), `AgreementDocumentID`, `Status` (Proposed/Agreed/Rejected).
- **Business Rules:**
    1. Requires DG approval (via Legal Manager review).
    2. If payment amount is specified, it will appear in Finance tab.

### 4.8 Object: `JudgmentDefendant`
- **Attributes:** `JudgmentID`, `CaseID`, `JudgmentDate`, `Outcome` (Won/Lost), `AmountAwarded`, `LegalCostsAwarded`, `OtherCosts` (array of {type, amount}), `DocumentID`, `Remarks`, `DGDecision` (Accept/Appeal), `AppealDueDate` (if Appeal), `AppealFilingID` (link to filing if created).
- **Business Rules:**
    1. After judgment recorded, Legal Manager reviews and recommends to DG.
    2. DG decides: Accept (case proceeds to closure/financials) or Appeal (set due date). If Appeal, system creates a `FilingDefendant` of type "Notice of Appeal" and a task.
    3. If Appeal due date passes without filing, task becomes overdue.

### 4.9 Object: `FinancialDefendant`
- **Attributes:** `FinancialID`, `CaseID`, `ClaimAmount`, `LegalCostsIncurred`, `CostsAwarded`, `OtherCosts` (aggregated), `Recoveries[]` (if won), `Payments[]` (if lost).
- **Recovery/Payment Records:** Each record has `Date`, `Amount`, `Reference`, `Status` (Requested/Approved/Processed).
- **Business Rules:**
    1. No ERP integration; manual tracking.
    2. Buttons "Record Recovery" and "Record Payment" appear based on judgment outcome.

### 4.10 Object: `TaskLitigation`
- **Attributes:** `TaskID`, `CaseID`, `Title`, `AssignedToUserID`, `DueDate`, `Status` (Open/In Progress/Overdue/Closed), `Priority`, `RelatedEntityType`, `RelatedEntityID`.
- **Business Rules:**
    1. Auto-created for appeal deadlines, filing approvals, etc.
    2. Reminders at 7, 2, 1 day before due date; overdue notification.

### 4.11 Case Folder Link
- Each case has a `CaseFolderURL` pointing to document repository.

### 4.12 Activity Log
- All actions logged with user, timestamp, description.

### 4.13 Report Tab
- A chronological timeline view of all case events (registration, filings, hearings, directives, judgments, settlements, closures) is available to all authorised users.

### 4.14 Case Closure
- Legal Manager initiates; DG approves. After approval, case becomes read-only.

### 4.15 Archiving
- Configurable automatic or manual archiving after closure period.

---

## 5. Module: Litigation – FCC Suing (FCC_ SBP_LS_TB_03)
Manages cases where FCC is plaintiff. Similar structure to defendant module but with different filing/response types and registration forms.

### 5.0 Dashboard & Case List
- **Dashboard KPIs:** Total Cases Filed, Won/Loss Ratio, Cases on Appeal, High Risk Cases, Active Cases, Pending DG Review, Recoverable Amount, Recovered Amount.
- **Case List Columns:** Case Ref No, Respondent, Case Type, Court, Claim Amount, Stage, Status, Risk, Next Hearing, Actions.
- Users can filter the case list and perform a global search.
- Visible to all authorised users.

### 5.1 Object: `CasePlaintiff`
- **Attributes:** `CaseID` (auto `FCC/SUING/YYYY/NNN`), `ReportingDepartment`, `NatureOfBreach`, `RespondentName`, `RespondentType`, `EstimatedClaimAmount`, `Description`, `UrgencyLevel`, `RiskLevel`, `InitiationDocuments[]` (for full registration), `Stage` (similar to defendant), `DGReviewStatus`, `AssignedLegalOfficerID[]`, `AssignedLegalManagerID`, `NextHearingDate`, `CreatedAt`, `UpdatedAt`.
- **Registration Interfaces (two entry points):**
    - **Breach Report Intake (simplified):** Initiated by a Department User. Captures: Reporting Department, Nature of Breach, Respondent Name, Respondent Type, Description, Urgency Level, and optional supporting document. Creates a case with stage = New.
    - **Full Breach Report:** Initiated by a Legal Officer or Registry Officer. Captures all simplified fields plus: Estimated Claim Amount, Risk Level, and full Initiation Documents array. Creates a case with stage = New.
    - Both interfaces result in a `CasePlaintiff` record with an auto-generated `FCC/SUING/YYYY/NNN` reference number.

### 5.2 Object: `FilingPlaintiff` (FCC_ SBP_LS_TB_04)
- **Types:** Plaint, Petition, Statement of Claim, Application, Chamber Summons, Affidavit, Bill of Cost, Notice of Appeal.
- Same two-stage approval workflow as defendant.

### 5.3 Object: `ResponsePlaintiff`
- **Types:** Preliminary Objections, Response to Ruling, Response to Orders, Response to Affidavits, Counter Claim, Initial Response, Preliminary Objectives.
- Same recording as defendant.

### 5.4 Object: `Hearing`, `HearingReport` – identical to defendant.

### 5.5 Object: `SettlementPlaintiff` – identical to defendant.

### 5.6 Object: `JudgmentPlaintiff`
- Same fields as defendant judgment, plus DG decision to accept or appeal. If appeal, create filing "Notice of Appeal".

### 5.7 Object: `FinancialPlaintiff`
- Cards: Claim Amount, Legal Costs Incurred, Amount Awarded, Costs Awarded, Other Costs, Recovered Amount.
- Buttons: Record Recovery (if won), Record Payment (if lost).

### 5.8 Tasks, Case Folder, Report Tab, Activity Log, Closure, Archiving – identical to defendant.


---

## 6. Global Backend Logic & Constraints

### 6.1 Digital Signature Engine
- **Storage:** Encrypted signatures associated with User IDs (DG, Legal Manager, etc.).
- **Logic:** Signatures must be stamped on approval documents (e.g., filed documents, judgments, settlement agreements) at the moment of approval. The stamp must include a timestamp and user's full name. Electronic signature required for all legally binding approvals.

### 6.2 Unique Identifier Generation
- **Case Numbers:** `FCC/SUED/YYYY/NNN` and `FCC/SUING/YYYY/NNN` – sequence per year, atomic.
- **Meeting Numbers:** Prefixes defined per governing body, with either endless or financial-year sequence. Use database sequences with appropriate formatting.

### 6.3 Audit Trail
- Every state transition, data modification, conflict declaration, and approval must be logged in an `AuditTrail` table.
- Fields: `EntityID`, `EntityType`, `PreviousStatus`, `NewStatus`, `ActorID`, `IPAddress`, `ActionTimestamp`, `Comments`.

### 6.4 Notifications Engine
- Events trigger notifications (email/in-app) to relevant users based on role and assignment.
- Examples: new case registered (to DG), filing ready for review (to Legal Manager), filing approved (to Legal Officer), task reminders, appeal due date.

### 6.5 Integration Points
- **Corporate Service Microservice:** For user details, departments, org units. Must sync staff data. Also provides links to financial processes (Revenue Collection and External Payments under Finance).
- **Documents and Records Management Microservice:** Store all documents; return document IDs and links. Provide folder structure per case.
- **IAM Microservice:** Authentication and role-based access control.
- **Work Orchestration Service:** Interconnects processes across microservices. Manages cross-service notifications, task reminders, and workflow triggers.

### 6.6 Role-Based Access Control (RBAC)
- Permissions defined per role per entity/action. (Matrix to be detailed separately.)
- System must enforce that users can only access cases/meetings they are assigned to or have explicit permission for.

### 6.7 Quorum Calculation (Meeting)
- Must use real-time acceptance status. Quorum = (number of accepted members / total members) * 100 ≥ 51.

### 6.8 Conflict of Interest Handling
- Record conflict; exclude member from any decision/vote on that agenda. Do not affect future meeting participation.


---

## 7. Entity Relationship Context
- **User:** (From IAM/Corporate Service)
- **GoverningBody:** (Parent to Meeting, Member)
- **Meeting:** (Parent to MeetingAgenda, MeetingParticipant, Minutes, Resolution, Directive)
- **SubmissionForDetermination:** (Linked to MeetingAgenda)
- **CaseDefendant / CasePlaintiff:** (Parent to Filing, Response, Hearing, Settlement, Judgment, Financial, Task)
- **Document:** (Stored in Documents Microservice, referenced by ID in multiple entities)

---

*End of Document*