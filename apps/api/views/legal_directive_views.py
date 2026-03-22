"""
Legal Module — Directive + Task CRUD Views
Entities: MeetingDirective, LitigationDirective, TaskLitigation
No workflows — directives use standard status transitions only.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    MeetingDirective, LitigationDirective, TaskLitigation,
)
from apps.api.serializers.legal_serializers import (
    MeetingDirectiveSerializer, LitigationDirectiveSerializer,
    TaskLitigationSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalDirective, CanManageLegalDirective, CanApproveDirectiveClosure,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting Directive CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingDirectiveListCreateView(APIView):
    """
    GET  /legal/directives/meeting/
    POST /legal/directives/meeting/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalDirective().has_permission(request, self) or
                    CanManageLegalDirective().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_directive:view or :manage required.')
        else:
            if not CanManageLegalDirective().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_directive:manage required.')

    def get(self, request):
        try:
            queryset = MeetingDirective.objects.select_related(
                'meeting', 'agenda_item', 'directive_priority', 'directive_category',
            ).all()

            # Filters
            meeting = request.query_params.get('meeting')
            status_filter = request.query_params.get('status')
            assigned_user = request.query_params.get('assigned_user_id')
            fully_closed = request.query_params.get('fully_closed')

            if meeting:
                queryset = queryset.filter(meeting_id=meeting)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if assigned_user:
                queryset = queryset.filter(assigned_user_id=assigned_user)
            if fully_closed is not None:
                queryset = queryset.filter(fully_closed=fully_closed.lower() == 'true')

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['due_date', 'status', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = MeetingDirectiveSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='meeting_directive',
            )
        except Exception as e:
            logger.exception("Failed to retrieve meeting directives")
            return server_error_response(
                message="Failed to retrieve meeting directives",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = MeetingDirectiveSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # Business rule: parent minutes must be approved before directives can be created
            meeting = serializer.validated_data.get('meeting')
            if meeting:
                has_approved_minutes = meeting.minutes.filter(status='approved').exists()
                if not has_approved_minutes:
                    return error_response(
                        message="Meeting minutes must be approved before issuing directives",
                        code="MINUTES_NOT_APPROVED",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=MeetingDirectiveSerializer(entity).data,
                message="Meeting directive created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create meeting directive")
            return server_error_response(
                message="Failed to create meeting directive",
                details=str(e) if settings.DEBUG else None,
            )


class MeetingDirectiveDetailView(APIView):
    """
    GET    /legal/directives/meeting/<pk>/
    PUT    /legal/directives/meeting/<pk>/
    PATCH  /legal/directives/meeting/<pk>/
    DELETE /legal/directives/meeting/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalDirective().has_permission(request, self) or
                    CanManageLegalDirective().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_directive:view or :manage required.')
        else:
            if not CanManageLegalDirective().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_directive:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            MeetingDirective.objects.select_related(
                'meeting', 'agenda_item', 'directive_priority', 'directive_category',
            ),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=MeetingDirectiveSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve meeting directive")
            return server_error_response(
                message="Failed to retrieve meeting directive",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'fully_closed':
                return error_response(
                    message="Fully closed directives cannot be modified",
                    code="DIRECTIVE_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = MeetingDirectiveSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=MeetingDirectiveSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update meeting directive")
            return server_error_response(
                message="Failed to update meeting directive",
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
            return deleted_response(message="Meeting directive deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete meeting directive")
            return server_error_response(
                message="Failed to delete meeting directive",
                details=str(e) if settings.DEBUG else None,
            )


class MeetingDirectiveOverdueListView(APIView):
    """GET /legal/directives/meeting/overdue/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalDirective().has_permission(request, self) or
                CanManageLegalDirective().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_directive:view or :manage required.')

    def get(self, request):
        try:
            today = timezone.now().date()
            queryset = MeetingDirective.objects.select_related(
                'meeting', 'agenda_item', 'directive_priority',
            ).filter(
                due_date__lt=today,
                status__in=['open', 'in_progress'],
            ).order_by('due_date')

            page_data = paginate_queryset(queryset, request)
            serializer = MeetingDirectiveSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='meeting_directive_overdue',
            )
        except Exception as e:
            logger.exception("Failed to retrieve overdue meeting directives")
            return server_error_response(
                message="Failed to retrieve overdue meeting directives",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Litigation Directive CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class LitigationDirectiveListCreateView(APIView):
    """
    GET  /legal/directives/litigation/
    POST /legal/directives/litigation/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalDirective().has_permission(request, self) or
                    CanManageLegalDirective().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_directive:view or :manage required.')
        else:
            if not CanManageLegalDirective().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_directive:manage required.')

    def get(self, request):
        try:
            queryset = LitigationDirective.objects.select_related(
                'case_defendant', 'case_plaintiff',
            ).all()

            # Filters
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
                request, default='-issue_date',
                allowed_fields=['issue_date', 'due_date', 'status', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = LitigationDirectiveSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='litigation_directive',
            )
        except Exception as e:
            logger.exception("Failed to retrieve litigation directives")
            return server_error_response(
                message="Failed to retrieve litigation directives",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = LitigationDirectiveSerializer(data=request.data)
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
                data=LitigationDirectiveSerializer(entity).data,
                message="Litigation directive created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create litigation directive")
            return server_error_response(
                message="Failed to create litigation directive",
                details=str(e) if settings.DEBUG else None,
            )


class LitigationDirectiveDetailView(APIView):
    """
    GET    /legal/directives/litigation/<pk>/
    PUT    /legal/directives/litigation/<pk>/
    PATCH  /legal/directives/litigation/<pk>/
    DELETE /legal/directives/litigation/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalDirective().has_permission(request, self) or
                    CanManageLegalDirective().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_directive:view or :manage required.')
        else:
            if not CanManageLegalDirective().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_directive:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            LitigationDirective.objects.select_related('case_defendant', 'case_plaintiff'),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=LitigationDirectiveSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve litigation directive")
            return server_error_response(
                message="Failed to retrieve litigation directive",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'closed':
                return error_response(
                    message="Closed litigation directives cannot be modified",
                    code="DIRECTIVE_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = LitigationDirectiveSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=LitigationDirectiveSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update litigation directive")
            return server_error_response(
                message="Failed to update litigation directive",
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
            return deleted_response(message="Litigation directive deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete litigation directive")
            return server_error_response(
                message="Failed to delete litigation directive",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Task Litigation CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TaskLitigationListCreateView(APIView):
    """
    GET  /legal/tasks/litigation/
    POST /legal/tasks/litigation/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalDirective().has_permission(request, self) or
                    CanManageLegalDirective().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_directive:view or :manage required.')
        else:
            if not CanManageLegalDirective().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_directive:manage required.')

    def get(self, request):
        try:
            queryset = TaskLitigation.objects.select_related(
                'case_defendant', 'case_plaintiff',
            ).all()

            # Filters
            case_defendant = request.query_params.get('case_defendant')
            case_plaintiff = request.query_params.get('case_plaintiff')
            status_filter = request.query_params.get('status')
            priority = request.query_params.get('priority')

            if case_defendant:
                queryset = queryset.filter(case_defendant_id=case_defendant)
            if case_plaintiff:
                queryset = queryset.filter(case_plaintiff_id=case_plaintiff)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if priority:
                queryset = queryset.filter(priority=priority)

            ordering = get_ordering_param(
                request, default='due_date',
                allowed_fields=['due_date', 'status', 'priority', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = TaskLitigationSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='task_litigation',
            )
        except Exception as e:
            logger.exception("Failed to retrieve litigation tasks")
            return server_error_response(
                message="Failed to retrieve litigation tasks",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = TaskLitigationSerializer(data=request.data)
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
                data=TaskLitigationSerializer(entity).data,
                message="Litigation task created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create litigation task")
            return server_error_response(
                message="Failed to create litigation task",
                details=str(e) if settings.DEBUG else None,
            )


class TaskLitigationDetailView(APIView):
    """
    GET    /legal/tasks/litigation/<pk>/
    PUT    /legal/tasks/litigation/<pk>/
    PATCH  /legal/tasks/litigation/<pk>/
    DELETE /legal/tasks/litigation/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalDirective().has_permission(request, self) or
                    CanManageLegalDirective().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_directive:view or :manage required.')
        else:
            if not CanManageLegalDirective().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_directive:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            TaskLitigation.objects.select_related('case_defendant', 'case_plaintiff'),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=TaskLitigationSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve litigation task")
            return server_error_response(
                message="Failed to retrieve litigation task",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'closed':
                return error_response(
                    message="Closed tasks cannot be modified",
                    code="TASK_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = TaskLitigationSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=TaskLitigationSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update litigation task")
            return server_error_response(
                message="Failed to update litigation task",
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
            return deleted_response(message="Litigation task deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete litigation task")
            return server_error_response(
                message="Failed to delete litigation task",
                details=str(e) if settings.DEBUG else None,
            )


class TaskLitigationOverdueListView(APIView):
    """GET /legal/tasks/litigation/overdue/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalDirective().has_permission(request, self) or
                CanManageLegalDirective().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_directive:view or :manage required.')

    def get(self, request):
        try:
            today = timezone.now().date()
            queryset = TaskLitigation.objects.select_related(
                'case_defendant', 'case_plaintiff',
            ).filter(
                due_date__lt=today,
                status__in=['open', 'in_progress'],
            ).order_by('due_date')

            page_data = paginate_queryset(queryset, request)
            serializer = TaskLitigationSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='task_litigation_overdue',
            )
        except Exception as e:
            logger.exception("Failed to retrieve overdue litigation tasks")
            return server_error_response(
                message="Failed to retrieve overdue litigation tasks",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Litigation Directive — Submit for DG Approval / DG Decision (SIG-03 / B4-3)
# ═══════════════════════════════════════════════════════════════════════════════

VALID_DIRECTIVE_DG_DECISIONS = ('approve', 'reject')


class LitigationDirectiveSubmitForDGApprovalView(APIView):
    """POST /legal/litigation-directives/<pk>/submit-for-dg-approval/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalDirective().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_directive:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(LitigationDirective, pk=pk, is_active=True)

        if not entity.requires_dg_approval_for_closure:
            return error_response(
                message="This directive does not require DG approval for closure",
                code="DG_APPROVAL_NOT_REQUIRED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if entity.status not in ('open', 'in_progress'):
            return error_response(
                message=f"Cannot submit for DG approval from status '{entity.status}'",
                code="INVALID_STATUS_TRANSITION",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            entity.status = 'pending_dg_approval'
            entity.save(update_fields=['status', 'updated_at'])

        return success_response(
            data=LitigationDirectiveSerializer(entity).data,
        )


class LitigationDirectiveDGDecisionView(APIView):
    """POST /legal/litigation-directives/<pk>/dg-decision/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanApproveDirectiveClosure().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_directive:approve_closure required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        decision = request.data.get('decision')
        if decision not in VALID_DIRECTIVE_DG_DECISIONS:
            return error_response(
                message=f"'decision' must be one of {VALID_DIRECTIVE_DG_DECISIONS}",
                code="INVALID_DECISION",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        entity = get_object_or_404(LitigationDirective, pk=pk, is_active=True)

        if entity.status != 'pending_dg_approval':
            return error_response(
                message="Directive is not pending DG approval",
                code="NOT_PENDING_APPROVAL",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if decision == 'approve':
                entity.status = 'closed'
                entity.completion_date = timezone.now().date()
            else:
                entity.status = 'in_progress'
            entity.save(update_fields=['status', 'completion_date', 'updated_at'])

        return success_response(
            data=LitigationDirectiveSerializer(entity).data,
        )
