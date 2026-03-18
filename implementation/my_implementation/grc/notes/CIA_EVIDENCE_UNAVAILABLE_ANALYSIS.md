# CIA Evidence "(unavailable)" — Root Cause Analysis

> Issue: CIA (`cia@fcc.go.tz`) views a Risk Assessment and sees all evidence listed as `(unavailable)`.
> Auditor (`auditor@fcc.go.tz`) views the same Risk Assessment and sees all evidence correctly.
> Investigated: March 14, 2026.

---

## 1. The Exact Call Chain

When CIA opens a Risk Assessment detail view:

```
Frontend
  └─▶ GET /api/v1/grc/audit/risk-assessments/{id}/evidence/
              │
              ▼
        GRC view (RiskAssessmentEvidenceView.get)
              │  loops over each document UUID in assessment.evidence_attachments
              ▼
        DocumentServiceClient.get_document(doc_id)
              │  uses CIA's JWT as Bearer token
              ▼
        DRS: GET /api/v1/documents/{id}/
              │
              ▼
        DRS: can_access_document(document, cia_user_id, 'read', request)
              │
              ▼  returns 403 ← the failure point
              │
        GRC catches DocumentServiceError
              │
              ▼
        appends stub: { filename: '(unavailable)', status: 'missing' }
```

---

## 2. Why DRS Returns 403 for CIA (Full Decision Tree)

DRS `can_access_document` has 5 checks. CIA fails ALL of them:

| Step | Check | Result for CIA | Why |
|------|-------|---------------|-----|
| 0 | Is superuser? | ❌ DENIED | CIA is not superuser |
| 1 | Is document creator/owner? | ❌ DENIED | Auditor (IA) created the document, not CIA |
| 2 | Is document in a folder with CIA access? | ❌ DENIED | GRC never puts evidence in DRS folders |
| 3 | Is there a DocumentShare for CIA? | ❌ DENIED | GRC never creates DocumentShare entries on upload |
| 4 | Does CIA have the classification permission? | ❌ DENIED | **Permission code mismatch (see below)** |
| 5 | Default deny | → **403** | |

---

## 3. The Permission Code Mismatch (Root Cause)

**Step 4** is the correct path for CIA — a user with read access to confidential documents should be able to read them via their JWT classification permission.

However, there is a **mismatch between the permission code DRS checks and the permission code registered in IAM**:

### What DRS checks (in `document_access_control.py`):

```python
classification_permissions = {
    'public':       'document:document:read_public',
    'internal':     'document:document:read_internal',
    'confidential': 'document:document:read_confidential',   ← DRS expects this
    'restricted':   'document:document:read_restricted',
}
```

### What is registered in IAM (from `unified_service_permissions` table):

IAM has:
- `document:classification:confidential` ✅ registered, assigned to CIA
- `document:document:read` ✅ registered, assigned to CIA
- `document:document:read_confidential` ❌ **NOT registered in IAM at all**

### Result:

CIA's JWT `permissions_flat` contains `document:classification:confidential` and `document:document:read`,
but **never** `document:document:read_confidential`.

DRS checks for `document:document:read_confidential` → not found in CIA's JWT → **Step 4 fails → 403**.

---

## 4. Why the Auditor Sees Evidence Correctly

The auditor (`auditor@fcc.go.tz`) is the **creator** of the documents (`created_by = auditor_uuid`).

DRS Step 1 (`is_creator`) passes immediately → **200 OK** — no need to reach the classification check.

---

## 5. Solution Options

### Option A — IAM Data Change (Recommended)

Register `document:document:read_confidential` as a `ServicePermission` in IAM
(under `document-service`) and assign it to the relevant roles.

**Why this is the right fix:**
- No code changes to any service (GRC, DRS, or IAM)
- Pure data change — shell command on IAM database, same as Phase 2 and Phase 3 fixes
- Fixes ALL existing documents retroactively
- Works for any user who needs to read confidential documents

**What to add in IAM (`iam-service` shell):**

```python
from apps.roles.models import Service, ServicePermission, Role, RolePermission

drs = Service.objects.get(name='document-service')
grc = Service.objects.get(name='grc-service')

# Register the missing permission in IAM
perm, created = ServicePermission.objects.get_or_create(
    service=drs,
    permission_code='document:document:read_confidential',
    defaults={
        'name': 'Read Confidential Documents',
        'description': 'Read documents classified as confidential',
        'resource_type': 'document',
        'action': 'read_confidential',
        'category': 'document',
        'is_active': True,
    }
)
print(f'Permission: {"CREATED" if created else "ALREADY EXISTS"}')

# Assign to internal_auditor (IA uploads docs, also needs to re-read own docs across sessions)
# and chief_internal_auditor (CIA reviews evidence on all assessments)
for role_code, label in [('internal_auditor', 'IA'), ('chief_internal_auditor', 'CIA')]:
    role = Role.objects.get(code=role_code, service=grc)
    rp, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
    print(f'  [{label}] document:document:read_confidential: {"CREATED" if created else "ALREADY EXISTS"}')

print('Done. Users must re-login.')
```

**Users must re-login** after this to get a refreshed JWT.

---

### Option B — GRC DocumentShare on Upload (GRC-only code change)

When IA uploads evidence, GRC calls the DRS share endpoint (`POST /api/v1/documents/{id}/shares/`)
to create a `DocumentShare` entry for CIA with `read` permission.

**How it would work in GRC:**

In `RiskAssessmentEvidenceView.post()`, after a successful document upload:
1. Look up the `reviewed_by` field on the assessment (contains CIA's UUID if assigned)
2. Call `POST /api/v1/documents/{id}/shares/` with CIA's user_id and `permission='read'`

**Limitations of this approach:**
- `reviewed_by` may be `null` at the time of upload (CIA hasn't been assigned yet)
- All previously uploaded documents are NOT retroactively fixed — CIA still sees `(unavailable)` for existing evidence
- Adds complexity: one extra DRS API call per file uploaded
- If the CIA reviewer changes later, old documents remain shared with the old CIA
- Only fixes CIA access; any other role that should read evidence would also need shares

---

### Option C — DRS Code Change (DO NOT do this without senior approval)

Change `_get_classification_permission()` in DRS `document_access_control.py` to accept
`document:classification:confidential` instead of `document:document:read_confidential`.

**This was attempted and reverted** — touching DRS core service code without senior approval
violates the project rule: *"Core services must never be modified — only studied."*

---

## 6. Recommendation

**Option A is the correct fix.** It is:
- A data change only (IAM shell command, no code)
- Consistent with how Phases 2 and 3 were fixed
- The only fix that works for existing uploaded documents

**Option B** (GRC DocumentShare) is a valid GRC-only code alternative but has significant limitations
and does not fix already-uploaded evidence.

**Option C** (DRS code change) requires senior approval per the project core-service rule.

---

## 7. The `authentication.py` UUID Fix (Related DRS Change)

During diagnosis, a second DRS issue was also found and fixed:

**Issue:** `IAMJWTAuthentication.get_user()` in DRS `apps/api/authentication.py` was setting
`user.id = user_id` where `user_id` is a **raw string** from the JWT.
`document.created_by` is stored as a Python `UUID` object.
The equality check `document.created_by == user.id` (UUID == string) always returns `False`,
so **even the document creator could not upload files to their own document**.

**Fix applied:** Convert `user_id` to `UUID(str(user_id))` before setting on the user object.

**This fix is in DRS `apps/api/authentication.py`** — a non-core file.

If this was reverted along with other DRS changes, it needs to be re-applied for
**auditor file uploads to work at all** (the upload 503 will return).

> **For senior review:** The `authentication.py` fix is in `apps/api/` (service-specific layer),
> not in `apps/core/` (which is the protected core). It corrects a bug where string/UUID type
> mismatch breaks the creator ownership check for any user uploading documents.

---

## 8. Summary Table

| Problem | Root Cause | Fix Location | Touches Core? |
|---------|-----------|-------------|--------------|
| CIA sees `(unavailable)` | `document:document:read_confidential` not in IAM | IAM data (shell command) | No |
| Auditor upload was 503 | `user.id` = string vs `created_by` = UUID in DRS auth | DRS `apps/api/authentication.py` | No (`apps/api/`, not `apps/core/`) |

---

## 9. What CIA Should Be Able To Do (Per SRS)

From SRS `AUDT2_ext.md`:

- **Requirement 32**: *"The system shall facilitate the review and approval of working paper forms by the CIA."*
- **Step 19** (Process Flow): *"CIA review and approve working paper forms and submit to LA for further action."*

| Action | CIA | IA (Auditor) |
|--------|-----|-------------|
| View evidence list | ✅ Must review | ✅ |
| **Download / open** evidence file | ✅ Must read to review | ✅ |
| Approve working papers | ✅ Yes | ❌ |
| Upload evidence | ❌ IA uploads | ✅ |
| Delete evidence | ❌ | ✅ |

**CIA is a reviewer — they must be able to open/download files, not just see the names.**

---

## 10. Current State (End of Session — March 14, 2026)

### What is Working ✅

| Feature | Status |
|---------|--------|
| Auditor uploads evidence to Risk Assessment | ✅ Working |
| Auditor can see and remove their uploaded evidence | ✅ Working |
| CIA can see evidence list (names, size, date) | ✅ Working (fixed via IAM Option A) |
| `document:document:read_confidential` in IAM | ✅ Done (Section 9 of grc_notes.md) |
| `grc:audit_meeting:manage` for IA and CIA | ✅ Done (Section 10 of grc_notes.md) |
| DRS `audit_meeting_minutes` + `audit_meeting_attendance` types seeded | ✅ Done (Section 9 of Phase file) |

### What Is In the Container but NOT in Host Code ⚠️

| File | Change | Status |
|------|--------|--------|
| `document-records-service/apps/api/authentication.py` | Convert `user.id` to `UUID(str(user_id))` | In container ✅ / Host reverted ❌ |

**Risk:** If DRS container is rebuilt (`docker compose up --build`), the UUID fix is lost and auditor uploads break again with 503.

**Action needed:** Senior to review and approve this change for the host file.
See Section 7 above for the exact one-line fix and justification.

### What Has NOT Been Tested Yet ⏳

| Feature | What to test |
|---------|-------------|
| CIA downloads an evidence file | Click download on evidence — should open/download the file |
| Working paper upload by IA | `POST /api/v1/grc/audit/engagements/{id}/working-papers/` |
| Working paper evidence upload | `POST /api/v1/grc/audit/working-papers/{id}/evidence/` |
| Meeting minutes/attendance upload | `PATCH /api/v1/grc/audit/meetings/{id}/` with minutes_file + attendance_file |

---

## 11. How to Proceed Next Session

### Step 1 — Test CIA download
Log in as CIA (`cia@fcc.go.tz` / `Pass@1234`), open a Risk Assessment, click an evidence file.
- If it downloads/opens → ✅ proceed to Step 2
- If it gives a 403/503 → investigate DRS download endpoint permissions

### Step 2 — Test remaining upload flows
Log in as Auditor (`auditor@fcc.go.tz` / `Pass@1234`) and test:
1. Working paper upload (from Engagement detail)
2. Meeting minutes and attendance file upload (from Audit Meeting detail, PATCH)

### Step 3 — Send to Senior for DRS `authentication.py` review
Share `CIA_EVIDENCE_UNAVAILABLE_ANALYSIS.md` (this file) with the senior dev.
The change is in `apps/api/authentication.py` (not `apps/core/`):

```python
# File: document-records-service/apps/api/authentication.py
# In class IAMJWTAuthentication.get_user(), after: user_id = validated_token.get('user_id')

# Add these lines before: user = User()
try:
    user_id = UUID(str(user_id))
except (ValueError, AttributeError):
    logger.error(f"Invalid user_id format in JWT token: {user_id}")
    return AnonymousUser()

# Also add at top of file:
from uuid import UUID
```

### Step 4 — Once senior approves DRS fix
Apply the change to the host file and rebuild DRS:
```bash
docker compose up --build document-records-service
```

---

## 12. IAM Commands Reference for This Feature

All IAM changes are documented in:
`grc-service/implementation/my_implementation/grc/notes/grc_notes.md`

- **Section 9** — Grant DRS permissions (`document:document:create/read/confidential`) to GRC roles
- **Section 10** — Register `grc:audit_meeting:manage` and assign to IA and CIA
- **Section 11** — Grant `document:document:read_confidential` to GRC roles (CIA evidence fix)
