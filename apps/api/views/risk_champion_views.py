"""
Risk Champion & Appointment CRUD + Workflow Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import RiskChampion, RiskChampionAppointment
from apps.api.serializers.risk_serializers import (
    RiskChampionSerializer,
    RiskChampionAppointmentSerializer,
)
from apps.api.permissions_jwt import (
    CanViewRiskChampion,
    CanManageRiskChampion,
    HasAnyPermission,
)
from apps.core.services.risk_champion_service import RiskChampionAppointmentService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    error_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── Risk Champion CRUD ─────────────────────────────────────────────────────


class RiskChampionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewRiskChampion().has_permission(request, self)
            can_manage = CanManageRiskChampion().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:risk_champion:view or grc:risk_champion:manage required.')
        elif request.method == 'POST':
            if not CanManageRiskChampion().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_champion:manage required.')

    def get(self, request):
        try:
            org_unit_id = request.query_params.get('org_unit_id')
            org_unit_type = request.query_params.get('org_unit_type')
            status_filter = request.query_params.get('status')

            queryset = RiskChampion.objects.filter(is_active=True)

            if org_unit_id:
                queryset = queryset.filter(org_unit_id=org_unit_id)
            if org_unit_type:
                queryset = queryset.filter(org_unit_type=org_unit_type)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'term_start', 'org_unit_type'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskChampionSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk champions")
            return server_error_response(message="Failed to retrieve risk champions")

    def post(self, request):
        try:
            serializer = RiskChampionSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    champion = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": RiskChampionSerializer(champion).data, "message": "Risk champion created successfully"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Exception as e:
            logger.exception("Failed to create risk champion")
            return server_error_response(message="Failed to create risk champion")


class RiskChampionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewRiskChampion().has_permission(request, self)
            can_manage = CanManageRiskChampion().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:risk_champion:view or grc:risk_champion:manage required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageRiskChampion().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_champion:manage required.')

    def get(self, request, pk):
        try:
            champion = get_object_or_404(RiskChampion, pk=pk)
            return Response({"success": True, "data": RiskChampionSerializer(champion).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve risk champion")
            return server_error_response(message="Failed to retrieve risk champion")

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            champion = get_object_or_404(RiskChampion, pk=pk)
            serializer = RiskChampionSerializer(champion, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    champion.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RiskChampionSerializer(updated).data, "message": "Risk champion updated successfully"})
            return validation_error_response(errors=serializer.errors)
        except Exception as e:
            logger.exception("Failed to update risk champion")
            return server_error_response(message="Failed to update risk champion")

    def delete(self, request, pk):
        try:
            champion = get_object_or_404(RiskChampion, pk=pk)
            active_appointments = champion.appointments.filter(is_active=True).count()
            if active_appointments > 0:
                return error_response(
                    message=f"Cannot delete champion with {active_appointments} active appointment(s)",
                    code="HAS_ACTIVE_APPOINTMENTS",
                )
            with transaction.atomic():
                champion.is_active = False
                champion.save()
            return Response({"success": True, "message": "Risk champion deleted successfully"})
        except Exception as e:
            logger.exception("Failed to delete risk champion")
            return server_error_response(message="Failed to delete risk champion")


# ── Risk Champion Appointment CRUD ─────────────────────────────────────────


class RiskChampionAppointmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewRiskChampion().has_permission(request, self)
            can_manage = CanManageRiskChampion().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:risk_champion:view or grc:risk_champion:manage required.')
        elif request.method == 'POST':
            if not CanManageRiskChampion().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_champion:manage required.')

    def get(self, request, pk):
        try:
            champion = get_object_or_404(RiskChampion, pk=pk)
            queryset = RiskChampionAppointment.objects.select_related('risk_champion').filter(
                risk_champion=champion, is_active=True,
            )
            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'appointment_date', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskChampionAppointmentSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk champion appointments")
            return server_error_response(message="Failed to retrieve appointments")

    def post(self, request, pk):
        try:
            champion = get_object_or_404(RiskChampion, pk=pk)
            serializer = RiskChampionAppointmentSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    appointment = serializer.save(risk_champion=champion, created_by=user_id)
                return Response(
                    {"success": True, "data": RiskChampionAppointmentSerializer(appointment).data, "message": "Appointment created successfully"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Exception as e:
            logger.exception("Failed to create risk champion appointment")
            return server_error_response(message="Failed to create appointment")


class RiskChampionAppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewRiskChampion().has_permission(request, self)
            can_manage = CanManageRiskChampion().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:risk_champion:view or grc:risk_champion:manage required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageRiskChampion().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_champion:manage required.')

    def get(self, request, pk):
        try:
            appointment = get_object_or_404(
                RiskChampionAppointment.objects.select_related('risk_champion'), pk=pk,
            )
            return Response({"success": True, "data": RiskChampionAppointmentSerializer(appointment).data})
        except Exception as e:
            logger.exception("Failed to retrieve appointment")
            return server_error_response(message="Failed to retrieve appointment")

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            appointment = get_object_or_404(RiskChampionAppointment, pk=pk)
            serializer = RiskChampionAppointmentSerializer(appointment, data=request.data, partial=partial)
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
                return Response({"success": True, "data": RiskChampionAppointmentSerializer(updated).data, "message": "Appointment updated successfully"})
            return validation_error_response(errors=serializer.errors)
        except Exception as e:
            logger.exception("Failed to update appointment")
            return server_error_response(message="Failed to update appointment")

    def delete(self, request, pk):
        try:
            appointment = get_object_or_404(RiskChampionAppointment, pk=pk)
            if appointment.workflow_plan_id and not appointment.workflow_completed_at:
                return error_response(message="Cannot delete appointment with active workflow", code="ACTIVE_WORKFLOW")
            with transaction.atomic():
                appointment.is_active = False
                appointment.save()
            return Response({"success": True, "message": "Appointment deleted successfully"})
        except Exception as e:
            logger.exception("Failed to delete appointment")
            return server_error_response(message="Failed to delete appointment")


# ── Risk Champion Appointment Workflow Views ───────────────────────────────


class RiskChampionAppointmentWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRiskChampion().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_champion:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            appointment = get_object_or_404(RiskChampionAppointment, pk=pk)
            if appointment.status not in ('draft',):
                return error_response(
                    message=f"Only draft appointments can be submitted. Current status: '{appointment.status}'",
                    code="INVALID_STATUS",
                )
            if appointment.workflow_plan_id:
                return Response(
                    {"success": False, "error": {"message": "Workflow already in progress", "code": "WORKFLOW_ALREADY_STARTED", "workflow_plan_id": str(appointment.workflow_plan_id)}},
                    status=status.HTTP_409_CONFLICT,
                )
            service = RiskChampionAppointmentService()
            appointment = service.submit_for_approval(
                appointment_id=str(pk), submitter_id=str(user_id),
            )
            # Upload appointment letter PDF to DRS (non-blocking, outside atomic)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
            from apps.core.utils.risk_document_helpers import _upload_appointment_letter_pdf_to_drs
            _upload_appointment_letter_pdf_to_drs(appointment, auth_token=auth_token)
            appointment.refresh_from_db()
            return Response(
                {"success": True, "data": RiskChampionAppointmentSerializer(appointment).data, "message": "Appointment submitted for approval", "workflow_plan_id": str(appointment.workflow_plan_id) if appointment.workflow_plan_id else None},
            )
        except Exception as e:
            logger.exception("Failed to start appointment workflow")
            return server_error_response(message="Failed to start appointment workflow")


class RiskChampionAppointmentWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewRiskChampion().has_permission(request, self) or CanManageRiskChampion().has_permission(request, self)):
            self.permission_denied(request, message='grc:risk_champion:view or :manage required.')

    def get(self, request, pk):
        try:
            appointment = get_object_or_404(RiskChampionAppointment, pk=pk)
            if not appointment.workflow_plan_id:
                return Response({"success": True, "data": {"has_workflow": False, "status": appointment.status}})
            workflow_data = RiskChampionAppointmentService().get_workflow_status(str(pk))
            return Response({"success": True, "data": workflow_data})
        except Exception as e:
            logger.exception("Failed to get workflow status")
            return Response(
                {"success": False, "error": {"message": "Failed to retrieve workflow status", "details": str(e)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class RiskChampionAppointmentWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewRiskChampion().has_permission(request, self) or CanManageRiskChampion().has_permission(request, self)):
            self.permission_denied(request, message='grc:risk_champion:view or :manage required.')

    def get(self, request, pk):
        try:
            appointment = get_object_or_404(RiskChampionAppointment, pk=pk)
            if not appointment.workflow_plan_id:
                return Response({"success": True, "data": {"has_workflow": False, "activities": []}})
            activity = RiskChampionAppointmentService().get_workflow_history(str(pk))
            return Response({"success": True, "data": {"has_workflow": True, "workflow_plan_id": str(appointment.workflow_plan_id), "activities": activity}})
        except Exception as e:
            logger.exception("Failed to get workflow history")
            return Response(
                {"success": False, "error": {"message": "Failed to retrieve workflow history", "details": str(e)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class RiskChampionAppointmentWorkflowAdvanceView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:risk_champion:manage', 'grc:risk_champion:view']).has_permission(request, self):
            self.permission_denied(request, message='grc:risk_champion:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        action_name = request.data.get('action')
        if not action_name:
            return error_response(message="'action' is required", code="ACTION_REQUIRED")
        try:
            result = RiskChampionAppointmentService().advance_workflow_stage(
                appointment_id=str(pk), action=action_name,
                actor_id=str(user_id), comment=request.data.get('comment', ''),
            )
            # After workflow advance, check if approved — re-upload + stamp
            appointment = RiskChampionAppointment.objects.get(pk=pk)
            if appointment.status == 'approved':
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
                from apps.core.utils.risk_document_helpers import _reupload_appointment_letter_pdf, stamp_risk_document
                _reupload_appointment_letter_pdf(appointment, auth_token=auth_token)
                stamp_risk_document(appointment, approver_id=str(user_id), entity_type='risk_champion_appointment', auth_token=auth_token)
            return Response({"success": True, "data": result})
        except ValueError as e:
            return error_response(message=str(e), code="WORKFLOW_ACTION_FAILED")
        except Exception as e:
            logger.exception("Failed to advance appointment workflow")
            return Response(
                {"success": False, "error": {"message": "Failed to execute workflow action", "details": str(e)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class RiskChampionAppointmentWorkflowCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRiskChampion().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_champion:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            RiskChampionAppointmentService().cancel_workflow_plan(
                appointment_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', ''),
            )
            return Response({"success": True, "data": {"status": "workflow_cancelled"}})
        except ValueError as e:
            return error_response(message=str(e), code="CANCEL_WORKFLOW_FAILED")
        except Exception as e:
            logger.exception("Failed to cancel appointment workflow")
            return Response(
                {"success": False, "error": {"message": "Failed to cancel workflow", "details": str(e)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class RiskChampionAppointmentWorkflowRecallView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRiskChampion().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_champion:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            appointment = get_object_or_404(RiskChampionAppointment.objects.select_for_update(), pk=pk)
            if not appointment.workflow_plan_id:
                return error_response(message="No active workflow to recall", code="NO_WORKFLOW")
            service = RiskChampionAppointmentService()
            service.cancel_workflow_plan(
                appointment_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', 'Recalled for rework'),
            )
            with transaction.atomic():
                appointment.refresh_from_db()
                appointment.clear_workflow()
                appointment.status = 'draft'
                appointment.rework_count = (appointment.rework_count or 0) + 1
                appointment.save(update_fields=['workflow_plan_id', 'workflow_stage', 'workflow_stage_id', 'workflow_started_at', 'workflow_completed_at', 'status', 'rework_count'])
            return Response({"success": True, "data": RiskChampionAppointmentSerializer(appointment).data, "message": "Appointment recalled for rework"})
        except ValueError as e:
            return error_response(message=str(e), code="RECALL_FAILED")
        except Exception as e:
            logger.exception("Failed to recall appointment workflow")
            return server_error_response(message="Failed to recall appointment")
