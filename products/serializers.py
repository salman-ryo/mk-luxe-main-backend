from django.db.models import Avg, Count
from rest_framework import serializers

from .models import Category, Product, ProductFAQ, ProductImage, ProductReview, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "image_url",
            # "parent",  # REMOVED – parent field no longer exists in Category model
            "is_active",
            "sort_order",
            "product_count",
        )


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = (
            "id",
            "image_url",
            "alt_text",
            "is_primary",
            "sort_order",
            "variant",
        )


class ProductVariantSerializer(serializers.ModelSerializer):
    available_stock = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "name",
            "sku",
            "barcode",
            "material",
            "color",
            "size",
            "length_mm",
            "width_mm",
            "weight_grams",
            "price",
            "compare_at_price",
            "stock_quantity",
            "reserved_quantity",
            "available_stock",
            "low_stock_threshold",
            "is_low_stock",
            "is_active",
            "is_default",
            "attributes",
        )


class ProductFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFAQ
        fields = (
            "id",
            "question",
            "answer",
            "sort_order",
            "is_active",
        )


class ProductReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = (
            "id",
            "name",
            "rating",
            "title",
            "comment",
            "is_verified_purchase",
            "created_at",
        )


class ProductListSerializer(serializers.ModelSerializer):
    primary_category = CategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    has_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "primary_category",
            "primary_image",
            "short_description",
            "anti_tarnish",
            "is_featured",
            "is_new_arrival",
            "is_best_seller",
            "price_from",
            "price_to",
            "price_display",
            "currency",
            "avg_rating",
            "review_count",
            "has_stock",
            "is_available_online",
        )

    def get_primary_image(self, obj):
        images = getattr(obj, "images_cache", None) or list(obj.images.all())
        if not images:
            return None

        primary = next((img for img in images if img.is_primary), images[0])
        return ProductImageSerializer(primary).data

    def get_price_display(self, obj):
        return obj.price_range


class ProductDetailSerializer(serializers.ModelSerializer):
    primary_category = CategorySerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    faqs = ProductFAQSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    price_display = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "primary_category",
            "categories",
            "short_description",
            "description",
            "care_instructions",
            "what_you_get",
            "anti_tarnish",
            "water_resistant",
            "sweat_resistant",
            "hypoallergenic",
            "nickel_free",
            "lightweight",
            "material",
            "base_metal",
            "plating",
            "finish",
            "gemstone",
            "color_family",
            "specifications",
            "seo_title",
            "seo_description",
            "price_from",
            "price_to",
            "price_display",
            "currency",
            "warranty_months",
            "return_window_days",
            "delivery_note",
            "is_available_online",
            "is_available_at_stall",
            "stall_note",
            "cover_image_url",
            "alt_text",
            "weight_grams",
            "length_mm",
            "width_mm",
            "avg_rating",
            "review_count",
            "variants",
            "images",
            "faqs",
            "reviews",
            "created_at",
            "updated_at",
        )

    def get_reviews(self, obj):
        approved_reviews = obj.reviews.filter(is_approved=True).order_by("-created_at")[:6]
        return ProductReviewSerializer(approved_reviews, many=True).data

    def get_price_display(self, obj):
        return obj.price_range