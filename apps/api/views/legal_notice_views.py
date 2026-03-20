"""
Legal Module — Legal Notice CRUD Views
Entity: LegalNotice (standalone — no workflow)
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import LegalNotice, LegalNoticeCounter
from apps.api.serializers.legal_serializers import LegalNoticeSerializer
from apps.api.permissions_jwt import (
    CanViewLegalNotice, CanManageLegalNotice,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)


class LegalNoticeListCreateView(APIView):
    """
    GET  /legal/notices/
    POST /legal/notices/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalNotice().has_permission(request, self) or
                    CanManageLegalNotice().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_notice:view or :manage required.')
        else:
            if not CanManageLegalNotice().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_notice:manage required.')

    def get(self, request):
        try:
            queryset = LegalNotice.objects.select_related(
                'related_case_defendant', 'related_case_plaintiff',
            ).all()

            # Filters
            notice_type = request.query_params.get('notice_type')
            status_filter = request.query_params.get('status')
            case_defendant = request.query_params.get('related_case_defendant')
            case_plaintiff = request.query_params.get('related_case_plaintiff')

            if notice_type:
                queryset = queryset.filter(notice_type=notice_type)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if case_defendant:
                queryset = queryset.filter(related_case_defendant_id=case_defendant)
            if case_plaintiff:
                queryset = queryset.filter(related_case_plaintiff_id=case_plaintiff)

            ordering = get_ordering_param(
                request, default='-issued_date',
                allowed_fields=['issued_date', 'served_date', 'status', 'notice_type', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = LegalNoticeSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='legal_notice',
            )
        except Exception as e:
            logger.exception("Failed to retrieve legal notices")
            return server_error_response(
                message="Failed to retrieve legal notices",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = LegalNoticeSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(
                    created_by=user_id,
                )

            return created_response(
                data=LegalNoticeSerializer(entity).data,
                message="Legal notice created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create legal notice")
            return server_error_response(
                message="Failed to create legal notice",
                details=str(e) if settings.DEBUG else None,
            )


class LegalNoticeDetailView(APIView):
    """
    GET    /legal/notices/<pk>/
    PUT    /legal/notices/<pk>/
    PATCH  /legal/notices/<pk>/
    DELETE /legal/notices/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalNotice().has_permission(request, self) or
                    CanManageLegalNotice().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_notice:view or :manage required.')
        else:
            if not CanManageLegalNotice().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_notice:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            LegalNotice.objects.select_related(
                'related_case_defendant', 'related_case_plaintiff',
            ),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=LegalNoticeSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve legal notice")
            return server_error_response(
                message="Failed to retrieve legal notice",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'expired':
                return error_response(
                    message="Expired notices cannot be modified",
                    code="NOTICE_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = LegalNoticeSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=LegalNoticeSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update legal notice")
            return server_error_response(
                message="Failed to update legal notice",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Legal notice deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete legal notice")
            return server_error_response(
                message="Failed to delete legal notice",
                details=str(e) if settings.DEBUG else None,
            )
