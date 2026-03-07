"""
Audit Dashboard Statistics View for GRC Service.

Aggregates counts from all audit models to provide real-time
dashboard stats. Follows pattern from iam-service/apps/core/dashboard.py.
"""

import logging

from django.db.models import Count, Q, Avg
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import (
    AuditUniverse,
    AuditableEntity,
    RiskAssessment,
    AuditPlan,
    AuditEngagement,
    AuditFinding,
    AuditRecommendation,
    ImplementationMonitoring,
    WorkingPaper,
    AuditReport,
)
from apps.api.permissions_jwt import CanViewAuditDashboard
from apps.api.utils.response_helpers import (
    success_response,
    server_error_response,
)

logger = logging.getLogger(__name__)


class AuditDashboardStatsView(APIView):
    """
    GET /api/v1/grc/audit/dashboard/stats/

    Returns aggregated counts for all audit models, broken down by status.
    Used by the GRC Dashboard to display real-time summary statistics.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if not CanViewAuditDashboard().has_permission(request, self):
            self.permission_denied(
                request, message="grc:audit_dashboard:view required."
            )

    def get(self, request):
        try:
            # ── Audit Universe ────────────────────────────────────────
            universe_total = AuditUniverse.objects.count()
            universe_by_status = dict(
                AuditUniverse.objects.values_list("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            )

            # ── Auditable Entities ────────────────────────────────────
            entity_total = AuditableEntity.objects.count()
            entity_by_type = dict(
                AuditableEntity.objects.values_list("entity_type")
                .annotate(c=Count("id"))
                .values_list("entity_type", "c")
            )

            # ── Risk Assessments ──────────────────────────────────────
            risk_total = RiskAssessment.objects.count()
            risk_by_status = dict(
                RiskAssessment.objects.values_list("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            )

            # ── Audit Plans ───────────────────────────────────────────
            plan_total = AuditPlan.objects.count()
            plan_by_status = dict(
                AuditPlan.objects.values_list("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            )
            plan_approved = plan_by_status.get("approved", 0) + plan_by_status.get(
                "implementation", 0
            )

            # ── Audit Engagements ─────────────────────────────────────
            engagement_total = AuditEngagement.objects.count()
            engagement_by_status = dict(
                AuditEngagement.objects.values_list("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            )
            engagement_active = (
                engagement_by_status.get("planning", 0)
                + engagement_by_status.get("fieldwork", 0)
                + engagement_by_status.get("reporting", 0)
            )
            engagement_completed = engagement_by_status.get("completed", 0)

            # ── Audit Findings ────────────────────────────────────────
            finding_total = AuditFinding.objects.count()
            finding_by_status = dict(
                AuditFinding.objects.values_list("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            )

            # ── Audit Recommendations ─────────────────────────────────
            recommendation_total = AuditRecommendation.objects.count()
            recommendation_by_status = dict(
                AuditRecommendation.objects.values_list("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            )
            recommendation_open = (
                recommendation_by_status.get("open", 0)
                + recommendation_by_status.get("in_progress", 0)
            )

            # ── Implementation Monitoring ─────────────────────────────
            monitoring_total = ImplementationMonitoring.objects.count()
            monitoring_avg_progress = (
                ImplementationMonitoring.objects.aggregate(
                    avg=Avg("latest_progress")
                )["avg"]
                or 0
            )
            monitoring_complete = ImplementationMonitoring.objects.filter(
                latest_progress__gte=100
            ).count()

            # ── Working Papers ────────────────────────────────────────
            working_paper_total = WorkingPaper.objects.count()
            working_paper_by_status = dict(
                WorkingPaper.objects.values_list("review_status")
                .annotate(c=Count("id"))
                .values_list("review_status", "c")
            )

            # ── Audit Reports ─────────────────────────────────────────
            report_total = AuditReport.objects.count()
            report_by_status = dict(
                AuditReport.objects.values_list("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            )

            # ── Build response ────────────────────────────────────────
            stats = {
                # Summary cards (top-level KPIs)
                "summary": {
                    "total_risks": risk_total,
                    "active_actions": recommendation_open,
                    "completed_audits": engagement_completed,
                    "audit_engagements": engagement_total,
                    "total_findings": finding_total,
                },
                # Per-module card stats for Internal Audit tab
                "audit_universe": {
                    "total": universe_total,
                    "approved": universe_by_status.get("approved", 0),
                    "draft": universe_by_status.get("draft", 0),
                    "under_review": universe_by_status.get("under_review", 0),
                    "archived": universe_by_status.get("archived", 0),
                },
                "auditable_entities": {
                    "total": entity_total,
                    "by_type": entity_by_type,
                },
                "risk_assessments": {
                    "total": risk_total,
                    "draft": risk_by_status.get("draft", 0),
                    "submitted": risk_by_status.get("submitted", 0),
                    "reviewed": risk_by_status.get("reviewed", 0),
                    "approved": risk_by_status.get("approved", 0),
                },
                "audit_plans": {
                    "total": plan_total,
                    "approved": plan_approved,
                    "draft": plan_by_status.get("draft", 0),
                    "by_status": plan_by_status,
                },
                "audit_engagements": {
                    "total": engagement_total,
                    "active": engagement_active,
                    "completed": engagement_completed,
                    "planning": engagement_by_status.get("planning", 0),
                    "fieldwork": engagement_by_status.get("fieldwork", 0),
                    "reporting": engagement_by_status.get("reporting", 0),
                },
                "audit_findings": {
                    "total": finding_total,
                    "draft": finding_by_status.get("draft", 0),
                    "discussed": finding_by_status.get("discussed", 0),
                    "final": finding_by_status.get("final", 0),
                },
                "audit_recommendations": {
                    "total": recommendation_total,
                    "open": recommendation_by_status.get("open", 0),
                    "in_progress": recommendation_by_status.get("in_progress", 0),
                    "implemented": recommendation_by_status.get("implemented", 0),
                    "verified": recommendation_by_status.get("verified", 0),
                    "closed": recommendation_by_status.get("closed", 0),
                },
                "implementation_monitoring": {
                    "total": monitoring_total,
                    "completed": monitoring_complete,
                    "avg_progress": round(float(monitoring_avg_progress), 1),
                },
                "working_papers": {
                    "total": working_paper_total,
                    "draft": working_paper_by_status.get("draft", 0),
                    "pending": working_paper_by_status.get("pending", 0),
                    "reviewed": working_paper_by_status.get("reviewed", 0),
                    "approved": working_paper_by_status.get("approved", 0),
                },
                "audit_reports": {
                    "total": report_total,
                    "draft": report_by_status.get("draft", 0),
                    "under_review": report_by_status.get("under_review", 0),
                    "approved": report_by_status.get("approved", 0),
                    "distributed": report_by_status.get("distributed", 0),
                },
            }

            return success_response(data=stats, message="Dashboard stats retrieved successfully")

        except Exception as exc:
            logger.exception("Error fetching audit dashboard stats")
            return server_error_response(str(exc))
