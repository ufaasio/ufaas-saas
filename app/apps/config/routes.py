from fastapi_mongo_base.utils import usso_routes

from .models import Configuration
from .schemas import Config


class ConfigRouter(usso_routes.AbstractTenantUSSORouter):
    model = Configuration
    schema = Config


router = ConfigRouter().router
