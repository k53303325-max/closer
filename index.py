"""Vercel default Python entry (re-export webhook handler)."""

from api.telegram import handler

__all__ = ["handler"]
