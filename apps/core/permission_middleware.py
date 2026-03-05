"""
Permission validation middleware for GRC Service.
Validates permissions from JWT tokens without calling IAM service.

Follows the exact pattern of document-records-service/apps/core/permission_middleware.py:
- Set clean request attributes (user_id, user_email, is_superuser, is_staff, grc_permissions)
- Extract service-specific permission list (grc_permissions) from JWT
- No process_response() cleanup (Doc Records does not do this)
"""
import logging
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class JWTPermissionMiddleware(MiddlewareMixin):
    """
    Middleware to validate JWT permissions locally without IAM service calls.

    On every authenticated request this middleware:
    1. Decodes the Bearer JWT using the shared JWT_SECRET_KEY
    2. Confirms the user has access to the 'grc' service
    3. Sets the following attributes on the request object for use by
       apps/api/permissions_jwt.py permission classes:
         - request.user_id          (str UUID)
         - request.user_email       (str)
         - request.is_superuser     (bool)
         - request.is_staff         (bool)
         - request.user_permissions (dict  — raw JWT 'permissions' field)
         - request.user_permissions_flat (list — raw JWT 'permissions_flat' field)
         - request.user_services    (list)
         - request.grc_permissions  (list of 'grc:*' permission codes)

    Skips validation for health checks, static files, and service-token requests.
    """

    # Accept any of these values as 'has GRC service access'
    _GRC_SERVICE_ALIASES = {'grc-service', 'grc'}

    def process_request(self, request):
        """
        Process incoming request.  Returns None to continue, or a JsonResponse
        to short-circuit with an error.
        """
        # ── Skip paths ────────────────────────────────────────────────────────
        skip_paths = [
            '/health/',
            '/admin/',
            '/static/',
            '/media/',
            '/api/v1/auth/',
            '/api/v1/token/',
            '/api/schema/',
            '/api/docs/',
        ]
        if any(request.path.startswith(p) for p in skip_paths):
            return None

        # ── Service-to-service token: let DRF authentication handle it ───────
        if request.META.get('HTTP_X_SERVICE_TOKEN'):
            logger.debug(f"Service token detected for {request.path}")
            return None

        # ── Require Bearer token ──────────────────────────────────────────────
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            # No Bearer header — let DRF give the proper 401 with its own message
            return None

        token = auth_header.split(' ', 1)[1]

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={'verify_exp': True},
            )

            # ── Service access gate ───────────────────────────────────────────
            services = payload.get('services', [])
            has_grc = (
                '*' in services
                or any(s in self._GRC_SERVICE_ALIASES for s in services)
            )
            is_superuser = payload.get('is_superuser', False)

            if not is_superuser and not has_grc:
                logger.warning(
                    f"User {payload.get('user_id')} denied GRC service access. "
                    f"Services in token: {services}"
                )
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'message': 'Access to GRC service denied',
                            'code': 'SERVICE_ACCESS_DENIED',
                        },
                    },
                    status=403,
                )

            # ── Attach clean attributes (matches Doc Records pattern) ─────────
            request.user_id = payload.get('user_id')
            request.user_email = payload.get('email')
            request.is_superuser = is_superuser
            request.is_staff = payload.get('is_staff', False)
            request.user_permissions = payload.get('permissions', {})
            request.user_permissions_flat = payload.get('permissions_flat', [])
            request.user_services = services

            # ── Build grc_permissions list (same logic as Doc Records) ────────
            if is_superuser:
                request.grc_permissions = ['*']
                logger.info(f"User {request.user_email} is superuser — granted all GRC permissions")
            else:
                # Try the permissions dict first (keyed by service name)
                perms_dict = request.user_permissions
                grc_perms = perms_dict.get('grc-service', []) or perms_dict.get('grc', [])

                # Fall back to filtering permissions_flat for 'grc:' prefixed codes
                if not grc_perms:
                    flat = request.user_permissions_flat
                    if isinstance(flat, list) and flat == ['*']:
                        grc_perms = ['*']
                    elif isinstance(flat, list):
                        grc_perms = [p for p in flat if p.startswith('grc:')]

                request.grc_permissions = grc_perms if isinstance(grc_perms, list) else []
                logger.debug(
                    f"User {request.user_email} has {len(request.grc_permissions)} GRC permissions. "
                    f"First 10: {request.grc_permissions[:10]}"
                )

                if has_grc and not request.grc_permissions:
                    logger.warning(
                        f"User {request.user_email} has GRC service access but no grc: permissions "
                        f"found in JWT. permissions dict keys: {list(perms_dict.keys())}"
                    )

            logger.debug(f"JWT validated for user {request.user_id} accessing {request.path}")
            return None

        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired JWT token for {request.path}")
            return JsonResponse(
                {
                    'success': False,
                    'error': {'message': 'Token has expired', 'code': 'TOKEN_EXPIRED'},
                },
                status=401,
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token for {request.path}: {e}")
            return JsonResponse(
                {
                    'success': False,
                    'error': {'message': 'Invalid authentication token', 'code': 'INVALID_TOKEN'},
                },
                status=401,
            )
        except Exception as e:
            logger.error(f"Error validating JWT for {request.path}: {e}")
            return JsonResponse(
                {
                    'success': False,
                    'error': {'message': 'Authentication error', 'code': 'AUTH_ERROR'},
                },
                status=500,
            )
