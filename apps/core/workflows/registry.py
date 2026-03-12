"""
GRC Service Workflow Template Registry.
Publishes workflow templates to Work Orchestration via Kafka.

Mirrors corporate-service/apps/core/workflows/registry.py exactly,
with SERVICE_NAME = "grc-service".
"""
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)


class WorkflowTemplateRegistry:
    """
    Registry for managing and publishing workflow templates to Kafka.

    Templates are loaded from YAML files and published to the Work Orchestration
    service via Kafka for centralized workflow management.
    """

    SERVICE_NAME = "grc-service"
    SERVICE_VERSION = getattr(settings, 'SERVICE_VERSION', '1.0.0')

    def __init__(self):
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._producer = None
        self._topic = getattr(
            settings,
            'KAFKA_WORKFLOW_TEMPLATES_TOPIC',
            'workflow-templates'
        )

    def _get_producer(self):
        """Get or create Kafka producer."""
        if self._producer is None:
            try:
                from confluent_kafka import Producer

                kafka_config = {
                    'bootstrap.servers': getattr(
                        settings,
                        'KAFKA_BOOTSTRAP_SERVERS',
                        os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
                    ),
                    'client.id': f'{self.SERVICE_NAME}-workflow-template-registry',
                    'acks': 'all',
                    'retries': 3,
                    'retry.backoff.ms': 1000,
                }

                self._producer = Producer(kafka_config)
                logger.debug("Kafka producer created for workflow template registry")

            except ImportError:
                logger.error("confluent_kafka not installed. Workflow template publishing unavailable.")
                return None
            except Exception as e:
                logger.error(f"Failed to create Kafka producer: {e}")
                return None

        return self._producer

    def _delivery_callback(self, err, msg):
        """Callback for Kafka message delivery."""
        if err:
            logger.error(f"Workflow template delivery failed: {err}")
        else:
            logger.debug(
                f"Workflow template delivered to {msg.topic()} [{msg.partition()}] "
                f"at offset {msg.offset()}"
            )

    def load_templates(self, template_file: Optional[str] = None) -> int:
        """
        Load templates from YAML file.

        Returns:
            Number of templates loaded.
        """
        if template_file is None:
            template_file = Path(__file__).parent / 'workflows.yaml'
        else:
            template_file = Path(template_file)

        if not template_file.exists():
            logger.warning(f"Workflow template file not found: {template_file}")
            return 0

        try:
            with open(template_file, 'r') as f:
                data = yaml.safe_load(f)

            templates = data.get('templates', [])

            for template in templates:
                code = template.get('code')
                if code:
                    template['_loaded_at'] = datetime.utcnow().isoformat()
                    template['_source_file'] = str(template_file)
                    template['_checksum'] = self._compute_checksum(template)
                    self._templates[code] = template

            logger.info(f"Loaded {len(templates)} workflow templates from {template_file}")
            return len(templates)

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse workflow template YAML: {e}")
            return 0
        except Exception as e:
            logger.error(f"Failed to load workflow templates: {e}")
            return 0

    def _compute_checksum(self, template: Dict[str, Any]) -> str:
        """Compute checksum for template content."""
        content = {k: v for k, v in template.items() if not k.startswith('_')}
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def get_template(self, code: str) -> Optional[Dict[str, Any]]:
        """Get a template by code."""
        return self._templates.get(code)

    def list_templates(self) -> List[str]:
        """List all template codes."""
        return list(self._templates.keys())

    def publish_templates(self) -> bool:
        """
        Publish all loaded templates to Kafka.

        Returns:
            True if all templates published successfully.
        """
        producer = self._get_producer()
        if producer is None:
            logger.error("No Kafka producer available for workflow template publishing")
            return False

        if not self._templates:
            self.load_templates()

        if not self._templates:
            logger.warning("No workflow templates to publish")
            return False

        success_count = 0

        for code, template in self._templates.items():
            try:
                message = self._create_registration_message(template)

                producer.produce(
                    topic=self._topic,
                    key=code.encode('utf-8'),
                    value=json.dumps(message).encode('utf-8'),
                    callback=self._delivery_callback
                )

                success_count += 1

            except Exception as e:
                logger.error(f"Failed to publish workflow template {code}: {e}")

        try:
            remaining = producer.flush(timeout=10)
            if remaining > 0:
                logger.warning(f"{remaining} workflow template messages were not delivered")

        except Exception as e:
            logger.error(f"Error flushing Kafka messages: {e}")
            return False

        logger.info(f"Published {success_count}/{len(self._templates)} workflow templates to Kafka")
        return success_count == len(self._templates)

    def _create_registration_message(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Create Kafka message for workflow template registration."""
        return {
            'event_type': 'workflow.template.registered',
            'timestamp': datetime.utcnow().isoformat(),
            'source_service': self.SERVICE_NAME,
            'source_version': self.SERVICE_VERSION,
            'template': {
                'code': template.get('code'),
                'name': template.get('name'),
                'workflow_type': template.get('workflow_type'),
                'version': template.get('version', 1),
                'is_active': template.get('is_active', True),
                'definition': template.get('definition', {}),
                'checksum': template.get('_checksum'),
            }
        }

    def get_registration_summary(self) -> Dict[str, Any]:
        """Get summary of workflow template registration data."""
        if not self._templates:
            self.load_templates()

        workflow_types: Dict[str, int] = {}
        for template in self._templates.values():
            wt = template.get('workflow_type', 'unknown')
            workflow_types[wt] = workflow_types.get(wt, 0) + 1

        return {
            'service_name': self.SERVICE_NAME,
            'service_version': self.SERVICE_VERSION,
            'total_templates': len(self._templates),
            'templates_by_workflow_type': workflow_types,
            'template_codes': list(self._templates.keys()),
        }


# Singleton instance
workflow_template_registry = WorkflowTemplateRegistry()
