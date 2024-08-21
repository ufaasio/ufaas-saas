import uuid
from typing import Any, Generic, Type, TypeVar

import singleton
from core.exceptions import BaseHTTPException
from fastapi import APIRouter, Depends, Query, Request
from server.config import Settings
from server.db import get_db_session
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .handlers import create_dto, update_dto
from .models import BaseEntity
from .schemas import BaseEntitySchema, PaginatedResponse

# Define a type variable
T = TypeVar("T", bound=BaseEntity)
TS = TypeVar("TS", bound=BaseEntitySchema)


class AbstractBaseRouter(Generic[T, TS], metaclass=singleton.Singleton):
    def __init__(
        self,
        model: Type[T],
        user_dependency: Any,
        *args,
        prefix: str = None,
        tags: list[str] = None,
        schema: Type[TS] = None,
        **kwargs,
    ):
        self.model = model
        self.schema = schema
        self.user_dependency = user_dependency
        if prefix is None:
            prefix = f"/{self.model.__name__.lower()}s"
        if tags is None:
            tags = [self.model.__name__]
        self.router = APIRouter(prefix=prefix, tags=tags, **kwargs)
        self.config_schemas(self.schema, **kwargs)
        self.config_routes(**kwargs)

    @classmethod
    def config_schemas(cls, schema, **kwargs):
        cls.list_response_schema = PaginatedResponse[schema]
        cls.retrieve_response_schema = schema
        cls.create_response_schema = schema
        cls.update_response_schema = schema
        cls.delete_response_schema = schema

        cls.create_request_schema = schema
        cls.update_request_schema = schema

    def config_routes(self, **kwargs):
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
            "/{uid:uuid}",
            self.update_item,
            methods=["PATCH"],
            response_model=self.update_response_schema,
            status_code=200,
        )
        self.router.add_api_route(
            "/{uid:uuid}",
            self.delete_item,
            methods=["DELETE"],
            response_model=self.delete_response_schema,
            # status_code=204,
        )

    async def get_user(self, request: Request, *args, **kwargs):
        if self.user_dependency is None:
            return None
        return await self.user_dependency(request)

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        session: AsyncSession = Depends(get_db_session),
    ):
        user = await self.get_user(request)
        limit = max(1, min(limit, Settings.page_max_limit))

        # Create the base query
        base_query = [
            self.model.is_deleted == False,
        ]

        # Apply user_id filtering if the model has a user_id attribute
        if hasattr(self.model, "user_id"):
            base_query.append(self.model.user_id == user.uid)

        # Query for getting the total count of items
        total_count_query = select(func.count()).filter(*base_query)  # .subquery()

        # Create the base query for fetching the items
        items_query = (
            select(self.model)
            .filter(*base_query)
            .order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
            # .subquery()
        )

        # Combine both queries into a single select statement
        combined_query = select(
            total_count_query.subquery().c[0].label("total"), items_query.subquery()
        )

        # Execute the combined query
        # result = await session.execute(combined_query)
        # res2 = result.fetchall()
        # res = result.scalars().all()

        total_result = await session.execute(total_count_query)
        total = total_result.scalar()

        # Extract total count and items

        items_result = await session.execute(items_query)
        rows = items_result.scalars().all()
        items = [self.schema(**row.__dict__) for row in rows]

        return PaginatedResponse(items=items, offset=offset, limit=limit, total=total)

    async def retrieve_item(
        self,
        request: Request,
        uid: uuid.UUID,
        session: AsyncSession = Depends(get_db_session),
    ):
        user = await self.get_user(request)
        user_id = user.uid if user else None
        item = await self.model.get_item(session, uid, user_id)

        if item is None:
            raise BaseHTTPException(
                status_code=404,
                error="item_not_found",
                message=f"{self.model.__name__.capitalize()} not found",
            )
        return self.retrieve_response_schema(**item.__dict__)

    async def create_item(
        self,
        request: Request,
        item: dict,
        session: AsyncSession = Depends(get_db_session),
    ):
        user = await self.get_user(request)
        item_data = await create_dto(self.schema)(request, user)

        # Create a new item instance from the model
        item = self.model(**item_data.model_dump())

        # Add the item to the session and commit the transaction
        session.add(item)
        await session.commit()
        await session.refresh(item)

        return self.create_response_schema(**item.__dict__)

    async def update_item(
        self,
        request: Request,
        uid: uuid.UUID,
        data: dict,
        session: AsyncSession = Depends(get_db_session),
    ):
        user = await self.get_user(request)
        user_id = user.uid if user else None
        item = await self.model.get_item(session, uid, user_id)

        if not item:
            raise BaseHTTPException(
                status_code=404,
                error="item_not_found",
                message=f"{self.model.__name__.capitalize()} not found",
            )

        item_data = await update_dto(self.model)(request, item, user)
        session.add(item_data)
        await session.commit()
        await session.refresh(item_data)

        return self.update_response_schema(**item_data.__dict__)

    async def delete_item(
        self,
        request: Request,
        uid: uuid.UUID,
        session: AsyncSession = Depends(get_db_session),
    ):
        user = await self.get_user(request)
        user_id = user.uid if user else None
        item = await self.model.get_item(session, uid, user_id)

        if not item:
            raise BaseHTTPException(
                status_code=404,
                error="item_not_found",
                message=f"{self.model.__name__.capitalize()} not found",
            )

        item.is_deleted = True
        session.add(item)
        await session.commit()
        await session.refresh(item)

        return self.delete_response_schema(**item.__dict__)
