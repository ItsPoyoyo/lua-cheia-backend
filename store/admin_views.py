from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from store.models import CartOrder, CartOrderItem


@staff_member_required
def sales_dashboard(request):
    """
    Sales dashboard view for admin panel
    """
    # Get date range (default to last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get date range from request if provided
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Filter orders by date range and payment status
    orders = CartOrder.objects.filter(
        date__date__range=[start_date, end_date],
        payment_status='paid'
    )
    
    # Calculate total sales metrics
    total_sales = orders.aggregate(
        total_amount=Sum('total'),
        total_orders=Count('id')
    )
    
    total_amount = total_sales['total_amount'] or Decimal('0.00')
    total_orders = total_sales['total_orders'] or 0
    
    # Calculate average order value
    avg_order_value = total_amount / total_orders if total_orders > 0 else Decimal('0.00')
    
    # Daily sales data for chart
    daily_sales = orders.annotate(
        date_only=TruncDate('date')
    ).values('date_only').annotate(
        daily_total=Sum('total'),
        daily_orders=Count('id')
    ).order_by('date_only')
    
    # Prepare chart data
    chart_dates = []
    chart_amounts = []
    chart_orders = []
    
    for sale in daily_sales:
        chart_dates.append(sale['date_only'].strftime('%Y-%m-%d'))
        chart_amounts.append(float(sale['daily_total']))
        chart_orders.append(sale['daily_orders'])
    
    # Monthly sales data
    monthly_sales = orders.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        monthly_total=Sum('total'),
        monthly_orders=Count('id')
    ).order_by('month')
    
    # Top selling products
    top_products = CartOrderItem.objects.filter(
        order__date__date__range=[start_date, end_date],
        order__payment_status='paid'
    ).values(
        'product__title'
    ).annotate(
        total_sold=Sum('qty'),
        total_revenue=Sum('total')
    ).order_by('-total_sold')[:10]
    
    # Recent orders
    recent_orders = orders.order_by('-date')[:10]
    
    context = {
        'title': 'Sales Dashboard',
        'start_date': start_date,
        'end_date': end_date,
        'total_amount': total_amount,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'chart_dates': json.dumps(chart_dates),
        'chart_amounts': json.dumps(chart_amounts),
        'chart_orders': json.dumps(chart_orders),
        'daily_sales': daily_sales,
        'monthly_sales': monthly_sales,
        'top_products': top_products,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'admin/sales_dashboard.html', context)


@staff_member_required
def sales_analytics(request):
    """
    Advanced sales analytics view
    """
    # Get all paid orders
    orders = CartOrder.objects.filter(payment_status='paid')
    
    # Sales by payment status
    payment_status_data = CartOrder.objects.values('payment_status').annotate(
        count=Count('id'),
        total=Sum('total')
    )
    
    # Sales by order status
    order_status_data = orders.values('order_status').annotate(
        count=Count('id'),
        total=Sum('total')
    )
    
    # Monthly growth
    current_month = timezone.now().replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    
    current_month_sales = orders.filter(
        date__gte=current_month
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    
    last_month_sales = orders.filter(
        date__gte=last_month,
        date__lt=current_month
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    
    growth_rate = 0
    if last_month_sales > 0:
        growth_rate = ((current_month_sales - last_month_sales) / last_month_sales) * 100
    
    context = {
        'title': 'Sales Analytics',
        'payment_status_data': payment_status_data,
        'order_status_data': order_status_data,
        'current_month_sales': current_month_sales,
        'last_month_sales': last_month_sales,
        'growth_rate': growth_rate,
    }
    
    return render(request, 'admin/sales_analytics.html', context)

