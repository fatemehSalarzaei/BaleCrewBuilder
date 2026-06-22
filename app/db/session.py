from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_engine = None
_session_factory = None


def _ensure_engine() -> None:
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False, future=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    _ensure_engine()
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session
