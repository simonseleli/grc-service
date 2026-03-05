"""
Messaging utilities for Kafka integration
"""

from .kafka_producer import (
    FIMSKafkaProducer,
    get_kafka_producer,
    publish_event
)

__all__ = [
    'FIMSKafkaProducer',
    'get_kafka_producer',
    'publish_event',
]
