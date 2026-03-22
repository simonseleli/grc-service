from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("health/", include("apps.api.urls.health")),
    path("config/", include("apps.api.urls.config_urls")),
    path("organizational/", include("apps.api.urls.organizational_urls")),
    path("audit/", include("apps.api.urls.audit")),
    path("legal/", include("apps.api.urls.legal")),
    path("risk/", include("apps.api.urls.risk")),
]
