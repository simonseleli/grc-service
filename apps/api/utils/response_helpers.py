"""
Reusable response helpers to standardize GRC API payloads.

Follows the FIMS platform pattern used by:
- document-records-service/apps/api/utils/response_helpers.py
- iam-service (similar envelope structure)

All GRC views should use these instead of constructing Response dicts inline.
This ensures:
- Consistent envelope structure across all endpoints
- Standardized error format
- Proper pagination metadata

Response Format (standard):
    {
        "success": true,
        "data": { ... },
        "meta"?: { ... },
        "message"?: "..."
    }

Response Format (list with pagination — Document Records pattern):
    {
        "success": true,
        "data": [...items directly...],
        "meta": {
            "page": 1,
            "page_size": 20,
            "total": 100,
            "total_pages": 5
        }
    }

Error Format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable message",
            "details": { ... } | null
        }
    }
"""

from typing import Any, Dict, List, Optional, Union

from django.utils import timezone
from rest_framework import status as drf_status
from rest_framework.response import Response


# =============================================================================
# SUCCESS RESPONSES
# =============================================================================

def success_response(
    data: Any = None,
    *,
    meta: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    status_code: int = drf_status.HTTP_200_OK,
) -> Response:
    """
    Standard success envelope for single-item responses.
    Matches document-records-service/apps/api/utils/response_helpers.py exactly.

    Format:
        {"success": true, "data": {...}, "meta"?: {...}, "message"?: "..."}

    Args:
        data: Response data (dict, list, or any serializable)
        meta: Optional metadata dict (only included when provided)
        message: Optional success message
        status_code: HTTP status code (default: 200)

    Returns:
        DRF Response with envelope
    """
    payload: Dict[str, Any] = {"success": True, "data": data}
    if meta is not None:
        payload["meta"] = meta
    if message:
        payload["message"] = message
    return Response(payload, status=status_code)


def paginated_list_response(
    items: List,
    *,
    count: int,
    page: int,
    page_size: int,
    total_pages: Optional[int] = None,
    meta: Optional[Dict[str, Any]] = None,
    **_extra,
) -> Response:
    """
    Paginated list envelope (FIMS standard — Document Records pattern).

    This follows the Document Records service pattern EXACTLY:
    - Items go DIRECTLY in ``data`` (not wrapped in {items: [...]})
    - Total count goes in ``meta.total`` (not data.count)
    - Pagination info goes in ``meta``

    Format (matches document-records-service paginated_response):
        {
            "success": true,
            "data": [...items directly...],
            "meta": {
                "page": 1,
                "page_size": 20,
                "total": 100,
                "total_pages": 5
            }
        }

    Args:
        items: List of serialized items for current page
        count: Total count across ALL pages (becomes meta.total)
        page: Current page number (1-based)
        page_size: Items per page
        total_pages: Total pages (calculated if not provided)
        meta: Additional meta fields to merge
        **_extra: Accepts (and ignores) legacy kwargs like ``resource``

    Returns:
        DRF Response with paginated list envelope
    """
    if total_pages is None:
        total_pages = (count + page_size - 1) // page_size if page_size > 0 else 0

    pagination_meta: Dict[str, Any] = {
        "page": page,
        "page_size": page_size,
        "total": count,
        "total_pages": total_pages,
    }
    if meta:
        pagination_meta.update(meta)

    return success_response(
        data=items,
        meta=pagination_meta,
        status_code=drf_status.HTTP_200_OK,
    )


def created_response(
    data: Any,
    *,
    meta: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    **_extra,
) -> Response:
    """
    Standard response for resource creation (HTTP 201).
    """
    return success_response(
        data=data,
        meta=meta,
        message=message or "Created successfully",
        status_code=drf_status.HTTP_201_CREATED,
    )


def updated_response(
    data: Any,
    *,
    meta: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    **_extra,
) -> Response:
    """
    Standard response for resource update (HTTP 200).
    """
    return success_response(
        data=data,
        meta=meta,
        message=message or "Updated successfully",
        status_code=drf_status.HTTP_200_OK,
    )


def deleted_response(
    message: Optional[str] = None,
    **_extra,
) -> Response:
    """
    Standard response for resource deletion (soft delete).
    """
    return Response(
        {
            "success": True,
            "message": message or "Deleted successfully",
        },
        status=drf_status.HTTP_200_OK,
    )


# =============================================================================
# ERROR RESPONSES
# =============================================================================

def error_response(
    message: str,
    *,
    status_code: int = drf_status.HTTP_400_BAD_REQUEST,
    code: Optional[str] = None,
    details: Optional[Any] = None,
) -> Response:
    """
    Standard error envelope.
    
    Format:
        {"success": false, "error": {"message": "...", "code"?: "...", "details"?: ...}}
    
    Args:
        message: Human-readable error message
        status_code: HTTP status code (default: 400)
        code: Machine-readable error code (e.g., "VALIDATION_ERROR")
        details: Additional error details (e.g., field errors)
    
    Returns:
        DRF Response with error envelope
    
    Example:
        return error_response(
            message="Invalid fiscal year",
            code="INVALID_FISCAL_YEAR",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    """
    error_payload: Dict[str, Any] = {"message": message}
    if code:
        error_payload["code"] = code
    if details is not None:
        error_payload["details"] = details
    
    return Response(
        {"success": False, "error": error_payload},
        status=status_code,
    )


def not_found_response(
    message: str = "Resource not found",
    code: str = "NOT_FOUND",
) -> Response:
    """
    Convenience wrapper for 404 errors.
    
    Args:
        message: Error message
        code: Error code
    
    Returns:
        DRF Response with HTTP 404
    
    Example:
        return not_found_response("Audit universe not found")
    """
    return error_response(
        message=message,
        status_code=drf_status.HTTP_404_NOT_FOUND,
        code=code,
    )


def validation_error_response(
    errors: Union[Dict, List, str],
    message: str = "Validation error",
) -> Response:
    """
    Convenience wrapper for validation errors (HTTP 400).
    
    Args:
        errors: Serializer errors or validation details
        message: Summary message
    
    Returns:
        DRF Response with HTTP 400
    
    Example:
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
    """
    return error_response(
        message=message,
        status_code=drf_status.HTTP_400_BAD_REQUEST,
        code="VALIDATION_ERROR",
        details=errors,
    )


def unauthorized_response(
    message: str = "Authentication required",
) -> Response:
    """
    Convenience wrapper for 401 errors.
    
    Args:
        message: Error message
    
    Returns:
        DRF Response with HTTP 401
    
    Example:
        return unauthorized_response("Invalid or expired token")
    """
    return error_response(
        message=message,
        status_code=drf_status.HTTP_401_UNAUTHORIZED,
        code="AUTH_REQUIRED",
    )


def forbidden_response(
    message: str = "Permission denied",
    permission: Optional[str] = None,
) -> Response:
    """
    Convenience wrapper for 403 errors.
    
    Args:
        message: Error message
        permission: Permission code that was required
    
    Returns:
        DRF Response with HTTP 403
    
    Example:
        return forbidden_response(
            message="You cannot approve this audit universe",
            permission="grc:audit_universe:approve",
        )
    """
    details = {"required_permission": permission} if permission else None
    return error_response(
        message=message,
        status_code=drf_status.HTTP_403_FORBIDDEN,
        code="PERMISSION_DENIED",
        details=details,
    )


def conflict_response(
    message: str,
    code: str = "CONFLICT",
) -> Response:
    """
    Convenience wrapper for 409 Conflict errors.
    
    Args:
        message: Conflict description
        code: Error code
    
    Returns:
        DRF Response with HTTP 409
    
    Example:
        return conflict_response("Audit universe already exists for this fiscal year")
    """
    return error_response(
        message=message,
        status_code=drf_status.HTTP_409_CONFLICT,
        code=code,
    )


def server_error_response(
    message: str = "Internal server error",
    details: Optional[str] = None,
) -> Response:
    """
    Convenience wrapper for 500 errors.
    
    Args:
        message: Error message (keep generic for production)
        details: Exception details (only include in DEBUG mode)
    
    Returns:
        DRF Response with HTTP 500
    
    Example:
        try:
            ...
        except Exception as e:
            logger.exception("Unexpected error")
            return server_error_response(
                details=str(e) if settings.DEBUG else None
            )
    """
    return error_response(
        message=message,
        status_code=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        details=details,
    )
