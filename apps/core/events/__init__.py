"""
GRC Domain Events
Base classes and structures for domain events
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any
import uuid


@dataclass
class GRCDomainEvent:
    """Base class for all GRC domain events"""
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = field(default='')
    timestamp: datetime = field(default_factory=datetime.utcnow)
    service_name: str = field(default='grc-service')
    aggregate_id: str = field(default='')
    user_id: str = field(default='')
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'service_name': self.service_name,
            'aggregate_id': self.aggregate_id,
            'user_id': self.user_id,
            'metadata': self.metadata,
            'data': self._get_event_data()
        }
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Override in subclasses to provide event-specific data"""
        return {}
    
    @property
    def topic(self) -> str:
        """Kafka topic for this event - follows FIMS standard"""
        # Topic name matches full event type: fims.{event_type}
        # Examples:
        #   'grc.working.paper.created' -> 'fims.grc.working.paper.created'
        #   'grc.audit.engagement.updated' -> 'fims.grc.audit.engagement.updated'
        
        if self.event_type.startswith('grc.'):
            # Return full event type with fims prefix (no .events suffix!)
            return f"fims.{self.event_type}"
        
        # Fallback: normalize and add prefixes
        return f"fims.grc.{self.event_type.lower().replace('_', '.')}"

