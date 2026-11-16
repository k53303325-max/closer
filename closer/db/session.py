from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from closer.config import get_settings, resolve_database_url

_url = resolve_database_url()
_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}
_engine = create_async_engine(_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
