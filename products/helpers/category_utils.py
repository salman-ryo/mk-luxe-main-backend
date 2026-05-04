from __future__ import annotations

from typing import Any, Optional

from django.utils.text import slugify

from ..models import Category
from .parsers import _clean_text


def _get_payload_section(payload: Any, key: str, default):
    """
    Supports both:
    1) direct payloads: { ...product fields... }
    2) wrapped payloads: { "product": {...}, "variants": [...], ... }
    """
    if isinstance(payload, dict) and key in payload:
        return payload.get(key, default)
    return default


def _unique_keep_order(items):
    """Deduplicate a list of model instances/values while preserving insertion order."""
    seen = set()
    out = []
    for item in items:
        key = getattr(item, "pk", item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _get_or_create_category(category_data: Any) -> Optional[Category]:
    """
    Accept either a plain string name or a dict with 'name'/'slug' keys.
    Gets or creates the Category, updating name if it drifted.
    """
    if not category_data:
        return None

    if isinstance(category_data, str):
        name = _clean_text(category_data)
        slug = slugify(name)
    else:
        name = _clean_text(category_data.get("name"))
        slug = _clean_text(category_data.get("slug")) or slugify(name)

    if not name and not slug:
        return None

    defaults = {"name": name or slug.replace("-", " ").title()}
    category, _ = Category.objects.get_or_create(slug=slug, defaults=defaults)

    if name and category.name != name:
        category.name = name
        category.save(update_fields=["name"])

    return category