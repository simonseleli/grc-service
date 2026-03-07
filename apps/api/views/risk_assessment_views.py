"""
Risk Assessment CRUD Views for GRC Service
Provides full CRUD operations for risk assessment management following FIMS patterns
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

from apps.core.models import RiskAssessment, AuditableEntity, RiskRating
from apps.api.serializers.audit_serializers import RiskAssessmentSerializer
from apps.api.permissions_jwt import (
    CanConductRiskAssessment,
    CanReviewRiskAssessment,
)
from apps.infrastructure.external.document_service_client import (
    get_document_client,
    DocumentServiceError,
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
    server_error_response,
)



class RiskAssessmentListCreateView(APIView):
    """List all risk assessments or create a new one"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanConductRiskAssessment().has_permission(request, self) or
                    CanReviewRiskAssessment().has_permission(request, self)):
                self.permission_denied(request, message='grc:risk_assessment:conduct or :review required.')
        elif request.method == 'POST':
            if not CanConductRiskAssessment().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_assessment:conduct required.')

    def get(self, request):
        """Get all risk assessments with optional filtering and pagination"""
        try:
            # Get query parameters for filtering
            entity_id = request.query_params.get('auditable_entity')
            assessment_period = request.query_params.get('assessment_period')
            overall_rating = request.query_params.get('overall_risk_rating')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')
            
            # Build query with related data
            queryset = RiskAssessment.objects.select_related(
                'auditable_entity',
                'auditable_entity__audit_universe',
                'overall_risk_rating',
                'residual_risk_rating',
                'auto_overall_rating',
                'auto_residual_rating',
            ).all()
            
            # Apply filters
            if entity_id:
                queryset = queryset.filter(auditable_entity_id=entity_id)
            if assessment_period:
                queryset = queryset.filter(assessment_period=assessment_period)
            if overall_rating:
                queryset = queryset.filter(overall_risk_rating_id=overall_rating)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-created_at',
                allowed_fields=['created_at', 'assessment_period', 'status', 'assessment_date']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = RiskAssessmentSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="risk_assessment",
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk assessments")
            return server_error_response(
                message="Failed to retrieve risk assessments",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create a new risk assessment"""
        try:
            serializer = RiskAssessmentSerializer(data=request.data)
            
            if serializer.is_valid():
                entity_id = serializer.validated_data['auditable_entity_id']
                assessment_period = serializer.validated_data.get('assessment_period')
                
                # Verify auditable entity exists
                entity = get_object_or_404(AuditableEntity, id=entity_id)
                
                # Check for duplicate assessment for same period
                if assessment_period and RiskAssessment.objects.filter(
                    auditable_entity_id=entity_id,
                    assessment_period=assessment_period,
                    is_active=True
                ).exists():
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Risk assessment for this entity and period already exists",
                                "code": "DUPLICATE_ASSESSMENT"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verify risk rating IDs exist
                overall_rating_id = serializer.validated_data.get('overall_risk_rating_id')
                residual_rating_id = serializer.validated_data.get('residual_risk_rating_id')
                
                if overall_rating_id:
                    get_object_or_404(RiskRating, id=overall_rating_id)
                if residual_rating_id:
                    get_object_or_404(RiskRating, id=residual_rating_id)
                
                with transaction.atomic():
                    # Get user ID from request or use system user
                    # FIMS pattern: always require authenticated user — no system user fallback
                    user_id = getattr(request.user, 'id', None)
                    if not user_id:
                        return Response(
                            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                    
                    # Set assessed_by if not provided
                    assessed_by = serializer.validated_data.get('assessed_by', user_id)
                    
                    assessment = serializer.save(created_by=user_id, assessed_by=assessed_by)
                
                return Response(
                    {
                        "success": True,
                        "data": RiskAssessmentSerializer(assessment).data,
                        "message": "Risk assessment created successfully"
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
                        "message": "Failed to create risk assessment",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RiskAssessmentDetailView(APIView):
    """Retrieve, update, or delete a specific risk assessment"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanConductRiskAssessment().has_permission(request, self) or
                    CanReviewRiskAssessment().has_permission(request, self)):
                self.permission_denied(request, message='grc:risk_assessment:conduct or :review required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanConductRiskAssessment().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_assessment:conduct required.')

    def get(self, request, pk):
        """Get a specific risk assessment by ID"""
        try:
            assessment = get_object_or_404(
                RiskAssessment.objects.select_related(
                    'auditable_entity',
                    'auditable_entity__audit_universe',
                    'overall_risk_rating',
                    'residual_risk_rating',
                    'auto_overall_rating',
                    'auto_residual_rating',
                ),
                pk=pk
            )
            
            serializer = RiskAssessmentSerializer(assessment)
            
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "meta": {
                        "service": "grc-service",
                        "resource": "risk_assessment",
                        "version": "v1.0",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to retrieve risk assessment",
                        "details": str(e)
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Update a risk assessment (full update)"""
        try:
            assessment = get_object_or_404(RiskAssessment, pk=pk)
            
            # Prevent updates to approved assessments
            if assessment.status == 'approved':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update approved risk assessment",
                            "code": "ASSESSMENT_APPROVED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = RiskAssessmentSerializer(assessment, data=request.data)
            
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
                    
                    updated_assessment = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": RiskAssessmentSerializer(updated_assessment).data,
                        "message": "Risk assessment updated successfully"
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
                        "message": "Failed to update risk assessment",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Partially update a risk assessment"""
        try:
            assessment = get_object_or_404(RiskAssessment, pk=pk)
            
            # Prevent updates to approved assessments
            if assessment.status == 'approved':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot update approved risk assessment",
                            "code": "ASSESSMENT_APPROVED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = RiskAssessmentSerializer(assessment, data=request.data, partial=True)
            
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
                    
                    updated_assessment = serializer.save(modified_by=user_id)
                
                return Response(
                    {
                        "success": True,
                        "data": RiskAssessmentSerializer(updated_assessment).data,
                        "message": "Risk assessment updated successfully"
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
                        "message": "Failed to update risk assessment",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Soft delete a risk assessment"""
        try:
            assessment = get_object_or_404(RiskAssessment, pk=pk)
            
            # Prevent deletion of approved assessments
            if assessment.status == 'approved':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete approved risk assessment",
                            "code": "ASSESSMENT_APPROVED"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                assessment.is_active = False
                assessment.save(update_fields=['is_active'])
            
            return Response(
                {
                    "success": True,
                    "message": "Risk assessment deleted successfully"
                },
                status=status.HTTP_200_OK
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete risk assessment",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RiskAssessmentSubmitView(APIView):
    """Submit a risk assessment for review"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanConductRiskAssessment().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_assessment:conduct required.')

    def post(self, request, pk):
        """Submit assessment for review or approval"""
        try:
            assessment = get_object_or_404(RiskAssessment, pk=pk)
            
            # Only draft or reviewed assessments can be submitted
            if assessment.status not in ['draft', 'reviewed']:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Cannot submit assessment with status '{assessment.status}'",
                            "code": "INVALID_STATUS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                if assessment.status == 'draft':
                    assessment.status = 'submitted'
                    message = "Risk assessment submitted for review successfully"
                elif assessment.status == 'reviewed':
                    assessment.status = 'approved'
                    message = "Risk assessment approved successfully"
                
                assessment.save(update_fields=['status'])
            
            return Response(
                {
                    "success": True,
                    "data": RiskAssessmentSerializer(assessment).data,
                    "message": message
                }
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to submit risk assessment",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RiskAssessmentReviewView(APIView):
    """Review and approve/reject a risk assessment"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanReviewRiskAssessment().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_assessment:review required.')

    def post(self, request, pk):
        """Review assessment with action (approve/reject)"""
        try:
            assessment = get_object_or_404(RiskAssessment, pk=pk)
            
            action = request.data.get('action')
            comments = request.data.get('comments', '')
            
            if action not in ['approve', 'reject']:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid action. Must be 'approve' or 'reject'",
                            "code": "INVALID_ACTION"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Only submitted assessments can be reviewed
            if assessment.status != 'submitted':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Only submitted assessments can be reviewed",
                            "code": "INVALID_STATUS"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Get reviewer ID
                # FIMS pattern: always require authenticated user — no system user fallback
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                
                assessment.reviewed_by = user_id
                
                if action == 'approve':
                    assessment.status = 'reviewed'
                    message = "Risk assessment reviewed and moved to approved status"
                else:  # reject
                    assessment.status = 'draft'
                    message = f"Risk assessment rejected and returned to draft. Reason: {comments}"
                
                assessment.save(update_fields=['status', 'reviewed_by'])
            
            return Response(
                {
                    "success": True,
                    "data": RiskAssessmentSerializer(assessment).data,
                    "message": message
                }
            )
                
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to review risk assessment",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RiskAssessmentEvidenceView(APIView):
    """Manage evidence attachments on a risk assessment (GAP 10).

    Delegates file storage to Document Records Service (Principle 2).
    GRC stores only the DRS document UUIDs in ``evidence_attachments``.

    POST  /risk-assessments/{pk}/evidence/  — upload evidence file(s)
    GET   /risk-assessments/{pk}/evidence/  — list evidence metadata from DRS
    DELETE /risk-assessments/{pk}/evidence/{document_id}/ — detach evidence
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanConductRiskAssessment().has_permission(request, self) or
                    CanReviewRiskAssessment().has_permission(request, self)):
                self.permission_denied(request, message='grc:risk_assessment:conduct or :review required.')
        elif request.method in ('POST', 'DELETE'):
            if not CanConductRiskAssessment().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_assessment:conduct required.')

    # ── helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _get_auth_token(request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        return auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None

    # ── GET — list evidence metadata ─────────────────────────────────
    def get(self, request, pk, document_id=None):
        """Return metadata for all evidence documents attached to this assessment."""
        try:
            assessment = get_object_or_404(RiskAssessment, pk=pk)
            doc_ids = assessment.evidence_attachments or []

            if not doc_ids:
                return Response({
                    "success": True,
                    "data": [],
                    "meta": {"total": 0},
                })

            auth_token = self._get_auth_token(request)
            client = get_document_client(auth_token=auth_token)

            documents = []
            for did in doc_ids:
                try:
                    doc = client.get_document(str(did))
                    doc['download_url'] = client.get_download_url(str(did))
                    # Normalize to EvidenceAttachment frontend type
                    doc['document_id'] = doc.get('id', '')
                    doc['filename'] = (
                        doc.get('title') or doc.get('file_name') or
                        doc.get('filename') or ''
                    )
                    doc['upload_url'] = doc.get('download_url')
                    doc['uploaded_by'] = doc.get('created_by')
                    documents.append(doc)
                except DocumentServiceError:
                    # Document may have been deleted in DRS — still include a stub
                    documents.append({
                        'id': str(did),
                        'document_id': str(did),
                        'filename': '(unavailable)',
                        'status': 'missing',
                        'download_url': None,
                        'upload_url': None,
                    })

            return Response({
                "success": True,
                "data": documents,
                "meta": {"total": len(documents)},
            })
        except Exception as e:
            logger.exception("Failed to retrieve evidence attachments")
            return server_error_response(
                message="Failed to retrieve evidence attachments",
                details=str(e) if settings.DEBUG else None,
            )

    # ── POST — upload evidence file to DRS and attach UUID ───────────
    def post(self, request, pk, document_id=None):
        """Upload evidence file to DRS and link to assessment.

        Accepts ``multipart/form-data`` with:
        - ``file`` — the evidence file (required)
        - ``title`` — document title (optional, defaults to filename)
        - ``description`` — document description (optional)
        """
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated",
                    code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            assessment = get_object_or_404(RiskAssessment, pk=pk)

            # Prevent uploads to approved assessments
            if assessment.status == 'approved':
                return error_response(
                    message="Cannot add evidence to an approved assessment",
                    code="ASSESSMENT_APPROVED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return error_response(
                    message="No file provided",
                    code="FILE_REQUIRED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            title = request.data.get('title', uploaded_file.name)
            description = request.data.get(
                'description',
                f"Evidence for risk assessment: {assessment.auditable_entity.name} ({assessment.assessment_period})",
            )

            auth_token = self._get_auth_token(request)
            client = get_document_client(auth_token=auth_token)

            # Step 1: Create document + upload to DRS
            try:
                document = client.create_document_with_file(
                    title=title,
                    description=description,
                    file_data=uploaded_file,
                    file_name=uploaded_file.name,
                    document_type='audit_working_paper',
                    classification='confidential',
                    record_type='non_permanent',
                    retention_period=2555,  # 7 years for audit records
                    metadata={
                        'risk_assessment_id': str(assessment.id),
                        'auditable_entity_id': str(assessment.auditable_entity_id),
                        'entity_name': assessment.auditable_entity.name,
                        'assessment_period': assessment.assessment_period,
                        'service': 'grc-service',
                        'module': 'risk_assessment_evidence',
                    },
                    tags=['audit', 'evidence', 'risk-assessment',
                          assessment.auditable_entity.code],
                )
                new_doc_id = str(document['id'])
            except DocumentServiceError as e:
                logger.error(f"DRS upload failed for assessment {pk}: {e}")
                return error_response(
                    message="Failed to upload file to Document Records Service",
                    code="DOCUMENT_SERVICE_ERROR",
                    status_code=status.HTTP_502_BAD_GATEWAY,
                )

            # Step 2: Append UUID to evidence_attachments
            with transaction.atomic():
                # Re-read to avoid lost updates
                assessment = RiskAssessment.objects.select_for_update().get(pk=pk)
                attachments = list(assessment.evidence_attachments or [])
                if new_doc_id not in attachments:
                    attachments.append(new_doc_id)
                assessment.evidence_attachments = attachments
                assessment.save(update_fields=['evidence_attachments'])

            logger.info(
                f"Evidence {new_doc_id} attached to assessment {pk} by user {user_id}"
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "document_id": new_doc_id,
                        "title": title,
                        "file_name": uploaded_file.name,
                        "assessment_id": str(pk),
                        "total_evidence": len(attachments),
                    },
                    "message": "Evidence uploaded and attached successfully",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.exception("Failed to upload evidence")
            return server_error_response(
                message="Failed to upload evidence",
                details=str(e) if settings.DEBUG else None,
            )


class RiskAssessmentEvidenceDetailView(APIView):
    """Detach a single evidence document from a risk assessment.

    DELETE /risk-assessments/{pk}/evidence/{document_id}/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanConductRiskAssessment().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_assessment:conduct required.')

    def delete(self, request, pk, document_id):
        """Remove a document UUID from the assessment's evidence list.

        This does NOT delete the document from DRS — it only detaches it.
        """
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated",
                    code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            assessment = get_object_or_404(RiskAssessment, pk=pk)

            if assessment.status == 'approved':
                return error_response(
                    message="Cannot modify evidence on an approved assessment",
                    code="ASSESSMENT_APPROVED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            doc_str = str(document_id)
            with transaction.atomic():
                assessment = RiskAssessment.objects.select_for_update().get(pk=pk)
                attachments = list(assessment.evidence_attachments or [])
                if doc_str not in attachments:
                    return error_response(
                        message="Document not found in evidence attachments",
                        code="EVIDENCE_NOT_FOUND",
                        status_code=status.HTTP_404_NOT_FOUND,
                    )
                attachments.remove(doc_str)
                assessment.evidence_attachments = attachments
                assessment.save(update_fields=['evidence_attachments'])

            logger.info(
                f"Evidence {document_id} detached from assessment {pk} by user {user_id}"
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "document_id": doc_str,
                        "assessment_id": str(pk),
                        "total_evidence": len(attachments),
                    },
                    "message": "Evidence detached successfully",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Failed to detach evidence")
            return server_error_response(
                message="Failed to detach evidence",
                details=str(e) if settings.DEBUG else None,
            )
