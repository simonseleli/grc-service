# Core Service Edit — DRS `seed_document_types.py`

> **File touched:** `document-records-service/apps/infrastructure/persistence/seed_document_types.py`
> **Date:** March 14–15, 2026
> **Author:** GRC service developer
> **For senior review:** Yes — please read before the next DRS image rebuild.

---

## 1. Summary of the Change

A single new dictionary entry was added to the `INITIAL_DOCUMENT_TYPES` list in
`document-records-service/apps/infrastructure/persistence/seed_document_types.py`.

**What was added:**

```python

1. for Declaration
{
    'code': 'audit_declaration',
    'name': 'Declaration of Independence',
    'description': 'Signed Declaration of Independence and Conflict of Interest Form for audit engagements',
    'icon': 'file-signature',
    'color': '#0EA5E9',  # sky blue
    'default_classification': 'confidential',
    'default_retention_period': 7,  # 7 years for audit records
    'requires_approval': False,
    'reference_prefix': 'DCL',
    'is_system': False,
},

2. for Engagement Notification

    {
        'code': 'audit_engagement_notification',
        'name': 'Engagement Notification',
        'description': 'Formal Engagement Notification issued to the auditee before fieldwork begins (SRS Req 26)',
        'icon': 'file-text',
        'color': '#059669',  # emerald-600
        'default_classification': 'confidential',
        'default_retention_period': 7,  # 7 years for audit records
        'requires_approval': True,
        'reference_prefix': 'EN',
        'is_system': False,
    },


3. 
    {
        'code': 'audit_meeting_minutes',
        'name': 'Audit Meeting Minutes',
        'description': 'Minutes and proceedings for audit meetings (entry, exit, pre-exit)',
        'icon': 'clipboard-list',
        'color': '#DC2626',  # red-600
        'default_classification': 'confidential',
        'default_retention_period': 2555,  # 7 years for audit records
        'requires_approval': False,
        'reference_prefix': 'AMM',
        'is_system': False,
    },
    {
        'code': 'audit_meeting_attendance',
        'name': 'Audit Meeting Attendance',
        'description': 'Attendance register for audit meetings (entry and exit)',
        'icon': 'user-check',
        'color': '#DC2626',  # red-600
        'default_classification': 'confidential',
        'default_retention_period': 2555,  # 7 years for audit records
        'requires_approval': False,
        'reference_prefix': 'AMA',
        'is_system': False,
    },


```

**Nothing else in the file was modified.** No logic, no schema, no existing entry was altered.

---

## 2. The Problem

The GRC service is required by the SRS to generate and store a **Declaration of Independence**
(and Conflict of Interest) form for each audit engagement. Specifically:

- **SRS Requirement 16**: Every auditor assigned to an engagement must file a signed
  Declaration of Independence form before the engagement proceeds.
- **SRS Requirement 18**: Declarations must be stored as official documents with full
  audit trail (a QR code stamped on the final page, linking to a verification endpoint).
- **SRS Requirement 38**: The DRS (Document Records Service) is the single source of truth
  for all official documents in FIMS. No service should store official documents locally.

To fulfil this, the GRC service must:
1. Generate a PDF of the declaration (WeasyPrint from an HTML template).
2. Upload that PDF to DRS via `POST /api/v1/documents/`.
3. Store the returned DRS document UUID in `Declaration.document_id`.
4. Later, when all auditors sign, call the DRS stamp endpoint
   `POST /api/v1/documents/{id}/generate-approved-stamp/` to overlay the QR code.

**Step 2 requires DRS to have a matching `DocumentType` record** for code `audit_declaration`.
DRS validates the `document_type` field on every upload — if the code does not exist in the
`DocumentType` table, it returns HTTP 400 and the upload fails.

---

## 3. Why the `audit_declaration` Code Was Missing

DRS ships with a standard `INITIAL_DOCUMENT_TYPES` list that covers generic government document
types (`contract`, `report`, `letter`, `policy`, `invoice`, etc.) and a few audit-specific types
that were added earlier (`audit_report`, `audit_working_paper`).

The `audit_declaration` code was never added because, when DRS was originally seeded, the
Declaration of Independence feature in GRC was not yet fully implemented. The document model
existed in GRC, but the PDF generation and DRS upload path was not built. As a result, no one
had registered `audit_declaration` as a document type.

---

## 4. Why We Could Not Solve This in GRC Alone

Several alternatives were considered before touching the DRS file:

### Option A — Use an existing generic type (e.g., `report` or `form`)
Ruled out. Using a mismatched type code undermines auditability. The `reference_prefix` field
(`DCL` for declarations vs `RPT` for reports) defines how DRS generates human-readable reference
numbers (e.g., `DCL-2026-001`). Using `report` would generate `RPT-2026-XXX` on a declaration
document, which is incorrect and confusing for reviewers. It also masks the document type in
the DRS admin panel and API responses.

### Option B — Call a DRS API endpoint to create the document type at runtime
Ruled out. DRS does **not** expose a public REST endpoint for creating `DocumentType` records.
These are infrastructure-level data entries managed via a Django management command
(`python manage.py seed_document_types`), not via the API. GRC has no mechanism to insert
document types into DRS's database.

### Option C — Have GRC store declarations locally (skip DRS)
Ruled out. SRS Requirement 38 explicitly mandates DRS as the single document store. Storing
declarations locally in GRC would violate the architecture, prevent QR stamping (which is a
DRS-only operation), and produce an incomplete audit trail.

### Option D — Have DRS auto-create unknown document types on first use
Ruled out. This would require modifying DRS core logic (the document creation view or
serializer), which is a far more invasive change than adding a seed entry. It would also
create poorly-described document types without proper metadata (icon, color, retention period,
reference prefix).

---

## 5. Why This Is the Correct and Minimal Touch

The `seed_document_types.py` file is **not business logic** — it is **reference data
configuration**. Its only purpose is to define what document types the system knows about.
Adding a new entry to it is equivalent to adding a row to a configuration table.

Key reasons this is safe and appropriate:

| Property | Detail |
|----------|--------|
| **No logic changed** | Only a new dict was appended to a list. Zero logic alteration. |
| **Idempotent seeding** | `seed_document_types()` uses Django's `get_or_create` — running the command multiple times is safe. Re-running will not duplicate or alter the entry. |
| **`is_system: False`** | The new entry is explicitly marked `is_system: False`, distinguishing it from the core system types (`is_system: True`). This is the correct setting for a service-specific document category. |
| **No schema change** | No new fields, no migrations, no model changes were needed. |
| **No existing entries touched** | The 16 pre-existing entries are untouched. |
| **Consistent with prior GRC additions** | `audit_report` (prefix `AUD`) and `audit_working_paper` (prefix `AWP`) were added the same way in a previous session. This is the established pattern for registering GRC-specific document types. |
| **Retention period matches regulation** | 7 years (`2555` days) — consistent with `audit_working_paper` and standard audit record retention under Tanzania's Public Audit Act. |

---

## 6. How It Was Applied to the Running Container

Since DRS does not have a volume-mount for source files in its `docker-compose.yml`
(code is baked into the image at build time), the change was applied to the running
container without a rebuild using:

```bash
# Copy updated file into the running DRS container
docker cp document-records-service/apps/infrastructure/persistence/seed_document_types.py \
    fims-document-records-service:/app/apps/infrastructure/persistence/seed_document_types.py

# Run the seed management command inside the container
docker exec -it fims-document-records-service \
    python manage.py seed_document_types
```

**Output confirmed:**
```
✓ Created document type: Declaration of Independence (audit_declaration)
✅ Seeding complete: 1 created, 0 updated
```

The change is **already in the host source file** (`document-records-service/apps/infrastructure/
persistence/seed_document_types.py`), so it will be included automatically in the next
DRS image rebuild (`docker compose up --build`).

---

## 7. Impact Assessment

| Area | Impact |
|------|--------|
| Existing document types | None — no existing entry was modified |
| DRS API behaviour | No change — the new type is available via the existing `DocumentType` API, same as all other types |
| DRS database schema | No change — `DocumentType` model unchanged |
| Other services (IAM, WO, corporate, client) | No impact — they do not use `audit_declaration` |
| GRC service | Positive — `POST /api/v1/documents/` now accepts `audit_declaration` as a valid type; declaration PDF upload succeeds |
| Re-seeding on rebuild | Safe — `get_or_create` means re-seeding on container rebuild is a no-op for this entry |

---

## 8. What Happens If This Entry Is Removed

If `audit_declaration` is removed from the seed list and the DRS container is rebuilt
without running the seed command, the `DocumentType` DB record will still exist (seed
commands do not delete records). However, if the DRS database is ever wiped and
re-seeded from scratch (e.g., a fresh deployment), the entry will be missing again and:

1. GRC's `_upload_declaration_pdf_to_drs()` will fail with HTTP 400 from DRS.
2. `Declaration.document_id` will remain `null`.
3. The QR/signature stamp step (`DeclarationSignView`) will silently skip stamping
   because it checks `if not decl.document_id`.
4. No SRS Requirement 16/18/38 compliance — declarations will be stored locally
   in GRC only, with no QR stamp.

**Conclusion:** The entry must remain in the seed file permanently.

---

## 9. Request to Senior

Please review and confirm:

1. **Is adding a non-system (`is_system: False`) document type entry to DRS's seed file
   acceptable without formal CR?** This follows the same precedent as `audit_report` and
   `audit_working_paper` which were added similarly.

2. **Should `audit_declaration` be marked `is_system: True` or `is_system: False`?**
   Current choice is `False` (application-level, GRC-specific). If policy requires all
   audit document types to be `True` (system-level), I can update it.

3. **No other core service files were modified** for the Declaration PDF feature.
   All PDF generation logic lives entirely in `grc-service`. See:
   - `grc-service/apps/core/utils/pdf_generators.py` *(new file)*
   - `grc-service/templates/grc/declaration_of_independence.html` *(new file)*
   - `grc-service/apps/api/views/declaration_views.py` *(modified — GRC only)*

---

*For full technical background on the Declaration of Independence implementation (GAP 9),
see: `grc-service/implementation/my_implementation/grc/aligned_with_FIMS/GAP9_DECLARATION_QR_STAMP.md`*
