# WO Service — GRC Workflow Template Analysis

**Date:** Session 3 — Audit Program SRS Completion  
**Status:** Pre-change analysis (read-only investigation)  
**Author:** Copilot Agent  

---

## 1. Problem Statement

GRC's `OrchestrationClient` queries WO's template API at runtime to resolve a
`workflow_type` string into a concrete template UUID. If WO has no matching
template, the client falls back to sending inline stages directly in the
`start_workflow` payload. The inline-stage path works but bypasses WO's
reusable template registry — a fragile, non-idiomatic approach.

**Current state:** WO's `seed_workflow_templates.py` contains **4 generic
templates** (`approval`, `commission`, `management`, `disposal`) — **none of
the 9 GRC-specific workflow types exist**.

The immediate fix needed for SRS compliance of `grc.audit_program_approval`
(the 2-stage IA → CIA approval) is to register
`grc_audit_program_approval` in WO.

---

## 2. WO Service Architecture

### Key Files

| Path | Purpose |
|------|---------|
| `apps/core/management/commands/seed_workflow_templates.py` | **Entry point** — defines `DEFAULT_TEMPLATES`, seeds on startup or manual run |
| `apps/core/use_cases/workflow_template_use_cases.py` | `CreateWorkflowTemplateUseCase` + `CreateWorkflowTemplateCommand` |
| `apps/core/entities/template.py` | `WorkflowTemplate` entity — fields: `id`, `name`, `workflow_type`, `definition`, `version`, `is_active` |
| `apps/api/` | REST API — `GET /plans/templates/` filtered by `workflow_type` |
| `apps/infrastructure/persistence/` | `DjangoWorkflowRepository` — `list_templates(workflow_type=..., limit=1)` |

### Template Registration Flow

```
seed_workflow_templates.py
    └── for each template in DEFAULT_TEMPLATES:
            CreateWorkflowTemplateCommand(name, workflow_type, definition)
            CreateWorkflowTemplateUseCase.execute(command)
                └── validate_form_schema(definition["stages"])
                └── WorkflowTemplateRepository.create(template)
```

### `CreateWorkflowTemplateCommand` Signature

```python
CreateWorkflowTemplateCommand(
    name: str,           # Human-readable name
    workflow_type: str,  # Machine key — GRC queries by this (e.g. "grc_audit_program_approval")
    definition: dict,    # Must contain "stages" list
)
```

### Stage Structure (per WO validation rules)

```python
{
    "definition_key": str,   # Unique key within template (e.g. "ia_program_review")
    "name": str,             # Display name
    "order": int,            # 0-based stage ordering
    "assignees": list,       # [] = dynamic assignment at runtime  
    "actions": [             # User-facing action buttons
        {
            "name": str,         # e.g. "approve"
            "label": str,        # e.g. "Approve"
            "next_state": str,   # e.g. "completed", "rejected", "pending"
        }
    ],
    "form_schema": {         # Fields rendered per stage
        "fields": [
            {
                "name": str,       # Field key
                "type": str,       # One of: text, textarea, select, radio, checkbox, date, number, email, file
                "required": bool,
            }
        ]
    },
    "metadata": dict,        # Optional — automation hooks, escalation reminders, webhooks
    "sla": dict,             # Optional — e.g. {"targetHours": 48}  (stored as-is, not validated by WO)
}
```

---

## 3. GRC → WO Template Code Mapping

Source: `grc-service/apps/infrastructure/external/orchestration_client.py`

```python
TEMPLATE_CODE_TO_WO_TYPE = {
    "grc.working_paper_approval":           "grc_working_paper_approval",
    "grc.audit_universe_approval":          "grc_audit_universe_approval",
    "grc.rbiap_approval":                   "grc_rbiap_approval",
    "grc.engagement_lifecycle":             "grc_engagement_lifecycle",
    "grc.engagement_notification_approval": "grc_engagement_notification_approval",
    "grc.audit_report_approval":            "grc_audit_report_approval",
    "grc.audit_memo_approval":              "grc_audit_memo_approval",
    "grc.audit_program_approval":           "grc_audit_program_approval",   # ← THIS SESSION
    "grc.quarterly_report_approval":        "grc_quarterly_report_approval",
}
```

### WO Templates Currently Seeded (pre-change)

| `workflow_type` | Name | Status |
|-----------------|------|--------|
| `approval` | General Document Approval | ✅ Seeded |
| `commission` | Commission Vetting Workflow | ✅ Seeded |
| `management` | Management Review Workflow | ✅ Seeded |
| `disposal` | Disposal Approval Workflow | ✅ Seeded |
| `grc_audit_program_approval` | GRC Audit Program Approval | ❌ **MISSING** |
| `grc_working_paper_approval` | GRC Working Paper Approval | ❌ Missing |
| `grc_audit_universe_approval` | GRC Audit Universe Approval | ❌ Missing |
| `grc_rbiap_approval` | GRC RBIAP Approval | ❌ Missing |
| `grc_engagement_lifecycle` | GRC Engagement Lifecycle | ❌ Missing |
| `grc_engagement_notification_approval` | GRC Engagement Notification Approval | ❌ Missing |
| `grc_audit_report_approval` | GRC Audit Report Approval | ❌ Missing |
| `grc_audit_memo_approval` | GRC Audit Memo Approval | ❌ Missing |
| `grc_quarterly_report_approval` | GRC Quarterly Report Approval | ❌ Missing |

**Scope of this session:** Only `grc_audit_program_approval` is required to
achieve 100% SRS compliance for the Audit Program workflow (P2-GAP AuditProgram
approval). Other GRC template types will be added as their respective SRS
requirements are implemented.

---

## 4. GRC `AuditProgram.get_workflow_stages()` — Source of Truth

Source: `grc-service/apps/core/models/audit_entities.py`, line 2650

```python
def get_workflow_stages(self) -> list:
    return [
        {
            "definition_key": "ia_program_review",
            "name": "IA Review",
            "order": 0,
            "assignees": [],
            "actions": [
                {"name": "approve", "label": "Approve", "next_state": "completed"},
                {"name": "return",  "label": "Return to Lead Auditor", "next_state": "rejected"},
            ],
            "form_schema": {
                "fields": [{"name": "comments", "type": "textarea", "required": False}]
            },
            "sla": {"targetHours": 48},
        },
        {
            "definition_key": "cia_program_approval",
            "name": "CIA Approval",
            "order": 1,
            "assignees": [],
            "actions": [
                {"name": "approve", "label": "Approve", "next_state": "completed"},
                {"name": "return",  "label": "Return to IA", "next_state": "pending"},
            ],
            "form_schema": {
                "fields": [{"name": "comments", "type": "textarea", "required": False}]
            },
            "sla": {"targetHours": 72},
        },
    ]
```

The WO template definition must mirror these stage `definition_key` values
exactly — WO uses them to map stage completions back to GRC's Kafka consumer
(`_handle_audit_program_completion`).

---

## 5. The Change

### File to Edit

```
work-orchestration-service/apps/core/management/commands/seed_workflow_templates.py
```

### What to Add

Append to `DEFAULT_TEMPLATES` list:

```python
{
    "name": "GRC Audit Program Approval",
    "workflow_type": "grc_audit_program_approval",
    "definition": {
        "stages": [
            {
                "definition_key": "ia_program_review",
                "name": "IA Review",
                "order": 0,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve",                    "next_state": "completed"},
                    {"name": "return",  "label": "Return to Lead Auditor",     "next_state": "rejected"},
                ],
                "form_schema": {
                    "fields": [
                        {"name": "comments", "type": "textarea", "required": False},
                    ]
                },
                "metadata": {
                    "description": "Internal Audit review of the audit program before CIA approval.",
                    "sla": {"targetHours": 48},
                },
            },
            {
                "definition_key": "cia_program_approval",
                "name": "CIA Approval",
                "order": 1,
                "assignees": [],
                "actions": [
                    {"name": "approve", "label": "Approve",      "next_state": "completed"},
                    {"name": "return",  "label": "Return to IA", "next_state": "pending"},
                ],
                "form_schema": {
                    "fields": [
                        {"name": "comments", "type": "textarea", "required": False},
                    ]
                },
                "metadata": {
                    "description": "Chief Internal Auditor final approval of the audit program.",
                    "sla": {"targetHours": 72},
                },
            },
        ]
    },
},
```

**Note on `sla`:** GRC's inline-stages put `sla` at stage root; WO's
`validate_form_schema` only validates `form_schema.fields`, so top-level `sla`
in stage dict is stored as-is. For the seeded template, `sla` is moved into
`metadata` for clarity — this does not affect WO's behavior.

---

## 6. How GRC Resolves the Template

```
AuditProgramApproveView.post()
    └── program.start_workflow(template_code="grc.audit_program_approval", ...)
        └── OrchestrationClient.start_workflow(template_code, ...)
            └── TEMPLATE_CODE_TO_WO_TYPE["grc.audit_program_approval"]
                → wo_type = "grc_audit_program_approval"
            └── _get_template_id_by_code(wo_type)
                → GET /plans/templates/?workflow_type=grc_audit_program_approval&limit=1
                → returns template.id (UUID)        ← enabled by seeding
            └── POST /plans/   { template_id: <uuid>, entity_id: ..., stages: [] }
                → WO creates WorkflowPlan
                → GRC stores plan_id on AuditProgram
```

---

## 7. Flow After Seeding

```
CIA clicks "Approve" in AuditProgram detail dialog
    → POST /api/grc/programs/{id}/approve/
    → AuditProgramApproveView.post()
    → program.status = "under_review"
    → start_workflow() → WO plan created with 2 stages
    → WO sends notifications to IA team (stage 1)

IA approves stage 1 (ia_program_review) in WO portal
    → WO publishes Kafka event "workflow.completed" to grc-service
    → GRC consumer: _handle_audit_program_completion()
        → outcome == "approved" → status = "approved", approval_date = now
        → DRS stamp triggered (non-blocking)

CIA approves stage 2 (cia_program_approval) in WO portal
    → Same Kafka path → final status = "approved"
    → Engagement workflow unlock: hasApprovedProgram = true
```

---

## 8. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| WO breaks if stage validation is stricter than expected | Low | `validate_form_schema` only validates `form_schema.fields`; `textarea` is a valid type |
| Seeding fails if template already exists | Low | Seed command checks `existing = repo.list_templates(workflow_type=..., limit=1)` and skips if found |
| Seed must be re-run after adding template | Low | Run `python manage.py seed_workflow_templates` in WO container |
| GRC falls back to inline stages if WO unreachable | None | 3-tier fallback already implemented in `OrchestrationClient.start_workflow()` |
| Other GRC `grc_*` types still missing from WO | Medium | Acceptable — each type uses inline-stage fallback until seeded in future sessions |

---

## 9. Verification Commands

### Check WO container has the new template after seeding

```bash
docker compose exec work-orchestration-service python manage.py shell -c "
from apps.infrastructure.persistence.models import WorkflowTemplateModel
qs = WorkflowTemplateModel.objects.filter(workflow_type__startswith='grc')
for t in qs: print(t.workflow_type, t.id, t.is_active)
"
```

### Re-run seed (idempotent — safe to run multiple times)

```bash
# from work-orchestration-service/ directory
docker compose exec work-orchestration-service python manage.py seed_workflow_templates --recreate
```

### Verify GRC can resolve the template UUID at runtime

```bash
docker compose exec grc-service python manage.py shell -c "
from apps.infrastructure.external.orchestration_client import OrchestrationClient
client = OrchestrationClient()
wo_type = client.TEMPLATE_CODE_TO_WO_TYPE['grc.audit_program_approval']
tid = client._get_template_id_by_code('grc.audit_program_approval')
print('workflow_type:', wo_type)
print('template_id:', tid)
"
```

Expected: prints a UUID (not `None`).

---

## 10. Files Changed This Session

| File | Change |
|------|--------|
| `work-orchestration-service/apps/core/management/commands/seed_workflow_templates.py` | Added `grc_audit_program_approval` entry to `DEFAULT_TEMPLATES` |

**Not changed (already complete):**
- `grc-service/apps/infrastructure/external/orchestration_client.py` — template code mapping correct
- `grc-service/apps/core/models/audit_entities.py` — `get_workflow_stages()` correct
- `grc-service/apps/infrastructure/messaging/kafka_consumer.py` — `_handle_audit_program_completion()` correct
- `grc-service/apps/api/views/audit_program_views.py` — `AuditProgramApproveView` correct
- `grc-service/apps/core/migrations/0016_*` — applied
