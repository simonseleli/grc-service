# Legal Module — Data Models, Part 2
**Service:** `grc-service`
**Module:** Legal
**Phase:** 5B-2 — Entity Relationships
**Covers:** All Legal entities · FK/1:1/1:M/M:M relationships · Optionality · DB constraints

> **Note:** This document covers all relationships across all Legal entities, including the
> litigation entities not modelled in Part 1. Litigation entity field definitions appear in §4.

---

## Table of Contents

1. [Relationship Notation](#1-relationship-notation)
2. [Domain 1 — Governance Structure Relationships](#2-domain-1--governance-structure-relationships)
3. [Domain 2 — Determinations Relationships](#3-domain-2--determinations-relationships)
4. [Domain 3 — Meeting Governance Relationships](#4-domain-3--meeting-governance-relationships)
5. [Domain 4 — Litigation (FCC Sued) Entities & Relationships](#5-domain-4--litigation-fcc-sued-entities--relationships)
6. [Domain 5 — Litigation (FCC Suing) Entities & Relationships](#6-domain-5--litigation-fcc-suing-entities--relationships)
7. [Domain 6 — Public Register Relationships](#7-domain-6--public-register-relationships)
8. [Cross-Domain Relationships](#8-cross-domain-relationships)
9. [Relationship Optionality Reference](#9-relationship-optionality-reference)
10. [DB Constraint Catalogue](#10-db-constraint-catalogue)
11. [Full Entity Relationship Map](#11-full-entity-relationship-map)

---

## 1. Relationship Notation

| Symbol | Meaning |
|---|---|
| `──<` | One-to-many (FK on the many side) |
| `──1──` | One-to-one (OneToOneField) |
| `──0..1──` | Optional one-to-one (nullable FK or nullable OneToOneField) |
| `──>` | Many-to-one (FK pointing to parent) |
| `M:M` | Many-to-many (through table) |
| `UUID ref` | No FK in DB; only a UUID field pointing to an external service |
| `[MANDATORY]` | FK is non-nullable; relationship is required |
| `[OPTIONAL]` | FK is nullable; relationship may be absent |

---

## 2. Domain 1 — Governance Structure Relationships

### 2.1 CommitteeType → GoverningBody

```
CommitteeType ──< GoverningBody   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `GoverningBody.committee_type` |
| Django field | `ForeignKey(CommitteeType, on_delete=PROTECT)` |
| Nullable | No — every governing body must have a type |
| on_delete | `PROTECT` — cannot delete a committee type that has bodies |
| Reverse name | `committee_type.governing_bodies.all()` |

**Business rule:** `CommitteeType.is_active = False` hides the type from creation dropdowns but does not cascade to existing `GoverningBody` records.

---

### 2.2 GoverningBody → Member

```
GoverningBody ──< Member   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `Member.governing_body` |
| Django field | `ForeignKey(GoverningBody, on_delete=CASCADE)` |
| Nullable | No — every member belongs to exactly one body |
| on_delete | `CASCADE` — deleting a body removes all its member snapshots |
| Reverse name | `governing_body.members.all()` |

**Partial UniqueConstraint:** `(governing_body, user_id)` where `is_active=True` — a user cannot be an active member of the same body twice.

---

### 2.3 GoverningBody → Meeting

```
GoverningBody ──< Meeting   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `Meeting.governing_body` |
| Django field | `ForeignKey(GoverningBody, on_delete=PROTECT)` |
| Nullable | No — every meeting belongs to a body |
| on_delete | `PROTECT` — cannot delete a body that has meetings |
| Reverse name | `governing_body.meetings.all()` |

---

### 2.4 GoverningBody — Secretary (UUID reference, no FK)

```
GoverningBody.secretary_user_ids   [M:M via JSONField, UUID ref to IAM]
```

- Stored as `JSONField(default=list)` — a list of UUID strings.
- No FK or through table; IAM owns the canonical user records.
- Multiple secretaries per body (E1.3, E1.5).
- Queried in views: `governing_body.is_secretary(request.user_id)`.

---

### 2.5 GoverningBody → SubmissionForDetermination

```
GoverningBody ──< SubmissionForDetermination   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `SubmissionForDetermination.target_body` |
| Django field | `ForeignKey(GoverningBody, on_delete=PROTECT)` |
| Nullable | No — submission must target a specific body |
| Reverse name | `target_body.submissions.all()` |

---

## 3. Domain 2 — Determinations Relationships

### 3.1 SubmissionForDetermination → Meeting (agenda attachment)

```
SubmissionForDetermination ──0..1── Meeting   [optional 1:M, OPTIONAL]
```

| Property | Value |
|---|---|
| FK field | `SubmissionForDetermination.meeting` |
| Django field | `ForeignKey(Meeting, on_delete=SET_NULL, null=True, blank=True)` |
| Nullable | Yes — null until Secretary attaches it to an agenda |
| on_delete | `SET_NULL` — if meeting is deactivated, submission is unlinked but not lost |
| Reverse name | `meeting.linked_submissions.all()` |

**State coupling:** Setting this FK in the view simultaneously transitions `SubmissionForDetermination.status → under_review` and creates a `MeetingAgenda` record. Clearing it is not permitted once `status = under_review`.

---

### 3.2 SubmissionForDetermination → MeetingAgenda

```
SubmissionForDetermination ──0..1── MeetingAgenda   [optional 1:1 per active meeting, OPTIONAL]
```

| Property | Value |
|---|---|
| FK field | `MeetingAgenda.submission` |
| Django field | `ForeignKey(SubmissionForDetermination, on_delete=PROTECT)` |
| Nullable | No — an agenda item always references a submission |
| Unique constraint | `(meeting, submission)` where `is_active=True` — one submission per active agenda |
| Reverse name | `submission.agenda_items.all()` |

---

## 4. Domain 3 — Meeting Governance Relationships

### 4.1 Meeting → MeetingAgenda

```
Meeting ──< MeetingAgenda   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `MeetingAgenda.meeting` |
| Django field | `ForeignKey(Meeting, on_delete=CASCADE)` |
| Nullable | No |
| on_delete | `CASCADE` — deleting a meeting removes all agenda items |
| Reverse name | `meeting.agenda_items.all()` |

---

### 4.2 Meeting ──1── Minutes

```
Meeting ──1── Minutes   [1:1, MANDATORY on Minutes side]
```

| Property | Value |
|---|---|
| FK field | `Minutes.meeting` |
| Django field | `OneToOneField(Meeting, on_delete=CASCADE)` |
| Nullable | No — minutes always belong to exactly one meeting |
| Direction | Minutes → Meeting (unique FK on Minutes side) |
| on_delete | `CASCADE` — if meeting deleted, its minutes are also deleted |
| Reverse name | `meeting.minutes` (single object, not queryset) |

**Creation rule (E6.1):** Minutes can only be created when `meeting.status in ('ongoing', 'closed')`. Enforced in the view, not at the DB level.

---

### 4.3 Meeting → MeetingParticipant

```
Meeting ──< MeetingParticipant   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `MeetingParticipant.meeting` |
| Django field | `ForeignKey(Meeting, on_delete=CASCADE)` |
| Nullable | No |
| Unique constraint | `(meeting, user_id)` where `is_active=True` |
| Reverse name | `meeting.participants.all()` |

---

### 4.4 Meeting → MeetingDirective

```
Meeting ──< MeetingDirective   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `MeetingDirective.meeting` |
| Django field | `ForeignKey(Meeting, on_delete=CASCADE)` |
| Nullable | No — every directive is issued within a specific meeting |
| Reverse name | `meeting.directives.all()` |

**Second FK (final closure):**

```
MeetingDirective ──0..1── Meeting (finally_closed_in_meeting)   [OPTIONAL]
```

| Property | Value |
|---|---|
| FK field | `MeetingDirective.finally_closed_in_meeting` |
| Django field | `ForeignKey(Meeting, on_delete=SET_NULL, null=True, blank=True, related_name='finally_closed_directives')` |
| Nullable | Yes — null until Secretary performs final closure |
| Direction | Points to a **different** meeting than the issuing meeting |

---

### 4.5 MeetingAgenda → MeetingDirective

```
MeetingAgenda ──< MeetingDirective   [1:M, OPTIONAL on directive side]
```

| Property | Value |
|---|---|
| FK field | `MeetingDirective.agenda_item` |
| Django field | `ForeignKey(MeetingAgenda, on_delete=SET_NULL, null=True, blank=True)` |
| Nullable | Yes — null for Matters Arising directives (no agenda item) |
| on_delete | `SET_NULL` — if agenda item removed, directive survives as stand-alone |
| Reverse name | `agenda_item.directives.all()` |

---

### 4.6 MeetingAgenda → ConflictDeclaration

```
MeetingAgenda ──< ConflictDeclaration   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `ConflictDeclaration.agenda_item` |
| Django field | `ForeignKey(MeetingAgenda, on_delete=CASCADE)` |
| Nullable | No |
| Unique constraint | `(agenda_item, member_user_id)` where `is_active=True` |
| Reverse name | `agenda_item.conflict_declarations.all()` |

---

### 4.7 MeetingAgenda ──1── Resolution

```
MeetingAgenda ──1── Resolution   [1:1, MANDATORY on Resolution side]
```

| Property | Value |
|---|---|
| FK field | `Resolution.agenda_item` |
| Django field | `OneToOneField(MeetingAgenda, on_delete=CASCADE)` |
| Nullable | No — every resolution derives from exactly one agenda item |
| Direction | Resolution → MeetingAgenda |
| on_delete | `CASCADE` — cascade to resolution if agenda item is deleted |
| Reverse name | `agenda_item.resolution` (single object) |

**Creation rule (E7.1):** System-created only when `MeetingAgenda.outcome` is set. Not manually created via API.

---

### 4.8 Meeting → Resolution

```
Meeting ──< Resolution   [1:M, MANDATORY]
```

| Property | Value |
|---|---|
| FK field | `Resolution.meeting` |
| Django field | `ForeignKey(Meeting, on_delete=CASCADE)` |
| Nullable | No |
| Reverse name | `meeting.resolutions.all()` |

---

## 5. Domain 4 — Litigation (FCC Sued) Entities & Relationships

### 5.1 CaseDefendant — entity summary

`CaseDefendant(TimestampedModel, StatusMixin, WorkflowMixin)` — `db_table = 'legal_case_defendant'`

Root entity of the FCC Sued domain. All litigation child entities are children of this entity. Auto-generated reference number `FCC/SUED/YYYY/NNN`.

**Key FK fields on CaseDefendant itself:**
```python
court_level         = ForeignKey(CourtLevel, on_delete=PROTECT)
urgency_level       = ForeignKey(LitigationUrgencyLevel, on_delete=PROTECT)
risk_level          = ForeignKey(LitigationRiskLevel, on_delete=PROTECT, null=True)
assigned_legal_manager_id = UUIDField(null=True)        # IAM ref
initiation_documents = JSONField(default=list)           # DRS document UUID list
```

---

### 5.2 CaseDefendant — child relationships

```
CaseDefendant ──< LitigationDirective     [1:M, OPTIONAL — created on DG review]
CaseDefendant ──< FilingDefendant         [1:M, OPTIONAL]
CaseDefendant ──< ResponseDefendant       [1:M, OPTIONAL]
CaseDefendant ──< Hearing                 [1:M, OPTIONAL]
CaseDefendant ──0..1── SettlementDefendant [1:1, OPTIONAL]
CaseDefendant ──0..1── JudgmentDefendant   [1:1, OPTIONAL]
CaseDefendant ──1── FinancialDefendant    [1:1, MANDATORY — auto-created on registration]
CaseDefendant ──< TaskLitigation          [1:M, OPTIONAL]
```

| Relationship | FK field | on_delete | Nullable |
|---|---|---|---|
| `CaseDefendant → LitigationDirective` | `LitigationDirective.case_defendant` | `CASCADE` | No |
| `CaseDefendant → FilingDefendant` | `FilingDefendant.case_defendant` | `CASCADE` | No |
| `CaseDefendant → ResponseDefendant` | `ResponseDefendant.case_defendant` | `CASCADE` | No |
| `CaseDefendant → Hearing` | `Hearing.case_defendant` | `CASCADE` | No (for defendant hearings) |
| `CaseDefendant → SettlementDefendant` | `SettlementDefendant.case_defendant` | `CASCADE` | No |
| `CaseDefendant → JudgmentDefendant` | `JudgmentDefendant.case_defendant` | `CASCADE` | No |
| `CaseDefendant → FinancialDefendant` | `FinancialDefendant.case_defendant` | `CASCADE` | No |
| `CaseDefendant → TaskLitigation` | `TaskLitigation.case_defendant` | `CASCADE` | No (nullable for plaintiff side) |

**UniqueConstraints on child entities:**
- `SettlementDefendant`: `(case_defendant,)` where `is_active=True` — one active settlement per case
- `JudgmentDefendant`: `(case_defendant,)` where `is_active=True` — one active judgment per case
- `FinancialDefendant`: `OneToOneField` to `CaseDefendant` — strictly one financial record per case

---

### 5.3 Hearing → HearingReport

```
Hearing ──< HearingReport   [1:M, OPTIONAL]
```

| Property | Value |
|---|---|
| FK field | `HearingReport.hearing` |
| Django field | `ForeignKey(Hearing, on_delete=CASCADE)` |
| Nullable | No |
| Reverse name | `hearing.reports.all()` |

**Propagation rule (SRS B4):** The most recent `HearingReport.next_hearing_date` propagates up to update `CaseDefendant.next_hearing_date`. Done in the view after `HearingReport` save:
```python
case.next_hearing_date = hearing_report.next_hearing_date
case.save(update_fields=['next_hearing_date', 'updated_at'])
```

---

### 5.4 JudgmentDefendant → FilingDefendant (Appeal auto-create)

```
JudgmentDefendant ──0..1── FilingDefendant   [optional 1:1, OPTIONAL]
```

| Property | Value |
|---|---|
| FK field | `JudgmentDefendant.appeal_filing` |
| Django field | `ForeignKey(FilingDefendant, on_delete=SET_NULL, null=True, blank=True, related_name='appeal_judgment')` |
| Nullable | Yes — only set if DG decides to appeal (E12.3) |
| Direction | JudgmentDefendant → FilingDefendant (the appeal filing) |

**Auto-create rule (C10, E12.3):** When DG sets `JudgmentDefendant.dg_decision = 'appeal'`, the view inside `transaction.atomic()`:
1. Creates `FilingDefendant(type='notice_of_appeal', status='draft', case_defendant=...)`
2. Sets `JudgmentDefendant.appeal_filing = <new filing>`
3. Creates `TaskLitigation(title='File Notice of Appeal', due_date=appeal_due_date, ...)`
4. Sets `JudgmentDefendant.appeal_task = <new task>`

---

### 5.5 JudgmentDefendant → TaskLitigation (Appeal deadline auto-create)

```
JudgmentDefendant ──0..1── TaskLitigation   [optional 1:1, OPTIONAL]
```

| Property | Value |
|---|---|
| FK field | `JudgmentDefendant.appeal_task` |
| Django field | `ForeignKey(TaskLitigation, on_delete=SET_NULL, null=True, blank=True, related_name='appeal_judgment_defendant')` |
| Nullable | Yes — only set on appeal decision |

---

### 5.6 TaskLitigation — case discriminator pattern

`TaskLitigation` is shared between FCC Sued and FCC Suing. It uses two nullable FKs with a DB-level check to ensure it belongs to exactly one case:

```python
class TaskLitigation(TimestampedModel, StatusMixin):
    case_defendant = ForeignKey(CaseDefendant, on_delete=CASCADE, null=True, blank=True, related_name='tasks')
    case_plaintiff = ForeignKey(CasePlaintiff, on_delete=CASCADE, null=True, blank=True, related_name='tasks')
```

**DB constraint (enforced via `CheckConstraint`):**
```python
class Meta:
    constraints = [
        models.CheckConstraint(
            check=(
                models.Q(case_defendant__isnull=False, case_plaintiff__isnull=True) |
                models.Q(case_defendant__isnull=True, case_plaintiff__isnull=False)
            ),
            name='legal_task_litigation_exactly_one_case',
        )
    ]
```

This pattern ensures a task always belongs to exactly one case type — never both, never neither.

---

### 5.7 Hearing — case discriminator pattern

`Hearing` is also shared between FCC Sued and FCC Suing, using the same discriminator pattern:

```python
class Hearing(TimestampedModel, StatusMixin):
    case_defendant = ForeignKey(CaseDefendant, on_delete=CASCADE, null=True, blank=True, related_name='hearings')
    case_plaintiff = ForeignKey(CasePlaintiff, on_delete=CASCADE, null=True, blank=True, related_name='hearings')
```

**DB constraint:**
```python
models.CheckConstraint(
    check=(
        models.Q(case_defendant__isnull=False, case_plaintiff__isnull=True) |
        models.Q(case_defendant__isnull=True, case_plaintiff__isnull=False)
    ),
    name='legal_hearing_exactly_one_case',
)
```

---

### 5.8 LitigationDirective — case discriminator pattern

`LitigationDirective` is also shared (DG-issued on both case types):

```python
class LitigationDirective(TimestampedModel, StatusMixin):
    case_defendant = ForeignKey(CaseDefendant, on_delete=CASCADE, null=True, blank=True, related_name='litigation_directives')
    case_plaintiff = ForeignKey(CasePlaintiff, on_delete=CASCADE, null=True, blank=True, related_name='litigation_directives')
    issued_by_user_id = UUIDField()    # DG's UUID from IAM
```

**DB constraint:** same `CheckConstraint` pattern ensuring exactly one parent case.

---

## 6. Domain 5 — Litigation (FCC Suing) Entities & Relationships

### 6.1 CasePlaintiff — entity summary

`CasePlaintiff(TimestampedModel, StatusMixin, WorkflowMixin)` — `db_table = 'legal_case_plaintiff'`

Root entity of the FCC Suing domain. Mirrors `CaseDefendant` structure. Two registration paths produce the same entity type (C13). Auto-generated reference `FCC/SUING/YYYY/NNN`.

**Discriminator field:**
```python
registration_type = CharField(
    max_length=20,
    choices=[('simplified', 'Breach Report Intake'), ('full', 'Full Breach Report')],
    default='full',
    help_text="Whether registered via simplified intake (Department User) or full form"
)
```

---

### 6.2 CasePlaintiff — child relationships

```
CasePlaintiff ──< LitigationDirective    [1:M, OPTIONAL — via shared discriminator]
CasePlaintiff ──< FilingPlaintiff        [1:M, OPTIONAL]
CasePlaintiff ──< ResponsePlaintiff      [1:M, OPTIONAL]
CasePlaintiff ──< Hearing                [1:M, OPTIONAL — via shared discriminator]
CasePlaintiff ──0..1── SettlementPlaintiff [1:1, OPTIONAL]
CasePlaintiff ──0..1── JudgmentPlaintiff   [1:1, OPTIONAL]
CasePlaintiff ──1── FinancialPlaintiff   [1:1, MANDATORY — auto-created on registration]
CasePlaintiff ──< TaskLitigation         [1:M, OPTIONAL — via shared discriminator]
```

All FK patterns are identical to `CaseDefendant` child relationships. Child entities for Plaintiff side use `case_plaintiff` FK (see table below):

| Entity | FK field on child | Django field | on_delete |
|---|---|---|---|
| `FilingPlaintiff` | `case_plaintiff` | `ForeignKey(CasePlaintiff, on_delete=CASCADE)` | CASCADE |
| `ResponsePlaintiff` | `case_plaintiff` | `ForeignKey(CasePlaintiff, on_delete=CASCADE)` | CASCADE |
| `SettlementPlaintiff` | `case_plaintiff` | `ForeignKey(CasePlaintiff, on_delete=CASCADE)` | CASCADE |
| `JudgmentPlaintiff` | `case_plaintiff` | `ForeignKey(CasePlaintiff, on_delete=CASCADE)` | CASCADE |
| `FinancialPlaintiff` | `case_plaintiff` | `OneToOneField(CasePlaintiff, on_delete=CASCADE)` | CASCADE |

---

### 6.3 JudgmentPlaintiff → FilingPlaintiff + TaskLitigation (Appeal auto-create)

Identical pattern to `JudgmentDefendant`:

```
JudgmentPlaintiff ──0..1── FilingPlaintiff   [OPTIONAL — appeal notice of appeal]
JudgmentPlaintiff ──0..1── TaskLitigation    [OPTIONAL — appeal deadline task]
```

```python
class JudgmentPlaintiff(TimestampedModel, StatusMixin, WorkflowMixin):
    appeal_filing = ForeignKey(FilingPlaintiff, on_delete=SET_NULL, null=True, blank=True, related_name='appeal_judgment')
    appeal_task   = ForeignKey(TaskLitigation,  on_delete=SET_NULL, null=True, blank=True, related_name='appeal_judgment_plaintiff')
```

---

## 7. Domain 6 — Public Register Relationships

### 7.1 Meeting → PublicDecision

```
Meeting ──< PublicDecision   [1:M, OPTIONAL]
```

| Property | Value |
|---|---|
| FK field | `PublicDecision.meeting` |
| Django field | `ForeignKey(Meeting, on_delete=PROTECT, null=True, blank=True)` |
| Nullable | Yes — a public decision may reference a meeting, but standalone decisions are also valid |
| on_delete | `PROTECT` — cannot delete a meeting that has published decisions referencing it |
| Reverse name | `meeting.public_decisions.all()` |

---

## 8. Cross-Domain Relationships

### 8.1 External service references (UUID-only, no FK)

All user references across the Legal module use plain `UUIDField` — no FK to a local User model. The following fields are UUID references to IAM / Corporate Service:

| Entity | Field | Referenced Service |
|---|---|---|
| `GoverningBody` | `secretary_user_ids` (JSONField list) | IAM / Corporate Service |
| `Member` | `user_id` | IAM / Corporate Service |
| `Meeting` | `secretary_id` | IAM |
| `MeetingParticipant` | `user_id` | IAM |
| `ConflictDeclaration` | `member_user_id` | IAM |
| `MeetingDirective` | `assigned_user_id` | IAM |
| `MeetingDirective` | `finally_closed_by` | IAM |
| `SubmissionForDetermination` | `submitter_user_id` | IAM / Corporate Service |
| `Minutes` | `approved_by` (JSONField list) | IAM |
| `Resolution` | `responsible_person_id` | IAM |
| `CaseDefendant` | `assigned_legal_officer_ids` (JSONField list) | IAM |
| `CaseDefendant` | `assigned_legal_manager_id` | IAM |
| `CasePlaintiff` | `assigned_legal_officer_ids` (JSONField list) | IAM |
| `CasePlaintiff` | `assigned_legal_manager_id` | IAM |
| `LitigationDirective` | `issued_by_user_id` | IAM (DG) |
| `LegalAuditLog` | `actor_id` | IAM |
| All `TimestampedModel` | `created_by`, `modified_by` | IAM |

### 8.2 External document references (UUID-only, no FK)

All document attachments store Document Records Service UUIDs only:

| Entity | Field | Type | Cardinality |
|---|---|---|---|
| `SubmissionForDetermination` | `supporting_documents` | JSONField (list) | 0..N |
| `MeetingAgenda` | `documents` | JSONField (list) | 0..N |
| `MeetingDirective` | `evidence_document_id` | UUIDField | 0..1 |
| `Minutes` | `attachments` | JSONField (list) | 0..N |
| `Resolution` | `attachments` | JSONField (list) | 0..N |
| `CaseDefendant` | `initiation_documents` | JSONField (list) | 0..N |
| `CasePlaintiff` | `initiation_documents` | JSONField (list) | 0..N |
| `LitigationDirective` | `attachments` | JSONField (list) | 0..N |
| `FilingDefendant` | `document_id` | UUIDField | 1 (mandatory) |
| `FilingPlaintiff` | `document_id` | UUIDField | 1 (mandatory) |
| `ResponseDefendant` | `document_id` | UUIDField | 1 |
| `ResponsePlaintiff` | `document_id` | UUIDField | 1 |
| `HearingReport` | `attachment_id` | UUIDField | 0..1 |
| `SettlementDefendant` | `agreement_document_id` | UUIDField | 1 (mandatory) |
| `SettlementPlaintiff` | `agreement_document_id` | UUIDField | 1 (mandatory) |
| `JudgmentDefendant` | `document_id` | UUIDField | 1 |
| `JudgmentPlaintiff` | `document_id` | UUIDField | 1 |

### 8.3 LegalAuditLog — cross-entity pointer

`LegalAuditLog` references any Legal entity via a generic `(entity_type, entity_id)` pair — not a FK. This avoids creating 22+ separate audit log tables and allows the log to span any entity type without schema changes.

```python
# Querying audit log for a specific entity
LegalAuditLog.objects.filter(
    entity_type='filing_defendant',
    entity_id=filing.id,
).order_by('-created_at')
```

---

## 9. Relationship Optionality Reference

### 9.1 Mandatory relationships (non-nullable FKs)

These FKs can never be null. The referenced parent must exist before the child can be created.

| Child entity | Mandatory FK field | Parent |
|---|---|---|
| `GoverningBody` | `committee_type` | `CommitteeType` |
| `Member` | `governing_body` | `GoverningBody` |
| `Meeting` | `governing_body` | `GoverningBody` |
| `Meeting` | `meeting_mode` | `MeetingMode` |
| `Meeting` | `meeting_type` | `MeetingType` |
| `MeetingAgenda` | `meeting` | `Meeting` |
| `MeetingAgenda` | `submission` | `SubmissionForDetermination` |
| `ConflictDeclaration` | `agenda_item` | `MeetingAgenda` |
| `MeetingParticipant` | `meeting` | `Meeting` |
| `MeetingDirective` | `meeting` | `Meeting` |
| `MeetingDirective` | `directive_priority` | `DirectivePriority` |
| `Minutes` | `meeting` (OneToOneField) | `Meeting` |
| `Resolution` | `meeting` | `Meeting` |
| `Resolution` | `agenda_item` (OneToOneField) | `MeetingAgenda` |
| `SubmissionForDetermination` | `target_body` | `GoverningBody` |
| `CaseDefendant` | `court_level` | `CourtLevel` |
| `CaseDefendant` | `urgency_level` | `LitigationUrgencyLevel` |
| `FilingDefendant` | `case_defendant` | `CaseDefendant` |
| `FilingPlaintiff` | `case_plaintiff` | `CasePlaintiff` |
| `ResponseDefendant` | `case_defendant` | `CaseDefendant` |
| `ResponsePlaintiff` | `case_plaintiff` | `CasePlaintiff` |
| `SettlementDefendant` | `case_defendant` | `CaseDefendant` |
| `SettlementPlaintiff` | `case_plaintiff` | `CasePlaintiff` |
| `JudgmentDefendant` | `case_defendant` | `CaseDefendant` |
| `JudgmentPlaintiff` | `case_plaintiff` | `CasePlaintiff` |
| `FinancialDefendant` | `case_defendant` (OneToOneField) | `CaseDefendant` |
| `FinancialPlaintiff` | `case_plaintiff` (OneToOneField) | `CasePlaintiff` |
| `HearingReport` | `hearing` | `Hearing` |
| `PublicDecision` | — | — (meeting FK is optional) |

### 9.2 Optional relationships (nullable FKs)

| Child entity | Optional FK field | When null |
|---|---|---|
| `SubmissionForDetermination` | `meeting` | Not yet attached to an agenda |
| `MeetingDirective` | `agenda_item` | Directive added to Matters Arising |
| `MeetingDirective` | `directive_category` | Category not assigned |
| `MeetingDirective` | `finally_closed_in_meeting` | Not yet finally closed |
| `MeetingDirective` | `assigned_user_id` | Assigned to org unit only |
| `Resolution` | `responsible_person_id` | No designated responsible party |
| `CaseDefendant` | `risk_level` | Not yet assessed |
| `HearingReport` | `attachment_id` | No report document attached |
| `JudgmentDefendant` | `appeal_filing` | DG chose Accept (no appeal) |
| `JudgmentDefendant` | `appeal_task` | DG chose Accept (no appeal) |
| `JudgmentPlaintiff` | `appeal_filing` | DG chose Accept |
| `JudgmentPlaintiff` | `appeal_task` | DG chose Accept |
| `TaskLitigation` | `case_defendant` | Belongs to a plaintiff case |
| `TaskLitigation` | `case_plaintiff` | Belongs to a defendant case |
| `Hearing` | `case_defendant` | Belongs to a plaintiff case |
| `Hearing` | `case_plaintiff` | Belongs to a defendant case |
| `LitigationDirective` | `case_defendant` | Belongs to plaintiff case |
| `LitigationDirective` | `case_plaintiff` | Belongs to defendant case |
| `PublicDecision` | `meeting` | Standalone decision (no meeting reference) |

---

## 10. DB Constraint Catalogue

All `UniqueConstraint` and `CheckConstraint` definitions for the Legal module, grouped by entity.

### UniqueConstraints (partial — scoped to `is_active=True`)

| Entity | Fields | Constraint name |
|---|---|---|
| `Member` | `(governing_body, user_id)` | `legal_member_active_body_user_uniq` |
| `Meeting` | `(governing_body, meeting_number)` | `legal_meeting_active_body_number_uniq` |
| `MeetingAgenda` | `(meeting, submission)` | `legal_meeting_agenda_active_meeting_submission_uniq` |
| `MeetingParticipant` | `(meeting, user_id)` | `legal_meeting_participant_active_meeting_user_uniq` |
| `ConflictDeclaration` | `(agenda_item, member_user_id)` | `legal_conflict_declaration_active_item_member_uniq` |
| `SettlementDefendant` | `(case_defendant,)` | `legal_settlement_defendant_active_case_uniq` |
| `SettlementPlaintiff` | `(case_plaintiff,)` | `legal_settlement_plaintiff_active_case_uniq` |
| `JudgmentDefendant` | `(case_defendant,)` | `legal_judgment_defendant_active_case_uniq` |
| `JudgmentPlaintiff` | `(case_plaintiff,)` | `legal_judgment_plaintiff_active_case_uniq` |
| `CaseDefendant` | `(reference_number,)` | `legal_case_defendant_active_ref_uniq` |
| `CasePlaintiff` | `(reference_number,)` | `legal_case_plaintiff_active_ref_uniq` |

### OneToOneField constraints (DB-level unique)

| Entity | OneToOneField target | Meaning |
|---|---|---|
| `Minutes` | `Meeting` | One meeting → one minutes record |
| `Resolution` | `MeetingAgenda` | One agenda item → one resolution |
| `FinancialDefendant` | `CaseDefendant` | One case → one financial record |
| `FinancialPlaintiff` | `CasePlaintiff` | One case → one financial record |

### CheckConstraints (shared entity discriminator)

| Entity | Constraint name | Rule |
|---|---|---|
| `Hearing` | `legal_hearing_exactly_one_case` | Exactly one of `case_defendant`/`case_plaintiff` is non-null |
| `HearingReport` | — | Via cascade from `Hearing` |
| `LitigationDirective` | `legal_litigation_directive_exactly_one_case` | Exactly one of `case_defendant`/`case_plaintiff` is non-null |
| `TaskLitigation` | `legal_task_litigation_exactly_one_case` | Exactly one of `case_defendant`/`case_plaintiff` is non-null |

### on_delete behaviour summary

| Behaviour | When used |
|---|---|
| `CASCADE` | Child entities that cannot logically exist without their parent (e.g., agenda items without a meeting, hearings without a case) |
| `PROTECT` | Parents that must not be deleted while children exist (e.g., governing body with meetings, case with filings) |
| `SET_NULL` | Optional references that become irrelevant if parent is soft-deleted (e.g., finally_closed_in_meeting, appeal_filing) |

---

## 11. Full Entity Relationship Map

```
[IAM Service]                               [Corporate Service]
    │ (UUID refs)                               │ (UUID refs + Kafka sync)
    │                                           │
    ▼                                           ▼
CommitteeType ──< GoverningBody ──────────────> Member (snapshot)
                     │                          │
                     ├──< Meeting               │ (quorum count from members)
                     │      │                   │
                     │      ├──< MeetingAgenda ──< ConflictDeclaration
                     │      │         │         │
                     │      │         ├──1── Resolution
                     │      │         └──< MeetingDirective (with agenda_item)
                     │      │
                     │      ├──< MeetingDirective (Matters Arising, no agenda_item)
                     │      ├──< MeetingParticipant
                     │      ├──1── Minutes ──[WO: grc.legal_minutes_approval]
                     │      └──< PublicDecision
                     │
                     └──< SubmissionForDetermination ──> MeetingAgenda (on attachment)


CaseDefendant ──< LitigationDirective
              ──< FilingDefendant ──[WO: grc.legal_filing_approval]
              ──< ResponseDefendant
              ──< Hearing ──< HearingReport
              ──1── SettlementDefendant ──[WO: grc.legal_settlement_approval]
              ──1── JudgmentDefendant ──[WO: grc.legal_judgment_decision]
              │         └──0..1──> FilingDefendant (Notice of Appeal)
              │         └──0..1──> TaskLitigation (appeal deadline)
              ──1── FinancialDefendant
              ──< TaskLitigation
              └──[WO: grc.legal_case_closure]


CasePlaintiff ──< LitigationDirective        (same structure)
              ──< FilingPlaintiff ──[WO: grc.legal_filing_approval]
              ──< ResponsePlaintiff
              ──< Hearing ──< HearingReport
              ──1── SettlementPlaintiff ──[WO: grc.legal_settlement_approval]
              ──1── JudgmentPlaintiff ──[WO: grc.legal_judgment_decision]
              │         └──0..1──> FilingPlaintiff (Notice of Appeal)
              │         └──0..1──> TaskLitigation (appeal deadline)
              ──1── FinancialPlaintiff
              ──< TaskLitigation
              └──[WO: grc.legal_case_closure]


LegalAuditLog ─────────> any entity via (entity_type, entity_id) generic ref

[WO] = Work Orchestration Service workflow plan
```

---

*End of Part 2 — Entity Relationships*
*Next: Part 3 — Litigation Entity Full Model Definitions (CaseDefendant, CasePlaintiff and all children)*
