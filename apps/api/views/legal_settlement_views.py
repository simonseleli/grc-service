"""
Legal Module — Settlement + Financial CRUD + Workflow Views
Entities: SettlementDefendant, SettlementPlaintiff, FinancialDefendant, FinancialPlaintiff
Uses LegalSettlementService with dual-entity `side` parameter.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    SettlementDefendant, SettlementPlaintiff,
    FinancialDefendant, FinancialPlaintiff,
    CaseDefendant, CasePlaintiff,
)
from apps.api.serializers.legal_serializers import (
    SettlementDefendantSerializer, SettlementPlaintiffSerializer,
    FinancialDefendantSerializer, FinancialPlaintiffSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalSettlement, CanManageLegalSettlement, CanApproveLegalSettlement,
    HasAnyPermission,
)
from apps.core.services.legal_settlement_service import LegalSettlementService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response, conflict_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Settlement Defendant CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementDefendantListCreateView(APIView):
    """
    GET  /legal/settlements/defendant/
    POST /legal/settlements/defendant/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalSettlement().has_permission(request, self) or
                    CanManageLegalSettlement().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')
        else:
            if not CanManageLegalSettlement().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def get(self, request):
        try:
            queryset = SettlementDefendant.objects.select_related('case_defendant').all()

            case_defendant = request.query_params.get('case_defendant')
            status_filter = request.query_params.get('status')
            if case_defendant:
                queryset = queryset.filter(case_defendant_id=case_defendant)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-settlement_date',
                allowed_fields=['settlement_date', 'status', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = SettlementDefendantSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='settlement_defendant',
            )
        except Exception as e:
            logger.exception("Failed to retrieve defendant settlements")
            return server_error_response(
                message="Failed to retrieve defendant settlements",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = SettlementDefendantSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # Business rule: parent case must be active (not closed)
            case = serializer.validated_data.get('case_defendant')
            if case and case.status == 'closed':
                return error_response(
                    message="Cannot create settlement on a closed case",
                    code="CASE_CLOSED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=SettlementDefendantSerializer(entity).data,
                message="Defendant settlement created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create defendant settlement")
            return server_error_response(
                message="Failed to create defendant settlement",
                details=str(e) if settings.DEBUG else None,
            )


class SettlementDefendantDetailView(APIView):
    """
    GET    /legal/settlements/defendant/<pk>/
    PUT    /legal/settlements/defendant/<pk>/
    PATCH  /legal/settlements/defendant/<pk>/
    DELETE /legal/settlements/defendant/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalSettlement().has_permission(request, self) or
                    CanManageLegalSettlement().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')
        else:
            if not CanManageLegalSettlement().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            SettlementDefendant.objects.select_related('case_defendant'), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=SettlementDefendantSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve defendant settlement")
            return server_error_response(
                message="Failed to retrieve defendant settlement",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'agreed':
                return error_response(
                    message="Agreed settlements cannot be modified",
                    code="SETTLEMENT_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = SettlementDefendantSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=SettlementDefendantSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update defendant settlement")
            return server_error_response(
                message="Failed to update defendant settlement",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Defendant settlement deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete defendant settlement")
            return server_error_response(
                message="Failed to delete defendant settlement",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Settlement Defendant Workflow
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementDefendantSubmitView(APIView):
    """POST /legal/settlements/defendant/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalSettlement().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            entity = get_object_or_404(SettlementDefendant, pk=pk)

            if entity.status != 'proposed':
                return error_response(
                    message=f"Only proposed settlements can be submitted. Current: '{entity.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            entity = LegalSettlementService().submit_for_approval(
                entity_id=str(pk), submitter_id=str(user_id), side='defendant',
            )

            return success_response(
                data=SettlementDefendantSerializer(entity).data,
                message="Settlement submitted for approval",
            )
        except Exception as e:
            logger.exception("Failed to submit defendant settlement")
            return server_error_response(
                message="Failed to submit defendant settlement",
                details=str(e) if settings.DEBUG else None,
            )


class SettlementDefendantWorkflowStatusView(APIView):
    """GET /legal/settlements/defendant/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalSettlement().has_permission(request, self) or
                CanManageLegalSettlement().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(SettlementDefendant, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})
        try:
            data = LegalSettlementService().get_workflow_status(str(pk), side='defendant')
        except Exception as exc:
            logger.error("Error fetching workflow status for SettlementDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow status",
                                  code="WORKFLOW_STATUS_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data=data)


class SettlementDefendantWorkflowHistoryView(APIView):
    """GET /legal/settlements/defendant/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalSettlement().has_permission(request, self) or
                CanManageLegalSettlement().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(SettlementDefendant, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})
        try:
            activities = LegalSettlementService().get_workflow_history(str(pk), side='defendant')
        except Exception as exc:
            logger.error("Error fetching workflow history for SettlementDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow history",
                                  code="WORKFLOW_HISTORY_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={
            'has_workflow': True,
            'workflow_plan_id': str(entity.workflow_plan_id),
            'activities': activities,
        })


class SettlementDefendantWorkflowActionView(APIView):
    """POST /legal/settlements/defendant/<pk>/workflow-action/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_settlement:manage', 'grc:legal_settlement:approve',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_settlement:manage or :approve required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        action_name = request.data.get('action')
        if not action_name:
            return error_response(message="'action' is required", code="ACTION_REQUIRED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        try:
            result = LegalSettlementService().advance_workflow_stage(
                entity_id=str(pk), action=action_name,
                actor_id=str(user_id), comment=request.data.get('comment', ''),
                side='defendant',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="WORKFLOW_ACTION_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error executing workflow action for SettlementDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to execute workflow action",
                                  code="WORKFLOW_ACTION_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)

        # GAP-10: Stamp the settlement agreement when the workflow completes
        if result.get('plan_status') == 'completed':
            from apps.core.utils.legal_document_stamp import stamp_legal_document
            try:
                entity = SettlementDefendant.objects.get(pk=pk)
                stamp_legal_document(
                    entity=entity,
                    document_id_field='agreement_document_id',
                    approver_id=str(user_id),
                    entity_type='settlement_defendant',
                    auth_token=request.auth,
                )
            except Exception as stamp_exc:
                logger.warning("GAP-10: Post-workflow stamp failed for SettlementDefendant %s: %s", pk, stamp_exc)

        return success_response(data=result)


class SettlementDefendantCancelWorkflowView(APIView):
    """POST /legal/settlements/defendant/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalSettlement().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            LegalSettlementService().cancel_workflow_plan(
                entity_id=str(pk), actor_id=str(user_id),
                reason=request.data.get('reason', ''), side='defendant',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error cancelling workflow for SettlementDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to cancel workflow",
                                  code="CANCEL_WORKFLOW_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Settlement Plaintiff CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementPlaintiffListCreateView(APIView):
    """
    GET  /legal/settlements/plaintiff/
    POST /legal/settlements/plaintiff/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalSettlement().has_permission(request, self) or
                    CanManageLegalSettlement().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')
        else:
            if not CanManageLegalSettlement().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def get(self, request):
        try:
            queryset = SettlementPlaintiff.objects.select_related('case_plaintiff').all()

            case_plaintiff = request.query_params.get('case_plaintiff')
            status_filter = request.query_params.get('status')
            if case_plaintiff:
                queryset = queryset.filter(case_plaintiff_id=case_plaintiff)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-settlement_date',
                allowed_fields=['settlement_date', 'status', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = SettlementPlaintiffSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='settlement_plaintiff',
            )
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff settlements")
            return server_error_response(
                message="Failed to retrieve plaintiff settlements",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = SettlementPlaintiffSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            case = serializer.validated_data.get('case_plaintiff')
            if case and case.status == 'closed':
                return error_response(
                    message="Cannot create settlement on a closed case",
                    code="CASE_CLOSED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=SettlementPlaintiffSerializer(entity).data,
                message="Plaintiff settlement created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create plaintiff settlement")
            return server_error_response(
                message="Failed to create plaintiff settlement",
                details=str(e) if settings.DEBUG else None,
            )


class SettlementPlaintiffDetailView(APIView):
    """
    GET    /legal/settlements/plaintiff/<pk>/
    PUT    /legal/settlements/plaintiff/<pk>/
    PATCH  /legal/settlements/plaintiff/<pk>/
    DELETE /legal/settlements/plaintiff/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalSettlement().has_permission(request, self) or
                    CanManageLegalSettlement().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')
        else:
            if not CanManageLegalSettlement().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            SettlementPlaintiff.objects.select_related('case_plaintiff'), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=SettlementPlaintiffSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff settlement")
            return server_error_response(
                message="Failed to retrieve plaintiff settlement",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'agreed':
                return error_response(
                    message="Agreed settlements cannot be modified",
                    code="SETTLEMENT_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = SettlementPlaintiffSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=SettlementPlaintiffSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update plaintiff settlement")
            return server_error_response(
                message="Failed to update plaintiff settlement",
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        try:
            entity = self._get_entity(pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Plaintiff settlement deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete plaintiff settlement")
            return server_error_response(
                message="Failed to delete plaintiff settlement",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Settlement Plaintiff Workflow
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementPlaintiffSubmitView(APIView):
    """POST /legal/settlements/plaintiff/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalSettlement().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            entity = get_object_or_404(SettlementPlaintiff, pk=pk)

            if entity.status != 'proposed':
                return error_response(
                    message=f"Only proposed settlements can be submitted. Current: '{entity.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            entity = LegalSettlementService().submit_for_approval(
                entity_id=str(pk), submitter_id=str(user_id), side='plaintiff',
            )

            return success_response(
                data=SettlementPlaintiffSerializer(entity).data,
                message="Settlement submitted for approval",
            )
        except Exception as e:
            logger.exception("Failed to submit plaintiff settlement")
            return server_error_response(
                message="Failed to submit plaintiff settlement",
                details=str(e) if settings.DEBUG else None,
            )


class SettlementPlaintiffWorkflowStatusView(APIView):
    """GET /legal/settlements/plaintiff/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalSettlement().has_permission(request, self) or
                CanManageLegalSettlement().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(SettlementPlaintiff, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})
        try:
            data = LegalSettlementService().get_workflow_status(str(pk), side='plaintiff')
        except Exception as exc:
            logger.error("Error fetching workflow status for SettlementPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow status",
                                  code="WORKFLOW_STATUS_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data=data)


class SettlementPlaintiffWorkflowHistoryView(APIView):
    """GET /legal/settlements/plaintiff/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalSettlement().has_permission(request, self) or
                CanManageLegalSettlement().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(SettlementPlaintiff, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})
        try:
            activities = LegalSettlementService().get_workflow_history(str(pk), side='plaintiff')
        except Exception as exc:
            logger.error("Error fetching workflow history for SettlementPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow history",
                                  code="WORKFLOW_HISTORY_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={
            'has_workflow': True,
            'workflow_plan_id': str(entity.workflow_plan_id),
            'activities': activities,
        })


class SettlementPlaintiffWorkflowActionView(APIView):
    """POST /legal/settlements/plaintiff/<pk>/workflow-action/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_settlement:manage', 'grc:legal_settlement:approve',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_settlement:manage or :approve required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        action_name = request.data.get('action')
        if not action_name:
            return error_response(message="'action' is required", code="ACTION_REQUIRED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        try:
            result = LegalSettlementService().advance_workflow_stage(
                entity_id=str(pk), action=action_name,
                actor_id=str(user_id), comment=request.data.get('comment', ''),
                side='plaintiff',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="WORKFLOW_ACTION_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error executing workflow action for SettlementPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to execute workflow action",
                                  code="WORKFLOW_ACTION_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)

        # GAP-10: Stamp the settlement agreement when the workflow completes
        if result.get('plan_status') == 'completed':
            from apps.core.utils.legal_document_stamp import stamp_legal_document
            try:
                entity = SettlementPlaintiff.objects.get(pk=pk)
                stamp_legal_document(
                    entity=entity,
                    document_id_field='agreement_document_id',
                    approver_id=str(user_id),
                    entity_type='settlement_plaintiff',
                    auth_token=request.auth,
                )
            except Exception as stamp_exc:
                logger.warning("GAP-10: Post-workflow stamp failed for SettlementPlaintiff %s: %s", pk, stamp_exc)

        return success_response(data=result)


class SettlementPlaintiffCancelWorkflowView(APIView):
    """POST /legal/settlements/plaintiff/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalSettlement().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            LegalSettlementService().cancel_workflow_plan(
                entity_id=str(pk), actor_id=str(user_id),
                reason=request.data.get('reason', ''), side='plaintiff',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error cancelling workflow for SettlementPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to cancel workflow",
                                  code="CANCEL_WORKFLOW_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Financial Defendant (read/update only — auto-created with case)
# ═══════════════════════════════════════════════════════════════════════════════

class FinancialDefendantDetailView(APIView):
    """
    GET   /legal/financials/defendant/{case_defendant_pk}/
    PATCH /legal/financials/defendant/{case_defendant_pk}/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalSettlement().has_permission(request, self) or
                    CanManageLegalSettlement().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')
        else:
            if not CanManageLegalSettlement().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def get(self, request, case_defendant_pk):
        try:
            entity = get_object_or_404(
                FinancialDefendant.objects.select_related('case_defendant'),
                case_defendant_id=case_defendant_pk,
            )
            return success_response(data=FinancialDefendantSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve defendant financials")
            return server_error_response(
                message="Failed to retrieve defendant financials",
                details=str(e) if settings.DEBUG else None,
            )

    def patch(self, request, case_defendant_pk):
        try:
            entity = get_object_or_404(
                FinancialDefendant, case_defendant_id=case_defendant_pk,
            )
            serializer = FinancialDefendantSerializer(entity, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=FinancialDefendantSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update defendant financials")
            return server_error_response(
                message="Failed to update defendant financials",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Financial Plaintiff (read/update only — auto-created with case)
# ═══════════════════════════════════════════════════════════════════════════════

class FinancialPlaintiffDetailView(APIView):
    """
    GET   /legal/financials/plaintiff/{case_plaintiff_pk}/
    PATCH /legal/financials/plaintiff/{case_plaintiff_pk}/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalSettlement().has_permission(request, self) or
                    CanManageLegalSettlement().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_settlement:view or :manage required.')
        else:
            if not CanManageLegalSettlement().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_settlement:manage required.')

    def get(self, request, case_plaintiff_pk):
        try:
            entity = get_object_or_404(
                FinancialPlaintiff.objects.select_related('case_plaintiff'),
                case_plaintiff_id=case_plaintiff_pk,
            )
            return success_response(data=FinancialPlaintiffSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff financials")
            return server_error_response(
                message="Failed to retrieve plaintiff financials",
                details=str(e) if settings.DEBUG else None,
            )

    def patch(self, request, case_plaintiff_pk):
        try:
            entity = get_object_or_404(
                FinancialPlaintiff, case_plaintiff_id=case_plaintiff_pk,
            )
            serializer = FinancialPlaintiffSerializer(entity, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=FinancialPlaintiffSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update plaintiff financials")
            return server_error_response(
                message="Failed to update plaintiff financials",
                details=str(e) if settings.DEBUG else None,
            )
