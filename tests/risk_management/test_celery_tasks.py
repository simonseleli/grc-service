"""
Risk Management Module — Celery task tests.

Covers:
  - check_risk_monitoring_deadlines  (overdue RTAP items, quarterly reminders, escalations)
  - check_nc_closure_status          (overdue non-conformance notifications)
"""

import datetime
import uuid
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone

from apps.core.models import (
    RTAPItem, RTAPQuarterlyUpdate, NonConformance,
)
from apps.core.models.lookups import FiscalYear, Quarter

from tests.risk_management.conftest import (
    SYSTEM_USER_ID, OFFICER_USER_ID, QA_USER_ID,
)

MONITORING_TASK_MODULE = "apps.core.tasks.risk_monitoring_deadlines"
NC_TASK_MODULE = "apps.core.tasks.risk_nc_monitoring"


# ═══════════════════════════════════════════════════════════════════════════════
# check_risk_monitoring_deadlines — Overdue RTAP Items
# ═══════════════════════════════════════════════════════════════════════════════

class TestOverdueRTAPItems:

    @pytest.mark.django_db
    def test_flags_overdue_rtap_items(self, rtap_item):
        """RTAPItem with past target_date + non-completed status → overdue notification."""
        rtap_item.target_date = datetime.date(2025, 1, 1)
        rtap_item.status = 'not_started'
        rtap_item.save(update_fields=['target_date', 'status'])

        with patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['overdue_flagged'] >= 1
        mock_notify.assert_called()

    @pytest.mark.django_db
    def test_skips_completed_rtap_items(self, rtap_item):
        """Completed RTAPItems should not be flagged as overdue."""
        rtap_item.target_date = datetime.date(2025, 1, 1)
        rtap_item.status = 'completed'
        rtap_item.save(update_fields=['target_date', 'status'])

        with patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['overdue_flagged'] == 0
        mock_notify.assert_not_called()

    @pytest.mark.django_db
    def test_skips_future_target_date(self, rtap_item):
        """RTAPItems with future target_date should not be flagged."""
        rtap_item.target_date = datetime.date(2099, 12, 31)
        rtap_item.status = 'in_progress'
        rtap_item.save(update_fields=['target_date', 'status'])

        with patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['overdue_flagged'] == 0
        mock_notify.assert_not_called()

    @pytest.mark.django_db
    def test_skips_inactive_rtap_items(self, rtap_item):
        """Inactive RTAPItems should not be flagged."""
        rtap_item.target_date = datetime.date(2025, 1, 1)
        rtap_item.is_active = False
        rtap_item.save(update_fields=['target_date', 'is_active'])

        with patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['overdue_flagged'] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# check_risk_monitoring_deadlines — Quarterly Submission Reminders
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuarterlySubmissionReminders:

    @pytest.mark.django_db
    def test_sends_reminder_when_quarter_ending_soon(self, rtap_item, fiscal_year):
        """Reminder sent when current quarter ends in ≤3 days and items lack updates."""
        today = timezone.now().date()
        # Create a quarter that ends in 2 days
        q = Quarter.objects.create(
            fiscal_year=fiscal_year, quarter_number=3, name='Q3',
            start_date=today - datetime.timedelta(days=80),
            end_date=today + datetime.timedelta(days=2),
            created_by=SYSTEM_USER_ID,
        )

        with (
            patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification"),
            patch(f"{MONITORING_TASK_MODULE}._send_rc_submission_reminder") as mock_remind,
            patch(f"{MONITORING_TASK_MODULE}._escalate_non_responsive_rcs", return_value=0),
        ):
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['reminders_sent'] >= 1
        mock_remind.assert_called()

    @pytest.mark.django_db
    def test_no_reminder_when_quarter_not_ending_soon(self, rtap_item, fiscal_year):
        """No reminders when quarter end is far away (>3 days)."""
        today = timezone.now().date()
        Quarter.objects.create(
            fiscal_year=fiscal_year, quarter_number=3, name='Q3',
            start_date=today - datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=60),
            created_by=SYSTEM_USER_ID,
        )

        with (
            patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification"),
            patch(f"{MONITORING_TASK_MODULE}._send_rc_submission_reminder") as mock_remind,
            patch(f"{MONITORING_TASK_MODULE}._escalate_non_responsive_rcs", return_value=0),
        ):
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['reminders_sent'] == 0
        mock_remind.assert_not_called()

    @pytest.mark.django_db
    def test_no_reminder_when_update_exists(self, rtap_item, rtap_quarterly_update, fiscal_year):
        """No reminder when item already has a quarterly update for the current quarter."""
        today = timezone.now().date()
        q = rtap_quarterly_update.quarter
        # Make this quarter the current one
        q.start_date = today - datetime.timedelta(days=80)
        q.end_date = today + datetime.timedelta(days=1)
        q.save(update_fields=['start_date', 'end_date'])

        with (
            patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification"),
            patch(f"{MONITORING_TASK_MODULE}._send_rc_submission_reminder") as mock_remind,
            patch(f"{MONITORING_TASK_MODULE}._escalate_non_responsive_rcs", return_value=0),
        ):
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['reminders_sent'] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# check_risk_monitoring_deadlines — Escalation
# ═══════════════════════════════════════════════════════════════════════════════

class TestEscalationForNonResponsiveRCs:

    @pytest.mark.django_db
    def test_escalation_sent_after_7_days_past_quarter_end(self, rtap_item, fiscal_year):
        """Escalation sent when >7 days past quarter end and no update submitted."""
        today = timezone.now().date()
        q = Quarter.objects.create(
            fiscal_year=fiscal_year, quarter_number=3, name='Q3',
            start_date=today - datetime.timedelta(days=100),
            end_date=today - datetime.timedelta(days=10),
            created_by=SYSTEM_USER_ID,
        )

        with (
            patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification"),
            patch(f"{MONITORING_TASK_MODULE}._send_quarterly_submission_reminders", return_value=0),
            patch(f"{MONITORING_TASK_MODULE}._send_escalation_to_rmqam") as mock_escalate,
        ):
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['escalations_sent'] >= 1
        mock_escalate.assert_called()

    @pytest.mark.django_db
    def test_no_escalation_before_7_days(self, rtap_item, fiscal_year):
        """No escalation if quarter ended <7 days ago."""
        today = timezone.now().date()
        Quarter.objects.create(
            fiscal_year=fiscal_year, quarter_number=3, name='Q3',
            start_date=today - datetime.timedelta(days=80),
            end_date=today - datetime.timedelta(days=3),
            created_by=SYSTEM_USER_ID,
        )

        with (
            patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification"),
            patch(f"{MONITORING_TASK_MODULE}._send_quarterly_submission_reminders", return_value=0),
            patch(f"{MONITORING_TASK_MODULE}._send_escalation_to_rmqam") as mock_escalate,
        ):
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['escalations_sent'] == 0
        mock_escalate.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# check_risk_monitoring_deadlines — Return value structure
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskMonitoringReturnValue:

    @pytest.mark.django_db
    def test_returns_dict_with_expected_keys(self, db):
        """Task always returns a dict with three keys."""
        with (
            patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification"),
            patch(f"{MONITORING_TASK_MODULE}._send_rc_submission_reminder"),
            patch(f"{MONITORING_TASK_MODULE}._send_escalation_to_rmqam"),
        ):
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert 'overdue_flagged' in result
        assert 'reminders_sent' in result
        assert 'escalations_sent' in result

    @pytest.mark.django_db
    def test_zero_counts_when_no_data(self, db):
        """All counts are 0 when no RTAP items or quarters exist."""
        with (
            patch(f"{MONITORING_TASK_MODULE}._send_rtap_overdue_notification"),
            patch(f"{MONITORING_TASK_MODULE}._send_rc_submission_reminder"),
            patch(f"{MONITORING_TASK_MODULE}._send_escalation_to_rmqam"),
        ):
            from apps.core.tasks.risk_monitoring_deadlines import check_risk_monitoring_deadlines
            result = check_risk_monitoring_deadlines()

        assert result['overdue_flagged'] == 0
        assert result['reminders_sent'] == 0
        assert result['escalations_sent'] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# check_nc_closure_status
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckNCClosureStatus:

    @pytest.mark.django_db
    def test_flags_overdue_ncs(self, nonconformance):
        """NC with past due_date + non-closed status → overdue notification."""
        nonconformance.due_date = datetime.date(2025, 1, 1)
        nonconformance.responsible_officer = OFFICER_USER_ID
        nonconformance.save(update_fields=['due_date', 'responsible_officer'])

        with patch(f"{NC_TASK_MODULE}._send_nc_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_nc_monitoring import check_nc_closure_status
            result = check_nc_closure_status()

        assert result['overdue_ncs_notified'] >= 1
        mock_notify.assert_called()

    @pytest.mark.django_db
    def test_skips_closed_ncs(self, nonconformance):
        """Closed NCs should not be flagged."""
        nonconformance.due_date = datetime.date(2025, 1, 1)
        nonconformance.status = 'closed'
        nonconformance.save(update_fields=['due_date', 'status'])

        with patch(f"{NC_TASK_MODULE}._send_nc_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_nc_monitoring import check_nc_closure_status
            result = check_nc_closure_status()

        assert result['overdue_ncs_notified'] == 0
        mock_notify.assert_not_called()

    @pytest.mark.django_db
    def test_skips_ncs_without_due_date(self, nonconformance):
        """NCs without a due_date should not be flagged."""
        nonconformance.due_date = None
        nonconformance.save(update_fields=['due_date'])

        with patch(f"{NC_TASK_MODULE}._send_nc_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_nc_monitoring import check_nc_closure_status
            result = check_nc_closure_status()

        assert result['overdue_ncs_notified'] == 0

    @pytest.mark.django_db
    def test_skips_ncs_with_future_due_date(self, nonconformance):
        """NCs with future due_date should not be flagged."""
        nonconformance.due_date = datetime.date(2099, 12, 31)
        nonconformance.responsible_officer = OFFICER_USER_ID
        nonconformance.save(update_fields=['due_date', 'responsible_officer'])

        with patch(f"{NC_TASK_MODULE}._send_nc_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_nc_monitoring import check_nc_closure_status
            result = check_nc_closure_status()

        assert result['overdue_ncs_notified'] == 0
        mock_notify.assert_not_called()

    @pytest.mark.django_db
    def test_skips_inactive_ncs(self, nonconformance):
        """Inactive NCs should not be flagged."""
        nonconformance.due_date = datetime.date(2025, 1, 1)
        nonconformance.is_active = False
        nonconformance.save(update_fields=['due_date', 'is_active'])

        with patch(f"{NC_TASK_MODULE}._send_nc_overdue_notification") as mock_notify:
            from apps.core.tasks.risk_nc_monitoring import check_nc_closure_status
            result = check_nc_closure_status()

        assert result['overdue_ncs_notified'] == 0

    @pytest.mark.django_db
    def test_returns_dict_with_expected_key(self, db):
        """Task always returns a dict with overdue_ncs_notified."""
        with patch(f"{NC_TASK_MODULE}._send_nc_overdue_notification"):
            from apps.core.tasks.risk_nc_monitoring import check_nc_closure_status
            result = check_nc_closure_status()

        assert 'overdue_ncs_notified' in result

    @pytest.mark.django_db
    def test_zero_count_when_no_ncs(self, db):
        """Count is 0 when no NCs exist."""
        with patch(f"{NC_TASK_MODULE}._send_nc_overdue_notification"):
            from apps.core.tasks.risk_nc_monitoring import check_nc_closure_status
            result = check_nc_closure_status()

        assert result['overdue_ncs_notified'] == 0
