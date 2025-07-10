from django.http import HttpResponseForbidden
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import redirect
from django.urls import reverse
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
                '/admin/store/wishlist/',  # Wishlist data
                '/admin/store/cart/',  # Cart data
                '/admin/store/review/',  # Review data
            ]
            
            for forbidden_path in forbidden_paths:
                if request.path.startswith(forbidden_path):
                    logger.warning(f"Vendedor {request.user.username} attempted to access forbidden path: {request.path}")
                    return HttpResponseForbidden(
                        "<h1>Access Denied</h1>"
                        "<p>You don't have permission to access this section.</p>"
                        "<p>Contact your administrator if you believe this is an error.</p>"
                        f"<p><a href='/admin/'>Return to Admin Home</a></p>"
                    )
        
        response = self.get_response(request)
        return response


class VendedorAdminRedirectMiddleware:
    """
    Redirect vendedores to appropriate admin sections
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Redirect vendedores from main admin to product management
        if (request.path == '/admin/' and 
            request.user.is_authenticated and 
            request.user.groups.filter(name='vendedores').exists() and
            not request.user.is_superuser):
            
            return redirect('/admin/store/product/')
        
        response = self.get_response(request)
        return response

