"""Best-effort SQLite ALTER for dev DBs created before new columns."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

_ALTER_STATEMENTS = [
    "ALTER TABLE documents ADD COLUMN counterparty_user_id INTEGER",
    "ALTER TABLE documents ADD COLUMN invite_token_hash VARCHAR(64)",
    "ALTER TABLE documents ADD COLUMN invite_expires_at DATETIME",
    "ALTER TABLE documents ADD COLUMN change_request JSON",
]


async def sqlite_migrate(engine: AsyncEngine) -> None:
    if "sqlite" not in str(engine.url):
        return
    async with engine.begin() as conn:
        for stmt in _ALTER_STATEMENTS:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS signatures (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    version_no INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role VARCHAR(16) NOT NULL,
                    signed_at DATETIME,
                    pdf_sha256 VARCHAR(64),
                    otp_hash VARCHAR(64),
                    otp_expires_at DATETIME,
                    otp_attempts INTEGER DEFAULT 0,
                    sms_sent_count INTEGER DEFAULT 0,
                    otp_locked_until DATETIME,
                    last_code_sent_at DATETIME,
                    UNIQUE(document_id, version_no, user_id)
                )
                """
            )
        )
    logger.info("SQLite stage-3 migrate done")