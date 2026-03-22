"""
QMS Audit Plan + Team Assignment CRUD + Workflow Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import QMSAuditPlan, QMSAuditTeamAssignment
from apps.api.serializers.risk_serializers import (
    QMSAuditPlanSerializer,
    QMSAuditTeamAssignmentSerializer,
)
from apps.api.permissions_jwt import (
    CanManageQMSAuditPlan,
    CanApproveQMSAuditPlan,
    HasAnyPermission,
)
from apps.core.services.qms_audit_plan_service import QMSAuditPlanService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── QMS Audit Plan CRUD ───────────────────────────────────────────────────


class QMSAuditPlanListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:qms_audit_plan:manage', 'grc:qms_audit_plan:approve']).has_permission(request, self):
                self.permission_denied(request, message='QMS audit plan permission required.')
        elif request.method == 'POST':
            if not CanManageQMSAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='grc:qms_audit_plan:manage required.')

    def get(self, request):
        try:
            queryset = QMSAuditPlan.objects.select_related(
                'audit_program',
            ).filter(is_active=True)

            program = request.query_params.get('audit_program')
            auditee_unit = request.query_params.get('auditee_unit')
            status_filter = request.query_params.get('status')

            if program:
                queryset = queryset.filter(audit_program_id=program)
            if auditee_unit:
                queryset = queryset.filter(auditee_unit_id=auditee_unit)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'planned_start_date', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QMSAuditPlanSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve QMS audit plans")
            return server_error_response(message="Failed to retrieve QMS audit plans")

    def post(self, request):
        try:
            serializer = QMSAuditPlanSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    plan = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": QMSAuditPlanSerializer(plan).data, "message": "QMS audit plan created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create QMS audit plan")
            return server_error_response(message="Failed to create QMS audit plan")


class QMSAuditPlanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:qms_audit_plan:manage', 'grc:qms_audit_plan:approve']).has_permission(request, self):
                self.permission_denied(request, message='QMS audit plan permission required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageQMSAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='grc:qms_audit_plan:manage required.')

    def get(self, request, pk):
        try:
            plan = get_object_or_404(QMSAuditPlan.objects.select_related('audit_program'), pk=pk)
            return Response({"success": True, "data": QMSAuditPlanSerializer(plan).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve QMS audit plan")
            return server_error_response(message="Failed to retrieve QMS audit plan")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            serializer = QMSAuditPlanSerializer(plan, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    plan.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": QMSAuditPlanSerializer(updated).data, "message": "QMS audit plan updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update QMS audit plan")
            return server_error_response(message="Failed to update QMS audit plan")

    def delete(self, request, pk):
        try:
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            with transaction.atomic():
                plan.is_active = False
                plan.save()
            return Response({"success": True, "message": "QMS audit plan deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete QMS audit plan")
            return server_error_response(message="Failed to delete QMS audit plan")


# ── Team Assignment (sub-resource of Plan) ─────────────────────────────────


class QMSTeamAssignmentListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def get(self, request, pk):
        try:
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            queryset = QMSAuditTeamAssignment.objects.select_related('audit_plan').filter(
                audit_plan=plan, is_active=True,
            )
            ordering = get_ordering_param(request, default='created_at', allowed_fields=['created_at', 'role'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QMSAuditTeamAssignmentSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve team assignments")
            return server_error_response(message="Failed to retrieve team assignments")

    def post(self, request, pk):
        try:
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            serializer = QMSAuditTeamAssignmentSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    assignment = serializer.save(audit_plan=plan, created_by=user_id)
                return Response(
                    {"success": True, "data": QMSAuditTeamAssignmentSerializer(assignment).data, "message": "Team assignment created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create team assignment")
            return server_error_response(message="Failed to create team assignment")


class QMSTeamAssignmentDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def get(self, request, pk):
        try:
            assignment = get_object_or_404(QMSAuditTeamAssignment.objects.select_related('audit_plan'), pk=pk)
            return Response({"success": True, "data": QMSAuditTeamAssignmentSerializer(assignment).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve team assignment")
            return server_error_response(message="Failed to retrieve team assignment")

    def patch(self, request, pk):
        try:
            assignment = get_object_or_404(QMSAuditTeamAssignment, pk=pk)
            serializer = QMSAuditTeamAssignmentSerializer(assignment, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    assignment.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": QMSAuditTeamAssignmentSerializer(updated).data, "message": "Team assignment updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update team assignment")
            return server_error_response(message="Failed to update team assignment")

    def delete(self, request, pk):
        try:
            assignment = get_object_or_404(QMSAuditTeamAssignment, pk=pk)
            with transaction.atomic():
                assignment.is_active = False
                assignment.save()
            return Response({"success": True, "message": "Team assignment deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete team assignment")
            return server_error_response(message="Failed to delete team assignment")


# ── Workflow Views ─────────────────────────────────────────────────────────


class QMSAuditPlanWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            if not QMSAuditTeamAssignment.objects.filter(audit_plan=plan, is_active=True).exists():
                return error_response(message="Plan must have at least one team assignment before submission", status_code=status.HTTP_400_BAD_REQUEST)
            service = QMSAuditPlanService()
            plan = service.submit_for_approval(plan_id=str(pk), submitter_id=str(user_id))
            return Response({"success": True, "data": QMSAuditPlanSerializer(plan).data, "message": "Workflow submitted"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to start workflow for QMS audit plan %s", pk)
            return server_error_response(message="Failed to start workflow")


class QMSAuditPlanWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            workflow_data = QMSAuditPlanService().get_workflow_status(str(pk))
            return Response({"success": True, "data": workflow_data})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get workflow status for QMS audit plan %s", pk)
            return server_error_response(message="Failed to get workflow status")


class QMSAuditPlanWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            activity = QMSAuditPlanService().get_workflow_history(str(pk))
            return Response({"success": True, "data": activity})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get workflow history for QMS audit plan %s", pk)
            return server_error_response(message="Failed to get workflow history")


class QMSAuditPlanWorkflowAdvanceView(APIView):
    permission_classes = [IsAuthenticated, CanApproveQMSAuditPlan]

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
            result = QMSAuditPlanService().advance_workflow_stage(
                plan_id=str(pk), action=action_name, actor_id=str(user_id), comment=request.data.get('comment', ''),
            )
            return Response({"success": True, "data": result, "message": "Workflow advanced"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to advance workflow for QMS audit plan %s", pk)
            return server_error_response(message="Failed to advance workflow")


class QMSAuditPlanWorkflowCancelView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            QMSAuditPlanService().cancel_workflow_plan(plan_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', ''))
            return Response({"success": True, "message": "Workflow cancelled"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to cancel workflow for QMS audit plan %s", pk)
            return server_error_response(message="Failed to cancel workflow")


class QMSAuditPlanWorkflowRecallView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            plan = get_object_or_404(QMSAuditPlan.objects.select_for_update(), pk=pk)
            if plan.status == 'draft':
                return error_response(message="Cannot recall a draft plan", status_code=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                QMSAuditPlanService().cancel_workflow_plan(plan_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', 'Recalled for rework'))
                plan.refresh_from_db()
                plan.clear_workflow()
                plan.status = 'draft'
                plan.rework_count = getattr(plan, 'rework_count', 0) + 1
                plan.save()
            return Response({"success": True, "data": QMSAuditPlanSerializer(plan).data, "message": "Plan recalled"})
        except ValueError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to recall QMS audit plan %s", pk)
            return server_error_response(message="Failed to recall plan")
