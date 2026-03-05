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
    AuditPlanCreatedEvent,
    AuditPlanApprovedEvent,
)
from shared.constants.event_types import (
    AUDIT_ENGAGEMENT_EVENTS,
    WORKING_PAPER_EVENTS,
    AUDIT_FINDING_EVENTS,
    AUDIT_PLAN_EVENTS,
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


# Service instance
messaging_service = KafkaMessagingService()
