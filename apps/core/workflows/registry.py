"""
Workflow Template Registry for GRC Service.

Loads the canonical workflow definitions from workflows.yaml so that other
GRC code (WorkingPaperService, management commands) has a single source of
truth for stage/action definitions.

NOTE — template registration via Kafka does NOT work:
Work Orchestration Service has no consumer for the "workflow-templates" topic.
Templates must be seeded directly into the WO database using WO's own
management command:

    docker exec <wo-container> python manage.py seed_workflow_templates

Once seeded, retrieve the UUID with:

    python manage.py register_workflow_templates --fetch

…and store it as GRC_WORKFLOW_TEMPLATE_ID in GRC's environment so
WorkingPaperService can pass template_id instead of inline stages.
"""
import os
import yaml
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

WORKFLOWS_YAML_PATH = os.path.join(os.path.dirname(__file__), "workflows.yaml")


class WorkflowTemplateRegistry:
    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        with open(WORKFLOWS_YAML_PATH, "r") as f:
            data = yaml.safe_load(f)
        templates = data.get("templates", [])
        return {tpl["code"]: tpl for tpl in templates}

    def get_template(self, code: str) -> Optional[Dict[str, Any]]:
        return self.templates.get(code)

    def list_templates(self) -> List[Dict[str, Any]]:
        return list(self.templates.values())
