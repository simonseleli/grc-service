"""
Risk Meeting + Meeting Attendance CRUD Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import RiskMeeting, MeetingAttendance
from apps.api.serializers.risk_serializers import (
    RiskMeetingSerializer,
    MeetingAttendanceSerializer,
)
from apps.api.permissions_jwt import (
    CanManageRiskMeeting,
    CanViewRiskMeeting,
    HasAnyPermission,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── Risk Meeting CRUD ──────────────────────────────────────────────────────


class RiskMeetingListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:risk_meeting:manage', 'grc:risk_meeting:view']).has_permission(request, self):
                self.permission_denied(request, message='Risk meeting permission required.')
        elif request.method == 'POST':
            if not CanManageRiskMeeting().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_meeting:manage required.')

    def get(self, request):
        try:
            queryset = RiskMeeting.objects.filter(is_active=True)

            meeting_type = request.query_params.get('meeting_type')
            status_filter = request.query_params.get('status')
            if meeting_type:
                queryset = queryset.filter(meeting_type=meeting_type)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(request, default='-meeting_date', allowed_fields=['meeting_date', 'created_at', 'status'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskMeetingSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve risk meetings")
            return server_error_response(message="Failed to retrieve risk meetings")

    def post(self, request):
        try:
            serializer = RiskMeetingSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    meeting = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": RiskMeetingSerializer(meeting).data, "message": "Risk meeting created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create risk meeting")
            return server_error_response(message="Failed to create risk meeting")


class RiskMeetingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission(['grc:risk_meeting:manage', 'grc:risk_meeting:view']).has_permission(request, self):
                self.permission_denied(request, message='Risk meeting permission required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageRiskMeeting().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_meeting:manage required.')

    def get(self, request, pk):
        try:
            meeting = get_object_or_404(RiskMeeting, pk=pk)
            return Response({"success": True, "data": RiskMeetingSerializer(meeting).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve risk meeting")
            return server_error_response(message="Failed to retrieve risk meeting")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            meeting = get_object_or_404(RiskMeeting, pk=pk)
            serializer = RiskMeetingSerializer(meeting, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    meeting.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RiskMeetingSerializer(updated).data, "message": "Risk meeting updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update risk meeting")
            return server_error_response(message="Failed to update risk meeting")

    def delete(self, request, pk):
        try:
            meeting = get_object_or_404(RiskMeeting, pk=pk)
            with transaction.atomic():
                meeting.is_active = False
                meeting.save()
            return Response({"success": True, "message": "Risk meeting deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete risk meeting")
            return server_error_response(message="Failed to delete risk meeting")


# ── Meeting Attendance (sub-resource) ──────────────────────────────────────


class MeetingAttendanceListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageRiskMeeting]

    def get(self, request, pk):
        try:
            meeting = get_object_or_404(RiskMeeting, pk=pk)
            queryset = MeetingAttendance.objects.select_related('meeting').filter(
                meeting=meeting, is_active=True,
            )
            ordering = get_ordering_param(request, default='created_at', allowed_fields=['created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = MeetingAttendanceSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve meeting attendance")
            return server_error_response(message="Failed to retrieve meeting attendance")

    def post(self, request, pk):
        try:
            meeting = get_object_or_404(RiskMeeting, pk=pk)
            serializer = MeetingAttendanceSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    attendance = serializer.save(meeting=meeting, created_by=user_id)
                return Response(
                    {"success": True, "data": MeetingAttendanceSerializer(attendance).data, "message": "Attendance recorded"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to record meeting attendance")
            return server_error_response(message="Failed to record meeting attendance")


class MeetingAttendanceDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageRiskMeeting]

    def get(self, request, pk):
        try:
            attendance = get_object_or_404(MeetingAttendance.objects.select_related('meeting'), pk=pk)
            return Response({"success": True, "data": MeetingAttendanceSerializer(attendance).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve meeting attendance")
            return server_error_response(message="Failed to retrieve meeting attendance")

    def patch(self, request, pk):
        try:
            attendance = get_object_or_404(MeetingAttendance, pk=pk)
            serializer = MeetingAttendanceSerializer(attendance, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    attendance.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": MeetingAttendanceSerializer(updated).data, "message": "Attendance updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update meeting attendance")
            return server_error_response(message="Failed to update meeting attendance")

    def delete(self, request, pk):
        try:
            attendance = get_object_or_404(MeetingAttendance, pk=pk)
            with transaction.atomic():
                attendance.is_active = False
                attendance.save()
            return Response({"success": True, "message": "Attendance deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete meeting attendance")
            return server_error_response(message="Failed to delete meeting attendance")
