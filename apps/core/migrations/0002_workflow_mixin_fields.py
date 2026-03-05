"""
Migration 0002: Replace orchestration_plan_id with full WorkflowMixin fields.

Changes per model:
  AuditUniverse, AuditPlan, AuditEngagement, AuditReport:
    - RenameField  orchestration_plan_id  →  workflow_plan_id
    - AddField     workflow_stage
    - AddField     workflow_stage_id
    - AddField     workflow_started_at
    - AddField     workflow_completed_at

  WorkingPaper (had no workflow fields at all):
    - AddField     workflow_plan_id
    - AddField     workflow_stage
    - AddField     workflow_stage_id
    - AddField     workflow_started_at
    - AddField     workflow_completed_at
"""
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        # ── AuditUniverse ────────────────────────────────────────────────────
        migrations.RenameField(
            model_name="audituniverse",
            old_name="orchestration_plan_id",
            new_name="workflow_plan_id",
        ),
        migrations.AddField(
            model_name="audituniverse",
            name="workflow_stage",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Current stage name in Work Orchestration Service",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="audituniverse",
            name="workflow_stage_id",
            field=models.UUIDField(
                blank=True,
                null=True,
                help_text="UUID of the current stage in Work Orchestration Service",
            ),
        ),
        migrations.AddField(
            model_name="audituniverse",
            name="workflow_started_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan was started",
            ),
        ),
        migrations.AddField(
            model_name="audituniverse",
            name="workflow_completed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan reached a terminal state",
            ),
        ),

        # ── AuditPlan ────────────────────────────────────────────────────────
        migrations.RenameField(
            model_name="auditplan",
            old_name="orchestration_plan_id",
            new_name="workflow_plan_id",
        ),
        migrations.AddField(
            model_name="auditplan",
            name="workflow_stage",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Current stage name in Work Orchestration Service",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="auditplan",
            name="workflow_stage_id",
            field=models.UUIDField(
                blank=True,
                null=True,
                help_text="UUID of the current stage in Work Orchestration Service",
            ),
        ),
        migrations.AddField(
            model_name="auditplan",
            name="workflow_started_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan was started",
            ),
        ),
        migrations.AddField(
            model_name="auditplan",
            name="workflow_completed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan reached a terminal state",
            ),
        ),

        # ── AuditEngagement ──────────────────────────────────────────────────
        migrations.RenameField(
            model_name="auditengagement",
            old_name="orchestration_plan_id",
            new_name="workflow_plan_id",
        ),
        migrations.AddField(
            model_name="auditengagement",
            name="workflow_stage",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Current stage name in Work Orchestration Service",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="auditengagement",
            name="workflow_stage_id",
            field=models.UUIDField(
                blank=True,
                null=True,
                help_text="UUID of the current stage in Work Orchestration Service",
            ),
        ),
        migrations.AddField(
            model_name="auditengagement",
            name="workflow_started_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan was started",
            ),
        ),
        migrations.AddField(
            model_name="auditengagement",
            name="workflow_completed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan reached a terminal state",
            ),
        ),

        # ── AuditReport ──────────────────────────────────────────────────────
        migrations.RenameField(
            model_name="auditreport",
            old_name="orchestration_plan_id",
            new_name="workflow_plan_id",
        ),
        migrations.AddField(
            model_name="auditreport",
            name="workflow_stage",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Current stage name in Work Orchestration Service",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="auditreport",
            name="workflow_stage_id",
            field=models.UUIDField(
                blank=True,
                null=True,
                help_text="UUID of the current stage in Work Orchestration Service",
            ),
        ),
        migrations.AddField(
            model_name="auditreport",
            name="workflow_started_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan was started",
            ),
        ),
        migrations.AddField(
            model_name="auditreport",
            name="workflow_completed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan reached a terminal state",
            ),
        ),

        # ── WorkingPaper (no workflow columns at all in 0001) ────────────────
        migrations.AddField(
            model_name="workingpaper",
            name="workflow_plan_id",
            field=models.UUIDField(
                blank=True,
                null=True,
                db_index=True,
                help_text="UUID of the workflow plan in Work Orchestration Service",
            ),
        ),
        migrations.AddField(
            model_name="workingpaper",
            name="workflow_stage",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Current stage name in Work Orchestration Service",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="workingpaper",
            name="workflow_stage_id",
            field=models.UUIDField(
                blank=True,
                null=True,
                help_text="UUID of the current stage in Work Orchestration Service",
            ),
        ),
        migrations.AddField(
            model_name="workingpaper",
            name="workflow_started_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan was started",
            ),
        ),
        migrations.AddField(
            model_name="workingpaper",
            name="workflow_completed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the workflow plan reached a terminal state",
            ),
        ),
    ]
