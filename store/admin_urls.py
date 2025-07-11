from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.sales_dashboard, name='admin:sales_dashboard'),
    path('analytics/', admin_views.sales_analytics, name='admin:sales_analytics'),
]

