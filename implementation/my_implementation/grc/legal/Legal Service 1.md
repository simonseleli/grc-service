# Technical Functional Requirements Specification: FCC Legal Services Module

## 1. Introduction
This document defines the backend logic, workflow states, and business rules for the Fair Competition Commission (FCC) Legal Services module. It serves as the primary reference for designing the API, database schema, and workflow engine. The module covers governance meetings, litigation management (both as defendant and plaintiff), determinations, and public registers.

---

## 2. Module: Meeting Governance (FCC_LGL_TB_01)
Manages the complete lifecycle of governance meetings, including agenda creation from determination submissions, participant management, conflict of interest, quorum, minutes, resolutions, and directives.

### 2.1 Object: `Meeting`
- **Attributes:** `MeetingID`, `Title` (predefined types), `MeetingNumber` (auto-generated with prefix and numbering scheme), `Location`, `Mode` (Physical/Virtual/Hybrid), `VenueLink`, `StartDateTime`, `EndDateTime`, `Type` (Ordinary/Extraordinary/Special), `GoverningBodyID`, `AgendaSummary`, `Status`, `QuorumMet` (boolean), `QuorumPercentage`, `SecretaryID`, `CreatedAt`, `UpdatedAt`.
- **Workflow States:** `DRAFT` → `REGISTERED` → `INVITATIONS_SENT` → `AGENDA_SHARED` → `QUORUM_READY` → `ONGOING` → `POSTPONED` → `CLOSED` | `CANCELLED` | `RESCHEDULED`.
- **Business Rules:**
    1. **Meeting Number Generation:** Must generate unique numbers per governing body using a configured prefix and either endless sequence (`<PREFIX>-NNN`) or financial year format (`<PREFIX>/YYYY-YYYY/NNN`). Sequence must be atomic to avoid duplicates.
    2. **Agenda Population:** Agenda items are sourced from `SubmissionForDetermination` objects where `TargetBodyID` matches the meeting's `GoverningBodyID` and `Status` is not yet determined. Secretary selects items; selected items become `MeetingAgenda` records.
    3. **Matters Arising:** Automatically populate from unresolved `Directive` records where `GoverningBodyID` matches and `FinallyClosed = false`.
    4. **Quorum Calculation:** Quorum is met when ≥51% of members of the governing body have accepted invitations. Calculation must consider only members with `Accept` response. If quorum not met by `StartDateTime`, Secretary can reschedule (status returns to `REGISTERED` or `DRAFT`).
    5. **Conflict of Interest:** Members can declare conflict on specific agenda items. System records conflict and excludes member from any votes/determinations on that item. Conflict record does not affect future meeting participation.
    6. **Meeting Start:** Only allowed if `QuorumMet = true` and current time is within meeting schedule. Secretary triggers start; status becomes `ONGOING`.
    7. **Postponement:** Secretary can postpone an ongoing meeting; status becomes `POSTPONED`. Meeting can be resumed later within same instance.
    8. **Closure:** Secretary closes meeting when all business concluded; status becomes `CLOSED`. No further actions allowed.

### 2.2 Object: `MeetingAgenda`
- **Attributes:** `AgendaID`, `MeetingID`, `SubmissionID` (link to determination submission), `Order`, `Title`, `Description`, `Documents[]` (links), `ConflictDeclarations[]` (list of member IDs), `Outcome` (determination result), `DirectivesCreated[]`.
- **Business Rules:**
    1. Agenda items from submissions: after meeting, outcome is recorded and propagated back to the original `SubmissionForDetermination`.
    2. If a member declares conflict on this agenda, their vote/determination is not counted.

### 2.3 Object: `MeetingParticipant`
- **Attributes:** `ParticipantID`, `MeetingID`, `UserID`, `Role` (Member/Invitee), `InvitationStatus` (Pending/Accepted/Declined), `DeclineReason`, `AttendanceMarked` (boolean for actual attendance during ongoing meeting).
- **Business Rules:**
    1. Invitations sent automatically after meeting registration. Responses recorded.
    2. Only members with `InvitationStatus = Accepted` are counted for quorum.
    3. During ongoing meeting, Secretary may mark attendance manually (optional).

### 2.4 Object: `Directive`
- **Attributes:** `DirectiveID`, `MeetingID`, `AgendaID` (optional), `Description`, `Category`, `Priority` (Critical/High/Medium/Low), `AssignedOrgUnit`, `AssignedUserID`, `DueDate`, `Status` (Open/In Progress/Overdue/Closed), `CompletionSummary`, `CompletionDate`, `EvidenceDocumentID`, `FinallyClosed` (boolean), `FinallyClosedMeetingID` (meeting where finally closed).
- **Workflow States:** `OPEN` → `IN_PROGRESS` (optional) → `CLOSED` (initial closure by assignee) → `FULLY_CLOSED` (by Secretary in Matters Arising).
- **Business Rules:**
    1. Only the assigned user can perform initial closure (mark as `CLOSED` with summary).
    2. Final closure can only be done by Secretary in a subsequent meeting’s Matters Arising, after reviewing completion. This sets `FinallyClosed = true` and removes from future Matters Arising.
    3. If due date passes without closure, status becomes `OVERDUE` automatically, with notifications.

### 2.5 Object: `Minutes`
- **Attributes:** `MinutesID`, `MeetingID`, `Title`, `Content`, `Attachments[]`, `Status` (Draft/Pending Approval/Approved), `CreatedBy`, `ApprovedBy[]`, `ApprovalDate`.
- **Workflow States:** `DRAFT` → `PENDING_APPROVAL` → `APPROVED`.
- **Business Rules:**
    1. After meeting, Secretary drafts minutes and submits for approval to participating members.
    2. Approval may be by majority vote or explicit sign-off (configurable). Upon approval, status becomes `APPROVED` and minutes are final.

### 2.6 Object: `Resolution`
- **Attributes:** `ResolutionID`, `MeetingID`, `AgendaID`, `ResolutionText`, `DateAdopted`, `Status` (Approved/Rejected/Noted), `ResponsiblePerson`, `EffectiveDate`, `Attachments[]`.
- **Business Rules:**
    1. Automatically created from agenda outcomes. Visible only to meeting invitees.

### 2.7 Audit for Meetings
- Every state change, conflict declaration, directive update, minutes approval must be logged in `AuditTrail`.

---

## 3. Module: Governance Structure (FCC_LGL_TB_02)
Manages committees, governing bodies, and members.

### 3.1 Object: `CommitteeType`
- **Attributes:** `TypeID`, `Name`, `Description`, `Status` (Active/Inactive), `CreatedAt`, `UpdatedAt`.

### 3.2 Object: `GoverningBody`
- **Attributes:** `BodyID`, `TypeID` (link to CommitteeType), `Name`, `CompositeTitle`, `Description`, `Status` (Active/Deactivated), `SecretaryUserID[]` (multiple secretaries allowed), `CreatedAt`, `UpdatedAt`.

### 3.3 Object: `Member`
- **Attributes:** `MemberID`, `UserID`, `BodyID`, `Position` (Member/Secretary/Chairman), `Email` (sync from HR), `Department`, `Status` (Active/Inactive), `JoinedDate`, `LeftDate`, `CreatedAt`, `UpdatedAt`.
- **Business Rules:**
    1. Member data is synchronized with Corporate Service Microservice.
    2. A user can be a member of multiple bodies.

---

## 4. Module: Determinations & Approvals (FCC_LGL_TB_03)
Unified submission process for items requiring formal decision by a governing body.

### 4.1 Object: `SubmissionForDetermination`
- **Attributes:** `SubmissionID`, `Title`, `Description`, `SubmitterUserID`, `SubmitterDept`, `SubmissionDate`, `TargetBodyID` (governing body), `SupportingDocuments[]` (links), `Status` (Submitted/Under Review/Deferred/Approved/Rejected), `OutcomeNotes`, `MeetingID` (where discussed), `DeterminationDate`, `DirectivesCreated[]`.
- **Workflow States:** `SUBMITTED` → `UNDER_REVIEW` (when added to meeting agenda) → `DETERMINED` (after meeting) with outcome (Approved/Rejected/Deferred).
- **Business Rules:**
    1. Submission can be edited/withdrawn by submitter until linked to a meeting agenda.
    2. When added to a meeting agenda, status becomes `UNDER_REVIEW`.
    3. After meeting, outcome recorded and status updated. If approved, any directives are created automatically and linked.

---

## 5. Module: Litigation – FCC Sued (FCC_LGL_TB_04)
Manages cases where FCC is defendant.

### 5.1 Object: `CaseDefendant`
- **Attributes:** `CaseID` (auto `FCC/SUED/YYYY/NNN`), `CourtCaseNumber`, `CourtRegistry`, `CourtLevel`, `ServiceDate`, `Plaintiffs[]` (repeatable), `PlaintiffAdvocate`, `ClaimAmount`, `NatureOfClaim`, `DepartmentAffected`, `UrgencyLevel`, `RiskLevel`, `InitiationDocuments[]` (each with Title, Type, DocumentID), `Stage` (New/Under DG Review/Directive Issued/Hearing Stage/Judgment Received/Appeal Filed/Closed/On Hold), `DGReviewStatus` (Pending/Reviewed/Directive Issued), `AssignedLegalOfficerID[]`, `AssignedLegalManagerID`, `NextHearingDate`, `CreatedAt`, `UpdatedAt`.
- **Workflow States:** (as per stage list) – transitions controlled by actions.

### 5.2 Object: `DirectiveLitigation` (separate from meeting directives)
- **Attributes:** `DirectiveID`, `CaseID`, `IssuedByUserID` (DG), `IssueDate`, `Instruction`, `DueDate`, `Status` (Open/In Progress/Closed), `CompletionSummary`, `CompletionDate`, `Attachments[]`.
- **Business Rules:**
    1. Issued by DG during review or at any time.
    2. Legal Officer/Manager can update status; closure may require DG approval (configurable).

### 5.3 Object: `FilingDefendant`
- **Attributes:** `FilingID`, `CaseID`, `Type` (Statement of Defence/Affidavit/Application/etc.), `Title`, `DocumentID`, `Version`, `Status` (Draft/Under Review (LM)/Approved by LM/Under Review (DG)/Approved/Filed), `SubmittedByUserID`, `ApprovalChain` (logs of reviews).
- **Workflow States:** `DRAFT` → `UNDER_REVIEW_LM` → `APPROVED_LM` → `UNDER_REVIEW_DG` → `APPROVED` → `FILED`.
- **Business Rules:**
    1. Two-stage approval: Legal Officer → Legal Manager → DG. Notifications at each step.
    2. After DG approval, Legal Officer can mark as `FILED` with actual filing date.

### 5.4 Object: `ResponseDefendant` (documents from plaintiff)
- **Attributes:** `ResponseID`, `CaseID`, `Type` (Preliminary Objections/Response to Ruling/Counter Claim/etc.), `ReceivedDate`, `DocumentID`, `Description`.

### 5.5 Object: `Hearing`
- **Attributes:** `HearingID`, `CaseID`, `HearingDate`, `Court`, `Judge`, `Notes`.

### 5.6 Object: `HearingReport`
- **Attributes:** `ReportID`, `HearingID`, `ReportType` (Proceedings/Ruling/Order), `Summary`, `Remarks`, `NextHearingDate`, `AttachmentID`.
- **Business Rules:**
    1. Multiple reports can be attached to one hearing.
    2. The most recent `NextHearingDate` from any report updates the parent case's `NextHearingDate`.

### 5.7 Object: `SettlementDefendant`
- **Attributes:** `SettlementID`, `CaseID`, `SettlementDate`, `Terms` (text), `PaymentAmount` (optional), `AgreementDocumentID`, `Status` (Proposed/Agreed/Rejected).
- **Business Rules:**
    1. Requires DG approval (via Legal Manager review).
    2. If payment amount is specified, it will appear in Finance tab.

### 5.8 Object: `JudgmentDefendant`
- **Attributes:** `JudgmentID`, `CaseID`, `JudgmentDate`, `Outcome` (Won/Lost), `AmountAwarded`, `LegalCostsAwarded`, `OtherCosts` (array of {type, amount}), `DocumentID`, `Remarks`, `DGDecision` (Accept/Appeal), `AppealDueDate` (if Appeal), `AppealFilingID` (link to filing if created).
- **Business Rules:**
    1. After judgment recorded, Legal Manager reviews and recommends to DG.
    2. DG decides: Accept (case proceeds to closure/financials) or Appeal (set due date). If Appeal, system creates a `FilingDefendant` of type "Notice of Appeal" and a task.
    3. If Appeal due date passes without filing, task becomes overdue.

### 5.9 Object: `FinancialDefendant`
- **Attributes:** `FinancialID`, `CaseID`, `ClaimAmount`, `LegalCostsIncurred`, `CostsAwarded`, `OtherCosts` (aggregated), `Recoveries[]` (if won), `Payments[]` (if lost).
- **Recovery/Payment Records:** Each record has `Date`, `Amount`, `Reference`, `Status` (Requested/Approved/Processed).
- **Business Rules:**
    1. No ERP integration; manual tracking.
    2. Buttons "Record Recovery" and "Record Payment" appear based on judgment outcome.

### 5.10 Object: `TaskLitigation`
- **Attributes:** `TaskID`, `CaseID`, `Title`, `AssignedToUserID`, `DueDate`, `Status` (Open/In Progress/Overdue/Closed), `Priority`, `RelatedEntityType`, `RelatedEntityID`.
- **Business Rules:**
    1. Auto-created for appeal deadlines, filing approvals, etc.
    2. Reminders at 7, 2, 1 day before due date; overdue notification.

### 5.11 Case Folder Link
- Each case has a `CaseFolderURL` pointing to document repository.

### 5.12 Activity Log
- All actions logged with user, timestamp, description.

### 5.13 Case Closure
- Legal Manager initiates; DG approves. After approval, case becomes read-only.

### 5.14 Archiving
- Configurable automatic or manual archiving after closure period.

---

## 6. Module: Litigation – FCC Suing (FCC_LGL_TB_05)
Manages cases where FCC is plaintiff. Similar structure to defendant module but with different filing/response types and registration forms.

### 6.1 Object: `CasePlaintiff`
- **Attributes:** `CaseID` (auto `FCC/SUING/YYYY/NNN`), `ReportingDepartment`, `NatureOfBreach`, `RespondentName`, `RespondentType`, `EstimatedClaimAmount`, `Description`, `UrgencyLevel`, `RiskLevel`, `InitiationDocuments[]` (for full registration), `Stage` (similar to defendant), `DGReviewStatus`, `AssignedLegalOfficerID[]`, `AssignedLegalManagerID`, `NextHearingDate`, `CreatedAt`, `UpdatedAt`.
- **Registration Interfaces:**
    - **Breach Report Intake (simplified):** fields as per FR‑SUING‑03.
    - **Full Report Breach:** fields as per FR‑SUING‑03.
    - Both create a case with stage = New.

### 6.2 Object: `FilingPlaintiff`
- **Types:** Plaint, Petition, Statement of Claim, Application, Chamber Summons, Affidavit, Bill of Cost, Notice of Appeal.
- Same two-stage approval workflow as defendant.

### 6.3 Object: `ResponsePlaintiff`
- **Types:** Preliminary Objections, Response to Ruling, Response to Orders, Response to Affidavits, Counter Claim, Initial Response, Preliminary Objectives.
- Same recording as defendant.

### 6.4 Object: `Hearing`, `HearingReport` – identical to defendant.

### 6.5 Object: `SettlementPlaintiff` – identical to defendant.

### 6.6 Object: `JudgmentPlaintiff`
- Same fields as defendant judgment, plus DG decision to accept or appeal. If appeal, create filing "Notice of Appeal".

### 6.7 Object: `FinancialPlaintiff`
- Cards: Claim Amount, Legal Costs Incurred, Amount Awarded, Costs Awarded, Other Costs, Recovered Amount.
- Buttons: Record Recovery (if won), Record Payment (if lost).

### 6.8 Tasks, Case Folder, Activity Log, Closure, Archiving – identical to defendant.

---

## 7. Module: Public Register (FCC_LGL_TB_06)
Manages published decisions.

### 7.1 Object: `PublicDecision`
- **Attributes:** `DecisionID`, `Title`, `MeetingID` (link), `BodyText`, `DecisionText`, `DecisionDate`, `Status` (Draft/Published), `PublishedDate`, `CreatedBy`, `UpdatedAt`.
- **Workflow States:** `DRAFT` → `PUBLISHED`.
- **Business Rules:**
    1. Only Secretariat can publish.
    2. Published decisions become visible via public portal (future).

---

## 8. Global Backend Logic & Constraints

### 8.1 Digital Signature Engine
- **Storage:** Encrypted signatures associated with User IDs (DG, Legal Manager, etc.).
- **Logic:** Signatures must be stamped on approval documents (e.g., filed documents, judgments, settlement agreements) at the moment of approval. The stamp must include a timestamp and user's full name. Electronic signature required for all legally binding approvals.

### 8.2 Unique Identifier Generation
- **Case Numbers:** `FCC/SUED/YYYY/NNN` and `FCC/SUING/YYYY/NNN` – sequence per year, atomic.
- **Meeting Numbers:** Prefixes defined per governing body, with either endless or financial-year sequence. Use database sequences with appropriate formatting.

### 8.3 Audit Trail
- Every state transition, data modification, conflict declaration, and approval must be logged in an `AuditTrail` table.
- Fields: `EntityID`, `EntityType`, `PreviousStatus`, `NewStatus`, `ActorID`, `IPAddress`, `ActionTimestamp`, `Comments`.

### 8.4 Notifications Engine
- Events trigger notifications (email/in-app) to relevant users based on role and assignment.
- Examples: new case registered (to DG), filing ready for review (to Legal Manager), filing approved (to Legal Officer), task reminders, appeal due date.

### 8.5 Integration Points
- **Corporate Service Microservice:** For user details, departments, org units. Must sync staff data.
- **Documents and Records Management Microservice:** Store all documents; return document IDs and links. Provide folder structure per case.
- **IAM Microservice:** Authentication and role-based access control.

### 8.6 Role-Based Access Control (RBAC)
- Permissions defined per role per entity/action. (Matrix to be detailed separately.)
- System must enforce that users can only access cases/meetings they are assigned to or have explicit permission for.

### 8.7 Quorum Calculation (Meeting)
- Must use real-time acceptance status. Quorum = (number of accepted members / total members) * 100 ≥ 51.

### 8.8 Conflict of Interest Handling
- Record conflict; exclude member from any decision/vote on that agenda. Do not affect future meeting participation.

### 8.9 Budgetary Control (Not applicable – no ERP integration)

---

## 9. Entity Relationship Context
- **User:** (From IAM/Corporate Service)
- **GoverningBody:** (Parent to Meeting, Member)
- **Meeting:** (Parent to MeetingAgenda, MeetingParticipant, Minutes, Resolution, Directive)
- **SubmissionForDetermination:** (Linked to MeetingAgenda)
- **CaseDefendant / CasePlaintiff:** (Parent to Filing, Response, Hearing, Settlement, Judgment, Financial, Task)
- **Document:** (Stored in Documents Microservice, referenced by ID in multiple entities)

---

*End of Document*
