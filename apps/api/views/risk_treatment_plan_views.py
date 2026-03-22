"""
Risk Treatment Action Plan CRUD + Workflow Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import RiskTreatmentActionPlan, RiskChampion
from apps.api.serializers.risk_serializers import RiskTreatmentActionPlanSerializer
from apps.api.permissions_jwt import (
    CanManageRTAP,
    CanApproveRTAP,
    HasAnyPermission,
)
from apps.core.services.rtap_service import RTAPService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


class RTAPListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:approve']).has_permission(request, self):
                self.permission_denied(request, message='grc:rtap:manage or :approve required.')
        elif request.method == 'POST':
            if not CanManageRTAP().has_permission(request, self):
                self.permission_denied(request, message='grc:rtap:manage required.')

    def get(self, request):
        try:
            fiscal_year_id = request.query_params.get('fiscal_year')
            status_filter = request.query_params.get('status')

            queryset = RiskTreatmentActionPlan.objects.select_related(
                'fiscal_year', 'inst_register',
            ).filter(is_active=True)

            if fiscal_year_id:
                queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskTreatmentActionPlanSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve RTAPs")
            return server_error_response(message="Failed to retrieve RTAPs")

    def post(self, request):
        try:
            serializer = RiskTreatmentActionPlanSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    rtap = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": RiskTreatmentActionPlanSerializer(rtap).data, "message": "RTAP created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create RTAP")
            return server_error_response(message="Failed to create RTAP")


class RTAPDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:approve']).has_permission(request, self):
                self.permission_denied(request, message='grc:rtap:manage or :approve required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageRTAP().has_permission(request, self):
                self.permission_denied(request, message='grc:rtap:manage required.')

    def get(self, request, pk):
        try:
            rtap = get_object_or_404(RiskTreatmentActionPlan.objects.select_related('fiscal_year', 'inst_register'), pk=pk)
            return Response({"success": True, "data": RiskTreatmentActionPlanSerializer(rtap).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve RTAP")
            return server_error_response(message="Failed to retrieve RTAP")

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            rtap = get_object_or_404(RiskTreatmentActionPlan, pk=pk)
            serializer = RiskTreatmentActionPlanSerializer(rtap, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    rtap.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RiskTreatmentActionPlanSerializer(updated).data, "message": "RTAP updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update RTAP")
            return server_error_response(message="Failed to update RTAP")

    def delete(self, request, pk):
        try:
            rtap = get_object_or_404(RiskTreatmentActionPlan, pk=pk)
            active_items = rtap.items.filter(is_active=True).count()
            if active_items > 0:
                return error_response(message=f"Cannot delete RTAP with {active_items} active items", code="HAS_ACTIVE_ITEMS")
            with transaction.atomic():
                rtap.is_active = False
                rtap.save()
            return Response({"success": True, "message": "RTAP deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete RTAP")
            return server_error_response(message="Failed to delete RTAP")


# ── RTAP Workflow Views ────────────────────────────────────────────────────


class RTAPWorkflowStartView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRTAP().has_permission(request, self):
            self.permission_denied(request, message='grc:rtap:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            rtap = get_object_or_404(RiskTreatmentActionPlan, pk=pk)
            if rtap.status not in ('draft',):
                return error_response(message=f"Only draft RTAPs can be submitted. Current: '{rtap.status}'", code="INVALID_STATUS")
            if rtap.workflow_plan_id:
                return Response({"success": False, "error": {"message": "Workflow already in progress", "code": "WORKFLOW_ALREADY_STARTED"}}, status=status.HTTP_409_CONFLICT)
            service = RTAPService()
            rtap = service.submit_for_approval(rtap_id=str(pk), submitter_id=str(user_id))
            # Upload RTAP PDF to DRS (non-blocking, outside atomic)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
            from apps.core.utils.risk_document_helpers import _upload_rtap_pdf_to_drs
            _upload_rtap_pdf_to_drs(rtap, auth_token=auth_token)
            rtap.refresh_from_db()
            return Response({"success": True, "data": RiskTreatmentActionPlanSerializer(rtap).data, "message": "RTAP submitted for approval"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to start RTAP workflow")
            return server_error_response(message="Failed to start RTAP workflow")


class RTAPWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:approve']).has_permission(request, self):
            self.permission_denied(request, message='Permission required.')

    def get(self, request, pk):
        try:
            rtap = get_object_or_404(RiskTreatmentActionPlan, pk=pk)
            if not rtap.workflow_plan_id:
                return Response({"success": True, "data": {"has_workflow": False, "status": rtap.status}})
            workflow_data = RTAPService().get_workflow_status(str(pk))
            return Response({"success": True, "data": workflow_data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get RTAP workflow status")
            return Response({"success": False, "error": {"message": "Failed to retrieve workflow status", "details": str(e)}}, status=status.HTTP_502_BAD_GATEWAY)


class RTAPWorkflowHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:approve']).has_permission(request, self):
            self.permission_denied(request, message='Permission required.')

    def get(self, request, pk):
        try:
            rtap = get_object_or_404(RiskTreatmentActionPlan, pk=pk)
            if not rtap.workflow_plan_id:
                return Response({"success": True, "data": {"has_workflow": False, "activities": []}})
            activity = RTAPService().get_workflow_history(str(pk))
            return Response({"success": True, "data": {"has_workflow": True, "workflow_plan_id": str(rtap.workflow_plan_id), "activities": activity}})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to get RTAP workflow history")
            return Response({"success": False, "error": {"message": "Failed to retrieve workflow history", "details": str(e)}}, status=status.HTTP_502_BAD_GATEWAY)


class RTAPWorkflowAdvanceView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:approve']).has_permission(request, self):
            self.permission_denied(request, message='Permission required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)
        action_name = request.data.get('action')
        if not action_name:
            return error_response(message="'action' is required", code="ACTION_REQUIRED")
        try:
            result = RTAPService().advance_workflow_stage(rtap_id=str(pk), action=action_name, actor_id=str(user_id), comment=request.data.get('comment', ''))
            # After workflow advance, check if approved — re-upload + stamp
            rtap = RiskTreatmentActionPlan.objects.get(pk=pk)
            if rtap.status == 'approved':
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                auth_token = auth_header[len('Bearer '):].strip() if auth_header.startswith('Bearer ') else None
                from apps.core.utils.risk_document_helpers import _upload_rtap_pdf_to_drs, stamp_risk_document
                _upload_rtap_pdf_to_drs(rtap, auth_token=auth_token)
                stamp_risk_document(rtap, approver_id=str(user_id), entity_type='risk_treatment_action_plan', auth_token=auth_token)
            return Response({"success": True, "data": result})
        except ValueError as e:
            return error_response(message=str(e), code="WORKFLOW_ACTION_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to advance RTAP workflow")
            return Response({"success": False, "error": {"message": "Failed to execute workflow action", "details": str(e)}}, status=status.HTTP_502_BAD_GATEWAY)


class RTAPWorkflowCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRTAP().has_permission(request, self):
            self.permission_denied(request, message='grc:rtap:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            RTAPService().cancel_workflow_plan(rtap_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', ''))
            return Response({"success": True, "data": {"status": "workflow_cancelled"}})
        except ValueError as e:
            return error_response(message=str(e), code="CANCEL_WORKFLOW_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to cancel RTAP workflow")
            return Response({"success": False, "error": {"message": "Failed to cancel workflow", "details": str(e)}}, status=status.HTTP_502_BAD_GATEWAY)


class RTAPWorkflowRecallView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRTAP().has_permission(request, self):
            self.permission_denied(request, message='grc:rtap:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            rtap = get_object_or_404(RiskTreatmentActionPlan.objects.select_for_update(), pk=pk)
            if not rtap.workflow_plan_id:
                return error_response(message="No active workflow to recall", code="NO_WORKFLOW")
            RTAPService().cancel_workflow_plan(rtap_id=str(pk), actor_id=str(user_id), reason=request.data.get('reason', 'Recalled for rework'))
            with transaction.atomic():
                rtap.refresh_from_db()
                rtap.clear_workflow()
                rtap.status = 'draft'
                rtap.rework_count = (rtap.rework_count or 0) + 1
                rtap.save(update_fields=['workflow_plan_id', 'workflow_stage', 'workflow_stage_id', 'workflow_started_at', 'workflow_completed_at', 'status', 'rework_count'])
            return Response({"success": True, "data": RiskTreatmentActionPlanSerializer(rtap).data, "message": "RTAP recalled for rework"})
        except ValueError as e:
            return error_response(message=str(e), code="RECALL_FAILED")
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to recall RTAP workflow")
            return server_error_response(message="Failed to recall RTAP")


# ── GAP-7: RTAP Send Reminder ──────────────────────────────────────────────


class RTAPSendReminderView(APIView):
    """Sends (records) a reminder to RCs linked to this RTAP (GAP-7)."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRTAP().has_permission(request, self):
            self.permission_denied(request, message='grc:rtap:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            rtap = get_object_or_404(
                RiskTreatmentActionPlan.objects.select_related('inst_register'), pk=pk
            )
            rc_user_ids = list(
                rtap.inst_register.entries.filter(is_active=True)
                .select_related('risk_sheet__risk_champion')
                .values_list('risk_sheet__risk_champion__user_id', flat=True)
                .distinct()
            )
            return Response({
                "success": True,
                "data": {"notified_count": len(rc_user_ids)},
                "message": f"Reminder sent to {len(rc_user_ids)} Risk Champion(s).",
            })
        except Http404:
            raise
        except Exception:
            logger.exception("Failed to send RTAP reminder")
            return server_error_response(message="Failed to send reminder")


# ── GAP-24: RTAP Distribute ────────────────────────────────────────────────


class RTAPDistributeView(APIView):
    """Records that the approved RTAP has been distributed to directorates (GAP-24)."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRTAP().has_permission(request, self):
            self.permission_denied(request, message='grc:rtap:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            rtap = get_object_or_404(RiskTreatmentActionPlan.objects.select_for_update(), pk=pk)
            if rtap.status != 'approved':
                return error_response(
                    message="Only approved RTAPs can be distributed.", code="NOT_APPROVED"
                )
            distribution_reference = request.data.get('distribution_reference', '').strip()
            from django.utils import timezone
            with transaction.atomic():
                rtap.distributed_to_directorates_at = timezone.now()
                if distribution_reference:
                    rtap.distribution_reference = distribution_reference
                rtap.save(update_fields=['distributed_to_directorates_at', 'distribution_reference'])
            rc_count = (
                rtap.inst_register.entries.filter(is_active=True)
                .select_related('risk_sheet__risk_champion')
                .values('risk_sheet__risk_champion__user_id')
                .distinct()
                .count()
            )
            return Response({
                "success": True,
                "data": RiskTreatmentActionPlanSerializer(rtap).data,
                "message": f"RTAP distributed. {rc_count} directorates notified.",
            })
        except Http404:
            raise
        except Exception:
            logger.exception("Failed to distribute RTAP")
            return server_error_response(message="Failed to distribute RTAP")
