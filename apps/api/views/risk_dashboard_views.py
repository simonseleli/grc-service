"""
Risk Dashboard + Comparative Analysis Views (read-only)
"""
import logging

from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import (
    RiskAssessmentSheet,
    DepartmentalRiskRegister,
    InstitutionalRiskRegister,
    RiskTreatmentActionPlan,
    NonConformance,
    QuarterlyPerformanceReport,
)
from apps.api.permissions_jwt import CanViewRiskDashboard
from apps.api.utils.response_helpers import server_error_response

logger = logging.getLogger(__name__)


class RiskDashboardView(APIView):
    """Aggregated risk management dashboard statistics."""
    permission_classes = [IsAuthenticated, CanViewRiskDashboard]

    def get(self, request):
        try:
            fiscal_year = request.query_params.get('fiscal_year')

            base_filter = Q(is_active=True)
            if fiscal_year:
                fy_filter = base_filter & Q(fiscal_year_id=fiscal_year)
            else:
                fy_filter = base_filter

            assessments = RiskAssessmentSheet.objects.filter(fy_filter)
            assessment_stats = assessments.aggregate(
                total=Count('id'),
            )

            dept_registers = DepartmentalRiskRegister.objects.filter(fy_filter)
            dept_register_stats = dept_registers.values('status').annotate(count=Count('id'))

            inst_registers = InstitutionalRiskRegister.objects.filter(fy_filter)
            inst_register_stats = inst_registers.values('status').annotate(count=Count('id'))

            rtaps = RiskTreatmentActionPlan.objects.filter(fy_filter)
            rtap_stats = rtaps.values('status').annotate(count=Count('id'))

            nc_filter = base_filter
            if fiscal_year:
                nc_filter = base_filter & Q(audit_report__audit_plan__audit_program__fiscal_year_id=fiscal_year)
            non_conformances = NonConformance.objects.filter(nc_filter)
            nc_stats = non_conformances.values('status').annotate(count=Count('id'))

            data = {
                "assessments": assessment_stats,
                "dept_registers": {item['status']: item['count'] for item in dept_register_stats},
                "inst_registers": {item['status']: item['count'] for item in inst_register_stats},
                "rtaps": {item['status']: item['count'] for item in rtap_stats},
                "non_conformances": {item['status']: item['count'] for item in nc_stats},
            }

            return Response({"success": True, "data": data})
        except Exception as e:
            logger.exception("Failed to generate risk dashboard")
            return server_error_response(message="Failed to generate risk dashboard")


class RiskDashboardComparativeAnalysisView(APIView):
    """Compare risk metrics across departments or fiscal years."""
    permission_classes = [IsAuthenticated, CanViewRiskDashboard]

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
