"""
Risk Control Matrix Views for GRC Service (GAP 4 — SRS Req 22)
CRUD for RCM parent and nested RCM entries.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import RiskControlMatrix, RCMEntry, AuditEngagement, RiskRating
from apps.api.serializers.audit_serializers import (
    RiskControlMatrixSerializer, RCMEntrySerializer,
)
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import RCM_EVENTS
from apps.api.permissions_jwt import CanManageRCM, CanApproveRCM

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    error_response,
    not_found_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


class RCMListCreateView(APIView):
    """List all RCMs or create a new one."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRCM().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_rcm:manage required.')

    def get(self, request):
        try:
            engagement_id = request.query_params.get('audit_engagement')
            status_filter = request.query_params.get('status')

            queryset = RiskControlMatrix.objects.select_related('audit_engagement').all()

            if engagement_id:
                queryset = queryset.filter(audit_engagement_id=engagement_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = RiskControlMatrixSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="risk_control_matrix",
            )
        except Exception as e:
            logger.exception("Failed to retrieve RCMs")
            return server_error_response(
                message="Failed to retrieve risk control matrices",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = RiskControlMatrixSerializer(data=request.data)
            if serializer.is_valid():
                engagement_id = serializer.validated_data['audit_engagement_id']
                engagement = get_object_or_404(AuditEngagement, id=engagement_id)

                # Business guard: engagement must be in planning phase
                if engagement.status != 'planning':
                    return error_response(
                        message="RCM can only be created during the planning phase",
                        code="INVALID_ENGAGEMENT_STATUS",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                # One RCM per engagement
                if RiskControlMatrix.objects.filter(audit_engagement=engagement).exists():
                    return error_response(
                        message="An RCM already exists for this engagement",
                        code="RCM_EXISTS",
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
                    prepared_by = serializer.validated_data.get('prepared_by', user_id)
                    rcm = serializer.save(created_by=user_id, prepared_by=prepared_by)

                try:
                    messaging_service.publish_audit_plan_event(
                        event_type=RCM_EVENTS['RCM_CREATED'],
                        plan_id=engagement.audit_plan_id,
                        additional_data={
                            'rcm_id': str(rcm.id),
                            'engagement_id': str(engagement.id),
                        },
                    )
                except Exception as event_error:
                    logger.error("Error publishing RCM created event: %s", event_error)

                return Response(
                    {
                        "success": True,
                        "data": RiskControlMatrixSerializer(rcm).data,
                        "message": "Risk Control Matrix created successfully",
                    },
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to create RCM")
            return server_error_response(
                message="Failed to create risk control matrix",
                details=str(e) if settings.DEBUG else None,
            )


class RCMDetailView(APIView):
    """Retrieve, update, or delete an RCM."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRCM().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_rcm:manage required.')

    def get(self, request, pk):
        try:
            rcm = RiskControlMatrix.objects.select_related(
                'audit_engagement',
            ).prefetch_related(
                'entries', 'entries__risk_rating',
            ).get(pk=pk)
            return success_response(
                data=RiskControlMatrixSerializer(rcm).data,
                resource="risk_control_matrix",
            )
        except RiskControlMatrix.DoesNotExist:
            return not_found_response(resource="risk_control_matrix")

    def put(self, request, pk):
        try:
            rcm = get_object_or_404(RiskControlMatrix, pk=pk)
            if rcm.status not in ('draft',):
                return error_response(
                    message="Only draft RCMs can be edited",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = RiskControlMatrixSerializer(rcm, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                with transaction.atomic():
                    serializer.save(modified_by=user_id)
                return success_response(
                    data=RiskControlMatrixSerializer(rcm).data,
                    resource="risk_control_matrix",
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to update RCM %s", pk)
            return server_error_response(
                message="Failed to update risk control matrix",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            rcm = get_object_or_404(RiskControlMatrix, pk=pk)
            if rcm.status != 'draft':
                return error_response(
                    message="Only draft RCMs can be deleted",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            rcm.is_active = False
            rcm.save(update_fields=['is_active'])
            return success_response(data={"id": str(pk)}, message="RCM soft-deleted")
        except Exception as e:
            logger.exception("Failed to delete RCM %s", pk)
            return server_error_response(
                message="Failed to delete risk control matrix",
                details=str(e) if settings.DEBUG else None,
            )


class RCMSubmitView(APIView):
    """Submit an RCM for CIA approval."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRCM().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_rcm:manage required.')

    def post(self, request, pk):
        try:
            rcm = get_object_or_404(RiskControlMatrix, pk=pk)
            if rcm.status != 'draft':
                return error_response(
                    message="Only draft RCMs can be submitted for approval",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Must have at least one entry
            if rcm.entries.count() == 0:
                return error_response(
                    message="RCM must have at least one entry before submission",
                    code="NO_ENTRIES",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                rcm.status = 'submitted'
                rcm.save(update_fields=['status'])

            try:
                messaging_service.publish_audit_plan_event(
                    event_type=RCM_EVENTS['RCM_SUBMITTED'],
                    plan_id=rcm.audit_engagement.audit_plan_id,
                    additional_data={
                        'rcm_id': str(rcm.id),
                        'engagement_id': str(rcm.audit_engagement_id),
                    },
                )
            except Exception as event_error:
                logger.error("Error publishing RCM submitted event: %s", event_error)

            return success_response(
                data=RiskControlMatrixSerializer(rcm).data,
                message="RCM submitted for approval",
            )
        except Exception as e:
            logger.exception("Error submitting RCM %s", pk)
            return server_error_response(
                message="Failed to submit RCM for approval",
                details=str(e) if settings.DEBUG else None,
            )


class RCMApproveView(APIView):
    """CIA approves or returns an RCM."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanApproveRCM().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_rcm:approve required.')

    def post(self, request, pk):
        try:
            rcm = get_object_or_404(RiskControlMatrix, pk=pk)
            if rcm.status != 'submitted':
                return error_response(
                    message="Only submitted RCMs can be approved",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            action = request.data.get('action', 'approve')
            with transaction.atomic():
                if action == 'approve':
                    rcm.status = 'approved'
                elif action == 'return':
                    rcm.status = 'draft'
                else:
                    return error_response(
                        message="Invalid action. Use 'approve' or 'return'",
                        code="INVALID_ACTION",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                rcm.save(update_fields=['status'])

            if action == 'approve':
                try:
                    messaging_service.publish_audit_plan_event(
                        event_type=RCM_EVENTS['RCM_APPROVED'],
                        plan_id=rcm.audit_engagement.audit_plan_id,
                        additional_data={
                            'rcm_id': str(rcm.id),
                            'engagement_id': str(rcm.audit_engagement_id),
                        },
                    )
                except Exception as event_error:
                    logger.error("Error publishing RCM approved event: %s", event_error)

            return success_response(
                data=RiskControlMatrixSerializer(rcm).data,
                message=f"RCM {'approved' if action == 'approve' else 'returned to draft'}",
            )
        except Exception as e:
            logger.exception("Error approving RCM %s", pk)
            return server_error_response(
                message="Failed to process RCM approval",
                details=str(e) if settings.DEBUG else None,
            )


# ── RCM Entry CRUD ────────────────────────────────────────────────────────────

class RCMEntryListCreateView(APIView):
    """List entries for an RCM or add new entries."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRCM().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_rcm:manage required.')

    def get(self, request, rcm_id):
        try:
            rcm = get_object_or_404(RiskControlMatrix, pk=rcm_id)
            entries = RCMEntry.objects.filter(
                risk_control_matrix=rcm,
            ).select_related('risk_rating').order_by('order')

            serializer = RCMEntrySerializer(entries, many=True)
            return success_response(data=serializer.data)
        except Exception as e:
            logger.exception("Failed to retrieve RCM entries for %s", rcm_id)
            return server_error_response(
                message="Failed to retrieve RCM entries",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request, rcm_id):
        try:
            rcm = get_object_or_404(RiskControlMatrix, pk=rcm_id)
            if rcm.status != 'draft':
                return error_response(
                    message="Entries can only be added to draft RCMs",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated",
                    code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            serializer = RCMEntrySerializer(data=request.data)
            if serializer.is_valid():
                risk_rating_id = request.data.get('risk_rating_id')
                with transaction.atomic():
                    entry = RCMEntry.objects.create(
                        risk_control_matrix=rcm,
                        order=serializer.validated_data.get('order', 0),
                        process_area=serializer.validated_data['process_area'],
                        risk_description=serializer.validated_data['risk_description'],
                        risk_rating_id=risk_rating_id,
                        control_description=serializer.validated_data['control_description'],
                        control_owner=serializer.validated_data['control_owner'],
                        control_type=serializer.validated_data['control_type'],
                        design_adequate=serializer.validated_data.get('design_adequate'),
                        design_assessment_notes=serializer.validated_data.get('design_assessment_notes', ''),
                        test_approach=serializer.validated_data.get('test_approach', 'effectiveness_test'),
                        priority=serializer.validated_data.get('priority', 'medium'),
                        in_scope=serializer.validated_data.get('in_scope', True),
                        exclusion_justification=serializer.validated_data.get('exclusion_justification', ''),
                        created_by=user_id,
                    )

                return Response(
                    {
                        "success": True,
                        "data": RCMEntrySerializer(entry).data,
                        "message": "RCM entry added",
                    },
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to create RCM entry for %s", rcm_id)
            return server_error_response(
                message="Failed to create RCM entry",
                details=str(e) if settings.DEBUG else None,
            )


class RCMEntryDetailView(APIView):
    """Retrieve, update, or delete a single RCM entry."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageRCM().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_rcm:manage required.')

    def get(self, request, pk):
        try:
            entry = RCMEntry.objects.select_related('risk_rating', 'risk_control_matrix').get(pk=pk)
            return success_response(data=RCMEntrySerializer(entry).data)
        except RCMEntry.DoesNotExist:
            return not_found_response(resource="rcm_entry")

    def put(self, request, pk):
        try:
            entry = get_object_or_404(RCMEntry, pk=pk)
            if entry.risk_control_matrix.status != 'draft':
                return error_response(
                    message="Entries can only be edited in draft RCMs",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = RCMEntrySerializer(entry, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                # Handle risk_rating_id from request data directly
                risk_rating_id = request.data.get('risk_rating_id')
                with transaction.atomic():
                    update_fields = {}
                    for field in ['order', 'process_area', 'risk_description',
                                  'control_description', 'control_owner', 'control_type',
                                  'design_adequate', 'design_assessment_notes',
                                  'test_approach', 'priority', 'in_scope',
                                  'exclusion_justification']:
                        if field in request.data:
                            setattr(entry, field, request.data[field])
                    if risk_rating_id:
                        entry.risk_rating_id = risk_rating_id
                    entry.modified_by = user_id
                    entry.save()
                return success_response(data=RCMEntrySerializer(entry).data)
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to update RCM entry %s", pk)
            return server_error_response(
                message="Failed to update RCM entry",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            entry = get_object_or_404(RCMEntry, pk=pk)
            if entry.risk_control_matrix.status != 'draft':
                return error_response(
                    message="Entries can only be deleted from draft RCMs",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            entry.delete()
            return success_response(data={"id": str(pk)}, message="RCM entry deleted")
        except Exception as e:
            logger.exception("Failed to delete RCM entry %s", pk)
            return server_error_response(
                message="Failed to delete RCM entry",
                details=str(e) if settings.DEBUG else None,
            )
