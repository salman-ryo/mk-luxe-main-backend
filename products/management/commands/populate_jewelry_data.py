from decimal import Decimal
import random
from django.core.management.base import BaseCommand
from products.models import (   # <-- change 'your_app_name' to your actual app
    Category, Product, ProductVariant, ProductImage,
    ProductReview, ProductFAQ, ProductCategory
)


def make_sku(prefix: str, idx: int) -> str:
    return f"{prefix.upper()}-{idx:04d}"


CATEGORIES = [
    {"name": "Necklaces", "description": "Elegant chains, pendants, and statement necklaces."},
    {"name": "Earrings", "description": "Studs, hoops, drop earrings for every occasion."},
    {"name": "Rings", "description": "Stackable rings, solitaires, and cocktail rings."},
    {"name": "Bracelets", "description": "Bangles, cuffs, and charm bracelets."},
    {"name": "Pendants", "description": "Solo pendants on delicate chains."},
    {"name": "Anklets", "description": "Delicate anklets for summer styling."},
    {"name": "Brooches", "description": "Vintage and modern brooches."},
    {"name": "Men's Jewelry", "description": "Minimalist chains, bracelets, and rings for men."},
]

# Product name parts
NECKLACE_NAMES = ["Luna", "Aria", "Zara", "Maya", "Ivy", "Sage", "Nova", "Elara", "Lyra", "Orion"]
EARRING_NAMES = ["Twinkle", "Glimmer", "Dewdrop", "Whisper", "Belle", "Cascade", "Serene", "Petite"]
RING_NAMES = ["Solitaire", "Eternity", "Twist", "Vow", "Promise", "Radiance", "Bloom", "Ember"]
BRACELET_NAMES = ["Tie", "Charm", "Link", "Bangle", "Cuff", "Mesh", "Chain", "Infinity"]
PENDANT_NAMES = ["Tear", "Heart", "Star", "Moon", "Leaf", "Feather", "Key", "Locket"]
ANKLET_NAMES = ["Beach", "Summer", "Barefoot", "Tassel", "Shell", "Pearl"]
BROOCH_NAMES = ["Rose", "Peacock", "Butterfly", "Leaf", "Vintage", "Crystal"]
MENS_NAMES = ["Edge", "Steel", "Titan", "Rugged", "Sleek", "Nomad"]

MATERIALS = ["Brass", "Stainless Steel", "Copper", "Zinc Alloy"]
BASE_METALS = ["Brass", "Copper", "Stainless Steel"]
PLATINGS = ["Gold Plated", "Rose Gold Plated", "Silver Plated", "Ruthenium Plated"]
FINISHES = ["High Polish", "Matte", "Satin", "Hammered", "Textured"]
GEMSTONES = ["Cubic Zirconia", "Labradorite", "Moonstone", "Turquoise", "Onyx", "Pearl", "Amethyst", "None"]
COLORS = ["Gold", "Rose Gold", "Silver", "Black", "White", "Blue", "Green", "Red"]

PRICE_RANGES = [
    (499, 1299),   # low
    (1299, 3499),  # medium
    (3499, 7999),  # high
    (7999, 19999)  # premium
]

def random_price():
    low, high = random.choice(PRICE_RANGES)
    return Decimal(str(random.randint(low, high)))


class Command(BaseCommand):
    help = "Populates the database with realistic jewelry dummy data (flat categories)"

    def handle(self, *args, **options):
        self.stdout.write("Clearing existing data...")
        ProductFAQ.objects.all().delete()
        ProductReview.objects.all().delete()
        ProductImage.objects.all().delete()
        ProductVariant.objects.all().delete()
        ProductCategory.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write("Creating categories...")
        category_objs = {}
        for cat_data in CATEGORIES:
            cat = Category.objects.create(
                name=cat_data["name"],
                description=cat_data["description"],
                is_active=True,
                sort_order=CATEGORIES.index(cat_data)
            )
            category_objs[cat_data["name"]] = cat

        self.stdout.write(f"Created {Category.objects.count()} categories.")

        all_categories = list(category_objs.values())
        product_counter = 1
        products_created = 0

        for category in all_categories:
            self.stdout.write(f"  Generating products for {category.name}...")
            num_products = random.randint(6, 8)

            for i in range(num_products):
                # Generate product name based on category
                if category.name == "Necklaces":
                    name_base = random.choice(NECKLACE_NAMES)
                    name = f"{name_base} Chain Necklace"
                elif category.name == "Earrings":
                    name_base = random.choice(EARRING_NAMES)
                    name = f"{name_base} Earrings"
                elif category.name == "Rings":
                    name_base = random.choice(RING_NAMES)
                    name = f"{name_base} Ring"
                elif category.name == "Bracelets":
                    name_base = random.choice(BRACELET_NAMES)
                    name = f"{name_base} Bracelet"
                elif category.name == "Pendants":
                    name_base = random.choice(PENDANT_NAMES)
                    name = f"{name_base} Pendant"
                elif category.name == "Anklets":
                    name_base = random.choice(ANKLET_NAMES)
                    name = f"{name_base} Anklet"
                elif category.name == "Brooches":
                    name_base = random.choice(BROOCH_NAMES)
                    name = f"{name_base} Brooch"
                else:  # Men's Jewelry
                    name_base = random.choice(MENS_NAMES)
                    name = f"{name_base} {random.choice(['Chain', 'Bracelet', 'Ring'])}"

                # Flags
                is_featured = random.choice([True, False, False])
                is_new = random.choice([True, False, False])
                is_best = random.choice([True, False, False])

                # Material attributes
                material = random.choice(MATERIALS)
                base_metal = random.choice(BASE_METALS)
                plating = random.choice(PLATINGS)
                finish = random.choice(FINISHES)
                gemstone = random.choice(GEMSTONES) if random.random() > 0.5 else ""
                color_family = random.choice(COLORS)

                weight = Decimal(str(round(random.uniform(1.5, 25.0), 2)))
                length = Decimal(str(round(random.uniform(10, 60), 1))) if category.name in ["Necklaces", "Bracelets", "Anklets"] else None
                width = Decimal(str(round(random.uniform(5, 30), 1))) if category.name in ["Earrings", "Pendants", "Brooches"] else None

                short_desc = f"Handcrafted {plating.lower()} {material.lower()} {category.name.lower()} with {gemstone if gemstone else 'a refined finish'}. {finish} design."

                product = Product(
                    name=name,
                    status=Product.Status.ACTIVE,
                    is_active=True,
                    is_featured=is_featured,
                    is_new_arrival=is_new,
                    is_best_seller=is_best,
                    primary_category=category,
                    short_description=short_desc,
                    description=f"<p>{short_desc} This stunning piece is perfect for daily wear or special occasions. {'Hypoallergenic and nickel-free.' if random.random() > 0.7 else ''}</p>",
                    care_instructions="Store in a dry place. Avoid contact with perfumes and lotions. Clean with a soft cloth.",
                    what_you_get=["Jewelry piece", "Eco-friendly pouch", "Care card"],
                    anti_tarnish=random.choice([True, True, False]),
                    water_resistant=random.choice([True, False]),
                    sweat_resistant=random.choice([True, False]),
                    hypoallergenic=random.choice([True, False]),
                    nickel_free=random.choice([True, False]),
                    lightweight=random.choice([True, True, False]),
                    material=material,
                    base_metal=base_metal,
                    plating=plating,
                    finish=finish,
                    gemstone=gemstone,
                    color_family=color_family,
                    specifications={"clasp_type": random.choice(["Lobster", "Toggle", "Magnetic"]) if category.name in ["Necklaces", "Bracelets"] else ""},
                    seo_title=name,
                    seo_description=short_desc[:320],
                    warranty_months=6,
                    return_window_days=15,
                    delivery_note="Ships within 2-3 business days",
                    is_available_online=True,
                    is_available_at_stall=random.choice([True, False]),
                    stall_note="Visit our stall at the local pop-up market" if random.random() > 0.7 else "",
                    weight_grams=weight,
                    length_mm=length,
                    width_mm=width,
                )
                product.save()

                # Optionally add extra categories (random 0–2 other categories)
                other_cats = [c for c in all_categories if c != category]
                random.shuffle(other_cats)
                for extra in other_cats[:random.randint(0, 2)]:
                    ProductCategory.objects.create(product=product, category=extra)

                # Create variants (1–3)
                variant_count = random.randint(1, 3)
                variants = []
                default_set = False
                for v_idx in range(variant_count):
                    if variant_count > 1:
                        if category.name == "Rings":
                            size = random.choice(["6", "7", "8", "9", "10"])
                            color_variant = random.choice(["Gold", "Rose Gold", "Silver"])
                        elif category.name in ["Bracelets", "Anklets"]:
                            size = random.choice(["S", "M", "L"])
                            color_variant = random.choice(["Gold", "Silver"])
                        else:
                            size = ""
                            color_variant = color_family if v_idx == 0 else random.choice(COLORS)
                    else:
                        size = ""
                        color_variant = color_family

                    price = random_price()
                    compare_at = price + Decimal(str(random.randint(200, 1500))) if random.random() > 0.3 else None
                    stock = random.randint(5, 150)
                    reserved = random.randint(0, min(stock, 10))
                    is_default = not default_set and v_idx == 0
                    if is_default:
                        default_set = True

                    variant = ProductVariant(
                        product=product,
                        name=f"{product.name} - {color_variant}" if color_variant else product.name,
                        sku=make_sku(category.name[:3].upper(), product_counter * 10 + v_idx),
                        material=material,
                        color=color_variant,
                        size=size,
                        length_mm=length,
                        width_mm=width,
                        weight_grams=weight,
                        price=price,
                        compare_at_price=compare_at,
                        stock_quantity=stock,
                        reserved_quantity=reserved,
                        low_stock_threshold=3,
                        is_active=True,
                        is_default=is_default,
                        attributes={"season": random.choice(["Spring", "Summer", "All Year"])},
                    )
                    variant.save()
                    variants.append(variant)

                # Update product price range
                prices = [v.price for v in variants if v.price is not None]
                if prices:
                    product.price_from = min(prices)
                    product.price_to = max(prices) if len(set(prices)) > 1 else None
                    product.save(update_fields=['price_from', 'price_to'])

                # Images (2–4)
                num_images = random.randint(2, 4)
                for img_idx in range(num_images):
                    img_url = f"https://picsum.photos/id/{random.randint(1, 200)}/800/800?grayscale" if random.random() > 0.5 else \
                              f"https://placekitten.com/800/800?image={random.randint(1, 16)}"
                    ProductImage.objects.create(
                        product=product,
                        variant=variants[0] if img_idx == 0 and variants else None,
                        image_url=img_url,
                        alt_text=f"{product.name} - view {img_idx+1}",
                        is_primary=(img_idx == 0),
                        sort_order=img_idx
                    )

                # Reviews (2–5)
                review_texts = [
                    "Absolutely love this piece! Very elegant.",
                    "Good quality, but slightly smaller than expected.",
                    "Stunning design, got many compliments.",
                    "Shipping was fast and packaging is lovely.",
                    "The plating started fading after a month, disappointing.",
                    "Beautiful and exactly as shown.",
                    "Very lightweight and comfortable to wear all day.",
                    "Great value for money.",
                ]
                num_reviews = random.randint(2, 5)
                for _ in range(num_reviews):
                    rating = random.randint(3, 5) if random.random() > 0.2 else random.randint(1, 2)
                    ProductReview.objects.create(
                        product=product,
                        name=random.choice(["Priya", "Amit", "Neha", "Rahul", "Sneha", "Vikram"]),
                        email="customer@example.com",
                        rating=rating,
                        title="Great product!" if rating >= 4 else "Okay but not great",
                        comment=random.choice(review_texts),
                        is_verified_purchase=random.choice([True, True, False]),
                        is_approved=True
                    )

                # FAQs (1–3)
                faq_questions = [
                    "Is this hypoallergenic?",
                    "Can I wear it every day?",
                    "Does it tarnish?",
                    "What is the return policy?",
                    "Is the gemstone real?",
                ]
                faq_answers = [
                    "Yes, it is nickel-free and hypoallergenic." if product.hypoallergenic else "It may contain nickel, please check materials.",
                    "Absolutely! It's designed for daily wear.",
                    "Our anti-tarnish coating keeps it shining for months." if product.anti_tarnish else "With proper care, it will last long.",
                    "You can return within 15 days of delivery.",
                    "The gemstone is lab-created / high-quality cubic zirconia.",
                ]
                num_faqs = random.randint(1, 3)
                for faq_idx in range(num_faqs):
                    ProductFAQ.objects.create(
                        product=product,
                        question=random.choice(faq_questions),
                        answer=random.choice(faq_answers),
                        sort_order=faq_idx,
                        is_active=True
                    )

                product_counter += 1
                products_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {products_created} products, "
            f"{ProductVariant.objects.count()} variants, "
            f"{ProductImage.objects.count()} images, "
            f"{ProductReview.objects.count()} reviews, "
            f"{ProductFAQ.objects.count()} FAQs."
        ))