import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Literal

from fastapi_mongo_base.schemas import BusinessOwnedEntitySchema
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from utils.numtools import decimal_amount


class Bundle(BaseModel):
    asset: str
    quota: Decimal
    unit: str | None = None

    model_config = ConfigDict(allow_inf_nan=True)

    @field_validator("quota", mode="before")
    def validate_quota(cls, value):
        return decimal_amount(value)


class AcquisitionType(str, Enum):
    trial = "trial"
    # credit = "credit"
    purchased = "purchased"
    gifted = "gifted"
    # deferred = "deferred"
    promotion = "promotion"
    # subscription = "subscription"
    # on_demand = "on_demand"
    borrowed = "borrowed"
    freemium = "freemium"
    postpaid = "postpaid"


class EnrollmentSchema(BusinessOwnedEntitySchema):
    price: Decimal = Decimal(0)
    acquisition_type: AcquisitionType = AcquisitionType.purchased
    invoice_id: str | None = None
    started_at: datetime = Field(default_factory=datetime.now)
    expired_at: datetime | None = None
    status: Literal["active", "expired"] = "active"

    bundles: list[Bundle]
    variant: str | None = None

    due_date: datetime | None = None
    is_paid: bool | None = None

    @field_validator("price", mode="before")
    def validate_price(cls, value):
        return decimal_amount(value)

    @model_validator(mode="after")
    def validate_due_date(cls, data: "EnrollmentSchema"):
        if data.acquisition_type == AcquisitionType.borrowed and not data.due_date:
            raise ValueError("Due date must be provided for borrowed acquisitions")
        if data.acquisition_type == AcquisitionType.borrowed:
            data.is_paid = False if data.is_paid is None else data.is_paid
        return data


class EnrollmentDetailSchema(EnrollmentSchema):
    leftover_bundles: list[Bundle]


class EnrollmentCreateSchema(BaseModel):
    user_id: uuid.UUID
    bundles: list[Bundle]

    price: Decimal = Decimal(0)
    invoice_id: str | None = None
    start_at: datetime = Field(default_factory=datetime.now)
    expire_at: datetime | None = None
    duration: int | None = Field(None, alias="duration_days")
    status: Literal["active", "expired"] = "active"
    acquisition_type: AcquisitionType = AcquisitionType.purchased

    variant: str | None = None
    meta_data: dict | None = None

    due_date: datetime | None = None

    @model_validator(mode="after")
    def validate_duration(cls, data: "EnrollmentCreateSchema"):
        if data.expire_at and data.duration:
            raise ValueError(
                "Only one of expire_at or duration_days should be provided"
            )
        if data.duration:
            data.expire_at = data.start_at + timedelta(days=data.duration)
            # data.duration = None

        return data


class EnrollmentUpdateSchema(BaseModel):
    price: Decimal = Decimal(0)
    invoice_id: str | None = None
    # start_at: datetime = Field(default_factory=datetime.now)
    # expire_at: datetime | None = None
    status: Literal["active", "expired"] = "active"
    acquisition_type: AcquisitionType = AcquisitionType.purchased
    meta_data: dict | None = None

    due_date: datetime | None = None
    is_paid: bool = False


class FreemiumQuota(BaseModel):
    mode: Literal["freemium", "trial"] = "freemium"
    period_days: int = 1
    bundles: list[Bundle] = []
    variant: str | None = None
