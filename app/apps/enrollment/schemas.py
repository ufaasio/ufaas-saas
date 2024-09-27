import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from fastapi_mongo_base.schemas import BusinessOwnedEntitySchema
from pydantic import BaseModel, Field, field_validator

from utils.numtools import decimal_amount


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
    borrowed = "borrowed"
    freemium = "freemium"


class EnrollmentSchema(BusinessOwnedEntitySchema):
    price: Decimal = Decimal(0)
    acquisition_type: AcquisitionType = AcquisitionType.purchase
    invoice_id: str | None = None
    started_at: datetime = Field(default_factory=datetime.now)
    expired_at: datetime | None = None
    status: Literal["active", "expired"] = "active"

    bundles: list[Bundle]
    variant: str | None = None

    due_date: datetime | None = None
    is_paid: bool = False

    @field_validator("price", mode="before")
    def validate_price(cls, value):
        return decimal_amount(value)


class EnrollmentDetailSchema(EnrollmentSchema):
    leftover_bundles: list[Bundle]


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


class FreemiumQuota(BaseModel):
    mode: Literal["freemium", "trial"] = "freemium"
    period_days: int = 1
    bundles: list[Bundle] = []
    variant: str | None = None
