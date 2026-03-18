"""
Audit Finding CRUD Views for GRC Service
Provides full CRUD operations for audit finding management following FIMS patterns
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import (
    AuditFinding, AuditEngagement, FiscalYear, Quarter,
    FindingType, AuditSeverity, RiskRating, WorkingPaper, AuditMeeting
)
from apps.api.serializers.audit_serializers import AuditFindingSerializer
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_FINDING_EVENTS
from apps.api.permissions_jwt import (
    CanManageAuditFinding,
    CanRespondToAuditFinding,
    CanManagementRespondToAuditFinding,
)

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


class AuditFindingListCreateView(APIView):
    """List all audit findings or create a new one"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanManageAuditFinding().has_permission(request, self) or
                    CanRespondToAuditFinding().has_permission(request, self)):
                self.permission_denied(request, message='grc:audit_finding:manage or :respond required.')
        elif request.method == 'POST':
            if not CanManageAuditFinding().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_finding:manage required.')

    def get(self, request):
        """Get all audit findings with optional filtering and pagination"""
        try:
            # Get query parameters for filtering
            engagement_id = request.query_params.get('engagement')
            fiscal_year_id = request.query_params.get('fiscal_year')
            quarter_id = request.query_params.get('quarter')
            severity_id = request.query_params.get('severity')
            finding_type_id = request.query_params.get('finding_type')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')
            
            # Build query with related data
            queryset = AuditFinding.objects.select_related(
                'engagement',
                'engagement__audit_plan',
                'engagement__auditable_entity',
                'fiscal_year',
                'quarter',
                'finding_type',
                'severity',
                'risk_rating',
                'working_paper'
            ).all()
            
            # Apply filters
            if engagement_id:
                queryset = queryset.filter(engagement_id=engagement_id)
            if fiscal_year_id:
                queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
            if quarter_id:
                queryset = queryset.filter(quarter_id=quarter_id)
            if severity_id:
                queryset = queryset.filter(severity_id=severity_id)
            if finding_type_id:
                queryset = queryset.filter(finding_type_id=finding_type_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-created_at',
                allowed_fields=['created_at', 'status', 'reference_number', 'severity__level']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditFindingSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_finding",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit findings")
            return server_error_response(
                message="Failed to retrieve audit findings",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create a new audit finding"""
        try:
            serializer = AuditFindingSerializer(data=request.data)
            
            if serializer.is_valid():
                engagement_id = serializer.validated_data['engagement_id']
                reference_number = serializer.validated_data.get('reference_number', '').strip()
                
                # Verify engagement exists and is in fieldwork or reporting phase
                engagement = get_object_or_404(AuditEngagement, id=engagement_id)
                if engagement.status not in ['fieldwork', 'reporting']:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": f"Cannot create finding for engagement in '{engagement.status}' phase",
                                "code": "INVALID_ENGAGEMENT_PHASE"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Auto-generate reference number if not provided (FIMS pattern — same as WorkingPaper)
                if not reference_number:
                    count = AuditFinding.objects.filter(engagement=engagement).count()
                    reference_number = f"FND-{engagement.reference_number}-{count + 1:03d}"
                    serializer.validated_data['reference_number'] = reference_number

                # Check for duplicate reference number within engagement
                if reference_number and AuditFinding.objects.filter(
                    engagement_id=engagement_id,
                    reference_number=reference_number
                ).exists():
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Finding with this reference number already exists in this engagement",
                                "code": "DUPLICATE_REFERENCE"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verify lookup table references exist
                fiscal_year_id = serializer.validated_data.get('fiscal_year_id')
                quarter_id = serializer.validated_data.get('quarter_id')
                finding_type_id = serializer.validated_data.get('finding_type_id')
                severity_id = serializer.validated_data.get('severity_id')
                risk_rating_id = serializer.validated_data.get('risk_rating_id')
                
                if fiscal_year_id:
                    get_object_or_404(FiscalYear, id=fiscal_year_id)
                if quarter_id:
                    get_object_or_404(Quarter, id=quarter_id)
                if finding_type_id:
                    get_object_or_404(FindingType, id=finding_type_id)
                if severity_id:
                    get_object_or_404(AuditSeverity, id=severity_id)
                if risk_rating_id:
                    get_object_or_404(RiskRating, id=risk_rating_id)

                # GAP-F2: if a working_paper_id is supplied, it must belong to the same engagement
                working_paper_id = serializer.validated_data.get('working_paper_id')
                if working_paper_id:
                    try:
                        wp = WorkingPaper.objects.get(id=working_paper_id)
                    except WorkingPaper.DoesNotExist:
                        return Response(
                            {
                                "success": False,
                                "error": {
                                    "message": "Working paper not found",
                                    "code": "WP_NOT_FOUND"
                                }
                            },
                            status=status.HTTP_404_NOT_FOUND
                        )
                    if str(wp.engagement_id) != str(engagement_id):
                        return Response(
                            {
                                "success": False,
                                "error": {
                                    "message": "Working paper does not belong to this engagement",
                                    "code": "WP_ENGAGEMENT_MISMATCH"
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
                    finding = serializer.save(created_by=user_id)

                # Publish FIMS domain event — best-effort, never fails the request
                try:
                    severity_code = str(finding.severity.code) if finding.severity else ''
                    finding_type_code = str(finding.finding_type.code) if finding.finding_type else ''
                    messaging_service.publish_audit_finding_event(
                        event_type=AUDIT_FINDING_EVENTS['FINDING_CREATED'],
                        finding_id=finding.id,
                        engagement_id=finding.engagement_id,
                        additional_data={
                            'title': finding.title,
                            'severity': severity_code,
                            'finding_type': finding_type_code,
                            'created_by': str(user_id),
                            'user_id': str(user_id),
                        }
                    )
                except Exception as event_error:
                    logger.error(f"Error publishing finding created event: {event_error}")

                return Response(
                    {
                        "success": True,
                        "data": AuditFindingSerializer(finding).data,
                        "message": "Audit finding created successfully"
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
                        "message": "Failed to create audit finding",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditFindingDetailView(APIView):
    """Retrieve, update, or delete a specific audit finding"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanManageAuditFinding().has_permission(request, self) or
                    CanRespondToAuditFinding().has_permission(request, self)):
                self.permission_denied(request, message='grc:audit_finding:manage or :respond required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanManageAuditFinding().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_finding:manage required.')

    def get(self, request, pk):
        """Get a specific audit finding by ID"""
        try:
            finding = get_object_or_404(
                AuditFinding.objects.select_related(
                    'engagement',
                    'engagement__audit_plan',
                    'engagement__auditable_entity',
                    'fiscal_year',
                    'quarter',
                    'finding_type',
                    'severity',
                    'risk_rating',
                    'working_paper'
                ),
                pk=pk
            )
            
            serializer = AuditFindingSerializer(finding)
            
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "meta": {
                        "service": "grc-service",
                        "resource": "audit_finding",
                        "version": "v1.0",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to retrieve audit finding",
                        "details": str(e)
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Update an audit finding (full update)"""
        try:
            finding = get_object_or_404(AuditFinding, pk=pk)
            
            # Prevent updates to final findings
            if finding.status == 'final':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update final finding",
                            "code": "FINDING_FINALIZED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AuditFindingSerializer(finding, data=request.data)
            
            if serializer.is_valid():
                # GAP-F2: if a working_paper_id is supplied, it must belong to the same engagement
                working_paper_id = serializer.validated_data.get('working_paper_id')
                if working_paper_id:
                    engagement_id = serializer.validated_data.get('engagement_id', finding.engagement_id)
                    try:
                        wp = WorkingPaper.objects.get(id=working_paper_id)
                    except WorkingPaper.DoesNotExist:
                        return Response(
                            {
                                "success": False,
                                "error": {
                                    "message": "Working paper not found",
                                    "code": "WP_NOT_FOUND"
                                }
                            },
                            status=status.HTTP_404_NOT_FOUND
                        )
                    if str(wp.engagement_id) != str(engagement_id):
                        return Response(
                            {
                                "success": False,
                                "error": {
                                    "message": "Working paper does not belong to this engagement",
                                    "code": "WP_ENGAGEMENT_MISMATCH"
                                }
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )
                with transaction.atomic():
                    # Get user ID for modified_by tracking — require authenticated user
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    updated_finding = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditFindingSerializer(updated_finding).data,
                        "message": "Audit finding updated successfully"
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
                        "message": "Failed to update audit finding",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Partially update an audit finding"""
        try:
            finding = get_object_or_404(AuditFinding, pk=pk)
            
            # Prevent updates to final findings
            if finding.status == 'final':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update final finding",
                            "code": "FINDING_FINALIZED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AuditFindingSerializer(finding, data=request.data, partial=True)
            
            if serializer.is_valid():
                # GAP-F2: if a working_paper_id is supplied, it must belong to the same engagement
                working_paper_id = serializer.validated_data.get('working_paper_id')
                if working_paper_id:
                    engagement_id = serializer.validated_data.get('engagement_id', finding.engagement_id)
                    try:
                        wp = WorkingPaper.objects.get(id=working_paper_id)
                    except WorkingPaper.DoesNotExist:
                        return Response(
                            {
                                "success": False,
                                "error": {
                                    "message": "Working paper not found",
                                    "code": "WP_NOT_FOUND"
                                }
                            },
                            status=status.HTTP_404_NOT_FOUND
                        )
                    if str(wp.engagement_id) != str(engagement_id):
                        return Response(
                            {
                                "success": False,
                                "error": {
                                    "message": "Working paper does not belong to this engagement",
                                    "code": "WP_ENGAGEMENT_MISMATCH"
                                }
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )
                with transaction.atomic():
                    # Get user ID for modified_by tracking — require authenticated user
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    updated_finding = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": AuditFindingSerializer(updated_finding).data,
                        "message": "Audit finding updated successfully"
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
                        "message": "Failed to update audit finding",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Soft delete an audit finding"""
        try:
            finding = get_object_or_404(AuditFinding, pk=pk)
            
            # Prevent deletion of final findings
            if finding.status == 'final':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete final finding",
                            "code": "FINDING_FINALIZED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if finding has recommendations
            if hasattr(finding, 'recommendations') and finding.recommendations.filter(is_active=True).exists():
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete finding with active recommendations",
                            "code": "HAS_ACTIVE_RECOMMENDATIONS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                finding.is_active = False
                finding.save(update_fields=['is_active'])
            
            return Response(
                {
                    "success": True,
                    "message": "Audit finding deleted successfully"
                },
                status=status.HTTP_200_OK
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete audit finding",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditFindingFinalizeView(APIView):
    """Finalize a finding after discussion with auditee"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditFinding().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_finding:manage required.')

    def post(self, request, pk):
        """Move finding through workflow: draft → discussed → final"""
        try:
            finding = get_object_or_404(AuditFinding, pk=pk)
            
            target_status = request.data.get('target_status')
            
            # Valid status transitions
            valid_transitions = {
                'draft': ['discussed'],
                'discussed': ['final', 'draft'],  # Can go back to draft for revisions
            }
            
            if target_status not in valid_transitions.get(finding.status, []):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot transition from '{finding.status}' to '{target_status}'",
                            "code": "INVALID_STATUS_TRANSITION",
                            "current_status": finding.status,
                            "allowed_transitions": valid_transitions.get(finding.status, [])
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # GAP-F4: draft → discussed requires a completed Pre-Exit meeting (SRS Step 17)
            if target_status == 'discussed':
                has_preexit = AuditMeeting.objects.filter(
                    engagement=finding.engagement,
                    meeting_type='pre_exit',
                    status='completed'
                ).exists()
                if not has_preexit:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "A completed Pre-Exit meeting is required before marking a finding as discussed",
                                "code": "PRE_EXIT_MEETING_REQUIRED"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Require responses before finalizing
            if target_status == 'final':
                if not finding.auditee_response:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Auditee response required before finalizing finding",
                                "code": "MISSING_AUDITEE_RESPONSE"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if not finding.management_response:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Management response required before finalizing finding",
                                "code": "MISSING_MANAGEMENT_RESPONSE"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            with transaction.atomic():
                finding.status = target_status
                now = timezone.now()
                update_fields = ['status']
                if target_status == 'discussed' and not finding.discussed_at:
                    finding.discussed_at = now
                    update_fields.append('discussed_at')
                elif target_status == 'final' and not finding.finalized_at:
                    finding.finalized_at = now
                    update_fields.append('finalized_at')
                finding.save(update_fields=update_fields)
            
            return Response(
                {
                    "success": True,
                    "data": AuditFindingSerializer(finding).data,
                    "message": f"Finding transitioned to {target_status} successfully"
                }
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to finalize finding",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditFindingResponseView(APIView):
    """Add or update auditee/management responses"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        # Only the auditee (respond) or management (management_respond) may call this endpoint.
        # The Lead Auditor (manage) manages findings but does NOT write responses.
        is_auditee_responder = CanRespondToAuditFinding().has_permission(request, self)
        is_management_responder = CanManagementRespondToAuditFinding().has_permission(request, self)
        if not (is_auditee_responder or is_management_responder):
            self.permission_denied(
                request,
                message='grc:audit_finding:respond or grc:audit_finding:management_respond required.',
            )

    def patch(self, request, pk):
        """Update finding responses"""
        try:
            finding = get_object_or_404(AuditFinding, pk=pk)
            
            # Cannot modify responses on final findings
            if finding.status == 'final':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot modify responses on final finding",
                            "code": "FINDING_FINALIZED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            auditee_response = request.data.get('auditee_response')
            management_response = request.data.get('management_response')

            # ── Role-based field enforcement (GAP-F3) ─────────────────────────
            # Per RBAC matrix:
            #   grc:audit_finding:respond            → auditee       → may only set auditee_response
            #   grc:audit_finding:management_respond → management    → may only set management_response
            is_auditee_responder = CanRespondToAuditFinding().has_permission(request, self)
            is_management_responder = CanManagementRespondToAuditFinding().has_permission(request, self)

            # Auditee: strip management_response and block if they try to force it
            if is_auditee_responder and not is_management_responder:
                management_response = None

            if management_response is not None and not is_management_responder:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Only management can provide management response",
                            "code": "PERMISSION_DENIED"
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            # Management: strip auditee_response and block if they try to force it
            if is_management_responder and not is_auditee_responder:
                auditee_response = None

            if auditee_response is not None and not is_auditee_responder:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Only auditees can provide auditee response",
                            "code": "PERMISSION_DENIED"
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            # ──────────────────────────────────────────────────────────────────

            fields_to_save = []
            with transaction.atomic():
                if auditee_response is not None:
                    finding.auditee_response = auditee_response
                    fields_to_save.append('auditee_response')
                if management_response is not None:
                    finding.management_response = management_response
                    fields_to_save.append('management_response')

                if fields_to_save:
                    finding.save(update_fields=fields_to_save)

            return Response(
                {
                    "success": True,
                    "data": AuditFindingSerializer(finding).data,
                    "message": "Responses updated successfully"
                }
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update responses",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
