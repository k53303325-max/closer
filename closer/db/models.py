from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from closer.compat import UTC

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    tg_username: Mapped[Optional[str]] = mapped_column(String(64))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    phone_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    free_contracts_used: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    profile: Mapped[Optional["Profile"]] = relationship(back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    status: Mapped[Optional[str]] = mapped_column(String(32))  # individual | self_employed | ip | ooo
    full_name: Mapped[Optional[str]] = mapped_column(String(256))
    passport_enc: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    inn: Mapped[Optional[str]] = mapped_column(String(16))
    ogrn: Mapped[Optional[str]] = mapped_column(String(16))
    org_name: Mapped[Optional[str]] = mapped_column(String(256))
    signer_position: Mapped[Optional[str]] = mapped_column(String(256))
    signer_basis: Mapped[Optional[str]] = mapped_column(String(256))
    address_enc: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    email: Mapped[Optional[str]] = mapped_column(String(256))
    bank: Mapped[Optional[str]] = mapped_column(Text)
    sbp: Mapped[Optional[str]] = mapped_column(String(256))
    vat_mode: Mapped[str] = mapped_column(String(16), default="none")
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (UniqueConstraint("user_id", "kind", "doc_version", name="uq_consent_user_kind_ver"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # pep_offer | pd_policy
    doc_version: Mapped[str] = mapped_column(String(64))
    doc_sha256: Mapped[str] = mapped_column(String(64))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_key: Mapped[str] = mapped_column(String(32), default="uslugi")
    status: Mapped[str] = mapped_column(String(32), default="composing")  # composing | draft | deleted
    contract_number: Mapped[Optional[str]] = mapped_column(String(32))
    user_role: Mapped[Optional[str]] = mapped_column(String(16))  # executor | customer
    deal: Mapped[dict] = mapped_column(JSONB, default=dict)
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    versions: Mapped[List["DocumentVersion"]] = relationship(back_populates="document")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_no", name="uq_document_version_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    values: Mapped[dict] = mapped_column(JSONB, default=dict)
    pdf_storage_key: Mapped[Optional[str]] = mapped_column(String(512))
    pdf_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped[Document] = relationship(back_populates="versions")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    event: Mapped[str] = mapped_column(String(64), index=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    doc_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    prev_hash: Mapped[str] = mapped_column(String(64))
    record_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
