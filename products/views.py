from __future__ import annotations

from django.db import transaction
from django.db.models import Avg, Count, Exists, F, Max, Min, OuterRef, Q
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.auth import APIKeyProtectedViewSetMixin

from .helpers import (
    _get_or_create_category,
    _get_payload_section,
    _to_decimal,
    _unique_keep_order,
    build_faqs,
    build_images,
    build_product,
    build_variants,
    parse_bool,
)
from .models import Category, Product, ProductVariant
from .serializers import CategorySerializer, ProductDetailSerializer, ProductListSerializer


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

        boolean_filter_map = {
            "featured": "is_featured",
            "new_arrival": "is_new_arrival",
            "best_seller": "is_best_seller",
            "anti_tarnish": "anti_tarnish",
            "water_resistant": "water_resistant",
            "sweat_resistant": "sweat_resistant",
            "hypoallergenic": "hypoallergenic",
            "nickel_free": "nickel_free",
            "lightweight": "lightweight",
            "online": "is_available_online",
        }
        for param_name, db_field in boolean_filter_map.items():
            value = parse_bool(params.get(param_name))
            if value is not None:
                qs = qs.filter(**{db_field: value})

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
        sort_map = {
            "price_asc": (F("min_variant_price").asc(nulls_last=True), "-is_featured", "-created_at"),
            "price_desc": (F("min_variant_price").desc(nulls_last=True), "-is_featured", "-created_at"),
            "rating": ("-avg_rating", "-is_featured", "-created_at"),
            "popular": ("-review_count", "-is_featured", "-created_at"),
            "oldest": ("created_at",),
            "newest": ("-created_at",),
            "stock": ("-has_stock", "-created_at"),
        }
        qs = qs.order_by(*sort_map.get(sort, ("-is_featured", "-created_at")))

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

        primary_category = _get_or_create_category(product_data.get("primary_category") or {})

        category_items = _unique_keep_order(
            cat
            for item in (product_data.get("categories") or [])
            if (cat := _get_or_create_category(item)) is not None
        )

        product = build_product(product_data, primary_category=primary_category)

        primary_pk = primary_category.pk if primary_category else None
        for category in category_items:
            if category.pk != primary_pk:
                product.categories.add(category)

        build_variants(product, variants_data)
        build_images(product, images_data)
        build_faqs(product, faqs_data)

        serialized = ProductDetailSerializer(product, context=self.get_serializer_context()).data
        return Response(serialized, status=status.HTTP_201_CREATED)