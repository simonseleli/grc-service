"""
QMS Audit Program CRUD + Workflow Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import QMSAuditProgram
from apps.api.serializers.risk_serializers import QMSAuditProgramSerializer
from apps.api.permissions_jwt import (
    CanManageQMSAuditProgram,
    CanApproveQMSAuditProgram,
    HasAnyPermission,
)
from apps.core.services.qms_audit_program_service import QMSAuditProgramService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── QMS Audit Program CRUD ────────────────────────────────────────────────


class QMSAuditProgramListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:qms_audit_program:manage', 'grc:qms_audit_program:approve']).has_permission(request, self):
                self.permission_denied(request, message='QMS audit program permission required.')
        elif request.method == 'POST':
            if not CanManageQMSAuditProgram().has_permission(request, self):
                self.permission_denied(request, message='grc:qms_audit_program:manage required.')

    def get(self, request):
        try:
            queryset = QMSAuditProgram.objects.select_related('fiscal_year').filter(is_active=True)

            fiscal_year = request.query_params.get('fiscal_year')
            status_filter = request.query_params.get('status')
            if fiscal_year:
                queryset = queryset.filter(fiscal_year_id=fiscal_year)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QMSAuditProgramSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve QMS audit programs")
            return server_error_response(message="Failed to retrieve QMS audit programs")

    def post(self, request):
        try:
            serializer = QMSAuditProgramSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    program = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": QMSAuditProgramSerializer(program).data, "message": "QMS audit program created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create QMS audit program")
            return server_error_response(message="Failed to create QMS audit program")


class QMSAuditProgramDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:qms_audit_program:manage', 'grc:qms_audit_program:approve']).has_permission(request, self):
                self.permission_denied(request, message='QMS audit program permission required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageQMSAuditProgram().has_permission(request, self):
                self.permission_denied(request, message='grc:qms_audit_program:manage required.')

    def get(self, request, pk):
        try:
            program = get_object_or_404(QMSAuditProgram.objects.select_related('fiscal_year'), pk=pk)
            return Response({"success": True, "data": QMSAuditProgramSerializer(program).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve QMS audit program")
            return server_error_response(message="Failed to retrieve QMS audit program")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            program = get_object_or_404(QMSAuditProgram, pk=pk)
            serializer = QMSAuditProgramSerializer(program, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    program.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": QMSAuditProgramSerializer(updated).data, "message": "QMS audit program updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update QMS audit program")
            return server_error_response(message="Failed to update QMS audit program")

    def delete(self, request, pk):
        try:
            program = get_object_or_404(QMSAuditProgram, pk=pk)
            with transaction.atomic():
                program.is_active = False
                program.save()
            return Response({"success": True, "message": "QMS audit program deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete QMS audit program")
            return server_error_response(message="Failed to delete QMS audit program")


# ── Workflow Views ─────────────────────────────────────────────────────────


class QMSAuditProgramWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditProgram]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            service = QMSAuditProgramService()
            program = service.submit_for_approval(program_id=str(pk), submitter_id=str(user_id))
            return Response({"success": True, "data": QMSAuditProgramSerializer(program).data, "message": "Workflow submitted"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to start workflow for QMS audit program %s", pk)
            return server_error_response(message="Failed to start workflow")


class QMSAuditProgramWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            workflow_data = QMSAuditProgramService().get_workflow_status(str(pk))
            return Response({"success": True, "data": workflow_data})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get workflow status for QMS audit program %s", pk)
            return server_error_response(message="Failed to get workflow status")


class QMSAuditProgramWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            activity = QMSAuditProgramService().get_workflow_history(str(pk))
            return Response({"success": True, "data": activity})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get workflow history for QMS audit program %s", pk)
            return server_error_response(message="Failed to get workflow history")


class QMSAuditProgramWorkflowAdvanceView(APIView):
    permission_classes = [IsAuthenticated, CanApproveQMSAuditProgram]

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
            result = QMSAuditProgramService().advance_workflow_stage(
                program_id=str(pk), action=action_name, actor_id=str(user_id), comment=request.data.get('comment', ''),
            )
            return Response({"success": True, "data": result, "message": "Workflow advanced"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to advance workflow for QMS audit program %s", pk)
            return server_error_response(message="Failed to advance workflow")


class QMSAuditProgramWorkflowCancelView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditProgram]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            QMSAuditProgramService().cancel_workflow_plan(program_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', ''))
            return Response({"success": True, "message": "Workflow cancelled"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to cancel workflow for QMS audit program %s", pk)
            return server_error_response(message="Failed to cancel workflow")


class QMSAuditProgramWorkflowRecallView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditProgram]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            program = get_object_or_404(QMSAuditProgram.objects.select_for_update(), pk=pk)
            if program.status == 'draft':
                return error_response(message="Cannot recall a draft program", status_code=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                QMSAuditProgramService().cancel_workflow_plan(program_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', 'Recalled for rework'))
                program.refresh_from_db()
                program.clear_workflow()
                program.status = 'draft'
                program.rework_count = getattr(program, 'rework_count', 0) + 1
                program.save()
            return Response({"success": True, "data": QMSAuditProgramSerializer(program).data, "message": "Program recalled"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to recall QMS audit program %s", pk)
            return server_error_response(message="Failed to recall program")
