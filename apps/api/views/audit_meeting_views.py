"""
Audit Meeting CRUD Views for GRC Service
Provides full CRUD operations for audit meeting management following FIMS patterns.

Covers SRS 1.8.3:
  - Step 14: Entry meeting (entry conference with process owners)
  - Step 17: Pre-exit meeting (clarification / communication of results)
  - Step 20: Audit-team meeting (consolidate deviations & recommendations)
  - Step 24: Exit meeting (present results to auditee management)
"""

import logging

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditMeeting, AuditEngagement, AuditReport, WorkingPaper
from apps.api.serializers.audit_serializers import AuditMeetingSerializer
from apps.api.permissions_jwt import CanManageAuditMeeting, CanViewAuditMeeting
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import AUDIT_MEETING_EVENTS
from apps.infrastructure.external.document_service_client import (
    get_document_client,
    DocumentServiceError,
)

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    created_response,
    error_response,
    not_found_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sync_engagement_meeting_date(meeting):
    """
    GAP-6 fix: keep AuditEngagement.entry_meeting_date / exit_meeting_date
    in sync with the corresponding AuditMeeting.scheduled_date.

    Called after a meeting is created, updated, or has its status changed.
    For cancelled meetings the engagement date is cleared.
    """
    field_map = {
        'entry': 'entry_meeting_date',
        'exit':  'exit_meeting_date',
    }
    field_name = field_map.get(meeting.meeting_type)
    if not field_name:
        return  # Only entry/exit meetings have corresponding engagement fields

    engagement = meeting.engagement

    if meeting.status == 'cancelled':
        new_value = None
    else:
        new_value = meeting.scheduled_date

    if getattr(engagement, field_name) != new_value:
        setattr(engagement, field_name, new_value)
        engagement.save(update_fields=[field_name, 'updated_at'])
        logger.info(
            'Synced %s=%s on engagement %s from meeting %s',
            field_name, new_value, engagement.reference_number,
            meeting.reference_number,
        )


def _generate_meeting_documents(meeting, auth_token=None):
    """
    GAP-9: Auto-generate meeting minutes and attendance register PDFs
    and store them in the Document Records Service when a meeting is completed.

    Scope (SRS §1.8.3):
      - entry   → minutes PDF + attendance register PDF
      - exit    → minutes PDF + attendance register PDF
      - pre_exit→ minutes PDF only  (SRS Step 17 data requirement, no separate attendance register)
      - team    → skipped           (internal team meeting, no formal SRS output)

    The function is intentionally non-blocking: any PDF/upload error is logged
    and swallowed so that the meeting completion itself is never rolled back.
    Already-set document IDs are never overwritten (preserve manual uploads).
    """
    import io
    from apps.core.utils.pdf_generators import (
        generate_meeting_minutes_pdf,
        generate_attendance_register_pdf,
    )
    from apps.infrastructure.external.document_service_client import DocumentServiceClient

    if meeting.meeting_type == 'team':
        return

    client = DocumentServiceClient(auth_token=auth_token)
    fields_to_update = []

    # ── Minutes PDF (entry, exit, pre_exit) ──────────────────────────────
    if not meeting.minutes_document_id:
        try:
            pdf_bytes = generate_meeting_minutes_pdf(meeting)
            doc = client.create_document_with_file(
                title=f"Meeting Minutes — {meeting.reference_number}",
                description=(
                    f"Meeting minutes for {meeting.get_meeting_type_display()} "
                    f"of engagement {meeting.engagement.reference_number}"
                ),
                document_type='audit_meeting_minutes',
                classification='confidential',
                retention_period=2555,  # 7 years for audit records
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"meeting_minutes_{meeting.id}.pdf",
                metadata={
                    'source_service': 'grc',
                    'entity_type': 'audit_meeting',
                    'entity_id': str(meeting.id),
                    'engagement_id': str(meeting.engagement_id),
                    'meeting_type': meeting.meeting_type,
                    'reference_number': meeting.reference_number,
                },
            )
            meeting.minutes_document_id = doc['id']
            fields_to_update.append('minutes_document_id')
            logger.info(
                'GAP-9: Minutes PDF for meeting %s uploaded to DRS as document %s',
                meeting.id, doc['id'],
            )
        except Exception as exc:
            logger.warning(
                'GAP-9: Could not generate/upload minutes PDF for meeting %s: %s',
                meeting.id, exc,
            )

    # ── Attendance Register PDF (entry, exit only) ───────────────────────
    if meeting.meeting_type in ('entry', 'exit') and not meeting.attendance_document_id:
        try:
            pdf_bytes = generate_attendance_register_pdf(meeting)
            doc = client.create_document_with_file(
                title=f"Attendance Register — {meeting.reference_number}",
                description=(
                    f"Attendance register for {meeting.get_meeting_type_display()} "
                    f"of engagement {meeting.engagement.reference_number}"
                ),
                document_type='audit_meeting_attendance',
                classification='confidential',
                retention_period=2555,
                file_data=io.BytesIO(pdf_bytes),
                file_name=f"attendance_register_{meeting.id}.pdf",
                metadata={
                    'source_service': 'grc',
                    'entity_type': 'audit_meeting',
                    'entity_id': str(meeting.id),
                    'engagement_id': str(meeting.engagement_id),
                    'meeting_type': meeting.meeting_type,
                    'reference_number': meeting.reference_number,
                },
            )
            meeting.attendance_document_id = doc['id']
            fields_to_update.append('attendance_document_id')
            logger.info(
                'GAP-9: Attendance PDF for meeting %s uploaded to DRS as document %s',
                meeting.id, doc['id'],
            )
        except Exception as exc:
            logger.warning(
                'GAP-9: Could not generate/upload attendance PDF for meeting %s: %s',
                meeting.id, exc,
            )

    if fields_to_update:
        meeting.save(update_fields=fields_to_update)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Valid status transition map
VALID_MEETING_TRANSITIONS = {
    'scheduled':   ['in_progress', 'cancelled'],
    'in_progress': ['completed', 'cancelled'],
    'completed':   [],   # Terminal
    'cancelled':   [],   # Terminal
}

# Meeting types that are editable (not locked) by status
LOCKED_STATUSES = ('completed', 'cancelled')

# Only these fields may be changed when a meeting is in_progress
IN_PROGRESS_EDITABLE_FIELDS = frozenset(
    ['minutes', 'key_discussions', 'clarifications', 'agreed_observations',
     'action_items', 'attendees',
     'minutes_document_id', 'attendance_document_id',
     'minutes_file', 'attendance_file']
)

# Map: meeting_type → permitted engagement statuses
MEETING_TYPE_ENGAGEMENT_PHASES = {
    'entry':    ('fieldwork',),          # FIX-1: entry meeting requires EN transmitted (fieldwork phase)
    'pre_exit': ('fieldwork', 'reporting'),
    'team':     ('fieldwork', 'reporting'),
    'exit':     ('reporting', 'completed'),
}


# ---------------------------------------------------------------------------
# 1. AuditMeetingListCreateView
# ---------------------------------------------------------------------------

class AuditMeetingListCreateView(APIView):
    """
    GET  /api/v1/grc/audit/meetings/   — List meetings with pagination + filters
    POST /api/v1/grc/audit/meetings/   — Schedule a new meeting
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            # Viewers (CIA, audit_committee) and managers (LA) can list meetings.
            can_view   = CanViewAuditMeeting().has_permission(request, self)
            can_manage = CanManageAuditMeeting().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:audit_meeting:view or grc:audit_meeting:manage permission required.',
                )
        else:
            # POST — only the Lead Auditor (internal_auditor) may schedule meetings.
            if not CanManageAuditMeeting().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:audit_meeting:manage permission required.',
                )

    def get(self, request):
        """List all audit meetings with optional filtering and pagination."""
        try:
            engagement_id  = request.query_params.get('engagement')
            meeting_type   = request.query_params.get('meeting_type')
            status_filter  = request.query_params.get('status')
            is_active      = request.query_params.get('is_active')

            queryset = AuditMeeting.objects.select_related('engagement').all()

            if engagement_id:
                queryset = queryset.filter(engagement_id=engagement_id)
            if meeting_type:
                queryset = queryset.filter(meeting_type=meeting_type)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            ordering = get_ordering_param(
                request,
                default='-scheduled_date',
                allowed_fields=[
                    'scheduled_date', 'created_at', 'status', 'meeting_type',
                ],
            )
            queryset = queryset.order_by(ordering)

            page_data  = paginate_queryset(queryset, request)
            serializer = AuditMeetingSerializer(page_data['queryset'], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data['total'],
                page=page_data['page'],
                page_size=page_data['page_size'],
                resource='audit_meeting',
            )

        except Exception as e:
            logger.exception('Failed to retrieve audit meetings')
            return server_error_response(
                message='Failed to retrieve audit meetings',
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        """Schedule a new audit meeting for an engagement."""
        try:
            serializer = AuditMeetingSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': 'Validation failed',
                            'details': serializer.errors,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            engagement_id    = serializer.validated_data['engagement_id']
            meeting_type     = serializer.validated_data['meeting_type']
            reference_number = serializer.validated_data.get('reference_number', '').strip()
            title            = serializer.validated_data.get('title', '').strip()

            # --- Verify engagement exists ------------------------------------
            engagement = get_object_or_404(AuditEngagement, id=engagement_id)

            # --- Verify engagement phase allows this meeting type -------------
            allowed_phases = MEETING_TYPE_ENGAGEMENT_PHASES.get(meeting_type, ())
            if engagement.status not in allowed_phases:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Cannot schedule an '{meeting_type}' meeting for an engagement "
                                f"in '{engagement.status}' phase. "
                                f"Allowed phases: {', '.join(allowed_phases)}."
                            ),
                            'code': 'INVALID_ENGAGEMENT_PHASE',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Pre-exit requires at least one approved working paper --
            # SRS Step 16: LA must have reviewed WPs before arranging pre-exit meeting.
            if meeting_type == 'pre_exit':
                has_approved_wp = WorkingPaper.objects.filter(
                    engagement=engagement,
                    review_status='approved',
                    is_active=True,
                ).exists()
                if not has_approved_wp:
                    return Response(
                        {
                            'success': False,
                            'error': {
                                'message': (
                                    'Cannot schedule a Pre-Exit Meeting until at least one '
                                    'Working Paper for this engagement has been approved '
                                    '(SRS Step 16 dependency).'
                                ),
                                'code': 'PRE_EXIT_REQUIRES_APPROVED_WPS',
                            },
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # --- Prevent duplicate meeting type per engagement ---------------
            # SRS GAP-4: each engagement should have at most one non-cancelled
            # meeting of each type (entry, pre_exit, team, exit).
            existing = AuditMeeting.objects.filter(
                engagement=engagement,
                meeting_type=meeting_type,
                is_active=True,
            ).exclude(status='cancelled')
            if existing.exists():
                type_display = dict(AuditMeeting.MEETING_TYPE_CHOICES).get(
                    meeting_type, meeting_type
                )
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"This engagement already has an active '{type_display}' meeting "
                                f"({existing.first().reference_number}). "
                                f"Cancel or complete the existing meeting before scheduling a new one."
                            ),
                            'code': 'DUPLICATE_MEETING_TYPE',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Require authenticated user ----------------------------------
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return Response(
                    {
                        'success': False,
                        'error': {'message': 'User not authenticated', 'code': 'AUTH_REQUIRED'},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # --- Auto-generate reference_number if not provided --------------
            if not reference_number:
                type_code = meeting_type.upper()   # 'ENTRY', 'PRE_EXIT', etc.
                count = AuditMeeting.objects.filter(
                    engagement=engagement,
                    meeting_type=meeting_type,
                ).count()
                reference_number = (
                    f"MTG-{engagement.reference_number}-{type_code}-{count + 1:03d}"
                )
                serializer.validated_data['reference_number'] = reference_number

            # --- Auto-generate title if not provided -------------------------
            if not title:
                type_display = dict(AuditMeeting.MEETING_TYPE_CHOICES).get(
                    meeting_type, meeting_type
                )
                serializer.validated_data['title'] = f"{type_display} - {engagement.title}"

            # --- Set organized_by from JWT user ------------------------------
            serializer.validated_data['organized_by'] = user_id

            with transaction.atomic():
                meeting = serializer.save(created_by=user_id)
                # GAP-6: sync scheduled_date → engagement meeting date
                _sync_engagement_meeting_date(meeting)

            # --- Publish Kafka event (best-effort) ---------------------------
            try:
                messaging_service.publish_audit_event(
                    event_type=AUDIT_MEETING_EVENTS['MEETING_SCHEDULED'],
                    audit_data={
                        'meeting_id':        str(meeting.id),
                        'engagement_id':     str(engagement.id),
                        'reference_number':  meeting.reference_number,
                        'meeting_type':      meeting.meeting_type,
                        'organized_by':      str(user_id),
                        'user_id':           str(user_id),
                    },
                )
            except Exception as event_error:
                logger.error(f'Error publishing meeting.scheduled event: {event_error}')

            return Response(
                {
                    'success': True,
                    'data': AuditMeetingSerializer(
                        meeting, context={'request': request}
                    ).data,
                    'message': 'Meeting scheduled successfully',
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.exception('Failed to schedule audit meeting')
            return Response(
                {
                    'success': False,
                    'error': {
                        'message': 'Failed to schedule audit meeting',
                        'details': str(e) if settings.DEBUG else None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# 2. AuditMeetingDetailView
# ---------------------------------------------------------------------------

class AuditMeetingDetailView(APIView):
    """
    GET    /api/v1/grc/audit/meetings/{pk}/   — Get meeting detail
    PUT    /api/v1/grc/audit/meetings/{pk}/   — Full update
    PATCH  /api/v1/grc/audit/meetings/{pk}/   — Partial update
    DELETE /api/v1/grc/audit/meetings/{pk}/   — Soft delete
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            # Read access: viewers (CIA, audit_committee) and managers (LA).
            can_view   = CanViewAuditMeeting().has_permission(request, self)
            can_manage = CanManageAuditMeeting().has_permission(request, self)
            if not (can_view or can_manage):
                self.permission_denied(
                    request,
                    message='grc:audit_meeting:view or grc:audit_meeting:manage permission required.',
                )
        else:
            # PUT / PATCH / DELETE — manage permission required.
            if not CanManageAuditMeeting().has_permission(request, self):
                self.permission_denied(
                    request,
                    message='grc:audit_meeting:manage permission required.',
                )

    def _get_meeting(self, pk):
        return get_object_or_404(
            AuditMeeting.objects.select_related('engagement__auditable_entity'),
            pk=pk,
        )

    def get(self, request, pk):
        """Retrieve meeting details."""
        try:
            meeting    = self._get_meeting(pk)
            serializer = AuditMeetingSerializer(meeting, context={'request': request})
            return success_response(data=serializer.data)
        except Exception as e:
            logger.exception('Failed to retrieve audit meeting')
            return server_error_response(
                message='Failed to retrieve audit meeting',
                details=str(e) if settings.DEBUG else None,
            )

    def _update(self, request, pk, partial=False):
        """Shared helper for PUT and PATCH."""
        try:
            meeting = self._get_meeting(pk)

            # --- Lock completed/cancelled meetings ---------------------------
            if meeting.status in LOCKED_STATUSES:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Meeting '{meeting.reference_number}' is locked "
                                f"(status: {meeting.status})."
                            ),
                            'code': 'MEETING_LOCKED',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Ownership check: only the organizer may edit ----------------
            # SRS: LA who scheduled the meeting is responsible for its records.
            user_id = getattr(request.user, 'id', None)
            if str(meeting.organized_by) != str(user_id):
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': 'MEETING_NOT_ORGANIZER',
                            'message': 'Only the meeting organizer can edit this meeting.',
                        },
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # --- In-progress: restrict editable fields -----------------------
            if meeting.status == 'in_progress' and not partial:
                # Full update while in-progress: only allow the restricted fields
                filtered_data = {
                    k: v for k, v in request.data.items()
                    if k in IN_PROGRESS_EDITABLE_FIELDS
                }
                serializer = AuditMeetingSerializer(
                    meeting, data=filtered_data, partial=True,
                    context={'request': request}
                )
            elif meeting.status == 'in_progress' and partial:
                disallowed = set(request.data.keys()) - IN_PROGRESS_EDITABLE_FIELDS
                if disallowed:
                    return Response(
                        {
                            'success': False,
                            'error': {
                                'message': (
                                    f"These fields cannot be edited while meeting is in-progress: "
                                    f"{', '.join(sorted(disallowed))}."
                                ),
                                'code': 'MEETING_LOCKED',
                            },
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                serializer = AuditMeetingSerializer(
                    meeting, data=request.data, partial=True,
                    context={'request': request}
                )
            else:
                serializer = AuditMeetingSerializer(
                    meeting, data=request.data, partial=partial,
                    context={'request': request}
                )

            if not serializer.is_valid():
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': 'Validation failed',
                            'details': serializer.errors,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_id = getattr(request.user, 'id', None)
            with transaction.atomic():
                updated = serializer.save(modified_by=user_id)
                # GAP-6: sync scheduled_date → engagement meeting date
                _sync_engagement_meeting_date(updated)

            # --- Handle document file uploads (FIMS Document Records Service) ---
            minutes_file    = request.FILES.get('minutes_file')
            attendance_file = request.FILES.get('attendance_file')

            if minutes_file or attendance_file:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                auth_token = (
                    auth_header.replace('Bearer ', '')
                    if auth_header.startswith('Bearer ') else None
                )
                document_client = get_document_client(auth_token=auth_token)
                fields_to_update = []

                if minutes_file:
                    try:
                        doc = document_client.create_document(
                            title=f"Meeting Minutes - {updated.reference_number}",
                            description=f"Minutes for: {updated.title}",
                            document_type='audit_meeting_minutes',
                            classification='confidential',
                            record_type='non_permanent',
                            retention_period=2555,
                            metadata={
                                'meeting_id': str(updated.id),
                                'meeting_reference': updated.reference_number,
                                'engagement_id': str(updated.engagement_id),
                                'service': 'grc-service',
                                'module': 'audit_meetings',
                            },
                            tags=['audit', 'meeting-minutes', updated.reference_number]
                        )
                        doc_id = doc['id']
                        document_client.upload_file(doc_id, minutes_file, minutes_file.name)
                        updated.minutes_document_id = doc_id
                        fields_to_update.append('minutes_document_id')
                        logger.info(f"Minutes document {doc_id} uploaded for meeting {updated.id}")
                    except DocumentServiceError as e:
                        logger.warning(f"Minutes file upload failed for meeting {updated.id}: {e}")

                if attendance_file:
                    try:
                        doc = document_client.create_document(
                            title=f"Attendance Sheet - {updated.reference_number}",
                            description=f"Attendance register for: {updated.title}",
                            document_type='audit_meeting_attendance',
                            classification='confidential',
                            record_type='non_permanent',
                            retention_period=2555,
                            metadata={
                                'meeting_id': str(updated.id),
                                'meeting_reference': updated.reference_number,
                                'engagement_id': str(updated.engagement_id),
                                'service': 'grc-service',
                                'module': 'audit_meetings',
                            },
                            tags=['audit', 'attendance-sheet', updated.reference_number]
                        )
                        doc_id = doc['id']
                        document_client.upload_file(doc_id, attendance_file, attendance_file.name)
                        updated.attendance_document_id = doc_id
                        fields_to_update.append('attendance_document_id')
                        logger.info(f"Attendance document {doc_id} uploaded for meeting {updated.id}")
                    except DocumentServiceError as e:
                        logger.warning(f"Attendance file upload failed for meeting {updated.id}: {e}")

                if fields_to_update:
                    updated.save(update_fields=fields_to_update)

            return success_response(
                data=AuditMeetingSerializer(updated, context={'request': request}).data,
            )

        except Exception as e:
            logger.exception('Failed to update audit meeting')
            return server_error_response(
                message='Failed to update audit meeting',
                details=str(e) if settings.DEBUG else None,
            )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        """Soft-delete a meeting (sets is_active=False)."""
        try:
            meeting = self._get_meeting(pk)

            # --- Ownership check: only the organizer may delete ---------------
            user_id = getattr(request.user, 'id', None)
            if str(meeting.organized_by) != str(user_id):
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': 'MEETING_NOT_ORGANIZER',
                            'message': 'Only the meeting organizer can delete this meeting.',
                        },
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Cannot soft-delete a completed meeting
            if meeting.status == 'completed':
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Meeting '{meeting.reference_number}' cannot be deleted "
                                "after it has been completed."
                            ),
                            'code': 'MEETING_LOCKED',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                meeting.is_active = False
                meeting.save(update_fields=['is_active', 'updated_at'])

            return Response(
                {
                    'success': True,
                    'message': f"Meeting '{meeting.reference_number}' has been deactivated.",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception('Failed to delete audit meeting')
            return server_error_response(
                message='Failed to delete audit meeting',
                details=str(e) if settings.DEBUG else None,
            )


# ---------------------------------------------------------------------------
# 3. AuditMeetingStatusUpdateView
# ---------------------------------------------------------------------------

class AuditMeetingStatusUpdateView(APIView):
    """
    POST /api/v1/grc/audit/meetings/{pk}/update-status/
    Body: { "status": "in_progress" | "completed" | "cancelled" }

    Valid transitions:
      scheduled   → in_progress | cancelled
      in_progress → completed   | cancelled
      completed   → (terminal)
      cancelled   → (terminal)
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageAuditMeeting().has_permission(request, self):
            self.permission_denied(
                request,
                message='grc:audit_meeting:manage permission required.',
            )

    def post(self, request, pk):
        try:
            meeting    = get_object_or_404(
                AuditMeeting.objects.select_related('engagement__auditable_entity'), pk=pk
            )
            new_status = request.data.get('status', '').strip()

            # --- Ownership check: only the organizer may change status -------
            user_id = getattr(request.user, 'id', None)
            if str(meeting.organized_by) != str(user_id):
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': 'MEETING_NOT_ORGANIZER',
                            'message': 'Only the meeting organizer can update the meeting status.',
                        },
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # --- Validate target status exists in choices --------------------
            valid_statuses = [s for s, _ in AuditMeeting.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Invalid status '{new_status}'. "
                                f"Valid values: {', '.join(valid_statuses)}."
                            ),
                            'code': 'INVALID_STATUS',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Validate transition is allowed ------------------------------
            allowed = VALID_MEETING_TRANSITIONS.get(meeting.status, [])
            if new_status not in allowed:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Cannot transition meeting from '{meeting.status}' "
                                f"to '{new_status}'. "
                                f"Allowed: {allowed or ['(none — terminal state)']}"
                            ),
                            'code': 'INVALID_STATUS_TRANSITION',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Status-specific validations ---------------------------------
            if new_status == 'completed':
                # SRS requires minutes to be documented before completing
                if not (meeting.minutes or '').strip():
                    return Response(
                        {
                            'success': False,
                            'error': {
                                'message': (
                                    "Meeting minutes must be recorded before marking "
                                    "a meeting as completed (SRS requirement)."
                                ),
                                'code': 'MINUTES_REQUIRED',
                            },
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # --- Apply transition --------------------------------------------
            old_status     = meeting.status
            meeting.status = new_status

            with transaction.atomic():
                meeting.save(update_fields=['status', 'updated_at'])
                # GAP-6: sync engagement meeting date (clears on cancel)
                _sync_engagement_meeting_date(meeting)

            # GAP-9: auto-generate meeting documents (minutes + attendance) on completion
            if new_status == 'completed':
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                auth_token = (
                    auth_header[len('Bearer '):].strip()
                    if auth_header.startswith('Bearer ')
                    else None
                )
                _generate_meeting_documents(meeting, auth_token=auth_token)

            # --- Map transition to Kafka event --------------------------------
            EVENT_MAP = {
                'in_progress': AUDIT_MEETING_EVENTS['MEETING_STARTED'],
                'completed':   AUDIT_MEETING_EVENTS['MEETING_COMPLETED'],
                'cancelled':   AUDIT_MEETING_EVENTS['MEETING_CANCELLED'],
            }
            event_type = EVENT_MAP.get(new_status)
            if event_type:
                try:
                    user_id = getattr(request.user, 'id', None)
                    messaging_service.publish_audit_event(
                        event_type=event_type,
                        audit_data={
                            'meeting_id':       str(meeting.id),
                            'reference_number': meeting.reference_number,
                            'old_status':       old_status,
                            'new_status':       new_status,
                            'user_id':          str(user_id) if user_id else None,
                        },
                    )
                except Exception as event_error:
                    logger.error(
                        f'Error publishing meeting status change event: {event_error}'
                    )

            return Response(
                {
                    'success': True,
                    'data': AuditMeetingSerializer(
                        meeting, context={'request': request}
                    ).data,
                    'message': (
                        f"Meeting status updated from '{old_status}' to '{new_status}'."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception('Failed to update meeting status')
            return server_error_response(
                message='Failed to update meeting status',
                details=str(e) if settings.DEBUG else None,
            )


# ---------------------------------------------------------------------------
# 4. AuditMeetingSendNotificationView
# ---------------------------------------------------------------------------
class AuditMeetingSendNotificationView(APIView):
    """
    POST /meetings/{pk}/send-notification/
    SRS Step 23: LA sends Exit Meeting Notification including draft audit report
    to auditee, auditors and other personnel responsible for the finding.
    """
    permission_classes = [IsAuthenticated, CanManageAuditMeeting]

    def post(self, request, pk):
        try:
            meeting = get_object_or_404(AuditMeeting, pk=pk, is_active=True)

            # --- Ownership check: only the organizer may send notification ---
            user_id = getattr(request.user, 'id', None)
            if str(meeting.organized_by) != str(user_id):
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': 'MEETING_NOT_ORGANIZER',
                            'message': 'Only the meeting organizer can send notifications for this meeting.',
                        },
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # ── Must be an exit meeting ──────────────────────────────────
            if meeting.meeting_type != 'exit':
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': 'Notifications can only be sent for exit meetings.',
                            'code': 'NOT_EXIT_MEETING',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Must be scheduled (not already started/completed) ────────
            if meeting.status != 'scheduled':
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                f"Cannot send notification for a meeting in "
                                f"'{meeting.status}' status. Meeting must be 'scheduled'."
                            ),
                            'code': 'INVALID_MEETING_STATUS',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Must not have already been sent ──────────────────────────
            if meeting.notification_sent:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': 'Exit meeting notification has already been sent.',
                            'code': 'NOTIFICATION_ALREADY_SENT',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Engagement must have an approved draft report ────────────
            engagement = meeting.engagement
            draft_report = AuditReport.objects.filter(
                engagement=engagement,
                report_type='draft',
                status='approved',
                is_active=True,
            ).order_by('-created_at').first()

            if not draft_report:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'message': (
                                'No approved draft audit report found for this engagement. '
                                'Per SRS Step 23, the exit meeting notification must include '
                                'the draft audit report.'
                            ),
                            'code': 'NO_APPROVED_DRAFT_REPORT',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Send notification ────────────────────────────────────────
            with transaction.atomic():
                now = timezone.now()
                meeting.notification_sent = True
                meeting.notification_date = now
                meeting.draft_report_id = draft_report.id
                meeting.save(update_fields=[
                    'notification_sent', 'notification_date', 'draft_report_id',
                ])

            # ── Publish Kafka event ──────────────────────────────────────
            try:
                user_id = getattr(request.user, 'id', None)
                messaging_service.publish_audit_event(
                    event_type=AUDIT_MEETING_EVENTS['MEETING_NOTIFICATION_SENT'],
                    audit_data={
                        'meeting_id':       str(meeting.id),
                        'reference_number': meeting.reference_number,
                        'engagement_id':    str(engagement.id),
                        'draft_report_id':  str(draft_report.id),
                        'notification_date': now.isoformat(),
                        'user_id':          str(user_id) if user_id else None,
                    },
                )
            except Exception as event_err:
                logger.warning(
                    f'Failed to publish exit notification event for '
                    f'meeting {meeting.id}: {event_err}'
                )

            logger.info(
                f'Exit meeting notification sent for meeting {meeting.id} '
                f'(engagement {engagement.reference_number}), '
                f'draft report {draft_report.id}'
            )

            return Response(
                {
                    'success': True,
                    'data': AuditMeetingSerializer(
                        meeting, context={'request': request}
                    ).data,
                    'message': (
                        'Exit meeting notification sent successfully. '
                        'Draft audit report has been linked.'
                    ),
                },
                status=status.HTTP_200_OK,
            )

        except Http404:
            raise
        except Exception as e:
            logger.exception('Failed to send exit meeting notification')
            return server_error_response(
                message='Failed to send exit meeting notification',
                details=str(e) if settings.DEBUG else None,
            )
