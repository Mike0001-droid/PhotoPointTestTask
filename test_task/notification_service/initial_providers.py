from .providers.registry import ProviderRegistry
from .providers.email import EmailProvider
from .providers.telegram import TelegramProvider
from .providers.sms import SMSProvider
from test_task.config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, BOT_TOKEN


provider_registry = ProviderRegistry()

provider_registry.register('email', EmailProvider({
    'smtp_host': SMTP_HOST,
    'smtp_port': SMTP_PORT,
    'smtp_username': SMTP_USERNAME,
    'smtp_password': SMTP_PASSWORD,
    'from_email': 'noreply@example.com',
}))

provider_registry.register('telegram', TelegramProvider({
    'bot_token': BOT_TOKEN,
}))

provider_registry.register('sms', SMSProvider({
    'api_key': 'your-sms-api-key',
    'sender_id': 'NotifyService',
}))