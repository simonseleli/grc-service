"""
Declaration of Independence Views for GRC Service (GAP 2 — SRS Req 16, 18, 38)
Per-team-member, per-engagement conflict of interest declarations.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import DeclarationOfIndependence, AuditEngagement
from apps.api.serializers.audit_serializers import DeclarationOfIndependenceSerializer
from apps.infrastructure.services.messaging_service import messaging_service
from shared.constants.event_types import DECLARATION_EVENTS
from apps.api.permissions_jwt import CanManageDeclaration, CanSignDeclaration

# FIMS standard utilities
from apps.api.utils.pagination import paginate_queryset, get_ordering_param
from apps.api.utils.response_helpers import (
    paginated_list_response,
    success_response,
    error_response,
    not_found_response,
    validation_error_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


def _upload_declaration_pdf_to_drs(decl, auth_token: str = None) -> None:
    """
    GAP 9 / SRS Req 18 + 38: Generate a PDF for the declaration and upload it
    to DRS, storing the returned document UUID in decl.document_id.

    This must run immediately after each declaration is created so that
    document_id is set before the declarant clicks Sign. When all declarations
    for an engagement are signed, DeclarationSignView loops over declarations
    with document_id set and calls DRS generate-approved-stamp — which overlays
    the QR code and CIA signature on the PDF.

    auth_token: the requesting user's JWT (passed from request.auth). DRS
    checks document:document:create permission embedded in the token, which
    is already granted to the internal_auditor role via IAM (see grc_notes.md
    section 9 — Grant DRS permissions to GRC roles).

    Non-blocking: any error is logged and swallowed. The declaration record
    is still valid without a PDF; stamping simply will not run for that record.
    """
    import io
    from apps.infrastructure.external.document_service_client import DocumentServiceClient
    from apps.core.utils.pdf_generators import generate_declaration_pdf
    try:
        # select_related so template rendering has no extra DB hits
        decl.audit_engagement  # already accessed by caller, but ensure it's loaded
        pdf_bytes = generate_declaration_pdf(decl)
        client = DocumentServiceClient(auth_token=auth_token)  # JWT carries document:document:create
        doc = client.create_document_with_file(
            title=f"Declaration of Independence — {decl.declarant_name}",
            description=(
                f"Conflict of Interest Declaration for audit engagement "
                f"{decl.audit_engagement.reference_number}"
            ),
            document_type='audit_declaration',
            classification='confidential',
            retention_period=2555,  # 7 years for audit records
            file_data=io.BytesIO(pdf_bytes),
            file_name=f"declaration_{decl.id}.pdf",
            metadata={
                'source_service': 'grc',
                'entity_type': 'declaration',
                'entity_id': str(decl.id),
                'engagement_id': str(decl.audit_engagement_id),
                'declarant_id': str(decl.declarant_user_id),
            },
        )
        decl.document_id = doc['id']
        decl.save(update_fields=['document_id'])
        logger.info(
            "GAP 9: Declaration %s PDF uploaded to DRS as document %s",
            decl.id, doc['id'],
        )
    except Exception as pdf_err:
        logger.warning(
            "GAP 9: Could not upload declaration PDF to DRS for declaration %s: %s",
            decl.id, pdf_err,
        )


class DeclarationListCreateView(APIView):
    """List all declarations or create new one(s)."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageDeclaration().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_declaration:manage required.')

    def get(self, request):
        """List declarations with optional engagement filter."""
        try:
            engagement_id = request.query_params.get('audit_engagement')
            status_filter = request.query_params.get('status')

            queryset = DeclarationOfIndependence.objects.select_related(
                'audit_engagement', 'audit_memo',
            ).all()

            if engagement_id:
                queryset = queryset.filter(audit_engagement_id=engagement_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            ordering = get_ordering_param(
                request, default='-created_at',
                allowed_fields=['created_at', 'status', 'declarant_name'],
            )
            queryset = queryset.order_by(ordering)

            page_data = paginate_queryset(queryset, request)
            serializer = DeclarationOfIndependenceSerializer(page_data["queryset"], many=True)

            return paginated_list_response(
                items=serializer.data,
                count=page_data["total"],
                page=page_data["page"],
                page_size=page_data["page_size"],
                resource="declaration",
            )
        except Exception as e:
            logger.exception("Failed to retrieve declarations")
            return server_error_response(
                message="Failed to retrieve declarations",
                details=str(e) if settings.DEBUG else None,
            )

    def post(self, request):
        """Create a declaration (or bulk-create for all team members)."""
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated",
                    code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # Support bulk creation: { "audit_engagement_id": "...", "members": [...] }
            bulk_members = request.data.get('members')
            engagement_id = request.data.get('audit_engagement_id')

            if bulk_members and engagement_id:
                engagement = get_object_or_404(AuditEngagement, id=engagement_id)
                created = []
                with transaction.atomic():
                    for member in bulk_members:
                        # Skip if already exists for this engagement + user
                        if DeclarationOfIndependence.objects.filter(
                            audit_engagement=engagement,
                            declarant_user_id=member['user_id'],
                        ).exists():
                            continue
                        decl = DeclarationOfIndependence.objects.create(
                            audit_engagement=engagement,
                            declarant_user_id=member['user_id'],
                            declarant_name=member.get('name', ''),
                            declarant_role=member.get('role', 'team_member'),
                            created_by=user_id,
                        )
                        created.append(decl)

                # GAP 9: upload a PDF to DRS for each declaration so document_id
                # is set and the stamp trigger can fire when all are signed.
                for decl in created:
                    _upload_declaration_pdf_to_drs(decl, auth_token=request.auth)

                serializer = DeclarationOfIndependenceSerializer(created, many=True)
                return Response(
                    {
                        "success": True,
                        "data": serializer.data,
                        "message": f"{len(created)} declaration(s) created",
                    },
                    status=status.HTTP_201_CREATED,
                )

            # Single creation
            serializer = DeclarationOfIndependenceSerializer(data=request.data)
            if serializer.is_valid():
                with transaction.atomic():
                    decl = serializer.save(created_by=user_id)

                # GAP 9: upload PDF to DRS immediately so document_id is set
                # before the declarant clicks Sign.
                _upload_declaration_pdf_to_drs(decl, auth_token=request.auth)

                try:
                    messaging_service.publish_audit_plan_event(
                        event_type=DECLARATION_EVENTS['DECLARATION_CREATED'],
                        plan_id=decl.audit_engagement.audit_plan_id,
                        additional_data={
                            'declaration_id': str(decl.id),
                            'engagement_id': str(decl.audit_engagement_id),
                        },
                    )
                except Exception as event_error:
                    logger.error("Error publishing declaration created event: %s", event_error)

                return Response(
                    {
                        "success": True,
                        "data": DeclarationOfIndependenceSerializer(decl).data,
                        "message": "Declaration created",
                    },
                    status=status.HTTP_201_CREATED,
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to create declaration")
            return server_error_response(
                message="Failed to create declaration",
                details=str(e) if settings.DEBUG else None,
            )


class DeclarationDetailView(APIView):
    """Retrieve or update a declaration."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanManageDeclaration().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_declaration:manage required.')

    def get(self, request, pk):
        try:
            decl = DeclarationOfIndependence.objects.select_related(
                'audit_engagement', 'audit_memo',
            ).get(pk=pk)
            return success_response(
                data=DeclarationOfIndependenceSerializer(decl).data,
                resource="declaration",
            )
        except DeclarationOfIndependence.DoesNotExist:
            return not_found_response(resource="declaration")

    def put(self, request, pk):
        try:
            decl = get_object_or_404(DeclarationOfIndependence, pk=pk)
            if decl.status == 'signed':
                return error_response(
                    message="Signed declarations cannot be modified",
                    code="ALREADY_SIGNED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            serializer = DeclarationOfIndependenceSerializer(decl, data=request.data, partial=True)
            if serializer.is_valid():
                user_id = getattr(request.user, 'id', None)
                with transaction.atomic():
                    serializer.save(modified_by=user_id)
                return success_response(
                    data=DeclarationOfIndependenceSerializer(decl).data,
                    resource="declaration",
                )
            return validation_error_response(serializer.errors)
        except Exception as e:
            logger.exception("Failed to update declaration %s", pk)
            return server_error_response(
                message="Failed to update declaration",
                details=str(e) if settings.DEBUG else None,
            )


class DeclarationSignView(APIView):
    """Team member signs their declaration of independence."""

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanSignDeclaration().has_permission(request, self):
            self.permission_denied(request, message='grc:audit_declaration:sign required.')

    def post(self, request, pk):
        try:
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return error_response(
                    message="User not authenticated",
                    code="AUTH_REQUIRED",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            decl = get_object_or_404(DeclarationOfIndependence, pk=pk)

            # Only the declarant can sign their own declaration
            if str(decl.declarant_user_id) != str(user_id):
                return error_response(
                    message="You can only sign your own declaration",
                    code="NOT_DECLARANT",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            if decl.is_signed:
                return error_response(
                    message="Declaration already signed",
                    code="ALREADY_SIGNED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Check conflict details if conflict reported
            has_conflict = request.data.get('has_conflict', False)
            conflict_details = request.data.get('conflict_details', '')
            if has_conflict and not conflict_details:
                return error_response(
                    message="Conflict details are required when reporting a conflict",
                    code="CONFLICT_DETAILS_REQUIRED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                decl.has_conflict = has_conflict
                decl.conflict_details = conflict_details
                decl.is_signed = True
                decl.signed_at = timezone.now()
                decl.status = 'signed'
                decl.save(update_fields=[
                    'has_conflict', 'conflict_details', 'is_signed', 'signed_at', 'status',
                ])

            # Regenerate the PDF with is_signed=True so the "Digitally Signed" block
            # (name + date) is rendered instead of the blank signature lines.
            # Must happen BEFORE the stamp loop so DRS stamps the correct version.
            if decl.document_id:
                try:
                    import io
                    from apps.core.utils.pdf_generators import generate_declaration_pdf
                    from apps.infrastructure.external.document_service_client import DocumentServiceClient as _DSC
                    _pdf = generate_declaration_pdf(decl)
                    _DSC(auth_token=request.auth).upload_file(
                        document_id=str(decl.document_id),
                        file_data=io.BytesIO(_pdf),
                        file_name=f"declaration_{decl.id}.pdf",
                    )
                    logger.info("GAP 9: Regenerated signed PDF for declaration %s in DRS", decl.id)
                except Exception as _regen_err:
                    logger.warning(
                        "GAP 9: Could not regenerate signed PDF for declaration %s: %s",
                        decl.id, _regen_err,
                    )

            try:
                messaging_service.publish_audit_plan_event(
                    event_type=DECLARATION_EVENTS['DECLARATION_SIGNED'],
                    plan_id=decl.audit_engagement.audit_plan_id,
                    additional_data={
                        'declaration_id': str(decl.id),
                        'engagement_id': str(decl.audit_engagement_id),
                        'declarant': str(user_id),
                    },
                )
            except Exception as event_error:
                logger.error("Error publishing declaration signed event: %s", event_error)

            # GAP 9 / SRS Req 18 + 38: If all declarations for this engagement are
            # now signed, trigger the approved stamp on each declaration that has
            # a DRS document_id set.
            try:
                all_signed = not DeclarationOfIndependence.objects.filter(
                    audit_engagement=decl.audit_engagement,
                    is_active=True,
                ).exclude(status='signed').exists()

                if all_signed:
                    from apps.infrastructure.external.document_service_client import DocumentServiceClient
                    # Use the signer's JWT as auth_token — DRS JWTPermissionMiddleware requires
                    # a Bearer token on every request. X-Service-Token alone is blocked by
                    # middleware before DRF permission classes can check it.
                    client = DocumentServiceClient(auth_token=request.auth)
                    for d in DeclarationOfIndependence.objects.filter(
                        audit_engagement=decl.audit_engagement,
                        is_active=True,
                        status='signed',
                    ).exclude(document_id=None):
                        try:
                            result = client.generate_approved_stamp(
                                document_id=str(d.document_id),
                                approver_id=str(user_id),
                                entity_type='declaration',
                                entity_id=str(d.id),
                            )
                            stamped_url = result.get('stamped_document_url')
                            if stamped_url:
                                # DRS returns an internal Docker URL — rewrite to the
                                # public API gateway URL so the browser can open it.
                                internal_base = settings.DOCUMENT_SERVICE_URL.rstrip('/')
                                public_base = getattr(settings, 'DOCUMENT_SERVICE_PUBLIC_URL', '').rstrip('/')
                                if public_base and stamped_url.startswith(internal_base):
                                    stamped_url = public_base + stamped_url[len(internal_base):]
                                d.stamped_document_url = stamped_url
                                d.save(update_fields=['stamped_document_url'])
                        except Exception as stamp_err:
                            logger.warning(
                                "GAP 9: Stamp failed for Declaration %s: %s", d.id, stamp_err
                            )
            except Exception as gap9_err:
                logger.warning("GAP 9: Declaration stamp check failed: %s", gap9_err)

            # Refresh from DB so the response reflects stamped_document_url if the
            # stamp loop ran above (it updates separate ORM objects, not `decl`).
            decl.refresh_from_db()

            return success_response(
                data=DeclarationOfIndependenceSerializer(decl).data,
                message="Declaration signed successfully",
            )
        except Exception as e:
            logger.exception("Error signing declaration %s", pk)
            return server_error_response(
                message="Failed to sign declaration",
                details=str(e) if settings.DEBUG else None,
            )


class EngagementDeclarationsView(APIView):
    """Get all declarations for a specific engagement."""

    permission_classes = [IsAuthenticated]

    def get(self, request, engagement_id):
        try:
            engagement = get_object_or_404(AuditEngagement, pk=engagement_id)
            declarations = DeclarationOfIndependence.objects.filter(
                audit_engagement=engagement,
            ).order_by('declarant_name')

            serializer = DeclarationOfIndependenceSerializer(declarations, many=True)

            # Summary for the engagement
            total = declarations.count()
            signed = declarations.filter(status='signed').count()
            all_signed = total > 0 and total == signed

            return success_response(data={
                "engagement_id": str(engagement.id),
                "declarations": serializer.data,
                "summary": {
                    "total": total,
                    "signed": signed,
                    "pending": total - signed,
                    "all_signed": all_signed,
                },
            })
        except Exception as e:
            logger.exception("Error fetching declarations for engagement %s", engagement_id)
            return server_error_response(
                message="Failed to fetch engagement declarations",
                details=str(e) if settings.DEBUG else None,
            )
