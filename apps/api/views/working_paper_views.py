"""
Working Paper Views - Phase 2 Week 1 + FIMS Document Storage Integration
Handles CRUD operations for audit working papers with Document Records Service integration
"""

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import WorkingPaper, AuditEngagement
from apps.api.serializers import WorkingPaperSerializer, WorkingPaperListSerializer
from apps.infrastructure.external.document_service_client import (
    get_document_client, 
    DocumentServiceError
)
from apps.core.services.working_paper_service import WorkingPaperService
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import WORKING_PAPER_EVENTS
from apps.api.permissions_jwt import (
    CanManageWorkingPaper,
    CanReviewWorkingPaper,
    CanManageAuditEngagement,
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

logger = logging.getLogger(__name__)


class EngagementWorkingPapersView(APIView):
    """
    GET: List all working papers for an engagement
    POST: Create a new working paper for an engagement (with Document Service integration)
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Support file uploads
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanManageWorkingPaper().has_permission(request, self) or
                    CanReviewWorkingPaper().has_permission(request, self) or
                    CanManageAuditEngagement().has_permission(request, self)):
                self.permission_denied(
                    request,
                    message='grc:audit_working_paper:manage, :review, or grc:audit_engagement:manage required.',
                )
        elif request.method == 'POST':
            if not CanManageWorkingPaper().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_working_paper:manage required.')

    def get(self, request, engagement_id):
        """List working papers for an engagement with pagination"""
        try:
            engagement = get_object_or_404(AuditEngagement, id=engagement_id)
            
            # Filter by review status if provided
            review_status = request.query_params.get('review_status')
            paper_type = request.query_params.get('paper_type')
            
            queryset = WorkingPaper.objects.filter(engagement=engagement)
            
            if review_status:
                queryset = queryset.filter(review_status=review_status)
            if paper_type:
                queryset = queryset.filter(paper_type=paper_type)
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-created_at',
                allowed_fields=['created_at', 'paper_type', 'review_status', 'title']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = WorkingPaperListSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="working_paper",
                engagement_id=str(engagement_id),
            )
            
        except Exception as e:
            logger.exception(f"Error listing working papers for engagement {engagement_id}")
            return server_error_response(
                message="Failed to retrieve working papers",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, engagement_id):
        """
        Create a new working paper with Document Records Service integration.
        
        FIMS Pattern:
        1. Create document metadata in Document Records Service
        2. Upload file (if provided)
        3. Store document_id in GRC database
        """
        try:
            # FIMS Pattern: Always validate user_id from JWT token
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "User not authenticated",
                            "code": "AUTH_REQUIRED"
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            engagement = get_object_or_404(AuditEngagement, id=engagement_id)
            
            # Extract file from request (if provided)
            uploaded_file = request.FILES.get('file')
            
            # Get JWT token from request for service-to-service calls
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
            
            # Auto-generate reference number
            count = WorkingPaper.objects.filter(engagement=engagement).count()
            reference_number = f"WP-{engagement.reference_number}-{count + 1:03d}"
            
            # Get working paper metadata
            title = request.data.get('title')
            paper_type = request.data.get('paper_type', 'other')
            
            if not title:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Title is required",
                            "code": "VALIDATION_ERROR"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Step 1: Create document metadata in Document Records Service
            document_client = get_document_client(auth_token=auth_token)
            
            try:
                document = document_client.create_document(
                    title=title,
                    description=f"Working paper for audit engagement: {engagement.title}",
                    document_type='audit_working_paper',
                    classification='confidential',  # Audit documents are confidential
                    record_type='non_permanent',
                    retention_period=2555,  # 7 years for audit records
                    metadata={
                        'engagement_id': str(engagement.id),
                        'engagement_reference': engagement.reference_number,
                        'paper_type': paper_type,
                        'service': 'grc-service',
                        'module': 'working_papers'
                    },
                    tags=['audit', 'working-paper', paper_type, engagement.reference_number]
                )
                
                document_id = document['id']
                logger.info(f"Document {document_id} created in Document Records Service for working paper")
                
            except DocumentServiceError as e:
                logger.error(f"Failed to create document in Document Records Service: {e}")
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Failed to create document in Document Records Service",
                            "details": str(e),
                            "code": "DOCUMENT_SERVICE_ERROR"
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Step 2: Upload file if provided
            if uploaded_file:
                try:
                    document = document_client.upload_file(
                        document_id=document_id,
                        file_data=uploaded_file,
                        file_name=uploaded_file.name
                    )
                    logger.info(f"File uploaded to document {document_id}: {uploaded_file.name}")
                except DocumentServiceError as e:
                    # Document created but file upload failed
                    logger.warning(f"Document {document_id} created but file upload failed: {e}")
                    # Continue anyway - user can upload file later
            
            # Step 3: Create WorkingPaper metadata in GRC database
            working_paper = WorkingPaper.objects.create(
                engagement=engagement,
                reference_number=reference_number,
                title=title,
                paper_type=paper_type,
                document_id=document_id,  # Reference to Document Records Service
                evidence_document_ids=[],  # Empty initially
                prepared_by=user_id,  # Real user ID from IAM token
                review_status='draft',
                created_by=user_id,
                modified_by=user_id
            )
            
            logger.info(f"Working paper {working_paper.id} created for engagement {engagement_id} by user {user_id}")
            
            # Step 4: Publish event to Kafka
            try:
                event_published = messaging_service.publish_working_paper_event(
                    event_type=WORKING_PAPER_EVENTS['WORKING_PAPER_CREATED'],
                    working_paper_id=working_paper.id,
                    engagement_id=engagement.id,
                    additional_data={
                        'title': title,
                        'paper_type': paper_type,
                        'document_id': str(document_id),
                        'reference_number': reference_number,
                        'engagement_title': engagement.title,
                        'created_by': str(user_id)
                    }
                )
                
                if event_published:
                    logger.info(f"Published working paper created event for {working_paper.id}")
                else:
                    logger.warning(f"Failed to publish working paper created event for {working_paper.id}")
            except Exception as event_error:
                # Don't fail the request if event publishing fails
                logger.error(f"Error publishing working paper created event: {str(event_error)}")
            
            serializer = WorkingPaperSerializer(working_paper)
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "message": "Working paper created successfully"
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error creating working paper for engagement {engagement_id}: {str(e)}", exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to create working paper",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WorkingPaperDetailView(APIView):
    """
    GET: Retrieve working paper details
    PUT: Update working paper
    DELETE: Delete working paper
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanManageWorkingPaper().has_permission(request, self) or
                    CanReviewWorkingPaper().has_permission(request, self)):
                self.permission_denied(
                    request,
                    message='grc:audit_working_paper:manage or :review required.',
                )
        elif request.method in ('PUT', 'DELETE'):
            if not CanManageWorkingPaper().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_working_paper:manage required.')

    def get(self, request, paper_id):
        """Get working paper details"""
        try:
            working_paper = get_object_or_404(WorkingPaper, id=paper_id)
            serializer = WorkingPaperSerializer(working_paper)
            return Response(
                {
                    "success": True,
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error retrieving working paper {paper_id}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to retrieve working paper",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, paper_id):
        """Update working paper"""
        try:
            # FIMS Pattern: Always validate user_id
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "User not authenticated",
                            "code": "AUTH_REQUIRED"
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            working_paper = get_object_or_404(WorkingPaper, id=paper_id)
            
            # Check if paper is approved (cannot edit approved papers)
            if working_paper.review_status == 'approved':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot edit approved working paper",
                            "code": "APPROVED_PAPER"
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Ensure user is the preparer
            if str(working_paper.prepared_by) != str(user_id):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Only the preparer can edit this working paper",
                            "code": "PERMISSION_DENIED"
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = WorkingPaperSerializer(working_paper, data=request.data, partial=True)
            if serializer.is_valid():
                working_paper = serializer.save()
                logger.info(f"Working paper {paper_id} updated by user {user_id}")
                return Response(
                    {
                        "success": True,
                        "data": serializer.data,
                        "message": "Working paper updated successfully"
                    },
                    status=status.HTTP_200_OK
                )
                
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
            logger.error(f"Error updating working paper {paper_id}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update working paper",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, paper_id):
        """Delete working paper"""
        try:
            # FIMS Pattern: Always validate user_id
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "User not authenticated",
                            "code": "AUTH_REQUIRED"
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            working_paper = get_object_or_404(WorkingPaper, id=paper_id)
            
            # Check if paper is approved (cannot delete approved papers)
            if working_paper.review_status == 'approved':
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete approved working paper",
                            "code": "APPROVED_PAPER"
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Ensure user is the preparer
            if str(working_paper.prepared_by) != str(user_id):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Only the preparer can delete this working paper",
                            "code": "PERMISSION_DENIED"
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            working_paper.delete()
            logger.info(f"Working paper {paper_id} deleted by user {user_id}")
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error deleting working paper {paper_id}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to delete working paper",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WorkingPaperReviewView(APIView):
    """
    POST /working-papers/<paper_id>/review/
        Submit a working paper to the Work Orchestration Service.
        Creates a workflow plan and stores the plan UUID on the working paper.

    PATCH /working-papers/<paper_id>/review/
        Internal endpoint — update local review_status when WOS emits an event
        (called by Kafka consumer or testing).
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'POST':
            if not CanManageWorkingPaper().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_working_paper:manage required.')
        elif request.method == 'PATCH':
            if not CanReviewWorkingPaper().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_working_paper:review required.')

    def post(self, request, paper_id):
        """Submit working paper for approval via Work Orchestration Service."""
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        working_paper = get_object_or_404(WorkingPaper, id=paper_id)

        if str(working_paper.prepared_by) != str(user_id):
            return Response(
                {"success": False, "error": {"message": "Only the preparer can submit for review", "code": "PERMISSION_DENIED"}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if working_paper.review_status != "draft":
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": f"Working paper is already in '{working_paper.review_status}' status",
                        "code": "INVALID_STATUS",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


        try:
            service = WorkingPaperService()
            wp = service.submit_for_approval(
                working_paper_id=str(paper_id),
                submitter_id=str(user_id),
            )
        except Exception as exc:
            logger.error("Error submitting working paper %s for review: %s", paper_id, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to start workflow", "details": str(exc)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Publish local event so other services stay in sync
        try:
            messaging_service.publish_working_paper_event(
                event_type=WORKING_PAPER_EVENTS.get("WORKING_PAPER_SUBMITTED", "working_paper.submitted"),
                working_paper_id=wp.id,
                engagement_id=wp.engagement_id,
                additional_data={
                    "workflow_plan_id": str(wp.workflow_plan_id) if wp.workflow_plan_id else None,
                    "submitted_by": str(user_id),
                },
            )
        except Exception as event_error:
            logger.error("Error publishing submission event for WP %s: %s", paper_id, event_error)

        serializer = WorkingPaperSerializer(wp)
        return Response(
            {
                "success": True,
                "data": serializer.data,
                "message": "Working paper submitted for review",
                "workflow_plan_id": str(wp.workflow_plan_id) if wp.workflow_plan_id else None,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, paper_id):
        """
        Update local review_status from a workflow event.

        Expected body: { "action": "approved" | "rejected", "review_comments": "..." }
        """
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        working_paper = get_object_or_404(WorkingPaper, id=paper_id)
        action = request.data.get("action")

        if action == "approved":
            working_paper.review_status = "approved"
            working_paper.reviewed_by = user_id
            working_paper.save(update_fields=["review_status", "reviewed_by"])
            logger.info("WorkingPaper %s approved by %s", paper_id, user_id)

        elif action == "rejected":
            working_paper.review_status = "reviewed"
            working_paper.reviewed_by = user_id
            working_paper.review_comments = request.data.get("review_comments", "")
            working_paper.save(update_fields=["review_status", "reviewed_by", "review_comments"])
            logger.info("WorkingPaper %s rejected by %s", paper_id, user_id)

        else:
            return Response(
                {"success": False, "error": {"message": "Invalid action. Use: approved or rejected", "code": "INVALID_ACTION"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = WorkingPaperSerializer(working_paper)
        return Response(
            {"success": True, "data": serializer.data, "message": f"Working paper {action} successfully"},
            status=status.HTTP_200_OK,
        )


class WorkingPaperWorkflowStatusView(APIView):
    """
    GET /working-papers/<paper_id>/workflow-status/
        Return the current state of the workflow plan in Work Orchestration Service.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanManageWorkingPaper().has_permission(request, self) or
                CanReviewWorkingPaper().has_permission(request, self)):
            self.permission_denied(
                request,
                message='grc:audit_working_paper:manage or :review required.',
            )

    def get(self, request, paper_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        working_paper = get_object_or_404(WorkingPaper, id=paper_id)

        if not working_paper.workflow_plan_id:
            return Response(
                {
                    "success": True,
                    "data": {
                        "has_workflow": False,
                        "status": working_paper.review_status,
                    },
                },
                status=status.HTTP_200_OK,
            )


        try:
            workflow_data = WorkingPaperService().get_workflow_status(str(paper_id))
        except Exception as exc:
            logger.error("Error fetching workflow status for WP %s: %s", paper_id, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to retrieve workflow status", "details": str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"success": True, "data": workflow_data}, status=status.HTTP_200_OK)


class WorkingPaperWorkflowHistoryView(APIView):
    """
    GET /working-papers/<paper_id>/workflow-history/
        Return the activity log of the workflow plan from Work Orchestration Service.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanManageWorkingPaper().has_permission(request, self) or
                CanReviewWorkingPaper().has_permission(request, self)):
            self.permission_denied(
                request,
                message='grc:audit_working_paper:manage or :review required.',
            )

    def get(self, request, paper_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        working_paper = get_object_or_404(WorkingPaper, id=paper_id)

        if not working_paper.workflow_plan_id:
            return Response(
                {
                    "success": True,
                    "data": {
                        "has_workflow": False,
                        "activity": [],
                    },
                },
                status=status.HTTP_200_OK,
            )


        try:
            activity = WorkingPaperService().get_workflow_history(str(paper_id))
        except Exception as exc:
            logger.error("Error fetching workflow activity for WP %s: %s", paper_id, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to retrieve workflow history", "details": str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "success": True,
                "data": {
                    "has_workflow": True,
                    "workflow_plan_id": str(working_paper.workflow_plan_id),
                    "activity": activity,
                },
            },
            status=status.HTTP_200_OK,
        )


class WorkingPaperWorkflowActionView(APIView):
    """
    POST /audit/working-papers/<paper_id>/workflow-action/
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
        if not CanManageWorkingPaper().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_working_paper:manage required.')

    def post(self, request, paper_id):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        action_name = request.data.get('action')
        if not action_name:
            return Response(
                {"success": False, "error": {"message": "'action' is required", "code": "ACTION_REQUIRED"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = WorkingPaperService().advance_workflow_stage(
                paper_id=str(paper_id),
                action=action_name,
                actor_id=str(user_id),
                comment=request.data.get('comment', ''),
            )
        except ValueError as exc:
            return Response(
                {"success": False, "error": {"message": str(exc), "code": "WORKFLOW_ACTION_FAILED"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error executing workflow action for WorkingPaper %s: %s", paper_id, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to execute workflow action", "details": str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class WorkingPaperCancelWorkflowView(APIView):
    """
    POST /audit/working-papers/<paper_id>/cancel-workflow/
        Cancel the active workflow for a working paper.
        Matches corporate-service cancel_workflow endpoint pattern.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageWorkingPaper().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_working_paper:manage required.')

    def post(self, request, paper_id):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return Response(
                {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            WorkingPaperService().cancel_workflow_plan(
                paper_id=str(paper_id),
                actor_id=str(user_id),
                reason=request.data.get('reason', ''),
            )
        except ValueError as exc:
            return Response(
                {"success": False, "error": {"message": str(exc), "code": "CANCEL_WORKFLOW_FAILED"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error cancelling workflow for WorkingPaper %s: %s", paper_id, exc, exc_info=True)
            return Response(
                {"success": False, "error": {"message": "Failed to cancel workflow", "details": str(exc)}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"success": True, "data": {"status": "workflow_cancelled"}},
            status=status.HTTP_200_OK,
        )


# ─── Working Paper Evidence Views (DRS Integration) ──────────────────────────

class WorkingPaperEvidenceView(APIView):
    """Manage supporting evidence attachments on a working paper.

    Delegates file storage to Document Records Service (FIMS Principle 2).
    GRC stores only the DRS document UUIDs in ``evidence_document_ids``.

    GET    /working-papers/{paper_id}/evidence/                  — list
    POST   /working-papers/{paper_id}/evidence/                  — upload
    DELETE /working-papers/{paper_id}/evidence/{document_id}/    — detach
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanManageWorkingPaper().has_permission(request, self) or
                    CanReviewWorkingPaper().has_permission(request, self)):
                self.permission_denied(
                    request,
                    message='grc:audit_working_paper:manage or :review required.',
                )
        elif request.method in ('POST', 'DELETE'):
            if not CanManageWorkingPaper().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:audit_working_paper:manage required.',
                )

    @staticmethod
    def _get_auth_token(request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        return auth_header.removeprefix('Bearer ').strip() if auth_header.startswith('Bearer ') else None

    @staticmethod
    def _normalize_doc(doc: dict) -> dict:
        """Normalize DRS document fields to match EvidenceAttachment frontend type."""
        return {
            **doc,
            'document_id': doc.get('id', ''),
            'filename': doc.get('title') or doc.get('file_name') or doc.get('filename') or '',
            'upload_url': doc.get('download_url'),
            'uploaded_by': doc.get('created_by'),
        }

    # ── GET — list evidence ───────────────────────────────────────────
    def get(self, request, paper_id):
        """Return metadata for all evidence documents attached to this working paper."""
        try:
            paper = get_object_or_404(WorkingPaper, id=paper_id)
            doc_ids = paper.evidence_document_ids or []

            if not doc_ids:
                return Response({"success": True, "data": [], "meta": {"total": 0}})

            auth_token = self._get_auth_token(request)
            client = get_document_client(auth_token=auth_token)

            documents = []
            for did in doc_ids:
                try:
                    doc = client.get_document(str(did))
                    doc['download_url'] = client.get_download_url(str(did))
                    documents.append(self._normalize_doc(doc))
                except DocumentServiceError:
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
            logger.exception("Failed to retrieve working paper evidence")
            return server_error_response(
                message="Failed to retrieve working paper evidence",
                details=str(e) if settings.DEBUG else None,
            )

    # ── POST — upload evidence to DRS and attach UUID ─────────────────
    def post(self, request, paper_id):
        """Upload supporting evidence file to DRS and link to working paper.

        Accepts ``multipart/form-data`` with:
        - ``file``        — the evidence file (required)
        - ``title``       — document title (optional, defaults to filename)
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

            paper = get_object_or_404(WorkingPaper, id=paper_id)

            # Block uploads on approved working papers
            if paper.review_status == 'approved':
                return error_response(
                    message="Cannot add evidence to an approved working paper",
                    code="WORKING_PAPER_APPROVED",
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
                f"Supporting evidence for working paper: {paper.title} ({paper.reference_number})",
            )

            auth_token = self._get_auth_token(request)
            client = get_document_client(auth_token=auth_token)

            # Step 1: Create document + upload file to DRS
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
                        'working_paper_id': str(paper.id),
                        'engagement_id': str(paper.engagement_id),
                        'reference_number': paper.reference_number,
                        'service': 'grc-service',
                        'module': 'working_paper_evidence',
                    },
                    tags=['audit', 'evidence', 'working-paper', paper.reference_number],
                )
                new_doc_id = str(document['id'])
            except DocumentServiceError as e:
                logger.error(f"DRS upload failed for working paper {paper_id}: {e}")
                return error_response(
                    message="Failed to upload file to Document Records Service",
                    code="DOCUMENT_SERVICE_ERROR",
                    status_code=status.HTTP_502_BAD_GATEWAY,
                )

            # Step 2: Append DRS UUID to evidence_document_ids
            with transaction.atomic():
                paper = WorkingPaper.objects.select_for_update().get(id=paper_id)
                doc_ids = list(paper.evidence_document_ids or [])
                if new_doc_id not in doc_ids:
                    doc_ids.append(new_doc_id)
                paper.evidence_document_ids = doc_ids
                paper.save(update_fields=['evidence_document_ids'])

            logger.info(
                f"Evidence {new_doc_id} attached to working paper {paper_id} by user {user_id}"
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "document_id": new_doc_id,
                        "title": title,
                        "file_name": uploaded_file.name,
                        "working_paper_id": str(paper_id),
                        "total_evidence": len(doc_ids),
                    },
                    "message": "Evidence uploaded and attached successfully",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.exception("Failed to upload working paper evidence")
            return server_error_response(
                message="Failed to upload working paper evidence",
                details=str(e) if settings.DEBUG else None,
            )


class WorkingPaperEvidenceDetailView(APIView):
    """Detach a single evidence document from a working paper.

    DELETE /working-papers/{paper_id}/evidence/{document_id}/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageWorkingPaper().has_permission(request, self):
            self.permission_denied(
                request,
                message='grc:audit_working_paper:manage required.',
            )

    def delete(self, request, paper_id, document_id):
        """Remove a DRS document UUID from the working paper's evidence list.

        Does NOT delete the document from DRS — only detaches the reference.
        """
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated",
                    code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            paper = get_object_or_404(WorkingPaper, id=paper_id)

            if paper.review_status == 'approved':
                return error_response(
                    message="Cannot modify evidence on an approved working paper",
                    code="WORKING_PAPER_APPROVED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            doc_str = str(document_id)
            with transaction.atomic():
                paper = WorkingPaper.objects.select_for_update().get(id=paper_id)
                doc_ids = list(paper.evidence_document_ids or [])
                if doc_str not in doc_ids:
                    return error_response(
                        message="Document not found in evidence attachments",
                        code="EVIDENCE_NOT_FOUND",
                        status_code=status.HTTP_404_NOT_FOUND,
                    )
                doc_ids.remove(doc_str)
                paper.evidence_document_ids = doc_ids
                paper.save(update_fields=['evidence_document_ids'])

            logger.info(
                f"Evidence {document_id} detached from working paper {paper_id} by user {user_id}"
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "document_id": doc_str,
                        "working_paper_id": str(paper_id),
                        "total_evidence": len(doc_ids),
                    },
                    "message": "Evidence detached successfully",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Failed to detach working paper evidence")
            return server_error_response(
                message="Failed to detach working paper evidence",
                details=str(e) if settings.DEBUG else None,
            )
