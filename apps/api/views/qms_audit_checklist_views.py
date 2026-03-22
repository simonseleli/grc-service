"""
Audit Checklist CRUD Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import AuditChecklist
from apps.api.serializers.risk_serializers import AuditChecklistSerializer
from apps.api.permissions_jwt import CanManageQMSChecklist
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


class AuditChecklistListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSChecklist]

    def get(self, request):
        try:
            queryset = AuditChecklist.objects.select_related('audit_plan').filter(is_active=True)

            plan = request.query_params.get('audit_plan')
            if plan:
                queryset = queryset.filter(audit_plan_id=plan)

            ordering = get_ordering_param(request, default='created_at', allowed_fields=['created_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = AuditChecklistSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve audit checklists")
            return server_error_response(message="Failed to retrieve audit checklists")

    def post(self, request):
        try:
            serializer = AuditChecklistSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    checklist = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": AuditChecklistSerializer(checklist).data, "message": "Checklist item created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create checklist item")
            return server_error_response(message="Failed to create checklist item")


class AuditChecklistDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageQMSChecklist]

    def get(self, request, pk):
        try:
            checklist = get_object_or_404(AuditChecklist.objects.select_related('audit_plan'), pk=pk)
            return Response({"success": True, "data": AuditChecklistSerializer(checklist).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve checklist item")
            return server_error_response(message="Failed to retrieve checklist item")

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial=False):
        try:
            checklist = get_object_or_404(AuditChecklist, pk=pk)
            serializer = AuditChecklistSerializer(checklist, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    checklist.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": AuditChecklistSerializer(updated).data, "message": "Checklist item updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update checklist item")
            return server_error_response(message="Failed to update checklist item")

    def delete(self, request, pk):
        try:
            checklist = get_object_or_404(AuditChecklist, pk=pk)
            with transaction.atomic():
                checklist.is_active = False
                checklist.save()
            return Response({"success": True, "message": "Checklist item deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete checklist item")
            return server_error_response(message="Failed to delete checklist item")
