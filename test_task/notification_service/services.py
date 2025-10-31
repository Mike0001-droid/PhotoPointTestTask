import asyncio
import datetime
from django.utils import timezone
from django.contrib.auth.models import User
from .models import UserContact, VerificationCode
from .initial_providers import provider_registry


class NotificationDeliveryService:
    def __init__(self):
        self.provider_registry = provider_registry
        self.max_attempts = 3
        self.retry_delays = {
            1: 10,
            2: 30,
        }

    async def deliver_notification(self, message_data, tracker):
        user = User.objects.get(id=message_data['user_id'])
        preferred_channel = message_data.get('preferred_channel')
        
        if tracker.attempt_count > 0:
            return await self._retry_delivery(user, message_data, tracker)
        
        if preferred_channel:
            success = await self._try_preferred_channel(
                user, preferred_channel, message_data, tracker
            )
            if success:
                return True
        return await self._deliver_with_fallback(user, message_data, tracker)
    
    def send_verification_code(self, user_contact):
        code = VerificationCode.generate_code()
        expires_at = timezone.now() + datetime.timedelta(minutes=15)
        
        verification_code = VerificationCode.objects.create(
            user_contact=user_contact,
            code=code,
            expires_at=expires_at
        )
        
        provider = self.provider_registry.get_provider(user_contact.channel)
        if not provider:
            verification_code.delete()
            return False, "Provider not available"
        
        try:
            subject = "Код верификации"
            message = f"""
                Ваш код верификации: {code}
                Код действителен в течение 15 минут.
                Если вы не запрашивали верификацию, проигнорируйте это сообщение.
            """.strip()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                success, error = loop.run_until_complete(
                    provider.send(
                        to=user_contact.value,
                        subject=subject,
                        message=message
                    )
                )
                
                if success:
                    return True, verification_code.id
                else:
                    verification_code.delete()
                    return False, error
                    
            finally:
                loop.close()
                
        except Exception as e:
            verification_code.delete()
            return False, str(e)
    
    def verify_contact(self, user_contact, code):
        try:
            verification_code = VerificationCode.objects.get(
                user_contact=user_contact,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            verification_code.mark_used()
            
            user_contact.is_verified = True
            user_contact.save()
            
            VerificationCode.objects.filter(
                user_contact=user_contact,
                is_used=False
            ).delete()
            return True, "Contact verified successfully"
            
        except VerificationCode.DoesNotExist:
            return False, "Invalid or expired verification code"
    
    async def _retry_delivery(self, user, message_data, tracker):
        if tracker.attempt_count >= self.max_attempts:
            tracker.status = 'failed'
            tracker.last_error = 'Max attempts exceeded'
            tracker.save()
            return False
        
        delay = self.retry_delays.get(tracker.attempt_count, 60)
        await asyncio.sleep(delay)
        
        success = await self._try_deliver_via_channel(
            tracker.channel, tracker.contact_info, message_data, tracker
        )
        
        if not success and tracker.attempt_count == 1:
            return await self._deliver_with_fallback(user, message_data, tracker)
        return success
    
    async def _try_preferred_channel(self, user, preferred_channel, message_data, tracker):
        contact = UserContact.objects.filter(
            user=user,
            channel=preferred_channel,
            is_verified=True
        ).order_by('-is_primary').first()
        
        if not contact:
            return False
        
        return await self._try_deliver_via_channel(
            contact.channel, contact.value, message_data, tracker
        )
    
    async def _deliver_with_fallback(self, user, message_data, tracker):
        contacts = UserContact.objects.filter(
            user=user, 
            is_verified=True
        ).order_by('-is_primary', 'channel')
        
        for contact in contacts:
            if (tracker.attempt_count > 0 and 
                tracker.channel == contact.channel and 
                tracker.contact_info == contact.value):
                continue
                
            success = await self._try_deliver_via_channel(
                contact.channel, contact.value, message_data, tracker
            )
            if success:
                return True
        
        return False
    
    async def _try_deliver_via_channel(self, channel, contact_value, message_data, tracker):
        provider = self.provider_registry.get_provider(channel)
        if not provider:
            return False
        
        tracker.channel = channel
        tracker.contact_info = contact_value
        tracker.attempt_count += 1
        
        try:
            success, error = await provider.send(
                to=contact_value,
                subject=message_data['title'],
                message=message_data['message']
            )
            
            if success:
                tracker.status = 'delivered'
                tracker.delivered_at = timezone.now()
                await tracker.asave()
                return True
            else:
                tracker.status = 'retrying' if tracker.attempt_count < self.max_attempts else 'failed'
                tracker.last_error = error
                await tracker.asave()
                return False
                
        except Exception as e:
            tracker.status = 'retrying' if tracker.attempt_count < self.max_attempts else 'failed'
            tracker.last_error = str(e)
            await tracker.asave()
            return False