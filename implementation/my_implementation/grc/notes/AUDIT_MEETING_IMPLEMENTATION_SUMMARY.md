# Audit Meeting — Implementation Summary

**Date completed:** March 2026  
**SRS reference:** §1.8.3 Conducting Internal Audit (Steps 14, 17, 20, 23, 24)  
**Branch:** development

---

## What was built

The Audit Meeting module allows the audit team to schedule, conduct, and document all formal meetings during an audit engagement. Four meeting types are supported as per SRS:

| Meeting Type | SRS Step | Purpose |
|---|---|---|
| Entry Meeting | Step 14 | Opening meeting between LA, audit team, and auditee process owners |
| Pre-Exit Meeting | Step 17 | Clarification of results before the exit meeting |
| Audit Team Meeting | Step 20 | Internal team review prior to exit meeting with auditee |
| Exit Meeting | Step 24 | Formal closing meeting; draft report presented to auditee |

---

## Backend (GRC Service)

### Model — `AuditMeeting`
- Linked to a parent `AuditEngagement`
- Auto-generated reference number: `MTG-{engagement_ref}-{TYPE}-{sequence}`
- Fields: `title`, `meeting_type`, `scheduled_date`, `actual_date`, `location`, `status`
- `attendees` — JSON list of participants: `name`, `title/position`, `role` (auditor/auditee/observer), `present` flag
- `agenda`, `minutes`, `key_discussions` — text fields for meeting content
- `clarifications`, `agreed_observations` — pre-exit specific fields (SRS Step 17)
- `action_items` — JSON list with `description`, `responsible`, `due_date`, `status`
- `minutes_document_id` — UUID pointing to the PDF in DRS
- `attendance_document_id` — UUID pointing to attendance register PDF in DRS
- Exit meeting notification fields: `notification_sent`, `notification_date`, `draft_report_id`

### Status lifecycle
```
scheduled → in_progress → completed
         ↘ cancelled       ↗ (no reversal)
```
- Meetings cannot be edited once `completed` or `cancelled`
- A meeting requires minutes text to be recorded before it can be marked `completed` (SRS requirement)
- Only one non-cancelled meeting per type per engagement (e.g. no duplicate entry meetings)

### API Endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/grc/audit/meetings/` | List meetings (filterable by engagement, type, status) |
| POST | `/api/v1/grc/audit/meetings/` | Schedule a new meeting |
| GET | `/api/v1/grc/audit/meetings/{id}/` | Get meeting detail |
| PATCH | `/api/v1/grc/audit/meetings/{id}/` | Update meeting details |
| DELETE | `/api/v1/grc/audit/meetings/{id}/` | Delete (only if scheduled/in_progress) |
| POST | `/api/v1/grc/audit/meetings/{id}/status/` | Change status (transition: scheduled → in_progress → completed / cancelled) |
| POST | `/api/v1/grc/audit/meetings/{id}/send-notification/` | Send exit meeting notification to auditee (SRS Step 23) |

### Business rules enforced
- Only the meeting organizer (LA who scheduled it) can edit, delete, or change status — `MEETING_NOT_ORGANIZER` error otherwise
- Pre-exit meeting can only be scheduled after working papers exist for the engagement (SRS Step 16 dependency)
- Exit meeting notification requires a `draft_report_id` (SRS Step 23: notification must include draft report)
- Exit meeting notification is one-time — cannot be resent if already sent
- `entry_meeting_date` and `exit_meeting_date` on the parent `AuditEngagement` are automatically synced when the corresponding meeting is created/updated/cancelled (GAP-6 fix)

### Auto PDF generation on completion (GAP-9)
When a meeting is marked `completed`, the system automatically generates PDFs and uploads them to DRS:

| Meeting Type | Minutes PDF | Attendance Register PDF |
|---|---|---|
| Entry | ✅ | ✅ |
| Pre-Exit | ✅ | ❌ (not required by SRS) |
| Audit Team | ❌ (internal only) | ❌ |
| Exit | ✅ | ✅ |

- PDFs are generated using WeasyPrint from HTML templates
- Uploaded to the Document Records Service (DRS); only the UUID is stored in GRC
- Non-blocking — PDF failure never rolls back the meeting completion
- Idempotent — existing document IDs are never overwritten

### Kafka events published
| Event | Trigger |
|---|---|
| `AUDIT_MEETING_CREATED` | Meeting scheduled |
| `AUDIT_MEETING_UPDATED` | Meeting details edited |
| `AUDIT_MEETING_STARTED` | Status → `in_progress` |
| `AUDIT_MEETING_COMPLETED` | Status → `completed` |
| `AUDIT_MEETING_CANCELLED` | Status → `cancelled` |

### Permissions (IAM)
| Permission | Who has it | What it allows |
|---|---|---|
| `grc:audit_meeting:manage` | `lead_auditor`, `internal_auditor` | Create, edit, change status, delete |
| `grc:audit_meeting:view` | `cia`, `audit_committee` | Read-only access |

---

## Frontend (Staff Portal)

### Pages & components
- **`AuditMeetingsPage`** — full CRUD table listing all meetings for an engagement; sortable columns (type, date, status); status colour-coded badges
- **`EngagementDetailPage`** — meetings section embedded in the engagement detail; shows meetings count and quick links
- **Schedule Meeting dialog** — form with all meeting fields; attendee management (add/remove rows)
- **Edit Meeting dialog** — same form, pre-populated
- **Status change actions** — "Start", "Complete", "Cancel" buttons per meeting row
- **Send Exit Notification** button — only visible for exit meetings; requires draft report ID

### Access control in UI
- Schedule Meeting button, Edit/Delete actions, and status actions are hidden for users with only `view` permission (`canManageMeetings` hook)
- Download buttons for Minutes and Attendance Register appear once `minutes_document_id` / `attendance_document_id` are set

---

## PDF Documents produced

### Meeting Minutes
Sections: Engagement Information → Meeting Details → Attendance Summary (table) → Agenda

### Attendance Register
Sections: Engagement Information → Meeting Details → Attendance Register (table with Signature column) → footer: `N Total Invited | N Present`

Both documents use reference number `MTG-ENG-XXXXXX-TYPE-NNN` and are downloadable through the DRS download endpoint via the API Gateway.

---

## What is NOT done / left for later

- **Fieldwork section of Working Papers** — left intentionally to resume next sprint
- Exit meeting notification email delivery (Kafka consumer picks this up — backend hook exists, email template TBD)
