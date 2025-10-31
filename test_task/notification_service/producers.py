import json
from kafka import KafkaProducer
from .models import DeliveryTracker
from .schemas import NotificationMessage
from test_task.config import KAFKA_BROKER_URL


class NotificationProducer:
    def __init__(self):
        self.producer = None

    def _get_producer(self):
        if self.producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER_URL,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        return self.producer
    
    def send_notification(self, user_id: int, title: str, message: str, **kwargs):
        kafka_message = NotificationMessage.create(user_id, title, message, **kwargs)
        try:
            self.producer.send('notifications', kafka_message.model_dump())
            
            DeliveryTracker.objects.create(
                message_id=kafka_message.message_id,
                user_id=user_id,
                status='pending'
            )
            
            return kafka_message.message_id
        except Exception as e:
            print(f"Kafka error: {e}")
            return None

notification_producer = NotificationProducer()