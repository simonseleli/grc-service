"""
Legal Module — Judgment + Appeal CRUD + Workflow Views
Entities: JudgmentDefendant, JudgmentPlaintiff, AppealDefendant, AppealPlaintiff
Uses LegalJudgmentService with dual-entity `side` parameter.
Appeals are auto-created (OneToOne), so only GET/PATCH — no POST/DELETE.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    JudgmentDefendant, JudgmentPlaintiff,
    AppealDefendant, AppealPlaintiff,
)
from apps.api.serializers.legal_serializers import (
    JudgmentDefendantSerializer, JudgmentPlaintiffSerializer,
    AppealDefendantSerializer, AppealPlaintiffSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalJudgment, CanManageLegalJudgment, CanRecordLegalJudgment,
    CanViewLegalAppeal, CanManageLegalAppeal,
    HasAnyPermission,
)
from apps.core.services.legal_judgment_service import LegalJudgmentService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response, conflict_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Judgment Defendant CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class JudgmentDefendantListCreateView(APIView):
    """
    GET  /legal/judgments/defendant/
    POST /legal/judgments/defendant/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalJudgment().has_permission(request, self) or
                    CanManageLegalJudgment().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_judgment:view or :manage required.')
        else:
            if not HasAnyPermission([
                'grc:legal_judgment:manage', 'grc:legal_judgment:record',
            ]).has_permission(request, self):
                self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

    def get(self, request):
        try:
            queryset = JudgmentDefendant.objects.select_related('case_defendant').all()

            case_defendant = request.query_params.get('case_defendant')
            outcome = request.query_params.get('outcome')
            dg_decision = request.query_params.get('dg_decision')
            if case_defendant:
                queryset = queryset.filter(case_defendant_id=case_defendant)
            if outcome:
                queryset = queryset.filter(outcome=outcome)
            if dg_decision:
                queryset = queryset.filter(dg_decision=dg_decision)

            ordering = get_ordering_param(
                request, default='-judgment_date',
                allowed_fields=['judgment_date', 'outcome', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = JudgmentDefendantSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='judgment_defendant',
            )
        except Exception as e:
            logger.exception("Failed to retrieve defendant judgments")
            return server_error_response(
                message="Failed to retrieve defendant judgments",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = JudgmentDefendantSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            case = serializer.validated_data.get('case_defendant')
            if case and case.status == 'closed':
                return error_response(
                    message="Cannot record judgment on a closed case",
                    code="CASE_CLOSED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=JudgmentDefendantSerializer(entity).data,
                message="Defendant judgment recorded successfully",
            )
        except Exception as e:
            logger.exception("Failed to create defendant judgment")
            return server_error_response(
                message="Failed to create defendant judgment",
                details=str(e) if settings.DEBUG else None,
            )


class JudgmentDefendantDetailView(APIView):
    """
    GET    /legal/judgments/defendant/<pk>/
    PUT    /legal/judgments/defendant/<pk>/
    PATCH  /legal/judgments/defendant/<pk>/
    DELETE /legal/judgments/defendant/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalJudgment().has_permission(request, self) or
                    CanManageLegalJudgment().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_judgment:view or :manage required.')
        else:
            if not HasAnyPermission([
                'grc:legal_judgment:manage', 'grc:legal_judgment:record',
            ]).has_permission(request, self):
                self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            JudgmentDefendant.objects.select_related('case_defendant'), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=JudgmentDefendantSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve defendant judgment")
            return server_error_response(
                message="Failed to retrieve defendant judgment",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            serializer = JudgmentDefendantSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=JudgmentDefendantSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update defendant judgment")
            return server_error_response(
                message="Failed to update defendant judgment",
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
            return deleted_response(message="Defendant judgment deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete defendant judgment")
            return server_error_response(
                message="Failed to delete defendant judgment",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Judgment Defendant Workflow
# ═══════════════════════════════════════════════════════════════════════════════

class JudgmentDefendantSubmitView(APIView):
    """POST /legal/judgments/defendant/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_judgment:manage', 'grc:legal_judgment:record',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            entity = get_object_or_404(JudgmentDefendant, pk=pk)

            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            entity = LegalJudgmentService().submit_for_approval(
                entity_id=str(pk), submitter_id=str(user_id), side='defendant',
            )

            return success_response(
                data=JudgmentDefendantSerializer(entity).data,
                message="Judgment submitted for approval",
            )
        except Exception as e:
            logger.exception("Failed to submit defendant judgment")
            return server_error_response(
                message="Failed to submit defendant judgment",
                details=str(e) if settings.DEBUG else None,
            )


class JudgmentDefendantWorkflowStatusView(APIView):
    """GET /legal/judgments/defendant/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalJudgment().has_permission(request, self) or
                CanManageLegalJudgment().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_judgment:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(JudgmentDefendant, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})
        try:
            data = LegalJudgmentService().get_workflow_status(str(pk), side='defendant')
        except Exception as exc:
            logger.error("Error fetching workflow status for JudgmentDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow status",
                                  code="WORKFLOW_STATUS_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data=data)


class JudgmentDefendantWorkflowHistoryView(APIView):
    """GET /legal/judgments/defendant/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalJudgment().has_permission(request, self) or
                CanManageLegalJudgment().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_judgment:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(JudgmentDefendant, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})
        try:
            activities = LegalJudgmentService().get_workflow_history(str(pk), side='defendant')
        except Exception as exc:
            logger.error("Error fetching workflow history for JudgmentDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow history",
                                  code="WORKFLOW_HISTORY_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={
            'has_workflow': True,
            'workflow_plan_id': str(entity.workflow_plan_id),
            'activities': activities,
        })


class JudgmentDefendantWorkflowActionView(APIView):
    """POST /legal/judgments/defendant/<pk>/workflow-action/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_judgment:manage', 'grc:legal_judgment:record',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

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
            result = LegalJudgmentService().advance_workflow_stage(
                entity_id=str(pk), action=action_name,
                actor_id=str(user_id), comment=request.data.get('comment', ''),
                side='defendant',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="WORKFLOW_ACTION_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error executing workflow action for JudgmentDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to execute workflow action",
                                  code="WORKFLOW_ACTION_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)

        # GAP-10: Stamp the judgment document when the workflow completes
        if result.get('plan_status') == 'completed':
            from apps.core.utils.legal_document_stamp import stamp_legal_document
            try:
                entity = JudgmentDefendant.objects.get(pk=pk)
                stamp_legal_document(
                    entity=entity,
                    document_id_field='document_id',
                    approver_id=str(user_id),
                    entity_type='judgment_defendant',
                    auth_token=request.auth,
                )
            except Exception as stamp_exc:
                logger.warning("GAP-10: Post-workflow stamp failed for JudgmentDefendant %s: %s", pk, stamp_exc)

        return success_response(data=result)


class JudgmentDefendantCancelWorkflowView(APIView):
    """POST /legal/judgments/defendant/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalJudgment().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_judgment:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            LegalJudgmentService().cancel_workflow_plan(
                entity_id=str(pk), actor_id=str(user_id),
                reason=request.data.get('reason', ''), side='defendant',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error cancelling workflow for JudgmentDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to cancel workflow",
                                  code="CANCEL_WORKFLOW_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Judgment Plaintiff CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class JudgmentPlaintiffListCreateView(APIView):
    """
    GET  /legal/judgments/plaintiff/
    POST /legal/judgments/plaintiff/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalJudgment().has_permission(request, self) or
                    CanManageLegalJudgment().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_judgment:view or :manage required.')
        else:
            if not HasAnyPermission([
                'grc:legal_judgment:manage', 'grc:legal_judgment:record',
            ]).has_permission(request, self):
                self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

    def get(self, request):
        try:
            queryset = JudgmentPlaintiff.objects.select_related('case_plaintiff').all()

            case_plaintiff = request.query_params.get('case_plaintiff')
            outcome = request.query_params.get('outcome')
            dg_decision = request.query_params.get('dg_decision')
            if case_plaintiff:
                queryset = queryset.filter(case_plaintiff_id=case_plaintiff)
            if outcome:
                queryset = queryset.filter(outcome=outcome)
            if dg_decision:
                queryset = queryset.filter(dg_decision=dg_decision)

            ordering = get_ordering_param(
                request, default='-judgment_date',
                allowed_fields=['judgment_date', 'outcome', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = JudgmentPlaintiffSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='judgment_plaintiff',
            )
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff judgments")
            return server_error_response(
                message="Failed to retrieve plaintiff judgments",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = JudgmentPlaintiffSerializer(data=request.data)
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
                    message="Cannot record judgment on a closed case",
                    code="CASE_CLOSED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=JudgmentPlaintiffSerializer(entity).data,
                message="Plaintiff judgment recorded successfully",
            )
        except Exception as e:
            logger.exception("Failed to create plaintiff judgment")
            return server_error_response(
                message="Failed to create plaintiff judgment",
                details=str(e) if settings.DEBUG else None,
            )


class JudgmentPlaintiffDetailView(APIView):
    """
    GET    /legal/judgments/plaintiff/<pk>/
    PUT    /legal/judgments/plaintiff/<pk>/
    PATCH  /legal/judgments/plaintiff/<pk>/
    DELETE /legal/judgments/plaintiff/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalJudgment().has_permission(request, self) or
                    CanManageLegalJudgment().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_judgment:view or :manage required.')
        else:
            if not HasAnyPermission([
                'grc:legal_judgment:manage', 'grc:legal_judgment:record',
            ]).has_permission(request, self):
                self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            JudgmentPlaintiff.objects.select_related('case_plaintiff'), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=JudgmentPlaintiffSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff judgment")
            return server_error_response(
                message="Failed to retrieve plaintiff judgment",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            serializer = JudgmentPlaintiffSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=JudgmentPlaintiffSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update plaintiff judgment")
            return server_error_response(
                message="Failed to update plaintiff judgment",
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
            return deleted_response(message="Plaintiff judgment deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete plaintiff judgment")
            return server_error_response(
                message="Failed to delete plaintiff judgment",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Judgment Plaintiff Workflow
# ═══════════════════════════════════════════════════════════════════════════════

class JudgmentPlaintiffSubmitView(APIView):
    """POST /legal/judgments/plaintiff/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_judgment:manage', 'grc:legal_judgment:record',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            entity = get_object_or_404(JudgmentPlaintiff, pk=pk)

            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            entity = LegalJudgmentService().submit_for_approval(
                entity_id=str(pk), submitter_id=str(user_id), side='plaintiff',
            )

            return success_response(
                data=JudgmentPlaintiffSerializer(entity).data,
                message="Judgment submitted for approval",
            )
        except Exception as e:
            logger.exception("Failed to submit plaintiff judgment")
            return server_error_response(
                message="Failed to submit plaintiff judgment",
                details=str(e) if settings.DEBUG else None,
            )


class JudgmentPlaintiffWorkflowStatusView(APIView):
    """GET /legal/judgments/plaintiff/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalJudgment().has_permission(request, self) or
                CanManageLegalJudgment().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_judgment:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(JudgmentPlaintiff, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})
        try:
            data = LegalJudgmentService().get_workflow_status(str(pk), side='plaintiff')
        except Exception as exc:
            logger.error("Error fetching workflow status for JudgmentPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow status",
                                  code="WORKFLOW_STATUS_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data=data)


class JudgmentPlaintiffWorkflowHistoryView(APIView):
    """GET /legal/judgments/plaintiff/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalJudgment().has_permission(request, self) or
                CanManageLegalJudgment().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_judgment:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(JudgmentPlaintiff, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})
        try:
            activities = LegalJudgmentService().get_workflow_history(str(pk), side='plaintiff')
        except Exception as exc:
            logger.error("Error fetching workflow history for JudgmentPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow history",
                                  code="WORKFLOW_HISTORY_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={
            'has_workflow': True,
            'workflow_plan_id': str(entity.workflow_plan_id),
            'activities': activities,
        })


class JudgmentPlaintiffWorkflowActionView(APIView):
    """POST /legal/judgments/plaintiff/<pk>/workflow-action/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_judgment:manage', 'grc:legal_judgment:record',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

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
            result = LegalJudgmentService().advance_workflow_stage(
                entity_id=str(pk), action=action_name,
                actor_id=str(user_id), comment=request.data.get('comment', ''),
                side='plaintiff',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="WORKFLOW_ACTION_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error executing workflow action for JudgmentPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to execute workflow action",
                                  code="WORKFLOW_ACTION_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)

        # GAP-10: Stamp the judgment document when the workflow completes
        if result.get('plan_status') == 'completed':
            from apps.core.utils.legal_document_stamp import stamp_legal_document
            try:
                entity = JudgmentPlaintiff.objects.get(pk=pk)
                stamp_legal_document(
                    entity=entity,
                    document_id_field='document_id',
                    approver_id=str(user_id),
                    entity_type='judgment_plaintiff',
                    auth_token=request.auth,
                )
            except Exception as stamp_exc:
                logger.warning("GAP-10: Post-workflow stamp failed for JudgmentPlaintiff %s: %s", pk, stamp_exc)

        return success_response(data=result)


class JudgmentPlaintiffCancelWorkflowView(APIView):
    """POST /legal/judgments/plaintiff/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalJudgment().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_judgment:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            LegalJudgmentService().cancel_workflow_plan(
                entity_id=str(pk), actor_id=str(user_id),
                reason=request.data.get('reason', ''), side='plaintiff',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error cancelling workflow for JudgmentPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to cancel workflow",
                                  code="CANCEL_WORKFLOW_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Appeal Defendant (auto-created — GET list, GET/PATCH detail only)
# ═══════════════════════════════════════════════════════════════════════════════

class AppealDefendantListView(APIView):
    """GET /legal/appeals/defendant/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalAppeal().has_permission(request, self) or
                CanManageLegalAppeal().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_appeal:view or :manage required.')

    def get(self, request):
        try:
            queryset = AppealDefendant.objects.select_related('judgment', 'court_level').all()

            judgment = request.query_params.get('judgment')
            status_filter = request.query_params.get('status')
            if judgment:
                queryset = queryset.filter(judgment_id=judgment)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-appeal_date',
                allowed_fields=['appeal_date', 'status', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = AppealDefendantSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='appeal_defendant',
            )
        except Exception as e:
            logger.exception("Failed to retrieve defendant appeals")
            return server_error_response(
                message="Failed to retrieve defendant appeals",
                details=str(e) if settings.DEBUG else None,
            )


class AppealDefendantDetailView(APIView):
    """
    GET   /legal/appeals/defendant/<pk>/
    PATCH /legal/appeals/defendant/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalAppeal().has_permission(request, self) or
                    CanManageLegalAppeal().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_appeal:view or :manage required.')
        else:
            if not CanManageLegalAppeal().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_appeal:manage required.')

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                AppealDefendant.objects.select_related('judgment', 'court_level'), pk=pk,
            )
            return success_response(data=AppealDefendantSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve defendant appeal")
            return server_error_response(
                message="Failed to retrieve defendant appeal",
                details=str(e) if settings.DEBUG else None,
            )

    def patch(self, request, pk):
        try:
            entity = get_object_or_404(AppealDefendant, pk=pk)
            serializer = AppealDefendantSerializer(entity, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=AppealDefendantSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update defendant appeal")
            return server_error_response(
                message="Failed to update defendant appeal",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Appeal Plaintiff (auto-created — GET list, GET/PATCH detail only)
# ═══════════════════════════════════════════════════════════════════════════════

class AppealPlaintiffListView(APIView):
    """GET /legal/appeals/plaintiff/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalAppeal().has_permission(request, self) or
                CanManageLegalAppeal().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_appeal:view or :manage required.')

    def get(self, request):
        try:
            queryset = AppealPlaintiff.objects.select_related('judgment', 'court_level').all()

            judgment = request.query_params.get('judgment')
            status_filter = request.query_params.get('status')
            if judgment:
                queryset = queryset.filter(judgment_id=judgment)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-appeal_date',
                allowed_fields=['appeal_date', 'status', 'created_at'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = AppealPlaintiffSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='appeal_plaintiff',
            )
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff appeals")
            return server_error_response(
                message="Failed to retrieve plaintiff appeals",
                details=str(e) if settings.DEBUG else None,
            )


class AppealPlaintiffDetailView(APIView):
    """
    GET   /legal/appeals/plaintiff/<pk>/
    PATCH /legal/appeals/plaintiff/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalAppeal().has_permission(request, self) or
                    CanManageLegalAppeal().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_appeal:view or :manage required.')
        else:
            if not CanManageLegalAppeal().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_appeal:manage required.')

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                AppealPlaintiff.objects.select_related('judgment', 'court_level'), pk=pk,
            )
            return success_response(data=AppealPlaintiffSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff appeal")
            return server_error_response(
                message="Failed to retrieve plaintiff appeal",
                details=str(e) if settings.DEBUG else None,
            )

    def patch(self, request, pk):
        try:
            entity = get_object_or_404(AppealPlaintiff, pk=pk)
            serializer = AppealPlaintiffSerializer(entity, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=AppealPlaintiffSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update plaintiff appeal")
            return server_error_response(
                message="Failed to update plaintiff appeal",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# DG Decision (accept / appeal) — triggers auto-creation of Appeal records
# ═══════════════════════════════════════════════════════════════════════════════

VALID_DG_DECISIONS = ('accept', 'appeal')


class JudgmentDefendantDGDecisionView(APIView):
    """POST /legal/judgments/defendant/<pk>/dg-decision/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_judgment:manage', 'grc:legal_judgment:record',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        decision = request.data.get('decision')
        if decision not in VALID_DG_DECISIONS:
            return error_response(
                message=f"'decision' must be one of {VALID_DG_DECISIONS}",
                code="INVALID_DECISION",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            entity = LegalJudgmentService().process_appeal_decision(
                entity_id=str(pk), decision=decision,
                actor_id=str(user_id), side='defendant',
            )
            return success_response(data=JudgmentDefendantSerializer(entity).data)
        except JudgmentDefendant.DoesNotExist:
            return error_response(message="Judgment not found", code="NOT_FOUND",
                                  status_code=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.exception("DG decision failed for defendant judgment %s", pk)
            return server_error_response(
                message="Failed to record DG decision",
                details=str(exc) if settings.DEBUG else None,
            )


class JudgmentPlaintiffDGDecisionView(APIView):
    """POST /legal/judgments/plaintiff/<pk>/dg-decision/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_judgment:manage', 'grc:legal_judgment:record',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_judgment:manage or :record required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        decision = request.data.get('decision')
        if decision not in VALID_DG_DECISIONS:
            return error_response(
                message=f"'decision' must be one of {VALID_DG_DECISIONS}",
                code="INVALID_DECISION",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            entity = LegalJudgmentService().process_appeal_decision(
                entity_id=str(pk), decision=decision,
                actor_id=str(user_id), side='plaintiff',
            )
            return success_response(data=JudgmentPlaintiffSerializer(entity).data)
        except JudgmentPlaintiff.DoesNotExist:
            return error_response(message="Judgment not found", code="NOT_FOUND",
                                  status_code=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.exception("DG decision failed for plaintiff judgment %s", pk)
            return server_error_response(
                message="Failed to record DG decision",
                details=str(exc) if settings.DEBUG else None,
            )
