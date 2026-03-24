# Legal Module — Menu Transformation Plan
*(Incremental migration from current menu structure to refined menu structure)*

---

## 1. Transformation Strategy Overview

### 1.1 High-Level Approach

Each remaining menu is transformed **one at a time**, in dependency order. Each transformation follows this sequence:

1. Update sidebar config entry (title, URL, icon, position)
2. Update or create route(s) in App.tsx
3. Rename/refactor page components as needed
4. Update internal navigation links (breadcrumbs, card links, cross-page references)
5. Verify backend API alignment
6. Validate end-to-end (sidebar → page → API → data)

No two menus are transformed in the same step unless they share a dependency that requires simultaneous change.

### 1.2 Order of Transformation (Rationale)

The order is determined by:
- **Dependency chains** — menus that are referenced by other menus must transform first
- **Risk minimisation** — standalone read-only pages transform before complex interconnected ones
- **Already completed** — Dashboard and Governing Bodies are done

**Transformation Order:**

| Step | Current Menu                | Target Menu                  | Reason for Position                                   |
|------|-----------------------------|------------------------------|-------------------------------------------------------|
| ✅    | Dashboard                   | Dashboard                    | Already transformed                                   |
| ✅    | Governing Bodies (submenu)  | Governing Bodies (submenu)   | Already transformed                                   |
| 1    | Meetings                    | Meeting Repository           | Core engine — Meetings generate Resolutions, Directives, Minutes. Must transform before dependents. |
| 2    | *(new)*                     | Meeting Packs                | New menu — depends on Meeting Repository existing. Must come after Meetings. |
| 3    | Resolutions                 | Resolution Register          | Depends on Meetings. Rename + URL change + enhanced columns. |
| 4    | Directives                  | Directives                   | Depends on Meetings. URL change + enhanced list columns. |
| 5    | Submissions                 | Submission for Determination | Rename + URL change. Independent of other transforms.  |
| 6    | Minutes                     | Minutes Sharing              | Depends on Meetings. URL change + enhanced list and detail. |
| 7    | Public Register             | Public Register              | Mostly unchanged. Minor URL confirmation.              |
| 8    | FCC Sued (Defendant)        | FCC Sued                     | Standalone litigation module. Complex but self-contained. |
| 9    | FCC Suing (Plaintiff)       | FCC Suing                    | Mirrors FCC Sued. Transforms last to reuse patterns.   |

---

---

## 2. Menu-by-Menu Transformation Plan

---

### STEP 1: Meetings → Meeting Repository

**Current Menu Name:** Legal Meetings
**Target Menu Name:** Meeting Repository
**Sidebar URL Change:** `/service/grc/legal/meetings` → `/service/grc/legal/meetings` *(URL stays the same)*
**Type of Change:** Rename + UI enhancement

#### Current State (from `legal_current_UI_reference.md`)
- Sidebar title: `Legal Meetings`
- List page: `LegalMeetingsPage.tsx` — basic table with columns: Reference, Title, Governing Body, Mode, Start Date, Status
- No summary KPI cards
- Detail page: `LegalMeetingDetailPage.tsx` — vertical stacked sections (Participants, Agenda, Matters Arising)
- Detail does NOT use tabs

#### Target State (from `refined_menu_structure.md`)
- Sidebar title: `Meeting Repository`
- List page: must add summary KPI cards row (Total Meetings, Draft, Registered, Invitations Sent, Ongoing, Completed)
- Table columns: Meeting No., Title, Governing Body, Type, Start Date, Status, Quorum (percentage + Met/Not Met)
- Detail page: must use **tabbed layout** with 7 tabs: Agenda, Participants, Conflicts, Minutes, Resolutions, Directives, Audit
- Detail: Quorum Status Panel with percentage bar
- Detail: Meeting lifecycle buttons (Initiate Meeting, Reschedule, Cancel) with conditional visibility

#### Transformation Steps

**UI Changes:**
1. Rename sidebar entry title from `Legal Meetings` to `Meeting Repository` in `servicesConfig.ts`
2. Update `LegalMeetingsPage.tsx`:
   - Add summary KPI cards row above the table
   - Add `Quorum` column to table (percentage + Met/Not Met badge)
   - Add `Type` column (Ordinary/Extraordinary/Special)
   - Rename column header `Reference` → `Meeting No.`
3. Update `LegalMeetingDetailPage.tsx`:
   - Convert vertical stacked sections into **7-tab layout** (Agenda, Participants, Conflicts, Minutes, Resolutions, Directives, Audit)
   - Add Quorum Status Panel (percentage bar, threshold indicator)
   - Add conditional lifecycle buttons: `[Initiate Meeting]`, `[Reschedule]`, `[Cancel Meeting]`
   - Agenda tab: add Matters Arising subsection with `[Finally Close]` action
   - Conflicts tab: new section — `[+ Declare Conflict]` with conflict table
   - Minutes tab: minutes list scoped to this meeting
   - Resolutions tab: resolutions auto-created from agenda outcomes
   - Directives tab: `[+ Add Directive]` during ONGOING meeting
   - Audit tab: chronological log of all meeting state changes
4. Update `CreateMeetingDialog`:
   - Change `Title` field to a predefined meeting type selector
   - Add `Meeting Number` as auto-generated read-only field
   - Add `Agenda Summary` field
   - Add `Location / Venue` and `Venue/Meeting Link` fields

**Routing Changes:**
- No URL change needed — stays at `/service/grc/legal/meetings` and `/service/grc/legal/meetings/:id`

**⚠️ SRS Compliance Requirements (must not break during tab restructuring):**
1. **SRS §1.2.1 BR#1** — Invitations MUST be AUTO-SENT when meeting status moves Draft → Registered. This is a backend trigger but must NOT be disabled or bypassed during any UI restructuring of the create/register dialog.
2. **SRS §1.2.1 BR#5** — When a meeting is created, the system MUST auto-populate the Participants tab with all active members of the selected governing body. Verify this auto-populate still fires after the tab conversion.
3. **SRS §1.1 BR#3** — When a Secretary attaches a Submission to the meeting agenda (`[Attach Agenda Item]`), the linked `SubmissionForDetermination` status MUST auto-transition to `UNDER_REVIEW`. This side-effect must be verified to survive the Agenda tab rebuild.
4. **SRS §1.2.1 BR#8** — `[Initiate Meeting]` must remain gated: only enabled when `QuorumMet = true` AND current time is within the scheduled meeting window.
5. **SRS §1.2.4 BR#2** — `[Finally Close]` on Matters Arising directives is ONLY valid in THIS meeting context (Secretary in Matters Arising). This action must NOT appear on the standalone `DirectiveDetailPage.tsx` (see Step 4 for correction).

**Component Reuse or Creation:**
- Reuse: `MeetingParticipantsSection`, `MeetingAgendaSection`, `MattersArisingSection` (already exist) — need to be wrapped into tabs
- Create: `ConflictDeclarationsSection` (new tab content)
- Create: `MeetingResolutionsSection` (scoped resolutions view within meeting)
- Create: `MeetingDirectivesSection` (scoped directives view within meeting)
- Create: `MeetingAuditLogSection` (audit trail view)
- Create: `QuorumStatusPanel` component
- Modify: `CreateMeetingDialog` — add new fields

**API Alignment:**
- Backend must support: quorum calculation endpoint (or embedded in meeting detail response)
- Backend must support: conflict of interest CRUD on agenda items
- Backend must support: meeting audit trail endpoint
- Verify: meeting detail response includes `quorum_percentage`, `quorum_met`, `meeting_number`
- Verify: agenda-attachment endpoint also updates `SubmissionForDetermination.status` → `UNDER_REVIEW` (SRS §1.1 BR#3)

---

### STEP 2: *(New)* Meeting Packs

**Current Menu Name:** *(Does not exist)*
**Target Menu Name:** Meeting Packs
**Sidebar URL:** `/service/grc/legal/circulars`
**Type of Change:** New menu — creation from scratch

**⚠️ SRS Note:** The SRS does not define a `MeetingPack` as a first-class object. This menu is derived from SRS §1.2.3 (MeetingParticipant — invitees have read-only access to agendas/directives) and §1.2.2 (MeetingAgenda Documents). **Backend team must formally define the `MeetingPack` data model and endpoint before this step is implemented.** Do not implement Step 2 until the backend model is confirmed.

#### Current State
- No existing page or route
- No sidebar entry

#### Target State (from `refined_menu_structure.md`)
- New sidebar menu item between Meeting Repository and Resolution Register
- List page: Meeting Packs accessible only to invited participants (Accepted status)
- Columns: Meeting Reference, Title, Governing Body, Date Added, Date, Pack Status
- Detail page: Pack Items list with documents, conflict status per item
- Pack Item Detail: Preview/Download document integration

#### Transformation Steps

**UI Changes:**
1. Add new sidebar entry in `servicesConfig.ts`:
   - Title: `Meeting Packs`
   - URL: `/service/grc/legal/circulars`
   - Icon: appropriate icon (e.g., `Package` or `FolderOpen`)
   - Group: `Legal`
   - Position: after Meeting Repository, before Resolution Register
2. Create `MeetingPacksPage.tsx`:
   - List page with search
   - Table: Meeting Reference, Title, Governing Body, Date Added, Date, Pack Status
   - Access filtered to invited participants with Accepted status only
3. Create `MeetingPackDetailPage.tsx`:
   - Pack header with status
   - Pack Items table: Item #, Agenda Item, Document Title, Category, Version, Upload Date, Conflict Status, Actions
   - `[View More]` per item → Pack Item Detail (inline or modal)
   - Document Preview + Download integration (DMS)

**Routing Changes:**
- Add in App.tsx:
  - `legal/circulars` → `MeetingPacksPage`
  - `legal/circulars/:id` → `MeetingPackDetailPage`

**Component Reuse or Creation:**
- Create: `MeetingPacksPage.tsx` (new)
- Create: `MeetingPackDetailPage.tsx` (new)
- Reuse: existing table/card patterns from other list pages

**API Alignment:**
- Backend must provide: meeting packs list endpoint (filtered by participant acceptance)
- Backend must provide: meeting pack detail with pack items and document links
- Backend must provide: conflict status per agenda item (already exists from meeting conflicts feature)
- Integration: Documents & Records Management service for document preview/download

---

### STEP 3: Resolutions → Resolution Register

**Current Menu Name:** Resolutions
**Target Menu Name:** Resolution Register
**Sidebar URL Change:** `/service/grc/legal/resolutions` → `/service/grc/legal/resolution-register`
**Type of Change:** Rename + URL change + UI enhancement

#### Current State (from `legal_current_UI_reference.md`)
- Sidebar title: `Resolutions`
- URL: `/service/grc/legal/resolutions`
- List page: `ResolutionsPage.tsx` — read-only register, no create button
- Columns: Resolution (text), Status, Date Adopted
- View action opens **inline dialog** (not a separate page)
- Filters: Status, Search

#### Target State (from `refined_menu_structure.md`)
- Sidebar title: `Resolution Register`
- URL: `/service/grc/legal/resolution-register`
- List page: enhanced table with columns: Resolution ID, Meeting No., Governing Body, Agenda Item, Resolution Text (summary), Responsible Person, Date Adopted, Effective Date, Status
- `[Export]` button
- Filters: All Bodies, All Statuses, Search
- View action navigates to **detail page** `/service/grc/legal/resolution-register/:id`
- Detail page shows full resolution fields: Meeting Reference, Governing Body, Agenda Item, Resolution Text, Responsible Person, Effective Date, Date Adopted, Attachments

#### Transformation Steps

**UI Changes:**
1. Rename sidebar entry in `servicesConfig.ts`:
   - Title: `Resolutions` → `Resolution Register`
   - URL: `/service/grc/legal/resolutions` → `/service/grc/legal/resolution-register`
2. Rename or update `ResolutionsPage.tsx`:
   - Add columns: Resolution ID, Meeting No., Governing Body, Agenda Item, Responsible Person, Effective Date
   - Add `[Export]` button
   - Add Governing Body dropdown filter
   - Change `[View]` action from inline dialog to navigation: `/service/grc/legal/resolution-register/:id`
3. Create `ResolutionDetailPage.tsx` (new page):
   - Full detail view: Resolution ID, Status badge, Meeting Reference, Governing Body, Agenda Item, Resolution Text, Responsible Person, Effective Date, Date Adopted, Attachments
4. Update any internal links pointing to `/legal/resolutions` to point to `/legal/resolution-register`
   - Dashboard quick links
   - Meeting detail Resolutions tab links

**Routing Changes:**
- Remove: `legal/resolutions` route
- Add: `legal/resolution-register` → `ResolutionsPage` (or renamed `ResolutionRegisterPage`)
- Add: `legal/resolution-register/:id` → `ResolutionDetailPage`

**Component Reuse or Creation:**
- Modify: `ResolutionsPage.tsx` (add columns, export, filter, navigation)
- Create: `ResolutionDetailPage.tsx` (new)
- Remove: inline resolution detail dialog (replaced by full page)

**⚠️ SRS Compliance — Access Control (SRS §1.2.6 BR#1 + BR#2):**
- SRS states: *"Visible only to meeting invitees"* and *"Resolutions are searchable by invited participants."*
- The Resolution Register list page MUST only show resolutions from meetings where the **current authenticated user was an invited participant** (i.e., exists in `MeetingParticipant` with `InvitationStatus = Accepted` or `Attended`).
- A user who has never been invited to any meeting must see an empty register, not all resolutions.
- This filtering MUST be enforced at the **backend query level** (not just in the frontend).
- The backend list endpoint must accept the current user as a filter parameter and scope results accordingly.

**API Alignment:**
- Backend resolution list endpoint must include: `resolution_id`, `meeting_number`, `governing_body`, `agenda_item`, `responsible_person`, `effective_date`
- Backend resolution list endpoint MUST filter by `current_user_participation` — returns only resolutions from meetings the user was invited to (SRS §1.2.6 BR#1)
- Backend must provide: single resolution detail endpoint (also participant-scoped)
- Verify: resolution list can filter by governing body

---

### STEP 4: Directives → Directives

**Current Menu Name:** Directives
**Target Menu Name:** Directives
**Sidebar URL Change:** `/service/grc/legal/directives` → `/service/grc/legal/meeting-directives`
**Type of Change:** URL change + UI enhancement

#### Current State (from `legal_current_UI_reference.md`)
- Sidebar title: `Directives`
- URL: `/service/grc/legal/directives`
- List page: `DirectivesPage.tsx` — read-only, no create button
- Columns: Reference, Description (80 chars), Meeting, Assigned To, Priority, Status, Due Date
- Detail page: `DirectiveDetailPage.tsx` — Reference, Description, Status, Meeting, Assigned To, Priority, Due Date
- Detail buttons: `[Close Directive]`, `[Fully Close]` ← **⚠️ Current `[Fully Close]` on detail page is an SRS violation (see below)**

#### Target State (from `refined_menu_structure.md`)
- Sidebar title: `Directives`
- URL: `/service/grc/legal/meeting-directives`
- List page: enhanced table with columns: Directive ID, Meeting No., Agenda Item / Source, Description, Category, Priority, Assigned To, Due Date, Status, Finally Closed
- Filters: All Statuses, All Bodies, All Categories, Search
- No Close button on list (closure from detail page only)
- Detail page: enhanced with Category, Governing Body, Finally Closed status, Finally Closed At fields
- Detail actions: **`[Close Directive]` ONLY** (assigned user, when status = Open/In Progress). `[Finally Close]` does NOT appear here.

**⚠️ SRS §1.2.4 BR#2 — CRITICAL:** *"Final closure can only be done by Secretary in a subsequent meeting's Matters Arising."*
- The `[Fully Close]` / `[Finally Close]` button must be **REMOVED** from `DirectiveDetailPage.tsx`.
- This action belongs EXCLUSIVELY inside the Meeting detail page → Agenda tab → Matters Arising subsection (Step 1).
- Keeping it on the directive detail page would allow final closure outside of a meeting context, which violates SRS.

#### Transformation Steps

**UI Changes:**
1. Update sidebar entry in `servicesConfig.ts`:
   - URL: `/service/grc/legal/directives` → `/service/grc/legal/meeting-directives`
2. Update `DirectivesPage.tsx`:
   - Add columns: Directive ID, Agenda Item / Source, Category, Finally Closed
   - Replace `Meeting` column with `Meeting No.`
   - Add filters: All Bodies, All Categories
3. Update `DirectiveDetailPage.tsx`:
   - Add fields: Category, Governing Body, Completion Summary, Completion Date, Evidence Document, Finally Closed, Finally Closed At
   - **REMOVE `[Fully Close]` / `[Finally Close]` button entirely** (SRS §1.2.4 BR#2 — this action belongs only in Meeting Matters Arising)
   - Retain only `[Close Directive]` — visible to the assigned user only, when status = Open or In Progress
   - When `finally_closed = true`, show read-only "Finally Closed" info fields (Finally Closed At, Finally Closed Meeting)
4. Update internal links:
   - Dashboard directive links
   - Meeting detail directive references

**Routing Changes:**
- Change: `legal/directives` → `legal/meeting-directives`
- Change: `legal/directives/:id` → `legal/meeting-directives/:id`

**Component Reuse or Creation:**
- Modify: `DirectivesPage.tsx` (add columns, filters)
- Modify: `DirectiveDetailPage.tsx` (add fields)
- No new components needed

**API Alignment:**
- Backend directive list must include: `directive_id`, `meeting_number`, `agenda_item`, `category`, `finally_closed`
- Backend directive detail must include: `governing_body`, `completion_summary`, `completion_date`, `evidence_document`, `finally_closed_at`, `finally_closed_meeting_id`
- Verify: directive list can filter by governing body and category
- Verify: the Finally Close endpoint is only callable from within the meeting Matters Arising context (not exposed as a standalone directive action)

---

### STEP 5: Submissions → Submission for Determination

**Current Menu Name:** Submissions
**Target Menu Name:** Submission for Determination
**Sidebar URL Change:** `/service/grc/legal/submissions` → `/service/grc/legal/submissions` *(URL stays the same)*
**Type of Change:** Rename + UI enhancement

#### Current State (from `legal_current_UI_reference.md`)
- Sidebar title: `Submissions`
- URL: `/service/grc/legal/submissions`
- List page: `SubmissionsPage.tsx` — any authenticated user can create
- Columns: Title, Target Body, Status, Submitted
- Detail page: `SubmissionDetailPage.tsx` — Title, Reference, Status, edit/withdraw when submitted
- Create dialog: Title, Target Governing Body, Description

#### Target State (from `refined_menu_structure.md`)
- Sidebar title: `Submission for Determination`
- URL: `/service/grc/legal/submissions`
- List page: enhanced with columns: Submission ID, Title, Description (snippet), Submitted By, Governing Body, Submission Date, Status, Meeting Linked
- Actions: `[View]`, `[Edit]` (when Submitted), `[Withdraw]` (when Submitted)
- Detail page: enhanced with Supporting Documents, Linked Meeting, Determination Outcome section
- Create dialog: add Supporting Documents upload, Additional Details field

#### Transformation Steps

**UI Changes:**
1. Rename sidebar entry in `servicesConfig.ts`:
   - Title: `Submissions` → `Submission for Determination`
2. Update `SubmissionsPage.tsx`:
   - Add columns: Submission ID, Description (snippet), Submitted By, Meeting Linked
   - Add `[Withdraw]` action button on list rows (when status = Submitted)
3. Update `SubmissionDetailPage.tsx`:
   - Verify all sections present: Submission Details Card, Description Card, Supporting Documents Card, Determination Outcome Card
   - Determination Outcome Card: show when status = determined → Outcome, Determination Date, Outcome Notes, `[View Determining Meeting]`
4. Update `CreateSubmissionDialog`:
   - Add Supporting Documents upload field (multiple files)
   - Add Additional Details/Context textarea field

**Routing Changes:**
- No URL change needed

**Component Reuse or Creation:**
- Modify: `SubmissionsPage.tsx` (add columns, Withdraw action)
- Modify: `SubmissionDetailPage.tsx` (verify all sections)
- Modify: `CreateSubmissionDialog` (add fields)

**⚠️ SRS §1.1 BR#3 — Cross-Step Dependency:**
When a Secretary attaches a submission to a meeting agenda (done in Step 1, Meeting Repository), the `SubmissionForDetermination.status` must auto-transition to `UNDER_REVIEW`. This is triggered by Step 1, but this step must verify it is working correctly by:
- Checking that a submission with status `under_review` shows the correct locked state in this page (edit/withdraw disabled)
- Checking that `Meeting Linked` column populates correctly when the submission is attached

**API Alignment:**
- Backend submission list must include: `submission_id`, `description`, `submitted_by`, `meeting_linked`
- Backend submission create must accept: `supporting_documents[]`, `additional_context`
- Verify: submission detail includes `determination_outcome`, `determination_date`, `outcome_notes`, `meeting_id`
- Verify: status auto-transitions to `UNDER_REVIEW` when submission is attached to a meeting agenda (SRS §1.1 BR#3)

---

### STEP 6: Minutes → Minutes Sharing

**Current Menu Name:** Minutes
**Target Menu Name:** Minutes Sharing
**Sidebar URL Change:** `/service/grc/legal/minutes` → `/service/grc/legal/minutes` *(URL stays the same)*
**Type of Change:** Rename + UI enhancement

#### Current State (from `legal_current_UI_reference.md`)
- Sidebar title: `Minutes`
- URL: `/service/grc/legal/minutes`
- List page: `MinutesPage.tsx` — read-only (minutes created from Meeting detail)
- Columns: Reference, Title, Meeting, Status, Prepared By, Created
- Detail page: `MinutesDetailPage.tsx` — Reference, Meeting, Status, Prepared By

#### Target State (from `refined_menu_structure.md`)
- Sidebar title: `Minutes Sharing`
- URL: `/service/grc/legal/minutes`
- List page: enhanced with columns: Minutes ID, Title, Meeting No., Created By, Created Date, Attachments, Status, Approved By, Approval Date
- `[+ Draft Minutes]` button (Secretary only, for ONGOING/CLOSED meetings)
- Filters: All Statuses, All Bodies, Search
- Detail page: enhanced with full minutes content display, attachments list, approval workflow display
- `[Submit for Approval]` action with approval method selection and member list

#### Transformation Steps

**UI Changes:**
1. Rename sidebar entry in `servicesConfig.ts`:
   - Title: `Minutes` → `Minutes Sharing`
2. Update `MinutesPage.tsx`:
   - Add `[+ Draft Minutes]` button (Secretary role gate)
   - Add columns: Minutes ID, Attachments count, Approved By, Approval Date
   - Add filter: All Bodies dropdown
   - Add `[Submit for Approval]` action on rows where status = Draft
3. Update `MinutesDetailPage.tsx`:
   - Display full minutes content (rich text)
   - Display attachments list with View/Download links
   - Display Approved By list and Approval Date
   - Add `[Submit for Approval]` dialog with:
     - Approval method selector (Majority Vote / Explicit Sign-off)
     - Auto-populated member list (from meeting participants)
4. Verify `CreateMinutesDialog` fields:
   - Select Meeting (ONGOING/CLOSED only)
   - Title
   - Minutes Content (rich text editor)
   - Attachments (multiple upload)

**Routing Changes:**
- No URL change needed

**Component Reuse or Creation:**
- Modify: `MinutesPage.tsx` (add columns, filters, Draft button)
- Modify: `MinutesDetailPage.tsx` (add content display, approval workflow)
- Create or verify: `SubmitMinutesForApprovalDialog` (approval method + member selection)

**API Alignment:**
- Backend minutes list must include: `minutes_id`, `attachments_count`, `approved_by[]`, `approval_date`
- Backend minutes detail must include: `content` (rich text), `attachments[]`, `approval_method`
- Backend must provide: submit-for-approval endpoint accepting `approval_method` and `member_ids[]`
- Verify: minutes list can filter by governing body

---

### STEP 7: Public Register → Public Register

**Current Menu Name:** Public Register
**Target Menu Name:** Public Register
**Sidebar URL Change:** `/service/grc/legal/public-register` → `/service/grc/legal/public-register` *(no change)*
**Type of Change:** UI enhancement only

#### Current State (from `legal_current_UI_reference.md`)
- Sidebar title: `Public Register`
- URL: `/service/grc/legal/public-register`
- List page: `PublicRegisterPage.tsx` — KPI cards (Total, Draft, Published), create button (Secretariat only)
- Columns: Title, Decision Date, Status, Published Date
- Detail page: `PublicDecisionDetailPage.tsx` — Title, Status, Decision Date, Published Date, Body Text, Decision Text
- Publish/Edit/Delete buttons on draft decisions

#### Target State (from `refined_menu_structure.md`)
- Same URL
- List: add columns: Decision ID, Created By
- Detail: add Meeting link field (`Select Commission Meeting`)
- Create form: `Select Commission Meeting` field (linked meeting)

#### Transformation Steps

**UI Changes:**
1. No sidebar change needed
2. Update `PublicRegisterPage.tsx`:
   - Add column: Decision ID
   - Add column: Created By
3. Update `PublicDecisionDetailPage.tsx`:
   - Add Meeting Reference field (linked meeting, if present)
4. Update `CreatePublicDecisionDialog`:
   - Verify or add: `Select Commission Meeting` field (optional, links to meeting)

**Routing Changes:**
- No changes needed

**Component Reuse or Creation:**
- Modify: `PublicRegisterPage.tsx` (add columns)
- Modify: `PublicDecisionDetailPage.tsx` (add meeting link)
- Modify: `CreatePublicDecisionDialog` (verify meeting field)

**API Alignment:**
- Backend public decision response should include: `decision_id`, `created_by`, `meeting_id`/`meeting_reference`
- Verify: create endpoint accepts `meeting_id` (optional)

---

### STEP 8: FCC Sued (Defendant) → FCC Sued

**Current Menu Name:** FCC Sued (Defendant)
**Target Menu Name:** FCC Sued
**Sidebar URL Change:** `/service/grc/legal/fcc-sued` → `/service/grc/legal/fcc-sued` *(no change)*
**Type of Change:** Rename + UI enhancement (extensive)

#### Current State (from `legal_current_UI_reference.md`)
- Sidebar title: `FCC Sued (Defendant)`
- URL: `/service/grc/legal/fcc-sued`
- List: KPI cards (New, Hearing Stage, Judgment Received, On Hold), Show Archived toggle
- Columns: Case No., Title, Plaintiff, Court, Stage, Filed
- Detail: 9 tabs (Directives, Filings, Responses, Hearings, Settlements, Judgments, Financials, Tasks, Report)
- Register dialog: `CreateCaseDefendantDialog`

#### Target State (from `refined_menu_structure.md`)
- Sidebar title: `FCC Sued`
- List page: dashboard-style KPI row (Total Cases Filed, Active Cases, Cases on Appeal, Pending DG Review, High Risk Cases, Won/Loss Ratio)
- Table columns: Case Ref No, Plaintiff/Applicant, Court, Case Type, Claim Amount, Stage, Status, Risk Level, Next Hearing
- Filters: All Statuses, All Courts, All Risks, Search
- Register form: expanded fields — Plaintiff repeatable (+ Add Another), Co-Defendants field, Department Affected as dropdown, Documents Served upload, Save Draft + Submit to DG buttons
- Detail page: 9 tabs — Filings, Responses, Hearings, Settlement, Financials, Tasks, Judgment, Report, Activity Log
- Detail: DG Review panel (when Under DG Review)
- Detail: Case Closure workflow (Initiate Closure → DG Approval)
- Each tab has specific enhancements per `refined_menu_structure.md`

#### Transformation Steps

**UI Changes:**
1. Rename sidebar entry in `servicesConfig.ts`:
   - Title: `FCC Sued (Defendant)` → `FCC Sued`
2. Update `FCCSuedCasesPage.tsx`:
   - Update KPI cards to match target: Total Cases Filed, Active Cases, Cases on Appeal, Pending DG Review, High Risk Cases, Won/Loss Ratio
   - Update table columns: add Case Type, Claim Amount, Status, Risk Level, Next Hearing
   - Add filters: All Courts, All Risks dropdowns
3. Update `CreateCaseDefendantDialog`:
   - Make Plaintiffs repeatable (`[+ Add Another Plaintiff]`)
   - Add Co-Defendants/Collaborators field (repeatable)
   - Make Department Affected a dropdown (select from departments)
   - Add Documents Served upload (multiple files)
   - Add dual buttons: `[Save Draft]` and `[Submit to DG]`
4. Update `FCCSuedCaseDetailPage.tsx`:
   - Add DG Review panel (visible when stage = Under DG Review):
     - `[Issue Directive]` and `[Mark as Reviewed]` (DG only)
   - Reorder/rename tabs to match: Filings, Responses, Hearings, Settlement, Financials, Tasks, Judgment, Report, Activity Log
   - Add Case Closure section: `[Initiate Closure]` → Closure Summary → Submit to DG
   - Filings tab: show approval chain status badges per filing
   - Hearings tab: add `[+ Add Report]` per hearing with report type selection
   - Settlement tab: DG approval workflow display
   - Judgment tab: DG Decision panel (Accept/Appeal), auto-creation of Notice of Appeal filing
   - Financials tab: conditional Record Payment / Record Recovery based on judgment outcome
   - Report tab: chronological timeline of all case events
   - Activity Log tab: full audit log table
5. Update internal links:
   - Dashboard FCC Sued KPI links

**Routing Changes:**
- No URL changes needed

**Component Reuse or Creation:**
- Modify: `FCCSuedCasesPage.tsx` (KPIs, columns, filters)
- Modify: `FCCSuedCaseDetailPage.tsx` (DG Review panel, closure workflow, tab enhancements)
- Modify: `CreateCaseDefendantDialog` (repeatable plaintiffs, departments, documents)
- Modify: All case section components (`CaseDirectivesSection`, `CaseFilingsSection`, etc.) — these are shared between Sued/Suing
- Create (if not existing): `DGReviewPanel`, `CaseClosureDialog`, `DGDirectiveDecisionDialog`

**API Alignment:**
- Backend case list must include: `case_type`, `claim_amount`, `status`, `risk_level`, `next_hearing_date`
- Backend must provide: DG review endpoints (issue directive, mark reviewed)
- Backend must provide: case closure workflow endpoints (initiate, DG approve)
- Backend must provide: filing approval chain status
- Backend judgment endpoint must support: DG decision (accept/appeal) with auto-creation of appeal filing
- Backend must provide: case activity log / timeline endpoint
- Verify: dashboard KPI endpoint provides all 6 required metrics

---

### STEP 9: FCC Suing (Plaintiff) → FCC Suing

**Current Menu Name:** FCC Suing (Plaintiff)
**Target Menu Name:** FCC Suing
**Sidebar URL Change:** `/service/grc/legal/fcc-suing` → `/service/grc/legal/fcc-suing` *(no change)*
**Type of Change:** Rename + UI enhancement (mirrors FCC Sued + plaintiff-specific differences)

#### Current State (from `legal_current_UI_reference.md`)
- Sidebar title: `FCC Suing (Plaintiff)`
- URL: `/service/grc/legal/fcc-suing`
- List: Two create paths (Raise Breach Report, Register Full Case), 6 KPI cards, My Cases toggle
- Columns: Case Ref, Respondent, Court, Claim Amount, Stage, Risk, Type, Next Hearing
- Detail: same 9 tabs as FCC Sued with `caseType="plaintiff"`

#### Target State (from `refined_menu_structure.md`)
- Sidebar title: `FCC Suing`
- KPI cards: Total Cases Filed, Active Cases, Cases on Appeal, Pending DG Review, High Risk Cases, Won/Loss Ratio, Total Recoverable, Recovered Amount
- Two entry points maintained: `[+ Report Breach]` (simplified) and `[+ Register Full Breach Report]` (full)
- Filters: All Stages, All Types, All Risks, Search
- Detail: identical to FCC Sued but with plaintiff-specific filing types, response types, and financials
- Financials: Recovered Amount card, Record Recovery button

#### Transformation Steps

**UI Changes:**
1. Rename sidebar entry in `servicesConfig.ts`:
   - Title: `FCC Suing (Plaintiff)` → `FCC Suing`
2. Update `FCCSuingCasesPage.tsx`:
   - Update KPI cards to add: Total Recoverable, Recovered Amount (in addition to existing 6)
   - Verify all filter dropdowns present
3. Update `BreachReportIntakeDialog`:
   - Verify fields match target: Reporting Department, Nature of Breach, Respondent Name, Respondent Type, Estimated Claim Amount (optional), Description, Urgency Level
   - Add Supporting Documents upload (optional)
   - Add dual buttons: `[Save Draft]` and `[Submit to DG]`
4. Update `CreateCasePlaintiffDialog`:
   - Add Initiation Documents upload (multiple, each with Title and Type)
   - Add Risk Level field
   - Add dual buttons: `[Save Draft]` and `[Submit to DG]`
5. Update `FCCSuingCaseDetailPage.tsx`:
   - Same enhancements as FCC Sued (DG Review panel, closure workflow)
   - Financials tab: add Recovered Amount card and updated button logic
   - Filing types: Plaint, Petition, Statement of Claim, etc. (plaintiff-specific)
   - Response types: plaintiff-specific types
6. Update internal links:
   - Dashboard FCC Suing KPI links

**Routing Changes:**
- No URL changes needed

**Component Reuse or Creation:**
- Modify: `FCCSuingCasesPage.tsx` (KPIs)
- Modify: `BreachReportIntakeDialog` and `CreateCasePlaintiffDialog` (field additions)
- Modify: `FCCSuingCaseDetailPage.tsx` (DG Review panel, closure, financials)
- Reuse: shared case section components (already receive `caseType` prop)
- All new components created in Step 8 (DG Review, Closure, etc.) are reused here automatically

**API Alignment:**
- Backend plaintiff case list must include: `total_recoverable`, `recovered_amount` for KPI cards
- Backend breach report intake must accept: `supporting_documents[]`
- Backend full registration must accept: `initiation_documents[]` (with Title and Type per file)
- Verify: all shared case endpoints work with `caseType="plaintiff"` parameter

---

---

## 3. Dependency & Risk Analysis

### 3.1 Dependency Map

```
Meeting Repository (Step 1)
├── Meeting Packs (Step 2) — depends on meetings existing; also needs backend MeetingPack model defined first
├── Resolution Register (Step 3) — resolutions created from meeting outcomes; access MUST be scoped to invited participants
├── Directives (Step 4) — directives created during meetings; [Finally Close] belongs only here in Matters Arising
├── Minutes Sharing (Step 6) — minutes created for meetings
└── Submission for Determination (Step 5)
        └── [Attach Agenda Item] in Step 1 triggers auto-status change in Step 5 (SUBMITTED → UNDER_REVIEW)

FCC Sued (Step 8) — standalone, no dependency on governance menus
└── FCC Suing (Step 9) — shares components with FCC Sued

Public Register (Step 7) — standalone, optionally linked to meetings
```

### 3.2 Risk Matrix

| Step | Risk Level | Risk Description | Impact if Broken |
|------|------------|------------------|------------------|
| 1 - Meeting Repository | **HIGH** | Core hub — Resolutions, Directives, Minutes all depend on meeting detail tabs working correctly. Auto-invite and auto-member-populate triggers must survive restructuring. | Cascading failures in Steps 2-6; auto-invitation broken |
| 2 - Meeting Packs | **HIGH** | New feature with NO SRS object defined. Backend data model needs to be defined first. Access control must filter by participant acceptance status. | Page shows data to wrong users; no backend; blocks Step 2 entirely |
| 3 - Resolution Register | **HIGH** | SRS requires resolutions visible ONLY to meeting invitees. If access control is not enforced at backend, ALL users will see ALL resolutions — SRS violation. | Data breach of governance decisions |
| 4 - Directives | **HIGH** | [Fully Close] exists on current detail page and MUST be removed. If left, it violates SRS §1.2.4 BR#2 — final closure can only happen in Meeting Matters Arising. | Secretary can bypass meeting context for final closure |
| 5 - Submissions | **LOW** | No URL change, title rename + column additions only. Must verify UNDER_REVIEW auto-transition still works from Step 1. | Minimal risk |
| 6 - Minutes Sharing | **LOW** | No URL change, enhancement only | Minimal risk |
| 7 - Public Register | **LOW** | No changes to URL or core functionality | Minimal risk |
| 8 - FCC Sued | **HIGH** | Extensive UI changes to complex multi-tab detail page. DG Review workflow is mission-critical | Litigation workflow disruption |
| 9 - FCC Suing | **MEDIUM** | Mirrors FCC Sued — share components. If Step 8 is stable, risk is lower | Breached by Step 8 bugs |

### 3.3 Mitigation Strategy

1. **Meeting Repository (Step 1)**: Transform list page first, then detail page tab-by-tab. Verify each tab independently before moving to next. Explicitly test: auto-invite trigger, auto-member-populate, and agenda-attachment UNDER_REVIEW side-effect after restructuring.
2. **Meeting Packs (Step 2)**: Do NOT begin implementation until backend team has defined and deployed the `MeetingPack` endpoint. This is a hard prerequisite.
3. **URL Changes (Steps 3-4)**: Implement redirect from old URL to new URL temporarily. Update all internal `navigate()` and `<Link>` references before removing old routes.
4. **Resolution Register (Step 3)**: Before going live, confirm with backend that the list endpoint is scoped to the current user's meeting participation. Add an integration test to verify a non-participant user cannot access resolutions.
5. **Directives (Step 4)**: Remove `[Fully Close]` from `DirectiveDetailPage.tsx` as part of this step. Do not ship this step with that button still present.
6. **FCC Sued (Step 8)**: Transform one tab at a time. Keep existing tab structure working while enhancing. Add new features (DG Review panel, Closure) as additive changes, not replacements.
7. **Cross-menu links**: Maintain a checklist of all cross-page navigation paths. Verify each after every transformation step.

---

---

## 4. Backend Alignment Check

### 4.1 Existing Backend Support (Verified from SRS)

| Target Menu | Backend Status | Notes |
|---|---|---|
| Meeting Repository | **Partially supported** | Meeting CRUD exists. Need to verify: quorum calculation, conflict of interest CRUD, audit trail, meeting lifecycle transitions |
| Meeting Packs | **Needs verification** | SRS mentions packs implicitly via meeting agenda + documents. May need a dedicated endpoint or computed view |
| Resolution Register | **Supported** | Resolutions are auto-created from agenda outcomes (SRS §1.2.6). Need: list endpoint with expanded fields |
| Directives | **Supported** | Directive CRUD exists (SRS §1.2.4). Need: category field, finally_closed tracking, governing body filter |
| Submission for Determination | **Supported** | Full CRUD exists (SRS §1.1). Need: supporting_documents upload, determination outcome fields |
| Minutes Sharing | **Supported** | Minutes CRUD exists (SRS §1.2.5). Need: approval workflow endpoints, content display |
| Public Register | **Supported** | Full CRUD exists (SRS §3.1). Need: meeting link field |
| FCC Sued | **Supported** | Comprehensive endpoints (SRS §4). Need: DG review endpoints, case closure workflow, activity log, filing approval chain |
| FCC Suing | **Supported** | Mirrors defendant module (SRS §5). Need: breach report intake, same enhancements as FCC Sued |

### 4.2 Backend Gaps Requiring Attention

| Gap | Target Menu(s) | Priority | SRS Reference | Description |
|-----|:---:|---|---|---|
| **MeetingPack data model undefined** | Meeting Packs | **CRITICAL** | No SRS object | Backend must define `MeetingPack` model/endpoint before Step 2 can begin. Blocks entire Step 2. |
| **Resolution access control** | Resolution Register | **CRITICAL** | §1.2.6 BR#1-2 | Resolution list endpoint MUST scope results to meetings the current user was invited to. Without this, all resolutions are exposed to all users. |
| **Finally Close endpoint context** | Directives | **CRITICAL** | §1.2.4 BR#2 | The Finally Close API action must be callable ONLY from within a meeting Matters Arising context (i.e., requires a `meeting_id` parameter). Calling it standalone must be rejected. |
| Quorum calculation endpoint | Meeting Repository | HIGH | §6.7 | Must return `quorum_percentage` and `quorum_met` in meeting detail response |
| Submission auto-status on agenda attach | Meeting Repository, Submissions | HIGH | §1.1 BR#3 | When agenda item attached, `SubmissionForDetermination.status` → `UNDER_REVIEW` must be atomic |
| Auto-populate members on meeting create | Meeting Repository | HIGH | §1.2.1 BR#5 | On meeting creation, active members of the governing body must auto-insert into `MeetingParticipant` |
| Auto-invite on Draft → Registered | Meeting Repository | HIGH | §1.2.1 BR#1 | Invitation notifications sent automatically on status transition |
| Conflict of interest CRUD | Meeting Repository | HIGH | §1.2.1 BR#7 | CRUD on agenda item conflicts, exclude member from vote/determination |
| Meeting audit trail | Meeting Repository | MEDIUM | §1.2.7 | Chronological log of all meeting state changes and actions |
| Resolution expanded fields | Resolution Register | MEDIUM | §1.2.6 | `resolution_id`, `meeting_number`, `governing_body`, `responsible_person`, `effective_date` in list endpoint |
| Directive category field | Directives | MEDIUM | §1.2.4 | Category enum (Legal/Compliance/Operational/Financial/Governance/Administrative/Risk) |
| DG Review endpoints | FCC Sued, FCC Suing | HIGH | §4.2 | Issue directive during case review, mark as reviewed without directive |
| Case closure workflow | FCC Sued, FCC Suing | HIGH | §4.14 | Initiate closure (LM) → DG approval → read-only state |
| Case activity log | FCC Sued, FCC Suing | MEDIUM | §4.12 | Chronological timeline of all case events |
| Filing approval chain display | FCC Sued, FCC Suing | MEDIUM | §4.3 | Full chain status (LM review → DG review → Filed) in list response |
| Appeal auto-creation | FCC Sued, FCC Suing | HIGH | §4.8 | When DG decides Appeal: auto-create Filing + Task |
| Plaintiff KPIs | FCC Suing | MEDIUM | §5.0 | Total Recoverable, Recovered Amount aggregation |

---

---

## 5. Execution Order

### Phase 1 — Governance Engine (Steps 1-2)

```
Step 1: Meeting Repository
  1.1  Rename sidebar entry
  1.2  Update list page (KPI cards, columns)
  1.3  Update detail page (convert to tabs)
  1.4  Update create dialog (new fields)
  1.5  Verify backend alignment
  1.6  Validate

Step 2: Meeting Packs
  2.1  Add sidebar entry
  2.2  Create list page
  2.3  Create detail page
  2.4  Add routes
  2.5  Verify backend alignment
  2.6  Validate
```

### Phase 2 — Meeting Outputs (Steps 3-6)

```
Step 3: Resolution Register
  3.1  Rename sidebar entry + URL change
  3.2  Update list page (columns, export, navigation)
  3.3  Create detail page
  3.4  Update routes (add new, keep old as redirect)
  3.5  Update internal links
  3.6  Validate

Step 4: Directives
  4.1  Update sidebar URL
  4.2  Update list page (columns, filters)
  4.3  Update detail page (fields)
  4.4  Update routes (add new, keep old as redirect)
  4.5  Update internal links
  4.6  Validate

Step 5: Submission for Determination
  5.1  Rename sidebar entry
  5.2  Update list page (columns, withdraw action)
  5.3  Update detail page (verify sections)
  5.4  Update create dialog (documents, context)
  5.5  Validate

Step 6: Minutes Sharing
  6.1  Rename sidebar entry
  6.2  Update list page (columns, draft button, filters)
  6.3  Update detail page (content, approval)
  6.4  Create/verify approval dialog
  6.5  Validate
```

### Phase 3 — Standalone Menus (Steps 7-9)

```
Step 7: Public Register
  7.1  Update list page (add columns)
  7.2  Update detail page (meeting link)
  7.3  Update create dialog (meeting field)
  7.4  Validate

Step 8: FCC Sued
  8.1   Rename sidebar entry
  8.2   Update list page (KPIs, columns, filters)
  8.3   Update register dialog (repeatable plaintiffs, departments, documents)
  8.4   Add DG Review panel to detail page
  8.5   Enhance Filings tab (approval chain badges)
  8.6   Enhance Hearings tab (add report workflow)
  8.7   Enhance Settlement tab (DG approval workflow)
  8.8   Enhance Judgment tab (DG decision, auto-appeal)
  8.9   Enhance Financials tab (conditional buttons)
  8.10  Enhance Report tab (chronological timeline)
  8.11  Add Activity Log tab
  8.12  Add Case Closure workflow
  8.13  Validate all tabs

Step 9: FCC Suing
  9.1  Rename sidebar entry
  9.2  Update list page (additional KPIs)
  9.3  Update breach report dialog (documents)
  9.4  Update full registration dialog (initiation documents, risk)
  9.5  Apply same detail enhancements as Step 8 (shared components)
  9.6  Verify plaintiff-specific differences (filing types, financials)
  9.7  Validate
```

---

---

## 6. Validation Strategy

### 6.1 Per-Step Validation Checklist

After each transformation step, verify:

| Check | How |
|-------|-----|
| **Sidebar renders correctly** | Visual check — correct title, icon, URL, position |
| **Route resolves** | Navigate to URL directly — page loads without 404 |
| **List page loads data** | Table populates from API — correct columns, filters work |
| **Detail page loads** | Click View → detail page renders all fields |
| **Create/Edit works** | Fill form → submit → new record appears in list |
| **TypeScript compiles** | `npx tsc --noEmit` → 0 errors |
| **Cross-links work** | All navigation from other pages to this page resolve correctly |
| **Old URLs redirect** | (For URL changes) Old URL redirects to new URL |
| **Permissions enforced** | Buttons/actions hidden for users without correct permission codes |

### 6.2 API Verification

For each step, confirm:
1. List endpoint returns all required columns
2. Detail endpoint returns all required fields
3. Create/Update endpoints accept all new fields
4. Filter parameters work correctly
5. Error responses are handled gracefully in UI

### 6.3 Regression Checks

After Steps 1-2 (Meeting Repository + Packs):
- Verify Dashboard KPI links still navigate correctly
- Verify Governing Bodies detail → meeting references still work

After Steps 3-6 (Meeting Outputs):
- Verify Meeting detail tabs all render correctly (Resolutions, Directives, Minutes content)
- Verify old URLs for Resolutions and Directives redirect properly

After Steps 8-9 (Litigation):
- Full end-to-end case lifecycle test: Register → DG Review → Hearing → Judgment → Closure
- Verify both Sued and Suing share components correctly without cross-contamination

### 6.4 Final Validation

After all 9 steps complete:

1. **Sidebar audit**: Every menu item matches the refined menu structure exactly:
   ```
   Dashboard
   Governing Bodies (Types / Bodies / Members)
   Meeting Repository
   Meeting Packs
   Resolution Register
   Directives
   Submission for Determination
   Minutes Sharing
   Public Register
   FCC Sued
   FCC Suing
   ```

2. **URL audit**: Every route matches target URL in `refined_menu_structure.md`

3. **SRS coverage**: Every SRS object and workflow has a corresponding UI path

4. **Permission audit**: Every action button is gated by the correct permission code

5. **TypeScript clean**: `npx tsc --noEmit` → 0 errors across all projects

---

*End of Legal Menu Transformation Plan*
