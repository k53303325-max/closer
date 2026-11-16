"""JSON column: JSON on SQLite, JSONB on PostgreSQL."""

from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JsonDict = JSON().with_variant(JSONB(), "postgresql")