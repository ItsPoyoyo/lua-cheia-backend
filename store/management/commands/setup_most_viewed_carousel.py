from django.core.management.base import BaseCommand
from store.models import MostViewedCarousel, Product
from django.db import transaction

class Command(BaseCommand):
    help = 'Setup the Most Viewed Carousel with initial data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--title',
            type=str,
            default='Mais Vendidos',
            help='Title for the carousel'
        )
        parser.add_argument(
            '--max-products',
            type=int,
            default=10,
            help='Maximum number of products to display'
        )

    def handle(self, *args, **options):
        title = options['title']
        max_products = options['max_products']

        try:
            with transaction.atomic():
                # Check if carousel already exists
                carousel, created = MostViewedCarousel.objects.get_or_create(
                    title=title,
                    defaults={
                        'is_active': True,
                        'auto_update': True,
                        'max_products': max_products
                    }
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Created new Most Viewed Carousel: "{title}"')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Most Viewed Carousel "{title}" already exists')
                    )

                # Add some initial products if the carousel is empty
                if carousel.products.count() == 0:
                    # Get published products, preferably with higher view counts
                    products = Product.objects.filter(
                        status="published",
                        in_stock=True
                    ).order_by('-views', '-date')[:max_products]

                    if products.exists():
                        carousel.products.set(products)
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Added {products.count()} products to the carousel')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING('⚠️  No published products found to add to carousel')
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Carousel already has {carousel.products.count()} products')
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n🎉 Most Viewed Carousel setup complete!'
                        f'\n📊 Title: {carousel.title}'
                        f'\n🔢 Max Products: {carousel.max_products}'
                        f'\n📦 Current Products: {carousel.products.count()}'
                        f'\n🔄 Auto Update: {"Enabled" if carousel.auto_update else "Disabled"}'
                        f'\n✅ Status: {"Active" if carousel.is_active else "Inactive"}'
                        f'\n\n🌐 You can now manage this carousel in the admin panel!'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error setting up Most Viewed Carousel: {str(e)}')
            )

