from decimal import Decimal

from django.db.models import Avg, Count, Exists, OuterRef, Q
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Category, Product, ProductVariant
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


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            # Removed .select_related("parent") because parent field no longer exists
            .annotate(product_count=Count("products", distinct=True))
            .order_by("sort_order", "name")
        )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"

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
            )
        )

        params = self.request.query_params

        # Search
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

        # Category filters
        category_slug = params.get("category")
        category_id = params.get("category_id")
        primary_category_slug = params.get("primary_category")
        if category_slug:
            qs = qs.filter(Q(primary_category__slug=category_slug) | Q(categories__slug=category_slug))
        if category_id:
            qs = qs.filter(Q(primary_category__id=category_id) | Q(categories__id=category_id))
        if primary_category_slug:
            qs = qs.filter(primary_category__slug=primary_category_slug)

        # Product flags
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

        # Stock filter
        in_stock = parse_bool(params.get("in_stock"))
        if in_stock is True:
            qs = qs.filter(has_stock=True)
        elif in_stock is False:
            qs = qs.filter(has_stock=False)

        # Variant / material filters
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

        # Price filter uses variant prices
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        if min_price:
            try:
                qs = qs.filter(variants__price__gte=Decimal(min_price))
            except Exception:
                pass
        if max_price:
            try:
                qs = qs.filter(variants__price__lte=Decimal(max_price))
            except Exception:
                pass

        # Status filter if you want to expose drafts internally
        status = params.get("status")
        if status:
            qs = qs.filter(status=status)

        # Sorting
        sort = params.get("sort") or params.get("ordering")
        if sort == "price_asc":
            qs = qs.order_by("variants__price", "-is_featured", "-created_at")
        elif sort == "price_desc":
            qs = qs.order_by("-variants__price", "-is_featured", "-created_at")
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