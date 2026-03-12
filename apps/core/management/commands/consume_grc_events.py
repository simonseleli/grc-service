"""
Django management command to consume events from other FIMS services
"""
import logging
from django.core.management.base import BaseCommand
from apps.infrastructure.messaging.kafka_consumer import GRCKafkaConsumer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start Kafka consumer for GRC service to consume events from other FIMS services'
    
    def handle(self, *args, **options):
        """Run the Kafka consumer"""
        self.stdout.write(
            self.style.SUCCESS("🚀 Starting GRC Kafka Consumer...")
        )
        self.stdout.write(
            self.style.WARNING(
                "ℹ️  Consumer will run indefinitely and automatically reconnect if Kafka becomes unavailable"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "📡 Listening for events from: IAM, Document Records, Work Orchestration"
            )
        )

        consumer = GRCKafkaConsumer()
        try:
            # Start consuming messages
            consumer.consume_messages()
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Consumer stopped by user"))
            consumer.close()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Consumer failed with unrecoverable error: {e}")
            )
            logger.error(f"GRC Kafka consumer failed: {e}", exc_info=True)
            consumer.close()
            raise  # Re-raise to let Docker restart the container
