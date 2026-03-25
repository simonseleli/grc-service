"""
Risk Management business entity models for GRC Service.
Module: Risk Management and Quality Assurance (RMQAU)
Contains all 26 business models across 8 groups.
Lookup models (RiskCategory, RiskLikelihood, etc.) live in lookups.py.
"""
import uuid
from django.db import models
from django.utils import timezone
from .base import TimestampedModel, StatusMixin, WorkflowMixin


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — QA Training Management [GAP-02]
# (Defined first because QualityAuditor has FK to QATrainingSession)
# ══════════════════════════════════════════════════════════════════════════════

class QATrainingSession(TimestampedModel, StatusMixin):
    """
    ISO 9001:2015 training session organized before QA examination.
    SRS §1.9.8 Steps 2–5.
    """
    title = models.CharField(max_length=255)
    trainer_name = models.CharField(max_length=255)
    trainer_organization = models.CharField(max_length=255, blank=True)
    training_date = models.DateField()
    training_time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=255, blank=True)
    APPROVAL_STATUS_CHOICES = [
        ('proposed', 'Proposed'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_STATUS_CHOICES, default='proposed', db_index=True
    )
    approved_by = models.UUIDField(
        null=True, blank=True, help_text="RMQAM user_id who approved this session"
    )
    approval_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    rejection_notes = models.TextField(blank=True, help_text="GAP-23: Reason for rejecting the training session")

    class Meta:
        db_table = 'grc_risk_qa_training_session'
        ordering = ['-training_date']

    def __str__(self):
        return f"QA Training: {self.title} ({self.training_date})"


class QATrainingAttendee(TimestampedModel, StatusMixin):
    """
    Attendance record linking a QualityAuditor to a QATrainingSession.
    """
    training_session = models.ForeignKey(
        QATrainingSession, on_delete=models.CASCADE, related_name='attendees'
    )
    quality_auditor = models.ForeignKey(
        'QualityAuditor', on_delete=models.CASCADE, related_name='training_records'
    )
    attended = models.BooleanField(default=False)
    # GAP-3: Per-session exam tracking
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    exam_attempt_number = models.IntegerField(null=True, blank=True)
    exam_date = models.DateField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_qa_training_attendee'
        unique_together = [['training_session', 'quality_auditor']]

    def __str__(self):
        return f"Attendee {self.quality_auditor_id} – {self.training_session}"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — Risk Champion & QA Appointment
# ══════════════════════════════════════════════════════════════════════════════

class RiskChampion(TimestampedModel, StatusMixin):
    """
    Appointed Risk Champion — one active per Directorate/Unit/Zone.
    Business Rule E.1/E.11.
    """
    ORG_UNIT_TYPE_CHOICES = [
        ('directorate', 'Directorate'),
        ('unit', 'Unit'),
        ('zone', 'Zone'),
    ]
    org_unit_id = models.UUIDField(
        db_index=True, help_text="Directorate / Unit / Zone UUID from Corporate Service"
    )
    org_unit_type = models.CharField(max_length=50, choices=ORG_UNIT_TYPE_CHOICES)
    user_id = models.UUIDField(db_index=True, help_text="IAM user UUID of the Risk Champion")
    nominated_by = models.UUIDField(help_text="Head who nominated this RC (IAM user UUID)")
    term_start = models.DateField()
    term_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    # GAP-13: RC qualification fields
    qualifications = models.TextField(blank=True)
    experience_summary = models.TextField(blank=True)
    justification = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_risk_champion'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['org_unit_id', 'org_unit_type'],
                condition=models.Q(is_active=True),
                name='unique_active_rc_per_org_unit',
            )
        ]

    def __str__(self):
        return f"RC {self.user_id} – {self.org_unit_type}:{self.org_unit_id}"


class RiskChampionAppointment(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Appointment letter workflow record for a Risk Champion.
    DRS dual-reference pattern for document storage.
    """
    risk_champion = models.ForeignKey(
        RiskChampion, on_delete=models.CASCADE, related_name='appointments'
    )
    appointment_date = models.DateField()
    # DRS dual-reference
    document_id = models.UUIDField(
        null=True, blank=True, help_text="Document UUID in Document Records Service"
    )
    stamped_document_url = models.URLField(
        blank=True, default='', help_text="Signed/stamped letter URL from DRS"
    )
    remarks = models.TextField(blank=True)
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_SIGNED = 'signed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_SIGNED, 'Signed'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    # GAP-06: Dispatch tracking
    dispatched = models.BooleanField(default=False)
    dispatch_date = models.DateField(null=True, blank=True)
    dispatch_reference = models.CharField(max_length=100, blank=True)
    recipient_confirmed = models.BooleanField(default=False)
    recipient_confirmed_date = models.DateField(null=True, blank=True)
    # GAP-14: Rework counter
    rework_count = models.IntegerField(default=0)
    # GAP-17: Review comments
    last_review_comment = models.TextField(blank=True)
    last_reviewed_by = models.UUIDField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_champion_appointment'
        ordering = ['-created_at']

    def __str__(self):
        return f"Appointment for RC {self.risk_champion_id} ({self.status})"

    def get_workflow_context(self) -> dict:
        return {
            'entity_type': 'risk_champion_appointment',
            'entity_id': str(self.id),
            'risk_champion_id': str(self.risk_champion_id),
            'org_unit_id': str(self.risk_champion.org_unit_id),
            'org_unit_type': self.risk_champion.org_unit_type,
        }

    def get_workflow_metadata(self) -> dict:
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {
            'entity_type': 'risk_champion_appointment',
            'entity_id': str(self.id),
            'status': self.status,
            'appointment_date': str(self.appointment_date),
        }
        return add_entity_detail_path_to_metadata(meta, 'risk_champion_appointment')


class QualityAuditor(TimestampedModel, StatusMixin):
    """
    Quality Auditor — certified internal QMS auditor.
    Business Rule E.3: ≥75% exam score, max 2 attempts.
    """
    ORG_UNIT_TYPE_CHOICES = [
        ('directorate', 'Directorate'),
        ('unit', 'Unit'),
        ('zone', 'Zone'),
    ]
    user_id = models.UUIDField(db_index=True, help_text="IAM user UUID of the Quality Auditor")
    nominated_by = models.UUIDField(help_text="Head who nominated this QA (IAM user UUID)")
    org_unit_id = models.UUIDField(db_index=True, help_text="QA's home unit UUID")
    org_unit_type = models.CharField(max_length=50, choices=ORG_UNIT_TYPE_CHOICES)
    # Certification
    exam_attempt = models.IntegerField(default=0, help_text="Number of exam attempts (max 2 per Rule E.3)")
    exam_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Latest exam score as percentage"
    )
    is_certified = models.BooleanField(default=False, db_index=True)
    certification_date = models.DateField(null=True, blank=True)
    term_start = models.DateField(null=True, blank=True)
    term_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    # GAP-10: Qualifications / experience (mirrors RiskChampion)
    qualifications = models.TextField(blank=True)
    experience_summary = models.TextField(blank=True)
    # GAP-02: Link to training session
    training_session = models.ForeignKey(
        QATrainingSession, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='auditors', help_text="Completed training before examination"
    )
    # SRS-FIX G-08: Nomination status for replacement tracking
    NOMINATION_STATUS_ACTIVE = 'active'
    NOMINATION_STATUS_REPLACEMENT_NEEDED = 'replacement_needed'
    NOMINATION_STATUS_REPLACED = 'replaced'
    NOMINATION_STATUS_CHOICES = [
        (NOMINATION_STATUS_ACTIVE, 'Active'),
        (NOMINATION_STATUS_REPLACEMENT_NEEDED, 'Replacement Needed'),
        (NOMINATION_STATUS_REPLACED, 'Replaced'),
    ]
    nomination_status = models.CharField(
        max_length=30, choices=NOMINATION_STATUS_CHOICES,
        default=NOMINATION_STATUS_ACTIVE, db_index=True,
    )

    class Meta:
        db_table = 'grc_risk_quality_auditor'
        ordering = ['-created_at']

    def __str__(self):
        return f"QA {self.user_id} – certified={self.is_certified}"


class QualityAuditorAppointment(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Appointment letter workflow for a Quality Auditor.
    Mirrors RiskChampionAppointment structure.
    """
    quality_auditor = models.ForeignKey(
        QualityAuditor, on_delete=models.CASCADE, related_name='appointments'
    )
    appointment_date = models.DateField()
    # DRS dual-reference
    document_id = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    remarks = models.TextField(blank=True)
    STATUS_CHOICES = RiskChampionAppointment.STATUS_CHOICES
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True
    )
    # GAP-06: Dispatch tracking
    dispatched = models.BooleanField(default=False)
    dispatch_date = models.DateField(null=True, blank=True)
    dispatch_reference = models.CharField(max_length=100, blank=True)
    recipient_confirmed = models.BooleanField(default=False)
    recipient_confirmed_date = models.DateField(null=True, blank=True)
    # GAP-14: Rework counter
    rework_count = models.IntegerField(default=0)
    # GAP-17: Review comments
    last_review_comment = models.TextField(blank=True)
    last_reviewed_by = models.UUIDField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_qa_appointment'
        ordering = ['-created_at']

    def __str__(self):
        return f"Appointment for QA {self.quality_auditor_id} ({self.status})"

    def get_workflow_context(self) -> dict:
        return {
            'entity_type': 'quality_auditor_appointment',
            'entity_id': str(self.id),
            'quality_auditor_id': str(self.quality_auditor_id),
            'org_unit_id': str(self.quality_auditor.org_unit_id),
            'org_unit_type': self.quality_auditor.org_unit_type,
        }

    def get_workflow_metadata(self) -> dict:
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {
            'entity_type': 'quality_auditor_appointment',
            'entity_id': str(self.id),
            'status': self.status,
            'appointment_date': str(self.appointment_date),
        }
        return add_entity_detail_path_to_metadata(meta, 'quality_auditor_appointment')


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — Risk Assessment & Departmental Register
# ══════════════════════════════════════════════════════════════════════════════

class RiskAssessmentSheet(TimestampedModel, StatusMixin):
    """
    One identified risk per Risk Champion per assessment cycle.
    inherent_risk_score auto-computed on save() as likelihood × impact.
    """
    risk_champion = models.ForeignKey(
        RiskChampion, on_delete=models.PROTECT, related_name='risk_sheets'
    )
    org_unit_id = models.UUIDField(db_index=True)
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, related_name='risk_sheets'
    )
    # Risk identification
    risk_category = models.ForeignKey(
        'RiskCategory', on_delete=models.PROTECT, related_name='risk_sheets'
    )
    risk_sector = models.ForeignKey(
        'RiskSector', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='risk_sheets'
    )
    strategic_objective = models.ForeignKey(
        'StrategicObjective', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='risk_sheets'
    )
    risk_title = models.CharField(max_length=255)
    risk_description = models.TextField()
    causes = models.TextField(blank=True, help_text="Root causes of the risk")
    consequences = models.TextField(blank=True, help_text="Consequences if risk materialises")
    risk_indicator = models.CharField(max_length=255, blank=True, help_text="Key risk indicator")
    risk_owner = models.UUIDField(help_text="IAM user UUID of the Risk Owner")
    supporting_owners = models.JSONField(
        default=list, help_text="List of supporting risk owner IAM user UUIDs"
    )
    # Scoring inputs (lookup FK)
    likelihood = models.ForeignKey('RiskLikelihood', on_delete=models.PROTECT)
    impact = models.ForeignKey('RiskImpact', on_delete=models.PROTECT)
    # Computed inherent score
    inherent_risk_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    inherent_risk_level = models.ForeignKey(
        'RiskLevel', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inherent_sheets'
    )
    # Controls & residual
    existing_controls = models.TextField(blank=True)
    residual_likelihood = models.ForeignKey(
        'RiskLikelihood', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='residual_sheets'
    )
    residual_impact = models.ForeignKey(
        'RiskImpact', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='residual_impact_sheets'
    )
    residual_risk_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    residual_risk_level = models.ForeignKey(
        'RiskLevel', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='residual_sheets'
    )
    control_assessment = models.TextField(blank=True)
    further_action = models.TextField(blank=True)
    # GAP-07: Historical data cross-references
    references = models.JSONField(
        default=list,
        help_text='[{"type": "audit_finding|previous_risk|lesson_learned|external_report", "id": "uuid_or_null", "title": "...", "url": "..."}]'
    )
    # GAP-15/28: Status workflow (Phase 1 fix)
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED_TO_HEAD = 'submitted_to_head'
    STATUS_HEAD_ENDORSED = 'head_endorsed'
    STATUS_SUBMITTED_TO_RMQAM = 'submitted_to_rmqam'
    STATUS_APPROVED = 'approved'
    STATUS_RETURNED_FOR_REWORK = 'returned_for_rework'
    RAS_STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED_TO_HEAD, 'Submitted to Head'),
        (STATUS_HEAD_ENDORSED, 'Head Endorsed'),
        (STATUS_SUBMITTED_TO_RMQAM, 'Submitted to RMQAM'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_RETURNED_FOR_REWORK, 'Returned for Rework'),
    ]
    status = models.CharField(
        max_length=30, choices=RAS_STATUS_CHOICES,
        default=STATUS_DRAFT, db_index=True,
    )
    review_comments = models.TextField(blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    resubmitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_assessment_sheet'
        ordering = ['-created_at']

    def __str__(self):
        return f"Risk: {self.risk_title} (Score: {self.inherent_risk_score})"

    def save(self, *args, **kwargs):
        """Auto-compute inherent and residual risk scores."""
        if self.likelihood_id and self.impact_id:
            self.inherent_risk_score = (
                self.likelihood.numerical_value * self.impact.numerical_value
            )
            from .lookups import RiskLevel
            self.inherent_risk_level = RiskLevel.objects.filter(
                min_score__lte=self.inherent_risk_score,
                max_score__gte=self.inherent_risk_score,
                is_active=True,
            ).first()
        if self.residual_likelihood_id and self.residual_impact_id:
            self.residual_risk_score = (
                self.residual_likelihood.numerical_value * self.residual_impact.numerical_value
            )
            from .lookups import RiskLevel
            self.residual_risk_level = RiskLevel.objects.filter(
                min_score__lte=self.residual_risk_score,
                max_score__gte=self.residual_risk_score,
                is_active=True,
            ).first()
        super().save(*args, **kwargs)


class DepartmentalRiskRegister(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Consolidated Risk Register per Directorate/Unit/Zone per fiscal year.
    """
    ORG_UNIT_TYPE_CHOICES = [
        ('directorate', 'Directorate'),
        ('unit', 'Unit'),
        ('zone', 'Zone'),
    ]
    org_unit_id = models.UUIDField(db_index=True)
    org_unit_type = models.CharField(max_length=50, choices=ORG_UNIT_TYPE_CHOICES)
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, related_name='dept_registers'
    )
    submitted_by = models.UUIDField(
        null=True, blank=True, help_text="RC UUID who submitted this register"
    )
    submission_date = models.DateField(null=True, blank=True)
    rmqam_reviewer = models.UUIDField(
        null=True, blank=True, help_text="RMQAM UUID who reviewed"
    )
    review_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True
    )
    # GAP-18: Endorsement confirmation
    endorsed_by = models.UUIDField(null=True, blank=True)
    endorsement_date = models.DateField(null=True, blank=True)
    endorsement_document_id = models.UUIDField(
        null=True, blank=True, help_text="DRS reference for endorsement evidence"
    )
    # GAP-14: Rework counter
    rework_count = models.IntegerField(default=0)
    # GAP-17: Review comments
    last_review_comment = models.TextField(blank=True)
    last_reviewed_by = models.UUIDField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_dept_register'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['org_unit_id', 'fiscal_year'],
                condition=models.Q(is_active=True),
                name='unique_active_dept_register_per_unit_year',
            )
        ]

    def __str__(self):
        return f"Dept Register {self.org_unit_type}:{self.org_unit_id} – FY {self.fiscal_year_id}"

    def get_workflow_context(self) -> dict:
        return {
            'entity_type': 'departmental_risk_register',
            'entity_id': str(self.id),
            'org_unit_id': str(self.org_unit_id),
            'org_unit_type': self.org_unit_type,
            'fiscal_year_id': str(self.fiscal_year_id),
        }

    def get_workflow_metadata(self) -> dict:
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {
            'entity_type': 'departmental_risk_register',
            'entity_id': str(self.id),
            'status': self.status,
            'org_unit_type': self.org_unit_type,
        }
        return add_entity_detail_path_to_metadata(meta, 'departmental_risk_register')


class DeptRegisterEntry(TimestampedModel, StatusMixin):
    """
    Association between DepartmentalRiskRegister and RiskAssessmentSheet.
    """
    dept_register = models.ForeignKey(
        DepartmentalRiskRegister, on_delete=models.CASCADE, related_name='entries'
    )
    risk_sheet = models.ForeignKey(
        RiskAssessmentSheet, on_delete=models.PROTECT, related_name='register_entries'
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_dept_register_entry'
        ordering = ['sort_order']
        unique_together = [['dept_register', 'risk_sheet']]

    def __str__(self):
        return f"Entry #{self.sort_order} in {self.dept_register_id}"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — Institutional Register & RTAP
# ══════════════════════════════════════════════════════════════════════════════

class InstitutionalRiskRegister(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Organisation-wide risk register. One active per fiscal year (Rule E.11).
    4-stage approval: RMQAM → Management → Committee → Commission.
    """
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, related_name='institutional_registers'
    )
    prepared_by = models.UUIDField(help_text="RMQAM UUID who compiled this register")
    preparation_date = models.DateField(null=True, blank=True)
    # DRS dual-reference
    document_id = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    remarks = models.TextField(blank=True)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('rmqam_review', 'RMQAM Review'),
        ('management_review', 'Management Review'),
        ('committee_review', 'Committee Review'),
        ('commission_review', 'Commission Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True
    )
    # GAP-03: Committee meeting and LSM submission tracking
    committee_meeting_date = models.DateField(null=True, blank=True)
    lsm_submission_date = models.DateField(null=True, blank=True)
    # GAP-14: Rework counter
    rework_count = models.IntegerField(default=0)
    # GAP-17: Review comments
    last_review_comment = models.TextField(blank=True)
    last_reviewed_by = models.UUIDField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    # GAP-8: IRR Workshop notification fields
    workshop_date = models.DateField(null=True, blank=True)
    workshop_venue = models.CharField(max_length=255, blank=True)
    directors_notified_at = models.DateTimeField(null=True, blank=True)
    rcs_notified_at = models.DateTimeField(null=True, blank=True)
    # GAP-24: Distribution tracking
    distributed_to_directorates_at = models.DateTimeField(null=True, blank=True)
    distribution_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'grc_risk_inst_register'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['fiscal_year'],
                condition=models.Q(is_active=True),
                name='unique_active_irr_per_fiscal_year',
            )
        ]

    def __str__(self):
        return f"IRR – FY {self.fiscal_year_id} ({self.status})"

    def clean(self):
        """SRS-FIX G-04: Validate LSM submission ≥7 days before Committee meeting."""
        from django.core.exceptions import ValidationError
        super().clean()
        if self.lsm_submission_date and self.committee_meeting_date:
            if (self.committee_meeting_date - self.lsm_submission_date).days < 7:
                raise ValidationError(
                    "LSM must receive documents at least 7 days before the Committee meeting."
                )

    def get_workflow_context(self) -> dict:
        return {
            'entity_type': 'institutional_risk_register',
            'entity_id': str(self.id),
            'fiscal_year_id': str(self.fiscal_year_id),
            'prepared_by': str(self.prepared_by),
        }

    def get_workflow_metadata(self) -> dict:
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {
            'entity_type': 'institutional_risk_register',
            'entity_id': str(self.id),
            'status': self.status,
        }
        return add_entity_detail_path_to_metadata(meta, 'institutional_risk_register')


class InstitutionalRiskEntry(TimestampedModel, StatusMixin):
    """
    Single risk entry in the IRR — sourced from approved DeptRegisterEntries
    that meet the risk threshold (Rule E.4).
    """
    inst_register = models.ForeignKey(
        InstitutionalRiskRegister, on_delete=models.CASCADE, related_name='entries'
    )
    risk_sheet = models.ForeignKey(
        RiskAssessmentSheet, on_delete=models.PROTECT, related_name='inst_register_entries'
    )
    risk_ranking = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'grc_risk_inst_register_entry'
        ordering = ['risk_ranking']
        unique_together = [['inst_register', 'risk_sheet']]

    def __str__(self):
        return f"IRR Entry #{self.risk_ranking} – {self.risk_sheet.risk_title}"


class RiskTreatmentActionPlan(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Risk Treatment Action Plan. 1:1 with InstitutionalRiskRegister.
    One active RTAP per year (Rule E.11). Same 4-stage approval chain as IRR.
    """
    inst_register = models.OneToOneField(
        InstitutionalRiskRegister, on_delete=models.PROTECT, related_name='rtap'
    )
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, related_name='rtaps'
    )
    prepared_by = models.UUIDField(help_text="RMQAM UUID who prepared the RTAP")
    # DRS dual-reference
    document_id = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    remarks = models.TextField(blank=True)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('rmqam_review', 'RMQAM Review'),
        ('management_review', 'Management Review'),
        ('committee_review', 'Committee Review'),
        ('commission_review', 'Commission Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True
    )
    overall_progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Computed percentage of completed RTAP items"
    )
    # GAP-03: Committee meeting and LSM submission tracking
    committee_meeting_date = models.DateField(null=True, blank=True)
    lsm_submission_date = models.DateField(null=True, blank=True)
    # GAP-14: Rework counter
    rework_count = models.IntegerField(default=0)
    # GAP-17: Review comments
    last_review_comment = models.TextField(blank=True)
    last_reviewed_by = models.UUIDField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    # GAP-24: Distribution tracking
    distributed_to_directorates_at = models.DateTimeField(null=True, blank=True)
    distribution_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'grc_risk_rtap'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['fiscal_year'],
                condition=models.Q(is_active=True),
                name='unique_active_rtap_per_fiscal_year',
            )
        ]

    def __str__(self):
        return f"RTAP – FY {self.fiscal_year_id} ({self.status})"

    def clean(self):
        """SRS-FIX G-04: Validate LSM submission ≥7 days before Committee meeting."""
        from django.core.exceptions import ValidationError
        super().clean()
        if self.lsm_submission_date and self.committee_meeting_date:
            if (self.committee_meeting_date - self.lsm_submission_date).days < 7:
                raise ValidationError(
                    "LSM must receive documents at least 7 days before the Committee meeting."
                )

    def get_workflow_context(self) -> dict:
        return {
            'entity_type': 'risk_treatment_action_plan',
            'entity_id': str(self.id),
            'fiscal_year_id': str(self.fiscal_year_id),
            'prepared_by': str(self.prepared_by),
        }

    def get_workflow_metadata(self) -> dict:
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {
            'entity_type': 'risk_treatment_action_plan',
            'entity_id': str(self.id),
            'status': self.status,
            'overall_progress': str(self.overall_progress),
        }
        return add_entity_detail_path_to_metadata(meta, 'risk_treatment_action_plan')


class RTAPItem(TimestampedModel, StatusMixin):
    """
    One treatment control per risk entry in the RTAP.
    Status: not_started / in_progress / completed (Rule E.10).
    """
    rtap = models.ForeignKey(
        RiskTreatmentActionPlan, on_delete=models.CASCADE, related_name='items'
    )
    inst_entry = models.ForeignKey(
        InstitutionalRiskEntry, on_delete=models.PROTECT, related_name='rtap_items'
    )
    treatment_description = models.TextField()
    responsible_officer = models.UUIDField(help_text="IAM UUID of the responsible officer")
    target_date = models.DateField()
    kci = models.TextField(blank=True, help_text="Key Control Indicator")
    EFFECTIVENESS_CHOICES = [
        ('effective', 'Effective'),
        ('partially_effective', 'Partially Effective'),
        ('not_effective', 'Not Effective'),
    ]
    preventive_effectiveness = models.CharField(
        max_length=30, choices=EFFECTIVENESS_CHOICES, blank=True,
        help_text="Effectiveness of preventive controls"
    )
    preventive_rating = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Preventive control effectiveness rating %"
    )
    corrective_effectiveness = models.CharField(
        max_length=30, choices=EFFECTIVENESS_CHOICES, blank=True,
        help_text="Effectiveness of corrective controls"
    )
    corrective_rating = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Corrective control effectiveness rating %"
    )
    resources_required = models.TextField(blank=True, help_text="Resources required for treatment")
    STATUS_NOT_STARTED = 'not_started'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_RETURNED_FOR_REWORK = 'returned_for_rework'
    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, 'Not Started'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_RETURNED_FOR_REWORK, 'Returned for Rework'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_NOT_STARTED, db_index=True
    )
    sort_order = models.IntegerField(default=0)
    # GAP-22: Rework tracking
    review_comments = models.TextField(blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    resubmitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_rtap_item'
        ordering = ['sort_order']

    def __str__(self):
        return f"RTAP Item: {self.treatment_description[:50]} ({self.status})"


class RTAPQuarterlyUpdate(TimestampedModel, StatusMixin):
    """
    Quarterly implementation status update for a single RTAPItem.
    """
    rtap_item = models.ForeignKey(
        RTAPItem, on_delete=models.CASCADE, related_name='quarterly_updates'
    )
    quarter = models.ForeignKey(
        'core.Quarter', on_delete=models.PROTECT, related_name='rtap_updates'
    )
    reported_by = models.UUIDField(help_text="RC UUID who submitted this update")
    update_date = models.DateField()
    STATUS_CHOICES = RTAPItem.STATUS_CHOICES
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='not_started', db_index=True
    )
    progress_notes = models.TextField(blank=True)
    evidence = models.JSONField(
        default=list,
        help_text="[{'type': 'document|url', 'ref': '...', 'label': '...'}]"
    )

    class Meta:
        db_table = 'grc_risk_rtap_quarterly_update'
        ordering = ['quarter__fiscal_year', 'quarter__quarter_number']
        unique_together = [['rtap_item', 'quarter']]

    def __str__(self):
        return f"Update: RTAP Item {self.rtap_item_id} – Q{self.quarter_id}"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — Quarterly Reporting
# ══════════════════════════════════════════════════════════════════════════════

class QuarterlyPerformanceReport(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Quarterly Risk Management Implementation Report.
    5-stage approval: RMQAM → LSM → Management → Committee → Commission.
    """
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, related_name='risk_quarterly_reports'
    )
    quarter = models.ForeignKey(
        'core.Quarter', on_delete=models.PROTECT, related_name='risk_quarterly_reports'
    )
    prepared_by = models.UUIDField(help_text="RMQAM UUID who prepared this report")
    preparation_date = models.DateField(null=True, blank=True)
    # Snapshot metrics
    total_risks = models.IntegerField(default=0)
    high_risks = models.IntegerField(default=0)
    medium_risks = models.IntegerField(default=0)
    low_risks = models.IntegerField(default=0)
    rtap_completed = models.IntegerField(default=0)
    rtap_in_progress = models.IntegerField(default=0)
    rtap_not_started = models.IntegerField(default=0)
    report_body = models.TextField(blank=True)
    # DRS dual-reference
    document_id = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('rmqam_prepare', 'RMQAM Preparing'),
        ('lsm_submit', 'LSM Submission'),
        ('management_review', 'Management Review'),
        ('committee_review', 'Committee Review'),
        ('commission_submit', 'Commission Submission'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True
    )
    # GAP-03: Committee meeting and LSM submission tracking
    committee_meeting_date = models.DateField(null=True, blank=True)
    lsm_submission_date = models.DateField(null=True, blank=True)
    # GAP-12: IAGO tracking
    iago_submitted = models.BooleanField(default=False)
    iago_submission_date = models.DateField(null=True, blank=True)
    iago_reference = models.CharField(max_length=100, blank=True)
    # GAP-14: Rework counter
    rework_count = models.IntegerField(default=0)
    # GAP-17: Review comments
    last_review_comment = models.TextField(blank=True)
    last_reviewed_by = models.UUIDField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_quarterly_report'
        ordering = ['-fiscal_year__start_date', '-quarter__quarter_number']
        constraints = [
            models.UniqueConstraint(
                fields=['fiscal_year', 'quarter'],
                condition=models.Q(is_active=True),
                name='unique_active_quarterly_report_per_period',
            )
        ]

    def __str__(self):
        return f"QPR – FY {self.fiscal_year_id} Q{self.quarter_id} ({self.status})"

    def clean(self):
        """SRS-FIX G-05: Validate LSM submission ≥7 days before Committee meeting."""
        from django.core.exceptions import ValidationError
        super().clean()
        if self.lsm_submission_date and self.committee_meeting_date:
            if (self.committee_meeting_date - self.lsm_submission_date).days < 7:
                raise ValidationError(
                    "LSM must receive documents at least 7 days before the Committee meeting."
                )

    def snapshot_metrics(self):
        """
        SRS-FIX G-09: Auto-compute QPR snapshot fields from live RTAP/IRR data.
        Call before save() when transitioning to rmqam_prepare or beyond.
        """
        irr = InstitutionalRiskRegister.objects.filter(
            fiscal_year=self.fiscal_year, is_active=True
        ).first()
        if irr:
            entries = InstitutionalRiskEntry.objects.filter(
                inst_register=irr, is_active=True
            ).select_related('risk_sheet__residual_risk_level')
            self.total_risks = entries.count()
            self.high_risks = entries.filter(
                risk_sheet__residual_risk_level__code='high'
            ).count()
            self.medium_risks = entries.filter(
                risk_sheet__residual_risk_level__code='medium'
            ).count()
            self.low_risks = entries.filter(
                risk_sheet__residual_risk_level__code='low'
            ).count()

        rtap = RiskTreatmentActionPlan.objects.filter(
            fiscal_year=self.fiscal_year, is_active=True
        ).first()
        if rtap:
            items = RTAPItem.objects.filter(rtap=rtap, is_active=True)
            self.rtap_completed = items.filter(status='completed').count()
            self.rtap_in_progress = items.filter(status='in_progress').count()
            self.rtap_not_started = items.filter(status='not_started').count()

    def get_workflow_context(self) -> dict:
        return {
            'entity_type': 'quarterly_performance_report',
            'entity_id': str(self.id),
            'fiscal_year_id': str(self.fiscal_year_id),
            'quarter_id': str(self.quarter_id),
            'prepared_by': str(self.prepared_by),
        }

    def get_workflow_metadata(self) -> dict:
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {
            'entity_type': 'quarterly_performance_report',
            'entity_id': str(self.id),
            'status': self.status,
            'total_risks': self.total_risks,
        }
        return add_entity_detail_path_to_metadata(meta, 'quarterly_performance_report')


class ActivityReport(TimestampedModel, StatusMixin):
    """
    Quarterly RC activity report — submitted by the RC.
    """
    inst_register = models.ForeignKey(
        InstitutionalRiskRegister, on_delete=models.PROTECT, related_name='activity_reports'
    )
    quarter = models.ForeignKey(
        'core.Quarter', on_delete=models.PROTECT, related_name='activity_reports'
    )
    reported_by = models.UUIDField(help_text="RC UUID who submitted this report")
    submission_date = models.DateField()
    activities_summary = models.TextField()
    issues_raised = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    attachments = models.JSONField(
        default=list, help_text="[{'document_id': '...', 'title': '...'}]"
    )
    # SRS-FIX G-03: DG noting (FCC_SBP_RMQA_04 step 8)
    dg_noted = models.BooleanField(default=False)
    dg_noted_by = models.UUIDField(null=True, blank=True, help_text="DG user UUID who noted this report")
    dg_noted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_activity_report'
        ordering = ['-submission_date']
        unique_together = [['inst_register', 'quarter', 'reported_by']]

    def __str__(self):
        return f"Activity Report – {self.submission_date}"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — QMS Audit
# ══════════════════════════════════════════════════════════════════════════════

class QMSAuditProgram(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Annual QMS Audit Program — one active per fiscal year.
    """
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, related_name='qms_programs'
    )
    program_title = models.CharField(max_length=255)
    objective = models.TextField()
    scope = models.TextField()
    prepared_by = models.UUIDField(help_text="RMO/RMQAU UUID who prepared the program")
    approved_by = models.UUIDField(null=True, blank=True)
    approval_date = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True
    )

    class Meta:
        db_table = 'grc_risk_qms_program'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['fiscal_year'],
                condition=models.Q(is_active=True),
                name='unique_active_qms_program_per_fiscal_year',
            )
        ]

    def __str__(self):
        return f"QMS Program: {self.program_title}"

    def get_workflow_context(self) -> dict:
        return {
            'entity_type': 'qms_audit_program',
            'entity_id': str(self.id),
            'fiscal_year_id': str(self.fiscal_year_id),
            'prepared_by': str(self.prepared_by),
        }

    def get_workflow_metadata(self) -> dict:
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {
            'entity_type': 'qms_audit_program',
            'entity_id': str(self.id),
            'status': self.status,
            'program_title': self.program_title,
        }
        return add_entity_detail_path_to_metadata(meta, 'qms_audit_program')


class QMSAuditPlan(TimestampedModel, StatusMixin, WorkflowMixin):
    """
    Specific audit plan within a QMS Audit Program — one per auditee unit.
    Rule E.7: notification ≥10 days before audit start.
    Rule E.2: QAs cannot audit own unit.
    """
    audit_program = models.ForeignKey(
        QMSAuditProgram, on_delete=models.CASCADE, related_name='audit_plans'
    )
    plan_title = models.CharField(max_length=255)
    auditee_unit_id = models.UUIDField(
        db_index=True, help_text="Corporate Service unit UUID being audited"
    )
    lead_team_leader = models.UUIDField(help_text="QA UUID of the lead Team Leader")
    audit_start_date = models.DateField()
    audit_end_date = models.DateField()
    notification_date = models.DateField(
        null=True, blank=True,
        help_text="Date auditee was notified; must be ≥10 days before audit_start_date"
    )
    scope = models.TextField()
    criteria = models.TextField(blank=True)
    # DRS dual-reference
    document_id = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True
    )
    # GAP-04: NDA forms
    nda_signed = models.BooleanField(default=False)
    nda_signed_date = models.DateField(null=True, blank=True)
    nda_document_id = models.UUIDField(
        null=True, blank=True, help_text="DRS reference for signed NDA"
    )
    # GAP-10: Timetable agreement
    timetable_agreed = models.BooleanField(default=False)
    # GAP-14: Rework counter
    rework_count = models.IntegerField(default=0)
    # GAP-17: Review comments
    last_review_comment = models.TextField(blank=True)
    last_reviewed_by = models.UUIDField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_qms_plan'
        ordering = ['-created_at']

    def __str__(self):
        return f"QMS Plan: {self.plan_title} ({self.status})"

    def clean(self):
        """Validate auditee notification lead time (Rule E.7)."""
        from django.core.exceptions import ValidationError
        if self.notification_date and self.audit_start_date:
            delta = (self.audit_start_date - self.notification_date).days
            if delta < 10:
                raise ValidationError(
                    "Auditee must be notified at least 10 days before the audit start date."
                )

    def get_workflow_context(self) -> dict:
        return {
            'entity_type': 'qms_audit_plan',
            'entity_id': str(self.id),
            'audit_program_id': str(self.audit_program_id),
            'auditee_unit_id': str(self.auditee_unit_id),
            'lead_team_leader': str(self.lead_team_leader),
        }

    def get_workflow_metadata(self) -> dict:
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        meta = {
            'entity_type': 'qms_audit_plan',
            'entity_id': str(self.id),
            'status': self.status,
            'plan_title': self.plan_title,
        }
        return add_entity_detail_path_to_metadata(meta, 'qms_audit_plan')


class QMSAuditTeamAssignment(TimestampedModel, StatusMixin):
    """
    Join table: assigns a QA (by UUID) to an Audit Plan.
    Rule E.2: QA org unit ≠ auditee unit — enforced in clean().
    """
    audit_plan = models.ForeignKey(
        QMSAuditPlan, on_delete=models.CASCADE, related_name='team_assignments'
    )
    auditor_id = models.UUIDField(db_index=True, help_text="QualityAuditor user UUID")
    ROLE_TEAM_LEADER = 'team_leader'
    ROLE_AUDITOR = 'auditor'
    ROLE_CHOICES = [
        (ROLE_TEAM_LEADER, 'Team Leader'),
        (ROLE_AUDITOR, 'Auditor'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_AUDITOR)

    class Meta:
        db_table = 'grc_risk_qms_team_assignment'
        unique_together = [['audit_plan', 'auditor_id']]

    def clean(self):
        """SRS-FIX G-07: QA cannot audit their own unit (Rule E.2)."""
        from django.core.exceptions import ValidationError
        super().clean()
        qa = QualityAuditor.objects.filter(user_id=self.auditor_id, is_active=True).first()
        if qa and self.audit_plan_id:
            plan = self.audit_plan
            if qa.org_unit_id == plan.auditee_unit_id:
                raise ValidationError(
                    "QA cannot audit their own unit (conflict of interest — Rule E.2)."
                )

    def __str__(self):
        return f"Team: {self.auditor_id} ({self.role}) – Plan {self.audit_plan_id}"


class AuditChecklist(TimestampedModel, StatusMixin):
    """
    ISO clause audit checklist item — one per clause per auditor per plan.
    """
    audit_plan = models.ForeignKey(
        QMSAuditPlan, on_delete=models.CASCADE, related_name='checklists'
    )
    iso_clause = models.ForeignKey(
        'ISOClause', on_delete=models.PROTECT, related_name='checklist_items'
    )
    auditor_id = models.UUIDField(db_index=True, help_text="QA UUID who completed this item")
    CONFORMITY_CONFORMING = 'conforming'
    CONFORMITY_MINOR_NC = 'minor_nc'
    CONFORMITY_MAJOR_NC = 'major_nc'
    CONFORMITY_OBSERVATION = 'observation'
    CONFORMITY_NOT_APPLICABLE = 'not_applicable'
    CONFORMITY_CHOICES = [
        (CONFORMITY_CONFORMING, 'Conforming'),
        (CONFORMITY_MINOR_NC, 'Minor Non-Conformance'),
        (CONFORMITY_MAJOR_NC, 'Major Non-Conformance'),
        (CONFORMITY_OBSERVATION, 'Observation'),
        (CONFORMITY_NOT_APPLICABLE, 'Not Applicable'),
    ]
    conformity = models.CharField(
        max_length=20, choices=CONFORMITY_CHOICES,
        default=CONFORMITY_NOT_APPLICABLE, db_index=True
    )
    findings_detail = models.JSONField(
        default=dict,
        help_text="{'evidence': [...], 'objective_evidence': '...', 'auditor_notes': '...'}"
    )

    class Meta:
        db_table = 'grc_risk_qms_checklist'
        unique_together = [['audit_plan', 'iso_clause', 'auditor_id']]

    def __str__(self):
        return f"Checklist: {self.iso_clause_id} – {self.conformity}"


class QMSAuditReport(TimestampedModel, StatusMixin):
    """
    Final audit report for a QMSAuditPlan. 1:1 with QMSAuditPlan.
    """
    audit_plan = models.OneToOneField(
        QMSAuditPlan, on_delete=models.PROTECT, related_name='report'
    )
    report_title = models.CharField(max_length=255)
    executive_summary = models.TextField(blank=True)
    scope_summary = models.TextField(blank=True)
    # Signatures
    tl_signed_by = models.UUIDField(null=True, blank=True)
    tl_signed_at = models.DateTimeField(null=True, blank=True)
    auditee_signed_by = models.UUIDField(null=True, blank=True)
    auditee_signed_at = models.DateTimeField(null=True, blank=True)
    # DRS dual-reference
    document_id = models.UUIDField(null=True, blank=True)
    stamped_document_url = models.URLField(blank=True, default='')
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('tl_signed', 'TL Signed'),
        ('auditee_acknowledged', 'Auditee Acknowledged'),
        ('finalised', 'Finalised'),
        # GAP-12/25/26: Extended post-finalisation governance (Phase 1 fix)
        ('submitted_to_rmqam', 'Submitted to RMQAM'),
        ('returned_for_revision', 'Returned for Revision'),
        ('presented_at_mrm', 'Presented at MRM'),
        ('directives_received', 'Directives Received'),
        ('submitted_to_audit_committee', 'Submitted to Audit Committee'),
        ('audit_committee_reviewed', 'Audit Committee Reviewed'),
        ('adopted_by_commission', 'Adopted by Commission'),
    ]
    status = models.CharField(
        max_length=35, choices=STATUS_CHOICES, default='draft', db_index=True
    )
    # GAP-12: MRM directive tracking fields
    mrm_directives = models.TextField(blank=True)
    mrm_directives_communicated_at = models.DateTimeField(null=True, blank=True)
    rmqam_review_comments = models.TextField(blank=True)
    returned_for_revision_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_qms_report'
        ordering = ['-created_at']

    def __str__(self):
        return f"QMS Report: {self.report_title} ({self.status})"


class NonConformance(TimestampedModel, StatusMixin):
    """
    Non-Conformance record raised within a QMS Audit Report.
    Rule E.9: TL may correct/amend/delete before finalisation.
    """
    audit_report = models.ForeignKey(
        QMSAuditReport, on_delete=models.CASCADE, related_name='nonconformances'
    )
    iso_clause = models.ForeignKey(
        'ISOClause', on_delete=models.PROTECT, related_name='nonconformances'
    )
    nc_type = models.ForeignKey(
        'NonConformanceType', on_delete=models.PROTECT, related_name='nonconformances'
    )
    description = models.TextField()
    objective_evidence = models.TextField()
    raised_by = models.UUIDField(help_text="QA UUID who raised this NC")
    # Corrective action
    corrective_action = models.TextField(blank=True)
    responsible_officer = models.UUIDField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    STATUS_RAISED = 'raised'
    STATUS_ACKNOWLEDGED = 'acknowledged'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_CLOSED = 'closed'
    STATUS_DISPUTED = 'disputed'
    STATUS_WITHDRAWN = 'withdrawn'
    STATUS_CHOICES = [
        (STATUS_RAISED, 'Raised'),
        (STATUS_ACKNOWLEDGED, 'Acknowledged'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_DISPUTED, 'Disputed'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_RAISED, db_index=True
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closure_notes = models.TextField(blank=True)
    # GAP-4: Dispute tracking fields (Phase 1 fix)
    dispute_reason = models.TextField(blank=True)
    disputed_at = models.DateTimeField(null=True, blank=True)
    disputed_by = models.UUIDField(null=True, blank=True)
    # GAP-5: Monthly review tracking
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_nonconformance'
        ordering = ['-created_at']

    def __str__(self):
        return f"NC: {self.nc_type_id} – {self.description[:50]} ({self.status})"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — Meeting & Workshop Management [GAP-01, GAP-08]
# ══════════════════════════════════════════════════════════════════════════════

class RiskMeeting(TimestampedModel, StatusMixin):
    """
    Risk discussion meetings, workshops, brainstorming sessions, awareness sessions.
    SRS §1.9.5 Steps 1–2, §1.9.6 Steps 1–3, §4.11.1.1 #3 and #9.
    """
    MEETING_TYPE_CHOICES = [
        ('risk_discussion', 'Risk Discussion'),
        ('workshop', 'Workshop'),
        ('brainstorming', 'Brainstorming'),
        ('institutional_workshop', 'Institutional Workshop'),
        ('awareness_session', 'Awareness Session'),
        ('management_review', 'Management Review'),  # GAP-6
        ('interview', 'Interview'),  # SRS-FIX G-12: §4.11.1.1 req 3
    ]
    meeting_type = models.CharField(max_length=30, choices=MEETING_TYPE_CHOICES)
    organized_by = models.UUIDField(help_text="user_id of organizer")
    org_unit_id = models.UUIDField(
        null=True, blank=True, help_text="Nullable for cross-unit workshops"
    )
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, related_name='risk_meetings'
    )
    title = models.CharField(max_length=255)
    agenda = models.TextField(blank=True)
    meeting_date = models.DateTimeField()
    venue = models.CharField(max_length=255, blank=True)
    virtual_link = models.URLField(null=True, blank=True)
    MEETING_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20, choices=MEETING_STATUS_CHOICES, default='scheduled', db_index=True
    )
    minutes = models.TextField(blank=True)
    outcomes = models.JSONField(default=list)

    class Meta:
        db_table = 'grc_risk_meeting'
        ordering = ['-meeting_date']

    def __str__(self):
        return f"{self.get_meeting_type_display()}: {self.title}"


class MeetingAttendance(TimestampedModel, StatusMixin):
    """
    Attendance record for a RiskMeeting.
    """
    meeting = models.ForeignKey(
        RiskMeeting, on_delete=models.CASCADE, related_name='attendance'
    )
    user_id = models.UUIDField()
    attended = models.BooleanField(default=False)

    class Meta:
        db_table = 'grc_risk_meeting_attendance'
        unique_together = [['meeting', 'user_id']]

    def __str__(self):
        return f"Attendance: {self.user_id} – {self.meeting_id}"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 8 — QMS Audit Support [GAP-05, GAP-10]
# ══════════════════════════════════════════════════════════════════════════════

class QMSAuditMeeting(TimestampedModel, StatusMixin):
    """
    Entry/exit/pre-audit meetings for a QMS Audit Plan.
    SRS §1.9.9 Steps 9–11 (entry), Steps 15–17 (exit).
    Named QMSAuditMeeting to avoid collision with audit_entities.AuditMeeting.
    """
    audit_plan = models.ForeignKey(
        QMSAuditPlan, on_delete=models.CASCADE, related_name='meetings'
    )
    MEETING_TYPE_CHOICES = [
        ('pre_audit', 'Pre-Audit'),
        ('entry', 'Entry'),
        ('exit', 'Exit'),
    ]
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPE_CHOICES)
    meeting_date = models.DateTimeField()
    minutes = models.TextField(blank=True)
    attendance = models.JSONField(default=list, help_text="List of user_ids")
    timetable_agreed = models.BooleanField(default=False)
    timetable_revised = models.BooleanField(default=False)

    class Meta:
        db_table = 'grc_risk_qms_audit_meeting'
        unique_together = [['audit_plan', 'meeting_type']]

    def __str__(self):
        return f"{self.get_meeting_type_display()} Meeting – Plan {self.audit_plan_id}"


class QMSAuditTimetableEntry(TimestampedModel, StatusMixin):
    """
    Detailed timetable entry for a QMS Audit Plan.
    """
    audit_plan = models.ForeignKey(
        QMSAuditPlan, on_delete=models.CASCADE, related_name='timetable_entries'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    process_or_area = models.CharField(max_length=255)
    assigned_auditor = models.UUIDField()
    auditee_unit_id = models.UUIDField()
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_qms_timetable_entry'
        ordering = ['date', 'start_time', 'sort_order']

    def __str__(self):
        return f"Timetable: {self.process_or_area} ({self.date} {self.start_time})"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 9 — Knowledge Base & Surveys [SRS-FIX G-01, G-02]
# ══════════════════════════════════════════════════════════════════════════════

class RiskKnowledgeBase(TimestampedModel, StatusMixin):
    """
    SRS-FIX G-02: Formal interface for lessons learned, industry best practices,
    and historical audit findings used during risk identification (§4.11.1.1 req 4).
    """
    SOURCE_TYPE_CHOICES = [
        ('lesson_learned', 'Lesson Learned'),
        ('audit_finding', 'Audit Finding'),
        ('industry_best_practice', 'Industry Best Practice'),
        ('external_report', 'External Report'),
    ]
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, null=True, blank=True,
        related_name='knowledge_base_entries'
    )
    document_id = models.UUIDField(
        null=True, blank=True, help_text="DRS document UUID for supporting evidence"
    )
    tags = models.JSONField(default=list, help_text="Searchable keyword tags")
    contributed_by = models.UUIDField(help_text="IAM user UUID who contributed this entry")

    class Meta:
        db_table = 'grc_risk_knowledge_base'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_source_type_display()}] {self.title}"


class RiskSurvey(TimestampedModel, StatusMixin):
    """
    SRS-FIX G-01: Risk identification survey (§4.11.1.1 req 3).
    Targeted to an org unit for a fiscal year.
    """
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    fiscal_year = models.ForeignKey(
        'core.FiscalYear', on_delete=models.PROTECT, related_name='risk_surveys'
    )
    org_unit_id = models.UUIDField(
        null=True, blank=True,
        help_text="Target org unit UUID (null = institution-wide)"
    )
    created_by_user = models.UUIDField(help_text="RMQAM/RMO user UUID who created the survey")
    STATUS_DRAFT = 'draft'
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_OPEN, 'Open'),
        (STATUS_CLOSED, 'Closed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grc_risk_survey'
        ordering = ['-created_at']

    def __str__(self):
        return f"Survey: {self.title} ({self.status})"


class RiskSurveyQuestion(TimestampedModel, StatusMixin):
    """Individual question within a RiskSurvey."""
    survey = models.ForeignKey(RiskSurvey, on_delete=models.CASCADE, related_name='questions')
    QUESTION_TYPE_CHOICES = [
        ('text', 'Text'),
        ('rating', 'Rating (1-5)'),
        ('yes_no', 'Yes / No'),
        ('multiple_choice', 'Multiple Choice'),
    ]
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    question_text = models.TextField()
    choices = models.JSONField(default=list, help_text="Options for multiple_choice type")
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'grc_risk_survey_question'
        ordering = ['sort_order']

    def __str__(self):
        return f"Q{self.sort_order}: {self.question_text[:50]}"


class RiskSurveyResponse(TimestampedModel, StatusMixin):
    """
    One respondent's answer set for a survey.
    """
    survey = models.ForeignKey(RiskSurvey, on_delete=models.CASCADE, related_name='responses')
    respondent_id = models.UUIDField(db_index=True, help_text="IAM user UUID")
    submitted_at = models.DateTimeField(null=True, blank=True)
    answers = models.JSONField(
        default=list,
        help_text='[{"question_id": "uuid", "answer": "..."}]'
    )

    class Meta:
        db_table = 'grc_risk_survey_response'
        unique_together = [['survey', 'respondent_id']]
        ordering = ['-created_at']

    def __str__(self):
        return f"Response: {self.respondent_id} – {self.survey_id}"
