"""Shared test fixtures for GraphNovel."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.database import Base


@pytest.fixture(scope="session")
async def engine():
    """Session-scoped SQLite in-memory engine for fast tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Per-test database session with automatic rollback."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
def mock_ai_service(mocker):
    """Mock AI service that returns predictable responses."""
    mock = mocker.AsyncMock()
    mock.generate.return_value = "Test generated content."
    mock.generate_json.return_value = {"key": "value", "score": 85}
    return mock
