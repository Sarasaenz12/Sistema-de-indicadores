from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from apps.authentication.views import welcome_view

urlpatterns = [
    path('', welcome_view),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/archivos/', include('apps.archivos.urls')),
    path('api/reportes/', include('apps.reportes.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)