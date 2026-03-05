"""
Notification Publisher for GRC Service.
Publishes notification events to Kafka for Work Orchestration to process.

Follows the same pattern as:
  - iam-service/apps/core/notifications/publisher.py
  - document-records-service/apps/core/notifications/publisher.py
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.utils import timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class NotificationPublisher:
    """Publishes notification events to Kafka."""

    def __init__(self):
        self.kafka_bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(',')
        # Priority-based topics (same as IAM / Document Records)
        self.topics = {
            'urgent': getattr(settings, 'KAFKA_NOTIFICATIONS_URGENT_TOPIC', 'notifications-urgent'),
            'high': getattr(settings, 'KAFKA_NOTIFICATIONS_HIGH_TOPIC', 'notifications-high'),
            'normal': getattr(settings, 'KAFKA_NOTIFICATIONS_NORMAL_TOPIC', 'notifications-normal'),
            'low': getattr(settings, 'KAFKA_NOTIFICATIONS_LOW_TOPIC', 'notifications-low'),
        }
        # Fallback to default topic
        self.topic = getattr(settings, 'KAFKA_NOTIFICATIONS_TOPIC', 'notifications')
        self.service_name = 'grc-service'
        self._producer: Optional[KafkaProducer] = None

    def _get_producer(self) -> Optional[KafkaProducer]:
        """Get or create Kafka producer."""
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    retries=3,
                    retry_backoff_ms=250,
                    request_timeout_ms=30000,
                )
                logger.info("Initialized Kafka producer for GRC notifications")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}", exc_info=True)
                return None
        return self._producer

    def _generate_idempotency_key(
        self,
        template_code: str,
        recipient: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Generate idempotency key for notification.
        Uses template code, recipient, and key context fields.
        """
        key_parts = [template_code, recipient]

        # Add important context fields to ensure uniqueness
        if 'audit_universe' in context and isinstance(context['audit_universe'], dict):
            entity_id = context['audit_universe'].get('id', '')
            key_parts.append(str(entity_id))
        elif 'audit_plan' in context and isinstance(context['audit_plan'], dict):
            entity_id = context['audit_plan'].get('id', '')
            key_parts.append(str(entity_id))
        elif 'engagement' in context and isinstance(context['engagement'], dict):
            entity_id = context['engagement'].get('id', '')
            key_parts.append(str(entity_id))

        # Add timestamp to minute precision for idempotency window
        timestamp_minute = timezone.now().strftime('%Y%m%d%H%M')
        key_parts.append(timestamp_minute)

        return '-'.join(key_parts)

    def send_notification(
        self,
        template_code: str,
        recipients: Dict[str, List[str]],
        context: Dict[str, Any],
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish notification event to Kafka.

        Args:
            template_code: Template code (e.g., 'grc.audit_universe.submitted')
            recipients: Dictionary with channel keys and recipient lists
                       e.g., {'email': ['user@example.com'], 'user_ids': ['uuid-...']}
            context: Template context variables
            priority: Notification priority ('low', 'normal', 'high', 'urgent')
            metadata: Optional metadata

        Returns:
            True if event was published successfully, False otherwise
        """
        producer = self._get_producer()
        if not producer:
            logger.error("Cannot send notification: Kafka producer not available")
            return False

        # Generate idempotency key from first recipient
        first_recipient = None
        for channel_recipients in recipients.values():
            if channel_recipients:
                first_recipient = (
                    channel_recipients[0]
                    if isinstance(channel_recipients, list)
                    else channel_recipients
                )
                break

        idempotency_key = self._generate_idempotency_key(
            template_code,
            first_recipient or 'unknown',
            context,
        )

        # Create notification event (same structure as IAM / Document Records)
        event = {
            'event_type': 'notification.send',
            'event_version': '1.0',
            'timestamp': timezone.now().isoformat(),
            'source_service': self.service_name,
            'notification': {
                'idempotency_key': idempotency_key,
                'template_code': template_code,
                'recipients': recipients,
                'context': context,
                'priority': priority,
                'metadata': metadata or {},
            },
        }

        try:
            # Select topic based on priority
            topic = self.topics.get(priority.lower(), self.topic)

            # Publish to Kafka (partition by template code for ordering)
            future = producer.send(
                topic=topic,
                key=template_code,
                value=event,
            )

            # Wait for delivery (with timeout)
            try:
                record_metadata = future.get(timeout=10)
                logger.info(
                    f"Notification event published: {template_code} "
                    f"(topic: {record_metadata.topic}, partition: {record_metadata.partition}, "
                    f"idempotency_key: {idempotency_key})"
                )
                return True
            except Exception as e:
                logger.error(f"Failed to deliver notification {template_code}: {e}")
                return False

        except Exception as e:
            logger.error(f"Error publishing notification {template_code}: {e}", exc_info=True)
            return False

    def send_email(
        self,
        template_code: str,
        to: str | List[str],
        context: Dict[str, Any],
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Convenience method to send email notification.

        Args:
            template_code: Template code
            to: Email address(es) - string or list
            context: Template context
            priority: Notification priority
            metadata: Optional metadata

        Returns:
            True if event was published successfully
        """
        if isinstance(to, str):
            to = [to]

        return self.send_notification(
            template_code=template_code,
            recipients={'email': to},
            context=context,
            priority=priority,
            metadata=metadata,
        )

    def send_sms(
        self,
        template_code: str,
        to: str | List[str],
        context: Dict[str, Any],
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Convenience method to send SMS notification.

        Args:
            template_code: Template code
            to: Phone number(s) - string or list
            context: Template context
            priority: Notification priority
            metadata: Optional metadata

        Returns:
            True if event was published successfully
        """
        if isinstance(to, str):
            to = [to]

        return self.send_notification(
            template_code=template_code,
            recipients={'sms': to},
            context=context,
            priority=priority,
            metadata=metadata,
        )

    def send_in_app(
        self,
        template_code: str,
        user_ids: List[str],
        context: Dict[str, Any],
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Convenience method to send in-app notification.
        The WO NotificationConsumer creates NotificationModel records
        for each user_id in the recipients.

        Args:
            template_code: Template code
            user_ids: List of user UUIDs to notify
            context: Template context
            priority: Notification priority
            metadata: Optional metadata

        Returns:
            True if event was published successfully
        """
        merged_metadata = {**(metadata or {}), 'user_ids': user_ids}

        return self.send_notification(
            template_code=template_code,
            recipients={'user_ids': user_ids},
            context=context,
            priority=priority,
            metadata=merged_metadata,
        )

    def close(self):
        """Close the Kafka producer."""
        if self._producer:
            try:
                self._producer.close()
                logger.info("GRC notification publisher producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")


# Singleton instance
_notification_publisher: Optional[NotificationPublisher] = None


def get_notification_publisher() -> NotificationPublisher:
    """Get singleton instance of notification publisher."""
    global _notification_publisher
    if _notification_publisher is None:
        _notification_publisher = NotificationPublisher()
    return _notification_publisher
