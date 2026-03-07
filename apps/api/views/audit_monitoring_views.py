from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditRecommendation, ImplementationMonitoring
from apps.api.serializers.audit_serializers import AuditRecommendationSerializer
from apps.api.permissions_jwt import CanViewAuditDashboard, CanUpdateAuditMonitoring

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    server_error_response,
)


class AuditMonitoringListView(APIView):
    """Read-only list of audit monitoring data (recommendations with implementation status)"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewAuditDashboard().has_permission(request, self) or
                CanUpdateAuditMonitoring().has_permission(request, self)):
            self.permission_denied(
                request,
                message='grc:audit_dashboard:view or grc:audit_monitoring:update required.',
            )

    def get(self, request):
        """Get all audit recommendations with monitoring data, with pagination"""
        try:
            # Query active audit recommendations with related monitoring data
            queryset = AuditRecommendation.objects.select_related(
                'finding', 
                'finding__engagement',
                'finding__fiscal_year',
                'finding__quarter',
                'finding__severity'
            ).prefetch_related(
                'monitoring'  # One-to-one reverse relationship (related_name='monitoring')
            ).filter(is_active=True)
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-created_at',
                allowed_fields=['created_at', 'target_date', 'status', 'priority']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditRecommendationSerializer(page_data["queryset"], many=True)
            
            # Augment data with monitoring information
            monitoring_data = []
            for rec_data, rec_obj in zip(serializer.data, page_data["queryset"]):
                monitoring_info = rec_data.copy()
                
                # Add implementation monitoring data if exists
                try:
                    monitoring = rec_obj.monitoring
                    monitoring_info.update({
                        'implementation_progress': float(monitoring.latest_progress),
                        'last_review_date': monitoring.last_review_date,
                        'next_review_date': monitoring.next_review_date,
                        'reviewed_by': monitoring.reviewed_by,
                    })
                except ImplementationMonitoring.DoesNotExist:
                    monitoring_info.update({
                        'implementation_progress': 0.0,
                        'last_review_date': None,
                        'next_review_date': None,
                        'reviewed_by': None,
                    })
                
                monitoring_data.append(monitoring_info)
            
            return paginated_list_response(
                items=monitoring_data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_monitoring",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit monitoring data")
            return server_error_response(
                message="Failed to retrieve audit monitoring data",
                details=str(e) if settings.DEBUG else None,
            )
