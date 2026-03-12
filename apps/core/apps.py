from __future__ import annotations

import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "GRC Core"

    def ready(self):
        # Import models to ensure they're registered
        from . import models  # noqa: F401

        # Skip Kafka/network operations during build-time commands (no network available).
        # Same guard used by all other FIMS services (WO, Doc Records, IAM).
        if self._is_build_command():
            logger.debug("Skipping Kafka/network operations during build-time command")
            return

        # Guide §2: Load and register workflow templates on startup.
        self._load_workflow_templates()

        # Register permissions with IAM on every startup — FIMS pattern (mirrors WO and Doc Records).
        if not self._is_testing():
            self._register_permissions_on_startup()

        # Register notification templates with Work Orchestration via Kafka — FIMS pattern
        # (mirrors iam-service/apps/core/apps.py and document-records-service/apps/core/apps.py).
        if not self._is_testing():
            self._register_notification_templates()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_build_command(self) -> bool:
        """True when running a command that has no Kafka/network access."""
        if os.environ.get("SKIP_KAFKA_INIT", "").lower() in ("true", "1", "yes"):
            return True
        build_commands = [
            "collectstatic",
            "migrate",
            "makemigrations",
            "showmigrations",
            "check",
            "shell",
            "dbshell",
            "inspectdb",
            "diffsettings",
            "compilemessages",
            "makemessages",
            "createcachetable",
            "squashmigrations",
        ]
        return any(cmd in sys.argv for cmd in build_commands)

    def _is_testing(self) -> bool:
        return "test" in sys.argv or "pytest" in sys.argv

    def _load_workflow_templates(self) -> None:
        """Register workflow templates with Work Orchestration via Kafka.

        Mirrors corporate-service/apps/core/apps.py _register_workflow_templates().
        """
        try:
            from .workflows.registry import workflow_template_registry

            logger.info("Registering GRC workflow templates with Work Orchestration...")

            loaded = workflow_template_registry.load_templates()
            if loaded == 0:
                logger.warning("No workflow templates loaded from YAML file")
                return

            success = workflow_template_registry.publish_templates()

            if success:
                summary = workflow_template_registry.get_registration_summary()
                logger.info(
                    "Successfully registered %d workflow templates "
                    "(workflow_types: %s)",
                    summary['total_templates'],
                    list(summary['templates_by_workflow_type'].keys()),
                )
            else:
                logger.warning("Some workflow templates failed to register (check Kafka connectivity)")

        except Exception as exc:
            logger.error(
                "Could not register workflow templates: %s. "
                "Service will continue without workflow template registration.",
                exc, exc_info=True,
            )

    def _register_permissions_on_startup(self) -> None:
        """Publish GRC permission catalog to IAM via Kafka — mirrors WO and Doc Records pattern."""
        try:
            from .kafka_permission_publisher import permission_publisher
            from .permissions import GrcServicePermissions

            logger.info("Registering GRC permissions with IAM...")
            if permission_publisher.publish_permissions():
                logger.info(
                    "Registered %d permissions for %s",
                    len(GrcServicePermissions.PERMISSIONS),
                    GrcServicePermissions.SERVICE_NAME,
                )
                permission_publisher.publish_service_health()
            else:
                logger.error("Failed to register GRC permissions with IAM.")
        except Exception as exc:  # pragma: no cover — do not block startup
            logger.error("Error registering GRC permissions on startup: %s", exc)

    def _register_notification_templates(self) -> None:
        """Register notification templates with Work Orchestration via Kafka.

        Follows the FIMS pattern from:
          - iam-service/apps/core/apps.py → _register_notification_templates()
          - document-records-service/apps/core/apps.py → _register_notification_templates()

        Reads apps/core/templates/notifications.yaml and publishes each template
        as a `template.registered` event to the `notification-templates` Kafka topic.
        WO's TemplateRegistrationConsumer stores them in NotificationTemplateModel.
        """
        try:
            from .templates.registry import get_template_registry

            logger.info("Registering GRC notification templates with Work Orchestration...")
            registry = get_template_registry()
            registered = registry.register_templates()

            if registered > 0:
                logger.info(f"Successfully registered {registered} notification template(s)")
            else:
                logger.warning("No templates were registered (check template files and Kafka connectivity)")

        except Exception as exc:
            # Don't fail startup if template registration fails
            logger.error(
                "Could not register notification templates: %s. "
                "Service will continue without template registration.",
                exc,
                exc_info=True,
            )
