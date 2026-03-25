"""
Risk Knowledge Base CRUD Views (SRS-FIX G-02)
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import RiskKnowledgeBase
from apps.api.serializers.risk_serializers import RiskKnowledgeBaseSerializer
from apps.api.permissions_jwt import CanManageInstitutionalRiskRegister, HasAnyPermission
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


class RiskKnowledgeBaseListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission([
                'grc:institutional_risk_register:manage',
                'grc:institutional_risk_register:approve',
            ]).has_permission(request, self):
                self.permission_denied(request, message='Risk knowledge base permission required.')
        elif request.method == 'POST':
            if not CanManageInstitutionalRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def get(self, request):
        try:
            queryset = RiskKnowledgeBase.objects.select_related('fiscal_year').filter(is_active=True)

            source_type = request.query_params.get('source_type')
            fiscal_year = request.query_params.get('fiscal_year')
            if source_type:
                queryset = queryset.filter(source_type=source_type)
            if fiscal_year:
                queryset = queryset.filter(fiscal_year_id=fiscal_year)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'title'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskKnowledgeBaseSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve knowledge base entries")
            return server_error_response(message="Failed to retrieve knowledge base entries")

    def post(self, request):
        try:
            serializer = RiskKnowledgeBaseSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    entry = serializer.save(created_by=user_id, contributed_by=user_id)
                return Response(
                    {"success": True, "data": RiskKnowledgeBaseSerializer(entry).data, "message": "Knowledge base entry created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create knowledge base entry")
            return server_error_response(message="Failed to create knowledge base entry")


class RiskKnowledgeBaseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission([
                'grc:institutional_risk_register:manage',
                'grc:institutional_risk_register:approve',
            ]).has_permission(request, self):
                self.permission_denied(request, message='Risk knowledge base permission required.')
        elif request.method in ('PATCH', 'DELETE'):
            if not CanManageInstitutionalRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def get(self, request, pk):
        try:
            entry = get_object_or_404(RiskKnowledgeBase.objects.select_related('fiscal_year'), pk=pk)
            return Response({"success": True, "data": RiskKnowledgeBaseSerializer(entry).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve knowledge base entry")
            return server_error_response(message="Failed to retrieve knowledge base entry")

    def patch(self, request, pk):
        try:
            entry = get_object_or_404(RiskKnowledgeBase, pk=pk)
            serializer = RiskKnowledgeBaseSerializer(entry, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    entry.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RiskKnowledgeBaseSerializer(updated).data, "message": "Knowledge base entry updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update knowledge base entry")
            return server_error_response(message="Failed to update knowledge base entry")

    def delete(self, request, pk):
        try:
            entry = get_object_or_404(RiskKnowledgeBase, pk=pk)
            with transaction.atomic():
                entry.is_active = False
                entry.save()
            return Response({"success": True, "message": "Knowledge base entry deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete knowledge base entry")
            return server_error_response(message="Failed to delete knowledge base entry")
