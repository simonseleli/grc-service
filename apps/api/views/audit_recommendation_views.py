"""
Audit Recommendation CRUD Views for GRC Service
Provides full CRUD operations for audit recommendation management following FIMS patterns
"""

import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import (
    AuditRecommendation, AuditFinding
)
from apps.api.serializers.audit_serializers import AuditRecommendationSerializer
from apps.api.permissions_jwt import CanManageAuditFinding

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    created_response,
    error_response,
    not_found_response,
    validation_error_response,
    server_error_response,
)



class AuditRecommendationListCreateView(APIView):
    """List all audit recommendations or create a new one"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditFinding().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_finding:manage required.')

    def get(self, request):
        """Get all audit recommendations with optional filtering and pagination"""
        try:
            # Get query parameters for filtering
            finding_id = request.query_params.get('finding')
            priority = request.query_params.get('priority')
            status_filter = request.query_params.get('status')
            responsible_party = request.query_params.get('responsible_party')
            is_active = request.query_params.get('is_active')
            overdue = request.query_params.get('overdue')  # true/false
            
            # Build query with related data
            queryset = AuditRecommendation.objects.select_related(
                'finding',
                'finding__engagement',
                'finding__severity',
                'finding__finding_type'
            ).all()
            
            # Apply filters
            if finding_id:
                queryset = queryset.filter(finding_id=finding_id)
            if priority:
                queryset = queryset.filter(priority=priority)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if responsible_party:
                queryset = queryset.filter(responsible_party=responsible_party)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            if overdue and overdue.lower() == 'true':
                # Filter for open/in_progress recommendations past target_date
                today = timezone.now().date()
                queryset = queryset.filter(
                    target_date__lt=today,
                    status__in=['open', 'in_progress']
                )
            
            # Apply ordering using database-level Case/When (FIMS standard: avoid Python sorting)
            # Default: priority (high=1, medium=2, low=3), then by target_date
            queryset = queryset.annotate(
                priority_order=Case(
                    When(priority='high', then=Value(1)),
                    When(priority='medium', then=Value(2)),
                    When(priority='low', then=Value(3)),
                    default=Value(4),
                    output_field=IntegerField(),
                )
            ).order_by('priority_order', 'target_date')
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditRecommendationSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_recommendation",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit recommendations")
            return server_error_response(
                message="Failed to retrieve audit recommendations",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create a new audit recommendation"""
        try:
            serializer = AuditRecommendationSerializer(data=request.data)
            
            if serializer.is_valid():
                finding_id = serializer.validated_data['finding_id']
                reference_number = serializer.validated_data.get('reference_number')
                
                # Verify finding exists and is final
                finding = get_object_or_404(AuditFinding, id=finding_id)
                if finding.status != 'final':
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": f"Cannot create recommendation for finding in '{finding.status}' status. Finding must be final.",
                                "code": "FINDING_NOT_FINAL"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check for duplicate reference number within finding
                if reference_number and AuditRecommendation.objects.filter(
                    finding_id=finding_id,
                    reference_number=reference_number
                ).exists():
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Recommendation with this reference number already exists for this finding",
                                "code": "DUPLICATE_REFERENCE"
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
                    
                    # Auto-generate reference_number if not provided
                    if not reference_number:
                        finding_ref = finding.reference_number or str(finding_id)[:8]
                        existing_count = AuditRecommendation.objects.filter(finding_id=finding_id).count()
                        reference_number = f"REC-{finding_ref}-{existing_count + 1:03d}"
                    
                    recommendation = serializer.save(created_by=user_id, reference_number=reference_number)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditRecommendationSerializer(recommendation).data,
                        "message": "Audit recommendation created successfully"
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
                        "message": "Failed to create audit recommendation",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditRecommendationDetailView(APIView):
    """Retrieve, update, or delete a specific audit recommendation"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditFinding().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_finding:manage required.')

    def get(self, request, pk):
        """Get a specific audit recommendation by ID"""
        try:
            recommendation = get_object_or_404(
                AuditRecommendation.objects.select_related(
                    'finding',
                    'finding__engagement',
                    'finding__severity',
                    'finding__finding_type'
                ),
                pk=pk
            )
            
            serializer = AuditRecommendationSerializer(recommendation)
            
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "meta": {
                        "service": "grc-service",
                        "resource": "audit_recommendation",
                        "version": "v1.0",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to retrieve audit recommendation",
                        "details": str(e)
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Update an audit recommendation (full update)"""
        try:
            recommendation = get_object_or_404(AuditRecommendation, pk=pk)
            
            # Prevent updates to verified or closed recommendations
            if recommendation.status in ['verified', 'closed']:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot update {recommendation.status} recommendation",
                            "code": "RECOMMENDATION_LOCKED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AuditRecommendationSerializer(recommendation, data=request.data)
            
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
                    
                    updated_recommendation = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditRecommendationSerializer(updated_recommendation).data,
                        "message": "Audit recommendation updated successfully"
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
                        "message": "Failed to update audit recommendation",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Partially update an audit recommendation"""
        try:
            recommendation = get_object_or_404(AuditRecommendation, pk=pk)
            
            # Prevent updates to verified or closed recommendations
            if recommendation.status in ['verified', 'closed']:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot update {recommendation.status} recommendation",
                            "code": "RECOMMENDATION_LOCKED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AuditRecommendationSerializer(recommendation, data=request.data, partial=True)
            
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
                    
                    updated_recommendation = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditRecommendationSerializer(updated_recommendation).data,
                        "message": "Audit recommendation updated successfully"
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
                        "message": "Failed to update audit recommendation",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Soft delete an audit recommendation"""
        try:
            recommendation = get_object_or_404(AuditRecommendation, pk=pk)
            
            # Prevent deletion of verified or closed recommendations
            if recommendation.status in ['verified', 'closed']:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot delete {recommendation.status} recommendation",
                            "code": "RECOMMENDATION_LOCKED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if recommendation has monitoring records
            if hasattr(recommendation, 'monitoring') and recommendation.monitoring:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete recommendation with monitoring records",
                            "code": "HAS_MONITORING_RECORDS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                recommendation.is_active = False
                recommendation.save(update_fields=['is_active'])
            
            return Response(
                {
                    "success": True,
                    "message": "Audit recommendation deleted successfully"
                },
                status=status.HTTP_200_OK
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete audit recommendation",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditRecommendationStatusUpdateView(APIView):
    """Update recommendation implementation status"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditFinding().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_finding:manage required.')

    def post(self, request, pk):
        """Update recommendation status through workflow"""
        try:
            recommendation = get_object_or_404(AuditRecommendation, pk=pk)
            
            target_status = request.data.get('target_status')
            
            # Valid status transitions
            valid_transitions = {
                'open': ['in_progress'],
                'in_progress': ['implemented', 'open'],  # Can revert to open
                'implemented': ['verified', 'in_progress'],  # Can revert or move forward
                'verified': ['closed', 'in_progress'],  # Can revert or close
                'closed': [],  # Cannot transition from closed
            }
            
            if target_status not in valid_transitions.get(recommendation.status, []):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot transition from '{recommendation.status}' to '{target_status}'",
                            "code": "INVALID_STATUS_TRANSITION",
                            "current_status": recommendation.status,
                            "allowed_transitions": valid_transitions.get(recommendation.status, [])
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Additional validations for specific statuses
            if target_status == 'implemented':
                implementation_notes = request.data.get('implementation_notes')
                if not implementation_notes:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Implementation notes required when marking as implemented",
                                "code": "MISSING_IMPLEMENTATION_NOTES"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if target_status == 'verified':
                verification_evidence = request.data.get('verification_evidence')
                if not verification_evidence:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Verification evidence required when marking as verified",
                                "code": "MISSING_VERIFICATION_EVIDENCE"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            with transaction.atomic():
                recommendation.status = target_status
                recommendation.save(update_fields=['status'])
            
            return Response(
                {
                    "success": True,
                    "data": AuditRecommendationSerializer(recommendation).data,
                    "message": f"Recommendation transitioned to {target_status} successfully"
                }
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update recommendation status",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditRecommendationOverdueView(APIView):
    """Get overdue recommendations requiring attention"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditFinding().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_finding:manage required.')

    def get(self, request):
        """Get all overdue recommendations with pagination"""
        try:
            today = timezone.now().date()
            
            # Get recommendations past target date and still open/in_progress
            queryset = AuditRecommendation.objects.select_related(
                'finding',
                'finding__engagement',
                'finding__severity'
            ).filter(
                target_date__lt=today,
                status__in=['open', 'in_progress'],
                is_active=True
            ).order_by('target_date')
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditRecommendationSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_recommendation_overdue",
                as_of_date=today.isoformat(),
            )
        except Exception as e:
            logger.exception("Failed to retrieve overdue recommendations")
            return server_error_response(
                message="Failed to retrieve overdue recommendations",
                details=str(e) if settings.DEBUG else None,
            )
