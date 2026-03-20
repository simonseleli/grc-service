"""
Legal Module — Governing Body & Member CRUD Views
Entities: GoverningBody, Member, CommitteeType, SubmissionForDetermination
"""

import logging

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    GoverningBody, Member, CommitteeType, SubmissionForDetermination,
)
from apps.api.serializers.legal_serializers import (
    GoverningBodySerializer, GoverningBodyListSerializer,
    MemberSerializer, CommitteeTypeSerializer,
    SubmissionForDeterminationSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalGoverningBody, CanManageLegalGoverningBody,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, not_found_response, validation_error_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Committee Type (lookup-style, read-only for regular users)
# ═══════════════════════════════════════════════════════════════════════════════

class CommitteeTypeListView(APIView):
    """GET /legal/committee-types/  — List all active committee types."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            queryset = CommitteeType.objects.filter(is_active=True).order_by('name')
            serializer = CommitteeTypeSerializer(queryset, many=True)
            return success_response(data=serializer.data)
        except Exception as e:
            logger.exception("Failed to retrieve committee types")
            return server_error_response(
                message="Failed to retrieve committee types",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Governing Body
# ═══════════════════════════════════════════════════════════════════════════════

class GoverningBodyListCreateView(APIView):
    """
    GET  /legal/governing-bodies/       — List governing bodies
    POST /legal/governing-bodies/       — Create a governing body
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalGoverningBody().has_permission(request, self)
            can_manage = CanManageLegalGoverningBody().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:view or :manage permission required.',
                )
        else:
            if not CanManageLegalGoverningBody().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:manage permission required.',
                )

    def get(self, request):
        try:
            committee_type_id = request.query_params.get('committee_type')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')
            search = request.query_params.get('search')

            queryset = GoverningBody.objects.select_related('committee_type').all()

            if committee_type_id:
                queryset = queryset.filter(committee_type_id=committee_type_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            if search:
                queryset = queryset.filter(name__icontains=search)

            ordering = get_ordering_param(
                request, default='name',
                allowed_fields=['name', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = GoverningBodyListSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='governing_body',
            )
        except Exception as e:
            logger.exception("Failed to retrieve governing bodies")
            return server_error_response(
                message="Failed to retrieve governing bodies",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = GoverningBodySerializer(data=request.data)
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
                data=GoverningBodySerializer(entity).data,
                message="Governing body created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create governing body")
            return server_error_response(
                message="Failed to create governing body",
                details=str(e) if settings.DEBUG else None,
            )


class GoverningBodyDetailView(APIView):
    """
    GET    /legal/governing-bodies/<pk>/
    PUT    /legal/governing-bodies/<pk>/
    PATCH  /legal/governing-bodies/<pk>/
    DELETE /legal/governing-bodies/<pk>/   (soft delete)
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalGoverningBody().has_permission(request, self)
            can_manage = CanManageLegalGoverningBody().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:view or :manage permission required.',
                )
        else:
            if not CanManageLegalGoverningBody().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:manage permission required.',
                )

    def _get_entity(self, pk):
        return get_object_or_404(
            GoverningBody.objects.select_related('committee_type'), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            serializer = GoverningBodySerializer(entity)
            return success_response(data=serializer.data)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve governing body")
            return server_error_response(
                message="Failed to retrieve governing body",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            serializer = GoverningBodySerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=GoverningBodySerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update governing body")
            return server_error_response(
                message="Failed to update governing body",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)

            if entity.meetings.filter(is_active=True).exclude(status__in=['closed', 'cancelled']).exists():
                return error_response(
                    message="Cannot deactivate governing body with active meetings",
                    code="HAS_ACTIVE_MEETINGS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])

            return deleted_response(message="Governing body deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete governing body")
            return server_error_response(
                message="Failed to delete governing body",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Member
# ═══════════════════════════════════════════════════════════════════════════════

class MemberListCreateView(APIView):
    """
    GET  /legal/governing-bodies/{gb_pk}/members/
    POST /legal/governing-bodies/{gb_pk}/members/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalGoverningBody().has_permission(request, self)
            can_manage = CanManageLegalGoverningBody().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:view or :manage permission required.',
                )
        else:
            if not CanManageLegalGoverningBody().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:manage permission required.',
                )

    def get(self, request, gb_pk):
        try:
            governing_body = get_object_or_404(GoverningBody, pk=gb_pk)
            position = request.query_params.get('position')
            is_active = request.query_params.get('is_active')

            queryset = Member.objects.filter(
                governing_body=governing_body,
            ).select_related('governing_body')

            if position:
                queryset = queryset.filter(position=position)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request, default='position',
                allowed_fields=['position', 'joined_date', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = MemberSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='member',
            )
        except Exception as e:
            logger.exception("Failed to retrieve members")
            return server_error_response(
                message="Failed to retrieve members",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, gb_pk):
        try:
            governing_body = get_object_or_404(GoverningBody, pk=gb_pk, is_active=True)
            serializer = MemberSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id, governing_body=governing_body)

            return created_response(
                data=MemberSerializer(entity).data,
                message="Member added successfully",
            )
        except Exception as e:
            logger.exception("Failed to add member")
            return server_error_response(
                message="Failed to add member",
                details=str(e) if settings.DEBUG else None,
            )


class MemberDetailView(APIView):
    """
    GET    /legal/members/<pk>/
    PUT    /legal/members/<pk>/
    PATCH  /legal/members/<pk>/
    DELETE /legal/members/<pk>/   (soft delete)
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalGoverningBody().has_permission(request, self)
            can_manage = CanManageLegalGoverningBody().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:view or :manage permission required.',
                )
        else:
            if not CanManageLegalGoverningBody().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:manage permission required.',
                )

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                Member.objects.select_related('governing_body'), pk=pk,
            )
            serializer = MemberSerializer(entity)
            return success_response(data=serializer.data)
        except Exception as e:
            logger.exception("Failed to retrieve member")
            return server_error_response(
                message="Failed to retrieve member",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = get_object_or_404(Member, pk=pk)
            serializer = MemberSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=MemberSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update member")
            return server_error_response(
                message="Failed to update member",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = get_object_or_404(Member, pk=pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Member deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete member")
            return server_error_response(
                message="Failed to delete member",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Submission for Determination
# ═══════════════════════════════════════════════════════════════════════════════

class SubmissionForDeterminationListCreateView(APIView):
    """
    GET  /legal/submissions/
    POST /legal/submissions/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalGoverningBody().has_permission(request, self)
            can_manage = CanManageLegalGoverningBody().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:view or :manage permission required.',
                )
        else:
            if not CanManageLegalGoverningBody().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:manage permission required.',
                )

    def get(self, request):
        try:
            target_body_id = request.query_params.get('target_body')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')

            queryset = SubmissionForDetermination.objects.select_related(
                'target_body', 'meeting',
            ).all()

            if target_body_id:
                queryset = queryset.filter(target_body_id=target_body_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request, default='-submission_date',
                allowed_fields=['submission_date', 'created_at', 'status'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = SubmissionForDeterminationSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='submission_for_determination',
            )
        except Exception as e:
            logger.exception("Failed to retrieve submissions")
            return server_error_response(
                message="Failed to retrieve submissions",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = SubmissionForDeterminationSerializer(data=request.data)
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
                    submitter_user_id=user_id,
                )

            return created_response(
                data=SubmissionForDeterminationSerializer(entity).data,
                message="Submission created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create submission")
            return server_error_response(
                message="Failed to create submission",
                details=str(e) if settings.DEBUG else None,
            )


class SubmissionForDeterminationDetailView(APIView):
    """
    GET    /legal/submissions/<pk>/
    PUT    /legal/submissions/<pk>/
    PATCH  /legal/submissions/<pk>/
    DELETE /legal/submissions/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalGoverningBody().has_permission(request, self)
            can_manage = CanManageLegalGoverningBody().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:view or :manage permission required.',
                )
        else:
            if not CanManageLegalGoverningBody().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:legal_governing_body:manage permission required.',
                )

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                SubmissionForDetermination.objects.select_related('target_body', 'meeting'),
                pk=pk,
            )
            serializer = SubmissionForDeterminationSerializer(entity)
            return success_response(data=serializer.data)
        except Exception as e:
            logger.exception("Failed to retrieve submission")
            return server_error_response(
                message="Failed to retrieve submission",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = get_object_or_404(SubmissionForDetermination, pk=pk)

            if entity.is_locked:
                return error_response(
                    message="Cannot update submission in current status",
                    code="SUBMISSION_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = SubmissionForDeterminationSerializer(
                entity, data=request.data, partial=partial,
            )
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(
                data=SubmissionForDeterminationSerializer(updated).data,
            )
        except Exception as e:
            logger.exception("Failed to update submission")
            return server_error_response(
                message="Failed to update submission",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = get_object_or_404(SubmissionForDetermination, pk=pk)

            if entity.is_locked:
                return error_response(
                    message="Cannot delete submission in current status",
                    code="SUBMISSION_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])

            return deleted_response(message="Submission deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete submission")
            return server_error_response(
                message="Failed to delete submission",
                details=str(e) if settings.DEBUG else None,
            )

