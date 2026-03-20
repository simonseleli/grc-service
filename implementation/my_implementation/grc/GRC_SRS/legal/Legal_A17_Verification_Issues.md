# Legal Frontend Plan — Addendum A.17 Verification Issues

**Verified by:** GitHub Copilot (Claude Sonnet 4.6)  
**Date:** March 20, 2026  
**File audited:** `Legal_Module_Frontend_Implementation_Plan.md` — Addendum A.17 (lines ~2782–3087)  
**SRS source:** `Legal_Service.md`  
**Backend checked:** `grc-service/apps/api/views/`, `grc-service/apps/api/urls/legal.py`, `grc-service/apps/core/models/legal_entities.py`

---

## Status Overview

| # | Issue | Severity | Type | Status |
|---|---|---|---|---|
| 1 | `sendMeetingInvitations` endpoint does not exist | **High** | Missing backend endpoint | ✅ Done |
| 2 | Case Report/Timeline endpoint does not exist | **High** | Missing backend endpoint | ✅ Done |
| 3 | Case stats endpoint wrong path | **Medium** | Wrong URL in frontend plan | ✅ Done |
| 4 | Agenda outcome values incomplete — `noted` missing | **Low** | Wrong constant in frontend plan | ✅ Done |
| 5 | `LitigationDirective` status overdue inconsistency in plan doc | **Low** | Plan doc vs actual backend mismatch | ✅ Done |

---

## Issue 1 — `sendMeetingInvitations` endpoint does not exist

**A.17 Section:** A.17.2  
**A.17 claims:**
```ts
sendMeetingInvitations(id)  →  POST /api/v1/legal/meetings/{id}/send-invitations/
```

**Reality:** No such URL or view exists in the backend. Checked:
- `grc-service/apps/api/urls/legal.py` — no `send-invitations` pattern
- `grc-service/apps/api/views/legal_meeting_views.py` — no corresponding view class

**What does exist:**
- `POST /meetings/<meeting_pk>/participants/` — adds a participant (member or invitee)
- `DELETE /meeting-participants/<pk>/` — removes a participant
- Meeting status transitions are handled via workflow-action or PATCH on the meeting

**SRS says (§1.2.1 rule 5):** "When a meeting is created for a governing body, the system automatically populates the Members section with all active members." Auto-population is implemented. However, the explicit `INVITATIONS_SENT` status transition (REGISTERED → INVITATIONS_SENT) requires a deliberate Secretary action — there is no dedicated backend endpoint for it.

**Fix required (choose one):**

**Option A — Add backend endpoint (preferred, matches SRS lifecycle exactly):**
- Add `MeetingSendInvitationsView` to `legal_meeting_views.py`
- Add `meetings/<uuid:pk>/send-invitations/` to `legal.py` URLs
- Logic: check `status == 'registered'`, transition to `invitations_sent`, send notification to all participants with `invitation_status = 'pending'`

**Option B — Use PATCH (workaround):**
- Frontend PATCHes `{ status: 'invitations_sent' }` directly on the meeting
- Simpler but bypasses any server-side validation/notification logic
- Update A.17.2 service table accordingly: `sendMeetingInvitations(id)` calls `PATCH /meetings/{id}/` with `{ status: 'invitations_sent' }`

---

## Issue 2 — Case Report / Timeline endpoint does not exist

**A.17 Section:** A.17.5  
**A.17 claims:**
```ts
getCaseReport(caseType, caseId)  →  GET /api/v1/legal/cases/{type}/{id}/report/
```

**Reality:** No such URL or view exists. Checked:
- `grc-service/apps/api/urls/legal.py` — no `/report/` pattern on cases
- `grc-service/apps/api/views/legal_case_views.py` — no report view

**What does exist:**
- `GET /activity-log/<entity_type>/<entity_id>/` — granular audit log (NOT the same thing)
- Activity log logs every CRUD operation; the Report/Timeline is a curated milestone view

**SRS says (§4.13):** "A chronological timeline view of all case events (registration, filings, hearings, directives, judgments, settlements, closures) is available to all authorised users."

This is a genuine SRS requirement that was **missed during backend implementation**.

**Fix required — Add backend endpoint:**
- Add `CaseReportView` to `legal_case_views.py`
- Add URL: `cases/<str:side>/<uuid:pk>/report/` to `legal.py`
- Response: ordered list of milestone events aggregated from: case creation, `Hearing` records, `FilingDefendant/Plaintiff` records, `JudgmentDefendant/Plaintiff`, `SettlementDefendant/Plaintiff`, `LitigationDirective` (DG-issued), case status changes (from audit log)
- Permission: `grc:legal_case:view`
- Auth: required

**Endpoint spec:**
```
GET /api/v1/grc/legal/cases/{defendant|plaintiff}/{id}/report/

Response:
{
  "case_id": "...",
  "case_type": "defendant",
  "events": [
    {
      "id": "...",
      "event_type": "case_registered",
      "title": "Case Registered",
      "detail": "Registered by John Doe",
      "timestamp": "2025-01-15T09:00:00Z"
    },
    ...
  ]
}
```

**Event types to include:** `case_registered`, `dg_review_started`, `dg_review_completed`, `hearing_held`, `filing_submitted`, `filing_approved`, `settlement_recorded`, `judgment_recorded`, `appeal_filed`, `case_closed`, `directive_issued`

---

## Issue 3 — Case stats endpoint wrong URL path

**A.17 Section:** A.17.3  
**A.17 claims:**
```ts
getCaseDefendantStats()  →  GET /api/v1/legal/cases/defendant/stats/
getCasePlaintiffStats()  →  GET /api/v1/legal/cases/plaintiff/stats/
```
And legalKeys:
```ts
caseDefendantStatsKeys.stats
casePlaintiffStatsKeys.stats
```

**Reality:** These `/stats/` endpoints do NOT exist. The statistics are served by the **dashboard endpoints** instead:
```
GET /api/v1/grc/legal/dashboard/defendant/   ← returns defendant case KPIs
GET /api/v1/grc/legal/dashboard/plaintiff/   ← returns plaintiff case KPIs (+ recoverable/recovered amounts)
```

This was correctly documented in the backend implementation plan (Appendix D §D.15).

**Fix required — Update A.17.3 in the frontend plan:**

Replace service table entries:
```ts
// WRONG (from A.17.3):
getCaseDefendantStats()  →  GET /api/v1/legal/cases/defendant/stats/
getCasePlaintiffStats()  →  GET /api/v1/legal/cases/plaintiff/stats/

// CORRECT:
getCaseDefendantDashboard()  →  GET /api/v1/grc/legal/dashboard/defendant/
getCasePlaintiffDashboard()  →  GET /api/v1/grc/legal/dashboard/plaintiff/
```

Replace legalKeys entries:
```ts
// WRONG:
caseDefendantStatsKeys.stats
casePlaintiffStatsKeys.stats

// CORRECT:
legalDashboardKeys.defendant
legalDashboardKeys.plaintiff
```

Also update A.17.3 test scenario text:
```
// WRONG:
- [ ] KPI cards load with correct counts from `/legal/dashboard/stats/`

// CORRECT:
- [ ] FCCSuedCasesPage KPI cards load from GET /api/v1/grc/legal/dashboard/defendant/
- [ ] FCCSuingCasesPage KPI cards load from GET /api/v1/grc/legal/dashboard/plaintiff/
```

Also update A.16.10 Dashboard test scenario:
```
// WRONG:
- [ ] KPI cards load with correct counts from `/legal/dashboard/stats/`

// CORRECT:
- [ ] Defendant KPI cards load from GET /api/v1/grc/legal/dashboard/defendant/
- [ ] Plaintiff KPI cards load from GET /api/v1/grc/legal/dashboard/plaintiff/
```

---

## Issue 4 — Agenda outcome values incomplete (`noted` missing)

**A.17 Section:** A.17.1 and A.17.8  

**A.17.1 claims:**
```ts
export const AGENDA_OUTCOMES = ['approved', 'rejected', 'deferred'] as const;
```

**Reality:** The actual `MeetingAgenda` model has **4** outcome choices:
```python
OUTCOME_CHOICES = [
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('noted', 'Noted'),       ← MISSING from A.17.1
    ('deferred', 'Deferred'),
]
```

The SRS §1.1 mentions `Approved/Rejected/Deferred` but the backend also added `Noted` (which aligns with SRS §1.2.6 Resolutions where `Noted` is a valid status for agenda items that are acknowledged without formal determination).

**Fix required — Update A.17.1 constants:**

```ts
// WRONG:
export const AGENDA_OUTCOMES = ['approved', 'rejected', 'deferred'] as const;

// CORRECT:
export const AGENDA_OUTCOMES = ['approved', 'rejected', 'noted', 'deferred'] as const;
```

Also update `RecordAgendaOutcomeDialog` spec — the `outcome` Select field should have 4 options:
- Approved
- Rejected
- Noted ← add this
- Deferred

And update the outcome logic note:
```
// WRONG (A.17.1):
If outcome = 'approved': backend auto-creates directives; invalidate meetingDirectiveKeys...

// CORRECT:
If outcome = 'approved': backend auto-creates directives; invalidate meetingDirectiveKeys...
If outcome = 'noted': no directive auto-creation; submission remains Under Review (or moves to a final noted state)
If outcome = 'deferred': no directive auto-creation; submission remains Under Review
If outcome = 'rejected': no directive auto-creation; submission status → determined (rejected)
```

Also update SUBMISSION_OUTCOMES (A.17.8):
```ts
// WRONG:
SUBMISSION_OUTCOMES = ['approved', 'rejected', 'deferred']

// CORRECT:
SUBMISSION_OUTCOMES = ['approved', 'rejected', 'noted', 'deferred']
```

---

## Issue 5 — `LitigationDirective` status overdue inconsistency (plan doc vs actual)

**A.17 Section:** A.17.8  
**Affected old section:** Implementation plan Step 2 §4.5 (model status choices)

**A.17.8 correctly states:**
```ts
LITIGATION_DIRECTIVE_STATUSES = ['open', 'in_progress', 'closed']
// Note: litigation directives do NOT have 'fully_closed' state
```

**Actual backend model:**
```python
class LitigationDirective(TimestampedModel, StatusMixin):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]
```
✅ A.17.8 is **correct** here.

**The inconsistency is in the backend implementation plan** — [Legal_Module_Implementation_Plan.md](Legal_Module_Implementation_Plan.md) §4.5 lists:
```
| `LitigationDirective` | `pending → in_progress → completed → overdue` |
```
This is **wrong** — the actual backend uses `open → in_progress → closed` (3 statuses, no `pending` or `overdue`).

**Fix required — Update the backend plan doc §4.5 (for correctness):**
```
// WRONG in backend plan §4.5:
| `LitigationDirective` | `pending → in_progress → completed → overdue` |

// CORRECT:
| `LitigationDirective` | `open → in_progress → closed` |
```

---

## Additional Note — Meeting status choices in backend plan are also outdated

**This is not an A.17 issue but was discovered during verification.**

The **backend implementation plan** §4.5 states:
```
| `Meeting` | `scheduled → in_progress → completed → cancelled` |
```

But the **actual backend model** has 10 statuses:
```python
draft, registered, invitations_sent, agenda_shared, quorum_ready,
ongoing, postponed, closed, cancelled, rescheduled
```

A.17.2 correctly describes the full lifecycle. However, any other section of the frontend plan that references `scheduled → in_progress → completed → cancelled` is using the outdated values.

**Search for and fix in the frontend plan:**
- `status === 'scheduled'` → `status === 'draft'`
- `status === 'in_progress'` → `status === 'ongoing'` (for Meeting — not for other entities)
- `status === 'completed'` (Meeting) → `status === 'closed'`

---

## Fix Priority Order

1. **Issue 1 (send-invitations)** — Decide Option A or B, then either add backend endpoint or fix A.17.2 service table
2. **Issue 2 (case report)** — Add backend endpoint + add to frontend plan
3. **Issue 3 (stats path)** — Frontend plan text fix only (no backend change needed)
4. **Issue 4 (noted outcome)** — Frontend plan text fix only (no backend change needed)
5. **Issue 5 + Note (status choices)** — Both plan docs text fix only
