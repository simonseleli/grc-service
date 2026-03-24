# Legal Services Module — Refined UI Design
*(Restructured to align with official Legal Services module menu structure)*

---

## SIDEBAR NAVIGATION STRUCTURE

```
⚖️  LEGAL SERVICES
│
├── Dashboard
├── Governing Bodies
│     ├── Types
│     ├── Bodies
│     └── Members
├── Meeting Repository
├── Meeting Packs
├── Resolution Register
├── Directives
├── Submission for Determination
├── Minutes Sharing
├── Public Register
├── FCC Sued
└── FCC Suing
```

> NOTE: "Court Applications" and "Legal Opinions" are NOT included — they have no SRS basis.
> Litigation directives (DG directives on cases) live inside case detail pages, not the sidebar.

---

---

## DASHBOARD
URL: /service/grc/legal/

Legal Services
Overview of all active governance, litigation, and compliance activity

---
Summary Cards Row 1:
[My Open Directives: 3]   [Upcoming Meetings: 2]   [Pending Submissions: 5]   [Open Litigation Cases: 8]

Summary Cards Row 2:
[Cases Pending DG Review: 2]   [Overdue Tasks: 1]   [Resolutions This Month: 4]   [Pending Minutes Approval: 1]

---
Quick Links:
[Register Meeting]  [New Submission]  [Report Breach]  [Register Case (Sued)]

---


---

## 1. GOVERNING BODIES

---

### 1a. Types
URL: /service/grc/legal/governing-bodies/types

Committee Types
Configure the types of committees and governing bodies in the organisation

[+ Create New]   [Search committee types...]   [All Statuses ▼]

| Committee Name    | Description                                                               | Status   | Created Date | Actions        |
|-------------------|---------------------------------------------------------------------------|----------|--------------|----------------|
| Risk and Governance | Oversees risk management and governance practices within the organisation. | Active   | 2024-01-10   | [View] [Edit]  |
| Audit             | Responsible for internal audit oversight and financial compliance.        | Active   | 2024-01-12   | [View] [Edit]  |
| Commission        | The main governing commission for competition regulation.                 | Active   | 2024-01-05   | [View] [Edit]  |
| Management        | Senior management governing committee.                                    | Active   | 2024-02-01   | [View] [Edit]  |

Showing 1-4 of 4 | Rows per page: 10

---
On clicking [View] for "Risk and Governance":

Risk and Governance
Committee Type Details

Status: [Active]   [Deactivate]   [Edit]

Description:
  Oversees risk management and governance practices within the organisation.

Created:    January 10, 2024
Last Updated: February 1, 2025

---

On clicking [+ Create New]:

Create Committee Type

Name *
  [Enter committee type name          ]

Description
  [Enter description...               ]

Status *
  [Active ▼]

[Cancel]  [Save]

---

### 1b. Bodies
URL: /service/grc/legal/governing-bodies/bodies

Governing Bodies
Manage formal governing bodies and their secretary assignments

[+ Create New]   [Search governing bodies...]   [All Statuses ▼]

| Name                                      | Type              | Description                                                   | Secretary(ies)     | Status | Created Date | Actions       |
|-------------------------------------------|-------------------|---------------------------------------------------------------|--------------------|--------|--------------|---------------|
| Risk and Governance Committee             | Risk and Governance | Oversees risk management and governance practices.          | John Mwalimu       | Active | 2024-01-10   | [View] [Edit] |
| Audit Committee                           | Audit             | Responsible for internal audit oversight.                     | Peter Ndunguru     | Active | 2024-01-15   | [View] [Edit] |
| Fair Competition Commission               | Commission        | The governing commission responsible for competition regulation. | Mary Kimaro     | Active | 2024-01-05   | [View] [Edit] |
| Senior Management Team                    | Management        | Senior management team responsible for day-to-day operations. | Sarah Mushi        | Active | 2024-02-01   | [View] [Edit] |

Showing 1-4 of 4 | Rows per page: 10

---
On clicking [View] for "Fair Competition Commission":

Fair Competition Commission
Governing Body Details

Status: [Active]   [Edit]   [Deactivate]

Type:           Commission
Composite Title: Fair Competition Commission
Description:    The governing commission responsible for competition regulation.

Secretary(ies):
  Mary Kimaro  [Remove]
  [+ Assign Secretary]

Members:        6 active members   [View Members]

Created:        January 5, 2024
Last Updated:   February 1, 2025

---

On clicking [+ Create New]:

Create Governing Body

Name *
  [Enter governing body name          ]

Committee Type *
  [Select type ▼]

Composite Title
  [e.g., Fair Competition Commission  ]

Description
  [Enter description...               ]

Secretary(ies) *
  [Select user(s) ▼]   [+ Add Another Secretary]

Status *
  [Active ▼]

[Cancel]  [Save]

---

### 1c. Members
URL: /service/grc/legal/governing-bodies/members

Members & Secretaries
Manage committee and management members across all governing bodies

[+ Add Member]   [Search members...]   [All Bodies ▼]   [All Types ▼]   [All Statuses ▼]

| Name              | Member Type        | Position  | Governing Body                | Department       | Status | Actions       |
|-------------------|--------------------|-----------|-------------------------------|------------------|--------|---------------|
| Dr. Amina Hassan  | Committee Member   | Chairman  | Risk and Governance Committee | Risk Management  | Active | [View] [Edit] |
| John Mwalimu      | Committee Member   | Secretary | Risk and Governance Committee | Legal Services   | Active | [View] [Edit] |
| Sarah Kimaro      | Management Member  | Chairman  | Senior Management Team        | Finance          | Active | [View] [Edit] |
| Peter Ndunguru    | Committee Member   | Secretary | Audit Committee               | Internal Audit   | Active | [View] [Edit] |
| Grace Mollel      | Committee Member   | Member    | Risk and Governance Committee | Operations       | Active | [View] [Edit] |
| James Haule       | Management Member  | Member    | Senior Management Team        | ICT              | Active | [View] [Edit] |

Showing 1-6 of 6 | Rows per page: 10

---
On clicking [View] for "Dr. Amina Hassan":

Dr. Amina Hassan
Committee Member Details

Status: [Active]   [Edit]   [Deactivate]

Member Type:      Committee Member
Position:         Chairman
Governing Body:   Risk and Governance Committee
Email:            amina.hassan@fcc.go.tz   (synced from Corporate Service)
Department:       Risk Management
Joined Date:      January 20, 2024
Left Date:        —

Note: This member is also assigned to: Audit Committee (Member)

Last Updated: February 1, 2025

---

On clicking [+ Add Member]:

Add Member

Select User *
  [Search and select staff member ▼]

Member Type *
  [ ] Committee Member
  [ ] Management Member

Governing Body *
  [Select governing body ▼]

Position *
  [Select: Member / Secretary / Chairman ▼]

Joined Date *
  [mm/dd/yyyy]

[Cancel]  [Save]

---


---

## 2. MEETING REPOSITORY
URL: /service/grc/legal/meetings

Meetings
Primary governance engine for meeting lifecycle management

[+ Register New Meeting]
[Search meetings...]   [All Bodies ▼]   [All Types ▼]   [All Statuses ▼]

---
Summary Cards:
[Total Meetings: 5]  [Draft: 1]  [Registered: 2]  [Invitations Sent: 1]  [Ongoing: 1]  [Completed: 2]
---

| Meeting No.      | Title                             | Governing Body                | Type            | Start Date  | Status            | Quorum     | Actions          |
|------------------|-----------------------------------|-------------------------------|-----------------|-------------|-------------------|------------|------------------|
| CM/2025-2026/001 | Commission Meeting                | Fair Competition Commission   | Commission Mtg  | 2025-03-15  | Registered        | 75% (Met)  | [View]           |
| ACM-002          | Audit Committee Meeting           | Audit Committee               | Audit Comm.Mtg  | 2025-03-10  | Ongoing           | 80% (Met)  | [View]           |
| RGC-003          | Governance Committee Meeting      | Risk and Governance Committee | Governance Mtg  | 2025-03-20  | Draft             | 0% (Not Met) | [View]         |
| SMT/2025-2026/004| Management Governance Meeting     | Senior Management Team        | Management Mtg  | 2025-03-25  | Closed            | 60% (Met)  | [View]           |
| CM/2025-2026/005 | Commission Case Meeting           | Fair Competition Commission   | Commission Mtg  | 2025-04-10  | Invitations Sent  | 40% (Not Met) | [View]        |

Showing 1-5 of 5 | Rows per page: 10

> NOTE: Quorum column shows percentage + Met/Not Met. No "Near Threshold" pseudo-status.
> Invitations are sent AUTOMATICALLY by the system when a meeting moves from Draft → Registered.
> There is NO manual "Send Invitation" button on the list page.

---

On clicking [+ Register New Meeting]:

Register New Meeting
Secretary creates a new meeting record

Meeting Title *   (predefined types — select from list)
  [Select meeting type: Commission Meeting / Audit Committee Meeting / Governance Committee Meeting / Management Meeting ... ▼]

Meeting Number
  [Auto-generated by system based on governing body prefix and numbering scheme — read-only]

Governing Body *   (only bodies where this user is Secretary)
  [Select governing body ▼]

Meeting Type *
  [Ordinary / Extraordinary / Special ▼]

Start Date & Time *
  [mm/dd/yyyy]  [HH:MM]

End Date & Time *
  [mm/dd/yyyy]  [HH:MM]

Mode *
  [Physical / Virtual / Hybrid ▼]

Location / Venue
  [Enter venue name or address         ]

Venue/Meeting Link (for Virtual/Hybrid)
  [Enter URL                           ]

Agenda Summary
  [Brief summary of meeting purpose... ]

[Cancel]  [Save as Draft]

> On save, status = DRAFT.
> On "Register" action from Draft, status → REGISTERED and system AUTOMATICALLY sends invitations
> to all active members of the selected governing body.

---

On clicking [View] for CM/2025-2026/001:
URL: /service/grc/legal/meetings/1

Commission Meeting
CM/2025-2026/001
Status: [Registered]

Governing Body:  Fair Competition Commission
Type:            Commission Meeting
Category:        Ordinary
Start:           2025-03-15  09:00
End:             2025-03-15  13:00
Mode:            Physical
Venue:           Main Boardroom

---
Quorum Status Panel:
  Accepted: 3 of 4 eligible members (75%)
  [████████████░░░░] 75%
  Status: MET ✓   (≥51% threshold)
---

[Initiate Meeting]   (enabled only when QuorumMet = true and current time is within schedule)
[Reschedule]         (available when quorum not met)
[Cancel Meeting]

---
MEETING DETAIL PAGE TABS:
[ Agenda ] [ Participants ] [ Conflicts ] [ Minutes ] [ Resolutions ] [ Directives ] [ Audit ]
---

### TAB 1: Agenda

Agenda Items
[+ Attach Agenda Item]

| # | Agenda Item                               | Submitted By          | Submission ID  | Status      | Outcome     | Directives | Actions           |
|---|-------------------------------------------|-----------------------|----------------|-------------|-------------|------------|-------------------|
| 1 | Review of Q1 Financial Performance        | Finance Director      | SUB-2025-003   | Pending     | Pending     | 0          | [View] [Remove]   |
| 2 | Merger Case ABC/2025/001 Determination    | Legal Services        | SUB-2025-007   | Pending     | Pending     | 1          | [View] [Remove]   |
| 3 | Consumer Protection Policy Update         | Consumer Affairs      | SUB-2025-010   | Pending     | Approved    | 2          | [View] [Remove]   |

---
Matters Arising (auto-populated)
Automatically carried forward from unresolved directives of the same governing body (FinallyClosed = false)

| Directive ID  | Description                                      | Assigned To     | Due Date   | Status      | Actions                    |
|---------------|--------------------------------------------------|-----------------|------------|-------------|----------------------------|
| DIR-2025-004  | Address audit findings from Q4 2024              | Dept-Finance    | 2025-04-10 | Overdue     | [View] [Finally Close]     |
| DIR-2025-006  | Review risk registers per audit observations     | Committee       | 2025-05-01 | Open        | [View] [Finally Close]     |

---

On clicking [+ Attach Agenda Item]:

Attach Agenda Item
Select an existing Submission for Determination targeted to this governing body.
(Only submissions with Status = Submitted and TargetBodyID = this meeting's GoverningBodyID are shown)

Submission *
  [Select from list of available submissions ▼]
  Shows: Title — Submitted By — Date

Order / Position
  [1 ▼]

[Cancel]  [Attach]

> On attach, the linked SubmissionForDetermination status → UNDER_REVIEW.

---

On clicking [Finally Close] in Matters Arising:
(Secretary only — final closure in Matters Arising)

Finally Close Directive
DIR-2025-004 — Address audit findings from Q4 2024

This action permanently marks the directive as Fully Closed and removes it from all future Matters Arising.

Completion Summary *
  [Describe how the directive was completed...]

Completion Date *
  [mm/dd/yyyy]

Evidence Document
  [Upload or select from DMS    ]  [No file chosen]

☑ I confirm this directive has been satisfactorily completed (Secretary)

[Cancel]  [Confirm Final Closure]

---

### TAB 2: Participants

Members (Governing Body — Auto-populated by system)
[+ Invite Additional Staff]

| Name              | Designation         | Section/Unit | Role      | Quorum Eligible | Voting Rights | Invitation Status | Attendance | Actions  |
|-------------------|---------------------|--------------|-----------|-----------------|---------------|-------------------|------------|----------|
| Dr. John Makundi  | Commissioner        | Commission   | Chairman  | Yes             | Yes           | Accepted          | —          | [View]   |
| Mary Kimaro       | Board Secretary     | Secretariat  | Secretary | Yes             | Yes           | Accepted          | —          | [View]   |
| Peter Mwanga      | Commissioner        | Commission   | Member    | Yes             | Yes           | Accepted          | —          | [View]   |
| Sarah Mushi       | Commissioner        | Commission   | Member    | Yes             | Yes           | Declined          | —          | [View]   |

> Members section is AUTO-POPULATED when meeting is created. No manual "Add Member" button.
> Quorum = 3 Accepted / 4 Eligible = 75% → Met.

---

Invitees (Additional Internal Staff)
[+ Invite Staff]

| Name          | Designation    | Section/Unit  | Role     | Invitation Status | Actions  |
|---------------|----------------|---------------|----------|-------------------|----------|
| James Nyamizi | Legal Counsel  | Legal Services | Observer | Accepted          | [Remove] |

> Invitees receive read-only access to agenda and directives. They cannot vote.

---

On clicking [+ Invite Staff]:

Invite Staff Member
Invite an internal staff member as an observer/invitee to this meeting.

Staff Member *
  [Search and select staff ▼]

Role
  [Observer ▼]

[Cancel]  [Send Invitation]

> Invitation is sent immediately by the system upon saving.

---

During ONGOING meeting — Attendance marking:
Secretary can mark actual attendance by toggling the Attendance column.
[☑ Mark Present] button appears per participant row when meeting is ONGOING.

---

### TAB 3: Conflicts

Conflict of Interest Declarations
[+ Declare Conflict]

| Declared By   | Agenda Item                              | Type                 | Severity | Recusal Required | Status | Actions    |
|---------------|------------------------------------------|----------------------|----------|------------------|--------|------------|
| Peter Mwanga  | Merger Case ABC/2025/001 Determination   | Direct Financial     | Material | Yes              | Active | [Withdraw] |

> Members with Active conflict on an agenda item are excluded from votes/determinations on that item.
> Conflict does NOT affect participation in other agenda items or future meetings.

---

On clicking [+ Declare Conflict]:

Declare Conflict of Interest
Declarations are item-level and may trigger mandatory recusal.

Declaring Member *
  [Select member ▼]   (auto-filled if current user is a member)

Agenda Item *
  [Select from this meeting's agenda items ▼]

Type of Conflict *
  [Select: Direct Financial / Indirect Financial / Personal / Other ▼]

Severity *
  [Select: Material / Minor ▼]

Description *
  [Describe the nature of the conflict...]

Recusal Required
  [Toggle: Yes / No]

[Cancel]  [Submit Declaration]

> On submit, the system records conflict and excludes the member from that agenda item's determination.

---

### TAB 4: Minutes

Meeting Minutes
[+ Draft Minutes]   (available after meeting is ONGOING or CLOSED)

| Title                              | Created By    | Created Date | Attachments | Status           | Approved By         | Approval Date | Actions                      |
|------------------------------------|---------------|--------------|-------------|------------------|---------------------|---------------|------------------------------|
| CM/2025-2026/001 Minutes           | Mary Kimaro   | 2025-03-15   | 2 files     | Pending Approval | —                   | —             | [View] [Submit for Approval] |

> Status values: Draft / Pending Approval / Approved.
> "Shared" is NOT a valid status.

---

On clicking [+ Draft Minutes]:

Draft Meeting Minutes

Select Meeting *
  [CM/2025-2026/001 — Commission Meeting ▼]   (pre-filled from context)

Title *
  [e.g., CM/2025-2026/001 Minutes            ]

Minutes Content *
  [Rich text editor — enter proceedings, decisions, action items...]

Attachments
  [Upload files   ]  [No files chosen]  (multiple files allowed)

[Cancel]  [Save as Draft]

---

On clicking [Submit for Approval]:

Submit Minutes for Approval
Minutes will be sent to all participating members for sign-off.

Approval Method *
  [Majority Vote / Explicit Sign-off by all members ▼]   (configurable)

Note: Approval notifications will be sent automatically to all participating members.

[Cancel]  [Submit for Approval]

> Status → PENDING_APPROVAL.
> Members receive notification and can Approve or Request Changes.
> When approval threshold is met → status → APPROVED. Minutes become final (read-only).

---

### TAB 5: Resolutions

Resolutions
Automatically captured from agenda item outcomes. Visible only to meeting invitees.
[Export]   [Search resolutions...]

| Resolution ID  | Agenda Item                              | Resolution Text                                                                        | Responsible Person         | Date Adopted | Effective Date | Status   | Actions |
|----------------|------------------------------------------|----------------------------------------------------------------------------------------|----------------------------|--------------|----------------|----------|---------|
| RES-2025-001   | Consumer Protection Policy Update        | The Commission approves the updated Consumer Protection Policy effective immediately.  | Director of Consumer Affairs | 2025-03-15  | 2025-03-15     | Approved | [View]  |
| RES-2025-002   | Merger Case ABC/2025/001 Determination   | The Commission approves the merger subject to conditions listed in the determination.  | Director of Legal Services   | 2025-03-15  | 2025-04-01     | Approved | [View]  |

> Resolutions are AUTO-CREATED from agenda item outcomes after determination.
> No manual "Create Resolution" button — they are system-generated.
> Visible ONLY to invited participants (members and invitees of this meeting).

---

On clicking [View] for RES-2025-001:

RES-2025-001
Resolution Details

Status: [Approved]

Meeting Reference:    CM/2025-2026/001
Agenda Item:          Consumer Protection Policy Update
Resolution Text:      The Commission approves the updated Consumer Protection Policy effective immediately.
Responsible Person:   Director of Consumer Affairs
Effective Date:       2025-03-15
Date Adopted:         2025-03-15

Attachments: [None]

---

### TAB 6: Directives

Meeting Directives
Directives issued during this meeting. Sourced from agenda items and Matters Arising.
[+ Add Directive]   (available during ONGOING meeting only, Secretary role)

| Directive ID  | Agenda Item / Source                       | Description                                          | Category    | Priority | Assigned To                  | Due Date   | Status      | FinallyClosed | Actions              |
|---------------|--------------------------------------------|------------------------------------------------------|-------------|----------|------------------------------|------------|-------------|---------------|----------------------|
| DIR-2025-001  | Consumer Protection Policy Update          | Disseminate updated policy to all directorates.      | Compliance  | Critical | Executive Office             | 2025-03-30 | In Progress | No            | [View] [Close]       |
| DIR-2025-002  | Merger Case ABC/2025/001 Determination     | Prepare detailed merger analysis report.             | Legal       | High     | Legal Services (Dept)        | 2025-04-15 | Open        | No            | [View] [Close]       |
| DIR-2025-003  | Matters Arising                            | Conduct staff training on consumer protection.       | Operational | Medium   | Mary Kimaro (Individual)     | 2025-04-30 | Open        | No            | [View] [Close]       |

> [Close] action is available ONLY to the assigned user (initial closure).
> Final Closure is done by Secretary in the Matters Arising tab of a LATER meeting.

---

On clicking [+ Add Directive] (during ONGOING meeting, Secretary only):

Add Directive
Issue a directive from this meeting

Agenda Item / Source *
  [Select: Agenda Item or Matters Arising ▼]

Description *
  [Describe the directive clearly...]

Category *
  [Select: Legal / Compliance / Operational / Financial / Governance / Administrative / Risk ▼]

Priority *
  [Critical / High / Medium / Low ▼]

Assign To — Type *
  [Department / Org Unit / Individual ▼]

Assigned To *
  [Select department or search for individual ▼]

Due Date *
  [mm/dd/yyyy]

[Cancel]  [Save Directive]

---

On clicking [Close] (assigned user only — initial closure):

Close Directive
DIR-2025-002 — Prepare detailed merger analysis report

Completion Summary *
  [Describe how the directive was completed...]

Completion Date *
  [mm/dd/yyyy]

Evidence Document
  [Upload or select from DMS   ]  [No file chosen]

☑ I confirm this directive has been completed (Assigned User only)

[Cancel]  [Submit Closure]

> Status → CLOSED.
> Final closure (FULLY_CLOSED) is done by the Secretary in Matters Arising of a subsequent meeting.

---

### TAB 7: Audit

Audit Log
All state changes, agenda links, participant responses, conflict declarations, directive actions, and minutes approvals are automatically logged.

| Action                  | User          | Timestamp           | Details                                                    |
|-------------------------|---------------|---------------------|------------------------------------------------------------|
| Meeting Created         | Admin         | 2025-02-01 09:00    | Meeting CM/2025-2026/001 created as Draft.                 |
| Status Changed          | Admin         | 2025-02-10 10:30    | Status changed from Draft to Registered.                   |
| Invitations Sent        | System        | 2025-02-10 10:30    | Invitations automatically sent to 4 members.               |
| Invitation Responded    | Peter Mwanga  | 2025-02-12 08:15    | Peter Mwanga accepted the invitation. (Quorum: 50%)        |
| Invitation Responded    | Sarah Mushi   | 2025-02-12 09:00    | Sarah Mushi declined the invitation.                       |
| Invitation Responded    | Dr. John Makundi | 2025-02-13 10:00 | Dr. John Makundi accepted. (Quorum: 75% — Met)             |
| Agenda Item Attached    | Mary Kimaro   | 2025-02-20 11:00    | SUB-2025-007 attached to agenda (position 2).              |
| Conflict Declared       | Peter Mwanga  | 2025-03-14 08:00    | Conflict declared on Merger Case agenda item.              |
| Meeting Initiated       | Mary Kimaro   | 2025-03-15 09:02    | Meeting status changed from Registered to Ongoing.         |

---


---


---

## 3. MEETING PACKS
URL: /service/grc/legal/circulars

Meeting Packs
Accessible only to invited participants (Accepted status)

[Search meeting packs...]

| Meeting Reference | Title                              | Governing Body              | Date Added | Date       | Pack Status | Actions     |
|-------------------|------------------------------------|-----------------------------|------------|------------|-------------|-------------|
| MP/2025/001       | Q1 Commission Review Meeting Pack  | Commission                  | 2025-02-01 | 2025-02-05 | Active      | [View Pack] |
| MP/2025/002       | Management Policy Review           | Management                  | 2025-02-03 | 2025-02-06 | Draft       | [View Pack] |
| MP/2025/003       | Audit Committee Budget Review      | Audit Committee             | 2025-02-04 | 2025-02-04 | Draft       | [View Pack] |

> Visible ONLY to staff members who have been invited to the meeting AND have Accepted status.
> Each Meeting Pack entry corresponds to a meeting in the Meeting Repository.
> Pack Status reflects the meeting's current state (Draft / Active / Closed).

---

On clicking [View Pack] for MP/2025/001:
URL: /service/grc/legal/circulars/1

Q1 Commission Review Meeting Pack
MP/2025/001

Status: [Active]

---
Pack Items (2)

| Item # | Agenda Item                     | Document Title                     | Category    | Version | Upload Date | Conflict Status | Actions      |
|--------|---------------------------------|------------------------------------|-------------|---------|-------------|-----------------|------------------|
| 1      | Merger Case Determination       | Merger Case ABC/2025/001           | Legal Memo  | 1.2     | 2025-02-01  | Declared        | [View More]  |
| 2      | Policy Update                   | Consumer Protection Policy Update  | Board Paper | 2.0     | 2025-02-02  | None            | [View More]  |

> Conflict Status = Declared indicates the current user, or a member of this meeting,
> has declared a conflict of interest on that agenda item (per SRS §1.2.1 BR#7).

---

On clicking [View More] for a Pack Item:

Pack Item Detail
Item #1 — Merger Case Determination

Agenda Item:     Merger Case Determination
Document Title:  Merger Case ABC/2025/001
Category:        Legal Memo
Version:         1.2
Upload Date:     2025-02-01
Conflict Status: Declared

[Preview Document]   [Download Document]

> Preview opens document in browser viewer (Documents & Records Management integration).
> Download fetches the file directly.
> Both actions are read-only for participants. No editing allowed.

---


---

## 4. RESOLUTION REGISTER
URL: /service/grc/legal/resolution-register

Resolution Register
Central archive of all governance resolutions — searchable by invited participants only

[Export]   [Search resolutions...]   [All Bodies ▼]   [All Statuses ▼]

| Resolution ID  | Meeting No.      | Governing Body              | Agenda Item                          | Resolution Text (summary)                                                        | Responsible Person          | Date Adopted | Effective Date | Status   | Actions |
|----------------|------------------|-----------------------------|--------------------------------------|----------------------------------------------------------------------------------|-----------------------------|--------------|----------------|----------|---------|
| RES-2025-001   | CM/2025-2026/001 | Fair Competition Commission | Consumer Protection Policy Update    | The Commission approves the updated Consumer Protection Policy...                | Director of Consumer Affairs | 2025-03-15  | 2025-03-15     | Approved | [View]  |
| RES-2025-002   | ACM-002          | Audit Committee             | Internal Audit Findings Q4 2024      | The Committee notes audit findings and requests management to address gaps...    | Head of Internal Audit       | 2025-03-10  | 2025-03-10     | Noted    | [View]  |
| RES-2025-003   | SMT/2025-2026/004| Senior Management Team      | Staff Training Policy                | Management adopts the revised Staff Training Policy for FY 2025/26.             | Director of HR               | 2025-03-25  | 2025-04-01     | Approved | [View]  |

Showing 1-3 of 3 | Rows per page: 10

> This register is READ-ONLY. Resolutions are system-generated from meeting agenda outcomes.
> Visible ONLY to invited participants of the respective meeting.

---

On clicking [View] for RES-2025-001:
URL: /service/grc/legal/resolution-register/1

RES-2025-001
Resolution Details

Status: [Approved]

Meeting Reference:    CM/2025-2026/001
Governing Body:       Fair Competition Commission
Agenda Item:          Consumer Protection Policy Update
Resolution Text:
  The Commission approves the updated Consumer Protection Policy effective immediately.
Responsible Person:   Director of Consumer Affairs
Effective Date:       2025-03-15
Date Adopted:         2025-03-15
Attachments:          [None]

---


---

## 5. DIRECTIVES
URL: /service/grc/legal/meeting-directives

Meeting Directives
Track and manage all governance directives issued from meetings

[Search directives...]   [All Statuses ▼]   [All Bodies ▼]   [All Categories ▼]

| Directive ID  | Meeting No.      | Agenda Item / Source                 | Description                                          | Category    | Priority | Assigned To             | Due Date   | Status      | Finally Closed | Actions              |
|---------------|------------------|--------------------------------------|------------------------------------------------------|-------------|----------|-------------------------|------------|-------------|----------------|----------------------|
| DIR-2025-001  | CM/2025-2026/001 | Consumer Protection Policy Update    | Disseminate updated policy to all directorates.      | Compliance  | Critical | Executive Office        | 2025-03-30 | In Progress | No             | [View]               |
| DIR-2025-002  | CM/2025-2026/001 | Merger Case ABC/2025/001 Det.        | Prepare detailed merger analysis report.             | Legal       | High     | Legal Services (Dept)   | 2025-04-15 | Open        | No             | [View]               |
| DIR-2025-003  | CM/2025-2026/001 | Matters Arising                      | Conduct staff training on consumer protection.       | Operational | Medium   | Mary Kimaro             | 2025-04-30 | Open        | No             | [View]               |
| DIR-2025-004  | ACM-002          | Internal Audit Findings Q4 2024      | Address all audit findings and submit evidence.      | Financial   | High     | Finance Dept            | 2025-04-10 | Overdue     | No             | [View]               |
| DIR-2025-005  | ACM-002          | Internal Audit Findings Q4 2024      | Update internal control procedures per audit.        | Governance  | Medium   | Secretariat             | 2025-04-20 | Open        | No             | [View]               |
| DIR-2025-006  | ACM-002          | Audit Observations                   | Review risk registers per audit observations.        | Risk        | Low      | Risk Committee          | 2025-05-01 | Open        | No             | [View]               |
| DIR-2025-007  | SMT/2025-2026/004| Staff Training Policy                | Develop annual training calendar per new policy.     | Admin       | Medium   | Dr. John Makundi        | 2025-04-15 | Closed      | No             | [View]               |

Showing 1-7 of 7 | Rows per page: 10

> IMPORTANT: On this list, there is NO "Close" button.
> Initial closure is done by the ASSIGNED USER from within the directive detail page.
> Final closure is done by the SECRETARY in the meeting's Matters Arising tab.

---

On clicking [View] for DIR-2025-001:
URL: /service/grc/legal/meeting-directives/1

DIR-2025-001
Directive Details

Status: [In Progress]

Meeting Reference:    CM/2025-2026/001
Governing Body:       Fair Competition Commission
Agenda Item:          Consumer Protection Policy Update
Description:          Disseminate updated Consumer Protection Policy to all directorates.
Category:             Compliance
Priority:             Critical
Assigned To:          Executive Office (Department)
Due Date:             2025-03-30
Completion Summary:   —
Completion Date:      —
Evidence Document:    —
Finally Closed:       No
Finally Closed At:    —

---

Actions visible based on role:
  [Close Directive]     → Visible ONLY to the ASSIGNED USER when Status = Open or In Progress
  [Finally Close]       → Visible ONLY to the SECRETARY in Matters Arising of a later meeting

---

[Close Directive] form (Assigned User only):

Close Directive
DIR-2025-001 — Disseminate updated Consumer Protection Policy to all directorates.

Completion Summary *
  [Describe how the directive was completed...]

Completion Date *
  [mm/dd/yyyy]

Evidence Document
  [Upload or select from DMS    ]  [No file chosen]

☑ I confirm this directive has been completed (Assigned User only)

[Cancel]  [Confirm Closure]

> On confirm: Status → CLOSED.
> Directive remains in Matters Arising of future meetings until Secretary performs Final Closure.

---


---

## 6. SUBMISSION FOR DETERMINATION
URL: /service/grc/legal/submissions

Submission for Determination
Submissions requiring formal decision by a governing body

[+ Create New]   [Search submissions...]   [All Statuses ▼]   [All Bodies ▼]

| Submission ID  | Title                                  | Description (snippet)                     | Submitted By              | Governing Body         | Submission Date | Status       | Meeting Linked       | Actions             |
|----------------|----------------------------------------|-------------------------------------------|---------------------------|------------------------|-----------------|--------------|----------------------|---------------------|
| SUB-2025-001   | Risk Assessment Framework Review       | Updated risk assessment framework...      | Risk Management Unit      | Risk and Governance    | 2025-02-01      | Under Review | CM/2025-2026/001     | [View] [Withdraw]   |
| SUB-2025-002   | Internal Audit Findings Q4             | Findings from Q4 internal audit cycle...  | Internal Audit            | Audit Committee        | 2025-02-05      | Submitted    | —                    | [View] [Edit] [Withdraw] |
| SUB-2025-003   | Governance Policy Update               | Proposed update to governance policy...   | Legal Services            | Risk and Governance    | 2025-01-20      | Determined   | SMT/2025-2026/004    | [View]              |

> [Edit] and [Withdraw] are available ONLY when Status = Submitted (not yet linked to a meeting agenda).
> Once linked to a meeting (Status = Under Review), editing/withdrawing is disabled.

Showing 1-3 of 3 | Rows per page: 10

---

On clicking [View] for SUB-2025-001:
URL: /service/grc/legal/submissions/1

Risk Assessment Framework Review
SUB-2025-001
Submission Details

Status: [Under Review]    (linked to CM/2025-2026/001)

Title:              Risk Assessment Framework Review
Description:        Updated risk assessment framework requiring committee determination for FY 2025/26.
Submitted By:       Risk Management Unit
Governing Body:     Risk and Governance Committee
Submission Date:    February 1, 2025

Supporting Documents:
  - Enterprise Risk Framework 2025.pdf   [View]

Linked Meeting:     CM/2025-2026/001 — Commission Meeting
Determination Date: —
Outcome:            Pending
Outcome Notes:      —
Directives Created: —

Last Updated: February 5, 2025

---

On clicking [+ Create New]:

Submission for Determination
Submit a document for formal determination by a governing body.

Title *
  [Enter submission title                                   ]

Description *
  [Describe the submission and what determination is sought...]

Governing Body *    (select the body this submission targets)
  [Select governing body ▼]

Supporting Documents
  [Upload files   ]  [No files chosen]  (multiple allowed)

Additional Details / Context
  [Provide any additional context...                        ]

[Cancel]  [Submit for Determination]

> On submit: Status = SUBMITTED.
> Submission becomes available for Secretary to select when building a meeting agenda for the chosen governing body.

---


---

## 7. MINUTES SHARING
URL: /service/grc/legal/minutes

Minutes
Meeting minutes drafting, submission for approval, and final record

[+ Draft Minutes]   [Search minutes...]   [All Statuses ▼]   [All Bodies ▼]

| Minutes ID    | Title                                        | Meeting No.      | Created By    | Created Date | Attachments | Status           | Approved By                    | Approval Date | Actions                        |
|---------------|----------------------------------------------|------------------|---------------|--------------|-------------|------------------|--------------------------------|---------------|--------------------------------|
| MIN-2025-001  | CM/2025-2026/001 Minutes                     | CM/2025-2026/001 | Mary Kimaro   | 2025-03-15   | 2 files     | Pending Approval | —                              | —             | [View] [Submit for Approval]   |
| MIN-2025-002  | ACM-002 Minutes                              | ACM-002          | John Mwalimu  | 2025-03-10   | 1 file      | Approved         | Dr. John Makundi, Mary Kimaro  | 2025-03-17    | [View]                         |
| MIN-2025-003  | SMT/2025-2026/004 Minutes                    | SMT/2025-2026/004| Sarah Mushi   | 2025-02-28   | 0 files     | Draft            | —                              | —             | [View] [Edit] [Submit]         |

> Valid statuses: Draft | Pending Approval | Approved.
> "Shared" is NOT a valid status in this system.

Showing 1-3 of 3 | Rows per page: 10

---

On clicking [View] for MIN-2025-002 (Approved):
URL: /service/grc/legal/minutes/2

ACM-002 Minutes
MIN-2025-002

Status: [Approved]

Meeting:      ACM-002 — Audit Committee Meeting
Created By:   John Mwalimu
Meeting Date: March 10, 2025

Minutes Content:
  The meeting was called to order at 09:00 AM.

  1. Review of Q4 2024 Internal Audit Findings
     The Committee reviewed the Q4 2024 internal audit findings presented by the Head of Internal Audit.
     Resolution: The Committee notes the findings and directs management to address all gaps within 30 days.

  2. Internal Control Procedures Review  
     The Committee reviewed the updated internal control framework.
     Resolution: Approved with minor amendments. Effective immediately.

  The meeting was adjourned at 12:30 PM.

Attachments:
  - ACM-002-Agenda.pdf      [View / Download]
  - ACM-002-Supporting.pdf  [View / Download]

Approved By:   Dr. John Makundi, Mary Kimaro
Approval Date: March 17, 2025

Created: March 10, 2025 | Last Updated: March 17, 2025

---

On clicking [+ Draft Minutes]:

Draft Meeting Minutes

Select Meeting *   (only ONGOING or CLOSED meetings can have minutes drafted)
  [Select meeting ▼]

Title *
  [e.g., CM/2025-2026/001 Minutes   ]

Minutes Content *
  [Rich text editor — enter full proceedings, discussions, decisions...]

Attachments
  [Upload files   ]  [No files chosen]  (multiple files allowed — PDF, DOC, DOCX)

[Cancel]  [Save as Draft]

> Status → DRAFT. Only the Secretary can draft minutes.

---

On clicking [Submit for Approval]:

Submit Minutes for Approval
Minutes will be distributed to all participating members for approval.

Approval Method *
  [Majority Vote ▼ / Explicit Sign-off by all participants]

Members to approve:   (auto-populated from meeting participants who attended)
  ☑ Dr. John Makundi
  ☑ Mary Kimaro
  ☑ Peter Mwanga
  ☐ Sarah Mushi   (Declined invitation — excluded)

[Cancel]  [Submit for Approval]

> Status → PENDING_APPROVAL.
> System sends approval notifications to selected members.
> On reaching approval threshold → Status → APPROVED. Minutes become read-only.

---


---

## 8. PUBLIC REGISTER
URL: /service/grc/legal/public-register

Public Register
Official record of published commission decisions

[+ Add Decision]   (Secretariat only)
[Search decisions...]   [All Statuses ▼]

| Decision ID   | Title                                          | Decision Date | Published Date | Status    | Created By    | Actions             |
|---------------|------------------------------------------------|---------------|----------------|-----------|---------------|---------------------|
| PD-2025-001   | Merger Approval — XYZ Corporation              | 2025-03-15    | 2025-03-16     | Published | Mary Kimaro   | [View]              |
| PD-2025-002   | Consumer Protection Order — Unfair Pricing     | 2025-02-20    | 2025-02-21     | Published | Mary Kimaro   | [View]              |
| PD-2025-003   | Competition Investigation Closure              | 2025-01-25    | —              | Draft     | Mary Kimaro   | [View] [Publish]    |

> [Publish] action is available ONLY to Secretariat users.
> Published decisions become visible via public portal (future CRM integration).

Showing 1-3 of 3 | Rows per page: 10

---

On clicking [View] for PD-2025-001:
URL: /service/grc/legal/public-register/1

Merger Approval — XYZ Corporation
PD-2025-001

Status: [Published]   Published: March 16, 2025

Meeting:            CM/2025-2026/001 — Commission Meeting
Decision Date:      March 15, 2025

Background / Body:
  The Commission considered the merger application submitted by XYZ Corporation for the acquisition
  of ABC Ltd. After thorough review of market analysis, competition implications, and stakeholder
  submissions, the Commission deliberated on the matter.

Decision Text:
  The Commission hereby approves the merger between XYZ Corporation and ABC Ltd, subject to the
  following conditions:
    1. Divestiture of overlapping business units within 12 months.
    2. Maintenance of employment levels for 24 months.
    3. Quarterly compliance reports to FCC.

Created: March 15, 2025 | Last Updated: March 16, 2025

---

On clicking [+ Add Decision]:

Add Public Decision

Select Commission Meeting *
  [Select meeting ▼]

Title *
  [Decision title                               ]

Background / Body *
  [Background information and context...        ]

Decision Text *
  [The formal decision, orders, or conditions..  ]

Decision Date *
  [mm/dd/yyyy]

[Cancel]  [Save as Draft]
(Status = DRAFT on save. Secretariat uses [Publish] from the list to publish.)

---


---

## 9. FCC SUED
URL: /service/grc/legal/fcc-sued

FCC Sued — Case Repository
Manage cases where FCC has been sued

[+ Register New Case]
[Search cases...]   [All Statuses ▼]   [All Courts ▼]   [All Risks ▼]

---
Dashboard KPIs (as per SRS §4.0):
[Total Cases Filed: 5]  [Active Cases: 4]  [Cases on Appeal: 1]  [Pending DG Review: 2]  [High Risk Cases: 2]  [Won/Loss Ratio: 1/1]
---

| Case Ref No          | Plaintiff / Applicant           | Court               | Case Type     | Claim Amount | Stage            | Status  | Risk Level | Next Hearing | Actions |
|----------------------|---------------------------------|---------------------|---------------|--------------|------------------|---------|------------|--------------|---------|
| FCC/SUED/2025/001    | ABC Company Ltd                 | High Court          | Civil         | TZS 150M     | Hearing Stage    | Active  | High       | 2025-03-20   | [View]  |
| FCC/SUED/2025/002    | XYZ Trading Co, Jane Mushi      | District Court      | Civil         | TZS 50M      | Under DG Review  | Active  | Medium     | —            | [View]  |
| FCC/SUED/2025/003    | Trade Union Federation          | Court of Appeal     | Labour        | TZS 300M     | Appeal Filed     | Active  | High       | 2025-04-10   | [View]  |
| FCC/SUED/2024/015    | Mega Corp Ltd                   | High Court          | Civil         | TZS 80M      | Closed           | Closed  | Low        | —            | [View]  |
| FCC/SUED/2025/004    | Small Business Association      | Tribunal            | Administrative| TZS 25M      | New              | Active  | Medium     | 2025-03-25   | [View]  |

Showing 1-5 of 5 | Rows per page: 10

---

On clicking [+ Register New Case]:
(Actor: Registry Officer, Legal Officer, or Legal Manager — as per SRS §4.1 BR#1)

Register New Case — FCC Sued

Court Information
Court Name / Registry *
  [e.g., High Court Commercial Division, Dar es Salaam   ]

Court Level *
  [Select: Tribunal / District Court / High Court / Court of Appeal / Supreme Court ▼]

Court Case Number *
  [e.g., HC/COM/2025/123   ]

Service Date *
  [mm/dd/yyyy]

Plaintiff Information
Plaintiff / Applicant Name *   [Plaintiff 1              ]   [+ Add Another Plaintiff]

Plaintiff Advocate (Optional)
  [Enter advocate name      ]

Co-Defendants / Collaborators (Optional)
  [Collaborator 1           ]   [+ Add Another]

Case Details
Claim Amount (TZS)
  [Optional                 ]

Nature of Claim *
  [Select: Contract Breach / Administrative / Labour / Competition / Other ▼]

Department Affected *
  [Select department ▼]

Documents Served (Optional)
  [Upload files   ]  [No files chosen]

Risk & Urgency
Urgency Level *
  [Select: Urgent / High / Medium / Low ▼]

Risk Level
  [Select: High / Medium / Low ▼]

[Cancel]  [Save Draft]  [Submit to DG]

> On Submit to DG: Stage → Under DG Review. DG is notified automatically.
> System auto-generates Case Ref: FCC/SUED/YYYY/NNN.

---

On clicking [View] for FCC/SUED/2025/001:
URL: /service/grc/legal/fcc-sued/1

ABC Company Ltd vs FCC
FCC/SUED/2025/001
Stage: [Hearing Stage]   Risk: [High Risk]

[Edit Basic Info]  [Assign Legal Officers]  [Initiate Closure]

Court:              High Court Commercial Division, Dar es Salaam
Court Level:        High Court
Case Number:        HC/COM/2025/123
Service Date:       2025-01-15
Plaintiff(s):       ABC Company Ltd
Plaintiff Advocate: Adv. John Kambi
Claim Amount:       TZS 150,000,000
Nature of Claim:    Contract Breach
Department:         Procurement
Next Hearing:       2025-03-20

Assigned Legal Officer(s): Maria Sanga
Assigned Legal Manager:    Peter Mwanga

DG Review Status:   [Directive Issued]
DG Directive:       "File defence immediately" — 2025-01-16

Case Folder:        [Open in Document Repository ↗]

---
CASE DETAIL TABS:
[ Filings ] [ Responses ] [ Hearings ] [ Settlement ] [ Financials ] [ Tasks ] [ Judgment ] [ Report ] [ Activity Log ]
---

### 9.TAB1: Filings (Court Filings)

Case Filings
[+ Upload New Filing]

Filing workflow: DRAFT → UNDER REVIEW (LM) → APPROVED BY LM → UNDER REVIEW (DG) → APPROVED → FILED

| Filing ID    | Type                   | Title                                | Version | Submitted By  | Status                  | Approval Chain                     | Actions                    |
|--------------|------------------------|--------------------------------------|---------|---------------|-------------------------|------------------------------------|----------------------------|
| FIL-2025-001 | Statement of Defence   | Written Statement of Defence v1      | v1      | Maria Sanga   | Filed                   | LM ✓ → DG ✓ → Filed               | [View] [Download]          |
| FIL-2025-002 | Affidavit              | Supporting Affidavit                 | v1      | Maria Sanga   | Approved                | LM ✓ → DG ✓                       | [View] [Mark as Filed]     |
| FIL-2025-003 | Application            | Application for Extension of Time    | v1      | Maria Sanga   | Under Review (LM)       | → Legal Manager reviewing         | [View]                     |

---

On clicking [+ Upload New Filing]:

Upload New Filing

Filing Type *
  [Select: Statement of Defence / Affidavit / Application / Chamber Summons / Bill of Cost / Notice of Appeal / Other ▼]

Title *
  [Enter filing title            ]

Upload Document *
  [Upload file   ]  [No file chosen]  (PDF, DOC, DOCX — max 10MB)

Description
  [Brief description of this filing   ]

[Cancel]  [Save Draft]  [Submit for Approval]

> Save Draft → Status = DRAFT.
> Submit for Approval → Status = UNDER_REVIEW_LM. Legal Manager notified.
> On LM approval → Status = APPROVED_LM. DG notified.
> On DG approval → Status = APPROVED. Legal Officer notified — can now mark as Filed.
> On Mark as Filed → Status = FILED with actual filing date recorded.

---

### 9.TAB2: Responses (Plaintiff Responses)

Plaintiff Responses
[+ Register Response]

| Response ID   | Type                       | Received Date | Document     | Description                      | Actions       |
|---------------|----------------------------|---------------|--------------|----------------------------------|---------------|
| RES-DEF-001   | Preliminary Objections     | 2025-02-10    | [View]       | Plaintiff's preliminary objec.   | [View]        |
| RES-DEF-002   | Response to Ruling         | 2025-03-01    | [View]       | Plaintiff's response to order.   | [View]        |

---

On clicking [+ Register Response]:

Register Plaintiff Response

Response Type *
  [Select: Preliminary Objections / Response to Ruling / Counter Claim / Response to Orders / Response to Affidavits / Initial Response / Other ▼]

Received Date *
  [mm/dd/yyyy]

Upload Document *
  [Upload file   ]  [No file chosen]

Description
  [Brief description                  ]

[Cancel]  [Save]

---

### 9.TAB3: Hearings

Hearings
[+ Add Hearing]

| Hearing ID    | Court                               | Hearing Type | Date       | Judge           | Outcome    | Representative | Actions                     |
|---------------|-------------------------------------|--------------|------------|-----------------|------------|----------------|-----------------------------|
| HRG-2025-001  | High Court Dar es Salaam            | Mention      | 2025-02-05 | Hon. J. Mwamba  | Adjourned  | Maria Sanga    | [View] [+ Add Report]       |
| HRG-2025-002  | High Court Dar es Salaam            | Full Hearing | 2025-03-20 | Hon. J. Mwamba  | —          | Maria Sanga    | [View] [+ Add Report]       |

> Next Hearing Date on the case header is auto-updated from the most recent HearingReport.NextHearingDate.

---

On clicking [+ Add Hearing]:

Add Hearing

Hearing Type *
  [Select: Mention / Full Hearing / Ruling / Order / Other ▼]

Court Name
  [High Court Dar es Salaam        ]   (pre-filled from case, editable)

Date of Hearing *
  [mm/dd/yyyy]

Judge
  [Enter judge name                ]

Notes
  [Any preliminary notes           ]

[Cancel]  [Save]

---

On clicking [+ Add Report] for a hearing:

Add Hearing Report
HRG-2025-001 — High Court, Mention, 2025-02-05

Report Type *
  [Select: Proceedings / Ruling / Order ▼]

Summary of Proceedings *
  [Describe what happened at the hearing...]

Orders Made
  [Court orders, if any            ]

Remarks
  [Any additional remarks          ]

Next Hearing Date
  [mm/dd/yyyy]   (updates case NextHearingDate if this is the most recent report)

Upload Document (Optional)
  [Upload file   ]  [No file chosen]

[Cancel]  [Save]

---

### 9.TAB4: Settlement

Settlement
[+ Register Settlement]

No settlement recorded.

---

On clicking [+ Register Settlement]:

Register Settlement

Settlement Amount (TZS) *
  [Enter amount                     ]

Terms *
  [e.g., Lump sum payment within 30 days, etc...  ]

Settlement Date *
  [mm/dd/yyyy]

Upload Settlement Agreement *
  [Upload file   ]  [No file chosen]

[Cancel]  [Submit to DG]

> Requires DG approval (via Legal Manager review).
> If payment amount is specified, it will automatically appear in the Financials tab.
> Status workflow: Proposed → (LM Review) → Submitted to DG → Agreed | Rejected.

---

### 9.TAB5: Financials

Financials
Manual tracking — no ERP integration

Cards:
  [Claim Amount: TZS 150,000,000]   [Legal Costs Incurred: TZS 5,000,000]   [Costs Awarded: —]   [Other Costs: TZS 2,000,000]

> Record Payment button: visible when judgment outcome = Lost
> Record Recovery button: visible when judgment outcome = Won

[Record Payment]  [Record Recovery]  [Export Summary]

Payment & Recovery History
| Date       | Type     | Category              | Amount         | Reference   | Status    | Description                      |
|------------|----------|-----------------------|----------------|-------------|-----------|----------------------------------|
| 2025-01-20 | Payment  | Legal Consultancy     | TZS 2,000,000  | REF-001     | Processed | Legal consultancy fees           |

---

On clicking [Record Payment]:

Record Payment

Date *             [mm/dd/yyyy]
Type:              Payment   (fixed)
Category *         [Select: Legal Fees / Court Fees / Damages / Other ▼]
Amount (TZS) *     [Enter amount   ]
Reference          [Enter reference number   ]
Description        [Brief description         ]

[Cancel]  [Save]

---

On clicking [Record Recovery]:

Record Recovery

Date *             [mm/dd/yyyy]
Type:              Recovery   (fixed)
Category *         [Select: Costs Awarded / Damages Recovered / Other ▼]
Amount (TZS) *     [Enter amount   ]
Reference          [Enter reference number   ]
Description        [Brief description         ]

[Cancel]  [Save]

---

### 9.TAB6: Tasks

Tasks & Deadlines
(System auto-creates tasks for appeal deadlines, filing approvals, overdue responses, etc.)

| Task ID      | Title                                           | Related To          | Assigned To  | Due Date   | Priority | Status      | Actions  |
|--------------|-------------------------------------------------|---------------------|--------------|------------|----------|-------------|----------|
| TSK-2025-001 | Submit Statement of Defence                     | FIL-2025-001        | Maria Sanga  | 2025-01-30 | High     | Closed      | [View]   |
| TSK-2025-002 | Respond to Preliminary Objection                | HRG-2025-001        | Maria Sanga  | 2025-03-15 | High     | In Progress | [View]   |
| TSK-2025-003 | File Notice of Appeal (if appeal decision made) | JUD-2025-001        | Maria Sanga  | 2025-04-30 | Critical | Open        | [View]   |

> Reminders are sent automatically at 7, 2, and 1 day before due date.
> If due date passes without closure, status → OVERDUE and notification is sent.

---

### 9.TAB7: Judgment

Judgment
[+ Record Judgment]

No judgment recorded yet.

---

On clicking [+ Record Judgment]:

Record Judgment

Judgment Date *
  [mm/dd/yyyy]

Outcome *
  [Select: Won / Lost ▼]

Amount Awarded (TZS)
  [Optional                ]

Legal Costs Awarded
  [Select: In Favour of FCC / Against FCC / None ▼]

Other Costs (repeatable)
  [Cost Type:              ]  [Amount (TZS):           ]  [+ Add Another]

Remarks
  [Any remarks on the judgment         ]

Appeal Period Deadline
  [mm/dd/yyyy]

Upload Judgment Document *
  [Upload file   ]  [No file chosen]

[Cancel]  [Save Draft]  [Submit for LM Review]

> On Submit for LM Review: Legal Manager reviews and recommends Accept or Appeal to DG.
> DG makes final decision:
>   - Accept → case proceeds to final financials and closure workflow.
>   - Appeal → set AppealDueDate. System AUTO-CREATES a FilingDefendant of type "Notice of Appeal"
>              and a Task with deadline = AppealDueDate. Both are created automatically.
>   - If AppealDueDate passes without filing, the task becomes OVERDUE.

---

On DG decision screen (DG role only):

DG Decision on Judgment
JUD-2025-001 — ABC Company Ltd vs FCC — Outcome: Lost

Legal Manager Recommendation: Appeal

Your Decision *
  [ ] Accept Judgment
  [ ] File Appeal

If Appeal:
  Appeal Due Date *   [mm/dd/yyyy]

[Cancel]  [Confirm Decision]

> On "File Appeal" + confirm:
>   - System creates FilingDefendant: Type = "Notice of Appeal", Status = DRAFT.
>   - System creates Task: "File Notice of Appeal", Due = AppealDueDate, Assigned to Legal Officer.
>   - Case stage → Appeal Filed.

---

### 9.TAB8: Report (Chronological Timeline)

Report & Timeline
[Export PDF]  [Export Excel]

2025-01-15
System
Case Registered
  Auto-generated reference FCC/SUED/2025/001 by Maria Sanga.

2025-01-16
DG Office
DG Directive Issued
  "File defence immediately" — Directive issued by DG.

2025-01-25
Maria Sanga
Statement of Defence Filed
  FIL-2025-001 — Written Statement of Defence v1 — marked as Filed.

2025-02-05
Maria Sanga
Hearing Attended
  HRG-2025-001 — Mention — adjourned to March 20.

2025-02-10
RO Office
Plaintiff Response Received
  RES-DEF-001 — Preliminary Objections received.

---

### 9.TAB9: Activity Log

Activity Log

| Date                | User          | Action                        | Detail                                              |
|---------------------|---------------|-------------------------------|-----------------------------------------------------|
| 2025-01-15 10:00    | System        | Case Registered               | Auto-generated ref FCC/SUED/2025/001                |
| 2025-01-15 10:01    | System        | DG Notified                   | Notification sent to DG for new case review         |
| 2025-01-16 14:00    | DG Office     | DG Directive Issued           | "File defence immediately"                          |
| 2025-01-25 09:00    | Maria Sanga   | Filing Submitted for Approval | FIL-2025-001 submitted to Legal Manager             |
| 2025-01-26 11:00    | Peter Mwanga  | Filing Approved (LM)          | FIL-2025-001 approved by Legal Manager              |
| 2025-01-27 16:00    | DG Office     | Filing Approved (DG)          | FIL-2025-001 approved by DG                         |
| 2025-01-28 09:30    | Maria Sanga   | Filing Marked as Filed        | FIL-2025-001 filed in court                         |
| 2025-02-05 14:00    | Maria Sanga   | Hearing Recorded              | HRG-2025-001 — Mention — Adjourned                  |

---


---

## 10. FCC SUING
URL: /service/grc/legal/fcc-suing

FCC Suing — Case Repository
Manage cases where FCC is the plaintiff

[+ Report Breach]          (Department User — simplified intake)
[+ Register Full Breach Report]   (Legal Officer / Registry Officer — full registration)
[Search cases...]   [All Stages ▼]   [All Types ▼]   [All Risks ▼]

---
Dashboard KPIs (as per SRS §5.0):
[Total Cases Filed: 5]  [Active Cases: 4]  [Cases on Appeal: 0]  [Pending DG Review: 1]  [High Risk Cases: 2]  [Won/Loss Ratio: 0/1]  [Total Recoverable: TZS 850M]  [Recovered Amount: TZS 0]
---

| Case Ref No           | Respondent               | Case Type   | Court         | Claim Amount | Stage            | Status  | Risk   | Next Hearing | Actions |
|-----------------------|--------------------------|-------------|---------------|--------------|------------------|---------|--------|--------------|---------|
| FCC/SUING/2025/001    | ABC Corporation          | Litigation  | High Court    | TZS 200M     | Hearing Stage    | Active  | High   | 2025-03-25   | [View]  |
| FCC/SUING/2025/002    | XYZ Telecom Ltd          | Litigation  | High Court    | TZS 100M     | Under Mediation  | Active  | Medium | —            | [View]  |
| FCC/SUING/2025/003    | Delta Energy Co          | Litigation  | Arbitration   | TZS 500M     | Under Arbitration| Active  | High   | 2025-04-05   | [View]  |
| FCC/SUING/2024/008    | Quick Services Ltd       | Settlement  | —             | TZS 50M      | Closed           | Closed  | Low    | —            | [View]  |
| FCC/SUING/2025/004    | Mega Holdings Group      | Litigation  | —             | —            | Under DG Review  | Active  | High   | —            | [View]  |

Showing 1-5 of 5 | Rows per page: 10

---

ENTRY POINT 1 — On clicking [+ Report Breach]:
(Actor: Department User — simplified intake form)

Report Breach
Submit a breach for FCC to pursue legal action. Required fields marked with *.

Breach Information
Reporting Department *
  [Select department ▼]

Nature of Breach *
  [Select: Antitrust / Unfair Trade / Consumer Protection / Price Fixing / Other ▼]

Respondent Details
Respondent Name *
  [Enter respondent name            ]

Respondent Type *
  [Select: Company / Individual / Partnership / Government Entity ▼]

Estimated Claim Amount (TZS)
  [Optional                         ]

Description of Breach *
  [Describe the breach in detail... ]

Supporting Documents (Optional)
  [Upload files   ]  [No files chosen]  (PDF, DOC, DOCX, XLSX — max 10MB)

Urgency Level *
  [Select: Urgent / High / Medium / Low ▼]

[Cancel]  [Save Draft]  [Submit to DG]

> Creates CasePlaintiff with Stage = New.
> Auto-generates Case Ref: FCC/SUING/YYYY/NNN.
> On Submit: DG is notified automatically.
> NOTE: Risk Level is NOT on this simplified form — it is captured in the Full Breach Report.

---

ENTRY POINT 2 — On clicking [+ Register Full Breach Report]:
(Actor: Legal Officer or Registry Officer — full registration form)

Register Full Breach Report
Full registration for FCC to initiate litigation. Required fields marked with *.

Breach Information
Reporting Department *
  [Select department ▼]

Nature of Breach *
  [Select: Antitrust / Unfair Trade / Consumer Protection / Price Fixing / Other ▼]

Respondent Details
Respondent Name *
  [Enter respondent name            ]

Respondent Type *
  [Select: Company / Individual / Partnership / Government Entity ▼]

Case Financial Details
Estimated Claim Amount (TZS)
  [Enter amount                     ]

Description of Breach *
  [Describe the breach in detail... ]

Initiation Documents
  [Upload files   ]  [No files chosen]  (multiple documents — full case opening pack)
  [+ Add Another Document]   (each with Title and Type)

Risk & Urgency
Urgency Level *
  [Select: Urgent / High / Medium / Low ▼]

Risk Level *
  [Select: High / Medium / Low ▼]

[Cancel]  [Save Draft]  [Submit to DG]

> Creates CasePlaintiff with Stage = New.
> Auto-generates Case Ref: FCC/SUING/YYYY/NNN.
> On Submit: DG is notified automatically.

---

On clicking [View] for FCC/SUING/2025/001:
URL: /service/grc/legal/fcc-suing/1

FCC vs ABC Corporation
FCC/SUING/2025/001
Stage: [Hearing Stage]   Risk: [High Risk]

[Edit Basic Info]  [Assign Legal Officers]  [Initiate Closure]

Respondent:         ABC Corporation
Respondent Type:    Company
Reporting Dept.:    Research & Market Analysis
Nature of Breach:   Antitrust
Estimated Claim:    TZS 200,000,000
Case Type:          Litigation
Court Level:        High Court
Next Hearing:       2025-03-25

Assigned Legal Officer(s): Anna Kimaro
Assigned Legal Manager:    Peter Mwanga

DG Review Status:   [Directive Issued]
DG Directive:       "Proceed with litigation immediately" — 2025-01-12

Description:        Evidence of price-fixing agreement between major suppliers in the construction sector.

Case Folder:        [Open in Document Repository ↗]

---
CASE DETAIL TABS:
[ Filings ] [ Responses ] [ Hearings ] [ Settlement ] [ Financials ] [ Tasks ] [ Judgment ] [ Report ] [ Activity Log ]
---

> All tabs follow the IDENTICAL structure as FCC Sued with the following differences:

### Filing differences (FCC Suing):
Filing Types: Plaint / Petition / Statement of Claim / Application / Chamber Summons / Affidavit / Bill of Cost / Notice of Appeal
(vs Defendant: Statement of Defence / Affidavit / Application / etc.)

### Response differences (FCC Suing):
Response Types: Preliminary Objections / Response to Ruling / Response to Orders / Response to Affidavits / Counter Claim / Initial Response / Preliminary Objectives

### Financials differences (FCC Suing):
Cards:
  [Claim Amount: TZS 200,000,000]   [Legal Costs Incurred: TZS 6,000,000]   [Amount Awarded: —]   [Costs Awarded: —]   [Other Costs: TZS 3,000,000]   [Recovered Amount: TZS 0]

> Record Recovery button: visible when judgment outcome = Won
> Record Payment button: visible when judgment outcome = Lost

### Judgment differences (FCC Suing):
Same fields as FCC Sued. On DG decision:
  - Accept → case proceeds to final financials and closure.
  - Appeal → system AUTO-CREATES a FilingPlaintiff of type "Notice of Appeal" and a Task.

---
All other tabs (Tasks, Hearings, Settlement, Report, Activity Log) are IDENTICAL to FCC Sued.
---


---

## CROSS-CUTTING NOTES (apply to entire module)

### DG Review Section (inside case details)
When Stage = "Under DG Review", a DG Review panel appears at the top of the case detail:

DG Review
This case is pending DG review.

(Visible to DG only):
  [Issue Directive]   →  opens DirectiveLitigation form; on submit, Stage → Directive Issued
  [Mark as Reviewed]  →  marks DGReviewStatus = Reviewed without issuing directive; Stage → next applicable

DG Directive form:

Issue DG Directive
CaseID: FCC/SUED/2025/002

Instruction *
  [Enter the directive clearly...      ]

Due Date *
  [mm/dd/yyyy]

Attachments (Optional)
  [Upload file   ]  [No file chosen]

[Cancel]  [Issue Directive]

---

### Case Closure (both modules)
[Initiate Closure] button — visible to Legal Manager only when case is appropriate stage.
On click:

Initiate Case Closure
This action will submit the case for DG approval to close.

Closure Summary *
  [Summarise the case outcome and basis for closure...]

[Cancel]  [Submit to DG for Approval]

> On DG approval: case becomes READ-ONLY. No further edits allowed.
> Case proceeds to archiving per configured period.

---

### Filing Approval Chain (both modules)
The approval chain status is visible on every filing row:

Status badge examples:
  [Draft]                → authored by Legal Officer, not yet submitted
  [Under Review (LM)]    → submitted, Legal Manager reviewing
  [Approved by LM]       → Legal Manager approved, awaiting DG
  [Under Review (DG)]    → DG reviewing
  [Approved]             → DG approved; Legal Officer can mark as Filed
  [Filed]                → filed in court, date recorded

---

*End of Refined Menu Structure Document*
*(SRS Reference: Legal_Service.md — 100% coverage)*
