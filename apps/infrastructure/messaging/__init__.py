"""
Messaging Infrastructure

NOTE: Imports are done lazily to avoid Kafka connection attempts during Django build
commands (collectstatic, migrate, etc.) when Kafka is not available.
"""

__all__ = ['KafkaEventProducer', 'EventPublisher', 'publish_event', 'publish_events', 'consume_events']


def __getattr__(name):
    """Lazy import to avoid Kafka connections during build."""
    if name == 'KafkaEventProducer':
        from .kafka_producer import KafkaEventProducer
        return KafkaEventProducer
    elif name == 'consume_events':
        from .kafka_consumer import consume_events
        return consume_events
    elif name == 'EventPublisher':
        from .event_publisher import EventPublisher
        return EventPublisher
    elif name == 'publish_event':
        from .event_publisher import publish_event
        return publish_event
    elif name == 'publish_events':
        from .event_publisher import publish_events
        return publish_events
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
