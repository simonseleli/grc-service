# Work Orchestration Service — Notifications Integration Guide

> **Document Type:** Service Integration Reference — Notifications Only  
> **Audience:** Engineers integrating any new FIMS service with Work Orchestration notifications  
> **Source:** Evidence-based analysis of `work-orchestration-service` codebase + `grc-service` reference implementation  
> **Last Updated:** 2026-03-07  
> **Scope:** This document covers **notifications only**. Workflow plan/stage integration is a separate topic.

---

## Table of Contents

1. [What Work Orchestration Owns — Notifications](#1-what-work-orchestration-owns--notifications)
2. [What Your Service Must Provide](#2-what-your-service-must-provide)
3. [The Two Integration Pipelines](#3-the-two-integration-pipelines)
4. [Pipeline 1 — Template Registration](#4-pipeline-1--template-registration)
5. [Pipeline 2 — Sending Notifications](#5-pipeline-2--sending-notifications)
6. [Template YAML Reference](#6-template-yaml-reference)
7. [Notification Event Envelope Reference](#7-notification-event-envelope-reference)
8. [Template Rendering Engine](#8-template-rendering-engine)
9. [Channel Behavior](#9-channel-behavior)
10. [In-App Notifications API](#10-in-app-notifications-api)
11. [Reliability, Timing, and Error Handling](#11-reliability-timing-and-error-handling)
12. [Complete Integration Checklist](#12-complete-integration-checklist)
13. [Anti-Patterns — What Not To Do](#13-anti-patterns--what-not-to-do)
14. [End-to-End Flow Diagram](#14-end-to-end-flow-diagram)

---

## 1. What Work Orchestration Owns — Notifications

Work Orchestration Service (WO, port **8004**) is the **sole authority** for notification delivery in FIMS. No service sends email, SMS, or creates in-app notification records directly. Everything goes through WO.

### What WO provides

| Capability | How Provided |
|---|---|
| **Email delivery** | Django `send_mail()` → SMTP backend (configurable via admin `NotificationSettings`) |
| **SMS delivery** | Infobip API (production) or Console logger (development), also configurable via admin |
| **In-app notification records** | `NotificationModel` stored in WO's PostgreSQL DB; queried by frontend via REST API |
| **Template storage and versioning** | `NotificationTemplateModel` stores all registered templates, with full version history |
| **Template rendering** | `TemplateRenderer` — Jinja-like `{{variable}}` syntax with nested access and conditionals |
| **Priority-based routing** | 4 separate Kafka topics (urgent/high/normal/low) map to different SLA queues |
| **Dead Letter Queue (DLQ)** | Failed notifications go to Kafka topic `notification-failed` for inspection |
| **Delivery logging** | `NotificationDeliveryLog` records every delivery attempt, channel, and result |
| **Notification batching** | Groups notifications by template+channel (batch size 50, timeout 5s) for efficient SMTP |
| **In-app REST API** | Users read/mark/delete their in-app notifications via WO's REST endpoints |

### What WO does NOT do

- WO does **not** pull recipient contact details from IAM on your behalf — your service must resolve email addresses and user IDs before publishing.
- WO does **not** understand your business logic — it only renders templates and delivers.
- WO does **not** schedule future notifications — for scheduled/recurring delivery, use WO's `ReminderModel` (out of scope for this guide).
- WO does **not** consume from a per-service topic — it only consumes from the shared priority topics (`notifications-urgent`, `notifications-high`, `notifications-normal`, `notifications-low`, `notifications`).

---

## 2. What Your Service Must Provide

Before WO can deliver any notification for your service, you must:

1. **A `notifications.yaml` file** — defines all your notification templates with full body HTML and text.
2. **A `TemplateRegistry` class** — reads `notifications.yaml` and publishes `template.registered` events to Kafka at service startup.
3. **A `NotificationPublisher` class** — publishes `notification.send` events to the correct priority Kafka topic when a business event occurs.
4. **A `ready()` hook in `apps.py`** — calls `TemplateRegistry.register_templates()` on startup.
5. **Kafka settings in your `settings.py`** — the topic names and bootstrap servers (these are platform-level env vars, not per-service).

The GRC service has a **reference implementation** of all of these that you can copy directly:

| File | Location in grc-service |
|---|---|
| Template YAML | `apps/core/templates/notifications.yaml` |
| Template Registry | `apps/core/templates/registry.py` |
| Notification Publisher | `apps/core/notifications/publisher.py` |
| Startup hook | `apps/core/apps.py` (calls `registry.register_templates()` in `ready()`) |

---

## 3. The Two Integration Pipelines

There are exactly **two separate Kafka pipelines** you must set up. They are independent and both are required.

```
YOUR SERVICE                          KAFKA                       WORK ORCHESTRATION
─────────────                         ─────                       ──────────────────
                                                                  
  [startup]                                                       
  apps.py ready()                                                
      │                                                           
      └─ TemplateRegistry             notification-templates ──► TemplateRegistrationConsumer
         publish template.registered ───────────────────────►    (polled every 10 seconds)
                                                                  stores to NotificationTemplateModel
                                                                  
  [runtime — any business event]                                  
  NotificationPublisher               notifications-high ──────► NotificationConsumer
      publish notification.send ─────────────────────────────►   (polled every 5 seconds)
                                      notifications-normal         look up template by code
                                      notifications-urgent         render {{variables}}
                                      notifications-low            deliver email/SMS/in-app
                                      notifications (fallback)     
```

**Critical:** If you publish a `notification.send` event before the template is registered, WO will not find the template and will route the event to the `notification-failed` DLQ. **Templates must be registered first**, which happens automatically on startup if you implement the `TemplateRegistry` correctly.

---

## 4. Pipeline 1 — Template Registration

### 4.1 How It Works

On every service startup, your `apps.py` calls `TemplateRegistry.register_templates()`. This reads `notifications.yaml`, creates a `template.registered` event for each template, and publishes them to the `notification-templates` Kafka topic.

WO's Celery Beat runs `process_template_registrations` every **10 seconds**. It polls the `notification-templates` topic using consumer group `work-orchestration-template-consumer` and calls `TemplateRegistrationConsumer.consume_template_registered()` for each event.

WO stores templates in `NotificationTemplateModel` (unique by `code`). Re-registering the same template code updates it (bumps the version, archives the old body to `NotificationTemplateVersion` for history). This means your startup can re-publish templates safely on every deploy — it is **idempotent**.

### 4.2 Registration Event Envelope

Your `TemplateRegistry` must publish this exact structure to the `notification-templates` topic:

```json
{
  "event_type": "template.registered",
  "event_version": "1.0",
  "timestamp": "2026-03-07T10:00:00.000000+00:00",
  "source_service": "your-service-name",
  "source_version": "1.0.0",
  "template": {
    "code": "your-service.entity.action",
    "name": "Human Readable Template Name",
    "description": "What this notification is for",
    "category": "workflow",
    "channels": ["email", "in_app"],
    "subject": "FCC FIMS — Action Required: {{entity.name}}",
    "body_html": "<html>...</html>",
    "body_text": "Plain text version...",
    "variables": [
      {
        "name": "entity.name",
        "required": true,
        "type": "string",
        "description": "Name of the entity"
      }
    ],
    "metadata": {
      "service": "your-service",
      "domain": "entity",
      "action": "action_taken",
      "priority": "normal",
      "version": "1.0.0"
    }
  }
}
```

### 4.3 Required vs Optional Template Fields

| Field | Required | Consumed By WO | Notes |
|---|---|---|---|
| `code` | **YES** | Used as primary key for lookup on `notification.send` | Must be unique platform-wide; use `service.entity.action` format |
| `name` | YES | Stored for admin display | Human-readable |
| `category` | YES | Stored for filtering | e.g., `workflow`, `verification`, `document`, `reminder` |
| `channels` | YES | Stored for admin display and documentation — **does NOT gate delivery** | `["email"]`, `["sms"]`, `["email", "in_app"]` etc. |
| `subject` | YES | Rendered and used as email subject / in-app title | Supports `{{variable}}` syntax |
| `body_html` | YES if email | Used as primary body for email (HTML) | Supports `{{variable}}` syntax |
| `body_text` | YES if SMS | Stored in `metadata.body_text`, used for SMS / fallback | If absent, WO strips HTML tags from `body_html` |
| `variables` | NO | Not consumed by WO at render time — documentation only | Still include it — it is the contract for context callers |
| `metadata` | NO | `metadata.priority` used as template default priority | Informational |
| `description` | NO | Admin display only | Optional but recommended |

**WO will store `body_html` as the primary `body` field and `body_text` inside `metadata.body_text`.** On rendering:
- Email HTML body → `body` field (HTML)
- SMS / text body → `metadata.body_text` (plain text); if `body_text` was not provided, WO strips HTML tags from `body`

### 4.4 Template Code Convention

```
format:  <service-prefix>.<domain>.<action>
example: grc.audit_universe.submitted
         grc.audit_plan.approved
         grc.engagement.returned
         
         iam.user.registration
         document.approval.request
         client.user.email_otp
```

- The prefix **must match your service name** (e.g., `grc` for `grc-service`, `iam` for `iam-service`)
- Use dots as separators — never hyphens or underscores in the code
- Keep it short but descriptive — it is referenced everywhere
- **Platform codes already in use:** `iam.*`, `document.*`, `client.*`, `grc.*`

### 4.5 Reference Implementation — TemplateRegistry

Copy this from `grc-service/apps/core/templates/registry.py` and adapt the `service_name` and YAML path:

```python
# apps/core/templates/registry.py

import json, logging, yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
from kafka import KafkaProducer

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """Registers notification templates with WO via Kafka on startup."""

    def __init__(self):
        self.kafka_bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(',')
        self.topic = getattr(settings, 'KAFKA_NOTIFICATION_TEMPLATES_TOPIC', 'notification-templates')
        self.service_name = 'your-service-name'          # ← change this
        self.service_version = getattr(settings, 'SERVICE_VERSION', '1.0.0')
        self._producer: Optional[KafkaProducer] = None

    def _get_producer(self) -> Optional[KafkaProducer]:
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    retries=3,
                    retry_backoff_ms=250,
                    request_timeout_ms=30000,
                )
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}", exc_info=True)
                return None
        return self._producer

    def _load_templates_from_yaml(self) -> List[Dict[str, Any]]:
        yaml_file = Path(__file__).parent / 'notifications.yaml'
        if not yaml_file.exists():
            logger.warning(f"Templates file not found: {yaml_file}")
            return []
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            templates = data.get('templates', [])
            logger.info(f"Loaded {len(templates)} templates")
            return templates

    def register_templates(self) -> int:
        producer = self._get_producer()
        if not producer:
            return 0
        templates = self._load_templates_from_yaml()
        registered = 0
        for template in templates:
            if not template.get('code'):
                continue
            event = {
                'event_type': 'template.registered',
                'event_version': '1.0',
                'timestamp': timezone.now().isoformat(),
                'source_service': self.service_name,
                'source_version': self.service_version,
                'template': template,
            }
            try:
                future = producer.send(
                    topic=self.topic,
                    key=template['code'],
                    value=event,
                )
                future.get(timeout=10)
                registered += 1
            except Exception as e:
                logger.error(f"Failed to register template {template.get('code')}: {e}")
        producer.flush(timeout=30)
        logger.info(f"Registered {registered}/{len(templates)} templates")
        return registered


_template_registry: Optional[TemplateRegistry] = None

def get_template_registry() -> TemplateRegistry:
    global _template_registry
    if _template_registry is None:
        _template_registry = TemplateRegistry()
    return _template_registry
```

### 4.6 Startup Hook in apps.py

```python
# apps/core/apps.py

from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = 'apps.core'

    def ready(self):
        import threading

        def _register_templates():
            import time
            time.sleep(5)   # let Django fully initialize first
            try:
                from .templates.registry import get_template_registry
                registry = get_template_registry()
                registered = registry.register_templates()
                from django.utils import timezone
                import logging
                logging.getLogger(__name__).info(
                    f"Registered {registered} notification template(s) at {timezone.now()}"
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to register notification templates: {e}", exc_info=True
                )

        thread = threading.Thread(target=_register_templates, daemon=True)
        thread.start()
```

> **Why sleep(5)?** Apps run `ready()` before all Django internals are fully initialized. The 5-second delay prevents database access errors during migrations or fresh starts.

---

## 5. Pipeline 2 — Sending Notifications

### 5.1 How It Works

When a business event occurs in your service (e.g., an audit plan is approved), you call `NotificationPublisher.send_notification()`. This publishes a `notification.send` event to the correct **priority-based Kafka topic**.

WO's Celery Beat runs `process_notifications` every **5 seconds**. It polls all priority topics using consumer group `work-orchestration-notification-consumer-v2` (manual offset commit) and calls `NotificationConsumer.consume_notification_send()` for each event.

WO then:
1. Looks up the template by `template_code` → must be `ACTIVE` in `NotificationTemplateModel`
2. Renders `subject` and `body` using `TemplateRenderer` with the provided `context`
3. Delivers via each channel listed in `recipients`
4. Creates a `NotificationModel` record for each `user_id` (in-app channel)
5. On failure: routes event to `notification-failed` DLQ topic

### 5.2 Priority Topic Selection

| Priority | Kafka Topic | Celery Poll | Use When |
|---|---|---|---|
| `urgent` | `notifications-urgent` | Every 5s | System failures, security alerts, immediate action required |
| `high` | `notifications-high` | Every 5s | Approval requests, workflow stage assigned to user |
| `normal` | `notifications-normal` | Every 5s | Status updates, approval results, general workflow notifications |
| `low` | `notifications-low` | Every 5s | Reminders, FYI summaries, report availability |
| *(fallback)* | `notifications` | Every 5s | Backward compatibility only — use priority topics |

> All 4 priority topics are consumed by the same single Celery task every 5 seconds. The separate topics exist for **future SLA differentiation** and **monitoring dashboards**, not for different polling intervals at this time.

### 5.3 Notification Event Envelope — Exact Format

This is the exact structure WO expects. The consumer validates `event_type == 'notification.send'` and then reads `event['notification']`.

```json
{
  "event_type": "notification.send",
  "event_version": "1.0",
  "timestamp": "2026-03-07T10:30:00.123456+00:00",
  "source_service": "grc-service",
  "notification": {
    "idempotency_key": "grc.audit_plan.approved-cia@fcc.go.tz-202603071030",
    "template_code": "grc.audit_plan.approved",
    "recipients": {
      "email": ["cia@fcc.go.tz", "ia@fcc.go.tz"],
      "user_ids": ["uuid-of-cia", "uuid-of-ia"]
    },
    "context": {
      "audit_plan": {
        "id": "plan-uuid",
        "reference_number": "RBIAP-2025/26-001",
        "title": "Annual Audit Plan FY2025/26"
      },
      "approver": {
        "name": "Dr. Jane Smith"
      },
      "approved_at": "2026-03-07T10:30:00Z",
      "detail_url": "https://staff.fcc.go.tz/grc/audit/plans/plan-uuid"
    },
    "priority": "normal",
    "metadata": {
      "user_ids": ["uuid-of-cia", "uuid-of-ia"]
    }
  }
}
```

### 5.4 The `recipients` Dictionary — All Supported Keys

| Key | Type | What WO Does With It |
|---|---|---|
| `email` | `List[str]` — email addresses | Delivers email using `send_mail()` with rendered subject + HTML body |
| `sms` | `List[str]` — phone numbers (E.164 format) | Delivers SMS using Infobip or ConsoleSMSProvider |
| `user_ids` | `List[str]` — IAM user UUID strings | Creates `NotificationModel` records (in-app) for each user |

**To send in-app + email together:**
```python
recipients = {
    'email': ['user@fcc.go.tz'],
    'user_ids': ['uuid-of-user'],
}
```
WO iterates all keys present and delivers via each. The `user_ids` in-app records are created in WO's own `NotificationModel` database, not in yours.

> **Note on `in_app` vs `user_ids`:** The consumer checks for `'email'` in recipients to send email, `'sms'` in recipients to send SMS, and creates in-app records only when `user_ids` is present in `metadata` OR when an `email` recipient matches a tracked user. To be explicit and reliable, **always include `user_ids` in both `recipients` and `metadata.user_ids`** if you want in-app records created.

### 5.5 Idempotency Key

The idempotency key prevents duplicate deliveries within the same time window (e.g., if Celery retries). The key parts are joined with `-`, using Python `strftime('%Y%m%d%H%M')` for the timestamp:

```
{template_code}-{primary_recipient}-[{entity_id}-]{YYYYMMDDHHmm}
```

- `entity_id` is included only when a known context key is present (`audit_universe.id`, `audit_plan.id`, `engagement.id`) — the GRC publisher extracts it from `context`
- Timestamp is minute-precision (`202603071030`) — same key for all events within the same minute

Example:
```python
from django.utils import timezone

def _generate_idempotency_key(template_code: str, recipient: str, entity_id: str = '') -> str:
    timestamp_minute = timezone.now().strftime('%Y%m%d%H%M')
    parts = [template_code, recipient]
    if entity_id:
        parts.append(str(entity_id))
    parts.append(timestamp_minute)
    return '-'.join(parts)
```

> WO does **not currently enforce** deduplication by idempotency key in code — it is published into the event so WO can use it for monitoring and future dedup. Include it anyway — it is part of the contract.

### 5.6 Reference Implementation — NotificationPublisher

Copy from `grc-service/apps/core/notifications/publisher.py`. The key methods your service will call:

```python
publisher = get_notification_publisher()

# Email only
publisher.send_email(
    template_code='your-service.entity.approved',
    to=['reviewer@fcc.go.tz'],
    context={'entity': {'name': 'Report XYZ'}, 'approver': {'name': 'John'}},
    priority='normal',
)

# In-app only
publisher.send_in_app(
    template_code='your-service.entity.approved',
    user_ids=['uuid-1', 'uuid-2'],
    context={'entity': {'name': 'Report XYZ'}},
    priority='normal',
)

# Multi-channel (email + in-app)
publisher.send_notification(
    template_code='your-service.entity.submitted',
    recipients={
        'email': ['cia@fcc.go.tz'],
        'user_ids': ['uuid-of-cia'],
    },
    context={'entity': {'reference': 'REF-001'}},
    priority='high',
    metadata={'user_ids': ['uuid-of-cia']},
)
```

---

## 6. Template YAML Reference

Your `notifications.yaml` must have this top-level structure:

```yaml
templates:
  - code: "your-service.entity.action"
    name: "Full Human-Readable Template Name"
    description: "Short explanation of when this is triggered"
    category: "workflow"          # workflow | verification | document | reminder | account
    channels: ["email", "in_app"] # must match what you'll set in recipients
    subject: "FCC FIMS — {{entity.title}} Requires Your Attention"
    body_html: |
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #0066cc;">Descriptive Heading</h2>
            <p>Hello {{recipient.first_name}},</p>
            <p>Body text here with {{entity.reference_number}}.</p>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{detail_url}}" style="background-color: #0066cc; color: white;
                 padding: 12px 24px; text-decoration: none; border-radius: 4px;">
                View Details
              </a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">
              Best regards,<br>FCC FIMS — Your Module Name
            </p>
          </div>
        </body>
      </html>
    body_text: |
      Descriptive Heading

      Hello {{recipient.first_name}},

      Body text here with {{entity.reference_number}}.

      View Details: {{detail_url}}

      Best regards,
      FCC FIMS — Your Module Name
    variables:
      - name: "recipient.first_name"
        required: true
        type: "string"
        description: "Recipient's first name from IAM user lookup"
      - name: "entity.reference_number"
        required: true
        type: "string"
        description: "Auto-generated reference number"
      - name: "detail_url"
        required: true
        type: "url"
        description: "Full URL to the entity detail page in staff portal"
    metadata:
      service: "your-service"
      domain: "entity"
      action: "action_taken"
      priority: "normal"          # default priority hint
      version: "1.0.0"
```

### Template Body Tips

- Use `{{variable}}` for simple substitution
- Use `{{parent.child}}` for nested dict access (e.g., `{{audit_plan.reference_number}}`)
- Use `{% if variable %}...{% endif %}` for conditional blocks (useful for optional fields)
- **Always provide both `body_html` and `body_text`** — email uses HTML, SMS uses text
- The `variables` list in YAML is **documentation/contract only** — WO does not validate at render time; missing variables silently leave `{{placeholder}}` in the output (safe mode)

---

## 7. Notification Event Envelope Reference

### 7.1 Top-Level Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `event_type` | string | **YES** | Must be exactly `"notification.send"` — WO rejects anything else |
| `event_version` | string | YES | `"1.0"` |
| `timestamp` | string (ISO 8601) | YES | `timezone.now().isoformat()` |
| `source_service` | string | YES | Your service name, e.g., `"grc-service"` |
| `notification` | object | **YES** | Contains all notification data — see below |

### 7.2 `notification` Object Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `template_code` | string | **YES** | Must match a registered, ACTIVE `NotificationTemplateModel.code` |
| `recipients` | object | **YES** | Keys: `email`, `sms`, `user_ids` — at least one key required |
| `context` | object | YES | Variables for template rendering; nested dicts supported |
| `priority` | string | YES | `urgent`, `high`, `normal`, `low` — determines which Kafka topic to use |
| `idempotency_key` | string | YES | Unique per recipient per minute: `template_code-recipient-YYYYMMDDTHHMM` |
| `metadata` | object | NO | Include `user_ids` list here too if you want in-app records |

### 7.3 Context Variable Naming

WO's `TemplateRenderer` supports nested dict access using dots. Match your context keys to your YAML template placeholder names exactly:

```python
context = {
    'audit_plan': {
        'id': str(plan.id),
        'reference_number': plan.reference_number,
        'title': plan.title,
    },
    'approver': {
        'first_name': approver_user['first_name'],
        'name': f"{approver_user['first_name']} {approver_user['last_name']}",
    },
    'approved_at': plan.approved_at.strftime('%d %b %Y, %H:%M'),
    'detail_url': f"https://staff.fcc.go.tz/grc/audit/plans/{plan.id}",
}
```

Tells you the YAML template can use: `{{audit_plan.reference_number}}`, `{{approver.first_name}}`, `{{approved_at}}`, `{{detail_url}}`, etc.

> **Delivery is controlled by `recipients` keys, not `template.channels`:** Whatever keys you include in `recipients` (`email`, `sms`, `user_ids`) determine what channels WO uses. The `channels` field on the template is stored for documentation and admin display only — WO's notification consumer never consults it when delivering. Keep them consistent for clarity, but know that `recipients` is the actual gatekeeper.

> **Rule:** resolve all display values (names, formatted dates, URLs) in your service before passing to context. WO does not call IAM or any other service to resolve names.

---

## 8. Template Rendering Engine

WO uses its own `TemplateRenderer` class — **not Django templates, not Jinja2**. Key behaviors:

### 8.1 Variable Substitution

```
Syntax:     {{variable_name}}
Nested:     {{parent.child}}  →  context['parent']['child']
Default:    if variable not found, placeholder is left as-is (safe mode)
```

```python
# Template: "Hello {{user.first_name}}, your plan {{plan.ref}} is ready."
# Context:  {'user': {'first_name': 'Alice'}, 'plan': {'ref': 'RBIAP-001'}}
# Result:   "Hello Alice, your plan RBIAP-001 is ready."

# Missing variable (safe mode):
# Context:  {'user': {'first_name': 'Alice'}}
# Result:   "Hello Alice, your plan {{plan.ref}} is ready."
```

### 8.2 Conditional Blocks

```
Syntax:   {% if variable_name %}...content...{% endif %}
Behavior: Content rendered only if variable is truthy in context
Nesting:  Variable is looked up at top level of context dict only (no dot notation in condition)
```

**Critical limitation:** Due to how the regex is written (`[^{]*?`), content inside the conditional block **cannot contain `{` characters**. This means `{{variable}}` substitutions inside `{% if %}` blocks do NOT work — the entire conditional block fails to parse.

```
# This WORKS — plain text inside condition
{% if comments %}
Comments section is available.
{% endif %}

# This DOES NOT WORK — {{}} inside condition, regex fails to parse
{% if comments %}
<p>{{comments}}</p>
{% endif %}
```

**Workaround:** Pre-render any conditional content in your service before passing it to context:

```python
context = {
    # Pre-format optional content yourself before publishing
    'comments_section': f"<p><b>Comments:</b> {entity.comments}</p>" if entity.comments else "",
}
# Then use {{comments_section}} directly in the template body (no if block needed)
```

> **In practice:** No existing GRC templates use `{% if %}` blocks (confirmed by code search). The current renderer supports it for very simple cases (plain text content only). For conditional display of optional fields, pre-compute the value in your service context.

### 8.3 What the Renderer Does NOT Support

- `{% for %}` loops — no list iteration
- `{% else %}` — no else branch
- Filters like `{{ variable | upper }}` — no Django/Jinja filters
- Raw blocks or template inheritance

If you need loops (e.g., a list of findings), pre-format them as a string in your context before publishing.

---

## 9. Channel Behavior

### 9.1 Email Channel

- **Delivered via:** Django `send_mail()` using `EMAIL_BACKEND` configured in WO's settings
- **Configuration:** Admin-configurable via `NotificationSettings` model (SMTP host, port, TLS, credentials)
- **From address:** `DEFAULT_FROM_EMAIL` (default: `noreply@fcc.go.tz`)
- **Body:** Uses `body_html` for HTML email; strips tags for plain-text part if `body_text` not provided
- **Subject:** Rendered from template `subject` field with context substitution

### 9.2 SMS Channel

- **Delivered via:** The notification consumer calls `resolve_sms_provider()` **directly** (not via `NotificationClient`). In development this resolves to `ConsoleSMSProvider` (logs the message to stdout, returns `True`). In production, if `NotificationSettings.sms_provider == 'infobip'` and Infobip credentials are set, it resolves to `InfoBipSMSProvider` which makes a real HTTP call to the Infobip API.
- **Configuration:** Admin-configurable via the `NotificationSettings` DB model (provider, API key, from number). If Infobip is selected but credentials are missing, it falls back to console.
- **Body:** Uses `metadata.body_text` (the `body_text` from your YAML); if absent, WO strips HTML tags from `body`.
- **Phone format:** E.164 format required (e.g., `+255712345678`)

> **Note:** `NotificationClient.send_sms_notification()` IS a no-op placeholder, but the notification consumer does **not** use that method. The consumer's `_send_sms()` calls the provider directly, so SMS delivery via the Kafka pipeline is fully functional in both dev and prod environments.

### 9.3 In-App Channel

- **Delivered via:** WO creates `NotificationModel` records in its own PostgreSQL database
- **Trigger:** Consumer creates a record for each `user_id` in `recipients.user_ids` (or `metadata.user_ids`)
- **Record contains:** `title` = rendered subject, `message` = rendered body_text, `priority` (from `metadata.priority` or defaults to `normal`), `category` (from template), `link` = empty string (the Kafka pipeline does not extract a link from context — link is only populated when in-app records are created via `NotificationClient.send_in_app_notification()` directly), `read = False`
- **Read by frontend:** Via WO REST API `GET /api/v1/work-orchestration/notifications/` (staff portal calls this)
- **Marked as read:** `PATCH /api/v1/work-orchestration/notifications/{id}/` with `{"read": true}`

---

## 10. In-App Notifications API

Once WO creates in-app notification records, they are served back to users via WO's REST API. These endpoints are behind the API Gateway at `/api/v1/work-orchestration/`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/work-orchestration/notifications/` | Bearer JWT | List user's notifications (paginated) |
| `GET` | `/api/v1/work-orchestration/notifications/stats/` | Bearer JWT | Unread count, total count |
| `GET` | `/api/v1/work-orchestration/notifications/{id}/` | Bearer JWT | Single notification detail |
| `PATCH` | `/api/v1/work-orchestration/notifications/{id}/` | Bearer JWT | Mark as read/unread |
| `DELETE` | `/api/v1/work-orchestration/notifications/{id}/` | Bearer JWT | Delete notification |

### Query Parameters for List Endpoint

| Param | Type | Description |
|---|---|---|
| `read` | `true` / `false` | Filter by read status |
| `category` | string | Filter by category |
| `limit` | integer (1–100, default 50) | Items per page |
| `page` | integer (default 1) | Page number |

### Response Structure

```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "user-uuid",
      "title": "Rendered subject string",
      "message": "Rendered body_text string",
      "link": "/grc/audit/plans/plan-uuid",
      "read": false,
      "read_at": null,
      "priority": "high",
      "category": "workflow",
      "metadata": { "template_code": "grc.audit_plan.submitted", ... },
      "created_at": "2026-03-07T10:30:00.000000Z",
      "updated_at": "2026-03-07T10:30:00.000000Z"
    }
  ],
  "meta": {
    "total": 15,
    "page": 1,
    "pages": 1,
    "per_page": 50
  }
}
```

> **Frontend pattern:** The staff portal should poll `GET .../notifications/stats/` to show an unread badge count (from `data.unread`), and separately fetch the full list on notification drawer open.

---

## 11. Reliability, Timing, and Error Handling

### 11.1 Celery Beat Schedule (from WO settings.py)

| Task | Celery Task | Interval | Kafka Topic(s) | Consumer Group |
|---|---|---|---|---|
| Template registrations | `process_template_registrations` | **Every 10 seconds** | `notification-templates` | `work-orchestration-template-consumer` |
| Notification delivery | `process_notifications` | **Every 5 seconds** | `notifications-urgent/high/normal/low` + `notifications` | `work-orchestration-notification-consumer-v2` |
| Reminders | `process_reminders` | Every 60 seconds | Internal (DB) | — |
| Workflow events | `process_workflow_events` | Every 30 seconds | `workflow-events` | `workflow-automation-hooks` |

**Implications:**
- A template published at startup may take up to **10 seconds** to be available in WO
- A notification published by your service may take up to **5 seconds** to be delivered
- This is fire-and-forget async — your `send_notification()` call returns as soon as Kafka accepts the message

### 11.2 Consumer Commit Strategy

WO's `NotificationConsumer` uses **manual offset commits** (`enable.auto.commit: False`):

- Offsets are committed **after** a batch of messages is processed
- If processing fails for a message, its offset is **not committed** — it will be reprocessed on next poll
- This guarantees **at-least-once delivery** semantics
- **Consequence:** If your template renders correctly and email sends, but Kafka commit fails, the notification may be sent twice. The idempotency key in your event is the mitigation for this.

### 11.3 Dead Letter Queue (DLQ)

Failed events are written to the `notification-failed` Kafka topic with metadata:

```json
{
  "original_event": { ... },
  "error": "No active template found: grc.unsaved_template",
  "failed_at": "2026-03-07T10:30:00.000000Z"
}
```

**Common failures and causes:**

| Error Message | Cause | Fix |
|---|---|---|
| `"Notification event missing 'template_code' field"` | The `notification.template_code` key is absent | Fix publisher — ensure `template_code` is always set |
| `"No active template found: your.template.code"` | Template not yet registered, or registration failed | Check `notifications.yaml` and startup logs for `register_templates` result |
| `"No recipients specified in notification"` | `notification.recipients` is empty or missing | Fix publisher — always provide at least one recipient key |
| `"Template rendering failed: ..."` | Template body has a syntax error | Fix YAML body — check for unclosed `{% if %}` or malformed `{{}}` |
| `"All notification channels failed"` | SMTP / Infobip call failed | Infrastructure issue — check email/SMS configuration |

### 11.4 Error Handling in Your Publisher

WO failure is **non-blocking** — your service should not fail its own business transaction if notification publishing fails. The pattern:

```python
try:
    publisher = get_notification_publisher()
    publisher.send_email(
        template_code='grc.audit_plan.approved',
        to=[cia_email],
        context=context,
        priority='normal',
    )
except Exception as e:
    # Log but don't raise — notification failure should not block business action
    logger.error(f"Failed to publish approval notification: {e}", exc_info=True)
```

---

## 12. Complete Integration Checklist

Use this checklist for every new service or new notification you add.

### Step 1 — Define Your Templates

- [ ] Create `apps/core/templates/notifications.yaml`
- [ ] Each template has: `code`, `name`, `category`, `channels`, `subject`, `body_html`, `body_text`, `variables`, `metadata`
- [ ] Template codes follow `service-prefix.entity.action` convention (all dots, no hyphens)
- [ ] All template codes start with YOUR service prefix
- [ ] Reviewed `body_html` for correct `{{variable}}` syntax — no unclosed tags
- [ ] Reviewed `body_text` is the plain-text equivalent (no HTML tags)
- [ ] `metadata.priority` set to correct default (`urgent`/`high`/`normal`/`low`)

### Step 2 — Implement TemplateRegistry

- [ ] Create `apps/core/templates/registry.py` (copy from grc-service, change `service_name`)
- [ ] Registry reads `notifications.yaml` from same directory
- [ ] Registry publishes to `KAFKA_NOTIFICATION_TEMPLATES_TOPIC` (defaults to `notification-templates`)
- [ ] `register_templates()` is idempotent (safe to re-run on every deploy)

### Step 3 — Wire Startup Registration

- [ ] In `apps/core/apps.py` `ready()`: call `get_template_registry().register_templates()` in a daemon thread with 5-second delay
- [ ] Verified in dev logs that `"Registered N notification template(s)"` appears within 15 seconds of startup

### Step 4 — Implement NotificationPublisher

- [ ] Create `apps/core/notifications/publisher.py` (copy from grc-service, change `service_name`)
- [ ] Publisher targets correct priority topic based on `priority` argument
- [ ] `send_notification()`, `send_email()`, `send_sms()`, `send_in_app()` methods present
- [ ] Idempotency key generated correctly
- [ ] Publisher failure is non-blocking (wrapped in try/except in calling code)

### Step 5 — Add Kafka Settings

- [ ] `settings.py` has all 6 Kafka notification topic vars:
  ```python
  KAFKA_NOTIFICATIONS_TOPIC = os.getenv('KAFKA_NOTIFICATIONS_TOPIC', 'notifications')
  KAFKA_NOTIFICATIONS_URGENT_TOPIC = os.getenv('KAFKA_NOTIFICATIONS_URGENT_TOPIC', 'notifications-urgent')
  KAFKA_NOTIFICATIONS_HIGH_TOPIC = os.getenv('KAFKA_NOTIFICATIONS_HIGH_TOPIC', 'notifications-high')
  KAFKA_NOTIFICATIONS_NORMAL_TOPIC = os.getenv('KAFKA_NOTIFICATIONS_NORMAL_TOPIC', 'notifications-normal')
  KAFKA_NOTIFICATIONS_LOW_TOPIC = os.getenv('KAFKA_NOTIFICATIONS_LOW_TOPIC', 'notifications-low')
  KAFKA_NOTIFICATION_TEMPLATES_TOPIC = os.getenv('KAFKA_NOTIFICATION_TEMPLATES_TOPIC', 'notification-templates')
  ```
- [ ] `kafka-python` listed in `requirements.txt` (`kafka-python==2.0.2`)

### Step 6 — Call Publisher from Business Logic

- [ ] Every place that triggers a notification calls `get_notification_publisher().send_*()`
- [ ] Context dict resolves all display values before publishing (names from IAM lookup, formatted dates, staff portal URLs)
- [ ] Priority selected appropriately per event type
- [ ] If sending in-app, `user_ids` is present in BOTH `recipients` and `metadata`

### Step 7 — Verify End-to-End

- [ ] Start WO service alongside your service
- [ ] Trigger the business event
- [ ] Check WO Celery logs for `"Processed N notification event(s)"`
- [ ] Check WO DB: `SELECT code, status, version FROM notification_templates WHERE code LIKE 'your-prefix.%'`
- [ ] Check WO DB: `SELECT id, template_code, status FROM notification_delivery_logs ORDER BY created_at DESC LIMIT 10`
- [ ] Check in-app: `GET /api/v1/work-orchestration/notifications/` with a user JWT — should show new record

---

## 13. Anti-Patterns — What Not To Do

### ❌ Never send email directly from your service

```python
# WRONG — Direct Django email from your service
from django.core.mail import send_mail
send_mail(subject='...', message='...', recipient_list=['...'])

# CORRECT — Publish to Kafka, let WO deliver
publisher.send_email(template_code='...', to=['...'], context={...})
```

FIMS Architecture Principle 2 states WO is the sole authority for notification delivery. Direct SMTP from your service bypasses template management, delivery logging, and retry logic.

### ❌ Never call WO's REST endpoint to send email directly

There is a legacy REST endpoint `POST /api/v1/work-orchestration/notifications/email/send/` that sends email without a template. The client-service docs mark this as **legacy and being replaced**. Do **not** use it for new integrations. It bypasses the template system entirely.

### ❌ Never publish to WO's notification topics from a non-service context

The `notification.send` event must come from a backend service. Client-side code (frontend, browser) must never publish to Kafka directly.

### ❌ Never hard-code recipient email addresses in templates

Templates contain `{{variable}}` placeholders. Recipient addresses must be resolved by your service at runtime (lookup from IAM, extracted from your model) and passed in `recipients`. Templates must contain zero hard-coded email addresses.

### ❌ Never skip template registration and rely on manual DB seeding

Manually inserting `NotificationTemplateModel` records into WO's database bypasses versioning and will be overwritten on next deploy when your service re-registers. Always use the Kafka `template.registered` pipeline.

### ❌ Never block your transaction waiting for notification delivery

Notification publishing is fire-and-forget. The Kafka `producer.send()` is async. Do not `future.get()` with a long timeout in your business transaction path. The GRC pattern uses `future.get(timeout=10)` which is acceptable, but if Kafka is unreachable, gracefully degrade — do not fail the business action.

### ❌ Never nest loops or complex logic in template bodies

The `TemplateRenderer` does not support `{% for %}` loops. If you need to include a list (e.g., list of findings, list of team members), format it as a pre-rendered string in your context before publishing.

### ❌ Never include sensitive data in notification context

Context is stored in WO's `NotificationModel.metadata` as JSON. Do not include passwords, tokens, PII beyond names/emails, or file contents in the context dict.

---

## 14. End-to-End Flow Diagram

```
YOUR SERVICE                                    KAFKA                       WORK ORCHESTRATION
─────────────────────────────────────────────────────────────────────────────────────────────────

SERVICE STARTUP
apps.py.ready() → TemplateRegistry
    load notifications.yaml
    for each template:
        publish {event_type: "template.registered", template: {...}}
            ────────────────────────────────────────► notification-templates topic
                                                                    │
                                                                    ▼ (polled every 10s)
                                                          TemplateRegistrationConsumer
                                                          .consume_template_registered()
                                                          upsert NotificationTemplateModel
                                                          (code=unique key, version++)


BUSINESS EVENT (e.g., audit plan approved)
use_case → notify CIA + IA reviewer

    1. Look up CIA email + user_id from IAM service (REST call)
    2. Look up IA email + user_id from IAM service (REST call)
    3. Build context dict (plan data, approver name, detail URL)

    NotificationPublisher.send_notification(
        template_code = 'grc.audit_plan.approved',
        recipients    = {'email': [cia@, ia@], 'user_ids': [uuid1, uuid2]},
        context       = {'audit_plan': {...}, 'approver': {...}, ...},
        priority      = 'normal'
    )
        publish {event_type: "notification.send", notification: {...}}
            ────────────────────────────────────────► notifications-normal topic
                                                                    │
                                                                    ▼ (polled every 5s)
                                                          NotificationConsumer
                                                          .consume_notification_send()
                                                          
                                                          1. lookup template by code
                                                             ← NotificationTemplateModel
                                                          
                                                          2. render subject with context
                                                             "RBIAP-001 Approved" 
                                                          
                                                          3. render body_html with context
                                                             full HTML email body
                                                          
                                                          4. render body_text with context
                                                             plain text body
                                                          
                                                          5a. deliver EMAIL
                                                              NotificationClient.send_email_notification()
                                                              │
                                                              └─► Django send_mail()
                                                                  │
                                                                  └─► SMTP server
                                                                      ─► cia@fcc.go.tz ✓
                                                                      ─► ia@fcc.go.tz ✓
                                                          
                                                          5b. create IN-APP records
                                                              NotificationModel.objects.create(
                                                                  user_id = uuid1 (CIA)
                                                                  title   = rendered subject
                                                                  message = rendered body_text
                                                                  read    = False
                                                              )
                                                              NotificationModel.objects.create(
                                                                  user_id = uuid2 (IA)
                                                                  ...
                                                              )
                                                          
                                                          6. commit Kafka offset


FRONTEND (Staff Portal)
    page load → GET /api/v1/work-orchestration/notifications/stats/
        ← {"data": {"total": 3, "unread": 1, "read": 2}}
        → show badge "1" on bell icon

    click bell → GET /api/v1/work-orchestration/notifications/
        ← list of NotificationModel records for user
        → show notification panel

    click notification → PATCH /api/v1/work-orchestration/notifications/{id}/
        body: {"read": true}
        ← updated record
        → mark as read in UI
```

---

*This document was derived by direct code analysis of `work-orchestration-service` and the `grc-service` reference implementation. All patterns, field names, topic names, timing values, and event structures are based on actual production code.*
