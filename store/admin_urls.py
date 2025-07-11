from django.urls import path

from . import admin_views

urlpatterns = [
    path('', admin_views.sales_dashboard, name='sales_dashboard'),
    path('analytics/', admin_views.sales_analytics, name='sales_analytics'),

]

