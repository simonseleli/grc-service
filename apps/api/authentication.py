"""
Custom Authentication Classes for GRC Service
Following FIMS authentication patterns from Document Records Service
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)


class IAMJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that trusts tokens signed by shared JWT_SECRET_KEY
    Since both IAM and GRC services use the same JWT secret, we can trust the token signature.
    
    This creates a user object from the validated JWT token claims without
    calling the IAM service on every request (performance optimization).
    """
    
    def get_user(self, validated_token):
        """
        Create user object from validated JWT token claims
        """
        try:
            # Extract user ID from token
            user_id = validated_token.get('user_id')
            
            if not user_id:
                logger.error("No user_id found in JWT token")
                return AnonymousUser()
            
            # Create a minimal user object for Django
            # Since the token is already validated (signed with shared secret), we trust it
            from django.contrib.auth.models import User
            user = User()
            user.id = user_id
            user.username = validated_token.get('email', f'user_{user_id}')
            user.email = validated_token.get('email', '')
            user.is_active = True  # Token is valid, so user is active
            user.is_staff = validated_token.get('is_staff', False)
            user.is_superuser = validated_token.get('is_superuser', False)
            
            # Store additional token claims for permission checks
            user._jwt_permissions = validated_token.get('permissions', {})
            user._jwt_permissions_flat = validated_token.get('permissions_flat', [])
            user._jwt_services = validated_token.get('services', [])
            
            logger.debug(f"Authenticated user {user_id} via JWT token")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user from token: {e}")
            return AnonymousUser()


class ServiceAuthentication(JWTAuthentication):
    """
    Service-to-service authentication for internal FIMS services
    Allows services to communicate without user context (for background jobs, etc.)
    """
    
    def authenticate(self, request):
        """
        Authenticate service requests using X-Service-Token header
        Falls back to JWT authentication if service token not present
        """
        # Check for service token in headers
        service_token = request.META.get('HTTP_X_SERVICE_TOKEN')
        if service_token:
            # Validate service token
            if self.validate_service_token(service_token):
                logger.debug("Authenticated via service token")
                # Create a service user (anonymous but marked as authenticated)
                from django.contrib.auth.models import User
                user = User()
                user.id = '00000000-0000-0000-0000-000000000001'  # System user
                user.username = 'service'
                user.is_active = True
                user.is_staff = True
                user._is_service = True
                return (user, None)
        
        # Fall back to JWT authentication
        return super().authenticate(request)
    
    def validate_service_token(self, token):
        """
        Validate service token against configured service tokens
        In production, this should check against a secret from environment
        """
        from django.conf import settings
        expected_token = getattr(settings, 'SERVICE_TO_SERVICE_TOKEN', None)
        if expected_token:
            return token == expected_token
        # For development, accept any non-empty token over 20 chars
        return bool(token and len(token) > 20)
