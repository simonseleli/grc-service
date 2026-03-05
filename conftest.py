"""
Shared pytest fixtures for GRC Service tests.
Builds the full model fixture chain required by WorkingPaper:
  FiscalYear → AuditUniverse → AuditableEntity
                             → AuditPlan → AuditEngagement → WorkingPaper
"""
import uuid
import datetime
from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.core.models import WorkingPaper, AuditEngagement
from apps.core.models.audit_entities import AuditPlan, AuditableEntity, AuditUniverse
from apps.core.models.lookups import FiscalYear


# ---------------------------------------------------------------------------
# Stable UUIDs used across fixtures so tests can assert on them
# ---------------------------------------------------------------------------
PREPARER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER_USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PLAN_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
DOCUMENT_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def make_mock_user(user_id):
    """Return a mock user object accepted by force_authenticate."""
    user = MagicMock()
    user.id = str(user_id)
    user.is_authenticated = True
    return user


@pytest.fixture
def preparer_client():
    """APIClient authenticated as the working paper preparer."""
    client = APIClient()
    client.force_authenticate(user=make_mock_user(PREPARER_ID))
    return client


@pytest.fixture
def other_client():
    """APIClient authenticated as a user who is NOT the preparer."""
    client = APIClient()
    client.force_authenticate(user=make_mock_user(OTHER_USER_ID))
    return client


@pytest.fixture
def anon_client():
    """Unauthenticated APIClient."""
    return APIClient()


# ---------------------------------------------------------------------------
# Model fixtures — full chain
# ---------------------------------------------------------------------------

SYSTEM_USER_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


@pytest.fixture
def fiscal_year(db):
    return FiscalYear.objects.create(
        year_code="2025/2026",
        name="Fiscal Year 2025/2026",
        start_date=datetime.date(2025, 7, 1),
        end_date=datetime.date(2026, 6, 30),
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def audit_universe(db, fiscal_year):
    return AuditUniverse.objects.create(
        fiscal_year=fiscal_year,
        description="Test audit universe",
        status="approved",
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def auditable_entity(db, audit_universe):
    return AuditableEntity.objects.create(
        audit_universe=audit_universe,
        entity_type="unit",
        name="Finance Unit",
        code="FIN-001",
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def audit_plan(db, fiscal_year, audit_universe):
    return AuditPlan.objects.create(
        reference_number="PLAN-001",
        title="Annual Audit Plan",
        fiscal_year=fiscal_year,
        audit_universe=audit_universe,
        prepared_by=PREPARER_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def engagement(db, audit_plan, auditable_entity):
    return AuditEngagement.objects.create(
        reference_number="ENG-001",
        audit_plan=audit_plan,
        auditable_entity=auditable_entity,
        title="Finance Unit Audit",
        lead_auditor=PREPARER_ID,
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def working_paper(db, engagement):
    """A draft working paper with no workflow plan (initial state)."""
    return WorkingPaper.objects.create(
        engagement=engagement,
        reference_number="WP-001",
        title="Test Working Paper",
        paper_type="fieldwork",
        document_id=DOCUMENT_ID,
        prepared_by=PREPARER_ID,
        review_status="draft",
        created_by=SYSTEM_USER_ID,
    )


@pytest.fixture
def working_paper_with_plan(db, engagement):
    """A working paper that already has a workflow plan started."""
    return WorkingPaper.objects.create(
        engagement=engagement,
        reference_number="WP-002",
        title="In-Review Working Paper",
        paper_type="fieldwork",
        document_id=DOCUMENT_ID,
        prepared_by=PREPARER_ID,
        review_status="pending",
        workflow_plan_id=PLAN_ID,
        workflow_stage="working_paper_review",
        workflow_stage_id=uuid.uuid4(),
        created_by=SYSTEM_USER_ID,
    )
