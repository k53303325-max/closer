from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from closer.db.models import Base

logger = logging.getLogger(__name__)


async def ensure_schema(engine: AsyncEngine) -> None:
    if "sqlite" not in str(engine.url):
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("SQLite schema ready at %s", engine.url.database)