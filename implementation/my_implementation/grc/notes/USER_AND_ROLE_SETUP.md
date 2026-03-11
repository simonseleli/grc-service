# FIMS GRC — User & Role Setup Guide

This document explains how to create users and assign GRC roles so they can interact with the system. It covers the full flow from architecture to hands-on commands.

---

## Architecture: How Auth Works End-to-End

```
Browser/Client
    │
    ▼
API Gateway (NGINX :8080)
    │  forwards request + Authorization header
    ▼
GRC Service (:8006)
    │  reads JWT → extracts user_id
    │  calls IAM /api/v1/introspect/
    ▼
IAM Service (:8000)
    │  looks up user → user's roles → roles' permission_codes
    │  returns: { user_id, permissions: ["grc:audit_plan:approve", ...] }
    ▼
GRC Service
    │  checks if required permission_code is in the returned list
    │  grants or denies access to the view
```

**Key points:**
- JWT is HS256, signed with `JWT_SECRET_KEY` (shared across all services)
- The JWT only carries `user_id` — it does NOT embed permissions
- Every protected GRC request triggers a live IAM introspect call
- Permission codes like `grc:audit_plan:approve` live in IAM's `unified_service_permissions` table, linked to Roles via `role_permissions`, linked to Users via `user_roles`

---

## Database Tables Involved (IAM)

| Table | Purpose |
|---|---|
| `users` | All user accounts |
| `unified_services` | Registered microservices (grc-service, iam-service, etc.) |
| `unified_service_permissions` | Granular permission codes per service |
| `roles` | Role definitions (linked to a service or IAM-global) |
| `role_permissions` | Links roles ↔ permissions (supports both Django + service permissions) |
| `user_roles` | Links users ↔ roles |

---

## GRC Roles (defined in `grc-service/config/permissions/grc-service.json`)

| Role Code | Display Name | SRS Actor | What They Do |
|---|---|---|---|
| `chief_internal_auditor` | Chief Internal Auditor | CIA | Approves audit universe, audit plan, programs, reports, memos |
| `internal_auditor` | Lead Auditor (LA/IA) | IA | Conducts risk assessments, creates engagements, working papers, findings |
| `audit_committee` | Audit Committee | AC | Reviews and approves plan + reports strategically |
| `management` | Management | Management | Reviews RBIAP, monitors implementation |
| `auditee` | Auditee | HOD/Department | Responds to findings, updates implementation status |

These roles are curated inside IAM (not auto-created by Kafka). You must create them manually using the steps below.

---

## Permission Codes in IAM (34 total)

> These were published automatically by `grc-service` on startup via Kafka → IAM's `consume_unified_permissions` consumer stored them.

```
grc:audit_universe:view          grc:audit_universe:manage        grc:audit_universe:approve
grc:risk_assessment:conduct      grc:risk_assessment:review
grc:audit_plan:view              grc:audit_plan:manage            grc:audit_plan:approve
grc:audit_engagement:manage
grc:audit_memo:view              grc:audit_memo:manage
grc:audit_declaration:manage     grc:audit_declaration:sign
grc:audit_survey:manage
grc:audit_rcm:manage             grc:audit_rcm:approve
grc:audit_program:manage
grc:engagement_notification:manage   grc:engagement_notification:approve
grc:audit_working_paper:manage   grc:audit_working_paper:review
grc:audit_finding:manage         grc:audit_finding:respond
grc:audit_report:view            grc:audit_report:approve
grc:audit_monitoring:update
grc:quarterly_report:manage      grc:quarterly_report:approve
grc:audit_dashboard:view
grc:config:fiscal_year:manage    grc:config:audit_severity:manage
grc:config:finding_type:manage   grc:config:risk_rating:manage    grc:config:system:manage
```

---

## Step-by-Step Setup

### Prerequisites

All services must be running:
```bash
cd /home/simons/Coding/FIMS
./test-start.sh
```

---

### Step 1 — Create GRC Roles in IAM

Open the IAM Django shell:
```bash
docker exec -it fims-iam-service python manage.py shell
```

Run:
```python
from apps.roles.models import Role, Service

grc = Service.objects.get(name='grc-service')

roles_data = [
    ('chief_internal_auditor', 'Chief Internal Auditor',
     'Approves audit universe, plans, programs, memos, and reports'),
    ('internal_auditor',       'Internal Auditor / Lead Auditor',
     'Conducts risk assessments, manages engagements and working papers'),
    ('audit_committee',        'Audit Committee',
     'Reviews and approves strategic audit outputs'),
    ('management',             'Management',
     'Reviews RBIAP, monitors audit implementation'),
    ('auditee',                'Auditee',
     'Responds to audit findings and updates implementation status'),
]

for code, name, desc in roles_data:
    role, created = Role.objects.get_or_create(
        code=code,
        service=grc,
        defaults={
            'name': name,
            'description': desc,
            'is_system': True,
            'is_active': True,
        }
    )
    print(f"{'Created' if created else 'Already exists'}: [{code}] {name}")
```

---

### Step 2 — Assign Permissions to Each Role

Still in the IAM shell:
```python
from apps.roles.models import Role, Service, RolePermission, ServicePermission

grc = Service.objects.get(name='grc-service')

role_permission_map = {
    'internal_auditor': [
        'grc:audit_universe:view', 'grc:audit_universe:manage',
        'grc:risk_assessment:conduct',
        'grc:audit_plan:view', 'grc:audit_plan:manage',
        'grc:audit_engagement:manage',
        'grc:audit_memo:view', 'grc:audit_memo:manage',
        'grc:audit_declaration:manage', 'grc:audit_declaration:sign',
        'grc:audit_survey:manage',
        'grc:audit_rcm:manage', 'grc:audit_rcm:approve',
        'grc:audit_program:manage',
        'grc:engagement_notification:manage',
        'grc:audit_working_paper:manage', 'grc:audit_working_paper:review',
        'grc:audit_finding:manage',
        'grc:audit_report:view',
        'grc:audit_monitoring:update',
        'grc:quarterly_report:manage',
        'grc:audit_dashboard:view',
    ],
    'chief_internal_auditor': [
        'grc:audit_universe:view', 'grc:audit_universe:approve',
        'grc:risk_assessment:review',
        'grc:audit_plan:view', 'grc:audit_plan:manage', 'grc:audit_plan:approve',
        'grc:audit_engagement:manage',
        'grc:audit_memo:view', 'grc:audit_memo:manage',
        'grc:audit_declaration:manage',
        'grc:audit_survey:manage',
        'grc:audit_rcm:manage', 'grc:audit_rcm:approve',
        'grc:audit_program:manage',
        'grc:engagement_notification:manage', 'grc:engagement_notification:approve',
        'grc:audit_working_paper:review',
        'grc:audit_report:view', 'grc:audit_report:approve',
        'grc:quarterly_report:manage', 'grc:quarterly_report:approve',
        'grc:audit_dashboard:view',
        'grc:config:fiscal_year:manage', 'grc:config:audit_severity:manage',
        'grc:config:finding_type:manage', 'grc:config:risk_rating:manage',
        'grc:config:system:manage',
    ],
    'audit_committee': [
        'grc:audit_plan:view', 'grc:audit_plan:approve',
        'grc:audit_memo:view',
        'grc:audit_report:view', 'grc:audit_report:approve',
        'grc:quarterly_report:approve',
        'grc:audit_dashboard:view',
    ],
    'management': [
        'grc:audit_plan:view',
        'grc:audit_report:view',
        'grc:audit_monitoring:update',
        'grc:quarterly_report:approve',
        'grc:audit_dashboard:view',
    ],
    'auditee': [
        'grc:audit_plan:view',
        'grc:audit_finding:respond',
        'grc:audit_monitoring:update',
    ],
}

for role_code, perm_codes in role_permission_map.items():
    role = Role.objects.get(code=role_code, service=grc)
    assigned = 0
    for perm_code in perm_codes:
        try:
            perm = ServicePermission.objects.get(permission_code=perm_code, service=grc)
            _, created = RolePermission.objects.get_or_create(
                role=role,
                service_permission=perm,
            )
            if created:
                assigned += 1
        except ServicePermission.DoesNotExist:
            print(f"  ⚠  Permission not found: {perm_code}")
    print(f"✓ {role.name}: {assigned} new permissions assigned")
```

---

### Step 3 — Create Users

#### Option A: Django Shell (fastest for initial setup)

```bash
docker exec -it fims-iam-service python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()

# Change names/emails/employee_ids as needed
users_to_create = [
    {
        'email': 'cia@fcc.go.tz',
        'first_name': 'John',
        'last_name': 'Mbwana',
        'employee_id': 'FCC-CIA-001',
        'position': 'Chief Internal Auditor',
        'department': 'Internal Audit',
        'user_type': 'internal',
        'status': 'active',
        'is_active': True,
        'is_staff': True,
        'username': 'cia',
    },
    {
        'email': 'auditor@fcc.go.tz',
        'first_name': 'Mary',
        'last_name': 'Simba',
        'employee_id': 'FCC-IA-001',
        'position': 'Internal Auditor',
        'department': 'Internal Audit',
        'user_type': 'internal',
        'status': 'active',
        'is_active': True,
        'is_staff': True,
        'username': 'auditor',
    },
    {
        'email': 'auditcommittee@fcc.go.tz',
        'first_name': 'Paul',
        'last_name': 'Kamau',
        'employee_id': 'FCC-AC-001',
        'position': 'Audit Committee Member',
        'department': 'Board',
        'user_type': 'internal',
        'status': 'active',
        'is_active': True,
        'is_staff': True,
        'username': 'auditcommittee',
    },
    {
        'email': 'management@fcc.go.tz',
        'first_name': 'Grace',
        'last_name': 'Mwangi',
        'employee_id': 'FCC-MG-001',
        'position': 'Director',
        'department': 'Management',
        'user_type': 'internal',
        'status': 'active',
        'is_active': True,
        'is_staff': True,
        'username': 'management',
    },
    {
        'email': 'auditee@fcc.go.tz',
        'first_name': 'Ali',
        'last_name': 'Hassan',
        'employee_id': 'FCC-AE-001',
        'position': 'Head of Department',
        'department': 'Operations',
        'user_type': 'internal',
        'status': 'active',
        'is_active': True,
        'is_staff': False,
        'username': 'auditee',
    },
]

for data in users_to_create:
    user, created = User.objects.get_or_create(
        email=data['email'],
        defaults=data,
    )
    if created:
        user.set_password('Pass@1234')
        user.save()
        print(f"Created: {user.email}")
    else:
        print(f"Already exists: {user.email}")
```

#### Option B: REST API (for ongoing user management)

First, get an admin token:
```bash
curl -s -X POST http://localhost:8080/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@fcc.go.tz", "password": "admin123"}' | python3 -m json.tool
```

Then create a user:
```bash
TOKEN="<paste_access_token_here>"

curl -X POST http://localhost:8080/api/v1/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cia@fcc.go.tz",
    "first_name": "John",
    "last_name": "Mbwana",
    "employee_id": "FCC-CIA-001",
    "department": "Internal Audit",
    "position": "Chief Internal Auditor",
    "user_type": "internal",
    "status": "active",
    "is_active": true,
    "is_staff": true,
    "password": "Pass@1234",
    "password_confirm": "Pass@1234"
  }'
```

> **Through tunnel:** replace `http://localhost:8080` with `http://fims-staff.tunnel.ictpack.net`

---

### Step 4 — Assign Roles to Users

```bash
docker exec -it fims-iam-service python manage.py shell
```

```python
from apps.roles.models import Role, Service, UserRole
from django.contrib.auth import get_user_model
User = get_user_model()

grc = Service.objects.get(name='grc-service')

assignments = [
    ('cia@fcc.go.tz',            'chief_internal_auditor'),
    ('auditor@fcc.go.tz',        'internal_auditor'),
    ('auditcommittee@fcc.go.tz', 'audit_committee'),
    ('management@fcc.go.tz',     'management'),
    ('auditee@fcc.go.tz',        'auditee'),
]

for email, role_code in assignments:
    try:
        user = User.objects.get(email=email)
        role = Role.objects.get(code=role_code, service=grc)
        ua, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={'is_active': True}
        )
        print(f"{'Assigned' if created else 'Already has'}: {email} → {role.name}")
    except User.DoesNotExist:
        print(f"⚠  User not found: {email}")
    except Role.DoesNotExist:
        print(f"⚠  Role not found: {role_code} (run Step 1 first)")
```

---

### Step 5 — Verify Everything Is Correct

```bash
docker exec fims-iam-service python manage.py shell -c "
from apps.roles.models import Role, Service, UserRole, ServicePermission
from django.contrib.auth import get_user_model
User = get_user_model()

grc = Service.objects.get(name='grc-service')
roles = Role.objects.filter(service=grc)

print(f'GRC Roles: {roles.count()}')
for role in roles:
    perm_count = role.role_permissions.filter(service_permission__isnull=False).count()
    user_count = UserRole.objects.filter(role=role, is_active=True).count()
    print(f'  [{role.code}] {role.name} — {perm_count} perms, {user_count} users')

print()
print('User → Role assignments:')
for ua in UserRole.objects.filter(role__service=grc, is_active=True).select_related('user', 'role'):
    print(f'  {ua.user.email} → {ua.role.name}')
"
```

---

### Step 6 — Test Login for Each User

```bash
curl -s -X POST http://localhost:8080/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "cia@fcc.go.tz", "password": "Pass@1234"}' | python3 -m json.tool
```

You should get back an `access` and `refresh` JWT token. Use the access token as `Authorization: Bearer <token>` to call GRC endpoints.

---

## How Permissions Are Checked in GRC

The GRC service uses custom JWT permission classes in `grc-service/apps/api/permissions_jwt.py`. Each class maps to a permission code. Example:

```python
class CanApproveAuditPlan(BaseJWTPermission):
    """Check: grc:audit_plan:approve — CIA / committee approval of RBIAP."""
    required_permission = "grc:audit_plan:approve"
```

**Flow when a request arrives at GRC:**
1. GRC middleware extracts the JWT `access` token
2. Decodes it to get `user_id` (no DB hit yet)
3. Calls `GET /api/v1/introspect/` on IAM with the token
4. IAM returns the user's full permission list from `user_roles` → `role_permissions` → `unified_service_permissions`
5. GRC checks if `grc:audit_plan:approve` is in that list
6. Grants or denies

**Implication:** If you change a role's permissions or reassign a user's role in IAM, the effect is immediate on the next request — no restart needed.

---

## Admin User (Auto-created by IAM)

The admin user is automatically created by `iam-service/apps/core/signals.py` after migrations run, using values from `.env`:

| Field | Value from `.env` |
|---|---|
| Email | `admin@fcc.go.tz` |
| Password | `admin123` |
| Username | `admin` |
| Type | `internal` superuser |

> **Change the admin password in production** — edit `IAM_SUPERUSER_PASSWORD` in `iam-service/.env` before first deploy.

---

## Quick Reference Commands

| Action | Command |
|---|---|
| Open IAM shell | `docker exec -it fims-iam-service python manage.py shell` |
| List all users | `User.objects.values('email', 'status', 'user_type')` |
| List all GRC roles | `Role.objects.filter(service__name='grc-service').values('code', 'name')` |
| List user's roles | `UserRole.objects.filter(user__email='x@y.tz').select_related('role')` |
| Remove a role from user | `UserRole.objects.filter(user__email='x@y.tz', role__code='internal_auditor').delete()` |
| Check permission exists in IAM | `ServicePermission.objects.filter(permission_code='grc:audit_plan:approve').exists()` |

---

## Notes on Permission Codes in IAM

All 34 GRC permissions use the `grc:` prefix (e.g. `grc:audit_plan:approve`). This prefix is mandatory — the GRC permission middleware (`permission_middleware.py`) filters `permissions_flat` from the JWT using `p.startswith('grc:')`, so any code without the prefix is ignored.

**Why you may see old non-prefixed codes on a fresh install:** Kafka's `auto_offset_reset='earliest'` causes the IAM consumer to replay all historical messages from before the `grc:` prefix was standardised. If this happens, run:

```bash
docker exec fims-iam-service python manage.py shell -c "
from apps.roles.models import ServicePermission, Service, RolePermission
grc = Service.objects.get(name='grc-service')
orphans = [p for p in ServicePermission.objects.filter(service=grc).exclude(permission_code__startswith='grc:') if not RolePermission.objects.filter(service_permission=p).exists()]
ServicePermission.objects.filter(id__in=[p.id for p in orphans]).delete()
print(f'Cleaned {len(orphans)} orphaned permissions')
"
```
