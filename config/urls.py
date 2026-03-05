from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

from apps.api.views.health_view import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="service-health-check"),
    path("api/v1/grc/", include("apps.api.urls")),
]
