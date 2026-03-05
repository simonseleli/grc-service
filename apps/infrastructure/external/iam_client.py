"""
IAM Service Client for GRC Service.
Fetches user profiles from the IAM service for notification context.

Follows the same pattern as:
  - document-records-service/apps/core/iam_client.py
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class IAMClient:
    """
    Client for fetching user data from IAM service.
    Used by notification publisher to resolve user email / display name.
    """

    def __init__(self):
        self.iam_service_url = getattr(
            settings, 'IAM_SERVICE_URL', 'http://iam-service:8000'
        )
        self.timeout = 5  # seconds
        self.cache_timeout = 300  # 5 minutes

    def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to IAM service."""
        import requests

        url = f"{self.iam_service_url}/api/v1{endpoint}"
        request_headers = headers or {}

        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                headers=request_headers if request_headers else None,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"IAM service request failed ({method} {url}): {e}")
            return None

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile from IAM service.
        Returns dict with keys: id, email, first_name, last_name, username, etc.
        """
        cache_key = f"grc_iam_user_profile:{user_id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        result = self._make_request('GET', f'/users/{user_id}/')

        if result:
            cache.set(cache_key, result, self.cache_timeout)

        return result

    def get_user_display_name(self, user_id: str) -> str:
        """
        Get human-readable display name for a user.
        Falls back to 'User <uuid prefix>' if profile cannot be fetched.
        """
        profile = self.get_user_profile(user_id)
        if profile:
            first = profile.get('first_name', '')
            last = profile.get('last_name', '')
            full_name = f"{first} {last}".strip()
            return full_name or profile.get('username', str(user_id)[:8])
        return f"User {str(user_id)[:8]}"

    def get_user_email(self, user_id: str) -> Optional[str]:
        """Get email address for a user."""
        profile = self.get_user_profile(user_id)
        return profile.get('email') if profile else None
