"""
Quarterly Performance Report CRUD + Workflow Views
"""
import logging

from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import QuarterlyPerformanceReport
from apps.api.serializers.risk_serializers import QuarterlyPerformanceReportSerializer
from apps.api.permissions_jwt import (
    CanManageQuarterlyRiskReport,
    CanApproveQuarterlyRiskReport,
    HasAnyPermission,
)
from apps.core.services.quarterly_risk_report_service import QuarterlyRiskReportService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── Quarterly Performance Report CRUD ──────────────────────────────────────


class QuarterlyReportListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:quarterly_risk_report:manage', 'grc:quarterly_risk_report:approve']).has_permission(request, self):
                self.permission_denied(request, message='Quarterly report permission required.')
        elif request.method == 'POST':
            if not CanManageQuarterlyRiskReport().has_permission(request, self):
                self.permission_denied(request, message='grc:quarterly_risk_report:manage required.')

    def get(self, request):
        try:
            queryset = QuarterlyPerformanceReport.objects.select_related(
                'fiscal_year', 'quarter',
            ).filter(is_active=True)

            org_unit = request.query_params.get('org_unit')
            fiscal_year = request.query_params.get('fiscal_year')
            quarter = request.query_params.get('quarter')
            status_filter = request.query_params.get('status')

            if org_unit:
                queryset = queryset.filter(org_unit_id=org_unit)
            if fiscal_year:
                queryset = queryset.filter(fiscal_year_id=fiscal_year)
            if quarter:
                queryset = queryset.filter(quarter_id=quarter)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QuarterlyPerformanceReportSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve quarterly reports")
            return server_error_response(message="Failed to retrieve quarterly reports")

    def post(self, request):
        try:
            serializer = QuarterlyPerformanceReportSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    report = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": QuarterlyPerformanceReportSerializer(report).data, "message": "Quarterly report created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create quarterly report")
            return server_error_response(message="Failed to create quarterly report")


class QuarterlyReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:quarterly_risk_report:manage', 'grc:quarterly_risk_report:approve']).has_permission(request, self):
                self.permission_denied(request, message='Quarterly report permission required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageQuarterlyRiskReport().has_permission(request, self):
                self.permission_denied(request, message='grc:quarterly_risk_report:manage required.')

    def get(self, request, pk):
        try:
            report = get_object_or_404(
                QuarterlyPerformanceReport.objects.select_related('fiscal_year', 'quarter'),
                pk=pk,
            )
            return Response({"success": True, "data": QuarterlyPerformanceReportSerializer(report).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve quarterly report")
            return server_error_response(message="Failed to retrieve quarterly report")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            report = get_object_or_404(QuarterlyPerformanceReport, pk=pk)
            serializer = QuarterlyPerformanceReportSerializer(report, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    report.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": QuarterlyPerformanceReportSerializer(updated).data, "message": "Quarterly report updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update quarterly report")
            return server_error_response(message="Failed to update quarterly report")

    def delete(self, request, pk):
        try:
            report = get_object_or_404(QuarterlyPerformanceReport, pk=pk)
            with transaction.atomic():
                report.is_active = False
                report.save()
            return Response({"success": True, "message": "Quarterly report deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete quarterly report")
            return server_error_response(message="Failed to delete quarterly report")


class QPRExportView(APIView):
    """
    GAP-20: Download a Quarterly Performance Report as PDF.

    GET /risk/quarterly-reports/:id/export/
    Returns application/pdf attachment.
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:quarterly_risk_report:manage',
            'grc:quarterly_risk_report:approve',
        ]).has_permission(request, self):
            self.permission_denied(request, message='Quarterly report permission required.')

    def get(self, request, pk):
        try:
            report = get_object_or_404(QuarterlyPerformanceReport, pk=pk, is_active=True)
            from apps.core.utils.pdf_generators import generate_quarterly_report_pdf
            pdf_bytes = generate_quarterly_report_pdf(report)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="quarterly_report_{report.id}.pdf"'
            )
            return response
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to export QPR %s as PDF", pk)
            return server_error_response(message="Failed to export quarterly report")


# ── Workflow Views ─────────────────────────────────────────────────────────


class QuarterlyReportWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated, CanManageQuarterlyRiskReport]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            # SRS-FIX G-09: Snapshot live metrics before submitting for approval
            report = get_object_or_404(QuarterlyPerformanceReport, pk=pk)
            report.snapshot_metrics()
            service = QuarterlyRiskReportService()
            report = service.submit_for_approval(report_id=str(pk), submitter_id=str(user_id))
            # Upload QPR PDF to DRS (non-blocking, outside atomic)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
            from apps.core.utils.risk_document_helpers import _upload_quarterly_report_pdf_to_drs
            _upload_quarterly_report_pdf_to_drs(report, auth_token=auth_token)
            report.refresh_from_db()
            return Response({"success": True, "data": QuarterlyPerformanceReportSerializer(report).data, "message": "Workflow submitted"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to start workflow for quarterly report %s", pk)
            return server_error_response(message="Failed to start workflow")


class QuarterlyReportWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            workflow_data = QuarterlyRiskReportService().get_workflow_status(str(pk))
            return Response({"success": True, "data": workflow_data})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get workflow status for quarterly report %s", pk)
            return server_error_response(message="Failed to get workflow status")


class QuarterlyReportWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            activity = QuarterlyRiskReportService().get_workflow_history(str(pk))
            return Response({"success": True, "data": activity})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get workflow history for quarterly report %s", pk)
            return server_error_response(message="Failed to get workflow history")


class QuarterlyReportWorkflowAdvanceView(APIView):
    permission_classes = [IsAuthenticated, CanApproveQuarterlyRiskReport]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            action_name = request.data.get('action', '')
            if not action_name:
                return error_response(message="'action' is required", status_code=status.HTTP_400_BAD_REQUEST)
            result = QuarterlyRiskReportService().advance_workflow_stage(
                report_id=str(pk), action=action_name, actor_id=str(user_id), comment=request.data.get('comment', ''),
            )
            # After workflow advance, check if approved — re-upload + stamp
            report = QuarterlyPerformanceReport.objects.get(pk=pk)
            if report.status == 'approved':
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
                from apps.core.utils.risk_document_helpers import _upload_quarterly_report_pdf_to_drs, stamp_risk_document
                _upload_quarterly_report_pdf_to_drs(report, auth_token=auth_token)
                stamp_risk_document(report, approver_id=str(user_id), entity_type='quarterly_performance_report', auth_token=auth_token)
            return Response({"success": True, "data": result, "message": "Workflow advanced"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to advance workflow for quarterly report %s", pk)
            return server_error_response(message="Failed to advance workflow")


class QuarterlyReportWorkflowCancelView(APIView):
    permission_classes = [IsAuthenticated, CanManageQuarterlyRiskReport]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            QuarterlyRiskReportService().cancel_workflow_plan(report_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', ''))
            return Response({"success": True, "message": "Workflow cancelled"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to cancel workflow for quarterly report %s", pk)
            return server_error_response(message="Failed to cancel workflow")


class QuarterlyReportWorkflowRecallView(APIView):
    permission_classes = [IsAuthenticated, CanManageQuarterlyRiskReport]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            report = get_object_or_404(QuarterlyPerformanceReport.objects.select_for_update(), pk=pk)
            if report.status == 'draft':
                return error_response(message="Cannot recall a draft report", status_code=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                QuarterlyRiskReportService().cancel_workflow_plan(report_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', 'Recalled for rework'))
                report.refresh_from_db()
                report.clear_workflow()
                report.status = 'draft'
                report.rework_count = getattr(report, 'rework_count', 0) + 1
                report.save()
            return Response({"success": True, "data": QuarterlyPerformanceReportSerializer(report).data, "message": "Report recalled"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to recall quarterly report %s", pk)
            return server_error_response(message="Failed to recall report")
