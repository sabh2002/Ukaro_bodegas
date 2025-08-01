# customers/urls.py

from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('add/', views.customer_create, name='customer_create'),
    path('<int:pk>/', views.customer_detail, name='customer_detail'),
    path('<int:pk>/edit/', views.customer_update, name='customer_update'),
    path('<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    path('credits/', views.credit_list, name='credit_list'),
    path('credits/add/', views.credit_create, name='credit_create'),
    path('credits/<int:pk>/', views.credit_detail, name='credit_detail'),
    path('credits/<int:pk>/pay/', views.credit_payment, name='credit_payment'),
]