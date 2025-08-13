from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
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

# Custom admin site configuration
admin.site.site_header = "SuperParaguai - Panel de Administración"
admin.site.site_title = "SuperParaguai Admin"
admin.site.index_title = "Bienvenido al Panel de Administración"

# Remove default apps from admin
admin.site.unregister(Group)

class GalleryInline(admin.TabularInline):
    model = Gallery
    extra = 1
    fields = ['image', 'color', 'active']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"

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
        return "No Color"
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
        return format_html('<a href="{}">{} products</a>', url, count)
    product_count.short_description = "Products"

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
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'image', 'category'),
            'classes': ('wide',)
        }),
        ('Pricing & Shipping', {
            'fields': ('price', 'old_price', 'shipping_ammount'),
            'classes': ('wide',)
        }),
        ('Inventory Management', {
            'fields': ('stock_qty', 'max_cart_limit', 'stock_summary'),
            'classes': ('wide',)
        }),
        ('Status & Visibility', {
            'fields': ('status', 'featured', 'show_in_most_viewed', 'in_stock'),
            'classes': ('wide',)
        }),
        ('Analytics', {
            'fields': ('rating', 'views', 'date'),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('pid',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ColorInline, SizeInline, GalleryInline, SpecificationInline]
    
    def stock_status(self, obj):
        if obj.stock_qty <= 0:
            return format_html('<span style="color: red; font-weight: bold;">Out of Stock</span>')
        elif obj.stock_qty <= 5:
            return format_html('<span style="color: orange; font-weight: bold;">Low Stock</span>')
        else:
            return format_html('<span style="color: green; font-weight: bold;">In Stock</span>')
    stock_status.short_description = "Stock Status"
    
    def total_stock(self, obj):
        color_stock = sum(c.stock_qty for c in obj.colors.all())
        size_stock = sum(s.stock_qty for s in obj.sizes.all())
        return f"Main: {obj.stock_qty} | Colors: {color_stock} | Sizes: {size_stock}"
    total_stock.short_description = "Stock Breakdown"
    
    def stock_summary(self, obj):
        if not obj.pk:
            return "Save product first to see stock summary"
        
        html = f"<strong>Main Stock:</strong> {obj.stock_qty}<br>"
        
        colors = obj.colors.all()
        if colors:
            html += "<strong>Color Stock:</strong><br>"
            for color in colors:
                status = "✅" if color.stock_qty > 0 else "❌"
                html += f"&nbsp;&nbsp;{status} {color.name}: {color.stock_qty}<br>"
        
        sizes = obj.sizes.all()
        if sizes:
            html += "<strong>Size Stock:</strong><br>"
            for size in sizes:
                status = "✅" if size.stock_qty > 0 else "❌"
                html += f"&nbsp;&nbsp;{status} {size.name}: {size.stock_qty}<br>"
        
        return mark_safe(html)
    stock_summary.short_description = "Stock Summary"
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, (Color, Size)):
                instance.in_stock = instance.stock_qty > 0
            instance.save()
        formset.save_m2m()

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

@admin.register(CartOrder)
class CartOrderAdmin(SalesDashboardAdmin):
    list_display = [
        'oid', 'buyer_info', 'payment_status', 'order_status', 
        'total_amount', 'items_count', 'date'
    ]
    list_filter = ['payment_status', 'order_status', 'date']
    search_fields = ['oid', 'buyer__username', 'full_name', 'email']
    readonly_fields = ['oid', 'date', 'order_items_display']
    filter_horizontal = ['vendor']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('oid', 'buyer', 'date'),
            'classes': ('wide',)
        }),
        ('Customer Details', {
            'fields': ('full_name', 'email', 'phone'),
            'classes': ('wide',)
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'state', 'country'),
            'classes': ('wide',)
        }),
        ('Order Status', {
            'fields': ('payment_status', 'order_status'),
            'classes': ('wide',)
        }),
        ('Financial Details', {
            'fields': ('sub_total', 'shipping_ammount', 'tax_fee', 'service_fee', 'total'),
            'classes': ('wide',)
        }),
        ('Order Items', {
            'fields': ('order_items_display',),
            'classes': ('wide', 'collapse'),
        }),
        ('Vendors', {
            'fields': ('vendor',),
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
        ('Order Information', {
            'fields': ('order', 'vendor'),
            'classes': ('wide',)
        }),
        ('Product Details', {
            'fields': ('product', 'qty', 'color', 'size'),
            'classes': ('wide',)
        }),
        ('Pricing', {
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

# Rename the admin display
CartOrderItemAdmin.verbose_name = "Order Item"
CartOrderItemAdmin.verbose_name_plural = "Order Items"

@admin.register(Color)
class ColorAdmin(VendedorPermissionMixin, admin.ModelAdmin):
    list_display = ['name', 'product', 'color_preview', 'stock_qty', 'stock_status']
    list_filter = ['in_stock']
    search_fields = ['name', 'product__title']
    readonly_fields = ['in_stock']
    
    def color_preview(self, obj):
        if obj.color_code:
            return format_html(
                '<div style="width: 30px; height: 30px; background-color: {}; border: 1px solid #ccc; border-radius: 3px; display: inline-block;"></div>',
                obj.color_code
            )
        return "No Color"
    color_preview.short_description = "Color"
    
    def stock_status(self, obj):
        if obj.stock_qty <= 0:
            return format_html('<span style="color: red;">❌ Out of Stock</span>')
        elif obj.stock_qty <= 5:
            return format_html('<span style="color: orange;">⚠️ Low Stock</span>')
        else:
            return format_html('<span style="color: green;">✅ In Stock</span>')
    stock_status.short_description = "Status"

@admin.register(Size)
class SizeAdmin(VendedorPermissionMixin, admin.ModelAdmin):
    list_display = ['name', 'product', 'price', 'stock_qty', 'stock_status']
    list_filter = ['in_stock']
    search_fields = ['name', 'product__title']
    readonly_fields = ['in_stock']
    
    def stock_status(self, obj):
        if obj.stock_qty <= 0:
            return format_html('<span style="color: red;">❌ Out of Stock</span>')
        elif obj.stock_qty <= 5:
            return format_html('<span style="color: orange;">⚠️ Low Stock</span>')
        else:
            return format_html('<span style="color: green;">✅ In Stock</span>')
    stock_status.short_description = "Status"

@admin.register(Gallery)
class GalleryAdmin(VendedorPermissionMixin, admin.ModelAdmin):
    list_display = ['product', 'color', 'image_preview', 'active']
    list_filter = ['active']
    search_fields = ['product__title', 'color__name']
    list_editable = ['active']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"

@admin.register(CarouselImage)
class CarouselImageAdmin(admin.ModelAdmin):
    list_display = ['caption', 'image_preview', 'is_active']
    list_filter = ['is_active']
    search_fields = ['caption']
    list_editable = ['is_active']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height: 60px; object-fit: cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"
    
    actions = ['activate_images', 'deactivate_images']
    
    def activate_images(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} carousel images activated.")
    activate_images.short_description = "Activate selected carousel images"
    
    def deactivate_images(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} carousel images deactivated.")
    deactivate_images.short_description = "Deactivate selected carousel images"

@admin.register(OffersCarousel)
class OffersCarouselAdmin(admin.ModelAdmin):
    list_display = ['title', 'products_count', 'is_active', 'is_automated']
    list_filter = ['is_active']
    search_fields = ['title']
    list_editable = ['is_active']
    filter_horizontal = ['products']
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = "Products Count"
    
    def is_automated(self, obj):
        automated_titles = ['Productos Más Vendidos', 'Tendencias Actuales', 'Nuevos Arrivals', 'Ofertas Especiales']
        return obj.title in automated_titles
    is_automated.boolean = True
    is_automated.short_description = "Automated"
    
    actions = ['trigger_automation', 'activate_carousels', 'deactivate_carousels']
    
    def trigger_automation(self, request, queryset):
        from store.carousel_automation import CarouselAutomation
        automation = CarouselAutomation()
        result = automation.update_offers_carousel(force=True)
        if result:
            self.message_user(request, "Carousel automation triggered successfully.")
        else:
            self.message_user(request, "Carousel automation failed.", level='ERROR')
    trigger_automation.short_description = "Trigger carousel automation"
    
    def activate_carousels(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} carousels activated.")
    activate_carousels.short_description = "Activate selected carousels"
    
    def deactivate_carousels(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} carousels deactivated.")
    deactivate_carousels.short_description = "Deactivate selected carousels"

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'image_preview', 'is_active', 'is_automated', 'date']
    list_filter = ['is_active', 'date']
    search_fields = ['title']
    list_editable = ['is_active']
    readonly_fields = ['date']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height: 60px; object-fit: cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"
    
    def is_automated(self, obj):
        return obj.title and (obj.title.startswith('Oferta Especial') or obj.title.startswith('Tendencia'))
    is_automated.boolean = True
    is_automated.short_description = "Automated"
    
    actions = ['trigger_banner_automation', 'activate_banners', 'deactivate_banners']
    
    def trigger_banner_automation(self, request, queryset):
        from store.carousel_automation import CarouselAutomation
        automation = CarouselAutomation()
        result = automation.update_promotional_banners(force=True)
        if result:
            self.message_user(request, "Banner automation triggered successfully.")
        else:
            self.message_user(request, "Banner automation failed.", level='ERROR')
    trigger_banner_automation.short_description = "Trigger banner automation"
    
    def activate_banners(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} banners activated.")
    activate_banners.short_description = "Activate selected banners"
    
    def deactivate_banners(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} banners deactivated.")
    deactivate_banners.short_description = "Deactivate selected banners"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'qty', 'total', 'date']
    list_filter = ['date']
    search_fields = ['product__title', 'user__username', 'cart_id']
    readonly_fields = ['date']

@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ['country', 'rate', 'active']
    list_filter = ['active']
    search_fields = ['country']
    list_editable = ['rate', 'active']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount', 'active', 'date']
    list_filter = ['active', 'date']
    search_fields = ['code']
    list_editable = ['active']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'order', 'seen', 'date']
    list_filter = ['seen', 'date']
    search_fields = ['user__username']
    list_editable = ['seen']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'date']
    list_filter = ['date']
    search_fields = ['user__username', 'product__title']

