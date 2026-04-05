from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def unique_slug_for(model_class: type[models.Model], value: str, exclude_pk: Any = None) -> str:
    """
    Generate a unique slug for a model instance.
    """
    base_slug = slugify(value)[:240] or "item"
    slug = base_slug
    counter = 2

    qs = model_class.objects.all()
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)

    while qs.filter(slug=slug).exists():
        suffix = f"-{counter}"
        slug = f"{base_slug[: 240 - len(suffix)]}{suffix}"
        counter += 1

    return slug


class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "sort_order"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug_for(Category, self.name, self.pk)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("category-detail", kwargs={"slug": self.slug})


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)

    primary_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_products",
    )
    categories = models.ManyToManyField(Category, through="ProductCategory", blank=True, related_name="products")

    short_description = models.CharField(max_length=280, blank=True)
    description = models.TextField(blank=True)
    care_instructions = models.TextField(blank=True)
    what_you_get = models.JSONField(default=list, blank=True)

    anti_tarnish = models.BooleanField(default=True, db_index=True)
    water_resistant = models.BooleanField(default=False)
    sweat_resistant = models.BooleanField(default=False)
    hypoallergenic = models.BooleanField(default=False)
    nickel_free = models.BooleanField(default=False)
    lightweight = models.BooleanField(default=True)

    material = models.CharField(max_length=120, blank=True)
    base_metal = models.CharField(max_length=120, blank=True)
    plating = models.CharField(max_length=120, blank=True)
    finish = models.CharField(max_length=120, blank=True)
    gemstone = models.CharField(max_length=120, blank=True)
    color_family = models.CharField(max_length=80, blank=True)

    specifications = models.JSONField(default=dict, blank=True)

    seo_title = models.CharField(max_length=160, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)

    # Denormalized for listings; actual selling price comes from variants
    price_from = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_to = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="INR")

    warranty_months = models.PositiveIntegerField(null=True, blank=True)
    return_window_days = models.PositiveIntegerField(null=True, blank=True)
    delivery_note = models.CharField(max_length=255, blank=True)

    is_available_online = models.BooleanField(default=True, db_index=True)
    is_available_at_stall = models.BooleanField(default=True)
    stall_note = models.CharField(max_length=255, blank=True)

    cover_image_url = models.URLField(max_length=500, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)

    weight_grams = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    length_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    width_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status", "is_active"]),
            models.Index(fields=["primary_category", "is_active"]),
            models.Index(fields=["anti_tarnish", "is_active"]),
            models.Index(fields=["is_featured", "is_active"]),
            models.Index(fields=["is_new_arrival", "is_active"]),
            models.Index(fields=["is_best_seller", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug_for(Product, self.name, self.pk)

        if not self.seo_title:
            self.seo_title = self.name

        if not self.seo_description and self.short_description:
            self.seo_description = self.short_description[:320]

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.price_from is not None and self.price_to is not None and self.price_from > self.price_to:
            raise ValidationError({"price_to": "price_to must be greater than or equal to price_from."})

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        if self.primary_category:
            return reverse(
                "product-detail",
                kwargs={"category_slug": self.primary_category.slug, "slug": self.slug},
            )
        return reverse("product-detail-no-category", kwargs={"slug": self.slug})

    @property
    def price_range(self):
        if self.price_from is None and self.price_to is None:
            return None
        if self.price_from is not None and self.price_to is not None and self.price_from != self.price_to:
            return f"{self.currency} {self.price_from} - {self.price_to}"
        value = self.price_from if self.price_from is not None else self.price_to
        return f"{self.currency} {value}"


class ProductCategory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "category"], name="uniq_product_category_link"),
        ]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} -> {self.category.name}"


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")

    name = models.CharField(max_length=180, blank=True)
    sku = models.CharField(max_length=80, unique=True, null=True, blank=True, db_index=True)
    barcode = models.CharField(max_length=120, null=True, blank=True, db_index=True)

    material = models.CharField(max_length=120, blank=True)
    color = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=80, blank=True)
    length_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    width_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    weight_grams = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(default=False)

    attributes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-is_default", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_default=True),
                name="uniq_default_variant_per_product",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["barcode"]),
            models.Index(fields=["is_default", "is_active"]),
            models.Index(fields=["price"]),
        ]

    def clean(self):
        super().clean()
        if self.price is not None and self.price < Decimal("0"):
            raise ValidationError({"price": "Price cannot be negative."})
        if self.compare_at_price is not None and self.price is not None and self.compare_at_price < self.price:
            raise ValidationError({"compare_at_price": "compare_at_price must be >= price."})
        if self.reserved_quantity > self.stock_quantity:
            raise ValidationError({"reserved_quantity": "Reserved quantity cannot exceed stock quantity."})

    @property
    def available_stock(self) -> int:
        return max(self.stock_quantity - self.reserved_quantity, 0)

    @property
    def is_low_stock(self) -> bool:
        return self.available_stock <= self.low_stock_threshold

    def __str__(self) -> str:
        parts = [self.product.name]
        if self.material:
            parts.append(self.material)
        if self.color:
            parts.append(self.color)
        if self.size:
            parts.append(self.size)
        return " - ".join(parts)


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="images",
    )
    image_url = models.URLField(max_length=500)
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["product", "is_primary"]),
            models.Index(fields=["variant", "is_primary"]),
            models.Index(fields=["sort_order"]),
        ]

    def __str__(self) -> str:
        return f"Image for {self.product.name}"


class ProductReview(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=180, blank=True)
    comment = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "is_approved"]),
            models.Index(fields=["rating"]),
        ]

    def clean(self):
        super().clean()
        if not 1 <= self.rating <= 5:
            raise ValidationError({"rating": "Rating must be between 1 and 5."})

    def __str__(self) -> str:
        return f"{self.product.name} - {self.rating} stars"


class ProductFAQ(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=255)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["sort_order"]),
        ]

    def __str__(self) -> str:
        return self.question