from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from store.models import (
    Product, Wishlist, Tax, Category, Gallery, Specification, Size, Color, Cart,
    CartOrder, CartOrderItem, Coupon, Notification, CarouselImage, OffersCarousel, Banner
)
from store.permissions import VendedorPermissionMixin
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Enhanced admin site configuration with Spanish translations
admin.site.site_header = "SuperParaguai - Panel de Administración"
admin.site.site_title = "SuperParaguai Admin"
admin.site.index_title = "Bienvenido al Panel de Administración"

# Remove default apps from admin
admin.site.unregister(Group)

class SalesDashboardAdmin(admin.ModelAdmin):
    """Custom admin for sales dashboard"""
    
    def changelist_view(self, request, extra_context=None):
        # Calculate sales statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Today's sales
        today_sales = CartOrder.objects.filter(
            date__date=today,
            payment_status='paid'
        ).aggregate(
            total=Sum('total'),
            count=Count('id')
        )
        
        # Last 7 days sales
        week_sales = CartOrder.objects.filter(
            date__date__gte=week_ago,
            payment_status='paid'
        ).aggregate(
            total=Sum('total'),
            count=Count('id')
        )
        
        # Last 30 days sales
        month_sales = CartOrder.objects.filter(
            date__date__gte=month_ago,
            payment_status='paid'
        ).aggregate(
            total=Sum('total'),
            count=Count('id')
        )
        
        # All time sales
        all_time_sales = CartOrder.objects.filter(
            payment_status='paid'
        ).aggregate(
            total=Sum('total'),
            count=Count('id')
        )
        
        extra_context = extra_context or {}
        extra_context.update({
            'today_sales': today_sales['total'] or 0,
            'today_orders': today_sales['count'] or 0,
            'week_sales': week_sales['total'] or 0,
            'week_orders': week_sales['count'] or 0,
            'month_sales': month_sales['total'] or 0,
            'month_orders': month_sales['count'] or 0,
            'all_time_sales': all_time_sales['total'] or 0,
            'all_time_orders': all_time_sales['count'] or 0,
        })
        
        return super().changelist_view(request, extra_context)

class GalleryInline(admin.TabularInline):
    model = Gallery
    extra = 1
    fields = ['image', 'color', 'active']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />', obj.image.url)
        return "Sin imagen"
    image_preview.short_description = "Vista previa"

class SpecificationInline(admin.TabularInline):
    model = Specification
    extra = 1
    fields = ['title', 'content']

class SizeInline(admin.TabularInline):
    model = Size
    extra = 1
    fields = ['name', 'price', 'stock_qty', 'in_stock']
    readonly_fields = ['in_stock']

class ColorInline(admin.TabularInline):
    model = Color
    extra = 1
    fields = ['name', 'color_code', 'image', 'stock_qty', 'in_stock', 'color_preview']
    readonly_fields = ['in_stock', 'color_preview']
    
    def color_preview(self, obj):
        if obj.color_code:
            return format_html(
                '<div style="width: 30px; height: 30px; background-color: {}; border: 1px solid #ccc; border-radius: 3px;"></div>',
                obj.color_code
            )
        return "Sin color"
    color_preview.short_description = "Color"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'active', 'product_count']
    list_filter = ['active']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
    
    def product_count(self, obj):
        count = obj.product_set.count()
        url = reverse('admin:store_product_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} productos</a>', url, count)
    product_count.short_description = "Productos"

@admin.register(Product)
class ProductAdmin(VendedorPermissionMixin, admin.ModelAdmin):
    list_display = [
        'title', 'category', 'price', 'stock_status', 'total_stock', 
        'featured', 'show_in_most_viewed', 'status', 'views'
    ]
    list_filter = ['category', 'featured', 'status', 'in_stock']
    search_fields = ['title', 'description']
    list_editable = ['featured', 'status', 'show_in_most_viewed']
    readonly_fields = ['pid', 'rating', 'views', 'date', 'stock_summary']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'slug', 'description', 'image', 'category'),
            'classes': ('wide',)
        }),
        ('Precios y Envío', {
            'fields': ('price', 'old_price', 'shipping_ammount'),
            'classes': ('wide',)
        }),
        ('Inventario', {
            'fields': ('stock_qty', 'max_cart_limit', 'stock_summary'),
            'classes': ('wide',)
        }),
        ('Estado y Visibilidad', {
            'fields': ('status', 'featured', 'show_in_most_viewed', 'in_stock'),
            'classes': ('wide',)
        }),
    )
    
    inlines = [GalleryInline, SpecificationInline, SizeInline, ColorInline]
    
    def stock_status(self, obj):
        if obj.stock_qty <= 0:
            return format_html('<span style="color: red;">Sin stock</span>')
        elif obj.stock_qty <= 10:
            return format_html('<span style="color: orange;">Stock bajo</span>')
        else:
            return format_html('<span style="color: green;">En stock</span>')
    stock_status.short_description = "Estado del stock"
    
    def total_stock(self, obj):
        return obj.stock_qty
    total_stock.short_description = "Stock total"

@admin.register(CartOrder)
class CartOrderAdmin(SalesDashboardAdmin):
    list_display = [
        'oid', 'buyer_info', 'total_amount', 'payment_status', 
        'order_status', 'date', 'items_count'
    ]
    list_filter = ['payment_status', 'order_status', 'date']
    search_fields = ['oid', 'full_name', 'email', 'phone']
    readonly_fields = ['oid', 'date', 'order_items_display']
    list_per_page = 25
    
    fieldsets = (
        ('Información del Cliente', {
            'fields': ('buyer', 'full_name', 'email', 'phone'),
            'classes': ('wide',)
        }),
        ('Dirección de Envío', {
            'fields': ('address', 'city', 'state', 'country'),
            'classes': ('wide',)
        }),
        ('Detalles del Pedido', {
            'fields': ('payment_status', 'order_status', 'date'),
            'classes': ('wide',)
        }),
        ('Resumen Financiero', {
            'fields': ('sub_total', 'shipping_ammount', 'tax_fee', 'service_fee', 'total'),
            'classes': ('wide',)
        }),
        ('Artículos del Pedido', {
            'fields': ('order_items_display',),
            'classes': ('collapse',)
        }),
    )
    
    def buyer_info(self, obj):
        if obj.buyer:
            return f"{obj.buyer.username} ({obj.full_name})"
        return obj.full_name
    buyer_info.short_description = "Cliente"
    
    def total_amount(self, obj):
        return f"${obj.total:.2f}"
    total_amount.short_description = "Total"
    
    def items_count(self, obj):
        count = obj.orderitem.count()
        return f"{count} artículos"
    items_count.short_description = "Artículos"
    
    def order_items_display(self, obj):
        if not obj.pk:
            return "Guarde el pedido primero para ver los artículos"
        
        items = obj.orderitem.all()
        if not items:
            return "No hay artículos en este pedido"
        
        html = f"<h4>Artículos del Pedido ({items.count()} artículos)</h4>"
        html += "<table style='width: 100%; border-collapse: collapse; margin-top: 10px;'>"
        html += "<thead><tr style='background-color: #f8f9fa;'>"
        html += "<th style='border: 1px solid #dee2e6; padding: 8px; text-align: left;'>Producto</th>"
        html += "<th style='border: 1px solid #dee2e6; padding: 8px; text-align: center;'>Cantidad</th>"
        html += "<th style='border: 1px solid #dee2e6; padding: 8px; text-align: center;'>Precio</th>"
        html += "<th style='border: 1px solid #dee2e6; padding: 8px; text-align: center;'>Total</th>"
        html += "<th style='border: 1px solid #dee2e6; padding: 8px; text-align: center;'>Variante</th>"
        html += "</tr></thead><tbody>"
        
        for item in items:
            variant_info = []
            if item.color:
                variant_info.append(f"Color: {item.color}")
            if item.size:
                variant_info.append(f"Talla: {item.size}")
            variant_text = " | ".join(variant_info) if variant_info else "Sin variante"
            
            html += "<tr>"
            html += f"<td style='border: 1px solid #dee2e6; padding: 8px;'>{item.product.title}</td>"
            html += f"<td style='border: 1px solid #dee2e6; padding: 8px; text-align: center;'>{item.qty}</td>"
            html += f"<td style='border: 1px solid #dee2e6; padding: 8px; text-align: center;'>${item.price:.2f}</td>"
            html += f"<td style='border: 1px solid #dee2e6; padding: 8px; text-align: center;'>${item.total:.2f}</td>"
            html += f"<td style='border: 1px solid #dee2e6; padding: 8px; text-align: center;'>{variant_text}</td>"
            html += "</tr>"
        
        html += "</tbody></table>"
        
        # Add summary
        html += f"<div style='margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;'>"
        html += f"<h5>Resumen del Pedido</h5>"
        html += f"<p><strong>Subtotal:</strong> ${obj.sub_total:.2f}</p>"
        html += f"<p><strong>Envío:</strong> ${obj.shipping_ammount:.2f}</p>"
        html += f"<p><strong>Impuestos:</strong> ${obj.tax_fee:.2f}</p>"
        html += f"<p><strong>Cargo por servicio:</strong> ${obj.service_fee:.2f}</p>"
        html += f"<p style='font-size: 18px; font-weight: bold; color: #007bff;'>Total: ${obj.total:.2f}</p>"
        html += "</div>"
        
        return mark_safe(html)
    order_items_display.short_description = "Artículos y Resumen del Pedido"

# Set verbose names
CartOrderAdmin.verbose_name = "Pedido"
CartOrderAdmin.verbose_name_plural = "Pedidos"

@admin.register(CartOrderItem)
class CartOrderItemAdmin(admin.ModelAdmin):
    list_display = ['order_link', 'product', 'qty', 'color', 'size', 'price', 'total', 'vendor']
    list_filter = ['order__payment_status', 'order__order_status', 'vendor']
    search_fields = ['order__oid', 'product__title', 'vendor__username']
    readonly_fields = ['order', 'product', 'vendor']
    list_per_page = 50
    
    fieldsets = (
        ('Información del Pedido', {
            'fields': ('order', 'vendor'),
            'classes': ('wide',)
        }),
        ('Detalles del Producto', {
            'fields': ('product', 'qty', 'color', 'size'),
            'classes': ('wide',)
        }),
        ('Precios', {
            'fields': ('price', 'sub_total', 'total'),
            'classes': ('wide',)
        }),
    )
    
    def order_link(self, obj):
        url = reverse('admin:store_cartorder_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.oid)
    order_link.short_description = "Pedido"
    
    def price(self, obj):
        return f"${obj.price:.2f}"
    price.short_description = "Precio unitario"
    
    def total(self, obj):
        return f"${obj.total:.2f}"
    total.short_description = "Total"

# Set verbose names
CartOrderItemAdmin.verbose_name = "Artículo del Pedido"
CartOrderItemAdmin.verbose_name_plural = "Artículos de Pedidos"

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'active', 'valid_from', 'valid_to', 'usage_count']
    list_filter = ['active', 'discount_type', 'valid_from', 'valid_to']
    search_fields = ['code']
    list_editable = ['active']
    
    def usage_count(self, obj):
        return obj.cartorder_set.count()
    usage_count.short_description = "Usos"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'vendor', 'order', 'seen', 'date']
    list_filter = ['seen', 'date', 'vendor']
    search_fields = ['user__username', 'vendor__username', 'order__oid']
    list_editable = ['seen']
    list_per_page = 50

@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ['country', 'rate', 'active']
    list_filter = ['active', 'country']
    list_editable = ['active', 'rate']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'date']
    list_filter = ['date']
    search_fields = ['user__username', 'product__title']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['cart_id', 'product', 'user', 'qty', 'total', 'date']
    list_filter = ['date']
    search_fields = ['cart_id', 'product__title', 'user__username']

@admin.register(CarouselImage)
class CarouselImageAdmin(admin.ModelAdmin):
    list_display = ['title', 'image_preview', 'active', 'order']
    list_editable = ['active', 'order']
    list_filter = ['active']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height: 60px; object-fit: cover;" />', obj.image.url)
        return "Sin imagen"
    image_preview.short_description = "Vista previa"

@admin.register(OffersCarousel)
class OffersCarouselAdmin(admin.ModelAdmin):
    list_display = ['title', 'image_preview', 'active', 'order']
    list_editable = ['active', 'order']
    list_filter = ['active']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height: 60px; object-fit: cover;" />', obj.image.url)
        return "Sin imagen"
    image_preview.short_description = "Vista previa"

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'image_preview', 'active', 'order']
    list_editable = ['active', 'order']
    list_filter = ['active']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height: 60px; object-fit: cover;" />', obj.image.url)
        return "Sin imagen"
    image_preview.short_description = "Vista previa"
