"""
Permission decorators for GRC configuration management
"""

from functools import wraps
from django.http import JsonResponse
from django.conf import settings
import requests


def require_permission(permission_name):
    """
    Decorator to enforce permission requirements for configuration management operations
    """
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, request, *args, **kwargs):
            # Extract user information from request headers (set by API Gateway)
            user_id = request.headers.get('X-User-ID')
            user_role = request.headers.get('X-User-Role')
            
            if not user_id or not user_role:
                return JsonResponse(
                    {
                        "success": False,
                        "error": {
                            "message": "Authentication required",
                            "code": "AUTHENTICATION_REQUIRED"
                        }
                    },
                    status=401
                )
            
            # Check if user has the required permission
            if not check_user_permission(user_id, user_role, permission_name):
                return JsonResponse(
                    {
                        "success": False,
                        "error": {
                            "message": f"Permission required: {permission_name}",
                            "code": "PERMISSION_DENIED"
                        }
                    },
                    status=403
                )
            
            # Add user info to request for use in view
            request.user_id = user_id
            request.user_role = user_role
            
            return view_method(self, request, *args, **kwargs)
        return wrapper
    return decorator


def check_user_permission(user_id, user_role, permission_name):
    """
    Check if user has the required permission through IAM service
    """
    try:
        # Check local permission configuration first
        from shared.permissions import load_service_permissions
        
        service_permissions = load_service_permissions()
        
        # Get role permissions
        role_permissions = service_permissions.get('roles', {}).get(user_role, {}).get('permissions', [])
        
        # Check if role has the required permission
        if permission_name in role_permissions:
            return True
        
        # If not found locally, check with IAM service
        iam_service_url = getattr(settings, 'IAM_SERVICE_URL', 'http://iam-service:8000')
        
        response = requests.get(
            f"{iam_service_url}/api/v1/permissions/check/",
            params={
                'user_id': user_id,
                'permission': permission_name,
                'service': 'grc-service'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('has_permission', False)
        
        return False
        
    except Exception as e:
        # Log error and deny access by default
        print(f"Permission check error: {str(e)}")
        return False


def config_fiscal_year_permission(view_method):
    """Decorator for fiscal year configuration permission"""
    return require_permission('config:fiscal_year:manage')(view_method)


def config_audit_severity_permission(view_method):
    """Decorator for audit severity configuration permission"""
    return require_permission('config:audit_severity:manage')(view_method)


def config_finding_type_permission(view_method):
    """Decorator for finding type configuration permission"""
    return require_permission('config:finding_type:manage')(view_method)


def config_risk_rating_permission(view_method):
    """Decorator for risk rating configuration permission"""
    return require_permission('config:risk_rating:manage')(view_method)


def config_system_permission(view_method):
    """Decorator for system configuration permission"""
    return require_permission('config:system:manage')(view_method)