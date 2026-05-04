from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from django.db import transaction
from django.db.models import Avg, Count, Exists, F, Max, Min, OuterRef, Q
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.auth import APIKeyProtectedViewSetMixin

from .models import Category, Product, ProductFAQ, ProductImage, ProductVariant
from .serializers import CategorySerializer, ProductDetailSerializer, ProductListSerializer


def parse_bool(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _get_payload_section(payload: Any, key: str, default):
    """
    Supports both:
    1) direct payloads: { ...product fields... }
    2) wrapped payloads: { "product": {...}, "variants": [...], ... }
    """
    if isinstance(payload, dict) and key in payload:
        return payload.get(key, default)
    return default


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _unique_keep_order(items):
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
    category, created = Category.objects.get_or_create(slug=slug, defaults=defaults)

    if name and category.name != name:
        category.name = name
        category.save(update_fields=["name"])

    return category


class StandardPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            .annotate(product_count=Count("products", distinct=True))
            .order_by("sort_order", "name")
        )


class ProductViewSet(APIKeyProtectedViewSetMixin, viewsets.ModelViewSet):
    """
    GET    /products/         -> list
    GET    /products/<slug>/  -> retrieve
    POST   /products/         -> create (protected by API key)
    """

    permission_classes = [AllowAny]
    protected_actions = {"create"}
    required_api_key_env = "PRODUCT_ADMIN_API_KEY"
    api_key_header_name = "X-API-Key"

    lookup_field = "slug"
    pagination_class = StandardPageNumberPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True, status=Product.Status.ACTIVE)
            .select_related("primary_category")
            .prefetch_related("categories", "images", "variants", "faqs", "reviews")
            .annotate(
                avg_rating=Avg("reviews__rating", filter=Q(reviews__is_approved=True)),
                review_count=Count("reviews", filter=Q(reviews__is_approved=True), distinct=True),
                has_stock=Exists(
                    ProductVariant.objects.filter(
                        product=OuterRef("pk"),
                        is_active=True,
                        stock_quantity__gt=0,
                    )
                ),
                min_variant_price=Min("variants__price", filter=Q(variants__price__isnull=False)),
                max_variant_price=Max("variants__price", filter=Q(variants__price__isnull=False)),
            )
        )

        params = self.request.query_params

        search = params.get("search") or params.get("q")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(short_description__icontains=search)
                | Q(description__icontains=search)
                | Q(material__icontains=search)
                | Q(base_metal__icontains=search)
                | Q(plating__icontains=search)
                | Q(finish__icontains=search)
                | Q(gemstone__icontains=search)
                | Q(variants__name__icontains=search)
                | Q(variants__sku__icontains=search)
            )

        category_slug = params.get("category")
        category_id = params.get("category_id")
        primary_category_slug = params.get("primary_category")

        if category_slug:
            qs = qs.filter(Q(primary_category__slug=category_slug) | Q(categories__slug=category_slug))
        if category_id:
            qs = qs.filter(Q(primary_category__id=category_id) | Q(categories__id=category_id))
        if primary_category_slug:
            qs = qs.filter(primary_category__slug=primary_category_slug)

        for field in [
            "featured",
            "new_arrival",
            "best_seller",
            "anti_tarnish",
            "water_resistant",
            "sweat_resistant",
            "hypoallergenic",
            "nickel_free",
            "lightweight",
            "online",
        ]:
            value = parse_bool(params.get(field))
            if value is None:
                continue

            if field == "featured":
                qs = qs.filter(is_featured=value)
            elif field == "new_arrival":
                qs = qs.filter(is_new_arrival=value)
            elif field == "best_seller":
                qs = qs.filter(is_best_seller=value)
            elif field == "anti_tarnish":
                qs = qs.filter(anti_tarnish=value)
            elif field == "water_resistant":
                qs = qs.filter(water_resistant=value)
            elif field == "sweat_resistant":
                qs = qs.filter(sweat_resistant=value)
            elif field == "hypoallergenic":
                qs = qs.filter(hypoallergenic=value)
            elif field == "nickel_free":
                qs = qs.filter(nickel_free=value)
            elif field == "lightweight":
                qs = qs.filter(lightweight=value)
            elif field == "online":
                qs = qs.filter(is_available_online=value)

        in_stock = parse_bool(params.get("in_stock"))
        if in_stock is True:
            qs = qs.filter(has_stock=True)
        elif in_stock is False:
            qs = qs.filter(has_stock=False)

        material = params.get("material")
        if material:
            qs = qs.filter(
                Q(material__icontains=material)
                | Q(base_metal__icontains=material)
                | Q(plating__icontains=material)
                | Q(variants__material__icontains=material)
            )

        color = params.get("color")
        if color:
            qs = qs.filter(Q(color_family__icontains=color) | Q(variants__color__icontains=color))

        size = params.get("size")
        if size:
            qs = qs.filter(Q(variants__size__icontains=size) | Q(specifications__icontains=size))

        min_price = _to_decimal(params.get("min_price"))
        max_price = _to_decimal(params.get("max_price"))

        if min_price is not None:
            qs = qs.filter(min_variant_price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(min_variant_price__lte=max_price)

        status_param = params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        sort = params.get("sort") or params.get("ordering")
        if sort == "price_asc":
            qs = qs.order_by(F("min_variant_price").asc(nulls_last=True), "-is_featured", "-created_at")
        elif sort == "price_desc":
            qs = qs.order_by(F("min_variant_price").desc(nulls_last=True), "-is_featured", "-created_at")
        elif sort == "rating":
            qs = qs.order_by("-avg_rating", "-is_featured", "-created_at")
        elif sort == "popular":
            qs = qs.order_by("-review_count", "-is_featured", "-created_at")
        elif sort == "oldest":
            qs = qs.order_by("created_at")
        elif sort == "newest":
            qs = qs.order_by("-created_at")
        elif sort == "stock":
            qs = qs.order_by("-has_stock", "-created_at")
        else:
            qs = qs.order_by("-is_featured", "-created_at")

        return qs.distinct()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        payload = request.data if isinstance(request.data, dict) else {}

        product_data = _get_payload_section(payload, "product", payload)
        variants_data = _get_payload_section(payload, "variants", [])
        images_data = _get_payload_section(payload, "images", [])
        faqs_data = _get_payload_section(payload, "faqs", [])

        if not isinstance(product_data, dict):
            return Response(
                {"detail": "Invalid payload. 'product' must be an object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        primary_category_data = product_data.get("primary_category") or {}
        primary_category = _get_or_create_category(primary_category_data)

        category_items = []
        for item in product_data.get("categories", []) or []:
            cat = _get_or_create_category(item)
            if cat:
                category_items.append(cat)

        category_items = _unique_keep_order(category_items)

        product = Product()

        scalar_fields = [
            "name",
            "slug",
            "short_description",
            "description",
            "care_instructions",
            "material",
            "base_metal",
            "plating",
            "finish",
            "gemstone",
            "color_family",
            "seo_title",
            "seo_description",
            "currency",
            "delivery_note",
            "stall_note",
            "cover_image_url",
            "alt_text",
        ]
        for field in scalar_fields:
            value = product_data.get(field, None)
            if value is None:
                continue
            setattr(product, field, _clean_text(value))

        bool_fields = [
            "is_active",
            "is_featured",
            "is_new_arrival",
            "is_best_seller",
            "anti_tarnish",
            "water_resistant",
            "sweat_resistant",
            "hypoallergenic",
            "nickel_free",
            "lightweight",
            "is_available_online",
            "is_available_at_stall",
        ]
        for field in bool_fields:
            value = product_data.get(field, None)
            if value is None:
                continue
            parsed = parse_bool(value)
            if parsed is not None:
                setattr(product, field, parsed)

        status_value = _clean_text(product_data.get("status"))
        product.status = status_value or Product.Status.ACTIVE

        product.what_you_get = product_data.get("what_you_get", []) or []
        product.specifications = product_data.get("specifications", {}) or {}

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

        for category in category_items:
            if category.pk != (primary_category.pk if primary_category else None):
                product.categories.add(category)

        created_variants = []
        for idx, variant_data in enumerate(variants_data or []):
            if not isinstance(variant_data, dict):
                continue

            variant = ProductVariant(product=product)

            variant_scalar_fields = [
                "name",
                "sku",
                "barcode",
                "material",
                "color",
                "size",
            ]
            for field in variant_scalar_fields:
                value = variant_data.get(field, None)
                if value is None:
                    continue
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

            variant.attributes = variant_data.get("attributes", {}) or {}
            variant.save()
            created_variants.append(variant)

        if created_variants and not any(v.is_default for v in created_variants):
            first_variant = created_variants[0]
            first_variant.is_default = True
            first_variant.save(update_fields=["is_default"])

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

        serialized = ProductDetailSerializer(product, context=self.get_serializer_context()).data
        return Response(serialized, status=status.HTTP_201_CREATED)