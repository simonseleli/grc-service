# FIMS — Working Paper Document Download: Architecture Reference

> **Reference implementation:** Audit Engagement → Working Papers (Document Download)  
> **Module:** grc-service  
> **Status:** Fully implemented and working as of March 2026  

This document is the definitive guide for understanding how FIMS handles the
**user-uploaded document download** pattern, as implemented in Working Papers.
Unlike the PDF generation + stamp flow (see `PDF_GENERATION_STAMP_DOWNLOAD_REFERENCE.md`),
Working Papers use a **user-uploaded file stored in the Document Records Service (DRS)**.
This reference covers the entire lifecycle: upload → storage → download.

All similar features in the system that deal with user-uploaded file attachments
and downloads **must** follow this same architecture.

---

## Table of Contents

1. [Core Architecture Principle](#1-core-architecture-principle)
2. [Complete Flow Diagrams](#2-complete-flow-diagrams)
   - [Upload Flow](#upload-flow)
   - [Download Flow](#download-flow)
3. [Data Model (GRC Side)](#3-data-model-grc-side)
4. [Backend Implementation](#4-backend-implementation)
   - [Step 1 — Document Service Client](#step-1--document-service-client)
   - [Step 2 — File Upload View (POST Create)](#step-2--file-upload-view-post-create)
   - [Step 3 — Serializer with Download URL](#step-3--serializer-with-download-url)
   - [Step 4 — Evidence Upload View](#step-4--evidence-upload-view)
5. [API Endpoints](#5-api-endpoints)
6. [Frontend Implementation](#6-frontend-implementation)
   - [Step 1 — Gateway Client Setup](#step-1--gateway-client-setup)
   - [Step 2 — GRC Service API Functions](#step-2--grc-service-api-functions)
   - [Step 3 — React Query Hooks](#step-3--react-query-hooks)
   - [Step 4 — Download Handler (Core)](#step-4--download-handler-core)
   - [Step 5 — Download Button UI](#step-5--download-button-ui)
   - [Step 6 — File Upload Dialog](#step-6--file-upload-dialog)
   - [Step 7 — Evidence Attachment Section](#step-7--evidence-attachment-section)
7. [Permissions and Roles](#7-permissions-and-roles)
8. [API Gateway (nginx) Routing](#8-api-gateway-nginx-routing)
9. [DRS Download View (Document Records Service)](#9-drs-download-view-document-records-service)
10. [Event Publishing (Kafka)](#10-event-publishing-kafka)
11. [Error Handling and Edge Cases](#11-error-handling-and-edge-cases)
12. [Key Files Reference](#12-key-files-reference)
13. [Replication Checklist](#13-replication-checklist)

---

## 1. Core Architecture Principle

FIMS uses a **microservice-based document storage** architecture:

```
┌──────────────┐                  ┌─────────────┐               ┌───────────────────────────┐
│   Frontend   │ ──── HTTP ─────▶ │ API Gateway │ ── proxy ──▶  │ Document Records Service  │
│ (staff-portal)│                  │   (nginx)   │               │     (DRS — port 8002)     │
└──────────────┘                  └─────────────┘               └───────────────────────────┘
                                        │
                                        ├── proxy ──▶  GRC Service (port 8004)
                                        │
                                        └── proxy ──▶  IAM Service (port 8001)
```

**The Golden Rule:** GRC Service **never stores files**. It only stores a `document_id`
(UUID) reference. All file storage, retrieval, and serving is handled by the Document
Records Service (DRS).

**Download requests go directly to DRS** through the API Gateway — GRC is not
involved in the download path at all.

---

## 2. Complete Flow Diagrams

### Upload Flow

```
User clicks "Create Working Paper" → fills form + selects file
    │
    ▼
Frontend sends POST (multipart/form-data) to GRC backend
    │  POST /api/v1/grc/audit/engagements/{engagement_id}/working-papers/
    │  Body: { title, paper_type, file }
    │
    ▼
GRC Backend (EngagementWorkingPapersView.post):
    │
    ├── 1. Extract JWT auth token from request header
    ├── 2. Validate engagement exists
    ├── 3. Auto-generate reference_number (WP-{eng_ref}-{seq:03d})
    │
    ├── 4. Call DRS via DocumentServiceClient:
    │      ├── Step A: POST /api/v1/documents/           → create metadata
    │      └── Step B: POST /api/v1/documents/{id}/upload/ → upload file
    │      Returns: { id: "<uuid>", ... }
    │
    ├── 5. Create WorkingPaper row in GRC DB with document_id = DRS UUID
    ├── 6. Publish Kafka event (grc.working.paper.created)
    │
    └── 7. Return success response with serialized WorkingPaper
```

### Download Flow

```
User clicks "Download" button on Working Paper detail page
    │
    ▼
Frontend (handleDownloadDocument):
    │
    ├── 1. documentClient.get(`/${paper.document_id}/download/`, { responseType: 'blob' })
    │      Resolves to: GET {GATEWAY_URL}/api/v1/documents/{document_id}/download/
    │      Headers: Authorization: Bearer <JWT>
    │
    ▼
API Gateway (nginx):
    │  location /api/v1/documents/ → proxy_pass http://document-records-service:8002
    │
    ▼
DRS (DocumentDownloadView.get):
    │
    ├── 1. Validate JWT authentication (or signed token)
    ├── 2. Resolve Document by UUID
    ├── 3. Ensure current version
    ├── 4. Resolve file from storage backend → get file handle
    ├── 5. Return FileResponse(as_attachment=True, filename=..., content_type=...)
    │      Headers: Content-Disposition: attachment; filename="original_name.pdf"
    │
    ▼
Frontend receives blob response:
    │
    ├── 1. Extract filename from Content-Disposition header
    │      (fallback: "{reference_number}-document")
    ├── 2. URL.createObjectURL(blob)
    ├── 3. Create invisible <a download="{filename}"> element
    ├── 4. Programmatically click it
    ├── 5. Remove <a> and revoke object URL
    │
    ▼
Browser triggers file download dialog
```

---

## 3. Data Model (GRC Side)

### WorkingPaper Model

**File:** `grc-service/apps/core/models/audit_entities.py`

```python
class WorkingPaper(TimestampedModel, StatusMixin, WorkflowMixin):
    """Audit evidence and documentation."""

    engagement = models.ForeignKey(
        AuditEngagement, on_delete=models.CASCADE, related_name='working_papers'
    )
    reference_number = models.CharField(max_length=100)
    title = models.CharField(max_length=500)

    PAPER_TYPE_CHOICES = [
        ('planning', 'Planning Documentation'),
        ('fieldwork', 'Fieldwork Documentation'),
        ('analysis', 'Analysis and Evaluation'),
        ('conclusion', 'Conclusions and Opinions'),
        ('other', 'Other Documentation'),
    ]
    paper_type = models.CharField(max_length=20, choices=PAPER_TYPE_CHOICES)

    # ── DRS Integration (the key fields) ──────────────────────────
    document_id = models.UUIDField(
        help_text="Primary document ID in Document Records Service"
    )
    evidence_document_ids = models.JSONField(
        default=list, blank=True
    )  # List of DRS UUIDs for supporting evidence

    prepared_by = models.UUIDField()
    reviewed_by = models.UUIDField(null=True, blank=True)

    REVIEW_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
    ]
    review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUS_CHOICES, default='draft', db_index=True
    )
    review_comments = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_working_paper'
        ordering = ['-created_at']
        unique_together = [['engagement', 'reference_number']]
```

**Critical fields for document download:**

| Field | Type | Purpose |
|-------|------|---------|
| `document_id` | `UUIDField` | Reference to the primary document in DRS |
| `evidence_document_ids` | `JSONField` (list of UUIDs) | References to supporting evidence documents in DRS |

**Inherited fields from `TimestampedModel`:**
- `id` (UUID PK), `created_at`, `updated_at`, `created_by`, `modified_by`

**Inherited fields from `StatusMixin`:**
- `is_active` (BooleanField)

**Inherited fields from `WorkflowMixin`:**
- `workflow_plan_id`, `workflow_stage`, `workflow_stage_id`, `workflow_started_at`, `workflow_completed_at`

### Key Design Decision

GRC stores **only the UUID reference** — never the file bytes, path, or URL.
The DRS owns the file lifecycle (versioning, storage backend, retention, disposal).

---

## 4. Backend Implementation

### Step 1 — Document Service Client

**File:** `grc-service/apps/infrastructure/external/document_service_client.py`

This is the **inter-service HTTP client** that GRC uses to communicate with DRS.
It is **only used during upload** (creating documents). Downloads go directly from
frontend → API Gateway → DRS, bypassing GRC entirely.

```python
class DocumentServiceClient:
    """Client for interacting with Document Records Service."""

    def __init__(self, base_url=None, auth_token=None):
        self.base_url = (base_url or settings.DOCUMENT_SERVICE_URL).rstrip('/')
        self.auth_token = auth_token
        self.timeout = 30

    def _get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers

    def create_document(self, title, description, document_type='audit_working_paper',
                        classification='confidential', record_type='non_permanent',
                        retention_period=2555, metadata=None, tags=None, **kwargs):
        """Create document metadata in DRS (Step 1 of two-step process)."""
        url = f'{self.base_url}/api/v1/documents/'
        payload = {
            'title': title,
            'description': description,
            'document_type': document_type,
            'classification': classification,
            'record_type': record_type,
            'retention_period': retention_period,
            'metadata': metadata or {},
            'tags': tags or [],
        }
        response = requests.post(url, json=payload, headers=self._get_headers(),
                                 timeout=self.timeout)
        if response.status_code == 201:
            return response.json()['data']
        raise DocumentServiceError(f"Document creation failed: {response.status_code}")

    def upload_file(self, document_id, file_data, file_name):
        """Upload file to existing document (Step 2 of two-step process)."""
        url = f'{self.base_url}/api/v1/documents/{document_id}/upload/'
        files = {'file': (file_name, file_data)}
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        # Do NOT set Content-Type — let requests set multipart boundary
        response = requests.post(url, files=files, headers=headers, timeout=self.timeout)
        if response.status_code == 200:
            return response.json()['data']
        raise DocumentServiceError(f"File upload failed: {response.status_code}")

    def create_document_with_file(self, title, description, file_data=None,
                                   file_name=None, **kwargs):
        """Convenience: create metadata + upload file in one call."""
        document = self.create_document(title=title, description=description, **kwargs)
        if file_data and file_name:
            document = self.upload_file(document['id'], file_data, file_name)
        return document

    def get_document(self, document_id):
        """Retrieve document metadata from DRS."""
        url = f'{self.base_url}/api/v1/documents/{document_id}/'
        response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
        if response.status_code == 200:
            return response.json()['data']
        raise DocumentServiceError(f"Retrieval failed: {response.status_code}")

    def get_download_url(self, document_id):
        """Get relative download URL for a document."""
        return f'/api/v1/documents/{document_id}/download/'


def get_document_client(auth_token=None):
    """Factory function — always use this to get a client instance."""
    return DocumentServiceClient(auth_token=auth_token)
```

**Important patterns:**
1. **Two-step upload:** First `POST /documents/` (metadata) → then `POST /documents/{id}/upload/` (file)
2. **Auth token passthrough:** The user's JWT is extracted from the GRC request and forwarded to DRS
3. **Settings dependency:** `settings.DOCUMENT_SERVICE_URL` (typically `http://document-records-service:8002`)

### Step 2 — File Upload View (POST Create)

**File:** `grc-service/apps/api/views/working_paper_views.py` — `EngagementWorkingPapersView.post()`

```python
def post(self, request, engagement_id):
    """Create a working paper with DRS integration."""
    
    # 1. Validate user
    user_id = getattr(request.user, 'id', None)
    if not user_id:
        return Response({"success": False, "error": {"message": "User not authenticated"}},
                        status=status.HTTP_401_UNAUTHORIZED)

    engagement = get_object_or_404(AuditEngagement, id=engagement_id)

    # 2. Extract file from multipart request
    uploaded_file = request.FILES.get('file')

    # 3. Extract JWT for DRS passthrough
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    auth_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None

    # 4. Auto-generate reference number
    count = WorkingPaper.objects.filter(engagement=engagement).count()
    reference_number = f"WP-{engagement.reference_number}-{count + 1:03d}"

    title = request.data.get('title')
    paper_type = request.data.get('paper_type', 'other')

    # 5. Create document in DRS
    document_client = get_document_client(auth_token=auth_token)
    document = document_client.create_document_with_file(
        title=title,
        description=f"Working paper for audit engagement: {engagement.title}",
        document_type='audit_working_paper',
        classification='confidential',
        record_type='non_permanent',
        retention_period=2555,          # 7 years for audit records
        file_data=uploaded_file if uploaded_file else None,
        file_name=uploaded_file.name if uploaded_file else None,
        metadata={
            'engagement_id': str(engagement.id),
            'engagement_reference': engagement.reference_number,
            'paper_type': paper_type,
            'service': 'grc-service',
            'module': 'working_papers'
        },
        tags=['audit', 'working-paper', paper_type, engagement.reference_number]
    )
    document_id = document['id']

    # 6. Create GRC record with DRS reference
    working_paper = WorkingPaper.objects.create(
        engagement=engagement,
        reference_number=reference_number,
        title=title,
        paper_type=paper_type,
        document_id=document_id,        # ← the DRS UUID reference
        evidence_document_ids=[],
        prepared_by=user_id,
        review_status='draft',
        created_by=user_id,
        modified_by=user_id
    )

    # 7. Publish Kafka event
    messaging_service.publish_working_paper_event(
        event_type='WORKING_PAPER_CREATED',
        working_paper_id=str(working_paper.id),
        engagement_id=str(engagement_id),
        additional_data={'title': title, 'paper_type': paper_type, 'document_id': str(document_id)}
    )

    # 8. Return serialized response
    serializer = WorkingPaperSerializer(working_paper)
    return success_response(data=serializer.data, message="Working paper created", status_code=201)
```

**Key observations:**
- View uses `MultiPartParser`, `FormParser`, and `JSONParser` parser classes
- Permission check: `CanManageWorkingPaper` (`grc:audit_working_paper:manage`)
- DRS metadata includes `service` and `module` tags for traceability
- The `document_type` sent to DRS is `'audit_working_paper'` — this must exist in DRS's DocumentType table

### Step 3 — Serializer with Download URL

**File:** `grc-service/apps/api/serializers/audit_serializers.py`

```python
class WorkingPaperSerializer(serializers.ModelSerializer):
    engagement_title = serializers.CharField(source='engagement.title', read_only=True)
    paper_type_display = serializers.CharField(source='get_paper_type_display', read_only=True)
    review_status_display = serializers.CharField(source='get_review_status_display', read_only=True)
    document_download_url = serializers.SerializerMethodField()

    class Meta:
        model = WorkingPaper
        fields = [
            'id', 'engagement', 'engagement_title', 'reference_number', 'title',
            'paper_type', 'paper_type_display', 'document_id', 'document_download_url',
            'evidence_document_ids', 'prepared_by', 'reviewed_by', 'review_status',
            'review_status_display', 'review_comments',
            'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
            'workflow_started_at', 'workflow_completed_at',
            'is_active', 'created_by', 'modified_by', 'created_at', 'updated_at'
        ]

    def get_document_download_url(self, obj):
        if obj.document_id:
            return f'/api/v1/documents/{obj.document_id}/download/'
        return None
```

**Note:** The `document_download_url` field is computed but **not actually used** by the
frontend. The frontend constructs its own authenticated download request using
`documentClient.get(/${document_id}/download/)`. However, including this field in the
serializer is good practice — it could be used by API consumers, mobile apps, or
third-party integrations.

### Step 4 — Evidence Upload View

**File:** `grc-service/apps/api/views/working_paper_views.py` — `WorkingPaperEvidenceView.post()`

Evidence documents follow the exact same DRS pattern:

```python
def post(self, request, paper_id):
    """Upload supporting evidence file to DRS and link to working paper."""

    paper = get_object_or_404(WorkingPaper, id=paper_id)

    # Guard: cannot add evidence to approved papers
    if paper.review_status == 'approved':
        return error_response(message="Cannot add evidence to an approved working paper",
                              code="WORKING_PAPER_APPROVED", status_code=400)

    uploaded_file = request.FILES.get('file')
    auth_token = self._get_auth_token(request)
    client = get_document_client(auth_token=auth_token)

    # Upload to DRS (same two-step pattern)
    document = client.create_document_with_file(
        title=request.data.get('title', uploaded_file.name),
        description=f"Supporting evidence for: {paper.title} ({paper.reference_number})",
        file_data=uploaded_file,
        file_name=uploaded_file.name,
        document_type='audit_working_paper',
        classification='confidential',
        metadata={
            'working_paper_id': str(paper.id),
            'engagement_id': str(paper.engagement_id),
            'service': 'grc-service',
            'module': 'working_paper_evidence',
        },
        tags=['audit', 'evidence', 'working-paper', paper.reference_number],
    )
    new_doc_id = str(document['id'])

    # Append UUID to evidence_document_ids (atomic update)
    with transaction.atomic():
        paper = WorkingPaper.objects.select_for_update().get(id=paper_id)
        doc_ids = list(paper.evidence_document_ids or [])
        if new_doc_id not in doc_ids:
            doc_ids.append(new_doc_id)
        paper.evidence_document_ids = doc_ids
        paper.save(update_fields=['evidence_document_ids'])
```

**Key pattern:** Evidence documents are stored in the `evidence_document_ids` JSONField as a
list of DRS UUIDs. The `select_for_update()` ensures thread-safe concurrent appends.

---

## 5. API Endpoints

All endpoints are prefixed with `/api/v1/grc/audit/`.

### GRC Service Endpoints (Working Papers)

| Method | Endpoint | View | Description |
|--------|----------|------|-------------|
| `GET` | `engagements/{id}/working-papers/` | `EngagementWorkingPapersView` | List papers for engagement |
| `POST` | `engagements/{id}/working-papers/` | `EngagementWorkingPapersView` | Create paper + upload to DRS |
| `GET` | `working-papers/{id}/` | `WorkingPaperDetailView` | Get single paper detail |
| `PUT` | `working-papers/{id}/` | `WorkingPaperDetailView` | Update paper metadata |
| `DELETE` | `working-papers/{id}/` | `WorkingPaperDetailView` | Delete paper (preparer only) |
| `POST` | `working-papers/{id}/review/` | `WorkingPaperReviewView` | Submit for approval workflow |
| `PATCH` | `working-papers/{id}/review/` | `WorkingPaperReviewView` | Update review status |
| `GET` | `working-papers/{id}/workflow-status/` | `WorkingPaperWorkflowStatusView` | Get workflow state |
| `GET` | `working-papers/{id}/workflow-history/` | `WorkingPaperWorkflowHistoryView` | Get workflow log |
| `POST` | `working-papers/{id}/workflow-action/` | `WorkingPaperWorkflowActionView` | Execute workflow action |
| `POST` | `working-papers/{id}/cancel-workflow/` | `WorkingPaperCancelWorkflowView` | Cancel active workflow |
| `GET` | `working-papers/{id}/evidence/` | `WorkingPaperEvidenceView` | List evidence docs |
| `POST` | `working-papers/{id}/evidence/` | `WorkingPaperEvidenceView` | Upload evidence to DRS |
| `DELETE` | `working-papers/{id}/evidence/{doc_id}/` | `WorkingPaperEvidenceDetailView` | Detach evidence |

### DRS Endpoints (Document Download)

| Method | Endpoint | View | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/documents/{id}/download/` | `DocumentDownloadView` | Download file as attachment |
| `GET` | `/api/v1/documents/{id}/preview/` | `DocumentPreviewView` | Inline preview |
| `GET` | `/api/v1/documents/{id}/file-access/` | `DocumentFileAccessView` | Signed URLs + metadata |
| `GET` | `/api/v1/documents/{id}/qr/` | `DocumentQRView` | QR code for document |
| `HEAD` | `/api/v1/documents/{id}/download/` | `DocumentDownloadView` | Metadata only (no body) |

### Request/Response Structure

**Create Working Paper Request (multipart/form-data):**
```
POST /api/v1/grc/audit/engagements/{engagement_id}/working-papers/
Authorization: Bearer <jwt>
Content-Type: multipart/form-data

title=Risk Assessment Procedures
paper_type=fieldwork
file=<binary file data>
```

**Create Working Paper Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "engagement": "uuid",
    "engagement_title": "FY2026 Revenue Audit",
    "reference_number": "WP-ENG-2026-001-001",
    "title": "Risk Assessment Procedures",
    "paper_type": "fieldwork",
    "paper_type_display": "Fieldwork Documentation",
    "document_id": "uuid (DRS reference)",
    "document_download_url": "/api/v1/documents/{document_id}/download/",
    "evidence_document_ids": [],
    "prepared_by": "uuid",
    "reviewed_by": null,
    "review_status": "draft",
    "review_status_display": "Draft",
    "created_at": "2026-03-17T10:30:00Z"
  },
  "message": "Working paper created"
}
```

**Download Response:**
```
GET /api/v1/documents/{document_id}/download/
Authorization: Bearer <jwt>

→ 200 OK
Content-Type: application/pdf (or original MIME type)
Content-Disposition: attachment; filename="original_filename.pdf"
Content-Length: 245760

<binary file data>
```

---

## 6. Frontend Implementation

### Step 1 — Gateway Client Setup

**File:** `frontend/packages/shared/src/api/gateway.ts`

```typescript
const SERVICES = {
  iam: `${GATEWAY_URL}/api/v1/iam`,
  documents: `${GATEWAY_URL}/api/v1/documents`,  // ← DRS
  grc: `${GATEWAY_URL}/api/v1/grc`,
  // ...
} as const;

const createServiceClient = (serviceName: ServiceName) => {
  const client = axios.create({
    baseURL: SERVICES[serviceName],
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,
  });

  // Auto-attach JWT from localStorage
  client.interceptors.request.use((config) => {
    const token = localStorage.getItem('accessToken');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    // Let browser set Content-Type for FormData
    if (config.data instanceof FormData) delete config.headers['Content-Type'];
    return config;
  });

  // Handle 401 → redirect to /session-expired
  // For 'documents' service: unwrap { success, data } envelope
  // ...
  return client;
};

export const documentClient = createServiceClient('documents');
export const grcClient = createServiceClient('grc');
```

**Key points:**
- `documentClient` base URL: `{GATEWAY_URL}/api/v1/documents`
- JWT auto-injected from `localStorage.getItem('accessToken')`
- For `documents` service: response envelope `{ success, data }` is auto-unwrapped
- FormData requests automatically have Content-Type header removed (browser sets multipart boundary)

### Step 2 — GRC Service API Functions

**File:** `frontend/apps/staff-portal/src/services/grcService.ts`

```typescript
// Create working paper (with file upload support)
export async function createWorkingPaper(engagementId: string, data: WorkingPaperFormData, file?: File) {
  const formData = new FormData();
  formData.append('title', data.title);
  formData.append('paper_type', data.paper_type);
  if (file) formData.append('file', file);
  
  const response = await grcClient.post(
    `audit/engagements/${engagementId}/working-papers/`,
    formData
  );
  return response.data;
}

// Fetch single working paper (detail)
export async function fetchWorkingPaper(id: string) {
  const response = await grcClient.get(`audit/working-papers/${id}/`);
  return response.data;
}

// Evidence upload
export async function uploadWorkingPaperEvidence(paperId: string, file: File, meta?: { title?: string }) {
  const formData = new FormData();
  formData.append('file', file);
  if (meta?.title) formData.append('title', meta.title);
  
  const response = await grcClient.post(
    `audit/working-papers/${paperId}/evidence/`,
    formData
  );
  return response.data;
}
```

**Note:** There is **no `downloadWorkingPaper()` function** in grcService.ts — downloads
go through `documentClient` directly in the component.

### Step 3 — React Query Hooks

**File:** `frontend/apps/staff-portal/src/hooks/useWorkingPapers.ts`

| Hook | Purpose |
|------|---------|
| `useEngagementWorkingPapers(engagementId, page, pageSize)` | List papers (React Query) |
| `useWorkingPaper(id)` | Single paper detail (React Query) |
| `useCreateWorkingPaper()` | Create mutation (React Query) |
| `useUpdateWorkingPaper()` | Update mutation (React Query) |
| `useDeleteWorkingPaper()` | Delete mutation (React Query) |
| `useSubmitWorkingPaperForApproval()` | Start workflow mutation |
| `useWorkingPaperWorkflowStatus(id)` | Get workflow state |
| `useWorkingPaperWorkflowHistory(id)` | Get workflow log |

**There is NO `useDownloadWorkingPaper` hook.** Download is handled inline in the
component because it's a one-shot blob operation, not query/cache data.

### Step 4 — Download Handler (Core)

**File:** `frontend/apps/staff-portal/src/pages/grc/WorkingPaperDetailPage.tsx`

This is the **reference implementation** for document download in the frontend:

```typescript
const handleDownloadDocument = async () => {
  if (!paper?.document_id || downloadingDoc) return;
  setDownloadingDoc(true);

  try {
    // 1. Request blob from DRS via documentClient
    const response = await documentClient.get(
      `/${paper.document_id}/download/`,
      { responseType: 'blob' }
    );

    // 2. Extract filename from Content-Disposition header
    const contentDisposition = response.headers['content-disposition'];
    let filename = `${paper.reference_number || 'working-paper'}-document`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) filename = match[1];
    }

    // 3. Create object URL and trigger download
    const url = URL.createObjectURL(response.data as Blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 4. Clean up
    URL.revokeObjectURL(url);
  } catch (err: any) {
    toast.error('Failed to download working paper document', {
      description: err.response?.data?.error || err.message,
    });
  } finally {
    setDownloadingDoc(false);
  }
};
```

**Pattern breakdown:**

1. **Guard clause:** Prevent double-clicks and missing document_id
2. **Blob request:** `responseType: 'blob'` tells Axios to receive binary data
3. **Filename extraction:** Parse `Content-Disposition: attachment; filename="foo.pdf"` header
4. **Fallback filename:** Use `{reference_number}-document` if header parsing fails
5. **Invisible anchor trick:** Standard browser download trigger
6. **Cleanup:** Always revoke the object URL to prevent memory leaks
7. **Error handling:** Toast notification with error description
8. **Loading state:** `downloadingDoc` state prevents concurrent downloads

### Step 5 — Download Button UI

**File:** `frontend/apps/staff-portal/src/pages/grc/WorkingPaperDetailPage.tsx`

```tsx
{paper.document_id && (
  <Card>
    <CardHeader className="pb-2">
      <CardTitle className="text-base flex items-center gap-2">
        <FileText className="h-4 w-4" />
        Working Paper Document
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
        <div className="flex flex-col min-w-0">
          <span className="font-medium truncate max-w-xs">
            {paper.title} — Main Document
          </span>
          <span className="text-xs text-muted-foreground">
            Document ID: {paper.document_id}
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownloadDocument}
          disabled={downloadingDoc}
        >
          {downloadingDoc ? (
            <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5 mr-1.5" />
          )}
          Download
        </Button>
      </div>
    </CardContent>
  </Card>
)}
```

**UI patterns:**
- Only renders if `paper.document_id` is truthy
- `Download` icon from `lucide-react`
- Spinner (`Loader2`) during download
- Button disabled while downloading
- Document ID shown for debugging/reference

### Step 6 — File Upload Dialog

**File:** `frontend/apps/staff-portal/src/components/grc/CreateWorkingPaperDialog.tsx`

- Form validated with `zod` (title min 10 chars, paper_type enum)
- File handled outside react-hook-form (File objects don't serialize in Zod)
- Accepted types: `.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.jpg,.jpeg,.png`
- Max size: 25 MB
- Drag-to-upload area with file preview
- On submit: `createMutation.mutateAsync({ engagementId, data, file })`

### Step 7 — Evidence Attachment Section

**File:** `frontend/apps/staff-portal/src/components/grc/EvidenceAttachmentSection.tsx`

Reusable component for both `working-paper` and `risk-assessment` entity types.
Download handler follows the exact same pattern as `handleDownloadDocument`:

```typescript
const handleDownload = async (att: EvidenceAttachment) => {
  try {
    const response = await documentClient.get(`/${att.document_id}/download/`, {
      responseType: 'blob',
    });
    const contentDisposition = response.headers['content-disposition'];
    let filename = att.filename || 'document';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) filename = match[1];
    }
    const url = URL.createObjectURL(response.data as Blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch {
    toast.error('Failed to download file');
  }
};
```

---

## 7. Permissions and Roles

### Permission Definitions

**File:** `grc-service/config/permissions/grc-service.json`

| Permission Code | Action | Who Needs It |
|----------------|--------|-------------|
| `grc:audit_working_paper:manage` | Create, update, delete, upload | Internal Auditors, Lead Auditors |
| `grc:audit_working_paper:review` | Review and approve | Lead Auditors, Chief Internal Auditor |

### Permission Check Mechanism

**File:** `grc-service/apps/api/permissions_jwt.py`

Permissions are **fully local** — no HTTP calls to IAM during request processing:

1. `JWTPermissionMiddleware` (middleware) extracts permission codes from the JWT payload and stores them in `request.grc_permissions` (a list of strings like `['grc:audit_working_paper:manage', ...]`)
2. Each view checks permissions via `_check_grc_permission_locally(request, permission_code)`
3. Superusers have `['*']` which grants all permissions

```python
def _check_grc_permission_locally(request, permission_code):
    grc_permissions = getattr(request, 'grc_permissions', [])
    if '*' in grc_permissions:
        return True  # Superuser wildcard
    return permission_code in grc_permissions
```

### Permission Classes

```python
class CanManageWorkingPaper(BasePermission):
    """grc:audit_working_paper:manage"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_working_paper:manage')

class CanReviewWorkingPaper(BasePermission):
    """grc:audit_working_paper:review"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_working_paper:review')
```

### Per-View Permission Matrix

| View | `GET` | `POST` | `PUT`/`DELETE` | `PATCH` |
|------|-------|--------|----------------|---------|
| `EngagementWorkingPapersView` | `:manage` OR `:review` OR `engagement:manage` | `:manage` | — | — |
| `WorkingPaperDetailView` | `:manage` OR `:review` | — | `:manage` (preparer only for edit/delete) | — |
| `WorkingPaperReviewView` | — | `:manage` (submit) | — | `:review` |
| `WorkingPaperWorkflowStatusView` | `:manage` OR `:review` | — | — | — |
| `WorkingPaperWorkflowHistoryView` | `:manage` OR `:review` | — | — | — |
| `WorkingPaperWorkflowActionView` | — | `:manage` | — | — |
| `WorkingPaperCancelWorkflowView` | — | `:manage` | — | — |
| `WorkingPaperEvidenceView` | `:manage` OR `:review` | `:manage` | — | — |
| `WorkingPaperEvidenceDetailView` | — | — | `:manage` (DELETE) | — |

### DRS Download Permission

The DRS `DocumentDownloadView` uses `AllowAny` permission class but **manually checks authentication**:
- If `?token=` query param exists → validate signed JWT (for OnlyOffice integration)
- Otherwise → `request.user.is_authenticated` must be True

**There is NO per-document permission check in DRS** — any authenticated user with
a valid JWT can download any document if they know the UUID. Access control is
enforced at the **GRC layer** (the frontend only gets `document_id` from GRC responses,
which are permission-gated).

### Role Mapping

| Role | Permissions | Can Download? |
|------|------------|---------------|
| Internal Auditor / Lead Auditor | `:manage`, `:review` | Yes — can see papers and click download |
| Chief Internal Auditor | `:review` + superuser wildcard | Yes |
| Management / Auditee | No working paper permissions | No — cannot see papers in UI |

---

## 8. API Gateway (nginx) Routing

**File:** `api-gateway/config/nginx.conf`

```nginx
upstream document_service {
    server document-records-service:8002 max_fails=3 fail_timeout=30s resolve;
}

upstream grc_service {
    server grc-service:8004 max_fails=3 fail_timeout=30s resolve;
}

# Document download/preview requests → DRS
location /api/v1/documents/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://document-records-service:8002/api/v1/documents/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Authorization $http_authorization;
    proxy_connect_timeout 30s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;
}

# GRC API requests → GRC Service
location /api/v1/grc/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://grc-service:8004/api/v1/grc/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Authorization $http_authorization;
    proxy_connect_timeout 30s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;
}
```

**Key details:**
- Rate limiting: `api` zone with burst=20
- `Authorization` header is passed through to backend services
- 30s timeouts for connect/send/read
- On 502/503/504: returns JSON `@service_unavailable` error

---

## 9. DRS Download View (Document Records Service)

**File:** `document-records-service/apps/api/views/document_download_view.py`

The actual file serving happens in `BaseDocumentFileView.get()`:

1. **Authentication:** Validate JWT (from header or `?token=` query param)
2. **Document lookup:** `GetDocumentUseCase(repository).execute(document_id, user_id)`
3. **Version resolution:** Ensure current version is loaded
4. **File resolution:** `DocumentStorageService.resolve_document(document)` → returns path, size, opener, backend
5. **MIME detection:** From `document.mime_type` or filename extension
6. **Response:**
   - `HEAD` request → metadata headers only
   - `GET` request → `FileResponse(file_handle, as_attachment=True, filename=..., content_type=...)`

**Response headers:**
```
Content-Disposition: attachment; filename="Risk_Assessment_Report.pdf"
Content-Type: application/pdf
Content-Length: 245760
```

---

## 10. Event Publishing (Kafka)

### Working Paper Events

**Topic:** `fims.grc.working.paper.events`

| Event Type | When Published | Key Payload Fields |
|-----------|---------------|-------------------|
| `grc.working.paper.created` | After successful creation | `title`, `paper_type`, `document_id`, `created_by` |
| `grc.working.paper.submitted` | After workflow submission | `title`, `submitted_by`, `reviewer_id` |
| `grc.working.paper.approved` | After CIA approval | `title`, `approved_by` |
| `grc.working.paper.rejected` | After rejection | `title`, `rejected_by`, `reason` |

**Event envelope format:**
```json
{
  "id": "uuid",
  "type": "grc.working.paper.created",
  "timestamp": "2026-03-17T10:30:00Z",
  "service": "grc-service",
  "version": "1.0",
  "data": {
    "working_paper_id": "uuid",
    "engagement_id": "uuid",
    "title": "Risk Assessment Procedures",
    "document_id": "uuid"
  }
}
```

**Files involved:**
- Event constants: `shared/constants/event_types.py`
- Event classes: `apps/core/events/audit_events.py`
- Publishing service: `apps/infrastructure/services/messaging_service.py`
- Kafka producer: `shared/common/messaging/kafka_producer.py`

---

## 11. Error Handling and Edge Cases

### Backend Error Cases

| Scenario | Response Code | Error Code | Handling |
|----------|--------------|------------|---------|
| User not authenticated | 401 | `AUTH_REQUIRED` | View manually checks `request.user.id` |
| Missing title | 400 | `VALIDATION_ERROR` | Validated before DRS call |
| DRS document creation fails | 500 | `DOCUMENT_SERVICE_ERROR` | Caught `DocumentServiceError` |
| DRS file upload fails (metadata created) | 500 | `DOCUMENT_SERVICE_ERROR` | Document metadata exists but no file — logged as warning |
| Engagement not found | 404 | Django default | `get_object_or_404` |
| Working paper not found | 404 | Django default | `get_object_or_404` |
| Approved paper edit attempt | 400 | `WORKING_PAPER_APPROVED` | Guard check on `review_status == 'approved'` |
| No file provided for evidence | 400 | `FILE_REQUIRED` | Explicit check |
| File too large | — | — | Not enforced server-side (frontend enforces 25MB limit) |
| Permission denied | 403 | DRF default | `check_permissions()` method |

### Frontend Error Cases

| Scenario | Handling |
|----------|---------|
| Download fails (network error) | `toast.error()` with error message |
| Download fails (401) | Auto-redirect to `/session-expired` (gateway interceptor) |
| Content-Disposition header missing | Fallback filename: `{reference_number}-document` |
| `paper.document_id` is null | Download button not rendered |
| Double-click during download | `downloadingDoc` state + button `disabled` |
| Evidence document missing in DRS | Returns `{ status: 'missing', filename: '(unavailable)' }` placeholder |

### Concurrent Evidence Upload

The evidence upload uses `select_for_update()` + `transaction.atomic()` to prevent
race conditions when multiple users upload evidence to the same working paper simultaneously.

---

## 12. Key Files Reference

### Backend (grc-service)

| Category | File |
|----------|------|
| **Model** | `apps/core/models/audit_entities.py` (WorkingPaper class) |
| **Base Mixins** | `apps/core/models/base.py` (TimestampedModel, StatusMixin, WorkflowMixin) |
| **Views** | `apps/api/views/working_paper_views.py` |
| **Serializers** | `apps/api/serializers/audit_serializers.py` |
| **URLs** | `apps/api/urls/audit.py` |
| **Permissions** | `apps/api/permissions_jwt.py` |
| **Permission Definitions** | `config/permissions/grc-service.json` |
| **DRS Client** | `apps/infrastructure/external/document_service_client.py` |
| **Service Layer** | `apps/core/services/working_paper_service.py` |
| **Events** | `apps/core/events/audit_events.py` |
| **Event Constants** | `shared/constants/event_types.py` |
| **Messaging** | `apps/infrastructure/services/messaging_service.py` |
| **Kafka Producer** | `shared/common/messaging/kafka_producer.py` |
| **Workflow YAML** | `apps/core/workflows/workflows.yaml` |
| **Workflow Entity Paths** | `apps/core/workflow_entity_paths.py` |
| **Tests** | `tests/api/test_working_paper_workflow.py` |
| **E2E Tests** | `tests/e2e/test_working_paper_workflow_e2e.py` |
| **Fixtures** | `conftest.py` |

### Frontend (frontend/)

| Category | File |
|----------|------|
| **Types** | `apps/staff-portal/src/types/grc.ts` (WorkingPaper interface) |
| **API Gateway** | `packages/shared/src/api/gateway.ts` (documentClient, grcClient) |
| **GRC API Functions** | `apps/staff-portal/src/services/grcService.ts` |
| **Document Service** | `apps/staff-portal/src/api/documentService.ts` (generic download helper) |
| **React Query Hooks** | `apps/staff-portal/src/hooks/useWorkingPapers.ts` |
| **Detail Page (download)** | `apps/staff-portal/src/pages/grc/WorkingPaperDetailPage.tsx` |
| **Create Dialog** | `apps/staff-portal/src/components/grc/CreateWorkingPaperDialog.tsx` |
| **Evidence Component** | `apps/staff-portal/src/components/grc/EvidenceAttachmentSection.tsx` |
| **List Component** | `apps/staff-portal/src/components/grc/WorkingPapersSection.tsx` |
| **Routing** | `apps/staff-portal/src/App.tsx` (route: `/service/grc/working-papers/:paperId`) |

### Infrastructure

| Category | File |
|----------|------|
| **API Gateway Config** | `api-gateway/config/nginx.conf` |
| **DRS Download View** | `document-records-service/apps/api/views/document_download_view.py` |

---

## 13. Replication Checklist

When implementing a similar user-uploaded document download feature for another entity:

### Backend Steps

- [ ] **1. Model:** Add `document_id = models.UUIDField(...)` field to your model
- [ ] **1b. Evidence (optional):** Add `evidence_document_ids = models.JSONField(default=list)` if supporting documents are needed
- [ ] **2. Serializer:** Add `document_download_url = SerializerMethodField()` and implement `get_document_download_url()`
- [ ] **3. View (Upload):** In your `POST` view:
  - Extract `request.FILES.get('file')`
  - Extract JWT: `request.META.get('HTTP_AUTHORIZATION', '')`
  - Call `get_document_client(auth_token=...)`.`create_document_with_file(...)`
  - Store returned `document['id']` in your model's `document_id` field
- [ ] **4. View (Upload) parsers:** Add `parser_classes = [MultiPartParser, FormParser, JSONParser]`
- [ ] **5. Permissions:** Create appropriate `BasePermission` subclass and register in `config/permissions/grc-service.json`
- [ ] **6. URLs:** Register endpoints in the appropriate URL config
- [ ] **7. Events (optional):** Create domain event classes and publish via `messaging_service`

### Frontend Steps

- [ ] **8. Type:** Add `document_id?: string` and `document_download_url?: string` to your TypeScript interface
- [ ] **9. API Function:** Create service function using `grcClient.post()` with `FormData` for upload
- [ ] **10. React Query Hook:** Create query hook for fetching detail and mutation hook for creating
- [ ] **11. Download Handler:** Copy the `handleDownloadDocument` pattern:
  ```typescript
  const response = await documentClient.get(`/${entity.document_id}/download/`, {
    responseType: 'blob',
  });
  // ... extract filename, create objectURL, trigger download
  ```
- [ ] **12. Download Button:** Render conditionally when `document_id` is truthy, with loading spinner
- [ ] **13. Upload Dialog:** Use react-hook-form + zod, handle File outside zod, use `FormData` for submission

### Configuration Steps

- [ ] **14. DRS Document Type:** Ensure your `document_type` string (e.g., `'audit_working_paper'`) exists in DRS's DocumentType table
- [ ] **15. Nginx (if new service):** Ensure API Gateway has proxy config for your service

### What NOT to Do

- **Do NOT** store file bytes in the GRC database
- **Do NOT** create a GRC endpoint for download — let the frontend call DRS directly
- **Do NOT** generate signed URLs on the backend — the frontend `documentClient` handles authentication
- **Do NOT** create a React Query hook for download — it's a one-shot blob operation, not cached data

---

## Appendix A — Generic Document Download Utility

The frontend has a reusable `documentService.downloadDocument()` function that implements
the same blob download pattern. You may use this instead of inline download handlers:

**File:** `frontend/apps/staff-portal/src/api/documentService.ts`

```typescript
downloadDocument: async (id: string, filename?: string) => {
  const response = await documentClient.get(`/${id}/download/`, { responseType: 'blob' });
  const contentDisposition = response.headers['content-disposition'];
  const contentType = response.headers['content-type'] || 'application/octet-stream';
  
  let downloadFilename = filename || `document-${id}`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="(.+)"/);
    if (match) downloadFilename = match[1];
  }
  
  const blob = new Blob([response.data], { type: contentType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = downloadFilename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => window.URL.revokeObjectURL(url), 100);
}
```

This is functionally equivalent to the inline `handleDownloadDocument` in WorkingPaperDetailPage
but is importable from any component.

---

## Appendix B — DRS Document Type Configuration

When creating documents in DRS, you pass `document_type='audit_working_paper'`. This
string must correspond to a record in DRS's `DocumentType` table. Default DRS parameters:

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `document_type` | `'audit_working_paper'` | Must exist in DRS |
| `classification` | `'confidential'` | Audit documents are restricted |
| `record_type` | `'non_permanent'` | Subject to retention rules |
| `retention_period` | `2555` | 7 years (audit standard) |

---

## Appendix C — TypeScript Interface

```typescript
export interface WorkingPaper {
  id: string;
  engagement: string;
  engagement_title?: string;
  reference_number: string;
  title: string;
  paper_type: 'planning' | 'fieldwork' | 'analysis' | 'conclusion' | 'other';
  paper_type_display?: string;
  document_id?: string;
  document_download_url?: string;
  evidence_document_ids?: string[];
  prepared_by: string;
  reviewed_by?: string;
  review_status: 'draft' | 'pending' | 'reviewed' | 'approved';
  review_status_display?: string;
  review_comments?: string;
  workflow_plan_id?: string;
  workflow_stage?: string;
  workflow_stage_id?: string;
  workflow_started_at?: string;
  workflow_completed_at?: string;
  is_active: boolean;
  created_by?: string;
  modified_by?: string;
  created_at: string;
  updated_at?: string;
}
```
