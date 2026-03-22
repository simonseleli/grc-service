"""
Legal Module — Meeting CRUD + Workflow Views
Entities: Meeting, MeetingAgenda, ConflictDeclaration, MeetingParticipant
"""

import logging
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    Meeting, MeetingAgenda, ConflictDeclaration, MeetingParticipant,
    MeetingCounter, GoverningBody, MeetingDirective, Member,
)
from apps.api.serializers.legal_serializers import (
    MeetingSerializer, MeetingListSerializer,
    MeetingAgendaSerializer, ConflictDeclarationSerializer,
    MeetingParticipantSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalMeeting, CanManageLegalMeeting, CanApproveLegalMeeting,
    HasAnyPermission,
)
from apps.core.services.legal_meeting_service import LegalMeetingService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response, conflict_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)

LOCKED_STATUSES = ('closed', 'cancelled')


def _generate_meeting_number(gb, sequence: int) -> str:
    """Generate meeting number using GoverningBody prefix and format config (MIN-18 / B4-5)."""
    from datetime import datetime
    now = datetime.now()
    prefix = (gb.meeting_number_prefix or '').strip() or 'MTG'
    fmt = gb.meeting_number_format or 'sequential'
    if fmt == 'financial_year':
        # Financial year: July-June.  FY = year of July start.
        fy = now.year if now.month >= 7 else now.year - 1
        return f"{prefix}-FY{fy}/{fy + 1}-{sequence:03d}"
    # Default: sequential with YYYYMM
    return f"{prefix}-{now.strftime('%Y%m')}-{sequence:03d}"


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingListCreateView(APIView):
    """
    GET  /legal/meetings/       — List meetings
    POST /legal/meetings/       — Create a meeting
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalMeeting().has_permission(request, self)
            can_manage = CanManageLegalMeeting().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:legal_meeting:view or :manage permission required.',
                )
        else:
            if not CanManageLegalMeeting().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:legal_meeting:manage permission required.',
                )

    def get(self, request):
        try:
            governing_body_id = request.query_params.get('governing_body')
            meeting_type_id = request.query_params.get('meeting_type')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')

            queryset = Meeting.objects.select_related(
                'governing_body', 'meeting_type', 'meeting_mode',
            ).all()

            if governing_body_id:
                queryset = queryset.filter(governing_body_id=governing_body_id)
            if meeting_type_id:
                queryset = queryset.filter(meeting_type_id=meeting_type_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request, default='-scheduled_start',
                allowed_fields=['scheduled_start', 'created_at', 'status'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = MeetingListSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='meeting',
            )
        except Exception as e:
            logger.exception("Failed to retrieve meetings")
            return server_error_response(
                message="Failed to retrieve meetings",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = MeetingSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            governing_body_id = serializer.validated_data.get('governing_body_id') or (
                serializer.validated_data.get('governing_body') and
                serializer.validated_data['governing_body'].id
            )
            if governing_body_id:
                gb = get_object_or_404(GoverningBody, pk=governing_body_id, is_active=True)
            else:
                return error_response(
                    message="governing_body is required",
                    code="GOVERNING_BODY_REQUIRED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            meeting_number = serializer.validated_data.get('meeting_number', '').strip()
            if not meeting_number:
                with transaction.atomic():
                    counter, _ = MeetingCounter.objects.select_for_update().get_or_create(
                        governing_body_id=gb.id,
                        defaults={'sequence': 0},
                    )
                    counter.sequence += 1
                    counter.save(update_fields=['sequence'])
                    meeting_number = _generate_meeting_number(gb, counter.sequence)

            with transaction.atomic():
                entity = serializer.save(
                    created_by=user_id,
                    secretary_id=user_id,
                    meeting_number=meeting_number,
                )

                # GAP-04: Auto-populate participants from active members
                members = Member.objects.filter(
                    governing_body=entity.governing_body, is_active=True,
                )
                if members.exists():
                    participants = [
                        MeetingParticipant(
                            meeting=entity,
                            user_id=m.user_id,
                            role='secretary' if m.position == 'secretary' else 'member',
                            invitation_status='pending',
                            created_by=user_id,
                        )
                        for m in members
                    ]
                    MeetingParticipant.objects.bulk_create(participants)
                    member_count = len(participants)
                    entity.total_member_count = member_count
                    entity.rsvp_pending_count = member_count
                    entity.save(update_fields=['total_member_count', 'rsvp_pending_count', 'updated_at'])

            return created_response(
                data=MeetingSerializer(entity).data,
                message="Meeting created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create meeting")
            return server_error_response(
                message="Failed to create meeting",
                details=str(e) if settings.DEBUG else None,
            )


class MeetingDetailView(APIView):
    """
    GET    /legal/meetings/<pk>/
    PUT    /legal/meetings/<pk>/
    PATCH  /legal/meetings/<pk>/
    DELETE /legal/meetings/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalMeeting().has_permission(request, self)
            can_manage = CanManageLegalMeeting().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:legal_meeting:view or :manage permission required.',
                )
        else:
            if not CanManageLegalMeeting().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:legal_meeting:manage permission required.',
                )

    def _get_entity(self, pk):
        return get_object_or_404(
            Meeting.objects.select_related(
                'governing_body', 'meeting_type', 'meeting_mode',
            ), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            serializer = MeetingSerializer(entity)
            return success_response(data=serializer.data)
        except Exception as e:
            logger.exception("Failed to retrieve meeting")
            return server_error_response(
                message="Failed to retrieve meeting",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status in LOCKED_STATUSES:
                return error_response(
                    message=f"Meeting is locked (status: {entity.status})",
                    code="MEETING_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = MeetingSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=MeetingSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update meeting")
            return server_error_response(
                message="Failed to update meeting",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'closed':
                return error_response(
                    message="Cannot delete a closed meeting",
                    code="MEETING_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])

            return deleted_response(message="Meeting deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete meeting")
            return server_error_response(
                message="Failed to delete meeting",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting Workflow Views
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingSubmitView(APIView):
    """POST /legal/meetings/<pk>/submit/  — Start meeting lifecycle workflow"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalMeeting().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_meeting:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            entity = get_object_or_404(Meeting, pk=pk)

            if entity.status != 'draft':
                return error_response(
                    message=f"Only draft meetings can be submitted. Current status: '{entity.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            service = LegalMeetingService()
            entity = service.submit_for_approval(
                meeting_id=str(pk),
                submitter_id=str(user_id),
            )

            return success_response(
                data=MeetingSerializer(entity).data,
                message="Meeting submitted for workflow",
            )
        except Exception as e:
            logger.exception("Failed to submit meeting for workflow")
            return server_error_response(
                message="Failed to submit meeting for workflow",
                details=str(e) if settings.DEBUG else None,
            )


class MeetingWorkflowStatusView(APIView):
    """GET /legal/meetings/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalMeeting().has_permission(request, self) or
                CanManageLegalMeeting().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_meeting:view or :manage required.')

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(Meeting, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})

        try:
            data = LegalMeetingService().get_workflow_status(str(pk))
        except Exception as exc:
            logger.error("Error fetching workflow status for Meeting %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to retrieve workflow status",
                code="WORKFLOW_STATUS_FAILED",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data=data)


class MeetingWorkflowHistoryView(APIView):
    """GET /legal/meetings/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalMeeting().has_permission(request, self) or
                CanManageLegalMeeting().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_meeting:view or :manage required.')

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(Meeting, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})

        try:
            activities = LegalMeetingService().get_workflow_history(str(pk))
        except Exception as exc:
            logger.error("Error fetching workflow history for Meeting %s: %s", pk, exc, exc_info=True)
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


class MeetingWorkflowActionView(APIView):
    """POST /legal/meetings/<pk>/workflow-action/  body: {"action":"approve","comment":"..."}"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_meeting:manage', 'grc:legal_meeting:approve',
        ]).has_permission(request, self):
            self.permission_denied(
                request,
                message='grc:legal_meeting:manage or :approve required.',
            )

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
            result = LegalMeetingService().advance_workflow_stage(
                meeting_id=str(pk),
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
            logger.error("Error executing workflow action for Meeting %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to execute workflow action",
                code="WORKFLOW_ACTION_ERROR",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data=result)


class MeetingCancelWorkflowView(APIView):
    """POST /legal/meetings/<pk>/cancel-workflow/  body: {"reason":"..."}"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalMeeting().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_meeting:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            LegalMeetingService().cancel_workflow_plan(
                meeting_id=str(pk),
                actor_id=str(user_id),
                reason=request.data.get('reason', ''),
            )
        except ValueError as exc:
            return error_response(
                message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error cancelling workflow for Meeting %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to cancel workflow",
                code="CANCEL_WORKFLOW_ERROR",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting Agenda
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingAgendaListCreateView(APIView):
    """
    GET  /legal/meetings/{meeting_pk}/agenda/
    POST /legal/meetings/{meeting_pk}/agenda/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalMeeting().has_permission(request, self)
            can_manage = CanManageLegalMeeting().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:legal_meeting:view or :manage required.')
        else:
            if not CanManageLegalMeeting().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_meeting:manage required.')

    def get(self, request, meeting_pk):
        try:
            meeting = get_object_or_404(Meeting, pk=meeting_pk)
            queryset = MeetingAgenda.objects.filter(
                meeting=meeting,
            ).select_related('submission').order_by('order')

            page_data = paginate_queryset(queryset, request)
            serializer = MeetingAgendaSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='meeting_agenda',
            )
        except Exception as e:
            logger.exception("Failed to retrieve agenda items")
            return server_error_response(
                message="Failed to retrieve agenda items",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, meeting_pk):
        try:
            meeting = get_object_or_404(Meeting, pk=meeting_pk, is_active=True)

            if meeting.status in LOCKED_STATUSES:
                return error_response(
                    message=f"Meeting is locked (status: {meeting.status})",
                    code="MEETING_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = MeetingAgendaSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id, meeting=meeting)

                # GAP-02: Auto-transition submission to under_review
                if entity.submission_id and entity.submission.status == 'submitted':
                    entity.submission.status = 'under_review'
                    entity.submission.save(update_fields=['status', 'updated_at'])

            return created_response(
                data=MeetingAgendaSerializer(entity).data,
                message="Agenda item added successfully",
            )
        except Exception as e:
            logger.exception("Failed to add agenda item")
            return server_error_response(
                message="Failed to add agenda item",
                details=str(e) if settings.DEBUG else None,
            )


class MeetingAgendaDetailView(APIView):
    """
    GET    /legal/agenda/<pk>/
    PUT    /legal/agenda/<pk>/
    PATCH  /legal/agenda/<pk>/
    DELETE /legal/agenda/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalMeeting().has_permission(request, self)
            can_manage = CanManageLegalMeeting().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:legal_meeting:view or :manage required.')
        else:
            if not CanManageLegalMeeting().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_meeting:manage required.')

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                MeetingAgenda.objects.select_related('meeting', 'submission'), pk=pk,
            )
            return success_response(data=MeetingAgendaSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve agenda item")
            return server_error_response(
                message="Failed to retrieve agenda item",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = get_object_or_404(MeetingAgenda, pk=pk)

            if entity.meeting.status in LOCKED_STATUSES:
                return error_response(
                    message="Cannot update agenda on a locked meeting",
                    code="MEETING_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # GAP-05: Conflict-of-interest vote exclusion guard
            # If outcome is being recorded, block users who declared a conflict
            if 'outcome' in request.data:
                user_id = getattr(request.user, 'id', None)
                has_conflict = ConflictDeclaration.objects.filter(
                    agenda_item=entity,
                    member_user_id=user_id,
                    is_active=True,
                ).exists()
                if has_conflict:
                    return error_response(
                        message="Cannot record outcome — you have declared a conflict of interest on this agenda item",
                        code="CONFLICT_OF_INTEREST",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

            serializer = MeetingAgendaSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=MeetingAgendaSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update agenda item")
            return server_error_response(
                message="Failed to update agenda item",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = get_object_or_404(MeetingAgenda, pk=pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Agenda item deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete agenda item")
            return server_error_response(
                message="Failed to delete agenda item",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Conflict Declaration
# ═══════════════════════════════════════════════════════════════════════════════

class ConflictDeclarationListCreateView(APIView):
    """
    GET  /legal/meetings/{meeting_pk}/conflicts/
    POST /legal/meetings/{meeting_pk}/conflicts/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        can_view = CanViewLegalMeeting().has_permission(request, self)
        can_manage = CanManageLegalMeeting().has_permission(request, self)
        if not (can_view or can_manage):
            self.permission_denied(request, message='grc:legal_meeting:view or :manage required.')

    def get(self, request, meeting_pk):
        try:
            meeting = get_object_or_404(Meeting, pk=meeting_pk)
            queryset = ConflictDeclaration.objects.filter(agenda_item__meeting=meeting)

            page_data = paginate_queryset(queryset, request)
            serializer = ConflictDeclarationSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='conflict_declaration',
            )
        except Exception as e:
            logger.exception("Failed to retrieve conflict declarations")
            return server_error_response(
                message="Failed to retrieve conflict declarations",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, meeting_pk):
        try:
            meeting = get_object_or_404(Meeting, pk=meeting_pk, is_active=True)
            serializer = ConflictDeclarationSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id, meeting=meeting)

            return created_response(
                data=ConflictDeclarationSerializer(entity).data,
                message="Conflict declaration created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create conflict declaration")
            return server_error_response(
                message="Failed to create conflict declaration",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting Participant (Attendance)
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingParticipantListCreateView(APIView):
    """
    GET  /legal/meetings/{meeting_pk}/participants/
    POST /legal/meetings/{meeting_pk}/participants/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalMeeting().has_permission(request, self)
            can_manage = CanManageLegalMeeting().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:legal_meeting:view or :manage required.')
        else:
            if not CanManageLegalMeeting().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_meeting:manage required.')

    def get(self, request, meeting_pk):
        try:
            meeting = get_object_or_404(Meeting, pk=meeting_pk)
            queryset = MeetingParticipant.objects.filter(meeting=meeting)

            page_data = paginate_queryset(queryset, request)
            serializer = MeetingParticipantSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='meeting_participant',
            )
        except Exception as e:
            logger.exception("Failed to retrieve participants")
            return server_error_response(
                message="Failed to retrieve participants",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, meeting_pk):
        try:
            meeting = get_object_or_404(Meeting, pk=meeting_pk, is_active=True)
            serializer = MeetingParticipantSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id, meeting=meeting)

            return created_response(
                data=MeetingParticipantSerializer(entity).data,
                message="Participant added successfully",
            )
        except Exception as e:
            logger.exception("Failed to add participant")
            return server_error_response(
                message="Failed to add participant",
                details=str(e) if settings.DEBUG else None,
            )


class MeetingParticipantDetailView(APIView):
    """
    GET    /legal/participants/<pk>/
    PATCH  /legal/participants/<pk>/
    DELETE /legal/participants/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            can_view = CanViewLegalMeeting().has_permission(request, self)
            can_manage = CanManageLegalMeeting().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(request, message='grc:legal_meeting:view or :manage required.')
        else:
            if not CanManageLegalMeeting().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_meeting:manage required.')

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                MeetingParticipant.objects.select_related('meeting'), pk=pk,
            )
            return success_response(data=MeetingParticipantSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve participant")
            return server_error_response(
                message="Failed to retrieve participant",
                details=str(e) if settings.DEBUG else None,
            )

    def patch(self, request, pk):
        try:
            entity = get_object_or_404(MeetingParticipant, pk=pk)
            serializer = MeetingParticipantSerializer(entity, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=MeetingParticipantSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update participant")
            return server_error_response(
                message="Failed to update participant",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            entity = get_object_or_404(MeetingParticipant, pk=pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Participant removed successfully")
        except Exception as e:
            logger.exception("Failed to remove participant")
            return server_error_response(
                message="Failed to remove participant",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Matters Arising — Auto-Populate from Unresolved Directives
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingSendInvitationsView(APIView):
    """
    POST /legal/meetings/{pk}/send-invitations/
    Transitions meeting status from 'registered' → 'invitations_sent'.
    Secretary-only action. Publishes invitation event to notify participants.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalMeeting().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_meeting:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            meeting = get_object_or_404(Meeting, pk=pk, is_active=True)

            if meeting.status != 'registered':
                return error_response(
                    message=(
                        f"Only registered meetings can have invitations sent. "
                        f"Current status: '{meeting.status}'"
                    ),
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            participant_count = MeetingParticipant.objects.filter(
                meeting=meeting, is_active=True,
            ).count()

            with transaction.atomic():
                meeting.status = 'invitations_sent'
                meeting.modified_by = user_id
                meeting.save(update_fields=['status', 'modified_by'])

            try:
                from apps.infrastructure.services.messaging_service import messaging_service
                from shared.constants.event_types import LEGAL_MEETING_EVENTS
                messaging_service.publish_legal_meeting_event(
                    event_type=LEGAL_MEETING_EVENTS['INVITATIONS_SENT'],
                    meeting_id=meeting.id,
                    additional_data={
                        'governing_body_id': str(meeting.governing_body_id),
                        'reference_number': meeting.meeting_number or '',
                        'participant_count': participant_count,
                        'sent_by': str(user_id),
                    },
                )
            except Exception as pub_err:
                logger.warning(
                    "Failed to publish invitations_sent event for Meeting %s: %s",
                    pk, pub_err,
                )

            return success_response(
                data=MeetingSerializer(meeting).data,
                message="Invitations sent successfully",
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to send meeting invitations")
            return server_error_response(
                message="Failed to send meeting invitations",
                details=str(e) if settings.DEBUG else None,
            )


class MeetingPopulateMattersArisingView(APIView):
    """
    POST /legal/meetings/{pk}/populate-matters-arising/
    Auto-creates agenda items from unresolved directives of the same governing body.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalMeeting().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_meeting:manage required.')

    def post(self, request, pk):
        try:
            meeting = get_object_or_404(Meeting, pk=pk, is_active=True)

            if meeting.status in LOCKED_STATUSES:
                return error_response(
                    message=f"Meeting is locked (status: {meeting.status})",
                    code="MEETING_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # Find unresolved directives for this governing body
            unresolved = MeetingDirective.objects.filter(
                meeting__governing_body=meeting.governing_body,
                fully_closed=False,
                status__in=['open', 'in_progress', 'overdue'],
                is_active=True,
            )

            # Exclude directives already on this meeting's agenda
            existing_directive_ids = set(
                MeetingAgenda.objects.filter(
                    meeting=meeting,
                    source_directive__isnull=False,
                    is_active=True,
                ).values_list('source_directive_id', flat=True)
            )

            to_create = []
            next_order = (
                MeetingAgenda.objects.filter(meeting=meeting, is_active=True)
                .order_by('-order').values_list('order', flat=True).first() or 0
            )

            for directive in unresolved:
                if directive.id in existing_directive_ids:
                    continue
                next_order += 1
                to_create.append(MeetingAgenda(
                    meeting=meeting,
                    source_directive=directive,
                    order=next_order,
                    title=f"Matters Arising: {directive.description[:100]}",
                    description=directive.description,
                    created_by=user_id,
                ))

            created = []
            if to_create:
                with transaction.atomic():
                    created = MeetingAgenda.objects.bulk_create(to_create)

            return success_response(
                data={
                    'created_count': len(created),
                    'items': MeetingAgendaSerializer(created, many=True).data,
                },
            )
        except Exception as e:
            logger.exception("Failed to populate matters arising")
            return server_error_response(
                message="Failed to populate matters arising",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Meeting Directives Sub-Resource (SIG-02 / B4-4)
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingDirectivesSubResourceView(APIView):
    """
    GET /legal/meetings/<pk>/directives/
    Returns directives for a meeting, scoped to invitees (participants).
    Any authenticated participant of the meeting can view.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            meeting = get_object_or_404(Meeting, pk=pk, is_active=True)
            user_id = getattr(request.user, 'id', None)

            # Check if user is a participant of this meeting OR has manage permission
            is_participant = MeetingParticipant.objects.filter(
                meeting=meeting, user_id=user_id, is_active=True,
            ).exists()
            has_manage = CanManageLegalMeeting().has_permission(request, self)
            has_view = CanViewLegalMeeting().has_permission(request, self)

            if not (is_participant or has_manage or has_view):
                self.permission_denied(
                    request,
                    message='Must be a meeting participant or have meeting view/manage permission.',
                )

            from apps.api.serializers.legal_serializers import MeetingDirectiveSerializer
            queryset = MeetingDirective.objects.select_related(
                'meeting', 'agenda_item', 'directive_priority', 'directive_category',
            ).filter(meeting=meeting, is_active=True)

            # Optional filters
            status_filter = request.query_params.get('status')
            assigned_user = request.query_params.get('assigned_user_id')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if assigned_user:
                queryset = queryset.filter(assigned_user_id=assigned_user)

            from apps.api.utils.pagination import paginate_queryset, get_ordering_param
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
        except (exceptions.PermissionDenied, exceptions.NotAuthenticated):
            raise
        except Exception as e:
            logger.exception("Failed to retrieve meeting directives sub-resource")
            return server_error_response(
                message="Failed to retrieve meeting directives",
                details=str(e) if settings.DEBUG else None,
            )
