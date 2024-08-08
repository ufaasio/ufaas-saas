import uuid
from datetime import datetime

from pydantic import BaseModel


class EnrollmentSchema(BaseModel):
    invoice_id: uuid.UUID
    started_at: datetime
    expired_at: datetime
    plan: dict
    on_item: str
    resources: dict
    remain_resources: dict
