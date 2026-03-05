"""
Audit Survey Views for GRC Service (GAP 3 — SRS Req 19-21)
Preliminary survey including Fraud Risk Assessment.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditSurvey, AuditEngagement
from apps.api.serializers.audit_serializers import AuditSurveySerializer
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_SURVEY_EVENTS
from apps.api.permissions_jwt import CanManageAuditSurvey

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    error_response,
    not_found_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


class AuditSurveyListCreateView(APIView):
    """List all surveys or create a new one."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditSurvey().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_survey:manage required.')

    def get(self, request):
        try:
            engagement_id = request.query_params.get('audit_engagement')
            status_filter = request.query_params.get('status')

            queryset = AuditSurvey.objects.select_related('audit_engagement').all()

            if engagement_id:
                queryset = queryset.filter(audit_engagement_id=engagement_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status', 'survey_date'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = AuditSurveySerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_survey",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit surveys")
            return server_error_response(
                message="Failed to retrieve audit surveys",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = AuditSurveySerializer(data=request.data)
            if serializer.is_valid():
                engagement_id = serializer.validated_data['audit_engagement_id']
                engagement = get_object_or_404(AuditEngagement, id=engagement_id)

                # Business guard: engagement must be in planning phase
                if engagement.status != 'planning':
                    return error_response(
                        message="Survey can only be created during the planning phase",
                        code="INVALID_ENGAGEMENT_STATUS",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                # One survey per engagement
                if AuditSurvey.objects.filter(audit_engagement=engagement).exists():
                    return error_response(
                        message="A survey already exists for this engagement",
                        code="SURVEY_EXISTS",
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
                    surveyed_by = serializer.validated_data.get('surveyed_by', user_id)
                    survey = serializer.save(created_by=user_id, surveyed_by=surveyed_by)

                try:
                    messaging_service.publish_audit_plan_event(
                        event_type=AUDIT_SURVEY_EVENTS['SURVEY_CREATED'],
                        plan_id=engagement.audit_plan_id,
                        additional_data={
                            'survey_id': str(survey.id),
                            'engagement_id': str(engagement.id),
                        },
                    )
                except Exception as event_error:
                    logger.error("Error publishing survey created event: %s", event_error)

                return Response(
                    {
                        "success": True,
                        "data": AuditSurveySerializer(survey).data,
                        "message": "Audit survey created successfully",
                    },
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to create audit survey")
            return server_error_response(
                message="Failed to create audit survey",
                details=str(e) if settings.DEBUG else None,
            )


class AuditSurveyDetailView(APIView):
    """Retrieve, update, or delete an audit survey."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditSurvey().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_survey:manage required.')

    def get(self, request, pk):
        try:
            survey = AuditSurvey.objects.select_related('audit_engagement').get(pk=pk)
            return success_response(
                data=AuditSurveySerializer(survey).data,
                resource="audit_survey",
            )
        except AuditSurvey.DoesNotExist:
            return not_found_response(resource="audit_survey")

    def put(self, request, pk):
        try:
            survey = get_object_or_404(AuditSurvey, pk=pk)
            if survey.status != 'draft':
                return error_response(
                    message="Only draft surveys can be edited",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = AuditSurveySerializer(survey, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                with transaction.atomic():
                    serializer.save(modified_by=user_id)
                return success_response(
                    data=AuditSurveySerializer(survey).data,
                    resource="audit_survey",
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to update audit survey %s", pk)
            return server_error_response(
                message="Failed to update audit survey",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            survey = get_object_or_404(AuditSurvey, pk=pk)
            if survey.status != 'draft':
                return error_response(
                    message="Only draft surveys can be deleted",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            survey.is_active = False
            survey.save(update_fields=['is_active'])
            return success_response(data={"id": str(pk)}, message="Audit survey soft-deleted")
        except Exception as e:
            logger.exception("Failed to delete audit survey %s", pk)
            return server_error_response(
                message="Failed to delete audit survey",
                details=str(e) if settings.DEBUG else None,
            )


class AuditSurveyCompleteView(APIView):
    """Mark a survey as completed."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditSurvey().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_survey:manage required.')

    def post(self, request, pk):
        try:
            survey = get_object_or_404(AuditSurvey, pk=pk)
            if survey.status != 'draft':
                return error_response(
                    message="Only draft surveys can be completed",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                survey.status = 'completed'
                survey.save(update_fields=['status'])

            try:
                messaging_service.publish_audit_plan_event(
                    event_type=AUDIT_SURVEY_EVENTS['SURVEY_COMPLETED'],
                    plan_id=survey.audit_engagement.audit_plan_id,
                    additional_data={
                        'survey_id': str(survey.id),
                        'engagement_id': str(survey.audit_engagement_id),
                    },
                )
            except Exception as event_error:
                logger.error("Error publishing survey completed event: %s", event_error)

            return success_response(
                data=AuditSurveySerializer(survey).data,
                message="Audit survey marked as completed",
            )
        except Exception as e:
            logger.exception("Error completing audit survey %s", pk)
            return server_error_response(
                message="Failed to complete audit survey",
                details=str(e) if settings.DEBUG else None,
            )


class EngagementSurveyView(APIView):
    """Get the survey for a specific engagement."""

    permission_classes = [IsAuthenticated]

    def get(self, request, engagement_id):
        try:
            engagement = get_object_or_404(AuditEngagement, pk=engagement_id)
            try:
                survey = AuditSurvey.objects.get(audit_engagement=engagement)
                return success_response(
                    data=AuditSurveySerializer(survey).data,
                    resource="audit_survey",
                )
            except AuditSurvey.DoesNotExist:
                return success_response(data=None, message="No survey exists for this engagement")
        except Exception as e:
            logger.exception("Error fetching survey for engagement %s", engagement_id)
            return server_error_response(
                message="Failed to fetch engagement survey",
                details=str(e) if settings.DEBUG else None,
            )
