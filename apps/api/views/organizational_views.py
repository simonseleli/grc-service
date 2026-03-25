"""
Organizational data API views for GRC Service
Provides access to organizational data synced from Corporate Service
"""

import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.utils import timezone
from django.db.models import Q

from apps.core.models import Directorate, Department, Unit, Section, OrganizationalSyncLog
from apps.core.services import OrganizationalSyncService
from apps.api.serializers.organizational_serializers import (
    DirectorateSerializer, DepartmentSerializer, UnitSerializer, 
    SectionSerializer, OrganizationalSyncLogSerializer
)
from rest_framework.permissions import IsAuthenticated
from apps.api.permissions_jwt import (
    CanViewAuditUniverse,
    CanManageAuditUniverse,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    server_error_response,
)


class OrganizationalDataView(APIView):
    """Get organizational data for audit universe and reporting"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditUniverse().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_universe:view required.')

    def get(self, request):
        """Get all organizational data in hierarchical structure (no pagination - tree view)"""
        try:
            # Get query parameters
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            include_hierarchy = request.query_params.get('hierarchy', 'true').lower() == 'true'
            
            # Build base queryset
            directorates = Directorate.objects.filter(is_active=is_active).order_by('name')
            
            if include_hierarchy:
                # Include related objects for hierarchical view
                directorates = directorates.prefetch_related(
                    'departments__units__sections'
                )
            
            # Serialize data
            directorate_data = DirectorateSerializer(directorates, many=True, context={
                'include_hierarchy': include_hierarchy
            }).data
            
            return success_response(
                data={
                    "directorates": directorate_data,
                },
            )
        except Exception as e:
            logger.exception("Failed to retrieve organizational data")
            return server_error_response(
                message="Failed to retrieve organizational data",
                details=str(e) if settings.DEBUG else None,
            )


class DirectorateListView(APIView):
    """List directorates for audit universe creation"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        from apps.api.permissions_jwt import IsGRCUser
        if not IsGRCUser().has_permission(request, self):
            self.permission_denied(request, message='A valid GRC role is required.')

    def get(self, request):
        """Get all active directorates with pagination"""
        try:
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            search = request.query_params.get('search')
            
            queryset = Directorate.objects.filter(is_active=is_active)
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | Q(code__icontains=search)
                )
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='name',
                allowed_fields=['name', 'code', 'created_at']
            )
            queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = DirectorateSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="directorates",
            )
        except Exception as e:
            logger.exception("Failed to retrieve directorates")
            return server_error_response(
                message="Failed to retrieve directorates",
                details=str(e) if settings.DEBUG else None,
            )


class DepartmentListView(APIView):
    """List departments for audit universe creation"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditUniverse().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_universe:view required.')

    def get(self, request):
        """Get departments, optionally filtered by directorate, with pagination"""
        try:
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            directorate_id = request.query_params.get('directorate_id')
            search = request.query_params.get('search')
            
            queryset = Department.objects.filter(is_active=is_active).select_related('directorate')
            
            if directorate_id:
                queryset = queryset.filter(directorate_id=directorate_id)
                
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | Q(code__icontains=search)
                )
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='directorate__name,name',
                allowed_fields=['directorate__name', 'name', 'code']
            )
            # Handle compound ordering
            if ',' in ordering:
                ordering_fields = [f.strip() for f in ordering.split(',')]
                queryset = queryset.order_by(*ordering_fields)
            else:
                queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = DepartmentSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="departments",
                filtered_by_directorate=directorate_id is not None,
            )
        except Exception as e:
            logger.exception("Failed to retrieve departments")
            return server_error_response(
                message="Failed to retrieve departments",
                details=str(e) if settings.DEBUG else None,
            )


class UnitListView(APIView):
    """List units for audit universe creation"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditUniverse().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_universe:view required.')

    def get(self, request):
        """Get units, optionally filtered by department, with pagination"""
        try:
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            department_id = request.query_params.get('department_id')
            search = request.query_params.get('search')
            
            queryset = Unit.objects.filter(is_active=is_active).select_related(
                'directorate', 'department'
            )
            
            if department_id:
                queryset = queryset.filter(department_id=department_id)
                
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | Q(code__icontains=search)
                )
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='department__name,name',
                allowed_fields=['department__name', 'name', 'code']
            )
            # Handle compound ordering
            if ',' in ordering:
                ordering_fields = [f.strip() for f in ordering.split(',')]
                queryset = queryset.order_by(*ordering_fields)
            else:
                queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = UnitSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="units",
                filtered_by_department=department_id is not None,
            )
        except Exception as e:
            logger.exception("Failed to retrieve units")
            return server_error_response(
                message="Failed to retrieve units",
                details=str(e) if settings.DEBUG else None,
            )


class SectionListView(APIView):
    """List sections for audit universe creation"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditUniverse().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_universe:view required.')

    def get(self, request):
        """Get sections, optionally filtered by unit, with pagination"""
        try:
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            unit_id = request.query_params.get('unit_id')
            search = request.query_params.get('search')
            
            queryset = Section.objects.filter(is_active=is_active).select_related(
                'unit__department__directorate'
            )
            
            if unit_id:
                queryset = queryset.filter(unit_id=unit_id)
                
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | Q(code__icontains=search)
                )
            
            # Apply ordering (FIMS standard)
            ordering = get_ordering_param(
                request,
                default='unit__name,name',
                allowed_fields=['unit__name', 'name', 'code']
            )
            # Handle compound ordering
            if ',' in ordering:
                ordering_fields = [f.strip() for f in ordering.split(',')]
                queryset = queryset.order_by(*ordering_fields)
            else:
                queryset = queryset.order_by(ordering)
            
            # Apply pagination (FIMS standard)
            page_data = paginate_queryset(queryset, request)
            
            serializer = SectionSerializer(page_data["queryset"], many=True)
            
            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="sections",
                filtered_by_unit=unit_id is not None,
            )
        except Exception as e:
            logger.exception("Failed to retrieve sections")
            return server_error_response(
                message="Failed to retrieve sections",
                details=str(e) if settings.DEBUG else None,
            )


class OrganizationalSyncView(APIView):
    """Manage organizational data synchronization from Corporate Service"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not CanViewAuditUniverse().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_universe:view required.')
        elif request.method == 'POST':
            if not CanManageAuditUniverse().has_permission(request, self):
                self.permission_denied(request, message='grc:audit_universe:manage required.')

    def get(self, request):
        """Get sync status and history"""
        try:
            # Get recent sync logs
            logs = OrganizationalSyncLog.objects.all()[:10]  # Last 10 sync operations
            
            # Get last sync for each type
            last_syncs = {}
            for sync_type in ['directorates', 'departments', 'units', 'sections', 'full_sync']:
                last_sync = OrganizationalSyncLog.objects.filter(
                    sync_type=sync_type, 
                    status='completed'
                ).first()
                last_syncs[sync_type] = last_sync.completed_at if last_sync else None
            
            return Response(
                {
                    "success": True,
                    "data": {
                        "sync_history": OrganizationalSyncLogSerializer(logs, many=True).data,
                        "last_sync_times": last_syncs,
                        "current_stats": {
                            "directorates": Directorate.objects.filter(is_active=True).count(),
                            "departments": Department.objects.filter(is_active=True).count(),
                            "units": Unit.objects.filter(is_active=True).count(),
                            "sections": Section.objects.filter(is_active=True).count(),
                        },
                        "last_refresh": timezone.now().isoformat(),
                    },
                    "meta": {
                        "service": "grc-service",
                        "resource": "organizational_sync",
                        "version": "v1.0",
                    },
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to retrieve sync status",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Trigger organizational data sync"""
        try:
            sync_type = request.data.get('sync_type', 'full_sync')
            user_id = request.headers.get('X-User-ID')
            
            valid_sync_types = ['directorates', 'departments', 'units', 'sections', 'full_sync']
            if sync_type not in valid_sync_types:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": f"Invalid sync type. Valid types: {', '.join(valid_sync_types)}",
                            "code": "INVALID_SYNC_TYPE"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            sync_service = OrganizationalSyncService()
            
            if sync_type == 'full_sync':
                results = sync_service.sync_all(started_by=user_id)
                message = "Full organizational sync completed successfully"
            elif sync_type == 'directorates':
                processed, created, updated = sync_service.sync_directorates(started_by=user_id)
                results = {'directorates': (processed, created, updated)}
                message = "Directorate sync completed successfully"
            elif sync_type == 'departments':
                processed, created, updated = sync_service.sync_departments(started_by=user_id)
                results = {'departments': (processed, created, updated)}
                message = "Department sync completed successfully"
            elif sync_type == 'units':
                processed, created, updated = sync_service.sync_units(started_by=user_id)
                results = {'units': (processed, created, updated)}
                message = "Unit sync completed successfully"
            elif sync_type == 'sections':
                processed, created, updated = sync_service.sync_sections(started_by=user_id)
                results = {'sections': (processed, created, updated)}
                message = "Section sync completed successfully"
            
            return Response(
                {
                    "success": True,
                    "data": {
                        "sync_results": results,
                        "timestamp": timezone.now().isoformat(),
                    },
                    "message": message
                }
            )
            
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": f"Sync operation failed: {str(e)}",
                        "code": "SYNC_FAILED"
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )