# Work Orchestration Service — Full Integration Guide

> **Document Type:** Authoritative Developer Reference  
> **Audience:** Engineers adding workflow-based approval to any FIMS service  
> **Source:** Evidence-based analysis of `work-orchestration-service` + `corporate-service` codebase, line-by-line verified  
> **Last Updated:** 2026-03-13  
> **Scope:** Covers the complete lifecycle — design-time setup, runtime flow, UI integration, and event feedback

---

## Table of Contents

1. [Core Concept — What WO Actually Is](#1-core-concept--what-wo-actually-is)
2. [The Big Question: Who Builds the Approval UI?](#2-the-big-question-who-builds-the-approval-ui)
3. [The Five Integration Phases](#3-the-five-integration-phases)
4. [Phase 1 — Define the Workflow Template (YAML)](#4-phase-1--define-the-workflow-template-yaml)
5. [Phase 2 — Register the Template at Startup (Kafka)](#5-phase-2--register-the-template-at-startup-kafka)
6. [Phase 3 — Start a Workflow Plan (REST)](#6-phase-3--start-a-workflow-plan-rest)
7. [Phase 4 — UI Integration (Frontend WorkflowConsole)](#7-phase-4--ui-integration-frontend-workflowconsole)
8. [Phase 5 — Listen for Workflow Outcome Events (Kafka)](#8-phase-5--listen-for-workflow-outcome-events-kafka)
9. [Data Ownership Summary](#9-data-ownership-summary)
10. [Implementation Checklist for a New Service](#10-implementation-checklist-for-a-new-service)
11. [Complete Data Flow Diagram](#11-complete-data-flow-diagram)
12. [Anti-Patterns — What Never To Do][def]

---

## 1. Core Concept — What WO Actually Is

Work Orchestration Service (WO, port **8004**) is the **sole authority for multi-step approval flows** across all of FIMS. It is a domain-agnostic engine — it does not know what a leave application or procurement request is. It only understands:

| WO Concept     | Meaning                                                                  |
|----------------|--------------------------------------------------------------------------|
| **Template**   | A reusable blueprint (stages, actions, SLA, assignees) for a workflow type |
| **Plan**       | A live instance of a template, tied to one business entity               |
| **Stage**      | A single step in the plan (e.g., "Manager Approval", "HR Verification")  |
| **Action**     | A button a user can click on a stage (approve, reject, return, etc.)     |
| **Context**    | Variables passed at plan creation to resolve dynamic assignees           |
| **Metadata**   | Arbitrary JSON stored on the plan — used for display and routing         |

When a service wants approval on an entity (leave, document, contract, etc.), it delegates **entirely** to WO. The service does not run any stage logic, does not check who is allowed to approve, and does not render the approval steps UI.

---

## 2. The Big Question: Who Builds the Approval UI?

**Short answer: No service builds its own approval UI for workflow steps.**

Here is the full picture:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         STAFF PORTAL (React)                              │
│                                                                            │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────┐  │
│  │  Service Entity Detail Page      │    │   WorkflowConsole Component  │  │
│  │  (built by each service's FE)   │───▶│   (SHARED — built once in   │  │
│  │                                  │    │    WO's frontend package)   │  │
│  │  e.g. LeaveApplicationDetailPage│    │                              │  │
│  │  e.g. DocumentDetailPage        │    │  • Shows all stages          │  │
│  │  e.g. ProcurementDetailPage     │    │  • Shows action buttons      │  │
│  │                                  │    │  • Shows activity history   │  │
│  │  Renders entity-specific info:   │    │  • Shows assignee names     │  │
│  │  - Leave dates, type, balance    │    │  • Handles approve/reject   │  │
│  │  - Document title, type, content │    │  • Decides who can act      │  │
│  │                                  │    │  (all powered by WO API)    │  │
│  └─────────────────────────────────┘    └─────────────────────────────┘  │
│                    │  passes `planId`               │                      │
└────────────────────┼───────────────────────────────┼──────────────────────┘
                     │                               │
              (service API)                   (WO API directly)
                     │                               │
         ┌───────────▼───────┐           ┌───────────▼────────────┐
         │  Service Backend   │           │  Work Orchestration     │
         │  (corporate, docs, │           │  Service :8004          │
         │   clients, GRC...) │           │                         │
         │                    │           │  GET /plans/{planId}/   │
         │  owns entity data  │           │  POST /plans/{planId}/  │
         │  tracks plan_id    │           │    stages/{stageId}/    │
         └────────────────────┘           │    actions/             │
                                          └─────────────────────────┘
```

### What each party is responsible for

| Responsibility | Who Builds It |
|---|---|
| Entity detail page (leave dates, amounts, etc.) | **Each service's frontend team** |
| Workflow stages visualization (which stage, who approved) | **Shared `WorkflowConsole` React component** |
| Action buttons (Approve / Reject / Return) | **`WorkflowConsole` — calls WO API directly** |
| Assignee validation (who can act on current stage) | **WO backend** (embedded in plan response) |
| Initiator exclusion (can't approve own request) | **WO backend** (embedded in plan response) |
| Sequential stage enforcement (Stage 2 can't run before Stage 1) | **WO backend** |
| Activity log (who approved when and why) | **WO backend + `WorkflowConsole`** |

---

## 3. The Five Integration Phases

Every service that integrates with WO goes through exactly five phases:

```
Phase 1: DEFINE          Phase 2: REGISTER       Phase 3: START
 Write workflows.yaml → Publish to Kafka → Call WO REST to create plan
  (design-time)          (service startup)      (user submits entity)
       │                       │                       │
       └───────────────────────▼───────────────────────┘
                               │
Phase 4: UI              Phase 5: LISTEN
 Frontend renders console ← WO stores plan data
  `WorkflowConsole`          ← User actions handled by WO directly
  reads WO API, user acts    ← WO publishes outcome event to Kafka
  on stages via WO API       → Service consumer updates entity status
```

---

## 4. Phase 1 — Define the Workflow Template (YAML)

Each service defines its workflows in a YAML file. Corporate service: `apps/core/workflows/workflows.yaml`.

### Template structure

```yaml
templates:
  - code: "your_service.entity_workflow"    # Globally unique code. Format: service.entity_name
    name: "Human Readable Workflow Name"
    workflow_type: "your_service_type"       # Used in Kafka event routing (e.g., 'corporate_hr')
    version: 1                               # Increment when changing the template
    definition:
      description: "What this workflow does"
      sla:
        targetMinutes: 4320                  # Total workflow SLA in minutes
        breachStrategy: "escalate"
      metadata:
        module: "hr"                         # Helps WO and frontend categorize workflows
        category: "leave"
      stages:
        - definitionKey: "stage_unique_key"  # Unique within this template
          name: "Stage Display Name"
          order: 1                           # Sequential. Stage 1 starts, Stage 2 waits.
          assignees:
            - "{{context_variable_id}}"      # Resolved from context at plan creation
            - "role:hr_officer"              # Any user with this role code
            - "{{manager_id}}"              # Can combine both types
          metadata:
            status_on_complete: "hod_approved"  # Entity status when this stage completes
          actions:
            - name: "approve"
              label: "Approve"
              nextState: "completed"         # "completed" advances workflow to next stage
            - name: "reject"
              label: "Reject"
              nextState: "rejected"          # "rejected" terminates workflow
            - name: "return"
              label: "Return for Amendment"
              nextState: "returned"          # Entity goes back to applicant for revision
          sla:
            durationMinutes: 1440            # Per-stage SLA
            breachStrategy: "notify"

        - definitionKey: "stage_2_key"
          name: "Second Approver"
          order: 2
          assignees: ["role:director"]
          metadata:
            status_on_complete: "approved"
          actions:
            - name: "approve"
              label: "Approve"
              nextState: "completed"
            - name: "reject"
              label: "Reject"
              nextState: "rejected"
          sla:
            durationMinutes: 2880
```

### Assignee types

| Type | Example | Behavior |
|---|---|---|
| Context variable | `{{line_manager_id}}` | UUID resolved from the `context` dict passed when starting the plan |
| Role reference | `role:hr_officer` | Any user whose JWT `roles` contains this role code |
| Multiple / either-or | `["{{manager_id}}", "role:director"]` | User is the specific person OR has the role |

### Action `nextState` values

| Value | Effect |
|---|---|
| `completed` | Stage is done; WO auto-advances to the next `pending` stage |
| `rejected` | Stage and plan are rejected; workflow terminates |
| `returned` | Entity sent back for revision; triggers revision flow in service |
| `pending` | Stage stays at current state (save draft patterns) |

### `status_on_complete` in stage metadata

This is a key pattern. Each stage can declare what entity status the originating service should apply when that stage completes. WO embeds this in `stageMetadata.status_on_complete` inside the `WorkflowStageUpdated` Kafka event payload. The consumer reads it and maps to the DB status — keeping the common status transitions declarative in `workflows.yaml` instead of hardcoded in Python.

However, `status_on_complete` is not the only mechanism. Handlers also perform **stage-specific imperative actions** by checking `stage_key` — for example, recording timestamps (`hod_approved_at`) or approver IDs (`hod_approved_by_id`) that are specific to a stage. Both mechanisms coexist in the same handler:

```python
# in _handle_your_entity()
if status_on_complete:
    entity.status = status_on_complete  # declarative, from YAML

if stage_key == 'hod_approval':         # imperative, stage-specific bookkeeping
    entity.hod_approved_by_id = actor_id
    entity.hod_approved_at = timezone.now()
```

---

## 5. Phase 2 — Register the Template at Startup (Kafka)

Services must publish their templates to WO via Kafka when they start up. WO stores them as `WorkflowTemplateModel` records. This is a one-time registration that WO persists — no need to publish on every request.

### What you build in your service

**1. `WorkflowTemplateRegistry` class** — loads `workflows.yaml` and publishes to Kafka

```python
# apps/core/workflows/registry.py (copy pattern from corporate-service)

class WorkflowTemplateRegistry:
    SERVICE_NAME = "your-service-name"
    
    def load_templates(self):
        """Load templates from YAML file."""
        # loads templates from workflows.yaml
    
    def publish_templates(self):
        """Publish all loaded templates to Kafka."""
        for code, template in self._templates.items():
            event = {
                'event_type': 'workflow.template.registered',
                'source_service': self.SERVICE_NAME,
                'template': template,  # full template dict from YAML
            }
            self._kafka_producer.send(topic='workflow-templates', message=event, key=code)
```

**2. `apps.py` — call registry at startup**

```python
# apps/core/apps.py

class CoreConfig(AppConfig):
    name = 'apps.core'
    
    def ready(self):
        from apps.core.workflows.registry import WorkflowTemplateRegistry
        try:
            registry = WorkflowTemplateRegistry()
            registry.load_templates()
            registry.publish_templates()
        except Exception as e:
            logger.error(f"Failed to register workflow templates: {e}")
```

### What WO does with the message

WO's `WorkflowTemplateRegistrationConsumer` listens to topic `workflow-templates`:
- If template code doesn't exist → **creates** new `WorkflowTemplateModel`
- If template exists with same version → **skips** (idempotent)
- If template exists with older version → **updates** to new version
- If template exists with newer version → **skips** (never downgrade)

After registration, services look up templates by code using `GET /api/v1/workflow/templates/?code={code}` to resolve the UUID for plan creation.

---

## 6. Phase 3 — Start a Workflow Plan (REST)

When a user submits an entity for approval, your service calls WO to create a plan instance from the template.

### Service-side: `OrchestrationClient`

Build a client class that wraps HTTP calls to WO. This follows the `corporate-service` pattern:

```python
# apps/infrastructure/external/orchestration_client.py

class OrchestrationClient:
    def __init__(self):
        self.base_url = settings.WORK_ORCHESTRATION_SERVICE_URL
        self.api_base = f"{self.base_url}/api/v1/workflow"
        self._service_token = settings.SERVICE_TO_SERVICE_TOKEN
    
    def start_workflow(
        self,
        template_code: str,    # e.g., 'your_service.entity_workflow'
        context: dict,          # Variables to resolve stage assignees
        initiator_id: str,      # UUID of the user starting the workflow
        metadata: dict = None,  # Extra data to store on the plan
    ) -> Optional[WorkflowPlanResult]:
        # 1. Look up template UUID from code: GET /templates/?code=...
        template_id = self._get_template_id_by_code(template_code)
        
        # 2. Create the plan
        payload = {
            'template_id': template_id,
            'workflow_type': template_code.split('.')[0],
            'created_by': initiator_id,
            'metadata': {
                **(metadata or {}),
                'context': context,
                'template_code': template_code,
            },
        }
        response = requests.post(
            f"{self.api_base}/plans/",
            json=payload,
            headers={'X-Service-Token': self._service_token},
        )
        # Return WorkflowPlanResult(plan_id, status, current_stage_id, ...)
```

### What context must contain

Context is the dictionary of variable values that WO uses to resolve `{{placeholder}}` assignees in the template stages. For example:

```python
context = {
    'applicant_id': str(leave_application.applicant.user_id),
    'line_manager_id': str(leave_application.line_manager.user_id),
    'director_id': str(department.director.user_id),
    # ... any placeholder used in your workflows.yaml stages
}
```

### What metadata should contain

```python
metadata = {
    # REQUIRED for event routing — consumer makes REST call to WO to read these fields
    # from plan.metadata. If missing, your consumer cannot route events to your handler.
    'entity_type': 'leave_application',          # must match key in ENTITY_HANDLERS dict
    'entity_id': str(leave_application.id),       # used to look up the entity in your DB
    
    # Required for WO UI "View full details" link
    'entity_detail_path': '/service/corporate/leave-applications',  # staff portal path
    
    # For display in WorkflowConsole
    'applicant_id': str(applicant.user_id),      # WO uses this to resolve applicant name
    'title': leave_application.reference_number,
    
    # Any additional display data needed by the console
    'leave_type': leave_application.leave_type,
    'start_date': str(leave_application.start_date),
}
```

### Storing plan data on your entity

Your entity model must store the plan reference. Use the `WorkflowMixin`:

```python
# apps/core/mixins/workflow_mixin.py (copy from corporate-service)

class WorkflowMixin(models.Model):
    workflow_plan_id = models.UUIDField(null=True, blank=True, db_index=True)
    workflow_stage = models.CharField(max_length=100, blank=True, default='')
    workflow_stage_id = models.UUIDField(null=True, blank=True)
    workflow_started_at = models.DateTimeField(null=True, blank=True)
    workflow_completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
```

After `start_workflow()` returns:

```python
# In your use case / view:
plan_result = orchestration_client.start_workflow(
    template_code='your_service.entity_workflow',
    context=context,
    initiator_id=str(request.user_id),
    metadata=metadata,
)

if plan_result:
    entity.workflow_plan_id = plan_result.plan_id
    entity.workflow_stage = plan_result.current_stage_name
    entity.workflow_stage_id = plan_result.current_stage_id
    entity.workflow_started_at = timezone.now()
    entity.status = 'pending'  # Entity is now awaiting approval
    entity.save()
```

### What WO does when a plan is created

1. Looks up the template by UUID
2. Reads the stage definitions from `template.definition.stages`
3. Resolves `{{placeholder}}` assignees using the `context` dict
4. Creates all stage records with `status='pending'`
5. Sets Stage 1 to `status='in_progress'` (the first active stage)
6. Calculates SLA `due_at` timestamps using the cumulative hours model
7. Returns the full plan with all stages

---

## 7. Phase 4 — UI Integration (Frontend WorkflowConsole)

### The Shared Component

The staff portal has a single shared React component `WorkflowConsole` that provides the full approval UI for **every service**. It lives in:

```
frontend/apps/staff-portal/src/components/work-orchestration/WorkflowConsole.tsx
```

It does everything:
- Fetches `GET /api/v1/workflow/plans/{planId}/` every 15 seconds
- Renders each stage with its status badge
- Shows action buttons (`Approve`, `Reject`, `Return for Amendment`) based on `user_can_act`
- Shows activity history (who acted, when, with what comment)
- Handles the approve/reject dialog (requires comment for reject/return)
- Calls `POST /api/v1/workflow/plans/{planId}/stages/{stageId}/actions/` directly against WO
- Shows `"You cannot approve your own request"` / `"You are not assigned to this stage"` messages (all decided by WO)

### What each domain service's frontend must build

Each service builds its own **entity detail page** — this is the domain-specific part. It contains:
- The entity data (leave dates, amounts, document title, etc.)  
- A "Workflow" section/tab that renders `<WorkflowConsole planId={entity.workflow_plan_id} />`

```tsx
// Example: LeaveApplicationDetailPage.tsx

import { WorkflowConsole } from "@staff/components/work-orchestration/WorkflowConsole";

export function LeaveApplicationDetailPage() {
  const { id } = useParams();
  const { data: leave } = useLeaveApplication(id);

  return (
    <div>
      {/* ── Domain-specific section (built by your team) ── */}
      <Card>
        <CardHeader>
          <CardTitle>Leave Application: {leave?.reference_number}</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Type: {leave?.leave_type}</p>
          <p>Dates: {leave?.start_date} to {leave?.end_date}</p>
          <p>Days: {leave?.total_days}</p>
          {/* ... all entity-specific detail ... */}
        </CardContent>
      </Card>

      {/* ── Workflow section (shared, no extra work needed) ── */}
      {leave?.workflow_plan_id && (
        <WorkflowConsole planId={leave.workflow_plan_id} />
      )}
    </div>
  );
}
```

### The WO-enriched plan response

When `WorkflowConsole` calls `GET /api/v1/workflow/plans/{planId}/`, WO returns an enriched response that includes user-specific fields the frontend uses directly:

```json
{
  "data": {
    "id": "plan-uuid",
    "status": "active",
    "stages": [
      {
        "id": "stage-uuid",
        "name": "Manager Approval",
        "order": 1,
        "status": "in_progress",
        "assignees": ["user-uuid"],
        "assignee_names": ["John Doe"],
        "actions": [
          { "name": "approve", "label": "Approve", "nextState": "completed" },
          { "name": "reject", "label": "Reject", "nextState": "rejected" }
        ],
        "is_locked": false,
        "is_completed": false,
        "is_active": true,
        "user_can_act": true,
        "user_already_acted": false,
        "action_blocked_reason": null
      },
      {
        "id": "stage-2-uuid",
        "name": "HR Verification",
        "order": 2,
        "status": "pending",
        "is_locked": true,
        "user_can_act": false,
        "action_blocked_reason": "Waiting for previous stage"
      }
    ],
    "user_can_approve": true,
    "user_can_reject": true,
    "action_blocked_reason": null,
    "viewer_context": {
      "is_initiator": false,
      "is_applicant": false,
      "is_assignee": true,
      "view_type": "assignee"
    }
  }
}
```

WO computes all these flags server-side — the frontend only renders what it receives.

### Alternative: Server-side rendered embedded console

WO also provides a Django `TemplateView` at:
```
GET /api/v1/workflow/plans/{planId}/console/
```
This renders `templates/workflow/generic_viewer.html` — a vanilla JS-based approval UI that is `xframe_options_exempt` (can be embedded in an `<iframe>`). This is an alternative if a context does not support React.

### `entity_detail_path` — the "View full details" link

WO's console can display a "View full details" link back to the originating service's detail page. For this to work:

1. Register the path in your service's `workflow_entity_paths.py`:
```python
ENTITY_DETAIL_PATHS = {
    'leave_application': '/service/corporate/leave-applications',
    'your_entity': '/service/your-service/your-entities',
}
```

2. Include it in plan metadata at creation time:
```python
metadata['entity_detail_path'] = '/service/your-service/your-entities'
```

---

## 8. Phase 5 — Listen for Workflow Outcome Events (Kafka)

When users take actions in WO, your service needs to know about it to update entity status in your own DB. This is done via Kafka events.

### Event types your service will receive

WO publishes to the `workflow-events` Kafka topic. Every event is wrapped in the standard `KafkaEventDispatcher` envelope:

```json
{
  "event_type": "<EventTypeName>",
  "payload": { ... }
}
```

**Your consumer handles two event types:**

**1. `WorkflowStageUpdated`** — fires every time a stage action is taken (approve, reject, return, resubmit, withdraw, etc.). Consumer should only act when `newStatus` is `"completed"` or `"rejected"`, OR `action` is one of `"return"`, `"resubmit"`, `"withdraw"`. All other intermediate updates (e.g., status `"in_review"`) are ignored.

**2. `WorkflowCompleted`** — fires when all stages resolve and the plan status becomes `"completed"`.

> **Note:** WO also publishes a third event — `{workflow_type}.workflow.completed` — from `WorkflowCompletionHandler` using a separate `kafka-python` producer. This carries richer payload (disposal data, form data, final_decision, result_data). It is published to the same `workflow-events` topic. Services that need rich completion data (e.g., document-records-service) consume this. Standard services consuming `WorkflowCompleted` do **not** need to handle this third event type.

### Event payload: WorkflowStageUpdated

All fields in the `payload` use **camelCase** keys — this is the exact structure published by WO's `advance_stage` use case:

```json
{
  "event_type": "WorkflowStageUpdated",
  "payload": {
    "planId": "plan-uuid",
    "stageId": "stage-uuid",
    "stageKey": "leave_head_approval",
    "stageName": "Head of Department Approval",
    "action": "approve",
    "actorId": "user-uuid",
    "newStatus": "completed",
    "stageMetadata": {
      "status_on_complete": "hod_approved"
    }
  }
}
```

Your consumer reads: `payload = event.get('payload', {})`, then `payload.get('planId')`, `payload.get('stageKey')`, etc.

> **Critical — entity routing via REST:** `entity_type` and `entity_id` are **NOT** embedded in the Kafka event. After reading `planId` from the event, your consumer must make a synchronous REST call back to WO (`GET /api/v1/workflow/plans/{planId}/`) to retrieve the plan's stored `metadata`, which contains `entity_type` and `entity_id`. This is why these two fields **must** be included in `metadata` when you call `start_workflow()`.

### Event payload: WorkflowCompleted

```json
{
  "event_type": "WorkflowCompleted",
  "payload": {
    "planId": "plan-uuid",
    "workflowType": "corporate_hr"
  }
}
```

The consumer reads only `planId` from this payload, then makes the same REST call (`_get_plan_metadata(plan_id)`) to fetch `entity_type` and `entity_id`. The entity handler is invoked with synthetic arguments: `action='approve'`, `stage_key='workflow_completed'`, `is_workflow_completed=True`.

### What you build in your service

**1. Kafka consumer class** (`WorkflowEventConsumer`)

```python
# apps/core/consumers/workflow_event_consumer.py

class WorkflowEventConsumer:
    # Map entity_type strings to handler methods
    ENTITY_HANDLERS = {
        'leave_application': '_handle_leave_application',
        'your_entity_type': '_handle_your_entity',
    }
    
    def process_message(self, event: dict):
        event_type = event.get('event_type', '')
        
        if event_type == 'WorkflowStageUpdated':
            self.process_workflow_stage_updated(event)
        elif event_type == 'WorkflowCompleted':
            self.process_workflow_completed(event)
        # All other event_type values (including '{type}.workflow.completed') are ignored
    
    def process_workflow_stage_updated(self, event: dict):
        # IMPORTANT: All fields are nested under 'payload' with camelCase keys
        payload = event.get('payload', {})
        
        plan_id = payload.get('planId')
        action = payload.get('action')
        new_status = payload.get('newStatus', '')
        stage_key = payload.get('stageKey', '')
        actor_id = payload.get('actorId')
        stage_metadata = payload.get('stageMetadata', {})
        status_on_complete = stage_metadata.get('status_on_complete', '')
        
        # Filter: only act on terminal stage transitions
        if (new_status not in ('completed', 'rejected')
                and action not in ('return', 'resubmit', 'withdraw')):
            return  # ignore intermediate/in-progress updates
        
        # entity_type and entity_id are NOT in the Kafka event.
        # Fetch them via a REST call to WO.
        plan_meta = self._get_plan_metadata(plan_id)
        if not plan_meta:
            return
        entity_type = plan_meta.get('entity_type')
        entity_id = plan_meta.get('entity_id')
        
        handler_name = self.ENTITY_HANDLERS.get(entity_type)
        if handler_name:
            handler = getattr(self, handler_name)
            handler(
                entity_id=entity_id,
                action=action,
                stage_key=stage_key,
                actor_id=actor_id,
                is_workflow_completed=False,
                status_on_complete=status_on_complete,
            )
    
    def process_workflow_completed(self, event: dict):
        payload = event.get('payload', {})
        plan_id = payload.get('planId')
        
        # entity_type and entity_id must be fetched from WO REST
        plan_meta = self._get_plan_metadata(plan_id)
        if not plan_meta:
            return
        entity_type = plan_meta.get('entity_type')
        entity_id = plan_meta.get('entity_id')
        
        handler_name = self.ENTITY_HANDLERS.get(entity_type)
        if handler_name:
            handler = getattr(self, handler_name)
            # WO completion always means the final decision was "approved"
            # (rejected plans never reach WorkflowCompleted).
            # stage_key is the synthetic sentinel value 'workflow_completed'.
            handler(
                entity_id=entity_id,
                action='approve',            # synthetic — plan completed = final approval
                stage_key='workflow_completed',  # synthetic sentinel
                actor_id=None,
                is_workflow_completed=True,
                status_on_complete='',
            )
    
    def _get_plan_metadata(self, plan_id: str) -> dict:
        """
        Makes a REST call to WO to retrieve the plan's stored metadata dict.
        Returns the metadata dict (containing entity_type, entity_id, etc.)
        or an empty dict on failure.
        """
        from apps.infrastructure.external.orchestration_client import OrchestrationClient
        try:
            client = OrchestrationClient()
            plan = client.get_plan(plan_id)
            return plan.metadata if plan else {}
        except Exception:
            return {}
    
    def _handle_your_entity(
        self,
        entity_id: str,
        action: str,
        stage_key: str,
        actor_id: str | None,
        is_workflow_completed: bool,
        status_on_complete: str,
    ):
        with transaction.atomic():
            entity = YourModel.objects.select_for_update().get(id=entity_id)
            
            if action == 'reject':
                entity.status = 'rejected'
            elif action == 'return':
                entity.status = 'returned'
                entity.revision_count = (entity.revision_count or 0) + 1
            elif is_workflow_completed:
                # Final plan completion — set terminal approved status
                entity.status = 'approved'
                entity.workflow_completed_at = timezone.now()
            elif status_on_complete:
                # Intermediate stage completed — apply the status declared
                # in workflows.yaml stage metadata (configurable, not hardcoded)
                entity.status = status_on_complete
            
            # Optionally record stage-specific fields (mix of declarative + imperative)
            # e.g. if stage_key == 'hod_approval':
            #     entity.hod_approved_by_id = actor_id
            #     entity.hod_approved_at = timezone.now()
            
            entity.save()
```

**2. Management command to run the consumer**

```python
# apps/core/management/commands/run_workflow_consumer.py

from django.core.management.base import BaseCommand
from apps.core.consumers.workflow_event_consumer import WorkflowEventConsumer

class Command(BaseCommand):
    def handle(self, *args, **options):
        consumer = WorkflowEventConsumer()
        consumer.run()  # blocking, long-running
```

**3. Docker Compose service for the consumer**

```yaml
# In your service's docker-compose.yml
your-service-workflow-consumer:
  build: .
  command: python manage.py run_workflow_consumer
  depends_on:
    - fims-kafka
    - your-service-db
  networks:
    - fims-network
```

---

## 9. Data Ownership Summary

| Data | Lives In | How It Flows |
|---|---|---|
| Workflow template definition | **Your service** (`workflows.yaml`) + WO's DB (copy) | Published via Kafka at startup |
| Workflow plan (stages, status, activity) | **WO's DB** | Created by your service REST call; updated by users acting in UI |
| Entity business data (leave dates, amounts, etc.) | **Your service's DB** | Fetched by your service API |
| Entity status (pending, hod_approved, approved, rejected) | **Your service's DB** | Updated by your Kafka consumer when WO publishes events |
| `workflow_plan_id` foreign key | **Your service's DB** (on the entity model) | Stored when you call `start_workflow()` |
| User action decisions (who approved what, when, comment) | **WO's DB** (`WorkflowActivityModel`) | Queried by frontend via WO API directly |
| Notification delivery | **WO's DB** | Your service publishes to Kafka notification topics |

---

## 10. Implementation Checklist for a New Service

### Backend files to create/copy

- [ ] `apps/core/workflows/workflows.yaml` — define all workflow templates
- [ ] `apps/core/workflows/registry.py` — `WorkflowTemplateRegistry` to publish templates
- [ ] `apps/core/mixins/workflow_mixin.py` — abstract model with `workflow_plan_id`, `workflow_stage`, etc.
- [ ] `apps/core/consumers/workflow_event_consumer.py` — `WorkflowEventConsumer` listening to `workflow-events`
- [ ] `apps/infrastructure/external/orchestration_client.py` — `OrchestrationClient` wrapping WO REST calls
- [ ] Entity models inherit `WorkflowMixin`
- [ ] `apps/core/apps.py` — call `registry.publish_templates()` in `ready()`
- [ ] `apps/core/management/commands/run_workflow_consumer.py` — Django management command
- [ ] `docker-compose.yml` — add `your-service-workflow-consumer` container

### Settings to add

```python
# settings.py
WORK_ORCHESTRATION_SERVICE_URL = os.getenv('WORK_ORCHESTRATION_SERVICE_URL', 'http://work-orchestration-service:8004')
SERVICE_TO_SERVICE_TOKEN = os.getenv('SERVICE_TO_SERVICE_TOKEN', 'fims-service-secret-token')
KAFKA_WORKFLOW_TEMPLATES_TOPIC = 'workflow-templates'
KAFKA_WORKFLOW_EVENTS_TOPIC = 'workflow-events'
KAFKA_WORKFLOW_EVENTS_CONSUMER_GROUP = 'your-service-workflow-consumer'
```

### Frontend files to create

- [ ] Entity detail page (e.g., `YourEntityDetailPage.tsx`) — builds entity-specific UI
- [ ] Import and render `<WorkflowConsole planId={entity.workflow_plan_id} />` in that page
- [ ] Route to that detail page in `App.tsx`
- [ ] Register entity path in `workflow_entity_paths.py` (backend — for WO console link)

---

## 11. Complete Data Flow Diagram

```
YOUR SERVICE                        KAFKA                      WORK ORCHESTRATION
────────────                        ─────                      ──────────────────

[Service startup]
apps.py ready()
  └── WorkflowTemplateRegistry      workflow-templates ──────► WorkflowTemplateConsumer
      publish templates ────────────────────────────────────►   stores WorkflowTemplateModel
      (idempotent, version-aware)


[User submits entity for approval]
OrchestrationClient
  .start_workflow(code, context,    HTTP POST /plans/ ────────► CreateWorkflowPlanUseCase
   initiator_id, metadata) ────────────────────────────────────  resolves {{context}} assignees
                                                                  creates stages (stage 1 = in_progress)
                          ◄────────── returns plan JSON ─────────  stage 2,3... = pending
entity.workflow_plan_id = plan_id


[Approver opens approval page]
                                                               ◄── GET /plans/{planId}/
                HTML/JSON plan data ───────────────────────►
                (with user_can_act, assignee_names,            enriches with user permission flags
                 action_blocked_reason)


[Approver clicks "Approve"]
                                    HTTP POST                  ► AdvanceStageUseCase
                                    /plans/{planId}/           ────────────────────────
                                    stages/{stageId}/actions/    validates assignee
                                                                  validates not initiator
                                                                  validates not already acted
                                                                  updates stage to completed
                                                                  auto-advances to next stage
                                    ◄── updated plan JSON ────    (or sets plan.completed)


[Every stage terminal action (approve/reject/return/resubmit/withdraw)]
                                                               WO KafkaEventDispatcher
                                    workflow-events ◄───────── publishes WorkflowStageUpdated
YOUR Kafka Consumer                                            {"event_type": "WorkflowStageUpdated",
  WorkflowEventConsumer                                         "payload": {camelCase fields}}
  .process_message(event)
     │
     ├── payload = event.get('payload', {})
     ├── plan_id = payload['planId']
     ├── Ignored if new_status not in ('completed','rejected')
     │   AND action not in ('return','resubmit','withdraw')
     │
     ├── _get_plan_metadata(plan_id)
     │   └── REST GET /plans/{plan_id}/ → WO returns plan with metadata
     │       (entity_type, entity_id must be in metadata — set at plan creation)
     │
     └── routes by entity_type → updates entity.status in your DB
         (status from status_on_complete YAML field)
         (stage-specific timestamps/IDs set by stage_key check)

[When ALL stages complete — plan.status = 'completed']
                                    workflow-events ◄───────── WO dispatches WorkflowCompleted
YOUR Kafka Consumer                                            {"event_type": "WorkflowCompleted",
  process_workflow_completed(event)                            "payload": {"planId": ..., "workflowType": ...}}
     ├── reads only planId from payload
     ├── REST GET to fetch entity_type / entity_id
     └── calls handler(action='approve', stage_key='workflow_completed',
                        is_workflow_completed=True)

[Also published on plan completion — for richer downstream needs]
                                    workflow-events ◄───────── WO WorkflowCompletionHandler
                                                               event_type: "{workflow_type}.workflow.completed"
                                                               (kafka-python producer, separate from dispatcher)
                                                               includes: result_data, disposal_data, approval_data
                                                               (standard consumer ignores this event_type)
```

---

## 12. Anti-Patterns — What Never To Do

| ❌ Anti-Pattern | ✅ Correct Approach |
|---|---|
| Build your own approval UI (approve/reject buttons, stage visualization) | Use the shared `WorkflowConsole` React component |
| Store who approved what in your service's DB | Read activity from WO API; WO owns the immutable audit trail |
| Check in your service whether a user is allowed to approve | Let WO do it; it returns `user_can_act` and `action_blocked_reason` |
| Duplicate stage logic (sequential enforcement, initiator exclusion) | WO enforces all of this automatically |
| Read `entity_type`/`entity_id` directly from the Kafka event payload | They are NOT in the event. Make a REST call to `GET /plans/{planId}/` to retrieve plan metadata — which is why you must set `entity_type`/`entity_id` in `metadata` at plan creation |
| Parse top-level fields (`event.get('plan_id')`, `event.get('action')`) | All data is inside `event.get('payload', {})` with camelCase keys (`planId`, `stageKey`, `actorId`, `newStatus`, `stageMetadata`) |
| Hard-code ALL entity status transitions in consumer Python code | Use `status_on_complete` in `workflows.yaml` for generic transitions; only write imperative stage_key checks for stage-specific field recording (timestamps, approver IDs) |
| Act on every `WorkflowStageUpdated` event | Filter: only process when `newStatus in ('completed', 'rejected')` OR `action in ('return', 'resubmit', 'withdraw')` |
| Direct DB access to WO's tables | Only communicate via REST API and Kafka events |
| Re-implement notification sending for workflow approvals | Use WO's notification system via Kafka (see `WORK_ORCHESTRATION_NOTIFICATIONS.md`) |
| Create a new plan for every page reload | Call `start_workflow()` once when entity is submitted; store `workflow_plan_id` on entity |
| Poll WO for plan status from your backend | Store `workflow_plan_id` and let the frontend query WO directly; or react to Kafka events |
| Implement your own workflow template logic | Everything must be in `workflows.yaml` and registered with WO via Kafka |

---

## See Also

- [WORK_ORCHESTRATION_INTEGRATION.md](./WORK_ORCHESTRATION_INTEGRATION.md) — frontend template YAML reference and stage integration examples
- [WORK_ORCHESTRATION_NOTIFICATIONS.md](./WORK_ORCHESTRATION_NOTIFICATIONS.md) — notification template registration and publishing
- `corporate-service/apps/core/workflows/` — reference implementation of template registry
- `corporate-service/apps/core/consumers/workflow_event_consumer.py` — reference consumer implementation
- `corporate-service/apps/infrastructure/external/orchestration_client.py` — reference REST client
- `frontend/apps/staff-portal/src/components/work-orchestration/WorkflowConsole.tsx` — the shared UI component


[def]: #12-anti-patterns--what-never-to-do