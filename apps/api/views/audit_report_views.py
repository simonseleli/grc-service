"""
Audit Report CRUD Views for GRC Service
Provides full CRUD operations for audit report management following FIMS patterns.

Covers SRS 1.8.3 Steps 20-24 and Requirements 35-38:
  - Prepare draft report with consolidated findings / risk scoring
  - CIA review, approval, and distribution workflow
  - Report locking when status progresses past draft
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
    AuditReport, AuditEngagement, AuditFinding, AuditRecommendation,
)
from apps.api.serializers.audit_serializers import AuditReportSerializer
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_REPORT_EVENTS
from apps.api.permissions_jwt import (
    CanViewAuditReport,
    CanApproveAuditReport,
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

# ---------------------------------------------------------------------------
# Status transition table
# ---------------------------------------------------------------------------
VALID_REPORT_TRANSITIONS = {
    'draft': ['under_review'],
    'under_review': ['approved', 'draft'],   # CIA can approve or return
    'approved': ['distributed'],             # Handled by distribute endpoint
    'distributed': [],                       # Terminal
}

# Statuses that block standard field edits
LOCKED_STATUSES = ('under_review', 'approved', 'distributed')


class AuditReportListCreateView(APIView):
    """
    GET  /api/v1/grc/audit/reports/   — List reports with pagination + filters
    POST /api/v1/grc/audit/reports/   — Create a report for an engagement
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewAuditReport().has_permission(request, self) or
                    CanApproveAuditReport().has_permission(request, self)):
                self.permission_denied(
                    request,
                    message='grc:audit_report:view or :approve required.'
                )
        elif request.method == 'POST':
            if not CanViewAuditReport().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:audit_report:view required to create reports.'
                )

    def get(self, request):
        """List all audit reports with optional filtering and pagination."""
        try:
            engagement_id  = request.query_params.get('engagement')
            status_filter  = request.query_params.get('status')
            report_type    = request.query_params.get('report_type')
            is_active      = request.query_params.get('is_active')

            queryset = AuditReport.objects.select_related(
                'engagement',
                'engagement__audit_plan',
                'engagement__auditable_entity',
                'opinion',
            ).all()

            if engagement_id:
                queryset = queryset.filter(engagement_id=engagement_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if report_type:
                queryset = queryset.filter(report_type=report_type)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request,
                default='-created_at',
                allowed_fields=['created_at', 'status', 'reference_number', 'report_type'],
            )
            queryset = queryset.order_by(ordering)

            page_data   = paginate_queryset(queryset, request)
            serializer  = AuditReportSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='audit_report',
            )

        except Exception as e:
            logger.exception('Failed to retrieve audit reports')
            return server_error_response(
                message='Failed to retrieve audit reports',
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        """Create a new audit report for an engagement."""
        try:
            serializer = AuditReportSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': 'Validation failed',
                            'details': serializer.errors,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            engagement_id    = serializer.validated_data['engagement_id']
            reference_number = serializer.validated_data.get('reference_number', '').strip()

            # --- Verify engagement exists and is in reporting/completed phase ----
            engagement = get_object_or_404(AuditEngagement, id=engagement_id)
            if engagement.status not in ('reporting', 'completed'):
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Cannot create report for engagement in "
                                f"'{engagement.status}' phase. "
                                "Engagement must be in 'reporting' or 'completed' status."
                            ),
                            'code': 'INVALID_ENGAGEMENT_PHASE',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Verify no report already exists (OneToOne) ----------------------
            if AuditReport.objects.filter(engagement=engagement).exists():
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': 'An audit report already exists for this engagement.',
                            'code': 'DUPLICATE_REPORT',
                        },
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # --- Require authenticated user --------------------------------------
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {
                        'success': False,
                        'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # --- Auto-generate reference number if not provided ------------------
            if not reference_number:
                count = AuditReport.objects.filter(
                    engagement__audit_plan=engagement.audit_plan
                ).count()
                reference_number = f"RPT-{engagement.reference_number}-{count + 1:03d}"
                serializer.validated_data['reference_number'] = reference_number

            # --- Set prepared_by from JWT user -----------------------------------
            serializer.validated_data['prepared_by'] = user_id

            # --- Auto-populate findings_summary from active findings -------------
            findings_qs = AuditFinding.objects.filter(
                engagement=engagement, is_active=True
            ).values('id', 'reference_number', 'title', 'status')
            # Attach severity name separately to avoid issues with FK being None
            findings_list = []
            for f in findings_qs:
                findings_list.append({
                    'id': str(f['id']),
                    'reference_number': f['reference_number'],
                    'title': f['title'],
                    'status': f['status'],
                })
            serializer.validated_data['findings_summary'] = findings_list

            # --- Auto-populate recommendations_summary --------------------------
            recs_qs = AuditRecommendation.objects.filter(
                finding__engagement=engagement, is_active=True
            ).values('id', 'reference_number', 'title', 'priority', 'status')
            serializer.validated_data['recommendations_summary'] = [
                {
                    'id': str(r['id']),
                    'reference_number': r['reference_number'],
                    'title': r['title'],
                    'priority': r['priority'],
                    'status': r['status'],
                }
                for r in recs_qs
            ]

            with transaction.atomic():
                report = serializer.save(created_by=user_id)

            # --- Publish Kafka event (best-effort) -------------------------------
            try:
                messaging_service.publish_audit_event(
                    event_type=AUDIT_REPORT_EVENTS['REPORT_GENERATED'],
                    audit_data={
                        'report_id': str(report.id),
                        'engagement_id': str(engagement.id),
                        'reference_number': report.reference_number,
                        'report_type': report.report_type,
                        'prepared_by': str(user_id),
                        'user_id': str(user_id),
                    },
                )
            except Exception as event_error:
                logger.error(f'Error publishing audit_report.created event: {event_error}')

            return Response(
                {
                    'success': True,
                    'data': AuditReportSerializer(
                        report,
                        context={'request': request}
                    ).data,
                    'message': 'Audit report created successfully',
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.exception('Failed to create audit report')
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': 'Failed to create audit report',
                        'details': str(e) if settings.DEBUG else None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuditReportDetailView(APIView):
    """
    GET   /api/v1/grc/audit/reports/{pk}/   — Get report detail
    PUT   /api/v1/grc/audit/reports/{pk}/   — Full update (draft only)
    PATCH /api/v1/grc/audit/reports/{pk}/   — Partial update (draft only)
    DELETE /api/v1/grc/audit/reports/{pk}/  — Soft delete
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewAuditReport().has_permission(request, self) or
                    CanApproveAuditReport().has_permission(request, self)):
                self.permission_denied(
                    request,
                    message='grc:audit_report:view or :approve required.'
                )
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanViewAuditReport().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:audit_report:view required.'
                )

    def _get_report(self, pk):
        return get_object_or_404(
            AuditReport.objects.select_related(
                'engagement',
                'engagement__audit_plan',
                'engagement__auditable_entity',
                'opinion',
            ),
            pk=pk,
        )

    def get(self, request, pk):
        """Get a specific audit report."""
        try:
            report = self._get_report(pk)
            return Response(
                {
                    'success': True,
                    'data': AuditReportSerializer(report).data,
                    'meta': {
                        'service': 'grc-service',
                        'resource': 'audit_report',
                        'version': 'v1.0',
                    },
                }
            )
        except Exception as e:
            logger.exception(f'Failed to retrieve audit report {pk}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': 'Failed to retrieve audit report',
                        'details': str(e) if settings.DEBUG else None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _check_editable(self, report, request):
        """
        Returns None if editable, or a Response with the lock error.
        CIA can still edit while under_review (they are the reviewer).
        """
        if report.status in LOCKED_STATUSES:
            # Exception: CIA (CanApproveAuditReport) may edit during under_review
            if (report.status == 'under_review' and
                    CanApproveAuditReport().has_permission(request, self)):
                return None
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': (
                            f"Report is locked in '{report.status}' status and cannot be edited."
                        ),
                        'code': 'REPORT_LOCKED',
                        'current_status': report.status,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def put(self, request, pk):
        """Full update of an audit report (draft only)."""
        try:
            report = self._get_report(pk)
            lock_response = self._check_editable(report, request)
            if lock_response:
                return lock_response

            serializer = AuditReportSerializer(report, data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        'success': False,
                        'error': {'message': 'Validation failed', 'details': serializer.errors},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                updated = serializer.save()

            return Response(
                {
                    'success': True,
                    'data': AuditReportSerializer(updated).data,
                    'message': 'Audit report updated successfully',
                }
            )

        except Exception as e:
            logger.exception(f'Failed to update audit report {pk}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': 'Failed to update audit report',
                        'details': str(e) if settings.DEBUG else None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request, pk):
        """Partial update of an audit report (draft only)."""
        try:
            report = self._get_report(pk)
            lock_response = self._check_editable(report, request)
            if lock_response:
                return lock_response

            serializer = AuditReportSerializer(report, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {
                        'success': False,
                        'error': {'message': 'Validation failed', 'details': serializer.errors},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                updated = serializer.save()

            return Response(
                {
                    'success': True,
                    'data': AuditReportSerializer(updated).data,
                    'message': 'Audit report updated successfully',
                }
            )

        except Exception as e:
            logger.exception(f'Failed to partially update audit report {pk}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': 'Failed to update audit report',
                        'details': str(e) if settings.DEBUG else None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, pk):
        """Soft-delete an audit report (blocked if approved or distributed)."""
        try:
            report = get_object_or_404(AuditReport, pk=pk)

            if report.status in ('approved', 'distributed'):
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Cannot delete a report with status '{report.status}'."
                            ),
                            'code': 'REPORT_LOCKED',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                report.is_active = False
                report.save(update_fields=['is_active'])

            return Response(
                {
                    'success': True,
                    'message': 'Audit report deleted successfully',
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception(f'Failed to delete audit report {pk}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': 'Failed to delete audit report',
                        'details': str(e) if settings.DEBUG else None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuditReportStatusUpdateView(APIView):
    """
    POST /api/v1/grc/audit/reports/{pk}/update-status/
    Body: { "status": "under_review" | "approved" | "draft" }

    Handles all status transitions except 'distributed' (use the distribute endpoint).
    Requires CanApproveAuditReport for the approved transition.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewAuditReport().has_permission(request, self) or
                CanApproveAuditReport().has_permission(request, self)):
            self.permission_denied(
                request,
                message='grc:audit_report:view or :approve required.'
            )

    def post(self, request, pk):
        """Transition the report to a new status."""
        try:
            report = get_object_or_404(
                AuditReport.objects.select_related('engagement', 'opinion'), pk=pk
            )

            new_status = request.data.get('status')

            if not new_status:
                return Response(
                    {
                        'success': False,
                        'error': {'message': "'status' field is required.", 'code': 'MISSING_STATUS'},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            allowed = VALID_REPORT_TRANSITIONS.get(report.status, [])
            if new_status not in allowed:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Cannot transition from '{report.status}' to '{new_status}'."
                            ),
                            'code': 'INVALID_STATUS_TRANSITION',
                            'current_status': report.status,
                            'allowed_transitions': allowed,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Approve transition requires CanApproveAuditReport (CIA) --------
            if new_status == 'approved':
                if not CanApproveAuditReport().has_permission(request, self):
                    self.permission_denied(
                        request,
                        message='grc:audit_report:approve required to approve reports.'
                    )

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {
                        'success': False,
                        'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            update_fields = ['status']

            # --- Per-transition side effects ------------------------------------
            if report.status == 'draft' and new_status == 'under_review':
                report.reviewed_by = user_id
                update_fields.append('reviewed_by')

            elif report.status == 'under_review' and new_status == 'approved':
                report.approved_by   = user_id
                report.approval_date = timezone.now()
                update_fields += ['approved_by', 'approval_date']

            elif report.status == 'under_review' and new_status == 'draft':
                # Return for revision — clear reviewer
                report.reviewed_by = None
                update_fields.append('reviewed_by')

            with transaction.atomic():
                report.status = new_status
                report.save(update_fields=update_fields)

            # --- Publish event on approval (best-effort) -----------------------
            if new_status == 'approved':
                try:
                    messaging_service.publish_audit_event(
                        event_type=AUDIT_REPORT_EVENTS['REPORT_APPROVED'],
                        audit_data={
                            'report_id': str(report.id),
                            'engagement_id': str(report.engagement_id),
                            'approved_by': str(user_id),
                            'user_id': str(user_id),
                        },
                    )
                except Exception as event_error:
                    logger.error(f'Error publishing report approved event: {event_error}')

            return Response(
                {
                    'success': True,
                    'data': AuditReportSerializer(report).data,
                    'message': f"Report status updated to '{new_status}' successfully",
                }
            )

        except Exception as e:
            logger.exception(f'Failed to update report status for {pk}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': 'Failed to update report status',
                        'details': str(e) if settings.DEBUG else None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuditReportDistributeView(APIView):
    """
    POST /api/v1/grc/audit/reports/{pk}/distribute/
    Body: { "distribution_list": [{"user_id": "uuid", "name": "...", "role": "..."}] }

    Marks the report as distributed to the specified recipients.
    Requires CanApproveAuditReport (CIA distributes).
    Report must be in 'approved' status.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanApproveAuditReport().has_permission(request, self):
            self.permission_denied(
                request,
                message='grc:audit_report:approve required to distribute reports.'
            )

    def post(self, request, pk):
        """Distribute an approved report to the given recipient list."""
        try:
            report = get_object_or_404(
                AuditReport.objects.select_related('engagement', 'opinion'), pk=pk
            )

            if report.status != 'approved':
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                "Report must be in 'approved' status before distribution. "
                                f"Current status: '{report.status}'."
                            ),
                            'code': 'INVALID_STATUS',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            distribution_list = request.data.get('distribution_list', [])
            if not isinstance(distribution_list, list):
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': "'distribution_list' must be a list.",
                            'code': 'INVALID_DISTRIBUTION_LIST',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {
                        'success': False,
                        'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                report.distribution_list = distribution_list
                report.distributed_at    = timezone.now()
                report.status            = 'distributed'
                report.report_type       = 'final'  # Distribution implies final
                report.save(update_fields=[
                    'distribution_list', 'distributed_at', 'status', 'report_type'
                ])

            # --- Publish event (best-effort) ------------------------------------
            try:
                messaging_service.publish_audit_event(
                    event_type=AUDIT_REPORT_EVENTS['REPORT_PUBLISHED'],
                    audit_data={
                        'report_id': str(report.id),
                        'engagement_id': str(report.engagement_id),
                        'distributed_by': str(user_id),
                        'recipient_count': len(distribution_list),
                        'user_id': str(user_id),
                    },
                )
            except Exception as event_error:
                logger.error(f'Error publishing report distributed event: {event_error}')

            return Response(
                {
                    'success': True,
                    'data': AuditReportSerializer(report).data,
                    'message': 'Audit report distributed successfully',
                }
            )

        except Exception as e:
            logger.exception(f'Failed to distribute audit report {pk}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': 'Failed to distribute audit report',
                        'details': str(e) if settings.DEBUG else None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
