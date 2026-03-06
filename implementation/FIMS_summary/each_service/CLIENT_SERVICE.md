# Client Service — Internal System Reference

> **Document Type:** Service Deep-Dive  
> **Audience:** Backend engineers building or integrating with Client Service  
> **Last Updated:** 2026-02-24  
> **Status:** Evidence-based reverse-engineering from production codebase

---

## Table of Contents

1. [Service Identity](#1-service-identity)
2. [Architectural Overview](#2-architectural-overview)
3. [Domain Model](#3-domain-model)
4. [Two-Tier Verification System](#4-two-tier-verification-system)
5. [API Reference](#5-api-reference)
6. [Permission System](#6-permission-system)
7. [Core Services](#7-core-services)
8. [Use Cases](#8-use-cases)
9. [Repository Layer](#9-repository-layer)
10. [External Integrations](#10-external-integrations)
11. [Kafka Event Architecture](#11-kafka-event-architecture)
12. [Celery Tasks & Scheduling](#12-celery-tasks--scheduling)
13. [Caching Strategy](#13-caching-strategy)
14. [Audit System](#14-audit-system)
15. [Notification Templates](#15-notification-templates)
16. [Infrastructure & Deployment](#16-infrastructure--deployment)
17. [Known Issues & Architectural Notes](#17-known-issues--architectural-notes)

---

## 1. Service Identity

| Attribute | Value |
|---|---|
| **Service Name** | `client-service` |
| **Port** | 8006 |
| **Database** | `fims_clients` on `postgres-client-service` |
| **Redis** | `redis-client-service:6379` (DB 0 = cache, DB 1 = Celery) |
| **API Prefix** | `/api/v1/` (gateway rewrites `/api/v1/clients/*` → `/api/v1/*`) |
| **Docker Container** | `fims-client-service` |
| **Kafka Client ID** | `client-service` |
| **Kafka Consumer Group** | `client-service-consumer-group` |
| **Framework** | Django 4.2 + DRF 3.14 |
| **Python** | 3.11 |

### What This Service Owns

- **Entity management** — businesses/organizations that interact with FCC (registration, verification, status lifecycle)
- **Client user accounts** — individuals using the client portal (separate from IAM staff users)
- **Entity-user relationships** — many-to-many links with role-based access (primary, representative, authorized)
- **Entity and user verification** — two-tier verification system with configurable requirements per user type
- **OTP-based verification** — email and phone OTP generation, sending, and verification
- **Document metadata** — references to documents stored in document-records-service, with cached metadata and verification status
- **Application linking** — associations between entities and regulatory applications
- **External entity tracking** — unregistered entities participating in applications (e.g., merger targets)
- **Payment context** — payment tracking per entity and application (data sourced from events)
- **Client-specific audit logging** — 50+ auditable actions across all domain operations
- **Verification configuration** — admin-configurable verification rules per user type and account type

### What This Service Does NOT Own

| Capability | Owner | How Client Service Uses It |
|---|---|---|
| Staff authentication | IAM Service | Validates JWTs locally using shared `JWT_SECRET_KEY` |
| User identity creation | IAM Service | Calls `IAMClient.create_user()` to create portal accounts |
| Document file storage | Document Records Service | Calls `DocumentClient` for upload/download; stores only UUID references |
| Notification delivery | Work Orchestration Service | Publishes to Kafka notification topics via `NotificationPublisher` |
| Workflow orchestration | Work Orchestration Service | No direct workflow integration currently |
| CORS handling | API Gateway (NGINX) | Configured but redundant behind gateway |

---

## 2. Architectural Overview

### Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  apps/api/views/      — 18 view files, ~80 endpoints            │
│  apps/api/serializers/ — 5 serializer files                     │
│  apps/api/permissions.py — 6 custom permission classes          │
│  apps/api/authentication.py — DRF bridge to JWT middleware      │
├─────────────────────────────────────────────────────────────────┤
│                      Domain Layer                                │
│  apps/core/entities/       — 8 dataclass-based domain entities  │
│  apps/core/use_cases/      — 50+ use case classes               │
│  apps/core/repositories/   — 8 abstract repository interfaces   │
│  apps/core/services/       — 7 domain services                  │
│  apps/core/validators/     — Password complexity validators     │
├─────────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                            │
│  apps/infrastructure/persistence/ — Django ORM models + repos   │
│  apps/infrastructure/external/    — 6 external service clients  │
│  apps/infrastructure/messaging/   — Kafka consumer + handlers   │
│  apps/infrastructure/tasks/       — Celery tasks                │
│  apps/infrastructure/cache/       — Redis cache service         │
│  apps/infrastructure/services/    — Audit service               │
│  apps/infrastructure/middleware/  — Audit middleware             │
├─────────────────────────────────────────────────────────────────┤
│                    Cross-Cutting                                  │
│  apps/core/permission_middleware.py — JWT validation             │
│  apps/core/kafka_producer.py       — Event publishing           │
│  apps/core/kafka_permission_publisher.py — Permission registry  │
│  apps/core/notifications/          — Kafka notification system  │
│  apps/core/templates/              — Notification templates     │
│  apps/audit/                       — Audit log model            │
└─────────────────────────────────────────────────────────────────┘
```

### Docker Compose Services

| Container | Image | Purpose |
|---|---|---|
| `fims-client-service` | Custom build | Django app (Gunicorn, 4 workers, port 8006) |
| `fims-client-celery-worker` | Custom build | Celery worker (concurrency=4) |
| `fims-client-celery-beat` | Custom build | Celery beat scheduler |
| `fims-client-kafka-consumer` | Custom build | Dedicated Kafka consumer (`run_kafka_consumer` command) |
| `postgres-client-service` | postgres:15-alpine | PostgreSQL 15 |
| `redis-client-service` | redis:7-alpine | Redis 7 |

---

## 3. Domain Model

### 3.1 Entity-Relationship Diagram

```
┌───────────────────────┐       ┌────────────────────────┐
│        Entity         │       │         User           │
│ (businesses/orgs)     │       │ (individual clients)   │
│                       │       │                        │
│ id (UUID, PK)         │       │ id (UUID, PK)          │
│ status                │       │ status                 │
│ user_type             │       │ registration_type      │
│ tin                   │       │ user_type              │
│ business_reg_number   │       │ email (unique)         │
│ legal_name            │       │ phone_number           │
│ trading_name          │       │ nin (unique)           │
│ primary_email         │       │ legal_name             │
│ primary_phone         │       │ iam_user_id (→ IAM)    │
│ address (JSON)        │       │ *_verified flags       │
│ contact_person        │       │ metadata (JSON)        │
│ *_verified flags      │       └──────────┬─────────────┘
│ metadata (JSON)       │                  │
└──────────┬────────────┘                  │
           │                               │
           │       ┌──────────────────┐    │
           └───────┤   EntityUser     ├────┘
                   │ (many-to-many)   │
                   │                  │
                   │ entity (FK)      │
                   │ user (FK)        │
                   │ role (primary/   │
                   │   representative/│
                   │   authorized)    │
                   │ is_active        │
                   │ permissions (JSON)│
                   └──────────────────┘
```

### 3.2 Complete Model Registry

| Model | Table | PK Type | Key Fields |
|---|---|---|---|
| **Entity** | `entities` | UUID | status, user_type, tin (unique), business_registration_number, legal_name, trading_name, primary_email, primary_phone, address (JSON), *_verified flags |
| **User** | `client_users` | UUID | status, registration_type, user_type, email (unique), phone_number, nin (unique), legal_name, iam_user_id (→ IAM), *_verified flags |
| **EntityUser** | `entity_users` | UUID | entity (FK), user (FK), role, is_active, linked_by, unlinked_at, permissions (JSON) |
| **UserProfile** | `user_profiles` | UUID | user (OneToOne), preferred_language, notification_preferences (JSON), document_preferences (JSON), active_entity_id |
| **ExternalEntity** | `external_entities` | UUID | application_id, application_type, entity_role, legal_name, tin, linked_entity (FK → Entity, nullable) |
| **EntityApplication** | `entity_applications` | UUID | entity (FK), application_id, application_type, application_reference, status |
| **EntityDocument** | `entity_documents` | UUID | entity (FK), document_id (→ doc-records), document_type, verification_status, cached_title/file_name/file_size/mime_type |
| **UserDocument** | `user_documents` | UUID | user (FK), document_id (→ doc-records), document_type, verification_status, cached metadata fields |
| **VerificationConfiguration** | `verification_configurations` | UUID | user_type, account_type (unique together), requires_nin/tin/brela/phone, *_manual flags |
| **UserVerification** | `user_verifications` | UUID | user (FK), verification_type (EMAIL/NIN/PHONE), status, verification_method (auto/manual), document_id |
| **EntityVerification** | `entity_verifications` | UUID | entity (FK), verification_type (EMAIL/TIN/BRELA/PHONE), status, verification_method |
| **AuditLog** | `audit_logs` | BigAuto | user_id, action, resource_type, resource_id, ip_address, severity, success |

### 3.3 Enumerations

| Enum | Values | Used By |
|---|---|---|
| `EntityStatus` | `pending`, `active`, `suspended`, `deactivated` | Entity |
| `UserStatus` | `pending`, `active`, `suspended`, `deactivated` | User |
| `RegistrationType` | `individual`, `entity_default`, `entity_added` | User |
| `EntityUserRole` | `primary`, `representative`, `authorized` | EntityUser |
| `UserType` | `resident`, `foreign` | Entity, User, VerificationConfiguration |
| `AccountType` | `individual`, `entity` | VerificationConfiguration |

### 3.4 Entity Document Types

| Entity Documents | User Documents |
|---|---|
| `business_registration` (Business Registration Certificate) | `nin_card` (NIN Card) |
| `tin_certificate` (TIN Certificate) | `passport` (Passport) |
| `business_license` (Business License) | `drivers_license` (Driver's License) |
| `articles_of_incorporation` (Articles of Incorporation) | `profile_photo` (Profile Photo) |
| `other` (Other) | `other` (Other) |

---

## 4. Two-Tier Verification System

The client service implements a two-tier verification model that governs entity and user activation.

### Tier 1 — Basic Identity (Immediate)

- **Email verification** via OTP (always required)
- Grants: `pending` status, ability to access verification endpoints
- Performed during registration flow

### Tier 2 — Full Identity (Configurable)

Requirements are determined by `VerificationConfiguration` based on `user_type` × `account_type`:

| User Type | Account Type | Possible Requirements |
|---|---|---|
| Resident | Individual | NIN (NIDA API or manual), Phone (OTP or manual) |
| Resident | Entity | TIN (TRA API or manual), BRELA (API or manual), Phone |
| Foreign | Individual | NIN (manual only), Phone |
| Foreign | Entity | TIN (manual), BRELA (manual), Phone |

Each requirement has a `manual` flag:
- `manual = False` → Automated API verification (NIDA, TRA, BRELA)
- `manual = True` → User uploads document, admin reviews and approves/rejects

### Verification Flow

```
Registration
    │
    ├─ Create Entity/User → status: PENDING
    ├─ Create IAM Account (via IAMClient)
    ├─ Send Email OTP ────────────────────┐
    │                                      │
    ▼                                      ▼
Tier 1: Email OTP Verified          (email_verified = true)
    │
    ├─ Check VerificationConfiguration
    │   for user_type + account_type
    │
    ▼
Tier 2: Identity Verifications
    ├─ NIN → NIDA API (auto) or document upload (manual)
    ├─ TIN → TRA API (auto) or document upload (manual)
    ├─ BRELA → BRELA API (auto) or document upload (manual)
    ├─ Phone → OTP (auto) or document upload (manual)
    │
    ▼
All Tier 2 Complete
    │
    ├─ Entity/User status → ACTIVE
    ├─ IAM account activated (IAMClient.update_user_active_status)
    └─ External user roles assigned (IAMClient.assign_external_user_roles)
```

### Admin Override

Staff with `client:admin:create_user` permission can create users with verification overrides:
- Skip specific verification steps
- Mark verifications as pre-approved
- Auto-activate users on creation

---

## 5. API Reference

### 5.1 Root URL Structure

```
/health/                    → Health check (public)
/api/v1/                    → All API endpoints (via api_urls.py)
    ├── entities/           → Entity CRUD + registration
    ├── users/              → User CRUD + registration + profile
    ├── entity-users/       → Entity-user relationship management
    ├── verify/             → Verification endpoints (NIN, TIN, BRELA, OTP)
    ├── applications/       → Application linking
    ├── external-entities/  → External entity management
    ├── admin/              → Admin endpoints (statistics, audit, config)
    └── api/schema/         → OpenAPI schema (drf-spectacular)
```

### 5.2 Entity Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `POST` | `/api/v1/entities/register/` | `AllowAny` | **Public.** Full entity registration: creates entity + default user + IAM account + sends email OTP |
| `GET` | `/api/v1/entities/` | `HasServiceAccess` | List entities (paginated, filterable by status, TIN) |
| `POST` | `/api/v1/entities/` | `HasServiceAccess` | Create entity (admin) |
| `GET` | `/api/v1/entities/<id>/` | `IsLinkedToEntity` | Get entity detail (lazy-syncs verification from primary user) |
| `PUT/PATCH` | `/api/v1/entities/<id>/` | `IsLinkedToEntity` | Update entity |
| `DELETE` | `/api/v1/entities/<id>/` | `IsLinkedToEntity` | Delete entity |

### 5.3 User Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `POST` | `/api/v1/users/register/individual/` | `AllowAny` | **Public.** Individual user registration + IAM account + email OTP |
| `GET` | `/api/v1/users/` | `HasServiceAccess` | List users (paginated, filterable) |
| `POST` | `/api/v1/users/` | `HasServiceAccess` | Create user (admin) |
| `GET/PUT/PATCH` | `/api/v1/users/me/` | `AllowIndividualUsers` | Current user self-service |
| `GET/PUT/PATCH/DELETE` | `/api/v1/users/<id>/` | `IsAuthenticated` | User CRUD by ID |
| `GET/PUT/PATCH` | `/api/v1/users/<id>/profile/` | `CanAccessOwnProfile` | User profile (lang, prefs, active entity) |

### 5.4 Entity-User Relationship Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `GET` | `/api/v1/entities/<id>/users/` | `IsAuthenticated` | List users linked to entity |
| `POST` | `/api/v1/entities/<id>/users/` | `IsAuthenticated` | Link existing user to entity |
| `POST` | `/api/v1/entities/<id>/users/create/` | `IsAuthenticated` | Create and link new user |
| `POST` | `/api/v1/entities/<id>/users/add/` | `IsAuthenticated` | Link user (alternate path) |
| `DELETE` | `/api/v1/entities/<id>/users/<user_id>/` | `IsAuthenticated` | Unlink user from entity |
| `DELETE` | `/api/v1/entity-users/<id>/unlink/` | `IsAuthenticated` | Unlink by EntityUser ID |
| `GET` | `/api/v1/users/me/entities/` | `AllowIndividualUsers` | Current user's linked entities |
| `GET` | `/api/v1/users/<id>/entities/` | `IsAuthenticated` | User's linked entities by ID |
| `POST` | `/api/v1/users/me/switch-entity/` | `IsAuthenticated` | Switch active entity context |
| `POST` | `/api/v1/users/<id>/switch-entity/` | `IsAuthenticated` | Switch entity for user by ID |

### 5.5 Verification Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `POST` | `/api/v1/verify/nin/` | `AllowIndividualUsers` | Verify NIN via NIDA API |
| `POST` | `/api/v1/verify/tin/` | `IsAuthenticated` | Verify TIN via TRA API |
| `POST` | `/api/v1/verify/brela/` | `IsAuthenticated` | Verify business registration via BRELA API |
| `POST` | `/api/v1/verify/email/send/` | `AllowAny` | **Public.** Send email OTP |
| `POST` | `/api/v1/verify/email/resend/` | `AllowAny` | **Public.** Resend email OTP |
| `POST` | `/api/v1/verify/email/` | `AllowAny` | **Public.** Verify email OTP |
| `POST` | `/api/v1/verify/phone/send/` | `AllowIndividualUsers` | Send phone OTP via SMS |
| `POST` | `/api/v1/verify/phone/` | `AllowIndividualUsers` | Verify phone OTP |
| `POST` | `/api/v1/entities/<id>/complete-registration/` | `IsAuthenticated` | Complete entity registration (checks all verifications) |
| `POST` | `/api/v1/users/<id>/complete-registration/` | `IsAuthenticated` | Complete user registration |
| `GET` | `/api/v1/users/me/verification-status/` | `AllowIndividualUsers` | Current user verification status + tier completion |
| `GET` | `/api/v1/users/<id>/verification-status/` | `AllowIndividualUsers` | User verification status by ID |
| `GET` | `/api/v1/entities/<id>/verification-status/` | `AllowIndividualUsers` | Entity verification status |
| `GET` | `/api/v1/verify/requirements/` | — | Get verification requirements for type |
| `GET` | `/api/v1/verify/summary/` | — | Verification summary |
| `POST` | `/api/v1/users/verify/upload/` | `IsAuthenticated` | Upload manual verification document (user) |
| `POST` | `/api/v1/entities/verify/upload/` | `IsAuthenticated` | Upload manual verification document (entity) |

### 5.6 Document Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `GET` | `/api/v1/entities/<id>/documents/` | `IsAuthenticated` | List entity documents (Tier 2 required) |
| `POST` | `/api/v1/entities/<id>/documents/` | `IsAuthenticated` | Upload entity document |
| `GET` | `/api/v1/entities/<id>/documents/<doc_id>/` | `IsAuthenticated` | Entity document detail + download URL |
| `DELETE` | `/api/v1/entities/<id>/documents/<doc_id>/` | `IsAuthenticated` | Delete entity document |
| `GET` | `/api/v1/entities/<id>/documents/<doc_id>/download/` | `HasServiceAccess` | Admin download URL |
| `POST` | `/api/v1/entities/<id>/documents/sync/` | `IsAuthenticated` | Sync all entity document metadata |
| `POST` | `/api/v1/entities/<id>/documents/<doc_id>/sync/` | `IsAuthenticated` | Sync single entity document |
| `POST` | `/api/v1/entities/<id>/documents/<doc_id>/verify/` | `IsAuthenticated` | Verify/reject entity document |
| `GET` | `/api/v1/entities/<id>/documents/by-status/` | `IsAuthenticated` | Documents filtered by status |
| `GET` | `/api/v1/entities/<id>/documents/expiring/` | `IsAuthenticated` | Expiring entity documents |
| — | — | — | *User document endpoints mirror entity endpoints at `/api/v1/users/<id>/documents/`* |

### 5.7 Application & External Entity Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `GET` | `/api/v1/entities/<id>/applications/` | `IsAuthenticated` | Entity's linked applications |
| `POST` | `/api/v1/entities/<id>/applications/link/` | `IsAuthenticated` | Link application to entity |
| `GET` | `/api/v1/applications/<app_id>/entities/` | `IsAuthenticated` | All entities for application |
| `GET/POST` | `/api/v1/applications/<app_id>/external-entities/` | `IsAuthenticated` | List/add external entities |
| `POST` | `/api/v1/external-entities/<id>/link-to-entity/<entity_id>/` | `IsAuthenticated` | Link external to registered entity |

### 5.8 Payment Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `GET` | `/api/v1/entities/<id>/payments/` | `IsAuthenticated` | Entity payments (filterable by status, application) |
| `GET` | `/api/v1/applications/<app_id>/payments/` | `IsAuthenticated` | Application payments |

### 5.9 Admin Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `GET` | `/api/v1/admin/statistics/entities/` | `HasServiceAccess` | Entity statistics (by status, type, verification) |
| `GET` | `/api/v1/admin/trends/registrations/` | `HasServiceAccess` | Registration trends (month/week/day) |
| `GET` | `/api/v1/admin/reports/entities/<id>/activity/` | `HasServiceAccess` | Entity activity report |
| `GET` | `/api/v1/admin/search/entities/` | `HasServiceAccess` | Advanced entity search |
| `GET` | `/api/v1/admin/entities/<id>/` | `HasServiceAccess` | Admin entity retrieve (no linkage check) |
| `GET` | `/api/v1/admin/audit/logs/` | `HasServiceAccess` | Paginated audit logs |
| `GET` | `/api/v1/admin/audit/logs/<id>/` | `HasServiceAccess` | Audit log detail |
| `GET/POST` | `/api/v1/admin/verification-configs/` | `HasServiceAccess` | List/create verification configs |
| `GET/PUT/DELETE` | `/api/v1/admin/verification-configs/<id>/` | `HasServiceAccess` | Manage verification config |
| `GET` | `/api/v1/admin/verification-configs/by-type/` | `HasServiceAccess` | Config by user_type + account_type |
| `GET` | `/api/v1/admin/verifications/all/` | `HasServiceAccess` | All verifications with status counts |
| `GET` | `/api/v1/admin/verifications/pending/` | `HasServiceAccess` | Pending manual verifications |
| `POST` | `/api/v1/admin/verifications/users/<id>/approve/` | `HasServiceAccess` | Approve user verification |
| `POST` | `/api/v1/admin/verifications/users/<id>/reject/` | `HasServiceAccess` | Reject user verification |
| `POST` | `/api/v1/admin/verifications/entities/<id>/approve/` | `HasServiceAccess` | Approve entity verification |
| `POST` | `/api/v1/admin/verifications/entities/<id>/reject/` | `HasServiceAccess` | Reject entity verification |
| `GET` | `/api/v1/admin/users/create/requirements/` | `require_permission('client:admin:create_user')` | Dynamic verification requirements |
| `POST` | `/api/v1/admin/users/create/individual/` | `require_permission('client:admin:create_user')` | Admin create individual user |
| `POST` | `/api/v1/admin/users/create/entity-user/` | `require_permission('client:admin:create_user')` | Admin create entity user (501 — not yet implemented) |

### 5.10 Health Check

| Method | Path | Permission | Description |
|---|---|---|---|
| `GET` | `/health/` | Public | Checks database + Redis connectivity |

---

## 6. Permission System

### 6.1 Permission Classes

| Class | Behavior |
|---|---|
| `HasServiceAccess` | JWT validated, user has `client-service` in services list. Superusers bypass. |
| `IsLinkedToEntity` | User must be linked to at least one entity. Superusers bypass. |
| `IsEntityUser` | Object-level: user must be linked to the specific entity. Superusers bypass. |
| `CanAccessOwnProfile` | Object-level: user can only access their own profile. |
| `AllowIndividualUsers` | Allows all authenticated users (individual or entity-linked). Checks `request.user_id`. |
| `require_permission(code)` | Factory: returns a class that checks for specific permission code in `permissions_flat`. Superusers bypass. |

### 6.2 Special Decorator

| Name | Behavior |
|---|---|
| `@require_identity_verification` | Checks Tier 2 completion before allowing access. Used on document expiry, application, and payment views. |

### 6.3 Registered Permission Codes (20 total)

| Code | Category |
|---|---|
| `client:view` | Client management |
| `client:manage` | Client management |
| `verification_config:view` | Verification management |
| `verification_config:manage` | Verification management |
| `verification_review:view` | Verification management |
| `verification_review:approve` | Verification management |
| `client_report:view` | Reports & analytics |
| `client_audit:view` | Audit & compliance |
| `client:profile:view` | Self-service |
| `client:profile:update` | Self-service |
| `client:verification:view` | Self-service |
| `client:verification:submit` | Self-service |
| `client:entity:view` | Self-service |
| `client:application:create` | Self-service |
| `client:application:view` | Self-service |
| `client:document:view` | Self-service |
| `client:document:upload` | Self-service |
| `client:admin:create_user` | Admin operations |
| `client:admin:manage_verifications` | Admin operations |
| `client:admin:view_all` | Admin operations |

### 6.4 JWT Middleware Behavior

**Skip paths** (no authentication required):
- `/health/`, `/admin/`, `/static/`, `/media/`
- `/api/v1/auth/`, `/api/v1/token/`
- `/api/v1/users/register/`, `/api/v1/entities/register/`
- `/api/v1/verify/email/send/`, `/api/v1/verify/email/resend/`, `/api/v1/verify/email/`

**Self-service exemptions** (authenticated but no service access check):
- `/verify/`, `/users/me/`, verification-status endpoints, entity detail GET

**Service access check**: user's JWT `services` list must include `client-service`, `clients`, or `client`, OR the user must have `client`-prefixed permissions in `permissions_flat`.

---

## 7. Core Services

### 7.1 OTPService

Generates and verifies OTPs for email and phone verification.

| Method | Description |
|---|---|
| `generate_otp(identifier, purpose)` | Generates random N-digit OTP, stores in Redis cache |
| `verify_otp(identifier, purpose, otp)` | Verifies OTP, tracks attempts, returns `{verified, error, remaining_attempts}` |
| `resend_otp(identifier, purpose)` | Deletes old OTP, generates new one |

**Configuration:**
- `OTP_LENGTH`: default 6
- `OTP_EXPIRY_MINUTES`: default 10
- `OTP_MAX_ATTEMPTS`: default 3
- **Cache key**: `otp:{purpose}:{identifier}` (TTL: 600s)

### 7.2 NotificationService

Publishes notification events to Kafka via `NotificationPublisher`.

| Method | Template Code | Priority | Description |
|---|---|---|---|
| `send_email_otp()` | `client.user.email_otp` | high | Email OTP for verification |
| `send_sms_otp()` | `client.user.sms_otp` | high | SMS OTP for verification |
| `send_document_expiry_notification()` | `client.entity.document_expiry` | normal | Expiring document alerts |
| `send_notification()` | (generic) | configurable | Generic notification wrapper |

### 7.3 DocumentMetadataSyncService

Syncs document metadata from document-records-service to keep local cached fields current.

| Method | Description |
|---|---|
| `sync_entity_document(entity_doc, force)` | Sync single entity document if cache > 24h old |
| `sync_user_document(user_doc, force)` | Sync single user document |
| `sync_all_stale_documents(max_age_hours, limit)` | Batch sync all stale documents |

### 7.4 DocumentValidationService

Validates document uploads against type-specific rules.

**Entity required documents**: `business_registration` (10MB), `tin_certificate` (5MB)
**User required documents**: `nin_card` (5MB)

### 7.5 VerificationConfigurationService

CRUD operations on verification configurations with business rule validation.

### 7.6 VerificationRequirementService

Wraps `GetVerificationRequirementsUseCase` and `CheckVerificationCompletionUseCase` to determine what verifications a user/entity still needs.

### 7.7 PasswordResetTokenService

Generates password setup links for newly created users. TODO: token storage in Redis is not yet implemented — `validate_token()` always returns `{valid: True}`.

---

## 8. Use Cases

### 8.1 Entity Use Cases (~20 classes)

| Use Case | Description |
|---|---|
| `RegisterEntityUseCase` | Full registration: create entity → create default user → create IAM account → send email OTP |
| `CreateEntityUseCase` | Creates entity record |
| `GetEntityUseCase` / `ListEntitiesUseCase` | Retrieve / list with pagination |
| `UpdateEntityUseCase` / `DeleteEntityUseCase` | Modify / remove entity |
| `VerifyNINUseCase`, `VerifyTINUseCase`, `VerifyBRELAUseCase` | API-based verification calls |
| `CompleteEntityRegistrationUseCase` | Checks all verifications, activates if complete |
| `ActivateEntityOnVerificationCompleteUseCase` | Activates entity + IAM account + assigns external roles |
| `UploadEntityDocumentUseCase` | Uploads to doc-records, creates local reference |
| `SyncEntityDocumentUseCase`, `SyncAllEntityDocumentsUseCase` | Metadata sync from doc-records |
| `VerifyEntityDocumentUseCase` | Admin verify/reject document |
| `CheckEntityDocumentExpiryUseCase`, `CheckAllExpiringDocumentsUseCase` | Expiry detection |
| `SearchEntitiesUseCase` | Full-text search with filters |
| `SendEntityNotificationUseCase` | Sends notification to entity contacts |

### 8.2 User Use Cases (~18 classes)

| Use Case | Description |
|---|---|
| `RegisterIndividualUserUseCase` | Full registration: create user → create IAM account → profile → email OTP |
| `AdminCreateUserUseCase` | Admin creates user with verification overrides, auto-activation |
| `CreateUserUseCase` / `GetUserUseCase` / `UpdateUserUseCase` / `DeleteUserUseCase` | CRUD |
| `SendEmailOTPUseCase`, `VerifyEmailOTPUseCase` | Email OTP flow |
| `SendPhoneOTPUseCase`, `VerifyPhoneOTPUseCase` | Phone OTP flow |
| `CompleteUserRegistrationUseCase` | Checks all verifications |
| `ActivateUserOnVerificationCompleteUseCase` | Activates user + IAM + roles |
| `GetUserProfileUseCase`, `UpdateUserProfileUseCase` | Profile management |
| User document use cases | Mirror entity document use cases |

### 8.3 Entity-User Use Cases (6 classes)

| Use Case | Description |
|---|---|
| `AddUserToEntityUseCase` | Link existing user by ID or email |
| `CreateAndLinkUserToEntityUseCase` | Create new user and link in one operation |
| `UnlinkUserFromEntityUseCase` | Soft-delete link (sets `unlinked_at`) |
| `SwitchActiveEntityUseCase` | Updates `UserProfile.active_entity_id` |
| `GetUserEntitiesUseCase` / `GetEntityUsersUseCase` | Query linked users/entities |

### 8.4 Application Use Cases

| Use Case | Description |
|---|---|
| `LinkApplicationToEntityUseCase` | Creates EntityApplication record |
| `UpdateApplicationStatusUseCase` | Updates application status (triggered by Kafka events) |
| `GetEntityApplicationsUseCase` / `GetApplicationEntitiesUseCase` | Query applications |
| `AddExternalEntityToApplicationUseCase` | Add unregistered entity to application |
| `LinkExternalEntityToRegisteredEntityUseCase` | Link external entity to a registered entity |

### 8.5 Payment Use Cases

| Use Case | Description |
|---|---|
| `GetEntityPaymentsUseCase` | Get payments for entity |
| `GetApplicationPaymentsUseCase` | Get payments for application |
| `UpdatePaymentStatusUseCase` | Update payment status (triggered by Kafka events) |

### 8.6 Verification Use Cases

| Use Case | Description |
|---|---|
| `GetVerificationRequirementsUseCase` | Gets required verifications from VerificationConfiguration |
| `CheckVerificationCompletionUseCase` | Checks completion percentage, missing items |
| `ReviewManualVerificationUseCase` | Admin approve/reject manual verification |
| `UploadVerificationDocumentUseCase` | Upload document for manual verification |

### 8.7 Analytics Use Cases

| Use Case | Description |
|---|---|
| `GetEntityStatisticsUseCase` | Statistics by status, type, verification |
| `CachedEntityStatisticsUseCase` | Cached wrapper (30-minute TTL) |

---

## 9. Repository Layer

### 9.1 Interfaces (8 total)

| Interface | Key Methods |
|---|---|
| `IEntityRepository` | `create`, `get_by_id`, `get_by_tin`, `get_by_email`, `update`, `list_all(skip, limit, filters, order_by)`, `search`, `count` |
| `IUserRepository` | `create`, `get_by_id`, `get_by_email`, `get_by_nin`, `get_by_iam_user_id`, `update`, `list_all` |
| `IEntityUserRepository` | `create`, `get_active_by_entity_and_user`, `get_users_by_entity`, `get_entities_by_user`, `get_primary_user_for_entity`, `unlink`, `update` |
| `IEntityDocumentRepository` | `create`, `get_by_id`, `get_by_document_id`, `get_by_entity(entity_id, doc_type, status)`, `update`, `delete`, `count` |
| `IUserDocumentRepository` | `create`, `get_by_id`, `get_by_document_id`, `get_by_user(user_id, doc_type, status)`, `update`, `delete` |
| `IEntityApplicationRepository` | `create`, `get_by_application_id`, `get_by_entity(entity_id, type, status)`, `update`, `delete`, `count` |
| `IExternalEntityRepository` | `create`, `get_by_id`, `get_by_application(app_id, role)`, `get_by_tin`, `link_to_entity`, `update`, `delete` |
| `IVerificationConfigurationRepository` | `create`, `get_by_id`, `get_by_type(user_type, account_type)`, `list_all`, `update`, `delete` |

### 9.2 Implementations (9 total)

Each interface has one Django ORM implementation in `apps/infrastructure/persistence/repositories/`, plus:
- `CachedEntityRepository` — decorates `EntityRepositoryImpl` with Redis read-through caching (1-hour TTL)

---

## 10. External Integrations

### 10.1 IAM Service (`IAMClient`)

Base URL: `http://iam-service:8000`, auth: `X-Service-Token`

| Operation | Endpoint | When Called |
|---|---|---|
| Create portal user | `POST /api/v1/auth/register/` | During entity/user registration |
| Get user by ID | `GET /api/v1/users/<id>/` | User lookup |
| Lookup by email | `GET /api/v1/users/lookup/email/<email>/` | Email-based user resolution |
| Activate user | `POST /api/v1/users/<id>/activate-for-client-service/` | When all Tier 2 verifications pass |
| Assign external roles | `POST /api/v1/rbac/users/<id>/assign-external-roles/` | After user activation |

### 10.2 Document Records Service (`DocumentClient`)

Base URL: `http://document-service:8002`, auth: `X-Service-Token`

| Operation | Endpoint | When Called |
|---|---|---|
| Create document | `POST /api/v1/documents/` | Entity/user document upload |
| Upload file | `POST /api/v1/documents/<id>/upload/` | File attachment |
| Get document | `GET /api/v1/documents/<id>/` | Metadata sync, detail views |
| Get file access | `GET /api/v1/documents/<id>/file-access/` | Download URL generation |
| Delete document | `DELETE /api/v1/documents/<id>/` | Document removal |

### 10.3 Work Orchestration Service (`NotificationClient` — Legacy)

Base URL: `http://work-orchestration-service:8004`, auth: `X-Service-Token`

| Operation | Endpoint | Status |
|---|---|---|
| Send email | `POST /api/v1/workflow/notifications/email/send/` | **Legacy** — being replaced by Kafka `NotificationPublisher` |
| Send SMS | `POST /api/v1/notifications/sms` | **Legacy** |
| Bulk notification | `POST /api/v1/notifications/bulk` | **Legacy** |

### 10.4 Government API Integrations

| Service | Client Class | API URL Setting | Status |
|---|---|---|---|
| **NIDA** (National ID Authority) | `NIDAClient` | `NIDA_API_URL` | **Placeholder** — `verify_nin()` not connected to real API |
| **TRA** (Tanzania Revenue Authority) | `TRAClient` | `TRA_API_URL` | **Placeholder** — `verify_tin()` not connected to real API |
| **BRELA** (Business Registration) | `BRELAClient` | `BRELA_API_URL` | **Placeholder** — `verify_business_registration()` not connected to real API |

All three government clients have the same pattern:
- Accept API URL + API key from settings
- Return structured `{verified, name/legal_name, ..., error}` response
- Currently return placeholder/mock data with TODO comments

---

## 11. Kafka Event Architecture

### 11.1 Topics Produced

| Topic | Event Types | When Published |
|---|---|---|
| `service.permission.registry` | `service_permission_registration`, `service_permission_update`, `service_health_check` | On startup, permission changes |
| `notification-templates` | `template.registered` | On startup (8 templates from `notifications.yaml`) |
| `notifications-urgent` | `notification.send` | — (not currently used) |
| `notifications-high` | `notification.send` | Email OTP, SMS OTP |
| `notifications-normal` | `notification.send` | Document expiry notifications, generic notifications |
| `notifications-low` | `notification.send` | — (reserved for low-priority) |
| `notifications` | `notification.send` | Fallback if priority topic unavailable |

### 11.2 Topics Consumed

| Topic | Event Types | Handler | Action |
|---|---|---|---|
| `application-service.application.created` | `application.created` | `handle_application_created` | Links application to entity via `LinkApplicationToEntityUseCase` |
| `application-service.application.status_changed` | `application.status_changed` | `handle_application_status_changed` | Updates application status |
| `finance-service.payment.completed` | `payment.completed` | `handle_payment_completed` | Updates payment + sends confirmation notification |
| `finance-service.payment.completed` | `payment.failed` | `handle_payment_failed` | Sends payment failure notification |

### 11.3 Consumer Configuration

| Setting | Value |
|---|---|
| Consumer Group | `client-service-consumer-group` |
| Auto Offset Reset | `latest` |
| Auto Commit | `True` (1s interval) |
| Management Command | `python manage.py run_kafka_consumer` |
| Dedicated Container | `fims-client-kafka-consumer` |

### 11.4 Producer Configuration

| Setting | Value |
|---|---|
| Client ID | `client-service` |
| Ack Timeout | 10 seconds |
| Singleton | Lazy-initialized via `get_kafka_producer()` |
| Notification Partitioning | By `template_code` |

### 11.5 Notification Event Envelope

```json
{
  "event_type": "notification.send",
  "event_version": "1.0",
  "timestamp": "2026-02-24T10:00:00Z",
  "source_service": "client-service",
  "notification_id": "uuid-v4",
  "idempotency_key": "template_code-recipient-YYYYMMDDTHHM",
  "data": {
    "template_code": "client.user.email_otp",
    "priority": "high",
    "recipients": {
      "email": ["user@example.com"]
    },
    "context": {
      "otp": "123456",
      "user_first_name": "John",
      "otp_expiry_minutes": 10
    }
  }
}
```

---

## 12. Celery Tasks & Scheduling

### 12.1 Beat Schedule

| Task | Schedule | Parameters | Description |
|---|---|---|---|
| `sync_document_metadata` | Every hour (3600s) | `max_age_hours=24`, `limit=100` | Syncs all entity + user documents with stale metadata |
| `check_document_expiry` | Daily (86400s) | `days_before_expiry=30` | Checks for expiring/expired documents, sends notifications per entity |

### 12.2 On-Demand Tasks

| Task | Parameters | Triggered By |
|---|---|---|
| `sync_entity_document_metadata` | `entity_document_id`, `force` | Document sync endpoints |
| `sync_user_document_metadata` | `user_document_id`, `force` | Document sync endpoints |

### 12.3 Celery Configuration

| Setting | Value |
|---|---|
| Broker | `redis://redis-client-service:6379/1` |
| Result Backend | `redis://redis-client-service:6379/1` |
| Serializer | JSON |
| Timezone | `Africa/Dar_es_Salaam` |
| Task Time Limit | 30 minutes |
| Soft Time Limit | 25 minutes |
| Autodiscover | `apps.core`, `apps.api`, `apps.audit` |

---

## 13. Caching Strategy

### 13.1 Cache Configuration

| Setting | Value |
|---|---|
| Backend | `django_redis.cache.RedisCache` |
| URL | `redis://redis-client-service:6379/0` |
| Key Prefix | `client_service` |
| Default Timeout | 3600s (1 hour) |
| Compressor | ZlibCompressor |
| Ignore Exceptions | `True` (graceful degradation) |

### 13.2 Cache Key Patterns

| Pattern | TTL | Usage |
|---|---|---|
| `entity:{id}` | 1h | Single entity read-through |
| `entity:tin:{tin}` | 1h | Entity lookup by TIN |
| `entity:email:{email}` | 1h | Entity lookup by email |
| `entity:list:{hash}` | 5min | Entity list results |
| `entity:stats:{range}` | 30min | Entity statistics |
| `user:{id}` | 1h | Single user |
| `user:entities:{id}` | 1h | User's linked entities |
| `entity:users:{id}` | 1h | Entity's linked users |
| `entity:documents:{id}:{hash}` | 1h | Entity documents |
| `user:documents:{id}:{hash}` | 1h | User documents |
| `otp:{purpose}:{identifier}` | 10min | OTP codes |

### 13.3 Cache Invalidation

The `CacheService` provides targeted invalidation:
- `invalidate_entity(entity_id)` — clears entity + entity documents + entity users keys
- `invalidate_user(user_id)` — clears user + user entities keys
- `CachedEntityRepository` — invalidates on `create` and `update` operations

**Note:** `delete_pattern()` is not fully implemented — logs a warning. Individual key deletion works correctly.

---

## 14. Audit System

### 14.1 Audit Middleware

The `AuditMiddleware` automatically logs all write operations (POST, PUT, PATCH, DELETE) except on excluded paths (`/health`, `/metrics`, `/api/v1/clients/audit/`).

It extracts:
- Resource type from URL path (entity, user, document, application)
- Resource ID from URL path
- Action name (e.g., `ENTITY_CREATE`, `USER_UPDATE`, `DOCUMENT_DELETE`)
- IP address from `X-Forwarded-For` or `REMOTE_ADDR`
- User agent from request headers

### 14.2 Audit Actions (50+ total)

| Category | Actions |
|---|---|
| Entity | `ENTITY_CREATE`, `ENTITY_UPDATE`, `ENTITY_DELETE`, `ENTITY_REGISTER`, `ENTITY_VERIFY_NIN`, `ENTITY_VERIFY_TIN`, `ENTITY_VERIFY_BRELA`, `ENTITY_VERIFY_EMAIL`, `ENTITY_VERIFY_PHONE`, `ENTITY_COMPLETE_REGISTRATION` |
| User | `USER_CREATE`, `USER_UPDATE`, `USER_DELETE`, `USER_REGISTER`, `USER_VERIFY_EMAIL`, `USER_VERIFY_PHONE`, `USER_VERIFY_NIN`, `USER_COMPLETE_REGISTRATION` |
| Entity-User | `ENTITY_USER_LINK`, `ENTITY_USER_UNLINK`, `ENTITY_USER_ROLE_CHANGE`, `ENTITY_USER_SWITCH_ACTIVE` |
| Document | `DOCUMENT_UPLOAD`, `DOCUMENT_DELETE`, `DOCUMENT_VERIFY`, `DOCUMENT_REJECT`, `DOCUMENT_SYNC` |
| Application | `APPLICATION_LINK`, `APPLICATION_STATUS_UPDATE`, `EXTERNAL_ENTITY_ADD`, `EXTERNAL_ENTITY_LINK` |
| Payment | `PAYMENT_VIEW`, `PAYMENT_STATUS_UPDATE` |
| Notification | `NOTIFICATION_SENT` |

### 14.3 Severity Levels

`low`, `medium`, `high`, `critical`

---

## 15. Notification Templates

The service registers 10 notification templates via Kafka on startup.

| Template Code | Channels | Category | Description |
|---|---|---|---|
| `client.user.email_otp` | email | verification | Email verification OTP |
| `client.user.sms_otp` | sms | verification | SMS verification OTP |
| `client.entity.registration` | email | registration | Entity registration confirmation |
| `client.user.registration` | email | registration | Individual user registration confirmation |
| `client.entity.document_expiry` | email, sms | document | Document expiry alert |
| `client.user.verification.approved` | email | verification | User verification approved |
| `client.user.verification.rejected` | email | verification | User verification rejected |
| `client.entity.verification.approved` | email | verification | Entity verification approved |
| `client.entity.verification.rejected` | email | verification | Entity verification rejected |
| `client.user.admin_created_welcome` | email | account | Welcome email for admin-created users |

Templates are loaded from `apps/core/templates/notifications.yaml` and published to the `notification-templates` Kafka topic via `TemplateRegistry.register_templates()`.

---

## 16. Infrastructure & Deployment

### 16.1 Dockerfile

- Base image: `python:3.11-slim`
- System deps: `gcc`, `postgresql-client`, `libpq-dev`, `curl`
- Exposes port: **8006**
- Healthcheck: `curl -f http://localhost:8006/health/` every 30s
- Entrypoint: `scripts/entrypoint.sh` (waits for PostgreSQL, runs migrations, collectstatic)

### 16.2 Production Docker Compose

- Uses `.env.prod` instead of `.env`
- Same 6 containers as dev
- All on `fims-network` (external)
- Health checks enabled with start periods

### 16.3 Management Commands

| Command | Description |
|---|---|
| `python manage.py run_kafka_consumer` | Starts Kafka consumer for 3 topics. Accepts `--topics` arg. |
| `python manage.py register_permissions_kafka` | Publishes all 20 permissions to `service.permission.registry` |

### 16.4 Dependencies (Key Packages)

| Package | Version | Purpose |
|---|---|---|
| Django | 4.2.7 | Web framework |
| djangorestframework | 3.14.0 | REST API |
| djangorestframework-simplejwt | 5.3.0 | JWT support |
| kafka-python | 2.0.2 | Kafka producer |
| confluent-kafka | 2.3.0 | Kafka consumer |
| celery[redis] | 5.3.4 | Task queue |
| psycopg2-binary | 2.9.9 | PostgreSQL driver |
| redis | 4.6.0 | Redis client |
| django-redis | 5.4.0 | Django cache backend |
| drf-spectacular | 0.27.2 | OpenAPI docs |
| PyJWT | 2.8.0 | JWT decoding |
| requests | 2.31.0 | HTTP client |
| prometheus-client | 0.19.0 | Monitoring |
| gunicorn | 21.2.0 | Production server |

### 16.5 Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | `SECRET_KEY` | Shared JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `KAFKA_BOOTSTRAP_SERVERS` | `fims-kafka:9092` | Kafka broker |
| `IAM_SERVICE_URL` | `http://iam-service:8000` | IAM service base URL |
| `DOCUMENT_SERVICE_URL` | `http://document-service:8002` | Document service base URL |
| `WORK_ORCHESTRATION_SERVICE_URL` | `http://work-orchestration-service:8004` | Work orchestration base URL |
| `CLIENT_PORTAL_URL` | `http://fcc-client.{TUNNEL_DOMAIN}` | Client portal for password reset links |
| `NIDA_API_URL`, `NIDA_API_KEY` | empty | NIDA integration |
| `TRA_API_URL`, `TRA_API_KEY` | empty | TRA integration |
| `BRELA_API_URL`, `BRELA_API_KEY` | empty | BRELA integration |
| `OTP_LENGTH` | `6` | OTP digit count |
| `OTP_EXPIRY_MINUTES` | `10` | OTP cache TTL |
| `OTP_MAX_ATTEMPTS` | `3` | Max verification attempts |
| `CACHE_DEFAULT_TIMEOUT` | `3600` | Default cache TTL |
| `CACHE_ENTITY_TIMEOUT` | `3600` | Entity cache TTL |
| `CACHE_STATISTICS_TIMEOUT` | `1800` | Statistics cache TTL |
| `CACHE_LIST_TIMEOUT` | `300` | List cache TTL |

---

## 17. Known Issues & Architectural Notes

### 17.1 Placeholder Government API Integrations

The `NIDAClient`, `TRAClient`, and `BRELAClient` are all placeholders with TODO comments. The `verify_*()` methods exist but are not connected to real government APIs. Until these are integrated, the verification system relies on the manual (document upload + admin review) pathway.

### 17.2 Password Reset Token Storage Not Implemented

`PasswordResetTokenService.validate_token()` always returns `{valid: True}`. The token is not actually stored or validated against a Redis or database backend. The `generate_token()` method works but the token cannot be verified on the receiving end.

### 17.3 Admin Create Entity User Not Implemented

`AdminCreateEntityUserView` returns `HTTP 501 Not Implemented`. Only individual user creation is implemented for admin operations.

### 17.4 Dual Kafka Client Libraries

The service uses both `kafka-python` (for producers) and `confluent-kafka` (for consumers). This is consistent with other FIMS services but introduces two different APIs for Kafka operations.

### 17.5 Cache `delete_pattern()` Not Fully Implemented

The `CacheService.delete_pattern()` method logs a warning instead of performing wildcard key deletion. Individual key invalidation works, but pattern-based cache busting is incomplete.

### 17.6 Consumed Topics for Future Services

The Kafka consumer is configured to listen on topics from services not yet built:
- `application-service.application.created` → from a planned application service
- `application-service.application.status_changed` → from a planned application service
- `finance-service.payment.completed` → from a planned finance service

These consumers are ready but currently receive no events.

### 17.7 CORS Configuration Redundancy

The service configures CORS headers via `django-cors-headers` middleware, but this is redundant when running behind the API gateway which handles CORS. The IAM service explicitly removes CORS middleware; client-service retains it.

### 17.8 Entity-User Verification Sync

When fetching entity details, the view lazily syncs email/phone verification status from the entity's primary user. This means entity verification state can change on read operations, which is a side-effect pattern to be aware of.

### 17.9 Registration Flow Creates IAM Users

Both `EntityRegisterView` and `UserRegisterIndividualView` are public (`AllowAny`) and create IAM accounts via `IAMClient.create_user()`. The IAM account starts inactive and is only activated when all Tier 2 verifications complete via `IAMClient.update_user_active_status()`.

---

*This document was derived from implementation evidence in the FIMS client-service codebase. All patterns, models, endpoints, and architectural decisions described here are based on actual code analysis.*
