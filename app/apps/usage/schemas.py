import uuid
from decimal import Decimal

from apps.enrollment.schemas import Bundle
from fastapi_mongo_base.schemas import BusinessOwnedEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, field_validator, model_validator


class UsageConsumption(BaseModel):
    enrollment_id: uuid.UUID
    amount: Decimal
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

    @model_validator(mode="after")
    def validate_enrollment_id(cls, item: "UsageCreateSchema"):
        if not item.user_id and not item.enrollment_id:
            raise ValueError("Either user_id or enrollment_id must be provided")
        return item

    @field_validator("amount", mode="after")
    def validate_amount(cls, value: Decimal):
        if value <= 0:
            raise ValueError("Amount must be greater than 0")
        return value


class UsageSchema(BusinessOwnedEntitySchema):
    # enrollment_id: uuid.UUID
    # asset: str
    # amount: Decimal

    consumptions: list[UsageConsumption]
    asset: str
    amount: Decimal
    variant: str | None = None

    # @classmethod
    # def search_field_set(cls) -> list[str]:
    #     return list(set(super().search_field_set() + ["asset", "variant"]))

    @classmethod
    def search_exclude_set(cls) -> list[str]:
        return list(set(super().search_field_set() + ["consumptions"]))

    @field_validator("consumptions")
    def validate_enrollments_id(cls, value):
        if not value:
            raise ValueError("enrollments_id must not be empty")
        return value

    @field_validator("amount", mode="before")
    def validate_amount(cls, value):
        return decimal_amount(value)
