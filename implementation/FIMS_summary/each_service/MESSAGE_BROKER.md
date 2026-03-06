# Message Broker — Deep Architectural Reference

> **Component:** FIMS Message Broker (Apache Kafka + Zookeeper)  
> **Image:** `confluentinc/cp-kafka:7.4.0` / `confluentinc/cp-zookeeper:7.4.0`  
> **Kafka Hostname:** `fims-kafka` (Docker DNS)  
> **Ports:** 9092 (primary PLAINTEXT), 29092 (internal PLAINTEXT)  
> **Zookeeper:** `zookeeper:2181`  
> **Schema Registry:** `schema-registry:8081`  
> **Kafka UI:** `fims-kafka-ui` (port configurable, default 9093)  
> **Network:** `fims-network` (external Docker bridge)

---

## Table of Contents

1. [Role Within FIMS](#1-role-within-fims)
2. [Infrastructure Components](#2-infrastructure-components)
3. [Docker Compose Configuration](#3-docker-compose-configuration)
4. [Kafka Broker Configuration](#4-kafka-broker-configuration)
5. [Complete Topic Registry](#5-complete-topic-registry)
6. [Per-Service Kafka Usage](#6-per-service-kafka-usage)
7. [Consumer Group Registry](#7-consumer-group-registry)
8. [Client Library Usage](#8-client-library-usage)
9. [Event Envelope Standards](#9-event-envelope-standards)
10. [Topic Initialization Scripts](#10-topic-initialization-scripts)
11. [Networking & Connectivity](#11-networking--connectivity)
12. [Environment Variables](#12-environment-variables)
13. [Operational Procedures](#13-operational-procedures)
14. [Known Issues & Architectural Notes](#14-known-issues--architectural-notes)
15. [Integration Guide for New Services](#15-integration-guide-for-new-services)
16. [Architectural Boundaries](#16-architectural-boundaries)

---

## 1. Role Within FIMS

The message broker is the **central nervous system** for asynchronous inter-service communication. It provides:

1. **Permission Registration Pipeline** — Every domain service publishes its permission definitions to IAM via Kafka, enabling decentralized permission authoring with centralized enforcement.

2. **Workflow Event Streaming** — Work-orchestration-service publishes workflow state changes (plan started, stage updated, plan completed) that other services consume to react to orchestration outcomes.

3. **Notification Delivery Pipeline** — All services publish notification events to priority-based topics. Work-orchestration-service consumes these, renders templates, and delivers via email/SMS/in-app/webhook.

4. **Notification Template Registration** — Services register their notification templates via Kafka so work-orchestration-service can store, version, and render them.

5. **Domain Event Broadcasting** — Services publish business events (document created, client registered, etc.) for loose coupling and eventual-consistency patterns.

The broker does **not** handle authentication, business logic, or data storage beyond Kafka's own log retention.

---

## 2. Infrastructure Components

### 2.1 Zookeeper

| Attribute | Value |
|---|---|
| **Image** | `confluentinc/cp-zookeeper:7.4.0` |
| **Container** | `fims-zookeeper` |
| **Port** | 2181 |
| **Purpose** | Kafka broker coordination, leader election, configuration management |
| **Health Check** | `nc -z localhost 2181` (every 30s, 3 retries) |
| **Volumes** | `zookeeper_data:/var/lib/zookeeper/data`, `zookeeper_logs:/var/lib/zookeeper/log` |

Configuration:
- `ZOOKEEPER_CLIENT_PORT`: 2181
- `ZOOKEEPER_TICK_TIME`: 2000ms
- `ZOOKEEPER_LOG4J_LOGGERS`: `org.apache.zookeeper=WARN`

### 2.2 Apache Kafka

| Attribute | Value |
|---|---|
| **Image** | `confluentinc/cp-kafka:7.4.0` |
| **Container** | `fims-kafka` |
| **Hostname** | `fims-kafka` (used by all services for Docker DNS) |
| **Ports** | 9092 (PLAINTEXT), 29092 (PLAINTEXT_INTERNAL) |
| **Broker ID** | 1 (single-broker deployment) |
| **Health Check** | `kafka-broker-api-versions --bootstrap-server localhost:9092` (every 30s) |
| **Volumes** | `kafka_data:/var/lib/kafka/data`, `kafka_logs:/var/log/kafka` |

### 2.3 Schema Registry

| Attribute | Value |
|---|---|
| **Image** | `confluentinc/cp-schema-registry:7.4.0` |
| **Container** | `fims-schema-registry` |
| **Port** | 8081 |
| **Purpose** | Schema management for Kafka messages (available but not actively enforced by services) |
| **Bootstrap** | Connects to `fims-kafka:9092` |

### 2.4 Kafka UI

| Attribute | Value |
|---|---|
| **Image** | `provectuslabs/kafka-ui:latest` |
| **Container** | `fims-kafka-ui` |
| **Port** | Configurable via `KAFKA_UI_PORT` (default 9093) |
| **Purpose** | Web-based admin interface for topic inspection, consumer groups, message browsing |
| **Cluster Name** | `fims-cluster` |
| **Dynamic Config** | Enabled |

---

## 3. Docker Compose Configuration

### 3.1 Development (`docker-compose.yml`)

4 services: `zookeeper`, `kafka`, `kafka-ui`, `schema-registry`

**Key development-specific settings:**
- Kafka ports published to host: `9092:9092`, `29092:29092`
- Schema Registry port published: `8081:8081`
- JVM heap tuned for dev: `-Xmx512m -Xms256m`
- G1GC with `MaxGCPauseMillis=20`, `InitiatingHeapOccupancyPercent=35`

### 3.2 Production (`docker-compose.prod.yml`)

Same 4 services with differences:
- No published ports (Kafka only accessible within `fims-network`)
- No JVM heap overrides (relies on container memory limits)
- Same `fims-network` external network

### 3.3 Shared Configuration

All compose files:
- `restart: unless-stopped` for all services
- Kafka depends on Zookeeper with `condition: service_healthy`
- All services on `fims-network` (external)
- Named Docker volumes for data persistence

---

## 4. Kafka Broker Configuration

### 4.1 Listener Configuration

```
KAFKA_LISTENERS:            PLAINTEXT://0.0.0.0:9092, PLAINTEXT_INTERNAL://0.0.0.0:29092
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://fims-kafka:9092, PLAINTEXT_INTERNAL://fims-kafka:29092
```

- **PLAINTEXT (9092)** — Primary listener, used by all services via `fims-kafka:9092`
- **PLAINTEXT_INTERNAL (29092)** — Secondary internal listener (available but services use 9092)
- **Security:** Both listeners use `PLAINTEXT` protocol (no encryption or auth)
- **Inter-broker:** Uses `PLAINTEXT` listener

### 4.2 Topic Management

| Setting | Value | Notes |
|---|---|---|
| `KAFKA_AUTO_CREATE_TOPICS_ENABLE` | `true` | Topics auto-created on first produce/consume |
| `KAFKA_DELETE_TOPIC_ENABLE` | `true` | Topics can be deleted via admin tools |
| `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` | 1 | Single-broker setup |
| `KAFKA_TRANSACTION_STATE_LOG_MIN_ISR` | 1 | Single-broker setup |
| `KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR` | 1 | Single-broker setup |
| `KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS` | 0 | Instant rebalance (dev-friendly) |

### 4.3 JVM Configuration (Development)

```
KAFKA_HEAP_OPTS: -Xmx512m -Xms256m
KAFKA_JVM_PERFORMANCE_OPTS: -XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35
```

Tuned to prevent OOM kills on developer machines with limited RAM.

---

## 5. Complete Topic Registry

### 5.1 Active Topics (Verified Producer + Consumer)

These topics have confirmed producers AND consumers in the codebase:

| # | Topic | Producers | Consumers | Partitions | Purpose |
|---|---|---|---|---|---|
| 1 | `service.permission.registry` | doc-records, client, work-orchestration | iam-service (2 consumer groups) | 3 | Permission registration pipeline |
| 2 | `workflow-events` | work-orchestration | doc-records (2 consumer groups), work-orchestration (automation) | 3 | Workflow state changes |
| 3 | `notification-templates` | iam, doc-records, client | work-orchestration | 3 | Template registration |
| 4 | `notifications` | iam, doc-records, client | work-orchestration | 3 | Default/fallback notifications |
| 5 | `notifications-urgent` | iam, doc-records, client | work-orchestration | 3 | Urgent priority notifications |
| 6 | `notifications-high` | iam, doc-records, client | work-orchestration | 3 | High priority notifications |
| 7 | `notifications-normal` | iam, doc-records, client | work-orchestration | 3 | Normal priority notifications |
| 8 | `notifications-low` | iam, doc-records, client | work-orchestration | 3 | Low priority notifications |

### 5.2 Producer-Only Topics (No Active Consumers Found)

These topics are actively produced to but have no confirmed consumers in the scanned codebase:

| # | Topic | Producer | Notes |
|---|---|---|---|
| 9 | `notification-failed` | work-orchestration (DLQ) | Dead Letter Queue — monitoring/alerting only |
| 10 | `user.events` | iam-service (shared producer) | Generic user event topic |
| 11 | `user.created` | iam-service (messaging_service) | Fine-grained user lifecycle |
| 12 | `user.updated` | iam-service (messaging_service) | Fine-grained user lifecycle |
| 13 | `user.deleted` | iam-service (messaging_service) | Fine-grained user lifecycle |
| 14 | `user.login` | iam-service (messaging_service) | User activity tracking |
| 15 | `user.logout` | iam-service (messaging_service) | User activity tracking |
| 16 | `document.events` | iam-service (shared producer) | Generic document event topic |
| 17 | `audit.events` | iam-service (messaging_service) | Audit trail events |
| 18 | `fims.documents.*` (dynamic) | doc-records (EventPublisher) | Pattern: `fims.documents.{event_type}` |
| 19 | `corporate.events` | corporate-service (stub) | Corporate domain events (Phase 1 stub) |
| 20 | `client-service.entity.events` | client-service | Client entity changes |
| 21 | `client-service.user.events` | client-service | Client user changes |
| 22 | `client-service.entity.user.events` | client-service | Client entity-user association events |

### 5.3 Consumer-Only Topics (Expected from External/Unscanned Services)

| # | Topic | Consumer | Expected Producer |
|---|---|---|---|
| 23 | `fims.iam.user.updated` | doc-records | iam-service (not yet producing to this exact name) |
| 24 | `fims.work.task.created` | doc-records | work-orchestration (not yet producing to this exact name) |
| 25 | `application-service.application.created` | client-service | application-service (not yet built) |
| 26 | `application-service.application.status_changed` | client-service | application-service (not yet built) |
| 27 | `finance-service.payment.completed` | client-service | finance-service (not yet built) |

### 5.4 Dynamic Topic Patterns

**Document Records Service** generates topics dynamically from domain events:

```python
# apps/core/events/base.py
@property
def topic(self) -> str:
    return f"fims.documents.{self.event_type.lower().replace('_', '.')}"
```

This creates topics like:
- `fims.documents.document.created`
- `fims.documents.document.updated`
- `fims.documents.document.deleted`
- `fims.documents.document.archived`
- `fims.documents.disposal.form.created`
- etc.

### 5.5 Planned Topics (From kafka-topics.sh Script)

The `config/kafka-topics.sh` script defines **60+ provisioning topics** based on the system design document. Most are not yet active. Categories include:

| Category | Example Topics | Status |
|---|---|---|
| User Management | `user.created`, `user.updated`, `user.deleted` | Partially active (IAM produces) |
| Document Workflow | `document.uploaded`, `document.approved` | Superseded by `fims.documents.*` pattern |
| Client Management | `client.registered`, `client.verified` | Superseded by `client-service.*` topics |
| Competition Regulation | `merger.application.submitted` | Not yet active |
| Restrictive Trade | `trade.practice.reported` | Not yet active |
| Anti-Counterfeits | `counterfeit.report.received` | Not yet active |
| Commission | `commission.meeting.scheduled` | Not yet active |
| Finance | `payment.received`, `expense.approved` | Not yet active |
| Research | `research.project.started` | Not yet active |
| Publications | `publication.created` | Not yet active |
| Governance | `policy.created`, `compliance.audit.started` | Not yet active |
| Notifications | `notification.sent`, `email.sent` | Superseded by priority-based topics |
| ICTSM | `system.health.check` | Not yet active |
| GovESB | `integration.request.received` | Not yet active |
| Audit | `audit.log.created`, `security.breach.detected` | Not yet active |
| System | `service.started`, `service.stopped` | Not yet active |
| Workflow | `workflow-events`, `service.permission.registry` | **Active** |

---

## 6. Per-Service Kafka Usage

### 6.1 IAM Service

| Role | Topics |
|---|---|
| **Produces to** | `service.permission.registry` (consumed by self), `notification-templates`, `notifications-*` (all priority), `notifications`, `user.events`, `user.created/updated/deleted/login/logout`, `document.events`, `audit.events` |
| **Consumes from** | `service.permission.registry` |
| **Client Library** | `kafka-python==2.0.2` only |
| **Client ID** | `iam-service` |

### 6.2 Document Records Service

| Role | Topics |
|---|---|
| **Produces to** | `service.permission.registry`, `notification-templates`, `notifications-*` (all priority), `notifications`, `fims.documents.*` (dynamic) |
| **Consumes from** | `workflow-events`, `fims.iam.user.updated`, `fims.work.task.created` |
| **Client Libraries** | **Both** `confluent-kafka==2.3.0` AND `kafka-python==2.0.2` |
| **Client ID** | `document-records-service` |

### 6.3 Work Orchestration Service

| Role | Topics |
|---|---|
| **Produces to** | `workflow-events`, `service.permission.registry`, `notification-failed` (DLQ) |
| **Consumes from** | `workflow-events`, `notification-templates`, `notifications-urgent/high/normal/low`, `notifications` |
| **Client Libraries** | **Both** `confluent-kafka==2.3.0` AND `kafka-python==2.0.2` |
| **Client ID** | `work-orchestration-service` |

### 6.4 Client Service

| Role | Topics |
|---|---|
| **Produces to** | `service.permission.registry`, `notification-templates`, `notifications-*` (all priority), `notifications`, `client-service.entity.events`, `client-service.user.events`, `client-service.entity.user.events` |
| **Consumes from** | `application-service.application.created`, `application-service.application.status_changed`, `finance-service.payment.completed` |
| **Client Libraries** | `kafka-python==2.0.2` (primary), `confluent-kafka==2.3.0` in requirements |
| **Client ID** | `client-service` |

### 6.5 Corporate Service

| Role | Topics |
|---|---|
| **Produces to** | `corporate.events` (stub/Phase 1 — logs only) |
| **Consumes from** | *(none)* |
| **Client Library** | `confluent-kafka==2.3.0` (stub producer) |

---

## 7. Consumer Group Registry

| Consumer Group ID | Service | Topic(s) Consumed | Library |
|---|---|---|---|
| `iam-permission-consumer-group` | iam-service | `service.permission.registry` | kafka-python |
| `iam-unified-permission-consumer-group` | iam-service | `service.permission.registry` | kafka-python |
| `document-records-consumer` | document-records | `fims.iam.user.updated`, `fims.work.task.created`, `workflow-events` | confluent-kafka |
| `document-service-workflow-consumer` | document-records | `workflow-events` | kafka-python |
| `workflow-automation-hooks` | work-orchestration | `workflow-events` | confluent-kafka |
| `work-orchestration-notification-consumer-v2` | work-orchestration | `notifications-*` (all 5 topics) | confluent-kafka |
| `work-orchestration-template-consumer` | work-orchestration | `notification-templates` | confluent-kafka |
| `client-service-consumer-group` | client-service | application/finance events | kafka-python |

### Notable Multi-Consumer Patterns

**`service.permission.registry`** — IAM has **two independent consumer groups**:
- `iam-permission-consumer-group` (`apps/permissions/kafka_consumer.py`)
- `iam-unified-permission-consumer-group` (`apps/roles/kafka_consumer.py`)

Both receive every message independently. This is intentional — they serve different permission processing pipelines.

**`workflow-events`** — Three consumer groups across two services:
- `document-records-consumer` (doc-records, confluent-kafka)
- `document-service-workflow-consumer` (doc-records, kafka-python)
- `workflow-automation-hooks` (work-orchestration, confluent-kafka)

Document-records has two consumers for the same topic in different consumer groups, meaning each processes all messages independently.

---

## 8. Client Library Usage

### 8.1 Library Matrix

| Service | `kafka-python` | `confluent-kafka` | Primary |
|---|---|---|---|
| iam-service | Yes | No | kafka-python |
| document-records-service | Yes | Yes | Mixed |
| work-orchestration-service | Yes | Yes | Mixed |
| client-service | Yes | Yes (installed) | kafka-python |
| corporate-service | No | Yes | confluent-kafka |

### 8.2 Usage Patterns

**`kafka-python` (class: `KafkaProducer`, `KafkaConsumer`):**
- Used for permission publishers (`kafka_permission_publisher.py`)
- Used for notification publishers (`NotificationPublisher`)
- Used for template registries (`TemplateRegistry`)
- Used in IAM's `messaging_service.py` for all event types
- Used in `shared/common/messaging/` producers

**`confluent-kafka` (class: `confluent_kafka.Producer`, `confluent_kafka.Consumer`):**
- Used for infrastructure-level messaging (`apps/infrastructure/messaging/`)
- Used for work-orchestration's notification consumer and template consumer
- Used for document-records' event publisher and domain consumer
- Generally used for higher-throughput, lower-level messaging

### 8.3 Dual-Library Note

Three services (document-records, work-orchestration, client) have **both libraries installed**. Within each service, different modules use different libraries. This arose organically — `kafka-python` was used first for cross-cutting concerns (permissions, notifications), while `confluent-kafka` was adopted later for infrastructure-level consumers needing finer control (manual offset commits, poll-based consumption, delivery reports).

---

## 9. Event Envelope Standards

### 9.1 Standard Domain Event Envelope

```json
{
  "id": "uuid-v4",
  "type": "event.type.name",
  "timestamp": "2026-02-24T10:00:00.000Z",
  "service": "source-service-name",
  "version": "1.0",
  "data": { ... }
}
```

### 9.2 Notification Request Envelope

```json
{
  "event_type": "notification_request",
  "event_version": "1.0",
  "timestamp": "2026-02-24T10:00:00Z",
  "source_service": "document-service",
  "notification_id": "uuid-v4",
  "idempotency_key": "template_code-recipient-timestamp_minute",
  "data": {
    "template_code": "document.approval.request",
    "priority": "normal",
    "recipients": {
      "email": ["user@example.com"],
      "sms": ["+255123456789"],
      "user_ids": ["uuid"]
    },
    "context": {
      "document": { "id": "...", "title": "...", "reference_number": "..." }
    }
  }
}
```

### 9.3 Template Registration Envelope

```json
{
  "event_type": "template.registered",
  "source_service": "document-records-service",
  "source_version": "1.0.0",
  "timestamp": "2026-02-24T12:00:00Z",
  "template": {
    "code": "document.approval.request",
    "name": "Document Approval Request",
    "category": "document",
    "channels": ["email", "in_app"],
    "subject": "Approval Required: {{document.title}}",
    "body_html": "<p>...</p>",
    "body_text": "...",
    "variables": ["document.title", "document.reference"],
    "metadata": { "priority": "normal" }
  }
}
```

### 9.4 Permission Registration Envelope

```json
{
  "event_type": "service_permission_registration",
  "source_service": "document-records-service",
  "source_version": "1.0.0",
  "timestamp": "2026-02-24T12:00:00Z",
  "data": {
    "service": {
      "name": "document-records-service",
      "version": "1.0.0",
      "description": "..."
    },
    "permissions": [
      {
        "permission_code": "document.read",
        "name": "Read Document",
        "description": "...",
        "resource_type": "document",
        "action": "read",
        "category": "document_management"
      }
    ]
  }
}
```

### 9.5 Workflow Event Envelope

```json
{
  "event_type": "WorkflowStageUpdated",
  "plan_id": "uuid",
  "stage_id": "uuid",
  "workflow_type": "approval",
  "action": "approve",
  "actor_id": "uuid",
  "new_status": "completed",
  "form_data": { ... },
  "metadata": { ... },
  "timestamp": "2026-02-24T12:00:00Z"
}
```

### 9.6 Serialization

- All events serialized as **JSON** with UTF-8 encoding
- Kafka message keys: typically `None` or service-specific (e.g., plan_id for workflow events)
- No Avro/Protobuf schemas enforced (Schema Registry available but not actively used)

---

## 10. Topic Initialization Scripts

### 10.1 Full Topic Provisioning (`config/kafka-topics.sh`)

Provisions **60+ topics** across all planned FIMS domains. Designed to be run once against a fresh Kafka instance. Uses `docker exec fims-dev-kafka` — note the `fims-dev-kafka` container name (development environment naming).

Categories provisioned:
- User Management (6 topics)
- Document Workflow (6 topics)
- Client Management (5 topics)
- Competition Regulation (6 topics)
- Restrictive Trade Practices (4 topics)
- Anti-Counterfeits (4 topics)
- Commission Management (4 topics)
- Finance (6 topics)
- Research (4 topics)
- Publications (4 topics)
- Resource Management (4 topics)
- Governance (6 topics)
- Notifications (5 topics)
- ICTSM (4 topics)
- GovESB (5 topics)
- Audit (3 topics)
- System (4 topics)
- Workflow Orchestration (2 topics)

**Default partitions:** 3 per topic  
**Default replication:** 1 (single-broker)

### 10.2 Critical Topic Bootstrap (`config/create-workflow-topic.sh`)

Ensures the two most critical topics exist, even if the full script hasn't been run:

1. `workflow-events` — 3 partitions, replication factor 1
2. `service.permission.registry` — 3 partitions, replication factor 1

Features:
- Waits up to 60 seconds for Kafka readiness (polls every 2s, max 30 attempts)
- Idempotent (checks if topic already exists before creating)
- Designed to run inside the Kafka container (`kafka-topics.sh` local binary)

---

## 11. Networking & Connectivity

### 11.1 Docker Network

All message broker components and all FIMS services share the **`fims-network`** external Docker bridge network.

```
┌─ fims-network ──────────────────────────────────────────┐
│                                                          │
│  ┌─────────────┐     ┌─────────────┐                    │
│  │ zookeeper   │◄────│ fims-kafka  │                    │
│  │ :2181       │     │ :9092/29092 │                    │
│  └─────────────┘     └──────┬──────┘                    │
│                             │                            │
│           ┌─────────────────┼────────────────┐          │
│           │                 │                │          │
│  ┌────────┴───┐  ┌─────────┴────┐  ┌────────┴───┐     │
│  │ schema-    │  │ kafka-ui     │  │ All FIMS   │     │
│  │ registry   │  │ :9093        │  │ services   │     │
│  │ :8081      │  │              │  │ connect to │     │
│  └────────────┘  └──────────────┘  │ fims-kafka │     │
│                                     │ :9092      │     │
│                                     └────────────┘     │
└──────────────────────────────────────────────────────────┘
```

### 11.2 Service Connection Pattern

Every FIMS service connects to Kafka using:
```python
KAFKA_BOOTSTRAP_SERVERS = 'fims-kafka:9092'
```

This resolves via Docker DNS to the Kafka container's IP on `fims-network`.

### 11.3 Advertised Listeners

```
PLAINTEXT://fims-kafka:9092
PLAINTEXT_INTERNAL://fims-kafka:29092
```

Both advertised listeners use `fims-kafka` (the container hostname), which is correct for Docker-internal communication. Services resolve this via Docker DNS.

**Important:** The advertised listeners do NOT use `localhost` — this is critical. Kafka clients receive the advertised listener address after initial connection and use it for subsequent communication. Using `localhost` would break inter-container connectivity.

---

## 12. Environment Variables

### 12.1 Zookeeper

| Variable | Default | Purpose |
|---|---|---|
| `ZOOKEEPER_PORT` | 2181 | Host-published port |
| `ZOOKEEPER_CLIENT_PORT` | 2181 | Internal client port |
| `ZOOKEEPER_TICK_TIME` | 2000 | Base time unit in milliseconds |
| `ZOOKEEPER_LOG4J_LOGGERS` | `org.apache.zookeeper=WARN` | Log level |

### 12.2 Kafka

| Variable | Default | Purpose |
|---|---|---|
| `KAFKA_PORT` | 9092 | Host-published primary port |
| `KAFKA_PORT_INTERNAL` | 29092 | Host-published internal port |
| `KAFKA_BROKER_ID` | 1 | Broker identifier |
| `KAFKA_ZOOKEEPER_CONNECT` | `zookeeper:2181` | Zookeeper connection |
| `KAFKA_AUTO_CREATE_TOPICS_ENABLE` | `true` | Auto-create topics on first use |
| `KAFKA_DELETE_TOPIC_ENABLE` | `true` | Allow topic deletion |
| `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` | 1 | Single-broker setup |
| `KAFKA_TRANSACTION_STATE_LOG_MIN_ISR` | 1 | Single-broker setup |
| `KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR` | 1 | Single-broker setup |
| `KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS` | 0 | Instant rebalance |
| `KAFKA_JMX_PORT` | 9101 | JMX monitoring port |
| `KAFKA_JMX_HOSTNAME` | `localhost` | JMX hostname |

### 12.3 Kafka UI

| Variable | Default | Purpose |
|---|---|---|
| `KAFKA_UI_PORT` | 9093 | Host-published web UI port |
| `KAFKA_CLUSTERS_0_NAME` | `fims-cluster` | Cluster display name |
| `KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS` | `fims-kafka:9092` | Kafka connection |
| `KAFKA_CLUSTERS_0_ZOOKEEPER` | `zookeeper:2181` | Zookeeper connection |
| `DYNAMIC_CONFIG_ENABLED` | `true` | Allow config changes via UI |

### 12.4 Schema Registry

| Variable | Default | Purpose |
|---|---|---|
| `SCHEMA_REGISTRY_PORT` | 8081 | Host-published port |
| `SCHEMA_REGISTRY_HOST_NAME` | `schema-registry` | Hostname |
| `SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS` | `fims-kafka:9092` | Kafka connection |
| `SCHEMA_REGISTRY_LISTENERS` | `http://0.0.0.0:8081` | HTTP listener |

---

## 13. Operational Procedures

### 13.1 Starting the Broker

```bash
cd message-broker
docker compose up -d
```

Startup order (enforced by `depends_on`):
1. Zookeeper starts and becomes healthy (port 2181 check)
2. Kafka starts and connects to Zookeeper
3. Schema Registry and Kafka UI start

### 13.2 Verifying Health

```bash
# Check all containers running
docker compose ps

# Test Kafka connectivity
docker exec fims-kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# List topics
docker exec fims-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check consumer groups
docker exec fims-kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list
```

### 13.3 Creating Topics Manually

```bash
docker exec fims-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create \
  --topic my-new-topic \
  --partitions 3 \
  --replication-factor 1 \
  --if-not-exists
```

### 13.4 Inspecting Consumer Group Lag

```bash
docker exec fims-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group work-orchestration-notification-consumer-v2 \
  --describe
```

### 13.5 Browsing Messages

```bash
# Read from beginning
docker exec fims-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic workflow-events \
  --from-beginning \
  --max-messages 10

# Read latest
docker exec fims-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic service.permission.registry \
  --timeout-ms 5000
```

### 13.6 Producing Test Messages

```bash
echo '{"type":"test","data":"hello"}' | docker exec -i fims-kafka kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic workflow-events
```

### 13.7 Full Reset (Delete All Data)

```bash
docker compose down -v
docker compose up -d
```

**Warning:** This destroys all Kafka data, consumer offsets, and topic configurations.

### 13.8 Provisioning All Topics

```bash
# Run the full topic creation script
docker exec fims-kafka bash /path/to/kafka-topics.sh

# Or just the critical topics
docker exec fims-kafka bash /path/to/create-workflow-topic.sh
```

---

## 14. Known Issues & Architectural Notes

### 14.1 Dual Kafka Library Usage

Three services (document-records, work-orchestration, client) have **both** `kafka-python` and `confluent-kafka` installed. Different modules within the same service use different libraries:
- `kafka-python`: Used for permissions, notifications, templates (cross-cutting concerns)
- `confluent-kafka`: Used for infrastructure-level consumers/producers (finer control)

**Risk:** Configuration drift between the two libraries (e.g., different serialization defaults, different error handling). Not a correctness issue, but a maintenance concern.

### 14.2 Duplicate Consumers on Same Topics

**`service.permission.registry`** — IAM has two independent consumer groups, both processing every message:
- `iam-permission-consumer-group`
- `iam-unified-permission-consumer-group`

**`workflow-events`** — Document-records has two independent consumer groups:
- `document-records-consumer` (confluent-kafka)
- `document-service-workflow-consumer` (kafka-python)

This means permission and workflow messages are processed twice by the same service. This is functional (separate processing pipelines) but may indicate consolidation opportunities.

### 14.3 Orphan Topics

Several IAM-produced topics (`user.events`, `user.created/updated/deleted`, `document.events`, `audit.events`) have **no consumers** in any scanned service. These exist for future integration or monitoring purposes.

### 14.4 Topic Name Mismatches

- Document-records consumes `fims.iam.user.updated` but IAM produces to `user.updated` and `user.events` — **name mismatch**
- Document-records consumes `fims.work.task.created` but work-orchestration produces to `workflow-events` — **name mismatch**

These consumer subscriptions will receive no messages until the producers adopt the expected topic names, or the consumers are updated.

### 14.5 Schema Registry Underutilized

The Confluent Schema Registry is deployed but no service enforces Avro, Protobuf, or JSON Schema validation. All events are plain JSON. The registry is available for future schema evolution enforcement.

### 14.6 Single-Broker Deployment

The current setup uses a single Kafka broker (broker ID 1) with replication factor 1. This is appropriate for development but provides:
- **No fault tolerance** — broker failure loses availability
- **No data redundancy** — partition data exists on one node only
- **No ISR-based safety** — min ISR is 1

For production, consider multi-broker deployment with replication factor ≥ 2.

### 14.7 No Authentication/Encryption

All Kafka listeners use `PLAINTEXT` protocol. There is:
- No SASL authentication
- No TLS encryption
- No ACLs (Access Control Lists)

Acceptable for Docker-internal communication where the network boundary is the trust boundary. For production with external access, SASL_SSL should be considered.

---

## 15. Integration Guide for New Services

### Step 1: Add Kafka Dependency

In `requirements.txt`:
```
kafka-python==2.0.2
```

Or for confluent-kafka (recommended for consumers needing poll-based control):
```
confluent-kafka==2.3.0
```

### Step 2: Configure Settings

```python
# config/settings.py

# Kafka Connection
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'fims-kafka:9092')

# Permission Registration
KAFKA_PERMISSION_TOPIC = 'service.permission.registry'

# Notification Publishing
KAFKA_NOTIFICATION_TEMPLATES_TOPIC = 'notification-templates'
KAFKA_NOTIFICATIONS_TOPIC = 'notifications'
KAFKA_NOTIFICATIONS_URGENT_TOPIC = 'notifications-urgent'
KAFKA_NOTIFICATIONS_HIGH_TOPIC = 'notifications-high'
KAFKA_NOTIFICATIONS_NORMAL_TOPIC = 'notifications-normal'
KAFKA_NOTIFICATIONS_LOW_TOPIC = 'notifications-low'

# Domain Events (your service's own topics)
KAFKA_TOPICS = {
    'my_events': 'my-service.events',
}

# Kafka Client Config
KAFKA_CONFIG = {
    'client_id': 'my-service',
    'group_id': 'my-service-group',
}
```

### Step 3: Implement Standard Producers

Copy these from any existing service (they're nearly identical across services):

1. **Permission Publisher** — `apps/core/kafka_permission_publisher.py`
   - Produces to `service.permission.registry`
   - Reads from `config/permissions/my-service.json`

2. **Notification Publisher** — `apps/core/notifications/publisher.py`
   - Produces to `notifications-{priority}` topics
   - Generates idempotency keys
   - Falls back to default `notifications` topic

3. **Template Registry** — `apps/core/templates/registry.py`
   - Produces to `notification-templates`
   - Registers your service's notification templates

### Step 4: Implement Domain Event Producer (Optional)

```python
from kafka import KafkaProducer
import json

class MyServiceEventProducer:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers='fims-kafka:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
        )
    
    def publish_event(self, event_type, data, key=None):
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "my-service",
            "version": "1.0",
            "data": data,
        }
        self.producer.send(
            'my-service.events',
            value=event,
            key=key,
        )
        self.producer.flush()
```

### Step 5: Implement Consumer (If Needed)

```python
from kafka import KafkaConsumer
import json

class MyServiceConsumer:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'some-topic-to-consume',
            bootstrap_servers='fims-kafka:9092',
            group_id='my-service-consumer-group',
            auto_offset_reset='earliest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        )
    
    def poll_and_process(self):
        messages = self.consumer.poll(timeout_ms=1000)
        for tp, records in messages.items():
            for record in records:
                self.handle_event(record.value)
```

### Step 6: Topic Naming Convention

Follow the established patterns:

| Pattern | Example | When to Use |
|---|---|---|
| `service-name.entity.events` | `my-service.entity.events` | Domain entity lifecycle events |
| `service-name.entity.action` | `my-service.report.generated` | Specific domain actions |
| `fims.domain.events` | `fims.documents.events` | Cross-cutting domain events |

---

## 16. Architectural Boundaries

### Never Produce to Another Service's Internal Topics

Each service's domain topics (e.g., `fims.documents.*`, `client-service.entity.events`) are owned by that service. Other services consume but never produce to them.

### Never Bypass the Notification Pipeline

Don't produce directly to `notification-failed` or manipulate notification delivery. Publish to `notifications-{priority}` and let work-orchestration handle delivery.

### Never Consume `service.permission.registry` Outside IAM

Only IAM consumes the permission registration topic. If your service needs permission data, get it from the JWT payload (which IAM populates from these registrations).

### Never Hard-Create Topics in Service Code

Topics should be auto-created (enabled by default) or provisioned via the scripts in `config/`. Services should not include topic creation logic — they should assume topics exist.

### Never Use `localhost:9092` in Service Code

Always use `fims-kafka:9092` — the Docker DNS hostname. Using `localhost` will fail in Docker networking.

### Respect the Idempotency Key Pattern

When publishing notifications, always generate idempotency keys (`template_code-recipient-timestamp_minute`) to prevent duplicate deliveries during retries.

---

*This document was derived from direct analysis of the message-broker configuration, all service settings.py files, Kafka producer/consumer implementations across every FIMS service, and Docker Compose configurations. All topic registries, consumer groups, and integration patterns are based on actual code evidence.*
