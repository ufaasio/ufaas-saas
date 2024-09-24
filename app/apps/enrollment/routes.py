from fastapi import Request

from apps.business.routes import AbstractAuthRouter

from .models import Enrollment
from .schemas import EnrollmentCreateSchema, EnrollmentSchema


class EnrollmentRouter(AbstractAuthRouter[Enrollment, EnrollmentSchema]):
    def __init__(self):
        super().__init__(model=Enrollment, schema=EnrollmentSchema, user_dependency=None)

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

    async def create_item(self, request: Request, data: EnrollmentCreateSchema):
        # only business can create enrollment
        return await super().create_item(request, data.model_dump())


router = EnrollmentRouter().router
