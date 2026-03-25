"""
Legal module entity models for grc-service.
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
    CourtLevel,
    LitigationUrgencyLevel,
    LitigationRiskLevel,
    MeetingMode,
    MeetingType,
    DirectivePriority,
    DirectiveCategory,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Counter Models — Atomic reference number generation
# ═══════════════════════════════════════════════════════════════════════════════

class LegalCaseCounter(BaseModel):
    """Atomic sequence counter for case reference numbers."""
    case_type = models.CharField(max_length=20, help_text="'defendant' or 'plaintiff'")
    year = models.PositiveIntegerField()
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'grc_legal_case_counter'
        unique_together = [('case_type', 'year')]

    def __str__(self):
        return f"{self.case_type}/{self.year} → {self.sequence}"


class MeetingCounter(BaseModel):
    """Atomic sequence counter for meeting numbers per governing body."""
    governing_body_id = models.UUIDField(db_index=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'grc_meeting_counter'
        unique_together = [('governing_body_id',)]

    def __str__(self):
        return f"Meeting counter {self.governing_body_id} → {self.sequence}"


class LegalNoticeCounter(BaseModel):
    """Atomic sequence counter for legal notice reference numbers."""
    year = models.PositiveIntegerField()
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'grc_legal_notice_counter'
        unique_together = [('year',)]

    def __str__(self):
        return f"LegalNotice {self.year} → {self.sequence}"


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 1 — Governance Structure
# ═══════════════════════════════════════════════════════════════════════════════

class CommitteeType(BaseModel, StatusMixin):
    """Classification of a governing body type. Admin-managed, not user-created."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'legal_committee_type'
        ordering = ['name']
        verbose_name = 'Committee Type'
        verbose_name_plural = 'Committee Types'

    def __str__(self):
        return f"{self.code} — {self.name}"


class GoverningBody(TimestampedModel, StatusMixin):
    """A formal committee or governing body within FCC."""
    committee_type = models.ForeignKey(
        CommitteeType, on_delete=models.PROTECT, related_name='governing_bodies',
    )
    name = models.CharField(max_length=255)
    composite_title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    secretary_user_ids = models.JSONField(default=list, blank=True)

    # ── Meeting number configuration (MIN-18) ────────────────────────────────
    MEETING_NUMBER_FORMAT_CHOICES = [
        ('sequential', 'Sequential'),
        ('financial_year', 'Financial Year'),
    ]
    meeting_number_prefix = models.CharField(max_length=20, blank=True)
    meeting_number_format = models.CharField(
        max_length=20,
        choices=MEETING_NUMBER_FORMAT_CHOICES,
        default='sequential',
    )

    class Meta:
        db_table = 'legal_governing_body'
        ordering = ['name']
        verbose_name = 'Governing Body'
        verbose_name_plural = 'Governing Bodies'

    def __str__(self):
        return self.name

    def is_secretary(self, user_id: str) -> bool:
        return str(user_id) in [str(uid) for uid in (self.secretary_user_ids or [])]


class Member(TimestampedModel, StatusMixin):
    """A person sitting on a governing body. Local snapshot synced from Corporate Service."""

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
        GoverningBody, on_delete=models.CASCADE, related_name='members',
    )
    user_id = models.UUIDField(db_index=True)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='member', db_index=True)
    member_type = models.CharField(max_length=30, choices=MEMBER_TYPE_CHOICES, default='committee_member', db_index=True)
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=255, blank=True)
    joined_date = models.DateField(null=True, blank=True)
    left_date = models.DateField(null=True, blank=True)

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

    def __str__(self):
        return f"Member {self.user_id} on {self.governing_body_id} ({self.get_position_display()})"


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 2 — Determinations & Approvals
# ═══════════════════════════════════════════════════════════════════════════════

class SubmissionForDetermination(TimestampedModel, StatusMixin):
    """A formal matter submitted to a governing body for a binding determination."""

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

    title = models.CharField(max_length=500)
    description = models.TextField()
    submitter_user_id = models.UUIDField(db_index=True)
    submitter_dept = models.CharField(max_length=255, blank=True)
    submission_date = models.DateField()
    target_body = models.ForeignKey(
        GoverningBody, on_delete=models.PROTECT, related_name='submissions',
    )
    supporting_documents = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted', db_index=True)
    meeting = models.ForeignKey(
        'Meeting', on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_submissions',
    )
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, null=True, blank=True)
    outcome_notes = models.TextField(blank=True)
    determination_date = models.DateTimeField(null=True, blank=True)
    directives_created = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'legal_submission_for_determination'
        ordering = ['-submission_date', '-created_at']
        verbose_name = 'Submission for Determination'
        verbose_name_plural = 'Submissions for Determination'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_editable(self) -> bool:
        return self.status == 'submitted'

    @property
    def is_locked(self) -> bool:
        return self.status in ('under_review', 'determined')


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 3 — Meeting Governance
# ═══════════════════════════════════════════════════════════════════════════════

class Meeting(TimestampedModel, StatusMixin, WorkflowMixin):
    """A formal governance meeting of a governing body."""

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
        GoverningBody, on_delete=models.PROTECT, related_name='meetings',
    )
    meeting_number = models.CharField(max_length=50, blank=True, db_index=True)
    title = models.CharField(max_length=500)
    location = models.CharField(max_length=500, blank=True)
    meeting_mode = models.ForeignKey(
        MeetingMode, on_delete=models.PROTECT, related_name='meetings',
    )
    venue_link = models.URLField(blank=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    meeting_type = models.ForeignKey(
        MeetingType, on_delete=models.PROTECT, related_name='meetings',
    )
    agenda_summary = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    secretary_id = models.UUIDField(db_index=True)
    # Quorum tracking
    total_member_count = models.PositiveIntegerField(default=0)
    rsvp_yes_count = models.PositiveIntegerField(default=0)
    rsvp_no_count = models.PositiveIntegerField(default=0)
    rsvp_pending_count = models.PositiveIntegerField(default=0)
    quorum_met = models.BooleanField(default=False, db_index=True)
    quorum_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # ── Rescheduling (SIG-10) ────────────────────────────────────────────────
    reschedule_reason = models.TextField(blank=True)

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

    def __str__(self):
        return f"{self.meeting_number or 'DRAFT'} — {self.title}"

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        quorum_fields = {'rsvp_yes_count', 'rsvp_no_count', 'rsvp_pending_count', 'total_member_count'}
        should_calc = update_fields is None or bool(set(update_fields) & quorum_fields)

        if should_calc and self.total_member_count > 0:
            percentage = (self.rsvp_yes_count / self.total_member_count) * 100
            self.quorum_percentage = round(percentage, 2)
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
        now = timezone.now()
        return (
            self.quorum_met
            and self.status == 'quorum_ready'
            and self.scheduled_start <= now <= self.scheduled_end
        )

    def get_workflow_context(self) -> dict:
        return {
            'meeting_id': str(self.id),
            'meeting_ref': self.meeting_number,
            'meeting_title': self.title,
            'governing_body_id': str(self.governing_body_id),
            'secretary_id': str(self.secretary_id),
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'meeting',
            'entity_id': str(self.id),
            'meeting_ref': self.meeting_number,
            'meeting_title': self.title,
            'status': self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'meeting')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='meeting',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class MeetingAgenda(TimestampedModel, StatusMixin):
    """A single agenda item in a meeting, sourced from a SubmissionForDetermination."""

    OUTCOME_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('noted', 'Noted'),
        ('deferred', 'Deferred'),
    ]

    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name='agenda_items',
    )
    submission = models.ForeignKey(
        SubmissionForDetermination, on_delete=models.PROTECT, null=True, blank=True,
        related_name='agenda_items',
    )
    source_directive = models.ForeignKey(
        'MeetingDirective', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='arising_agenda_items',
    )
    order = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    documents = models.JSONField(default=list, blank=True)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, null=True, blank=True, db_index=True)
    outcome_notes = models.TextField(blank=True)
    outcome_recorded_at = models.DateTimeField(null=True, blank=True)
    directives_created = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'legal_meeting_agenda'
        ordering = ['meeting', 'order']
        constraints = [
            models.UniqueConstraint(
                fields=['meeting', 'submission'],
                condition=models.Q(is_active=True, submission__isnull=False),
                name='legal_meeting_agenda_active_meeting_submission_uniq',
            ),
            models.UniqueConstraint(
                fields=['meeting', 'source_directive'],
                condition=models.Q(is_active=True, source_directive__isnull=False),
                name='legal_meeting_agenda_active_meeting_directive_uniq',
            ),
        ]

    def __str__(self):
        return f"Agenda #{self.order}: {self.title} ({self.meeting_id})"


class ConflictDeclaration(TimestampedModel, StatusMixin):
    """A member's declaration of conflict of interest on a specific agenda item."""
    agenda_item = models.ForeignKey(
        MeetingAgenda, on_delete=models.CASCADE, related_name='conflict_declarations',
    )
    member_user_id = models.UUIDField(db_index=True)
    declared_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

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

    def __str__(self):
        return f"Conflict by {self.member_user_id} on agenda item {self.agenda_item_id}"


class MeetingParticipant(TimestampedModel, StatusMixin):
    """Participation record for a meeting."""

    ROLE_CHOICES = [
        ('member', 'Member'),
        ('invitee', 'Invitee'),
        ('secretary', 'Secretary'),
    ]
    INVITATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name='participants',
    )
    user_id = models.UUIDField(db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member', db_index=True)
    invitation_status = models.CharField(max_length=20, choices=INVITATION_STATUS_CHOICES, default='pending', db_index=True)
    decline_reason = models.TextField(blank=True)
    attendance_marked = models.BooleanField(default=False)
    responded_at = models.DateTimeField(null=True, blank=True)

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

    def __str__(self):
        return f"{self.user_id} — {self.get_role_display()} at {self.meeting_id}"


class MeetingDirective(TimestampedModel, StatusMixin):
    """A formal action item issued during a meeting."""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('overdue', 'Overdue'),
        ('closed', 'Closed'),
        ('fully_closed', 'Fully Closed'),
    ]

    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name='directives',
    )
    agenda_item = models.ForeignKey(
        MeetingAgenda, on_delete=models.SET_NULL, null=True, blank=True, related_name='directives',
    )
    directive_priority = models.ForeignKey(
        DirectivePriority, on_delete=models.PROTECT, related_name='meeting_directives',
    )
    directive_category = models.ForeignKey(
        DirectiveCategory, on_delete=models.PROTECT, null=True, blank=True, related_name='meeting_directives',
    )
    description = models.TextField()
    assigned_org_unit = models.CharField(max_length=255, blank=True)
    assigned_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    completion_summary = models.TextField(blank=True)
    completion_date = models.DateField(null=True, blank=True)
    evidence_document_id = models.UUIDField(null=True, blank=True)
    fully_closed = models.BooleanField(default=False, db_index=True)
    finally_closed_in_meeting = models.ForeignKey(
        Meeting, on_delete=models.SET_NULL, null=True, blank=True, related_name='finally_closed_directives',
    )
    finally_closed_at = models.DateTimeField(null=True, blank=True)
    finally_closed_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'legal_meeting_directive'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['meeting', 'status']),
            models.Index(fields=['assigned_user_id', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]

    def __str__(self):
        return f"Directive [{self.get_status_display()}] — {str(self.description)[:80]}"

    @property
    def is_matters_arising(self) -> bool:
        return self.agenda_item_id is None

    @property
    def is_closeable_by_assignee(self) -> bool:
        return self.status in ('open', 'in_progress', 'overdue')

    @property
    def is_finally_closeable(self) -> bool:
        return self.status == 'closed' and not self.fully_closed


class Minutes(TimestampedModel, StatusMixin, WorkflowMixin):
    """Official written record of a meeting's proceedings."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
    ]

    meeting = models.OneToOneField(
        Meeting, on_delete=models.CASCADE, related_name='minutes',
    )
    title = models.CharField(max_length=500)
    content = models.TextField()
    attachments = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    approved_by = models.JSONField(default=list, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'legal_minutes'
        ordering = ['-created_at']
        verbose_name = 'Minutes'
        verbose_name_plural = 'Minutes'

    def __str__(self):
        return f"Minutes — {self.title} ({self.get_status_display()})"

    def get_workflow_context(self) -> dict:
        return {
            'minutes_id': str(self.id),
            'meeting_id': str(self.meeting_id),
            'meeting_ref': self.meeting.meeting_number,
            'meeting_title': self.meeting.title,
            'secretary_id': str(self.created_by),
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'minutes',
            'entity_id': str(self.id),
            'meeting_ref': self.meeting.meeting_number,
            'meeting_title': self.meeting.title,
            'status': self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'minutes')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='minutes',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class Resolution(TimestampedModel, StatusMixin):
    """Formal decision adopted during a meeting for a specific agenda item."""

    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('noted', 'Noted'),
    ]

    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name='resolutions',
    )
    agenda_item = models.OneToOneField(
        MeetingAgenda, on_delete=models.CASCADE, related_name='resolution',
    )
    resolution_text = models.TextField()
    date_adopted = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    responsible_person_id = models.UUIDField(null=True, blank=True, db_index=True)
    effective_date = models.DateField(null=True, blank=True)
    attachments = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'legal_resolution'
        ordering = ['meeting', 'date_adopted']

    def __str__(self):
        return f"Resolution [{self.get_status_display()}] — {self.meeting_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 4 — Litigation (FCC Sued)
# ═══════════════════════════════════════════════════════════════════════════════

class CaseDefendant(TimestampedModel, StatusMixin, WorkflowMixin):
    """Legal case where FCC has been sued by a plaintiff."""

    STATUS_CHOICES = [
        ('new', 'New'),
        ('under_dg_review', 'Under DG Review'),
        ('directive_issued', 'Directive Issued'),
        ('hearing_stage', 'Hearing Stage'),
        ('judgment_received', 'Judgment Received'),
        ('appeal_filed', 'Appeal Filed'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
    ]

    reference_number = models.CharField(max_length=50, db_index=True)
    court_case_number = models.CharField(max_length=100, blank=True)
    court_registry = models.CharField(max_length=255, blank=True)
    court_level = models.ForeignKey(
        CourtLevel, on_delete=models.PROTECT, related_name='defendant_cases',
    )
    service_date = models.DateField(null=True, blank=True)
    plaintiffs = models.JSONField(default=list, blank=True)
    plaintiff_advocate = models.CharField(max_length=255, blank=True)
    claim_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    nature_of_claim = models.TextField(blank=True)
    department_affected = models.CharField(max_length=255, blank=True)
    urgency_level = models.ForeignKey(
        LitigationUrgencyLevel, on_delete=models.PROTECT, related_name='defendant_cases',
    )
    risk_level = models.ForeignKey(
        LitigationRiskLevel, on_delete=models.PROTECT, null=True, blank=True, related_name='defendant_cases',
    )
    initiation_documents = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new', db_index=True)
    dg_review_status = models.CharField(
        max_length=30, blank=True, default='pending',
        help_text="Pending/Reviewed/Directive Issued",
    )
    assigned_legal_officer_ids = models.JSONField(default=list, blank=True)
    assigned_legal_manager_id = models.UUIDField(null=True, blank=True, db_index=True)
    next_hearing_date = models.DateField(null=True, blank=True)

    # ── Archiving (GAP-14) ───────────────────────────────────────────────────
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.UUIDField(null=True, blank=True)

    # ── Case Folder (SRS §4.11) ────────────────────────────────────────────
    case_folder_url = models.URLField(max_length=500, blank=True, help_text="URL to the DRS case folder")

    # ── On-hold (SIG-09) ────────────────────────────────────────────────────
    hold_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'legal_case_defendant'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reference_number'],
                condition=models.Q(is_active=True),
                name='legal_case_defendant_active_ref_uniq',
            )
        ]

    def __str__(self):
        return f"{self.reference_number} — Defendant Case"

    def get_workflow_context(self) -> dict:
        return {
            'case_defendant_id': str(self.id),
            'reference_number': self.reference_number,
            'court_level': str(self.court_level_id),
            'applicant_id': '',
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'case_defendant',
            'entity_id': str(self.id),
            'reference_number': self.reference_number,
            'status': self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'case_defendant')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='case_defendant',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class FilingDefendant(TimestampedModel, StatusMixin, WorkflowMixin):
    """A court document filed by FCC in its defence."""

    FILING_TYPE_CHOICES = [
        ('statement_of_defence', 'Statement of Defence'),
        ('affidavit', 'Affidavit'),
        ('application', 'Application'),
        ('chamber_summons', 'Chamber Summons'),
        ('bill_of_cost', 'Bill of Cost'),
        ('notice_of_appeal', 'Notice of Appeal'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('under_review_lm', 'Under Review (LM)'),
        ('approved_lm', 'Approved (LM)'),
        ('under_review_dg', 'Under Review (DG)'),
        ('approved', 'Approved'),
        ('filed', 'Filed'),
    ]

    case_defendant = models.ForeignKey(
        CaseDefendant, on_delete=models.CASCADE, related_name='filings',
    )
    filing_type = models.CharField(max_length=30, choices=FILING_TYPE_CHOICES)
    title = models.CharField(max_length=500)
    document_id = models.UUIDField(help_text="Document UUID from DRS")
    stamped_document_url = models.URLField(
        max_length=500, blank=True, null=True,
        help_text="URL to the stamped PDF served by DRS (GAP-10)",
    )
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True)
    submitted_by_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    approval_chain = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'legal_filing_defendant'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_filing_type_display()})"

    def get_workflow_context(self) -> dict:
        return {
            'filing_defendant_id': str(self.id),
            'case_defendant_id': str(self.case_defendant_id),
            'reference_number': self.case_defendant.reference_number,
            'applicant_id': '',
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'filing_defendant',
            'entity_id': str(self.id),
            'case_reference': self.case_defendant.reference_number,
            'filing_type': self.filing_type,
            'status': self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'filing_defendant')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='filing_defendant',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class ResponseDefendant(TimestampedModel, StatusMixin):
    """Documents received from the plaintiff during a defendant case."""

    RESPONSE_TYPE_CHOICES = [
        ('preliminary_objections', 'Preliminary Objections'),
        ('counter_claim', 'Counter Claim'),
        ('reply_to_defence', 'Reply to Defence'),
        ('response_to_ruling', 'Response to Ruling'),
        ('other', 'Other'),
    ]

    case_defendant = models.ForeignKey(
        CaseDefendant, on_delete=models.CASCADE, related_name='responses',
    )
    response_type = models.CharField(max_length=30, choices=RESPONSE_TYPE_CHOICES)
    received_date = models.DateField()
    document_id = models.UUIDField(help_text="Document UUID from DRS")
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'legal_response_defendant'
        ordering = ['-received_date']

    def __str__(self):
        return f"Response ({self.get_response_type_display()}) — {self.case_defendant_id}"


class Hearing(TimestampedModel, StatusMixin):
    """A scheduled court session. Shared between defendant and plaintiff cases."""

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('adjourned', 'Adjourned'),
        ('cancelled', 'Cancelled'),
    ]

    case_defendant = models.ForeignKey(
        CaseDefendant, on_delete=models.CASCADE, null=True, blank=True, related_name='hearings',
    )
    case_plaintiff = models.ForeignKey(
        'CasePlaintiff', on_delete=models.CASCADE, null=True, blank=True, related_name='hearings',
    )
    hearing_date = models.DateField()
    court = models.CharField(max_length=255, blank=True)
    judge = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', db_index=True)

    class Meta:
        db_table = 'legal_hearing'
        ordering = ['-hearing_date']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(case_defendant__isnull=False, case_plaintiff__isnull=True)
                    | models.Q(case_defendant__isnull=True, case_plaintiff__isnull=False)
                ),
                name='legal_hearing_exactly_one_case',
            )
        ]

    def __str__(self):
        return f"Hearing on {self.hearing_date}"


class HearingReport(TimestampedModel, StatusMixin):
    """Report of proceedings or outcome from a specific hearing."""

    REPORT_TYPE_CHOICES = [
        ('proceedings', 'Proceedings'),
        ('ruling', 'Ruling'),
        ('order', 'Order'),
    ]

    hearing = models.ForeignKey(
        Hearing, on_delete=models.CASCADE, related_name='reports',
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    summary = models.TextField()
    remarks = models.TextField(blank=True)
    next_hearing_date = models.DateField(null=True, blank=True)
    attachment_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'legal_hearing_report'
        ordering = ['-created_at']

    def __str__(self):
        return f"Report ({self.get_report_type_display()}) — Hearing {self.hearing_id}"


class SettlementDefendant(TimestampedModel, StatusMixin, WorkflowMixin):
    """Out-of-court settlement for a defendant case."""

    STATUS_CHOICES = [
        ('proposed', 'Proposed'),
        ('agreed', 'Agreed'),
        ('rejected', 'Rejected'),
    ]

    case_defendant = models.ForeignKey(
        CaseDefendant, on_delete=models.CASCADE, related_name='settlements',
    )
    settlement_date = models.DateField()
    terms = models.TextField()
    payment_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    agreement_document_id = models.UUIDField(help_text="Document UUID from DRS")
    stamped_document_url = models.URLField(
        max_length=500, blank=True, null=True,
        help_text="URL to the stamped PDF served by DRS (GAP-10)",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='proposed', db_index=True)

    class Meta:
        db_table = 'legal_settlement_defendant'
        ordering = ['-settlement_date']
        constraints = [
            models.UniqueConstraint(
                fields=['case_defendant'],
                condition=models.Q(is_active=True),
                name='legal_settlement_defendant_active_case_uniq',
            )
        ]

    def __str__(self):
        return f"Settlement — {self.case_defendant_id}"

    def get_workflow_context(self) -> dict:
        return {
            'settlement_defendant_id': str(self.id),
            'case_defendant_id': str(self.case_defendant_id),
            'reference_number': self.case_defendant.reference_number,
            'applicant_id': '',
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'settlement_defendant',
            'entity_id': str(self.id),
            'case_reference': self.case_defendant.reference_number,
            'status': self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'settlement_defendant')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='settlement_defendant',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class JudgmentDefendant(TimestampedModel, StatusMixin, WorkflowMixin):
    """Court's final judgment in a defendant case."""

    OUTCOME_CHOICES = [
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]
    DG_DECISION_CHOICES = [
        ('accept', 'Accept'),
        ('appeal', 'Appeal'),
    ]

    case_defendant = models.ForeignKey(
        CaseDefendant, on_delete=models.CASCADE, related_name='judgments',
    )
    judgment_date = models.DateField()
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    amount_awarded = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    legal_costs_awarded = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    other_costs = models.JSONField(default=list, blank=True)
    document_id = models.UUIDField(help_text="Judgment document UUID from DRS")
    stamped_document_url = models.URLField(
        max_length=500, blank=True, null=True,
        help_text="URL to the stamped PDF served by DRS (GAP-10)",
    )
    remarks = models.TextField(blank=True)
    dg_decision = models.CharField(
        max_length=10, choices=DG_DECISION_CHOICES, null=True, blank=True,
    )
    appeal_due_date = models.DateField(null=True, blank=True)
    appeal_filing = models.ForeignKey(
        FilingDefendant, on_delete=models.SET_NULL, null=True, blank=True, related_name='appeal_judgment',
    )
    appeal_task = models.ForeignKey(
        'TaskLitigation', on_delete=models.SET_NULL, null=True, blank=True, related_name='appeal_judgment_defendant',
    )

    class Meta:
        db_table = 'legal_judgment_defendant'
        ordering = ['-judgment_date']
        constraints = [
            models.UniqueConstraint(
                fields=['case_defendant'],
                condition=models.Q(is_active=True),
                name='legal_judgment_defendant_active_case_uniq',
            )
        ]

    def __str__(self):
        return f"Judgment ({self.get_outcome_display()}) — {self.case_defendant_id}"

    def get_workflow_context(self) -> dict:
        return {
            'judgment_defendant_id': str(self.id),
            'case_defendant_id': str(self.case_defendant_id),
            'reference_number': self.case_defendant.reference_number,
            'applicant_id': '',
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'judgment_defendant',
            'entity_id': str(self.id),
            'case_reference': self.case_defendant.reference_number,
            'outcome': self.outcome,
            'status': self.dg_decision or 'pending',
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'judgment_defendant')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='judgment_defendant',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class FinancialDefendant(TimestampedModel):
    """Financial tracking for a defendant case. Auto-created on case registration."""
    case_defendant = models.OneToOneField(
        CaseDefendant, on_delete=models.CASCADE, related_name='financial',
    )
    claim_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    legal_costs_incurred = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    costs_awarded = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    other_costs = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    recoveries = models.JSONField(default=list, blank=True)
    payments = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'legal_financial_defendant'

    def __str__(self):
        return f"Financials — {self.case_defendant_id}"


class LitigationDirective(TimestampedModel, StatusMixin):
    """A directive issued by the DG on a litigation case. Shared between defendant/plaintiff."""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending_dg_approval', 'Pending DG Approval'),
        ('closed', 'Closed'),
    ]

    case_defendant = models.ForeignKey(
        CaseDefendant, on_delete=models.CASCADE, null=True, blank=True, related_name='litigation_directives',
    )
    case_plaintiff = models.ForeignKey(
        'CasePlaintiff', on_delete=models.CASCADE, null=True, blank=True, related_name='litigation_directives',
    )
    issued_by_user_id = models.UUIDField(db_index=True)
    issue_date = models.DateField()
    instruction = models.TextField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    completion_summary = models.TextField(blank=True)
    completion_date = models.DateField(null=True, blank=True)
    attachments = models.JSONField(default=list, blank=True)

    # ── DG approval gate (SIG-03) ────────────────────────────────────────────
    requires_dg_approval_for_closure = models.BooleanField(
        default=False,
        help_text='When True, closure must pass through DG approval before being finalised.',
    )

    class Meta:
        db_table = 'legal_litigation_directive'
        ordering = ['-issue_date']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(case_defendant__isnull=False, case_plaintiff__isnull=True)
                    | models.Q(case_defendant__isnull=True, case_plaintiff__isnull=False)
                ),
                name='legal_litigation_directive_exactly_one_case',
            )
        ]

    def __str__(self):
        return f"Litigation Directive [{self.get_status_display()}] — {self.issue_date}"


class TaskLitigation(TimestampedModel, StatusMixin):
    """A deadline-driven task associated with a litigation case. Shared between defendant/plaintiff."""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('overdue', 'Overdue'),
        ('closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    case_defendant = models.ForeignKey(
        CaseDefendant, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks',
    )
    case_plaintiff = models.ForeignKey(
        'CasePlaintiff', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks',
    )
    title = models.CharField(max_length=500)
    assigned_to_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    related_entity_type = models.CharField(max_length=80, blank=True)
    related_entity_id = models.UUIDField(null=True, blank=True)

    # ── Auto-creation flag (MIN-03) ──────────────────────────────────────────
    auto_created = models.BooleanField(
        default=False,
        help_text='True when the task was created programmatically (e.g. appeal deadline, filing review).',
    )

    class Meta:
        db_table = 'legal_task_litigation'
        ordering = ['due_date']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(case_defendant__isnull=False, case_plaintiff__isnull=True)
                    | models.Q(case_defendant__isnull=True, case_plaintiff__isnull=False)
                ),
                name='legal_task_litigation_exactly_one_case',
            )
        ]

    def __str__(self):
        return f"Task [{self.get_status_display()}] — {self.title[:80]}"


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 5 — Litigation (FCC Suing)
# ═══════════════════════════════════════════════════════════════════════════════

class CasePlaintiff(TimestampedModel, StatusMixin, WorkflowMixin):
    """Legal case where FCC is the plaintiff, pursuing action against a respondent."""

    STATUS_CHOICES = [
        ('new', 'New'),
        ('under_dg_review', 'Under DG Review'),
        ('directive_issued', 'Directive Issued'),
        ('hearing_stage', 'Hearing Stage'),
        ('judgment_received', 'Judgment Received'),
        ('appeal_filed', 'Appeal Filed'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
    ]
    REGISTRATION_TYPE_CHOICES = [
        ('simplified', 'Breach Report Intake'),
        ('full', 'Full Breach Report'),
    ]

    reference_number = models.CharField(max_length=50, db_index=True)
    registration_type = models.CharField(max_length=20, choices=REGISTRATION_TYPE_CHOICES, default='full')
    reporting_department = models.CharField(max_length=255, blank=True)
    nature_of_breach = models.TextField(blank=True)
    respondent_name = models.CharField(max_length=500, blank=True)
    respondent_type = models.CharField(max_length=100, blank=True)
    estimated_claim_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    court_level = models.ForeignKey(
        CourtLevel, on_delete=models.PROTECT, null=True, blank=True, related_name='plaintiff_cases',
    )
    urgency_level = models.ForeignKey(
        LitigationUrgencyLevel, on_delete=models.PROTECT, null=True, blank=True, related_name='plaintiff_cases',
    )
    risk_level = models.ForeignKey(
        LitigationRiskLevel, on_delete=models.PROTECT, null=True, blank=True, related_name='plaintiff_cases',
    )
    initiation_documents = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new', db_index=True)
    dg_review_status = models.CharField(max_length=30, blank=True, default='pending')
    assigned_legal_officer_ids = models.JSONField(default=list, blank=True)
    assigned_legal_manager_id = models.UUIDField(null=True, blank=True, db_index=True)
    next_hearing_date = models.DateField(null=True, blank=True)

    # ── Archiving (GAP-14) ───────────────────────────────────────────────────
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.UUIDField(null=True, blank=True)

    # ── Case Folder (SRS §5.8) ────────────────────────────────────────────
    case_folder_url = models.URLField(max_length=500, blank=True, help_text="URL to the DRS case folder")

    # ── On-hold (SIG-09) ────────────────────────────────────────────────────
    hold_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'legal_case_plaintiff'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reference_number'],
                condition=models.Q(is_active=True),
                name='legal_case_plaintiff_active_ref_uniq',
            )
        ]

    def __str__(self):
        return f"{self.reference_number} — Plaintiff Case"

    def get_workflow_context(self) -> dict:
        return {
            'case_plaintiff_id': str(self.id),
            'reference_number': self.reference_number,
            'applicant_id': '',
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'case_plaintiff',
            'entity_id': str(self.id),
            'reference_number': self.reference_number,
            'status': self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'case_plaintiff')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='case_plaintiff',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class FilingPlaintiff(TimestampedModel, StatusMixin, WorkflowMixin):
    """Court documents filed by FCC in its capacity as plaintiff."""

    FILING_TYPE_CHOICES = [
        ('plaint', 'Plaint'),
        ('petition', 'Petition'),
        ('statement_of_claim', 'Statement of Claim'),
        ('application', 'Application'),
        ('chamber_summons', 'Chamber Summons'),
        ('affidavit', 'Affidavit'),
        ('bill_of_cost', 'Bill of Cost'),
        ('notice_of_appeal', 'Notice of Appeal'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('under_review_lm', 'Under Review (LM)'),
        ('approved_lm', 'Approved (LM)'),
        ('under_review_dg', 'Under Review (DG)'),
        ('approved', 'Approved'),
        ('filed', 'Filed'),
    ]

    case_plaintiff = models.ForeignKey(
        CasePlaintiff, on_delete=models.CASCADE, related_name='filings',
    )
    filing_type = models.CharField(max_length=30, choices=FILING_TYPE_CHOICES)
    title = models.CharField(max_length=500)
    document_id = models.UUIDField(help_text="Document UUID from DRS")
    stamped_document_url = models.URLField(
        max_length=500, blank=True, null=True,
        help_text="URL to the stamped PDF served by DRS (GAP-10)",
    )
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True)
    submitted_by_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    approval_chain = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'legal_filing_plaintiff'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_filing_type_display()})"

    def get_workflow_context(self) -> dict:
        return {
            'filing_plaintiff_id': str(self.id),
            'case_plaintiff_id': str(self.case_plaintiff_id),
            'reference_number': self.case_plaintiff.reference_number,
            'applicant_id': '',
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'filing_plaintiff',
            'entity_id': str(self.id),
            'case_reference': self.case_plaintiff.reference_number,
            'filing_type': self.filing_type,
            'status': self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'filing_plaintiff')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='filing_plaintiff',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class ResponsePlaintiff(TimestampedModel, StatusMixin):
    """Documents received from the respondent in a plaintiff case."""

    RESPONSE_TYPE_CHOICES = [
        ('preliminary_objections', 'Preliminary Objections'),
        ('response_to_ruling', 'Response to Ruling'),
        ('response_to_orders', 'Response to Orders'),
        ('response_to_affidavits', 'Response to Affidavits'),
        ('counter_claim', 'Counter Claim'),
        ('initial_response', 'Initial Response'),
        ('other', 'Other'),
    ]

    case_plaintiff = models.ForeignKey(
        CasePlaintiff, on_delete=models.CASCADE, related_name='responses',
    )
    response_type = models.CharField(max_length=30, choices=RESPONSE_TYPE_CHOICES)
    received_date = models.DateField()
    document_id = models.UUIDField(help_text="Document UUID from DRS")
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'legal_response_plaintiff'
        ordering = ['-received_date']

    def __str__(self):
        return f"Response ({self.get_response_type_display()}) — {self.case_plaintiff_id}"


class SettlementPlaintiff(TimestampedModel, StatusMixin, WorkflowMixin):
    """Out-of-court settlement for a plaintiff case."""

    STATUS_CHOICES = [
        ('proposed', 'Proposed'),
        ('agreed', 'Agreed'),
        ('rejected', 'Rejected'),
    ]

    case_plaintiff = models.ForeignKey(
        CasePlaintiff, on_delete=models.CASCADE, related_name='settlements',
    )
    settlement_date = models.DateField()
    terms = models.TextField()
    payment_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    agreement_document_id = models.UUIDField(help_text="Document UUID from DRS")
    stamped_document_url = models.URLField(
        max_length=500, blank=True, null=True,
        help_text="URL to the stamped PDF served by DRS (GAP-10)",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='proposed', db_index=True)

    class Meta:
        db_table = 'legal_settlement_plaintiff'
        ordering = ['-settlement_date']
        constraints = [
            models.UniqueConstraint(
                fields=['case_plaintiff'],
                condition=models.Q(is_active=True),
                name='legal_settlement_plaintiff_active_case_uniq',
            )
        ]

    def __str__(self):
        return f"Settlement — {self.case_plaintiff_id}"

    def get_workflow_context(self) -> dict:
        return {
            'settlement_plaintiff_id': str(self.id),
            'case_plaintiff_id': str(self.case_plaintiff_id),
            'reference_number': self.case_plaintiff.reference_number,
            'applicant_id': '',
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'settlement_plaintiff',
            'entity_id': str(self.id),
            'case_reference': self.case_plaintiff.reference_number,
            'status': self.status,
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'settlement_plaintiff')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='settlement_plaintiff',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class JudgmentPlaintiff(TimestampedModel, StatusMixin, WorkflowMixin):
    """Court's final judgment in a plaintiff case."""

    OUTCOME_CHOICES = [
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]
    DG_DECISION_CHOICES = [
        ('accept', 'Accept'),
        ('appeal', 'Appeal'),
    ]

    case_plaintiff = models.ForeignKey(
        CasePlaintiff, on_delete=models.CASCADE, related_name='judgments',
    )
    judgment_date = models.DateField()
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    amount_awarded = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    legal_costs_awarded = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    other_costs = models.JSONField(default=list, blank=True)
    document_id = models.UUIDField(help_text="Judgment document UUID from DRS")
    stamped_document_url = models.URLField(
        max_length=500, blank=True, null=True,
        help_text="URL to the stamped PDF served by DRS (GAP-10)",
    )
    remarks = models.TextField(blank=True)
    dg_decision = models.CharField(
        max_length=10, choices=DG_DECISION_CHOICES, null=True, blank=True,
    )
    appeal_due_date = models.DateField(null=True, blank=True)
    appeal_filing = models.ForeignKey(
        FilingPlaintiff, on_delete=models.SET_NULL, null=True, blank=True, related_name='appeal_judgment',
    )
    appeal_task = models.ForeignKey(
        TaskLitigation, on_delete=models.SET_NULL, null=True, blank=True, related_name='appeal_judgment_plaintiff',
    )

    class Meta:
        db_table = 'legal_judgment_plaintiff'
        ordering = ['-judgment_date']
        constraints = [
            models.UniqueConstraint(
                fields=['case_plaintiff'],
                condition=models.Q(is_active=True),
                name='legal_judgment_plaintiff_active_case_uniq',
            )
        ]

    def __str__(self):
        return f"Judgment ({self.get_outcome_display()}) — {self.case_plaintiff_id}"

    def get_workflow_context(self) -> dict:
        return {
            'judgment_plaintiff_id': str(self.id),
            'case_plaintiff_id': str(self.case_plaintiff_id),
            'reference_number': self.case_plaintiff.reference_number,
            'applicant_id': '',
        }

    def get_workflow_metadata(self) -> dict:
        meta = {
            'entity_type': 'judgment_plaintiff',
            'entity_id': str(self.id),
            'case_reference': self.case_plaintiff.reference_number,
            'outcome': self.outcome,
            'status': self.dg_decision or 'pending',
        }
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        return add_entity_detail_path_to_metadata(meta, 'judgment_plaintiff')

    def log_workflow_action(self, action, actor_id, stage_name='', comment='', metadata=None, ip_address=None, previous_status='', new_status=''):
        LegalAuditLog.objects.create(
            entity_type='judgment_plaintiff',
            entity_id=self.id,
            action=action,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            stage_name=stage_name,
            comment=comment or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )


class FinancialPlaintiff(TimestampedModel):
    """Financial tracking for a plaintiff case. Auto-created on case registration."""
    case_plaintiff = models.OneToOneField(
        CasePlaintiff, on_delete=models.CASCADE, related_name='financial',
    )
    claim_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    legal_costs_incurred = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    amount_awarded = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    costs_awarded = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    other_costs = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    recovered_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    recoveries = models.JSONField(default=list, blank=True)
    payments = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'legal_financial_plaintiff'

    def __str__(self):
        return f"Financials — {self.case_plaintiff_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 6 — Public Register
# ═══════════════════════════════════════════════════════════════════════════════

class PublicDecision(TimestampedModel, StatusMixin):
    """An official public-facing record of a commission decision."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    title = models.CharField(max_length=500)
    meeting = models.ForeignKey(
        Meeting, on_delete=models.PROTECT, null=True, blank=True, related_name='public_decisions',
    )
    body_text = models.TextField()
    decision_text = models.TextField()
    decision_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    published_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'legal_public_decision'
        ordering = ['-decision_date']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-cutting — Audit Log
# ═══════════════════════════════════════════════════════════════════════════════

class LegalAuditLog(BaseModel):
    """Immutable domain-level audit trail for all Legal module state transitions."""
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    action = models.CharField(max_length=100)
    actor_id = models.UUIDField(db_index=True)
    previous_status = models.CharField(max_length=50, blank=True)
    new_status = models.CharField(max_length=50, blank=True)
    stage_name = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'legal_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['actor_id', 'created_at']),
            models.Index(fields=['entity_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.entity_type}/{self.entity_id} — {self.action} at {self.created_at}"


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 7 — Appeals (auto-created on final Judgment)
# ═══════════════════════════════════════════════════════════════════════════════

class AppealDefendant(TimestampedModel, StatusMixin):
    """Appeal record linked to a defendant judgment. Created atomically when DG decides to appeal."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('dismissed', 'Dismissed'),
        ('upheld', 'Upheld'),
        ('withdrawn', 'Withdrawn'),
    ]

    judgment = models.OneToOneField(
        JudgmentDefendant, on_delete=models.CASCADE, related_name='appeal',
    )
    appeal_date = models.DateField()
    grounds = models.TextField(help_text="Legal grounds for the appeal")
    court_level = models.ForeignKey(
        CourtLevel, on_delete=models.PROTECT, null=True, blank=True, related_name='appeals_defendant',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    outcome = models.TextField(blank=True)
    outcome_date = models.DateField(null=True, blank=True)
    document_id = models.UUIDField(null=True, blank=True, help_text="Appeal document UUID from DRS")
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = 'legal_appeal_defendant'
        ordering = ['-appeal_date']

    def __str__(self):
        return f"Appeal ({self.get_status_display()}) — Judgment {self.judgment_id}"


class AppealPlaintiff(TimestampedModel, StatusMixin):
    """Appeal record linked to a plaintiff judgment. Created atomically when DG decides to appeal."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('dismissed', 'Dismissed'),
        ('upheld', 'Upheld'),
        ('withdrawn', 'Withdrawn'),
    ]

    judgment = models.OneToOneField(
        JudgmentPlaintiff, on_delete=models.CASCADE, related_name='appeal',
    )
    appeal_date = models.DateField()
    grounds = models.TextField(help_text="Legal grounds for the appeal")
    court_level = models.ForeignKey(
        CourtLevel, on_delete=models.PROTECT, null=True, blank=True, related_name='appeals_plaintiff',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    outcome = models.TextField(blank=True)
    outcome_date = models.DateField(null=True, blank=True)
    document_id = models.UUIDField(null=True, blank=True, help_text="Appeal document UUID from DRS")
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = 'legal_appeal_plaintiff'
        ordering = ['-appeal_date']

    def __str__(self):
        return f"Appeal ({self.get_status_display()}) — Judgment {self.judgment_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# Domain 8 — Legal Notices (standalone, no workflow)
# ═══════════════════════════════════════════════════════════════════════════════

class LegalNotice(TimestampedModel, StatusMixin):
    """Standalone legal notice, optionally related to a litigation case."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('acknowledged', 'Acknowledged'),
        ('expired', 'Expired'),
    ]

    related_case_defendant = models.ForeignKey(
        CaseDefendant, on_delete=models.SET_NULL, null=True, blank=True, related_name='legal_notices',
    )
    related_case_plaintiff = models.ForeignKey(
        CasePlaintiff, on_delete=models.SET_NULL, null=True, blank=True, related_name='legal_notices',
    )
    notice_type = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    content = models.TextField()
    issued_date = models.DateField()
    served_date = models.DateField(null=True, blank=True)
    recipient_info = models.JSONField(default=dict, blank=True, help_text="Recipient details")
    document_id = models.UUIDField(null=True, blank=True, help_text="Notice document UUID from DRS")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)

    class Meta:
        db_table = 'legal_notice'
        ordering = ['-issued_date']

    def __str__(self):
        return f"Notice: {self.title[:80]} ({self.get_status_display()})"
