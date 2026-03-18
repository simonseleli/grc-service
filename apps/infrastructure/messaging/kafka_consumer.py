"""
Kafka Event Consumer for GRC Service
Consumes events from IAM, Document Records, and other FIMS services
"""
import json
import logging
import time
from typing import Dict, Any, Optional
from django.conf import settings
from kafka import KafkaConsumer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class GRCKafkaConsumer:
    """
    Kafka consumer for GRC service to consume events from other FIMS services
    Follows IAM service implementation pattern (kafka-python library)
    """
    
    def __init__(self):
        """Initialize consumer with FIMS event topics"""
        # Topics to consume from other FIMS services.
        # 'workflow-events' is the topic WO publishes to via WorkflowCompletionHandler
        # (work-orchestration-service/apps/core/services/completion_handler.py).
        self.topics = [
            'fims.iam.user.updated',
            'fims.iam.role.updated',
            'fims.iam.permission.updated',
            'fims.documents.document.created',
            'fims.documents.document.updated',
            'fims.documents.document.archived',
            'fims.documents.document.deleted',
            'workflow-events',
        ]
        
        self.consumer = None
        self._retry_delay = 30  # seconds between retry attempts
        self._max_retries = 10  # maximum number of retries
        
        # Get Kafka configuration
        self.bootstrap_servers = getattr(
            settings, 
            'KAFKA_BOOTSTRAP_SERVERS', 
            'fims-kafka:9092'
        )
        
    def _initialize_consumer(self):
        """Initialize Kafka consumer with retry logic"""
        logger.info(f"🔧 Initializing GRC Kafka consumer with brokers: {self.bootstrap_servers}")
        
        retry_count = 0
        while retry_count < self._max_retries:
            try:
                self.consumer = KafkaConsumer(
                    *self.topics,  # Subscribe to all topics
                    bootstrap_servers=self.bootstrap_servers,
                    group_id='grc-service-consumer-group',
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda m: m.decode('utf-8') if m else None,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=3000,
                    consumer_timeout_ms=1000,  # Don't block forever waiting for messages
                )
                
                logger.info(f"✅ GRC Kafka consumer initialized for topics: {', '.join(self.topics)}")
                return True
                
            except KafkaError as e:
                retry_count += 1
                if retry_count < self._max_retries:
                    logger.warning(
                        f"Failed to initialize Kafka consumer (attempt {retry_count}/{self._max_retries}): {e}"
                    )
                    logger.info(f"Retrying in {self._retry_delay} seconds...")
                    time.sleep(self._retry_delay)
                else:
                    logger.error(
                        f"Failed to initialize Kafka consumer after {self._max_retries} attempts: {e}"
                    )
                    logger.warning("Consumer will continue running and retry periodically")
                    self.consumer = None
                    return False
    
    def _ensure_consumer_initialized(self):
        """Ensure consumer is initialized, retry if necessary"""
        if self.consumer is None:
            logger.info("Attempting to initialize Kafka consumer...")
            return self._initialize_consumer()
        return True
    
    def consume_messages(self):
        """
        Start consuming messages from Kafka topics
        Main entry point for the consumer
        """
        logger.info("🚀 Starting GRC Kafka consumer...")
        
        # Initialize consumer
        if not self._initialize_consumer():
            logger.error("Failed to initialize consumer, will retry in background")
        
        # Continuous consumption loop
        while True:
            try:
                # Ensure consumer is initialized
                if not self._ensure_consumer_initialized():
                    logger.warning(f"Consumer not initialized, sleeping {self._retry_delay}s before retry")
                    time.sleep(self._retry_delay)
                    continue
                
                # Poll for messages
                for message in self.consumer:
                    try:
                        self._process_message(message)
                        self.consumer.commit()
                    except Exception as e:
                        logger.error(f"Error processing message from {message.topic}: {e}", exc_info=True)
                        # Offset is NOT committed so the message will be redelivered
                        
            except KafkaError as e:
                logger.error(f"Kafka consumer error: {e}")
                self.consumer = None  # Force re-initialization
                time.sleep(self._retry_delay)
            except Exception as e:
                logger.error(f"Unexpected error in consumer loop: {e}", exc_info=True)
                time.sleep(self._retry_delay)
    
    def _process_message(self, message):
        """
        Process a single Kafka message and route to appropriate handler
        
        Args:
            message: Kafka message object
        """
        try:
            event_data = message.value
            topic = message.topic
            event_type = event_data.get('event_type', 'unknown')
            service_name = event_data.get('service_name', 'unknown')
            
            logger.info(
                f"📩 Received event: {event_type} from {service_name} (topic: {topic})"
            )
            
            # Route to appropriate handler based on topic
            if topic.startswith('fims.iam.'):
                self._handle_iam_event(event_data, topic)
            elif topic.startswith('fims.documents.'):
                self._handle_document_event(event_data, topic)
            elif topic == 'workflow-events':
                self._handle_workflow_event(event_data, topic)
            else:
                logger.warning(f"No handler for topic: {topic}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise
    
    def _handle_iam_event(self, event_data: Dict[str, Any], topic: str):
        """
        Handle IAM service events (user/role/permission updates)
        
        Args:
            event_data: Event payload
            topic: Kafka topic name
        """
        event_type = event_data.get('event_type', '')
        data = event_data.get('data', {})
        
        try:
            if 'user' in event_type.lower():
                # Handle user-related events
                user_id = data.get('user_id') or data.get('id')
                logger.info(f"Processing IAM user event: {event_type} for user {user_id}")
                
                # TODO: Implement user permission cache update
                # - Update cached user permissions for audit access control
                # - Invalidate any cached user data if needed
                # - Update audit trail with user permission changes
                
            elif 'role' in event_type.lower():
                # Handle role-related events
                role_id = data.get('role_id') or data.get('id')
                logger.info(f"Processing IAM role event: {event_type} for role {role_id}")
                
                # TODO: Implement role update logic
                # - Update role-based access control for audit engagement
                # - Refresh user permissions if roles changed
                # - Update audit team assignments if needed
                
            elif 'permission' in event_type.lower():
                # Handle permission-related events
                permission_code = data.get('permission_code')
                logger.info(f"Processing IAM permission event: {event_type} for {permission_code}")
                
                # TODO: Implement permission update logic
                # - Refresh permission cache
                # - Update access control rules
                
            else:
                logger.warning(f"Unknown IAM event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling IAM event {event_type}: {e}", exc_info=True)
    
    def _handle_document_event(self, event_data: Dict[str, Any], topic: str):
        """
        Handle Document Records service events
        
        Args:
            event_data: Event payload
            topic: Kafka topic name
        """
        event_type = event_data.get('event_type', '')
        data = event_data.get('data', {})
        
        try:
            if 'created' in event_type.lower():
                # Handle document creation
                document_id = data.get('document_id') or data.get('id')
                document_type = data.get('document_type')
                uploader_id = data.get('uploaded_by') or data.get('created_by')
                
                logger.info(
                    f"Processing document creation: {document_id} (type: {document_type}) "
                    f"by user {uploader_id}"
                )
                
                # TODO: Implement auto-linking logic for audit evidence
                # - Check if document should be linked to an audit engagement
                # - Check if document is evidence for a working paper
                # - Auto-categorize document based on audit context
                # - Update working paper evidence references
                
            elif 'updated' in event_type.lower():
                # Handle document updates
                document_id = data.get('document_id') or data.get('id')
                logger.info(f"Processing document update: {document_id}")
                
                # TODO: Implement update logic
                # - Update working paper references if document metadata changed
                # - Track document version history in audit trail
                
            elif 'archived' in event_type.lower():
                # Handle document archival
                document_id = data.get('document_id') or data.get('id')
                logger.info(f"Processing document archival: {document_id}")
                
                # TODO: Implement archival logic
                # - Update working paper status if evidence was archived
                # - Mark audit evidence as archived in working papers
                # - Update audit engagement status if needed
                
            elif 'deleted' in event_type.lower():
                # Handle document deletion
                document_id = data.get('document_id') or data.get('id')
                logger.warning(f"Processing document deletion: {document_id}")
                
                # TODO: Implement deletion logic
                # - Remove document references from working papers
                # - Update audit engagement if critical evidence deleted
                # - Log deletion in audit trail for compliance
                
            else:
                logger.warning(f"Unknown document event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling document event {event_type}: {e}", exc_info=True)
    
    def _handle_workflow_event(self, event_data: Dict[str, Any], topic: str):
        """
        Handle Work Orchestration workflow events from the 'workflow-events' topic.

        WO publishes two event categories here (FIMS Principle 2: WO is sole authority):
          1. Per-stage events (event_type ending '.stage.completed'):
             Fired by WorkflowCompletionHandler.handle_stage_completion() after each stage
             action completes. Used to update GRC entity status incrementally.
             Carries 'stage_key' and 'action_name' in metadata.
          2. Final workflow events (event_type ending '.workflow.completed'):
             Fired by WorkflowCompletionHandler.handle_workflow_completion() when all
             stages are done. Carries 'final_decision' = approved | rejected | cancelled.

        Event structure (from completion_handler.py):
            event_type    : '{workflow_type}.workflow.completed' or '{workflow_type}.stage.completed'
            workflow_type : first segment of template_code  e.g. 'grc'
            final_decision: 'approved' | 'rejected' | 'cancelled' (empty for stage events)
            metadata      : plan context — includes 'subject_ref', 'template_code',
                            'stage_key', 'action_name' (stage events only)
        """
        event_type = event_data.get('event_type', '')
        workflow_type = event_data.get('workflow_type', '')
        final_decision = event_data.get('final_decision', '')
        metadata = event_data.get('metadata', {})

        try:
            # KafkaEventDispatcher publishes WorkflowStageUpdated on every stage action.
            # Handle it first — it has a different structure (payload.planId vs top-level fields).
            if event_type == 'WorkflowStageUpdated':
                self._handle_stage_updated(event_data)
                return

            # Handle both per-stage and full-workflow GRC events
            is_stage_event = event_type.endswith('.stage.completed')
            is_workflow_event = event_type.endswith('.workflow.completed')
            if workflow_type != 'grc' or not (is_stage_event or is_workflow_event):
                logger.debug(f"Ignoring non-GRC workflow event: {event_type}")
                return

            subject_ref = metadata.get('subject_ref')
            if not subject_ref:
                logger.warning(f"Received GRC workflow.completed with no subject_ref: {event_data}")
                return

            # Route by template_code embedded in metadata by OrchestrationClient
            template_code = metadata.get('template_code', '')

            logger.info(
                f"Processing GRC workflow completion: event_type={event_type} "
                f"template_code={template_code} subject_ref={subject_ref} "
                f"final_decision={final_decision}"
            )

            if template_code == 'grc.working_paper_approval':
                self._handle_working_paper_completion(subject_ref, final_decision, event_data)
            elif template_code == 'grc.audit_universe_approval':
                self._handle_audit_universe_completion(subject_ref, final_decision)
            elif template_code == 'grc.rbiap_approval':
                self._handle_audit_plan_completion(subject_ref, final_decision, event_data)
            elif template_code == 'grc.engagement_lifecycle':
                self._handle_audit_engagement_stage(subject_ref, final_decision, metadata)
            elif template_code == 'grc.audit_report_approval':
                self._handle_audit_report_completion(subject_ref, final_decision, event_data)
            elif template_code == 'grc.audit_memo_approval':
                self._handle_audit_memo_completion(subject_ref, final_decision, event_data)
            elif template_code == 'grc.audit_program_approval':
                self._handle_audit_program_completion(subject_ref, final_decision, event_data)
            elif template_code == 'grc.engagement_notification_approval':        # P2-GAP 1
                self._handle_engagement_notification_completion(subject_ref, final_decision, event_data)
            else:
                logger.warning(
                    f"Unknown GRC template_code '{template_code}' for subject_ref={subject_ref}"
                )

        except Exception as e:
            logger.error(f"Error handling workflow event {event_type}: {e}", exc_info=True)

    # ------------------------------------------------------------------ #
    # WorkflowStageUpdated handler (KafkaEventDispatcher events)          #
    # ------------------------------------------------------------------ #

    # Maps template_code → Django model class name for stage sync
    _STAGE_SYNC_MODEL_MAP: Dict[str, str] = {
        'grc.working_paper_approval':           'WorkingPaper',
        'grc.audit_universe_approval':          'AuditUniverse',
        'grc.rbiap_approval':                   'AuditPlan',
        'grc.engagement_lifecycle':             'AuditEngagement',
        'grc.audit_report_approval':            'AuditReport',
        'grc.audit_memo_approval':              'AuditMemo',
        'grc.audit_program_approval':           'AuditProgram',
        'grc.engagement_notification_approval': 'EngagementNotification',
        'grc.quarterly_report_approval':        'QuarterlyAuditReport',
    }

    def _handle_stage_updated(self, event_data: Dict[str, Any]) -> None:
        """
        Handle WorkflowStageUpdated events published by WO's KafkaEventDispatcher.

        Fired on every stage action (submit, approve, reject, return, etc.).
        Keeps the GRC entity's workflow_stage / workflow_stage_id fields current
        so the frontend always reflects the active WO stage.

        Event structure (from advance_stage.py KafkaEventDispatcher.dispatch):
            event_type : 'WorkflowStageUpdated'
            payload    :
                planId       – WO plan UUID
                stageId      – UUID of the stage that was just acted upon
                stageKey     – definition key (e.g. 'cia_review')
                stageName    – display name (e.g. 'CIA Review')
                action       – action taken (e.g. 'approve', 'reject', 'submit', 'return')
                actorId      – UUID of the actor
                newStatus    – new status of that stage ('in_progress', 'completed', 'rejected')
                stageMetadata – stage-level metadata dict

        Mirrors corporate-service WorkflowEventConsumer.process_workflow_stage_updated().
        """
        payload = event_data.get('payload', {})
        plan_id = payload.get('planId')
        action = payload.get('action', '')
        new_status = payload.get('newStatus', '')

        if not plan_id:
            logger.warning("WorkflowStageUpdated missing planId — skipping")
            return

        # Only sync on meaningful transitions (matching corporate filter exactly)
        revision_actions = ('return', 'resubmit', 'withdraw')
        if new_status not in ('completed', 'rejected') and action not in revision_actions:
            logger.debug(
                f"WorkflowStageUpdated: skipping status={new_status!r} action={action!r}"
            )
            return

        # Fetch plan to get entity metadata and current in_progress stage
        from apps.infrastructure.external.orchestration_client import OrchestrationClient
        client = OrchestrationClient()
        plan = client.get_plan(plan_id)
        if not plan:
            logger.warning(f"WorkflowStageUpdated: could not fetch plan {plan_id}")
            return

        metadata = plan.metadata
        template_code = metadata.get('template_code', '')

        # Only process GRC workflows
        if not template_code.startswith('grc.'):
            return

        entity_id = metadata.get('entity_id') or metadata.get('subject_ref')
        if not entity_id:
            logger.warning(
                f"WorkflowStageUpdated: plan {plan_id} missing entity_id/subject_ref in metadata"
            )
            return

        # Locate the stage that is now in_progress (the next active stage).
        # A terminal/display stage (no actions, no assignees) is treated the same as
        # no stage — it means the workflow is effectively complete and we must route
        # to the completion handler rather than just syncing display fields.
        current_stage = next(
            (s for s in plan.stages if s.get('status') == 'in_progress'),
            None,
        )
        is_terminal_stage = (
            current_stage is not None
            and not current_stage.get('actions')
            and not current_stage.get('assignees')
        )
        if not current_stage or is_terminal_stage:
            # No next in_progress stage — the workflow has fully completed or been rejected.
            # WO only fires WorkflowStageUpdated (not grc.workflow.completed) in this env,
            # so we must derive the final decision from plan.plan_status here.
            plan_status = getattr(plan, 'plan_status', '') or ''
            final_decision = ''
            if plan_status in ('approved', 'completed'):
                final_decision = 'approved'
            elif plan_status in ('rejected', 'cancelled'):
                final_decision = 'rejected'

            if final_decision:
                logger.info(
                    f"WorkflowStageUpdated: no next stage, plan_status={plan_status!r} → "
                    f"treating as terminal final_decision={final_decision!r} for "
                    f"template={template_code!r} entity={entity_id}"
                )
                # Route to the correct completion handler
                if template_code == 'grc.working_paper_approval':
                    self._handle_working_paper_completion(entity_id, final_decision, event_data)
                elif template_code == 'grc.audit_universe_approval':
                    self._handle_audit_universe_completion(entity_id, final_decision)
                elif template_code == 'grc.rbiap_approval':
                    self._handle_audit_plan_completion(entity_id, final_decision, event_data)
                elif template_code == 'grc.engagement_lifecycle':
                    self._handle_audit_engagement_stage(entity_id, final_decision, metadata)
                elif template_code == 'grc.audit_report_approval':
                    self._handle_audit_report_completion(entity_id, final_decision, event_data)
                elif template_code == 'grc.audit_memo_approval':
                    self._handle_audit_memo_completion(entity_id, final_decision, event_data)
                elif template_code == 'grc.audit_program_approval':
                    self._handle_audit_program_completion(entity_id, final_decision, event_data)
                elif template_code == 'grc.engagement_notification_approval':
                    self._handle_engagement_notification_completion(entity_id, final_decision, event_data)
                elif template_code == 'grc.quarterly_report_approval':
                    self._handle_quarterly_report_completion(entity_id, final_decision, event_data)
            else:
                logger.debug(
                    f"WorkflowStageUpdated: no in_progress stage for plan {plan_id} "
                    f"plan_status={plan_status!r} — no action taken"
                )
            return

        new_stage_name = current_stage.get('name', '')
        new_stage_id = current_stage.get('id')

        # status_on_complete comes from the stage's own metadata embedded in the event payload
        status_on_complete = payload.get('stageMetadata', {}).get('status_on_complete', '')

        self._sync_workflow_stage(
            entity_id=entity_id,
            template_code=template_code,
            new_stage_name=new_stage_name,
            new_stage_id=str(new_stage_id) if new_stage_id else None,
            status_on_complete=status_on_complete,
        )

    def _sync_workflow_stage(
        self,
        entity_id: str,
        template_code: str,
        new_stage_name: str,
        new_stage_id: Optional[str],
        status_on_complete: str = '',
    ) -> None:
        """
        Update workflow_stage / workflow_stage_id on the GRC entity.
        If status_on_complete is provided (from WO stage metadata), also updates
        the entity's status field — mirroring corporate-service behaviour.

        WorkingPaper is skipped for status updates because its workflow-driven
        field is review_status (not status), which is handled by the completion handler.
        """
        model_name = self._STAGE_SYNC_MODEL_MAP.get(template_code)
        if not model_name:
            logger.warning(
                f"_sync_workflow_stage: no model mapping for template_code={template_code!r}"
            )
            return

        try:
            from apps.core.models import (
                WorkingPaper, AuditUniverse, AuditPlan, AuditEngagement,
                AuditReport, AuditMemo, AuditProgram, EngagementNotification,
                QuarterlyAuditReport,
            )
            _MODEL_CLASSES = {
                'WorkingPaper':           WorkingPaper,
                'AuditUniverse':          AuditUniverse,
                'AuditPlan':              AuditPlan,
                'AuditEngagement':        AuditEngagement,
                'AuditReport':            AuditReport,
                'AuditMemo':              AuditMemo,
                'AuditProgram':           AuditProgram,
                'EngagementNotification': EngagementNotification,
                'QuarterlyAuditReport':   QuarterlyAuditReport,
            }
            model_cls = _MODEL_CLASSES[model_name]
            entity = model_cls.objects.get(id=entity_id)
            entity.update_workflow_stage(stage_name=new_stage_name, stage_id=new_stage_id)
            update_fields = ['workflow_stage', 'workflow_stage_id']

            # Apply status_on_complete from WO stage metadata.
            # Skip WorkingPaper — its workflow status is review_status, not status,
            # and is managed exclusively by the completion event handler.
            if status_on_complete and model_name != 'WorkingPaper':
                entity.status = status_on_complete
                update_fields.append('status')

            entity.save(update_fields=update_fields)
            logger.info(
                f"WorkflowStageUpdated: synced {model_name} {entity_id} → "
                f"stage={new_stage_name!r} stage_id={new_stage_id}"
                + (f" status={status_on_complete!r}" if status_on_complete else "")
            )
        except Exception as exc:
            logger.error(
                f"_sync_workflow_stage: failed to update {model_name} {entity_id}: {exc}",
                exc_info=True,
            )

    # ------------------------------------------------------------------ #
    # Per-entity workflow completion handlers                              #
    # ------------------------------------------------------------------ #

    def _handle_working_paper_completion(
        self, subject_ref: str, final_decision: str, event_data: dict
    ):
        """Update WorkingPaper.review_status when WO workflow completes."""
        from apps.core.models import WorkingPaper

        try:
            wp = WorkingPaper.objects.get(id=subject_ref)
        except WorkingPaper.DoesNotExist:
            logger.warning(f"WorkingPaper {subject_ref} not found for workflow completion event")
            return
        except Exception as exc:
            logger.error(f"DB error looking up WorkingPaper {subject_ref}: {exc}")
            return

        if final_decision == 'approved':
            wp.review_status = 'approved'
            wp.save(update_fields=['review_status'])
            logger.info(f"WorkingPaper {subject_ref} approved via WO workflow event")
        elif final_decision in ('rejected',):
            wp.review_status = 'reviewed'
            result_data = event_data.get('result_data', {})
            comments = result_data.get('comments', '')
            if comments:
                wp.review_comments = comments
                wp.save(update_fields=['review_status', 'review_comments'])
            else:
                wp.save(update_fields=['review_status'])
            logger.info(f"WorkingPaper {subject_ref} rejected via WO workflow event")
        elif final_decision == 'cancelled':
            wp.review_status = 'draft'
            wp.save(update_fields=['review_status'])
            logger.info(f"WorkingPaper {subject_ref} workflow cancelled — reset to draft")
        else:
            logger.warning(
                f"Unknown final_decision '{final_decision}' for WorkingPaper {subject_ref}"
            )

    def _handle_audit_universe_completion(self, subject_ref: str, final_decision: str):
        """Update AuditUniverse.status when CIA review workflow completes."""
        from apps.core.models import AuditUniverse
        from django.utils import timezone

        try:
            universe = AuditUniverse.objects.get(id=subject_ref)
        except AuditUniverse.DoesNotExist:
            logger.warning(f"AuditUniverse {subject_ref} not found for workflow completion event")
            return
        except Exception as exc:
            logger.error(f"DB error looking up AuditUniverse {subject_ref}: {exc}")
            return

        if final_decision == 'approved':
            universe.status = 'approved'
            universe.approved_at = timezone.now()
            universe.complete_workflow()
            universe.save(update_fields=['status', 'approved_at', 'workflow_completed_at'])
            logger.info(f"AuditUniverse {subject_ref} approved via WO workflow event")

            # Notify the original submitter that the universe was approved
            self._publish_universe_decision_notification(
                universe, decision='approved', approved_at=timezone.now()
            )

        elif final_decision in ('rejected', 'cancelled'):
            universe.status = 'draft'
            universe.clear_workflow()
            universe.save(update_fields=['status', 'workflow_plan_id', 'workflow_stage', 'workflow_stage_id', 'workflow_started_at', 'workflow_completed_at'])
            logger.info(f"AuditUniverse {subject_ref} returned to draft (decision: {final_decision})")

            # Notify the original submitter that the universe was returned
            self._publish_universe_decision_notification(
                universe, decision='returned'
            )
        else:
            logger.warning(
                f"Unknown final_decision '{final_decision}' for AuditUniverse {subject_ref}"
            )

    def _publish_universe_decision_notification(
        self, universe, decision: str, approved_at=None, comments: str = ''
    ):
        """
        Publish approved/returned notification for an audit universe.
        Notifies the submitter (created_by) about the CIA decision.
        """
        try:
            from apps.core.notifications.publisher import get_notification_publisher
            from apps.infrastructure.external.iam_client import IAMClient
            from django.conf import settings

            publisher = get_notification_publisher()
            iam = IAMClient()

            # Resolve submitter (created_by)
            submitter_id = str(universe.created_by) if universe.created_by else None
            if not submitter_id:
                logger.warning(f"AuditUniverse {universe.id} has no created_by — cannot notify")
                return

            submitter_profile = iam.get_user_profile(submitter_id)
            submitter_email = submitter_profile.get('email') if submitter_profile else None
            submitter_first = (
                submitter_profile.get('first_name', 'User') if submitter_profile else 'User'
            )

            fiscal_year = getattr(universe.fiscal_year, 'year_code', 'N/A')
            domain = getattr(settings, 'EXTERNAL_DOMAIN', None) or getattr(
                settings, 'TUNNEL_DOMAIN', 'localhost:3001'
            )
            scheme = 'https' if 'localhost' not in domain else 'http'
            detail_url = f"{scheme}://{domain}/service/grc/audit-universe/{universe.id}"

            # Resolve reviewer/approver name
            reviewer_id = str(universe.reviewed_by) if universe.reviewed_by else None
            reviewer_name = 'CIA Reviewer'
            if reviewer_id:
                reviewer_profile = iam.get_user_profile(reviewer_id)
                if reviewer_profile:
                    first = reviewer_profile.get('first_name', '')
                    last = reviewer_profile.get('last_name', '')
                    reviewer_name = f"{first} {last}".strip() or reviewer_name

            recipients = {'user_ids': [submitter_id]}
            if submitter_email:
                recipients['email'] = [submitter_email]

            metadata = {
                'audit_universe_id': str(universe.id),
                'submitter_id': submitter_id,
                'user_ids': [submitter_id],
            }

            if decision == 'approved':
                publisher.send_notification(
                    template_code='grc.audit_universe.approved',
                    recipients=recipients,
                    context={
                        'submitter': {
                            'first_name': submitter_first,
                            'email': submitter_email or '',
                        },
                        'audit_universe': {
                            'id': str(universe.id),
                            'fiscal_year': fiscal_year,
                        },
                        'approver': {'name': reviewer_name},
                        'approved_at': (
                            approved_at.strftime('%Y-%m-%d %H:%M') if approved_at else ''
                        ),
                        'detail_url': detail_url,
                    },
                    priority='normal',
                    metadata=metadata,
                )
            else:
                publisher.send_notification(
                    template_code='grc.audit_universe.returned',
                    recipients=recipients,
                    context={
                        'submitter': {
                            'first_name': submitter_first,
                            'email': submitter_email or '',
                        },
                        'audit_universe': {
                            'id': str(universe.id),
                            'fiscal_year': fiscal_year,
                        },
                        'reviewer': {'name': reviewer_name},
                        'comments': comments or 'No comments provided.',
                        'detail_url': detail_url,
                    },
                    priority='high',
                    metadata=metadata,
                )

            logger.info(
                "Published %s notification for AuditUniverse %s → submitter %s",
                decision,
                universe.id,
                submitter_id,
            )

        except Exception as e:
            logger.error(
                "Failed to publish %s notification for AuditUniverse %s: %s",
                decision,
                universe.id,
                e,
                exc_info=True,
            )

    def _handle_audit_plan_completion(
        self, subject_ref: str, final_decision: str, event_data: dict
    ):
        """Update AuditPlan.status when RBIAP approval workflow completes."""
        from apps.core.models import AuditPlan
        from django.utils import timezone

        try:
            plan = AuditPlan.objects.get(id=subject_ref)
        except AuditPlan.DoesNotExist:
            logger.warning(f"AuditPlan {subject_ref} not found for workflow completion event")
            return
        except Exception as exc:
            logger.error(f"DB error looking up AuditPlan {subject_ref}: {exc}")
            return

        if final_decision == 'approved':
            plan.status = 'approved'
            plan.committee_approved_at = timezone.now()
            plan.complete_workflow()
            plan.save(update_fields=['status', 'committee_approved_at', 'workflow_completed_at'])
            logger.info(f"AuditPlan {subject_ref} approved via WO RBIAP workflow event")

            # Publish FIMS domain event for downstream services — best-effort
            try:
                from apps.infrastructure.services.messaging_service import messaging_service
                from shared.constants.event_types import AUDIT_PLAN_EVENTS
                messaging_service.publish_audit_plan_event(
                    event_type=AUDIT_PLAN_EVENTS.get('PLAN_APPROVED', 'audit_plan.approved'),
                    plan_id=plan.id,
                    additional_data={
                        'fiscal_year': str(plan.fiscal_year.year_code) if plan.fiscal_year else '',
                        'approval_date': timezone.now().isoformat(),
                    },
                )
            except Exception as event_error:
                logger.error(f"Error publishing plan approved domain event: {event_error}")

        elif final_decision in ('rejected', 'cancelled'):
            plan.status = 'draft'
            plan.clear_workflow()
            plan.save(update_fields=['status', 'workflow_plan_id', 'workflow_stage', 'workflow_stage_id', 'workflow_started_at', 'workflow_completed_at'])
            logger.info(f"AuditPlan {subject_ref} returned to draft (decision: {final_decision})")
        else:
            logger.warning(
                f"Unknown final_decision '{final_decision}' for AuditPlan {subject_ref}"
            )

    def _handle_audit_engagement_stage(
        self, subject_ref: str, final_decision: str, metadata: dict
    ):
        """
        Update AuditEngagement.status when WO fires a workflow or stage event.

        Two event types are handled (FIMS Principle 2: WO drives all lifecycle transitions):

        1. Per-stage events (final_decision is empty, metadata has stage_key + action_name):
           Fired after each stage action completes in WO. Maps directly to a GRC status:
             planning  + start_fieldwork  → fieldwork
             fieldwork + start_reporting  → reporting
           The 'planning → fieldwork' transition is handled here via Kafka so GRC stays
           consistent with WO authority (note: start_workflow() in service also sets
           fieldwork immediately for UX responsiveness, but the Kafka event is canonical).

        2. Final workflow events (final_decision = 'approved' | 'rejected' | 'cancelled'):
           Fired once when all WO stages complete.
             approved  → completed
             rejected / cancelled → reset to planning
        """
        from apps.core.models import AuditEngagement
        from django.utils import timezone

        try:
            engagement = AuditEngagement.objects.get(id=subject_ref)
        except AuditEngagement.DoesNotExist:
            logger.warning(f"AuditEngagement {subject_ref} not found for workflow completion event")
            return
        except Exception as exc:
            logger.error(f"DB error looking up AuditEngagement {subject_ref}: {exc}")
            return

        # ── Per-stage transitions: WO fires these as each lifecycle phase advances ──
        stage_key = metadata.get('stage_key', '')
        action_name = metadata.get('action_name', '')

        # Map (completed_stage, action_taken) → next GRC engagement status
        STAGE_STATUS_MAP = {
            ('planning', 'start_fieldwork'): 'fieldwork',
            ('fieldwork', 'start_reporting'): 'reporting',
        }

        new_status = STAGE_STATUS_MAP.get((stage_key, action_name))
        if new_status:
            engagement.status = new_status
            engagement.save(update_fields=['status'])
            logger.info(
                "AuditEngagement %s status updated to '%s' via WO stage event "
                "(stage=%s action=%s)",
                subject_ref, new_status, stage_key, action_name,
            )
            return

        # If stage_key + action_name were present but not in the map, this is the
        # terminal 'reporting → complete' stage event — the workflow completion event
        # that follows immediately will handle the 'completed' status transition.
        if stage_key and action_name:
            logger.debug(
                "AuditEngagement %s: terminal stage event (stage=%s action=%s) — "
                "awaiting workflow completion event for final status.",
                subject_ref, stage_key, action_name,
            )
            return

        # ── Final workflow completion: WO fires this once all stages are done ──
        if final_decision == 'approved':
            # Workflow fully completed — engagement is done
            engagement.status = 'completed'
            engagement.complete_workflow()
            if not engagement.actual_end_date:
                engagement.actual_end_date = timezone.now().date()
            engagement.save(update_fields=['status', 'workflow_completed_at', 'actual_end_date'])
            logger.info(f"AuditEngagement {subject_ref} marked completed via WO workflow event")
        elif final_decision in ('rejected', 'cancelled'):
            # Workflow cancelled — reset to planning
            engagement.status = 'planning'
            engagement.clear_workflow()
            engagement.save(update_fields=['status', 'workflow_plan_id', 'workflow_stage', 'workflow_stage_id', 'workflow_started_at', 'workflow_completed_at'])
            logger.info(f"AuditEngagement {subject_ref} workflow cancelled — reset to planning")
        else:
            logger.warning(
                f"Unhandled WO event for AuditEngagement {subject_ref}: "
                f"stage_key={stage_key!r} action={action_name!r} final_decision={final_decision!r}"
            )

    def _handle_audit_report_completion(self, subject_ref: str, final_decision: str, event_data: dict = None):
        """Update AuditReport.status when CIA review workflow completes.

        On approval:
        - Sets status, approval_date, approved_by on the report
        - Publishes GAP 12 finding.finalized events for all findings in the engagement
        - Triggers GAP 9 DRS stamp to embed CIA signature + QR code (best-effort)
        """
        from apps.core.models import AuditReport
        from django.utils import timezone

        event_data = event_data or {}

        try:
            report = AuditReport.objects.select_related(
                'engagement__auditable_entity',
                'engagement__audit_plan__fiscal_year',
            ).get(id=subject_ref)
        except AuditReport.DoesNotExist:
            logger.warning(f"AuditReport {subject_ref} not found for workflow completion event")
            return
        except Exception as exc:
            logger.error(f"DB error looking up AuditReport {subject_ref}: {exc}")
            return

        if final_decision == 'approved':
            # ----- resolve the approver user ID from the WO event -----
            approved_by_id = (
                event_data.get('user_id')
                or event_data.get('approved_by')
                or (event_data.get('metadata') or {}).get('user_id')
                or str(report.approved_by) if report.approved_by else None
            )

            now = timezone.now()
            update_fields = ['status', 'approval_date', 'workflow_completed_at']
            report.status = 'approved'
            report.approval_date = now
            report.workflow_completed_at = now
            if approved_by_id and not report.approved_by:
                report.approved_by = approved_by_id
                update_fields.append('approved_by')
            report.save(update_fields=update_fields)
            logger.info(f"AuditReport {subject_ref} approved via WO workflow event")

            # ----- GAP 12: publish finding.finalized for all findings -----
            try:
                from apps.infrastructure.services.messaging_service import messaging_service
                findings = report.engagement.findings.select_related(
                    'finding_type', 'severity', 'risk_rating',
                    'engagement__auditable_entity',
                    'engagement__audit_plan__fiscal_year',
                ).filter(is_active=True)
                published = 0
                for finding in findings:
                    ok = messaging_service.publish_finding_finalized_event(
                        finding=finding,
                        approved_by=approved_by_id or '',
                    )
                    if ok:
                        published += 1
                logger.info(
                    f"Published {published} finding.finalized events for report {subject_ref}"
                )
            except Exception as gap12_err:
                logger.error(
                    f"GAP 12: Failed to publish finding.finalized events for report "
                    f"{subject_ref}: {gap12_err}"
                )

            # ----- GAP 9: stamp approved PDF with CIA signature + QR -----
            if report.document_id:
                try:
                    self._trigger_approved_stamp(
                        document_id=str(report.document_id),
                        approver_id=approved_by_id or '',
                        entity_type='audit_report',
                        entity_id=subject_ref,
                        entity=report,
                        stamp_field='stamped_document_url',
                    )
                except Exception as gap9_err:
                    logger.error(
                        f"GAP 9: Failed to trigger stamp for AuditReport {subject_ref}: {gap9_err}"
                    )

        elif final_decision == 'distributed':
            report.status = 'distributed'
            report.distributed_at = timezone.now()
            report.complete_workflow()
            report.save(update_fields=['status', 'distributed_at', 'workflow_completed_at'])
            logger.info(f"AuditReport {subject_ref} marked distributed via WO workflow event")
        elif final_decision in ('rejected', 'cancelled'):
            report.status = 'draft'
            report.clear_workflow()
            report.save(update_fields=['status', 'workflow_plan_id', 'workflow_stage', 'workflow_stage_id', 'workflow_started_at', 'workflow_completed_at'])
            logger.info(f"AuditReport {subject_ref} returned to draft (decision: {final_decision})")
        else:
            logger.warning(
                f"Unknown final_decision '{final_decision}' for AuditReport {subject_ref}"
            )

    def _handle_audit_memo_completion(
        self, subject_ref: str, final_decision: str, event_data: dict = None
    ):
        """
        Update AuditMemo.status when the grc.audit_memo_approval workflow completes.

        Workflow stages (from get_workflow_stages()):
          cia_review → dg_approval → transmission
        Final workflow event: approved → status='approved' | rejected/cancelled → 'draft'

        Also triggers GAP 9 DRS stamp if a document_id is attached.
        """
        from apps.core.models import AuditMemo
        from django.utils import timezone

        event_data = event_data or {}

        try:
            memo = AuditMemo.objects.get(id=subject_ref)
        except AuditMemo.DoesNotExist:
            logger.warning(f"AuditMemo {subject_ref} not found for workflow completion event")
            return
        except Exception as exc:
            logger.error(f"DB error looking up AuditMemo {subject_ref}: {exc}")
            return

        if final_decision == 'approved':
            approved_by_id = (
                event_data.get('user_id')
                or event_data.get('approved_by')
                or (event_data.get('metadata') or {}).get('user_id')
            )

            now = timezone.now()
            update_fields = ['status', 'dg_approval_date', 'workflow_completed_at']
            memo.status = 'approved'
            memo.dg_approval_date = now
            memo.workflow_completed_at = now
            if approved_by_id and not memo.approved_by_dg:
                memo.approved_by_dg = approved_by_id
                update_fields.append('approved_by_dg')
            memo.save(update_fields=update_fields)
            logger.info(f"AuditMemo {subject_ref} approved via WO workflow event")

            # GAP 9: stamp PDF if a DRS document is attached
            if getattr(memo, 'document_id', None):
                try:
                    self._trigger_approved_stamp(
                        document_id=str(memo.document_id),
                        approver_id=approved_by_id or '',
                        entity_type='audit_memo',
                        entity_id=subject_ref,
                        entity=memo,
                        stamp_field='stamped_document_url',
                    )
                except Exception as gap9_err:
                    logger.error(
                        f"GAP 9: Failed to trigger stamp for AuditMemo {subject_ref}: {gap9_err}"
                    )

        elif final_decision in ('rejected', 'cancelled'):
            memo.status = 'draft'
            memo.clear_workflow()
            memo.save(update_fields=[
                'status', 'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
                'workflow_started_at', 'workflow_completed_at',
            ])
            logger.info(f"AuditMemo {subject_ref} returned to draft (decision: {final_decision})")
        else:
            logger.warning(
                f"Unknown final_decision '{final_decision}' for AuditMemo {subject_ref}"
            )

    def _handle_audit_program_completion(
        self, subject_ref: str, final_decision: str, event_data: dict = None
    ):
        """
        Update AuditProgram.status when the grc.audit_program_approval workflow completes.

        Workflow stages (from get_workflow_stages()):
          ia_review → cia_approval
        Final workflow event: approved → status='approved' | rejected/cancelled → 'draft'

        Also triggers GAP 9 DRS stamp if a document_id is attached.
        """
        from apps.core.models import AuditProgram
        from django.utils import timezone

        event_data = event_data or {}

        try:
            program = AuditProgram.objects.get(id=subject_ref)
        except AuditProgram.DoesNotExist:
            logger.warning(f"AuditProgram {subject_ref} not found for workflow completion event")
            return
        except Exception as exc:
            logger.error(f"DB error looking up AuditProgram {subject_ref}: {exc}")
            return

        if final_decision == 'approved':
            approved_by_id = (
                event_data.get('user_id')
                or event_data.get('approved_by')
                or (event_data.get('metadata') or {}).get('user_id')
            )

            now = timezone.now()
            update_fields = ['status', 'approval_date', 'workflow_completed_at']
            program.status = 'approved'
            program.approval_date = now
            program.workflow_completed_at = now
            if approved_by_id and not program.approved_by:
                program.approved_by = approved_by_id
                update_fields.append('approved_by')
            program.save(update_fields=update_fields)
            logger.info(f"AuditProgram {subject_ref} approved via WO workflow event")

            # GAP 9: stamp PDF if a DRS document is attached
            if getattr(program, 'document_id', None):
                try:
                    self._trigger_approved_stamp(
                        document_id=str(program.document_id),
                        approver_id=approved_by_id or '',
                        entity_type='audit_program',
                        entity_id=subject_ref,
                        entity=program,
                        stamp_field='stamped_document_url',
                    )
                except Exception as gap9_err:
                    logger.error(
                        f"GAP 9: Failed to trigger stamp for AuditProgram {subject_ref}: {gap9_err}"
                    )

        elif final_decision in ('rejected', 'cancelled'):
            program.status = 'draft'
            program.clear_workflow()
            program.save(update_fields=[
                'status', 'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
                'workflow_started_at', 'workflow_completed_at',
            ])
            logger.info(
                f"AuditProgram {subject_ref} returned to draft (decision: {final_decision})"
            )
        else:
            logger.warning(
                f"Unknown final_decision '{final_decision}' for AuditProgram {subject_ref}"
            )

    def _handle_engagement_notification_completion(
        self, subject_ref: str, final_decision: str, event_data: dict = None
    ):
        """
        Update EngagementNotification.status when the grc.engagement_notification_approval
        workflow completes.  (P2-GAP 1 — SRS Req 25)

        Final workflow event:
          approved          → status='approved', cia_approval_date, workflow_completed_at, approved_by_cia
          rejected/cancelled → status='draft', clear WorkflowMixin fields
        """
        from apps.core.models import EngagementNotification
        from django.utils import timezone

        event_data = event_data or {}

        try:
            en = EngagementNotification.objects.get(id=subject_ref)
        except EngagementNotification.DoesNotExist:
            logger.warning(
                f"EngagementNotification {subject_ref} not found for workflow completion event"
            )
            return
        except Exception as exc:
            logger.error(
                f"DB error looking up EngagementNotification {subject_ref}: {exc}"
            )
            return

        if final_decision == 'approved':
            approved_by_id = (
                event_data.get('user_id')
                or event_data.get('approved_by')
                or (event_data.get('metadata') or {}).get('user_id')
            )

            now = timezone.now()
            update_fields = ['status', 'cia_approval_date', 'workflow_completed_at']
            en.status = 'approved'
            en.cia_approval_date = now
            en.workflow_completed_at = now
            if approved_by_id and not en.approved_by_cia:
                en.approved_by_cia = approved_by_id
                update_fields.append('approved_by_cia')
            en.save(update_fields=update_fields)
            logger.info(f"EngagementNotification {subject_ref} approved via WO workflow event")

            # GAP 9: stamp PDF if a DRS document is attached
            if getattr(en, 'document_id', None):
                try:
                    self._trigger_approved_stamp(
                        document_id=str(en.document_id),
                        approver_id=approved_by_id or '',
                        entity_type='engagement_notification',
                        entity_id=subject_ref,
                        entity=en,
                        stamp_field='stamped_document_url',
                    )
                except Exception as gap9_err:
                    logger.error(
                        f"GAP 9: Failed to trigger stamp for EngagementNotification {subject_ref}: {gap9_err}"
                    )

            # Notify LA that EN was approved
            try:
                from apps.core.services.engagement_notification_service import (
                    EngagementNotificationService,
                )
                EngagementNotificationService()._publish_approval_notification(
                    en, approved_by_id or '', approved=True
                )
            except Exception as notif_err:
                logger.error(
                    f"Failed to publish approval notification for EngagementNotification "
                    f"{subject_ref}: {notif_err}"
                )

        elif final_decision in ('rejected', 'cancelled'):
            # Resolve comments from event_data for the return notification
            result_data = event_data.get('result_data', {})
            comments = result_data.get('comments', '')

            reviewer_id = (
                event_data.get('user_id')
                or (event_data.get('metadata') or {}).get('user_id')
                or ''
            )

            en.status = 'draft'
            en.clear_workflow()
            en.save(update_fields=[
                'status', 'workflow_plan_id', 'workflow_stage', 'workflow_stage_id',
                'workflow_started_at', 'workflow_completed_at',
            ])
            logger.info(
                f"EngagementNotification {subject_ref} returned to draft "
                f"(decision: {final_decision})"
            )

            # Notify LA that EN was returned
            try:
                from apps.core.services.engagement_notification_service import (
                    EngagementNotificationService,
                )
                EngagementNotificationService()._publish_approval_notification(
                    en, reviewer_id, approved=False, comments=comments
                )
            except Exception as notif_err:
                logger.error(
                    f"Failed to publish return notification for EngagementNotification "
                    f"{subject_ref}: {notif_err}"
                )

        else:
            logger.warning(
                f"Unknown final_decision '{final_decision}' for "
                f"EngagementNotification {subject_ref}"
            )

    def _trigger_approved_stamp(
        self,
        document_id: str,
        approver_id: str,
        entity_type: str,
        entity_id: str,
        entity,
        stamp_field: str = 'stamped_document_url',
    ) -> None:
        """
        Call DRS to overlay CIA signature + QR code onto the approved PDF document.

        Best-effort: logs and swallows all errors so the approval is never blocked.
        Stores the returned stamped_document_url on the entity model.

        Args:
            document_id: DRS document UUID to stamp.
            approver_id: CIA user UUID (used to fetch signature from IAM via DRS).
            entity_type: GRC entity type label (e.g. 'audit_report').
            entity_id:   GRC entity UUID (embedded in QR verification URL).
            entity:      Django model instance to update with stamped_document_url.
            stamp_field: field name on entity for the stamped URL (default 'stamped_document_url').
        """
        from apps.infrastructure.external.document_service_client import DocumentServiceClient
        from django.conf import settings

        service_token = getattr(settings, 'SERVICE_TO_SERVICE_TOKEN', None)
        client = DocumentServiceClient(auth_token=None)
        result = client.generate_approved_stamp(
            document_id=document_id,
            approver_id=approver_id,
            entity_type=entity_type,
            entity_id=entity_id,
            service_token=service_token,
        )

        stamped_url = result.get('stamped_document_url')
        if stamped_url and hasattr(entity, stamp_field):
            setattr(entity, stamp_field, stamped_url)
            entity.save(update_fields=[stamp_field])
            logger.info(
                f"GAP 9: Saved stamped_document_url on {entity_type} {entity_id}: {stamped_url}"
            )
    
    def close(self):
        """Close the Kafka consumer gracefully"""
        if self.consumer:
            logger.info("Closing GRC Kafka consumer...")
            self.consumer.close()
            logger.info("✅ GRC Kafka consumer closed")
