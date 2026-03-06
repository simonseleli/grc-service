# Work Orchestration Service — Deep Architectural Reference

> **Service:** work-orchestration-service  
> **Port:** 8004  
> **Database:** `workflow_orchestration_db` on `postgres-work-orchestration-service` (PostgreSQL 15)  
> **Cache / Broker:** `redis-work-orchestration-service:6379/2`  
> **Container:** `fims-work-orchestration-service`  
> **Gateway Routes:** `/api/v1/work-orchestration/*`

---

## Table of Contents

1. [Primary Responsibilities & Domain Ownership](#1-primary-responsibilities--domain-ownership)
2. [Capabilities Exposed to Other Services](#2-capabilities-exposed-to-other-services)
3. [Exclusive Ownership vs. Delegation](#3-exclusive-ownership-vs-delegation)
4. [Architecture — Clean Architecture Layers](#4-architecture--clean-architecture-layers)
5. [Data Model Reference](#5-data-model-reference)
6. [Complete API Surface](#6-complete-api-surface)
7. [Workflow Plan Lifecycle](#7-workflow-plan-lifecycle)
8. [Stage Execution & Sequential Enforcement](#8-stage-execution--sequential-enforcement)
9. [Automation Engine](#9-automation-engine)
10. [Notification Delivery System](#10-notification-delivery-system)
11. [Kafka Event Architecture](#11-kafka-event-architecture)
12. [Cross-Service Dependencies](#12-cross-service-dependencies)
13. [Background Tasks (Celery)](#13-background-tasks-celery)
14. [Permission Registration](#14-permission-registration)
15. [How Other Services Consume Work Orchestration](#15-how-other-services-consume-work-orchestration)
16. [Integration Guide for New Services](#16-integration-guide-for-new-services)
17. [Architectural Boundaries — What Not To Do](#17-architectural-boundaries--what-not-to-do)

---

## 1. Primary Responsibilities & Domain Ownership

The work-orchestration-service is the **central workflow engine** for the entire FIMS platform. It manages the lifecycle of any multi-step, multi-actor approval or task-based process. It does **not** know about domain-specific business rules (documents, compliance, HR) — it only understands plans, stages, actions, tasks, and notifications.

### 1.1 Workflow Plan Management
- Create, read, update, and cancel workflow plans
- Template-based plan creation (workflow templates with predefined stage definitions)
- Sequential stage execution enforcement
- SLA tracking with due-date calculation per stage
- Plan metadata enrichment (tags, arbitrary JSON metadata)
- Plan versioning and contract versioning
- Plan activity audit trail (immutable event log)

### 1.2 Stage Orchestration
- Stage lifecycle: `pending` → `assigned` → `in_progress` → `completed` / `rejected` / `cancelled`
- Action-based progression (each stage defines configurable button/actions)
- Assignee management per stage (user UUIDs)
- Form schema support (stages can declare form schemas for data collection)
- SLA with target hours + grace hours → automatic due-date calculation
- Auto-advance: completing one stage automatically activates the next pending stage
- Quorum-based voting for commission/management workflows

### 1.3 Task Management
- Workflow-bound tasks (linked to a plan and optionally a stage)
- Standalone tasks (independent tasks, not tied to any workflow)
- Task types (configurable catalog: `TaskTypeModel`)
- Task queues (configurable routing catalog: `TaskQueueModel`)
- Task priorities: low, medium, high, urgent
- Task status machine: `pending` → `assigned` → `in_progress` → `review` → `completed` (also: `on_hold`, `overdue`, `blocked`, `cancelled`)
- Task assignment and reassignment
- Time tracking: estimated vs actual hours, timesheets per task
- Task comments (threaded discussion per task)
- Task collaborators with roles (viewer, editor, reviewer) and invitation workflow

### 1.4 Notification Delivery Engine
- Multi-channel notification delivery: email (SMTP), SMS (Infobip), in-app, webhook
- Notification template system with `{{placeholder}}` rendering
- Template registration via Kafka (other services publish their templates)
- Priority-based Kafka topic routing (urgent, high, normal, low)
- Dead Letter Queue (DLQ) for failed notifications
- In-app notification store with read/unread tracking
- Notification batching for efficiency
- Delivery logging and usage statistics per template

### 1.5 Reminder System
- Scheduled reminders for tasks and workflow plans
- Multi-channel delivery (email, SMS, in-app, webhook)
- Recurrence support (configurable frequency and max occurrences)
- Snooze support (with max snooze limits)
- Escalation policies (time-based or retry-based escalation)
- Retry with exponential backoff (configurable backoff seconds)
- User channel preference integration (respects IAM notification preferences)

### 1.6 Notification Settings Management
- Admin-configurable SMTP settings (stored in database, overrides env vars)
- Admin-configurable SMS provider settings (Infobip integration)
- SMTP connection testing endpoint
- SMS connection testing endpoint
- Singleton settings pattern (only one NotificationSettings row)

### 1.7 Analytics & Reporting
- Workflow statistics dashboard (counts by status)
- Overdue task listing
- Task queue summary (tasks per queue)
- Stage analytics (duration, bottleneck detection)
- Vetting report data aggregation (approval workflow analytics)
- Task report data aggregation (task completion metrics)

---

## 2. Capabilities Exposed to Other Services

### 2.1 Workflow Plan REST API (Primary Integration Point)

This is how document-records-service, GRC, and other services create and manage workflows:

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /plans/` | POST | Create a workflow plan (with stages, tasks, metadata) |
| `GET /plans/<uuid>/` | GET | Get plan details with all stages |
| `PATCH /plans/<uuid>/` | PATCH | Update plan metadata/status |
| `POST /plans/<uuid>/stages/<uuid>/actions/` | POST | Execute action on a stage (approve, reject, etc.) |
| `PATCH /plans/<uuid>/stages/<uuid>/` | PATCH | Update stage (SLA, assignees, metadata, status) |
| `GET /plans/<uuid>/activity/` | GET | Get plan activity audit trail |
| `GET /plans/<uuid>/console/` | GET | Get plan console view (embeddable UI data) |

### 2.2 Workflow Template API

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /templates/` | GET | List available workflow templates |
| `POST /templates/` | POST | Create a workflow template |
| `GET /templates/<uuid>/` | GET | Template detail with stage definitions |
| `PUT /templates/<uuid>/` | PUT | Update template |

### 2.3 Task API

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /tasks/` | GET | List tasks (filterable by status, assignee, queue) |
| `GET /plans/<uuid>/tasks/<uuid>/` | GET | Task detail within a plan |
| `POST /standalone-tasks/` | POST | Create a standalone task |
| `GET /standalone-tasks/<uuid>/` | GET | Standalone task detail |

### 2.4 Notification Template API

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /notifications/templates/` | GET | List notification templates |
| `POST /notifications/templates/` | POST | Create notification template |
| `GET /notifications/templates/<uuid>/` | GET | Template detail |
| `PUT /notifications/templates/<uuid>/` | PUT | Update template |

### 2.5 Kafka Event Streams (Outbound)

| Topic | Events Published | Consumers |
|---|---|---|
| `workflow-events` | `WorkflowStarted`, `WorkflowStageUpdated`, `WorkflowCompleted`, `{type}.workflow.completed` | document-records-service, grc-service (any service with orchestration integration) |

### 2.6 Kafka Topic Consumption (Inbound)

| Topic | Purpose | Publisher |
|---|---|---|
| `notification-templates` | Template registration from services | All services |
| `notifications-urgent` | Urgent notification delivery requests | All services |
| `notifications-high` | High-priority notifications | All services |
| `notifications-normal` | Normal-priority notifications | All services |
| `notifications-low` | Low-priority notifications | All services |
| `notifications` | Default/fallback notification topic | All services (backward compat) |

---

## 3. Exclusive Ownership vs. Delegation

### 3.1 What Work Orchestration Owns Exclusively

| Capability | Why |
|---|---|
| **Workflow plan state** | Plans, stages, and their statuses are exclusively managed here |
| **Stage execution logic** | Sequential enforcement, auto-advance, quorum checking |
| **Workflow templates** | Reusable workflow definitions live here |
| **Task management** | All task creation, assignment, status tracking, timesheets |
| **Notification delivery** | The only service that actually sends emails, SMS, in-app messages |
| **Notification templates** | Central template store — other services register, this service stores/renders |
| **Reminder scheduling** | All reminder creation, delivery, escalation, recurrence |
| **Workflow activity log** | Immutable audit trail for all workflow events |
| **In-app notification store** | The `notifications` table is the source of truth for user notifications |
| **Notification settings** | SMTP and SMS provider configuration |

### 3.2 What Work Orchestration Delegates

| Capability | Delegated To | Mechanism |
|---|---|---|
| **User authentication** | iam-service | JWT validation via shared secret (JWTPermissionMiddleware) |
| **User notification preferences** | iam-service | REST call via `IAMPreferenceClient` with 5-min Redis cache |
| **Business rule validation** | Calling service | E.g., document-records validates approval thresholds |
| **Domain-specific metadata** | Calling service | Services embed their context in plan/stage metadata |
| **Permission registration** | iam-service | Kafka to `service.permission.registry` topic |

### 3.3 What Other Services Delegate to Work Orchestration

| Service | What It Delegates | How |
|---|---|---|
| document-records-service | Document approval workflows, disposal workflows | REST via `WorkOrchestrationClient` |
| grc-service | Compliance review and audit workflows | REST API calls |
| iam-service | N/A (no workflows yet) | — |
| All services | Notification delivery | Kafka to priority notification topics |
| All services | Notification template registration | Kafka to `notification-templates` topic |

---

## 4. Architecture — Clean Architecture Layers

```
┌────────────────────────────────────────────────────────────────────┐
│  apps/api/                                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Views (APIView), Serializers, URL routing                    │  │
│  │ Permission enforcement (IsJWTAuthenticated, role-based)      │  │
│  └─────────────────────────┬────────────────────────────────────┘  │
│                            │ calls                                  │
│  apps/core/                ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ use_cases/       — Command/Query pattern for all operations  │  │
│  │ entities/        — Pure domain dataclasses (no Django deps)  │  │
│  │ repositories/    — Abstract repository interface             │  │
│  │ services/        — Domain services (notifications, reports)  │  │
│  │ automation/      — Workflow automation engine                 │  │
│  │ consumers/       — Kafka consumers (notifications, templates)│  │
│  │ permissions.py   — Permission registry from JSON config      │  │
│  │ tasks.py         — Celery task definitions                   │  │
│  └─────────────────────────┬────────────────────────────────────┘  │
│                            │ uses interfaces                        │
│  apps/infrastructure/      ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ persistence/     — DjangoWorkflowRepository (ORM impl)       │  │
│  │ messaging/       — KafkaEventDispatcher, KafkaEventConsumer  │  │
│  │ events/          — Event dispatcher abstractions              │  │
│  │ notifications/   — Channel implementations (email, SMS, etc) │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### 4.1 Domain Entities (apps/core/entities/)

Pure Python dataclasses — no Django dependencies:

| Entity | Purpose |
|---|---|
| `WorkflowPlan` | Top-level workflow with plan_id, workflow_type, status, stages[], tasks[] |
| `StageDefinition` | Stage with definition_key, order, status, assignees[], actions[], form_schema, SLA |
| `StageAction` | Button/action within a stage: name, label, next_state, metadata |
| `Task` | Atomic work unit: external_id, title, task_type, queue, priority, assignee, timesheets[] |
| `TaskTimesheetEntry` | Time logging: started_at, ended_at, hours, notes |
| `Reminder` | Scheduled notification: channel, due_at, recurrence, escalation_policy |
| `WorkflowTemplate` | Reusable plan definition: workflow_type, version, definition JSON |
| `NotificationTemplate` | Template: code, channels, subject, body, priority, recipient_groups |
| `TaskComment` | Comment on task: external_id, content, author_id |
| `TaskCollaborator` | Collaborator: role (viewer/editor/reviewer), status (pending/accepted/declined) |

### 4.2 Use Cases (apps/core/use_cases/)

All operations follow the **Command/Query + Use Case** pattern:

| Use Case | Command/Query | Description |
|---|---|---|
| `CreateWorkflowPlanUseCase` | `CreateWorkflowPlanCommand` | Creates plan from stages or template, publishes `WorkflowStarted` |
| `AdvanceStageUseCase` | `AdvanceStageCommand` | Executes action on stage, enforces sequential rules, auto-advances |
| `UpdateStageUseCase` | `UpdateStageCommand` | Updates stage SLA, assignees, metadata, recalculates due_at |
| `ScheduleReminderUseCase` | `ScheduleReminderCommand` | Creates a reminder with channel/recurrence/escalation |
| `ListRemindersUseCase` | `ListRemindersQuery` | Lists reminders for a plan/task |
| `ListTasksUseCase` | `ListTasksQuery` | Lists tasks with filtering |
| `GetTaskUseCase` | `GetTaskQuery` | Gets task with enrichment |
| `CreateTaskUseCase` | `CreateTaskCommand` | Creates a task within a plan or standalone |
| `UpdateTaskUseCase` | `UpdateTaskCommand` | Updates task status, assignee, priority |
| `GetStandaloneTaskUseCase` | `GetStandaloneTaskQuery` | Gets standalone task detail |
| `ListActivityUseCase` | `ListActivityQuery` | Audit trail for a plan |
| `GetWorkflowStatsUseCase` | — | Aggregate workflow statistics |
| `ListOverdueTasksUseCase` | `OverdueTasksQuery` | Lists overdue tasks |
| `GetTaskQueueSummaryUseCase` | `TaskQueueSummaryQuery` | Queue-level task distribution |
| `GetStageAnalyticsUseCase` | — | Stage duration/bottleneck analytics |
| `WorkflowTemplateUseCase(s)` | — | CRUD for workflow templates |
| `NotificationTemplateUseCase(s)` | — | CRUD for notification templates |
| `CollaboratorUseCase(s)` | — | Manage task collaborators |
| `CommentUseCase(s)` | — | Manage task comments |
| `TimesheetUseCase(s)` | — | Log and list time entries |
| `VettingReportUseCase(s)` | — | Vetting workflow report generation |
| `TaskReportUseCase(s)` | — | Task analytics report generation |

### 4.3 Repository Pattern

Single repository interface: `WorkflowRepository` (protocol)

Implementation: `DjangoWorkflowRepository` in `apps/infrastructure/persistence/workflow_repository.py`

Methods include:
- `create_plan`, `get_plan`, `save_plan`, `list_plans`
- `update_stage`, `get_stage`
- `create_task`, `get_task`, `update_task`, `list_tasks`
- `create_reminder`, `update_reminder`, `list_reminders`, `get_due_reminders`
- `get_template`, `list_templates`, `save_template`
- `record_activity`, `list_activity`
- `list_notification_templates`, `get_notification_template`

---

## 5. Data Model Reference

### 5.1 WorkflowPlanModel

```
Table: workflow_plans
PK: id (UUIDField)
Indexes: workflow_type, status
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `workflow_type` | CharField(100) | e.g., `approval`, `disposal`, `commission`, `management`, `custom` |
| `status` | CharField(32) | `draft`, `active`, `completed`, `rejected`, `cancelled`, `failed` |
| `version` | PositiveIntegerField | Default: 1 |
| `contract_version` | CharField(20) | Default: `1.0.0` |
| `created_by` | UUIDField | IAM user ID |
| `metadata` | JSONField | Arbitrary context from calling service |
| `tags` | JSONField | List of string tags |
| `sla` | JSONField | Plan-level SLA configuration |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

### 5.2 WorkflowStageModel

```
Table: workflow_stages
PK: id (UUIDField)
Index: (plan, status), definition_key
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `plan` | FK(WorkflowPlanModel) | CASCADE |
| `definition_key` | CharField(100) | Template stage identifier (e.g., `management_review`, `dg_approval`) |
| `name` | CharField(120) | Display name |
| `status` | CharField(32) | `pending`, `assigned`, `in_progress`, `completed`, `rejected`, `cancelled` |
| `order` | PositiveIntegerField | Execution order (sequential) |
| `assignees` | JSONField | List of user UUIDs assigned to this stage |
| `form_schema` | JSONField | Dynamic form definition for data collection |
| `actions` | JSONField | List of `{name, label, next_state, metadata}` action definitions |
| `due_at` | DateTimeField | Calculated from SLA target + grace hours |
| `metadata` | JSONField | Stage-specific context (quorum settings, automation config, form_data) |
| `sla` | JSONField | `{targetHours, graceHours}` |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

### 5.3 WorkflowTaskModel

```
Table: workflow_tasks
PK: id (UUIDField)
Indexes: (plan, status), (assignee, status), task_type, (queue, status)
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `plan` | FK(WorkflowPlanModel) | CASCADE, nullable (standalone tasks) |
| `stage` | FK(WorkflowStageModel) | SET_NULL, nullable |
| `title` | CharField(200) | |
| `task_type` | CharField(100) | Configurable (linked to `TaskTypeModel`) |
| `queue` | CharField(64) | Default: `default` |
| `status` | CharField(32) | `pending`, `assigned`, `in_progress`, `review`, `on_hold`, `overdue`, `blocked`, `completed`, `cancelled` |
| `priority` | CharField(16) | `low`, `medium`, `high`, `urgent` |
| `assignee` | UUIDField | IAM user ID |
| `created_by` | UUIDField | |
| `description` | TextField | |
| `due_at` | DateTimeField | |
| `completed_at` | DateTimeField | |
| `related_entity` | JSONField | Generic reference: `{type: "document", id: "uuid"}` |
| `context` | JSONField | Additional context data |
| `estimated_hours` | DecimalField(7,2) | |
| `actual_hours` | DecimalField(7,2) | |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

### 5.4 WorkflowTemplateModel

```
Table: workflow_templates
PK: id (UUIDField)
Unique: (workflow_type, version)
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | CharField(150) | |
| `workflow_type` | CharField(100) | e.g., `approval`, `disposal` |
| `version` | PositiveIntegerField | |
| `is_active` | BooleanField | |
| `definition` | JSONField | `{stages: [{definition_key, name, actions, metadata, form_schema, sla}]}` |
| `created_by` | UUIDField | |

### 5.5 NotificationTemplateModel

```
Table: notification_templates
PK: id (UUIDField)
Unique: (code, version)
Indexes: status, category, code
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `code` | CharField(200) | Unique template code (e.g., `iam.user.registration`, `document.approval.request`) |
| `version` | PositiveIntegerField | Auto-incremented on re-registration |
| `name` | CharField(150) | |
| `description` | TextField | |
| `category` | CharField(120) | e.g., `authentication`, `document`, `task` |
| `channels` | JSONField | `["email", "in_app", "sms"]` |
| `priority` | CharField(16) | `urgent`, `high`, `normal`, `low` |
| `status` | CharField(16) | `draft`, `active`, `archived` |
| `subject` | CharField(200) | Email subject with `{{placeholders}}` |
| `body` | TextField | HTML body with `{{placeholders}}` and `{% if var %}...{% endif %}` |
| `triggered_by` | JSONField | List of event types that trigger this template |
| `recipient_groups` | JSONField | |
| `scheduled_delivery` | BooleanField | |
| `retry_policy` | JSONField | Retry configuration |
| `metadata` | JSONField | Source service info, variables, body_text for SMS |
| `created_by` | UUIDField | |

### 5.6 NotificationModel (In-App Notifications)

```
Table: notifications
PK: id (UUIDField)
Indexes: (user_id, read), (user_id, -created_at), category
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUIDField | IAM user ID (NOT NULL) |
| `title` | CharField(200) | |
| `message` | TextField | |
| `link` | CharField(500) | Deep link to relevant page |
| `read` | BooleanField | Default: False |
| `read_at` | DateTimeField | |
| `priority` | CharField(16) | `urgent`, `high`, `normal`, `low` |
| `category` | CharField(120) | e.g., `task`, `workflow`, `reminder` |
| `metadata` | JSONField | |

### 5.7 ReminderModel

```
Table: workflow_reminders
PK: id (UUIDField)
Indexes: (status, due_at), (channel, status)
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `plan` | FK(WorkflowPlanModel) | Nullable |
| `task` | FK(WorkflowTaskModel) | Nullable |
| `title` | CharField(200) | |
| `message` | TextField | |
| `channel` | CharField(16) | `email`, `sms`, `in_app`, `webhook` |
| `status` | CharField(16) | `pending`, `sent`, `cancelled`, `failed` |
| `target_user_id` | UUIDField | |
| `due_at` | DateTimeField | When to fire |
| `retry_count` | PositiveIntegerField | |
| `max_retries` | PositiveIntegerField | Default: 3 |
| `recurrence` | JSONField | `{frequency: "daily", interval: 1}` |
| `recurrence_count` | PositiveIntegerField | |
| `max_occurrences` | PositiveIntegerField | |
| `snooze_until` | DateTimeField | |
| `snooze_count` | PositiveIntegerField | |
| `max_snoozes` | PositiveIntegerField | |
| `escalation_policy` | JSONField | `{afterMinutes: 30, channel: "email", targetUserId: "uuid"}` |
| `escalated_at` | DateTimeField | |
| `sent_at` | DateTimeField | |
| `metadata` | JSONField | |
| `last_error` | TextField | |

### 5.8 Supporting Models

| Model | Table | Purpose |
|---|---|---|
| `TaskTypeModel` | `workflow_task_types` | Configurable task type catalog (code, name, metadata) |
| `TaskQueueModel` | `workflow_task_queues` | Configurable task queue catalog |
| `TaskTimesheetEntryModel` | `workflow_task_timesheets` | Time entries per task |
| `TaskCommentModel` | `workflow_task_comments` | Comments with external_id dedup |
| `TaskCollaboratorModel` | `workflow_task_collaborators` | Collaborators: role + invitation status |
| `WorkflowActivityModel` | `workflow_activity` | Immutable audit log for plan events |
| `NotificationTemplateVersion` | `notification_template_versions` | Version history for templates |
| `NotificationDeliveryLog` | `notification_delivery_logs` | Delivery attempts and results per channel |
| `NotificationTemplateUsage` | `notification_template_usage` | Daily aggregated usage stats per template |
| `NotificationSettings` | `notification_settings` | Singleton: SMTP + SMS provider config |

---

## 6. Complete API Surface

All endpoints are under the base path (via gateway: `/api/v1/work-orchestration/`).

### 6.1 Workflow Plans

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/plans/` | GET | Bearer | List workflow plans |
| `/plans/` | POST | Bearer + `workflow:plan:create` | Create workflow plan (from stages or template) |
| `/plans/<uuid>/` | GET | Bearer + `workflow:plan:read` | Plan detail with all stages |
| `/plans/<uuid>/` | PATCH | Bearer + `workflow:plan:update` | Update plan metadata/status/tags |
| `/plans/<uuid>/stages/<uuid>/actions/` | POST | Bearer + `workflow:stage:action` | Execute action on stage (approve, reject, etc.) |
| `/plans/<uuid>/stages/<uuid>/` | GET | Bearer | Stage detail |
| `/plans/<uuid>/stages/<uuid>/` | PATCH | Bearer + `workflow:stage:assign` | Update stage SLA, assignees, metadata |
| `/plans/<uuid>/activity/` | GET | Bearer + `workflow:activity:audit` | Plan activity audit trail |
| `/plans/<uuid>/console/` | GET | Bearer + `workflow:console:embed` | Embeddable console view |

### 6.2 Tasks (Workflow-bound and Standalone)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/tasks/` | GET | Bearer + `workflow:task:read` | List all tasks (filter by status, assignee, queue) |
| `/plans/<uuid>/tasks/<uuid>/` | GET | Bearer | Task detail within plan |
| `/plans/<uuid>/tasks/<uuid>/` | PATCH | Bearer + `workflow:task:update` | Update task |
| `/plans/<uuid>/tasks/<uuid>/timesheets/` | GET/POST | Bearer + `workflow:timesheet:log` | Timesheet entries for plan task |
| `/standalone-tasks/` | GET | Bearer | List standalone tasks |
| `/standalone-tasks/` | POST | Bearer + `workflow:task:create` | Create standalone task |
| `/standalone-tasks/<uuid>/` | GET | Bearer | Standalone task detail |
| `/standalone-tasks/<uuid>/` | PATCH | Bearer + `workflow:task:update` | Update standalone task |
| `/standalone-tasks/<uuid>/timesheets/` | GET/POST | Bearer + `workflow:timesheet:log` | Timesheet entries for standalone task |

### 6.3 Task Comments & Collaborators

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/tasks/<uuid>/comments/` | GET/POST | Bearer | List/create comments on task |
| `/tasks/<uuid>/comments/<id>/` | GET/PATCH/DELETE | Bearer | Manage specific comment |
| `/tasks/<uuid>/collaborators/` | GET/POST | Bearer | List/add collaborators |
| `/tasks/<uuid>/collaborators/<id>/` | GET/PATCH/DELETE | Bearer | Manage specific collaborator |
| `/invitations/` | GET | Bearer | List invitations for current user |

### 6.4 Workflow Templates

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/templates/` | GET | Bearer | List workflow templates |
| `/templates/` | POST | Bearer + `workflow:template:create` | Create template |
| `/templates/<uuid>/` | GET | Bearer | Template detail |
| `/templates/<uuid>/` | PUT | Bearer + `workflow:template:update` | Update template |

### 6.5 Reminders

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/reminders/` | GET/POST | Bearer + `workflow:reminder:create` | List/create reminders |

### 6.6 Notifications

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/notifications/` | GET | Bearer | List notifications for current user |
| `/notifications/<uuid>/` | GET/PATCH | Bearer | Get/mark notification (read, etc.) |
| `/notifications/stats/` | GET | Bearer | Notification read/unread counts |
| `/notifications/email/send/` | POST | Bearer | Send email notification directly |
| `/notifications/templates/` | GET/POST | Bearer + `workflow:notification_template:manage` | List/create notification templates |
| `/notifications/templates/<uuid>/` | GET/PUT/DELETE | Bearer | Manage notification template |

### 6.7 Notification Settings

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/settings/notifications/` | GET/PUT | Bearer + Admin | Get/update SMTP and SMS settings |
| `/settings/notifications/test-smtp/` | POST | Bearer + Admin | Test SMTP connection |
| `/settings/notifications/test-sms/` | POST | Bearer + Admin | Test SMS connection |

### 6.8 Analytics

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/analytics/stats/` | GET | Bearer + `workflow:analytics:view` | Workflow/task aggregate stats |
| `/analytics/tasks/overdue/` | GET | Bearer + `workflow:analytics:view` | List overdue tasks |
| `/analytics/queues/` | GET | Bearer + `workflow:analytics:view` | Task queue distribution |
| `/analytics/stages/` | GET | Bearer + `workflow:analytics:view` | Stage duration analytics |

### 6.9 Reports

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/reports/vetting/` | GET | Bearer | Vetting workflow report |
| `/reports/tasks/` | GET | Bearer | Task analytics report |

### 6.10 Task Types & Queues

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/task-types/` | GET/POST | Bearer | List/create task types |
| `/task-types/<uuid>/` | GET/PATCH/DELETE | Bearer | Manage task type |
| `/task-queues/` | GET/POST | Bearer | List/create task queues |
| `/task-queues/<uuid>/` | GET/PATCH/DELETE | Bearer | Manage task queue |

### 6.11 Health

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health/` | GET | Public | Service health check |

---

## 7. Workflow Plan Lifecycle

### 7.1 Plan Status Machine

```
┌─────────────┐
│   draft     │ ── (plan created without template activation)
└──────┬──────┘
       │ activate (automatic when stages provided)
       ▼
┌─────────────┐
│   active    │ ── (stages being executed sequentially)
└──────┬──────┘
       │
   ┌───┴──────────────────────┐
   │                          │
   ▼                          ▼
┌─────────────┐        ┌─────────────┐
│ completed   │        │  cancelled  │
│ (all stages │        │  (manual    │
│  resolved)  │        │   cancel)   │
└─────────────┘        └─────────────┘
       │
       │ rejected (if any stage rejected)
       ▼
┌─────────────┐
│  rejected   │
└─────────────┘
```

### 7.2 Plan Creation Flow

1. Calling service sends `POST /plans/` with stages definitions (or `template_id`)
2. `CreateWorkflowPlanUseCase` generates UUID for plan and each stage
3. If `template_id` provided, stages are inflated from `WorkflowTemplateModel.definition`
4. Plan metadata from caller is merged into stage metadata (quorum, participants, etc.)
5. First stage set to `in_progress`, all subsequent stages set to `pending`
6. SLA due dates calculated cumulatively: stage N due_at = plan.created_at + Σ(targetHours + graceHours) for stages 0..N
7. Plan saved to DB, `WorkflowStarted` event dispatched to Kafka
8. Activity log entry recorded
9. For commission workflows: notification sent to commission members

---

## 8. Stage Execution & Sequential Enforcement

### 8.1 Sequential Rules

The service enforces **strict sequential stage execution**:

1. **Workflow must be active** — cannot act on completed/cancelled/rejected plans
2. **Stage must be `in_progress`** — only the currently active stage accepts actions
3. **User deduplication** — each user can only act once per stage (checked via activity log)
4. **Earlier stages must be complete** — cannot skip ahead to a later stage

### 8.2 Action Execution Flow

```
Client                           Work Orchestration
  │                                      │
  │ POST /plans/{id}/stages/{id}/actions/│
  │  { action: "approve",               │
  │    actor_id: "uuid",                 │
  │    form_data: { vote: "approved" } } │
  │─────────────────────────────────────>│
  │                                      │
  │    1. Load plan + stage              │
  │    2. Validate sequential rules      │
  │    3. Find action definition         │
  │    4. Merge metadata + form_data     │
  │    5. For voting workflows:          │
  │       keep in_progress until         │
  │       quorum met                     │
  │    6. Update stage status            │
  │    7. If completed → activate next   │
  │       pending stage                  │
  │    8. If ALL stages complete →       │
  │       mark plan completed            │
  │    9. Dispatch WorkflowStageUpdated  │
  │   10. Dispatch WorkflowCompleted     │
  │       (if plan done)                 │
  │   11. Record activity entries        │
  │                                      │
  │  { plan: {...}, stage: {...} }       │
  │<─────────────────────────────────────│
```

### 8.3 Auto-Advance Mechanism

When a stage transitions to `completed`:
1. Stages sorted by `order`
2. Find next stage with `pending` status
3. Update that stage to `in_progress`
4. For commission workflows: send poll notification to new stage assignees

### 8.4 Quorum-Based Voting (Commission/Management)

For `commission` and `management` workflow types:
- Stage metadata contains: `minimum_voters`, `quorum_percentage`, `assigned_participants`
- When each voter acts, action executes but stage stays `in_progress`
- The calling service (document-records) is responsible for checking if quorum is met
- Stage only transitions to `completed` when the calling service explicitly completes it

---

## 9. Automation Engine

The `WorkflowAutomationEngine` processes workflow events and triggers automated actions.

### 9.1 Architecture

```
Kafka topic: workflow-events
       │
       ▼
Celery task: process_workflow_events (every 30s)
       │
       ▼
WorkflowAutomationEngine.process(event)
       │
       ├── _handle_WorkflowStageUpdated
       │       ├── _maybe_auto_advance     → Auto-advance to next stage
       │       ├── _maybe_schedule_escalation → Schedule escalation reminder
       │       └── _maybe_trigger_webhooks  → POST to external webhook URLs
       │
       └── (extensible for future event types)
```

### 9.2 Automation Configuration (Stage Metadata)

Automation is configured via stage metadata under the `automation` key:

```json
{
  "automation": {
    "autoAdvance": {
      "onStatuses": ["completed"],
      "action": "approve",
      "stageDefinition": "next_stage_key",
      "actorId": "automation-bot",
      "comment": "Auto-approved"
    },
    "escalationReminder": {
      "onStatuses": ["blocked", "pending"],
      "offsetMinutes": 30,
      "channel": "email",
      "targetUserId": "supervisor-uuid",
      "maxRetries": 3
    },
    "webhooks": [
      {
        "events": ["WorkflowStageUpdated"],
        "url": "https://external-system.example.com/webhook",
        "timeout": 5
      }
    ]
  }
}
```

### 9.3 Auto-Advance Logic
1. When a stage updates, check `automation.autoAdvance` config
2. If `newStatus` matches `onStatuses`, resolve the target stage
3. Resolution order: explicit `stageId` → `stageDefinition` key lookup → next stage by order
4. Execute the configured action on the target stage as `automation-bot`

### 9.4 Escalation Reminders
1. When a stage enters `blocked` or `pending`, check `escalationReminder` config
2. Schedule a reminder due in `offsetMinutes` from now
3. Target the configured user (or first assignee if not specified)

---

## 10. Notification Delivery System

### 10.1 Multi-Channel Architecture

```
┌───────────────────────────────────────────────────────────────┐
│  Service publishes to Kafka priority topics                    │
│  (notifications-urgent, -high, -normal, -low)                  │
│                                                                │
│  Event format:                                                 │
│  {                                                             │
│    "notification": {                                           │
│      "template_code": "document.approval.request",             │
│      "recipients": { "user_ids": [...], "email": [...] },      │
│      "context": { "user": {"first_name": "John"}, ... },      │
│      "metadata": { "priority": "high" }                       │
│    },                                                          │
│    "source_service": "document-records-service"                │
│  }                                                             │
└───────────────────────┬───────────────────────────────────────┘
                        │ Consumed every 5 seconds
                        ▼
┌───────────────────────────────────────────────────────────────┐
│  NotificationConsumer                                          │
│  ┌─────────────┐   ┌───────────────┐   ┌─────────────────┐   │
│  │ Look up     │──>│ Render with   │──>│ Send via        │   │
│  │ template    │   │ TemplateRenderer│   │ channels:      │   │
│  │ by code     │   │ {{placeholders}}│   │ • EmailChannel │   │
│  │             │   │ {% if %}        │   │ • SmsChannel   │   │
│  └─────────────┘   └───────────────┘   │ • InAppChannel  │   │
│                                         └─────────────────┘   │
│                                                                │
│  On failure → Dead Letter Queue (notification-failed)          │
│  On success → NotificationDeliveryLog, NotificationTemplateUsage│
└───────────────────────────────────────────────────────────────┘
```

### 10.2 Template Registration Flow

Other services register their notification templates via Kafka:

```
Service publishes to: notification-templates
{
  "event_type": "template.registered",
  "source_service": "document-records-service",
  "template": {
    "code": "document.approval.request",
    "name": "Document Approval Request",
    "category": "document",
    "channels": ["email", "in_app"],
    "subject": "Approval Required: {{document.title}}",
    "body_html": "<p>Document {{document.reference}} needs your approval...</p>",
    "body_text": "Document {{document.reference}} needs your approval...",
    "variables": ["document.title", "document.reference", "approver.name"]
  }
}
```

The `TemplateRegistrationConsumer` (polled every 10 seconds):
1. Looks up existing template by `code`
2. If exists: archives current version to `NotificationTemplateVersion`, increments version
3. Creates/updates `NotificationTemplateModel` with new data
4. Sets status to `active`

### 10.3 Notification Channels

| Channel | Implementation | Notes |
|---|---|---|
| `email` | Django `send_mail()` | SMTP settings from `NotificationSettings` or env vars |
| `sms` | `InfoBipSMSProvider` or `ConsoleSMSProvider` | Provider resolved dynamically from DB |
| `in_app` | Direct DB insert to `NotificationModel` | Immediate — no external call |
| `webhook` | HTTP POST to configured URL | Bearer token auth supported |

### 10.4 Template Rendering

The `TemplateRenderer` supports:
- Simple placeholders: `{{variable_name}}`
- Nested access: `{{user.first_name}}`
- Conditional blocks: `{% if variable %}content{% endif %}`
- Safe mode (unmatched placeholders left as-is) or strict mode

---

## 11. Kafka Event Architecture

### 11.1 Events Published

| Event Type | Topic | Trigger | Payload |
|---|---|---|---|
| `WorkflowStarted` | `workflow-events` | Plan created | `{planId, workflowType, status, createdBy, metadata}` |
| `WorkflowStageUpdated` | `workflow-events` | Stage action executed | `{planId, stageId, action, actorId, newStatus, form_data}` |
| `WorkflowCompleted` | `workflow-events` | All stages resolved | `{planId, workflowType}` |
| `{type}.workflow.completed` | `workflow-events` | Plan completed (detailed) | `{event_type, plan_id, workflow_type, final_status, final_decision, result_data, disposal_data, metadata}` |

### 11.2 Events Consumed

| Topic | Consumer | Purpose |
|---|---|---|
| `workflow-events` | `WorkflowAutomationEngine` | Automation hooks (auto-advance, escalation, webhooks) |
| `notification-templates` | `TemplateRegistrationConsumer` | Template CRUD from services |
| `notifications-urgent/high/normal/low` | `NotificationConsumer` | Notification delivery |
| `notifications` (default) | `NotificationConsumer` | Backward-compatible notifications |

### 11.3 Dead Letter Queue

Failed notifications are sent to `notification-failed` topic with:
```json
{
  "original_event": { ... },
  "error": "Template not found: bad.template.code",
  "failed_at": "2026-02-24T10:30:00Z"
}
```

---

## 12. Cross-Service Dependencies

### 12.1 Work Orchestration → IAM Service

| Interaction | Type | Details |
|---|---|---|
| JWT validation | Local decode | JWTPermissionMiddleware with shared `JWT_SECRET_KEY` |
| User notification preferences | REST + cache | `IAMPreferenceClient` → `GET /api/v1/users/<id>/notification-preferences/` with 5-min Redis TTL |
| Permission registration | Kafka | Publishes to `service.permission.registry` |

### 12.2 Work Orchestration ← Other Services

| Interaction | Type | Details |
|---|---|---|
| Plan creation | REST | `POST /plans/` from document-records, grc-service |
| Stage actions | REST | `POST /plans/<id>/stages/<id>/actions/` |
| Plan status polling | REST | `GET /plans/<id>/` |
| Template registration | Kafka | Consumes from `notification-templates` |
| Notification requests | Kafka | Consumes from priority notification topics |

### 12.3 Dependency Graph

```
                    ┌─────────────────────────────────────────────┐
                    │       work-orchestration-service             │
                    │                                             │
  JWT decode        │  ┌─────────────────┐  ┌─────────────────┐  │
  (local) ──────────│──│ JWTPermission   │  │ Automation      │  │
                    │  │ Middleware       │  │ Engine          │  │
  User preferences  │  ├─────────────────┤  │ (auto-advance,  │  │
  (REST + cache) ──>│  │ IAMPreference   │  │  escalation,    │  │
                    │  │ Client          │  │  webhooks)      │  │
                    │  │ (5min Redis TTL)│  └──────┬──────────┘  │
                    │  └─────────────────┘         │              │
                    │                              │ consumes     │
 Kafka inbound:     │  ┌─────────────────┐         │              │
 notification-*  ──>│  │ Notification    │  ┌──────┴──────────┐  │
 notification-   ──>│  │ Consumer        │  │ Kafka Consumer  │  │
 templates       ──>│  │ (email,SMS,     │  │ (workflow-events│  │
                    │  │  in_app,webhook)│  │  topic)         │  │
                    │  └─────────────────┘  └─────────────────┘  │
                    │                                             │
 Kafka outbound:    │  ┌─────────────────┐                       │
 workflow-events ──<│  │ KafkaEvent      │                       │
                    │  │ Dispatcher      │                       │
 Perm registration: │  ├─────────────────┤                       │
 service.permission.│  │ Permission      │                       │
 registry        ──<│  │ Publisher       │                       │
                    │  └─────────────────┘                       │
                    │                                             │
 REST inbound:      │                                             │
 doc-records  ─────>│── /plans/, /plans/{id}/stages/{id}/actions/ │
 grc-service  ─────>│── /templates/, /tasks/                      │
 frontend     ─────>│── /notifications/, /analytics/              │
                    └─────────────────────────────────────────────┘
```

---

## 13. Background Tasks (Celery)

The work-orchestration-service runs **4 Celery Beat tasks**:

| Task | Schedule | Purpose |
|---|---|---|
| `process_workflow_events` | Every 30 seconds | Poll Kafka `workflow-events` topic, feed events to `WorkflowAutomationEngine` for auto-advance, escalation, and webhook triggers |
| `process_reminders` | Every 60 seconds | Process pending reminders due now: deliver via channels, handle retries/snooze/escalation/recurrence |
| `process_template_registrations` | Every 10 seconds | Poll Kafka `notification-templates` topic, create/update notification templates from service registrations |
| `process_notifications` | Every 5 seconds | Poll Kafka notification priority topics, look up templates, render, and deliver via email/SMS/in-app/webhook |

### Celery Architecture

```
┌──────────────────────────────────────┐
│  work-orchestration-celery           │
│  (celery -A config.celery worker     │
│   -l info --concurrency=4)           │
│                                      │
│  work-orchestration-beat             │
│  (celery -A config.celery beat       │
│   -l info)                           │
│                                      │
│  Broker: redis-work-orchestration:   │
│           6379/2                     │
└──────────────────────────────────────┘
```

---

## 14. Permission Registration

Work-orchestration-service registers **23 permissions** with IAM via Kafka topic `service.permission.registry`.

### Permission Codes

| Category | Codes | Count |
|---|---|---|
| **Plan Management** | `workflow:plan:create`, `workflow:plan:read`, `workflow:plan:update`, `workflow:plan:cancel` | 4 |
| **Stage Operations** | `workflow:stage:action`, `workflow:stage:override`, `workflow:stage:assign` | 3 |
| **Task Management** | `workflow:task:create`, `workflow:task:read`, `workflow:task:update`, `workflow:task:assign`, `workflow:task:complete` | 5 |
| **Timesheet** | `workflow:timesheet:log` | 1 |
| **Templates** | `workflow:template:create`, `workflow:template:update`, `workflow:template:publish` | 3 |
| **Reminders** | `workflow:reminder:create`, `workflow:reminder:update` | 2 |
| **Notification Templates** | `workflow:notification_template:manage` | 1 |
| **Analytics** | `workflow:analytics:view` | 1 |
| **Activity Audit** | `workflow:activity:audit` | 1 |
| **Console** | `workflow:console:embed` | 1 |
| **System** | `workflow:system:admin` | 1 |

**Permission Code Convention:** `workflow:resource:action` (colon-separated)

---

## 15. How Other Services Consume Work Orchestration

### 15.1 Creating a Workflow Plan (from document-records-service)

```python
# In WorkOrchestrationClient.create_plan()
payload = {
    "workflow_type": "approval",
    "created_by": str(user_id),
    "status": "active",
    "template_id": str(template_uuid),  # Optional: use a stored template
    "metadata": {
        "document_id": str(document.id),
        "document_title": document.title,
        "document_reference": document.reference_number,
        "document_type": document.document_type,
        "minimum_voters": 3,
        "quorum_percentage": 51,
        "assigned_participants": [str(uid) for uid in approver_ids]
    },
    "stages": [
        {
            "definition_key": "management_review",
            "name": "Management Review",
            "order": 0,
            "assignees": [str(manager_id)],
            "actions": [
                {"name": "approve", "label": "Approve", "next_state": "completed"},
                {"name": "reject", "label": "Reject", "next_state": "rejected"},
                {"name": "request_changes", "label": "Request Changes", "next_state": "in_progress"}
            ],
            "sla": {"targetHours": 48, "graceHours": 8},
            "form_schema": {
                "type": "object",
                "properties": {
                    "comments": {"type": "string"},
                    "vote": {"type": "string", "enum": ["approved", "rejected"]}
                }
            }
        },
        {
            "definition_key": "dg_approval",
            "name": "DG Approval",
            "order": 1,
            "assignees": [str(dg_user_id)],
            "actions": [
                {"name": "approve", "label": "Approve", "next_state": "completed"},
                {"name": "reject", "label": "Reject", "next_state": "rejected"}
            ],
            "sla": {"targetHours": 72}
        }
    ]
}

response = requests.post(
    f"{WORK_ORCHESTRATION_URL}/api/v1/work-orchestration/plans/",
    json=payload,
    headers={"Authorization": f"Bearer {jwt_token}"}
)

plan = response.json()
# plan["id"] → UUID to store as orchestration_plan_id on your entity
```

### 15.2 Advancing a Stage (Approval Action)

```python
payload = {
    "action": "approve",
    "actor_id": str(approver_id),
    "comment": "Approved — document meets requirements",
    "form_data": {
        "vote": "approved",
        "comments": "All criteria satisfied"
    }
}

response = requests.post(
    f"{WORK_ORCHESTRATION_URL}/api/v1/work-orchestration/plans/{plan_id}/stages/{stage_id}/actions/",
    json=payload,
    headers={"Authorization": f"Bearer {jwt_token}"}
)
```

### 15.3 Polling Plan Status (Sync Task)

```python
response = requests.get(
    f"{WORK_ORCHESTRATION_URL}/api/v1/work-orchestration/plans/{plan_id}/",
    headers={"Authorization": f"Bearer {jwt_token}"}
)

plan = response.json()
# plan["status"] → "active", "completed", "rejected"
# plan["stages"] → list of stages with their current statuses
```

### 15.4 Publishing a Notification

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='fims-kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Determine priority topic
topic = "notifications-high"  # or -urgent, -normal, -low

producer.send(topic, {
    "notification": {
        "template_code": "document.approval.request",
        "recipients": {
            "user_ids": [str(approver_id)],
            "email": ["approver@fcc.go.tz"]
        },
        "context": {
            "document": {
                "title": "Monthly Financial Report",
                "reference": "FCC-2026-RPT-00042"
            },
            "approver": {
                "first_name": "John"
            },
            "link": "/documents/uuid-here"
        },
        "metadata": {
            "priority": "high",
            "category": "document"
        }
    },
    "source_service": "document-records-service"
})
```

### 15.5 Registering a Notification Template

```python
producer.send("notification-templates", {
    "event_type": "template.registered",
    "source_service": "my-service",
    "source_version": "1.0.0",
    "timestamp": "2026-02-24T12:00:00Z",
    "template": {
        "code": "myservice.event.occurred",
        "name": "My Event Notification",
        "category": "my-category",
        "channels": ["email", "in_app"],
        "subject": "Event: {{event.name}}",
        "body_html": "<p>Hello {{user.first_name}}, {{event.description}}</p>",
        "body_text": "Hello {{user.first_name}}, {{event.description}}",
        "variables": ["user.first_name", "event.name", "event.description"],
        "metadata": {"priority": "normal"}
    }
})
```

---

## 16. Integration Guide for New Services

### Step 1: Add Environment Variable

```
WORK_ORCHESTRATION_SERVICE_URL=http://work-orchestration-service:8004
```

### Step 2: Create a Client Class (with Circuit Breaker)

```python
import requests
from django.conf import settings

class WorkOrchestrationClient:
    def __init__(self):
        self.base_url = f"{settings.WORK_ORCHESTRATION_SERVICE_URL}/api/v1/work-orchestration"
    
    def create_plan(self, workflow_type, stages, created_by, metadata=None, template_id=None, token=None):
        payload = {
            "workflow_type": workflow_type,
            "created_by": str(created_by),
            "status": "active",
            "stages": stages,
            "metadata": metadata or {},
        }
        if template_id:
            payload["template_id"] = str(template_id)
        
        return requests.post(
            f"{self.base_url}/plans/",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        ).json()
    
    def advance_stage(self, plan_id, stage_id, action, actor_id, form_data=None, token=None):
        return requests.post(
            f"{self.base_url}/plans/{plan_id}/stages/{stage_id}/actions/",
            json={
                "action": action,
                "actor_id": str(actor_id),
                "form_data": form_data or {}
            },
            headers={"Authorization": f"Bearer {token}"}
        ).json()
    
    def get_plan(self, plan_id, token=None):
        return requests.get(
            f"{self.base_url}/plans/{plan_id}/",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
```

### Step 3: Store the Plan ID

```python
class MyBusinessEntity(models.Model):
    name = models.CharField(max_length=200)
    orchestration_plan_id = models.UUIDField(
        null=True, blank=True,
        help_text="Workflow plan UUID from work-orchestration-service"
    )
```

### Step 4: Register Notification Templates (on startup)

Publish your notification templates to Kafka `notification-templates` topic from a management command or ready signal.

### Step 5: Publish Notifications via Kafka

Use the priority-based notification topics — never call the notification API directly for cross-service notifications.

### Step 6: Poll Plan Status (Optional Sync)

For long-running workflows, add a Celery task that periodically polls plan status to keep your local entity synchronized.

---

## 17. Architectural Boundaries — What Not To Do

### Never Build a Workflow Engine in Your Service
All multi-step, multi-actor approval processes must use work-orchestration-service. Don't implement stage tracking, sequential execution, or approval chains locally.

### Never Send Emails or SMS Directly
All notification delivery must go through work-orchestration's notification system. Publish to Kafka notification topics — never call `send_mail()` or SMS APIs from your service.

### Never Store Notification Templates in Your Service
Register them via Kafka `notification-templates` topic. Work-orchestration stores, versions, and renders them.

### Never Create In-App Notifications in Your Database
The `notifications` table lives in work-orchestration's database. Your service should publish notification events; work-orchestration creates the records.

### Never Duplicate Task or Timesheet Tracking
Use standalone tasks or workflow-bound tasks in work-orchestration. Don't build a parallel task system.

### Never Bypass the Sequential Stage Enforcement
The service enforces that only the current `in_progress` stage can be acted upon. Don't try to jump stages by calling update_stage directly with a completed status.

### Never Implement Your Own Quorum/Voting Logic
Commission and management voting is handled by the stage execution system with `minimum_voters` and `quorum_percentage` metadata. Let work-orchestration manage the voting flow.

### Never Connect to the Work Orchestration Database
Access workflow data only through REST APIs or Kafka events. Each service has its own database.

### Never Implement Reminder/Escalation Logic
Use the reminder system with recurrence and escalation policies. Don't build timer-based notification logic in your service.

---

*This document was derived from direct code analysis of the work-orchestration-service codebase. All endpoints, models, flows, and integration patterns described here are based on actual implementation evidence.*
