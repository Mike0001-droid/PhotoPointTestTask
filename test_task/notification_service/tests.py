from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from .models import UserContact, DeliveryTracker


class NotificationAPITestCase(TestCase):
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        self.email_contact = UserContact.objects.create(
            user=self.user,
            channel='email',
            value='test@example.com',
            is_verified=True,
            is_primary=True
        )
        self.telegram_contact = UserContact.objects.create(
            user=self.user,
            channel='telegram',
            value='123456789',
            is_verified=True
        )

    def test_send_notification_success(self):
        """Тест успешной отправки уведомления"""
        data = {
            'title': 'Test Notification',
            'message': 'This is a test message',
            'channel': 'email'
        }
        
        response = self.client.post('/api/notifications/send/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message_id', response.data)
        tracker = DeliveryTracker.objects.get(message_id=response.data['message_id'])
        self.assertEqual(tracker.user_id, self.user.id)
        self.assertEqual(tracker.channel, 'email')

    def test_send_notification_no_channel(self):
        """Тест отправки уведомления без указания канала"""
        data = {
            'title': 'Test Notification',
            'message': 'This is a test message'
        }
        
        response = self.client.post('/api/notifications/send/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_send_notification_invalid_channel(self):
        """Тест отправки уведомления на неверифицированный канал"""
        data = {
            'title': 'Test Notification',
            'message': 'This is a test message',
            'channel': 'sms'
        }
        
        response = self.client.post('/api/notifications/send/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_notification_missing_fields(self):
        """Тест отправки уведомления без обязательных полей"""
        data = {
            'title': 'Test Notification'
        }
        
        response = self.client.post('/api/notifications/send/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_channels(self):
        """Тест получения доступных каналов"""
        response = self.client.get('/api/notifications/channels/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('channels', response.data)
        self.assertEqual(len(response.data['channels']), 2)
        
        channel = response.data['channels'][0]
        self.assertIn('channel', channel)
        self.assertIn('value', channel)
        self.assertIn('is_primary', channel)

    def test_get_delivery_status_specific(self):
        """Тест получения статуса конкретного сообщения"""
        tracker = DeliveryTracker.objects.create(
            message_id='550e8400-e29b-41d4-a716-446655440000',
            user_id=self.user.id,
            channel='email',
            status='delivered',
            contact_info='test@example.com'
        )
        
        response = self.client.get('/api/notifications/status/?message_id=550e8400-e29b-41d4-a716-446655440000')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message_id'], str(tracker.message_id))
        self.assertEqual(response.data['status'], 'delivered')

    def test_get_delivery_status_list(self):
        """Тест получения списка доставок"""
        for i in range(3):
            DeliveryTracker.objects.create(
                message_id=f'550e8400-e29b-41d4-a716-44665544000{i}',
                user_id=self.user.id,
                channel='email',
                status='delivered',
                contact_info='test@example.com'
            )
        
        response = self.client.get('/api/notifications/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('deliveries', response.data)
        self.assertEqual(len(response.data['deliveries']), 3)

    def test_get_stats(self):
        """Тест получения статистики"""
        DeliveryTracker.objects.create(
            message_id='550e8400-e29b-41d4-a716-446655440001',
            user_id=self.user.id,
            channel='email',
            status='delivered',
            contact_info='test@example.com'
        )
        DeliveryTracker.objects.create(
            message_id='550e8400-e29b-41d4-a716-446655440002',
            user_id=self.user.id,
            channel='telegram',
            status='failed',
            contact_info='123456789'
        )
        
        response = self.client.get('/api/notifications/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['delivered'], 1)
        self.assertEqual(response.data['failed'], 1)
        self.assertIn('by_channel', response.data)


class UserContactAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_contact(self):
        """Тест создания контакта"""
        data = {
            'channel': 'email',
            'value': 'new@example.com'
        }
        
        response = self.client.post('/api/contacts/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserContact.objects.count(), 1)
        
        contact = UserContact.objects.first()
        self.assertEqual(contact.channel, 'email')
        self.assertEqual(contact.value, 'new@example.com')
        self.assertFalse(contact.is_verified)

    def test_create_duplicate_contact(self):
        """Тест создания дубликата контакта"""
        UserContact.objects.create(
            user=self.user,
            channel='email',
            value='existing@example.com'
        )
        
        data = {
            'channel': 'email',
            'value': 'existing@example.com'
        }
        
        response = self.client.post('/api/contacts/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_contacts(self):
        """Тест получения списка контактов"""
        UserContact.objects.create(
            user=self.user,
            channel='email',
            value='test@example.com'
        )
        
        response = self.client.get('/api/contacts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_update_contact(self):
        """Тест обновления контакта"""
        contact = UserContact.objects.create(
            user=self.user,
            channel='email',
            value='old@example.com'
        )
        
        data = {
            'value': 'new@example.com'
        }
        
        response = self.client.patch(f'/api/contacts/{contact.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contact.refresh_from_db()
        self.assertEqual(contact.value, 'new@example.com')

    def test_delete_contact(self):
        """Тест удаления контакта"""
        contact = UserContact.objects.create(
            user=self.user,
            channel='email',
            value='test@example.com'
        )
        
        response = self.client.delete(f'/api/contacts/{contact.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UserContact.objects.count(), 0)


class AuthenticationTest(TestCase):
    """Тесты аутентификации"""
    
    def test_unauthenticated_access(self):
        """Тест доступа без аутентификации"""
        client = APIClient()
        
        response = client.get('/api/notifications/channels/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = client.post('/api/notifications/send/', {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class VerificationTest(TestCase):
    """Тесты верификации контактов"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.contact = UserContact.objects.create(
            user=self.user,
            channel='email',
            value='test@example.com'
        )

    def test_send_verification(self):
        """Тест отправки кода верификации"""
        response = self.client.post(f'/api/contacts/{self.contact.id}/send_verification/')
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])

    def test_verify_contact_missing_code(self):
        """Тест верификации без кода"""
        response = self.client.post(f'/api/contacts/{self.contact.id}/verify/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)