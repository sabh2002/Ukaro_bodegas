# utils/api_urls.py

from django.urls import path, include
from . import api_views

urlpatterns = [
    # Utils APIs
    path('exchange-rate/', api_views.exchange_rate_view, name='exchange_rate'),
    path('products/barcode/<str:barcode>/', api_views.product_by_barcode, name='product_by_barcode'),
    path('customers/search/', api_views.customer_search, name='customer_search'),
    
    # APIs de otras aplicaciones - comentado para evitar conflicto de namespace
    # path('products/<int:pk>/', include('inventory.urls', namespace='inventory-api')),
    # path('products/search/', include('inventory.urls', namespace='inventory-search')),
]
