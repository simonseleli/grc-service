"""
Legal Module — Dashboard KPI Views (GAP-12)

Three aggregate endpoints returning legal statistics:
  GET /legal/dashboard/stats/       — general cross-entity KPIs
  GET /legal/dashboard/defendant/   — FCC Sued litigation KPIs
  GET /legal/dashboard/plaintiff/   — FCC Suing litigation KPIs
"""

import logging
from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    GoverningBody, Member, SubmissionForDetermination,
    Meeting, MeetingDirective, Minutes,
    CaseDefendant, CasePlaintiff,
    FilingDefendant, FilingPlaintiff,
    TaskLitigation,
    JudgmentDefendant, JudgmentPlaintiff,
    AppealDefendant, AppealPlaintiff,
    FinancialPlaintiff,
    PublicDecision,
)
from apps.api.permissions_jwt import CanViewLegalCase, HasAnyPermission
from apps.api.utils.response_helpers import success_response, server_error_response

logger = logging.getLogger(__name__)


class LegalDashboardStatsView(APIView):
    """
    GET /api/v1/grc/legal/dashboard/stats/

    Returns aggregated cross-entity KPIs for the Legal Dashboard.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            now = timezone.now()

            # Governance
            total_governing_bodies = GoverningBody.objects.filter(is_active=True).count()
            active_members = Member.objects.filter(is_active=True, left_date__isnull=True).count()

            # Meetings
            total_meetings = Meeting.objects.filter(is_active=True).count()
            upcoming_meetings = Meeting.objects.filter(
                is_active=True,
                status__in=['registered', 'invitations_sent', 'agenda_shared', 'quorum_ready'],
                scheduled_start__gte=now,
            ).count()
            active_meetings = Meeting.objects.filter(
                is_active=True,
                status__in=['registered', 'invitations_sent', 'agenda_shared', 'quorum_ready', 'ongoing'],
            ).count()

            # Submissions
            total_submissions = SubmissionForDetermination.objects.filter(is_active=True).count()
            pending_submissions = SubmissionForDetermination.objects.filter(
                is_active=True,
                status__in=['submitted', 'under_review'],
            ).count()

            # Meeting Directives
            total_directives = MeetingDirective.objects.filter(is_active=True).count()
            open_directives = MeetingDirective.objects.filter(
                is_active=True,
                status__in=['open', 'in_progress', 'overdue'],
            ).count()
            overdue_directives = MeetingDirective.objects.filter(
                is_active=True,
                status='overdue',
            ).count()

            # Minutes
            draft_minutes_pending = Minutes.objects.filter(
                is_active=True,
                status__in=['draft', 'pending_approval'],
            ).count()

            # Litigation — Defendant
            total_cases_defendant = CaseDefendant.objects.filter(is_active=True).count()
            active_cases_defendant = CaseDefendant.objects.filter(
                is_active=True,
            ).exclude(status__in=['closed', 'on_hold']).count()

            # Litigation — Plaintiff
            total_cases_plaintiff = CasePlaintiff.objects.filter(is_active=True).count()
            active_cases_plaintiff = CasePlaintiff.objects.filter(
                is_active=True,
            ).exclude(status__in=['closed', 'on_hold']).count()

            # Filings pending approval
            pending_filings = (
                FilingDefendant.objects.filter(
                    is_active=True,
                    status__in=['under_review_lm', 'approved_lm', 'under_review_dg'],
                ).count()
                + FilingPlaintiff.objects.filter(
                    is_active=True,
                    status__in=['under_review_lm', 'approved_lm', 'under_review_dg'],
                ).count()
            )

            # Tasks overdue
            overdue_tasks = TaskLitigation.objects.filter(
                is_active=True,
                status__in=['open', 'in_progress', 'overdue'],
                due_date__lt=date.today(),
            ).count()

            # Public Register
            total_public_decisions = PublicDecision.objects.filter(is_active=True).count()
            published_decisions = PublicDecision.objects.filter(
                is_active=True,
                status='published',
            ).count()

            data = {
                "total_governing_bodies": total_governing_bodies,
                "governing_bodies": total_governing_bodies,
                "active_members": active_members,
                "total_meetings": total_meetings,
                "upcoming_meetings": upcoming_meetings,
                "active_meetings": active_meetings,
                "total_submissions": total_submissions,
                "pending_submissions": pending_submissions,
                "total_directives": total_directives,
                "open_directives": open_directives,
                "overdue_directives": overdue_directives,
                "draft_minutes_pending": draft_minutes_pending,
                "total_cases_defendant": total_cases_defendant,
                "active_cases_defendant": active_cases_defendant,
                "total_cases_plaintiff": total_cases_plaintiff,
                "active_cases_plaintiff": active_cases_plaintiff,
                "pending_filings": pending_filings,
                "overdue_tasks": overdue_tasks,
                "total_public_decisions": total_public_decisions,
                "published_decisions": published_decisions,
            }
            return success_response(data=data, message="Legal dashboard stats retrieved.")

        except Exception as exc:
            logger.exception("Error fetching legal dashboard stats")
            return server_error_response(str(exc))


def _won_loss_ratio(won: int, lost: int) -> str:
    total = won + lost
    if total == 0:
        return "0:0"
    won_pct = round(won * 100 / total)
    lost_pct = 100 - won_pct
    return f"{won_pct}:{lost_pct}"


class LegalDashboardDefendantView(APIView):
    """
    GET /api/v1/grc/legal/dashboard/defendant/

    Returns aggregated KPIs for defendant (FCC Sued) litigation.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalCase().has_permission(request, self):
            self.permission_denied(
                request, message="grc:legal_case:view required."
            )

    def get(self, request):
        try:
            active_qs = CaseDefendant.objects.filter(is_active=True)

            total_cases = active_qs.count()
            active_cases = active_qs.exclude(status__in=['closed', 'on_hold']).count()
            cases_on_appeal = active_qs.filter(status='appeal_filed').count()
            high_risk_cases = active_qs.filter(
                risk_level__code__icontains='high',
            ).count()
            pending_dg_review = active_qs.filter(
                dg_review_status='pending',
            ).exclude(status='closed').count()

            outcomes = dict(
                JudgmentDefendant.objects.filter(
                    is_active=True,
                    case_defendant__is_active=True,
                ).values_list('outcome').annotate(c=Count('id')).values_list('outcome', 'c')
            )
            won = outcomes.get('won', 0)
            lost = outcomes.get('lost', 0)

            data = {
                "total_cases": total_cases,
                "won_loss_ratio": _won_loss_ratio(won, lost),
                "cases_on_appeal": cases_on_appeal,
                "high_risk_cases": high_risk_cases,
                "active_cases": active_cases,
                "pending_dg_review": pending_dg_review,
            }
            return success_response(data=data, message="Defendant dashboard KPIs retrieved.")

        except Exception as exc:
            logger.exception("Error fetching defendant dashboard KPIs")
            return server_error_response(str(exc))


class LegalDashboardPlaintiffView(APIView):
    """
    GET /api/v1/grc/legal/dashboard/plaintiff/

    Returns aggregated KPIs for plaintiff (FCC Suing) litigation.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalCase().has_permission(request, self):
            self.permission_denied(
                request, message="grc:legal_case:view required."
            )

    def get(self, request):
        try:
            active_qs = CasePlaintiff.objects.filter(is_active=True)

            total_cases = active_qs.count()
            active_cases = active_qs.exclude(status__in=['closed', 'on_hold']).count()
            cases_on_appeal = active_qs.filter(status='appeal_filed').count()
            high_risk_cases = active_qs.filter(
                risk_level__code__icontains='high',
            ).count()
            pending_dg_review = active_qs.filter(
                dg_review_status='pending',
            ).exclude(status='closed').count()

            outcomes = dict(
                JudgmentPlaintiff.objects.filter(
                    is_active=True,
                    case_plaintiff__is_active=True,
                ).values_list('outcome').annotate(c=Count('id')).values_list('outcome', 'c')
            )
            won = outcomes.get('won', 0)
            lost = outcomes.get('lost', 0)

            financials = FinancialPlaintiff.objects.filter(
                case_plaintiff__is_active=True,
            ).aggregate(
                recoverable=Sum('claim_amount'),
                recovered=Sum('recovered_amount'),
            )
            recoverable_amount = financials['recoverable'] or Decimal('0.00')
            recovered_amount = financials['recovered'] or Decimal('0.00')

            data = {
                "total_cases": total_cases,
                "won_loss_ratio": _won_loss_ratio(won, lost),
                "cases_on_appeal": cases_on_appeal,
                "high_risk_cases": high_risk_cases,
                "active_cases": active_cases,
                "pending_dg_review": pending_dg_review,
                "recoverable_amount": str(recoverable_amount),
                "recovered_amount": str(recovered_amount),
            }
            return success_response(data=data, message="Plaintiff dashboard KPIs retrieved.")

        except Exception as exc:
            logger.exception("Error fetching plaintiff dashboard KPIs")
            return server_error_response(str(exc))
