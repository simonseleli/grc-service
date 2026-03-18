# Engagement Notification — SRS Alignment Analysis

**SRS Reference:** `AUDT2_ext.md`  
**Relevant SRS Sections:** §4.10.1.2 Audit Engagement, §4.10.1.3 Audit Survey, §4.10.1.4 Audit Implementation  
**Relevant SRS Steps:** 10–12, 14, 24–27  
**Date:** 2026-03-16

---

## SRS Requirements Summary for EN

| Step | SRS Requirement | Actor |
|------|-----------------|-------|
| 9 | CIA approves Audit Program and instructs LA to prepare EN | CIA |
| 10 | LA prepares EN and submits for vetting/approval | Lead Auditor (LA) |
| 11 | CIA approves EN — signature and QR code embedded automatically | CIA |
| 12 | EN and notification is sent to auditee | LA |
| 14 | LA arranges and conducts entry meeting; records attendance and proceedings | LA |
| 24 | System facilitates EN preparation by Lead Auditor | LA |
| 25 | System enables review and approval of EN by CIA or designated authority | CIA |
| 26 | System generates the Approved EN as output of the process | System |
| 27 | System facilitates arrangement and conduct of entry meeting between LA and auditee | LA |

**Communication & Entry Meeting section (SRS):**
> *"The system/process shall allow LA to: Send Engagement Notification to auditees. Arrange and conduct an entry meeting. Record attendance and meeting proceedings."*

---

## ✅ Implemented and Aligned

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 1 | EN model with full lifecycle status flow: `draft → under_review → approved → transmitted` | ✅ | `EngagementNotification.STATUS_CHOICES` |
| 2 | LA prepares EN (SRS Step 10, 24) | ✅ | `prepared_by` field; auditor-only "Add" button |
| 3 | LA edits EN only when in `draft` status | ✅ | Edit button gated to `canManageNotification` (auditor) |
| 4 | LA submits EN for CIA approval via WO workflow (SRS Step 10) | ✅ | `EngagementNotificationService.submit_for_approval()` |
| 5 | WO template: `grc.engagement_notification_approval` (1-stage CIA review) | ✅ | Single-stage CIA-only workflow |
| 6 | CIA approves EN (SRS Step 11, 25) | ✅ | Approve button shown to `!canManageNotification` (CIA) when `under_review` |
| 7 | CIA returns EN to LA for revision (SRS Step 25 implied) | ✅ | Return button shown to CIA; kafka consumer resets EN to `draft`, clears workflow |
| 8 | GAP 9: CIA signature + QR stamp triggered after approval via DRS (SRS Step 11) | ✅ (partial) | `_trigger_approved_stamp()` fires in kafka consumer; see gap below |
| 9 | `approved_by_cia` + `cia_approval_date` recorded on approval | ✅ | Set in `_handle_engagement_notification_completion()` |
| 10 | LA transmits EN to auditee after CIA approval (SRS Step 12) | ✅ | Transmit button shown to auditor when `approved`; calls `transmit()` in service |
| 11 | `transmitted_at` timestamp recorded on transmission | ✅ | `EngagementNotificationService.transmit()` |
| 12 | Parent `AuditEngagement` status advances to `fieldwork` after EN transmitted | ✅ | Done in `transmit()` service method |
| 13 | "Start Engagement Workflow" button requires EN approved OR transmitted | ⚠️ Partial | `EngagementDetailPage.tsx` — currently accepts both; SRS requires `transmitted` only (see GAP B) |
| 14 | Status auto-refreshes in UI after CIA approve or return (no manual reload needed) | ✅ | `useEngagementNotifications` hook triggers refetch on dialog close |
| 15 | EN notification emails: submitted (to CIA), approved/returned (to LA) | ✅ | `_publish_submitted_notification()`, `_publish_approval_notification()` |
| 16 | Kafka consumer handles single-stage EN rejection correctly | ✅ | `single_stage_templates` guard prevents accidental resets of other WO workflows |

---

## 📌 Clarification: Declaration of Independence vs EN Signature — Two Different SRS Requirements

These are **completely separate** — do not confuse them:

| Document | SRS Step | Who acts | How | Our implementation |
|----------|----------|----------|-----|-------------------|
| **Declaration of Independence / Conflict of Interest** | Step 16, 18, 38 | Each audit team member | User clicks **"Sign"** → system generates PDF → stores `document_id` → user can download | ✅ Done — `DeclarationDetailDialog` with "Download Signed Declaration" button via `documentClient.get(/{document_id}/download/)` |
| **Engagement Notification** | Step 11, 26 | System (automatically on CIA approval) | CIA approves in WO → system **auto-stamps** EN PDF with CIA signature + QR via DRS | ⚠️ Partial — stamp is triggered but blocked by missing `document_id` (see GAP F / GAP A below) |

> **The Declaration PDF download pattern (using `document_id` + DRS download endpoint) is the correct model to also use for EN once the EN PDF is generated.**

---

## ❌ Gaps — Not Implemented (SRS Requirement Exists)

### GAP F — EN PDF Not Auto-Generated (Root Cause) (SRS Step 26) ⚠️ Must Fix First

** REFERENCE IS: To see how This document generated and Download is implemented, we look on Signed Declaration is implemented in Declaration of Independence Signed Declaration i can download the signed Document


**SRS Requirement:**  
> *"The system shall generate the Approved Engagement Notification as an output of the process."*

**What's implemented:** EN is structured data (fields in DB). A PDF is only produced if LA **manually uploads** one via DRS. There is no auto-generation of the EN as a formatted PDF.

**Why this is the root cause:** `_trigger_approved_stamp()` in the Kafka consumer already handles stamping — but it only fires `if getattr(en, 'document_id', None)`. Because there is no auto-generated PDF, `document_id` is always `null`, so the stamp never fires and users can never download the document.

**Impact:** Without `document_id`, GAP A (download) cannot work at all. This must be resolved first.

**To fix:** When LA submits EN for approval, auto-generate the EN as a PDF in DRS using the EN's structured data (same pattern as Declaration signing). Backend endpoint in `engagement_notification_views.py` calls DRS to render a PDF from EN fields and stores the returned `document_id` on the record:

```python
# In EngagementNotificationService.submit_for_approval() — after workflow starts:
drs_result = drs_client.generate_document(
    template='engagement_notification',
    context={
        'reference_number': en.reference_number,
        'audit_period_start': str(en.audit_period_start),
        'audit_period_end': str(en.audit_period_end),
        'scope_summary': en.scope_summary,
        'prepared_by': str(en.prepared_by),
        'audit_team': en.audit_team_snapshot,
    }
)
if drs_result and drs_result.get('document_id'):
    en.document_id = drs_result['document_id']
    en.save(update_fields=['document_id', ...])
```

This unblocks GAP A (stamp fires) and enables the download button.

---

### GAP A — Download Button for Approved EN Not Available (SRS Step 11 / GAP 9)
** REFERENCE IS: To see how This Download is implemented, we look on Signed Declaration is implemented in Declaration of Independence Signed Declaration i can download the signed Document

**SRS Requirement:** After CIA approval, embed CIA signature and QR code in EN document and make it available.  
**What works:** `_trigger_approved_stamp()` is already wired in the Kafka consumer — it fires on `approved` decision and attempts to call DRS. DRS stamps the PDF **in-place** (same `document_id`, modified in-place; does NOT return a new URL).  
**What's actually missing:** `document_id` is `null` because no PDF is generated (GAP F). So the stamp never fires and there is nothing to download.

**Correct fix approach (Declaration pattern — no webhook needed):**  
Once GAP F is resolved and `document_id` is set:
1. DRS stamps the document in-place on CIA approval (existing code already handles this).
2. Add a **"Download Approved EN"** button in `EngagementNotificationDetailDialog.tsx` using the same pattern as `DeclarationDetailDialog`:

```tsx
// Show when status is 'approved' or 'transmitted' and document_id exists
{(notification.status === 'approved' || notification.status === 'transmitted')
  && notification.document_id && (
  <Button onClick={() => handleDownload(notification.document_id)}>
    <FileDown className="mr-2 h-4 w-4" />
    Download Approved EN
  </Button>
)}
```

```ts
// Download handler — same as DeclarationDetailDialog
const handleDownload = async (documentId: string) => {
  const response = await documentClient.get(`/${documentId}/download/`, { responseType: 'blob' });
  // create blob link and trigger download
};
```

> **Note:** The existing `stamped_document_url` field and the `"View Stamped Document"` external link in the dialog can remain as a bonus/fallback if DRS ever returns a URL. But the primary download mechanism should use `document_id` directly, matching the Declaration pattern. No DRS callback webhook is needed.

---

### GAP B — "Start Engagement Workflow" Should Require EN = `transmitted` (SRS Step 27)

**SRS Requirement:** Entry meeting (which starts fieldwork) happens only after EN is **sent to auditee**. Sending = `transmitted` status.  
**What's implemented:** The "Start Engagement Workflow" button is enabled when EN status is in `['approved', 'transmitted']`.  
**What the SRS strictly requires:** EN must be `transmitted` (not just `approved`) before fieldwork begins — transmitting is the act of formally notifying the auditee.

**Impact:** It is currently possible to start the engagement workflow before the auditee has been notified (EN = approved but not yet transmitted).

**To fix:** In `EngagementDetailPage.tsx`, tighten the precondition:
```ts
// Current (too permissive)
engagementNotification?.status === 'approved' || engagementNotification?.status === 'transmitted'

// Should be
engagementNotification?.status === 'transmitted'
```

---

### GAP C — No Outbound Email / Formal Delivery to Auditee on Transmit (SRS Step 12)

> ⏸️ **DEFERRED — FIMS Notification System Not Yet Fully Implemented**
> The notification/email delivery pipeline (WO `NotificationConsumer` + templates) is partially built but not production-ready.  
> This gap will be revisited once the notification system is stable.  
> — *Noted: 2026-03-16*

**SRS Requirement:** When EN is transmitted, the **auditee receives formal notification** — the EN document is sent to auditee contacts.  
**What's implemented:** LA clicks "Transmit to Auditee" → EN status becomes `transmitted`, `transmitted_at` is stamped. **No outbound message is sent to the auditee.**  
**What's missing:** An email (or system message via Notification Service) to the auditee's contact(s) with the EN document attached.

**Impact:** The auditee is never formally notified by the system. The "Transmit" action is currently an internal status change only.

**To fix when notification system is ready (MVP approach):**  
On `transmit()` in `engagement_notification_service.py`, call `publisher.send_notification()` with:
- `template_code='grc.engagement_notification.transmitted'`
- `recipients={'email': [auditee_email]}` — auditee email from IAM via `en.audit_engagement.auditable_entity.head_of_entity` UUID
- Context: EN reference number, engagement title, LA name, `detail_url`, `transmitted_at`

Also requires:
1. Template `grc.engagement_notification.transmitted` seeded in WO (`seed_notification_templates.py`) — same pattern as existing `grc.engagement_notification.submitted` template.
2. Auditee email resolvable via IAM for `head_of_entity` UUID on `AuditableEntity`.

The GRC-side code follows the exact same pattern as `_publish_submitted_notification()` already implemented in this file.

---

### GAP D — Entry Meeting Phase Guard (Meetings Module — Cross-Reference Only)

> **This fix touches the Meetings module, not any EN file.** Full details and code are in `POST_ENGAGEMENT_SRS_ALIGNMENT.md` as **GAP MT1 / FIX-1**.

**Why it is noted here:** `EngagementNotificationService.transmit()` is what advances the engagement to `fieldwork`. The entry meeting phase guard in `audit_meeting_views.py` currently allows entry meetings during `planning` — before EN is even transmitted. Fixing the guard enforces the SRS sequence (Step 12: EN sent → Step 14: entry meeting arranged). EN transmit is the upstream trigger, so the dependency is noted here for context.

**→ Apply when working on the Meetings module → `grc-service/apps/api/views/audit_meeting_views.py` (see POST_ENGAGEMENT_SRS_ALIGNMENT.md FIX-1)**

---

### GAP E — `notification_date` Not Auto-Set on Transmit (SRS Step 12)

**SRS Requirement:** The notification date on the EN document should reflect the actual date it was transmitted to the auditee.  
**What's implemented:** `notification_date` is an optional field set manually by LA when creating/editing the EN. `transmitted_at` is set automatically on transmit, but `notification_date` is not updated.  
**What's missing:** Auto-set `notification_date = transmitted_at.date()` when transmission occurs.

**Impact:** The notification date on the formal EN document may not match the actual transmission date.

**To fix:** In `EngagementNotificationService.transmit()`, add:
```python
en.notification_date = now.date()
en.save(update_fields=['status', 'transmitted_at', 'notification_date'])
```

---

---

## Priority Assessment

| Priority | Gap | Complexity | SRS Compliance Impact |
|----------|-----|------------|----------------------|
| 🔴 **Critical** | GAP F — EN PDF not auto-generated (root cause for GAP A) | Medium (DRS template + backend) | High — blocks stamp and download |
| 🔴 High | GAP B — Transmit required before fieldwork | Low (1-line frontend change) | High |
| 🔴 High | GAP E — notification_date auto-set | Low (1-line backend change) | Medium |
| 🟡 Medium | GAP A — Download button for approved EN | Low (after GAP F fixed — frontend only) | Medium |
| ⏸️ Deferred | GAP C — Outbound email to auditee on transmit | Blocked: FIMS notification system not yet complete | High |
| 🟡 Medium | GAP G — EN creation requires approved AuditProgram | Low (backend guard + 1-line frontend) | High |
| ↗ *Cross-module* | GAP D — Entry meeting phase guard | Meetings module fix — see POST_ENGAGEMENT FIX-1 | n/a |

---

## Recommended Fix Order

1. **GAP F first** — implement EN PDF auto-generation on submit (DRS template). This is the root cause that blocks everything else.
2. **GAP A** — once `document_id` is populated, add Download button in `EngagementNotificationDetailDialog.tsx` (Declaration pattern).
3. **GAP B** — tighten Start Engagement Workflow to require `transmitted` only.
4. **GAP E** — auto-set `notification_date` on transmit.
5. ~~**GAP C**~~ — ⏸️ DEFERRED — requires FIMS notification system to be production-ready first.
6. **GAP G** — add `AuditProgram.status == 'approved'` precondition on EN creation (backend + frontend).

> **GAP D** (entry meeting phase guard in `audit_meeting_views.py`) is a Meetings module fix — apply it from `POST_ENGAGEMENT_SRS_ALIGNMENT.md` FIX-1.

---

## Quick Wins (Can Be Done Now, No Dependencies)

### Fix 1: GAP B — Tighten Start Engagement Workflow Precondition
**File:** `frontend/apps/staff-portal/src/pages/grc/EngagementDetailPage.tsx`  
Change: `status === 'approved' || status === 'transmitted'` → `status === 'transmitted'`

### Fix 2: GAP E — Auto-set notification_date on transmit
**File:** `grc-service/apps/core/services/engagement_notification_service.py`  
In `transmit()`, add `en.notification_date = now.date()` and include in `update_fields`.

---

---

## GAP G — Pre-EN Chain Not Enforced (AuditProgram → EN)

### SRS Requirement

SRS §4.10.1.3 Step 9 → 10: CIA approves the Audit Program, then instructs LA to prepare EN. The EN-relevant link in the chain is:

```
AuditProgram (approved) → EN (can be created)
```

> **Note:** The upstream Survey → RCM → AuditProgram enforcement is a Planning module gap documented in `POST_ENGAGEMENT_SRS_ALIGNMENT.md`.

### What's Implemented

`EngagementNotification` creation only checks:

```
engagement.status == 'planning'
```

**No AuditProgram precondition exists:**

| Step | What should be required | What is actually checked |
|------|------------------------|--------------------------|
| `EngagementNotification` creation | `AuditProgram.status == 'approved'` | Only `engagement.status == 'planning'` |
| `EngagementNotification` creation | "Create EN" button disabled unless `auditProgram.status == 'approved'` in `EngagementDetailPage.tsx` | Not enforced in frontend |

### Impact

A user can create an EN today with no approved Audit Program — as long as the engagement is in `planning` phase. SRS Step 9 (CIA approves program, then instructs LA to prepare EN) is bypassed.

### Fix

**Backend — `engagement_notification_views.py` `post()` method:**
```python
# Add after the engagement.status check:
try:
    program = AuditProgram.objects.get(audit_engagement=engagement)
    if program.status != 'approved':
        return error_response(
            message="Audit Program must be approved before creating an Engagement Notification",
            code="AUDIT_PROGRAM_NOT_APPROVED",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
except AuditProgram.DoesNotExist:
    return error_response(
        message="An approved Audit Program must exist before creating an Engagement Notification",
        code="AUDIT_PROGRAM_MISSING",
        status_code=status.HTTP_400_BAD_REQUEST,
    )
```

**Frontend — `EngagementDetailPage.tsx` "Create EN" button:**  
The "Create EN" button should be disabled unless `auditProgram.status == 'approved'`. Add this to the same precondition block that already checks EN status.

> **Note:** The `AuditProgram` creation preconditions (Survey completed, RCM approved) are a Planning module fix — see `POST_ENGAGEMENT_SRS_ALIGNMENT.md`.

---

## Notes on Role Assignment

Per the SRS and current implementation:

| Action | Actor | How enforced |
|--------|-------|-------------|
| Create / Edit EN | Lead Auditor (LA) | `canManageNotification = !hasPermission(approve)` |
| Submit EN for approval | Lead Auditor (LA) | Same — `canManageNotification` |
| Approve EN | CIA | `!canManageNotification` (CIA has `approve` permission) |
| Return EN to draft | CIA | Same |
| Transmit EN to auditee | Lead Auditor (LA) | SRS §Communication & Entry Meeting: *"The system shall allow LA to send EN to auditees"* |

> **Note on Transmit:** SRS §4.10.1.3 Step 12 says LA sends the EN. The "Communication and Entry Meeting" section explicitly states the LA's responsibility. The `canManageNotification` check (auditor = true) on the Transmit button is therefore **correct per SRS**.
