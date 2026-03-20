"""
Legal Module — Lookup Table Views
Read-only list endpoints for the 7 legal lookup tables.
"""

import logging

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.permissions_jwt import (
    CanViewLegalCase, CanViewLegalDirective, CanViewLegalMeeting,
)
from apps.api.serializers.lookup_serializers import (
    CourtLevelSerializer,
    DirectiveCategorySerializer,
    DirectivePrioritySerializer,
    LitigationRiskLevelSerializer,
    LitigationUrgencyLevelSerializer,
    MeetingModeSerializer,
    MeetingTypeSerializer,
)
from apps.api.utils.pagination import get_ordering_param, paginate_queryset
from apps.api.utils.response_helpers import (
    paginated_list_response,
    server_error_response,
)
from apps.core.models import (
    CourtLevel,
    DirectiveCategory,
    DirectivePriority,
    LitigationRiskLevel,
    LitigationUrgencyLevel,
    MeetingMode,
    MeetingType,
)

logger = logging.getLogger(__name__)


# ── Litigation Lookups ───────────────────────────────────────────────────────


class CourtLevelListView(APIView):
    """GET /legal/lookups/court-levels/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:view required.')

    def get(self, request):
        try:
            queryset = CourtLevel.objects.filter(is_active=True)
            ordering = get_ordering_param(
                request, default='sort_order',
                allowed_fields=['sort_order', 'name', 'code'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = CourtLevelSerializer(page_data['queryset'], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data['total'],
                page=page_data['page'], page_size=page_data['page_size'],
                resource='court_level',
            )
        except Exception as e:
            logger.exception("Failed to retrieve court levels")
            return server_error_response(
                message="Failed to retrieve court levels",
                details=str(e) if settings.DEBUG else None,
            )


class LitigationUrgencyLevelListView(APIView):
    """GET /legal/lookups/urgency-levels/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:view required.')

    def get(self, request):
        try:
            queryset = LitigationUrgencyLevel.objects.filter(is_active=True)
            ordering = get_ordering_param(
                request, default='sort_order',
                allowed_fields=['sort_order', 'name', 'code'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = LitigationUrgencyLevelSerializer(page_data['queryset'], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data['total'],
                page=page_data['page'], page_size=page_data['page_size'],
                resource='litigation_urgency_level',
            )
        except Exception as e:
            logger.exception("Failed to retrieve urgency levels")
            return server_error_response(
                message="Failed to retrieve urgency levels",
                details=str(e) if settings.DEBUG else None,
            )


class LitigationRiskLevelListView(APIView):
    """GET /legal/lookups/risk-levels/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:view required.')

    def get(self, request):
        try:
            queryset = LitigationRiskLevel.objects.filter(is_active=True)
            ordering = get_ordering_param(
                request, default='sort_order',
                allowed_fields=['sort_order', 'name', 'code'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = LitigationRiskLevelSerializer(page_data['queryset'], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data['total'],
                page=page_data['page'], page_size=page_data['page_size'],
                resource='litigation_risk_level',
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk levels")
            return server_error_response(
                message="Failed to retrieve risk levels",
                details=str(e) if settings.DEBUG else None,
            )


# ── Meeting Lookups ──────────────────────────────────────────────────────────


class MeetingModeListView(APIView):
    """GET /legal/lookups/meeting-modes/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalMeeting().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_meeting:view required.')

    def get(self, request):
        try:
            queryset = MeetingMode.objects.filter(is_active=True)
            ordering = get_ordering_param(
                request, default='sort_order',
                allowed_fields=['sort_order', 'name', 'code'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = MeetingModeSerializer(page_data['queryset'], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data['total'],
                page=page_data['page'], page_size=page_data['page_size'],
                resource='meeting_mode',
            )
        except Exception as e:
            logger.exception("Failed to retrieve meeting modes")
            return server_error_response(
                message="Failed to retrieve meeting modes",
                details=str(e) if settings.DEBUG else None,
            )


class MeetingTypeListView(APIView):
    """GET /legal/lookups/meeting-types/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalMeeting().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_meeting:view required.')

    def get(self, request):
        try:
            queryset = MeetingType.objects.filter(is_active=True)
            ordering = get_ordering_param(
                request, default='sort_order',
                allowed_fields=['sort_order', 'name', 'code'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = MeetingTypeSerializer(page_data['queryset'], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data['total'],
                page=page_data['page'], page_size=page_data['page_size'],
                resource='meeting_type',
            )
        except Exception as e:
            logger.exception("Failed to retrieve meeting types")
            return server_error_response(
                message="Failed to retrieve meeting types",
                details=str(e) if settings.DEBUG else None,
            )


# ── Directive Lookups ────────────────────────────────────────────────────────


class DirectivePriorityListView(APIView):
    """GET /legal/lookups/directive-priorities/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalDirective().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_directive:view required.')

    def get(self, request):
        try:
            queryset = DirectivePriority.objects.filter(is_active=True)
            ordering = get_ordering_param(
                request, default='sort_order',
                allowed_fields=['sort_order', 'name', 'code'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = DirectivePrioritySerializer(page_data['queryset'], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data['total'],
                page=page_data['page'], page_size=page_data['page_size'],
                resource='directive_priority',
            )
        except Exception as e:
            logger.exception("Failed to retrieve directive priorities")
            return server_error_response(
                message="Failed to retrieve directive priorities",
                details=str(e) if settings.DEBUG else None,
            )


class DirectiveCategoryListView(APIView):
    """GET /legal/lookups/directive-categories/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalDirective().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_directive:view required.')

    def get(self, request):
        try:
            queryset = DirectiveCategory.objects.filter(is_active=True)
            ordering = get_ordering_param(
                request, default='sort_order',
                allowed_fields=['sort_order', 'name', 'code'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = DirectiveCategorySerializer(page_data['queryset'], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data['total'],
                page=page_data['page'], page_size=page_data['page_size'],
                resource='directive_category',
            )
        except Exception as e:
            logger.exception("Failed to retrieve directive categories")
            return server_error_response(
                message="Failed to retrieve directive categories",
                details=str(e) if settings.DEBUG else None,
            )
