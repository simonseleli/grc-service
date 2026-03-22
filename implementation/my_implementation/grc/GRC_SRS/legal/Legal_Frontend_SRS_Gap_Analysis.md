# Legal Module Frontend — SRS Gap Analysis Report

**Reference SRS:** `Legal_Service.md`  
**Reference Plan:** `Legal_Module_Frontend_Implementation_Plan.md`  
**Analysis Date:** 2026-03-21  
**Purpose:** Identify every gap between the SRS requirements and the frontend implementation plan to ensure 100% SRS coverage.

---

## Summary

| Severity | Count |
|---|---|
| 🔴 CRITICAL — Missing or incorrect, breaks SRS compliance | 5 |
| 🟠 SIGNIFICANT — Important SRS feature absent or substantially incomplete | 11 |
| 🟡 MINOR — Discrepancy, clarification, or edge case not fully addressed | 18 |
| ⚫ PLAN OVER-SCOPE — Plan contains features NOT in SRS | 1 |
| **Total** | **35** |

> **Re-verification pass (2026-03-21):** Items CRIT-05, SIG-10–SIG-11, and MIN-14–MIN-18 were added after a second full read of both source documents against the initial 27-item analysis.

---

## 🔴 CRITICAL GAPS

### CRIT-01 — Submission Creation Permission Incorrectly Gated

**SRS Reference:** §1.1 Business Rule 1  
> "Any authenticated user (Department User, Legal Officer, or any staff member) can create a Submission for Determination."

**Current Plan Behavior (Phase 10, §7.2 Phase 7 Page Inventory):**  
`SubmissionsPage` create button is gated on `canManageGoverningBody`, and Phase 10.6 RBAC matrix lists `canManageGoverningBody` as the required permission for creating submissions. This restricts submission creation to Secretariat/Secretary role only.

**Required Fix:**  
- The SRS grants submission creation to **all authenticated staff**—not just Secretariat.
- No dedicated `grc:legal_submission:manage` permission code exists in the 28 permission codes from `grc-service.json` (see Phase 5.1 / A.16.2). A new permission code is required, or a broad base-access code must be applied.
- **Proposed permission code:** `grc:legal_submission:create` (to be confirmed with backend)
- Alternatively: if the backend enforces the "any staff" rule at the API level, the frontend should show the "Create Submission" button to **all authenticated users** without a permission gate.
- The **Withdraw** CTA remains gated on submitter identity only (not RBAC) — this is correct per SRS §1.1 rule 2.
- The permission matrix in Phase 10.6 must be corrected for `SubmissionsPage`.

**Impact:** Incorrect RBAC prevents Department Users and standard staff from creating submissions, violating the core business rule.

---

### CRIT-02 — Registry Officer Role Not Mapped to Any Permission Code

**SRS Reference:** §4.1 Business Rule 1 (FCC Sued Registration)
> "Case registration can be performed by a Registry Officer, Legal Officer, or Legal Manager."

**SRS Reference:** §5.1 (FCC Suing Registration)  
> Same roles implied; breach report intake also available to Department Users.

**Current Plan Behavior:**  
The plan defines 28 permission codes (Phase 5.1 / A.16.2) with roles: `legal_officer`, `legal_manager`, Secretary, Meeting Member. There is **no Registry Officer role** defined anywhere in the permission system. Case registration (`canManageCases`) is mapped to Legal Officer + Legal Manager only.

**Required Fix:**  
- The SRS defines Registry Officer as a distinct role that can register cases but likely does not have full case management capability.
- Confirm with backend whether `grc:legal_case:manage` already covers the Registry Officer role, or whether a separate permission code `grc:legal_case:register` is required.
- Add a `Registry Officer` role entry to the role-permission table in Phase 5.1 and Phase A.8.2.
- The `BreachReportIntakeDialog` (Department User) and full case registration dialogs must clearly reflect which role is granted access.

**Impact:** The Registry Officer role is a SRS-defined stakeholder. If they cannot register cases due to missing permission mapping, a core workflow is broken.

---

### CRIT-03 — `CASE_STAGES` Enum Mismatch and Incorrect Stage Badge Colors

**SRS Reference:** §4.1 Stage attribute  
> Stage values: `New / Under DG Review / Directive Issued / Hearing Stage / Judgment Received / Appeal Filed / Closed / On Hold`

**Current Plan Behavior (Phase 8.2 badge color table):**  
The stage badge color table in `FCCSuedCaseDetailPage` and `FCCSuingCaseDetailPage` includes the following values that do **NOT** exist in the SRS case stage enum:

| Badge in Plan | SRS Status |
|---|---|
| `settlement` | ❌ NOT a stage in SRS (Settlement is a child entity, not a case stage) |
| `judgment` | ❌ NOT a stage in SRS (use `judgment_received`) |
| `appealed` | ❌ NOT a stage in SRS (correct value is `appeal_filed`) |
| `closure_pending` | ❓ NOT listed in SRS stages (may be a backend-side transition state) |

**Required Fix:**  
1. Remove `settlement` and `judgment` from the badge color table — these are not case stages.
2. Rename `appealed` → `appeal_filed` to match SRS enum.
3. Clarify `closure_pending` with the backend — if it is a backend stage (used during case closure workflow), add it to `CASE_STAGES` in Phase 2.2 and document it; if not, remove it from badge colors.
4. Verify the plan's `CASE_STAGES` const map in Phase 2.2 exactly matches the SRS stage values: `new, under_dg_review, directive_issued, hearing_stage, judgment_received, appeal_filed, closed, on_hold`.

**Impact:** Incorrect stage enum causes badge rendering errors and potential broken stage-gated CTA logic.

---

### CRIT-04 — No `closure_pending` Stage in CASE_STAGES While Used in Badge Colors

**SRS Reference:** §4.14 Case Closure  
> "Legal Manager initiates; DG approves. After approval, case becomes read-only."

**Current Plan Behavior:**  
Phase 2.2 `CASE_STAGES` does not include `closure_pending`, but the Phase 8.2 badge color table defines a color for it. If the backend adds this intermediate stage during the closure workflow, the frontend type system is incomplete.

**Required Fix:**  
- Confirm with backend whether `closure_pending` is a backend stage or just an internal workflow state not surfaced in `case.stage`.
- If it IS surfaced: add `closure_pending` to `CASE_STAGES` enum in Phase 2.2.
- If it is NOT surfaced: remove it from the badge color table.
- In either case, document the exact case stage lifecycle including closure states.

---

### CRIT-05 — Breach Report Intake Permission Gate Incorrect

**SRS Reference:** §5.1 Registration Interfaces  
> "Breach Report Intake (simplified): Initiated by a **Department User**."

**Current Plan Behavior (Phase 10.6 FCCSuingCasesPage):**  
```
FCCSuingCasesPage | canViewCases, canManageCases | canManageCases | … | Breach Report: canManageCases
```
The "Raise Breach Report" button is gated on `canManageCases` (`grc:legal_case:manage`). Department Users are not granted `canManageCases` — that permission belongs to Legal Officers, Registry Officers, and Legal Managers. Department Users would therefore see no way to raise a breach report, violating the SRS requirement.

**Required Fix:**  
- This is the direct parallel of CRIT-01 (Submission creation by any staff) but applies to `CasePlaintiff` breach report intake.
- None of the 28 canonical permission codes covers "Department User initiates breach report." A new permission code is needed — e.g., `grc:legal_case:intake` — or the breach report button should be accessible to any authenticated user (enforced server-side).
- **Proposed approach:** Show "Raise Breach Report" button to all authenticated users (no explicit permission code gate), same pattern as the CRIT-01 fix for Submissions. Backend enforces who can actually submit via API authorization.
- The existing "Create Case" (full registration) button correctly remains gated on `canManageCases`.
- Update Phase 10.6 `FCCSuingCasesPage` row: `Breach Report: any authenticated user (no explicit RBAC gate — see CRIT-01 pattern)`

**Impact:** Department Users are completely blocked from initiating breach reports from the frontend, preventing a core FCC Suing intake workflow.

---

## 🟠 SIGNIFICANT GAPS

### SIG-01 — Case Archiving: Service Functions Exist, UI Completely Missing

**SRS Reference:** §4.15, §5.8  
> "Configurable automatic or manual archiving after closure period."

**Current Plan Behavior:**  
Phase 3.2 defines `archiveCase(caseType, id)` and `unarchiveCase(caseType, id)` service functions. However, there is **no corresponding UI** anywhere in the plan:
- No "Archive" / "Unarchive" button in `FCCSuedCaseDetailPage` or `FCCSuingCaseDetailPage`
- No CTA listed in Phase 8.2 for archiving
- No "Archived Cases" list view or filter
- No stage/permission guard for the archive action
- No RBAC matrix entry for who can archive

**Required Fix:**  
Add to `FCCSuedCaseDetailPage` and `FCCSuingCaseDetailPage`:
- "Archive" button — visible when `stage === 'closed'`, gated on `canCloseCases` (Legal Manager)
- "Unarchive" button — for already-archived cases with appropriate role guard
- An `is_archived: boolean` field to the `CaseDefendant` and `CasePlaintiff` TypeScript types
- A filter option on `FCCSuedCasesPage` and `FCCSuingCasesPage` to show/hide archived cases (default: exclude archived)
- Add to Phase 10.6 RBAC matrix: archive/unarchive gated on `canCloseCases`
- Add to Phase 15 test checklist: archive/unarchive verification

---

### SIG-02 — Meeting Invitee Access to Directives (Standalone DirectivesPage)

**SRS Reference:** §1.2.4 Business Rule 4  
> "All meeting invitees can view directives in read-only mode."

**Current Plan Behavior:**  
The plan covers that invitees can view agendas and directives within the `LegalMeetingDetailPage` (A.17.2, §8.2 meeting participants). However, the standalone `DirectivesPage` is gated on `canViewDirectives → grc:legal_directive:view`.

Internal staff who are invited to a meeting as invitees may **not** have the `grc:legal_directive:view` permission if they are not Legal team members (e.g., Department Users invited to a Committee meeting). The SRS says they are entitled to read-only directive access.

**Required Fix:**  
- The `DirectivesPage` and `DirectiveDetailPage` should be accessible to:
  a. Users with `grc:legal_directive:view` permission (standard access), AND
  b. Users who are meeting invitees (data-level access via backend enforcement)
- The backend API should return only directives the user is entitled to see (enforcement is backend-side per §6.6).
- Frontend must handle the scenario where `DirectivesPage` shows a **limited** list for invitee-role users (filtered by backend) without displaying a permission-denied error.
- Add a note to Phase 10 documenting this dual-access pattern for directives.
- On `DirectivesPage`, if the user's list is empty because they only see meeting-scoped directives, the empty state message should be participant-aware: "No directives assigned or accessible to you."

---

### SIG-03 — Litigation Directive Closure: Configurable DG Approval Not Reflected

**SRS Reference:** §4.2 Business Rule 3  
> "Legal Officer/Manager can update status; closure may require DG approval (configurable)."

**Current Plan Behavior:**  
The plan has `CaseDirectivesSection` with a status update path, but the directive closure UI is not fully specified for the litigation directive (as opposed to meeting directives). The `updateLitigationTask` and `closeLitigationTask` service functions cover tasks, and there is `updateDirectiveStatus` for meeting directives. However, the "configurable DG approval" for litigation directive closure is not addressed anywhere in the plan.

**Required Fix:**  
- Add a `requires_dg_approval_for_closure: boolean` field to `LitigationDirective` TypeScript type (or derive it from a system config).
- In `CaseDirectivesSection`, when a user tries to close a litigation directive:
  - If `requires_dg_approval_for_closure === false`: Legal Officer/Manager can directly close it (existing flow).
  - If `requires_dg_approval_for_closure === true`: closing the directive creates a "closure request" that the DG must approve via workflow.
- Add a note in Phase 9.2 `CaseDirectivesSection` about this conditional behavior.
- Add `LITIGATION_DIRECTIVE_STATUSES = ['open', 'in_progress', 'closed']` to Phase 2.2 (already in A.17.8 but not linked to the configurable closure UI).

---

### SIG-04 — In-App Notification Center Not Addressed

**SRS Reference:** §6.4 Notifications Engine  
> "Events trigger notifications (email/in-app) to relevant users based on role and assignment. Examples: new case registered (to DG), filing ready for review (to Legal Manager), filing approved (to Legal Officer), task reminders, appeal due date."

**Current Plan Behavior:**  
The plan covers **toast notifications** for the current user's own actions (Phase 11). However, SRS §6.4 describes a notifications engine that pushes notifications **to specific roles and assignees** — DG notified when a new case is registered, Legal Manager notified when a filing is ready for review, etc. These are received-notification patterns, not action-toast patterns.

There is no plan for:
- A notification inbox / notification bell in the UI header
- Showing unread notification count
- A "Notifications" page or panel listing received notifications
- In-app notification delivery from Work Orchestration Service

**Required Fix:**  
- If in-app notifications (notification bell/inbox) are handled by the platform's shared notification component (already built for other modules), add a note that the Legal module must hook into the same notification subscription system.
- If not yet built, add this as a Phase 2 feature with explicit requirements:
  - Subscribe to notification events for Legal module entities
  - DG receives in-app notification when case is registered
  - Legal Manager receives in-app notification when filing is submitted for LM review
  - Legal Officer receives in-app notification when filing is approved by LM or DG
  - All relevant users receive task reminder notifications (7/2/1 day before due date)
- Document whether this is a **separate task** from the current implementation plan scope.

**Note:** Task reminder scheduling (SRS §4.10 — "Reminders at 7, 2, 1 day before due date; overdue notification") is handled by backend Celery Beat (A.9.1). The in-app display of those reminders still requires a notification delivery mechanism in the frontend.

---

### SIG-05 — Data-Level Access Control (Assigned-To Case Filtering) Not Documented

**SRS Reference:** §6.6 RBAC  
> "System must enforce that users can only access cases/meetings they are assigned to or have explicit permission for."

**Current Plan Behavior:**  
The plan's RBAC coverage (Phase 10) focuses on permission-code-based access (role-level) but does not address **data-level access control** — specifically, a Legal Officer should only see cases where `assigned_legal_officer_ids` includes their user ID.

There is no mention in the plan of:
- How a Legal Officer's case list is filtered to show only their assigned cases
- What happens when a user with `canViewCases` navigates to a case detail for a case they are NOT assigned to
- Whether the API enforces row-level filtering by assignment

**Required Fix:**  
- Document in Phase 3 (API Integration) that the backend case list endpoint (`GET legal/cases/defendant/` and `GET legal/cases/plaintiff/`) applies row-level filtering based on the requesting user's assignment.
- Confirm: Legal Officers see only their assigned cases; Legal Managers see all cases they manage; DG sees all cases pending review; Admins see all cases.
- In the frontend, this is primarily backend-enforced, but add a note to Phase 15 test checklist:
  - [ ] Legal Officer sees only their assigned cases in the list (not all cases)
  - [ ] Navigating to an unassigned case detail returns a 403/404, and the detail page error state handles this gracefully
- Add to Phase 12.3 error state documentation: a 403 on a case detail page means "you are not assigned to this case" — show a user-friendly message: "You are not an assigned officer on this case."

---

### SIG-06 — Response Types for FCC Sued (Defendant) Are Incomplete

**SRS Reference:** §4.4 ResponseDefendant  
> "Types: Preliminary Objections / Response to Ruling / Counter Claim / etc."

**Current Plan Behavior (Phase 6, useLegalConfig):**  
Response types for defendant are listed as only: `"Preliminary Objections, Counter Claims"`.

The SRS mentions "Response to Ruling" and implies more types with "/etc." The FCC Suing response types include more variants ("Response to Ruling, Response to Orders, Response to Affidavits, Initial Response") but the defendant side is cut short.

**Required Fix:**  
Expand defendant response types in Phase 6 (`useResponseTypes`) to at least match the broader set:
```
Response types (defendant):
- Preliminary Objections
- Response to Ruling
- Counter Claim
- Response to Orders
- Response to Affidavits
- Initial Response
- [Others as confirmed with Legal team/backend]
```
The `/etc.` in the SRS should prompt a confirmation with the Legal team or backend-configured system for the full list. Document in Phase 6 that response types may be backend-configurable and should be fetched dynamically or confirmed against the backend's `ResponseType` lookup if one exists.

---

### SIG-07 — Recovered Amount Card Not Explicitly Specified for FCC Suing Financials

**SRS Reference:** §5.7 FinancialPlaintiff  
> "Cards: Claim Amount, Legal Costs Incurred, Amount Awarded, Costs Awarded, Other Costs, **Recovered Amount**."

**Current Plan Behavior:**  
`CaseFinancialsSection` is specified generically for both defendant and plaintiff cases. The SRS explicitly calls out "Recovered Amount" as a **distinct summary card** specific to the FCC Suing (plaintiff) financial view. The plan mentions it in the KPI dashboard context (A.17.3) but does NOT specify it as a separate card in the `CaseFinancialsSection` props or UI layout for plaintiff cases.

**Required Fix:**  
- Add a conditional `Recovered Amount` card to `CaseFinancialsSection` when `caseType === 'plaintiff'`:
  ```tsx
  {caseType === 'plaintiff' && (
    <Card>
      <CardContent>
        <p className="text-sm text-muted-foreground">Recovered Amount</p>
        <p className="text-2xl font-bold">
          {formatCurrency(financials?.recovered_amount ?? 0)}
        </p>
      </CardContent>
    </Card>
  )}
  ```
- Add `recovered_amount: number` field to `FinancialPlaintiff` TypeScript type in Phase 2.
- The FCC Sued (defendant) side does NOT show "Recovered Amount" — the distinction is intentional per the SRS.
- Add to Phase 15 test checklist: "FCCSuingCaseDetailPage Financials section shows 'Recovered Amount' card; FCCSuedCaseDetailPage does not."

---

### SIG-08 — Member Data Sync from Corporate Service Not Reflected in UI

**SRS Reference:** §2.3 Business Rule 1  
> "Member data is synchronized with Corporate Service Microservice."

**Current Plan Behavior:**  
Phase 9.2 `CreateMemberDialog` fields are: `user_id (SmartSelect)`, `position`, `member_type`, `joined_date`. The SRS attributes include `email (sync from HR)` and `department`. There is no mention in the plan that:
- `email` and `department` are **read-only**, auto-populated from Corporate Service
- They should NOT be editable fields in the create/edit member form
- When displayed in member detail or the GoverningBodyDetailPage Members Section, they should reflect the live HR source (or the last synced value)

**Required Fix:**  
- In `CreateMemberDialog`, do NOT include `email` or `department` as form input fields — they are populated automatically from Corporate Service when the `user_id` is selected.
- When `user_id` is selected in the SmartSelect, show a read-only preview of the resolved user's email and department pulled from Corporate Service lookup:
  ```tsx
  {selectedUser && (
    <div className="rounded-md bg-muted p-3 text-sm space-y-1">
      <p><span className="text-muted-foreground">Email:</span> {selectedUser.email}</p>
      <p><span className="text-muted-foreground">Department:</span> {selectedUser.department}</p>
    </div>
  )}
  ```
- In the Member list columns and GoverningBodyDetailPage Members Section, show `department` as a column for admin-level context.
- Add to Phase 2 `Member` TypeScript type documentation: "email and department are read-only, synced from Corporate Service on record creation."

---

### SIG-09 — `On Hold` Stage Has No Defined CTAs

**SRS Reference:** §4.1 Stage list includes `On Hold`

**Current Plan Behavior:**  
The plan includes `on_hold` in `CASE_STAGES` and badge colors, but there are no CTAs defined for the `on_hold` state in either `FCCSuedCaseDetailPage` or `FCCSuingCaseDetailPage`. No service function exists to transition to/from `on_hold`. The plan's CTA tables (Phase 8.2) jump from `new` → `closed` with no mention of `on_hold`.

**Required Fix:**  
- Define what triggers `on_hold`: is it a manual action by Legal Manager or DG? Is it system-triggered?
- Add CTA: "Place On Hold" — visible from active stages (likely `hearing_stage` or `directive_issued`), gated on `isLegalManager`.
- Add CTA: "Resume from Hold" — visible when `stage === 'on_hold'`, gated on `isLegalManager`.
- Add corresponding service functions: `placeOnHold(caseType, id)` and `resumeFromHold(caseType, id)`.
- Add to Phase 15 checklist: verify on_hold transitions.

---

### SIG-10 — `RescheduleMeetingDialog` Missing from Dialog Inventory

**SRS Reference:** §1.2.1 Business Rules 4 & 10  
> "If quorum not met by StartDateTime, Secretary can reschedule (status returns to REGISTERED or DRAFT)."  
> "Secretary can postpone an ongoing meeting; status becomes POSTPONED. Meeting can be resumed later within same instance."

**Current Plan Behavior:**  
The plan includes a "Reschedule" CTA on `LegalMeetingDetailPage` (available from `draft`, `registered`, `postponed` states) and the service function `rescheduleMeeting(id, data)`. However, **no dialog is specified** anywhere in the Phase 9.2 dialog inventory to collect the new schedule data. The original `CreateMeetingDialog` cannot be reused (it creates a new meeting; reschedule modifies an existing one). The `rescheduleMeeting(id, data)` service function accepts a `data` payload that must at minimum include a new `start_datetime` and `end_datetime`, but there is no dialog to capture these values.

**Required Fix:**  
- Add `RescheduleMeetingDialog` to the dialog inventory (Phase 9.2 / Phase 16 Step 4):
  ```
  | RescheduleMeetingDialog | Fields: start_datetime (DateTimePicker, required), end_datetime (DateTimePicker, required), reschedule_reason (Textarea, optional) | max-w-xl |
  ```
- Cross-field validation: `end_datetime` must be after `start_datetime` (same `.refine()` pattern as meeting creation in §9.3).
- On submit: calls `rescheduleMeeting(id, { start_datetime, end_datetime, reschedule_reason? })`
- On success: meeting status transitions to `rescheduled`; new dates are reflected in the meeting details card.
- Add to Phase 16 Step 4: `components/grc/legal/RescheduleMeetingDialog.tsx`
- The CTA table in Phase 8.2 `LegalMeetingDetailPage` should reference this dialog explicitly.

**Note:** "Reschedule" (new date, creates `rescheduled` status) is distinct from "Postpone" (temporary hold, `postponed` status). Postpone is a direct stage transition with no data collection — no dialog needed. Reschedule requires the new date/time.

**Impact:** "Reschedule" button is rendered but clicking it has no defined behavior — the mutation cannot fire without a dialog to collect the new dates.

---

### SIG-11 — Settlement and Judgment Approval Workflow Has No UI Specification

**SRS Reference:** §4.7 SettlementDefendant Business Rule 1 / §4.8 JudgmentDefendant Business Rules 1–2

> §4.7: "Requires DG approval (via Legal Manager review)."  
> §4.8: "After judgment recorded, Legal Manager reviews and recommends to DG. DG decides: Accept or Appeal."

**Current Plan Behavior:**  
Phase 14.1 correctly lists `SettlementDefendant/Plaintiff` (workflow: `grc.legal_settlement_approval`) and `JudgmentDefendant/Plaintiff` (workflow: `grc.legal_judgment_decision`) as workflow-enabled entities. Service functions `submitSettlementForApproval(settlementId)`, `submitJudgmentForReview(judgmentId)`, and `dgDecisionOnJudgment(judgmentId, data)` are all defined.

However, **no UI is specified for triggering these flows**:
- Phase 8.2 `FCCSuedCaseDetailPage` CTA table does **not** include "Submit Settlement for Approval" or "Submit Judgment for LM Review" or "DG Decision on Judgment" buttons.
- Phase 8.3 workflow classification table lists only the case closure workflow for `FCCSuedCaseDetailPage` — settlement and judgment workflows are absent.
- `CaseSettlementSection` and `CaseJudgmentSection` have no `EmbeddedWorkflowConsole` or CTA buttons specified for the approval chain.
- `RecordJudgmentDialog` fields (§9.2) do NOT include `dg_decision` or `appeal_due_date` — meaning the DG decision happens separately, but there is no UI to make that decision.

**Required Fix:**

**For CaseSettlementSection:**
- Add "Submit for Approval" CTA when `settlement.status === 'proposed'` AND `isLegalOfficer`:
  ```tsx
  {settlement?.status === 'proposed' && isLegalOfficer && (
    <Button onClick={() => submitSettlementForApproval(settlement.id)}>
      Submit for Approval
    </Button>
  )}
  ```
- Add an `EmbeddedWorkflowConsole` inside `CaseSettlementSection` (or as a card directly below it) for workflow-enabled settlement approvals:
  ```tsx
  <EmbeddedWorkflowConsole
    entityType="legal-settlement-defendant"
    entityId={settlement.id}
    entityTitle={`Settlement — ${caseData.case_id}`}
    workflowPlanId={settlement.workflow_plan_id}
    onSubmit={isLegalOfficer && settlement.status === 'proposed' ? handleSubmitSettlement : undefined}
  />
  ```

**For CaseJudgmentSection:**
- Add "Submit for LM Review" CTA when `judgment.status` is a draft/initial state AND `isLegalOfficer`.
- Add a "DG Decision" section when `judgment.status === 'pending_dg_decision'` (or equivalent backend status): dropdown or button group for DG to select Accept or Appeal, with conditional `appeal_due_date` field (show `DatePicker` only when "Appeal" selected — mirrors the `RecordJudgmentDialog` §9.3 validation but in a separate dialog/section).
- Add an `EmbeddedWorkflowConsole` for `grc.legal_judgment_decision` workflow similarly.

**Add to Phase 8.3 classification table:**

| Page | Stage transitions | Workflow submissions | Notes |
|---|---|---|---|
| `CaseSettlementSection` | — | "Submit for Approval" → starts `grc.legal_settlement_approval` | EWC embedded in section |
| `CaseJudgmentSection` | "Submit for LM Review" (Legal Officer), "DG Accept/Appeal Decision" (DG) | — | Approval via EWC or dedicated CTA |

**Add to Phase 9.2 dialog inventory:**

| Dialog | Fields | Size |
|---|---|---|
| `DGJudgmentDecisionDialog` | dg_decision (radio/Select: Accept \| Appeal), appeal_due_date (DatePicker, required when Appeal) | `max-w-lg` |

**Impact:** Without CTAs and workflow UI for settlement/judgment approval, the Legal Manager cannot submit for DG review and the DG cannot make the accept/appeal decision on any judgment. The entire litigation approval chain is broken past the initial recording stage.

---

## 🟡 MINOR GAPS

### MIN-01 — Quorum Not Met → Reschedule Flow Not Specified

**SRS Reference:** §1.2.1 Business Rule 4  
> "If quorum not met by StartDateTime, Secretary can reschedule (status returns to REGISTERED or DRAFT)."

**Gap:** This specific scenario—quorum failure at the scheduled start time—does not have a dedicated CTA or flow in the plan. The existing "Reschedule" CTA is available from `draft` and `registered` states. If quorum was insufficient when `quorum_ready` status was expected but never achieved, the path back to `registered` for rescheduling is implicit but not documented.

**Fix:** Add a note in Phase 8.2 `LegalMeetingDetailPage`: when meeting status stalls at `invitations_sent` or `agenda_shared` and quorum is NOT met by start time, Secretary uses the "Reschedule" button to reset status to `registered`. The quorum display (A.6.2) should show a warning banner when quorum threshold has not been met and the scheduled start time has passed.

---

### MIN-02 — Minutes Approval Type (Majority Vote vs Sign-Off) Not Addressed

**SRS Reference:** §1.2.5 Business Rule 2  
> "Approval may be by majority vote or explicit sign-off (configurable)."

**Gap:** The plan handles Minutes approval entirely through the `EmbeddedWorkflowConsole` with the `grc.legal_minutes_approval` workflow template. The SRS says this is configurable (majority vote or explicit sign-off). The frontend plan doesn't address this configurability at all.

**Fix:** Add a note in `MinutesDetailPage` (Phase 8.2): the approval mechanism is determined by the workflow template configuration managed by the System Administrator. Frontend behavior is driven by what the `EmbeddedWorkflowConsole` renders. No special frontend code needed, but this should be documented so implementers know the behavior changes based on system configuration.

---

### MIN-03 — Task Auto-Creation Not Distinguished from Manual Tasks

**SRS Reference:** §4.10 Business Rule 1  
> "Auto-created for appeal deadlines, filing approvals, etc."

**Gap:** `TaskLitigation` TypeScript type and `CaseTasksSection` component do not include an `auto_created: boolean` field or `source` indicator. Users viewing the tasks list cannot distinguish auto-created tasks (system-generated) from manually created ones.

**Fix:**  
- Add `auto_created: boolean` (or `source: 'manual' | 'system'`) to `TaskLitigation` TypeScript type.
- In `CaseTasksSection`, auto-created tasks show a "System" badge next to the task title.
- Auto-created tasks should NOT show a "Delete" action button (backend also enforces this).
- The "Create Task" button in `CaseTasksSection` creates only manual tasks.

---

### MIN-04 — Member Secretary Assignment to Multiple Bodies (Secretary Multi-Assignment UI)

**SRS Reference:** §2.3 Business Rule 4  
> "Administrator can assign users as Secretary to multiple governing bodies."

**Gap:** The plan's `CreateGoverningBodyDialog` has a `secretary_user_ids` multi-select SmartSelect, which allows assigning multiple secretaries to one body. But the reverse—seeing all bodies a given user is Secretary of—is not surfaced in the `MembersPage` or any view. The `Member` entity has a position field (`Member/Secretary/Chairman`) which implies Secretary can be indicated at the membership level, separate from the governing body's `secretary_user_ids` array.

**Fix:**  
- In `MembersPage`, when a member has `position === 'Secretary'`, show all governing bodies they are Secretary of (this would require fetching governing bodies filtered by `secretary_user_id`).
- In `GoverningBodyDetailPage`, the "Secretaries" card already exists per Phase 8.2 — confirm it shows all assigned secretaries resolving their names via `UserDisplay`.
- Add a note: secretary assignment is done via `UpdateGoverningBodyDialog` (edit the body, modify `secretary_user_ids`), not via the `CreateMemberDialog`.

---

### MIN-05 — Public Register Future Portal Integration Note Missing

**SRS Reference:** §3.1 Business Rule 2  
> "Published decisions become visible via public portal (future)."

**Gap:** The plan covers the internal Public Register page and the publish action, but does not note that published decisions are intended for a future public portal integration (likely with FCC CRM per §1.2 Scope). Implementers may not know this context.

**Fix:** Add a note in `PublicDecisionDetailPage` spec (Phase 8.2) and `PublicRegisterPage` spec: "Published decisions feed the future public portal. The `status = 'published'` and `published_date` fields are consumed by the FCC CRM integration (future scope). The internal view here is for governance management only."

---

### MIN-06 — Conflict of Interest Must Not Persist Across Meetings

**SRS Reference:** §1.2.4 Business Rule 3 / §6.8  
> "Conflict record does not affect future meeting participation."

**Gap:** When displaying member records in `MeetingParticipantsSection`, if a member has historical conflict declarations from past meetings, those must not carry over to the current meeting. The plan's conflict display (A.6.4) doesn't explicitly state this scoping rule. A developer might inadvertently show an "has conflicts" warning for a member based on all-time conflict history rather than the current meeting's agenda items only.

**Fix:** Add to `MeetingAgendaSection` / A.6.4 documentation: Conflict declarations are scoped to `agenda_id`. When displaying conflicts, only show declarations where `agenda.meeting_id === currentMeeting.id`. Do NOT aggregate conflict status across meetings. A member with past conflicts is not flagged in new meetings.

---

### MIN-07 — `canManageMembers` Reference in A.15.1 Is Not a Valid Permission Code

**SRS Reference:** Phase 5.1 (28 canonical permission codes)

**Gap:** Addendum A.15.1 `MembersPage Specification` says:
> "Actions per row: Edit, Deactivate (permission-gated: `canManageMembers`)"

But `canManageMembers` is NOT one of the 28 canonical permission codes or convenience booleans defined in Phase 5.1. The correct boolean is `canManageGoverningBody`.

**Fix:** In A.15.1, replace `canManageMembers` → `canManageGoverningBody` in all references. Confirm Phase 10.6 RBAC matrix for `MembersPage` uses the same correction.

---

### MIN-08 — Task Reminder Schedule Should Be Noted in Frontend Plan

**SRS Reference:** §4.10 Business Rule 2  
> "Reminders at 7, 2, 1 day before due date; overdue notification."

**Gap:** The plan (A.9.1) notes that overdue status is computed by backend Celery Beat. But it doesn't mention the reminder schedule (7/2/1 day) or that users should expect to receive these notifications via the notification engine (SIG-04). If the in-app notification system is built, these reminders should appear in the notification inbox.

**Fix:** Add a note in `CaseTasksSection` and Phase 11 (Notifications): "The Work Orchestration Service sends task reminder notifications at 7, 2, and 1 day before due date. These are delivered via the notification engine (SIG-04 — notification inbox). The task list UI uses `stale_time: 5min` and does not need to poll for overdue transitions separately."

---

### MIN-09 — Member Position vs Meeting Role — Potential Type Confusion

**SRS Reference:** §2.3 `Member` attributes: Position `(Member/Secretary/Chairman)` vs §1.2.3 `MeetingParticipant` attributes: Role `(Member/Invitee)`

**Gap:** The `Member.position` enum (`Member/Secretary/Chairman`) and `MeetingParticipant.role` enum (`Member/Invitee`) share the value `"Member"` with different semantic meanings. TypeScript types must keep these distinct. Looking at Phase 2, the `Member` type has a `position` field and the `MeetingParticipant` type has an `invitation_status` field, but the `role` field (`member | invitee`) is defined for `MeetingParticipant`. These are correctly separate, but not explicitly documented as distinct enums.

**Fix:** In Phase 2 TypeScript types, add comments distinguishing:
- `Member.position`: `'member' | 'secretary' | 'chairman'` — the member's governance structure role (Section 2 of SRS)
- `MeetingParticipant.role`: `'member' | 'invitee'` — participant category for a specific meeting (Section 1.2.3 of SRS)

Add to Phase 2.2: `MEMBER_POSITIONS = ['member', 'secretary', 'chairman']` and `PARTICIPANT_ROLES = ['member', 'invitee']` as separate const maps.

---

### MIN-10 — Approval Chain Display Uses `actor_name` (Stored) but LegalAuditLog Does Not Store It

**SRS Reference:** §6.1 / Plan A.1.4, A.16.4

**Gap:** Phase A.6.5 (Digital Signature Display) renders an Approval Chain card showing `actor_name`. However, A.16.4 explicitly states the corrected `LegalAuditLog` type does NOT store `actor_name` — it must be resolved from the `actor_id` UUID.

But `ApprovalChainEntry` (A.1.2) includes `actor_name: string` as a stored field:
```ts
interface ApprovalChainEntry {
  actor_id: string;
  actor_name: string;  ← This is stored in ApprovalChainEntry, NOT LegalAuditLog
  ...
}
```

These are two different structures. `ApprovalChainEntry` (stored on FilingDefendant/FilingPlaintiff) explicitly stores `actor_name` (backend-populated at time of approval). `LegalAuditLog` does NOT store `actor_name`.

**Fix:** This is an inconsistency in the plan's documentation that could confuse implementers. Add a clarifying note:
- `ApprovalChainEntry.actor_name` → stored string, rendered directly (not via `UserDisplay`)
- `LegalAuditLog.actor_id` → UUID, always resolved via `<UserDisplay userId={...} />` component
- Do NOT use `UserDisplay` in the ApprovalChainDisplay component — render `entry.actor_name` directly.

---

### MIN-11 — `DG_REVIEW_STATUS` Values Not Fully Defined in Phase 2.2

**SRS Reference:** §4.1 `DGReviewStatus (Pending / Reviewed / Directive Issued)`

**Gap:** Phase 2.2 lists `DG_REVIEW_STATUSES` in A.17.8 ("clarify the DG_REVIEW_STATUS values") but does NOT include them in the main Phase 2.2 status enum maps section. They are only added as a note in A.17.8.

**Fix:** Add `DG_REVIEW_STATUSES = ['pending', 'reviewed', 'directive_issued']` explicitly to Phase 2.2 status enum maps table. Also confirm the `dg_review_status` field is included in both `CaseDefendant` and `CasePlaintiff` TypeScript types (it is in the SRS for both §4.1 and §5.1).

---

### MIN-12 — Resolution Detail Page Missing (Resolutions Are Searchable)

**SRS Reference:** §1.2.6 Business Rule 2  
> "Resolutions are searchable by invited participants."

**Gap:** The plan has a `ResolutionsPage` (read-only list, no create button — correct per A.15.4). However, there is no `ResolutionDetailPage` specified. The SRS says resolutions are searchable, implying users need to be able to open and read individual resolutions. A list with only columns provides limited context.

**Fix:** Options:
1. Add a `ResolutionDetailPage` with the full resolution text, date adopted, meeting link, responsible person, effective date, and attachments — accessible via the list row "View" action.
2. Alternatively, expand the `ResolutionsPage` row to show a "View" panel (drawer/slide-over) with full resolution details without a separate page.

Either way, the resolution text (which is the core content per §1.2.6) must be readable. A list page showing only columns doesn't expose the full `resolution_text` field.

---

### MIN-13 — `PlaintiffAdvocate` Omitted from FCCSuedCasesPage List Columns

**SRS Reference:** §4.0 Case List Columns  
> "Case Ref No, Respondent, Case Type, Court, Claim Amount, Stage, Status, Risk, Next Hearing, Actions"

Note: The SRS column "Respondent" maps to "Plaintiffs" for defendant cases. The `plaintiff_advocate` field is a case attribute (§4.1 attributes).

**Gap:** The SRS-specified case list columns don't include `plaintiff_advocate`, but the detail page should prominently show it. The plan's `FCCSuedCasesPage` column spec (Phase 7.2) shows: `Case ID, Court, Plaintiffs, Stage, Urgency`. This is missing:
- Claim Amount column (addressed in A.17.4)
- Risk Level column (addressed in A.17.4)
- Next Hearing column (addressed in A.17.4)
- Status column vs Stage column: The SRS shows BOTH "Stage" AND "Status" — in the current data model stage IS the primary progression indicator. Clarify with backend if there's a separate `status` field or if `stage` serves both roles.

**Fix:** Confirm whether `CaseDefendant` and `CasePlaintiff` have a separate `status` field distinct from `stage`. If not, the SRS "Status" column maps to display of `stage`. If yes, add both as columns. All A.17.4 corrections must be applied to both case list pages.

---
### MIN-14 — Activity Log Does Not Display Status Transition Details

**SRS Reference:** §6.3 Audit Trail  
> "Fields: EntityID, EntityType, PreviousStatus, NewStatus, ActorID, IPAddress, ActionTimestamp, Comments."

**Current Plan Behavior:**  
The corrected `LegalAuditLog` TypeScript type (Addendum A.16.4) was derived from `Legal_Module_Base_Models_Mixins.md` and does NOT include `previous_value` / `new_value` / `actor_name` fields. The Activity Log display code in A.8.4 renders:
```tsx
{entry.action}{entry.comment ? ` — ${entry.comment}` : ''}
```
This shows only the action name (e.g., `status_changed`) and an optional comment, with no indication of **what the status changed from/to**. The SRS requires PreviousStatus and NewStatus to be logged and presumably visible.

**Analysis:**  
The backend's `LegalAuditLog` model stores status transition context in the `metadata: Record<string, unknown>` field. For `action === 'status_changed'` events, `metadata` is expected to contain `{ from_status: string, to_status: string }`. The frontend just doesn't read or render these values.

**Required Fix:**  
- In the Activity Log display (A.8.4), check `metadata` for status transition details:
  ```tsx
  const getActionDetail = (entry: LegalAuditLog) => {
    if (entry.action === 'status_changed' && entry.metadata?.from_status) {
      return `${entry.action}: ${entry.metadata.from_status} → ${entry.metadata.to_status}`;
    }
    return `${entry.action}${entry.comment ? ` — ${entry.comment}` : ''}`;
  };
  ```
- Confirm with backend team: what `metadata` keys are populated for each `action` type? Add this as a contract note in Phase 3 (API Integration).
- Note: `IPAddress` is intentionally excluded from frontend display for security/privacy reasons — this is correct and not a gap.
- `actor_name` is NOT in the model (A.16.4 is correct) — always use `<UserDisplay userId={entry.actor_id} />`.

---

### MIN-15 — "Start Meeting" CTA Missing Time-Window Guard

**SRS Reference:** §1.2.1 Business Rule 8  
> "Meeting Start: Only allowed if `QuorumMet = true` **and current time is within meeting schedule**."

**Current Plan Behavior (Phase 8.2 LegalMeetingDetailPage CTA table):**  
```tsx
"Start Meeting" | status === 'quorum_ready' AND meeting.quorum_met === true AND isSecretary
```
The CTA guard checks quorum and secretary role but does **not** check whether the current time is within the meeting's `start_datetime` to `end_datetime` window. A Secretary could theoretically click "Start Meeting" days before the scheduled date.

**Required Fix:**  
- Add a time-window check to the "Start Meeting" guard:
  ```tsx
  const now = new Date();
  const canStartMeeting = 
    meeting.status === 'quorum_ready' &&
    meeting.quorum_met === true &&
    isSecretary &&
    now >= new Date(meeting.start_datetime);   // cannot start before scheduled time
  ```
- If the Secretary is on the page before the scheduled start time, show an informational note:
  ```tsx
  {meeting.status === 'quorum_ready' && meeting.quorum_met && isSecretary && now < new Date(meeting.start_datetime) && (
    <Alert>
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription>
        Meeting can be started from {formatDate(meeting.start_datetime)}.
      </AlertDescription>
    </Alert>
  )}
  ```
- The backend also enforces this constraint — the frontend check is UX enhancement only, preventing the user from submitting a request that will fail.
- Note: The plan does NOT need an upper bound check (`now <= end_datetime`) — the Secretary might need to start slightly late.

---

### MIN-16 — DirectiveDetailPage Assigned-User Identity Check Pattern Not Documented

**SRS Reference:** §1.2.4 Business Rule 1  
> "Only the assigned user can perform initial closure (mark as `CLOSED` with summary)."

**Current Plan Behavior (Phase 10.6):**  
The phase correctly states `DirectiveDetailPage | — (no RBAC booleans needed) | Mark In Progress / Close: assigned user identity check`. However, unlike the Submission Withdraw pattern (which has explicit code examples throughout the plan), the directive identity check has no matching implementation example anywhere in the plan.

**Required Fix:**  
- Add to Phase 8.2 `DirectiveDetailPage` CTAs the explicit check pattern:
  ```tsx
  const isAssignedUser = directive.assigned_user_id === currentUser?.id;

  {isAssignedUser && directive.status === 'open' && (
    <Button onClick={handleMarkInProgress}>Mark In Progress</Button>
  )}
  {isAssignedUser && directive.status !== 'closed' && directive.status !== 'fully_closed' && (
    <Button onClick={() => setIsCloseDialogOpen(true)}>Close Directive</Button>
  )}
  ```
- "Fully Close" CTA remains Secretary-only (not assigned-user), in the Matters Arising context:
  ```tsx
  {isSecretary && directive.status === 'closed' && !directive.finally_closed && (
    <Button onClick={() => setIsFullyCloseDialogOpen(true)}>Fully Close</Button>
  )}
  ```
- These patterns should also be referenced from Phase 10.3 (Action Restrictions) documentation.

---

### MIN-17 — `CreateResolutionDialog` Contradicts SRS Auto-Creation Rule

**SRS Reference:** §1.2.6 Business Rule 1  
> "Automatically created from agenda outcomes. Visible only to meeting invitees."

**Contradicting Plan Sections:**
- **A.7.9** (Gap Closures) adds `CreateResolutionDialog` to the dialog inventory for `POST legal/minutes/{pk}/resolutions/`
- **A.15.4** (E7.1 business rule enforcement) explicitly states: "Do not render a 'Create Resolution' button anywhere — resolutions are auto-created by the system."
- **ResolutionsPage** (Phase 7.2) is correctly specified as read-only with no create button

**Analysis:**  
The `CreateResolutionDialog` in A.7.9 was added to support manual resolution creation from within the `MinutesDetailPage` (for the Secretary to formalize resolution text after the meeting). However, the SRS says resolutions are auto-created from agenda outcomes. There is a tension between:
1. SRS §1.2.6 rule 1 (auto-created) → no manual creation
2. A.7.9 (Secretary can manually add resolution text under minutes) → create dialog exists

**Required Fix:**  
- Confirm with the backend team which interpretation is correct:
  - **Option A:** Resolutions are 100% auto-created (SRS strict reading) → remove `CreateResolutionDialog` entirely; remove `POST legal/minutes/{pk}/resolutions/` from Phase 9.6 sub-resource endpoints; remove dialog from A.7.9. Secretary has no manual resolution creation ability.
  - **Option B:** Resolutions are auto-created with a template but the Secretary can finalize/edit the `resolution_text` field → keep the dialog but rename it `EditResolutionDialog` and scope it to editing existing auto-created resolutions (no create from scratch). The `POST` endpoint becomes `PATCH legal/resolutions/{id}/`.
- Until confirmed, mark `CreateResolutionDialog` as **conditional** in the implementation plan — do NOT implement until the contradiction is resolved with the backend team.
- Add to Phase 15 test checklist: "Verify whether Secretary can manually create resolutions or only system-creates them from agenda outcomes."

---

### MIN-18 — GoverningBody Missing Meeting Number Prefix/Format Configuration Fields

**SRS Reference:** §1.2.1 Business Rule 1  
> "Must generate unique numbers per governing body using a configured prefix and either endless sequence (`<PREFIX>-NNN`) or financial year format (`<PREFIX>/YYYY-YYYY/NNN`). Sequence must be atomic to avoid duplicates."

**SRS §6.2 (Unique Identifier Generation):**  
> "Meeting Numbers: Prefixes defined per governing body, with either endless or financial-year sequence."

**Current Plan Behavior:**  
The `GoverningBody` TypeScript type (Phase 2.1) includes: `id`, `committee_type`, `name`, `composite_title`, `description`, `secretary_user_ids`, `is_active`, `created_by/at/updated_at`. There are **no meeting number configuration fields** — neither `meeting_number_prefix` nor `meeting_number_format`. The `CreateGoverningBodyDialog` (Phase 9.2) similarly has no such fields.

**Required Fix:**  
1. **Confirm with backend team** whether these fields are stored on `GoverningBody` or in a separate config model. The SRS says "prefixes defined per governing body" — the most natural place is the `GoverningBody` model itself.
2. If stored on `GoverningBody`, add to TypeScript type:
   ```ts
   meeting_number_prefix?: string;          // e.g. "FCC-CMT-A"
   meeting_number_format?: 'sequential' | 'financial_year';
   ```
3. Add to `CreateGoverningBodyDialog` fields:
   - `meeting_number_prefix` (Input, required — text field with uppercase enforcement)
   - `meeting_number_format` (Select: "Sequential (PREFIX-NNN)" | "Financial Year (PREFIX/YYYY-YYYY/NNN)")
4. Display on `GoverningBodyDetailPage` in the Details Card.
5. Add to Phase 15 checklist: "Meeting numbers generated for a body use the configured prefix and format."

**Note:** This configuration is critical for system setup — without it, all meetings for a governing body will have incorrectly formatted reference numbers.

---
## ⚫ PLAN OVER-SCOPE (Feature NOT in SRS)

### OVER-01 — Legal Notices Feature Not Defined in SRS

**SRS Coverage:** The SRS (`Legal_Service.md`) defines 6 functional areas: Meeting Governance, Governance Structures, Determinations & Approvals, Litigation – FCC Sued, Litigation – FCC Suing, Public Register. Legal Notices are **NOT** one of them.

**Plan Behavior:**  
The implementation plan includes:
- `CreateLegalNoticeDialog` (Phase 9.2)
- Two permission codes: `grc:legal_notice:view` and `grc:legal_notice:manage` (Phase 5.1 / A.16.2)
- `canViewNotices` and `canManageNotices` booleans in `useLegalPermissions.ts`
- A `hooks/useLegalNotices.ts` mention

These features exist in the backend (`grc-service.json` has the permission codes), but they have **no SRS specification**. This is either:
1. A feature from a separate requirements document not referenced here
2. Feature creep that should be removed from scope
3. An implicit service-of-process / legal notice tracking requirement that the SRS author considered out of scope

**Action Required:**  
- **Do NOT implement Legal Notices as part of the legal module per this SRS.** The SRS is the authoritative requirements document.
- If Legal Notices are a confirmed backend feature from another spec, that spec must be obtained and a separate specification section/document created before frontend implementation begins.
- The `grc:legal_notice:view/manage` permission codes should remain in `useLegalPermissions.ts` for future use but not wired to any UI components until a corresponding SRS section or specification is approved.
- Remove `CreateLegalNoticeDialog` from the current implementation plan scope; add it to a `Phase 2 — Out of Scope` section.

---

## Implementation Priority Order for Gap Fixes

The following order is recommended for addressing the identified gaps, based on SRS compliance impact:

### Immediate (before implementation starts):
1. **CRIT-01** — Fix Submission creation permission (any staff)
2. **CRIT-02** — Map Registry Officer role to permissions
3. **CRIT-03** — Fix CASE_STAGES and badge color table
4. **CRIT-04** — Resolve `closure_pending` stage with backend
5. **CRIT-05** — Fix Breach Report Intake permission (any staff / Department Users)

### Before Phase 7-8 implementation:
6. **SIG-07** — Add Recovered Amount card to plaintiff financials
7. **SIG-08** — Update member dialog for Corporate Service sync fields
8. **SIG-09** — Define On Hold stage CTAs
9. **SIG-10** — Add `RescheduleMeetingDialog` to dialog inventory
10. **SIG-11** — Specify Settlement and Judgment approval workflow UI (EWC placement, CTAs, `DGJudgmentDecisionDialog`)
11. **MIN-03** — Add auto_created field to TaskLitigation type
12. **MIN-09** — Add separate const maps for Member positions vs Participant roles
13. **MIN-11** — Add DG_REVIEW_STATUSES to Phase 2.2
14. **MIN-17** — Resolve CreateResolutionDialog vs auto-creation contradiction (confirm with backend before implementation)
15. **MIN-18** — Confirm GoverningBody meeting number prefix/format fields with backend; add to type + form

### Before Phase 10-11 implementation:
16. **SIG-02** — Document invitee access pattern for DirectivesPage
17. **SIG-05** — Document assigned-to filtering behavior + test checklist
18. **MIN-07** — Fix `canManageMembers` → `canManageGoverningBody` in A.15.1
19. **MIN-15** — Add time-window guard to "Start Meeting" CTA
20. **MIN-16** — Document DirectiveDetailPage assigned-user identity check code pattern

### Deferred to Phase 2 of development:
21. **SIG-01** — Case archiving UI (archive/unarchive)
22. **SIG-03** — Configurable DG approval for litigation directive closure
23. **SIG-04** — In-app notification inbox
24. **SIG-06** — Confirm and expand defendant response types
25. **MIN-12** — Resolution detail page
26. **OVER-01** — Legal Notices — defer to separate spec

### Documentation/Notes (low overhead):
27. **MIN-01** — Quorum failure reschedule flow note
28. **MIN-02** — Minutes approval type configurability note
29. **MIN-04** — Secretary multi-body assignment UX note
30. **MIN-05** — Public portal future integration note
31. **MIN-06** — Conflict of interest meeting scoping note
32. **MIN-08** — Task reminder schedule note
33. **MIN-10** — Approval chain vs audit log actor_name clarification
34. **MIN-13** — Confirm Stage vs Status column for case list pages
35. **MIN-14** — Activity Log status transition display (check `metadata.from_status`/`to_status`)

---

## Checklist Update for Phase 15 (Testing)

Add the following test cases to Phase 15 that are currently missing:

### From Initial Analysis (27 gaps):
- [ ] Department User (without `canManageGoverningBody`) can CREATE a submission (CRIT-01)
- [ ] Registry Officer can register a case (CRIT-02)
- [ ] Case badge colors match exact SRS stage values (no `settlement`, `judgment`, `appealed` stages) (CRIT-03)
- [ ] Closed case shows "Archive" button; archived case does not appear in default list (SIG-01)
- [ ] Meeting invitee (without `grc:legal_directive:view`) can only see directives from their meeting (SIG-02)
- [ ] Litigation directive closure flow respects `requires_dg_approval_for_closure` config (SIG-03)
- [ ] FCCSuingCaseDetailPage Financials shows "Recovered Amount" summary card (SIG-07)
- [ ] Creating a member pre-populates email + department from Corporate Service (read-only) (SIG-08)
- [ ] Legal Officer's case list only shows cases where they are assigned (SIG-05)
- [ ] Legal Notice CREATE button/dialog is NOT present in Phase 1 implementation (OVER-01)
- [ ] Case can be placed On Hold; "On Hold" badge displays; "Resume from Hold" CTA appears (SIG-09)
- [ ] Member.position (Member/Secretary/Chairman) and MeetingParticipant.role (Member/Invitee) render distinctly (MIN-09)
- [ ] Conflict declaration is scoped to current meeting agenda item — no cross-meeting carry-over (MIN-06)
- [ ] Resolution row "View" action opens full resolution text (MIN-12)
- [ ] FCCSuedCasesPage and FCCSuingCasesPage list columns include Claim Amount, Risk Level, Next Hearing (A.17.4)

### From Re-Verification Pass (8 new gaps):
- [ ] Department User (without `canManageCases`) can click "Raise Breach Report" on FCCSuingCasesPage (CRIT-05)
- [ ] "Reschedule" CTA on LegalMeetingDetailPage opens `RescheduleMeetingDialog` and captures new date/time (SIG-10)
- [ ] After reschedule, new start/end datetime visible in meeting details card (SIG-10)
- [ ] "Submit Settlement for Approval" CTA appears in CaseSettlementSection when `status === 'proposed'` and `isLegalOfficer` (SIG-11)
- [ ] Settlement workflow console (EWC) renders in CaseSettlementSection after submission (SIG-11)
- [ ] "Submit Judgment for LM Review" CTA appears in CaseJudgmentSection after judgment is recorded (SIG-11)
- [ ] DG can make accept/appeal decision on judgment via `DGJudgmentDecisionDialog` (SIG-11)
- [ ] `appeal_due_date` field is required in DG judgment decision dialog when "Appeal" is selected (SIG-11)
- [ ] Activity Log for `status_changed` events shows "from status → to status" (MIN-14)
- [ ] "Start Meeting" button is disabled/hidden when current time is before `meeting.start_datetime` (MIN-15)
- [ ] Secretary who is before scheduled time sees informational alert about start time (MIN-15)
- [ ] Only assigned user sees "Mark In Progress" and "Close Directive" buttons on DirectiveDetailPage (MIN-16)
- [ ] Secretary (not assigned user) sees "Fully Close" button on DirectiveDetailPage (MIN-16)
- [ ] Confirm whether `CreateResolutionDialog` is present (verify contradiction resolution: Option A = removed, Option B = edit-only) (MIN-17)
- [ ] GoverningBodyDetailPage displays meeting_number_prefix and meeting_number_format fields (MIN-18)
- [ ] CreateGoverningBodyDialog allows setting meeting number prefix and format when creating/editing (MIN-18)
- [ ] Meeting numbers generated for the body use the correct prefix and format pattern (MIN-18)

---

*Analysis based on: `Legal_Service.md` (SRS) vs `Legal_Module_Frontend_Implementation_Plan.md` (v+Addenda A.1–A.17)*  
*Re-verification performed: 2026-03-21 — 8 additional gaps (CRIT-05, SIG-10–SIG-11, MIN-14–MIN-18) added.*

