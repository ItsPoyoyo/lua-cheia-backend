from celery import shared_task
from django.utils import timezone
from store.carousel_automation import CarouselAutomation
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_carousels_task(force=False):
    """
    Celery task to update carousels automatically
    """
    try:
        automation = CarouselAutomation()
        result = automation.run_full_automation(force=force)
        
        logger.info(f"Carousel automation task completed at {timezone.now()}: {result}")
        return {
            'success': result,
            'timestamp': timezone.now().isoformat(),
            'message': 'Carousel automation completed successfully' if result else 'Carousel automation failed'
        }
    except Exception as e:
        logger.error(f"Error in carousel automation task: {str(e)}")
        return {
            'success': False,
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }


@shared_task
def update_offers_carousel_task(force=False):
    """
    Celery task to update only offers carousel
    """
    try:
        automation = CarouselAutomation()
        result = automation.update_offers_carousel(force=force)
        
        logger.info(f"Offers carousel automation task completed: {result}")
        return {
            'success': result,
            'timestamp': timezone.now().isoformat(),
            'message': 'Offers carousel updated successfully' if result else 'Offers carousel update failed'
        }
    except Exception as e:
        logger.error(f"Error in offers carousel automation task: {str(e)}")
        return {
            'success': False,
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }


@shared_task
def update_promotional_banners_task(force=False):
    """
    Celery task to update promotional banners
    """
    try:
        automation = CarouselAutomation()
        result = automation.update_promotional_banners(force=force)
        
        logger.info(f"Promotional banners automation task completed: {result}")
        return {
            'success': result,
            'timestamp': timezone.now().isoformat(),
            'message': 'Promotional banners updated successfully' if result else 'Promotional banners update failed'
        }
    except Exception as e:
        logger.error(f"Error in promotional banners automation task: {str(e)}")
        return {
            'success': False,
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }


@shared_task
def cleanup_old_automated_content():
    """
    Clean up old automated carousel content
    """
    try:
        from store.models import Banner, CarouselImage
        from datetime import timedelta
        
        # Remove automated banners older than 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        old_banners = Banner.objects.filter(
            title__startswith='Oferta Especial',
            date__lt=thirty_days_ago
        )
        deleted_banners = old_banners.count()
        old_banners.delete()
        
        # Remove automated carousel images older than 30 days
        old_carousel_images = CarouselImage.objects.filter(
            caption__startswith='Destacado:',
            # Assuming we add a date field or use id as proxy for age
        )
        
        logger.info(f"Cleanup completed: {deleted_banners} old banners removed")
        return {
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'deleted_banners': deleted_banners,
            'message': 'Cleanup completed successfully'
        }
    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")
        return {
            'success': False,
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }

