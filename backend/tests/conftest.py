import os
from collections.abc import AsyncIterator, Awaitable, Callable

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-do-not-use-in-prod")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("CORS_ORIGINS", "https://testserver")
os.environ.setdefault("COOKIE_SECURE", "true")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("ACCESS_COOKIE_NAME", "access_token")
os.environ.setdefault("REFRESH_COOKIE_NAME", "refresh_token")
os.environ.setdefault("CSRF_COOKIE_NAME", "csrf_token")
os.environ.setdefault("CSRF_HEADER_NAME", "X-CSRF-Token")
os.environ.setdefault("RATE_LIMIT_LOGIN", "5/minute")
os.environ.setdefault("RATE_LIMIT_DEFAULT", "1000/minute")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

CsrfHeaders = Callable[[AsyncClient], Awaitable[dict[str, str]]]

engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _override_get_db() -> AsyncIterator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
async def setup_db() -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(request: pytest.FixtureRequest) -> AsyncIterator[AsyncClient]:
    client_host = f"test-{abs(hash(request.node.nodeid)) % 10_000_000}.local"
    transport = ASGITransport(app=app, client=(client_host, 123))
    async with AsyncClient(transport=transport, base_url="https://testserver") as ac:
        yield ac


@pytest.fixture
async def test_user() -> User:
    async with TestSessionLocal() as session:
        user = User(
            email="test@example.com",
            hashed_password=hash_password("correct-password"),
            display_name="Test User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def other_user() -> User:
    async with TestSessionLocal() as session:
        user = User(
            email="other@example.com",
            hashed_password=hash_password("correct-password"),
            display_name="Other User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def csrf_headers() -> CsrfHeaders:
    async def _get_csrf_headers(client: AsyncClient) -> dict[str, str]:
        await client.get("/health")
        token = client.cookies.get("csrf_token")
        assert token is not None
        return {"X-CSRF-Token": token}

    return _get_csrf_headers
