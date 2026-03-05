"""
Custom exception handler for GRC Service.

Follows FIMS platform pattern (IAM, Document Records) for consistent error responses.
All exceptions are wrapped in a standard envelope format.

Response format:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": {...} or null
    }
}
"""

import logging
import traceback

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error responses.
    
    Follows IAM/Document Records pattern for FIMS platform consistency.
    """
    # Extract context info for logging
    view_name = getattr(context.get('view'), '__class__', type(None)).__name__
    request = context.get('request')
    request_path = getattr(request, 'path', 'unknown') if request else 'unknown'
    error_trace = traceback.format_exc()
    
    # Log the exception
    logger.error(f"Exception in {view_name} at {request_path}: {exc}")
    if settings.DEBUG:
        logger.error(f"Traceback:\n{error_trace}")
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # DRF handled the exception - customize the response format
        custom_response_data = {
            'success': False,
            'error': {
                'code': _get_error_code(exc),
                'message': _get_error_message(exc),
                'details': _get_error_details(response.data),
            }
        }
        response.data = custom_response_data
    else:
        # Exception not handled by DRF - handle common cases
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = 'INTERNAL_ERROR'
        message = 'An unexpected error occurred'
        details = None
        
        if isinstance(exc, DjangoValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = 'VALIDATION_ERROR'
            message = str(exc.message) if hasattr(exc, 'message') else str(exc)
            details = getattr(exc, 'message_dict', None)
        elif isinstance(exc, IntegrityError):
            status_code = status.HTTP_409_CONFLICT
            error_code = 'INTEGRITY_ERROR'
            message = 'Database integrity constraint violated'
            if settings.DEBUG:
                details = {'db_error': str(exc)}
        elif isinstance(exc, ValueError):
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = 'INVALID_VALUE'
            message = str(exc)
        elif isinstance(exc, PermissionError):
            status_code = status.HTTP_403_FORBIDDEN
            error_code = 'PERMISSION_DENIED'
            message = str(exc) or 'Permission denied'
        else:
            # Unknown exception - log full details
            logger.exception(f"Unhandled exception in {view_name}: {exc}")
            if settings.DEBUG:
                message = str(exc)
                details = {'type': type(exc).__name__, 'traceback': error_trace}
        
        response = Response(
            {
                'success': False,
                'error': {
                    'code': error_code,
                    'message': message,
                    'details': details,
                }
            },
            status=status_code
        )
    
    return response


def _get_error_code(exc):
    """
    Get error code based on exception type.
    
    Order of preference:
    1. exc.default_code (DRF exceptions)
    2. exc.code (custom exceptions)
    3. Inferred from exception class name
    """
    if hasattr(exc, 'default_code') and exc.default_code:
        return str(exc.default_code).upper()
    if hasattr(exc, 'code') and exc.code:
        return str(exc.code).upper()
    
    # Infer from class name
    class_name = type(exc).__name__
    # Convert CamelCase to SCREAMING_SNAKE_CASE
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).upper()


def _get_error_message(exc):
    """
    Get user-friendly error message from exception.
    """
    if hasattr(exc, 'detail'):
        detail = exc.detail
        if isinstance(detail, list):
            return str(detail[0]) if detail else 'An error occurred'
        if isinstance(detail, dict):
            # Try to get a general message
            if 'detail' in detail:
                return str(detail['detail'])
            if 'message' in detail:
                return str(detail['message'])
            # Return first error message
            for key, value in detail.items():
                if isinstance(value, list) and value:
                    return f"{key}: {value[0]}"
                return f"{key}: {value}"
        return str(detail)
    
    if hasattr(exc, 'message'):
        return str(exc.message)
    
    return str(exc) or 'An error occurred'


def _get_error_details(response_data):
    """
    Extract error details from DRF response data.
    
    Returns None if no useful details, otherwise returns the details dict.
    """
    if not response_data:
        return None
    
    if isinstance(response_data, dict):
        # Remove 'detail' key if it's the only content (already in message)
        if list(response_data.keys()) == ['detail']:
            return None
        # Return field errors for validation
        return response_data
    
    if isinstance(response_data, list):
        return {'errors': response_data}
    
    return None
