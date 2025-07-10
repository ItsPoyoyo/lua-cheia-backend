from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from store.models import Product, OffersCarousel, CarouselImage, Banner
from store.carousel_automation import CarouselAutomation


class Command(BaseCommand):
    help = 'Automatically update carousel content based on product performance and trends'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['all', 'offers', 'banners', 'images'],
            default='all',
            help='Type of carousel to update'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if recently updated'
        )

    def handle(self, *args, **options):
        automation = CarouselAutomation()
        
        self.stdout.write(self.style.SUCCESS('Starting carousel automation...'))
        
        if options['type'] in ['all', 'offers']:
            self.stdout.write('Updating offers carousel...')
            automation.update_offers_carousel(force=options['force'])
            
        if options['type'] in ['all', 'banners']:
            self.stdout.write('Updating promotional banners...')
            automation.update_promotional_banners(force=options['force'])
            
        if options['type'] in ['all', 'images']:
            self.stdout.write('Updating carousel images...')
            automation.update_carousel_images(force=options['force'])
        
        self.stdout.write(
            self.style.SUCCESS('Carousel automation completed successfully!')
        )

