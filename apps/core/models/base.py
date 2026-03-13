"""
Base model classes for GRC Audit Service.
Following FIMS patterns from other services.
"""
import uuid
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base model with common fields used across all GRC entities.
    Follows the pattern from Document Records and Client services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class TimestampedModel(BaseModel):
    """
    Extended base model with created_by tracking.
    Used for models that need audit trail of who created/modified them.
    """
    created_by = models.UUIDField(
        help_text="User ID from IAM service who created this record"
    )
    modified_by = models.UUIDField(
        null=True, 
        blank=True,
        help_text="User ID from IAM service who last modified this record"
    )
    
    class Meta:
        abstract = True


class StatusMixin(models.Model):
    """
    Mixin for entities that have workflow status.
    """
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this record is active and available for use"
    )
    
    class Meta:
        abstract = True


class WorkflowMixin(models.Model):
    """
    Mixin for entities that integrate with Work Orchestration Service.

    Fields mirror the guide's WorkflowMixin (workflow-integration-guide.md §4.1):
      workflow_plan_id       – UUID of the plan created in Work Orchestration Service
      workflow_stage         – human-readable name of the current stage
      workflow_stage_id      – UUID of the current stage record in WO
      workflow_started_at    – when the workflow plan was first created
      workflow_completed_at  – when the workflow reached a terminal state
    """
    workflow_plan_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the workflow plan in Work Orchestration Service"
    )
    workflow_stage = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Current stage name in Work Orchestration Service"
    )
    workflow_stage_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of the current stage in Work Orchestration Service"
    )
    workflow_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the workflow plan was started"
    )
    workflow_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the workflow plan reached a terminal state"
    )

    class Meta:
        abstract = True

    @property
    def has_workflow(self) -> bool:
        """Check if this entity has an associated workflow."""
        return self.workflow_plan_id is not None

    @property
    def has_active_workflow(self) -> bool:
        """Check if this entity has an active (not completed) workflow."""
        return self.workflow_plan_id is not None and self.workflow_completed_at is None

    @property
    def is_workflow_completed(self) -> bool:
        """Check if the workflow has been completed."""
        return self.workflow_completed_at is not None

    def start_workflow(
        self,
        plan_id: str,
        initial_stage: str = '',
        stage_id=None,
    ) -> None:
        """Mark workflow as started. Sets all 5 workflow fields."""
        self.workflow_plan_id = plan_id
        self.workflow_stage = initial_stage
        self.workflow_stage_id = stage_id
        self.workflow_started_at = timezone.now()
        self.workflow_completed_at = None

    def update_workflow_stage(
        self,
        stage_name: str,
        stage_id=None,
    ) -> None:
        """Update the current workflow stage."""
        self.workflow_stage = stage_name
        if stage_id:
            self.workflow_stage_id = stage_id

    def complete_workflow(self) -> None:
        """Mark workflow as completed."""
        self.workflow_completed_at = timezone.now()

    def cancel_workflow(self) -> None:
        """Mark workflow as cancelled (also sets completed time)."""
        self.workflow_completed_at = timezone.now()

    def clear_workflow(self) -> None:
        """Clear all workflow fields."""
        self.workflow_plan_id = None
        self.workflow_stage = ''
        self.workflow_stage_id = None
        self.workflow_started_at = None
        self.workflow_completed_at = None

    def get_workflow_context(self) -> dict:
        """
        Return context variables for WO stage assignee resolution.
        Override in subclasses to provide entity-specific variables.
        Matches corporate-service WorkflowMixin default.
        """
        return {
            'entity_type': self._meta.model_name,
            'entity_id': str(self.pk),
        }

    def get_workflow_metadata(self) -> dict:
        """
        Return metadata to store with the WO plan (display data).
        Override in subclasses to provide entity-specific metadata.
        Matches corporate-service WorkflowMixin default.
        """
        return {
            'entity_type': self._meta.model_name,
            'entity_id': str(self.pk),
            'entity_repr': str(self),
        }

    def log_workflow_action(self, action: str, actor_id: str, stage_name: str, comment: str = '', metadata: dict = None) -> None:
        """
        Hook for audit logging of workflow actions.
        Override in subclasses to persist per-action audit records.
        Matches corporate-service WorkflowMixin stub.
        """
        self.workflow_completed_at = None