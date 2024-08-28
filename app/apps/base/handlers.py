from typing import Callable, Optional, Type, TypeVar

from fastapi import Request
from usso import UserData

from .models import BaseEntity, OwnedEntity

T = TypeVar("T", bound=BaseEntity)
OT = TypeVar("OT", bound=OwnedEntity)


def create_dto(cls: Type[OT]) -> Callable:
    async def dto(request: Request, user: Optional[UserData] = None, **kwargs) -> OT:
        form_data = await request.json()
        if user:
            form_data["user_id"] = user.uid
        return cls(**form_data)

    return dto


def update_dto(cls: Type[OT]) -> Callable:
    async def dto(
        request: Request, item: OT, user: Optional[UserData] = None, **kwargs
    ) -> OT:
        # request.path_params["uid"]
        form_data = await request.json()
        # kwargs = {}
        # if user:
        #     kwargs["user_id"] = user.uid

        for key, value in form_data.items():
            setattr(item, key, value)

        return item

    return dto
