# FIMS Notification System — End-to-End Implementation Guide

This guide documents the complete notification pipeline and provides code snippets a developer can follow to add notifications to any FIMS microservice.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Kafka Event Contract](#kafka-event-contract)
3. [Producer Service (Your Service)](#producer-service)
   - [NotificationClient](#notificationclient--kafka-producer)
   - [Template-code Mapping](#template-code-mapping--dispatch-helper)
   - [When to Fire Notifications](#when-to-fire-notifications)
   - [Feature-flag Gating](#feature-flag-gating-for-incremental-rollout)
4. [Notification Templates (YAML)](#notification-templates-yaml)
5. [Work Orchestration Consumer](#work-orchestration-consumer-already-built)
6. [Template Registration](#template-registration-kafka)
7. [Frontend Integration](#frontend-already-built)
8. [Checklist for New Services](#checklist-for-adding-notifications-to-a-new-service)
9. [Notification Trigger Matrix](#notification-trigger-matrix)
10. [Permanence and Cross-Service Scope](#permanence-and-cross-service-scope)
11. [Deployment Requirements for New Environments](#deployment-requirements-for-new-environments)

---

## Architecture Overview

```
┌─────────────────────┐       Kafka "notifications"       ┌──────────────────────────┐
│  Producer Service   │ ──────────────────────────────────>│ Work Orchestration Svc   │
│  (Corporate, etc.)  │   notification.send event          │                          │
│                     │                                    │  NotificationConsumer    │
│  NotificationClient │                                    │    ├─ template lookup     │
│  workflow_event_    │                                    │    ├─ render HTML/text    │
│    consumer         │                                    │    ├─ resolve channels    │
└─────────────────────┘                                    │    ├─ send email          │
                                                           │    ├─ create in_app record│
                                                           │    └─ log delivery        │
                                                           │                          │
                                                           │  NotificationModel (DB)  │
                                                           └──────────┬───────────────┘
                                                                      │
                                                           GET /notifications/
                                                                      │
                                                           ┌──────────▼───────────────┐
                                                           │  Frontend                │
                                                           │  NotificationBell (poll) │
                                                           └──────────────────────────┘
```

**Data flow:**

1. An action occurs in a producer service (e.g., workflow stage completes).
2. The service's `WorkflowEventConsumer` determines **who** to notify and **what template** to use.
3. It publishes a `notification.send` event to the `notifications` Kafka topic via `NotificationClient`.
4. Work Orchestration's `NotificationConsumer` picks up the event, looks up the template, renders it, resolves user channel preferences from IAM, and dispatches to email + in-app (with retry, idempotency, and DLQ).
5. The frontend polls the Work Orchestration notification API and displays unread items in the bell icon.

---

## Permanence and Cross-Service Scope

This section clarifies what is global vs service-specific, and what must be in code/images for persistence.

### What applies to all services (global/shared)

- Work Orchestration notification pipeline (`notification.send` consumer, template lookup, rendering, delivery logs, in-app records).
- Notification API endpoints and frontend bell/list behavior.
- DB schema in Work Orchestration for notification records and delivery logs.

If these are correct in Work Orchestration images + migrations, all producer services can benefit.

### What is service-specific

- Workflow event mapping logic in each producer service (`WorkflowStarted`, `WorkflowStageUpdated`, `WorkflowCompleted`).
- Recipient resolution strategy (submitter/assignees/role expansion).
- Template namespace and template registration (`your_service.*` codes in that service's `notifications.yaml`).

If one service does not implement workflow-start/stage notification dispatch, only that service will miss those notifications.

### Runtime patch vs permanent implementation

- `docker cp` + container restart is useful for emergency debugging, but it is **not permanent**.
- Permanent behavior requires:
  - Source code updated in repository.
  - Changes committed and built into new images.
  - Deployment using those new images.
  - Required migrations applied in target environment.

---

## Kafka Event Contract

Every service publishes the same canonical event shape to the `notifications` Kafka topic:

```json
{
    "event_type": "notification.send",
    "timestamp": "2026-03-17T10:30:00+00:00",
    "source_service": "your-service-name",
    "source_version": "1.0.0",
    "notification": {
        "event_id": "uuid-v4",
        "template_code": "documents.review.approval_request",
        "recipient_ids": ["user-uuid-1", "user-uuid-2"],
        "context": {
            "entity_type": "document_review",
            "entity_id": "abc-123",
            "action_url": "/documents/abc-123",
            "document_title": "Annual Report 2025",
            "submitter_name": "Jane Doe"
        },
        "channels": ["email", "in_app"],
        "priority": "high",
        "metadata": {
            "workflow_plan_id": "plan-uuid",
            "trigger_event_kind": "stage_changed"
        }
    }
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `event_type` | string | yes | Always `"notification.send"` |
| `timestamp` | ISO 8601 | yes | UTC timestamp of event creation |
| `source_service` | string | yes | Producing service name (e.g. `"corporate-service"`) |
| `source_version` | string | no | Service version for traceability |
| `notification.event_id` | UUID | yes | Unique event ID, used for idempotency |
| `notification.template_code` | string | yes | Template to render (e.g. `"corporate.leave.approved"`) |
| `notification.recipient_ids` | string[] | yes | IAM user UUIDs (not emails) |
| `notification.context` | object | yes | Variables for template rendering |
| `notification.channels` | string[] | no | `["email", "in_app"]` (default if omitted) |
| `notification.priority` | string | no | `urgent` / `high` / `normal` (default) / `low` |
| `notification.metadata` | object | no | Audit and tracking info |

### Key Rules

- `recipient_ids` are always **IAM user UUIDs**, not emails. The consumer resolves emails from IAM.
- `context` keys must match `{{placeholder}}` names in the corresponding template.
- `channels` defaults to `["email", "in_app"]` if omitted.
- `event_id` is used for idempotency — duplicate events with the same ID are skipped.

---

## Producer Service

You need three things in your service to start sending notifications:

### NotificationClient — Kafka Producer

Copy and adapt from Corporate Service. The core method is `send_notification`:

**File:** `apps/infrastructure/external/notification_client.py`

```python
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class NotificationClient:
    _producer = None
    _topic = None

    def __init__(self):
        if NotificationClient._producer is None:
            try:
                from confluent_kafka import Producer
                NotificationClient._producer = Producer({
                    "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                    "linger.ms": 10,
                    "batch.num.messages": 1,
                })
                NotificationClient._topic = getattr(
                    settings, 'KAFKA_NOTIFICATIONS_TOPIC', 'notifications'
                )
            except Exception as e:
                logger.error(f"Failed to init Kafka producer: {e}", exc_info=True)
        self._producer = NotificationClient._producer
        self._topic = NotificationClient._topic

    def send_notification(
        self,
        template_code: str,
        recipient_ids: List[str],
        context: Dict[str, Any],
        priority: str = "normal",
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not self._producer:
            logger.error("Cannot send notification: Kafka producer not initialized")
            return False

        if not recipient_ids:
            logger.warning(f"No recipients for notification {template_code}")
            return False

        event_id = str(uuid.uuid4())
        canonical = {
            "event_id": event_id,
            "template_code": template_code,
            "recipient_ids": recipient_ids,
            "context": context,
            "priority": priority,
            "channels": channels or ["email", "in_app"],
            "metadata": metadata or {},
        }
        envelope = {
            "event_type": "notification.send",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_service": "your-service-name",   # <-- CHANGE THIS
            "source_version": getattr(settings, "SERVICE_VERSION", "1.0.0"),
            "notification": canonical,
        }
        try:
            serialized = json.dumps(envelope).encode("utf-8")
            self._producer.produce(self._topic, serialized)
            self._producer.flush(timeout=5)
            logger.info(
                f"Published notification: {template_code} to {len(recipient_ids)} recipients"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish notification: {e}", exc_info=True)
            return False


_notification_client: Optional[NotificationClient] = None

def get_notification_client() -> NotificationClient:
    global _notification_client
    if _notification_client is None:
        _notification_client = NotificationClient()
    return _notification_client
```

You can also add **convenience methods** for domain-specific notifications (optional, but improves readability):

```python
class NotificationClient:
    # ... core send_notification above ...

    def send_document_approved_notification(
        self,
        submitter_id: str,
        document_title: str,
        approver_name: str,
    ) -> bool:
        return self.send_notification(
            template_code="documents.doc_review.approved",
            recipient_ids=[submitter_id],
            context={
                "document_title": document_title,
                "approver_name": approver_name,
                "action_url": f"/documents/{submitter_id}",
            },
            priority="normal",
        )
```

---

### Template-code Mapping & Dispatch Helper

In your workflow event consumer, define a mapping from entity types to template prefixes:

**File:** `apps/core/consumers/workflow_event_consumer.py`

```python
class WorkflowEventConsumer:

    # Maps each entity type to its notification template prefix.
    # Template codes follow the pattern: {service}.{prefix}.{action}
    # e.g. "documents.doc_review.approval_request"
    NOTIFICATION_ENTITY_PREFIX = {
        'document_review': 'doc_review',
        'case_file': 'case_file',
        # ... add all your entity types here
    }

    def _template_code(self, entity_type: str, event_kind: str) -> str:
        """
        Resolve notification template code from entity type + event kind.

        event_kind is one of: assignment, stage_changed, approved, rejected, returned
        """
        prefix = self.NOTIFICATION_ENTITY_PREFIX.get(entity_type, "workflow")

        if event_kind in {"approved", "rejected", "returned", "resolved"}:
            return f"documents.{prefix}.{event_kind}"
        if event_kind == "stage_changed":
            return f"documents.{prefix}.approval_request"
        if event_kind == "assignment":
            return "documents.workflow.assignment"
        return f"documents.{prefix}.approval_request"

    def _emit_notification(
        self,
        template_code: str,
        recipient_ids: List[str],
        context: Dict[str, Any],
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        from apps.infrastructure.external.notification_client import get_notification_client

        if not recipient_ids:
            return

        client = get_notification_client()
        ok = client.send_notification(
            template_code=template_code,
            recipient_ids=recipient_ids,
            context=context,
            priority=priority,
            channels=["email", "in_app"],
            metadata=metadata or {},
        )
        if not ok:
            logger.warning(
                "Failed to publish notification template=%s recipients=%d",
                template_code, len(recipient_ids),
            )
```

---

### Recipient Resolution

The producer must determine **who** to notify. Three helper methods handle this:

```python
class WorkflowEventConsumer:
    # ...

    def _extract_submitter_id(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Resolve submitter user ID from plan metadata."""
        candidates = (
            metadata.get('initiator_id'),
            metadata.get('submitted_by'),
            metadata.get('created_by'),
            metadata.get('requester_user_id'),
            metadata.get('applicant_user_id'),
            metadata.get('officer_user_id'),
            (metadata.get('context') or {}).get('initiator_id'),
            (metadata.get('context') or {}).get('submitted_by'),
            (metadata.get('context') or {}).get('created_by'),
        )
        for value in candidates:
            if value:
                return str(value)
        return None

    def _resolve_assignees(self, assignees: List[Any]) -> Dict[str, Any]:
        """Expand assignees list into user IDs and unresolved role tokens."""
        user_ids: Set[str] = set()
        unresolved_roles: List[str] = []

        for assignee in assignees or []:
            if not assignee:
                continue
            value = str(assignee).strip()
            if not value:
                continue
            if value.startswith("role:"):
                unresolved_roles.append(value)
                continue
            if value.startswith("{{") and value.endswith("}}"):
                continue
            user_ids.add(value)

        return {
            "user_ids": sorted(user_ids),
            "unresolved_roles": sorted(set(unresolved_roles)),
        }

    def _active_stage_assignees(self, plan) -> Dict[str, Any]:
        """Get recipients from currently active/in-progress stage(s)."""
        recipients: Set[str] = set()
        unresolved_roles: Set[str] = set()
        stage_keys: List[str] = []

        if not plan or not plan.stages:
            return {"recipient_ids": [], "roles": [], "stage_keys": []}

        for stage in plan.stages:
            status = (stage.get('status') or '').lower()
            if status not in ('in_progress', 'active', 'pending'):
                continue
            stage_key = stage.get('definition_key') or stage.get('definitionKey')
            if stage_key:
                stage_keys.append(stage_key)
            resolved = self._resolve_assignees(stage.get('assignees') or [])
            recipients.update(resolved["user_ids"])
            unresolved_roles.update(resolved["unresolved_roles"])

        return {
            "recipient_ids": sorted(recipients),
            "roles": sorted(unresolved_roles),
            "stage_keys": stage_keys,
        }
```

---

### When to Fire Notifications

Central dispatch method — called after every workflow event is processed:

```python
def _dispatch_workflow_notifications(
    self,
    plan_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    stage_key: str,
    actor_id: Optional[str],
    event_kind: str,
) -> None:
    """Dispatch assignment/stage-change/outcome notifications."""
    # Feature-flag check
    enabled = getattr(settings, "WORKFLOW_NOTIFICATION_ENABLED_ENTITIES", "all")
    if enabled != "all" and entity_type not in set(enabled or []):
        logger.info("Notification rollout skipped entity_type=%s", entity_type)
        return

    # 1. Fetch plan from Work Orchestration
    metadata = self._get_plan_metadata(plan_id) or {}
    plan = self._get_plan(plan_id)

    # 2. Resolve submitter (the person who originally submitted)
    submitter_id = self._extract_submitter_id(metadata)

    # 3. Resolve current stage assignees (people who need to act next)
    stage_recipients = self._active_stage_assignees(plan)
    assignee_ids = stage_recipients["recipient_ids"]

    # 4. Build template context
    context = {
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "plan_id": str(plan_id),
        "stage_key": stage_key or "",
        "action": action or "",
        "actor_id": str(actor_id) if actor_id else "",
        "submitter_id": submitter_id or "",
        "next_stage_keys": stage_recipients.get("stage_keys", []),
        "action_url": f"/workflows/{plan_id}",
    }

    # 5. Build audit metadata
    event_metadata = {
        "workflow_entity_type": entity_type,
        "workflow_entity_id": str(entity_id),
        "workflow_plan_id": str(plan_id),
        "trigger_event_kind": event_kind,
    }

    # 6. Dispatch based on event kind
    if event_kind in {"assignment", "stage_changed"}:
        # Notify assignees (people who need to take action)
        template = self._template_code(entity_type, event_kind)
        self._emit_notification(
            template_code=template,
            recipient_ids=assignee_ids,
            context=context,
            priority="high",
            metadata=event_metadata,
        )
        # Notify submitter that their item moved to a new stage
        if submitter_id:
            self._emit_notification(
                template_code="corporate.workflow.stage_changed",  # <-- use your service prefix
                recipient_ids=[submitter_id],
                context=context,
                priority="normal",
                metadata=event_metadata,
            )
        return

    # Outcome notifications: approved/rejected/returned
    outcome_template = self._template_code(entity_type, event_kind)
    all_recipients = sorted(set(
        ([submitter_id] if submitter_id else []) + assignee_ids
    ))
    self._emit_notification(
        template_code=outcome_template,
        recipient_ids=all_recipients,
        context=context,
        priority="normal",
        metadata=event_metadata,
    )
```

**Call it from your event handlers:**

```python
def process_workflow_stage_updated(self, event: Dict[str, Any]) -> bool:
    payload = event.get('payload', {})
    plan_id = payload.get('planId')
    action = payload.get('action', '')
    actor_id = payload.get('actorId')
    new_status = payload.get('newStatus', '')
    stage_key = payload.get('stageKey', '')
    # ... resolve entity_type, entity_id from plan metadata ...

    # Handle assignment events immediately
    if action == 'assign':
        self._dispatch_workflow_notifications(
            plan_id, entity_type, entity_id, action,
            stage_key, actor_id, event_kind='assignment',
        )
        return True

    # Run entity handler (update DB status, etc.)
    handled = handler(entity_id=entity_id, action=action, ...)
    if not handled:
        return False

    # Determine event_kind from action/status
    if action in ('return',):
        event_kind = 'returned'
    elif action in ('reject',) or new_status == 'rejected':
        event_kind = 'rejected'
    else:
        event_kind = 'stage_changed'

    self._dispatch_workflow_notifications(
        plan_id, entity_type, entity_id, action,
        stage_key, actor_id, event_kind,
    )
    return True


def process_workflow_completed(self, event: Dict[str, Any]) -> bool:
    # ... resolve entity_type, entity_id ...
    # Run entity handler (mark as approved, etc.)
    handled = handler(...)
    if not handled:
        return False

    self._dispatch_workflow_notifications(
        plan_id, entity_type, entity_id, 'approve',
        'workflow_completed', None, event_kind='approved',
    )
    return True
```

---

### Feature-flag Gating for Incremental Rollout

Add to your Django `settings.py`:

```python
# "all" enables notifications for every entity type.
# Set to a list to enable only specific entities during phased rollout:
# WORKFLOW_NOTIFICATION_ENABLED_ENTITIES = ["document_review", "case_file"]
WORKFLOW_NOTIFICATION_ENABLED_ENTITIES = "all"
```

The guard check in `_dispatch_workflow_notifications` ensures only opted-in entity types generate notifications.

---

## Notification Templates (YAML)

Each entity type needs up to **4 templates** (approval_request, approved, rejected, returned), plus **2 generic templates** shared across all entities (assignment, stage_changed).

**File:** `apps/core/templates/notifications.yaml`

### Generic Templates (shared across all entities in the service)

```yaml
templates:
  # -----------------------------------------------------------------------
  # Generic workflow notifications
  # -----------------------------------------------------------------------
  - code: "documents.workflow.assignment"     # <-- use your service prefix
    name: "Workflow Assignment"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "You Have a New Workflow Assignment"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #0066cc;">Workflow Assignment</h2>
            <p>You have been assigned a workflow task.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
              <tr>
                <td style="padding: 6px 12px; color: #666;">Type</td>
                <td style="padding: 6px 12px;">{{entity_type}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Stage</td>
                <td style="padding: 6px 12px;">{{stage_key}}</td>
              </tr>
            </table>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{action_url}}"
                 style="background-color: #0066cc; color: white; padding: 12px 24px;
                        text-decoration: none; border-radius: 4px;">
                Open Workflow</a>
            </p>
          </div>
        </body>
      </html>
    body_text: "You have been assigned a task for {{entity_type}} at stage {{stage_key}}."
    variables:
      - { name: "entity_type", required: true, type: "string" }
      - { name: "entity_id", required: true, type: "string" }
      - { name: "stage_key", required: true, type: "string" }
      - { name: "action_url", required: true, type: "url" }
    metadata:
      service: "document-records"
      domain: "workflow"
      entity: "workflow"
      action: "assignment"
      priority: "high"
      version: "1.0.0"

  - code: "documents.workflow.stage_changed"
    name: "Workflow Stage Changed"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "Workflow Stage Updated"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #0066cc;">Workflow Stage Updated</h2>
            <p>The workflow has moved to a new stage.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
              <tr>
                <td style="padding: 6px 12px; color: #666;">Type</td>
                <td style="padding: 6px 12px;">{{entity_type}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Action</td>
                <td style="padding: 6px 12px;">{{action}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Stage</td>
                <td style="padding: 6px 12px;">{{stage_key}}</td>
              </tr>
            </table>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{action_url}}"
                 style="background-color: #0066cc; color: white; padding: 12px 24px;
                        text-decoration: none; border-radius: 4px;">
                View Workflow</a>
            </p>
          </div>
        </body>
      </html>
    body_text: "Workflow {{entity_type}} ({{entity_id}}) moved to stage {{stage_key}} after action {{action}}."
    variables:
      - { name: "entity_type", required: true, type: "string" }
      - { name: "entity_id", required: true, type: "string" }
      - { name: "action", required: true, type: "string" }
      - { name: "stage_key", required: true, type: "string" }
      - { name: "action_url", required: true, type: "url" }
    metadata:
      service: "document-records"
      domain: "workflow"
      entity: "workflow"
      action: "stage_changed"
      priority: "normal"
      version: "1.0.0"
```

### Per-Entity Templates (example for a "document review" entity)

```yaml
  # -----------------------------------------------------------------------
  # Document Review
  # -----------------------------------------------------------------------
  - code: "documents.doc_review.approval_request"
    name: "Document Review Approval Request"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "Document Requires Your Review"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #0066cc;">Document Review Required</h2>
            <p>A document requires your review and approval:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
              <tr>
                <td style="padding: 6px 12px; color: #666;">Document</td>
                <td style="padding: 6px 12px; font-weight: bold;">{{document_title}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Submitted By</td>
                <td style="padding: 6px 12px;">{{submitter_name}}</td>
              </tr>
            </table>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{action_url}}"
                 style="background-color: #0066cc; color: white; padding: 12px 24px;
                        text-decoration: none; border-radius: 4px;">
                Review Document</a>
            </p>
          </div>
        </body>
      </html>
    body_text: "Document '{{document_title}}' submitted by {{submitter_name}} requires your review."
    variables:
      - { name: "document_title", required: true, type: "string" }
      - { name: "submitter_name", required: true, type: "string" }
      - { name: "action_url", required: true, type: "url" }
    metadata:
      service: "document-records"
      entity: "document_review"
      action: "approval_request"
      priority: "high"
      version: "1.0.0"

  - code: "documents.doc_review.approved"
    name: "Document Review Approved"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "Document Approved"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #28a745;">Document Approved</h2>
            <p>Your document has been approved.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
              <tr>
                <td style="padding: 6px 12px; color: #666;">Document</td>
                <td style="padding: 6px 12px; font-weight: bold;">{{document_title}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Approved By</td>
                <td style="padding: 6px 12px;">{{approver_name}}</td>
              </tr>
            </table>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{action_url}}"
                 style="background-color: #28a745; color: white; padding: 12px 24px;
                        text-decoration: none; border-radius: 4px;">
                View Document</a>
            </p>
          </div>
        </body>
      </html>
    body_text: "Your document '{{document_title}}' has been approved by {{approver_name}}."
    variables:
      - { name: "document_title", required: true, type: "string" }
      - { name: "approver_name", required: true, type: "string" }
      - { name: "action_url", required: true, type: "url" }
    metadata:
      service: "document-records"
      entity: "document_review"
      action: "approved"
      priority: "normal"
      version: "1.0.0"

  - code: "documents.doc_review.rejected"
    name: "Document Review Rejected"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "Document Rejected"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #dc3545;">Document Rejected</h2>
            <p>Your document has been rejected.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
              <tr>
                <td style="padding: 6px 12px; color: #666;">Document</td>
                <td style="padding: 6px 12px; font-weight: bold;">{{document_title}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Rejected By</td>
                <td style="padding: 6px 12px;">{{rejector_name}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Reason</td>
                <td style="padding: 6px 12px;">{{rejection_reason}}</td>
              </tr>
            </table>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{action_url}}"
                 style="background-color: #dc3545; color: white; padding: 12px 24px;
                        text-decoration: none; border-radius: 4px;">
                View Document</a>
            </p>
          </div>
        </body>
      </html>
    body_text: "Your document '{{document_title}}' was rejected by {{rejector_name}}. Reason: {{rejection_reason}}"
    variables:
      - { name: "document_title", required: true, type: "string" }
      - { name: "rejector_name", required: true, type: "string" }
      - { name: "rejection_reason", required: true, type: "string" }
      - { name: "action_url", required: true, type: "url" }
    metadata:
      service: "document-records"
      entity: "document_review"
      action: "rejected"
      priority: "normal"
      version: "1.0.0"

  - code: "documents.doc_review.returned"
    name: "Document Review Returned"
    category: "workflow"
    channels: ["email", "in_app"]
    subject: "Document Returned for Amendment"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #fd7e14;">Document Returned for Amendment</h2>
            <p>Your document has been returned for amendment.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
              <tr>
                <td style="padding: 6px 12px; color: #666;">Document</td>
                <td style="padding: 6px 12px; font-weight: bold;">{{document_title}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Returned By</td>
                <td style="padding: 6px 12px;">{{returner_name}}</td>
              </tr>
              <tr>
                <td style="padding: 6px 12px; color: #666;">Reason</td>
                <td style="padding: 6px 12px;">{{return_reason}}</td>
              </tr>
            </table>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{action_url}}"
                 style="background-color: #fd7e14; color: white; padding: 12px 24px;
                        text-decoration: none; border-radius: 4px;">
                View Document</a>
            </p>
          </div>
        </body>
      </html>
    body_text: "Your document '{{document_title}}' was returned by {{returner_name}}. Reason: {{return_reason}}"
    variables:
      - { name: "document_title", required: true, type: "string" }
      - { name: "returner_name", required: true, type: "string" }
      - { name: "return_reason", required: true, type: "string" }
      - { name: "action_url", required: true, type: "url" }
    metadata:
      service: "document-records"
      entity: "document_review"
      action: "returned"
      priority: "normal"
      version: "1.0.0"
```

### Template Design Notes

- `body_html` is used for **email** and is the source of truth for content.
- `body_text` is a concise one-liner used for the **in-app** notification message (also used as email plaintext fallback).
- `channels: ["email", "in_app"]` on every template ensures dual-channel delivery.
- `{{placeholder}}` names **must** match the keys in the `context` dictionary from the producer.
- Use consistent color conventions: blue for action required, green for approved, red for rejected, orange for returned.

---

## Work Orchestration Consumer (Already Built)

The `NotificationConsumer` in Work Orchestration handles everything automatically — **no changes needed** when adding a new service. Here is what it does:

1. **Normalizes** incoming events (supports both new canonical and legacy formats via `_normalize_event`).
2. **Looks up** the template by `template_code` from `NotificationTemplateModel` in the database.
3. **Renders** the template with the provided context using `TemplateRenderer` (supports nested keys like `{{user.first_name}}`).
4. **Resolves channels per user**: intersects template channels, requested channels, and user preferences from IAM via `_resolve_channel_targets`.
5. **Sends email** with retry/backoff via `_dispatch_with_retry` (configurable retries + exponential backoff).
6. **Creates `NotificationModel` records** (in-app) for each recipient.
7. **Logs delivery** in `NotificationDeliveryLog` with idempotency keys (`event_id:template_code:channel:recipient`) to prevent duplicate sends.
8. **DLQ**: Malformed or permanently failed events are sent to the `notification-failed` dead-letter topic for later replay.
9. **Compatibility path**: accepts canonical `event.notification` and legacy `event.payload` envelopes.
10. **Topic subscription**: consumer should subscribe to the configured `KAFKA_NOTIFICATIONS_TOPIC` (commonly `notifications`) to avoid idle polling on missing topics.

### Key Configuration (Work Orchestration `settings.py`)

```python
KAFKA_NOTIFICATIONS_TOPIC = "notifications"
KAFKA_NOTIFICATION_CONSUMER_GROUP = "work-orchestration-notification-consumer"
KAFKA_NOTIFICATION_DLQ_TOPIC = "notification-failed"
NOTIFICATION_CHANNEL_MAX_RETRIES = 3
NOTIFICATION_CHANNEL_RETRY_BACKOFF_SECONDS = 0.5
```

> Important: ensure Work Orchestration migrations include the `notifications` table (`NotificationModel`).  
> If this table is missing, `/api/v1/workflow/notifications/*` endpoints will fail with DB errors.

### DLQ Replay

A management command exists to replay failed events:

```bash
python manage.py replay_notification_dlq --max-messages 100
```

---

## Template Registration (Kafka)

Templates must be registered into Work Orchestration's database. This is done via Kafka on service startup.

**File:** `apps/core/templates/registry.py`

```python
import json
import logging
import yaml
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


class TemplateRegistry:
    SERVICE_NAME = "your-service-name"

    def __init__(self):
        self._templates = {}
        self._loaded = False

    def load_templates(self):
        yaml_path = Path(__file__).parent / "notifications.yaml"
        if not yaml_path.exists():
            logger.warning("notifications.yaml not found at %s", yaml_path)
            return
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        for tmpl in data.get("templates", []):
            code = tmpl.get("code")
            if code:
                self._templates[code] = tmpl
        self._loaded = True

    def list_templates(self) -> list:
        if not self._loaded:
            self.load_templates()
        return list(self._templates.keys())

    def publish_templates(self):
        """Publish all templates to Kafka for Work Orchestration to consume."""
        if not self._loaded:
            self.load_templates()
        try:
            from confluent_kafka import Producer
            producer = Producer({
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            })
            topic = getattr(settings, "KAFKA_TEMPLATE_TOPIC", "notification-templates")

            for code, tmpl in self._templates.items():
                event = {
                    "event_type": "template.registered",
                    "source_service": self.SERVICE_NAME,
                    "template": tmpl,
                }
                producer.produce(topic, json.dumps(event).encode("utf-8"))

            producer.flush(timeout=10)
            logger.info("Published %d templates to %s", len(self._templates), topic)
        except Exception as e:
            logger.error("Failed to publish templates: %s", e, exc_info=True)


template_registry = TemplateRegistry()
```

**Management command:** `apps/core/management/commands/register_notification_templates.py`

```python
from django.core.management.base import BaseCommand
from apps.core.templates.registry import template_registry


class Command(BaseCommand):
    help = "Register notification templates with Work Orchestration via Kafka."

    def handle(self, *args, **options):
        template_registry.load_templates()
        count = len(template_registry.list_templates())
        self.stdout.write(f"Loaded {count} templates, publishing...")
        template_registry.publish_templates()
        self.stdout.write(self.style.SUCCESS(f"Published {count} templates."))
```

Run on deploy:

```bash
python manage.py register_notification_templates
```

---

## Template Validation Command

Catch missing templates before production:

**File:** `apps/core/management/commands/validate_notification_templates.py`

```python
from django.core.management.base import BaseCommand, CommandError
from apps.core.consumers.workflow_event_consumer import WorkflowEventConsumer
from apps.core.templates.registry import template_registry


class Command(BaseCommand):
    help = "Validate workflow notification template mapping coverage."

    def handle(self, *args, **options):
        template_registry.load_templates()
        codes = set(template_registry.list_templates())
        missing = []

        for entity_type in WorkflowEventConsumer.NOTIFICATION_ENTITY_PREFIX:
            prefix = WorkflowEventConsumer.NOTIFICATION_ENTITY_PREFIX[entity_type]
            required = {
                f"documents.{prefix}.approval_request",
                f"documents.{prefix}.approved",
                f"documents.{prefix}.rejected",
            }
            for code in required:
                if code not in codes:
                    missing.append((entity_type, code))

        for shared in ("documents.workflow.assignment", "documents.workflow.stage_changed"):
            if shared not in codes:
                missing.append(("workflow", shared))

        if missing:
            self.stderr.write(self.style.ERROR(f"Missing {len(missing)} templates:"))
            for entity, code in missing:
                self.stderr.write(f"  {entity} -> {code}")
            raise CommandError("Template validation failed.")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"All {len(codes)} templates validated successfully."
            ))
```

Run in CI or pre-deploy:

```bash
python manage.py validate_notification_templates
```

---

## Frontend (Already Built)

`NotificationBell.tsx` polls the Work Orchestration API every 30 seconds. No frontend changes are needed when adding a new service — the bell automatically displays any `NotificationModel` records created for the authenticated user.

### API Endpoints (Work Orchestration)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/workflow/notifications/` | GET | List notifications for authenticated user |
| `/api/v1/workflow/notifications/stats/` | GET | Unread count |
| `/api/v1/workflow/notifications/<id>/` | PATCH | Mark as read |

### Frontend Polling Code (for reference)

```typescript
// Fetch unread notifications
const { data } = useQuery({
  queryKey: ["notifications", "unread", "bell"],
  queryFn: () =>
    workOrchestrationService.getNotifications({ read: false, limit: 20 }),
  refetchInterval: 30000,
});

// Fetch unread count
const { data: stats } = useQuery({
  queryKey: ["notification-stats", "bell"],
  queryFn: () => workOrchestrationService.getNotificationStats(),
  refetchInterval: 30000,
});
```

---

## Checklist for Adding Notifications to a New Service

1. **Copy `NotificationClient`** into `apps/infrastructure/external/notification_client.py`.
   Change `source_service` to your service name.

2. **Define `NOTIFICATION_ENTITY_PREFIX`** mapping in your workflow event consumer
   for all entity types in the service.

3. **Add helper methods** to your workflow event consumer:
   `_template_code`, `_emit_notification`, `_extract_submitter_id`,
   `_resolve_assignees`, `_active_stage_assignees`, `_dispatch_workflow_notifications`.

4. **Create `notifications.yaml`** with templates for each entity
   (`approval_request`, `approved`, `rejected`, `returned`)
   plus 2 generic templates (`assignment`, `stage_changed`).

5. **Copy `TemplateRegistry`** and `register_notification_templates` management command.

6. **Add `validate_notification_templates`** management command.

7. **Wire event handlers**: call `_dispatch_workflow_notifications()` after every
   entity handler returns `True` in `process_workflow_stage_updated` and
   `process_workflow_completed`.

8. **Handle `WorkflowStarted` events** in producer workflow consumers and dispatch
   `event_kind='assignment'` for first-stage assignees. Without this, the initial
   assignee on workflow creation will not receive a notification.

9. **Configure Django settings**:

   ```python
   KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
   KAFKA_NOTIFICATIONS_TOPIC = "notifications"
   WORKFLOW_NOTIFICATION_ENABLED_ENTITIES = "all"
   ```

10. **Register templates on deploy**: `python manage.py register_notification_templates`

11. **Validate templates in CI**: `python manage.py validate_notification_templates`

---

## Notification Trigger Matrix

| Workflow Event | Who Gets Notified | Template Used | Priority |
|---|---|---|---|
| Workflow started / stage assigned | All assignees of the active stage | `*.workflow.assignment` | high |
| Stage completed (approve) | Next stage assignees + submitter | `*.{entity}.approval_request` + `*.workflow.stage_changed` | high / normal |
| Workflow fully completed | Submitter + last stage assignees | `*.{entity}.approved` | normal |
| Stage rejected | Submitter + assignees | `*.{entity}.rejected` | normal |
| Stage returned | Submitter | `*.{entity}.returned` | normal |

In every case, both **email** and **in_app** channels fire unless the user's IAM preferences disable one.

---

## Deployment Requirements for New Environments

Use this as a production rollout gate to ensure behavior is preserved in fresh environments.

1. Build and deploy updated images (do not rely on runtime container edits).
2. Apply Work Orchestration migrations:
   - `python manage.py migrate`
   - verify `notifications` table exists.
3. Ensure Work Orchestration notification consumer is running and healthy.
4. Confirm `KAFKA_NOTIFICATIONS_TOPIC` exists (`notifications` by default).
5. Confirm producer services publish valid `notification.send` events.
6. Register templates from each producer service on startup/deploy.
7. Verify active templates exist in Work Orchestration (`notification_templates` table).
8. Smoke test:
   - create a new workflow item,
   - confirm first assignee receives in-app notification,
   - confirm delivery logs contain both `in_app` and `email` statuses.

---

## Django Settings Reference

| Setting | Default | Description |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | `"kafka:9092"` | Kafka broker addresses |
| `KAFKA_NOTIFICATIONS_TOPIC` | `"notifications"` | Topic for notification events |
| `KAFKA_TEMPLATE_TOPIC` | `"notification-templates"` | Topic for template registration |
| `KAFKA_NOTIFICATION_DLQ_TOPIC` | `"notification-failed"` | Dead letter queue topic |
| `WORKFLOW_NOTIFICATION_ENABLED_ENTITIES` | `"all"` | Feature flag: `"all"` or list of entity types |
| `NOTIFICATION_CHANNEL_MAX_RETRIES` | `3` | Retry attempts per channel dispatch |
| `NOTIFICATION_CHANNEL_RETRY_BACKOFF_SECONDS` | `0.5` | Base backoff between retries |
| `SERVICE_VERSION` | `"1.0.0"` | Service version for event tracing |

---

## Reference: Corporate Service Implementation

The Corporate Service (`microservices/corporate-service/`) is the reference implementation with all 24 entity types fully wired. Key files to study:

| File | Purpose |
|---|---|
| `apps/infrastructure/external/notification_client.py` | Kafka producer (NotificationClient) |
| `apps/core/consumers/workflow_event_consumer.py` | Event consumer with full dispatch logic |
| `apps/core/templates/notifications.yaml` | All templates (3100+ lines) |
| `apps/core/templates/registry.py` | Template registry and Kafka publisher |
| `apps/core/management/commands/register_notification_templates.py` | Template registration command |
| `apps/core/management/commands/validate_notification_templates.py` | Template validation command |
| `apps/core/consumers/revision_handler.py` | Return/resubmit notification examples |
