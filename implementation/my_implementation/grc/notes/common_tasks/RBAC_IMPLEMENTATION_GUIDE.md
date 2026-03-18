# FIMS — Role-Based Access Control (RBAC) Implementation Guide

> **Scope:** GRC Service (backend + frontend). The same pattern is used in all other FIMS services (DRS, IAM, WO). Follow this guide for every new module.
> **Last updated:** March 2026

---

**NOTE:
THIS GUIDE IS FOR REFERENCE ONLY. IF A TASK REQUIRES NEW ROLES OR PERMISSIONS, THEY SHOULD BE CREATED SPECIFICALLY ACCORDING TO THE REQUIREMENTS OF THAT TASK. BUT THEY SHOULD FOLLOW THE SAME EXISTING PATTERN AS DEFINED IN OTHER PARTS.
AND REFERENCE COMMANDS, HOW TO REGISTER NEW ROLES AND PERMISSIONS CREATED, USERS, AND SETUP ARE EXPLAINED IN THE FILE (grc-service/implementation/my_implementation/grc/notes/grc_notes.md) FROM LINE 1 TO 550 **


**NOTE:
THIS GUIDE IS FOR REFERENCE ONLY. IF A TASK REQUIRES NEW ROLES OR PERMISSIONS, THEY SHOULD BE CREATED SPECIFICALLY ACCORDING TO THE REQUIREMENTS OF THAT TASK. BUT THEY SHOULD FOLLOW THE SAME EXISTING PATTERN AS DEFINED IN OTHER PARTS.
AND REFERENCE COMMANDS, HOW TO REGISTER NEW ROLES AND PERMISSIONS CREATED, USERS, AND SETUP ARE EXPLAINED IN THE FILE (grc-service/implementation/my_implementation/grc/notes/grc_notes.md) FROM LINE 1 TO 550 **



## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [The Full Flow: How a Permission Check Works](#2-the-full-flow-how-a-permission-check-works)
3. [Step 1 — Define Permissions (grc-service.json)](#3-step-1--define-permissions-grc-servicejson)
4. [Step 2 — Register Permissions in IAM](#4-step-2--register-permissions-in-iam)
5. [Step 3 — Assign Permissions to Roles](#5-step-3--assign-permissions-to-roles)
6. [Step 4 — Backend Enforcement (Django Views)](#6-step-4--backend-enforcement-django-views)
7. [Step 5 — Frontend Enforcement (React)](#7-step-5--frontend-enforcement-react)
8. [Roles Reference](#8-roles-reference)
9. [Permission Code Master List](#9-permission-code-master-list)
10. [Complete Worked Example: Adding RBAC for a New Module](#10-complete-worked-example-adding-rbac-for-a-new-module)
11. [Ownership Guards (Row-Level Access Control)](#11-ownership-guards-row-level-access-control)
12. [Cross-Service Permissions (WO, DRS)](#12-cross-service-permissions-wo-drs)
13. [Checklist for New Module RBAC](#13-checklist-for-new-module-rbac)
14. [Common Pitfalls and Fixes](#14-common-pitfalls-and-fixes)
15. [Debugging Guide](#15-debugging-guide)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ IAM SERVICE                                                                  │
│  - Owns roles, permissions, users, assignments                               │
│  - Issues JWT tokens containing permissions_flat + services                  │
│  - ServicePermission records: {service, permission_code, name, ...}          │
│  - RolePermission records: many-to-many (role ↔ permission)                  │
│  - UserRole records: many-to-many (user ↔ role)                              │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ JWT issued on login
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ JWT PAYLOAD (decoded example)                                                │
│  {                                                                           │
│    "user_id": "abc-123",                                                     │
│    "email": "auditor@fcc.go.tz",                                             │
│    "is_superuser": false,                                                    │
│    "services": ["grc-service", "document-service"],                          │
│    "permissions_flat": [                                                     │
│      "grc:audit_engagement:manage",                                          │
│      "grc:audit_meeting:manage",                                             │
│      "grc:audit_working_paper:manage",                                       │
│      "document:document:create",                                             │
│      ...                                                                     │
│    ]                                                                         │
│  }                                                                           │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ Bearer token on every request
                         ┌────────┴──────────────────┐
                         ▼                           ▼
            ┌────────────────────────┐   ┌──────────────────────────────┐
            │ GRC SERVICE (backend)  │   │ FRONTEND (React)             │
            │                        │   │                              │
            │ JWTPermissionMiddleware│   │ tokenUtils.getPermissions    │
            │  → request.grc_perms  │   │  → reads permissions_flat    │
            │                        │   │  from localStorage JWT       │
            │ permissions_jwt.py     │   │                              │
            │  CanXxx classes check  │   │ useGRCPermissions hook       │
            │  request.grc_perms     │   │  → canManageXxx booleans     │
            │                        │   │                              │
            │ DRF check_permissions  │   │ Conditionally render:        │
            │  called per view       │   │  - buttons                   │
            │                        │   │  - actions                   │
            │ Ownership guards in    │   │  - entire pages              │
            │  view logic            │   └──────────────────────────────┘
            └────────────────────────┘
```

**Golden rule:** The frontend hides UI elements for unauthorized roles. The backend **always** enforces independently — frontend hiding is a UX convenience only, not security.

---

## 2. The Full Flow: How a Permission Check Works

When `auditor@fcc.go.tz` (internal_auditor) calls `POST /api/v1/grc/audit/meetings/`:

1. **IAM issued JWT on login** containing `"grc:audit_meeting:manage"` in `permissions_flat`
2. Frontend sends `Authorization: Bearer <jwt>` header
3. **`JWTPermissionMiddleware`** (runs on every request):
   - Decodes the JWT using `JWT_SECRET_KEY` — no IAM call, 100% local
   - Checks `services` array includes `grc-service` or `grc`
   - Filters `permissions_flat` to only `grc:*` codes → sets `request.grc_permissions`
   - Sets `request.grc_permissions = ['grc:audit_meeting:manage', ...]`

   > **Design note:** The JWT also contains a `permissions` dict, but it is always `{}` (empty) by design in `jwt_enhanced.py`. The middleware's lookup `perms_dict.get('grc-service', [])` therefore always returns `[]`. The real working path is the fallback that filters `permissions_flat` directly. Do not try to populate the `permissions` dict — the flat list is the intended design.
4. DRF calls **`check_permissions(request)`** on the view class
5. View calls `CanManageAuditMeeting().has_permission(request, self)`:
   - Delegates to `_check_grc_permission_locally(request, 'grc:audit_meeting:manage')`
   - Checks `'grc:audit_meeting:manage' in request.grc_permissions` → `True`
6. Request proceeds to `post()` handler
7. Inside handler: ownership guard checks `meeting.organized_by == request.user_id`

If the user does NOT have the permission, step 5 returns `False`, DRF raises a 403:
```json
{"detail": "grc:audit_meeting:manage permission required."}
```

---

## 3. Step 1 — Define Permissions (`grc-service.json`)

**File:** `grc-service/config/permissions/grc-service.json`

This file is the **source of truth** for what permissions exist. Every permission code used in backend view classes and frontend hooks must have an entry here.

### Format

```json
{
  "service": {
    "name": "grc-service",
    "version": "0.1.0",
    "description": "Governance, Risk, and Compliance Service (Audit Module)"
  },
  "permissions": [
    {
      "permission_code": "grc:audit_meeting:manage",
      "name": "Manage Audit Meetings",
      "description": "Schedule and manage audit meetings (entry, pre-exit, exit)",
      "resource_type": "audit_meeting",
      "action": "manage",
      "category": "audit_meeting"
    },
    {
      "permission_code": "grc:audit_meeting:view",
      "name": "View Audit Meetings",
      "description": "Read-only access to audit meeting records",
      "resource_type": "audit_meeting",
      "action": "view",
      "category": "audit_meeting"
    }
  ]
}
```

### Permission code convention

```
{service}:{resource}:{action}

grc : audit_meeting : manage
grc : audit_meeting : view
grc : audit_plan    : approve
```

Standard actions:
| Action | Meaning |
|---|---|
| `view` | Read-only access |
| `manage` | Create, update, delete |
| `approve` | Approve / sign off |
| `review` | Review and provide feedback |
| `conduct` | Perform the action (e.g. conduct risk assessment) |
| `sign` | Electronically sign a document |
| `respond` | Respond to / acknowledge (e.g. auditee responds to finding) |
| `update` | Partial update only (e.g. update monitoring status) |

> **Always define the read (`view`) permission separately from the write (`manage`) permission.** This lets some roles read without letting them write.

---

## 4. Step 2 — Register Permissions in IAM

Adding to `grc-service.json` is not enough — the permission must also exist as a `ServicePermission` record in the IAM database. This is the record that gets attached to roles and ultimately ends up in the JWT.

### How to register (run once per environment)

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission

grc = Service.objects.get(name='grc-service')

# Add as many permissions as needed — get_or_create is idempotent
permissions = [
    {
        'permission_code': 'grc:audit_meeting:manage',
        'name': 'Manage Audit Meetings',
        'description': 'Schedule and manage audit meetings (entry, pre-exit, exit)',
        'resource_type': 'audit_meeting',
        'action': 'manage',
        'category': 'audit',
        'is_active': True,
    },
    {
        'permission_code': 'grc:audit_meeting:view',
        'name': 'View Audit Meetings',
        'description': 'Read-only access to audit meeting records',
        'resource_type': 'audit_meeting',
        'action': 'view',
        'category': 'audit',
        'is_active': True,
    },
]

for p in permissions:
    obj, created = ServicePermission.objects.get_or_create(
        service=grc,
        permission_code=p['permission_code'],
        defaults={k: v for k, v in p.items() if k != 'permission_code'},
    )
    print(f'  {p[\"permission_code\"]}: {\"CREATED\" if created else \"ALREADY EXISTS\"}')
"
```

### Verify a permission exists

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission
grc = Service.objects.get(name='grc-service')
perms = ServicePermission.objects.filter(service=grc).values_list('permission_code', flat=True)
for p in sorted(perms):
    print(p)
"
```

---

## 5. Step 3 — Assign Permissions to Roles

Once a `ServicePermission` record exists in IAM, assign it to the appropriate roles using `RolePermission`.

### Roles available in FIMS (GRC module)

| Role code | Name | SRS Actor |
|---|---|---|
| `internal_auditor` | Internal Auditor / Lead Auditor | LA + IA team — does the work |
| `chief_internal_auditor` | Chief Internal Auditor | CIA — approves everything |
| `audit_committee` | Audit Committee | Reviews and approves strategic outputs |
| `management` | Management | Reviews and monitors |
| `auditee` | Auditee | Responds to findings; views limited data |
| `director_general` | Director General | Approves audit memos |
| `commission` | Commission | Notes quarterly reports |

### How to assign permissions to roles

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

grc = Service.objects.get(name='grc-service')

# Map: role_code → list of permission codes to assign
assignments = {
    'internal_auditor': [
        'grc:audit_meeting:manage',
        'grc:audit_working_paper:manage',
        'grc:audit_working_paper:review',
    ],
    'chief_internal_auditor': [
        'grc:audit_meeting:view',          # CIA views but does NOT manage meetings
        'grc:audit_working_paper:review',
    ],
    'audit_committee': [
        'grc:audit_meeting:view',
    ],
}

for role_code, perm_codes in assignments.items():
    role = Role.objects.get(code=role_code, service=grc)
    for perm_code in perm_codes:
        try:
            perm = ServicePermission.objects.get(service=grc, permission_code=perm_code)
            rp, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
            print(f'  [{role_code}] {perm_code}: {\"CREATED\" if created else \"ALREADY EXISTS\"}')
        except ServicePermission.DoesNotExist:
            print(f'  ERROR: {perm_code} not found in IAM — register it first (Step 2)')

print('Done. Users must log out and back in for JWT to refresh.')
"
```

### How to REVOKE a permission from a role

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

grc = Service.objects.get(name='grc-service')
role = Role.objects.get(code='chief_internal_auditor', service=grc)
perm = ServicePermission.objects.get(service=grc, permission_code='grc:audit_meeting:manage')

deleted, _ = RolePermission.objects.filter(role=role, service_permission=perm).delete()
print(f'Revoked: {deleted} row(s) deleted')
"
```

> **After any IAM change:** users must log out and back in. The JWT is issued at login time and is not updated until a new token is issued.

---

## 6. Step 4 — Backend Enforcement (Django Views)

### 6.1 The Middleware (already set up — do not change)

`JWTPermissionMiddleware` in `grc-service/apps/core/permission_middleware.py` runs on every request and sets `request.grc_permissions`. It is registered in `config/settings.py`:

```python
MIDDLEWARE = [
    ...
    "apps.core.permission_middleware.JWTPermissionMiddleware",
    ...
]
```

You never need to touch this. It does three things:
1. Decodes the JWT (locally, no IAM call)
2. Validates the user has access to `grc-service` (checks the `services` list in JWT)
3. Sets `request.grc_permissions` to the list of `grc:*` codes from the token

### 6.2 Define a Permission Class

**File:** `grc-service/apps/api/permissions_jwt.py`

For every new permission code you define, add a named class here:

```python
# ── My New Module ─────────────────────────────────────────────────────────────

class CanManageMyModule(BasePermission):
    """Check: grc:my_module:manage — create and update my module records."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:my_module:manage')


class CanViewMyModule(BasePermission):
    """Check: grc:my_module:view — read-only access to my module."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:my_module:view')
```

> There are also generic classes for one-off use:
> - `HasPermission('grc:my_module:manage')` — single code check
> - `HasAnyPermission(['grc:a:view', 'grc:b:view'])` — any of these codes
> - `HasAllPermissions(['grc:a:view', 'grc:b:manage'])` — must have all

### 6.3 Enforce Permissions in a View

**The required pattern:** use `check_permissions()` with a GET/write split.

```python
from rest_framework.permissions import IsAuthenticated
from apps.api.permissions_jwt import CanManageMyModule, CanViewMyModule

class MyModuleListCreateView(APIView):
    permission_classes = [IsAuthenticated]  # First gate: must have a valid JWT

    def check_permissions(self, request):
        super().check_permissions(request)  # Always call super() first
        if request.method == 'GET':
            # Read: allow both viewers and managers
            can_view   = CanViewMyModule().has_permission(request, self)
            can_manage = CanManageMyModule().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:my_module:view or grc:my_module:manage required.',
                )
        else:
            # Write (POST): only managers
            if not CanManageMyModule().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:my_module:manage required.',
                )

    def get(self, request):
        ...

    def post(self, request):
        ...


class MyModuleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view   = CanViewMyModule().has_permission(request, self)
            can_manage = CanManageMyModule().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:my_module:view or :manage required.')
        else:
            # PATCH, PUT, DELETE — write only
            if not CanManageMyModule().has_permission(request, self):
                self.permission_denied(request, message='grc:my_module:manage required.')

    def get(self, request, pk):
        ...

    def patch(self, request, pk):
        ...

    def delete(self, request, pk):
        ...
```

### 6.4 Simple views (write-only endpoints — no GET)

For endpoints that are pure actions (no GET), put `permission_classes` directly:

```python
class MyModuleStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, CanManageMyModule]

    def post(self, request, pk):
        ...
```

Or using `check_permissions` for clarity:

```python
class MyModuleStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageMyModule().has_permission(request, self):
            self.permission_denied(request, message='grc:my_module:manage required.')
```

### 6.5 Views with special combined logic (referenced patterns)

**Pattern: write OR review both have access (Working Papers)**
```python
def check_permissions(self, request):
    super().check_permissions(request)
    if request.method == 'GET':
        if not (CanManageWorkingPaper().has_permission(request, self) or
                CanReviewWorkingPaper().has_permission(request, self) or
                CanManageAuditEngagement().has_permission(request, self)):
            self.permission_denied(request, message='...')
    else:
        if not CanManageWorkingPaper().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_working_paper:manage required.')
```

**Pattern: combined permissions to derive role context (Audit Plans)**

> Some views combine two booleans to infer a specific role (see frontend below),
> but this technique can also be used on the backend:
> `is_cia = can_manage and can_approve` — guard CIA-only actions this way.

---

## 7. Step 5 — Frontend Enforcement (React)

### 7.1 Add the permission code to the hook

**File:** `frontend/apps/staff-portal/src/hooks/useGRCPermissions.tsx`

Two things to update:

**A) Add to `ALL_GRC_PERMISSION_CODES` array:**
```typescript
const ALL_GRC_PERMISSION_CODES: Array<keyof GRCPermissions> = [
  ...
  'grc:my_module:manage',   // ← add
  'grc:my_module:view',     // ← add
];
```

**B) Add convenience booleans at the bottom of `useGRCPermissions()`:**
```typescript
return {
  ...
  // My Module
  canManageMyModule: hasPermission('grc:my_module:manage'),
  canViewMyModule:   hasPermission('grc:my_module:view'),
};
```

### 7.2 Add the type

**File:** `frontend/apps/staff-portal/src/types/grc.ts`

```typescript
export interface GRCPermissions {
  ...
  'grc:my_module:manage': boolean;
  'grc:my_module:view':   boolean;
}
```

### 7.3 Use in a page/component

```typescript
import { useGRCPermissions } from '@staff/hooks/useGRCPermissions';

export function MyModulePage() {
  const { canManageMyModule } = useGRCPermissions();

  return (
    <div>
      {/* Show "Create" button only for managers */}
      {canManageMyModule && (
        <Button onClick={handleCreate}>Create Record</Button>
      )}

      <DataTable
        data={records}
        // Pass undefined to hide Edit/Delete actions for non-managers
        onEdit={canManageMyModule ? handleEdit : undefined}
        onDelete={canManageMyModule ? handleDelete : undefined}
      />
    </div>
  );
}
```

### 7.4 Combined permission logic (advanced)

```typescript
const { canManagePlans, canApprovePlans } = useGRCPermissions();

// Derived role flags
const canDraftPlans   = canManagePlans && !canApprovePlans;  // IA only
const canImprovePlans = canManagePlans && canApprovePlans;   // CIA only

// Only IA sees the "Submit for Approval" button:
{canDraftPlans && <Button>Submit for Approval</Button>}

// Only CIA sees "Request Improvement":
{canImprovePlans && <Button>Request Improvement</Button>}
```

### 7.5 How permissions reach the frontend

```
IAM issues JWT on login
  └── JWT payload contains { permissions_flat: ["grc:audit_meeting:manage", ...] }

Browser stores JWT in localStorage as "accessToken"

tokenUtils.getPermissionsFromToken()
  └── reads localStorage.getItem("accessToken")
  └── base64-decodes the JWT payload
  └── returns payload.permissions_flat → string[]

buildPermissionsFromToken()  (inside useGRCPermissions)
  └── for each code in ALL_GRC_PERMISSION_CODES:
       permissions[code] = isSuperuser || tokenPermissions.includes(code)

useGRCPermissions() returns:
  └── canManageMeetings: permissions['grc:audit_meeting:manage']  ← true/false
```

> **Important:** The frontend reads the JWT from `localStorage` — it does **not** call IAM to re-validate. This means if IAM permissions change, the user must log out and log back in. There is no way to invalidate the frontend token in real time.

---

## 8. Roles Reference

### Who has what — full GRC permission matrix

| Permission | internal_auditor | chief_internal_auditor | audit_committee | management | auditee | director_general | commission |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `grc:audit_universe:view` | ✅ | ✅ | — | — | — | — | — |
| `grc:audit_universe:manage` | ✅ | — | — | — | — | — | — |
| `grc:audit_universe:approve` | — | ✅ | — | — | — | — | — |
| `grc:risk_assessment:conduct` | ✅ | — | — | — | — | — | — |
| `grc:risk_assessment:review` | — | ✅ | — | — | — | — | — |
| `grc:audit_plan:view` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| `grc:audit_plan:manage` | ✅ | ✅ | — | — | — | — | — |
| `grc:audit_plan:approve` | — | ✅ | ✅ | — | — | — | ✅ |
| `grc:audit_engagement:manage` | ✅ | ✅ | — | — | — | — | — |
| `grc:audit_working_paper:manage` | ✅ | — | — | — | — | — | — |
| `grc:audit_working_paper:review` | ✅ | ✅ | — | — | — | — | — |
| `grc:audit_finding:manage` | ✅ | — | — | — | — | — | — |
| `grc:audit_finding:respond` | — | — | — | — | ✅ | — | — |
| `grc:audit_report:view` | ✅ | ✅ | ✅ | ✅ | — | ✅ | — |
| `grc:audit_report:approve` | — | ✅ | ✅ | — | — | — | — |
| `grc:audit_meeting:manage` | ✅ | — | — | — | — | — | — |
| `grc:audit_meeting:view` | — | ✅ | ✅ | — | — | — | — |
| `grc:audit_monitoring:update` | ✅ | — | — | ✅ | ✅ | — | — |
| `grc:audit_dashboard:view` | ✅ | ✅ | ✅ | ✅ | — | ✅ | — |
| `grc:quarterly_report:manage` | ✅ | ✅ | — | — | — | — | — |
| `grc:quarterly_report:approve` | — | ✅ | ✅ | ✅ | — | — | ✅ |
| `grc:audit_memo:view` | ✅ | ✅ | — | — | — | ✅ | — |
| `grc:audit_memo:manage` | ✅ | ✅ | — | — | — | — | — |
| `grc:audit_memo:approve` | — | — | — | — | — | ✅ | — |
| `grc:audit_declaration:manage` | ✅ | ✅ | — | — | — | — | — |
| `grc:audit_declaration:sign` | ✅ | — | — | — | — | — | — |
| `grc:config:system:manage` | — | ✅ | — | — | — | — | — |

### Test users (dev/staging)

| Email | Role |
|---|---|
| `cia@fcc.go.tz` | `chief_internal_auditor` |
| `auditor@fcc.go.tz` | `internal_auditor` (acts as Lead Auditor) |
| `teammember@fcc.go.tz` | `internal_auditor` (acts as Audit Team Member) |
| `auditcommittee@fcc.go.tz` | `audit_committee` |
| `management@fcc.go.tz` | `management` |
| `auditee@fcc.go.tz` | `auditee` |
| `dg@fcc.go.tz` | `director_general` |
| `commission@fcc.go.tz` | `commission` |
| **Password for all:** | `Pass@1234` |

---

## 9. Permission Code Master List

All currently registered GRC permission codes:

```
grc:audit_universe:view
grc:audit_universe:manage
grc:audit_universe:approve
grc:risk_assessment:conduct
grc:risk_assessment:review
grc:audit_plan:view
grc:audit_plan:manage
grc:audit_plan:approve
grc:audit_engagement:manage
grc:audit_working_paper:manage
grc:audit_working_paper:review
grc:audit_finding:manage
grc:audit_finding:respond
grc:audit_report:view
grc:audit_report:approve
grc:audit_monitoring:update
grc:audit_dashboard:view
grc:config:fiscal_year:manage
grc:config:audit_severity:manage
grc:config:finding_type:manage
grc:config:risk_rating:manage
grc:config:system:manage
grc:audit_memo:view
grc:audit_memo:manage
grc:audit_memo:approve
grc:audit_declaration:manage
grc:audit_declaration:sign
grc:audit_survey:manage
grc:audit_rcm:manage
grc:audit_rcm:approve
grc:audit_program:manage
grc:engagement_notification:manage
grc:engagement_notification:approve
grc:quarterly_report:manage
grc:quarterly_report:approve
grc:audit_meeting:manage
grc:audit_meeting:view
```

---

## 10. Complete Worked Example: Adding RBAC for a New Module

> **Scenario:** Implementing an "Audit Recommendation" module. Lead Auditor raises recommendations; CIA reviews and closes them.
>
> **Note:** The codes used here (`grc:audit_recommendation:manage`, `:review`) do **not** yet exist in the codebase — that is intentional so every step produces a real `CREATED` result rather than `ALREADY EXISTS`.

### Step A — `grc-service.json`

Add to the `permissions` array:

```json
{
  "permission_code": "grc:audit_recommendation:manage",
  "name": "Manage Audit Recommendations",
  "description": "Create, update, and submit audit recommendations",
  "resource_type": "audit_recommendation",
  "action": "manage",
  "category": "audit_recommendation"
},
{
  "permission_code": "grc:audit_recommendation:review",
  "name": "Review Audit Recommendations",
  "description": "CIA review and close audit recommendations",
  "resource_type": "audit_recommendation",
  "action": "review",
  "category": "audit_recommendation"
}
```

### Step B — IAM: register permissions (run once)

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission

grc = Service.objects.get(name='grc-service')

new_perms = [
    {
        'permission_code': 'grc:audit_recommendation:manage',
        'name': 'Manage Audit Recommendations',
        'description': 'Create, update, and submit audit recommendations',
        'resource_type': 'audit_recommendation',
        'action': 'manage',
        'category': 'audit_recommendation',
        'is_active': True,
    },
    {
        'permission_code': 'grc:audit_recommendation:review',
        'name': 'Review Audit Recommendations',
        'description': 'CIA review and close audit recommendations',
        'resource_type': 'audit_recommendation',
        'action': 'review',
        'category': 'audit_recommendation',
        'is_active': True,
    },
]

for p in new_perms:
    obj, created = ServicePermission.objects.get_or_create(
        service=grc,
        permission_code=p['permission_code'],
        defaults={k: v for k, v in p.items() if k != 'permission_code'},
    )
    print(f'  {p[\"permission_code\"]}: {\"CREATED\" if created else \"ALREADY EXISTS\"}')
"
# Expected output:
#   grc:audit_recommendation:manage: CREATED
#   grc:audit_recommendation:review: CREATED
```

### Step C — IAM: assign to roles

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

grc = Service.objects.get(name='grc-service')
perm_manage = ServicePermission.objects.get(service=grc, permission_code='grc:audit_recommendation:manage')
perm_review = ServicePermission.objects.get(service=grc, permission_code='grc:audit_recommendation:review')

assignments = {
    'internal_auditor':      [perm_manage],           # LA raises recommendations
    'chief_internal_auditor': [perm_manage, perm_review],  # CIA can also manage + review
}

for role_code, perms in assignments.items():
    role = Role.objects.get(code=role_code, service=grc)
    for perm in perms:
        rp, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
        print(f'  [{role_code}] {perm.permission_code}: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

print('Done. Users must log out and back in for JWT to refresh.')
"
# Expected output:
#   [internal_auditor] grc:audit_recommendation:manage: CREATED
#   [chief_internal_auditor] grc:audit_recommendation:manage: CREATED
#   [chief_internal_auditor] grc:audit_recommendation:review: CREATED
```

### Step D — `permissions_jwt.py`

```python
# grc-service/apps/api/permissions_jwt.py

class CanManageAuditRecommendation(BasePermission):
    """Check: grc:audit_recommendation:manage — create and update recommendations."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_recommendation:manage')


class CanReviewAuditRecommendation(BasePermission):
    """Check: grc:audit_recommendation:review — CIA review/close recommendations."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_recommendation:review')
```

### Step E — View (`audit_recommendation_views.py`)

```python
from apps.api.permissions_jwt import CanManageAuditRecommendation, CanReviewAuditRecommendation

class AuditRecommendationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            # Both managers and reviewers can read
            can_manage = CanManageAuditRecommendation().has_permission(request, self)
            can_review = CanReviewAuditRecommendation().has_permission(request, self)
            if not (can_manage or can_review):
                self.permission_denied(
                    request,
                    message='grc:audit_recommendation:manage or :review required.',
                )
        else:
            # Only managers can create
            if not CanManageAuditRecommendation().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:audit_recommendation:manage required.',
                )

    def get(self, request):
        ...

    def post(self, request):
        ...


class AuditRecommendationReviewView(APIView):
    """CIA-only endpoint — closes / returns a recommendation."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanReviewAuditRecommendation().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_recommendation:review required.')

    def post(self, request, pk):
        ...
```

### Step F — Frontend type (`types/grc.ts`)

```typescript
export interface GRCPermissions {
  // ... existing codes ...
  // Audit Recommendations
  'grc:audit_recommendation:manage': boolean;
  'grc:audit_recommendation:review': boolean;
}
```

### Step G — Frontend hook (`useGRCPermissions.tsx`)

```typescript
// 1. Add to ALL_GRC_PERMISSION_CODES:
const ALL_GRC_PERMISSION_CODES: Array<keyof GRCPermissions> = [
  // ... existing codes ...
  'grc:audit_recommendation:manage',
  'grc:audit_recommendation:review',
];

// 2. Add convenience booleans to the return object:
return {
  // ... existing booleans ...
  // Recommendations
  canManageRecommendations: hasPermission('grc:audit_recommendation:manage'),
  canReviewRecommendations: hasPermission('grc:audit_recommendation:review'),
};
```

### Step H — Frontend usage

```typescript
const { canManageRecommendations, canReviewRecommendations } = useGRCPermissions();

// Only LA sees the "Raise Recommendation" button:
{canManageRecommendations && (
  <Button onClick={handleCreate}>Raise Recommendation</Button>
)}

// Only CIA sees the "Close Recommendation" action:
{canReviewRecommendations && (
  <Button onClick={handleClose}>Close</Button>
)}
```

---

## 11. Ownership Guards (Row-Level Access Control)

Service-level permissions (`CanManageAuditMeeting`) grant access to the endpoint.
**Ownership guards** restrict individual records — e.g. only the user who created a record can edit or delete it.

### Pattern

```python
def patch(self, request, pk):
    meeting = get_object_or_404(AuditMeeting, pk=pk)

    # Ownership check: only the organizer can edit
    organizer_id = str(meeting.organized_by) if meeting.organized_by else None
    if str(request.user_id) != organizer_id:
        return Response(
            {
                'success': False,
                'error': {
                    'message': 'Only the meeting organizer can edit this meeting.',
                    'code': 'MEETING_NOT_ORGANIZER',
                },
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # Continue with update...
```

### When to use ownership guards

| Scenario | Use ownership guard? |
|---|---|
| Only the creator should edit/delete | ✅ Yes |
| Only the preparer can submit their own WP for review | ✅ Yes |
| Any user with `manage` permission can edit any record | ❌ No — permission class sufficient |
| CIA can approve anyone's records | ❌ No — permission class sufficient |

### Ownership guard with superuser bypass

```python
# Superusers bypass ownership guards
if not request.is_superuser and str(request.user_id) != organizer_id:
    return Response({'error': {'code': 'NOT_ORGANIZER'}}, status=403)
```

---

## 12. Cross-Service Permissions (WO, DRS)

GRC roles need permissions in **other services** for cross-service calls to work. These are assigned to GRC roles but registered under the target service.

### Work Orchestration Service (WO)

Required for any role that submits or acts on workflows:

| Permission | Who needs it |
|---|---|
| `workflow:plan:create` | `internal_auditor`, `chief_internal_auditor` |
| `workflow:plan:read` | Any role that views WO status |
| `workflow:stage:action` | Any role that approves/rejects/returns a stage |

```bash
# One-time setup — run in iam-service shell
wo = Service.objects.get(name='work-orchestration-service')
grc = Service.objects.get(name='grc-service')

for role_code in ['internal_auditor', 'chief_internal_auditor']:
    role = Role.objects.get(code=role_code, service=grc)
    for code in ['workflow:plan:create', 'workflow:plan:read', 'workflow:stage:action']:
        perm = ServicePermission.objects.get(service=wo, permission_code=code)
        RolePermission.objects.get_or_create(role=role, service_permission=perm)
```

### Document Records Service (DRS)

Required for roles that create or read documents via GRC:

| Permission | Who needs it |
|---|---|
| `document:document:create` | `internal_auditor` |
| `document:document:read` | `internal_auditor`, `chief_internal_auditor` |
| `document:classification:confidential` | `internal_auditor`, `chief_internal_auditor` |
| `document:document:read_confidential` | `internal_auditor`, `chief_internal_auditor` |

> These permissions appear in the **DRS section** of the JWT, not the GRC section. DRS validates them directly against the JWT. If missing, DRS returns 403 → GRC returns 502 → API Gateway converts to 503. The error message will look like a GRC service error but the real cause is a missing DRS permission in IAM.

---

## 13. Checklist for New Module RBAC

Use this checklist every time you add RBAC to a new GRC module:

### IAM / Backend setup (one-time per environment)
- [ ] Define permission codes following the `{service}:{resource}:{action}` convention
- [ ] Add entries to `grc-service/config/permissions/grc-service.json`
- [ ] Register `ServicePermission` records in IAM (`get_or_create`, idempotent)
- [ ] Assign `RolePermission` records to the correct roles in IAM
- [ ] Verify with: decode a fresh JWT and check `permissions_flat` contains the new codes

### Backend code
- [ ] Add `CanManageXxx` class to `apps/api/permissions_jwt.py`
- [ ] Add `CanViewXxx` class to `apps/api/permissions_jwt.py` (if a read-only role exists)
- [ ] In each view class: add `permission_classes = [IsAuthenticated]`
- [ ] Split `check_permissions()` by HTTP method — GET allows view OR manage; write allows manage only
- [ ] Add ownership guards in the view handler body where record-level isolation is needed
- [ ] Return `403` with a meaningful `code` string (e.g. `'NOT_OWNER'`, `'MEETING_NOT_ORGANIZER'`) so frontend can show a specific message

### Frontend code
- [ ] Add new codes to `ALL_GRC_PERMISSION_CODES` in `useGRCPermissions.tsx`
- [ ] Add convenience booleans to the return object (`canManageXxx`, `canViewXxx`)
- [ ] Add the codes to the `GRCPermissions` TypeScript interface in `types/grc.ts`
- [ ] Use the booleans in the page component to show/hide buttons and actions
- [ ] Pass `undefined` (not `false`) to `onEdit` / `onDelete` props to fully hide actions

### After deployment
- [ ] All affected users log out and back in (JWT must be re-issued)
- [ ] Test the full matrix: table below lists which users should get 200 vs 403

---

## 14. Common Pitfalls and Fixes

### Pitfall 1: Permission in code but not in IAM — silent 403

**Symptom:** A user with the right role always gets 403 for a new feature, even though the view code looks correct.

**Cause:** The `ServicePermission` record does not exist in IAM. The IAM service never added this permission to the role when it built the JWT.

**Fix:** Run the Step 2 registration script (Section 4). Then have the user log out and back in.

**How to confirm:**
```bash
# Decode the user's JWT and check permissions_flat:
python3 -c "
import json, base64, sys
token = 'paste_jwt_here'
payload = token.split('.')[1]
payload += '=' * (4 - len(payload) % 4)
d = json.loads(base64.b64decode(payload))
grc = [p for p in d.get('permissions_flat',[]) if 'meeting' in p]
print(grc)
"
```

---

### Pitfall 2: Single permission class for all methods — view-only roles blocked from GET

**Symptom:** CIA or audit_committee can't view any records — they get 403 everywhere.

**Cause:** The view's `check_permissions()` checks `CanManageXxx` for ALL methods including GET.

**Wrong pattern:**
```python
def check_permissions(self, request):
    super().check_permissions(request)
    if not CanManageAuditMeeting().has_permission(request, self):  # ← blocks CIA on GET
        self.permission_denied(...)
```

**Correct pattern:**
```python
def check_permissions(self, request):
    super().check_permissions(request)
    if request.method == 'GET':
        if not (CanViewAuditMeeting().has_permission(request, self) or
                CanManageAuditMeeting().has_permission(request, self)):
            self.permission_denied(...)
    else:
        if not CanManageAuditMeeting().has_permission(request, self):
            self.permission_denied(...)
```

---

### Pitfall 3: `request.grc_permissions` not set — middleware not running

**Symptom:** Error: `request.grc_permissions not found`; every request denied.

**Cause:** `JWTPermissionMiddleware` is not in `MIDDLEWARE` or the import path is wrong.

**Check:** `grc-service/config/settings.py` must contain:
```python
"apps.core.permission_middleware.JWTPermissionMiddleware",
```

---

### Pitfall 4: New permission code missing from the frontend hook array

**Symptom:** The backend allows the action; the button never appears in the UI.

**Cause:** The new permission code was added to `grc-service.json` and backend classes but not to `ALL_GRC_PERMISSION_CODES` in `useGRCPermissions.tsx`. The hook silently ignores unknown codes and defaults them to `false`.

**Fix:** Add the code to both `ALL_GRC_PERMISSION_CODES` and the return object of `useGRCPermissions`.

---

### Pitfall 5: `stamped_document_url` or `document_id` always null even after stamp

This is not a permission bug but is usually diagnosed alongside one. The root cause in 100% of observed cases is calling the DRS stamp from a Kafka consumer (no JWT). See `PDF_GENERATION_STAMP_DOWNLOAD_REFERENCE.md` — Critical Lesson section.

---

### Pitfall 6: User JWTs are cached — changes not reflected

**Symptom:** IAM changes show correct permissions in IAM DB but user still gets 403.

**Cause:** The JWT is issued at login and stored in `localStorage`. Changes to IAM do not update existing tokens.

**Fix:** User must log out and log back in. There is no server-side invalidation in the current architecture (tokens are validated locally).

---

### Pitfall 7: Two internal_auditor users — WO self-approval guard

**Symptom:** Same user submits a WP and then tries to approve it in Stage 1 — gets a WO self-approval error.

**Cause:** WO has a guard that prevents the submitter from approving their own workflow stage.

**Fix:** Use two different `internal_auditor` users. `teammember@fcc.go.tz` submits; `auditor@fcc.go.tz` (LA) approves Stage 1. CIA approves Stage 2.

---

## 15. Debugging Guide

### Step 1 — Check what permissions are in the user's JWT

```bash
# Replace with the actual token from browser DevTools → Application → localStorage → accessToken
python3 -c "
import json, base64
token = 'PASTE_TOKEN_HERE'
payload = token.split('.')[1]
payload += '=' * (4 - len(payload) % 4)
d = json.loads(base64.b64decode(payload))
print('services:', d.get('services'))
print('is_superuser:', d.get('is_superuser'))
print()
print('grc permissions:')
for p in sorted(d.get('permissions_flat', [])):
    if p.startswith('grc:'):
        print(' ', p)
"
```

### Step 2 — Check what permissions IAM has assigned to a role

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, Role, RolePermission

grc = Service.objects.get(name='grc-service')
role = Role.objects.get(code='chief_internal_auditor', service=grc)
perms = RolePermission.objects.filter(role=role).select_related('service_permission')
print(f'Permissions for {role.name}:')
for rp in sorted(perms, key=lambda x: x.service_permission.permission_code):
    print(f'  {rp.service_permission.permission_code}')
"
```

### Step 3 — Check what the GRC backend sees for a specific request

Add a temporary `print` in the view or check GRC service logs:

```bash
docker logs fims-grc-service --tail=100 -f | grep -i "permission\|denied\|granted\|403"
```

The middleware logs at DEBUG level:
- `Permission granted: user=auditor@fcc.go.tz, permission=grc:audit_meeting:manage`
- `Permission denied: user=cia@fcc.go.tz, required=grc:audit_meeting:manage, available=[...]`

### Step 4 — Verify IAM has the permission registered at all

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission
grc = Service.objects.get(name='grc-service')
exists = ServicePermission.objects.filter(service=grc, permission_code='grc:audit_meeting:manage').exists()
print('Exists in IAM:', exists)
"
```

### Step 5 — Full permission check for a specific user

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.services import UnifiedPermissionResolutionService
from apps.users.models import User

user = User.objects.get(email='cia@fcc.go.tz')
data = UnifiedPermissionResolutionService.get_user_permissions(user)
print('services:', data.get('services', []))
print()
print('grc permissions in JWT:')
for p in sorted(data.get('permissions_flat', [])):
    if 'grc' in p:
        print(' ', p)
"
```

### Step 6 — Force-refresh a user's JWT (have them log out and back in via API)

There is no server-side token refresh. The only fix is for the user to log out (which clears `localStorage`) and log back in to get a fresh JWT.

---

## Summary: The 6-file RBAC touch points

For every new permission, you touch exactly these 6 files:

| # | File | What you add |
|---|---|---|
| 1 | `grc-service/config/permissions/grc-service.json` | New permission code entry |
| 2 | IAM shell (one-time setup) | `ServicePermission` + `RolePermission` records |
| 3 | `grc-service/apps/api/permissions_jwt.py` | `CanXxx(BasePermission)` class |
| 4 | `grc-service/apps/api/views/{module}_views.py` | `check_permissions()` split by method |
| 5 | `frontend/apps/staff-portal/src/hooks/useGRCPermissions.tsx` | Code in array + boolean in return |
| 6 | `frontend/apps/staff-portal/src/types/grc.ts` | Code added to `GRCPermissions` interface |



**NOTE:
THIS GUIDE IS FOR REFERENCE ONLY. IF A TASK REQUIRES NEW ROLES OR PERMISSIONS, THEY SHOULD BE CREATED SPECIFICALLY ACCORDING TO THE REQUIREMENTS OF THAT TASK. BUT THEY SHOULD FOLLOW THE SAME EXISTING PATTERN AS DEFINED IN OTHER PARTS.
AND REFERENCE COMMANDS, USERS, AND SETUP ARE EXPLAINED IN THE FILE (grc-service/implementation/my_implementation/grc/notes/grc_notes.md) FROM LINE 1 TO 550 **


**NOTE:
THIS GUIDE IS FOR REFERENCE ONLY. IF A TASK REQUIRES NEW ROLES OR PERMISSIONS, THEY SHOULD BE CREATED SPECIFICALLY ACCORDING TO THE REQUIREMENTS OF THAT TASK. BUT THEY SHOULD FOLLOW THE SAME EXISTING PATTERN AS DEFINED IN OTHER PARTS.
AND REFERENCE COMMANDS, USERS, AND SETUP ARE EXPLAINED IN THE FILE (grc-service/implementation/my_implementation/grc/notes/grc_notes.md) FROM LINE 1 TO 550 **


**NOTE:
THIS GUIDE IS FOR REFERENCE ONLY. IF A TASK REQUIRES NEW ROLES OR PERMISSIONS, THEY SHOULD BE CREATED SPECIFICALLY ACCORDING TO THE REQUIREMENTS OF THAT TASK. BUT THEY SHOULD FOLLOW THE SAME EXISTING PATTERN AS DEFINED IN OTHER PARTS.
AND REFERENCE COMMANDS, USERS, AND SETUP ARE EXPLAINED IN THE FILE (grc-service/implementation/my_implementation/grc/notes/grc_notes.md) FROM LINE 1 TO 550 **