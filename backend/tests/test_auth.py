from httpx import AsyncClient

from app.models.user import User
from tests.conftest import CsrfHeaders

LOGIN_PATH = "/auth/login"
REFRESH_PATH = "/auth/refresh"
LOGOUT_PATH = "/auth/logout"
ME_PATH = "/auth/me"


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, user: User, password: str) -> None:
    headers = await csrf_headers(client)
    await client.post(LOGIN_PATH, json={"email": user.email, "password": password}, headers=headers)


async def test_login_success(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    headers = await csrf_headers(client)
    response = await client.post(
        LOGIN_PATH,
        json={"email": test_user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email
    assert client.cookies.get("access_token") is not None
    assert client.cookies.get("refresh_token") is not None


async def test_login_bad_password(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    headers = await csrf_headers(client)
    response = await client.post(
        LOGIN_PATH,
        json={"email": test_user.email, "password": "wrong-password"},
        headers=headers,
    )
    assert response.status_code == 401
    assert client.cookies.get("access_token") is None


async def test_login_requires_csrf_header(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    await csrf_headers(client)
    response = await client.post(
        LOGIN_PATH,
        json={"email": test_user.email, "password": "correct-password"},
    )
    assert response.status_code == 403


async def test_login_rejects_mismatched_csrf_header(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    await csrf_headers(client)
    response = await client.post(
        LOGIN_PATH,
        json={"email": test_user.email, "password": "correct-password"},
        headers={"X-CSRF-Token": "not-the-right-token"},
    )
    assert response.status_code == 403


async def test_me_without_token(client: AsyncClient) -> None:
    response = await client.get(ME_PATH)
    assert response.status_code == 401


async def test_me_with_token(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    await _login(client, csrf_headers, test_user, "correct-password")
    response = await client.get(ME_PATH)
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email


async def test_refresh_rotates_token(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    await _login(client, csrf_headers, test_user, "correct-password")
    old_refresh = client.cookies.get("refresh_token")
    assert old_refresh is not None

    refresh_headers = await csrf_headers(client)
    response = await client.post(REFRESH_PATH, headers=refresh_headers)
    assert response.status_code == 200

    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh is not None
    assert new_refresh != old_refresh


async def test_reused_revoked_refresh_token_revokes_family(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    await _login(client, csrf_headers, test_user, "correct-password")
    old_refresh = client.cookies.get("refresh_token")
    assert old_refresh is not None

    refresh_headers = await csrf_headers(client)
    response = await client.post(REFRESH_PATH, headers=refresh_headers)
    assert response.status_code == 200
    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh is not None
    assert new_refresh != old_refresh

    client.cookies.set("refresh_token", old_refresh, domain="testserver.local")
    reuse_headers = await csrf_headers(client)
    response = await client.post(REFRESH_PATH, headers=reuse_headers)
    assert response.status_code == 401

    client.cookies.set("refresh_token", new_refresh, domain="testserver.local")
    final_headers = await csrf_headers(client)
    response = await client.post(REFRESH_PATH, headers=final_headers)
    assert response.status_code == 401


async def test_refresh_without_csrf_header_rejected(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    await _login(client, csrf_headers, test_user, "correct-password")
    response = await client.post(REFRESH_PATH)
    assert response.status_code == 403


async def test_logout_revokes_refresh_token(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    await _login(client, csrf_headers, test_user, "correct-password")

    logout_headers = await csrf_headers(client)
    response = await client.post(LOGOUT_PATH, headers=logout_headers)
    assert response.status_code == 200

    refresh_headers = await csrf_headers(client)
    response = await client.post(REFRESH_PATH, headers=refresh_headers)
    assert response.status_code == 401
