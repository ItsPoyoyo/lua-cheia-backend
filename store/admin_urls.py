from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.simple_dashboard, name='simple_dashboard'),
    path('analytics/', admin_views.sales_analytics, name='sales_analytics'),
    path('sales/', admin_views.sales_dashboard, name='sales_dashboard'),
]

