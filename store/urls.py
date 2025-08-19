from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('admin/live-orders/', views.live_orders_feed, name='live_orders_feed'),
    path('admin/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('admin/performance-metrics/', views.performance_metrics, name='performance_metrics'),
    path('whatsapp-checkout/', views.whatsapp_checkout, name='whatsapp_checkout'),
]
