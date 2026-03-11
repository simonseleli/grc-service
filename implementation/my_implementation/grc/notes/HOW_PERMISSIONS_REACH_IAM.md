# How GRC Permissions Automatically Reach IAM

## Simple Explanation

Think of it like a restaurant:
- **GRC service** is the **kitchen** — it knows what dishes (permissions) it can make
- **Kafka** is the **waiter** — it carries the message
- **IAM service** is the **menu board** — it displays and stores what's available

Every time the kitchen opens (GRC starts), it tells the waiter the full menu, and the waiter updates the board automatically.

---

## The 3 Files Involved on GRC Side

### 1. `grc-service/config/permissions/grc-service.json`
This is the **source of truth** — a plain JSON file listing all 34 permissions with their codes, names, and categories.

```
grc:audit_plan:view
grc:audit_plan:manage
grc:audit_plan:approve
... (31 more)
```

Nobody writes these into the database manually. The JSON file is the master list.

---

### 2. `grc-service/apps/core/apps.py`
This is the **startup hook** — Django calls `ready()` automatically every time the GRC service boots.

```python
def ready(self):
    # Django calls this automatically on every startup
    self._register_permissions_on_startup()
```

Think of `ready()` as "what should I do when I wake up?" — GRC answers: publish my permissions.

---

### 3. `grc-service/apps/core/kafka_permission_publisher.py`
This is the **sender** — it reads the JSON file and sends all permissions as a Kafka message.

```python
# Sends this message to Kafka topic: "service.permission.registry"
{
    "event_type": "service_permission_registration",
    "source_service": "grc-service",
    "data": {
        "permissions": [ ...all 34 from JSON... ]
    }
}
```

---

## The 1 File Involved on IAM Side

### `iam-service/apps/roles/kafka_consumer.py`
This is the **receiver** — IAM runs a background process that listens to the `service.permission.registry` topic 24/7.

When a message arrives from GRC, IAM saves each permission into its database table (`unified_service_permissions`), creating or updating rows. It never overwrites roles or user assignments — only the permission catalog.

---

## Full Flow (Simple)

```
GRC service boots
    │
    ▼
apps/core/apps.py → ready()
    │
    ▼
reads grc-service.json (34 permissions)
    │
    ▼
sends message to Kafka topic "service.permission.registry"
    │
    ▼  (Kafka delivers it)
    │
    ▼
IAM's kafka consumer receives the message
    │
    ▼
saves all 34 permissions into IAM database
```

That's it. No manual step needed. Restart GRC → permissions update in IAM automatically.

---

## What Triggers It

| Trigger | Does it publish? |
|---|---|
| `docker compose up grc-service` | ✅ Yes — gunicorn starts Django, `ready()` fires |
| `docker restart fims-grc-service` | ✅ Yes — same |
| `python manage.py migrate` | ❌ No — guarded as "build command" |
| `python manage.py shell` | ❌ No — same guard |
| `python manage.py collectstatic` | ❌ No — same guard |

The guard exists because during migrations there is no Kafka connection yet — it would crash. The code in `apps.py` checks `_is_build_command()` and skips Kafka if you're running one of those commands.

---

## Why Old Non-Prefixed Permissions Appeared

Kafka stores every message ever sent in its topic log. When IAM's consumer starts fresh, it reads from the **beginning of the log** (`auto_offset_reset='earliest'`), including old messages from before the `grc:` prefix was added to permission codes.

The JSON file was already corrected (all 34 use `grc:` prefix), but the old messages from the previous version were still sitting in Kafka's history. IAM re-consumed them and created duplicate entries without the prefix.

**Fix:** Delete the non-prefixed orphans from IAM DB directly (already done). The cleanup script is in `USER_AND_ROLE_SETUP.md` if it happens again.
