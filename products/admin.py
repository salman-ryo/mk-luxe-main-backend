from django.contrib import admin

from .models import (
    Category,
    Product,
    ProductCategory,
    ProductFAQ,
    ProductImage,
    ProductReview,
    ProductVariant,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "name",
        "sku",
        "barcode",
        "material",
        "color",
        "size",
        "price",
        "compare_at_price",
        "stock_quantity",
        "reserved_quantity",
        "low_stock_threshold",
        "is_default",
        "is_active",
    )
    show_change_link = True


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image_url", "alt_text", "is_primary", "sort_order", "variant")
    show_change_link = True


class ProductFAQInline(admin.TabularInline):
    model = ProductFAQ
    extra = 1
    fields = ("question", "answer", "sort_order", "is_active")
    show_change_link = True


class ProductCategoryInline(admin.TabularInline):
    model = ProductCategory
    extra = 1
    autocomplete_fields = ("category",)
    show_change_link = False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order", "slug")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "status",
        "primary_category",
        "is_active",
        "is_featured",
        "anti_tarnish",
        "price_from",
        "price_to",
        "created_at",
    )
    list_filter = (
        "status",
        "is_active",
        "is_featured",
        "is_new_arrival",
        "is_best_seller",
        "anti_tarnish",
        "water_resistant",
        "sweat_resistant",
        "hypoallergenic",
        "nickel_free",
        "is_available_online",
        "is_available_at_stall",
        "primary_category",
    )
    search_fields = ("name", "slug", "short_description", "description", "material", "base_metal", "plating", "finish")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("primary_category",)
    inlines = (ProductVariantInline, ProductImageInline, ProductFAQInline, ProductCategoryInline)
    ordering = ("-is_featured", "-created_at")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Basic", {
            "fields": ("name", "slug", "status", "is_active", "is_featured", "is_new_arrival", "is_best_seller")
        }),
        ("Categories", {
            "fields": ("primary_category",)
        }),
        ("Descriptions", {
            "fields": ("short_description", "description", "care_instructions", "what_you_get")
        }),
        ("Jewelry traits", {
            "fields": (
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
            )
        }),
        ("SEO", {
            "fields": ("seo_title", "seo_description")
        }),
        ("Listing price", {
            "fields": ("price_from", "price_to", "currency")
        }),
        ("Operations", {
            "fields": ("warranty_months", "return_window_days", "delivery_note")
        }),
        ("Stall & online", {
            "fields": ("is_available_online", "is_available_at_stall", "stall_note")
        }),
        ("Media", {
            "fields": ("cover_image_url", "alt_text")
        }),
        ("Measurements", {
            "fields": ("weight_grams", "length_mm", "width_mm")
        }),
        ("System", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "sku",
        "material",
        "color",
        "size",
        "price",
        "stock_quantity",
        "reserved_quantity",
        "is_default",
        "is_active",
    )
    list_filter = ("is_active", "is_default", "material", "color")
    search_fields = ("product__name", "sku", "barcode", "material", "color", "size")
    autocomplete_fields = ("product",)
    ordering = ("product", "-is_default", "id")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "variant", "is_primary", "sort_order", "image_url")
    list_filter = ("is_primary",)
    search_fields = ("product__name", "variant__sku", "image_url", "alt_text")
    autocomplete_fields = ("product", "variant")
    ordering = ("product", "sort_order")


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "rating", "is_verified_purchase", "is_approved", "created_at")
    list_filter = ("rating", "is_verified_purchase", "is_approved")
    search_fields = ("product__name", "name", "email", "title", "comment")
    autocomplete_fields = ("product",)
    ordering = ("-created_at",)


@admin.register(ProductFAQ)
class ProductFAQAdmin(admin.ModelAdmin):
    list_display = ("product", "question", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("product__name", "question", "answer")
    autocomplete_fields = ("product",)
    ordering = ("product", "sort_order")