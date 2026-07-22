"""Configuration schemas."""

from fastapi_mongo_base.schemas import TenantScopedEntitySchema


class Config(TenantScopedEntitySchema):
    """Configuration schema."""

    wallet_id: str | None = None
    income_wallet_id: str | None = None

    default_borrow_period: int = 0
