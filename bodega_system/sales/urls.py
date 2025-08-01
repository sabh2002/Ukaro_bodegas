# sales/urls.py

from django.urls import path
from . import views
from . import api_views

app_name = 'sales'

urlpatterns = [
    path('', views.sale_list, name='sale_list'),
    path('new/', views.sale_create, name='sale_create'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('<int:pk>/receipt/', views.sale_receipt, name='sale_receipt'),
    
    # APIs
    path('api/create/', api_views.create_sale_api, name='create_sale_api'),
]