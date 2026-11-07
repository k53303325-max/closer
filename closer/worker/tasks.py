from __future__ import annotations

import os

from arq.connections import RedisSettings


async def ping(ctx: dict) -> str:
    return "pong"


class WorkerSettings:
    """arq worker entrypoint: ``arq closer.worker.tasks.WorkerSettings``."""

    functions = [ping]
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    )
