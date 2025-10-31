import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Optional


class NotificationMessage(BaseModel):
    message_id: str
    user_id: int
    title: str
    message: str
    preferred_channel: Optional[str] = None
    created_at: str
    
    @classmethod
    def create(cls, user_id: int, title: str, message: str, **kwargs):
        return cls(
            message_id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            message=message,
            created_at=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def model_dump(self) -> Dict[str, Any]:
        return super().model_dump()