"""
Legal Module — Activity Log View (GAP-13)

Read-only paginated timeline of LegalAuditLog entries per entity.
  GET /legal/activity-log/<entity_type>/<entity_id>/
"""

import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import LegalAuditLog
from apps.api.serializers.legal_serializers import LegalAuditLogSerializer
from apps.api.permissions_jwt import CanViewLegalCase, HasAnyPermission
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, server_error_response,
)

logger = logging.getLogger(__name__)

ALLOWED_ENTITY_TYPES = {
    'case_defendant', 'case_plaintiff',
    'filing_defendant', 'filing_plaintiff',
    'hearing', 'hearing_report',
    'settlement_defendant', 'settlement_plaintiff',
    'judgment_defendant', 'judgment_plaintiff',
    'meeting', 'minutes',
    'governing_body', 'member',
    'litigation_directive', 'task_litigation',
    'legal_notice', 'public_decision',
}


class LegalActivityLogView(APIView):
    """
    GET /api/v1/grc/legal/activity-log/<entity_type>/<entity_id>/

    Returns a paginated, reverse-chronological list of audit log entries
    for a specific legal entity.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewLegalCase().has_permission(request, self):
            self.permission_denied(
                request, message="grc:legal_case:view required."
            )

    def get(self, request, entity_type, entity_id):
        try:
            if entity_type not in ALLOWED_ENTITY_TYPES:
                from apps.api.utils.response_helpers import error_response
                return error_response(
                    message=f"Invalid entity_type '{entity_type}'.",
                    code="INVALID_ENTITY_TYPE",
                    status_code=400,
                )

            queryset = LegalAuditLog.objects.filter(
                entity_type=entity_type,
                entity_id=entity_id,
            ).order_by('-created_at')

            page_data = paginate_queryset(queryset, request)
            serializer = LegalAuditLogSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='legal_audit_log',
            )
        except Exception as exc:
            logger.exception("Error fetching activity log")
            return server_error_response(str(exc))
