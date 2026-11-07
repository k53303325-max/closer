from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from closer.config import get_settings


@dataclass(frozen=True)
class PepOffer:
    version: str
    sha256: str
    body: str
    summary: str


def _extract_offer_body(markdown: str) -> str:
    m = re.search(r"^## Текст\s*$", markdown, flags=re.MULTILINE)
    if m:
        return markdown[m.end() :].strip()
    return markdown.strip()


def _summary_from_body(body: str) -> str:
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    return "\n".join(lines[:4])


@lru_cache
def load_pep_offer() -> PepOffer:
    settings = get_settings()
    path: Path = settings.pep_offer_path
    text = path.read_text(encoding="utf-8")
    body = _extract_offer_body(text)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return PepOffer(
        version=settings.pep_offer_version,
        sha256=digest,
        body=body,
        summary=_summary_from_body(body),
    )
