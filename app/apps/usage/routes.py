import uuid

from fastapi import Request
from ufaas_fastapi_business.middlewares import AuthorizationException
from ufaas_fastapi_business.routes import AbstractAuthRouter

from .models import Usage
from .schemas import UsageCreateSchema, UsageSchema
from .services import select_enrollment


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
        self.create_response_schema = list[self.schema]

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

    async def list_items(self, request: Request, offset: int = 0, limit: int = 10):
        """
        List usages with pagination.

        Args:

            offset (int, optional): The offset for pagination. Defaults to 0.
            limit (int, optional): The limit for pagination. Defaults to 10.

        Returns:

            The list of usages.
        """
        return await super().list_items(request, offset, limit)

    async def retrieve_item(self, request: Request, uid: uuid.UUID):
        """
        Retrieve a usage.

        Args:

            uid (uuid.UUID): The uid of the usage.

        Returns:

            The usage.
        """
        return await super().retrieve_item(request, uid)

    async def create_item(self, request: Request, data: UsageCreateSchema):
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

        enrollment_quotas = await select_enrollment(
            business_name=auth.business.name,
            user_id=auth.user_id,
            asset=data.asset,
            amount=data.amount,
            variant=data.variant,
            enrollment_id=data.enrollment_id,
        )
        res: list[Usage] = []
        for enrollment, quota, leftover_bundles in enrollment_quotas:
            # create usage
            item = Usage(
                business_name=auth.business.name,
                user_id=auth.user_id,
                asset=data.asset,
                amount=quota,
                variant=data.variant,
                enrollment_id=enrollment.uid,
                meta_data=data.meta_data,
                leftover_bundles=leftover_bundles,
            )
            await item.save()
            res.append(item)
        return [UsageSchema(**item.model_dump()) for item in res]


router = UsageRouter().router
