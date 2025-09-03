from django.urls import path
from . import views

app_name = 'utils'

urlpatterns = [
    # Gestión de tasa de cambio
    path('exchange-rate/', views.exchange_rate_management, name='exchange_rate_management'),
    path('exchange-rate/history/', views.exchange_rate_history, name='exchange_rate_history'),
]