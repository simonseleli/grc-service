# GRC → WO Workflow Template Registration via Kafka

**Status:** Design guide — not yet implemented  
**Precedent:** Notification template registration (GRC → WO via `notification-templates` topic)  
**Goal:** GRC publishes its workflow template definitions to WO at startup via Kafka; WO stores them in its DB so `OrchestrationClient._get_template_id_by_code()` can resolve UUIDs instead of falling back to inline stages.

---

## 1. Why and What

### The problem today

GRC's `OrchestrationClient.start_workflow()` has a three-tier fallback:

```
1. Resolve template UUID from WO via workflow_type  (preferred — template_id in plan)
   ↓ template not found in WO DB
2. Send inline stages from entity.get_workflow_stages()  (fallback — works but bypasses WO templates)
   ↓ stages also missing
3. Log warning, skip workflow creation
```

Tier 2 works. But tier 1 is preferable because:
- WO console shows a named template, not anonymous stage blobs
- WO can enforce SLA definitions from the template
- Assignee resolution via `{{context_var}}` is template-driven
- Template versioning means stage-graph changes can be audited

The blocker: WO has no mechanism for a service to register workflow templates from outside. WO's `seed_workflow_templates.py` seeds WO-native generic templates only. WO's template API exposes only GET (no POST).

### The solution

Follow the **notification template Kafka pattern** already established (GRC → `notification-templates` topic → WO's `TemplateRegistrationConsumer`), but for workflow templates instead:

```
GRC startup
  → WorkflowTemplatePublisher.publish()
  → Kafka topic: workflow-templates
  → WO: WorkflowTemplateRegistrationConsumer
  → CreateWorkflowTemplateUseCase.execute()
  → WO DB: WorkflowPlanModel template row
  → OrchestrationClient._get_template_id_by_code() → UUID found ✓
```

---

## 2. What Already Exists (Do Not Touch)

| File | Purpose | Status |
|---|---|---|
| `grc-service/apps/core/workflows/workflows.yaml` | All GRC workflow template definitions | ✅ Complete — all templates including `grc.audit_program_approval` already defined |
| `grc-service/apps/core/workflows/registry.py` | Loads YAML locally for inline-stages fallback | ✅ Works — keep as-is, still used for inline fallback |
| `grc-service/apps/core/templates/registry.py` | **Notification** template Kafka publisher — exact pattern to copy | ✅ Reference |
| `grc-service/apps/core/apps.py` | Django AppConfig `ready()` — already calls `_register_notification_templates()` | ✅ Add new hook here |
| `grc-service/apps/infrastructure/external/orchestration_client.py` | `TEMPLATE_CODE_TO_WO_TYPE` mapping, `_get_template_id_by_code()` | ✅ Already correct — no changes needed |
| `grc-service/apps/core/management/commands/register_workflow_templates.py` | CLI verification tool | ✅ Update docstring only |
| `wo/apps/core/consumers/template_registration_consumer.py` | **Notification** template Kafka consumer — exact pattern to copy | ✅ Reference |
| `wo/apps/core/management/commands/run_kafka_consumer.py` | Starts all WO Kafka consumers | ✅ Add new consumer here |
| `wo/apps/core/use_cases/workflow_template_use_cases.py` | `CreateWorkflowTemplateUseCase.execute()` + `CreateWorkflowTemplateCommand` | ✅ Existing use-case — consumer calls this |

---

## 3. Kafka Topic and Event Schema

### Topic name

```
workflow-templates
```

Add to both services' settings as `KAFKA_WORKFLOW_TEMPLATES_TOPIC`.

### Event: `workflow.template.registered`

Published by GRC, consumed by WO.

```json
{
  "event_type": "workflow.template.registered",
  "event_version": "1.0",
  "timestamp": "2026-03-10T08:00:00.000Z",
  "source_service": "grc-service",
  "source_version": "1.0.0",
  "template": {
    "code": "grc.audit_program_approval",
    "name": "Audit Program Approval",
    "workflow_type": "grc_audit_program_approval",
    "version": 1,
    "definition": {
      "stages": [
        {
          "definitionKey": "ia_program_review",
          "name": "IA Review",
          "order": 1,
          "assignees": [],
          "actions": [
            { "name": "approve", "label": "Approve",                "nextState": "completed" },
            { "name": "return",  "label": "Return to Lead Auditor", "nextState": "rejected" }
          ],
          "sla": { "durationMinutes": 2880, "breachStrategy": "notify" }
        },
        {
          "definitionKey": "cia_program_approval",
          "name": "CIA Approval",
          "order": 2,
          "assignees": [],
          "actions": [
            { "name": "approve", "label": "Approve",      "nextState": "completed" },
            { "name": "return",  "label": "Return to IA", "nextState": "pending" }
          ],
          "sla": { "durationMinutes": 4320, "breachStrategy": "notify" }
        }
      ]
    }
  }
}
```

**Key mapping rule:** `template.workflow_type` in the event = the value in `OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE[template.code]`. The consumer stores it as `workflow_type` in the WO template row — exactly what `_get_template_id_by_code()` queries against.

**YAML→Event field name translation:**

| `workflows.yaml` key | Kafka event key | WO DB column |
|---|---|---|
| `code` | `template.code` | (stored in `metadata` or as label, not a DB column) |
| `name` | `template.name` | `name` |
| (derived from `TEMPLATE_CODE_TO_WO_TYPE`) | `template.workflow_type` | `workflow_type` |
| `version` | `template.version` | `version` |
| `definition.stages[].definitionKey` | same | `definition.stages[].definition_key` ¹ |

¹ WO's `CreateWorkflowTemplateCommand` uses snake_case internally (`definition_key`, `next_state`). The consumer must translate `definitionKey`→`definition_key` and `nextState`→`next_state` when building the `definition` dict passed to the use-case. See §5 consumer implementation for the exact normalisation function.

---

## 4. GRC Side — What to Build

### 4.1  `grc-service/apps/core/workflows/workflow_template_publisher.py`  *(new file)*

Copy the structure of `grc-service/apps/core/templates/registry.py` (notification publisher). Key differences:

| Notification publisher | Workflow template publisher |
|---|---|
| Reads `notifications.yaml` | Reads `workflows.yaml` (via `WorkflowTemplateRegistry`) |
| Topic: `notification-templates` | Topic: `workflow-templates` |
| Event type: `template.registered` | Event type: `workflow.template.registered` |
| Validates notification fields (code, channels, subject…) | Validates workflow fields (code, workflow_type, definition.stages) |
| No code→workflow_type mapping needed | Must map `code` → `workflow_type` using `OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE` |

Minimal class outline:

```python
class WorkflowTemplatePublisher:
    """
    Publishes GRC workflow templates to WO via the workflow-templates Kafka topic.
    Mirrors apps/core/templates/registry.py (notification template publisher).
    """

    def __init__(self):
        self.topic = getattr(settings, 'KAFKA_WORKFLOW_TEMPLATES_TOPIC', 'workflow-templates')
        self.service_name = 'grc-service'
        self.service_version = getattr(settings, 'SERVICE_VERSION', '1.0.0')
        self._producer: Optional[KafkaProducer] = None

    def _get_producer(self) -> Optional[KafkaProducer]: ...  # same pattern as notification publisher

    def _build_event(self, template: Dict[str, Any], workflow_type: str) -> Dict[str, Any]:
        return {
            'event_type': 'workflow.template.registered',
            'event_version': '1.0',
            'timestamp': timezone.now().isoformat(),
            'source_service': self.service_name,
            'source_version': self.service_version,
            'template': {
                'code': template['code'],
                'name': template['name'],
                'workflow_type': workflow_type,
                'version': template.get('version', 1),
                'definition': template['definition'],
            },
        }

    def publish(self) -> int:
        """
        Publish all templates from workflows.yaml that have a matching
        TEMPLATE_CODE_TO_WO_TYPE entry.  Returns the count published.
        """
        from apps.core.workflows.registry import WorkflowTemplateRegistry
        from apps.infrastructure.external.orchestration_client import OrchestrationClient

        registry = WorkflowTemplateRegistry()
        code_to_wo_type = OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE
        producer = self._get_producer()
        if not producer:
            return 0

        published = 0
        for template in registry.list_templates():
            code = template.get('code', '')
            wo_type = code_to_wo_type.get(code)
            if not wo_type:
                logger.debug("Skipping template %s — no TEMPLATE_CODE_TO_WO_TYPE entry", code)
                continue
            event = self._build_event(template, wo_type)
            try:
                future = producer.send(topic=self.topic, key=code, value=event)
                future.get(timeout=10)
                published += 1
                logger.info("Published workflow template: %s → workflow_type=%s", code, wo_type)
            except Exception as exc:
                logger.error("Failed to publish workflow template %s: %s", code, exc)
        return published
```

### 4.2  `grc-service/apps/core/apps.py`  *(add one method + one call)*

In `CoreConfig.ready()`, after `_register_notification_templates()`, add:

```python
if not self._is_testing():
    self._register_workflow_templates_via_kafka()
```

New method:

```python
def _register_workflow_templates_via_kafka(self) -> None:
    """
    Publish GRC workflow template definitions to WO via the workflow-templates
    Kafka topic.  WO's WorkflowTemplateRegistrationConsumer stores them in its DB
    so OrchestrationClient._get_template_id_by_code() can resolve UUIDs at runtime.
    
    Pattern: mirrors _register_notification_templates() / TemplateRegistry.
    """
    try:
        from apps.core.workflows.workflow_template_publisher import WorkflowTemplatePublisher
        publisher = WorkflowTemplatePublisher()
        count = publisher.publish()
        if count:
            logger.info("GRC: published %d workflow template(s) to WO via Kafka", count)
        else:
            logger.warning(
                "GRC: no workflow templates published — check KAFKA_WORKFLOW_TEMPLATES_TOPIC "
                "and TEMPLATE_CODE_TO_WO_TYPE entries in OrchestrationClient"
            )
    except Exception as exc:
        logger.error(
            "GRC: workflow template Kafka registration failed: %s. "
            "OrchestrationClient will fall back to inline stages.",
            exc,
            exc_info=True,
        )
```

> **Note on startup race condition:** GRC publishes at startup. WO's consumer may not have processed the messages by the time the first `start_workflow()` call is made (e.g., within seconds of startup). The inline-stages fallback in `OrchestrationClient` handles this correctly — it is a feature, not a bug. The `_template_id_cache` will be populated on the next call after WO has stored the template.

### 4.3  `grc-service/apps/core/management/commands/register_workflow_templates.py`  *(update docstring only)*

Replace the existing docstring block that says:

```
Templates CANNOT be registered from GRC via Kafka or API — WO has no inbound
template-registration endpoint. GRC templates are owned by WO and seeded using
WO's own management command (guide §2 — template ownership pattern).
```

With:

```
Templates are registered from GRC → WO via the workflow-templates Kafka topic.
GRC publishes on startup (apps.py ready() → _register_workflow_templates_via_kafka()).
WO's WorkflowTemplateRegistrationConsumer stores them in its DB.

To verify:
    docker exec <grc-container> python manage.py register_workflow_templates --fetch
```

Also update the Step 1 / Step 2 instructions in the docstring to match the new Kafka flow.

### 4.4  Settings — `grc-service/config/settings.py`

Add:

```python
KAFKA_WORKFLOW_TEMPLATES_TOPIC = env('KAFKA_WORKFLOW_TEMPLATES_TOPIC', default='workflow-templates')
```

---

## 5. WO Side — What to Build

### 5.1  `wo/apps/core/consumers/workflow_template_registration_consumer.py`  *(new file)*

Mirror `template_registration_consumer.py` exactly, but for `WorkflowPlanModel` templates instead of `NotificationTemplateModel`.

Key logic inside `consume_workflow_template_registered(event)`:

```python
from apps.core.use_cases.workflow_template_use_cases import (
    CreateWorkflowTemplateCommand,
    CreateWorkflowTemplateUseCase,
)
from apps.infrastructure.persistence import DjangoWorkflowRepository

def _camel_to_snake_stages(stages: list) -> list:
    """
    Translate camelCase YAML field names to snake_case expected by
    CreateWorkflowTemplateCommand.
    
    Mapping:
      definitionKey → definition_key
      nextState     → next_state
    """
    normalised = []
    for stage in stages:
        actions = [
            {**a, 'next_state': a.pop('nextState', a.get('next_state', 'completed'))}
            for a in stage.get('actions', [])
        ]
        normalised.append({
            **stage,
            'definition_key': stage.pop('definitionKey', stage.get('definition_key', '')),
            'actions': actions,
        })
    return normalised

def consume_workflow_template_registered(self, event: dict) -> bool:
    template_data = event.get('template', {})
    code         = template_data.get('code')
    name         = template_data.get('name', '')
    workflow_type = template_data.get('workflow_type', '')
    definition   = template_data.get('definition', {})

    if not all([code, workflow_type, definition]):
        logger.error("workflow.template.registered event missing required fields")
        return False

    # Normalise stage field names (YAML uses camelCase; WO use-case expects snake_case)
    if 'stages' in definition:
        definition = {**definition, 'stages': _camel_to_snake_stages(definition['stages'])}

    try:
        repo     = DjangoWorkflowRepository()
        use_case = CreateWorkflowTemplateUseCase(repo)

        # Upsert: deactivate existing then create new version
        existing = repo.list_templates(workflow_type=workflow_type, limit=1)
        if existing:
            # For now: skip if already exists (idempotent).
            # Future: compare version field and update only if newer.
            logger.info("Workflow template '%s' already registered — skipping", workflow_type)
            return True

        command = CreateWorkflowTemplateCommand(
            name=name,
            workflow_type=workflow_type,
            definition=definition,
        )
        use_case.execute(command)
        logger.info("Registered workflow template: %s (type=%s)", code, workflow_type)
        return True

    except Exception as exc:
        logger.error("Failed to register workflow template %s: %s", code, exc)
        return False
```

**Topic and group:**

```python
self.topic    = getattr(settings, 'KAFKA_WORKFLOW_TEMPLATES_TOPIC', 'workflow-templates')
self.group_id = getattr(settings, 'KAFKA_WORKFLOW_TEMPLATE_CONSUMER_GROUP',
                         'work-orchestration-workflow-template-consumer')
```

**Event type guard** (in `process_message`):

```python
if event.get('event_type') != 'workflow.template.registered':
    return False  # Not our message type
```

### 5.2  `wo/apps/core/management/commands/run_kafka_consumer.py`  *(add new consumer)*

Import and wire up the new consumer alongside the existing two:

```python
from apps.core.consumers.workflow_template_registration_consumer import (
    WorkflowTemplateRegistrationConsumer,
)
```

Add `--workflow-template-consumer` argument and instantiate `WorkflowTemplateRegistrationConsumer()` when that flag (or the default "run all") is active.

### 5.3  Settings — `wo/config/settings.py`

Add:

```python
KAFKA_WORKFLOW_TEMPLATES_TOPIC         = env('KAFKA_WORKFLOW_TEMPLATES_TOPIC', default='workflow-templates')
KAFKA_WORKFLOW_TEMPLATE_CONSUMER_GROUP = env('KAFKA_WORKFLOW_TEMPLATE_CONSUMER_GROUP',
                                              default='work-orchestration-workflow-template-consumer')
```

---

## 6. Field-Name Normalisation Reference

`workflows.yaml` uses camelCase (matching WO's external API serializer). `CreateWorkflowTemplateCommand` (WO's internal use-case) uses snake_case. The consumer must translate:

| `workflows.yaml` / event | `CreateWorkflowTemplateCommand` / WO DB |
|---|---|
| `stages[].definitionKey` | `stages[].definition_key` |
| `stages[].actions[].nextState` | `stages[].actions[].next_state` |
| `stages[].sla.durationMinutes` | `stages[].sla.targetHours` ¹ or keep as-is if WO stores raw |

¹ Check `validate_template_definition()` in `workflow_template_use_cases.py` for what it actually validates. The method validates `form_schema` field types but does not transform SLA. Store SLA as-is inside the `definition` JSON blob.

---

## 7. Implementation Order

Work in this sequence to avoid breaking existing functionality:

1. **WO consumer** — implement `WorkflowTemplateRegistrationConsumer` and wire it into `run_kafka_consumer.py`. Deploy / restart WO. At this point WO listens but nothing publishes yet.

2. **Settings** — add `KAFKA_WORKFLOW_TEMPLATES_TOPIC` to both services' settings and `.env.example` files.

3. **GRC publisher** — implement `WorkflowTemplatePublisher`. Test via management command first (see §8) before hooking it into `apps.py`.

4. **GRC apps.py hook** — add `_register_workflow_templates_via_kafka()` call. Restart GRC. Templates should appear in WO DB within seconds.

5. **Verify** — run `docker exec <grc-container> python manage.py register_workflow_templates --fetch` and confirm all codes show `✓` with a UUID.

6. **Update docstrings** — update `grc-service/apps/core/workflows/registry.py` and the `register_workflow_templates` management command docstrings.

---

## 8. Testing and Verification

### Manual publish test (before wiring into apps.py)

```bash
docker exec grc-service python manage.py shell -c "
from apps.core.workflows.workflow_template_publisher import WorkflowTemplatePublisher
count = WorkflowTemplatePublisher().publish()
print(f'Published {count} templates')
"
```

### Verify WO received and stored them

```bash
docker exec work-orchestration-service python manage.py shell -c "
from apps.infrastructure.persistence import DjangoWorkflowRepository
repo = DjangoWorkflowRepository()
for code in ['grc_audit_program_approval', 'grc_working_paper_approval', 'grc_rbiap_approval']:
    result = repo.list_templates(workflow_type=code, limit=1)
    status = f'UUID={result[0].template_id}' if result else 'NOT FOUND'
    print(f'{code}: {status}')
"
```

### Verify OrchestrationClient resolves UUIDs

```bash
docker exec grc-service python manage.py register_workflow_templates --fetch
```

Expected output:

```
GRC Template Resolution (what _get_template_id_by_code() will return):
  ✓  grc.audit_program_approval
       workflow_type=grc_audit_program_approval
       uuid=<UUID>
  ✓  grc.working_paper_approval
       ...
```

---

## 9. What Does NOT Change

- `grc-service/apps/core/workflows/workflows.yaml` — source of truth, already complete
- `grc-service/apps/core/workflows/registry.py` — keeps loading YAML locally; the inline-stages fallback remains valid during the startup window and in dev environments without a running WO Kafka consumer
- `grc-service/apps/infrastructure/external/orchestration_client.py` — `TEMPLATE_CODE_TO_WO_TYPE` and `_get_template_id_by_code()` are correct as-is
- `wo/apps/core/management/commands/seed_workflow_templates.py` — remains WO-native templates only (`approval`, `commission`, `management`, `disposal`); no GRC templates here

---

## 10. Files Summary

### New files to create

| Service | File |
|---|---|
| GRC | `apps/core/workflows/workflow_template_publisher.py` |
| WO | `apps/core/consumers/workflow_template_registration_consumer.py` |

### Files to modify

| Service | File | Change |
|---|---|---|
| GRC | `apps/core/apps.py` | Add `_register_workflow_templates_via_kafka()` method + call in `ready()` |
| GRC | `config/settings.py` | Add `KAFKA_WORKFLOW_TEMPLATES_TOPIC` |
| GRC | `env.example` | Add `KAFKA_WORKFLOW_TEMPLATES_TOPIC=workflow-templates` |
| GRC | `apps/core/workflows/registry.py` | Update docstring (remove "Kafka doesn't work" note) |
| GRC | `apps/core/management/commands/register_workflow_templates.py` | Update docstring to reflect new Kafka flow |
| WO | `apps/core/management/commands/run_kafka_consumer.py` | Import + wire `WorkflowTemplateRegistrationConsumer` |
| WO | `config/settings.py` | Add `KAFKA_WORKFLOW_TEMPLATES_TOPIC` + consumer group setting |
| WO | `env.example` | Add new settings |
