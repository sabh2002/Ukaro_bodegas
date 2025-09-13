# finances/urls.py

from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    # Dashboard y reportes
    path('', views.finance_dashboard, name='dashboard'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/purchases/', views.purchases_report, name='purchases_report'),
    path('reports/profits/', views.profits_report, name='profits_report'),
    
    # Gestión de gastos
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/edit/', views.expense_update, name='expense_update'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    
    # Cierre diario
    path('daily-close/', views.daily_close_list, name='daily_close_list'),
    path('daily-close/add/', views.daily_close_create, name='daily_close_create'),
    path('daily-close/<int:pk>/', views.daily_close_detail, name='daily_close_detail'),
]