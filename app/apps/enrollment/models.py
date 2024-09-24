from fastapi_mongo_base.models import BusinessOwnedEntity

from .schemas import Bundle, EnrollmentSchema


class Enrollment(EnrollmentSchema, BusinessOwnedEntity):

    async def get_leftover_bundles(self) -> list[Bundle]:
        from apps.usage.models import Usage

        latest_usage = await Usage.get_latest_usage(self.id)
        if latest_usage:
            return latest_usage.leftover_bundles
        return self.bundles
