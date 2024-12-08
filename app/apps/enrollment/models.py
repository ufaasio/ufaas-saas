import uuid
from datetime import datetime

from beanie.odm.queries.find import FindMany
from bson import UUID_SUBTYPE, Binary
from fastapi_mongo_base.models import BusinessOwnedEntity

from .schemas import AcquisitionType, Bundle, EnrollmentSchema


class Enrollment(EnrollmentSchema, BusinessOwnedEntity):
    class Settings:
        indexes = BusinessOwnedEntity.Settings.indexes

    @classmethod
    def get_query(
        cls,
        user_id: uuid.UUID = None,
        business_name: str = None,
        is_deleted: bool = False,
        uid: uuid.UUID = None,
        asset: str = None,
        variant: str = None,
        is_valid: bool = True,
        created_at_from: datetime = None,
        created_at_to: datetime = None,
        start_at_from: datetime = None,
        start_at_to: datetime = None,
        expire_at_from: datetime = None,
        expire_at_to: datetime = None,
        due_date_from: datetime = None,
        due_date_to: datetime = None,
        paid_at_from: datetime = None,
        paid_at_to: datetime = None,
        *args,
        **kwargs,
    ) -> FindMany:
        if is_valid and not uid:
            return cls.find(
                cls.get_active_enrollments_base_query(
                    business_name=business_name,
                    user_id=user_id,
                    asset=asset,
                    variant=variant,
                    is_deleted=is_deleted,
                    *args,
                    **kwargs,
                )
            )

        query = super().get_query(
            user_id=user_id,
            business_name=business_name,
            is_deleted=is_deleted,
            uid=uid,
            *args,
            **kwargs,
        )
        if asset:
            query = query.filter(cls.bundles.asset == asset)
        if variant:
            query = query.filter(cls.variant == variant)
        if created_at_from:
            query = query.filter(cls.created_at >= created_at_from)
        if created_at_to:
            query = query.filter(cls.created_at <= created_at_to)
        if start_at_from:
            query = query.filter(cls.start_at >= start_at_from)
        if start_at_to:
            query = query.filter(cls.start_at <= start_at_to)
        if expire_at_from:
            query = query.filter(cls.expire_at >= expire_at_from)
        if expire_at_to:
            query = query.filter(cls.expire_at <= expire_at_to)
        if due_date_from:
            query = query.filter(cls.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(cls.due_date <= due_date_to)
        if paid_at_from:
            query = query.filter(cls.paid_at >= paid_at_from)
        if paid_at_to:
            query = query.filter(cls.paid_at <= paid_at_to)
        return query

    async def get_leftover_bundles(self) -> list[Bundle]:
        from apps.usage.models import Usage

        latest_usage = await Usage.get_latest_usage(self.uid)
        if latest_usage:
            for consumption in latest_usage.consumptions:
                if consumption.enrollment_id == self.uid:
                    return consumption.leftover_bundles
        return self.bundles

    @classmethod
    def get_active_enrollments_base_query(
        cls,
        business_name: str,
        user_id: uuid.UUID,
        asset: str = None,
        variant: str = None,
        enrollment_id: uuid.UUID = None,
        is_deleted: bool = False,
        **kwargs,
    ) -> list[dict]:
        now = datetime.now()

        base_query = [
            {"business_name": business_name},
            {"is_deleted": is_deleted},
            {"start_at": {"$lt": now}},
            {"status": "active"},
            {
                "$or": [
                    {
                        "acquisition_type": {"$in": AcquisitionType.normal_types()},
                    },
                    {
                        "acquisition_type": "borrowed",
                        "due_date": {"$gt": now},
                        "paid_at": {"$ne": None},
                    },
                ]
            },
            {
                "$or": [
                    {"expire_at": {"$gt": now}},  # expire_at after now
                    {"expire_at": None},  # or expire_at is None
                ]
            },
            # {
            #     "$or": [
            #         {"variant": None},  # variant is None
            #         {"variant": variant},  # or variant matches given variant
            #     ]
            # },
        ]
        if enrollment_id:
            base_query.append({"uid": enrollment_id})

        if user_id:
            user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            user_id = Binary.from_uuid(user_id, UUID_SUBTYPE)
            base_query.append({"user_id": user_id})

        if asset:
            base_query.append({"bundles.asset": asset})

        return base_query

    @classmethod
    async def overdue_enrollments(cls, user_id: uuid.UUID) -> list["Enrollment"]:
        now = datetime.now()
        return await cls.find(
            {
                "user_id": user_id,
                "acquisition_type": "borrowed",
                # "status": "active",
                "due_date": {"$lt": now},
                "paid_at": None,
            }
        ).to_list()
        return bool(overdue_enrollments)
