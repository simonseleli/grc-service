"""
URL configuration for organizational data endpoints
"""

from django.urls import path
from apps.api.views.organizational_views import (
    OrganizationalDataView, DirectorateListView, DepartmentListView,
    UnitListView, SectionListView, OrganizationalSyncView
)

urlpatterns = [
    # Organizational data endpoints
    path('organizational-data/', OrganizationalDataView.as_view(), name='organizational-data'),
    
    # Individual organizational level endpoints
    path('directorates/', DirectorateListView.as_view(), name='directorates'),
    path('departments/', DepartmentListView.as_view(), name='departments'),
    path('units/', UnitListView.as_view(), name='units'),
    path('sections/', SectionListView.as_view(), name='sections'),
    
    # Sync management
    path('sync/', OrganizationalSyncView.as_view(), name='organizational-sync'),
]