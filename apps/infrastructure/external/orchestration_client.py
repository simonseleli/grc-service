"""
OrchestrationClient for Work Orchestration Service API (FIMS pattern).

Public API follows the workflow-integration-guide.md §4.3:
  start_workflow(template_code, context, initiator_id, subject_ref, metadata)

The client implements _get_template_id_by_code() (guide §4.3 pattern) which
queries WO's template list API at runtime to resolve the UUID for a given
template_code. Results are cached for the process lifetime. If WO templates
are not yet seeded, the client falls back to inline stage definitions.

Verified against: work-orchestration-service/apps/api/serializers/workflow_serializers.py
- WorkflowStartRequestSerializer accepts: template_id, workflow_type, created_by,
  metadata, stages, tags, sla
- Plans endpoint:     GET/POST /api/v1/workflow/plans/
- Templates endpoint: GET      /api/v1/workflow/templates/
- Activity endpoint:  GET      /api/v1/workflow/plans/{plan_id}/activity/
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class WorkflowPlanResult:
    plan_id: str
    status: str
    current_stage_id: Optional[str]
    current_stage_name: Optional[str]
    stages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: Optional[str] = None


class OrchestrationClient:
    """
    HTTP client for Work Orchestration Service.

    Guide-aligned usage (§4.3):
        client = OrchestrationClient()
        result = client.start_workflow(
            template_code="grc.working_paper_approval",
            context=entity.get_workflow_context(),
            initiator_id=str(user.id),
            subject_ref=str(entity.id),
            metadata=entity.get_workflow_metadata(),
            stages=entity.get_workflow_stages(),   # inline fallback; used when WO template not found
        )
    """

    # Maps GRC template_code → WO workflow_type (set in WO seed_workflow_templates.py).
    # Used by _get_template_id_by_code() to look up the UUID from WO at runtime.
    TEMPLATE_CODE_TO_WO_TYPE: Dict[str, str] = {
        "grc.working_paper_approval":  "grc_working_paper_approval",
        "grc.audit_universe_approval": "grc_audit_universe_approval",
        "grc.rbiap_approval":          "grc_rbiap_approval",
        "grc.engagement_notification": "grc_engagement_lifecycle",
        "grc.audit_report_approval":   "grc_audit_report_approval",
    }

    # Process-lifetime cache: template_code → UUID string.
    # Populated on first successful lookup; cleared by process restart.
    _template_id_cache: Dict[str, str] = {}

    def __init__(self):
        from django.conf import settings as _settings
        self.base_url = getattr(
            _settings, 'WORK_ORCHESTRATION_SERVICE_URL', 'http://work-orchestration-service:8004'
        ).rstrip('/')
        self.service_token = getattr(_settings, 'SERVICE_TO_SERVICE_TOKEN', None)

    def _headers(self, auth_token: Optional[str] = None) -> Dict[str, str]:
        """
        Build request headers.

        - If a caller-supplied JWT ``auth_token`` is present, send it as
          ``Authorization: Bearer <jwt>`` so WO resolves the real user.
        - Otherwise fall back to ``SERVICE_TO_SERVICE_TOKEN`` sent as
          ``X-Service-Token`` — the header WO's ``JWTPermissionMiddleware``
          reads for service-to-service auth (matching document-records-service
          pattern).
        """
        h: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if auth_token:
            h["Authorization"] = f"Bearer {auth_token}"
        elif self.service_token:
            h["X-Service-Token"] = self.service_token
        return h

    def _plans_url(self) -> str:
        return f"{self.base_url}/api/v1/workflow/plans/"

    def _templates_url(self) -> str:
        return f"{self.base_url}/api/v1/workflow/templates/"

    def _get_template_id_by_code(
        self,
        template_code: str,
        auth_token: Optional[str] = None,
    ) -> Optional[str]:
        """
        Look up WO template UUID by GRC template_code (guide §4.3 pattern).

        Maps template_code to WO workflow_type, queries WO's template list API,
        and returns the matching template UUID. Results are cached for the
        process lifetime so repeated start_workflow calls have no overhead.

        Returns None if WO is unreachable or the template has not been seeded.
        """
        if template_code in self._template_id_cache:
            return self._template_id_cache[template_code]

        wo_type = self.TEMPLATE_CODE_TO_WO_TYPE.get(template_code)
        if not wo_type:
            logger.debug("No WO workflow_type mapping for template_code=%s", template_code)
            return None

        try:
            resp = requests.get(
                self._templates_url(),
                headers=self._headers(auth_token),
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                templates = data.get("data", data) if isinstance(data, dict) else data
                for tpl in templates:
                    if tpl.get("workflow_type") == wo_type and tpl.get("is_active", True):
                        uid = tpl.get("id")
                        if uid:
                            self._template_id_cache[template_code] = uid
                            logger.info(
                                "Resolved template_id for %s (workflow_type=%s): %s",
                                template_code, wo_type, uid,
                            )
                            return uid
                logger.debug(
                    "WO template workflow_type=%s not found — run: "
                    "python manage.py seed_workflow_templates (in WO container)",
                    wo_type,
                )
            else:
                logger.warning("WO template list returned HTTP %s", resp.status_code)
        except Exception as exc:
            logger.debug(
                "_get_template_id_by_code lookup failed for %s: %s", template_code, exc
            )

        return None

    def start_workflow(
        self,
        template_code: str,
        context: Dict[str, Any],
        initiator_id: str,
        subject_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        # Override parameters: pass stages for inline mode (no seeded WO template)
        # or template_id when a UUID is known.
        stages: Optional[List[Dict[str, Any]]] = None,
        template_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sla: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None,
    ) -> Optional[WorkflowPlanResult]:
        """
        Create a workflow plan in Work Orchestration Service.

        Guide-aligned public signature (§4.3):
            template_code  – e.g. 'grc.working_paper_approval'
            context        – variables for assignee resolution (embedded in metadata)
            initiator_id   – UUID of user starting the workflow
            subject_ref    – entity UUID stored with the plan for traceability
            metadata       – additional display data (context + subject_ref embedded here)
            stages         – inline stage definitions; used only when WO template not found

        Resolution order for template_id (guide §4.3 pattern):
          1. Caller-supplied template_id (explicit override)
          2. _get_template_id_by_code() — queries WO's template list API at runtime
          3. Inline stages fallback — used only when WO templates have not been seeded

        WO receives:
            workflow_type  – derived from template_code prefix (e.g. "grc")
            created_by     – initiator_id
            metadata       – combined dict (entity metadata + context + subject_ref + template_code)
            template_id    – if resolved; mutually exclusive with stages in the payload
            stages         – inline stage defs; sent only when template_id is absent
        """
        # Guide §4.3: resolve template_id from WO at runtime.
        # Falls back to inline stages if WO templates have not been seeded yet.
        if not template_id:
            template_id = self._get_template_id_by_code(template_code, auth_token)

        if not template_id and not stages:
            logger.warning(
                "start_workflow: no template_id resolved and no inline stages provided "
                "for template_code=%s — workflow will not start.",
                template_code,
            )
            return None

        # Guide §4.3: embed context + subject_ref inside the metadata dict
        combined_metadata: Dict[str, Any] = {
            **(metadata or {}),
            "context": context,
            "subject_ref": subject_ref,
            "template_code": template_code,
        }

        # workflow_type is derived from the template code prefix (e.g. "grc")
        workflow_type = template_code.split(".")[0] if "." in template_code else template_code

        payload: Dict[str, Any] = {
            "workflow_type": workflow_type,
            "created_by": initiator_id,
            "metadata": combined_metadata,
            "tags": tags or [],
            "sla": sla or {},
        }
        if template_id:
            payload["template_id"] = template_id
        elif stages:
            # Only send inline stages when no template_id was resolved (fallback mode)
            payload["stages"] = stages

        url = self._plans_url()
        try:
            resp = requests.post(url, json=payload, headers=self._headers(auth_token), timeout=15)
        except requests.RequestException as exc:
            logger.error("OrchestrationClient.start_workflow request failed: %s", exc)
            return None

        if resp.status_code == 201:
            data = resp.json().get("data", {})
            # WO response has a "stages" list; "current_stage_id/name" do NOT exist
            # as top-level fields (verified from WorkflowPlanResponseSerializer).
            # Find the first in_progress stage, falling back to the first stage.
            stages = data.get("stages", [])
            current_stage = next(
                (s for s in stages if s.get("status") == "in_progress"),
                stages[0] if stages else None,
            )
            return WorkflowPlanResult(
                plan_id=data.get("id"),          # response field is "id" (source="plan_id")
                status=data.get("status"),
                current_stage_id=current_stage.get("id") if current_stage else None,
                current_stage_name=current_stage.get("name") if current_stage else None,
                stages=stages,
                metadata=data.get("metadata", {}),
                # created_at: WorkflowPlanResponseSerializer does not include this field;
                # always None — kept in dataclass for future compatibility.
            )

        logger.error(
            "OrchestrationClient.start_workflow failed: status=%s body=%s",
            resp.status_code,
            resp.text[:300],
        )
        return None

    def get_plan_status(
        self,
        plan_id: str,
        auth_token: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the current state of a workflow plan.
        GET /api/v1/workflow/plans/{plan_id}/
        """
        url = f"{self._plans_url()}{plan_id}/"
        try:
            resp = requests.get(url, headers=self._headers(auth_token), timeout=10)
        except requests.RequestException as exc:
            logger.error("OrchestrationClient.get_plan_status request failed: %s", exc)
            return None

        if resp.status_code == 200:
            return resp.json().get("data", resp.json())

        logger.warning(
            "OrchestrationClient.get_plan_status: status=%s plan_id=%s",
            resp.status_code, plan_id,
        )
        return None

    def get_plan_activity(
        self,
        plan_id: str,
        auth_token: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch activity/history log for a workflow plan.
        GET /api/v1/workflow/plans/{plan_id}/activity/

        Verified from WorkflowPlanActivityView in work-orchestration-service.
        """
        url = f"{self._plans_url()}{plan_id}/activity/"
        try:
            resp = requests.get(url, headers=self._headers(auth_token), timeout=10)
        except requests.RequestException as exc:
            logger.error("OrchestrationClient.get_plan_activity request failed: %s", exc)
            return []

        if resp.status_code == 200:
            body = resp.json()
            return body.get("data", body) if isinstance(body, dict) else body

        logger.warning(
            "OrchestrationClient.get_plan_activity: status=%s plan_id=%s",
            resp.status_code, plan_id,
        )
        return []
