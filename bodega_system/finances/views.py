# finances/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def finance_dashboard(request):
    """Vista principal del dashboard financiero"""
    # Implementación pendiente
    return render(request, 'finances/dashboard.html', {
        'total_sales': 0,
        'total_purchases': 0,
        'total_profit': 0
    })

@login_required
def sales_report(request):
    """Vista para el reporte de ventas"""
    # Implementación pendiente
    return render(request, 'finances/sales_report.html', {
        'sales': []
    })

@login_required
def purchases_report(request):
    """Vista para el reporte de compras"""
    # Implementación pendiente
    return render(request, 'finances/purchases_report.html', {
        'purchases': []
    })

@login_required
def profits_report(request):
    """Vista para el reporte de ganancias"""
    # Implementación pendiente
    return render(request, 'finances/profits_report.html', {
        'profits': {}
    })