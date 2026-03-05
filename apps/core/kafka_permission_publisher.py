"""
Kafka Permission Publisher for the GRC Service.
"""
from __future__ import annotations

import logging
from datetime import datetime

from .kafka_producer import kafka_producer
from .permissions import GrcServicePermissions

logger = logging.getLogger(__name__)


class PermissionPublisher:
    """Publishes the service permission catalog and health data to IAM via Kafka."""

    TOPIC_NAME = "service.permission.registry"

    def __init__(self) -> None:
        self.topic = self.TOPIC_NAME
        self.permissions = GrcServicePermissions

    def publish_permissions(self) -> bool:
        """Send the full permission catalog to IAM."""

        try:
            registration = self.permissions.get_permission_registration_data()
            registration["registration_timestamp"] = datetime.utcnow().isoformat()

            message = {
                "event_type": "service_permission_registration",
                "event_version": "1.0",
                "timestamp": datetime.utcnow().isoformat(),
                "source_service": self.permissions.SERVICE_NAME,
                "permission_hash": registration.get("permission_hash"),
                "data": registration,
            }

            success = kafka_producer.send_message(
                topic=self.topic,
                message=message,
                key=self.permissions.SERVICE_NAME,
            )

            if success:
                logger.info(
                    "Published %s permissions for %s",
                    len(self.permissions.PERMISSIONS),
                    self.permissions.SERVICE_NAME,
                )
                return True

            logger.error("Failed to publish permissions for %s", self.permissions.SERVICE_NAME)
            return False
        except Exception as exc:  # pragma: no cover - operational path
            logger.error("Error publishing permissions: %s", exc, exc_info=True)
            return False

    def publish_permission_update(self, permission_code: str, action: str = "updated") -> bool:
        """Publish a targeted permission change event."""

        try:
            permission = self.permissions.get_permission_by_code(permission_code)
            if not permission:
                logger.error("Permission not found: %s", permission_code)
                return False

            message = {
                "event_type": "service_permission_update",
                "event_version": "1.0",
                "timestamp": datetime.utcnow().isoformat(),
                "source_service": self.permissions.SERVICE_NAME,
                "action": action,
                "data": {
                    "service_name": self.permissions.SERVICE_NAME,
                    "permission_code": permission_code,
                    "permission": permission,
                    "action": action,
                    "permission_hash": self.permissions.get_permission_hash(),
                },
            }

            success = kafka_producer.send_message(
                topic=self.topic,
                message=message,
                key=f"{self.permissions.SERVICE_NAME}:{permission_code}",
            )

            if success:
                logger.info("Published %s for permission %s", action, permission_code)
                return True

            logger.error("Failed to publish %s for permission %s", action, permission_code)
            return False
        except Exception as exc:  # pragma: no cover - operational path
            logger.error("Error publishing permission update: %s", exc, exc_info=True)
            return False

    def publish_service_health(self) -> bool:
        """Emit a lightweight health message so IAM can track producers."""

        try:
            message = {
                "event_type": "service_health_check",
                "event_version": "1.0",
                "timestamp": datetime.utcnow().isoformat(),
                "source_service": self.permissions.SERVICE_NAME,
                "data": {
                    "service_name": self.permissions.SERVICE_NAME,
                    "service_version": self.permissions.SERVICE_VERSION,
                    "status": "healthy",
                    "permissions_count": len(self.permissions.PERMISSIONS),
                    "last_registration": datetime.utcnow().isoformat(),
                },
            }

            success = kafka_producer.send_message(
                topic=self.topic,
                message=message,
                key=f"{self.permissions.SERVICE_NAME}:health",
            )

            if success:
                logger.info("Published service health for %s", self.permissions.SERVICE_NAME)
                return True

            logger.error("Failed to publish service health for %s", self.permissions.SERVICE_NAME)
            return False
        except Exception as exc:  # pragma: no cover - operational path
            logger.error("Error publishing service health: %s", exc, exc_info=True)
            return False


permission_publisher = PermissionPublisher()
