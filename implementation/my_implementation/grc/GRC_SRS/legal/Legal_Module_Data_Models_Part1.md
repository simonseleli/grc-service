# Legal Module — Data Models, Part 1
**Service:** `grc-service`
**Module:** Legal
**Phase:** 5B-1 — Core Entities
**File target:** `apps/core/models/legal_entities.py`
**Covers:** Governance Structure · Determinations · Meeting Governance · Cross-cutting Audit Log

---

## Table of Contents

1. [File Header & Imports](#1-file-header--imports)
2. [Domain 1 — Governance Structure](#2-domain-1--governance-structure)
   - CommitteeType
   - GoverningBody
   - Member
3. [Domain 2 — Determinations & Approvals](#3-domain-2--determinations--approvals)
   - SubmissionForDetermination
4. [Domain 3 — Meeting Governance](#4-domain-3--meeting-governance)
   - Meeting
   - MeetingAgenda
   - ConflictDeclaration
   - MeetingParticipant
   - MeetingDirective
   - Minutes
   - Resolution
5. [Cross-cutting — LegalAuditLog](#5-cross-cutting--legalauditlog)
6. [Entity Quick Reference](#6-entity-quick-reference)

---

## 1. File Header & Imports

```python
"""
Legal module entity models for grc-service.
Part 1: Governance Structure, Determinations, Meeting Governance.

All models follow grc-service conventions:
  - UUID primary keys (from BaseModel)
  - TimestampedModel for all user-created business entities
  - StatusMixin for all soft-deletable entities (is_active flag)
  - WorkflowMixin only for entities that enter a Work Orchestration workflow plan
  - db_table prefix: legal_
  - User references are UUID-only fields (no ForeignKey to an auth.User model)
  - Document references are UUID-only fields (no file storage in grc-service)
"""

import uuid
from django.db import models
from django.utils import timezone

from .base import BaseModel, TimestampedModel, StatusMixin, WorkflowMixin
from .lookups import (
    MeetingMode,
    MeetingType,
    DirectivePriority,
    DirectiveCategory,
)
from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
```

---

## 2. Domain 1 — Governance Structure

### 2.1 CommitteeType

**Purpose:** Master classification of governing body types (e.g., Commission, Audit Committee, Management Committee). Admin-managed; acts as a configurable category for `GoverningBody`.

**Composition:** `BaseModel, StatusMixin`
- `BaseModel` — UUID PK, timestamps
- `StatusMixin` — `is_active` soft-delete flag
- No `TimestampedModel` — system/admin data, not user-submitted
- No `WorkflowMixin` — no WO workflow

**Relationships:**
- `CommitteeType ──< GoverningBody` (one type → many bodies)

```python
class CommitteeType(BaseModel, StatusMixin):
    """
    Classification of a governing body type.
    Master data; admin-managed. Not user-created.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Short unique code (e.g., 'AUDIT', 'COMMISSION', 'MANAGEMENT')"
    )
    name = models.CharField(
        max_length=150,
        help_text="Display name of the committee type"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional detailed description of this committee type"
    )

    class Meta:
        db_table = 'legal_committee_type'
        ordering = ['name']
        verbose_name = 'Committee Type'
        verbose_name_plural = 'Committee Types'

    def __str__(self):
        return f"{self.code} — {self.name}"
```

**Key field notes:**
- `code` is unique across the table (not partial) — committee type codes never change.
- `is_active = False` hides the type from governing body creation dropdowns but does not cascade to existing governing bodies.

---

### 2.2 GoverningBody

**Purpose:** A formal committee or governing body within FCC. The organisational context for meetings, submissions, and members. Every meeting and submission belongs to exactly one governing body.

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — UUID PK, timestamps, `created_by`, `modified_by`
- `StatusMixin` — `is_active` soft-delete
- No `WorkflowMixin` — no WO workflow

**Relationships:**
- `GoverningBody.committee_type → CommitteeType` (FK)
- `GoverningBody ──< Member` (one body → many members)
- `GoverningBody ──< Meeting` (one body → many meetings)
- `GoverningBody ──< SubmissionForDetermination` (one body → many targeted submissions)
- Secretary assignments stored as a JSONField of UUID array (multiple secretaries, from IAM)

```python
class GoverningBody(TimestampedModel, StatusMixin):
    """
    A formal committee or governing body within FCC.
    All meetings and submissions target a specific GoverningBody.
    """
    committee_type = models.ForeignKey(
        CommitteeType,
        on_delete=models.PROTECT,
        related_name='governing_bodies',
        help_text="Classification of this governing body"
    )
    name = models.CharField(
        max_length=255,
        help_text="Official name of the governing body"
    )
    composite_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Full composite title used in formal documents"
    )
    description = models.TextField(
        blank=True,
        help_text="Purpose and mandate of this governing body"
    )
    # Multiple secretaries; each entry is a UUID from IAM
    secretary_user_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of User UUIDs (from IAM) assigned as Secretaries to this body"
    )

    class Meta:
        db_table = 'legal_governing_body'
        ordering = ['name']
        verbose_name = 'Governing Body'
        verbose_name_plural = 'Governing Bodies'

    def __str__(self):
        return self.name

    def is_secretary(self, user_id: str) -> bool:
        """Return True if the given user UUID is a secretary of this body."""
        return str(user_id) in [str(uid) for uid in (self.secretary_user_ids or [])]
```

**Key field notes:**
- `secretary_user_ids` is a `JSONField(default=list)` — a list of UUID strings. Do not use a M2M relation; user objects are never stored in grc-service (E20.1).
- `committee_type` uses `on_delete=PROTECT` — deleting a committee type that has attached bodies is blocked at the database level.
- `is_secretary()` is a convenience model method used in view-level authorisation checks (E3.2: "Secretary can only create meetings for governing bodies to which they are assigned").

---

### 2.3 Member

**Purpose:** Represents a person sitting on a specific governing body. A lightweight local snapshot synced from Corporate Service via the `corporate.events` Kafka consumer. grc-service does not own the canonical staff record (E1.1).

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — UUID PK, timestamps, `created_by`, `modified_by`
- `StatusMixin` — `is_active` soft-delete (deactivated when `employee.deactivated` event received)
- No `WorkflowMixin`

**Relationships:**
- `Member.governing_body → GoverningBody` (FK)
- `Member.user_id` → IAM user (UUID reference only)

**Business rules:** E1.2 (user can be member of multiple bodies), E1.4 (MemberType distinguishes Committee Members from Management Members), E3.7 (members auto-populated on meeting creation)

```python
class Member(TimestampedModel, StatusMixin):
    """
    A person sitting on a governing body.
    Local snapshot synced from Corporate Service via Kafka.
    grc-service stores only the fields needed for meeting governance.
    Canonical record is owned by Corporate Service.
    """

    POSITION_CHOICES = [
        ('member', 'Member'),
        ('secretary', 'Secretary'),
        ('chairman', 'Chairman'),
    ]

    MEMBER_TYPE_CHOICES = [
        ('committee_member', 'Committee Member'),
        ('management_member', 'Management Member'),
    ]

    governing_body = models.ForeignKey(
        GoverningBody,
        on_delete=models.CASCADE,
        related_name='members',
        help_text="The governing body this member belongs to"
    )
    user_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the user (from IAM / Corporate Service)"
    )
    position = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES,
        default='member',
        db_index=True,
    )
    member_type = models.CharField(
        max_length=30,
        choices=MEMBER_TYPE_CHOICES,
        default='committee_member',
        db_index=True,
    )
    # Snapshot fields — updated by corporate.events Kafka consumer
    email = models.EmailField(
        blank=True,
        help_text="Email snapshot from Corporate Service (updated via Kafka)"
    )
    department = models.CharField(
        max_length=255,
        blank=True,
        help_text="Department snapshot from Corporate Service (updated via Kafka)"
    )
    joined_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date this person joined the governing body"
    )
    left_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date this person left the governing body (null = still active)"
    )

    class Meta:
        db_table = 'legal_member'
        ordering = ['governing_body', 'position', 'user_id']
        constraints = [
            models.UniqueConstraint(
                fields=['governing_body', 'user_id'],
                condition=models.Q(is_active=True),
                name='legal_member_active_body_user_uniq',
            )
        ]
        verbose_name = 'Member'
        verbose_name_plural = 'Members'

    def __str__(self):
        return f"Member {self.user_id} on {self.governing_body_id} ({self.get_position_display()})"
```

**Key field notes:**
- `user_id` is a plain `UUIDField` — no FK to auth.User (no User model exists in grc-service).
- Partial `UniqueConstraint` on `(governing_body, user_id)` where `is_active=True` — allows the same user to be re-added after deactivation without violating the constraint.
- `email` and `department` are **snapshot fields**. They are updated by the `corporate.events` Kafka consumer (`employee.profile.updated`), not by API writes. The view serializer marks them `read_only=True`.
- `is_active = False` is set by the Kafka consumer when an `employee.deactivated` event is received for this `user_id`.

---

## 3. Domain 2 — Determinations & Approvals

### 3.1 SubmissionForDetermination

**Purpose:** A formal request by any authenticated staff member asking a governing body to make an official binding decision on a matter. Feeds the meeting agenda. Upon determination, outcome is recorded back on the submission.

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — UUID PK, timestamps, `created_by` (submitter), `modified_by`
- `StatusMixin` — `is_active` soft-delete; soft-delete only permitted while Status = SUBMITTED (E2.2)
- No `WorkflowMixin` — internal status machine (no WO workflow plan required)

**Relationships:**
- `SubmissionForDetermination.target_body → GoverningBody` (FK)
- `SubmissionForDetermination.meeting → Meeting` (FK, nullable — set when Secretary attaches to agenda)
- Reverse: `MeetingAgenda.submission → SubmissionForDetermination`

**Workflow states:** `SUBMITTED → UNDER_REVIEW → DETERMINED`

**Business rules:** E2.1 (any authenticated user can create), E2.2 (edit/withdraw only while SUBMITTED), E2.3 (locked once UNDER_REVIEW), E2.4 (Secretary can only attach to matching body's meeting), E2.5 (outcome written back after determination)

```python
class SubmissionForDetermination(TimestampedModel, StatusMixin):
    """
    A formal matter submitted to a governing body for a binding determination.
    Can be raised by any authenticated staff member.
    Locked for editing once attached to a meeting agenda.
    """

    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('determined', 'Determined'),
        ('withdrawn', 'Withdrawn'),
    ]

    OUTCOME_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('deferred', 'Deferred'),
        ('noted', 'Noted'),
    ]

    title = models.CharField(
        max_length=500,
        help_text="Short title of the matter being submitted"
    )
    description = models.TextField(
        help_text="Full description of the matter and the determination sought"
    )
    submitter_user_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the user who created this submission (from IAM)"
    )
    submitter_dept = models.CharField(
        max_length=255,
        blank=True,
        help_text="Department of the submitter at time of submission (snapshot)"
    )
    submission_date = models.DateField(
        help_text="Date the submission was formally made"
    )
    target_body = models.ForeignKey(
        GoverningBody,
        on_delete=models.PROTECT,
        related_name='submissions',
        help_text="The governing body asked to make the determination"
    )
    supporting_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="List of document UUIDs from Document Records Service"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='submitted',
        db_index=True,
    )
    # Set by Secretary when attached to a meeting agenda
    meeting = models.ForeignKey(
        'Meeting',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_submissions',
        help_text="Meeting to which this submission is currently attached (null = not yet attached)"
    )
    # Written back after determination
    outcome = models.CharField(
        max_length=20,
        choices=OUTCOME_CHOICES,
        null=True,
        blank=True,
        help_text="Final determination outcome (set after meeting deliberation)"
    )
    outcome_notes = models.TextField(
        blank=True,
        help_text="Notes qualifying the determination outcome"
    )
    determination_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the governing body made its determination"
    )
    directives_created = models.JSONField(
        default=list,
        blank=True,
        help_text="List of MeetingDirective UUIDs auto-created from this submission's determination"
    )

    class Meta:
        db_table = 'legal_submission_for_determination'
        ordering = ['-submission_date', '-created_at']
        verbose_name = 'Submission for Determination'
        verbose_name_plural = 'Submissions for Determination'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_editable(self) -> bool:
        """True only while status = SUBMITTED (E2.2 & E2.3)."""
        return self.status == 'submitted'

    @property
    def is_locked(self) -> bool:
        """True once attached to a meeting agenda (E2.3)."""
        return self.status in ('under_review', 'determined')
```

**Key field notes:**
- `submitter_user_id` maps to `created_by` semantically but is kept separate so the submitter identity is always explicit in the payload (it must appear in API responses; `created_by` is an internal audit trail field).
- `supporting_documents` stores a list of UUID strings — documents uploaded to DRS before or during submission.
- `meeting` FK is nullable — null means "not yet assigned to any meeting". Set to the meeting's UUID when Secretary attaches it.
- `directives_created` is a denormalized list for fast lookup. The canonical FK relationship runs through `MeetingAgenda.directives_created` and the `MeetingDirective.agenda` FK.
- `is_editable` and `is_locked` properties are used in view-level permission checks — not DB constraints.

---

## 4. Domain 3 — Meeting Governance

### 4.1 Meeting

**Purpose:** Represents a formal governance meeting of a governing body. The central entity of the Meeting Governance domain. All agenda items, participants, minutes, resolutions, and directives are children of this entity.

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — UUID PK, timestamps, `created_by` (Secretary), `modified_by`
- `StatusMixin` — `is_active` soft-delete
- No `WorkflowMixin` — Meeting uses an internal 9-state machine (not a WO workflow plan)

**Relationships:**
- `Meeting.governing_body → GoverningBody` (FK)
- `Meeting.meeting_mode → MeetingMode` (FK to lookup)
- `Meeting.meeting_type → MeetingType` (FK to lookup; carries `quorum_percentage`)
- `Meeting ──< MeetingAgenda` (reverse FK)
- `Meeting ──< MeetingParticipant` (reverse FK)
- `Meeting ──1── Minutes` (OneToOneField on Minutes)
- `Meeting ──< Resolution` (reverse FK)
- `Meeting ──< MeetingDirective` (reverse FK)

**Workflow states:** `DRAFT → REGISTERED → INVITATIONS_SENT → AGENDA_SHARED → QUORUM_READY → ONGOING → POSTPONED → CLOSED | CANCELLED | RESCHEDULED`

**Business rules:** E3.1 (atomic meeting_number), E3.2 (Secretary owns body), E3.5 (quorum rule), E3.6 (ONGOING only when quorum + time), E3.11 (CLOSED is terminal)

```python
class Meeting(TimestampedModel, StatusMixin):
    """
    A formal governance meeting of a governing body.
    Central parent of all meeting-related child entities.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('registered', 'Registered'),
        ('invitations_sent', 'Invitations Sent'),
        ('agenda_shared', 'Agenda Shared'),
        ('quorum_ready', 'Quorum Ready'),
        ('ongoing', 'Ongoing'),
        ('postponed', 'Postponed'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ]

    governing_body = models.ForeignKey(
        GoverningBody,
        on_delete=models.PROTECT,
        related_name='meetings',
        help_text="The governing body holding this meeting"
    )
    # Auto-generated in view on registration; unique per governing body
    meeting_number = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Auto-generated meeting number unique per governing body (e.g., 'GC/2026/001')"
    )
    title = models.CharField(
        max_length=500,
        help_text="Official title of the meeting"
    )
    location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Physical location or venue name"
    )
    meeting_mode = models.ForeignKey(
        MeetingMode,
        on_delete=models.PROTECT,
        related_name='meetings',
        help_text="Physical/Virtual/Hybrid attendance mode"
    )
    venue_link = models.URLField(
        blank=True,
        help_text="Virtual meeting link (applicable for Virtual/Hybrid modes)"
    )
    scheduled_start = models.DateTimeField(
        help_text="Scheduled start date and time"
    )
    scheduled_end = models.DateTimeField(
        help_text="Scheduled end date and time"
    )
    meeting_type = models.ForeignKey(
        MeetingType,
        on_delete=models.PROTECT,
        related_name='meetings',
        help_text="Ordinary / Extraordinary / Special. Determines quorum threshold."
    )
    agenda_summary = models.TextField(
        blank=True,
        help_text="High-level summary of agenda topics (optional; set on AGENDA_SHARED)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
    )
    secretary_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the Secretary managing this meeting (from IAM)"
    )
    # --- Quorum tracking ---
    # Denormalized counters; updated each time a MeetingParticipant RSVP is saved
    total_member_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of governing body members (snapshot at registration)"
    )
    rsvp_yes_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of members who Accepted the invitation"
    )
    rsvp_no_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of members who Declined the invitation"
    )
    rsvp_pending_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of members with Pending RSVP"
    )
    # Computed on save; also computed by Celery Beat task every 15 min
    quorum_met = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the 51%+ quorum threshold has been reached (auto-calculated)"
    )
    quorum_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Current quorum percentage (auto-calculated: rsvp_yes / total_members × 100)"
    )

    class Meta:
        db_table = 'legal_meeting'
        ordering = ['-scheduled_start']
        constraints = [
            models.UniqueConstraint(
                fields=['governing_body', 'meeting_number'],
                condition=models.Q(is_active=True),
                name='legal_meeting_active_body_number_uniq',
            )
        ]
        verbose_name = 'Meeting'
        verbose_name_plural = 'Meetings'

    def __str__(self):
        return f"{self.meeting_number or 'DRAFT'} — {self.title}"

    def save(self, *args, **kwargs):
        """
        Auto-calculate quorum_met and quorum_percentage on every save.
        Skips recalculation when update_fields does not include quorum-related fields.
        Matches Internal Audit RiskAssessment.save() pattern.
        """
        update_fields = kwargs.get('update_fields')
        quorum_fields = {
            'rsvp_yes_count', 'rsvp_no_count', 'rsvp_pending_count', 'total_member_count'
        }
        should_calc = update_fields is None or bool(set(update_fields) & quorum_fields)

        if should_calc and self.total_member_count > 0:
            percentage = (self.rsvp_yes_count / self.total_member_count) * 100
            self.quorum_percentage = round(percentage, 2)
            # Quorum threshold from meeting_type lookup; fallback to 51%
            threshold = 51
            if self.meeting_type_id:
                try:
                    threshold = MeetingType.objects.get(pk=self.meeting_type_id).quorum_percentage
                except MeetingType.DoesNotExist:
                    pass
            self.quorum_met = self.quorum_percentage >= threshold
            if update_fields is not None:
                kwargs['update_fields'] = list(set(update_fields) | {'quorum_met', 'quorum_percentage'})

        super().save(*args, **kwargs)

    @property
    def can_start(self) -> bool:
        """
        True if meeting can be transitioned to ONGOING (E3.6).
        Requires quorum + current time is within the scheduled window.
        Business rule check only — does not enforce; view enforces.
        """
        now = timezone.now()
        return (
            self.quorum_met
            and self.status == 'quorum_ready'
            and self.scheduled_start <= now <= self.scheduled_end
        )

    def get_workflow_context(self) -> dict:
        """Not a WO workflow entity — returns empty context."""
        return {}
```

**Key field notes:**
- `meeting_number` is **blank by default** and auto-generated in the view on transition to `REGISTERED` status, using an atomic database sequence. It is never set by the client.
- `total_member_count`, `rsvp_yes_count`, `rsvp_no_count`, `rsvp_pending_count` are denormalized counters. They are incremented/decremented by the `MeetingParticipant` RSVP update view using `F()` expressions and `update_fields`, not by calling `save()` on Meeting.
- `save()` override only recalculates quorum fields — it does not perform status transitions.
- `MeetingType.quorum_percentage` carries the threshold (e.g., 51 for Ordinary, 67 for Special). The `save()` reads it via a DB lookup guarded with `try/except`.
- `on_delete=PROTECT` on `governing_body` and lookup FKs — meetings cannot exist without a valid body.

---

### 4.2 MeetingAgenda

**Purpose:** An agenda item within a meeting, sourced exclusively from a `SubmissionForDetermination`. Records the deliberation outcome of that item. Conflict declarations and directives are tracked per agenda item.

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — UUID PK, timestamps, `created_by` (Secretary), `modified_by`
- `StatusMixin` — `is_active` soft-delete
- No `WorkflowMixin`

**Relationships:**
- `MeetingAgenda.meeting → Meeting` (FK)
- `MeetingAgenda.submission → SubmissionForDetermination` (FK)
- `MeetingAgenda ──< ConflictDeclaration` (reverse FK)
- `MeetingAgenda ──< MeetingDirective` (reverse FK, nullable)
- `MeetingAgenda ──1── Resolution` (one agenda item → one auto-created Resolution)

**Business rules:** E3.3 (agenda items must come from submissions only), E2.4 (target body must match meeting body), C3 (outcomes propagate to submission)

```python
class MeetingAgenda(TimestampedModel, StatusMixin):
    """
    A single agenda item in a meeting, sourced from a SubmissionForDetermination.
    Outcome of deliberation is recorded here and written back to the submission.
    """

    OUTCOME_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('noted', 'Noted'),
        ('deferred', 'Deferred'),
    ]

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='agenda_items',
        help_text="The meeting this agenda item belongs to"
    )
    submission = models.ForeignKey(
        SubmissionForDetermination,
        on_delete=models.PROTECT,
        related_name='agenda_items',
        help_text="The submission being deliberated in this agenda item"
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order within the meeting agenda (1-indexed)"
    )
    # Denormalized from submission for display (snapshot at time of attachment)
    title = models.CharField(
        max_length=500,
        help_text="Title of this agenda item (snapshot from submission)"
    )
    description = models.TextField(
        blank=True,
        help_text="Description snapshot from submission"
    )
    # Additional documents attached specifically to this agenda item
    documents = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional document UUIDs from Document Records Service for this agenda item"
    )
    # Outcome recorded during ONGOING meeting by Secretary
    outcome = models.CharField(
        max_length=20,
        choices=OUTCOME_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        help_text="Determination outcome for this agenda item"
    )
    outcome_notes = models.TextField(
        blank=True,
        help_text="Qualifying notes on the determination outcome"
    )
    outcome_recorded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when outcome was recorded"
    )
    directives_created = models.JSONField(
        default=list,
        blank=True,
        help_text="List of MeetingDirective UUIDs auto-created from this item's determination"
    )

    class Meta:
        db_table = 'legal_meeting_agenda'
        ordering = ['meeting', 'order']
        constraints = [
            models.UniqueConstraint(
                fields=['meeting', 'submission'],
                condition=models.Q(is_active=True),
                name='legal_meeting_agenda_active_meeting_submission_uniq',
            )
        ]
        verbose_name = 'Meeting Agenda Item'
        verbose_name_plural = 'Meeting Agenda Items'

    def __str__(self):
        return f"Agenda #{self.order}: {self.title} ({self.meeting_id})"
```

**Key field notes:**
- `UniqueConstraint` on `(meeting, submission)` where `is_active=True` prevents the same submission from being attached twice to the same meeting, while allowing historical (deactivated) records to coexist.
- `title` and `description` are snapshots from the submission at attachment time. They do not update if the submission is later modified.
- When `outcome` is set, the view must also: (a) write outcome back to `submission.outcome` and `submission.determination_date`, (b) transition `submission.status → determined`, (c) auto-create a `Resolution` record.

---

### 4.3 ConflictDeclaration

**Purpose:** Records a member's declaration of personal or financial conflict of interest on a specific agenda item. Excludes that member from votes on that item only (E4.2). Effectively immutable once created — no update or delete by users.

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — creation tracked (declared by member; `created_by` = member's `user_id`)
- `StatusMixin` — `is_active` flag; only administrator can deactivate (correction of erroneous declarations)
- No `WorkflowMixin`

**Relationships:**
- `ConflictDeclaration.agenda_item → MeetingAgenda` (FK)
- `ConflictDeclaration.member_user_id` → IAM user (UUID reference)

**Business rules:** E4.1 (conflict is agenda-item level, not meeting level), E4.3 (no effect on other items or future meetings)

```python
class ConflictDeclaration(TimestampedModel, StatusMixin):
    """
    A member's declaration of conflict of interest on a specific agenda item.
    Excludes the member from votes on that item only.
    Created by the member; effectively append-only from the member's perspective.
    """
    agenda_item = models.ForeignKey(
        MeetingAgenda,
        on_delete=models.CASCADE,
        related_name='conflict_declarations',
        help_text="The agenda item on which the conflict is declared"
    )
    member_user_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the member declaring the conflict (from IAM)"
    )
    declared_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Exact timestamp of the conflict declaration"
    )
    reason = models.TextField(
        blank=True,
        help_text="Optional explanation of the nature of the conflict"
    )

    class Meta:
        db_table = 'legal_conflict_declaration'
        ordering = ['agenda_item', 'declared_at']
        constraints = [
            models.UniqueConstraint(
                fields=['agenda_item', 'member_user_id'],
                condition=models.Q(is_active=True),
                name='legal_conflict_declaration_active_item_member_uniq',
            )
        ]
        verbose_name = 'Conflict Declaration'
        verbose_name_plural = 'Conflict Declarations'

    def __str__(self):
        return f"Conflict by {self.member_user_id} on agenda item {self.agenda_item_id}"
```

**Key field notes:**
- `declared_at` uses `auto_now_add=True` — the exact timestamp is system-set and non-editable. This provides a tamper-evident declaration record.
- `UniqueConstraint` prevents a member from declaring conflict on the same agenda item twice (while `is_active=True`).
- The view checks this table on any vote/determination action to exclude conflicted members before applying the outcome.

---

### 4.4 MeetingParticipant

**Purpose:** Records the participation of a person (governing body member or invited observer) in a specific meeting. Tracks invitation status for quorum calculation. Auto-populated for all active members when a meeting is registered (E3.7); additional invitees can be added manually.

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — creation tracked
- `StatusMixin` — `is_active` soft-delete
- No `WorkflowMixin`

**Relationships:**
- `MeetingParticipant.meeting → Meeting` (FK)
- `MeetingParticipant.user_id` → IAM user (UUID reference)

**Business rules:** E3.5 (only Accepted count for quorum), E3.7 (auto-populated on registration), E3.8 (invitees read-only; cannot vote)

```python
class MeetingParticipant(TimestampedModel, StatusMixin):
    """
    Participation record for a meeting.
    Auto-created for all active governing body members when meeting is REGISTERED.
    Additional invitees can be added manually before ONGOING.
    """

    ROLE_CHOICES = [
        ('member', 'Member'),        # Governing body member — can vote
        ('invitee', 'Invitee'),      # Observer — read-only; cannot vote (E3.8)
        ('secretary', 'Secretary'),  # Secretary of the meeting
    ]

    INVITATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='participants',
        help_text="The meeting this participant is linked to"
    )
    user_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the participant (from IAM)"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member',
        db_index=True,
    )
    invitation_status = models.CharField(
        max_length=20,
        choices=INVITATION_STATUS_CHOICES,
        default='pending',
        db_index=True,
    )
    decline_reason = models.TextField(
        blank=True,
        help_text="Reason provided when declining the invitation"
    )
    attendance_marked = models.BooleanField(
        default=False,
        help_text="Whether physical/virtual attendance was confirmed during the meeting"
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the participant accepted or declined"
    )

    class Meta:
        db_table = 'legal_meeting_participant'
        ordering = ['meeting', 'role', 'user_id']
        constraints = [
            models.UniqueConstraint(
                fields=['meeting', 'user_id'],
                condition=models.Q(is_active=True),
                name='legal_meeting_participant_active_meeting_user_uniq',
            )
        ]
        verbose_name = 'Meeting Participant'
        verbose_name_plural = 'Meeting Participants'

    def __str__(self):
        return f"{self.user_id} — {self.get_role_display()} at {self.meeting_id}"
```

**Key field notes:**
- When `invitation_status` is updated (RSVP), the view must also update `Meeting.rsvp_yes_count` / `rsvp_no_count` / `rsvp_pending_count` using `F()` expressions:
  ```python
  # In the RSVP view, after saving the participant:
  if previous_status != new_status:
      from django.db.models import F
      update = {}
      if previous_status == 'pending':
          update['rsvp_pending_count'] = F('rsvp_pending_count') - 1
      elif previous_status == 'accepted':
          update['rsvp_yes_count'] = F('rsvp_yes_count') - 1
      elif previous_status == 'declined':
          update['rsvp_no_count'] = F('rsvp_no_count') - 1
      if new_status == 'accepted':
          update['rsvp_yes_count'] = F('rsvp_yes_count') + 1
      elif new_status == 'declined':
          update['rsvp_no_count'] = F('rsvp_no_count') + 1
      elif new_status == 'pending':
          update['rsvp_pending_count'] = F('rsvp_pending_count') + 1
      Meeting.objects.filter(pk=participant.meeting_id).update(**update)
  ```
- Only participants with `role='member'` and `invitation_status='accepted'` count toward quorum (E3.5).
- `responded_at` is set in the view when `invitation_status` changes from `pending`.

---

### 4.5 MeetingDirective

**Purpose:** A formal action item issued during a meeting (to any agenda item or Matters Arising), assigned to a person or organisational unit. Persists across meetings in Matters Arising until finally closed by the Secretary. This entity is distinct from `LitigationDirective` (which is DG-issued on cases, covered in Part 2).

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — creation tracked (Secretary creates)
- `StatusMixin` — `is_active` soft-delete
- No `WorkflowMixin` — two-actor closure is internal state machine (not a WO workflow)

**Relationships:**
- `MeetingDirective.meeting → Meeting` (FK — the meeting where it was issued)
- `MeetingDirective.agenda_item → MeetingAgenda` (FK, nullable — Matters Arising directives have no agenda item)
- `MeetingDirective.directive_priority → DirectivePriority` (FK to lookup)
- `MeetingDirective.directive_category → DirectiveCategory` (FK to lookup)
- `MeetingDirective.finally_closed_in_meeting → Meeting` (FK, nullable — meeting where final closure occurred)
- `MeetingDirective.assigned_user_id` → IAM user (UUID reference)

**Workflow states:** `OPEN → IN_PROGRESS → OVERDUE (auto) → CLOSED (by assignee) → FULLY_CLOSED (by Secretary)`

**Business rules:** E5.1 (only assignee can close), E5.2 (only Secretary can finally_close, in a subsequent meeting's Matters Arising), E5.3 (completion summary required), E5.4 (auto-OVERDUE), E5.5 (FULLY_CLOSED excluded from Matters Arising), E5.7 (can only be added during ONGOING meeting)

```python
class MeetingDirective(TimestampedModel, StatusMixin):
    """
    A formal action item issued during or after a meeting.
    Tracks compliance with meeting decisions. Persists in Matters Arising
    of subsequent meetings until finally closed by the Secretary.
    Distinct from LitigationDirective (Part 2).
    """

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('overdue', 'Overdue'),
        ('closed', 'Closed'),
        ('fully_closed', 'Fully Closed'),
    ]

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='directives',
        help_text="The meeting in which this directive was issued"
    )
    agenda_item = models.ForeignKey(
        MeetingAgenda,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='directives',
        help_text="Agenda item this directive relates to (null = Matters Arising)"
    )
    directive_priority = models.ForeignKey(
        DirectivePriority,
        on_delete=models.PROTECT,
        related_name='meeting_directives',
        help_text="Priority classification of this directive"
    )
    directive_category = models.ForeignKey(
        DirectiveCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='meeting_directives',
        help_text="Thematic category of this directive (optional)"
    )
    description = models.TextField(
        help_text="Full text of the directive instruction"
    )
    assigned_org_unit = models.CharField(
        max_length=255,
        blank=True,
        help_text="Organisational unit responsible (name or code)"
    )
    assigned_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the individual assigned to action this directive"
    )
    due_date = models.DateField(
        help_text="Date by which this directive must be closed"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        db_index=True,
    )
    completion_summary = models.TextField(
        blank=True,
        help_text="Summary of actions taken to close this directive (required on CLOSED)"
    )
    completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the directive was actioned and closed by the assignee"
    )
    evidence_document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of supporting evidence document from Document Records Service"
    )
    # Final closure fields — set by Secretary in a subsequent Matters Arising
    fully_closed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True once Secretary performs final closure in Matters Arising"
    )
    finally_closed_in_meeting = models.ForeignKey(
        Meeting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finally_closed_directives',
        help_text="The subsequent meeting in which final closure was confirmed"
    )
    finally_closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of final closure"
    )
    finally_closed_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of the Secretary who performed final closure"
    )

    class Meta:
        db_table = 'legal_meeting_directive'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['meeting', 'status']),
            models.Index(fields=['assigned_user_id', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]
        verbose_name = 'Meeting Directive'
        verbose_name_plural = 'Meeting Directives'

    def __str__(self):
        return f"Directive [{self.get_status_display()}] — {str(self.description)[:80]}"

    @property
    def is_matters_arising(self) -> bool:
        """True if this directive was added to Matters Arising (no agenda item)."""
        return self.agenda_item_id is None

    @property
    def is_closeable_by_assignee(self) -> bool:
        """True if the assignee can perform initial closure (E5.1)."""
        return self.status in ('open', 'in_progress', 'overdue')

    @property
    def is_finally_closeable(self) -> bool:
        """True if the Secretary can perform final closure (E5.2)."""
        return self.status == 'closed' and not self.fully_closed
```

**Query for Matters Arising (used in meeting views):**
```python
# All open directives for a governing body — excludes fully_closed (E5.5)
MeetingDirective.objects.filter(
    meeting__governing_body=governing_body,
    fully_closed=False,
    is_active=True,
).exclude(
    status='fully_closed',
).order_by('due_date', '-directive_priority__order')
```

---

### 4.6 Minutes

**Purpose:** The official written record of a meeting's proceedings. Drafted by the Secretary after the meeting is ONGOING or CLOSED. Submitted to participating members for approval via Work Orchestration. Becomes the legal record once approved.

**Composition:** `TimestampedModel, StatusMixin, WorkflowMixin`
- `TimestampedModel` — UUID PK, timestamps, `created_by` (Secretary), `modified_by`
- `StatusMixin` — `is_active` soft-delete
- `WorkflowMixin` — WO multi-signoff workflow for member approval (template: `grc.legal_minutes_approval`)

**Relationships:**
- `Minutes.meeting → Meeting` (OneToOneField — one meeting → one set of minutes)
- `Minutes.approved_by` → JSONField of UUID list (members who approved)

**Workflow states:** `DRAFT → PENDING_APPROVAL → APPROVED`

**Business rules:** E6.1 (only after ONGOING/CLOSED), E6.2 (only Secretary can draft), E6.3 (approval method configurable), E6.4 (APPROVED = read-only and final)

```python
class Minutes(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Official written record of a meeting's proceedings.
    Enters a Work Orchestration multi-signoff workflow for member approval.
    Once APPROVED, becomes read-only and final (E6.4).
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
    ]

    meeting = models.OneToOneField(
        Meeting,
        on_delete=models.CASCADE,
        related_name='minutes',
        help_text="The meeting these minutes belong to (one meeting = one minutes record)"
    )
    title = models.CharField(
        max_length=500,
        help_text="Official title of the minutes document"
    )
    content = models.TextField(
        help_text="Full text content of the meeting minutes"
    )
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text="List of document UUIDs from Document Records Service"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
    )
    # Populated as members approve (each approval appends the approver's UUID)
    approved_by = models.JSONField(
        default=list,
        blank=True,
        help_text="List of User UUIDs who have approved these minutes"
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when minutes reached approved status"
    )

    class Meta:
        db_table = 'legal_minutes'
        ordering = ['-created_at']
        verbose_name = 'Minutes'
        verbose_name_plural = 'Minutes'

    def __str__(self):
        return f"Minutes — {self.title} ({self.get_status_display()})"

    def get_workflow_context(self) -> dict:
        """
        Context variables for WO assignee resolution.
        Template: grc.legal_minutes_approval.
        Provides meeting participant UUIDs as the multi-signoff assignee list.
        """
        return {
            'minutes_id':   str(self.id),
            'meeting_id':   str(self.meeting_id),
            'meeting_ref':  self.meeting.meeting_number,
            'meeting_title': self.meeting.title,
            'secretary_id': str(self.created_by),
        }

    def get_workflow_metadata(self) -> dict:
        """Metadata stored with the WO plan for display in WO console."""
        meta = {
            'entity_type':   'minutes',
            'entity_id':     str(self.id),
            'meeting_ref':   self.meeting.meeting_number,
            'meeting_title': self.meeting.title,
            'status':        self.status,
        }
        return add_entity_detail_path_to_metadata(meta, 'minutes')

    def log_workflow_action(self, action, actor_id, stage_name, comment='', metadata=None) -> None:
        """Persist LegalAuditLog record for each WO stage action."""
        LegalAuditLog.objects.create(
            entity_type='minutes',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            stage_name=stage_name,
            comment=comment or '',
            metadata=metadata or {},
        )
```

**Key field notes:**
- `OneToOneField` to `Meeting` enforces the "one meeting → one minutes record" constraint at the DB level. DRF serializer returns a 400 if a second Minutes is created for the same meeting.
- `approved_by` is a JSONField list — appended to on each approval action. The WO multi-signoff stage fires a `workflow-events` Kafka event on each signoff; the consumer appends to `approved_by` and checks the threshold.
- `WorkflowMixin` fields (`workflow_plan_id`, `workflow_stage`, etc.) are all set by `MinutesService.submit_for_approval()` — never by the client.

---

### 4.7 Resolution

**Purpose:** Formal decision adopted during a meeting on a specific agenda item. Auto-created by the system from agenda item outcomes; not manually created. Visible only to meeting participants (E7.2). Read-only post-creation.

**Composition:** `TimestampedModel, StatusMixin`
- `TimestampedModel` — creation tracked (system creates; `created_by` = Secretary's UUID)
- `StatusMixin` — `is_active` flag; resolutions are never soft-deleted (retained permanently)
- No `WorkflowMixin` — no WO workflow

**Relationships:**
- `Resolution.meeting → Meeting` (FK)
- `Resolution.agenda_item → MeetingAgenda` (FK)
- `Resolution.responsible_person_id` → IAM user (UUID reference, nullable)

**Business rules:** E7.1 (auto-created only), E7.2 (visible to invited participants only), E7.3 (searchable within that set)

```python
class Resolution(TimestampedModel, StatusMixin):
    """
    Formal decision adopted during a meeting for a specific agenda item.
    System-created from agenda item outcomes; never manually created.
    Read-only post-creation. Visible only to meeting participants (E7.2).
    """

    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('noted', 'Noted'),
    ]

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='resolutions',
        help_text="The meeting in which this resolution was adopted"
    )
    agenda_item = models.OneToOneField(
        MeetingAgenda,
        on_delete=models.CASCADE,
        related_name='resolution',
        help_text="The agenda item from which this resolution was derived (one item = one resolution)"
    )
    resolution_text = models.TextField(
        help_text="Full text of the adopted resolution"
    )
    date_adopted = models.DateTimeField(
        help_text="Date and time the resolution was formally adopted"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True,
    )
    responsible_person_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the person responsible for implementing this resolution (from IAM)"
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date from which this resolution takes effect"
    )
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text="List of document UUIDs from Document Records Service"
    )

    class Meta:
        db_table = 'legal_resolution'
        ordering = ['meeting', 'date_adopted']
        verbose_name = 'Resolution'
        verbose_name_plural = 'Resolutions'

    def __str__(self):
        return f"Resolution [{self.get_status_display()}] — {self.meeting_id}"
```

**Key field notes:**
- `OneToOneField` on `agenda_item` enforces "one agenda item → one resolution" at the DB level (E7.1).
- Resolution access control is enforced in the view: query is scoped to meetings where the requesting user is a `MeetingParticipant`. No model-level access control needed.
- `responsible_person_id` is optional — some resolutions are noted without a designated responsible party.

---

## 5. Cross-cutting — LegalAuditLog

**Purpose:** Immutable append-only log of every domain-level action, state transition, approvals, and workflow event across all Legal module entities. Required by E18 business rules. Never updated or deleted.

**Composition:** `BaseModel` only
- `BaseModel` — UUID PK, `created_at`, `updated_at`
- No `StatusMixin` — audit logs are never deactivated (E18.3)
- No `TimestampedModel` — no `created_by`/`modified_by` mixin (actor is part of the log payload)
- No `WorkflowMixin`

**Population:** Written directly by model `log_workflow_action()` overrides, and by views in a `try/finally` block for all state transitions.

```python
class LegalAuditLog(BaseModel):
    """
    Immutable domain-level audit trail for all Legal module state transitions,
    approvals, and workflow actions.
    Append-only: records are never updated or deactivated (E18.3).
    """
    entity_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Model name of the entity being acted on (e.g., 'meeting', 'filing_defendant')"
    )
    entity_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the entity being acted on"
    )
    action = models.CharField(
        max_length=100,
        help_text="The action performed (e.g., 'status_change', 'approve', 'close', 'create')"
    )
    actor_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the user who performed the action (from IAM)"
    )
    previous_status = models.CharField(
        max_length=50,
        blank=True,
        help_text="Status of the entity before this action"
    )
    new_status = models.CharField(
        max_length=50,
        blank=True,
        help_text="Status of the entity after this action"
    )
    stage_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="WO workflow stage name (for workflow-related actions)"
    )
    comment = models.TextField(
        blank=True,
        help_text="User-provided comment or reason for the action"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the actor at time of action"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context (e.g., changed field values, WO plan ID, signature hash)"
    )

    class Meta:
        db_table = 'legal_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['actor_id', 'created_at']),
            models.Index(fields=['entity_type', 'created_at']),
        ]
        verbose_name = 'Legal Audit Log'
        verbose_name_plural = 'Legal Audit Logs'

    def __str__(self):
        return f"{self.entity_type}/{self.entity_id} — {self.action} at {self.created_at}"
```

**Usage pattern in views:**

```python
# After every state transition in a Legal view, inside transaction.atomic():
LegalAuditLog.objects.create(
    entity_type='meeting',
    entity_id=meeting.id,
    action='status_change',
    actor_id=request.user_id,
    previous_status=previous_status,
    new_status=meeting.status,
    comment=request.data.get('comment', ''),
    ip_address=request.META.get('REMOTE_ADDR'),
    metadata={
        'meeting_number': meeting.meeting_number,
        'governing_body_id': str(meeting.governing_body_id),
    }
)
```

**Digital signature metadata** (E17 rules) is stored in `metadata` as a nested dict:
```json
{
    "signature": {
        "signer_name": "John Doe",
        "signer_id": "<uuid>",
        "signed_at": "2026-03-19T10:30:00Z",
        "document_hash": "sha256:..."
    }
}
```

---

## 6. Entity Quick Reference

### Part 1 entities at a glance

| Entity | db_table | Mixins | WorkflowMixin | WO Template |
|---|---|---|:---:|---|
| `CommitteeType` | `legal_committee_type` | Base, Status | ✗ | — |
| `GoverningBody` | `legal_governing_body` | Timestamped, Status | ✗ | — |
| `Member` | `legal_member` | Timestamped, Status | ✗ | — |
| `SubmissionForDetermination` | `legal_submission_for_determination` | Timestamped, Status | ✗ | — |
| `Meeting` | `legal_meeting` | Timestamped, Status | ✗ | — |
| `MeetingAgenda` | `legal_meeting_agenda` | Timestamped, Status | ✗ | — |
| `ConflictDeclaration` | `legal_conflict_declaration` | Timestamped, Status | ✗ | — |
| `MeetingParticipant` | `legal_meeting_participant` | Timestamped, Status | ✗ | — |
| `MeetingDirective` | `legal_meeting_directive` | Timestamped, Status | ✗ | — |
| `Minutes` | `legal_minutes` | Timestamped, Status, **Workflow** | ✓ | `grc.legal_minutes_approval` |
| `Resolution` | `legal_resolution` | Timestamped, Status | ✗ | — |
| `LegalAuditLog` | `legal_audit_log` | Base only | ✗ | — |

### Status machine summary

| Entity | Status Choices | Terminal States |
|---|---|---|
| `SubmissionForDetermination` | submitted, under_review, determined, withdrawn | determined, withdrawn |
| `Meeting` | draft, registered, invitations_sent, agenda_shared, quorum_ready, ongoing, postponed, closed, cancelled, rescheduled | closed, cancelled |
| `MeetingDirective` | open, in_progress, overdue, closed, fully_closed | fully_closed |
| `Minutes` | draft, pending_approval, approved | approved |
| `Resolution` | approved, rejected, noted | all (auto-created, not transitioned) |

### Relationships summary (Part 1)

```
CommitteeType ──< GoverningBody ──< Member
                                ──< Meeting ──< MeetingAgenda ──< ConflictDeclaration
                                │                              ──< MeetingDirective
                                │                              ──1── Resolution
                                ──< MeetingParticipant         
                                ──1── Minutes
                                ──< MeetingDirective (governing body level)
                 
GoverningBody ──< SubmissionForDetermination ──1── MeetingAgenda
                                             ──1── MeetingDirective (if triggers directives)

Meeting (finally_closed_in_meeting) ──< MeetingDirective (final closure reference)
Minutes.meeting (OneToOneField) → Meeting
Resolution.agenda_item (OneToOneField) → MeetingAgenda
```

---

*End of Part 1 — Governance Structure, Determinations, Meeting Governance, LegalAuditLog*
*Next: Part 2 — Litigation Entities (CaseDefendant, CasePlaintiff, and all child entities) + PublicDecision*
