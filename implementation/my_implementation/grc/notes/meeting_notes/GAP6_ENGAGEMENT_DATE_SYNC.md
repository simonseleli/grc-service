# GAP-6: Legacy Meeting Date Fields on Engagement Model (Auto-Sync)

**Status:** ✅ FIXED  
**Date:** 2026-03-17  
**File:** `grc-service/apps/api/views/audit_meeting_views.py`

---

## Problem

`AuditEngagement` has two legacy fields:
```python
entry_meeting_date = models.DateTimeField(null=True, blank=True)
exit_meeting_date = models.DateTimeField(null=True, blank=True)
```

Meeting dates lived in TWO places — the `AuditMeeting.scheduled_date` and the `AuditEngagement.entry_meeting_date` / `exit_meeting_date`. They were never kept in sync, so the engagement fields were always `None` even when meetings existed.

---

## Fix Applied (Option A — Auto-Sync)

Added a helper function `_sync_engagement_meeting_date(meeting)` that:
- Maps `entry` → `engagement.entry_meeting_date`, `exit` → `engagement.exit_meeting_date`
- Sets the engagement field to `meeting.scheduled_date`
- Clears the engagement field to `None` when a meeting is `cancelled`
- Only writes to DB if the value actually changed
- Ignores `pre_exit` and `team` meeting types (no corresponding engagement fields)

Called from 3 places (all inside `transaction.atomic()`):
1. `AuditMeetingListCreateView.post()` — syncs when a meeting is created
2. `AuditMeetingDetailView._update()` — syncs when `scheduled_date` is updated via PUT/PATCH
3. `AuditMeetingStatusUpdateView.post()` — clears date when meeting is cancelled

No model changes or migrations required.

---

## Tests Performed

### Setup
- Engagement: `ENG-20252026-001` (ID: `dfaf71de-682a-48e8-9a49-35126acb1896`, status: `fieldwork`)
- Starting state: `entry_meeting_date: None`, `exit_meeting_date: None`
- Authentication: `admin@fcc.go.tz` via IAM token

### Test 1: PATCH scheduled_date → engagement syncs

```bash
# Update entry meeting scheduled_date from 2026-04-15 to 2026-04-20
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/072799cd-cd1c-4e81-b4c7-b00ae0cfd81a/" \
  -d '{"scheduled_date": "2026-04-20T14:00:00+03:00"}'
```

**Result:** ✅  
- Meeting `scheduled_date` → `2026-04-20T14:00:00+03:00`
- Engagement `entry_meeting_date` → `2026-04-20T14:00:00+03:00` (was `None`)

### Test 2: Cancel meeting → engagement date cleared

```bash
# Cancel the entry meeting
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/072799cd-cd1c-4e81-b4c7-b00ae0cfd81a/update-status/" \
  -d '{"status": "cancelled"}'
```

**Result:** ✅  
- Meeting status → `cancelled`
- Engagement `entry_meeting_date` → `None` (cleared)

### Test 3: Create new entry meeting → engagement date populated

```bash
# Create a new entry meeting (previous one was cancelled, so GAP-4 allows it)
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id": "dfaf71de-682a-48e8-9a49-35126acb1896", "meeting_type": "entry", "scheduled_date": "2026-05-01T09:00:00+03:00", "title": "Entry Meeting - GAP-6 Test"}'
```

**Result:** ✅  
- New meeting `MTG-ENG-20252026-001-ENTRY-003` created with `scheduled_date: 2026-05-01T09:00:00+03:00`
- Engagement `entry_meeting_date` → `2026-05-01T09:00:00+03:00`

### Test 4: pre_exit/team meetings don't affect engagement dates

**Result:** ✅  
- Existing `pre_exit` and `team` meetings had no effect on `entry_meeting_date` or `exit_meeting_date`

### Log Verification

```
fims-grc-service | Synced entry_meeting_date=2026-05-01 09:00:00+03:00 on engagement ENG-20252026-001 from meeting MTG-ENG-20252026-001-ENTRY-003
```

---

## What Was NOT Changed

- **Model** — `entry_meeting_date` and `exit_meeting_date` fields kept as-is on `AuditEngagement`
- **Serializer** — fields remain in `AuditEngagementSerializer` (read/write)
- **Frontend** — TypeScript types already have these optional fields; no UI change needed
- **Migrations** — none required
