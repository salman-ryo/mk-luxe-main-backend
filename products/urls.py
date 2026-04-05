from django.urls import path
from .views import CategoryViewSet, ProductViewSet

# Bind viewset methods manually
product_list = ProductViewSet.as_view({
    "get": "list",
})

product_detail = ProductViewSet.as_view({
    "get": "retrieve",
})

category_list = CategoryViewSet.as_view({
    "get": "list",
})

category_detail = CategoryViewSet.as_view({
    "get": "retrieve",
})

urlpatterns = [
    # Products
    path("products/", product_list, name="product-list"),
    path("products/<slug:slug>/", product_detail, name="product-detail"),

    # Categories
    path("categories/", category_list, name="category-list"),
    path("categories/<slug:slug>/", category_detail, name="category-detail"),
]