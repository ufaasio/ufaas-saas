import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi_mongo_base.schemas import BusinessOwnedEntitySchema
from pydantic import BaseModel, Field, field_validator

from utils.numtools import decimal_amount
from enum import Enum


class Bundle(BaseModel):
    asset: str
    quota: Decimal

    @field_validator("quota", mode="before")
    def validate_quota(cls, value):
        return decimal_amount(value)


class AcquisitionType(str, Enum):
    trial = "trial"
    credit = "credit"
    purchase = "purchase"
    gifted = "gifted"
    deferred = "deferred"
    promo = "promo"
    subscription = "subscription"
    on_demand = "on_demand"


class EnrollmentSchema(BusinessOwnedEntitySchema):
    price: Decimal
    acquisition_type: AcquisitionType = AcquisitionType.purchase
    invoice_id: str | None = None
    started_at: datetime = Field(default_factory=datetime.now)
    expired_at: datetime | None = None
    status: Literal["active", "expired"] = "active"

    bundles: list[Bundle]
    variant: str | None = None

    @field_validator("price", mode="before")
    def validate_price(cls, value):
        return decimal_amount(value)


class EnrollmentCreateSchema(BaseModel):
    user_id: uuid.UUID
    price: Decimal
    invoice_id: str | None = None
    start_at: datetime = Field(default_factory=datetime.now)
    expire_at: datetime | None = None
    status: Literal["active", "expired"] = "active"

    bundles: list[Bundle] = []
    variant: str | None = None
    meta_data: dict | None = None
