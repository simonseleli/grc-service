"""
Configuration Management Views for GRC Service
Provides CRUD operations for configurable lookup values with permission enforcement
"""

import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.core.models import (
    FiscalYear, Quarter, AuditSeverity, FindingType, 
    RiskRating, AuditOpinion
)
from apps.core.models.lookups import (
    RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
    NonConformanceType, ISOClause,
    RiskSector, StrategicObjective,
)
from apps.api.serializers.lookup_serializers import (
    FiscalYearSerializer, QuarterSerializer, AuditSeveritySerializer,
    FindingTypeSerializer, RiskRatingSerializer, AuditOpinionSerializer,
    RiskCategorySerializer, RiskLikelihoodSerializer, RiskImpactSerializer,
    RiskLevelSerializer, NonConformanceTypeSerializer, ISOClauseSerializer,
    RiskSectorSerializer, StrategicObjectiveSerializer,
)
from rest_framework.permissions import IsAuthenticated
from apps.api.permissions_jwt import (
    CanManageFiscalYear,
    CanManageAuditSeverity,
    CanManageFindingType,
    CanManageRiskRating,
    CanManageSystemConfig,
    CanViewAuditPlan,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    created_response,
    updated_response,
    deleted_response,
    error_response,
    not_found_response,
    validation_error_response,
    conflict_response,
    server_error_response,
)


class ConfigFiscalYearView(APIView):
    """Configuration management for Fiscal Years"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        # GET is read-only — any authenticated GRC user may list fiscal years (needed for dropdowns)
        # Write operations (POST/PUT/PATCH/DELETE) require the manage permission
        if request.method != 'GET' and not CanManageFiscalYear().has_permission(request, self):
            self.permission_denied(request, message='grc:config:fiscal_year:manage required.')

    def get(self, request):
        """Get all fiscal years (active and inactive) with pagination"""
        try:
            queryset = FiscalYear.objects.all()
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-start_date',
                allowed_fields=['start_date', 'end_date', 'name', 'year_code']
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
                resource="config_fiscal_year",
                permission_required="config:fiscal_year:manage",
            )
        except Exception as e:
            logger.exception("Failed to retrieve fiscal year configuration")
            return server_error_response(
                message="Failed to retrieve fiscal year configuration",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create new fiscal year"""
        try:
            serializer = FiscalYearSerializer(data=request.data)
            if serializer.is_valid():
                # Check for overlapping fiscal years
                start_date = serializer.validated_data['start_date']
                end_date = serializer.validated_data['end_date']
                
                overlapping = FiscalYear.objects.filter(
                    start_date__lte=end_date,
                    end_date__gte=start_date,
                    is_active=True
                ).exists()
                
                if overlapping:
                    return Response(
                        {
                            "success": False,
                            "error": {
                                "message": "Fiscal year dates overlap with existing active fiscal year",
                                "code": "FISCAL_YEAR_OVERLAP"
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                with transaction.atomic():
                    fiscal_year = serializer.save(
                        created_by=request.user.id if hasattr(request, 'user') else None
                    )
                    
                    # Automatically create quarters for this fiscal year
                    quarters_data = [
                        {
                            'quarter_number': 1,
                            'name': 'Q1',
                            'start_date': start_date,
                            'end_date': start_date.replace(month=9, day=30),
                        },
                        {
                            'quarter_number': 2,
                            'name': 'Q2',
                            'start_date': start_date.replace(month=10, day=1),
                            'end_date': start_date.replace(month=12, day=31),
                        },
                        {
                            'quarter_number': 3,
                            'name': 'Q3',
                            'start_date': end_date.replace(month=1, day=1),
                            'end_date': end_date.replace(month=3, day=31),
                        },
                        {
                            'quarter_number': 4,
                            'name': 'Q4',
                            'start_date': end_date.replace(month=4, day=1),
                            'end_date': end_date,
                        },
                    ]
                    
                    for quarter_data in quarters_data:
                        Quarter.objects.create(
                            fiscal_year=fiscal_year,
                            quarter_number=quarter_data['quarter_number'],
                            name=quarter_data['name'],
                            start_date=quarter_data['start_date'],
                            end_date=quarter_data['end_date'],
                            created_by=request.user.id if hasattr(request, 'user') else None
                        )
                
                return Response(
                    {
                        "success": True,
                        "data": FiscalYearSerializer(fiscal_year).data,
                        "message": "Fiscal year created successfully with quarters"
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid fiscal year data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to create fiscal year",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, fiscal_year_id):
        """Update fiscal year"""
        try:
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            serializer = FiscalYearSerializer(fiscal_year, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_fiscal_year = serializer.save(
                    modified_by=request.user.id if hasattr(request, 'user') else None
                )
                
                return Response(
                    {
                        "success": True,
                        "data": FiscalYearSerializer(updated_fiscal_year).data,
                        "message": "Fiscal year updated successfully"
                    }
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid fiscal year data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except FiscalYear.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Fiscal year not found",
                        "code": "FISCAL_YEAR_NOT_FOUND"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update fiscal year",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, fiscal_year_id):
        """Soft delete fiscal year (mark as inactive)"""
        try:
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            
            # Check if fiscal year is being used
            if hasattr(fiscal_year, 'audioplans') and fiscal_year.audioplans.exists():
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete fiscal year that is being used in audit plans",
                            "code": "FISCAL_YEAR_IN_USE"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            fiscal_year.is_active = False
            fiscal_year.modified_by = request.user.id if hasattr(request, 'user') else None
            fiscal_year.save()
            
            # Also deactivate associated quarters
            Quarter.objects.filter(fiscal_year=fiscal_year).update(is_active=False)
            
            return Response(
                {
                    "success": True,
                    "message": "Fiscal year deactivated successfully"
                }
            )
        except FiscalYear.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Fiscal year not found",
                        "code": "FISCAL_YEAR_NOT_FOUND"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to deactivate fiscal year",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfigQuarterView(APIView):
    """Configuration view for Quarters - read-only (created automatically with fiscal years)"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        # Quarters are read-only; any authenticated GRC user may list them
        if request.method != 'GET' and not CanManageFiscalYear().has_permission(request, self):
            self.permission_denied(request, message='grc:config:fiscal_year:manage required.')

    def get(self, request):
        """Get all quarters (active and inactive) with pagination"""
        try:
            queryset = Quarter.objects.select_related('fiscal_year').all()
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='-fiscal_year__start_date,quarter_number',
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
                resource="config_quarter",
                note="Quarters are automatically created with fiscal years",
            )
        except Exception as e:
            logger.exception("Failed to retrieve quarters")
            return server_error_response(
                message="Failed to retrieve quarters",
                details=str(e) if settings.DEBUG else None,
            )


class ConfigAuditSeverityView(APIView):
    """Configuration management for Audit Severities"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        # GET (read for dropdowns) is open to any authenticated GRC user
        # Write operations require the config manage permission (CIA only)
        if request.method != 'GET' and not CanManageAuditSeverity().has_permission(request, self):
            self.permission_denied(request, message='grc:config:audit_severity:manage required.')

    def get(self, request):
        """Get all audit severity levels with pagination"""
        try:
            queryset = AuditSeverity.objects.all()
            
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
                resource="config_audit_severity",
                permission_required="config:audit_severity:manage",
            )
        except Exception as e:
            logger.exception("Failed to retrieve audit severity configuration")
            return server_error_response(
                message="Failed to retrieve audit severity configuration",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create new audit severity level"""
        try:
            serializer = AuditSeveritySerializer(data=request.data)
            if serializer.is_valid():
                severity = serializer.save(
                    created_by=request.user.id if hasattr(request, 'user') else None
                )
                
                return Response(
                    {
                        "success": True,
                        "data": AuditSeveritySerializer(severity).data,
                        "message": "Audit severity created successfully"
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid audit severity data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to create audit severity",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, severity_id):
        """Update audit severity level"""
        try:
            severity = AuditSeverity.objects.get(id=severity_id)
            serializer = AuditSeveritySerializer(severity, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_severity = serializer.save(
                    modified_by=request.user.id if hasattr(request, 'user') else None
                )
                
                return Response(
                    {
                        "success": True,
                        "data": AuditSeveritySerializer(updated_severity).data,
                        "message": "Audit severity updated successfully"
                    }
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid audit severity data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except AuditSeverity.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Audit severity not found",
                        "code": "AUDIT_SEVERITY_NOT_FOUND"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update audit severity",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, severity_id):
        """Soft delete audit severity (mark as inactive)"""
        try:
            severity = AuditSeverity.objects.get(id=severity_id)
            
            # Check if severity is being used
            if hasattr(severity, 'auditfindings') and severity.auditfindings.exists():
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete audit severity that is being used in findings",
                            "code": "AUDIT_SEVERITY_IN_USE"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            severity.is_active = False
            severity.modified_by = request.user.id if hasattr(request, 'user') else None
            severity.save()
            
            return Response(
                {
                    "success": True,
                    "message": "Audit severity deactivated successfully"
                }
            )
        except AuditSeverity.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Audit severity not found",
                        "code": "AUDIT_SEVERITY_NOT_FOUND"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to deactivate audit severity",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfigFindingTypeView(APIView):
    """Configuration management for Finding Types"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        # GET (read for dropdowns) is open to any authenticated GRC user
        # Write operations require the config manage permission (CIA only)
        if request.method != 'GET' and not CanManageFindingType().has_permission(request, self):
            self.permission_denied(request, message='grc:config:finding_type:manage required.')

    def get(self, request):
        """Get all finding types with pagination"""
        try:
            queryset = FindingType.objects.all()
            
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
                resource="config_finding_type",
                permission_required="config:finding_type:manage",
            )
        except Exception as e:
            logger.exception("Failed to retrieve finding type configuration")
            return server_error_response(
                message="Failed to retrieve finding type configuration",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create new finding type"""
        try:
            serializer = FindingTypeSerializer(data=request.data)
            if serializer.is_valid():
                finding_type = serializer.save(
                    created_by=request.user.id if hasattr(request, 'user') else None
                )
                
                return Response(
                    {
                        "success": True,
                        "data": FindingTypeSerializer(finding_type).data,
                        "message": "Finding type created successfully"
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid finding type data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to create finding type",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, finding_type_id):
        """Update finding type"""
        try:
            finding_type = FindingType.objects.get(id=finding_type_id)
            serializer = FindingTypeSerializer(finding_type, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_finding_type = serializer.save(
                    modified_by=request.user.id if hasattr(request, 'user') else None
                )
                
                return Response(
                    {
                        "success": True,
                        "data": FindingTypeSerializer(updated_finding_type).data,
                        "message": "Finding type updated successfully"
                    }
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid finding type data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except FindingType.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Finding type not found",
                        "code": "FINDING_TYPE_NOT_FOUND"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update finding type",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, finding_type_id):
        """Soft delete finding type (mark as inactive)"""
        try:
            finding_type = FindingType.objects.get(id=finding_type_id)
            
            # Check if finding type is being used
            if hasattr(finding_type, 'auditfindings') and finding_type.auditfindings.exists():
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete finding type that is being used in findings",
                            "code": "FINDING_TYPE_IN_USE"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            finding_type.is_active = False
            finding_type.modified_by = request.user.id if hasattr(request, 'user') else None
            finding_type.save()
            
            return Response(
                {
                    "success": True,
                    "message": "Finding type deactivated successfully"
                }
            )
        except FindingType.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Finding type not found",
                        "code": "FINDING_TYPE_NOT_FOUND"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to deactivate finding type",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfigRiskRatingView(APIView):
    """Configuration management for Risk Ratings"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            # Write operations require the config manage permission (CIA only)
            if not CanManageRiskRating().has_permission(request, self):
                self.permission_denied(request, message='grc:config:risk_rating:manage required.')
        else:
            # GET (read for dropdowns) requires any valid GRC role
            if not CanViewAuditPlan().has_permission(request, self):
                self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all risk ratings with pagination"""
        try:
            queryset = RiskRating.objects.all()
            
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
                resource="config_risk_rating",
                permission_required="config:risk_rating:manage",
            )
        except Exception as e:
            logger.exception("Failed to retrieve risk rating configuration")
            return server_error_response(
                message="Failed to retrieve risk rating configuration",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """Create new risk rating"""
        try:
            serializer = RiskRatingSerializer(data=request.data)
            if serializer.is_valid():
                risk_rating = serializer.save(
                    created_by=request.user.id if hasattr(request, 'user') else None
                )
                
                return Response(
                    {
                        "success": True,
                        "data": RiskRatingSerializer(risk_rating).data,
                        "message": "Risk rating created successfully"
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid risk rating data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to create risk rating",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, risk_rating_id):
        """Update risk rating"""
        try:
            risk_rating = RiskRating.objects.get(id=risk_rating_id)
            serializer = RiskRatingSerializer(risk_rating, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_risk_rating = serializer.save(
                    modified_by=request.user.id if hasattr(request, 'user') else None
                )
                
                return Response(
                    {
                        "success": True,
                        "data": RiskRatingSerializer(updated_risk_rating).data,
                        "message": "Risk rating updated successfully"
                    }
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid risk rating data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except RiskRating.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Risk rating not found",
                        "code": "RISK_RATING_NOT_FOUND"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to update risk rating",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, risk_rating_id):
        """Soft delete risk rating (mark as inactive)"""
        try:
            risk_rating = RiskRating.objects.get(id=risk_rating_id)
            
            # Check if risk rating is being used
            if hasattr(risk_rating, 'auditfindings') and risk_rating.auditfindings.exists():
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Cannot delete risk rating that is being used in findings",
                            "code": "RISK_RATING_IN_USE"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            risk_rating.is_active = False
            risk_rating.modified_by = request.user.id if hasattr(request, 'user') else None
            risk_rating.save()
            
            return Response(
                {
                    "success": True,
                    "message": "Risk rating deactivated successfully"
                }
            )
        except RiskRating.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Risk rating not found",
                        "code": "RISK_RATING_NOT_FOUND"
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to deactivate risk rating",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfigSystemView(APIView):
    """System-wide configuration management"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageSystemConfig().has_permission(request, self):
            self.permission_denied(request, message='grc:config:system:manage required.')

    def get(self, request):
        """Get system configuration information"""
        try:
            # Get counts of active items for each configuration type
            fiscal_year_count = FiscalYear.objects.filter(is_active=True).count()
            quarter_count = Quarter.objects.filter(is_active=True).count()
            severity_count = AuditSeverity.objects.filter(is_active=True).count()
            finding_type_count = FindingType.objects.filter(is_active=True).count()
            risk_rating_count = RiskRating.objects.filter(is_active=True).count()
            audit_opinion_count = AuditOpinion.objects.filter(is_active=True).count()
            
            # Get current active fiscal year using date-range logic
            current_fiscal_year = FiscalYear.get_current_fiscal_year()
            current_fiscal_year_data = FiscalYearSerializer(current_fiscal_year).data if current_fiscal_year else None
            
            return success_response(
                data={
                    "configuration_summary": {
                        "fiscal_years": fiscal_year_count,
                        "quarters": quarter_count,
                        "audit_severities": severity_count,
                        "finding_types": finding_type_count,
                        "risk_ratings": risk_rating_count,
                        "audit_opinions": audit_opinion_count,
                    },
                    "current_fiscal_year": current_fiscal_year_data,
                },
            )
        except Exception as e:
            logger.exception("Failed to retrieve system configuration")
            return server_error_response(
                message="Failed to retrieve system configuration",
                details=str(e) if settings.DEBUG else None,
            )
    
    def post(self, request):
        """System configuration actions (e.g., refresh, reset)"""
        try:
            action = request.data.get('action')
            
            if action == 'refresh_lookup_tables':
                # Refresh lookup table data from external sources if needed
                # For now, just return current state
                return Response(
                    {
                        "success": True,
                        "message": "Lookup tables refreshed successfully",
                        "data": {
                            "action": "refresh_lookup_tables",
                            "timestamp": timezone.now().isoformat()
                        }
                    }
                )
            
            elif action == 'validate_configuration':
                # Validate system configuration
                validation_results = {
                    "fiscal_year_setup": FiscalYear.objects.filter(is_active=True).exists(),
                    "quarters_setup": Quarter.objects.filter(is_active=True).exists(),
                    "severities_setup": AuditSeverity.objects.filter(is_active=True).exists(),
                    "finding_types_setup": FindingType.objects.filter(is_active=True).exists(),
                    "risk_ratings_setup": RiskRating.objects.filter(is_active=True).exists(),
                    "audit_opinions_setup": AuditOpinion.objects.filter(is_active=True).exists(),
                }
                
                all_valid = all(validation_results.values())
                
                return Response(
                    {
                        "success": True,
                        "data": {
                            "validation_results": validation_results,
                            "configuration_valid": all_valid,
                            "timestamp": timezone.now().isoformat()
                        },
                        "message": "Configuration validation completed"
                    }
                )
            
            else:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Invalid system action",
                            "code": "INVALID_SYSTEM_ACTION",
                            "allowed_actions": ["refresh_lookup_tables", "validate_configuration"]
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to execute system configuration action",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ── Risk Management Config Views ────────────────────────────────────────────


class _RiskLookupConfigBase(APIView):
    """
    Base class for Risk Management lookup CRUD views.
    Subclasses set model_class, serializer_class, resource_name, and label.
    """
    permission_classes = [IsAuthenticated]
    model_class = None
    serializer_class = None
    resource_name = ''
    label = ''

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method != 'GET' and not CanManageSystemConfig().has_permission(request, self):
            self.permission_denied(request, message='grc:config:system:manage required.')

    def get(self, request, pk=None):
        if pk:
            try:
                obj = self.model_class.objects.get(pk=pk)
                return success_response(data=self.serializer_class(obj).data)
            except self.model_class.DoesNotExist:
                return not_found_response(message=f'{self.label} not found')
        try:
            queryset = self.model_class.objects.all()
            ordering = get_ordering_param(request, default='sort_order', allowed_fields=['sort_order', 'name', 'code'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = self.serializer_class(page_data["queryset"], many=True)
            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
                resource=self.resource_name,
            )
        except Exception as e:
            logger.exception(f"Failed to retrieve {self.label} configuration")
            return server_error_response(message=f"Failed to retrieve {self.label} configuration", details=str(e) if settings.DEBUG else None)

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                obj = serializer.save(created_by=request.user.id if hasattr(request, 'user') else None)
                return created_response(data=self.serializer_class(obj).data, message=f'{self.label} created successfully')
            return validation_error_response(errors=serializer.errors)
        except Exception as e:
            logger.exception(f"Failed to create {self.label}")
            return server_error_response(message=f"Failed to create {self.label}", details=str(e) if settings.DEBUG else None)

    def put(self, request, pk=None):
        if not pk:
            return error_response(message='ID is required for update', status_code=status.HTTP_400_BAD_REQUEST)
        try:
            obj = self.model_class.objects.get(pk=pk)
            serializer = self.serializer_class(obj, data=request.data, partial=True)
            if serializer.is_valid():
                updated = serializer.save(modified_by=request.user.id if hasattr(request, 'user') else None)
                return updated_response(data=self.serializer_class(updated).data, message=f'{self.label} updated successfully')
            return validation_error_response(errors=serializer.errors)
        except self.model_class.DoesNotExist:
            return not_found_response(message=f'{self.label} not found')
        except Exception as e:
            logger.exception(f"Failed to update {self.label}")
            return server_error_response(message=f"Failed to update {self.label}", details=str(e) if settings.DEBUG else None)

    def delete(self, request, pk=None):
        if not pk:
            return error_response(message='ID is required for delete', status_code=status.HTTP_400_BAD_REQUEST)
        try:
            obj = self.model_class.objects.get(pk=pk)
            obj.is_active = False
            obj.modified_by = request.user.id if hasattr(request, 'user') else None
            obj.save()
            return deleted_response(message=f'{self.label} deactivated successfully')
        except self.model_class.DoesNotExist:
            return not_found_response(message=f'{self.label} not found')
        except Exception as e:
            logger.exception(f"Failed to deactivate {self.label}")
            return server_error_response(message=f"Failed to deactivate {self.label}", details=str(e) if settings.DEBUG else None)


class ConfigRiskCategoryView(_RiskLookupConfigBase):
    model_class = RiskCategory
    serializer_class = RiskCategorySerializer
    resource_name = 'config_risk_category'
    label = 'Risk Category'


class ConfigRiskLikelihoodView(_RiskLookupConfigBase):
    model_class = RiskLikelihood
    serializer_class = RiskLikelihoodSerializer
    resource_name = 'config_risk_likelihood'
    label = 'Risk Likelihood'


class ConfigRiskImpactView(_RiskLookupConfigBase):
    model_class = RiskImpact
    serializer_class = RiskImpactSerializer
    resource_name = 'config_risk_impact'
    label = 'Risk Impact'


class ConfigRiskLevelView(_RiskLookupConfigBase):
    model_class = RiskLevel
    serializer_class = RiskLevelSerializer
    resource_name = 'config_risk_level'
    label = 'Risk Level'


class ConfigRiskSectorView(_RiskLookupConfigBase):
    model_class = RiskSector
    serializer_class = RiskSectorSerializer
    resource_name = 'config_risk_sector'
    label = 'Risk Sector'


class ConfigStrategicObjectiveView(_RiskLookupConfigBase):
    model_class = StrategicObjective
    serializer_class = StrategicObjectiveSerializer
    resource_name = 'config_strategic_objective'
    label = 'Strategic Objective'


class ConfigNonConformanceTypeView(_RiskLookupConfigBase):
    model_class = NonConformanceType
    serializer_class = NonConformanceTypeSerializer
    resource_name = 'config_non_conformance_type'
    label = 'Non-Conformance Type'


class ConfigISOClauseView(_RiskLookupConfigBase):
    model_class = ISOClause
    serializer_class = ISOClauseSerializer
    resource_name = 'config_iso_clause'
    label = 'ISO Clause'