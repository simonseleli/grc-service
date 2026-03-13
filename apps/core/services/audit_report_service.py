"""
Service for Audit Report workflow integration (FIMS pattern).

Follows audit_universe_service.py pattern:
  - calls entity.get_workflow_context()  → assignee-resolution variables
  - calls entity.get_workflow_metadata() → display data stored in WO plan
  - calls OrchestrationClient.start_workflow(template_code, context, initiator_id,
      subject_ref, metadata)  → guide §4.3 signature

Template: grc.audit_report_approval (2-stage: IA report review → CIA report approval)
SRS Requirement: 36.
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.core.models import AuditReport
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class AuditReportService:

    # Guide §4.2: WORKFLOW_TEMPLATE_CODE identifies the process
    WORKFLOW_TEMPLATE_CODE = "grc.audit_report_approval"

    def __init__(self):
        self.workflow_client = OrchestrationClient()

    @transaction.atomic
    def submit_for_approval(
        self,
        report_id: str,
        submitter_id: str,
    ):
        """
        Submit an audit report to the Work Orchestration Service for IA/CIA approval.

        Follows guide §4.2 exactly:
          1. Build workflow context  (get_workflow_context → assignee resolution)
          2. Build metadata          (get_workflow_metadata → UI display)
          3. Start workflow          (guide §4.3 signature — context embedded in metadata)
          4. Save all 5 WorkflowMixin fields on the model
        """
        report = AuditReport.objects.select_for_update().get(id=report_id)

        if report.workflow_plan_id:
            logger.info(
                "AuditReport %s already has workflow plan %s — skipping",
                report.id,
                report.workflow_plan_id,
            )
            return report

        # Step 1 – context: variables used by WO to resolve stage assignees
        context = report.get_workflow_context()
        context['applicant_id'] = submitter_id  # FIMS pattern: set at service layer

        # Step 2 – metadata: display data stored with the plan in WO
        metadata = report.get_workflow_metadata()

        # Step 3 – start workflow: client auto-resolves template_id from WO (guide §4.3),
        # falling back to inline stages if WO templates have not been seeded yet.
        result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(report.id),
            metadata=metadata,
        )

        if result and result.plan_id:
            report.start_workflow(

                plan_id=result.plan_id,

                initial_stage=result.current_stage_name or '',

                stage_id=result.current_stage_id,

            )
            report.status = "under_review"
            report.save(update_fields=[
                "workflow_plan_id",
                "workflow_stage",
                "workflow_stage_id",
                "workflow_started_at",
                "status",
            ])
            logger.info(
                "Started workflow plan %s for AuditReport %s (stage: %s)",
                result.plan_id,
                report.id,
                result.current_stage_name,
            )
        else:
            logger.error("Failed to start workflow for AuditReport %s", report.id)

        return report

    def get_workflow_status(self, report_id: str):
        """Get current workflow status. Follows corporate FIMS pattern."""
        entity = AuditReport.objects.get(id=report_id)
        if not entity.workflow_plan_id:
            return None
        plan = self.workflow_client.get_plan(str(entity.workflow_plan_id))
        if not plan:
            return {
                'has_workflow': True,
                'workflow_plan_id': str(entity.workflow_plan_id),
                'status': 'unknown',
            }
        current_stage_data = next(
            (s for s in plan.stages if s.get('id') == plan.current_stage_id), None
        )
        return {
            'has_workflow': True,
            'plan_id': plan.plan_id,
            'workflow_plan_id': plan.plan_id,
            'status': plan.status,
            'current_stage': plan.current_stage_name,
            'current_stage_id': plan.current_stage_id,
            'current_stage_data': current_stage_data,
            'available_actions': current_stage_data.get('actions', []) if current_stage_data else [],
            'stages': plan.stages,
            'metadata': plan.metadata,
            'is_completed': plan.status in ('completed', 'cancelled'),
        }

    def get_workflow_history(self, report_id: str):
        """Get workflow activity history. Follows corporate FIMS pattern."""
        entity = AuditReport.objects.get(id=report_id)
        if not entity.workflow_plan_id:
            return []
        return self.workflow_client.get_plan_activity(str(entity.workflow_plan_id))

