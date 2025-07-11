from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from store.models import (
    Product, Wishlist, Tax, Category, Gallery, Specification, Size, Color, Cart,
    CartOrder, CartOrderItem, Coupon, Notification, CarouselImage, OffersCarousel, Banner
)
from store.permissions import VendedorPermissionMixin
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Custom admin site configuration
admin.site.site_header = "Lua Cheia Admin"
admin.site.site_title = "Lua Cheia Admin Portal"
admin.site.index_title = "Welcome to Lua Cheia Administration"

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

@admin.register(CartOrder)
class CartOrderAdmin(admin.ModelAdmin):
    list_display = [
        'oid', 'buyer_info', 'payment_status', 'order_status', 
        'total_amount', 'items_count', 'date'
    ]
    list_filter = ['payment_status', 'order_status', 'date']
    search_fields = ['oid', 'buyer__username', 'full_name', 'email']
    readonly_fields = ['oid', 'date', 'order_summary']
    filter_horizontal = ['vendor']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('oid', 'buyer', 'date', 'order_summary'),
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
        ('Vendors', {
            'fields': ('vendor',),
            'classes': ('collapse',)
        }),
    )
    
    def buyer_info(self, obj):
        if obj.buyer:
            return f"{obj.buyer.username} ({obj.full_name})"
        return obj.full_name
    buyer_info.short_description = "Customer"
    
    def total_amount(self, obj):
        return f"${obj.total:.2f}"
    total_amount.short_description = "Total"
    
    def items_count(self, obj):
        count = obj.orderitem.count()
        return f"{count} items"
    items_count.short_description = "Items"
    
    def order_summary(self, obj):
        if not obj.pk:
            return "Save order first to see summary"
        
        items = obj.orderitem.all()
        html = "<strong>Order Items:</strong><br>"
        for item in items:
            html += f"• {item.product.title} x{item.qty} - ${item.total}<br>"
        
        html += f"<br><strong>Totals:</strong><br>"
        html += f"Subtotal: ${obj.sub_total}<br>"
        html += f"Shipping: ${obj.shipping_ammount}<br>"
        html += f"Tax: ${obj.tax_fee}<br>"
        html += f"Service Fee: ${obj.service_fee}<br>"
        html += f"<strong>Total: ${obj.total}</strong>"
        
        return mark_safe(html)
    order_summary.short_description = "Order Summary"

@admin.register(CartOrderItem)
class CartOrderItemAdmin(admin.ModelAdmin):
    list_display = ['order_link', 'product', 'qty', 'color', 'size', 'total']
    list_filter = ['order__payment_status', 'order__order_status']
    search_fields = ['order__oid', 'product__title']
    readonly_fields = ['order', 'product']
    
    def order_link(self, obj):
        url = reverse('admin:store_cartorder_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.oid)
    order_link.short_description = "Order"

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

