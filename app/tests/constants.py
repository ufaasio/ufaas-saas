"""Test constants."""

import os

import dotenv
from singleton import Singleton

dotenv.load_dotenv()


class StaticData(metaclass=Singleton):
    """Static test data constants."""

    tenant_id_1 = "0197f464-46c8-72a1-8b23-0819b8622a0c"
    business_domain_1 = "test.uln.me"

    tenant_id_2 = "business_2"

    user_id_1_1 = "00000001-0000-0000-0001-000000000001"
    user_id_1_2 = "00000001-0000-0000-0001-000000000002"
    user_id_2_1 = "00000001-0000-0000-0002-000000000001"
    user_id_2_2 = "00000001-0000-0000-0002-000000000002"
    wallet_id_1_1 = "00000002-0000-0000-0001-000000000001"
    wallet_id_1_2 = "00000002-0000-0000-0001-000000000002"
    wallet_id_1_3 = "00000002-0000-0000-0001-000000000003"
    wallet_id_2_1 = "00000002-0000-0000-0002-000000000001"
    wallet_id_2_2 = "00000002-0000-0000-0002-000000000002"

    refresh_token = os.getenv("USSO_REFRESH_TOKEN_BUSINESS")
    refresh_token_user = os.getenv("USSO_REFRESH_TOKEN_USER")
    usso_api_key = os.getenv("USSO_ADMIN_API_KEY")
