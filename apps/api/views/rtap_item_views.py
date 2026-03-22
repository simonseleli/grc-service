"""
RTAP Item + Quarterly Update CRUD Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import RTAPItem, RTAPQuarterlyUpdate
from apps.api.serializers.risk_serializers import (
    RTAPItemSerializer,
    RTAPQuarterlyUpdateSerializer,
)
from apps.api.permissions_jwt import (
    CanManageRTAP,
    CanRespondRTAP,
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


# ── RTAP Item CRUD ─────────────────────────────────────────────────────────


class RTAPItemListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:respond']).has_permission(request, self):
                self.permission_denied(request, message='grc:rtap:manage or :respond required.')
        elif request.method == 'POST':
            if not CanManageRTAP().has_permission(request, self):
                self.permission_denied(request, message='grc:rtap:manage required.')

    def get(self, request):
        try:
            rtap_id = request.query_params.get('rtap')
            status_filter = request.query_params.get('status')

            queryset = RTAPItem.objects.select_related('rtap', 'inst_entry').filter(is_active=True)

            if rtap_id:
                queryset = queryset.filter(rtap_id=rtap_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='sort_order', allowed_fields=['sort_order', 'created_at', 'target_date', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RTAPItemSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve RTAP items")
            return server_error_response(message="Failed to retrieve RTAP items")

    def post(self, request):
        try:
            serializer = RTAPItemSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    item = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": RTAPItemSerializer(item).data, "message": "RTAP item created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create RTAP item")
            return server_error_response(message="Failed to create RTAP item")


class RTAPItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:respond']).has_permission(request, self):
                self.permission_denied(request, message='grc:rtap:manage or :respond required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:respond']).has_permission(request, self):
                self.permission_denied(request, message='grc:rtap:manage or :respond required.')

    def get(self, request, pk):
        try:
            item = get_object_or_404(RTAPItem.objects.select_related('rtap', 'inst_entry'), pk=pk)
            return Response({"success": True, "data": RTAPItemSerializer(item).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve RTAP item")
            return server_error_response(message="Failed to retrieve RTAP item")

    def patch(self, request, pk):
        try:
            item = get_object_or_404(RTAPItem, pk=pk)
            serializer = RTAPItemSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    item.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RTAPItemSerializer(updated).data, "message": "RTAP item updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update RTAP item")
            return server_error_response(message="Failed to update RTAP item")

    def delete(self, request, pk):
        try:
            item = get_object_or_404(RTAPItem, pk=pk)
            with transaction.atomic():
                item.is_active = False
                item.save()
            return Response({"success": True, "message": "RTAP item deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete RTAP item")
            return server_error_response(message="Failed to delete RTAP item")


# ── GAP-22: RTAP Item Rework Endpoints ─────────────────────────────────────


class RTAPItemReturnForReworkView(APIView):
    """RMQAM/RMO returns an RTAP item for rework: in_progress → returned_for_rework."""
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
        review_comments = request.data.get('review_comments', '').strip()
        if not review_comments:
            return error_response(message="'review_comments' is required to return an item for rework.", code="REVIEW_COMMENTS_REQUIRED")
        try:
            item = get_object_or_404(RTAPItem.objects.select_for_update(), pk=pk)
            valid_from = {RTAPItem.STATUS_IN_PROGRESS, RTAPItem.STATUS_NOT_STARTED}
            if item.status not in valid_from:
                return error_response(
                    message=f"Item cannot be returned for rework from '{item.status}'. Expected: {sorted(valid_from)}.",
                    code="INVALID_STATUS_TRANSITION",
                )
            from django.utils import timezone
            with transaction.atomic():
                item.status = RTAPItem.STATUS_RETURNED_FOR_REWORK
                item.review_comments = review_comments
                item.returned_at = timezone.now()
                item.modified_by = user_id
                item.save(update_fields=['status', 'review_comments', 'returned_at', 'modified_by'])
            return Response({"success": True, "data": RTAPItemSerializer(item).data, "message": "RTAP item returned for rework"})
        except Http404:
            raise
        except Exception:
            logger.exception("Failed to return RTAP item for rework")
            return server_error_response(message="Failed to return RTAP item for rework")


class RTAPItemResubmitView(APIView):
    """RC resubmits an RTAP item after rework: returned_for_rework → in_progress."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:respond']).has_permission(request, self):
            self.permission_denied(request, message='grc:rtap:manage or :respond required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            item = get_object_or_404(RTAPItem.objects.select_for_update(), pk=pk)
            if item.status != RTAPItem.STATUS_RETURNED_FOR_REWORK:
                return error_response(
                    message=f"Only items with status 'returned_for_rework' can be resubmitted. Current: '{item.status}'.",
                    code="INVALID_STATUS_TRANSITION",
                )
            from django.utils import timezone
            with transaction.atomic():
                item.status = RTAPItem.STATUS_IN_PROGRESS
                item.resubmitted_at = timezone.now()
                item.modified_by = user_id
                item.save(update_fields=['status', 'resubmitted_at', 'modified_by'])
            return Response({"success": True, "data": RTAPItemSerializer(item).data, "message": "RTAP item resubmitted"})
        except Http404:
            raise
        except Exception:
            logger.exception("Failed to resubmit RTAP item")
            return server_error_response(message="Failed to resubmit RTAP item")


# ── RTAP Quarterly Update (sub-resource of RTAPItem) ───────────────────────


class RTAPQuarterlyUpdateListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:respond']).has_permission(request, self):
            self.permission_denied(request, message='grc:rtap:manage or :respond required.')

    def get(self, request, pk):
        try:
            item = get_object_or_404(RTAPItem, pk=pk)
            queryset = RTAPQuarterlyUpdate.objects.select_related('rtap_item', 'quarter').filter(
                rtap_item=item, is_active=True,
            )
            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RTAPQuarterlyUpdateSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve quarterly updates")
            return server_error_response(message="Failed to retrieve quarterly updates")

    def post(self, request, pk):
        try:
            item = get_object_or_404(RTAPItem, pk=pk)
            serializer = RTAPQuarterlyUpdateSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    update = serializer.save(rtap_item=item, created_by=user_id)
                return Response(
                    {"success": True, "data": RTAPQuarterlyUpdateSerializer(update).data, "message": "Quarterly update created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create quarterly update")
            return server_error_response(message="Failed to create quarterly update")


class RTAPQuarterlyUpdateDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission(['grc:rtap:manage', 'grc:rtap:respond']).has_permission(request, self):
            self.permission_denied(request, message='grc:rtap:manage or :respond required.')

    def get(self, request, pk):
        try:
            update = get_object_or_404(RTAPQuarterlyUpdate.objects.select_related('rtap_item', 'quarter'), pk=pk)
            return Response({"success": True, "data": RTAPQuarterlyUpdateSerializer(update).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve quarterly update")
            return server_error_response(message="Failed to retrieve quarterly update")

    def patch(self, request, pk):
        try:
            update = get_object_or_404(RTAPQuarterlyUpdate, pk=pk)
            serializer = RTAPQuarterlyUpdateSerializer(update, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    update.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RTAPQuarterlyUpdateSerializer(updated).data, "message": "Quarterly update updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update quarterly update")
            return server_error_response(message="Failed to update quarterly update")

    def delete(self, request, pk):
        try:
            update = get_object_or_404(RTAPQuarterlyUpdate, pk=pk)
            with transaction.atomic():
                update.is_active = False
                update.save()
            return Response({"success": True, "message": "Quarterly update deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete quarterly update")
            return server_error_response(message="Failed to delete quarterly update")
