import logging
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.files.base import ContentFile
from django.conf import settings
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import os

from store.models import (
    Product, OffersCarousel, CarouselImage, Banner, 
    CartOrderItem, Review, Category
)

logger = logging.getLogger(__name__)


class CarouselAutomation:
    """
    Automated carousel management system for LuaCheia
    """
    
    def __init__(self):
        self.last_update_threshold = timedelta(hours=6)  # Update every 6 hours
    
    def should_update(self, last_update, force=False):
        """Check if carousel should be updated"""
        if force:
            return True
        if not last_update:
            return True
        return timezone.now() - last_update > self.last_update_threshold
    
    def get_trending_products(self, limit=10):
        """Get trending products based on recent orders and views"""
        # Get products with most orders in last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        trending = Product.objects.filter(
            status='published',
            in_stock=True,
            stock_qty__gt=0
        ).annotate(
            recent_orders=Count(
                'cartorderitem',
                filter=Q(cartorderitem__order__date__gte=thirty_days_ago)
            ),
            total_revenue=Sum(
                'cartorderitem__total',
                filter=Q(cartorderitem__order__date__gte=thirty_days_ago)
            ),
            avg_rating=Avg('review__rating')
        ).filter(
            recent_orders__gt=0
        ).order_by('-recent_orders', '-total_revenue', '-views')[:limit]
        
        return trending
    
    def get_best_selling_products(self, limit=10):
        """Get best selling products of all time"""
        return Product.objects.filter(
            status='published',
            in_stock=True,
            stock_qty__gt=0
        ).annotate(
            total_orders=Count('cartorderitem'),
            total_revenue=Sum('cartorderitem__total')
        ).filter(
            total_orders__gt=0
        ).order_by('-total_orders', '-total_revenue')[:limit]
    
    def get_new_arrivals(self, limit=10):
        """Get newest products"""
        return Product.objects.filter(
            status='published',
            in_stock=True,
            stock_qty__gt=0
        ).order_by('-date')[:limit]
    
    def get_discounted_products(self, limit=10):
        """Get products with highest discounts"""
        return Product.objects.filter(
            status='published',
            in_stock=True,
            stock_qty__gt=0,
            old_price__gt=0
        ).extra(
            select={'discount_percent': '((old_price - price) / old_price) * 100'}
        ).order_by('-discount_percent')[:limit]
    
    def update_offers_carousel(self, force=False):
        """Update offers carousel with trending and discounted products"""
        try:
            # Get or create different carousel types
            carousels_config = [
                {
                    'title': 'Productos Más Vendidos',
                    'products': self.get_best_selling_products(8),
                    'identifier': 'best_selling'
                },
                {
                    'title': 'Tendencias Actuales',
                    'products': self.get_trending_products(8),
                    'identifier': 'trending'
                },
                {
                    'title': 'Nuevos Arrivals',
                    'products': self.get_new_arrivals(8),
                    'identifier': 'new_arrivals'
                },
                {
                    'title': 'Ofertas Especiales',
                    'products': self.get_discounted_products(8),
                    'identifier': 'special_offers'
                }
            ]
            
            for config in carousels_config:
                carousel, created = OffersCarousel.objects.get_or_create(
                    title=config['title'],
                    defaults={'is_active': True}
                )
                
                if created or force or self.should_update(carousel.date if hasattr(carousel, 'date') else None):
                    # Clear existing products
                    carousel.products.clear()
                    
                    # Add new products
                    for product in config['products']:
                        carousel.products.add(product)
                    
                    carousel.is_active = True
                    carousel.save()
                    
                    logger.info(f"Updated carousel '{config['title']}' with {len(config['products'])} products")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating offers carousel: {str(e)}")
            return False
    
    def create_promotional_banner(self, product, banner_type='discount'):
        """Create a promotional banner image for a product"""
        try:
            # Create a banner image
            width, height = 800, 400
            image = Image.new('RGB', (width, height), color='#1f2937')
            draw = ImageDraw.Draw(image)
            
            # Try to load a font, fallback to default if not available
            try:
                title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 48)
                subtitle_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
            
            # Add text based on banner type
            if banner_type == 'discount' and product.old_price and product.old_price > product.price:
                discount_percent = int(((product.old_price - product.price) / product.old_price) * 100)
                main_text = f"{discount_percent}% OFF"
                subtitle_text = product.title[:30] + "..." if len(product.title) > 30 else product.title
            else:
                main_text = "NUEVO"
                subtitle_text = product.title[:30] + "..." if len(product.title) > 30 else product.title
            
            # Draw text
            draw.text((50, 150), main_text, fill='#ffffff', font=title_font)
            draw.text((50, 220), subtitle_text, fill='#e5e7eb', font=subtitle_font)
            draw.text((50, 260), f"${product.price}", fill='#10b981', font=subtitle_font)
            
            # Save to BytesIO
            img_io = io.BytesIO()
            image.save(img_io, format='PNG')
            img_io.seek(0)
            
            return ContentFile(img_io.getvalue(), name=f'banner_{product.id}_{banner_type}.png')
            
        except Exception as e:
            logger.error(f"Error creating banner for product {product.id}: {str(e)}")
            return None
    
    def update_promotional_banners(self, force=False):
        """Update promotional banners with current offers"""
        try:
            # Get products for banners
            discount_products = self.get_discounted_products(3)
            trending_products = self.get_trending_products(2)
            
            # Create banners for discounted products
            for i, product in enumerate(discount_products):
                banner_title = f"Oferta Especial - {product.title}"
                
                banner, created = Banner.objects.get_or_create(
                    title=banner_title,
                    defaults={
                        'link': f'/product/{product.slug}/',
                        'is_active': True
                    }
                )
                
                if created or force:
                    # Create banner image
                    banner_image = self.create_promotional_banner(product, 'discount')
                    if banner_image:
                        banner.image.save(
                            f'auto_banner_discount_{product.id}.png',
                            banner_image,
                            save=True
                        )
                        logger.info(f"Created discount banner for {product.title}")
            
            # Create banners for trending products
            for i, product in enumerate(trending_products):
                banner_title = f"Tendencia - {product.title}"
                
                banner, created = Banner.objects.get_or_create(
                    title=banner_title,
                    defaults={
                        'link': f'/product/{product.slug}/',
                        'is_active': True
                    }
                )
                
                if created or force:
                    # Create banner image
                    banner_image = self.create_promotional_banner(product, 'trending')
                    if banner_image:
                        banner.image.save(
                            f'auto_banner_trending_{product.id}.png',
                            banner_image,
                            save=True
                        )
                        logger.info(f"Created trending banner for {product.title}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating promotional banners: {str(e)}")
            return False
    
    def update_carousel_images(self, force=False):
        """Update carousel images with product highlights"""
        try:
            # Get featured products for carousel
            featured_products = Product.objects.filter(
                status='published',
                featured=True,
                in_stock=True,
                stock_qty__gt=0
            ).order_by('-views')[:5]
            
            if not featured_products:
                # Fallback to trending products
                featured_products = self.get_trending_products(5)
            
            for i, product in enumerate(featured_products):
                caption = f"Destacado: {product.title}"
                
                carousel_image, created = CarouselImage.objects.get_or_create(
                    caption=caption,
                    defaults={'is_active': True}
                )
                
                if created or force:
                    # Use product image or create a promotional image
                    if product.image:
                        try:
                            # Copy product image to carousel
                            response = requests.get(product.image.url)
                            if response.status_code == 200:
                                carousel_image.image.save(
                                    f'carousel_product_{product.id}.jpg',
                                    ContentFile(response.content),
                                    save=True
                                )
                                logger.info(f"Updated carousel image for {product.title}")
                        except Exception as e:
                            logger.error(f"Error copying image for {product.title}: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating carousel images: {str(e)}")
            return False
    
    def run_full_automation(self, force=False):
        """Run complete carousel automation"""
        results = {
            'offers': self.update_offers_carousel(force),
            'banners': self.update_promotional_banners(force),
            'images': self.update_carousel_images(force)
        }
        
        logger.info(f"Carousel automation completed: {results}")
        return all(results.values())

