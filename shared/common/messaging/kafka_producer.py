"""
Kafka producer utilities for FIMS microservices
Provides standardized event publishing across all services
"""

import json
import logging
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
from django.conf import settings
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class FIMSKafkaProducer:
    """Kafka producer for FIMS events"""
    
    def __init__(self):
        self.producer = None
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                value_serializer=lambda v: json.dumps(v, default=self._json_serializer).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3,
                retry_backoff_ms=100,
                request_timeout_ms=30000,
                api_version=(2, 0, 2)
            )
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {str(e)}")
            raise
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime and other objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def publish_event(self, topic: str, event_type: str, data: Dict[str, Any], 
                     key: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> bool:
        """
        Publish event to Kafka topic
        
        Args:
            topic: Kafka topic name
            event_type: Type of event
            data: Event data payload
            key: Optional message key
            headers: Optional message headers
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.producer:
                logger.error("Kafka producer not initialized")
                return False
            
            # Create event envelope
            event = {
                'id': str(uuid.uuid4()),
                'type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'service': getattr(settings, 'SERVICE_NAME', 'grc-service'),
                'version': '1.0',
                'data': data
            }
            
            # Prepare headers
            message_headers = []
            if headers:
                for header_key, header_value in headers.items():
                    message_headers.append((header_key, header_value.encode('utf-8')))
            
            # Publish message
            future = self.producer.send(
                topic,
                value=event,
                key=key,
                headers=message_headers
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Event published successfully: topic={topic}, "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}, "
                f"event_type={event_type}"
            )
            
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka error publishing event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error publishing event: {str(e)}")
            return False
    
    def publish_audit_event(self, event_type: str, audit_data: Dict[str, Any], 
                           key: Optional[str] = None) -> bool:
        """
        Publish GRC audit-related event
        
        Args:
            event_type: Type of audit event
            audit_data: Audit event data
            key: Optional message key
            
        Returns:
            True if successful, False otherwise
        """
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            **audit_data
        }
        
        return self.publish_event(
            topic='fims.grc.audit.events',
            event_type=event_type,
            data=data,
            key=key
        )
    
    def publish_working_paper_event(self, event_type: str, working_paper_data: Dict[str, Any],
                                   key: Optional[str] = None) -> bool:
        """
        Publish working paper-related event
        
        Args:
            event_type: Type of working paper event
            working_paper_data: Working paper event data
            key: Optional message key
            
        Returns:
            True if successful, False otherwise
        """
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            **working_paper_data
        }
        
        return self.publish_event(
            topic='fims.grc.working.paper.events',
            event_type=event_type,
            data=data,
            key=key
        )
    
    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")


# Global producer instance
_kafka_producer = None


def get_kafka_producer() -> FIMSKafkaProducer:
    """Get global Kafka producer instance"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = FIMSKafkaProducer()
    return _kafka_producer


def publish_event(topic: str, event_type: str, data: Dict[str, Any], 
                 key: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> bool:
    """
    Convenience function to publish event using global producer
    
    Args:
        topic: Kafka topic name
        event_type: Type of event
        data: Event data payload
        key: Optional message key
        headers: Optional message headers
        
    Returns:
        True if successful, False otherwise
    """
    producer = get_kafka_producer()
    return producer.publish_event(topic, event_type, data, key, headers)
