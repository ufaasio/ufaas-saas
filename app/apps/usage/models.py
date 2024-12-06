import uuid
from datetime import datetime

from beanie.odm.queries.find import FindMany
from fastapi_mongo_base.models import BusinessOwnedEntity
from pymongo import DESCENDING

from .schemas import UsageSchema


class Usage(UsageSchema, BusinessOwnedEntity):
    class Settings:
        indexes = BusinessOwnedEntity.Settings.indexes

    @classmethod
    async def get_latest_usage(cls, enrollment_id: uuid.UUID) -> "Usage":
        # Fetch the latest usage for the given enrollment_id, sorted by the creation time in descending order
        usages = (
            await cls.find({"consumption.enrollment_id": enrollment_id})
            .sort([("created_at", DESCENDING)])
            .to_list(1)  # Limit to the first result
        )

        # Return the first usage if it exists, otherwise return None
        return usages[0] if usages else None

    @classmethod
    def get_query(
        cls,
        user_id: uuid.UUID = None,
        business_name: str = None,
        is_deleted: bool = False,
        uid: uuid.UUID = None,
        asset: str = None,
        variant: str = None,
        created_at_from: datetime = None,
        created_at_to: datetime = None,
        *args,
        **kwargs
    ) -> FindMany:
        query = super().get_query(
            user_id=user_id,
            business_name=business_name,
            is_deleted=is_deleted,
            uid=uid,
            *args,
            **kwargs
        )
        if asset:
            query = query.filter(cls.asset == asset)
        if variant:
            query = query.filter(cls.variant == variant)
        if created_at_from:
            query = query.filter(cls.created_at >= created_at_from)
        if created_at_to:
            query = query.filter(cls.created_at <= created_at_to)
        return query
