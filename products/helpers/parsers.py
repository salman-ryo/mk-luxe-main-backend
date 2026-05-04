from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional


def parse_bool(value) -> Optional[bool]:
    """Coerce a loose string/int value to True, False, or None."""
    if value is None:
        return None
    value = str(value).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _clean_text(value: Any) -> str:
    """Strip and stringify any value; returns empty string for None."""
    if value is None:
        return ""
    return str(value).strip()


def _to_decimal(value: Any) -> Optional[Decimal]:
    """Safely coerce a value to Decimal, returning None on failure."""
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None