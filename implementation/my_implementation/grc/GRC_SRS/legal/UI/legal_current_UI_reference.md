# Legal Services Module — Current Implemented UI Reference
*(Written from actual component source code — not from design documents)*
*(Components: apps/staff-portal/src/pages/grc/legal/ and src/components/grc/legal/)*

---

## SIDEBAR NAVIGATION

```

    Legal Services
    ├── Dashboard
    ├── Governing Bodies
    │     ├── Types
    │     ├── Bodies
    │     └── Members                      
    ├── Meetings                       
    ├── Resolutions                    
    ├── Directives                     
    ├── Minutes                         
    ├── Submissions for Determination  
    ├── Public Register                 
    ├── FCC Sued (Defendant)            
    └── FCC Suing (Plaintiff)         
```

---

## 1. Dashboard
File: `LegalDashboardPage.tsx`
URL: /service/grc/legal/

### General KPI Cards (role-gated)

| Card Label                  | Permission required          | Navigates to          |
|-----------------------------|------------------------------|-----------------------|
| Active Meetings             | canViewMeetings              | /legal/meetings       |
| Open Directives             | canViewDirectives            | /legal/directives     |
| Active Cases (Sued)         | canViewCases                 | /legal/fcc-sued       |
| Active Cases (Suing)        | canViewCases                 | /legal/fcc-suing      |
| Pending Filings             | canViewFilings               | —                     |
| Overdue Tasks               | (always shown)               | —                     |
| Pending Submissions         | (always shown)               | /legal/submissions    |
| Minutes Awaiting Approval   | canViewMinutes               | /legal/minutes        |

### FCC Sued KPI Section (canViewCases only)
Cards: Total Cases Filed · Active Cases · Pending DG Review · High Risk Cases · Cases on Appeal · Won/Loss Ratio

### FCC Suing KPI Section (canViewCases only)
Cards: Total Cases Filed · Active Cases · Pending DG Review · High Risk Cases · Cases on Appeal (+ more plaintiff KPIs)

> All values from hooks: `useLegalDashboardStats`, `useCaseDashboardDefendant`, `useCaseDashboardPlaintiff`

---

## 2. Committee Types
File: `CommitteeTypesPage.tsx`
URL: /service/grc/legal/committee-types

### List
> `[+ Create]` button: `canManageGoverningBody` only

| Column  | Notes                   |
|---------|-------------------------|
| Code    |                         |
| Name    |                         |
| Status  | Active / Inactive badge |
| Created |                         |

Actions per row: [Edit] [Delete] — `canManageGoverningBody` only

### Create / Edit Dialog (`CreateCommitteeTypeDialog`)
| Field       | Type     | Required | Notes                           |
|-------------|----------|----------|---------------------------------|
| Code        | text     | *        | e.g. `BOARD`, `AUDIT_COMM`      |
| Name        | text     | *        | e.g. `Board of Directors`       |
| Description | textarea | —        |                                 |
| Active      | switch   | —        | boolean toggle                  |

---

## 3. Governing Bodies
File: `GoverningBodiesPage.tsx`
URL: /service/grc/legal/governing-bodies

### List
> `[+ Create]` button: `canManageGoverningBody` only

| Column          | Notes                |
|-----------------|----------------------|
| Name            |                      |
| Committee Type  |                      |
| Members         | count                |
| Status          | Active / Inactive    |

Filters: Search (text)
Actions per row: [View] [Edit] [Delete] — `canManageGoverningBody` only

### Create / Edit Dialog (`CreateGoverningBodyDialog`)
| Field                 | Type     | Required | Notes                                                          |
|-----------------------|----------|----------|----------------------------------------------------------------|
| Committee Type        | select   | *        | searchable                                                     |
| Name                  | text     | *        | e.g. `Legal Committee`                                         |
| Composite Title       | text     | —        | e.g. `FCC Legal Committee`                                     |
| Description           | textarea | —        |                                                                |
| Secretary User IDs    | text     | —        | comma-separated UUIDs                                          |
| Meeting Number Prefix | text     | —        | e.g. `LC`, `BOARD` (default: `MTG`)                            |
| Number Format         | select   | —        | Sequential: `MTG-202603-001` / Financial Year: `MTG-FY2025/2026-001` |

### Governing Body Detail
URL: /service/grc/legal/governing-bodies/:id

Header: body name · composite title / committee type as subtitle · Active/Inactive badge · `[Edit]` (`canManageGoverningBody`)

**Details Card** — fields displayed:
- Committee Type
- Chairperson
- Total Members
- Status
- Created
- Last Updated

**Description Card** — shown only if `body.description` has content

**Secretaries Card** — shown only if `secretary_user_ids.length > 0` — displays UserDisplay badges per secretary

**Meeting Configuration Card** — shown only to `canManageGoverningBody` (meeting prefix/format settings)

**Members Table** (below all cards — NOT inside a tab)
> `[+ Add Member]` — `canManageGoverningBody` only

| Column          | Notes                       |
|-----------------|-----------------------------|
| Full Name       |                             |
| Position        |                             |
| Type            | internal / external         |
| Joined Date     |                             |
| Status          |                             |
| Actions         | [Edit] [Delete] per row     |

Add/Edit Member Dialog (`CreateMemberDialog`):
| Field        | Type   | Required | Notes                                  |
|--------------|--------|----------|----------------------------------------|
| Governing Body | select | *      | searchable                             |
| User ID      | text   | *        | UUID, e.g. `Enter user UUID...`       |
| Position     | select | *        | `Select position...`                   |
| Member Type  | select | *        | `internal` / `external`               |
| Joined Date  | date   | *        |                                        |

---

## 4. Members
File: `MembersPage.tsx`
URL: /service/grc/legal/members

### List (read view only — members are managed from within a Governing Body detail page)
> No create button on this page

| Column          | Notes                       |
|-----------------|-----------------------------|
| Full Name       |                             |
| Governing Body  |                             |
| Position        |                             |
| Type            | internal / external         |
| Joined          |                             |
| Status          | Active / Inactive badge     |

Filters: Search (text)

---

## 5. Meetings
File: `LegalMeetingsPage.tsx`, `LegalMeetingDetailPage.tsx`
URL: /service/grc/legal/meetings

### List
> `[+ Create Meeting]` button: `canManageMeetings` only

| Column         | Notes                 |
|----------------|-----------------------|
| Reference      |                       |
| Title          |                       |
| Governing Body |                       |
| Mode           |                       |
| Start Date     |                       |
| Status         | badge (MEETING_STATUSES) |

Filters:
- Status dropdown: All Statuses / Draft / Registered / Invitations Sent / Agenda Shared / Quorum Ready / Ongoing / Postponed / Closed / Cancelled / Rescheduled
- Search (text)

### Create / Edit Dialog (`CreateMeetingDialog`)
| Field                 | Type          | Required | Notes                                        |
|-----------------------|---------------|----------|----------------------------------------------|
| Title                 | text          | *        | e.g. `Legal Committee Meeting - March 2026`  |
| Governing Body        | select        | *        | searchable                                   |
| Meeting Type          | select        | *        |                                              |
| Mode                  | select        | *        |                                              |
| Start Date & Time     | datetime      | *        |                                              |
| End Date & Time       | datetime      | *        |                                              |
| Location              | text          | —        | e.g. `Conference Room A`                     |
| Virtual Meeting Link  | text (URL)    | —        | shown when mode is virtual                   |

### Meeting Detail
URL: /service/grc/legal/meetings/:id

Header: Meeting title · Governing Body name · Status badge
Header buttons (`canManageDirectives`):  `[Issue Directive]` · (`canManageMinutes`) `[Create Minutes]`
When meeting is `ongoing` or `closed` → `[Record Outcome]` appears per agenda item
When meeting is `ongoing` → `[Declare Conflict]` appears per agenda item

**The detail page does NOT use tabs — sections are stacked vertically:**

1. **MeetingParticipantsSection** — attendees from governing body members, attendance tracking
2. **MeetingAgendaSection** — list of agenda items
   - `[Record Outcome]` per item → `RecordAgendaOutcomeDialog` (when ongoing/closed)
   - `[Declare Conflict]` per item → `ConflictDeclarationDialog` (when ongoing)
3. **MattersArisingSection** — action items / matters arising

Dialogs used on this page:
- `CreateDirectiveDialog` (from `[Issue Directive]`)
- `CreateMinutesDialog` (from `[Create Minutes]`)
- `RecordAgendaOutcomeDialog`
- `ConflictDeclarationDialog`
- `RescheduleMeetingDialog`

---

## 6. Resolutions
File: `ResolutionsPage.tsx`
URL: /service/grc/legal/resolutions

### List (read-only register — resolutions are auto-created from meeting agenda outcomes)
> No create button (`showCreateButton={false}` in the component)

| Column              | Notes                         |
|---------------------|-------------------------------|
| Resolution          | text, first 100 chars shown   |
| Status              | badge (Approved/Rejected/Noted)|
| Date Adopted        |                               |

Filters:
- Status dropdown: All Statuses / Approved / Rejected / Noted
- Search (text)

On `[View]` → opens an **inline Dialog** (NOT a separate page):

**Resolution Detail Dialog** fields:
- Status badge
- Date Adopted
- Full Resolution Text (whitespace preserved)
- Effective Date (if set)

---

## 7. Directives
File: `DirectivesPage.tsx`, `DirectiveDetailPage.tsx`
URL: /service/grc/legal/directives

### List (read-only; directives are created from within Meeting detail)
> No create button on this page

| Column          | Notes                         |
|-----------------|-------------------------------|
| Reference       |                               |
| Description     | first 80 chars                |
| Meeting         | meeting title                 |
| Assigned To     |                               |
| Priority        |                               |
| Status          | badge (DIRECTIVE_STATUSES)    |
| Due Date        |                               |

Filters:
- Status dropdown: All Statuses / Open / In Progress / Overdue / Closed / Fully Closed
- Search (text)

On `[View]` → navigates to `/service/grc/legal/directives/:id`

### Directive Detail
URL: /service/grc/legal/directives/:id

Header: Reference number · Description · Status badge
Buttons:
- `[Close Directive]` → `CloseDirectiveDialog` (`canManageDirectives`)
- `[Fully Close]` → `FullyCloseDirectiveDialog` (`canApproveDirectiveClosure`)

Fields displayed: Meeting (linked) · Assigned To · Priority · Due Date · Status

---

## 8. Minutes
File: `MinutesPage.tsx`, `MinutesDetailPage.tsx`
URL: /service/grc/legal/minutes

### List (read-only; minutes are created from within Meeting detail)
> No create button on this page

| Column      | Notes                     |
|-------------|---------------------------|
| Reference   |                           |
| Title       |                           |
| Meeting     | meeting title             |
| Status      | badge (MINUTES_STATUSES)  |
| Prepared By |                           |
| Created     |                           |

Filters:
- Status dropdown: All Statuses / Draft / Pending Approval / Approved
- Search (text)

On `[View]` → navigates to `/service/grc/legal/minutes/:id`

### Minutes Detail
URL: /service/grc/legal/minutes/:id

Header: Title · Reference number · Status badge
Fields displayed: Reference Number · Meeting (linked) · Status · Prepared By

> Minutes are created using `CreateMinutesDialog` launched from within the Meeting detail page.

---

## 9. Submissions for Determination
File: `SubmissionsPage.tsx`, `SubmissionDetailPage.tsx`
URL: /service/grc/legal/submissions

### List
> `[+ Create Submission]` button: **NO permission gate** — any authenticated user can create

| Column      | Notes                          |
|-------------|--------------------------------|
| Title       |                                |
| Target Body | governing body name            |
| Status      | badge (SUBMISSION_STATUSES)    |
| Submitted   | date                           |

Filters:
- Status dropdown: All Statuses / Submitted / Under Review / Determined / Withdrawn
- Target Body dropdown (active governing bodies from lookup)
- Search (text)

Actions per row:
- `[View]` — navigates to detail
- `[Edit]` — only if `status === 'submitted'` AND current user is the originator

### Create / Edit Dialog (`CreateSubmissionDialog`)
| Field                 | Type     | Required | Notes                                           |
|-----------------------|----------|----------|-------------------------------------------------|
| Title                 | text     | *        | e.g. `Budget Review Request`                    |
| Target Governing Body | select   | *        | searchable, active bodies only                  |
| Description           | textarea | *        | e.g. `Describe the matter requiring determination...` |

### Submission Detail
URL: /service/grc/legal/submissions/:id

Header: Title · Reference Number (auto-generated, font-mono) · Status badge
Buttons — visible only if `status === 'submitted'` AND current user is originator:
- `[Edit]` → opens `CreateSubmissionDialog` in edit mode
- `[Withdraw]` → confirmation dialog → status → Withdrawn

Alert shown when `status !== 'submitted'` AND `!== 'withdrawn'`:
> "This submission is linked to a meeting agenda and can no longer be edited."

**Submission Details Card** fields:
- Title
- Target Body
- Status
- Submission Date
- Submitter Department
- Created

**Description Card** — shown if `description` has content

**Supporting Documents Card** — shown if `supporting_documents[]` array has items

**Determination Outcome Card** — shown when status = `determined`:
- Outcome
- Determination Date
- Outcome Notes
- `[View Determining Meeting]` → navigates to meeting detail

---

## 10. Public Register
File: `PublicRegisterPage.tsx`, `PublicDecisionDetailPage.tsx`
URL: /service/grc/legal/public-register

### List
> `[+ Create]` button: `canManagePublicDecisions` only

KPI cards above the list table:
- Total Decisions
- Draft (count from current results)
- Published (count from current results)

| Column          | Notes                            |
|-----------------|----------------------------------|
| Title           |                                  |
| Decision Date   |                                  |
| Status          | badge (Draft / Published)        |
| Published Date  |                                  |

Filters:
- Status dropdown: All / Draft / Published
- Search (text)

### Create / Edit Dialog (`CreatePublicDecisionDialog`)
| Field          | Type     | Required | Notes                                             |
|----------------|----------|----------|---------------------------------------------------|
| Title          | text     | *        | e.g. `Spectrum Allocation Decision`               |
| Decision Date  | date     | *        |                                                   |
| Linked Meeting | select   | —        | optional                                          |
| Body Text      | textarea | *        | background and context                            |
| Decision Text  | textarea | *        | the formal decision statement                     |

### Public Decision Detail
URL: /service/grc/legal/public-register/:id

Header: Title · Status badge
Buttons — shown to `canManagePublicDecisions`, only when `status === 'draft'`:
- `[Publish]` → `AlertDialog` confirmation → status → Published (read-only after)
- `[Edit]` → opens `CreatePublicDecisionDialog` in edit mode
- `[Delete]` → `AlertDialog` confirmation → delete

Alert shown when status = `published`:
> "This decision has been published and is now read-only."

**Decision Details Card** fields:
- Title
- Decision Date
- Status
- Published Date
- Created
- Last Updated

**Body Text Card** — shown if `body_text` has content

**Decision Text Card** — shown if `decision_text` has content

---

## 11. FCC Sued (Defendant Cases)
File: `FCCSuedCasesPage.tsx`, `FCCSuedCaseDetailPage.tsx`
URL: /service/grc/legal/fcc-sued

### List
> `[+ Register Case]` button: `canRegisterCases` only

KPI cards above the list (counts from current page results):
- New
- Hearing Stage
- Judgment Received
- On Hold

Toggles:
- `[ ] Show Archived` checkbox

| Column        | Notes                      |
|---------------|----------------------------|
| Case No.      |                            |
| Title         |                            |
| Plaintiff     |                            |
| Court         |                            |
| Stage         | badge (CASE_STAGES)        |
| Filed         | date registered            |

Filters: Search (text) · Show Archived (checkbox)

### Register Case Dialog (`CreateCaseDefendantDialog`)
| Field                | Type     | Required | Notes                                  |
|----------------------|----------|----------|----------------------------------------|
| Court Case Number    | text     | *        | e.g. `Civil Case No. 123/2026`         |
| Court Registry       | text     | *        | e.g. `Dar es Salaam`                   |
| Court Level          | select   | *        |                                        |
| Service Date         | date     | *        |                                        |
| Plaintiffs           | text     | *        | comma-separated names                  |
| Plaintiff Advocate   | text     | —        |                                        |
| Claim Amount (TZS)   | number   | —        |                                        |
| Department Affected  | text     | —        |                                        |
| Nature of Claim      | textarea | *        |                                        |
| Urgency Level        | select   | —        | Urgent / High / Medium / Low           |
| Risk Level           | select   | —        | High / Medium / Low                    |

### FCC Sued Case Detail
URL: /service/grc/legal/fcc-sued/:id

Header: Court Case Number · Stage badge (CASE_STAGES)
Banners:
- "Case On Hold" alert banner — when stage = `on_hold`
- "Case Closed" alert banner — when stage = `closed` → `isReadOnly = true` (all tabs become read-only)

**Case Information Card** (2/3 width) fields:
- Court Case No.
- Court Registry
- Court Level
- Plaintiff(s)
- Plaintiff Advocate
- Claim Amount (TZS, comma-formatted)
- Nature of Claim
- Service Date
- Next Hearing

**Actions Card** (1/3 width) — buttons are role- and stage-gated:

| Button               | Condition                                         |
|----------------------|---------------------------------------------------|
| Submit for DG Review | stage = `new` + `canManageCases`                  |
| Mark DG Reviewed     | stage = `under_dg_review` + `canManageCases`      |
| Hold Case            | not closed, not on_hold + `canManageCases`        |
| Resume Case          | stage = `on_hold` + `canManageCases`              |
| Request Closure      | not closed, not on_hold + `canManageCases`        |
| Approve Closure      | not closed + `canCloseCases`                      |
| *(separator)*        |                                                   |
| Archive Case         | `is_active` + closed + `canManageCases`           |
| Unarchive Case       | `!is_active` + `canManageCases`                   |

#### Case Detail Tabs (9 tabs — shadcn Tabs component)

```
[ Directives ] [ Filings ] [ Responses ] [ Hearings ] [ Settlements ] [ Judgments ] [ Financials ] [ Tasks ] [ Report ]
```

All section components receive `caseType="defendant"` and `isReadOnly={isReadOnly}` props.

**TAB: Directives** — `CaseDirectivesSection`
DG directives issued on this case.

**TAB: Filings** — `CaseFilingsSection`
FCC's court filings (statement of defence, affidavit, etc.)
Filing status progression:
`Draft` → `Under Review (LM)` → `Approved (LM)` → `Under Review (DG)` → `Approved` → `Filed`

**TAB: Responses** — `CaseResponsesSection`
Responses/documents received from the plaintiff.

**TAB: Hearings** — `CaseHearingsSection`
Scheduled and past hearing records.
- `[+ Schedule Hearing]` → `CreateHearingDialog`
- `[Record Outcome]` → `HearingReportDialog`

**TAB: Settlements** — `CaseSettlementSection`
Settlement discussions.
Status values: `Proposed` / `Agreed` / `Rejected`

**TAB: Judgments** — `CaseJudgmentSection`
Judgment outcome and DG decision on whether to appeal.
- Judgment outcomes: `Won` / `Lost`
- DG decisions: `Accept` / `Appeal`
- `[+ Record Judgment]` → `RecordJudgmentDialog` (`canRecordJudgments`)
- DG decision → `DGDirectiveDecisionDialog`

**TAB: Financials** — `CaseFinancialsSection`
Legal costs and payments.
Financial entry statuses: `Requested` / `Approved` / `Processed`
- `[+ Record Cost]` → `FinancialRecordDialog`

**TAB: Tasks** — `CaseTasksSection`
Tasks and deadlines for this case.
Task statuses: `Open` / `In Progress` / `Overdue` / `Closed`
- `[+ Add Task]` → `CreateLitigationTaskDialog`

**TAB: Report** — `CaseReportSection`
Chronological timeline of all case activity.

---

## 12. FCC Suing (Plaintiff Cases)
File: `FCCSuingCasesPage.tsx`, `FCCSuingCaseDetailPage.tsx`
URL: /service/grc/legal/fcc-suing

### List
Two create paths:
- `[Raise Breach Report]` button — always visible to any authenticated user → `BreachReportIntakeDialog` (simplified intake)
- `[+ Register Full Case]` button — `canRegisterCases` OR `canManageCases` → `CreateCasePlaintiffDialog`

KPI cards above the list (6 total):
- New
- Hearing Stage
- Judgment Received
- On Hold
- Recoverable Amount (TZS sum of estimated_claim_amount)
- Recovered Amount (TZS sum of recovered_amount)

Toggles:
- `[ ] Show Archived` checkbox
- `[ ] My Cases` checkbox — shown only to `canManageCases` users

| Column       | Notes                                          |
|--------------|------------------------------------------------|
| Case Ref     | reference_number                               |
| Respondent   | respondent_name                                |
| Court        | court_name or court_level                      |
| Claim Amount | estimated_claim_amount, TZS formatted          |
| Stage        | badge (CASE_STAGES)                            |
| Risk         | risk_level                                     |
| Type         | badge: `Breach Report` vs `Full`               |
| Next Hearing |                                                |

Filters: Search (text) · Show Archived · My Cases

### Raise Breach Report Dialog (`BreachReportIntakeDialog`)
Simplified intake — any authenticated user:
| Field              | Type     | Required | Notes                        |
|--------------------|----------|----------|------------------------------|
| Reporting Department | text   | *        |                              |
| Respondent Name    | text     | *        |                              |
| Respondent Type    | select   | *        |                              |
| Nature of Breach   | textarea | *        |                              |
| Description        | textarea | *        |                              |
| Urgency Level      | select   | *        | Urgent / High / Medium / Low |

> No Court Level, no Risk Level, no Claim Amount — those are for full registration only.

### Register Full Case Dialog (`CreateCasePlaintiffDialog`)
| Field                    | Type     | Required | Notes                        |
|--------------------------|----------|----------|------------------------------|
| Reporting Department     | text     | *        | e.g. `Broadcasting`          |
| Respondent Name          | text     | *        |                              |
| Respondent Type          | select   | *        |                              |
| Nature of Breach         | textarea | *        |                              |
| Estimated Claim Amount (TZS) | number | —      |                              |
| Description              | textarea | —        |                              |
| Court Level              | select   | *        |                              |
| Urgency Level            | select   | *        | Urgent / High / Medium / Low |
| Risk Level               | select   | *        | High / Medium / Low          |

### FCC Suing Case Detail
URL: /service/grc/legal/fcc-suing/:id

Header: Case reference number · Stage badge · "Breach Report" badge (when `registration_type === 'simplified'`)
Banners: "Case On Hold" · "Case Closed" → `isReadOnly = true`

**Case Information Card** fields:
- Respondent Name
- Respondent Type
- Reporting Dept.
- Nature of Breach
- Estimated Claim Amount (TZS)
- Court Level
- Next Hearing

**Actions Card** — identical lifecycle buttons as FCC Sued (Submit for DG Review / Hold / Resume / Request Closure / Approve Closure / Archive / Unarchive)

#### Case Detail Tabs (9 tabs — identical names as FCC Sued)

```
[ Directives ] [ Filings ] [ Responses ] [ Hearings ] [ Settlements ] [ Judgments ] [ Financials ] [ Tasks ] [ Report ]
```

All section components are identical to FCC Sued but passed `caseType="plaintiff"`.
`CaseFinancialsSection` in plaintiff mode also displays Recoverable Amount / Recovered Amount totals.

---

## 13. Permission Codes Reference

File: `src/hooks/useLegalPermissions.ts`
Permission codes are sourced from the JWT token (`permissions_flat` claim) — NOT role-based.
A superuser (`*` in token) bypasses all checks.

| Permission Code                         | Controls                                                      |
|-----------------------------------------|---------------------------------------------------------------|
| `grc:legal_governing_body:view`         | View governing bodies and members                             |
| `grc:legal_governing_body:manage`       | Create/edit/delete governing bodies, members, committee types |
| `grc:legal_meeting:view`                | View meetings list and detail                                 |
| `grc:legal_meeting:manage`              | Create/edit meetings, issue directives, create minutes        |
| `grc:legal_meeting:approve`             | Approve meeting records                                       |
| `grc:legal_minutes:view`                | View minutes                                                  |
| `grc:legal_minutes:manage`              | Create minutes                                                |
| `grc:legal_minutes:approve`             | Approve minutes                                               |
| `grc:legal_case:view`                   | View case lists and detail pages                              |
| `grc:legal_case:manage`                 | Lifecycle management (hold, resume, request closure, archive) |
| `grc:legal_case:close`                  | Approve case closure (DG level)                               |
| `grc:legal_case:register`               | Register new cases (both sued and suing)                      |
| `grc:legal_filing:view`                 | View court filings                                            |
| `grc:legal_filing:manage`               | Create and edit filings                                       |
| `grc:legal_filing:approve`              | Approve filings (LM and DG steps)                             |
| `grc:legal_hearing:view`                | View hearing records                                          |
| `grc:legal_hearing:manage`              | Schedule hearings and record outcomes                         |
| `grc:legal_settlement:view`             | View settlement records                                       |
| `grc:legal_settlement:manage`           | Create and edit settlement records                            |
| `grc:legal_settlement:approve`          | Approve settlements                                           |
| `grc:legal_judgment:view`               | View judgment records                                         |
| `grc:legal_judgment:manage`             | Manage judgment records                                       |
| `grc:legal_judgment:record`             | Record judgment outcome                                       |
| `grc:legal_directive:view`              | View directives                                               |
| `grc:legal_directive:manage`            | Create and update directives                                  |
| `grc:legal_directive:approve_closure`   | Fully close a directive                                       |
| `grc:legal_appeal:view`                 | View appeal records                                           |
| `grc:legal_appeal:manage`               | Manage appeals                                                |
| `grc:legal_notice:view`                 | View legal notices                                            |
| `grc:legal_notice:manage`               | Manage legal notices                                          |
| `grc:legal_public_decision:view`        | View public register                                          |
| `grc:legal_public_decision:manage`      | Create, edit, and publish public decisions                    |

---

## 14. Status Value Reference

### Meeting Statuses (`MEETING_STATUSES`)
`draft` · `registered` · `invitations_sent` · `agenda_shared` · `quorum_ready` · `ongoing` · `postponed` · `closed` · `cancelled` · `rescheduled`

### Submission Statuses (`SUBMISSION_STATUSES`)
`submitted` · `under_review` · `determined` · `withdrawn`

### Directive Statuses (`DIRECTIVE_STATUSES`)
`open` · `in_progress` · `overdue` · `closed` · `fully_closed`

### Minutes Statuses (`MINUTES_STATUSES`)
`draft` · `pending_approval` · `approved`

### Resolution Statuses (`RESOLUTION_STATUSES`)
`approved` · `rejected` · `noted`

### Filing Statuses (`FILING_STATUSES`)
`draft` → `under_review_lm` → `approved_lm` → `under_review_dg` → `approved` → `filed`

### Case Stages (`CASE_STAGES`)
`new` → `under_dg_review` → `directive_issued` → `hearing_stage` → `judgment_received` → `appeal_filed` → `closed`
(also: `on_hold`)

### Settlement Statuses (`SETTLEMENT_STATUSES`)
`proposed` · `agreed` · `rejected`

### Judgment Outcomes (`JUDGMENT_OUTCOMES`)
`won` · `lost`

### DG Decisions (`DG_DECISIONS`)
`accept` · `appeal`

### Task Statuses (`TASK_STATUSES`)
`open` · `in_progress` · `overdue` · `closed`

### Financial Entry Statuses (`FINANCIAL_ENTRY_STATUSES`)
`requested` · `approved` · `processed`

### Public Decision Statuses (`PUBLIC_DECISION_STATUSES`)
`draft` · `published`

---

*End of Legal Services Module — Current Implemented UI Reference*
*(Source verified from: apps/staff-portal/src/pages/grc/legal/*.tsx and src/components/grc/legal/*.tsx)*
