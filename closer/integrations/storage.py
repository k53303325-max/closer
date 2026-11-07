from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Protocol

from closer.config import Settings, get_settings


class ObjectStorage(Protocol):
    async def put_bytes(self, key: str, data: bytes) -> str: ...

    async def put_file(self, key: str, src: Path) -> str: ...

    async def path_for(self, key: str) -> Path: ...

    async def read_bytes(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class LocalObjectStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _full(self, key: str) -> Path:
        key = key.lstrip("/").replace("..", "")
        path = (self._root / key).resolve()
        if not str(path).startswith(str(self._root)):
            raise ValueError("invalid storage key")
        return path

    async def put_bytes(self, key: str, data: bytes) -> str:
        return await asyncio.to_thread(self._put_bytes_sync, key, data)

    def _put_bytes_sync(self, key: str, data: bytes) -> str:
        path = self._full(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def put_file(self, key: str, src: Path) -> str:
        return await asyncio.to_thread(self._put_file_sync, key, src)

    def _put_file_sync(self, key: str, src: Path) -> str:
        dest = self._full(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return str(dest)

    async def path_for(self, key: str) -> Path:
        return self._full(key)

    async def read_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(self._full(key).read_bytes)

    async def delete(self, key: str) -> None:
        path = self._full(key)
        if path.is_file():
            await asyncio.to_thread(path.unlink)


class S3ObjectStorage:
    """S3-compatible backend (RF). Wire boto3/aiobotocore when STORAGE_BACKEND=s3."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region

    async def put_bytes(self, key: str, data: bytes) -> str:
        raise NotImplementedError("S3 storage is not wired yet; set STORAGE_BACKEND=local")

    async def put_file(self, key: str, src: Path) -> str:
        raise NotImplementedError("S3 storage is not wired yet; set STORAGE_BACKEND=local")

    async def path_for(self, key: str) -> Path:
        raise NotImplementedError("S3 storage has no local path")

    async def read_bytes(self, key: str) -> bytes:
        raise NotImplementedError("S3 storage is not wired yet; set STORAGE_BACKEND=local")

    async def delete(self, key: str) -> None:
        raise NotImplementedError("S3 storage is not wired yet; set STORAGE_BACKEND=local")


def get_storage(settings: Settings | None = None) -> ObjectStorage:
    settings = settings or get_settings()
    backend = (settings.storage_backend or "local").lower()
    if backend == "local":
        return LocalObjectStorage(settings.local_storage_path)
    if backend == "s3":
        if not all(
            [settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key, settings.s3_bucket]
        ):
            raise RuntimeError("S3 storage requires S3_ENDPOINT, keys and S3_BUCKET")
        return S3ObjectStorage(
            settings.s3_endpoint or "",
            settings.s3_access_key or "",
            settings.s3_secret_key or "",
            settings.s3_bucket or "",
            settings.s3_region,
        )
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.storage_backend}")
