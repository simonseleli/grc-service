"""
Risk Assessment Sheet CRUD Views
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.risk_entities import RiskAssessmentSheet
from apps.api.serializers.risk_serializers import RiskAssessmentSheetSerializer
from django.utils import timezone
from apps.api.permissions_jwt import (
    CanConductRiskAssessmentRM,
    CanReviewRiskAssessmentRM,
    HasAnyPermission,
)
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    validation_error_response,
    error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


class RiskAssessmentSheetListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanConductRiskAssessmentRM().has_permission(request, self) or
                    CanReviewRiskAssessmentRM().has_permission(request, self)):
                self.permission_denied(request, message='grc:risk_assessment:conduct or :review required.')
        elif request.method == 'POST':
            if not CanConductRiskAssessmentRM().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_assessment:conduct required.')

    def get(self, request):
        try:
            fiscal_year_id = request.query_params.get('fiscal_year')
            risk_champion_id = request.query_params.get('risk_champion')
            org_unit_id = request.query_params.get('org_unit_id')
            status_filter = request.query_params.get('status')

            queryset = RiskAssessmentSheet.objects.select_related(
                'risk_champion', 'fiscal_year', 'risk_category',
                'likelihood', 'impact', 'inherent_risk_level',
                'residual_likelihood', 'residual_impact', 'residual_risk_level',
            ).filter(is_active=True)

            if fiscal_year_id:
                queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
            if risk_champion_id:
                queryset = queryset.filter(risk_champion_id=risk_champion_id)
            if org_unit_id:
                queryset = queryset.filter(org_unit_id=org_unit_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'risk_title', 'inherent_risk_score'],
            )
            queryset = queryset.order_by(ordering)
            page_data = paginate_queryset(queryset, request)
            serializer = RiskAssessmentSheetSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data, count=page_data["total"],
                page=page_data["page"], page_size=page_data["page_size"],
            )
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve risk assessment sheets")
            return server_error_response(message="Failed to retrieve risk assessment sheets")

    def post(self, request):
        try:
            serializer = RiskAssessmentSheetSerializer(data=request.data)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    sheet = serializer.save(created_by=user_id)
                return Response(
                    {"success": True, "data": RiskAssessmentSheetSerializer(sheet).data, "message": "Risk assessment sheet created successfully"},
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to create risk assessment sheet")
            return server_error_response(message="Failed to create risk assessment sheet")


class RiskAssessmentSheetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanConductRiskAssessmentRM().has_permission(request, self) or
                    CanReviewRiskAssessmentRM().has_permission(request, self)):
                self.permission_denied(request, message='grc:risk_assessment:conduct or :review required.')
        elif request.method in ('PUT', 'PATCH', 'DELETE'):
            if not CanConductRiskAssessmentRM().has_permission(request, self):
                self.permission_denied(request, message='grc:risk_assessment:conduct required.')

    def get(self, request, pk):
        try:
            sheet = get_object_or_404(
                RiskAssessmentSheet.objects.select_related(
                    'risk_champion', 'fiscal_year', 'risk_category',
                    'likelihood', 'impact', 'inherent_risk_level',
                    'residual_likelihood', 'residual_impact', 'residual_risk_level',
                ), pk=pk,
            )
            return Response({"success": True, "data": RiskAssessmentSheetSerializer(sheet).data})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve risk assessment sheet")
            return server_error_response(message="Failed to retrieve risk assessment sheet")

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            sheet = get_object_or_404(RiskAssessmentSheet, pk=pk)
            serializer = RiskAssessmentSheetSerializer(sheet, data=request.data, partial=partial)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                if not user_id:
                    return Response(
                        {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                with transaction.atomic():
                    sheet.modified_by = user_id
                    updated = serializer.save()
                return Response({"success": True, "data": RiskAssessmentSheetSerializer(updated).data, "message": "Risk assessment sheet updated successfully"})
            return validation_error_response(errors=serializer.errors)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to update risk assessment sheet")
            return server_error_response(message="Failed to update risk assessment sheet")

    def delete(self, request, pk):
        try:
            sheet = get_object_or_404(RiskAssessmentSheet, pk=pk)
            with transaction.atomic():
                sheet.is_active = False
                sheet.save()
            return Response({"success": True, "message": "Risk assessment sheet deleted successfully"})
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to delete risk assessment sheet")
            return server_error_response(message="Failed to delete risk assessment sheet")


# ── GAP-15/28: RAS Status Transition Action Views ─────────────────────────────

_RAS_TRANSITIONS = {
    'draft': ['submitted_to_head'],
    'submitted_to_head': ['head_endorsed', 'returned_for_rework'],
    'head_endorsed': ['submitted_to_rmqam'],
    'submitted_to_rmqam': ['approved', 'returned_for_rework'],
    'returned_for_rework': ['submitted_to_head'],
    'approved': [],
}


def _ras_transition(request, pk, target_status, required_from, actor_field=None, extra_callback=None):
    """Shared helper for all RAS status transitions."""
    user_id = getattr(request.user, 'id', None)
    if not user_id:
        return Response(
            {"success": False, "error": {"message": "User not authenticated", "code": "AUTH_REQUIRED"}},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    try:
        with transaction.atomic():
            sheet = get_object_or_404(RiskAssessmentSheet.objects.select_for_update(), pk=pk)
            if sheet.status not in required_from:
                return error_response(
                    message=f"Cannot transition from '{sheet.status}' to '{target_status}'. "
                            f"Allowed from: {required_from}",
                    code="INVALID_STATUS_TRANSITION",
                )
            if extra_callback:
                err = extra_callback(request, sheet, user_id)
                if err:
                    return err
            sheet.status = target_status
            if actor_field:
                setattr(sheet, actor_field, user_id)
            sheet.modified_by = user_id
            sheet.save()
        return Response({
            "success": True,
            "data": RiskAssessmentSheetSerializer(sheet).data,
            "message": f"Risk assessment sheet status updated to '{target_status}'",
        })
    except Http404:
        raise
    except Exception as e:
        logger.exception("Failed to transition RAS to %s", target_status)
        return server_error_response(message=f"Failed to update risk assessment sheet status")


class RASSubmitView(APIView):
    """RC submits RAS to Head of Directorate. draft → submitted_to_head."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanConductRiskAssessmentRM().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_assessment:conduct required.')

    def post(self, request, pk):
        return _ras_transition(
            request, pk,
            target_status=RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD,
            required_from=[RiskAssessmentSheet.STATUS_DRAFT, RiskAssessmentSheet.STATUS_RETURNED_FOR_REWORK],
        )


class RASEndorseView(APIView):
    """Head endorses RAS. submitted_to_head → head_endorsed."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanReviewRiskAssessmentRM().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_assessment:review required.')

    def post(self, request, pk):
        return _ras_transition(
            request, pk,
            target_status=RiskAssessmentSheet.STATUS_HEAD_ENDORSED,
            required_from=[RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD],
        )


class RASSubmitToRMQAMView(APIView):
    """Head submits endorsed RAS to RMQAM. head_endorsed → submitted_to_rmqam."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanReviewRiskAssessmentRM().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_assessment:review required.')

    def post(self, request, pk):
        return _ras_transition(
            request, pk,
            target_status=RiskAssessmentSheet.STATUS_SUBMITTED_TO_RMQAM,
            required_from=[RiskAssessmentSheet.STATUS_HEAD_ENDORSED],
        )


class RASApproveView(APIView):
    """RMQAM approves RAS. submitted_to_rmqam → approved."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanReviewRiskAssessmentRM().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_assessment:review required.')

    def post(self, request, pk):
        return _ras_transition(
            request, pk,
            target_status=RiskAssessmentSheet.STATUS_APPROVED,
            required_from=[RiskAssessmentSheet.STATUS_SUBMITTED_TO_RMQAM],
        )


class RASReturnForReworkView(APIView):
    """RMQAM or Head returns RAS for rework. submitted_to_head|submitted_to_rmqam → returned_for_rework."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanReviewRiskAssessmentRM().has_permission(request, self):
            self.permission_denied(request, message='grc:risk_assessment:review required.')

    def post(self, request, pk):
        def set_rework_fields(req, sheet, user_id):
            review_comments = req.data.get('review_comments', '').strip()
            if not review_comments:
                return error_response(message="'review_comments' is required when returning for rework.", code="REVIEW_COMMENTS_REQUIRED")
            sheet.review_comments = review_comments
            sheet.rejected_at = timezone.now()
            return None

        return _ras_transition(
            request, pk,
            target_status=RiskAssessmentSheet.STATUS_RETURNED_FOR_REWORK,
            required_from=[
                RiskAssessmentSheet.STATUS_SUBMITTED_TO_HEAD,
                RiskAssessmentSheet.STATUS_SUBMITTED_TO_RMQAM,
            ],
            extra_callback=set_rework_fields,
        )
