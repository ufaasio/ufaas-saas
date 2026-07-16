"""Enrollment API routes."""

import logging
from datetime import datetime

from fastapi import Query, Request
from fastapi_mongo_base.schemas import PaginatedResponse
from fastapi_mongo_base.utils import usso_routes

from server.config import Settings

from .models import Enrollment
from .schemas import (
    EnrollmentCreateSchema,
    EnrollmentDetailSchema,
    EnrollmentSchema,
    EnrollmentUpdateSchema,
    QuotasResponseSchema,
)

logger = logging.getLogger(__name__)


class EnrollmentRouter(usso_routes.AbstractTenantUSSORouter):
    """Router for enrollment CRUD operations."""

    model = Enrollment
    schema = EnrollmentDetailSchema

    def config_schemas(self, schema: type, **kwargs: object) -> None:
        """Configure response schemas."""
        super().config_schemas(schema, **kwargs)
        self.delete_response_schema = EnrollmentSchema
        self.quotas_response_schema = QuotasResponseSchema

    def config_routes(self, **kwargs: object) -> None:
        """Configure routes."""
        self.router.add_api_route(
            "/quotas",
            self.quotas,
            methods=["GET"],
            response_model=self.quotas_response_schema,
            status_code=200,
        )
        super().config_routes(**kwargs)

    async def quotas(
        self,
        request: Request,
        asset: str,
        user_id: str | None = None,
        variant: str | None = None,
    ) -> QuotasResponseSchema:
        """Retrieve the total quotas of an asset for a user."""
        user = await self.get_user(request)

        logger.info("user_id: %s, variant: %s", user_id, variant)

        overdue_enrollments = await Enrollment.overdue_enrollments(
            user.tenant_id, user_id
        )

        logger.info(
            "overdue_enrollments: %s, %s, %s", overdue_enrollments, asset, variant
        )

        quotas = await Enrollment.quotas(
            tenant_id=user.tenant_id,
            user_id=user_id or user.uid,
            asset=asset,
            variant=variant,
        )

        logger.info("%s %s %s %s %s", quotas, asset, variant, user.uid, user.tenant_id)

        return QuotasResponseSchema(**{
            "user_id": user.uid,
            "quota": quotas if not overdue_enrollments else 0,
            "overdue": bool(overdue_enrollments),
            "asset": asset,
            "variant": variant,
            "_quota": quotas,
        })

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        user_id: str | None = None,
        asset: str | None = None,
        variant: str | None = None,
        is_valid: bool = True,
        created_at_from: datetime | None = None,
        created_at_to: datetime | None = None,
        start_at_from: datetime | None = None,
        start_at_to: datetime | None = None,
        expire_at_from: datetime | None = None,
        expire_at_to: datetime | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        paid_at_from: datetime | None = None,
        paid_at_to: datetime | None = None,
    ) -> PaginatedResponse[EnrollmentDetailSchema]:
        """
        Retrieve a list of enrollments with pagination.

        Args:
            request: The incoming request.
            offset: The offset value for pagination.
            limit: The maximum number of items to retrieve.
            user_id: Filter by user ID.
            asset: Filter by asset.
            variant: Filter by variant.
            is_valid: Filter by validity status.
            created_at_from: Filter by created_at start range.
            created_at_to: Filter by created_at end range.
            start_at_from: Filter by start_at start range.
            start_at_to: Filter by start_at end range.
            expire_at_from: Filter by expire_at start range.
            expire_at_to: Filter by expire_at end range.
            due_date_from: Filter by due_date start range.
            due_date_to: Filter by due_date end range.
            paid_at_from: Filter by paid_at start range.
            paid_at_to: Filter by paid_at end range.

        Returns:
            PaginatedResponse: The paginated response containing the items,
                offset, limit, and total count.
        """
        return await self._list_items(
            request=request,
            offset=offset,
            limit=limit,
            user_id=user_id,
            asset=asset,
            variant=variant,
            is_valid=is_valid,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            start_at_from=start_at_from,
            start_at_to=start_at_to,
            expire_at_from=expire_at_from,
            expire_at_to=expire_at_to,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
            paid_at_from=paid_at_from,
            paid_at_to=paid_at_to,
        )

    async def _list_items(
        self,
        request: Request,
        offset: int = 0,
        limit: int = 10,
        **kwargs: object,
    ) -> PaginatedResponse[EnrollmentDetailSchema]:
        user = await self.get_user(request)
        limit = max(1, min(limit, Settings.page_max_limit))

        filters = self.get_list_filter_queries(user=user)
        if filters.get("__deny__"):
            return PaginatedResponse(
                items=[],
                total=0,
                offset=offset,
                limit=limit,
            )

        items, total = await self.model.list_total_combined(
            offset=offset,
            limit=limit,
            tenant_id=user.tenant_id,
            **(kwargs | filters),
        )
        items_in_schema = [
            self.list_item_schema(
                **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
            )
            for item in items
        ]

        return PaginatedResponse(
            items=items_in_schema,
            total=total,
            offset=offset,
            limit=limit,
        )

    async def retrieve_item(self, request: Request, uid: str) -> EnrollmentDetailSchema:
        """
        Retrieve an enrollment with the given UID.

        Args:
            request: The incoming request.
            uid: The UID of the item to retrieve.

        Returns:
            Enrolment: The retrieved enrollment with the leftover bundles.
        """
        item: Enrollment = await super().retrieve_item(request, uid)
        return self.retrieve_response_schema(
            **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
        )

    async def create_item(
        self, request: Request, data: EnrollmentCreateSchema
    ) -> EnrollmentDetailSchema:
        """
        Create an enrollment item.

        Args:
            request: The incoming request.
            data: The enrollment creation data.
            - user_id: str, owner of the enrollment
            - price: Decimal, price of the enrollment
            - invoice_id: str | None, invoice id of the enrollment if any
            - start_at: datetime, start date of the enrollment,
                        default set now if not provided
            - expire_at: datetime | None, expiration date of the enrollment
                         for the selected bundles, default None
            - duration: int | None, duration of the enrollment in days, default None
            - status: "active" | "inactive", the status of the enrollment,
                      default "active"
            - bundles: list[Bundle], list of bundles that are included in the enrollment
                       Each bundle should have a asset, quota, and unit.
                asset: str, the asset name (For example, "Storage" in storage service,
                       "Tokens" in LLM API service, ...)
                quota: Decimal, the quota of the asset
                unit: str | None, the unit of the quota
                      (
                        For example, "GB" in storage service,
                        "Tokens" in LLM API service, ...
                      ) if any
            - variant: str | None, the variant limitation of the enrollment.
                    For example, "car" category in a classified advertisements service.
                    For normal enrollment, it would be None and it is not to be provided
            - meta_data: dict | None = None, additional metadata for the enrollment
                    that will be stored as a dictionary.

        Returns:
            dict: The created enrollment item.

        Raises:
            - AuthorizationException:
                If the user is not authorized to create an enrollment.
        """
        # only business can create enrollment
        user = await self.get_user(request)

        if data.user_id:
            await self.authorize(
                action="create",
                user=user,
                filter_data=data.model_dump(exclude_none=True),
            )

        item = self.model(
            tenant_id=user.tenant_id,
            user_id=data.user_id or user.uid,
            **data.model_dump(exclude=["user_id"]),
        )
        await item.save()
        return self.schema(
            **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
        )

    async def update_item(
        self, request: Request, uid: str, data: EnrollmentUpdateSchema
    ) -> EnrollmentDetailSchema:
        """Update an enrollment."""
        item: Enrollment = await super().update_item(
            request, uid, data.model_dump(exclude_unset=True)
        )
        return self.retrieve_response_schema(
            **item.model_dump(), leftover_bundles=await item.get_leftover_bundles()
        )

    async def delete_item(self, request: Request, uid: str) -> EnrollmentDetailSchema:
        """Delete an enrollment."""
        return await super().delete_item(request, uid)


router = EnrollmentRouter().router
