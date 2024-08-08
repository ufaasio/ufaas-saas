import uuid
from datetime import datetime

from pydantic import BaseModel


class UsageSchema(BaseModel):
    user_id: uuid.UUID
    business_id: uuid.UUID
    on_item: str
    resource: str
    volume: int
    expired_at: datetime
