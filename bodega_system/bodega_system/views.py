# bodega_system/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, F  # Importar F desde django.db.models
import datetime

from accounts import models
from inventory.models import Product
from sales.models import Sale
from customers.models import Customer, CustomerCredit

@login_required
def dashboard_view(request):
    """Vista para el dashboard principal"""
    # Obtener la fecha actual
    today = timezone.now().date()
    
    # Obtener estadísticas de ventas de hoy
    sales_today = Sale.objects.filter(date__date=today)
    sales_count = sales_today.count()
    sales_total = sales_today.aggregate(total=Sum('total_bs'))['total'] or 0
    
    # Obtener productos con stock bajo (usando F de django.db.models)
    low_stock_products = Product.objects.filter(
        stock__lte=F('min_stock'),  # Ahora usar F directamente
        is_active=True
    ).count()
    
    # Obtener total de productos
    total_products = Product.objects.filter(is_active=True).count()
    
    # Obtener total de clientes
    total_customers = Customer.objects.filter(is_active=True).count()
    
    # Obtener créditos pendientes
    pending_credits = CustomerCredit.objects.filter(is_paid=False).count()
    
    # Renderizar template
    return render(request, 'dashboard.html', {
        'sales_count': sales_count,
        'sales_total': sales_total,
        'low_stock_products': low_stock_products,
        'total_products': total_products,
        'total_customers': total_customers,
        'pending_credits': pending_credits,
    })