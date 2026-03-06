# IAM Service — Deep Architectural Reference

> **Service:** iam-service  
> **Port:** 8000  
> **Database:** `fims_db` on `postgres-iam-service` (PostgreSQL 15)  
> **Cache:** `redis-iam-service:6380`  
> **Container:** `fims-iam-service`  
> **Gateway Routes:** `/api/v1/auth/*`, `/api/v1/users/*`, `/api/v1/roles/*`, `/api/v1/rbac/*`, `/api/v1/mfa/*`, `/api/v1/sessions/*`, `/api/v1/audit-logs/*`

---

## Table of Contents

1. [Primary Responsibilities & Domain Ownership](#1-primary-responsibilities--domain-ownership)
2. [Capabilities Exposed to Other Services](#2-capabilities-exposed-to-other-services)
3. [Exclusive Ownership vs. Delegation](#3-exclusive-ownership-vs-delegation)
4. [Data Model Reference](#4-data-model-reference)
5. [Complete API Surface](#5-complete-api-surface)
6. [Authentication Flow in Detail](#6-authentication-flow-in-detail)
7. [JWT Token Architecture](#7-jwt-token-architecture)
8. [Permission Registration System (Kafka)](#8-permission-registration-system-kafka)
9. [Cross-Service Dependencies & Collaboration](#9-cross-service-dependencies--collaboration)
10. [How Other Services Consume IAM](#10-how-other-services-consume-iam)
11. [Background Tasks (Celery)](#11-background-tasks-celery)
12. [Notification Publishing](#12-notification-publishing)
13. [Integration Guide for New Services](#13-integration-guide-for-new-services)
14. [Architectural Boundaries — What Not To Do](#14-architectural-boundaries--what-not-to-do)

---

## 1. Primary Responsibilities & Domain Ownership

The IAM service is the **sole identity and access management authority** for the entire FIMS platform. It owns all of the following domains:

### 1.1 User Identity
- The canonical `User` model (UUID primary key, email as `USERNAME_FIELD`)
- User profiles (name, department, position, employee_id, phone, profile picture, signature)
- User types and status management
- Email verification flow
- User creation, update, deletion, and activation

### 1.2 Authentication
- Login (email/password + optional username support)
- JWT token issuance (access + refresh tokens with embedded permissions)
- Token refresh with session JTI rotation
- Logout with session revocation
- Token introspection
- Password reset (request + complete flow with email-based tokens)
- Password change (authenticated password update)
- Expired password reset (handles logins with expired passwords)

### 1.3 Multi-Factor Authentication (MFA)
- TOTP device enrollment and verification (via `django-otp` / `pyotp`)
- Email OTP as fallback (sends code to user's email)
- Backup codes (generation, verification, one-time use)
- MFA status management (enable/disable per user)
- MFA attempt logging

### 1.4 Session Management
- Session creation tied to JWT JTI (JSON Token Identifier)
- One-session-per-user policy (new login terminates old sessions)
- Session extension on activity (configurable idle + absolute timeouts)
- Session termination (manual admin revocation)
- Session status checking (active, expired, revoked)
- Automatic session cleanup (via Celery)

### 1.5 Role-Based Access Control (RBAC)
- Role definitions (with service associations)
- Role assignment to users (with optional expiration dates)
- Role permissions — links roles to Django permissions AND cross-service `ServicePermission` entries
- Bulk role assignment / removal
- Role assignment by user attributes
- Permission matrix data for admin UI
- Default role auto-assignment for new users (`assign_by_default`)
- External user role assignment for client service users (`assign_to_external_users`)

### 1.6 Cross-Service Permission Registry
- Consuming permission definitions from all other FIMS services via Kafka
- Creating/updating `Service` and `ServicePermission` records
- Deactivating permissions that are no longer registered by a service
- Aggregating all permissions across all services into a unified system

### 1.7 Audit Logging
- Comprehensive action-level audit trail (LOGIN, LOGOUT, ROLE_ASSIGN, PASSWORD_CHANGE, etc.)
- IP address tracking with intelligent proxy resolution (Cloudflare, X-Forwarded-For, NGINX)
- User agent logging
- Severity classification (low, medium, high, critical)
- Resource-level audit (USER, ROLE, PERMISSION, SESSION, SYSTEM, SECURITY_SETTINGS)

### 1.8 Account Security
- Account lockout on repeated failed login attempts (configurable threshold)
- Automatic unlock after lockout duration expires
- Password expiration (configurable days, warning notifications)
- Password reuse prevention (history-based)
- Password complexity validation (admin-configurable rules)
- Guessable password detection (username/personal info, sequential patterns, common passwords)
- Security settings management (singleton admin-configurable model)

### 1.9 Admin Dashboard
- Dashboard statistics (user counts, role counts, etc.)
- Dashboard charts data
- Recent activity feed

---

## 2. Capabilities Exposed to Other Services

### 2.1 JWT Token Validation (Implicit — No API Call Required)

**This is the primary capability consumed by all other services.**

IAM does not need to be called at runtime for authentication. Every other service validates JWTs locally using the shared secret. The IAM service's contribution here is the **token structure** it issues.

**JWT Payload Contract (what every other service can rely on):**
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "is_staff": true,
  "is_superuser": false,
  "permissions": {},
  "permissions_flat": ["document.read", "document.write", "hr.view_employee"],
  "services": ["document-service", "corporate-service"],
  "jti": "unique-token-identifier",
  "token_type": "access",
  "exp": 1740000000,
  "iat": 1739996400
}
```

**Key fields other services rely on:**

| Field | Type | Purpose |
|---|---|---|
| `user_id` | UUID string | Canonical user identifier across all services |
| `email` | string | User email for display and notification targeting |
| `is_superuser` | boolean | If `true`, bypass all permission checks |
| `permissions_flat` | string[] | Flat list of all permission codes. `["*"]` for superusers |
| `services` | string[] | Service names the user has access to. `["*"]` for superusers |
| `jti` | string | JWT ID — only IAM itself uses this for session binding |

### 2.2 User Lookup API (REST)

Other services call IAM to resolve user IDs to display names/emails. Three endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /api/v1/users/lookup/` | GET | Paginated, filterable, searchable user list |
| `GET /api/v1/users/lookup/email/<email>/` | GET | Single user lookup by email |
| `GET /api/v1/users/lookup/id/<user_id>/` | GET | Single user lookup by UUID |

**Response format (single user lookup):**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "username": "jdoe",
    "is_active": true,
    "user_type": "staff",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

**Usage note:** The document-records-service uses `IAMClient` with Redis-backed caching (5-minute TTL) to call these endpoints, avoiding repeated HTTP calls for the same user.

### 2.3 Token Introspection API (REST)

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `GET /api/v1/introspect/` | GET | Bearer JWT | Returns full user info + roles + permissions for the authenticated user |

**Response:**
```json
{
  "success": true,
  "data": {
    "active": true,
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "username": "jdoe",
      "first_name": "John",
      "last_name": "Doe",
      "status": "active",
      "user_type": "staff",
      "is_email_verified": true
    },
    "roles": [
      { "id": "uuid", "code": "admin", "name": "Administrator" }
    ],
    "permissions": [
      { "id": 1, "codename": "add_user", "name": "Can add user" }
    ],
    "exp": 1740000000
  }
}
```

### 2.4 User Permission Resolution API (REST)

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `GET /api/v1/profile/permissions/` | GET | Bearer JWT | Get current user's permissions (flat and by-service) |
| `GET /api/v1/profile/all-permissions/` | GET | Bearer JWT | Get all permissions available |
| `GET /api/v1/users/<user_id>/permissions/` | GET | Admin only | Get permissions for a specific user |

**Response (current user permissions):**
```json
{
  "is_superuser": false,
  "roles": [
    {
      "id": "uuid",
      "name": "Document Manager",
      "code": "doc_manager",
      "service": "document-service",
      "full_code": "document-service.doc_manager"
    }
  ],
  "permissions": ["document.read", "document.write", "document.approve"],
  "permissions_by_service": {
    "document-service": ["document.read", "document.write", "document.approve"],
    "iam": ["view_user", "change_user"]
  },
  "services": ["document-service", "iam"]
}
```

### 2.5 Permission Registration Kafka Consumer

IAM consumes permission definitions from other services via Kafka topic `service.permission.registry`. This is how other services register their permissions with the central IAM authority.

**Consumed message format:**
```json
{
  "event_type": "service_permission_registration",
  "source_service": "document-service",
  "data": {
    "service_name": "document-service",
    "service_version": "1.0.0",
    "service_description": "Document management service",
    "permissions": [
      {
        "permission_code": "document.read",
        "name": "Read Documents",
        "description": "Can read document metadata and content",
        "resource_type": "document",
        "action": "read",
        "category": "document_management"
      }
    ]
  }
}
```

**Processing logic:**
1. Upsert `Service` record (create or update by name)
2. For each permission in the payload, upsert `ServicePermission` record
3. Deactivate any `ServicePermission` entries for the service that were NOT in the current registration (stale permission cleanup)
4. Log counts: new permissions, updated permissions

### 2.6 Role Definition Kafka Consumer

IAM also consumes role definitions from services:

**Consumed message format:**
```json
{
  "event_type": "service_role_definitions",
  "data": {
    "service_name": "document-service",
    "service_version": "1.0.0",
    "roles": [
      {
        "code": "doc_manager",
        "name": "Document Manager",
        "description": "Can manage all documents",
        "permissions": ["document.read", "document.write", "document.approve"]
      }
    ]
  }
}
```

### 2.7 User Activation for Client Service (REST S2S)

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `POST /api/v1/users/<user_id>/activate-for-client-service/` | POST | X-Service-Token | Activate a user account after email verification in client service |

This is a service-to-service endpoint. The client-service calls it when an external user completes email verification.

### 2.8 External User Role Assignment (REST S2S)

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `POST /api/v1/rbac/users/<user_id>/assign-external-roles/` | POST | Service auth | Assign roles marked `assign_to_external_users=True` to a verified external user |

### 2.9 User Domain Events (Kafka)

IAM publishes user lifecycle events to Kafka:

| Topic | Event Types | Consumed By |
|---|---|---|
| `fims.iam.user.updated` | User profile changes | document-records-service (syncs cached user data) |
| `audit.events` | Audit log entries | (for centralized logging if configured) |

---

## 3. Exclusive Ownership vs. Delegation

### 3.1 What IAM Owns Exclusively (No Other Service May Do This)

| Capability | Why |
|---|---|
| **User creation and storage** | Single source of truth for all user identities |
| **Password hashing and verification** | Django's built-in PBKDF2/Argon2 — only IAM touches the password field |
| **JWT token issuance** | Only IAM generates `EnhancedAccessToken` and `EnhancedRefreshToken` |
| **Session tracking** | Only IAM binds JTI to sessions and validates session status |
| **Role definitions** | Roles are IAM-level entities that span services |
| **Permission aggregation** | Only IAM holds the unified permission registry from all services |
| **MFA enrollment and verification** | TOTP devices, backup codes, email OTP — all managed solely by IAM |
| **Audit logging for identity actions** | LOGIN, LOGOUT, ROLE_ASSIGN — IAM's audit domain |
| **Account lockout logic** | Failed attempt counting, lock duration, unlock |
| **Security settings** | Global security configuration (password policy, lockout thresholds, session timeouts) |

### 3.2 What IAM Delegates to Other Services

| Capability | Delegated To | Mechanism |
|---|---|---|
| **Notification delivery** (emails, SMS) | work-orchestration-service | Kafka `NotificationPublisher` to priority topics |
| **Password reset email sending** | work-orchestration-service | Via `NotificationPublisher` or `WorkOrchestrationClient` REST call |
| **Password expiration warning emails** | work-orchestration-service | Via `NotificationPublisher` |
| **Account lockout admin alert emails** | work-orchestration-service | Via `NotificationPublisher` |
| **Document management** | document-records-service | No direct integration currently |
| **Workflow orchestration** | work-orchestration-service | No direct integration currently |

### 3.3 What Other Services Delegate to IAM

| Service | What It Delegates | How |
|---|---|---|
| All services | User authentication | JWT validation using shared secret (no IAM call needed) |
| All services | Permission definitions | Kafka to `service.permission.registry` topic |
| client-service | User account activation | REST `POST /users/<id>/activate-for-client-service/` |
| client-service | External user role assignment | REST `POST /rbac/users/<id>/assign-external-roles/` |
| document-records-service | User name resolution | REST `GET /users/lookup/id/<id>/` (cached via IAMClient) |
| All services | User info resolution | REST user lookup endpoints |

---

## 4. Data Model Reference

### 4.1 User (apps.users.models.User)

```
Table: users
PK: id (UUIDField)
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key, auto-generated |
| `email` | EmailField | **Unique**, used as `USERNAME_FIELD` |
| `username` | CharField(150) | Unique, nullable, optional |
| `first_name` | CharField(150) | Required |
| `last_name` | CharField(150) | Required |
| `phone_number` | CharField(20) | Nullable |
| `employee_id` | CharField(50) | Unique, nullable |
| `department` | CharField(100) | Nullable |
| `position` | CharField(100) | Nullable |
| `user_type` | CharField(50) | Nullable (e.g., "staff", "external") |
| `status` | CharField(50) | Default: "active" |
| `is_active` | BooleanField | Django built-in |
| `is_staff` | BooleanField | Django built-in |
| `is_superuser` | BooleanField | Django built-in |
| `password` | CharField | Django built-in (hashed) |
| `mfa_enabled` | BooleanField | Default: False |
| `mfa_secret` | CharField(255) | Nullable |
| `profile_picture` | ImageField | `profile_pictures/%Y/%m/%d/` |
| `signature` | ImageField | `signatures/%Y/%m/%d/` |
| `email_verified_at` | DateTimeField | Nullable — set on verification |
| `email_verification_token` | CharField(255) | Cleared after verification |
| `password_reset_token` | CharField(255) | Cleared after use |
| `password_reset_expires` | DateTimeField | Nullable |
| `failed_login_attempts` | PositiveIntegerField | Default: 0, indexed |
| `locked_until` | DateTimeField | Nullable, indexed |
| `last_failed_login_at` | DateTimeField | Nullable |
| `password_changed_at` | DateTimeField | Nullable |
| `password_expires_at` | DateTimeField | Nullable, indexed |
| `last_login_at` | DateTimeField | Nullable |
| `last_login_ip` | CharField(45) | Nullable |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |
| `created_by` | FK(self) | Nullable |
| `updated_by` | FK(self) | Nullable |

**Indexes:** `email`, `is_active`, `failed_login_attempts`, `locked_until`, `password_expires_at`

### 4.2 Service (apps.roles.models.Service)

```
Table: unified_services
PK: id (UUIDField)
```

Tracks microservices that register their permissions with IAM via Kafka.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | CharField(100) | **Unique**, indexed (e.g., "document-service") |
| `version` | CharField(50) | Default: "1.0.0" |
| `description` | TextField | Nullable |
| `is_active` | BooleanField | Default: True, indexed |
| `last_registration` | DateTimeField | auto_now — updated on each Kafka registration |
| `registration_count` | IntegerField | Incremented on each re-registration |

### 4.3 Role (apps.roles.models.Role)

```
Table: roles
PK: id (UUIDField)
Unique constraint: (code, service)
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `code` | CharField(50) | Indexed — unique per service |
| `name` | CharField(100) | Display name |
| `description` | TextField | Nullable |
| `is_system` | BooleanField | Default: False — protects from deletion |
| `is_active` | BooleanField | Default: True, indexed |
| `assign_by_default` | BooleanField | Auto-assign to new staff users |
| `assign_to_external_users` | BooleanField | Auto-assign to verified external users |
| `service` | FK(Service) | Nullable — null for legacy IAM roles |
| `created_by` | FK(User) | Nullable |
| `updated_by` | FK(User) | Nullable |

**Key methods:**
- `full_code` → `"{service.name}.{code}"` or just `"{code}"` for IAM roles
- `permissions_list` → list of all permission codenames (Django + service)
- `has_permission(code)` → checks both Django and service permission types

### 4.4 ServicePermission (apps.roles.models.ServicePermission)

```
Table: unified_service_permissions
PK: id (UUIDField)
Unique constraint: (service, permission_code)
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `permission_code` | CharField(255) | Indexed (e.g., "document.read") |
| `name` | CharField(255) | Display name |
| `description` | TextField | Nullable |
| `resource_type` | CharField(100) | e.g., "document", "entity" |
| `action` | CharField(100) | e.g., "create", "read", "update", "delete" |
| `category` | CharField(100) | e.g., "document_management" |
| `is_active` | BooleanField | Default: True — deactivated when no longer registered |
| `service` | FK(Service) | Parent service |
| `django_permission` | FK(Permission) | Optional link to Django's Permission model |

### 4.5 RolePermission (apps.roles.models.RolePermission)

```
Table: role_permissions
PK: id (UUIDField)
Unique constraints: (role, permission), (role, service_permission)
```

Links roles to either Django permissions or cross-service permissions:

| Field | Type | Notes |
|---|---|---|
| `role` | FK(Role) | |
| `permission` | FK(Django Permission) | Nullable — for Django's built-in permissions |
| `service_permission` | FK(ServicePermission) | Nullable — for cross-service permissions |
| `created_by` | FK(User) | Nullable |

**Constraint:** Exactly one of `permission` or `service_permission` must be set.

### 4.6 UserRole (apps.roles.models.UserRole)

```
Table: user_roles
PK: id (UUIDField)
Unique constraint: (user, role)
```

| Field | Type | Notes |
|---|---|---|
| `user` | FK(User) | |
| `role` | FK(Role) | |
| `is_active` | BooleanField | Default: True |
| `expires_at` | DateTimeField | Nullable — for temporary role assignments |
| `assigned_by` | FK(User) | Nullable |

### 4.7 UserSession (apps.user_sessions.models.UserSession)

```
Table: user_sessions
PK: id (BigAutoField)
```

| Field | Type | Notes |
|---|---|---|
| `user` | FK(User) | |
| `session_key` | CharField(255) | Unique, nullable |
| `access_jti` | CharField(500) | **The JWT's JTI** — indexed, used for session-token binding |
| `refresh_token` | TextField | Full refresh token string |
| `ip_address` | GenericIPAddressField | |
| `user_agent` | TextField | |
| `status` | CharField(20) | "active", "expired", "revoked" |
| `idle_timeout_at` | DateTimeField | Recalculated on activity |
| `absolute_timeout_at` | DateTimeField | Set once at login |
| `last_activity_at` | DateTimeField | Updated on activity |
| `login_at` | DateTimeField | auto_now_add |
| `logout_at` | DateTimeField | Set on logout/revocation |

### 4.8 AuditLog (apps.audit.models.AuditLog)

```
Table: audit_logs
PK: id (BigAutoField)
```

| Field | Type | Notes |
|---|---|---|
| `user` | FK(User) | Nullable (for system events) |
| `action` | CharField(50) | Indexed — see action choices below |
| `resource_type` | CharField(20) | USER, ROLE, PERMISSION, SESSION, SYSTEM, etc. |
| `resource_id` | CharField(255) | ID of the affected resource |
| `ip_address` | GenericIPAddressField | With Cloudflare/proxy resolution |
| `user_agent` | TextField | |
| `description` | TextField | Human-readable description |
| `metadata` | JSONField | Arbitrary additional data |
| `severity` | CharField(20) | "low", "medium", "high", "critical" |
| `created_at` | DateTimeField | auto_now_add, indexed |

**Action choices:**
- Authentication: `LOGIN`, `LOGOUT`, `LOGIN_FAILED`, `PASSWORD_CHANGE`, `PASSWORD_RESET_REQUEST`, `PASSWORD_RESET_COMPLETE`, `PASSWORD_EXPIRED`, `PASSWORD_EXPIRATION_WARNING`, `PASSWORD_CHANGE_FORCED`, `EMAIL_VERIFY`, `ACCOUNT_LOCKED`, `ACCOUNT_UNLOCKED`, `ACCOUNT_UNLOCKED_AUTO`
- User management: `USER_CREATE`, `USER_UPDATE`, `USER_DELETE`, `USER_STATUS_CHANGE`
- Role management: `ROLE_CREATE`, `ROLE_UPDATE`, `ROLE_DELETE`, `ROLE_ASSIGN`, `ROLE_REVOKE`, `USER_ROLE_UPDATE`, `USER_ROLE_REMOVE`
- Permission: `PERMISSION_GRANT`, `PERMISSION_REVOKE`
- Session: `SESSION_CREATE`, `SESSION_REVOKE`, `SESSION_EXPIRE`
- System: `SYSTEM_START`, `SYSTEM_STOP`, `CONFIG_CHANGE`, `SECURITY_SETTINGS_UPDATE`

### 4.9 SecuritySettings (apps.users.models.SecuritySettings)

Singleton model (one row) configurable by admins at runtime:

| Setting | Default | Range |
|---|---|---|
| `account_lockout_max_attempts` | 3 | 1–10 |
| `account_lockout_duration_minutes` | 30 | 1–1440 |
| `account_lockout_admin_alert_threshold` | 5 | 1+ |
| `account_lockout_admin_alert_window_minutes` | 10 | 1+ |
| `password_expiration_days` | 90 | 1–365 |
| `password_warning_days_before_expiration` | 7 | 1–30 |
| `password_reuse_history_count` | 5 | 1–20 |
| `password_min_uppercase` | 1 | 0–10 |
| `password_min_lowercase` | 1 | 0–10 |
| `password_min_digits` | 1 | 0–10 |
| `password_min_special` | 1 | 0–10 |
| `password_check_username` | True | |
| `password_check_user_info` | True | |
| `password_check_sequential` | True | |
| `password_check_repeated` | True | |
| `password_check_common` | True | |
| `session_idle_timeout_minutes` | 30 | 5–480 |
| `session_absolute_timeout_minutes` | 480 | 30–1440 |
| `session_cleanup_interval_minutes` | 5 | 1–60 |
| `session_extend_on_activity` | True | |
| `session_retention_hours` | 24 | 1–168 |

---

## 5. Complete API Surface

### 5.1 Authentication Endpoints

All routes are under `/api/v1/` and duplicated at `/api/v1/iam/` for direct access.

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/auth/login/` | POST | Public | MFA-aware login (two-step if MFA enabled) |
| `/auth/refresh/` | POST | Public | Refresh JWT access token |
| `/auth/logout/` | POST | Bearer | Logout and revoke session |
| `/auth/register/` | POST | Admin | Register a new user account |
| `/auth/verify-email/` | POST | Public | Verify email with token |
| `/auth/forgot-password/` | POST | Public | Request password reset email |
| `/auth/reset-password/` | POST | Public | Complete password reset with token |
| `/auth/reset-expired-password/` | POST | Public | Reset an expired password |
| `/introspect/` | GET | Bearer | Get current user info + roles + permissions |
| `/health/` | GET | Public | Health check |

### 5.2 User Management Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/users/` | GET | Admin | List all users (paginated, searchable) |
| `/users/` | POST | Admin | Create new user |
| `/users/<uuid>/` | GET | Admin | Get user details |
| `/users/<uuid>/` | PUT/PATCH | Admin | Update user |
| `/users/<uuid>/` | DELETE | Admin | Delete user |
| `/profile/` | GET | Bearer | Get own profile |
| `/profile/update/` | PUT/PATCH | Bearer | Update own profile |
| `/profile/signature/save/` | POST | Bearer | Upload signature image |
| `/profile/signature/remove/` | DELETE | Bearer | Remove signature |
| `/profile/picture/upload/` | POST | Bearer | Upload profile picture |
| `/profile/picture/remove/` | DELETE | Bearer | Remove profile picture |
| `/profile/permissions/` | GET | Bearer | Get own permissions |
| `/profile/all-permissions/` | GET | Bearer | Get all available permissions |
| `/profile/change-password/` | POST | Bearer | Change own password |
| `/users/<uuid>/permissions/` | GET | Admin | Get permissions for a specific user |

### 5.3 User Lookup Endpoints (For Other Services)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/users/lookup/` | GET | Bearer | Paginated user search (lightweight) |
| `/users/lookup/email/<email>/` | GET | Bearer | Lookup by email |
| `/users/lookup/id/<user_id>/` | GET | Bearer | Lookup by UUID |

### 5.4 Account Security Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/users/<uuid>/unlock/` | POST | Admin | Manually unlock a locked account |
| `/users/<uuid>/lockout-status/` | GET | Admin | Get lockout status for a user |
| `/profile/lockout-status/` | GET | Bearer | Get own lockout status |
| `/users/locked/` | GET | Admin | List all currently locked accounts |
| `/profile/password-status/` | GET | Bearer | Get own password expiration status |
| `/users/<uuid>/force-password-change/` | POST | Admin | Force a user to change password |
| `/security-settings/` | GET/PUT | Admin | Get/update security settings |
| `/security-settings/public/` | GET | Public | Get public security config (password rules) |
| `/security-settings/password-hashing-info/` | GET | Admin | Get password hashing algorithm info |
| `/security-settings/test-smtp/` | POST | Admin | Test SMTP connection |

### 5.5 Service-to-Service Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/users/<uuid>/activate-for-client-service/` | POST | X-Service-Token | Activate user after external email verification |
| `/rbac/users/<uuid>/assign-external-roles/` | POST | Service auth | Assign external-user roles |

### 5.6 Role Management Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/roles/` | GET | Bearer | List all roles |
| `/roles/` | POST | Admin | Create role |
| `/roles/<uuid>/` | GET | Bearer | Get role details |
| `/roles/<uuid>/` | PUT/PATCH | Admin | Update role |
| `/roles/<uuid>/` | DELETE | Admin | Delete role |
| `/users/<int>/roles/<int>/assign/` | POST | Admin | Assign role to user (legacy) |
| `/users/<int>/roles/<int>/remove/` | POST | Admin | Remove role from user (legacy) |

### 5.7 RBAC Endpoints (Unified System)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/rbac/user-roles/` | GET/POST | Admin | List/Create user-role assignments |
| `/rbac/user-roles/<uuid>/` | GET/PUT/DELETE | Admin | Manage specific assignment |
| `/rbac/users/<uuid>/roles/` | GET | Admin | Get all roles for a user |
| `/rbac/user-roles/assign/` | POST | Admin | Assign role to user |
| `/rbac/user-roles/remove/` | POST | Admin | Remove role from user |
| `/rbac/user-roles/assign-by-attributes/` | POST | Admin | Bulk-assign roles by user attributes |
| `/rbac/user-roles/revoke-by-attributes/` | POST | Admin | Bulk-revoke roles by user attributes |
| `/rbac/role-permissions/` | GET/POST | Admin | List/Create role-permission links |
| `/rbac/role-permissions/<uuid>/` | GET/PUT/DELETE | Admin | Manage specific link |
| `/rbac/role-permissions/stats/` | GET | Admin | Permission statistics |
| `/rbac/role-permissions/bulk-assign/` | POST | Admin | Bulk-assign permissions to role |
| `/rbac/role-permissions/bulk-remove/` | POST | Admin | Bulk-remove permissions from role |
| `/rbac/role-permissions/matrix-data/` | GET | Admin | Permission matrix for admin UI |
| `/rbac/roles/<uuid>/permissions/` | GET | Admin | Get all permissions for a role |
| `/rbac/permissions/` | GET | Admin | List all permissions (Django + service) |
| `/rbac/permissions/filter-options/` | GET | Admin | Get filter options for permission list |

### 5.8 Session Management Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/sessions/` | GET | Bearer | List user's sessions |
| `/sessions/<int>/` | GET | Bearer | Get session details |
| `/sessions/<int>/terminate/` | POST | Bearer | Terminate a specific session |
| `/sessions/current/status/` | GET | Bearer | Check current session status |
| `/sessions/extend/` | POST | Bearer | Extend current session |
| `/sessions/activity/` | POST | Bearer | Report session activity (resets idle timer) |

### 5.9 MFA Endpoints (under /mfa/)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/mfa/enroll/totp/` | POST | Bearer | Start TOTP enrollment (returns QR) |
| `/mfa/verify/totp/` | POST | Bearer | Verify TOTP enrollment |
| `/mfa/disable/` | POST | Bearer | Disable MFA |
| `/mfa/status/` | GET | Bearer | Get MFA status |
| `/mfa/email-otp/send/` | POST | Bearer | Send email OTP code |
| `/mfa/email-otp/verify/` | POST | Bearer | Verify email OTP code |
| `/mfa/backup-codes/` | GET/POST | Bearer | List/create backup codes |
| `/mfa/backup-codes/generate/` | POST | Bearer | Generate new backup codes |
| `/mfa/backup-codes/verify/` | POST | Bearer | Verify a backup code |
| `/mfa/devices/` | GET | Bearer | List MFA devices |
| `/mfa/devices/totp/` | POST | Bearer | Create TOTP device |
| `/mfa/devices/totp/<id>/` | PUT | Bearer | Update TOTP device |
| `/mfa/devices/totp/<id>/delete/` | DELETE | Bearer | Delete TOTP device |
| `/mfa/devices/static/` | POST | Bearer | Create static (backup) device |
| `/mfa/admin/devices/` | GET | Admin | List all MFA devices (admin) |
| `/mfa/admin/backup-codes/` | GET | Admin | List all backup codes (admin) |

### 5.10 Audit Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/audit-logs/` | GET | Admin | List all audit logs (paginated) |
| `/audit-logs/<int>/` | GET | Admin | Get audit log detail |
| `/users/<int>/audit-logs/` | GET | Admin | Get audit logs for a specific user |
| `/objects/<type>/<int>/audit-logs/` | GET | Admin | Get audit logs for a specific resource |

### 5.11 Dashboard Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/dashboard/stats/` | GET | Bearer | Dashboard statistics |
| `/dashboard/charts/` | GET | Bearer | Dashboard chart data |
| `/dashboard/recent-activity/` | GET | Bearer | Recent activity feed |

---

## 6. Authentication Flow in Detail

### 6.1 Standard Login (No MFA)

```
Client                          IAM Service
  |                                  |
  |  POST /auth/login/               |
  |  { email, password }             |
  |--------------------------------->|
  |                                  |  1. Lookup user by email or username
  |                                  |  2. Check account lockout (auto-unlock if expired)
  |                                  |  3. Check if user has active roles
  |                                  |  4. Check password expiration
  |                                  |  5. Verify password
  |                                  |  6. If MFA disabled → skip to step 9
  |                                  |  7. If MFA enabled → return mfa_required=true
  |                                  |  8. (see MFA flow below)
  |                                  |  9. Reset failed login attempts
  |                                  | 10. Terminate existing sessions (one-per-user)
  |                                  | 11. Generate EnhancedRefreshToken + EnhancedAccessToken
  |                                  | 12. Resolve permissions via UnifiedPermissionResolutionService
  |                                  | 13. Embed permissions_flat + services in JWT
  |                                  | 14. Create UserSession (store JTI + refresh token)
  |                                  | 15. Initialize session timeouts
  |                                  | 16. Log audit trail (LOGIN action)
  |  { access, refresh, user }       |
  |<---------------------------------|
```

### 6.2 Login With MFA (Two-Step)

```
Client                         IAM Service
  |                                 |
  |  POST /auth/login/              |
  |  { email, password }            |
  |-------------------------------->|
  |                                 |  1-5. Same as standard flow
  |                                 |  6. MFA enabled → generate temp token
  |  { mfa_required: true,          |
  |    mfa_token: "<temp>",         |
  |    supported_methods: ["totp",  |
  |      "email", "backup"] }       |
  |<--------------------------------|
  |                                 |
  |  POST /auth/login/              |
  |  { mfa_token, mfa_code,         |
  |    method: "totp" }             |
  |-------------------------------->|
  |                                 |  7. Decode temp token → get user
  |                                 |  8. Verify MFA code by method:
  |                                 |     - totp: pyotp.TOTP.verify(code, valid_window=2)
  |                                 |     - email: EmailOTPService.verify_otp()
  |                                 |     - backup: lookup unused MFABackupCode
  |                                 |  9-16. Same as standard flow
  |  { access, refresh, user }      |
  |<--------------------------------|
```

### 6.3 Login Failure Scenarios

| Condition | Status | Code |
|---|---|---|
| User not found | 401 | — |
| Account locked | 403 | `ACCOUNT_LOCKED` |
| No active roles assigned | 403 | `NO_ROLES_ASSIGNED` |
| Password expired | 403 | `PASSWORD_EXPIRED` |
| Wrong password | 401 | — |
| Wrong password → threshold hit → lock | 400 | Account locked message |
| Invalid MFA code | 401 | — |
| Invalid/expired MFA temp token | 401 | — |

### 6.4 Token Refresh

```
Client                         IAM Service
  |                                 |
  |  POST /auth/refresh/            |
  |  { refresh: "<refresh_token>" } |
  |-------------------------------->|
  |                                 |  1. Validate refresh token signature + expiry
  |                                 |  2. Generate new access token (with EnhancedAccessToken)
  |                                 |  3. Lookup UserSession by refresh_token
  |                                 |  4. Update session's access_jti to new token's JTI
  |                                 |  5. If token rotation enabled, update refresh_token too
  |  { access, [refresh] }          |
  |<--------------------------------|
```

---

## 7. JWT Token Architecture

### 7.1 Token Generation Pipeline

```
User logs in
    ↓
EnhancedRefreshToken.for_user(user)
    ↓
UnifiedPermissionResolutionService.get_user_permissions(user)
    ├── Query all active UserRole → Role → RolePermission
    ├── Collect Django permissions (codenames)
    ├── Collect ServicePermission codes (grouped by service)
    ├── Check direct UserServicePermission (if model exists)
    ├── If superuser: permissions_flat = ["*"], services = all
    └── Return: { permissions: {}, permissions_flat: [...], services: [...] }
    ↓
Embed in token payload
    ↓
Sign with HS256 + JWT_SECRET_KEY
```

### 7.2 Token Size Optimization

The original design embedded a nested `permissions` dict (by service) in the JWT. This caused HTTP 431 errors when tokens grew too large. The current design:

1. `permissions` → always `{}` (empty dict) — kept for backward compatibility
2. `permissions_flat` → flat list of all permission codes, sorted
3. Superusers → `permissions_flat: ["*"]` instead of listing all permissions
4. `services` → list of service names the user has access to

### 7.3 Shared Secret Contract

**Every FIMS service MUST use the same values:**
```python
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')  # Same value across all services
JWT_ALGORITHM = 'HS256'                       # Must be HS256
```

If these don't match, tokens issued by IAM will fail validation in other services.

---

## 8. Permission Registration System (Kafka)

### 8.1 Architecture Overview

```
┌────────────────────┐     Kafka Topic:                  ┌─────────────────┐
│ document-records   │  service.permission.registry       │                 │
│ PermissionPublisher│─────────────────────────────────-->│  IAM Service    │
│                    │                                    │  UnifiedPerm    │
├────────────────────┤                                    │  Consumer       │
│ client-service     │─────────────────────────────────-->│                 │
│ PermissionPublisher│                                    │  Creates/Updates│
├────────────────────┤                                    │  - Service      │
│ corporate-service  │─────────────────────────────────-->│  - ServicePerm  │
│ PermissionPublisher│                                    │  - Role (opt)   │
├────────────────────┤                                    │                 │
│ work-orchestration │─────────────────────────────────-->│                 │
│ PermissionPublisher│                                    └─────────────────┘
└────────────────────┘
```

### 8.2 Consumer Processing

IAM's `UnifiedPermissionConsumer` (Celery task, runs every 60 seconds):

1. Polls `service.permission.registry` topic
2. For each message, checks `event_type`:
   - `service_permission_registration` → processes permissions
   - `service_role_definitions` → processes role templates
3. Within a database transaction:
   - Upserts `Service` record by name
   - For each permission, upserts `ServicePermission` by (service, permission_code)
   - Deactivates `ServicePermission` entries not in current registration
4. Consumer group: `iam-unified-permission-consumer-group`
5. Auto offset reset: `earliest` (will process all historical messages on first run)
6. Retry logic: 10 retries with 30-second delays on Kafka connection failure

### 8.3 Permission Lifecycle

```
Service starts up
    ↓
Loads config/permissions/<service>.json
    ↓
PermissionPublisher.publish_permissions()
    ↓
Kafka topic: service.permission.registry
    ↓
(within 60 seconds)
    ↓
IAM Celery task: consume_permission_registrations
    ↓
UnifiedPermissionConsumer processes message
    ↓
Service + ServicePermission records created/updated in IAM DB
    ↓
Admin assigns ServicePermissions to Roles via RBAC UI
    ↓
Next user login: EnhancedAccessToken includes new permissions in JWT
```

---

## 9. Cross-Service Dependencies & Collaboration

### 9.1 IAM → Work Orchestration Service

| Interaction | Type | Details |
|---|---|---|
| Send notification emails | Kafka | `NotificationPublisher` → priority topics |
| Send email directly (fallback) | REST | `WorkOrchestrationClient.send_email()` → `/api/v1/workflow/notifications/email/send/` |

**When IAM sends notifications:**
- Password reset emails
- Email verification emails
- Password expiration warning emails
- Account lockout admin alerts
- MFA email OTP codes

### 9.2 IAM ← All Services (Kafka)

| Interaction | Type | Details |
|---|---|---|
| Permission registration | Kafka consumer | `service.permission.registry` topic |
| Role definition registration | Kafka consumer | Same topic, different `event_type` |

### 9.3 IAM ← Client Service (REST S2S)

| Interaction | Endpoint | Details |
|---|---|---|
| Activate user after verification | `POST /users/<id>/activate-for-client-service/` | Client service calls IAM with X-Service-Token |
| Assign external roles | `POST /rbac/users/<id>/assign-external-roles/` | Client service calls IAM after entity verification |

### 9.4 IAM ← Document Records Service (REST)

| Interaction | Endpoint | Details |
|---|---|---|
| User lookup (cached) | `GET /users/lookup/id/<id>/` | doc-records uses IAMClient with 5-min Redis cache |

### 9.5 IAM → All Services (Kafka Events)

| Interaction | Topic | Details |
|---|---|---|
| User profile changes | `fims.iam.user.updated` | Published via `KafkaMessagingService` |
| Audit events | `audit.events` | Published via `KafkaMessagingService` |

### 9.6 Dependency Graph

```
                    ┌──────────────────────────────────────┐
                    │          iam-service                  │
                    │                                      │
  Permission Reg    │  ┌─────────────┐  ┌───────────────┐  │   Notifications
  (Kafka consumer)  │  │ Unified     │  │ Notification  │──│──── Kafka ────> work-orchestration
  <── Kafka ────────│──│ Permission  │  │ Publisher     │  │
                    │  │ Consumer    │  └───────────────┘  │
  All services ─────│──│             │                     │
  produce to        │  └─────────────┘                     │
  service.permission│                                      │
  .registry         │  ┌─────────────┐  ┌───────────────┐  │   User events
                    │  │ Enhanced    │  │ Kafka         │──│──── Kafka ────> document-records
                    │  │ JWT Token   │  │ Messaging     │  │                 (user profile cache)
                    │  │ Generator   │  │ Service       │  │
                    │  └─────────────┘  └───────────────┘  │
                    │                                      │
  client-service ───│──→ activate-for-client-service       │
  (REST S2S)        │──→ assign-external-roles             │
                    │                                      │
  All services      │  (JWT validation is LOCAL using      │
  validate JWTs     │   shared secret — no IAM call)       │
  independently     │                                      │
                    └──────────────────────────────────────┘
```

---

## 10. How Other Services Consume IAM

### 10.1 JWT Validation Middleware (The Primary Integration)

Every non-IAM service implements a `JWTPermissionMiddleware`. This middleware decodes and validates the JWT token locally, with no HTTP call to IAM.

**Example from corporate-service (`apps/core/permission_middleware.py`):**

```python
class JWTPermissionMiddleware(MiddlewareMixin):
    skip_paths = ['/health/', '/admin/', '/static/', '/media/']

    def process_request(self, request):
        # 1. Skip public paths
        if any(request.path.startswith(p) for p in self.skip_paths):
            return None

        # 2. Extract Bearer token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authorization header missing'}, status=401)
        token = auth_header.split(' ')[1]

        # 3. Decode JWT locally
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,      # Must match IAM's SECRET
            algorithms=[settings.JWT_ALGORITHM],  # HS256
            options={'verify_exp': True},
        )

        # 4. Extract fields from payload
        request.user_id = payload.get('user_id')
        request.user_email = payload.get('email')
        request.is_superuser = payload.get('is_superuser', False)
        request.user_permissions_flat = payload.get('permissions_flat', [])
        request.user_services = payload.get('services', [])

        # 5. Verify service access
        service_aliases = {'corporate-service', 'corporate'}
        has_service = any(s in service_aliases for s in request.user_services)
        if not request.is_superuser and not has_service:
            return JsonResponse({'error': 'Access denied'}, status=403)

        # 6. Create lightweight user object
        class AuthenticatedUser:
            def __init__(self, user_id, email, is_superuser, is_staff):
                self.id = user_id
                self.pk = user_id
                self.email = email
                self.is_superuser = is_superuser
                self.is_staff = is_staff
                self.is_active = True
                self.is_authenticated = True

        request.user = AuthenticatedUser(...)
```

**Key: No Django model queried. No IAM HTTP call. Pure JWT decode.**

### 10.2 How Services Check Permissions

After the middleware runs, views check permissions using `request.user_permissions_flat`:

```python
# Example: Check if user has document.approve permission
if 'document.approve' not in request.user_permissions_flat and not request.is_superuser:
    return Response({'error': 'Permission denied'}, status=403)
```

Or via DRF permission classes:
```python
class HasPermission(BasePermission):
    def __init__(self, required_permission):
        self.required_permission = required_permission

    def has_permission(self, request, view):
        if request.is_superuser:
            return True
        if '*' in getattr(request, 'user_permissions_flat', []):
            return True
        return self.required_permission in getattr(request, 'user_permissions_flat', [])
```

### 10.3 How the Document Records Service Resolves User Names

```python
# From document-records-service — IAMClient with caching
class IAMClient:
    def __init__(self):
        self.base_url = settings.IAM_SERVICE_URL
        self.cache_ttl = 300  # 5 minutes

    def get_user(self, user_id):
        cache_key = f'iam_user_{user_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        response = requests.get(
            f'{self.base_url}/api/v1/users/lookup/id/{user_id}/',
            headers={'Authorization': f'Bearer {self._get_service_token()}'}
        )
        user_data = response.json().get('user')
        cache.set(cache_key, user_data, self.cache_ttl)
        return user_data
```

### 10.4 How the Client Service Activates Users

After a client completes email verification:
```python
# client-service calls IAM
response = requests.post(
    f'{settings.IAM_SERVICE_URL}/api/v1/users/{user_id}/activate-for-client-service/',
    headers={
        'X-Service-Token': settings.SERVICE_TO_SERVICE_TOKEN,
        'Content-Type': 'application/json'
    }
)
```

### 10.5 How Services Register Permissions

Each service publishes on startup or via periodic Celery task:
```python
# From any service — PermissionPublisher
class PermissionPublisher:
    def publish_permissions(self):
        with open('config/permissions/my-service.json') as f:
            config = json.load(f)

        event = {
            'event_type': 'service_permission_registration',
            'source_service': config['service']['name'],
            'data': {
                'service_name': config['service']['name'],
                'service_version': config['service']['version'],
                'service_description': config['service']['description'],
                'permissions': config['permissions']
            }
        }

        producer.send('service.permission.registry', value=event)
```

---

## 11. Background Tasks (Celery)

IAM runs a Celery worker and Celery Beat. All tasks:

| Task | Schedule | Function |
|---|---|---|
| `consume_permission_registrations` | Every 60 seconds | Poll Kafka for permission registrations from services |
| `unlock_expired_accounts` | Every 5 minutes | Auto-unlock accounts whose lockout duration has expired |
| `check_password_expirations` | Daily at 9:00 AM | Send warning emails for passwords expiring within the warning period |
| `enforce_password_expiration` | Every 6 hours | Identify and flag users with expired passwords |
| `cleanup_expired_sessions` | Every 5 minutes | Mark sessions as expired if idle/absolute timeout has passed |
| `delete_old_inactive_sessions` | Every hour | Delete expired/revoked sessions older than retention period |

---

## 12. Notification Publishing

IAM uses a `NotificationPublisher` (Kafka-based) for sending emails and notifications. It never calls `django.core.mail.send_mail` directly.

**Publisher flow:**
```
IAM Code
    ↓
NotificationPublisher.send_notification(
    template_code='iam.password.reset',
    recipients={'email': ['user@example.com']},
    context={'user': {...}, 'reset_url': '...'},
    priority='high'
)
    ↓
Kafka topic: notifications-high
    ↓
work-orchestration-service consumes
    ↓
Renders template + sends email via configured SMTP
```

**Templates IAM publishes (registered via Kafka `notification-templates` topic):**
- `iam.user.registration` — welcome email after account creation
- `iam.password.reset` — password reset link
- `iam.password.expiration.warning` — password expiring soon
- `iam.email.verification` — email verification link
- `iam.account.lockout` — account locked notification
- `iam.account.lockout.admin` — admin alert for lockout patterns
- `iam.mfa.email.otp` — email OTP code for MFA

IAM also has a `WorkOrchestrationClient` as a REST-based fallback for direct email sending (used if Kafka is unavailable).

---

## 13. Integration Guide for New Services

### 13.1 Step 1: Share the JWT Secret

Add to your service's `.env` file:
```
JWT_SECRET_KEY=<same value as IAM>
JWT_ALGORITHM=HS256
```

And in `settings.py`:
```python
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
```

### 13.2 Step 2: Implement JWT Middleware

Copy and adapt `JWTPermissionMiddleware` from any existing service. At minimum:

```python
import jwt
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

class JWTPermissionMiddleware(MiddlewareMixin):
    skip_paths = ['/health/', '/admin/', '/static/', '/media/']

    def process_request(self, request):
        # Skip public paths
        if any(request.path.startswith(p) for p in self.skip_paths):
            return None

        # Check for service-to-service token
        service_token = request.META.get('HTTP_X_SERVICE_TOKEN')
        if service_token == settings.SERVICE_TO_SERVICE_TOKEN:
            request.user = ServiceUser()
            request.is_superuser = True
            request.user_permissions_flat = ['*']
            return None

        # Extract and validate JWT
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authorization header missing'}, status=401)

        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={'verify_exp': True}
            )
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)

        # Extract claims
        request.user_id = payload.get('user_id')
        request.user_email = payload.get('email')
        request.is_superuser = payload.get('is_superuser', False)
        request.user_permissions_flat = payload.get('permissions_flat', [])
        request.user_services = payload.get('services', [])

        # Verify service access
        service_aliases = {'my-service', 'my_service'}
        has_access = (
            request.is_superuser or
            '*' in (request.user_permissions_flat or []) or
            any(s in service_aliases for s in (request.user_services or []))
        )
        if not has_access:
            return JsonResponse({'error': 'No access to this service'}, status=403)

        # Create lightweight user object
        class AuthenticatedUser:
            def __init__(self, uid, email, is_superuser, is_staff):
                self.id = uid
                self.pk = uid
                self.email = email
                self.is_superuser = is_superuser
                self.is_staff = is_staff
                self.is_active = True
                self.is_authenticated = True
            def __str__(self):
                return self.email or str(self.id)

        request.user = AuthenticatedUser(
            request.user_id, request.user_email,
            request.is_superuser, payload.get('is_staff', False)
        )
        return None
```

### 13.3 Step 3: Implement DRF Authentication Bridge

```python
from rest_framework.authentication import BaseAuthentication

class JWTMiddlewareAuthentication(BaseAuthentication):
    """Bridges middleware-set user to DRF authentication."""
    def authenticate(self, request):
        django_request = getattr(request, '_request', request)
        user = getattr(django_request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            if type(user).__name__ in ('AuthenticatedUser', 'ServiceUser'):
                return (user, None)
        return None
```

### 13.4 Step 4: Define and Register Your Permissions

Create `config/permissions/my-service.json`:
```json
{
  "service": {
    "name": "my-service",
    "version": "1.0.0",
    "description": "My new FIMS service"
  },
  "permissions": [
    {
      "permission_code": "my.entity.create",
      "name": "Create Entity",
      "description": "Can create entities",
      "resource_type": "entity",
      "action": "create",
      "category": "entity_management"
    },
    {
      "permission_code": "my.entity.read",
      "name": "Read Entity",
      "description": "Can read entities",
      "resource_type": "entity",
      "action": "read",
      "category": "entity_management"
    }
  ]
}
```

Implement a publisher that sends this to Kafka on startup. IAM's Celery task will pick it up within 60 seconds.

### 13.5 Step 5: Reference Users by UUID Only

In your models, reference IAM users with a plain `UUIDField`:
```python
class MyModel(models.Model):
    created_by = models.UUIDField(null=True, blank=True)
    assigned_to = models.UUIDField(null=True, blank=True)
```

**Never use ForeignKey to IAM's User model.** The databases are isolated.

### 13.6 Step 6: Use IAM Lookup Endpoints for Display Names

If you need to display user names:
```python
# Call IAM's lookup endpoint with caching
def get_user_display_name(user_id):
    cache_key = f'iam_user_{user_id}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    response = requests.get(
        f'{settings.IAM_SERVICE_URL}/api/v1/users/lookup/id/{user_id}/',
        headers={'Authorization': f'Bearer {request_token}'},
        timeout=5
    )
    if response.status_code == 200:
        user = response.json().get('user', {})
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        cache.set(cache_key, name, 300)  # 5 min cache
        return name
    return str(user_id)
```

### 13.7 Step 7: Add Your Service to IAM's Service Access Check

When IAM assigns roles with your service's permissions to users, your service name will appear in their `services` list in the JWT. Make sure your middleware checks for your service name in `request.user_services`.

---

## 14. Architectural Boundaries — What Not To Do

### Never Create a User Table in Your Service
IAM owns all user identity. If you need user data, call IAM's lookup endpoints and cache the results.

### Never Issue JWT Tokens
Only IAM generates and signs JWTs. All other services only validate them.

### Never Build a Login Endpoint
Authentication happens exclusively through IAM's `/auth/login/` endpoint. The frontend always talks to IAM for auth.

### Never Implement Password Reset
IAM handles the entire password reset flow: token generation, email sending (via Kafka to work-orchestration), and password update.

### Never Store or Hash Passwords
IAM is the only service that touches password fields. Django's `AbstractUser.set_password()` and `check_password()` are only called within IAM.

### Never Duplicate Permission Definitions
Define your permissions in `config/permissions/`, publish them to Kafka. IAM stores them. Role admins assign them. The JWT carries them.

### Never Call IAM for Every Request
JWT validation is local. The token is self-contained. Only call IAM for user profile lookups (and cache those).

### Never Trust Only `permissions` (Empty Dict)
The `permissions` field in the JWT is intentionally empty to reduce token size. Always use `permissions_flat` for permission checks.

### Never Assume `services` List Is Complete
Superusers may have `services: ["*"]`. Always check for the wildcard pattern in addition to your service name.

### Never Bypass the Service Access Check
If a user's JWT doesn't include your service in the `services` list and they're not a superuser, deny access. This is how IAM controls which users can access which services.

---

*This document was derived from direct code analysis of the IAM service codebase. All endpoints, models, flows, and integration patterns described here are based on actual implementation evidence.*
