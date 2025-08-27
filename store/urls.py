from django.urls import path, include
from . import views
from .views import (
    health_check,
)

app_name = 'store'

urlpatterns = [
    path('admin/live-orders/', views.live_orders_feed, name='live_orders_feed'),
    path('admin/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('admin/performance-metrics/', views.performance_metrics, name='performance_metrics'),
    path('whatsapp-checkout/', views.whatsapp_checkout, name='whatsapp_checkout'),
    path('admin/', include('store.admin_urls')),  # Include admin URLs for sales analytics
    path('test-media/', views.test_media, name='test_media'),  # Test media serving
    path('media/<path:file_path>', views.serve_media_file, name='serve_media_file'),  # Custom media serving
    # Health check for Railway
    path('health/', health_check, name='health_check'),
]
