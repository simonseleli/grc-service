"""
Risk Management Module — RBAC / Permission tests.

Verifies that:
  - Unauthenticated requests → 401
  - Authenticated without grc_permissions → 403  (deny_all_permissions fixture)
  - Correct permission codes grant access (mocked specific codes)
  - All 27 named permission classes enforce auth and check correct codes
  - Role→permission mapping in grc-service.json is consistent

Tests one representative endpoint per lookup group.
Note: Business entity API endpoints are not yet implemented (Phase 7+),
so endpoint tests focus on lookup/config endpoints implemented in Phase 3.
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from apps.api.permissions_jwt import (
    _check_grc_permission_locally,
    HasPermission,
    HasAnyPermission,
    HasAllPermissions,
    CanViewRiskChampion,
    CanManageRiskChampion,
    CanConductRiskAssessmentRM,
    CanReviewRiskAssessmentRM,
    CanManageDeptRiskRegister,
    CanApproveDeptRiskRegister,
    CanManageInstitutionalRiskRegister,
    CanApproveInstitutionalRiskRegister,
    CanManageRTAP,
    CanApproveRTAP,
    CanRespondRTAP,
    CanManageQuarterlyRiskReport,
    CanApproveQuarterlyRiskReport,
    CanManageQualityAuditor,
    CanManageQMSAuditProgram,
    CanApproveQMSAuditProgram,
    CanManageQMSAuditPlan,
    CanApproveQMSAuditPlan,
    CanManageQMSChecklist,
    CanManageQMSAuditReport,
    CanSignQMSAuditReport,
    CanManageNonConformance,
    CanRespondNonConformance,
    CanViewRiskDashboard,
    CanManageRiskMeeting,
    CanViewRiskMeeting,
    CanManageQATraining,
)

from tests.risk_management.conftest import RMQAM_USER_ID


def _mock_risk_permission(request, code):
    """Allow only specific risk management permission codes."""
    allowed = {
        'grc:risk_management:view',
        'grc:risk_management:manage',
        'grc:audit_plan:view',
    }
    return code in allowed


def _make_authed_request(grc_permissions=None):
    """Create a mock authenticated request with grc_permissions."""
    request = MagicMock()
    request.user.is_authenticated = True
    request.grc_permissions = grc_permissions or []
    request.user_email = 'test@example.com'
    return request


def _make_unauthed_request():
    """Create a mock unauthenticated request."""
    request = MagicMock()
    request.user = None
    return request


# ═══════════════════════════════════════════════════════════════════════════════
# Permission class unit tests — each class checks the correct code
# ═══════════════════════════════════════════════════════════════════════════════

PERMISSION_CLASS_MAP = [
    (CanViewRiskChampion, 'grc:risk_champion:view'),
    (CanManageRiskChampion, 'grc:risk_champion:manage'),
    (CanConductRiskAssessmentRM, 'grc:risk_assessment:conduct'),
    (CanReviewRiskAssessmentRM, 'grc:risk_assessment:review'),
    (CanManageDeptRiskRegister, 'grc:dept_risk_register:manage'),
    (CanApproveDeptRiskRegister, 'grc:dept_risk_register:approve'),
    (CanManageInstitutionalRiskRegister, 'grc:institutional_risk_register:manage'),
    (CanApproveInstitutionalRiskRegister, 'grc:institutional_risk_register:approve'),
    (CanManageRTAP, 'grc:rtap:manage'),
    (CanApproveRTAP, 'grc:rtap:approve'),
    (CanRespondRTAP, 'grc:rtap:respond'),
    (CanManageQuarterlyRiskReport, 'grc:quarterly_risk_report:manage'),
    (CanApproveQuarterlyRiskReport, 'grc:quarterly_risk_report:approve'),
    (CanManageQualityAuditor, 'grc:quality_auditor:manage'),
    (CanManageQMSAuditProgram, 'grc:qms_audit_program:manage'),
    (CanApproveQMSAuditProgram, 'grc:qms_audit_program:approve'),
    (CanManageQMSAuditPlan, 'grc:qms_audit_plan:manage'),
    (CanApproveQMSAuditPlan, 'grc:qms_audit_plan:approve'),
    (CanManageQMSChecklist, 'grc:qms_checklist:manage'),
    (CanManageQMSAuditReport, 'grc:qms_audit_report:manage'),
    (CanSignQMSAuditReport, 'grc:qms_audit_report:sign'),
    (CanManageNonConformance, 'grc:non_conformance:manage'),
    (CanRespondNonConformance, 'grc:non_conformance:respond'),
    (CanViewRiskDashboard, 'grc:risk_dashboard:view'),
    (CanManageRiskMeeting, 'grc:risk_meeting:manage'),
    (CanViewRiskMeeting, 'grc:risk_meeting:view'),
    (CanManageQATraining, 'grc:qa_training:manage'),
]


class TestRiskManagementPermissionClasses:
    """Unit tests for all 27 risk management permission classes."""

    @pytest.mark.parametrize(
        'perm_class,code',
        PERMISSION_CLASS_MAP,
        ids=[cls.__name__ for cls, _ in PERMISSION_CLASS_MAP],
    )
    def test_unauthenticated_denied(self, perm_class, code):
        request = _make_unauthed_request()
        assert perm_class().has_permission(request, None) is False

    @pytest.mark.parametrize(
        'perm_class,code',
        PERMISSION_CLASS_MAP,
        ids=[cls.__name__ for cls, _ in PERMISSION_CLASS_MAP],
    )
    def test_no_permissions_denied(self, perm_class, code):
        request = _make_authed_request(grc_permissions=[])
        assert perm_class().has_permission(request, None) is False

    @pytest.mark.parametrize(
        'perm_class,code',
        PERMISSION_CLASS_MAP,
        ids=[cls.__name__ for cls, _ in PERMISSION_CLASS_MAP],
    )
    def test_correct_permission_granted(self, perm_class, code):
        request = _make_authed_request(grc_permissions=[code])
        assert perm_class().has_permission(request, None) is True

    @pytest.mark.parametrize(
        'perm_class,code',
        PERMISSION_CLASS_MAP,
        ids=[cls.__name__ for cls, _ in PERMISSION_CLASS_MAP],
    )
    def test_wrong_permission_denied(self, perm_class, code):
        request = _make_authed_request(grc_permissions=['grc:some_other:view'])
        assert perm_class().has_permission(request, None) is False

    @pytest.mark.parametrize(
        'perm_class,code',
        PERMISSION_CLASS_MAP,
        ids=[cls.__name__ for cls, _ in PERMISSION_CLASS_MAP],
    )
    def test_wildcard_granted(self, perm_class, code):
        request = _make_authed_request(grc_permissions=['*'])
        assert perm_class().has_permission(request, None) is True


class TestHelperFunction:
    """Tests for _check_grc_permission_locally."""

    def test_missing_grc_permissions_attr(self):
        request = MagicMock(spec=[])  # no grc_permissions attr
        assert _check_grc_permission_locally(request, 'grc:risk_champion:view') is False

    def test_wildcard_grants_any_code(self):
        request = _make_authed_request(grc_permissions=['*'])
        assert _check_grc_permission_locally(request, 'grc:anything:here') is True

    def test_exact_match(self):
        request = _make_authed_request(grc_permissions=['grc:rtap:manage'])
        assert _check_grc_permission_locally(request, 'grc:rtap:manage') is True

    def test_no_match(self):
        request = _make_authed_request(grc_permissions=['grc:rtap:manage'])
        assert _check_grc_permission_locally(request, 'grc:rtap:approve') is False


class TestGenericPermissionClasses:
    """Tests for HasPermission, HasAnyPermission, HasAllPermissions."""

    def test_has_permission_granted(self):
        request = _make_authed_request(grc_permissions=['grc:risk_champion:view'])
        assert HasPermission('grc:risk_champion:view').has_permission(request, None) is True

    def test_has_permission_denied(self):
        request = _make_authed_request(grc_permissions=[])
        assert HasPermission('grc:risk_champion:view').has_permission(request, None) is False

    def test_has_any_permission_one_match(self):
        request = _make_authed_request(grc_permissions=['grc:rtap:manage'])
        perm = HasAnyPermission(['grc:rtap:manage', 'grc:rtap:approve'])
        assert perm.has_permission(request, None) is True

    def test_has_any_permission_none_match(self):
        request = _make_authed_request(grc_permissions=['grc:other:view'])
        perm = HasAnyPermission(['grc:rtap:manage', 'grc:rtap:approve'])
        assert perm.has_permission(request, None) is False

    def test_has_all_permissions_all_present(self):
        request = _make_authed_request(
            grc_permissions=['grc:rtap:manage', 'grc:rtap:approve']
        )
        perm = HasAllPermissions(['grc:rtap:manage', 'grc:rtap:approve'])
        assert perm.has_permission(request, None) is True

    def test_has_all_permissions_partial(self):
        request = _make_authed_request(grc_permissions=['grc:rtap:manage'])
        perm = HasAllPermissions(['grc:rtap:manage', 'grc:rtap:approve'])
        assert perm.has_permission(request, None) is False


# ═══════════════════════════════════════════════════════════════════════════════
# grc-service.json consistency tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGRCServiceJSON:
    """Validates risk management entries in grc-service.json."""

    @pytest.fixture(autouse=True)
    def load_json(self):
        json_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', 'config', 'permissions', 'grc-service.json',
        )
        with open(json_path) as f:
            self.data = json.load(f)
        self.permissions = self.data['permissions']
        self.roles = self.data['roles']
        self.perm_codes = {p['permission_code'] for p in self.permissions}

    def test_all_27_risk_management_codes_present(self):
        expected = {code for _, code in PERMISSION_CLASS_MAP}
        missing = expected - self.perm_codes
        assert not missing, f"Missing permission codes in grc-service.json: {missing}"

    def test_risk_management_permissions_have_correct_category(self):
        # risk_assessment:conduct and risk_assessment:review are shared codes
        # that existed in Internal Audit with category=risk_assessment — skip them
        shared_codes = {'grc:risk_assessment:conduct', 'grc:risk_assessment:review'}
        rm_codes = {code for _, code in PERMISSION_CLASS_MAP} - shared_codes
        for perm in self.permissions:
            if perm['permission_code'] in rm_codes:
                assert perm['category'] == 'risk_management', (
                    f"{perm['permission_code']} has category={perm['category']}, expected risk_management"
                )

    def test_rmqam_role_exists(self):
        rmqam = [r for r in self.roles if r['code'] == 'rmqam']
        assert len(rmqam) == 1

    def test_rmo_role_exists(self):
        rmo = [r for r in self.roles if r['code'] == 'rmo']
        assert len(rmo) == 1

    def test_lsm_role_exists(self):
        lsm = [r for r in self.roles if r['code'] == 'lsm']
        assert len(lsm) == 1

    def test_risk_champion_role_exists(self):
        rc = [r for r in self.roles if r['code'] == 'risk_champion']
        assert len(rc) == 1

    def test_quality_auditor_role_exists(self):
        qa = [r for r in self.roles if r['code'] == 'quality_auditor']
        assert len(qa) == 1

    def test_role_permissions_are_valid_codes(self):
        rm_roles = ['rmqam', 'rmo', 'lsm', 'risk_champion', 'quality_auditor']
        for role in self.roles:
            if role['code'] in rm_roles:
                for perm_code in role['permissions']:
                    assert perm_code in self.perm_codes, (
                        f"Role {role['code']} references unknown permission: {perm_code}"
                    )

    def test_rmqam_has_dashboard_access(self):
        rmqam = [r for r in self.roles if r['code'] == 'rmqam'][0]
        assert 'grc:risk_dashboard:view' in rmqam['permissions']

    def test_risk_champion_cannot_approve_registers(self):
        rc = [r for r in self.roles if r['code'] == 'risk_champion'][0]
        assert 'grc:dept_risk_register:approve' not in rc['permissions']
        assert 'grc:institutional_risk_register:approve' not in rc['permissions']

    def test_quality_auditor_has_checklist_access(self):
        qa = [r for r in self.roles if r['code'] == 'quality_auditor'][0]
        assert 'grc:qms_checklist:manage' in qa['permissions']

    def test_risk_assessment_conduct_and_review_are_separate(self):
        assert 'grc:risk_assessment:conduct' in self.perm_codes
        assert 'grc:risk_assessment:review' in self.perm_codes


# ═══════════════════════════════════════════════════════════════════════════════
# Lookup endpoint permissions (Phase 3 endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLookupPermissions:

    @pytest.mark.django_db
    def test_risk_categories_unauthenticated_401(self, anon_client, risk_category):
        resp = anon_client.get('/api/v1/grc/audit/lookups/risk-categories/')
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_risk_categories_no_perms_403(self, rmqam_client, risk_category, deny_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk-categories/')
        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_risk_categories_with_perm_200(self, rmqam_client, risk_category):
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_mock_risk_permission,
        ):
            resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk-categories/')
        assert resp.status_code == 200

    @pytest.mark.django_db
    def test_combined_lookup_unauthenticated_401(self, anon_client):
        resp = anon_client.get('/api/v1/grc/audit/lookups/risk/')
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_combined_lookup_no_perms_403(self, rmqam_client, deny_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk/')
        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_iso_clauses_unauthenticated_401(self, anon_client, iso_clause):
        resp = anon_client.get('/api/v1/grc/audit/lookups/iso-clauses/')
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_iso_clauses_no_perms_403(self, rmqam_client, iso_clause, deny_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/iso-clauses/')
        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_nc_types_unauthenticated_401(self, anon_client, nc_type_major):
        resp = anon_client.get('/api/v1/grc/audit/lookups/non-conformance-types/')
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Config endpoint permissions
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfigPermissions:

    @pytest.mark.django_db
    def test_config_risk_categories_unauthenticated_401(self, anon_client):
        resp = anon_client.get('/api/v1/grc/config/risk-categories/')
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_config_risk_categories_get_no_extra_perms_200(self, rmqam_client, deny_all_permissions):
        """Config GET only requires IsAuthenticated (no extra GRC perm check)."""
        resp = rmqam_client.get('/api/v1/grc/config/risk-categories/')
        assert resp.status_code == 200

    @pytest.mark.django_db
    def test_config_risk_categories_with_perm_200(self, rmqam_client, risk_category):
        with patch(
            'apps.api.permissions_jwt._check_grc_permission_locally',
            side_effect=_mock_risk_permission,
        ):
            resp = rmqam_client.get('/api/v1/grc/config/risk-categories/')
        assert resp.status_code == 200
