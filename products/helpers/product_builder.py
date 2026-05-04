from __future__ import annotations

from typing import Any

from django.utils.text import slugify

from products.models import Product, ProductFAQ, ProductImage, ProductVariant
from .parsers import _clean_text, _to_decimal, parse_bool


PRODUCT_SCALAR_FIELDS = [
    "name", "slug", "short_description", "description", "care_instructions",
    "material", "base_metal", "plating", "finish", "gemstone", "color_family",
    "seo_title", "seo_description", "currency", "delivery_note", "stall_note",
    "cover_image_url", "alt_text",
]

PRODUCT_BOOL_FIELDS = [
    "is_active", "is_featured", "is_new_arrival", "is_best_seller",
    "anti_tarnish", "water_resistant", "sweat_resistant", "hypoallergenic",
    "nickel_free", "lightweight", "is_available_online", "is_available_at_stall",
]

VARIANT_SCALAR_FIELDS = ["name", "sku", "barcode", "material", "color", "size"]


def build_product(product_data: dict, primary_category=None) -> Product:
    """
    Instantiate and save a Product from a flat data dict.
    Does NOT handle categories M2M — caller is responsible for that.
    """
    product = Product()

    for field in PRODUCT_SCALAR_FIELDS:
        value = product_data.get(field)
        if value is not None:
            setattr(product, field, _clean_text(value))

    for field in PRODUCT_BOOL_FIELDS:
        value = product_data.get(field)
        if value is not None:
            parsed = parse_bool(value)
            if parsed is not None:
                setattr(product, field, parsed)

    status_value = _clean_text(product_data.get("status"))
    product.status = status_value or Product.Status.ACTIVE

    product.what_you_get = product_data.get("what_you_get") or []
    product.specifications = product_data.get("specifications") or {}

    product.price_from = _to_decimal(product_data.get("price_from"))
    product.price_to = _to_decimal(product_data.get("price_to"))

    product.warranty_months = product_data.get("warranty_months")
    product.return_window_days = product_data.get("return_window_days")
    product.weight_grams = _to_decimal(product_data.get("weight_grams"))
    product.length_mm = _to_decimal(product_data.get("length_mm"))
    product.width_mm = _to_decimal(product_data.get("width_mm"))

    if primary_category:
        product.primary_category = primary_category

    if not product.slug:
        product.slug = slugify(product.name or "item")

    product.save()
    return product


def build_variants(product: Product, variants_data: list) -> list[ProductVariant]:
    """
    Bulk-create ProductVariant instances for the given product.
    Ensures exactly one default variant exists.
    """
    created_variants = []

    for idx, variant_data in enumerate(variants_data or []):
        if not isinstance(variant_data, dict):
            continue

        variant = ProductVariant(product=product)

        for field in VARIANT_SCALAR_FIELDS:
            value = variant_data.get(field)
            if value is not None:
                setattr(variant, field, _clean_text(value))

        variant.length_mm = _to_decimal(variant_data.get("length_mm"))
        variant.width_mm = _to_decimal(variant_data.get("width_mm"))
        variant.weight_grams = _to_decimal(variant_data.get("weight_grams"))
        variant.price = _to_decimal(variant_data.get("price"))
        variant.compare_at_price = _to_decimal(variant_data.get("compare_at_price"))

        variant.stock_quantity = int(variant_data.get("stock_quantity") or 0)
        variant.reserved_quantity = int(variant_data.get("reserved_quantity") or 0)
        variant.low_stock_threshold = int(variant_data.get("low_stock_threshold") or 3)

        is_active = variant_data.get("is_active")
        if is_active is not None:
            parsed = parse_bool(is_active)
            if parsed is not None:
                variant.is_active = parsed

        is_default = variant_data.get("is_default")
        if is_default is not None:
            parsed = parse_bool(is_default)
            if parsed is not None:
                variant.is_default = parsed
        else:
            variant.is_default = idx == 0

        variant.attributes = variant_data.get("attributes") or {}
        variant.save()
        created_variants.append(variant)

    # Guarantee at least one default variant
    if created_variants and not any(v.is_default for v in created_variants):
        first = created_variants[0]
        first.is_default = True
        first.save(update_fields=["is_default"])

    return created_variants


def build_images(product: Product, images_data: list) -> None:
    """Create ProductImage records for the given product."""
    for idx, image_data in enumerate(images_data or []):
        if not isinstance(image_data, dict):
            continue

        ProductImage.objects.create(
            product=product,
            image_url=_clean_text(image_data.get("image_url")),
            alt_text=_clean_text(image_data.get("alt_text")),
            is_primary=bool(image_data.get("is_primary", idx == 0)),
            sort_order=int(image_data.get("sort_order") or idx),
        )


def build_faqs(product: Product, faqs_data: list) -> None:
    """Create ProductFAQ records for the given product."""
    for idx, faq_data in enumerate(faqs_data or []):
        if not isinstance(faq_data, dict):
            continue

        ProductFAQ.objects.create(
            product=product,
            question=_clean_text(faq_data.get("question")),
            answer=_clean_text(faq_data.get("answer")),
            sort_order=int(faq_data.get("sort_order") or idx),
            is_active=bool(faq_data.get("is_active", True)),
        )