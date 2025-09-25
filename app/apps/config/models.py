from typing import Self

from fastapi_mongo_base.models import TenantScopedEntity

from .schemas import Config


class Configuration(Config, TenantScopedEntity):
    @classmethod
    async def get_config(cls, tenant_id: str) -> Self:
        return await cls.find_one({"tenant_id": tenant_id})
