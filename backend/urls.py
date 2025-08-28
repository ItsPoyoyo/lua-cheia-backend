from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.utils import timezone

# Try to use custom admin if available
try:
    from store.admin import custom_admin_site
    admin.site = custom_admin_site
except ImportError:
    # Use default Django admin if custom admin is not available
    pass

# Simple health check that doesn't depend on any external packages
def simple_health_check(request):
    """
    Simple health check endpoint for Railway monitoring
    Returns 200 OK if the application is running
    """
    return HttpResponse(
        f"SuperParaguai E-commerce API is running - {timezone.now().isoformat()}",
        status=200
    )

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('store.urls')),
    
    # Root health check for Railway (no external dependencies)
    path('health/', simple_health_check, name='root_health_check'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# Add media files serving for production
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)