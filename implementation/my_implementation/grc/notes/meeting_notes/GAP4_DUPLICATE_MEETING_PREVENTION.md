# GAP-4: Duplicate Meeting Type Prevention

**Status:** ✅ COMPLETE  
**SRS Implication:** Each engagement should have at most one active meeting of each type (entry, pre_exit, team, exit). Cancelled meetings should not block new ones.

---

## What Was Implemented

Added a validation check in the backend `AuditMeetingListCreateView.post()` method that prevents creating a second non-cancelled meeting of the same type for the same engagement.

### Files Modified

| Layer | File | Change |
|-------|------|--------|
| View | `grc-service/apps/api/views/audit_meeting_views.py` | Added duplicate check after phase validation, before user check |

### Implementation

```python
# --- Prevent duplicate meeting type per engagement ---------------
existing = AuditMeeting.objects.filter(
    engagement=engagement,
    meeting_type=meeting_type,
    is_active=True,
).exclude(status='cancelled')
if existing.exists():
    type_display = dict(AuditMeeting.MEETING_TYPE_CHOICES).get(meeting_type, meeting_type)
    return Response(
        {
            'success': False,
            'error': {
                'message': (
                    f"This engagement already has an active '{type_display}' meeting "
                    f"({existing.first().reference_number}). "
                    f"Cancel or complete the existing meeting before scheduling a new one."
                ),
                'code': 'DUPLICATE_MEETING_TYPE',
            },
        },
        status=status.HTTP_400_BAD_REQUEST,
    )
```

### Key Design Decisions

- Uses `.exclude(status='cancelled')` so cancelled meetings don't block new ones
- Checks `is_active=True` to also skip soft-deleted meetings
- Returns the existing meeting's reference number in the error message for user clarity
- Error code `DUPLICATE_MEETING_TYPE` can be handled by frontend if needed

### No Frontend or Migration Changes Needed

Backend-only validation. Frontend gets a clear 400 error with a descriptive message.

---

## E2E API Tests

### Setup

```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/iam/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"auditor@fcc.go.tz","password":"Pass@1234"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access','') or d.get('data',{}).get('access',''))") \
  && echo "Token length: ${#TOKEN}"
```

Engagement used: `dfaf71de-682a-48e8-9a49-35126acb1896` (ENG-20252026-001, fieldwork phase)

### Test 1: Duplicate entry meeting → DUPLICATE_MEETING_TYPE

An entry meeting already existed (MTG-ENG-20252026-001-ENTRY-001).

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id":"dfaf71de-682a-48e8-9a49-35126acb1896","meeting_type":"entry","title":"Entry Conference 2","scheduled_date":"2026-04-05","agenda":"Second entry"}'
```

**Result:** ✅ Blocked
```json
{
  "success": false,
  "error": {
    "message": "This engagement already has an active 'Entry Meeting' meeting (MTG-ENG-20252026-001-ENTRY-001). Cancel or complete the existing meeting before scheduling a new one.",
    "code": "DUPLICATE_MEETING_TYPE"
  }
}
```

### Test 2: Different type (pre_exit) → SUCCESS

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id":"dfaf71de-682a-48e8-9a49-35126acb1896","meeting_type":"pre_exit","title":"Pre-Exit Conference","scheduled_date":"2026-04-10","agenda":"Discuss draft findings"}'
```

**Result:** ✅ `success=True ref=MTG-ENG-20252026-001-PRE_EXIT-001`

### Test 3: Duplicate pre_exit → DUPLICATE_MEETING_TYPE

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id":"dfaf71de-682a-48e8-9a49-35126acb1896","meeting_type":"pre_exit","title":"Pre-Exit 2","scheduled_date":"2026-04-12","agenda":"second"}'
```

**Result:** ✅ `success=False err_code=DUPLICATE_MEETING_TYPE`

### Test 4: New entry after cancelling old → SUCCESS

First cancelled the entry meeting:
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/89c8f178-7c09-4cb7-ba4a-a0c672014130/update-status/" \
  -d '{"status":"cancelled"}'
# Result: status=cancelled
```

Then created a new entry:
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id":"dfaf71de-682a-48e8-9a49-35126acb1896","meeting_type":"entry","title":"Entry Conference (Rescheduled)","scheduled_date":"2026-04-08","agenda":"Rescheduled kickoff"}'
```

**Result:** ✅ `success=True ref=MTG-ENG-20252026-001-ENTRY-002`

---

## Test Summary

| # | Test Case | Expected | Actual | Pass |
|---|-----------|----------|--------|------|
| 1 | Duplicate entry meeting | `DUPLICATE_MEETING_TYPE` | Blocked with existing ref | ✅ |
| 2 | Different type (pre_exit) for same engagement | Success | Created | ✅ |
| 3 | Duplicate pre_exit | `DUPLICATE_MEETING_TYPE` | Blocked | ✅ |
| 4 | New entry after cancelling old one | Success | Created as ENTRY-002 | ✅ |
