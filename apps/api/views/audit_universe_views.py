"""
Audit Universe CRUD Views for GRC Service
Provides full CRUD operations for audit universe management following FIMS patterns
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

from apps.core.models import AuditUniverse, FiscalYear
from apps.api.serializers.audit_serializers import AuditUniverseSerializer
from apps.api.permissions_jwt import (
    CanViewAuditUniverse,
    CanManageAuditUniverse,
    CanApproveAuditUniverse,
)
from apps.core.services.audit_universe_service import AuditUniverseService

# FIMS standard utilities (Phase 2)
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



class AuditUniverseListCreateView(APIView):
    """List all audit universes or create a new one"""

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
        """Get all audit universes with optional filtering and pagination"""
        try:
            # Get query parameters for filtering
            fiscal_year_id = request.query_params.get('fiscal_year')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')
            
            # Build query
            queryset = AuditUniverse.objects.select_related('fiscal_year').all()
            
            if fiscal_year_id:
                queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
            # Apply ordering (FIMS standard: support ordering query param)
            ordering = get_ordering_param(
                request,
                default='-fiscal_year__start_date',
                allowed_fields=['fiscal_year__start_date', 'created_at', 'status', 'name']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            # Serialize only the current page
            serializer = AuditUniverseSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_universe",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit universes")
            return server_error_response(
                message="Failed to retrieve audit universes",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create a new audit universe"""
        try:
            serializer = AuditUniverseSerializer(data=request.data)
            
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)
            
            fiscal_year_id = serializer.validated_data['fiscal_year_id']
            
            # Check if an active universe already exists for this fiscal year
            existing = AuditUniverse.objects.filter(
                fiscal_year_id=fiscal_year_id,
                is_active=True,
            ).exists()
            
            if existing:
                return conflict_response(
                    message="Audit universe already exists for this fiscal year",
                    code="UNIVERSE_ALREADY_EXISTS",
                )
            
            # Verify fiscal year exists
            fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)
            
            with transaction.atomic():
                # FIMS pattern: always require authenticated user
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return error_response(
                        message="User not authenticated",
                        code="AUTH_REQUIRED",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                    )
                
                audit_universe = serializer.save(created_by=user_id)
            
            return created_response(
                data=AuditUniverseSerializer(audit_universe).data,
                message="Audit universe created successfully",
            )
                
        except Exception as e:
            logger.exception("Failed to create audit universe")
            return server_error_response(
                message="Failed to create audit universe",
                details=str(e) if settings.DEBUG else None,
            )


class AuditUniverseDetailView(APIView):
    """Retrieve, update, or delete a specific audit universe"""

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
        """Get a specific audit universe by ID"""
        try:
            audit_universe = get_object_or_404(
                AuditUniverse.objects.select_related('fiscal_year'),
                pk=pk
            )
            serializer = AuditUniverseSerializer(audit_universe)
            
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "meta": {
                        "service": "grc-service",
                        "resource": "audit_universe",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Audit universe not found",
                        "details": str(e)
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Update a specific audit universe"""
        try:
            audit_universe = get_object_or_404(AuditUniverse, pk=pk)
            
            # Don't allow updating approved universes
            if audit_universe.status == 'approved':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update approved audit universe",
                            "code": "UNIVERSE_APPROVED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AuditUniverseSerializer(audit_universe, data=request.data, partial=False)
            
            if serializer.is_valid():
                with transaction.atomic():
                    updated_universe = serializer.save()
                
                return Response(
                    {
                        "success": True,
                        "data": AuditUniverseSerializer(updated_universe).data,
                        "message": "Audit universe updated successfully"
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
                        "message": "Failed to update audit universe",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Partially update a specific audit universe"""
        try:
            audit_universe = get_object_or_404(AuditUniverse, pk=pk)
            
            serializer = AuditUniverseSerializer(audit_universe, data=request.data, partial=True)
            
            if serializer.is_valid():
                with transaction.atomic():
                    updated_universe = serializer.save()
                
                return Response(
                    {
                        "success": True,
                        "data": AuditUniverseSerializer(updated_universe).data,
                        "message": "Audit universe updated successfully"
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
                        "message": "Failed to update audit universe",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Delete (soft delete) a specific audit universe"""
        try:
            audit_universe = get_object_or_404(AuditUniverse, pk=pk)
            
            # Don't allow deleting approved universes with active plans
            if audit_universe.status == 'approved' and audit_universe.audit_plans.filter(is_active=True).exists():
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete audit universe with active plans",
                            "code": "HAS_ACTIVE_PLANS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Soft delete by marking as inactive
                audit_universe.is_active = False
                audit_universe.save()
            
            return Response(
                {
                    "success": True,
                    "message": "Audit universe deleted successfully"
                },
                status=status.HTTP_200_OK
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete audit universe",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditUniverseApprovalView(APIView):
    """Handle audit universe approval workflow"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditUniverse().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_universe:manage required.')

    def post(self, request, pk):
        """Submit audit universe for approval via Work Orchestration Service."""
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            audit_universe = get_object_or_404(AuditUniverse, pk=pk)

            if audit_universe.status not in ('draft', 'under_review'):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot submit audit universe with status '{audit_universe.status}'",
                            "code": "INVALID_STATUS",
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if audit_universe.workflow_plan_id:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Audit universe workflow already in progress",
                            "code": "WORKFLOW_ALREADY_STARTED",
                            "workflow_plan_id": str(audit_universe.workflow_plan_id),
                        },
                    },
                    status=status.HTTP_409_CONFLICT,
                )


            service = AuditUniverseService()
            audit_universe = service.submit_for_approval(
                universe_id=str(pk),
                submitter_id=str(user_id),
            )

            return Response(
                {
                    "success": True,
                    "data": AuditUniverseSerializer(audit_universe).data,
                    "message": "Audit universe submitted for approval via workflow",
                    "workflow_plan_id": str(audit_universe.workflow_plan_id) if audit_universe.workflow_plan_id else None,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error("Error submitting AuditUniverse %s for approval: %s", pk, e, exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to submit audit universe for approval",
                        "details": str(e),
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuditUniverseWorkflowStatusView(APIView):
    """
    GET /audit/universe/<pk>/workflow-status/
        Return the current state of the workflow plan in Work Orchestration Service.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewAuditUniverse().has_permission(request, self) or
                CanManageAuditUniverse().has_permission(request, self)):
            self.permission_denied(
                request,
                message='grc:audit_universe:view or :manage required.',
            )

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        universe = get_object_or_404(AuditUniverse, id=pk)

        if not universe.workflow_plan_id:
            return Response(
                {
                    'success': True,
                    'data': {
                        'has_workflow': False,
                        'status': universe.status,
                    },
                },
                status=status.HTTP_200_OK,
            )


        try:
            workflow_data = AuditUniverseService().get_workflow_status(str(pk))
        except Exception as exc:
            logger.error('Error fetching workflow status for AuditUniverse %s: %s', pk, exc, exc_info=True)
            return Response(
                {'success': False, 'error': {'message': 'Failed to retrieve workflow status', 'details': str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'success': True, 'data': workflow_data}, status=status.HTTP_200_OK)


class AuditUniverseWorkflowHistoryView(APIView):
    """
    GET /audit/universe/<pk>/workflow-history/
        Return the activity log of the workflow plan from Work Orchestration Service.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewAuditUniverse().has_permission(request, self) or
                CanManageAuditUniverse().has_permission(request, self)):
            self.permission_denied(
                request,
                message='grc:audit_universe:view or :manage required.',
            )

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        universe = get_object_or_404(AuditUniverse, id=pk)

        if not universe.workflow_plan_id:
            return Response(
                {
                    'success': True,
                    'data': {
                        'has_workflow': False,
                        'activities': [],
                    },
                },
                status=status.HTTP_200_OK,
            )


        try:
            activity = AuditUniverseService().get_workflow_history(str(pk))
        except Exception as exc:
            logger.error('Error fetching workflow activity for AuditUniverse %s: %s', pk, exc, exc_info=True)
            return Response(
                {'success': False, 'error': {'message': 'Failed to retrieve workflow history', 'details': str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'success': True,
                'data': {
                    'has_workflow': True,
                    'workflow_plan_id': str(universe.workflow_plan_id),
                    'activities': activity,
                },
            },
            status=status.HTTP_200_OK,
        )


class AuditUniverseWorkflowActionView(APIView):
    """
    POST /audit/universe/<pk>/workflow-action/
        Execute a workflow action (approve, reject, return, etc.).
        Matches corporate-service workflow_action endpoint pattern.

    Request body:
    {
        "action": "approve",  // Required
        "comment": "..."      // Optional
    }
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanApproveAuditUniverse().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_universe:approve required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        action_name = request.data.get('action')
        if not action_name:
            return Response(
                {'success': False, 'error': {'message': "'action' is required", 'code': 'ACTION_REQUIRED'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = AuditUniverseService().advance_workflow_stage(
                universe_id=str(pk),
                action=action_name,
                actor_id=str(user_id),
                comment=request.data.get('comment', ''),
            )
        except ValueError as exc:
            return Response(
                {'success': False, 'error': {'message': str(exc), 'code': 'WORKFLOW_ACTION_FAILED'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error('Error executing workflow action for AuditUniverse %s: %s', pk, exc, exc_info=True)
            return Response(
                {'success': False, 'error': {'message': 'Failed to execute workflow action', 'details': str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'success': True, 'data': result}, status=status.HTTP_200_OK)


class AuditUniverseCancelWorkflowView(APIView):
    """
    POST /audit/universe/<pk>/cancel-workflow/
        Cancel the active workflow for an audit universe.
        Matches corporate-service cancel_workflow endpoint pattern.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditUniverse().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_universe:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            AuditUniverseService().cancel_workflow_plan(
                universe_id=str(pk),
                actor_id=str(user_id),
                reason=request.data.get('reason', ''),
            )
        except ValueError as exc:
            return Response(
                {'success': False, 'error': {'message': str(exc), 'code': 'CANCEL_WORKFLOW_FAILED'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error('Error cancelling workflow for AuditUniverse %s: %s', pk, exc, exc_info=True)
            return Response(
                {'success': False, 'error': {'message': 'Failed to cancel workflow', 'details': str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {'success': True, 'data': {'status': 'workflow_cancelled'}},
            status=status.HTTP_200_OK,
        )
