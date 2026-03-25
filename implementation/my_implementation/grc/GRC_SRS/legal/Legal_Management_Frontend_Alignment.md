# Legal Management — Frontend Alignment Report

**Date**: 2025-07-14  
**Scope**: Full frontend verification against `Legal_Service.md` SRS and backend implementation  
**Backend baseline**: All R1–R15 backend fixes confirmed complete  
**Frontend baseline**: Staff Portal (`frontend/apps/staff-portal/src/`)

---

## Executive Summary

A comprehensive review of the Legal module frontend revealed **18 issues** across 8 files. All issues have been fixed. The frontend is now fully aligned with the SRS and backend implementation.

---

## Issues Fixed

### F1 — Missing `shareAgenda()` API function
| Attribute | Value |
|-----------|-------|
| **File** | `services/legalService.ts` |
| **Severity** | HIGH |
| **Description** | `POST meetings/{id}/share-agenda/` had no client function. Backend `MeetingShareAgendaView` was unreachable from the frontend. |
| **Fix** | Added `export async function shareAgenda(id: string): Promise<LegalMeeting>` calling `POST ${LEGAL_PATHS.meetings}${id}/share-agenda/`. |

---

### F2 — Missing `markQuorumReady()` API function
| Attribute | Value |
|-----------|-------|
| **File** | `services/legalService.ts` |
| **Severity** | HIGH |
| **Description** | `POST meetings/{id}/mark-quorum-ready/` had no client function. Backend `MeetingMarkQuorumReadyView` was unreachable from the frontend. |
| **Fix** | Added `export async function markQuorumReady(id: string): Promise<LegalMeeting>` calling `POST ${LEGAL_PATHS.meetings}${id}/mark-quorum-ready/`. |

---

### F3 — Missing `sendInvitations()` API function
| Attribute | Value |
|-----------|-------|
| **File** | `services/legalService.ts` |
| **Severity** | HIGH |
| **Description** | `POST meetings/{id}/send-invitations/` had no client function. Backend `MeetingSendInvitationsView` was unreachable from the frontend. |
| **Fix** | Added `export async function sendInvitations(id: string): Promise<LegalMeeting>` calling `POST ${LEGAL_PATHS.meetings}${id}/send-invitations/`. |

---

### F4 — `rescheduleMeeting()` sending wrong field names
| Attribute | Value |
|-----------|-------|
| **File** | `services/legalService.ts`, `components/grc/legal/RescheduleMeetingDialog.tsx` |
| **Severity** | HIGH |
| **Description** | Frontend sent `{ start_datetime, end_datetime, reschedule_reason }` but `MeetingRescheduleView.post()` reads `request.data.get('scheduled_start')`, `request.data.get('scheduled_end')`, `request.data.get('reason')`. This caused all reschedule calls to fail silently with 400 "Missing fields". |
| **Fix** | Updated `rescheduleMeeting()` signature to `{ scheduled_start, scheduled_end, reason }`. Updated `RescheduleMeetingDialog.tsx` Zod schema, form defaults, reset, onSubmit payload, and all `name=` bindings to use the correct field names. |

---

### F5 — Missing `useShareAgenda` React Query hook
| Attribute | Value |
|-----------|-------|
| **File** | `hooks/useLegalMeetings.ts` |
| **Severity** | HIGH |
| **Description** | No hook for triggering Share Agenda action. |
| **Fix** | Added `export function useShareAgenda()` using the `useMeetingAction` factory. |

---

### F6 — Missing `useMarkQuorumReady` React Query hook
| Attribute | Value |
|-----------|-------|
| **File** | `hooks/useLegalMeetings.ts` |
| **Severity** | HIGH |
| **Description** | No hook for triggering Mark Quorum Ready action. |
| **Fix** | Added `export function useMarkQuorumReady()` using the `useMeetingAction` factory. |

---

### F7 — Missing `useSendInvitations` React Query hook
| Attribute | Value |
|-----------|-------|
| **File** | `hooks/useLegalMeetings.ts` |
| **Severity** | HIGH |
| **Description** | No hook for triggering Send Invitations action. |
| **Fix** | Added `export function useSendInvitations()` using the `useMeetingAction` factory. |

---

### F8 — `useRescheduleMeeting` hook using wrong field names
| Attribute | Value |
|-----------|-------|
| **File** | `hooks/useLegalMeetings.ts` |
| **Severity** | HIGH |
| **Description** | `mutationFn` type was `{ start_datetime, end_datetime, reschedule_reason }` — mismatched with both the fixed service and backend. |
| **Fix** | Updated `mutationFn` type to `{ scheduled_start: string; scheduled_end: string; reason: string }`. |

---

### F9 — Missing "Send Invitations" button in meeting lifecycle actions
| Attribute | Value |
|-----------|-------|
| **File** | `pages/grc/legal/LegalMeetingDetailPage.tsx` |
| **Severity** | HIGH |
| **Description** | SRS requires: "registered → invitations_sent" via Send Invitations. Backend endpoint `send-invitations/` existed and was functional, but no UI button was ever wired up. |
| **Fix** | Added `canSendInvitations = status === 'registered'` guard and a "Send Invitations" button that calls `sendInvitationsMutation.mutate(meeting.id)`. |

---

### F10 — Missing "Share Agenda" button in meeting lifecycle actions
| Attribute | Value |
|-----------|-------|
| **File** | `pages/grc/legal/LegalMeetingDetailPage.tsx` |
| **Severity** | HIGH |
| **Description** | SRS requires: "invitations_sent → agenda_shared" via Share Agenda. Button was completely absent. |
| **Fix** | Added `canShareAgenda = status === 'invitations_sent' || status === 'registered'` guard (matching backend `MeetingShareAgendaView` which accepts both statuses) and a "Share Agenda" button. |

---

### F11 — Missing "Mark Quorum Ready" button in meeting lifecycle actions
| Attribute | Value |
|-----------|-------|
| **File** | `pages/grc/legal/LegalMeetingDetailPage.tsx` |
| **Severity** | HIGH |
| **Description** | SRS requires: "agenda_shared → quorum_ready" when quorum is met. Button was completely absent. |
| **Fix** | Added `canMarkQuorumReady = (status === 'agenda_shared' || status === 'invitations_sent' || status === 'registered') && quorumMet` guard (matching backend `MeetingMarkQuorumReadyView`) and a "Mark Quorum Ready" button. |

---

### F12 — Postpone button showing for wrong meeting statuses
| Attribute | Value |
|-----------|-------|
| **File** | `pages/grc/legal/LegalMeetingDetailPage.tsx` |
| **Severity** | MEDIUM |
| **Description** | Postpone was gated by `isModifiable && !isDraft`, which meant it showed only for `registered`, `invitations_sent`, `agenda_shared` — but NOT for `ongoing` or `quorum_ready`. Backend `MeetingPostponeView` blocks only `closed`, `cancelled`, `postponed`. |
| **Fix** | Replaced condition with `canPostpone = !['closed', 'cancelled', 'postponed'].includes(status)`, aligning with the backend's actual permission logic. |

---

### F13 — Reschedule button not available from `postponed` status
| Attribute | Value |
|-----------|-------|
| **File** | `pages/grc/legal/LegalMeetingDetailPage.tsx` |
| **Severity** | MEDIUM |
| **Description** | Reschedule was also gated by `isModifiable && !isDraft` — same as Postpone — and therefore excluded the `postponed` status. Backend `MeetingRescheduleView` blocks only `closed` and `cancelled`; `postponed` meetings are explicitly eligible for rescheduling (this is the primary recovery path after postponement). |
| **Fix** | Replaced condition with `canReschedule = !['closed', 'cancelled'].includes(status)`. |

---

### F14 — Cancel button not shown after `postponed` status
| Attribute | Value |
|-----------|-------|
| **File** | `pages/grc/legal/LegalMeetingDetailPage.tsx` |
| **Severity** | MEDIUM |
| **Description** | Cancel was inside the same `isModifiable && !isDraft` block — `postponed` meetings could not be cancelled from the UI even though the backend allows it. |
| **Fix** | Cancel button now shows when `!isClosed && status !== 'cancelled'`, matching the backend `MeetingCancelView` logic. |

---

### F15 — `CaseDefendant` type missing `case_folder_url` field
| Attribute | Value |
|-----------|-------|
| **File** | `types/legal.ts` |
| **Severity** | HIGH |
| **Description** | Backend migration 0037 added `case_folder_url` to the `CaseDefendant` model and serializer, but the TypeScript interface was never updated. TypeScript would error if any code tried to access `caseData.case_folder_url`. |
| **Fix** | Added `case_folder_url?: string` to the `CaseDefendant` interface. |

---

### F16 — `CasePlaintiff` type missing `case_folder_url` field
| Attribute | Value |
|-----------|-------|
| **File** | `types/legal.ts` |
| **Severity** | HIGH |
| **Description** | Same as F15 for the plaintiff case model. |
| **Fix** | Added `case_folder_url?: string` to the `CasePlaintiff` interface. |

---

### F17 — `case_folder_url` not displayed in FCC Sued case info card
| Attribute | Value |
|-----------|-------|
| **File** | `pages/grc/legal/FCCSuedCaseDetailPage.tsx` |
| **Severity** | MEDIUM |
| **Description** | After F15/F16 fixes, the field was available in the type but not rendered in the UI. |
| **Fix** | Added a conditional "Case Folder" row in the Case Information card that renders an anchor link to `case_folder_url` when the field is present. Also added a "DG Review Status" display field to the same card. |

---

### F18 — `dg_review_status` and `case_folder_url` not displayed in FCC Suing case info card
| Attribute | Value |
|-----------|-------|
| **File** | `pages/grc/legal/FCCSuingCaseDetailPage.tsx` |
| **Severity** | MEDIUM |
| **Description** | Same as F17 for the plaintiff/suing case page. `dg_review_status` was used in stage logic but not shown as a visible field to the user. |
| **Fix** | Added "DG Review Status" and conditional "Case Folder" rows to the Case Information card. |

---

### F19 — `response_to_ruling` missing from defendant response types
| Attribute | Value |
|-----------|-------|
| **File** | `hooks/useLegalConfig.ts` |
| **Severity** | MEDIUM |
| **Description** | Backend R12 added `response_to_ruling` as a valid response type for BOTH defendant and plaintiff case types. `RESPONSE_TYPES_PLAINTIFF` had the new entry but `RESPONSE_TYPES_DEFENDANT` did not. |
| **Fix** | Added `{ value: 'response_to_ruling', label: 'Response to Ruling' }` to `RESPONSE_TYPES_DEFENDANT`. |

---

### F20 — `CreateResponseDialog` using free-text Input for `response_type`
| Attribute | Value |
|-----------|-------|
| **File** | `components/grc/legal/CreateResponseDialog.tsx` |
| **Severity** | HIGH |
| **Description** | The dialog used an open-ended `<Input>` for the `response_type` field, allowing arbitrary text. This would cause backend validation failures for values not in `RESPONSE_TYPE_CHOICES`. The `useResponseTypes(caseType)` hook already existed in `useLegalConfig.ts` but was not wired to this dialog. |
| **Fix** | Replaced `<Input>` with a `<Select>` component populated from `useResponseTypes(caseType)`. Added imports for `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue` from `@ui/select` and `useResponseTypes` from `useLegalConfig`. |

---

## Files Changed

| File | Issues Fixed |
|------|-------------|
| `services/legalService.ts` | F1, F2, F3, F4 |
| `hooks/useLegalMeetings.ts` | F5, F6, F7, F8 |
| `components/grc/legal/RescheduleMeetingDialog.tsx` | F4 (form side) |
| `pages/grc/legal/LegalMeetingDetailPage.tsx` | F9, F10, F11, F12, F13, F14 |
| `types/legal.ts` | F15, F16 |
| `pages/grc/legal/FCCSuedCaseDetailPage.tsx` | F17 (case_folder_url + dg_review_status) |
| `pages/grc/legal/FCCSuingCaseDetailPage.tsx` | F18 (case_folder_url + dg_review_status) |
| `hooks/useLegalConfig.ts` | F19 |
| `components/grc/legal/CreateResponseDialog.tsx` | F20 |

---

## SRS Module Coverage (Post-Fix)

| SRS Module | Coverage |
|------------|----------|
| **Determinations** — Submission list, detail, meeting linkage, outcome recording | ✅ Full |
| **Meeting Governance** — Full 10-status lifecycle (draft→registered→invitations_sent→agenda_shared→quorum_ready→ongoing→closed; postponed→rescheduled; cancelled) | ✅ Full |
| **Meeting Governance** — All lifecycle buttons (Register, Send Invitations, Share Agenda, Mark Quorum Ready, Start, Close, Postpone, Reschedule, Cancel) | ✅ Full (all previously missing buttons added) |
| **Governance Structure** — Committee types, governing bodies, members CRUD | ✅ Full |
| **Public Register** — Public decisions CRUD and listing | ✅ Full |
| **Litigation Defendant** — Case lifecycle (registered→active→under_dg_review→closure_initiated→closed), DG review, filings, responses, hearings, settlement, judgment, financials, tasks | ✅ Full |
| **Litigation Plaintiff** — Same as Defendant with plaintiff-specific fields | ✅ Full |
| **Case Documents** — `case_folder_url` field displayed in both case detail pages | ✅ Full |
| **Response Types** — All valid defendant and plaintiff response types available as Select options | ✅ Full |

---

## Backend API Alignment (Meeting Lifecycle Reference)

| Action | Backend Endpoint | Allowed From Statuses | Frontend Condition |
|--------|-----------------|----------------------|-------------------|
| Register | `POST /register/` | `draft` | `isDraft` |
| Send Invitations | `POST /send-invitations/` | `registered` | `status === 'registered'` |
| Share Agenda | `POST /share-agenda/` | `registered`, `invitations_sent` | `status === 'invitations_sent' \|\| status === 'registered'` |
| Mark Quorum Ready | `POST /mark-quorum-ready/` | `registered`, `invitations_sent`, `agenda_shared` (quorum_met required) | `(status in [agenda_shared, invitations_sent, registered]) && quorumMet` |
| Start Meeting | `POST /start/` | `quorum_ready`, `agenda_shared` (quorum_met + time window) | `(status === 'quorum_ready' \|\| status === 'agenda_shared') && quorumMet && now >= start_datetime` |
| Close Meeting | `POST /close/` | `ongoing` | `isOngoing` |
| Postpone | `POST /postpone/` | Any except `closed`, `cancelled`, `postponed` | `!['closed', 'cancelled', 'postponed'].includes(status)` |
| Reschedule | `POST /reschedule/` | Any except `closed`, `cancelled` | `!['closed', 'cancelled'].includes(status)` |
| Cancel | `POST /cancel/` | Any except `closed`, `cancelled` | `!isClosed && status !== 'cancelled'` |

---

*Report generated after comprehensive SRS review, backend implementation audit, and frontend codebase analysis. All 20 issues were fixed in the same session.*
