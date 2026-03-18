# GAP-9 — Meeting Minutes & Attendance Register as Formal DRS Documents

## Status: ✅ COMPLETE

## Problem
The SRS (§1.8.3) requires Meeting Minutes and an Attendance Register to be produced as
formal Process Outputs stored in the Document Records Service (DRS) for each audit meeting.
Previously, PDFs were only generated on demand (if at all); they were never automatically
stored in DRS when a meeting was completed.

---

## Solution

Auto-generate both PDFs and upload them to DRS when a meeting transitions to `completed`.
Non-blocking: any generation/upload error is logged and swallowed so meeting completion
itself is never rolled back.

---

## Files Changed

| File | Change |
|------|--------|
| `apps/api/views/audit_meeting_views.py` | `_generate_meeting_documents()` helper (line ~86) + trigger in `AuditMeetingStatusUpdateView.post()` (line ~799) |
| `apps/core/utils/pdf_generators.py` | `generate_meeting_minutes_pdf()` and `generate_attendance_register_pdf()` |
| `templates/grc/meeting_minutes.html` | 8 sections, 60mm bottom margin, pre-exit conditional block |
| `templates/grc/attendance_register.html` | Attendance table, signature cells, summary counts, 60mm bottom margin |
| `apps/core/migrations/0006_alter_auditmeeting_options_and_more.py` | Migration adding `minutes_document_id` and `attendance_document_id` UUIDFields |
| `document-records-service/apps/infrastructure/persistence/seed_document_types.py` | Added `audit_meeting_minutes` and `audit_meeting_attendance` entries (types confirmed seeded in DRS DB) |

---

## Implementation Details

### Helper function — `_generate_meeting_documents(meeting, auth_token=None)`
Located in `audit_meeting_views.py` at line ~86 (before constants section).

**Scope rules (SRS §1.8.3):**
| Meeting Type | Minutes PDF | Attendance Register PDF |
|-------------|-------------|------------------------|
| `entry`     | ✅ generate  | ✅ generate             |
| `exit`      | ✅ generate  | ✅ generate             |
| `pre_exit`  | ✅ generate  | ❌ skip                 |
| `team`      | ❌ skip      | ❌ skip                 |

**Skip rule:** If `minutes_document_id` (or `attendance_document_id`) is already set,
the function skips that PDF — manual uploads are preserved and never overwritten.

**DRS document types:**
- Minutes → `document_type='audit_meeting_minutes'`
- Attendance → `document_type='audit_meeting_attendance'`

**No QR/stamp:** Meeting minutes have no CIA approval workflow, so
`generate_approved_stamp()` is NOT called. The 60mm bottom page margin in the HTML
templates reserves DRS stamp space but remains blank without a stamp image.

**Retention:** `retention_period=2555` days (≈7 years for audit records).

**Auth token:** Passed from the incoming request's `Authorization: Bearer <token>` header
so DRS receives proper credentials for document creation.

**Serializer:** `AuditMeetingSerializer` (single class, covers both list and detail responses)
already includes both fields in its `fields` list — no separate list/detail split needed.

**`refresh_from_db()` not needed:** `_generate_meeting_documents()` mutates the same
in-memory `meeting` object before returning, so the serializer in the view sees the
updated `minutes_document_id` / `attendance_document_id` without a DB re-fetch.

### Trigger in `AuditMeetingStatusUpdateView.post()`
Located at line ~799:
```python
# GAP-9: auto-generate meeting documents (minutes + attendance) on completion
if new_status == 'completed':
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    auth_token = (
        auth_header[len('Bearer '):].strip()
        if auth_header.startswith('Bearer ')
        else None
    )
    _generate_meeting_documents(meeting, auth_token=auth_token)
```
Placed **outside** the `transaction.atomic()` block so a DRS upload failure cannot
roll back the meeting status change.

---

## Test Cases

### 1. Entry meeting completion → both PDFs generated
```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/iam/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"cia@fcc.go.tz","password":"Pass@1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Prerequisite: meeting must have minutes text recorded and status must be 'in_progress'
# The view enforces: minutes text required before completing (MINUTES_REQUIRED guard)
# Transition to in_progress first if needed:
curl -X POST http://localhost:8080/api/v1/grc/meetings/$MEETING_ID/update-status/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Then record minutes via PATCH, then complete:
MEETING_ID=<your_entry_meeting_id>

curl -X POST http://localhost:8080/api/v1/grc/meetings/$MEETING_ID/update-status/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```
**Expected:** Response `data` contains non-null `minutes_document_id` AND `attendance_document_id`.
GRC logs: `GAP-9: Minutes PDF for meeting … uploaded` AND `GAP-9: Attendance PDF for meeting … uploaded`.

### 2. Pre-exit meeting completion → only minutes generated
Same as above (with `minutes` text set) but using a `pre_exit` type meeting.
**Expected:** `minutes_document_id` set. `attendance_document_id` remains null.

### 3. Team meeting completion → no PDFs generated
Same as above but using a `team` type meeting.
**Expected:** Both document IDs remain null. No `GAP-9` log lines appear.

### 4. Skip if already set (idempotency)
Pre-set `minutes_document_id` on a meeting via Django admin or direct DB update, then
transition it to `completed`.
**Expected:** The existing `minutes_document_id` is NOT overwritten.

### 5. DRS unavailable — meeting still completes
Temporarily misconfigure `DOCUMENT_SERVICE_URL` (e.g. wrong port), then complete a meeting.
**Expected:** Status transitions to `completed` successfully. `WARNING GAP-9: Could not generate/upload` logged. No 500 error returned.

### Verify GRC logs
```bash
docker logs fims-grc-service 2>&1 | grep "GAP-9"
```

---

## Related Gaps
- **GAP-6:** Engagement `entry_meeting_date`/`exit_meeting_date` auto-sync → `GAP6_ENGAGEMENT_DATE_SYNC.md`
- **GAP-8:** Pre-exit meeting blocked if no approved working papers → `GAP8_PRE_EXIT_WP_VALIDATION.md`
