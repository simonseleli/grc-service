"""
Service for Quarterly Audit Report workflow integration (FIMS pattern).

Follows audit_universe_service.py pattern:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata, stages=...)  → guide §4.3 signature

Template: grc.quarterly_report_approval
  4-stage: CIA review → Management review → Audit Committee review → Commission noting
SRS: Quarterly reporting obligation (SRS 1.8.3).
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.core.models import QuarterlyAuditReport
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class QuarterlyReportService:

    # Guide §4.2: WORKFLOW_TEMPLATE_CODE identifies the process
    WORKFLOW_TEMPLATE_CODE = "grc.quarterly_report_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(
        self,
        report_id: str,
        submitter_id: str,
        auth_token: str | None = None,
    ):
        """
        Submit a quarterly audit report to the Work Orchestration Service for the
        4-stage approval chain: CIA → Management → Committee → Commission.

        Follows guide §4.2 exactly:
          1. Build workflow context  (get_workflow_context → assignee resolution)
          2. Build metadata          (get_workflow_metadata → UI display)
          3. Start workflow          (guide §4.3 signature — context embedded in metadata)
          4. Save all 5 WorkflowMixin fields on the model
        """
        report = QuarterlyAuditReport.objects.select_for_update().get(id=report_id)

        if report.workflow_plan_id:
            logger.info(
                "QuarterlyAuditReport %s already has workflow plan %s — skipping",
                report.id,
                report.workflow_plan_id,
            )
            return report

        # Step 1 – context: variables used by WO to resolve stage assignees
        context = report.get_workflow_context()

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = report.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            self.WORKFLOW_TEMPLATE_CODE,
            context,
            submitter_id,
            subject_ref=str(report.id),
            metadata=metadata,
            stages=report.get_workflow_stages(),
            auth_token=auth_token,
        )

        if result and result.plan_id:
            report.workflow_plan_id = result.plan_id
            report.workflow_stage = result.current_stage_name or ""
            report.workflow_stage_id = result.current_stage_id or None
            report.workflow_started_at = timezone.now()
            report.status = "cia_review"
            report.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for QuarterlyAuditReport %s (stage: %s)",
                result.plan_id,
                report.id,
                result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for QuarterlyAuditReport %s", report.id)

        return report
