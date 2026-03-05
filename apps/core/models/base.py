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