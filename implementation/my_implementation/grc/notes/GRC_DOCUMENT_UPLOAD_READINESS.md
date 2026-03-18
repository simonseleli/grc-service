# GRC Document Upload — Readiness Analysis

> Analysis of what is needed to enable document uploads (evidence, working papers,
> meeting files) across GRC.
> Conducted: March 14, 2026.

---

## Verdict

**GRC code is complete and correct. The problem is entirely in IAM data and DRS seed data.**

No changes are required in `grc-service/` code or the API gateway nginx config.
Two external fixes are needed to unblock all uploads.

---

## 1. What GRC Has (All Correct)

| Feature | File | Status |
|---------|------|--------|
| Risk Assessment evidence upload / list / detach | `apps/api/views/risk_assessment_views.py` → `RiskAssessmentEvidenceView` | ✅ |
| Working Paper creation → DRS upload | `apps/api/views/working_paper_views.py` → `EngagementWorkingPapersView` | ✅ |
| Audit Meeting minutes/attendance upload (via PATCH/PUT) | `apps/api/views/audit_meeting_views.py` → `_update()` | ✅ |
| URL routing for all evidence endpoints | `apps/api/urls/audit.py` | ✅ |
| DRS base URL setting | `config/settings.py` → `DOCUMENT_SERVICE_URL = http://document-records-service:8002` | ✅ |
| JWT passthrough to DRS on every call | All upload views forward `Authorization: Bearer` token | ✅ |
| DRS error → 502 response to frontend | All views catch `DocumentServiceError` | ✅ |
| API Gateway routes all `/api/v1/grc/` to `grc-service:8006` | `api-gateway/config/nginx.conf` | ✅ |

---

## 2. Root Cause of the 503 Error (Blocker — ALL Uploads)

### The full call chain that produces 503:

```
Frontend
  └─▶ POST /api/v1/grc/audit/risk-assessments/{id}/evidence/
           │
           ▼
      Nginx (API Gateway)       → routes /api/v1/grc/ to grc-service:8006   ✅
           │
           ▼
      GRC middleware            → JWT has "grc-service" in services → OK     ✅
      GRC view                  → calls DRS: POST http://document-records-service:8002/api/v1/documents/
           │
           ▼
      DRS JWTPermissionMiddleware
           → reads JWT services = ["grc-service"]
           → "document-service" NOT found                                     ❌ → returns 403
           │
           ▼
      GRC catches DocumentServiceError
           → returns 502 Bad Gateway to nginx
           │
           ▼
      Nginx: proxy_intercept_errors on + error_page 502 = @service_unavailable
           → returns 503 to frontend with:
              {"error": "service_unavailable", "message": "The requested microservice is not running..."}
```

### The database evidence:

```sql
-- All GRC users only have grc-service, never document-service:
email                  | services
auditor@fcc.go.tz      | {grc-service}
cia@fcc.go.tz          | {grc-service}
(all other users)      | {grc-service}

-- document-service has zero role assignments:
-- SELECT ... FROM roles WHERE service = 'document-service' → 0 rows
```

### Why this happens:

DRS `JWTPermissionMiddleware` gates every request at the service level first.
It checks `request.user_services` (from the JWT `services` array).
If `"document-service"` is not in that list, it returns **403** before any view runs.

The IAM JWT only includes a service in `services` if the user's role is registered under that service.
Currently **no GRC role** has an assignment to the `document-service` in IAM.

---

## 3. Fix 1 — IAM: Add `document-service` Role Assignments (Required)

This fix is done in the **IAM admin panel** or via an IAM management command.
No code changes in GRC or DRS.

### Roles that need `document-service` access:

| Role | Why | Minimum DRS Permissions Required |
|------|-----|---------------------------------|
| `internal_auditor` | Uploads evidence, creates working papers, uploads meeting docs | `document:document:create`, `document:document:read`, `document:classification:confidential` |
| `chief_internal_auditor` | Views evidence on assessments and working papers (read-only, does not use upload endpoints) | `document:document:read`, `document:classification:confidential` |

### How to add (IAM admin):

1. Go to IAM admin → Services → `document-service`
2. Create or find roles scoped to `document-service` for `internal_auditor` and `chief_internal_auditor`
3. Assign the permission codes listed above to each role
4. Make sure the role is linked to the correct users

After this fix:
- The JWT `services` array for `auditor@fcc.go.tz` (IA) will include `"document-service"`
- The JWT `permissions_flat` will include `document:document:create`, `document:document:read`, `document:classification:confidential`
- DRS middleware will allow the request through
- GRC's `POST /api/v1/documents/` calls will return 201 instead of 403

> **Users must re-login after this fix** so their JWT is refreshed with the new service/permissions.

---

## 4. Fix 2 — DRS Seeder: Add Missing Meeting Document Types (Required for meetings)

The audit meeting view uses two document type codes that are **not seeded** in DRS:

| Code used in GRC | Seeded in DRS? |
|------------------|----------------|
| `audit_working_paper` | ✅ Yes |
| `audit_report` | ✅ Yes |
| `audit_meeting_minutes` | ❌ **No** |
| `audit_meeting_attendance` | ❌ **No** |

Without these types, `POST /api/v1/documents/` returns **400** when the meeting view tries to
create a minutes or attendance document. The meeting upload silently logs a warning and continues
(the meeting saves, but no document is stored).

### Fix — Add to DRS seeder:

**File:** `document-records-service/apps/infrastructure/persistence/seed_document_types.py`

Add to `INITIAL_DOCUMENT_TYPES`:

```python
{
    'code': 'audit_meeting_minutes',
    'name': 'Audit Meeting Minutes',
    'description': 'Minutes and proceedings for audit meetings',
    'icon': 'clipboard-list',
    'color': '#DC2626',  # red-600
    'default_classification': 'confidential',
    'default_retention_period': 2555,  # 7 years
    'requires_approval': False,
    'reference_prefix': 'AMM',
    'is_system': False,
},
{
    'code': 'audit_meeting_attendance',
    'name': 'Audit Meeting Attendance',
    'description': 'Attendance register for audit meetings',
    'icon': 'user-check',
    'color': '#DC2626',  # red-600
    'default_classification': 'confidential',
    'default_retention_period': 2555,  # 7 years
    'requires_approval': False,
    'reference_prefix': 'AMA',
    'is_system': False,
},
```

Then re-run the seeder inside the DRS container:

```bash
docker exec fims-document-records-service python manage.py shell -c "
from apps.infrastructure.persistence.seed_document_types import seed_document_types
seed_document_types()
"
```

---

## 5. Fix 3 — IAM: `internal_auditor` missing `grc:audit_meeting:manage` (Needed for meeting uploads)

Even after fixes 1 and 2, IA users cannot upload meeting documents because the meeting view
requires `grc:audit_meeting:manage`, which `internal_auditor` does not have.

From IAM role data:
```
chief_internal_auditor → has: grc:audit_meeting:manage  ✅
internal_auditor       → does NOT have: grc:audit_meeting:manage  ❌
```

Meeting documents (minutes, attendance) are created during `PATCH /meetings/{id}/` which is
gated by `CanManageAuditMeeting` → requires `grc:audit_meeting:manage`.

Add `grc:audit_meeting:manage` to the `internal_auditor` role in IAM if IA staff are expected
to record meeting outcomes and upload files.

---

## 6. Summary of All Required Actions

| # | What | Where | Who Changes It |
|---|------|-------|----------------|
| 1 | Add `document-service` service access with `document:document:create`, `document:document:read`, `document:classification:confidential` to `internal_auditor` role | IAM admin / management command | Admin / Senior Dev |
| 2 | Add `document:document:read`, `document:classification:confidential` to `chief_internal_auditor` role under `document-service` | IAM admin / management command | Admin / Senior Dev |
| 3 | Add `audit_meeting_minutes` and `audit_meeting_attendance` to DRS document type seeder and re-run it | `document-records-service/apps/infrastructure/persistence/seed_document_types.py` | Dev (study policy, minimal code add) |
| 4 | Add `grc:audit_meeting:manage` to `internal_auditor` GRC role (if IA should manage meetings) | IAM admin | Admin / Business Decision |

**GRC service code: no changes needed.**
**API gateway: no changes needed.**

---

## 7. Upload Flow (After Fixes Applied)

### Risk Assessment Evidence (IA user)

```
POST /api/v1/grc/audit/risk-assessments/{id}/evidence/
  multipart/form-data: file=<file>, title=<optional>, description=<optional>

→ GRC checks: grc:risk_assessment:conduct ✅ (IA has this)
→ GRC calls DRS:
    POST /api/v1/documents/              [create metadata, type=audit_working_paper]
    POST /api/v1/documents/{id}/upload/  [upload file bytes]
→ GRC saves UUID to assessment.evidence_attachments
→ Returns 201 with document_id
```

### Working Paper (IA user)

```
POST /api/v1/grc/audit/engagements/{id}/working-papers/
  multipart/form-data: file=<file>, title=<required>, paper_type=<optional>

→ GRC checks: grc:audit_working_paper:manage ✅ (IA has this)
→ GRC calls DRS:
    POST /api/v1/documents/              [type=audit_working_paper]
    POST /api/v1/documents/{id}/upload/
→ GRC saves UUID to working_paper.document_id
→ Returns 201
```

### Audit Meeting Files (CIA or IA after fix 3)

```
PATCH /api/v1/grc/audit/meetings/{id}/
  multipart/form-data: minutes_file=<file>, attendance_file=<file>

→ GRC checks: grc:audit_meeting:manage
→ GRC saves text fields first, then:
    minutes_file:    POST /api/v1/documents/ [type=audit_meeting_minutes] + upload
    attendance_file: POST /api/v1/documents/ [type=audit_meeting_attendance] + upload
→ GRC saves UUIDs to meeting.minutes_document_id / meeting.attendance_document_id
→ Returns 200
```

---

## 8. Working Papers Evidence (Additional context)

Working papers also have their own evidence attachments (separate from the main file):

```
POST /api/v1/grc/audit/working-papers/{id}/evidence/   → upload evidence to working paper
GET  /api/v1/grc/audit/working-papers/{id}/evidence/   → list evidence
DELETE /api/v1/grc/audit/working-papers/{id}/evidence/{doc_id}/  → detach
```

These follow the same pattern as risk assessment evidence (type=`audit_working_paper`).
Same IAM fix (Fix 1) unblocks these as well.

---

## 9. Implementation Phases (Ordered Fix Plan)

> Follow these phases in order. Phase 1 has no dependencies and can be done first.
> Phase 4 (re-login) must always come last, after all IAM changes are complete.

---

### Phase 1 — DRS: Add Missing Document Types *(code + seed)*

**Unblocks:** meeting minutes and attendance file uploads
**No dependencies — do this first.**

1. Open `document-records-service/apps/infrastructure/persistence/seed_document_types.py`
2. Add `audit_meeting_minutes` and `audit_meeting_attendance` entries to `INITIAL_DOCUMENT_TYPES` (see section 4 above for exact code)
3. Re-run the seeder inside the DRS container:

```bash
docker exec fims-document-records-service python manage.py shell -c "
from apps.infrastructure.persistence.seed_document_types import seed_document_types
seed_document_types()
"
```

---

### Phase 2 — IAM: Add `document-service` Access to GRC Roles *(IAM admin)*

**Unblocks:** ALL document uploads (evidence, working papers, meeting files)
**This is the critical blocker fix.**

1. Go to IAM admin → Services → `document-service`
2. For **`internal_auditor`** role, add permissions:
   - `document:document:create`
   - `document:document:read`
   - `document:classification:confidential`
3. For **`chief_internal_auditor`** role, add permissions:
   - `document:document:read`
   - `document:classification:confidential`
4. Confirm the roles are linked to the correct users

---

### Phase 3 — IAM: Add `grc:audit_meeting:manage` to `internal_auditor` *(business decision)*

**Unblocks:** meeting file uploads for IA users (CIA already has this permission)
**Requires a business decision before applying.**

1. Confirm with the business whether `internal_auditor` users should record meeting outcomes and upload meeting files
2. If yes → IAM admin → GRC service → `internal_auditor` role → add `grc:audit_meeting:manage`

---

### Phase 4 — Re-login All Affected Users *(required after every IAM change)*

**JWTs are not refreshed until re-login — this step is mandatory.**

1. All `internal_auditor` and `chief_internal_auditor` users must log out and log back in
2. This issues a new JWT with the updated `services` array and `permissions_flat` entries

---

### Phase 5 — Verify End-to-End

Test each upload path after all phases are complete:

| Test | Endpoint | Expected Result |
|------|----------|-----------------|
| Risk assessment evidence | `POST /api/v1/grc/audit/risk-assessments/{id}/evidence/` | 201 Created |
| Working paper upload | `POST /api/v1/grc/audit/engagements/{id}/working-papers/` | 201 Created |
| Working paper evidence | `POST /api/v1/grc/audit/working-papers/{id}/evidence/` | 201 Created |
| Meeting minutes/attendance | `PATCH /api/v1/grc/audit/meetings/{id}/` | 200 OK |
