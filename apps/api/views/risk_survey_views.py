"""
Risk Survey CRUD Views (SRS-FIX G-01)
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import RiskSurvey, RiskSurveyQuestion, RiskSurveyResponse
from apps.api.serializers.risk_serializers import (
    RiskSurveySerializer,
    RiskSurveyQuestionSerializer,
    RiskSurveyResponseSerializer,
)
from apps.api.permissions_jwt import CanManageInstitutionalRiskRegister, HasAnyPermission
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ── Risk Survey ────────────────────────────────────────────────────────────


class RiskSurveyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission([
                'grc:institutional_risk_register:manage',
                'grc:institutional_risk_register:approve',
            ]).has_permission(request, self):
                self.permission_denied(request, message='Risk survey permission required.')
        elif request.method == 'POST':
            if not CanManageInstitutionalRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def get(self, request):
        try:
            queryset = RiskSurvey.objects.select_related('fiscal_year').filter(is_active=True)

            fiscal_year = request.query_params.get('fiscal_year')
            survey_status = request.query_params.get('status')
            org_unit = request.query_params.get('org_unit')
            if fiscal_year:
                queryset = queryset.filter(fiscal_year_id=fiscal_year)
            if survey_status:
                queryset = queryset.filter(status=survey_status)
            if org_unit:
                queryset = queryset.filter(org_unit_id=org_unit)

            ordering = get_ordering_param(request, default='-created_at', allowed_fields=['created_at', 'title', 'opens_at'])
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskSurveySerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve risk surveys")
            return server_error_response(message="Failed to retrieve risk surveys")

    def post(self, request):
        try:
            serializer = RiskSurveySerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    survey = serializer.save(created_by=user_id, created_by_user=user_id)
                return Response(
                    {"success": True, "data": RiskSurveySerializer(survey).data, "message": "Risk survey created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create risk survey")
            return server_error_response(message="Failed to create risk survey")


class RiskSurveyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission([
                'grc:institutional_risk_register:manage',
                'grc:institutional_risk_register:approve',
            ]).has_permission(request, self):
                self.permission_denied(request, message='Risk survey permission required.')
        elif request.method in ('PATCH', 'DELETE'):
            if not CanManageInstitutionalRiskRegister().has_permission(request, self):
                self.permission_denied(request, message='grc:institutional_risk_register:manage required.')

    def get(self, request, pk):
        try:
            survey = get_object_or_404(RiskSurvey.objects.select_related('fiscal_year').prefetch_related('questions'), pk=pk)
            return Response({"success": True, "data": RiskSurveySerializer(survey).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve risk survey")
            return server_error_response(message="Failed to retrieve risk survey")

    def patch(self, request, pk):
        try:
            survey = get_object_or_404(RiskSurvey, pk=pk)
            serializer = RiskSurveySerializer(survey, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    survey.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RiskSurveySerializer(updated).data, "message": "Risk survey updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update risk survey")
            return server_error_response(message="Failed to update risk survey")

    def delete(self, request, pk):
        try:
            survey = get_object_or_404(RiskSurvey, pk=pk)
            with transaction.atomic():
                survey.is_active = False
                survey.save()
            return Response({"success": True, "message": "Risk survey deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete risk survey")
            return server_error_response(message="Failed to delete risk survey")


# ── Survey Questions (sub-resource) ────────────────────────────────────────


class RiskSurveyQuestionListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageInstitutionalRiskRegister]

    def get(self, request, pk):
        try:
            survey = get_object_or_404(RiskSurvey, pk=pk)
            queryset = RiskSurveyQuestion.objects.filter(survey=survey, is_active=True).order_by('sort_order')
            page_data = paginate_queryset(queryset, request)
            serializer = RiskSurveyQuestionSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve survey questions")
            return server_error_response(message="Failed to retrieve survey questions")

    def post(self, request, pk):
        try:
            survey = get_object_or_404(RiskSurvey, pk=pk)
            serializer = RiskSurveyQuestionSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    question = serializer.save(survey=survey, created_by=user_id)
                return Response(
                    {"success": True, "data": RiskSurveyQuestionSerializer(question).data, "message": "Survey question created"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create survey question")
            return server_error_response(message="Failed to create survey question")


class RiskSurveyQuestionDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageInstitutionalRiskRegister]

    def get(self, request, pk):
        try:
            question = get_object_or_404(RiskSurveyQuestion, pk=pk)
            return Response({"success": True, "data": RiskSurveyQuestionSerializer(question).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve survey question")
            return server_error_response(message="Failed to retrieve survey question")

    def patch(self, request, pk):
        try:
            question = get_object_or_404(RiskSurveyQuestion, pk=pk)
            serializer = RiskSurveyQuestionSerializer(question, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    question.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RiskSurveyQuestionSerializer(updated).data, "message": "Survey question updated"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update survey question")
            return server_error_response(message="Failed to update survey question")

    def delete(self, request, pk):
        try:
            question = get_object_or_404(RiskSurveyQuestion, pk=pk)
            with transaction.atomic():
                question.is_active = False
                question.save()
            return Response({"success": True, "message": "Survey question deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete survey question")
            return server_error_response(message="Failed to delete survey question")


# ── Survey Responses (sub-resource) ────────────────────────────────────────


class RiskSurveyResponseListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not HasAnyPermission([
                'grc:institutional_risk_register:manage',
                'grc:institutional_risk_register:approve',
            ]).has_permission(request, self):
                self.permission_denied(request, message='Survey response permission required.')

    def get(self, request, pk):
        try:
            survey = get_object_or_404(RiskSurvey, pk=pk)
            queryset = RiskSurveyResponse.objects.filter(survey=survey, is_active=True).order_by('-submitted_at')
            page_data = paginate_queryset(queryset, request)
            serializer = RiskSurveyResponseSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve survey responses")
            return server_error_response(message="Failed to retrieve survey responses")

    def post(self, request, pk):
        """Any authenticated user can submit a response to an open survey."""
        try:
            survey = get_object_or_404(RiskSurvey, pk=pk)
            if survey.status != 'open':
                return Response(
                    {"success": False, "error": {"message": "Survey is not open for responses", "code": "SURVEY_CLOSED"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            data = request.data.copy()
            data['respondent_id'] = str(user_id)
            serializer = RiskSurveyResponseSerializer(data=data)
            if serializer.is_valid():
                with transaction.atomic():
                    response_obj = serializer.save(survey=survey, created_by=user_id)
                return Response(
                    {"success": True, "data": RiskSurveyResponseSerializer(response_obj).data, "message": "Survey response submitted"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to submit survey response")
            return server_error_response(message="Failed to submit survey response")


class RiskSurveyResponseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:institutional_risk_register:manage',
            'grc:institutional_risk_register:approve',
        ]).has_permission(request, self):
            self.permission_denied(request, message='Survey response permission required.')

    def get(self, request, pk):
        try:
            response_obj = get_object_or_404(RiskSurveyResponse, pk=pk)
            return Response({"success": True, "data": RiskSurveyResponseSerializer(response_obj).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve survey response")
            return server_error_response(message="Failed to retrieve survey response")

    def delete(self, request, pk):
        try:
            response_obj = get_object_or_404(RiskSurveyResponse, pk=pk)
            with transaction.atomic():
                response_obj.is_active = False
                response_obj.save()
            return Response({"success": True, "message": "Survey response deleted"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete survey response")
            return server_error_response(message="Failed to delete survey response")
