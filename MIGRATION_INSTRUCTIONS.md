# Migration Instructions for Lua Cheia Store

## Important: Database Migration Required

This update includes a new **Most Viewed Carousel** feature that requires a database migration.

### Step 1: Apply the Migration

Run the following command in your backend directory:

```bash
python manage.py migrate
```

### Step 2: Setup Most Viewed Carousel (Recommended)

**Easy way using management command:**

```bash
python manage.py setup_most_viewed_carousel
```

This will automatically:
- Create a "Mais Vendidos" carousel
- Add initial products to it
- Configure it with optimal settings

**Manual way (if you prefer):**

To create an initial most viewed carousel manually, run:

```bash
python manage.py shell
```

Then execute the following Python code:

```python
from store.models import MostViewedCarousel, Product

# Create a most viewed carousel
carousel = MostViewedCarousel.objects.create(
    title="Mais Vendidos",
    is_active=True,
    auto_update=True,
    max_products=10
)

# Add some products to it (optional - it will auto-populate based on views)
products = Product.objects.filter(status="published")[:5]
carousel.products.set(products)

print("Most Viewed Carousel created successfully!")
exit()
```

### Step 3: Verify in Admin Panel

1. Go to your admin panel: `http://localhost:8000/admin/`
2. Look for "Most Viewed Carousels" in the Store section
3. You should now be able to manage the carousel products manually

### Troubleshooting

If you get a "no such table" error:
1. Make sure you've run `python manage.py migrate`
2. Check that the migration file `0036_mostviewedcarousel.py` exists in `store/migrations/`
3. If the migration doesn't exist, run `python manage.py makemigrations store` first

### Features

- **Auto-Update**: The carousel automatically updates with the most viewed products
- **Manual Management**: You can manually add/remove products in the admin panel
- **Configurable**: Set the maximum number of products to display
- **Active/Inactive**: Enable or disable the carousel as needed

The carousel will now be visible in your admin panel and you can manage it just like any other model!

