# FIMS Platform Architecture — Internal System Reference

> **Document Type:** Internal Architecture Whitepaper  
> **Audience:** Backend engineers building or extending services within FIMS  
> **Last Updated:** 2026-02-24  
> **Status:** Evidence-based reverse-engineering from production codebase

---

## Table of Contents

1. [High-Level Overview & Architectural Philosophy](#1-high-level-overview--architectural-philosophy)
2. [Service Inventory & Boundaries](#2-service-inventory--boundaries)
3. [Cross-Service Communication Mechanisms](#3-cross-service-communication-mechanisms)
4. [Authentication & Authorization Architecture](#4-authentication--authorization-architecture)
5. [Shared Domain Services & Delegation Model](#5-shared-domain-services--delegation-model)
6. [Architectural Conventions](#6-architectural-conventions)
7. [Dependency Philosophy — What Must Never Be Duplicated](#7-dependency-philosophy--what-must-never-be-duplicated)
8. [Step-by-Step Guide: Building a New FIMS Service](#8-step-by-step-guide-building-a-new-fims-service)
9. [Common Architectural Mistakes to Avoid](#9-common-architectural-mistakes-to-avoid)

---

## 1. High-Level Overview & Architectural Philosophy

### 1.1 What is FIMS?

FIMS (**F**air Competition Commission **I**ntegrated **M**anagement **S**ystem) is a microservices-based enterprise platform built for the Fair Competition Commission (FCC) of Tanzania. It manages the full lifecycle of regulatory operations including document management, client registration, corporate HR/finance/procurement, workflow orchestration, identity and access management, and governance/risk/compliance (GRC).

### 1.2 Core Architectural Principles

**Principle 1 — Domain Ownership Without Duplication.**  
Each service owns exactly one business domain. If a capability belongs to another service's domain, the consuming service **delegates** to that service. Services must never re-implement functionality that belongs to a dedicated domain service.

**Principle 2 — Centralized Domain Services.**  
Three services serve as platform-wide infrastructure that other services consume:
- **IAM Service** — sole authority for identity, authentication, roles, permissions, sessions, and audit
- **Document Records Service** — sole authority for all document storage, metadata, versioning, workflows, disposal, and records management
- **Work Orchestration Service** — sole authority for workflow plans/stages/tasks, notification templates, notification delivery (email/SMS/in-app), and reminders

**Principle 3 — JWT-Based Shared Trust.**  
All services validate JWTs locally using a shared secret. Once IAM issues a token, no downstream service needs to call IAM at runtime for authentication. Permissions are embedded in the JWT payload.

**Principle 4 — Event-Driven Decoupling Via Kafka.**  
Services communicate asynchronously through Apache Kafka. Synchronous REST calls are reserved for user-facing API requests and time-sensitive service-to-service queries (e.g., fetching a workflow plan status).

**Principle 5 — Database-Per-Service Isolation.**  
Every service has its own PostgreSQL instance. No shared databases. Cross-service data is accessed only through APIs or events.

### 1.3 Technology Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django 4.2 + Django REST Framework |
| API Docs | drf-spectacular (OpenAPI 3.0) |
| Authentication | djangorestframework-simplejwt (HS256 shared secret) |
| Database | PostgreSQL 15 (per-service instance) |
| Cache / Session / Celery Broker | Redis 7 (per-service instance) |
| Async Task Queue | Celery 5.3 + Celery Beat |
| Message Broker | Apache Kafka (Confluent 7.4) with Zookeeper |
| API Gateway | NGINX (custom routing, CORS, rate limiting) |
| Frontend | React + TypeScript + Vite (monorepo: staff-portal, client-portal) |
| Container Orchestration | Docker Compose (fims-network shared Docker network) |
| Production Server | Gunicorn |
| Monitoring | Prometheus metrics endpoints per service |
| Service Registry (planned) | Consul |

### 1.4 Network Topology

```
┌─ Browser ──────────────────────────────────────────────────────┐
│  staff-portal (fcc-staff.tunnel.ictpack.net)                   │
│  client-portal (fcc-client.tunnel.ictpack.net)                 │
└────────────────────────────┬───────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─ API Gateway (NGINX) ─ :8080 ─────────────────────────────────┐
│  CORS, rate limiting, path-based routing, SSL termination      │
│  /api/v1/auth/*, /api/v1/users/*  → iam-service:8000          │
│  /api/v1/documents/*              → document-records:8002      │
│  /api/v1/workflow/*               → work-orchestration:8004    │
│  /api/v1/clients/*                → client-service:8006        │
│  /api/v1/corporate/*              → corporate-service:8008     │
│  /api/v1/grc/*                    → grc-service:8006           │
└────────────────────────────┬───────────────────────────────────┘
                             │ HTTP
                             ▼
┌─ fims-network (Docker bridge network) ─────────────────────────┐
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ iam-service  │  │ doc-records  │  │ work-orchestration │    │
│  │ :8000        │  │ :8002        │  │ :8004              │    │
│  │ + PostgreSQL │  │ + PostgreSQL │  │ + PostgreSQL       │    │
│  │ + Redis      │  │ + Redis      │  │ + Redis            │    │
│  │ + Celery     │  │ + Celery     │  │ + Celery           │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│                                                                 │
│  ┌──────────────┐  ┌────────────────┐  ┌───────────┐          │
│  │ client-svc   │  │ corporate-svc  │  │ grc-svc   │          │
│  │ :8006        │  │ :8008          │  │ :8006     │          │
│  │ + PostgreSQL │  │ + PostgreSQL   │  │ + Postgres│          │
│  │ + Redis      │  │ + Redis        │  │ + Redis   │          │
│  └──────────────┘  └────────────────┘  └───────────┘          │
│                                                                 │
│  ┌──────────────────────────────────────────────┐              │
│  │ Apache Kafka (fims-kafka:9092) + Zookeeper   │              │
│  │ + Schema Registry + Kafka UI                  │              │
│  └──────────────────────────────────────────────┘              │
│                                                                 │
│  ┌──────────────────────────────┐                              │
│  │ OnlyOffice Docs (doc editing)│                              │
│  └──────────────────────────────┘                              │
│                                                                 │
│  ┌─────────────────────────────────┐                           │
│  │ Frontend: staff-portal:3000     │                           │
│  │ Frontend: client-portal:3000    │                           │
│  └─────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Inventory & Boundaries

### 2.1 IAM Service (Identity & Access Management)

| Attribute | Value |
|---|---|
| **Port** | 8000 |
| **Database** | `fims_db` on `postgres-iam-service` |
| **API prefix** | `/api/v1/iam/` (also responds without `/iam/` for gateway routing) |

**Owns:**
- User model (UUID primary key, custom `AbstractUser`, `email` as `USERNAME_FIELD`)
- Authentication (login with MFA support, JWT token issuance, refresh, logout)
- Roles and Service Permissions (RBAC system with cross-service permission registry)
- User Sessions (with session-validating JWT auth — tokens tied to active sessions)
- Audit Logs (comprehensive action tracking: LOGIN, LOGOUT, ROLE_ASSIGN, etc.)
- Account Lockout (configurable max attempts, duration, admin alerts)
- Password Policy (expiration, reuse prevention, complexity validation)
- Multi-Factor Authentication (TOTP via django-otp)
- Email sending configuration (SMTP settings stored as singleton SecuritySettings model)
- Permission aggregation from all services (Kafka consumer on `service.permission.registry`)

**Does NOT own:**
- Document storage or management → must delegate to document-records-service
- Workflows and task orchestration → must delegate to work-orchestration-service
- Business domain data (clients, corporate, GRC) → must delegate to respective services

**Django Apps:**
`apps.core`, `apps.users`, `apps.roles`, `apps.authentication`, `apps.user_sessions`, `apps.audit`, `apps.mfa`, `apps.rbac`

**Key Custom Models:**
- `User` — UUID pk, email login, lockout/expiration fields, profile picture, signature
- `Role` — service-aware, with `assign_by_default` and `assign_to_external_users` flags
- `ServicePermission` — cross-service permission registered via Kafka
- `Service` — tracks microservices that register permissions
- `AuditLog` — structured action logging with resource types
- `UserSession` — session tracking with JTI binding to JWT tokens
- `SecuritySettings` — singleton model for security configuration

### 2.2 Document Records Service

| Attribute | Value |
|---|---|
| **Port** | 8002 |
| **Database** | `fims_documents` on `postgres-document-records-service` |
| **API prefix** | `/api/v1/documents/`, `/api/v1/folders/`, `/api/v1/document-types/`, `/api/v1/document-templates/`, `/api/v1/report-templates/`, `/api/v1/reports/`, `/api/v1/storage-locations/` |

**Owns:**
- All document lifecycle (upload, metadata, versioning, download, disposal)
- Document types (configurable via database, replacing hardcoded enum)
- Document templates and template workflows
- Document classification (open, confidential) and classification-based access control
- Folder/File management (hierarchical virtual file system)
- Physical storage location tracking (buildings, floors, shelves)
- Incoming/Outgoing document registers
- Disposal forms and disposal workflows
- Document approval workflows (delegated to work-orchestration-service)
- Reports and scheduled report generation
- Document access requests
- QR Code generation and digital signatures
- OnlyOffice integration for in-browser document editing
- Retention period management and decongestion policies
- Storage threshold monitoring and alerts

**Does NOT own:**
- User authentication or permissions → delegates to IAM
- Workflow plan creation/progression → delegates to work-orchestration-service via `WorkOrchestrationClient`
- Notification delivery → delegates to work-orchestration-service via `NotificationPublisher` + Kafka
- Client or corporate domain data → completely separate

**Architecture:** Clean Architecture layers:
- `apps.core.entities` — pure domain dataclasses (`Document`, `DisposalForm`, `Approval`, etc.)
- `apps.core.use_cases` — application-level business logic
- `apps.core.repositories` — abstract repository interfaces
- `apps.core.workflow` — workflow orchestration adapter layer (bridges to work-orchestration-service)
- `apps.infrastructure.persistence` — Django ORM models implementing domain repositories
- `apps.infrastructure.tasks` — Celery tasks (archival, cleanup, disposal, notifications, reports)
- `apps.api` — REST endpoints, serializers, permissions

### 2.3 Work Orchestration Service

| Attribute | Value |
|---|---|
| **Port** | 8004 |
| **Database** | `workflow_orchestration_db` on `postgres-work-orchestration-service` |
| **API prefix** | `/api/v1/workflow/` |

**Owns:**
- Workflow plans (multi-stage approval pipelines)
- Workflow stages (with assignees, form schemas, actions, SLAs)
- Workflow tasks (assignable, prioritizable, with due dates and time tracking)
- Workflow templates (reusable definitions seeded at startup via `seed_workflow_templates` management command)
- Task types and task queues (configurable catalogs)
- Task comments and collaborators
- Task timesheets (time logging)
- Reminders (scheduled, multi-channel: email/SMS/in-app/webhook, with snooze and escalation)
- Notification templates (code-based, versioned, with priority routing)
- Notification delivery (email via SMTP, SMS via Infobip, in-app storage)
- Notification delivery logs and usage statistics
- Notification settings (singleton admin-configurable model for SMTP/SMS credentials)
- Workflow activity log (immutable audit trail)
- Workflow analytics (overdue tasks, queue summaries, stage analytics)

**Does NOT own:**
- Document data → must never store document content
- User profiles → relies on user_id UUIDs from JWT
- Business domain logic → acts as a generic orchestration engine

**Key Models:**
- `WorkflowPlanModel` — top-level workflow instance (type, status, metadata, tags, SLA)
- `WorkflowStageModel` — ordered stage within a plan (assignees, form_schema, actions)
- `WorkflowTaskModel` — atomic work item (assignee, priority, due_at, queue, related_entity)
- `WorkflowTemplateModel` — reusable plan definition (definition JSON)
- `NotificationTemplateModel` — code-based notification template (channels, priority, body with placeholders)
- `NotificationModel` — in-app notification for users
- `NotificationDeliveryLog` — tracks all delivery attempts
- `ReminderModel` — scheduled reminder with recurrence and escalation
- `NotificationSettings` — singleton SMTP/SMS configuration

### 2.4 Client Service

| Attribute | Value |
|---|---|
| **Port** | 8006 |
| **Database** | `fims_clients` on `postgres-client-service` |
| **API prefix** | `/api/v1/` (gateway rewrites `/api/v1/clients/*` → `/api/v1/*`) |

**Owns:**
- Client entity management (individuals and organizations interacting with FCC)
- Client user accounts (client portal users, separate from staff users in IAM)
- Entity registration, verification, and compliance tracking
- OTP-based verification (for client identity)
- Client document metadata synchronization (periodic sync from document-records-service)
- Client-specific audit logging

**Does NOT own:**
- Staff authentication → IAM service
- Document storage → document-records-service
- Workflow → work-orchestration-service
- Notification delivery → work-orchestration-service via Kafka

**External API integrations configured:**
- NIDA (National ID Authority)
- TRA (Tanzania Revenue Authority)
- BRELA (Business Registrations and Licensing Agency)

### 2.5 Corporate Service

| Attribute | Value |
|---|---|
| **Port** | 8008 |
| **Database** | `fims_corporate` on `postgres-corporate-service` |
| **API prefix** | `/api/v1/corporate/` |

**Owns:**
- Human Resources (HR) management
- Finance management
- Procurement management
- Asset management

**Does NOT own:**
- Authentication → IAM
- Documents → document-records-service
- Workflow → work-orchestration-service

**Configured External Service URLs:**
- `IAM_SERVICE_URL` (http://iam-service:8000)
- `DOCUMENT_SERVICE_URL` (http://document-records-service:8001)
- `WORK_ORCHESTRATION_SERVICE_URL` (http://work-orchestration-service:8002)

### 2.6 API Gateway (NGINX)

| Attribute | Value |
|---|---|
| **Port** | 8080 (external) → 80 (internal) |
| **Type** | NGINX reverse proxy |

**Owns:**
- Path-based routing to all backend services
- CORS handling (adds `Access-Control-Allow-*` headers, strips duplicate headers from backends)
- Rate limiting (separate zones: `api:10r/s`, `auth:5r/s`)
- SSL termination (for production)
- `X-Forwarded-For`, `X-Real-IP`, `X-Forwarded-Proto` header injection
- Frontend routing (host-based: `fcc-staff.*` → staff-portal, all others → client-portal)
- Graceful service unavailability (returns JSON 503 if a backend is down)

**Does NOT own:**
- Authentication (passes `Authorization` header through to backends)
- Business logic of any kind

### 2.7 Message Broker (Apache Kafka)

| Component | Details |
|---|---|
| **Kafka** | Confluent CP 7.4, container: `fims-kafka:9092` |
| **Zookeeper** | Confluent CP 7.4, port 2181 |
| **Schema Registry** | Confluent CP 7.4 |
| **Kafka UI** | Provectus Kafka UI |

**Key Topics:**
| Topic | Producer(s) | Consumer(s) | Purpose |
|---|---|---|---|
| `service.permission.registry` | All domain services | IAM service | Permission auto-registration |
| `workflow-events` | work-orchestration-service | document-records-service | Workflow state changes |
| `notification-templates` | All services | work-orchestration-service | Template registration |
| `notifications` | All services | work-orchestration-service | Default notification channel |
| `notifications-urgent` | All services | work-orchestration-service | Urgent priority notifications |
| `notifications-high` | All services | work-orchestration-service | High priority notifications |
| `notifications-normal` | All services | work-orchestration-service | Normal priority notifications |
| `notifications-low` | All services | work-orchestration-service | Low priority notifications |
| `notification-failed` | work-orchestration-service | (DLQ) | Dead-letter for failed notifications |
| `fims.documents.events` | document-records-service | Various | Document domain events |
| `fims.iam.user.updated` | iam-service | document-records-service | User profile changes |
| `corporate.events` | corporate-service | Various | Corporate domain events |
| `client-service.entity.events` | client-service | Various | Client entity events |

### 2.8 Frontend (Monorepo)

| Attribute | Value |
|---|---|
| **Framework** | React + TypeScript + Vite |
| **UI Library** | shadcn/ui (Radix primitives) |
| **Structure** | Monorepo with `apps/staff-portal`, `apps/client-portal`, `packages/shared`, `packages/ui` |

Two separate portal builds:
- **Staff Portal** — internal FCC staff interface
- **Client Portal** — external client-facing interface

---

## 3. Cross-Service Communication Mechanisms

### 3.1 Synchronous (REST over HTTP)

Used for:
- **User-facing API requests** — frontend → gateway → backend service
- **Service-to-service queries** — e.g., document-records-service → work-orchestration-service for plan creation

**Authentication for service-to-service calls:**
```
Header: X-Service-Token: <shared-secret>
```
The `SERVICE_TO_SERVICE_TOKEN` env var (default: `fims-service-secret-token`) is shared between services that need to call each other directly. The receiving service's JWT middleware recognizes this header and creates a `ServiceUser` with superuser privileges.

**Circuit Breaker Pattern:**
The document-records-service implements a circuit breaker (`CircuitBreaker` class) for calls to work-orchestration-service:
- `failure_threshold` — consecutive failures before opening (default: 5)
- `recovery_timeout` — seconds before attempting recovery (default: 60)
- Protects against cascading failures when orchestration service is down

### 3.2 Asynchronous (Kafka Events)

Used for:
- **Permission registration** — services publish their permission definitions to IAM
- **Notification delivery** — services publish notification events, work-orchestration-service consumes and delivers
- **Workflow events** — work-orchestration-service publishes stage/task state changes
- **Domain events** — services publish business events for loose coupling

**Kafka Event Envelope Standard:**
```json
{
  "id": "uuid-v4",
  "type": "event.type.name",
  "timestamp": "2026-02-24T10:00:00.000Z",
  "service": "source-service-name",
  "version": "1.0",
  "data": { ... }
}
```

**Notification Event Envelope:**
```json
{
  "event_type": "notification_request",
  "event_version": "1.0",
  "timestamp": "2026-02-24T10:00:00Z",
  "source_service": "document-service",
  "notification_id": "uuid-v4",
  "idempotency_key": "template_code-recipient-timestamp_minute",
  "data": {
    "template_code": "document.approval.request",
    "priority": "normal",
    "recipients": {
      "email": ["user@example.com"],
      "sms": ["+255123456789"]
    },
    "context": {
      "document": { "id": "...", "title": "...", "reference_number": "..." }
    }
  }
}
```

### 3.3 Data Ownership Rules

1. **Each service owns its database** — no shared database access across services
2. **User IDs are UUIDs** — all services refer to users by UUID, never by email or name
3. **Cross-reference by ID only** — if service A needs data from service B, it either:
   - Fetches it via REST API at request time, or
   - Listens for domain events via Kafka and caches relevant data locally
4. **No foreign keys across service boundaries** — use UUID fields (not ForeignKey) to reference entities from other services
5. **Document-records-service caches IAM user data** — uses `IAMClient` with Redis-backed caching (5-minute TTL) to resolve user IDs to names/emails

---

## 4. Authentication & Authorization Architecture

### 4.1 Token Issuance (IAM Service Only)

1. User sends `POST /api/v1/auth/login/` with email/password (+ optional MFA code)
2. IAM authenticates, checks account lockout, validates MFA
3. IAM generates `EnhancedAccessToken` and `EnhancedRefreshToken`:
   - Access token lifetime: configurable (default 1 hour)
   - Refresh token lifetime: configurable (default 7 days)
   - Algorithm: HS256 with shared `JWT_SECRET_KEY`

**JWT Payload Structure:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "is_staff": true,
  "is_superuser": false,
  "permissions": {},
  "permissions_flat": ["document.read", "document.write", "hr.view_employee"],
  "services": ["document-service", "corporate-service", "work-orchestration-service"],
  "jti": "unique-token-id",
  "token_type": "access",
  "exp": 1740000000,
  "iat": 1739996400
}
```

**Key design decisions:**
- `permissions` dict is intentionally empty to minimize token size (was causing HTTP 431 errors)
- `permissions_flat` contains all permission codes across all services
- Superusers get `permissions_flat: ["*"]` as a wildcard marker
- `services` lists service names the user has access to

### 4.2 Token Validation (Every Service)

Every service except IAM validates JWTs **locally** — no IAM service calls needed at runtime.

**Pattern implemented identically across services:**

1. `JWTPermissionMiddleware` (Django middleware) intercepts every request
2. Extracts `Bearer` token from `Authorization` header
3. Decodes JWT using shared `JWT_SECRET_KEY` + HS256
4. Extracts from payload: `user_id`, `email`, `is_superuser`, `permissions_flat`, `services`
5. Validates service access (checks if user's `services` list includes the current service)
6. Creates a lightweight `AuthenticatedUser` or `SimpleUser` object (not a Django model)
7. Sets `request.user`, `request.user_id`, `request.user_permissions_flat`, etc.

Then:

8. `JWTMiddlewareAuthentication` (DRF authentication class) bridges the middleware user to DRF
9. View-level permission classes check `request.user_permissions_flat` for specific codes

**IAM Service Exception:** IAM uses `SessionValidatingJWTAuthentication` (extends simplejwt) that additionally verifies the JWT's JTI matches an active `UserSession` record.

### 4.3 Permission Registration (Decentralized Definitions, Centralized Aggregation)

Each service defines its permissions in a JSON config file:
```
config/permissions/<service-name>.json
```

Structure:
```json
{
  "service": {
    "name": "client-service",
    "version": "1.0.0",
    "description": "Client entity and user management"
  },
  "permissions": [
    {
      "permission_code": "client.entity.create",
      "name": "Create Entity",
      "description": "Can create new client entities",
      "resource_type": "entity",
      "action": "create",
      "category": "entity_management"
    }
  ],
  "roles": [...]
}
```

Each service has a `PermissionPublisher` class that sends this data to Kafka topic `service.permission.registry`. IAM consumes these events and upserts `Service` + `ServicePermission` records into its database. Roles in IAM then reference these cross-service permissions.

### 4.4 Service-to-Service Authentication

For internal HTTP calls between services, the calling service sends:
```
X-Service-Token: <shared SECRET>
```

The receiving service's JWT middleware recognizes this header and creates a `ServiceUser` with:
- `is_superuser = True`
- `permissions = ['*']` (wildcard)
- `id = 'service'`
- `email = 'service@internal'`

This bypasses per-user permission checks for internal operations.

---

## 5. Shared Domain Services & Delegation Model

### 5.1 Work Orchestration Service — How To Integrate

The work-orchestration-service provides three key capabilities to every other service:

#### A) Workflow Plans (Approval Pipelines)

Any service that needs multi-step approval must:
1. Call `POST /api/v1/workflow/plans/` on work-orchestration-service to create a plan
2. The plan definition includes stages, assignees, form schemas, and actions
3. Stage progression is done via `POST /api/v1/workflow/plans/<id>/stages/<id>/actions/`
4. The orchestration service emits events to Kafka (`workflow-events` topic) on state changes
5. The originating service listens for these events and updates its domain state accordingly

**Evidence — Document Records Service:**
- Uses `WorkOrchestrationClient` (HTTP client with circuit breaker) to create/advance workflow plans
- Uses `WorkflowEventBridge` to listen for Kafka events and map them back to document domain events
- Uses `WorkflowAdapterRegistry` to route different workflow types to the orchestration service

**Evidence — Workflow Plan creation call:**
```python
# From document-records-service/apps/core/workflow/orchestration_client.py
client = WorkOrchestrationClient()
plan = client.create_plan(workflow_type="document_approval", metadata={...})
```

#### B) Notification Delivery

Any service that needs to send notifications (email, SMS, in-app) must:
1. Register notification templates via Kafka (`notification-templates` topic) or via REST
2. Publish notification events to priority-based Kafka topics:
   - `notifications-urgent`, `notifications-high`, `notifications-normal`, `notifications-low`
3. Work-orchestration-service consumes these events, renders templates, and delivers via configured channels

**Pattern — NotificationPublisher (identical in every consuming service):**
```python
from apps.core.notifications.publisher import NotificationPublisher

publisher = NotificationPublisher()
publisher.send_notification(
    template_code='document.approval.request',
    recipients={'email': ['approver@fcc.go.tz']},
    context={'document': {'title': '...', 'reference_number': '...'}},
    priority='high',
)
```

Each service has an identical `NotificationPublisher` class that:
- Creates a Kafka producer
- Generates idempotency keys (template_code + recipient + timestamp minute)
- Routes to priority-specific topics
- Falls back to default `notifications` topic if priority topic unavailable

#### C) Notification Templates

Templates are registered via Kafka by any service:
```json
{
  "event_type": "service_permission_registration",
  "source_service": "document-service",
  "data": {
    "code": "document.approval.request",
    "name": "Document Approval Request",
    "channels": ["email", "in_app"],
    "priority": "high",
    "subject": "Approval Required: {{document.title}}",
    "body": "Document {{document.reference_number}} requires your approval..."
  }
}
```

Work-orchestration-service stores these as `NotificationTemplateModel` records and uses them to render notifications.

### 5.2 Document Records Service — How To Integrate

Any service that manages documents must delegate to document-records-service:

1. **Upload documents** — `POST /api/v1/documents/` with multipart form data
2. **Reference documents** — Store the document UUID, never the file content
3. **Retrieve metadata** — `GET /api/v1/documents/<id>/`
4. **Download files** — `GET /api/v1/documents/<id>/download/`
5. **Initiate workflows** — Document-records-service will itself delegate to work-orchestration-service

**Key: No other service should store files, manage versions, or implement document workflows.**

### 5.3 IAM Service — How To Integrate

1. **Authentication** — Use shared `JWT_SECRET_KEY` and the `JWTPermissionMiddleware` pattern
2. **User data lookup** — Use `IAMClient` to fetch user profiles (with caching)
3. **Permission registration** — Use `PermissionPublisher` to register service permissions via Kafka
4. **Audit logging** — IAM owns its own audit; domain services maintain domain-specific audit logs

---

## 6. Architectural Conventions

### 6.1 Project Structure Convention

Every FIMS Django service follows this layout:
```
<service-name>/
├── apps/
│   ├── api/                    # REST layer
│   │   ├── authentication.py   # DRF authentication bridges
│   │   ├── permissions.py      # DRF permission classes
│   │   ├── exceptions.py       # Custom exception handler
│   │   ├── serializers/        # DRF serializers
│   │   ├── views/              # DRF views/viewsets
│   │   └── urls/               # URL routing
│   ├── core/                   # Business logic + domain
│   │   ├── entities/           # Domain entities (dataclasses or enums)
│   │   ├── exceptions.py       # Domain exceptions
│   │   ├── kafka_producer.py   # Kafka producer wrapper
│   │   ├── kafka_permission_publisher.py  # Permission registration
│   │   ├── notifications/      # Notification publisher
│   │   ├── permission_middleware.py  # JWT middleware
│   │   ├── permissions.py      # Permission constants/loader
│   │   ├── repositories/       # Repository interfaces
│   │   ├── services/           # Business services
│   │   └── use_cases/          # Application use cases
│   └── infrastructure/         # Technical infrastructure
│       ├── external/           # External service clients
│       ├── messaging/          # Kafka consumers/producers
│       ├── persistence/        # Django models and ORM repositories
│       │   ├── models.py
│       │   ├── migrations/
│       │   └── repositories/
│       └── tasks/              # Celery tasks
├── config/
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Root URL configuration
│   ├── celery.py               # Celery app configuration
│   ├── wsgi.py
│   └── permissions/            # JSON permission definitions
│       └── <service-name>.json
├── shared/                     # Shared utilities (per-service copy)
│   ├── common/
│   │   ├── auth/jwt_utils.py
│   │   ├── messaging/kafka_producer.py, kafka_consumer.py
│   │   └── monitoring/metrics.py
│   └── constants/
│       ├── event_types.py
│       └── api_endpoints.py
├── templates/                  # Email templates
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── manage.py
└── .env
```

### 6.2 API Versioning

All APIs are versioned at `/api/v1/`. The version prefix is part of the URL path:
```
/api/v1/documents/
/api/v1/workflow/plans/
/api/v1/corporate/hr/employees/
```

### 6.3 Pagination

**Standard:** `PageNumberPagination` from DRF with consistent defaults:
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
}
```

**Query parameters:** `?page=2&page_size=50`

IAM Service has a custom `CustomPageNumberPagination` that wraps responses in:
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "count": 150,
      "next": "http://...",
      "previous": null,
      "page": 1,
      "page_size": 20,
      "total_pages": 8
    }
  }
}
```

Other services use DRF's default paginated response:
```json
{
  "count": 150,
  "next": "http://...",
  "previous": null,
  "results": [...]
}
```

### 6.4 Error Response Format

**IAM Service** (`apps.core.exceptions.custom_exception_handler`):
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": { ... },
    "validation_errors": { "field": ["error1", "error2"] }
  }
}
```

**Document Records Service** (`apps.api.exceptions.custom_exception_handler`):
```json
{
  "error": {
    "message": "Human-readable message",
    "status_code": 400,
    "details": { ... }
  }
}
```

**Unauthenticated responses (all services via middleware):**
```json
{
  "error": "Authorization header missing or invalid"
}
```

**Service unavailable (API Gateway):**
```json
{
  "error": "service_unavailable",
  "message": "The requested microservice is not running. Start the service and try again."
}
```

### 6.5 Response Conventions

- All endpoints return JSON (renderer: `JSONRenderer` only)
- Success responses vary by service but generally follow DRF defaults
- IAM tends to use `{"success": true, "data": {...}}` envelope
- Other services tend to return data directly (DRF default)
- UUID fields are serialized as strings
- Timestamps use ISO 8601 format with timezone

### 6.6 Authentication Header Format

```
Authorization: Bearer <jwt-access-token>
```

Service-to-service:
```
X-Service-Token: <shared-secret>
```

### 6.7 Filtering, Searching, Ordering

All services use:
```python
'DEFAULT_FILTER_BACKENDS': [
    'django_filters.rest_framework.DjangoFilterBackend',
    'rest_framework.filters.SearchFilter',
    'rest_framework.filters.OrderingFilter',
]
```

Usage: `?search=keyword&ordering=-created_at&field_name=value`

### 6.8 Logging Convention

Every service uses Python logging with:
- **Console handler** — always enabled
- **File handler** — `logs/<service-name>.log` with RotatingFileHandler (10-15 MB, 5-10 backups)
- **Format (verbose):** `{levelname} {asctime} {module} {process:d} {thread:d} {message}`
- **Root level:** INFO
- **Django level:** INFO
- **Apps level:** DEBUG or INFO

### 6.9 Database Conventions

- Default PK: `BigAutoField` (or explicit `UUIDField` for business entities)
- Timestamps: `created_at = auto_now_add=True`, `updated_at = auto_now=True`
- Soft references to IAM users: `UUIDField(null=True)` named `user_id`, `created_by`, `assignee`, etc.
- All services use PostgreSQL 15 with Alpine images
- Atomic requests enabled where noted (`ATOMIC_REQUESTS: True`)
- Connection pooling: `CONN_MAX_AGE` between 60-600 seconds

### 6.10 Docker & Networking

- All services join the external Docker network `fims-network`
- Service names follow: `<service-name>` (used as Docker hostname)
- Container names follow: `fims-<service-name>`
- Each service has: main container + celery-worker + celery-beat
- Infrastructure containers: `postgres-<service-name>`, `redis-<service-name>`
- Health checks: HTTP check to `/health/` endpoint, or CLI check for PostgreSQL/Redis
- Production server: Gunicorn with 4 workers, 120s timeout

### 6.11 Celery Convention

- Broker: Redis (dedicated DB, typically `/1` or `/2`)
- Result backend: Same Redis instance
- Serializer: JSON only
- Timezone: `Africa/Dar_es_Salaam` (most services) or UTC (IAM)
- Task time limit: 30 minutes
- Soft time limit: 25 minutes
- Beat schedule defined in `settings.py` with `CELERY_BEAT_SCHEDULE`

### 6.12 Kafka Convention

- Bootstrap servers: `fims-kafka:9092`
- Client ID: `<service-name>`
- Consumer group: `<service-name>-group` (or more specific per topic)
- Serialization: JSON (UTF-8 encoded)
- Auto-create topics: enabled
- Event envelope: includes `id`, `type`, `timestamp`, `service`, `version`, `data`

---

## 7. Dependency Philosophy — What Must Never Be Duplicated

### Absolute Rules

| Capability | Owner | Other services MUST |
|---|---|---|
| User authentication | IAM Service | Validate JWTs locally using shared secret — never build a separate login |
| User/role/permission storage | IAM Service | Register permissions via Kafka; never maintain a local user table |
| JWT token issuance | IAM Service | Never issue tokens from any other service |
| Document storage | Document Records Service | Delegate all file operations — never store files locally |
| Document versioning | Document Records Service | Never track versions — reference by document UUID |
| Document workflows | Doc Records → Work Orchestration | Chain: use doc-records API, which delegates to orchestration |
| Workflow plan management | Work Orchestration Service | Create plans via REST API — never hardcode approval chains |
| Notification delivery | Work Orchestration Service | Publish to Kafka topics — never call SMTP/SMS directly |
| Notification templates | Work Orchestration Service | Register via Kafka — never hardcode email bodies |
| CORS handling | API Gateway (NGINX) | Never configure CORS in Django if behind gateway |
| API routing | API Gateway (NGINX) | Services expose their port; gateway routes by path |
| Rate limiting | API Gateway (NGINX) | Do not duplicate rate limiting in Django (except IAM's ratelimit) |

### Delegation Patterns in Evidence

**Document Records → Work Orchestration (approval workflow):**
```python
# orchestration_client.py creates plans via REST
client = WorkOrchestrationClient()
plan = client.create_plan(workflow_type="document_approval", ...)
# Then listens for Kafka events via WorkflowEventBridge
```

**All Services → Work Orchestration (notifications):**
```python
# NotificationPublisher sends to Kafka priority topics
publisher = NotificationPublisher()
publisher.send_notification(template_code='...', recipients={...}, context={...})
```

**All Services → IAM (permission registration):**
```python
# PermissionPublisher sends to Kafka topic 'service.permission.registry'
publisher = PermissionPublisher()
publisher.publish_permissions()
```

### What Each Service May Own Locally

- Its own PostgreSQL database schema
- Its own Redis cache
- Its own Celery tasks for domain-specific async work
- Its own domain entities and business logic
- Its own API serializers and views
- Domain-specific audit/event logs (complementary to IAM audit)
- Caching of cross-service data (with TTLs)

---

## 8. Step-by-Step Guide: Building a New FIMS Service

### Step 1: Scaffold the Project

```bash
mkdir my-service && cd my-service
django-admin startproject config .
```

Create the directory structure:
```
my-service/
├── apps/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── authentication.py
│   │   ├── permissions.py
│   │   ├── exceptions.py
│   │   ├── serializers/
│   │   ├── views/
│   │   └── urls/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── entities/
│   │   ├── exceptions.py
│   │   ├── kafka_producer.py
│   │   ├── kafka_permission_publisher.py
│   │   ├── notifications/
│   │   │   └── publisher.py
│   │   ├── permission_middleware.py
│   │   └── permissions.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── persistence/
│       │   ├── __init__.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   └── migrations/
│       └── tasks/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── permissions/
│       └── my-service.json
├── shared/
│   ├── __init__.py
│   ├── common/
│   │   ├── auth/jwt_utils.py
│   │   ├── messaging/kafka_producer.py, kafka_consumer.py
│   │   └── monitoring/metrics.py
│   └── constants/
│       ├── event_types.py
│       └── api_endpoints.py
├── templates/
├── logs/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```

### Step 2: Configure Settings

Copy the settings pattern from any existing service. Key items:

```python
# config/settings.py

# JWT — MUST match IAM service
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

# Database — own instance
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'fims_myservice'),
        'HOST': os.getenv('DB_HOST', 'postgres-my-service'),
        ...
    }
}

# Redis — own instance
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis-my-service:6379/0')

# Kafka — shared cluster
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'fims-kafka:9092')

# External services
IAM_SERVICE_URL = os.getenv('IAM_SERVICE_URL', 'http://iam-service:8000')
DOCUMENT_SERVICE_URL = os.getenv('DOCUMENT_SERVICE_URL', 'http://document-records-service:8002')
WORK_ORCHESTRATION_SERVICE_URL = os.getenv('WORK_ORCHESTRATION_SERVICE_URL', 'http://work-orchestration-service:8004')

# Service-to-service auth
SERVICE_TO_SERVICE_TOKEN = os.getenv('SERVICE_TO_SERVICE_TOKEN', 'fims-service-secret-token')

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.api.authentication.JWTMiddlewareAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # if needed
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.permission_middleware.JWTPermissionMiddleware',  # JWT auth
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### Step 3: Implement JWT Middleware

Copy and adapt `JWTPermissionMiddleware` from any existing service (e.g., corporate-service — it's the cleanest).

Key requirements:
1. Skip paths: `/health/`, `/admin/`, `/static/`, `/media/`
2. Accept `X-Service-Token` for service-to-service calls
3. Decode JWT with `jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])`
4. Extract: `user_id`, `email`, `is_superuser`, `permissions_flat`, `services`
5. Verify the user has your service in their `services` list
6. Create a lightweight `AuthenticatedUser` object and set `request.user`

### Step 4: Implement DRF Authentication Bridge

```python
# apps/api/authentication.py
class JWTMiddlewareAuthentication(BaseAuthentication):
    def authenticate(self, request):
        django_request = getattr(request, '_request', request)
        middleware_user = getattr(django_request, 'user', None)
        if middleware_user and type(middleware_user).__name__ == 'AuthenticatedUser':
            return (middleware_user, None)
        return None
```

### Step 5: Define and Register Permissions

Create `config/permissions/my-service.json`:
```json
{
  "service": {
    "name": "my-service",
    "version": "1.0.0",
    "description": "My service description"
  },
  "permissions": [
    {
      "permission_code": "my.resource.create",
      "name": "Create Resource",
      "description": "Can create resources",
      "resource_type": "resource",
      "action": "create",
      "category": "resource_management"
    }
  ]
}
```

Implement `PermissionPublisher` (copy from client-service or document-records-service).
Register a Django management command or Celery task to call `publish_permissions()` on startup.

### Step 6: Set Up Docker Compose

```yaml
services:
  postgres-my-service:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: fims_myservice
      POSTGRES_USER: myservice_user
      POSTGRES_PASSWORD: myservice_password_2024
    networks:
      - fims-network
    healthcheck: ...

  redis-my-service:
    image: redis:7-alpine
    networks:
      - fims-network
    healthcheck: ...

  my-service:
    build: .
    ports:
      - "8010:8010"
    env_file: .env
    depends_on:
      postgres-my-service: { condition: service_healthy }
      redis-my-service: { condition: service_healthy }
    networks:
      - fims-network
    command: >
      sh -c "
        python manage.py migrate &&
        python manage.py collectstatic --noinput &&
        gunicorn config.wsgi:application --bind 0.0.0.0:8010 --workers 4 --timeout 120
      "

  my-celery-worker:
    build: .
    command: celery -A config.celery worker -l info --concurrency=4
    depends_on: [postgres-my-service, redis-my-service]
    networks: [fims-network]

  my-celery-beat:
    build: .
    command: celery -A config.celery beat -l info
    depends_on: [redis-my-service]
    networks: [fims-network]

networks:
  fims-network:
    external: true
```

### Step 7: Add Gateway Route

Add a location block to `api-gateway/config/nginx.conf`:
```nginx
location /api/v1/my-service/ {
    if ($request_method = 'OPTIONS') {
        # ... standard CORS preflight block ...
        return 204;
    }
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://my-service:8010/api/v1/my-service/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization $http_authorization;
    
    proxy_hide_header 'Access-Control-Allow-Origin';
    proxy_hide_header 'Access-Control-Allow-Credentials';
    add_header 'Access-Control-Allow-Origin' $cors_origin always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;
}
```

Also add an upstream block:
```nginx
upstream my_service {
    zone my_service_zone 64k;
    resolver 127.0.0.11 valid=10s ipv6=off;
    resolver_timeout 5s;
    least_conn;
    server my-service:8010 max_fails=3 fail_timeout=30s resolve;
    keepalive 32;
}
```

### Step 8: Implement Notification Publishing

Copy `NotificationPublisher` from client-service or document-records-service. Update the `service_name`, and add Kafka topic settings to `settings.py`.

### Step 9: Implement Health Check

```python
# apps/api/urls/health_urls.py
from django.urls import path
from apps.api.views.health_view import health_check

urlpatterns = [
    path('', health_check, name='health'),
]
```

```python
# apps/api/views/health_view.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'healthy', 'service': 'my-service'})
```

### Step 10: Test Integration

1. Start all infrastructure: `cd message-broker && docker compose up -d`
2. Start IAM: `cd iam-service && docker compose up -d`
3. Start your service: `cd my-service && docker compose up -d`
4. Start gateway: `cd api-gateway && docker compose up -d`
5. Login: `POST http://localhost:8080/api/v1/auth/login/` → get JWT
6. Call your API: `GET http://localhost:8080/api/v1/my-service/... -H "Authorization: Bearer <token>"`

---

## 9. Common Architectural Mistakes to Avoid

### Mistake 1: Building Your Own Authentication

**Wrong:** Creating a login endpoint, user table, or session management in your service.  
**Right:** Validate JWTs from IAM using the shared secret. IAM is the sole identity provider.

### Mistake 2: Storing Documents Locally

**Wrong:** Accepting file uploads in your service and writing them to your own filesystem.  
**Right:** Delegate all file storage to document-records-service. Store only the document UUID as a reference.

### Mistake 3: Implementing Approval Workflows Inline

**Wrong:** Hardcoding multi-step approval logic (e.g., "if manager approves, then director approves") in your service.  
**Right:** Create a workflow plan in work-orchestration-service with stages, assignees, and actions. Listen for Kafka events to track progression.

### Mistake 4: Sending Emails/SMS Directly

**Wrong:** Importing `django.core.mail.send_mail` or calling SMTP/SMS APIs from your service.  
**Right:** Publish notification events to Kafka. Work-orchestration-service owns delivery configuration (SMTP settings, SMS provider, templates).

### Mistake 5: Calling IAM Service for Every Request

**Wrong:** Making HTTP calls to IAM on every API request to validate tokens or fetch permissions.  
**Right:** Decode the JWT locally. The token already contains `permissions_flat` and `services`. Only call IAM for user profile data, and cache the results.

### Mistake 6: Sharing a Database

**Wrong:** Connecting to another service's PostgreSQL instance.  
**Right:** Each service has its own database. Access cross-service data through REST APIs or Kafka events.

### Mistake 7: Hardcoding Permission Strings

**Wrong:** Checking `if request.user.email == 'admin@fcc.go.tz'` or `if request.user_permissions_flat.count('document.approve') > 0` without a formal permission definition.  
**Right:** Define permissions in `config/permissions/<service>.json`, register them with IAM via Kafka, and check via `request.user_permissions_flat`.

### Mistake 8: Ignoring the API Gateway

**Wrong:** Configuring CORS headers in your Django service when running behind the gateway.  
**Right:** The gateway handles CORS. Django services should either disable CORS middleware or let it be redundant. (Note: current codebase shows some services still configure CORS — the IAM service explicitly states "CORS is handled by NGINX API Gateway" and removes the middleware.)

### Mistake 9: Using Integer Primary Keys for Business Entities

**Wrong:** Using auto-incrementing integers for entities that will be referenced across services.  
**Right:** Use `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` for all business models. This ensures globally unique identifiers across the distributed system.

### Mistake 10: Not Implementing a Health Check

**Wrong:** Skipping the `/health/` endpoint.  
**Right:** Every service must expose an unauthenticated `GET /health/` endpoint. The API gateway and Docker health checks rely on it.

### Mistake 11: Tight Coupling Via Synchronous Calls

**Wrong:** Making synchronous REST calls for non-critical operations that can tolerate eventual consistency.  
**Right:** Use Kafka events for non-critical data propagation. Reserve synchronous calls for user-facing request paths where immediate consistency is required.

### Mistake 12: Not Publishing Domain Events

**Wrong:** Only modifying your local database without notifying other services about state changes.  
**Right:** Publish domain events to Kafka topics (e.g., `my-service.entity.events`) so other services can react to your state changes without coupling to your API.

### Mistake 13: Duplicating the NotificationPublisher or KafkaProducer Pattern

**Wrong:** Writing a completely custom Kafka integration from scratch.  
**Right:** Copy the established `NotificationPublisher` and `KafkaProducer` patterns from existing services. They handle producer initialization, retries, idempotency keys, and priority-based topic routing.

### Mistake 14: Not Registering Your Service's Permissions on Startup

**Wrong:** Only defining permissions in code without publishing them to IAM.  
**Right:** Create a management command or Celery task that calls `PermissionPublisher.publish_permissions()` — ideally run during container startup or as a periodic task.

---

## Appendix A: Port Allocation

| Service | Port |
|---|---|
| IAM Service | 8000 |
| Document Records Service | 8002 |
| Work Orchestration Service | 8004 |
| Client Service | 8006 |
| Corporate Service | 8008 |
| GRC Service | 8006 (conflicts with client — check deployment) |
| API Gateway | 8080 |
| Kafka | 9092 (internal), 29092 (internal alternate) |
| Kafka UI | 8081 (typical) |
| Zookeeper | 2181 |
| Schema Registry | 8081 |
| OnlyOffice Docs | 80 |

## Appendix B: Environment Variables (Cross-Service)

| Variable | Required By | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | All services | Shared JWT signing secret |
| `JWT_ALGORITHM` | All services | JWT algorithm (HS256) |
| `KAFKA_BOOTSTRAP_SERVERS` | All services | Kafka broker address |
| `SERVICE_TO_SERVICE_TOKEN` | Services making internal calls | Shared service auth token |
| `IAM_SERVICE_URL` | All services except IAM | URL of IAM service |
| `DOCUMENT_SERVICE_URL` | Services needing documents | URL of document-records-service |
| `WORK_ORCHESTRATION_SERVICE_URL` | Services needing workflows/notifications | URL of work-orchestration-service |
| `TUNNEL_DOMAIN` | All services | External domain for links |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` | All services | Per-service database config |
| `REDIS_URL` | All services | Per-service Redis URL |
| `CELERY_BROKER_URL` | All services | Per-service Celery broker |

## Appendix C: Shared `shared/` Directory

Each service contains a `shared/` directory with identical utility code:

| Module | Purpose |
|---|---|
| `shared.common.auth.jwt_utils` | `JWTManager` — token generation/decoding utilities |
| `shared.common.messaging.kafka_producer` | `FIMSKafkaProducer` — standardized event publishing |
| `shared.common.messaging.kafka_consumer` | `FIMSKafkaConsumer` — standardized event consumption with handler registry |
| `shared.common.monitoring.metrics` | Prometheus metrics utilities |
| `shared.constants.event_types` | All domain event type constants |
| `shared.constants.api_endpoints` | All service API endpoint constants |

> **Important:** The `shared/` directory is **copied** into each service, not imported as a shared library. If you update it, you must update all copies. A future refactoring opportunity is to extract this into a Python package.

---

*This document was derived from implementation evidence in the FIMS codebase. All patterns, conventions, and architectural decisions described here are based on actual code analysis — not assumptions.*
