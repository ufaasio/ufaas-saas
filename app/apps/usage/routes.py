import uuid
from datetime import datetime

from apps.enrollment.models import Enrollment
from fastapi import Request
from fastapi_mongo_base.schemas import PaginatedResponse
from ufaas_fastapi_business.middlewares import AuthorizationException
from ufaas_fastapi_business.routes import AbstractAuthRouter

from .models import Usage
from .schemas import UsageConsumption, UsageCreateSchema, UsageSchema
from .services import create_usage


class UsageRouter(AbstractAuthRouter[Usage, UsageSchema]):
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

    def __init__(self):
        super().__init__(model=Usage, schema=UsageSchema, user_dependency=None)

    def config_schemas(self, schema, **kwargs):
        """
        Configures the schemas for the router.

        Args:
            schema: The schema class to be configured.
            **kwargs: Additional keyword arguments.

        Returns:
            None
        """
        super().config_schemas(schema)
        # self.create_response_schema = list[self.schema]

    def config_routes(self):
        """
        Configures the routes for the router.

        Returns:
            None
        """
        self.router.add_api_route(
            "/",
            self.list_items,
            methods=["GET"],
            response_model=self.list_response_schema,
            status_code=200,
        )
        self.router.add_api_route(
            "/{uid:uuid}",
            self.retrieve_item,
            methods=["GET"],
            response_model=self.retrieve_response_schema,
            status_code=200,
        )
        self.router.add_api_route(
            "/",
            self.create_item,
            methods=["POST"],
            response_model=self.create_response_schema,
            status_code=201,
        )
        self.router.add_api_route(
            "/{uid:uuid}/cancel",
            self.cancel_item,
            methods=["POST"],
            response_model=self.retrieve_response_schema,
        )

    async def list_items(
        self,
        request: Request,
        offset: int = 0,
        limit: int = 10,
        user_id: uuid.UUID = None,
        asset: str = None,
        variant: str = None,
        created_at_from: datetime = None,
        created_at_to: datetime = None,
    ):
        """
        List usages with pagination.

        Args:

            offset (int, optional): The offset for pagination. Defaults to 0.
            limit (int, optional): The limit for pagination. Defaults to 10.

        Returns:

            The list of usages.
        """
        auth = await self.get_auth(request)
        items, total = await self.model.list_total_combined(
            user_id=auth.user_id,
            business_name=auth.business.name,
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

    async def retrieve_item(self, request: Request, uid: uuid.UUID):
        """
        Retrieve a usage.

        Args:

            uid (uuid.UUID): The uid of the usage.

        Returns:

            The usage.
        """
        return await super().retrieve_item(request, uid)

    async def create_item(
        self, request: Request, data: UsageCreateSchema, borrow: bool = False
    ):
        """
        Create an usage item and calculate the leftover bundles.

        Args:

            enrollment_id: uuid.UUID | None, the enrollment that the usage is associated with. If not provided, the usage will be associated to the best matching enrollment.
            asset: str, the asset name that the usage is associated with.
            amount: Decimal, the amount of the asset that is used. Defaults to 1.
            variant: str | None, the variant of the asset that is used if the usage could be passed in variant limitation. In normal use cases, this does not need to be provided.
            meta_data: dict | None, the metadata of the usage.

        Note:

            If not provided, the usage will be associated with the best matching enrollment. The best matching is determined by the following order:
            1. The enrollment that has the same enrollment_id.
            2. The enrollment that has the same asset and variant.
            3. The enrollment expired the earliest.

            The system will use the enrollments one by one until the amount is used up.

        Returns:

            list[dict]: The list of created usage items. Each related to an enrollment.

        Raises:
            AuthorizationException: If the user is not authorized to create an enrollment.
        """
        # only business can create usage
        auth = await self.get_auth(request)

        if auth.issuer_type == "User":
            # TODO check scopes
            raise AuthorizationException("User cannot create enrollment")

        # logging.info(f'Creating usage {auth.issuer_type}, {auth.business.name}, {auth.user_id}, {data}')

        item = await create_usage(
            business_name=auth.business.name,
            user_id=auth.user_id,
            asset=data.asset,
            amount=data.amount,
            variant=data.variant,
            enrollment_id=data.enrollment_id,
            meta_data=data.meta_data,
            borrow=borrow,
        )
        await item.save()
        return item

    async def cancel_item(self, request: Request, uid: uuid.UUID):
        """
        Cancel a usage item.

        Args:

            uid (uuid.UUID): The uid of the usage.

        Returns:

            The canceled usage.
        """
        auth = await self.get_auth(request)
        item: Usage = await self.model.get_item(uid, business_name=auth.business.name)
        cancel_consumptions = []
        for consumption in item.consumptions:
            enrollment: Enrollment = await Enrollment.get_item(
                consumption.enrollment_id
            )
            leftover_bundles = await enrollment.get_leftover_bundles()
            for bundle in leftover_bundles:
                if bundle.asset == item.asset:
                    bundle.quota += consumption.amount
            new_consumption = UsageConsumption(
                enrollment_id=enrollment.uid,
                amount=-consumption.amount,
                leftover_bundles=leftover_bundles,  # TODO check if the leftover bundles are correct
            )
            cancel_consumptions.append(new_consumption)

        cancel_item = Usage(
            business_name=auth.business.name,
            user_id=auth.user_id,
            asset=item.asset,
            amount=item.amount,
            variant=item.variant,
            meta_data=item.meta_data,
            consumptions=cancel_consumptions,
        )
        await cancel_item.save()
        return cancel_item


router = UsageRouter().router
