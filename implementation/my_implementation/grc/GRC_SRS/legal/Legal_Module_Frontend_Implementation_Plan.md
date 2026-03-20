# Legal Module — Frontend Implementation Plan

**Module:** Legal (within GRC Service)  
**Target:** `frontend/apps/staff-portal/`  
**Standards:** `frontend_core_patterns.md`, `frontend_component_patterns.md`, `NEW_DETAIL_PAGE_REFERENCE.md`  
**Backend Reference:** `LEGAL_DOMAIN_EXTRACTION.md`, `Legal_Module_Architecture_Mapping.md`, `Legal_Module_Data_Models_Part1–3.md`, `Legal_Module_Workflow_Integration.md`

---

## Phase 1 — Setup & Module Initialization

### 1.1 Folder Structure

Create the following files/folders inside the existing staff-portal src tree. Legal files live alongside existing Internal Audit files — **no separate app or monorepo package**.

```
frontend/apps/staff-portal/src/
├── types/
│   └── legal.ts                              # All Legal module type definitions
├── hooks/
│   ├── legalKeys.ts                          # Query key factories for all Legal entities
│   ├── useLegalPermissions.ts                # Permission hook (mirrors useGRCPermissions)
│   ├── useLegalConfig.ts                     # Lookup hooks (CourtLevel, MeetingMode, etc.)
│   ├── useLegalDashboard.ts                  # Dashboard stats hook
│   ├── useCommitteeTypes.ts                  # CRUD hooks for CommitteeType
│   ├── useGoverningBodies.ts                 # CRUD hooks for GoverningBody
│   ├── useMembers.ts                         # CRUD hooks for Member
│   ├── useSubmissions.ts                     # CRUD hooks for SubmissionForDetermination
│   ├── useLegalMeetings.ts                   # CRUD + lifecycle hooks for Meeting
│   ├── useMeetingAgenda.ts                   # CRUD hooks for MeetingAgenda
│   ├── useMeetingParticipants.ts             # CRUD hooks for MeetingParticipant
│   ├── useMeetingDirectives.ts               # CRUD hooks for MeetingDirective
│   ├── useMinutes.ts                         # CRUD hooks for Minutes
│   ├── useResolutions.ts                     # Read hooks for Resolution (auto-created)
│   ├── useCaseDefendant.ts                   # CRUD + stage hooks for CaseDefendant
│   ├── useCasePlaintiff.ts                   # CRUD + stage hooks for CasePlaintiff
│   ├── useLitigationDirectives.ts            # CRUD hooks for LitigationDirective
│   ├── useFilings.ts                         # CRUD + approval hooks for Filing (both sides)
│   ├── useResponses.ts                       # CRUD hooks for Response (both sides)
│   ├── useHearings.ts                        # CRUD hooks for Hearing + HearingReport
│   ├── useSettlements.ts                     # CRUD hooks for Settlement (both sides)
│   ├── useJudgments.ts                       # CRUD hooks for Judgment (both sides)
│   ├── useFinancials.ts                      # CRUD hooks for Financial (both sides)
│   ├── useLitigationTasks.ts                 # CRUD hooks for TaskLitigation
│   ├── usePublicDecisions.ts                 # CRUD hooks for PublicDecision
│   └── useLegalWorkflows.ts                  # Workflow status/history hooks for Legal entities
├── services/
│   └── legalService.ts                       # All Legal API call functions
├── pages/
│   └── grc/
│       └── legal/
│           ├── CommitteeTypesPage.tsx
│           ├── GoverningBodiesPage.tsx
│           ├── GoverningBodyDetailPage.tsx
│           ├── MembersPage.tsx
│           ├── LegalDashboardPage.tsx
│           ├── SubmissionsPage.tsx
│           ├── SubmissionDetailPage.tsx
│           ├── LegalMeetingsPage.tsx
│           ├── LegalMeetingDetailPage.tsx
│           ├── DirectivesPage.tsx
│           ├── DirectiveDetailPage.tsx
│           ├── MinutesPage.tsx
│           ├── MinutesDetailPage.tsx
│           ├── ResolutionsPage.tsx
│           ├── FCCSuedCasesPage.tsx
│           ├── FCCSuedCaseDetailPage.tsx
│           ├── FCCSuingCasesPage.tsx
│           ├── FCCSuingCaseDetailPage.tsx
│           ├── PublicRegisterPage.tsx
│           └── PublicDecisionDetailPage.tsx
├── components/
│   └── grc/
│       └── legal/
│           ├── CreateCommitteeTypeDialog.tsx
│           ├── CreateGoverningBodyDialog.tsx
│           ├── CreateMemberDialog.tsx
│           ├── CreateSubmissionDialog.tsx
│           ├── CreateMeetingDialog.tsx
│           ├── MeetingAgendaSection.tsx
│           ├── MeetingParticipantsSection.tsx
│           ├── ConflictDeclarationDialog.tsx
│           ├── CreateDirectiveDialog.tsx
│           ├── CreateMinutesDialog.tsx
│           ├── CreateCaseDefendantDialog.tsx
│           ├── CreateCasePlaintiffDialog.tsx
│           ├── BreachReportIntakeDialog.tsx
│           ├── CreateFilingDialog.tsx
│           ├── CreateResponseDialog.tsx
│           ├── CreateHearingDialog.tsx
│           ├── HearingReportDialog.tsx
│           ├── CreateSettlementDialog.tsx
│           ├── RecordJudgmentDialog.tsx
│           ├── FinancialRecordDialog.tsx
│           ├── CreateLitigationTaskDialog.tsx
│           ├── CreatePublicDecisionDialog.tsx
│           ├── CaseFilingsSection.tsx
│           ├── CaseResponsesSection.tsx
│           ├── CaseHearingsSection.tsx
│           ├── CaseSettlementSection.tsx
│           ├── CaseJudgmentSection.tsx
│           ├── CaseFinancialsSection.tsx
│           ├── CaseTasksSection.tsx
│           ├── CaseDirectivesSection.tsx
│           ├── MattersArisingSection.tsx
│           ├── CloseDirectiveDialog.tsx
│           ├── FullyCloseDirectiveDialog.tsx
│           └── LegalStatusBadge.tsx
```

### 1.2 Routing Setup

Add Legal routes under the existing GRC `<Route path="/service/grc">` block in `App.tsx`:

```
/service/grc/legal/dashboard                      → LegalDashboardPage
/service/grc/legal/committee-types               → CommitteeTypesPage
/service/grc/legal/governing-bodies               → GoverningBodiesPage
/service/grc/legal/governing-bodies/:id           → GoverningBodyDetailPage
/service/grc/legal/members                        → MembersPage
/service/grc/legal/submissions                    → SubmissionsPage
/service/grc/legal/submissions/:id                → SubmissionDetailPage
/service/grc/legal/meetings                       → LegalMeetingsPage
/service/grc/legal/meetings/:id                   → LegalMeetingDetailPage
/service/grc/legal/directives                     → DirectivesPage
/service/grc/legal/directives/:id                 → DirectiveDetailPage
/service/grc/legal/minutes                        → MinutesPage
/service/grc/legal/minutes/:id                    → MinutesDetailPage
/service/grc/legal/resolutions                    → ResolutionsPage
/service/grc/legal/fcc-sued                       → FCCSuedCasesPage
/service/grc/legal/fcc-sued/:id                   → FCCSuedCaseDetailPage
/service/grc/legal/fcc-suing                      → FCCSuingCasesPage
/service/grc/legal/fcc-suing/:id                  → FCCSuingCaseDetailPage
/service/grc/legal/public-register                → PublicRegisterPage
/service/grc/legal/public-register/:id            → PublicDecisionDetailPage
```

All routes nested under `<ServiceProtectedRoute serviceKey="grc">` — no separate service guard.

### 1.3 Sidebar Navigation

Add a "Legal" section group to the GRC sidebar configuration (in the service layout config file or `ServiceLayout` component):

```
Legal
├── Dashboard
├── Committee Types
├── Governing Bodies
├── Members
├── Submissions
├── Meetings
├── Directives
├── Minutes
├── Resolutions
├── FCC Sued (Cases)
├── FCC Suing (Cases)
└── Public Register
```

Use `lucide-react` icons per entry:
- Dashboard → `LayoutDashboard`
- Committee Types → `Building2`
- Governing Bodies → `Landmark`
- Members → `Users`
- Submissions → `FileInput`
- Meetings → `Calendar`
- Directives → `ListTodo`
- Minutes → `FileText`
- Resolutions → `Scale`
- FCC Sued → `ShieldAlert`
- FCC Suing → `Gavel`
- Public Register → `Globe`

---

## Phase 2 — Type Definitions

### 2.1 Create `types/legal.ts`

Define TypeScript interfaces for every Legal entity. Map directly from the Django models in `Legal_Module_Data_Models_Part1.md`.

**Governance Structure types:**
- `CommitteeType` — `id`, `code`, `name`, `description`, `is_active`, `created_at`, `updated_at`
- `GoverningBody` — `id`, `committee_type` (nested `CommitteeType`), `name`, `composite_title`, `description`, `secretary_user_ids: string[]`, `is_active`, `created_by`, `created_at`, `updated_at`
- `Member` — `id`, `governing_body` (nested or id), `user_id`, `position`, `member_type`, `email`, `department`, `joined_date`, `left_date`, `is_active`, `created_at`, `updated_at`

**Determinations types:**
- `SubmissionForDetermination` — `id`, `title`, `description`, `submitter_user_id`, `submitter_department`, `submission_date`, `target_body` (nested or id), `supporting_documents: string[]`, `status` (`submitted` | `under_review` | `determined`), `outcome`, `outcome_notes`, `meeting_id`, `determination_date`, `is_active`, `created_at`, `updated_at`

**Meeting Governance types:**
- `LegalMeeting` — `id`, `title`, `meeting_number`, `location`, `mode`, `venue_link`, `start_datetime`, `end_datetime`, `meeting_type`, `governing_body` (nested), `agenda_summary`, `status`, `quorum_met`, `quorum_percentage`, `secretary_id`, `workflow_plan_id`, `workflow_current_stage`, `workflow_status`, `created_at`, `updated_at`
- `MeetingAgenda` — `id`, `meeting` (id), `submission` (nested `SubmissionForDetermination`), `order`, `title`, `description`, `documents: string[]`, `conflict_declarations: string[]`, `outcome`, `created_at`
- `ConflictDeclaration` — `id`, `agenda` (id), `member_user_id`, `reason`, `created_at`
- `MeetingParticipant` — `id`, `meeting` (id), `user_id`, `role` (`member` | `invitee`), `invitation_status` (`pending` | `accepted` | `declined`), `decline_reason`, `attendance_marked`
- `MeetingDirective` — `id`, `meeting` (id), `agenda` (id, optional), `description`, `category`, `priority`, `assigned_org_unit`, `assigned_user_id`, `due_date`, `status`, `completion_summary`, `completion_date`, `evidence_document_id`, `finally_closed`, `finally_closed_meeting_id`, `created_at`
- `Minutes` — `id`, `meeting` (id), `title`, `content`, `attachments: string[]`, `status`, `workflow_plan_id`, `workflow_current_stage`, `workflow_status`, `approved_by: string[]`, `approval_date`, `created_at`
- `Resolution` — `id`, `meeting` (id), `agenda` (id), `resolution_text`, `date_adopted`, `status`, `responsible_person_id`, `effective_date`, `attachments: string[]`, `created_at`

**Litigation types (FCC Sued):**
- `CaseDefendant` — `id`, `case_id` (auto ref `FCC/SUED/YYYY/NNN`), `court_case_number`, `court_registry`, `court_level`, `service_date`, `plaintiffs: string[]`, `plaintiff_advocate`, `claim_amount`, `nature_of_claim`, `department_affected`, `urgency_level`, `risk_level`, `initiation_documents: string[]`, `stage`, `dg_review_status`, `assigned_legal_officer_ids: string[]`, `assigned_legal_manager_id`, `next_hearing_date`, `workflow_plan_id`, `workflow_current_stage`, `workflow_status`, `is_active`, `created_at`, `updated_at`
- `LitigationDirective` — `id`, `case_id`, `case_type`, `issued_by_user_id`, `issue_date`, `instruction`, `due_date`, `status`, `completion_summary`, `completion_date`, `attachments: string[]`, `created_at`
- `FilingDefendant` — `id`, `case` (id), `filing_type`, `title`, `document_id`, `version`, `status`, `submitted_by_user_id`, `approval_chain`, `workflow_plan_id`, `workflow_current_stage`, `workflow_status`, `filed_date`, `created_at`
- `ResponseDefendant` — `id`, `case` (id), `response_type`, `received_date`, `document_id`, `description`, `created_at`
- `Hearing` — `id`, `case_id`, `case_type`, `hearing_date`, `court`, `judge`, `notes`, `created_at`
- `HearingReport` — `id`, `hearing` (id), `report_type`, `summary`, `remarks`, `next_hearing_date`, `attachment_id`, `created_at`
- `SettlementDefendant` — `id`, `case` (id), `settlement_date`, `terms`, `payment_amount`, `agreement_document_id`, `status`, `workflow_plan_id`, `workflow_current_stage`, `workflow_status`, `created_at`
- `JudgmentDefendant` — `id`, `case` (id), `judgment_date`, `outcome`, `amount_awarded`, `legal_costs_awarded`, `other_costs`, `document_id`, `remarks`, `dg_decision`, `appeal_due_date`, `appeal_filing_id`, `workflow_plan_id`, `workflow_current_stage`, `workflow_status`, `created_at`
- `FinancialDefendant` — `id`, `case` (id), `claim_amount`, `legal_costs_incurred`, `costs_awarded`, `other_costs`, `recoveries: FinancialEntry[]`, `payments: FinancialEntry[]`, `created_at`
- `TaskLitigation` — `id`, `case_id`, `case_type`, `title`, `assigned_to_user_id`, `due_date`, `status`, `priority`, `related_entity_type`, `related_entity_id`, `created_at`

**Litigation types (FCC Suing):** Mirror defendant types with `Plaintiff` suffix:
- `CasePlaintiff`, `FilingPlaintiff`, `ResponsePlaintiff`, `SettlementPlaintiff`, `JudgmentPlaintiff`, `FinancialPlaintiff`

**Public Register types:**
- `PublicDecision` — `id`, `title`, `meeting_id`, `body_text`, `decision_text`, `decision_date`, `status` (`draft` | `published`), `published_date`, `created_by`, `created_at`

**Shared types:**
- `FinancialEntry` — `id`, `date`, `amount`, `reference`, `status`
- `LegalListParams` extends `GRCListParams` (same shape)
- `LegalCollectionResult<T>` matches `AuditCollectionResult<T>` shape

**Lookup types:**
- `CourtLevel`, `LitigationUrgencyLevel`, `LitigationRiskLevel`, `MeetingMode`, `MeetingType`, `DirectivePriority`, `DirectiveCategory`

### 2.2 Status enum maps

Define `const` maps for all Legal entity statuses:

- `MEETING_STATUSES` — draft, registered, invitations_sent, agenda_shared, quorum_ready, ongoing, postponed, closed, cancelled, rescheduled
- `SUBMISSION_STATUSES` — submitted, under_review, determined, withdrawn
- `DIRECTIVE_STATUSES` — open, in_progress, overdue, closed, fully_closed
- `MINUTES_STATUSES` — draft, pending_approval, approved
- `RESOLUTION_STATUSES` — approved, rejected, noted
- `FILING_STATUSES` — draft, under_review_lm, approved_lm, under_review_dg, approved, filed
- `CASE_STAGES` — new, under_dg_review, directive_issued, hearing_stage, judgment_received, appeal_filed, closed, on_hold
- `SETTLEMENT_STATUSES` — proposed, agreed, rejected
- `JUDGMENT_OUTCOMES` — won, lost
- `DG_DECISIONS` — accept, appeal
- `TASK_STATUSES` — open, in_progress, overdue, closed
- `FINANCIAL_ENTRY_STATUSES` — requested, approved, processed
- `PUBLIC_DECISION_STATUSES` — draft, published

---

## Phase 3 — API Integration Layer

### 3.1 Service File: `legalService.ts`

Create `frontend/apps/staff-portal/src/services/legalService.ts`.

- Import `grcClient` from `@shared/api/gateway` (same Axios instance used by `grcService.ts`)
- Use the same `unwrap<T>()` helper and `mapPaginatedResponse<T>()` from existing `grcService.ts`
- Base URL prefix: `/api/v1/legal/`

### 3.2 Endpoint Mapping

Map backend REST endpoints to service functions. Pattern: one exported function per API call.

**Governance Structure:**

| Function | Method | Endpoint |
|---|---|---|
| `getLegalDashboardStats()` | GET | `/api/v1/legal/dashboard/stats/` |
| `getCommitteeTypes(params)` | GET | `/api/v1/legal/committee-types/` |
| `getCommitteeType(id)` | GET | `/api/v1/legal/committee-types/{id}/` |
| `createCommitteeType(data)` | POST | `/api/v1/legal/committee-types/` |
| `updateCommitteeType(id, data)` | PATCH | `/api/v1/legal/committee-types/{id}/` |
| `deleteCommitteeType(id)` | DELETE | `/api/v1/legal/committee-types/{id}/` |
| `getGoverningBodies(params)` | GET | `/api/v1/legal/governing-bodies/` |
| `getGoverningBody(id)` | GET | `/api/v1/legal/governing-bodies/{id}/` |
| `createGoverningBody(data)` | POST | `/api/v1/legal/governing-bodies/` |
| `updateGoverningBody(id, data)` | PATCH | `/api/v1/legal/governing-bodies/{id}/` |
| `deleteGoverningBody(id)` | DELETE | `/api/v1/legal/governing-bodies/{id}/` |
| `getMembers(params)` | GET | `/api/v1/legal/members/` |
| `createMember(data)` | POST | `/api/v1/legal/members/` |
| `updateMember(id, data)` | PATCH | `/api/v1/legal/members/{id}/` |
| `deleteMember(id)` | DELETE | `/api/v1/legal/members/{id}/` |

**Determinations:**

| Function | Method | Endpoint |
|---|---|---|
| `getSubmissions(params)` | GET | `/api/v1/legal/submissions/` |
| `getSubmission(id)` | GET | `/api/v1/legal/submissions/{id}/` |
| `createSubmission(data)` | POST | `/api/v1/legal/submissions/` |
| `updateSubmission(id, data)` | PATCH | `/api/v1/legal/submissions/{id}/` |
| `withdrawSubmission(id)` | POST | `/api/v1/legal/submissions/{id}/withdraw/` |

**Meeting Governance:**

| Function | Method | Endpoint |
|---|---|---|
| `getLegalMeetings(params)` | GET | `/api/v1/legal/meetings/` |
| `getLegalMeeting(id)` | GET | `/api/v1/legal/meetings/{id}/` |
| `createLegalMeeting(data)` | POST | `/api/v1/legal/meetings/` |
| `updateLegalMeeting(id, data)` | PATCH | `/api/v1/legal/meetings/{id}/` |
| `getLegalMeetingQuorum(id)` | GET | `/api/v1/legal/meetings/{id}/quorum/` |
| `registerMeeting(id)` | POST | `/api/v1/legal/meetings/{id}/register/` |
| `startMeeting(id)` | POST | `/api/v1/legal/meetings/{id}/start/` |
| `closeMeeting(id)` | POST | `/api/v1/legal/meetings/{id}/close/` |
| `postponeMeeting(id)` | POST | `/api/v1/legal/meetings/{id}/postpone/` |
| `rescheduleMeeting(id, data)` | POST | `/api/v1/legal/meetings/{id}/reschedule/` |
| `cancelMeeting(id)` | POST | `/api/v1/legal/meetings/{id}/cancel/` |
| `getMeetingAgendaItems(meetingId)` | GET | `/api/v1/legal/meetings/{id}/agenda/` |
| `addAgendaItem(meetingId, data)` | POST | `/api/v1/legal/meetings/{id}/agenda/` |
| `updateAgendaItem(meetingId, agendaId, data)` | PATCH | `/api/v1/legal/meetings/{id}/agenda/{agendaId}/` |
| `removeAgendaItem(meetingId, agendaId)` | DELETE | `/api/v1/legal/meetings/{id}/agenda/{agendaId}/` |
| `recordAgendaOutcome(meetingId, agendaId, data)` | POST | `/api/v1/legal/meetings/{id}/agenda/{agendaId}/determine/` |
| `getMeetingParticipants(meetingId)` | GET | `/api/v1/legal/meetings/{id}/participants/` |
| `respondToInvitation(meetingId, data)` | POST | `/api/v1/legal/meetings/{id}/participants/respond/` |
| `declareConflict(meetingId, agendaId, data)` | POST | `/api/v1/legal/meetings/{id}/agenda/{agendaId}/conflict/` |
| `getMeetingDirectives(meetingId)` | GET | `/api/v1/legal/meetings/{id}/directives/` |
| `createMeetingDirective(meetingId, data)` | POST | `/api/v1/legal/meetings/{id}/directives/` |
| `updateDirectiveStatus(directiveId, data)` | PATCH | `/api/v1/legal/directives/{id}/` |
| `closeDirective(directiveId, data)` | POST | `/api/v1/legal/directives/{id}/close/` |
| `fullyCloseDirective(directiveId, data)` | POST | `/api/v1/legal/directives/{id}/fully-close/` |
| `getMinutes(params)` | GET | `/api/v1/legal/minutes/` |
| `getMinutesDetail(id)` | GET | `/api/v1/legal/minutes/{id}/` |
| `createMinutes(meetingId, data)` | POST | `/api/v1/legal/meetings/{id}/minutes/` |
| `updateMinutes(id, data)` | PATCH | `/api/v1/legal/minutes/{id}/` |
| `submitMinutesForApproval(id)` | POST | `/api/v1/legal/minutes/{id}/submit/` |
| `getResolutions(params)` | GET | `/api/v1/legal/resolutions/` |
| `getResolution(id)` | GET | `/api/v1/legal/resolutions/{id}/` |

**Litigation — FCC Sued:**

| Function | Method | Endpoint |
|---|---|---|
| `getCaseDefendants(params)` | GET | `/api/v1/legal/cases/defendant/` |
| `getCaseDefendant(id)` | GET | `/api/v1/legal/cases/defendant/{id}/` |
| `createCaseDefendant(data)` | POST | `/api/v1/legal/cases/defendant/` |
| `updateCaseDefendant(id, data)` | PATCH | `/api/v1/legal/cases/defendant/{id}/` |
| `submitForDGReview(caseType, id)` | POST | `/api/v1/legal/cases/{type}/{id}/submit-dg-review/` |
| `issueDGDirective(caseType, id, data)` | POST | `/api/v1/legal/cases/{type}/{id}/issue-directive/` |
| `markDGReviewed(caseType, id)` | POST | `/api/v1/legal/cases/{type}/{id}/mark-reviewed/` |
| `getFilings(caseType, caseId, params)` | GET | `/api/v1/legal/cases/{type}/{id}/filings/` |
| `createFiling(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/filings/` |
| `submitFilingForApproval(filingId)` | POST | `/api/v1/legal/filings/{id}/submit/` |
| `approveFilingLM(filingId)` | POST | `/api/v1/legal/filings/{id}/approve-lm/` |
| `approveFilingDG(filingId)` | POST | `/api/v1/legal/filings/{id}/approve-dg/` |
| `markFilingFiled(filingId, data)` | POST | `/api/v1/legal/filings/{id}/mark-filed/` |
| `getResponses(caseType, caseId)` | GET | `/api/v1/legal/cases/{type}/{id}/responses/` |
| `createResponse(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/responses/` |
| `getHearings(caseType, caseId)` | GET | `/api/v1/legal/cases/{type}/{id}/hearings/` |
| `createHearing(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/hearings/` |
| `getHearingReports(hearingId)` | GET | `/api/v1/legal/hearings/{id}/reports/` |
| `createHearingReport(hearingId, data)` | POST | `/api/v1/legal/hearings/{id}/reports/` |
| `getSettlement(caseType, caseId)` | GET | `/api/v1/legal/cases/{type}/{id}/settlement/` |
| `createSettlement(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/settlement/` |
| `submitSettlementForApproval(settlementId)` | POST | `/api/v1/legal/settlements/{id}/submit/` |
| `getJudgment(caseType, caseId)` | GET | `/api/v1/legal/cases/{type}/{id}/judgment/` |
| `recordJudgment(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/judgment/` |
| `submitJudgmentForReview(judgmentId)` | POST | `/api/v1/legal/judgments/{id}/submit/` |
| `dgDecisionOnJudgment(judgmentId, data)` | POST | `/api/v1/legal/judgments/{id}/dg-decision/` |
| `getFinancials(caseType, caseId)` | GET | `/api/v1/legal/cases/{type}/{id}/financials/` |
| `recordRecovery(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/financials/recovery/` |
| `recordPayment(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/financials/payment/` |
| `getLitigationTasks(caseType, caseId)` | GET | `/api/v1/legal/cases/{type}/{id}/tasks/` |
| `createLitigationTask(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/tasks/` |
| `updateLitigationTask(taskId, data)` | PATCH | `/api/v1/legal/tasks/{id}/` |
| `closeLitigationTask(taskId, data)` | POST | `/api/v1/legal/tasks/{id}/close/` |
| `getOverdueLitigationTasks(params)` | GET | `/api/v1/legal/tasks/overdue/` |
| `getLitigationDirectives(caseType, caseId)` | GET | `/api/v1/legal/cases/{type}/{id}/directives/` |
| `requestCaseClosure(caseType, caseId, data)` | POST | `/api/v1/legal/cases/{type}/{id}/request-closure/` |
| `approveCaseClosure(caseType, caseId)` | POST | `/api/v1/legal/cases/{type}/{id}/approve-closure/` |

**Litigation — FCC Suing:** Identical functions using `caseType = 'plaintiff'`.

**Public Register:**

| Function | Method | Endpoint |
|---|---|---|
| `getPublicDecisions(params)` | GET | `/api/v1/legal/public-decisions/` |
| `getPublicDecision(id)` | GET | `/api/v1/legal/public-decisions/{id}/` |
| `createPublicDecision(data)` | POST | `/api/v1/legal/public-decisions/` |
| `updatePublicDecision(id, data)` | PATCH | `/api/v1/legal/public-decisions/{id}/` |
| `publishDecision(id)` | POST | `/api/v1/legal/public-decisions/{id}/publish/` |

### 3.3 Error Handling

Follow the exact pattern from `frontend_core_patterns.md` §2.5:

- In hooks `onError`: `toast.error('Failed to <action>', { description: error.response?.data?.error || error.message })`
- In components: persistent `<Alert variant="destructive">` for data-load failures
- Never surface raw error objects to the user

### 3.4 Data Fetching Structure

- All list hooks accept `(page: number, pageSize: number, filters?: Record<string, unknown>)`
- All detail hooks accept `(id: string)`
- All hooks use the query key factory from `legalKeys.ts`
- `staleTime: 5 * 60 * 1000` for entity data; `staleTime: 30_000` for workflow status hooks
- Filter by `is_active !== false` after fetching list results

---

## Phase 4 — Query Key Factory

### 4.1 Create `legalKeys.ts`

Define key factories for every Legal entity following the `grcKeys.ts` pattern:

```
committeeTypeKeys.all / lists / list(page, pageSize, filterKey) / details / detail(id)
governanceLegalKeys.all                                 ← key group for dashboard
legalDashboardKeys.all / stats
governanceLegalKeys — see individual entity keys below:
governingBodyKeys.all / lists / list(...) / details / detail(id)
memberKeys.all / lists / list(...) / details / detail(id)
submissionKeys.all / lists / list(...) / details / detail(id)
legalMeetingKeys.all / lists / list(...) / details / detail(id)
meetingAgendaKeys.all / byMeeting(meetingId)
meetingParticipantKeys.all / byMeeting(meetingId)
meetingDirectiveKeys.all / lists / list(...) / details / detail(id) / byMeeting(meetingId)
minutesKeys.all / lists / list(...) / details / detail(id)
resolutionKeys.all / lists / list(...) / details / detail(id)
caseDefendantKeys.all / lists / list(...) / details / detail(id)
casePlaintiffKeys.all / lists / list(...) / details / detail(id)
litigationDirectiveKeys.all / byCase(caseId)
filingKeys.all / byCase(caseId) / detail(id)
responseKeys.all / byCase(caseId)
hearingKeys.all / byCase(caseId) / reports(hearingId)
settlementKeys.all / byCase(caseId) / detail(id)
judgmentKeys.all / byCase(caseId) / detail(id)
financialKeys.all / byCase(caseId)
litigationTaskKeys.all / byCase(caseId) / detail(id)
publicDecisionKeys.all / lists / list(...) / details / detail(id)
legalWorkflowKeys.status(entityType, entityId) / history(entityType, entityId)
legalDashboardKeys.stats
```

---

## Phase 5 — Permission Hook

### 5.1 Create `useLegalPermissions.ts`

Follow the same pattern as `useGRCPermissions.tsx`. Read from `permissions_flat` in JWT.

**Permission code format:** `grc:legal_<resource_type>:<action>` (underscore after `legal`, per-resource)

> **SOURCE OF TRUTH:** `grc-service/config/permissions/grc-service.json` — these are the codes published by grc-service to IAM on startup. Do NOT invent domain-grouped codes like `grc:legal:governance:view`; they do not exist in the backend.

**All 28 legal permission codes (from `grc-service.json`):**
```
// Governing Bodies
grc:legal_governing_body:view     # View governing body records, members, committees
grc:legal_governing_body:manage   # Create, update, manage governing bodies and members

// Meetings
grc:legal_meeting:view            # View meeting details, agendas, participants, minutes
grc:legal_meeting:manage          # Schedule, update meetings, agendas, RSVPs
grc:legal_meeting:approve         # Approve meeting lifecycle workflow stages

// Minutes
grc:legal_minutes:view            # View meeting minutes, resolutions, directives
grc:legal_minutes:manage          # Draft, update, submit minutes for approval
grc:legal_minutes:approve         # Approve meeting minutes through workflow

// Cases (Litigation)
grc:legal_case:view               # View defendant and plaintiff case records
grc:legal_case:manage             # Create, update, manage litigation cases
grc:legal_case:close              # Approve case closure and DG noting workflow stages

// Filings
grc:legal_filing:view             # View court filing documents and approval chains
grc:legal_filing:manage           # Create, update, submit filings for approval
grc:legal_filing:approve          # Approve legal filings through workflow

// Hearings
grc:legal_hearing:view            # View hearing schedules, reports, outcomes
grc:legal_hearing:manage          # Create, update hearings and submit reports

// Settlements
grc:legal_settlement:view         # View settlement records and agreement details
grc:legal_settlement:manage       # Create, update, submit settlements for approval
grc:legal_settlement:approve      # Approve settlement workflow stages

// Judgments
grc:legal_judgment:view           # View judgment records, appeals, financial outcomes
grc:legal_judgment:manage         # Record, update, submit judgments for review
grc:legal_judgment:record         # Record judgment and trigger appeal creation

// Directives
grc:legal_directive:view          # View litigation directives and task assignments
grc:legal_directive:manage        # Create, assign, update directives and tasks

// Appeals
grc:legal_appeal:view             # View appeal records, decisions, outcomes
grc:legal_appeal:manage           # Create, update, manage appeal records

// Notices
grc:legal_notice:view             # View legal notices and service records
grc:legal_notice:manage           # Create, update, track notice service and delivery
```

**Convenience booleans (mapped from `grc-service.json` codes):**

```ts
// Governing Bodies
canViewGoverningBody    → grc:legal_governing_body:view
canManageGoverningBody  → grc:legal_governing_body:manage

// Meetings
canViewMeetings         → grc:legal_meeting:view
canManageMeetings       → grc:legal_meeting:manage
canApproveMeetings      → grc:legal_meeting:approve

// Minutes
canViewMinutes          → grc:legal_minutes:view
canManageMinutes        → grc:legal_minutes:manage
canApproveMinutes       → grc:legal_minutes:approve

// Cases
canViewCases            → grc:legal_case:view
canManageCases          → grc:legal_case:manage
canCloseCases           → grc:legal_case:close

// Filings
canViewFilings          → grc:legal_filing:view
canManageFilings        → grc:legal_filing:manage
canApproveFilings       → grc:legal_filing:approve

// Hearings
canViewHearings         → grc:legal_hearing:view
canManageHearings       → grc:legal_hearing:manage

// Settlements
canViewSettlements      → grc:legal_settlement:view
canManageSettlements    → grc:legal_settlement:manage
canApproveSettlements   → grc:legal_settlement:approve

// Judgments
canViewJudgments        → grc:legal_judgment:view
canManageJudgments      → grc:legal_judgment:manage
canRecordJudgments      → grc:legal_judgment:record

// Directives
canViewDirectives       → grc:legal_directive:view
canManageDirectives     → grc:legal_directive:manage

// Appeals
canViewAppeals          → grc:legal_appeal:view
canManageAppeals        → grc:legal_appeal:manage

// Notices
canViewNotices          → grc:legal_notice:view
canManageNotices        → grc:legal_notice:manage
```

Use `hasPermission(code: string)` and `hasAnyPermission(codes: string[])` — same interface as `useGRCPermissions`.

**Role-level derivation from codes (based on roles in `grc-service.json`):**
```tsx
// Legal Manager: has filing:approve and case:close
const isLegalManager = canApproveFilings && canCloseCases;
// Legal Officer: can manage filings but cannot approve them
const isLegalOfficer = canManageFilings && !canApproveFilings;
// Secretary: manages meetings and governing bodies
const isSecretary = canManageMeetings && canManageGoverningBody;
// Meeting Member: can approve meetings but cannot manage them
const isMeetingParticipant = canApproveMeetings && !canManageMeetings;
```

---

## Phase 6 — Lookup & Config Hooks

### 6.1 Create `useLegalConfig.ts`

All lookup hooks accept `enabled: boolean` for lazy loading in dialogs.

```
useCourtLevels(enabled)          → GET /api/v1/legal/lookups/court-levels/
useUrgencyLevels(enabled)        → GET /api/v1/legal/lookups/urgency-levels/
useRiskLevels(enabled)           → GET /api/v1/legal/lookups/risk-levels/
useMeetingModes(enabled)         → GET /api/v1/legal/lookups/meeting-modes/
useMeetingTypes(enabled)         → GET /api/v1/legal/lookups/meeting-types/
useDirectivePriorities(enabled)  → GET /api/v1/legal/lookups/directive-priorities/
useDirectiveCategories(enabled)  → GET /api/v1/legal/lookups/directive-categories/
useFilingTypes(caseType, enabled) → context-dependent static map
useResponseTypes(caseType, enabled) → context-dependent static map
```

Filing types (defendant): Statement of Defence, Affidavit, Application, Chamber Summons, Bill of Cost, Notice of Appeal.  
Filing types (plaintiff): Plaint, Petition, Statement of Claim, Application, Chamber Summons, Affidavit, Bill of Cost, Notice of Appeal.  
Response types (defendant): Preliminary Objections, Counter Claims.  
Response types (plaintiff): Preliminary Objections, Response to Ruling, Response to Orders, Response to Affidavits, Counter Claim, Initial Response.

---

## Phase 7 — Core UI Implementation (List Pages)

### 7.1 Pattern for Every List Page

Follow Style B from `frontend_core_patterns.md` §0a exactly:

- Wrapper: `<div className="space-y-4">`
- Header: `flex items-center justify-between` with icon + `text-2xl font-bold` title + permission-gated action buttons
- Info Alert (optional): contextual guidance below header
- Error Alert: `<Alert variant="destructive">` when `error` is truthy
- Loading banner: dashed border with `Loader2` spinner
- Table: `<GenericListPage>` with server pagination
- Dialogs: siblings of main div inside fragment `<>...</>`

### 7.2 List Pages to Build

| Page | Entity | Key columns | Actions |
|---|---|---|---|
| `CommitteeTypesPage` | CommitteeType | Code, Name, Status | Create, Edit, Deactivate |
| `GoverningBodiesPage` | GoverningBody | Name, Committee Type, Members Count, Status | Create, View Detail |
| `MembersPage` | Member | Full Name, Governing Body, Position, Member Type, Status | Add, Edit, Deactivate |
| `SubmissionsPage` | SubmissionForDetermination | Title, Target Body, Status, Date | Create, View Detail, Withdraw |
| `LegalMeetingsPage` | Meeting | Meeting No., Title, Governing Body, Date, Status | Create, View Detail |
| `DirectivesPage` | MeetingDirective | Description, Assigned To, Due Date, Priority, Status | View Detail |
| `MinutesPage` | Minutes | Meeting, Title, Status | View Detail |
| `ResolutionsPage` | Resolution | Meeting, Agenda Item, Status, Date | View (read-only) |
| `FCCSuedCasesPage` | CaseDefendant | Case ID, Court, Plaintiffs, Stage, Urgency | Create, View Detail |
| `FCCSuingCasesPage` | CasePlaintiff | Case ID, Respondent, Stage, Urgency | Create (full), Raise Breach Report (simplified), View Detail |
| `PublicRegisterPage` | PublicDecision | Title, Decision Date, Status | Create, View Detail, Publish |

### 7.3 Data Transform Functions

Each list page defines a `transform<Entity>ForList()` function mapping to `ListItem` shape:
- Required keys: `id`, `title`, `status`, `createdAt`, `updatedAt`
- Extra keys for custom columns
- `_original` reference for action handlers

### 7.4 Pagination State

```tsx
const [page, setPage] = useState(1);
const [pageSize, setPageSize] = useState(20);
```

Reset `page` to 1 on filter or pageSize change.

### 7.5 Search & Filter

- Text search: `const [searchQuery, setSearchQuery] = useState('')` → passed as `{ search: searchQuery || undefined }` to hook
- Status filter: dropdown select filtering by status field
- Date filters: `date_from`, `date_to` for meeting and case lists
- Governing body filter: on meetings, submissions, and directives lists

### 7.6 Bulk Actions

Not required for initial implementation. Defer to Phase 2 of development. Individual row actions (View, Edit, Delete) via `GenericListPage` handlers.

---

## Phase 8 — Detail Pages (Workflow-Enabled)

**STRICTLY follow `NEW_DETAIL_PAGE_REFERENCE.md` for all detail pages.**

### 8.1 Common Detail Page Structure

Every detail page follows this exact layout:

```
┌─────────────────────────────────────────────────────────┐
│ ← (back)   Entity Title              [CTAs]  [Badge]   │
│            Subtitle / reference                         │
├─────────────────────────────────────────────────────────┤
│ Card: Entity Details (grid gap-4 md:grid-cols-2)        │
├─────────────────────────────────────────────────────────┤
│ Card: Additional Info (conditional)                     │
├─────────────────────────────────────────────────────────┤
│ Card/Section: Child entities (embedded tables/sections) │
├─────────────────────────────────────────────────────────┤
│ EmbeddedWorkflowConsole (full-width, bottom)            │
└─────────────────────────────────────────────────────────┘
```

- Wrapper: `<div className="space-y-4 p-4">`
- Header: `flex items-center gap-4` with ghost icon-only back button (`ChevronLeft` — NOT `ArrowLeft`, `size="icon"`, `variant="ghost"`, `aria-label="Back"`)
- Title: `text-2xl font-semibold` (NOT `font-bold`)
- Subtitle: `text-sm text-muted-foreground` with `font-mono` for reference numbers
- Status badge: custom Tailwind classes (NOT `variant=` props)
- Cards: `<CardHeader className="pb-2">` + `<CardTitle className="text-base flex items-center gap-2">` with lucide icon
- Label/value: `text-sm text-muted-foreground` label + `font-medium` value
- No `<CardDescription>`, no `<Separator>`
- Loading: centered `Loader2` in `min-h-[300px]`
- Error: `<Alert variant="destructive">` with back button

### 8.2 Detail Pages to Build

#### `GoverningBodyDetailPage`

**Cards:**
- Details Card: Name, Committee Type, Composite Title, Status, Created, Updated
- Description Card (conditional)
- Secretaries Card: list of secretary UUIDs resolved via `UserDisplay`
- Members Section: embedded table of members with Add/Edit/Remove actions (when status allows)

**No workflow console** — GoverningBody does not have WorkflowMixin.

---

#### `SubmissionDetailPage`

**Cards:**
- Submission Details Card: Title, Target Body, Status, Submission Date, Submitter
- Supporting Documents Card (conditional): links to documents via Document Records Service
- Outcome Card (conditional, shown when status = determined): Outcome, Determination Date, Outcome Notes, Meeting link

**CTAs:**
- "Edit" button — only when `status === 'submitted'` AND user is the submitter
- "Withdraw" button — only when `status === 'submitted'` AND user is the submitter

**No workflow console** — internal status machine.

---

#### `LegalMeetingDetailPage` (Workflow-Enabled)

**Cards:**
- Meeting Details Card: Meeting Number, Title, Governing Body, Mode, Location/Link, Start/End Time, Type, Quorum Met, Quorum Percentage, Secretary
- Agenda Section (`MeetingAgendaSection`): embedded table of agenda items with Add/Reorder/Remove actions; for each item: Outcome, Conflict Declarations, linked Submission
- Participants Section (`MeetingParticipantsSection`): table showing invitation status, attendance; Accept/Decline action for current user
- Directives Section: table of meeting directives; Add Directive button (only during ONGOING)
- Matters Arising Section (`MattersArisingSection`): auto-populated from open directives of the governing body; Secretary can "Fully Close" from here
- Minutes Card (conditional): link to Minutes record; "Draft Minutes" button (only after ONGOING)
- Resolutions Card (conditional): read-only list of auto-created resolutions

**CTAs (status-gated + permission-gated):**
- "Register Meeting" — status = draft, Secretary only
- "Share Agenda" — status = invitations_sent, Secretary only
- "Start Meeting" — status = quorum_ready AND quorum_met = true, Secretary only
- "Postpone" — status = ongoing, Secretary only
- "Close Meeting" — status = ongoing, Secretary only
- "Cancel" — status in (draft, registered), Secretary only
- "Reschedule" — status in (draft, registered, postponed), Secretary only

**Workflow console:** `EmbeddedWorkflowConsole` at bottom — uses `grc.legal_meeting_lifecycle` template.

**Status badge colors:**
```
draft:             bg-gray-100 text-gray-800
registered:        bg-blue-100 text-blue-800
invitations_sent:  bg-blue-100 text-blue-800
agenda_shared:     bg-indigo-100 text-indigo-800
quorum_ready:      bg-green-100 text-green-800
ongoing:           bg-yellow-100 text-yellow-800
postponed:         bg-orange-100 text-orange-800
closed:            bg-green-100 text-green-800
cancelled:         bg-red-100 text-red-800
rescheduled:       bg-purple-100 text-purple-800
```

---

#### `DirectiveDetailPage`

**Cards:**
- Directive Details: Description, Category, Priority, Assigned To, Assigned Org Unit, Due Date, Status
- Meeting Context: Meeting reference, Agenda Item reference
- Completion Card (conditional, when closed/fully_closed): Completion Summary, Completion Date, Evidence Document link

**CTAs:**
- "Mark In Progress" — status = open, assigned user only
- "Close Directive" — status in (open, in_progress), assigned user only → requires CompletionSummary
- "Fully Close" — status = closed, Secretary only (in a meeting's Matters Arising context)

**No workflow console** — internal status machine.

---

#### `MinutesDetailPage` (Workflow-Enabled)

**Cards:**
- Minutes Details: Title, Meeting reference, Status, Created
- Content Card: full minutes content (rich text or plain text display)
- Attachments Card (conditional)
- Approval Info Card (conditional): Approved By list, Approval Date

**CTAs:**
- "Edit" — status = draft, Secretary only
- "Submit for Approval" — status = draft AND no workflow started, Secretary only

**Workflow console:** `EmbeddedWorkflowConsole` — uses `grc.legal_minutes_approval` template.

---

#### `FCCSuedCaseDetailPage` (Workflow-Enabled)

**Header:** Case ID (auto `FCC/SUED/YYYY/NNN`), Court Case Number, Status Badge (stage)

**Cards:**
- Case Details Card: Court Level, Court Registry, Court Case No., Service Date, Nature of Claim, Department Affected, Urgency Level, Risk Level, Claim Amount
- Plaintiffs Card: Plaintiffs list, Plaintiff Advocate
- Assignment Card: Assigned Legal Officer(s), Assigned Legal Manager
- DG Review Card (conditional, stage = under_dg_review): DG Review Status, DG Directive (if issued)

**Embedded Child Sections (Tabbed or sequential):**
- `CaseDirectivesSection` — DG directives table
- `CaseFilingsSection` — filings table with status badges, approval actions
- `CaseResponsesSection` — plaintiff responses table (read-only log)
- `CaseHearingsSection` — hearings table with expandable reports
- `CaseSettlementSection` — settlement card (single record, conditional)
- `CaseJudgmentSection` — judgment card with DG decision (single record, conditional)
- `CaseFinancialsSection` — financial summary cards + Recovery/Payment sub-tables
- `CaseTasksSection` — tasks table with status, priority, due dates

**CTAs (stage-gated + role-gated):**
- "Submit for DG Review" — stage = new, Legal Officer/Manager
- "Issue Directive" — stage = under_dg_review, DG only
- "Mark Reviewed" — stage = under_dg_review, DG only
- "New Filing" — stage in (directive_issued, hearing_stage), Legal Officer
- "New Hearing" — stage = hearing_stage, Legal Officer
- "Record Settlement" — active case stages, Legal Officer
- "Record Judgment" — stage = hearing_stage, Legal Officer
- "Request Closure" — case concluded, Legal Manager only
- "Approve Closure" — pending closure, DG only

**Filing Row Actions:**
- "Submit for Approval" — filing status = draft, submitted_by user
- "Approve (LM)" — filing status = under_review_lm, Legal Manager
- "Approve (DG)" — filing status = under_review_dg, DG
- "Mark Filed" — filing status = approved, Legal Officer

**Financial Cards:**
- Claim Amount, Legal Costs Incurred, Costs Awarded, Other Costs
- "Record Recovery" button — only if judgment.outcome = won
- "Record Payment" button — only if judgment.outcome = lost

**Workflow console:** `EmbeddedWorkflowConsole` — uses `grc.legal_case_closure` template (activated when closure is requested).

---

#### `FCCSuingCaseDetailPage` (Workflow-Enabled)

**Identical structure to FCCSuedCaseDetailPage** with these differences:
- Case ID prefix: `FCC/SUING/YYYY/NNN`
- Respondent fields instead of Plaintiff fields: Respondent Name, Respondent Type, Nature of Breach, Reporting Department
- Filing types: Plaint, Petition, Statement of Claim, etc.
- Response types: different set (see Lookup section)
- Financial cards: add "Recovered Amount" card
- Registration source indicator: "Full Report" or "Breach Report Intake" badge

---

#### `PublicDecisionDetailPage`

**Cards:**
- Decision Details: Title, Decision Date, Status, Meeting link, Created By, Published Date (conditional)
- Body Text Card: full body text
- Decision Text Card: formal decision text

**CTAs:**
- "Edit" — status = draft, Secretariat only
- "Publish" — status = draft, Secretariat only
  - Confirm dialog before publishing

**No workflow console** — two-state status machine.

---

## Phase 9 — Forms & Modals

### 9.1 Form Stack (All Dialogs)

- `react-hook-form` + `zodResolver` + Zod schema + shadcn Form components
- Schema defined at module scope outside the component
- `useEffect` reset on `[open, mode, entity, form]`
- `onSubmit` cleans data: trim strings, convert empty to `undefined`
- Dialog sizes per `frontend_component_patterns.md` §3.1

### 9.2 Dialog Inventory

#### Governance Structure

| Dialog | Fields | Size |
|---|---|---|
| `CreateCommitteeTypeDialog` | code (auto-uppercase), name, description | `max-w-lg` |
| `CreateGoverningBodyDialog` | committee_type (SmartSelect), name, composite_title, description, secretary_user_ids (multi-select) | `max-w-2xl` |
| `CreateMemberDialog` | governing_body (SmartSelect, locked in context), user_id (SmartSelect from Corporate Service), position (Select), member_type (Select), joined_date | `max-w-2xl` |

#### Determinations

| Dialog | Fields | Size |
|---|---|---|
| `CreateSubmissionDialog` | title, description (Textarea), target_body (SmartSelect), supporting_documents (file upload widget) | `max-w-3xl` |

#### Meeting Governance

| Dialog | Fields | Size |
|---|---|---|
| `CreateMeetingDialog` | governing_body (SmartSelect), title, mode (Select), meeting_type (Select), location, venue_link, start_datetime, end_datetime | `max-w-3xl` |
| `ConflictDeclarationDialog` | reason (Textarea) | `max-w-lg` |
| `CreateDirectiveDialog` | description (Textarea), category (Select), priority (Select), assigned_user_id (SmartSelect), assigned_org_unit, due_date | `max-w-2xl` |
| `CloseDirectiveDialog` | completion_summary (Textarea, required), completion_date (DatePicker, required), evidence_document_id (file upload, optional) | `max-w-2xl` |
| `FullyCloseDirectiveDialog` | completion_summary read-only display, confirmation checkbox: "Confirm final closure" — this marks FinallyClosed=true and removes directive from all future Matters Arising | `max-w-lg` |
| `CreateMinutesDialog` | title, content (Textarea rows=12), attachments (file upload widget) | `max-w-3xl` |

#### Litigation — Case Registration

| Dialog | Fields | Size |
|---|---|---|
| `CreateCaseDefendantDialog` | court_level (SmartSelect), court_registry, court_case_number, service_date, plaintiffs (dynamic field array), plaintiff_advocate, claim_amount, nature_of_claim, department_affected, urgency_level (Select), risk_level (Select), initiation_documents (file upload) | `max-w-4xl` |
| `CreateCasePlaintiffDialog` (Full) | reporting_department, nature_of_breach, respondent_name, respondent_type, description (Textarea), estimated_claim_amount, urgency_level, risk_level, initiation_documents | `max-w-4xl` |
| `BreachReportIntakeDialog` (Simplified) | reporting_department (pre-filled from user), nature_of_breach, respondent_name, respondent_type, description, urgency_level, optional document | `max-w-2xl` |

#### Litigation — Child Entities

| Dialog | Fields | Size |
|---|---|---|
| `CreateFilingDialog` | filing_type (Select), title, document (file upload) | `max-w-2xl` |
| `CreateResponseDialog` | response_type (Select), received_date, document (file upload), description | `max-w-2xl` |
| `CreateHearingDialog` | hearing_date, court, judge, notes (Textarea) | `max-w-2xl` |
| `HearingReportDialog` | report_type (Select), summary (Textarea), remarks, next_hearing_date, attachment (file upload) | `max-w-2xl` |
| `CreateSettlementDialog` | settlement_date, terms (Textarea), payment_amount (optional number), agreement_document (file upload) | `max-w-2xl` |
| `RecordJudgmentDialog` | judgment_date, outcome (Select: Won/Lost), amount_awarded, legal_costs_awarded, other_costs, document (file upload), remarks (Textarea) | `max-w-3xl` |
| `FinancialRecordDialog` | type (Recovery/Payment), date, amount, reference, status (Select) | `max-w-lg` |
| `CreateLitigationTaskDialog` | title, assigned_to_user_id (SmartSelect), due_date, priority (Select) | `max-w-2xl` |

#### Public Register

| Dialog | Fields | Size |
|---|---|---|
| `CreatePublicDecisionDialog` | title, meeting_id (SmartSelect from closed meetings), body_text (Textarea), decision_text (Textarea), decision_date | `max-w-3xl` |

### 9.3 Validation Rules

- All title/name fields: `z.string().min(3).max(255)`
- Code fields: `z.string().min(2).max(50).regex(/^[A-Z0-9-]+$/)`
- Date fields: `z.string().min(1, 'Date is required')`
- Amount fields: `z.coerce.number().min(0)`
- Select/SmartSelect FKs: `z.string().min(1, 'Selection is required')`
- Textarea fields (optional): `z.string().optional()`
- Textarea fields (required): `z.string().min(10, 'Description too short')`
- File fields: handled via separate upload mutation, store returned `document_id`

### 9.4 File Upload Pattern

Documents are uploaded to Document Records Service, not to grc-service:
1. User selects file in form
2. On form submit, first call `POST /api/v1/documents/` (Document Records Service) to upload
3. Receive `document_id` UUID
4. Include `document_id` in the entity creation/update payload to grc-service

Use existing shared upload utilities if available. If not, create a `useDocumentUpload()` hook.

---

## Phase 10 — RBAC Enforcement

### 10.1 Button Visibility

**Rule: Never render a button and then disable for permission. Hide entirely.**

```tsx
{canManageMeetings && (
  <Button onClick={() => setIsCreateOpen(true)}>
    <Plus className="mr-2 h-4 w-4" />
    Create Meeting
  </Button>
)}
```

### 10.2 Page Access

- All Legal pages render inside `<ServiceProtectedRoute serviceKey="grc">` — service-level guard
- No additional route-level guards needed for Legal sub-pages
- Pages with no data access show empty states, not access denied

### 10.3 Action Restrictions — Composite Role Logic

Derive functional role booleans at the top of each page:

```tsx
// Correct boolean names from Phase 5.1 (sourced from grc-service.json):
const {
  canManageCases,
  canManageFilings,
  canApproveFilings,   // grc:legal_filing:approve — Legal Manager only
  canCloseCases,       // grc:legal_case:close — Legal Manager only
  canRecordJudgments,  // grc:legal_judgment:record — Legal Manager only
} = useLegalPermissions();

// Composite role guards:
// Legal Manager: can approve filings and close cases (both gated on legal_manager role)
const isLegalManager = canApproveFilings && canCloseCases;
// Legal Officer: can manage filings but cannot approve them
const isLegalOfficer = canManageFilings && !canApproveFilings;
```

### 10.4 Status + Permission Gates

Every CTA button must gate on BOTH permission AND entity status:

```tsx
{canManageMeetings && meeting.status === 'draft' && isSecretary && (
  <Button onClick={handleRegister}>Register Meeting</Button>
)}
```

Secretary check: compare current user's UUID against `meeting.secretary_id` or `governing_body.secretary_user_ids`.

### 10.5 Row-Level Actions

- Pass `onEdit={canManage ? handleEdit : undefined}` to `GenericListPage`
- Pass `onDelete={canManage ? handleDelete : undefined}`
- For inline status actions (e.g., Approve Filing), render conditionally per row based on filing.status and user permission

---

## Phase 11 — Notifications

### 11.1 Toasts (Transient)

| Event | Type | Example |
|---|---|---|
| Entity created | `toast.success` | "Meeting created successfully" |
| Entity updated | `toast.success` | "Filing approved by Legal Manager" |
| Entity deleted | `toast.success` | "Committee type deactivated" |
| Workflow submitted | `toast.success` | "Minutes submitted for approval via Work Orchestration" |
| Mutation failure | `toast.error` | "Failed to create case" with error description |
| Business rule block | `toast.error` | "Cannot start meeting — quorum not met" |
| Soft warning | `toast.warning` | "No agenda items — add submissions before sharing agenda" |

Place: inside mutation hooks (`onSuccess`, `onError`). Page-level toasts only for business-rule blocks before calling mutate.

### 11.2 In-Page Alerts

| Context | Component | Variant |
|---|---|---|
| Data load failure | `<Alert variant="destructive">` | Persistent, with retry option |
| Informational guidance | `<Alert>` (default) | Blue-bordered |
| Read-only warning | Yellow border div (inline) | "This case is closed and read-only" |

### 11.3 Confirm Dialogs

Use `<AlertDialog>` for all destructive or irreversible actions:
- Delete entity
- Withdraw submission
- Cancel meeting
- Publish decision (cannot unpublish)
- Approve case closure (makes case read-only)

Pattern: exactly as in `frontend_core_patterns.md` §4.7.

---

## Phase 12 — State & Async Handling

### 12.1 Loading States

**List pages:** dashed border loading banner with `Loader2` spinner (never full-screen block):
```tsx
{isLoading && (
  <div className="mb-4 flex items-center rounded-md border border-dashed bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    Loading...
  </div>
)}
```

**Detail pages:** centered spinner in `min-h-[300px]`:
```tsx
if (isLoading) {
  return (
    <div className="flex items-center justify-center min-h-[300px]">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}
```

**Dialogs:** spinner gate before rendering form when lookup data is loading:
```tsx
{isLoadingLookups ? (
  <div className="flex items-center justify-center py-8">
    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
  </div>
) : (
  <Form>{/* fields */}</Form>
)}
```

### 12.2 Mutation Pending States

- Disable submit/action buttons with `disabled={mutation.isPending}`
- Show spinner in button: `<Loader2 className="mr-2 h-4 w-4 animate-spin" />`
- Disable Cancel button in dialogs during pending mutations
- Never hide buttons for pending state — only disable

### 12.3 Error States

- Check `isError || !data` before rendering detail pages
- Show `<Alert variant="destructive">` with descriptive message
- Include "Go Back" button below error alert on detail pages

### 12.4 Optimistic Updates

Not used. All mutations invalidate query cache on success:
```tsx
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: legalMeetingKeys.lists() });
}
```

---

## Phase 13 — Navigation & UX Consistency

### 13.1 Sidebar Integration

Legal section in GRC sidebar is a collapsible group. Each Legal page is a direct child nav item.

Sidebar active state: highlight based on current route path prefix `/service/grc/legal/`.

### 13.2 Back Navigation

All detail pages use deterministic back navigation (NOT `navigate(-1)`):
```tsx
const handleBack = () => navigate('/service/grc/legal/meetings');
```

### 13.3 After Create Navigation

- Cases: navigate to detail page after creation (Option A)
- Meetings: navigate to detail page after creation (Option A)
- Smaller entities (CommitteeType, Filing, etc.): stay on list/parent, close dialog (Option B)

### 13.4 Layout Consistency

- List pages: `<div className="space-y-4">` — no outer `p-4`
- Detail pages: `<div className="space-y-4 p-4">` — 16px padding
- No `space-y-6` or `p-6` anywhere
- Cards follow exact pattern from `NEW_DETAIL_PAGE_REFERENCE.md`

---

## Phase 14 — Integration with Workflow Service

### 14.1 Workflow-Enabled Entities

| Entity | Template Code | Entity Type Key |
|---|---|---|
| Meeting | `grc.legal_meeting_lifecycle` | `legal-meeting` |
| Minutes | `grc.legal_minutes_approval` | `legal-minutes` |
| CaseDefendant | `grc.legal_case_closure` | `legal-case-defendant` |
| CasePlaintiff | `grc.legal_case_closure` | `legal-case-plaintiff` |
| ~~FilingDefendant~~ | ~~`grc.legal_filing_approval`~~ | ~~`legal-filing-defendant`~~ — **REMOVED: Filings use domain-level status machine, not WO workflow. See Addendum A.10.6.** |
| ~~FilingPlaintiff~~ | ~~`grc.legal_filing_approval`~~ | ~~`legal-filing-plaintiff`~~ — **REMOVED: See above.** |
| SettlementDefendant | `grc.legal_settlement_approval` | `legal-settlement-defendant` |
| SettlementPlaintiff | `grc.legal_settlement_approval` | `legal-settlement-plaintiff` |
| JudgmentDefendant | `grc.legal_judgment_decision` | `legal-judgment-defendant` |
| JudgmentPlaintiff | `grc.legal_judgment_decision` | `legal-judgment-plaintiff` |

### 14.2 Workflow Hooks

Create `useLegalWorkflows.ts`:

```tsx
useLegalWorkflowStatus(entityType: string, entityId: string)
useLegalWorkflowHistory(entityType: string, entityId: string)
```

Follow exact pattern from `useGRCWorkflows.ts`. `staleTime: 30_000`, `retry: 1`.

### 14.3 Workflow Stage Display

- Detail pages fetch `workflowStatus` and display current stage in the header badge area
- Workflow history is displayed inside `EmbeddedWorkflowConsole`
- Stage transitions triggered by CTA buttons call the backend action endpoint; on success, invalidate workflow status cache

### 14.4 EmbeddedWorkflowConsole Placement

On every workflow-enabled detail page:
- Always at the **bottom** of the page, full-width
- NOT in a side column, NOT inside a card alongside other content
- Props stay exactly the same as Internal Audit pattern:
  ```tsx
  <EmbeddedWorkflowConsole
    entityType="legal-meeting"
    entityId={meeting.id}
    entityTitle={meeting.title}
    workflowPlanId={workflowStatus?.workflow_plan_id || meeting.workflow_plan_id}
    onSubmit={canStartWorkflow ? handleStartWorkflow : undefined}
    isDraft={meeting.status === 'draft'}
  />
  ```

### 14.5 Reflecting Status Changes

- When a workflow stage advances (via WO console or CTA button), the backend updates the entity's `status` field
- Frontend refetches the entity detail query (`invalidateQueries`) to reflect the new status
- Status badge on the header updates automatically via React Query stale invalidation
- No manual state management for workflow status — rely on server state via React Query

---

## Phase 15 — Testing & Validation

### 15.1 UI Behavior Checks

For each page, verify:
- [ ] Loading state renders correctly (spinner, no raw data flash)
- [ ] Error state renders correctly (destructive Alert with message)
- [ ] Empty state renders correctly (GenericListPage empty message)
- [ ] Pagination works (page change, page size change resets to page 1)
- [ ] Search filter works and resets page to 1
- [ ] Create dialog opens, validates, submits, closes on success, shows toast
- [ ] Edit dialog pre-fills values, submits update, closes on success
- [ ] Delete confirmation dialog opens, deletes on confirm, closes on settled
- [ ] Detail page loads, displays all cards with correct data
- [ ] Back button navigates to list page (not browser back)
- [ ] Status badges display correct colors for all statuses

### 15.2 API Integration Checks

For each entity, verify:
- [ ] List endpoint returns paginated data with correct shape
- [ ] Detail endpoint returns full entity with nested relations
- [ ] Create mutation sends correct payload, invalidates list cache
- [ ] Update mutation sends PATCH, invalidates both list and detail caches
- [ ] Delete mutation calls DELETE, invalidates list cache
- [ ] Action endpoints (register, submit, approve, etc.) return updated entity
- [ ] Error responses display correct error messages via toast

### 15.3 RBAC Validation

For each role, verify:
- [ ] Buttons hidden when permission absent (not just disabled)
- [ ] Row actions (`onEdit`, `onDelete`) pass `undefined` when not permitted
- [ ] Status-gated buttons only appear in valid statuses
- [ ] Secretary-gated actions check current user against `secretary_user_ids`
- [ ] DG-gated actions only appear for DG role
- [ ] Filing approval chain: correct buttons at each stage for each role
- [ ] Closed/read-only entities show no edit/action buttons

### 15.4 Workflow Validation

For each workflow-enabled entity, verify:
- [ ] Workflow console renders State A (loading), State B (active), State C (not started)
- [ ] Submit buttons trigger workflow start correctly
- [ ] Stage transitions update status badge and card content
- [ ] Workflow history displays in the console iframe
- [ ] "Open in New Tab" button works when workflow active

---

## Phase 16 — Implementation Order

Execute in this exact sequence. Each step depends on the previous.

### Step 1: Foundation Layer
1. `types/legal.ts` — all type definitions and status maps
2. `hooks/legalKeys.ts` — query key factories
3. `services/legalService.ts` — all API functions
4. `hooks/useLegalPermissions.ts` — permission hook
5. `hooks/useLegalConfig.ts` — lookup hooks
6. `hooks/useLegalWorkflows.ts` — workflow status/history hooks
7. `components/grc/legal/LegalStatusBadge.tsx` — shared status badge component
8. Routing: add Legal routes to `App.tsx`
9. Sidebar: add Legal nav section to service layout config

### Step 2: Governance Structure (Admin/Setup)
10. `hooks/useCommitteeTypes.ts`
11. `components/grc/legal/CreateCommitteeTypeDialog.tsx`
12. `pages/grc/legal/CommitteeTypesPage.tsx`
13. `hooks/useGoverningBodies.ts`
14. `hooks/useMembers.ts`
15. `components/grc/legal/CreateGoverningBodyDialog.tsx`
16. `components/grc/legal/CreateMemberDialog.tsx`
17. `pages/grc/legal/GoverningBodiesPage.tsx`
18. `pages/grc/legal/GoverningBodyDetailPage.tsx`
18a. `pages/grc/legal/MembersPage.tsx` — standalone list page for admin-level cross-body member view

### Step 3: Determinations
19. `hooks/useSubmissions.ts`
20. `components/grc/legal/CreateSubmissionDialog.tsx`
21. `pages/grc/legal/SubmissionsPage.tsx`
22. `pages/grc/legal/SubmissionDetailPage.tsx`

### Step 4: Meeting Governance
23. `hooks/useLegalMeetings.ts`
24. `hooks/useMeetingAgenda.ts`
25. `hooks/useMeetingParticipants.ts`
26. `hooks/useMeetingDirectives.ts`
27. `hooks/useMinutes.ts`
28. `hooks/useResolutions.ts`
29. `components/grc/legal/CreateMeetingDialog.tsx`
30. `components/grc/legal/MeetingAgendaSection.tsx`
31. `components/grc/legal/MeetingParticipantsSection.tsx`
32. `components/grc/legal/ConflictDeclarationDialog.tsx`
33. `components/grc/legal/CreateDirectiveDialog.tsx`
33a. `components/grc/legal/CloseDirectiveDialog.tsx`
33b. `components/grc/legal/FullyCloseDirectiveDialog.tsx`
34. `components/grc/legal/MattersArisingSection.tsx`
35. `components/grc/legal/CreateMinutesDialog.tsx`
36. `pages/grc/legal/LegalMeetingsPage.tsx`
37. `pages/grc/legal/LegalMeetingDetailPage.tsx`
38. `pages/grc/legal/DirectivesPage.tsx`
39. `pages/grc/legal/DirectiveDetailPage.tsx`
40. `pages/grc/legal/MinutesPage.tsx`
41. `pages/grc/legal/MinutesDetailPage.tsx`
42. `pages/grc/legal/ResolutionsPage.tsx`

### Step 5: Litigation — FCC Sued
43. `hooks/useCaseDefendant.ts`
44. `hooks/useLitigationDirectives.ts`
45. `hooks/useFilings.ts`
46. `hooks/useResponses.ts`
47. `hooks/useHearings.ts`
48. `hooks/useSettlements.ts`
49. `hooks/useJudgments.ts`
50. `hooks/useFinancials.ts`
51. `hooks/useLitigationTasks.ts`
52. `components/grc/legal/CreateCaseDefendantDialog.tsx`
53. `components/grc/legal/CaseDirectivesSection.tsx`
54. `components/grc/legal/CreateFilingDialog.tsx`
55. `components/grc/legal/CaseFilingsSection.tsx`
56. `components/grc/legal/CreateResponseDialog.tsx`
57. `components/grc/legal/CaseResponsesSection.tsx`
58. `components/grc/legal/CreateHearingDialog.tsx`
59. `components/grc/legal/HearingReportDialog.tsx`
60. `components/grc/legal/CaseHearingsSection.tsx`
61. `components/grc/legal/CreateSettlementDialog.tsx`
62. `components/grc/legal/CaseSettlementSection.tsx`
63. `components/grc/legal/RecordJudgmentDialog.tsx`
64. `components/grc/legal/CaseJudgmentSection.tsx`
65. `components/grc/legal/FinancialRecordDialog.tsx`
66. `components/grc/legal/CaseFinancialsSection.tsx`
67. `components/grc/legal/CreateLitigationTaskDialog.tsx`
68. `components/grc/legal/CaseTasksSection.tsx`
69. `pages/grc/legal/FCCSuedCasesPage.tsx`
70. `pages/grc/legal/FCCSuedCaseDetailPage.tsx`

### Step 6: Litigation — FCC Suing
71. `hooks/useCasePlaintiff.ts`
72. `components/grc/legal/CreateCasePlaintiffDialog.tsx`
73. `components/grc/legal/BreachReportIntakeDialog.tsx`
74. `pages/grc/legal/FCCSuingCasesPage.tsx`
75. `pages/grc/legal/FCCSuingCaseDetailPage.tsx`

> Note: FCC Suing reuses all child section components from Step 5 (`CaseFilingsSection`, etc.) — they already accept `caseType` prop to distinguish defendant vs plaintiff.

### Step 7: Public Register
76. `hooks/usePublicDecisions.ts`
77. `components/grc/legal/CreatePublicDecisionDialog.tsx`
78. `pages/grc/legal/PublicRegisterPage.tsx`
79. `pages/grc/legal/PublicDecisionDetailPage.tsx`

### Step 8: Integration Testing & Polish
80. End-to-end flow testing: Create governing body → Add members → Create submission → Create meeting → Add agenda → Start meeting → Record outcome → Create directives → Draft minutes → Approve minutes
81. End-to-end litigation flow: Register case → DG review → Create filing → Approve filing → Record hearing → Record judgment → DG decision → Closure
82. RBAC matrix validation for all roles
83. Workflow console integration testing for all 10 workflow entities
84. Status badge color verification across all entity types
85. Responsive layout verification (mobile, tablet, desktop)

> **Additional from A.15:**
86. CloseDirectiveDialog form: CompletionSummary (required), CompletionDate (required), evidence doc (optional) — verify submit disabled without summary
87. FullyCloseDirectiveDialog confirmation: directive disappears from Matters Arising after fully closed
88. MembersPage: cross-body member list, governing_body filter, Active/Former toggle
89. MeetingAgendaSection: SmartSelect only shows submissions matching meeting's governing body and status = submitted
90. CreateMeetingDialog: SmartSelect only shows governing bodies where current user is Secretary (when not Admin)
91. ResolutionsPage: empty state message shown (not error) when no resolutions accessible; no Create button visible
92. CaseFinancialsSection: External Payments / Revenue Collection links appear conditionally based on judgment outcome

---

---

## ADDENDUM A — Gap Closures & Corrections

> This addendum addresses gaps identified during cross-referencing with ALL backend/design references, the SRS (`Legal_Service.md`), and the three frontend standards guides. Items are organized by the Phase they correct or extend.

---

### A.1 Phase 2 Corrections — Missing Type Fields & Enums

#### A.1.1 TimestampedModel / Audit Fields

Only entities that inherit `TimestampedModel` (not bare `BaseModel`) include `created_by` / `modified_by`. Per Base Models §11 Quick Reference, the distinction is:

- **Lookup models** (`CourtLevel`, `LitigationUrgencyLevel`, `LitigationRiskLevel`, `MeetingMode`, `MeetingType`, `DirectivePriority`, `DirectiveCategory`): `BaseModel + StatusMixin` only — **NO** `created_by`/`modified_by`.
- **`CommitteeType`**: `BaseModel + StatusMixin` only — **NO** `created_by`/`modified_by`. It is admin-managed config data, not a user-audited business entity.
- **All other business entities** listed below: DO include `created_by`/`modified_by` (they inherit `TimestampedModel`).

```ts
// Add ONLY to entities with TimestampedModel (NOT CommitteeType, NOT lookup models):
created_by?: string;   // UUID of the creating user
modified_by?: string;   // UUID of last modifier
```

Affected entities (TimestampedModel inheritors): `GoverningBody`, `Member`, `SubmissionForDetermination`, `LegalMeeting`, `MeetingAgenda`, `ConflictDeclaration`, `MeetingParticipant`, `MeetingDirective`, `Minutes`, `Resolution`, `CaseDefendant`, `CasePlaintiff`, all child litigation entities, `PublicDecision`.

**NOT affected:** `CommitteeType` and all lookup model types.

#### A.1.2 Missing Fields per Entity

**LegalMeeting — add:**
```ts
total_member_count: number;
rsvp_yes_count: number;
rsvp_no_count: number;
rsvp_pending_count: number;
calculated_quorum_threshold: number;  // server-computed from meeting_type.quorum_percentage × total_member_count
```

**MeetingAgenda — add:**
```ts
outcome_notes?: string;          // qualification/notes on the outcome
outcome_recorded_at?: string;    // ISO timestamp when outcome was set
directives_created: string[];    // UUIDs of auto-created MeetingDirective records
is_active: boolean;
```

**ConflictDeclaration — add:**
```ts
declared_at: string;    // auto_now_add timestamp
is_active: boolean;
```

**MeetingParticipant — add:**
```ts
responded_at?: string;  // when RSVP changed from pending
is_active: boolean;
```

**MeetingDirective — add:**
```ts
finally_closed_at?: string;     // when Secretary performed final closure
finally_closed_by?: string;     // UUID of the Secretary who closed it
is_active: boolean;
```

**SubmissionForDetermination — add:**
```ts
directives_created: string[];   // UUIDs of auto-created directives from outcome
```

**Minutes — add:**
```ts
is_active: boolean;
```

**CaseDefendant / CasePlaintiff — add:**
```ts
case_folder_url?: string;       // link to Document Records Service folder
```

**FilingDefendant / FilingPlaintiff — add:**
```ts
approval_chain: ApprovalChainEntry[];  // audit trail of approval steps
```

**Where:**
```ts
interface ApprovalChainEntry {
  stage: string;
  actor_id: string;
  actor_name: string;
  action: 'approved' | 'rejected' | 'returned';
  timestamp: string;
  signature_hash?: string;       // e.g. "sha256:abc..."
  comments?: string;
}
```

#### A.1.3 Missing / Corrected Enum Values

**Resolution statuses** — change from unspecified to:
```ts
RESOLUTION_STATUSES = ['approved', 'rejected', 'noted'];
```

**FinancialEntry status** — specify explicitly:
```ts
FINANCIAL_ENTRY_STATUSES = ['requested', 'approved', 'processed'];
```

**CasePlaintiff additional field — registration_source:**
```ts
registration_source: 'full_report' | 'breach_report_intake';
```

#### A.1.4 LegalAuditLog Type (CORRECTED)

The actual `LegalAuditLog` Django model (from `Base_Models_Mixins.md` §11) is an append-only record with these exact fields. The TypeScript type must mirror them precisely:

```ts
// From legal_audit_log db table — append-only, never updated or deactivated
interface LegalAuditLog {
  id: string;              // UUID PK (from BaseModel)
  created_at: string;      // ISO timestamp (from BaseModel — this IS the event timestamp)
  entity_type: string;     // e.g. 'filing_defendant', 'meeting', 'case_defendant'
  entity_id: string;       // UUID of the entity
  action: string;          // e.g. 'created', 'status_changed', 'approved', 'workflow_action'
  actor_id: string;        // UUID of the user who performed the action (from IAM)
  stage_name: string;      // workflow stage name (blank-string if not a workflow action)
  comment: string;         // optional actor comment (blank-string if none)
  metadata: Record<string, unknown>; // arbitrary key-value context (JSON)
  // NOTE: no is_active (immutable — never soft-deleted)
  // NOTE: no created_by / modified_by mixin fields — actor is part of payload
  // NOTE: actor_name is NOT stored — resolve at display time via IAMClient cache
}
```

**Key differences from the previous definition:**
- NO `previous_value` / `new_value` fields — state diff is not part of this log table
- NO `description` field — use `action` + `comment` + `metadata` instead
- NO `actor_name` — always resolve UUID → name via `UserDisplay` component
- `stage_name` and `comment` are blank strings (not nullable) when not applicable
- `created_at` serves as the event timestamp — there is no separate `timestamp` field

---

### A.2 Phase 3 Corrections — Missing Endpoints & Contracts

#### A.2.1 Additional Endpoints

| Function | Method | Endpoint |
|---|---|---|
| `getAuditLog(entityType, entityId)` | GET | `/api/v1/legal/audit-log/?entity_type={type}&entity_id={id}` |
| `markAttendance(meetingId, participantId)` | POST | `/api/v1/legal/meetings/{id}/participants/{pid}/mark-attendance/` |
| `resumeMeeting(id)` | POST | `/api/v1/legal/meetings/{id}/resume/` |
| `getMattersArising(governingBodyId)` | GET | `/api/v1/legal/directives/matters-arising/?body={id}` |
| `getLookupCourtLevels()` | GET | `/api/v1/legal/lookups/court-levels/` |
| `getLookupUrgencyLevels()` | GET | `/api/v1/legal/lookups/urgency-levels/` |
| `getLookupRiskLevels()` | GET | `/api/v1/legal/lookups/risk-levels/` |
| `getLookupMeetingModes()` | GET | `/api/v1/legal/lookups/meeting-modes/` |
| `getLookupMeetingTypes()` | GET | `/api/v1/legal/lookups/meeting-types/` |
| `getLookupDirectivePriorities()` | GET | `/api/v1/legal/lookups/directive-priorities/` |
| `getLookupDirectiveCategories()` | GET | `/api/v1/legal/lookups/directive-categories/` |

#### A.2.2 Lookup Response Shape

All lookup endpoints return:
```ts
interface LookupItem {
  id: string;
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
  color_code?: string;          // hex color for UI badges (on urgency, risk, priority lookups)
  // Lookup-specific extra fields:
  requires_venue_link?: boolean; // MeetingMode only
  quorum_percentage?: number;    // MeetingType only
}
```

#### A.2.3 Pagination Response Shape

All list endpoints return:
```ts
interface PaginatedResponse<T> {
  results: T[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}
```

Frontend must extract `meta.total_pages` for GenericListPage pagination. Max `page_size` enforced at 100 — frontend must clamp values.

#### A.2.4 Error Response Shape

Backend errors follow this structure:
```ts
// Business rule violation / validation error:
{ error: string; details?: Record<string, string[]> }

// 409 Conflict (unique constraint):
{ error: "Duplicate record"; field: string }
```

Frontend extracts: `error.response?.data?.error || error.message`
For field-level errors: map `details` keys to form field errors via `form.setError()`.

#### A.2.5 Nested vs ID Responses

- **List endpoints:** Return flat IDs for FK fields (e.g., `governing_body: "uuid"`) PLUS a `governing_body_name: string` denormalized display field.
- **Detail endpoints:** Return nested objects for primary FKs (e.g., `governing_body: { id, name, committee_type: {...} }`).
- **Write endpoints (POST/PATCH):** Accept flat IDs only (e.g., `governing_body: "uuid"`).

Convention: Serializer uses `source=` to flatten nested reads but accepts IDs for writes. Frontend types should define both:
```ts
// For list display:
interface MeetingListItem {
  governing_body: string;
  governing_body_name: string;  // denormalized
}

// For detail display:
interface MeetingDetail {
  governing_body: GoverningBody; // full nested object
}
```

---

### A.3 Phase 4 Corrections — Query Key Factory Additions

Add to `legalKeys.ts`:

```ts
legalAuditLogKeys.all / byEntity(entityType, entityId)
mattersArisingKeys.all / byGoverningBody(governingBodyId)
```

Also add filter serialization helper matching the GRC pattern:
```ts
import { serializeFilters } from '../hooks/grcKeys'; // reuse existing serializer

export const legalMeetingKeys = {
  all: ['legal-meetings'] as const,
  lists: () => [...legalMeetingKeys.all, 'list'] as const,
  list: (page: number, pageSize: number, filterKey: string) =>
    [...legalMeetingKeys.lists(), page, pageSize, filterKey] as const,
  details: () => [...legalMeetingKeys.all, 'detail'] as const,
  detail: (id: string) => [...legalMeetingKeys.details(), id] as const,
};
// Apply this pattern to ALL entity key factories.
```

---

### A.4 Phase 6 Corrections — Lookup Hook Enhancements

#### A.4.1 Color Code Usage

Lookup items with `color_code` (urgency, risk, priority) must use the server-provided color for badge rendering:

```tsx
// In list columns and detail pages:
<span
  className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium"
  style={{ backgroundColor: `${lookup.color_code}20`, color: lookup.color_code }}
>
  {lookup.name}
</span>
```

Do NOT hardcode badge colors for urgency/risk/priority — always use the `color_code` from the lookup response.

#### A.4.2 Conditional Field Visibility from Lookups

- `MeetingMode.requires_venue_link`:  
  When creating/editing a meeting, show the `venue_link` field ONLY when the selected `MeetingMode` has `requires_venue_link === true`:
  ```tsx
  const selectedMode = meetingModes?.find(m => m.id === form.watch('mode'));
  {selectedMode?.requires_venue_link && (
    <FormField name="venue_link" ... />
  )}
  ```

- `MeetingType.quorum_percentage`:  
  On Meeting detail page, display informational text:
  ```tsx
  <span className="text-sm text-muted-foreground">
    ({meetingType.quorum_percentage}% quorum = {meeting.calculated_quorum_threshold} of {meeting.total_member_count} members)
  </span>
  ```

#### A.4.3 Deactivated Lookup Display Rules

- **In create/edit forms (dropdowns):** Show ONLY `is_active === true` lookups.
- **In detail views (read-only display):** Show the stored lookup value EVEN if it has since been deactivated. Append a "(Deactivated)" label in `text-muted-foreground`.

---

### A.5 Phase 7 Corrections — List Page Specifications

#### A.5.1 Per-Page Filter Requirements

| Page | Text Search Fields | Status Filter | Date Filter | FK Filter |
|---|---|---|---|---|
| CommitteeTypesPage | code, name | is_active (Active/Inactive) | — | — |
| GoverningBodiesPage | name | is_active | — | committee_type |
| SubmissionsPage | title | status (submitted/under_review/determined/withdrawn) | submission_date range | target_body |
| LegalMeetingsPage | title, meeting_number | status (all 10 values) | start_datetime range | governing_body |
| DirectivesPage | description | status (open/in_progress/overdue/closed/fully_closed) | due_date range | governing_body |
| MinutesPage | title | status (draft/pending_approval/approved) | — | — |
| ResolutionsPage | resolution_text | status (approved/rejected/noted) | date_adopted range | — |
| FCCSuedCasesPage | case_id, court_case_number | stage (all values) | service_date range | urgency_level, risk_level |
| FCCSuingCasesPage | case_id | stage (all values) | — | urgency_level, risk_level |
| PublicRegisterPage | title | status (draft/published) | decision_date range | — |

#### A.5.2 Urgency/Risk Visual Indicators in Lists

For FCCSuedCasesPage and FCCSuingCasesPage, urgency and risk columns must render using the lookup's `color_code`:
- High urgency/risk: colored badge with server-provided color
- Default sort: cases sorted by `urgency_level` descending (highest urgency first)

#### A.5.3 Soft-Delete Filtering

All list pages MUST pass `is_active=true` as a default filter parameter. Backend should also enforce this, but frontend adds it as defense-in-depth:
```ts
const { data } = useMeetings(page, pageSize, { ...filters, is_active: true });
```

#### A.5.4 List Page Wrapper Class (Compliance Rule)

All Legal list pages use exactly: `<div className="space-y-4">` — **no `p-4`**, **no `space-y-6`**. Detail pages use `<div className="space-y-4 p-4">`. This is non-negotiable per `frontend_core_patterns.md` §5.2.

---

### A.6 Phase 8 Corrections — Detail Page Enhancements

#### A.6.1 Resume Meeting CTA (Missing from LegalMeetingDetailPage)

Add CTA:
- **"Resume Meeting"** — visible when `status === 'postponed'` AND user is Secretary
- Calls `resumeMeeting(id)` → transitions status from `postponed` → `ongoing`
- Toast: "Meeting resumed"

Updated CTA list for LegalMeetingDetailPage:
```
"Register Meeting"  — status = draft, Secretary only
"Share Agenda"      — status = invitations_sent, Secretary only  
"Start Meeting"     — status = quorum_ready AND quorum_met = true, Secretary only
"Resume Meeting"    — status = postponed, Secretary only          ← NEW
"Postpone"          — status = ongoing, Secretary only
"Close Meeting"     — status = ongoing, Secretary only
"Cancel"            — status in (draft, registered), Secretary only
"Reschedule"        — status in (draft, registered, postponed), Secretary only
```

#### A.6.2 Quorum Progress Display (LegalMeetingDetailPage)

Add to Meeting Details Card:
```tsx
<div className="text-sm text-muted-foreground">
  Quorum: {meeting.rsvp_yes_count} / {meeting.total_member_count} accepted
  ({meeting.quorum_percentage}% — threshold: {meeting.calculated_quorum_threshold})
</div>
{meeting.quorum_met ? (
  <span className="text-xs text-green-600 font-medium">Quorum met ✓</span>
) : (
  <span className="text-xs text-amber-600 font-medium">Quorum not met</span>
)}
```

Also add RSVP breakdown to Participants Section:
- Accepted: `{meeting.rsvp_yes_count}`
- Declined: `{meeting.rsvp_no_count}`
- Pending: `{meeting.rsvp_pending_count}`

#### A.6.3 Attendance Marking (MeetingParticipantsSection)

When meeting status is `ongoing`:
- Each participant row shows a checkbox for attendance marking
- Secretary can click to toggle `attendance_marked`
- Calls `markAttendance(meetingId, participantId)`
- Non-secretary users see read-only attendance status

#### A.6.4 Conflict of Interest Display (LegalMeetingDetailPage → MeetingAgendaSection)

For each agenda item, display conflict declarations:
- Show a "Conflicts" sub-row or expandable section under each agenda item
- List declared conflicts: member name + reason + declared_at timestamp
- Members with active conflicts show a ⚠ icon badge next to their name in the Participants table for that agenda item
- When recording agenda outcome, excluded members (those with conflicts) should be visually indicated (strikethrough or grayed out) — they are excluded from voting on that item

#### A.6.5 Digital Signature Display

On all approval-chain entities (filings, settlements, judgments), after approval:
- Show an "Approval Chain" card or section listing all approval steps:
  ```
  ┌────────────────────────────────────────────┐
  │ 👤 Approval Chain                          │
  ├────────────────────────────────────────────┤
  │ 1. Legal Manager — Approved — 14 Mar 2026  │
  │    Signed: sha256:abc123...                │
  │ 2. Director General — Approved — 15 Mar 26 │
  │    Signed: sha256:def456...                │
  └────────────────────────────────────────────┘
  ```
- `ApprovalChainEntry` records fetched as part of filing/settlement/judgment detail response
- Signature hash displayed as `font-mono text-xs text-muted-foreground`
- Frontend does NOT verify signatures — this is backend-only. Display is informational.

#### A.6.6 Audit History Section (All Detail Pages)

Add an "Activity Log" collapsible section at the bottom of EVERY detail page (above the workflow console if present):

```tsx
<Card>
  <CardHeader className="pb-2">
    <CardTitle className="text-base flex items-center gap-2">
      <History className="h-4 w-4" />
      Activity Log
    </CardTitle>
  </CardHeader>
  <CardContent>
    {auditEntries.map(entry => (
      <div key={entry.id} className="flex items-start gap-3 py-2 border-b last:border-0">
        <span className="text-xs text-muted-foreground whitespace-nowrap">{formatDate(entry.timestamp)}</span>
        <span className="text-sm">{entry.actor_name}</span>
        <span className="text-sm text-muted-foreground">{entry.description}</span>
      </div>
    ))}
  </CardContent>
</Card>
```

Uses `getAuditLog(entityType, entityId)` from legalService. Query key: `legalAuditLogKeys.byEntity(type, id)`.

#### A.6.7 Case Folder Link (FCCSuedCaseDetailPage / FCCSuingCaseDetailPage)

In the Case Details Card, add:
```tsx
{caseData.case_folder_url && (
  <div>
    <span className="text-sm text-muted-foreground">Case Folder</span>
    <a href={caseData.case_folder_url} target="_blank" rel="noopener noreferrer"
       className="text-sm font-medium text-blue-600 hover:underline flex items-center gap-1">
      <ExternalLink className="h-3 w-3" /> Open in Document Records
    </a>
  </div>
)}
```

#### A.6.8 DG Review Outcome Indicator (FCCSuedCaseDetailPage / FCCSuingCaseDetailPage)

In the DG Review Card, when stage moves past `under_dg_review`, show which outcome occurred:
- If `litigationDirectives.length > 0` where `issued_by === DG` → show "DG issued directive" badge
- If `dg_review_status === 'reviewed'` and no DG directive → show "DG reviewed — no directive" badge

#### A.6.9 Appeal Flow After DG Decision (FCCSuedCaseDetailPage)

When DG selects "Appeal" on a judgment:
1. Backend atomically creates: `FilingDefendant` (Notice of Appeal) + `TaskLitigation` (appeal prep task)
2. Frontend receives response including `{ filing_id, task_id }` from `dgDecisionOnJudgment()`
3. Show toast: "Appeal initiated — Notice of Appeal filing created"
4. Invalidate: `filingKeys.byCase(caseId)`, `litigationTaskKeys.byCase(caseId)`, `caseDefendantKeys.detail(caseId)`
5. Case stage transitions to `appeal_filed`

#### A.6.10 Read-Only Mode for Closed Cases

When `case.stage === 'closed'`:
- Show yellow banner at top: "This case is closed and read-only"
- Hide ALL action buttons (create filing, hearing, settlement, etc.)
- Hide edit actions on child entity rows
- `EmbeddedWorkflowConsole` shows completed state (no actions)
- Do NOT just check permissions — check stage independently:
  ```tsx
  const isCaseClosed = caseData.stage === 'closed';
  // ALL create/edit buttons gated on: !isCaseClosed && hasPermission
  ```

#### A.6.11 Submission Locking Feedback

On `SubmissionDetailPage`, when `status !== 'submitted'`:
- Show info banner: "This submission is linked to a meeting agenda and can no longer be edited."
- Hide Edit and Withdraw buttons entirely (not just for permissions, but for locked status)
- When `status === 'determined'`, show the Outcome Card with meeting link:
  ```tsx
  {submission.meeting_id && (
    <Button variant="link" onClick={() => navigate(`/service/grc/legal/meetings/${submission.meeting_id}`)}>
      View Determining Meeting
    </Button>
  )}
  ```

#### A.6.12 HearingReport NextHearingDate Propagation

After creating a `HearingReport` via `HearingReportDialog`, invalidate:
- `hearingKeys.byCase(caseId)` — to refresh hearing list
- `caseDefendantKeys.detail(caseId)` OR `casePlaintiffKeys.detail(caseId)` — to refresh `next_hearing_date` on the case header

This ensures the case detail card's "Next Hearing Date" updates automatically without manual page refresh.

#### A.6.13 Detail Page Title Rules (Frontend Guide Compliance)

- `<h1>` contains ONLY text. No icons inside the `<h1>` tag.
- Status badge and icons go OUTSIDE the h1, in the same flex row.
- Back button: `<ChevronLeft>` icon (NOT `<ArrowLeft>`), `variant="ghost"`, `size="icon"`, `aria-label="Back"`
- Title font: `text-2xl font-semibold` (NOT `font-bold`)
- Subtitle: `text-sm text-muted-foreground`, reference numbers in `font-mono`

#### A.6.14 Conditional Card Rendering Rule

All optional/conditional cards are NOT rendered if their display condition is false. Never render an empty card with "—" placeholders for missing data. This applies to:
- Description Card (if no description)
- DG Review Card (if stage ≠ under_dg_review)
- Outcome Card on submissions (if status ≠ determined)
- Settlement Card (if no settlement exists)
- Judgment Card (if no judgment exists)
- Approval Info on Minutes (if not yet approved)

---

### A.7 Phase 9 Corrections — Form Enhancements

#### A.7.1 Dialog Overflow Rule

ALL dialogs must include `max-h-[90vh] overflow-y-auto` on the `DialogContent`:
```tsx
<DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
```
This prevents tall forms from pushing below the viewport. This is mandatory per `frontend_component_patterns.md` §3.1.

#### A.7.2 Form Section Headings

For multi-section dialogs (CreateCaseDefendantDialog, CreateMeetingDialog), use section separators:
```tsx
<h3 className="text-sm font-semibold text-foreground border-b pb-2">Court Information</h3>
```
NOT `text-muted-foreground` for section headings. Section headings separate logical groups of fields.

#### A.7.3 Data Cleaning on Submit

Every form's `onSubmit` handler must clean data before mutation:
```tsx
const cleanedData = {
  ...data,
  description: data.description?.trim() || undefined,
  venue_link: data.venue_link?.trim() || undefined,
  due_date: data.due_date || undefined,
  assigned_user_id: data.assigned_user_id || undefined,
  // All optional text fields: trim, convert empty to undefined
  // All optional FK fields: convert empty string to undefined
  // All optional date fields: convert empty to undefined
};
mutate(cleanedData);
```

#### A.7.4 Dynamic Field Array Pattern (Plaintiffs, Secretary IDs)

**For `plaintiffs` in CreateCaseDefendantDialog:** Use `useFieldArray` with bordered containers:
```tsx
{fields.map((field, index) => (
  <div key={field.id} className="border rounded-md p-3 space-y-3">
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium">Plaintiff {index + 1}</span>
      <Button variant="ghost" size="icon" onClick={() => remove(index)}>
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
    <FormField name={`plaintiffs.${index}.name`} ... />
  </div>
))}
<Button variant="outline" onClick={() => append({ name: '' })}>
  <Plus className="mr-2 h-4 w-4" /> Add Plaintiff
</Button>
```

**For `secretary_user_ids` in CreateGoverningBodyDialog:** Use multi-select `SmartSelect` with `isMultiple` — NOT `useFieldArray`. Secretaries are a UUID array, not structured objects.

#### A.7.5 SmartSelect Disabled in Edit Mode

All FK SmartSelect fields that link to parent entities must be disabled in edit mode:
```tsx
<SmartSelect
  value={form.watch('governing_body')}
  onChange={(val) => form.setValue('governing_body', val)}
  disabled={mode === 'edit'}  // prevent re-linking
/>
```
Applies to: `governing_body` in Member/Meeting, `case` in Filing/Response/Hearing, `meeting` in Agenda/Directive/Minutes.

#### A.7.6 Inline Alert for Empty FK Lookups

When a filtered FK dropdown returns 0 results, show an inline alert and disable submit:
```tsx
{mode === 'create' && closedMeetings.length === 0 && !isLoadingMeetings && (
  <Alert className="mt-2">
    <AlertTriangle className="h-4 w-4" />
    <AlertTitle>No Closed Meetings</AlertTitle>
    <AlertDescription>
      Public decisions can only be linked to closed meetings.
    </AlertDescription>
  </Alert>
)}
```
Applies to: CreatePublicDecisionDialog (closed meetings), CreateSubmissionDialog (active governing bodies).

#### A.7.7 Auto-Generated Reference Number Display

For case creation dialogs and meeting creation, the reference number is auto-generated by the backend. In create forms:
- Do NOT show a "Reference Number" field
- After successful creation, toast includes the generated reference: "Case created: FCC/SUED/2026/001"

For meeting_number: same pattern — show the generated number only in the success toast and on the detail page.

#### A.7.8 Directive Assignment Rule

For `CreateDirectiveDialog`, the `assigned_user_id` and `assigned_org_unit` fields follow this rule:
- At least one of the two is required
- Both can be populated (assigned to a specific user within an org unit)
- Validation: `z.object({ assigned_user_id: z.string().optional(), assigned_org_unit: z.string().optional() }).refine(data => data.assigned_user_id || data.assigned_org_unit, { message: 'Assign to a user or organizational unit' })`

---

### A.8 Phase 10 Corrections — RBAC Enhancements

#### A.8.1 Secretary Role Helper

Create a reusable helper for secretary checks:
```tsx
// In useLegalPermissions.ts:
export function useIsSecretary(governingBodySecretaryIds: string[] | undefined): boolean {
  const { userId } = useCurrentUser();
  return governingBodySecretaryIds?.includes(userId) ?? false;
}
```

Use this consistently across all meeting-related pages instead of ad-hoc comparisons.

#### A.8.2 Complete Permission Code Reference

The canonical permission codes are defined in `grc-service/config/permissions/grc-service.json` and published by grc-service to IAM on startup. See **Phase 5.1** for the complete list with all 28 codes and their convenience boolean mappings.

**Roles defined in `grc-service.json` and their permission sets:**

| Role | Key Permissions |
|---|---|
| `legal_manager` | `grc:legal_governing_body:view/manage`, `grc:legal_meeting:view/manage/approve`, `grc:legal_minutes:view/manage/approve`, `grc:legal_case:view/manage/close`, `grc:legal_filing:view/manage/approve`, `grc:legal_hearing:view/manage`, `grc:legal_settlement:view/manage/approve`, `grc:legal_judgment:view/manage/record`, `grc:legal_directive:view/manage`, `grc:legal_appeal:view/manage`, `grc:legal_notice:view/manage` |
| `legal_officer` | `grc:legal_governing_body:view`, `grc:legal_meeting:view`, `grc:legal_minutes:view`, `grc:legal_case:view/manage`, `grc:legal_filing:view/manage`, `grc:legal_hearing:view/manage`, `grc:legal_settlement:view/manage`, `grc:legal_judgment:view/manage`, `grc:legal_directive:view/manage`, `grc:legal_appeal:view`, `grc:legal_notice:view/manage` |
| Secretary | `grc:legal_governing_body:view/manage`, `grc:legal_meeting:view/manage`, `grc:legal_minutes:view/manage`, `grc:legal_directive:view/manage` |
| Meeting Member | `grc:legal_governing_body:view`, `grc:legal_meeting:view/approve`, `grc:legal_minutes:view/approve`, `grc:legal_directive:view` |

The permission codes are carried in the JWT `permissions_flat` array.

#### A.8.3 Row-Level Action Rendering

List pages pass action handlers conditionally per-row where needed:
```tsx
// Standard: same for all rows
onEdit={canManage ? handleEdit : undefined}

// Per-row (e.g., filings with different approval stages):
renderActions={(row) => (
  <>
    {row.status === 'draft' && row.submitted_by_user_id === userId && (
      <Button size="sm" onClick={() => submitFiling(row.id)}>Submit</Button>
    )}
    {row.status === 'under_review_lm' && canApproveFilings && (
      <Button size="sm" onClick={() => approveLM(row.id)}>Approve (LM)</Button>
    )}
    {row.status === 'under_review_dg' && canApproveFilings && (
      <Button size="sm" onClick={() => approveDG(row.id)}>Approve (DG)</Button>
    )}
    {row.status === 'approved' && canManageFilings && (
      <Button size="sm" onClick={() => markFiled(row.id)}>Mark Filed</Button>
    )}
  </>
)}
```

---

### A.9 Phase 12 Corrections — Overdue Status & Refresh

#### A.9.1 Overdue Task/Directive Detection

Backend Celery Beat task (`legal_task_deadlines.py`) runs daily at 06:00 to mark overdue items. Frontend does NOT need to poll or calculate overdue status client-side. Instead:

- React Query's `staleTime: 5 * 60 * 1000` ensures fresh data loads on page visit
- When user is on DirectivesPage or CaseTasksSection, the status column reflects backend-computed `overdue` status
- No shorter polling interval is needed — overdue transitions are daily, not real-time

#### A.9.2 Matters Arising Refresh

The MattersArisingSection on LegalMeetingDetailPage:
- Auto-populates when meeting status transitions to `ongoing` (backend side-effect)
- On the frontend, data is fetched using `getMattersArising(governingBodyId)` with standard `staleTime: 5 * 60 * 1000`
- Include a manual "Refresh" button (ghost variant, RefreshCw icon) for Secretary to re-fetch during long meetings
- Secretary can "Fully Close" a directive from this section → calls `fullyCloseDirective(directiveId, { meeting_id })` → invalidates matters arising cache

---

### A.10 Phase 14 Corrections — Workflow Integration Enhancements

#### A.10.1 Entity Status vs Workflow Stage Coordination

- The entity's own `status` field is the **source of truth** for UI display (badges, CTAs, card visibility)
- The `workflow_stage` field reflects the Work Orchestration service's view and drives the `EmbeddedWorkflowConsole`
- Backend automatically syncs: when a workflow stage advances, it updates the entity's `status` field
- Frontend does NOT directly read `workflow_stage` for UI state — it uses `status` (or `stage` for cases)
- After any workflow action, invalidate the entity detail query to pick up the new `status`

#### A.10.2 Workflow Available Actions Contract

`/api/v1/work-orchestration/plans/{planId}/actions/` returns:
```ts
interface WorkflowAction {
  name: string;          // e.g., "approve", "reject", "return"
  label: string;         // e.g., "Approve", "Reject", "Return for Revision"
  next_stage?: string;   // where the workflow goes after this action
  requires_comment: boolean;
}
```
The `EmbeddedWorkflowConsole` component handles this internally — frontend Legal code does NOT need to parse these.

#### A.10.3 Workflow History Data Shape

`/api/v1/work-orchestration/plans/{planId}/history/` returns:
```ts
interface WorkflowHistoryEntry {
  timestamp: string;
  actor_id: string;
  actor_name: string;
  action: string;
  from_stage: string;
  to_stage: string;
  comment?: string;
}
```
Rendered by `EmbeddedWorkflowConsole` internally.

#### A.10.4 Workflow SLA Display

Workflow templates define SLA targets (`sla.targetMinutes`, per-stage `sla.durationMinutes`). The `EmbeddedWorkflowConsole` component displays SLA information when available. Frontend Legal pages do NOT need custom SLA rendering — the console handles it.

#### A.10.5 Cancelled/Rejected Workflow State

When a workflow action results in `rejected`:
- Backend reverts entity status to previous state (e.g., Minutes `pending_approval` → `draft`)
- Frontend refetches entity detail — picks up reverted status
- Workflow console shows "Rejected" state with option to resubmit

#### A.10.6 Filing Approval — Status Machine vs Workflow Console

Filings use a **domain-level status machine** (draft → under_review_lm → approved_lm → under_review_dg → approved → filed), BUT the Django models for `FilingDefendant` and `FilingPlaintiff` DO inherit `WorkflowMixin` (confirmed by `Legal_Module_Base_Models_Mixins.md` §11 Quick Reference). This means:

- The five `WorkflowMixin` fields (`workflow_plan_id`, `workflow_stage`, `workflow_stage_id`, `workflow_started_at`, `workflow_completed_at`) **do appear** in the backend serializer and therefore **must be included** in the TypeScript `FilingDefendant` and `FilingPlaintiff` types.
- However, the **`EmbeddedWorkflowConsole` is NOT rendered** on filing detail views. The approval progresses via CTA buttons (Submit → Approve LM → Approve DG → Mark Filed) which call the domain-level status endpoints directly.
- Architecture Mapping §5.1 confirms: "grc-service owns filing approval state internally. Work Orchestration is used for delivery and reminders, not as the source of truth for domain state."

**TypeScript type correction — ensure FilingDefendant/FilingPlaintiff include all WorkflowMixin fields:**
```ts
interface FilingDefendant {
  // ... existing fields ...
  // WorkflowMixin fields (included because Django model inherits WorkflowMixin):
  workflow_plan_id?: string | null;
  workflow_stage: string;         // blank string when no WO plan active
  workflow_stage_id?: string | null;
  workflow_started_at?: string | null;
  workflow_completed_at?: string | null;
  // domain-level approval status (this is the source of truth for UI):
  status: 'draft' | 'under_review_lm' | 'approved_lm' | 'under_review_dg' | 'approved' | 'filed';
  approval_chain: ApprovalChainEntry[];
  // ... rest of fields ...
}
```

Apply the same WorkflowMixin fields to `FilingPlaintiff` type.

**Corrected Workflow-Enabled Entities:**

| Entity | Template Code | Entity Type Key |
|---|---|---|
| Meeting | `grc.legal_meeting_lifecycle` | `legal-meeting` |
| Minutes | `grc.legal_minutes_approval` | `legal-minutes` |
| CaseDefendant | `grc.legal_case_closure` | `legal-case-defendant` |
| CasePlaintiff | `grc.legal_case_closure` | `legal-case-plaintiff` |
| SettlementDefendant | `grc.legal_settlement_approval` | `legal-settlement-defendant` |
| SettlementPlaintiff | `grc.legal_settlement_approval` | `legal-settlement-plaintiff` |
| JudgmentDefendant | `grc.legal_judgment_decision` | `legal-judgment-defendant` |
| JudgmentPlaintiff | `grc.legal_judgment_decision` | `legal-judgment-plaintiff` |

#### A.10.7 Workflow Hook Type Signature

```tsx
useLegalWorkflowStatus(
  entityType: 'legal-meeting' | 'legal-minutes' | 'legal-case-defendant' | 'legal-case-plaintiff' |
              'legal-settlement-defendant' | 'legal-settlement-plaintiff' |
              'legal-judgment-defendant' | 'legal-judgment-plaintiff',
  entityId: string
)
```

---

### A.11 Phase 13 Corrections — Navigation & UX

#### A.11.1 Submission → Meeting Navigation

On SubmissionDetailPage when `status === 'determined'` and `meeting_id` is set, include:
- A link row in the Outcome Card: `"Determined in Meeting" → navigate to /service/grc/legal/meetings/{meeting_id}`
- The meeting link should show meeting_number and title for context

#### A.11.2 Task → Related Entity Navigation

On CaseTasksSection, for tasks with `related_entity_type` and `related_entity_id`:
- Show a "View Related" link that navigates to the related entity
- Entity type mapping: `filing` → filing detail within case, `hearing` → hearing section, etc.
- If related entity is a filing: `"Related: Notice of Appeal (Filing #FCC/SUED/2026/001-F03)"`

#### A.11.3 Members Filtering

On MembersPage and in GoverningBodyDetailPage → Members Section:
- Members with `left_date` set are filtered out from the active members list by default
- Add toggle: "Show former members" → includes members with `left_date` set (shown grayed out)

---

### A.12 Phase 15 Corrections — Additional Test Scenarios

Add these test scenarios to the validation checklists:

#### A.12.1 Meeting Lifecycle

- [ ] Register → auto-populates participants from governing body members
- [ ] Invitations auto-sent on registration (toast confirms)
- [ ] RSVP response updates quorum counters in real-time
- [ ] Quorum threshold display shows correct calculation
- [ ] Postpone → Resume flow works correctly
- [ ] Reschedule flow with new date/time works correctly
- [ ] Matters Arising auto-populates when meeting goes to ongoing
- [ ] Conflict declaration prevents member from voting on that agenda item
- [ ] Agenda outcome → auto-creates Resolution record
- [ ] Minutes approval workflow triggers correctly

#### A.12.2 Litigation Lifecycle

- [ ] DG "Appeal" decision → auto-creates filing + task (verify both appear)
- [ ] Filing approval chain: draft → LM approve → DG approve → filed (4-step chain)
- [ ] Filing ApprovalChain display shows all steps with timestamps
- [ ] Judgment DG decision with "accept" vs "appeal" branches correctly
- [ ] Case closure flow: request → approve → case becomes fully read-only
- [ ] Financial record/recovery conditional on judgment outcome
- [ ] HearingReport → updates case next_hearing_date
- [ ] Case folder link navigates to Document Records Service

#### A.12.3 Cross-Cutting

- [ ] Deactivated lookup values shown in read-only detail views with "(Deactivated)" label
- [ ] Audit history section loads and displays for all detail pages
- [ ] User UUIDs resolve to display names via `UserDisplay` component
- [ ] All dialogs respect `max-h-[90vh] overflow-y-auto`
- [ ] Form data cleaning removes empty strings before mutation
- [ ] 409 Conflict responses handled gracefully with user-friendly message
- [ ] CloseDirectiveDialog: requires completion_summary + completion_date; evidence doc optional
- [ ] FullyCloseDirectiveDialog: directive removed from Matters Arising after Secretary confirms
- [ ] MembersPage: Active/Former toggle filters by left_date; cross-body governing_body filter works
- [ ] MeetingAgendaSection SmartSelect: only submissions with matching target_body and status=submitted shown
- [ ] CreateMeetingDialog governing_body SmartSelect: filtered to secretary's assigned bodies for non-Admin users
- [ ] ResolutionsPage: empty state shown (not error) with descriptive participant-visibility message; no Create button
- [ ] CaseFinancialsSection: finance deep-links visible conditionally on judgment outcome (won/lost)

---

### A.13 Phase 16 Corrections — Updated Implementation Order

Insert after Step 1 (Foundation Layer), item 7:

```
7a. `hooks/useLegalAuditLog.ts` — audit log query hook
7b. `components/grc/legal/ActivityLogSection.tsx` — reusable audit log card
7c. `components/grc/legal/ApprovalChainDisplay.tsx` — reusable approval chain card
7d. `components/grc/legal/UserDisplay.tsx` — UUID → user name display component
```

Add to Step 8 (Integration Testing & Polish):
```
86. Audit history display verification for all detail pages
87. Approval chain display verification for filings/settlements/judgments
88. Quorum counter and RSVP tally verification
89. Conflict of interest display and exclusion verification
90. Meeting resume flow verification
91. Appeal auto-creation flow verification
92. Read-only closed case enforcement verification
```

---

### A.14 Cross-Cutting UI Pattern Rules (Frontend Guide Compliance)

These rules apply across ALL Legal module pages:

1. **Status badges:** Use Tailwind `className` overrides — NEVER `variant=` props on `<Badge>`. Per `frontend_core_patterns.md` §5.7.

2. **Status label formatting:** Use Title-Case with underscore replacement:
   ```ts
   const formatStatusLabel = (status: string) =>
     status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
   ```

3. **User display:** For all `*_by` UUID fields, use a shared `UserDisplay` component that resolves UUID → name via IAM cache. Pattern:
   ```tsx
   <UserDisplay userId={entity.created_by} fallback="System" />
   ```

4. **Back button:** Always `<ChevronLeft>` (NOT `<ArrowLeft>`), `variant="ghost"`, `size="icon"`, `aria-label="Back"`.

5. **Card headers:** `<CardHeader className="pb-2">` + `<CardTitle className="text-base flex items-center gap-2">` — inherits `font-semibold` from component default.

6. **No `<CardDescription>`**, no `<Separator>` components on detail pages.

7. **`font-semibold`** for detail page titles, **`font-bold`** for list page titles.

8. **Lookup lazy-loading:** All dialogs pass `isDialogOpen` as the `enabled` parameter to lookup hooks.

9. **Page-size ceiling:** Frontend clamps `pageSize` to max 100 before sending to API.

---

### A.15 LEGAL_DOMAIN_EXTRACTION.md — Additional Business Rule Enforcement

These rules come directly from section E of `LEGAL_DOMAIN_EXTRACTION.md` and were not explicitly represented in the implementation plan above.

---

#### A.15.1 MembersPage Specification (Gap: Missing Route + Spec)

`MembersPage` provides an admin-level cross-body list of all members (E1.2 — a user can be a member of multiple bodies simultaneously). It complements the per-body Members Section inside `GoverningBodyDetailPage`.

**Route:** `/service/grc/legal/members`

**Filters:**
- Text search: user name / department
- Governing body filter (FK dropdown)
- Position filter (Member / Secretary / Chairman)
- Member type filter (Committee Member / Management Member)
- Status toggle: Active / Former (former = `left_date` IS NOT NULL) — default: Active only

**Columns:** Full Name, Governing Body, Position, Member Type, Joined Date, Status

**Actions per row:** Edit, Deactivate (permission-gated: `canManageMembers`)

**Note:** Member creation is done from within `GoverningBodyDetailPage` (governing body context is always required). `MembersPage` is read/edit only — there is no "Add Member" button here.

**getMember(id) endpoint:** Add to `legalService.ts`:
```ts
getMember: (id: string) => grcClient.get<Member>(`/api/v1/legal/members/${id}/`)
```

---

#### A.15.2 E2.4 — Submission Filter in MeetingAgendaSection

**Business rule (E2.4):** A Secretary can only attach submissions where `TargetBodyID` matches the meeting's `GoverningBodyID`.

**Implementation:** In `MeetingAgendaSection`, the submissions SmartSelect (used when Secretary adds an agenda item) must be pre-filtered:

```ts
// Pass as query filter when fetching candidate submissions:
const submissionFilter = {
  target_body: meeting.governing_body.id,
  status: 'submitted',   // only SUBMITTED submissions can be added to an agenda
  is_active: true,
};
```

- Only submissions with `status === 'submitted'` AND `target_body === meeting.governing_body.id` appear in the SmartSelect.
- Backend also enforces this constraint; the frontend filter is defense-in-depth and improves UX.
- If no eligible submissions exist, show the inline alert pattern (A.7.6): "No pending submissions for this governing body."

---

#### A.15.3 E3.2 — CreateMeetingDialog Governing Body Filter

**Business rule (E3.2):** A Secretary can only create meetings for governing bodies to which they are assigned (`SecretaryUserID[]`).

**Implementation:** The `governing_body` SmartSelect in `CreateMeetingDialog` must pass a filter:

```ts
// When fetching governing bodies for the SmartSelect:
const filter = canManageGoverningBodies
  ? {}                                            // Admin: sees all bodies
  : { secretary_user_id: currentUserId };         // Secretary: sees only assigned bodies
```

- Use `canManageGoverningBodies` permission to distinguish Admin vs Secretary.
- If the current user is a Secretary but has no assigned bodies, show the inline alert (A.7.6): "You are not assigned as Secretary to any governing body."
- Backend also validates on POST; frontend filter provides early UX feedback.

**Endpoint filter parameter:** `GET /api/v1/legal/governing-bodies/?secretary_user_id={uuid}` — the backend ViewSet must support this filter param.

---

#### A.15.4 E7.2 — ResolutionsPage Participant-Restricted Visibility

**Business rule (E7.2 + E7.3):** Resolutions are visible **only to invited participants** (members and invitees) of the respective meeting. Resolutions must be searchable within that participant set.

**Implementation:** The backend `ResolutionViewSet` enforces participant-restricted access and returns only resolutions the requesting user is authorised to see. The frontend does NOT need client-side filtering.

However, the `ResolutionsPage` must:
1. **Not show an empty state as an error** — an empty list simply means the user has no resolutions from meetings they attended. The empty state message should be: "No resolutions accessible. You do not appear to be a participant of any meetings that have recorded resolutions."
2. **Search** must be passed server-side (not client-side filtered): `GET /api/v1/legal/resolutions/?search={query}` — backend applies participant filter before search.
3. **Do not render** a "Create Resolution" button anywhere — resolutions are auto-created by the system (E7.1). The `canViewResolutions` permission is read-only.

---

#### A.15.5 E20.4 — Corporate Service Financial Process Links

**Domain constraint (E20.4):** The Corporate Service provides navigation links to financial processes — specifically **Revenue Collection** (when FCC wins and recoveries are expected) and **External Payments** (when FCC loses and must pay out a judgment).

**Implementation:** In `CaseFinancialsSection` (both defendant and plaintiff), when a judgment exists with a payment or recovery:

```tsx
{/* If judgment outcome = Lost (payment owed) */}
{judgment?.outcome === 'lost' && (
  <div className="text-sm text-muted-foreground mt-2">
    <span>To process payment via Finance: </span>
    <a
      href={corporateServiceUrl('/finance/external-payments')}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 hover:underline inline-flex items-center gap-1"
    >
      <ExternalLink className="h-3 w-3" /> External Payments (Finance)
    </a>
  </div>
)}

{/* If judgment outcome = Won (recovery expected) */}
{judgment?.outcome === 'won' && (
  <div className="text-sm text-muted-foreground mt-2">
    <span>To record recovery via Finance: </span>
    <a
      href={corporateServiceUrl('/finance/revenue-collection')}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 hover:underline inline-flex items-center gap-1"
    >
      <ExternalLink className="h-3 w-3" /> Revenue Collection (Finance)
    </a>
  </div>
)}
```

**`corporateServiceUrl(path)`** is a config helper function that builds the URL to the Corporate Service frontend using the environment-configured base URL. Add this to the shared config/environment utilities.

**Note:** These links are navigational only. Financial transactions are NOT managed in grc-service (E13.1 — no ERP integration). The links guide users to the correct Finance module in the main platform.

---

*End of Addendum A.15*

---

### A.16 Architecture Documents Gap Closures (Architecture Mapping + Architecture Overview + Base Models Mixins)

This addendum documents the gaps identified during the third verification pass against three backend architecture reference documents:
- `Legal_Module_Architecture_Mapping.md`
- `Legal_Module_Architecture_Overview.md`
- `Legal_Module_Base_Models_Mixins.md`

---

#### A.16.1 Legal Dashboard — Completely Missing from Plan (CRITICAL GAP)

Backend has `legal_dashboard_views.py` → `LegalDashboardStatsView` at:
- **Endpoint:** `GET /api/v1/legal/dashboard/stats/`
- **Permission:** Not yet defined in `grc-service.json` — the dashboard endpoint may use a combination of existing codes or a new `grc:legal_dashboard:view` code to be added by the backend team. **Do not assume this code exists until it is added to the JSON file.**

This was entirely absent from the plan. The following additions have been applied (structural changes already made to Phase 1, 3, 4):

**Phase 3.2 — `getLegalDashboardStats()` added to service table:**
```ts
getLegalDashboardStats: () => grcClient.get('/api/v1/legal/dashboard/stats/')
```

**Phase 4 — `legalDashboardKeys` added to query key factory:**
```ts
export const legalDashboardKeys = {
  all: ['legal-dashboard'] as const,
  stats: () => [...legalDashboardKeys.all, 'stats'] as const,
};
```

**`hooks/useLegalDashboard.ts` — new hook:**
```ts
import { useQuery } from '@tanstack/react-query';
import { legalDashboardKeys } from '../keys/legalKeys';
import { getLegalDashboardStats } from '../services/legalService';

export function useLegalDashboardStats() {
  return useQuery({
    queryKey: legalDashboardKeys.stats(),
    queryFn: getLegalDashboardStats,
    staleTime: 2 * 60 * 1000,   // 2-minute stale time — dashboard can be slightly stale
  });
}
```

**`pages/grc/legal/LegalDashboardPage.tsx` — implementation spec:**
- Guard: `canViewDashboard` from `useLegalPermissions()` (see Phase 5.1)
- Layout: `<div className="space-y-6">` (not `p-4` — follows list page wrapper convention)
- Content: KPI cards showing aggregated counts across all 6 legal sub-domains:

| KPI Card | Stat | Navigation Link |
|---|---|---|
| Active Meetings | `stats.active_meetings` | `/service/grc/legal/meetings` |
| Open Directives | `stats.open_directives` | `/service/grc/legal/directives` |
| Active Cases (Sued) | `stats.active_cases_sued` | `/service/grc/legal/fcc-sued` |
| Active Cases (Suing) | `stats.active_cases_suing` | `/service/grc/legal/fcc-suing` |
| Pending Filings | `stats.pending_filings` | Relevant case page |
| Overdue Tasks | `stats.overdue_tasks` | Sued/Suing case list |
| Pending Submissions | `stats.pending_submissions` | `/service/grc/legal/submissions` |
| Minutes Awaiting Approval | `stats.draft_minutes_pending` | `/service/grc/legal/minutes` |

KPI card UI pattern: same as Internal Audit dashboard KPI cards (`<Card>` with icon + count + label + `<Link>`).

**Phase 16 — Add to Step 1 (Foundation Layer) implementation order:**
```
After item 6 (useLegalConfig):
  6a. hooks/useLegalDashboard.ts
  6b. pages/grc/legal/LegalDashboardPage.tsx
```

---

#### A.16.2 Permission Code Format — Corrected to grc-service.json (CRITICAL GAP)

> **RETRACTION:** An earlier version of this addendum claimed the canonical codes were domain-grouped (`grc:legal:governance:view`), citing `Legal_Module_Architecture_Overview.md §6.8`. **That was wrong.** The actual source of truth is `grc-service/config/permissions/grc-service.json`, which defines per-resource codes in the format `grc:legal_<resource_type>:<action>`.

**The 28 canonical permission codes from `grc-service.json`:**

| Permission Code | Name | Resource |
|---|---|---|
| `grc:legal_governing_body:view` | View Legal Governing Bodies | `legal_governing_body` |
| `grc:legal_governing_body:manage` | Manage Legal Governing Bodies | `legal_governing_body` |
| `grc:legal_meeting:view` | View Legal Meetings | `legal_meeting` |
| `grc:legal_meeting:manage` | Manage Legal Meetings | `legal_meeting` |
| `grc:legal_meeting:approve` | Approve Legal Meetings | `legal_meeting` |
| `grc:legal_minutes:view` | View Legal Minutes | `legal_minutes` |
| `grc:legal_minutes:manage` | Manage Legal Minutes | `legal_minutes` |
| `grc:legal_minutes:approve` | Approve Legal Minutes | `legal_minutes` |
| `grc:legal_case:view` | View Legal Cases | `legal_case` |
| `grc:legal_case:manage` | Manage Legal Cases | `legal_case` |
| `grc:legal_case:close` | Close Legal Cases | `legal_case` |
| `grc:legal_filing:view` | View Legal Filings | `legal_filing` |
| `grc:legal_filing:manage` | Manage Legal Filings | `legal_filing` |
| `grc:legal_filing:approve` | Approve Legal Filings | `legal_filing` |
| `grc:legal_hearing:view` | View Legal Hearings | `legal_hearing` |
| `grc:legal_hearing:manage` | Manage Legal Hearings | `legal_hearing` |
| `grc:legal_settlement:view` | View Legal Settlements | `legal_settlement` |
| `grc:legal_settlement:manage` | Manage Legal Settlements | `legal_settlement` |
| `grc:legal_settlement:approve` | Approve Legal Settlements | `legal_settlement` |
| `grc:legal_judgment:view` | View Legal Judgments | `legal_judgment` |
| `grc:legal_judgment:manage` | Manage Legal Judgments | `legal_judgment` |
| `grc:legal_judgment:record` | Record Legal Judgments | `legal_judgment` |
| `grc:legal_directive:view` | View Legal Directives | `legal_directive` |
| `grc:legal_directive:manage` | Manage Legal Directives | `legal_directive` |
| `grc:legal_appeal:view` | View Legal Appeals | `legal_appeal` |
| `grc:legal_appeal:manage` | Manage Legal Appeals | `legal_appeal` |
| `grc:legal_notice:view` | View Legal Notices | `legal_notice` |
| `grc:legal_notice:manage` | Manage Legal Notices | `legal_notice` |

Phase 5.1 (`useLegalPermissions.ts`) has been updated with these correct codes and corresponding convenience booleans. See Phase 5.1 for the complete implementation.

---

#### A.16.3 CommitteeType TypeScript Type — Remove created_by / modified_by

**`Legal_Module_Base_Models_Mixins.md` §11 Quick Reference confirms:**
- `CommitteeType` mixin composition: `BaseModel + StatusMixin` only
- `TimestampedModel = ✗` → therefore **NO `created_by` or `modified_by` fields**

**Correct TypeScript type:**
```ts
interface CommitteeType {
  id: string;             // UUID from BaseModel
  name: string;
  code: string;
  description?: string;
  is_active: boolean;     // from StatusMixin
  // NOTE: no created_at, updated_at, created_by, modified_by
  //       CommitteeType uses BaseModel+StatusMixin only — no TimestampedModel
}
```

This correction supersedes the blanket statement in A.1.1 ("ALL entities"). Only entities with `TimestampedModel = ✓` in the §11 table get `created_at`/`updated_at`/`created_by`/`modified_by`.

**Rule:** Consult §11 Quick Reference table for each entity's exact mixin composition before defining its TypeScript type.

---

#### A.16.4 LegalAuditLog TypeScript Type — Corrected Fields

**`Legal_Module_Base_Models_Mixins.md` §11 Quick Reference defines actual `LegalAuditLog` fields:**

The correct TypeScript type (replaces the incorrect version in A.1.4):

```ts
interface LegalAuditLog {
  id: string;
  entity_type: string;     // e.g. 'filing_defendant', 'case_sued'
  entity_id: string;       // UUID of the target entity
  action: string;          // e.g. 'status_changed', 'approved', 'filed'
  actor_id: string;        // UUID of the user who performed the action
  stage_name: string;      // named stage in the approval chain (e.g. 'LM Review')
  comment: string;         // optional comment left by actor
  metadata: Record<string, unknown>;  // additional structured data
  created_at: string;      // LegalAuditLog inherits TimestampedModel
}
```

**Removed fields (were incorrect):** `actor_name`, `previous_value`, `new_value`, `description`.

---

#### A.16.5 Matters Arising Query Parameter Correction

Architecture Overview §6.4 (`legal_matter_arising_views.py`) uses `?body=<id>` (not `?governing_body=<id>`).

**Corrected service function:**
```ts
// ✓ Correct
getMatterArising: (params?: { body?: string; status?: string; page?: number }) =>
  grcClient.get('/api/v1/legal/directives/matters-arising/', { params })

// ✗ Incorrect (do not use)
// getMatterArising: (params?: { governing_body?: string; ... })
```

**Corrected hook filter:**
```ts
const { data } = useMatterArisingList({ body: selectedBodyId });
// NOT: { governing_body: selectedBodyId }
```

This correction is already applied to Phase 3.2 service table and A.2.1.

---

#### A.16.6 Meeting Quorum Endpoint

Architecture Overview §6.4 (`legal_meeting_views.py`) exposes:
- **Endpoint:** `GET /api/v1/legal/meetings/<id>/quorum/`
- **Service function:** `getLegalMeetingQuorum(id)` (added to Phase 3.2)

**Response type:**
```ts
interface MeetingQuorumResponse {
  meeting_id: string;
  total_member_count: number;
  rsvp_yes_count: number;
  rsvp_no_count: number;
  rsvp_pending_count: number;
  quorum_threshold: number;      // from MeetingType.quorum_percentage
  quorum_met: boolean;
  quorum_percentage: number;     // current attendance percentage
}
```

**Usage in `LegalMeetingDetailPage`:**
```ts
const { data: quorum } = useQuery({
  queryKey: legalMeetingKeys.quorum(meeting.id),
  queryFn: () => getLegalMeetingQuorum(meeting.id),
  // Poll every 30s when meeting is in registration/invitation phase:
  refetchInterval:
    meeting.status === 'registered' || meeting.status === 'invitations_sent'
      ? 30_000
      : false,
});
```

**Add to `legalMeetingKeys`:**
```ts
quorum: (id: string) => [...legalMeetingKeys.all, 'quorum', id] as const,
```

Display the `MeetingQuorumProgressPanel` (A.4.2) using this response — not just static fields from the meeting detail object.

---

#### A.16.7 Overdue Litigation Tasks Endpoint

Architecture Overview §6.4 (`legal_task_views.py`) exposes:
- **Endpoint:** `GET /api/v1/legal/tasks/overdue/`
- **Scope:** Cross-case (returns ALL overdue `TaskLitigation` records, not scoped to a single case)
- **Service function:** `getOverdueLitigationTasks()` (added to Phase 3.2)

**Add hook in `useLitigationTasks.ts`:**
```ts
export function useOverdueLitigationTasks() {
  return useQuery({
    queryKey: litigationTaskKeys.overdue(),
    queryFn: getOverdueLitigationTasks,
    staleTime: 5 * 60 * 1000,
  });
}
```

**Add to `litigationTaskKeys`:**
```ts
overdue: () => [...litigationTaskKeys.all, 'overdue'] as const,
```

**Usage:**
- `LegalDashboardPage` uses `useOverdueLitigationTasks()` to populate the "Overdue Tasks" KPI count.
- A future "Overdue Tasks" list view (Phase 7.2) may consume this hook directly.

---

#### A.16.8 Corporate Service Departments Endpoint for Breach Report Intake

Architecture Mapping §7.3 confirms: `GET /api/v1/corporate/hr/departments/` is available (cached by Corporate Service for 10 minutes). This endpoint provides the department list for the `reporting_department` field in `BreachReportIntakeDialog`.

**Add to `useLegalConfig.ts`:**
```ts
export function useDepartments(enabled = true) {
  return useQuery({
    queryKey: ['corporate', 'departments'],
    queryFn: () => corporateClient.get('/api/v1/corporate/hr/departments/'),
    staleTime: 10 * 60 * 1000,   // 10 min — matches Corporate Service cache TTL
    enabled,
  });
}
```

**`BreachReportIntakeDialog` — `reporting_department` field:**
- Render as `<Select>` populated from `useDepartments(isOpen)` (lazy fetch, only when dialog is open)
- NOT a free-text `<Input>` — department must be selected from the Corporate Service list
- Error state: if departments fail to load, show inline `<Alert variant="destructive">Unable to load departments. Please try again.</Alert>`

**Add to Phase 3.2 service table:**
```
| getDepartments() | GET | /api/v1/corporate/hr/departments/ |
```

---

#### A.16.9 FinancialPaymentRecord — Backend Model Naming Alignment

Architecture Overview §6.1 lists `FinancialPaymentRecord` as a **separate Django model** in the FCC Sued group (distinct from `FinancialDefendant`). This is the individual payment/recovery row entry model. The plan uses `FinancialEntry` as the TypeScript type name.

**Rename `FinancialEntry` → `FinancialPaymentRecord` in `types/legal.ts` for backend alignment:**
```ts
// Individual payment or recovery row — rename from FinancialEntry to FinancialPaymentRecord
interface FinancialPaymentRecord {
  id: string;
  date: string;
  amount: number;
  reference: string;
  status: 'requested' | 'approved' | 'processed';
  record_type: 'recovery' | 'payment';   // discriminator between recovery rows and payment rows
}

// FinancialDefendant references FinancialPaymentRecord (not FinancialEntry):
interface FinancialDefendant {
  id: string;
  case: string;
  claimed_amount: number;
  judgement_amount?: number;
  paid_date?: string;
  recovery_status: string;
  recoveries: FinancialPaymentRecord[];   // renamed from FinancialEntry
  payments: FinancialPaymentRecord[];     // renamed from FinancialEntry
  // ... rest of fields
}
```

Update all component files that import `FinancialEntry` to use `FinancialPaymentRecord`.

---

#### A.16.10 Phase 15 — Additional Test Scenarios (from Architecture Documents)

Add to Phase 15 test checklist:

**Dashboard:**
- [ ] Defendant KPI cards load from `GET /api/v1/grc/legal/dashboard/defendant/`
- [ ] Plaintiff KPI cards load from `GET /api/v1/grc/legal/dashboard/plaintiff/`
- [ ] `FCCSuedCasesPage` KPI section uses `legalDashboardKeys.defendant` query key
- [ ] `FCCSuingCasesPage` KPI section uses `legalDashboardKeys.plaintiff` query key
- [ ] Each KPI card link navigates to correct list page
- [ ] Dashboard hidden (redirect or 403) when user lacks the legal dashboard permission (confirm code with backend before implementing guard)

**Permissions:**
- [ ] All 28 permission codes in `useLegalPermissions.ts` match `grc:legal_<resource_type>:<action>` format exactly (sourced from `grc-service/config/permissions/grc-service.json`)
- [ ] No fabricated domain-grouped codes (e.g., `grc:legal:governance:view`, `grc:legal:litigation:manage`) remain anywhere in the codebase

**Types:**
- [ ] `CommitteeType` TypeScript type does NOT include `created_by`, `modified_by`, `created_at`, `updated_at`
- [ ] `LegalAuditLog` type has fields: `entity_type`, `entity_id`, `action`, `actor_id`, `stage_name`, `comment`, `metadata` — does NOT have `previous_value`, `new_value`, `actor_name`
- [ ] `FilingDefendant` and `FilingPlaintiff` types include all 5 `WorkflowMixin` fields despite no `EmbeddedWorkflowConsole`
- [ ] `FinancialPaymentRecord` naming used consistently (not `FinancialEntry`) in all financial components

**Endpoints:**
- [ ] `BreachReportIntakeDialog` populates `reporting_department` from Corporate Service (not free-text)
- [ ] Matters arising list fetches with `?body=<id>` (not `?governing_body=<id>`)
- [ ] Quorum endpoint polled every 30s for meetings in `registered`/`invitations_sent` status
- [ ] Overdue tasks endpoint returns cross-case tasks; count reflected on dashboard KPI card

---

*End of Addendum A.16*

---

### A.17 Legal_Service.md (SRS) Gap Closures

This addendum documents gaps found by verifying the plan against the canonical SRS document `Legal_Service.md`. All items here are directly sourced from the SRS and were not previously addressed.

---

#### A.17.1 `AGENDA_OUTCOMES` Const Map + `RecordAgendaOutcomeDialog` (SRS §1.1)

**SRS §1.1:** "After meeting, outcome recorded and status updated. If approved, any directives are created automatically and linked." Outcome values are `Approved`, `Rejected`, `Noted`, or `Deferred`.

**Add to `types/legal.ts`:**
```ts
export const AGENDA_OUTCOMES = ['approved', 'rejected', 'noted', 'deferred'] as const;
export type AgendaOutcome = typeof AGENDA_OUTCOMES[number];

// SUBMISSION_OUTCOMES (same values — SubmissionForDetermination also reflects these outcomes):
export const SUBMISSION_OUTCOMES = ['approved', 'rejected', 'noted', 'deferred'] as const;
export type SubmissionOutcome = typeof SUBMISSION_OUTCOMES[number];
```

**Add to `types/legal.ts` — extend `MeetingAgenda`:**
```ts
// outcome field type:
outcome: AgendaOutcome | null;
```

**Missing component — add to folder structure:**
```
components/grc/legal/RecordAgendaOutcomeDialog.tsx
```

**Add to Phase 16 Step 4 (Meeting Governance) after `CreateDirectiveDialog`:**
```
32a. components/grc/legal/RecordAgendaOutcomeDialog.tsx
```

**`RecordAgendaOutcomeDialog` spec:**
- Props: `agendaItem`, `open`, `onOpenChange`, `meetingId`
- Fields: `outcome` (Select: Approved / Rejected / Noted / Deferred), `outcome_notes` (Textarea, optional)
- Shown during `status === 'ongoing'` only; Secretary and permitted participants can access
- On submit: calls `recordAgendaOutcome(meetingId, agendaId, { outcome, outcome_notes })`
- On success: invalidates `meetingAgendaKeys.byMeeting(meetingId)` and `submissionKeys.detail(agendaItem.submission_id)` — this propagates outcome back to the original `SubmissionForDetermination`
- If outcome = 'approved': backend auto-creates directives; invalidate `meetingDirectiveKeys.byMeeting(meetingId)` after success
- Size: `max-w-lg`

**In `MeetingAgendaSection`:** Add "Record Outcome" action button per agenda row when `meeting.status === 'ongoing'` and agenda item has no outcome yet (`outcome === null`).

---

#### A.17.2 Meeting Invitation Workflow — Missing CTA and Service Functions (SRS §1.2.1)

**SRS §1.2.1:** The meeting lifecycle is `DRAFT → REGISTERED → INVITATIONS_SENT → AGENDA_SHARED → QUORUM_READY → ONGOING`. The transition from `REGISTERED → INVITATIONS_SENT` requires an explicit action by the Secretary to send out invitations. The plan currently skips this step.

**Add to `legalService.ts` service table (Phase 3.2):**

| Function | Method | Endpoint |
|---|---|---|
| `sendMeetingInvitations(id)` | POST | `/api/v1/legal/meetings/{id}/send-invitations/` |
| `addMeetingInvitee(meetingId, data)` | POST | `/api/v1/legal/meetings/{id}/participants/` |
| `removeMeetingInvitee(meetingId, participantId)` | DELETE | `/api/v1/legal/meetings/{id}/participants/{pid}/` |

**Update CTA list for `LegalMeetingDetailPage` (replaces Phase 8.2 CTA list):**
```
"Register Meeting"    — status = draft, Secretary only
"Send Invitations"    — status = registered, Secretary only           ← NEW
"Share Agenda"        — status = invitations_sent, Secretary only
"Start Meeting"       — status = quorum_ready AND quorum_met, Secretary only
"Resume Meeting"      — status = postponed, Secretary only
"Postpone"            — status = ongoing, Secretary only
"Close Meeting"       — status = ongoing, Secretary only
"Cancel"              — status in (draft, registered), Secretary only
"Reschedule"          — status in (draft, registered, postponed), Secretary only
```

**`MeetingParticipantsSection` Invitee Management (SRS §1.2.1 rule 6):**
- Show "Add Invitee" button when Secretary AND `status` in (`registered`, `invitations_sent`, `agenda_shared`)
- Click opens a SmartSelect dialog: search for internal staff (from IAM) who are NOT already members of the governing body
- Calls `addMeetingInvitee(meetingId, { user_id, role: 'invitee' })`
- Invitees rows show a "Remove" action (calls `removeMeetingInvitee`)
- Invitees can view agendas and directives but **cannot vote** — the section should visually distinguish members vs invitees (e.g., `Role` column shows "Member" or "Invitee" badge)

**Auto-populate note (SRS §1.2.1 rule 5):**
- When a meeting is created, the backend automatically adds all active governing body members as participants with `role = 'member'` and `invitation_status = 'pending'`
- After `createLegalMeeting()` succeeds, invalidate `meetingParticipantKeys.byMeeting(newMeetingId)` to load the pre-populated participant list

---

#### A.17.3 Case List KPI Dashboard Sections (SRS §4.0 and §5.0)

**SRS §4.0 and §5.0** define a "Dashboard & Case List" for both FCC Sued and FCC Suing pages. Each case list page has KPI summary cards at the top, above the searchable/filterable case list.

**`FCCSuedCasesPage` — KPI cards (SRS §4.0):**

| KPI | Field | Description |
|---|---|---|
| Total Cases Filed | `stats.total_cases` | All registered cases |
| Active Cases | `stats.active_cases` | Cases NOT in `closed` or `on_hold` stage |
| Pending DG Review | `stats.pending_dg_review` | Cases in `under_dg_review` stage |
| High Risk Cases | `stats.high_risk_cases` | Cases with high/critical risk level |
| Cases on Appeal | `stats.cases_on_appeal` | Cases in `appeal_filed` stage |
| Won/Loss Ratio | `stats.won` / `stats.lost` | Closed cases with `Won` vs `Lost` judgment |

**`FCCSuingCasesPage` — KPI cards (SRS §5.0 — same as above plus):**

| KPI | Field | Description |
|---|---|---|
| Recoverable Amount | `stats.recoverable_amount` | Sum of `estimated_claim_amount` for active suing cases |
| Recovered Amount | `stats.recovered_amount` | Sum of actual `recoveries[].amount` with status=processed |

**Implementation:**
- Add `getCaseDefendantDashboard()` → `GET /api/v1/grc/legal/dashboard/defendant/` to service table
- Add `getCasePlaintiffDashboard()` → `GET /api/v1/grc/legal/dashboard/plaintiff/` to service table
- Use `legalDashboardKeys.defendant` and `legalDashboardKeys.plaintiff` from the existing `legalDashboardKeys` in `legalKeys.ts` (no new keys needed)
- Render KPI cards using the same pattern as the Internal Audit dashboard KPI cards: `<Card>` with number + label + optional icon. No navigation link needed (already on the right page).
- KPI section: `<div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">` above the list table
- Apply `staleTime: 2 * 60 * 1000` for stats queries

---

#### A.17.4 Case List Pages — Missing Required Columns (SRS §4.0 / §5.0)

**SRS §4.0 specifies these columns for FCC Sued:** Case Ref No, Respondent (Plaintiffs), Case Type, Court, Claim Amount, Stage, Status, Risk, Next Hearing, Actions.

**SRS §5.0 specifies these columns for FCC Suing:** Same structure with Respondent instead of Plaintiffs.

**Current plan Phase 7.2 has (incomplete):**
- `FCCSuedCasesPage`: Case ID, Court, Plaintiffs, Stage, Urgency
- `FCCSuingCasesPage`: Case ID, Respondent, Stage, Urgency

**Add the following missing columns to both list pages:**

| Column | Field | Notes |
|---|---|---|
| Claim Amount | `claim_amount` / `estimated_claim_amount` | Numeric, formatted as currency |
| Risk Level | `risk_level` (from lookup) | Colored badge using `color_code` from lookup |
| Next Hearing | `next_hearing_date` | Date display, blank if null |

Also change `FCCSuedCasesPage` to show both columns: Stage AND Status (if separate fields) — or confirm Stage is the primary field. Per SRS, `Stage` is the primary progression indicator.

**"Case Type" column (SRS §4.0 / §5.0):** The SRS lists "Case Type" as a column but it is NOT a discrete field in `CaseDefendant` or `CasePlaintiff`. It likely maps to:
- For defendant: a display value derived from `nature_of_claim` categories (to be confirmed with backend)
- For plaintiff: the `respondent_type` field or a separate categorization

**Action:** Leave "Case Type" as a future column; add a `// TODO:` note in `FCCSuedCasesPage` until backend clarifies the field mapping. Do NOT block implementation on this.

---

#### A.17.5 Case Report/Timeline Section (SRS §4.13)

**SRS §4.13:** "A chronological timeline view of all case events (registration, filings, hearings, directives, judgments, settlements, closures) is available to all authorised users."

This is **distinct from the Activity Log** (A.6.6 which is a granular audit trail). The Report Tab is a curated, high-level timeline of KEY case milestones — not every CRUD operation.

**Add to folder structure:**
```
components/grc/legal/CaseReportSection.tsx
```

**Add to Phase 16 Step 5 (after `CaseTasksSection`):**
```
68a. components/grc/legal/CaseReportSection.tsx
```

**`CaseReportSection` component spec:**
- Renders a vertical timeline of major case events (reverse-chronological)
- Events sourced from the backend case report endpoint:
  - Add to service table: `getCaseReport(caseType, caseId)` → `GET /api/v1/legal/cases/{type}/{id}/report/`
  - Add to legalKeys: `caseReportKeys.byCase(caseType, caseId)`

**Timeline event types (displayed in chronological order):**

| Icon | Event Type | Detail shown |
|---|---|---|
| `FileText` | Case Registered | Registration date, registered by |
| `Search` | DG Review Started | Date, triggered by |
| `CheckCircle2` | DG Review Completed | Outcome (reviewed/directive issued) |
| `Gavel` | Hearing Held | Hearing date, court, judge |
| `FileCheck` | Filing Submitted | Filing type, title, submitted by |
| `CheckCircle2` | Filing Approved | Stage (LM/DG), approved by |
| `Scale` | Settlement Recorded | Settlement date, status |
| `LandmarkIcon` | Judgment Recorded | Outcome (Won/Lost), amount |
| `AlertTriangle` | Appeal Filed | Filing reference, due date |
| `Lock` | Case Closed | Closed by, closure date |
| `ListTodo` | Directive Issued (DG) | Instruction summary |

**Layout:**
```tsx
<Card>
  <CardHeader className="pb-2">
    <CardTitle className="text-base flex items-center gap-2">
      <ClipboardList className="h-4 w-4" /> Case Report
    </CardTitle>
  </CardHeader>
  <CardContent>
    <div className="relative border-l ml-4 border-border">
      {events.map(event => (
        <div key={event.id} className="mb-4 ml-4">
          <div className="absolute w-2 h-2 bg-primary rounded-full -left-1 mt-1" />
          <p className="text-xs text-muted-foreground">{formatDate(event.timestamp)}</p>
          <p className="text-sm font-medium">{event.title}</p>
          <p className="text-sm text-muted-foreground">{event.detail}</p>
        </div>
      ))}
    </div>
  </CardContent>
</Card>
```

**Placement in case detail pages:** Add `CaseReportSection` as the LAST child section in `FCCSuedCaseDetailPage` and `FCCSuingCaseDetailPage`, directly above the `ActivityLogSection` (A.6.6) and `EmbeddedWorkflowConsole`.

---

#### A.17.6 Settlement Payment Amount → Finance Tab Integration (SRS §4.7)

**SRS §4.7 rule 2:** "If payment amount is specified [in settlement], it will appear in Finance tab."

**Update `CaseFinancialsSection`:**
- When a `SettlementDefendant` or `SettlementPlaintiff` record exists with `payment_amount > 0` and `status === 'agreed'`, display a "Settlement Payment" informational row in the Financials section:
  ```tsx
  {settlement?.payment_amount && settlement.status === 'agreed' && (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
      <span className="font-medium">Settlement Payment:</span>
      {' '}{formatCurrency(settlement.payment_amount)}
      {' '}— agreed on {formatDate(settlement.settlement_date)}
    </div>
  )}
  ```
- This is informational only — NOT a separate `FinancialPaymentRecord` entry
- Pass `settlement` as a prop to `CaseFinancialsSection`, or fetch it from existing settlement query cache

**Update `CaseFinancialsSection` props:**
```ts
interface CaseFinancialsSectionProps {
  caseId: string;
  caseType: 'defendant' | 'plaintiff';
  settlement?: SettlementDefendant | SettlementPlaintiff | null;  // NEW
}
```

---

#### A.17.7 Attendance Marking and Member Auto-Population Notes (SRS §1.2.3, §1.2.1 rule 5)

**SRS §1.2.3:** "During ongoing meeting, Secretary may mark attendance manually (optional)."

This is already addressed in A.6.3. But the implementation note needs clarification on timing:
- Attendance marking is available ONLY during `status === 'ongoing'`
- During other statuses (registered, invitations_sent, etc.), attendance_marked column shows read-only `false` for all participants
- After meeting is `closed`, shows final attendance record (read-only)

**SRS §1.2.1 rule 5:** "When a meeting is created for a governing body, the system automatically populates the Members section with all active members of that governing body."

**Frontend behavior:**
- After `createLegalMeeting()` succeeds and the user navigates to the new meeting detail page, the Participants section should immediately show all active governing body members pre-populated with `invitation_status = 'pending'`
- Do NOT show "No participants" empty state for new meetings — show the auto-populated members

---

#### A.17.8 Phase 2 — Missing `SUBMISSION_OUTCOMES` and `AGENDA_DIALOG_OUTCOMES` Status Maps

**Add to Phase 2.2 status enum maps:**
```ts
// Submission / Agenda outcome values (SRS §1.1):
AGENDA_OUTCOMES = ['approved', 'rejected', 'noted', 'deferred']
SUBMISSION_OUTCOMES = ['approved', 'rejected', 'noted', 'deferred']

// Litigation Directive status (SRS §4.2 — separate from meeting directives):
LITIGATION_DIRECTIVE_STATUSES = ['open', 'in_progress', 'closed']
// Note: litigation directives do NOT have 'fully_closed' state — that applies only to meeting directives
```

**Clarify the DG_REVIEW_STATUS values:**
```ts
DG_REVIEW_STATUSES = ['pending', 'reviewed', 'directive_issued']
```

---

#### A.17.9 Phase 15 — Additional Test Scenarios (from SRS)

Add to Phase 15 test checklist:

**Meeting Governance:**
- [ ] "Send Invitations" CTA appears when `status === 'registered'`, not before and not after
- [ ] After meeting creation, Participants section shows auto-populated governing body members
- [ ] Secretary can add invitees; invitees visible with "Invitee" role badge (not "Member")
- [ ] "Record Outcome" button appears per agenda item during ONGOING only
- [ ] Outcome = Approved → directives auto-created → directive list refreshes automatically
- [ ] Outcome = Deferred → no directives created; submission remains Under Review

**Case Lists:**
- [ ] FCCSuedCasesPage shows KPI summary cards: Total, Active, Pending DG Review, High Risk, On Appeal, Won/Loss Ratio
- [ ] FCCSuingCasesPage shows extra KPI cards: Recoverable Amount, Recovered Amount
- [ ] Case list columns include: Claim Amount, Risk Level (colored badge), Next Hearing Date
- [ ] Next Hearing Date updates on case list after hearing report with `next_hearing_date` is submitted

**Case Detail:**
- [ ] CaseReportSection shows timeline of major events (registration, hearings, filings, judgment, closure)
- [ ] CaseFinancialsSection shows "Settlement Payment" row when agreed settlement has payment_amount > 0
- [ ] When case moves to `appeal_filed` stage, CaseReportSection shows "Appeal Filed" event entry

---

*End of Addendum A.17*

---

*End of Addendum A*

---

*End of Frontend Implementation Plan*  
*Source: LEGAL_DOMAIN_EXTRACTION.md, Legal_Module_Architecture_Mapping.md, Legal_Module_Data_Models_Part1–3.md, Legal_Module_Workflow_Integration.md, Legal_Module_Base_Models_Mixins.md, Legal_Module_Lookup_Tables.md, Legal_Module_Architecture_Overview.md, Internal_Audit_Backend_Patterns.md, Legal_Service.md, frontend_core_patterns.md, frontend_component_patterns.md, NEW_DETAIL_PAGE_REFERENCE.md*
