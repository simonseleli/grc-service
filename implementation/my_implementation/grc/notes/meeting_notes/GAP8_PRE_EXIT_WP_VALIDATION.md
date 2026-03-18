# GAP-8: Pre-Exit Meeting Does Not Validate Working Papers Reviewed

**Status:** ✅ FIXED  
**Date:** 2026-03-17  
**File:** `grc-service/apps/api/views/audit_meeting_views.py`

---

## Problem

SRS Step 16 states:
> "LA reviews evidence gathered in Working Paper by audit team members… and arrange pre-exit meeting with the auditee."
> **Dependency: Working papers reviewed**

Pre-exit meeting creation only checked `engagement.status in ('fieldwork', 'reporting')`. It did NOT verify that any Working Papers had actually been approved, meaning a pre-exit meeting could be scheduled before any WPs were reviewed — violating the SRS dependency.

---

## Fix Applied

In `AuditMeetingListCreateView.post()`, immediately after the engagement phase check, added a guard for `pre_exit` meetings:

```python
# --- GAP-8: Pre-exit requires at least one approved working paper --
# SRS Step 16: LA must have reviewed WPs before arranging pre-exit meeting.
if meeting_type == 'pre_exit':
    has_approved_wp = WorkingPaper.objects.filter(
        engagement=engagement,
        review_status='approved',
        is_active=True,
    ).exists()
    if not has_approved_wp:
        return Response(
            {
                'success': False,
                'error': {
                    'message': (
                        'Cannot schedule a Pre-Exit Meeting until at least one '
                        'Working Paper for this engagement has been approved '
                        '(SRS Step 16 dependency).'
                    ),
                    'code': 'PRE_EXIT_REQUIRES_APPROVED_WPS',
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
```

`WorkingPaper` was already imported in the file (`from apps.core.models import ..., WorkingPaper`).

**Key decisions:**
- `review_status='approved'` = WP passed both Stage 1 (LA review) and Stage 2 (CIA approval) in the workflow. (`review_status='reviewed'` means rejected/sent back, not approved.)
- `is_active=True` = only counts active (non-soft-deleted) WPs
- Only `pre_exit` type is gated — `entry`, `team`, `exit` are not affected

---

## Tests Performed

### Setup
- Engagement: `ENG-20252026-001` (ID: `dfaf71de-682a-48e8-9a49-35126acb1896`, status: `fieldwork`)
- Working Papers: `WP-ENG-20252026-001-001` and `WP-ENG-20252026-001-002` both in `draft` status
- Authentication: `admin@fcc.go.tz`

---

### Test 1: Pre-exit with NO approved WPs → blocked

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id": "dfaf71de-682a-48e8-9a49-35126acb1896", "meeting_type": "pre_exit", "scheduled_date": "2026-05-10T10:00:00+03:00", "title": "Pre-Exit Test"}'
```

**Result:** ✅
```
success: False
code: PRE_EXIT_REQUIRES_APPROVED_WPS
msg: Cannot schedule a Pre-Exit Meeting until at least one Working Paper for this engagement has been approved (SRS Step 16 dependency).
```

---

### Test 2: Other meeting types NOT affected by WP check

Attempted to create a `team` meeting (no approved WPs) — it passed through the WP check and hit `DUPLICATE_MEETING_TYPE` instead (a different, pre-existing guard). Confirms the WP check only applies to `pre_exit`.

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id": "dfaf71de-682a-48e8-9a49-35126acb1896", "meeting_type": "team", "scheduled_date": "2026-05-05T09:00:00+03:00", "title": "Audit Team Meeting"}'
```

**Result:** ✅
```
success: False
code: DUPLICATE_MEETING_TYPE   ← NOT PRE_EXIT_REQUIRES_APPROVED_WPS
```

---

### Test 3: Pre-exit WITH an approved WP → allowed

Approved `WP-ENG-20252026-001-001` directly in the shell:

```bash
docker compose exec grc-service python manage.py shell -c "
from apps.core.models.audit_entities import WorkingPaper
wp = WorkingPaper.objects.get(reference_number='WP-ENG-20252026-001-001')
wp.review_status = 'approved'
wp.save(update_fields=['review_status'])
print('Approved:', wp.reference_number, '| status=', wp.review_status)
"
# Output: Approved: WP-ENG-20252026-001-001 | status= approved
```

Then attempted pre-exit creation again:

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8006/api/v1/grc/audit/meetings/" \
  -d '{"engagement_id": "dfaf71de-682a-48e8-9a49-35126acb1896", "meeting_type": "pre_exit", "scheduled_date": "2026-05-10T10:00:00+03:00", "title": "Pre-Exit Meeting - Test"}'
```

**Result:** ✅
```
success: True
ref: MTG-ENG-20252026-001-PRE_EXIT-002
```

Meeting created successfully — WP check passed with ≥1 approved WP.

---

## What Was NOT Changed

- **Model** — no changes to `WorkingPaper` or `AuditMeeting`
- **Serializer** — no changes
- **Migrations** — none required
- **Frontend** — no changes needed; the 400 error with `PRE_EXIT_REQUIRES_APPROVED_WPS` code can be displayed to the user
- **Other meeting types** — `entry`, `team`, `exit` creation is completely unaffected
