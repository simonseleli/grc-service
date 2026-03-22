"""
QMS Audit Report CRUD + Signing Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import QMSAuditReport
from apps.api.serializers.risk_serializers import QMSAuditReportSerializer
from apps.api.permissions_jwt import (
    CanManageQMSAuditReport,
    CanSignQMSAuditReport,
    HasAnyPermission,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── QMS Audit Report CRUD ─────────────────────────────────────────────────


class QMSAuditReportListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:qms_audit_report:manage', 'grc:qms_audit_report:sign']).has_permission(request, self):
                self.permission_denied(request, message='QMS audit report permission required.')
        elif request.method == 'POST':
            if not CanManageQMSAuditReport().has_permission(request, self):
                self.permission_denied(request, message='grc:qms_audit_report:manage required.')

    def get(self, request):
        try:
            queryset = QMSAuditReport.objects.select_related('audit_plan').filter(is_active=True)

            plan = request.query_params.get('audit_plan')
            status_filter = request.query_params.get('status')
            if plan:
                queryset = queryset.filter(audit_plan_id=plan)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QMSAuditReportSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve QMS audit reports")
            return server_error_response(message="Failed to retrieve QMS audit reports")

    def post(self, request):
        try:
            serializer = QMSAuditReportSerializer(data=request.data)
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
                    {"success": True, "data": QMSAuditReportSerializer(report).data, "message": "QMS audit report created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create QMS audit report")
            return server_error_response(message="Failed to create QMS audit report")


class QMSAuditReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:qms_audit_report:manage', 'grc:qms_audit_report:sign']).has_permission(request, self):
                self.permission_denied(request, message='QMS audit report permission required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageQMSAuditReport().has_permission(request, self):
                self.permission_denied(request, message='grc:qms_audit_report:manage required.')

    def get(self, request, pk):
        try:
            report = get_object_or_404(QMSAuditReport.objects.select_related('audit_plan'), pk=pk)
            return Response({"success": True, "data": QMSAuditReportSerializer(report).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve QMS audit report")
            return server_error_response(message="Failed to retrieve QMS audit report")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            report = get_object_or_404(QMSAuditReport, pk=pk)
            serializer = QMSAuditReportSerializer(report, data=request.data, partial=partial)
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
                return Response({"success": True, "data": QMSAuditReportSerializer(updated).data, "message": "QMS audit report updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update QMS audit report")
            return server_error_response(message="Failed to update QMS audit report")

    def delete(self, request, pk):
        try:
            report = get_object_or_404(QMSAuditReport, pk=pk)
            with transaction.atomic():
                report.is_active = False
                report.save()
            return Response({"success": True, "message": "QMS audit report deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete QMS audit report")
            return server_error_response(message="Failed to delete QMS audit report")


# ── Signing Views ──────────────────────────────────────────────────────────


class QMSAuditReportSignTLView(APIView):
    """Team Leader signs the audit report."""
    permission_classes = [IsAuthenticated, CanSignQMSAuditReport]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            with transaction.atomic():
                report = get_object_or_404(QMSAuditReport.objects.select_for_update(), pk=pk)
                if report.tl_signed_by:
                    return error_response(message="Report already signed by team leader", status_code=status.HTTP_400_BAD_REQUEST)
                report.tl_signed_by = str(user_id)
                report.tl_signed_at = timezone.now()
                report.modified_by = user_id
                report.save()
            # Upload QMS audit report PDF to DRS (non-blocking, outside atomic)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
            from apps.core.utils.risk_document_helpers import _upload_qms_audit_report_pdf_to_drs, stamp_risk_document
            _upload_qms_audit_report_pdf_to_drs(report, auth_token=auth_token)
            # If both signatures present, stamp the document
            report.refresh_from_db()
            if report.tl_signed_by and report.auditee_signed_by:
                stamp_risk_document(report, approver_id=str(user_id), entity_type='qms_audit_report', auth_token=auth_token)
                report.refresh_from_db()
            return Response({"success": True, "data": QMSAuditReportSerializer(report).data, "message": "Report signed by team leader"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to sign report (TL) %s", pk)
            return server_error_response(message="Failed to sign report")


class QMSAuditReportSignAuditeeView(APIView):
    """Auditee signs the audit report."""
    permission_classes = [IsAuthenticated, CanSignQMSAuditReport]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            with transaction.atomic():
                report = get_object_or_404(QMSAuditReport.objects.select_for_update(), pk=pk)
                if report.auditee_signed_by:
                    return error_response(message="Report already signed by auditee", status_code=status.HTTP_400_BAD_REQUEST)
                report.auditee_signed_by = str(user_id)
                report.auditee_signed_at = timezone.now()
                report.modified_by = user_id
                report.save()
            # Re-upload QMS audit report PDF to DRS (non-blocking, outside atomic)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
            from apps.core.utils.risk_document_helpers import _upload_qms_audit_report_pdf_to_drs, stamp_risk_document
            _upload_qms_audit_report_pdf_to_drs(report, auth_token=auth_token)
            # If both signatures present, stamp the document
            report.refresh_from_db()
            if report.tl_signed_by and report.auditee_signed_by:
                stamp_risk_document(report, approver_id=str(user_id), entity_type='qms_audit_report', auth_token=auth_token)
                report.refresh_from_db()
            return Response({"success": True, "data": QMSAuditReportSerializer(report).data, "message": "Report signed by auditee"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to sign report (auditee) %s", pk)
            return server_error_response(message="Failed to sign report")


# ── GAP-12/25/26: QMS Report Post-Finalisation Governance Views ───────────────

def _qms_report_transition(request, pk, target_status, required_from, extra_callback=None):
    """Shared helper for QMS Audit Report status transitions."""
    user_id = getattr(request.user, 'id', None)
    if not user_id:
        return Response(
            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    try:
        with transaction.atomic():
            report = get_object_or_404(QMSAuditReport.objects.select_for_update(), pk=pk)
            if report.status not in required_from:
                return error_response(
                    message=f"Cannot transition from '{report.status}' to '{target_status}'. "
                            f"Allowed from: {required_from}",
                    code="INVALID_STATUS_TRANSITION",
                )
            if extra_callback:
                err = extra_callback(request, report, user_id)
                if err:
                    return err
            report.status = target_status
            report.modified_by = user_id
            report.save()
        return Response({
            "success": True,
            "data": QMSAuditReportSerializer(report).data,
            "message": f"QMS audit report status updated to '{target_status}'",
        })
    except Http404:
        raise
    except Exception as e:
        logger.exception("Failed to transition QMS report to %s", target_status)
        return server_error_response(message="Failed to update QMS audit report status")


class QMSReportSubmitToRMQAMView(APIView):
    """Submit finalised report to RMQAM. finalised → submitted_to_rmqam."""
    permission_classes = [IsAuthenticated, CanManageQMSAuditReport]

    def post(self, request, pk):
        return _qms_report_transition(
            request, pk,
            target_status='submitted_to_rmqam',
            required_from=['finalised'],
        )


class QMSReportReturnForRevisionView(APIView):
    """RMQAM returns report for revision. submitted_to_rmqam → returned_for_revision."""
    permission_classes = [IsAuthenticated, CanManageQMSAuditReport]

    def post(self, request, pk):
        def set_revision_fields(req, report, user_id):
            comments = req.data.get('rmqam_review_comments', '').strip()
            if not comments:
                return error_response(message="'rmqam_review_comments' is required.", code="COMMENTS_REQUIRED")
            report.rmqam_review_comments = comments
            report.returned_for_revision_at = timezone.now()
            return None

        return _qms_report_transition(
            request, pk,
            target_status='returned_for_revision',
            required_from=['submitted_to_rmqam'],
            extra_callback=set_revision_fields,
        )


class QMSReportPresentAtMRMView(APIView):
    """Mark report as presented at MRM. submitted_to_rmqam|returned_for_revision → presented_at_mrm."""
    permission_classes = [IsAuthenticated, CanManageQMSAuditReport]

    def post(self, request, pk):
        return _qms_report_transition(
            request, pk,
            target_status='presented_at_mrm',
            required_from=['submitted_to_rmqam', 'returned_for_revision'],
        )


class QMSReportRecordDirectivesView(APIView):
    """Record MRM directives. presented_at_mrm → directives_received."""
    permission_classes = [IsAuthenticated, CanManageQMSAuditReport]

    def post(self, request, pk):
        def set_directive_fields(req, report, user_id):
            directives = req.data.get('mrm_directives', '').strip()
            if not directives:
                return error_response(message="'mrm_directives' is required.", code="DIRECTIVES_REQUIRED")
            report.mrm_directives = directives
            report.mrm_directives_communicated_at = timezone.now()
            return None

        return _qms_report_transition(
            request, pk,
            target_status='directives_received',
            required_from=['presented_at_mrm'],
            extra_callback=set_directive_fields,
        )


class QMSReportSubmitToAuditCommitteeView(APIView):
    """Submit to audit committee. directives_received → submitted_to_audit_committee."""
    permission_classes = [IsAuthenticated, CanManageQMSAuditReport]

    def post(self, request, pk):
        return _qms_report_transition(
            request, pk,
            target_status='submitted_to_audit_committee',
            required_from=['directives_received'],
        )


class QMSReportAuditCommitteeReviewView(APIView):
    """Audit committee reviews. submitted_to_audit_committee → audit_committee_reviewed."""
    permission_classes = [IsAuthenticated, CanManageQMSAuditReport]

    def post(self, request, pk):
        return _qms_report_transition(
            request, pk,
            target_status='audit_committee_reviewed',
            required_from=['submitted_to_audit_committee'],
        )


class QMSReportAdoptByCommissionView(APIView):
    """Commission adopts report. audit_committee_reviewed → adopted_by_commission."""
    permission_classes = [IsAuthenticated, CanManageQMSAuditReport]

    def post(self, request, pk):
        return _qms_report_transition(
            request, pk,
            target_status='adopted_by_commission',
            required_from=['audit_committee_reviewed'],
        )
