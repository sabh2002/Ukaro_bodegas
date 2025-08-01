# finances/urls.py

from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('', views.finance_dashboard, name='dashboard'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/purchases/', views.purchases_report, name='purchases_report'),
    path('reports/profits/', views.profits_report, name='profits_report'),
]