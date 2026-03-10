"""
Migration: Add audit_scope field to AuditProgram.

SRS Requirement (AUDT2_ext.md Process Flow §8, Key Information):
  "LA defines audit scope covering areas of focus from the RCM —
   Areas in scope, Areas excluded with justification, Audit objectives."

Previously this field was dropped in the gap analysis as an assumption.
This migration restores it for full SRS alignment.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_alter_implementationmonitoring_auditee_responded_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditprogram',
            name='audit_scope',
            field=models.TextField(
                blank=True,
                null=True,
                help_text=(
                    'Audit scope: areas in scope, areas excluded with justification. '
                    "SRS key data requirement (Process Flow §8): 'LA defines audit scope "
                    "covering areas of focus from the RCM — Areas in scope, "
                    "Areas excluded with justification, Audit objectives.'"
                ),
            ),
        ),
    ]
