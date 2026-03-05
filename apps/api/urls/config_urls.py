"""
URL configuration for GRC configuration management endpoints
"""

from django.urls import path
from apps.api.views.config_views import (
    ConfigFiscalYearView, ConfigQuarterView, ConfigAuditSeverityView, ConfigFindingTypeView,
    ConfigRiskRatingView, ConfigSystemView
)

urlpatterns = [
    # Fiscal Year Configuration
    path('fiscal-years/', ConfigFiscalYearView.as_view(), name='config-fiscal-years'),
    path('fiscal-years/<int:fiscal_year_id>/', ConfigFiscalYearView.as_view(), name='config-fiscal-year-detail'),
    
    # Quarter Configuration (read-only - created automatically with fiscal years)
    path('quarters/', ConfigQuarterView.as_view(), name='config-quarters'),
    
    # Audit Severity Configuration
    path('audit-severities/', ConfigAuditSeverityView.as_view(), name='config-audit-severities'),
    path('audit-severities/<int:severity_id>/', ConfigAuditSeverityView.as_view(), name='config-audit-severity-detail'),
    
    # Finding Type Configuration
    path('finding-types/', ConfigFindingTypeView.as_view(), name='config-finding-types'),
    path('finding-types/<int:finding_type_id>/', ConfigFindingTypeView.as_view(), name='config-finding-type-detail'),
    
    # Risk Rating Configuration
    path('risk-ratings/', ConfigRiskRatingView.as_view(), name='config-risk-ratings'),
    path('risk-ratings/<int:risk_rating_id>/', ConfigRiskRatingView.as_view(), name='config-risk-rating-detail'),
    
    # System Configuration
    path('system/', ConfigSystemView.as_view(), name='config-system'),
]