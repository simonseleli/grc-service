# GRC Users & Roles Reference

**Password for all test users:** `Pass@1234`

---

## Users

| Email | Name | Role | is_staff |
|---|---|---|---|
| `cia@fcc.go.tz` | John Mbwana | Chief Internal Auditor | ✅ |
| `auditor@fcc.go.tz` | Mary Simba | Internal Auditor / Lead Auditor | ✅ |
| `auditcommittee@fcc.go.tz` | Paul Kamau | Audit Committee | ✅ |
| `management@fcc.go.tz` | Grace Mwangi | Management | ✅ |
| `auditee@fcc.go.tz` | Ali Hassan | Auditee | ❌ |
| `admin@fcc.go.tz` | Admin | Superuser (IAM) | ✅ — password: `admin123` |

---

## Roles & Permissions

### Chief Internal Auditor — 27 permissions
> `cia@fcc.go.tz` · Approves audit universe, plans, programs, memos, and reports

| Permission Code | What It Allows |
|---|---|
| `grc:audit_universe:view` | View audit universe |
| `grc:audit_universe:approve` | Approve audit universe |
| `grc:risk_assessment:review` | Review risk assessments |
| `grc:audit_plan:view` | View audit plans |
| `grc:audit_plan:manage` | Create/edit audit plans |
| `grc:audit_plan:approve` | Approve RBIAP |
| `grc:audit_engagement:manage` | Manage audit engagements |
| `grc:audit_memo:view` | View audit memos |
| `grc:audit_memo:manage` | Create/edit audit memos |
| `grc:audit_declaration:manage` | Manage declarations of independence |
| `grc:audit_survey:manage` | Manage audit surveys |
| `grc:audit_rcm:manage` | Manage risk control matrices |
| `grc:audit_rcm:approve` | Approve RCM |
| `grc:audit_program:manage` | Manage audit programs |
| `grc:engagement_notification:manage` | Manage engagement notifications |
| `grc:engagement_notification:approve` | Approve engagement notifications |
| `grc:audit_working_paper:review` | Review working papers |
| `grc:audit_report:view` | View audit reports |
| `grc:audit_report:approve` | Approve audit reports |
| `grc:quarterly_report:manage` | Create/edit quarterly reports |
| `grc:quarterly_report:approve` | Approve quarterly reports |
| `grc:audit_dashboard:view` | View audit dashboard |
| `grc:config:fiscal_year:manage` | Manage fiscal years |
| `grc:config:audit_severity:manage` | Manage audit severity levels |
| `grc:config:finding_type:manage` | Manage finding types |
| `grc:config:risk_rating:manage` | Manage risk ratings |
| `grc:config:system:manage` | Manage system configuration |

---

### Internal Auditor / Lead Auditor — 22 permissions
> `auditor@fcc.go.tz` · Conducts risk assessments, creates engagements, working papers, findings

| Permission Code | What It Allows |
|---|---|
| `grc:audit_universe:view` | View audit universe |
| `grc:audit_universe:manage` | Create/edit audit universe |
| `grc:risk_assessment:conduct` | Conduct risk assessments |
| `grc:audit_plan:view` | View audit plans |
| `grc:audit_plan:manage` | Create/edit audit plans |
| `grc:audit_engagement:manage` | Manage audit engagements |
| `grc:audit_memo:view` | View audit memos |
| `grc:audit_memo:manage` | Create/edit audit memos |
| `grc:audit_declaration:manage` | Manage declarations of independence |
| `grc:audit_declaration:sign` | Sign declarations of independence |
| `grc:audit_survey:manage` | Manage audit surveys |
| `grc:audit_rcm:manage` | Manage risk control matrices |
| `grc:audit_rcm:approve` | Approve RCM |
| `grc:audit_program:manage` | Manage audit programs |
| `grc:engagement_notification:manage` | Manage engagement notifications |
| `grc:audit_working_paper:manage` | Create/edit working papers |
| `grc:audit_working_paper:review` | Review working papers |
| `grc:audit_finding:manage` | Create/edit audit findings |
| `grc:audit_report:view` | View audit reports |
| `grc:audit_monitoring:update` | Update implementation monitoring |
| `grc:quarterly_report:manage` | Create/edit quarterly reports |
| `grc:audit_dashboard:view` | View audit dashboard |

---

### Audit Committee — 7 permissions
> `auditcommittee@fcc.go.tz` · Reviews and approves plan + reports strategically

| Permission Code | What It Allows |
|---|---|
| `grc:audit_plan:view` | View audit plans |
| `grc:audit_plan:approve` | Approve RBIAP |
| `grc:audit_memo:view` | View audit memos |
| `grc:audit_report:view` | View audit reports |
| `grc:audit_report:approve` | Approve audit reports |
| `grc:quarterly_report:approve` | Approve quarterly reports |
| `grc:audit_dashboard:view` | View audit dashboard |

---

### Management — 5 permissions
> `management@fcc.go.tz` · Reviews RBIAP, monitors audit implementation

| Permission Code | What It Allows |
|---|---|
| `grc:audit_plan:view` | View audit plans |
| `grc:audit_report:view` | View audit reports |
| `grc:audit_monitoring:update` | Update implementation monitoring |
| `grc:quarterly_report:approve` | Approve quarterly reports |
| `grc:audit_dashboard:view` | View audit dashboard |

---

### Auditee — 3 permissions
> `auditee@fcc.go.tz` · Responds to findings, updates implementation status

| Permission Code | What It Allows |
|---|---|
| `grc:audit_plan:view` | View audit plans |
| `grc:audit_finding:respond` | Respond to audit findings |
| `grc:audit_monitoring:update` | Update implementation monitoring |

---

## Quick Login Test

```bash
# Login as CIA
export TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"cia@fcc.go.tz","password":"Pass@1234"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access','') or d.get('data',{}).get('access',''))")

echo "TOKEN=${TOKEN:0:40}..."
```
