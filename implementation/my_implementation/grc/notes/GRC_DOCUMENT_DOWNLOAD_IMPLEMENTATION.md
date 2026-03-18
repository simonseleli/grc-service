# GRC Document Download — Implementation Notes

**Date:** 2026-03-14  
**Scope:** Risk Assessment evidence & Working Paper evidence  
**Status:** ✅ Complete (pending frontend rebuild to deploy)

---

## 1. Background

The GRC evidence panel (`EvidenceAttachmentSection`) previously showed uploaded files with name,
size, and date — but had no way for any user to download them. CIA (Chief Internal Auditor) who
has `readonly` access to evidence needed to be able to download files without being able to
upload or delete them.

---

## 2. How the Full Download Chain Works

```
Browser (CIA/IA)
  → clicks Download button
  → documentClient.get(`/{document_id}/download/`, { responseType: 'blob' })
      (axios interceptor auto-injects Authorization: Bearer <JWT>)
  → Gateway nginx → routes /api/v1/documents/* → DRS
  → DRS: GET /api/v1/documents/{id}/download/
      validates Bearer JWT (IAMJWTAuthentication)
      checks document access (document_access_control.py)
      streams FileResponse as attachment blob
  → browser: creates object URL → triggers native file download
```

---

## 3. Pre-existing Backend (No Changes Needed)

All of this existed already and was **not modified**:

| Layer | File / Endpoint | What it does |
|---|---|---|
| DRS URL | `apps/api/urls/documents.py` line 94 | `<uuid>/download/` → `DocumentDownloadView` |
| DRS View | `apps/api/views/document_download_view.py` | `BaseDocumentFileView` with `disposition = 'attachment'` — streams `FileResponse` |
| GRC client | `apps/infrastructure/external/document_service_client.py` | `get_download_url(id)` returns `/api/v1/documents/{id}/download/` |
| GRC evidence GET | `apps/api/views/risk_assessment_views.py` line 624 | Sets `doc['download_url'] = client.get_download_url(str(did))` in every evidence item |
| GRC working paper GET | `apps/api/views/working_paper_views.py` line 891 | Same — sets `download_url` for every working paper evidence item |
| Gateway nginx | `api-gateway/config/` | Proxies `/api/v1/documents/*` to DRS |
| Frontend axios client | `frontend/packages/shared/src/api/gateway.ts` line 199 | `documentClient` — base URL `${GATEWAY_URL}/api/v1/documents`, auto-injects JWT |

---

## 4. What Was Changed

### 4.1 `frontend/apps/staff-portal/src/types/grc.ts`

Added `download_url` to the `EvidenceAttachment` interface (was missing, causing TypeScript to
not know about the field the backend already sent):

```ts
export interface EvidenceAttachment {
  id: string;
  document_id: string;
  filename: string;
  file_size?: number;
  mime_type?: string;
  uploaded_by?: string;
  upload_url?: string;
  download_url?: string;   // ← ADDED
  created_at: string;
}
```

---

### 4.2 `frontend/apps/staff-portal/src/components/grc/EvidenceAttachmentSection.tsx`

**a) New imports:**
```ts
import { useRef, useState } from 'react';                        // added useState
import { Download, Loader2, Trash2, Upload } from 'lucide-react'; // added Download icon
import { documentClient } from '@shared/api/gateway';            // added documentClient
```

**b) New state inside the component:**
```ts
const [downloadingId, setDownloadingId] = useState<string | null>(null);
```

**c) New `handleDownload` function:**
```ts
const handleDownload = async (att: EvidenceAttachment) => {
  if (!att.document_id || downloadingId === att.document_id) return;
  setDownloadingId(att.document_id);
  try {
    const response = await documentClient.get(`/${att.document_id}/download/`, {
      responseType: 'blob',
    });
    const url = URL.createObjectURL(response.data as Blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = att.filename || 'evidence';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (err: any) {
    toast.error('Failed to download evidence', {
      description: err.response?.data?.error || err.message,
    });
  } finally {
    setDownloadingId(null);
  }
};
```

**d) Download button added to each evidence list item (always visible, even for readonly users):**
```tsx
<div className="flex items-center gap-1 shrink-0">
  <Button
    variant="ghost"
    size="icon"
    className="h-7 w-7"
    disabled={downloadingId === att.document_id}
    onClick={() => handleDownload(att)}
    title="Download"
  >
    {downloadingId === att.document_id ? (
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
    ) : (
      <Download className="h-3.5 w-3.5" />
    )}
  </Button>
  {!readonly && (
    <Button variant="ghost" size="icon" ... >  {/* delete — unchanged */}
    </Button>
  )}
</div>
```

---

## 5. Permission Logic — Who Sees What

The `readonly` prop on `EvidenceAttachmentSection` is driven by:

```tsx
// RiskAssessmentDetailDialog.tsx line 262
readonly={item.status === 'approved' || !canConductRiskAssessment}
```

Where `canConductRiskAssessment = hasPermission('grc:risk_assessment:conduct')`.

| Role | `grc:risk_assessment:conduct` | `readonly` | Download | Upload | Delete |
|---|---|---|---|---|---|
| Internal Auditor | ✅ | `false` (non-approved) | ✅ | ✅ | ✅ |
| CIA | ❌ | `true` (always) | ✅ | ❌ | ❌ |

CIA has `grc:risk_assessment:review` — NOT `grc:risk_assessment:conduct` — so they are always
`readonly`. The download button renders **outside** the `{!readonly && ...}` guard so CIA can
always download.

---

## 6. IAM Permissions Required (Already in Place)

For the DRS download endpoint to accept the user's JWT, the user must have
`document:document:read` in their JWT `permissions` array. Both roles already have this
(added in Phase 2 of the GRC document upload implementation):

- `document:document:read` → IA and CIA GRC roles ✅
- `document:document:read_confidential` → IA and CIA GRC roles ✅ (added to fix CIA "(unavailable)" issue)

---

## 7. Deploy

The changes are frontend-only. To deploy, rebuild the staff-portal image and restart:

```bash
# From workspace root
docker compose -f frontend/docker-compose.yml up --build staff-portal -d
# or whichever compose file runs the frontend
```

---

## 8. Extending to Other Entity Types

`EvidenceAttachmentSection` accepts `entityType: 'risk-assessment' | 'working-paper'`.
The download logic is the same for both — `documentClient` always calls DRS directly using the
`document_id`. No changes needed to add download support to working paper evidence; the same
component is reused in `WorkingPaperDetailPage.tsx` line 326.

To add a new entity type in the future:
1. Add the type to the `EntityType` union
2. Add `fetchFn`, `uploadFn`, `deleteFn` entries for the new type
3. The download button works automatically — no changes needed
