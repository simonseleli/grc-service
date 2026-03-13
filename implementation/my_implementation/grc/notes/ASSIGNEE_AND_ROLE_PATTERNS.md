# Assignee & Role Patterns in FIMS
## Reference: How user assignment works across Corporate, Work Orchestration, and GRC

> Prepared from deep-dive: corporate-service workflows, work-orchestration-service models, and grc-service entity models.

---

## 1. The Two Assignee Types in Work Orchestration

Work Orchestration (WO) supports **two fundamentally different kinds of assignees** stored in `WorkflowStageModel.assignees` (JSONField, list):

| Format | Example | Meaning | Resolved when? |
|---|---|---|---|
| `{{variable_name}}` | `{{lead_auditor}}` | A specific user UUID from context | **At workflow-start time** — resolved by `_resolve_assignees()` and stored as a real UUID |
| `role:role_code` | `role:hr_officer` | Anyone with that role | **At action time** — checked by `_is_user_in_assignees()` against user's JWT roles |

These are **not equivalent**. The distinction is critical.

---

## 2. How `{{variable_name}}` Works (Specific User)

### Flow
```
Service creates entity
  → entity.get_workflow_context() returns {"lead_auditor": "uuid-of-mary"}
  → OrchestrationClient.start_workflow(context=context)
  → WO _resolve_assignees(["{{lead_auditor}}"], context)  →  ["uuid-of-mary"]
  → Stored in DB: stage.assignees = ["uuid-of-mary"]
  → WO checks UUID match against request.user_id at action time
```

### Where the UUID comes from
**It is always derived from the data model, never from a raw form dropdown.**
- Corporate: `line_manager_id`, `hod_id`, `supervisor_id`, `director_id` — all come from `StaffProfile` relationships, not entered by the user. `merge_hierarchy_context(context, applicant_id)` auto-fetches them from the DB.
- GRC: `lead_auditor` comes from `AuditEngagement.lead_auditor` — a UUID the IA explicitly chose when creating the engagement (from a role-filtered picker).

### Corporate patterns using `{{uuid}}`
```yaml
# Specific person because the relationship is 1-to-1 and data-derived:
assignees: ["{{line_manager_id}}"]   # from StaffProfile.line_manager_id
assignees: ["{{hod_id}}"]            # from StaffProfile.department.head_id
assignees: ["{{supervisor_id}}"]     # alias for line_manager_id
assignees: ["{{director_id}}"]       # from directorate head
assignees: ["{{lead_auditor}}"]      # GRC: chosen IA for this engagement
```

---

## 3. How `role:xxx` Works (Any Member of Role)

### Flow
```
Stage stored with: assignees = ["role:hr_officer"]
User takes action on stage
  → _is_user_in_assignees(user_id, user_email, stage.assignees, user_roles)
  → Checks: "hr_officer" in user_roles   (user_roles from JWT)
  → If yes → user is permitted to act
```

**No UUID ever enters the picture.** The role code is stored literally in `assignees`.  
No pre-selection needed. No IAM lookup needed at workflow-start time.

### Corporate patterns using `role:`
```yaml
# Any member of the role can handle it (pool-based):
assignees: ["role:hr_officer"]
assignees: ["role:hr_admin_manager"]
assignees: ["role:finance_accounts_manager"]
assignees: ["role:director_general"]
assignees: ["role:director_corporate_services"]
```

### Mixed (both at same stage)
```yaml
# Primary specific person PLUS role fallback:
assignees: ["{{director_id}}", "role:director_corporate_services"]
```
This means: the specific director AND anyone with that role can act.

---

## 4. GRC Entity Patterns Analysis

### AuditUniverse — `get_workflow_context()`
```python
return {
    "audit_universe_id": str(self.id),
    "fiscal_year_id": str(self.fiscal_year_id),
}
```
Workflow stages:
```python
"assignees": []   # Empty — no specific assignee
```
**Conclusion:** CIA review of universe uses `assignees: []` — open to any user with the `grc:audit_universe:approve` permission (enforced by view permission checks, not WO assignee list).

### AuditEngagement — `get_workflow_context()`
```python
return {
    "audit_engagement_id": str(self.id),
    "lead_auditor": str(self.lead_auditor),  # specific UUID
    "audit_plan_id": str(self.audit_plan_id),
}
```
Workflow stages:
```python
"assignees": ["{{lead_auditor}}"]  # resolved to specific UUID at workflow-start
```
**Conclusion:** `lead_auditor` UUID is stored on the model AND used for WO routing. This is the **correct FIMS pattern** — a UUID you store AND use for workflow.

---

## 5. The `reviewed_by` Question

### What the SRS says
> *"CIA reviews and approves the audit universe"*  
> *"Adopted reports shall be reviewed by the Audit Committee"*

The review is an **action**, not a pre-assignment. The SRS does not say "IA chooses who will review it when creating it."

### What `reviewed_by` actually does (VERIFIED)
`reviewed_by` currently serves a **dual purpose**:

1. **Notification routing** — `AuditUniverseService._publish_submission_notification()` reads `reviewed_by` to send the submission email to the right CIA user. If NULL, the notification falls back to notifying the **submitter** (the IA), not the CIA. So the picker has a real functional use right now.
2. **Audit trail** — records which CIA was designated as the reviewer.

It is **NOT used for WO routing** — `get_workflow_context()` does not pass it to WO, and `get_workflow_stages()` has `assignees: []`.

`advance_workflow_stage()` does **NOT** auto-set `reviewed_by = actor_id` at approval time. That code does not exist yet.

### Current behaviour summary
```
IA creates universe → reviewed_by = chosen CIA UUID (from picker)
Submit for approval → notification sent to that UUID ✓
CIA opens WO task → clicks Approve (via workflow-action endpoint)
Backend: reviewed_by is still whatever IA set; it is never auto-updated
```

### CRITICAL BUG found during verification ⚠️
`AuditUniverseWorkflowActionView.check_permissions()` requires **`grc:audit_universe:manage`** (IA role), but the CIA only has **`grc:audit_universe:approve`**.

This means the CIA **cannot call the workflow-action endpoint** to approve the universe. Only the IA (who has `manage`) can. The IA could self-approve their own universe through this endpoint — clearly wrong.

Fix needed:
```python
# audit_universe_views.py — AuditUniverseWorkflowActionView
# Change:
if not CanManageAuditUniverse().has_permission(request, self):
# To:
if not CanApproveAuditUniverse().has_permission(request, self):
```

### Fields that need a form picker vs. fields that don't

| Field | Form picker needed? | Why | Set when |
|---|---|---|---|
| `lead_auditor` | **YES** | Multiple IAs exist; IA must choose which leads this job | Create dialog |
| `audit_team` | **YES** | Multiple IAs; pick the team | Create dialog |
| `responsible_party` | **YES** | Any staff member; pick who implements the recommendation | Create dialog |
| `reviewed_by` (Universe) | **YES, keep for now** | Used to target notification to correct CIA on submission; if removed, notification falls back to notifying the IA submitter, not CIA | Create dialog |
| `reviewed_by_cia` (Plan) | **YES, keep for now** | Same reason | Create dialog |
| `reviewed_by` (Quarterly Report) | **YES, keep for now** | Same reason | Create dialog |

> **Future improvement**: if FCC always has exactly 1 CIA, you could auto-assign `reviewed_by` from a DB lookup of users with `chief_internal_auditor` role, removing the picker entirely and making notification automatic. This requires the `role_code` IAM filter fix (Section 6) to be in place.

---

## 6. IAM `role_code` Filter — The Reality

IAM's `UserLookupView` (`GET /users/lookup/`) only supports:
```python
filterset_fields = ['is_active', 'user_type']
```
`role_code` is **not a supported filter**. Passing `?role_code=chief_internal_auditor` returns ALL users silently — no error, no filtering.

### This affects the `lead_auditor` and `audit_team` dropdowns

The role-filtered GRC endpoint `GET /audit/lookups/users/?role_code=internal_auditor` **proxies to IAM** using `role_code`, but IAM ignores it → returns all users.

### Options to fix
| Option | Effort | Notes |
|---|---|---|
| **Add `role_code` filter to IAM `UserLookupView`** | 5 lines | Non-breaking; only activates when param present; correct approach |
| Filter in GRC by calling IAM per-user | N+1 problem | Not viable |
| Use `role:internal_auditor` in WO only (no picker) | Avoids filter | Only works for WO routing, not for form dropdowns |

**Recommended fix**: 5-line addition to `iam-service/apps/users/views.py`:
```python
def get_queryset(self):
    queryset = User.objects.filter(is_active=True).only(...)
    role_code = self.request.query_params.get('role_code')
    if role_code:
        queryset = queryset.filter(
            user_roles__role__code=role_code,
            user_roles__is_active=True
        ).distinct()
    return queryset
```

---

## 7. Summary of Recommended Actions

### Bug fix — CRITICAL (must fix before testing)
1. **Fix `AuditUniverseWorkflowActionView` permission** — change `CanManageAuditUniverse` → `CanApproveAuditUniverse`. Currently the CIA cannot approve their own universe through the WO action endpoint. The IA could self-approve.

### Correct the role-filter on dropdowns
2. **Add `role_code` filter to IAM `UserLookupView`** — 5 lines, non-breaking. Fixes the `lead_auditor`, `audit_team`, and `reviewed_by` dropdowns so they only show users with the correct role.

### Already done (correct)
- `lead_auditor` picker in `CreateAuditEngagementDialog` — correct pattern; just needs IAM `role_code` fix to filter properly.
- `audit_team` picker — same.
- `responsible_party` kept as all-users — correct; can be any staff.
- `reviewed_by` picker kept in Create dialog — correct for now; targets submission notification to the right CIA user.
- `get_workflow_context()` on `AuditEngagement` passes `lead_auditor` UUID — correct FIMS pattern.

### GRC workflow `assignees: []` on AuditUniverse
Consider updating to `"assignees": ["role:chief_internal_auditor"]` in `get_workflow_stages()`. Currently empty — any authenticated user could act via WO. Using `role:` would let WO's `_is_user_in_assignees()` enforce it automatically by JWT role.

---

## 8. Key Code References

| File | What it shows |
|---|---|
| `corporate-service/apps/core/workflows/workflows.yaml` | All templates with `{{uuid}}` vs `role:` patterns |
| `corporate-service/apps/core/workflow_context.py` | `merge_hierarchy_context()` — how UUIDs are derived from DB |
| `work-orchestration-service/apps/core/use_cases/create_workflow_plan.py` | `_resolve_assignees()`, `_resolve_placeholder()` — how `{{}}` → UUID |
| `work-orchestration-service/apps/api/views/workflow_views.py` | `_is_user_in_assignees()` — how `role:` is checked at action time |
| `grc-service/apps/core/models/audit_entities.py` | `AuditEngagement.get_workflow_context()` — `{{lead_auditor}}` source |
| `iam-service/apps/users/views.py` line 547 | `UserLookupView.get_queryset()` — where `role_code` filter is missing |
