"""
Pagination utility for GRC APIView-based list endpoints.

Since GRC uses raw APIView (not GenericAPIView or ModelViewSet), DRF's
automatic pagination doesn't apply. This utility provides manual pagination
that matches the FIMS platform standard.

Settings (from config/settings.py REST_FRAMEWORK):
    PAGE_SIZE: 20 (default items per page)
    MAX_PAGE_SIZE: 100 (maximum allowed page_size)

Query Parameters:
    page (int): Page number, 1-based. Default: 1
    page_size (int): Items per page. Default: 20, Max: 100

Usage:
    from apps.api.utils.pagination import paginate_queryset
    from apps.api.utils.response_helpers import paginated_list_response
    
    def get(self, request):
        queryset = MyModel.objects.all()
        page_data = paginate_queryset(queryset, request)
        serializer = MySerializer(page_data["queryset"], many=True)
        return paginated_list_response(
            items=serializer.data,
            count=page_data["total"],
            page=page_data["page"],
            page_size=page_data["page_size"],
            resource="my_resource",
        )

Pattern reference:
    Document Records Service: apps/api/views/document_views.py (lines 95-100)
"""

from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.db.models import QuerySet


# Get defaults from REST_FRAMEWORK settings (set in Phase 1)
# Fallback to FIMS standard values if not configured
_REST_SETTINGS = getattr(settings, 'REST_FRAMEWORK', {})
DEFAULT_PAGE_SIZE: int = _REST_SETTINGS.get('PAGE_SIZE', 20)
MAX_PAGE_SIZE: int = _REST_SETTINGS.get('MAX_PAGE_SIZE', 100)


def _get_query_param(request, name: str, default: str = None) -> Optional[str]:
    """
    Get a query parameter from request, handling both DRF Request and Django WSGIRequest.
    
    DRF Request has `query_params`, Django WSGIRequest has `GET`.
    Document Records uses `request.GET.get()` directly.
    """
    # Try DRF's query_params first (preferred)
    if hasattr(request, 'query_params'):
        return request.query_params.get(name, default)
    # Fall back to Django's GET
    if hasattr(request, 'GET'):
        return request.GET.get(name, default)
    return default


def paginate_queryset(
    queryset: QuerySet,
    request,
    default_page_size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Apply pagination to a queryset based on request query parameters.
    
    Follows Document Records pattern:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        skip = (page - 1) * page_size
    
    Args:
        queryset: Django QuerySet to paginate
        request: DRF Request or Django WSGIRequest with query params
        default_page_size: Override default page size (optional)
    
    Returns:
        dict with:
            queryset: The sliced queryset for the current page
            page: Current page number (1-based)
            page_size: Items per page
            total: Total count across all pages
            total_pages: Number of pages
    
    Example:
        >>> page_data = paginate_queryset(AuditUniverse.objects.all(), request)
        >>> serializer = AuditUniverseSerializer(page_data["queryset"], many=True)
        >>> page_data["total"]  # e.g., 250
        >>> page_data["page"]   # e.g., 1
    """
    page_size_default = default_page_size if default_page_size else DEFAULT_PAGE_SIZE
    
    # Parse page parameter (1-based, minimum 1)
    try:
        page = int(_get_query_param(request, 'page', '1'))
        page = max(1, page)  # Ensure minimum of 1
    except (ValueError, TypeError):
        page = 1
    
    # Parse page_size parameter with bounds enforcement
    try:
        page_size = int(_get_query_param(request, 'page_size', str(page_size_default)))
        # Enforce bounds: minimum 1, maximum MAX_PAGE_SIZE
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    except (ValueError, TypeError):
        page_size = page_size_default
    
    # Get total count (single DB query, cached by Django)
    total = queryset.count()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    # Adjust page if it exceeds total pages (but keep minimum of 1)
    if total_pages > 0 and page > total_pages:
        page = total_pages
    
    # Calculate offset for slicing
    offset = (page - 1) * page_size
    
    # Slice queryset (Django evaluates lazily)
    paginated_queryset = queryset[offset:offset + page_size]
    
    return {
        "queryset": paginated_queryset,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def get_ordering_param(
    request,
    default: str = '-created_at',
    allowed_fields: Optional[List[str]] = None,
) -> str:
    """
    Extract and validate ordering parameter from request.
    
    Query Parameters:
        ordering (str): Field to sort by. Prefix with '-' for descending.
    
    Args:
        request: DRF Request or Django WSGIRequest
        default: Default ordering if not specified or invalid
        allowed_fields: List of allowed field names (without '-' prefix).
                       If None, all fields are allowed.
    
    Returns:
        Validated ordering string (e.g., '-created_at', 'name')
    
    Example:
        >>> ordering = get_ordering_param(request, default='-fiscal_year__start_date')
        >>> queryset = queryset.order_by(ordering)
    """
    ordering = _get_query_param(request, 'ordering', default)
    
    if not ordering:
        return default
    
    # If allowed_fields is specified, validate the field
    if allowed_fields is not None:
        # Strip leading '-' for comparison
        field_name = ordering.lstrip('-')
        if field_name not in allowed_fields:
            return default
    
    return ordering


def parse_boolean_param(value: Optional[str], default: bool = False) -> bool:
    """
    Parse a boolean query parameter.
    
    Handles common truthy/falsy string values:
        True: 'true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES'
        False: 'false', 'False', 'FALSE', '0', 'no', 'No', 'NO', None, ''
    
    Args:
        value: String value from query parameter
        default: Default if value is None or empty
    
    Returns:
        Boolean value
    
    Example:
        >>> is_active = parse_boolean_param(request.query_params.get('is_active'))
    """
    if value is None or value == '':
        return default
    
    return value.lower() in ('true', '1', 'yes')


def parse_uuid_list(value: Optional[str]) -> List[str]:
    """
    Parse a comma-separated list of UUIDs from query parameter.
    
    Args:
        value: Comma-separated string of UUIDs (e.g., "uuid1,uuid2,uuid3")
    
    Returns:
        List of UUID strings (empty list if None or empty)
    
    Example:
        >>> ids = parse_uuid_list(request.query_params.get('ids'))
        >>> queryset = queryset.filter(id__in=ids)
    """
    if not value:
        return []
    
    return [uuid.strip() for uuid in value.split(',') if uuid.strip()]
