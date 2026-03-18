# WO Stage Assignees Bug — Fix Summary

**Date fixed**: 2026-03-13  
**Related analysis**: `WO_ASSIGNEE_BUG_ANALYSIS.md`  
**Symptom**: CIA user (`cia@fcc.go.tz`) got HTTP 403 on `GET /api/v1/workflow/plans/{id}/`  
immediately after an auditor submitted an Audit Universe for approval.

---

## The Bug in One Line

Every approval stage in `workflows.yaml` had `assignees: []`.  
WO copied those empty lists into the live plan's stages at creation time, so no user  
ever passed the `CanViewWorkflowAsParticipant` assignee check → 403.

---

## Files Modified

### 1. `apps/core/workflows/workflows.yaml`

**The primary fix.** Populated `assignees` on every active approval stage across all 8 workflow templates.

| Template | Stage | Before | After |
|---|---|---|---|
| `grc.working_paper_approval` | `working_paper_approval` | `["role:grc_reviewer"]` ❌ | `["role:chief_internal_auditor"]` |
| `grc.audit_universe_approval` | `cia_review` | `[]` | `["role:chief_internal_auditor"]` |
| `grc.rbiap_approval` | `cia_review` | `[]` | `["role:chief_internal_auditor"]` |
| `grc.rbiap_approval` | `management_review` | `[]` | `["role:management"]` |
| `grc.rbiap_approval` | `committee_review` | `[]` | `["role:audit_committee"]` |
| `grc.rbiap_approval` | `commission_noting` | `[]` | `["role:commission"]` |
| `grc.engagement_notification_approval` | `cia_approval` | `[]` | `["role:chief_internal_auditor"]` |
| `grc.audit_memo_approval` | `cia_memo_review` | `[]` | `["role:chief_internal_auditor"]` |
| `grc.audit_memo_approval` | `dg_memo_approval` | `[]` | `["role:director_general"]` |
| `grc.audit_program_approval` | `ia_program_review` | `[]` | `["role:internal_auditor"]` |
| `grc.audit_program_approval` | `cia_program_approval` | `[]` | `["role:chief_internal_auditor"]` |
| `grc.audit_report_approval` | `ia_report_review` | `[]` | `["role:internal_auditor"]` |
| `grc.audit_report_approval` | `cia_report_approval` | `[]` | `["role:chief_internal_auditor"]` |
| `grc.quarterly_report_approval` | `cia_qr_review` | `[]` | `["role:chief_internal_auditor"]` |
| `grc.quarterly_report_approval` | `management_qr_review` | `[]` | `["role:management"]` |
| `grc.quarterly_report_approval` | `committee_qr_review` | `[]` | `["role:audit_committee"]` |
| `grc.quarterly_report_approval` | `commission_qr_noting` | `[]` | `["role:commission"]` |

Stages left as `[]` intentionally: `working_paper_review` (uses `{{lead_auditor}}`),  
`working_paper_completed` (terminal), all 3 `engagement_lifecycle` stages (use `{{lead_auditor}}`).

---

### 2. `config/permissions/grc-service.json`

Added two new roles (`director_general`, `commission`) that were required by the YAML fix  
but missing from the permissions config. Both are backed by the SRS:

| Role code | SRS reference | Permissions granted |
|---|---|---|
| `director_general` | SRS req 12-13: DG approves Internal Audit Memo | `grc:audit_memo:view`, `grc:audit_memo:approve`, `grc:audit_report:view`, `grc:audit_dashboard:view` |
| `commission` | SRS §1.8.1 step 10 / §1.8.5: Commission notes RBIAP & Quarterly Reports | `grc:audit_plan:view`, `grc:audit_plan:approve`, `grc:quarterly_report:approve`, `grc:audit_dashboard:view` |

---

### 3. `implementation/my_implementation/grc/notes/grc_notes.md`

Updated **Section 7 — Create GRC Roles, Users & Assign Roles** to include the 2 new roles  
and their corresponding test users so the IAM setup script stays complete.

| New entry | Details |
|---|---|
| Role `director_general` | Director General — password `Pass@1234` |
| Role `commission` | Commission — password `Pass@1234` |
| User `dg@fcc.go.tz` | James Ndonga, Director General |
| User `commission@fcc.go.tz` | Rose Kimaro, Commissioner |

---

## IAM Live Changes (run once)

Executed against `fims-iam-service` to create the 2 new roles in the running system:

```bash
cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell
# → Created: [director_general], [commission]
# → Assigned permissions to both roles
# → Created users dg@fcc.go.tz, commission@fcc.go.tz
# → Assigned roles to users
```

> **Note**: `grc:audit_memo:approve` was reported MISSING for `director_general` during this run
> because the *running* GRC service (`/home/simons/Coding/FIMS/grc-service`) has an older
> `grc-service.json` that predates the addition of `grc:audit_memo:approve`. To resolve,
> sync `config/permissions/grc-service.json` from `_FIMS` to `FIMS` and restart the GRC service
> so it re-publishes the permission to IAM via Kafka. Then re-run the role-permission assignment.

---

## After the Fix: Re-register Templates

GRC must re-publish the updated `workflows.yaml` to WO so new plans get the correct assignees:

```bash
# Restart GRC service — apps.ready() triggers Kafka template publish
cd /home/simons/Coding/FIMS && docker compose restart grc-service
```

## Existing Stuck Plans

Plans created *before* this fix still have `assignees: []` in their stages.  
Delete and resubmit them:

```bash
# 1. Delete the plan in WO
docker exec fims-work-orchestration-service python manage.py shell -c "
from apps.core.models import WorkflowPlan
WorkflowPlan.objects.filter(id='<plan_id>').delete()
"

# 2. Clear the workflow reference on the GRC entity so it can be resubmitted
docker exec fims-grc-service python manage.py shell -c "
from apps.core.models.audit_entities import AuditUniverse
u = AuditUniverse.objects.get(id='<universe_id>')
u.workflow_plan_id = None; u.workflow_stage = ''
u.workflow_stage_id = None; u.workflow_started_at = None
u.status = 'draft'; u.save()
"
```
