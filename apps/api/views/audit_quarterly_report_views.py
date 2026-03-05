"""
Quarterly Audit Report CRUD Views for GRC Service.

Provides full CRUD + workflow operations for quarterly internal audit
progress reports following FIMS patterns.

Quarterly reports consolidate all AuditReport instances within a fiscal
quarter and are submitted to the Commission via a 6-stage workflow.

SRS 1.8.3 — Quarterly reporting obligation.

Reference format  : QTR-{FY}-Q{num}-{seq:03d}  e.g. QTR-2024/2025-Q3-001
Workflow          : draft → cia_review → management_review → committee_review
                    → improvement_required → approved → submitted_to_commission
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import (
    QuarterlyAuditReport, AuditReport, FiscalYear, Quarter,
)
from apps.api.serializers.audit_serializers import (
    QuarterlyAuditReportSerializer,
    QuarterlyAuditReportListSerializer,
)
from apps.api.permissions_jwt import (
    CanManageQuarterlyReport,
    CanApproveQuarterlyReport,
)
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import QUARTERLY_REPORT_EVENTS

from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    created_response,
    error_response,
    not_found_response,
    server_error_response,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status transition map — SRS §1.8.3 workflow
# ---------------------------------------------------------------------------

VALID_QUARTERLY_TRANSITIONS = {
    'draft':                   ['cia_review'],
    'cia_review':              ['management_review', 'draft'],
    'management_review':       ['committee_review', 'improvement_required'],
    'committee_review':        ['approved', 'improvement_required'],
    'improvement_required':    ['cia_review'],
    'approved':                ['submitted_to_commission'],
    'submitted_to_commission': [],
}

LOCKED_STATUSES = ('submitted_to_commission',)
APPROVAL_REQUIRED_STATUSES = ('approved', 'submitted_to_commission')


# ---------------------------------------------------------------------------
# 1. QuarterlyReportListCreateView
# ---------------------------------------------------------------------------

class QuarterlyReportListCreateView(APIView):
    """
    GET  /api/v1/grc/audit/quarterly-reports/   — List quarterly reports
    POST /api/v1/grc/audit/quarterly-reports/   — Create a quarterly report
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageQuarterlyReport().has_permission(request, self):
            self.permission_denied(request, message='grc:quarterly_report:manage permission required.')

    def get(self, request):
        try:
            fiscal_year_id = request.query_params.get('fiscal_year')
            quarter_id     = request.query_params.get('quarter')
            status_filter  = request.query_params.get('status')
            is_active      = request.query_params.get('is_active')

            queryset = QuarterlyAuditReport.objects.select_related(
                'fiscal_year', 'quarter'
            ).prefetch_related('engagement_reports').all()

            if fiscal_year_id:
                queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
            if quarter_id:
                queryset = queryset.filter(quarter_id=quarter_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request,
                default='-reporting_period_end',
                allowed_fields=['reporting_period_end', 'reporting_period_start', 'created_at', 'status'],
            )
            queryset = queryset.order_by(ordering)

            page_data  = paginate_queryset(queryset, request)
            serializer = QuarterlyAuditReportListSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='quarterly_audit_report',
            )

        except Exception as e:
            logger.exception('Failed to retrieve quarterly audit reports')
            return server_error_response(message='Failed to retrieve quarterly audit reports', details=str(e) if settings.DEBUG else None)

    def post(self, request):
        try:
            serializer = QuarterlyAuditReportSerializer(data=request.data)

            if not serializer.is_valid():
                return Response({'success': False, 'error': {'message': 'Validation failed', 'details': serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)

            fiscal_year_id   = serializer.validated_data['fiscal_year_id']
            quarter_id       = serializer.validated_data['quarter_id']
            reference_number = serializer.validated_data.get('reference_number', '').strip()

            fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)
            quarter     = get_object_or_404(Quarter, id=quarter_id)

            if quarter.fiscal_year_id != fiscal_year.id:
                return Response({'success': False, 'error': {'message': f"Quarter '{quarter.name}' does not belong to fiscal year '{fiscal_year.year_code}'.", 'code': 'QUARTER_FISCAL_YEAR_MISMATCH'}}, status=status.HTTP_400_BAD_REQUEST)

            if QuarterlyAuditReport.objects.filter(fiscal_year=fiscal_year, quarter=quarter).exists():
                return Response({'success': False, 'error': {'message': f"A quarterly report for {quarter.name} {fiscal_year.year_code} already exists.", 'code': 'DUPLICATE_QUARTERLY_REPORT'}}, status=status.HTTP_400_BAD_REQUEST)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response({'success': False, 'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'}}, status=status.HTTP_401_UNAUTHORIZED)

            # Auto-generate QTR-{FY}-Q{num}-{seq:03d}
            if not reference_number:
                count         = QuarterlyAuditReport.objects.count()
                fy_code       = fiscal_year.year_code.replace('/', '-')
                qnum          = getattr(quarter, 'quarter_number', quarter.name)
                reference_number = f"QTR-{fy_code}-Q{qnum}-{count + 1:03d}"
                serializer.validated_data['reference_number'] = reference_number

            serializer.validated_data['prepared_by'] = user_id

            with transaction.atomic():
                report = serializer.save(created_by=user_id)

            try:
                messaging_service.publish_audit_event(
                    event_type=QUARTERLY_REPORT_EVENTS['QUARTERLY_REPORT_CREATED'],
                    audit_data={'report_id': str(report.id), 'reference_number': report.reference_number, 'fiscal_year': fiscal_year.year_code, 'quarter': quarter.name, 'prepared_by': str(user_id), 'user_id': str(user_id)},
                )
            except Exception as event_error:
                logger.error(f'Error publishing quarterly_report.created event: {event_error}')

            return Response({'success': True, 'data': QuarterlyAuditReportSerializer(report, context={'request': request}).data, 'message': 'Quarterly audit report created successfully'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception('Failed to create quarterly audit report')
            return Response({'success': False, 'error': {'message': 'Failed to create quarterly audit report', 'details': str(e) if settings.DEBUG else None}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# 2. QuarterlyReportDetailView
# ---------------------------------------------------------------------------

class QuarterlyReportDetailView(APIView):
    """
    GET    /api/v1/grc/audit/quarterly-reports/<pk>/  — Retrieve
    PUT    /api/v1/grc/audit/quarterly-reports/<pk>/  — Full update
    PATCH  /api/v1/grc/audit/quarterly-reports/<pk>/  — Partial update
    DELETE /api/v1/grc/audit/quarterly-reports/<pk>/  — Soft-delete (draft only)
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageQuarterlyReport().has_permission(request, self):
            self.permission_denied(request, message='grc:quarterly_report:manage permission required.')

    def _get_report(self, pk):
        return get_object_or_404(
            QuarterlyAuditReport.objects.select_related('fiscal_year', 'quarter').prefetch_related('engagement_reports'),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            report = self._get_report(pk)
            return success_response(data=QuarterlyAuditReportSerializer(report, context={'request': request}).data)
        except Exception as e:
            logger.exception('Failed to retrieve quarterly audit report')
            return server_error_response(message='Failed to retrieve quarterly audit report', details=str(e) if settings.DEBUG else None)

    def _update(self, request, pk, partial=False):
        try:
            report = self._get_report(pk)

            if report.status in LOCKED_STATUSES:
                return Response({'success': False, 'error': {'message': f"Report '{report.reference_number}' is locked (submitted to commission).", 'code': 'REPORT_LOCKED'}}, status=status.HTTP_400_BAD_REQUEST)

            serializer = QuarterlyAuditReportSerializer(report, data=request.data, partial=partial, context={'request': request})
            if not serializer.is_valid():
                return Response({'success': False, 'error': {'message': 'Validation failed', 'details': serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)

            user_id = getattr(request.user, 'id', None)

            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            try:
                messaging_service.publish_audit_event(event_type=QUARTERLY_REPORT_EVENTS['QUARTERLY_REPORT_UPDATED'], audit_data={'report_id': str(updated.id), 'user_id': str(user_id), 'status': updated.status})
            except Exception as event_error:
                logger.error(f'Error publishing quarterly_report.updated event: {event_error}')

            return success_response(data=QuarterlyAuditReportSerializer(updated, context={'request': request}).data)

        except Exception as e:
            logger.exception('Failed to update quarterly audit report')
            return server_error_response(message='Failed to update quarterly audit report', details=str(e) if settings.DEBUG else None)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            report = self._get_report(pk)

            if report.status != 'draft':
                return Response({'success': False, 'error': {'message': f"Cannot delete report '{report.reference_number}': only draft reports may be deleted.", 'code': 'REPORT_NOT_DRAFT'}}, status=status.HTTP_400_BAD_REQUEST)

            report.is_active = False
            report.save(update_fields=['is_active'])

            return Response({'success': True, 'message': f"Quarterly report '{report.reference_number}' has been deactivated."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception('Failed to delete quarterly audit report')
            return server_error_response(message='Failed to delete quarterly audit report', details=str(e) if settings.DEBUG else None)


# ---------------------------------------------------------------------------
# 3. QuarterlyReportStatusUpdateView
# ---------------------------------------------------------------------------

class QuarterlyReportStatusUpdateView(APIView):
    """
    POST /api/v1/grc/audit/quarterly-reports/<pk>/update-status/

    Advances the report through the SRS-defined 6-stage workflow.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        has_manage  = CanManageQuarterlyReport().has_permission(request, self)
        has_approve = CanApproveQuarterlyReport().has_permission(request, self)
        if not (has_manage or has_approve):
            self.permission_denied(request, message='grc:quarterly_report:manage or grc:quarterly_report:approve required.')

    def post(self, request, pk):
        report     = get_object_or_404(QuarterlyAuditReport, pk=pk)
        new_status = request.data.get('status', '').strip()
        reason     = request.data.get('reason', '').strip()
        notes      = request.data.get('notes', '').strip()

        if not new_status:
            return Response({'success': False, 'error': {'message': "'status' is required.", 'code': 'MISSING_STATUS'}}, status=status.HTTP_400_BAD_REQUEST)

        allowed_next = VALID_QUARTERLY_TRANSITIONS.get(report.status, [])
        if new_status not in allowed_next:
            return Response({'success': False, 'error': {'message': f"Cannot transition from '{report.status}' to '{new_status}'. Allowed: {allowed_next or 'none (terminal)'}.", 'code': 'INVALID_STATUS_TRANSITION'}}, status=status.HTTP_400_BAD_REQUEST)

        # Approve / submit requires approval permission
        if new_status in APPROVAL_REQUIRED_STATUSES:
            if not CanApproveQuarterlyReport().has_permission(request, self):
                return Response({'success': False, 'error': {'message': f"Only users with grc:quarterly_report:approve can set status to '{new_status}'.", 'code': 'PERMISSION_DENIED'}}, status=status.HTTP_403_FORBIDDEN)

        # Business rules: require linked reports before management_review
        if new_status == 'management_review':
            if report.engagement_reports.count() == 0:
                return Response({'success': False, 'error': {'message': "At least one audit report must be linked before advancing to Management Review.", 'code': 'NO_REPORTS_LINKED'}}, status=status.HTTP_400_BAD_REQUEST)
            if not report.executive_summary.strip():
                return Response({'success': False, 'error': {'message': "Executive summary is required before advancing to Management Review.", 'code': 'EXECUTIVE_SUMMARY_REQUIRED'}}, status=status.HTTP_400_BAD_REQUEST)

        # submission_date required when submitting to commission
        if new_status == 'submitted_to_commission':
            if not request.data.get('submission_date') and not report.submission_date:
                return Response({'success': False, 'error': {'message': "'submission_date' is required when submitting to commission.", 'code': 'SUBMISSION_DATE_REQUIRED'}}, status=status.HTTP_400_BAD_REQUEST)

        user_id    = getattr(request.user, 'id', None)
        old_status = report.status
        update_fields = ['status']

        if new_status == 'management_review' and notes:
            report.management_notes = notes
            update_fields.append('management_notes')

        if new_status in ('committee_review', 'improvement_required') and notes:
            report.committee_notes = notes
            update_fields.append('committee_notes')

        if new_status == 'approved':
            report.approved_by   = user_id
            report.approval_date = timezone.now()
            update_fields.extend(['approved_by', 'approval_date'])
            if notes:
                report.committee_notes = notes
                update_fields.append('committee_notes')

        if new_status == 'submitted_to_commission':
            sub_date = request.data.get('submission_date')
            if sub_date:
                report.submission_date = sub_date
                update_fields.append('submission_date')
            sub_to = request.data.get('submitted_to', '').strip()
            if sub_to:
                report.submitted_to = sub_to
                update_fields.append('submitted_to')

        report.status = new_status
        report.save(update_fields=update_fields)

        try:
            event_map = {
                'approved':                QUARTERLY_REPORT_EVENTS['QUARTERLY_REPORT_APPROVED'],
                'submitted_to_commission': QUARTERLY_REPORT_EVENTS['QUARTERLY_REPORT_SUBMITTED'],
            }
            messaging_service.publish_audit_event(
                event_type=event_map.get(new_status, QUARTERLY_REPORT_EVENTS['QUARTERLY_REPORT_UPDATED']),
                audit_data={'report_id': str(report.id), 'old_status': old_status, 'new_status': new_status, 'reason': reason, 'user_id': str(user_id)},
            )
        except Exception as event_error:
            logger.error(f'Error publishing quarterly_report status event: {event_error}')

        return Response({'success': True, 'data': QuarterlyAuditReportSerializer(report, context={'request': request}).data, 'message': f"Report status updated to '{new_status}' successfully."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 4. QuarterlyReportConsolidateView  (SRS §1.8.3 — auto-gather approved reports)
# ---------------------------------------------------------------------------

class QuarterlyReportConsolidateView(APIView):
    """
    POST /api/v1/grc/audit/quarterly-reports/<pk>/consolidate/

    Auto-gathers all approved AuditReport objects whose engagement belongs to
    this quarterly report's fiscal quarter, computes aggregated statistics,
    and links them to this report.

    Optional body param: include_distributed=true  — also include 'distributed' reports.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageQuarterlyReport().has_permission(request, self):
            self.permission_denied(request, message='grc:quarterly_report:manage permission required.')

    def post(self, request, pk):
        report = get_object_or_404(QuarterlyAuditReport, pk=pk)

        if report.status in LOCKED_STATUSES:
            return Response({'success': False, 'error': {'message': f"Report '{report.reference_number}' is locked.", 'code': 'REPORT_LOCKED'}}, status=status.HTTP_400_BAD_REQUEST)

        include_distributed = (
            request.data.get('include_distributed') is True
            or str(request.data.get('include_distributed', '')).lower() == 'true'
        )

        eligible_statuses = ['approved']
        if include_distributed:
            eligible_statuses.append('distributed')

        # AuditEngagement → AuditPlan → FiscalYear (no direct quarter FK)
        # Use reporting period dates to scope engagements to the quarter
        audit_reports_qs = AuditReport.objects.filter(
            engagement__audit_plan__fiscal_year=report.fiscal_year,
            engagement__planned_start_date__lte=report.reporting_period_end,
            engagement__planned_end_date__gte=report.reporting_period_start,
            status__in=eligible_statuses,
        ).select_related('engagement')

        if not audit_reports_qs.exists():
            return Response({
                'success': False,
                'error': {
                    'message': (
                        f"No approved audit reports found for {report.quarter} / "
                        f"{report.fiscal_year.year_code}. Ensure engagements have approved AuditReports."
                    ),
                    'code': 'NO_ELIGIBLE_REPORTS',
                },
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            report.engagement_reports.set(audit_reports_qs)

            total_engagements     = audit_reports_qs.values('engagement_id').distinct().count()
            total_findings        = 0
            critical_findings     = 0
            total_recommendations = 0

            for ar in audit_reports_qs:
                total_findings        += getattr(ar, 'total_findings', 0) or 0
                critical_findings     += getattr(ar, 'critical_findings', 0) or 0
                total_recommendations += getattr(ar, 'total_recommendations', 0) or 0

            # Fallback: count from related model objects
            if total_findings == 0:
                from apps.core.models import AuditFinding
                eids = list(audit_reports_qs.values_list('engagement_id', flat=True))
                total_findings    = AuditFinding.objects.filter(engagement_id__in=eids).count()
                critical_findings = AuditFinding.objects.filter(engagement_id__in=eids, severity__name__icontains='critical').count() \
                                  + AuditFinding.objects.filter(engagement_id__in=eids, severity__name__icontains='high').count()

            if total_recommendations == 0:
                from apps.core.models import AuditRecommendation
                eids = list(audit_reports_qs.values_list('engagement_id', flat=True))
                total_recommendations = AuditRecommendation.objects.filter(finding__engagement_id__in=eids).count()

            implementation_rate = Decimal('0.00')
            if total_recommendations > 0:
                try:
                    from apps.core.models import ImplementationMonitoring
                    eids = list(audit_reports_qs.values_list('engagement_id', flat=True))
                    implemented = ImplementationMonitoring.objects.filter(
                        recommendation__finding__engagement_id__in=eids,
                        implementation_status='implemented',
                    ).count()
                    implementation_rate = Decimal(str(round(implemented / total_recommendations * 100, 2)))
                except Exception:
                    pass

            report.total_engagements     = total_engagements
            report.total_findings        = total_findings
            report.critical_findings     = critical_findings
            report.total_recommendations = total_recommendations
            report.implementation_rate   = implementation_rate
            report.save(update_fields=[
                'total_engagements', 'total_findings', 'critical_findings',
                'total_recommendations', 'implementation_rate',
            ])

        linked_count = audit_reports_qs.count()
        return Response({
            'success': True,
            'data': QuarterlyAuditReportSerializer(report, context={'request': request}).data,
            'message': (
                f"Consolidated {linked_count} audit report(s) ({total_engagements} engagement(s)). "
                f"findings={total_findings}, critical={critical_findings}, "
                f"recommendations={total_recommendations}, rate={implementation_rate}%."
            ),
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 5. QuarterlyReportEngagementReportsView  (manual M2M management)
# ---------------------------------------------------------------------------

class QuarterlyReportEngagementReportsView(APIView):
    """
    POST   /api/v1/grc/audit/quarterly-reports/<pk>/engagement-reports/
           Body: {"report_ids": ["uuid1", "uuid2"]}
           Manually link AuditReport objects to this quarterly report.

    DELETE /api/v1/grc/audit/quarterly-reports/<pk>/engagement-reports/
           Body: {"report_ids": ["uuid1"]}
           Manually unlink AuditReport objects from this quarterly report.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageQuarterlyReport().has_permission(request, self):
            self.permission_denied(request, message='grc:quarterly_report:manage permission required.')

    def _get_report(self, pk):
        return get_object_or_404(QuarterlyAuditReport, pk=pk)

    def post(self, request, pk):
        report = self._get_report(pk)
        if report.status in LOCKED_STATUSES:
            return Response({'success': False, 'error': {'message': f"Report '{report.reference_number}' is locked.", 'code': 'REPORT_LOCKED'}}, status=status.HTTP_400_BAD_REQUEST)

        report_ids = request.data.get('report_ids', [])
        if not report_ids:
            return Response({'success': False, 'error': {'message': "'report_ids' list is required.", 'code': 'MISSING_REPORT_IDS'}}, status=status.HTTP_400_BAD_REQUEST)

        audit_reports = AuditReport.objects.filter(id__in=report_ids)
        found_ids     = set(str(r.id) for r in audit_reports)
        missing_ids   = [i for i in report_ids if i not in found_ids]
        if missing_ids:
            return Response({'success': False, 'error': {'message': f"Audit reports not found: {missing_ids}", 'code': 'REPORTS_NOT_FOUND'}}, status=status.HTTP_400_BAD_REQUEST)

        report.engagement_reports.add(*audit_reports)
        return Response({'success': True, 'data': QuarterlyAuditReportSerializer(report, context={'request': request}).data, 'message': f"Added {len(audit_reports)} audit report(s) to the quarterly report."}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        report = self._get_report(pk)
        if report.status in LOCKED_STATUSES:
            return Response({'success': False, 'error': {'message': f"Report '{report.reference_number}' is locked.", 'code': 'REPORT_LOCKED'}}, status=status.HTTP_400_BAD_REQUEST)

        report_ids = request.data.get('report_ids', [])
        if not report_ids:
            return Response({'success': False, 'error': {'message': "'report_ids' list is required.", 'code': 'MISSING_REPORT_IDS'}}, status=status.HTTP_400_BAD_REQUEST)

        audit_reports = AuditReport.objects.filter(id__in=report_ids)
        report.engagement_reports.remove(*audit_reports)
        return Response({'success': True, 'data': QuarterlyAuditReportSerializer(report, context={'request': request}).data, 'message': "Removed audit report(s) from the quarterly report."}, status=status.HTTP_200_OK)
