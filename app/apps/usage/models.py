import uuid

from fastapi_mongo_base.models import BusinessOwnedEntity
from pymongo import DESCENDING

from .schemas import UsageSchema


class Usage(UsageSchema, BusinessOwnedEntity):
    @classmethod
    async def get_latest_usage(cls, enrollment_id: uuid.UUID) -> "Usage":
        # Fetch the latest usage for the given enrollment_id, sorted by the creation time in descending order
        usages = (
            await cls.find({"enrollment_id": enrollment_id})
            .sort([("created_at", DESCENDING)])
            .to_list(1)  # Limit to the first result
        )

        # Return the first usage if it exists, otherwise return None
        return usages[0] if usages else None
