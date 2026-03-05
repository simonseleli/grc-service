"""
Template Registry for GRC Service.
Registers notification templates with Work Orchestration via Kafka on startup.

This follows the exact FIMS pattern used by:
  - iam-service/apps/core/templates/registry.py
  - document-records-service/apps/core/templates/registry.py

Flow:
  1. GRC starts → apps.py ready() → _register_notification_templates()
  2. Registry reads notifications.yaml → publishes `template.registered` events
     to Kafka `notification-templates` topic
  3. WO's TemplateRegistrationConsumer stores templates in NotificationTemplateModel
  4. When GRC publishes `notification.send` with `template_code`, WO looks up
     the template from its DB, renders it, and delivers via email/SMS/in-app
"""

import json
import logging
import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """Manages notification template registration for GRC service."""

    def __init__(self):
        self.kafka_bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(',')
        self.topic = getattr(settings, 'KAFKA_NOTIFICATION_TEMPLATES_TOPIC', 'notification-templates')
        self.service_name = 'grc-service'
        self.service_version = getattr(settings, 'SERVICE_VERSION', '1.0.0')
        self._producer: Optional[KafkaProducer] = None

    def _get_producer(self) -> Optional[KafkaProducer]:
        """Get or create Kafka producer."""
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    retries=3,
                    retry_backoff_ms=250,
                    request_timeout_ms=30000,
                )
                logger.info("Initialized Kafka producer for template registration")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}", exc_info=True)
                return None
        return self._producer

    def _load_templates_from_yaml(self) -> List[Dict[str, Any]]:
        """Load templates from YAML file."""
        try:
            # Get the templates directory
            templates_dir = Path(__file__).parent
            yaml_file = templates_dir / 'notifications.yaml'

            if not yaml_file.exists():
                logger.warning(f"Templates file not found: {yaml_file}")
                return []

            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                templates = data.get('templates', [])
                logger.info(f"Loaded {len(templates)} templates from {yaml_file}")
                return templates

        except Exception as e:
            logger.error(f"Error loading templates from YAML: {e}", exc_info=True)
            return []

    def _validate_template(self, template: Dict[str, Any]) -> bool:
        """Validate template structure."""
        required_fields = ['code', 'name', 'category', 'channels', 'subject']

        for field in required_fields:
            if field not in template:
                logger.error(f"Template missing required field: {field}")
                return False

        # Validate code format
        code = template.get('code', '')
        if not code.startswith('grc.'):
            logger.warning(f"Template code '{code}' should start with 'grc.'")

        return True

    def _create_registration_event(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Create template registration event."""
        return {
            'event_type': 'template.registered',
            'event_version': '1.0',
            'timestamp': timezone.now().isoformat(),
            'source_service': self.service_name,
            'source_version': self.service_version,
            'template': template
        }

    def register_templates(self) -> int:
        """
        Load templates and publish them to Kafka.

        Returns:
            Number of templates successfully published
        """
        producer = self._get_producer()
        if not producer:
            logger.error("Cannot register templates: Kafka producer not available")
            return 0

        templates = self._load_templates_from_yaml()
        if not templates:
            logger.warning("No templates to register")
            return 0

        registered = 0

        for template in templates:
            # Validate template
            if not self._validate_template(template):
                logger.error(f"Skipping invalid template: {template.get('code', 'unknown')}")
                continue

            try:
                # Create registration event
                event = self._create_registration_event(template)

                # Publish to Kafka (value_serializer will handle JSON encoding)
                template_code = template.get('code', 'unknown')
                future = producer.send(
                    topic=self.topic,
                    key=template_code,  # Partition by template code
                    value=event  # Will be serialized by value_serializer
                )

                # Wait for delivery (with timeout)
                try:
                    record_metadata = future.get(timeout=10)
                    logger.info(
                        f"Template registration published: {template_code} "
                        f"(topic: {record_metadata.topic}, partition: {record_metadata.partition})"
                    )
                    registered += 1
                except Exception as e:
                    logger.error(f"Failed to deliver template {template_code}: {e}")

            except Exception as e:
                logger.error(f"Error registering template {template.get('code', 'unknown')}: {e}", exc_info=True)

        # Flush to ensure all messages are sent
        try:
            producer.flush(timeout=30)
            logger.info(f"Successfully registered {registered} out of {len(templates)} templates")
        except Exception as e:
            logger.error(f"Error flushing producer: {e}")

        return registered

    def close(self):
        """Close the Kafka producer."""
        if self._producer:
            try:
                self._producer.close()
                logger.info("Template registry producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")


# Singleton instance
_template_registry: Optional[TemplateRegistry] = None


def get_template_registry() -> TemplateRegistry:
    """Get singleton instance of template registry."""
    global _template_registry
    if _template_registry is None:
        _template_registry = TemplateRegistry()
    return _template_registry
