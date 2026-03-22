"""
Quality Auditor + Appointment CRUD + Workflow Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import QualityAuditor, QualityAuditorAppointment
from apps.api.serializers.risk_serializers import (
    QualityAuditorSerializer,
    QualityAuditorAppointmentSerializer,
)
from apps.api.permissions_jwt import CanManageQualityAuditor, HasAnyPermission
from apps.core.services.quality_auditor_service import QualityAuditorAppointmentService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── Quality Auditor CRUD ──────────────────────────────────────────────────


class QualityAuditorListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageQualityAuditor]

    def get(self, request):
        try:
            queryset = QualityAuditor.objects.filter(is_active=True)
            department = request.query_params.get('department')
            if department:
                queryset = queryset.filter(department_id=department)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'name'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QualityAuditorSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve quality auditors")
            return server_error_response(message="Failed to retrieve quality auditors")

    def post(self, request):
        try:
            serializer = QualityAuditorSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    auditor = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": QualityAuditorSerializer(auditor).data, "message": "Quality auditor created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create quality auditor")
            return server_error_response(message="Failed to create quality auditor")


class QualityAuditorDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageQualityAuditor]

    def get(self, request, pk):
        try:
            auditor = get_object_or_404(QualityAuditor, pk=pk)
            return Response({"success": True, "data": QualityAuditorSerializer(auditor).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve quality auditor")
            return server_error_response(message="Failed to retrieve quality auditor")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            auditor = get_object_or_404(QualityAuditor, pk=pk)
            serializer = QualityAuditorSerializer(auditor, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    auditor.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": QualityAuditorSerializer(updated).data, "message": "Quality auditor updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update quality auditor")
            return server_error_response(message="Failed to update quality auditor")

    def delete(self, request, pk):
        try:
            auditor = get_object_or_404(QualityAuditor, pk=pk)
            with transaction.atomic():
                auditor.is_active = False
                auditor.save()
            return Response({"success": True, "message": "Quality auditor deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete quality auditor")
            return server_error_response(message="Failed to delete quality auditor")


# ── Quality Auditor Appointment (sub-resource) ────────────────────────────


class QualityAuditorAppointmentListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageQualityAuditor]

    def get(self, request, pk):
        try:
            auditor = get_object_or_404(QualityAuditor, pk=pk)
            queryset = QualityAuditorAppointment.objects.select_related(
                'quality_auditor',
            ).filter(quality_auditor=auditor, is_active=True)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QualityAuditorAppointmentSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve auditor appointments")
            return server_error_response(message="Failed to retrieve auditor appointments")

    def post(self, request, pk):
        try:
            auditor = get_object_or_404(QualityAuditor, pk=pk)
            # GAP-13: Enforce is_certified pre-condition before appointment creation
            if not auditor.is_certified:
                return error_response(
                    message="Quality Auditor must pass the ISO exam before an appointment can be created.",
                    code="NOT_CERTIFIED",
                )
            serializer = QualityAuditorAppointmentSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    appointment = serializer.save(quality_auditor=auditor, created_by=user_id)
                return Response(
                    {"success": True, "data": QualityAuditorAppointmentSerializer(appointment).data, "message": "Appointment created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create auditor appointment")
            return server_error_response(message="Failed to create auditor appointment")


class QualityAuditorAppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageQualityAuditor]

    def get(self, request, pk):
        try:
            appointment = get_object_or_404(
                QualityAuditorAppointment.objects.select_related('quality_auditor'),
                pk=pk,
            )
            return Response({"success": True, "data": QualityAuditorAppointmentSerializer(appointment).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve auditor appointment")
            return server_error_response(message="Failed to retrieve auditor appointment")

    def patch(self, request, pk):
        try:
            appointment = get_object_or_404(QualityAuditorAppointment, pk=pk)
            serializer = QualityAuditorAppointmentSerializer(appointment, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    appointment.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": QualityAuditorAppointmentSerializer(updated).data, "message": "Appointment updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update auditor appointment")
            return server_error_response(message="Failed to update auditor appointment")

    def delete(self, request, pk):
        try:
            appointment = get_object_or_404(QualityAuditorAppointment, pk=pk)
            with transaction.atomic():
                appointment.is_active = False
                appointment.save()
            return Response({"success": True, "message": "Appointment deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete auditor appointment")
            return server_error_response(message="Failed to delete auditor appointment")


# ── Appointment Workflow Views ─────────────────────────────────────────────


class QAAppointmentWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated, CanManageQualityAuditor]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            service = QualityAuditorAppointmentService()
            appointment = service.submit_for_approval(appointment_id=str(pk), submitter_id=str(user_id))
            # Upload appointment letter PDF to DRS (non-blocking, outside atomic)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
            from apps.core.utils.risk_document_helpers import _upload_appointment_letter_pdf_to_drs
            _upload_appointment_letter_pdf_to_drs(appointment, auth_token=auth_token)
            appointment.refresh_from_db()
            return Response({"success": True, "data": QualityAuditorAppointmentSerializer(appointment).data, "message": "Workflow submitted"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to start workflow for auditor appointment %s", pk)
            return server_error_response(message="Failed to start workflow")


class QAAppointmentWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            workflow_data = QualityAuditorAppointmentService().get_workflow_status(str(pk))
            return Response({"success": True, "data": workflow_data})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get workflow status for auditor appointment %s", pk)
            return server_error_response(message="Failed to get workflow status")


class QAAppointmentWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            activity = QualityAuditorAppointmentService().get_workflow_history(str(pk))
            return Response({"success": True, "data": activity})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get workflow history for auditor appointment %s", pk)
            return server_error_response(message="Failed to get workflow history")


class QAAppointmentWorkflowAdvanceView(APIView):
    permission_classes = [IsAuthenticated, CanManageQualityAuditor]

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
            result = QualityAuditorAppointmentService().advance_workflow_stage(
                appointment_id=str(pk), action=action_name, actor_id=str(user_id), comment=request.data.get('comment', ''),
            )
            # After workflow advance, check if approved — re-upload + stamp
            from apps.core.models.risk_entities import QualityAuditorAppointment
            appointment = QualityAuditorAppointment.objects.get(pk=pk)
            if appointment.status == 'approved':
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
                from apps.core.utils.risk_document_helpers import _reupload_appointment_letter_pdf, stamp_risk_document
                _reupload_appointment_letter_pdf(appointment, auth_token=auth_token)
                stamp_risk_document(appointment, approver_id=str(user_id), entity_type='quality_auditor_appointment', auth_token=auth_token)
            return Response({"success": True, "data": result, "message": "Workflow advanced"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to advance workflow for auditor appointment %s", pk)
            return server_error_response(message="Failed to advance workflow")


class QAAppointmentWorkflowCancelView(APIView):
    permission_classes = [IsAuthenticated, CanManageQualityAuditor]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            QualityAuditorAppointmentService().cancel_workflow_plan(
                appointment_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', ''),
            )
            return Response({"success": True, "message": "Workflow cancelled"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to cancel workflow for auditor appointment %s", pk)
            return server_error_response(message="Failed to cancel workflow")


class QAAppointmentWorkflowRecallView(APIView):
    permission_classes = [IsAuthenticated, CanManageQualityAuditor]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            appointment = get_object_or_404(QualityAuditorAppointment.objects.select_for_update(), pk=pk)
            if appointment.status == 'draft':
                return error_response(message="Cannot recall a draft appointment", status_code=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                QualityAuditorAppointmentService().cancel_workflow_plan(
                    appointment_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', 'Recalled for rework'),
                )
                appointment.refresh_from_db()
                appointment.clear_workflow()
                appointment.status = 'draft'
                appointment.rework_count = getattr(appointment, 'rework_count', 0) + 1
                appointment.save()
            return Response({"success": True, "data": QualityAuditorAppointmentSerializer(appointment).data, "message": "Appointment recalled"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to recall auditor appointment %s", pk)
            return server_error_response(message="Failed to recall appointment")
