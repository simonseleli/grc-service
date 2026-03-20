"""
Legal Module — Hearing + HearingReport CRUD Views
XOR case discriminator: case_defendant or case_plaintiff (never both).
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import Hearing, HearingReport
from apps.api.serializers.legal_serializers import (
    HearingSerializer, HearingReportSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalHearing, CanManageLegalHearing,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Hearing CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class HearingListCreateView(APIView):
    """
    GET  /legal/hearings/
    POST /legal/hearings/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalHearing().has_permission(request, self) or
                    CanManageLegalHearing().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_hearing:view or :manage required.')
        else:
            if not CanManageLegalHearing().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_hearing:manage required.')

    def get(self, request):
        try:
            queryset = Hearing.objects.select_related(
                'case_defendant', 'case_plaintiff',
            ).all()

            case_defendant = request.query_params.get('case_defendant')
            case_plaintiff = request.query_params.get('case_plaintiff')
            status_filter = request.query_params.get('status')

            if case_defendant:
                queryset = queryset.filter(case_defendant_id=case_defendant)
            if case_plaintiff:
                queryset = queryset.filter(case_plaintiff_id=case_plaintiff)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-hearing_date',
                allowed_fields=['hearing_date', 'status', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = HearingSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='hearing',
            )
        except Exception as e:
            logger.exception("Failed to retrieve hearings")
            return server_error_response(
                message="Failed to retrieve hearings",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = HearingSerializer(data=request.data)
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
                data=HearingSerializer(entity).data,
                message="Hearing created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create hearing")
            return server_error_response(
                message="Failed to create hearing",
                details=str(e) if settings.DEBUG else None,
            )


class HearingDetailView(APIView):
    """
    GET    /legal/hearings/<pk>/
    PUT    /legal/hearings/<pk>/
    PATCH  /legal/hearings/<pk>/
    DELETE /legal/hearings/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalHearing().has_permission(request, self) or
                    CanManageLegalHearing().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_hearing:view or :manage required.')
        else:
            if not CanManageLegalHearing().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_hearing:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            Hearing.objects.select_related('case_defendant', 'case_plaintiff'),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=HearingSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve hearing")
            return server_error_response(
                message="Failed to retrieve hearing",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status in ('completed', 'cancelled'):
                return error_response(
                    message=f"Hearing is locked (status: {entity.status})",
                    code="HEARING_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = HearingSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=HearingSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update hearing")
            return server_error_response(
                message="Failed to update hearing",
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
            return deleted_response(message="Hearing deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete hearing")
            return server_error_response(
                message="Failed to delete hearing",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Hearing Report CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class HearingReportListCreateView(APIView):
    """
    GET  /legal/hearings/{hearing_pk}/reports/
    POST /legal/hearings/{hearing_pk}/reports/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalHearing().has_permission(request, self) or
                    CanManageLegalHearing().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_hearing:view or :manage required.')
        else:
            if not CanManageLegalHearing().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_hearing:manage required.')

    def get(self, request, hearing_pk):
        try:
            hearing = get_object_or_404(Hearing, pk=hearing_pk)
            queryset = HearingReport.objects.filter(hearing=hearing).order_by('-created_at')

            page_data = paginate_queryset(queryset, request)
            serializer = HearingReportSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='hearing_report',
            )
        except Exception as e:
            logger.exception("Failed to retrieve hearing reports")
            return server_error_response(
                message="Failed to retrieve hearing reports",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, hearing_pk):
        try:
            hearing = get_object_or_404(Hearing, pk=hearing_pk, is_active=True)
            serializer = HearingReportSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id, hearing=hearing)

                # Propagate next_hearing_date to parent case (SRS §4.6 Rule 2)
                if entity.next_hearing_date:
                    case = hearing.case_defendant or hearing.case_plaintiff
                    if case:
                        case.next_hearing_date = entity.next_hearing_date
                        case.save(update_fields=['next_hearing_date', 'updated_at'])

            return created_response(
                data=HearingReportSerializer(entity).data,
                message="Hearing report created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create hearing report")
            return server_error_response(
                message="Failed to create hearing report",
                details=str(e) if settings.DEBUG else None,
            )


class HearingReportDetailView(APIView):
    """
    GET    /legal/hearing-reports/<pk>/
    PUT    /legal/hearing-reports/<pk>/
    PATCH  /legal/hearing-reports/<pk>/
    DELETE /legal/hearing-reports/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalHearing().has_permission(request, self) or
                    CanManageLegalHearing().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_hearing:view or :manage required.')
        else:
            if not CanManageLegalHearing().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_hearing:manage required.')

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                HearingReport.objects.select_related('hearing'), pk=pk,
            )
            return success_response(data=HearingReportSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve hearing report")
            return server_error_response(
                message="Failed to retrieve hearing report",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = get_object_or_404(HearingReport, pk=pk)
            serializer = HearingReportSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=HearingReportSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update hearing report")
            return server_error_response(
                message="Failed to update hearing report",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = get_object_or_404(HearingReport, pk=pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Hearing report deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete hearing report")
            return server_error_response(
                message="Failed to delete hearing report",
                details=str(e) if settings.DEBUG else None,
            )
