from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_TEXTS_DIR = Path(__file__).resolve().parents[2] / "texts"
_DEFAULT_LOCALE = "ru"


@lru_cache
def _load_locale(locale: str) -> dict[str, Any]:
    path = _TEXTS_DIR / f"{locale}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"texts not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"invalid texts file: {path}")
    return data


def t(key: str, locale: str = _DEFAULT_LOCALE, **kwargs: object) -> str:
    """Resolve dotted key, e.g. ``start.welcome``."""
    node: Any = _load_locale(locale)
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"text key not found: {key!r} ({locale})")
        node = node[part]
    if not isinstance(node, str):
        raise KeyError(f"text key is not a string: {key!r}")
    return node.format(**kwargs) if kwargs else node
