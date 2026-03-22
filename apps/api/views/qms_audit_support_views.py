"""
QMS Audit Meeting + Timetable Entry CRUD Views (plan-scoped sub-resources)
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import QMSAuditPlan, QMSAuditMeeting, QMSAuditTimetableEntry
from apps.api.serializers.risk_serializers import (
    QMSAuditMeetingSerializer,
    QMSAuditTimetableEntrySerializer,
)
from apps.api.permissions_jwt import CanManageQMSAuditPlan
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── QMS Audit Meeting (plan-scoped) ───────────────────────────────────────


class QMSAuditMeetingListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def get(self, request, pk):
        try:
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            queryset = QMSAuditMeeting.objects.select_related('audit_plan').filter(
                audit_plan=plan, is_active=True,
            )
            ordering = get_ordering_param(request, default='-meeting_date', allowed_fields=['meeting_date', 'created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QMSAuditMeetingSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve audit meetings")
            return server_error_response(message="Failed to retrieve audit meetings")

    def post(self, request, pk):
        try:
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            serializer = QMSAuditMeetingSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    meeting = serializer.save(audit_plan=plan, created_by=user_id)
                return Response(
                    {"success": True, "data": QMSAuditMeetingSerializer(meeting).data, "message": "Audit meeting created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create audit meeting")
            return server_error_response(message="Failed to create audit meeting")


class QMSAuditMeetingDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def get(self, request, pk):
        try:
            meeting = get_object_or_404(QMSAuditMeeting.objects.select_related('audit_plan'), pk=pk)
            return Response({"success": True, "data": QMSAuditMeetingSerializer(meeting).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve audit meeting")
            return server_error_response(message="Failed to retrieve audit meeting")

    def patch(self, request, pk):
        try:
            meeting = get_object_or_404(QMSAuditMeeting, pk=pk)
            serializer = QMSAuditMeetingSerializer(meeting, data=request.data, partial=True)
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
                return Response({"success": True, "data": QMSAuditMeetingSerializer(updated).data, "message": "Audit meeting updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update audit meeting")
            return server_error_response(message="Failed to update audit meeting")

    def delete(self, request, pk):
        try:
            meeting = get_object_or_404(QMSAuditMeeting, pk=pk)
            with transaction.atomic():
                meeting.is_active = False
                meeting.save()
            return Response({"success": True, "message": "Audit meeting deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete audit meeting")
            return server_error_response(message="Failed to delete audit meeting")


# ── QMS Audit Timetable Entry (plan-scoped) ────────────────────────────────


class QMSAuditTimetableEntryListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def get(self, request, pk):
        try:
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            queryset = QMSAuditTimetableEntry.objects.select_related('audit_plan').filter(
                audit_plan=plan, is_active=True,
            )
            ordering = get_ordering_param(request, default='sort_order', allowed_fields=['sort_order', 'created_at', 'scheduled_date'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QMSAuditTimetableEntrySerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve timetable entries")
            return server_error_response(message="Failed to retrieve timetable entries")

    def post(self, request, pk):
        try:
            plan = get_object_or_404(QMSAuditPlan, pk=pk)
            serializer = QMSAuditTimetableEntrySerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    entry = serializer.save(audit_plan=plan, created_by=user_id)
                return Response(
                    {"success": True, "data": QMSAuditTimetableEntrySerializer(entry).data, "message": "Timetable entry created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create timetable entry")
            return server_error_response(message="Failed to create timetable entry")


class QMSAuditTimetableEntryDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSAuditPlan]

    def get(self, request, pk):
        try:
            entry = get_object_or_404(QMSAuditTimetableEntry.objects.select_related('audit_plan'), pk=pk)
            return Response({"success": True, "data": QMSAuditTimetableEntrySerializer(entry).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve timetable entry")
            return server_error_response(message="Failed to retrieve timetable entry")

    def patch(self, request, pk):
        try:
            entry = get_object_or_404(QMSAuditTimetableEntry, pk=pk)
            serializer = QMSAuditTimetableEntrySerializer(entry, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    entry.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": QMSAuditTimetableEntrySerializer(updated).data, "message": "Timetable entry updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update timetable entry")
            return server_error_response(message="Failed to update timetable entry")

    def delete(self, request, pk):
        try:
            entry = get_object_or_404(QMSAuditTimetableEntry, pk=pk)
            with transaction.atomic():
                entry.is_active = False
                entry.save()
            return Response({"success": True, "message": "Timetable entry deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete timetable entry")
            return server_error_response(message="Failed to delete timetable entry")
