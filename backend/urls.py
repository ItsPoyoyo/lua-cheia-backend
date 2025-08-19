from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.http import JsonResponse

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

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
    path('admin/sales-dashboard/', include('store.admin_urls')),  # Sales dashboard
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching

    #Documentation
    path("", schema_view.with_ui('swagger', cache_timeout=0), name="schema-swagger-ui"),
    
    # Health Check Endpoint
    path('health/', lambda request: JsonResponse({'status': 'healthy', 'message': 'Django app is running'}), name='health'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)