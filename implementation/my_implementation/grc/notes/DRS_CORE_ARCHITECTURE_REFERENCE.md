# DRS Core Architecture Reference

> Deep-dive study of Document Records Service (DRS) internals.
> For the **consumer/client side** (how GRC calls DRS), see `DRS_DOCUMENT_UPLOAD_REFERENCE.md`.
> This file covers **how DRS itself works**, what it expects, and
> what any calling service must satisfy.

---

## 1. Layered Architecture

DRS follows Clean Architecture (Onion / Hexagonal). Requests flow inward through layers:

```
HTTP Request
    ↓
[Middleware]  JWTPermissionMiddleware           → sets request.document_permissions
    ↓
[API Layer]   apps/api/views/*.py               → REST views
    ↓
[Use Cases]   apps/core/use_cases/document/     → orchestrate business rules
    ↓
[Domain]      apps/core/entities/document.py    → pure business logic, no Django
    ↓
[Repository]  apps/infrastructure/persistence/  → Django ORM models & queries
    ↓
[Storage]     local media/ (or S3)              → actual file bytes
```

Layer dirs:
| Dir | Role |
|-----|------|
| `apps/api/` | REST views, serializers, URL patterns, permission classes |
| `apps/core/` | Domain entities, use cases, middleware, permissions config |
| `apps/domain/` | Domain services (thin wrapper) |
| `apps/infrastructure/` | Django ORM models, repos, external clients (IAM), Kafka |

---

## 2. Service Identity

| Setting | Value |
|---------|-------|
| IAM registered name (`unified_services.name`) | `document-service` |
| Docker container hostname | `document-records-service` |
| Internal port | `8002` |
| Django `settings.SERVICE_NAME` | `document-records-service` |
| GRC env `DOCUMENT_SERVICE_URL` | `http://document-records-service:8002` |

> **⚠️ The IAM name is `document-service`** (no "records").
> JWT tokens store this in `services: ["document-service", ...]`.
> The middleware checks against this IAM-registered name.

---

## 3. Authentication Chain

Every request to DRS passes through two layers:

### Layer 1 — `JWTPermissionMiddleware` (middleware, runs first)

**File:** `apps/core/permission_middleware.py`

What it does, in order:
1. Skips `/health/`, `/admin/`, `/static/`, `/media/`, `/api/v1/auth/`, `/api/v1/token/`, ONLYOFFICE callback, and `*/download/` paths.
2. Extracts `Authorization: Bearer <token>` header.
3. Decodes JWT using `settings.JWT_SECRET_KEY` (same shared key as IAM).
4. Sets on `request`:
   - `request.user_id` — UUID string
   - `request.user_email` — email string
   - `request.is_superuser` — bool
   - `request.is_staff` — bool
   - `request.user_permissions` — dict (now always `{}` due to IAM token optimization)
   - `request.user_permissions_flat` — list (all permissions across services, e.g. `['document:document:create', 'document:document:read', 'grc:risk_assessment:conduct', ...]`)
   - `request.user_services` — list of IAM service names, e.g. `['document-service', 'grc-service']`
5. **Service gate**: if user is not superuser AND `document-service` not in `request.user_services` → returns **403**.
6. Extracts `request.document_permissions`:
   - For superusers: `['*']`
   - For regular users: extracts all permissions from `permissions_flat` that start with `document:` (e.g. `document:document:create`, `document:document:read`, ...).
7. Returns `None` (passes to next middleware/view).

### Layer 2 — `IAMJWTAuthentication` (DRF authentication class)

**File:** `apps/api/authentication.py`

- Validates the JWT signature using `simplejwt` + shared secret.
- Creates a minimal Django `User` object from the JWT payload.
- Sets `request.user` — this satisfies DRF's `IsAuthenticated` for views.

### Result: every view gets both `request.user` (for DRF) AND `request.document_permissions` (for permission checks).

---

## 4. JWT Payload Structure (IAM-Issued)

The IAM `EnhancedAccessToken` generates JWT with:

```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "is_staff": false,
  "is_superuser": false,
  "permissions": {},
  "permissions_flat": [
    "document:document:create",
    "document:document:read",
    "document:document:update",
    "document:classification:confidential",
    "grc:risk_assessment:conduct",
    "..."
  ],
  "services": ["document-service", "grc-service"],
  "roles": ["IA", "GRC_STAFF"]
}
```

> **Important:** `permissions` is always `{}` (empty dict) as an IAM optimization to keep
> token size small. All permissions live in `permissions_flat`.
> The DRS middleware is aware of this and reads `permissions_flat`.

---

## 5. Permission System

### Permission Codes

**File:** `config/permissions/document-service.json`

All DRS permission codes follow the pattern `document:<resource>:<action>`.

Key document management codes:

| Code | Action |
|------|--------|
| `document:document:create` | Create document metadata |
| `document:document:read` | Read/list documents |
| `document:document:update` | Edit document metadata |
| `document:document:delete` | Delete document (draft only) |
| `document:document:approve` | Move document to approved status |
| `document:document:permanent_delete` | Permanent delete (DG-level) |
| `document:classification:confidential` | Access confidential documents |
| `document:classification:public` | Access public documents |
| `document:system:admin` | Full system administration |
| `document:document_version:create` | Create new document version |

### Permission Check Classes

**File:** `apps/api/permissions_jwt.py`

Core function:
```python
def _check_permission_locally(request, permission_code: str) -> bool:
    """Reads request.document_permissions (set by middleware)."""
    document_permissions = getattr(request, 'document_permissions', [])
    if hasattr(request, 'is_superuser') and request.is_superuser:
        return True  # Superusers bypass all checks
    return '*' in document_permissions or permission_code in document_permissions
```

Permission classes available:

| Class | Checks |
|-------|--------|
| `CanCreateDocument` | `document:document:create` |
| `CanReadDocument` | `document:document:read` |
| `CanUpdateDocument` | `document:document:update` |
| `CanDeleteDocument` | `document:document:delete` |
| `CanAdminDocumentSystem` | `document:system:admin` |
| `HasPermission('code')` | Any specific code |
| `HasAnyPermission(['a','b'])` | At least one |
| `HasAllPermissions(['a','b'])` | All of them |

### What Views Actually Check

| DRS Endpoint | View | Permission Required |
|---|---|---|
| `GET /api/v1/documents/` | `DocumentListCreateView` | `document:document:read` OR `document:system:admin` |
| `POST /api/v1/documents/` | `DocumentListCreateView` | `document:document:create` OR `document:system:admin` |
| `GET /api/v1/documents/{id}/` | `DocumentDetailView` | `IsAuthenticated` + `can_access_document()` |
| `PUT /api/v1/documents/{id}/` | `DocumentDetailView` | `IsAuthenticated` + `can_access_document()` (edit) |
| `DELETE /api/v1/documents/{id}/` | `DocumentDetailView` | `IsAuthenticated` + `can_access_document()` (admin) |
| `POST /api/v1/documents/{id}/upload/` | `DocumentUploadView` | `IsAuthenticated` only |
| `GET /api/v1/documents/{id}/download/` | `DocumentDownloadView` | Skipped by middleware, `IsAuthenticated` only |
| `POST /api/v1/documents/{id}/versions/` | `DocumentVersionsView` | `IsAuthenticated` |
| `POST /api/v1/documents/{id}/generate-approved-stamp/` | `GenerateApprovedStampView` | `IsAuthenticated` |

> **Key:** `POST /api/v1/documents/{id}/upload/` **does NOT check** `document:document:update` — 
> only `IsAuthenticated`. But `POST /api/v1/documents/` (creating metadata) checks
> `document:document:create`.

---

## 6. Document Access Control (`can_access_document`)

**File:** `apps/api/utils/document_access_control.py`

For detail/edit/delete views, DRS uses a richer decision tree. The middleware gates the service,
but this function gates individual documents:

```
0. Is user superuser/admin?          → GRANT all access
1. Is user the document creator?     → GRANT full access
2. Is document in a folder?
   a. Does the folder have shares?
      - No shares → folder is open → GRANT read
      - Has shares → check user's share in folder.access_permissions
        - Has share → GRANT at that folder permission level
        - No share  → DENY (folder is restricted)
3. Any active DocumentShare for this user (direct/group/role)?  → GRANT at share level
4. Does user have classification permission in JWT?
   e.g. document.classification = 'confidential' → need 'document:classification:confidential'
   → GRANT read-only if yes
5. Default → DENY
```

Permission level hierarchy: `read < comment < edit < admin/manage`

> **Summary for GRC use case:** GRC creates documents with `created_by = user_id` (the IAM user
> whose JWT was passed). That user then owns the document and passes step 1 for all future access.

---

## 7. Document Entity

**File:** `apps/core/entities/document.py`

### Statuses (`DocumentStatus`)

| Status | Meaning |
|--------|---------|
| `draft` | Just created, can be edited/deleted |
| `under_review` | Submitted for review |
| `approved` | Approved (no edits allowed) |
| `rejected` | Rejected |
| `active` | In active lifecycle |
| `semi_active` | Semi-active lifecycle stage |
| `inactive` | Inactive lifecycle stage |
| `closed` | Closed (no edits allowed) |
| `eligible_for_decongestion` | Ready for disposal review |
| `archived` | Archived |
| `disposed` | Permanently disposed |

### Classifications (`DocumentClassification`)

| Value | Meaning |
|-------|---------|
| `open` | Publicly accessible |
| `confidential` | Restricted to authorized users |

> Note: `internal` and `restricted` are used elsewhere in access code but the
> actual domain entity only has `open` and `confidential`.

### Business Rules (entity methods)

```python
document.can_edit(user_id)   # False if disposed, approved, closed, locked by another
document.can_delete(user_id) # Only draft documents, not locked, not archived
```

---

## 8. Document Types (Fully Seeded in DRS)

**File:** `apps/infrastructure/persistence/seed_document_types.py`

These are pre-seeded and guaranteed to exist:

| Code | Name | Classification | Retention | Is System |
|------|------|----------------|-----------|-----------|
| `contract` | Contract | confidential | 10y | ✅ |
| `report` | Report | internal | 7y | ✅ |
| `letter` | Letter | internal | 5y | ✅ |
| `form` | Form | internal | 5y | ✅ |
| `certificate` | Certificate | public | 15y | ✅ |
| `notice` | Notice | public | 3y | ✅ |
| `invoice` | Invoice | confidential | 10y | ✅ |
| `memo` | Memo | internal | 3y | ✅ |
| `directive` | Directive | internal | 10y | ✅ |
| `minutes` | Minutes | internal | 7y | ✅ |
| `policy` | Policy | internal | 10y | ✅ |
| `other` | Other | internal | 5y | ✅ |
| `application` | Application | internal | 7y | ❌ |
| `license` | License | public | 10y | ❌ |
| `regulation` | Regulation | public | 15y | ❌ |
| `proposal` | Proposal | internal | 7y | ❌ |
| `audit_report` | Audit Report | confidential | 10y | ❌ |
| `audit_working_paper` | Audit Working Paper | confidential | 7y | ❌ |
| `agreement` | Agreement | confidential | 10y | ❌ |
| `correspondence` | Correspondence | internal | 5y | ❌ |
| `resolution` | Resolution | public | 15y | ❌ |

> **⚠️ `audit_meeting_minutes` and `audit_meeting_attendance` are NOT in the seeder.**
> These codes are used in `grc-service/apps/api/views/audit_meeting_views.py` but do not exist
> as seeded document types in DRS. They must be added manually to the seeder or via DRS admin
> before GRC's audit meeting views will work without a 400 error.

---

## 9. Full URL Map

**File:** `apps/api/urls/documents.py`

| Method | Path | View |
|--------|------|------|
| `GET/POST` | `/api/v1/documents/` | `DocumentListCreateView` |
| `GET/PUT/DELETE` | `/api/v1/documents/{id}/` | `DocumentDetailView` |
| `POST` | `/api/v1/documents/{id}/upload/` | `DocumentUploadView` |
| `GET` | `/api/v1/documents/{id}/download/` | `DocumentDownloadView` |
| `GET` | `/api/v1/documents/{id}/preview/` | `DocumentPreviewView` |
| `GET/POST` | `/api/v1/documents/{id}/versions/` | `DocumentVersionsView` |
| `POST` | `/api/v1/documents/{id}/generate-approved-stamp/` | `GenerateApprovedStampView` |
| `GET` | `/api/v1/documents/{id}/thumbnail/` | `DocumentThumbnailView` |
| `POST` | `/api/v1/documents/{id}/status/` | `DocumentStatusChangeView` |
| `GET` | `/api/v1/documents/{id}/approval-status/` | `DocumentApprovalStatusView` |
| `GET/POST` | `/api/v1/documents/{id}/shares/` | `DocumentSharesView` |
| `GET/POST` | `/api/v1/documents/{id}/comments/` | `DocumentCommentsView` |
| `GET/POST` | `/api/v1/documents/{id}/signatures/` | `DocumentSignatureListView` |
| `POST` | `/api/v1/documents/{id}/signatures/{sig_id}/upload/` | `DocumentSignatureUploadView` |
| `GET` | `/api/v1/documents/search/` | `DocumentSearchView` |
| `GET` | `/api/v1/documents/stats/` | `DocumentStatsView` |
| `POST` | `/api/v1/documents/{id}/archive/` | `DocumentArchiveView` |
| `POST` | `/api/v1/documents/{id}/restore/` | `DocumentArchiveView` |
| `POST` | `/api/v1/documents/{id}/transfer-ownership/` | `DocumentOwnershipTransferView` |

Other DRS URL modules: `folders`, `document-types`, `storage-locations`, `incoming-register`, `outgoing-register`, `reports`, `workflows`, `onlyoffice`.

---

## 10. What a Calling Service Needs

For **any service** (GRC, Corporate, etc.) to successfully call DRS on behalf of a user:

### A. The user's IAM role must have `document-service` service access

In the JWT `services` array, `"document-service"` must appear. This is set when the user's role
is registered under the `document-service` service in IAM.

The middleware blocks with **403** at step 5 if this is missing — before any view code runs.

### B. The user must have the required permission code

For `POST /api/v1/documents/` (create metadata): needs `document:document:create`
For `POST /api/v1/documents/{id}/upload/`: needs only `IsAuthenticated` (no explicit permission code)
For `GET /api/v1/documents/{id}/`: needs `document:document:read` OR ownership OR share

These permissions must be in the user's `permissions_flat` JWT claim, meaning the user's role
must have these permissions assigned in IAM under the `document-service` service.

### C. Always pass the user's JWT token

```python
auth_header = request.META.get('HTTP_AUTHORIZATION', '')
token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
client = get_document_client(auth_token=token)
```

Never hardcode a service token for user-facing operations — always forward the user's JWT.
This ensures DRS logs `created_by = user_id` correctly and access control works.

### D. Service-to-Service calls (no user JWT)

Use `X-Service-Token` header instead. Only for background tasks (Kafka consumers, scheduled jobs):

```python
client = DocumentServiceClient(auth_token=None)
# client uses X-Service-Token header automatically via generate_approved_stamp()
```

---

## 11. Response Envelope

All DRS responses are wrapped:

```json
{
  "success": true,
  "data": { ... document object ... }
}
```

The `DocumentServiceClient.create_document()` returns `data['data']` directly (already unwrapped).
So `document['id']` gives the UUID directly.

For paginated list responses:
```json
{
  "success": true,
  "data": [...],
  "pagination": { "page": 1, "page_size": 20, "total": 100 }
}
```

---

## 12. Common Failure Modes

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| DRS returns **403** `"Access denied: No permissions for document service"` | User's role has no `document-service` in IAM services | Add service assignment in IAM admin for that role |
| DRS returns **403** on `POST /api/v1/documents/` | User has service access but no `document:document:create` permission | Add permission to role in IAM |
| DRS returns **400** `"document_type invalid"` | `document_type` code doesn't exist in DRS DB | Add type in DRS admin or run seeder |
| DRS returns **401** `"Token has expired"` | JWT expired | User needs to re-login |
| DRS returns **401** `"Invalid token"` | Wrong JWT secret or malformed token | Verify `JWT_SECRET_KEY` matches across services |
| GRC returns **502** to frontend | GRC called DRS, DRS returned 4xx/5xx | Check DRS logs, usually permission or doc-type issue |
| API gateway returns **503** | Request never reached the service | Gateway routing issue or service container is down |

---

## 13. `permission_middleware.py` — Note on Previous Modification

**Status:** The file was modified in a previous session without prior discussion.
Since there is no git history, the exact diff is unknown.

**What the current code does (and why it's correct):**

The middleware's permission extraction logic reads `permissions_flat` because IAM now issues
tokens with an empty `permissions` dict (optimization to keep JWT size small). Without this
logic, no user would ever have any `document_permissions` set, and all DRS views checking
specific permission codes would fail silently.

The `service_aliases` check uses `{'document-service', 'documents', 'document'}` but only
`'document-service'` matters (that is the actual IAM-registered service name).

**Safe simplification** (if ever reverting, this is what the clean version should look like):

```python
# Check if user has access to document service
has_service = 'document-service' in (request.user_services or [])
if not request.is_superuser and not has_service:
    return JsonResponse({'error': 'Access denied: No permissions for document service'}, status=403)

# Extract document permissions from permissions_flat (IAM optimized token format)
if request.is_superuser:
    request.document_permissions = ['*']
else:
    perms_flat = request.user_permissions_flat or []
    if perms_flat == ['*']:
        request.document_permissions = ['*']
    else:
        request.document_permissions = [p for p in perms_flat if p.startswith('document:')]
```

> **Policy reminder:** Do NOT modify DRS (or any other core service's) code without explicit
> discussion and agreement. Study the code, understand it, then apply patterns in the calling
> service (e.g. GRC) as needed.

---

## 14. Corrections to `DRS_DOCUMENT_UPLOAD_REFERENCE.md`

| Section | Issue | Correction |
|---------|-------|------------|
| §5 "DRS API Endpoints" | Base URL shown as `http://document-records-service:8001` | Correct URL is `http://document-records-service:8002` |
| §6 "Document Type Codes" | `audit_meeting_minutes` and `audit_meeting_attendance` listed | These are NOT in DRS seeder — they need to be added before GRC audit meeting views work |
| §12 "Permission Summary" | Shows GRC-level permissions | These are correct GRC permissions, but remember DRS also needs `document:document:create` for the user's role |

> The rest of §1–§15 of `DRS_DOCUMENT_UPLOAD_REFERENCE.md` is **accurate and correct**
> (excluding the Working Papers and Audit Meetings sections which were user-created and
> unverified as of the time of this study).

---

## 15. DRS Core Services Map (Quick Reference)

```
apps/core/
├── entities/
│   └── document.py          ← Domain entity, business rules, status enum
├── use_cases/
│   └── document/            ← Orchestrate entity + repo operations
├── permission_middleware.py  ← JWT decode, service gate, doc_permissions extraction
├── permissions.py           ← PermissionConfigLoader (reads JSON, publishes to IAM)
├── iam_client.py            ← HTTP client to IAM (token validation, user profile)
├── config/
│   └── domain_config.py     ← URL resolution (tunnel vs localhost)
└── ...

apps/api/
├── authentication.py        ← IAMJWTAuthentication (simplejwt + shared secret)
├── permissions_jwt.py       ← CanCreateDocument, HasPermission, etc.
├── permissions.py           ← Object-level: IsDocumentOwner, HasDocumentAccess
├── views/document_views.py  ← DocumentListCreateView, DocumentUploadView, etc.
├── utils/
│   └── document_access_control.py ← can_access_document() decision tree
└── urls/documents.py        ← URL patterns

apps/infrastructure/
├── persistence/
│   ├── seed_document_types.py  ← Initial document types seeder
│   └── models.py               ← Django ORM models
└── external/                   ← External clients (if any)

config/
└── permissions/
    └── document-service.json   ← Permission definitions published to IAM
```
