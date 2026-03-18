# GAP-2: Exit Meeting Notification

**Status:** ✅ COMPLETE  
**SRS Reference:** Step 23 — LA sends Exit Meeting Notification including draft audit report

---

## What Was Implemented

Full-stack feature: backend API endpoint to mark an exit meeting's notification as sent (linking the engagement's approved draft report), frontend button in the detail dialog, and notification indicator in the list page.

### Files Modified

| Layer | File | Change |
|-------|------|--------|
| Model | `grc-service/apps/core/models/audit_entities.py` | Added `notification_sent` (BooleanField), `notification_date` (DateTimeField), `draft_report_id` (UUIDField) |
| Serializer | `grc-service/apps/api/serializers/audit_serializers.py` | Added 3 fields to `Meta.fields` + `read_only_fields` |
| View | `grc-service/apps/api/views/audit_meeting_views.py` | Added `AuditMeetingSendNotificationView` (~140 lines) |
| URL | `grc-service/apps/api/urls/audit.py` | Route: `meetings/<uuid:pk>/send-notification/` |
| Kafka Event | `grc-service/shared/constants/event_types.py` | `MEETING_NOTIFICATION_SENT` event |
| Migration | `grc-service/apps/core/migrations/0019_add_meeting_notification_fields.py` | Schema migration |
| TS Types | `frontend/apps/staff-portal/src/types/grc.ts` | `notification_sent`, `notification_date`, `draft_report_id` on `AuditMeeting` |
| API Service | `frontend/apps/staff-portal/src/services/grcService.ts` | `sendAuditMeetingNotification(id)` function |
| Hook | `frontend/apps/staff-portal/src/hooks/useAuditMeetings.ts` | `useSendAuditMeetingNotification()` mutation |
| Barrel Export | `frontend/apps/staff-portal/src/hooks/useAuditMutations.tsx` | Re-exports the new hook |
| Detail Dialog | `frontend/apps/staff-portal/src/components/grc/AuditMeetingDetailDialog.tsx` | "Exit Meeting Notification" section with Send button / Sent indicator |
| List Page | `frontend/apps/staff-portal/src/pages/grc/AuditMeetingsPage.tsx` | Send icon next to status badge for notified exit meetings |

### Backend View Logic

`AuditMeetingSendNotificationView.post(request, pk)`:

1. Fetch meeting by UUID (`get_object_or_404`)
2. Validate `meeting_type == 'exit'` → else `NOT_EXIT_MEETING`
3. Validate `status == 'scheduled'` → else `INVALID_MEETING_STATUS`
4. Validate `notification_sent == False` → else `NOTIFICATION_ALREADY_SENT`
5. Look up `AuditReport` where `engagement=meeting.engagement, report_type='draft', status='approved', is_active=True` → else `NO_APPROVED_DRAFT_REPORT`
6. Atomically set `notification_sent=True`, `notification_date=now`, `draft_report_id=report.id`
7. Publish `MEETING_NOTIFICATION_SENT` Kafka event
8. Return serialized meeting with success message

**Bug fix applied:** `except Http404: raise` before `except Exception` to prevent 404 being swallowed as 500.

---

## E2E API Tests

### Setup

```bash
# Login
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/iam/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"auditor@fcc.go.tz","password":"Pass@1234"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access','') or d.get('data',{}).get('access',''))") \
  && echo "Token length: ${#TOKEN}"
```

### Test 1: Non-existent meeting → 404

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/00000000-0000-0000-0000-000000000001/send-notification/" \
  | python3 -m json.tool
```

**Result:** ✅
```json
{
    "success": false,
    "error": {
        "code": "HTTP404",
        "message": "No AuditMeeting matches the given query.",
        "details": null
    }
}
```

### Test 2: Exit meeting without draft report → NO_APPROVED_DRAFT_REPORT

Created an exit meeting via Django shell (bypassing phase validation):
```bash
docker exec -i fims-grc-service python manage.py shell <<'PYEOF'
from apps.core.models import AuditMeeting, AuditEngagement
from django.utils import timezone
eng = AuditEngagement.objects.first()
meeting = AuditMeeting.objects.create(
    engagement=eng, meeting_type='exit', title='Exit Conference - E2E Test',
    scheduled_date=timezone.now(), location='Conference Room A',
    agenda='Review draft findings', status='scheduled',
    organized_by=eng.created_by, reference_number='MTG-TEST-001',
    created_by=eng.created_by,
)
print(f'MEETING_ID={meeting.id}')
PYEOF
```

```bash
MEETING_ID="f40d7968-f046-4722-8030-863c10dda62b"
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/${MEETING_ID}/send-notification/" \
  | python3 -m json.tool
```

**Result:** ✅
```json
{
    "success": false,
    "error": {
        "message": "No approved draft audit report found for this engagement. Per SRS Step 23, the exit meeting notification must include the draft audit report.",
        "code": "NO_APPROVED_DRAFT_REPORT"
    }
}
```

### Test 3: Exit meeting with approved draft report → SUCCESS

Created an approved draft report:
```bash
docker exec -i fims-grc-service python manage.py shell <<'PYEOF'
from apps.core.models import AuditReport, AuditEngagement, AuditOpinion
eng = AuditEngagement.objects.first()
uid = eng.created_by
opinion = AuditOpinion.objects.first()
report = AuditReport.objects.create(
    engagement=eng, report_type='draft', title='Draft Report Test',
    status='approved', reference_number='RPT-TEST-001',
    created_by=uid, prepared_by=uid, opinion=opinion,
)
print(f'REPORT_ID={report.id}')
PYEOF
```

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/${MEETING_ID}/send-notification/" \
  | python3 -m json.tool
```

**Result:** ✅
```json
{
    "success": true,
    "data": {
        "id": "f40d7968-f046-4722-8030-863c10dda62b",
        "engagement": "dfaf71de-682a-48e8-9a49-35126acb1896",
        "engagement_title": "ICT General Controls Audit 2025/2026",
        "engagement_reference": "ENG-20252026-001",
        "reference_number": "MTG-TEST-001",
        "meeting_type": "exit",
        "title": "Exit Conference - E2E Test",
        "notification_sent": true,
        "notification_date": "2026-03-17T14:52:41.281440+03:00",
        "draft_report_id": "a80876ad-d813-4f70-ae0b-1404f805f712",
        "status": "scheduled"
    },
    "message": "Exit meeting notification sent successfully. Draft audit report has been linked."
}
```

### Test 4: Duplicate notification → NOTIFICATION_ALREADY_SENT

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/${MEETING_ID}/send-notification/" \
  | python3 -m json.tool
```

**Result:** ✅
```json
{
    "success": false,
    "error": {
        "message": "Exit meeting notification has already been sent.",
        "code": "NOTIFICATION_ALREADY_SENT"
    }
}
```

### Test 5: Exit meeting via API (engagement in fieldwork phase) → INVALID_ENGAGEMENT_PHASE

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id":"dfaf71de-682a-48e8-9a49-35126acb1896","meeting_type":"exit","title":"Test","scheduled_date":"2026-04-01","agenda":"Test"}' \
  | python3 -m json.tool
```

**Result:** ✅
```json
{
    "success": false,
    "error": {
        "message": "Cannot schedule an 'exit' meeting for an engagement in 'fieldwork' phase. Allowed phases: reporting, completed.",
        "code": "INVALID_ENGAGEMENT_PHASE"
    }
}
```

---

## Test Summary

| # | Test Case | Expected Code | Actual | Pass |
|---|-----------|---------------|--------|------|
| 1 | Non-existent meeting | 404 | `HTTP404` | ✅ |
| 2 | No approved draft report | 400 | `NO_APPROVED_DRAFT_REPORT` | ✅ |
| 3 | Valid exit meeting + draft report | 200 | `notification_sent: true`, `draft_report_id` linked | ✅ |
| 4 | Duplicate notification | 400 | `NOTIFICATION_ALREADY_SENT` | ✅ |
| 5 | Wrong engagement phase | 400 | `INVALID_ENGAGEMENT_PHASE` | ✅ |

### Additional Checks

- **URL routing verified:** `grcClient → /api/v1/grc/ → nginx pass-through → grc-service:8006 → audit/ → meetings/<uuid>/send-notification/`
- **Migrations confirmed:** `[X] 0018` (GAP-1) and `[X] 0019` (GAP-2) both applied
- **Frontend build:** Passed with 0 TS errors, containers rebuilt and running
- **Detail dialog phantom fields fixed:** Removed non-existent `chaired_by` and `minutes_prepared_by` references
