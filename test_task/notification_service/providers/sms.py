from .base import BaseProvider


class SMSProvider(BaseProvider):
    async def send(self, to: str, subject: str, message: str, **kwargs):
        try:
            #Имитация отправки смс
            full_message = f"{subject}: {message}"
            print(f"SMS to {to}: {full_message}")
            return True, None
        except Exception as e:
            return False, f"SMS error: {e}"