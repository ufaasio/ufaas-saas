"""Enrollment schemas."""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from fastapi_mongo_base.schemas import TenantUserEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Bundle(BaseModel):
    """A bundle of an asset with a quota."""

    asset: str
    quota: Decimal
    order: Literal[0, 1, 2] = 1
    unit: str | None = None
    meta_data: dict | None = None

    model_config = ConfigDict(allow_inf_nan=True)

    @field_validator("quota", mode="before")
    @classmethod
    def validate_quota(cls, value: Decimal) -> Decimal:
        """Validate and normalize quota amount."""
        return decimal_amount(value)


class AcquisitionType(StrEnum):
    """Acquisition type for enrollments."""

    trial = "trial"
    purchased = "purchased"
    gifted = "gifted"
    promotion = "promotion"
    borrowed = "borrowed"
    postpaid = "postpaid"

    @classmethod
    def normal_types(cls) -> list[str]:
        """Get normal (non-borrowed) acquisition types."""
        return [
            cls.trial,
            cls.purchased,
            cls.gifted,
            cls.promotion,
            cls.postpaid,
        ]


class EnrollmentCreateSchema(BaseModel):
    """Schema for creating an enrollment."""

    user_id: str
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
    def validate_duration(self) -> Self:
        """Validate that only one of expire_at or duration is provided."""
        if self.expire_at and self.duration:
            msg = "Only one of expire_at or duration_days should be provided"
            raise ValueError(msg)
        if self.duration:
            self.expire_at = self.start_at + timedelta(days=self.duration)
        return self

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        """Validate and normalize price amount."""
        return decimal_amount(value)

    @field_validator("bundles", mode="after")
    @classmethod
    def validate_bundles(cls, value: list[Bundle]) -> list[Bundle]:
        """Validate that bundles are not empty."""
        if not value:
            msg = "Bundles are required"
            raise ValueError(msg)
        return value


class EnrollmentSchema(EnrollmentCreateSchema, TenantUserEntitySchema):
    """Schema representing an enrollment entity."""

    paid_at: datetime | None = None

    @model_validator(mode="after")
    def validate_duration(self) -> Self:
        """Validate enrollment duration."""
        return self

    @model_validator(mode="after")
    def validate_due_date(self) -> Self:
        """Validate due date for borrowed acquisitions."""
        if self.acquisition_type == AcquisitionType.borrowed and not self.due_date:
            msg = "Due date must be provided for borrowed acquisitions"
            raise ValueError(msg)
        if self.acquisition_type == AcquisitionType.borrowed:
            self.paid_at = False if self.paid_at is None else self.paid_at
        return self

    def summary(self, tabs: int = 0) -> str:
        """Get a text summary of the enrollment."""
        now = datetime.now()
        exp = (self.expire_at - now).seconds if self.expire_at else "inf"
        s = f"{'\t' * tabs}{self.uid}: ({self.variant}) {exp} ["
        for b in self.bundles:
            s += f"({b.asset}: {b.quota}) "
        s += "]\n"
        return s

    @classmethod
    def summaries(cls, enrollments: list[Self], tabs: int = 0) -> str:
        """Get text summaries for a list of enrollments."""
        s = ""
        for e in enrollments:
            s += e.summary(tabs + 1)
        return s


class EnrollmentDetailSchema(EnrollmentSchema):
    """Schema for enrollment detail with leftover bundles."""

    leftover_bundles: list[Bundle]


class EnrollmentUpdateSchema(BaseModel):
    """Schema for updating an enrollment."""

    price: Decimal = Decimal(0)
    invoice_id: str | None = None
    status: Literal["active", "inactive"] = "active"
    acquisition_type: AcquisitionType = AcquisitionType.purchased
    meta_data: dict | None = None

    due_date: datetime | None = None
    paid_at: datetime | None = None


class FreemiumQuota(BaseModel):
    """Freemium quota configuration."""

    mode: Literal["freemium", "trial"] = "freemium"
    period_days: int = 1
    bundles: list[Bundle] = []
    variant: str | None = None


class QuotasResponseSchema(BaseModel):
    """Response schema for quota queries."""

    user_id: str | None = None
    asset: str
    quota: Decimal
    unit: str | None = None
    variant: str | None = None
    _quota: Decimal | None = None

    model_config = ConfigDict(allow_inf_nan=True)
