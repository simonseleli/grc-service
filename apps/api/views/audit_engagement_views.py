"""
Audit Engagement CRUD Views for GRC Service
Provides full CRUD operations for audit engagement management following FIMS patterns
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditEngagement, AuditPlan, AuditableEntity, DeclarationOfIndependence
from apps.api.serializers.audit_serializers import AuditEngagementSerializer
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_ENGAGEMENT_EVENTS
from apps.api.permissions_jwt import CanManageAuditEngagement
from apps.core.services.audit_engagement_service import AuditEngagementService
from apps.infrastructure.external.orchestration_client import OrchestrationClient

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

logger = logging.getLogger(__name__)


class AuditEngagementListCreateView(APIView):
    """List all audit engagements or create a new one"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditEngagement().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_engagement:manage required.')

    def get(self, request):
        """Get all audit engagements with optional filtering and pagination"""
        try:
            # Get query parameters for filtering
            plan_id = request.query_params.get('audit_plan')
            entity_id = request.query_params.get('auditable_entity')
            engagement_type = request.query_params.get('engagement_type')
            status_filter = request.query_params.get('status')
            lead_auditor = request.query_params.get('lead_auditor')
            is_active = request.query_params.get('is_active')
            
            # Query engagements with related data
            queryset = AuditEngagement.objects.select_related(
                'audit_plan',
                'audit_plan__fiscal_year',
                'auditable_entity',
                'auditable_entity__audit_universe'
            ).all()
            
            # Apply filters
            if plan_id:
                queryset = queryset.filter(audit_plan_id=plan_id)
            if entity_id:
                queryset = queryset.filter(auditable_entity_id=entity_id)
            if engagement_type:
                queryset = queryset.filter(engagement_type=engagement_type)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if lead_auditor:
                queryset = queryset.filter(lead_auditor=lead_auditor)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-created_at',
                allowed_fields=['created_at', 'status', 'engagement_type', 'reference_number', 'planned_start_date']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditEngagementSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_engagement",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit engagements")
            return server_error_response(
                message="Failed to retrieve audit engagements",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create a new audit engagement"""
        try:
            serializer = AuditEngagementSerializer(data=request.data)
            
            if serializer.is_valid():
                plan_id = serializer.validated_data['audit_plan_id']
                entity_id = serializer.validated_data['auditable_entity_id']
                reference_number = serializer.validated_data.get('reference_number')
                
                # Verify audit plan exists and is approved
                plan = get_object_or_404(AuditPlan, id=plan_id)
                if plan.status not in ['approved', 'implementation']:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Cannot create engagement for unapproved audit plan",
                                "code": "PLAN_NOT_APPROVED"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verify auditable entity exists
                entity = get_object_or_404(AuditableEntity, id=entity_id)

                # Auto-generate reference number if blank/not provided
                if not reference_number:
                    fiscal_year = plan.fiscal_year
                    year_code = fiscal_year.year_code.replace('/', '')
                    existing_count = AuditEngagement.objects.filter(
                        audit_plan__fiscal_year=fiscal_year
                    ).count()
                    reference_number = f"ENG-{year_code}-{existing_count + 1:03d}"

                # Check for duplicate reference number
                if AuditEngagement.objects.filter(reference_number=reference_number).exists():
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Engagement with this reference number already exists",
                                "code": "DUPLICATE_REFERENCE"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # FIMS pattern: always require authenticated user — no system user fallback
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

                with transaction.atomic():
                    engagement = serializer.save(
                        created_by=user_id,
                        reference_number=reference_number,
                    )

                # Publish FIMS domain event — best-effort, never fails the request
                try:
                    messaging_service.publish_audit_engagement_event(
                        event_type=AUDIT_ENGAGEMENT_EVENTS['ENGAGEMENT_CREATED'],
                        engagement_id=engagement.id,
                        additional_data={
                            'title': engagement.title,
                            'engagement_type': engagement.engagement_type,
                            'auditable_entity_id': str(engagement.auditable_entity_id),
                            'created_by': str(user_id),
                            'user_id': str(user_id),
                        }
                    )
                except Exception as event_error:
                    logger.error(f"Error publishing engagement created event: {event_error}")

                return Response(
                    {
                        "success": True,
                        "data": AuditEngagementSerializer(engagement).data,
                        "message": "Audit engagement created successfully"
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
                        "message": "Failed to create audit engagement",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditEngagementDetailView(APIView):
    """Retrieve, update, or delete a specific audit engagement"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditEngagement().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_engagement:manage required.')

    def get(self, request, pk):
        """Get a specific audit engagement by ID"""
        try:
            engagement = get_object_or_404(
                AuditEngagement.objects.select_related(
                    'audit_plan',
                    'audit_plan__fiscal_year',
                    'auditable_entity',
                    'auditable_entity__audit_universe'
                ),
                pk=pk
            )
            
            serializer = AuditEngagementSerializer(engagement)
            
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "meta": {
                        "service": "grc-service",
                        "resource": "audit_engagement",
                        "version": "v1.0",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to retrieve audit engagement",
                        "details": str(e)
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Update an audit engagement (full update)"""
        try:
            engagement = get_object_or_404(AuditEngagement, pk=pk)
            
            # Prevent updates to completed engagements
            if engagement.status == 'completed':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update completed engagement",
                            "code": "ENGAGEMENT_COMPLETED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AuditEngagementSerializer(engagement, data=request.data)
            
            if serializer.is_valid():
                with transaction.atomic():
                    # Get user ID for modified_by tracking — require authenticated user
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    updated_engagement = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditEngagementSerializer(updated_engagement).data,
                        "message": "Audit engagement updated successfully"
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
                        "message": "Failed to update audit engagement",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Partially update an audit engagement"""
        try:
            engagement = get_object_or_404(AuditEngagement, pk=pk)
            
            # Prevent updates to completed engagements
            if engagement.status == 'completed':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update completed engagement",
                            "code": "ENGAGEMENT_COMPLETED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AuditEngagementSerializer(engagement, data=request.data, partial=True)
            
            if serializer.is_valid():
                with transaction.atomic():
                    # Get user ID for modified_by tracking — require authenticated user
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    updated_engagement = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditEngagementSerializer(updated_engagement).data,
                        "message": "Audit engagement updated successfully"
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
                        "message": "Failed to update audit engagement",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Soft delete an audit engagement"""
        try:
            engagement = get_object_or_404(AuditEngagement, pk=pk)
            
            # Prevent deletion of completed engagements
            if engagement.status == 'completed':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete completed engagement",
                            "code": "ENGAGEMENT_COMPLETED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if engagement has findings
            if hasattr(engagement, 'findings') and engagement.findings.filter(is_active=True).exists():
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete engagement with active findings",
                            "code": "HAS_ACTIVE_FINDINGS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                engagement.is_active = False
                engagement.save(update_fields=['is_active'])
            
            return Response(
                {
                    "success": True,
                    "message": "Audit engagement deleted successfully"
                },
                status=status.HTTP_200_OK
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete audit engagement",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditEngagementPhaseTransitionView(APIView):
    """Transition engagement through lifecycle phases"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditEngagement().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_engagement:manage required.')

    def post(self, request, pk):
        """Start the engagement lifecycle workflow via Work Orchestration Service.

        The first call (planning → fieldwork) starts the WO workflow plan.
        All subsequent phase transitions are managed by WO — GRC status is
        updated when WO fires stage-completion events (handled by kafka consumer).
        """
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            engagement = get_object_or_404(AuditEngagement, pk=pk)

            if engagement.status != 'planning':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": (
                                f"Cannot start engagement workflow from status '{engagement.status}'. "
                                "The workflow can only be started while the engagement is in 'planning' status. "
                                "Subsequent phase transitions are managed by Work Orchestration Service."
                            ),
                            "code": "WORKFLOW_MANAGED_BY_WO" if engagement.workflow_plan_id else "INVALID_STATUS",
                            "workflow_plan_id": str(engagement.workflow_plan_id) if engagement.workflow_plan_id else None,
                        },
                    },
                    status=status.HTTP_409_CONFLICT if engagement.workflow_plan_id else status.HTTP_400_BAD_REQUEST,
                )

            # SRS Requirement 16: All declarations of independence must be signed
            # before an engagement can transition from planning to fieldwork.
            declarations = DeclarationOfIndependence.objects.filter(
                audit_engagement=engagement,
            )
            if declarations.exists():
                unsigned = declarations.exclude(status='signed')
                if unsigned.exists():
                    unsigned_names = list(
                        unsigned.values_list('declarant_name', flat=True)[:5]
                    )
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": (
                                    "All team members must sign their Declaration of Independence "
                                    "before the engagement can proceed to fieldwork."
                                ),
                                "code": "DECLARATIONS_NOT_SIGNED",
                                "unsigned_members": unsigned_names,
                                "unsigned_count": unsigned.count(),
                            },
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Forward the user's JWT to WO so it can authenticate the plan creation request
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.removeprefix('Bearer ').strip() or None

            service = AuditEngagementService()
            engagement = service.start_workflow(
                engagement_id=str(pk),
                initiator_id=str(user_id),
                auth_token=auth_token,
            )

            # Publish FIMS domain event — best-effort
            # Note: publish_audit_engagement_event only handles ENGAGEMENT_CREATED/UPDATED;
            # ENGAGEMENT_STARTED has no event class yet — use ENGAGEMENT_UPDATED.
            try:
                messaging_service.publish_audit_engagement_event(
                    event_type=AUDIT_ENGAGEMENT_EVENTS.get('ENGAGEMENT_UPDATED'),
                    engagement_id=engagement.id,
                    additional_data={
                        'started_by': str(user_id),
                        'workflow_plan_id': str(engagement.workflow_plan_id) if engagement.workflow_plan_id else None,
                    },
                )
            except Exception as event_error:
                logger.error("Error publishing engagement started event for %s: %s", pk, event_error)

            return Response(
                {
                    "success": True,
                    "data": AuditEngagementSerializer(engagement).data,
                    "message": "Engagement lifecycle workflow started via Work Orchestration Service",
                    "workflow_plan_id": str(engagement.workflow_plan_id) if engagement.workflow_plan_id else None,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error("Error starting workflow for AuditEngagement %s: %s", pk, e, exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to start engagement lifecycle workflow",
                        "details": str(e),
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuditEngagementTeamView(APIView):
    """Manage audit team assignments"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditEngagement().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_engagement:manage required.')

    def patch(self, request, pk):
        """Update audit team members"""
        try:
            engagement = get_object_or_404(AuditEngagement, pk=pk)
            
            # Prevent team changes during reporting or after completion
            if engagement.status in ['reporting', 'completed']:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot modify team during {engagement.status} phase",
                            "code": "INVALID_PHASE_FOR_TEAM_CHANGE"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            audit_team = request.data.get('audit_team')
            lead_auditor = request.data.get('lead_auditor')
            
            with transaction.atomic():
                if audit_team is not None:
                    engagement.audit_team = audit_team
                if lead_auditor:
                    engagement.lead_auditor = lead_auditor
                
                engagement.save(update_fields=['audit_team', 'lead_auditor'])
            
            return Response(
                {
                    "success": True,
                    "data": AuditEngagementSerializer(engagement).data,
                    "message": "Audit team updated successfully"
                }
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update audit team",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditEngagementWorkflowStatusView(APIView):
    """
    GET /audit/engagements/<pk>/workflow-status/
        Return the current state of the workflow plan in Work Orchestration Service.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditEngagement().has_permission(request, self):
            self.permission_denied(
                request,
                message='grc:audit_engagement:manage required.',
            )

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        engagement = get_object_or_404(AuditEngagement, id=pk)

        if not engagement.workflow_plan_id:
            return Response(
                {
                    'success': True,
                    'data': {
                        'has_workflow': False,
                        'status': engagement.status,
                    },
                },
                status=status.HTTP_200_OK,
            )

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        auth_token = auth_header.removeprefix('Bearer ').strip() or None

        try:
            client = OrchestrationClient()
            plan = client.get_plan_status(plan_id=str(engagement.workflow_plan_id), auth_token=auth_token)
        except Exception as exc:
            logger.error('Error fetching workflow status for AuditEngagement %s: %s', pk, exc, exc_info=True)
            return Response(
                {'success': False, 'error': {'message': 'Failed to retrieve workflow status', 'details': str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'success': True,
                'data': {
                    'has_workflow': True,
                    'workflow_plan_id': str(engagement.workflow_plan_id),
                    'workflow_stage': engagement.workflow_stage,
                    'workflow_stage_id': str(engagement.workflow_stage_id) if engagement.workflow_stage_id else None,
                    'status': engagement.status,
                    'plan': plan,
                },
            },
            status=status.HTTP_200_OK,
        )


class AuditEngagementWorkflowHistoryView(APIView):
    """
    GET /audit/engagements/<pk>/workflow-history/
        Return the activity log of the workflow plan from Work Orchestration Service.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditEngagement().has_permission(request, self):
            self.permission_denied(
                request,
                message='grc:audit_engagement:manage required.',
            )

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        engagement = get_object_or_404(AuditEngagement, id=pk)

        if not engagement.workflow_plan_id:
            return Response(
                {
                    'success': True,
                    'data': {
                        'has_workflow': False,
                        'activity': [],
                    },
                },
                status=status.HTTP_200_OK,
            )

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        auth_token = auth_header.removeprefix('Bearer ').strip() or None

        try:
            client = OrchestrationClient()
            activity = client.get_plan_activity(plan_id=str(engagement.workflow_plan_id), auth_token=auth_token)
        except Exception as exc:
            logger.error('Error fetching workflow activity for AuditEngagement %s: %s', pk, exc, exc_info=True)
            return Response(
                {'success': False, 'error': {'message': 'Failed to retrieve workflow history', 'details': str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'success': True,
                'data': {
                    'has_workflow': True,
                    'workflow_plan_id': str(engagement.workflow_plan_id),
                    'activity': activity,
                },
            },
            status=status.HTTP_200_OK,
        )
