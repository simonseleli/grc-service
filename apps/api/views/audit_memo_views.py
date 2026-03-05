"""
Audit Memo CRUD Views for GRC Service (GAP 1 — SRS Req 10-14, 18)
Provides full CRUD + submit + workflow for Internal Audit Memos following FIMS patterns.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditMemo, AuditPlan, AuditableEntity
from apps.api.serializers.audit_serializers import AuditMemoSerializer, AuditMemoListSerializer
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_MEMO_EVENTS
from apps.api.permissions_jwt import CanViewAuditMemo, CanManageAuditMemo, CanApproveAuditMemo
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


def _generate_memo_reference(plan: AuditPlan) -> str:
    """Generate a unique memo reference number: MEMO-{plan_ref}-{seq}"""
    existing_count = AuditMemo.objects.filter(audit_plan=plan).count()
    seq = existing_count + 1
    return f"MEMO-{plan.reference_number}-{seq:03d}"


class AuditMemoListCreateView(APIView):
    """List all audit memos or create a new one."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewAuditMemo().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_memo:view required.')
        elif request.method == 'POST':
            if not CanManageAuditMemo().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_memo:manage required.')

    def get(self, request):
        """Get all audit memos with optional filtering and pagination."""
        try:
            plan_id = request.query_params.get('audit_plan')
            entity_id = request.query_params.get('auditable_entity')
            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')

            queryset = AuditMemo.objects.select_related(
                'audit_plan', 'audit_plan__fiscal_year',
                'auditable_entity', 'auditable_entity__audit_universe',
            ).all()

            if plan_id:
                queryset = queryset.filter(audit_plan_id=plan_id)
            if entity_id:
                queryset = queryset.filter(auditable_entity_id=entity_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request,
                default='-created_at',
                allowed_fields=['created_at', 'status', 'reference_number', 'timeline_start'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = AuditMemoListSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_memo",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit memos")
            return server_error_response(
                message="Failed to retrieve audit memos",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        """Create a new audit memo."""
        try:
            serializer = AuditMemoSerializer(data=request.data)
            if serializer.is_valid():
                plan_id = serializer.validated_data['audit_plan_id']
                entity_id = serializer.validated_data['auditable_entity_id']

                # Business guard: plan must be approved or under implementation
                plan = get_object_or_404(AuditPlan, id=plan_id)
                if plan.status not in ('approved', 'implementation'):
                    return error_response(
                        message="Cannot create memo for a plan that is not approved",
                        code="PLAN_NOT_APPROVED",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                # Verify entity exists
                get_object_or_404(AuditableEntity, id=entity_id)

                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return error_response(
                        message="User not authenticated",
                        code="AUTH_REQUIRED",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                    )

                with transaction.atomic():
                    reference = serializer.validated_data.get('reference_number') or _generate_memo_reference(plan)
                    prepared_by = serializer.validated_data.get('prepared_by', user_id)
                    memo = serializer.save(
                        created_by=user_id,
                        prepared_by=prepared_by,
                        reference_number=reference,
                    )

                # Publish domain event — best-effort
                try:
                    messaging_service.publish_audit_plan_event(
                        event_type=AUDIT_MEMO_EVENTS['MEMO_CREATED'],
                        plan_id=memo.audit_plan_id,
                        additional_data={
                            'memo_id': str(memo.id),
                            'created_by': str(user_id),
                        },
                    )
                except Exception as event_error:
                    logger.error("Error publishing memo created event: %s", event_error)

                return Response(
                    {
                        "success": True,
                        "data": AuditMemoSerializer(memo).data,
                        "message": "Audit memo created successfully",
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to create audit memo")
            return server_error_response(
                message="Failed to create audit memo",
                details=str(e) if settings.DEBUG else None,
            )


class AuditMemoDetailView(APIView):
    """Retrieve, update, or delete a single audit memo."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewAuditMemo().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_memo:view required.')
        else:
            if not CanManageAuditMemo().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_memo:manage required.')

    def get(self, request, pk):
        try:
            memo = AuditMemo.objects.select_related(
                'audit_plan', 'audit_plan__fiscal_year', 'audit_plan__audit_universe',
                'auditable_entity', 'auditable_entity__audit_universe',
            ).get(pk=pk)
            return success_response(data=AuditMemoSerializer(memo).data, resource="audit_memo")
        except AuditMemo.DoesNotExist:
            return not_found_response(resource="audit_memo")
        except Exception as e:
            logger.exception("Failed to retrieve audit memo %s", pk)
            return server_error_response(
                message="Failed to retrieve audit memo",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        try:
            memo = get_object_or_404(AuditMemo, pk=pk)
            if memo.status not in ('draft',):
                return error_response(
                    message=f"Only draft memos can be edited. Current status: '{memo.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = AuditMemoSerializer(memo, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                with transaction.atomic():
                    serializer.save(modified_by=user_id)
                return success_response(data=AuditMemoSerializer(memo).data, resource="audit_memo")
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to update audit memo %s", pk)
            return server_error_response(
                message="Failed to update audit memo",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            memo = get_object_or_404(AuditMemo, pk=pk)
            if memo.status != 'draft':
                return error_response(
                    message="Only draft memos can be deleted",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            memo.is_active = False
            memo.save(update_fields=['is_active'])
            return success_response(data={"id": str(pk)}, message="Audit memo soft-deleted")
        except Exception as e:
            logger.exception("Failed to delete audit memo %s", pk)
            return server_error_response(
                message="Failed to delete audit memo",
                details=str(e) if settings.DEBUG else None,
            )


class AuditMemoSubmitView(APIView):
    """Submit audit memo for CIA review via Work Orchestration Service."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditMemo().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_memo:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated",
                code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            memo = get_object_or_404(AuditMemo, pk=pk)

            if memo.status != 'draft':
                return error_response(
                    message=f"Only draft memos can be submitted. Current status: '{memo.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            if memo.workflow_plan_id:
                return conflict_response(
                    message="Memo approval workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.removeprefix('Bearer ').strip() or None

            with transaction.atomic():
                # Start workflow via Work Orchestration Service
                client = OrchestrationClient()
                context = memo.get_workflow_context()
                metadata = memo.get_workflow_metadata()

                result = client.start_workflow(
                    "grc.audit_memo_approval",
                    context,
                    str(user_id),
                    subject_ref=str(memo.id),
                    metadata=metadata,
                    stages=memo.get_workflow_stages(),
                    auth_token=auth_token,
                )

                if result and result.plan_id:
                    memo.workflow_plan_id = result.plan_id
                    memo.workflow_stage = result.current_stage_name or ""
                    memo.workflow_stage_id = result.current_stage_id or None
                    from django.utils import timezone
                    memo.workflow_started_at = timezone.now()
                    memo.status = 'cia_review'
                    memo.save(update_fields=[
                        'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
                        'workflow_started_at', 'status',
                    ])
                else:
                    logger.error("Failed to start workflow for AuditMemo %s", pk)

            # Publish domain event — best-effort
            try:
                messaging_service.publish_audit_plan_event(
                    event_type=AUDIT_MEMO_EVENTS['MEMO_SUBMITTED'],
                    plan_id=memo.audit_plan_id,
                    additional_data={
                        'memo_id': str(memo.id),
                        'submitted_by': str(user_id),
                        'workflow_plan_id': str(memo.workflow_plan_id) if memo.workflow_plan_id else None,
                    },
                )
            except Exception as event_error:
                logger.error("Error publishing memo submitted event: %s", event_error)

            return success_response(
                data=AuditMemoSerializer(memo).data,
                message="Audit memo submitted for approval via workflow",
            )
        except Exception as e:
            logger.exception("Error submitting AuditMemo %s for approval", pk)
            return server_error_response(
                message="Failed to submit audit memo for approval",
                details=str(e) if settings.DEBUG else None,
            )


class AuditMemoWorkflowStatusView(APIView):
    """Get current workflow status for an audit memo from WO Service."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            memo = get_object_or_404(AuditMemo, pk=pk)
            if not memo.workflow_plan_id:
                return error_response(
                    message="No workflow has been started for this memo",
                    code="NO_WORKFLOW",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            auth_token = auth_header.removeprefix('Bearer ').strip() or None

            client = OrchestrationClient()
            wo_status = client.get_plan_status(str(memo.workflow_plan_id), auth_token=auth_token)

            return success_response(data={
                "memo_id": str(memo.id),
                "workflow_plan_id": str(memo.workflow_plan_id),
                "workflow_stage": memo.workflow_stage,
                "memo_status": memo.status,
                "wo_status": wo_status,
            })
        except Exception as e:
            logger.exception("Error fetching workflow status for memo %s", pk)
            return server_error_response(
                message="Failed to get memo workflow status",
                details=str(e) if settings.DEBUG else None,
            )
