from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from store.models import (
    Product, Wishlist, Tax, Category, Gallery, Specification, Size, Color, Cart,
    CartOrder, CartOrderItem, Coupon, Notification, CarouselImage, OffersCarousel, Banner,
    ProductFaq, Review
)
from store.permissions import VendorPermissionMixin

# Import other app models with error handling
try:
    from userauths.models import User, Profile
    from vendor.models import Vendor
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    print("Warning: Some models not available during startup")

# ============================================================================
# INLINE CLASSES
# ============================================================================

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

# ============================================================================
# ADMIN CLASS DEFINITIONS
# ============================================================================

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
class ProductAdmin(VendorPermissionMixin, admin.ModelAdmin):
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
    
    inlines = [GalleryInline, SpecificationInline, SizeInline, ColorInline]
    
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

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock_qty', 'in_stock']
    list_filter = ['in_stock']
    search_fields = ['name']
    list_editable = ['price', 'stock_qty', 'in_stock']
    readonly_fields = ['in_stock']

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_code', 'stock_qty', 'in_stock', 'color_preview']
    list_filter = ['in_stock']
    search_fields = ['name']
    list_editable = ['color_code', 'stock_qty', 'in_stock']
    readonly_fields = ['in_stock', 'color_preview']
    
    def color_preview(self, obj):
        if obj.color_code:
            return format_html(
                '<div style="width: 30px; height: 30px; background-color: {}; border: 1px solid #ccc; border-radius: 3px;"></div>',
                obj.color_code
            )
        return "No Color"
    color_preview.short_description = "Color"

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ['product', 'image', 'color', 'active', 'image_preview']
    list_filter = ['active', 'product', 'color']
    search_fields = ['product__title']
    list_editable = ['active']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"

@admin.register(Specification)
class SpecificationAdmin(admin.ModelAdmin):
    list_display = ['product', 'title', 'content']
    list_filter = ['product']
    search_fields = ['title', 'content', 'product__title']
    list_editable = ['title', 'content']

@admin.register(ProductFaq)
class ProductFaqAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'question', 'active', 'date']
    list_filter = ['active', 'product']
    search_fields = ['question', 'answer', 'product__title']
    list_editable = ['active']
    readonly_fields = ['date']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'active', 'date']
    list_filter = ['rating', 'active', 'date']
    search_fields = ['product__title', 'user__username', 'review']
    list_editable = ['active', 'rating']
    readonly_fields = ['date']

@admin.register(CartOrder)
class CartOrderAdmin(admin.ModelAdmin):
    list_display = [
        'oid', 'buyer_info', 'payment_method_display', 'payment_status', 'order_status', 
        'total_amount', 'items_count', 'date'
    ]
    list_filter = ['payment_method', 'payment_status', 'order_status', 'date']
    search_fields = ['oid', 'buyer__username', 'full_name', 'email']
    readonly_fields = ['oid', 'date', 'order_items_display', 'stock_status_display', 'stock_levels_display']
    filter_horizontal = ['vendor']
    
    actions = ['mark_as_whatsapp_order', 'show_whatsapp_orders', 'mark_whatsapp_orders_paid', 'mark_whatsapp_orders_completed', 'whatsapp_orders_summary', 'highlight_whatsapp_orders', 'test_stock_reduction', 'debug_whatsapp_order']
    
    def mark_as_whatsapp_order(self, request, queryset):
        """Mark selected orders as WhatsApp orders"""
        updated = queryset.update(payment_method='whatsapp')
        self.message_user(request, f'{updated} orders marked as WhatsApp orders.')
    mark_as_whatsapp_order.short_description = "📱 Mark as WhatsApp Order"
    
    def mark_whatsapp_orders_paid(self, request, queryset):
        """Mark selected WhatsApp orders as paid and reduce stock"""
        print("=" * 60)
        print("DEBUG: mark_whatsapp_orders_paid action called")
        print(f"DEBUG: Total orders selected: {queryset.count()}")
        
        # Filter only WhatsApp orders
        whatsapp_orders = queryset.filter(payment_method='whatsapp')
        print(f"DEBUG: WhatsApp orders found: {whatsapp_orders.count()}")
        
        updated = 0
        stock_reduced = 0
        
        for order in whatsapp_orders:
            try:
                print(f"DEBUG: Processing order {order.oid}")
                print(f"DEBUG: Current payment_status: {order.payment_status}")
                print(f"DEBUG: Current payment_method: {order.payment_method}")
                
                # Only process if not already paid
                if order.payment_status != 'paid':
                    print(f"DEBUG: Updating order {order.oid} to paid status")
                    
                    # Update payment status
                    order.payment_status = 'paid'
                    order.save()
                    
                    print(f"DEBUG: Order {order.oid} saved with paid status")
                    print(f"DEBUG: Order items count: {order.orderitem.count()}")
                    
                    # Reduce stock for this WhatsApp order
                    try:
                        print(f"DEBUG: Calling reduce_stock_for_whatsapp_order for order {order.oid}")
                        print(f"DEBUG: About to call stock reduction method...")
                        
                        result = order.reduce_stock_for_whatsapp_order()
                        print(f"DEBUG: Stock reduction method returned: {result}")
                        
                        stock_reduced += 1
                        print(f"DEBUG: Stock reduced successfully for order {order.oid}")
                        self.message_user(request, f'✅ Stock reduced successfully for order {order.oid}', level='SUCCESS')
                    except Exception as stock_error:
                        print(f"DEBUG: Stock reduction failed for order {order.oid}: {stock_error}")
                        print(f"DEBUG: Error type: {type(stock_error)}")
                        print(f"DEBUG: Error details: {str(stock_error)}")
                        self.message_user(request, f'⚠️ Stock reduction failed for order {order.oid}: {str(stock_error)}', level='WARNING')
                    
                    updated += 1
                else:
                    print(f"DEBUG: Order {order.oid} is already paid, skipping")
                    self.message_user(request, f'ℹ️ Order {order.oid} is already marked as paid.', level='WARNING')
                    
            except Exception as e:
                print(f"DEBUG: Error processing order {order.oid}: {e}")
                self.message_user(request, f'❌ Error processing order {order.oid}: {str(e)}', level='ERROR')
        
        print(f"DEBUG: Final results - updated: {updated}, stock_reduced: {stock_reduced}")
        print("=" * 60)
        
        if updated > 0:
            self.message_user(request, f'✅ {updated} WhatsApp orders marked as paid. 📦 Stock reduced for {stock_reduced} orders.')
        else:
            self.message_user(request, 'ℹ️ No WhatsApp orders were processed.')
    mark_whatsapp_orders_paid.short_description = "💰 Mark WhatsApp Orders as Paid & Reduce Stock"
    
    def show_whatsapp_orders(self, request, queryset):
        """Filter to show only WhatsApp orders"""
        # Redirect to filtered view with enhanced styling
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(f"{reverse('admin:store_cartorder_changelist')}?payment_method=whatsapp")
    show_whatsapp_orders.short_description = "🔍 Show WhatsApp Orders Only"
    
    def mark_whatsapp_orders_completed(self, request, queryset):
        """Mark selected WhatsApp orders as completed and reduce stock"""
        # Filter only WhatsApp orders
        whatsapp_orders = queryset.filter(payment_method='whatsapp')
        updated = 0
        stock_reduced = 0
        
        for order in whatsapp_orders:
            try:
                # Update payment and order status
                order.payment_status = 'paid'
                order.order_status = 'completed'
                order.save()
                
                # Reduce stock for this WhatsApp order
                order.reduce_stock_for_whatsapp_order()
                stock_reduced += 1
                updated += 1
                
            except Exception as e:
                self.message_user(request, f'❌ Error processing order {order.oid}: {str(e)}', level='ERROR')
        
        if updated > 0:
            self.message_user(request, f'✅ {updated} WhatsApp orders marked as completed. 📦 Stock reduced for {stock_reduced} orders.')
        else:
            self.message_user(request, 'ℹ️ No WhatsApp orders were processed.')
    mark_whatsapp_orders_completed.short_description = "✅ Mark WhatsApp Orders as Completed & Reduce Stock"
    
    def whatsapp_orders_summary(self, request, queryset):
        """Show summary of WhatsApp orders"""
        from django.db.models import Sum
        whatsapp_orders = CartOrder.objects.filter(payment_method='whatsapp')
        total_orders = whatsapp_orders.count()
        total_value = whatsapp_orders.aggregate(Sum('total'))['total__sum'] or 0
        pending_orders = whatsapp_orders.filter(payment_status='pending').count()
        
        message = f"""
        📱 WhatsApp Orders Summary:
        • Total Orders: {total_orders}
        • Total Value: ${total_value:.2f}
        • Pending Orders: {pending_orders}
        """
        self.message_user(request, message)
    whatsapp_orders_summary.short_description = "📊 WhatsApp Orders Summary"
    
    def highlight_whatsapp_orders(self, request, queryset):
        """Highlight WhatsApp orders in the list"""
        # This action just shows a message about WhatsApp orders
        whatsapp_count = queryset.filter(payment_method='whatsapp').count()
        if whatsapp_count > 0:
            self.message_user(request, f'✅ {whatsapp_count} WhatsApp orders are highlighted with 📱 emoji and special styling!')
        else:
            self.message_user(request, 'ℹ️ No WhatsApp orders in the current selection. Use the filter to see WhatsApp orders.')
    highlight_whatsapp_orders.short_description = "✨ Highlight WhatsApp Orders"
    
    def test_stock_reduction(self, request, queryset):
        """Test stock reduction for selected orders (for debugging)"""
        if len(queryset) != 1:
            self.message_user(request, '⚠️ Please select exactly one order to test stock reduction.', level='WARNING')
            return
            
        order = queryset.first()
        print(f"DEBUG: Testing stock reduction for order {order.oid}")
        print(f"DEBUG: Order payment_method: {order.payment_method}")
        print(f"DEBUG: Order payment_status: {order.payment_status}")
        print(f"DEBUG: Order items count: {order.orderitem.count()}")
        
        try:
            # Test the stock reduction method
            order.reduce_stock_for_whatsapp_order()
            self.message_user(request, f'✅ Stock reduction test successful for order {order.oid}!', level='SUCCESS')
        except Exception as e:
            self.message_user(request, f'❌ Stock reduction test failed for order {order.oid}: {str(e)}', level='ERROR')
            print(f"DEBUG: Test failed with error: {e}")
    
    test_stock_reduction.short_description = "🧪 Test Stock Reduction (Debug)"
    
    def debug_whatsapp_order(self, request, queryset):
        """Debug WhatsApp order details (for troubleshooting)"""
        if len(queryset) != 1:
            self.message_user(request, '⚠️ Please select exactly one order to debug.', level='WARNING')
            return
            
        order = queryset.first()
        
        # Show order details
        message = f"""
        🔍 Order Debug Info:
        • Order ID: {order.oid}
        • Payment Method: {order.payment_method}
        • Payment Status: {order.payment_status}
        • Order Status: {order.order_status}
        • Items Count: {order.orderitem.count()}
        • Total: ${order.total:.2f}
        """
        
        # Show item details
        items_info = []
        for item in order.orderitem.all():
            items_info.append(f"""
        📦 Item: {item.product.title}
        • Quantity: {item.qty}
        • Color: '{item.color}' (type: {type(item.color)})
        • Size: '{item.size}' (type: {type(item.size)})
        • Price: ${item.price:.2f}
        • Product Stock: {item.product.stock_qty}
        """)
            
            # Show color stock if available
            if item.color and item.color != "No Color":
                try:
                    color = item.product.colors.filter(name=item.color).first()
                    if color:
                        items_info.append(f"        • Color Stock: {color.stock_qty}")
                    else:
                        items_info.append(f"        • Color Stock: Color '{item.color}' not found!")
                except Exception as e:
                    items_info.append(f"        • Color Stock: Error - {e}")
            
            # Show size stock if available
            if item.size and item.size != "No Size":
                try:
                    size = item.product.sizes.filter(name=item.size).first()
                    if size:
                        items_info.append(f"        • Size Stock: {size.stock_qty}")
                    else:
                        items_info.append(f"        • Size Stock: Size '{item.size}' not found!")
                except Exception as e:
                    items_info.append(f"        • Size Stock: Error - {e}")
        
        full_message = message + "\n".join(items_info)
        self.message_user(request, full_message, level='INFO')
    
    debug_whatsapp_order.short_description = "🔍 Debug WhatsApp Order Details"
    
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
            'fields': ('payment_method', 'payment_status', 'order_status', 'stock_status_display'),
            'classes': ('wide',)
        }),
        ('Financial Details', {
            'fields': ('sub_total', 'shipping_ammount', 'tax_fee', 'service_fee', 'total'),
            'classes': ('wide',)
        }),
        ('Order Items', {
            'fields': ('order_items_display', 'stock_levels_display'),
            'classes': ('wide', 'collapse',),
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
    
    def stock_status_display(self, obj):
        """Display stock status and provide manual stock reduction button for WhatsApp orders"""
        if obj.payment_method == 'whatsapp':
            if obj.payment_status == 'paid':
                # Check if stock was actually reduced
                try:
                    # This will trigger the stock reduction method to check
                    obj.reduce_stock_for_whatsapp_order()
                    return format_html(
                        '<span style="color: green; font-weight: bold;">✅ Stock Reduced</span>'
                    )
                except Exception as e:
                    # Stock reduction failed or not needed
                    return format_html(
                        '<span style="color: orange; font-weight: bold;">⚠️ Stock Reduction Failed</span><br>'
                        '<small style="color: red;">{}</small>'.format(str(e))
                    )
            else:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">⚠️ Stock Not Reduced</span><br>'
                    '<small>Mark as paid to reduce stock</small>'
                )
        else:
            return format_html(
                '<span style="color: blue;">📦 Stock managed automatically</span>'
            )
    stock_status_display.short_description = "Stock Status"
    
    def stock_levels_display(self, obj):
        """Display current stock levels for order items"""
        if not obj.pk:
            return "Save the order first to see stock levels"
        
        try:
            items_info = []
            for item in obj.orderitem.all():
                item_info = f"<strong>{item.product.title}</strong><br>"
                item_info += f"• Product Stock: {item.product.stock_qty}<br>"
                
                if item.color and item.color != "No Color":
                    try:
                        color = item.product.colors.filter(name=item.color).first()
                        if color:
                            item_info += f"• Color '{item.color}' Stock: {color.stock_qty}<br>"
                        else:
                            item_info += f"• Color '{item.color}' Stock: Not found<br>"
                    except:
                        item_info += f"• Color '{item.color}' Stock: Error<br>"
                
                if item.size and item.size != "No Size":
                    try:
                        size = item.product.sizes.filter(name=item.size).first()
                        if size:
                            item_info += f"• Size '{item.size}' Stock: {size.stock_qty}<br>"
                        else:
                            item_info += f"• Size '{item.size}' Stock: Not found<br>"
                    except:
                        item_info += f"• Size '{item.size}' Stock: Error<br>"
                
                items_info.append(item_info)
            
            if items_info:
                return format_html("<br>".join(items_info))
            else:
                return "No items in this order"
                
        except Exception as e:
            return f"Error loading stock levels: {str(e)}"
    
    stock_levels_display.short_description = "Current Stock Levels"
    
    def payment_method_display(self, obj):
        """Highlight WhatsApp orders with enhanced styling"""
        if obj.payment_method == 'whatsapp':
            if obj.payment_status == 'pending':
                return f"📱 WHATSAPP ⚠️ (Stock not reduced)"
            elif obj.payment_status == 'paid':
                return f"📱 WHATSAPP ✅ (Stock reduced)"
            else:
                return f"📱 WHATSAPP {obj.payment_status.upper()}"
        elif obj.payment_method:
            return obj.payment_method.upper()
        return 'N/A'
    payment_method_display.short_description = "Método de Pago"
    
    def get_list_display(self, request):
        """Customize list display for WhatsApp orders"""
        list_display = list(super().get_list_display(request))
        return list_display
    
    def get_queryset(self, request):
        """Add custom ordering and WhatsApp filtering"""
        qs = super().get_queryset(request)
        
        # Check if we want to show only WhatsApp orders
        if request.GET.get('whatsapp_only'):
            qs = qs.filter(payment_method='whatsapp')
        
        return qs.order_by('-date')
    
    def changelist_view(self, request, extra_context=None):
        """Add WhatsApp orders summary"""
        extra_context = extra_context or {}
        
        try:
            # Get WhatsApp orders count
            whatsapp_count = CartOrder.objects.filter(payment_method='whatsapp').count()
            pending_whatsapp = CartOrder.objects.filter(payment_method='whatsapp', payment_status='pending').count()
            
            extra_context['whatsapp_stats'] = {
                'total': whatsapp_count,
                'pending': pending_whatsapp
            }
        except Exception as e:
            # If there's an error, just add empty stats
            extra_context['whatsapp_stats'] = {
                'total': 0,
                'pending': 0
            }
        
        return super().changelist_view(request, extra_context)
    
    def save_model(self, request, obj, form, change):
        """Override save to automatically reduce stock for WhatsApp orders when marked as paid"""
        if change:  # Only for existing objects (editing)
            try:
                # Get the old instance to check if payment_status changed
                old_instance = CartOrder.objects.get(pk=obj.pk)
                old_payment_status = old_instance.payment_status
                new_payment_status = obj.payment_status
                
                print(f"DEBUG: save_model called for order {obj.oid}")
                print(f"DEBUG: Old payment_status: {old_payment_status}")
                print(f"DEBUG: New payment_status: {new_payment_status}")
                print(f"DEBUG: Payment method: {obj.payment_method}")
                
                # Check if this is a WhatsApp order that was just marked as paid
                if (obj.payment_method == 'whatsapp' and 
                    old_payment_status != 'paid' and 
                    new_payment_status == 'paid'):
                    
                    print(f"DEBUG: WhatsApp order {obj.oid} marked as paid - reducing stock")
                    
                    # First save the order with the new status
                    super().save_model(request, obj, form, change)
                    
                    # Now reduce the stock
                    try:
                        obj.reduce_stock_for_whatsapp_order()
                        print(f"DEBUG: Stock reduced successfully for order {obj.oid}")
                        
                        # Add success message
                        messages.success(request, f'✅ WhatsApp order {obj.oid} marked as paid and stock reduced successfully!')
                        
                    except Exception as stock_error:
                        print(f"DEBUG: Stock reduction failed for order {obj.oid}: {stock_error}")
                        messages.error(request, f'❌ Stock reduction failed for order {obj.oid}: {str(stock_error)}')
                        
                else:
                    # Normal save for non-WhatsApp orders or status changes
                    print(f"DEBUG: Normal save for order {obj.oid}")
                    super().save_model(request, obj, form, change)
                    
            except Exception as e:
                print(f"DEBUG: Error in save_model: {e}")
                # Fall back to normal save
                super().save_model(request, obj, form, change)
        else:
            # New order creation - normal save
            super().save_model(request, obj, form, change)
    
    def order_items_display(self, obj):
        if not obj.pk:
            return "Guarde el pedido primero para ver los artículos"
        
        try:
            items = obj.orderitem.all()
            if not items.exists():
                return "No hay artículos en este pedido"
            
            items_list = []
            for item in items:
                try:
                    variant_info = []
                    if item.color:
                        variant_info.append(f"Color: {item.color}")
                    if item.size:
                        variant_info.append(f"Talla: {item.size}")
                    variant_text = " | ".join(variant_info) if variant_info else "Sin variante"
                    
                    items_list.append(
                        f"• {item.product.title} - Cantidad: {item.qty} - "
                        f"Precio: ${item.price:.2f} - Total: ${item.total:.2f} - {variant_text}"
                    )
                except Exception as e:
                    items_list.append(f"• Error loading item: {str(e)}")
            
            summary = f"<strong>Resumen del Pedido:</strong><br>"
            summary += f"Total de artículos: {items.count()}<br><br>"
            summary += "<br>".join(items_list)
            summary += f"<br><br><strong>Total del pedido: ${obj.total:.2f}</strong>"
            
            return mark_safe(summary)
            
        except Exception as e:
            return f"Error loading order items: {str(e)}"
    order_items_display.short_description = "Artículos del Pedido"

@admin.register(CartOrderItem)
class CartOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'oid', 'order_oid', 'product_title', 'qty', 'price', 'total', 
        'color', 'size', 'vendor', 'date'
    ]
    list_filter = ['date', 'vendor', 'color', 'size']
    search_fields = ['oid', 'order__oid', 'product__title', 'vendor__name']
    readonly_fields = ['oid', 'date']
    
    def order_oid(self, obj):
        return obj.order.oid if obj.order else 'N/A'
    order_oid.short_description = "Order ID"
    
    def product_title(self, obj):
        return obj.product.title if obj.product else 'N/A'
    product_title.short_description = "Product"
    
    def vendor(self, obj):
        return obj.vendor.name if obj.vendor else 'N/A'
    vendor.short_description = "Vendor"

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
    list_display = ['title', 'products_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title']
    list_editable = ['is_active']
    filter_horizontal = ['products']
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = "Products Count"
    
    actions = ['activate_carousels', 'deactivate_carousels']
    
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
    list_display = ['title', 'image_preview', 'is_active', 'date']
    list_filter = ['is_active', 'date']
    search_fields = ['title']
    list_editable = ['is_active']
    readonly_fields = ['date']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height: 60px; object-fit: cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"
    
    actions = ['activate_banners', 'deactivate_banners']
    
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

# User and Profile Admin
# Only define ProfileInline if Profile model is available
if MODELS_AVAILABLE:
    @admin.register(User)
    class UserAdmin(admin.ModelAdmin):
        list_display = ('email', 'full_name', 'phone', 'is_active', 'is_staff')
        list_filter = ('is_active', 'is_staff', 'is_superuser')
        search_fields = ('email', 'full_name', 'phone')
        ordering = ('-date_joined',)
        inlines = (ProfileInline,)
        
        fieldsets = (
            (None, {'fields': ('email', 'password')}),
            ('Personal info', {'fields': ('full_name', 'phone')}),
            ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
            ('Important dates', {'fields': ('last_login', 'date_joined')}),
        )

    @admin.register(Profile)
    class ProfileAdmin(admin.ModelAdmin):
        list_display = ['full_name', 'gender', 'country', 'state', 'city', 'user']
        list_filter = ['gender', 'country', 'state']
        search_fields = ['full_name', 'country', 'state', 'city', 'user__email']
        readonly_fields = ['user']

    @admin.register(Vendor)
    class VendorAdmin(admin.ModelAdmin):
        list_display = ['name', 'email', 'mobile', 'active', 'date']
        list_filter = ['active', 'date']
        search_fields = ['name', 'email', 'mobile', 'description']
        readonly_fields = ['date', 'slug']
        prepopulated_fields = {'slug': ('name',)}
else:
    # Create dummy classes if models are not available
    class UserAdmin:
        pass
    
    class ProfileAdmin:
        pass
    
    class VendorAdmin:
        pass



# ============================================================================
# CUSTOM ADMIN SITE CONFIGURATION
# ============================================================================

from django.contrib.admin import AdminSite
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

class CustomAdminSite(AdminSite):
    site_header = "SuperParaguai Admin"
    site_title = "SuperParaguai Admin Portal"
    index_title = "Dashboard"
    
    def has_permission(self, request):
        """Check if user has permission to access admin"""
        if not request.user.is_authenticated:
            return False
        
        # Superusers and staff can always access
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Vendors can access limited admin areas
        if request.user.groups.filter(name='Vendors').exists():
            return True
        
        return False
    
    def get_app_list(self, request):
        """Filter app list based on user permissions"""
        app_list = super().get_app_list(request)
        
        # If user is superuser or staff, show all apps
        if request.user.is_superuser or request.user.is_staff:
            return app_list
        
        # If user is vendor, filter apps
        if request.user.groups.filter(name='Vendors').exists():
            allowed_apps = ['store', 'vendor']
            return [app for app in app_list if app['app_label'] in allowed_apps]
        
        return app_list
    
    def index(self, request, extra_context=None):
        """
        Override the admin index view to show our custom dashboard
        """
        # Get today's date in the current timezone
        now = timezone.now()
        today = now.date()
        
        # Calculate today's sales (include all orders, not just paid)
        # Use last 24 hours instead of calendar day to avoid timezone issues
        yesterday = now - timedelta(hours=24)
        today_orders = CartOrder.objects.filter(
            date__gte=yesterday
        )
        today_sales = today_orders.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        today_count = today_orders.count()
        today_avg = today_sales / today_count if today_count > 0 else Decimal('0.00')
        
        # Calculate this week's sales (last 7 days) - include all orders
        week_start = now - timedelta(days=7)
        week_orders = CartOrder.objects.filter(
            date__gte=week_start
        )
        week_sales = week_orders.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        week_count = week_orders.count()
        
        # Calculate this month's sales - include all orders
        month_start = now - timedelta(days=30)
        month_orders = CartOrder.objects.filter(
            date__gte=month_start
        )
        month_sales = month_orders.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        month_count = month_orders.count()
        
        # Calculate total sales (all time) - include all orders
        total_orders = CartOrder.objects.all()
        total_sales = total_orders.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        total_count = total_orders.count()
        
        # Get recent orders (last 10 orders)
        recent_orders = CartOrder.objects.all().order_by('-date')[:10]
        
        # Get WhatsApp orders count for this week
        whatsapp_orders_count = CartOrder.objects.filter(
            payment_method='whatsapp',
            date__gte=week_start
        ).count()
        
        extra_context = extra_context or {}
        extra_context.update({
            'today_sales': today_sales,
            'today_orders': today_count,
            'today_avg': today_avg,
            'week_sales': week_sales,
            'week_orders': week_count,
            'month_sales': month_sales,
            'month_orders': month_count,
            'total_sales': total_sales,
            'total_orders': total_count,
            'recent_orders': recent_orders,
            'whatsapp_orders_count': whatsapp_orders_count,
        })
        
        return super().index(request, extra_context)

# Create custom admin site instance
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register all models with the custom admin site
custom_admin_site.register(Category, CategoryAdmin)
custom_admin_site.register(Product, ProductAdmin)
custom_admin_site.register(CartOrder, CartOrderAdmin)
custom_admin_site.register(CartOrderItem, CartOrderItemAdmin)
custom_admin_site.register(Coupon, CouponAdmin)
custom_admin_site.register(Notification, NotificationAdmin)
custom_admin_site.register(Wishlist, WishlistAdmin)
custom_admin_site.register(Tax, TaxAdmin)
custom_admin_site.register(Cart, CartAdmin)
custom_admin_site.register(Banner, BannerAdmin)
custom_admin_site.register(CarouselImage, CarouselImageAdmin)
custom_admin_site.register(OffersCarousel, OffersCarouselAdmin)
custom_admin_site.register(Review, ReviewAdmin)
custom_admin_site.register(ProductFaq, ProductFaqAdmin)

# Register User, Profile, and Vendor models only if available
if MODELS_AVAILABLE:
    try:
        custom_admin_site.register(User, UserAdmin)
        custom_admin_site.register(Profile, ProfileAdmin)
        custom_admin_site.register(Vendor, VendorAdmin)
    except Exception as e:
        print(f"Warning: Could not register some admin models: {e}")
else:
    print("Warning: Skipping admin model registration - models not available")


