"""
Legal Module — Case CRUD + Workflow Views
Entities: CaseDefendant, CasePlaintiff (dual-entity via side parameter)
"""

import logging
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    CaseDefendant, CasePlaintiff, LegalCaseCounter,
    FinancialDefendant, FinancialPlaintiff,
)
from apps.api.serializers.legal_serializers import (
    CaseDefendantSerializer, CaseDefendantListSerializer,
    CasePlaintiffSerializer, CasePlaintiffListSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalCase, CanManageLegalCase, CanCloseLegalCase,
    HasAnyPermission,
)
from apps.core.services.legal_case_service import LegalCaseService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response, conflict_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)

MODEL_MAP = {
    'defendant': CaseDefendant,
    'plaintiff': CasePlaintiff,
}
SERIALIZER_MAP = {
    'defendant': CaseDefendantSerializer,
    'plaintiff': CasePlaintiffSerializer,
}
LIST_SERIALIZER_MAP = {
    'defendant': CaseDefendantListSerializer,
    'plaintiff': CasePlaintiffListSerializer,
}
LOCKED_STATUSES = ('closed',)


def _generate_case_reference(case_type: str) -> str:
    """Generate next sequential reference number for a case type."""
    now = datetime.now()
    year = now.year
    prefix = 'FCC/SUED' if case_type == 'defendant' else 'FCC/SUING'

    counter, _ = LegalCaseCounter.objects.select_for_update().get_or_create(
        case_type=case_type, year=year,
        defaults={'sequence': 0},
    )
    counter.sequence += 1
    counter.save(update_fields=['sequence'])
    return f"{prefix}/{year}/{counter.sequence:03d}"


# ═══════════════════════════════════════════════════════════════════════════════
# Case Defendant CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class CaseDefendantListCreateView(APIView):
    """
    GET  /legal/cases/defendant/
    POST /legal/cases/defendant/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalCase().has_permission(request, self) or
                    CanManageLegalCase().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_case:view or :manage required.')
        else:
            if not CanManageLegalCase().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_case:manage required.')

    def get(self, request):
        try:
            queryset = CaseDefendant.objects.select_related(
                'court_level', 'urgency_level', 'risk_level',
            ).filter(is_archived=False)

            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')
            include_archived = request.query_params.get('include_archived')
            if include_archived and include_archived.lower() == 'true':
                queryset = CaseDefendant.objects.select_related(
                    'court_level', 'urgency_level', 'risk_level',
                ).all()
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status', 'reference_number'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = CaseDefendantListSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='case_defendant',
            )
        except Exception as e:
            logger.exception("Failed to retrieve defendant cases")
            return server_error_response(
                message="Failed to retrieve defendant cases",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = CaseDefendantSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                reference_number = serializer.validated_data.get('reference_number', '').strip()
                if not reference_number:
                    reference_number = _generate_case_reference('defendant')

                entity = serializer.save(
                    created_by=user_id,
                    reference_number=reference_number,
                )
                # Auto-create financial record (SRS §4.9)
                FinancialDefendant.objects.create(
                    case_defendant=entity,
                    created_by=user_id,
                )

            return created_response(
                data=CaseDefendantSerializer(entity).data,
                message="Defendant case created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create defendant case")
            return server_error_response(
                message="Failed to create defendant case",
                details=str(e) if settings.DEBUG else None,
            )


class CaseDefendantDetailView(APIView):
    """
    GET    /legal/cases/defendant/<pk>/
    PUT    /legal/cases/defendant/<pk>/
    PATCH  /legal/cases/defendant/<pk>/
    DELETE /legal/cases/defendant/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalCase().has_permission(request, self) or
                    CanManageLegalCase().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_case:view or :manage required.')
        else:
            if not CanManageLegalCase().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_case:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            CaseDefendant.objects.select_related('court_level', 'urgency_level', 'risk_level'),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=CaseDefendantSerializer(entity).data)
        except Http404:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve defendant case")
            return server_error_response(
                message="Failed to retrieve defendant case",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status in LOCKED_STATUSES:
                return error_response(
                    message=f"Case is locked (status: {entity.status})",
                    code="CASE_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = CaseDefendantSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=CaseDefendantSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update defendant case")
            return server_error_response(
                message="Failed to update defendant case",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'closed':
                return error_response(
                    message="Cannot delete a closed case",
                    code="CASE_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])

            return deleted_response(message="Defendant case deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete defendant case")
            return server_error_response(
                message="Failed to delete defendant case",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Case Defendant Workflow Views
# ═══════════════════════════════════════════════════════════════════════════════

class CaseDefendantSubmitView(APIView):
    """POST /legal/cases/defendant/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            entity = get_object_or_404(CaseDefendant, pk=pk)

            if entity.status != 'new':
                return error_response(
                    message=f"Only new cases can be submitted. Current: '{entity.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            service = LegalCaseService()
            entity = service.submit_for_approval(
                entity_id=str(pk),
                submitter_id=str(user_id),
                side='defendant',
            )

            return success_response(
                data=CaseDefendantSerializer(entity).data,
                message="Defendant case submitted for workflow",
            )
        except Exception as e:
            logger.exception("Failed to submit defendant case")
            return server_error_response(
                message="Failed to submit defendant case",
                details=str(e) if settings.DEBUG else None,
            )


class CaseDefendantWorkflowStatusView(APIView):
    """GET /legal/cases/defendant/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalCase().has_permission(request, self) or
                CanManageLegalCase().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_case:view or :manage required.')

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(CaseDefendant, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})

        try:
            data = LegalCaseService().get_workflow_status(str(pk), side='defendant')
        except Exception as exc:
            logger.error("Error fetching workflow status for CaseDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to retrieve workflow status",
                code="WORKFLOW_STATUS_FAILED",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data=data)


class CaseDefendantWorkflowHistoryView(APIView):
    """GET /legal/cases/defendant/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalCase().has_permission(request, self) or
                CanManageLegalCase().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_case:view or :manage required.')

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(CaseDefendant, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})

        try:
            activities = LegalCaseService().get_workflow_history(str(pk), side='defendant')
        except Exception as exc:
            logger.error("Error fetching workflow history for CaseDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to retrieve workflow history",
                code="WORKFLOW_HISTORY_FAILED",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data={
            'has_workflow': True,
            'workflow_plan_id': str(entity.workflow_plan_id),
            'activities': activities,
        })


class CaseDefendantWorkflowActionView(APIView):
    """POST /legal/cases/defendant/<pk>/workflow-action/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_case:manage', 'grc:legal_case:close',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:manage or :close required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        action_name = request.data.get('action')
        if not action_name:
            return error_response(
                message="'action' is required", code="ACTION_REQUIRED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = LegalCaseService().advance_workflow_stage(
                entity_id=str(pk),
                action=action_name,
                actor_id=str(user_id),
                comment=request.data.get('comment', ''),
                side='defendant',
            )
        except ValueError as exc:
            return error_response(
                message=str(exc), code="WORKFLOW_ACTION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error executing workflow action for CaseDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to execute workflow action",
                code="WORKFLOW_ACTION_ERROR",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data=result)


class CaseDefendantCancelWorkflowView(APIView):
    """POST /legal/cases/defendant/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            LegalCaseService().cancel_workflow_plan(
                entity_id=str(pk),
                actor_id=str(user_id),
                reason=request.data.get('reason', ''),
                side='defendant',
            )
        except ValueError as exc:
            return error_response(
                message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error cancelling workflow for CaseDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to cancel workflow",
                code="CANCEL_WORKFLOW_ERROR",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Case Plaintiff CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class CasePlaintiffListCreateView(APIView):
    """
    GET  /legal/cases/plaintiff/
    POST /legal/cases/plaintiff/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalCase().has_permission(request, self) or
                    CanManageLegalCase().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_case:view or :manage required.')
        else:
            if not CanManageLegalCase().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_case:manage required.')

    def get(self, request):
        try:
            queryset = CasePlaintiff.objects.select_related(
                'court_level', 'urgency_level', 'risk_level',
            ).filter(is_archived=False)

            status_filter = request.query_params.get('status')
            is_active = request.query_params.get('is_active')
            include_archived = request.query_params.get('include_archived')
            if include_archived and include_archived.lower() == 'true':
                queryset = CasePlaintiff.objects.select_related(
                    'court_level', 'urgency_level', 'risk_level',
                ).all()
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status', 'reference_number'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = CasePlaintiffListSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='case_plaintiff',
            )
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff cases")
            return server_error_response(
                message="Failed to retrieve plaintiff cases",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = CasePlaintiffSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                reference_number = serializer.validated_data.get('reference_number', '').strip()
                if not reference_number:
                    reference_number = _generate_case_reference('plaintiff')

                entity = serializer.save(
                    created_by=user_id,
                    reference_number=reference_number,
                )
                # Auto-create financial record (SRS §4.9)
                FinancialPlaintiff.objects.create(
                    case_plaintiff=entity,
                    created_by=user_id,
                )

            return created_response(
                data=CasePlaintiffSerializer(entity).data,
                message="Plaintiff case created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create plaintiff case")
            return server_error_response(
                message="Failed to create plaintiff case",
                details=str(e) if settings.DEBUG else None,
            )


class CasePlaintiffDetailView(APIView):
    """
    GET    /legal/cases/plaintiff/<pk>/
    PUT    /legal/cases/plaintiff/<pk>/
    PATCH  /legal/cases/plaintiff/<pk>/
    DELETE /legal/cases/plaintiff/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalCase().has_permission(request, self) or
                    CanManageLegalCase().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_case:view or :manage required.')
        else:
            if not CanManageLegalCase().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_case:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            CasePlaintiff.objects.select_related('court_level', 'urgency_level', 'risk_level'),
            pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=CasePlaintiffSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff case")
            return server_error_response(
                message="Failed to retrieve plaintiff case",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status in LOCKED_STATUSES:
                return error_response(
                    message=f"Case is locked (status: {entity.status})",
                    code="CASE_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = CasePlaintiffSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=CasePlaintiffSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update plaintiff case")
            return server_error_response(
                message="Failed to update plaintiff case",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'closed':
                return error_response(
                    message="Cannot delete a closed case",
                    code="CASE_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])

            return deleted_response(message="Plaintiff case deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete plaintiff case")
            return server_error_response(
                message="Failed to delete plaintiff case",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Case Plaintiff Workflow Views
# ═══════════════════════════════════════════════════════════════════════════════

class CasePlaintiffSubmitView(APIView):
    """POST /legal/cases/plaintiff/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            entity = get_object_or_404(CasePlaintiff, pk=pk)

            if entity.status != 'new':
                return error_response(
                    message=f"Only new cases can be submitted. Current: '{entity.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            service = LegalCaseService()
            entity = service.submit_for_approval(
                entity_id=str(pk),
                submitter_id=str(user_id),
                side='plaintiff',
            )

            return success_response(
                data=CasePlaintiffSerializer(entity).data,
                message="Plaintiff case submitted for workflow",
            )
        except Exception as e:
            logger.exception("Failed to submit plaintiff case")
            return server_error_response(
                message="Failed to submit plaintiff case",
                details=str(e) if settings.DEBUG else None,
            )


class CasePlaintiffWorkflowStatusView(APIView):
    """GET /legal/cases/plaintiff/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalCase().has_permission(request, self) or
                CanManageLegalCase().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_case:view or :manage required.')

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(CasePlaintiff, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})

        try:
            data = LegalCaseService().get_workflow_status(str(pk), side='plaintiff')
        except Exception as exc:
            logger.error("Error fetching workflow status for CasePlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to retrieve workflow status",
                code="WORKFLOW_STATUS_FAILED",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data=data)


class CasePlaintiffWorkflowHistoryView(APIView):
    """GET /legal/cases/plaintiff/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalCase().has_permission(request, self) or
                CanManageLegalCase().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_case:view or :manage required.')

    def get(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        entity = get_object_or_404(CasePlaintiff, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})

        try:
            activities = LegalCaseService().get_workflow_history(str(pk), side='plaintiff')
        except Exception as exc:
            logger.error("Error fetching workflow history for CasePlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to retrieve workflow history",
                code="WORKFLOW_HISTORY_FAILED",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data={
            'has_workflow': True,
            'workflow_plan_id': str(entity.workflow_plan_id),
            'activities': activities,
        })


class CasePlaintiffWorkflowActionView(APIView):
    """POST /legal/cases/plaintiff/<pk>/workflow-action/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_case:manage', 'grc:legal_case:close',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:manage or :close required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        action_name = request.data.get('action')
        if not action_name:
            return error_response(
                message="'action' is required", code="ACTION_REQUIRED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = LegalCaseService().advance_workflow_stage(
                entity_id=str(pk),
                action=action_name,
                actor_id=str(user_id),
                comment=request.data.get('comment', ''),
                side='plaintiff',
            )
        except ValueError as exc:
            return error_response(
                message=str(exc), code="WORKFLOW_ACTION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error executing workflow action for CasePlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to execute workflow action",
                code="WORKFLOW_ACTION_ERROR",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data=result)


class CasePlaintiffCancelWorkflowView(APIView):
    """POST /legal/cases/plaintiff/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            LegalCaseService().cancel_workflow_plan(
                entity_id=str(pk),
                actor_id=str(user_id),
                reason=request.data.get('reason', ''),
                side='plaintiff',
            )
        except ValueError as exc:
            return error_response(
                message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Error cancelling workflow for CasePlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to cancel workflow",
                code="CANCEL_WORKFLOW_ERROR",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Archive / Unarchive endpoints (GAP-14)
# ═══════════════════════════════════════════════════════════════════════════════

ARCHIVE_MODEL_MAP = {
    'defendant': CaseDefendant,
    'plaintiff': CasePlaintiff,
}


class CaseArchiveView(APIView):
    """POST /cases/<side>/<pk>/archive/ — soft-archive a closed case."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:manage required.')

    def post(self, request, side, pk):
        Model = ARCHIVE_MODEL_MAP.get(side)
        if Model is None:
            return error_response(
                message=f"Invalid case side: {side}",
                code="INVALID_SIDE",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            entity = get_object_or_404(Model, pk=pk, is_active=True)
        except Exception:
            return error_response(
                message="Case not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if entity.status != 'closed':
            return error_response(
                message="Only closed cases can be archived",
                code="NOT_CLOSED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if entity.is_archived:
            return error_response(
                message="Case is already archived",
                code="ALREADY_ARCHIVED",
                status_code=status.HTTP_409_CONFLICT,
            )

        from django.utils import timezone
        entity.is_archived = True
        entity.archived_at = timezone.now()
        entity.archived_by = getattr(request.user, 'id', None)
        entity.save(update_fields=['is_archived', 'archived_at', 'archived_by', 'updated_at'])

        return success_response(
            data={'id': str(entity.id), 'is_archived': True, 'archived_at': str(entity.archived_at)},
        )


class CaseUnarchiveView(APIView):
    """POST /cases/<side>/<pk>/unarchive/ — restore an archived case."""
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalCase().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_case:manage required.')

    def post(self, request, side, pk):
        Model = ARCHIVE_MODEL_MAP.get(side)
        if Model is None:
            return error_response(
                message=f"Invalid case side: {side}",
                code="INVALID_SIDE",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            entity = get_object_or_404(Model, pk=pk, is_active=True)
        except Exception:
            return error_response(
                message="Case not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not entity.is_archived:
            return error_response(
                message="Case is not archived",
                code="NOT_ARCHIVED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        entity.is_archived = False
        entity.archived_at = None
        entity.archived_by = None
        entity.save(update_fields=['is_archived', 'archived_at', 'archived_by', 'updated_at'])

        return success_response(
            data={'id': str(entity.id), 'is_archived': False},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Case Report / Timeline (SRS §4.13)
# ═══════════════════════════════════════════════════════════════════════════════

def _to_iso(value) -> str:
    """Normalise a date or datetime to an ISO 8601 string for unified sorting."""
    if isinstance(value, datetime):
        return value.isoformat()
    return f"{value}T00:00:00"  # DateField → midnight on that day


class CaseReportView(APIView):
    """
    GET /legal/cases/<str:side>/<uuid:pk>/report/
    Returns a chronological timeline of all case milestone events aggregated
    from Hearings, Filings, Settlements, Judgments, Appeals, and Directives.
    SRS §4.13 — available to all authorised users with view/manage access.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalCase().has_permission(request, self) or
                CanManageLegalCase().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_case:view or :manage required.')

    def get(self, request, side, pk):
        Model = MODEL_MAP.get(side)
        if Model is None:
            return error_response(
                message=f"Invalid case side: '{side}'. Use 'defendant' or 'plaintiff'.",
                code="INVALID_SIDE",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        case = get_object_or_404(Model, pk=pk)

        try:
            events = self._build_events(case, side)
        except Exception as e:
            logger.exception("Failed to build report for %s case %s", side, pk)
            return server_error_response(
                message="Failed to generate case report",
                details=str(e) if settings.DEBUG else None,
            )

        return success_response(data={
            'case_id': str(case.id),
            'case_type': side,
            'reference_number': case.reference_number,
            'events': events,
        })

    def _build_events(self, case, side: str) -> list:
        events = []

        # 1. Case registration
        events.append({
            'id': f"case_registered_{case.id}",
            'event_type': 'case_registered',
            'title': 'Case Registered',
            'detail': f"Reference: {case.reference_number}",
            'timestamp': _to_iso(case.created_at),
        })

        # 2. Hearings
        for hearing in case.hearings.all():
            events.append({
                'id': str(hearing.id),
                'event_type': 'hearing_held',
                'title': 'Hearing Held',
                'detail': f"Court: {hearing.court or 'N/A'} — {hearing.get_status_display()}",
                'timestamp': _to_iso(hearing.hearing_date),
            })

        # 3. Filings
        for filing in case.filings.all():
            events.append({
                'id': str(filing.id),
                'event_type': 'filing_submitted',
                'title': 'Filing Submitted',
                'detail': f"{filing.get_filing_type_display()}: {filing.title}",
                'timestamp': _to_iso(filing.created_at),
            })

        # 4. Settlements
        for settlement in case.settlements.all():
            events.append({
                'id': str(settlement.id),
                'event_type': 'settlement_recorded',
                'title': 'Settlement Recorded',
                'detail': f"Status: {settlement.get_status_display()}",
                'timestamp': _to_iso(settlement.settlement_date),
            })

        # 5. Judgments + linked appeals
        for judgment in case.judgments.select_related('appeal').all():
            events.append({
                'id': str(judgment.id),
                'event_type': 'judgment_recorded',
                'title': 'Judgment Recorded',
                'detail': f"Outcome: {judgment.get_outcome_display()}",
                'timestamp': _to_iso(judgment.judgment_date),
            })
            try:
                appeal = judgment.appeal
                events.append({
                    'id': str(appeal.id),
                    'event_type': 'appeal_filed',
                    'title': 'Appeal Filed',
                    'detail': f"Status: {appeal.get_status_display()}",
                    'timestamp': _to_iso(appeal.appeal_date),
                })
            except Exception:
                pass  # no appeal on this judgment

        # 6. Litigation directives
        for directive in case.litigation_directives.all():
            events.append({
                'id': str(directive.id),
                'event_type': 'directive_issued',
                'title': 'Directive Issued',
                'detail': directive.instruction[:120] if directive.instruction else '',
                'timestamp': _to_iso(directive.issue_date),
            })

        # 7. Case closure
        if case.status == 'closed':
            events.append({
                'id': f"case_closed_{case.id}",
                'event_type': 'case_closed',
                'title': 'Case Closed',
                'detail': '',
                'timestamp': _to_iso(case.updated_at),
            })

        events.sort(key=lambda e: e['timestamp'])
        return events
