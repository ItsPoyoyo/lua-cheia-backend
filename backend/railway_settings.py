# Railway-specific settings override
# This file contains settings that are specifically for Railway deployment

# Disable strict HTTPS requirements for Railway
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Ensure proper HTTP handling
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Disable HSTS for Railway (can cause issues)
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Ensure static files work
STATIC_URL = '/static/'
STATIC_ROOT = '/app/staticfiles'

# Ensure media files work
MEDIA_URL = '/media/'
MEDIA_ROOT = '/app/media'

# Debug logging for Railway
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
