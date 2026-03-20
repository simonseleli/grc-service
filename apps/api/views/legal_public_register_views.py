"""
Legal Module — Public Decision & Public Register Views (GAP-11)

Entities: PublicDecision
Endpoints:
  - GET/POST  /legal/public-decisions/           (authenticated - secretariat)
  - GET/PATCH /legal/public-decisions/<pk>/       (authenticated - CRUD)
  - POST      /legal/public-decisions/<pk>/publish/ (authenticated - publish)
  - GET       /legal/public-register/             (unauthenticated - public)
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from apps.core.models import PublicDecision
from apps.api.serializers.legal_serializers import PublicDecisionSerializer
from apps.api.permissions_jwt import (
    CanViewPublicDecision, CanManagePublicDecision,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


class PublicDecisionListCreateView(APIView):
    """
    GET  /legal/public-decisions/
    POST /legal/public-decisions/
    Authenticated — secretariat manages draft/published decisions.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewPublicDecision().has_permission(request, self) or
                    CanManagePublicDecision().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_public_decision:view or :manage required.')
        else:
            if not CanManagePublicDecision().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_public_decision:manage required.')

    def get(self, request):
        try:
            queryset = PublicDecision.objects.select_related('meeting').all()

            # Filters
            status_filter = request.query_params.get('status')
            meeting_id = request.query_params.get('meeting')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if meeting_id:
                queryset = queryset.filter(meeting_id=meeting_id)

            ordering = get_ordering_param(
                request, default='-decision_date',
                allowed_fields=['decision_date', 'published_date', 'status', 'title', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = PublicDecisionSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='public_decision',
            )
        except Exception as e:
            logger.exception("Failed to retrieve public decisions")
            return server_error_response(
                message="Failed to retrieve public decisions",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = PublicDecisionSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=PublicDecisionSerializer(entity).data,
                message="Public decision created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create public decision")
            return server_error_response(
                message="Failed to create public decision",
                details=str(e) if settings.DEBUG else None,
            )


class PublicDecisionDetailView(APIView):
    """
    GET    /legal/public-decisions/<pk>/
    PATCH  /legal/public-decisions/<pk>/
    DELETE /legal/public-decisions/<pk>/
    Authenticated — secretariat CRUD.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewPublicDecision().has_permission(request, self) or
                    CanManagePublicDecision().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_public_decision:view or :manage required.')
        else:
            if not CanManagePublicDecision().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_public_decision:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            PublicDecision.objects.select_related('meeting'),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=PublicDecisionSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve public decision")
            return server_error_response(
                message="Failed to retrieve public decision",
                details=str(e) if settings.DEBUG else None,
            )

    def patch(self, request, pk):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'published':
                return error_response(
                    message="Published decisions cannot be modified. Create a new version instead.",
                    code="DECISION_PUBLISHED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = PublicDecisionSerializer(entity, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=PublicDecisionSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update public decision")
            return server_error_response(
                message="Failed to update public decision",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'published':
                return error_response(
                    message="Published decisions cannot be deleted",
                    code="DECISION_PUBLISHED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])

            return success_response(data={"message": "Public decision deactivated successfully"})
        except Exception as e:
            logger.exception("Failed to delete public decision")
            return server_error_response(
                message="Failed to delete public decision",
                details=str(e) if settings.DEBUG else None,
            )


class PublicDecisionPublishView(APIView):
    """
    POST /legal/public-decisions/<pk>/publish/
    Transitions a draft decision to published status.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManagePublicDecision().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_public_decision:manage required.')

    def post(self, request, pk):
        try:
            entity = get_object_or_404(PublicDecision, pk=pk)

            if entity.status == 'published':
                return error_response(
                    message="Decision is already published",
                    code="ALREADY_PUBLISHED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity.status = 'published'
                entity.published_date = timezone.now()
                entity.save(update_fields=['status', 'published_date', 'updated_at'])

            return success_response(
                data=PublicDecisionSerializer(entity).data,
                message="Decision published successfully",
            )
        except Exception as e:
            logger.exception("Failed to publish public decision")
            return server_error_response(
                message="Failed to publish public decision",
                details=str(e) if settings.DEBUG else None,
            )


class PublicRegisterListView(APIView):
    """
    GET /legal/public-register/
    Unauthenticated — returns only published decisions.
    This is a public-facing read-only endpoint.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            queryset = PublicDecision.objects.filter(
                status='published',
                is_active=True,
            ).select_related('meeting').order_by('-decision_date')

            # Optional search
            search = request.query_params.get('search')
            if search:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(title__icontains=search) | Q(decision_text__icontains=search)
                )

            page_data = paginate_queryset(queryset, request)
            serializer = PublicDecisionSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='public_register',
            )
        except Exception as e:
            logger.exception("Failed to retrieve public register")
            return server_error_response(
                message="Failed to retrieve public register",
                details=str(e) if settings.DEBUG else None,
            )
