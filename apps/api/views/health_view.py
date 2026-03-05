from __future__ import annotations

from django.http import JsonResponse


def health_check(request):  # pragma: no cover - trivial
    return JsonResponse({
        "status": "healthy",
        "service": "grc-service",
    })
