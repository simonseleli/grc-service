# Document Records Service (DRS) — Upload Reference

> Comprehensive analysis of how document uploads work across FIMS services,
> based on the GRC service implementation (which has the **real, production client**)
> and the Corporate service (which has a **stub client — not yet implemented**).

---

## 1. Big Picture: FIMS Principle 2 — Delegate File Storage to DRS

All FIMS microservices follow this rule:

> **Never store files locally. Always delegate to the Document Records Service.**

Each service (GRC, Corporate, IAM, etc.) stores only a **UUID reference** (`document_id`) in its own database. The actual file bytes, metadata, versioning, and download URLs all live in DRS.

```
┌──────────────────┐                        ┌───────────────────────────┐
│   GRC Service    │                        │  Document Records Service │
│                  │  ① POST /documents/    │                           │
│  evidence_       │ ──────────────────────▶│  Creates document record  │
│  attachments =   │  ← returns doc UUID    │  Stores metadata          │
│  [uuid1, uuid2]  │                        │                           │
│  (JSONField)     │  ② POST /{id}/upload/  │                           │
│                  │ ──────────────────────▶│  Stores the actual file   │
│                  │                        │  (S3 / local media)       │
│                  │  ③ GET /{id}/download/ │                           │
│   Frontend       │ ──────────────────────▶│  Streams file to browser  │
└──────────────────┘                        └───────────────────────────┘
```

---

## 2. The DRS Client — `DocumentServiceClient`

**Location:** `grc-service/apps/infrastructure/external/document_service_client.py`

This is the **authoritative, fully-implemented client** used by GRC. Corporate's client (`corporate-service/apps/infrastructure/external/document_client.py`) is a **stub** — it logs debug messages and returns `None`. If Corporate ever needs real DRS integration, it must adopt GRC's client pattern.

### Factory function (always use this):

```python
from apps.infrastructure.external import get_document_client

client = get_document_client(auth_token=auth_token)
```

`auth_token` is the user's JWT token, extracted from the request:

```python
auth_header = request.META.get('HTTP_AUTHORIZATION', '')
token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
client = get_document_client(auth_token=token)
```

---

## 3. Upload Patterns

### Pattern A — Two-step (explicit control)

Used in: Working Papers creation (`working_paper_views.py`)

```python
# Step 1: Create document metadata
document = client.create_document(
    title="My Document Title",
    description="Human-readable description",
    document_type='audit_working_paper',   # must exist in DRS
    classification='confidential',          # 'open' | 'confidential'
    record_type='non_permanent',            # 'permanent' | 'non_permanent'
    retention_period=2555,                  # days (2555 = 7 years)
    metadata={
        'source_entity_id': str(entity.id),
        'service': 'grc-service',
        'module': 'working_papers',
    },
    tags=['audit', 'working-paper', entity.reference_number],
)
doc_id = document['id']

# Step 2: Upload the actual file
document = client.upload_file(
    document_id=doc_id,
    file_data=uploaded_file,        # Django InMemoryUploadedFile
    file_name=uploaded_file.name
)
```

Use this pattern when:
- You need to handle step 1 and step 2 failures separately
- You may want to create a metadata-only document first (no file yet)
- You need to log each step individually

### Pattern B — One-shot (convenience)

Used in: Risk Assessment evidence (`risk_assessment_views.py`), Working Paper evidence

```python
document = client.create_document_with_file(
    title=title,
    description=description,
    file_data=uploaded_file,
    file_name=uploaded_file.name,
    document_type='audit_working_paper',
    classification='confidential',
    record_type='non_permanent',
    retention_period=2555,
    metadata={
        'risk_assessment_id': str(assessment.id),
        'service': 'grc-service',
        'module': 'risk_assessment_evidence',
    },
    tags=['audit', 'evidence', 'risk-assessment'],
)
new_doc_id = str(document['id'])
```

`create_document_with_file()` calls `create_document()` then `upload_file()` internally.
If the file upload fails after the document was created, it re-raises `DocumentServiceError`.

---

## 4. Retrieving Documents

### Get metadata for a single document:

```python
doc = client.get_document(str(document_id))
# Returns dict with: id, title, file_name, file_size, created_at, created_by, status, ...
```

### Get download URL (generate, don't store):

```python
url = client.get_download_url(str(document_id))
# Returns: '/api/v1/documents/{id}/download/'
# This is a relative path — prepend the DRS base URL if needed externally
```

### List all evidence for a GRC entity (fetching each UUID in a loop):

```python
doc_ids = assessment.evidence_attachments or []  # JSONField list of UUIDs

documents = []
for did in doc_ids:
    try:
        doc = client.get_document(str(did))
        doc['download_url'] = client.get_download_url(str(did))
        # Normalize field names for frontend EvidenceAttachment type:
        doc['document_id'] = doc.get('id', '')
        doc['filename'] = doc.get('title') or doc.get('file_name') or doc.get('filename') or ''
        documents.append(doc)
    except DocumentServiceError:
        # Document deleted in DRS — include stub so list doesn't break
        documents.append({
            'id': str(did),
            'document_id': str(did),
            'filename': '(unavailable)',
            'status': 'missing',
            'download_url': None,
        })
```

---

## 5. DRS API Endpoints

All routed through the API gateway, base: `http://document-records-service:8001`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/documents/` | Create document metadata → returns `{data: {id, ...}}` |
| `POST` | `/api/v1/documents/{id}/upload/` | Upload file to document → `multipart/form-data`, field: `file` |
| `GET` | `/api/v1/documents/{id}/` | Get document metadata |
| `GET` | `/api/v1/documents/{id}/download/` | Stream/download the file |
| `GET` | `/api/v1/documents/{id}/preview/` | Inline preview (PDF, images) |
| `POST` | `/api/v1/documents/{id}/versions/` | Create a new version |
| `GET` | `/api/v1/documents/{id}/versions/` | List version history |
| `POST` | `/api/v1/documents/{id}/generate-approved-stamp/` | Embed CIA stamp + QR on PDF |
| `DELETE` | `(not via client)` | GRC only detaches — never deletes from DRS |

**Response envelope:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "...",
    "file_name": "...",
    "file_size": 12345,
    "document_type": "audit_working_paper",
    "classification": "confidential",
    "status": "draft",
    "created_at": "...",
    "created_by": "user-uuid"
  }
}
```

---

## 6. Document Type Codes

These must exist as seeded records in DRS. GRC uses:

| `document_type` code | Used for |
|----------------------|----------|
| `audit_working_paper` | Working papers, risk assessment evidence, working paper evidence |
| `audit_meeting_minutes` | Audit meeting minutes files |
| `audit_meeting_attendance` | Attendance sheet files |

> **⚠️ Important:** If `document_type` doesn't exist in DRS, the `POST /api/v1/documents/` call returns 400. Add new types in DRS's seeder/admin before using them from GRC.

---

## 7. Classification & Retention

| Field | GRC Value | Meaning |
|-------|-----------|---------|
| `classification` | `'confidential'` | All audit documents are confidential |
| `record_type` | `'non_permanent'` | Audit records are not permanent |
| `retention_period` | `2555` days | 7 years (audit regulatory requirement) |

---

## 8. How GRC Stores References

GRC **never stores the file** — only UUID references:

| GRC Entity | Storage field | Field type |
|---|---|---|
| `RiskAssessment` | `evidence_attachments` | `JSONField(default=list)` — list of UUID strings |
| `WorkingPaper` | `document_id` (main file) + `evidence_attachments` | `UUIDField` + `JSONField` |
| `AuditMeeting` | `minutes_document_id`, `attendance_document_id` | `UUIDField` each |

Adding a reference (atomic, prevents lost updates):

```python
from django.db import transaction

with transaction.atomic():
    assessment = RiskAssessment.objects.select_for_update().get(pk=pk)
    attachments = list(assessment.evidence_attachments or [])
    if new_doc_id not in attachments:
        attachments.append(new_doc_id)
    assessment.evidence_attachments = attachments
    assessment.save(update_fields=['evidence_attachments'])
```

Removing a reference (detach only — DRS record survives):

```python
with transaction.atomic():
    assessment = RiskAssessment.objects.select_for_update().get(pk=pk)
    attachments = list(assessment.evidence_attachments or [])
    attachments.remove(str(document_id))
    assessment.evidence_attachments = attachments
    assessment.save(update_fields=['evidence_attachments'])
```

---

## 9. Error Handling

```python
from apps.infrastructure.external import DocumentServiceError

try:
    document = client.create_document_with_file(...)
except DocumentServiceError as e:
    return error_response(
        message="Failed to upload file to Document Records Service",
        code="DOCUMENT_SERVICE_ERROR",
        status_code=status.HTTP_502_BAD_GATEWAY,
    )
```

`DocumentServiceError` is raised for:
- HTTP errors from DRS (4xx, 5xx)
- Network/connection failures (`requests.exceptions.RequestException`)

Use `502 Bad Gateway` (not 500) — the failure is DRS's fault, not GRC's.

---

## 10. Frontend — `grcService.ts`

Evidence-related functions (all go through the API gateway → GRC → DRS):

```typescript
// List evidence for a risk assessment
fetchEvidence(assessmentId: string): Promise<EvidenceAttachment[]>
// → GET /api/v1/grc/audit/risk-assessments/{id}/evidence/

// Upload evidence (multipart/form-data, field: 'file')
uploadEvidence(assessmentId: string, file: File, meta?: { description?: string }): Promise<EvidenceAttachment>
// → POST /api/v1/grc/audit/risk-assessments/{id}/evidence/

// Detach evidence (does not delete from DRS)
deleteEvidence(assessmentId: string, documentId: string): Promise<void>
// → DELETE /api/v1/grc/audit/risk-assessments/{id}/evidence/{documentId}/
```

Same pattern for working papers:

```typescript
fetchWorkingPaperEvidence(paperId: string): Promise<EvidenceAttachment[]>
uploadWorkingPaperEvidence(paperId: string, file: File, meta?: ...): Promise<EvidenceAttachment>
deleteWorkingPaperEvidence(paperId: string, documentId: string): Promise<void>
```

**Multi-file edge case (Audit Meetings):** Minutes and attendance files are sent as part of a regular `PATCH` to the meeting endpoint using `multipart/form-data` with fields `minutes_file` and `attendance_file`. The GRC view handles DRS upload internally.

---

## 11. Frontend — `EvidenceAttachmentSection` Component

**Location:** `frontend/apps/staff-portal/src/components/grc/EvidenceAttachmentSection.tsx`

Reusable component that handles the full evidence lifecycle:

```tsx
<EvidenceAttachmentSection
  entityType="risk-assessment"   // or "working-paper"
  entityId={item.id}
  readonly={item.status === 'approved' || !canConductRiskAssessment}
/>
```

| Prop | Effect |
|------|--------|
| `entityType="risk-assessment"` | Uses `fetchEvidence` / `uploadEvidence` / `deleteEvidence` |
| `entityType="working-paper"` | Uses `fetchWorkingPaperEvidence` / etc. |
| `readonly={true}` | Hides "Upload Evidence" button and trash icons — view only |
| `readonly={false}` (default) | Full upload/delete UI |

**Auto-fetch:** On mount (when `entityId` is truthy), fetches the list from GRC.
**Upload flow:** Click button → hidden `<input type="file">` → `uploadEvidence()` → `react-query` cache invalidated → list refreshes.
**Stale time:** 5 minutes (won't re-fetch on every modal open if recently fetched).

---

## 12. Permission Summary

| Action | GRC Permission | Notes |
|--------|---------------|-------|
| View evidence list (GET) | `grc:risk_assessment:conduct` OR `grc:risk_assessment:review` | Both IA and CIA can view |
| Upload evidence (POST) | `grc:risk_assessment:conduct` | IA only |
| Delete/detach evidence (DELETE) | `grc:risk_assessment:conduct` | IA only |
| Any action on `approved` assessment | Nobody | Backend returns 400 `ASSESSMENT_APPROVED` |

Frontend enforces this via `readonly={!canConductRiskAssessment}` on `EvidenceAttachmentSection`.

---

## 13. S2S (Service-to-Service) Calls

For Kafka-triggered or background operations where there is no user JWT:

```python
from apps.infrastructure.external.document_service_client import DocumentServiceClient
from django.conf import settings

service_token = getattr(settings, 'SERVICE_TO_SERVICE_TOKEN', None)
client = DocumentServiceClient(auth_token=None)

# For stamp generation, pass service_token explicitly:
result = client.generate_approved_stamp(
    document_id=str(doc_id),
    approver_id=str(approver_id),
    entity_type='audit_report',
    entity_id=str(entity_id),
    service_token=service_token,
)
```

The `generate_approved_stamp()` method sends an `X-Service-Token` header (not `Authorization: Bearer`).

---

## 14. Corporate Service — Status

The Corporate `DocumentClient` at `corporate-service/apps/infrastructure/external/document_client.py` is a **Phase 1 stub**:

```python
def upload(self, file_content, filename, metadata=None):
    logger.debug("DocumentClient.upload stub: %s", filename)
    return None  # ← does nothing
```

Corporate instead stores `document_id` as a `UUIDField` on entities — the expectation is that the document was already uploaded separately (e.g., via the IAM client portal or a dedicated upload endpoint), and the UUID is passed in the request body. **No actual file upload integration exists in Corporate today.**

If Corporate needs real DRS upload in the future, copy GRC's `document_service_client.py` pattern.

---

## 15. Key Gotchas

1. **Don't omit `Content-Type` on upload** — `requests` sets it automatically for multipart; manually adding `Content-Type: application/json` breaks the file upload.
2. **`select_for_update()` is mandatory** when appending/removing from `evidence_attachments` — concurrent requests can cause list corruption without it.
3. **Detach ≠ Delete** — `DELETE /evidence/{doc_id}/` only removes the UUID from `evidence_attachments`. The DRS document survives. Audit records must not be permanently deleted.
4. **`create_document()` returns `data['data']`** — the DRS envelope wraps inside `{"success": true, "data": {...}}`. The client unwraps it for you; `document['id']` is the UUID directly.
5. **DRS `document_type` must be pre-seeded** — check DRS admin/fixtures before using new type codes.
6. **Download URL is relative** — `client.get_download_url(id)` returns `/api/v1/documents/{id}/download/`. The frontend uses the API gateway base URL; service-to-service calls use the DRS base URL directly.
