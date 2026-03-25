"""
Risk Dashboard + Comparative Analysis Views (read-only)
"""
import logging

from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import (
    RiskAssessmentSheet,
    RiskChampion,
    QualityAuditor,
    DepartmentalRiskRegister,
    InstitutionalRiskRegister,
    RiskTreatmentActionPlan,
    RTAPItem,
    NonConformance,
    QuarterlyPerformanceReport,
    QMSAuditProgram,
    QMSAuditPlan,
    QMSAuditReport,
    RiskMeeting,
    RiskSurvey,
)
from apps.api.permissions_jwt import CanViewRiskDashboard
from apps.api.utils.response_helpers import server_error_response

logger = logging.getLogger(__name__)


class RiskDashboardView(APIView):
    """Aggregated risk management dashboard statistics — SRS-aligned."""
    permission_classes = [IsAuthenticated, CanViewRiskDashboard]

    @method_decorator(cache_page(300))
    def get(self, request):
        try:
            fiscal_year = request.query_params.get('fiscal_year')

            base_filter = Q(is_active=True)
            if fiscal_year:
                fy_filter = base_filter & Q(fiscal_year_id=fiscal_year)
            else:
                fy_filter = base_filter

            # ── Risk Champions (SRS FCC_SBP_RMQA_01) ───────────────────────
            total_rc = RiskChampion.objects.filter(base_filter).count()
            active_rc = RiskChampion.objects.filter(
                base_filter,
                term_end__isnull=True,
            ).count() + RiskChampion.objects.filter(
                base_filter,
                term_end__gte=timezone.now().date(),
            ).count()

            # ── Assessment Sheets (SRS FCC_SBP_RMQA_03) ────────────────────
            assessments = RiskAssessmentSheet.objects.filter(fy_filter)
            assessment_total = assessments.count()
            assessment_by_status = {
                item['status']: item['count']
                for item in assessments.values('status').annotate(count=Count('id'))
            }

            # ── Departmental Risk Registers (SRS FCC_SBP_RMQA_03) ──────────
            dept_registers = DepartmentalRiskRegister.objects.filter(fy_filter)
            dept_by_status = {
                item['status']: item['count']
                for item in dept_registers.values('status').annotate(count=Count('id'))
            }

            # ── Institutional Risk Registers (SRS FCC_SBP_RMQA_04) ─────────
            inst_registers = InstitutionalRiskRegister.objects.filter(fy_filter)
            inst_by_status = {
                item['status']: item['count']
                for item in inst_registers.values('status').annotate(count=Count('id'))
            }

            # ── RTAP (SRS FCC_SBP_RMQA_05) ─────────────────────────────────
            rtaps = RiskTreatmentActionPlan.objects.filter(fy_filter)
            rtap_by_status = {
                item['status']: item['count']
                for item in rtaps.values('status').annotate(count=Count('id'))
            }
            rtap_items_qs = RTAPItem.objects.filter(rtap__in=rtaps, is_active=True)
            rtap_items_total = rtap_items_qs.count()
            rtap_items_completed = rtap_items_qs.filter(status='completed').count()
            rtap_completion_rate = (
                round((rtap_items_completed / rtap_items_total) * 100)
                if rtap_items_total > 0 else 0
            )

            # ── QPR Summary (SRS — Quarterly Reporting) ────────────────────
            latest_qpr = (
                QuarterlyPerformanceReport.objects
                .filter(base_filter)
                .select_related('quarter', 'fiscal_year')
                .order_by('-fiscal_year__start_date', '-quarter__quarter_number')
                .first()
            )
            if latest_qpr:
                qpr_total_items = (
                    latest_qpr.rtap_completed
                    + latest_qpr.rtap_in_progress
                    + latest_qpr.rtap_not_started
                )
                qpr_impl_rate = (
                    round((latest_qpr.rtap_completed / qpr_total_items) * 100)
                    if qpr_total_items > 0 else 0
                )
                qpr_summary = {
                    "current_quarter": f"Q{latest_qpr.quarter.quarter_number} {latest_qpr.fiscal_year}",
                    "implementation_rate": qpr_impl_rate,
                    "total_reports": QuarterlyPerformanceReport.objects.filter(fy_filter).count(),
                }
            else:
                qpr_summary = {
                    "current_quarter": "—",
                    "implementation_rate": 0,
                    "total_reports": 0,
                }

            # ── Quality Assurance Summary (SRS FCC_SBP_RMQA_06/07) ─────────
            total_qa = QualityAuditor.objects.filter(base_filter).count()
            certified_qa = QualityAuditor.objects.filter(
                base_filter, is_certified=True
            ).count()

            nc_filter = base_filter
            if fiscal_year:
                nc_filter = base_filter & Q(
                    audit_report__audit_plan__audit_program__fiscal_year_id=fiscal_year
                )
            non_conformances = NonConformance.objects.filter(nc_filter)
            nc_by_status = {
                item['status']: item['count']
                for item in non_conformances.values('status').annotate(count=Count('id'))
            }
            pending_nc = non_conformances.exclude(
                status__in=['closed', 'withdrawn']
            ).count()

            # QMS Audit Stats
            qms_programs_total = QMSAuditProgram.objects.filter(fy_filter).count()
            qms_plans_total = QMSAuditPlan.objects.filter(
                base_filter, audit_program__in=QMSAuditProgram.objects.filter(fy_filter)
            ).count()
            qms_reports_total = QMSAuditReport.objects.filter(
                base_filter, audit_plan__audit_program__in=QMSAuditProgram.objects.filter(fy_filter)
            ).count()

            # ── Risk Meetings (SRS — workshops, brainstorming) ─────────────
            meetings_qs = RiskMeeting.objects.filter(fy_filter)
            meetings_total = meetings_qs.count()
            meetings_upcoming = meetings_qs.filter(
                meeting_date__gte=timezone.now()
            ).count()

            # ── Risk Surveys (SRS §4.11.1.1 #3) ───────────────────────────
            surveys_qs = RiskSurvey.objects.filter(fy_filter)
            surveys_total = surveys_qs.count()
            surveys_open = surveys_qs.filter(status='open').count()

            data = {
                "risk_champions": {
                    "total": total_rc,
                    "active": active_rc,
                },
                "assessments": {
                    "total": assessment_total,
                    "by_status": assessment_by_status,
                },
                "dept_registers": {
                    "total": sum(dept_by_status.values()),
                    "by_status": dept_by_status,
                },
                "inst_registers": {
                    "total": sum(inst_by_status.values()),
                    "by_status": inst_by_status,
                },
                "rtaps": {
                    "total": sum(rtap_by_status.values()),
                    "completion_rate": rtap_completion_rate,
                    "by_status": rtap_by_status,
                },
                "qpr_summary": qpr_summary,
                "qa_summary": {
                    "total_quality_auditors": total_qa,
                    "certified_quality_auditors": certified_qa,
                    "pending_nc_closures": pending_nc,
                    "qms_programs": qms_programs_total,
                    "qms_plans": qms_plans_total,
                    "qms_reports": qms_reports_total,
                },
                "non_conformances": {
                    "total": non_conformances.count(),
                    "by_status": nc_by_status,
                },
                "meetings": {
                    "total": meetings_total,
                    "upcoming": meetings_upcoming,
                },
                "surveys": {
                    "total": surveys_total,
                    "open": surveys_open,
                },
            }

            return Response({"success": True, "data": data})
        except Exception as e:
            logger.exception("Failed to generate risk dashboard")
            return server_error_response(message="Failed to generate risk dashboard")


class RiskDashboardComparativeAnalysisView(APIView):
    """Compare risk metrics across departments or fiscal years."""
    permission_classes = [IsAuthenticated, CanViewRiskDashboard]

    @method_decorator(cache_page(300))
    def get(self, request):
        try:
            compare_by = request.query_params.get('compare_by', 'department')
            fiscal_year = request.query_params.get('fiscal_year')

            base_filter = Q(is_active=True)
            if fiscal_year:
                base_filter = base_filter & Q(fiscal_year_id=fiscal_year)

            if compare_by == 'department':
                dept_data = (
                    DepartmentalRiskRegister.objects
                    .filter(base_filter)
                    .values('org_unit_id')
                    .annotate(
                        total=Count('id'),
                        draft=Count('id', filter=Q(status='draft')),
                        submitted=Count('id', filter=Q(status='submitted')),
                        approved=Count('id', filter=Q(status='approved')),
                    )
                )
                data = list(dept_data)
            elif compare_by == 'fiscal_year':
                fy_data = (
                    DepartmentalRiskRegister.objects
                    .filter(is_active=True)
                    .values('fiscal_year')
                    .annotate(
                        total=Count('id'),
                        draft=Count('id', filter=Q(status='draft')),
                        submitted=Count('id', filter=Q(status='submitted')),
                        approved=Count('id', filter=Q(status='approved')),
                    )
                )
                data = list(fy_data)
            else:
                data = []

            return Response({"success": True, "data": data})
        except Exception as e:
            logger.exception("Failed to generate comparative analysis")
            return server_error_response(message="Failed to generate comparative analysis")


class RiskDashboardExportView(APIView):
    """
    GAP-20: Export the risk dashboard as a PDF download.

    GET /risk/dashboard/export/?fiscal_year=<uuid>
    Returns application/pdf attachment.
    """
    permission_classes = [IsAuthenticated, CanViewRiskDashboard]

    def get(self, request):
        try:
            fiscal_year_id = request.query_params.get('fiscal_year')

            base_filter = Q(is_active=True)
            if fiscal_year_id:
                fy_filter = base_filter & Q(fiscal_year_id=fiscal_year_id)
            else:
                fy_filter = base_filter

            assessment_stats = RiskAssessmentSheet.objects.filter(fy_filter).aggregate(
                total=Count('id'),
            )
            dept_register_stats = (
                DepartmentalRiskRegister.objects.filter(fy_filter)
                .values('status').annotate(count=Count('id'))
            )
            inst_register_stats = (
                InstitutionalRiskRegister.objects.filter(fy_filter)
                .values('status').annotate(count=Count('id'))
            )
            rtap_stats = (
                RiskTreatmentActionPlan.objects.filter(fy_filter)
                .values('status').annotate(count=Count('id'))
            )

            nc_filter = base_filter
            if fiscal_year_id:
                nc_filter = base_filter & Q(
                    audit_report__audit_plan__audit_program__fiscal_year_id=fiscal_year_id
                )
            nc_stats = (
                NonConformance.objects.filter(nc_filter)
                .values('status').annotate(count=Count('id'))
            )

            data = {
                "assessments": assessment_stats,
                "dept_registers": {item['status']: item['count'] for item in dept_register_stats},
                "inst_registers": {item['status']: item['count'] for item in inst_register_stats},
                "rtaps": {item['status']: item['count'] for item in rtap_stats},
                "non_conformances": {item['status']: item['count'] for item in nc_stats},
            }

            fiscal_year = None
            if fiscal_year_id:
                from apps.core.models.lookups import FiscalYear
                fiscal_year = FiscalYear.objects.filter(pk=fiscal_year_id).first()

            from apps.core.utils.pdf_generators import generate_risk_dashboard_pdf
            pdf_bytes = generate_risk_dashboard_pdf(data, fiscal_year=fiscal_year)

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            fy_suffix = f"_{fiscal_year_id}" if fiscal_year_id else ""
            response['Content-Disposition'] = (
                f'attachment; filename="risk_dashboard{fy_suffix}.pdf"'
            )
            return response
        except Exception as e:
            logger.exception("Failed to export risk dashboard as PDF")
            return server_error_response(message="Failed to export risk dashboard")
