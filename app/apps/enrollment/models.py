"""Enrollment models."""

from datetime import datetime
from decimal import Decimal
from typing import Self

from beanie.odm.queries.find import FindMany
from fastapi_mongo_base.models import TenantUserEntity

from .schemas import AcquisitionType, Bundle, EnrollmentSchema


class Enrollment(EnrollmentSchema, TenantUserEntity):
    """Enrollment model."""

    @classmethod
    def get_query(
        cls,
        user_id: str | None = None,
        tenant_id: str | None = None,
        is_deleted: bool = False,
        uid: str | None = None,
        asset: str | None = None,
        variant: str | None = None,
        is_valid: bool = True,
        **kwargs: object,
    ) -> FindMany:
        """Get query for enrollments."""
        if is_valid and not uid:
            return cls.find(
                cls.get_active_enrollments_base_query(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    asset=asset,
                    variant=variant,
                    is_deleted=is_deleted,
                    **kwargs,
                )
            )

        query = super().get_query(
            user_id=user_id,
            tenant_id=tenant_id,
            is_deleted=is_deleted,
            uid=uid,
            **kwargs,
        )
        if asset:
            query.find({"bundles.asset": asset})

        return query

    async def get_leftover_bundles(self) -> list[Bundle]:
        """Get leftover bundles after usage."""
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
        tenant_id: str,
        user_id: str,
        asset: str | None = None,
        variant: str | None = None,
        enrollment_id: str | None = None,
        is_deleted: bool = False,
        **kwargs: object,
    ) -> dict:
        """Get base query for active enrollments."""
        now = datetime.now()

        base_query = {
            "tenant_id": tenant_id,
            "is_deleted": is_deleted,
            "start_at": {"$lt": now},
            "status": "active",
            "$and": [
                {
                    "$or": [
                        {"acquisition_type": {"$in": AcquisitionType.normal_types()}},
                        {
                            "acquisition_type": "borrowed",
                            "due_date": {"$gt": now},
                            "paid_at": {"$ne": None},
                        },
                    ]
                },
                {
                    "$or": [
                        {"expire_at": {"$gt": now}},
                        {"expire_at": None},
                    ]
                },
                {
                    "$or": [
                        {"variant": None},
                        {"variant": variant},
                    ]
                },
            ],
        }
        if enrollment_id:
            base_query["uid"] = enrollment_id

        if user_id:
            base_query["user_id"] = user_id

        if asset:
            base_query["bundles.asset"] = asset

        return base_query

    @classmethod
    async def overdue_enrollments(cls, tenant_id: str, user_id: str) -> list[Self]:
        """Get overdue borrowed enrollments."""
        now = datetime.now()
        return await cls.find({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "acquisition_type": "borrowed",
            "due_date": {"$lt": now},
            "paid_at": None,
        }).to_list()

    @classmethod
    async def quotas(
        cls,
        tenant_id: str,
        user_id: str,
        asset: str,
        variant: str | None = None,
    ) -> Decimal:
        """Retrieve the total quotas of an asset for a user."""
        base_query = cls.get_active_enrollments_base_query(
            tenant_id=tenant_id,
            user_id=user_id,
            asset=asset,
            variant=variant,
        )

        enrollments = await cls.find(base_query).to_list()
        quota = 0
        for enrollment in enrollments:
            quota += sum(
                bundle.quota
                for bundle in await enrollment.get_leftover_bundles()
                if bundle.asset == asset
            )
        return quota
