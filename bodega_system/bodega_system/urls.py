# bodega_system/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from utils.middleware import custom_permission_denied_view

# ✅ IMPORTAR LA VISTA DEL DASHBOARD CON RESTRICCIONES
from . import views  # Asegurar que views.py esté en el directorio principal

# ✅ IMPORTAR VISTAS DE API PARA RUTAS GLOBALES
from inventory import api_views as inventory_api
from customers import api_views as customers_api  # ← LÍNEA AGREGADA

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ✅ DASHBOARD CON RESTRICCIONES
    path('', login_required(views.dashboard), name='dashboard'),
    
    # URLs de las aplicaciones
    path('accounts/', include('accounts.urls')),
    path('sales/', include('sales.urls')),
    path('inventory/', include('inventory.urls')),
    path('customers/', include('customers.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('finances/', include('finances.urls')),
    
    # ✅ NUEVAS RUTAS PARA ESTADÍSTICAS
    path('analytics/', login_required(views.dashboard_analytics), name='dashboard_analytics'),
    path('my-stats/', login_required(views.my_stats), name='my_stats'),
    
    # ✅ AGREGAR: APIs globales (sin prefijo de app)
    # Esto permite que /api/products/barcode/ funcione directamente
    path('api/products/barcode/<str:barcode>/', inventory_api.product_by_barcode_api, name='global_product_by_barcode_api'),
    path('api/products/search/', inventory_api.product_search_api, name='global_product_search_api'),
    path('api/products/<int:pk>/', inventory_api.product_detail_api, name='global_product_detail_api'),
    path('api/products/suggestions/', inventory_api.product_suggestions_api, name='global_product_suggestions_api'),
    path('api/products/stock-summary/', inventory_api.product_stock_summary_api, name='global_product_stock_summary_api'),
    
    # ✅ CORREGIDO: API de clientes (usando función importada, no string)
    path('api/customers/search/', customers_api.customer_search_api, name='global_customer_search_api'),
    
    # APIs de combos
    path('api/combos/search/', inventory_api.combo_search_api, name='global_combo_search_api'),
    
    # APIs misceláneas
    path('api/categories/', inventory_api.categories_list_api, name='global_categories_list_api'),
    path('api/validate-barcode/', inventory_api.validate_barcode_api, name='global_validate_barcode_api'),
    path('api/generate-barcode/', inventory_api.generate_barcode_api, name='global_generate_barcode_api'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = custom_permission_denied_view

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)