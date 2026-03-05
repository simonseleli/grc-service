"""
Kafka Producer helper for the GRC Service.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from django.conf import settings
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class GrcServiceKafkaProducer:
    """Kafka producer wrapper dedicated to the GRC service."""

    def __init__(self) -> None:
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(",")
        self.client_id = getattr(settings, "KAFKA_CONFIG", {}).get("client_id", "grc-service")
        self._producer: Optional[KafkaProducer] = None

    def _get_producer(self) -> Optional[KafkaProducer]:
        """Create the Kafka producer lazily."""

        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    client_id=f"{self.client_id}-producer",
                    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                    key_serializer=lambda key: key.encode("utf-8") if key else None,
                    retries=3,
                    retry_backoff_ms=100,
                    request_timeout_ms=30000,
                    api_version=(0, 10, 1),
                )
                logger.info("Kafka producer initialized for servers %s", self.bootstrap_servers)
            except Exception as exc:  # pragma: no cover - infra issue
                logger.error("Failed to initialize Kafka producer: %s", exc)
                return None

        return self._producer

    def send_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None) -> bool:
        """Publish a message to Kafka."""

        producer = self._get_producer()
        if not producer:
            logger.error("Kafka producer unavailable")
            return False

        try:
            future = producer.send(topic=topic, value=message, key=key)
            metadata = future.get(timeout=10)
            logger.info(
                "Message published to topic=%s partition=%s offset=%s",
                topic,
                metadata.partition,
                metadata.offset,
            )
            return True
        except KafkaError as exc:
            logger.error("Kafka error sending message to %s: %s", topic, exc)
            return False
        except Exception as exc:  # pragma: no cover - unexpected error
            logger.error("Unexpected error sending message to %s: %s", topic, exc)
            return False

    def send_batch_messages(self, topic: str, messages: list, key: Optional[str] = None) -> bool:
        """Publish several messages sequentially."""

        producer = self._get_producer()
        if not producer:
            logger.error("Kafka producer unavailable")
            return False

        try:
            futures = [producer.send(topic=topic, value=payload, key=key) for payload in messages]
            for future in futures:
                future.get(timeout=10)
            logger.info("Published %s messages to topic=%s", len(messages), topic)
            return True
        except KafkaError as exc:
            logger.error("Kafka error sending batch to %s: %s", topic, exc)
            return False
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error sending batch to %s: %s", topic, exc)
            return False

    def close(self) -> None:
        """Close the underlying producer."""

        if self._producer:
            try:
                self._producer.close()
            except Exception as exc:  # pragma: no cover - close failure
                logger.error("Error closing Kafka producer: %s", exc)
            finally:
                self._producer = None


_kafka_producer: Optional[GrcServiceKafkaProducer] = None


def get_kafka_producer() -> GrcServiceKafkaProducer:
    """Return a lazily-instantiated Kafka producer."""

    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = GrcServiceKafkaProducer()
    return _kafka_producer


class _LazyKafkaProducer:
    """Descriptor to defer initialization until first use."""

    def __getattr__(self, name: str):  # pragma: no cover - simple proxy
        return getattr(get_kafka_producer(), name)


kafka_producer = _LazyKafkaProducer()
