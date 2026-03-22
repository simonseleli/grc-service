"""
Backend Phase 3 — Model Field Additions

Tests verify all new fields exist, have correct defaults, and are
persisted/retrieved correctly.

B3-1: LitigationDirective.requires_dg_approval_for_closure + pending_dg_approval status
B3-2: CaseDefendant.hold_reason + CasePlaintiff.hold_reason
B3-3: Meeting.reschedule_reason
B3-4: TaskLitigation.auto_created
B3-5: GoverningBody.meeting_number_prefix + meeting_number_format
"""
import pytest

from apps.core.models import (
    CaseDefendant, CasePlaintiff,
    LitigationDirective, TaskLitigation,
)
from apps.core.models.legal_entities import GoverningBody, Meeting


# ═══════════════════════════════════════════════════════════════════════════════
# B3-5 — GoverningBody: meeting_number_prefix + meeting_number_format
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoverningBodyMeetingNumberConfig:
    @pytest.mark.django_db
    def test_defaults(self, governing_body):
        assert governing_body.meeting_number_prefix == ''
        assert governing_body.meeting_number_format == 'sequential'

    @pytest.mark.django_db
    def test_set_prefix(self, governing_body):
        governing_body.meeting_number_prefix = 'FCC-LEGAL'
        governing_body.save(update_fields=['meeting_number_prefix'])
        governing_body.refresh_from_db()
        assert governing_body.meeting_number_prefix == 'FCC-LEGAL'

    @pytest.mark.django_db
    def test_set_financial_year_format(self, governing_body):
        governing_body.meeting_number_format = 'financial_year'
        governing_body.save(update_fields=['meeting_number_format'])
        governing_body.refresh_from_db()
        assert governing_body.meeting_number_format == 'financial_year'

    @pytest.mark.django_db
    def test_choices_are_valid(self):
        choices = dict(GoverningBody.MEETING_NUMBER_FORMAT_CHOICES)
        assert 'sequential' in choices
        assert 'financial_year' in choices


# ═══════════════════════════════════════════════════════════════════════════════
# B3-3 — Meeting: reschedule_reason
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingRescheduleReason:
    @pytest.mark.django_db
    def test_default_is_empty(self, meeting):
        assert meeting.reschedule_reason == ''

    @pytest.mark.django_db
    def test_persist_reason(self, meeting):
        meeting.reschedule_reason = 'Key speaker unavailable'
        meeting.save(update_fields=['reschedule_reason'])
        meeting.refresh_from_db()
        assert meeting.reschedule_reason == 'Key speaker unavailable'

    @pytest.mark.django_db
    def test_field_nullable_false(self):
        """reschedule_reason is blank=True but NOT null — stored as empty string."""
        field = Meeting._meta.get_field('reschedule_reason')
        assert field.blank is True
        assert field.null is False


# ═══════════════════════════════════════════════════════════════════════════════
# B3-2 — CaseDefendant / CasePlaintiff: hold_reason
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaseDefendantHoldReason:
    @pytest.mark.django_db
    def test_default_is_empty(self, case_defendant):
        assert case_defendant.hold_reason == ''

    @pytest.mark.django_db
    def test_persist_hold_reason(self, case_defendant):
        case_defendant.hold_reason = 'Awaiting court ruling'
        case_defendant.save(update_fields=['hold_reason'])
        case_defendant.refresh_from_db()
        assert case_defendant.hold_reason == 'Awaiting court ruling'

    @pytest.mark.django_db
    def test_hold_reason_blank_allowed(self):
        field = CaseDefendant._meta.get_field('hold_reason')
        assert field.blank is True
        assert field.null is False


class TestCasePlaintiffHoldReason:
    @pytest.mark.django_db
    def test_default_is_empty(self, case_plaintiff):
        assert case_plaintiff.hold_reason == ''

    @pytest.mark.django_db
    def test_persist_hold_reason(self, case_plaintiff):
        case_plaintiff.hold_reason = 'Investigation pending'
        case_plaintiff.save(update_fields=['hold_reason'])
        case_plaintiff.refresh_from_db()
        assert case_plaintiff.hold_reason == 'Investigation pending'

    @pytest.mark.django_db
    def test_hold_reason_blank_allowed(self):
        field = CasePlaintiff._meta.get_field('hold_reason')
        assert field.blank is True
        assert field.null is False


# ═══════════════════════════════════════════════════════════════════════════════
# B3-1 — LitigationDirective: requires_dg_approval_for_closure + pending_dg_approval
# ═══════════════════════════════════════════════════════════════════════════════

class TestLitigationDirectiveDGApproval:
    @pytest.mark.django_db
    def test_default_is_false(self, litigation_directive):
        assert litigation_directive.requires_dg_approval_for_closure is False

    @pytest.mark.django_db
    def test_set_requires_dg_approval(self, litigation_directive):
        litigation_directive.requires_dg_approval_for_closure = True
        litigation_directive.save(update_fields=['requires_dg_approval_for_closure'])
        litigation_directive.refresh_from_db()
        assert litigation_directive.requires_dg_approval_for_closure is True

    @pytest.mark.django_db
    def test_pending_dg_approval_is_valid_status(self, litigation_directive):
        valid_statuses = [c[0] for c in LitigationDirective.STATUS_CHOICES]
        assert 'pending_dg_approval' in valid_statuses

    @pytest.mark.django_db
    def test_set_pending_dg_approval_status(self, litigation_directive):
        litigation_directive.status = 'pending_dg_approval'
        litigation_directive.save(update_fields=['status'])
        litigation_directive.refresh_from_db()
        assert litigation_directive.status == 'pending_dg_approval'

    @pytest.mark.django_db
    def test_original_statuses_still_valid(self, litigation_directive):
        valid_statuses = [c[0] for c in LitigationDirective.STATUS_CHOICES]
        for s in ('open', 'in_progress', 'closed'):
            assert s in valid_statuses

    @pytest.mark.django_db
    def test_field_is_boolean(self):
        from django.db.models import BooleanField
        field = LitigationDirective._meta.get_field('requires_dg_approval_for_closure')
        assert isinstance(field, BooleanField)
        assert field.default is False


# ═══════════════════════════════════════════════════════════════════════════════
# B3-4 — TaskLitigation: auto_created
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskLitigationAutoCreated:
    @pytest.mark.django_db
    def test_default_is_false(self, task_litigation):
        assert task_litigation.auto_created is False

    @pytest.mark.django_db
    def test_set_auto_created_true(self, task_litigation):
        task_litigation.auto_created = True
        task_litigation.save(update_fields=['auto_created'])
        task_litigation.refresh_from_db()
        assert task_litigation.auto_created is True

    @pytest.mark.django_db
    def test_field_is_boolean(self):
        from django.db.models import BooleanField
        field = TaskLitigation._meta.get_field('auto_created')
        assert isinstance(field, BooleanField)
        assert field.default is False

    @pytest.mark.django_db
    def test_manual_task_stays_false(self, task_litigation):
        """Manually created tasks must not have auto_created set."""
        assert task_litigation.auto_created is False
        refreshed = TaskLitigation.objects.get(pk=task_litigation.pk)
        assert refreshed.auto_created is False
