# bodega_system/urls.py - URLS PRINCIPALES CORREGIDAS

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from utils.middleware import custom_permission_denied_view
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Dashboard
    path('', login_required(views.dashboard), name='dashboard'),
    
    # URLs de las aplicaciones
    path('accounts/', include('accounts.urls')),
    path('sales/', include('sales.urls')),
    path('inventory/', include('inventory.urls')),
    path('customers/', include('customers.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('finances/', include('finances.urls')),
    path('utils/', include('utils.urls')),
    
    # ⭐ NUEVA SECCIÓN: APIs consolidadas
    path('api/', include('utils.api_urls')),
    
    # URLs adicionales del dashboard
    path('analytics/', login_required(views.dashboard_analytics), name='dashboard_analytics'),
    path('my-stats/', login_required(views.my_stats), name='my_stats'),
]

handler403 = custom_permission_denied_view

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)