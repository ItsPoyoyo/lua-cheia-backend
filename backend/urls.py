from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Try to use custom admin if jazzmin is available
try:
    from store.admin import custom_admin_site
    admin.site = custom_admin_site
except ImportError:
    # Use default Django admin if custom admin is not available
    pass

schema_view = get_schema_view(
    openapi.Info(
        title="SuperParaguai API",
        default_version='v1',
        description="This is the documentation for the backend API",
        terms_of_service="http://mywebsite.com/policies/",
        contact=openapi.Contact(email="gazouinihussein@gmail.com"),
        license=openapi.License("BSD licensed"),
    ),
    public = True,
    permission_classes = (permissions.AllowAny, )
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('store.urls')),
    
    # Root health check for Railway
    path('health/', health_check, name='root_health_check'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# Add media files serving for production
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)