# Meetings Module — Gap Analysis vs SRS

> Compared against: `SRS_MEETINGS_ANALYSIS.md` (SRS 1.8.3 Steps 14, 17, 20, 23–24)
> Codebase analysed: Backend (GRC Django) + Frontend (React/TS staff-portal)

---

## Executive Summary

The meeting module has a **solid foundation** — the model, API, views, and frontend CRUD are all in place. However, there are **7 gaps** that need fixing to achieve 100% SRS compliance. Most are small-to-medium effort.

| Area | Score | Notes |
|------|-------|-------|
| Data Model | 8/10 | Missing 2 SRS-specific fields for pre-exit meeting |
| Phase Gating | 9/10 | Well implemented, minor entry meeting phase issue |
| Meeting Types | 10/10 | All 4 types present and correct |
| File Uploads (DRS) | 10/10 | Both minutes + attendance upload to DRS correctly |
| Attendee Tracking | 9/10 | Good JSON structure, missing "organization" field mapping |
| Exit Meeting Notification | 3/10 | Not implemented — SRS explicitly requires it |
| Engagement Integration | 4/10 | No meeting tab on engagement detail page |
| Duplicate Prevention | 5/10 | No validation — allows multiple entry meetings per engagement |
| Frontend Detail Dialog | 6/10 | Field name mismatches with TypeScript types |

---

## Strengths (What's Already Working Well)

### S1. All 4 Meeting Types Present ✅
```
entry → Entry Meeting (SRS Step 14)
pre_exit → Pre-Exit Meeting (SRS Step 17)
team → Audit Team Meeting (SRS Step 20)
exit → Exit Meeting (SRS Steps 23–24)
```
Exact match with SRS requirements.

### S2. Engagement Phase Gating ✅
```python
MEETING_TYPE_ENGAGEMENT_PHASES = {
    'entry':    ('fieldwork',),
    'pre_exit': ('fieldwork', 'reporting'),
    'team':     ('fieldwork', 'reporting'),
    'exit':     ('reporting', 'completed'),
}
```
Correctly prevents creating meetings in wrong phases. The backend validates engagement status before allowing meeting creation.

### S3. Status State Machine ✅
```
scheduled → in_progress → completed (terminal)
                       → cancelled (terminal)
```
With field locking: completed/cancelled meetings can't be edited. In-progress meetings only allow minutes/attendees/documents. This is good practice.

### S4. DRS File Upload (Minutes + Attendance) ✅
The backend correctly:
1. Creates document record in DRS via `document_client.create_document()`
2. Uploads file binary via `document_client.upload_file(doc_id, file, filename)`
3. Stores UUID as `minutes_document_id` / `attendance_document_id`

This is the correct pattern (unlike working papers which are broken).

### S5. Kafka Event Publishing ✅
All 4 meeting lifecycle events published:
- `grc.audit.meeting.scheduled`
- `grc.audit.meeting.started`
- `grc.audit.meeting.completed`
- `grc.audit.meeting.cancelled`

### S6. Attendee Tracking ✅
JSON structure captures:
- Name, Title/Position, Role (auditor/auditee/observer/management), Presence (boolean)
- Frontend has dynamic add/remove rows with role selection

### S7. Auto-generated Reference Numbers ✅
Format: `MTG-{engagement_ref}-{TYPE}-{seq:03d}` — clean, unique, traceable.

### S8. Minutes Required Before Completion ✅
Backend enforces non-empty `minutes` before allowing transition to `completed` status.

---

## Gaps (What Needs Fixing)

### GAP-1: No "Clarifications" and "Agreed Observations" Fields for Pre-Exit Meeting 🔴
**SRS Requirement:**
> Pre-Exit Meeting — Key Information Required: **Clarifications**, **Agreed observations**

**Current State:** The model has generic `minutes` and `key_discussions` fields only. No meeting-type-specific fields.

**Impact:** Pre-exit meeting data doesn't capture SRS-required structured information.

**Fix Plan:**
| Layer | Change |
|-------|--------|
| **Model** | Add `clarifications = models.TextField(blank=True, default='')` and `agreed_observations = models.TextField(blank=True, default='')` to `AuditMeeting` |
| **Serializer** | Add both fields to `AuditMeetingSerializer.Meta.fields` |
| **Frontend types** | Add `clarifications?: string` and `agreed_observations?: string` to `AuditMeeting` interface |
| **Frontend form** | Show these 2 fields conditionally when `meeting_type === 'pre_exit'` |
| **Migration** | `python manage.py makemigrations && migrate` |

**Effort:** Small (1-2 hours)

---

### GAP-2: No Exit Meeting Notification Feature 🔴
**SRS Requirement (Step 23):**
> "LA arranges exit meeting by **sending Exit meeting Notification including draft audit report** to auditee, auditors and other personnel responsible for the finding"

**Current State:** No notification mechanism exists. No `notification_sent` field, no draft report attachment to the notification.

**Impact:** Major SRS gap — the exit meeting notification with attached draft report is an explicit SRS requirement.

**Fix Plan:**
| Layer | Change |
|-------|--------|
| **Model** | Add fields: `notification_sent = BooleanField(default=False)`, `notification_date = DateTimeField(null=True, blank=True)`, `notification_document_id = UUIDField(null=True, blank=True)` (for exit meeting notification document), `draft_report_document_id = UUIDField(null=True, blank=True)` (link to draft audit report) |
| **Backend view** | Add new action endpoint: `POST /meetings/{id}/send-notification/`. This should: (a) validate meeting is `exit` type, (b) validate engagement has an approved draft report, (c) create notification in DRS, (d) set `notification_sent=True` and `notification_date`, (e) publish Kafka event |
| **Frontend** | Add "Send Exit Meeting Notification" button on exit meetings that are `scheduled`. Show notification status badge. Allow attaching/linking draft audit report. |
| **URL** | Add route: `path("meetings/<uuid:pk>/send-notification/", ...)` |

**Effort:** Medium (4-6 hours)

---

### GAP-3: No Meeting Tab on Engagement Detail Page 🔴
**SRS Context:** Meetings are linked to engagements (FK). Users working on an engagement need to see its meetings.

**Current State:** `EngagementDetailPage.tsx` has ZERO meeting references. No tab, no section, no link.

**Impact:** Users must leave the engagement and go to the separate Meetings list page, then filter by engagement. Poor UX and breaks the engagement-centric workflow.

**Fix Plan:**
| Layer | Change |
|-------|--------|
| **Frontend** | Add a "Meetings" tab/section to `EngagementDetailPage.tsx` that: (a) queries meetings filtered by `engagement_id`, (b) shows a table with type, date, status, attendee count, (c) has "Schedule Meeting" button, (d) links to meeting detail dialog |
| **Backend** | Already supports filtering: `GET /audit/meetings/?engagement={id}` (verify filter param exists) |

**Effort:** Medium (3-4 hours)

---

### GAP-4: No Duplicate Meeting Type Prevention 🟡
**SRS Implication:** Each engagement should have exactly one entry meeting (Step 14), one pre-exit meeting (Step 17), one audit team meeting (Step 20), and one exit meeting (Steps 23-24).

**Current State:** No validation — you can create 5 entry meetings for the same engagement. The reference number just increments (MTG-...-ENTRY-001, MTG-...-ENTRY-002, etc.)

**Impact:** Data quality risk. Multiple entry meetings per engagement is nonsensical per SRS.

**Fix Plan:**
| Layer | Change |
|-------|--------|
| **Backend view** | In `post()`, before creating, check: `AuditMeeting.objects.filter(engagement=engagement, meeting_type=meeting_type, is_active=True).exists()`. If true, return 400 with error code `DUPLICATE_MEETING_TYPE`. |
| **Exception** | Allow multiple if the previous one was `cancelled`. Only block if an `active` (non-cancelled) meeting of same type exists. |

**Effort:** Small (30 minutes)

---

### GAP-5: Frontend Detail Dialog Field Mismatches 🟡
**Current State:** `AuditMeetingDetailDialog.tsx` references fields that don't exist in TypeScript types:
- `a.organization` — types have `a.title` (job title / position)
- `a.attended` — types have `a.present` (boolean)
- `item.chaired_by` — not in `AuditMeeting` interface
- `item.minutes_prepared_by` — not in `AuditMeeting` interface

**Impact:** Runtime display issues — some columns may show `undefined`.

**Fix Plan:**
| Layer | Change |
|-------|--------|
| **Frontend** | Fix field names in detail dialog: `a.organization` → `a.title`, `a.attended` → `a.present` |
| **Model (optional)** | Consider adding `chaired_by` and `minutes_prepared_by` fields to the model if desired, OR remove them from the detail dialog |

**Effort:** Small (30 minutes)

---

### GAP-6: Legacy Meeting Date Fields on Engagement Model 🟡
**Current State:** `AuditEngagement` has two legacy fields:
```python
entry_meeting_date = models.DateTimeField(null=True, blank=True)
exit_meeting_date = models.DateTimeField(null=True, blank=True)
```
These duplicate data now that meeting records exist separately.

**Impact:** Data inconsistency — meeting dates live in TWO places. If someone updates the `AuditMeeting.scheduled_date`, the `AuditEngagement.entry_meeting_date` doesn't update, and vice-versa.

**Fix Plan:**
| Option | Description |
|--------|-------------|
| **A (Recommended)** | Keep legacy fields but auto-sync them when a meeting is created/updated. In the meeting view's `post()` and `_update()`, after saving the meeting, also update `engagement.entry_meeting_date` or `engagement.exit_meeting_date` if meeting_type is `entry` or `exit`. |
| **B (Cleaner)** | Deprecate legacy fields. Remove them from the engagement serializer. Always query from `AuditMeeting` table. Requires frontend changes wherever these fields are displayed on the engagement. |

**Effort:** Small-Medium (1-2 hours for Option A)

---

### GAP-7: No Action Items UI in Create/Edit Form � (Enhancement — NOT in SRS)
**Current State:** The model and types support `action_items` (JSON array with description, assigned_to, due_date, status). The detail dialog DISPLAYS action items. But the create/edit dialog has NO UI to add/edit them.

**Note:** The SRS does NOT explicitly require action items for meetings. It requires minutes, attendance, clarifications (pre-exit), and notifications (exit). Action items are a **nice-to-have UX enhancement**, not an SRS compliance gap.

**Impact:** Low — action items can only be set via API directly, not through the UI.

**Fix Plan (optional):**
| Layer | Change |
|-------|--------|
| **Frontend form** | Add an "Action Items" section (similar to Attendees) with dynamic rows for description, assigned to, due date, status. Show in edit mode only. |

**Effort:** Small-Medium (2-3 hours) — **defer to after SRS gaps are closed**

---

### GAP-8: Pre-Exit Meeting Does Not Validate Working Papers Reviewed 🔴
**SRS Requirement:**
> Pre-Exit Meeting — "Dependencies: Working papers reviewed"
> "LA reviews evidence gathered in Working Paper by audit team members... and arrange preexit meeting with the auditee." (Step 16)

**Current State:** Pre-exit meeting creation only checks `engagement.status in ('fieldwork', 'reporting')`. It does NOT check whether any Working Papers have actually been reviewed/approved.

**Impact:** A pre-exit meeting could be scheduled before any WPs are reviewed, violating SRS dependency.

**Fix Plan:**
| Layer | Change |
|-------|--------|
| **Backend view** | In `post()`, when `meeting_type == 'pre_exit'`, add a check: `WorkingPaper.objects.filter(engagement=engagement, review_status='approved').exists()`. If false, return 400 with error `PRE_EXIT_REQUIRES_APPROVED_WPS`. |

**Effort:** Small (30 minutes)

> **Cross-ref:** This matches GAP MT3 in `POST_ENGAGEMENT_SRS_ALIGNMENT.md`

---

### GAP-9: Meeting Minutes/Attendance Not Produced as Formal DRS Documents 🟡
**SRS Requirement:**
> Process Outputs (§1.8.3): "Entry Meeting Minutes", "Exit Meeting Minutes" — listed as named formal outputs on par with the Engagement Audit Report.
>
> Data Requirements — Entry Meeting: "Entry meeting minutes, **Attendance register**"
> Data Requirements — Exit Meeting: "Exit meeting minutes, **Attendance register**"
> Data Requirements — Pre-Exit Meeting: "Pre-exit meeting notes"
>
> Step 14: "record the attendance and proceedings of the meeting for future reference"
> Step 24: "document exit meeting minutes **and attendance sheet**"

**Scope — Which meetings are affected:**
| Meeting Type | SRS Named Output | SRS Data Requirement | What must be produced in DRS |
|---|---|---|---|
| **Entry** | ✅ "Entry Meeting Minutes" (Process Output) | Minutes + Attendance register | `minutes_document_id` + `attendance_document_id` |
| **Exit** | ✅ "Exit Meeting Minutes" (Process Output) | Minutes + Attendance register | `minutes_document_id` + `attendance_document_id` |
| **Pre-Exit** | ❌ (not a named output) | "Pre-exit meeting notes" | `minutes_document_id` (notes only, no attendance required) |
| **Team** | ❌ (not a named output) | No explicit data requirement | Optional — not required by SRS |

**Clarification on "auto-generate":** The SRS says "record" and "document" — it does not say "auto-generate". However, all other formal process outputs in the system (Engagement Notification with QR code, Audit Report) are produced *within* the system as DRS documents. The gap is not that the SRS demands PDF auto-generation — it is that Minutes and Attendance are listed as **formal process outputs** but the system currently has no mechanism to produce them as retrievable DRS documents without the user manually creating and uploading a file outside the system.

**Current State:** `minutes_document_id` and `attendance_document_id` exist on the model and can be populated via manual file upload in `_update()`. However:
1. **No document is produced when a meeting completes** — the fields stay `null` unless the LA manually uploads external files
2. **The attendance sheet is completely omitted** from any auto-generation consideration — yet the SRS explicitly names it alongside minutes for both entry and exit meetings
3. The structured data needed to produce both documents is already in the system (`minutes`, `attendees`, `key_discussions`, `agenda`, `location`, `scheduled_date`, `reference_number`)

**Impact:** Entry and Exit Meeting Minutes + Attendance Registers are explicit SRS process outputs. Pre-exit meeting notes are a data requirement. None are automatically produced as DRS documents. The user must go outside the system to create them.

**How other parts of the system handle this (reference pattern):**

The system already has a complete, working document-generation pipeline used by Declaration of Independence and Engagement Notification. Meeting Minutes must follow the **exact same pattern** — do not invent a new approach.

| Component | Already exists? | Location |
|-----------|----------------|----------|
| `WeasyPrint` (HTML→PDF) | ✅ Already in `requirements.txt` | — |
| `pdf_generators.py` (PDF generation functions) | ✅ Already exists | `apps/core/utils/pdf_generators.py` |
| `DocumentServiceClient.create_document_with_file()` | ✅ Already exists | `apps/infrastructure/external/document_service_client.py` |
| HTML templates rendered to PDF | ✅ Pattern exists | `templates/grc/engagement_notification.html`, `templates/grc/declaration_of_independence.html` |
| QR code + CIA signature stamp | ❌ **NOT needed for meetings** | See note below |

**Important — No QR/signature stamp for meetings:**
The Declaration and Engagement Notification get a QR code + CIA signature stamped by DRS because they go through a **CIA approval workflow** (`generate_approved_stamp` fires on CIA approval via Kafka). Meeting Minutes do NOT have a CIA approval step in the SRS — they are recorded by LA when a meeting completes. Therefore:
- ✅ Generate PDF from HTML template
- ✅ Upload to DRS via `create_document_with_file()`
- ✅ Store UUID in `minutes_document_id` / `attendance_document_id`
- ❌ No `generate_approved_stamp` call needed

**Fix Plan — What must be added:**

| What | File | Description |
|------|------|-------------|
| `generate_meeting_minutes_pdf(meeting)` | `apps/core/utils/pdf_generators.py` | New function — renders `templates/grc/meeting_minutes.html` with meeting context, returns PDF bytes |
| `generate_attendance_register_pdf(meeting)` | `apps/core/utils/pdf_generators.py` | New function — renders `templates/grc/attendance_register.html` with attendees list, returns PDF bytes |
| `templates/grc/meeting_minutes.html` | `templates/grc/` | New HTML template — same A4 layout, 60mm bottom margin (room for DRS footer), includes: FCC header, reference number, engagement reference, date/time, location, attendees count, agenda, minutes text, key discussions, clarifications (pre-exit only) |
| `templates/grc/attendance_register.html` | `templates/grc/` | New HTML template — includes: header, reference number, date/time, location, attendee table (No., Name, Title/Position, Role, Present ✓/✗, Signature line) |
| `_generate_meeting_documents(meeting, auth_token)` helper | `apps/api/views/audit_meeting_views.py` | New helper — generates and uploads both documents to DRS, non-blocking (logs warning on failure, never raises). Called from `AuditMeetingStatusUpdateView.post()` when `new_status == 'completed'` |

**Trigger point:** `AuditMeetingStatusUpdateView.post()` — when `new_status == 'completed'`, call the helper inside `transaction.atomic()` after `meeting.save()`.

**Scope rules inside the helper:**
```
entry   → generate minutes_document_id + attendance_document_id
exit    → generate minutes_document_id + attendance_document_id
pre_exit → generate minutes_document_id only (SRS: "meeting notes", no attendance required)
team    → skip (no SRS data requirement)
```

**Skip-if-already-set rule:** If the user already manually uploaded (`minutes_document_id is not None`), skip auto-generation — never overwrite a manual upload.

**DRS document_type values to use:**
```
minutes PDF      → document_type='audit_meeting_minutes'
attendance PDF   → document_type='audit_meeting_attendance'
```
(These already exist as document_type strings in the system — the meeting views already use them for manual uploads in `_update()`.)

**Effort:** Medium (3-4 hours)

> **Cross-ref:** This matches GAP MT4 in `POST_ENGAGEMENT_SRS_ALIGNMENT.md`

---

### Note: GAP MT1 from POST_ENGAGEMENT_SRS_ALIGNMENT.md — Already Resolved ✅
The older analysis noted that entry meeting allowed `planning` phase (before EN transmitted). This has **already been fixed** in the code:
```python
MEETING_TYPE_ENGAGEMENT_PHASES = {
    'entry': ('fieldwork',),  # FIX-1: entry meeting requires EN transmitted (fieldwork phase)
    ...
}
```
Entry meetings now require `fieldwork` status, which is only set after EN transmission. No action needed.

---

## SRS Checklist — Status Summary

### Entry Meeting (Step 14)
| Requirement | Status | Gap |
|-------------|--------|-----|
| LA can create Entry Meeting linked to engagement | ✅ | — |
| Meeting date recorded | ✅ | — |
| Participants/attendance recorded | ✅ | — |
| Proceedings/minutes recorded | ✅ | — |
| Meeting type = "Entry Meeting" | ✅ | — |
| Entry Meeting Minutes as formal DRS output | ⚠️ Manual | GAP-9 — produced manually, not auto-generated on completion |
| Attendance Register as formal DRS output | ⚠️ Manual | GAP-9 — attendance sheet not auto-generated on completion |
| Only one entry meeting per engagement | ❌ | GAP-4 |
| Visible from engagement detail | ❌ | GAP-3 |

### Pre-exit Meeting (Step 17)
| Requirement | Status | Gap |
|-------------|--------|-----|
| LA can create Pre-exit Meeting linked to engagement | ✅ | — |
| Participants recorded | ✅ | — |
| Clarifications captured | ❌ | GAP-1 |
| Agreed observations captured | ❌ | GAP-1 |
| Dependency: WPs reviewed | ❌ | GAP-8 — phase-gated but doesn't check WP review status |
| Visible from engagement detail | ❌ | GAP-3 |

### Audit Team Meeting (Step 20)
| Requirement | Status | Gap |
|-------------|--------|-----|
| LA can create Audit Team Meeting | ✅ | — |
| Internal audit team only (no auditees) | ⚠️ Not enforced | Attendee roles not validated by backend |
| Deviations reviewed / captured | ⚠️ Partial | Can be recorded in `key_discussions` or `minutes`, but no structured field |
| Recommendations consolidated | ⚠️ Partial | Same — generic text, no structured link to findings/recommendations |
| Phase-gated after CIA approves WPs | ✅ | Allowed in fieldwork/reporting phases |

### Exit Meeting (Steps 23–24)
| Requirement | Status | Gap |
|-------------|--------|-----|
| LA can create Exit Meeting | ✅ | — |
| Exit Meeting Notification sent | ❌ | GAP-2 |
| Draft audit report attached to notification | ❌ | GAP-2 |
| Attendance sheet recorded | ✅ | via attendance_document_id DRS upload |
| Exit meeting minutes recorded | ✅ | via minutes_document_id DRS upload |
| Exit Meeting Minutes as formal DRS output | ⚠️ Manual | GAP-9 — produced manually, not auto-generated on completion |
| Attendance Register as formal DRS output | ⚠️ Manual | GAP-9 — attendance sheet not auto-generated on completion |
| Phase-gated to reporting/completed | ✅ | — |
| Visible from engagement detail | ❌ | GAP-3 |

---

## Priority Fix Order

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| **P1** | GAP-1: Pre-exit clarifications/agreed observations | Small | SRS data compliance |
| **P2** | GAP-2: Exit Meeting Notification + draft report | Medium | Major SRS requirement |
| **P3** | GAP-3: Meeting tab on Engagement Detail | Medium | Workflow UX |
| **P4** | GAP-4: Duplicate meeting type prevention | Small | Data quality |
| **P5** | GAP-5: Detail dialog field mismatches | Small | Bug fix |
| **P6** | GAP-6: Legacy field sync | Small | Data consistency |
| **P7** | GAP-8: Pre-exit WP review validation | Small | SRS dependency enforcement |
| **P8** | GAP-9: Auto-generate meeting minutes PDF | Medium | SRS formal output |
| **P9** | GAP-7: Action items UI | Small-Med | Enhancement (NOT in SRS) — defer |

---

## Files That Need Changes

| File | Gaps Addressed |
|------|---------------|
| `grc-service/apps/core/models/audit_entities.py` | GAP-1 (add fields), GAP-2 (add fields) |
| `grc-service/apps/api/serializers/audit_serializers.py` | GAP-1, GAP-2 (add to serializer) |
| `grc-service/apps/api/views/audit_meeting_views.py` | GAP-2 (notification endpoint), GAP-4 (duplicate check), GAP-6 (sync dates), GAP-8 (WP review check), GAP-9 (auto-generate minutes + attendance on completion) |
| `grc-service/apps/core/templates/meetings/` (new) | GAP-9 — HTML templates for minutes PDF and attendance register PDF |
| `grc-service/apps/api/urls/audit.py` | GAP-2 (new route) |
| `frontend/apps/staff-portal/src/types/grc.ts` | GAP-1, GAP-2 (add TS fields) |
| `frontend/apps/staff-portal/src/components/grc/CreateAuditMeetingDialog.tsx` | GAP-1 (conditional fields), GAP-7 (action items) |
| `frontend/apps/staff-portal/src/components/grc/AuditMeetingDetailDialog.tsx` | GAP-5 (fix field names) |
| `frontend/apps/staff-portal/src/pages/grc/EngagementDetailPage.tsx` | GAP-3 (add meetings tab) |
| `frontend/apps/staff-portal/src/services/grcService.ts` | GAP-2 (send notification API) |
| `frontend/apps/staff-portal/src/hooks/useAuditMeetings.ts` | GAP-2 (notification mutation) |
