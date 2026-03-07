# IAM Service Integration Guide

**Status:** Authoritative developer reference  
**Service port:** 8000 (default)  
**API base (with gateway prefix):** `/api/v1/iam/`  
**API base (without gateway prefix):** `/api/v1/`  
**Docker container name:** `fims-iam-service`

---

## Table of Contents

1. [What IAM Owns](#1-what-iam-owns)
2. [Architecture Position](#2-architecture-position)
3. [Authentication Flow — Step-by-Step](#3-authentication-flow--step-by-step)
4. [JWT Token Structure](#4-jwt-token-structure)
5. [Session Management](#5-session-management)
6. [User Endpoints](#6-user-endpoints)
7. [Profile & Signature Endpoints](#7-profile--signature-endpoints)
8. [Account Security Endpoints](#8-account-security-endpoints)
9. [Roles Endpoints](#9-roles-endpoints)
10. [RBAC Endpoints](#10-rbac-endpoints)
11. [Permission Registration via Kafka](#11-permission-registration-via-kafka)
12. [Consuming Services — JWT Middleware Pattern](#12-consuming-services--jwt-middleware-pattern)
13. [Consuming Services — Permission Classes Pattern](#13-consuming-services--permission-classes-pattern)
14. [MFA Endpoints](#14-mfa-endpoints)
15. [Session Endpoints](#15-session-endpoints)
16. [Audit Log Endpoints](#16-audit-log-endpoints)
17. [Token Introspection](#17-token-introspection)
18. [Kafka Topics IAM Publishes](#18-kafka-topics-iam-publishes)
19. [Kafka Topics IAM Consumes](#19-kafka-topics-iam-consumes)
20. [Service-to-Service Authentication](#20-service-to-service-authentication)
21. [User Lookup for Other Services](#21-user-lookup-for-other-services)
22. [Media Serving — Profiles & Signatures](#22-media-serving--profiles--signatures)
23. [GRC-Specific Integration Patterns](#23-grc-specific-integration-patterns)
24. [Strict Rules — What Other Services Must Never Do](#24-strict-rules--what-other-services-must-never-do)
25. [Complete API Quick Reference](#25-complete-api-quick-reference)

---

## 1. What IAM Owns

IAM is the **sole authority** for all identity, authentication, and permission concerns across FIMS. **No other service may store user passwords, issue JWTs, or decide whether a user has a given permission code.**

| Domain | IAM owns it | Other services |
|---|---|---|
| User accounts, passwords, login | ✅ | Must call IAM |
| JWT issuance & refresh | ✅ | Must use IAM's tokens |
| Session lifecycle | ✅ | Read from JWT claims |
| Role definitions | ✅ | Register via Kafka |
| Permission code registry | ✅ | Register via Kafka |
| Permission enforcement | Codes live in JWT | Each service enforces locally |
| MFA devices/backup codes | ✅ | Transparently handled at login |
| Account lockout logic | ✅ | Services read error response |
| Audit log of IAM events | ✅ | Services write their own |

---

## 2. Architecture Position

```
Browser/App
    │
    ▼
api-gateway (nginx, port 443/80)
    │  routes /api/v1/iam/*  ──────────────────────────────────────────▶ IAM service:8000
    │  routes /api/v1/grc/*  ──────────────────────────────────────────▶ grc-service:8001
    │  routes /api/v1/drs/*  ──────────────────────────────────────────▶ drs:8002
    │  routes /api/v1/wo/*   ──────────────────────────────────────────▶ WO:8004
    │
    │   JWT (with permissions_flat in payload)
    │   ─────────────────────────────────────▶ each downstream service decodes locally
    │
Kafka bus
    │   topic: service.permission.registry
    │   ◀── grc-service, drs, WO register their permissions
    │   ──▶ IAM stores in DB and embeds in next token
```

**Access pattern:**
- Front-end → IAM: login, logout, token refresh, MFA
- Front-end → other services: all other calls (carry the Bearer JWT)
- Other services → IAM: user lookup, activate-for-client-service, health check only

---

## 3. Authentication Flow — Step-by-Step

### 3.1 Standard Login (No MFA)

```
POST /api/v1/iam/auth/login/
Content-Type: application/json

{
  "email": "user@fcc.go.tz",
  "password": "secret"
}
```

**Response (200 OK):**
```json
{
  "access": "<jwt-access-token>",
  "refresh": "<jwt-refresh-token>",
  "session_id": "uuid",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@fcc.go.tz",
    "first_name": "John",
    "last_name": "Doe",
    "is_staff": false,
    "is_superuser": false
  }
}
```

Username login is also supported (D-010): send `"email": "johndoe"` (any value without `@` is treated as username).

**Rate limit:** 10 POST /min per IP address.

### 3.2 Login with MFA Enabled (Two-Step)

**Step 1 — submit credentials:**
```
POST /api/v1/iam/auth/login/
{
  "email": "user@fcc.go.tz",
  "password": "secret"
}
```

**Response when MFA is required:**
```json
{
  "mfa_required": true,
  "mfa_token": "<temporary-token>",
  "message": "MFA verification required"
}
```

**Step 2 — submit MFA code:**
```
POST /api/v1/iam/auth/login/
{
  "mfa_token": "<temporary-token-from-step1>",
  "mfa_code": "123456",
  "method": "totp"
}
```

`method` values: `"totp"` (TOTP device) or `"backup"` (backup code).

**Response (success):** same as standard login with `access`, `refresh`, `session_id`.

### 3.3 Account Lockout Error

After N failed password attempts (configurable), IAM returns:
```json
{
  "error": "Your account has been temporarily locked for security reasons.",
  "message": "Account locked due to multiple failed login attempts. Please try again in 30 minutes.",
  "locked_until": "2025-01-01T12:00:00Z",
  "unlocks_in": "30 minutes",
  "failed_attempts": 5,
  "max_attempts": 5
}
```
HTTP status: **400 Bad Request**

### 3.4 Token Refresh

```
POST /api/v1/iam/auth/refresh/
Content-Type: application/json

{
  "refresh": "<refresh-token>"
}
```

**Response (200 OK):**
```json
{
  "access": "<new-access-token>",
  "refresh": "<new-refresh-token>"
}
```

IAM rotates the refresh token and updates the session's `access_jti` on every refresh. A stale refresh token is rejected.

### 3.5 Logout

```
POST /api/v1/iam/auth/logout/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "refresh": "<refresh-token>"
}
```

IAM revokes the session (sets status → `revoked`). Subsequent requests with the same JWT are rejected with `SESSION_REVOKED`.

### 3.6 Register

```
POST /api/v1/iam/auth/register/
{
  "email": "user@fcc.go.tz",
  "username": "jdoe",
  "password": "StrongPass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

Rate limit: 5 POST/min per IP. New user receives an email verification link.

### 3.7 Password Reset Flow

```
POST /api/v1/iam/auth/forgot-password/    { "email": "..." }
POST /api/v1/iam/auth/reset-password/     { "token": "...", "password": "..." }
POST /api/v1/iam/auth/reset-expired-password/   { "old_password": "...", "new_password": "..." }
```

### 3.8 Email Verification

```
POST /api/v1/iam/auth/verify-email/
{
  "token": "<email-verification-token>"
}
```

---

## 4. JWT Token Structure

IAM generates **enhanced JWT tokens** (via `EnhancedAccessToken`) that embed the user's full permission payload. Other services decode these locally — **no IAM round-trip needed per request**.

### Access Token Payload

```json
{
  "token_type": "access",
  "jti": "unique-token-id",
  "exp": 1700000000,
  "iat": 1699996400,
  "user_id": "uuid-string",
  "email": "user@fcc.go.tz",
  "is_staff": false,
  "is_superuser": false,
  "permissions": {},
  "permissions_flat": [
    "grc:audit_universe:view",
    "grc:audit_universe:manage",
    "document:document:view",
    "document:document:upload",
    "wo:workflow:view"
  ],
  "services": ["grc-service", "document-records-service", "work-orchestration-service"]
}
```

### Key Claims

| Claim | Type | Description |
|---|---|---|
| `user_id` | string (UUID) | The user's UUID — use this as the foreign key in other services |
| `email` | string | User's email address |
| `is_staff` | bool | Django staff flag |
| `is_superuser` | bool | Django superuser flag |
| `permissions` | object | Always `{}` (kept empty to reduce token size) |
| `permissions_flat` | array | All permission codes the user holds across all services; `["*"]` for superusers |
| `services` | array | Names of services the user has at least one permission in |
| `jti` | string | Unique token ID — used to validate session revocation |
| `exp` | int | Expiry as Unix timestamp |

### Superuser Special Case

When `is_superuser: true`:
- `permissions_flat` → `["*"]`
- `services` → `["*"]` (or all registered services)

Your middleware/permission class must treat `"*"` in `permissions_flat` as "all permissions granted."

### Token Lifetime

| Token | Default lifetime |
|---|---|
| Access token | 1 hour (3600 seconds) |
| Refresh token | 7 days (604800 seconds) |

Configured via `JWT_ACCESS_TOKEN_LIFETIME` and `JWT_REFRESH_TOKEN_LIFETIME` in IAM's environment.

---

## 5. Session Management

IAM enforces **one active session per user**. When a user logs in from a new location, all existing sessions are revoked.

### Session States

| Status | Meaning |
|---|---|
| `active` | Valid — requests proceed |
| `revoked` | Explicitly terminated (logout, admin action, or new login) |
| `expired` | Timed out — re-login required |

### How `SessionValidatingJWTAuthentication` Works

On every authenticated request to IAM itself:
1. Validates JWT signature and expiry
2. Extracts `jti` from token
3. Looks up `UserSession` by `access_jti`
4. If session status is `revoked` or `expired` → raises `InvalidToken` with code `SESSION_REVOKED` / `SESSION_EXPIRED`
5. If no session found → allows request (backward compatibility)

> **Note:** Other services do NOT perform session validation. They only decode the JWT locally. Session revocation is enforced at IAM; the token remains cryptographically valid until it expires. Design accordingly: access token lifetime (1 hour) is the maximum window for a revoked session's token to be used at other services.

---

## 6. User Endpoints

All user management endpoints require `IsAuthenticated + IsAdminUser` unless noted.

### 6.1 List / Create Users

```
GET  /api/v1/iam/users/              → paginated user list
POST /api/v1/iam/users/              → create user
```

**Query filters:** `is_active`, `is_staff`, `is_superuser`, `user_type`, `status`  
**Search fields:** `email`, `first_name`, `last_name`, `username`  
**Ordering:** `created_at`, `last_name`, `first_name`, `email`

**User object:**
```json
{
  "id": "uuid",
  "email": "user@fcc.go.tz",
  "username": "jdoe",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+255712345678",
  "employee_id": "EMP001",
  "department": "Compliance",
  "position": "Officer",
  "user_type": "internal",
  "status": "active",
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "mfa_enabled": false,
  "profile_picture": "/api/v1/iam/media/profile_pictures/…",
  "signature": "/api/v1/iam/media/signatures/…",
  "last_login_at": "2025-01-01T08:00:00Z",
  "password_expires_at": "2025-07-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 6.2 User Detail

```
GET    /api/v1/iam/users/<uuid>/     → retrieve user
PUT    /api/v1/iam/users/<uuid>/     → full update
PATCH  /api/v1/iam/users/<uuid>/     → partial update
DELETE /api/v1/iam/users/<uuid>/     → delete user
```

---

## 7. Profile & Signature Endpoints

These operate on the **currently authenticated user**. No admin privilege needed.

```
GET  /api/v1/iam/profile/                         → current user profile
POST /api/v1/iam/profile/update/                  → update profile fields
POST /api/v1/iam/profile/change-password/         → change own password
GET  /api/v1/iam/profile/permissions/             → own permission codes
GET  /api/v1/iam/profile/all-permissions/         → own full permission list
GET  /api/v1/iam/profile/password-status/         → password expiry info
GET  /api/v1/iam/profile/lockout-status/          → own lockout status
```

### Signature Management

Users draw their signature on a canvas; the front-end sends it as base64. IAM stores it as an image file.

```
POST   /api/v1/iam/profile/signature/save/        → save drawn signature (base64)
DELETE /api/v1/iam/profile/signature/remove/      → remove signature
```

**Request body for save:**
```json
{
  "signature_data": "data:image/png;base64,iVBORw0KGgo..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Signature saved successfully",
  "signature_url": "https://gateway/api/v1/iam/media/signatures/2025/01/01/uuid_signature.png"
}
```

### Profile Picture

```
POST   /api/v1/iam/profile/picture/upload/        → upload picture (multipart)
DELETE /api/v1/iam/profile/picture/remove/        → remove picture
```

### Signature URL Pattern

Signatures are served at:
```
/api/v1/iam/media/signatures/<year>/<month>/<day>/<filename>
```
The URL uses the gateway host. Services (DRS, GRC) that need to embed a user's signature on PDFs must fetch this URL using a service token or use a signed URL.

---

## 8. Account Security Endpoints

```
GET  /api/v1/iam/users/<uuid>/lockout-status/       → lockout state for a user
POST /api/v1/iam/users/<uuid>/unlock/               → admin: unlock account
GET  /api/v1/iam/users/locked/                      → list locked accounts
POST /api/v1/iam/users/<uuid>/force-password-change/ → admin: force user to reset password
GET  /api/v1/iam/security-settings/                  → read security settings (admin)
PUT  /api/v1/iam/security-settings/                  → update security settings (admin)
GET  /api/v1/iam/security-settings/public/           → public subset (no auth required)
POST /api/v1/iam/security-settings/test-smtp/        → test SMTP connection (admin)
```

Security settings control lockout thresholds, password expiry, password rules, and SMTP configuration.

---

## 9. Roles Endpoints

```
GET  /api/v1/iam/roles/                             → list roles
POST /api/v1/iam/roles/                             → create role
GET  /api/v1/iam/roles/<uuid>/                      → role detail
PUT  /api/v1/iam/roles/<uuid>/                      → update role
DELETE /api/v1/iam/roles/<uuid>/                    → delete role
POST /api/v1/iam/users/<int:user_id>/roles/<int:role_id>/assign/  → assign role (legacy)
POST /api/v1/iam/users/<int:user_id>/roles/<int:role_id>/remove/  → remove role (legacy)
```

### Role Object

```json
{
  "id": "uuid",
  "code": "compliance_officer",
  "name": "Compliance Officer",
  "description": "Has access to GRC audit and compliance modules",
  "is_system": false,
  "is_active": true,
  "assign_by_default": false,
  "assign_to_external_users": false,
  "service": "grc-service",
  "full_code": "grc-service.compliance_officer"
}
```

**Important role flags:**
- `assign_by_default: true` → role is auto-assigned to every new user
- `assign_to_external_users: true` → role is auto-assigned to externally verified users
- `service` → null for legacy IAM roles; service UUID for service-specific roles

---

## 10. RBAC Endpoints

The RBAC module (`/api/v1/iam/rbac/`) is the **preferred path** for role assignments and permissions management (replaces legacy roles endpoints for role-permission linking).

```
GET  /api/v1/iam/rbac/user-roles/                         → list user-role assignments
POST /api/v1/iam/rbac/user-roles/                         → create assignment
GET  /api/v1/iam/rbac/user-roles/<uuid>/                  → detail
GET  /api/v1/iam/rbac/users/<uuid>/roles/                 → roles for a user
POST /api/v1/iam/rbac/user-roles/assign/                  → assign role to user
POST /api/v1/iam/rbac/user-roles/remove/                  → remove role from user
POST /api/v1/iam/rbac/user-roles/assign-by-attributes/    → bulk assign by department/type (D-017)
POST /api/v1/iam/rbac/user-roles/revoke-by-attributes/    → bulk revoke by attributes (D-017)
POST /api/v1/iam/rbac/users/<uuid>/assign-external-roles/ → service-to-service external role assignment

GET  /api/v1/iam/rbac/role-permissions/                   → list role-permission links
POST /api/v1/iam/rbac/role-permissions/                   → link permission to role
GET  /api/v1/iam/rbac/role-permissions/stats/             → permission statistics
POST /api/v1/iam/rbac/role-permissions/bulk-assign/       → bulk assign permissions to role
POST /api/v1/iam/rbac/role-permissions/bulk-remove/       → bulk remove permissions from role
GET  /api/v1/iam/rbac/role-permissions/matrix-data/       → permission matrix for UI
GET  /api/v1/iam/rbac/roles/<uuid>/permissions/           → permissions for a specific role

GET  /api/v1/iam/rbac/permissions/                        → list all registered permissions
GET  /api/v1/iam/rbac/permissions/filter-options/         → filter options for permissions UI
```

### Assign Role to User

```
POST /api/v1/iam/rbac/user-roles/assign/
Authorization: Bearer <admin-token>

{
  "user_id": "uuid",
  "role_id": "uuid",
  "expires_at": null
}
```

### Bulk Assign by Attributes (D-017)

```
POST /api/v1/iam/rbac/user-roles/assign-by-attributes/
{
  "role_id": "uuid",
  "department": "Compliance",
  "user_type": "internal"
}
```

---

## 11. Permission Registration via Kafka

Every service **must** register its permissions with IAM on startup. IAM stores them in the `service_permissions` table and embeds them in JWTs for any user who holds the relevant roles.

### Topic

```
service.permission.registry
```

IAM has **two consumers** on this topic:
- `PermissionRegistrationConsumer` (apps/permissions/kafka_consumer.py)
- `UnifiedPermissionConsumer` (apps/roles/kafka_consumer.py — preferred unified system)

Both process the same events; the unified consumer is the active one.

### Event Types Consumed by IAM

| Event type | Trigger |
|---|---|
| `service_permission_registration` | Service startup — registers all permission codes |
| `service_role_definitions` | Service startup — registers default role definitions |
| `service_permission_update` | Permission list changed at runtime |
| `service_health_check` | Periodic heart-beat (IAM updates `last_registration`) |

### `service_permission_registration` Payload

```json
{
  "event_type": "service_permission_registration",
  "source_service": "grc-service",
  "timestamp": "2025-01-01T08:00:00Z",
  "data": {
    "service_name": "grc-service",
    "service_version": "1.0.0",
    "service_description": "GRC - Governance, Risk and Compliance Service",
    "permissions": [
      {
        "permission_code": "grc:audit_universe:view",
        "name": "View Audit Universe",
        "description": "Allows viewing audit universe entries",
        "resource_type": "audit_universe",
        "action": "view",
        "category": "audit"
      },
      {
        "permission_code": "grc:audit_universe:manage",
        "name": "Manage Audit Universe",
        "description": "Allows creating, editing, deleting audit universe entries",
        "resource_type": "audit_universe",
        "action": "manage",
        "category": "audit"
      }
    ]
  }
}
```

### `service_role_definitions` Payload

```json
{
  "event_type": "service_role_definitions",
  "source_service": "grc-service",
  "timestamp": "2025-01-01T08:00:00Z",
  "data": {
    "service_name": "grc-service",
    "roles": [
      {
        "code": "grc_viewer",
        "name": "GRC Viewer",
        "description": "Read-only access to GRC module",
        "permissions": ["grc:audit_universe:view", "grc:risk:view"]
      },
      {
        "code": "grc_officer",
        "name": "GRC Compliance Officer",
        "description": "Full access to GRC module",
        "permissions": ["grc:audit_universe:view", "grc:audit_universe:manage", "grc:risk:view", "grc:risk:manage"]
      }
    ]
  }
}
```

### Permission Code Naming Convention

```
<service-identifier>:<resource>:<action>
```

Examples:
- `grc:audit_universe:view`
- `grc:audit_universe:manage`
- `document:document:view`
- `document:document:upload`
- `wo:workflow:view`
- `wo:workflow:create`

Use the **same service identifier consistently** in all permission codes published and in the `services` claim checked by the middleware.

### How IAM Embeds Permissions in Token

After IAM receives a `service_permission_registration` event:
1. Stores service and permissions in DB
2. Link permissions to roles via the RBAC admin UI or `bulk-assign` API
3. On next login/refresh: `UnifiedPermissionResolutionService.get_user_permissions(user)` resolves all permissions across all roles and embeds them in `permissions_flat`

---

## 12. Consuming Services — JWT Middleware Pattern

Every service that needs to enforce IAM-issued permissions must implement a `JWTPermissionMiddleware`. The GRC service implementation is the canonical reference.

### File: `apps/core/permission_middleware.py`

```python
"""
Permission validation middleware — validates permissions from JWT tokens locally.
"""
import logging
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class JWTPermissionMiddleware(MiddlewareMixin):
    """
    On every authenticated request:
    1. Decodes Bearer JWT using shared JWT_SECRET_KEY
    2. Checks the user has access to this service (in token.services[])
    3. Sets request attributes:
         request.user_id          – str UUID
         request.user_email       – str
         request.is_superuser     – bool
         request.is_staff         – bool
         request.user_permissions – dict  (raw JWT 'permissions' field — usually {})
         request.user_permissions_flat – list (raw JWT 'permissions_flat')
         request.user_services    – list
         request.<svc>_permissions – list of '<svc>:*' permission codes for THIS service
    """
    _SERVICE_ALIASES = {'my-service', 'my-service-name'}  # Match what IAM stores

    def process_request(self, request):
        # Skip paths
        skip_paths = ['/health/', '/admin/', '/static/', '/media/', '/api/schema/', '/api/docs/']
        if any(request.path.startswith(p) for p in skip_paths):
            return None

        # Service-to-service: X-Service-Token header bypasses JWT check
        if request.META.get('HTTP_X_SERVICE_TOKEN'):
            return None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None  # Let DRF handle 401

        token = auth_header.split(' ', 1)[1]

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={'verify_exp': True},
            )

            services = payload.get('services', [])
            is_superuser = payload.get('is_superuser', False)
            has_service = '*' in services or any(s in self._SERVICE_ALIASES for s in services)

            if not is_superuser and not has_service:
                return JsonResponse({
                    'success': False,
                    'error': {'message': 'Access to this service denied', 'code': 'SERVICE_ACCESS_DENIED'}
                }, status=403)

            # Set request attributes
            request.user_id = payload.get('user_id')
            request.user_email = payload.get('email')
            request.is_superuser = is_superuser
            request.is_staff = payload.get('is_staff', False)
            request.user_permissions = payload.get('permissions', {})
            request.user_permissions_flat = payload.get('permissions_flat', [])
            request.user_services = services

            # Extract service-specific permissions
            all_perms = request.user_permissions_flat
            if '*' in all_perms:
                request.my_permissions = ['*']
            else:
                request.my_permissions = [p for p in all_perms if p.startswith('my-service:')]

        except jwt.ExpiredSignatureError:
            return JsonResponse({'success': False, 'error': {'message': 'Token has expired', 'code': 'TOKEN_EXPIRED'}}, status=401)
        except jwt.InvalidTokenError as e:
            return JsonResponse({'success': False, 'error': {'message': 'Invalid token', 'code': 'INVALID_TOKEN'}}, status=401)

        return None
```

### Register in `config/settings.py`

```python
MIDDLEWARE = [
    # ... other middleware ...
    "apps.core.permission_middleware.JWTPermissionMiddleware",
    # ... DRF middleware ...
]
```

### Required Environment Variables

Every consuming service needs these IAM-compatible settings:
```env
# Must match IAM's settings exactly
JWT_SECRET_KEY=<shared-secret>
JWT_ALGORITHM=HS256
```

---

## 13. Consuming Services — Permission Classes Pattern

After the middleware populates `request.<svc>_permissions`, create per-permission DRF permission classes.

### File: `apps/api/permissions_jwt.py`

```python
"""
JWT-based permission classes — all checks are LOCAL, no HTTP calls to IAM.
"""
import logging
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


def _check_permission_locally(request, permission_code: str) -> bool:
    """Check a permission code against the list set by JWTPermissionMiddleware."""
    if not hasattr(request, 'my_permissions'):
        logger.warning(f"request.my_permissions not found. Denying: {permission_code}")
        return False

    perms = request.my_permissions
    if '*' in perms:
        return True  # Superuser wildcard

    has_it = permission_code in perms
    if not has_it:
        logger.warning(
            f"Permission denied: user={getattr(request, 'user_email', '?')}, "
            f"required={permission_code}"
        )
    return has_it


class CanViewMyResource(BasePermission):
    def has_permission(self, request, view):
        return _check_permission_locally(request, 'my-service:my_resource:view')


class CanManageMyResource(BasePermission):
    def has_permission(self, request, view):
        return _check_permission_locally(request, 'my-service:my_resource:manage')
```

### Use in Views

```python
from rest_framework.permissions import IsAuthenticated
from apps.api.permissions_jwt import CanViewMyResource, CanManageMyResource

class MyResourceView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewMyResource().has_permission(request, self):
                self.permission_denied(request, message='my-service:my_resource:view required')
        elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if not CanManageMyResource().has_permission(request, self):
                self.permission_denied(request, message='my-service:my_resource:manage required')
```

### Why Local Checks (No IAM HTTP Calls)

- The JWT `permissions_flat` array is the authoritative permission list for the current token's lifetime
- Checking locally avoids an IAM round-trip on every request (latency + single-point-of-failure risk)
- Permission changes take effect on the user's next token refresh (up to 1 hour delay is acceptable)
- Superusers always get `["*"]` in permissions_flat → all permissions granted without enumeration

---

## 14. MFA Endpoints

All MFA endpoints are under `/api/v1/iam/mfa/`.

### MFA Status

```
GET /api/v1/iam/mfa/status/
Authorization: Bearer <token>
```

Response:
```json
{
  "mfa_enabled": true,
  "totp_device_count": 1,
  "backup_codes_remaining": 8
}
```

### TOTP Enrollment

```
POST /api/v1/iam/mfa/enroll/totp/       → get QR code / secret
POST /api/v1/iam/mfa/verify/totp/       → confirm enrollment with 6-digit code

POST /api/v1/iam/mfa/devices/totp/                     → create TOTP device
PUT  /api/v1/iam/mfa/devices/totp/<id>/                → update
POST /api/v1/iam/mfa/devices/totp/<id>/delete/         → delete
```

### Backup Codes

```
POST /api/v1/iam/mfa/backup-codes/generate/    → generate 10 new backup codes
POST /api/v1/iam/mfa/backup-codes/verify/      → verify a backup code at login
GET  /api/v1/iam/mfa/backup-codes/             → list backup codes (masked)
```

### Email OTP (D-011)

For accounts without a TOTP device, IAM supports email-based OTP:

```
POST /api/v1/iam/mfa/email-otp/send/        → send OTP to registered email
POST /api/v1/iam/mfa/email-otp/verify/      → verify OTP code
```

### Disable MFA

```
POST /api/v1/iam/mfa/disable/
{ "password": "current-password" }
```

### Admin Endpoints

```
GET /api/v1/iam/mfa/admin/devices/          → all MFA devices across users
GET /api/v1/iam/mfa/admin/backup-codes/     → all backup codes
GET /api/v1/iam/mfa/attempts/               → MFA attempt history (own)
GET /api/v1/iam/mfa/attempts/all/           → all attempts (admin)
```

---

## 15. Session Endpoints

```
GET  /api/v1/iam/sessions/                     → list own sessions
GET  /api/v1/iam/sessions/<id>/                → session detail
POST /api/v1/iam/sessions/<id>/terminate/      → terminate a specific session
GET  /api/v1/iam/sessions/current/status/      → current session status
POST /api/v1/iam/sessions/extend/              → extend session expiry
POST /api/v1/iam/sessions/activity/            → update last activity timestamp
```

### Session Object

```json
{
  "id": 42,
  "user": "uuid",
  "access_jti": "token-jti",
  "ip_address": "196.0.0.1",
  "user_agent": "Mozilla/5.0...",
  "status": "active",
  "is_active": true,
  "expires_at": "2025-01-02T08:00:00Z",
  "last_activity_at": "2025-01-01T09:30:00Z",
  "created_at": "2025-01-01T08:00:00Z"
}
```

---

## 16. Audit Log Endpoints

IAM maintains an internal audit trail of all authentication and identity events.

```
GET /api/v1/iam/audit-logs/                            → list audit logs (admin)
GET /api/v1/iam/audit-logs/<id>/                       → log detail
GET /api/v1/iam/users/<int:user_id>/audit-logs/        → audit logs for a user
GET /api/v1/iam/objects/<type>/<int:id>/audit-logs/    → audit logs for an object
```

### Audit Log Actions

| Category | Actions |
|---|---|
| Auth | `LOGIN`, `LOGOUT`, `LOGIN_FAILED`, `EMAIL_VERIFY` |
| Password | `PASSWORD_CHANGE`, `PASSWORD_RESET_REQUEST`, `PASSWORD_RESET_COMPLETE`, `PASSWORD_EXPIRED`, `PASSWORD_EXPIRATION_WARNING`, `PASSWORD_CHANGE_FORCED` |
| Account | `ACCOUNT_LOCKED`, `ACCOUNT_UNLOCKED`, `ACCOUNT_UNLOCKED_AUTO` |
| Users | `USER_CREATE`, `USER_UPDATE`, `USER_DELETE`, `USER_STATUS_CHANGE` |
| Roles | `ROLE_CREATE`, `ROLE_UPDATE`, `ROLE_DELETE`, `ROLE_ASSIGN`, `ROLE_REVOKE`, `USER_ROLE_UPDATE`, `USER_ROLE_REMOVE` |
| Permissions | `PERMISSION_GRANT`, `PERMISSION_REVOKE` |
| Sessions | `SESSION_CREATE`, `SESSION_REVOKE`, `SESSION_EXPIRE` |
| Applicants | `APPLICANT_CREATE`, `APPLICANT_UPDATE`, `APPLICANT_APPROVE`, `APPLICANT_REJECT`, `APPLICANT_CONVERT` |
| System | `SYSTEM_START`, `SYSTEM_STOP`, `CONFIG_CHANGE`, `SECURITY_SETTINGS_UPDATE` |

### Audit Log Object

```json
{
  "id": 1234,
  "user": "uuid",
  "action": "LOGIN",
  "resource_type": "USER",
  "resource_id": "uuid",
  "ip_address": "196.0.0.1",
  "user_agent": "Mozilla/5.0...",
  "description": "User logged in successfully",
  "metadata": {},
  "severity": "low",
  "created_at": "2025-01-01T08:00:00Z"
}
```

---

## 17. Token Introspection

```
GET /api/v1/iam/introspect/
Authorization: Bearer <access-token>
```

Returns full user details plus current roles and permissions as stored in IAM's DB (not just the JWT payload).

**Response:**
```json
{
  "success": true,
  "data": {
    "active": true,
    "user": {
      "id": "uuid",
      "email": "user@fcc.go.tz",
      "username": "jdoe",
      "first_name": "John",
      "last_name": "Doe",
      "status": "active",
      "user_type": "internal",
      "is_email_verified": true
    },
    "roles": [
      {"id": "uuid", "code": "compliance_officer", "name": "Compliance Officer"}
    ],
    "permissions": [
      {"id": 1, "codename": "grc:audit_universe:view", "name": "View Audit Universe"}
    ],
    "exp": 1700000000
  }
}
```

Use this endpoint when a service needs **current, fresh** permission data (e.g., after role reassignment). For normal per-request checks, use the JWT claims instead.

---

## 18. Kafka Topics IAM Publishes

IAM publishes notification events for Work Orchestration to deliver to users.

### Notification Topics

| Topic | Priority level | Example events |
|---|---|---|
| `notifications-urgent` | Urgent | Account locked |
| `notifications-high` | High | Password reset, email verification |
| `notifications-normal` | Normal | Welcome email, profile update |
| `notifications-low` | Low | Login notification |

### Notification Event Schema

```json
{
  "event_id": "uuid",
  "event_type": "notification",
  "source_service": "iam-service",
  "timestamp": "2025-01-01T08:00:00Z",
  "data": {
    "template_code": "iam.user.registration",
    "recipients": {
      "email": ["user@fcc.go.tz"]
    },
    "context": {
      "user": {
        "id": "uuid",
        "email": "user@fcc.go.tz",
        "first_name": "John"
      },
      "verification_link": "https://app.fcc.go.tz/verify?token=..."
    },
    "priority": "high",
    "idempotency_key": "iam.user.registration-user@fcc.go.tz-uuid-202501011200"
  }
}
```

### IAM Notification Template Codes

| Code | When sent |
|---|---|
| `iam.user.registration` | New user registered |
| `iam.auth.email_verification` | Email verification required |
| `iam.auth.password_reset` | Password reset requested |
| `iam.auth.password_expiry_warning` | Password expires soon |
| `iam.auth.account_locked` | Account locked due to failed attempts |
| `iam.auth.account_unlocked` | Account unlocked by admin |
| `iam.auth.login_notification` | New login detected |

---

## 19. Kafka Topics IAM Consumes

| Topic | Consumer group | Description |
|---|---|---|
| `service.permission.registry` | `iam-unified-permission-consumer-group` | Receives permission registrations from all services |

IAM also has a legacy consumer (`iam-permission-consumer-group`) on the same topic for the `permissions` app. Both process the same events.

---

## 20. Service-to-Service Authentication

When microservices call each other without a user's Bearer token (e.g., DRS calling IAM for user lookup during document approval), they use the `X-Service-Token` header.

```
GET /api/v1/iam/users/lookup/email/user@fcc.go.tz/
X-Service-Token: <service-token>
```

The `JWTPermissionMiddleware` (in all consuming services) skips its validation when it sees `X-Service-Token`, letting DRF handle it. IAM itself recognises the service token and grants access to service-only endpoints.

Configure in each service's environment:
```env
IAM_SERVICE_TOKEN=<shared-service-token>
IAM_SERVICE_URL=http://fims-iam-service:8000
```

---

## 21. User Lookup for Other Services

These endpoints are specifically designed for service-to-service use:

```
GET /api/v1/iam/users/lookup/
GET /api/v1/iam/users/lookup/email/<email>/
GET /api/v1/iam/users/lookup/id/<user_id>/
GET /api/v1/iam/users/<uuid>/permissions/
```

### Lookup by Email

```
GET /api/v1/iam/users/lookup/email/officer@fcc.go.tz/
X-Service-Token: <service-token>
```

**Response:**
```json
{
  "id": "uuid",
  "email": "officer@fcc.go.tz",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "signature_url": "https://gateway/api/v1/iam/media/signatures/2025/01/01/uuid_sig.png",
  "profile_picture_url": "https://gateway/api/v1/iam/media/profile_pictures/..."
}
```

### Activate for Client Service

When the client-service creates an external user account, it calls IAM to activate it:

```
POST /api/v1/iam/users/<uuid>/activate-for-client-service/
X-Service-Token: <service-token>
```

---

## 22. Media Serving — Profiles & Signatures

IAM serves user media (profile pictures and signatures) through a dedicated route:

```
/api/v1/iam/media/<path>
```

The `serve_media` view handles authentication before serving files — it checks either a Bearer token or an `X-Service-Token`. This means signature images embedded in DRS PDFs must be fetched by the backend using a service token, not a direct file URL.

**Usage in DRS (approved stamp / signature overlay):**
```python
import requests

signature_url = f"{settings.IAM_SERVICE_URL}/api/v1/iam/media/signatures/{signature_path}"
response = requests.get(
    signature_url,
    headers={"X-Service-Token": settings.IAM_SERVICE_TOKEN},
    timeout=10
)
signature_bytes = response.content
```

---

## 23. GRC-Specific Integration Patterns

### 23.1 Permission Registration at Startup

GRC registers its permissions on startup via Kafka. The registration is idempotent — safe to run on every deployment.

```python
# apps/infrastructure/startup.py (or AppConfig.ready())
from apps.infrastructure.kafka_publisher import publish_permission_registration

def register_grc_permissions():
    publish_permission_registration(
        service_name='grc-service',
        service_version='1.0.0',
        service_description='GRC - Governance, Risk and Compliance Service',
        permissions_file='config/permissions/grc-service.json'
    )
```

### 23.2 Permission File Format (`config/permissions/grc-service.json`)

```json
{
  "service_name": "grc-service",
  "permissions": [
    {
      "permission_code": "grc:audit_universe:view",
      "name": "View Audit Universe",
      "description": "Read access to audit universe entries",
      "resource_type": "audit_universe",
      "action": "view",
      "category": "audit"
    },
    {
      "permission_code": "grc:audit_universe:manage",
      "name": "Manage Audit Universe",
      "description": "Create, edit, delete audit universe entries",
      "resource_type": "audit_universe",
      "action": "manage",
      "category": "audit"
    }
  ]
}
```

### 23.3 Checking Permissions in GRC Views

```python
# apps/api/permissions_jwt.py
from rest_framework.permissions import BasePermission

class CanViewAuditUniverse(BasePermission):
    def has_permission(self, request, view):
        perms = getattr(request, 'grc_permissions', [])
        return '*' in perms or 'grc:audit_universe:view' in perms

class CanManageAuditUniverse(BasePermission):
    def has_permission(self, request, view):
        perms = getattr(request, 'grc_permissions', [])
        return '*' in perms or 'grc:audit_universe:manage' in perms
```

### 23.4 Extracting User Identity in GRC Views

```python
def my_view(request):
    user_id = request.user_id          # UUID string from JWT
    user_email = request.user_email    # from JWT
    is_su = request.is_superuser       # from JWT
    
    # For display name, call IAM only if you need it:
    # user_info = iam_client.lookup_by_id(user_id)
```

### 23.5 Working with User Signatures (for PDF Overlay)

GRC documents that need a user's approval signature:
1. Get `user_id` from request JWT
2. Call `GET /api/v1/iam/users/lookup/id/<user_id>/` with `X-Service-Token`
3. Extract `signature_url` from response
4. Fetch signature bytes from IAM media URL with `X-Service-Token`
5. Embed bytes in PDF using `reportlab` / `PyPDF2`

If the user has no signature, prompt them via the profile endpoint before allowing approval.

### 23.6 Using IAM Roles for GRC Access Control

For GRC-level access (e.g., only Compliance Officers can view the audit universe):
1. Define GRC-specific roles in `service_role_definitions` Kafka event
2. Assign roles to users via RBAC admin UI or `POST /api/v1/iam/rbac/user-roles/assign/`
3. GRC permission classes check `request.grc_permissions` which IAM embedded in the JWT

Never duplicate role logic in GRC — roles live in IAM, permissions are enforced locally from the JWT.

---

## 24. Strict Rules — What Other Services Must Never Do

**❌ Never issue JWTs directly.** Only IAM issues and refreshes tokens. If a service needs to authenticate a machine-to-machine action, use `X-Service-Token`, not a self-signed JWT.

**❌ Never store user passwords.** IAM is the only password authority. If another service receives a password field, it must reject it or forward it to IAM's register endpoint.

**❌ Never call `GET /api/v1/iam/introspect/` on every request.** This is for debugging or post-role-change refresh only. Normal per-request permission checks must use the JWT payload locally.

**❌ Never bypass `JWTPermissionMiddleware`.** The middleware sets the `request.<svc>_permissions` list that DRF permission classes depend on. Removing it from MIDDLEWARE silently grants all permissions to all users.

**❌ Never hard-code user IDs.** Use `request.user_id` (from JWT) instead of querying the database for the current user. GRC, DRS, and WO do not have access to IAM's user table directly.

**❌ Never treat absence of `grc_permissions` attribute as "allow all".** If the middleware didn't run (or token was missing), `request.grc_permissions` won't exist. Permission classes must return `False` in that case (see `_check_grc_permission_locally`).

---

## 25. Complete API Quick Reference

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/iam/auth/login/` | None | Login (MFA-aware, rate limited) |
| POST | `/api/v1/iam/auth/refresh/` | None | Refresh access token |
| POST | `/api/v1/iam/auth/logout/` | Bearer | Logout and revoke session |
| POST | `/api/v1/iam/auth/register/` | None | Register new user |
| POST | `/api/v1/iam/auth/verify-email/` | None | Verify email token |
| POST | `/api/v1/iam/auth/forgot-password/` | None | Send reset email |
| POST | `/api/v1/iam/auth/reset-password/` | None | Confirm password reset |
| POST | `/api/v1/iam/auth/reset-expired-password/` | Bearer | Change expired password |
| GET | `/api/v1/iam/introspect/` | Bearer | Get full user + permission info |
| GET | `/api/v1/iam/health/` | None | Health check |

### Users

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/iam/users/` | Admin | List users (paginated, filterable) |
| POST | `/api/v1/iam/users/` | Admin | Create user |
| GET | `/api/v1/iam/users/<uuid>/` | Admin | Get user |
| PUT/PATCH | `/api/v1/iam/users/<uuid>/` | Admin | Update user |
| DELETE | `/api/v1/iam/users/<uuid>/` | Admin | Delete user |
| GET | `/api/v1/iam/users/lookup/` | ServiceToken | Lookup users |
| GET | `/api/v1/iam/users/lookup/email/<email>/` | ServiceToken | Lookup by email |
| GET | `/api/v1/iam/users/lookup/id/<uuid>/` | ServiceToken | Lookup by ID |
| GET | `/api/v1/iam/users/<uuid>/permissions/` | Bearer | User's permission list |
| POST | `/api/v1/iam/users/<uuid>/unlock/` | Admin | Unlock account |
| GET | `/api/v1/iam/users/<uuid>/lockout-status/` | Admin | Lockout status |
| GET | `/api/v1/iam/users/locked/` | Admin | List locked accounts |
| POST | `/api/v1/iam/users/<uuid>/force-password-change/` | Admin | Force password reset |
| POST | `/api/v1/iam/users/<uuid>/activate-for-client-service/` | ServiceToken | Activate for client service |

### Profile

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/iam/profile/` | Bearer | Own profile |
| POST | `/api/v1/iam/profile/update/` | Bearer | Update own profile |
| POST | `/api/v1/iam/profile/change-password/` | Bearer | Change own password |
| GET | `/api/v1/iam/profile/permissions/` | Bearer | Own permissions |
| GET | `/api/v1/iam/profile/all-permissions/` | Bearer | All permissions |
| GET | `/api/v1/iam/profile/password-status/` | Bearer | Password expiry info |
| GET | `/api/v1/iam/profile/lockout-status/` | Bearer | Own lockout status |
| POST | `/api/v1/iam/profile/signature/save/` | Bearer | Save drawn signature |
| DELETE | `/api/v1/iam/profile/signature/remove/` | Bearer | Remove signature |
| POST | `/api/v1/iam/profile/picture/upload/` | Bearer | Upload profile picture |
| DELETE | `/api/v1/iam/profile/picture/remove/` | Bearer | Remove profile picture |

### Roles

| Method | Path | Auth | Description |
|---|---|---|---|
| GET/POST | `/api/v1/iam/roles/` | Admin | List/create roles |
| GET/PUT/DELETE | `/api/v1/iam/roles/<uuid>/` | Admin | Role detail |

### RBAC

| Method | Path | Auth | Description |
|---|---|---|---|
| GET/POST | `/api/v1/iam/rbac/user-roles/` | Admin | List/create user-role assignments |
| GET | `/api/v1/iam/rbac/users/<uuid>/roles/` | Admin | User's roles |
| POST | `/api/v1/iam/rbac/user-roles/assign/` | Admin | Assign role to user |
| POST | `/api/v1/iam/rbac/user-roles/remove/` | Admin | Remove role from user |
| POST | `/api/v1/iam/rbac/user-roles/assign-by-attributes/` | Admin | Bulk assign by dept/type |
| POST | `/api/v1/iam/rbac/users/<uuid>/assign-external-roles/` | ServiceToken | Assign roles to external user |
| GET | `/api/v1/iam/rbac/permissions/` | Admin | All registered permissions |
| GET/POST | `/api/v1/iam/rbac/role-permissions/` | Admin | Role-permission links |
| POST | `/api/v1/iam/rbac/role-permissions/bulk-assign/` | Admin | Bulk add permissions to role |
| POST | `/api/v1/iam/rbac/role-permissions/bulk-remove/` | Admin | Bulk remove from role |
| GET | `/api/v1/iam/rbac/role-permissions/matrix-data/` | Admin | Permission matrix |

### MFA

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/iam/mfa/status/` | Bearer | MFA status |
| POST | `/api/v1/iam/mfa/enroll/totp/` | Bearer | Begin TOTP enrollment |
| POST | `/api/v1/iam/mfa/verify/totp/` | Bearer | Complete TOTP enrollment |
| POST | `/api/v1/iam/mfa/disable/` | Bearer | Disable MFA |
| POST | `/api/v1/iam/mfa/backup-codes/generate/` | Bearer | Generate backup codes |
| POST | `/api/v1/iam/mfa/backup-codes/verify/` | Bearer | Verify backup code |
| POST | `/api/v1/iam/mfa/email-otp/send/` | Bearer | Send email OTP |
| POST | `/api/v1/iam/mfa/email-otp/verify/` | Bearer | Verify email OTP |

### Sessions

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/iam/sessions/` | Bearer | List own sessions |
| GET | `/api/v1/iam/sessions/<id>/` | Bearer | Session detail |
| POST | `/api/v1/iam/sessions/<id>/terminate/` | Bearer | Terminate session |
| GET | `/api/v1/iam/sessions/current/status/` | Bearer | Current session status |
| POST | `/api/v1/iam/sessions/extend/` | Bearer | Extend session |
| POST | `/api/v1/iam/sessions/activity/` | Bearer | Update last activity |

### Audit Logs

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/iam/audit-logs/` | Admin | List all audit logs |
| GET | `/api/v1/iam/audit-logs/<id>/` | Admin | Audit log detail |
| GET | `/api/v1/iam/users/<int>/audit-logs/` | Admin | Logs for user |
| GET | `/api/v1/iam/objects/<type>/<int>/audit-logs/` | Admin | Logs for object |

### Security Settings

| Method | Path | Auth | Description |
|---|---|---|---|
| GET/PUT | `/api/v1/iam/security-settings/` | Admin | Security configuration |
| GET | `/api/v1/iam/security-settings/public/` | None | Public settings |
| POST | `/api/v1/iam/security-settings/test-smtp/` | Admin | Test SMTP |
| GET | `/api/v1/iam/security-settings/password-hashing-info/` | Admin | Hashing algorithm info |

### Media

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/iam/media/<path>` | Bearer / ServiceToken | Serve profile pictures and signatures |

---

*Last updated: 2025 — based on IAM service codebase at `/home/simons/Coding/FIMS/iam-service`*
