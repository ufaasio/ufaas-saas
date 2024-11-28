import logging
import uuid

from fastapi import Query, Request
from fastapi_mongo_base.schemas import PaginatedResponse
from server.config import Settings
from ufaas_fastapi_business.middlewares import AuthorizationException
from ufaas_fastapi_business.routes import AbstractAuthRouter

from .models import Enrollment
from .schemas import (
    EnrollmentCreateSchema,
    EnrollmentDetailSchema,
    EnrollmentSchema,
    EnrollmentUpdateSchema,
)


class EnrollmentRouter(AbstractAuthRouter[Enrollment, EnrollmentDetailSchema]):
    def __init__(self):
        super().__init__(
            model=Enrollment, schema=EnrollmentDetailSchema, user_dependency=None
        )

    def config_schemas(self, schema, **kwargs):
        super().config_schemas(schema, **kwargs)
        self.delete_response_schema = EnrollmentSchema

    def config_routes(self, **kwargs):
        super().config_routes(**kwargs)

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        user_id: uuid.UUID = None,
        asset: str = None,
        variant: str = None,
        is_valid: bool = True,
    ):
        """
        Retrieve a list of enrollments with pagination.

        Args:

            offset (int, optional): The offset value for pagination. Defaults to 0.
            limit (int, optional): The maximum number of items to retrieve. Defaults to 10.

        Returns:

            PaginatedResponse: The paginated response containing the items, offset, limit, and total count.
        """
        auth = await self.get_auth(request)
        if auth.issuer_type == "User" and user_id and user_id != auth.user_id:
            raise AuthorizationException("User cannot list other user's enrollment")

        logging.info(
            f"List items: {auth.user_id}, {auth.business.name}, "
            f"{auth.issuer_type}, {is_valid}, {asset}, {variant}, {is_valid}"
        )

        items, total = await self.model.list_total_combined(
            user_id=auth.user_id,
            business_name=auth.business.name,
            offset=offset,
            limit=limit,
            asset=asset,
            variant=variant,
            is_valid=is_valid,
        )
        items_in_schema = [
            self.list_item_schema(
                **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
            )
            for item in items
        ]
        return PaginatedResponse(
            items=items_in_schema, offset=offset, limit=limit, total=total
        )

    async def retrieve_item(self, request: Request, uid: uuid.UUID):
        """
        Retrieve an enrollment with the given UID.

        Args:

            uid (uuid.UUID): The UID of the item to retrieve.

        Returns:

            Enrolment: The retrieved enrollment with the leftover bundles.
        """
        item: Enrollment = await super().retrieve_item(request, uid)
        return self.retrieve_response_schema(
            **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
        )

    async def create_item(self, request: Request, data: EnrollmentCreateSchema):
        """

        Create an enrollment item.

        Args:

            - user_id: uuid.UUID, owner of the enrollment
            - price: Decimal, price of the enrollment
            - invoice_id: str | None, invoice id of the enrollment if any
            - start_at: datetime, start date of the enrollment, default set now if not provided
            - expire_at: datetime | None, expiration date of the enrollment for the selected bundles, default None
            - status: "active" | "expired", the status of the enrollment, default "active"
            - bundles: list[Bundle], list of bundles that are included in the enrollment. Each bundle should have a asset, quota, and unit.
                asset: str, the asset name (For example, "Storage" in storage service, "Tokens" in LLM API service, ...)
                quota: Decimal, the quota of the asset
                unit: str | None, the unit of the quota (For example, "GB" in storage service, "Tokens" in LLM API service, ...) if any
            - variant: str | None, the variant limitation of the enrollment. For example, "car" category in a classified advertisements service. For normal enrollment, it would be None and it is not to be provided.
            - meta_data: dict | None = None, additional metadata for the enrollment that will be stored as a dictionary.

        Returns:

            dict: The created enrollment item.

        Raises:

            - AuthorizationException: If the user is not authorized to create an enrollment.
        """
        # only business can create enrollment
        auth = await self.get_auth(request)
        if auth.issuer_type == "User":
            # TODO check scopes
            raise AuthorizationException("User cannot create enrollment")
        data: dict = data.model_dump()
        data.pop("user_id", None)
        item = self.model(
            business_name=auth.business.name,
            user_id=auth.user_id if auth.user_id else auth.user.uid,
            **data,
        )
        await item.save()
        return self.schema(
            **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
        )

    async def update_item(
        self, request: Request, uid: uuid.UUID, data: EnrollmentUpdateSchema
    ):
        item: Enrollment = await super().update_item(
            request, uid, data.model_dump(exclude_unset=True)
        )
        return self.retrieve_response_schema(
            **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
        )

    async def delete_item(self, request: Request, uid: uuid.UUID):
        return await super().delete_item(request, uid)


router = EnrollmentRouter().router
