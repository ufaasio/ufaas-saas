import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Literal

from fastapi_mongo_base.schemas import BusinessOwnedEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# from .schemas import Bundle, EnrollmentSchema


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
    # freemium = "freemium"
    postpaid = "postpaid"

    @classmethod
    def normal_types(cls):
        return [
            cls.trial,
            cls.purchased,
            cls.gifted,
            cls.promotion,
            cls.borrowed,
            cls.postpaid,
        ]


class EnrollmentCreateSchema(BaseModel):
    user_id: uuid.UUID
    bundles: list[Bundle]

    price: Decimal = Decimal(0)
    invoice_id: str | None = None
    start_at: datetime = Field(default_factory=datetime.now)
    expire_at: datetime | None = None
    duration: int | None = Field(None, description="Duration in days")
    status: Literal["active", "inactive"] = "active"
    acquisition_type: AcquisitionType = AcquisitionType.purchased

    variant: str | None = None
    meta_data: dict | None = None

    due_date: datetime | None = None

    model_config = ConfigDict(allow_inf_nan=True)

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

    @field_validator("price", mode="before")
    def validate_price(cls, value):
        return decimal_amount(value)

    @field_validator("bundles", mode="after")
    def validate_bundles(cls, value: list[Bundle]):
        if not value:
            raise ValueError("Bundles are required")
        return value


class EnrollmentSchema(EnrollmentCreateSchema, BusinessOwnedEntitySchema):
    # price: Decimal = Decimal(0)
    # acquisition_type: AcquisitionType = AcquisitionType.purchased
    # invoice_id: str | None = None
    # start_at: datetime = Field(default_factory=datetime.now)
    # expire_at: datetime | None = None
    # duration: int | None = None
    # status: Literal["active", "inactive"] = "active"

    # bundles: list[Bundle]
    # variant: str | None = None

    # due_date: datetime | None = None
    paid_at: datetime | None = None

    @model_validator(mode="after")
    def validate_duration(cls, data: "EnrollmentSchema"):
        return data

    @model_validator(mode="after")
    def validate_due_date(cls, data: "EnrollmentSchema"):
        if data.acquisition_type == AcquisitionType.borrowed and not data.due_date:
            raise ValueError("Due date must be provided for borrowed acquisitions")
        if data.acquisition_type == AcquisitionType.borrowed:
            data.paid_at = False if data.paid_at is None else data.paid_at
        return data


class EnrollmentDetailSchema(EnrollmentSchema):
    leftover_bundles: list[Bundle]


class EnrollmentUpdateSchema(BaseModel):
    price: Decimal = Decimal(0)
    invoice_id: str | None = None
    # start_at: datetime = Field(default_factory=datetime.now)
    # expire_at: datetime | None = None
    status: Literal["active", "inactive"] = "active"
    acquisition_type: AcquisitionType = AcquisitionType.purchased
    meta_data: dict | None = None

    due_date: datetime | None = None
    paid_at: datetime | None = None


class FreemiumQuota(BaseModel):
    mode: Literal["freemium", "trial"] = "freemium"
    period_days: int = 1
    bundles: list[Bundle] = []
    variant: str | None = None


class QuotasResponseSchema(BaseModel):
    user_id: uuid.UUID | None = None
    asset: str
    quota: Decimal
    unit: str | None = None
    variant: str | None = None
    _quota: Decimal | None = None

    model_config = ConfigDict(allow_inf_nan=True)
