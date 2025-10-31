from abc import ABC, abstractmethod

class BaseProvider(ABC):
    def __init__(self, config=None):
        self.config = config or {}
    
    @abstractmethod
    async def send(self, to: str, subject: str, message: str, **kwargs):
        pass