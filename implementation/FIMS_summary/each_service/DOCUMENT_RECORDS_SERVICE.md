# Document Records Service — Deep Architectural Reference

> **Service:** document-records-service  
> **Port:** 8002  
> **Database:** `fims_documents` on `postgres-document-records-service` (PostgreSQL 15)  
> **Cache:** `redis-document-records-service:6379`  
> **Container:** `fims-document-records-service`  
> **Gateway Routes:** `/api/v1/documents/*`, `/api/v1/folders/*`, `/api/v1/document-types/*`, `/api/v1/document-templates/*`, `/api/v1/report-templates/*`, `/api/v1/reports/*`, `/api/v1/storage-locations/*`, `/api/v1/template-versions/*`, `/api/v1/template-workflows/*`, `/api/v1/comments/*`

---

## Table of Contents

1. [Primary Responsibilities & Domain Ownership](#1-primary-responsibilities--domain-ownership)
2. [Capabilities Exposed to Other Services](#2-capabilities-exposed-to-other-services)
3. [Exclusive Ownership vs. Delegation](#3-exclusive-ownership-vs-delegation)
4. [Architecture — Clean Architecture Layers](#4-architecture--clean-architecture-layers)
5. [Data Model Reference](#5-data-model-reference)
6. [Complete API Surface](#6-complete-api-surface)
7. [Document Lifecycle & Status Machine](#7-document-lifecycle--status-machine)
8. [Workflow Integration (Work Orchestration)](#8-workflow-integration-work-orchestration)
9. [OnlyOffice Integration](#9-onlyoffice-integration)
10. [Cross-Service Dependencies & Collaboration](#10-cross-service-dependencies--collaboration)
11. [Notification Publishing](#11-notification-publishing)
12. [Permission Registration](#12-permission-registration)
13. [Background Tasks (Celery)](#13-background-tasks-celery)
14. [How Other Services Consume Document Records](#14-how-other-services-consume-document-records)
15. [Integration Guide for New Services](#15-integration-guide-for-new-services)
16. [Architectural Boundaries — What Not To Do](#16-architectural-boundaries--what-not-to-do)

---

## 1. Primary Responsibilities & Domain Ownership

The document-records-service is the **sole authority for all document storage, metadata, versioning, lifecycle management, collaboration, and records management** across the entire FIMS platform.

### 1.1 Document Management
- Document creation (upload-based or template-based via file or rich editor)
- Document metadata (title, description, reference number, tags, classification)
- Document types (admin-configurable, replacing hardcoded enum)
- Document templates (file-based with OnlyOffice editing, or rich editor with component structure)
- File storage (filesystem-based, with path tracking)
- Document versioning (version history, version comparison, revert)
- Document locking (pessimistic concurrency control for editing)
- Document downloading, previewing, and thumbnail generation
- QR code generation for document identification
- Document search (PostgreSQL full-text search with GIN indexes)

### 1.2 Document Lifecycle
- Status state machine: `draft` → `under_review` → `approved`/`rejected` → `active` → `semi_active` → `inactive` → `eligible_for_decongestion` → `archived` → `disposed`
- Lifecycle period tracking: active → semi-active → inactive transitions based on configurable day periods
- Retention period management
- Archival and restore operations
- Decongestion (marking documents eligible for disposal based on retention policies)

### 1.3 Classification & Access Control
- Document classification: **Open** vs **Confidential**
- Classification-based access enforcement (confidential documents require specific permissions)
- Document sharing with granular permission levels (read, comment, edit, admin)
- Share expiration (time-limited shares)
- Principal-based sharing (user, group, or role)
- Access request workflow (request → review → approve/reject)
- Access logging (comprehensive audit trail of all access events)

### 1.4 Folder & File Management (e-Office)
- Hierarchical folder system with FCC organizational file series codes
- Folder numbering using file series + keyword + planning number + part number
- Folder types: Personal and Subject
- Folder classification: Open and Classified
- Folder state management: Open → Closed (automated at capacity threshold)
- Capacity management: configurable max documents, warning thresholds, auto-close
- Folder activities audit trail
- Document-to-folder association (many-to-many via `FolderDocument`)

### 1.5 Document Collaboration
- Comments with nested replies (threaded discussions)
- @mention support (extracts user references from comment text)
- Private comments (visible only to mentioned users and document owner)
- Comment resolution workflow
- Digital signatures (digital and scanned methods)
- Signature request and upload flow
- Signature validation
- Ownership transfer
- Bulk sharing

### 1.6 Incoming & Outgoing Document Registers
- **Incoming Register** — tracks documents received by FCC (sender info, priority, routing history, current holder)
- **Outgoing Register** — tracks documents dispatched by FCC (recipient info, dispatch method, delivery tracking)
- Register document attachments (multiple documents per register entry)
- Document routing (track movement through departments/holders)
- Delivery confirmation for outgoing documents

### 1.7 Disposal Management
- Disposal form creation (with reason: retention expired, duplicate, obsolete, damaged)
- Two-stage approval: Director General + Records Department
- Disposal methods: shred, burn, digital delete, transfer to archives
- Disposal certificate tracking
- Auto-creation of disposal forms for eligible documents (via Celery)
- Auto-execution of fully approved digital disposals
- Disposal statistics

### 1.8 Reports
- Report template management (PDF, Excel, CSV)
- Scheduled report generation (daily, weekly, monthly, quarterly, yearly)
- On-demand report generation
- Report download
- Report summary dashboard

### 1.9 Physical Storage Tracking
- Storage location management (buildings, warehouses)
- Storage floor/section tracking
- Document physical storage records (shelf number, box/file number, row/column)
- Storage threshold monitoring and alerting

---

## 2. Capabilities Exposed to Other Services

### 2.1 Document CRUD API (REST)

The primary API for any service that needs to store, retrieve, or manage documents.

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /api/v1/documents/` | POST | Create a document (metadata + optional file upload) |
| `GET /api/v1/documents/<uuid>/` | GET | Retrieve document metadata |
| `PUT/PATCH /api/v1/documents/<uuid>/` | PUT/PATCH | Update document metadata |
| `DELETE /api/v1/documents/<uuid>/` | DELETE | Soft-delete a document |
| `POST /api/v1/documents/<uuid>/upload/` | POST | Upload/replace file for existing document |
| `GET /api/v1/documents/<uuid>/download/` | GET | Download the document file |
| `GET /api/v1/documents/<uuid>/preview/` | GET | Preview document in browser |

### 2.2 Document Search & Stats

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /api/v1/documents/search/` | GET | Full-text search with filters |
| `GET /api/v1/documents/search/suggestions/` | GET | Search autocomplete suggestions |
| `GET /api/v1/documents/stats/` | GET | Document statistics dashboard |
| `GET /api/v1/documents/storage/stats/` | GET | Storage usage statistics |

### 2.3 Workflow Integration API

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /api/v1/documents/<uuid>/submit-for-approval/` | POST | Submit document for approval workflow |
| `POST /api/v1/documents/<uuid>/approve/` | POST | Approve/reject a document |
| `GET /api/v1/documents/<uuid>/approval-status/` | GET | Check approval workflow status |
| `POST /api/v1/documents/workflows/start/` | POST | Start a workflow via orchestration engine |
| `POST /api/v1/documents/workflows/<uuid>/action/` | POST | Execute workflow action |
| `GET /api/v1/documents/workflows/<uuid>/status/` | GET | Get workflow instance status |

### 2.4 Kafka Domain Events

The document-records-service publishes domain events that other services can consume:

| Topic | Event Types | Use Case |
|---|---|---|
| `fims.documents.events` | Document created, updated, approved, archived, disposed | Other services reacting to document state changes |

### 2.5 Folder API (for Other Services)

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /api/v1/folders/` | GET | List folders |
| `POST /api/v1/folders/` | POST | Create a folder |
| `GET /api/v1/folders/<uuid>/` | GET | Folder details with documents |

---

## 3. Exclusive Ownership vs. Delegation

### 3.1 What Document Records Owns Exclusively

| Capability | Why |
|---|---|
| **File storage** | All files in FIMS live in this service's media directory — no other service stores files |
| **Document metadata and versioning** | Single source of truth for all document information |
| **Document types and templates** | Admin-configurable taxonomy for all FCC documents |
| **Folder/file management** | The e-Office hierarchical file system is entirely within this service |
| **Document registers** | Incoming and outgoing document tracking for FCC mailroom |
| **Disposal lifecycle** | From eligibility to approval to execution — fully owned |
| **Physical storage records** | Maps digital documents to physical shelving/warehousing |
| **Document collaboration** | Comments, shares, signatures, access requests |
| **QR code generation** | Per-document QR codes for physical document identification |
| **OnlyOffice integration** | In-browser document editing via OnlyOffice Docs |

### 3.2 What Document Records Delegates

| Capability | Delegated To | Mechanism |
|---|---|---|
| **User authentication** | iam-service | JWT validation via shared secret (JWTPermissionMiddleware) |
| **User identity resolution** | iam-service | REST calls via `IAMClient` with 5-min Redis cache |
| **Workflow plan creation and advancement** | work-orchestration-service | REST via `WorkOrchestrationClient` with circuit breaker |
| **Notification delivery** | work-orchestration-service | Kafka via `NotificationPublisher` to priority topics |
| **Permission registration** | iam-service | Kafka to `service.permission.registry` topic |
| **Workflow template management** | work-orchestration-service | Templates stored in orchestration service, not here |

### 3.3 What Other Services Delegate to Document Records

| Service | What It Delegates | How |
|---|---|---|
| All services | Document storage and management | REST API calls to `/api/v1/documents/*` |
| client-service | Client document metadata sync | Periodic sync from document-records events |
| corporate-service | HR/Finance/Procurement documents | REST API references to document UUIDs |
| grc-service | Compliance and audit documents | REST API references to document UUIDs |

---

## 4. Architecture — Clean Architecture Layers

The document-records-service follows **Clean Architecture** more strictly than other FIMS services:

```
┌────────────────────────────────────────────────────────────────┐
│  apps/api/                                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Views, Serializers, URL routing, DRF Permissions         │  │
│  │ (Translates HTTP ↔ Use Cases)                            │  │
│  └─────────────────────────┬────────────────────────────────┘  │
│                            │ calls                              │
│  apps/core/                ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ use_cases/     — Application-level business logic        │  │
│  │ entities/      — Pure domain dataclasses + enums         │  │
│  │ repositories/  — Abstract repository interfaces          │  │
│  │ services/      — Domain services                         │  │
│  │ workflow/      — Workflow orchestration adapter layer     │  │
│  │ notifications/ — NotificationPublisher                   │  │
│  │ exceptions.py  — Domain exception hierarchy              │  │
│  └─────────────────────────┬────────────────────────────────┘  │
│                            │ uses interfaces                    │
│  apps/infrastructure/      ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ persistence/   — Django ORM models implementing repos    │  │
│  │ tasks/         — Celery tasks                            │  │
│  │ external/      — External service clients                │  │
│  │ messaging/     — Kafka producers/consumers               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### 4.1 Domain Entities (apps/core/entities/)

Pure Python dataclasses representing domain concepts — no Django dependencies:
- `Document` — core document entity with all status/classification enums
- `DisposalForm` — disposal form entity
- `Approval` — approval action entity
- `Folder`, `FileSeries`, `Keyword` — folder management entities

### 4.2 Workflow Layer (apps/core/workflow/)

The workflow layer uses an **Adapter Pattern** to route workflow operations:

```
WorkflowOrchestrator
    ↓ uses
WorkflowAdapterRegistry
    ├── WorkOrchestrationAdapter  (proxies to work-orchestration-service REST API)
    ├── DisposalWorkflowAdapter   (handles disposal-specific workflow logic)
    └── ApprovalWorkflowAdapter   (handles document approval logic)
```

Each adapter implements the `WorkflowAdapter` interface:
- `can_handle(workflow_type, step_type) → bool`
- `start_workflow(document_id, workflow_data, initiator_id) → dict`
- `execute_step(instance_id, step_id, action, action_data, user_id) → dict`
- `get_workflow_status(instance_id) → dict`
- `get_available_actions(instance_id, user_id) → list`

The registry prefers the `WorkOrchestrationAdapter` first, so new workflow types automatically route to the central orchestration service.

---

## 5. Data Model Reference

### 5.1 Document

```
Table: documents
PK: id (UUIDField)
Unique constraint: (reference_number, version)
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `reference_number` | CharField(100) | Format: `FCC-YYYY-TYPE-XXXXX`, indexed |
| `title` | CharField(500) | |
| `description` | TextField | Nullable |
| `document_type_ref` | FK(DocumentType) | Configurable type (new system) |
| `document_type` | CharField(100) | Legacy type field (deprecated) |
| `file_path` | CharField(1000) | Filesystem path |
| `file_name` | CharField(500) | Original filename |
| `file_size` | BigIntegerField | Bytes |
| `mime_type` | CharField(100) | e.g., `application/pdf` |
| `file_extension` | CharField(10) | e.g., `.pdf` |
| `version` | IntegerField | Default: 1 |
| `is_current_version` | BooleanField | Indexed |
| `parent_document` | FK(self) | Points to original document for version chains |
| `change_summary` | TextField | What changed in this version |
| `status` | CharField(50) | See status machine below, indexed |
| `workflow_state` | CharField(100) | Current workflow state label |
| `orchestration_plan_id` | UUIDField | Link to work-orchestration plan, indexed |
| `classification` | CharField(50) | `open` or `confidential`, indexed |
| `is_confidential` | BooleanField | |
| `template` | FK(DocumentTemplate) | Template used to create this doc |
| `template_data` | JSONField | Field values from template |
| `tags` | ArrayField(CharField) | PostgreSQL array, GIN indexed |
| `metadata` | JSONField | Arbitrary additional metadata |
| `created_by` | UUIDField | IAM user ID, indexed |
| `owned_by` | UUIDField | Current owner (may differ from creator) |
| `edited_by` | UUIDField | Last editor |
| `locked_for_editing` | BooleanField | |
| `locked_by` | UUIDField | |
| `locked_at` | DateTimeField | |
| `record_type` | CharField(20) | `permanent` or `non_permanent` |
| `is_archived` | BooleanField | Indexed |
| `archived_at` | DateTimeField | |
| `retention_period` | IntegerField | Years |
| `disposal_date` | DateField | |
| `is_disposed` | BooleanField | |
| `lifecycle_start_date` | DateTimeField | When lifecycle tracking began |
| `active_until` | DateTimeField | Active → Semi-Active transition date |
| `semi_active_until` | DateTimeField | Semi-Active → Inactive transition |
| `active_period_days` | IntegerField | Override for this document |
| `semi_active_period_days` | IntegerField | Override for this document |
| `qr_code_path` | CharField(500) | |
| `qr_code_data` | TextField | |
| `search_vector` | SearchVectorField | PostgreSQL FTS, GIN indexed |

### 5.2 DocumentType

```
Table: document_types
PK: id (UUIDField)
```

Admin-configurable document types replacing the hardcoded enum:

| Field | Type | Notes |
|---|---|---|
| `code` | CharField(50) | Unique, lowercase + hyphens/underscores |
| `name` | CharField(100) | Display name |
| `description` | TextField | |
| `icon` | CharField(50) | UI icon name |
| `color` | CharField(20) | UI color |
| `default_classification` | CharField(50) | Default for new documents of this type |
| `default_retention_period` | IntegerField | Years (nullable) |
| `requires_approval` | BooleanField | |
| `lifecycle_enabled` | BooleanField | Default: True |
| `default_active_period_days` | IntegerField | Default: 1095 (3 years) |
| `default_semi_active_period_days` | IntegerField | Default: 1825 (5 years) |
| `reference_prefix` | CharField(10) | e.g., "CNT" for contracts |
| `is_active` | BooleanField | |
| `is_system` | BooleanField | Cannot be deleted |
| `document_count` | IntegerField | Usage tracking |

### 5.3 DocumentTemplate

```
Table: document_templates (implicit via Meta)
PK: id (UUIDField)
```

| Field | Type | Notes |
|---|---|---|
| `name` | CharField(200) | Unique |
| `description` | TextField | |
| `document_type` | FK(DocumentType) | |
| `template_type` | CharField(20) | `file_based` or `rich_editor` |
| `template_fields` | JSONField | **Deprecated** — use `template_structure` |
| `template_structure` | JSONField | Rich editor component tree |
| `template_file_path` | CharField(1000) | For file-based templates |
| `template_file_name` | CharField(500) | Original filename |
| `template_file_size` | BigIntegerField | |
| `template_file_mime_type` | CharField(100) | |
| `auto_copy_template_file` | BooleanField | Auto-copy file on doc creation |
| `allow_file_editing` | BooleanField | Enable OnlyOffice editing |
| `default_classification` | CharField(50) | |
| `requires_approval` | BooleanField | |
| `auto_generate_reference` | BooleanField | |
| `template_version` | IntegerField | |
| `process_type` | CharField(100) | For automated generation |
| `process_data_mapping` | JSONField | Maps process data to placeholders |
| `usage_count` | IntegerField | |
| `is_active` | BooleanField | |
| `is_system` | BooleanField | |
| `created_by` | UUIDField | IAM user ID |

### 5.4 DocumentVersion

```
Table: document_versions
PK: id (UUIDField)
Unique constraint: (document, version_number)
```

| Field | Type | Notes |
|---|---|---|
| `document` | FK(Document) | |
| `version_number` | IntegerField | |
| `file_path` | CharField(1000) | Snapshot of file at this version |
| `file_size` | BigIntegerField | |
| `change_summary` | TextField | |
| `created_by` | UUIDField | IAM user ID |

### 5.5 DocumentComment

```
Table: document_comments
PK: id (UUIDField)
```

| Field | Type | Notes |
|---|---|---|
| `document` | FK(Document) | |
| `parent_comment` | FK(self) | For nested replies |
| `comment_text` | TextField | |
| `highlighted_text` | TextField | Text being commented on |
| `line_number` | IntegerField | |
| `paragraph_number` | IntegerField | |
| `created_by` | UUIDField | |
| `is_resolved` | BooleanField | |
| `resolved_by` | UUIDField | |
| `mentioned_users` | JSONField | Auto-extracted @mentions |
| `is_private` | BooleanField | Only visible to mentioned users |
| `thread_depth` | IntegerField | Auto-calculated nesting depth |
| `is_edited` | BooleanField | |
| `edit_count` | IntegerField | |

### 5.6 DocumentShare

```
Table: document_shares
PK: id (UUIDField)
Unique constraint: (document, shared_with, principal_type)
```

| Field | Type | Notes |
|---|---|---|
| `document` | FK(Document) | |
| `shared_by` | UUIDField | |
| `shared_with` | UUIDField | User ID, Group ID, or Role ID |
| `principal_type` | CharField(20) | `user`, `group`, or `role` |
| `permission` | CharField(20) | `read`, `comment`, `edit`, `admin` |
| `expires_at` | DateTimeField | For time-limited sharing |
| `is_active` | BooleanField | |
| `message` | TextField | Sharing message |

### 5.7 DocumentApproval

```
Table: document_approvals
PK: id (UUIDField)
```

| Field | Type | Notes |
|---|---|---|
| `document` | FK(Document) | |
| `workflow_type` | CharField(50) | `management`, `commission`, `director`, `dg` |
| `approver_id` | UUIDField | |
| `approval_action` | CharField(50) | `approve`, `reject`, `request_changes` |
| `comments` | TextField | |

### 5.8 DocumentSignature

```
Table: document_signatures
PK: id (UUIDField)
```

| Field | Type | Notes |
|---|---|---|
| `document` | FK(Document) | |
| `signer_id` | UUIDField | |
| `signature_data` | TextField | Encrypted signature data |
| `signature_position` | JSONField | `{x, y, page}` |
| `signature_method` | CharField(50) | `digital` or `scanned` |
| `is_valid` | BooleanField | |
| `workflow_id` | UUIDField | Linked workflow |
| `workflow_step_key` | CharField(100) | |

### 5.9 IncomingRegister

```
Table: incoming_register
PK: id (UUIDField)
```

| Field | Type | Notes |
|---|---|---|
| `register_number` | CharField(100) | Unique |
| `received_date` | DateTimeField | |
| `document_type` | CharField(50) | `internal` or `external` |
| `sender_name` | CharField(500) | |
| `sender_organization` | CharField(500) | |
| `subject` | TextField | |
| `received_by` | UUIDField | Record Officer |
| `current_holder` | UUIDField | Who currently holds it |
| `status` | CharField(50) | `received`, `in_action`, `worked_on`, `completed` |
| `priority` | CharField(50) | `low`, `normal`, `high`, `urgent` |
| `document` | FK(Document) | Optional link to digital document |
| `routing_history` | JSONField | History of document movement |

### 5.10 OutgoingRegister

```
Table: outgoing_register
PK: id (UUIDField)
```

| Field | Type | Notes |
|---|---|---|
| `register_number` | CharField(100) | Unique |
| `dispatch_date` | DateTimeField | |
| `document` | FK(Document) | Optional link |
| `recipient_name` | CharField(500) | |
| `recipient_organization` | CharField(500) | |
| `recipient_email` | EmailField | |
| `dispatch_method` | CharField(50) | `e-office`, `email`, `postal`, `courier` |
| `dispatched_by` | UUIDField | |
| `delivery_status` | CharField(50) | `pending`, `delivered`, `failed`, `returned` |
| `tracking_number` | CharField(200) | |

### 5.11 DisposalForm

```
Table: disposal_forms
PK: id (UUIDField)
```

| Field | Type | Notes |
|---|---|---|
| `form_number` | CharField(100) | Unique |
| `submitted_by` | UUIDField | Record Officer |
| `disposal_reason` | CharField(200) | `retention_period_expired`, `duplicate`, `obsolete`, `damaged` |
| `dg_approval_status` | CharField(50) | `pending`, `approved`, `rejected` |
| `dg_approved_by` | UUIDField | |
| `records_dept_approval_status` | CharField(50) | |
| `records_dept_approved_by` | UUIDField | |
| `disposal_method` | CharField(50) | `shred`, `burn`, `digital_delete`, `transfer_to_archives` |
| `disposal_date` | DateTimeField | Execution date |
| `disposal_certificate_number` | CharField(100) | |
| `orchestration_plan_id` | UUIDField | Unique — links to workflow plan |

### 5.12 Folder

```
Table: folders
PK: id (UUIDField)
Unique constraint: (file_series, first_keyword, second_keyword, planning_number, part_number)
```

| Field | Type | Notes |
|---|---|---|
| `folder_number` | CharField(100) | Unique, auto-generated from components |
| `folder_type` | CharField(20) | `personal` or `subject` |
| `folder_classification` | CharField(20) | `open` or `classified` |
| `file_series` | FK(FileSeries) | FCC organizational code |
| `first_keyword` | FK(Keyword) | Primary classification |
| `second_keyword` | FK(Keyword) | Optional secondary |
| `planning_number` | CharField(4) | Zero-padded (00-99) |
| `part_number` | CharField(2) | Single letter (A-Z) |
| `subject` | CharField(255) | |
| `department` | CharField(255) | |
| `state` | CharField(20) | `open` or `closed` |
| `document_count` | IntegerField | |
| `max_documents` | IntegerField | Default: 100 |
| `capacity_warning_at` | IntegerField | Warn at this % (default: 90) |
| `auto_close_at` | IntegerField | Auto-close at this % (default: 100) |
| `created_by` | UUIDField | |
| `owned_by` | UUIDField | For personal folders |

### 5.13 Supporting Models

| Model | Table | Purpose |
|---|---|---|
| `FileSeries` | `file_series` | FCC organizational codes (e.g., HA = Legal Services) |
| `Keyword` | `keywords` | Classification keywords for folders |
| `FolderDocument` | `folder_documents` | Many-to-many: Folder ↔ Document |
| `FolderAccessRequest` | `folder_access_requests` | Access request workflow for folders/documents |
| `FolderActivity` | `folder_activities` | Audit trail for folder operations |
| `RegisterDocumentAttachment` | `register_document_attachments` | Multiple documents per register entry |
| `DisposalFormDocument` | `disposal_form_documents` | Documents included in a disposal form |
| `DocumentAccessLog` | `document_access_logs` | Audit trail for document access events |
| `DocumentChangeLog` | `document_change_logs` | Field-level change tracking for documents |
| `ReportTemplate` | `report_templates` | Templates for scheduled/on-demand reports |
| `GeneratedReport` | `generated_reports` | History of generated reports |
| `TemplateUsage` | `template_usage` | Tracks template usage by users |
| `StorageLocation` | `storage_locations` | Physical storage buildings/warehouses |
| `StorageFloor` | `storage_floors` | Floors/sections within locations |
| `DocumentPhysicalStorage` | `document_physical_storage` | Physical location of document copies |
| `StorageThresholdAlert` | `storage_threshold_alerts` | Storage capacity alerts |

---

## 6. Complete API Surface

### 6.1 Document CRUD & File Operations

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/` | GET | Bearer | List documents (paginated, filterable, searchable) |
| `/documents/` | POST | Bearer | Create document |
| `/documents/<uuid>/` | GET | Bearer | Document detail |
| `/documents/<uuid>/` | PUT/PATCH | Bearer | Update document |
| `/documents/<uuid>/` | DELETE | Bearer | Soft-delete document |
| `/documents/<uuid>/upload/` | POST | Bearer | Upload file to existing document |
| `/documents/<uuid>/download/` | GET | Bearer | Download document file |
| `/documents/<uuid>/preview/` | GET | Bearer | Preview document |
| `/documents/<uuid>/file-access/` | GET | Bearer | Get file access URL |
| `/documents/<uuid>/qr/` | GET | Bearer | Get QR code for document |
| `/documents/<uuid>/thumbnail/` | GET | Bearer | Get document thumbnail |
| `/documents/<uuid>/permanent/` | DELETE | Admin | Permanently delete disposed document |
| `/documents/automation/` | GET/PUT | Admin | Automation settings |
| `/documents/tags/` | GET | Bearer | List all used tags |

### 6.2 Versioning & Revert

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/<uuid>/versions/` | GET/POST | Bearer | List versions / Create new version |
| `/documents/<uuid>/new-version/` | POST | Bearer | Create new version |
| `/documents/<uuid>/version-history/` | GET | Bearer | Full version history |
| `/documents/<uuid>/versions/<int>/` | GET | Bearer | Specific version detail |
| `/documents/<uuid>/compare/` | GET | Bearer | Compare two versions |
| `/documents/<uuid>/revert/` | POST | Bearer | Revert document to previous version |
| `/documents/<uuid>/revert-fields/` | POST | Bearer | Revert specific fields only |
| `/documents/<uuid>/revert-history/` | GET | Bearer | Revert operation history |
| `/documents/<uuid>/versions/<int>/changes/` | GET | Bearer | Changes in a specific version |

### 6.3 Status & Locking

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/<uuid>/status/` | POST | Bearer | Change document status |
| `/documents/<uuid>/archive/` | POST | Bearer | Archive document |
| `/documents/<uuid>/restore/` | POST | Bearer | Restore archived document |
| `/documents/<uuid>/mark-eligible-for-disposal/` | POST | Bearer | Mark for disposal |
| `/documents/<uuid>/lock/` | POST | Bearer | Lock document for editing |
| `/documents/<uuid>/unlock/` | POST | Bearer | Unlock document |

### 6.4 Approval & Workflow

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/<uuid>/submit-for-approval/` | POST | Bearer | Submit for approval workflow |
| `/documents/<uuid>/approve/` | POST | Bearer | Approve/reject document |
| `/documents/<uuid>/approval-status/` | GET | Bearer | Current approval status |
| `/documents/<uuid>/approvals/` | GET | Bearer | Approval history |
| `/documents/approvals/stats/` | GET | Bearer | Approval statistics |
| `/documents/workflows/` | GET | Bearer | List workflow instances |
| `/documents/workflows/start/` | POST | Bearer | Start new workflow |
| `/documents/workflows/<uuid>/action/` | POST | Bearer | Execute workflow action |
| `/documents/workflows/<uuid>/status/` | GET | Bearer | Workflow status |
| `/documents/workflows/<uuid>/available-actions/` | GET | Bearer | Available workflow actions |
| `/documents/workflows/<uuid>/detail/` | GET | Bearer | Workflow instance detail |
| `/documents/workflows/approvals/pending/` | GET | Bearer | Pending approvals for current user |
| `/documents/workflows/approvals/history/<uuid>/` | GET | Bearer | Approval history for document |
| `/documents/workflows/<uuid>/reassign/` | POST | Admin | Reassign approval |
| `/documents/workflows/<uuid>/override/` | POST | Admin | Override approval decision |
| `/documents/workflows/<uuid>/force-complete/` | POST | Admin | Force-complete workflow |

### 6.5 Sharing & Collaboration

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/<uuid>/shares/` | GET/POST | Bearer | List/create shares for document |
| `/documents/document-shares/<uuid>/` | GET/PUT/DELETE | Bearer | Manage specific share |
| `/documents/document-shares/my-shares/` | GET | Bearer | Documents I shared |
| `/documents/document-shares/shared-with-me/` | GET | Bearer | Documents shared with me |
| `/documents/document-shares/bulk/` | POST | Bearer | Bulk share documents |
| `/documents/access-requests/bulk/` | POST | Bearer | Bulk access request |
| `/documents/collaboration/stats/` | GET | Bearer | Collaboration statistics |

### 6.6 Comments

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/<uuid>/comments/` | GET/POST | Bearer | List/create comments |
| `/documents/document-comments/<uuid>/` | GET/PUT/DELETE | Bearer | Manage specific comment |
| `/documents/document-comments/<uuid>/reply/` | POST | Bearer | Reply to comment |
| `/documents/document-comments/<uuid>/resolve/` | POST | Bearer | Resolve comment |
| `/comments/` | GET | Bearer | Standalone comment listing |

### 6.7 Signatures

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/<uuid>/signatures/` | GET | Bearer | List signatures |
| `/documents/<uuid>/signatures/request/` | POST | Bearer | Request signature |
| `/documents/<uuid>/signatures/<uuid>/` | GET/DELETE | Bearer | Signature detail |
| `/documents/<uuid>/signatures/<uuid>/upload/` | POST | Bearer | Upload signature |
| `/documents/<uuid>/signatures/<uuid>/validate/` | POST | Bearer | Validate signature |
| `/documents/signatures/my/` | GET | Bearer | My pending signature requests |

### 6.8 Physical Storage & Ownership

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/<uuid>/physical-storage/` | GET | Bearer | Get physical storage info |
| `/documents/<uuid>/physical-storage/create/` | POST | Bearer | Record physical storage |
| `/documents/<uuid>/transfer-ownership/` | POST | Bearer | Transfer document ownership |

### 6.9 Search & Stats

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/search/` | GET | Bearer | Full-text search |
| `/documents/search/suggestions/` | GET | Bearer | Autocomplete suggestions |
| `/documents/stats/` | GET | Bearer | Document statistics |
| `/documents/storage/stats/` | GET | Bearer | Storage usage stats |
| `/documents/storage/monitoring/stats/` | GET | Bearer | Storage monitoring dashboard |
| `/documents/storage/monitoring/alerts/` | GET/POST | Bearer | Storage threshold alerts |
| `/documents/storage/monitoring/alerts/<uuid>/resolve/` | POST | Bearer | Resolve alert |

### 6.10 Document Types

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/document-types/` | GET | Bearer | List all document types |
| `/document-types/` | POST | Admin | Create document type |
| `/document-types/<uuid>/` | GET/PUT/PATCH/DELETE | Admin | Manage document type |

### 6.11 Document Templates

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/document-templates/` | GET/POST | Bearer | List/create templates |
| `/document-templates/<uuid>/` | GET/PUT/PATCH/DELETE | Bearer | Manage template |

### 6.12 Template Versions & Workflows

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/template-versions/` | GET/POST | Bearer | Template version management |
| `/template-versions/<uuid>/` | GET/PUT/DELETE | Bearer | Specific version |
| `/template-versions/rollbacks/` | GET/POST | Bearer | Rollback operations |
| `/template-versions/change-logs/` | GET | Bearer | Change log history |
| `/template-workflows/workflows/` | GET/POST | Bearer | Template workflow management |
| `/template-workflows/change-requests/` | GET/POST | Bearer | Change requests |
| `/template-workflows/assignments/` | GET/POST | Bearer | Workflow assignments |

### 6.13 Incoming Register

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/incoming-register/` | GET/POST | Bearer | List/create entries |
| `/documents/incoming-register/<uuid>/` | GET/PUT/PATCH | Bearer | Entry detail/update |
| `/documents/incoming-register/<uuid>/route/` | POST | Bearer | Route document to holder |
| `/documents/incoming-register/my-inbox/` | GET | Bearer | Documents routed to me |
| `/documents/incoming-register/stats/` | GET | Bearer | Register statistics |
| `/documents/incoming-register/<uuid>/upload/` | POST | Bearer | Upload file attachment |
| `/documents/incoming-register/<uuid>/files/` | GET | Bearer | List file attachments |

### 6.14 Outgoing Register

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/outgoing-register/` | GET/POST | Bearer | List/create entries |
| `/documents/outgoing-register/<uuid>/` | GET/PUT/PATCH | Bearer | Entry detail/update |
| `/documents/outgoing-register/<uuid>/confirm-delivery/` | POST | Bearer | Confirm delivery |
| `/documents/outgoing-register/pending/` | GET | Bearer | Pending deliveries |
| `/documents/outgoing-register/stats/` | GET | Bearer | Register statistics |
| `/documents/outgoing-register/<uuid>/upload/` | POST | Bearer | Upload file attachment |
| `/documents/outgoing-register/<uuid>/files/` | GET | Bearer | List file attachments |

### 6.15 Register Files (Shared)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/register-files/<uuid>/download/` | GET | Bearer | Download attachment |
| `/documents/register-files/<uuid>/` | DELETE | Bearer | Delete attachment |

### 6.16 Disposal

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/disposal-forms/` | GET/POST | Bearer | List/create disposal forms |
| `/documents/disposal-forms/<uuid>/` | GET | Bearer | Disposal form detail |
| `/documents/disposal-forms/<uuid>/dg-approve/` | POST | DG role | DG approval |
| `/documents/disposal-forms/<uuid>/records-dept-approve/` | POST | Records role | Records dept approval |
| `/documents/disposal-forms/<uuid>/execute-disposal/` | POST | Admin | Execute disposal |
| `/documents/disposal-forms/<uuid>/status/` | GET | Bearer | Disposal status |
| `/documents/disposal-forms/eligible-documents/` | GET | Bearer | Documents eligible for disposal |
| `/documents/disposal-forms/stats/` | GET | Bearer | Disposal statistics |

### 6.17 Reports

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/report-templates/` | GET/POST | Bearer | List/create report templates |
| `/report-templates/<uuid>/` | GET/PUT/DELETE | Bearer | Manage template |
| `/reports/generate/` | POST | Bearer | Generate report |
| `/reports/` | GET | Bearer | List generated reports |
| `/reports/<uuid>/` | GET | Bearer | Report detail |
| `/reports/<uuid>/download/` | GET | Bearer | Download report |
| `/reports/summary/` | GET | Bearer | Report summary dashboard |

### 6.18 Folders

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/folders/` | GET/POST | Bearer | List/create folders |
| `/folders/<uuid>/` | GET/PUT/PATCH/DELETE | Bearer | Folder CRUD |
| `/folders/file-series/` | GET/POST | Bearer | File series management |
| `/folders/file-series/<uuid>/` | GET/PUT/DELETE | Bearer | Manage file series |
| `/folders/keywords/` | GET/POST | Bearer | Keyword management |
| `/folders/keywords/<uuid>/` | GET/PUT/DELETE | Bearer | Manage keyword |
| `/folders/access-requests/` | GET/POST | Bearer | Access request management |
| `/folders/access-requests/<uuid>/` | GET/PUT/DELETE | Bearer | Manage specific request |

### 6.19 Storage Locations

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/storage-locations/` | GET/POST | Bearer | List/create locations |
| `/storage-locations/<uuid>/` | GET/PUT/PATCH/DELETE | Bearer | Manage location |
| `/storage-locations/floors/` | GET/POST | Bearer | List/create floors |
| `/storage-locations/floors/<uuid>/` | GET/PUT/PATCH/DELETE | Bearer | Manage floor |

### 6.20 OnlyOffice Integration

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/documents/onlyoffice/callback/` | POST | Special | OnlyOffice save callback |
| `/documents/onlyoffice/<uuid>/config/` | GET | Bearer | Editor config for document |

### 6.21 Health & Metrics

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health/` | GET | Public | Service health check |
| `/metrics/` | GET | Public | Prometheus metrics |

---

## 7. Document Lifecycle & Status Machine

### 7.1 Status Transitions

```
                   ┌──────────────┐
                   │    draft     │──────────────────────────────┐
                   └──────┬───────┘                              │
                          │ submit-for-approval                  │
                          ▼                                      │
                   ┌──────────────┐                              │
                   │ under_review │                              │
                   └──────┬───────┘                              │
                   ┌──────┴──────┐                               │
               approve        reject                             │
                   │              │                               │
                   ▼              ▼                               │
            ┌───────────┐  ┌───────────┐                         │
            │ approved  │  │ rejected  │─── revise ──────────────┘
            └─────┬─────┘  └───────────┘
                  │ lifecycle starts
                  ▼
            ┌───────────┐
            │  active   │  (active_period_days from type config)
            └─────┬─────┘
                  │ active_until date passes
                  ▼
          ┌───────────────┐
          │  semi_active  │  (semi_active_period_days from type config)
          └───────┬───────┘
                  │ semi_active_until date passes
                  ▼
            ┌───────────┐
            │ inactive  │
            └─────┬─────┘
                  │ retention period expires
                  ▼
    ┌──────────────────────────────┐
    │ eligible_for_decongestion    │
    └──────────────┬───────────────┘
                   │ disposal form created + approved
                   ▼
            ┌───────────┐
            │ archived  │  (or disposed directly)
            └─────┬─────┘
                  │ disposal executed
                  ▼
            ┌───────────┐
            │ disposed  │  (permanent deletion possible)
            └───────────┘
```

### 7.2 Lifecycle Period Tracking

When a document becomes `active`:
1. `lifecycle_start_date` is set to current time
2. `active_until` = start + `active_period_days` (from DocumentType or override)
3. `semi_active_until` = start + `semi_active_period_days` (from DocumentType or override)

Celery tasks (`lifecycle_tasks`, `decongestion_tasks`) periodically check these dates and transition documents automatically.

---

## 8. Workflow Integration (Work Orchestration)

### 8.1 Architecture Overview

```
┌─────────────────────────────────────┐
│  Document Records Service           │
│                                     │
│  ┌───────────────────────┐         │
│  │ WorkflowOrchestrator  │         │         ┌────────────────────┐
│  │                       │         │         │ work-orchestration │
│  │  ┌─────────────────┐  │         │  REST   │ service            │
│  │  │ WorkOrchestration│──│─────────│────────>│                    │
│  │  │ Adapter          │  │         │         │ Plans, Stages,     │
│  │  └─────────────────┘  │         │         │ Tasks, Templates   │
│  │  ┌─────────────────┐  │         │         └────────────────────┘
│  │  │ DisposalWorkflow │  │         │
│  │  │ Adapter          │  │         │
│  │  └─────────────────┘  │         │
│  │  ┌─────────────────┐  │         │
│  │  │ ApprovalWorkflow │  │         │
│  │  │ Adapter          │  │         │
│  │  └─────────────────┘  │         │
│  └───────────────────────┘         │
└─────────────────────────────────────┘
```

### 8.2 WorkOrchestrationClient

The `WorkOrchestrationClient` is an HTTP client with circuit breaker protection:

```python
class WorkOrchestrationClient:
    def __init__(self):
        self.base_url = settings.WORK_ORCHESTRATION_SERVICE_URL
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )

    def create_plan(self, workflow_type, template_id, created_by, metadata, ...) → dict
    def advance_stage(self, plan_id, action, user_id, ...) → dict
    def update_stage(self, plan_id, stage_id, ...) → dict
    def update_plan(self, plan_id, ...) → dict
    def get_plan(self, plan_id) → dict
    def list_plans(...) → dict
    def list_templates(...) → dict
    def list_notification_templates(...) → dict
    def create_notification_template(payload) → dict
    def check_health() → dict
```

**Circuit Breaker States:**
- **Closed** (normal): Requests pass through
- **Open** (after 5 consecutive failures): All requests fail-fast for 60s
- **Half-Open** (after recovery timeout): One test request allowed

### 8.3 How Document Approval Works

1. User calls `POST /documents/<id>/submit-for-approval/`
2. `ApprovalActionHandler.initialize_workflow()` creates the workflow plan
3. The adapter calls `WorkOrchestrationClient.create_plan()` with document metadata
4. Work-orchestration-service returns `plan_id`
5. Document's `orchestration_plan_id` is set to this ID
6. Document status changes to `under_review`
7. When approver acts: `POST /documents/<id>/approve/` with `{action: "approve"}`
8. Adapter calls `WorkOrchestrationClient.advance_stage()`
9. Periodic sync task (`sync_document_status_from_plans`) polls plan status and updates document

### 8.4 How Disposal Workflow Works

1. Disposal form created → `DisposalWorkflowAdapter.start_workflow()`
2. Creates plan in work-orchestration with stages: DG approval → Records Dept approval
3. Approval actions route through `execute_step()` → updates disposal form fields
4. When both approvals complete → mark as ready for disposal execution
5. Auto-execute task runs every 6 hours for fully-approved digital disposals

---

## 9. OnlyOffice Integration

Document-records-service integrates with OnlyOffice Docs for in-browser document editing:

### 9.1 Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /documents/onlyoffice/<uuid>/config/` | Returns OnlyOffice editor config JSON (document URL, callback URL, permissions) |
| `POST /documents/onlyoffice/callback/` | OnlyOffice calls this when user saves — receives the edited document file |

### 9.2 Editing Flow

```
Browser                  Document Records              OnlyOffice Docs
  │                           │                              │
  │ GET /onlyoffice/config/   │                              │
  │──────────────────────────>│                              │
  │                           │  Generate JWT-signed config   │
  │  { documentUrl, callback, │                              │
  │    permissions, token }   │                              │
  │<──────────────────────────│                              │
  │                           │                              │
  │ Open editor (JS SDK)      │                              │
  │──────────────────────────────────────────────────────────>│
  │                           │                              │
  │                           │  GET documentUrl (download)   │
  │                           │<──────────────────────────────│
  │                           │                              │
  │  ... user edits ...       │                              │
  │                           │                              │
  │                           │  POST /onlyoffice/callback/  │
  │                           │<──────────────────────────────│
  │                           │  { status, url, key }         │
  │                           │  Download edited file from url │
  │                           │  Save new version             │
  │                           │  Return { error: 0 }          │
  │                           │──────────────────────────────>│
```

---

## 10. Cross-Service Dependencies & Collaboration

### 10.1 Document Records → IAM Service

| Interaction | Type | Details |
|---|---|---|
| JWT validation | Local decode | JWTPermissionMiddleware with shared JWT_SECRET_KEY |
| User lookup | REST + cache | `IAMClient` → `GET /api/v1/users/lookup/id/<id>/` with 5-min Redis TTL |
| Permission registration | Kafka producer | Publishes to `service.permission.registry` |

### 10.2 Document Records → Work Orchestration Service

| Interaction | Type | Details |
|---|---|---|
| Create workflow plan | REST | `WorkOrchestrationClient.create_plan()` |
| Advance workflow stage | REST | `WorkOrchestrationClient.advance_stage()` |
| Get plan status | REST | `WorkOrchestrationClient.get_plan()` |
| List templates | REST | `WorkOrchestrationClient.list_templates()` |
| Manage notification templates | REST | `create_notification_template()`, `list_notification_templates()` |
| Send notifications | Kafka | `NotificationPublisher` → priority topics |
| Circuit breaker protection | Local | 5 failures → 60s lockout |

### 10.3 Document Records ← IAM Service

| Interaction | Type | Details |
|---|---|---|
| User profile changes | Kafka consumer | `fims.iam.user.updated` → update cached user data |

### 10.4 Document Records ← Other Services

| Interaction | Type | Details |
|---|---|---|
| Document upload/download | REST | Via document CRUD endpoints |
| Document status queries | REST | Via detail and search endpoints |
| Domain event consumption | Kafka | `fims.documents.events` |

### 10.5 Dependency Graph

```
                    ┌──────────────────────────────────────────┐
                    │      document-records-service             │
                    │                                          │
  JWT validation    │  ┌─────────────────┐                     │
  (local decode)    │  │ JWTPermission   │                     │
                    │  │ Middleware       │                     │
  IAM user lookup   │  ├─────────────────┤  ┌───────────────┐  │
  (REST + cache) ───│──│ IAMClient       │  │ Notification  │──│── Kafka ──> work-orchestration
                    │  │ (5min Redis TTL)│  │ Publisher     │  │            (email delivery)
                    │  ├─────────────────┤  └───────────────┘  │
  Perm registration │  │ Permission      │                     │
  (Kafka producer)──│──│ Publisher       │  ┌───────────────┐  │
                    │  └─────────────────┘  │ WorkOrch      │──│── REST ──> work-orchestration
                    │                       │ Client        │  │            (plans, stages)
                    │  ┌─────────────────┐  │ (+circuit     │  │
                    │  │ OnlyOffice      │  │  breaker)     │  │
                    │  │ Integration     │  └───────────────┘  │
                    │  └─────────────────┘                     │
                    │                                          │
  All services ─────│── REST → /api/v1/documents/*             │
  (doc upload/      │                                          │
   download)        │── Kafka → fims.documents.events          │
                    │   (domain events for consumers)          │
                    └──────────────────────────────────────────┘
```

---

## 11. Notification Publishing

Document-records-service uses `NotificationPublisher` (identical pattern to other FIMS services) to send all notifications via Kafka:

**Topics used (priority-based routing):**
- `notifications-urgent` — critical alerts
- `notifications-high` — approval requests, signature requests
- `notifications-normal` — status changes, shares
- `notifications-low` — weekly reports, reminders

**Notification template codes published:**
- `document.approval.request` — approval needed
- `document.approval.completed` — approval done
- `document.shared` — document shared with user
- `document.comment.mention` — @mentioned in comment
- `document.signature.request` — signature requested
- `document.deadline.reminder` — deadline approaching
- `document.disposal.approval.request` — disposal needs approval
- `document.disposal.reminder` — pending disposal reminder
- `document.access_request.submitted` — access request submitted
- `document.access_request.approved` — access request approved
- `document.access_request.escalation` — escalation alert
- `document.storage.threshold.warning` — storage threshold warning
- `document.storage.threshold.critical` — storage threshold critical

---

## 12. Permission Registration

Document-records-service registers **100+ permissions** with IAM via Kafka topic `service.permission.registry`.

### 12.1 Permission Categories

| Category | Example Codes | Count |
|---|---|---|
| **Template Management** | `document:template:create/read/update/delete/bulk_operations/import_export/version_management/analytics` | 8 |
| **Document CRUD** | `document:document:create/read/update/delete/permanent_delete/approve/reject` | 7 |
| **Document Types** | `document:document_type:create/read/update/delete` | 4 |
| **Document Categories** | `document:document_category:create/read/update/delete` | 4 |
| **Classification** | `document:classification:public/internal/confidential/secret` | 4 |
| **Incoming Register** | `document:incoming_register:create/read/update/route` | 4 |
| **Outgoing Register** | `document:outgoing_register:create/read/update/confirm_delivery` | 4 |
| **Disposal** | `document:disposal:create/read/dg_approve/records_dept_approve/execute/view_eligible` | 6 |
| **Collaboration** | `collaboration:read/write/share/comment/admin` | 5 |
| **System** | `document:system:admin/audit/storage_monitoring` | 3 |
| **Storage Locations** | `document:storage_location:read/create/update/delete` | 4 |
| **Physical Storage** | `document:physical_storage:read/create/update/delete` | 4 |
| **Folders** | `document:folder:read/create/update/delete/manage_documents/manage_shares/close_reopen` | 7 |
| **File Series** | `document:file_series:read/create/update/delete` | 4 |
| **Keywords** | `document:keyword:read/create/update/delete` | 4 |
| **Access Requests** | `document:folder_access_request:read/create/approve/reject/manage/cancel` | 6 |
| **Report Templates** | `document:report_template:read/create/update/delete` | 4 |
| **Reports** | `document:report:read/create/delete` | 3 |
| **Workflows** | `document:workflow:read/execute` | 2 |
| **Template Workflows** | `document:template_workflow:read/create/update/delete` | 4 |
| **Template Versions** | `document:template_version:read/manage` | 2 |
| **Document Versions** | `document:document_version:read/create/restore` | 3 |
| **Signatures** | `document:signature:read/create/upload/validate` | 4 |
| **Automation** | `document:automation:read/manage` | 2 |

### 12.2 Permission Code Convention

Format: `domain:resource:action`

- `document:` prefix for most resource-based permissions
- `collaboration:` prefix for sharing/commenting
- Colon-separated (note: this service uses `:` rather than `.` as separator)

---

## 13. Background Tasks (Celery)

The document-records-service runs 18 scheduled Celery tasks:

| Task | Schedule | Purpose |
|---|---|---|
| `archive_old_documents` | Daily 2:00 AM | auto-archive documents past retention |
| `cleanup_temp_files` | Daily 1:00 AM | Remove temporary upload files |
| `cleanup_old_reports` | Weekly Sunday 3:00 AM | Delete old generated reports |
| `send_deadline_reminders` | Daily 9:00 AM | Send deadline approaching notifications |
| `auto_create_disposal_forms` | Daily 4:00 AM | Create disposal forms for eligible documents |
| `auto_execute_fully_approved_disposals` | Every 6 hours | Execute approved digital disposals |
| `remind_pending_disposal_approvals` | Daily 8:30 AM | Remind approvers of pending disposals |
| `process_deferred_plan_creations` | Every 15 minutes | Retry failed workflow plan creations |
| `check_retention_periods_and_mark_eligible` | Daily 2:00 AM | Mark documents eligible for decongestion |
| `check_storage_thresholds` | Every hour | Monitor storage capacity, create alerts |
| `sync_document_status_from_plans` | Every 10 minutes | Poll orchestration for document workflow updates |
| `sync_disposal_form_status_from_plans` | Every 10 minutes | Poll orchestration for disposal workflow updates |
| `check_orphaned_orchestration_plans` | Daily 3:00 AM | Find plans with no matching document |
| `check_missing_orchestration_plans` | Daily 4:00 AM | Find documents with plan IDs but no plan |
| `reconcile_all_workflow_statuses` | Daily 5:00 AM | Comprehensive workflow status sync |
| `run_scheduled_reports` | Hourly | Execute scheduled report generation |
| `check_access_request_escalations` | Daily 8:00 AM | Escalate overdue access requests |
| `generate_access_request_report` | Weekly Monday 9:00 AM + Monthly 1st | Generate access request analytics reports |

---

## 14. How Other Services Consume Document Records

### 14.1 Uploading a Document (from any service)

```python
import requests

# Upload a document with metadata
files = {'file': ('report.pdf', open('report.pdf', 'rb'), 'application/pdf')}
data = {
    'title': 'Monthly Financial Report',
    'document_type_ref': '<document-type-uuid>',
    'classification': 'confidential',
    'tags': ['finance', 'monthly', 'report'],
    'description': 'Financial report for January 2026'
}

response = requests.post(
    f'{settings.DOCUMENT_SERVICE_URL}/api/v1/documents/',
    files=files,
    data=data,
    headers={'Authorization': f'Bearer {jwt_token}'}
)

document_id = response.json()['id']
# Store document_id (UUID) as a reference in your service's models
```

### 14.2 Referencing Documents in Your Models

```python
# In your service's models.py — Store UUID reference, NOT a ForeignKey
class MyBusinessEntity(models.Model):
    name = models.CharField(max_length=200)
    supporting_document_id = models.UUIDField(
        null=True, blank=True,
        help_text="Document UUID from document-records-service"
    )
    attachments = ArrayField(
        models.UUIDField(),
        default=list,
        help_text="List of document UUIDs"
    )
```

### 14.3 Downloading a Document

```python
response = requests.get(
    f'{settings.DOCUMENT_SERVICE_URL}/api/v1/documents/{document_id}/download/',
    headers={'Authorization': f'Bearer {jwt_token}'},
    stream=True
)
# response.content contains the file bytes
# response.headers['Content-Disposition'] contains the filename
```

### 14.4 Checking Document Status

```python
response = requests.get(
    f'{settings.DOCUMENT_SERVICE_URL}/api/v1/documents/{document_id}/',
    headers={'Authorization': f'Bearer {jwt_token}'}
)
doc = response.json()
# doc['status'] — 'draft', 'approved', 'active', etc.
# doc['reference_number'] — 'FCC-2026-RPT-00001'
```

---

## 15. Integration Guide for New Services

### Step 1: Store Document UUIDs, Not Files

Never store files locally. Always upload to document-records-service and store the returned UUID.

### Step 2: Use the DOCUMENT_SERVICE_URL

In your `.env`:
```
DOCUMENT_SERVICE_URL=http://document-records-service:8002
```

### Step 3: Create a Document Client Class

```python
import requests
from django.conf import settings

class DocumentClient:
    def __init__(self):
        self.base_url = settings.DOCUMENT_SERVICE_URL

    def upload(self, file, metadata, token):
        return requests.post(
            f'{self.base_url}/api/v1/documents/',
            files={'file': file},
            data=metadata,
            headers={'Authorization': f'Bearer {token}'}
        ).json()

    def get_metadata(self, document_id, token):
        return requests.get(
            f'{self.base_url}/api/v1/documents/{document_id}/',
            headers={'Authorization': f'Bearer {token}'}
        ).json()

    def download(self, document_id, token):
        return requests.get(
            f'{self.base_url}/api/v1/documents/{document_id}/download/',
            headers={'Authorization': f'Bearer {token}'},
            stream=True
        )
```

### Step 4: Subscribe to Document Events (Optional)

If you need to react to document state changes:
```python
# Consume from Kafka topic: fims.documents.events
consumer = KafkaConsumer(
    'fims.documents.events',
    bootstrap_servers='fims-kafka:9092',
    group_id='my-service-documents-group'
)
```

---

## 16. Architectural Boundaries — What Not To Do

### Never Store Files in Your Service
Document-records-service is the sole file storage authority. Store only the document UUID.

### Never Re-implement Document Versioning
Document versioning, comparison, and revert are implemented here. Don't build it again.

### Never Build a Document Approval Workflow in Your Service
Submit documents for approval via the document-records API. It handles routing to work-orchestration.

### Never Manipulate Document Status Directly
Always go through the status change API. The service enforces valid transitions and tracks lifecycle dates.

### Never Build a File Upload/Download API
If you need to attach files to your business entities, upload them to document-records and reference the UUID.

### Never Implement Your Own Search
Use the `/documents/search/` endpoint. It uses PostgreSQL full-text search with GIN indexes — far more performant than DIY.

### Never Connect to the Document Database
Each service has its own database. Access document data only through REST APIs or Kafka events.

### Never Bypass the Classification System
If a document is classified as `confidential`, the document-records-service enforces access control. Don't try to serve confidential document content directly.

### Never Create Your Own Folder System
The e-Office folder system (file series, keywords, planning numbers) is fully managed here. Use the folder API.

---

*This document was derived from direct code analysis of the document-records-service codebase. All endpoints, models, flows, and integration patterns described here are based on actual implementation evidence.*
