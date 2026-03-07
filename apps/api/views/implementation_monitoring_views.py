"""
Implementation Monitoring CRUD Views for GRC Service
Provides full CRUD operations for tracking recommendation implementation progress
"""

import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import (
    ImplementationMonitoring, AuditRecommendation, AuditeeFollowUpResponse
)
from apps.api.serializers.audit_serializers import (
    ImplementationMonitoringSerializer,
    AuditeeFollowUpResponseSerializer,
)
from apps.api.permissions_jwt import CanUpdateAuditMonitoring

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    created_response,
    error_response,
    not_found_response,
    validation_error_response,
    conflict_response,
    server_error_response,
)



class ImplementationMonitoringListCreateView(APIView):
    """List all implementation monitoring records or create a new one"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def get(self, request):
        """Get all implementation monitoring records with optional filtering and pagination"""
        try:
            # Get query parameters for filtering
            recommendation_id = request.query_params.get('recommendation')
            reviewed_by = request.query_params.get('reviewed_by')
            progress_min = request.query_params.get('progress_min')
            progress_max = request.query_params.get('progress_max')
            is_active = request.query_params.get('is_active')
            
            # Build query with related data
            queryset = ImplementationMonitoring.objects.select_related(
                'recommendation',
                'recommendation__finding',
                'recommendation__finding__engagement'
            ).all()
            
            # Apply filters
            if recommendation_id:
                queryset = queryset.filter(recommendation_id=recommendation_id)
            if reviewed_by:
                queryset = queryset.filter(reviewed_by=reviewed_by)
            if progress_min:
                queryset = queryset.filter(latest_progress__gte=float(progress_min))
            if progress_max:
                queryset = queryset.filter(latest_progress__lte=float(progress_max))
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-last_review_date',
                allowed_fields=['last_review_date', 'next_review_date', 'latest_progress', 'created_at']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = ImplementationMonitoringSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="implementation_monitoring",
            )
        except Exception as e:
            logger.exception("Failed to retrieve implementation monitoring records")
            return server_error_response(
                message="Failed to retrieve implementation monitoring records",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create a new implementation monitoring record"""
        try:
            serializer = ImplementationMonitoringSerializer(data=request.data)
            
            if serializer.is_valid():
                recommendation_id = serializer.validated_data['recommendation_id']
                
                # Verify recommendation exists
                recommendation = get_object_or_404(AuditRecommendation, id=recommendation_id)
                
                # Check if recommendation already has monitoring
                if hasattr(recommendation, 'monitoring') and recommendation.monitoring:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Monitoring record already exists for this recommendation",
                                "code": "MONITORING_EXISTS"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Only create monitoring for recommendations that are in_progress or later
                if recommendation.status == 'open':
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Cannot create monitoring for recommendation that hasn't started implementation",
                                "code": "RECOMMENDATION_NOT_STARTED"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                with transaction.atomic():
                    # Get user ID from request or use system user
                    # FIMS pattern: always require authenticated user — no system user fallback
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    
                    monitoring = serializer.save(created_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": ImplementationMonitoringSerializer(monitoring).data,
                        "message": "Implementation monitoring record created successfully"
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Validation failed",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to create implementation monitoring record",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ImplementationMonitoringDetailView(APIView):
    """Retrieve, update, or delete a specific implementation monitoring record"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def get(self, request, pk):
        """Get a specific implementation monitoring record by ID"""
        try:
            monitoring = get_object_or_404(
                ImplementationMonitoring.objects.select_related(
                    'recommendation',
                    'recommendation__finding',
                    'recommendation__finding__engagement'
                ),
                pk=pk
            )
            
            serializer = ImplementationMonitoringSerializer(monitoring)
            
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "meta": {
                        "service": "grc-service",
                        "resource": "implementation_monitoring",
                        "version": "v1.0",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to retrieve implementation monitoring record",
                        "details": str(e)
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Update an implementation monitoring record (full update)"""
        try:
            monitoring = get_object_or_404(ImplementationMonitoring, pk=pk)
            
            # Check if associated recommendation is closed
            if monitoring.recommendation.status == 'closed':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update monitoring for closed recommendation",
                            "code": "RECOMMENDATION_CLOSED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = ImplementationMonitoringSerializer(monitoring, data=request.data)
            
            if serializer.is_valid():
                with transaction.atomic():
                    # Get user ID for modified_by tracking
                    # FIMS pattern: always require authenticated user — no system user fallback
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    
                    updated_monitoring = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": ImplementationMonitoringSerializer(updated_monitoring).data,
                        "message": "Implementation monitoring record updated successfully"
                    }
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Validation failed",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update implementation monitoring record",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Partially update an implementation monitoring record"""
        try:
            monitoring = get_object_or_404(ImplementationMonitoring, pk=pk)
            
            # Check if associated recommendation is closed
            if monitoring.recommendation.status == 'closed':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update monitoring for closed recommendation",
                            "code": "RECOMMENDATION_CLOSED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = ImplementationMonitoringSerializer(monitoring, data=request.data, partial=True)
            
            if serializer.is_valid():
                with transaction.atomic():
                    # Get user ID for modified_by tracking
                    # FIMS pattern: always require authenticated user — no system user fallback
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    
                    updated_monitoring = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": ImplementationMonitoringSerializer(updated_monitoring).data,
                        "message": "Implementation monitoring record updated successfully"
                    }
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Validation failed",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update implementation monitoring record",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Soft delete an implementation monitoring record"""
        try:
            monitoring = get_object_or_404(ImplementationMonitoring, pk=pk)
            
            # Prevent deletion if recommendation is verified or closed
            if monitoring.recommendation.status in ['verified', 'closed']:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot delete monitoring for {monitoring.recommendation.status} recommendation",
                            "code": "RECOMMENDATION_LOCKED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                monitoring.is_active = False
                monitoring.save(update_fields=['is_active'])
            
            return Response(
                {
                    "success": True,
                    "message": "Implementation monitoring record deleted successfully"
                },
                status=status.HTTP_200_OK
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete implementation monitoring record",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ImplementationMonitoringReviewView(APIView):
    """Record implementation review updates"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def post(self, request, pk):
        """Open a new review cycle (creates AuditeeFollowUpResponse row at cycle_number = max+1)."""
        try:
            monitoring = get_object_or_404(ImplementationMonitoring, pk=pk)

            # Check if recommendation is closed
            if monitoring.recommendation.status == 'closed':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot review monitoring for closed recommendation",
                            "code": "RECOMMENDATION_CLOSED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract review data
            implementation_progress = request.data.get('implementation_progress')
            next_review_date = request.data.get('next_review_date')

            # Validate required field
            if implementation_progress is None:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Implementation progress percentage required",
                            "code": "MISSING_PROGRESS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate progress percentage
            try:
                progress = float(implementation_progress)
                if progress < 0 or progress > 100:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Progress must be between 0 and 100",
                                "code": "INVALID_PROGRESS"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid progress value",
                            "code": "INVALID_PROGRESS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

                # Determine next cycle number
                last_cycle = monitoring.follow_up_responses.order_by('-cycle_number').first()
                next_cycle_number = (last_cycle.cycle_number + 1) if last_cycle else 1

                # Create the new cycle (pending — awaiting notify-auditee then submission)
                cycle = AuditeeFollowUpResponse.objects.create(
                    monitoring=monitoring,
                    cycle_number=next_cycle_number,
                    status='pending',
                    created_by=user_id,
                )

                # Update header snapshot fields
                monitoring.latest_progress = progress
                monitoring.last_review_date = timezone.now().date()
                monitoring.reviewed_by = user_id
                # Reset per-cycle notification/response fields for the new cycle
                monitoring.notification_sent_at = None
                monitoring.response_deadline = None
                monitoring.auditee_responded_at = None
                monitoring.is_overdue = False

                if next_review_date:
                    monitoring.next_review_date = next_review_date

                monitoring.save(update_fields=[
                    'latest_progress', 'last_review_date', 'next_review_date',
                    'reviewed_by', 'notification_sent_at', 'response_deadline',
                    'auditee_responded_at', 'is_overdue',
                ])

            return Response(
                {
                    "success": True,
                    "data": ImplementationMonitoringSerializer(monitoring).data,
                    "current_cycle": AuditeeFollowUpResponseSerializer(cycle).data,
                    "message": f"Review cycle {next_cycle_number} opened. Call /notify-auditee/ to notify the auditee."
                }
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to open review cycle",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ImplementationMonitoringDueReviewsView(APIView):
    """Get monitoring records due for review"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def get(self, request):
        """Get all monitoring records where next_review_date has passed, with pagination"""
        try:
            today = timezone.now().date()
            
            # Get monitoring records due for review
            queryset = ImplementationMonitoring.objects.select_related(
                'recommendation',
                'recommendation__finding',
                'recommendation__finding__engagement'
            ).filter(
                next_review_date__lte=today,
                recommendation__status__in=['in_progress', 'implemented'],
                is_active=True
            ).order_by('next_review_date')
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = ImplementationMonitoringSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="implementation_monitoring_due",
                as_of_date=today.isoformat(),
            )
        except Exception as e:
            logger.exception("Failed to retrieve due reviews")
            return server_error_response(
                message="Failed to retrieve due reviews",
                details=str(e) if settings.DEBUG else None,
            )


class ImplementationMonitoringNotifyAuditeeView(APIView):
    """Send notification to auditee and start the 5-day response window (GAP 7)."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    @staticmethod
    def _add_business_days(start_dt, num_days):
        """Add `num_days` business days (Mon-Fri) to a datetime."""
        import datetime
        current = start_dt
        added = 0
        while added < num_days:
            current += datetime.timedelta(days=1)
            if current.weekday() < 5:  # Mon=0 … Fri=4
                added += 1
        return current

    def post(self, request, pk):
        """Notify auditee: sets notification timestamps on the current open cycle + mirrors to header."""
        try:
            monitoring = get_object_or_404(ImplementationMonitoring, pk=pk)

            # Find the current open cycle (latest pending — created by /review/)
            current_cycle = (
                monitoring.follow_up_responses
                .filter(status='pending')
                .order_by('-cycle_number')
                .first()
            )

            if current_cycle is None:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "No open review cycle. Call /review/ first to create a new cycle.",
                            "code": "NO_OPEN_CYCLE",
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if current_cycle.notified_at:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Auditee has already been notified for this cycle",
                            "code": "ALREADY_NOTIFIED",
                            "notified_at": current_cycle.notified_at.isoformat(),
                            "deadline": current_cycle.response_deadline.isoformat() if current_cycle.response_deadline else None,
                        },
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            now = timezone.now()
            deadline = self._add_business_days(now, 5)

            with transaction.atomic():
                # Update the cycle row
                current_cycle.notified_at = now
                current_cycle.response_deadline = deadline
                current_cycle.save(update_fields=['notified_at', 'response_deadline'])

                # Mirror to header for quick querying
                monitoring.notification_sent_at = now
                monitoring.response_deadline = deadline
                monitoring.save(update_fields=['notification_sent_at', 'response_deadline'])

            # Publish notification event via Kafka → WO Service delivers email/SMS/in-app
            try:
                from apps.infrastructure.services.messaging_service import messaging_service
                messaging_service.publish_audit_plan_event(
                    event_type='monitoring.auditee_notified',
                    plan_id=monitoring.recommendation.finding.engagement.audit_plan_id,
                    additional_data={
                        'monitoring_id': str(monitoring.id),
                        'recommendation_id': str(monitoring.recommendation_id),
                        'cycle_number': current_cycle.cycle_number,
                        'deadline': deadline.isoformat(),
                    },
                )
            except Exception as event_error:
                logger.error("Error publishing auditee notification event: %s", event_error)

            return success_response(
                data=ImplementationMonitoringSerializer(monitoring).data,
                message=f"Auditee notified (cycle {current_cycle.cycle_number}). Response deadline: {deadline.strftime('%Y-%m-%d %H:%M')}",
            )
        except Exception as e:
            logger.exception("Failed to notify auditee for monitoring %s", pk)
            return server_error_response(
                message="Failed to notify auditee",
                details=str(e) if settings.DEBUG else None,
            )


class ImplementationMonitoringNonResponsiveView(APIView):
    """List monitoring records where auditee has not responded after notification (GAP 7)."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def get(self, request):
        """Get all non-responsive monitoring records (notified but no response)."""
        try:
            queryset = ImplementationMonitoring.objects.select_related(
                'recommendation',
                'recommendation__finding',
                'recommendation__finding__engagement',
            ).filter(
                notification_sent_at__isnull=False,
                auditee_responded_at__isnull=True,
                is_active=True,
            )

            # Optional: only overdue
            overdue_only = request.query_params.get('overdue_only', 'false').lower() == 'true'
            if overdue_only:
                queryset = queryset.filter(is_overdue=True)

            ordering = get_ordering_param(
                request, default='response_deadline',
                allowed_fields=['response_deadline', 'notification_sent_at', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = ImplementationMonitoringSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="non_responsive_monitoring",
            )
        except Exception as e:
            logger.exception("Failed to retrieve non-responsive monitoring records")
            return server_error_response(
                message="Failed to retrieve non-responsive records",
                details=str(e) if settings.DEBUG else None,
            )


# ─────────────────────────────────────────────────────────────────────────────
# P2-GAP 4: AuditeeFollowUpResponse views — one row per review cycle
# ─────────────────────────────────────────────────────────────────────────────

class AuditeeFollowUpResponseListCreateView(APIView):
    """
    GET  /follow-up-responses/?monitoring=<uuid>  — list cycles for a monitoring header
    GET  /implementation-monitoring/<uuid>/responses/  — nested alias (same view)
    POST /follow-up-responses/                    — create new cycle directly
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def get(self, request, monitoring_id=None):
        """List all follow-up response cycles for a monitoring record."""
        try:
            monitoring_pk = monitoring_id or request.query_params.get('monitoring')
            if not monitoring_pk:
                return error_response("?monitoring=<uuid> query parameter required.", code="MISSING_FILTER")

            monitoring = get_object_or_404(ImplementationMonitoring, pk=monitoring_pk)
            queryset = (
                AuditeeFollowUpResponse.objects
                .filter(monitoring=monitoring)
                .order_by('cycle_number')
            )

            page_data = paginate_queryset(queryset, request)
            serializer = AuditeeFollowUpResponseSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="follow_up_responses",
            )
        except Exception as e:
            logger.exception("Failed to list follow-up responses")
            return server_error_response(
                message="Failed to list follow-up responses",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, monitoring_id=None):
        """Create a new follow-up response cycle directly."""
        try:
            monitoring_pk = monitoring_id or request.data.get('monitoring_id')
            if not monitoring_pk:
                return error_response("monitoring_id required.", code="MISSING_FIELD")

            monitoring = get_object_or_404(ImplementationMonitoring, pk=monitoring_pk)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                last_cycle = monitoring.follow_up_responses.order_by('-cycle_number').first()
                next_cycle_number = (last_cycle.cycle_number + 1) if last_cycle else 1

                cycle = AuditeeFollowUpResponse.objects.create(
                    monitoring=monitoring,
                    cycle_number=next_cycle_number,
                    status='pending',
                    created_by=user_id,
                )

            return Response(
                {
                    "success": True,
                    "data": AuditeeFollowUpResponseSerializer(cycle).data,
                    "message": f"Follow-up response cycle {next_cycle_number} created.",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.exception("Failed to create follow-up response cycle")
            return server_error_response(
                message="Failed to create follow-up response cycle",
                details=str(e) if settings.DEBUG else None,
            )


class AuditeeFollowUpResponseDetailView(APIView):
    """
    GET   /follow-up-responses/<pk>/   — retrieve cycle detail
    PATCH /follow-up-responses/<pk>/   — partial update (auditor edits notes etc.)
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def get(self, request, pk):
        try:
            cycle = get_object_or_404(AuditeeFollowUpResponse, pk=pk)
            return success_response(data=AuditeeFollowUpResponseSerializer(cycle).data)
        except Exception as e:
            return server_error_response(message="Failed to retrieve follow-up response", details=str(e) if settings.DEBUG else None)

    def patch(self, request, pk):
        try:
            cycle = get_object_or_404(AuditeeFollowUpResponse, pk=pk)
            serializer = AuditeeFollowUpResponseSerializer(cycle, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(errors=serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)

            updated = serializer.save(modified_by=user_id)
            return success_response(data=AuditeeFollowUpResponseSerializer(updated).data, message="Follow-up response updated.")
        except Exception as e:
            return server_error_response(message="Failed to update follow-up response", details=str(e) if settings.DEBUG else None)


class AuditeeFollowUpResponseSubmitView(APIView):
    """POST /follow-up-responses/<pk>/submit/  — auditee submits progress + evidence"""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def post(self, request, pk):
        try:
            cycle = get_object_or_404(AuditeeFollowUpResponse, pk=pk)

            if cycle.status != 'pending':
                return Response(
                    {"success": False, "error": {
                        "message": f"Cannot submit a cycle that is already '{cycle.status}'.",
                        "code": "WRONG_STATUS",
                    }},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            implementation_progress = request.data.get('implementation_progress')
            if implementation_progress is None:
                return error_response("implementation_progress required.", code="MISSING_FIELD")

            try:
                progress = float(implementation_progress)
                if not (0 <= progress <= 100):
                    return error_response("progress must be 0–100.", code="INVALID_PROGRESS")
            except (ValueError, TypeError):
                return error_response("Invalid progress value.", code="INVALID_PROGRESS")

            progress_notes = request.data.get('progress_notes', '')
            evidence_documents = request.data.get('evidence_documents', [])

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)

            now = timezone.now()

            with transaction.atomic():
                cycle.submitted_by = user_id
                cycle.submitted_at = now
                cycle.implementation_progress = progress
                cycle.progress_notes = progress_notes
                cycle.evidence_documents = evidence_documents
                cycle.status = 'submitted'
                cycle.save(update_fields=[
                    'submitted_by', 'submitted_at', 'implementation_progress',
                    'progress_notes', 'evidence_documents', 'status',
                ])

                # Mirror auditee_responded_at to header
                cycle.monitoring.auditee_responded_at = now
                cycle.monitoring.save(update_fields=['auditee_responded_at'])

            return success_response(
                data=AuditeeFollowUpResponseSerializer(cycle).data,
                message="Response submitted successfully.",
            )
        except Exception as e:
            logger.exception("Failed to submit follow-up response %s", pk)
            return server_error_response(message="Failed to submit response", details=str(e) if settings.DEBUG else None)


class AuditeeFollowUpResponseVerifyView(APIView):
    """POST /follow-up-responses/<pk>/verify/  — auditor verifies (verdict: verified | rejected)"""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def post(self, request, pk):
        try:
            cycle = get_object_or_404(AuditeeFollowUpResponse, pk=pk)

            if cycle.status != 'submitted':
                return Response(
                    {"success": False, "error": {
                        "message": f"Cannot verify a cycle that has status '{cycle.status}'. Must be 'submitted'.",
                        "code": "WRONG_STATUS",
                    }},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            verdict = request.data.get('verdict')
            if verdict not in ('verified', 'rejected'):
                return error_response("verdict must be 'verified' or 'rejected'.", code="INVALID_VERDICT")

            verification_notes = request.data.get('verification_notes', '')

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response({"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}}, status=status.HTTP_401_UNAUTHORIZED)

            now = timezone.now()

            with transaction.atomic():
                cycle.verified_by = user_id
                cycle.verified_at = now
                cycle.verification_notes = verification_notes
                cycle.status = verdict
                cycle.save(update_fields=['verified_by', 'verified_at', 'verification_notes', 'status'])

                monitoring = cycle.monitoring
                monitoring.reviewed_by = user_id
                monitoring.last_review_date = now.date()

                if verdict == 'verified':
                    # Denormalize latest progress to header
                    monitoring.latest_progress = cycle.implementation_progress
                    # Close header if fully implemented
                    if cycle.implementation_progress >= 100:
                        monitoring.status = 'closed'
                    monitoring.save(update_fields=['reviewed_by', 'last_review_date', 'latest_progress', 'status'])
                else:
                    # rejected — caller should open a new cycle via /review/
                    monitoring.save(update_fields=['reviewed_by', 'last_review_date'])

            message_map = {
                'verified': "Response verified. Header latest_progress updated.",
                'rejected': "Response rejected. Open a new cycle via /review/ to continue.",
            }

            return success_response(
                data=AuditeeFollowUpResponseSerializer(cycle).data,
                message=message_map[verdict],
            )
        except Exception as e:
            logger.exception("Failed to verify follow-up response %s", pk)
            return server_error_response(message="Failed to verify response", details=str(e) if settings.DEBUG else None)


class AuditeeFollowUpResponseOverdueView(APIView):
    """GET /follow-up-responses/overdue/  — all cycles past deadline with no submission"""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanUpdateAuditMonitoring().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_monitoring:update required.')

    def get(self, request):
        try:
            now = timezone.now()
            queryset = (
                AuditeeFollowUpResponse.objects
                .select_related('monitoring', 'monitoring__recommendation')
                .filter(
                    status='pending',
                    response_deadline__lt=now,
                    is_active=True,
                )
                .order_by('response_deadline')
            )

            ordering = get_ordering_param(
                request,
                default='response_deadline',
                allowed_fields=['response_deadline', 'notified_at', 'created_at', 'cycle_number'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = AuditeeFollowUpResponseSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="overdue_follow_up_responses",
            )
        except Exception as e:
            logger.exception("Failed to retrieve overdue follow-up responses")
            return server_error_response(
                message="Failed to retrieve overdue follow-up responses",
                details=str(e) if settings.DEBUG else None,
            )
