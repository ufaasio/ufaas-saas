import uuid
from decimal import Decimal

from apps.enrollment.schemas import Bundle
from fastapi_mongo_base.schemas import BusinessOwnedEntitySchema
from pydantic import BaseModel, field_validator
from utils.numtools import decimal_amount


class UsageSchema(BusinessOwnedEntitySchema):
    enrollment_id: uuid.UUID

    asset: str
    amount: Decimal

    variant: str | None = None
    leftover_bundles: list[Bundle] = []

    @field_validator("amount", mode="before")
    def validate_amount(cls, value):
        return decimal_amount(value)


class UsageCreateSchema(BaseModel):
    user_id: uuid.UUID | None = None
    enrollment_id: uuid.UUID | None = None
    asset: str
    amount: Decimal = Decimal(1)
    variant: str | None = None
    meta_data: dict | None = None

    # @model_validator(mode="after")
    # def validate_enrollment_id(cls, item: "UsageCreateSchema"):
    #     if not item.user_id and not item.enrollment_id:
    #         raise ValueError("Either user_id or enrollment_id must be provided")
    #     return item
