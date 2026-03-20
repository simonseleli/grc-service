# Legal Module — FIMS Architecture Mapping
**Phase:** 2 — Architecture Mapping
**Service:** `grc-service` (port 8006)
**Input:** LEGAL_DOMAIN_EXTRACTION.md + FIMS_ARCHITECTURE.md
**Purpose:** Authoritative boundary definition before any model or API design begins.

---

## Table of Contents

1. [Legal Module Responsibilities (Owned by grc-service)](#1-legal-module-responsibilities-owned-by-grc-service)
2. [Delegated Responsibilities](#2-delegated-responsibilities)
3. [Integration Points & Communication Mode](#3-integration-points--communication-mode)
4. [Module Boundary Map](#4-module-boundary-map)
5. [Potential Overlapping Responsibilities & Resolutions](#5-potential-overlapping-responsibilities--resolutions)
6. [Kafka Topics — Legal Module](#6-kafka-topics--legal-module)
7. [Service-to-Service REST Calls — Legal Module](#7-service-to-service-rest-calls--legal-module)

---

## 1. Legal Module Responsibilities (Owned by grc-service)

These are **owned and persisted exclusively inside grc-service**. No other service replicates this data.

### 1.1 Governance Structure
- Create, update, and deactivate **CommitteeType** records.
- Create, update, and deactivate **GoverningBody** records, including assigning secretaries.
- Maintain **Member** records (local lightweight snapshot: UserID, BodyID, Position, MemberType, Status, dates).
  - The snapshot is seeded from Corporate Service data; grc-service does **not** own the canonical staff record.
- Enforce member-body relationship rules: MemberType (Committee Member vs Management Member), position, active/inactive status.

### 1.2 Determinations & Approvals
- Create, manage, and lifecycle-control **SubmissionForDetermination** records.
- Enforce submission state machine: `SUBMITTED → UNDER_REVIEW → DETERMINED`.
- Enforce originator-lock rule (submissions locked once under review).
- Record determination outcomes (Approved / Rejected / Deferred) and propagate back to the submission.

### 1.3 Meeting Governance
- Create and manage **Meeting** records with full 9-state lifecycle.
- Enforce governing-body/secretary access rules.
- Auto-generate unique, atomic meeting numbers per governing body and scheme (endless or financial-year).
- Build and manage **MeetingAgenda** (agenda items sourced exclusively from SubmissionForDetermination).
- Manage **MeetingParticipant** records — track invitation status (Accepted/Declined) and attendance.
- Compute and track quorum in real time: (Accepted / Total) × 100 ≥ 51%.
- Manage **Directive** (Meeting Directive) lifecycle:
  - Status machine: `OPEN → IN_PROGRESS → OVERDUE → CLOSED → FULLY_CLOSED`.
  - Enforce two-actor closure model (assignee first, Secretary second).
  - Auto-populate Matters Arising from open directives of the same governing body.
- Manage **Minutes** lifecycle: `DRAFT → PENDING_APPROVAL → APPROVED`.
- Auto-create **Resolution** records from agenda item outcomes.
- Manage **ConflictDeclaration** records per agenda item per member.

### 1.4 Litigation — FCC Sued
- Create and manage **CaseDefendant** records with auto-generated `FCC/SUED/YYYY/NNN` reference numbers (atomic per year).
- Manage case stages and DG review status.
- Manage **DirectiveLitigation** (DG directives on cases — separate entity from meeting Directive).
- Manage **FilingDefendant** records through 6-state approval chain.
- Manage **ResponseDefendant** (incoming plaintiff documents).
- Manage **Hearing** and **HearingReport** records; propagate `NextHearingDate` to the case.
- Manage **SettlementDefendant** lifecycle and DG approval.
- Manage **JudgmentDefendant** lifecycle, DG accept/appeal decision, and auto-create appeal filing + task.
- Manage **FinancialDefendant** records (manual tracking — no ERP integration).
- Manage **TaskLitigation** records (manual and auto-created; reminders delegated externally).
- Manage case closure and read-only archiving.

### 1.5 Litigation — FCC Suing
- Create and manage **CasePlaintiff** records with auto-generated `FCC/SUING/YYYY/NNN` references.
- Provide two distinct registration entry points: simplified Breach Report Intake (Dept User) and Full Breach Report (Legal Officer/Registry Officer).
- All sub-entity management identical to FCC Sued (`FilingPlaintiff`, `ResponsePlaintiff`, `SettlementPlaintiff`, `JudgmentPlaintiff`, `FinancialPlaintiff`).

### 1.6 Public Register
- Create and manage **PublicDecision** records: `DRAFT → PUBLISHED`.
- Enforce Secretariat-only publish permission.

### 1.7 Cross-Cutting Logic Owned by grc-service
- **Domain-level audit log** for all Legal Module state transitions (separate from IAM's system audit). Fields: EntityID, EntityType, PreviousStatus, NewStatus, ActorID, IPAddress, ActionTimestamp, Comments. Immutable.
- **Digital Signature stamping** at approval points: embed approver name + timestamp onto approval metadata. (Signature image/identity sourced from IAM/Corporate via REST; stamping logic lives in grc-service.)
- **Unique ID generation** for meeting numbers and case reference numbers (atomic, year-scoped sequences managed by grc-service's PostgreSQL sequences or Celery-coordinated locks).
- **RBAC enforcement** for all Legal Module actions (using `permissions_flat` from JWT; permission codes registered to IAM via Kafka).
- **Domain-specific task scheduling** (e.g., overdue detection Celery Beat jobs, appeal deadline watchers) — grc-service owns the scheduling logic; notification delivery is delegated.

---

## 2. Delegated Responsibilities

### 2.1 Delegated to IAM Service

| Responsibility | Why Delegated | How grc-service Consumes |
|---|---|---|
| User authentication and JWT issuance | IAM is the sole identity authority | JWT validated locally via shared `JWT_SECRET_KEY` — no IAM call at runtime |
| User profile data (name, email, department) | IAM/Corporate owns canonical staff records | REST call via `IAMClient` at read time; cache with Redis (5-min TTL) — never store locally |
| Role definitions and permission aggregation | IAM aggregates all service permissions | grc-service publishes its permissions to Kafka `service.permission.registry`; IAM stores them; JWT carries `permissions_flat` |
| System-level audit (logins, role assignments) | IAM owns system audit | grc-service maintains its own domain audit only |
| Account lockout, MFA, password policy | Security concerns owned by IAM | Transparent — handled before JWT reaches grc-service |

**grc-service obligation to IAM:**
- On startup (or via management command): publish Legal Module permission definitions to `service.permission.registry` Kafka topic.
- Store only `user_id` (UUID) in all domain models. Never store user names, emails, or department names in the primary record (only in read-model caches if needed).

---

### 2.2 Delegated to Document Records Service

| Responsibility | Why Delegated | How grc-service Consumes |
|---|---|---|
| File storage and retrieval | Document Records Service is the sole file authority | `POST /api/v1/documents/` to upload; store returned `document_id` UUID only |
| Document metadata, versioning, classification | Owned by Document Records Service | `GET /api/v1/documents/<id>/` for metadata; `GET /api/v1/documents/<id>/download/` for files |
| Document lifecycle (retention, disposal) | Owned by Document Records Service | Not invoked by grc-service; happens transparently per document type configuration |
| OnlyOffice in-browser editing | Technical capability of Document Records Service | Frontend references Document Records Service URL; grc-service not involved |

**Document-bearing Legal entities and what grc-service stores:**

| Entity | Document Field in grc-service | What's Actually Stored |
|---|---|---|
| SubmissionForDetermination | `supporting_documents[]` | Array of `document_id` UUIDs |
| MeetingAgenda | `documents[]` | Array of `document_id` UUIDs |
| Minutes | `attachments[]` | Array of `document_id` UUIDs |
| Directive (Meeting) | `evidence_document_id` | Single `document_id` UUID |
| DirectiveLitigation | `attachments[]` | Array of `document_id` UUIDs |
| FilingDefendant / FilingPlaintiff | `document_id` | Single `document_id` UUID |
| ResponseDefendant / ResponsePlaintiff | `document_id` | Single `document_id` UUID |
| HearingReport | `attachment_id` | Single `document_id` UUID |
| SettlementDefendant / Plaintiff | `agreement_document_id` | Single `document_id` UUID |
| JudgmentDefendant / Plaintiff | `document_id` | Single `document_id` UUID |
| CaseDefendant / CasePlaintiff | `initiation_documents[]` | Array of `document_id` UUIDs |
| PublicDecision | *(no document field)* | Body text stored inline |

**Rule:** grc-service never stores binary content, filenames, or file paths. It stores only the UUID reference returned by Document Records Service.

---

### 2.3 Delegated to Work Orchestration Service

| Responsibility | Why Delegated | How grc-service Consumes |
|---|---|---|
| Notification delivery (email, SMS, in-app) | Work Orchestration owns all notification channels | Publish to Kafka priority topics (`notifications-high`, etc.) using `NotificationPublisher` |
| Notification templates | Work Orchestration stores and renders templates | Register templates once via Kafka `notification-templates` topic on service startup |
| Task reminders (7-day, 2-day, 1-day before due) | Reminder scheduling is a Work Orchestration capability | Publish a reminder registration event to Work Orchestration when a `TaskLitigation` due date is set |
| Overdue escalation notifications | Same — delivery is Work Orchestration responsibility | grc-service Celery Beat detects overdue (status transition), then publishes notification event |
| Multi-stage approval workflow plans (filing approvals, settlement, closure) | Work Orchestration owns workflow plans and stage progression | Option A: Create a workflow plan via REST (`POST /api/v1/workflow/plans/`) and listen for `workflow-events` on Kafka to update filing/settlement status in grc-service. Option B (simpler, preferred for initial implementation): grc-service owns filing status transitions internally and only uses Work Orchestration for notifications. *(See §5 for decision.)*|

**What grc-service does NOT delegate from approvals:**
- The **business decision** (who approves, what the threshold is, what outcome means) stays in grc-service.
- Work Orchestration is a delivery/sequencing engine — it does not own the meaning of Legal domain approvals.

---

### 2.4 Delegated to Corporate Service

| Responsibility | Why Delegated | How grc-service Consumes |
|---|---|---|
| Canonical staff/employee records | Corporate Service owns HR | REST call to `GET /api/v1/corporate/hr/employees/<id>/` when populating member selectors |
| Department structure | Corporate Service owns org structure | REST call when rendering department lists in UI forms |
| Financial process links (Revenue Collection, External Payments) | Corporate Service owns finance | REST call from grc-service billing-related views; or event-driven sync if needed in future |

**Member sync pattern:**
- When a `GoverningBody` is created or its members are managed, grc-service fetches eligible staff from Corporate Service via REST.
- grc-service stores a **local snapshot** of member records (`UserID`, `BodyID`, `Position`, `MemberType`, `Status`) for query performance.
- When Corporate Service publishes `corporate.events` (e.g., `employee.deactivated`, `employee.updated`) to Kafka, grc-service consumes the event and updates its local member snapshot.

---

## 3. Integration Points & Communication Mode

### 3.1 Full Integration Matrix

| Integration | Direction | Mode | Trigger | Topic / Endpoint |
|---|---|---|---|---|
| Publish Legal permissions to IAM | grc → IAM (Kafka) | **Kafka (async)** | Service startup | `service.permission.registry` |
| Fetch user profile (name, email) | grc → IAM | **REST (sync)** | On demand (display, digital signature) | `GET /api/v1/iam/users/<id>/` |
| Upload document | grc → Document Records | **REST (sync)** | User uploads a file | `POST /api/v1/documents/` |
| Fetch document metadata | grc → Document Records | **REST (sync)** | Preview/download | `GET /api/v1/documents/<id>/` |
| Subscribe to document events | Document Records → grc (Kafka) | **Kafka (async)** | Document deleted/versioned externally | `fims.documents.events` |
| Register notification templates | grc → Work Orchestration (Kafka) | **Kafka (async)** | Service startup | `notification-templates` |
| Send notification (urgent) | grc → Work Orchestration (Kafka) | **Kafka (async)** | DG review required, appeal deadline | `notifications-urgent` |
| Send notification (high) | grc → Work Orchestration (Kafka) | **Kafka (async)** | Filing approval request, judgment | `notifications-high` |
| Send notification (normal) | grc → Work Orchestration (Kafka) | **Kafka (async)** | Meeting invitations, directive assigned | `notifications-normal` |
| Send notification (low) | grc → Work Orchestration (Kafka) | **Kafka (async)** | Quorum update, status changes | `notifications-low` |
| Register task reminders | grc → Work Orchestration | **REST (sync)** | TaskLitigation / Directive created with due date | `POST /api/v1/workflow/reminders/` |
| Fetch workflow plan status (if used) | grc → Work Orchestration | **REST (sync)** | Filing approval progression (if delegated) | `GET /api/v1/workflow/plans/<id>/` |
| Listen for workflow events (if used) | Work Orchestration → grc (Kafka) | **Kafka (async)** | Filing or settlement plan stage changes | `workflow-events` |
| Fetch employee list / member candidates | grc → Corporate Service | **REST (sync)** | Governing body setup, member assignment | `GET /api/v1/corporate/hr/employees/` |
| Consume employee update events | Corporate Service → grc (Kafka) | **Kafka (async)** | Staff deactivated / profile changed | `corporate.events` |
| Publish Legal domain events | grc → other services | **Kafka (async)** | Case registered, meeting closed, decision published | `grc.legal.events` (new topic) |

### 3.2 Communication Mode Decision Rules

| Scenario | Use REST | Use Kafka |
|---|---|---|
| User is waiting for a response (UI action) | ✅ | ❌ |
| Background side-effect after a state change | ❌ | ✅ |
| Data needed inline in an API response | ✅ | ❌ |
| Notification delivery | ❌ | ✅ |
| Permission/template registration at startup | ❌ | ✅ |
| Member sync on staff profile change | ❌ | ✅ |
| Fetching user name for a digital signature stamp | ✅ | ❌ |

---

## 4. Module Boundary Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                     grc-service (Legal Module)                      │
│  OWNS:                                                              │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  CommitteeType   │  GoverningBody   │  Member (snapshot) │       │
│  │  SubmissionForDetermination                              │       │
│  │  Meeting  │  MeetingAgenda  │  MeetingParticipant        │       │
│  │  Directive (meeting)  │  Minutes  │  Resolution           │       │
│  │  ConflictDeclaration                                     │       │
│  │  CaseDefendant   │  CasePlaintiff                        │       │
│  │  DirectiveLitigation  (DG directives on cases)           │       │
│  │  FilingDefendant │  FilingPlaintiff                      │       │
│  │  ResponseDefendant │ ResponsePlaintiff                    │       │
│  │  Hearing  │  HearingReport                               │       │
│  │  SettlementDefendant │ SettlementPlaintiff                │       │
│  │  JudgmentDefendant   │ JudgmentPlaintiff                  │       │
│  │  FinancialDefendant  │ FinancialPlaintiff                 │       │
│  │  TaskLitigation                                          │       │
│  │  PublicDecision                                          │       │
│  │  Legal Audit Log (domain-scoped, immutable)              │       │
│  └─────────────────────────────────────────────────────────┘        │
│  ORCHESTRATES BUT DOES NOT OWN:                                     │
│  ┌────────────────────────────────────────────────────────┐         │
│  │  Filing approval state machine (6 states)              │         │
│  │  Settlement DG approval state machine                  │         │
│  │  Judgment DG decision → auto-creates filing + task     │         │
│  │  Quorum calculation (real-time, from own data)         │         │
│  │  TaskLitigation overdue detection (Celery Beat job)    │         │
│  │  Digital signature metadata assembly                   │         │
│  └────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
               │                        │                   │
    REST / Kafka             REST / Kafka            Kafka
               │                        │                   │
┌──────────────▼──┐   ┌─────────────────▼──┐   ┌───────────▼───────┐
│  IAM Service     │   │ Document Records   │   │Work Orchestration │
│  PROVIDES:       │   │   PROVIDES:        │   │  PROVIDES:        │
│  - JWT issuance  │   │  - File storage    │   │  - Notifications  │
│  - User profiles │   │  - Document IDs    │   │  - Task reminders │
│  - permissions   │   │  - Metadata/DL     │   │  - Workflow plans │
│    aggregation   │   │  - Versioning      │   │    (optional)     │
└──────────────────┘   └────────────────────┘   └───────────────────┘
               │
    REST (sync, on demand)
               │
┌──────────────▼──────┐
│  Corporate Service  │
│  PROVIDES:          │
│  - Staff/employee   │
│    list for member  │
│    assignment       │
│  - Dept structure   │
│  - corporate.events │
│    (Kafka) for sync │
└─────────────────────┘
```

---

## 5. Potential Overlapping Responsibilities & Resolutions

### 5.1 Approval Workflows — grc-service vs Work Orchestration Service

**Overlap:** The 6-state filing approval chain (DRAFT → UNDER_REVIEW_LM → APPROVED_LM → UNDER_REVIEW_DG → APPROVED → FILED) resembles what Work Orchestration Service manages (multi-stage approval pipelines).

**Decision: grc-service owns filing approval state internally.**

**Rationale:**
- The filing approval states are **domain states** — they have direct business meaning in the Legal domain (e.g., `FILED` status affects case stage, DG decision triggers appeal auto-creation).
- Delegating state to Work Orchestration would require grc-service to trust an external state machine for a legally critical process, introducing latency and failure surface area.
- Work Orchestration is used for **delivery and reminders**, not as the source of truth for domain state.
- Pattern is consistent with how grc-service should handle all its approval chains (confirmed by architecture principle: "business domain logic → domain service").

**Boundary:**
- grc-service: owns and transitions approval status fields.
- Work Orchestration: receives Kafka events to send notifications at each transition.

---

### 5.2 Task Management — TaskLitigation vs Work Orchestration Tasks

**Overlap:** `TaskLitigation` (legal case tasks with due dates, assignments, reminders) structurally resembles `WorkflowTaskModel` in Work Orchestration Service.

**Decision: TaskLitigation is owned by grc-service. Reminders are delegated to Work Orchestration.**

**Rationale:**
- Legal tasks are case-scoped domain data. They hold references to `CaseID`, `RelatedEntityType`, `RelatedEntityID` — domain context unknown to Work Orchestration.
- Auto-creation logic (e.g., creating a task from a judgment appeal decision) is domain logic that belongs in grc-service.
- However, reminder delivery (7-day, 2-day, 1-day alerts) is a cross-service infrastructure concern → delegate to Work Orchestration via REST `POST /api/v1/workflow/reminders/`.

**Boundary:**
- grc-service: creates `TaskLitigation`, owns status transitions, detects overdue via Celery Beat.
- Work Orchestration: receives a reminder registration call when a task is created with a due date; handles all reminder delivery.

---

### 5.3 Directive (Meeting) vs DirectiveLitigation — Name Collision

**Overlap:** Both are called "Directive" in common language. The domain extraction names them `Directive` (meeting) and `DirectiveLitigation` (case), but they could be confused.

**Decision: Keep as two fully separate models in grc-service.**

**Rationale:**
- `Directive` (meeting) is scoped to a meeting → involves two-actor closure, Matters Arising flow, governing body context.
- `DirectiveLitigation` is scoped to a litigation case → issued by DG, has different closure logic, no Matters Arising.
- They share no fields beyond basic task metadata. Merging them would create nullable fields and tangled business rules.
- Naming convention in the codebase: `MeetingDirective` and `LitigationDirective` (or `DirectiveLitigation`) to avoid ambiguity.

---

### 5.4 grc-service Domain Audit vs IAM System Audit

**Overlap:** Both audit to a log. IAM logs system events (login, logout, role change). grc-service logs domain events (case status changed, directive closed, minutes approved).

**Decision: Both logs exist independently; they serve different purposes.**

**Boundary:**
- IAM Audit: system-level security events → IAM owns exclusively.
- grc-service Legal Audit: business-level state changes in Legal domain → grc-service owns exclusively.
- `ActorID` in Legal Audit always matches the user's IAM UUID for cross-reference.

---

### 5.5 Member Sync — grc-service Snapshot vs Corporate Service

**Overlap:** Corporate Service owns the canonical employee record. grc-service needs member data for quorum, invitation, and directive assignment.

**Decision: grc-service maintains a local lightweight snapshot; Corporate Service is the source of truth.**

**Pattern:**
1. Admin assigns a user as member → grc-service calls Corporate Service REST to validate user exists and fetch initial profile.
2. grc-service stores: `UserID` (UUID), `BodyID`, `Position`, `MemberType`, `JoinedDate`, `Status`.
3. grc-service does NOT store: name, email, profile picture, org chart position (fetched via `IAMClient` when needed for display).
4. When `corporate.events` Kafka topic delivers `employee.deactivated` → grc-service Kafka consumer updates local `Member.Status = INACTIVE` and nulls `LeftDate`.
5. When `corporate.events` delivers `employee.profile.updated` → grc-service discards any cached name/email (TTL-based cache invalidation).

---

### 5.6 Notification Templates — Ownership

**Decision:** grc-service defines templates; Work Orchestration Service stores and renders them.

**Pattern (identical to other FIMS services):**
- grc-service `management/startup` or Django `post_migrate` signal publishes all Legal notification templates to Kafka `notification-templates`.
- Work Orchestration Service upserts `NotificationTemplateModel` records.
- When grc-service needs to notify, it publishes to `notifications-<priority>` using `template_code` and context variables.

---

## 6. Kafka Topics — Legal Module

### 6.1 Topics grc-service Publishes To

| Topic | Message Type | When Published | Priority |
|---|---|---|---|
| `service.permission.registry` | Permission definitions | Service startup | — |
| `notification-templates` | Template definitions | Service startup | — |
| `notifications-urgent` | Notification request | DG review required, appeal deadline imminent | urgent |
| `notifications-high` | Notification request | Filing approval request (LM/DG), judgment recorded, settlement approval, case registered | high |
| `notifications-normal` | Notification request | Meeting invitation, directive assigned, minutes pending approval, task assigned | normal |
| `notifications-low` | Notification request | Quorum update, status changes, meeting postponed | low |
| `grc.legal.events` | Domain event | Case registered, meeting closed, decision published, directive fully closed | — |

### 6.2 Topics grc-service Consumes From

| Topic | Produced By | What grc-service Does |
|---|---|---|
| `workflow-events` | Work Orchestration | *(Only if filing approvals are delegated — see §5.1; currently not required)* |
| `corporate.events` | Corporate Service | Update local Member snapshot on `employee.deactivated` / `employee.profile.updated` |
| `fims.documents.events` | Document Records Service | Handle `document.deleted` or `document.archived` to null/flag affected `document_id` references |
| `fims.iam.user.updated` | IAM Service | Invalidate cached user profile data (names/emails used in audit display) |

### 6.3 New Topic to Create

| Topic | Owner | Consumers | Purpose |
|---|---|---|---|
| `grc.legal.events` | grc-service | Future: client portal, reporting service, public register sync | Domain events from Legal module for cross-service loose coupling |

**Proposed event types for `grc.legal.events`:**

| Event Type | Trigger |
|---|---|
| `legal.case.defendant.registered` | CaseDefendant created |
| `legal.case.plaintiff.registered` | CasePlaintiff created |
| `legal.case.closed` | Case closure approved by DG |
| `legal.meeting.closed` | Meeting status → CLOSED |
| `legal.public_decision.published` | PublicDecision status → PUBLISHED |
| `legal.directive.fully_closed` | Directive FinallyClosed = true |
| `legal.filing.filed` | FilingDefendant/Plaintiff status → FILED |

---

## 7. Service-to-Service REST Calls — Legal Module

### 7.1 grc-service → IAM Service

| Call | Endpoint | When | Caching |
|---|---|---|---|
| Fetch user profile for display | `GET /api/v1/iam/users/<user_id>/` | Rendering names in audit log, digital signature metadata | Redis, 5-min TTL |
| Validate user exists during member assignment | `GET /api/v1/iam/users/<user_id>/` | Admin assigns member to governing body | Short TTL or no cache |

### 7.2 grc-service → Document Records Service

| Call | Endpoint | When | Caching |
|---|---|---|---|
| Upload document | `POST /api/v1/documents/` | User attaches a file in any Legal form | None (write operation) |
| Fetch document metadata for preview | `GET /api/v1/documents/<id>/` | Document preview in filing/minutes/resolution | Short TTL per document_id |
| Generate download URL | `GET /api/v1/documents/<id>/download/` | User clicks download | None (token-protected URL) |

### 7.3 grc-service → Corporate Service

| Call | Endpoint | When | Caching |
|---|---|---|---|
| List eligible staff for member assignment | `GET /api/v1/corporate/hr/employees/` | Governing body member management screen | Redis, 5-min TTL |
| Fetch department list | `GET /api/v1/corporate/hr/departments/` | Breach Report Intake form (Department field) | Redis, 10-min TTL |

### 7.4 grc-service → Work Orchestration Service

| Call | Endpoint | When | Caching |
|---|---|---|---|
| Register task reminder | `POST /api/v1/workflow/reminders/` | TaskLitigation or meeting Directive created with due date | None (write operation) |
| Cancel reminder | `DELETE /api/v1/workflow/reminders/<id>/` | Task closed before due date | None |

**All service-to-service REST calls use header:**
```
X-Service-Token: <SERVICE_TO_SERVICE_TOKEN from env>
```

---

## 8. Summary — What Lives Where

| Concern | Owner | Mechanism |
|---|---|---|
| Authentication | IAM Service | JWT (locally validated) |
| User profiles | IAM Service | REST + Redis cache |
| Permissions | IAM aggregates, grc-service defines | Kafka + JWT `permissions_flat` |
| System audit (logins) | IAM Service | IAM internal |
| Domain audit (legal state changes) | grc-service | Own immutable Legal Audit Log table |
| File storage | Document Records Service | REST (store UUID reference only) |
| Document metadata/download | Document Records Service | REST |
| Notification delivery | Work Orchestration Service | Kafka `notifications-*` topics |
| Notification templates | Defined by grc-service, stored by Work Orchestration | Kafka `notification-templates` |
| Task reminders | Work Orchestration Service | REST registration by grc-service |
| Workflow plans (approval pipelines) | grc-service owns state; Work Orchestration delivers notifications | grc internal + Kafka for notifications |
| Staff/employee master data | Corporate Service | REST + Kafka `corporate.events` for sync |
| Member snapshot (body-scoped) | grc-service | Local table, synced from Corporate events |
| All Legal domain entities | grc-service | Own PostgreSQL instance |
| Case reference number sequences | grc-service | PostgreSQL atomic sequences |
| Meeting number sequences | grc-service | PostgreSQL atomic sequences |
| Quorum calculation | grc-service | Computed from own MeetingParticipant data |
| Overdue detection | grc-service | Celery Beat periodic task |
| Digital signature stamping | grc-service (metadata assembly) + IAM (signer identity via REST) | REST + own stamping logic |
| Public Register publish | grc-service | Own PublicDecision entity |

---

*End of Architecture Mapping*
*Source: LEGAL_DOMAIN_EXTRACTION.md + FIMS_ARCHITECTURE.md*
*Next phase: Backend Data Model Design*
