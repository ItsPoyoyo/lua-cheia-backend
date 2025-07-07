from django.contrib import admin
from django.contrib.auth.models import Group
from store.models import (
    Product, Wishlist, Tax, Category, Gallery, Specification, Size, Color, Cart,
    CartOrder, CartOrderItem, Review, Coupon, Notification, CarouselImage, OffersCarousel, Banner
)
import logging

# Set up logging
logger = logging.getLogger(__name__)

class GalleryInline(admin.TabularInline):
    model = Gallery
    extra = 0
    # Limit color choices to the product's colors only
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "color":
            if request._obj_ is not None:
                kwargs["queryset"] = Color.objects.filter(product=request._obj_)  # Changed from request._obj_.product to just request._obj_
            else:
                kwargs["queryset"] = Color.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class SpecificationInline(admin.TabularInline):
    model = Specification
    extra = 0

class SizeInline(admin.TabularInline):
    model = Size
    extra = 0
    fields = ['name', 'price', 'stock_qty', 'in_stock']

class ColorInline(admin.TabularInline):
    model = Color
    extra = 0
    fields = ['name', 'color_code', 'image', 'stock_qty', 'in_stock']

class ManagerAdmin(admin.ModelAdmin):
    """ Custom admin permissions for Vendor staff role """
    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj  # Store the current object for use in inlines
        return super().get_form(request, obj, **kwargs)

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Vendor').exists()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name='Vendor').exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name='Vendor').exists()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.groups.filter(name='Vendor').exists():
            return qs
        return qs.none()

class ProductAdmin(ManagerAdmin):
    list_display = ('title', 'price', 'stock_qty', 'in_stock', 'category', 'featured', 'views', 'vendor')
    list_editable = ('featured',)
    list_filter = ('category', 'vendor', 'featured')
    search_fields = ('title', 'description')
    readonly_fields = ('in_stock', 'rating')
    inlines = [GalleryInline, SpecificationInline, SizeInline, ColorInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'image', 'description', 'category', 'vendor')
        }),
        ('Pricing', {
            'fields': ('price', 'old_price', 'shipping_ammount')
        }),
        ('Inventory', {
            'fields': ('stock_qty', 'in_stock', 'max_cart_limit')
        }),
        ('Status', {
            'fields': ('status', 'featured', 'rating', 'views')
        }),
        ('Advanced', {
            'fields': ('pid', 'slug'),
            'classes': ('collapse',)
        }),
    )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, (Color, Size)):
                # Update in_stock status when saving colors/sizes
                instance.in_stock = instance.stock_qty > 0
            instance.save()
        formset.save_m2m()

class CartOrderAdmin(ManagerAdmin):
    list_display = ('oid', 'buyer', 'payment_status', 'order_status', 'total', 'date')
    list_filter = ('payment_status', 'order_status', 'date')
    search_fields = ('oid', 'buyer__username', 'full_name')
    readonly_fields = ('oid', 'date')
    filter_horizontal = ('vendor',)

class CartOrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'qty', 'total')
    list_filter = ('order__payment_status', 'order__order_status')
    search_fields = ('order__oid', 'product__title')

class ReviewAdmin(ManagerAdmin):
    list_display = ('user', 'product', 'rating', 'active', 'date')
    list_editable = ('active',)
    list_filter = ('rating', 'active', 'date')
    search_fields = ('user__username', 'product__title')

class ColorAdmin(ManagerAdmin):
    list_display = ('name', 'product', 'stock_qty', 'in_stock')
    list_filter = ('in_stock', 'product__vendor')
    search_fields = ('name', 'product__title')
    readonly_fields = ('in_stock',)

class SizeAdmin(ManagerAdmin):
    list_display = ('name', 'product', 'price', 'stock_qty', 'in_stock')
    list_filter = ('in_stock', 'product__vendor')
    search_fields = ('name', 'product__title')
    readonly_fields = ('in_stock',)

class GalleryAdmin(ManagerAdmin):
    list_display = ('product', 'color', 'active')
    list_filter = ('active', 'product__vendor')
    search_fields = ('product__title', 'color__name')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "color":
            if 'product_id' in request.GET:
                kwargs["queryset"] = Color.objects.filter(product_id=request.GET['product_id'])
            elif hasattr(request, '_obj_') and request._obj_:
                kwargs["queryset"] = Color.objects.filter(product=request._obj_)
            else:
                kwargs["queryset"] = Color.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class CarouselImageAdmin(admin.ModelAdmin):
    list_display = ('caption', 'is_active')
    list_editable = ('is_active',)

class OffersCarouselAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)
    filter_horizontal = ('products',)

class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'link', 'is_active', 'date')
    list_filter = ('is_active', 'date')
    search_fields = ('title', 'link')

# Register models
admin.site.register(Category)
admin.site.register(Product, ProductAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Cart)
admin.site.register(Coupon)
admin.site.register(CartOrder, CartOrderAdmin)
admin.site.register(CartOrderItem, CartOrderItemAdmin)
admin.site.register(Tax)
admin.site.register(Notification)
admin.site.register(Wishlist)
admin.site.register(Gallery, GalleryAdmin)
admin.site.register(Specification)
admin.site.register(Size, SizeAdmin)
admin.site.register(Color, ColorAdmin)
admin.site.register(CarouselImage, CarouselImageAdmin)
admin.site.register(OffersCarousel, OffersCarouselAdmin)
admin.site.register(Banner, BannerAdmin)