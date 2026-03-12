# GRC-Service Notes

Reference notes for working with **grc-service**.

---

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

Run once from `iam-service` after a fresh data wipe. Creates 5 roles, assigns permissions, creates 5 users, assigns roles.

> **Password for all test users:** `Pass@1234`

| Email | Role |
|---|---|
| `cia@fcc.go.tz` | Chief Internal Auditor |
| `auditor@fcc.go.tz` | Internal Auditor |
| `auditcommittee@fcc.go.tz` | Audit Committee |
| `management@fcc.go.tz` | Management |
| `auditee@fcc.go.tz` | Auditee |

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
        'grc:quarterly_report:manage','grc:quarterly_report:approve',
        'grc:audit_dashboard:view',
        'grc:config:fiscal_year:manage','grc:config:audit_severity:manage',
        'grc:config:finding_type:manage','grc:config:risk_rating:manage','grc:config:system:manage',
    ],
    'audit_committee': [
        'grc:audit_plan:view','grc:audit_plan:approve',
        'grc:audit_memo:view',
        'grc:audit_report:view','grc:audit_report:approve',
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
    {'email':'auditor@fcc.go.tz','first_name':'Mary','last_name':'Simba','employee_id':'FCC-IA-001','position':'Internal Auditor','department':'Internal Audit','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'auditor'},
    {'email':'auditcommittee@fcc.go.tz','first_name':'Paul','last_name':'Kamau','employee_id':'FCC-AC-001','position':'Audit Committee Member','department':'Board','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'auditcommittee'},
    {'email':'management@fcc.go.tz','first_name':'Grace','last_name':'Mwangi','employee_id':'FCC-MG-001','position':'Director','department':'Management','user_type':'internal','status':'active','is_active':True,'is_staff':True,'username':'management'},
    {'email':'auditee@fcc.go.tz','first_name':'Ali','last_name':'Hassan','employee_id':'FCC-AE-001','position':'Head of Department','department':'Operations','user_type':'internal','status':'active','is_active':True,'is_staff':False,'username':'auditee'},
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
    ('auditcommittee@fcc.go.tz', 'audit_committee'),
    ('management@fcc.go.tz',     'management'),
    ('auditee@fcc.go.tz',        'auditee'),
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


