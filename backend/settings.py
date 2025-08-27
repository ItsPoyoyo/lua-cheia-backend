"""
Production Settings for SuperParaguai E-commerce Platform
Configured for Railway hosting with environment variables
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from decouple import config

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load production environment variables if available
PRODUCTION_ENV_FILE = BASE_DIR / 'env.production'
if PRODUCTION_ENV_FILE.exists():
    from decouple import Config, RepositoryEnv
    config = Config(RepositoryEnv(PRODUCTION_ENV_FILE))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default='False').lower() == 'true'

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='lua-cheia-backend-production.up.railway.app,.railway.app').split(',')

FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='https://lua-cheia-backend-production.up.railway.app').split(',')

# ==================== BASIC SECURITY SETTINGS ====================
# These settings work without external packages

# HTTPS Settings (will be enabled in production)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default='False').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# CSRF Protection
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default='False').lower() == 'true'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = True

# Session Security
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default='False').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True

# XSS Protection
X_FRAME_OPTIONS = 'DENY'

# Password Security
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Application definition
INSTALLED_APPS = [
    'jazzmin',  # Must come before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Custom Apps
    'store',
    'vendor',
    'customer',
    'userauths',
    'api',
    # THIRD PARTIES
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'drf_yasg',
    'corsheaders',
]

CORS_ALLOWED_ORIGINS = [
    'https://lua-cheia-frontend.vercel.app',
    'https://lua-cheia-frontend-git-main-gazou.vercel.app',
    'https://lua-cheia-frontend-gazou.vercel.app',
]

# Remove localhost from production
# CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add WhiteNoise for Railway
    'django.middleware.http.ConditionalGetMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'store.middleware.SecurityMiddleware',
    'store.middleware.VendedorAdminRedirectMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates" )],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# Database - Use PostgreSQL in production
if config('DATABASE_URL'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(config('DATABASE_URL'))
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Asuncion'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = [
    ('es', 'Español'),
    ('pt', 'Português'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File Storage Configuration
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

AUTH_USER_MODEL = 'userauths.User'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = int(config('EMAIL_PORT', default='587'))
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default='True').lower() == 'true'
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='test@example.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='testpassword')

# Mailgun Configuration
MAILGUN_API_KEY = config('MAILGUN_API_KEY', default='')
MAILGUN_SENDER_DOMAIN = config('MAILGUN_SENDER_DOMAIN', default='')

# Use Mailgun if configured, otherwise use console backend
if MAILGUN_API_KEY and MAILGUN_SENDER_DOMAIN:
    ANYMAIL = {
        "MAILGUN_API_KEY": MAILGUN_API_KEY,
        "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
    }
    FROM_EMAIL = config('FROM_EMAIL', default='gazouinihussein@gmail.com')
else:
    # Fallback to console backend for development
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# REST Framework Security
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Allow public access to most endpoints
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/hour',  # Anonymous users: 1000 requests per hour (reasonable for browsing)
        'user': '10000/hour',  # Authenticated users: 10000 requests per hour (normal usage)
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Security Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),  # 24 hours for better user experience
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),  # 30 days for better user experience
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(hours=2),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}

# Jazzmin settings - BEAUTIFUL ADMIN INTERFACE! 🎨
JAZZMIN_SETTINGS = {
    'site_title': "SuperParaguai Admin",
    'site_brand': "SuperParaguai",
    'welcome_sign': "Bienvenido a SuperParaguai",
    'copyright': "SuperParaguai 2024",
    'show_sidebar': True,
    'show_ui_builder': False,
    'navigation_expanded': True,
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.user': 'fas fa-user',
        'auth.Group': 'fas fa-users',
        'store.CartOrder': 'fas fa-shopping-cart',
        'store.CartOrderItem': 'fas fa-list',
        'store.Product': 'fas fa-box',
        'store.Category': 'fas fa-tags',
        'store.Cart': 'fas fa-cart-plus',
        'store.Wishlist': 'fas fa-heart',
        'store.Review': 'fas fa-star',
        'store.Gallery': 'fas fa-images',
        'store.Specification': 'fas fa-info-circle',
        'store.Size': 'fas fa-ruler',
        'store.Color': 'fas fa-palette',
        'store.Tax': 'fas fa-percentage',
        'store.Coupon': 'fas fa-ticket-alt',
        'store.Notification': 'fas fa-bell',
        'store.CarouselImage': 'fas fa-images',
        'store.OffersCarousel': 'fas fa-ad',
        'store.Banner': 'fas fa-flag',
        'userauths.User': 'fas fa-user-circle',
        'userauths.Profile': 'fas fa-id-card',
        'vendor.Vendor': 'fas fa-store',
        'customer.Customer': 'fas fa-user-tie',
        'api': 'fas fa-code',
    },
    'order_with_respect_to': ['store', 'userauths', 'vendor', 'customer', 'api'],
    'custom_css': None,
    'custom_js': None,
    'hide_models': ['auth.Group'],
    'show_full_result_count': False,
    'show_ui_builder': False,
    'related_modal_active': True,
    'custom_links': {
        'store': [{
            'name': 'Sales Analytics', 
            'url': '/store/admin/analytics/', 
            'icon': 'fas fa-chart-line',
        }],
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

# Enhanced Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Railway-compatible security settings
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default='False').lower() == 'true'
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default='False').lower() == 'true'
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default='False').lower() == 'true'
USE_X_FORWARDED_HOST = config('USE_X_FORWARDED_HOST', default='True').lower() == 'true'
USE_X_FORWARDED_PORT = config('USE_X_FORWARDED_PORT', default='True').lower() == 'true'
SECURE_PROXY_SSL_HEADER = config('SECURE_PROXY_SSL_HEADER', default=None)
SECURE_HSTS_SECONDS = int(config('SECURE_HSTS_SECONDS', default='0'))

# Session Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF Protection
CSRF_COOKIE_HTTPONLY = True

# Admin Security
ADMIN_URL = 'admin/'
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_REDIRECT_URL = '/admin/login/'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'production.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': config('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Admin template configuration
TEMPLATES[0]['OPTIONS']['context_processors'].append('django.template.context_processors.i18n')
