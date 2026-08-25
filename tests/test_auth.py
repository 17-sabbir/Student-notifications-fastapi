import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from main import app
from app.db.session import Base
from app.models.user import User
from app.core.security import get_password_hash

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_signup(client: AsyncClient):
    response = await client.post("/auth/signup", json={
        "email": "test@example.com",
        "password": "SecurePass1"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_unverified(client: AsyncClient, db_session: AsyncSession):
    user = User(id="test-user-id", email="test@example.com", hashed_password=get_password_hash("SecurePass1"), is_verified=False)
    db_session.add(user)
    await db_session.commit()

    response = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "SecurePass1"
    })
    assert response.status_code == 403
    assert response.headers.get("X-Error-Code") == "EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
