"""
Legal Module — Dashboard KPI Views (GAP-12)

Two aggregate endpoints returning litigation statistics:
  GET /legal/dashboard/defendant/
  GET /legal/dashboard/plaintiff/
"""

import logging
from decimal import Decimal

from django.db.models import Count, Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    CaseDefendant, CasePlaintiff,
    JudgmentDefendant, JudgmentPlaintiff,
    AppealDefendant, AppealPlaintiff,
    FinancialPlaintiff,
)
from apps.api.permissions_jwt import CanViewLegalCase, HasAnyPermission
from apps.api.utils.response_helpers import success_response, server_error_response

logger = logging.getLogger(__name__)


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
