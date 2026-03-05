"""
Event Publisher
High-level interface for publishing domain events
"""

import logging
from typing import List
from apps.core.events import GRCDomainEvent
from .kafka_producer import get_kafka_producer

logger = logging.getLogger(__name__)


class EventPublisher:
    """High-level event publisher"""
    
    def __init__(self):
        """Initialize event publisher"""
        self.kafka_producer = get_kafka_producer()
    
    def publish(self, event: GRCDomainEvent):
        """
        Publish a single domain event
        
        Args:
            event: Domain event to publish
        """
        try:
            # Convert event to dictionary (FIMS-compliant structure)
            event_data = event.to_dict()
            
            # Get topic from event
            topic = event.topic
            
            # Use aggregate_id as partition key for ordering
            key = event.aggregate_id
            
            # Publish to Kafka
            self.kafka_producer.publish(topic, event_data, key)
            
            logger.info(f"Published event: {event.event_type} (ID: {event.event_id})")
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
    
    def publish_batch(self, events: List[GRCDomainEvent]):
        """
        Publish multiple domain events
        
        Args:
            events: List of domain events to publish
        """
        for event in events:
            self.publish(event)
        
        # Flush to ensure all messages are sent
        self.kafka_producer.flush()
    
    def close(self):
        """Close publisher"""
        self.kafka_producer.close()


# Singleton instance
_event_publisher = None


def get_event_publisher() -> EventPublisher:
    """Get singleton event publisher instance"""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = EventPublisher()
    return _event_publisher


def publish_event(event: GRCDomainEvent):
    """
    Convenience function to publish a single event
    
    Args:
        event: Domain event to publish
    """
    publisher = get_event_publisher()
    publisher.publish(event)


def publish_events(events: List[GRCDomainEvent]):
    """
    Convenience function to publish multiple events
    
    Args:
        events: List of domain events to publish
    """
    publisher = get_event_publisher()
    publisher.publish_batch(events)
