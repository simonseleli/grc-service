# SRS vs Frontend Implementation Plan — Comprehensive Gap Analysis
# Risk Management & Quality Assurance Module

**SRS Source:** `grc-service/implementation/my_implementation/grc/GRC_SRS/risk/RISK_MANAGEMENT.md`
**Plan Source:** `grc-service/implementation/my_implementation/grc/risk_management/Risk_management_Module_Frontend_Implementation_Plan.md`
**Backend:** 100% implemented (all endpoints live)
**Date:** March 2026

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully covered in Frontend Plan |
| ⚠️ | Partially covered — gaps documented below |
| ❌ | Not covered — missing from Frontend Plan entirely |

---

## Summary Table — SRS Processes vs Plan Coverage

| SRS Process | Number | Plan Coverage |
|-------------|--------|---------------|
| Appointment of Risk Champions | FCC_SBP_RMQA_01 | ⚠️ Partial |
| Development of Departmental Risk Register | FCC_SBP_RMQA_03 | ⚠️ Partial |
| Preparation of Institutional Risk Register | FCC_SBP_RMQA_04 | ⚠️ Partial |
| Implementation of Proposed Controls (RTAP) | FCC_SBP_RMQA_05 | ⚠️ Partial |
| Appointment of Quality Auditors | FCC_SBP_RMQA_06 | ⚠️ Partial |
| Conducting Quality Audit | FCC_SBP_RMQA_07 | ⚠️ Partial |
| System Req 4.11.1.1 — Risk Management | — | ⚠️ Partial |
| System Req 4.11.1.2 — Risk Champions | — | ⚠️ Partial |
| System Req 4.11.1.3 — Risk Profiling | — | ✅ Covered |
| System Req 4.11.1.4 — Quality Assurance | — | ⚠️ Partial |

---

## 1. Risk Dashboard Page — MISSING ENTIRELY

### SRS Requirement
- System Design §1.5.3.4: "Track risk status", "Generate risk report"
- SRS 4.11.1.1 req 13: "monitor implementation of agreed action plans and prepare quarterly report"
- SRS 4.11.1.1 req 14: "generate Quarterly Risk Management Implementation Report for submission to Audit Committee and IAGO"

### What the Plan Has
- `useRiskDashboard.ts` hook ✅
- `riskDashboard` API path constant ✅
- `fetchRiskDashboard()` and `fetchRiskDashboardComparativeAnalysis()` service functions ✅
- `RiskDashboard` and `RiskDashboardComparative` TypeScript interfaces ✅
- `canViewRiskDashboard` permission boolean ✅

### What Is Missing ❌
1. **`RiskDashboardPage.tsx`** — no page component exists in the folder structure
2. **Route** — no `/service/grc/risk-dashboard` route in `App.tsx`
3. **Sidebar item** — no "Risk Dashboard" entry in the `servicesConfig.ts` plan
4. **Implementation Phase** — not included in any Phase (A–I) in §13

### Impact
Without this page, the comparative analysis data and summary statistics computed by the backend are never shown to the user. The SRS requirement to "track risk status" and "generate risk reports" cannot be satisfied.

### Resolution Required
Add to the Frontend Plan:
```
// In folder structure (§1.1):
├── RiskDashboardPage.tsx    ← NEW

// In routing (§1.2):
<Route path="risk-dashboard" element={<RiskDashboardPage />} />

// In sidebar (§1.3):
{ title: 'Risk Dashboard', url: '/service/grc/risk-dashboard', icon: LayoutDashboard, group: 'Risk Management' }

// In §13 Phase D or Phase A:
Add RiskDashboardPage implementation step
```

**Dashboard must display:**
- `total_risks`, `open_risks` — from `RiskDashboard`
- `rtap_completion_rate` — progress bar
- `qpr_summary` — current quarter implementation rate
- `qa_summary.pending_nc_closures` — alert count
- Comparative analysis chart — quarters vs implementation rates from `RiskDashboardComparative`

---

## 2. Comparative Analysis View — NOT RENDERED

### SRS Requirement
- RTAP process: "RMQAM to compare current quarter implementation rates against previous quarters; identify trends, delays, and improvement areas"
- Data Requirements: current/previous implementation rate, variance and trend analysis

### What the Plan Has
- `QuarterlyPerformanceReport` type has `implementation_rate_current`, `implementation_rate_previous`, `variance` fields ✅
- `RiskDashboardComparative` interface with `quarters[]`, `implementation_rates[]`, `risk_counts[]` ✅
- `fetchRiskDashboardComparativeAnalysis()` endpoint ✅

### What Is Missing ❌
1. **No chart/graph component** described anywhere in the plan for comparative analysis data
2. **No section in `RiskPerformanceReportDetailPage`** to render the trend comparison
3. **No `RiskDashboardPage`** to embed the comparative chart (see Gap #1)

### Resolution Required
Document in §5 (Detail Pages) or the new §RiskDashboardPage:
- A line chart or bar chart component using `quarters[]` vs `implementation_rates[]` from the comparative analysis API
- Rendered in both `RiskDashboardPage` AND as a section card in `RiskPerformanceReportDetailPage`

---

## 3. QA Examination Tracking — INCOMPLETE

### SRS Requirement (FCC_SBP_RMQA_06)
- "QA must pass ISO 9001:2015 audit examination with score of 75%+"
- "If proposed QA fails to obtain 75%+ they will be required to re-sit"
- "If failed for second attempt, Heads will be required to propose another QA"
- Data Requirements: `attempt_number`, `score_obtained`, `pass_fail_status`

### What the Plan Has
- `QualityAuditor.exam_score` field ✅
- `QAAppointmentFormData.exam_score` field ✅
- `QAStatus` includes `'passed'` and `'failed'` values ✅

### What Is Missing ❌
1. **`QATrainingAttendee` lacks exam fields** — type only has `attendance_confirmed: boolean`; missing:
   - `exam_score: number`
   - `exam_attempt_number: number` (1 or 2)
   - `exam_date: string`
   - `passed: boolean`
2. **No form validation for 75% threshold** — `§6` (Forms & Modals) documents validation rules but does NOT include:
   - `z.coerce.number().min(75)` rule for passing score entry
   - Business rule: "if score < 75 and attempt_number === 2, trigger replacement nomination toast"
3. **No replacement nomination flow documented** — when a QA candidate fails twice, UI should display a destructive alert and guide the user to "propose a new candidate"
4. **No attempt counter** in `QualityAuditorDetailPage` or `QATrainingDetailPage`

### Resolution Required
Add to §3.3 (TypeScript types):
```ts
export interface QATrainingAttendee {
  id: string;
  training_session: string;
  attendee_id: string;
  attendance_confirmed: boolean;
  exam_date?: string;
  exam_score?: number;           // 0–100
  exam_attempt_number?: number;  // 1 or 2
  passed?: boolean;              // true if exam_score >= 75
  created_at: string;
}
```

Add to §6 (Forms & Modals) validation table:
```
| QA exam score | Zod | z.coerce.number().min(0).max(100) — display warning if < 75 |
| QA second attempt failure | submit-time guard | If attempt_number === 2 && score < 75: toast.error('Candidate failed second attempt. A replacement nomination is required.') and block further exam entry |
```

---

## 4. NC Dispute / Finding Amendment Flow — MISSING

### SRS Requirement (FCC_SBP_RMQA_07 steps 16–17)
- "If the auditee disagrees with the findings, TL corrects or amends or deletes that observation"
- "Upon agreement with the audit observation, auditee and TL signs the report"

### What the Plan Has
- Sign TL button and Sign Auditee button on `QMSAuditReportDetailPage` ✅
- `NonConformancesPage` with list + view dialog ✅
- `NonConformance.closure_status` field ✅

### What Is Missing ❌
1. **No "Dispute Finding" action** on `NonConformancesPage` or `QMSAuditReportDetailPage` — TL cannot mark a finding as "disputed" or "under amendment"
2. **No "Amend/Delete Finding" action** — the current plan only shows standard CRUD + status changes; no specific flow for auditee disagreement
3. **`closure_status` enum is missing `'disputed'` and `'amended'` values** in `NCStatus`
4. **No visible workflow** from `'open'` → `'disputed'` → `'amended'` → back to signing flow described in the plan

### Resolution Required
Add to §3.3 (TypeScript types):
```ts
export type NCStatus = 'open' | 'action_assigned' | 'in_progress' | 'closed' | 'disputed' | 'withdrawn';
```

Add to §5 (Detail Pages) or §6 (Forms & Modals):
- "Dispute Finding" button on `QMSAuditReportDetailPage` — only visible to auditee role
- "Resolve Dispute / Amend" button — only visible to TL role after dispute is raised
- On dispute: status → `'disputed'`; on TL amendment/deletion: TL can edit the `nc_description` or delete the NC; after resolution the signing flow resumes

---

## 5. Non-Conformance Monthly Monitoring — MISSING

### SRS Requirement (4.11.1.4 req 14)
- "RMQAU shall monitor closure status of corrective actions **monthly** and report to Commission **quarterly**"
- This implies both a monthly review view AND the quarterly rollup

### What the Plan Has
- `NonConformancesPage` — list with `closure_status`, `target_closure_date` ✅
- `QPR` workflow — quarterly submission ✅

### What Is Missing ❌
1. **No "overdue NCs" indicator** — no visual flag when `target_closure_date` is passed and `closure_status !== 'closed'`
2. **No monthly summary/report** — no page or section showing month-by-month NC closure progress
3. **No "last reviewed" date field** on `NonConformance` entity
4. **No filter/view for "open NCs older than X days"** or grouped by month

### Resolution Required
Add to §4 (Core UI – List Pages) for `NonConformancesPage`:
- Status badge for overdue NCs: if `target_closure_date < today && closure_status !== 'closed'`, show `variant="destructive"` badge labeled "Overdue"
- Filter chips: "All", "Open", "Overdue", "Closed"

Add to §5 (Detail Pages) or suggest as a card in `RiskDashboardPage`:
- "NC Closure Summary" card showing open/overdue/closed counts

---

## 6. Risk Awareness Session Categorization — UNDOCUMENTED

### SRS Requirement (4.11.1.1 req 1)
- "The system shall enable RMQAU to conduct awareness sessions for Risk Champions, Risk Owners, and staff on Risk Management Principles and processes, including risk identification"

### What the Plan Has
- `RiskMeetingsPage` with `RiskMeeting.meeting_type: string` field ✅

### What Is Missing ❌
1. **`meeting_type` enum values are not defined** in the plan — the SRS requires distinct categories; without documented values, this is open to mis-implementation
2. **Audience tracking** — SRS says sessions target "Risk Champions, Risk Owners, AND staff" — `RiskMeeting` has no `audience_type` or `target_attendees` field
3. **`RiskMeetings` is entirely disconnected from `DeptRiskRegister`** — the SRS process (FCC_SBP_RMQA_03 step 1) says RC sends notification to directorate staff BEFORE the risk assessment meeting; the plan shows no link between a `RiskMeeting` and a `DeptRiskRegister`

### Resolution Required
Add to §3.3 (TypeScript types) the `meeting_type` enum:
```ts
export type RiskMeetingType =
  | 'awareness_session'    // SRS 4.11.1.1 req 1
  | 'risk_review'          // FCC_SBP_RMQA_03 step 2
  | 'irr_workshop'         // FCC_SBP_RMQA_04 step 1-3
  | 'management_review'    // QPR / RTAP management discussion
  | 'other';
```

Add to §4 (List Pages) for `RiskMeetingsPage`:
- Filter by meeting type
- Show audience/directorate column

Add linkage note to `DeptRiskRegisterDetailPage`:
- Optional "Linked Risk Meeting" field shown in the register detail header (read-only reference)

---

## 7. RTAP "Send Reminder to RCs" Action — MISSING

### SRS Requirement (FCC_SBP_RMQA_05 step 1)
- "Risk Management Officer (RMO) sends email to Risk Champions reminding them to submit implementation status of proposed controls"

### What the Plan Has
- `RTAPDetailPage` with RTAP Items section ✅
- RTAP item `implementation_status` field visible to RC ✅

### What Is Missing ❌
1. **No "Send Reminder" button** on `RTAPDetailPage` — RMO cannot trigger a reminder notification to all RCs from the UI
2. **No backend endpoint documented** for triggering this notification — the plan's API path constants do not include a `POST /risk/rtap/:id/send-reminder/` endpoint, even though the backend is 100% implemented
3. **No success toast or confirmation** for the reminder action

### Resolution Required
Add to §3.1 (API Paths):
```ts
rtapSendReminder:  'risk/rtap/',   // POST /risk/rtap/:id/send-reminder/
```

Add to §5 (Detail Pages) for `RTAPDetailPage` header buttons:
```tsx
{canManageRTAP && (
  <Button variant="outline" onClick={handleSendReminder} disabled={sendReminderMutation.isPending}>
    <Bell className="mr-2 h-4 w-4" />
    Send Reminder to RCs
  </Button>
)}
```
- Only visible to users with `grc:rtap:manage` permission
- Success toast: `toast.success('Reminders sent', { description: 'All Risk Champions have been notified.' })`

---

## 8. IRR Workshop Notification Actions — MISSING

### SRS Requirement (FCC_SBP_RMQA_04 steps 1–2)
- Step 1: "RMQAM sends email to Director/Unit Manager/Zonal In-Charge requesting permission for RC attendance"
- Step 2: "RMO sends notification to RCs of workshop date, time, and venue"

### What the Plan Has
- `InstitutionalRiskDetailPage` with entries and `IRRActivityReportsSection` ✅

### What Is Missing ❌
1. **No "Notify Directors" button** on `InstitutionalRiskDetailPage` — RMQAM cannot trigger permission requests from the UI
2. **No "Notify RCs of Workshop" button** — RMO cannot send workshop notifications from the UI
3. **No endpoint documented** for these notification triggers
4. **No `workshop_date`, `workshop_venue` fields** on `InstitutionalRiskRegister` — if notifications are sent, the workshop details need to be stored on the IRR

### Resolution Required
Add to §3.1 (API Paths):
```ts
irrNotifyDirectors: 'risk/institutional-registers/',   // POST /:id/notify-directors/
irrNotifyRCs:       'risk/institutional-registers/',   // POST /:id/notify-rcs/
```

Add to §5 (Detail Pages) for `InstitutionalRiskRegisterDetailPage`:
- Header button "Notify Directors" (visible when `status === 'draft'`, requires `canManageIRR`)
- Header button "Notify RCs of Workshop" (visible after directors have been notified, requires `canManageIRR`)
- A read-only "Workshop Date" + "Workshop Venue" info row in the detail card

---

## 9. One-Active-RC-Per-Unit Rule — NOT VISIBLE IN UI

### SRS Requirement (FCC_SBP_RMQA_01 Exception)
- "Each Directorate/Unit/Zone must have only one active RC at a time"
- "One RC can coordinate more than one Unit"

### What the Plan Has
- `RiskChampionsPage` list ✅
- `directorate_unit_zone` field shown in the table ✅

### What Is Missing ❌
1. **No uniqueness validation** in `CreateRiskChampionDialog` — the form doesn't check if an active RC already exists for the selected directorate/unit/zone before submitting
2. **No UI enforcement** when creating a new champion for a unit that already has one — the error comes from the backend (409 Conflict) but the plan doesn't document the inline error message for this specific case
3. **No visual indicator** on `RiskChampionsPage` grouping by directorate to make it obvious which units have active RCs

### Resolution Required
Add to §6 (Forms & Modals), `CreateRiskChampionDialog` validation:
```ts
// submit-time guard (before API call):
const existingActive = riskChampions.find(
  rc => rc.directorate_unit_zone_id === selectedUnitId && rc.is_active
);
if (existingActive) {
  toast.error('This unit already has an active Risk Champion. Deactivate the existing one first.');
  return;
}
```

Add to §8.2 (Error Toasts) the specific 409 conflict message:
```ts
// RC uniqueness conflict:
case 409:
  toast.error('Active RC already exists', {
    description: 'This Directorate/Unit/Zone already has an active Risk Champion.',
  });
```

---

## 10. Nominee Qualifications / Experience Fields — MISSING

### SRS Requirement (4.11.1.2 req 3)
- "The recommendation process shall include capturing relevant details such as the nominee's qualifications and experience"
- Data Requirements: "nominee qualifications and experience" (both RC and QA)

### What the Plan Has
- `RiskChampionFormData`: `nominee_user_id`, `directorate_unit_zone_id`, `notes?` ✅
- `QualityAuditorFormData`: `nominee_user_id`, `directorate_unit_zone_id`, `notes?` ✅

### What Is Missing ❌
1. **`notes` field is not documented** as covering qualifications/experience — a plain text `notes` field might not be sufficient; the SRS intent is structured qualification capture
2. **No `qualifications` or `experience_summary` field** in either `RiskChampionFormData` or the QA equivalent

### Resolution Required
Clarify in the plan that `notes` = "qualifications and experience summary" (free-text is acceptable per SRS intent). Add a placeholder label to the form:
```tsx
<FormItem>
  <FormLabel>Qualifications & Experience</FormLabel>
  <FormControl>
    <Textarea placeholder="Summarize nominee's risk management qualifications and relevant experience..." />
  </FormControl>
</FormItem>
```
Rename `notes` → `qualifications_and_experience` in form field name for clarity.

---

## 11. QMS Plan — Non-Disclosure Form Signing — MISSING

### SRS Requirement (FCC_SBP_RMQA_07 step 11)
- "Non-disclosure form will be signed and handed over to the auditee while TL retains the copy"
- Data Requirements: `signed non-disclosure forms`

### What the Plan Has
- `QMSPlanDetailPage` with team assignments and timetable ✅
- `QMSAuditMeeting` (entry/exit meeting records) ✅

### What Is Missing ❌
1. **No `non_disclosure_signed` field** in `QMSAuditMeeting` or on the plan itself
2. **No "Upload NDA" or "Mark NDA as Signed" action** in `QMSPlanDetailPage`
3. **No document UUID field** for storing the signed NDA document

### Resolution Required
Add to `QMSAuditMeeting` type:
```ts
export interface QMSAuditMeeting {
  id: string;
  qms_plan: string;
  meeting_type: string;   // 'opening' | 'closing' | 'pre_audit'
  scheduled_date: string;
  venue: string;
  timetable_agreed?: boolean;                   // entry meeting specific
  non_disclosure_signed?: boolean;              // entry meeting specific
  non_disclosure_doc_uuid?: string;             // document link
  notes?: string;
  created_at: string;
}
```

Add a `QMSAuditMeetingsSection` subsection in `QMSPlanDetailPage` that shows:
- Entry meeting: agreed timetable checkbox + NDA status badge
- Exit meeting: outcome notes

---

## 12. MRM Directives Tracking — NOT DESCRIBED

### SRS Requirement (FCC_SBP_RMQA_07 step 19; 4.11.1.4 req 11–13)
- "RMQAM receives all directives from Management Review Meeting (MRM) and communicates to respective auditee and responsible party"
- "Track implementation of NC corrective actions and improvements"

### What the Plan Has
- `QMSReportStatus` includes `'presented_at_mrm'` and `'directives_received'` values ✅
- `NonConformancesPage` shows `closure_status` ✅

### What Is Missing ❌
1. **No "MRM Directives" section in `QMSAuditReportDetailPage`** — after status advances to `presented_at_mrm`, there is no UI section to record the specific directives
2. **No `mrm_directives` or `mrm_notes` field** in `QMSAuditReport` type or form
3. **No "Communicate to Auditees" button** after directives are received — RMQAM needs to trigger notification of directives to respective directorates
4. **No tracking of which NC items were addressed** per MRM directive

### Resolution Required
Add to `QMSAuditReport` TypeScript interface:
```ts
mrm_directives?: string;            // free-text or structured directives from MRM
mrm_directives_communicated_at?: string;  // timestamp when directives were sent to auditees
```

Add to `QMSAuditReportDetailPage` §5:
- **"MRM Directives" card section** — visible when `status === 'presented_at_mrm' || status === 'directives_received'`
- "Record Directives" textarea + "Mark as Communicated" button (RMQAM role)
- After "Mark as Communicated": success toast + status advances to `'directives_received'`

---

## 13. QA Appointment — Nominee Qualifications & Training pre-check — UNDOCUMENTED

### SRS Requirement (FCC_SBP_RMQA_06 Pre-Conditions)
- "QA must pass ISO 9001:2015 audit examination" — appointment letter cannot be issued unless exam is passed
- Pre-condition: `exam_score >= 75` AND `attempt_number <= 2`

### What the Plan Has
- `QAStatus` includes `'exam_pending'`, `'passed'`, `'failed'` ✅
- `QualityAuditor.exam_score` field ✅

### What Is Missing ❌
1. **No pre-condition gate for `CreateQAAppointmentDialog`** — the plan does not document that this dialog must only be accessible when `qualityAuditor.status === 'passed'`
2. **"Create Appointment" button should be hidden** when auditor status is not `'passed'` — this is equivalent to the triple-gate submit pattern already used for workflow, but for appointment creation

### Resolution Required
Add to §7 (RBAC Enforcement), Button Visibility table:
```
| QualityAuditorDetailPage | "Create QA Appointment" | canManageQualityAuditors | auditor.status === 'passed' |
```

Add to §6 (Forms), `CreateQAAppointmentDialog` notes:
> This dialog is only accessible when `qualityAuditor.status === 'passed'`. The button in `QAAppointmentSection` must implement this status gate in addition to the permission check.

---

## 14. Risk Champion Nominee Qualification Form — Dispatch Tracking

### SRS Requirement (FCC_SBP_RMQA_01 Process Output)
- "Dispatched appointment letter" is the measurable outcome
- "Signed letters shall be dispatched to RC through the Registry Office"

### What the Plan Has
- `RCAppointment.appointment_letter_doc_uuid` for storing the signed letter ✅
- `toast.success('Risk Champion appointed', { description: 'Appointment letter has been dispatched.' })` ✅

### What Is Missing ❌
1. **No `dispatched_at` or `dispatch_reference` field** in `RCAppointment` — the SRS requires traceability of dispatch
2. **No "Mark as Dispatched" action** separate from "letter signed" — signing and dispatching are two distinct steps in the SRS process

### Resolution Required
Add to `RCAppointment` type:
```ts
dispatched_at?: string;
dispatch_reference?: string;
```

Add to `RCAppointmentSection` within `RiskChampionDetailPage`:
- After appointment letter is uploaded (signed), show "Mark as Dispatched" button
- Captures `dispatch_reference` (optional text input) and sets `dispatched_at`

Same pattern applies to `QAAppointment` (FCC_SBP_RMQA_06 Output: "Dispatched appointment letter").

---

## 15. Risk Assessment Sheet — Rework/Return Cycle — NOT IN PLAN

### SRS Requirement (FCC_SBP_RMQA_03 step 6)
- "If not approved, RMQAM through RMO shall submit the risk assessment sheet to RC for rework and resubmit"
- Data Requirements: `rejection reason`, `review comments`, `resubmission date`

### What the Plan Has
- `RASStatus` includes `'returned_for_rework'` ✅
- `RiskAssessmentSheetsPage` list with status badge ✅

### What Is Missing ❌
1. **No "Return for Rework" button** in the `RiskAssessmentSheetsPage` or a detail view — RMQAM cannot return a RAS with rejection reason from the UI
2. **No `rejection_reason` or `review_comments` field** in `RiskAssessmentSheet` type
3. **No resubmission action** — RC cannot "resubmit" a returned RAS; `RASStatus` has `'returned_for_rework'` but no workflow to transition back to `'submitted_to_rmqam'` from this state
4. **`RiskAssessmentSheetsPage` is list-only (no workflow, dialog-only edit)** — this makes it hard to add the rework→approval loop without a dedicated detail page or multi-step dialog

### Resolution Required
Add to `RiskAssessmentSheet` type:
```ts
review_comments?: string;      // RMQAM feedback when returning for rework
rejected_at?: string;          // timestamp of rejection
resubmitted_at?: string;       // timestamp of resubmission
```

Add to §6 (Forms & Modals) for `RiskAssessmentSheetViewDialog`:
- Show rejection reason in a yellow `<Alert>` when `status === 'returned_for_rework'`
- Show "Resubmit" button visible to the RC (requires `grc:risk_assessment:conduct` permission + status gate)

Add to §6 for RMQAM action in the dialog or a new action column in the table:
- "Return for Rework" button visible to `grc:risk_assessment:review` role when `status === 'submitted_to_rmqam'`

---

## 16. RTAP — Submission to Management / Risk & Governance Committee — 7-Day Rule

### SRS Requirement (FCC_SBP_RMQA_04 step 10; FCC_SBP_RMQA_05 step 10)
- "Submit to LSM for onward submission to Members of the Risk and Governance Committee **seven days before the date of the Meeting**"

### What the Plan Has
- RTAP and IRR workflow statuses cover `submitted_to_committee` ✅
- QPR also has `submitted_to_committee` status ✅

### What Is Missing ❌
1. **No `committee_meeting_date` field** on `RTAP`, `IRR`, or `QPR` — the 7-day submission window cannot be tracked without knowing the upcoming committee meeting date
2. **No validation** that the submission is at least 7 days before the committee meeting
3. **No warning indicator** if the planned submission is too late

### Resolution Required
Add `committee_meeting_date?: string` to `RTAP`, `InstitutionalRiskRegister`, and `QuarterlyPerformanceReport` types.

Add to §6 (Forms) for the "Submit to Committee" action:
```ts
// submit-time guard:
if (committeeDate) {
  const daysUntil = Math.floor((new Date(committeeDate).getTime() - Date.now()) / 86400000);
  if (daysUntil < 7) {
    toast.warning('Late submission warning', {
      description: `Committee meeting is in ${daysUntil} days. Submission should be at least 7 days before.`
    });
    // Don't block — warn only
  }
}
```

---

## 17. Submission to IAGO — Missing Governance Target

### SRS Requirement (4.11.1.1 req 14)
- "generate Quarterly Risk Management Implementation Report for submission to **Audit Committee and Internal Auditor General Office (IAGO)**"
- The QPR is submitted to TWO separate recipients: Audit Committee AND IAGO

### What the Plan Has
- QPR workflow has `submitted_to_committee` status ✅

### What Is Missing ❌
1. **No `submitted_to_iago` or `iago_submission_date` field** on `QuarterlyPerformanceReport`
2. **No "Submit to IAGO" action** separate from the committee submission
3. **No IAGO submission step** in the QPR workflow status values

### Resolution Required
Add to `QPRStatus`:
```ts
export type QPRStatus =
  | 'draft'
  | 'submitted_to_management' | 'management_reviewed'
  | 'submitted_to_committee' | 'committee_reviewed'
  | 'submitted_to_iago'             // NEW — parallel to committee submission
  | 'committee_directives_actioned'
  | 'submitted_to_commission';
```

Or alternatively add `iago_submission_date?: string` as a standalone field if the backend treats IAGO submission as a separate action rather than a workflow stage.

---

## 18. Risk Champion — Role Assignment Trigger — NOT DESCRIBED IN UI

### SRS Requirement (4.11.1.2 req 5)
- "Approval actions shall trigger the assignment of the risk champion role to the nominated individual"

### What the Plan Has
- RC Appointment workflow advances to `'appointed'` status ✅
- Backend handles role assignment via signal handlers (100% implemented) ✅

### What Is Missing ❌
1. **No UI acknowledgment** that the role has been assigned — after workflow completes/RC appointed, the UI does not confirm "Risk Champion role has been assigned to [user]"
2. **No visible indication on the RiskChampionDetailPage** that the user's system role has been updated

### Resolution Required
Add to §8 (Notifications) a specific success toast for the workflow completion on `RCAppointmentDetailPage`:
```ts
toast.success('Risk Champion Appointed', {
  description: `${champion.nominee_name} has been appointed and granted Risk Champion permissions.`
});
```

This would be triggered when `workflowStatus.workflow_completed_at` is set and the entity status transitions to `'appointed'` or `'active'`.

---

## 19. QMS Audit Meetings — entry/exit Meeting Types Not Documented

### SRS Requirement (FCC_SBP_RMQA_07 steps 9, 15)
- "Upon Audit Team arrival, RMQAM through TL will conduct an **entry meeting** with auditees"
- "TL presents full report to auditee during the **exit meeting**"
- "Exit meeting: Amendment or deletion of findings where justified"

### What the Plan Has
- `QMSAuditMeeting.meeting_type: string` with hint `'opening' | 'closing'` ✅

### What Is Missing ❌
1. **Ambiguous type values** — `'opening'` and `'closing'` are not SRS standard terms; the SRS uses `'entry'` and `'exit'`
2. **No `pre_audit`** meeting type — the SRS step 12 describes "TL and Audit Team conducts **Pre-Audit meeting**"
3. **No meeting-specific fields** to capture timetable agreement (entry), NDA signing (entry), or finding amendments (exit)
4. **No `QMSAuditMeetingsSection`** described in `QMSPlanDetailPage` — the API path `qms-plans/:id/audit-meetings/` exists but no UI component is defined

### Resolution Required
Update `QMSAuditMeeting.meeting_type` documented values:
```ts
type QMSMeetingType = 'pre_audit' | 'entry' | 'exit';
```

Add `QMSAuditMeetingsSection.tsx` to `§1.1` folder structure and describe in §5:
- Section appears on `QMSPlanDetailPage` between team assignments and timetable
- Shows three meeting cards: Pre-Audit, Entry (with NDA toggle), Exit (with outcome notes)

---

## 20. System Design Use Cases — "Generate Risk Report" — UNDESCRIBED

### SRS Requirement (§1.5.3.4 System Design)
- Use Cases list includes: "Generate risk report"
- "Track risk status"

### What the Plan Has
- `RiskDashboardPage` is missing entirely (see Gap #1)
- `QPR` covers quarterly reports ✅

### What Is Missing ❌
1. **No "Export to PDF/Excel" feature** described anywhere for Risk Reports or QPR
2. **No "print view"** for IRR or RTAP documents
3. **No report generation endpoint** in the API paths (only `risk/dashboard/` for summary)

### Resolution Required (Low Priority)
If the backend has a dedicated report export endpoint, add to §3.1 (API Paths) and §3.2 (Service Functions). If not, document as out-of-scope for frontend Phase I but flag as a future enhancement.

---

## 21. RC/QA Nomination — RMQAM Initial Request to Heads Not Described

### SRS Requirement (FCC_SBP_RMQA_01 Step 1 + Basic Requirements)
- "RMQAM submits a written request to Directors/Units/Zone to propose the name of the RC"
- Basic Req: "The system shall allow Heads of Directorates/Units/Zones to: Receive official communication requesting nomination of an RC. Propose and submit the name of a designated RC."

### What the Plan Has
- `CreateRiskChampionDialog` — creates an RC record directly ✅
- `RCStatus` includes `pending` and `nominated` values ✅

### What Is Missing ❌
1. **No "Send Nomination Request" action** — RMQAM cannot trigger an official request to Heads through the UI; the two-phase process (RMQAM requests → Head proposes) is absent
2. **No Head-facing nomination form** — the plan creates the RC directly from RMQAM's side; there is no path for a Head of Directorate to view a pending request and submit their nominee name
3. **`CreateRiskChampionDialog` conflates nomination request with champion creation** — the SRS requires RMQAM to first request, and Heads to respond; the plan skips the request step
4. **Same issue applies to QA**: FCC_SBP_RMQA_06 follows the same pattern ("RMQAM submits written request to Directors/Units/Zone to propose name of Quality Champion")

### Resolution Required
Add to §6 (Forms & Modals), pre-nomination action:
- "Send Nomination Request" button on `RiskChampionsPage` (visible to `canManageRiskChampions`) that triggers a notification/request to selected Directorates
- Alternatively, document that this is handled offline and `CreateRiskChampionDialog` records the Heads' response (acknowledging the gap in process automation)

If the backend has a `POST /risk/champions/nomination-requests/` endpoint, add to §3.1 API Paths. Otherwise document as deferred automation.

---

## 22. RTAP Item — RMO Return-for-Rework Not Documented

### SRS Requirement (FCC_SBP_RMQA_05 Step 3)
- "If the status [of RTAP item implementation reports] are not in order after review, RMO sends back to RC for rework and resubmission"

### What the Plan Has
- `RTAPItemStatus = 'not_started' | 'in_progress' | 'completed'` ✅
- `RTAPItemsSection` with status display ✅

### What Is Missing ❌
1. **No `returned_for_rework` value** in `RTAPItemStatus` — RMO cannot mark an item as "returned" to RC
2. **No "Return for Rework" button** in `RTAPItemsSection` for RMO role
3. **No `review_comments` or `rejection_reason` field** on `RTAPItem` type — RMO cannot attach feedback when returning
4. **No Resubmit action** — RC cannot acknowledge the return and resubmit with corrections

### Resolution Required
Add to §3.3 (TypeScript types):
```ts
export type RTAPItemStatus = 'not_started' | 'in_progress' | 'completed' | 'returned_for_rework';

// Add to RTAPItem interface:
review_comments?: string;       // RMO feedback when returning
returned_at?: string;           // timestamp of return
resubmitted_at?: string;        // timestamp of resubmission
```

Add to §5 (`RTAPDetailPage`) in the `RTAPItemsSection`:
- "Return for Rework" button on each item row — visible to `canManageRTAP` (RMO role) when `status === 'in_progress'`
- Opens a dialog prompting for `review_comments`; sets status → `returned_for_rework`
- RC "Resubmit" button visible when `status === 'returned_for_rework'` and `canRespondRTAP` — resets status to `in_progress`

---

## 23. QA Training Session — RMQAM Approval Step Not Documented

### SRS Requirement (FCC_SBP_RMQA_06 Step 3)
- "PRMO seeks for trainer, then advises RMQAM the date, time and venue. Upon RMQAM grants approval, PRMO notifies the trainees the approved date, venue and time"

### What the Plan Has
- `QATrainingSession.approval_status: string` field ✅
- `QATrainingDetailPage` as a "non-workflow detail" hosting attendees section ✅

### What Is Missing ❌
1. **No "Approve Training" action** documented for RMQAM — `approval_status` is a plain string field with no documented approve/reject actions
2. **No "Notify Trainees" button** that is only enabled after training is approved
3. **`QATrainingDetailPage` is marked "non-workflow"** — but RMQAM approval is a mandatory step before trainees can be notified; this warrants at least a status-gate approve/reject action
4. **No `approval_status` enum values defined** — `string` type is too loose; what values are valid (`pending_approval | approved | rejected`)? Undocumented

### Resolution Required
Define `QATrainingApprovalStatus` enum:
```ts
export type QATrainingApprovalStatus = 'pending_approval' | 'approved' | 'rejected';
```

Update `QATrainingSession.approval_status` to `approval_status: QATrainingApprovalStatus`.

Add to §5 (`QATrainingDetailPage`) header buttons:
- "Approve Training" button — visible to `canManageQATraining` (RMQAM role) when `approval_status === 'pending_approval'`; sets → `approved`
- "Reject Training" button — same guard; sets → `rejected` with optional `rejection_notes`
- "Notify Trainees" button — visible only when `approval_status === 'approved'`; triggers notification with date/venue details

Add to §4 (`QATrainingPage` list) status badge for `approval_status`.

---

## 24. Post-Approval IRR/RTAP Distribution to Directorates — Not Described

### SRS Requirement (4.11.1.1 Req 12)
- "Upon Commission approval, the system shall enable RMQAU to submit the Risk Register and Risk Treatment Action Plan to respective Directorates/Sections/Units/Zones through Risk Champions for implementation"

### What the Plan Has
- `IRRStatus` includes `approved` as a terminal status ✅
- `RTAPStatus` includes `approved` as a terminal status ✅

### What Is Missing ❌
1. **No "Distribute to Directorates" button** on `InstitutionalRiskDetailPage` after `status === 'approved'`
2. **No "Distribute RTAP" button** on `RTAPDetailPage` after `status === 'approved'`
3. **No notification mechanism described** for RC to receive the approved IRR + RTAP
4. **No `distributed_at` or `distribution_status` field** on `InstitutionalRiskRegister` or `RTAP`

### Resolution Required
Add to `InstitutionalRiskRegister` and `RTAP` TypeScript interfaces:
```ts
distributed_to_directorates_at?: string;
distribution_reference?: string;
```

Add to §5 (`InstitutionalRiskDetailPage` and `RTAPDetailPage`) header buttons:
- "Distribute to RCs" button — visible to `canManageIRR` / `canManageRTAP` when `status === 'approved'` and `distributed_to_directorates_at` is null
- On click: triggers backend distribution action; success toast:
  ```ts
  toast.success('Distributed to Risk Champions', {
    description: 'The approved register and RTAP have been forwarded to all Risk Champions for implementation.'
  });
  ```

Add to §3.1 (API Paths):
```ts
irrDistribute:  'risk/institutional-registers/',   // POST /:id/distribute/
rtapDistribute: 'risk/rtap/',                       // POST /:id/distribute/
```

---

## 25. QMS Audit Report — RMQAU Return-for-Revision Cycle Missing

### SRS Requirement (4.11.1.4 Req 10)
- "In case of recommendations, the system shall allow the Lead Auditor to incorporate them and resubmit the report to RMQAU"

### What the Plan Has
- `QMSReportStatus = 'draft' | 'ncs_presented' | 'exit_meeting_held' | 'signed' | 'submitted_to_rmqam' | 'presented_at_mrm' | 'directives_received'` ✅

### What Is Missing ❌
1. **No `returned_for_revision` status** in `QMSReportStatus` — after TL submits to RMQAU (`submitted_to_rmqam`), RMQAU can return it with recommendations but there is no status to represent this
2. **No "Return with Recommendations" action** for RMQAU on `QMSAuditReportDetailPage` when `status === 'submitted_to_rmqam'`
3. **No "Incorporate & Resubmit" action** for TL when report is returned
4. **No `rmqam_review_comments` field** on `QMSAuditReport` type to store RMQAU's recommendations

### Resolution Required
Update `QMSReportStatus`:
```ts
export type QMSReportStatus =
  | 'draft' | 'ncs_presented' | 'exit_meeting_held' | 'signed'
  | 'submitted_to_rmqam'
  | 'returned_for_revision'    // NEW — RMQAU returned with recommendations
  | 'resubmitted'              // NEW — TL incorporated feedback and resubmitted
  | 'presented_at_mrm' | 'directives_received';
```

Add to `QMSAuditReport` interface:
```ts
rmqam_review_comments?: string;
returned_for_revision_at?: string;
resubmitted_at?: string;
```

Add to §5 (`QMSAuditReportDetailPage`):
- "Return with Recommendations" button — visible to `canManageQMSReports` (RMQAM role) when `status === 'submitted_to_rmqam'`; opens dialog for `rmqam_review_comments`; sets status → `returned_for_revision`
- "Incorporate & Resubmit" button — visible to `canManageQMSReports` (TL role) when `status === 'returned_for_revision'`; sets status → `resubmitted`
- Show RMQAM review comments in a yellow `<Alert>` when `status === 'returned_for_revision'`

---

## 26. QMS Audit Report — Audit Committee + Commission Adoption Steps Missing

### SRS Requirement (4.11.1.4 Req 12)
- "Upon Management discussion, the system shall enable RMQAU to present the report to the Audit Committee for deliberations and recommendation to the Commission for adoption"

### What the Plan Has
- `QMSReportStatus` ends at `directives_received` after MRM stage ✅

### What Is Missing ❌
1. **No `submitted_to_audit_committee` status** — the audit committee presentation step is entirely absent from `QMSReportStatus`
2. **No `adopted_by_commission` or `commission_approved` status** — Commission adoption is not in the status flow
3. **No "Submit to Audit Committee" button** on `QMSAuditReportDetailPage`
4. **No "Commission Adoption" action** described

### Resolution Required
Update `QMSReportStatus`:
```ts
export type QMSReportStatus =
  | 'draft' | 'ncs_presented' | 'exit_meeting_held' | 'signed'
  | 'submitted_to_rmqam' | 'returned_for_revision' | 'resubmitted'
  | 'presented_at_mrm'
  | 'directives_received'
  | 'submitted_to_audit_committee'    // NEW
  | 'audit_committee_reviewed'        // NEW
  | 'adopted_by_commission';          // NEW
```

Add to §5 (`QMSAuditReportDetailPage`) header buttons:
- "Submit to Audit Committee" — visible to `canManageQMSReports` when `status === 'directives_received'`; sets → `submitted_to_audit_committee`
- "Mark Commission Adoption" — visible when `status === 'audit_committee_reviewed'`; sets → `adopted_by_commission`

Update `qmsReportStatusColors` map in §4.5 to include the 3 new status values.

---

## 27. Risk Meeting View Dialog — Meeting Minutes and Attendance Recording Undocumented

### SRS Requirement (DRR Basic Requirements)
- "The system/process shall support: Recording attendance and meeting outcomes. Capturing consolidated risks discussed and agreed upon."
- Data Requirements: "Meeting minutes, Attendance list, Consolidated list of identified risks"

### What the Plan Has
- `RiskMeeting.notes?: string` field ✅
- `meetingAttendance` API path constant ✅
- `MeetingAttendance` TypeScript interface ✅

### What Is Missing ❌
1. **`<RiskMeetingViewDialog>` content is completely undocumented** — the plan mentions it exists (§2.3) but never describes its fields, sections, or actions
2. **No `meeting_minutes` or `outcomes` field** on `RiskMeeting` (the `notes` field is insufficient for structured minutes capture)
3. **`<MeetingAttendanceSection>` not described** — the `meetingAttendance` API path exists, but no UI component is documented to record/display attendance within the dialog or detail view
4. **No "Record Outcome / Consolidated Risks" section** — the DRR process requires the meeting to produce a "consolidated list of identified risks"; this output is not captured anywhere in the UI

### Resolution Required
Document `<RiskMeetingViewDialog>` content in §2.3 (or add a dedicated note in §6 / §4):

Show within the dialog:
- Meeting details (type, date, venue, directorate)
- `meeting_minutes` field (textarea, editable when `canManageRiskMeetings`)
- Attendance sub-table: list of attendees with `attended: boolean` toggle

Add to `RiskMeeting` interface:
```ts
meeting_minutes?: string;
consolidated_risk_summary?: string;    // outcome: consolidted risks discussed
```

Add to §6 (Forms & Modals):
- `RiskMeetingViewDialog` content specification with all displayed fields and edit actions

---

## 28. RAS Status Transition Actions — Submit-to-Head and Head-Endorsement Undocumented

### SRS Requirement (FCC_SBP_RMQA_03 Steps 3–5)
- Step 3: RC coordinates assessment using the designated risk assessment sheet
- Step 4: RAS submitted to Director/Unit Manager/Zonal In-Charge for review and action
- Step 5: Upon agreement with head, RC forwards RAS to RMQAM

### What the Plan Has
- `RASStatus = 'draft' | 'submitted_to_head' | 'head_endorsed' | 'submitted_to_rmqam' | 'approved' | 'returned_for_rework'` ✅ (5 statuses representing the full lifecycle)
- `RiskAssessmentSheetsPage` list ✅

### What Is Missing ❌
1. **No documented UI actions** for transitioning `draft → submitted_to_head` (RC submits to Head)
2. **No documented UI action** for `submitted_to_head → head_endorsed` (Head endorses — who triggers this?)
3. **No documented UI action** for `head_endorsed → submitted_to_rmqam` (RC forwards to RMQAM)
4. **`RiskAssessmentSheetsPage` is list-only** (dialog-based per §2.3) — the status flow actions must live inside `<RiskAssessmentSheetViewDialog>`, but this dialog's content is never described in the plan
5. **No role-gated buttons** described for each status transition (RC can submit to Head; Head can endorse; RC can forward to RMQAM)

### Resolution Required
Add comprehensive documentation of `<RiskAssessmentSheetViewDialog>` in §6 (Forms & Modals) or as a dedicated subsection:

```
Status transition action buttons (inside RiskAssessmentSheetViewDialog):
| Current Status       | Button Label            | Permission                    | Result Status          |
|----------------------|-------------------------|-------------------------------|------------------------|
| draft                | Submit to Head          | canConductRiskAssessments (RC)| submitted_to_head      |
| submitted_to_head    | Endorse Assessment      | canReviewRiskAssessments (Head)| head_endorsed          |
| head_endorsed        | Forward to RMQAM        | canConductRiskAssessments (RC)| submitted_to_rmqam     |
| submitted_to_rmqam   | Approve                 | canReviewRiskAssessments       | approved               |
| submitted_to_rmqam   | Return for Rework       | canReviewRiskAssessments       | returned_for_rework    |
| returned_for_rework  | Resubmit                | canConductRiskAssessments (RC)| submitted_to_head      |
```

Add to §8 (Notifications):
```ts
// On endorsement:
toast.success('Risk assessment sheet endorsed', { description: 'Forwarding to RMQAM.' });
// On RMQAM approval:
toast.success('Risk assessment sheet approved', { description: 'Added to approved register.' });
```

---

## 29. Non-Conformance — Finding Type Not Differentiated (NC vs. Area for Improvement)

### SRS Requirement (FCC_SBP_RMQA_07 Steps 13, 15; 4.11.1.4 Req 9, 11–13)
- "QA conducts the audit and document the Non-Conformances (NCs) **and Areas for Improvement**"
- "TL presents full report ... consolidates NCs **and Areas for Improvement**"
- 4.11.1.4 Req 9: "Quality Auditors shall prepare the Quality Audit Report" covering both NCs and improvement areas
- 4.11.1.4 Req 11: "RMQAU shall present the Quality Audit Report findings (Non-Conformances) and **proposed action plans** to Management"

### What the Plan Has
- `NonConformance` interface with `nc_description`, `iso_clause_violated`, `closure_status` ✅
- `NonConformancesPage` with list and view dialog ✅

### What Is Missing ❌
1. **No `finding_type` field** on `NonConformance` — the SRS consistently distinguishes between "Non-Conformances" and "Areas for Improvement (OFI/Opportunity for Improvement)"; the current type models only NCs
2. **`NonConformancesPage` shows NCs only** — Areas for Improvement (which may not require corrective action closure) are not tracked
3. **No separate column/filter** to distinguish NCs from Observations or OFIs
4. **Severity/classification** is not captured — ISO 9001:2015 audit typically distinguishes Minor NC, Major NC, and OFI

### Resolution Required
Update `NonConformance` TypeScript interface:
```ts
export type NCFindingType = 'major_nc' | 'minor_nc' | 'observation' | 'area_for_improvement';

export interface NonConformance {
  // ... existing fields ...
  finding_type: NCFindingType;    // NEW — required field
  // ...
}
```

Update `NonConformanceFormData` to include `finding_type: NCFindingType` as a required field.

Add to §6 (`CreateNonConformanceDialog`) form fields table:
```
| Finding Type | Select (required) | z.enum(['major_nc','minor_nc','observation','area_for_improvement']) |
```

Add to §4.4 (`NonConformancesPage` columns): `Finding Type` column after `ISO Clause`.

Add filter chip for `finding_type` in §4.6 (`NonConformancesPage` filters).

Update `ncStatusColors` map to handle that "Area for Improvement" items may not go through `action_assigned → in_progress → closed` in the same way.

---

## Complete Gap Priority Matrix

| # | Gap | Impact | Priority |
|---|-----|--------|----------|
| 1 | Risk Dashboard Page missing entirely | HIGH — key SRS requirement unimplemented | P1 |
| 2 | Comparative analysis view not rendered | HIGH — SRS trend analysis requirement | P1 |
| 3 | QA exam threshold (75%) & re-sit tracking | HIGH — core QA appointment process | P1 |
| 4 | NC dispute / finding amendment flow | HIGH — core QMS audit process | P1 |
| 5 | NC monthly monitoring / overdue indicator | MEDIUM — monitoring requirement | P2 |
| 6 | Risk meeting type enum & DRR linkage | MEDIUM — awareness session categorization | P2 |
| 7 | RTAP "Send Reminder to RCs" button | MEDIUM — RMQAM operational action | P2 |
| 8 | IRR workshop notification buttons | MEDIUM — RMQAM communication flow | P2 |
| 9 | One-active-RC-per-unit UI enforcement | MEDIUM — SRS business rule | P2 |
| 10 | Nominee qualifications form field naming | LOW — field label clarity | P3 |
| 11 | QMS Plan — NDA signing tracking | MEDIUM — audit process step | P2 |
| 12 | MRM directives section in QMS Report | MEDIUM — audit outcome tracking | P2 |
| 13 | QA appointment pre-condition gate | MEDIUM — status-gated button | P2 |
| 14 | RC / QA dispatch tracking (`dispatched_at`) | LOW — traceability field | P3 |
| 15 | RAS rework/return cycle | HIGH — RMQAM review loop | P1 |
| 16 | 7-day committee submission warning | LOW — warning/reminder only | P3 |
| 17 | QPR submission to IAGO | MEDIUM — missing governance target | P2 |
| 18 | Role assignment UI acknowledgment | LOW — informational only | P3 |
| 19 | QMS meeting types (pre_audit/entry/exit) | MEDIUM — audit meeting categorization | P2 |
| 20 | Export/Print for risk reports | LOW — future enhancement | P4 |
| 21 | RC/QA Nomination request flow — RMQAM initial request to Heads | MEDIUM — nomination two-phase process absent | P2 |
| 22 | RTAP Item — RMO return-for-rework not documented | MEDIUM — mirrors RAS rework gap for RTAP items | P2 |
| 23 | QA Training — RMQAM approval step not workflow-backed | MEDIUM — mandatory approval step undocumented | P2 |
| 24 | Post-approval IRR/RTAP distribution to Directorates | MEDIUM — key post-approval action (Req 12) | P2 |
| 25 | QMS Audit Report — RMQAU return-for-revision cycle missing | MEDIUM — report revision loop (Req 10) | P2 |
| 26 | QMS Audit Report — Audit Committee + Commission adoption steps missing | MEDIUM — governance escalation path (Req 12) | P2 |
| 27 | Risk Meeting — minutes + attendance recording undocumented | LOW — DRR data requirements for meetings | P3 |
| 28 | RAS status transition actions (submit-to-head, head-endorse) undocumented | HIGH — multi-step status flow has no UI actions | P1 |
| 29 | NC finding type not differentiated (NC vs Area for Improvement) | MEDIUM — ISO audit classification absent | P2 |

---

## What the Plan Covers Well ✅

The following SRS areas are comprehensively addressed in the Frontend Plan:

| Area | Plan Section(s) |
|------|----------------|
| All entity routes and page structure | §1, §2 |
| Complete TypeScript types for all entities | §3.3 |
| All workflow entities with `EmbeddedWorkflowConsole` | §5, §11 |
| Risk Assessment Sheet CRUD with all SRS data fields | §3.3, §4 |
| RTAP with items and quarterly updates | §3.1, §5 |
| QPR with implementation rate fields | §3.3, §5 |
| QMS Audit Program + Plan approval workflows | §5, §11.1 |
| QMS Checklists with `iso_clauses` and `checklist_items` | §3.3 |
| QMS Audit Report with TL + Auditee signing | §3.2.2, §7 |
| Non-Conformance with `closure_status` and respond action | §4, §7.3 |
| RBAC enforcement with triple-gate pattern | §7 |
| Zod validation for all forms | §6 |
| QA conflict-of-interest guard | §6.7 |
| 10-day notification rule for QMS audit plans (Rule E.7) | §6.7 |
| QMS Audit Plan requiring approved QMS Program | §6.7 |
| File upload (appointment letters as FormData) | §6 |
| Toast notifications for all mutations | §8 |
| Polling (workflow status refetch every 30s) | §9, §11 |
| Full implementation order (Phases A–I) | §13 |

---

## Recommended Plan Updates — Section by Section

The following sections need to be updated to resolve the gaps above:

| Plan Section | Updates Required |
|-------------|-----------------|
| §1.1 Folder Structure | Add `RiskDashboardPage.tsx` |
| §1.2 Routing | Add `/risk-dashboard` route |
| §1.3 Sidebar | Add "Risk Dashboard" menu item |
| §3.1 API Paths | Add `rtapSendReminder`, `irrNotifyDirectors`, `irrNotifyRCs`, `irrDistribute`, `rtapDistribute` |
| §3.3 Types | Update `QATrainingAttendee` with exam fields; add `dispatched_at` to RC/QA Appointment; add `review_comments` + `returned_at` to RAS and RTAPItem; add `mrm_directives` to QMSAuditReport; update `NCStatus` with `'disputed'`; update `NCFindingType` enum; update `QMSAuditMeeting` with NDA fields; update `QPRStatus` with IAGO step; add `QMSReportStatus` new values (returned_for_revision, submitted_to_audit_committee, adopted_by_commission); add `meeting_minutes` to RiskMeeting; add `distributed_to_directorates_at` to IRR and RTAP; add `QATrainingApprovalStatus` enum; add `finding_type` to NonConformance |
| §4 List Pages | Add overdue badge + filter chips for `NonConformancesPage`; add `finding_type` column + filter for `NonConformancesPage`; add NC count to dashboard; add approval_status badge to `QATrainingPage` |
| §5 Detail Pages | Add `RiskDashboardPage` spec; add "Send Reminder" to RTAP; add "Notify Directors/RCs" + "Distribute to RCs" to IRR; add "Distribute RTAP" to RTAP; add MRM directives section to QMS Report; add RMQAU return-for-revision action + status display to QMS Report; add "Submit to Audit Committee" + "Commission Adoption" to QMS Report; add `QMSAuditMeetingsSection` to QMS Plan; add "Approve/Reject Training" + "Notify Trainees" to QATrainingDetailPage |
| §6 Forms | Add 75%-threshold validation for QA exam; add "Return for Rework" action + resubmission for RAS and RTAP items; add QA appointment status pre-check; add committee date 7-day warning; document `one_active_rc` uniqueness guard; document `<RiskAssessmentSheetViewDialog>` content + all status transition buttons; document `<RiskMeetingViewDialog>` content + attendance sub-table; add `finding_type` to `CreateNonConformanceDialog`; document RMQAM nomination request flow |
| §7 RBAC | Add QA appointment status gate; add NC dispute/amend button visibility; add `QATrainingApprovalStatus` gated buttons for RMQAM; add post-approval distribution buttons |
| §8 Notifications | Add role-assignment confirmation toast; add specific 409 message for RC uniqueness; add RAS status transition toasts for each step |
| §13 Impl Order | Add `RiskDashboardPage` to Phase D; add Gap #7/8/21/24 notification/distribution actions to Phase F; add Gap #22/23/25/26/28/29 to respective phases |

---

*End of Gap Analysis — Risk Management & Quality Assurance Frontend vs SRS*
*Last updated: March 2026 — Re-verified pass 2 (Gaps #21–29 added)*
