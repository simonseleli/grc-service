# WO 403 Bug: CIA Reviewer Cannot Access Audit Universe Workflow Plan

**Date:** March 2026  
**Finding Type:** Bug / Missing Implementation  
**Based on:** Deep analysis of Corporate service + WO source code  
**Symptom:** CIA reviewer (e.g. `cia@fcc.go.tz`) gets `403 Forbidden` when trying
to `GET /api/v1/workflow/plans/<plan_id>/` after a workflow is submitted.

---

## How Template Registration Actually Works (Both Services)

Both GRC and Corporate use the **same Kafka-based registration pattern**:

```
Service (GRC or Corporate)
  └── WorkflowTemplateRegistry.publish_templates()
          └── loads workflows.yaml
          └── publishes Kafka message to topic "workflow-templates":
              {
                event_type: "workflow.template.registered",
                source_service: "grc-service",
                template: { code: "grc.audit_universe_approval", definition: {...} }
              }

WO: WorkflowTemplateRegistrationConsumer (workflow_template_consumer.py)
  └── receives message
  └── WorkflowTemplateModel.objects.create(code="grc.audit_universe_approval", ...)
      ← stores with code field populated

GRC OrchestrationClient._get_template_id_by_code("grc.audit_universe_approval")
  └── GET /api/v1/workflow/templates/   (returns ALL templates)
  └── client iterates list, finds template where code == "grc.audit_universe_approval"
  └── returns template UUID
```

**This means:** the GRC template YAML (`assignees: []`) is exactly what gets stored
in WO and used to create stages. There is no override or fallback.

> **Important note:** `register_workflow_templates.py` references 
> `OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE` — this attribute **no longer
> exists** in the current client. That comment is stale. The management command
> still works for the `--fetch` verification path but the reference is dead code.

---

## The Bug In One Sentence

The `cia_review` stage is created with **`assignees: []`** (empty), because the
YAML template defines it that way and the context passed at submission time
contains no `cia_reviewer_id` variable to resolve. WO's
`CanViewWorkflowAsParticipant` correctly rejects the CIA reviewer because they are
neither the initiator, the applicant, nor in any stage's assignee list.

---

## Full Call Flow (what actually happens)

```
[GRC] AuditUniverseService.submit_for_approval()
      └── universe.get_workflow_context()
              returns: {
                "audit_universe_id": "...",
                "fiscal_year_id":    "..."
              }
              ← MISSING: "cia_reviewer_id": str(universe.reviewed_by)

      └── context['applicant_id'] = submitter_id   # set in service layer

      └── OrchestrationClient.start_workflow(
              template_code = "grc.audit_universe_approval",
              context = { audit_universe_id, fiscal_year_id, applicant_id },
              initiator_id = submitter_id,
          )
          └── _get_template_id_by_code("grc.audit_universe_approval")
              → GET /templates/ → finds UUID (template IS registered via Kafka)

          └── POST /plans/ {
                template_id: <uuid>,
                metadata.context: {
                  audit_universe_id, fiscal_year_id, applicant_id
                  ← NO cia_reviewer_id
                }
              }

[WO] CreateWorkflowPlanUseCase
      └── _stages_from_template(template, context)
              reads YAML stage: definitionKey="cia_review", assignees=[]
              _resolve_assignees([], context) → []    ← nothing to resolve

      └── Stage persisted: assignees = []

[CIA John Mbwana] GET /api/v1/workflow/plans/<plan_id>/

[WO] WorkflowPlanDetailView → CanViewWorkflowAsParticipant.has_permission()
      1. workflow:plan:read permission?       → ❌ (CIA role has no such perm)
      2. is created_by (initiator)?           → ❌ (Mary Simba submitted it)
      3. is applicant_id in metadata?         → ❌ (applicant_id = Mary Simba)
      4. is in any stage.assignees?           → ❌ (assignees = [])
      Result: 403 Forbidden ← CONFIRMED ROOT CAUSE
```

---

## Deep Dive: The Corporate Pattern (100% Source-Verified)

### Step 1 — Template YAML uses one of two assignee patterns

**Pattern A — Dynamic placeholder (specific person, resolved at plan-creation time):**
```yaml
# corporate-service/apps/core/workflows/workflows.yaml

# leave_application: stage 1
- definitionKey: "leave_head_approval"
  assignees: ["{{line_manager_id}}"]        # resolved from context

# imprest_application: stage 1
- definitionKey: "imprest_hod_approval"
  assignees: ["{{hod_id}}"]                 # resolved from context

# petty_cash_requisition: stage 1
- definitionKey: "petty_cash_custodian_approval"
  assignees: ["{{custodian_id}}"]           # explicitly set in context

# internal_payment: stage 1
- definitionKey: "payment_hod_approval"
  assignees: ["{{first_approver_id}}"]      # derived logic in model/service
```

**Pattern B — Role-based (anyone with role can act):**
```yaml
- definitionKey: "payment_finance_verification"
  assignees: ["role:finance_officer"]

- definitionKey: "payment_fam_approval"
  assignees: ["role:finance_accounts_manager"]

- definitionKey: "leave_director_approval"
  assignees: ["{{director_id}}", "role:director_corporate_services"]  # BOTH patterns combined
```

> **Key observation:** Corporate **never** leaves `assignees: []` on an active
> review/approval stage. Every stage that needs human action has either a
> `{{placeholder}}` or a `role:xxx` (or both).

---

### Step 2 — The Model resolves dynamic IDs into the context

**Case A — Hierarchy-based (using `merge_hierarchy_context`):**
```python
# corporate-service/apps/hr/services/leave_application_service.py

context = {
    'entity_type': 'leave_application',
    'applicant_id': str(application.applicant_id),
    ...
}
# merge_hierarchy_context walks StaffProfile FK chain:
#   staff.line_manager.user_id  → line_manager_id
#   staff.department.head_id    → hod_id
#   directorate head_id         → director_id
context = merge_hierarchy_context(context, str(application.applicant_id))
# → context now has line_manager_id, hod_id, director_id all set to real IAM UUIDs
```

**Case B — Explicit ID (custodian picked by user):**
```python
# corporate-service/apps/finance/services/petty_cash_workflow_service.py

context = { 'entity_type': 'petty_cash_requisition', ... }
if custodian_id:
    context['custodian_id'] = custodian_id      # IAM UUID passed directly
context = merge_hierarchy_context(context, ...)  # also adds hod_id etc.
```

**Case C — Derived logic in model's `get_workflow_context()`:**
```python
# corporate-service/apps/infrastructure/persistence/models.py (InternalMemo)

def get_workflow_context(self) -> dict:
    context = { 'entity_type': 'internal_memo', ... }
    context = merge_hierarchy_context(context, str(self.officer_id))

    # If applicant IS the HOD, they can't approve their own request
    # → escalate to director instead
    if applicant_is_hod:
        context['first_approver_id'] = (
            context.get('director_id') or
            context.get('line_manager_id') or
            context.get('hod_id')
        )
    else:
        context['first_approver_id'] = context.get('hod_id')
    return context
```

---

### Step 3 — WO resolves placeholders at plan-creation time

```python
# work-orchestration-service/apps/core/use_cases/create_workflow_plan.py

def _resolve_placeholder(value: str, context: Dict) -> str:
    """{{variable_name}} → context[variable_name]. Returns original if not found."""
    match = re.match(r'^\{\{(\w+)\}\}$', value.strip())
    if match:
        resolved = context.get(match.group(1))
        if resolved:
            return str(resolved)
    return value   # unresolved placeholders kept as-is

def _resolve_assignees(assignees: List[str], context: Dict) -> List[str]:
    resolved = []
    for assignee in assignees:
        value = _resolve_placeholder(assignee, context)
        # Skip if still {{unresolved}} — don't store literal placeholder in DB
        if value.strip().startswith('{{') and value.strip().endswith('}}'):
            logger.warning("Skipping unresolved assignee placeholder: %s", assignee)
            continue
        if value:
            resolved.append(value)
    return resolved
```

The context is read from `metadata.context` in the plan creation payload:
```python
# work-orchestration-service/apps/core/use_cases/create_workflow_plan.py
context = command.metadata.get('context', {}) if command.metadata else {}
stages_input = _stages_from_template(template, context)
```

---

### Step 4 — WO permission check at view time

```python
# work-orchestration-service/apps/core/permissions_enforcement.py

class CanViewWorkflowAsParticipant(BasePermission):
    def has_permission(self, request, view):
        # Gate 1: IAM permission (broad — any workflow plan)
        if _check_permission(request, 'workflow:plan:read'):
            return True

        # Gate 2: Participant check (scoped to this specific plan)
        plan = repo.get_plan(plan_id)
        user_id = _get_user_id(request)
        user_roles = _get_user_roles(request)   # from JWT token

        if str(plan.created_by) == str(user_id):           return True  # initiator
        if str(applicant_id) == str(user_id):              return True  # applicant
        for stage in plan.stages:
            if _is_user_in_assignees(user_id, stage.assignees, user_roles):
                return True                                              # assignee

        return False

def _is_user_in_assignees(user_id, assignees, user_roles):
    for assignee in assignees:
        if str(assignee) == str(user_id):           return True  # UUID match
        if assignee.startswith('role:'):
            role_code = assignee[5:]
            if role_code in user_roles:             return True  # role match
    return False
```

`user_roles` comes from the JWT token (set by JWT middleware from IAM claims):
```python
jwt_roles = getattr(request, 'user_roles', None)
# e.g. ["chief_internal_auditor", "grc_reviewer", ...]
```

---

## GRC's Two Missing Pieces

### Missing Piece 1 — `get_workflow_context()` does not emit `cia_reviewer_id`

```python
# grc-service/apps/core/models/audit_entities.py  (AuditUniverse)

def get_workflow_context(self) -> dict:
    return {
        "audit_universe_id": str(self.id),
        "fiscal_year_id":    str(self.fiscal_year_id),
        # ← MISSING: "cia_reviewer_id": str(self.reviewed_by)
        #   even though reviewed_by is a UUID field on the model, always set
    }
```

The `reviewed_by` UUID IS set on the model (it's required at submission time),
but it's never put into the workflow context.

### Missing Piece 2 — `workflows.yaml` `cia_review` stage has empty assignees

```yaml
# grc-service/apps/core/workflows/workflows.yaml

- code: "grc.audit_universe_approval"
  definition:
    stages:
      - definitionKey: "cia_review"
        assignees: []               # ← should be ["{{cia_reviewer_id}}"]
                                    #   or at minimum ["role:chief_internal_auditor"]
```

Both pieces must be fixed together for pattern A (explicit reviewer).

---

## Why `get_workflow_stages()` Is Dead Code

The AuditUniverse model has a correct stage definition:

```python
def get_workflow_stages(self) -> list:
    return [{"definition_key": "cia_review", "assignees": ["role:chief_internal_auditor"], ...}]
```

But `AuditUniverseService.submit_for_approval()` never calls it. The client
`start_workflow()` only accepts `template_code` + `context` — inline stage
injection is not supported in the current implementation. This method is dead code.

---

## The Fix (100% Aligned with Corporate)

### Apply Both Patterns Together

**Step 1 — Add `cia_reviewer_id` to `get_workflow_context()` in the model:**

```python
# grc-service/apps/core/models/audit_entities.py  (AuditUniverse)

def get_workflow_context(self) -> dict:
    ctx = {
        "audit_universe_id": str(self.id),
        "fiscal_year_id":    str(self.fiscal_year_id),
    }
    # Always set applicant_id (set again in service layer, but belt+suspenders)
    # Add cia_reviewer_id so the YAML {{placeholder}} resolves to the chosen reviewer
    if self.reviewed_by:
        ctx["cia_reviewer_id"] = str(self.reviewed_by)
    return ctx
```

This mirrors exactly how `PettyCashRequisition` sets `custodian_id` or 
`InternalMemo.get_workflow_context()` sets `first_approver_id` — a concrete
IAM user UUID explicitly placed into context before `start_workflow` is called.

**Step 2 — Update `workflows.yaml` to reference the placeholder:**

```yaml
# grc-service/apps/core/workflows/workflows.yaml

- code: "grc.audit_universe_approval"
  name: "Audit Universe Approval"
  workflow_type: "grc"
  version: 2    # bump version so WO consumer updates the template
  definition:
    stages:
      - definitionKey: "cia_review"
        name: "CIA Review"
        order: 1
        assignees: ["{{cia_reviewer_id}}"]    # ← was [] previously
        ...
```

**Step 3 — Re-register the template via Kafka:**

```bash
docker exec <grc-container> python manage.py register_workflow_templates
```

WO's `WorkflowTemplateRegistrationConsumer` will update the stored template
(version bump causes it to overwrite the existing record).

> **Fallback safety:** if `cia_reviewer_id` is missing from context (unlikely
> since `reviewed_by` is required), WO skips the unresolved placeholder and
> the stage gets `assignees = []`. To prevent silent failures, add a guard:
>
> ```python
> if not context.get('cia_reviewer_id'):
>     raise ValueError("reviewed_by must be set before submitting for approval")
> ```

---

## Option: Role-Based (Simpler, but Less Precise)

If ANY CIA user should be able to review (not just the one chosen at creation):

```yaml
- definitionKey: "cia_review"
  assignees: ["role:chief_internal_auditor"]
```

- No context change needed
- John Mbwana gets access because his JWT roles include `chief_internal_auditor`
- Less aligned with corporate's explicit-reviewer pattern
- Corporate uses `role:xxx` only for organizational roles (finance_officer, etc.)
  where any role-holder is appropriate; it uses `{{placeholder}}` when a specific
  person is designated

---

## How Templates Get Into WO (Confirmed Flow)

```
GRC workflows.yaml (assignees: [])
         ↓ register_workflow_templates management command
         ↓ Kafka message: {event_type: "workflow.template.registered", template.code: "grc.audit_universe_approval"}
         ↓ WO WorkflowTemplateRegistrationConsumer
WO DB: WorkflowTemplateModel(code="grc.audit_universe_approval", definition={stages:[{assignees:[]}]})
         ↓ GRC OrchestrationClient._get_template_id_by_code()
         ↓ GET /api/v1/workflow/templates/ → client finds by code
template_id resolved → POST /plans/ with template_id + context
         ↓ _stages_from_template(template, context)
         ↓ _resolve_assignees([], context) = []
Stage saved: assignees = []  ← THIS IS THE BUG
```

After the fix:
```
workflows.yaml (assignees: ["{{cia_reviewer_id}}"])  + version bump
         ↓ re-register
WO DB updated: definition={stages:[{assignees:["{{cia_reviewer_id}}"]}]}
         ↓ submit_for_approval()
         ↓ get_workflow_context() → {"cia_reviewer_id": "6cf919b4-..."}
         ↓ _resolve_assignees(["{{cia_reviewer_id}}"], context)
         ↓ → ["6cf919b4-8dbf-4f8a-8b48-885e1b9fb77c"]
Stage saved: assignees = ["6cf919b4-..."]  ← John Mbwana's UUID
         ↓ CanViewWorkflowAsParticipant → is in stage.assignees → ✅ 200 OK
```

---

## Summary Table

| Item | Corporate | GRC (today) | GRC (after fix) |
|---|---|---|---|
| Template registration | Kafka → WO | Kafka → WO (same) | same |
| Stage assignees (specific) | `["{{hod_id}}"]` etc. | `[]` ← bug | `["{{cia_reviewer_id}}"]` |
| Stage assignees (role) | `["role:finance_officer"]` | N/A | could add `["role:chief_internal_auditor"]` |
| Context building | `merge_hierarchy_context()` or explicit | `get_workflow_context()` missing reviewer | add `cia_reviewer_id` to context |
| WO placeholder resolution | ✅ works | N/A (empty list) | ✅ will work |
| Reviewer can view plan | ✅ | ❌ 403 | ✅ |
| Template re-registration | `register_workflow_templates` | same command | run with version bump |

| Root cause | Fix |
|---|---|
| `get_workflow_context()` omits `reviewed_by` | Add `ctx["cia_reviewer_id"] = str(self.reviewed_by)` |
| `workflows.yaml` has `assignees: []` | Change to `["{{cia_reviewer_id}}"]` and bump version |
| Template not re-registered after YAML change | Run `register_workflow_templates` in GRC container |
