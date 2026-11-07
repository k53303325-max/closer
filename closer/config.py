from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(default="", validation_alias="BOT_TOKEN")

    database_url: str = Field(
        default="postgresql+asyncpg://closer:closer@localhost:5432/closer",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    gigachat_auth_key: str | None = Field(default=None, validation_alias="GIGACHAT_AUTH_KEY")

    sms_provider: str = Field(default="fake", validation_alias="SMS_PROVIDER")
    sms_api_key: str | None = Field(default=None, validation_alias="SMS_API_KEY")
    sms_login: str | None = Field(default=None, validation_alias="SMS_LOGIN")
    sms_test_phone: str | None = Field(default=None, validation_alias="SMS_TEST_PHONE")

    storage_backend: str = Field(default="local", validation_alias="STORAGE_BACKEND")
    local_storage_path: Path = Field(
        default=_REPO_ROOT / "data",
        validation_alias="LOCAL_STORAGE_PATH",
    )

    s3_endpoint: str | None = Field(default=None, validation_alias="S3_ENDPOINT")
    s3_access_key: str | None = Field(default=None, validation_alias="S3_ACCESS_KEY")
    s3_secret_key: str | None = Field(default=None, validation_alias="S3_SECRET_KEY")
    s3_bucket: str | None = Field(default=None, validation_alias="S3_BUCKET")
    s3_region: str | None = Field(default=None, validation_alias="S3_REGION")

    pd_encryption_key: str | None = Field(default=None, validation_alias="PD_ENCRYPTION_KEY")
    pd_policy_url: str = Field(
        default="https://example.com/pd-policy",
        validation_alias="PD_POLICY_URL",
    )

    pep_offer_version: str = Field(default="pep_offer_v1", validation_alias="PEP_OFFER_VERSION")
    pep_offer_path: Path = Field(
        default=_REPO_ROOT / "docs" / "pep_offer.md",
        validation_alias="PEP_OFFER_PATH",
    )

    contract_price_rub: int = Field(default=99, validation_alias="CONTRACT_PRICE_RUB")

    webhook_url: str | None = Field(default=None, validation_alias="WEBHOOK_URL")

    admin_tg_ids: list[int] = Field(default_factory=list, validation_alias="ADMIN_TG_IDS")
    admin_tg_usernames: list[str] = Field(
        default_factory=list,
        validation_alias="ADMIN_TG_USERNAMES",
    )

    @field_validator("admin_tg_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: object) -> list[int]:
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [int(x) for x in v]
        parts = [x.strip() for x in str(v).split(",") if x.strip()]
        return [int(x) for x in parts if x.isdigit() or (x.startswith("-") and x[1:].isdigit())]

    @field_validator("admin_tg_usernames", mode="before")
    @classmethod
    def parse_admin_usernames(cls, v: object) -> list[str]:
        if v is None or v == "":
            return []
        if isinstance(v, list):
            items = v
        else:
            items = [x.strip() for x in str(v).split(",") if x.strip()]
        return [x.lstrip("@").lower() for x in items]

    def is_admin(self, tg_user_id: int, username: str | None) -> bool:
        if tg_user_id in self.admin_tg_ids:
            return True
        if username and username.lstrip("@").lower() in self.admin_tg_usernames:
            return True
        return False

    @field_validator("local_storage_path", "pep_offer_path", mode="before")
    @classmethod
    def parse_path(cls, v: object) -> Path:
        return Path(v) if not isinstance(v, Path) else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
