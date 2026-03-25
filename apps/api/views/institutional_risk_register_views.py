"""
Institutional Risk Register + Entries + Activity Report CRUD + Workflow Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import (
    InstitutionalRiskRegister, InstitutionalRiskEntry, ActivityReport,
)
from apps.api.serializers.risk_serializers import (
    InstitutionalRiskRegisterSerializer,
    InstitutionalRiskEntrySerializer,
    ActivityReportSerializer,
)
from apps.api.permissions_jwt import (
    CanManageInstitutionalRiskRegister,
    CanApproveInstitutionalRiskRegister,
    HasAnyPermission,
)
from apps.core.services.institutional_risk_register_service import InstitutionalRiskRegisterService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── Institutional Risk Register CRUD ───────────────────────────────────────


class InstitutionalRiskRegisterListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:institutional_risk_register:manage', 'grc:institutional_risk_register:approve']).has_permission(request, self):
                self.permission_denied(request, message='grc:institutional_risk_register:manage or :approve required.')
        elif request.method == 'POST':
            if not CanManageInstitutionalRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def get(self, request):
        try:
            fiscal_year_id = request.query_params.get('fiscal_year')
            status_filter = request.query_params.get('status')

            queryset = InstitutionalRiskRegister.objects.select_related('fiscal_year').filter(is_active=True)
            if fiscal_year_id:
                queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = InstitutionalRiskRegisterSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve institutional risk registers")
            return server_error_response(message="Failed to retrieve institutional risk registers")

    def post(self, request):
        try:
            serializer = InstitutionalRiskRegisterSerializer(data=request.data)
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
                    {"success": True, "data": InstitutionalRiskRegisterSerializer(register).data, "message": "Institutional risk register created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create institutional risk register")
            return server_error_response(message="Failed to create institutional risk register")


class InstitutionalRiskRegisterDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:institutional_risk_register:manage', 'grc:institutional_risk_register:approve']).has_permission(request, self):
                self.permission_denied(request, message='grc:institutional_risk_register:manage or :approve required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageInstitutionalRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(InstitutionalRiskRegister.objects.select_related('fiscal_year'), pk=pk)
            return Response({"success": True, "data": InstitutionalRiskRegisterSerializer(register).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve institutional risk register")
            return server_error_response(message="Failed to retrieve institutional risk register")

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            serializer = InstitutionalRiskRegisterSerializer(register, data=request.data, partial=partial)
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
                return Response({"success": True, "data": InstitutionalRiskRegisterSerializer(updated).data, "message": "Register updated successfully"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update institutional risk register")
            return server_error_response(message="Failed to update institutional risk register")

    def delete(self, request, pk):
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            active_entries = register.entries.filter(is_active=True).count()
            if active_entries > 0:
                return error_response(message=f"Cannot delete register with {active_entries} active entries", code="HAS_ACTIVE_ENTRIES")
            with transaction.atomic():
                register.is_active = False
                register.save()
            return Response({"success": True, "message": "Register deleted successfully"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete institutional risk register")
            return server_error_response(message="Failed to delete institutional risk register")


# ── Institutional Risk Entry CRUD (sub-resource) ──────────────────────────


class InstitutionalRiskEntryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageInstitutionalRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            queryset = InstitutionalRiskEntry.objects.select_related('inst_register', 'risk_sheet').filter(
                inst_register=register, is_active=True,
            )
            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = InstitutionalRiskEntrySerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve institutional risk entries")
            return server_error_response(message="Failed to retrieve entries")

    def post(self, request, pk):
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            serializer = InstitutionalRiskEntrySerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    entry = serializer.save(inst_register=register, created_by=user_id)
                return Response(
                    {"success": True, "data": InstitutionalRiskEntrySerializer(entry).data, "message": "Entry added"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create institutional risk entry")
            return server_error_response(message="Failed to create entry")


class InstitutionalRiskEntryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageInstitutionalRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def get(self, request, pk):
        try:
            entry = get_object_or_404(InstitutionalRiskEntry.objects.select_related('inst_register', 'risk_sheet'), pk=pk)
            return Response({"success": True, "data": InstitutionalRiskEntrySerializer(entry).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve institutional risk entry")
            return server_error_response(message="Failed to retrieve entry")

    def delete(self, request, pk):
        try:
            entry = get_object_or_404(InstitutionalRiskEntry, pk=pk)
            with transaction.atomic():
                entry.is_active = False
                entry.save()
            return Response({"success": True, "message": "Entry removed"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete institutional risk entry")
            return server_error_response(message="Failed to delete entry")


# ── Activity Report CRUD (sub-resource of IRR) ────────────────────────────


class ActivityReportListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:institutional_risk_register:manage', 'grc:risk_assessment:conduct']).has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage or grc:risk_assessment:conduct required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            queryset = ActivityReport.objects.select_related('inst_register', 'quarter').filter(
                inst_register=register, is_active=True,
            )
            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = ActivityReportSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve activity reports")
            return server_error_response(message="Failed to retrieve activity reports")

    def post(self, request, pk):
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            serializer = ActivityReportSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    report = serializer.save(inst_register=register, reported_by=user_id, created_by=user_id)
                return Response(
                    {"success": True, "data": ActivityReportSerializer(report).data, "message": "Activity report created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create activity report")
            return server_error_response(message="Failed to create activity report")


class ActivityReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:institutional_risk_register:manage', 'grc:risk_assessment:conduct']).has_permission(request, self):
            self.permission_denied(request, message='Permission required.')

    def get(self, request, pk):
        try:
            report = get_object_or_404(ActivityReport.objects.select_related('inst_register', 'quarter'), pk=pk)
            return Response({"success": True, "data": ActivityReportSerializer(report).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve activity report")
            return server_error_response(message="Failed to retrieve activity report")

    def patch(self, request, pk):
        try:
            report = get_object_or_404(ActivityReport, pk=pk)
            serializer = ActivityReportSerializer(report, data=request.data, partial=True)
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
                return Response({"success": True, "data": ActivityReportSerializer(updated).data, "message": "Activity report updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update activity report")
            return server_error_response(message="Failed to update activity report")

    def delete(self, request, pk):
        try:
            report = get_object_or_404(ActivityReport, pk=pk)
            with transaction.atomic():
                report.is_active = False
                report.save()
            return Response({"success": True, "message": "Activity report deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete activity report")
            return server_error_response(message="Failed to delete activity report")


# ── Institutional Risk Register Workflow Views ─────────────────────────────


class InstitutionalRiskRegisterWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageInstitutionalRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            if register.status not in ('draft',):
                return error_response(message=f"Only draft registers can be submitted. Current: '{register.status}'", code="INVALID_STATUS")
            if register.workflow_plan_id:
                return Response(
                    {"success": False, "error": {"message": "Workflow already in progress", "code": "WORKFLOW_ALREADY_STARTED"}},
                    status=status.HTTP_409_CONFLICT,
                )
            if not register.entries.filter(is_active=True).exists():
                return error_response(message="Register must have at least one entry", code="NO_ENTRIES")
            service = InstitutionalRiskRegisterService()
            register = service.submit_for_approval(register_id=str(pk), submitter_id=str(user_id))
            # Upload IRR PDF to DRS (non-blocking, outside atomic)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
            from apps.core.utils.risk_document_helpers import _upload_risk_register_pdf_to_drs
            _upload_risk_register_pdf_to_drs(register, auth_token=auth_token)
            register.refresh_from_db()
            return Response(
                {"success": True, "data": InstitutionalRiskRegisterSerializer(register).data, "message": "Register submitted for approval"},
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to start IRR workflow")
            return server_error_response(message="Failed to start register workflow")


class InstitutionalRiskRegisterWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:institutional_risk_register:manage', 'grc:institutional_risk_register:approve']).has_permission(request, self):
            self.permission_denied(request, message='Permission required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            if not register.workflow_plan_id:
                return Response({"success": True, "data": {"has_workflow": False, "status": register.status}})
            workflow_data = InstitutionalRiskRegisterService().get_workflow_status(str(pk))
            return Response({"success": True, "data": workflow_data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get IRR workflow status")
            return Response({"success": False, "error": {"message": "Failed to retrieve workflow status", "details": str(e)}}, status=status.HTTP_502_BAD_GATEWAY)


class InstitutionalRiskRegisterWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:institutional_risk_register:manage', 'grc:institutional_risk_register:approve']).has_permission(request, self):
            self.permission_denied(request, message='Permission required.')

    def get(self, request, pk):
        try:
            register = get_object_or_404(InstitutionalRiskRegister, pk=pk)
            if not register.workflow_plan_id:
                return Response({"success": True, "data": {"has_workflow": False, "activities": []}})
            activity = InstitutionalRiskRegisterService().get_workflow_history(str(pk))
            return Response({"success": True, "data": {"has_workflow": True, "workflow_plan_id": str(register.workflow_plan_id), "activities": activity}})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get IRR workflow history")
            return Response({"success": False, "error": {"message": "Failed to retrieve workflow history", "details": str(e)}}, status=status.HTTP_502_BAD_GATEWAY)


class InstitutionalRiskRegisterWorkflowAdvanceView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:institutional_risk_register:manage', 'grc:institutional_risk_register:approve']).has_permission(request, self):
            self.permission_denied(request, message='Permission required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)
        action_name = request.data.get('action')
        if not action_name:
            return error_response(message="'action' is required", code="ACTION_REQUIRED")
        try:
            result = InstitutionalRiskRegisterService().advance_workflow_stage(
                register_id=str(pk), action=action_name, actor_id=str(user_id), comment=request.data.get('comment', ''),
            )
            # After workflow advance, check if approved — re-upload + stamp
            register = InstitutionalRiskRegister.objects.get(pk=pk)
            if register.status == 'approved':
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
                from apps.core.utils.risk_document_helpers import _upload_risk_register_pdf_to_drs, stamp_risk_document
                _upload_risk_register_pdf_to_drs(register, auth_token=auth_token)
                stamp_risk_document(register, approver_id=str(user_id), entity_type='institutional_risk_register', auth_token=auth_token)
            return Response({"success": True, "data": result})
        except ValueError as e:
            return error_response(message=str(e), code="WORKFLOW_ACTION_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to advance IRR workflow")
            return Response({"success": False, "error": {"message": "Failed to execute workflow action", "details": str(e)}}, status=status.HTTP_502_BAD_GATEWAY)


class InstitutionalRiskRegisterWorkflowCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageInstitutionalRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            InstitutionalRiskRegisterService().cancel_workflow_plan(register_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', ''))
            return Response({"success": True, "data": {"status": "workflow_cancelled"}})
        except ValueError as e:
            return error_response(message=str(e), code="CANCEL_WORKFLOW_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to cancel IRR workflow")
            return Response({"success": False, "error": {"message": "Failed to cancel workflow", "details": str(e)}}, status=status.HTTP_502_BAD_GATEWAY)


class InstitutionalRiskRegisterWorkflowRecallView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageInstitutionalRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            register = get_object_or_404(InstitutionalRiskRegister.objects.select_for_update(), pk=pk)
            if not register.workflow_plan_id:
                return error_response(message="No active workflow to recall", code="NO_WORKFLOW")
            InstitutionalRiskRegisterService().cancel_workflow_plan(register_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', 'Recalled for rework'))
            with transaction.atomic():
                register.refresh_from_db()
                register.clear_workflow()
                register.status = 'draft'
                register.rework_count = (register.rework_count or 0) + 1
                register.save(update_fields=['workflow_plan_id', 'workflow_stage', 'workflow_stage_id', 'workflow_started_at', 'workflow_completed_at', 'status', 'rework_count'])
            return Response({"success": True, "data": InstitutionalRiskRegisterSerializer(register).data, "message": "Register recalled for rework"})
        except ValueError as e:
            return error_response(message=str(e), code="RECALL_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to recall IRR workflow")
            return server_error_response(message="Failed to recall register")


# ── GAP-8: Workshop Notification Endpoints ─────────────────────────────────


class IRRNotifyDirectorsView(APIView):
    """Records that Directors have been notified of the IRR workshop (GAP-8)."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageInstitutionalRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            register = get_object_or_404(InstitutionalRiskRegister.objects.select_for_update(), pk=pk)
            from django.utils import timezone
            with transaction.atomic():
                register.directors_notified_at = timezone.now()
                register.save(update_fields=['directors_notified_at'])
            notified_count = register.entries.filter(is_active=True).count()
            return Response({
                "success": True,
                "data": {"notified_at": register.directors_notified_at.isoformat(), "notified_count": notified_count},
                "message": "Directors notified of IRR workshop",
            })
        except Http404:
            raise
        except Exception:
            logger.exception("Failed to notify directors")
            return server_error_response(message="Failed to notify directors")


class IRRNotifyRCsView(APIView):
    """Records that Risk Champions have been notified of the IRR workshop (GAP-8)."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageInstitutionalRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            register = get_object_or_404(InstitutionalRiskRegister.objects.select_for_update(), pk=pk)
            rc_user_ids = list(
                register.entries.filter(is_active=True)
                .select_related('risk_sheet__risk_champion')
                .values_list('risk_sheet__risk_champion__user_id', flat=True)
                .distinct()
            )
            from django.utils import timezone
            with transaction.atomic():
                register.rcs_notified_at = timezone.now()
                register.save(update_fields=['rcs_notified_at'])
            return Response({
                "success": True,
                "data": {"notified_at": register.rcs_notified_at.isoformat(), "notified_count": len(rc_user_ids)},
                "message": "Risk Champions notified of IRR workshop",
            })
        except Http404:
            raise
        except Exception:
            logger.exception("Failed to notify RCs")
            return server_error_response(message="Failed to notify Risk Champions")


# ── GAP-24: Distribution Endpoint ──────────────────────────────────────────


class IRRDistributeView(APIView):
    """Records that the approved IRR has been distributed to directorates (GAP-24)."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageInstitutionalRiskRegister().has_permission(request, self):
            self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            register = get_object_or_404(InstitutionalRiskRegister.objects.select_for_update(), pk=pk)
            if register.status != 'approved':
                return error_response(
                    message="Only approved registers can be distributed.", code="NOT_APPROVED"
                )
            distribution_reference = request.data.get('distribution_reference', '').strip()
            from django.utils import timezone
            with transaction.atomic():
                register.distributed_to_directorates_at = timezone.now()
                if distribution_reference:
                    register.distribution_reference = distribution_reference
                register.save(update_fields=['distributed_to_directorates_at', 'distribution_reference'])
            rc_count = (
                register.entries.filter(is_active=True)
                .select_related('risk_sheet__risk_champion')
                .values('risk_sheet__risk_champion__user_id')
                .distinct()
                .count()
            )
            return Response({
                "success": True,
                "data": InstitutionalRiskRegisterSerializer(register).data,
                "message": f"IRR distributed. {rc_count} directorates notified.",
            })
        except Http404:
            raise
        except Exception:
            logger.exception("Failed to distribute IRR")
            return server_error_response(message="Failed to distribute register")


# ── SRS-FIX G-03: DG Noting for Activity Report ───────────────────────────


class ActivityReportDGNoteView(APIView):
    """
    SRS-FIX G-03: RMQAM submits Activity Report to DG for noting.
    POST body: {} (DG user is taken from JWT).
    """
    permission_classes = [IsAuthenticated, CanManageInstitutionalRiskRegister]

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            report = get_object_or_404(ActivityReport.objects.select_for_update(), pk=pk)
            if report.dg_noted:
                return error_response(message="Activity report already noted by DG.", code="ALREADY_NOTED")
            from django.utils import timezone
            with transaction.atomic():
                report.dg_noted = True
                report.dg_noted_by = user_id
                report.dg_noted_at = timezone.now()
                report.save(update_fields=['dg_noted', 'dg_noted_by', 'dg_noted_at'])
            return Response({
                "success": True,
                "data": ActivityReportSerializer(report).data,
                "message": "Activity report noted by DG.",
            })
        except Http404:
            raise
        except Exception:
            logger.exception("Failed to DG-note activity report")
            return server_error_response(message="Failed to note activity report")


# ── SRS-FIX G-10: Standalone Activity Report List ─────────────────────────


class StandaloneActivityReportListView(APIView):
    """
    SRS-FIX G-10: Cross-register query for activity reports.
    GET /risk/activity-reports/?quarter=<uuid>&fiscal_year=<uuid>
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:institutional_risk_register:manage', 'grc:risk_assessment:conduct']).has_permission(request, self):
            self.permission_denied(request, message='Permission required.')

    def get(self, request):
        try:
            queryset = ActivityReport.objects.select_related('inst_register', 'quarter').filter(is_active=True)
            quarter = request.query_params.get('quarter')
            fiscal_year = request.query_params.get('fiscal_year')
            if quarter:
                queryset = queryset.filter(quarter_id=quarter)
            if fiscal_year:
                queryset = queryset.filter(inst_register__fiscal_year_id=fiscal_year)
            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'submission_date'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = ActivityReportSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Exception as e:
            logger.exception("Failed to retrieve activity reports")
            return server_error_response(message="Failed to retrieve activity reports")
