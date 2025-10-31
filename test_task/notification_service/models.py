import uuid
import random
from django.db import models
from django.contrib.auth.models import User



class NotificationChannel(models.TextChoices):
    EMAIL = 'email', 'Email'
    SMS = 'sms', 'SMS'
    TELEGRAM = 'telegram', 'Telegram'


class UserContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    channel = models.CharField("Место получения сообщения", max_length=20, choices=NotificationChannel.choices)
    value = models.CharField("Значение, используемое для передачи", max_length=255)
    is_primary = models.BooleanField("Приоритет доставки", default=False)
    is_verified = models.BooleanField("Верификация", default=False)
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        unique_together = ['user', 'channel', 'value']


class DeliveryTracker(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('retrying', 'Retrying'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_id = models.UUIDField("ID сообщения из Kafka", unique=True)
    user_id = models.IntegerField("ID пользователя")
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    contact_info = models.CharField("Куда отправлено", max_length=255)
    attempt_count = models.IntegerField("Количество попыток", default=0)
    last_error = models.TextField("Последняя ошибка", blank=True, null=True)
    created_at = models.DateTimeField("Дата создания трекера", auto_now_add=True)
    delivered_at = models.DateTimeField("Дата доставки сообщения", null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def get_channel_display(self):
        return dict(NotificationChannel.choices).get(self.channel, self.channel)


class VerificationCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_contact = models.ForeignKey(UserContact, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField("Код", max_length=6)
    is_used = models.BooleanField("Используется ли", default=False)
    expires_at = models.DateTimeField("Когда закончится")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user_contact', 'is_used', 'expires_at']),
        ]
    
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()
    
    def mark_used(self):
        self.is_used = True
        self.save()
    
    @classmethod
    def generate_code(cls):
        return str(random.randint(100000, 999999))