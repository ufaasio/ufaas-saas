"""Usage schemas."""

from decimal import Decimal
from typing import Self

from fastapi_mongo_base.schemas import TenantUserEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, field_validator, model_validator

from apps.enrollment.schemas import Bundle


class UsageConsumption(BaseModel):
    """A consumption record for a usage against an enrollment."""

    enrollment_id: str
    amount: Decimal
    leftover_bundles: list[Bundle] = []

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """Validate and normalize amount."""
        return decimal_amount(value)


class UsageCreateSchema(BaseModel):
    """Schema for creating a usage record."""

    user_id: str | None = None
    enrollment_id: str | None = None
    asset: str
    amount: Decimal = Decimal(1)
    variant: str | None = None
    meta_data: dict | None = None

    @model_validator(mode="after")
    def validate_enrollment_id(self) -> Self:
        """Validate that user_id or enrollment_id is provided."""
        if not self.user_id and not self.enrollment_id:
            msg = "Either user_id or enrollment_id must be provided"
            raise ValueError(msg)
        return self

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """Validate that amount is greater than zero."""
        if value <= 0:
            msg = "Amount must be greater than 0"
            raise ValueError(msg)
        return value


class UsageSchema(TenantUserEntitySchema):
    """Schema representing a usage entity."""

    consumptions: list[UsageConsumption]
    asset: str
    amount: Decimal
    variant: str | None = None

    @classmethod
    def search_exclude_set(cls) -> list[str]:
        """Get fields to exclude from search."""
        return list({*super().search_field_set(), "consumptions"})

    @field_validator("consumptions")
    @classmethod
    def validate_consumptions(cls, value: str) -> str:
        """Validate that consumptions are not empty."""
        if not value:
            msg = "enrollments_id must not be empty"
            raise ValueError(msg)
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """Validate and normalize amount."""
        return decimal_amount(value)
