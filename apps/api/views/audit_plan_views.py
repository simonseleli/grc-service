"""
Audit Plan CRUD Views for GRC Service
Provides full CRUD operations for audit plan management following FIMS patterns
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditPlan, AuditUniverse, FiscalYear, RiskAssessment
from apps.api.serializers.audit_serializers import AuditPlanSerializer
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_PLAN_EVENTS
from apps.api.permissions_jwt import (
    CanViewAuditPlan,
    CanManageAuditPlan,
    CanApproveAuditPlan,
)
from apps.core.services.audit_plan_service import AuditPlanService
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


class AuditPlanListCreateView(APIView):
    """List all audit plans or create a new one"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_plan:view required.')
        elif request.method == 'POST':
            if not CanManageAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_plan:manage required.')

    def get(self, request):
        """Get all audit plans with optional filtering and pagination"""
        try:
            # Get query parameters for filtering
            fiscal_year_id = request.query_params.get('fiscal_year')
            audit_universe_id = request.query_params.get('audit_universe')
            plan_type = request.query_params.get('plan_type')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')
            
            # Build query with related data
            queryset = AuditPlan.objects.select_related(
                'audit_universe',
                'audit_universe__fiscal_year',
                'fiscal_year'
            ).all()
            
            # Apply filters
            if fiscal_year_id:
                queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
            if audit_universe_id:
                queryset = queryset.filter(audit_universe_id=audit_universe_id)
            if plan_type:
                queryset = queryset.filter(plan_type=plan_type)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-fiscal_year__start_date',
                allowed_fields=['fiscal_year__start_date', 'created_at', 'status', 'plan_type', 'reference_number']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditPlanSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_plan",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit plans")
            return server_error_response(
                message="Failed to retrieve audit plans",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create a new audit plan"""
        try:
            serializer = AuditPlanSerializer(data=request.data)
            
            if serializer.is_valid():
                audit_universe_id = serializer.validated_data['audit_universe_id']
                fiscal_year_id = serializer.validated_data['fiscal_year_id']
                reference_number = serializer.validated_data.get('reference_number')
                
                # Verify audit universe exists and is approved
                audit_universe = get_object_or_404(AuditUniverse, id=audit_universe_id)
                if audit_universe.status != 'approved':
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Cannot create plan for unapproved audit universe",
                                "code": "UNIVERSE_NOT_APPROVED"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verify fiscal year exists
                fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)
                
                # Check for duplicate reference number
                if reference_number and AuditPlan.objects.filter(
                    reference_number=reference_number
                ).exists():
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Audit plan with this reference number already exists",
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
                    # Set prepared_by if not provided
                    prepared_by = serializer.validated_data.get('prepared_by', user_id)
                    
                    audit_plan = serializer.save(created_by=user_id, prepared_by=prepared_by)

                # Publish FIMS domain event — best-effort, never fails the request
                try:
                    fiscal_year = getattr(audit_plan, 'fiscal_year', None)
                    fiscal_year_code = str(fiscal_year.year_code) if fiscal_year else ''
                    messaging_service.publish_audit_plan_event(
                        event_type=AUDIT_PLAN_EVENTS['PLAN_CREATED'],
                        plan_id=audit_plan.id,
                        additional_data={
                            'fiscal_year': fiscal_year_code,
                            'plan_type': audit_plan.plan_type,
                            'created_by': str(user_id),
                            'user_id': str(user_id),
                        }
                    )
                except Exception as event_error:
                    logger.error(f"Error publishing plan created event: {event_error}")

                return Response(
                    {
                        "success": True,
                        "data": AuditPlanSerializer(audit_plan).data,
                        "message": "Audit plan created successfully"
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
                        "message": "Failed to create audit plan",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditPlanDetailView(APIView):
    """Retrieve, update, or delete a specific audit plan"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_plan:view required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_plan:manage required.')

    def get(self, request, pk):
        """Get a specific audit plan by ID"""
        try:
            audit_plan = get_object_or_404(
                AuditPlan.objects.select_related(
                    'audit_universe',
                    'audit_universe__fiscal_year',
                    'fiscal_year'
                ),
                pk=pk
            )
            serializer = AuditPlanSerializer(audit_plan)
            
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "meta": {
                        "service": "grc-service",
                        "resource": "audit_plan",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Audit plan not found",
                        "details": str(e)
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Update a specific audit plan (full update)"""
        try:
            audit_plan = get_object_or_404(AuditPlan, pk=pk)
            
            # Don't allow updating approved plans that are under implementation
            if audit_plan.status == 'implementation':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update audit plan under implementation",
                            "code": "PLAN_IN_IMPLEMENTATION"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AuditPlanSerializer(audit_plan, data=request.data, partial=False)
            
            if serializer.is_valid():
                with transaction.atomic():
                    # Get user ID for modified_by — require authenticated user
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    audit_plan.modified_by = user_id
                    updated_plan = serializer.save()
                
                return Response(
                    {
                        "success": True,
                        "data": AuditPlanSerializer(updated_plan).data,
                        "message": "Audit plan updated successfully"
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
                        "message": "Failed to update audit plan",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Partially update a specific audit plan"""
        try:
            audit_plan = get_object_or_404(AuditPlan, pk=pk)
            
            serializer = AuditPlanSerializer(audit_plan, data=request.data, partial=True)
            
            if serializer.is_valid():
                with transaction.atomic():
                    # Get user ID for modified_by — require authenticated user
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    audit_plan.modified_by = user_id
                    updated_plan = serializer.save()
                
                return Response(
                    {
                        "success": True,
                        "data": AuditPlanSerializer(updated_plan).data,
                        "message": "Audit plan updated successfully"
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
                        "message": "Failed to update audit plan",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Delete (soft delete) a specific audit plan"""
        try:
            audit_plan = get_object_or_404(AuditPlan, pk=pk)
            
            # Don't allow deleting plans under implementation with active engagements
            if audit_plan.status == 'implementation':
                active_engagements = audit_plan.audit_engagements.filter(is_active=True).count()
                if active_engagements > 0:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": f"Cannot delete audit plan with {active_engagements} active engagement(s)",
                                "code": "HAS_ACTIVE_ENGAGEMENTS"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            with transaction.atomic():
                # Soft delete by marking as inactive
                audit_plan.is_active = False
                audit_plan.save()
            
            return Response(
                {
                    "success": True,
                    "message": "Audit plan deleted successfully"
                },
                status=status.HTTP_200_OK
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete audit plan",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditPlanSubmitView(APIView):
    """Submit audit plan for review workflow"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_plan:manage required.')

    def post(self, request, pk):
        """Submit audit plan for RBIAP approval via Work Orchestration Service."""
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            audit_plan = get_object_or_404(AuditPlan, pk=pk)

            if audit_plan.status != 'draft':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Only draft plans can be submitted. Current status: '{audit_plan.status}'",
                            "code": "INVALID_STATUS",
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if audit_plan.workflow_plan_id:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "RBIAP approval workflow already in progress",
                            "code": "WORKFLOW_ALREADY_STARTED",
                            "workflow_plan_id": str(audit_plan.workflow_plan_id),
                        },
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Forward the user's JWT to WO so it can authenticate the plan creation request
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.removeprefix('Bearer ').strip() or None

            service = AuditPlanService()
            audit_plan = service.submit_for_approval(
                plan_id=str(pk),
                submitter_id=str(user_id),
                auth_token=auth_token,
            )

            # Publish FIMS domain event — best-effort
            # Note: PLAN_SUBMITTED does not exist in AUDIT_PLAN_EVENTS; use PLAN_UPDATED
            # to signal that the plan's status has changed to management_review.
            try:
                messaging_service.publish_audit_plan_event(
                    event_type=AUDIT_PLAN_EVENTS.get('PLAN_UPDATED'),
                    plan_id=audit_plan.id,
                    additional_data={
                        'submitted_by': str(user_id),
                        'workflow_plan_id': str(audit_plan.workflow_plan_id) if audit_plan.workflow_plan_id else None,
                    },
                )
            except Exception as event_error:
                logger.error("Error publishing plan submitted event for plan %s: %s", pk, event_error)

            return Response(
                {
                    "success": True,
                    "data": AuditPlanSerializer(audit_plan).data,
                    "message": "Audit plan submitted for RBIAP approval via workflow",
                    "workflow_plan_id": str(audit_plan.workflow_plan_id) if audit_plan.workflow_plan_id else None,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error("Error submitting AuditPlan %s for approval: %s", pk, e, exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to submit audit plan for approval",
                        "details": str(e),
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuditPlanApprovalView(APIView):
    """
    DEPRECATED — approval stages (CIA review, management adoption, committee approval,
    commission noting) are now managed by Work Orchestration Service.

    The approval workflow is started via POST /plans/<pk>/submit/ and all subsequent
    stage transitions are driven by WO. GRC status is updated when WO fires a
    workflow completion event consumed by the kafka consumer.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanApproveAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_plan:approve required.')

    def post(self, request, pk):
        """Approval is now handled by Work Orchestration Service."""
        return Response(
            {
                "success": False,
                "error": {
                    "message": (
                        "Direct approval is no longer supported. "
                        "The RBIAP approval workflow is managed by Work Orchestration Service. "
                        "Submit the plan via POST /plans/<pk>/submit/ to start the workflow."
                    ),
                    "code": "WORKFLOW_MANAGED_BY_WO",
                },
            },
            status=status.HTTP_410_GONE,
        )


class AuditPlanWorkflowStatusView(APIView):
    """
    GET /audit/plans/<pk>/workflow-status/
        Return the current state of the workflow plan in Work Orchestration Service.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewAuditPlan().has_permission(request, self) or
                CanManageAuditPlan().has_permission(request, self)):
            self.permission_denied(
                request,
                message='grc:audit_plan:view or :manage required.',
            )

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        plan = get_object_or_404(AuditPlan, id=pk)

        if not plan.workflow_plan_id:
            return Response(
                {
                    'success': True,
                    'data': {
                        'has_workflow': False,
                        'status': plan.status,
                    },
                },
                status=status.HTTP_200_OK,
            )

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        auth_token = auth_header.removeprefix('Bearer ').strip() or None

        try:
            client = OrchestrationClient()
            plan_status = client.get_plan_status(plan_id=str(plan.workflow_plan_id), auth_token=auth_token)
        except Exception as exc:
            logger.error('Error fetching workflow status for AuditPlan %s: %s', pk, exc, exc_info=True)
            return Response(
                {'success': False, 'error': {'message': 'Failed to retrieve workflow status', 'details': str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'success': True,
                'data': {
                    'has_workflow': True,
                    'workflow_plan_id': str(plan.workflow_plan_id),
                    'workflow_stage': plan.workflow_stage,
                    'workflow_stage_id': str(plan.workflow_stage_id) if plan.workflow_stage_id else None,
                    'status': plan.status,
                    'plan': plan_status,
                },
            },
            status=status.HTTP_200_OK,
        )


class AuditPlanWorkflowHistoryView(APIView):
    """
    GET /audit/plans/<pk>/workflow-history/
        Return the activity log of the workflow plan from Work Orchestration Service.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewAuditPlan().has_permission(request, self) or
                CanManageAuditPlan().has_permission(request, self)):
            self.permission_denied(
                request,
                message='grc:audit_plan:view or :manage required.',
            )

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        plan = get_object_or_404(AuditPlan, id=pk)

        if not plan.workflow_plan_id:
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
            activity = client.get_plan_activity(plan_id=str(plan.workflow_plan_id), auth_token=auth_token)
        except Exception as exc:
            logger.error('Error fetching workflow activity for AuditPlan %s: %s', pk, exc, exc_info=True)
            return Response(
                {'success': False, 'error': {'message': 'Failed to retrieve workflow history', 'details': str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'success': True,
                'data': {
                    'has_workflow': True,
                    'workflow_plan_id': str(plan.workflow_plan_id),
                    'activity': activity,
                },
            },
            status=status.HTTP_200_OK,
        )


class AuditPlanGenerateDraftView(APIView):
    """Auto-generate a prioritized draft RBIAP from approved risk assessments (GAP 11).

    POST /audit/plans/generate-draft/
    Body: { "fiscal_year_id": "...", "audit_universe_id": "..." }

    Queries all approved risk assessments for entities in the given universe,
    sorts by weighted risk score descending, and creates a draft plan with
    priority_areas auto-populated from the highest-risk entities.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_plan:manage required.')

    def post(self, request):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated",
                code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        fiscal_year_id = request.data.get('fiscal_year_id')
        universe_id = request.data.get('audit_universe_id')

        if not fiscal_year_id or not universe_id:
            return validation_error_response({
                'fiscal_year_id': ['This field is required.'] if not fiscal_year_id else [],
                'audit_universe_id': ['This field is required.'] if not universe_id else [],
            })

        try:
            fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)
            universe = get_object_or_404(AuditUniverse, id=universe_id)

            if universe.status != 'approved':
                return error_response(
                    message="Audit Universe must be approved before generating a plan",
                    code="UNIVERSE_NOT_APPROVED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Check if a plan already exists for this universe + fiscal year
            existing = AuditPlan.objects.filter(
                audit_universe=universe,
                fiscal_year=fiscal_year,
            ).first()
            if existing:
                return conflict_response(
                    message=f"A plan already exists for this universe and fiscal year: {existing.reference_number}",
                    code="PLAN_EXISTS",
                )

            # Query all approved risk assessments for entities in this universe
            assessments = RiskAssessment.objects.filter(
                auditable_entity__audit_universe=universe,
                status='approved',
                is_active=True,
            ).select_related(
                'auditable_entity', 'overall_risk_rating',
            ).order_by(
                # Sort by calculated_weighted_score desc (highest risk first);
                # fallback to overall_risk_rating numerical_value desc
                '-calculated_weighted_score',
                '-overall_risk_rating__numerical_value',
            )

            if not assessments.exists():
                return error_response(
                    message="No approved risk assessments found for entities in this universe",
                    code="NO_ASSESSMENTS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Deduplicate: keep only the highest-scoring assessment per entity
            seen_entities = set()
            deduped_assessments = []
            for assessment in assessments:
                eid = assessment.auditable_entity_id
                if eid not in seen_entities:
                    seen_entities.add(eid)
                    deduped_assessments.append(assessment)

            # Build priority_areas from top-ranked entities
            priority_areas = []
            for i, assessment in enumerate(deduped_assessments, 1):
                entity = assessment.auditable_entity
                priority_areas.append({
                    'rank': i,
                    'auditable_entity_id': str(entity.id),
                    'entity_name': entity.name,
                    'entity_type': entity.entity_type,
                    'entity_code': entity.code,
                    'risk_rating': assessment.overall_risk_rating.name if assessment.overall_risk_rating else 'N/A',
                    'risk_rating_code': assessment.overall_risk_rating.code if assessment.overall_risk_rating else None,
                    'weighted_score': float(assessment.calculated_weighted_score) if assessment.calculated_weighted_score else None,
                    'residual_score': float(assessment.calculated_residual_score) if assessment.calculated_residual_score else None,
                    'assessment_id': str(assessment.id),
                    'recommended_for_audit': True,
                })

            # Generate reference number
            year_code = fiscal_year.year_code.replace('/', '')
            existing_count = AuditPlan.objects.filter(fiscal_year=fiscal_year).count()
            ref_number = f"RBIAP-{year_code}-{existing_count + 1:03d}"

            with transaction.atomic():
                plan = AuditPlan.objects.create(
                    reference_number=ref_number,
                    title=f"Risk-Based Internal Audit Plan {fiscal_year.year_code}",
                    plan_type='annual',
                    status='draft',
                    audit_universe=universe,
                    fiscal_year=fiscal_year,
                    priority_areas=priority_areas,
                    resource_allocation={},
                    prepared_by=user_id,
                    created_by=user_id,
                )

            return Response(
                {
                    "success": True,
                    "data": AuditPlanSerializer(plan).data,
                    "message": (
                        f"Draft plan generated with {len(priority_areas)} prioritized "
                        f"entities based on approved risk assessments."
                    ),
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.exception("Failed to generate draft plan")
            return server_error_response(
                message="Failed to generate draft audit plan",
                details=str(e) if settings.DEBUG else None,
            )
