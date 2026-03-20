"""
Legal Module — Minutes CRUD + Workflow + Resolution sub-entity views.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import Minutes, Meeting, Resolution
from apps.api.serializers.legal_serializers import (
    MinutesSerializer, ResolutionSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalMinutes, CanManageLegalMinutes, CanApproveLegalMinutes,
    HasAnyPermission,
)
from apps.core.services.legal_minutes_service import LegalMinutesService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response, conflict_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Minutes CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class MinutesListCreateView(APIView):
    """
    GET  /legal/minutes/       — List minutes
    POST /legal/minutes/       — Create minutes for a meeting
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalMinutes().has_permission(request, self) or
                    CanManageLegalMinutes().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_minutes:view or :manage required.')
        else:
            if not CanManageLegalMinutes().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_minutes:manage required.')

    def get(self, request):
        try:
            meeting_id = request.query_params.get('meeting')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')

            queryset = Minutes.objects.select_related('meeting').all()

            if meeting_id:
                queryset = queryset.filter(meeting_id=meeting_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = MinutesSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='minutes',
            )
        except Exception as e:
            logger.exception("Failed to retrieve minutes")
            return server_error_response(
                message="Failed to retrieve minutes",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = MinutesSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            meeting_id = (
                serializer.validated_data.get('meeting_id') or
                (serializer.validated_data.get('meeting') and
                 serializer.validated_data['meeting'].id)
            )
            if meeting_id:
                meeting = get_object_or_404(Meeting, pk=meeting_id, is_active=True)
                if meeting.status != 'closed':
                    return error_response(
                        message="Meeting must be closed before minutes can be created",
                        code="MEETING_NOT_CLOSED",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=MinutesSerializer(entity).data,
                message="Minutes created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create minutes")
            return server_error_response(
                message="Failed to create minutes",
                details=str(e) if settings.DEBUG else None,
            )


class MinutesDetailView(APIView):
    """
    GET    /legal/minutes/<pk>/
    PUT    /legal/minutes/<pk>/
    PATCH  /legal/minutes/<pk>/
    DELETE /legal/minutes/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalMinutes().has_permission(request, self) or
                    CanManageLegalMinutes().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_minutes:view or :manage required.')
        else:
            if not CanManageLegalMinutes().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_minutes:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            Minutes.objects.select_related('meeting'), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=MinutesSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve minutes")
            return server_error_response(
                message="Failed to retrieve minutes",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'approved':
                return error_response(
                    message="Approved minutes cannot be modified",
                    code="MINUTES_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = MinutesSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=MinutesSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update minutes")
            return server_error_response(
                message="Failed to update minutes",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'approved':
                return error_response(
                    message="Approved minutes cannot be deleted",
                    code="MINUTES_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])

            return deleted_response(message="Minutes deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete minutes")
            return server_error_response(
                message="Failed to delete minutes",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Minutes Workflow Views
# ═══════════════════════════════════════════════════════════════════════════════

class MinutesSubmitView(APIView):
    """POST /legal/minutes/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalMinutes().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_minutes:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            entity = get_object_or_404(Minutes, pk=pk)

            if entity.status != 'draft':
                return error_response(
                    message=f"Only draft minutes can be submitted. Current: '{entity.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            service = LegalMinutesService()
            entity = service.submit_for_approval(
                minutes_id=str(pk),
                submitter_id=str(user_id),
            )

            return success_response(
                data=MinutesSerializer(entity).data,
                message="Minutes submitted for approval",
            )
        except Exception as e:
            logger.exception("Failed to submit minutes for workflow")
            return server_error_response(
                message="Failed to submit minutes for workflow",
                details=str(e) if settings.DEBUG else None,
            )


class MinutesWorkflowStatusView(APIView):
    """GET /legal/minutes/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalMinutes().has_permission(request, self) or
                CanManageLegalMinutes().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_minutes:view or :manage required.')

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(Minutes, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})

        try:
            data = LegalMinutesService().get_workflow_status(str(pk))
        except Exception as exc:
            logger.error("Error fetching workflow status for Minutes %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to retrieve workflow status",
                code="WORKFLOW_STATUS_FAILED",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data=data)


class MinutesWorkflowHistoryView(APIView):
    """GET /legal/minutes/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalMinutes().has_permission(request, self) or
                CanManageLegalMinutes().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_minutes:view or :manage required.')

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(Minutes, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})

        try:
            activities = LegalMinutesService().get_workflow_history(str(pk))
        except Exception as exc:
            logger.error("Error fetching workflow history for Minutes %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to retrieve workflow history",
                code="WORKFLOW_HISTORY_FAILED",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data={
            'has_workflow': True,
            'workflow_plan_id': str(entity.workflow_plan_id),
            'activities': activities,
        })


class MinutesWorkflowActionView(APIView):
    """POST /legal/minutes/<pk>/workflow-action/  body: {"action":"approve","comment":"..."}"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_minutes:manage', 'grc:legal_minutes:approve',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_minutes:manage or :approve required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        action_name = request.data.get('action')
        if not action_name:
            return error_response(
                message="'action' is required", code="ACTION_REQUIRED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = LegalMinutesService().advance_workflow_stage(
                minutes_id=str(pk),
                action=action_name,
                actor_id=str(user_id),
                comment=request.data.get('comment', ''),
            )
        except ValueError as exc:
            return error_response(
                message=str(exc), code="WORKFLOW_ACTION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error executing workflow action for Minutes %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to execute workflow action",
                code="WORKFLOW_ACTION_ERROR",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data=result)


class MinutesCancelWorkflowView(APIView):
    """POST /legal/minutes/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalMinutes().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_minutes:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            LegalMinutesService().cancel_workflow_plan(
                minutes_id=str(pk),
                actor_id=str(user_id),
                reason=request.data.get('reason', ''),
            )
        except ValueError as exc:
            return error_response(
                message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error cancelling workflow for Minutes %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to cancel workflow",
                code="CANCEL_WORKFLOW_ERROR",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Resolution (sub-entity of Minutes)
# ═══════════════════════════════════════════════════════════════════════════════

class ResolutionListCreateView(APIView):
    """
    GET  /legal/minutes/{minutes_pk}/resolutions/
    POST /legal/minutes/{minutes_pk}/resolutions/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalMinutes().has_permission(request, self) or
                    CanManageLegalMinutes().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_minutes:view or :manage required.')
        else:
            if not CanManageLegalMinutes().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_minutes:manage required.')

    def get(self, request, minutes_pk):
        try:
            minutes = get_object_or_404(Minutes, pk=minutes_pk)
            queryset = Resolution.objects.filter(
                meeting=minutes.meeting,
            ).select_related('agenda_item').order_by('date_adopted')

            page_data = paginate_queryset(queryset, request)
            serializer = ResolutionSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='resolution',
            )
        except Exception as e:
            logger.exception("Failed to retrieve resolutions")
            return server_error_response(
                message="Failed to retrieve resolutions",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, minutes_pk):
        try:
            minutes = get_object_or_404(Minutes, pk=minutes_pk, is_active=True)
            serializer = ResolutionSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id, meeting=minutes.meeting)

            return created_response(
                data=ResolutionSerializer(entity).data,
                message="Resolution created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create resolution")
            return server_error_response(
                message="Failed to create resolution",
                details=str(e) if settings.DEBUG else None,
            )


class ResolutionDetailView(APIView):
    """
    GET    /legal/resolutions/<pk>/
    PUT    /legal/resolutions/<pk>/
    PATCH  /legal/resolutions/<pk>/
    DELETE /legal/resolutions/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalMinutes().has_permission(request, self) or
                    CanManageLegalMinutes().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_minutes:view or :manage required.')
        else:
            if not CanManageLegalMinutes().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_minutes:manage required.')

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                Resolution.objects.select_related('meeting', 'agenda_item'), pk=pk,
            )
            return success_response(data=ResolutionSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve resolution")
            return server_error_response(
                message="Failed to retrieve resolution",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = get_object_or_404(Resolution, pk=pk)
            serializer = ResolutionSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=ResolutionSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update resolution")
            return server_error_response(
                message="Failed to update resolution",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = get_object_or_404(Resolution, pk=pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Resolution deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete resolution")
            return server_error_response(
                message="Failed to delete resolution",
                details=str(e) if settings.DEBUG else None,
            )
