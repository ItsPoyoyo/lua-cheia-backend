"""
Production Settings for SuperParaguai E-commerce
"""

import os
from pathlib import Path
from .base import *
from security_config import *

# ===== PRODUCTION SETTINGS =====

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Production allowed hosts
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# ===== DATABASE CONFIGURATION =====
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        **DATABASE_OPTIONS
    }
}

# ===== CACHE CONFIGURATION =====
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        **CACHE_OPTIONS
    }
}

# ===== STATIC FILES CONFIGURATION =====
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Additional static files locations
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Static files storage
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# ===== MEDIA FILES CONFIGURATION =====
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ===== EMAIL CONFIGURATION =====
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

# ===== LOGGING CONFIGURATION =====
LOGGING = LOGGING_CONFIG

# ===== MIDDLEWARE CONFIGURATION =====
MIDDLEWARE = CUSTOM_MIDDLEWARE + [
    'security.middleware.SecurityHeadersMiddleware',
    'security.middleware.RateLimitMiddleware',
    'security.middleware.SQLInjectionProtectionMiddleware',
    'security.middleware.XSSProtectionMiddleware',
    'security.middleware.RequestLoggingMiddleware',
    'security.middleware.AuthenticationMiddleware',
    'security.middleware.FileUploadSecurityMiddleware',
    'security.middleware.CSRFProtectionMiddleware',
    'security.middleware.PerformanceMonitoringMiddleware',
    'security.middleware.ErrorHandlingMiddleware',
]

# ===== REST FRAMEWORK CONFIGURATION =====
REST_FRAMEWORK = REST_FRAMEWORK

# ===== JWT CONFIGURATION =====
SIMPLE_JWT = SIMPLE_JWT

# ===== PASSWORD VALIDATION =====
AUTH_PASSWORD_VALIDATORS = AUTH_PASSWORD_VALIDATORS

# ===== CORS CONFIGURATION =====
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = CORS_ALLOW_CREDENTIALS
CORS_ALLOW_METHODS = CORS_ALLOW_METHODS
CORS_ALLOW_HEADERS = CORS_ALLOW_HEADERS

# ===== SECURITY SETTINGS =====
# HTTPS and SSL Settings
SECURE_SSL_REDIRECT = SECURE_SSL_REDIRECT
SECURE_PROXY_SSL_HEADER = SECURE_PROXY_SSL_HEADER
SECURE_HSTS_SECONDS = SECURE_HSTS_SECONDS
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_INCLUDE_SUBDOMAINS
SECURE_HSTS_PRELOAD = SECURE_HSTS_PRELOAD
SECURE_CONTENT_TYPE_NOSNIFF = SECURE_CONTENT_TYPE_NOSNIFF
SECURE_BROWSER_XSS_FILTER = SECURE_BROWSER_XSS_FILTER
SECURE_REFERRER_POLICY = SECURE_REFERRER_POLICY

# Session Security
SESSION_COOKIE_SECURE = SESSION_COOKIE_SECURE
SESSION_COOKIE_HTTPONLY = SESSION_COOKIE_HTTPONLY
SESSION_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
SESSION_COOKIE_AGE = SESSION_COOKIE_AGE
SESSION_EXPIRE_AT_BROWSER_CLOSE = SESSION_EXPIRE_AT_BROWSER_CLOSE
SESSION_SAVE_EVERY_REQUEST = SESSION_SAVE_EVERY_REQUEST

# CSRF Protection
CSRF_COOKIE_SECURE = CSRF_COOKIE_SECURE
CSRF_COOKIE_HTTPONLY = CSRF_COOKIE_HTTPONLY
CSRF_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS

# XSS Protection
X_FRAME_OPTIONS = X_FRAME_OPTIONS

# ===== FILE UPLOAD SECURITY =====
FILE_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE
FILE_UPLOAD_TEMP_DIR = FILE_UPLOAD_TEMP_DIR
FILE_UPLOAD_PERMISSIONS = FILE_UPLOAD_PERMISSIONS
FILE_UPLOAD_DIRECTORY_PERMISSIONS = FILE_UPLOAD_DIRECTORY_PERMISSIONS

# ===== STRIPE CONFIGURATION =====
STRIPE_SECRET_KEY = STRIPE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY = STRIPE_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET = STRIPE_WEBHOOK_SECRET

# ===== ADMIN CONFIGURATION =====
admin.site.site_header = ADMIN_SITE_HEADER
admin.site.site_title = ADMIN_SITE_TITLE
admin.site.index_title = ADMIN_INDEX_TITLE

# ===== FRONTEND URL =====
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://yourdomain.com')

# ===== MONITORING CONFIGURATION =====
MONITORING_CONFIG = MONITORING_CONFIG

# ===== BACKUP CONFIGURATION =====
BACKUP_CONFIG = BACKUP_CONFIG

# ===== API SECURITY =====
API_SECURITY = API_SECURITY

# ===== CUSTOM SETTINGS =====

# Disable Django Debug Toolbar
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,
}

# Disable Django Debug Toolbar
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']

# ===== PERFORMANCE OPTIMIZATIONS =====

# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS']['MAX_CONNS'] = 20

# Cache settings
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'ecom_prod'

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ===== SECURITY MONITORING =====

# Enable security monitoring
SECURITY_MONITORING = True

# Security alert email
SECURITY_ALERT_EMAIL = os.environ.get('SECURITY_ALERT_EMAIL')

# ===== ENVIRONMENT VALIDATION =====

def validate_environment():
    """Validate that all required environment variables are set"""
    missing_vars = []
    
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Validate environment on startup
validate_environment()

# ===== PRODUCTION CHECKS =====

# Ensure debug is disabled
if DEBUG:
    raise ValueError("DEBUG must be False in production")

# Ensure secret key is set and strong
if len(SECRET_KEY) < 50:
    raise ValueError("SECRET_KEY must be at least 50 characters long")

# Ensure allowed hosts is configured
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS must be configured in production")

print("✅ Production settings loaded successfully!")
print(f"🔒 Security features enabled: {len([m for m in MIDDLEWARE if 'security' in m.lower()])} security middlewares")
print(f"📊 Monitoring enabled: {MONITORING_CONFIG['ENABLE_LOGGING']}")
print(f"🚀 Performance optimizations: Database pooling, caching, and static file optimization enabled")
