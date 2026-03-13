"""
Views for GRC Service Lookup Tables
Provides CRUD operations for configurable lookup values
"""

import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import (
    FiscalYear, Quarter, AuditSeverity, FindingType, 
    RiskRating, AuditOpinion
)
from apps.api.serializers.lookup_serializers import (
    FiscalYearSerializer, QuarterSerializer, AuditSeveritySerializer,
    FindingTypeSerializer, RiskRatingSerializer, AuditOpinionSerializer
)
from apps.api.permissions_jwt import CanViewAuditPlan

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    server_error_response,
)


class LookupDataView(APIView):
    """Combined endpoint for all lookup table data"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all lookup table data in one response (combined endpoint, no pagination)"""
        try:
            # Fetch all active lookup data
            fiscal_years = FiscalYear.objects.filter(is_active=True).order_by('start_date')
            quarters = Quarter.objects.select_related('fiscal_year').filter(
                is_active=True
            ).order_by('fiscal_year__start_date', 'quarter_number')
            audit_severities = AuditSeverity.objects.filter(is_active=True).order_by('sort_order')
            finding_types = FindingType.objects.filter(is_active=True).order_by('category', 'name')
            risk_ratings = RiskRating.objects.filter(is_active=True).order_by('sort_order')
            audit_opinions = AuditOpinion.objects.filter(is_active=True).order_by('name')
            
            # Serialize data
            response_data = {
                'fiscal_years': FiscalYearSerializer(fiscal_years, many=True).data,
                'quarters': QuarterSerializer(quarters, many=True).data,
                'audit_severities': AuditSeveritySerializer(audit_severities, many=True).data,
                'finding_types': FindingTypeSerializer(finding_types, many=True).data,
                'risk_ratings': RiskRatingSerializer(risk_ratings, many=True).data,
                'audit_opinions': AuditOpinionSerializer(audit_opinions, many=True).data,
            }
            
            return success_response(
                data=response_data,
                meta={
                    "counts": {
                        "fiscal_years": fiscal_years.count(),
                        "quarters": quarters.count(),
                        "audit_severities": audit_severities.count(),
                        "finding_types": finding_types.count(),
                        "risk_ratings": risk_ratings.count(),
                        "audit_opinions": audit_opinions.count(),
                    },
                },
            )
        except Exception as e:
            logger.exception("Failed to retrieve lookup data")
            return server_error_response(
                message="Failed to retrieve lookup data",
                details=str(e) if settings.DEBUG else None,
            )


class FiscalYearListView(APIView):
    """CRUD operations for FiscalYear lookup table"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all active fiscal years with pagination"""
        try:
            queryset = FiscalYear.objects.filter(is_active=True)
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='start_date',
                allowed_fields=['start_date', 'end_date', 'name']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = FiscalYearSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="fiscal_year",
            )
        except Exception as e:
            logger.exception("Failed to retrieve fiscal years")
            return server_error_response(
                message="Failed to retrieve fiscal years",
                details=str(e) if settings.DEBUG else None,
            )


class QuarterListView(APIView):
    """CRUD operations for Quarter lookup table"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all active quarters with fiscal year data and pagination"""
        try:
            queryset = Quarter.objects.select_related('fiscal_year').filter(is_active=True)
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='fiscal_year__start_date,quarter_number',
                allowed_fields=['fiscal_year__start_date', 'quarter_number', 'start_date']
            )
            # Handle compound ordering
            if ',' in ordering:
                ordering_fields = [f.strip() for f in ordering.split(',')]
                queryset = queryset.order_by(*ordering_fields)
            else:
                queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = QuarterSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="quarter",
            )
        except Exception as e:
            logger.exception("Failed to retrieve quarters")
            return server_error_response(
                message="Failed to retrieve quarters",
                details=str(e) if settings.DEBUG else None,
            )


class AuditSeverityListView(APIView):
    """CRUD operations for AuditSeverity lookup table"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all active audit severity levels with pagination"""
        try:
            queryset = AuditSeverity.objects.filter(is_active=True)
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='sort_order',
                allowed_fields=['sort_order', 'name', 'code']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditSeveritySerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_severity",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit severity levels")
            return server_error_response(
                message="Failed to retrieve audit severity levels",
                details=str(e) if settings.DEBUG else None,
            )


class FindingTypeListView(APIView):
    """CRUD operations for FindingType lookup table"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all active finding types with pagination"""
        try:
            queryset = FindingType.objects.filter(is_active=True)
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='category,name',
                allowed_fields=['category', 'name', 'code']
            )
            # Handle compound ordering
            if ',' in ordering:
                ordering_fields = [f.strip() for f in ordering.split(',')]
                queryset = queryset.order_by(*ordering_fields)
            else:
                queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = FindingTypeSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="finding_type",
            )
        except Exception as e:
            logger.exception("Failed to retrieve finding types")
            return server_error_response(
                message="Failed to retrieve finding types",
                details=str(e) if settings.DEBUG else None,
            )


class RiskRatingListView(APIView):
    """CRUD operations for RiskRating lookup table"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all active risk ratings with pagination"""
        try:
            queryset = RiskRating.objects.filter(is_active=True)
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='sort_order',
                allowed_fields=['sort_order', 'name', 'code']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = RiskRatingSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="risk_rating",
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk ratings")
            return server_error_response(
                message="Failed to retrieve risk ratings",
                details=str(e) if settings.DEBUG else None,
            )


class GRCUsersByRoleView(APIView):
    """
    Proxy endpoint: returns IAM users that have a specific GRC role assigned.

    GET /audit/lookups/users/?role_code=<code>

    Supported role_code values (GRC roles only):
      - chief_internal_auditor
      - internal_auditor
      - audit_committee
      - management
      - auditee

    Returns a flat list of user objects: [{id, email, first_name, last_name}]
    Results are cached by the IAMClient for 5 minutes.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        role_code = request.query_params.get('role_code', '').strip()
        if not role_code:
            return Response(
                {'success': False, 'error': {'message': 'role_code query parameter is required', 'code': 'MISSING_PARAM'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only allow GRC role codes to prevent arbitrary IAM data exposure
        allowed_roles = {
            'chief_internal_auditor',
            'internal_auditor',
            'audit_committee',
            'management',
            'auditee',
        }
        if role_code not in allowed_roles:
            return Response(
                {'success': False, 'error': {'message': f'role_code must be one of: {sorted(allowed_roles)}', 'code': 'INVALID_ROLE_CODE'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.infrastructure.external.iam_client import IAMClient
            # Forward the caller's JWT so IAM can authenticate the request
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            token = auth_header.removeprefix('Bearer ').strip()
            iam = IAMClient()
            users = iam.get_users_by_role(role_code, token)
            return Response({'success': True, 'results': users, 'count': len(users)})
        except Exception as e:
            logger.exception("GRCUsersByRoleView: failed to fetch users from IAM")
            return server_error_response(
                message="Failed to fetch users by role",
                details=str(e) if settings.DEBUG else None,
            )


class AuditOpinionListView(APIView):
    """CRUD operations for AuditOpinion lookup table"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all active audit opinions with pagination"""
        try:
            queryset = AuditOpinion.objects.filter(is_active=True)
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='name',
                allowed_fields=['name', 'code']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = AuditOpinionSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="audit_opinion",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit opinions")
            return server_error_response(
                message="Failed to retrieve audit opinions",
                details=str(e) if settings.DEBUG else None,
            )