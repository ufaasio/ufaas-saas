"""Configuration models."""

from typing import Self

from fastapi_mongo_base.models import TenantScopedEntity

from .schemas import Config


class Configuration(Config, TenantScopedEntity):
    """Configuration model for tenant settings."""

    @classmethod
    async def get_config(cls, tenant_id: str) -> Self:
        """Get configuration for a tenant."""
        return await cls.find_one({"tenant_id": tenant_id})
