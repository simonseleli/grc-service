# WO Stage Assignees Bug — Root Cause Analysis & Fix Plan

**Date**: 2026-03-13  
**Symptom**: CIA user (`cia@fcc.go.tz`) gets **HTTP 403** on  
`GET /api/v1/workflow/plans/{plan_id}/` and `/activity/` after an  
auditor submits an Audit Universe for approval.

---

## 1. Root Cause Chain

### Step 1 — Template registration
GRC registers workflow templates to WO via Kafka on service startup  
(`apps.py` → `WorkflowTemplateRegistrar`).  
`apps/core/workflows/workflows.yaml` is the **single source of truth**  
for every template definition published to WO.

### Step 2 — Plan instantiation
When GRC calls `OrchestrationClient.start_workflow(template_code, context, ...)`,  
WO creates a plan via `CreateWorkflowPlanUseCase.execute()`.  
Inside that use case, `_stages_from_template(template, context)` iterates over  
every stage in `template.definition["stages"]` and builds `StageInput` objects —  
**directly copying** the YAML `assignees` list (after resolving `{{variable}}`  
placeholders using the provided context dict).

**File**: `work-orchestration-service/apps/core/use_cases/create_workflow_plan.py`  
**Functions**: `_stages_from_template` (line 285), `_resolve_assignees` (line 260)

### Step 3 — The bug
**Every approval stage in `workflows.yaml` has `assignees: []`.**  
Result: every created WO plan has stages with an empty assignees list.

### Step 4 — WO access denied
`CanViewWorkflowAsParticipant` (in `permissions_enforcement.py`) runs 4 checks:

| # | Check | Result for CIA |
|---|---|---|
| 1 | `workflow:plan:read` in user permissions? | ❌ CIA has only `grc:*` perms, not service-level WO perms |
| 2 | `plan.created_by == user_id`? | ❌ The auditor (Mary Simba) created it |
| 3 | `plan.applicant_id == user_id`? | ❌ Also the auditor |
| 4 | User in any stage's `assignees`? | ❌ All `assignees: []` → empty |

→ All 4 fail → **403 Forbidden**

---

## 2. Why the Model's `get_workflow_stages()` Doesn't Help

Each model (e.g. `AuditUniverse`) has a `get_workflow_stages()` method that  
returns **correct** assignees like `["role:chief_internal_auditor"]`.  
**But these methods are dead code** relative to plan creation:

- `start_workflow()` sends only `template_id` to WO (no inline stages)
- WO looks up the registered template by ID and uses its YAML-sourced definition
- `get_workflow_stages()` is never called during workflow creation

---

## 3. Corporate vs GRC Pattern

| Aspect | Corporate (`workflows.yaml`) | GRC (`workflows.yaml`) |
|---|---|---|
| Stage assignees | Always populated | `[]` on every approval stage |
| Role-based | `["role:finance_officer"]` | Missing |
| Context UUID | `["{{hod_id}}"]`, `["{{custodian_id}}"]` | `["{{lead_auditor}}"]` ✅ (engagement only) |

**Corporate never leaves `assignees: []` on an active approval stage.**  
Terminal/completed stages can have `[]` — that's fine.

---

## 4. WO Role Matching Mechanics

- IAM puts **bare role codes** (e.g. `chief_internal_auditor`) into the JWT  
  `roles` array via `get_user_roles()` (uses `role.code`, **not** `role.full_code`).
- WO `jwt_middleware.py` sets `request.user_roles = payload.get('roles', [])`.
- WO `_is_user_in_assignees()` strips the `role:` prefix then checks  
  `role_code in request.user_roles`.
- So `assignees: ["role:chief_internal_auditor"]` in YAML → matched against  
  `"chief_internal_auditor"` in JWT → ✅ CIA user passes the check.

---

## 5. Confirmed IAM Role Codes (`grc-service`)

| `role.code` | Display Name |
|---|---|
| `chief_internal_auditor` | Chief Internal Auditor |
| `internal_auditor` | Internal Auditor / Lead Auditor |
| `management` | Management |
| `audit_committee` | Audit Committee |
| `auditee` | Auditee |

---

## 6. Complete Fix Table — `workflows.yaml`

File: `apps/core/workflows/workflows.yaml`

| Template code | Stage `definitionKey` | Stage Name | Current | Fix |
|---|---|---|---|---|
| `grc.working_paper_approval` | `working_paper_review` | Working Paper Review | `["{{lead_auditor}}"]` | ✅ keep |
| `grc.working_paper_approval` | `working_paper_approval` | Working Paper Approval | `["role:grc_reviewer"]` | → `["role:chief_internal_auditor"]` ⚠️ |
| `grc.working_paper_approval` | `working_paper_completed` | Completed | `[]` | ✅ keep (terminal) |
| `grc.audit_universe_approval` | `cia_review` | CIA Review | `[]` | → `["role:chief_internal_auditor"]` |
| `grc.audit_plan_approval` | `cia_review` | CIA Review | `[]` | → `["role:chief_internal_auditor"]` |
| `grc.audit_plan_approval` | `management_review` | Management Review | `[]` | → `["role:management"]` |
| `grc.audit_plan_approval` | `committee_review` | Audit Committee Review | `[]` | → `["role:audit_committee"]` |
| `grc.audit_plan_approval` | `commission_noting` | Commission Noting | `[]` | → TBD ⚠️ |
| `grc.engagement_lifecycle` | `planning` | Audit Planning | `["{{lead_auditor}}"]` | ✅ keep |
| `grc.engagement_lifecycle` | `fieldwork` | Fieldwork | `["{{lead_auditor}}"]` | ✅ keep |
| `grc.engagement_lifecycle` | `reporting` | Reporting | `["{{lead_auditor}}"]` | ✅ keep |
| `grc.engagement_notification_approval` | `cia_approval` | CIA Approval | `[]` | → `["role:chief_internal_auditor"]` |
| `grc.audit_memo_approval` | `cia_memo_review` | CIA Review | `[]` | → `["role:chief_internal_auditor"]` |
| `grc.audit_memo_approval` | `dg_memo_approval` | DG Approval | `[]` | → TBD ⚠️ |
| `grc.audit_program_approval` | `ia_program_review` | IA Review | `[]` | → `["role:internal_auditor"]` |
| `grc.audit_program_approval` | `cia_program_approval` | CIA Approval | `[]` | → `["role:chief_internal_auditor"]` |
| `grc.audit_report_approval` | `ia_report_review` | IA Review | `[]` | → `["role:internal_auditor"]` |
| `grc.audit_report_approval` | `cia_report_approval` | CIA Approval | `[]` | → `["role:chief_internal_auditor"]` |
| `grc.quarterly_report_approval` | `cia_qr_review` | CIA Review | `[]` | → `["role:chief_internal_auditor"]` |
| `grc.quarterly_report_approval` | `management_qr_review` | Management Review | `[]` | → `["role:management"]` |
| `grc.quarterly_report_approval` | `committee_qr_review` | Audit Committee Review | `[]` | → `["role:audit_committee"]` |
| `grc.quarterly_report_approval` | `commission_qr_noting` | Commission Noting | `[]` | → TBD ⚠️ |

---

## 7. Open Questions (Decisions Required Before Fixing)

### ⚠️ Q1 — `commission_noting` / `commission_qr_noting`
**"Commission Noting"** implies a governing oversight body (e.g. a Presidential  
or Parliamentary Commission). IAM currently has **no `commission` role** for  
`grc-service`. Options:

- **Option A**: Map to `["role:audit_committee"]` (stretch — same people note it)
- **Option B**: Add a new `commission` role to IAM and seed appropriate users
- **Option C**: Map to `["role:management"]` (management acknowledges the noting)

### ⚠️ Q2 — `dg_memo_approval`
**"DG Approval"** (Director General) for the Audit Memo workflow.  
IAM has **no `dg` or `director_general` role** for `grc-service`. Options:

- **Option A**: Map to `["role:management"]` (DG is management-level)
- **Option B**: Add a new `dg` role to IAM and seed the DG user

### ⚠️ Q3 — `working_paper_approval` stage
Currently uses `["role:grc_reviewer"]` — **`grc_reviewer` does not exist in IAM**.  
The "Working Paper Approval" stage description says "Final approval by Head of Audit."  
Options:

- **Option A**: Replace with `["role:chief_internal_auditor"]`
- **Option B**: Add a new `grc_reviewer` role to IAM

---

## 8. After the YAML Fix

### Template Re-registration
Once `workflows.yaml` is updated, GRC service must **re-publish templates to WO**:

```bash
# Restart GRC service (triggers apps.ready() → Kafka template publish)
docker restart fims-grc-service

# Or if a management command exists:
docker exec fims-grc-service python manage.py register_workflow_templates
```

### Existing Plans
Plans created **before** the fix will still have `assignees: []` in their stages  
(WO stores a copy at creation time). Those must either:
1. **Deleted and resubmitted** (simplest during development/testing)
2. **Patched directly in WO DB** via Django shell or migration

To delete the stuck plan and re-test:
```bash
# In WO shell
docker exec fims-work-orchestration-service python manage.py shell -c "
from apps.core.models import WorkflowPlan
WorkflowPlan.objects.filter(id='d40af701-a4d6-40c1-8bed-629184e86e27').delete()
"

# In GRC shell — clear the plan reference so universe can be resubmitted
docker exec fims-grc-service python manage.py shell -c "
from apps.core.models.audit_entities import AuditUniverse
u = AuditUniverse.objects.get(id='<universe-id>')
u.workflow_plan_id = None
u.workflow_stage = ''
u.workflow_stage_id = None
u.workflow_started_at = None
u.status = 'draft'
u.save()
"
```

---

## 9. Files to Change

| File | Change |
|---|---|
| `apps/core/workflows/workflows.yaml` | Add role-based assignees to all 14 empty approval stages |
| IAM seed data (optional) | Add `commission` / `dg` roles if Q1/Q2 go with Option B |
| `apps/core/models/audit_entities.py` | `get_workflow_stages()` methods already correct; can be left as-is or cleaned up later |
