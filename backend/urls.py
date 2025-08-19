from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .views import health_check

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
    # Health Check Endpoints - Multiple paths for Railway
    path('health/', health_check, name='health'),
    path('health', health_check, name='health_no_slash'),
    path('', health_check, name='health_root'),
    
    path('admin/sales-dashboard/', include('store.admin_urls')),  # Sales dashboard
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching

    #Documentation
    path("docs/", schema_view.with_ui('swagger', cache_timeout=0), name="schema-swagger-ui"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)