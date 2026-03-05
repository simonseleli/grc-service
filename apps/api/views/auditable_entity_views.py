"""
Auditable Entity CRUD Views for GRC Service
Provides full CRUD operations for auditable entity management following FIMS patterns
"""

import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditableEntity, AuditUniverse
from apps.api.serializers.audit_serializers import AuditableEntitySerializer
from apps.api.permissions_jwt import (
    CanViewAuditUniverse,
    CanManageAuditUniverse,
)

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    created_response,
    updated_response,
    deleted_response,
    error_response,
    not_found_response,
    validation_error_response,
    conflict_response,
    server_error_response,
)



class AuditableEntityListCreateView(APIView):
    """List all auditable entities or create a new one"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewAuditUniverse().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_universe:view required.')
        elif request.method == 'POST':
            if not CanManageAuditUniverse().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_universe:manage required.')

    def get(self, request):
        """Get all auditable entities with optional filtering and pagination"""
        try:
            # Get query parameters for filtering
            audit_universe_id = request.query_params.get('audit_universe')
            entity_type = request.query_params.get('entity_type')
            directorate_id = request.query_params.get('directorate')
            unit_id = request.query_params.get('unit')
            is_active = request.query_params.get('is_active')
            
            # Build query with related data
            queryset = AuditableEntity.objects.select_related(
                'audit_universe',
                'audit_universe__fiscal_year'
            ).all()
            
            # Apply filters
            if audit_universe_id:
                queryset = queryset.filter(audit_universe_id=audit_universe_id)
            if entity_type:
                queryset = queryset.filter(entity_type=entity_type)
            if directorate_id:
                queryset = queryset.filter(directorate_id=directorate_id)
            if unit_id:
                queryset = queryset.filter(unit_id=unit_id)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(request, default='name', allowed_fields=['name', 'entity_type', 'created_at'])
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditableEntitySerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="auditable_entity",
            )
        except Exception as e:
            logger.exception("Failed to retrieve auditable entities")
            return server_error_response(
                message="Failed to retrieve auditable entities",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create a new auditable entity"""
        try:
            serializer = AuditableEntitySerializer(data=request.data)
            
            if serializer.is_valid():
                audit_universe_id = serializer.validated_data['audit_universe_id']
                code = serializer.validated_data.get('code')
                
                # Verify audit universe exists and is in a modifiable state
                # SRS: IA populates universe with entities BEFORE submitting for CIA review.
                # Entities can be added while universe is draft or under_review.
                # Once approved/archived, no new entities should be added.
                audit_universe = get_object_or_404(AuditUniverse, id=audit_universe_id)
                if audit_universe.status in ('approved', 'archived'):
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Cannot add entity to an approved or archived audit universe",
                                "code": "UNIVERSE_NOT_MODIFIABLE"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check for duplicate code within the same universe
                if code and AuditableEntity.objects.filter(
                    audit_universe_id=audit_universe_id,
                    code=code
                ).exists():
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Entity with this code already exists in this universe",
                                "code": "DUPLICATE_ENTITY_CODE"
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
                    
                    entity = serializer.save(created_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditableEntitySerializer(entity).data,
                        "message": "Auditable entity created successfully"
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
                        "message": "Failed to create auditable entity",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditableEntityDetailView(APIView):
    """Retrieve, update, or delete a specific auditable entity"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewAuditUniverse().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_universe:view required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageAuditUniverse().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_universe:manage required.')

    def get(self, request, pk):
        """Get a specific auditable entity by ID"""
        try:
            entity = get_object_or_404(
                AuditableEntity.objects.select_related(
                    'audit_universe',
                    'audit_universe__fiscal_year'
                ),
                pk=pk
            )
            
            serializer = AuditableEntitySerializer(entity)
            
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "meta": {
                        "service": "grc-service",
                        "resource": "auditable_entity",
                        "version": "v1.0",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to retrieve auditable entity",
                        "details": str(e)
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Update an auditable entity (full update)"""
        try:
            entity = get_object_or_404(AuditableEntity, pk=pk)
            
            # Check if entity has active risk assessments
            if hasattr(entity, 'risk_assessments') and entity.risk_assessments.filter(is_active=True).exists():
                # Allow updates, but log a warning that assessments may need review
                pass
            
            serializer = AuditableEntitySerializer(entity, data=request.data)
            
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
                    
                    updated_entity = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditableEntitySerializer(updated_entity).data,
                        "message": "Auditable entity updated successfully"
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
                        "message": "Failed to update auditable entity",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Partially update an auditable entity"""
        try:
            entity = get_object_or_404(AuditableEntity, pk=pk)
            
            serializer = AuditableEntitySerializer(entity, data=request.data, partial=True)
            
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
                    
                    updated_entity = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditableEntitySerializer(updated_entity).data,
                        "message": "Auditable entity updated successfully"
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
                        "message": "Failed to update auditable entity",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Soft delete an auditable entity"""
        try:
            entity = get_object_or_404(AuditableEntity, pk=pk)
            
            # Check if entity has active audit engagements
            if hasattr(entity, 'engagements') and entity.engagements.filter(is_active=True).exists():
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete entity with active audit engagements",
                            "code": "HAS_ACTIVE_ENGAGEMENTS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active'])
            
            return Response(
                {
                    "success": True,
                    "message": "Auditable entity deleted successfully"
                },
                status=status.HTTP_200_OK
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete auditable entity",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
