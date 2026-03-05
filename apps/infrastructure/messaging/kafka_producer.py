"""
Kafka Event Producer
Publishes domain events to Kafka
"""

import json
import logging
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
from django.conf import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """Kafka event producer for publishing domain events"""
    
    def __init__(self):
        """Initialize Kafka producer"""
        self.producer = None
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Create Kafka producer instance"""
        try:
            bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(',')
            
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                client_id='grc-service-event-producer',
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                compression_type='gzip',
                acks='all',  # Wait for all replicas
                retries=3,
                retry_backoff_ms=100,
                request_timeout_ms=30000,
                api_version=(0, 10, 1)
            )
            
            logger.info(f"Kafka producer initialized for servers: {bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
    
    def publish(self, topic: str, event_data: Dict[str, Any], key: str = None):
        """
        Publish event to Kafka topic
        
        Args:
            topic: Kafka topic name
            event_data: Event data dictionary (already formatted)
            key: Optional partition key
        """
        if not self.producer:
            logger.warning("Kafka producer not initialized, skipping event publication")
            return False
        
        try:
            # Publish to Kafka (value_serializer handles JSON encoding)
            future = self.producer.send(
                topic=topic,
                key=key,
                value=event_data
            )
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Event published to topic '{topic}': {event_data.get('event_type')} "
                f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka error publishing event to '{topic}': {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to publish event to '{topic}': {e}")
            return False
    
    def flush(self):
        """Flush pending messages"""
        if self.producer:
            self.producer.flush()
    
    def close(self):
        """Close producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")


# Singleton instance
_kafka_producer = None


def get_kafka_producer() -> KafkaEventProducer:
    """Get singleton Kafka producer instance"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaEventProducer()
    return _kafka_producer

