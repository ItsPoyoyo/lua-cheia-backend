import re
import time
from django.http import HttpResponseForbidden, JsonResponse
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """
    Comprehensive security middleware for e-commerce platform
    - Rate limiting
    - Input validation
    - Attack prevention
    - DDoS protection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit_cache = {}
        
    def __call__(self, request):
        # Security checks before processing request
        if not self._security_checks(request):
            return HttpResponseForbidden("Security violation detected")
            
        # Rate limiting
        if not self._rate_limit_check(request):
            return JsonResponse({
                "error": "Rate limit exceeded. Please try again later.",
                "retry_after": 60
            }, status=429)
            
        # Process request
        response = self.get_response(request)
        
        # Security headers
        response = self._add_security_headers(response)
        
        return response
        
    def _security_checks(self, request):
        """Perform comprehensive security checks"""
        try:
            # Check for suspicious patterns
            if self._detect_sql_injection(request):
                logger.warning(f"SQL Injection attempt from {request.META.get('REMOTE_ADDR')}")
                return False
                
            # Check for XSS attempts
            if self._detect_xss(request):
                logger.warning(f"XSS attempt from {request.META.get('REMOTE_ADDR')}")
                return False
                
            # Check for path traversal
            if self._detect_path_traversal(request):
                logger.warning(f"Path traversal attempt from {request.META.get('REMOTE_ADDR')}")
                return False
                
            # Check for suspicious user agents
            if self._detect_suspicious_ua(request):
                logger.warning(f"Suspicious User-Agent from {request.META.get('REMOTE_ADDR')}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Security check error: {e}")
            return False
            
    def _detect_sql_injection(self, request):
        """Detect SQL injection attempts"""
        sql_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            r"(\b(and|or)\s+\d+\s*=\s*\d+)",
            r"(\b(and|or)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(--|#|/\*|\*/)",
            r"(\bxp_cmdshell\b)",
            r"(\bwaitfor\b)",
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
                    
        return False
        
    def _detect_xss(self, request):
        """Detect XSS attempts"""
        xss_patterns = [
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
            r"<button[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"<style[^>]*>",
            r"<base[^>]*>",
            r"<bgsound[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"<title[^>]*>",
            r"<xml[^>]*>",
            r"<xmp[^>]*>",
            r"<plaintext[^>]*>",
            r"<listing[^>]*>",
            r"<marquee[^>]*>",
            r"<applet[^>]*>",
            r"<isindex[^>]*>",
            r"<dir[^>]*>",
            r"<menu[^>]*>",
            r"<listing[^>]*>",
            r"<xmp[^>]*>",
            r"<plaintext[^>]*>",
            r"<listing[^>]*>",
            r"<marquee[^>]*>",
            r"<applet[^>]*>",
            r"<isindex[^>]*>",
            r"<dir[^>]*>",
            r"<menu[^>]*>",
        ]
        
        # Check GET parameters
        for key, value in request.GET.items():
            if self._check_patterns(value, xss_patterns):
                return True
                
        # Check POST data
        if request.method == 'POST':
            for key, value in request.POST.items():
                if self._check_patterns(str(value), xss_patterns):
                    return True
                    
        return False
        
    def _detect_path_traversal(self, request):
        """Detect path traversal attempts"""
        path_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"\.\.%2f",
            r"\.\.%5c",
            r"\.\.%2F",
            r"\.\.%5C",
            r"\.\.%c0%af",
            r"\.\.%c0%5c",
            r"\.\.%c1%9c",
            r"\.\.%c1%af",
            r"\.\.%e0%80%af",
            r"\.\.%e0%80%5c",
            r"\.\.%e0%81%9c",
            r"\.\.%e0%81%af",
            r"\.\.%f0%80%80%af",
            r"\.\.%f0%80%80%5c",
            r"\.\.%f0%80%81%9c",
            r"\.\.%f0%80%81%af",
        ]
        
        path = request.path
        if self._check_patterns(path, path_patterns):
            return True
            
        return False
        
    def _detect_suspicious_ua(self, request):
        """Detect suspicious User-Agent strings"""
        ua = request.META.get('HTTP_USER_AGENT', '')
        suspicious_patterns = [
            r"sqlmap",
            r"nmap",
            r"nikto",
            r"dirbuster",
            r"gobuster",
            r"wfuzz",
            r"burp",
            r"zap",
            r"w3af",
            r"skipfish",
            r"arachni",
            r"wpscan",
            r"joomscan",
            r"droopescan",
            r"cmsmap",
            r"wpscan",
            r"joomscan",
            r"droopescan",
            r"cmsmap",
            r"wpscan",
            r"joomscan",
            r"droopescan",
            r"cmsmap",
        ]
        
        if self._check_patterns(ua.lower(), suspicious_patterns):
            return True
            
        return False
        
    def _check_patterns(self, text, patterns):
        """Check if text matches any of the patterns"""
        if not text:
            return False
            
        text = str(text).lower()
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
        
    def _rate_limit_check(self, request):
        """Implement rate limiting"""
        client_ip = self._get_client_ip(request)
        current_time = int(time.time())
        
        # Clean old entries
        self._clean_rate_limit_cache(current_time)
        
        # Check rate limit
        key = f"rate_limit:{client_ip}"
        requests = cache.get(key, [])
        
        # Remove old requests (older than 1 hour)
        requests = [req_time for req_time in requests if current_time - req_time < 3600]
        
        # Check limits
        if len(requests) >= 1000:  # 1000 requests per hour
            return False
            
        # Add current request
        requests.append(current_time)
        cache.set(key, requests, 3600)  # Cache for 1 hour
        
        return True
        
    def _get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
        
    def _clean_rate_limit_cache(self, current_time):
        """Clean old rate limit cache entries"""
        # This would be implemented with a more sophisticated cache cleanup
        # For now, we rely on Django's cache TTL
        pass
        
    def _add_security_headers(self, response):
        """Add security headers to response"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';"
        
        return response
