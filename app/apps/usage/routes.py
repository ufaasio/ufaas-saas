"""Usage API routes."""

from datetime import datetime

from fastapi import Request
from fastapi_mongo_base.errors import NotFoundError
from fastapi_mongo_base.schemas import PaginatedResponse
from fastapi_mongo_base.utils import usso_routes

from apps.enrollment.models import Enrollment

from .models import Usage
from .schemas import UsageConsumption, UsageCreateSchema, UsageSchema
from .services import create_usage


class UsageRouter(usso_routes.AbstractTenantUSSORouter):
    """
    Router for handling usage-related operations.

    Inherits from AbstractAuthRouter class and provides implementation for
    listing, retrieving, and creating usage items.

    Attributes:
        model (Type[Usage]): The model class for usage items.
        schema (Type[UsageSchema]): The schema class for usage items.

    Methods:
        config_schemas: Configures the schemas for the router.
        config_routes: Configures the routes for the router.
        list_items: Retrieves a list of usage items with pagination.
        retrieve_item: Retrieves a specific usage item.
        create_item: Creates a new usage item.
    """

    model = Usage
    schema = UsageSchema

    def config_routes(self) -> None:
        """Configure the routes for the router."""
        super().config_routes(update_route=False, delete_route=False)
        self.router.add_api_route(
            "/{uid:str}/cancel",
            self.cancel_item,
            methods=["POST"],
            response_model=self.retrieve_response_schema,
        )

    async def list_items(
        self,
        request: Request,
        offset: int = 0,
        limit: int = 10,
        user_id: str | None = None,
        asset: str | None = None,
        variant: str | None = None,
        created_at_from: datetime | None = None,
        created_at_to: datetime | None = None,
    ) -> PaginatedResponse[UsageSchema]:
        """
        List usages with pagination.

        Args:
            request: The incoming request.
            offset: The offset for pagination.
            limit: The limit for pagination.
            user_id: Filter by user ID.
            asset: Filter by asset.
            variant: Filter by variant.
            created_at_from: Filter by created_at start range.
            created_at_to: Filter by created_at end range.

        Returns:
            The list of usages.
        """
        return await self._list_items(
            request=request,
            offset=offset,
            limit=limit,
            user_id=user_id,
            asset=asset,
            variant=variant,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
        )
        user = await self.get_user(request)
        user_id = user_id or user.uid
        items, total = await self.model.list_total_combined(
            user_id=user_id,
            tenant_id=user.tenant_id,
            offset=offset,
            limit=limit,
            asset=asset,
            variant=variant,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
        )

        items_in_schema = [self.list_item_schema(**item.model_dump()) for item in items]

        return PaginatedResponse(
            items=items_in_schema, offset=offset, limit=limit, total=total
        )

    async def retrieve_item(self, request: Request, uid: str) -> UsageSchema:
        """Retrieve a usage item by UID."""
        user = await self.get_user(request)
        item = await self.get_item(uid=uid, user_id=None, tenant_id=user.tenant_id)
        await self.authorize(
            action="read",
            user=user,
            filter_data=item.model_dump(),
        )
        return item

    async def create_item(
        self, request: Request, data: UsageCreateSchema, borrow: bool = False
    ) -> Usage:
        """
        Create an usage item and calculate the leftover bundles.

        Args:
            request: The incoming request.
            data: The usage creation data.
            borrow: Whether to allow borrowing.
            enrollment_id: str | None, the enrollment that the usage
            is associated with. If not provided, the usage will be associated to
            the best matching enrollment.
            asset: str, the asset name that the usage is associated with.
            amount: Decimal, the amount of the asset that is used. Defaults to 1.
            variant: str | None, the variant of the asset that is used
            if the usage could be passed in variant limitation. In normal use cases,
            this does not need to be provided.
            meta_data: dict | None, the metadata of the usage.

        Note:
            If not provided, the usage will be associated with
            the best matching enrollment. The best matching is determined
            by the following order:
            1. The enrollment that has the same enrollment_id.
            2. The enrollment that has the same asset and variant.
            3. The enrollment expired the earliest.

            The system will use the enrollments one by one until the amount is used up.

        Returns:
            list[dict]: The list of created usage items. Each related to an enrollment.

        Raises:
            AuthorizationException:
                If the user is not authorized to create an enrollment.
        """
        # only business can create usage
        user = await self.get_user(request)
        user_id = data.user_id or user.uid

        item = await create_usage(
            tenant_id=user.tenant_id,
            user_id=user_id,
            asset=data.asset,
            amount=data.amount,
            variant=data.variant,
            enrollment_id=data.enrollment_id,
            meta_data=data.meta_data,
            borrow=borrow,
        )
        await item.save()
        return item

    async def cancel_item(self, request: Request, uid: str) -> Usage:
        """
        Cancel a usage item.

        Args:
            request: The incoming request.
            uid: The uid of the usage.

        Returns:
            The canceled usage.
        """
        user = await self.get_user(request)

        item: Usage = await self.model.get_item(
            uid, user_id=None, tenant_id=user.tenant_id
        )

        if not item:
            raise NotFoundError(
                error_code="usage_not_found",
                detail=f"{self.model.__name__.capitalize()} not found",
                message={
                    "en": f"{self.model.__name__.capitalize()} not found",
                    "fa": f"{self.model.__name__.capitalize()} یافت نشد",
                },
            )

        cancel_consumptions = []
        for consumption in item.consumptions:
            enrollment: Enrollment = await Enrollment.get_item(
                consumption.enrollment_id,
                user_id=None,
                tenant_id=user.tenant_id,
            )
            leftover_bundles = await enrollment.get_leftover_bundles()
            for bundle in leftover_bundles:
                if bundle.asset == item.asset:
                    bundle.quota += consumption.amount
            new_consumption = UsageConsumption(
                enrollment_id=enrollment.uid,
                amount=-consumption.amount,
                leftover_bundles=leftover_bundles,
                # TODO check if the leftover bundles are correct
            )
            cancel_consumptions.append(new_consumption)

        cancel_item = Usage(
            tenant_id=user.tenant_id,
            user_id=item.user_id,
            asset=item.asset,
            amount=item.amount,
            variant=item.variant,
            meta_data=item.meta_data,
            consumptions=cancel_consumptions,
        )
        await cancel_item.save()
        return cancel_item


router = UsageRouter().router
