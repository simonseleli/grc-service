"""
GRC Service — JWT-based API permission classes.

Follows the exact pattern of document-records-service/apps/api/permissions_jwt.py:
- Permission codes are extracted from the JWT by JWTPermissionMiddleware and stored
  on request.grc_permissions (list of 'grc:*' codes, or ['*'] for superusers).
- All checks are LOCAL — no HTTP calls to IAM service.
- One named BasePermission subclass per GRC permission code declared in
  config/permissions/grc-service.json.

Usage in views:
    from rest_framework.permissions import IsAuthenticated
    from apps.api.permissions_jwt import CanViewAuditUniverse, CanManageAuditUniverse

    class AuditUniverseListCreateView(APIView):
        permission_classes = [IsAuthenticated]

        def check_permissions(self, request):
            super().check_permissions(request)
            if request.method == 'GET':
                if not CanViewAuditUniverse().has_permission(request, self):
                    self.permission_denied(request, message='grc:audit_universe:view required')
            elif request.method == 'POST':
                if not CanManageAuditUniverse().has_permission(request, self):
                    self.permission_denied(request, message='grc:audit_universe:manage required')
"""
import logging
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helper
# ──────────────────────────────────────────────────────────────────────────────

def _check_grc_permission_locally(request, permission_code: str) -> bool:
    """
    Check a GRC permission code against the list extracted from the JWT by
    JWTPermissionMiddleware (stored in request.grc_permissions).

    Returns True if:
    - grc_permissions is ['*']  (superuser or wildcard grant), or
    - permission_code is in grc_permissions.
    Returns False and logs a warning otherwise.
    """
    if not hasattr(request, 'grc_permissions'):
        logger.warning(
            "request.grc_permissions not found — JWTPermissionMiddleware may not be running. "
            f"Denying: {permission_code}"
        )
        return False

    grc_permissions = request.grc_permissions  # set by JWTPermissionMiddleware

    # Superuser / wildcard grant
    if '*' in grc_permissions:
        logger.info(
            f"Wildcard GRC permissions — granting {permission_code} "
            f"to {getattr(request, 'user_email', 'unknown')}"
        )
        return True

    has_permission = permission_code in grc_permissions

    if not has_permission:
        logger.warning(
            f"Permission denied: user={getattr(request, 'user_email', 'unknown')}, "
            f"required={permission_code}, "
            f"available={grc_permissions[:10]}{'...' if len(grc_permissions) > 10 else ''}"
        )
    else:
        logger.debug(
            f"Permission granted: user={getattr(request, 'user_email', 'unknown')}, "
            f"permission={permission_code}"
        )

    return has_permission


# ──────────────────────────────────────────────────────────────────────────────
# Generic permission classes (mirroring Doc Records' HasPermission family)
# ──────────────────────────────────────────────────────────────────────────────

class HasPermission(BasePermission):
    """
    Generic single-permission check.

    Usage:
        permission_classes = [HasPermission('grc:audit_plan:approve')]
    """

    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, self.permission_code)


class HasAnyPermission(BasePermission):
    """
    User has ANY of the listed permission codes.

    Usage:
        permission_classes = [HasAnyPermission(['grc:audit_plan:view', 'grc:audit_report:view'])]
    """

    def __init__(self, permission_codes: list):
        self.permission_codes = permission_codes

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return any(
            _check_grc_permission_locally(request, code)
            for code in self.permission_codes
        )


class HasAllPermissions(BasePermission):
    """
    User has ALL of the listed permission codes.

    Usage:
        permission_classes = [HasAllPermissions(['grc:audit_plan:view', 'grc:audit_plan:approve'])]
    """

    def __init__(self, permission_codes: list):
        self.permission_codes = permission_codes

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return all(
            _check_grc_permission_locally(request, code)
            for code in self.permission_codes
        )


# ──────────────────────────────────────────────────────────────────────────────
# Named permission classes — one per code in config/permissions/grc-service.json
# ──────────────────────────────────────────────────────────────────────────────

# ── Audit Universe ────────────────────────────────────────────────────────────

class CanViewAuditUniverse(BasePermission):
    """Check: grc:audit_universe:view"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_universe:view')


class CanManageAuditUniverse(BasePermission):
    """Check: grc:audit_universe:manage — create / update audit universes."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_universe:manage')


class CanApproveAuditUniverse(BasePermission):
    """Check: grc:audit_universe:approve — CIA formally approves the audit universe."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_universe:approve')


# ── Risk Assessment ───────────────────────────────────────────────────────────

class CanConductRiskAssessment(BasePermission):
    """Check: grc:risk_assessment:conduct — perform and submit risk assessments."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:risk_assessment:conduct')


class CanReviewRiskAssessment(BasePermission):
    """Check: grc:risk_assessment:review — CIA reviews submitted risk assessments."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:risk_assessment:review')


# ── Audit Plan ────────────────────────────────────────────────────────────────

class CanViewAuditPlan(BasePermission):
    """Check: grc:audit_plan:view"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_plan:view')


class CanManageAuditPlan(BasePermission):
    """Check: grc:audit_plan:manage — IA / LA / CIA create and update draft plans."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_plan:manage')


class CanApproveAuditPlan(BasePermission):
    """Check: grc:audit_plan:approve — CIA / committee approval of RBIAP."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_plan:approve')


# ── Audit Engagement ──────────────────────────────────────────────────────────

class CanManageAuditEngagement(BasePermission):
    """Check: grc:audit_engagement:manage — create, assign, and update engagements."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_engagement:manage')


# ── Working Paper ─────────────────────────────────────────────────────────────

class CanReviewWorkingPaper(BasePermission):
    """Check: grc:audit_working_paper:review — review and approve working papers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_working_paper:review')


class CanManageWorkingPaper(BasePermission):
    """Check: grc:audit_working_paper:manage — IA / LA create and update working papers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_working_paper:manage')


# ── Audit Finding ─────────────────────────────────────────────────────────────

class CanManageAuditFinding(BasePermission):
    """Check: grc:audit_finding:manage — draft, update, and track findings."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_finding:manage')


class CanRespondToAuditFinding(BasePermission):
    """Check: grc:audit_finding:respond — auditee provides auditee_response to a finding."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_finding:respond')


class CanManagementRespondToAuditFinding(BasePermission):
    """Check: grc:audit_finding:management_respond — management provides management_response to a finding."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_finding:management_respond')


# ── Audit Report ──────────────────────────────────────────────────────────────

class CanViewAuditReport(BasePermission):
    """Check: grc:audit_report:view"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_report:view')


class CanApproveAuditReport(BasePermission):
    """Check: grc:audit_report:approve — approve reports for distribution."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_report:approve')


# ── Audit Meeting ─────────────────────────────────────────────────────────────

class CanManageAuditMeeting(BasePermission):
    """Check: grc:audit_meeting:manage — schedule and manage audit meetings."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_meeting:manage')


class CanViewAuditMeeting(BasePermission):
    """Check: grc:audit_meeting:view — read-only access to audit meetings (CIA, audit_committee)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_meeting:view')


# ── Quarterly Audit Report ───────────────────────────────────────────────────

class CanManageQuarterlyReport(BasePermission):
    """Check: grc:quarterly_report:manage — prepare and manage quarterly reports."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:quarterly_report:manage')


class CanApproveQuarterlyReport(BasePermission):
    """Check: grc:quarterly_report:approve — approve and submit quarterly reports."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:quarterly_report:approve')


# ── Implementation Monitoring ─────────────────────────────────────────────────

class CanUpdateAuditMonitoring(BasePermission):
    """Check: grc:audit_monitoring:update — update implementation status."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_monitoring:update')


# ── Analytics Dashboard ───────────────────────────────────────────────────────

class CanViewAuditDashboard(BasePermission):
    """Check: grc:audit_dashboard:view"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_dashboard:view')


# ── Configuration Management ──────────────────────────────────────────────────

class CanManageFiscalYear(BasePermission):
    """Check: grc:config:fiscal_year:manage"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:config:fiscal_year:manage')


class CanManageAuditSeverity(BasePermission):
    """Check: grc:config:audit_severity:manage"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:config:audit_severity:manage')


class CanManageFindingType(BasePermission):
    """Check: grc:config:finding_type:manage"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:config:finding_type:manage')


class CanManageRiskRating(BasePermission):
    """Check: grc:config:risk_rating:manage"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:config:risk_rating:manage')


class CanManageSystemConfig(BasePermission):
    """Check: grc:config:system:manage — system-wide GRC configuration."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:config:system:manage')


# ── Audit Memo (GAP 1) ───────────────────────────────────────────────────────

class CanViewAuditMemo(BasePermission):
    """Check: grc:audit_memo:view"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_memo:view')


class CanManageAuditMemo(BasePermission):
    """Check: grc:audit_memo:manage — LA/CIA create and update memos."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_memo:manage')


class CanApproveAuditMemo(BasePermission):
    """Check: grc:audit_memo:approve — CIA/DG approval of audit memos."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_memo:approve')


# ── Declaration of Independence (GAP 2) ──────────────────────────────────────

class CanManageDeclaration(BasePermission):
    """Check: grc:audit_declaration:manage — create and manage declarations."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_declaration:manage')


class CanSignDeclaration(BasePermission):
    """Check: grc:audit_declaration:sign — team members sign their declarations."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_declaration:sign')


# ── Audit Survey (GAP 3) ─────────────────────────────────────────────────────

class CanManageAuditSurvey(BasePermission):
    """Check: grc:audit_survey:manage — create and manage preliminary surveys."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_survey:manage')


# ── Risk Control Matrix (GAP 4) ──────────────────────────────────────────────

class CanManageRCM(BasePermission):
    """Check: grc:audit_rcm:manage — create and manage risk control matrices."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_rcm:manage')


class CanApproveRCM(BasePermission):
    """Check: grc:audit_rcm:approve — CIA approval of RCM."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_rcm:approve')


# ── Audit Program (GAP 5) ────────────────────────────────────────────────────

class CanManageAuditProgram(BasePermission):
    """Check: grc:audit_program:manage — create and manage audit programs."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_program:manage')


class CanApproveAuditProgram(BasePermission):
    """Check: grc:audit_program:approve — CIA approval of audit programs."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:audit_program:approve')


# ── Engagement Notification (P2-GAP 1) ──────────────────────────────────────

class CanManageEngagementNotification(BasePermission):
    """Check: grc:engagement_notification:manage — create, edit, submit, transmit ENs."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:engagement_notification:manage')


class CanApproveEngagementNotification(BasePermission):
    """Check: grc:engagement_notification:approve — CIA approval of Engagement Notifications."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _check_grc_permission_locally(request, 'grc:engagement_notification:approve')
