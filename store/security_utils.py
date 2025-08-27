import re
import html
import unicodedata
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
import logging

logger = logging.getLogger(__name__)

class SecurityUtils:
    """Security utilities for input validation and sanitization"""
    
    @staticmethod
    def sanitize_html(text, allowed_tags=None):
        """Sanitize HTML input to prevent XSS"""
        if not text:
            return ""
            
        # Remove all HTML tags by default
        if allowed_tags is None:
            allowed_tags = []
            
        # Basic HTML tag removal
        clean_text = re.sub(r'<[^>]+>', '', str(text))
        
        # HTML entity encoding
        clean_text = html.escape(clean_text)
        
        # Normalize unicode
        clean_text = unicodedata.normalize('NFKC', clean_text)
        
        return clean_text
        
    @staticmethod
    def validate_email(email):
        """Validate email format and security"""
        if not email:
            raise ValidationError("Email is required")
            
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")
            
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.\.',  # Path traversal
            r'javascript:',  # XSS
            r'<script',  # XSS
            r'data:',  # Data URI attacks
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                raise ValidationError("Email contains suspicious content")
                
        return email.lower().strip()
        
    @staticmethod
    def validate_phone(phone):
        """Validate phone number format and security"""
        if not phone:
            raise ValidationError("Phone number is required")
            
        # Remove all non-digit characters
        clean_phone = re.sub(r'[^\d+]', '', str(phone))
        
        # Check for suspicious patterns
        if len(clean_phone) < 8 or len(clean_phone) > 15:
            raise ValidationError("Invalid phone number length")
            
        # Check for suspicious content
        suspicious_patterns = [
            r'\.\.',  # Path traversal
            r'javascript:',  # XSS
            r'<script',  # XSS
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, str(phone), re.IGNORECASE):
                raise ValidationError("Phone number contains suspicious content")
                
        return clean_phone
        
    @staticmethod
    def validate_name(name):
        """Validate name format and security"""
        if not name:
            raise ValidationError("Name is required")
            
        # Remove HTML tags
        clean_name = re.sub(r'<[^>]+>', '', str(name))
        
        # Check length
        if len(clean_name) < 2 or len(clean_name) > 100:
            raise ValidationError("Name must be between 2 and 100 characters")
            
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.\.',  # Path traversal
            r'javascript:',  # XSS
            r'<script',  # XSS
            r'<iframe',  # XSS
            r'<object',  # XSS
            r'<embed',  # XSS
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, clean_name, re.IGNORECASE):
                raise ValidationError("Name contains suspicious content")
                
        return clean_name.strip()
        
    @staticmethod
    def validate_address(address):
        """Validate address format and security"""
        if not address:
            raise ValidationError("Address is required")
            
        # Remove HTML tags
        clean_address = re.sub(r'<[^>]+>', '', str(address))
        
        # Check length
        if len(clean_address) < 5 or len(clean_address) > 200:
            raise ValidationError("Address must be between 5 and 200 characters")
            
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.\.',  # Path traversal
            r'javascript:',  # XSS
            r'<script',  # XSS
            r'<iframe',  # XSS
            r'<object',  # XSS
            r'<embed',  # XSS
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, clean_address, re.IGNORECASE):
                raise ValidationError("Address contains suspicious content")
                
        return clean_address.strip()
        
    @staticmethod
    def validate_password(password):
        """Validate password strength and security"""
        if not password:
            raise ValidationError("Password is required")
            
        # Check length
        if len(password) < 12:
            raise ValidationError("Password must be at least 12 characters long")
            
        # Check complexity
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
            
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
            
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number")
            
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character")
            
        # Check for common patterns
        common_patterns = [
            r'123456',
            r'password',
            r'qwerty',
            r'admin',
            r'user',
            r'letmein',
            r'welcome',
            r'monkey',
            r'dragon',
            r'master',
        ]
        
        for pattern in common_patterns:
            if pattern.lower() in password.lower():
                raise ValidationError("Password contains common patterns")
                
        return password
        
    @staticmethod
    def validate_file_upload(file):
        """Validate file upload security"""
        if not file:
            raise ValidationError("File is required")
            
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size > max_size:
            raise ValidationError("File size must be less than 10MB")
            
        # Check file extension
        allowed_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp',
            '.pdf', '.doc', '.docx',
            '.txt', '.csv'
        ]
        
        file_extension = file.name.lower()
        if not any(file_extension.endswith(ext) for ext in allowed_extensions):
            raise ValidationError("File type not allowed")
            
        # Check for suspicious content in filename
        suspicious_patterns = [
            r'\.\.',  # Path traversal
            r'javascript:',  # XSS
            r'<script',  # XSS
            r'<iframe',  # XSS
            r'<object',  # XSS
            r'<embed',  # XSS
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, file.name, re.IGNORECASE):
                raise ValidationError("Filename contains suspicious content")
                
        return file
        
    @staticmethod
    def log_security_event(event_type, details, ip_address=None, user_id=None):
        """Log security events for monitoring"""
        log_message = f"SECURITY_EVENT: {event_type} - {details}"
        if ip_address:
            log_message += f" - IP: {ip_address}"
        if user_id:
            log_message += f" - User: {user_id}"
            
        logger.warning(log_message)
        
    @staticmethod
    def is_suspicious_request(request):
        """Check if request shows suspicious behavior"""
        suspicious_indicators = []
        
        # Check for too many requests
        if hasattr(request, 'META'):
            client_ip = request.META.get('REMOTE_ADDR')
            if client_ip:
                # This would integrate with rate limiting
                pass
                
        # Check for suspicious headers
        suspicious_headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CLIENT_IP',
        ]
        
        for header in suspicious_headers:
            if header in request.META:
                value = request.META[header]
                if value and ',' in value:  # Multiple IPs
                    suspicious_indicators.append(f"Multiple IPs in {header}")
                    
        # Check for suspicious user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if not user_agent or len(user_agent) < 10:
            suspicious_indicators.append("Suspicious User-Agent")
            
        return len(suspicious_indicators) > 0, suspicious_indicators
