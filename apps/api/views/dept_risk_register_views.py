"""
Departmental Risk Register + DeptRegisterEntry CRUD + Workflow Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import DepartmentalRiskRegister, DeptRegisterEntry
from apps.api.serializers.risk_serializers import (
    DepartmentalRiskRegisterSerializer,
    DeptRegisterEntrySerializer,
)
from apps.api.permissions_jwt import (
    CanManageDeptRiskRegister,
    CanApproveDeptRiskRegister,
    HasAnyPermission,
)
from apps.core.services.dept_risk_register_service import DeptRiskRegisterService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── Departmental Risk Register CRUD ────────────────────────────────────────


class DeptRiskRegisterListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:dept_risk_register:manage', 'grc:dept_risk_register:approve']).has_permission(request, self):
                self.permission_denied(request, message='grc:dept_risk_register:manage or :approve required.')
        elif request.method == 'POST':
            if not CanManageDeptRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:dept_risk_register:manage required.')

    def get(self, request):
        try:
            fiscal_year_id = request.query_params.get('fiscal_year')
            org_unit_id = request.query_params.get('org_unit_id')
            status_filter = request.query_params.get('status')

            queryset = DepartmentalRiskRegister.objects.select_related('fiscal_year').filter(is_active=True)

            if fiscal_year_id:
                queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
            if org_unit_id:
                queryset = queryset.filter(org_unit_id=org_unit_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = DepartmentalRiskRegisterSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve dept risk registers")
            return server_error_response(message="Failed to retrieve departmental risk registers")

    def post(self, request):
        try:
            serializer = DepartmentalRiskRegisterSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    register = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": DepartmentalRiskRegisterSerializer(register).data, "message": "Departmental risk register created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create dept risk register")
            return server_error_response(message="Failed to create departmental risk register")


class DeptRiskRegisterDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:dept_risk_register:manage', 'grc:dept_risk_register:approve']).has_permission(request, self):
                self.permission_denied(request, message='grc:dept_risk_register:manage or :approve required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageDeptRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:dept_risk_register:manage required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(DepartmentalRiskRegister.objects.select_related('fiscal_year'), pk=pk)
            return Response({"success": True, "data": DepartmentalRiskRegisterSerializer(register).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve dept risk register")
            return server_error_response(message="Failed to retrieve departmental risk register")

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            register = get_object_or_404(DepartmentalRiskRegister, pk=pk)
            serializer = DepartmentalRiskRegisterSerializer(register, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    register.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": DepartmentalRiskRegisterSerializer(updated).data, "message": "Register updated successfully"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update dept risk register")
            return server_error_response(message="Failed to update departmental risk register")

    def delete(self, request, pk):
        try:
            register = get_object_or_404(DepartmentalRiskRegister, pk=pk)
            active_entries = register.entries.filter(is_active=True).count()
            if active_entries > 0:
                return error_response(
                    message=f"Cannot delete register with {active_entries} active entries",
                    code="HAS_ACTIVE_ENTRIES",
                )
            with transaction.atomic():
                register.is_active = False
                register.save()
            return Response({"success": True, "message": "Register deleted successfully"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete dept risk register")
            return server_error_response(message="Failed to delete departmental risk register")


# ── DeptRegisterEntry CRUD (sub-resource) ──────────────────────────────────


class DeptRegisterEntryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageDeptRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:dept_risk_register:manage required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(DepartmentalRiskRegister, pk=pk)
            queryset = DeptRegisterEntry.objects.select_related('dept_register', 'risk_sheet').filter(
                dept_register=register, is_active=True,
            )
            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = DeptRegisterEntrySerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve dept register entries")
            return server_error_response(message="Failed to retrieve register entries")

    def post(self, request, pk):
        try:
            register = get_object_or_404(DepartmentalRiskRegister, pk=pk)
            serializer = DeptRegisterEntrySerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    entry = serializer.save(dept_register=register, created_by=user_id)
                return Response(
                    {"success": True, "data": DeptRegisterEntrySerializer(entry).data, "message": "Entry added successfully"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create dept register entry")
            return server_error_response(message="Failed to create register entry")


class DeptRegisterEntryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageDeptRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:dept_risk_register:manage required.')

    def get(self, request, pk):
        try:
            entry = get_object_or_404(DeptRegisterEntry.objects.select_related('dept_register', 'risk_sheet'), pk=pk)
            return Response({"success": True, "data": DeptRegisterEntrySerializer(entry).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve dept register entry")
            return server_error_response(message="Failed to retrieve register entry")

    def delete(self, request, pk):
        try:
            entry = get_object_or_404(DeptRegisterEntry, pk=pk)
            with transaction.atomic():
                entry.is_active = False
                entry.save()
            return Response({"success": True, "message": "Entry removed successfully"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete dept register entry")
            return server_error_response(message="Failed to delete register entry")


# ── Departmental Risk Register Workflow Views ──────────────────────────────


class DeptRiskRegisterWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageDeptRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:dept_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            register = get_object_or_404(DepartmentalRiskRegister, pk=pk)
            if register.status not in ('draft',):
                return error_response(message=f"Only draft registers can be submitted. Current: '{register.status}'", code="INVALID_STATUS")
            if register.workflow_plan_id:
                return Response(
                    {"success": False, "error": {"message": "Workflow already in progress", "code": "WORKFLOW_ALREADY_STARTED"}},
                    status=status.HTTP_409_CONFLICT,
                )
            if not register.entries.filter(is_active=True).exists():
                return error_response(message="Register must have at least one entry before submission", code="NO_ENTRIES")
            service = DeptRiskRegisterService()
            register = service.submit_for_approval(register_id=str(pk), submitter_id=str(user_id))
            return Response(
                {"success": True, "data": DepartmentalRiskRegisterSerializer(register).data, "message": "Register submitted for approval"},
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to start dept register workflow")
            return server_error_response(message="Failed to start register workflow")


class DeptRiskRegisterWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:dept_risk_register:manage', 'grc:dept_risk_register:approve']).has_permission(request, self):
            self.permission_denied(request, message='grc:dept_risk_register:manage or :approve required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(DepartmentalRiskRegister, pk=pk)
            if not register.workflow_plan_id:
                return Response({"success": True, "data": {"has_workflow": False, "status": register.status}})
            workflow_data = DeptRiskRegisterService().get_workflow_status(str(pk))
            return Response({"success": True, "data": workflow_data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get dept register workflow status")
            return Response(
                {"success": False, "error": {"message": "Failed to retrieve workflow status", "details": str(e)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class DeptRiskRegisterWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:dept_risk_register:manage', 'grc:dept_risk_register:approve']).has_permission(request, self):
            self.permission_denied(request, message='grc:dept_risk_register:manage or :approve required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(DepartmentalRiskRegister, pk=pk)
            if not register.workflow_plan_id:
                return Response({"success": True, "data": {"has_workflow": False, "activities": []}})
            activity = DeptRiskRegisterService().get_workflow_history(str(pk))
            return Response({"success": True, "data": {"has_workflow": True, "workflow_plan_id": str(register.workflow_plan_id), "activities": activity}})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get dept register workflow history")
            return Response(
                {"success": False, "error": {"message": "Failed to retrieve workflow history", "details": str(e)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class DeptRiskRegisterWorkflowAdvanceView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:dept_risk_register:manage', 'grc:dept_risk_register:approve']).has_permission(request, self):
            self.permission_denied(request, message='grc:dept_risk_register:manage or :approve required.')

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
            result = DeptRiskRegisterService().advance_workflow_stage(
                register_id=str(pk), action=action_name, actor_id=str(user_id), comment=request.data.get('comment', ''),
            )
            return Response({"success": True, "data": result})
        except ValueError as e:
            return error_response(message=str(e), code="WORKFLOW_ACTION_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to advance dept register workflow")
            return Response(
                {"success": False, "error": {"message": "Failed to execute workflow action", "details": str(e)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class DeptRiskRegisterWorkflowCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageDeptRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:dept_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            DeptRiskRegisterService().cancel_workflow_plan(register_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', ''))
            return Response({"success": True, "data": {"status": "workflow_cancelled"}})
        except ValueError as e:
            return error_response(message=str(e), code="CANCEL_WORKFLOW_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to cancel dept register workflow")
            return Response(
                {"success": False, "error": {"message": "Failed to cancel workflow", "details": str(e)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class DeptRiskRegisterWorkflowRecallView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageDeptRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:dept_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            register = get_object_or_404(DepartmentalRiskRegister.objects.select_for_update(), pk=pk)
            if not register.workflow_plan_id:
                return error_response(message="No active workflow to recall", code="NO_WORKFLOW")
            DeptRiskRegisterService().cancel_workflow_plan(register_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', 'Recalled for rework'))
            with transaction.atomic():
                register.refresh_from_db()
                register.clear_workflow()
                register.status = 'draft'
                register.rework_count = (register.rework_count or 0) + 1
                register.save(update_fields=['workflow_plan_id', 'workflow_stage', 'workflow_stage_id', 'workflow_started_at', 'workflow_completed_at', 'status', 'rework_count'])
            return Response({"success": True, "data": DepartmentalRiskRegisterSerializer(register).data, "message": "Register recalled for rework"})
        except ValueError as e:
            return error_response(message=str(e), code="RECALL_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to recall dept register workflow")
            return server_error_response(message="Failed to recall register")
