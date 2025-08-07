# inventory/urls.py - URLs actualizadas

from django.urls import path
from . import views
from . import api_views

app_name = 'inventory'

urlpatterns = [
    # Vistas de productos (existentes)
    path('', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Vistas de categorías (existentes)
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Vistas de ajustes de inventario (existentes)
    path('adjustments/', views.adjustment_list, name='adjustment_list'),
    path('adjustments/add/', views.adjustment_create, name='adjustment_create'),
    
    # NUEVAS URLs para combos
    path('combos/', views.combo_list, name='combo_list'),
    path('combos/add/', views.combo_create, name='combo_create'),
    path('combos/<int:pk>/', views.combo_detail, name='combo_detail'),
    path('combos/<int:pk>/edit/', views.combo_update, name='combo_update'),
    path('combos/<int:pk>/delete/', views.combo_delete, name='combo_delete'),
    path('combos/<int:pk>/toggle/', views.combo_toggle_status, name='combo_toggle_status'),
    
    # APIs (existentes y nuevas)
    path('api/products/<int:pk>/', api_views.product_detail_api, name='product_detail_api'),
    path('api/products/search/', api_views.product_search_api, name='product_search_api'),
    path('api/combos/search/', api_views.combo_search_api, name='combo_search_api'),
]