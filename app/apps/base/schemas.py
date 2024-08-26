import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class CoreEntitySchema(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_deleted: bool = False
    meta_info: dict[str, Any] | None = None


class BaseEntitySchema(CoreEntitySchema):
    uid: uuid.UUID = Field(default_factory=uuid.uuid4, index=True, unique=True)


class OwnedEntitySchema(BaseEntitySchema):
    user_id: uuid.UUID


class BusinessEntitySchema(BaseEntitySchema):
    business_name: str


class BusinessOwnedEntitySchema(OwnedEntitySchema, BusinessEntitySchema):
    pass


T = TypeVar("T", bound=BaseEntitySchema)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
