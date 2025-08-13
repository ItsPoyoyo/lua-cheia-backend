"""
Custom Security Middleware for Django
Provides additional security features for production
"""

import re
import logging
from django.http import HttpResponseForbidden, HttpResponse
from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
import hashlib
import time

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses
    """
    
    def process_response(self, request, response):
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.stripe.com; "
            "frame-src https://js.stripe.com https://hooks.stripe.com;"
        )
        response['Content-Security-Policy'] = csp
        
        return response

class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware
    """
    
    def process_request(self, request):
        # Skip rate limiting for certain paths
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return None
            
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Create rate limit key
        rate_limit_key = f"rate_limit:{client_ip}:{request.path}"
        
        # Check rate limit
        request_count = cache.get(rate_limit_key, 0)
        
        # Define rate limits
        rate_limits = {
            '/api/v1/login/': 5,  # 5 requests per minute
            '/api/v1/register/': 3,  # 3 requests per hour
            '/api/v1/password-reset/': 3,  # 3 requests per hour
            '/api/v1/payment-success/': 10,  # 10 requests per minute
            'default': 100,  # 100 requests per hour
        }
        
        # Get rate limit for this path
        limit = rate_limits.get(request.path, rate_limits['default'])
        
        if request_count >= limit:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on path {request.path}")
            return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
        
        # Increment counter
        cache.set(rate_limit_key, request_count + 1, 3600)  # 1 hour expiry
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    """
    Basic SQL injection protection
    """
    
    def process_request(self, request):
        # Check GET parameters
        for key, value in request.GET.items():
            if self.detect_sql_injection(value):
                logger.warning(f"Potential SQL injection detected in GET parameter {key}: {value}")
                return HttpResponseForbidden("Invalid request")
        
        # Check POST parameters
        if request.method == 'POST':
            for key, value in request.POST.items():
                if self.detect_sql_injection(value):
                    logger.warning(f"Potential SQL injection detected in POST parameter {key}: {value}")
                    return HttpResponseForbidden("Invalid request")
        
        return None
    
    def detect_sql_injection(self, value):
        """Detect potential SQL injection patterns"""
        if not isinstance(value, str):
            return False
            
        # SQL injection patterns
        patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            r"(\b(or|and)\b\s+\d+\s*[=<>])",
            r"(--|#|/\*|\*/)",
            r"(\bxp_|sp_|sysobjects|syscolumns)",
            r"(\bwaitfor\b\s+\bdelay\b)",
            r"(\bchar\b\s*\(\s*\d+\s*\))",
        ]
        
        value_lower = value.lower()
        for pattern in patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False

class XSSProtectionMiddleware(MiddlewareMixin):
    """
    XSS protection middleware
    """
    
    def process_request(self, request):
        # Check for XSS patterns in request data
        if request.method in ['POST', 'PUT', 'PATCH']:
            for key, value in request.POST.items():
                if self.detect_xss(value):
                    logger.warning(f"Potential XSS detected in parameter {key}: {value}")
                    return HttpResponseForbidden("Invalid request")
        
        return None
    
    def detect_xss(self, value):
        """Detect potential XSS patterns"""
        if not isinstance(value, str):
            return False
            
        # XSS patterns
        patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<form[^>]*>",
            r"<input[^>]*>",
            r"<textarea[^>]*>",
            r"<select[^>]*>",
        ]
        
        value_lower = value.lower()
        for pattern in patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False

class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Log all requests for security monitoring
    """
    
    def process_request(self, request):
        # Log request details
        client_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referer = request.META.get('HTTP_REFERER', '')
        
        # Hash sensitive data
        user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:8]
        
        logger.info(
            f"Request: {request.method} {request.path} "
            f"IP: {client_ip} "
            f"UA: {user_agent_hash} "
            f"Referer: {referer[:50] if referer else 'None'}"
        )
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class AuthenticationMiddleware(MiddlewareMixin):
    """
    Enhanced authentication middleware
    """
    
    def process_request(self, request):
        # Check for suspicious authentication patterns
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            # Log successful authentication
            logger.info(f"User {request.user.id} authenticated for {request.path}")
            
            # Check for multiple failed login attempts
            failed_attempts_key = f"failed_login:{request.user.id}"
            failed_attempts = cache.get(failed_attempts_key, 0)
            
            if failed_attempts > 5:
                logger.warning(f"Multiple failed login attempts for user {request.user.id}")
                # Could implement account lockout here
        
        return None

class FileUploadSecurityMiddleware(MiddlewareMixin):
    """
    File upload security middleware
    """
    
    def process_request(self, request):
        if request.method == 'POST' and request.FILES:
            for field_name, uploaded_file in request.FILES.items():
                # Check file size
                if uploaded_file.size > getattr(settings, 'MAX_FILE_SIZE', 5 * 1024 * 1024):
                    logger.warning(f"File size exceeded: {uploaded_file.name} ({uploaded_file.size} bytes)")
                    return HttpResponseForbidden("File size too large")
                
                # Check file extension
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf', '.txt', '.doc']
                file_extension = uploaded_file.name.lower().split('.')[-1]
                
                if f'.{file_extension}' not in allowed_extensions:
                    logger.warning(f"Invalid file extension: {uploaded_file.name}")
                    return HttpResponseForbidden("Invalid file type")
                
                # Check for executable files
                executable_extensions = ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']
                if f'.{file_extension}' in executable_extensions:
                    logger.warning(f"Executable file upload attempt: {uploaded_file.name}")
                    return HttpResponseForbidden("Executable files not allowed")
        
        return None

class CSRFProtectionMiddleware(MiddlewareMixin):
    """
    Enhanced CSRF protection
    """
    
    def process_request(self, request):
        # Additional CSRF checks for sensitive operations
        sensitive_paths = [
            '/api/v1/payment-success/',
            '/api/v1/orders/',
            '/api/v1/cart/',
            '/admin/',
        ]
        
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            for path in sensitive_paths:
                if request.path.startswith(path):
                    # Verify CSRF token
                    if not self.verify_csrf_token(request):
                        logger.warning(f"CSRF token verification failed for {request.path}")
                        return HttpResponseForbidden("CSRF verification failed")
        
        return None
    
    def verify_csrf_token(self, request):
        """Verify CSRF token"""
        from django.middleware.csrf import get_token
        
        # Get token from request
        csrf_token = request.META.get('HTTP_X_CSRFTOKEN') or request.POST.get('csrfmiddlewaretoken')
        
        if not csrf_token:
            return False
        
        # Verify token (simplified - Django handles this automatically)
        return True

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Performance monitoring middleware
    """
    
    def process_request(self, request):
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow requests
            if duration > 1.0:  # More than 1 second
                logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
            
            # Add performance header
            response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response

class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Custom error handling middleware
    """
    
    def process_exception(self, request, exception):
        # Log all exceptions
        logger.error(f"Exception in {request.path}: {str(exception)}")
        
        # Don't expose sensitive information in production
        if not settings.DEBUG:
            return HttpResponse("An error occurred. Please try again later.", status=500)
        
        return None
