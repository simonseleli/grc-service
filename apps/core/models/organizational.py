"""
Organizational structure models for GRC Audit Service.
These models cache/sync organizational data from Corporate Service.
"""
from django.db import models
from .base import BaseModel, TimestampedModel, StatusMixin


class Directorate(TimestampedModel, StatusMixin):
    """
    Directorate information cached from Corporate Service.
    Used for auditable entity organization and reporting structure.
    """
    external_id = models.UUIDField(
        unique=True,
        help_text="Reference ID from Corporate Service"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Official directorate code"
    )
    name = models.CharField(
        max_length=255,
        help_text="Official directorate name"
    )
    head_of_directorate = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the Director from IAM service"
    )
    last_sync = models.DateTimeField(
        auto_now=True,
        help_text="Last synchronization from Corporate Service"
    )
    
    class Meta:
        db_table = 'grc_directorate'
        ordering = ['name']
        verbose_name = 'Directorate'
        verbose_name_plural = 'Directorates'
        
    def __str__(self):
        return f"{self.code} - {self.name}"


class Department(TimestampedModel, StatusMixin):
    """
    Department information cached from Corporate Service.
    Departments belong to directorates in the organizational hierarchy.
    """
    external_id = models.UUIDField(
        unique=True,
        help_text="Reference ID from Corporate Service"
    )
    directorate = models.ForeignKey(
        Directorate,
        on_delete=models.CASCADE,
        related_name='departments',
        help_text="Parent directorate"
    )
    code = models.CharField(
        max_length=50,
        help_text="Official department code"
    )
    name = models.CharField(
        max_length=255,
        help_text="Official department name"
    )
    head_of_department = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the Department Head from IAM service"
    )
    last_sync = models.DateTimeField(
        auto_now=True,
        help_text="Last synchronization from Corporate Service"
    )
    
    class Meta:
        db_table = 'grc_department'
        ordering = ['directorate__name', 'name']
        unique_together = [['directorate', 'code']]
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        
    def __str__(self):
        return f"{self.directorate.code}/{self.code} - {self.name}"
    
    @property
    def full_code(self):
        """Get the full organizational code including directorate."""
        return f"{self.directorate.code}/{self.code}"


class Unit(TimestampedModel, StatusMixin):
    """
    Unit information cached from Corporate Service.
    Units belong to departments in the organizational hierarchy.
    """
    external_id = models.UUIDField(
        unique=True,
        help_text="Reference ID from Corporate Service"
    )
    directorate = models.ForeignKey(
        Directorate,
        on_delete=models.CASCADE,
        related_name='units',
        help_text="Parent directorate"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='units',
        help_text="Parent department"
    )
    code = models.CharField(
        max_length=50,
        help_text="Official unit code"
    )
    name = models.CharField(
        max_length=255,
        help_text="Official unit name"
    )
    head_of_unit = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the Unit Head from IAM service"
    )
    is_independent = models.BooleanField(
        default=False,
        help_text="Whether the unit operates independently"
    )
    last_sync = models.DateTimeField(
        auto_now=True,
        help_text="Last synchronization from Corporate Service"
    )
    
    class Meta:
        db_table = 'grc_unit'
        ordering = ['department__name', 'name']
        unique_together = [['department', 'code']]
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'
        
    def __str__(self):
        return f"{self.department.code}/{self.code} - {self.name}"
    
    @property
    def full_code(self):
        """Get the full organizational code including directorate and department."""
        return f"{self.directorate.code}/{self.department.code}/{self.code}"


class Section(TimestampedModel, StatusMixin):
    """
    Section information cached from Corporate Service.
    Sections belong to units in the organizational hierarchy.
    """
    external_id = models.UUIDField(
        unique=True,
        help_text="Reference ID from Corporate Service"
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='sections',
        help_text="Parent unit"
    )
    code = models.CharField(
        max_length=50,
        help_text="Official section code"
    )
    name = models.CharField(
        max_length=255,
        help_text="Official section name"
    )
    head_of_section = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the Section Head from IAM service"
    )
    last_sync = models.DateTimeField(
        auto_now=True,
        help_text="Last synchronization from Corporate Service"
    )
    
    class Meta:
        db_table = 'grc_section'
        ordering = ['unit__name', 'name']
        unique_together = [['unit', 'code']]
        verbose_name = 'Section'
        verbose_name_plural = 'Sections'
        
    def __str__(self):
        return f"{self.unit.full_code}/{self.code} - {self.name}"
    
    @property
    def full_code(self):
        """Get the full organizational code including all parent levels."""
        return f"{self.unit.full_code}/{self.code}"


class OrganizationalSyncLog(BaseModel):
    """
    Log of organizational data synchronization operations.
    Tracks when data was synced from Corporate Service.
    """
    SYNC_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    sync_type = models.CharField(
        max_length=50,
        choices=[
            ('directorates', 'Directorates'),
            ('departments', 'Departments'),
            ('units', 'Units'),
            ('sections', 'Sections'),
            ('full_sync', 'Full Organizational Sync'),
        ],
        help_text="Type of synchronization performed"
    )
    status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default='pending',
        help_text="Current status of the sync operation"
    )
    started_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID who initiated the sync (null for automated)"
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the sync operation started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the sync operation completed"
    )
    records_processed = models.IntegerField(
        default=0,
        help_text="Number of records processed during sync"
    )
    records_created = models.IntegerField(
        default=0,
        help_text="Number of new records created"
    )
    records_updated = models.IntegerField(
        default=0,
        help_text="Number of existing records updated"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error details if sync failed"
    )
    
    class Meta:
        db_table = 'grc_organizational_sync_log'
        ordering = ['-started_at']
        verbose_name = 'Organizational Sync Log'
        verbose_name_plural = 'Organizational Sync Logs'
        
    def __str__(self):
        return f"{self.sync_type} - {self.status} ({self.started_at})"