# Document Records Service (DRS) — Integration Guide

> **FIMS Principle 2 — Centralised Domain Services:**
> The Document Records Service is the **sole authority** for all document storage, metadata,
> versioning, workflows, disposal, and records management across the entire FIMS platform.
> Every other service that needs document capabilities **must delegate to DRS**. It must
> never re-implement file storage, versioning, locking, QR codes, signatures, or disposal.

---

## Table of Contents

1. [What DRS Owns](#1-what-drs-owns)
2. [Architecture: Principle of Delegation](#2-architecture-principle-of-delegation)
3. [Base URL & Auth Patterns](#3-base-url--auth-patterns)
4. [Document CRUD & File Management](#4-document-crud--file-management)
5. [Document Status Lifecycle](#5-document-status-lifecycle)
6. [Versioning](#6-versioning)
7. [Locking](#7-locking)
8. [QR Code Generation](#8-qr-code-generation)
9. [Approved Stamp (PDF Overlay)](#9-approved-stamp-pdf-overlay)
10. [Digital Signatures](#10-digital-signatures)
11. [Document Sharing & Access Control](#11-document-sharing--access-control)
12. [Comments](#12-comments)
13. [Folders & File Series](#13-folders--file-series)
14. [Document Templates (OnlyOffice)](#14-document-templates-onlyoffice)
15. [Disposal (Records Disposal Management)](#15-disposal-records-disposal-management)
16. [Incoming & Outgoing Register](#16-incoming--outgoing-register)
17. [Physical Storage Locations](#17-physical-storage-locations)
18. [Document Search & Stats](#18-document-search--stats)
19. [Reports](#19-reports)
20. [Storage Monitoring](#20-storage-monitoring)
21. [Kafka Events DRS Publishes](#21-kafka-events-drs-publishes)
22. [Kafka Topics DRS Consumes](#22-kafka-topics-drs-consumes)
23. [DRS & Work Orchestration Relationship](#23-drs--work-orchestration-relationship)
24. [Permissions Reference](#24-permissions-reference)
25. [Rules Every Service Must Follow](#25-rules-every-service-must-follow)
26. [GRC-Specific Integration Patterns](#26-grc-specific-integration-patterns)
27. [Complete API Quick Reference](#27-complete-api-quick-reference)

---

## 1. What DRS Owns

DRS has **exclusive domain ownership** over:

| Domain | Examples |
|---|---|
| Document storage & file management | Upload, download, preview, file access URLs |
| Document metadata | Title, type, classification, tags, retention period, reference number |
| Document versioning | Version history, version comparison, revert to previous |
| Document locking | Lock/unlock for editing |
| Document status & lifecycle | Draft → Under Review → Approved → Active → Semi-Active → Inactive → Eligible for Disposal → Disposed |
| QR codes | Generation, embedding in PDF, signed download URLs |
| Approved stamp overlay | CIA signature + QR code overlaid on the last page of a PDF |
| Digital signatures | Request, upload, validate, per-document signature chain |
| Document sharing | Share with users, set expiry, read/write/admin permissions |
| Document comments | Threaded comment trees on any document |
| Folder/Cabinet structure | Hierarchy of cabinets → folders → series; keyword management |
| Document templates | OnlyOffice-backed editable templates |
| Disposal | Disposal form creation, DG approval, Records Dept approval, actual disposal execution |
| Incoming register | Record of documents received, routing instructions |
| Outgoing register | Record of documents dispatched, delivery confirmation |
| Physical storage locations | Building → Floor → Room → Shelf → Box mapping for physical files |
| Reports | Generate reports on documents, disposal, compliance — PDF/Excel/JSON |
| Storage monitoring | Storage quota, threshold alerts, decongestion tracking |

No other service may build or maintain any of the above.

---

## 2. Architecture: Principle of Delegation

```
GRC Service                          Document Records Service
┌──────────────────────────┐         ┌────────────────────────────────────────┐
│  Create audit report     │─POST──▶│  Create document                        │
│  output document         │         │  (owns storage, metadata, versioning)   │
│                          │         └────────────────────────────────────────┘
│  Stamp approved PDF      │─POST──▶ DRS fetches CIA signature from IAM       │
│  with CIA signature      │         DRS overlays QR + signature on PDF       │
│                          │         Returns updated document_id               │
│  Check approval status   │─GET───▶ DRS approval status endpoint             │
│                          │         Returns workflow plan_id + decision       │
└──────────────────────────┘
```

### What this means in practice

- **GRC** needs to attach an output document to an engagement → GRC calls DRS to create the document and gets back a `document_id`. GRC stores only the `document_id`.
- **GRC** needs the CIA-stamped PDF → GRC calls `POST /documents/{id}/generate-approved-stamp/`. DRS handles everything: fetches CIA's signature image from IAM, overlays it with the QR code on the PDF, saves the updated file.
- **GRC** needs to initiate a document approval → GRC calls `POST /documents/{id}/submit-for-approval/`. DRS starts the WO workflow.
- **GRC** never stores file bytes itself, never generates QR codes itself, never overlays PDFs itself.

---

## 3. Base URL & Auth Patterns

### Service URL

```
http://document-records-service:8002/api/v1/
```

Internal Docker network hostname: `document-records-service`  
Port: `8002`

All endpoints are prefixed with the sub-resource under `/api/v1/`:

| Sub-resource | Base path |
|---|---|
| Documents | `/api/v1/documents/` |
| Folders | `/api/v1/folders/` |
| Storage locations | `/api/v1/storage-locations/` |
| Disposal | `/api/v1/disposal/` |
| Incoming register | `/api/v1/incoming-register/` |
| Outgoing register | `/api/v1/outgoing-register/` |
| Document templates | `/api/v1/document-templates/` |
| Report templates | `/api/v1/report-templates/` |
| Generated reports | `/api/v1/reports/` |

### Auth Pattern 1: User JWT (normal requests from frontend or downstream service on behalf of a user)

```http
Authorization: Bearer {user_jwt_token}
```

DRS reads the JWT, extracts permissions from it via `JWTPermissionMiddleware`, and checks specific permission codes (e.g., `document:document:create`).

### Auth Pattern 2: Service-to-Service (no user context, background jobs, Celery tasks)

```http
X-Service-Token: {SERVICE_TO_SERVICE_TOKEN}
```

Set the same shared secret in both services:
```
SERVICE_TO_SERVICE_TOKEN=fims-service-secret-token   # in env
```

DRS's `IsAuthenticatedOrServiceToken` permission class accepts either a valid user JWT **or** a matching `X-Service-Token`. Use the service token when calling DRS from Celery Beat tasks or Kafka consumers where there is no user session.

### Auth Pattern 3: Signed Document URLs (for ONLYOFFICE and QR downloads)

Certain download/preview endpoints accept a short-lived JWT `?token=` query parameter:

```
GET /api/v1/documents/{id}/download/?token={signed_jwt}
```

These signed URLs are generated by DRS and have a configurable TTL (default: 3600 seconds). The signing key is `ONLYOFFICE_JWT_SECRET` in DRS settings. **Your service does not need to generate these** — DRS generates and returns them when needed.

---

## 4. Document CRUD & File Management

### 4.1 Create Document

```http
POST /api/v1/documents/
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Audit Report FY2025/26 — FCC",
  "description": "Final audit report following CIA review",
  "document_type": "report",
  "classification": "confidential",
  "tags": ["audit", "fy2025-26", "fcc"],
  "record_type": "non_permanent",
  "retention_period": 7,
  "metadata": {
    "entity_type": "engagement",
    "entity_id": "engagement-uuid",
    "reference_number": "RBIENG-001"
  }
}
```

**`classification` values:** `open`, `confidential`  
**`record_type` values:** `permanent`, `non_permanent`  
**`document_type`:** any string — configurable via the DRS `DocumentType` database model (not hard-coded)

**Response:**
```json
{
  "data": {
    "id": "document-uuid",
    "reference_number": "DOC-2026-001",
    "title": "Audit Report FY2025/26 — FCC",
    "status": "draft",
    "version": 1,
    "classification": "confidential",
    "record_type": "non_permanent",
    "created_by": "user-uuid",
    "created_at": "2026-03-07T10:00:00Z"
  }
}
```

**Your service stores only the returned `id` (UUID).**

### 4.2 Upload File to Document

```http
POST /api/v1/documents/{document_id}/upload/
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: <binary>
```

Max upload size: **50 MB** (configurable via `MAX_UPLOAD_SIZE`).  
Allowed extensions: `doc, docx, pdf, txt, xlsx, xls, csv, jpeg, jpg, png, gif, epub`.

### 4.3 Download File

```http
GET /api/v1/documents/{document_id}/download/
Authorization: Bearer {token}
```

Returns: `Content-Disposition: attachment; filename="{filename}"` + binary stream.

For signed-URL download (no auth header needed, used by frontends):
```
GET /api/v1/documents/{document_id}/download/?token={signed_jwt}
```

### 4.4 Preview

```http
GET /api/v1/documents/{document_id}/preview/
Authorization: Bearer {token}
```

Supported preview types: PDF, PNG, JPG, JPEG, GIF, SVG, TXT, JSON, CSV, XML.  
For previewing other file types inline (Word, Excel), use the OnlyOffice view (see Section 14).

### 4.5 Get Document Detail

```http
GET /api/v1/documents/{document_id}/
Authorization: Bearer {token}
```

### 4.6 Update Document Metadata

```http
PATCH /api/v1/documents/{document_id}/
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Updated title",
  "tags": ["audit", "updated"],
  "metadata": {"custom_key": "value"}
}
```

> **Important:** `metadata` is a JSON field — you can store your service's context in it (e.g., `entity_id`, `entity_type`). DRS never validates or interprets this field.

### 4.7 Delete Document

```http
DELETE /api/v1/documents/{document_id}/
Authorization: Bearer {token}
```

Only `draft` documents that are not locked and not archived can be deleted.

### 4.8 Permanent Delete (Disposed Documents Only)

```http
DELETE /api/v1/documents/{document_id}/permanent/
Authorization: Bearer {token}
```

Permanently removes the file and record from DRS. Only allowed on documents with `status = disposed`.

### 4.9 Thumbnail

```http
GET /api/v1/documents/{document_id}/thumbnail/
Authorization: Bearer {token}
```

Returns: a small PNG thumbnail (generated from first page for PDFs, or resized image for image files).

---

## 5. Document Status Lifecycle

DRS manages the full records management lifecycle. Valid status transitions:

```
draft ──▶ under_review ──▶ approved  ──▶ active ──▶ semi_active ──▶ inactive
  ▲            │                │                                      │
  └────────────┘ (rejected)     └─▶ rejected                          │
                                                                       ▼
                                          eligible_for_decongestion ◀──┘
                                                     │
                                                 archived
                                                     │
                                              disposed (permanent)
```

### Change Status

```http
POST /api/v1/documents/{document_id}/status/
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "active",
  "comment": "Document activated after approval"
}
```

### Archive / Restore

```http
POST /api/v1/documents/{document_id}/archive/
POST /api/v1/documents/{document_id}/restore/
```

### Mark Eligible for Disposal

```http
POST /api/v1/documents/{document_id}/mark-eligible-for-disposal/
Authorization: Bearer {token}
```

Sets status to `eligible_for_decongestion`. This is a prerequisite for creating a disposal form.

---

## 6. Versioning

DRS maintains a full version history per document. When a new file is uploaded or metadata changes, a new version is created automatically.

### List Versions

```http
GET /api/v1/documents/{document_id}/versions/
Authorization: Bearer {token}
```

### Version History (detailed)

```http
GET /api/v1/documents/{document_id}/version-history/
Authorization: Bearer {token}
```

### Get Specific Version

```http
GET /api/v1/documents/{document_id}/versions/{version_number}/
Authorization: Bearer {token}
```

### Compare Versions

```http
GET /api/v1/documents/{document_id}/compare/?version_a=1&version_b=3
Authorization: Bearer {token}
```

Returns a field-by-field diff showing what changed between two versions.

### Revert to Previous Version

```http
POST /api/v1/documents/{document_id}/revert/
Authorization: Bearer {token}
Content-Type: application/json

{
  "target_version": 2,
  "change_summary": "Reverting to v2 — v3 contained errors"
}
```

### Revert Specific Fields Only

```http
POST /api/v1/documents/{document_id}/revert-fields/
Authorization: Bearer {token}
Content-Type: application/json

{
  "target_version": 2,
  "fields": ["title", "description"]
}
```

---

## 7. Locking

DRS allows a user to lock a document exclusively for editing. Other users cannot edit while the lock is held.

### Lock

```http
POST /api/v1/documents/{document_id}/lock/
Authorization: Bearer {token}
```

### Unlock

```http
DELETE /api/v1/documents/{document_id}/unlock/
Authorization: Bearer {token}
```

Business rules enforced by DRS:
- Only the user who holds the lock can unlock it (or an admin)
- Locked documents cannot be edited by anyone else
- Documents in `closed` or `approved` status cannot be locked
- Disposed or archived documents cannot be locked

---

## 8. QR Code Generation

Every document in DRS can have a QR code generated. The QR code encodes a signed download URL.

### Generate / Get QR Code

```http
GET /api/v1/documents/{document_id}/qr/
Authorization: Bearer {token}
```

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `format` | `png` \| `svg` | `png` | Output image format |
| `size` | int | `10` | QR box size |
| `border` | int | `4` | Quiet zone border |
| `error_correction` | `L` \| `M` \| `Q` \| `H` | `M` | Error correction level |
| `include_base64` | `true` \| `false` | `false` | Return base64 data URI instead of binary |

**PNG response:** `Content-Type: image/png` + binary  
**SVG response:** `Content-Type: image/svg+xml`  
**Base64 response:**

```json
{
  "data": {
    "document_id": "document-uuid",
    "qr_code": "data:image/png;base64,iVBORw0KGgo...",
    "format": "png",
    "download_url": "https://drs.fcc.go.tz/api/v1/documents/uuid/download/?token=..."
  }
}
```

The QR code, when scanned, opens the signed download URL — no login required.

### QR Code Data Storage

DRS automatically saves `qr_code_path` and `qr_code_data` fields on the `Document` record when a QR code is first generated. Subsequent calls return the saved QR unless `regenerate=true` is passed.

---

## 9. Approved Stamp (PDF Overlay)

When a document is formally approved, other services (primarily GRC) can request DRS to stamp the final PDF with the approver's signature image (fetched from IAM) and the document's QR code. This is overlaid on the **last page** of the PDF.

```
POST /api/v1/documents/{document_id}/generate-approved-stamp/
```

**Auth:** Standard JWT **or** `X-Service-Token` (service-to-service).

**Request body:**

```json
POST /api/v1/documents/{document_id}/generate-approved-stamp/
X-Service-Token: fims-service-secret-token
Content-Type: application/json

{
  "approver_id": "cia-user-uuid",
  "stamp_comment": "Approved by CIA on 2026-03-07"
}
```

**What DRS does internally:**

1. Fetches the document's current file from storage
2. Generates the document QR code (Section 8)
3. Fetches the approver's signature image URL from IAM (`/api/v1/users/{approver_id}/signature/`)
4. Opens the PDF using PyPDF2 + ReportLab
5. Overlays the QR code in the **bottom-left** corner (30×30 mm, 15 mm margin)
6. Overlays the signature image in the **bottom-right** corner (65×22 mm)
7. Draws a thin divider line above the stamp area
8. Saves the new stamped PDF, replacing `file_path` on the same `document_id`
9. Returns the **same** `document_id` — all existing download URLs still work

**Response:**

```json
{
  "data": {
    "document_id": "document-uuid",
    "stamped": true,
    "file_path": "documents/stamped/audit-report-stamped.pdf",
    "approver_id": "cia-user-uuid",
    "stamped_at": "2026-03-07T10:30:00Z"
  }
}
```

**Dependencies installed in DRS:** `PyPDF2`, `reportlab`, `Pillow`, `qrcode`.

**Edge cases:**
- If IAM's signature endpoint returns no image, DRS stamps the QR only (non-blocking — it does **not** fail)
- If the document is not a PDF, DRS returns `HTTP 400`
- If `approver_id` is omitted, no signature is placed (QR code only)

---

## 10. Digital Signatures

DRS maintains a per-document signature chain (separate from the approved stamp overlay). A signature represents a formal digital sign-off by a specific user.

### Request a Signature

```http
POST /api/v1/documents/{document_id}/signatures/request/
Authorization: Bearer {token}
Content-Type: application/json

{
  "signer_id": "user-uuid",
  "signature_method": "digital",
  "signature_position": {
    "page": 1,
    "x": 100,
    "y": 200,
    "width": 150,
    "height": 50
  },
  "workflow_id": "optional-workflow-uuid",
  "workflow_step_key": "optional-step"
}
```

**`signature_method` values:** `digital`, `drawn`, `image`

### Upload Signed Signature

```http
POST /api/v1/documents/{document_id}/signatures/{signature_id}/upload/
Authorization: Bearer {token}
Content-Type: application/json

{
  "signature_data": "base64-encoded-signature-image",
  "signature_method": "drawn",
  "signature_position": {"page": 1, "x": 100, "y": 200, "width": 150, "height": 50}
}
```

### Validate Signature

```http
POST /api/v1/documents/{document_id}/signatures/{signature_id}/validate/
Authorization: Bearer {token}
```

Returns `{"is_valid": true, "validated_at": "..."}`.

### List Signatures

```http
GET /api/v1/documents/{document_id}/signatures/
Authorization: Bearer {token}
```

### My Signature Queue

```http
GET /api/v1/documents/signatures/my/
Authorization: Bearer {token}
```

Returns documents pending the current user's signature.

---

## 11. Document Sharing & Access Control

### Share a Document

```http
POST /api/v1/documents/{document_id}/shares/
Authorization: Bearer {token}
Content-Type: application/json

{
  "shared_with": "target-user-uuid",
  "permission": "read",
  "expires_at": "2026-06-30T23:59:59Z",
  "message": "Please review this engagement notification"
}
```

**`permission` values:** `read`, `write`, `admin`

### List Shares for a Document

```http
GET /api/v1/documents/{document_id}/shares/
Authorization: Bearer {token}
```

### My Shared Documents (documents I shared)

```http
GET /api/v1/documents/document-shares/my-shares/
Authorization: Bearer {token}
```

### Shared With Me

```http
GET /api/v1/documents/document-shares/shared-with-me/
Authorization: Bearer {token}
```

### Update / Revoke a Share

```http
PATCH /api/v1/documents/document-shares/{share_id}/
DELETE /api/v1/documents/document-shares/{share_id}/
```

### Bulk Share

```http
POST /api/v1/documents/document-shares/bulk/
Content-Type: application/json

{
  "document_ids": ["uuid1", "uuid2"],
  "shared_with": "user-uuid",
  "permission": "read"
}
```

### Folder Access Requests

```http
POST /api/v1/access-requests/
GET  /api/v1/access-requests/
```

---

## 12. Comments

### Add Comment

```http
POST /api/v1/documents/{document_id}/comments/
Authorization: Bearer {token}
Content-Type: application/json

{
  "content": "Please update section 3.2 with the revised risk matrix",
  "author_id": "user-uuid"
}
```

### Reply to a Comment

```http
POST /api/v1/documents/document-comments/{comment_id}/reply/
Authorization: Bearer {token}
Content-Type: application/json

{
  "content": "Updated. Please re-review.",
  "author_id": "user-uuid"
}
```

### Resolve a Comment

```http
POST /api/v1/documents/document-comments/{comment_id}/resolve/
Authorization: Bearer {token}
```

### List Comments

```http
GET /api/v1/documents/{document_id}/comments/
Authorization: Bearer {token}
```

---

## 13. Folders & File Series

DRS organises documents in a hierarchy: **Cabinet → Folder → File Series**.

### ViewSet (DefaultRouter)

All under `/api/v1/folders/`:

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `folders/` | List or create folders |
| `GET/PATCH/DELETE` | `folders/{id}/` | Detail, update, or delete folder |
| `GET/POST` | `folders/file-series/` | List or create file series |
| `GET/PATCH/DELETE` | `folders/file-series/{id}/` | File series detail |
| `GET/POST` | `folders/keywords/` | Manage keywords |
| `GET/PATCH/DELETE` | `folders/keywords/{id}/` | Keyword detail |

---

## 14. Document Templates (OnlyOffice)

DRS integrates with **ONLYOFFICE Document Server** for in-browser collaborative editing.  
OnlyOffice is a separate container (`fims-onlyoffice`) running on port **8090**.

### Template ViewSet (DefaultRouter)

All under `/api/v1/document-templates/`:

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `document-templates/` | List or create templates |
| `GET/PATCH/DELETE` | `document-templates/{id}/` | Detail, update, delete template |

### OnlyOffice Edit Session

To open a document for inline editing in the browser:

```http
GET /api/v1/documents/onlyoffice/config/{document_id}/
Authorization: Bearer {token}
```

Returns the full OnlyOffice editor config JSON (including a signed `token` for ONLYOFFICE's JWT verification), which your frontend passes to the ONLYOFFICE JS SDK:

```javascript
new DocsAPI.DocEditor("editor-container", onlyofficeConfig);
```

DRS handles all ONLYOFFICE callbacks automatically (`POST /api/v1/documents/onlyoffice/callback/`). When the user saves, ONLYOFFICE calls this endpoint and DRS creates a new document version.

### Template Workflows

Workflow associations for document templates:

```http
GET /api/v1/template-workflows/
POST /api/v1/template-workflows/
GET/PATCH/DELETE /api/v1/template-workflows/{id}/
```

---

## 15. Disposal (Records Disposal Management)

DRS owns the complete disposal lifecycle for records management. The typical flow is:

```
Mark documents eligible → Create disposal form → DG approves → Records Dept approves → Execute disposal
```

For regular disposal forms, DRS internally delegates the approval steps to **Work Orchestration** (see Section 23). DRS also provides direct HTTP approval endpoints for simpler flows.

### 15.1 Mark Document Eligible for Disposal

```http
POST /api/v1/documents/{document_id}/mark-eligible-for-disposal/
Authorization: Bearer {token}
```

Sets `status = eligible_for_decongestion`.

### 15.2 List Eligible Documents

```http
GET /api/v1/disposal/eligible-documents/
Authorization: Bearer {token}
```

Returns all documents in `eligible_for_decongestion` status.

### 15.3 Create Disposal Form

```http
POST /api/v1/disposal/
Authorization: Bearer {token}
Content-Type: application/json

{
  "document_ids": ["doc-uuid-1", "doc-uuid-2"],
  "disposal_reason": "Retention period exceeded for non-permanent records",
  "proposed_disposal_method": "shredding",
  "submitted_by": "user-uuid"
}
```

**Response includes `form_id` (UUID)** which you store for subsequent approval tracking.

### 15.4 DG Approval (direct HTTP — for simpler flows without WO)

```http
POST /api/v1/disposal/{form_id}/dg-approve/
Authorization: Bearer {token}
Content-Type: application/json

{
  "approved": true,
  "comments": "Approved for disposal"
}
```

Requires `document:disposal:dg_approve` permission.

### 15.5 Records Department Approval

```http
POST /api/v1/disposal/{form_id}/records-dept-approve/
Authorization: Bearer {token}
Content-Type: application/json

{
  "approved": true,
  "disposal_method": "shredding",
  "comments": "Confirmed all documents are non-permanent, safe to dispose"
}
```

Requires `document:disposal:records_dept_approve` permission.

### 15.6 Execute Disposal

```http
POST /api/v1/disposal/{form_id}/execute-disposal/
Authorization: Bearer {token}
Content-Type: application/json

{
  "disposal_method": "shredding",
  "certificate_number": "DISPOSE-CERT-001",
  "executor_id": "user-uuid"
}
```

Requires `document:disposal:execute` permission.

After execution, DRS:
- Sets each document's `status = disposed`, `is_disposed = true`, `disposed_at = now()`
- Publishes `DOCUMENTS_DISPOSED` event to Kafka
- Keeps the metadata record but the file is deleted from storage

### 15.7 Disposal via Work Orchestration (recommended for full audit trail)

When the disposal form's workflow type is `document_disposal`, DRS starts a WO plan for the approval route. When WO returns `final_decision = approved`, DRS automatically executes the disposal via its `WorkflowEventConsumer`.

See [Section 23](#23-drs--work-orchestration-relationship) for the complete disposal-via-WO pattern.

### 15.8 Disposal Stats

```http
GET /api/v1/disposal/stats/
Authorization: Bearer {token}
```

### 15.9 Disposal Form Status

```http
GET /api/v1/disposal/{form_id}/status/
Authorization: Bearer {token}
```

---

## 16. Incoming & Outgoing Register

### 16.1 Incoming Register

Records documents received from external parties.

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `incoming-register/` | List or create register entries |
| `GET/PATCH` | `incoming-register/{id}/` | Detail or update |
| `POST` | `incoming-register/{id}/route/` | Route to a user |
| `GET` | `incoming-register/my-inbox/` | My inbox (routed to me) |
| `GET` | `incoming-register/stats/` | Stats |
| `POST` | `incoming-register/{id}/upload/` | Attach file |
| `GET` | `incoming-register/{id}/files/` | List attached files |

**Create entry:**

```json
POST /api/v1/incoming-register/
{
  "reference_number": "INC-2026-001",
  "sender": "Ministry of Finance",
  "subject": "Budget allocation FY2026",
  "received_by": "user-uuid",
  "priority": "high",
  "received_at": "2026-03-07T09:00:00Z"
}
```

**Route to user:**

```json
POST /api/v1/incoming-register/{id}/route/
{
  "to_user_id": "user-uuid",
  "instructions": "Please review and prepare a response by March 14"
}
```

### 16.2 Outgoing Register

Records documents dispatched to external parties.

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `outgoing-register/` | List or create |
| `GET/PATCH` | `outgoing-register/{id}/` | Detail or update |
| `POST` | `outgoing-register/{id}/confirm-delivery/` | Mark as delivered |
| `GET` | `outgoing-register/pending/` | Pending deliveries |
| `GET` | `outgoing-register/stats/` | Stats |
| `POST` | `outgoing-register/{id}/upload/` | Attach file |
| `GET` | `outgoing-register/{id}/files/` | List attached files |

**Create entry:**

```json
POST /api/v1/outgoing-register/
{
  "reference_number": "OUT-2026-001",
  "recipient": "GRC Department",
  "subject": "Audit Engagement Plan",
  "dispatched_by": "user-uuid",
  "dispatch_method": "email",
  "dispatched_at": "2026-03-07T10:00:00Z"
}
```

---

## 17. Physical Storage Locations

Maps the physical location of hard-copy documents in storage rooms.

### Storage Location ViewSet

Under `/api/v1/storage-locations/`:

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `storage-locations/` | List or create storage locations |
| `GET/PATCH/DELETE` | `storage-locations/{id}/` | Detail, update, delete |
| `GET/POST` | `storage-locations/floors/` | List or create floors |
| `GET/PATCH/DELETE` | `storage-locations/floors/{id}/` | Floor detail |

### Link a Document to Physical Storage

```http
POST /api/v1/documents/{document_id}/physical-storage/create/
Authorization: Bearer {token}
Content-Type: application/json

{
  "storage_location_id": "location-uuid",
  "shelf": "B-3",
  "box_number": "BOX-042",
  "notes": "Physical file in archive room B"
}
```

### Get Physical Location

```http
GET /api/v1/documents/{document_id}/physical-storage/
Authorization: Bearer {token}
```

---

## 18. Document Search & Stats

### Full-Text Search

```http
GET /api/v1/documents/search/?q=audit+report&document_type=report&status=approved&classification=confidential
Authorization: Bearer {token}
```

**Filter parameters:**

| Param | Description |
|---|---|
| `q` / `search` | Full-text search across title, description, tags |
| `document_type` | Filter by document type string |
| `status` | Filter by status value |
| `classification` | `open` or `confidential` |
| `is_archived` | `true` / `false` |
| `include_archived` | Include archived documents |
| `page` | Page number (default: 1) |
| `page_size` | Results per page (default: 20) |

### Search Suggestions (Autocomplete)

```http
GET /api/v1/documents/search/suggestions/?q=audit
Authorization: Bearer {token}
```

### Document Stats

```http
GET /api/v1/documents/stats/
Authorization: Bearer {token}
```

Returns counts by status, type, classification.

### Storage Stats

```http
GET /api/v1/documents/storage/stats/
Authorization: Bearer {token}
```

Returns total bytes used, file count, average file size.

---

## 19. Reports

DRS generates cross-document compliance and management reports.

### Report Templates

```http
GET/POST /api/v1/report-templates/
GET/PATCH/DELETE /api/v1/report-templates/{id}/
```

### Generate Report

```http
POST /api/v1/reports/generate/
Authorization: Bearer {token}
Content-Type: application/json

{
  "template_id": "template-uuid",
  "parameters": {
    "start_date": "2026-01-01",
    "end_date": "2026-03-31",
    "document_type": "report",
    "status": "approved"
  },
  "format": "pdf"
}
```

**`format` values:** `pdf`, `excel`, `json`, `csv`

### List Generated Reports

```http
GET /api/v1/reports/
Authorization: Bearer {token}
```

### Download Report

```http
GET /api/v1/reports/{report_id}/download/
Authorization: Bearer {token}
```

Returns a `Content-Disposition: attachment` file response.

### Report Summary

```http
GET /api/v1/reports/summary/
Authorization: Bearer {token}
```

---

## 20. Storage Monitoring

### Storage Monitoring Stats

```http
GET /api/v1/documents/storage/monitoring/stats/
Authorization: Bearer {token}
```

Returns current usage vs. configured threshold (default: 80%).

### Threshold Alerts

```http
GET  /api/v1/documents/storage/monitoring/alerts/
POST /api/v1/documents/storage/monitoring/alerts/{alert_id}/resolve/
Authorization: Bearer {token}
```

---

## 21. Kafka Events DRS Publishes

DRS publishes domain events to Kafka. All events follow this base schema:

```json
{
  "event_id": "uuid",
  "event_type": "DOCUMENT_CREATED",
  "timestamp": "2026-03-07T10:00:00Z",
  "service_name": "document-records-service",
  "aggregate_id": "document-uuid",
  "user_id": "user-uuid",
  "metadata": {},
  "data": { ...event-specific fields... }
}
```

**Kafka topic formula:**

```
fims.documents.{event_type.lower().replace('_', '.')}
```

Examples:
- `DOCUMENT_CREATED` → `fims.documents.document.created`
- `DOCUMENT_APPROVED` → `fims.documents.document.approved`
- `DOCUMENTS_DISPOSED` → `fims.documents.documents.disposed`

### All Events DRS Publishes

#### Document Events

| `event_type` | Kafka Topic | Trigger | Key `data` Fields |
|---|---|---|---|
| `DOCUMENT_CREATED` | `fims.documents.document.created` | Document created | `document_id`, `title`, `document_type`, `classification`, `created_by` |
| `DOCUMENT_UPDATED` | `fims.documents.document.updated` | Metadata updated | `document_id`, `title`, `updated_by`, `changes` |
| `DOCUMENT_DELETED` | `fims.documents.document.deleted` | Document deleted | `document_id`, `title`, `deleted_by`, `reason` |
| `DOCUMENT_ARCHIVED` | `fims.documents.document.archived` | Archived | `document_id`, `title`, `archived_by` |
| `DOCUMENT_RESTORED` | `fims.documents.document.restored` | Restored from archive | `document_id`, `title`, `restored_by` |
| `DOCUMENT_VERSION_CREATED` | `fims.documents.document.version.created` | New version created | `document_id`, `version_number`, `version_id`, `created_by`, `changes_summary` |
| `DOCUMENT_LOCKED` | `fims.documents.document.locked` | Locked for editing | `document_id`, `title`, `locked_by` |
| `DOCUMENT_UNLOCKED` | `fims.documents.document.unlocked` | Unlocked | `document_id`, `title`, `unlocked_by` |
| `DOCUMENT_FILE_UPLOADED` | `fims.documents.document.file.uploaded` | File uploaded | `document_id`, `file_name`, `file_size`, `file_type`, `uploaded_by`, `storage_path` |

#### Workflow / Approval Events

| `event_type` | Kafka Topic | Trigger | Key `data` Fields |
|---|---|---|---|
| `DOCUMENT_SUBMITTED_FOR_REVIEW` | `fims.documents.document.submitted.for.review` | Submitted for approval | `document_id`, `title`, `submitted_by`, `workflow_type` |
| `DOCUMENT_APPROVED` | `fims.documents.document.approved` | Approved by approver | `document_id`, `title`, `approver_id`, `approval_level`, `workflow_type`, `comments` |
| `DOCUMENT_REJECTED` | `fims.documents.document.rejected` | Rejected by approver | `document_id`, `title`, `approver_id`, `approval_level`, `workflow_type`, `reason` |
| `APPROVAL_COMPLETED` | `fims.documents.approval.completed` | All approvals done | `document_id`, `title`, `workflow_type`, `final_status` (`approved`/`rejected`), `total_approvals` |

#### Disposal Events

| `event_type` | Kafka Topic | Trigger | Key `data` Fields |
|---|---|---|---|
| `DISPOSAL_FORM_CREATED` | `fims.documents.disposal.form.created` | Disposal form created | `form_id`, `form_number`, `submitted_by`, `disposal_reason`, `document_count` |
| `DISPOSAL_FORM_DG_APPROVED` | `fims.documents.disposal.form.dg.approved` | DG approves | `form_id`, `form_number`, `approved_by`, `comments` |
| `DISPOSAL_FORM_DG_REJECTED` | `fims.documents.disposal.form.dg.rejected` | DG rejects | `form_id`, `form_number`, `rejected_by`, `reason` |
| `DISPOSAL_FORM_RECORDS_DEPT_APPROVED` | `fims.documents.disposal.form.records.dept.approved` | Records Dept approves | `form_id`, `form_number`, `approved_by`, `disposal_method`, `comments` |
| `DISPOSAL_FORM_RECORDS_DEPT_REJECTED` | `fims.documents.disposal.form.records.dept.rejected` | Records Dept rejects | `form_id`, `form_number`, `rejected_by`, `reason` |
| `DOCUMENTS_DISPOSED` | `fims.documents.documents.disposed` | Disposal executed | `form_id`, `form_number`, `document_ids`, `document_count`, `disposal_method`, `disposed_by` |

#### Register Events

| `event_type` | Kafka Topic | Key `data` Fields |
|---|---|---|
| `INCOMING_DOCUMENT_REGISTERED` | `fims.documents.incoming.document.registered` | `register_id`, `document_id`, `reference_number`, `sender`, `received_by`, `priority` |
| `DOCUMENT_ROUTED` | `fims.documents.document.routed` | `register_id`, `document_id`, `from_user_id`, `to_user_id`, `instructions` |
| `OUTGOING_DOCUMENT_DISPATCHED` | `fims.documents.outgoing.document.dispatched` | `register_id`, `document_id`, `recipient`, `dispatched_by`, `dispatch_method` |
| `DOCUMENT_DELIVERY_CONFIRMED` | `fims.documents.document.delivery.confirmed` | `register_id`, `document_id`, `recipient` |

#### Permission Registration (startup)

| Topic | Trigger |
|---|---|
| `service.permission.registry` | On DRS startup — registers all DRS permission codes with IAM |

---

## 22. Kafka Topics DRS Consumes

DRS subscribes to these topics (consumer group: `document-records-consumer`):

| Topic | What DRS Does When Consuming |
|---|---|
| `workflow-events` | Routes to `WorkflowEventConsumer` — handles `*.workflow.completed` events to auto-execute disposal or update document approval status |
| `fims.iam.user.updated` | Future: update cached user data |
| `fims.work.task.created` | Future: attach documents to tasks |

### How DRS Handles Workflow Completions from WO

When WO publishes a `{type}.workflow.completed` event, DRS routes based on `workflow_type`:

| `workflow_type` | What DRS Does |
|---|---|
| `disposal` | Executes the disposal (`ExecuteDisposalUseCase`) using `result_data.disposal_form_id` |
| `approval` | Updates `document.status` to `approved` or `rejected` |
| `management` | Same as `approval` |
| `commission` | Same as `approval` |

> This means your service **does not need to tell DRS** when an approval is done — DRS automatically reacts to WO's completion event. GRC only needs to start the WO plan and let DRS handle the outcome.

---

## 23. DRS & Work Orchestration Relationship

DRS uses WO for **formal approval workflows** (disposal approval, document management approval). DRS is a consuming service with respect to WO for these workflows.

### How DRS Starts a WO Plan

DRS uses `WorkOrchestrationClient` (HTTP `POST /plans/`) internally:

```python
# From apps/core/workflow/orchestration_client.py
client = WorkOrchestrationClient()
plan = client.create_plan(
    workflow_type="document_disposal",
    template_id=None,      # WO resolves template by workflow_type + template_code
    context={
        "entity_type": "disposal_form",
        "entity_id": str(disposal_form_id),
        "reference_number": form.form_number,
        "template_code": "document_disposal.approval",
        "disposal_form_id": str(disposal_form_id),
    },
    assignees={"dg_reviewer": [str(dg_user_id)]},
)
```

Auth: DRS passes `X-Service-Token` header to WO.

### What Other Services Need to Know

- **When GRC creates a document in DRS and starts an approval** (e.g., `submit-for-approval/`), DRS internally starts the WO plan. GRC does not call WO directly for DRS document approvals.
- **When the WO plan completes**, WO publishes `document.workflow.completed` to `workflow-events`. DRS consumes this and updates the document status. GRC reacts by subsequently reading the DRS document's updated status via `GET /documents/{id}/`.
- **GRC can also directly listen** to `fims.documents.document.approved` / `fims.documents.document.rejected` events on Kafka if it needs immediate notification.

---

## 24. Permissions Reference

DRS uses a declarative permission system loaded from `config/permissions/document-service.json` and registered to IAM at startup. All permissions use the format:

```
document:{resource_type}:{action}
```

### Key Permission Codes

| Permission Code | Who Needs It |
|---|---|
| `document:document:read` | Any user reading documents |
| `document:document:create` | Any service/user creating documents |
| `document:document:update` | Editing document metadata or file |
| `document:document:delete` | Deleting draft documents |
| `document:document:admin` | Full document admin |
| `document:disposal:create` | Create disposal forms |
| `document:disposal:dg_approve` | Approve disposal as DG |
| `document:disposal:records_dept_approve` | Approve disposal as Records Dept |
| `document:disposal:execute` | Execute disposal |
| `document:disposal:read` | View disposal forms |
| `document:disposal:view_eligible` | View eligible documents list |
| `document:signature:read` | View signatures |
| `document:signature:create` | Request signatures |
| `document:signature:upload` | Upload signed signature data |
| `document:signature:validate` | Validate signatures |
| `document:report:read` | View generated reports |
| `document:report:create` | Generate reports |
| `document:report:delete` | Delete reports |
| `document:report_template:read` | View report templates |
| `document:report_template:create` | Create report templates |
| `document:report_template:update` | Update report templates |
| `document:report_template:delete` | Delete report templates |

> The **admin permission `document:system:admin`** bypasses all individual checks — useful for superuser / service accounts. The `CanAdminDocumentSystem` class grants access to everything.

---

## 25. Rules Every Service Must Follow

These are **mandatory constraints** derived from FIMS Principle 1 (Domain Ownership Without Duplication) and Principle 2 (Centralised Domain Services):

### ❌ Never store document files yourself

```python
# WRONG — GRC stores the file itself
class AuditReport(models.Model):
    report_file = models.FileField(upload_to='audit_reports/')
```

```python
# CORRECT — GRC stores only the DRS document_id
class AuditReport(models.Model):
    drs_document_id = models.UUIDField(null=True, blank=True)
```

### ❌ Never implement versioning yourself

```python
# WRONG
class AuditReportVersion(models.Model):
    report = models.ForeignKey(AuditReport, on_delete=models.CASCADE)
    version_number = models.IntegerField()
    file = models.FileField()
```

```python
# CORRECT — call DRS
POST /api/v1/documents/{id}/new-version/
```

### ❌ Never generate QR codes yourself

```python
# WRONG
import qrcode
qr = qrcode.make("https://...")
```

```python
# CORRECT — call DRS
GET /api/v1/documents/{document_id}/qr/?format=png
```

### ❌ Never overlay PDFs or add stamps yourself

```python
# WRONG
from PyPDF2 import PdfWriter
# ... manual overlay logic in GRC
```

```python
# CORRECT — delegate to DRS
POST /api/v1/documents/{document_id}/generate-approved-stamp/
X-Service-Token: {token}
{"approver_id": "cia-uuid"}
```

### ❌ Never implement a disposal process yourself

If your service tracks records with retention periods, the **disposal** is DRS's domain. Your service marks records as eligible, then DRS handles the disposal form, approvals, and execution.

### ❌ Never validate user permissions against DRS documents yourself

DRS returns `HTTP 403` with `{"error": "Permission denied"}` if the requesting user lacks the required permission. Your service does not need to pre-check DRS permissions.

### ✅ What your service IS responsible for

| Responsibility | Service |
|---|---|
| Store `drs_document_id` on your entity | Your service |
| Call DRS to create/upload/download documents | Your service |
| Decide when to initiate `submit-for-approval/` | Your service |
| React to `fims.documents.document.approved` Kafka event | Your service (optional) |
| Present document download links to users | Your service (frontend) |
| Store your entity's context in `metadata` when creating a document | Your service |

---

## 26. GRC-Specific Integration Patterns

### Pattern 1: Attach an output document to an engagement

```python
# In GRC engagement completion or report generation flow

import requests

def attach_document_to_engagement(engagement_id, title, file_bytes, file_name, cia_user_id, jwt_token):
    DRS_BASE = "http://document-records-service:8002/api/v1"
    headers = {"Authorization": f"Bearer {jwt_token}"}

    # 1. Create document record
    doc_resp = requests.post(f"{DRS_BASE}/documents/", headers=headers, json={
        "title": title,
        "document_type": "report",
        "classification": "confidential",
        "record_type": "non_permanent",
        "metadata": {
            "entity_type": "engagement",
            "entity_id": str(engagement_id),
        },
    })
    document_id = doc_resp.json()["data"]["id"]

    # 2. Upload the file
    requests.post(
        f"{DRS_BASE}/documents/{document_id}/upload/",
        headers={"Authorization": f"Bearer {jwt_token}"},
        files={"file": (file_name, file_bytes, "application/pdf")},
    )

    # 3. Store only the document_id in GRC's DB
    Engagement.objects.filter(id=engagement_id).update(drs_report_document_id=document_id)
    return document_id
```

### Pattern 2: Generate the CIA-approved stamp on a PDF

Called when GRC marks an audit report as CIA-approved and the final PDF needs to carry the stamp.

```python
def generate_approved_stamp(document_id, cia_user_id):
    DRS_BASE = "http://document-records-service:8002/api/v1"
    SERVICE_TOKEN = settings.SERVICE_TO_SERVICE_TOKEN

    resp = requests.post(
        f"{DRS_BASE}/documents/{document_id}/generate-approved-stamp/",
        headers={
            "X-Service-Token": SERVICE_TOKEN,
            "Content-Type": "application/json",
        },
        json={"approver_id": str(cia_user_id)},
    )
    resp.raise_for_status()
    return resp.json()["data"]  # {document_id, stamped, stamped_at}
```

> After this call, the document at `document_id` now serves the stamped PDF — all existing download URLs are automatically updated. No URL change required.

### Pattern 3: Initiate document approval via DRS

```python
def submit_document_for_approval(document_id, workflow_type, jwt_token):
    DRS_BASE = "http://document-records-service:8002/api/v1"

    resp = requests.post(
        f"{DRS_BASE}/documents/{document_id}/submit-for-approval/",
        headers={"Authorization": f"Bearer {jwt_token}"},
        json={"workflow_type": workflow_type},  # e.g., "approval", "management"
    )
    resp.raise_for_status()
    return resp.json()["data"]  # contains orchestration_plan_id
```

DRS then:
1. Starts a WO plan of type `approval`
2. Stores `orchestration_plan_id` on the document
3. Returns it so GRC can optionally embed the WO console for reviewers

### Pattern 4: React to document approval in GRC

GRC's Kafka consumer listens to `fims.documents.document.approved`:

```python
# In GRC's Kafka consumer

def handle_document_approved(event: dict):
    document_id = event["data"].get("document_id")
    approver_id = event["data"].get("approver_id")
    workflow_type = event["data"].get("workflow_type")

    # Find the GRC entity linked to this document_id
    engagement = Engagement.objects.filter(
        drs_report_document_id=document_id
    ).first()
    if not engagement:
        return

    engagement.report_status = "approved"
    engagement.approved_by = approver_id
    engagement.save(update_fields=["report_status", "approved_by"])
```

### Pattern 5: Download and embed QR code in GRC frontend

```html
<!-- In GRC frontend (React/Vue) — just render the DRS QR endpoint as an <img> src -->
<img
  src="https://api.fcc.go.tz/drs/api/v1/documents/{documentId}/qr/?format=png"
  alt="Document QR code"
  style={{ width: 120, height: 120 }}
/>
```

Or fetch as base64 to embed in a generated PDF on the GRC side:

```python
def get_document_qr_base64(document_id, jwt_token):
    resp = requests.get(
        f"http://document-records-service:8002/api/v1/documents/{document_id}/qr/",
        headers={"Authorization": f"Bearer {jwt_token}"},
        params={"format": "png", "include_base64": "true"},
    )
    return resp.json()["data"]["qr_code"]  # "data:image/png;base64,..."
```

### Pattern 6: Disposal triggered from GRC

When GRC identifies that audit working papers exceed their retention period:

```python
def initiate_disposal(document_ids, reason, submitted_by_user_id, jwt_token):
    DRS_BASE = "http://document-records-service:8002/api/v1"
    headers = {"Authorization": f"Bearer {jwt_token}"}

    # 1. Mark each document eligible
    for doc_id in document_ids:
        requests.post(
            f"{DRS_BASE}/documents/{doc_id}/mark-eligible-for-disposal/",
            headers=headers,
        )

    # 2. Create disposal form — DRS handles the full approval workflow with WO
    resp = requests.post(f"{DRS_BASE}/disposal/", headers=headers, json={
        "document_ids": [str(d) for d in document_ids],
        "disposal_reason": reason,
        "proposed_disposal_method": "shredding",
        "submitted_by": str(submitted_by_user_id),
    })
    form_id = resp.json()["data"]["id"]
    return form_id
    # GRC stores form_id and waits for DOCUMENTS_DISPOSED Kafka event
```

---

## 27. Complete API Quick Reference

All paths are relative to `http://document-records-service:8002/api/v1/`.

### Documents

| Method | Path | Description | Required Permission |
|---|---|---|---|
| `GET` | `documents/` | List documents | `document:document:read` |
| `POST` | `documents/` | Create document | `document:document:create` |
| `GET` | `documents/{id}/` | Get document | `document:document:read` |
| `PATCH` | `documents/{id}/` | Update document | `document:document:update` |
| `DELETE` | `documents/{id}/` | Delete (draft only) | `document:document:delete` |
| `POST` | `documents/{id}/upload/` | Upload file | `document:document:update` |
| `GET` | `documents/{id}/download/` | Download file | `document:document:read` |
| `GET` | `documents/{id}/preview/` | Preview file | `document:document:read` |
| `GET` | `documents/{id}/qr/` | Get QR code | `document:document:read` |
| `POST` | `documents/{id}/generate-approved-stamp/` | Stamp PDF | `document:document:update` or `X-Service-Token` |
| `GET` | `documents/{id}/thumbnail/` | Get thumbnail | `document:document:read` |
| `POST` | `documents/{id}/lock/` | Lock for editing | `document:document:update` |
| `DELETE` | `documents/{id}/unlock/` | Unlock | `document:document:update` |
| `POST` | `documents/{id}/status/` | Change status | `document:document:update` |
| `POST` | `documents/{id}/archive/` | Archive | `document:document:update` |
| `POST` | `documents/{id}/restore/` | Restore from archive | `document:document:update` |
| `POST` | `documents/{id}/mark-eligible-for-disposal/` | Mark for disposal | `document:document:update` |
| `POST` | `documents/{id}/transfer-ownership/` | Transfer ownership | `document:document:admin` |
| `DELETE` | `documents/{id}/permanent/` | Permanent delete | `document:document:admin` |
| `GET` | `documents/search/` | Full-text search | `document:document:read` |
| `GET` | `documents/search/suggestions/` | Autocomplete | `document:document:read` |
| `GET` | `documents/stats/` | Document stats | `document:document:read` |
| `GET` | `documents/storage/stats/` | Storage stats | `document:document:read` |
| `GET` | `documents/tags/` | All tags | `document:document:read` |

### Versioning

| Method | Path | Description |
|---|---|---|
| `GET` | `documents/{id}/versions/` | List versions |
| `POST` | `documents/{id}/new-version/` | Create new version |
| `GET` | `documents/{id}/version-history/` | Detailed version history |
| `GET` | `documents/{id}/versions/{n}/` | Get specific version |
| `GET` | `documents/{id}/compare/` | Compare two versions |
| `POST` | `documents/{id}/revert/` | Revert to version |
| `POST` | `documents/{id}/revert-fields/` | Revert specific fields |
| `GET` | `documents/{id}/revert-history/` | Revert audit log |
| `GET` | `documents/{id}/versions/{n}/changes/` | Changes in a version |

### Signatures

| Method | Path | Description |
|---|---|---|
| `GET` | `documents/{id}/signatures/` | List signatures |
| `POST` | `documents/{id}/signatures/request/` | Request signature |
| `GET/DELETE` | `documents/{id}/signatures/{sig_id}/` | Detail or delete |
| `POST` | `documents/{id}/signatures/{sig_id}/upload/` | Upload signature |
| `POST` | `documents/{id}/signatures/{sig_id}/validate/` | Validate |
| `GET` | `documents/signatures/my/` | My pending signatures |

### Sharing

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `documents/{id}/shares/` | List or create shares |
| `GET/PATCH/DELETE` | `documents/document-shares/{share_id}/` | Share detail |
| `GET` | `documents/document-shares/my-shares/` | My shared docs |
| `GET` | `documents/document-shares/shared-with-me/` | Shared with me |
| `POST` | `documents/document-shares/bulk/` | Bulk share |
| `GET/POST` | `access-requests/` | Folder access requests |

### Comments

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `documents/{id}/comments/` | List or add comments |
| `GET/PATCH/DELETE` | `documents/document-comments/{id}/` | Comment detail |
| `POST` | `documents/document-comments/{id}/reply/` | Reply |
| `POST` | `documents/document-comments/{id}/resolve/` | Resolve |

### Approval Workflow

| Method | Path | Description |
|---|---|---|
| `POST` | `documents/{id}/submit-for-approval/` | Start approval workflow |
| `POST` | `documents/{id}/approve/` | Direct approval (simple flow) |
| `GET` | `documents/{id}/approval-status/` | Approval status |
| `GET` | `documents/{id}/approvals/` | All approval records |
| `GET` | `documents/workflows/approvals/pending/` | Pending approvals list |
| `GET` | `documents/workflows/approvals/history/{id}/` | Approval history |

### Disposal

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `disposal/` | List or create disposal forms |
| `GET/PATCH` | `disposal/{form_id}/` | Detail |
| `POST` | `disposal/{form_id}/dg-approve/` | DG approval |
| `POST` | `disposal/{form_id}/records-dept-approve/` | Records Dept approval |
| `POST` | `disposal/{form_id}/execute-disposal/` | Execute disposal |
| `GET` | `disposal/{form_id}/status/` | Disposal status |
| `GET` | `disposal/eligible-documents/` | Eligible documents |
| `GET` | `disposal/stats/` | Disposal stats |

### Registers

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `incoming-register/` | Incoming register |
| `GET/PATCH` | `incoming-register/{id}/` | Detail |
| `POST` | `incoming-register/{id}/route/` | Route to user |
| `GET` | `incoming-register/my-inbox/` | My inbox |
| `POST` | `incoming-register/{id}/upload/` | Attach file |
| `GET/POST` | `outgoing-register/` | Outgoing register |
| `GET/PATCH` | `outgoing-register/{id}/` | Detail |
| `POST` | `outgoing-register/{id}/confirm-delivery/` | Confirm delivery |
| `GET` | `outgoing-register/pending/` | Pending deliveries |

### Folders & Storage

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `folders/` | Folders |
| `GET/POST` | `folders/file-series/` | File series |
| `GET/POST` | `folders/keywords/` | Keywords |
| `GET/POST` | `storage-locations/` | Physical storage locations |
| `GET/POST` | `storage-locations/floors/` | Storage floors |
| `POST` | `documents/{id}/physical-storage/create/` | Link physical location |
| `GET` | `documents/{id}/physical-storage/` | Get physical location |

### Reports

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `report-templates/` | Report templates |
| `POST` | `reports/generate/` | Generate report |
| `GET` | `reports/` | List generated reports |
| `GET` | `reports/{id}/` | Report detail |
| `GET` | `reports/{id}/download/` | Download report |
| `GET` | `reports/summary/` | Summary stats |

### Storage Monitoring

| Method | Path | Description |
|---|---|---|
| `GET` | `documents/storage/monitoring/stats/` | Monitoring stats |
| `GET` | `documents/storage/monitoring/alerts/` | Threshold alerts |
| `POST` | `documents/storage/monitoring/alerts/{id}/resolve/` | Resolve alert |

---

*Last updated: March 2026*
