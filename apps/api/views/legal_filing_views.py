"""
Legal Module — Filing CRUD + Workflow + Response sub-entity views.
Entities: FilingDefendant, FilingPlaintiff, ResponseDefendant, ResponsePlaintiff
Uses LegalFilingService with dual-entity `side` parameter.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    FilingDefendant, FilingPlaintiff,
    ResponseDefendant, ResponsePlaintiff,
    CaseDefendant, CasePlaintiff,
)
from apps.api.serializers.legal_serializers import (
    FilingDefendantSerializer, FilingPlaintiffSerializer,
    ResponseDefendantSerializer, ResponsePlaintiffSerializer,
)
from apps.api.permissions_jwt import (
    CanViewLegalFiling, CanManageLegalFiling, CanApproveLegalFiling,
    HasAnyPermission,
)
from apps.core.services.legal_filing_service import LegalFilingService
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response, success_response, created_response,
    error_response, validation_error_response, conflict_response,
    server_error_response, deleted_response,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Filing Defendant CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class FilingDefendantListCreateView(APIView):
    """
    GET  /legal/filings/defendant/
    POST /legal/filings/defendant/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalFiling().has_permission(request, self) or
                    CanManageLegalFiling().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_filing:view or :manage required.')
        else:
            if not CanManageLegalFiling().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_filing:manage required.')

    def get(self, request):
        try:
            queryset = FilingDefendant.objects.select_related('case_defendant').all()

            case_defendant = request.query_params.get('case_defendant')
            status_filter = request.query_params.get('status')
            if case_defendant:
                queryset = queryset.filter(case_defendant_id=case_defendant)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status', 'filing_type'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = FilingDefendantSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='filing_defendant',
            )
        except Exception as e:
            logger.exception("Failed to retrieve defendant filings")
            return server_error_response(
                message="Failed to retrieve defendant filings",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = FilingDefendantSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # Business rule: parent case must not be closed
            case = serializer.validated_data.get('case_defendant')
            if case and case.status == 'closed':
                return error_response(
                    message="Cannot file on a closed case",
                    code="CASE_CLOSED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=FilingDefendantSerializer(entity).data,
                message="Defendant filing created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create defendant filing")
            return server_error_response(
                message="Failed to create defendant filing",
                details=str(e) if settings.DEBUG else None,
            )


class FilingDefendantDetailView(APIView):
    """
    GET    /legal/filings/defendant/<pk>/
    PUT    /legal/filings/defendant/<pk>/
    PATCH  /legal/filings/defendant/<pk>/
    DELETE /legal/filings/defendant/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalFiling().has_permission(request, self) or
                    CanManageLegalFiling().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_filing:view or :manage required.')
        else:
            if not CanManageLegalFiling().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_filing:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            FilingDefendant.objects.select_related('case_defendant'), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=FilingDefendantSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve defendant filing")
            return server_error_response(
                message="Failed to retrieve defendant filing",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'filed':
                return error_response(
                    message="Filed documents cannot be modified",
                    code="FILING_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = FilingDefendantSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=FilingDefendantSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update defendant filing")
            return server_error_response(
                message="Failed to update defendant filing",
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
            return deleted_response(message="Defendant filing deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete defendant filing")
            return server_error_response(
                message="Failed to delete defendant filing",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Filing Defendant Workflow
# ═══════════════════════════════════════════════════════════════════════════════

class FilingDefendantSubmitView(APIView):
    """POST /legal/filings/defendant/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalFiling().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_filing:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            entity = get_object_or_404(FilingDefendant, pk=pk)

            if entity.status != 'draft':
                return error_response(
                    message=f"Only draft filings can be submitted. Current: '{entity.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            entity = LegalFilingService().submit_for_approval(
                entity_id=str(pk), submitter_id=str(user_id), side='defendant',
            )

            return success_response(
                data=FilingDefendantSerializer(entity).data,
                message="Filing submitted for approval",
            )
        except Exception as e:
            logger.exception("Failed to submit defendant filing")
            return server_error_response(
                message="Failed to submit defendant filing",
                details=str(e) if settings.DEBUG else None,
            )


class FilingDefendantWorkflowStatusView(APIView):
    """GET /legal/filings/defendant/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalFiling().has_permission(request, self) or
                CanManageLegalFiling().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_filing:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(FilingDefendant, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})
        try:
            data = LegalFilingService().get_workflow_status(str(pk), side='defendant')
        except Exception as exc:
            logger.error("Error fetching workflow status for FilingDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(
                message="Failed to retrieve workflow status",
                code="WORKFLOW_STATUS_FAILED",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        return success_response(data=data)


class FilingDefendantWorkflowHistoryView(APIView):
    """GET /legal/filings/defendant/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalFiling().has_permission(request, self) or
                CanManageLegalFiling().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_filing:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(FilingDefendant, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})
        try:
            activities = LegalFilingService().get_workflow_history(str(pk), side='defendant')
        except Exception as exc:
            logger.error("Error fetching workflow history for FilingDefendant %s: %s", pk, exc, exc_info=True)
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


class FilingDefendantWorkflowActionView(APIView):
    """POST /legal/filings/defendant/<pk>/workflow-action/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_filing:manage', 'grc:legal_filing:approve',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_filing:manage or :approve required.')

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
            result = LegalFilingService().advance_workflow_stage(
                entity_id=str(pk), action=action_name,
                actor_id=str(user_id), comment=request.data.get('comment', ''),
                side='defendant',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="WORKFLOW_ACTION_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error executing workflow action for FilingDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to execute workflow action",
                                  code="WORKFLOW_ACTION_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)

        # GAP-10: Stamp the document when the filing workflow completes
        if result.get('plan_status') == 'completed':
            from apps.core.utils.legal_document_stamp import stamp_legal_document
            try:
                entity = FilingDefendant.objects.get(pk=pk)
                stamp_legal_document(
                    entity=entity,
                    document_id_field='document_id',
                    approver_id=str(user_id),
                    entity_type='filing_defendant',
                    auth_token=request.auth,
                )
            except Exception as stamp_exc:
                logger.warning("GAP-10: Post-workflow stamp failed for FilingDefendant %s: %s", pk, stamp_exc)

        return success_response(data=result)


class FilingDefendantCancelWorkflowView(APIView):
    """POST /legal/filings/defendant/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalFiling().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_filing:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            LegalFilingService().cancel_workflow_plan(
                entity_id=str(pk), actor_id=str(user_id),
                reason=request.data.get('reason', ''), side='defendant',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error cancelling workflow for FilingDefendant %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to cancel workflow",
                                  code="CANCEL_WORKFLOW_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Response Defendant CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class ResponseDefendantListCreateView(APIView):
    """
    GET  /legal/responses/defendant/
    POST /legal/responses/defendant/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalFiling().has_permission(request, self) or
                    CanManageLegalFiling().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_filing:view or :manage required.')
        else:
            if not CanManageLegalFiling().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_filing:manage required.')

    def get(self, request):
        try:
            queryset = ResponseDefendant.objects.select_related('case_defendant').all()

            case_defendant = request.query_params.get('case_defendant')
            if case_defendant:
                queryset = queryset.filter(case_defendant_id=case_defendant)

            ordering = get_ordering_param(
                request, default='-received_date',
                allowed_fields=['received_date', 'response_type'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = ResponseDefendantSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='response_defendant',
            )
        except Exception as e:
            logger.exception("Failed to retrieve defendant responses")
            return server_error_response(
                message="Failed to retrieve defendant responses",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = ResponseDefendantSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=ResponseDefendantSerializer(entity).data,
                message="Defendant response recorded successfully",
            )
        except Exception as e:
            logger.exception("Failed to create defendant response")
            return server_error_response(
                message="Failed to create defendant response",
                details=str(e) if settings.DEBUG else None,
            )


class ResponseDefendantDetailView(APIView):
    """
    GET    /legal/responses/defendant/<pk>/
    PATCH  /legal/responses/defendant/<pk>/
    DELETE /legal/responses/defendant/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalFiling().has_permission(request, self) or
                    CanManageLegalFiling().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_filing:view or :manage required.')
        else:
            if not CanManageLegalFiling().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_filing:manage required.')

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                ResponseDefendant.objects.select_related('case_defendant'), pk=pk,
            )
            return success_response(data=ResponseDefendantSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve defendant response")
            return server_error_response(
                message="Failed to retrieve defendant response",
                details=str(e) if settings.DEBUG else None,
            )

    def patch(self, request, pk):
        try:
            entity = get_object_or_404(ResponseDefendant, pk=pk)
            serializer = ResponseDefendantSerializer(entity, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=ResponseDefendantSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update defendant response")
            return server_error_response(
                message="Failed to update defendant response",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            entity = get_object_or_404(ResponseDefendant, pk=pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Defendant response deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete defendant response")
            return server_error_response(
                message="Failed to delete defendant response",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Filing Plaintiff CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class FilingPlaintiffListCreateView(APIView):
    """
    GET  /legal/filings/plaintiff/
    POST /legal/filings/plaintiff/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalFiling().has_permission(request, self) or
                    CanManageLegalFiling().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_filing:view or :manage required.')
        else:
            if not CanManageLegalFiling().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_filing:manage required.')

    def get(self, request):
        try:
            queryset = FilingPlaintiff.objects.select_related('case_plaintiff').all()

            case_plaintiff = request.query_params.get('case_plaintiff')
            status_filter = request.query_params.get('status')
            if case_plaintiff:
                queryset = queryset.filter(case_plaintiff_id=case_plaintiff)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status', 'filing_type'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = FilingPlaintiffSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='filing_plaintiff',
            )
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff filings")
            return server_error_response(
                message="Failed to retrieve plaintiff filings",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = FilingPlaintiffSerializer(data=request.data)
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
                    message="Cannot file on a closed case",
                    code="CASE_CLOSED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=FilingPlaintiffSerializer(entity).data,
                message="Plaintiff filing created successfully",
            )
        except Exception as e:
            logger.exception("Failed to create plaintiff filing")
            return server_error_response(
                message="Failed to create plaintiff filing",
                details=str(e) if settings.DEBUG else None,
            )


class FilingPlaintiffDetailView(APIView):
    """
    GET    /legal/filings/plaintiff/<pk>/
    PUT    /legal/filings/plaintiff/<pk>/
    PATCH  /legal/filings/plaintiff/<pk>/
    DELETE /legal/filings/plaintiff/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalFiling().has_permission(request, self) or
                    CanManageLegalFiling().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_filing:view or :manage required.')
        else:
            if not CanManageLegalFiling().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_filing:manage required.')

    def _get_entity(self, pk):
        return get_object_or_404(
            FilingPlaintiff.objects.select_related('case_plaintiff'), pk=pk,
        )

    def get(self, request, pk):
        try:
            entity = self._get_entity(pk)
            return success_response(data=FilingPlaintiffSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff filing")
            return server_error_response(
                message="Failed to retrieve plaintiff filing",
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        try:
            entity = self._get_entity(pk)

            if entity.status == 'filed':
                return error_response(
                    message="Filed documents cannot be modified",
                    code="FILING_LOCKED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = FilingPlaintiffSerializer(entity, data=request.data, partial=partial)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=FilingPlaintiffSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update plaintiff filing")
            return server_error_response(
                message="Failed to update plaintiff filing",
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
            return deleted_response(message="Plaintiff filing deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete plaintiff filing")
            return server_error_response(
                message="Failed to delete plaintiff filing",
                details=str(e) if settings.DEBUG else None,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Filing Plaintiff Workflow
# ═══════════════════════════════════════════════════════════════════════════════

class FilingPlaintiffSubmitView(APIView):
    """POST /legal/filings/plaintiff/<pk>/submit/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalFiling().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_filing:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(
                message="User not authenticated", code="AUTH_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            entity = get_object_or_404(FilingPlaintiff, pk=pk)

            if entity.status != 'draft':
                return error_response(
                    message=f"Only draft filings can be submitted. Current: '{entity.status}'",
                    code="INVALID_STATUS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if entity.workflow_plan_id:
                return conflict_response(
                    message="Workflow already in progress",
                    code="WORKFLOW_ALREADY_STARTED",
                )

            entity = LegalFilingService().submit_for_approval(
                entity_id=str(pk), submitter_id=str(user_id), side='plaintiff',
            )

            return success_response(
                data=FilingPlaintiffSerializer(entity).data,
                message="Filing submitted for approval",
            )
        except Exception as e:
            logger.exception("Failed to submit plaintiff filing")
            return server_error_response(
                message="Failed to submit plaintiff filing",
                details=str(e) if settings.DEBUG else None,
            )


class FilingPlaintiffWorkflowStatusView(APIView):
    """GET /legal/filings/plaintiff/<pk>/workflow-status/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalFiling().has_permission(request, self) or
                CanManageLegalFiling().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_filing:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(FilingPlaintiff, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'status': entity.status})
        try:
            data = LegalFilingService().get_workflow_status(str(pk), side='plaintiff')
        except Exception as exc:
            logger.error("Error fetching workflow status for FilingPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow status",
                                  code="WORKFLOW_STATUS_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data=data)


class FilingPlaintiffWorkflowHistoryView(APIView):
    """GET /legal/filings/plaintiff/<pk>/workflow-history/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not (CanViewLegalFiling().has_permission(request, self) or
                CanManageLegalFiling().has_permission(request, self)):
            self.permission_denied(request, message='grc:legal_filing:view or :manage required.')

    def get(self, request, pk):
        entity = get_object_or_404(FilingPlaintiff, pk=pk)
        if not entity.workflow_plan_id:
            return success_response(data={'has_workflow': False, 'activities': []})
        try:
            activities = LegalFilingService().get_workflow_history(str(pk), side='plaintiff')
        except Exception as exc:
            logger.error("Error fetching workflow history for FilingPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to retrieve workflow history",
                                  code="WORKFLOW_HISTORY_FAILED",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={
            'has_workflow': True,
            'workflow_plan_id': str(entity.workflow_plan_id),
            'activities': activities,
        })


class FilingPlaintiffWorkflowActionView(APIView):
    """POST /legal/filings/plaintiff/<pk>/workflow-action/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not HasAnyPermission([
            'grc:legal_filing:manage', 'grc:legal_filing:approve',
        ]).has_permission(request, self):
            self.permission_denied(request, message='grc:legal_filing:manage or :approve required.')

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
            result = LegalFilingService().advance_workflow_stage(
                entity_id=str(pk), action=action_name,
                actor_id=str(user_id), comment=request.data.get('comment', ''),
                side='plaintiff',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="WORKFLOW_ACTION_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error executing workflow action for FilingPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to execute workflow action",
                                  code="WORKFLOW_ACTION_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)

        # GAP-10: Stamp the document when the filing workflow completes
        if result.get('plan_status') == 'completed':
            from apps.core.utils.legal_document_stamp import stamp_legal_document
            try:
                entity = FilingPlaintiff.objects.get(pk=pk)
                stamp_legal_document(
                    entity=entity,
                    document_id_field='document_id',
                    approver_id=str(user_id),
                    entity_type='filing_plaintiff',
                    auth_token=request.auth,
                )
            except Exception as stamp_exc:
                logger.warning("GAP-10: Post-workflow stamp failed for FilingPlaintiff %s: %s", pk, stamp_exc)

        return success_response(data=result)


class FilingPlaintiffCancelWorkflowView(APIView):
    """POST /legal/filings/plaintiff/<pk>/cancel-workflow/"""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageLegalFiling().has_permission(request, self):
            self.permission_denied(request, message='grc:legal_filing:manage required.')

    def post(self, request, pk):
        user_id = getattr(request.user, 'id', None)
        if not user_id:
            return error_response(message="User not authenticated", code="AUTH_REQUIRED",
                                  status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            LegalFilingService().cancel_workflow_plan(
                entity_id=str(pk), actor_id=str(user_id),
                reason=request.data.get('reason', ''), side='plaintiff',
            )
        except ValueError as exc:
            return error_response(message=str(exc), code="CANCEL_WORKFLOW_FAILED",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error cancelling workflow for FilingPlaintiff %s: %s", pk, exc, exc_info=True)
            return error_response(message="Failed to cancel workflow",
                                  code="CANCEL_WORKFLOW_ERROR",
                                  status_code=status.HTTP_502_BAD_GATEWAY)
        return success_response(data={'status': 'workflow_cancelled'})


# ═══════════════════════════════════════════════════════════════════════════════
# Response Plaintiff CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class ResponsePlaintiffListCreateView(APIView):
    """
    GET  /legal/responses/plaintiff/
    POST /legal/responses/plaintiff/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalFiling().has_permission(request, self) or
                    CanManageLegalFiling().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_filing:view or :manage required.')
        else:
            if not CanManageLegalFiling().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_filing:manage required.')

    def get(self, request):
        try:
            queryset = ResponsePlaintiff.objects.select_related('case_plaintiff').all()

            case_plaintiff = request.query_params.get('case_plaintiff')
            if case_plaintiff:
                queryset = queryset.filter(case_plaintiff_id=case_plaintiff)

            ordering = get_ordering_param(
                request, default='-received_date',
                allowed_fields=['received_date', 'response_type'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = ResponsePlaintiffSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='response_plaintiff',
            )
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff responses")
            return server_error_response(
                message="Failed to retrieve plaintiff responses",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        try:
            serializer = ResponsePlaintiffSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated", code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            with transaction.atomic():
                entity = serializer.save(created_by=user_id)

            return created_response(
                data=ResponsePlaintiffSerializer(entity).data,
                message="Plaintiff response recorded successfully",
            )
        except Exception as e:
            logger.exception("Failed to create plaintiff response")
            return server_error_response(
                message="Failed to create plaintiff response",
                details=str(e) if settings.DEBUG else None,
            )


class ResponsePlaintiffDetailView(APIView):
    """
    GET    /legal/responses/plaintiff/<pk>/
    PATCH  /legal/responses/plaintiff/<pk>/
    DELETE /legal/responses/plaintiff/<pk>/
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not (CanViewLegalFiling().has_permission(request, self) or
                    CanManageLegalFiling().has_permission(request, self)):
                self.permission_denied(request, message='grc:legal_filing:view or :manage required.')
        else:
            if not CanManageLegalFiling().has_permission(request, self):
                self.permission_denied(request, message='grc:legal_filing:manage required.')

    def get(self, request, pk):
        try:
            entity = get_object_or_404(
                ResponsePlaintiff.objects.select_related('case_plaintiff'), pk=pk,
            )
            return success_response(data=ResponsePlaintiffSerializer(entity).data)
        except Exception as e:
            logger.exception("Failed to retrieve plaintiff response")
            return server_error_response(
                message="Failed to retrieve plaintiff response",
                details=str(e) if settings.DEBUG else None,
            )

    def patch(self, request, pk):
        try:
            entity = get_object_or_404(ResponsePlaintiff, pk=pk)
            serializer = ResponsePlaintiffSerializer(entity, data=request.data, partial=True)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)

            return success_response(data=ResponsePlaintiffSerializer(updated).data)
        except Exception as e:
            logger.exception("Failed to update plaintiff response")
            return server_error_response(
                message="Failed to update plaintiff response",
                details=str(e) if settings.DEBUG else None,
            )

    def delete(self, request, pk):
        try:
            entity = get_object_or_404(ResponsePlaintiff, pk=pk)
            with transaction.atomic():
                entity.is_active = False
                entity.save(update_fields=['is_active', 'updated_at'])
            return deleted_response(message="Plaintiff response deactivated successfully")
        except Exception as e:
            logger.exception("Failed to delete plaintiff response")
            return server_error_response(
                message="Failed to delete plaintiff response",
                details=str(e) if settings.DEBUG else None,
            )
