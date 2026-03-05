from __future__ import annotations

from django.urls import path

from apps.api.views.health_view import health_check

urlpatterns = [
    path("", health_check, name="api-health-check"),
]
