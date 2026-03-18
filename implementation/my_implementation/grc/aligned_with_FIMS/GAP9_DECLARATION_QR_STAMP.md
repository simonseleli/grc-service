# GAP 9 — Declaration of Independence: QR Code + Signature Stamping

**Status:** Partially implemented — signing works, PDF stamping does NOT activate
**SRS Requirements:** 16, 18, 38
**Affected model:** `DeclarationOfIndependence` (`grc_declaration_of_independence`)
**Investigated:** Full read of `document-records-service` source code — all confirmed facts below.

---

## What the SRS Requires

| SRS Req | Text |
|---|---|
| **Req 16** | "The system shall allow audit team members to sign the Declaration of Independence/Conflict of Interest Form prior to participation in audit activities." |
| **Req 18** | "The system shall **generate** the Approved Internal Audit Memo and **Signed Declaration of Independence/Conflict of Interest Form** as outputs of the process." |
| **Req 38** | "The system shall generate the... **Signed Declaration of Independence/Conflict of Interest Form**, and distribute them to stakeholders." |

The word **"generate"** means the system must produce an actual stamped PDF — not just a DB record with `is_signed=True`.

---

## What Is Currently Working ✅

When an auditor clicks **Sign**:

1. `is_signed = True` saved to DB
2. `signed_at = now()` saved
3. `status = 'signed'` saved
4. Kafka event published
5. Backend checks if **all** declarations for the engagement are now signed
6. If all signed → loops over declarations that have `document_id` set → calls DRS stamp

**Steps 1–5 work. Step 6 silently does nothing because `document_id` is always `null`.**

The stamp-trigger code in `DeclarationSignView` is already correctly written — it just never
fires because the `.exclude(document_id=None)` filter returns zero rows.

---

## What Is Missing ❌

### Root cause: `document_id` is never set

The `DeclarationOfIndependence` model already has these two fields ready:

```python
document_id       = models.UUIDField(null=True, blank=True)   # ← always null
stamped_document_url = models.URLField(null=True, blank=True)  # ← always null
```

Nothing in the current flow generates a PDF, uploads it to DRS, or stores the returned UUID.

---

## The Complete Flow (What It Should Look Like)

```
STEP 1 — User creates declaration in UI
         → DB record saved                         ✅ works
         → PDF generated from declaration data     ❌ missing
         → PDF uploaded to DRS                     ❌ missing
         → DRS UUID stored in declaration.document_id  ❌ missing

STEP 2 — User clicks Sign
         → DB: is_signed=True, status='signed'    ✅ works
         → Check: all declarations signed?         ✅ works

STEP 3 — All signed trigger fires
         → Loops over declarations with document_id set   ✅ code exists
         → Calls DRS generate-approved-stamp              ✅ code exists
         → Saves stamped_document_url                     ✅ code exists
         → (never reached because document_id is null)    ❌
```

---

## What DRS Already Has (Confirmed by Code Reading)

### ✅ Stamp endpoint — fully implemented

**File:** `document-records-service/apps/api/views/document_stamp_view.py`
**URL:** `POST /api/v1/documents/{document_id}/generate-approved-stamp/`

What it does:
1. Loads the PDF file from disk by document UUID
2. Fetches the approver's signature image from IAM (`IAMClient.get_user_profile`)
3. Generates a QR code → `https://{EXTERNAL_DOMAIN}/verify/{entity_type}/{entity_id}/`
4. Uses **ReportLab** to overlay: QR code (bottom-left, 30×30 mm) + signature (bottom-right, 65×22 mm) + separator line
5. Merges overlay onto the **last page** using PyPDF2
6. Saves the stamped file to storage, updates `Document.file_path` in DB
7. Returns `{ "document_id": "...", "stamped_document_url": "..." }`

Authentication: accepts `Bearer JWT` **or** `X-Service-Token`.

### ✅ GRC DocumentServiceClient — fully implemented

`grc-service/apps/infrastructure/external/document_service_client.py`:
- `create_document_with_file(title, description, document_type, classification, file_data, file_name, metadata, ...)` — creates metadata + uploads file in one call
- `generate_approved_stamp(document_id, approver_id, entity_type, entity_id, service_token)` — triggers DRS stamp

### ✅ PDF libraries in GRC — already installed

`grc-service/requirements.txt` already has:
```
weasyprint==60.1
reportlab==4.0.7
```
No new packages needed.

### ✅ DRS document types seeded for audit

`document-records-service/apps/infrastructure/persistence/seed_document_types.py` already has:
- `audit_report`
- `audit_working_paper`

**Missing:** `audit_declaration` — this must be added (Task 1).

---

## Implementation — 4 Tasks

### Task 1 — Add `audit_declaration` document type to DRS

**File:** `document-records-service/apps/infrastructure/persistence/seed_document_types.py`

Add this dict to `INITIAL_DOCUMENT_TYPES`:

```python
{
    'code': 'audit_declaration',
    'name': 'Declaration of Independence',
    'description': 'Signed Declaration of Independence and Conflict of Interest Form for audit engagements',
    'icon': 'file-signature',
    'color': '#0EA5E9',
    'default_classification': 'confidential',
    'default_retention_period': 7,
    'requires_approval': False,
    'reference_prefix': 'DCL',
    'is_system': False,
},
```

After adding, restart the DRS container (or run the seed management command inside it)
so the new type is inserted into the DB.

---

### Task 2 — Create the PDF generator utility

**New file:** `grc-service/apps/core/utils/pdf_generators.py`

```python
"""
PDF generation utilities for GRC formal output documents.
WeasyPrint (already in requirements.txt) is used for HTML → PDF conversion.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_declaration_pdf(decl) -> bytes:
    """
    Render a Declaration of Independence as PDF bytes.

    The HTML template uses a 60 mm bottom page margin so the DRS stamp
    (QR code + signature image) has space on the last page.

    Returns raw PDF bytes ready for upload to DRS.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    html_str = render_to_string('grc/declaration_of_independence.html', {
        'decl': decl,
        'engagement': decl.audit_engagement,
        'generated_at': timezone.now(),
    })
    return HTML(string=html_str).write_pdf()
```

---

### Task 3 — Create the HTML template for the declaration form

**New file:** `grc-service/templates/grc/declaration_of_independence.html`

The `@page` bottom margin **must be at least 55 mm** — DRS stamps QR (30×30 mm) and
signature (65×22 mm) in that space on the last page.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    @page { size: A4; margin: 20mm 25mm 60mm 25mm; }
    body  { font-family: Arial, sans-serif; font-size: 11pt; color: #222; line-height: 1.5; }
    .header { text-align: center; margin-bottom: 20px; }
    .title  { font-size: 14pt; font-weight: bold; margin: 6px 0; }
    .ref    { font-size: 9pt; color: #666; }
    .field  { margin: 14px 0; }
    .label  { font-weight: bold; }
    .body-text { text-align: justify; }
    .sig-block { margin-top: 30px; border-top: 1px solid #bbb; padding-top: 10px; }
  </style>
</head>
<body>

  <div class="header">
    <div class="title">FAIR COMPETITION COMMISSION</div>
    <div class="title">Declaration of Independence and Conflict of Interest</div>
    <div class="ref">Engagement: {{ engagement.reference_number }}</div>
  </div>

  <div class="field">
    <div class="label">Declarant Name:</div>
    <div>{{ decl.declarant_name }}</div>
  </div>
  <div class="field">
    <div class="label">Role in Engagement:</div>
    <div>{{ decl.get_declarant_role_display }}</div>
  </div>
  <div class="field">
    <div class="label">Audit Engagement:</div>
    <div>{{ engagement.title }} ({{ engagement.reference_number }})</div>
  </div>
  <div class="field">
    <div class="label">Date Generated:</div>
    <div>{{ generated_at|date:"d F Y" }}</div>
  </div>

  <div class="field body-text">
    <div class="label">Declaration:</div>
    <p>I, the undersigned, hereby declare that I am independent of the auditee
    and have no conflict of interest with respect to the matters subject to this
    audit engagement. I confirm that:</p>
    <ol>
      <li>I have no financial interest, direct or indirect, in the auditee or the subject matter under audit.</li>
      <li>I have no personal or professional relationship that could impair my objectivity or independence.</li>
      <li>I have disclosed all relationships and interests that could be perceived as a conflict of interest to my supervisor.</li>
      <li>I will conduct this audit with integrity, objectivity, and professional competence.</li>
      <li>I understand that any undisclosed conflict of interest may result in disciplinary action.</li>
    </ol>
  </div>

  {% if decl.is_signed %}
  <div class="sig-block">
    <div class="label">Signed by: {{ decl.declarant_name }}</div>
    <div>Date: {{ decl.signed_at|date:"d F Y H:i" }}</div>
    <!-- DRS overlays QR code (bottom-left) and signature image (bottom-right) below this line -->
  </div>
  {% else %}
  <div class="sig-block">
    <div>Signature: ___________________________</div>
    <div>Date: ___________________________</div>
  </div>
  {% endif %}

</body>
</html>
```

---

### Task 4 — Hook PDF generation into declaration creation

**File:** `grc-service/apps/api/views/declaration_views.py`

**Step A:** Add this helper function near the top of the file (after the existing imports):

```python
def _upload_declaration_pdf_to_drs(decl) -> None:
    """Generate a PDF for the declaration and upload it to DRS. Non-blocking."""
    import io
    from apps.infrastructure.external.document_service_client import DocumentServiceClient
    from apps.core.utils.pdf_generators import generate_declaration_pdf
    try:
        pdf_bytes = generate_declaration_pdf(decl)
        client = DocumentServiceClient(auth_token=None)  # service-to-service
        doc = client.create_document_with_file(
            title=f"Declaration of Independence — {decl.declarant_name}",
            description=(
                f"Conflict of Interest Declaration for audit engagement "
                f"{decl.audit_engagement.reference_number}"
            ),
            document_type='audit_declaration',
            classification='confidential',
            retention_period=2555,  # 7 years
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
        logger.info("GAP 9: Declaration %s PDF uploaded to DRS as %s", decl.id, doc['id'])
    except Exception as pdf_err:
        logger.warning("GAP 9: Could not upload declaration PDF to DRS: %s", pdf_err)
        # Non-blocking — the declaration record is still valid without a PDF.
        # Stamping will simply not run until document_id is set.
```

**Step B:** Call it in `DeclarationListCreateView.post()` after each declaration is created.

For **single creation**, after `decl = serializer.save(created_by=user_id)`:
```python
_upload_declaration_pdf_to_drs(decl)
```

For **bulk creation**, after the `for member in bulk_members:` loop completes:
```python
for decl in created:
    _upload_declaration_pdf_to_drs(decl)
```

No changes to `DeclarationSignView` are needed — the stamp trigger is already correct. Once
`document_id` is set by Task 4, it will fire automatically on the next sign action.

---

## Status Table

| Step | File | Works? | Action Needed |
|---|---|---|---|
| Create declaration DB record | `declaration_views.py` | ✅ | — |
| Generate PDF | `pdf_generators.py` | ❌ | **Task 2** |
| HTML template | `declaration_of_independence.html` | ❌ | **Task 3** |
| Upload PDF to DRS, store `document_id` | `declaration_views.py` | ❌ | **Task 4** |
| `audit_declaration` type in DRS DB | `seed_document_types.py` | ❌ | **Task 1** |
| User Sign → DB updated | `declaration_views.py` | ✅ | — |
| Check all declarations signed | `declaration_views.py` | ✅ | — |
| Call DRS stamp endpoint | `declaration_views.py` | ❌ (never reached) | Unblocked by Task 4 |
| Store `stamped_document_url` | `declaration_views.py` | ❌ (never reached) | Unblocked by Task 4 |
| DRS overlays QR + signature on PDF | `document_stamp_view.py` | ✅ | — |

---

## Implementation Order

Start with Tasks 1, 2, and 3 in any order — they are fully independent of each other.
Task 4 is last because it depends on all three being ready.

```
Step 1 of 4 — DRS seed (document-records-service)
  File:   document-records-service/apps/infrastructure/persistence/seed_document_types.py
  Action: Add the audit_declaration dict to INITIAL_DOCUMENT_TYPES
  Then:   Restart DRS container to apply the seed

Step 2 of 4 — PDF generator utility (grc-service)
  File:   grc-service/apps/core/utils/pdf_generators.py  (NEW FILE)
  Action: Create the file with generate_declaration_pdf() function (code above)

Step 3 of 4 — HTML template (grc-service)
  File:   grc-service/templates/grc/declaration_of_independence.html  (NEW FILE)
  Action: Create the HTML template (code above)
  Note:   Must keep @page bottom margin = 60mm so DRS stamp fits

Step 4 of 4 — Hook PDF upload into declaration creation (grc-service)
  File:   grc-service/apps/api/views/declaration_views.py
  Action: Add _upload_declaration_pdf_to_drs() helper + call it after each decl.save()
  Then:   Restart GRC container → test by creating a declaration → check declaration.document_id is set
```

After Step 4, test the full flow:
1. Create a declaration → `document_id` should be set (not null)
2. All team members sign → stamp trigger fires → `stamped_document_url` should be set
3. Download the stamped PDF → QR code and CIA signature visible at the bottom of the last page
