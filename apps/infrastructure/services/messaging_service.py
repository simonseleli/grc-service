"""
Messaging service implementation for GRC service
Publishes domain events using FIMS-compliant structure
"""

import logging
from typing import Dict, Any, Optional
import uuid

from apps.infrastructure.messaging import publish_event
from apps.core.events.audit_events import (
    AuditEngagementCreatedEvent,
    AuditEngagementUpdatedEvent,
    WorkingPaperCreatedEvent,
    WorkingPaperSubmittedEvent,
    WorkingPaperApprovedEvent,
    WorkingPaperRejectedEvent,
    AuditFindingCreatedEvent,
    AuditFindingFinalizedEvent,
    AuditPlanCreatedEvent,
    AuditPlanApprovedEvent,
)
from apps.core.events.legal_events import (
    LegalCaseCreatedEvent,
    LegalCaseClosedEvent,
    LegalJudgmentRecordedEvent,
    LegalMeetingCompletedEvent,
    LegalMeetingInvitationsSentEvent,
    LegalMinutesApprovedEvent,
    LegalDirectiveOverdueEvent,
    LegalFilingApprovedEvent,
    LegalSettlementApprovedEvent,
    LegalNoticeIssuedEvent,
)
from apps.core.events.risk_events import (
    RiskChampionAppointedEvent,
    DeptRiskRegisterApprovedEvent,
    InstitutionalRiskRegisterSubmittedEvent,
    RTAPApprovedEvent,
    RTAPUpdatedEvent,
    QuarterlyRiskReportSubmittedEvent,
    QualityAuditorAppointedEvent,
    NonConformanceRaisedEvent,
    QMSAuditReportSignedEvent,
)
from shared.constants.event_types import (
    AUDIT_ENGAGEMENT_EVENTS,
    WORKING_PAPER_EVENTS,
    AUDIT_FINDING_EVENTS,
    AUDIT_PLAN_EVENTS,
    LEGAL_CASE_EVENTS,
    LEGAL_JUDGMENT_EVENTS,
    LEGAL_MEETING_EVENTS,
    LEGAL_MINUTES_EVENTS,
    LEGAL_DIRECTIVE_EVENTS,
    LEGAL_FILING_EVENTS,
    LEGAL_SETTLEMENT_EVENTS,
    LEGAL_NOTICE_EVENTS,
    RISK_CHAMPION_EVENTS,
    RISK_REGISTER_EVENTS,
    RTAP_EVENTS,
    QUARTERLY_RISK_REPORT_EVENTS,
    QA_EVENTS,
    QMS_AUDIT_EVENTS,
)

logger = logging.getLogger(__name__)


class MessagingServiceInterface:
    """Messaging service interface"""
    
    def publish_audit_event(self, event_type: str, audit_data: Dict[str, Any]) -> bool:
        """Publish audit-related event"""
        pass


class KafkaMessagingService(MessagingServiceInterface):
    """Kafka-based messaging service implementation for GRC"""
    
    def __init__(self):
        logger.info("GRC Kafka messaging service initialized")
    
    def publish_audit_engagement_event(
        self, 
        event_type: str, 
        engagement_id: uuid.UUID, 
        additional_data: Dict[str, Any] = None
    ) -> bool:
        """
        Publish audit engagement event to Kafka
        
        Args:
            event_type: Type of audit engagement event
            engagement_id: Engagement ID
            additional_data: Additional event data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate event type
            if event_type not in AUDIT_ENGAGEMENT_EVENTS.values():
                logger.warning(f"Unknown audit engagement event type: {event_type}")
                return False
            
            additional_data = additional_data or {}
            
            # Create appropriate event based on type
            if event_type == AUDIT_ENGAGEMENT_EVENTS.get('ENGAGEMENT_CREATED'):
                event = AuditEngagementCreatedEvent(
                    engagement_id=str(engagement_id),
                    engagement_title=additional_data.get('title', ''),
                    engagement_type=additional_data.get('engagement_type', ''),
                    fiscal_year=additional_data.get('fiscal_year', ''),
                    auditable_entity_id=additional_data.get('auditable_entity_id', ''),
                    created_by=additional_data.get('created_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('created_by', '')),
                )
            elif event_type == AUDIT_ENGAGEMENT_EVENTS.get('ENGAGEMENT_UPDATED'):
                event = AuditEngagementUpdatedEvent(
                    engagement_id=str(engagement_id),
                    engagement_title=additional_data.get('title', ''),
                    updated_by=additional_data.get('updated_by', ''),
                    changes=additional_data.get('changes', {}),
                    user_id=additional_data.get('user_id', additional_data.get('updated_by', '')),
                )
            else:
                logger.warning(f"No event class for type: {event_type}")
                return False
            
            # Publish event using FIMS-compliant publisher
            publish_event(event)
            
            logger.info(f"Published engagement event: {event_type} for {engagement_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing engagement event {event_type}: {str(e)}")
            return False
    
    def publish_working_paper_event(
        self,
        event_type: str,
        working_paper_id: uuid.UUID,
        engagement_id: uuid.UUID,
        additional_data: Dict[str, Any] = None
    ) -> bool:
        """
        Publish working paper event to Kafka
        
        Args:
            event_type: Type of working paper event
            working_paper_id: Working paper ID
            engagement_id: Associated engagement ID
            additional_data: Additional event data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate event type
            if event_type not in WORKING_PAPER_EVENTS.values():
                logger.warning(f"Unknown working paper event type: {event_type}")
                return False
            
            additional_data = additional_data or {}
            
            # Create appropriate event based on type
            if event_type == WORKING_PAPER_EVENTS.get('WORKING_PAPER_CREATED'):
                event = WorkingPaperCreatedEvent(
                    working_paper_id=str(working_paper_id),
                    engagement_id=str(engagement_id),
                    title=additional_data.get('title', ''),
                    paper_type=additional_data.get('paper_type', ''),
                    document_id=additional_data.get('document_id'),
                    created_by=additional_data.get('created_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('created_by', '')),
                )
            elif event_type == WORKING_PAPER_EVENTS.get('WORKING_PAPER_SUBMITTED'):
                event = WorkingPaperSubmittedEvent(
                    working_paper_id=str(working_paper_id),
                    engagement_id=str(engagement_id),
                    title=additional_data.get('title', ''),
                    submitted_by=additional_data.get('submitted_by', ''),
                    reviewer_id=additional_data.get('reviewer_id'),
                    user_id=additional_data.get('user_id', additional_data.get('submitted_by', '')),
                )
            elif event_type == WORKING_PAPER_EVENTS.get('WORKING_PAPER_APPROVED'):
                event = WorkingPaperApprovedEvent(
                    working_paper_id=str(working_paper_id),
                    engagement_id=str(engagement_id),
                    title=additional_data.get('title', ''),
                    approved_by=additional_data.get('approved_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('approved_by', '')),
                )
            elif event_type == WORKING_PAPER_EVENTS.get('WORKING_PAPER_REJECTED'):
                event = WorkingPaperRejectedEvent(
                    working_paper_id=str(working_paper_id),
                    engagement_id=str(engagement_id),
                    title=additional_data.get('title', ''),
                    rejected_by=additional_data.get('rejected_by', ''),
                    reason=additional_data.get('reason', ''),
                    user_id=additional_data.get('user_id', additional_data.get('rejected_by', '')),
                )
            else:
                logger.warning(f"No event class for type: {event_type}")
                return False
            
            # Publish event using FIMS-compliant publisher
            publish_event(event)
            
            logger.info(f"Published working paper event: {event_type} for {working_paper_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing working paper event {event_type}: {str(e)}")
            return False
    
    def publish_audit_finding_event(
        self,
        event_type: str,
        finding_id: uuid.UUID,
        engagement_id: uuid.UUID,
        additional_data: Dict[str, Any] = None
    ) -> bool:
        """
        Publish audit finding event to Kafka
        
        Args:
            event_type: Type of audit finding event
            finding_id: Finding ID
            engagement_id: Associated engagement ID
            additional_data: Additional event data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate event type
            if event_type not in AUDIT_FINDING_EVENTS.values():
                logger.warning(f"Unknown audit finding event type: {event_type}")
                return False
            
            additional_data = additional_data or {}
            
            # Create appropriate event based on type
            if event_type == AUDIT_FINDING_EVENTS.get('FINDING_CREATED'):
                event = AuditFindingCreatedEvent(
                    finding_id=str(finding_id),
                    engagement_id=str(engagement_id),
                    working_paper_id=additional_data.get('working_paper_id'),
                    title=additional_data.get('title', ''),
                    severity=additional_data.get('severity', ''),
                    finding_type=additional_data.get('finding_type', ''),
                    created_by=additional_data.get('created_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('created_by', '')),
                )
            else:
                logger.warning(f"No event class for type: {event_type}")
                return False
            
            # Publish event using FIMS-compliant publisher
            publish_event(event)
            
            logger.info(f"Published finding event: {event_type} for {finding_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing finding event {event_type}: {str(e)}")
            return False


    def publish_audit_plan_event(
        self,
        event_type: str,
        plan_id: uuid.UUID,
        additional_data: Dict[str, Any] = None
    ) -> bool:
        """
        Publish audit plan event to Kafka.
        Covers plan creation and final committee approval.
        """
        try:
            from shared.constants.event_types import AUDIT_PLAN_EVENTS
            if event_type not in AUDIT_PLAN_EVENTS.values():
                logger.warning(f"Unknown audit plan event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == AUDIT_PLAN_EVENTS.get('PLAN_CREATED'):
                event = AuditPlanCreatedEvent(
                    plan_id=str(plan_id),
                    fiscal_year=additional_data.get('fiscal_year', ''),
                    plan_type=additional_data.get('plan_type', ''),
                    created_by=additional_data.get('created_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('created_by', '')),
                )
            elif event_type == AUDIT_PLAN_EVENTS.get('PLAN_APPROVED'):
                event = AuditPlanApprovedEvent(
                    plan_id=str(plan_id),
                    fiscal_year=additional_data.get('fiscal_year', ''),
                    approved_by=additional_data.get('approved_by', ''),
                    approval_date=additional_data.get('approval_date', ''),
                    user_id=additional_data.get('user_id', additional_data.get('approved_by', '')),
                )
            else:
                logger.warning(f"No event class for plan event type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published plan event: {event_type} for {plan_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing plan event {event_type}: {str(e)}")
            return False


    def publish_finding_finalized_event(
        self,
        finding,
        approved_by: str,
    ) -> bool:
        """
        Publish a finding.finalized event for consumption by the Risk Management System.

        Called when an AuditReport is approved by CIA — all findings within the
        engagement are considered finalised simultaneously (SRS Req 41).

        The payload is self-contained so that a future Risk Management consumer
        can create an org-risk entry without calling back to GRC.

        Args:
            finding: AuditFinding model instance (must have related engagement,
                     engagement.audit_plan.fiscal_year, finding_type, severity,
                     risk_rating, and recommendations prefetched or accessible).
            approved_by: User ID (str) of the CIA who approved the report.

        Returns:
            True if the event was published, False on error (best-effort).
        """
        try:
            engagement = getattr(finding, 'engagement', None)
            entity = getattr(engagement, 'auditable_entity', None) if engagement else None
            plan = getattr(engagement, 'audit_plan', None) if engagement else None
            fy = getattr(plan, 'fiscal_year', None) if plan else None

            # Resolve lookup FK display names safely
            finding_type_str = ''
            if finding.finding_type:
                finding_type_str = getattr(finding.finding_type, 'name', str(finding.finding_type))

            severity_str = ''
            if finding.severity:
                severity_str = getattr(finding.severity, 'name', str(finding.severity))

            rr_id, rr_name = '', ''
            if finding.risk_rating:
                rr_id = str(finding.risk_rating.id)
                rr_name = getattr(finding.risk_rating, 'name', '')

            rec_count = 0
            try:
                rec_count = finding.recommendations.count()
            except Exception:
                pass

            event = AuditFindingFinalizedEvent(
                finding_id=str(finding.id),
                reference_number=finding.reference_number or '',
                title=finding.title or '',
                description=getattr(finding, 'condition', '') or '',
                finding_type=finding_type_str,
                severity=severity_str,
                risk_rating_id=rr_id,
                risk_rating_name=rr_name,
                engagement_id=str(engagement.id) if engagement else '',
                engagement_reference=getattr(engagement, 'reference_number', '') if engagement else '',
                auditable_entity_id=str(entity.id) if entity else '',
                auditable_entity_name=getattr(entity, 'name', '') if entity else '',
                fiscal_year_id=str(fy.id) if fy else '',
                fiscal_year_code=getattr(fy, 'year_code', '') if fy else '',
                recommendation_count=rec_count,
                finalized_by=approved_by,
                user_id=approved_by,
            )

            publish_event(event)
            logger.info(
                f"Published finding.finalized event for finding {finding.id} "
                f"(engagement {getattr(engagement, 'id', 'N/A')})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to publish finding.finalized event for finding "
                f"{getattr(finding, 'id', 'N/A')}: {e}"
            )
            return False


    # ------------------------------------------------------------------ #
    # Legal Module event publishers                                       #
    # ------------------------------------------------------------------ #

    def publish_legal_case_event(
        self,
        event_type: str,
        case_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish legal case event to Kafka"""
        try:
            if event_type not in LEGAL_CASE_EVENTS.values():
                logger.warning(f"Unknown legal case event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == LEGAL_CASE_EVENTS.get('CASE_CREATED'):
                event = LegalCaseCreatedEvent(
                    case_id=str(case_id),
                    case_type=additional_data.get('case_type', ''),
                    reference_number=additional_data.get('reference_number', ''),
                    case_title=additional_data.get('case_title', ''),
                    court_level=additional_data.get('court_level', ''),
                    created_by=additional_data.get('created_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('created_by', '')),
                )
            elif event_type == LEGAL_CASE_EVENTS.get('CASE_CLOSED'):
                event = LegalCaseClosedEvent(
                    case_id=str(case_id),
                    case_type=additional_data.get('case_type', ''),
                    reference_number=additional_data.get('reference_number', ''),
                    closed_by=additional_data.get('closed_by', ''),
                    closure_reason=additional_data.get('closure_reason', ''),
                    user_id=additional_data.get('user_id', additional_data.get('closed_by', '')),
                )
            else:
                logger.warning(f"No event class for legal case type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published legal case event: {event_type} for {case_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing legal case event {event_type}: {e}")
            return False

    def publish_legal_judgment_event(
        self,
        event_type: str,
        judgment_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish legal judgment event to Kafka"""
        try:
            if event_type not in LEGAL_JUDGMENT_EVENTS.values():
                logger.warning(f"Unknown legal judgment event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == LEGAL_JUDGMENT_EVENTS.get('JUDGMENT_RECORDED'):
                event = LegalJudgmentRecordedEvent(
                    judgment_id=str(judgment_id),
                    case_id=additional_data.get('case_id', ''),
                    case_type=additional_data.get('case_type', ''),
                    judgment_date=additional_data.get('judgment_date', ''),
                    outcome=additional_data.get('outcome', ''),
                    recorded_by=additional_data.get('recorded_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('recorded_by', '')),
                )
            else:
                logger.warning(f"No event class for legal judgment type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published legal judgment event: {event_type} for {judgment_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing legal judgment event {event_type}: {e}")
            return False

    def publish_legal_meeting_event(
        self,
        event_type: str,
        meeting_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish legal meeting event to Kafka"""
        try:
            if event_type not in LEGAL_MEETING_EVENTS.values():
                logger.warning(f"Unknown legal meeting event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == LEGAL_MEETING_EVENTS.get('MEETING_COMPLETED'):
                event = LegalMeetingCompletedEvent(
                    meeting_id=str(meeting_id),
                    meeting_type=additional_data.get('meeting_type', ''),
                    governing_body_id=additional_data.get('governing_body_id', ''),
                    reference_number=additional_data.get('reference_number', ''),
                    completed_by=additional_data.get('completed_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('completed_by', '')),
                )
            elif event_type == LEGAL_MEETING_EVENTS.get('INVITATIONS_SENT'):
                event = LegalMeetingInvitationsSentEvent(
                    meeting_id=str(meeting_id),
                    governing_body_id=additional_data.get('governing_body_id', ''),
                    reference_number=additional_data.get('reference_number', ''),
                    participant_count=additional_data.get('participant_count', 0),
                    sent_by=additional_data.get('sent_by', ''),
                    user_id=additional_data.get('sent_by', ''),
                )
            else:
                logger.warning(f"No event class for legal meeting type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published legal meeting event: {event_type} for {meeting_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing legal meeting event {event_type}: {e}")
            return False

    def publish_legal_minutes_event(
        self,
        event_type: str,
        minutes_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish legal minutes event to Kafka"""
        try:
            if event_type not in LEGAL_MINUTES_EVENTS.values():
                logger.warning(f"Unknown legal minutes event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == LEGAL_MINUTES_EVENTS.get('MINUTES_APPROVED'):
                event = LegalMinutesApprovedEvent(
                    minutes_id=str(minutes_id),
                    meeting_id=additional_data.get('meeting_id', ''),
                    reference_number=additional_data.get('reference_number', ''),
                    approved_by=additional_data.get('approved_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('approved_by', '')),
                )
            else:
                logger.warning(f"No event class for legal minutes type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published legal minutes event: {event_type} for {minutes_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing legal minutes event {event_type}: {e}")
            return False

    def publish_legal_directive_event(
        self,
        event_type: str,
        directive_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish legal directive event to Kafka"""
        try:
            if event_type not in LEGAL_DIRECTIVE_EVENTS.values():
                logger.warning(f"Unknown legal directive event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == LEGAL_DIRECTIVE_EVENTS.get('DIRECTIVE_OVERDUE'):
                event = LegalDirectiveOverdueEvent(
                    directive_id=str(directive_id),
                    minutes_id=additional_data.get('minutes_id', ''),
                    meeting_id=additional_data.get('meeting_id', ''),
                    due_date=additional_data.get('due_date', ''),
                    assigned_to=additional_data.get('assigned_to', ''),
                    user_id=additional_data.get('user_id', ''),
                )
            else:
                logger.warning(f"No event class for legal directive type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published legal directive event: {event_type} for {directive_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing legal directive event {event_type}: {e}")
            return False

    def publish_legal_filing_event(
        self,
        event_type: str,
        filing_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish legal filing event to Kafka"""
        try:
            if event_type not in LEGAL_FILING_EVENTS.values():
                logger.warning(f"Unknown legal filing event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == LEGAL_FILING_EVENTS.get('FILING_APPROVED'):
                event = LegalFilingApprovedEvent(
                    filing_id=str(filing_id),
                    case_id=additional_data.get('case_id', ''),
                    filing_type=additional_data.get('filing_type', ''),
                    reference_number=additional_data.get('reference_number', ''),
                    approved_by=additional_data.get('approved_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('approved_by', '')),
                )
            else:
                logger.warning(f"No event class for legal filing type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published legal filing event: {event_type} for {filing_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing legal filing event {event_type}: {e}")
            return False

    def publish_legal_settlement_event(
        self,
        event_type: str,
        settlement_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish legal settlement event to Kafka"""
        try:
            if event_type not in LEGAL_SETTLEMENT_EVENTS.values():
                logger.warning(f"Unknown legal settlement event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == LEGAL_SETTLEMENT_EVENTS.get('SETTLEMENT_APPROVED'):
                event = LegalSettlementApprovedEvent(
                    settlement_id=str(settlement_id),
                    case_id=additional_data.get('case_id', ''),
                    settlement_amount=additional_data.get('settlement_amount', ''),
                    approved_by=additional_data.get('approved_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('approved_by', '')),
                )
            else:
                logger.warning(f"No event class for legal settlement type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published legal settlement event: {event_type} for {settlement_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing legal settlement event {event_type}: {e}")
            return False

    def publish_legal_notice_event(
        self,
        event_type: str,
        notice_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish legal notice event to Kafka"""
        try:
            if event_type not in LEGAL_NOTICE_EVENTS.values():
                logger.warning(f"Unknown legal notice event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == LEGAL_NOTICE_EVENTS.get('NOTICE_ISSUED'):
                event = LegalNoticeIssuedEvent(
                    notice_id=str(notice_id),
                    notice_type=additional_data.get('notice_type', ''),
                    reference_number=additional_data.get('reference_number', ''),
                    issued_by=additional_data.get('issued_by', ''),
                    recipient=additional_data.get('recipient', ''),
                    user_id=additional_data.get('user_id', additional_data.get('issued_by', '')),
                )
            else:
                logger.warning(f"No event class for legal notice type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published legal notice event: {event_type} for {notice_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing legal notice event {event_type}: {e}")
            return False

    # ── Risk Management Events ─────────────────────────────────────────

    def publish_risk_champion_event(
        self,
        event_type: str,
        champion_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish risk champion event to Kafka"""
        try:
            if event_type not in RISK_CHAMPION_EVENTS.values():
                logger.warning(f"Unknown risk champion event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == RISK_CHAMPION_EVENTS.get('CHAMPION_APPOINTED'):
                event = RiskChampionAppointedEvent(
                    champion_id=str(champion_id),
                    appointment_id=additional_data.get('appointment_id', ''),
                    champion_user_id=additional_data.get('champion_user_id', ''),
                    org_unit_id=additional_data.get('org_unit_id', ''),
                    org_unit_type=additional_data.get('org_unit_type', ''),
                    appointed_by=additional_data.get('appointed_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('appointed_by', '')),
                )
            else:
                logger.warning(f"No event class for risk champion type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published risk champion event: {event_type} for {champion_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing risk champion event {event_type}: {e}")
            return False

    def publish_risk_register_event(
        self,
        event_type: str,
        register_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish risk register event to Kafka"""
        try:
            if event_type not in RISK_REGISTER_EVENTS.values():
                logger.warning(f"Unknown risk register event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == RISK_REGISTER_EVENTS.get('DEPARTMENTAL_APPROVED'):
                event = DeptRiskRegisterApprovedEvent(
                    register_id=str(register_id),
                    org_unit_id=additional_data.get('org_unit_id', ''),
                    fiscal_year_code=additional_data.get('fiscal_year_code', ''),
                    approved_by=additional_data.get('approved_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('approved_by', '')),
                )
            elif event_type == RISK_REGISTER_EVENTS.get('INSTITUTIONAL_SUBMITTED'):
                event = InstitutionalRiskRegisterSubmittedEvent(
                    register_id=str(register_id),
                    fiscal_year_code=additional_data.get('fiscal_year_code', ''),
                    submitted_by=additional_data.get('submitted_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('submitted_by', '')),
                )
            else:
                logger.warning(f"No event class for risk register type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published risk register event: {event_type} for {register_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing risk register event {event_type}: {e}")
            return False

    def publish_rtap_event(
        self,
        event_type: str,
        rtap_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish RTAP event to Kafka"""
        try:
            if event_type not in RTAP_EVENTS.values():
                logger.warning(f"Unknown RTAP event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == RTAP_EVENTS.get('RTAP_APPROVED'):
                event = RTAPApprovedEvent(
                    rtap_id=str(rtap_id),
                    fiscal_year_code=additional_data.get('fiscal_year_code', ''),
                    approved_by=additional_data.get('approved_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('approved_by', '')),
                )
            elif event_type == RTAP_EVENTS.get('RTAP_UPDATED'):
                event = RTAPUpdatedEvent(
                    rtap_id=str(rtap_id),
                    rtap_item_id=additional_data.get('rtap_item_id', ''),
                    quarter=additional_data.get('quarter', ''),
                    new_status=additional_data.get('new_status', ''),
                    updated_by=additional_data.get('updated_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('updated_by', '')),
                )
            else:
                logger.warning(f"No event class for RTAP type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published RTAP event: {event_type} for {rtap_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing RTAP event {event_type}: {e}")
            return False

    def publish_quarterly_report_event(
        self,
        event_type: str,
        report_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish quarterly risk report event to Kafka"""
        try:
            if event_type not in QUARTERLY_RISK_REPORT_EVENTS.values():
                logger.warning(f"Unknown quarterly report event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == QUARTERLY_RISK_REPORT_EVENTS.get('RISK_REPORT_SUBMITTED'):
                event = QuarterlyRiskReportSubmittedEvent(
                    report_id=str(report_id),
                    fiscal_year_code=additional_data.get('fiscal_year_code', ''),
                    quarter=additional_data.get('quarter', ''),
                    submitted_by=additional_data.get('submitted_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('submitted_by', '')),
                )
            else:
                logger.warning(f"No event class for quarterly report type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published quarterly report event: {event_type} for {report_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing quarterly report event {event_type}: {e}")
            return False

    def publish_qa_event(
        self,
        event_type: str,
        auditor_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish quality auditor event to Kafka"""
        try:
            if event_type not in QA_EVENTS.values():
                logger.warning(f"Unknown QA event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == QA_EVENTS.get('QA_APPOINTED'):
                event = QualityAuditorAppointedEvent(
                    auditor_id=str(auditor_id),
                    appointment_id=additional_data.get('appointment_id', ''),
                    auditor_user_id=additional_data.get('auditor_user_id', ''),
                    org_unit_id=additional_data.get('org_unit_id', ''),
                    appointed_by=additional_data.get('appointed_by', ''),
                    user_id=additional_data.get('user_id', additional_data.get('appointed_by', '')),
                )
            else:
                logger.warning(f"No event class for QA type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published QA event: {event_type} for {auditor_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing QA event {event_type}: {e}")
            return False

    def publish_qms_audit_event(
        self,
        event_type: str,
        entity_id: uuid.UUID,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Publish QMS audit event to Kafka"""
        try:
            if event_type not in QMS_AUDIT_EVENTS.values():
                logger.warning(f"Unknown QMS audit event type: {event_type}")
                return False

            additional_data = additional_data or {}

            if event_type == QMS_AUDIT_EVENTS.get('NC_RAISED'):
                event = NonConformanceRaisedEvent(
                    nc_id=str(entity_id),
                    audit_report_id=additional_data.get('audit_report_id', ''),
                    iso_clause=additional_data.get('iso_clause', ''),
                    nc_type=additional_data.get('nc_type', ''),
                    description=additional_data.get('description', ''),
                    raised_by=additional_data.get('raised_by', ''),
                    responsible_officer=additional_data.get('responsible_officer'),
                    user_id=additional_data.get('user_id', additional_data.get('raised_by', '')),
                )
            elif event_type == QMS_AUDIT_EVENTS.get('REPORT_SIGNED'):
                event = QMSAuditReportSignedEvent(
                    report_id=str(entity_id),
                    audit_plan_id=additional_data.get('audit_plan_id', ''),
                    signed_by=additional_data.get('signed_by', ''),
                    signature_type=additional_data.get('signature_type', ''),
                    user_id=additional_data.get('user_id', additional_data.get('signed_by', '')),
                )
            else:
                logger.warning(f"No event class for QMS audit type: {event_type}")
                return False

            publish_event(event)
            logger.info(f"Published QMS audit event: {event_type} for {entity_id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing QMS audit event {event_type}: {e}")
            return False


# Service instance
messaging_service = KafkaMessagingService()
