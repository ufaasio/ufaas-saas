"""Usage models."""

from typing import Self

from fastapi_mongo_base.models import TenantUserEntity
from pymongo import DESCENDING

from .schemas import UsageSchema


class Usage(UsageSchema, TenantUserEntity):
    """Usage model representing resource consumption."""

    @classmethod
    async def get_latest_usage(cls, enrollment_id: str) -> Self:
        """Get the latest usage for a given enrollment ID."""
        usages = (
            await cls
            .find({"consumptions.enrollment_id": enrollment_id})
            .sort([("created_at", DESCENDING)])
            .to_list(1)
        )
        return usages[0] if usages else None
