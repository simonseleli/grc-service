# GAP 9 & GAP 12 — Implementation Guide

> **Author:** Implementation reference  
> **Date:** 2026-03-06  
> **Status:** Ready to implement  
> **Scope:** GRC Service + Document Records Service (backend) + Staff Portal (frontend)

---

## Table of Contents

1. [Pre-Implementation Audit — What Already Exists](#1-pre-implementation-audit--what-already-exists)
2. [GAP 9 — QR Code + Digital Signature on Approved Documents](#2-gap-9--qr-code--digital-signature-on-approved-documents)
   - [2.1 Architecture Decision](#21-architecture-decision)
   - [2.2 SRS Requirement Summary](#22-srs-requirement-summary)
   - [2.3 Documents That Get Stamped](#23-documents-that-get-stamped)
   - [2.4 Implementation Plan — Backend (DRS)](#24-implementation-plan--backend-drs)
   - [2.5 Implementation Plan — Backend (GRC)](#25-implementation-plan--backend-grc)
   - [2.6 Implementation Plan — Frontend](#26-implementation-plan--frontend)
   - [2.7 File-by-File Checklist](#27-file-by-file-checklist)
3. [GAP 12 — Risk Management System Integration](#3-gap-12--risk-management-system-integration)
   - [3.1 What Is Implementable Now vs. Phase 2](#31-what-is-implementable-now-vs-phase-2)
   - [3.2 SRS Requirement Summary](#32-srs-requirement-summary)
   - [3.3 Phase 1 (Now): Kafka Event Publishing](#33-phase-1-now-kafka-event-publishing)
   - [3.4 File-by-File Checklist](#34-file-by-file-checklist)
4. [Implementation Order](#4-implementation-order)
5. [Testing Checklist](#5-testing-checklist)

---

## 1. Pre-Implementation Audit — What Already Exists

### Document Records Service (DRS)

| Capability | Status | Location |
|---|---|---|
| `qrcode[pil]` library | ✅ Installed | `requirements.txt` |
| `PyPDF2==3.0.1` (PDF merge/overlay) | ✅ Installed | `requirements.txt` |
| `reportlab==4.0.7` (PDF canvas drawing) | ✅ Installed | `requirements.txt` |
| `Pillow==10.1.0` (image processing) | ✅ Installed | `requirements.txt` |
| `_generate_qr_image(payload, format)` | ✅ Implemented | `apps/api/views/document_download_view.py:468` |
| `GET /api/v1/documents/{uuid}/qr/` | ✅ Endpoint exists | `apps/api/urls/documents.py` |
| `DocumentSignature` model | ✅ Full model | `apps/infrastructure/persistence/models.py:572` |
| Signature API (request/upload/validate/list) | ✅ Full API | `apps/api/views/signature_views.py` |
| `IAMClient.get_user_profile(user_id)` | ✅ Exists | `apps/core/iam_client.py:76` — calls `GET /users/{uuid}/` |
| `Document.qr_code_path` / `qr_code_data` | ✅ DB fields | `apps/infrastructure/persistence/models.py:218–219` |

### IAM Service

| Capability | Status | Location |
|---|---|---|
| `signature` ImageField on User model | ✅ Exists | `apps/users/models.py` |
| `save_signature` endpoint (canvas → PNG) | ✅ Exists | `apps/users/views.py:54` |
| Signature URL returned in user profile | ✅ Via `/users/{uuid}/` | IAM user serializer includes `signature` URL |

### GRC Service

| Capability | Status | Location |
|---|---|---|
| `KafkaMessagingService` | ✅ Exists | `apps/infrastructure/services/messaging_service.py` |
| `publish_audit_finding_event()` | ✅ Exists | `messaging_service.py:182` |
| `AUDIT_FINDING_EVENTS` dict | ✅ Exists | `shared/constants/event_types.py` |
| `publish_event(event)` function | ✅ Exists | `apps/infrastructure/messaging/kafka_producer.py` |
| All event type dicts (MEMO, DECLARATION, REPORT…) | ✅ Exists | `shared/constants/event_types.py` |

### What Does NOT Exist (needs to be built)

| Item | Service | Description |
|---|---|---|
| `GenerateApprovedStampUseCase` | DRS | New use case: PDF + signature + QR overlay |
| `POST .../generate-approved-stamp/` | DRS | New endpoint that triggers the use case |
| DRS URL registration for new endpoint | DRS | Add path to `apps/api/urls/documents.py` |
| GRC → DRS HTTP client | GRC | New `DocumentRecordsClient` for making approved-stamp calls |
| Signal/hook after CIA approval | GRC | Wire DRS call on AuditMemo/AuditProgram/Declaration approval |
| `FINDING_FINALIZED` event type | GRC | Add to `shared/constants/event_types.py` |
| `publish_finding_finalized_event()` | GRC | Extended payload with risk data for Risk Mgmt |
| Wire finding finalized on approval | GRC | Call event publisher from finding approval view |
| Frontend "Download Approved Document" | Frontend | Per-entity button when `approved_document_url` is present |

---

## 2. GAP 9 — QR Code + Digital Signature on Approved Documents

### 2.1 Architecture Decision

**Following Principle 2 (Centralized Domain Services):**

- **Document Records Service** owns all document rendering, stamping, and file manipulation.
- **GRC Service** delegates: after CIA approval of a relevant entity, GRC calls DRS to stamp the underlying document.
- **IAM Service** owns the signature image. DRS fetches it directly (it already has an IAM client with caching).
- GRC does NOT generate QR codes or manipulate PDFs — it only triggers DRS and stores the returned `stamped_document_url`.

```
CIA approves AuditMemo / Declaration / AuditProgram / AuditReport
       │
       ▼
GRC signals post_save or approval view
       │
       ▼
GRC calls: POST /api/v1/documents/{drs_document_id}/generate-approved-stamp/
           { "approver_id": "<cia_user_id>", "entity_type": "audit_memo", "entity_id": "<grc_entity_id>" }
       │
       ▼
DRS GenerateApprovedStampUseCase:
  1. Fetch approver signature PNG from IAM: GET /users/{approver_id}/
  2. Generate QR code pointing to: https://fims.internal/verify/{reference_number}
  3. Use reportlab to draw: signature image (bottom-right) + QR (bottom-left) on a new canvas
  4. Use PyPDF2 to overlay canvas onto last page of existing PDF
  5. Save as new document version (version +1)
  6. Return: { stamped_document_url, version, qr_data }
       │
       ▼
GRC stores stamped_document_url on entity (e.g. AuditMemo.stamped_document_url)
       │
       ▼
Frontend: "Download Approved Document" button → fetches stamped_document_url
```

### 2.2 SRS Requirement Summary

From `AUDT2_ext.md`:

- **Step 11 (Survey phase):** "CIA approve (Signature and QR Code embedded automatically)"  
- **Requirement 38:** "generate the Approved Internal Audit Report, Signed Declaration of Independence/Conflict of Interest Form"  
- **SRS 1.8.1:** Applies to Engagement Notification approval (which maps to AuditProgram in our model)

### 2.3 Documents That Get Stamped

| GRC Entity | DRS Document field | Trigger |
|---|---|---|
| `AuditMemo` | `AuditMemo.document_id` (FK to DRS) | When `status → approved` (step 4 in memo workflow) |
| `DeclarationOfIndependence` | `DeclarationOfIndependence.document_id` | When all team members have signed (all `is_signed=True`) |
| `AuditProgram` | `AuditProgram.document_id` | When `status → approved` (CIA approves EN) |
| `AuditReport` | `AuditReport.document_id` | When `status → approved` |

> **Note:** `AuditSurvey` and `RCM` do NOT get stamped — they are internal working documents, not formal output documents per the SRS.

### 2.4 Implementation Plan — Backend (DRS)

#### Step 1 — New Use Case: `GenerateApprovedStampUseCase`

**File:** `apps/core/use_cases/document/generate_approved_stamp.py` *(new file)*

```python
"""
Use Case: Generate an approved stamp (signature + QR code) on a document PDF.
Called by GRC service after CIA approval of formal output documents.
"""
import io
import requests
from typing import Optional

from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

from apps.core.iam_client import IAMClient
from apps.core.services.document_service import DocumentService
from apps.api.views.document_download_view import DocumentQRView


class GenerateApprovedStampUseCase:
    """
    Fetches CIA signature from IAM, generates QR code, overlays both
    onto the last page of the document PDF, and saves a new version.
    """

    def __init__(self, document_repo, iam_client: IAMClient):
        self.document_repo = document_repo
        self.iam_client = iam_client

    def execute(
        self,
        document_id: str,
        approver_id: str,
        entity_type: str,     # e.g. 'audit_memo'
        entity_id: str,       # GRC entity UUID (for verification URL)
        verify_base_url: str, # e.g. https://fims.internal
    ) -> dict:
        """
        Returns:
            {
                "version": <int>,
                "stamped_file_path": <str>,
                "qr_data": <str>,
            }
        """
        document = self.document_repo.get_by_id(document_id)
        if not document or not document.file_path:
            raise ValueError("Document not found or has no file")

        # 1. Get approver signature from IAM
        user_profile = self.iam_client.get_user_profile(approver_id)
        signature_url = user_profile.get('signature') if user_profile else None

        # 2. Generate QR code bytes
        qr_payload = f"{verify_base_url}/verify/{entity_type}/{entity_id}/"
        qr_bytes, _ = DocumentQRView._generate_qr_image(qr_payload, 'png')

        # 3. Build overlay PDF using reportlab
        overlay_buffer = io.BytesIO()
        c = rl_canvas.Canvas(overlay_buffer, pagesize=A4)
        page_width, page_height = A4

        # QR code — bottom-left corner
        qr_img = Image.open(io.BytesIO(qr_bytes))
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        c.drawImage(
            qr_buffer, x=15*mm, y=10*mm,
            width=30*mm, height=30*mm,
            preserveAspectRatio=True,
        )

        # Signature — bottom-right corner (if available)
        if signature_url:
            try:
                sig_response = requests.get(signature_url, timeout=5)
                if sig_response.status_code == 200:
                    sig_buffer = io.BytesIO(sig_response.content)
                    c.drawImage(
                        sig_buffer, x=page_width - 80*mm, y=10*mm,
                        width=60*mm, height=25*mm,
                        preserveAspectRatio=True,
                        mask='auto',
                    )
            except Exception:
                pass  # Signature unavailable — proceed without it

        # Approval text line
        from django.utils import timezone
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(
            15*mm, 8*mm,
            f"Digitally approved · {entity_type.replace('_', ' ').title()} · "
            f"{timezone.now().strftime('%Y-%m-%d %H:%M UTC')}"
        )

        c.save()
        overlay_buffer.seek(0)

        # 4. Merge overlay onto last page of existing PDF
        existing_pdf = PdfReader(document.file_path)
        overlay_pdf = PdfReader(overlay_buffer)
        writer = PdfWriter()

        for i, page in enumerate(existing_pdf.pages):
            if i == len(existing_pdf.pages) - 1:
                page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)

        # 5. Write stamped PDF to a new version path
        import os
        base, ext = os.path.splitext(document.file_path)
        stamped_path = f"{base}_approved_v{document.version + 1}{ext}"
        with open(stamped_path, 'wb') as out_f:
            writer.write(out_f)

        return {
            "version": document.version + 1,
            "stamped_file_path": stamped_path,
            "qr_data": qr_payload,
        }
```

#### Step 2 — New API View

**File:** `apps/api/views/document_stamp_view.py` *(new file)*

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.api.permissions_jwt import IsAuthenticated
from apps.core.iam_client import IAMClient
from apps.core.use_cases.document.generate_approved_stamp import GenerateApprovedStampUseCase
from apps.infrastructure.persistence.repositories.document_repository_impl import DocumentRepositoryImpl
from django.conf import settings


class GenerateApprovedStampView(APIView):
    """
    POST /api/v1/documents/{document_id}/generate-approved-stamp/

    Body:
        {
            "approver_id": "<cia_user_id>",
            "entity_type": "audit_memo",   // audit_memo | declaration | audit_program | audit_report
            "entity_id": "<grc_entity_uuid>"
        }

    Returns:
        {
            "stamped_document_url": "<download_url>",
            "version": <int>,
            "qr_data": "<verification_url>"
        }

    Called by GRC Service after CIA approves a formal output document.
    The approver's signature is fetched from IAM Service automatically.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        approver_id = request.data.get('approver_id')
        entity_type = request.data.get('entity_type')
        entity_id = request.data.get('entity_id')

        if not all([approver_id, entity_type, entity_id]):
            return Response(
                {"error": "approver_id, entity_type, and entity_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            use_case = GenerateApprovedStampUseCase(
                document_repo=DocumentRepositoryImpl(),
                iam_client=IAMClient(),
            )
            result = use_case.execute(
                document_id=str(document_id),
                approver_id=str(approver_id),
                entity_type=entity_type,
                entity_id=str(entity_id),
                verify_base_url=getattr(settings, 'FIMS_VERIFY_BASE_URL', 'https://fims.internal'),
            )

            stamped_url = request.build_absolute_uri(
                f"/api/v1/documents/{document_id}/download/?version={result['version']}"
            )

            return Response({
                "stamped_document_url": stamped_url,
                "version": result["version"],
                "qr_data": result["qr_data"],
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "Failed to generate approved stamp", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
```

#### Step 3 — Register URL

**File:** `apps/api/urls/documents.py` — add one line inside the `urlpatterns` list:

```python
from apps.api.views.document_stamp_view import GenerateApprovedStampView

# Add after the existing approve/status paths:
path('<uuid:document_id>/generate-approved-stamp/', GenerateApprovedStampView.as_view(), name='document-generate-approved-stamp'),
```

#### Step 4 — DRS Settings

**File:** `config/settings.py` — add:

```python
# GAP 9: Approved stamp verification base URL
FIMS_VERIFY_BASE_URL = env('FIMS_VERIFY_BASE_URL', default='https://fims.internal')
```

### 2.5 Implementation Plan — Backend (GRC)

#### Step 1 — New DRS HTTP Client

**File:** `apps/infrastructure/external/document_records_client.py` *(new file)*

```python
"""
HTTP client for Document Records Service.
GRC delegates document stamping to DRS per FIMS Principle 2.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DRS_BASE_URL = getattr(settings, 'DOCUMENT_SERVICE_URL', 'http://document-records-service:8000')


class DocumentRecordsClient:
    """Thin HTTP client for calling DRS approved-stamp endpoint."""

    STAMP_TIMEOUT = 30  # seconds — PDF manipulation can take time

    def generate_approved_stamp(
        self,
        drs_document_id: str,
        approver_id: str,
        entity_type: str,
        entity_id: str,
        jwt_token: str,
    ) -> dict:
        """
        Calls POST /api/v1/documents/{id}/generate-approved-stamp/ on DRS.

        Returns:
            { stamped_document_url, version, qr_data }
        Raises:
            RuntimeError on non-2xx response.
        """
        url = f"{DRS_BASE_URL}/api/v1/documents/{drs_document_id}/generate-approved-stamp/"
        headers = {"Authorization": f"Bearer {jwt_token}"}
        payload = {
            "approver_id": approver_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.STAMP_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"DRS stamp request failed for {entity_type}/{entity_id}: {e}")
            raise RuntimeError(f"Failed to generate approved stamp: {e}") from e
```

#### Step 2 — Add `stamped_document_url` Field to Affected Models

**File:** `apps/core/models/audit_entities.py`

Add the following field to each of the 4 stamped models:

```python
# On AuditMemo:
stamped_document_url = models.URLField(max_length=500, blank=True, null=True,
    help_text="URL to the approved PDF with embedded signature and QR code")

# On DeclarationOfIndependence:
stamped_document_url = models.URLField(max_length=500, blank=True, null=True)

# On AuditProgram:
stamped_document_url = models.URLField(max_length=500, blank=True, null=True)

# On AuditReport (already exists — check; if not, add):
stamped_document_url = models.URLField(max_length=500, blank=True, null=True)
```

> **Migration:** `python manage.py makemigrations grc` — generates one migration for all 4 models.

#### Step 3 — Wire the Stamp Call on Approval

For each entity, find the approval view/action and add the DRS call after status update.

**Pattern to follow (same in all 4 places):**

```python
from apps.infrastructure.external.document_records_client import DocumentRecordsClient

# Inside the approval action, AFTER status is saved:
if instance.document_id:  # Only if entity has a DRS document
    try:
        client = DocumentRecordsClient()
        result = client.generate_approved_stamp(
            drs_document_id=str(instance.document_id),
            approver_id=str(request.user.id),
            entity_type='audit_memo',  # change per entity
            entity_id=str(instance.id),
            jwt_token=request.auth,    # forward the request JWT
        )
        instance.stamped_document_url = result.get('stamped_document_url')
        instance.save(update_fields=['stamped_document_url'])
    except RuntimeError as e:
        logger.warning(f"Stamp generation failed (non-blocking): {e}")
        # Non-blocking — approval still succeeds even if stamping fails
```

**Where to wire it:**

| Entity | File | Method/View | Trigger |
|---|---|---|---|
| `AuditMemo` | `apps/api/views/audit_memo_views.py` | Action `approve` | `status → approved` |
| `DeclarationOfIndependence` | `apps/api/views/declaration_views.py` | After last `is_signed=True` | All team members signed |
| `AuditProgram` | `apps/api/views/audit_program_views.py` | Action `approve` | `status → approved` |
| `AuditReport` | `apps/api/views/audit_report_views.py` | Action `approve` | `status → approved` |

#### Step 4 — Expose `stamped_document_url` in Serializers

Add the field to the serializer read-only fields for each entity:

```python
# In each entity's serializer:
stamped_document_url = serializers.URLField(read_only=True, allow_null=True)
```

### 2.6 Implementation Plan — Frontend

#### Step 1 — Update Service Functions

**File:** `frontend/apps/staff-portal/src/services/grcService.ts`

The `stamped_document_url` is now returned in the entity detail response — no new service call needed. It's just a URL that opens in a new tab.

#### Step 2 — Add "Download Approved Document" Button

Add this to the detail view/page of each affected entity, conditionally rendered when `stamped_document_url` is set:

```tsx
{item.stamped_document_url && (
  <a
    href={item.stamped_document_url}
    target="_blank"
    rel="noopener noreferrer"
    download
  >
    <Button variant="outline" size="sm">
      <FileDown className="mr-2 h-4 w-4" />
      Download Approved Document
    </Button>
  </a>
)}
```

**Where to add it:**

| Entity | Page File |
|---|---|
| `AuditMemo` | `AuditMemoDetailPage.tsx` |
| `DeclarationOfIndependence` | `AuditMemoDetailPage.tsx` (declarations are listed there) or `CreateDeclarationDialog.tsx` detail view |
| `AuditProgram` | `AuditProgramDetailPage.tsx` (or tab in engagement detail) |
| `AuditReport` | `AuditReportDetailPage.tsx` |

#### Step 3 — Add `stamped_document_url` to Types

**File:** `frontend/apps/staff-portal/src/types/grc.ts`

Add `stamped_document_url?: string | null` to `AuditMemo`, `DeclarationOfIndependence`, `AuditProgram`, and `AuditReport` interfaces.

### 2.7 File-by-File Checklist

**DRS:**
- [ ] `apps/core/use_cases/document/generate_approved_stamp.py` — new file
- [ ] `apps/api/views/document_stamp_view.py` — new file
- [ ] `apps/api/urls/documents.py` — add 1 path
- [ ] `config/settings.py` — add `FIMS_VERIFY_BASE_URL`
- [ ] `.env.example` — add `FIMS_VERIFY_BASE_URL`

**GRC:**
- [ ] `apps/infrastructure/external/document_records_client.py` — new file
- [ ] `apps/core/models/audit_entities.py` — add `stamped_document_url` to 4 models
- [ ] Run `makemigrations` + `migrate`
- [ ] `apps/api/views/audit_memo_views.py` — wire stamp call on approve
- [ ] `apps/api/views/declaration_views.py` — wire stamp call on last signature
- [ ] `apps/api/views/audit_program_views.py` — wire stamp call on approve
- [ ] `apps/api/views/audit_report_views.py` — wire stamp call on approve
- [ ] 4 serializers — add `stamped_document_url` read-only field
- [ ] `config/settings.py` — add `DOCUMENT_SERVICE_URL`
- [ ] `.env.example` — add `DOCUMENT_SERVICE_URL`

**Frontend:**
- [ ] `src/types/grc.ts` — add `stamped_document_url` to 4 type interfaces
- [ ] `AuditMemoDetailPage.tsx` — download button
- [ ] Declaration section — download button  
- [ ] `AuditProgramDetailPage.tsx` — download button
- [ ] `AuditReportDetailPage.tsx` — download button

---

## 3. GAP 12 — Risk Management System Integration

### 3.1 What Is Implementable Now vs. Phase 2

| Phase | What | Status |
|---|---|---|
| **Now (Phase 1)** | GRC publishes `finding.finalized` Kafka events with full risk payload | ✅ Implementable — infra already exists |
| **Now (Phase 1)** | Add `FINDING_FINALIZED` + `FINDING_APPROVED` event types to constants | ✅ Trivial add |
| **Phase 2** | Risk Management module consumes the events | ⏳ Requires Risk Mgmt module to exist |
| **Phase 2** | GRC imports org risk register from Risk Mgmt | ⏳ Requires Risk Mgmt API to exist |
| **Phase 2** | Bidirectional sync | ⏳ Full Phase 2 |

**Why publish now without a consumer?**  
The Kafka topic already exists. Publishing events from day 1 means:
1. No GRC changes needed when Risk Mgmt is built later
2. Historical events are available for replay if the consumer uses offset storage
3. Zero risk — unused events are silently discarded by Kafka

### 3.2 SRS Requirement Summary

From `AUDT2_ext.md` Requirement 41:

> "Risk Management System Integration: Two-way sync with the Risk Assurance and Quality Management System to feed audit findings as risks and to pull the organizational risk register for audit planning."

**Phase 1 implements:** "feed audit findings as risks"  
**Phase 2 implements:** "pull the organizational risk register for audit planning"

### 3.3 Phase 1 (Now): Kafka Event Publishing

#### Step 1 — Add Event Types to Constants

**File:** `shared/constants/event_types.py`

Add to the existing `AUDIT_FINDING_EVENTS` dict:

```python
AUDIT_FINDING_EVENTS = {
    'FINDING_CREATED':   'grc.audit.finding.created',
    'FINDING_UPDATED':   'grc.audit.finding.updated',
    'FINDING_ESCALATED': 'grc.audit.finding.escalated',
    'FINDING_RESOLVED':  'grc.audit.finding.resolved',
    'FINDING_CLOSED':    'grc.audit.finding.closed',
    # GAP 12 — Risk Management integration
    'FINDING_FINALIZED': 'grc.audit.finding.finalized',  # When finding is approved/closed with full context
    'FINDING_APPROVED':  'grc.audit.finding.approved',   # Alias — when audit report is approved
}
```

#### Step 2 — New Kafka Event Dataclass

**File:** `apps/infrastructure/messaging/events.py` (or wherever `AuditFindingCreatedEvent` is defined — find the file)

```python
@dataclass
class AuditFindingFinalizedEvent:
    """
    Published when an audit finding is finalized (audit report approved).
    Consumed by: Risk Management System (Phase 2) to feed findings as org risks.
    """
    finding_id: str
    reference_number: str
    title: str
    description: str
    finding_type: str           # e.g. 'compliance', 'financial', 'operational'
    severity: str               # e.g. 'high', 'medium', 'low'
    risk_rating_id: str
    risk_rating_name: str
    engagement_id: str
    engagement_reference: str
    auditable_entity_id: str
    auditable_entity_name: str
    auditable_entity_code: str
    fiscal_year_id: str
    fiscal_year_code: str
    recommendation_count: int
    resolved_at: Optional[str]  # ISO datetime string
    user_id: str                # CIA user who approved

    topic: str = 'grc.audit.finding.events'
    event_type: str = 'grc.audit.finding.finalized'
    version: str = '1.0'
```

#### Step 3 — Add Publisher Method to Messaging Service

**File:** `apps/infrastructure/services/messaging_service.py`

Add a new method to `KafkaMessagingService`:

```python
def publish_finding_finalized_event(
    self,
    finding,        # AuditFinding model instance
    user_id: str,
) -> bool:
    """
    Publish a finding.finalized event for consumption by the Risk Management System.
    Called when an audit report containing this finding is approved.

    Payload includes full risk context to allow the Risk Mgmt module
    to create a corresponding org risk entry without further GRC API calls.
    """
    try:
        engagement = finding.engagement if hasattr(finding, 'engagement') else None
        entity = (
            engagement.auditable_entity
            if engagement and hasattr(engagement, 'auditable_entity')
            else None
        )
        fy = (
            engagement.audit_plan.fiscal_year
            if engagement and hasattr(engagement, 'audit_plan') and engagement.audit_plan
            else None
        )

        event = AuditFindingFinalizedEvent(
            finding_id=str(finding.id),
            reference_number=finding.reference_number or '',
            title=finding.title or '',
            description=finding.description or '',
            finding_type=finding.finding_type or '',
            severity=str(finding.severity) if finding.severity else '',
            risk_rating_id=str(finding.risk_rating.id) if finding.risk_rating else '',
            risk_rating_name=finding.risk_rating.name if finding.risk_rating else '',
            engagement_id=str(engagement.id) if engagement else '',
            engagement_reference=engagement.reference_number if engagement else '',
            auditable_entity_id=str(entity.id) if entity else '',
            auditable_entity_name=entity.name if entity else '',
            auditable_entity_code=entity.code if entity else '',
            fiscal_year_id=str(fy.id) if fy else '',
            fiscal_year_code=fy.year_code if fy else '',
            recommendation_count=finding.recommendations.count() if hasattr(finding, 'recommendations') else 0,
            resolved_at=finding.resolved_at.isoformat() if getattr(finding, 'resolved_at', None) else None,
            user_id=str(user_id),
        )

        publish_event(event)
        logger.info(f"Published finding.finalized event for finding {finding.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish finding.finalized event: {e}")
        return False
```

#### Step 4 — Wire on Audit Report Approval

The correct trigger is: **when an `AuditReport` is approved**, because that's the formal closure of all findings within it.

**File:** `apps/api/views/audit_report_views.py`

Find the approve action and add:

```python
from apps.infrastructure.services.messaging_service import KafkaMessagingService

# After report.status = 'approved' and report.save():
messaging = KafkaMessagingService()
for finding in report.engagement.findings.filter(is_active=True):
    messaging.publish_finding_finalized_event(
        finding=finding,
        user_id=str(request.user.id),
    )
```

> **Why loop over all findings in the engagement?** The SRS says "feed audit findings as risks" — all findings in an approved report are finalized simultaneously.

### 3.4 File-by-File Checklist

**GRC:**
- [ ] `shared/constants/event_types.py` — add `FINDING_FINALIZED`, `FINDING_APPROVED` to `AUDIT_FINDING_EVENTS`
- [ ] `apps/infrastructure/messaging/events.py` — add `AuditFindingFinalizedEvent` dataclass
- [ ] `apps/infrastructure/services/messaging_service.py` — add `publish_finding_finalized_event()` method
- [ ] `apps/api/views/audit_report_views.py` — wire call in approve action

---

## 4. Implementation Order

```
1. GAP 12 — GRC side only (event types + publisher + wire)
   Reason: Pure GRC changes, no cross-service coordination, very low risk.
   Time: ~2 hours

2. GAP 9 Step 1 — DRS use case + view + URL
   Reason: DRS side is self-contained, can be developed and tested independently.
   Time: ~3–4 hours

3. GAP 9 Step 2 — GRC model fields + migrations + client
   Reason: Needs DRS endpoint to be working first for integration testing.
   Time: ~2 hours

4. GAP 9 Step 3 — Wire GRC approval views (4 entities)
   Reason: Requires the client from step 3 and the DRS endpoint from step 2.
   Time: ~2 hours

5. GAP 9 Step 4 — Frontend download buttons (4 entities)
   Reason: Needs the serializer fields to be exposed first.
   Time: ~1 hour
```

---

## 5. Testing Checklist

### GAP 9

- [ ] DRS: `POST /api/v1/documents/{uuid}/generate-approved-stamp/` with a real PDF document returns `stamped_document_url`
- [ ] DRS: Downloading `stamped_document_url` returns a PDF with QR code visible on the last page
- [ ] DRS: If approver has a signature in IAM, it appears bottom-right on the PDF
- [ ] DRS: If approver has no signature in IAM, stamp still succeeds (signature section is blank)
- [ ] GRC: Approving an AuditMemo (with a linked DRS document) populates `stamped_document_url` on the memo
- [ ] GRC: Approving an AuditProgram populates `stamped_document_url`
- [ ] GRC: Approving an AuditReport populates `stamped_document_url`
- [ ] GRC: If DRS stamp call fails, the approval action still completes (non-blocking)
- [ ] Frontend: "Download Approved Document" button appears only when `stamped_document_url` is set
- [ ] Frontend: Clicking the button downloads the stamped PDF

### GAP 12

- [ ] After `AuditReport` approval, a Kafka message appears on `grc.audit.finding.events` topic
- [ ] Message `event_type` is `grc.audit.finding.finalized`
- [ ] Message payload includes: `finding_id`, `reference_number`, `risk_rating_name`, `auditable_entity_name`, `fiscal_year_code`, `recommendation_count`
- [ ] If Kafka is down, the report approval still completes (event publishing is best-effort)
- [ ] Event is published once per finding (not duplicated)
