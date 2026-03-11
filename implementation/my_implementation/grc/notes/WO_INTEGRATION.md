# GRC ↔ Work Orchestration Service Integration

> **Purpose:** Complete technical reference for the interview. Covers every file, every class, every condition, and the exact data flow for the GRC–WO integration. Written from actual code analysis.

---

## Table of Contents

1. [Did We Integrate? — Yes](#1-did-we-integrate--yes)
2. [The Big Picture](#2-the-big-picture)
3. [Every File Involved](#3-every-file-involved)
4. [Workflow Templates — workflows.yaml](#4-workflow-templates--workflowsyaml)
5. [WorkflowMixin — Base Model Fields](#5-workflowmixin--base-model-fields)
6. [Model Methods (per entity)](#6-model-methods-per-entity)
7. [OrchestrationClient — HTTP to WO](#7-orchestrationclient--http-to-wo)
8. [Service Layer — submit_for_approval / start_workflow](#8-service-layer--submit_for_approval--start_workflow)
9. [API Views — How Requests Arrive](#9-api-views--how-requests-arrive)
10. [Kafka Consumer — WO Events Come Back](#10-kafka-consumer--wo-events-come-back)
11. [Template Registration — How Templates Get Into WO](#11-template-registration--how-templates-get-into-wo)
12. [GRC Kafka Consumer Container](#12-grc-kafka-consumer-container)
13. [Complete Flow — Working Paper Example](#13-complete-flow--working-paper-example)
14. [Complete Flow — Audit Engagement Lifecycle](#14-complete-flow--audit-engagement-lifecycle)
15. [Status Transitions Table (all entities)](#15-status-transitions-table-all-entities)
16. [Key Design Decisions & Conditions](#16-key-design-decisions--conditions)
17. [What Triggers What — Quick Reference](#17-what-triggers-what--quick-reference)

---

## 1. Did We Integrate? — Yes

Every major GRC audit entity has a **full two-way integration** with WO:

| GRC Entity | WO Template | Triggered By | WO Notifies GRC Back Via |
|---|---|---|---|
| `WorkingPaper` | `grc.working_paper_approval` | API `POST /submit/` | Kafka `workflow-events` |
| `AuditUniverse` | `grc.audit_universe_approval` | API `POST /submit-for-review/` | Kafka `workflow-events` |
| `AuditPlan` (RBIAP) | `grc.rbiap_approval` | API `POST /submit-for-approval/` | Kafka `workflow-events` |
| `AuditEngagement` | `grc.engagement_lifecycle` | API `POST /start-workflow/` | Kafka `workflow-events` |
| `AuditReport` | `grc.audit_report_approval` | API `POST / (inline)` | Kafka `workflow-events` |
| `AuditMemo` | `grc.audit_memo_approval` | API `POST /submit-for-approval/` | Kafka `workflow-events` |
| `AuditProgram` | `grc.audit_program_approval` | API `POST /submit-for-approval/` | Kafka `workflow-events` |
| `EngagementNotification` | `grc.engagement_notification_approval` | API `POST /submit/` | Kafka `workflow-events` |

---

## 2. The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GRC SERVICE                                    │
│                                                                             │
│  1. User clicks "Submit" / "Start Workflow" in Frontend                     │
│       │                                                                     │
│       ▼                                                                     │
│  2. API ViewSet action method (e.g. AuditUniverseViewSet.submit_for_review) │
│       │                                                                     │
│       ▼                                                                     │
│  3. Service class (e.g. AuditUniverseService.submit_for_approval)           │
│       │  calls entity.get_workflow_context()                                │
│       │  calls entity.get_workflow_metadata()                               │
│       │  calls entity.get_workflow_stages()   (inline fallback)             │
│       │                                                                     │
│       ▼                                                                     │
│  4. OrchestrationClient.start_workflow()                                    │
│       │  → _get_template_id_by_code()  (queries WO /templates/ API)        │
│       │  → POST /api/v1/workflow/plans/ (HTTP with X-Service-Token)         │
│       │  ← returns plan_id + current_stage_id/name                         │
│       │                                                                     │
│       ▼                                                                     │
│  5. Service saves 5 WorkflowMixin fields on the model + updates status      │
│       workflow_plan_id, workflow_stage, workflow_stage_id,                  │
│       workflow_started_at  ← saved NOW                                      │
│       workflow_completed_at ← saved later by Kafka consumer                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                    │  HTTP 201 created                   ▲
                    ▼                                     │
┌──────────────────────────────────────────────────────────────────────────────┐
│                       WORK ORCHESTRATION SERVICE                             │
│                                                                              │
│  - Stores WorkflowPlan + WorkflowStage records                               │
│  - Serves embedded console iframe to frontend                                │
│  - Users approve/reject stages in WO console                                 │
│  - Publishes events to Kafka topic 'workflow-events' on:                     │
│      • each stage action  → event_type ends '.stage.completed'               │
│      • all stages done    → event_type ends '.workflow.completed'            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                         │  Kafka 'workflow-events'
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    GRC KAFKA CONSUMER (separate container)                   │
│                                                                              │
│  GRCKafkaConsumer._handle_workflow_event()                                   │
│       │  filters: workflow_type == 'grc'                                     │
│       │  routes by template_code from metadata                               │
│       ▼                                                                      │
│  _handle_*_completion()   → updates entity status in GRC DB                 │
│  _handle_audit_report_completion()  → also publishes finding.finalized       │
│  _trigger_approved_stamp()  → calls DRS to stamp PDF with CIA signature      │
│  _publish_universe_decision_notification() → Kafka notification to user      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Every File Involved

```
grc-service/
│
├── apps/core/workflows/
│   ├── workflows.yaml              ← All 9 WO template definitions (YAML source of truth)
│   └── registry.py                 ← Loads YAML; WorkflowTemplateRegistry class
│
├── apps/core/workflow_entity_paths.py  ← Maps entity_type → frontend URL for "View details" link
│
├── apps/core/models/
│   ├── base.py                     ← WorkflowMixin (5 fields all entities use)
│   └── audit_entities.py           ← Each entity: get_workflow_context, get_workflow_metadata,
│                                       get_workflow_stages methods
│
├── apps/infrastructure/external/
│   └── orchestration_client.py     ← OrchestrationClient class — HTTP calls to WO
│
├── apps/core/services/
│   ├── working_paper_service.py    ← WorkingPaperService.submit_for_approval()
│   ├── audit_universe_service.py   ← AuditUniverseService.submit_for_approval()
│   ├── audit_plan_service.py       ← AuditPlanService.submit_for_approval()
│   ├── audit_engagement_service.py ← AuditEngagementService.start_workflow()
│   ├── audit_memo_service.py       ← AuditMemoService.submit_for_approval()
│   ├── audit_program_service.py    ← AuditProgramService.submit_for_approval()
│   ├── audit_report_service.py     ← (report submission is done inline in the view)
│   └── engagement_notification_service.py ← EngagementNotificationService
│
├── apps/api/views/
│   ├── audit_engagement_views.py   ← AuditEngagementViewSet.start_workflow action
│   ├── audit_universe_views.py     ← AuditUniverseViewSet.submit_for_review action
│   ├── working_paper_views.py      ← WorkingPaperViewSet.submit action
│   ├── audit_plan_views.py         ← AuditPlanViewSet.submit_for_approval action
│   ├── audit_memo_views.py         ← AuditMemoViewSet.submit_for_approval action (inline)
│   └── audit_program_views.py      ← AuditProgramViewSet.submit_for_approval action (inline)
│
├── apps/infrastructure/messaging/
│   └── kafka_consumer.py           ← GRCKafkaConsumer — receives WO events back
│
├── apps/core/management/commands/
│   ├── consume_grc_events.py       ← Django management command that runs the consumer
│   └── register_workflow_templates.py ← Dev/verify command: list templates + --fetch from WO
│
├── apps/core/apps.py               ← Django ready() hook — loads YAML on startup,
│                                       does NOT send to WO (WO has no inbound endpoint)
│
└── docker-compose.yml              ← grc-kafka-consumer service: runs consume_grc_events
```

---

## 4. Workflow Templates — workflows.yaml

**File:** `apps/core/workflows/workflows.yaml`

This is the single source of truth for all GRC approval/lifecycle process definitions.
There are **9 templates** defined:

### Template Summary

| Template Code | Template Name | Stages | SLA (total) | Special |
|---|---|---|---|---|
| `grc.working_paper_approval` | Working Paper Approval | 2 | 48 hrs | `{{lead_auditor}}` assignee in stage 1 |
| `grc.audit_universe_approval` | Audit Universe Approval | 1 | 72 hrs | No assignees (anyone in role) |
| `grc.rbiap_approval` | RBIAP Approval | 4 | ~28 days | CIA → Management → Committee → Commission |
| `grc.engagement_lifecycle` | Audit Engagement Lifecycle | 3 | ~35 days | Stage events used (planning→fieldwork→reporting) |
| `grc.engagement_notification_approval` | Engagement Notification Approval | 1 | 48 hrs | CIA single-stage approval |
| `grc.audit_memo_approval` | Audit Memo Approval | 2 | 7 days | CIA → DG approval |
| `grc.audit_program_approval` | Audit Program Approval | 2 | 5 days | IA review → CIA approval |
| `grc.audit_report_approval` | Audit Report Approval | 2 | 7 days | IA review → CIA approval |
| `grc.quarterly_report_approval` | Quarterly Audit Report Approval | 4 | 14 days | CIA → Management → Committee → Commission |

### Field-by-field Explanation

```yaml
templates:
  - code: "grc.rbiap_approval"      # Unique code GRC uses to identify this template.
                                     # OrchestrationClient maps this → WO workflow_type
    name: "RBIAP Approval"           # Human-readable name stored in WO
    workflow_type: "grc"             # WO groups plans by this. All GRC templates use "grc"
    version: 1                       # Increment when you change stage definitions
    definition:
      description: "..."
      sla:
        targetMinutes: 40320         # Overall SLA deadline for the whole workflow
        breachStrategy: "escalate"   # "escalate" = notify supervisor; "notify" = notify assignee
      metadata:
        module: "grc"                # Stored with WO template for filtering/display
        category: "audit_plan"       # WO uses this to categorise plans in its console
      stages:
        - definitionKey: "cia_review"      # ← KEY FIELD: matches stage_key in Kafka events
          name: "CIA Review"               #   and stage_key used in STAGE_STATUS_MAP
          order: 1                         # Stage sequence (1-based in YAML, 0-based in inline)
          assignees: []                    # Empty = anyone with access; "{{lead_auditor}}" =
                                           # resolved from context.lead_auditor at runtime
          actions:
            - name: "approve"              # ← action name used in STAGE_STATUS_MAP
              label: "Approve"             # Button text in WO console
              nextState: "completed"       # "completed" → WO advances to next stage
            - name: "return"
              label: "Return to Auditor"
              nextState: "rejected"        # "rejected" → WO marks stage rejected; workflow may end
          sla:
            durationMinutes: 4320          # Per-stage SLA (72 hrs)
            breachStrategy: "notify"
```

### `assignees` Values Used

| Value | What It Means | Which Templates |
|---|---|---|
| `[]` (empty array) | No specific assignee — anyone with the right role can act | Most approval templates |
| `["{{lead_auditor}}"]` | Resolved at runtime from `context.lead_auditor` UUID | `grc.working_paper_approval`, `grc.engagement_lifecycle` |

The `{{lead_auditor}}` placeholder is populated from `context` which GRC embeds in the plan metadata when calling `start_workflow()`. WO's assignee resolver reads `metadata.context.lead_auditor` and sets that user as the stage assignee.

### `nextState` Values

| Value | WO Behaviour | GRC Effect |
|---|---|---|
| `"completed"` | Stage moves to complete; next stage activates | Kafka fires `*.stage.completed` event |
| `"rejected"` | Stage marked rejected; depending on WO config, workflow may end | Kafka fires `*.workflow.completed` with `final_decision: "rejected"` |
| `"pending"` | Stage stays in progress (e.g. "Request Changes" keeps it open) | No state change event — assignee must act again |

### IMPORTANT: How Templates Actually Get Into WO

> **Templates CANNOT be sent from GRC to WO via Kafka.** WO has no Kafka consumer for a `workflow-templates` topic.

**Correct flow:**
1. GRC defines template in `workflows.yaml` (GRC's local reference copy)
2. The *same* template must be seeded into WO's own database using WO's management command:
   ```bash
   docker exec fims-work-orchestration-service python manage.py seed_workflow_templates
   ```
3. GRC's `OrchestrationClient` queries WO's `/api/v1/workflow/templates/` API at runtime to get the UUID
4. That UUID is used when creating a plan: `POST /api/v1/workflow/plans/` with `template_id`

**Fallback:** If WO templates haven't been seeded yet, GRC sends **inline stages** directly in the plan creation payload (the `get_workflow_stages()` method on each model). This is a safety net — `template_id` is preferred.

---

## 5. WorkflowMixin — Base Model Fields

**File:** `apps/core/models/base.py`

Every GRC entity that uses WO inherits from both its domain base and `WorkflowMixin`:

```python
class WorkflowMixin(models.Model):
    workflow_plan_id     = UUIDField(null=True, blank=True)  # WO Plan UUID
    workflow_stage       = CharField(max_length=255, blank=True, default='')  # Current stage name
    workflow_stage_id    = UUIDField(null=True, blank=True)  # WO Stage UUID
    workflow_started_at  = DateTimeField(null=True, blank=True)  # Set when plan is created
    workflow_completed_at = DateTimeField(null=True, blank=True)  # Set by Kafka consumer
    class Meta:
        abstract = True
```

**Who sets each field:**

| Field | Set By | When |
|---|---|---|
| `workflow_plan_id` | Service `submit_for_approval()` | After successful WO plan creation |
| `workflow_stage` | Service `submit_for_approval()` | First stage name from WO response |
| `workflow_stage_id` | Service `submit_for_approval()` | First stage UUID from WO response |
| `workflow_started_at` | Service `submit_for_approval()` | `timezone.now()` at submission |
| `workflow_completed_at` | Kafka consumer `_handle_*_completion()` | When WO fires `*.workflow.completed` |

**Declaration pattern on models:**

```python
class AuditUniverse(TimestampedModel, StatusMixin, WorkflowMixin):  # ← 3 mixins
    ...
```

---

## 6. Model Methods (per entity)

Each entity model defines **3 methods** that the service layer calls (FIMS pattern from the WO integration guide §4.1):

### `get_workflow_context()`
Variables used by WO to **resolve stage assignees**. The `{{lead_auditor}}` placeholder in the YAML is resolved from this dict.

```python
# AuditEngagement example
def get_workflow_context(self) -> dict:
    return {
        "audit_engagement_id": str(self.id),
        "lead_auditor": str(self.lead_auditor),   # ← resolves {{lead_auditor}} in YAML
        "audit_plan_id": str(self.audit_plan_id),
    }
```

### `get_workflow_metadata()`
Data stored **inside the WO plan** — used by the embedded console and for WO→GRC routing via Kafka. The critical field is `entity_type` + `entity_id` which the Kafka consumer uses to find the right GRC record.

```python
# AuditEngagement example
def get_workflow_metadata(self) -> dict:
    meta = {
        "entity_type": "audit_engagement",     # ← used by Kafka consumer to route event
        "entity_id": str(self.id),             # ← used by Kafka consumer to find record
        "reference_number": self.reference_number,
        "title": self.title,
        "entity_detail_path": "/service/grc/engagements",  # ← "View details" link in WO console
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, "audit_engagement")
```

> **`entity_detail_path`** is added by `add_entity_detail_path_to_metadata()` from `workflow_entity_paths.py`. This tells the WO embedded console where to send the user when they click "View full details".

### `get_workflow_stages()`
**Inline stage definitions** — used as a fallback when WO templates haven't been seeded. Same structure as the YAML but as Python dicts. Key difference: `definition_key` (snake_case) not `definitionKey` (camelCase).

```python
# AuditUniverse example (1-stage, simplified)
def get_workflow_stages(self) -> list:
    return [
        {
            "definition_key": "cia_review",
            "name": "CIA Review",
            "order": 0,
            "assignees": [],
            "actions": [
                {"name": "approve", "label": "Approve",  "next_state": "completed"},
                {"name": "return",  "label": "Return",   "next_state": "rejected"},
            ],
            "form_schema": {
                "fields": [{"name": "comments", "type": "textarea", "required": False}]
            },
            "sla": {"targetHours": 72},
        }
    ]
```

---

## 7. OrchestrationClient — HTTP to WO

**File:** `apps/infrastructure/external/orchestration_client.py`

This class handles all HTTP communication with WO. Three public methods used:

### `start_workflow()` — Creates a Plan

```python
def start_workflow(
    self,
    template_code: str,       # e.g. "grc.audit_universe_approval"
    context: dict,             # entity.get_workflow_context()
    initiator_id: str,         # UUID of user clicking "Submit"
    subject_ref: str,          # entity UUID — embedded in metadata for WO→GRC routing
    metadata: dict,            # entity.get_workflow_metadata()
    stages: list = None,       # entity.get_workflow_stages() — inline fallback
    template_id: str = None,   # override — skips _get_template_id_by_code if provided
    auth_token: str = None,    # user JWT (passed to WO to create plan as that user)
) -> Optional[WorkflowPlanResult]
```

**Resolution order for template_id:**
1. Caller-supplied `template_id` (explicit override, rarely used)
2. `_get_template_id_by_code(template_code)` — queries WO `/api/v1/workflow/templates/` and matches by `workflow_type`
3. Inline `stages` fallback — only sent when no `template_id` resolved

**What gets sent to WO (`POST /api/v1/workflow/plans/`):**
```json
{
  "template_id": "wo-uuid-if-resolved",
  "workflow_type": "grc",
  "created_by": "user-uuid",
  "metadata": {
    "entity_type": "audit_universe",
    "entity_id": "grc-uuid",
    "fiscal_year": "2025/2026",
    "entity_detail_path": "/service/grc/audit-universe",
    "context": { "audit_universe_id": "...", "fiscal_year_id": "..." },
    "subject_ref": "grc-entity-uuid",
    "template_code": "grc.audit_universe_approval"
  },
  "tags": [],
  "sla": {}
}
```

**OR when no template_id (inline fallback mode):**
Replace `"template_id"` with `"stages": [...]` array.

### `_get_template_id_by_code()` — Template UUID Lookup

```python
TEMPLATE_CODE_TO_WO_TYPE = {
    "grc.working_paper_approval":           "grc_working_paper_approval",
    "grc.audit_universe_approval":          "grc_audit_universe_approval",
    "grc.rbiap_approval":                   "grc_rbiap_approval",
    "grc.engagement_lifecycle":             "grc_engagement_lifecycle",
    "grc.engagement_notification_approval": "grc_engagement_notification_approval",
    "grc.audit_report_approval":            "grc_audit_report_approval",
    "grc.audit_memo_approval":              "grc_audit_memo_approval",
    "grc.audit_program_approval":           "grc_audit_program_approval",
    "grc.quarterly_report_approval":        "grc_quarterly_report_approval",
}
```

- Maps our `template_code` → WO's `workflow_type` field
- Queries `GET /api/v1/workflow/templates/` and finds the matching record
- **Caches result in process memory** (`_template_id_cache` class variable) — no repeated API calls
- Returns `None` if WO is unreachable or template not seeded → triggers inline stages fallback

### `get_plan_status()` and `get_plan_activity()`

```python
# Used by API views to show current workflow state + history to the frontend
def get_plan_status(self, plan_id: str) -> Optional[dict]:
    # GET /api/v1/workflow/plans/{plan_id}/

def get_plan_activity(self, plan_id: str) -> List[dict]:
    # GET /api/v1/workflow/plans/{plan_id}/activity/
```

### Authentication Headers

```python
def _headers(self, auth_token=None):
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}  # Pass user JWT to WO
    elif self.service_token:
        return {"X-Service-Token": self.service_token}    # Service-to-service auth
```

This is important: when submitting a plan, the **user's JWT** is forwarded so WO records the correct `created_by`. For status checks, the service token is used.

---

## 8. Service Layer — submit_for_approval / start_workflow

**Files:** `apps/core/services/*.py`

Every service follows the identical 4-step pattern (from WO integration guide §4.2):

```python
class AuditUniverseService:
    WORKFLOW_TEMPLATE_CODE = "grc.audit_universe_approval"

    @transaction.atomic
    def submit_for_approval(self, universe_id, submitter_id, auth_token=None):
        universe = AuditUniverse.objects.select_for_update().get(id=universe_id)

        # Guard: skip if already submitted
        if universe.workflow_plan_id:
            return universe   # ← idempotent: can be called twice safely

        # Step 1: context — assignee resolution variables
        context = universe.get_workflow_context()

        # Step 2: metadata — display data + entity routing info
        metadata = universe.get_workflow_metadata()

        # Step 3: start workflow (HTTP POST to WO)
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(universe.id),
            metadata=metadata,
            stages=universe.get_workflow_stages(),   # ← inline fallback
            auth_token=auth_token,
        )

        # Step 4: save WO plan info + update entity status
        if result and result.plan_id:
            universe.workflow_plan_id = result.plan_id
            universe.workflow_stage = result.current_stage_name or ""
            universe.workflow_stage_id = result.current_stage_id or None
            universe.workflow_started_at = timezone.now()
            universe.status = "under_review"       # ← entity-specific status change
            universe.save(update_fields=[...])

            # Step 5 (bonus): publish Kafka notification to CIA reviewer
            self._publish_submission_notification(universe, submitter_id)
        else:
            logger.error("Failed to start workflow for AuditUniverse %s", universe.id)

        return universe
```

**Key conditions checked at service level:**

| Service | Guard Condition | What Happens If Failed |
|---|---|---|
| All | `workflow_plan_id` already set | Silently return entity (idempotent) |
| `AuditEngagementService` | `audit_program` must be approved | 400 error raised in view before service called |
| All | WO returns non-201 | `result` is `None`; entity status NOT updated; error logged |

**`select_for_update()` — Why It's Used**

All services use `select_for_update()` when loading the entity. This puts a row-level DB lock so if two requests try to submit the same entity simultaneously, only one creates a WO plan.

---

## 9. API Views — How Requests Arrive

**Files:** `apps/api/views/*.py`

Each entity's ViewSet has a `@action` decorated method. Example pattern:

```python
@action(detail=True, methods=['post'], url_path='submit-for-review')
def submit_for_review(self, request, pk=None):
    user_id = getattr(request, 'user_id', None)

    # Extract user's JWT to pass to WO (so WO records the real user)
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    auth_token = auth_header.removeprefix('Bearer ').strip() or None

    service = AuditUniverseService()
    universe = service.submit_for_approval(
        universe_id=str(pk),
        submitter_id=str(user_id),
        auth_token=auth_token,
    )

    return Response({
        "success": True,
        "data": AuditUniverseSerializer(universe).data,
        "workflow_plan_id": str(universe.workflow_plan_id) if universe.workflow_plan_id else None,
    })
```

**Special case — AuditEngagement:**
The view checks that the engagement has an **approved audit program** before calling the service:
```python
# In audit_engagement_views.py before calling service:
has_approved_program = AuditProgram.objects.filter(
    engagement=engagement, status='approved'
).exists()
if not has_approved_program:
    return Response({"error": "Audit program must be approved first"}, status=400)
```

**Special case — AuditMemo and AuditProgram:**
These call `OrchestrationClient.start_workflow()` directly inside the view (no separate service class), following the same 4-step pattern inline.

---

## 10. Kafka Consumer — WO Events Come Back

**File:** `apps/infrastructure/messaging/kafka_consumer.py`

This is the **inbound** half of the integration. Running in its own Docker container, it subscribes to `workflow-events` and updates GRC entities when WO reports decisions.

### Topics Subscribed To

```python
self.topics = [
    'fims.iam.user.updated',
    'fims.iam.role.updated',
    'fims.iam.permission.updated',
    'fims.documents.document.created',
    'fims.documents.document.updated',
    'fims.documents.document.archived',
    'fims.documents.document.deleted',
    'workflow-events',          # ← WO publishes here on every stage/workflow event
]
```

### Event Routing Logic

```python
def _handle_workflow_event(self, event_data, topic):
    event_type = event_data.get('event_type', '')        # e.g. "grc.workflow.completed"
    workflow_type = event_data.get('workflow_type', '')  # e.g. "grc"
    final_decision = event_data.get('final_decision', '') # "approved" | "rejected" | "cancelled"
    metadata = event_data.get('metadata', {})

    is_stage_event = event_type.endswith('.stage.completed')
    is_workflow_event = event_type.endswith('.workflow.completed')

    # Filter: ONLY process GRC events
    if workflow_type != 'grc' or not (is_stage_event or is_workflow_event):
        return   # ← ignore Corporate, Document, etc. workflow events

    subject_ref = metadata.get('subject_ref')   # ← GRC entity UUID
    template_code = metadata.get('template_code', '')   # ← which entity type

    # Route to the right handler
    if template_code == 'grc.working_paper_approval':
        self._handle_working_paper_completion(subject_ref, final_decision, event_data)
    elif template_code == 'grc.audit_universe_approval':
        self._handle_audit_universe_completion(subject_ref, final_decision)
    elif template_code == 'grc.rbiap_approval':
        self._handle_audit_plan_completion(subject_ref, final_decision, event_data)
    elif template_code == 'grc.engagement_lifecycle':
        self._handle_audit_engagement_stage(subject_ref, final_decision, metadata)
    elif template_code == 'grc.audit_report_approval':
        self._handle_audit_report_completion(subject_ref, final_decision, event_data)
    elif template_code == 'grc.audit_memo_approval':
        self._handle_audit_memo_completion(subject_ref, final_decision, event_data)
    elif template_code == 'grc.audit_program_approval':
        self._handle_audit_program_completion(subject_ref, final_decision, event_data)
    elif template_code == 'grc.engagement_notification_approval':
        self._handle_engagement_notification_completion(subject_ref, final_decision, event_data)
```

### What Each Handler Does

**`_handle_working_paper_completion()`**
```python
if final_decision == 'approved':
    wp.review_status = 'approved'
elif final_decision in ('rejected',):
    wp.review_status = 'reviewed'     # back to reviewed (not draft)
    # also reads result_data.comments and saves to review_comments
elif final_decision == 'cancelled':
    wp.review_status = 'draft'
```

**`_handle_audit_universe_completion()`**
```python
if final_decision == 'approved':
    universe.status = 'approved'
    universe.approved_at = timezone.now()
    universe.workflow_completed_at = timezone.now()
    # Publishes 'grc.audit_universe.approved' Kafka notification to submitter
elif final_decision in ('rejected', 'cancelled'):
    universe.status = 'draft'
    universe.workflow_plan_id = None   # ← clears WO link so it can be resubmitted
    universe.workflow_stage = ''
    universe.workflow_stage_id = None
    # Publishes 'grc.audit_universe.returned' notification
```

**`_handle_audit_plan_completion()`**
```python
if final_decision == 'approved':
    plan.status = 'approved'
    plan.committee_approved_at = timezone.now()
    plan.workflow_completed_at = timezone.now()
    # Also publishes domain event via messaging_service
elif final_decision in ('rejected', 'cancelled'):
    plan.status = 'draft'
    # clears all workflow fields
```

**`_handle_audit_engagement_stage()`** ← SPECIAL CASE

This handles BOTH per-stage events AND final events:

```python
# Map (stage_key, action_name) → next GRC status
STAGE_STATUS_MAP = {
    ('planning', 'start_fieldwork'): 'fieldwork',
    ('fieldwork', 'start_reporting'): 'reporting',
}

stage_key = metadata.get('stage_key', '')
action_name = metadata.get('action_name', '')

new_status = STAGE_STATUS_MAP.get((stage_key, action_name))
if new_status:
    engagement.status = new_status   # ← intermediate status update (fieldwork/reporting)
    engagement.save(update_fields=['status'])
    return   # ← done for stage events

# Final workflow event:
if final_decision == 'approved':
    engagement.status = 'completed'
    engagement.workflow_completed_at = timezone.now()
    engagement.actual_end_date = timezone.now().date()
elif final_decision in ('rejected', 'cancelled'):
    engagement.status = 'planning'   # ← reset
    # clears workflow fields
```

**`_handle_audit_report_completion()`** ← MOST COMPLEX

On approval, does 3 things:
1. Sets `status='approved'`, `approval_date`, `workflow_completed_at`
2. **GAP 12**: publishes `finding.finalized` Kafka events for ALL findings in the engagement
3. **GAP 9**: calls `DocumentServiceClient.generate_approved_stamp()` to stamp PDF with CIA signature + QR code

**`_trigger_approved_stamp()`** — Called by report, memo, program, EN on approval
```python
client = DocumentServiceClient(auth_token=None)
result = client.generate_approved_stamp(
    document_id=document_id,    # DRS document UUID
    approver_id=approver_id,    # CIA user UUID
    entity_type=entity_type,    # e.g. 'audit_report'
    entity_id=entity_id,        # GRC entity UUID
    service_token=service_token,
)
stamped_url = result.get('stamped_document_url')
setattr(entity, stamp_field, stamped_url)   # saves URL back to model
```

**`_handle_engagement_notification_completion()`**
```python
if final_decision == 'approved':
    en.status = 'approved'
    en.cia_approval_date = timezone.now()
    # Also calls _trigger_approved_stamp if document attached
    # Also calls EngagementNotificationService._publish_approval_notification()
elif final_decision in ('rejected', 'cancelled'):
    en.status = 'draft'
    # clears workflow fields
    # Calls _publish_approval_notification(approved=False, comments=...)
```

---

## 11. Template Registration — How Templates Get Into WO

**Important distinction:**
- `apps/core/apps.py` `ready()` → loads YAML locally (just validates/logs). Does NOT send to WO.
- `apps/core/management/commands/register_workflow_templates.py` → dev tool to list templates and optionally verify them in WO with `--fetch`
- **Actual seeding in WO** → done in WO's own container:
  ```bash
  docker exec fims-work-orchestration-service python manage.py seed_workflow_templates
  ```

### `registry.py` — What It Does

```python
class WorkflowTemplateRegistry:
    def __init__(self):
        self.templates = self._load_templates()   # reads workflows.yaml

    def get_template(self, code: str) -> Optional[dict]:
        return self.templates.get(code)

    def list_templates(self) -> List[dict]:
        return list(self.templates.values())
```

The registry is used by:
- `apps.py ready()` — to log which templates are loaded on startup
- `register_workflow_templates` management command — to show what's defined locally
- NOT used by `OrchestrationClient` — the client reads the YAML indirectly via `get_workflow_stages()` on models

### `TEMPLATE_CODE_TO_WO_TYPE` Mapping

This dict in `OrchestrationClient` is what connects GRC's internal template names to WO's internal `workflow_type` field. If a new template is added:
1. Add it to `workflows.yaml`
2. Add corresponding inline stages to the model
3. Add the mapping to `TEMPLATE_CODE_TO_WO_TYPE`
4. Add handler in `_handle_workflow_event()` in `kafka_consumer.py`
5. Seed it in WO: `docker exec fims-work-orchestration-service python manage.py seed_workflow_templates`

---

## 12. GRC Kafka Consumer Container

**File:** `docker-compose.yml` — service `grc-kafka-consumer`

```yaml
grc-kafka-consumer:
  build: .
  container_name: fims-grc-kafka-consumer
  command: python manage.py consume_grc_events   # ← Django management command
  env_file: .env
  volumes:
    - ./logs:/app/logs
  depends_on:
    postgres-grc-service:
      condition: service_healthy
  networks:
    - fims-network
  restart: unless-stopped
```

**`consume_grc_events` management command** (`apps/core/management/commands/consume_grc_events.py`):
Calls `grc_kafka_consumer.consume_messages()` — an infinite loop that polls Kafka and routes messages to `_process_message()`.

**Consumer group ID:** `grc-service-consumer-group`
**`auto_offset_reset`:** `'earliest'` — replays all messages from the beginning on first connect (same cause as the duplicate permissions issue we fixed earlier)
**`consumer_timeout_ms`:** `1000` — doesn't block forever; keeps the loop responsive
**Retry logic:** Up to 10 retries with 30-second delays if Kafka connection fails

---

## 13. Complete Flow — Working Paper Example

**Scenario:** Auditor submits a working paper for approval

```
1. AUDITOR CLICKS "SUBMIT FOR REVIEW"
   Frontend: POST /api/v1/grc/working-papers/{id}/submit/
   Auth: Authorization: Bearer <auditor-jwt>

2. API VIEW (audit_working_paper_views.py)
   - Extracts user_id from request.user_id (set by JWTPermissionMiddleware)
   - Extracts auth_token from Authorization header
   - Creates WorkingPaperService()
   - Calls service.submit_for_approval(working_paper_id, submitter_id, auth_token)

3. SERVICE (working_paper_service.py)
   wp = WorkingPaper.objects.select_for_update().get(id=working_paper_id)
   if wp.workflow_plan_id: return wp   ← guard

   context = wp.get_workflow_context()
   # → {"lead_auditor": "uuid-of-auditor", "working_paper_id": "uuid"}

   metadata = wp.get_workflow_metadata()
   # → {"entity_type": "working_paper", "entity_id": "uuid",
   #    "title": "...", "entity_detail_path": "/service/grc/working-papers"}

4. ORCHESTRATION CLIENT (orchestration_client.py)
   _get_template_id_by_code("grc.working_paper_approval")
   # → queries GET http://work-orchestration-service:8004/api/v1/workflow/templates/
   # → finds workflow_type == "grc_working_paper_approval"
   # → returns UUID (cached for process lifetime)

   POST http://work-orchestration-service:8004/api/v1/workflow/plans/
   Headers: Authorization: Bearer <auditor-jwt>
   Body: {
     "template_id": "wo-template-uuid",
     "workflow_type": "grc",
     "created_by": "auditor-uuid",
     "metadata": {
       "entity_type": "working_paper",
       "entity_id": "wp-uuid",
       "context": {"lead_auditor": "auditor-uuid"},
       "subject_ref": "wp-uuid",
       "template_code": "grc.working_paper_approval",
       "entity_detail_path": "/service/grc/working-papers"
     }
   }

   WO responds 201:
   {
     "data": {
       "id": "plan-uuid",
       "status": "in_progress",
       "stages": [
         {"id": "stage1-uuid", "name": "Working Paper Review", "status": "in_progress"},
         {"id": "stage2-uuid", "name": "Working Paper Approval", "status": "pending"}
       ]
     }
   }

5. SERVICE SAVES
   wp.workflow_plan_id   = "plan-uuid"
   wp.workflow_stage     = "Working Paper Review"
   wp.workflow_stage_id  = "stage1-uuid"
   wp.workflow_started_at = now()
   wp.review_status      = "pending"
   wp.save(update_fields=[...])

6. API VIEW RETURNS 200
   {"success": true, "data": {...wp serialized...}, "workflow_plan_id": "plan-uuid"}

────── TIME PASSES — REVIEWER ACTS IN WO CONSOLE ──────

7. REVIEWER OPENS WO EMBEDDED CONSOLE (iframe in frontend)
   URL: http://wo:8004/api/v1/workflow/console/{plan-uuid}/?token={jwt}
   Clicks "Approve" on "Working Paper Approval" stage

8. WO PROCESSES ACTION
   - Updates stage status to completed
   - Since all stages done → WorkflowCompletionHandler fires
   - Publishes to Kafka topic 'workflow-events':
   {
     "event_type": "grc.workflow.completed",
     "workflow_type": "grc",
     "final_decision": "approved",
     "metadata": {
       "template_code": "grc.working_paper_approval",
       "subject_ref": "wp-uuid",
       "entity_type": "working_paper"
     }
   }

9. GRC KAFKA CONSUMER (grc-kafka-consumer container)
   _handle_workflow_event()
   → workflow_type == 'grc' ✓
   → event_type ends '.workflow.completed' ✓
   → template_code == 'grc.working_paper_approval'
   → calls _handle_working_paper_completion("wp-uuid", "approved", event_data)

   wp = WorkingPaper.objects.get(id="wp-uuid")
   wp.review_status = 'approved'
   wp.save(update_fields=['review_status'])

DONE: Working paper is now approved in GRC.
```

---

## 14. Complete Flow — Audit Engagement Lifecycle

The engagement uses **per-stage events** — GRC updates status at each phase transition, not just at the end.

```
Stages: planning → fieldwork → reporting → completed
GRC status: planning → fieldwork → reporting → completed

When WO fires 'grc.stage.completed' after "planning" stage (action: start_fieldwork):
  STAGE_STATUS_MAP[('planning', 'start_fieldwork')] = 'fieldwork'
  engagement.status = 'fieldwork'

When WO fires 'grc.stage.completed' after "fieldwork" stage (action: start_reporting):
  STAGE_STATUS_MAP[('fieldwork', 'start_reporting')] = 'reporting'
  engagement.status = 'reporting'

When WO fires 'grc.workflow.completed' (final_decision = 'approved'):
  engagement.status = 'completed'
  engagement.workflow_completed_at = now()
  engagement.actual_end_date = now().date()
```

**Special pre-condition in the view:**
```python
# engagement must have an approved audit program before lifecycle can start
has_approved_program = AuditProgram.objects.filter(
    engagement=engagement, status='approved'
).exists()
if not has_approved_program:
    return Response({"error": "...", "code": "AUDIT_PROGRAM_NOT_APPROVED"}, status=400)
```

---

## 15. Status Transitions Table (all entities)

| Entity | Before Submit | WO workflow starts | WO → approved | WO → rejected/cancelled |
|---|---|---|---|---|
| `WorkingPaper` | `review_status='draft'` | `review_status='pending'` | `review_status='approved'` | `review_status='reviewed'` |
| `AuditUniverse` | `status='draft'` | `status='under_review'` | `status='approved'`, `approved_at=now` | `status='draft'`, clears workflow fields |
| `AuditPlan` | `status='draft'` | `status='management_review'` | `status='approved'`, `committee_approved_at=now` | `status='draft'`, clears workflow fields |
| `AuditEngagement` | `status='planning'` | `status='fieldwork'` (immediately) | `status='completed'` (via per-stage events) | `status='planning'`, clears workflow |
| `AuditReport` | `status='draft'` | (set in view) | `status='approved'`, `approval_date=now`, stamps PDF, publishes finding events | `status='draft'`, clears workflow |
| `AuditMemo` | `status='draft'` | (set in view) | `status='approved'`, `dg_approval_date=now`, stamps PDF | `status='draft'`, clears workflow |
| `AuditProgram` | `status='draft'` | (set in view) | `status='approved'`, `approval_date=now`, stamps PDF | `status='draft'`, clears workflow |
| `EngagementNotification` | `status='draft'` | (set in view) | `status='approved'`, `cia_approval_date=now`, stamps PDF, notifies LA | `status='draft'`, clears workflow |

---

## 16. Key Design Decisions & Conditions

### 1. Template ID Resolution at Runtime (not hardcoded)
`_get_template_id_by_code()` queries WO at runtime so GRC never needs an environment variable for template UUIDs. The result is process-cached — only one HTTP call per container lifetime per template.

### 2. Inline Stages as Fallback
Every model implements `get_workflow_stages()`. If WO templates aren't seeded yet, GRC still sends a valid plan with inline stage definitions. This means the integration works even in a fresh environment before the WO seed command is run.

### 3. `subject_ref` is the GRC Entity UUID
The `subject_ref` field sent in the metadata is how the Kafka consumer finds the right GRC record when WO fires the completion event. **If this is missing from the metadata, the completion handler logs a warning and does nothing.**

### 4. `template_code` in Metadata is the Router
`template_code` (e.g. `"grc.working_paper_approval"`) is embedded in `metadata.template_code`. The Kafka consumer reads this to route to the correct `_handle_*_completion()` method. Without it, the event falls through to the `else: logger.warning(...)` branch.

### 5. `select_for_update()` Prevents Double Submission
Since `submit_for_approval()` is wrapped in `@transaction.atomic` and uses `select_for_update()`, concurrent requests for the same entity will queue at the DB, and the second one will find `workflow_plan_id` already set and return early. Prevents creating two WO plans for one GRC entity.

### 6. Auth Token Forwarding
The user's JWT is extracted from `HTTP_AUTHORIZATION` in the view and passed through to `OrchestrationClient.start_workflow()`. WO uses it to record `created_by` as the actual user (not the service account). Without this, WO would authenticate via `X-Service-Token` and record `created_by: 'service@internal'`.

### 7. Engagement Status Set Immediately (Optimistic)
`AuditEngagementService.start_workflow()` immediately sets `status='fieldwork'` when the WO plan is created — it doesn't wait for the Kafka stage event. This is an **optimistic update for UX**. The Kafka consumer's stage event logic would also set `fieldwork`, but the service does it immediately so the frontend sees the change right away.

### 8. GAP 9 — PDF Stamping on Approval
For `AuditReport`, `AuditMemo`, `AuditProgram`, and `EngagementNotification`, approval triggers a call to Document Records Service to overlay a CIA signature and QR code on the approved PDF. This is **best-effort** — errors are logged but do not prevent the approval from completing.

### 9. Consumer `auto_offset_reset='earliest'`
The consumer replays all messages from the beginning on first start. This means if GRC is restarted and WO already fired completion events, GRC will re-process them. All handlers are **idempotent** — calling them twice with the same `final_decision` sets the same status again, no harm done.

---

## 17. What Triggers What — Quick Reference

```
USER ACTION       →  GRC ENDPOINT                              →  SERVICE METHOD                           →  WO API CALL
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Submit WP         →  /working-papers/submit/                   →  WorkingPaperService.submit_for_approval   →  POST /plans/
Submit Universe   →  /audit-universe/submit-for-review/        →  AuditUniverseService.submit_for_approval  →  POST /plans/
Submit RBIAP      →  /audit-plans/submit-for-approval/         →  AuditPlanService.submit_for_approval      →  POST /plans/
Start Engagement  →  /engagements/start-workflow/              →  AuditEngagementService.start_workflow     →  POST /plans/
Submit Report     →  /audit-reports/...                        →  (inline in view)                          →  POST /plans/
Submit Memo       →  /audit-memos/submit-for-approval/         →  (inline in view)                          →  POST /plans/
Submit Program    →  /audit-programs/submit-for-approval/      →  (inline in view)                          →  POST /plans/
Submit EN         →  /engagement-notifications/submit/         →  EngagementNotificationService.submit      →  POST /plans/

WO EVENT               →  KAFKA TOPIC      →  GRC CONSUMER METHOD                              →  GRC DB CHANGE
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
grc.workflow.completed →  workflow-events  →  _handle_working_paper_completion                  →  review_status=approved/reviewed
grc.workflow.completed →  workflow-events  →  _handle_audit_universe_completion                 →  status=approved + notify
grc.workflow.completed →  workflow-events  →  _handle_audit_plan_completion                     →  status=approved + domain event
grc.stage.completed    →  workflow-events  →  _handle_audit_engagement_stage                    →  status=fieldwork/reporting
grc.workflow.completed →  workflow-events  →  _handle_audit_engagement_stage                    →  status=completed
grc.workflow.completed →  workflow-events  →  _handle_audit_report_completion                   →  status=approved + stamp + finding events
grc.workflow.completed →  workflow-events  →  _handle_audit_memo_completion                     →  status=approved + stamp
grc.workflow.completed →  workflow-events  →  _handle_audit_program_completion                  →  status=approved + stamp
grc.workflow.completed →  workflow-events  →  _handle_engagement_notification_completion        →  status=approved + stamp + notify
```

---

*Created: 2026-03-11. Derived from code analysis of the actual GRC service implementation.*
*Files in: `grc-service/apps/core/`, `grc-service/apps/infrastructure/`, `grc-service/apps/api/views/`*
