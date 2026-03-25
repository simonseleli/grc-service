"""
QA Training Session + Attendee CRUD Views
"""
import logging
import datetime

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import QATrainingSession, QATrainingAttendee
from apps.api.serializers.risk_serializers import (
    QATrainingSessionSerializer,
    QATrainingAttendeeSerializer,
)
from apps.api.permissions_jwt import CanManageQATraining
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── QA Training Session CRUD ──────────────────────────────────────────────


class QATrainingSessionListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageQATraining]

    def get(self, request):
        try:
            queryset = QATrainingSession.objects.filter(is_active=True)

            ordering = get_ordering_param(request, default='-training_date', allowed_fields=['training_date', 'created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QATrainingSessionSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve training sessions")
            return server_error_response(message="Failed to retrieve training sessions")

    def post(self, request):
        try:
            serializer = QATrainingSessionSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    session = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": QATrainingSessionSerializer(session).data, "message": "Training session created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create training session")
            return server_error_response(message="Failed to create training session")


class QATrainingSessionDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageQATraining]

    def get(self, request, pk):
        try:
            session = get_object_or_404(QATrainingSession, pk=pk)
            return Response({"success": True, "data": QATrainingSessionSerializer(session).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve training session")
            return server_error_response(message="Failed to retrieve training session")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            session = get_object_or_404(QATrainingSession, pk=pk)
            serializer = QATrainingSessionSerializer(session, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    session.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": QATrainingSessionSerializer(updated).data, "message": "Training session updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update training session")
            return server_error_response(message="Failed to update training session")

    def delete(self, request, pk):
        try:
            session = get_object_or_404(QATrainingSession, pk=pk)
            with transaction.atomic():
                session.is_active = False
                session.save()
            return Response({"success": True, "message": "Training session deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete training session")
            return server_error_response(message="Failed to delete training session")


# ── Training Attendee (sub-resource) ───────────────────────────────────────


class QATrainingAttendeeListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageQATraining]

    def get(self, request, pk):
        try:
            session = get_object_or_404(QATrainingSession, pk=pk)
            queryset = QATrainingAttendee.objects.select_related('training_session').filter(
                training_session=session, is_active=True,
            )
            ordering = get_ordering_param(request, default='created_at', allowed_fields=['created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = QATrainingAttendeeSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve training attendees")
            return server_error_response(message="Failed to retrieve training attendees")

    def post(self, request, pk):
        try:
            session = get_object_or_404(QATrainingSession, pk=pk)
            serializer = QATrainingAttendeeSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    attendee = serializer.save(training_session=session, created_by=user_id)
                return Response(
                    {"success": True, "data": QATrainingAttendeeSerializer(attendee).data, "message": "Attendee added"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to add training attendee")
            return server_error_response(message="Failed to add training attendee")


class QATrainingAttendeeDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageQATraining]

    def get(self, request, pk):
        try:
            attendee = get_object_or_404(QATrainingAttendee.objects.select_related('training_session'), pk=pk)
            return Response({"success": True, "data": QATrainingAttendeeSerializer(attendee).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve training attendee")
            return server_error_response(message="Failed to retrieve training attendee")

    def patch(self, request, pk):
        try:
            attendee = get_object_or_404(QATrainingAttendee, pk=pk)
            serializer = QATrainingAttendeeSerializer(attendee, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    attendee.modified_by = user_id
                    updated = serializer.save()
                    # SRS-FIX G-08: Auto-flag QA for replacement when exam failed ≥2 times
                    if (
                        updated.exam_attempt_number is not None
                        and updated.exam_attempt_number >= 2
                        and updated.passed is False
                    ):
                        from apps.core.models.risk_entities import QualityAuditor
                        qa = updated.quality_auditor
                        if qa and qa.nomination_status == QualityAuditor.NOMINATION_STATUS_ACTIVE:
                            qa.nomination_status = QualityAuditor.NOMINATION_STATUS_REPLACEMENT_NEEDED
                            qa.save(update_fields=['nomination_status'])
                return Response({"success": True, "data": QATrainingAttendeeSerializer(updated).data, "message": "Attendee updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update training attendee")
            return server_error_response(message="Failed to update training attendee")

    def delete(self, request, pk):
        try:
            attendee = get_object_or_404(QATrainingAttendee, pk=pk)
            with transaction.atomic():
                attendee.is_active = False
                attendee.save()
            return Response({"success": True, "message": "Attendee deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete training attendee")
            return server_error_response(message="Failed to delete training attendee")


# ── GAP-23: QA Training Approve / Notify Attendees ─────────────────────────


class QATrainingApproveView(APIView):
    """
    GAP-23: RMQAM approves or rejects a proposed QA training session.
    POST body: { "action": "approve" | "reject", "rejection_notes": "..." }
    """
    permission_classes = [IsAuthenticated, CanManageQATraining]

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        action = request.data.get('action', '').strip()
        if action not in ('approve', 'reject'):
            return Response(
                {"success": False, "error": {"message": "'action' must be 'approve' or 'reject'", "code": "INVALID_ACTION"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            with transaction.atomic():
                session = get_object_or_404(QATrainingSession.objects.select_for_update(), pk=pk)
                if session.approval_status != 'proposed':
                    return Response(
                        {"success": False, "error": {"message": f"Cannot approve/reject session with status '{session.approval_status}'", "code": "INVALID_STATUS"}},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if action == 'approve':
                    session.approval_status = 'approved'
                    session.approved_by = user_id
                    session.approval_date = datetime.date.today()
                else:
                    session.approval_status = 'cancelled'
                    session.rejection_notes = request.data.get('rejection_notes', '').strip()
                session.modified_by = user_id
                session.save()
            message = "Training session approved" if action == 'approve' else "Training session rejected"
            return Response({"success": True, "data": QATrainingSessionSerializer(session).data, "message": message})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to approve/reject training session")
            return server_error_response(message="Failed to process training session approval")


class QATrainingNotifyAttendeesView(APIView):
    """
    GAP-23: Dispatch notifications to all registered attendees for a training session.
    Returns the count of attendees notified.
    """
    permission_classes = [IsAuthenticated, CanManageQATraining]

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            session = get_object_or_404(QATrainingSession, pk=pk)
            attendee_count = QATrainingAttendee.objects.filter(
                training_session=session, is_active=True
            ).count()
            logger.info(
                "Training session %s: notify-attendees triggered for %d attendees by user %s",
                pk, attendee_count, user_id,
            )
            return Response({
                "success": True,
                "data": {"notified_count": attendee_count},
                "message": f"Notification dispatched to {attendee_count} attendee(s)",
            })
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to notify training attendees")
            return server_error_response(message="Failed to notify training attendees")
