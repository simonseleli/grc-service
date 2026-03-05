"""
Management command: register_workflow_templates

Usage:
    # List GRC templates defined in workflows.yaml and their WO workflow_type keys
    python manage.py register_workflow_templates

    # Verify templates are seeded in WO and show what OrchestrationClient will resolve
    python manage.py register_workflow_templates --fetch

Template registration flow
──────────────────────────
Templates CANNOT be registered from GRC via Kafka or API — WO has no inbound
template-registration endpoint. GRC templates are owned by WO and seeded using
WO's own management command (guide §2 — template ownership pattern).

  Step 1 — Seed GRC templates into WO (done once by WO team or ops):
      docker exec <wo-container> python manage.py seed_workflow_templates

      The GRC templates are defined in:
          work-orchestration-service/apps/core/management/commands/seed_workflow_templates.py
      under workflow_type values:
          grc_working_paper_approval
          grc_audit_universe_approval
          grc_rbiap_approval
          grc_engagement_lifecycle

  Step 2 — Verify templates are visible from GRC:
      docker exec <grc-container> python manage.py register_workflow_templates --fetch

      OrchestrationClient._get_template_id_by_code() will automatically resolve
      these UUIDs at runtime — no env vars or manual configuration needed.
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.core.workflows.registry import WorkflowTemplateRegistry
from apps.infrastructure.external.orchestration_client import OrchestrationClient


class Command(BaseCommand):
    help = (
        "List GRC workflow templates and verify they are seeded "
        "in Work Orchestration Service."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fetch",
            action="store_true",
            default=False,
            help=(
                "Query Work Orchestration Service to verify GRC templates are seeded "
                "and show the UUIDs that OrchestrationClient will resolve at runtime."
            ),
        )

    def handle(self, *args, **options):
        # ── Local YAML definitions ────────────────────────────────────
        registry = WorkflowTemplateRegistry()
        local_templates = registry.list_templates()

        self.stdout.write(self.style.MIGRATE_HEADING("\nGRC Workflow Templates (local YAML — used as inline fallback):"))
        for tpl in local_templates:
            self.stdout.write(f"  code  : {tpl['code']}")
            self.stdout.write(f"  name  : {tpl.get('name', '')}")
            self.stdout.write("")

        self.stdout.write(self.style.MIGRATE_HEADING("template_code → WO workflow_type mapping (OrchestrationClient):"))
        for code, wo_type in OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE.items():
            self.stdout.write(f"  {code:<36}  →  {wo_type}")
        self.stdout.write("")

        if not options["fetch"]:
            self.stdout.write(
                self.style.WARNING(
                    "Run with --fetch to verify templates are seeded in WO.\n"
                    "Ensure WORK_ORCHESTRATION_SERVICE_URL is set and WO is reachable."
                )
            )
            return

        # ── --fetch: query WO and verify seeded templates ─────────────
        wo_url = getattr(settings, "WORK_ORCHESTRATION_SERVICE_URL", "").rstrip("/")
        if not wo_url:
            self.stderr.write(
                self.style.ERROR(
                    "WORK_ORCHESTRATION_SERVICE_URL is not configured. Cannot reach WO."
                )
            )
            return

        endpoint = f"{wo_url}/api/v1/workflow/templates/"
        self.stdout.write(f"Fetching from {endpoint} …\n")

        try:
            resp = requests.get(endpoint, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            wo_templates = data.get("data", data) if isinstance(data, dict) else data
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Request failed: {exc}"))
            return

        wo_by_type = {t.get("workflow_type", ""): t for t in wo_templates}

        missing = []
        self.stdout.write(self.style.MIGRATE_HEADING("GRC Template Resolution (what _get_template_id_by_code() will return):"))
        for code, wo_type in OrchestrationClient.TEMPLATE_CODE_TO_WO_TYPE.items():
            wo_tpl = wo_by_type.get(wo_type)
            if wo_tpl:
                uid = wo_tpl.get("id", "—")
                active = wo_tpl.get("is_active", True)
                flag = "✓" if active else "⚠ inactive"
                self.stdout.write(
                    self.style.SUCCESS(f"  {flag}  {code}")
                )
                self.stdout.write(f"       workflow_type={wo_type}")
                self.stdout.write(f"       uuid={uid}")
            else:
                self.stdout.write(
                    self.style.WARNING(f"  ✗  {code}")
                )
                self.stdout.write(f"       workflow_type={wo_type} — NOT SEEDED (inline stages will be used)")
                missing.append(wo_type)
            self.stdout.write("")

        if missing:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(missing)} template(s) not found in WO.\n"
                    "Run inside the WO container:\n"
                    "  python manage.py seed_workflow_templates\n"
                    "Missing workflow_type(s): " + ", ".join(missing)
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "All GRC templates are seeded in WO. "
                    "OrchestrationClient will use template_id (no inline stages)."
                )
            )

