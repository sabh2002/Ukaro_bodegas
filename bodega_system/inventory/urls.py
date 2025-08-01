# inventory/urls.py

from django.urls import path
from . import views
from . import api_views

app_name = 'inventory'

urlpatterns = [
    # Vistas de productos
    path('', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Vistas de categorías
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Vistas de ajustes de inventario
    path('adjustments/', views.adjustment_list, name='adjustment_list'),
    path('adjustments/add/', views.adjustment_create, name='adjustment_create'),
    
    # APIs
    path('api/products/<int:pk>/', api_views.product_detail_api, name='product_detail_api'),
    path('api/products/search/', api_views.product_search_api, name='product_search_api'),
]