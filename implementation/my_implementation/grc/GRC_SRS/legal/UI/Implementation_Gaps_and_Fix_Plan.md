# Legal Menu Transformation — Implementation Gaps & Fix Plan

**Date Identified:** 2026-03-24  
**Based on:** `Legal_Menu_Transformation_Plan.md` vs live code audit  
**TypeScript Status:** ✅ Clean — 0 errors  
**Total Real Gaps:** 3  

---

## Audit Corrections (False Positives Cleared)

The following items were initially flagged as gaps but were confirmed **present and correct** upon deeper inspection:

| Initially Flagged | Actual Status | Evidence |
|---|---|---|
| STEP 1 — KPI cards "Total Meetings" and "Invitations Sent" missing | ✅ All 6 present | `LegalMeetingsPage.tsx` L128–133: Total, Draft, Registered, Invites Sent, Ongoing, Completed |
| STEP 1 — `CreateMeetingDialog` fields (meeting_type, agenda_summary, venue, venue_link) | ✅ All present | `CreateMeetingDialog.tsx` L39–132: all four fields in schema + form |
| STEP 9 — `BreachReportIntakeDialog` supporting documents + dual buttons | ✅ Complete | `BreachReportIntakeDialog.tsx` L231–267: Supporting Documents upload, Save Draft, Submit to DG |

---

## Real Gaps (3 items)

---

### GAP-001 — STEP 1: `CreateMeetingDialog` missing auto-generated Meeting Number field

**Step:** STEP 1 — Meeting Repository  
**File:** `apps/staff-portal/src/components/grc/legal/CreateMeetingDialog.tsx`  
**Priority:** Medium  
**Risk:** Low — cosmetic UX gap, no SRS compliance risk  

**Plan Requirement:**
> "Add `Meeting Number` as auto-generated read-only field" (STEP 1, UI Changes point 4)

**Current State:**  
The form has `meeting_type`, `agenda_summary`, `location`, `venue_link` — all correct.  
However, `meeting_number` is **not in the form at all** — no schema field, no input, no read-only display.

**Expected Behaviour:**  
- On create: show a read-only field displaying the auto-generated meeting number (from backend)
- On edit: show the existing meeting number as read-only
- Value is backend-generated (not user-entered); frontend displays it only

**Fix Required:**
1. In `CreateMeetingDialog.tsx` — add a read-only display field for `meeting_number` sourced from the entity when editing, or "Auto-assigned" placeholder when creating
2. Backend must return `meeting_number` in the meeting detail and creation response (verify this is already the case before fixing UI)

**Fix Instructions:**
```tsx
// In the form JSX, after the Title field, add:
{entity && (
  <div className="space-y-1">
    <label className="text-sm font-medium">Meeting Number</label>
    <Input value={entity.reference_number || entity.meeting_number || '—'} readOnly className="bg-muted" />
    <p className="text-xs text-muted-foreground">Auto-assigned by system</p>
  </div>
)}
```

---

### GAP-002 — STEP 3: No redirect route from old `/legal/resolutions` URL

**Step:** STEP 3 — Resolution Register  
**File:** `apps/staff-portal/src/App.tsx`  
**Priority:** Low  
**Risk:** Low — only affects users who bookmarked the old URL or followed an old internal link

**Plan Requirement (STEP 3, Routing Changes):**
> "Remove: `legal/resolutions` route  
> Add: `legal/resolution-register` → `ResolutionsPage`  
> *(Plan also says: keep old URL as redirect temporarily)*"

**Current State:**  
- New route `/legal/resolution-register` ✅ wired correctly  
- Old route `/legal/resolutions` is **completely absent** — navigating to it gives a 404/blank page  

**Fix Required:**  
Add a `<Navigate>` redirect in `App.tsx`:
```tsx
<Route path="legal/resolutions" element={<Navigate to="/service/grc/legal/resolution-register" replace />} />
<Route path="legal/resolutions/:id" element={<Navigate to="/service/grc/legal/resolution-register" replace />} />
```

**Placement:** Add these two lines immediately before or after the `legal/resolution-register` routes in `App.tsx`.

---

### GAP-003 — STEP 4: No redirect route from old `/legal/directives` URL

**Step:** STEP 4 — Directives  
**File:** `apps/staff-portal/src/App.tsx`  
**Priority:** Low  
**Risk:** Low — same as GAP-002; affects bookmarked links and any cross-page references still using the old path

**Plan Requirement (STEP 4, Routing Changes):**
> "Change: `legal/directives` → `legal/meeting-directives`  
> Change: `legal/directives/:id` → `legal/meeting-directives/:id`  
> *(Implies keeping old URL as redirect)*"

**Current State:**  
- New route `/legal/meeting-directives` ✅ wired correctly  
- Old route `/legal/directives` is **completely absent** — navigating to it gives a 404/blank page  

**Fix Required:**  
Add a `<Navigate>` redirect in `App.tsx`:
```tsx
<Route path="legal/directives" element={<Navigate to="/service/grc/legal/meeting-directives" replace />} />
<Route path="legal/directives/:id" element={<Navigate to="/service/grc/legal/meeting-directives" replace />} />
```

**Placement:** Add these two lines immediately before or after the `legal/meeting-directives` routes in `App.tsx`.

**Additional check:** Search all pages for any hardcoded `navigate('/service/grc/legal/directives')` or `<Link to="/service/grc/legal/directives">` references and update them to the new URL. Known locations to check:
- Dashboard legal quick links
- Meeting detail page → Directives tab (any cross-links)

---

## Fix Order (Recommended)

| Order | Gap | Reason |
|-------|-----|--------|
| 1 | GAP-002 (Resolutions redirect) | 2-line App.tsx change — zero risk, instant fix |
| 2 | GAP-003 (Directives redirect) + cross-link cleanup | 2-line App.tsx change + grep for old URLs. Do together since both are redirect-type fixes in the same file |
| 3 | GAP-001 (Meeting Number display) | Requires backend verification first (confirm `reference_number` / `meeting_number` is in API response), then small UI addition |

---

## Fix Scope Summary

| Gap | File(s) to Touch | Lines of Change (approx) |
|-----|-----------------|--------------------------|
| GAP-001 | `CreateMeetingDialog.tsx` | ~8 lines (read-only display block) |
| GAP-002 | `App.tsx` | 2 lines |
| GAP-003 | `App.tsx` + any pages with old URL hardcoded | 2 lines + grep cleanup |

**Total estimated change:** ~15–20 lines across 2–3 files.  
No new components required. No routing restructuring required.

---

## Steps Confirmed Complete (No Further Work Needed)

| Step | Status |
|------|--------|
| STEP 1 — Meeting Repository (sidebar, list KPIs, detail tabs, Quorum, lifecycle buttons) | ✅ Complete |
| STEP 2 — Meeting Packs (sidebar, list page, detail page, routes) | ✅ Complete |
| STEP 3 — Resolution Register (sidebar, URL, list columns, detail page, export) | ✅ Complete (except GAP-002) |
| STEP 4 — Directives (sidebar, URL, list columns, detail fields, [Fully Close] removed — SRS §1.2.4 BR#2 ✅) | ✅ Complete (except GAP-003) |
| STEP 5 — Submission for Determination (sidebar, list columns, Withdraw action) | ✅ Complete |
| STEP 6 — Minutes Sharing (sidebar, list columns, Draft button, Submit for Approval, All Bodies filter) | ✅ Complete |
| STEP 7 — Public Register (Decision ID, Created By columns) | ✅ Complete |
| STEP 8 — FCC Sued (sidebar, 6 KPIs, 9 tabs, DG Review panel, Closure dialog, CreateCaseDefendantDialog enhancements) | ✅ Complete |
| STEP 9 — FCC Suing (sidebar, 8 KPIs, 9 tabs, DG Review panel, Closure dialog, CreateCasePlaintiffDialog, BreachReportIntakeDialog enhancements) | ✅ Complete |
