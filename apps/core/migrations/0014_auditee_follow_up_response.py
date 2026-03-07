"""
P2-GAP 4: Split ImplementationMonitoring into header + AuditeeFollowUpResponse.

Operations (in order — must stay in this order for the RunPython data migration):
  1. AddField:     status on ImplementationMonitoring
  2. RenameField:  implementation_progress → latest_progress on ImplementationMonitoring
  3. CreateModel:  AuditeeFollowUpResponse
  4. RunPython:    copy existing monitoring rows → AuditeeFollowUpResponse cycle 1
  5. RemoveField:  progress_notes from ImplementationMonitoring  (after data copied)
  6. RemoveField:  evidence_documents from ImplementationMonitoring (after data copied)
"""

import uuid
import django.db.models.deletion
from django.db import migrations, models

# Sentinel UUID used as created_by for system-generated migration rows
_SYSTEM_UUID = uuid.UUID('00000000-0000-0000-0000-000000000000')


def forward_migrate_monitoring_cycles(apps, schema_editor):
    """
    For every ImplementationMonitoring row, create one AuditeeFollowUpResponse
    at cycle_number=1 copying the existing progress/notes/evidence data.

    Called while progress_notes and evidence_documents still exist on
    ImplementationMonitoring (RemoveField runs after this RunPython).
    """
    ImplementationMonitoring = apps.get_model('core', 'ImplementationMonitoring')
    AuditeeFollowUpResponse = apps.get_model('core', 'AuditeeFollowUpResponse')

    for monitoring in ImplementationMonitoring.objects.all():
        # Determine historical status of this cycle from header state
        if monitoring.reviewed_by:
            cycle_status = 'verified'
        elif monitoring.auditee_responded_at:
            cycle_status = 'submitted'
        else:
            cycle_status = 'pending'

        AuditeeFollowUpResponse.objects.create(
            monitoring=monitoring,
            cycle_number=1,
            status=cycle_status,
            # progress_notes / evidence_documents still exist on the model here
            implementation_progress=monitoring.latest_progress,
            progress_notes=monitoring.progress_notes or '',
            evidence_documents=monitoring.evidence_documents or [],
            # Notification phase
            notified_at=monitoring.notification_sent_at,
            response_deadline=monitoring.response_deadline,
            is_overdue=monitoring.is_overdue,
            # Submission phase
            submitted_by=None,
            submitted_at=monitoring.auditee_responded_at,
            # Verification phase
            verified_by=monitoring.reviewed_by,
            verified_at=None,
            verification_notes='',
            # TimestampedModel required field
            created_by=monitoring.reviewed_by or _SYSTEM_UUID,
        )


def reverse_migrate_monitoring_cycles(apps, schema_editor):
    """No-op reverse: AuditeeFollowUpResponse rows removed by DeleteModel."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_engagementnotification'),
    ]

    operations = [
        # 1. Add status column to ImplementationMonitoring header
        migrations.AddField(
            model_name='implementationmonitoring',
            name='status',
            field=models.CharField(
                choices=[('active', 'Active'), ('closed', 'Closed')],
                db_index=True,
                default='active',
                max_length=20,
            ),
        ),

        # 2. Rename implementation_progress → latest_progress on header
        migrations.RenameField(
            model_name='implementationmonitoring',
            old_name='implementation_progress',
            new_name='latest_progress',
        ),

        # 3. Create AuditeeFollowUpResponse (while progress_notes/evidence_documents
        #    still exist on ImplementationMonitoring — needed for RunPython below)
        migrations.CreateModel(
            name='AuditeeFollowUpResponse',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(help_text='User ID from IAM service who created this record')),
                ('modified_by', models.UUIDField(blank=True, help_text='User ID from IAM service who last modified this record', null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True, help_text='Whether this record is active and available for use')),
                ('monitoring', models.ForeignKey(
                    help_text='Parent monitoring header',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='follow_up_responses',
                    to='core.implementationmonitoring',
                )),
                ('cycle_number', models.PositiveIntegerField(
                    help_text='Cycle sequence number (1, 2, 3 …); auto-incremented in view layer',
                )),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('submitted', 'Submitted'), ('verified', 'Verified'), ('rejected', 'Rejected')],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('notified_at', models.DateTimeField(blank=True, help_text='When the auditee was notified for this cycle', null=True)),
                ('response_deadline', models.DateTimeField(blank=True, help_text='Response deadline for this cycle (notified_at + 5 business days)', null=True)),
                ('is_overdue', models.BooleanField(default=False)),
                ('submitted_by', models.UUIDField(blank=True, help_text='Auditee user ID who submitted the response', null=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('implementation_progress', models.DecimalField(
                    decimal_places=2,
                    default=0.0,
                    help_text='Implementation progress % reported by auditee for this cycle',
                    max_digits=5,
                )),
                ('progress_notes', models.TextField(blank=True)),
                ('evidence_documents', models.JSONField(blank=True, default=list, help_text='List of supporting document references')),
                ('verified_by', models.UUIDField(blank=True, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('verification_notes', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'Auditee Follow-up Response',
                'verbose_name_plural': 'Auditee Follow-up Responses',
                'db_table': 'grc_auditee_follow_up_response',
                'ordering': ['monitoring', 'cycle_number'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='auditeefollowupresponse',
            unique_together={('monitoring', 'cycle_number')},
        ),

        # 4. Data migration: copy existing monitoring rows → AuditeeFollowUpResponse
        migrations.RunPython(
            forward_migrate_monitoring_cycles,
            reverse_migrate_monitoring_cycles,
        ),

        # 5 & 6. Remove progress_notes and evidence_documents from header
        #        (data has been copied to AuditeeFollowUpResponse in step 4)
        migrations.RemoveField(
            model_name='implementationmonitoring',
            name='progress_notes',
        ),
        migrations.RemoveField(
            model_name='implementationmonitoring',
            name='evidence_documents',
        ),
    ]
