from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from store.models import Product, Category, Color, Size, Gallery, Specification
from vendor.models import Vendor


def create_vendedores_group():
    """
    Create vendedores (staff) group with limited permissions
    """
    # Create or get the vendedores group
    vendedores_group, created = Group.objects.get_or_create(name='vendedores')
    
    if created:
        print("Created vendedores group")
    else:
        print("Vendedores group already exists")
    
    # Clear existing permissions
    vendedores_group.permissions.clear()
    
    # Define allowed models and permissions for vendedores
    allowed_permissions = [
        # Product management
        ('store', 'product', ['view', 'add', 'change']),
        ('store', 'category', ['view']),
        ('store', 'color', ['view', 'add', 'change', 'delete']),
        ('store', 'size', ['view', 'add', 'change', 'delete']),
        ('store', 'gallery', ['view', 'add', 'change', 'delete']),
        ('store', 'specification', ['view', 'add', 'change', 'delete']),
        
        # Vendor management (limited)
        ('vendor', 'vendor', ['view', 'change']),
        
        # Order viewing (limited - no customer data)
        ('store', 'cartorder', ['view']),
        ('store', 'cartorderitem', ['view']),
    ]
    
    # Add permissions to the group
    for app_label, model_name, permission_types in allowed_permissions:
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            for perm_type in permission_types:
                permission_codename = f"{perm_type}_{model_name}"
                permission = Permission.objects.get(
                    codename=permission_codename,
                    content_type=content_type
                )
                vendedores_group.permissions.add(permission)
                print(f"Added permission: {permission_codename}")
        except (ContentType.DoesNotExist, Permission.DoesNotExist) as e:
            print(f"Permission not found: {app_label}.{model_name}.{perm_type} - {e}")
    
    print(f"Vendedores group configured with {vendedores_group.permissions.count()} permissions")
    return vendedores_group


def setup_vendor_user_permissions(user, vendor):
    """
    Setup permissions for a vendor user
    """
    # Add user to vendedores group
    vendedores_group = Group.objects.get(name='vendedores')
    user.groups.add(vendedores_group)
    
    # Set user as staff but not superuser
    user.is_staff = True
    user.is_superuser = False
    user.save()
    
    print(f"User {user.username} added to vendedores group and set as staff")


class VendedorPermissionMixin:
    """
    Mixin to restrict vendedor access to only their own vendor's data
    """
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # If user is superuser, return all objects
        if request.user.is_superuser:
            return qs
        
        # If user is in vendedores group, filter by their vendor
        if request.user.groups.filter(name='vendedores').exists():
            try:
                vendor = Vendor.objects.get(user=request.user)
                # Filter products by vendor
                if hasattr(qs.model, 'vendor'):
                    return qs.filter(vendor=vendor)
                # For related models, filter by product vendor
                elif hasattr(qs.model, 'product'):
                    return qs.filter(product__vendor=vendor)
            except Vendor.DoesNotExist:
                # If no vendor associated, return empty queryset
                return qs.none()
        
        return qs
    
    def has_change_permission(self, request, obj=None):
        # Superuser can change anything
        if request.user.is_superuser:
            return True
        
        # Vendedores can only change their own vendor's objects
        if request.user.groups.filter(name='vendedores').exists():
            if obj is None:
                return True  # Allow access to change list
            
            try:
                vendor = Vendor.objects.get(user=request.user)
                # Check if object belongs to vendor
                if hasattr(obj, 'vendor'):
                    return obj.vendor == vendor
                elif hasattr(obj, 'product'):
                    return obj.product.vendor == vendor
            except Vendor.DoesNotExist:
                return False
        
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        # Only allow delete for specific models
        allowed_delete_models = ['Color', 'Size', 'Gallery', 'Specification']
        
        if obj and obj.__class__.__name__ not in allowed_delete_models:
            return False
        
        return self.has_change_permission(request, obj)


def create_security_middleware():
    """
    Create middleware to enhance security
    """
    middleware_content = '''
from django.http import HttpResponseForbidden
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """
    Enhanced security middleware for LuaCheia admin
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log admin access attempts
        if request.path.startswith('/admin/'):
            if isinstance(request.user, AnonymousUser):
                logger.warning(f"Anonymous admin access attempt from {request.META.get('REMOTE_ADDR')}")
            else:
                logger.info(f"Admin access by {request.user.username} from {request.META.get('REMOTE_ADDR')}")
        
        # Restrict sensitive admin sections for vendedores
        if (request.path.startswith('/admin/') and 
            request.user.is_authenticated and 
            request.user.groups.filter(name='vendedores').exists() and
            not request.user.is_superuser):
            
            # Forbidden paths for vendedores
            forbidden_paths = [
                '/admin/auth/',  # User management
                '/admin/userauths/',  # User authentication
                '/admin/customer/',  # Customer data
                '/admin/store/cartorder/',  # Order details with customer info
                '/admin/store/notification/',  # Notifications
                '/admin/store/coupon/',  # Coupons
                '/admin/store/tax/',  # Tax settings
            ]
            
            for forbidden_path in forbidden_paths:
                if request.path.startswith(forbidden_path):
                    logger.warning(f"Vendedor {request.user.username} attempted to access forbidden path: {request.path}")
                    return HttpResponseForbidden("Access denied: Insufficient permissions")
        
        response = self.get_response(request)
        return response
'''
    
    return middleware_content

