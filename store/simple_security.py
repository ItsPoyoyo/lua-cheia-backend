"""
Simple Security Module for SuperParaguai
Provides basic security without external dependencies
"""

import re
import logging
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)

class SimpleSecurityMiddleware:
    """
    Basic security middleware that doesn't require external packages
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Basic security checks
        if self._is_suspicious_request(request):
            logger.warning(f"Suspicious request blocked from {request.META.get('REMOTE_ADDR')}")
            return HttpResponseForbidden("Suspicious request detected")
            
        # Process request
        response = self.get_response(request)
        
        # Add basic security headers
        response = self._add_basic_headers(response)
        
        return response
        
    def _is_suspicious_request(self, request):
        """Basic suspicious request detection"""
        try:
            # Check for obvious SQL injection attempts
            sql_patterns = [
                r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
                r"(--|#|/\*|\*/)",
                r"(\bxp_cmdshell\b)",
            ]
            
            # Check GET parameters
            for key, value in request.GET.items():
                if self._check_patterns(value, sql_patterns):
                    return True
                    
            # Check POST data
            if request.method == 'POST':
                for key, value in request.POST.items():
                    if self._check_patterns(str(value), sql_patterns):
                        return True
                        
            # Check for path traversal
            path_patterns = [
                r"\.\./",
                r"\.\.\\",
                r"\.\.%2f",
                r"\.\.%5c",
            ]
            
            if self._check_patterns(request.path, path_patterns):
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Security check error: {e}")
            return False
            
    def _check_patterns(self, text, patterns):
        """Check if text matches any suspicious patterns"""
        if not text:
            return False
            
        text = str(text).lower()
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
        
    def _add_basic_headers(self, response):
        """Add basic security headers"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response

def sanitize_input(text):
    """Basic input sanitization"""
    if not text:
        return ""
        
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', str(text))
    
    # Remove suspicious patterns
    suspicious = [
        r'javascript:',
        r'<script',
        r'<iframe',
        r'<object',
        r'<embed',
    ]
    
    for pattern in suspicious:
        clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
    return clean_text.strip()

def validate_email(email):
    """Basic email validation"""
    if not email:
        return False
        
    # Basic email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False
        
    # Check for suspicious content
    suspicious = [r'\.\.', r'javascript:', r'<script', r'data:']
    for pattern in suspicious:
        if re.search(pattern, email, re.IGNORECASE):
            return False
            
    return True

def log_security_event(event_type, details, ip_address=None):
    """Log security events"""
    log_message = f"SECURITY: {event_type} - {details}"
    if ip_address:
        log_message += f" - IP: {ip_address}"
        
    logger.warning(log_message)
