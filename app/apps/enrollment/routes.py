import uuid

from fastapi import Query, Request
from fastapi_mongo_base.schemas import PaginatedResponse

from apps.business.middlewares import AuthorizationException
from apps.business.routes import AbstractAuthRouter
from server.config import Settings

from .models import Enrollment
from .schemas import EnrollmentCreateSchema, EnrollmentDetailSchema


class EnrollmentRouter(AbstractAuthRouter[Enrollment, EnrollmentDetailSchema]):
    def __init__(self):
        super().__init__(
            model=Enrollment, schema=EnrollmentDetailSchema, user_dependency=None
        )

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
        # self.router.add_api_route(
        #     "/{uid:uuid}",
        #     self.update_item,
        #     methods=["PATCH"],
        #     response_model=self.update_response_schema,
        #     status_code=200,
        # )
        self.router.add_api_route(
            "/{uid:uuid}",
            self.delete_item,
            methods=["DELETE"],
            response_model=self.delete_response_schema,
            # status_code=204,
        )

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
    ):
        auth = await self.get_auth(request)
        items, total = await self.model.list_total_combined(
            user_id=auth.user_id,
            business_name=auth.business.name,
            offset=offset,
            limit=limit,
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
        item = await super().retrieve_item(request, uid)
        return self.retrieve_response_schema(
            **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
        )

    async def create_item(self, request: Request, data: EnrollmentCreateSchema):
        # only business can create enrollment
        auth = await self.get_auth(request)
        if auth.auth_type == "user":
            # TODO check scopes
            raise AuthorizationException("User cannot create enrollment")
        data = data.model_dump()
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

    async def delete_item(self, request: Request, uid: uuid.UUID):
        raise NotImplementedError("Delete is not allowed")
        item = await super().delete_item(request, uid)
        return self.retrieve_response_schema(
            **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
        )


router = EnrollmentRouter().router
