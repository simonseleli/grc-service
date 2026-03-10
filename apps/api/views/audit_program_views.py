"""
Audit Program Views for GRC Service (GAP 5 — SRS Req 22, 23)
CRUD + submit + workflow for Audit Programs (separate from engagement).
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

from apps.core.models import AuditProgram, AuditEngagement, RiskControlMatrix
from apps.api.serializers.audit_serializers import (
    AuditProgramSerializer, AuditProgramListSerializer,
)
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_PROGRAM_EVENTS
from apps.api.permissions_jwt import CanManageAuditProgram, CanApproveAuditProgram
from apps.infrastructure.external.orchestration_client import OrchestrationClient

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    error_response,
    not_found_response,
    validation_error_response,
    conflict_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


def _generate_program_reference(engagement: AuditEngagement) -> str:
    """Generate a unique program reference: PROG-{engagement_ref}"""
    return f"PROG-{engagement.reference_number}"


class AuditProgramListCreateView(APIView):
    """List all audit programs or create a new one."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanManageAuditProgram().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_program:manage required.')
        elif request.method == 'POST':
            if not CanManageAuditProgram().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_program:manage required.')

    def get(self, request):
        try:
            engagement_id = request.query_params.get('audit_engagement')
            status_filter = request.query_params.get('status')

            queryset = AuditProgram.objects.select_related(
                'audit_engagement', 'risk_control_matrix',
            ).all()

            if engagement_id:
                queryset = queryset.filter(audit_engagement_id=engagement_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status', 'reference_number'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = AuditProgramListSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_program",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit programs")
            return server_error_response(
                message="Failed to retrieve audit programs",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = AuditProgramSerializer(data=request.data)
            if serializer.is_valid():
                engagement_id = serializer.validated_data['audit_engagement_id']
                engagement = get_object_or_404(AuditEngagement, id=engagement_id)

                # Business guard: engagement must exist and be in planning
                if engagement.status != 'planning':
                    return error_response(
                        message="Audit program can only be created during the planning phase",
                        code="INVALID_ENGAGEMENT_STATUS",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                # One program per engagement
                if AuditProgram.objects.filter(audit_engagement=engagement).exists():
                    return error_response(
                        message="An audit program already exists for this engagement",
                        code="PROGRAM_EXISTS",
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
                    reference = serializer.validated_data.get('reference_number') or _generate_program_reference(engagement)
                    prepared_by = serializer.validated_data.get('prepared_by', user_id)

                    # Link RCM if provided
                    rcm_id = serializer.validated_data.get('risk_control_matrix_id')
                    rcm = None
                    if rcm_id:
                        rcm = get_object_or_404(RiskControlMatrix, id=rcm_id)

                    program = serializer.save(
                        created_by=user_id,
                        prepared_by=prepared_by,
                        reference_number=reference,
                        risk_control_matrix=rcm,
                    )

                try:
                    messaging_service.publish_audit_plan_event(
                        event_type=AUDIT_PROGRAM_EVENTS['PROGRAM_CREATED'],
                        plan_id=engagement.audit_plan_id,
                        additional_data={
                            'program_id': str(program.id),
                            'engagement_id': str(engagement.id),
                        },
                    )
                except Exception as event_error:
                    logger.error("Error publishing program created event: %s", event_error)

                return Response(
                    {
                        "success": True,
                        "data": AuditProgramSerializer(program).data,
                        "message": "Audit program created successfully",
                    },
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to create audit program")
            return server_error_response(
                message="Failed to create audit program",
                details=str(e) if settings.DEBUG else None,
            )


class AuditProgramDetailView(APIView):
    """Retrieve, update, or delete an audit program."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditProgram().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_program:manage required.')

    def get(self, request, pk):
        try:
            program = AuditProgram.objects.select_related(
                'audit_engagement', 'risk_control_matrix',
            ).get(pk=pk)
            return success_response(
                data=AuditProgramSerializer(program).data,
                resource="audit_program",
            )
        except AuditProgram.DoesNotExist:
            return not_found_response(resource="audit_program")

    def put(self, request, pk):
        try:
            program = get_object_or_404(AuditProgram, pk=pk)
            if program.status != 'draft':
                return error_response(
                    message="Only draft programs can be edited",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = AuditProgramSerializer(program, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                with transaction.atomic():
                    serializer.save(modified_by=user_id)
                return success_response(
                    data=AuditProgramSerializer(program).data,
                    resource="audit_program",
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to update audit program %s", pk)
            return server_error_response(
                message="Failed to update audit program",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            program = get_object_or_404(AuditProgram, pk=pk)
            if program.status != 'draft':
                return error_response(
                    message="Only draft programs can be deleted",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            program.is_active = False
            program.save(update_fields=['is_active'])
            return success_response(data={"id": str(pk)}, message="Audit program soft-deleted")
        except Exception as e:
            logger.exception("Failed to delete audit program %s", pk)
            return server_error_response(
                message="Failed to delete audit program",
                details=str(e) if settings.DEBUG else None,
            )


class AuditProgramSubmitView(APIView):
    """Submit audit program for IA → CIA approval via Work Orchestration Service."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditProgram().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_program:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated",
                code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            program = get_object_or_404(AuditProgram, pk=pk)

            if program.status != 'draft':
                return error_response(
                    message=f"Only draft programs can be submitted. Current status: '{program.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            if program.workflow_plan_id:
                return conflict_response(
                    message="Program approval workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.removeprefix('Bearer ').strip() or None

            with transaction.atomic():
                client = OrchestrationClient()
                context = program.get_workflow_context()
                metadata = program.get_workflow_metadata()

                result = client.start_workflow(
                    "grc.audit_program_approval",
                    context,
                    str(user_id),
                    subject_ref=str(program.id),
                    metadata=metadata,
                    stages=program.get_workflow_stages(),
                    auth_token=auth_token,
                )

                if result and result.plan_id:
                    program.workflow_plan_id = result.plan_id
                    program.workflow_stage = result.current_stage_name or ""
                    program.workflow_stage_id = result.current_stage_id or None
                    program.workflow_started_at = timezone.now()
                    program.status = 'under_review'
                    program.save(update_fields=[
                        'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
                        'workflow_started_at', 'status',
                    ])
                else:
                    logger.error("Failed to start workflow for AuditProgram %s", pk)

            try:
                messaging_service.publish_audit_plan_event(
                    event_type=AUDIT_PROGRAM_EVENTS['PROGRAM_SUBMITTED'],
                    plan_id=program.audit_engagement.audit_plan_id,
                    additional_data={
                        'program_id': str(program.id),
                        'submitted_by': str(user_id),
                    },
                )
            except Exception as event_error:
                logger.error("Error publishing program submitted event: %s", event_error)

            return success_response(
                data=AuditProgramSerializer(program).data,
                message="Audit program submitted for approval via workflow",
            )
        except Exception as e:
            logger.exception("Error submitting AuditProgram %s for approval", pk)
            return server_error_response(
                message="Failed to submit audit program for approval",
                details=str(e) if settings.DEBUG else None,
            )


class AuditProgramApproveView(APIView):
    """
    CIA approves or returns an Audit Program (direct approval endpoint).

    SRS Requirements: 23 — "CIA reviews and approves the draft audit program."
    Workflow: draft → (submit) → under_review → (approve) → approved
                                              → (return)  → draft

    POST body: { "action": "approve" | "return", "comments": "..." }
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanApproveAuditProgram().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_program:approve required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated",
                code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            program = get_object_or_404(AuditProgram, pk=pk)

            if program.status != 'under_review':
                return error_response(
                    message=f"Only programs under review can be approved or returned. Current status: '{program.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            action = request.data.get('action', 'approve')
            if action not in ('approve', 'return'):
                return error_response(
                    message="Invalid action. Use 'approve' or 'return'.",
                    code="INVALID_ACTION",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                if action == 'approve':
                    program.status = 'approved'
                    program.approved_by = user_id
                    program.approval_date = timezone.now()
                    program.save(update_fields=['status', 'approved_by', 'approval_date'])

                    # GAP 9 — DRS integration guide §26 Pattern 2:
                    # Delegate PDF stamping to DRS (CIA signature + QR code overlay).
                    # Per FIMS Principle 2: GRC must never overlay PDFs itself.
                    if program.document_id:
                        try:
                            from apps.infrastructure.external.document_service_client import DocumentServiceClient
                            doc_client = DocumentServiceClient(auth_token=None)
                            doc_client.generate_approved_stamp(
                                document_id=str(program.document_id),
                                approver_id=str(user_id),
                                entity_type='audit_program',
                                entity_id=str(program.id),
                                service_token=getattr(settings, 'SERVICE_TO_SERVICE_TOKEN', None),
                            )
                            # DRS stamps in-place (§9): GET /documents/{id}/download/ now
                            # serves the stamped PDF automatically. No URL change needed.
                            logger.info(
                                "GAP 9: DRS stamp triggered for AuditProgram %s by CIA %s",
                                pk, user_id,
                            )
                        except Exception as stamp_err:
                            # Best-effort: log but never block the approval
                            logger.error(
                                "GAP 9: DRS stamp failed for AuditProgram %s: %s",
                                pk, stamp_err,
                            )
                else:  # return
                    program.status = 'draft'
                    program.workflow_plan_id = None
                    program.workflow_stage = ''
                    program.workflow_stage_id = None
                    program.workflow_started_at = None
                    program.save(update_fields=[
                        'status', 'workflow_plan_id', 'workflow_stage',
                        'workflow_stage_id', 'workflow_started_at',
                    ])

            if action == 'approve':
                try:
                    messaging_service.publish_audit_plan_event(
                        event_type=AUDIT_PROGRAM_EVENTS['PROGRAM_APPROVED'],
                        plan_id=program.audit_engagement.audit_plan_id,
                        additional_data={
                            'program_id': str(program.id),
                            'engagement_id': str(program.audit_engagement_id),
                            'approved_by': str(user_id),
                        },
                    )
                except Exception as event_error:
                    logger.error("Error publishing program approved event: %s", event_error)

            message = (
                "Audit program approved successfully"
                if action == 'approve'
                else "Audit program returned to draft for revision"
            )
            return success_response(
                data=AuditProgramSerializer(program).data,
                message=message,
            )
        except Exception as e:
            logger.exception("Error processing approval for AuditProgram %s", pk)
            return server_error_response(
                message="Failed to process audit program approval",
                details=str(e) if settings.DEBUG else None,
            )


class AuditProgramWorkflowStatusView(APIView):
    """Get current workflow status for an audit program from WO Service."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            program = get_object_or_404(AuditProgram, pk=pk)
            if not program.workflow_plan_id:
                return error_response(
                    message="No workflow has been started for this program",
                    code="NO_WORKFLOW",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.removeprefix('Bearer ').strip() or None

            client = OrchestrationClient()
            wo_status = client.get_plan_status(str(program.workflow_plan_id), auth_token=auth_token)

            return success_response(data={
                "program_id": str(program.id),
                "workflow_plan_id": str(program.workflow_plan_id),
                "workflow_stage": program.workflow_stage,
                "program_status": program.status,
                "wo_status": wo_status,
            })
        except Exception as e:
            logger.exception("Error fetching workflow status for program %s", pk)
            return server_error_response(
                message="Failed to get program workflow status",
                details=str(e) if settings.DEBUG else None,
            )
