# Verification of `x_said.md` Claims

**Verified by:** Source code audit (March 13, 2026)  
**Files checked:** `grc-service/apps/core/apps.py`, `grc-service/apps/core/workflows/workflows.yaml`,
`grc-service/config/permissions/grc-service.json`,
`work-orchestration-service/apps/core/use_cases/create_workflow_plan.py`,
`work-orchestration-service/apps/core/permissions_enforcement.py`,
`work-orchestration-service/apps/core/jwt_middleware.py`,
`iam-service/apps/authentication/jwt_enhanced.py`,
`iam-service/apps/roles/services.py`

---

## ✅ Correct

### Line numbers (Section 2)
> `_resolve_assignees` (line 260), `_stages_from_template` (line 285)

Confirmed exact:
```
238: def _resolve_placeholder(value: str, context: Dict[str, Any]) -> str:
260: def _resolve_assignees(assignees: List[str], context: Dict[str, Any]) -> List[str]:
285: def _stages_from_template(template, context: Optional[Dict[str, Any]] = None) -> List[StageInput]:
```

---

### `get_workflow_stages()` is dead code (Section 2)
Confirmed. `AuditUniverseService.submit_for_approval()` calls
`start_workflow(template_code=..., context=...)` and never passes inline stages.
WO resolves the template by ID and builds stages exclusively from the stored
YAML definition.

---

### 4-check permission walkthrough (Section 1, Step 4)
All 4 checks exist and execute in that order. See exact code in
`permissions_enforcement.py` lines 207–224.

---

### JWT uses bare role codes, not `full_code` (Section 4)
Confirmed in `iam-service/apps/authentication/jwt_enhanced.py` line 49:
```python
user_role_codes = [role.get('code') for role in user_roles_data if role.get('code')]
token['roles'] = user_role_codes   # bare code, not full_code
```

---

### WO JWT middleware sets `request.user_roles` (Section 4)
Confirmed in `work-orchestration-service/apps/core/jwt_middleware.py` line 113:
```python
request.user_roles = payload.get('roles', [])
```

---

### IAM role codes for GRC (Section 5)
All 5 codes confirmed in `grc-service/config/permissions/grc-service.json`:

| `role.code` | Exists in config? |
|---|---|
| `internal_auditor` | ✅ line 283 |
| `chief_internal_auditor` | ✅ line 334 |
| `audit_committee` | ✅ line 368 |
| `management` | ✅ line 382 |
| `auditee` | ✅ line 394 |

---

### `grc_reviewer` does not exist in IAM (Section 7, Q3)
Confirmed — zero occurrences of `grc_reviewer` anywhere in `iam-service/` or
`grc-service/config/`. The `working_paper_approval` stage currently uses
`["role:grc_reviewer"]` which **will never match** any JWT at runtime.
Q3 diagnosis is correct.

---

### Template re-registration methods (Section 8)
Both methods described are valid:
```bash
docker restart fims-grc-service               # triggers apps.ready() → Kafka publish
docker exec fims-grc-service python manage.py register_workflow_templates  # manual
```

---

## ❌ Wrong

### Class name `WorkflowTemplateRegistrar` (Section 1, Step 1)
> `apps.py → WorkflowTemplateRegistrar`

**Incorrect.** The class is **`WorkflowTemplateRegistry`** (not `Registrar`).
The instance is `workflow_template_registry` imported from
`apps.core.workflows.registry`.

Actual call chain in `apps.py`:
```python
def ready(self):
    self._load_workflow_templates()

def _load_workflow_templates(self):
    from .workflows.registry import workflow_template_registry
    workflow_template_registry.load_templates()
    workflow_template_registry.publish_templates()
```

---

### Template code `grc.audit_plan_approval` (Section 6 Fix Table)
The fix table lists `grc.audit_plan_approval` with 4 stages:
`cia_review`, `management_review`, `committee_review`, `commission_noting`.

**This template does not exist.** The actual code is **`grc.rbiap_approval`**
(Risk-Based Internal Audit Plan Approval).

Full list of codes actually in `workflows.yaml`:
```
grc.working_paper_approval           ✅ exists
grc.audit_universe_approval          ✅ exists
grc.rbiap_approval                   ← correct code (NOT grc.audit_plan_approval)
grc.engagement_lifecycle             ✅ exists
grc.engagement_notification_approval ✅ exists
grc.audit_memo_approval              ✅ exists
grc.audit_program_approval           ✅ exists
grc.audit_report_approval            ✅ exists
grc.quarterly_report_approval        ✅ exists
```

If the fix table is applied using `grc.audit_plan_approval`, it targets a
non-existent template. The 4 stages (`cia_review`, `management_review`,
`committee_review`, `commission_noting`) belong to **`grc.rbiap_approval`**
and must be fixed there.

---

## ⚠️ Imprecise (Minor)

### "Every approval stage has `assignees: []`" (Section 1, Step 3)
The document says all approval stages have `assignees: []`. That is not
fully accurate — three templates already have correct non-empty assignees:

| Template | Stage | Current assignees |
|---|---|---|
| `grc.working_paper_approval` | `working_paper_review` | `["{{lead_auditor}}"]` ✅ |
| `grc.working_paper_approval` | `working_paper_approval` | `["role:grc_reviewer"]` (wrong role, but non-empty) |
| `grc.engagement_lifecycle` | `planning` | `["{{lead_auditor}}"]` ✅ |
| `grc.engagement_lifecycle` | `fieldwork` | `["{{lead_auditor}}"]` ✅ |
| `grc.engagement_lifecycle` | `reporting` | `["{{lead_auditor}}"]` ✅ |

The accurate statement is: **all CIA / management / committee / commission
approval stages have `assignees: []`**. The lifecycle and working paper review
stages already populate assignees correctly.

---

### `plan.applicant_id` (Section 1, Step 4, Check #3)
The document describes check #3 as `plan.applicant_id == user_id`.

The actual code reads:
```python
applicant_id = plan.metadata.get('context', {}).get('applicant_id')
```

It is `plan.metadata["context"]["applicant_id"]`, not a direct model attribute.
Functionally the check is the same, but the source is the metadata context dict,
not a top-level plan field.

---

## Summary Table

| Claim | Status | Notes |
|---|---|---|
| `_resolve_assignees` at line 260 | ✅ Correct | |
| `_stages_from_template` at line 285 | ✅ Correct | |
| `get_workflow_stages()` is dead code | ✅ Correct | |
| JWT uses bare `role.code` | ✅ Correct | |
| WO middleware sets `request.user_roles` | ✅ Correct | |
| IAM has all 5 GRC role codes | ✅ Correct | |
| `grc_reviewer` missing from IAM | ✅ Correct | |
| Re-registration via restart or management command | ✅ Correct | |
| Class name `WorkflowTemplateRegistrar` | ❌ Wrong | It is `WorkflowTemplateRegistry` |
| Template code `grc.audit_plan_approval` | ❌ Wrong | It is `grc.rbiap_approval` |
| "Every approval stage has `assignees: []`" | ⚠️ Imprecise | 5 stages already have correct values |
| `plan.applicant_id` direct attribute | ⚠️ Imprecise | It is `plan.metadata.context.applicant_id` |
