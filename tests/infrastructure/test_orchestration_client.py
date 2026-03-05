"""
Unit tests for OrchestrationClient (apps/infrastructure/external/orchestration_client.py).

Coverage:
  _headers()                 — token selection logic
  _plans_url() / _templates_url()  — URL construction
  _get_template_id_by_code() — mapping, HTTP query, caching, error handling
  start_workflow()           — template resolution order, payload shape, response parsing
  get_plan_status()          — happy path, non-200, network error
  get_plan_activity()        — happy/non-200/network, bare vs wrapped response

No Django DB access required — these are pure HTTP-client tests.

guide reference: workflow-integration-guide.md §4.3
"""

import uuid
from unittest.mock import MagicMock, patch, call

import pytest
import requests as requests_lib

# ---------------------------------------------------------------------------
# Import the client. Django settings are initialised by pytest.ini
# (DJANGO_SETTINGS_MODULE = config.settings).
# ---------------------------------------------------------------------------
from apps.infrastructure.external.orchestration_client import (
    OrchestrationClient,
    WorkflowPlanResult,
)


# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

BASE_URL = "http://work-orchestration-service:8004"
PLANS_URL = f"{BASE_URL}/api/v1/workflow/plans/"
TEMPLATES_URL = f"{BASE_URL}/api/v1/workflow/templates/"

TEMPLATE_UUID = str(uuid.uuid4())
PLAN_UUID = str(uuid.uuid4())
STAGE_UUID = str(uuid.uuid4())
AUTH_TOKEN = "Bearer eyJtest"


def _client(base_url=BASE_URL, service_token=None):
    """Build a client with patched Django settings so __init__ never touches DB."""
    with patch("apps.infrastructure.external.orchestration_client.requests"):
        # We only need __init__ to run; requests is re-patched per test.
        pass
    with patch("django.conf.settings") as mock_settings:
        mock_settings.WORK_ORCHESTRATION_SERVICE_URL = base_url
        mock_settings.SERVICE_TO_SERVICE_TOKEN = service_token
        return OrchestrationClient()


def _make_template(workflow_type, uid=None, is_active=True):
    return {"id": uid or str(uuid.uuid4()), "workflow_type": workflow_type, "is_active": is_active}


def _make_stage(stage_id=None, name="review", status="in_progress"):
    return {"id": stage_id or str(uuid.uuid4()), "name": name, "status": status}


# ---------------------------------------------------------------------------
# Autouse: clear the process-lifetime template cache before every test
# so cache hits from one test cannot affect another.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_template_cache():
    OrchestrationClient._template_id_cache.clear()
    yield
    OrchestrationClient._template_id_cache.clear()


# ---------------------------------------------------------------------------
# Fixture: a pre-built client (settings already patched)
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    with patch("django.conf.settings") as mock_settings:
        mock_settings.WORK_ORCHESTRATION_SERVICE_URL = BASE_URL
        mock_settings.SERVICE_TO_SERVICE_TOKEN = None
        return OrchestrationClient()


@pytest.fixture
def client_with_service_token():
    with patch("django.conf.settings") as mock_settings:
        mock_settings.WORK_ORCHESTRATION_SERVICE_URL = BASE_URL
        mock_settings.SERVICE_TO_SERVICE_TOKEN = "service-token-xyz"
        return OrchestrationClient()


# ===========================================================================
# _headers()
# ===========================================================================

class TestHeaders:
    """Token selection: caller token > service token > no header."""

    def test_auth_token_takes_priority_over_service_token(self, client_with_service_token):
        headers = client_with_service_token._headers(auth_token="caller-token")
        assert headers["Authorization"] == "Bearer caller-token"

    def test_service_token_used_when_no_caller_token(self, client_with_service_token):
        headers = client_with_service_token._headers()
        assert headers["Authorization"] == "Bearer service-token-xyz"

    def test_no_auth_header_when_no_tokens(self, client):
        headers = client._headers()
        assert "Authorization" not in headers

    def test_content_type_always_set(self, client):
        assert client._headers()["Content-Type"] == "application/json"


# ===========================================================================
# URL helpers
# ===========================================================================

class TestUrls:
    def test_plans_url(self, client):
        assert client._plans_url() == PLANS_URL

    def test_templates_url(self, client):
        assert client._templates_url() == TEMPLATES_URL

    def test_trailing_slash_stripped_from_base(self):
        with patch("django.conf.settings") as s:
            s.WORK_ORCHESTRATION_SERVICE_URL = "http://wo:8004/"
            s.SERVICE_TO_SERVICE_TOKEN = None
            c = OrchestrationClient()
        assert c._plans_url() == "http://wo:8004/api/v1/workflow/plans/"


# ===========================================================================
# _get_template_id_by_code()
# ===========================================================================

class TestGetTemplateIdByCode:
    """
    guide §4.3: Client resolves template UUID from WO's template list API.
    """

    def test_returns_uuid_for_known_code(self, client):
        """Happy path: WO returns matching active template."""
        template = _make_template("grc_rbiap_approval", uid=TEMPLATE_UUID)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [template]

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = client._get_template_id_by_code("grc.rbiap_approval", auth_token=AUTH_TOKEN)

        assert result == TEMPLATE_UUID
        mock_get.assert_called_once_with(
            TEMPLATES_URL,
            headers=client._headers(AUTH_TOKEN),
            timeout=5,
        )

    def test_result_is_cached_after_first_lookup(self, client):
        """Second call must use the cache — no second HTTP request."""
        template = _make_template("grc_rbiap_approval", uid=TEMPLATE_UUID)
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = [template]

        with patch("requests.get", return_value=mock_resp) as mock_get:
            r1 = client._get_template_id_by_code("grc.rbiap_approval")
            r2 = client._get_template_id_by_code("grc.rbiap_approval")

        assert r1 == r2 == TEMPLATE_UUID
        assert mock_get.call_count == 1, "should not call WO again after cache hit"

    def test_returns_none_for_unknown_template_code(self, client):
        """template_code not in TEMPLATE_CODE_TO_WO_TYPE → None immediately."""
        with patch("requests.get") as mock_get:
            result = client._get_template_id_by_code("grc.does_not_exist")

        assert result is None
        mock_get.assert_not_called()

    def test_returns_none_when_wo_returns_non_200(self, client):
        mock_resp = MagicMock(status_code=503)
        with patch("requests.get", return_value=mock_resp):
            result = client._get_template_id_by_code("grc.rbiap_approval")
        assert result is None

    def test_returns_none_when_workflow_type_not_in_list(self, client):
        """WO seeded but this particular workflow_type is absent."""
        other_template = _make_template("grc_working_paper_approval", uid=str(uuid.uuid4()))
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = [other_template]

        with patch("requests.get", return_value=mock_resp):
            result = client._get_template_id_by_code("grc.rbiap_approval")

        assert result is None
        assert "grc.rbiap_approval" not in OrchestrationClient._template_id_cache

    def test_returns_none_on_network_exception(self, client):
        with patch("requests.get", side_effect=requests_lib.ConnectionError("refused")):
            result = client._get_template_id_by_code("grc.rbiap_approval")
        assert result is None

    def test_skips_inactive_template_finds_active(self, client):
        """is_active=False templates must be skipped; the active one wins."""
        inactive = _make_template("grc_rbiap_approval", uid="inactive-uuid", is_active=False)
        active   = _make_template("grc_rbiap_approval", uid=TEMPLATE_UUID, is_active=True)
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = [inactive, active]

        with patch("requests.get", return_value=mock_resp):
            result = client._get_template_id_by_code("grc.rbiap_approval")

        assert result == TEMPLATE_UUID

    def test_handles_data_wrapped_response(self, client):
        """
        Defensive: if WO ever wraps template list as {"data": [...]}
        (verified: current WO template_views.py returns a bare list,
        but we handle both for forward compatibility).
        """
        template = _make_template("grc_rbiap_approval", uid=TEMPLATE_UUID)
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": [template]}

        with patch("requests.get", return_value=mock_resp):
            result = client._get_template_id_by_code("grc.rbiap_approval")

        assert result == TEMPLATE_UUID

    def test_all_known_codes_have_wo_type_mapping(self):
        """Smoke: every code in TEMPLATE_CODE_TO_WO_TYPE maps to a non-empty string."""
        for code, wo_type in OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE.items():
            assert isinstance(code, str) and code
            assert isinstance(wo_type, str) and wo_type


# ===========================================================================
# start_workflow()
# ===========================================================================

class TestStartWorkflow:
    """
    guide §4.3 — Resolution order:
      1. Caller-supplied template_id (explicit override)
      2. _get_template_id_by_code() (WO lookup)
      3. Inline stages fallback
    """

    def _post_response(self, plan_id=None, extra_stages=None):
        """Build a realistic WO 201 response body."""
        stages = extra_stages or [_make_stage(name="working_paper_review")]
        return {
            "data": {
                "id": plan_id or PLAN_UUID,
                "status": "active",
                "stages": stages,
                "metadata": {"subject_ref": "entity-123"},
                "created_at": "2026-02-20T10:00:00Z",
            }
        }

    # ----- Payload shape tests -----

    def test_uses_template_id_in_payload_when_resolved(self, client):
        """When _get_template_id_by_code resolves, payload must have template_id, no stages."""
        mock_get = MagicMock(status_code=200)
        mock_get.json.return_value = [_make_template("grc_rbiap_approval", uid=TEMPLATE_UUID)]

        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response()

        with patch("requests.get", return_value=mock_get), \
             patch("requests.post", return_value=mock_post) as post_spy:
            client.start_workflow(
                template_code="grc.rbiap_approval",
                context={"user_id": "u1"},
                initiator_id="u1",
                stages=[{"name": "step1"}],
            )

        payload = post_spy.call_args.kwargs["json"]
        assert payload["template_id"] == TEMPLATE_UUID
        assert "stages" not in payload, "stages must NOT be sent when template_id is resolved"

    def test_uses_inline_stages_when_template_not_found(self, client):
        """When WO has no seeded template, payload must use inline stages, no template_id."""
        mock_get = MagicMock(status_code=200)
        mock_get.json.return_value = []  # WO has no matching template

        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response()

        inline_stages = [{"name": "manual_step", "definition_key": "approval"}]
        with patch("requests.get", return_value=mock_get), \
             patch("requests.post", return_value=mock_post) as post_spy:
            client.start_workflow(
                template_code="grc.rbiap_approval",
                context={},
                initiator_id="u1",
                stages=inline_stages,
            )

        payload = post_spy.call_args.kwargs["json"]
        assert payload["stages"] == inline_stages
        assert "template_id" not in payload

    def test_caller_supplied_template_id_skips_lookup(self, client):
        """Explicit template_id must bypass _get_template_id_by_code entirely."""
        explicit_id = str(uuid.uuid4())
        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response()

        with patch("requests.get") as get_spy, \
             patch("requests.post", return_value=mock_post) as post_spy:
            client.start_workflow(
                template_code="grc.rbiap_approval",
                context={},
                initiator_id="u1",
                template_id=explicit_id,
            )

        get_spy.assert_not_called()  # no WO template lookup
        payload = post_spy.call_args.kwargs["json"]
        assert payload["template_id"] == explicit_id

    def test_returns_none_when_no_template_and_no_stages(self, client):
        """Guard: neither template_id resolved nor stages provided → return None."""
        mock_get = MagicMock(status_code=200)
        mock_get.json.return_value = []

        with patch("requests.get", return_value=mock_get), \
             patch("requests.post") as post_spy:
            result = client.start_workflow(
                template_code="grc.rbiap_approval",
                context={},
                initiator_id="u1",
                stages=None,
            )

        assert result is None
        post_spy.assert_not_called()

    # ----- combined_metadata tests -----

    def test_metadata_embeds_context_subject_ref_template_code(self, client):
        """guide §4.3: context + subject_ref + template_code must live inside metadata."""
        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response()

        context = {"prepared_by": "u1", "engagement_id": "eng-1"}
        subject_ref = "entity-abc"
        entity_metadata = {"paper_title": "Test Paper"}

        with patch("requests.get", return_value=MagicMock(status_code=200, **{"json.return_value": []})), \
             patch("requests.post", return_value=mock_post) as post_spy:
            client.start_workflow(
                template_code="grc.working_paper_approval",
                context=context,
                initiator_id="u1",
                subject_ref=subject_ref,
                metadata=entity_metadata,
                stages=[{"name": "step"}],
            )

        meta = post_spy.call_args.kwargs["json"]["metadata"]
        assert meta["context"] == context
        assert meta["subject_ref"] == subject_ref
        assert meta["template_code"] == "grc.working_paper_approval"
        assert meta["paper_title"] == "Test Paper"

    def test_workflow_type_derived_from_template_code_prefix(self, client):
        """workflow_type sent to WO must be the prefix before the first '.'."""
        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response()

        with patch("requests.get", return_value=MagicMock(status_code=200, **{"json.return_value": []})), \
             patch("requests.post", return_value=mock_post) as post_spy:
            client.start_workflow(
                template_code="grc.rbiap_approval",
                context={},
                initiator_id="u1",
                stages=[{"name": "step"}],
            )

        payload = post_spy.call_args.kwargs["json"]
        assert payload["workflow_type"] == "grc"

    def test_created_by_set_to_initiator_id(self, client):
        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response()

        with patch("requests.get", return_value=MagicMock(status_code=200, **{"json.return_value": []})), \
             patch("requests.post", return_value=mock_post) as post_spy:
            client.start_workflow(
                template_code="grc.rbiap_approval",
                context={},
                initiator_id="user-xyz",
                stages=[{"name": "step"}],
            )

        assert post_spy.call_args.kwargs["json"]["created_by"] == "user-xyz"

    # ----- Response parsing tests -----

    def test_returns_workflow_plan_result_on_201(self, client):
        stage = _make_stage(stage_id=STAGE_UUID, name="rbiap_review", status="in_progress")
        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response(plan_id=PLAN_UUID, extra_stages=[stage])

        with patch("requests.get", return_value=MagicMock(status_code=200, **{"json.return_value": []})), \
             patch("requests.post", return_value=mock_post):
            result = client.start_workflow(
                template_code="grc.rbiap_approval",
                context={},
                initiator_id="u1",
                stages=[{"name": "step"}],
            )

        assert isinstance(result, WorkflowPlanResult)
        assert result.plan_id == PLAN_UUID
        assert result.status == "active"
        assert result.current_stage_id == STAGE_UUID
        assert result.current_stage_name == "rbiap_review"

    def test_current_stage_picks_in_progress_over_first(self, client):
        """When multiple stages exist, the in_progress one should be current_stage."""
        pending = _make_stage(name="stage_A", status="pending")
        active  = _make_stage(stage_id=STAGE_UUID, name="stage_B", status="in_progress")

        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response(extra_stages=[pending, active])

        with patch("requests.get", return_value=MagicMock(status_code=200, **{"json.return_value": []})), \
             patch("requests.post", return_value=mock_post):
            result = client.start_workflow(
                template_code="grc.rbiap_approval", context={}, initiator_id="u1",
                stages=[{"name": "step"}],
            )

        assert result.current_stage_name == "stage_B"

    def test_current_stage_falls_back_to_first_when_none_in_progress(self, client):
        """If no stage has status=in_progress, fall back to stages[0]."""
        s0 = _make_stage(stage_id=STAGE_UUID, name="stage_first", status="pending")
        s1 = _make_stage(name="stage_second", status="pending")

        mock_post = MagicMock(status_code=201)
        mock_post.json.return_value = self._post_response(extra_stages=[s0, s1])

        with patch("requests.get", return_value=MagicMock(status_code=200, **{"json.return_value": []})), \
             patch("requests.post", return_value=mock_post):
            result = client.start_workflow(
                template_code="grc.rbiap_approval", context={}, initiator_id="u1",
                stages=[{"name": "step"}],
            )

        assert result.current_stage_id == STAGE_UUID

    def test_returns_none_on_non_201(self, client):
        mock_post = MagicMock(status_code=400, text='{"detail":"bad request"}')
        with patch("requests.get", return_value=MagicMock(status_code=200, **{"json.return_value": []})), \
             patch("requests.post", return_value=mock_post):
            result = client.start_workflow(
                template_code="grc.rbiap_approval", context={}, initiator_id="u1",
                stages=[{"name": "step"}],
            )
        assert result is None

    def test_returns_none_on_network_error(self, client):
        with patch("requests.get", return_value=MagicMock(status_code=200, **{"json.return_value": []})), \
             patch("requests.post", side_effect=requests_lib.ConnectionError("timeout")):
            result = client.start_workflow(
                template_code="grc.rbiap_approval", context={}, initiator_id="u1",
                stages=[{"name": "step"}],
            )
        assert result is None


# ===========================================================================
# get_plan_status()
# ===========================================================================

class TestGetPlanStatus:
    def test_returns_data_dict_on_200(self, client):
        expected = {"id": PLAN_UUID, "status": "active", "stages": []}
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": expected}

        with patch("requests.get", return_value=mock_resp):
            result = client.get_plan_status(PLAN_UUID, auth_token=AUTH_TOKEN)

        assert result == expected

    def test_unwraps_bare_200_response(self, client):
        """WO may return a bare dict (no "data" key)."""
        bare = {"id": PLAN_UUID, "status": "active"}
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = bare

        with patch("requests.get", return_value=mock_resp):
            result = client.get_plan_status(PLAN_UUID)

        assert result == bare

    def test_returns_none_on_404(self, client):
        mock_resp = MagicMock(status_code=404)
        with patch("requests.get", return_value=mock_resp):
            result = client.get_plan_status(PLAN_UUID)
        assert result is None

    def test_returns_none_on_network_error(self, client):
        with patch("requests.get", side_effect=requests_lib.Timeout("slow")):
            result = client.get_plan_status(PLAN_UUID)
        assert result is None

    def test_correct_url_called(self, client):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": {}}

        with patch("requests.get", return_value=mock_resp) as get_spy:
            client.get_plan_status(PLAN_UUID)

        called_url = get_spy.call_args.args[0]
        assert called_url == f"{PLANS_URL}{PLAN_UUID}/"


# ===========================================================================
# get_plan_activity()
# ===========================================================================

class TestGetPlanActivity:
    def _activity_event(self, action="submitted"):
        return {"action": action, "actor": "user-1", "timestamp": "2026-02-20T10:05:00Z"}

    def test_returns_list_on_200(self, client):
        events = [self._activity_event(), self._activity_event("approved")]
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = events  # bare list

        with patch("requests.get", return_value=mock_resp):
            result = client.get_plan_activity(PLAN_UUID)

        assert result == events

    def test_unwraps_data_wrapped_response(self, client):
        events = [self._activity_event()]
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": events}

        with patch("requests.get", return_value=mock_resp):
            result = client.get_plan_activity(PLAN_UUID)

        assert result == events

    def test_returns_empty_list_on_non_200(self, client):
        mock_resp = MagicMock(status_code=403)
        with patch("requests.get", return_value=mock_resp):
            result = client.get_plan_activity(PLAN_UUID)
        assert result == []

    def test_returns_empty_list_on_network_error(self, client):
        with patch("requests.get", side_effect=requests_lib.ConnectionError("refused")):
            result = client.get_plan_activity(PLAN_UUID)
        assert result == []

    def test_correct_url_called(self, client):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = []

        with patch("requests.get", return_value=mock_resp) as get_spy:
            client.get_plan_activity(PLAN_UUID)

        called_url = get_spy.call_args.args[0]
        assert called_url == f"{PLANS_URL}{PLAN_UUID}/activity/"


# ===========================================================================
# TEMPLATE_CODE_TO_WO_TYPE — contract smoke tests
# ===========================================================================

class TestTemplateMappingContract:
    """Ensure the mapping constant stays coherent as the codebase evolves."""

    EXPECTED_CODES = {
        "grc.working_paper_approval",
        "grc.audit_universe_approval",
        "grc.rbiap_approval",
        "grc.engagement_notification",
        "grc.audit_report_approval",
    }

    def test_all_expected_codes_present(self):
        assert self.EXPECTED_CODES <= set(OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE.keys())

    def test_all_wo_types_are_snake_case(self):
        """WO workflow_type values must be snake_case (no dots or dashes)."""
        for wo_type in OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE.values():
            assert "." not in wo_type, f"workflow_type '{wo_type}' must not contain dots"
            assert "-" not in wo_type, f"workflow_type '{wo_type}' must not contain dashes"

    def test_all_codes_start_with_grc_prefix(self):
        for code in OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE:
            assert code.startswith("grc."), f"template_code '{code}' must start with 'grc.'"
