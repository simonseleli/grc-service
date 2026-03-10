"""
Engagement Notification Views for GRC Service (P2-GAP 1 — SRS Req 24, 25, 26)
CRUD + submit + transmit + workflow-status for Engagement Notifications.

Follows audit_program_views.py pattern exactly.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import EngagementNotification, AuditEngagement
from apps.api.serializers.audit_serializers import (
    EngagementNotificationSerializer,
    EngagementNotificationListSerializer,
)
from apps.api.permissions_jwt import (
    CanManageEngagementNotification,
    CanApproveEngagementNotification,
)
from apps.core.services.engagement_notification_service import EngagementNotificationService
from apps.infrastructure.external.orchestration_client import OrchestrationClient

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    error_response,
    not_found_response,
    validation_error_response,
    conflict_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


def _generate_en_reference(engagement: AuditEngagement) -> str:
    """Generate a unique Engagement Notification reference: EN-{engagement_ref}"""
    return f"EN-{engagement.reference_number}"


# ─── List / Create ────────────────────────────────────────────────────────────

class EngagementNotificationListCreateView(APIView):
    """List all engagement notifications or create a new one."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageEngagementNotification().has_permission(request, self):
            self.permission_denied(
                request, message='grc:engagement_notification:manage required.'
            )

    def get(self, request):
        try:
            engagement_id = request.query_params.get('audit_engagement')
            status_filter = request.query_params.get('status')

            queryset = EngagementNotification.objects.select_related(
                'audit_engagement', 'audit_program',
            ).all()

            if engagement_id:
                queryset = queryset.filter(audit_engagement_id=engagement_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status', 'reference_number', 'notification_date'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = EngagementNotificationListSerializer(
                page_data['queryset'], many=True
            )
            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='engagement_notification',
            )
        except Exception as exc:
            logger.exception("Failed to retrieve engagement notifications")
            return server_error_response(
                message="Failed to retrieve engagement notifications",
                details=str(exc) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = EngagementNotificationSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            engagement_id = serializer.validated_data['audit_engagement_id']
            engagement = get_object_or_404(AuditEngagement, id=engagement_id)

            # Business guard: parent engagement must be in planning phase
            if engagement.status != 'planning':
                return error_response(
                    message="Engagement Notification can only be created during the planning phase",
                    code="INVALID_ENGAGEMENT_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # One EN per engagement (OneToOne relationship)
            if EngagementNotification.objects.filter(audit_engagement=engagement).exists():
                return error_response(
                    message="An Engagement Notification already exists for this engagement",
                    code="EN_EXISTS",
                    status_code=status.HTTP_409_CONFLICT,
                )

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated",
                    code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                reference = (
                    serializer.validated_data.get('reference_number')
                    or _generate_en_reference(engagement)
                )
                prepared_by = serializer.validated_data.get('prepared_by', user_id)

                en = serializer.save(
                    audit_engagement=engagement,
                    reference_number=reference,
                    prepared_by=prepared_by,
                    created_by=user_id,
                    status='draft',
                )

            return Response(
                {
                    "success": True,
                    "data": EngagementNotificationSerializer(en).data,
                    "message": "Engagement Notification created successfully",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            logger.exception("Failed to create engagement notification")
            return server_error_response(
                message="Failed to create engagement notification",
                details=str(exc) if settings.DEBUG else None,
            )


# ─── Detail (GET / PUT / DELETE) ─────────────────────────────────────────────

class EngagementNotificationDetailView(APIView):
    """Retrieve, update, or soft-delete an engagement notification."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageEngagementNotification().has_permission(request, self):
            self.permission_denied(
                request, message='grc:engagement_notification:manage required.'
            )

    def get(self, request, pk):
        try:
            en = EngagementNotification.objects.select_related(
                'audit_engagement', 'audit_program',
            ).get(pk=pk)
            return success_response(
                data=EngagementNotificationSerializer(en).data,
            )
        except EngagementNotification.DoesNotExist:
            return not_found_response('Engagement Notification not found')

    def put(self, request, pk):
        try:
            en = EngagementNotification.objects.select_related(
                'audit_engagement', 'audit_program',
            ).get(pk=pk)
        except EngagementNotification.DoesNotExist:
            return not_found_response('Engagement Notification not found')

        try:
            if en.status != 'draft':
                return error_response(
                    message="Only draft Engagement Notifications can be edited",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = EngagementNotificationSerializer(
                en, data=request.data, partial=True
            )
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                serializer.save(modified_by=user_id)

            return success_response(
                data=EngagementNotificationSerializer(en).data,
            )
        except Exception as exc:
            logger.exception("Failed to update engagement notification %s", pk)
            return server_error_response(
                message="Failed to update engagement notification",
                details=str(exc) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            en = EngagementNotification.objects.get(pk=pk)
        except EngagementNotification.DoesNotExist:
            return not_found_response('Engagement Notification not found')

        try:
            if en.status != 'draft':
                return error_response(
                    message="Only draft Engagement Notifications can be deleted",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            en.is_active = False
            en.save(update_fields=['is_active'])
            return success_response(
                data={"id": str(pk)}, message="Engagement Notification soft-deleted"
            )
        except Exception as exc:
            logger.exception("Failed to delete engagement notification %s", pk)
            return server_error_response(
                message="Failed to delete engagement notification",
                details=str(exc) if settings.DEBUG else None,
            )


# ─── Submit for CIA Approval ──────────────────────────────────────────────────

class EngagementNotificationSubmitView(APIView):
    """
    Submit a draft Engagement Notification for CIA approval
    via the Work Orchestration Service.
    SRS Req 25 — CIA must approve before transmission.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageEngagementNotification().has_permission(request, self):
            self.permission_denied(
                request, message='grc:engagement_notification:manage required.'
            )

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated",
                code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            en = EngagementNotification.objects.get(pk=pk)
        except EngagementNotification.DoesNotExist:
            return not_found_response('Engagement Notification not found')

        try:
            if en.status != 'draft':
                return error_response(
                    message=(
                        f"Only draft Engagement Notifications can be submitted. "
                        f"Current status: '{en.status}'"
                    ),
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            if en.workflow_plan_id:
                return conflict_response(
                    message="Approval workflow already in progress for this Engagement Notification",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.removeprefix('Bearer ').strip() or None

            # Delegate to service — handles workflow start + WF field saves + notification
            service = EngagementNotificationService()
            en = service.submit_for_approval(
                en_id=str(pk),
                submitter_id=str(user_id),
                auth_token=auth_token,
            )

            return success_response(
                data=EngagementNotificationSerializer(en).data,
                message="Engagement Notification submitted for CIA approval",
            )
        except Exception as exc:
            logger.exception("Error submitting EngagementNotification %s for approval", pk)
            return server_error_response(
                message="Failed to submit Engagement Notification for approval",
                details=str(exc) if settings.DEBUG else None,
            )


# ─── Transmit to Auditable Area ───────────────────────────────────────────────

class EngagementNotificationTransmitView(APIView):
    """
    Mark an approved Engagement Notification as transmitted to the auditable area.
    This also advances the parent AuditEngagement to 'fieldwork' status.
    SRS Req 26.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageEngagementNotification().has_permission(request, self):
            self.permission_denied(
                request, message='grc:engagement_notification:manage required.'
            )

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated",
                code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            service = EngagementNotificationService()
            en = service.transmit(en_id=str(pk), transmitter_id=str(user_id))

            return success_response(
                data=EngagementNotificationSerializer(en).data,
                message="Engagement Notification transmitted to auditable area",
            )
        except EngagementNotification.DoesNotExist:
            return not_found_response('Engagement Notification not found')
        except ValueError as ve:
            return error_response(
                message=str(ve),
                code="INVALID_STATUS",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Error transmitting EngagementNotification %s", pk)
            return server_error_response(
                message="Failed to transmit Engagement Notification",
                details=str(exc) if settings.DEBUG else None,
            )


# ─── Workflow Status ──────────────────────────────────────────────────────────

class EngagementNotificationWorkflowStatusView(APIView):
    """Get current workflow status for an Engagement Notification from WO Service."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            en = EngagementNotification.objects.get(pk=pk)
        except EngagementNotification.DoesNotExist:
            return not_found_response('Engagement Notification not found')

        try:
            if not en.workflow_plan_id:
                return error_response(
                    message="No approval workflow has been started for this Engagement Notification",
                    code="NO_WORKFLOW",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.removeprefix('Bearer ').strip() or None

            client = OrchestrationClient()
            wo_status = client.get_plan_status(
                str(en.workflow_plan_id), auth_token=auth_token
            )

            return success_response(data={
                "engagement_notification_id": str(en.id),
                "reference_number": en.reference_number,
                "workflow_plan_id": str(en.workflow_plan_id),
                "workflow_stage": en.workflow_stage,
                "en_status": en.status,
                "wo_status": wo_status,
            })
        except Exception as exc:
            logger.exception("Error fetching workflow status for EN %s", pk)
            return server_error_response(
                message="Failed to get Engagement Notification workflow status",
                details=str(exc) if settings.DEBUG else None,
            )
