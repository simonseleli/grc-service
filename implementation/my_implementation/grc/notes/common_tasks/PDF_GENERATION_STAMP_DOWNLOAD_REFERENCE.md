# FIMS — PDF Generation, Stamp & Download: Architecture Reference

> **Reference implementation:** Declaration of Independence (GAP 9)
> **SRS Requirements:** 16, 18, 38
> **Status of reference:** Fully implemented and working as of March 2026

This document explains, step by step, exactly how FIMS generates a PDF document,
applies the QR code + CIA signature stamp, and allows the user to download the
signed file. The Declaration of Independence is the canonical implementation.
All other features in the system that need the same capability must follow this
same architecture.

---

## Table of Contents

1. [Core Architecture Principle](#1-core-architecture-principle)
2. [Complete Flow Diagram](#2-complete-flow-diagram)
3. [Step-by-Step Breakdown](#3-step-by-step-breakdown)
   - [Step 1 — HTML Template](#step-1--html-template)
   - [Step 2 — PDF Generation (WeasyPrint)](#step-2--pdf-generation-weasyprint)
   - [Step 3 — Upload to DRS](#step-3--upload-to-drs)
   - [Step 4 — User Signing / Approval](#step-4--user-signing--approval)
   - [Step 5 — Stamp Trigger](#step-5--stamp-trigger)
   - [Step 6 — DRS Stamp Endpoint](#step-6--drs-stamp-endpoint)
   - [Step 7 — Store Stamped URL in GRC DB](#step-7--store-stamped-url-in-grc-db)
   - [Step 8 — Frontend Download](#step-8--frontend-download)
4. [Key Files Reference](#4-key-files-reference)
5. [DRS Client API](#5-drs-client-api)
6. [Data Model Requirements (GRC Side)](#6-data-model-requirements-grc-side)
7. [HTML Template Requirements](#7-html-template-requirements)
8. [Authentication & Permissions](#8-authentication--permissions)
9. [Checklist for Implementing in Another Module](#9-checklist-for-implementing-in-another-module)
10. [Rules and Constraints](#10-rules-and-constraints)
11. [Auto-triggered PDFs — No-Stamp Pattern (Meeting Documents)](#11-auto-triggered-pdfs--no-stamp-pattern-meeting-documents)
12. [Known DRS Document Type Codes](#12-known-drs-document-type-codes)
13. [Debugging PDF Generation](#13-debugging-pdf-generation)
- [⚠️ Critical Lesson: Stamp 401 — Where to Call generate_approved_stamp()](#️-critical-lesson-stamp-401--where-to-call-generate_approved_stamp)
- [Appendix: Stamp Overlay Dimensions](#appendix-stamp-overlay-dimensions-for-template-designers)

---

## 1. Core Architecture Principle

```
 GRC Service                                Document Records Service (DRS)
 ──────────────────────────────────────     ──────────────────────────────────────
 ✅ Generates HTML template context         ✅ Stores all file bytes (ONLY owner)
 ✅ Renders PDF bytes (WeasyPrint)          ✅ Manages document metadata
 ✅ Calls DRS to upload file               ✅ Generates QR code
 ✅ Stores returned document_id (UUID)      ✅ Fetches CIA signature from IAM
 ✅ Calls DRS to stamp when approved       ✅ Overlays stamp on last PDF page
 ✅ Stores returned stamped_url             ✅ Serves downloads via FileResponse
 ❌ NEVER stores file bytes itself
 ❌ NEVER generates QR codes itself
 ❌ NEVER overlays PDFs itself
```

**Golden rule:** GRC is the consumer. DRS is the authority. IAM owns signatures.

---

## 2. Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1 — Document Created                                                      │
│                                                                                 │
│  POST /api/v1/grc/audit/declarations/                                           │
│  (DeclarationListCreateView.post)                                               │
│       │                                                                         │
│       ▼                                                                         │
│  DeclarationOfIndependence.objects.create(...)                                  │
│       │                                                                         │
│       ▼                                                                         │
│  _upload_declaration_pdf_to_drs(decl, auth_token)                               │
│       │                                                                         │
│       ├── generate_declaration_pdf(decl)                                        │
│       │       └── render_to_string('grc/declaration_of_independence.html', ctx) │
│       │           └── HTML(string=html_str).write_pdf()  ← WeasyPrint           │
│       │               Returns: pdf_bytes                                        │
│       │                                                                         │
│       └── DocumentServiceClient.create_document_with_file(                     │
│               title, description, document_type='audit_declaration',            │
│               file_data=BytesIO(pdf_bytes), file_name="declaration_{id}.pdf"   │
│           )                                                                     │
│               ├── Step 1 → POST DRS /api/v1/documents/                         │
│               └── Step 2 → POST DRS /api/v1/documents/{id}/upload/             │
│                   Returns: {'id': <uuid>}                                       │
│                                                                                 │
│  decl.document_id = doc['id']        ← GRC stores UUID only                    │
│  decl.save(update_fields=['document_id'])                                       │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2 — User Signs (or Approves)                                              │
│                                                                                 │
│  POST /api/v1/grc/audit/declarations/{pk}/sign/                                 │
│  (DeclarationSignView.post)                                                     │
│       │                                                                         │
│       ├── DB: is_signed=True, signed_at=now(), status='signed'                  │
│       │                                                                         │
│       ├── Regenerate PDF (now renders "Digitally Signed" block):                │
│       │       generate_declaration_pdf(decl)  ← is_signed=True → template      │
│       │       DocumentServiceClient.upload_file(document_id, new_pdf_bytes)    │
│       │       (same document_id — overwrites file, URL unchanged)              │
│       │                                                                         │
│       └── Publish Kafka event: DECLARATION_SIGNED                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3 — Stamp Trigger (when ALL declarations for engagement are signed)       │
│                                                                                 │
│  all_signed = not declarations.exclude(status='signed').exists()                │
│                                                                                 │
│  if all_signed:                                                                 │
│      for d in declarations.filter(status='signed').exclude(document_id=None):  │
│          result = DocumentServiceClient.generate_approved_stamp(                │
│              document_id=str(d.document_id),                                   │
│              approver_id=str(user_id),       ← the signer's user UUID          │
│              entity_type='declaration',                                         │
│              entity_id=str(d.id),                                               │
│          )                                                                      │
│          d.stamped_document_url = result['stamped_document_url']                │
│          d.save(update_fields=['stamped_document_url'])                         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ INSIDE DRS — generate-approved-stamp endpoint                                   │
│                                                                                 │
│  POST /api/v1/documents/{document_id}/generate-approved-stamp/                  │
│  (GenerateApprovedStampView.post in document-records-service)                   │
│       │                                                                         │
│  1.   Load Document record from DB                                              │
│  2.   Resolve absolute file path on disk (DocumentStorageService)               │
│  3.   Fetch approver's signature image URL from IAM (IAMClient.get_user_profile)│
│  4.   Generate QR code:                                                         │
│           url = https://{EXTERNAL_DOMAIN}/verify/{entity_type}/{entity_id}/     │
│           DocumentQRView._generate_qr_image(url, 'png')  → qr_bytes            │
│  5.   Build ReportLab overlay canvas:                                           │
│           QR code  → bottom-left  (x=15mm, y=8mm, 30×30mm)                     │
│           Signature → bottom-right (x=page_width-82mm, y=8mm, 65×22mm)        │
│           Separator line at y=42mm                                              │
│           "Digitally approved – {datetime}" text at y=44mm                     │
│  6.   Merge overlay onto LAST PAGE using PyPDF2:                                │
│           PdfReader(existing) + PdfReader(overlay) → PdfWriter → stamped_buffer│
│  7.   Save stamped PDF as approved_{uuid4()}.pdf in storage                     │
│  8.   Update Document.file_path = stamped_path in DB                           │
│           (document_id unchanged → download URL still valid)                   │
│  9.   Return:                                                                   │
│           {                                                                     │
│             "document_id": "<uuid>",                                            │
│             "stamped_document_url": "...{base_url}/api/v1/documents/{id}/download/",│
│             "entity_type": "declaration",                                       │
│             "entity_id": "<grc-entity-uuid>"                                   │
│           }                                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4 — Download (Frontend)                                                   │
│                                                                                 │
│  Frontend: DeclarationDetailDialog.tsx                                          │
│       │                                                                         │
│  Show "Download Signed Declaration" button when:                                │
│       item.is_signed === true && item.document_id !== null                      │
│                                                                                 │
│  handleDownload():                                                              │
│       documentClient.get(`/{document_id}/download/`, { responseType: 'blob' }) │
│           → documentClient base URL = {GATEWAY_URL}/api/v1/documents           │
│           → Full URL: {GATEWAY_URL}/api/v1/documents/{id}/download/             │
│           → API Gateway routes to DRS                                           │
│           → DRS DocumentDownloadView serves FileResponse(as_attachment=True)   │
│                                                                                 │
│  Browser side:                                                                  │
│       blob = response.data                                                      │
│       url  = URL.createObjectURL(blob)                                          │
│       <a href={url} download="declaration-{name}.pdf">.click()                 │
│       URL.revokeObjectURL(url)    ← cleanup                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Breakdown

### Step 1 — HTML Template

**Location:** `grc-service/templates/grc/declaration_of_independence.html`

The document is authored as a plain HTML + CSS file that Django's template engine
renders with model context. WeasyPrint then converts it to PDF.

**Critical CSS rule — bottom margin must be ≥ 55 mm:**

```css
@page {
  size: A4;
  margin: 20mm 25mm 60mm 25mm;  /* bottom=60mm leaves room for the DRS stamp */
}
```

The DRS stamp occupies the reserved bottom area:
- QR code: 30×30 mm, positioned at x=15mm, y=8mm from bottom-left
- Signature: 65×22 mm, positioned at x=(page_width − 82mm), y=8mm from bottom-right
- Separator line: at y=42mm
- "Digitally approved" text: at y=44mm

If the bottom margin is less than 55 mm, the stamp will overlap document content.

**Template context variables** (passed from the PDF generator):

| Variable | Type | Description |
|---|---|---|
| `decl` | Model instance | The document model instance |
| `engagement` | Model instance | The related parent engagement |
| `generated_at` | datetime | `timezone.now()` at generation time |

The template uses `{% if decl.is_signed %}` to render the "Digitally Signed" block
with name + date when the declaration has been signed, or blank signature lines when
it is still pending.

---

### Step 2 — PDF Generation (WeasyPrint)

**Location:** `grc-service/apps/core/utils/pdf_generators.py`

```python
def generate_declaration_pdf(decl) -> bytes:
    from django.template.loader import render_to_string
    from weasyprint import HTML

    context = {
        'decl': decl,
        'engagement': decl.audit_engagement,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/declaration_of_independence.html', context)
    return HTML(string=html_str).write_pdf()
```

WeasyPrint is already in `grc-service/requirements.txt`. No additional setup
is needed. The function returns raw PDF bytes in memory — no disk I/O.

**`import io` placement:** The upload helper uses `io.BytesIO(pdf_bytes)`. The
`import io` statement is written **inside the function body** (as a lazy import),
not at the top of the module. Either location works, but keep it consistent with
the existing pattern in `declaration_views.py`.

**`select_related` requirement:** PDF templates access related objects (e.g.
`engagement.auditable_entity.name`). Always call `select_related` before passing
the model instance to the generator, otherwise Django will fire a separate DB query
for every related field access inside the template:

```python
# Good — pre-fetch everything the template needs in one query
decl = DeclarationOfIndependence.objects.select_related(
    'audit_engagement__auditable_entity',
).get(pk=pk)
pdf_bytes = generate_declaration_pdf(decl)

# For meeting documents:
meeting = AuditMeeting.objects.select_related(
    'engagement__auditable_entity',
).get(pk=pk)
pdf_bytes = generate_meeting_minutes_pdf(meeting)
```

If you forget `select_related`, the PDF will still generate (Django lazy-loads),
but it will make N+1 DB queries and slow down the response noticeably.

**Django TEMPLATES setting (required):** For `render_to_string` to locate templates
in `grc-service/templates/`, `config/settings.py` must have:

```python
TEMPLATES = [
    {
        ...
        "DIRS": [BASE_DIR / "templates"],   # ← this line is mandatory
        ...
    }
]
```

Without this, WeasyPrint will raise `TemplateDoesNotExist` at runtime.

When adding a new document type, add a new function here following the same pattern:
`generate_{document_type}_pdf(instance) -> bytes`.

---

### Step 3 — Upload to DRS

Called immediately after creating the model record, and again after signing (to
regenerate with the "Digitally Signed" block).

**Location:** `_upload_declaration_pdf_to_drs()` in
`grc-service/apps/api/views/declaration_views.py`

```python
pdf_bytes = generate_declaration_pdf(decl)
client = DocumentServiceClient(auth_token=auth_token)
doc = client.create_document_with_file(
    title=f"Declaration of Independence — {decl.declarant_name}",
    description=f"...",
    document_type='audit_declaration',   # must exist in DRS seed data
    classification='confidential',
    retention_period=2555,               # 7 years
    file_data=io.BytesIO(pdf_bytes),
    file_name=f"declaration_{decl.id}.pdf",
    metadata={
        'source_service': 'grc',
        'entity_type': 'declaration',
        'entity_id': str(decl.id),
        'engagement_id': str(decl.audit_engagement_id),
        'declarant_id': str(decl.declarant_user_id),
    },
)
decl.document_id = doc['id']
decl.save(update_fields=['document_id'])
```

`create_document_with_file()` is a convenience wrapper in
`DocumentServiceClient` that performs two HTTP calls to DRS:
1. `POST /api/v1/documents/` → creates document metadata, returns `{'id': uuid}`
2. `POST /api/v1/documents/{id}/upload/` → uploads PDF bytes as multipart/form-data

The entire upload is **non-blocking**: any exception is logged and swallowed.
The declaration record remains valid without a PDF; stamping will simply be skipped.

**Idempotency guard — never overwrite an existing document:** Before generating and
uploading, always check whether a `document_id` is already set. This prevents
duplicate DRS documents if the endpoint is called twice:

```python
if not decl.document_id:          # ← guard: only upload once
    pdf_bytes = generate_declaration_pdf(decl)
    doc = client.create_document_with_file(...)
    decl.document_id = doc['id']
    decl.save(update_fields=['document_id'])
```

For **re-upload after signing** (to update with the signed template block), use
`upload_file()` which overwrites the existing DRS file at the same `document_id`:

```python
DocumentServiceClient(auth_token=request.auth).upload_file(
    document_id=str(decl.document_id),
    file_data=io.BytesIO(new_pdf_bytes),
    file_name=f"declaration_{decl.id}.pdf",
)
```

`upload_file()` replaces the existing file at the same `document_id` — no new
document is created, and no download URLs change.

---

### Step 4 — User Signing / Approval

**Location:** `DeclarationSignView.post()` in `declaration_views.py`

For declarations, signing is explicit. The user POSTs to:

```
POST /api/v1/grc/audit/declarations/{pk}/sign/
Body: { "has_conflict": false, "conflict_details": "" }
```

The view:
1. Validates that the requester is the declarant (`decl.declarant_user_id == user_id`)
2. Sets `is_signed=True`, `signed_at=now()`, `status='signed'` on the model
3. Regenerates the PDF with the updated template (now renders "Digitally Signed" block)
4. Uploads the new PDF bytes to DRS at the same `document_id` (overwrite)
5. Publishes a Kafka event `DECLARATION_SIGNED`
6. Checks if all declarations for the engagement are now signed → triggers stamp
7. Calls `decl.refresh_from_db()` **before returning the response**

> **Critical — `refresh_from_db()` is not optional.**
> The stamp loop saves `stamped_document_url` on separate ORM instances (`d`),
> not on the original `decl` object. Without `refresh_from_db()`, the API response
> will return `stamped_document_url: null` even though it was just written to the DB.
> Always call it after any loop that updates related objects:
> ```python
> decl.refresh_from_db()
> return success_response(data=DeclarationOfIndependenceSerializer(decl).data, ...)
> ```

For **other document types** (Audit Report, Audit Memo, etc.), the trigger may be
a CIA approval event via the Work Orchestration workflow rather than direct signing.
The stamp call is always the same regardless of trigger mechanism.

---

### Step 5 — Stamp Trigger

After signing, the view checks whether all active declarations for the engagement
are now signed:

```python
all_signed = not DeclarationOfIndependence.objects.filter(
    audit_engagement=decl.audit_engagement,
    is_active=True,           # ← is_active comes from TimestampedModel (soft-delete)
).exclude(status='signed').exists()
```

**`is_active=True`** filters out soft-deleted records. All GRC models inherit from
`TimestampedModel` which provides this field. Always include it in the all-signed
check so deactivated records do not block the stamp trigger.

If `all_signed` is `True`, it loops over every declaration that has a `document_id`
and calls the stamp endpoint for each one:

```python
client = DocumentServiceClient(auth_token=request.auth)
for d in DeclarationOfIndependence.objects.filter(
    audit_engagement=decl.audit_engagement,
    is_active=True,
    status='signed',
).exclude(document_id=None):
    try:
        result = client.generate_approved_stamp(
            document_id=str(d.document_id),
            approver_id=str(user_id),      # the final signer acts as approver
            entity_type='declaration',
            entity_id=str(d.id),
        )
        stamped_url = result.get('stamped_document_url')
        # Rewrite internal Docker URL → public API Gateway URL
        internal_base = settings.DOCUMENT_SERVICE_URL.rstrip('/')
        public_base = getattr(settings, 'DOCUMENT_SERVICE_PUBLIC_URL', '').rstrip('/')
        if public_base and stamped_url.startswith(internal_base):
            stamped_url = public_base + stamped_url[len(internal_base):]
        d.stamped_document_url = stamped_url
        d.save(update_fields=['stamped_document_url'])
    except Exception as stamp_err:
        logger.warning("Stamp failed for %s: %s", d.id, stamp_err)
        # Non-blocking — one failed stamp does not abort the others
```

**Each stamp call is wrapped in its own try/except** so that one failure does not
prevent the remaining declarations from being stamped.

**URL rewriting:** DRS returns internal Docker hostnames like
`http://document-records-service:8002/api/v1/documents/{id}/download/`.
The rewrite replaces the prefix with `settings.DOCUMENT_SERVICE_PUBLIC_URL`
(e.g. `http://localhost:8080`) before saving. Use `getattr(..., '')` as a fallback
so a missing setting does not raise an `AttributeError` — it just skips the rewrite.

---

### Step 6 — DRS Stamp Endpoint

**Location:** `document-records-service/apps/api/views/document_stamp_view.py`
**URL:** `POST /api/v1/documents/{document_id}/generate-approved-stamp/`

Request body (JSON):
```json
{
  "approver_id":  "<cia-or-signer-user-uuid>",
  "entity_type":  "declaration",
  "entity_id":    "<grc-declaration-uuid>"
}
```

What DRS does internally:

1. **Loads document** from DB by UUID — resolves the current file path on disk.
2. **Fetches signature** from IAM: `IAMClient.get_user_profile(approver_id)`
   → returns `{ 'signature': '<url_to_image>' }`. Non-blocking if IAM is down.
3. **Generates QR code** pointing to:
   `https://{EXTERNAL_DOMAIN}/verify/{entity_type}/{entity_id}/`
   Uses the `qrcode` library, output format PNG.
4. **Builds ReportLab overlay canvas** (same page size as the PDF's last page):
   - QR code (`30×30 mm`) at `x=15mm, y=8mm`
   - Signature image (`65×22 mm`) at `x=page_width−82mm, y=8mm`
   - Grey separator line at `y=42mm`
   - "Digitally approved — {datetime UTC}" at `y=44mm`
5. **Merges with PyPDF2:** overlays the stamp canvas onto the last page.
6. **Saves** stamped PDF as `approved_{uuid4()}.pdf` in the same storage directory.
7. **Updates** `Document.file_path` and `Document.file_name` in DB — the
   `document_id` itself does not change, so all existing download URLs remain valid.
8. **Returns:**
   ```json
   {
     "document_id": "<drs-uuid>",
     "stamped_document_url": "<base_url>/api/v1/documents/<id>/download/",
     "entity_type": "declaration",
     "entity_id": "<grc-uuid>"
   }
   ```

**Libraries used by DRS for stamping:**
- `PyPDF2` — read/write/merge PDF pages
- `reportlab` — draw QR + signature overlay canvas
- `Pillow (PIL)` — open QR image bytes
- `qrcode` — generate QR code image

All are already in `document-records-service/requirements.txt`.

---

### Step 7 — Store Stamped URL in GRC DB

After the stamp call returns, GRC stores the URL on the model:

```python
d.stamped_document_url = result.get('stamped_document_url')
d.save(update_fields=['stamped_document_url'])
```

The model needs two fields:

```python
document_id = models.UUIDField(
    null=True, blank=True,
    help_text="DRS document UUID for the PDF"
)
stamped_document_url = models.URLField(
    max_length=500, blank=True, null=True,
    help_text="URL to the signed + QR-stamped PDF"
)
```

The serializer exposes both fields to the frontend.

---

### Step 8 — Frontend Download

**Location:** `frontend/apps/staff-portal/src/components/grc/DeclarationDetailDialog.tsx`

**Show condition:** Only show the download button when:
- `item.is_signed === true`
- `item.document_id !== null`

**Download handler:**
```typescript
const handleDownload = async () => {
  setIsDownloading(true);
  try {
    const response = await documentClient.get(`/${item.document_id}/download/`, {
      responseType: 'blob',
    });
    const blob = response.data as Blob;
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `declaration-${item.declarant_name || item.id}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (err: any) {
    toast.error('Failed to download declaration', {
      description: err.response?.data?.error || err.message,
    });
  } finally {
    setIsDownloading(false);
  }
};
```

`documentClient` is the axios instance for the `documents` service:
```
baseURL = {GATEWAY_URL}/api/v1/documents
```
Defined in `frontend/packages/shared/src/api/gateway.ts`.

The full request flow:
```
Frontend → API Gateway (/api/v1/documents/{id}/download/)
        → DRS DocumentDownloadView
        → Resolves file path on disk
        → FileResponse(as_attachment=True, content_type='application/pdf')
        → Browser blob download
```

**Note:** The download always fetches the current file at `document_id`.
After stamping, DRS updates `Document.file_path` to the stamped file — the
same download URL now serves the stamped PDF. No URL change required.

---

## 4. Key Files Reference

### Stamped-document reference implementations

| File | Purpose |
|---|---|
| `grc-service/apps/api/views/declaration_views.py` | Declarations — create, sign, upload to DRS, trigger stamp |
| `grc-service/apps/api/views/engagement_notification_views.py` | Engagement Notifications — create, CIA approval, stamp in workflow-action view |
| `grc-service/apps/core/utils/pdf_generators.py` | **All** WeasyPrint PDF generation functions (declarations, EN, meeting docs) |
| `grc-service/templates/grc/declaration_of_independence.html` | HTML template — Declaration of Independence |
| `grc-service/templates/grc/engagement_notification.html` | HTML template — Engagement Notification |
| `grc-service/apps/core/models/audit_entities.py` | `DeclarationOfIndependence` model — `document_id`, `stamped_document_url` |
| `grc-service/apps/infrastructure/external/document_service_client.py` | HTTP client for **all** DRS calls |
| `document-records-service/apps/api/views/document_stamp_view.py` | Stamp endpoint — QR + signature overlay logic |
| `document-records-service/apps/api/views/document_download_view.py` | Download endpoint — resolves and serves file |
| `document-records-service/apps/api/urls/documents.py` | DRS URL routing |
| `document-records-service/apps/infrastructure/persistence/seed_document_types.py` | Document type seed data — must include every type used by GRC |
| `frontend/apps/staff-portal/src/components/grc/DeclarationDetailDialog.tsx` | Frontend dialog with download button (Declaration reference) |
| `frontend/packages/shared/src/api/gateway.ts` | `documentClient` axios instance routing through API Gateway |

### Auto-triggered document reference implementation (no stamp)

| File | Purpose |
|---|---|
| `grc-service/apps/api/views/audit_meeting_views.py` | `_generate_meeting_documents()` — auto-triggered on meeting completion; `_sync_engagement_meeting_date()` |
| `grc-service/apps/core/utils/pdf_generators.py` | `generate_meeting_minutes_pdf()` and `generate_attendance_register_pdf()` |
| `grc-service/templates/grc/meeting_minutes.html` | HTML template — Meeting Minutes |
| `grc-service/templates/grc/attendance_register.html` | HTML template — Attendance Register |
| `grc-service/apps/core/models/audit_meeting.py` | `AuditMeeting` model — `minutes_document_id`, `attendance_document_id` |

---

## 5. DRS Client API

All GRC interaction with DRS goes through:
`grc-service/apps/infrastructure/external/document_service_client.py`

### Key methods

#### `create_document_with_file(...)` — Upload a new PDF to DRS

```python
doc = client.create_document_with_file(
    title="My Document Title",
    description="Human-readable description",
    document_type='audit_declaration',   # must be seeded in DRS
    classification='confidential',       # or 'open'
    retention_period=2555,               # days (2555 = 7 years)
    file_data=io.BytesIO(pdf_bytes),     # file-like object
    file_name="my_document.pdf",
    metadata={
        'source_service': 'grc',
        'entity_type': 'my_entity',
        'entity_id': str(instance.id),
    },
)
# doc['id'] → the DRS document UUID → store on the model
```

#### `upload_file(document_id, file_data, file_name)` — Overwrite existing file

```python
client.upload_file(
    document_id=str(instance.document_id),
    file_data=io.BytesIO(new_pdf_bytes),
    file_name="my_document_v2.pdf",
)
# Same document_id preserved — download URL unchanged
```

#### `generate_approved_stamp(document_id, approver_id, entity_type, entity_id)` — Apply QR + signature stamp

```python
result = client.generate_approved_stamp(
    document_id=str(instance.document_id),
    approver_id=str(approver_user_uuid),
    entity_type='my_entity',       # used to build the QR code verification URL
    entity_id=str(instance.id),    # used to build the QR code verification URL
)
# result['stamped_document_url'] → URL to the now-stamped PDF download
# result['document_id']          → unchanged DRS UUID
```

---

## 6. Data Model Requirements (GRC Side)

Every GRC model that has a PDF document must have these two fields:

```python
document_id = models.UUIDField(
    null=True,
    blank=True,
    help_text="DRS document UUID (GAP 9)"
)
stamped_document_url = models.URLField(
    max_length=500,
    blank=True,
    null=True,
    help_text="URL to the stamped PDF served by DRS (GAP 9)"
)
```

The serializer must include both fields so the frontend can:
- Check `document_id` to know whether to show a download button
- Use `document_id` directly as the DRS download path parameter

---

## 7. HTML Template Requirements

When creating a new PDF template:

1. **Location:** `grc-service/templates/grc/{document_name}.html`

2. **Bottom margin — mandatory:** must be ≥ 55mm (use 60mm for safety):
   ```css
   @page {
     size: A4;
     margin: 20mm 25mm 60mm 25mm;
   }
   ```

3. **Page size:** always A4 unless there is a specific reason otherwise.

4. **Font:** Arial or Helvetica (safe for WeasyPrint without extra font installation).

5. **Signed block pattern:** use `{% if decl.is_signed %}` (or equivalent field
   on your model) to conditionally render the "Digitally Signed" block vs blank
   signature lines. The stamp will overlay the blank margin regardless; the
   rendered text reflects the data-level signing state.

6. **Reserved stamp area comment:** add this comment in the template's signature block:
   ```html
   <!-- DRS will overlay QR code (bottom-left) + approver signature (bottom-right)
        in the reserved bottom margin -->
   ```

7. **Footer note:** include a note mentioning the QR code when `is_signed=True`:
   ```html
   {% if decl.is_signed %}
   The QR code at the bottom of this page can be scanned to verify authenticity.
   {% endif %}
   ```

---

## 8. Authentication & Permissions

### Required settings in `grc-service/config/settings.py`

```python
# Internal Docker network URL — used by GRC backend to call DRS
DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL", "http://document-records-service:8002")

# Public-facing URL (API Gateway) — used to rewrite stamped_document_url before
# storing it, so the browser can actually reach the download link
DOCUMENT_SERVICE_PUBLIC_URL = os.getenv("DOCUMENT_SERVICE_PUBLIC_URL", "http://localhost:8080")
```

Set both in `grc-service/env.example` (and in the actual `.env` file) so they are
available at runtime.

### DRS client import path

```python
from apps.infrastructure.external.document_service_client import DocumentServiceClient
```

### GRC → DRS calls

All HTTP calls from GRC to DRS must include the **user's Bearer JWT token**:

```python
client = DocumentServiceClient(auth_token=request.auth)
```

`request.auth` is the raw Bearer token value extracted by DRF's JWT authentication
middleware. DRS's `JWTPermissionMiddleware` validates it and checks that the token
carries the `document:document:create` permission (granted to internal auditor roles
via IAM; see IAM role setup).

**Never use `X-Service-Token` for calls that originate from a user action.** The
service token bypasses user-level permission checks and is only for background workers.

### DRS Stamp endpoint authentication

`GenerateApprovedStampView` accepts **both**:
- `Authorization: Bearer <jwt>` — for user-triggered stamps (as in Declaration sign)
- `X-Service-Token: <token>` — for background consumer-triggered stamps (Audit Report)

### Frontend → DRS calls (through API Gateway)

The `documentClient` axios instance (defined in `gateway.ts`) automatically attaches
`Authorization: Bearer <accessToken>` from localStorage on every request.

```typescript
const documentClient = createServiceClient('documents');
// baseURL = {GATEWAY_URL}/api/v1/documents
// → API Gateway routes /api/v1/documents/* → DRS
```

---

## 9. Checklist for Implementing in Another Module

Use this checklist when implementing PDF generation + stamp + download for a new
document type in GRC (e.g., Audit Report, Audit Memo, Engagement Notification).

### Backend (GRC Service)

- [ ] **Model:** Add `document_id = UUIDField(null=True, blank=True)` and
      `stamped_document_url = URLField(null=True, blank=True)` to the model.
- [ ] **Migration:** Create and run a migration for the two new fields.
- [ ] **Serializer:** Expose `document_id` and `stamped_document_url` as read-only fields.
- [ ] **Template:** Create `grc-service/templates/grc/{document_type}.html` with
      60mm bottom margin and conditional signed block.
- [ ] **PDF generator:** Add `generate_{document_type}_pdf(instance) -> bytes` to
      `grc-service/apps/core/utils/pdf_generators.py`.
- [ ] **Upload helper:** Write a `_upload_{document_type}_pdf_to_drs(instance, auth_token)` function that:
      1. Calls the PDF generator
      2. Calls `DocumentServiceClient.create_document_with_file(...)` (or `upload_file` to overwrite)
      3. Saves `instance.document_id`
- [ ] **Call upload on create:** Call the upload helper immediately after the model record is saved.
- [ ] **Call upload on sign/update:** Regenerate and re-upload the PDF after the signing event so the latest data is always in DRS.
- [ ] **Stamp trigger:** After the approval/signing event, check the trigger condition (all signed, CIA approved, etc.), then call `DocumentServiceClient.generate_approved_stamp(...)` and save `stamped_document_url`. Wrap each stamp call in its own `try/except` so one failure does not abort the rest.
- [ ] **URL rewrite:** Rewrite `settings.DOCUMENT_SERVICE_URL` prefix to `settings.DOCUMENT_SERVICE_PUBLIC_URL` before storing `stamped_document_url`. Use `getattr(settings, 'DOCUMENT_SERVICE_PUBLIC_URL', '')` so a missing setting fails gracefully.
- [ ] **`refresh_from_db()`:** After the stamp loop, call `instance.refresh_from_db()` before serializing the response — otherwise `stamped_document_url` will be `null` in the API response even though it was just saved to DB.

### DRS (Document Records Service)

- [ ] **Document type seed:** Ensure the `document_type` code used by GRC exists in
      `document-records-service/apps/infrastructure/persistence/seed_document_types.py`.
      Add it if missing and restart/reseed DRS.

### Frontend

- [ ] **Type definition:** Add `document_id: string | null` and `stamped_document_url: string | null` to the TypeScript type for the entity.
- [ ] **Download button:** Show download button when `item.is_signed && item.document_id`.
- [ ] **Download handler:** Use `documentClient.get(`/{item.document_id}/download/`, { responseType: 'blob' })` and trigger the browser file save.
- [ ] **Loading state:** Use a `isDownloading` boolean and show a spinner on the button during the request.
- [ ] **Error handling:** Wrap in try/catch and show a `toast.error(...)` on failure.
- [ ] **List serializer:** Add `document_id` to **both** the list serializer and the detail serializer. If `document_id` is only on the detail serializer, the download button will never appear on list/card views because the field will be `undefined`.

---

## 10. Rules and Constraints

These are absolute constraints — breaking them will cause silent failures or break
the download/stamp pipeline for all documents in the system.

| Rule | Reason |
|---|---|
| GRC never stores PDF bytes — only `document_id` | FIMS Principle 2: DRS is the sole file authority |
| GRC never generates QR codes | DRS owns QR generation; GRC just passes `entity_type` and `entity_id` |
| GRC never overlays PDFs | DRS owns the stamp overlay (ReportLab + PyPDF2) |
| Template bottom margin ≥ 55mm | Anything less causes the stamp to overlap document content |
| Upload is non-blocking | Missing PDF does not invalidate the declaration; it just skips stamping |
| Re-upload PDF after signing | The template renders differently based on `is_signed`; DRS must have the updated file |
| Same `document_id` on re-upload | `upload_file()` replaces the file at the existing UUID — download URL is unchanged |
| Pass user's JWT to DRS | DRS middleware enforces `document:document:create` permission on uploads |
| Rewrite internal Docker URL | DRS returns internal hostnames (`http://document-records-service:8002`); frontend cannot reach them — rewrite to `DOCUMENT_SERVICE_PUBLIC_URL` before saving |
| `audit_declaration` (or equivalent) type must exist in DRS seed | DRS will reject document creation with a 400 if the `document_type` code is unknown |
| Use `document_id` for download (not `stamped_document_url`) | After stamping, DRS updates `Document.file_path` at the **same UUID** — the `/download/` URL for that UUID now serves the stamped file automatically. `stamped_document_url` is stored for reference but the download button should use `document_id` directly. |

| Pass user's JWT to DRS | DRS middleware enforces `document:document:create` permission on uploads |
| Rewrite internal Docker URL | DRS returns internal hostnames (`http://document-records-service:8002`); frontend cannot reach them — rewrite to `DOCUMENT_SERVICE_PUBLIC_URL` before saving |
| `audit_declaration` (or equivalent) type must exist in DRS seed | DRS will reject document creation with a 400 if the `document_type` code is unknown |
| Use `document_id` for download (not `stamped_document_url`) | After stamping, DRS updates `Document.file_path` at the **same UUID** — the `/download/` URL for that UUID now serves the stamped file automatically. `stamped_document_url` is stored for reference but the download button should use `document_id` directly. |

---

## 11. Auto-triggered PDFs — No-Stamp Pattern (Meeting Documents)

Not all GRC documents go through a signing/approval/stamp workflow. Some are
**informational outputs** that must be generated automatically when a process reaches
a terminal state, stored in DRS, and made downloadable — but never stamped.

**Reference implementation:** `AuditMeeting` → Meeting Minutes + Attendance Register

### When to use this pattern

Use the no-stamp pattern when:
- The document is generated on a **status transition** (not a user sign action)
- The document does **not** require CIA approval or a digital stamp
- The document is produced automatically as part of a workflow step completing

Documents that follow this pattern right now:
| Document | Trigger | DRS type | Stamped? |
|---|---|---|---|
| Meeting Minutes | Meeting → `completed` | `audit_meeting_minutes` | No |
| Attendance Register | Meeting (entry/exit) → `completed` | `audit_meeting_attendance` | No |

Documents that follow the **stamped** pattern:
| Document | Trigger | DRS type | Stamped? |
|---|---|---|---|
| Declaration of Independence | User signs | `audit_declaration` | Yes |
| Engagement Notification | CIA approves via WO | `audit_engagement_notification` | Yes |

---

### One model → multiple documents

`AuditMeeting` is unique in that **one model instance produces two separate DRS
documents** (minutes and attendance register). Each has its own `document_id` field:

```python
# AuditMeeting model fields
minutes_document_id    = models.UUIDField(null=True, blank=True)
attendance_document_id = models.UUIDField(null=True, blank=True)
```

Rules for multi-document models:
- Each document has its own separate `document_id` field — never share UUIDs.
- Each has its own idempotency guard (`if not meeting.minutes_document_id` / `if not meeting.attendance_document_id`).
- Both are uploaded in the **same helper function** `_generate_meeting_documents()`.
- Expose **both** `document_id` fields in the serializer (list AND detail).

---

### The `_generate_meeting_documents()` pattern

The complete pattern for auto-triggered, no-stamp PDFs:

```python
def _generate_meeting_documents(meeting, auth_token=None):
    """
    GAP-9: Auto-generate PDFs on meeting completion and upload to DRS.
    Non-blocking — any error is logged and swallowed.
    Idempotent — already-set document IDs are never overwritten.
    """
    import io
    from apps.core.utils.pdf_generators import (
        generate_meeting_minutes_pdf,
        generate_attendance_register_pdf,
    )
    from apps.infrastructure.external.document_service_client import DocumentServiceClient

    # Skip meeting types that don't produce formal documents
    if meeting.meeting_type == 'team':
        return

    client = DocumentServiceClient(auth_token=auth_token)
    fields_to_update = []

    # ── Step 1: Minutes PDF (entry, exit, pre_exit) ─────────────────────
    if not meeting.minutes_document_id:            # ← idempotency guard
        try:
            pdf_bytes = generate_meeting_minutes_pdf(meeting)
            doc = client.create_document_with_file(
                title=f"Meeting Minutes — {meeting.reference_number}",
                description=f"...",
                document_type='audit_meeting_minutes',
                classification='confidential',
                retention_period=2555,
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"meeting_minutes_{meeting.id}.pdf",
                metadata={
                    'source_service': 'grc',
                    'entity_type': 'audit_meeting',
                    'entity_id': str(meeting.id),
                    'engagement_id': str(meeting.engagement_id),
                    'meeting_type': meeting.meeting_type,
                },
            )
            meeting.minutes_document_id = doc['id']
            fields_to_update.append('minutes_document_id')
        except Exception as exc:
            logger.warning('GAP-9: Minutes PDF failed for meeting %s: %s', meeting.id, exc)
            # Non-blocking: failure here does NOT roll back the meeting.status = 'completed'

    # ── Step 2: Attendance Register (entry, exit only) ───────────────────
    if meeting.meeting_type in ('entry', 'exit') and not meeting.attendance_document_id:
        try:
            pdf_bytes = generate_attendance_register_pdf(meeting)
            doc = client.create_document_with_file(
                title=f"Attendance Register — {meeting.reference_number}",
                document_type='audit_meeting_attendance',
                ...
            )
            meeting.attendance_document_id = doc['id']
            fields_to_update.append('attendance_document_id')
        except Exception as exc:
            logger.warning('GAP-9: Attendance PDF failed for meeting %s: %s', meeting.id, exc)

    # ── Step 3: Save only fields that were updated ───────────────────────
    if fields_to_update:
        meeting.save(update_fields=fields_to_update)
```

---

### Critical: call OUTSIDE the atomic transaction

`_generate_meeting_documents()` makes HTTP calls to DRS (external service). These
must happen **after** the `transaction.atomic()` block that saved `meeting.status`:

```python
# ✅ CORRECT — DB committed first, then DRS upload
with transaction.atomic():
    meeting.status = new_status
    meeting.save(update_fields=['status', 'updated_at'])
    _sync_engagement_meeting_date(meeting)       # DB-only, safe inside atomic

# DRS upload called AFTER the transaction commits
if new_status == 'completed':
    _generate_meeting_documents(meeting, auth_token=auth_token)

# ❌ WRONG — DRS upload inside atomic block
with transaction.atomic():
    meeting.status = new_status
    meeting.save(...)
    _generate_meeting_documents(meeting, auth_token=auth_token)  # ← NEVER do this
```

If the DRS upload is inside the atomic block and an unrelated DB error later triggers
a rollback, you end up with orphaned DRS documents (file stored in DRS but no
`document_id` saved to the meeting record).

---

### Auth token extraction for status-change views

In status-change views (where `request.auth` may be a token object rather than a raw
string), extract the raw Bearer token from the HTTP header directly:

```python
auth_header = request.META.get('HTTP_AUTHORIZATION', '')
auth_token = (
    auth_header[len('Bearer '):].strip()
    if auth_header.startswith('Bearer ')
    else None
)
_generate_meeting_documents(meeting, auth_token=auth_token)
```

Use `auth_token=None` as a fallback — `DocumentServiceClient(auth_token=None)` will
make unauthenticated calls that DRS may reject with 401 for protected endpoints. For
`create_document_with_file`, ensure the token is always present.

---

### Status-transition prerequisite guards

For meeting documents, SRS requires meeting text minutes to be recorded before a
meeting can be marked completed. Validate this **before** triggering PDF generation:

```python
if new_status == 'completed':
    if not (meeting.minutes or '').strip():
        return Response(
            {'error': {'message': 'Meeting minutes must be recorded before completing.'}},
            status=status.HTTP_400_BAD_REQUEST,
        )
```

This guard ensures the generated PDF always has substantive content, not an empty
minutes field.

---

### Template context for meeting documents

```python
# generate_meeting_minutes_pdf(meeting)
context = {
    'meeting':     meeting,               # AuditMeeting instance
    'engagement':  meeting.engagement,    # AuditEngagement instance
    'auditee_name': meeting.engagement.auditable_entity.name,
    'generated_at': timezone.now(),
}

# generate_attendance_register_pdf(meeting)
attendees = meeting.attendees or []       # list of dicts from JSONField
context = {
    'meeting':       meeting,
    'engagement':    meeting.engagement,
    'auditee_name':  meeting.engagement.auditable_entity.name,
    'generated_at':  timezone.now(),
    'present_count': sum(1 for a in attendees if a.get('present')),
}
```

**Required `select_related` before calling either generator:**

```python
meeting = AuditMeeting.objects.select_related(
    'engagement__auditable_entity',
).get(pk=pk)
```

---

### Checklist for adding a new no-stamp auto-triggered document

- [ ] Add `{name}_document_id = UUIDField(null=True, blank=True)` to the model.
- [ ] Create and run migration.
- [ ] Add field to **both** list and detail serializers.
- [ ] Add `generate_{name}_pdf(instance) -> bytes` to `pdf_generators.py`.
- [ ] Create `grc-service/templates/grc/{name}.html` with 20mm bottom margin (no stamp needed — no 60mm requirement).
- [ ] Seed the `document_type` code in `seed_document_types.py` if it doesn't exist (see Section 12).
- [ ] Write the `_generate_{name}_documents(instance, auth_token)` helper — idempotent, non-blocking.
- [ ] Call the helper **outside** the `transaction.atomic()` block, only when status reaches the trigger state.
- [ ] Extract auth token from `request.META.get('HTTP_AUTHORIZATION', '')`.
- [ ] Add any prerequisite validation (content checks) before the status transition.

> **Note on bottom margin:** Documents that are only downloaded (never stamped)
> do not need the 60mm reserved bottom margin. Use a standard 20–25mm bottom margin.
> Only documents that will receive the DRS stamp overlay need ≥ 55mm at the bottom.

---

## 12. Known DRS Document Type Codes

Every call to `create_document_with_file(document_type=...)` must use a code that
exists in the DRS seed data. DRS returns `HTTP 400` if the code is unknown.

**Full list of GRC-relevant codes** (from `seed_document_types.py`):

| Code | Name | `requires_approval` | Retention (days) | Reference prefix |
|---|---|---|---|---|
| `audit_declaration` | Declaration of Independence | False | 2555 (7 yr) | DCL |
| `audit_engagement_notification` | Engagement Notification | True | 2555 (7 yr) | EN |
| `audit_meeting_minutes` | Audit Meeting Minutes | False | 2555 (7 yr) | AMM |
| `audit_meeting_attendance` | Audit Meeting Attendance | False | 2555 (7 yr) | AMA |
| `audit_report` | Audit Report | True | 3650 (10 yr) | AUD |
| `audit_working_paper` | Audit Working Paper | False | 2555 (7 yr) | AWP |
| `memo` | Memo | False | 3650 (10 yr) | MEM |
| `report` | Report | True | 3650 (10 yr) | RPT |
| `minutes` | Minutes (general) | False | 2555 (7 yr) | MIN |
| `letter` | Letter | False | 1825 (5 yr) | LTR |

**Full seed file:** `document-records-service/apps/infrastructure/persistence/seed_document_types.py`

### How to add a new document type

1. Open `seed_document_types.py` and append a new entry to `INITIAL_DOCUMENT_TYPES`:

```python
{
    'code': 'audit_my_new_doc',              # unique snake_case string
    'name': 'My New Document',
    'description': 'Description for DRS UI',
    'icon': 'file-text',                     # lucide icon name
    'color': '#DC2626',
    'default_classification': 'confidential',
    'default_retention_period': 2555,        # days
    'requires_approval': False,
    'reference_prefix': 'MND',
    'is_system': False,
},
```

2. Restart and reseed DRS to pick up the new type:

```bash
docker compose -f document-records-service/docker-compose.yml restart document-records-service
# DRS runs seed_document_types on startup automatically
```

3. Verify the code is accepted by checking the DRS admin or running a test upload.

> **Warning:** If you use a new `document_type` code in GRC before seeding it in
> DRS, `create_document_with_file()` will return HTTP 400 and the upload helper's
> `except` block will swallow the error — the meeting/declaration will save without
> a `document_id`, and the download button will never appear.

---

## 13. Debugging PDF Generation

### Step 1 — Check GRC service logs

```bash
docker logs fims-grc-service --tail 100 -f | grep -i "GAP-9\|minutes\|attendance\|DRS\|document"
```

Look for:
- `GAP-9: Minutes PDF for meeting <id> uploaded to DRS as document <id>` → success
- `GAP-9: Could not generate/upload minutes PDF for meeting <id>: <error>` → failure

### Step 2 — Check if `document_id` is set on the model

```bash
docker exec -it fims-grc-service python manage.py shell
```

```python
from apps.core.models.audit_meeting import AuditMeeting
m = AuditMeeting.objects.get(id='<meeting-uuid>')
print(f"status: {m.status}")
print(f"minutes_document_id: {m.minutes_document_id}")
print(f"attendance_document_id: {m.attendance_document_id}")
```

### Step 3 — Reset a meeting for re-testing

If you need to re-trigger PDF generation (e.g. after a template fix), reset the
meeting state:

```python
from apps.core.models.audit_meeting import AuditMeeting
m = AuditMeeting.objects.get(id='<meeting-uuid>')
m.status = 'in_progress'
m.minutes_document_id = None
m.attendance_document_id = None
m.save(update_fields=['status', 'minutes_document_id', 'attendance_document_id'])
print(f"Reset OK — status: {m.status} | doc IDs cleared")
```

Then mark the meeting as completed again via the API to re-trigger generation.

### Step 4 — Test WeasyPrint rendering directly

```bash
docker exec -it fims-grc-service python manage.py shell
```

```python
from apps.core.models.audit_meeting import AuditMeeting
from apps.core.utils.pdf_generators import generate_meeting_minutes_pdf

m = AuditMeeting.objects.select_related('engagement__auditable_entity').get(id='<uuid>')
try:
    pdf_bytes = generate_meeting_minutes_pdf(m)
    print(f"PDF generated OK — {len(pdf_bytes)} bytes")
except Exception as e:
    print(f"ERROR: {e}")
```

If WeasyPrint fails, common causes:
- `TemplateDoesNotExist` → check `TEMPLATES[0]['DIRS']` in `settings.py` points to `BASE_DIR / "templates"`
- `AttributeError: 'NoneType' object has no attribute 'name'` → missing `select_related` on a related field
- CSS import errors → check that no external `@import url(...)` rules exist in the template (WeasyPrint cannot reach external URLs in Docker containers)

### Step 5 — Verify DRS document type is seeded

```bash
docker exec -it fims-document-records python manage.py shell
```

```python
from apps.infrastructure.persistence.models_document_type import DocumentType
print(list(DocumentType.objects.values_list('code', flat=True)))
# Should include: 'audit_meeting_minutes', 'audit_meeting_attendance', etc.
```

If the code is missing: add it to `seed_document_types.py` and restart the DRS container.

### Step 6 — Verify the download URL is accessible

Test the DRS download endpoint directly:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8080/api/v1/documents/<document_id>/download/ \
  -o test_output.pdf
```

If you get `404` → the DRS document record exists but the file is missing from storage.
If you get `401` → the JWT token is invalid or expired, or the user's role lacks `document:document:view`.

### Common failure modes and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `document_id` is `None` after meeting completion | DRS upload failed silently | Check GRC logs for `GAP-9: Could not generate`; check DRS document type is seeded |
| Download button never appears | `document_id` missing from list serializer | Add field to `{Model}ListSerializer` |
| "Failed to download" in browser | JWT token missing `document:document:view` | Verify IAM role has the permission assigned |
| PDF renders but content is wrong | `select_related` missing — template hit wrong DB object | Add `select_related('engagement__auditable_entity')` before calling the generator |
| WeasyPrint: `TemplateDoesNotExist` | `TEMPLATES[0]['DIRS']` not set | Add `BASE_DIR / "templates"` to `DIRS` in `settings.py` |
| DRS returns `400` on `create_document_with_file` | `document_type` code not seeded | Add to `seed_document_types.py`, restart DRS |
| Stamp fails with `401` | Stamp called from Kafka consumer | Move stamp call to the view using `request.auth` (see Critical Lesson) |
| `stamped_document_url` is `null` in API response | `refresh_from_db()` not called after stamp loop | Call `instance.refresh_from_db()` before serializing the response |
| Container changes not reflected in PDF output | Template change not picked up after rebuild | Rebuild and restart the GRC container: `docker compose up -d --build grc-service` |

---

## ⚠️ Critical Lesson: Stamp 401 — Where to Call `generate_approved_stamp()`

> **Learned during EN implementation (2026-03-16). Apply to every future feature that uses DRS stamping.**

### The Problem

When CIA approves a document via WO, the Kafka consumer receives `grc.workflow.completed`
and attempts to call `_trigger_approved_stamp()`. This call **always fails with 401** because:

- The Kafka consumer has **no JWT** — it runs as a background process with no user session
- DRS `generate-approved-stamp/` endpoint is protected by `JWTPermissionMiddleware`
- `X-Service-Token` alone is **blocked by the middleware before DRF permission classes even run**
- `SERVICE_TO_SERVICE_TOKEN` is not set in the Kafka consumer container env

```
fims-grc-kafka-consumer | Stamp request for document <id> failed:
  401 Client Error: Unauthorized for url: .../generate-approved-stamp/
```

### The Fix — Stamp in the View, Not the Consumer

Call `generate_approved_stamp()` **in the `workflow-action` view** using `request.auth`
(the CIA's live JWT), immediately after `advance_workflow_stage()` succeeds.

```python
# In the workflow-action POST view, after advance_workflow_stage() for action='approve':
if action == 'approve' and getattr(en, 'document_id', None):
    try:
        from apps.infrastructure.external.document_service_client import DocumentServiceClient
        client = DocumentServiceClient(auth_token=request.auth)
        client.generate_approved_stamp(
            document_id=str(en.document_id),
            approver_id=str(request.user_id),
            entity_type='engagement_notification',
            entity_id=str(pk),
        )
        logger.info('GAP 9: DRS stamp triggered for EngagementNotification %s by CIA %s', pk, request.user_id)
    except Exception as stamp_err:
        logger.error('GAP 9: DRS stamp failed for EngagementNotification %s: %s', pk, stamp_err)
```

**Key points:**
- `DocumentServiceClient(auth_token=request.auth)` — passes the CIA's JWT Bearer token
- Non-blocking: wrapped in `try/except` so a stamp failure never blocks the approval response
- The Kafka consumer's `_trigger_approved_stamp()` call can remain as-is — it will silently
  fail (401, swallowed), but the view-level stamp has already succeeded

### Pattern Summary

| Where to stamp | When to use | Auth |
|----------------|-------------|------|
| **In the view** (`workflow-action` POST) | Document approved via WO workflow | `request.auth` (user's live JWT) ✅ |
| **In the view** (direct approve action) | Document approved without WO (e.g. AuditProgram) | `request.auth` ✅ |
| **In the Kafka consumer** | ❌ Never — no JWT available, always 401 | — |

### Working Examples in Codebase

| Feature | File | Pattern |
|---------|------|---------|
| Declaration signing | `apps/api/views/declaration_views.py` | Stamps in sign view with `request.auth` |
| Audit Program approval | `apps/api/views/audit_program_views.py` | Stamps in approve view with `request.auth` |
| Engagement Notification | `apps/api/views/engagement_notification_views.py` | Stamps in `workflow-action` view with `request.auth` |

### Also Watch Out For: `document_id` Missing from List Serializer

The download button in the frontend gates on `notification.document_id`. If `document_id`
is missing from the **list serializer** (`EngagementNotificationListSerializer`), the field
will be `undefined` even though it is set in the DB — and the button will never appear.

**Always add `document_id` to both the list and detail serializers** for any model that
uses DRS PDF generation.

---

## Appendix: Stamp Overlay Dimensions (for template designers)

```
┌────────────────────────── A4 Page (210mm wide) ────────────────────────────┐
│                                                                             │
│  ←  Document body lives here — NO content below 60mm from bottom  →        │
│                                                                             │
│─────────────────── Separator line at y=42mm from bottom ───────────────────│
│  "Digitally approved – YYYY-MM-DD HH:MM UTC"   (y=44mm, 6.5pt Helvetica)   │
│                                                                             │
│  ┌─────────────┐                         ┌──────────────────────────────┐  │
│  │  QR Code    │                         │   CIA Signature Image        │  │
│  │  30 × 30mm  │                         │   65 × 22mm                  │  │
│  │  x=15mm     │                         │   x = page_width − 82mm      │  │
│  │  y=8mm      │                         │   y = 8mm                    │  │
│  └─────────────┘                         └──────────────────────────────┘  │
│  ↑                                                                          │
│  y=0 (bottom edge of page)                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```
