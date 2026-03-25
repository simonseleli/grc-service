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
from apps.core.models.lookups import (
    RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
    NonConformanceType, ISOClause,
)
from apps.api.serializers.lookup_serializers import (
    FiscalYearSerializer, QuarterSerializer, AuditSeveritySerializer,
    FindingTypeSerializer, RiskRatingSerializer, AuditOpinionSerializer,
    RiskCategorySerializer, RiskLikelihoodSerializer, RiskImpactSerializer,
    RiskLevelSerializer, NonConformanceTypeSerializer, ISOClauseSerializer,
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

    Supported role_code values (all GRC roles — Audit, Risk Management, Legal):
      Internal Audit: chief_internal_auditor, internal_auditor, audit_committee,
                      management, auditee, director_general, commission
      Risk Management: rmqam, rmo, risk_champion, quality_auditor, lsm
      Legal: legal_manager, legal_officer, committee_secretary, committee_chair

    Returns a flat list of user objects: [{id, email, first_name, last_name}]
    Results are cached by the IAMClient for 5 minutes.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        from apps.api.permissions_jwt import IsGRCUser
        if not IsGRCUser().has_permission(request, self):
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
            # Internal Audit roles
            'chief_internal_auditor',
            'internal_auditor',
            'audit_committee',
            'management',
            'auditee',
            'director_general',
            'commission',
            # Risk Management roles
            'rmqam',
            'rmo',
            'risk_champion',
            'quality_auditor',
            'lsm',
            # Legal roles
            'legal_manager',
            'legal_officer',
            'committee_secretary',
            'committee_chair',
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


# ── Risk Management Lookup Views ───────────────────────────────────────────


class RiskLookupDataView(APIView):
    """Combined endpoint for all Risk Management lookup data"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        try:
            risk_categories = RiskCategory.objects.filter(is_active=True).order_by('sort_order')
            risk_likelihoods = RiskLikelihood.objects.filter(is_active=True).order_by('sort_order')
            risk_impacts = RiskImpact.objects.filter(is_active=True).order_by('sort_order')
            risk_levels = RiskLevel.objects.filter(is_active=True).order_by('sort_order')
            nc_types = NonConformanceType.objects.filter(is_active=True).order_by('sort_order')
            iso_clauses = ISOClause.objects.filter(is_active=True).order_by('sort_order', 'clause_number')

            response_data = {
                'risk_categories': RiskCategorySerializer(risk_categories, many=True).data,
                'risk_likelihoods': RiskLikelihoodSerializer(risk_likelihoods, many=True).data,
                'risk_impacts': RiskImpactSerializer(risk_impacts, many=True).data,
                'risk_levels': RiskLevelSerializer(risk_levels, many=True).data,
                'non_conformance_types': NonConformanceTypeSerializer(nc_types, many=True).data,
                'iso_clauses': ISOClauseSerializer(iso_clauses, many=True).data,
            }

            return success_response(
                data=response_data,
                meta={
                    "counts": {
                        "risk_categories": risk_categories.count(),
                        "risk_likelihoods": risk_likelihoods.count(),
                        "risk_impacts": risk_impacts.count(),
                        "risk_levels": risk_levels.count(),
                        "non_conformance_types": nc_types.count(),
                        "iso_clauses": iso_clauses.count(),
                    },
                },
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk lookup data")
            return server_error_response(
                message="Failed to retrieve risk lookup data",
                details=str(e) if settings.DEBUG else None,
            )


class RiskCategoryListView(APIView):
    """Read-only list endpoint for RiskCategory lookup"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        try:
            queryset = RiskCategory.objects.filter(is_active=True)
            ordering = get_ordering_param(request, default='sort_order', allowed_fields=['sort_order', 'name', 'code'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskCategorySerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
                resource="risk_category",
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk categories")
            return server_error_response(message="Failed to retrieve risk categories", details=str(e) if settings.DEBUG else None)


class RiskLikelihoodListView(APIView):
    """Read-only list endpoint for RiskLikelihood lookup"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        try:
            queryset = RiskLikelihood.objects.filter(is_active=True)
            ordering = get_ordering_param(request, default='sort_order', allowed_fields=['sort_order', 'name', 'numerical_value'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskLikelihoodSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
                resource="risk_likelihood",
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk likelihoods")
            return server_error_response(message="Failed to retrieve risk likelihoods", details=str(e) if settings.DEBUG else None)


class RiskImpactListView(APIView):
    """Read-only list endpoint for RiskImpact lookup"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        try:
            queryset = RiskImpact.objects.filter(is_active=True)
            ordering = get_ordering_param(request, default='sort_order', allowed_fields=['sort_order', 'name', 'numerical_value'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskImpactSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
                resource="risk_impact",
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk impacts")
            return server_error_response(message="Failed to retrieve risk impacts", details=str(e) if settings.DEBUG else None)


class RiskLevelListView(APIView):
    """Read-only list endpoint for RiskLevel lookup"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        try:
            queryset = RiskLevel.objects.filter(is_active=True)
            ordering = get_ordering_param(request, default='sort_order', allowed_fields=['sort_order', 'name', 'min_score'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskLevelSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
                resource="risk_level",
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk levels")
            return server_error_response(message="Failed to retrieve risk levels", details=str(e) if settings.DEBUG else None)


class NonConformanceTypeListView(APIView):
    """Read-only list endpoint for NonConformanceType lookup"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        try:
            queryset = NonConformanceType.objects.filter(is_active=True)
            ordering = get_ordering_param(request, default='sort_order', allowed_fields=['sort_order', 'name', 'code'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = NonConformanceTypeSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
                resource="non_conformance_type",
            )
        except Exception as e:
            logger.exception("Failed to retrieve non-conformance types")
            return server_error_response(message="Failed to retrieve non-conformance types", details=str(e) if settings.DEBUG else None)


class ISOClauseListView(APIView):
    """Read-only list endpoint for ISOClause lookup"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditPlan().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        try:
            queryset = ISOClause.objects.filter(is_active=True)
            ordering = get_ordering_param(request, default='sort_order,clause_number', allowed_fields=['sort_order', 'clause_number', 'title'])
            if ',' in ordering:
                ordering_fields = [f.strip() for f in ordering.split(',')]
                queryset = queryset.order_by(*ordering_fields)
            else:
                queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = ISOClauseSerializer(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
                resource="iso_clause",
            )
        except Exception as e:
            logger.exception("Failed to retrieve ISO clauses")
            return server_error_response(message="Failed to retrieve ISO clauses", details=str(e) if settings.DEBUG else None)