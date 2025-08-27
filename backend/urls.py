from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Import health check view
from store.views import health_check

# Try to use custom admin if jazzmin is available
try:
    from store.admin import custom_admin_site
    admin.site = custom_admin_site
except ImportError:
    # Use default Django admin if custom admin is not available
    pass

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('store.urls')),
    
    # Root health check for Railway
    path('health/', health_check, name='root_health_check'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# Add media files serving for production
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)