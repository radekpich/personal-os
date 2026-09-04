from httpx import AsyncClient

from app.models.user import User
from tests.conftest import CsrfHeaders


async def test_register_endpoint_does_not_exist(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "password"},
    )
    assert response.status_code == 404


async def test_login_rate_limit_is_enforced(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await csrf_headers(client)
    for _ in range(5):
        response = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "wrong-password"},
            headers=headers,
        )
        assert response.status_code == 401

    response = await client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "wrong-password"},
        headers=headers,
    )
    assert response.status_code == 429
