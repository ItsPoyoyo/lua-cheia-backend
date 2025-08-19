from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def is_vendor(user):
    """Check if user is a vendor"""
    return user.is_authenticated and user.groups.filter(name='Vendors').exists()

def is_owner(user):
    """Check if user is the owner (superuser or staff)"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)

def vendor_required(view_func):
    """Decorator to restrict access to vendors only"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_vendor(request.user):
            messages.error(request, "Access denied. Vendor permissions required.")
            return redirect('admin:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def owner_required(view_func):
    """Decorator to restrict access to owners only"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_owner(request.user):
            messages.error(request, "Access denied. Owner permissions required.")
            return redirect('admin:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

class VendorPermissionMixin:
    """Mixin to restrict admin access for vendors"""
    
    def has_module_permission(self, request):
        """Vendors can only see allowed modules"""
        if is_owner(request.user):
            return True
        
        if is_vendor(request.user):
            allowed_modules = [
                'store',  # Products, Categories, Orders
                'vendor',  # Vendor profile
            ]
            return self.model._meta.app_label in allowed_modules
        
        return False
    
    def has_view_permission(self, request, obj=None):
        """Vendors can view their own objects"""
        if is_owner(request.user):
            return True
        
        if is_vendor(request.user):
            # Vendors can view their own products and orders
            if hasattr(obj, 'vendor') and obj.vendor:
                return obj.vendor.user == request.user
            return True
        
        return False
    
    def has_add_permission(self, request):
        """Vendors can add products"""
        if is_owner(request.user):
            return True
        
        if is_vendor(request.user):
            # Vendors can add products
            return self.model._meta.model_name in ['product', 'category']
        
        return False
    
    def has_change_permission(self, request, obj=None):
        """Vendors can edit their own objects"""
        if is_owner(request.user):
            return True
        
        if is_vendor(request.user):
            # Vendors can edit their own products
            if hasattr(obj, 'vendor') and obj.vendor:
                return obj.vendor.user == request.user
            return True
        
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Vendors can delete their own objects"""
        if is_owner(request.user):
            return True
        
        if is_vendor(request.user):
            # Vendors can delete their own products
            if hasattr(obj, 'vendor') and obj.vendor:
                return obj.vendor.user == request.user
            return True
        
        return False
    
    def get_queryset(self, request):
        """Filter queryset for vendors to see only their data"""
        qs = super().get_queryset(request)
        
        if is_owner(request.user):
            return qs
        
        if is_vendor(request.user):
            # Vendors see only their own products and orders
            if hasattr(self.model, 'vendor'):
                return qs.filter(vendor__user=request.user)
            elif hasattr(self.model, 'user'):
                return qs.filter(user=request.user)
        
        return qs

def setup_vendor_permissions():
    """Create vendor group and set up permissions"""
    vendor_group, created = Group.objects.get_or_create(name='Vendors')
    
    # Get content types for models vendors should access
    from store.models import Product, Category, CartOrder, CartOrderItem
    from vendor.models import Vendor
    
    # Permissions for vendors
    vendor_permissions = [
        # Product management
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Product), codename='add_product'),
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Product), codename='change_product'),
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Product), codename='view_product'),
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Product), codename='delete_product'),
        
        # Category management
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Category), codename='add_category'),
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Category), codename='change_category'),
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Category), codename='view_category'),
        
        # Order viewing (vendors can see orders but not modify them)
        Permission.objects.get(content_type=ContentType.objects.get_for_model(CartOrder), codename='view_cartorder'),
        Permission.objects.get(content_type=ContentType.objects.get_for_model(CartOrderItem), codename='view_cartorderitem'),
        
        # Vendor profile management
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Vendor), codename='change_vendor'),
        Permission.objects.get(content_type=ContentType.objects.get_for_model(Vendor), codename='view_vendor'),
    ]
    
    # Add permissions to vendor group
    vendor_group.permissions.set(vendor_permissions)
    
    return vendor_group

def restrict_vendor_access(request):
    """Middleware function to restrict vendor access"""
    if request.user.is_authenticated and is_vendor(request.user):
        # Block access to sensitive admin areas
        sensitive_paths = [
            '/admin/userauths/',
            '/admin/auth/',
            '/admin/sessions/',
            '/admin/admin/',
            '/admin/sites/',
        ]
        
        for path in sensitive_paths:
            if request.path.startswith(path):
                messages.error(request, "Access denied. Vendors cannot access user management.")
                return redirect('admin:index')
    
    return None

