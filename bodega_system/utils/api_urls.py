# utils/api_urls.py

from django.urls import path, include
from . import api_views
from inventory import api_views as inventory_api_views

urlpatterns = [
    # Utils APIs
    path('exchange-rate/', api_views.exchange_rate_view, name='exchange_rate'),
    path('products/barcode/<str:barcode>/', api_views.product_by_barcode, name='product_by_barcode'),
    path('customers/search/', api_views.customer_search, name='customer_search'),

    # Inventory APIs (búsqueda de productos)
    path('products/search/', inventory_api_views.product_search_api, name='product_search_api'),
    path('products/<int:pk>/', inventory_api_views.product_detail_api, name='product_detail_api'),
    path('combos/search/', inventory_api_views.combo_search_api, name='combo_search_api'),
]
