# Legal Module — DB Tables & Design Decisions
**Service:** `grc-service`
**Module:** Legal
**Phase:** 5B-3 — DB Table Registry & Key Design Decisions
**References:** Part 1 (5B-1), Part 2 (5B-2), Base Models & Mixins (5A), LEGAL_DOMAIN_EXTRACTION.md

> This document is the single authoritative reference for all design decisions that cut
> across model definitions. Consult before implementing any Legal entity.

---

## Table of Contents

1. [DB Table Naming Convention](#1-db-table-naming-convention)
2. [Complete DB Table Registry](#2-complete-db-table-registry)
3. [UUID-Only External References](#3-uuid-only-external-references)
4. [Lookup Table Inventory & Usage](#4-lookup-table-inventory--usage)
5. [JSONField Usage Patterns](#5-jsonfield-usage-patterns)
6. [1:1 Monitoring Patterns — Auto-Created Paired Entities](#6-11-monitoring-patterns--auto-created-paired-entities)
7. [Base Class Composition Decisions](#7-base-class-composition-decisions)
8. [FK on_delete Decisions](#8-fk-on_delete-decisions)
9. [Partial UniqueConstraint Patterns](#9-partial-uniqueconstraint-patterns)
10. [CheckConstraint Decisions — Shared Discriminator Entities](#10-checkconstraint-decisions--shared-discriminator-entities)
11. [Computed Field Patterns — save() Overrides](#11-computed-field-patterns--save-overrides)
12. [Atomic Reference Number Generation](#12-atomic-reference-number-generation)
13. [Generic Audit Log Pattern](#13-generic-audit-log-pattern)
14. [Appeal Auto-Create Pattern](#14-appeal-auto-create-pattern)
15. [WorkflowMixin Assignment Decisions](#15-workflowmixin-assignment-decisions)
16. [External Service Integration Decisions](#16-external-service-integration-decisions)
17. [Status & State Machine Decisions](#17-status--state-machine-decisions)
18. [Soft-Delete Strategy](#18-soft-delete-strategy)
19. [Choices vs FK — Decision Rule](#19-choices-vs-fk--decision-rule)
20. [Other SRS-Derived Decisions](#20-other-srs-derived-decisions)

---

## 1. DB Table Naming Convention

### Rule

| Category | `db_table` prefix | File |
|---|---|---|
| Business entities (user-managed, workflow-capable) | `legal_` | `apps/core/models/legal_entities.py` |
| Lookup / reference tables (admin-seeded, enumeration-like) | `grc_` | `apps/core/models/lookups.py` |

### Rationale

- `legal_` mirrors the `audit_` prefix used by Internal Audit entities — one namespace per module.
- `grc_` is the shared lookup namespace already in use; Legal lookups extend the same `lookups.py` file.
- Using Django's `db_table` avoids Django's default `appname_modelname` naming (which would produce `core_committeetye`).

### Enforcement

Every Legal model class has an explicit `db_table` in its inner `Meta` class. No model is left to use Django's default.

```python
class GoverningBody(TimestampedModel, StatusMixin):
    class Meta:
        db_table = 'legal_governing_body'
```

---

## 2. Complete DB Table Registry

### 2.1 Lookup Tables — `grc_` prefix (in `lookups.py`)

| Model | `db_table` | Purpose |
|---|---|---|
| `CourtLevel` | `grc_court_level` | Court hierarchy (Magistrate, High, Appeal, Supreme) |
| `LitigationUrgencyLevel` | `grc_litigation_urgency_level` | Case urgency (Critical, High, Medium, Low) |
| `LitigationRiskLevel` | `grc_litigation_risk_level` | Case risk rating (High, Medium, Low) |
| `MeetingMode` | `grc_meeting_mode` | Physical / Virtual / Hybrid |
| `MeetingType` | `grc_meeting_type` | Ordinary / Extraordinary / Special + quorum_percentage |
| `DirectivePriority` | `grc_directive_priority` | Critical / High / Medium / Low |
| `DirectiveCategory` | `grc_directive_category` | Configurable action categories |

### 2.2 Business Entities — `legal_` prefix (in `legal_entities.py`)

#### Domain 1 — Governance Structure

| Model | `db_table` |
|---|---|
| `CommitteeType` | `legal_committee_type` |
| `GoverningBody` | `legal_governing_body` |
| `Member` | `legal_member` |

#### Domain 2 — Determinations & Approvals

| Model | `db_table` |
|---|---|
| `SubmissionForDetermination` | `legal_submission_for_determination` |

#### Domain 3 — Meeting Governance

| Model | `db_table` |
|---|---|
| `Meeting` | `legal_meeting` |
| `MeetingAgenda` | `legal_meeting_agenda` |
| `ConflictDeclaration` | `legal_conflict_declaration` |
| `MeetingParticipant` | `legal_meeting_participant` |
| `MeetingDirective` | `legal_meeting_directive` |
| `Minutes` | `legal_minutes` |
| `Resolution` | `legal_resolution` |

#### Domain 4 — Litigation (FCC Sued)

| Model | `db_table` |
|---|---|
| `CaseDefendant` | `legal_case_defendant` |
| `LitigationDirective` | `legal_litigation_directive` |
| `FilingDefendant` | `legal_filing_defendant` |
| `ResponseDefendant` | `legal_response_defendant` |
| `Hearing` | `legal_hearing` |
| `HearingReport` | `legal_hearing_report` |
| `SettlementDefendant` | `legal_settlement_defendant` |
| `JudgmentDefendant` | `legal_judgment_defendant` |
| `FinancialDefendant` | `legal_financial_defendant` |
| `TaskLitigation` | `legal_task_litigation` |

#### Domain 5 — Litigation (FCC Suing)

| Model | `db_table` |
|---|---|
| `CasePlaintiff` | `legal_case_plaintiff` |
| `FilingPlaintiff` | `legal_filing_plaintiff` |
| `ResponsePlaintiff` | `legal_response_plaintiff` |
| `SettlementPlaintiff` | `legal_settlement_plaintiff` |
| `JudgmentPlaintiff` | `legal_judgment_plaintiff` |
| `FinancialPlaintiff` | `legal_financial_plaintiff` |

> `Hearing`, `HearingReport`, `LitigationDirective`, `TaskLitigation` are **shared** between
> Domains 4 and 5 — each has a single table with a discriminator FK pattern (§10).

#### Domain 6 — Public Register

| Model | `db_table` |
|---|---|
| `PublicDecision` | `legal_public_decision` |

#### Cross-cutting

| Model | `db_table` |
|---|---|
| `LegalAuditLog` | `legal_audit_log` |

### 2.3 Total: 35 entities

- 7 lookup tables (`grc_`)
- 28 business entity tables (`legal_`)

---

## 3. UUID-Only External References

### Core Rule

**No `ForeignKey` to any external service model.** All references to users, staff, or corporate entities are stored as plain `UUIDField` values. Display names are resolved at read time via service clients with Redis caching.

```python
# CORRECT — UUID-only reference to IAM
created_by = models.UUIDField(help_text="User ID from IAM service")

# FORBIDDEN — FK to auth.User or any remote model
created_by = models.ForeignKey(User, on_delete=models.CASCADE)  # Never
```

### Why UUID-only

- grc-service does not own user or staff records — IAM and Corporate Service do.
- Creating FKs across microservice boundaries couples DB schemas.
- FK integrity is enforced at the application layer, not the DB.

### Complete UUID Reference Inventory

#### Single-value `UUIDField` references

| Entity | Field | Referenced Service | Nullable |
|---|---|---|---|
| `GoverningBody` | `created_by`, `modified_by` | IAM | `modified_by` only |
| `Member` | `user_id` | IAM / Corporate | No |
| `Member` | `created_by`, `modified_by` | IAM | `modified_by` only |
| `Meeting` | `secretary_id` | IAM | No |
| `Meeting` | `created_by`, `modified_by` | IAM | `modified_by` only |
| `MeetingParticipant` | `user_id` | IAM | No |
| `ConflictDeclaration` | `member_user_id` | IAM | No |
| `MeetingDirective` | `assigned_user_id` | IAM | Yes — may be org-unit only |
| `MeetingDirective` | `finally_closed_by` | IAM | Yes — null until closed |
| `SubmissionForDetermination` | `submitter_user_id` | IAM / Corporate | No |
| `Resolution` | `responsible_person_id` | IAM | Yes |
| `CaseDefendant` | `assigned_legal_manager_id` | IAM | Yes |
| `CasePlaintiff` | `assigned_legal_manager_id` | IAM | Yes |
| `LitigationDirective` | `issued_by_user_id` | IAM (DG) | No |
| `LegalAuditLog` | `actor_id` | IAM | No |
| All `TimestampedModel` subclasses | `created_by` | IAM | No |
| All `TimestampedModel` subclasses | `modified_by` | IAM | Yes |

#### List-valued `JSONField` references (multi-user UUID arrays)

| Entity | Field | Referenced Service | Notes |
|---|---|---|---|
| `GoverningBody` | `secretary_user_ids` | IAM | Multiple secretaries allowed (E1.3) |
| `CaseDefendant` | `assigned_legal_officer_ids` | IAM | Multiple officers per case |
| `CasePlaintiff` | `assigned_legal_officer_ids` | IAM | Multiple officers per case |
| `Minutes` | `approved_by` | IAM | Growing list of approver IDs |

#### Helper method pattern (UUID list membership check)

```python
# Used in views and serializers — never in model __str__ or save()
def is_secretary(self, user_id: str) -> bool:
    return str(user_id) in [str(uid) for uid in self.secretary_user_ids]
```

---

## 4. Lookup Table Inventory & Usage

### What qualifies as a Lookup Table

A model qualifies for `lookups.py` / `grc_` prefix if:
- It is **admin-seeded** (not user-created in normal operations).
- It carries **no workflow**.
- It has no `TimestampedModel` (no `created_by`).
- Its only mutable field is `is_active` (from `StatusMixin`).
- It acts as a **configurable label**, not a lifecycle entity.

`CommitteeType` does NOT qualify — it is user-managed admin data with a business lifecycle → `legal_committee_type`.

### Lookup Models — Summary

| Model | Key extra field | Used by |
|---|---|---|
| `CourtLevel` | — | `CaseDefendant.court_level`, `CasePlaintiff.court_level` |
| `LitigationUrgencyLevel` | — | `CaseDefendant.urgency_level`, `CasePlaintiff.urgency_level` |
| `LitigationRiskLevel` | — | `CaseDefendant.risk_level` (optional), `CasePlaintiff.risk_level` |
| `MeetingMode` | — | `Meeting.meeting_mode` |
| `MeetingType` | `quorum_percentage` (DecimalField) | `Meeting.meeting_type` — drives quorum threshold |
| `DirectivePriority` | — | `MeetingDirective.directive_priority` |
| `DirectiveCategory` | — | `MeetingDirective.directive_category` (optional FK) |

### FK on_delete for all lookup FKs

All FKs from business entities → lookup tables use `on_delete=PROTECT`. This prevents accidental deletion of a lookup value that is in use:

```python
meeting_mode = models.ForeignKey(
    MeetingMode,
    on_delete=models.PROTECT,
    related_name='meetings',
)
```

### MeetingType.quorum_percentage — special case

`MeetingType` carries a `quorum_percentage` field (DecimalField, max_digits=5, decimal_places=2).
The `Meeting.save()` override reads this field to auto-calculate `quorum_threshold_count`.

```python
# In Meeting.save()
try:
    pct = self.meeting_type.quorum_percentage          # FK traversal — DB hit
    total = self.governing_body.members.filter(is_active=True).count()
    self.calculated_quorum_threshold = math.ceil(total * pct / 100)
    if 'calculated_quorum_threshold' not in (update_fields or []):
        update_fields = list(update_fields or []) + ['calculated_quorum_threshold']
except (MeetingType.DoesNotExist, GoverningBody.DoesNotExist):
    pass
```

---

## 5. JSONField Usage Patterns

### When to use JSONField

| Scenario | JSONField type | Example |
|---|---|---|
| List of UUIDs referencing an external service | `JSONField(default=list)` | `secretary_user_ids`, `assigned_legal_officer_ids` |
| List of document reference UUIDs (DRS) | `JSONField(default=list)` | `initiation_documents`, `attachments`, `supporting_documents` |
| List of approver UUIDs (growing) | `JSONField(default=list)` | `Minutes.approved_by` |
| Sub-records without their own lifecycle | `JSONField(default=list)` | `FinancialDefendant.recoveries`, `FinancialDefendant.payments` |

### When NOT to use JSONField

- When the items need their own workflow, status, or FK relationships → use a proper FK model.
- When the items need to be filtered/joined at the DB level → use a FK model + index.
- When order or position matters and needs sorting guarantees → consider a through-table with `order` field.

### JSONField sub-record schema — Financial payments/recoveries

`FinancialDefendant.payments` and `FinancialDefendant.recoveries` store a list of objects:

```json
[
  {
    "date": "2025-04-01",
    "amount": "150000.00",
    "reference": "TRF/2025/001",
    "status": "processed"
  }
]
```

- **Validated** in the serializer with a nested `Serializer` class, not in the model.
- **Not** a DB-indexed field — only surfaced for display on the Financials tab.
- `status` choices: `requested`, `approved`, `processed`.

### JSONField initialisation — Never use mutable defaults

```python
# CORRECT
attachments = models.JSONField(default=list)

# FORBIDDEN — all instances share the same list object
attachments = models.JSONField(default=[])
```

---

## 6. 1:1 Monitoring Patterns — Auto-Created Paired Entities

### Concept

Several entities are **automatically created** by the system at the moment a root entity is created. These form "monitoring cards" — they exist exclusively to track a parallel concern (financials, workflow record) that belongs 1:1 to the root.

### Pattern A — Financial record auto-created on case registration

Both `FinancialDefendant` and `FinancialPlaintiff` are created inside `transaction.atomic()` when their parent case is first saved:

```python
# In the case create view — AFTER case.save()
with transaction.atomic():
    case = serializer.save(created_by=request.user_id)
    FinancialDefendant.objects.create(
        case_defendant=case,
        created_by=request.user_id,
        claim_amount=case.claim_amount,   # copied from case at registration
    )
```

- `FinancialDefendant` uses `OneToOneField(CaseDefendant, on_delete=CASCADE)` — not a regular FK.
- The `OneToOneField` guarantees exactly one financial record per case at the DB level.
- The financial record is **never created via its own API endpoint** — only via the case registration flow.
- Deleting the case cascades to delete the financial record.

### Pattern B — Resolution auto-created from agenda outcome

`Resolution` is system-created when `MeetingAgenda.outcome` is recorded:

```python
# In the agenda outcome update view
with transaction.atomic():
    agenda.outcome = validated_data['outcome']
    agenda.save(update_fields=['outcome', 'updated_at'])
    Resolution.objects.get_or_create(
        agenda_item=agenda,
        defaults={
            'meeting': agenda.meeting,
            'resolution_text': validated_data.get('resolution_notes', ''),
            'status': 'noted',
            'created_by': request.user_id,
        }
    )
```

- `Resolution.agenda_item` is a `OneToOneField` — prevents duplicate resolutions.
- `get_or_create` is safe for retry; the `OneToOneField` acts as the uniqueness guard.

### Pattern C — Minutes: one meeting, one Minutes record

`Minutes` uses `OneToOneField(Meeting, on_delete=CASCADE, related_name='minutes')`. The Secretary creates it explicitly; the system does not auto-create it. The `OneToOneField` prevents accidental duplicates.

### Summary of 1:1 Entities

| 1:1 Entity | Parent | Creation trigger | OneToOneField target |
|---|---|---|---|
| `FinancialDefendant` | `CaseDefendant` | Case registration (auto) | `CaseDefendant` |
| `FinancialPlaintiff` | `CasePlaintiff` | Case registration (auto) | `CasePlaintiff` |
| `Resolution` | `MeetingAgenda` | Agenda outcome recorded (auto) | `MeetingAgenda` |
| `Minutes` | `Meeting` | Secretary drafts (explicit) | `Meeting` |
| `SettlementDefendant` | `CaseDefendant` | Legal Officer registers settlement (explicit) | via partial UniqueConstraint |
| `SettlementPlaintiff` | `CasePlaintiff` | Legal Officer registers settlement (explicit) | via partial UniqueConstraint |
| `JudgmentDefendant` | `CaseDefendant` | Legal Officer records judgment (explicit) | via partial UniqueConstraint |
| `JudgmentPlaintiff` | `CasePlaintiff` | Legal Officer records judgment (explicit) | via partial UniqueConstraint |

> `Settlement` and `Judgment` use partial `UniqueConstraint` (not `OneToOneField`) because
> they support soft-delete: only one active record per case, but inactive ones are retained.

---

## 7. Base Class Composition Decisions

### Decision matrix — choosing base classes

| Question | Answer → Action |
|---|---|
| Is it a business entity (user-submitted, has `created_by`)? | Yes → include `TimestampedModel` |
| Is it admin/system seed data (no explicit user creator)? | Yes → use `BaseModel` only |
| Does it support soft-delete (`is_active`)? | Yes → include `StatusMixin` |
| Does it enter a Work Orchestration workflow plan? | Yes → include `WorkflowMixin` |
| Is it a pure audit/event log? | Yes → `BaseModel` only (no mixin) |

### Composition table — all Legal entities

| Entity | `TimestampedModel` | `StatusMixin` | `WorkflowMixin` |
|---|---|---|---|
| `CommitteeType` | — | ✓ | — |
| `GoverningBody` | ✓ | ✓ | — |
| `Member` | ✓ | ✓ | — |
| `SubmissionForDetermination` | ✓ | ✓ | — |
| `Meeting` | ✓ | ✓ | ✓ |
| `MeetingAgenda` | ✓ | ✓ | — |
| `ConflictDeclaration` | ✓ | ✓ | — |
| `MeetingParticipant` | ✓ | ✓ | — |
| `MeetingDirective` | ✓ | ✓ | — |
| `Minutes` | ✓ | ✓ | ✓ |
| `Resolution` | ✓ | ✓ | — |
| `CaseDefendant` | ✓ | ✓ | ✓ |
| `LitigationDirective` | ✓ | ✓ | — |
| `FilingDefendant` | ✓ | ✓ | ✓ |
| `ResponseDefendant` | ✓ | ✓ | — |
| `Hearing` | ✓ | ✓ | — |
| `HearingReport` | ✓ | ✓ | — |
| `SettlementDefendant` | ✓ | ✓ | ✓ |
| `JudgmentDefendant` | ✓ | ✓ | ✓ |
| `FinancialDefendant` | ✓ | — | — |
| `TaskLitigation` | ✓ | ✓ | — |
| `CasePlaintiff` | ✓ | ✓ | ✓ |
| `FilingPlaintiff` | ✓ | ✓ | ✓ |
| `ResponsePlaintiff` | ✓ | ✓ | — |
| `SettlementPlaintiff` | ✓ | ✓ | ✓ |
| `JudgmentPlaintiff` | ✓ | ✓ | ✓ |
| `FinancialPlaintiff` | ✓ | — | — |
| `PublicDecision` | ✓ | ✓ | — |
| `LegalAuditLog` | — | — | — |
| **Lookup tables** (7) | — | ✓ | — |

**Notes:**
- `FinancialDefendant` and `FinancialPlaintiff` omit `StatusMixin` — they cannot be soft-deleted independently; they live and die with the parent case via `CASCADE`.
- `LegalAuditLog` uses only `BaseModel` — audit log entries are immutable, write-once. No soft-delete, no workflow.
- `CommitteeType` omits `TimestampedModel` — it is admin-configured system data, not user-submitted.

---

## 8. FK on_delete Decisions

### Decision rules

| Scenario | `on_delete` choice | Rationale |
|---|---|---|
| Child cannot exist without its parent (core ownership) | `CASCADE` | Deleting the parent destroys orphaned children |
| Parent must not be deleted while children exist | `PROTECT` | Prevents accidental data loss; requires manual cleanup |
| Optional cross-reference that becomes irrelevant if parent is gone | `SET_NULL` | Preserves the child; clears the link |

### Complete on_delete reference

| FK field | Parent model | `on_delete` | Why |
|---|---|---|---|
| `GoverningBody.committee_type` | `CommitteeType` | `PROTECT` | Cannot delete type in use |
| `Member.governing_body` | `GoverningBody` | `CASCADE` | Members are owned by the body |
| `Meeting.governing_body` | `GoverningBody` | `PROTECT` | Cannot delete body with meetings |
| `Meeting.meeting_mode` | `MeetingMode` | `PROTECT` | Lookup in use |
| `Meeting.meeting_type` | `MeetingType` | `PROTECT` | Lookup in use |
| `MeetingAgenda.meeting` | `Meeting` | `CASCADE` | Agenda owned by meeting |
| `MeetingAgenda.submission` | `SubmissionForDetermination` | `PROTECT` | Cannot delete submission referenced in agenda |
| `ConflictDeclaration.agenda_item` | `MeetingAgenda` | `CASCADE` | Declaration owned by agenda item |
| `MeetingParticipant.meeting` | `Meeting` | `CASCADE` | Participant record owned by meeting |
| `MeetingDirective.meeting` | `Meeting` | `CASCADE` | Directive owned by meeting |
| `MeetingDirective.agenda_item` | `MeetingAgenda` | `SET_NULL` | Directive survives if agenda item removed |
| `MeetingDirective.directive_priority` | `DirectivePriority` | `PROTECT` | Lookup in use |
| `MeetingDirective.directive_category` | `DirectiveCategory` | `SET_NULL` | Category is optional |
| `MeetingDirective.finally_closed_in_meeting` | `Meeting` | `SET_NULL` | Closure ref becomes irrelevant if meeting gone |
| `Minutes.meeting` (OneToOneField) | `Meeting` | `CASCADE` | Minutes owned by meeting |
| `Resolution.meeting` | `Meeting` | `CASCADE` | Resolution owned by meeting |
| `Resolution.agenda_item` (OneToOneField) | `MeetingAgenda` | `CASCADE` | Resolution owned by agenda item |
| `SubmissionForDetermination.target_body` | `GoverningBody` | `PROTECT` | Cannot delete body with submissions |
| `SubmissionForDetermination.meeting` | `Meeting` | `SET_NULL` | Submission survives if meeting deleted |
| `CaseDefendant.court_level` | `CourtLevel` | `PROTECT` | Lookup in use |
| `CaseDefendant.urgency_level` | `LitigationUrgencyLevel` | `PROTECT` | Lookup in use |
| `CaseDefendant.risk_level` | `LitigationRiskLevel` | `PROTECT` | Lookup in use |
| `FilingDefendant.case_defendant` | `CaseDefendant` | `CASCADE` | Filing owned by case |
| `ResponseDefendant.case_defendant` | `CaseDefendant` | `CASCADE` | Response owned by case |
| `Hearing.case_defendant` | `CaseDefendant` | `CASCADE` | Hearing owned by case |
| `Hearing.case_plaintiff` | `CasePlaintiff` | `CASCADE` | Hearing owned by case |
| `HearingReport.hearing` | `Hearing` | `CASCADE` | Report owned by hearing |
| `SettlementDefendant.case_defendant` | `CaseDefendant` | `CASCADE` | Settlement owned by case |
| `JudgmentDefendant.case_defendant` | `CaseDefendant` | `CASCADE` | Judgment owned by case |
| `JudgmentDefendant.appeal_filing` | `FilingDefendant` | `SET_NULL` | Auto-created appeal filing ref |
| `JudgmentDefendant.appeal_task` | `TaskLitigation` | `SET_NULL` | Auto-created appeal task ref |
| `FinancialDefendant.case_defendant` (OTO) | `CaseDefendant` | `CASCADE` | Financial record owned by case |
| `TaskLitigation.case_defendant` | `CaseDefendant` | `CASCADE` | Task owned by case |
| `TaskLitigation.case_plaintiff` | `CasePlaintiff` | `CASCADE` | Task owned by case |
| `FilingPlaintiff.case_plaintiff` | `CasePlaintiff` | `CASCADE` | Same pattern as Defendant side |
| `ResponsePlaintiff.case_plaintiff` | `CasePlaintiff` | `CASCADE` | Same |
| `SettlementPlaintiff.case_plaintiff` | `CasePlaintiff` | `CASCADE` | Same |
| `JudgmentPlaintiff.case_plaintiff` | `CasePlaintiff` | `CASCADE` | Same |
| `JudgmentPlaintiff.appeal_filing` | `FilingPlaintiff` | `SET_NULL` | Same as defendant |
| `JudgmentPlaintiff.appeal_task` | `TaskLitigation` | `SET_NULL` | Same as defendant |
| `FinancialPlaintiff.case_plaintiff` (OTO) | `CasePlaintiff` | `CASCADE` | Same |
| `LitigationDirective.case_defendant` | `CaseDefendant` | `CASCADE` | Directive owned by case |
| `LitigationDirective.case_plaintiff` | `CasePlaintiff` | `CASCADE` | Directive owned by case |
| `PublicDecision.meeting` | `Meeting` | `PROTECT` | Cannot delete meeting with published decisions |

---

## 9. Partial UniqueConstraint Patterns

### Why partial constraints (not simple `unique=True`)

All uniqueness rules in the Legal module are scoped to **active records only** (`is_active=True`). Using a plain `unique=True` would prevent soft-deleted records from ever being recreated.

### Pattern

```python
from django.db.models import Q, UniqueConstraint

class Meta:
    db_table = 'legal_member'
    constraints = [
        UniqueConstraint(
            fields=['governing_body', 'user_id'],
            condition=Q(is_active=True),
            name='legal_member_active_body_user_uniq',
        )
    ]
```

### Complete Partial UniqueConstraint Catalogue

| Entity | Fields | Condition | Constraint name |
|---|---|---|---|
| `Member` | `(governing_body, user_id)` | `is_active=True` | `legal_member_active_body_user_uniq` |
| `Meeting` | `(governing_body, meeting_number)` | `is_active=True` | `legal_meeting_active_body_number_uniq` |
| `MeetingAgenda` | `(meeting, submission)` | `is_active=True` | `legal_meeting_agenda_active_meeting_submission_uniq` |
| `MeetingParticipant` | `(meeting, user_id)` | `is_active=True` | `legal_meeting_participant_active_meeting_user_uniq` |
| `ConflictDeclaration` | `(agenda_item, member_user_id)` | `is_active=True` | `legal_conflict_declaration_active_item_member_uniq` |
| `SettlementDefendant` | `(case_defendant,)` | `is_active=True` | `legal_settlement_defendant_active_case_uniq` |
| `SettlementPlaintiff` | `(case_plaintiff,)` | `is_active=True` | `legal_settlement_plaintiff_active_case_uniq` |
| `JudgmentDefendant` | `(case_defendant,)` | `is_active=True` | `legal_judgment_defendant_active_case_uniq` |
| `JudgmentPlaintiff` | `(case_plaintiff,)` | `is_active=True` | `legal_judgment_plaintiff_active_case_uniq` |
| `CaseDefendant` | `(reference_number,)` | `is_active=True` | `legal_case_defendant_active_ref_uniq` |
| `CasePlaintiff` | `(reference_number,)` | `is_active=True` | `legal_case_plaintiff_active_ref_uniq` |

---

## 10. CheckConstraint Decisions — Shared Discriminator Entities

### Problem

Three entities — `Hearing`, `LitigationDirective`, and `TaskLitigation` — logically belong to either a `CaseDefendant` or a `CasePlaintiff`, but never both and never neither. Rather than duplicating identical model structures (e.g., `HearingDefendant` + `HearingPlaintiff`), a **discriminator FK pattern** is used.

### Pattern (identical for all three)

```python
class Hearing(TimestampedModel, StatusMixin):
    case_defendant = models.ForeignKey(
        'CaseDefendant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='hearings'
    )
    case_plaintiff = models.ForeignKey(
        'CasePlaintiff', on_delete=models.CASCADE,
        null=True, blank=True, related_name='hearings'
    )
    # ... other fields ...

    class Meta:
        db_table = 'legal_hearing'
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(case_defendant__isnull=False, case_plaintiff__isnull=True) |
                    models.Q(case_defendant__isnull=True,  case_plaintiff__isnull=False)
                ),
                name='legal_hearing_exactly_one_case',
            )
        ]
```

### Discriminator CheckConstraint catalogue

| Entity | Constraint name | Check |
|---|---|---|
| `Hearing` | `legal_hearing_exactly_one_case` | XOR — exactly one of `case_defendant`/`case_plaintiff` non-null |
| `LitigationDirective` | `legal_litigation_directive_exactly_one_case` | Same XOR pattern |
| `TaskLitigation` | `legal_task_litigation_exactly_one_case` | Same XOR pattern |

### Querying shared entities

```python
# All hearings for a defendant case
Hearing.objects.filter(case_defendant=case, is_active=True)

# All hearings for a plaintiff case
Hearing.objects.filter(case_plaintiff=case, is_active=True)

# All open tasks across all defendant cases
TaskLitigation.objects.filter(
    case_defendant__isnull=False,
    status='open',
    is_active=True,
)
```

---

## 11. Computed Field Patterns — save() Overrides

### Rule

Any field whose value is **derived** from other model data must be computed in `save()`. The computation must check `update_fields` to avoid redundant recalculation and must extend `update_fields` with the names of the computed fields.

### Reference pattern (from Internal Audit)

```python
def save(self, *args, **kwargs):
    update_fields = kwargs.get('update_fields')
    if update_fields is None or 'source_field' in update_fields:
        self.computed_field = self._calculate()
        if update_fields is not None:
            kwargs['update_fields'] = list(update_fields) + ['computed_field', 'updated_at']
    super().save(*args, **kwargs)
```

### Legal module save() overrides

#### 1. `Meeting.save()` — quorum threshold calculation

```python
def save(self, *args, **kwargs):
    update_fields = kwargs.get('update_fields')
    recompute = update_fields is None or any(
        f in update_fields for f in ['meeting_type', 'governing_body']
    )
    if recompute:
        try:
            total = self.governing_body.members.filter(is_active=True).count()
            pct   = self.meeting_type.quorum_percentage
            self.calculated_quorum_threshold = math.ceil(total * float(pct) / 100)
            if update_fields is not None:
                kwargs['update_fields'] = list(update_fields) + [
                    'calculated_quorum_threshold', 'updated_at'
                ]
        except Exception:
            pass
    super().save(*args, **kwargs)
```

**Computed field:** `calculated_quorum_threshold` (IntegerField) — the absolute member count required for quorum.

#### 2. `Meeting.save()` — quorum_met flag

`quorum_met` (BooleanField) is updated by the view when `MeetingParticipant.invitation_status` changes, using `F()` expressions to avoid race conditions:

```python
# In MeetingParticipant update view — not in save()
accepted_count = meeting.participants.filter(
    invitation_status='accepted', is_active=True
).count()
meeting.quorum_met = accepted_count >= meeting.calculated_quorum_threshold
meeting.save(update_fields=['quorum_met', 'updated_at'])
```

**Rule:** `quorum_met` is never recalculated inside `Meeting.save()` — only in response to explicit participant RSVP events.

#### 3. `HearingReport.save()` → propagates to parent case

`next_hearing_date` is propagated upward from `HearingReport` via view logic, not `save()`:

```python
# In HearingReport create/update view
report = serializer.save(created_by=request.user_id)
case = report.hearing.case_defendant or report.hearing.case_plaintiff
if report.next_hearing_date:
    case.next_hearing_date = report.next_hearing_date
    case.save(update_fields=['next_hearing_date', 'updated_at'])
```

This keeps the propagation traceable and avoids cascading `save()` chains.

---

## 12. Atomic Reference Number Generation

### Requirement (E8.2)

Case reference numbers must be sequential, unique per year, and race-condition-free. Format:
- FCC Sued: `FCC/SUED/{YYYY}/{NNN}` (e.g., `FCC/SUED/2025/001`)
- FCC Suing: `FCC/SUING/{YYYY}/{NNN}` (e.g., `FCC/SUING/2025/042`)

### Implementation pattern

Use `select_for_update()` with a counter model or PostgreSQL sequence function inside `transaction.atomic()`:

```python
def generate_case_reference(case_type: str, year: int) -> str:
    """
    Generates an atomic, sequential reference number per case type per year.
    Must be called inside transaction.atomic().
    """
    from apps.core.models.counters import LegalCaseCounter   # counter model
    counter, _ = LegalCaseCounter.objects.select_for_update().get_or_create(
        case_type=case_type,
        year=year,
        defaults={'sequence': 0},
    )
    counter.sequence += 1
    counter.save(update_fields=['sequence'])
    prefix = 'SUED' if case_type == 'defendant' else 'SUING'
    return f'FCC/{prefix}/{year}/{counter.sequence:03d}'
```

```python
# In the case create view
with transaction.atomic():
    reference = generate_case_reference('defendant', timezone.now().year)
    case = CaseDefendant.objects.create(
        reference_number=reference,
        created_by=request.user_id,
        ...
    )
    FinancialDefendant.objects.create(case_defendant=case, created_by=request.user_id)
```

### Meeting number auto-generation (E3.1)

Meetings use the same atomic counter pattern, scoped per `GoverningBody`:

```python
def generate_meeting_number(governing_body_id) -> str:
    from apps.core.models.counters import MeetingCounter
    counter, _ = MeetingCounter.objects.select_for_update().get_or_create(
        governing_body_id=governing_body_id,
        defaults={'sequence': 0},
    )
    counter.sequence += 1
    counter.save(update_fields=['sequence'])
    return f'{counter.sequence:04d}'
```

Both counter models (`LegalCaseCounter`, `MeetingCounter`) are lightweight models in `apps/core/models/counters.py` with `db_table = 'grc_legal_case_counter'` and `'grc_meeting_counter'` respectively.

---

## 13. Generic Audit Log Pattern

### Rationale

Rather than creating 28 separate audit log tables, `LegalAuditLog` uses a single generic table with a `(entity_type, entity_id)` pair to point at any Legal entity. This is the same approach used by Internal Audit's `AuditLog` model.

### Model composition

```python
class LegalAuditLog(BaseModel):   # BaseModel only — no TimestampedModel, no StatusMixin
    entity_type   = models.CharField(max_length=80, db_index=True)
    entity_id     = models.UUIDField(db_index=True)
    action        = models.CharField(max_length=80)   # e.g. 'status_changed', 'created'
    actor_id      = models.UUIDField()                # IAM user UUID
    actor_role    = models.CharField(max_length=80, blank=True)
    previous_data = models.JSONField(null=True, blank=True)
    new_data      = models.JSONField(null=True, blank=True)
    timestamp     = models.DateTimeField(auto_now_add=True, db_index=True)
    notes         = models.TextField(blank=True)

    class Meta:
        db_table  = 'legal_audit_log'
        ordering  = ['-timestamp']
        indexes   = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]
```

### Why `BaseModel` only (no `TimestampedModel`, no `StatusMixin`)

- `TimestampedModel` adds `created_by`/`modified_by` which is redundant — `actor_id` serves the same purpose.
- `StatusMixin` adds `is_active`. Audit log entries are **immutable and permanent** — they are never soft-deleted.
- No `updated_at` — log entries are write-once.

### Usage pattern

```python
# Log a status change — called from the view after every state transition
LegalAuditLog.objects.create(
    entity_type='case_defendant',
    entity_id=case.id,
    action='status_changed',
    actor_id=request.user_id,
    actor_role=request.user_role,
    previous_data={'status': old_status},
    new_data={'status': case.status},
)
```

### Querying

```python
# All events for a specific case
LegalAuditLog.objects.filter(
    entity_type='case_defendant',
    entity_id=case_id,
).order_by('-timestamp')

# All audit events for Minutes across all meetings
LegalAuditLog.objects.filter(entity_type='minutes').select_related()
```

---

## 14. Appeal Auto-Create Pattern

### Trigger (C10, E12.3)

When DG sets `JudgmentDefendant.dg_decision = 'appeal'` or `JudgmentPlaintiff.dg_decision = 'appeal'`, the view must atomically create two child entities and back-link them to the judgment.

### Implementation pattern

```python
# In JudgmentDefendant update view — dg_decision = 'appeal' path
with transaction.atomic():
    judgment.dg_decision = 'appeal'
    judgment.appeal_due_date = validated_data['appeal_due_date']
    judgment.save(update_fields=['dg_decision', 'appeal_due_date', 'updated_at'])

    appeal_filing = FilingDefendant.objects.create(
        case_defendant=judgment.case_defendant,
        filing_type='notice_of_appeal',
        status='draft',
        title=f'Notice of Appeal — {judgment.case_defendant.reference_number}',
        created_by=request.user_id,
    )
    appeal_task = TaskLitigation.objects.create(
        case_defendant=judgment.case_defendant,
        title=f'File Notice of Appeal by {judgment.appeal_due_date}',
        due_date=judgment.appeal_due_date,
        assigned_to_user_id=judgment.case_defendant.assigned_legal_officer_ids[0],
        status='open',
        priority='critical',
        related_entity_type='filing_defendant',
        related_entity_id=appeal_filing.id,
        created_by=request.user_id,
    )
    judgment.appeal_filing = appeal_filing
    judgment.appeal_task   = appeal_task
    judgment.save(update_fields=['appeal_filing', 'appeal_task', 'updated_at'])

    LegalAuditLog.objects.create(
        entity_type='judgment_defendant',
        entity_id=judgment.id,
        action='appeal_initiated',
        actor_id=request.user_id,
        new_data={'appeal_due_date': str(judgment.appeal_due_date)},
    )
```

**Key rules:**
- Entire operation inside `transaction.atomic()` — all three saves succeed or all roll back.
- `FilingDefendant` and `TaskLitigation` are created in the correct order (filing first, then task with `related_entity_id` pointing to the filing).
- `LegalAuditLog` entry created at the end, inside the same transaction.
- Identical pattern applies to `JudgmentPlaintiff` → `FilingPlaintiff` + `TaskLitigation`.

---

## 15. WorkflowMixin Assignment Decisions

### Which entities use WorkflowMixin and why

| Entity | WO Template | Reason for workflow |
|---|---|---|
| `Meeting` | `grc.legal_meeting_lifecycle` | Multi-stage meeting lifecycle requires WO tracking |
| `Minutes` | `grc.legal_minutes_approval` | Approval-by-committee workflow with sign-off threshold |
| `CaseDefendant` | `grc.legal_case_closure` | DG-approved case closure workflow |
| `CasePlaintiff` | `grc.legal_case_closure` | Same |
| `FilingDefendant` | `grc.legal_filing_approval` | Two-stage approval (LM → DG) |
| `FilingPlaintiff` | `grc.legal_filing_approval` | Same |
| `SettlementDefendant` | `grc.legal_settlement_approval` | DG approval gating |
| `SettlementPlaintiff` | `grc.legal_settlement_approval` | Same |
| `JudgmentDefendant` | `grc.legal_judgment_decision` | DG Accept/Appeal decision |
| `JudgmentPlaintiff` | `grc.legal_judgment_decision` | Same |

### Required WorkflowMixin overrides — per entity

Every `WorkflowMixin` entity must implement all three methods:

```python
def get_workflow_context(self):
    return {
        'entity_type': 'case_defendant',
        'entity_id': str(self.id),
        'reference_number': self.reference_number,
        # entity-specific context ...
    }

def get_workflow_metadata(self):
    return add_entity_detail_path_to_metadata(
        metadata={'template': 'grc.legal_case_closure'},
        entity_type='case_defendant',
        entity_id=str(self.id),
    )

def log_workflow_action(self, action, actor_id, notes=''):
    LegalAuditLog.objects.create(
        entity_type='case_defendant',
        entity_id=self.id,
        action=action,
        actor_id=actor_id,
        notes=notes,
    )
```

`add_entity_detail_path_to_metadata` is imported from `apps.core.workflow_entity_paths`.

---

## 16. External Service Integration Decisions

### 16.1 IAM Service — User resolution

- **What is stored:** UUID only.
- **How resolved:** Views call `IAMClient.get_user_profile(user_id)` → cached in Redis.
- **How set in models:** Views extract `request.user_id` (set by `JWTPermissionMiddleware`) and pass it as `created_by` or `modified_by` to `serializer.save(created_by=request.user_id)`.
- **Never:** `save()` overrides do not touch `created_by` or `modified_by`.

### 16.2 Corporate Service — Member sync (Kafka)

- `Member` entity is a **local snapshot** sourced from the Corporate Service.
- Sync mechanism: Kafka consumer on topic `corporate.events` updates `Member` records in grc-service.
- Sync is one-way: Corporate Service → grc-service. grc-service never pushes to Corporate Service.
- Relevant fields synced: `user_id`, `email`, `department`, `full_name`, `is_active`, `left_date`.

### 16.3 Document Records Service (DRS) — Document references

- **What is stored:** UUID only (`UUIDField` or `JSONField(default=list)`).
- **What is NOT stored:** File bytes, file names, file URLs.
- **How resolved:** Serializers call `DRSClient.get_document_info(document_id)` at read time.
- **Mandatory document fields:** `FilingDefendant.document_id`, `FilingPlaintiff.document_id`, `SettlementDefendant.agreement_document_id`, `SettlementPlaintiff.agreement_document_id`.
- **Optional single document fields:** `HearingReport.attachment_id`, `JudgmentDefendant.document_id`, `JudgmentPlaintiff.document_id`, `MeetingDirective.evidence_document_id`.
- **Optional multi-document fields (JSONField lists):** `SubmissionForDetermination.supporting_documents`, `CaseDefendant.initiation_documents`, `CasePlaintiff.initiation_documents`, `LitigationDirective.attachments`, `MeetingAgenda.documents`, `Minutes.attachments`, `Resolution.attachments`.

### 16.4 Work Orchestration Service (WO)

- WorkflowMixin provides `start_workflow()`, `update_workflow_stage()`, `complete_workflow()`, `cancel_workflow()` helpers.
- Workflow data stored on-entity: `workflow_id`, `workflow_stage`, `workflow_status`, `workflow_started_at`, `workflow_completed_at`.
- Workflows are started in the view at the appropriate state transition, not in `save()`.

### 16.5 Kafka — Notifications

- Status transition notifications (e.g., invitations sent on meeting registration, DG notified on case creation) are published to Kafka by CeleryTasks or signal handlers.
- **Not** triggered in `save()` — only in views or Celery tasks.
- Topic pattern: `grc.legal.{event_type}` (e.g., `grc.legal.meeting_invitation_sent`).

---

## 17. Status & State Machine Decisions

### Encoding pattern

All `status` fields use `CharField` with explicit `choices=`:

```python
STATUS_DRAFT = 'draft'
STATUS_REGISTERED = 'registered'
# ...
STATUS_CHOICES = [
    (STATUS_DRAFT, 'Draft'),
    (STATUS_REGISTERED, 'Registered'),
    # ...
]
status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
```

- `max_length=30` is sufficient for all current status strings.
- `db_index=True` — status is always filtered in list queries.
- Status values use snake_case strings (not Django-style `0/1` integers).

### No DB-level state machine enforcement

Status transitions are validated in the **serializer or view**, not via `CheckConstraint`. This keeps state transition logic visible and testable in application code.

```python
# In the view or service layer
VALID_TRANSITIONS = {
    'draft': ['registered'],
    'registered': ['invitations_sent', 'cancelled'],
    # ...
}
if new_status not in VALID_TRANSITIONS.get(meeting.status, []):
    raise ValidationError({'status': 'Invalid transition.'})
```

### Status-to-`is_active` relationship

`is_active` is **not** derived from `status`. They are independent:
- `is_active = False` = soft-deleted record (admin action).
- `status = 'closed'` = terminal workflow state (business action).
- A closed meeting (`status='closed'`) still has `is_active=True` and appears in history queries.

---

## 18. Soft-Delete Strategy

### Rule

All entities with `StatusMixin` use `is_active=False` as the soft-delete mechanism. No `deleted_at` timestamp is used.

### How soft-delete is applied

```python
# Soft-delete in the view — never model.delete()
instance.is_active = False
instance.modified_by = request.user_id
instance.save(update_fields=['is_active', 'modified_by', 'updated_at'])
```

### Default queryset filtering

All Legal list views filter `is_active=True` by default:

```python
queryset = CaseDefendant.objects.filter(is_active=True).order_by('-created_at')
```

### Partial constraints and soft-delete

Partial `UniqueConstraint(condition=Q(is_active=True))` means soft-deleted records do not count toward uniqueness. This allows re-creating a record after soft-deletion.

---

## 19. Choices vs FK — Decision Rule

| Scenario | Use | Reason |
|---|---|---|
| Small, fixed, code-level enum (e.g., FCC Sued vs Suing, RSVP status) | `CharField(choices=)` | Stable values; no admin configuration needed |
| Admin-configurable labels that may grow over time (e.g., urgency levels, meeting modes) | FK to a lookup table | Admin can add/deactivate values without a code change |
| Values that carry extra fields (e.g., `MeetingType.quorum_percentage`) | FK to a lookup table | Cannot store extra data on a `choices` string |

### Current Choices-based fields in Legal module

| Entity | Field | Type | Values |
|---|---|---|---|
| `MeetingParticipant` | `invitation_status` | CharField/choices | `pending`, `accepted`, `declined` |
| `MeetingParticipant` | `role` | CharField/choices | `member`, `invitee` |
| `Member` | `member_type` | CharField/choices | `committee_member`, `management_member` |
| `Member` | `position` | CharField/choices | `member`, `secretary`, `chairman` |
| `CasePlaintiff` | `registration_type` | CharField/choices | `simplified`, `full` |
| `JudgmentDefendant` | `dg_decision` | CharField/choices | `accept`, `appeal` |
| `JudgmentPlaintiff` | `dg_decision` | CharField/choices | `accept`, `appeal` |
| `FinancialDefendant` | `payment.status` (in JSONField) | string | `requested`, `approved`, `processed` |
| `FilingDefendant` | `filing_type` | CharField/choices | `statement_of_defence`, `affidavit`, `notice_of_appeal`, … |
| `FilingPlaintiff` | `filing_type` | CharField/choices | `plaint`, `petition`, `statement_of_claim`, `notice_of_appeal`, … |
| `ResponseDefendant` | `response_type` | CharField/choices | `preliminary_objections`, `counter_claim`, … |
| `ResponsePlaintiff` | `response_type` | CharField/choices | `preliminary_objections`, `initial_response`, … |
| `JudgmentDefendant` | `outcome` | CharField/choices | `won`, `lost` |
| `JudgmentPlaintiff` | `outcome` | CharField/choices | `won`, `lost` |

---

## 20. Other SRS-Derived Decisions

### 20.1 MeetingDirective has two FK fields to Meeting

`MeetingDirective` has `meeting` (the issuing meeting, mandatory) and `finally_closed_in_meeting` (the closure meeting, optional). They reference different meetings:

```python
meeting = ForeignKey('Meeting', on_delete=CASCADE, related_name='directives')
finally_closed_in_meeting = ForeignKey(
    'Meeting', on_delete=SET_NULL,
    null=True, blank=True,
    related_name='finally_closed_directives'
)
```

`related_name` on both FKs is mandatory to avoid accessor clash.

### 20.2 MeetingDirective — dual fully_closed guard

Both `fully_closed = BooleanField(default=False)` **and** `status = 'fully_closed'` are stored, serving different purposes:
- `fully_closed` index: fast filter for Matters Arising query `filter(fully_closed=False)`
- `status` string: drives the display state machine

```python
# Matters Arising query
MeetingDirective.objects.filter(
    meeting__governing_body=body,
    fully_closed=False,
    is_active=True,
).exclude(status='fully_closed')
```

### 20.3 Invitations sent automatically (not manually) — E3.4

When `Meeting.status` transitions `draft → registered`, the view publishes a Kafka event that triggers a Celery task to send invitations to all active members. The invitation send is **not** a separate API call — it is a side effect of the status transition.

```python
# In Meeting status update view — on 'registered' transition
meeting.status = 'registered'
meeting.save(update_fields=['status', 'modified_by', 'updated_at'])
# Trigger invitation task
send_meeting_invitations.delay(str(meeting.id))
```

### 20.4 Resolution visibility — E7.2

`Resolution` records are filtered in the view to participants of the meeting:

```python
# Permission check in Resolution list view
allowed_user_ids = meeting.participants.filter(
    is_active=True
).values_list('user_id', flat=True)
if request.user_id not in [str(uid) for uid in allowed_user_ids]:
    return forbidden_response()
```

No visibility flag is stored on the model itself — visibility is purely claim-based in the view.

### 20.5 PublicDecision — future CRM integration

`PublicDecision` carries a `published_date` (DateTimeField, nullable) that will be used for CRM sync. For now: `status = 'published'` and `published_date` is set when Secretariat publishes. The external CRM integration is **not** implemented — the field is a forward-compatibility placeholder.

### 20.6 FinancialDefendant vs FinancialPlaintiff asymmetry

`FinancialPlaintiff` has one extra card not present in `FinancialDefendant` (E13.4): `recovered_amount` (DecimalField, default=0). The `Record Recovery` button on the Plaintiff side records this field. Both models share the same `payments` and `recoveries` JSONField sub-record pattern.

### 20.7 Digital signature — filing approvals (E10.3)

Digital signature data is stored as part of the approval chain, not a separate model. `FilingDefendant.approval_chain` and `FilingPlaintiff.approval_chain` are `JSONField(default=list)` entries, each approval record containing:

```json
{
  "approver_id": "uuid",
  "approver_role": "legal_manager",
  "approved_at": "2025-04-01T10:00:00Z",
  "signature_hash": "sha256:...",
  "decision": "approved"
}
```

The `signature_hash` is produced by the Digital Signature Engine (internal service). The field is write-appended on each approval stage.

### 20.8 Case closure — read-only after DG approval (C12.2)

After DG approves case closure, the case `status` transitions to `closed`. The view enforces read-only after this:

```python
if instance.status == 'closed':
    return validation_error_response({'detail': 'Case is closed and cannot be modified.'})
```

No DB-level `read_only` flag is stored. Enforcement is view-layer only.

### 20.9 Agenda item ordering

`MeetingAgenda` has an `order` IntegerField (default=0) allowing the Secretary to control agenda item sequence. Uniqueness of `order` within a meeting is not DB-enforced — reordering is handled by the frontend with a bulk-update API endpoint.

### 20.10 Task reminder scheduling (E14.1)

`TaskLitigation` reminders at 7, 2, and 1 day before `due_date` are dispatched by a Celery periodic task (daily cron). The task queries:

```python
from django.utils import timezone
from datetime import timedelta

for days in [7, 2, 1]:
    target_date = timezone.now().date() + timedelta(days=days)
    overdue_tasks = TaskLitigation.objects.filter(
        due_date=target_date,
        status__in=['open', 'in_progress'],
        is_active=True,
    )
    for task in overdue_tasks:
        send_task_reminder.delay(str(task.id), days_remaining=days)
```

No `reminder_sent_*` Boolean fields are stored on `TaskLitigation` — reminders fire on the exact day regardless of prior sends.

---

*End of Part 3 — DB Tables & Design Decisions*
*Next: Part 4 — Litigation Entity Full Model Definitions (CaseDefendant, CasePlaintiff and all child entities, field-level detail)*
