# GAP-3: Meetings Card on Engagement Detail Page

**Status:** ✅ COMPLETE  
**SRS Context:** Meetings are linked to engagements (FK). Users need to see meetings within the engagement context.

---

## What Was Implemented

Added a "Meetings" card section to `EngagementDetailPage.tsx` following the exact same pattern as Working Papers, Declarations, and other existing cards. Also added `defaultEngagementId` prop to the create meeting dialog so the engagement is pre-selected.

### Files Modified

| Layer | File | Change |
|-------|------|--------|
| Engagement Page | `frontend/apps/staff-portal/src/pages/grc/EngagementDetailPage.tsx` | Added Meetings card with data hooks, state, JSX, create + detail dialogs |
| Create Dialog | `frontend/apps/staff-portal/src/components/grc/CreateAuditMeetingDialog.tsx` | Added `defaultEngagementId` prop, wired into form defaults + useEffect deps |

### No Backend Changes Needed

Backend already supports `?engagement=<uuid>` filtering on `GET /audit/meetings/`.

### Frontend Details

**Imports added:**
- `CreateAuditMeetingDialog`, `AuditMeetingDetailDialog`
- `useAuditMeetings`, `useCreateAuditMeeting`, `useSendAuditMeetingNotification`
- `AuditMeeting`, `AuditMeetingFormData` types

**State:**
- `isMeetingOpen` — controls create dialog
- `selectedMeeting` — controls detail dialog

**Data hook:**
```typescript
const { data: meetingsResult, isLoading: meetingsLoading } = useAuditMeetings(1, 100, { engagement: engagementId });
```

**Schedule button phase gating:** Visible when engagement is in `fieldwork`, `reporting`, or `completed` phase.

**Card contents:** List of clickable meeting items showing title, reference number, date, type badge, and status badge.

### Verification

- 0 TS errors
- Frontend build succeeded
- API filter returns correct response shape: `{ success: true, data: [...], meta: {...} }`
- `defaultEngagementId` pre-populates engagement field in create dialog
