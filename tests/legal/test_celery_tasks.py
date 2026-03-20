"""
Legal Module — Celery task tests.

Covers:
  - check_legal_directive_deadlines  (MeetingDirective → overdue, LitigationDirective → warn)
  - check_legal_task_deadlines       (TaskLitigation → reminders + overdue)
"""

import datetime
from unittest.mock import patch

import pytest

from apps.core.models import MeetingDirective, LitigationDirective, TaskLitigation

DIRECTIVE_TASK_MODULE = "apps.core.tasks.legal_directive_deadlines"
CASE_TASK_MODULE = "apps.core.tasks.legal_case_deadlines"


# ═══════════════════════════════════════════════════════════════════════════════
# check_legal_directive_deadlines
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckLegalDirectiveDeadlines:

    @pytest.mark.django_db
    def test_marks_overdue_meeting_directive(self, meeting_directive_overdue):
        """MeetingDirective with past due_date + non-terminal status → status='overdue'."""
        with patch(f"{DIRECTIVE_TASK_MODULE}._send_directive_overdue_notification"):
            from apps.core.tasks.legal_directive_deadlines import check_legal_directive_deadlines
            result = check_legal_directive_deadlines()

        meeting_directive_overdue.refresh_from_db()
        assert meeting_directive_overdue.status == "overdue"
        assert result["meeting_directives_overdue"] >= 1

    @pytest.mark.django_db
    def test_skips_already_overdue_directive(self, meeting_directive_overdue):
        """Directives already marked overdue should not be processed again."""
        meeting_directive_overdue.status = "overdue"
        meeting_directive_overdue.save(update_fields=["status"])

        with patch(f"{DIRECTIVE_TASK_MODULE}._send_directive_overdue_notification"):
            from apps.core.tasks.legal_directive_deadlines import check_legal_directive_deadlines
            result = check_legal_directive_deadlines()

        assert result["meeting_directives_overdue"] == 0

    @pytest.mark.django_db
    def test_skips_closed_directive(self, meeting_directive_overdue):
        """Closed directives should not be marked overdue."""
        meeting_directive_overdue.status = "closed"
        meeting_directive_overdue.save(update_fields=["status"])

        with patch(f"{DIRECTIVE_TASK_MODULE}._send_directive_overdue_notification"):
            from apps.core.tasks.legal_directive_deadlines import check_legal_directive_deadlines
            result = check_legal_directive_deadlines()

        assert result["meeting_directives_overdue"] == 0

    @pytest.mark.django_db
    def test_warns_overdue_litigation_directive(self, litigation_directive):
        """LitigationDirective with past due_date → warning notification."""
        # Force date to past
        litigation_directive.due_date = datetime.date(2025, 1, 1)
        litigation_directive.save(update_fields=["due_date"])

        with patch(f"{DIRECTIVE_TASK_MODULE}._send_directive_overdue_notification") as mock_notify:
            from apps.core.tasks.legal_directive_deadlines import check_legal_directive_deadlines
            result = check_legal_directive_deadlines()

        assert result["litigation_directives_warned"] >= 1
        mock_notify.assert_called()

    @pytest.mark.django_db
    def test_no_overdue_returns_zero_counts(self, meeting_directive):
        """When no directives are overdue, counts should be 0."""
        with patch(f"{DIRECTIVE_TASK_MODULE}._send_directive_overdue_notification"):
            from apps.core.tasks.legal_directive_deadlines import check_legal_directive_deadlines
            result = check_legal_directive_deadlines()

        assert result["meeting_directives_overdue"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# check_legal_task_deadlines
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckLegalTaskDeadlines:

    @pytest.mark.django_db
    def test_marks_overdue_task(self, task_litigation_overdue):
        """TaskLitigation with past due_date + non-terminal status → status='overdue'."""
        with (
            patch(f"{CASE_TASK_MODULE}._send_task_reminder"),
            patch(f"{CASE_TASK_MODULE}._send_task_overdue_notification"),
        ):
            from apps.core.tasks.legal_case_deadlines import check_legal_task_deadlines
            result = check_legal_task_deadlines()

        task_litigation_overdue.refresh_from_db()
        assert task_litigation_overdue.status == "overdue"
        assert result["overdue_marked"] >= 1

    @pytest.mark.django_db
    def test_skips_already_overdue_task(self, task_litigation_overdue):
        """Tasks already overdue should not be re-processed."""
        task_litigation_overdue.status = "overdue"
        task_litigation_overdue.save(update_fields=["status"])

        with (
            patch(f"{CASE_TASK_MODULE}._send_task_reminder"),
            patch(f"{CASE_TASK_MODULE}._send_task_overdue_notification"),
        ):
            from apps.core.tasks.legal_case_deadlines import check_legal_task_deadlines
            result = check_legal_task_deadlines()

        assert result["overdue_marked"] == 0

    @pytest.mark.django_db
    def test_sends_7_day_reminder(self, case_defendant):
        """Task due in exactly 7 days should trigger a reminder."""
        from tests.legal.conftest import LEGAL_OFFICER_ID, SYSTEM_USER_ID
        today = datetime.date.today()
        task = TaskLitigation.objects.create(
            case_defendant=case_defendant,
            title="7-day reminder test",
            assigned_to_user_id=LEGAL_OFFICER_ID,
            due_date=today + datetime.timedelta(days=7),
            status="open",
            priority="normal",
            created_by=SYSTEM_USER_ID,
        )

        with (
            patch(f"{CASE_TASK_MODULE}._send_task_reminder") as mock_remind,
            patch(f"{CASE_TASK_MODULE}._send_task_overdue_notification"),
        ):
            from apps.core.tasks.legal_case_deadlines import check_legal_task_deadlines
            result = check_legal_task_deadlines()

        assert result["reminders_sent"] >= 1
        mock_remind.assert_called()

    @pytest.mark.django_db
    def test_no_overdue_returns_zero_counts(self, task_litigation):
        """When no tasks overdue and no reminders needed, counts are 0."""
        with (
            patch(f"{CASE_TASK_MODULE}._send_task_reminder"),
            patch(f"{CASE_TASK_MODULE}._send_task_overdue_notification"),
        ):
            from apps.core.tasks.legal_case_deadlines import check_legal_task_deadlines
            result = check_legal_task_deadlines()

        assert result["overdue_marked"] == 0
