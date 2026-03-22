# GRC-Service Notes

Reference notes for working with **grc-service**.

---

HOW TO RESTART GRC:
docker compose restart grc-service && sleep 6 && echo "Restarted"

⚠️ Important Note
Do not restart grc-service while VS Code is running
The system will freeze, due to resources insufficient.


## 1. Migrations

```bash
# Generate migrations
docker compose exec grc-service python manage.py makemigrations

# Apply migrations
docker compose exec grc-service python manage.py migrate

# Check applied migrations
docker compose exec grc-service python manage.py showmigrations core
```

---

## 2. Login via IAM Service

**a. Get a token:**

```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/iam/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fcc.go.tz","password":"admin123"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access','') or d.get('data',{}).get('access',''))") \
  && echo "TOKEN=${TOKEN:0:40}..."
```

**b. Use the token to call a GRC endpoint:**

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8006/api/v1/grc/lookups/fiscal-years/" \
  | jq '.data[:3] | map({id, year_code})'
```

---

## 3. Decode JWT / Get Current User UUID

**Decode token in Python:**

```python
import json, base64
token = '$TOKEN'
payload = token.split('.')[1]
payload += '=' * (4 - len(payload) % 4)
d = json.loads(base64.b64decode(payload))
print('user_id:', d.get('user_id', ''))
```

**Unlock a locked admin account:**

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(email='admin@fcc.go.tz')
u.failed_login_attempts = 0
u.locked_until = None
u.save()
print('Unlocked:', u.email)
"
```

---

## 4. Restart GRC Service

```bash
docker compose restart grc-service 2>&1 | tail -3
# or wait for confirmation:
docker compose restart grc-service && sleep 5 && echo "Restarted"
```

---

## 5. Get Running Containers

```bash
dps
```

> Alias: `alias dps='docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}\t{{.RunningFor}}"'`

---

## 6. Delete All GRC Operational Data (Fresh Start)

Deletes all data from: Audit Universe, Risk Assessments, Audit Plans, Engagements, Findings, Recommendations, Meetings, Quarterly Reports.

Run in two steps due to a FK constraint on `AuditEngagement` from `grc_quarterly_audit_report_engagements`.

**Step A — Delete most models (may fail at AuditEngagement if junction rows exist):**

```bash
cd /home/simons/Coding/FIMS/grc-service && docker compose exec grc-service python manage.py shell -c "
from apps.core.models.audit_entities import (
    AuditRecommendation, AuditFinding, AuditMeeting,
    QuarterlyAuditReport, AuditEngagement, AuditPlan,
    RiskAssessment, AuditableEntity, AuditUniverse,
)

models = [
    ('AuditRecommendation', AuditRecommendation),
    ('AuditFinding',        AuditFinding),
    ('AuditMeeting',        AuditMeeting),
    ('QuarterlyAuditReport',QuarterlyAuditReport),
    ('AuditEngagement',     AuditEngagement),
    ('AuditPlan',           AuditPlan),
    ('RiskAssessment',      RiskAssessment),
    ('AuditableEntity',     AuditableEntity),
    ('AuditUniverse',       AuditUniverse),
]

for name, Model in models:
    count = Model.objects.count()
    Model.objects.all().delete()
    print(f'{name}: deleted {count}')

print('Done.')
"
```

**Step B — Clear orphan junction table then delete remaining models:**

```bash
cd /home/simons/Coding/FIMS/grc-service && docker compose exec grc-service python manage.py shell -c "
from django.db import connection

with connection.cursor() as cur:
    cur.execute('DELETE FROM grc_quarterly_audit_report_engagements')
    print(f'Cleared grc_quarterly_audit_report_engagements: {cur.rowcount} row(s)')

from apps.core.models.audit_entities import (
    AuditEngagement, AuditPlan, RiskAssessment, AuditableEntity, AuditUniverse,
)
for name, Model in [
    ('AuditEngagement',  AuditEngagement),
    ('AuditPlan',        AuditPlan),
    ('RiskAssessment',   RiskAssessment),
    ('AuditableEntity',  AuditableEntity),
    ('AuditUniverse',    AuditUniverse),
]:
    count = Model.objects.count()
    Model.objects.all().delete()
    print(f'{name}: deleted {count}')

print('Done.')
"
```

---

## 7. Create GRC Roles, Users & Assign Roles (Full Setup)

Run once from `iam-service` after a fresh data wipe. Creates 7 roles, assigns permissions, creates 7 users, assigns roles.

> **Password for all test users:** `Pass@1234`

| Email | Role | SRS Actor |
|---|---|---|
| `cia@fcc.go.tz` | Chief Internal Auditor | CIA — approves all |
| `auditor@fcc.go.tz` | Internal Auditor | **Lead Auditor (LA)** — manages engagements, reviews WPs |
| `teammember@fcc.go.tz` | Internal Auditor | **Audit Team Member (IA)** — creates & submits working papers |
| `auditcommittee@fcc.go.tz` | Audit Committee | Audit Committee |
| `management@fcc.go.tz` | Management | Management |
| `auditee@fcc.go.tz` | Auditee | Auditee |
| `dg@fcc.go.tz` | Director General | Director General |
| `commission@fcc.go.tz` | Commission | Commission |

> **Why two internal_auditor users?** SRS Step 15: *Audit Team Members* create and submit working papers to LA. SRS Step 16: *LA* reviews them. WO has a self-approval guard — the WP submitter cannot be the same person as Stage 1 reviewer (`{{lead_auditor}}`). So `teamember@fcc.go.tz` submits the WP, and `auditor@fcc.go.tz` (LA) reviews in Stage 1, then CIA approves in Stage 2.

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Role, Service, RolePermission, ServicePermission, UserRole
from django.contrib.auth import get_user_model
User = get_user_model()

grc = Service.objects.get(name='grc-service')

# ── Step 1: Create roles ──────────────────────────────────────────────────────
print('=== Step 1: Creating roles ===')
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
    ('director_general',       'Director General',
     'Approves Internal Audit Memos (SRS req 12-13)'),
    ('commission',             'Commission',
     'Notes approved RBIAP and Quarterly Reports (SRS §1.8.1 step 10, §1.8.5)'),
]
for code, name, desc in roles_data:
    role, created = Role.objects.get_or_create(
        code=code, service=grc,
        defaults={'name': name, 'description': desc, 'is_system': True, 'is_active': True}
    )
    print(f\"  {'Created' if created else 'Already exists'}: [{code}]\")

# ── Step 2: Assign permissions ────────────────────────────────────────────────
print()
print('=== Step 2: Assigning permissions ===')
role_permission_map = {
    'internal_auditor': [
        'grc:audit_universe:view','grc:audit_universe:manage',
        'grc:risk_assessment:conduct',
        'grc:audit_plan:view','grc:audit_plan:manage',
        'grc:audit_engagement:manage',
        'grc:audit_memo:view','grc:audit_memo:manage',
        'grc:audit_declaration:manage','grc:audit_declaration:sign',
        'grc:audit_survey:manage',
        'grc:audit_rcm:manage','grc:audit_rcm:approve',
        'grc:audit_program:manage',
        'grc:engagement_notification:manage',
        'grc:audit_working_paper:manage','grc:audit_working_paper:review',
        'grc:audit_finding:manage',
        'grc:audit_report:view',
        'grc:audit_monitoring:update',
        'grc:audit_meeting:manage',       # SRS: LA arranges entry/pre-exit/exit/team meetings
        'grc:quarterly_report:manage',
        'grc:audit_dashboard:view',
    ],
    'chief_internal_auditor': [
        'grc:audit_universe:view','grc:audit_universe:approve',
        'grc:risk_assessment:review',
        'grc:audit_plan:view','grc:audit_plan:manage','grc:audit_plan:approve',
        'grc:audit_engagement:manage',
        'grc:audit_memo:view','grc:audit_memo:manage',
        'grc:audit_declaration:manage',
        'grc:audit_survey:manage',
        'grc:audit_rcm:manage','grc:audit_rcm:approve',
        'grc:audit_program:manage',
        'grc:engagement_notification:manage','grc:engagement_notification:approve',
        'grc:audit_working_paper:review',
        'grc:audit_report:view','grc:audit_report:approve',
        'grc:audit_meeting:view',         # SRS: CIA can view meeting records; LA manages them
        'grc:quarterly_report:manage','grc:quarterly_report:approve',
        'grc:audit_dashboard:view',
        'grc:config:fiscal_year:manage','grc:config:audit_severity:manage',
        'grc:config:finding_type:manage','grc:config:risk_rating:manage','grc:config:system:manage',
    ],
    'audit_committee': [
        'grc:audit_plan:view','grc:audit_plan:approve',
        'grc:audit_memo:view',
        'grc:audit_report:view','grc:audit_report:approve',
        'grc:audit_meeting:view',         # SRS: audit committee reviews quarterly reports referencing meetings
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
    'director_general': [
        'grc:audit_memo:view',
        'grc:audit_memo:approve',
        'grc:audit_report:view',
        'grc:audit_dashboard:view',
    ],
    'commission': [
        'grc:audit_plan:view',
        'grc:audit_plan:approve',
        'grc:quarterly_report:approve',
        'grc:audit_dashboard:view',
    ],
}
for role_code, perm_codes in role_permission_map.items():
    role = Role.objects.get(code=role_code, service=grc)
    assigned = 0
    missing = []
    for perm_code in perm_codes:
        try:
            perm = ServicePermission.objects.get(permission_code=perm_code, service=grc)
            _, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
            if created:
                assigned += 1
        except ServicePermission.DoesNotExist:
            missing.append(perm_code)
    print(f\"  {role.name}: {assigned} assigned\" + (f\", MISSING: {missing}\" if missing else ''))

# ── Step 3: Create users ──────────────────────────────────────────────────────
print()
print('=== Step 3: Creating users ===')
users_to_create = [
    {'email':'cia@fcc.go.tz','first_name':'John','last_name':'Mbwana','employee_id':'FCC-CIA-001','position':'Chief Internal Auditor','department':'Internal Audit','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'cia'},
    {'email':'auditor@fcc.go.tz','first_name':'Mary','last_name':'Simba','employee_id':'FCC-IA-001','position':'Lead Auditor','department':'Internal Audit','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'auditor'},
    {'email':'teammember@fcc.go.tz','first_name':'David','last_name':'Omondi','employee_id':'FCC-IA-002','position':'Audit Team Member','department':'Internal Audit','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'teammember'},
    {'email':'auditcommittee@fcc.go.tz','first_name':'Paul','last_name':'Kamau','employee_id':'FCC-AC-001','position':'Audit Committee Member','department':'Board','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'auditcommittee'},
    {'email':'management@fcc.go.tz','first_name':'Grace','last_name':'Mwangi','employee_id':'FCC-MG-001','position':'Director','department':'Management','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'management'},
    {'email':'auditee@fcc.go.tz','first_name':'Ali','last_name':'Hassan','employee_id':'FCC-AE-001','position':'Head of Department','department':'Operations','user_type':'internal','status':'active','is_active':True,'is_staff':False,'username':'auditee'},
    {'email':'dg@fcc.go.tz','first_name':'James','last_name':'Ndonga','employee_id':'FCC-DG-001','position':'Director General','department':'Office of the DG','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'dg'},
    {'email':'commission@fcc.go.tz','first_name':'Rose','last_name':'Kimaro','employee_id':'FCC-CM-001','position':'Commissioner','department':'Commission','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'commission'},
]
for data in users_to_create:
    user, created = User.objects.get_or_create(email=data['email'], defaults=data)
    if created:
        user.set_password('Pass@1234')
        user.save()
    print(f\"  {'Created' if created else 'Already exists'}: {user.email}\")

# ── Step 4: Assign roles to users ─────────────────────────────────────────────
print()
print('=== Step 4: Assigning roles to users ===')
assignments = [
    ('cia@fcc.go.tz',            'chief_internal_auditor'),
    ('auditor@fcc.go.tz',        'internal_auditor'),
    ('teammember@fcc.go.tz',     'internal_auditor'),
    ('auditcommittee@fcc.go.tz', 'audit_committee'),
    ('management@fcc.go.tz',     'management'),
    ('auditee@fcc.go.tz',        'auditee'),
    ('dg@fcc.go.tz',             'director_general'),
    ('commission@fcc.go.tz',     'commission'),
]
for email, role_code in assignments:
    user = User.objects.get(email=email)
    role = Role.objects.get(code=role_code, service=grc)
    ua, created = UserRole.objects.get_or_create(user=user, role=role, defaults={'is_active': True})
    print(f\"  {'Assigned' if created else 'Already has'}: {email} → {role.name}\")

print()
print('=== All done! ===')
"
```

---

## 8. Grant WO Permissions to GRC Roles (Required Once Per Environment)

GRC roles need cross-service permissions on the Work Orchestration Service so
that non-admin users can submit workflows (`workflow:plan:create`) and act on
stages (`workflow:stage:action`).

**Why this is needed:**
- `CanExecuteStageAction` in WO checks `workflow:stage:action` in the JWT — a WO-level permission
- GRC roles only have `grc:*` permissions by default; WO permissions must be explicitly granted
- Without this, any non-superuser gets 403 when trying to approve/reject a workflow stage

**Run once from `iam-service` after a fresh setup or DB wipe:**

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

grc = Service.objects.get(name='grc-service')
wo  = Service.objects.get(name='work-orchestration-service')

# Roles that submit workflows (need plan:create)
initiator_roles = ['internal_auditor', 'chief_internal_auditor']

# All roles that act on stages (need stage:action + plan:read)
actor_roles = [
    'internal_auditor',
    'chief_internal_auditor',
    'audit_committee',
    'management',
    'director_general',
    'commission',
]

assigned = []
for role_code in set(initiator_roles + actor_roles):
    role = Role.objects.get(code=role_code, service=grc)
    needed = ['workflow:plan:read', 'workflow:stage:action']
    if role_code in initiator_roles:
        needed.append('workflow:plan:create')
    for perm_code in needed:
        perm = ServicePermission.objects.get(permission_code=perm_code, service=wo)
        _, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
        if created:
            assigned.append(f'{role_code} -> {perm_code}')

if assigned:
    print('Assigned:')
    for a in assigned:
        print(f'  {a}')
else:
    print('All WO permissions already assigned.')
print('Done.')
"
```

**After running:** users must log out and back in to get a fresh JWT containing the new permissions.

---

## 9. Grant DRS (document-service) Permissions to GRC Roles (Required Once Per Environment)

GRC roles need cross-service permissions to call the Document Records Service (DRS).
Without these, DRS returns 403 → GRC returns 502 → nginx converts it to 503.

**What this does:**
- Gives `internal_auditor` permission to create and read documents in DRS
- Gives `chief_internal_auditor` read-only access to documents in DRS
- Both get `document:classification:confidential` so they can access confidential audit documents

**Run once in IAM container:**

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission, UserRole

grc = Service.objects.get(name='grc-service')
drs = Service.objects.get(name='document-service')

# Permissions to add
ia_perm_codes = [
    'document:document:create',
    'document:document:read',
    'document:classification:confidential',
]
cia_perm_codes = [
    'document:document:read',
    'document:classification:confidential',
]

ia_role = Role.objects.get(code='internal_auditor', service=grc)
cia_role = Role.objects.get(code='chief_internal_auditor', service=grc)

def add_perms(role, codes, label):
    for code in codes:
        perm = ServicePermission.objects.get(service=drs, permission_code=code)
        rp, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
        status = 'CREATED' if created else 'ALREADY EXISTS'
        print(f'  [{label}] {code}: {status}')

print('--- internal_auditor ---')
add_perms(ia_role, ia_perm_codes, 'IA')

print('--- chief_internal_auditor ---')
add_perms(cia_role, cia_perm_codes, 'CIA')

print()
print('Done.')
"
```

**Expected output (first run):**
```
--- internal_auditor ---
  [IA] document:document:create: CREATED
  [IA] document:document:read: CREATED
  [IA] document:classification:confidential: CREATED
--- chief_internal_auditor ---
  [CIA] document:document:read: CREATED
  [CIA] document:classification:confidential: CREATED

Done.
```

**After running:** users must log out and back in to get a fresh JWT containing `"document-service"` in the `services` array.

**Verify the JWT will include document-service:**

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.services import UnifiedPermissionResolutionService
from apps.users.models import User

for email in ['auditor@fcc.go.tz', 'cia@fcc.go.tz']:
    user = User.objects.get(email=email)
    data = UnifiedPermissionResolutionService.get_user_permissions(user)
    services = data.get('services', [])
    drs_perms = [p for p in data.get('permissions_flat', []) if p.startswith('document:')]
    print(f'{email}:')
    print(f'  services: {services}')
    print(f'  document perms: {drs_perms}')
    print()
"
```

---

## 10. Register Missing GRC Permissions in IAM (e.g. `grc:audit_meeting:manage`)

> **⚠️ NOTE — CIA assignment corrected in Section 12.**
> The original script below assigned `grc:audit_meeting:manage` to BOTH `internal_auditor` AND `chief_internal_auditor`.
> Per SRS 1.8.3, CIA does NOT manage meetings — only the LA does. Use the Section 12 script to correct this.

Some GRC permission codes exist in GRC service code but are **never registered as `ServicePermission` records in IAM**.
This means they never appear in a user's JWT `permissions_flat`, so the permission check always fails silently.

**Symptom:** A user gets a `403` or `permission required` error for a feature that looks correctly coded in GRC views.

**How to check if a permission is missing in IAM:**

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission
grc = Service.objects.get(name='grc-service')
exists = ServicePermission.objects.filter(service=grc, permission_code='grc:audit_meeting:manage').exists()
print('exists:', exists)
"
```

**Fix — create the permission and assign to the relevant roles:**

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

grc = Service.objects.get(name='grc-service')

# Step 1: Create (register) the missing permission
perm, created = ServicePermission.objects.get_or_create(
    service=grc,
    permission_code='grc:audit_meeting:manage',
    defaults={
        'name': 'Manage Audit Meetings',
        'description': 'Schedule and manage audit meetings (entry, pre-exit, exit meetings)',
        'resource_type': 'audit_meeting',
        'action': 'manage',
        'category': 'audit',
        'is_active': True,
    }
)
print(f'Permission: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

# Step 2: Assign to internal_auditor and chief_internal_auditor
# Per SRS: LA (IA) arranges and records all meetings; CIA reviews and participates
for role_code, label in [('internal_auditor', 'IA'), ('chief_internal_auditor', 'CIA')]:
    role = Role.objects.get(code=role_code, service=grc)
    rp, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
    print(f'  [{label}] grc:audit_meeting:manage: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

print('Done.')
"
```

**Expected output (first run):**
```
Permission: CREATED
  [IA] grc:audit_meeting:manage: CREATED
  [CIA] grc:audit_meeting:manage: CREATED
Done.
```

**After running:** users must log out and back in to get a fresh JWT with the new permission in `permissions_flat`.

> **Pattern:** Use this same approach for any GRC permission code used in `permissions_jwt.py` that isn't showing up in user JWTs. The `get_or_create` is idempotent — safe to re-run.

---

## 11. Grant DRS `document:document:read_confidential` to GRC Roles (Required Once Per Environment)

**Problem:** CIA (and other reviewer roles) see evidence listed as `(unavailable)`.

**Root cause:** DRS `can_access_document` checks `document:document:read_confidential` to grant
read access to confidential documents. This permission code was **never registered in IAM** —
only `document:classification:confidential` existed, which is a different code. CIA's JWT
never contained `document:document:read_confidential`, so the classification check failed → 403.

**Fix — run once in IAM container:**

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

drs = Service.objects.get(name='document-service')
grc = Service.objects.get(name='grc-service')

# Register the missing permission in IAM under document-service
perm, created = ServicePermission.objects.get_or_create(
    service=drs,
    permission_code='document:document:read_confidential',
    defaults={
        'name': 'Read Confidential Documents',
        'description': 'Read documents classified as confidential',
        'resource_type': 'document',
        'action': 'read_confidential',
        'category': 'document',
        'is_active': True,
    }
)
print(f'Permission: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

# Assign to internal_auditor and chief_internal_auditor GRC roles
for role_code, label in [('internal_auditor', 'IA'), ('chief_internal_auditor', 'CIA')]:
    role = Role.objects.get(code=role_code, service=grc)
    rp, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
    print(f'  [{label}] document:document:read_confidential: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

print('Done.')
"
```

**Expected output (first run):**
```
Permission: CREATED
  [IA] document:document:read_confidential: CREATED
  [CIA] document:document:read_confidential: CREATED
Done.
```

**After running:** users must log out and back in to get a fresh JWT containing the new permission.






HOW I DELETE THE ENGAGEMENT NOTIFICATION (EN):

docker exec fims-grc-service python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.core.models.audit_entities import EngagementNotification
deleted, _ = EngagementNotification.objects.all().delete()
print('Deleted:', deleted)
" 2>&1 | tail -3



HOW I DELETE THE WORKING PAPERS

docker exec fims-grc-service python -c "
import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup()
from apps.core.models import WorkingPaper
count = WorkingPaper.objects.count()
WorkingPaper.objects.all().delete()
print(f'Deleted {count} working papers')
" 2>&1 | grep -i "deleted"

---

## 12. Fix Audit Meeting RBAC — Register `grc:audit_meeting:view` and Correct CIA Permissions

**Background (SRS 1.8.3):**
- `internal_auditor` (LA) — arranges AND records ALL meeting types → `grc:audit_meeting:manage`
- `chief_internal_auditor` (CIA) — authorises exit via audit *report* approval; should only VIEW meeting records → `grc:audit_meeting:view`
- `audit_committee` — reviews quarterly reports that reference meetings → `grc:audit_meeting:view`

**Problem found:** Section 10 (original script) gave CIA `grc:audit_meeting:manage`. The SRS does NOT support this.

**Fix — run once in IAM container:**

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

grc = Service.objects.get(name='grc-service')

# ── Step 1: Register grc:audit_meeting:view ───────────────────────────────────
view_perm, created = ServicePermission.objects.get_or_create(
    service=grc,
    permission_code='grc:audit_meeting:view',
    defaults={
        'name': 'View Audit Meetings',
        'description': 'Read-only access to audit meeting records (CIA, audit_committee)',
        'resource_type': 'audit_meeting',
        'action': 'view',
        'category': 'audit',
        'is_active': True,
    }
)
print(f'grc:audit_meeting:view: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

# ── Step 2: Ensure grc:audit_meeting:manage is registered (idempotent) ────────
manage_perm, created = ServicePermission.objects.get_or_create(
    service=grc,
    permission_code='grc:audit_meeting:manage',
    defaults={
        'name': 'Manage Audit Meetings',
        'description': 'Schedule and manage audit meetings — Lead Auditor only',
        'resource_type': 'audit_meeting',
        'action': 'manage',
        'category': 'audit',
        'is_active': True,
    }
)
print(f'grc:audit_meeting:manage: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

# ── Step 3: Ensure internal_auditor has manage (not view) ─────────────────────
ia_role = Role.objects.get(code='internal_auditor', service=grc)
rp, created = RolePermission.objects.get_or_create(role=ia_role, service_permission=manage_perm)
print(f'  [IA] grc:audit_meeting:manage: {\"CREATED\" if created else \"ALREADY EXISTS\"}')
# Remove view from IA if accidentally assigned
removed = RolePermission.objects.filter(role=ia_role, service_permission=view_perm).delete()
print(f'  [IA] grc:audit_meeting:view removed: {removed[0]} rows')

# ── Step 4: CIA gets view only — REVOKE manage, GRANT view ────────────────────
cia_role = Role.objects.get(code='chief_internal_auditor', service=grc)
revoked = RolePermission.objects.filter(role=cia_role, service_permission=manage_perm).delete()
print(f'  [CIA] grc:audit_meeting:manage REVOKED: {revoked[0]} rows')
rp, created = RolePermission.objects.get_or_create(role=cia_role, service_permission=view_perm)
print(f'  [CIA] grc:audit_meeting:view: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

# ── Step 5: audit_committee gets view ─────────────────────────────────────────
ac_role = Role.objects.get(code='audit_committee', service=grc)
rp, created = RolePermission.objects.get_or_create(role=ac_role, service_permission=view_perm)
print(f'  [AC]  grc:audit_meeting:view: {\"CREATED\" if created else \"ALREADY EXISTS\"}')

print('Done. Users must log out and back in for JWT to refresh.')
"
```

**Expected output (fresh environment):**
```
grc:audit_meeting:view: CREATED
grc:audit_meeting:manage: ALREADY EXISTS
  [IA] grc:audit_meeting:manage: ALREADY EXISTS
  [IA] grc:audit_meeting:view removed: 0 rows
  [CIA] grc:audit_meeting:manage REVOKED: 1 rows
  [CIA] grc:audit_meeting:view: CREATED
  [AC]  grc:audit_meeting:view: CREATED
Done. Users must log out and back in for JWT to refresh.
```

**After running:** restart the GRC service so the updated `CanViewAuditMeeting` permission class is loaded, then have users log out and back in.

```bash
docker restart fims-grc-service
```

**Test matrix:**

| User | Endpoint | Method | Expected |
|---|---|---|---|
| `auditor@fcc.go.tz` (LA) | `GET /meetings/` | GET | 200 ✅ |
| `auditor@fcc.go.tz` (LA) | `POST /meetings/` | POST | 201 ✅ |
| `auditor@fcc.go.tz` (LA) | `PATCH /meetings/{own_pk}/` | PATCH | 200 ✅ |
| `teammember@fcc.go.tz` (IA, not organizer) | `PATCH /meetings/{auditor_pk}/` | PATCH | 403 `MEETING_NOT_ORGANIZER` |
| `cia@fcc.go.tz` (CIA) | `GET /meetings/` | GET | 200 ✅ |
| `cia@fcc.go.tz` (CIA) | `POST /meetings/` | POST | 403 `permission required` |
| `cia@fcc.go.tz` (CIA) | `PATCH /meetings/{pk}/` | PATCH | 403 `permission required` |
| `auditcommittee@fcc.go.tz` (AC) | `GET /meetings/` | GET | 200 ✅ |
| `auditcommittee@fcc.go.tz` (AC) | `POST /meetings/` | POST | 403 `permission required` |

---


---

# LEGAL MODULE

Everything below relates to the **Legal Module** (governing bodies, meetings, cases, appeals, notices, etc.).

---

## 13. Legal Roles, Users & Permissions

### 13.1 Permission Codes (28 total)

All codes are defined in `config/permissions/grc-service.json` and exposed via `GrcServicePermissions`.

| Domain | Permission Code | Action |
|---|---|---|
| Governing Body | `grc:legal_governing_body:view` | View |
| Governing Body | `grc:legal_governing_body:manage` | Create/Update |
| Meeting | `grc:legal_meeting:view` | View |
| Meeting | `grc:legal_meeting:manage` | Schedule/Update |
| Meeting | `grc:legal_meeting:approve` | Approve via workflow |
| Minutes | `grc:legal_minutes:view` | View |
| Minutes | `grc:legal_minutes:manage` | Create/Update |
| Minutes | `grc:legal_minutes:approve` | Approve via workflow |
| Directive | `grc:legal_directive:view` | View |
| Directive | `grc:legal_directive:manage` | Create/Update/Track |
| Case | `grc:legal_case:view` | View |
| Case | `grc:legal_case:manage` | Create/Update |
| Case | `grc:legal_case:close` | Close/Archive |
| Hearing | `grc:legal_hearing:view` | View |
| Hearing | `grc:legal_hearing:manage` | Create/Record |
| Filing | `grc:legal_filing:view` | View |
| Filing | `grc:legal_filing:manage` | Create/Submit |
| Filing | `grc:legal_filing:approve` | Approve via workflow |
| Settlement | `grc:legal_settlement:view` | View |
| Settlement | `grc:legal_settlement:manage` | Create/Submit |
| Settlement | `grc:legal_settlement:approve` | Approve via workflow |
| Judgment | `grc:legal_judgment:view` | View |
| Judgment | `grc:legal_judgment:manage` | Create/Update |
| Judgment | `grc:legal_judgment:record` | Record final outcome |
| Appeal | `grc:legal_appeal:view` | View |
| Appeal | `grc:legal_appeal:manage` | Create/Update |
| Notice | `grc:legal_notice:view` | View |
| Notice | `grc:legal_notice:manage` | Create/Issue |

### 13.2 Legal Roles (4 roles)

| Role Code | Role Name | Legal Perms | WO Perms | Total |
|---|---|---|---|---|
| `legal_manager` | Legal Manager | 28 (all) | 3 (`plan:read`, `plan:create`, `stage:action`) | 31 |
| `legal_officer` | Legal Officer | 18 | 3 (`plan:read`, `plan:create`, `stage:action`) | 21 |
| `committee_secretary` | Committee Secretary | 8 | 2 (`plan:read`, `stage:action`) | 10 |
| `committee_chair` | Committee Chair | 6 | 2 (`plan:read`, `stage:action`) | 8 |

**Role → Permission breakdown:**

**legal_manager** (28 legal perms — all 28):
- All `governing_body`, `meeting`, `minutes`, `directive`, `case`, `hearing`, `filing`, `settlement`, `judgment`, `appeal`, `notice` permissions

**legal_officer** (18 legal perms):
- `governing_body:view`
- `meeting:view`, `minutes:view`
- `directive:view`, `directive:manage`
- `case:view`, `case:manage`
- `hearing:view`, `hearing:manage`
- `filing:view`, `filing:manage`
- `settlement:view`, `settlement:manage`
- `judgment:view`, `judgment:manage`
- `appeal:view`, `appeal:manage`
- `notice:view`, `notice:manage`

**committee_secretary** (8 legal perms):
- `governing_body:view`, `governing_body:manage`
- `meeting:view`, `meeting:manage`
- `minutes:view`, `minutes:manage`
- `directive:view`, `directive:manage`

**committee_chair** (6 legal perms):
- `governing_body:view`
- `meeting:view`, `meeting:approve`
- `minutes:view`, `minutes:approve`
- `directive:view`

### 13.3 Legal Test Users

> **Password for all legal test users:** `Pass@1234`

| Email | Username | Role | First Name | Last Name | Employee ID |
|---|---|---|---|---|---|
| `legalmanager@fcc.go.tz` | legalmanager | Legal Manager | Sarah | Mkapa | FCC-LM-001 |
| `legalofficer@fcc.go.tz` | legalofficer | Legal Officer | Peter | Mushi | FCC-LO-001 |
| `secretary@fcc.go.tz` | secretary | Committee Secretary | Anna | Mollel | FCC-CS-001 |
| `chair@fcc.go.tz` | chair | Committee Chair | Joseph | Massawe | FCC-CC-001 |

### 13.4 Permission Classes (in `apps/api/permissions_jwt.py`)

28 DRF permission classes — each checks a single permission code from the JWT:

| Class Name | Permission Code |
|---|---|
| `CanViewLegalGoverningBody` | `grc:legal_governing_body:view` |
| `CanManageLegalGoverningBody` | `grc:legal_governing_body:manage` |
| `CanViewLegalMeeting` | `grc:legal_meeting:view` |
| `CanManageLegalMeeting` | `grc:legal_meeting:manage` |
| `CanApproveLegalMeeting` | `grc:legal_meeting:approve` |
| `CanViewLegalMinutes` | `grc:legal_minutes:view` |
| `CanManageLegalMinutes` | `grc:legal_minutes:manage` |
| `CanApproveLegalMinutes` | `grc:legal_minutes:approve` |
| `CanViewLegalDirective` | `grc:legal_directive:view` |
| `CanManageLegalDirective` | `grc:legal_directive:manage` |
| `CanViewLegalCase` | `grc:legal_case:view` |
| `CanManageLegalCase` | `grc:legal_case:manage` |
| `CanCloseLegalCase` | `grc:legal_case:close` |
| `CanViewLegalHearing` | `grc:legal_hearing:view` |
| `CanManageLegalHearing` | `grc:legal_hearing:manage` |
| `CanViewLegalFiling` | `grc:legal_filing:view` |
| `CanManageLegalFiling` | `grc:legal_filing:manage` |
| `CanApproveLegalFiling` | `grc:legal_filing:approve` |
| `CanViewLegalSettlement` | `grc:legal_settlement:view` |
| `CanManageLegalSettlement` | `grc:legal_settlement:manage` |
| `CanApproveLegalSettlement` | `grc:legal_settlement:approve` |
| `CanViewLegalJudgment` | `grc:legal_judgment:view` |
| `CanManageLegalJudgment` | `grc:legal_judgment:manage` |
| `CanRecordLegalJudgment` | `grc:legal_judgment:record` |
| `CanViewLegalAppeal` | `grc:legal_appeal:view` |
| `CanManageLegalAppeal` | `grc:legal_appeal:manage` |
| `CanViewLegalNotice` | `grc:legal_notice:view` |
| `CanManageLegalNotice` | `grc:legal_notice:manage` |

---

## 14. Create Legal Roles, Users & Assign Permissions (Full Setup)

Run once from `iam-service` after a fresh data wipe. Creates 4 legal roles, assigns permissions (including WO cross-service), creates 4 users, assigns roles.

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Role, Service, RolePermission, ServicePermission, UserRole
from django.contrib.auth import get_user_model
User = get_user_model()

grc = Service.objects.get(name='grc-service')

# ── Step 1: Register 28 legal permissions ──
print('=== Step 1: Registering 28 legal permissions ===')
legal_perms = [
    ('grc:legal_governing_body:view',    'View Legal Governing Bodies',    'View governing body records and membership',                      'legal_governing_body', 'view'),
    ('grc:legal_governing_body:manage',  'Manage Legal Governing Bodies',  'Create and update governing body records and membership',          'legal_governing_body', 'manage'),
    ('grc:legal_meeting:view',           'View Legal Meetings',            'View legal meeting records, agendas, and attendance',              'legal_meeting',        'view'),
    ('grc:legal_meeting:manage',         'Manage Legal Meetings',          'Schedule, update, and manage legal meetings and attendance',        'legal_meeting',        'manage'),
    ('grc:legal_meeting:approve',        'Approve Legal Meetings',         'Approve legal meeting agendas and records through workflow',        'legal_meeting',        'approve'),
    ('grc:legal_minutes:view',           'View Legal Minutes',             'View meeting minutes and resolutions',                             'legal_minutes',        'view'),
    ('grc:legal_minutes:manage',         'Manage Legal Minutes',           'Create, update, and submit meeting minutes for approval',           'legal_minutes',        'manage'),
    ('grc:legal_minutes:approve',        'Approve Legal Minutes',          'Approve meeting minutes through workflow',                          'legal_minutes',        'approve'),
    ('grc:legal_directive:view',         'View Legal Directives',          'View meeting directives and litigation directives',                 'legal_directive',      'view'),
    ('grc:legal_directive:manage',       'Manage Legal Directives',        'Create, update, and track meeting and litigation directives',        'legal_directive',      'manage'),
    ('grc:legal_case:view',              'View Legal Cases',               'View litigation cases (defendant and plaintiff)',                    'legal_case',           'view'),
    ('grc:legal_case:manage',            'Manage Legal Cases',             'Create, update, and manage litigation cases through workflow',       'legal_case',           'manage'),
    ('grc:legal_case:close',             'Close Legal Cases',              'Close or archive completed litigation cases',                       'legal_case',           'close'),
    ('grc:legal_hearing:view',           'View Legal Hearings',            'View hearing records and outcomes',                                 'legal_hearing',        'view'),
    ('grc:legal_hearing:manage',         'Manage Legal Hearings',          'Create, update, and record hearing details and outcomes',            'legal_hearing',        'manage'),
    ('grc:legal_filing:view',            'View Legal Filings',             'View court filing records',                                         'legal_filing',         'view'),
    ('grc:legal_filing:manage',          'Manage Legal Filings',           'Create, update, and submit court filings through workflow',          'legal_filing',         'manage'),
    ('grc:legal_filing:approve',         'Approve Legal Filings',          'Approve court filings through workflow',                             'legal_filing',         'approve'),
    ('grc:legal_settlement:view',        'View Legal Settlements',         'View settlement records and terms',                                 'legal_settlement',     'view'),
    ('grc:legal_settlement:manage',      'Manage Legal Settlements',       'Create, update, and submit settlement proposals through workflow',   'legal_settlement',     'manage'),
    ('grc:legal_settlement:approve',     'Approve Legal Settlements',      'Approve settlement agreements through workflow',                     'legal_settlement',     'approve'),
    ('grc:legal_judgment:view',          'View Legal Judgments',            'View judgment records and awarded amounts',                          'legal_judgment',       'view'),
    ('grc:legal_judgment:manage',        'Manage Legal Judgments',          'Create, update, and submit judgment records through workflow',        'legal_judgment',       'manage'),
    ('grc:legal_judgment:record',        'Record Legal Judgments',          'Record final judgment outcomes and close judgment records',           'legal_judgment',       'record'),
    ('grc:legal_appeal:view',            'View Legal Appeals',             'View appeal records and statuses',                                   'legal_appeal',         'view'),
    ('grc:legal_appeal:manage',          'Manage Legal Appeals',           'Create, update, and manage appeal records',                          'legal_appeal',         'manage'),
    ('grc:legal_notice:view',            'View Legal Notices',             'View legal notice records',                                          'legal_notice',         'view'),
    ('grc:legal_notice:manage',          'Manage Legal Notices',           'Create, update, and issue legal notices',                             'legal_notice',         'manage'),
]
for code, name, desc, resource, action in legal_perms:
    sp, created = ServicePermission.objects.get_or_create(
        service=grc, permission_code=code,
        defaults={'name': name, 'description': desc, 'resource_type': resource, 'action': action, 'category': resource, 'is_active': True}
    )
    print(f'  [{\"CREATED\" if created else \"EXISTS\"}] {code}')

# ── Step 2: Create 4 legal roles ──
print()
print('=== Step 2: Creating 4 legal roles ===')
roles_data = [
    ('legal_manager',       'Legal Manager',       'Manages all legal module operations'),
    ('legal_officer',       'Legal Officer',        'Handles day-to-day legal operations'),
    ('committee_secretary', 'Committee Secretary',  'Manages governing body meetings, minutes, and directives'),
    ('committee_chair',     'Committee Chair',      'Approves meeting agendas, minutes, and reviews governing body operations'),
]
for code, name, desc in roles_data:
    role, created = Role.objects.get_or_create(
        code=code, service=grc,
        defaults={'name': name, 'description': desc, 'is_system': True, 'is_active': True}
    )
    print(f'  {\"CREATED\" if created else \"EXISTS\"}: [{code}]')

# ── Step 3: Assign permissions to roles ──
print()
print('=== Step 3: Assigning permissions to roles ===')
role_perm_map = {
    'legal_manager': [p[0] for p in legal_perms],  # all 28
    'legal_officer': [
        'grc:legal_governing_body:view',
        'grc:legal_meeting:view', 'grc:legal_minutes:view',
        'grc:legal_directive:view', 'grc:legal_directive:manage',
        'grc:legal_case:view', 'grc:legal_case:manage',
        'grc:legal_hearing:view', 'grc:legal_hearing:manage',
        'grc:legal_filing:view', 'grc:legal_filing:manage',
        'grc:legal_settlement:view', 'grc:legal_settlement:manage',
        'grc:legal_judgment:view', 'grc:legal_judgment:manage',
        'grc:legal_appeal:view', 'grc:legal_appeal:manage',
        'grc:legal_notice:view', 'grc:legal_notice:manage',
    ],  # 18 (note: no appeal:manage excluded — legal_officer gets view+manage for appeals)
    'committee_secretary': [
        'grc:legal_governing_body:view', 'grc:legal_governing_body:manage',
        'grc:legal_meeting:view', 'grc:legal_meeting:manage',
        'grc:legal_minutes:view', 'grc:legal_minutes:manage',
        'grc:legal_directive:view', 'grc:legal_directive:manage',
    ],  # 8
    'committee_chair': [
        'grc:legal_governing_body:view',
        'grc:legal_meeting:view', 'grc:legal_meeting:approve',
        'grc:legal_minutes:view', 'grc:legal_minutes:approve',
        'grc:legal_directive:view',
    ],  # 6
}
for role_code, perm_codes in role_perm_map.items():
    role = Role.objects.get(code=role_code, service=grc)
    assigned = 0
    for pc in perm_codes:
        sp = ServicePermission.objects.get(service=grc, permission_code=pc)
        _, created = RolePermission.objects.get_or_create(role=role, service_permission=sp)
        if created: assigned += 1
    print(f'  {role.name}: {assigned} new, {len(perm_codes)} total')

# ── Step 4: Create 4 legal test users ──
print()
print('=== Step 4: Creating 4 legal test users ===')
users_to_create = [
    {'email':'legalmanager@fcc.go.tz','first_name':'Sarah','last_name':'Mkapa','employee_id':'FCC-LM-001','position':'Legal Manager','department':'Legal','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'legalmanager'},
    {'email':'legalofficer@fcc.go.tz','first_name':'Peter','last_name':'Mushi','employee_id':'FCC-LO-001','position':'Legal Officer','department':'Legal','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'legalofficer'},
    {'email':'secretary@fcc.go.tz','first_name':'Anna','last_name':'Mollel','employee_id':'FCC-CS-001','position':'Committee Secretary','department':'Board Affairs','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'secretary'},
    {'email':'chair@fcc.go.tz','first_name':'Joseph','last_name':'Massawe','employee_id':'FCC-CC-001','position':'Committee Chair','department':'Board Affairs','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'chair'},
]
for data in users_to_create:
    user, created = User.objects.get_or_create(email=data['email'], defaults=data)
    if created:
        user.set_password('Pass@1234')
        user.save()
    print(f'  {\"CREATED\" if created else \"EXISTS\"}: {user.email}')

# ── Step 5: Assign roles to users ──
print()
print('=== Step 5: Assigning roles to users ===')
assignments = [
    ('legalmanager@fcc.go.tz',  'legal_manager'),
    ('legalofficer@fcc.go.tz',  'legal_officer'),
    ('secretary@fcc.go.tz',     'committee_secretary'),
    ('chair@fcc.go.tz',         'committee_chair'),
]
for email, role_code in assignments:
    user = User.objects.get(email=email)
    role = Role.objects.get(code=role_code, service=grc)
    _, created = UserRole.objects.get_or_create(user=user, role=role, defaults={'is_active': True})
    print(f'  {\"ASSIGNED\" if created else \"ALREADY HAS\"}: {email} -> {role.name}')

# ── Step 6: Grant WO cross-service permissions ──
print()
print('=== Step 6: Granting WO cross-service permissions ===')
try:
    wo = Service.objects.get(name='work-orchestration-service')
    initiator_roles = ['legal_manager', 'legal_officer']
    actor_roles = ['legal_manager', 'legal_officer', 'committee_secretary', 'committee_chair']
    for role_code in set(initiator_roles + actor_roles):
        role = Role.objects.get(code=role_code, service=grc)
        needed = ['workflow:plan:read', 'workflow:stage:action']
        if role_code in initiator_roles:
            needed.append('workflow:plan:create')
        for perm_code in needed:
            perm = ServicePermission.objects.get(permission_code=perm_code, service=wo)
            _, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
            if created: print(f'  ASSIGNED: {role_code} -> {perm_code}')
    print('  WO permissions done.')
except Service.DoesNotExist:
    print('  [SKIP] work-orchestration-service not registered')

print()
print('=== All done! ===')
"
```

**After running:** users must log out and back in to get a fresh JWT containing the new permissions.

---

## 15. Verify Legal RBAC (post-restart check)

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Role, Service, RolePermission, ServicePermission
from apps.roles.services import UnifiedPermissionResolutionService
from django.contrib.auth import get_user_model
User = get_user_model()

grc = Service.objects.get(name='grc-service')

print('=== Legal RBAC Verification ===')
print()
for email in ['legalmanager@fcc.go.tz', 'legalofficer@fcc.go.tz', 'secretary@fcc.go.tz', 'chair@fcc.go.tz']:
    user = User.objects.get(email=email)
    data = UnifiedPermissionResolutionService.get_user_permissions(user)
    legal_p = [p for p in data.get('permissions_flat', []) if p.startswith('grc:legal_')]
    wo_p = [p for p in data.get('permissions_flat', []) if p.startswith('workflow:')]
    print(f'  {email}: {len(legal_p)} legal, {len(wo_p)} WO')

print()
print('Expected:')
print('  legalmanager@fcc.go.tz:  28 legal, 3 WO')
print('  legalofficer@fcc.go.tz:  18 legal, 3 WO')
print('  secretary@fcc.go.tz:      8 legal, 2 WO')
print('  chair@fcc.go.tz:          6 legal, 2 WO')
"
```

---

## 16. Create Risk Management Roles, Users & Assign Roles (Full Setup)

Run once from `iam-service`. Creates 5 new roles, assigns permissions, creates 5 new users, assigns roles.
The existing `dg@fcc.go.tz` (Director General) user already exists from Internal Audit setup — here we add risk management permissions to the existing DG role.

> **Password for all test users:** `Pass@1234`

| Email | Role | SRS Actor |
|---|---|---|
| `rmqam@fcc.go.tz` | Risk Mgmt & QA Manager | RMQAM — manages and approves all risk/QA items |
| `rmo@fcc.go.tz` | Risk Management Officer | RMO — supports risk operations, submits workflows |
| `riskchampion@fcc.go.tz` | Risk Champion | RC — conducts risk assessments, manages dept registers |
| `qualityauditor@fcc.go.tz` | Quality Auditor | QA — conducts QMS audits, manages checklists/NCs |
| `lsm@fcc.go.tz` | Legal Service Manager | LSM — approves IRR, RTAP, quarterly reports |
| `dg@fcc.go.tz` *(existing)* | Director General | DG — signs RC/QA appointments |

> **Why separate RMQAM and RMO?** SRS §1.9.1 Steps 1-3: RMO nominates Risk Champions and drafts appointments, while RMQAM reviews and approves them. WO self-approval guard requires different users for submit vs approve stages.

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Role, Service, RolePermission, ServicePermission, UserRole
from django.contrib.auth import get_user_model
User = get_user_model()

grc = Service.objects.get(name='grc-service')

# ── Step 1: Create roles ──────────────────────────────────────────────────────
print('=== Step 1: Creating Risk Management roles ===')
roles_data = [
    ('rmqam', 'Risk Management and Quality Assurance Manager',
     'Manages risk management module, approves registers, reports, and QMS audits'),
    ('rmo', 'Risk Management Officer',
     'Supports risk management operations, manages champions, assessments, and QMS audits'),
    ('lsm', 'Legal Service Manager',
     'Approves institutional risk registers, RTAPs, and quarterly risk reports'),
    ('risk_champion', 'Risk Champion',
     'Conducts risk assessments, manages departmental registers, responds to RTAP items'),
    ('quality_auditor', 'Quality Auditor',
     'Conducts QMS audits, manages checklists and non-conformances'),
]
for code, name, desc in roles_data:
    role, created = Role.objects.get_or_create(
        code=code, service=grc,
        defaults={'name': name, 'description': desc, 'is_system': True, 'is_active': True}
    )
    print(f\"  {'Created' if created else 'Already exists'}: [{code}]\")

# ── Step 2: Assign permissions ────────────────────────────────────────────────
print()
print('=== Step 2: Assigning Risk Management permissions ===')
role_permission_map = {
    'rmqam': [
        'grc:risk_champion:view','grc:risk_champion:manage',
        'grc:risk_assessment:review',
        'grc:dept_risk_register:manage','grc:dept_risk_register:approve',
        'grc:institutional_risk_register:manage','grc:institutional_risk_register:approve',
        'grc:rtap:manage','grc:rtap:approve',
        'grc:quarterly_risk_report:manage','grc:quarterly_risk_report:approve',
        'grc:quality_auditor:manage','grc:qa_training:manage',
        'grc:qms_audit_program:manage','grc:qms_audit_program:approve',
        'grc:qms_audit_plan:manage','grc:qms_audit_plan:approve',
        'grc:qms_checklist:manage',
        'grc:qms_audit_report:manage','grc:qms_audit_report:sign',
        'grc:non_conformance:manage',
        'grc:risk_dashboard:view',
        'grc:risk_meeting:manage','grc:risk_meeting:view',
    ],
    'rmo': [
        'grc:risk_champion:view','grc:risk_champion:manage',
        'grc:risk_assessment:review',
        'grc:dept_risk_register:manage',
        'grc:institutional_risk_register:manage',
        'grc:rtap:manage',
        'grc:quarterly_risk_report:manage',
        'grc:quality_auditor:manage','grc:qa_training:manage',
        'grc:qms_audit_program:manage',
        'grc:qms_audit_plan:manage',
        'grc:qms_checklist:manage',
        'grc:qms_audit_report:manage',
        'grc:non_conformance:manage',
        'grc:risk_dashboard:view',
        'grc:risk_meeting:manage','grc:risk_meeting:view',
    ],
    'lsm': [
        'grc:institutional_risk_register:approve',
        'grc:rtap:approve',
        'grc:quarterly_risk_report:approve',
        'grc:risk_dashboard:view',
    ],
    'risk_champion': [
        'grc:risk_assessment:conduct',
        'grc:dept_risk_register:manage',
        'grc:rtap:respond',
        'grc:risk_dashboard:view',
        'grc:risk_meeting:manage','grc:risk_meeting:view',
    ],
    'quality_auditor': [
        'grc:qms_checklist:manage',
        'grc:qms_audit_report:manage',
        'grc:non_conformance:manage',
        'grc:risk_meeting:view',
    ],
    'director_general': [
        'grc:risk_champion:view',
        'grc:quality_auditor:manage',
        'grc:risk_dashboard:view',
    ],
}
for role_code, perm_codes in role_permission_map.items():
    role = Role.objects.get(code=role_code, service=grc)
    assigned = 0
    missing = []
    for perm_code in perm_codes:
        try:
            perm = ServicePermission.objects.get(permission_code=perm_code, service=grc)
            _, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
            if created:
                assigned += 1
        except ServicePermission.DoesNotExist:
            missing.append(perm_code)
    print(f\"  {role.name}: {assigned} assigned\" + (f\", MISSING: {missing}\" if missing else ''))

# ── Step 3: Create users ──────────────────────────────────────────────────────
print()
print('=== Step 3: Creating Risk Management users ===')
users_to_create = [
    {'email':'rmqam@fcc.go.tz','first_name':'Sarah','last_name':'Mwalimu','employee_id':'FCC-RMQAM-001','position':'Risk Management & QA Manager','department':'Risk Management','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'rmqam'},
    {'email':'rmo@fcc.go.tz','first_name':'Peter','last_name':'Kileo','employee_id':'FCC-RMO-001','position':'Risk Management Officer','department':'Risk Management','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'rmo'},
    {'email':'riskchampion@fcc.go.tz','first_name':'Anna','last_name':'Mushi','employee_id':'FCC-RC-001','position':'Risk Champion','department':'Operations','user_type':'internal','status':'active','is_active':True,'is_staff':False,'username':'riskchampion'},
    {'email':'qualityauditor@fcc.go.tz','first_name':'Frank','last_name':'Lupembe','employee_id':'FCC-QA-001','position':'Quality Auditor','department':'Risk Management','user_type':'internal','status':'active','is_active':True,'is_staff':False,'username':'qualityauditor'},
    {'email':'lsm@fcc.go.tz','first_name':'Hawa','last_name':'Kondo','employee_id':'FCC-LSM-001','position':'Legal Service Manager','department':'Legal Services','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'lsm'},
]
for data in users_to_create:
    user, created = User.objects.get_or_create(email=data['email'], defaults=data)
    if created:
        user.set_password('Pass@1234')
        user.save()
    print(f\"  {'Created' if created else 'Already exists'}: {user.email}\")

# ── Step 4: Assign roles to users ─────────────────────────────────────────────
print()
print('=== Step 4: Assigning roles to users ===')
assignments = [
    ('rmqam@fcc.go.tz',          'rmqam'),
    ('rmo@fcc.go.tz',            'rmo'),
    ('riskchampion@fcc.go.tz',   'risk_champion'),
    ('qualityauditor@fcc.go.tz', 'quality_auditor'),
    ('lsm@fcc.go.tz',           'lsm'),
    ('dg@fcc.go.tz',            'director_general'),
]
for email, role_code in assignments:
    user = User.objects.get(email=email)
    role = Role.objects.get(code=role_code, service=grc)
    ua, created = UserRole.objects.get_or_create(user=user, role=role, defaults={'is_active': True})
    print(f\"  {'Assigned' if created else 'Already has'}: {email} → {role.name}\")

print()
print('=== All done! ===')
"
```

---

## 17. Grant WO Permissions to Risk Management Roles (Required Once Per Environment)

Risk Management roles need cross-service permissions on the Work Orchestration Service so
that non-admin users can submit workflows (`workflow:plan:create`) and act on
stages (`workflow:stage:action`).

**Roles that submit workflows (RMQAM, RMO):** need `workflow:plan:create`, `workflow:plan:read`, `workflow:stage:action`
**Roles that act on stages (RMQAM, RMO, LSM, DG):** need `workflow:plan:read`, `workflow:stage:action`
**Risk Champion / Quality Auditor:** view only — `workflow:plan:read`

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

grc = Service.objects.get(name='grc-service')
wo  = Service.objects.get(name='work-orchestration-service')

# Roles that submit workflows (need plan:create + plan:read + stage:action)
initiator_roles = ['rmqam', 'rmo']

# Roles that act on workflow stages (need plan:read + stage:action)
actor_roles = ['rmqam', 'rmo', 'lsm', 'director_general']

# Roles that only need read access (to view workflow status)
viewer_roles = ['risk_champion', 'quality_auditor']

assigned = []
all_roles = set(initiator_roles + actor_roles + viewer_roles)

for role_code in all_roles:
    role = Role.objects.get(code=role_code, service=grc)
    needed = ['workflow:plan:read']
    if role_code in actor_roles:
        needed.append('workflow:stage:action')
    if role_code in initiator_roles:
        needed.append('workflow:plan:create')
    for perm_code in needed:
        perm = ServicePermission.objects.get(permission_code=perm_code, service=wo)
        _, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
        if created:
            assigned.append(f'{role_code} -> {perm_code}')

if assigned:
    print('Assigned:')
    for a in assigned:
        print(f'  {a}')
else:
    print('All WO permissions already assigned.')
print('Done.')
"
```

**After running:** users must log out and back in to get a fresh JWT containing the new permissions.

---

## 18. Grant DRS Permissions to Risk Management Roles (Required Once Per Environment)

RMQAM and RMO roles need cross-service permissions to upload/read documents in the
Document Records Service (DRS) — used for appointment letters, register PDFs, and
audit reports.

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Service, ServicePermission, Role, RolePermission

grc = Service.objects.get(name='grc-service')
drs = Service.objects.get(name='document-service')

role_drs_perms = {
    'rmqam': [
        'document:document:create',
        'document:document:read',
        'document:classification:confidential',
    ],
    'rmo': [
        'document:document:create',
        'document:document:read',
        'document:classification:confidential',
    ],
    'lsm': [
        'document:document:read',
        'document:classification:confidential',
    ],
    'risk_champion': [
        'document:document:read',
    ],
    'quality_auditor': [
        'document:document:read',
    ],
}

for role_code, perm_codes in role_drs_perms.items():
    role = Role.objects.get(code=role_code, service=grc)
    for perm_code in perm_codes:
        perm = ServicePermission.objects.get(service=drs, permission_code=perm_code)
        rp, created = RolePermission.objects.get_or_create(role=role, service_permission=perm)
        status = 'CREATED' if created else 'ALREADY EXISTS'
        print(f'  [{role_code}] {perm_code}: {status}')

print()
print('Done.')
"
```

**Expected output (first run):**
```
  [rmqam] document:document:create: CREATED
  [rmqam] document:document:read: CREATED
  [rmqam] document:classification:confidential: CREATED
  [rmo] document:document:create: CREATED
  [rmo] document:document:read: CREATED
  [rmo] document:classification:confidential: CREATED
  [lsm] document:document:read: CREATED
  [lsm] document:classification:confidential: CREATED
  [risk_champion] document:document:read: CREATED
  [quality_auditor] document:document:read: CREATED

Done.
```

**After running:** users must log out and back in to get a fresh JWT containing `"document-service"` in the `services` array.

---

## 19. Verify Risk Management RBAC Setup

Run this quick verification to confirm all Risk Management users have the expected
number of permissions:

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from apps.roles.models import Role, Service, RolePermission, ServicePermission
from apps.roles.services import UnifiedPermissionResolutionService
from django.contrib.auth import get_user_model
User = get_user_model()

grc = Service.objects.get(name='grc-service')

print('=== Risk Management RBAC Verification ===')
print()
for email in ['rmqam@fcc.go.tz', 'rmo@fcc.go.tz', 'riskchampion@fcc.go.tz', 'qualityauditor@fcc.go.tz', 'lsm@fcc.go.tz', 'dg@fcc.go.tz']:
    user = User.objects.get(email=email)
    data = UnifiedPermissionResolutionService.get_user_permissions(user)
    risk_p = [p for p in data.get('permissions_flat', []) if p.startswith('grc:risk_') or p.startswith('grc:dept_') or p.startswith('grc:institutional_') or p.startswith('grc:rtap') or p.startswith('grc:quarterly_risk') or p.startswith('grc:quality_') or p.startswith('grc:qms_') or p.startswith('grc:non_conformance') or p.startswith('grc:qa_training')]
    wo_p = [p for p in data.get('permissions_flat', []) if p.startswith('workflow:')]
    drs_p = [p for p in data.get('permissions_flat', []) if p.startswith('document:')]
    print(f'  {email}: {len(risk_p)} risk, {len(wo_p)} WO, {len(drs_p)} DRS')

print()
print('Expected:')
print('  rmqam@fcc.go.tz:          24 risk, 3 WO, 3 DRS')
print('  rmo@fcc.go.tz:            17 risk, 3 WO, 3 DRS')
print('  riskchampion@fcc.go.tz:    6 risk, 1 WO, 1 DRS')
print('  qualityauditor@fcc.go.tz:  4 risk, 1 WO, 1 DRS')
print('  lsm@fcc.go.tz:             4 risk, 2 WO, 2 DRS')
print('  dg@fcc.go.tz:              3 risk, 2 WO, 0 DRS (has DRS from IA setup)')
"
```

