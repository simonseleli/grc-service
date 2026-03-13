"""
Work Orchestration Service client.

Provides integration with the Work Orchestration Service for:
- Creating workflow plans from templates
- Advancing workflow stages (approve/reject/etc.)
- Fetching workflow plan status and activity

All methods handle service unavailability gracefully by returning None/empty list
and logging errors, allowing the calling service to continue operating.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


@dataclass
class WorkflowPlanResult:
    """Result from creating or fetching a workflow plan."""
    plan_id: str
    status: str
    current_stage_id: Optional[str] = None
    current_stage_name: Optional[str] = None
    stages: List[Dict] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.stages is None:
            self.stages = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StageActionResult:
    """Result from executing a stage action."""
    plan_id: str
    stage_id: str
    action: str
    new_status: str
    plan_status: str
    next_stage_id: Optional[str] = None
    next_stage_name: Optional[str] = None


@dataclass
class PendingTask:
    """A pending task/stage action for a user."""
    plan_id: str
    stage_id: str
    stage_name: str
    entity_type: str
    entity_id: str
    actions: List[Dict]
    due_at: Optional[str] = None
    metadata: Dict[str, Any] = None


class OrchestrationClientError(Exception):
    """Exception raised when Work Orchestration Service returns an error."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class OrchestrationClient:
    """
    Client for Work Orchestration Service.

    FIMS pattern — identical to corporate-service OrchestrationClient:
      - ALL HTTP calls go through _make_request()
      - _get_headers() ALWAYS uses X-Service-Token — never the user's JWT
      - Actor identity is passed as X-Actor-ID (for audit trail only)
      - applicant_id is set by the service layer in context before calling start_workflow

    All methods are designed to be resilient - they log errors and return None/empty
    results rather than raising exceptions, allowing the calling service to handle
    workflow service unavailability gracefully.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        from django.conf import settings
        self._settings = settings
        self.base_url = (
            base_url or
            getattr(settings, 'WORK_ORCHESTRATION_SERVICE_URL', None) or
            'http://work-orchestration-service:8004'
        )
        self.api_base = f"{self.base_url.rstrip('/')}/api/v1/workflow"
        self.timeout = timeout
        self._service_token = getattr(settings, 'SERVICE_TO_SERVICE_TOKEN', 'fims-service-secret-token')

    def _get_headers(self, actor_id: Optional[str] = None) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        # Add service-to-service authentication token
        # Work Orchestration Service expects X-Service-Token header
        headers['X-Service-Token'] = self._service_token

        # Add actor context if provided
        if actor_id:
            headers['X-Actor-ID'] = actor_id
        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        actor_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Make HTTP request to Work Orchestration Service."""
        url = f"{self.api_base}{endpoint}"
        headers = self._get_headers(actor_id)

        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code >= 400:
                logger.error(
                    "Work Orchestration API error: %s %s - Status %d: %s",
                    method, url, response.status_code, response.text[:500]
                )
                return None

            return response.json()

        except RequestException as e:
            logger.error(
                "Work Orchestration API request failed: %s %s - %s",
                method, url, str(e)
            )
            return None
        except ValueError as e:
            logger.error(
                "Work Orchestration API invalid JSON response: %s %s - %s",
                method, url, str(e)
            )
            return None

    def start_workflow(
        self,
        template_code: str,
        context: Dict[str, Any],
        initiator_id: str,
        subject_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkflowPlanResult]:
        """
        Start a workflow instance from a registered template.

        Args:
            template_code: The workflow template code (e.g., 'grc.engagement_lifecycle')
            context: Context variables for stage assignee resolution.
                     Must include 'applicant_id' — set by the service layer.
            initiator_id: User ID of the workflow initiator
            subject_ref: Optional reference to the subject entity
            metadata: Optional additional metadata to store with the plan

        Returns:
            WorkflowPlanResult with plan details, or None if failed
        """
        # Look up template by code first
        template_id = self._get_template_id_by_code(template_code)
        if not template_id:
            logger.error("Workflow template not found: %s", template_code)
            return None

        payload = {
            'template_id': template_id,
            'workflow_type': template_code.split('.')[0],  # e.g., 'grc' from 'grc.engagement_lifecycle'
            'created_by': initiator_id,
            'metadata': {
                **(metadata or {}),
                'context': context,
                'subject_ref': subject_ref,
                'template_code': template_code,
            },
        }

        response = self._make_request('POST', '/plans/', data=payload, actor_id=initiator_id)

        if not response:
            return None

        # Handle both formats: direct object {...} or wrapped {"data": {...}}
        if isinstance(response, dict) and 'data' in response:
            plan_data = response['data']
        elif isinstance(response, dict) and 'id' in response:
            plan_data = response  # Direct plan object
        else:
            return None

        # Find current active stage
        current_stage = None
        for stage in plan_data.get('stages', []):
            if stage.get('status') == 'in_progress':
                current_stage = stage
                break

        return WorkflowPlanResult(
            plan_id=plan_data['id'],
            status=plan_data.get('status', 'active'),
            current_stage_id=current_stage['id'] if current_stage else None,
            current_stage_name=current_stage['name'] if current_stage else None,
            stages=plan_data.get('stages', []),
            metadata=plan_data.get('metadata', {}),
            created_at=plan_data.get('created_at'),
        )

    def _get_template_id_by_code(self, template_code: str) -> Optional[str]:
        """Look up template ID by template code."""
        response = self._make_request(
            'GET', '/templates/',
            params={'code': template_code, 'is_active': 'true'}
        )

        if not response:
            return None

        # Handle both formats: direct array [...] or wrapped {"data": [...]}
        if isinstance(response, list):
            templates = response
        elif isinstance(response, dict) and 'data' in response:
            templates = response['data']
        else:
            return None

        # Find template matching the code (API returns all templates, we must filter)
        if isinstance(templates, list):
            for template in templates:
                if template.get('code') == template_code:
                    logger.info(f"Found template for code '{template_code}': id={template.get('id')}")
                    return template.get('id')
            # No matching template found - do NOT fallback to first template
            logger.warning(f"No template found matching code '{template_code}' in {len(templates)} templates")

        return None

    def advance_stage(
        self,
        plan_id: str,
        stage_id: str,
        action: str,
        actor_id: str,
        comment: Optional[str] = None,
        form_data: Optional[Dict] = None,
        metadata_patch: Optional[Dict] = None,
    ) -> Optional[StageActionResult]:
        """
        Advance a workflow to the next stage by executing an action.

        Args:
            plan_id: The workflow plan ID
            stage_id: The current stage ID to act on
            action: The action to execute (e.g., 'approve', 'reject', 'return')
            actor_id: User ID of the actor
            comment: Optional comment/reason for the action
            form_data: Optional form data submitted with the action
            metadata_patch: Optional metadata to merge into the plan

        Returns:
            StageActionResult with the result, or None if failed
        """
        payload = {
            'action_name': action,
            'actor_id': actor_id,
        }

        if comment:
            payload['comment'] = comment
        if form_data:
            payload['form_data'] = form_data
        if metadata_patch:
            payload['metadata_patch'] = metadata_patch

        response = self._make_request(
            'POST',
            f'/plans/{plan_id}/stages/{stage_id}/actions/',
            data=payload,
            actor_id=actor_id,
        )

        if not response or 'data' not in response:
            return None

        data = response['data']
        plan = data.get('plan', {})
        stage = data.get('stage', {})

        # Find next active stage
        next_stage = None
        for s in plan.get('stages', []):
            if s.get('status') == 'in_progress':
                next_stage = s
                break

        return StageActionResult(
            plan_id=plan_id,
            stage_id=stage_id,
            action=action,
            new_status=stage.get('status', 'completed'),
            plan_status=plan.get('status', 'active'),
            next_stage_id=next_stage['id'] if next_stage else None,
            next_stage_name=next_stage['name'] if next_stage else None,
        )

    def activate_stage(self, plan_id: str, stage_id: str, increment_revision: bool = True) -> bool:
        """
        Activate a workflow stage by setting its status to 'in_progress'.

        Uses the activate endpoint which supports revision tracking.
        When increment_revision is True, the stage's revision number is incremented,
        allowing users to re-act on the stage while preserving all previous activities.

        Args:
            plan_id: The workflow plan ID
            stage_id: The stage ID to activate
            increment_revision: If True, increment the stage revision to allow re-action
                              while preserving activity history (default: True)

        Returns:
            True if successful, False otherwise
        """
        response = self._make_request(
            'POST',
            f'/plans/{plan_id}/stages/{stage_id}/activate/',
            data={'increment_revision': increment_revision},
        )

        if response and isinstance(response, dict):
            revision = response.get('data', {}).get('revision', 'unknown')
            logger.info(f"Activated stage {stage_id} for plan {plan_id} (revision={revision})")
            return True

        logger.warning(f"Failed to activate stage {stage_id} for plan {plan_id}")
        return False

    def get_plan(self, plan_id: str) -> Optional[WorkflowPlanResult]:
        """
        Get workflow plan details.

        Args:
            plan_id: The workflow plan ID

        Returns:
            WorkflowPlanResult with plan details, or None if not found
        """
        response = self._make_request('GET', f'/plans/{plan_id}/')

        if not response or 'data' not in response:
            return None

        plan_data = response['data']

        # Find current active stage
        current_stage = None
        for stage in plan_data.get('stages', []):
            if stage.get('status') == 'in_progress':
                current_stage = stage
                break

        return WorkflowPlanResult(
            plan_id=plan_data['id'],
            status=plan_data.get('status', 'active'),
            current_stage_id=current_stage['id'] if current_stage else None,
            current_stage_name=current_stage['name'] if current_stage else None,
            stages=plan_data.get('stages', []),
            metadata=plan_data.get('metadata', {}),
            created_at=plan_data.get('created_at'),
        )

    def get_plan_activity(
        self,
        plan_id: str,
        stage_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get activity/audit log for a workflow plan.

        Args:
            plan_id: The workflow plan ID
            stage_id: Optional stage ID to filter by
            limit: Maximum number of entries to return

        Returns:
            List of activity entries
        """
        params = {'limit': limit}
        if stage_id:
            params['stage_id'] = stage_id

        response = self._make_request('GET', f'/plans/{plan_id}/activity/', params=params)

        if not response or 'data' not in response:
            return []

        return response['data']

    def get_pending_tasks(
        self,
        user_id: str,
        service: str = 'grc',
        workflow_type: Optional[str] = None,
    ) -> List[PendingTask]:
        """
        Get pending workflow tasks for a user.

        Args:
            user_id: The user ID to find tasks for
            service: The service filter (default: 'grc')
            workflow_type: Optional workflow type filter

        Returns:
            List of pending tasks
        """
        params = {'status': 'active'}
        if workflow_type:
            params['workflow_type'] = workflow_type

        response = self._make_request('GET', '/plans/', params=params)

        if not response or 'data' not in response:
            return []

        pending_tasks = []

        for plan in response['data']:
            for stage in plan.get('stages', []):
                if stage.get('status') != 'in_progress':
                    continue

                assignees = stage.get('assignees', [])
                if user_id in assignees or f'role:{user_id}' in assignees:
                    metadata = plan.get('metadata', {})

                    pending_tasks.append(PendingTask(
                        plan_id=plan['id'],
                        stage_id=stage['id'],
                        stage_name=stage.get('name', ''),
                        entity_type=metadata.get('entity_type', ''),
                        entity_id=metadata.get('entity_id', ''),
                        actions=stage.get('actions', []),
                        due_at=stage.get('due_at'),
                        metadata=metadata,
                    ))

        return pending_tasks

    def update_plan_metadata(
        self,
        plan_id: str,
        metadata_patch: Dict[str, Any],
    ) -> Optional[WorkflowPlanResult]:
        """
        Update workflow plan metadata.

        Args:
            plan_id: The workflow plan ID
            metadata_patch: Metadata fields to update/merge

        Returns:
            Updated WorkflowPlanResult, or None if failed
        """
        response = self._make_request(
            'PATCH',
            f'/plans/{plan_id}/',
            data={'metadata': metadata_patch},
        )

        if not response or 'data' not in response:
            return None

        plan_data = response['data']

        current_stage = None
        for stage in plan_data.get('stages', []):
            if stage.get('status') == 'in_progress':
                current_stage = stage
                break

        return WorkflowPlanResult(
            plan_id=plan_data['id'],
            status=plan_data.get('status', 'active'),
            current_stage_id=current_stage['id'] if current_stage else None,
            current_stage_name=current_stage['name'] if current_stage else None,
            stages=plan_data.get('stages', []),
            metadata=plan_data.get('metadata', {}),
            created_at=plan_data.get('created_at'),
        )

    def cancel_plan(self, plan_id: str, actor_id: str, reason: str = '') -> bool:
        """
        Cancel a workflow plan.

        Args:
            plan_id: The workflow plan ID
            actor_id: User ID of the actor cancelling
            reason: Reason for cancellation

        Returns:
            True if successful, False otherwise
        """
        response = self._make_request(
            'PATCH',
            f'/plans/{plan_id}/',
            data={
                'status': 'cancelled',
                'metadata': {
                    'cancelled_by': actor_id,
                    'cancelled_at': datetime.utcnow().isoformat(),
                    'cancellation_reason': reason,
                }
            },
            actor_id=actor_id,
        )

        return response is not None and 'data' in response
