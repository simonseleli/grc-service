# GRC Service Implementation Analysis

**Date**: 2026-03-12  
**Scope**: `my_custom_implementation/` — `grc-service/` (new service), `work-orchestration-service/` (modifications), `frontend/` (additions)  
**Reference**: `FIMS_summary/services_integration/WORK_ORCHESTRATION_FULL_INTEGRATION_GUIDE.md` + `corporate-service/` canonical reference

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What Is Correct — Do Not Change](#what-is-correct--do-not-change)
3. [Critical Bugs — Breaks Core Functionality](#critical-bugs--breaks-core-functionality)
4. [Significant Bugs — Wrong Behavior](#significant-bugs--wrong-behavior)
5. [Minor Issues — Code Quality](#minor-issues--code-quality)
6. [Per-File Findings](#per-file-findings)
7. [Fix Priority Order](#fix-priority-order)
8. [Reference: Correct Patterns](#reference-correct-patterns)

---

## Executive Summary

The GRC service is well-structured and follows the FIMS architecture correctly. A significant amount of work landed in the right place: model fields, service layer, metadata design, startup registration, and — importantly — the frontend.

**The frontend `EmbeddedWorkflowConsole` is correct and does NOT need to change.** It wraps the shared React `WorkflowConsole` component (not an iframe, not custom dialogs). This is the right approach per the guide.

**Template registration** is the only feature that is 100% broken — templates are loaded from YAML but never published to WO's Kafka topic. Fix this and `start_workflow()` starts resolving template UUIDs correctly.

**Final approval/rejection works end-to-end.** The `grc.workflow.completed` event IS handled correctly. Where it breaks is intermediate stage tracking (`workflow_stage` field never updates after submission).

---

## What Is Correct — Do Not Change

### `WorkflowMixin` base model (`apps/core/models/base.py`)
All 5 required fields with correct types: `workflow_plan_id`, `workflow_stage`, `workflow_stage_id`, `workflow_started_at`, `workflow_completed_at`. ✅

### `get_workflow_metadata()` on entity models
Returns the required keys: `entity_type`, `entity_id`, `entity_detail_path`. These are spread into `combined_metadata` via `**(metadata or {})` in `start_workflow()`. ✅

### `start_workflow()` combined metadata
`combined_metadata` includes `entity_type`, `entity_id` (from metadata), `context`, `subject_ref`, and `template_code`. WO stores this as `plan.metadata`. When `WorkflowCompletionHandler` publishes `grc.workflow.completed`, it embeds `plan.metadata` in the event — so the consumer can read `subject_ref` and `template_code` directly from the event. This design is deliberate and works. ✅

### `audit_universe_service.py` — `submit_for_approval()` pattern
Correct sequence: `get_workflow_context()` → `get_workflow_metadata()` → `client.start_workflow()` → saves all 5 WorkflowMixin fields → sets `status='pending'`. ✅

### Final workflow completion handling (consumer)
The `grc.workflow.completed` endpoint works correctly:
- All GRC plans have `workflow_type = "grc"` (derived from `template_code.split('.')[0]`)
- `WorkflowCompletionHandler.handle_workflow_completion()` publishes `"grc.workflow.completed"`
- Consumer checks `event_type.endswith('.workflow.completed')` → **True** ✅
- Consumer checks `workflow_type != 'grc'` → filter passes ✅
- Consumer reads `subject_ref` + `template_code` from `event_data['metadata']` ← `plan.metadata` is embedded in the event ✅
- Dispatch by `template_code` → routes to correct entity handler ✅
- `_determine_final_decision()` returns `'approved'`, `'rejected'`, or `'cancelled'` — handlers check these correctly ✅

Final approval and rejection work end-to-end.

### Permission and notification template publishing at startup (`apps.py`)
`_register_permissions_on_startup()` and `_register_notification_templates()` follow the FIMS pattern. ✅

### Frontend `EmbeddedWorkflowConsole` (`components/work-orchestration/EmbeddedWorkflowConsole.tsx`)
**FIXED**: Was incorrectly rendering the React `WorkflowConsole` component directly instead of using an iframe. All FIMS services must use the same pattern: **iframe → WO Django-rendered HTML** at `/api/v1/workflow/plans/{planId}/console/`. Component has been updated to match the corporate-service approach (`buildConsoleUrl()` + `<iframe sandbox=...>`). The 4 GRC detail pages required no changes — props are unchanged. ✅

### GRC detail pages
Correctly call `useGRCWorkflowStatus()` to get `workflowPlanId`, then pass it to `EmbeddedWorkflowConsole`. ✅

### `useGRCWorkflows.ts`
Follows the `useCorporateWorkflows` pattern with a GRC-specific entity type union and status function map. ✅

### `workflow_entity_paths.py` — All entity types mapped correctly. ✅

### `apps.py` build-command guard — Skips Kafka during `migrate`, `collectstatic`, etc. ✅

---

## Critical Bugs — Breaks Core Functionality

### BUG-C1 — Workflow templates never published to WO via Kafka

**Files**: `apps/core/apps.py` + `apps/core/workflows/registry.py`  
**Result**: WO has no GRC templates. `start_workflow()` cannot resolve a `template_id`. Falls back to inline stages — which are broken (BUG-S2) and will fail WO validation.

**What the code does**:
```python
# apps.py _load_workflow_templates()
registry = WorkflowTemplateRegistry()
templates = registry.list_templates()
logger.info("loaded %d templates: %s", len(templates), ...)
# ← STOPS HERE. Never calls publish_templates()
```

`WorkflowTemplateRegistry` in `registry.py` only loads the YAML. It has no `publish_templates()` method. The **wrong comment** in `registry.py` is the root cause:
```python
# NOTE — template registration via Kafka does NOT work:
# Work Orchestration Service has no consumer for the "workflow-templates" topic.
```
This comment is **factually wrong**. WO has `WorkflowTemplateRegistrationConsumer` on `workflow-templates`. Because of this comment, `publish_templates()` was never implemented.

**Fix — three steps:**

**Step 1**: Delete the wrong comment from `registry.py` and add `publish_templates()`:
```python
# apps/core/workflows/registry.py
import json
from confluent_kafka import Producer

class WorkflowTemplateRegistry:
    SERVICE_NAME = "grc-service"
    
    def __init__(self):
        self._templates = {}
        self._topic = getattr(settings, 'KAFKA_WORKFLOW_TEMPLATES_TOPIC', 'workflow-templates')
    
    def load_templates(self) -> int:
        with open(WORKFLOWS_YAML_PATH, 'r') as f:
            data = yaml.safe_load(f)
        for tpl in data.get('templates', []):
            code = tpl.get('code')
            if code:
                self._templates[code] = tpl
        return len(self._templates)
    
    def list_templates(self):
        return list(self._templates.values())
    
    def publish_templates(self) -> bool:
        producer = Producer({'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
                             'acks': 'all', 'retries': 3})
        for code, template in self._templates.items():
            message = {
                'event_type': 'workflow.template.registered',
                'source_service': self.SERVICE_NAME,
                'template': {
                    'code':          template.get('code'),
                    'name':          template.get('name'),
                    'workflow_type': template.get('workflow_type'),
                    'version':       template.get('version', 1),
                    'is_active':     template.get('is_active', True),
                    'definition':    template.get('definition', {}),
                }
            }
            producer.produce(topic=self._topic, key=code.encode(),
                             value=json.dumps(message).encode())
        producer.flush(timeout=10)
        return True
```

**Step 2**: Update `_load_workflow_templates()` in `apps.py` to call it:
```python
def _load_workflow_templates(self) -> None:
    try:
        from apps.core.workflows.registry import WorkflowTemplateRegistry
        registry = WorkflowTemplateRegistry()
        loaded = registry.load_templates()
        if loaded == 0:
            logger.warning("GRC: no workflow templates loaded")
            return
        success = registry.publish_templates()
        if success:
            logger.info("GRC: published %d workflow templates to Kafka", loaded)
        else:
            logger.warning("GRC: some templates failed to publish (check Kafka connectivity)")
    except Exception as exc:
        logger.error("GRC: failed to register workflow templates: %s", exc)
```

**Step 3**: Add to `settings.py`:
```python
KAFKA_WORKFLOW_TEMPLATES_TOPIC = os.getenv("KAFKA_WORKFLOW_TEMPLATES_TOPIC", "workflow-templates")
KAFKA_WORKFLOW_EVENTS_TOPIC = os.getenv("KAFKA_WORKFLOW_EVENTS_TOPIC", "workflow-events")
KAFKA_WORKFLOW_EVENTS_CONSUMER_GROUP = os.getenv(
    "KAFKA_WORKFLOW_EVENTS_CONSUMER_GROUP", "grc-service-consumer-group"
)
```

---

### BUG-C2 — `workflow_type` in YAML conflicts with `TEMPLATE_CODE_TO_WO_TYPE` lookup

**Files**: `apps/core/workflows/workflows.yaml` + `apps/infrastructure/external/orchestration_client.py`  
**Result**: Template UUID lookup fails for all 8 GRC templates. Nothing is found, inline stages used, workflow fails.

**The conflict**:
```yaml
# workflows.yaml — ALL templates use "grc"
- code: "grc.audit_universe_approval"
  workflow_type: "grc"                     ← WO stores as workflow_type="grc"
- code: "grc.working_paper_approval"
  workflow_type: "grc"                     ← WO stores as workflow_type="grc"
```

```python
# orchestration_client.py — queries for UNIQUE types
TEMPLATE_CODE_TO_WO_TYPE = {
    "grc.audit_universe_approval":  "grc_audit_universe_approval",  ← queries WO for THIS
    "grc.working_paper_approval":   "grc_working_paper_approval",   ← queries WO for THIS
}
```

WO stores both templates with `workflow_type="grc"`, but the lookup queries for `"grc_audit_universe_approval"` which doesn't exist in WO.

**Fix — pick one**:

**Option A (Recommended — 5 min fix)**: Change `_get_template_id_by_code()` to query by `code` (matching corporate-service exactly). Delete `TEMPLATE_CODE_TO_WO_TYPE`.

```python
def _get_template_id_by_code(self, template_code: str, auth_token=None) -> Optional[str]:
    if template_code in self._template_id_cache:
        return self._template_id_cache[template_code]
    try:
        resp = requests.get(
            self._templates_url(),
            params={'code': template_code, 'is_active': 'true'},
            headers=self._headers(auth_token),
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            templates = data.get('data', data) if isinstance(data, dict) else data
            for tpl in (templates if isinstance(templates, list) else []):
                if tpl.get('code') == template_code:
                    uid = str(tpl['id'])
                    self._template_id_cache[template_code] = uid
                    return uid
    except Exception as exc:
        logger.debug("Template lookup failed for %s: %s", template_code, exc)
    return None
```

**Option B**: Keep the current lookup approach but give each template a unique `workflow_type` in YAML (matching `TEMPLATE_CODE_TO_WO_TYPE` exactly):
```yaml
- code: "grc.audit_universe_approval"
  workflow_type: "grc_audit_universe_approval"   ← must match TEMPLATE_CODE_TO_WO_TYPE value
```

---

### BUG-C3 — WO `handle_stage_completion()` gated to wrong template code

**File**: `work-orchestration-service/apps/core/services/completion_handler.py` (user modification)  
**Result**: Engagement lifecycle stage transitions (planning→fieldwork→reporting) never fire via Kafka. `_handle_audit_engagement_stage()` in the consumer is never called.

```python
# completion_handler.py (user-added method)
def handle_stage_completion(self, plan, stage, action_name: str) -> bool:
    ...
    template_code = plan_metadata.get('template_code', '')
    if template_code != 'grc.engagement_notification':   # ← WRONG
        return False
```

The engagement lifecycle template code is `'grc.engagement_lifecycle'`. The condition `'grc.engagement_lifecycle' != 'grc.engagement_notification'` is always True, so the method always returns early.

**Fix**:
```python
# Option A — fix the exact code:
if template_code != 'grc.engagement_lifecycle':
    return False

# Option B — fire for ALL GRC templates:
if not template_code.startswith('grc.'):
    return False
```

---

## Significant Bugs — Wrong Behavior

### BUG-S1 — Intermediate stage progress never tracked (`workflow_stage` stuck at Stage 1)

**File**: `apps/infrastructure/messaging/kafka_consumer.py`  
**Result**: `workflow_stage` and `workflow_stage_id` on entities are set at plan creation and never updated as the plan advances to Stage 2, Stage 3, etc.

WO's `KafkaEventDispatcher` publishes `WorkflowStageUpdated` events after every stage action. These are NEVER handled. Only `{type}.stage.completed` and `{type}.workflow.completed` are handled.

The entity appears permanently at "Stage 1" to any code that reads `entity.workflow_stage`.

**Fix**: Add a handler for `WorkflowStageUpdated` at the top of `_handle_workflow_event()`:

```python
def _handle_workflow_event(self, event_data: dict, topic: str):
    event_type = event_data.get('event_type', '')

    # ← ADD THIS: Handle canonical KafkaEventDispatcher stage events
    if event_type == 'WorkflowStageUpdated':
        self._handle_stage_updated(event_data)
        return

    # Existing handlers unchanged below...
    ...

def _handle_stage_updated(self, event_data: dict):
    """
    Handle WorkflowStageUpdated from KafkaEventDispatcher.
    Updates workflow_stage on the entity so the field stays current.
    
    NOTE: entity_type/entity_id are NOT in this event.
    Must fetch via REST call to WO (same as corporate-service pattern).
    """
    payload = event_data.get('payload', {})
    plan_id = payload.get('planId')
    new_status = payload.get('newStatus', '')
    action = payload.get('action', '')

    # Only act on terminal transitions
    if new_status not in ('completed', 'rejected') and action not in ('return', 'resubmit', 'withdraw'):
        return

    # Fetch entity_type and entity_id from WO (they are not in this event payload)
    plan_info = self._get_plan_info(plan_id)
    if not plan_info:
        return

    entity_type = plan_info.get('entity_type')
    entity_id = plan_info.get('entity_id')
    stage_name = payload.get('stageName', '')
    stage_id = payload.get('stageId')

    if not entity_type or not entity_id:
        return

    self._update_workflow_stage_on_entity(entity_type, entity_id, stage_name, stage_id)

def _get_plan_info(self, plan_id: str) -> dict:
    """Fetch plan metadata via REST to get entity_type and entity_id."""
    from apps.infrastructure.external.orchestration_client import OrchestrationClient
    try:
        client = OrchestrationClient()
        plan = client.get_plan_status(plan_id)
        return plan.get('metadata', {}) if plan else {}
    except Exception as exc:
        logger.error("Failed to fetch plan %s: %s", plan_id, exc)
        return {}
```

---

### BUG-S2 — Inline stage fallback uses wrong field names (camelCase mismatch)

**File**: `apps/core/models/audit_entities.py` — `get_workflow_stages()`  
**Result**: If BUG-C1/C2 aren't fixed and the system falls back to inline stages, WO's `StageInputSerializer` will reject them

```python
# WRONG (current code):
{"order": 0, "next_state": "...", "definition_key": "..."}

# CORRECT (must match WO serializer and YAML convention):
{"order": 1, "nextState": "...", "definitionKey": "..."}
```

The YAML itself correctly uses camelCase. The inline Python fallback needs to match.

---

### BUG-S3 — `status_on_complete` missing from all YAML stage definitions

**File**: `apps/core/workflows/workflows.yaml`  
**Result**: All status transitions are hardcoded in consumer Python. Cannot set intermediate statuses (e.g., "currently under management review") without a new Python deployment.

Add `metadata.status_on_complete` to each stage:
```yaml
stages:
  - order: 1
    definitionKey: cia_review
    metadata:
      status_on_complete: "cia_reviewed"      # ← consumed by WorkflowStageUpdated handler
  - order: 2
    definitionKey: management_review
    metadata:
      status_on_complete: "management_reviewed"
```

---

### BUG-S4 — Kafka consumer uses `enable_auto_commit=True` (at-most-once delivery)

**File**: `apps/infrastructure/messaging/kafka_consumer.py`  
**Result**: If entity status update throws an exception, the Kafka offset is already committed. That event is permanently lost; entity status is never updated.

```python
# WRONG — auto-commit before confirmed processing:
KafkaConsumer(..., enable_auto_commit=True)

# CORRECT — manual commit only after success:
KafkaConsumer(..., enable_auto_commit=False)
# ... in consume loop:
self._process_message(message)
self.consumer.commit()   # ← only if _process_message() didn't raise
```

---

## Minor Issues — Code Quality

### BUG-M1 — Wrong comment in `registry.py` says Kafka doesn't work

The comment blocks the correct implementation. Delete it. WO does have `WorkflowTemplateRegistrationConsumer`.

### BUG-M2 — Module-level consumer singleton creates Kafka connections at import time

```python
# Last line of kafka_consumer.py — runs at every import:
grc_kafka_consumer = GRCKafkaConsumer()
```

Every gunicorn HTTP worker imports this module. Each creates a Kafka connection. Move instantiation inside the management command's `handle()`.

### BUG-M3 — IAM and document event handlers are TODO stubs

`_handle_iam_event()` and `_handle_document_event()` only log. Non-functional. Fine to leave as skeletons for now, but note for Phase 2.

### BUG-M4 — Duplicate `EmbeddedWorkflowConsole` at `components/workflow/` is unused by GRC

The `components/workflow/EmbeddedWorkflowConsole.tsx` is the old corporate-service iframe version. GRC detail pages import from `components/work-orchestration/EmbeddedWorkflowConsole.tsx` (the React wrapper). The `components/workflow/` version is not used by GRC. Leave it if corporate pages need it; otherwise it creates confusion.

---

## Per-File Findings

### `grc-service/config/settings.py`

| Setting | Status |
|---------|--------|
| `KAFKA_BOOTSTRAP_SERVERS` | ✅ |
| `WORK_ORCHESTRATION_SERVICE_URL` | ✅ |
| `SERVICE_TO_SERVICE_TOKEN` | ✅ |
| `KAFKA_WORKFLOW_TEMPLATES_TOPIC` | ❌ Missing — add for BUG-C1 |
| `KAFKA_WORKFLOW_EVENTS_TOPIC` | ❌ Missing |
| `KAFKA_WORKFLOW_EVENTS_CONSUMER_GROUP` | ❌ Missing |

### `grc-service/apps/core/apps.py`

| Item | Status |
|------|--------|
| Build-command guard | ✅ |
| Permission registration | ✅ |
| Notification template registration | ✅ |
| Workflow template registration (publish to Kafka) | ❌ BUG-C1 — loads only, never publishes |

### `grc-service/apps/core/workflows/registry.py`

| Item | Status |
|------|--------|
| Loads YAML into dict | ✅ |
| `publish_templates()` method | ❌ BUG-C1 — does not exist |
| Comment about Kafka not working | ❌ BUG-M1 — factually wrong, delete it |

### `grc-service/apps/core/workflows/workflows.yaml`

| Item | Status |
|------|--------|
| Stage field names (camelCase: `definitionKey`, `nextState`) | ✅ |
| `workflow_type: "grc"` for all templates | ❌ BUG-C2 — conflicts with `TEMPLATE_CODE_TO_WO_TYPE` lookup |
| `status_on_complete` in stage metadata | ❌ BUG-S3 — missing from all stages |

### `grc-service/apps/core/models/audit_entities.py`

| Item | Status |
|------|--------|
| `get_workflow_metadata()` — `entity_type`, `entity_id`, `entity_detail_path` | ✅ |
| `get_workflow_context()` — domain variables | ✅ |
| `get_workflow_stages()` — `"order": 0` | ❌ BUG-S2 — should be `1` |
| `get_workflow_stages()` — `"next_state"` | ❌ BUG-S2 — should be `"nextState"` |
| `get_workflow_stages()` — `"definition_key"` | ❌ BUG-S2 — should be `"definitionKey"` |

### `grc-service/apps/infrastructure/external/orchestration_client.py`

| Item | Status |
|------|--------|
| `start_workflow()` HTTP payload structure | ✅ |
| `combined_metadata` includes `entity_type`, `entity_id` | ✅ |
| Auth headers | ✅ |
| `get_plan_status()` method | ✅ |
| `TEMPLATE_CODE_TO_WO_TYPE` queries by unique type | ❌ BUG-C2 — conflicts with YAML `workflow_type: "grc"` |

### `grc-service/apps/infrastructure/messaging/kafka_consumer.py`

| Item | Status |
|------|--------|
| Subscribes to `workflow-events` | ✅ |
| Consumer group `grc-service-consumer-group` | ✅ |
| `grc.workflow.completed` → final approval/rejection | ✅ Works correctly |
| `subject_ref` + `template_code` routing | ✅ Works (plan.metadata is embedded in event) |
| Entity handler dispatch map | ✅ |
| `WorkflowStageUpdated` handling (stage progress) | ❌ BUG-S1 — never handled |
| `enable_auto_commit=True` | ❌ BUG-S4 |
| Module-level singleton | ❌ BUG-M2 |
| IAM + document handlers | ❌ BUG-M3 — TODO stubs |

### `grc-service/apps/core/services/audit_universe_service.py`

| Item | Status |
|------|--------|
| `submit_for_approval()` sequence | ✅ |
| Saves all 5 WorkflowMixin fields | ✅ |
| Notification publishing | ✅ |

### `work-orchestration-service/` modifications

| Item | Status |
|------|--------|
| `advance_stage.py` — calls `handle_stage_completion()` | ✅ Correct ordering |
| `completion_handler.py` — `handle_stage_completion()` method | ❌ BUG-C3 — wrong template_code gate |
| `seed_workflow_templates.py` — GRC templates | ❌ Not seeded (needed as backup to Kafka) |

### Frontend additions

| Item | Status |
|------|--------|
| `EmbeddedWorkflowConsole.tsx` in `work-orchestration/` — iframe → WO Django HTML | ✅ Fixed (was incorrectly using React component) |
| GRC detail pages pass `workflowPlanId` | ✅ |
| `useGRCWorkflows.ts` hook | ✅ |
| Duplicate `EmbeddedWorkflowConsole` in `components/workflow/` unused by GRC | ⚠️ BUG-M4 — unused by GRC, kept for corporate pages |

---

## Fix Priority Order

### Priority 1 — Template registration (needed for ANY workflow to start)
1. Add `publish_templates()` to `registry.py`
2. Call it from `_load_workflow_templates()` in `apps.py`
3. Add three missing settings to `settings.py`
4. Fix BUG-C2: either change lookup to use `code` (easiest), or update YAML `workflow_type` values

### Priority 2 — Engagement stage transitions (BUG-C3)
Fix the condition in WO's `completion_handler.py`:
```python
# Change 'grc.engagement_notification' to:
if not template_code.startswith('grc.'):
```

### Priority 3 — Intermediate stage tracking (BUG-S1)
Add `WorkflowStageUpdated` handler that updates `workflow_stage` / `workflow_stage_id`.

### Priority 4 — At-least-once delivery (BUG-S4)
Set `enable_auto_commit=False` and add manual `consumer.commit()` after successful processing.

### Priority 5 — Inline stage field names (BUG-S2)
Fix `get_workflow_stages()` to use camelCase and `order: 1`.

### Priority 6 — `status_on_complete` in YAML (BUG-S3)
Add per-stage declarative status to each stage in `workflows.yaml`.

### Priority 7 — Module-level singleton (BUG-M2)
Remove `grc_kafka_consumer = GRCKafkaConsumer()` from module bottom.

---

## Reference: Correct Patterns

### `apps.py` — complete `_load_workflow_templates()` (copying corporate-service pattern)

```python
def _load_workflow_templates(self) -> None:
    try:
        from apps.core.workflows.registry import WorkflowTemplateRegistry
        logger.info("Registering GRC workflow templates with Work Orchestration...")
        registry = WorkflowTemplateRegistry()
        loaded = registry.load_templates()
        if loaded == 0:
            logger.warning("No GRC workflow templates loaded from YAML")
            return
        success = registry.publish_templates()
        if success:
            logger.info("GRC: published %d workflow templates", loaded)
        else:
            logger.warning("GRC: some templates failed to publish")
    except Exception as exc:
        logger.error("GRC: could not register workflow templates: %s", exc, exc_info=True)
```

### Template lookup by `code` (Option A fix for BUG-C2)

```python
# Replaces current _get_template_id_by_code() in orchestration_client.py
def _get_template_id_by_code(self, template_code: str, auth_token=None) -> Optional[str]:
    if template_code in self._template_id_cache:
        return self._template_id_cache[template_code]
    try:
        resp = requests.get(
            self._templates_url(),
            params={'code': template_code, 'is_active': 'true'},
            headers=self._headers(auth_token),
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            templates = data.get('data', data) if isinstance(data, dict) else data
            for tpl in (templates if isinstance(templates, list) else []):
                if tpl.get('code') == template_code:
                    uid = str(tpl['id'])
                    self._template_id_cache[template_code] = uid
                    logger.info("Resolved template %s → %s", template_code, uid)
                    return uid
    except Exception as exc:
        logger.debug("Template lookup failed for %s: %s", template_code, exc)
    return None
```

### Correct inline stage definitions (BUG-S2 fix)

```python
def get_workflow_stages(self) -> list:
    return [
        {
            "order": 1,                           # 1-indexed, not 0
            "name": "cia_review",
            "nextState": "completed",             # camelCase
            "definitionKey": "approvals",         # camelCase
            "metadata": {"status_on_complete": "cia_reviewed"}
        },
    ]
```

### Manual Kafka commit (BUG-S4 fix)

```python
# In consume_messages():
self.consumer = KafkaConsumer(
    *self.topics,
    ...,
    enable_auto_commit=False,   # ← change this
)

for message in self.consumer:
    try:
        self._process_message(message)
        self.consumer.commit()      # ← only when processing succeeded
    except Exception as e:
        logger.error(f"Processing failed, keeping offset: {e}", exc_info=True)
        # Don't commit — event will be redelivered
```
