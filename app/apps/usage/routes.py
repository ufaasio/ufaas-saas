from fastapi import Request

from apps.business.middlewares import AuthorizationException
from apps.business.routes import AbstractAuthRouter

from .models import Usage
from .schemas import UsageCreateSchema, UsageSchema
from .services import select_enrollment


class UsageRouter(AbstractAuthRouter[Usage, UsageSchema]):
    def __init__(self):
        super().__init__(model=Usage, schema=UsageSchema, user_dependency=None)

    def config_schemas(self, schema, **kwargs):
        super().config_schemas(schema)
        self.create_response_schema = list[self.schema]

    def config_routes(self):
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

    async def create_item(self, request: Request, data: UsageCreateSchema):
        # only business can create usage
        auth = await self.get_auth(request)

        if auth.auth_type == "user":
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
        res = []
        for enrollment, quota, leftover_bundles in enrollment_quotas:
            # create usage
            item = self.model(
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
        return [self.schema(**item.model_dump()) for item in res]


router = UsageRouter().router
