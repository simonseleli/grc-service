# Legal Module — Workflow Integration
**Service:** `grc-service`
**Module:** Legal
**Phase:** 5D — Workflow Integration
**References:** 5A (Base Models & Mixins), 5B-1 to 5B-3 (Data Models), 5C (Lookup Tables)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Workflow Entities — Master Reference](#2-workflow-entities--master-reference)
3. [YAML Template Conventions](#3-yaml-template-conventions)
4. [Legal YAML Templates](#4-legal-yaml-templates)
5. [workflow_entity_paths.py — Legal Path Registration](#5-workflow_entity_pathspy--legal-path-registration)
6. [Model Override Methods](#6-model-override-methods)
7. [Service Layer Pattern](#7-service-layer-pattern)
8. [Standard 5 Service Methods](#8-standard-5-service-methods)
9. [Workflow View Pattern](#9-workflow-view-pattern)
10. [URL Registration](#10-url-registration)
11. [Kafka Event Integration](#11-kafka-event-integration)

---

## 1. Overview

The Legal module integrates with the external **Work Orchestration Service (WO)** for 10 entities that require multi-stage human approval or lifecycle management. The pattern is **identical** to the Internal Audit workflow integration — same `WorkflowMixin`, same `OrchestrationClient`, same YAML template structure.

### How it works

```
[Legal Entity] ──submit──▶ [GRC Service Layer] ──start_workflow()──▶ [Work Orchestration Service]
                                                                              │
[Kafka Consumer] ◀──stage-event── [WO Kafka Publisher] ◀──advance_stage()──┘
       │
       └──▶ entity.update_workflow_stage() / complete_workflow() + status update
```

### Key conventions that must not be deviated from

| Convention | Rule |
|---|---|
| Template code format | `grc.legal_{process_name}` — lowercase, dot-separated |
| YAML field style | `definitionKey` (camelCase), `nextState` (camelCase), stage `name` (Title Case) |
| Service call order | context → metadata → `start_workflow()` → save 5 fields |
| `applicant_id` | Always set at service layer: `context['applicant_id'] = submitter_id` |
| `select_for_update()` | Always used when loading entity before WO call |
| Inline fallback stages | **Strictly prohibited.** All workflows defined in WO Console via YAML. |

---

## 2. Workflow Entities — Master Reference

Ten Legal entities carry `WorkflowMixin`. They map to six YAML templates (shared between defendant/plaintiff sides of the same process).

| Entity | db_table | Template Code | Stages | Trigger |
|---|---|---|---|---|
| `Meeting` | `legal_meeting` | `grc.legal_meeting_lifecycle` | 3 | Secretary starts meeting process |
| `Minutes` | `legal_minutes` | `grc.legal_minutes_approval` | 2 | Secretary submits draft minutes |
| `CaseDefendant` | `legal_case_defendant` | `grc.legal_case_closure` | 3 | Legal Officer submits for closure |
| `CasePlaintiff` | `legal_case_plaintiff` | `grc.legal_case_closure` | 3 | Legal Officer submits for closure |
| `FilingDefendant` | `legal_filing_defendant` | `grc.legal_filing_approval` | 2 | Legal Officer submits filing |
| `FilingPlaintiff` | `legal_filing_plaintiff` | `grc.legal_filing_approval` | 2 | Legal Officer submits filing |
| `SettlementDefendant` | `legal_settlement_defendant` | `grc.legal_settlement_approval` | 3 | Legal Officer submits settlement |
| `SettlementPlaintiff` | `legal_settlement_plaintiff` | `grc.legal_settlement_approval` | 3 | Legal Officer submits settlement |
| `JudgmentDefendant` | `legal_judgment_defendant` | `grc.legal_judgment_decision` | 3 | Legal Officer records judgment |
| `JudgmentPlaintiff` | `legal_judgment_plaintiff` | `grc.legal_judgment_decision` | 3 | Legal Officer records judgment |

### Services mapping

| Entity pair | Service class | File |
|---|---|---|
| `Meeting` | `LegalMeetingService` | `apps/core/services/legal_meeting_service.py` |
| `Minutes` | `LegalMinutesService` | `apps/core/services/legal_minutes_service.py` |
| `CaseDefendant` / `CasePlaintiff` | `LegalCaseService` | `apps/core/services/legal_case_service.py` |
| `FilingDefendant` / `FilingPlaintiff` | `LegalFilingService` | `apps/core/services/legal_filing_service.py` |
| `SettlementDefendant` / `SettlementPlaintiff` | `LegalSettlementService` | `apps/core/services/legal_settlement_service.py` |
| `JudgmentDefendant` / `JudgmentPlaintiff` | `LegalJudgmentService` | `apps/core/services/legal_judgment_service.py` |

---

## 3. YAML Template Conventions

All Legal templates are appended to `apps/core/workflows/workflows.yaml`.

### Template skeleton

```yaml
- code: "grc.legal_{process}"
  name: "{Human Name}"
  workflow_type: "grc"
  version: 1
  definition:
    description: "..."
    sla:
      targetMinutes: <int>        # overall SLA in minutes
      breachStrategy: "escalate"
    metadata:
      module: "grc"
      category: "legal"
    stages:
      - definitionKey: "{stage_key}"   # snake_case
        name: "{Stage Display Name}"
        order: <int>
        assignees: ["role:{role_name}"] # or "{{context_variable}}"
        actions:
          - name: "{action}"            # lowercase
            label: "{Action Label}"
            nextState: "completed"      # camelCase: completed | rejected | pending
        sla:
          durationMinutes: <int>
          breachStrategy: "notify"
        metadata:
          status_on_complete: "{grc_status}"  # local status value on stage completion
```

### Field name rules

| Field | Style | Example |
|---|---|---|
| `definitionKey` | snake_case | `"legal_manager_approval"` |
| `name` (stage) | Title Case | `"Legal Manager Approval"` |
| `action.name` | lowercase | `"approve"`, `"reject"`, `"return"` |
| `action.label` | Title Case | `"Approve"`, `"Return to Officer"` |
| `nextState` | camelCase | `"completed"`, `"rejected"`, `"pending"` |
| `metadata.status_on_complete` | snake_case | `"pending_closure"` |

### Role identifiers used across Legal templates

| `assignees` value | Meaning |
|---|---|
| `"role:legal_officer"` | Assigned Legal Officer |
| `"role:legal_manager"` | Legal Manager / Head of Legal |
| `"role:director_general"` | Director General |
| `"role:secretary"` | Governing Body Secretary |
| `"role:committee_chair"` | Governing Body Committee Chair |
| `"{{legal_officer_id}}"` | Resolved from `get_workflow_context()` at runtime |
| `"{{submitter_id}}"` | Applicant who started the workflow |

---

## 4. Legal YAML Templates

### 4.1 `grc.legal_meeting_lifecycle`

```yaml
  - code: "grc.legal_meeting_lifecycle"
    name: "Legal Meeting Lifecycle"
    workflow_type: "grc"
    version: 1
    definition:
      description: "3-phase lifecycle: preparation → execution → closure"
      sla:
        targetMinutes: 20160        # 14 days overall
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "legal_meeting"
      stages:
        - definitionKey: "meeting_preparation"
          name: "Meeting Preparation"
          order: 1
          assignees: ["role:secretary"]
          actions:
            - name: "confirm_scheduled"
              label: "Confirm Scheduled"
              nextState: "completed"
            - name: "cancel"
              label: "Cancel Meeting"
              nextState: "rejected"
          sla:
            durationMinutes: 4320
            breachStrategy: "notify"
          metadata:
            status_on_complete: "scheduled"

        - definitionKey: "meeting_execution"
          name: "Meeting Execution"
          order: 2
          assignees: ["role:secretary"]
          actions:
            - name: "mark_held"
              label: "Mark as Held"
              nextState: "completed"
            - name: "adjourn"
              label: "Adjourn"
              nextState: "pending"
          sla:
            durationMinutes: 14400
            breachStrategy: "notify"
          metadata:
            status_on_complete: "held"

        - definitionKey: "meeting_closure"
          name: "Meeting Closure"
          order: 3
          assignees: ["role:legal_manager"]
          actions:
            - name: "close"
              label: "Close Meeting"
              nextState: "completed"
          sla:
            durationMinutes: 1440
            breachStrategy: "notify"
          metadata:
            status_on_complete: "closed"
```

### 4.2 `grc.legal_minutes_approval`

```yaml
  - code: "grc.legal_minutes_approval"
    name: "Legal Minutes Approval"
    workflow_type: "grc"
    version: 1
    definition:
      description: "2-stage: Secretary review → Committee chair approval"
      sla:
        targetMinutes: 10080        # 7 days
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "legal_minutes"
      stages:
        - definitionKey: "minutes_draft_review"
          name: "Minutes Draft Review"
          order: 1
          assignees: ["role:secretary"]
          actions:
            - name: "submit_for_approval"
              label: "Submit for Approval"
              nextState: "completed"
            - name: "return"
              label: "Return for Correction"
              nextState: "rejected"
          sla:
            durationMinutes: 2880
            breachStrategy: "notify"
          metadata:
            status_on_complete: "pending_approval"

        - definitionKey: "minutes_committee_approval"
          name: "Committee Approval"
          order: 2
          assignees: ["role:committee_chair"]
          actions:
            - name: "approve"
              label: "Approve"
              nextState: "completed"
            - name: "request_amendments"
              label: "Request Amendments"
              nextState: "pending"
          sla:
            durationMinutes: 7200
            breachStrategy: "notify"
          metadata:
            status_on_complete: "approved"
```

### 4.3 `grc.legal_case_closure`

```yaml
  - code: "grc.legal_case_closure"
    name: "Legal Case Closure"
    workflow_type: "grc"
    version: 1
    definition:
      description: "3-stage: Legal Officer → Legal Manager → DG for final closure note"
      sla:
        targetMinutes: 14400        # 10 days
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "legal_case"
      stages:
        - definitionKey: "case_officer_review"
          name: "Legal Officer Review"
          order: 1
          assignees: ["{{legal_officer_id}}"]
          actions:
            - name: "submit"
              label: "Submit for Closure"
              nextState: "completed"
            - name: "return"
              label: "Return to Draft"
              nextState: "rejected"
          sla:
            durationMinutes: 2880
            breachStrategy: "notify"
          metadata:
            status_on_complete: "pending_closure"

        - definitionKey: "legal_manager_approval"
          name: "Legal Manager Approval"
          order: 2
          assignees: ["role:legal_manager"]
          actions:
            - name: "approve"
              label: "Approve Closure"
              nextState: "completed"
            - name: "return"
              label: "Return to Officer"
              nextState: "pending"
          sla:
            durationMinutes: 4320
            breachStrategy: "notify"
          metadata:
            status_on_complete: "dg_review"

        - definitionKey: "dg_closure_noting"
          name: "DG Closure Noting"
          order: 3
          assignees: ["role:director_general"]
          actions:
            - name: "note"
              label: "Note and Close"
              nextState: "completed"
          sla:
            durationMinutes: 7200
            breachStrategy: "notify"
          metadata:
            status_on_complete: "closed"
```

### 4.4 `grc.legal_filing_approval`

```yaml
  - code: "grc.legal_filing_approval"
    name: "Legal Filing Approval"
    workflow_type: "grc"
    version: 1
    definition:
      description: "2-stage: Legal Officer review → Legal Manager approval before court filing"
      sla:
        targetMinutes: 5760         # 4 days
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "legal_filing"
      stages:
        - definitionKey: "filing_officer_review"
          name: "Filing Review"
          order: 1
          assignees: ["{{legal_officer_id}}"]
          actions:
            - name: "submit"
              label: "Submit for Approval"
              nextState: "completed"
            - name: "return"
              label: "Return to Draft"
              nextState: "rejected"
          sla:
            durationMinutes: 1440
            breachStrategy: "notify"
          metadata:
            status_on_complete: "pending_approval"

        - definitionKey: "legal_manager_filing_approval"
          name: "Legal Manager Approval"
          order: 2
          assignees: ["role:legal_manager"]
          actions:
            - name: "approve"
              label: "Approve Filing"
              nextState: "completed"
            - name: "reject"
              label: "Reject"
              nextState: "rejected"
            - name: "request_changes"
              label: "Request Changes"
              nextState: "pending"
          sla:
            durationMinutes: 4320
            breachStrategy: "notify"
          metadata:
            status_on_complete: "filed"
```

### 4.5 `grc.legal_settlement_approval`

```yaml
  - code: "grc.legal_settlement_approval"
    name: "Legal Settlement Approval"
    workflow_type: "grc"
    version: 1
    definition:
      description: "3-stage: Officer review → Legal Manager → DG final approval"
      sla:
        targetMinutes: 20160        # 14 days
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "legal_settlement"
      stages:
        - definitionKey: "settlement_officer_review"
          name: "Settlement Review"
          order: 1
          assignees: ["{{legal_officer_id}}"]
          actions:
            - name: "submit"
              label: "Submit for Approval"
              nextState: "completed"
            - name: "return"
              label: "Return to Draft"
              nextState: "rejected"
          sla:
            durationMinutes: 2880
            breachStrategy: "notify"
          metadata:
            status_on_complete: "pending_approval"

        - definitionKey: "legal_manager_settlement_review"
          name: "Legal Manager Review"
          order: 2
          assignees: ["role:legal_manager"]
          actions:
            - name: "forward_to_dg"
              label: "Forward to DG"
              nextState: "completed"
            - name: "reject"
              label: "Reject Settlement"
              nextState: "rejected"
          sla:
            durationMinutes: 7200
            breachStrategy: "notify"
          metadata:
            status_on_complete: "dg_review"

        - definitionKey: "dg_settlement_approval"
          name: "DG Approval"
          order: 3
          assignees: ["role:director_general"]
          actions:
            - name: "approve"
              label: "Approve Settlement"
              nextState: "completed"
            - name: "return"
              label: "Return to Manager"
              nextState: "pending"
          sla:
            durationMinutes: 10080
            breachStrategy: "notify"
          metadata:
            status_on_complete: "approved"
```

### 4.6 `grc.legal_judgment_decision`

```yaml
  - code: "grc.legal_judgment_decision"
    name: "Legal Judgment Decision"
    workflow_type: "grc"
    version: 1
    definition:
      description: "3-stage: Officer records judgment → Manager reviews → DG notes decision"
      sla:
        targetMinutes: 14400        # 10 days
        breachStrategy: "escalate"
      metadata:
        module: "grc"
        category: "legal_judgment"
      stages:
        - definitionKey: "judgment_officer_review"
          name: "Judgment Review"
          order: 1
          assignees: ["{{legal_officer_id}}"]
          actions:
            - name: "submit"
              label: "Submit Judgment"
              nextState: "completed"
            - name: "return"
              label: "Return to Draft"
              nextState: "rejected"
          sla:
            durationMinutes: 2880
            breachStrategy: "notify"
          metadata:
            status_on_complete: "pending_review"

        - definitionKey: "legal_manager_judgment_review"
          name: "Legal Manager Review"
          order: 2
          assignees: ["role:legal_manager"]
          actions:
            - name: "approve"
              label: "Approve and Forward"
              nextState: "completed"
            - name: "return"
              label: "Return to Officer"
              nextState: "pending"
          sla:
            durationMinutes: 4320
            breachStrategy: "notify"
          metadata:
            status_on_complete: "dg_noting"

        - definitionKey: "dg_judgment_noting"
          name: "DG Noting"
          order: 3
          assignees: ["role:director_general"]
          actions:
            - name: "note"
              label: "Note Decision"
              nextState: "completed"
          sla:
            durationMinutes: 7200
            breachStrategy: "notify"
          metadata:
            status_on_complete: "noted"
```

---

## 5. workflow_entity_paths.py — Legal Path Registration

Add Legal entities to `apps/core/workflow_entity_paths.py`:

```python
ENTITY_DETAIL_PATHS = {
    # ... existing audit entries ...

    # Legal — Governance
    'meeting':              '/service/grc/legal/meetings',
    'minutes':              '/service/grc/legal/minutes',

    # Legal — Litigation (Defendant)
    'case_defendant':       '/service/grc/legal/cases/defendant',
    'filing_defendant':     '/service/grc/legal/filings/defendant',
    'settlement_defendant': '/service/grc/legal/settlements/defendant',
    'judgment_defendant':   '/service/grc/legal/judgments/defendant',

    # Legal — Litigation (Plaintiff)
    'case_plaintiff':       '/service/grc/legal/cases/plaintiff',
    'filing_plaintiff':     '/service/grc/legal/filings/plaintiff',
    'settlement_plaintiff': '/service/grc/legal/settlements/plaintiff',
    'judgment_plaintiff':   '/service/grc/legal/judgments/plaintiff',
}
```

---

## 6. Model Override Methods

Every `WorkflowMixin` entity must override `get_workflow_context()` and `get_workflow_metadata()`.

### Rule

- `get_workflow_context()` — provides `{{variable}}` values referenced in `assignees` in the YAML template. Always includes `applicant_id` placeholder (set at service layer).
- `get_workflow_metadata()` — display fields stored in WO plan; always ends with `add_entity_detail_path_to_metadata(meta, entity_type)`.

### 6.1 Meeting

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'meeting',
        'entity_id': str(self.id),
        'governing_body_id': str(self.governing_body_id),
        'meeting_number': self.meeting_number,
    }

def get_workflow_metadata(self) -> dict:
    meta = {
        'entity_type': 'meeting',
        'entity_id': str(self.id),
        'meeting_number': self.meeting_number,
        'meeting_date': str(self.scheduled_date),
        'governing_body': str(self.governing_body_id),
        'status': self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, 'meeting')
```

### 6.2 Minutes

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'minutes',
        'entity_id': str(self.id),
        'meeting_id': str(self.meeting_id),
        'prepared_by': str(self.created_by),
    }

def get_workflow_metadata(self) -> dict:
    meta = {
        'entity_type': 'minutes',
        'entity_id': str(self.id),
        'meeting_id': str(self.meeting_id),
        'prepared_by': str(self.created_by),
        'status': self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, 'minutes')
```

### 6.3 CaseDefendant / CasePlaintiff

```python
# CaseDefendant
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'case_defendant',
        'entity_id': str(self.id),
        'reference_number': self.reference_number,
        'legal_officer_id': str(self.assigned_legal_officer_id) if self.assigned_legal_officer_id else '',
    }

def get_workflow_metadata(self) -> dict:
    meta = {
        'entity_type': 'case_defendant',
        'entity_id': str(self.id),
        'reference_number': self.reference_number,
        'case_title': self.case_title,
        'court_level': str(self.court_level_id),
        'status': self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, 'case_defendant')

# CasePlaintiff — mirrors CaseDefendant, entity_type = 'case_plaintiff'
```

### 6.4 FilingDefendant / FilingPlaintiff

```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'filing_defendant',
        'entity_id': str(self.id),
        'case_defendant_id': str(self.case_defendant_id),
        'legal_officer_id': str(self.created_by),
    }

def get_workflow_metadata(self) -> dict:
    meta = {
        'entity_type': 'filing_defendant',
        'entity_id': str(self.id),
        'case_defendant_id': str(self.case_defendant_id),
        'filing_date': str(self.filing_date) if self.filing_date else '',
        'status': self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, 'filing_defendant')
```

### 6.5 SettlementDefendant / JudgmentDefendant

**Settlement:**
```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'settlement_defendant',
        'entity_id': str(self.id),
        'case_defendant_id': str(self.case_defendant_id),
        'legal_officer_id': str(self.created_by),
    }

def get_workflow_metadata(self) -> dict:
    meta = {
        'entity_type': 'settlement_defendant',
        'entity_id': str(self.id),
        'case_defendant_id': str(self.case_defendant_id),
        'settlement_amount': str(self.settlement_amount) if self.settlement_amount else '',
        'status': self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, 'settlement_defendant')
```

**Judgment:**
```python
def get_workflow_context(self) -> dict:
    return {
        'entity_type': 'judgment_defendant',
        'entity_id': str(self.id),
        'case_defendant_id': str(self.case_defendant_id),
        'legal_officer_id': str(self.created_by),
    }

def get_workflow_metadata(self) -> dict:
    meta = {
        'entity_type': 'judgment_defendant',
        'entity_id': str(self.id),
        'case_defendant_id': str(self.case_defendant_id),
        'judgment_date': str(self.judgment_date) if self.judgment_date else '',
        'outcome': self.outcome if hasattr(self, 'outcome') else '',
        'status': self.status,
    }
    from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
    return add_entity_detail_path_to_metadata(meta, 'judgment_defendant')
```

> **Plaintiff side** — all methods mirror the defendant pattern exactly; only `entity_type` and FK field names change (`case_defendant_id` → `case_plaintiff_id`).

---

## 7. Service Layer Pattern

All six Legal services follow the canonical FIMS pattern from `working_paper_service.py` / `audit_universe_service.py`. The full canonical class is shown for `LegalMeetingService`; the others follow identically.

### 7.1 LegalMeetingService (canonical, full)

```python
"""
Service for Meeting workflow integration (FIMS pattern).
Template: grc.legal_meeting_lifecycle
  Stages: meeting_preparation → meeting_execution → meeting_closure
"""
import logging
from django.db import transaction
from apps.core.models import Meeting
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class LegalMeetingService:

    WORKFLOW_TEMPLATE_CODE = "grc.legal_meeting_lifecycle"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(self, meeting_id: str, submitter_id: str) -> Meeting:
        meeting = Meeting.objects.select_for_update().get(id=meeting_id)

        if meeting.workflow_plan_id:
            logger.info(
                "Meeting %s already has workflow plan %s — skipping",
                meeting.id, meeting.workflow_plan_id,
            )
            return meeting

        context = meeting.get_workflow_context()
        context['applicant_id'] = submitter_id         # FIMS pattern: set at service layer

        metadata = meeting.get_workflow_metadata()

        result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(meeting.id),
            metadata=metadata,
        )

        if result and result.plan_id:
            meeting.start_workflow(
                plan_id=result.plan_id,
                initial_stage=result.current_stage_name or '',
                stage_id=result.current_stage_id,
            )
            meeting.status = "scheduled"
            meeting.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for Meeting %s (stage: %s)",
                result.plan_id, meeting.id, result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for Meeting %s", meeting.id)

        return meeting

    def get_workflow_status(self, meeting_id: str) -> dict | None:
        entity = Meeting.objects.get(id=meeting_id)
        if not entity.workflow_plan_id:
            return None
        plan = self.workflow_client.get_plan(str(entity.workflow_plan_id))
        if not plan:
            return {
                'has_workflow': True,
                'workflow_plan_id': str(entity.workflow_plan_id),
                'status': 'unknown',
            }
        current_stage_data = next(
            (s for s in plan.stages if s.get('id') == plan.current_stage_id), None
        )
        return {
            'has_workflow': True,
            'plan_id': plan.plan_id,
            'workflow_plan_id': plan.plan_id,
            'status': plan.status,
            'current_stage': plan.current_stage_name,
            'current_stage_id': plan.current_stage_id,
            'current_stage_data': current_stage_data,
            'available_actions': current_stage_data.get('actions', []) if current_stage_data else [],
            'stages': plan.stages,
            'metadata': plan.metadata,
            'is_completed': plan.status in ('completed', 'cancelled'),
        }

    def get_workflow_history(self, meeting_id: str) -> list:
        entity = Meeting.objects.get(id=meeting_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

    @transaction.atomic
    def advance_workflow_stage(
        self, meeting_id: str, action: str, actor_id: str, comment: str = ''
    ) -> dict:
        entity = Meeting.objects.select_for_update().get(id=meeting_id)
        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this Meeting")

        plan = self.workflow_client.get_plan(str(entity.workflow_plan_id))
        if not plan:
            raise ValueError("Could not fetch workflow plan")

        stage_id = getattr(entity, 'workflow_stage_id', None) or plan.current_stage_id
        if not stage_id:
            raise ValueError("Could not determine current workflow stage")

        result = self.workflow_client.advance_stage(
            plan_id=str(entity.workflow_plan_id),
            stage_id=str(stage_id),
            action=action,
            actor_id=actor_id,
            comment=comment,
        )

        if not result:
            raise ValueError("Failed to execute workflow action")

        if result.next_stage_id:
            entity.update_workflow_stage(
                stage_name=result.next_stage_name or '',
                stage_id=result.next_stage_id,
            )
        if result.plan_status in ('completed', 'cancelled'):
            entity.complete_workflow()

        entity.save()

        return {
            'action': action,
            'new_stage_status': result.new_status,
            'plan_status': result.plan_status,
            'next_stage': result.next_stage_name,
            'next_stage_id': result.next_stage_id,
        }

    @transaction.atomic
    def cancel_workflow_plan(self, meeting_id: str, actor_id: str, reason: str = '') -> Meeting:
        entity = Meeting.objects.select_for_update().get(id=meeting_id)
        if not entity.workflow_plan_id:
            raise ValueError("No active workflow for this Meeting")

        success = self.workflow_client.cancel_plan(
            plan_id=str(entity.workflow_plan_id),
            actor_id=actor_id,
            reason=reason,
        )
        if not success:
            raise ValueError("Failed to cancel workflow")

        entity.cancel_workflow()
        entity.save()
        return entity
```

### 7.2 Other Service Classes — Declaration Only

Each of the following follows the `LegalMeetingService` pattern identically. Only the template code, model import, and status values in `submit_for_approval()` differ:

```python
# apps/core/services/legal_minutes_service.py
class LegalMinutesService:
    WORKFLOW_TEMPLATE_CODE = "grc.legal_minutes_approval"
    # Model: Minutes, initial status: "pending_approval"

# apps/core/services/legal_case_service.py
class LegalCaseService:
    WORKFLOW_TEMPLATE_CODE = "grc.legal_case_closure"
    # Models: CaseDefendant | CasePlaintiff  (pass model_class as param)
    # initial status: "pending_closure"

# apps/core/services/legal_filing_service.py
class LegalFilingService:
    WORKFLOW_TEMPLATE_CODE = "grc.legal_filing_approval"
    # Models: FilingDefendant | FilingPlaintiff
    # initial status: "pending_approval"

# apps/core/services/legal_settlement_service.py
class LegalSettlementService:
    WORKFLOW_TEMPLATE_CODE = "grc.legal_settlement_approval"
    # Models: SettlementDefendant | SettlementPlaintiff
    # initial status: "pending_approval"

# apps/core/services/legal_judgment_service.py
class LegalJudgmentService:
    WORKFLOW_TEMPLATE_CODE = "grc.legal_judgment_decision"
    # Models: JudgmentDefendant | JudgmentPlaintiff
    # initial status: "pending_review"
```

---

## 8. Standard 5 Service Methods

Every Legal service exposes exactly the same 5 methods. This is the FIMS contract — never reduce or rename:

| Method | Signature | Description |
|---|---|---|
| `submit_for_approval()` | `(entity_id: str, submitter_id: str) → Entity` | Creates WO plan; saves 5 `WorkflowMixin` fields; sets initial local status |
| `get_workflow_status()` | `(entity_id: str) → dict \| None` | Fetches live plan from WO; returns stages, current stage, available actions |
| `get_workflow_history()` | `(entity_id: str) → list` | Returns WO activity log for the plan |
| `advance_workflow_stage()` | `(entity_id: str, action: str, actor_id: str, comment: str = '') → dict` | Calls `workflow_client.advance_stage()`; updates `workflow_stage` fields |
| `cancel_workflow_plan()` | `(entity_id: str, actor_id: str, reason: str = '') → Entity` | Calls `workflow_client.cancel_plan()`; calls `entity.cancel_workflow()` |

### Shared/dual-model services (`LegalCaseService`, `LegalFilingService`, etc.)

Services that handle both Defendant and Plaintiff sides accept a `side` parameter or separate overloaded signatures. Recommended approach:

```python
class LegalCaseService:
    WORKFLOW_TEMPLATE_CODE = "grc.legal_case_closure"

    def _get_model(self, side: str):
        from apps.core.models import CaseDefendant, CasePlaintiff
        return CaseDefendant if side == 'defendant' else CasePlaintiff

    @transaction.atomic
    def submit_for_approval(
        self, entity_id: str, submitter_id: str, side: str = 'defendant'
    ):
        model = self._get_model(side)
        entity = model.objects.select_for_update().get(id=entity_id)
        # ... rest follows canonical pattern ...
```

---

## 9. Workflow View Pattern

Each entity exposes exactly **5 workflow endpoints** as class-based `APIView`s. The canonical pattern from `WorkingPaperWorkflowStatusView` / `WorkingPaperWorkflowActionView` is followed exactly.

### 5 standard view classes per entity

| View class suffix | HTTP method | URL path | Purpose |
|---|---|---|---|
| `SubmitForApprovalView` | `POST` | `/{entity}/{id}/submit-for-approval/` | Start WO plan |
| `WorkflowStatusView` | `GET` | `/{entity}/{id}/workflow-status/` | Live WO plan status |
| `WorkflowHistoryView` | `GET` | `/{entity}/{id}/workflow-history/` | WO activity log |
| `WorkflowActionView` | `POST` | `/{entity}/{id}/workflow-action/` | Advance stage (approve/reject/etc.) |
| `CancelWorkflowView` | `POST` | `/{entity}/{id}/cancel-workflow/` | Cancel active WO plan |

### Canonical view implementation (Meeting as example)

```python
# apps/api/views/legal_meeting_views.py

class LegalMeetingSubmitForApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        meeting = get_object_or_404(Meeting, id=pk)
        if meeting.workflow_plan_id:
            return Response(
                {"success": False, "error": {"message": "Workflow already started", "code": "WORKFLOW_EXISTS"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            meeting = LegalMeetingService().submit_for_approval(str(pk), str(user_id))
        except Exception as exc:
            logger.error("Error starting workflow for Meeting %s: %s", pk, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to start workflow", "details": str(exc)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        from apps.api.serializers.legal_serializers import MeetingSerializer
        return Response(
            {
                "success": True,
                "data": MeetingSerializer(meeting).data,
                "message": "Meeting workflow started",
                "workflow_plan_id": str(meeting.workflow_plan_id) if meeting.workflow_plan_id else None,
            },
            status=status.HTTP_200_OK,
        )


class LegalMeetingWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        meeting = get_object_or_404(Meeting, id=pk)
        if not meeting.workflow_plan_id:
            return Response(
                {"success": True, "data": {"has_workflow": False, "status": meeting.status}},
                status=status.HTTP_200_OK,
            )
        try:
            data = LegalMeetingService().get_workflow_status(str(pk))
        except Exception as exc:
            logger.error("Error fetching workflow status for Meeting %s: %s", pk, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to retrieve workflow status"}},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class LegalMeetingWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        meeting = get_object_or_404(Meeting, id=pk)
        if not meeting.workflow_plan_id:
            return Response(
                {"success": True, "data": {"has_workflow": False, "activity": []}},
                status=status.HTTP_200_OK,
            )
        try:
            activity = LegalMeetingService().get_workflow_history(str(pk))
        except Exception as exc:
            logger.error("Error fetching workflow history for Meeting %s: %s", pk, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to retrieve workflow history"}},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            {
                "success": True,
                "data": {
                    "has_workflow": True,
                    "workflow_plan_id": str(meeting.workflow_plan_id),
                    "activity": activity,
                },
            },
            status=status.HTTP_200_OK,
        )


class LegalMeetingWorkflowActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        action_name = request.data.get('action')
        if not action_name:
            return Response(
                {"success": False, "error": {"message": "'action' is required", "code": "ACTION_REQUIRED"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = LegalMeetingService().advance_workflow_stage(
                meeting_id=str(pk),
                action=action_name,
                actor_id=str(user_id),
                comment=request.data.get('comment', ''),
            )
        except ValueError as exc:
            return Response(
                {"success": False, "error": {"message": str(exc), "code": "WORKFLOW_ACTION_FAILED"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error executing workflow action for Meeting %s: %s", pk, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to execute workflow action"}},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class LegalMeetingCancelWorkflowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            LegalMeetingService().cancel_workflow_plan(
                meeting_id=str(pk),
                actor_id=str(user_id),
                reason=request.data.get('reason', ''),
            )
        except ValueError as exc:
            return Response(
                {"success": False, "error": {"message": str(exc), "code": "CANCEL_FAILED"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error cancelling workflow for Meeting %s: %s", pk, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to cancel workflow"}},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"success": True, "message": "Workflow cancelled"}, status=status.HTTP_200_OK)
```

---

## 10. URL Registration

All Legal workflow URLs live in `apps/api/urls/legal.py`. All use `<uuid:pk>` URL kwargs.

### Complete endpoint inventory — 50 workflow endpoints (10 entities × 5)

#### Governance domain

```python
# apps/api/urls/legal.py  (workflow section)

from apps.api.views.legal_meeting_views import (
    LegalMeetingSubmitForApprovalView,
    LegalMeetingWorkflowStatusView,
    LegalMeetingWorkflowHistoryView,
    LegalMeetingWorkflowActionView,
    LegalMeetingCancelWorkflowView,
)
from apps.api.views.legal_minutes_views import (
    LegalMinutesSubmitForApprovalView,
    LegalMinutesWorkflowStatusView,
    LegalMinutesWorkflowHistoryView,
    LegalMinutesWorkflowActionView,
    LegalMinutesCancelWorkflowView,
)

urlpatterns = [
    # ...CRUD patterns...

    # Meeting workflow (5 endpoints)
    path("meetings/<uuid:pk>/submit-for-approval/",  LegalMeetingSubmitForApprovalView.as_view(), name="legal-meeting-submit"),
    path("meetings/<uuid:pk>/workflow-status/",      LegalMeetingWorkflowStatusView.as_view(),    name="legal-meeting-workflow-status"),
    path("meetings/<uuid:pk>/workflow-history/",     LegalMeetingWorkflowHistoryView.as_view(),   name="legal-meeting-workflow-history"),
    path("meetings/<uuid:pk>/workflow-action/",      LegalMeetingWorkflowActionView.as_view(),    name="legal-meeting-workflow-action"),
    path("meetings/<uuid:pk>/cancel-workflow/",      LegalMeetingCancelWorkflowView.as_view(),    name="legal-meeting-cancel-workflow"),

    # Minutes workflow (5 endpoints)
    path("minutes/<uuid:pk>/submit-for-approval/",  LegalMinutesSubmitForApprovalView.as_view(), name="legal-minutes-submit"),
    path("minutes/<uuid:pk>/workflow-status/",      LegalMinutesWorkflowStatusView.as_view(),    name="legal-minutes-workflow-status"),
    path("minutes/<uuid:pk>/workflow-history/",     LegalMinutesWorkflowHistoryView.as_view(),   name="legal-minutes-workflow-history"),
    path("minutes/<uuid:pk>/workflow-action/",      LegalMinutesWorkflowActionView.as_view(),    name="legal-minutes-workflow-action"),
    path("minutes/<uuid:pk>/cancel-workflow/",      LegalMinutesCancelWorkflowView.as_view(),    name="legal-minutes-cancel-workflow"),
]
```

#### Litigation domain (Defendant side)

```python
    # CaseDefendant workflow (5 endpoints)
    path("cases/defendant/<uuid:pk>/submit-for-approval/", LegalCaseDefendantSubmitView.as_view(),   name="legal-case-defendant-submit"),
    path("cases/defendant/<uuid:pk>/workflow-status/",     LegalCaseDefendantStatusView.as_view(),   name="legal-case-defendant-workflow-status"),
    path("cases/defendant/<uuid:pk>/workflow-history/",    LegalCaseDefendantHistoryView.as_view(),  name="legal-case-defendant-workflow-history"),
    path("cases/defendant/<uuid:pk>/workflow-action/",     LegalCaseDefendantActionView.as_view(),   name="legal-case-defendant-workflow-action"),
    path("cases/defendant/<uuid:pk>/cancel-workflow/",     LegalCaseDefendantCancelView.as_view(),   name="legal-case-defendant-cancel-workflow"),

    # FilingDefendant workflow (5 endpoints)
    path("filings/defendant/<uuid:pk>/submit-for-approval/", LegalFilingDefendantSubmitView.as_view(),  name="legal-filing-defendant-submit"),
    path("filings/defendant/<uuid:pk>/workflow-status/",     LegalFilingDefendantStatusView.as_view(),  name="legal-filing-defendant-workflow-status"),
    path("filings/defendant/<uuid:pk>/workflow-history/",    LegalFilingDefendantHistoryView.as_view(), name="legal-filing-defendant-workflow-history"),
    path("filings/defendant/<uuid:pk>/workflow-action/",     LegalFilingDefendantActionView.as_view(),  name="legal-filing-defendant-workflow-action"),
    path("filings/defendant/<uuid:pk>/cancel-workflow/",     LegalFilingDefendantCancelView.as_view(),  name="legal-filing-defendant-cancel-workflow"),

    # SettlementDefendant workflow (5 endpoints)
    path("settlements/defendant/<uuid:pk>/submit-for-approval/", LegalSettlementDefendantSubmitView.as_view(),  name="legal-settlement-defendant-submit"),
    path("settlements/defendant/<uuid:pk>/workflow-status/",     LegalSettlementDefendantStatusView.as_view(),  name="legal-settlement-defendant-workflow-status"),
    path("settlements/defendant/<uuid:pk>/workflow-history/",    LegalSettlementDefendantHistoryView.as_view(), name="legal-settlement-defendant-workflow-history"),
    path("settlements/defendant/<uuid:pk>/workflow-action/",     LegalSettlementDefendantActionView.as_view(),  name="legal-settlement-defendant-workflow-action"),
    path("settlements/defendant/<uuid:pk>/cancel-workflow/",     LegalSettlementDefendantCancelView.as_view(),  name="legal-settlement-defendant-cancel-workflow"),

    # JudgmentDefendant workflow (5 endpoints)
    path("judgments/defendant/<uuid:pk>/submit-for-approval/", LegalJudgmentDefendantSubmitView.as_view(),  name="legal-judgment-defendant-submit"),
    path("judgments/defendant/<uuid:pk>/workflow-status/",     LegalJudgmentDefendantStatusView.as_view(),  name="legal-judgment-defendant-workflow-status"),
    path("judgments/defendant/<uuid:pk>/workflow-history/",    LegalJudgmentDefendantHistoryView.as_view(), name="legal-judgment-defendant-workflow-history"),
    path("judgments/defendant/<uuid:pk>/workflow-action/",     LegalJudgmentDefendantActionView.as_view(),  name="legal-judgment-defendant-workflow-action"),
    path("judgments/defendant/<uuid:pk>/cancel-workflow/",     LegalJudgmentDefendantCancelView.as_view(),  name="legal-judgment-defendant-cancel-workflow"),
```

#### Litigation domain (Plaintiff side)

```python
    # CasePlaintiff, FilingPlaintiff, SettlementPlaintiff, JudgmentPlaintiff
    # — identical pattern; replace "defendant" with "plaintiff" in all names above
    path("cases/plaintiff/<uuid:pk>/submit-for-approval/", LegalCasePlaintiffSubmitView.as_view(),  name="legal-case-plaintiff-submit"),
    # ... (5 endpoints each × 4 entities = 20 more)
```

### URL prefix

All Legal endpoints are mounted under `/api/v1/legal/` in the main `config/urls.py`:

```python
# config/urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path("api/v1/audit/", include("apps.api.urls.audit")),
    path("api/v1/legal/", include("apps.api.urls.legal")),   # Legal module
]
```

---

## 11. Kafka Event Integration

### When WO fires a stage-completion event

The GRC Kafka consumer (`apps/core/kafka_consumer/`) listens for WO stage events and updates the local entity status based on `metadata.status_on_complete` from the YAML template.

### Legal event handler pattern

```python
# apps/core/kafka_consumer/legal_workflow_handler.py

LEGAL_ENTITY_MODEL_MAP = {
    'meeting':              'apps.core.models.Meeting',
    'minutes':              'apps.core.models.Minutes',
    'case_defendant':       'apps.core.models.CaseDefendant',
    'case_plaintiff':       'apps.core.models.CasePlaintiff',
    'filing_defendant':     'apps.core.models.FilingDefendant',
    'filing_plaintiff':     'apps.core.models.FilingPlaintiff',
    'settlement_defendant': 'apps.core.models.SettlementDefendant',
    'settlement_plaintiff': 'apps.core.models.SettlementPlaintiff',
    'judgment_defendant':   'apps.core.models.JudgmentDefendant',
    'judgment_plaintiff':   'apps.core.models.JudgmentPlaintiff',
}

def handle_legal_workflow_stage_event(event: dict) -> None:
    """
    Called when WO fires a stage-completed event for a Legal entity.
    Updates local WorkflowMixin fields + entity status.
    """
    entity_type   = event.get('entity_type')
    entity_id     = event.get('entity_id')
    next_stage    = event.get('next_stage_name', '')
    next_stage_id = event.get('next_stage_id')
    plan_status   = event.get('plan_status')
    new_status    = event.get('metadata', {}).get('status_on_complete')

    model_path = LEGAL_ENTITY_MODEL_MAP.get(entity_type)
    if not model_path:
        logger.warning("Unrecognised legal entity_type in WO event: %s", entity_type)
        return

    from django.apps import apps
    app_label, model_name = model_path.rsplit('.', 1)
    Model = apps.get_model(app_label='core', model_name=model_name.lower())

    with transaction.atomic():
        entity = Model.objects.select_for_update().get(id=entity_id)
        entity.update_workflow_stage(stage_name=next_stage, stage_id=next_stage_id)
        if plan_status in ('completed', 'cancelled'):
            entity.complete_workflow()
        if new_status:
            entity.status = new_status
        entity.save(update_fields=[
            'workflow_stage', 'workflow_stage_id', 'workflow_completed_at', 'status', 'updated_at'
        ])
        logger.info(
            "Legal WO event handled: %s %s → stage=%s status=%s",
            entity_type, entity_id, next_stage, new_status,
        )
```

### Kafka topic & event registration

| Event type | Kafka topic | Handler |
|---|---|---|
| `grc.legal_meeting.workflow_stage_completed` | `grc-workflow-events` | `handle_legal_workflow_stage_event` |
| `grc.legal_minutes.workflow_stage_completed` | `grc-workflow-events` | `handle_legal_workflow_stage_event` |
| `grc.legal_case.workflow_stage_completed` | `grc-workflow-events` | `handle_legal_workflow_stage_event` |
| `grc.legal_filing.workflow_stage_completed` | `grc-workflow-events` | `handle_legal_workflow_stage_event` |
| `grc.legal_settlement.workflow_stage_completed` | `grc-workflow-events` | `handle_legal_workflow_stage_event` |
| `grc.legal_judgment.workflow_stage_completed` | `grc-workflow-events` | `handle_legal_workflow_stage_event` |

---

*Next: Part 5E — Serializers (all Legal entities)*
