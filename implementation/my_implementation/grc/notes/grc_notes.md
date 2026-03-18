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

