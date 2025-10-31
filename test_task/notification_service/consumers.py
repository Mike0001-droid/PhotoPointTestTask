from kafka import KafkaConsumer
from .models import DeliveryTracker
from test_task.config import KAFKA_BROKER_URL
from .services import NotificationDeliveryService


class NotificationConsumer:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'notifications',
            bootstrap_servers=KAFKA_BROKER_URL,
            group_id='notification-group',
            enable_auto_commit=False
        )
        self.delivery_service = NotificationDeliveryService()
    
    async def process_message(self, message):
        data = message.value
        try:
            tracker = DeliveryTracker.objects.get(message_id=data['message_id'])
            success = await self.delivery_service.deliver_notification(data, tracker)
            if success:
                tracker.status = 'delivered'
            elif tracker.status == 'pending':
                tracker.status = 'retrying'
            tracker.save()
            self.consumer.commit()
            
        except DeliveryTracker.DoesNotExist:
            print(f"Tracker not found for message {data['message_id']}")
        except Exception as e:
            print(f"Consumer error: {e}")
    
    async def start_consuming(self):
        for message in self.consumer:
            await self.process_message(message)

consumer = NotificationConsumer()