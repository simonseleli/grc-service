"""
Core services for GRC service
"""

from .corporate_sync import CorporateServiceClient, OrganizationalSyncService

__all__ = [
    'CorporateServiceClient',
    'OrganizationalSyncService',
]