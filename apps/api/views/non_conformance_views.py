"""
Non-Conformance CRUD Views
"""
import logging

from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import NonConformance
from apps.api.serializers.risk_serializers import NonConformanceSerializer
from apps.api.permissions_jwt import (
    CanManageNonConformance,
    CanRespondNonConformance,
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

VALID_NC_TRANSITIONS = {
    'open': ['in_progress', 'closed'],
    'in_progress': ['resolved', 'closed'],
    'resolved': ['closed', 'open'],
    'closed': [],
}


class NonConformanceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:non_conformance:manage', 'grc:non_conformance:respond']).has_permission(request, self):
                self.permission_denied(request, message='Non-conformance permission required.')
        elif request.method == 'POST':
            if not CanManageNonConformance().has_permission(request, self):
                self.permission_denied(request, message='grc:non_conformance:manage required.')

    def get(self, request):
        try:
            queryset = NonConformance.objects.select_related('audit_report', 'iso_clause', 'nc_type').filter(is_active=True)

            report = request.query_params.get('audit_report')
            plan = request.query_params.get('audit_plan')
            status_filter = request.query_params.get('status')
            severity = request.query_params.get('severity')

            if report:
                queryset = queryset.filter(audit_report_id=report)
            if plan:
                queryset = queryset.filter(audit_report__audit_plan_id=plan)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if severity:
                queryset = queryset.filter(severity=severity)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'status', 'severity'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = NonConformanceSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve non-conformances")
            return server_error_response(message="Failed to retrieve non-conformances")

    def post(self, request):
        try:
            serializer = NonConformanceSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    nc = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": NonConformanceSerializer(nc).data, "message": "Non-conformance created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create non-conformance")
            return server_error_response(message="Failed to create non-conformance")


class NonConformanceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:non_conformance:manage', 'grc:non_conformance:respond']).has_permission(request, self):
                self.permission_denied(request, message='Non-conformance permission required.')
        elif request.method in ('PUT', 'PATCH'):
            if not HasAnyPermission(['grc:non_conformance:manage', 'grc:non_conformance:respond']).has_permission(request, self):
                self.permission_denied(request, message='Non-conformance permission required.')
        elif request.method == 'DELETE':
            if not CanManageNonConformance().has_permission(request, self):
                self.permission_denied(request, message='grc:non_conformance:manage required.')

    def get(self, request, pk):
        try:
            nc = get_object_or_404(NonConformance.objects.select_related('audit_report', 'iso_clause', 'nc_type'), pk=pk)
            return Response({"success": True, "data": NonConformanceSerializer(nc).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve non-conformance")
            return server_error_response(message="Failed to retrieve non-conformance")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            nc = get_object_or_404(NonConformance, pk=pk)
            new_status = request.data.get('status')
            if new_status and new_status != nc.status:
                allowed = VALID_NC_TRANSITIONS.get(nc.status, [])
                if new_status not in allowed:
                    return error_response(
                        message=f"Cannot transition from '{nc.status}' to '{new_status}'",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            serializer = NonConformanceSerializer(nc, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    nc.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": NonConformanceSerializer(updated).data, "message": "Non-conformance updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update non-conformance")
            return server_error_response(message="Failed to update non-conformance")

    def delete(self, request, pk):
        try:
            nc = get_object_or_404(NonConformance, pk=pk)
            with transaction.atomic():
                nc.is_active = False
                nc.save()
            return Response({"success": True, "message": "Non-conformance deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete non-conformance")
            return server_error_response(message="Failed to delete non-conformance")


# ── GAP-4: NC Dispute / Finding Amendment Views ───────────────────────────────

_DISPUTABLE_STATUSES = [
    NonConformance.STATUS_RAISED,
    NonConformance.STATUS_ACKNOWLEDGED,
    NonConformance.STATUS_IN_PROGRESS,
]

_RESOLVABLE_STATUSES = [NonConformance.STATUS_DISPUTED]


class NCDisputeView(APIView):
    """
    Auditee disputes an NC finding. Sets status → disputed.
    Required: dispute_reason (body).
    Allowed from: raised, acknowledged, in_progress.
    Permission: grc:non_conformance:respond or grc:non_conformance:manage
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:non_conformance:manage', 'grc:non_conformance:respond']).has_permission(request, self):
            self.permission_denied(request, message='Non-conformance permission required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        dispute_reason = request.data.get('dispute_reason', '').strip()
        if not dispute_reason:
            return error_response(message="'dispute_reason' is required.", code="DISPUTE_REASON_REQUIRED")
        try:
            with transaction.atomic():
                nc = get_object_or_404(NonConformance.objects.select_for_update(), pk=pk)
                if nc.status not in _DISPUTABLE_STATUSES:
                    return error_response(
                        message=f"Cannot dispute NC with status '{nc.status}'. Allowed from: {_DISPUTABLE_STATUSES}",
                        code="INVALID_STATUS_FOR_DISPUTE",
                    )
                nc.status = NonConformance.STATUS_DISPUTED
                nc.dispute_reason = dispute_reason
                nc.disputed_at = timezone.now()
                nc.disputed_by = user_id
                nc.modified_by = user_id
                nc.save()
            return Response({
                "success": True,
                "data": NonConformanceSerializer(nc).data,
                "message": "Non-conformance disputed successfully",
            })
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to dispute non-conformance %s", pk)
            return server_error_response(message="Failed to dispute non-conformance")


class NCResolveDisputeView(APIView):
    """
    TL/QA resolves or withdraws a disputed NC. Sets status → closed or withdrawn.
    Required: resolution (body): 'close' | 'withdraw'
    Optional: closure_notes (body)
    Permission: grc:non_conformance:manage
    """
    permission_classes = [IsAuthenticated, CanManageNonConformance]

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        resolution = request.data.get('resolution', '').strip()
        if resolution not in ('close', 'withdraw'):
            return error_response(
                message="'resolution' must be 'close' or 'withdraw'.",
                code="INVALID_RESOLUTION",
            )
        try:
            with transaction.atomic():
                nc = get_object_or_404(NonConformance.objects.select_for_update(), pk=pk)
                if nc.status not in _RESOLVABLE_STATUSES:
                    return error_response(
                        message=f"NC is not in disputed status. Current: '{nc.status}'",
                        code="INVALID_STATUS_FOR_RESOLVE",
                    )
                if resolution == 'close':
                    nc.status = NonConformance.STATUS_CLOSED
                    nc.closed_at = timezone.now()
                    closure_notes = request.data.get('closure_notes', '').strip()
                    if closure_notes:
                        nc.closure_notes = closure_notes
                else:
                    nc.status = NonConformance.STATUS_WITHDRAWN
                nc.modified_by = user_id
                nc.save()
            return Response({
                "success": True,
                "data": NonConformanceSerializer(nc).data,
                "message": f"Non-conformance dispute resolved: {resolution}d",
            })
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to resolve dispute for non-conformance %s", pk)
            return server_error_response(message="Failed to resolve non-conformance dispute")


# ── GAP-5: NC Monthly Summary ─────────────────────────────────────────────────


class NCMonthlySummaryView(APIView):
    """
    GAP-5: Aggregated NC summary — total, overdue, and status breakdown.
    GET /risk/non-conformances/monthly-summary/
    Optional query params:
      - audit_plan: filter by audit plan UUID
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:non_conformance:manage', 'grc:non_conformance:respond']).has_permission(request, self):
            self.permission_denied(request, message='Non-conformance permission required.')

    def get(self, request):
        try:
            queryset = NonConformance.objects.filter(is_active=True)

            audit_plan = request.query_params.get('audit_plan')
            if audit_plan:
                queryset = queryset.filter(audit_report__audit_plan_id=audit_plan)

            today = timezone.now().date()
            overdue_count = queryset.filter(
                due_date__lt=today,
            ).exclude(status=NonConformance.STATUS_CLOSED).exclude(
                status=NonConformance.STATUS_WITHDRAWN,
            ).count()

            status_counts = queryset.values('status').annotate(count=Count('id'))
            breakdown = {item['status']: item['count'] for item in status_counts}

            return Response({
                "success": True,
                "data": {
                    "total": queryset.count(),
                    "overdue": overdue_count,
                    "breakdown": breakdown,
                },
            })
        except Exception as e:
            logger.exception("Failed to generate NC monthly summary")
            return server_error_response(message="Failed to generate NC monthly summary")
