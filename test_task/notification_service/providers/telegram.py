from aiogram import Bot
from .base import BaseProvider


class TelegramProvider(BaseProvider):
    def __init__(self, config=None):
        super().__init__(config)
        self.bot = Bot(token=config['bot_token'])
    
    async def send(self, to: str, subject: str, message: str, **kwargs):
        try:
            formatted_message = f"*{subject}*\n\n{message}"
            await self.bot.send_message(
                chat_id=to,
                text=formatted_message,
            )
            return True, None
        except Exception as e:
            return False, f"Telegram error: {e}"