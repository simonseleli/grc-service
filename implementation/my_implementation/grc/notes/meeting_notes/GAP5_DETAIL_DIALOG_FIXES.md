# GAP-5: Detail Dialog Field Mismatches (Fixed alongside GAP-1)

**Status:** ✅ FIXED  
**File:** `frontend/apps/staff-portal/src/components/grc/AuditMeetingDetailDialog.tsx`

---

## What Was Fixed

The attendees table in the detail dialog referenced non-existent fields on the `MeetingAttendee` type:

| Wrong Field | Correct Field |
|-------------|---------------|
| `a.organization` | `a.title` |
| `a.attended` | `a.present` |
| `a.id` (as key) | `idx` (array index) |

Also removed phantom "Roles & Metadata" section that referenced:
- `item.chaired_by` → does not exist (model has `organized_by` which is a UUID, not display name)
- `item.minutes_prepared_by` → does not exist anywhere in the system

These always rendered as "Not specified" and were misleading.
