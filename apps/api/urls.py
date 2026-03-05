"""
Main API URL configuration for GRC Service
"""

from django.urls import path, include

urlpatterns = [
    # Lookup data endpoints
    path('lookup/', include('apps.api.urls.lookup_urls')),
    
    # Configuration management endpoints
    path('config/', include('apps.api.urls.config_urls')),
    
    # Organizational data endpoints
    path('organizational/', include('apps.api.urls.organizational_urls')),
    
    # Core audit endpoints
    path('audit/', include('apps.api.urls.audit')),
]
