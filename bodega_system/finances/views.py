# finances/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal

from .models import Expense, ExpenseReceipt, DailyClose
from .forms import ExpenseForm, ExpenseReceiptFormset, DailyCloseForm, ReportFilterForm
from sales.models import Sale, SaleItem
from suppliers.models import SupplierOrder
from utils.decorators import admin_required
from utils.models import ExchangeRate

@login_required
def finance_dashboard(request):
    """Vista principal del dashboard financiero"""
    today = date.today()
    this_month_start = today.replace(day=1)
    
    # Métricas del día
    today_sales = Sale.objects.filter(date__date=today)
    today_sales_total_bs = today_sales.aggregate(total=Sum('total_bs'))['total'] or Decimal('0.00')
    today_sales_total_usd = today_sales.aggregate(total=Sum('total_usd'))['total'] or Decimal('0.00')
    today_sales_count = today_sales.count()

    # ⭐ NUEVO: Dashboard Híbrido - Separar ventas de contado vs crédito
    # Ventas de CONTADO (dinero que entró hoy por ventas)
    today_cash_sales = today_sales.filter(is_credit=False)
    today_cash_sales_usd = today_cash_sales.aggregate(total=Sum('total_usd'))['total'] or Decimal('0.00')
    today_cash_sales_bs = today_cash_sales.aggregate(total=Sum('total_bs'))['total'] or Decimal('0.00')
    today_cash_sales_count = today_cash_sales.count()

    # Ventas a CRÉDITO (dinero pendiente de cobro)
    today_credit_sales = today_sales.filter(is_credit=True)
    today_credit_sales_usd = today_credit_sales.aggregate(total=Sum('total_usd'))['total'] or Decimal('0.00')
    today_credit_sales_bs = today_credit_sales.aggregate(total=Sum('total_bs'))['total'] or Decimal('0.00')
    today_credit_sales_count = today_credit_sales.count()

    # PAGOS de créditos recibidos HOY (dinero que entró por cobro de deudas)
    from customers.models import CreditPayment
    today_credit_payments = CreditPayment.objects.filter(payment_date__date=today)
    today_credit_payments_usd = today_credit_payments.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    today_credit_payments_bs = today_credit_payments.aggregate(total=Sum('amount_bs'))['total'] or Decimal('0.00')
    today_credit_payments_count = today_credit_payments.count()

    # TOTAL COBRADO HOY = Ventas de contado + Pagos de créditos recibidos
    today_collected_usd = today_cash_sales_usd + today_credit_payments_usd
    today_collected_bs = today_cash_sales_bs + today_credit_payments_bs

    # PENDIENTE DE COBRO = Ventas a crédito del día (aún no pagadas)
    today_pending_collection_usd = today_credit_sales_usd
    today_pending_collection_bs = today_credit_sales_bs

    today_expenses = Expense.objects.filter(date=today)
    today_expenses_total_usd = today_expenses.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')

    # ⭐ CORREGIDO: Calcular ganancia REAL del día (no solo ventas - gastos)
    today_sale_items = SaleItem.objects.filter(
        sale__date__date=today,
        product__isnull=False
    ).select_related('product')

    today_real_profit_usd = Decimal('0.00')
    for item in today_sale_items:
        if not item.product:
            continue
        sale_price = item.price_usd or Decimal('0.00')
        purchase_price = item.product.purchase_price_usd or Decimal('0.00')
        item_profit = (sale_price - purchase_price) * item.quantity
        today_real_profit_usd += item_profit

    # Convertir a Bs
    current_rate = ExchangeRate.get_latest_rate()
    today_real_profit_bs = today_real_profit_usd * (current_rate.bs_to_usd if current_rate else Decimal('1.00'))

    # ⭐ CORREGIDO: Convertir gastos USD a Bs antes de restar
    today_expenses_total_bs = today_expenses_total_usd * (current_rate.bs_to_usd if current_rate else Decimal('1.00'))

    # Ganancia neta del día = ganancia por productos - gastos (ambos en Bs)
    today_net_profit_bs = today_real_profit_bs - today_expenses_total_bs

    # Calcular ganancia neta en USD también
    today_net_profit_usd = today_real_profit_usd - today_expenses_total_usd
    
    # Métricas del mes
    month_sales = Sale.objects.filter(date__date__gte=this_month_start, date__date__lte=today)
    month_sales_total_bs = month_sales.aggregate(total=Sum('total_bs'))['total'] or Decimal('0.00')
    month_sales_total_usd = month_sales.aggregate(total=Sum('total_usd'))['total'] or Decimal('0.00')
    
    month_purchases = SupplierOrder.objects.filter(
        order_date__date__gte=this_month_start, 
        order_date__date__lte=today,
        status='received'
    )
    month_purchases_total_bs = month_purchases.aggregate(total=Sum('total_bs'))['total'] or Decimal('0.00')
    month_purchases_total_usd = month_purchases.aggregate(total=Sum('total_usd'))['total'] or Decimal('0.00')
    
    month_expenses = Expense.objects.filter(date__gte=this_month_start, date__lte=today)
    month_expenses_total_usd = month_expenses.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')

    # Tasa de cambio actual (necesaria para conversiones)
    current_rate = ExchangeRate.get_latest_rate()

    # ⭐ MODIFICADO: Productos más RENTABLES este mes (no solo más vendidos)
    sale_items_month = SaleItem.objects.filter(
        sale__date__date__gte=this_month_start,
        sale__date__date__lte=today,
        product__isnull=False
    ).select_related('product')

    # Calcular rentabilidad REAL por producto Y ganancia total del mes
    products_profit = {}
    month_real_profit_usd = Decimal('0.00')  # ⭐ NUEVO: Ganancia real del mes

    for item in sale_items_month:
        # ⭐ VALIDACIÓN: Saltar si no hay producto (no debería pasar por el filtro, pero es defensivo)
        if not item.product:
            continue

        product_name = item.product.name
        if product_name not in products_profit:
            products_profit[product_name] = {
                'name': product_name,
                'total_quantity': Decimal('0.00'),
                'total_profit_usd': Decimal('0.00'),
            }

        quantity = item.quantity
        # ⭐ VALIDACIÓN: Manejar valores None defensivamente
        sale_price = item.price_usd or Decimal('0.00')
        purchase_price = item.product.purchase_price_usd or Decimal('0.00')
        profit = (sale_price - purchase_price) * quantity

        products_profit[product_name]['total_quantity'] += quantity
        products_profit[product_name]['total_profit_usd'] += profit
        month_real_profit_usd += profit  # ⭐ NUEVO: Sumar a ganancia total del mes

    # Convertir ganancia real del mes a Bs
    month_real_profit_bs = month_real_profit_usd * (current_rate.bs_to_usd if current_rate else Decimal('1.00'))

    # ⭐ CORREGIDO: Convertir gastos USD a Bs antes de restar
    month_expenses_total_bs = month_expenses_total_usd * (current_rate.bs_to_usd if current_rate else Decimal('1.00'))

    # ⭐ CORREGIDO: Ganancia neta REAL del mes = ganancia por productos - gastos (ambos en Bs)
    net_profit_real_bs = month_real_profit_bs - month_expenses_total_bs

    # Mantener cálculo aproximado para comparación (opcional)
    gross_profit_bs = month_sales_total_bs - month_purchases_total_bs
    gross_profit_usd = month_sales_total_usd - month_purchases_total_usd
    # ⭐ CORREGIDO: Convertir gastos a Bs antes de restar
    net_profit_bs = gross_profit_bs - month_expenses_total_bs  # Método aproximado

    # Ordenar por ganancia y tomar top 10
    top_products_by_profit = sorted(
        products_profit.values(),
        key=lambda x: x['total_profit_usd'],
        reverse=True
    )[:10]
    
    # Gastos por categoría este mes (en USD)
    expenses_by_category = month_expenses.values(
        'category'
    ).annotate(
        total_usd=Sum('amount_usd'),
        count=Count('id')
    ).order_by('-total_usd')

    context = {
        'today_sales_count': today_sales_count,
        'today_sales_total_bs': today_sales_total_bs,
        'today_sales_total_usd': today_sales_total_usd,  # ⭐ NUEVO: En USD

        # ⭐ NUEVO: Dashboard Híbrido - Vendido vs Cobrado
        'today_cash_sales_usd': today_cash_sales_usd,
        'today_cash_sales_bs': today_cash_sales_bs,
        'today_cash_sales_count': today_cash_sales_count,
        'today_credit_sales_usd': today_credit_sales_usd,
        'today_credit_sales_bs': today_credit_sales_bs,
        'today_credit_sales_count': today_credit_sales_count,
        'today_credit_payments_usd': today_credit_payments_usd,
        'today_credit_payments_bs': today_credit_payments_bs,
        'today_credit_payments_count': today_credit_payments_count,
        'today_collected_usd': today_collected_usd,
        'today_collected_bs': today_collected_bs,
        'today_pending_collection_usd': today_pending_collection_usd,
        'today_pending_collection_bs': today_pending_collection_bs,

        'today_expenses_total': today_expenses_total_bs,  # ⭐ CORREGIDO: En Bs
        'today_expenses_total_usd': today_expenses_total_usd,  # ⭐ NUEVO: En USD
        # ⭐ CORREGIDO: Usar ganancia REAL del día, no solo ventas - gastos
        'today_profit': today_net_profit_bs,
        'today_net_profit_usd': today_net_profit_usd,  # ⭐ NUEVO: Ganancia neta en USD
        'today_real_profit_usd': today_real_profit_usd,  # Ganancia en USD

        'month_sales_total_bs': month_sales_total_bs,
        'month_sales_total_usd': month_sales_total_usd,
        'month_purchases_total_bs': month_purchases_total_bs,
        'month_purchases_total_usd': month_purchases_total_usd,
        'month_expenses_total': month_expenses_total_bs,  # ⭐ CORREGIDO: En Bs
        'month_expenses_total_usd': month_expenses_total_usd,  # ⭐ NUEVO: En USD
        # Métodos de cálculo aproximado (para comparación)
        'gross_profit_bs': gross_profit_bs,
        'gross_profit_usd': gross_profit_usd,
        'net_profit_bs': net_profit_bs,
        # ⭐ NUEVO: Ganancias REALES del mes
        'month_real_profit_usd': month_real_profit_usd,
        'month_real_profit_bs': month_real_profit_bs,
        'net_profit_real_bs': net_profit_real_bs,

        # ⭐ MODIFICADO: Ahora son productos más rentables (no más vendidos)
        'top_products_by_profit': top_products_by_profit,
        'expenses_by_category': expenses_by_category,
        'current_rate': current_rate,
        'current_month': this_month_start.strftime('%B %Y'),
    }

    return render(request, 'finances/dashboard.html', context)

@login_required
def sales_report(request):
    """Vista para el reporte de ventas"""
    form = ReportFilterForm(request.GET or None)
    sales = Sale.objects.all()
    
    # Aplicar filtros
    if form.is_valid():
        start_date, end_date = _get_date_range(form.cleaned_data)
        if start_date and end_date:
            sales = sales.filter(date__date__gte=start_date, date__date__lte=end_date)
    
    # Ordenar y paginar
    sales = sales.order_by('-date')
    paginator = Paginator(sales, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular totales
    totals = sales.aggregate(
        total_bs=Sum('total_bs'),
        total_usd=Sum('total_usd'),
        count=Count('id')
    )
    
    return render(request, 'finances/sales_report.html', {
        'form': form,
        'page_obj': page_obj,
        'totals': totals,
    })

@login_required
def purchases_report(request):
    """Vista para el reporte de compras"""
    form = ReportFilterForm(request.GET or None)
    purchases = SupplierOrder.objects.filter(status='received')
    
    # Aplicar filtros
    if form.is_valid():
        start_date, end_date = _get_date_range(form.cleaned_data)
        if start_date and end_date:
            purchases = purchases.filter(order_date__date__gte=start_date, order_date__date__lte=end_date)
    
    # Ordenar y paginar
    purchases = purchases.order_by('-order_date').select_related('supplier')
    paginator = Paginator(purchases, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular totales
    totals = purchases.aggregate(
        total_bs=Sum('total_bs'),
        total_usd=Sum('total_usd'),
        count=Count('id')
    )
    
    return render(request, 'finances/purchases_report.html', {
        'form': form,
        'page_obj': page_obj,
        'totals': totals,
    })

@login_required
def profits_report(request):
    """Vista para el reporte de ganancias REAL por producto vendido"""
    form = ReportFilterForm(request.GET or None)

    # Obtener fechas del formulario
    if form.is_valid():
        start_date, end_date = _get_date_range(form.cleaned_data)
    else:
        # Por defecto, este mes
        today = date.today()
        start_date = today.replace(day=1)
        end_date = today

    # Calcular métricas de ganancias
    sales_data = Sale.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date
    ).aggregate(
        total_sales_bs=Sum('total_bs'),
        total_sales_usd=Sum('total_usd'),
        sales_count=Count('id')
    )

    purchases_data = SupplierOrder.objects.filter(
        order_date__date__gte=start_date,
        order_date__date__lte=end_date,
        status='received'
    ).aggregate(
        total_purchases_bs=Sum('total_bs'),
        total_purchases_usd=Sum('total_usd'),
        purchases_count=Count('id')
    )

    expenses_data = Expense.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        total_expenses_usd=Sum('amount_usd'),  # ⭐ CORREGIDO: Sumar en USD
        expenses_count=Count('id')
    )

    # Calcular ganancias
    total_sales_bs = sales_data['total_sales_bs'] or Decimal('0.00')
    total_sales_usd = sales_data['total_sales_usd'] or Decimal('0.00')
    total_purchases_bs = purchases_data['total_purchases_bs'] or Decimal('0.00')
    total_purchases_usd = purchases_data['total_purchases_usd'] or Decimal('0.00')
    total_expenses_usd = expenses_data['total_expenses_usd'] or Decimal('0.00')

    # ⭐ NUEVO: Calcular ganancia REAL por producto vendido
    # Ganancia = (precio_venta - precio_compra) × cantidad
    sale_items = SaleItem.objects.filter(
        sale__date__date__gte=start_date,
        sale__date__lte=end_date,
        product__isnull=False  # Solo productos, no combos
    ).select_related('product', 'sale')

    real_profit_usd = Decimal('0.00')
    for item in sale_items:
        # ⭐ VALIDACIÓN: Saltar si no hay producto
        if not item.product:
            continue

        # Ganancia por ítem = (precio venta - precio compra) × cantidad
        # ⭐ VALIDACIÓN: Manejar valores None defensivamente
        sale_price = item.price_usd or Decimal('0.00')
        purchase_price = item.product.purchase_price_usd or Decimal('0.00')
        item_profit = (sale_price - purchase_price) * item.quantity
        real_profit_usd += item_profit

    # Convertir ganancia real a Bs usando tasa promedio del período
    current_rate = ExchangeRate.get_latest_rate()
    real_profit_bs = real_profit_usd * (current_rate.bs_to_usd if current_rate else Decimal('1.00'))

    # ⭐ CORREGIDO: Convertir gastos USD a Bs antes de restar
    total_expenses_bs = total_expenses_usd * (current_rate.bs_to_usd if current_rate else Decimal('1.00'))

    # Ganancia neta real = ganancia por productos - gastos (ambos en Bs)
    net_profit_real_bs = real_profit_bs - total_expenses_bs
    net_profit_real_usd = real_profit_usd - total_expenses_usd  # ⭐ NUEVO: También en USD

    # Mantener cálculo anterior para comparación
    gross_profit_bs = total_sales_bs - total_purchases_bs
    gross_profit_usd = total_sales_usd - total_purchases_usd
    # ⭐ CORREGIDO: Convertir gastos a Bs antes de restar
    net_profit_bs = gross_profit_bs - total_expenses_bs
    
    # Ganancias por día (para gráfico)
    daily_profits = []
    current_date = start_date
    while current_date <= end_date:
        day_sales = Sale.objects.filter(date__date=current_date).aggregate(
            total=Sum('total_bs')
        )['total'] or Decimal('0.00')
        
        day_purchases = SupplierOrder.objects.filter(
            order_date__date=current_date,
            status='received'
        ).aggregate(
            total=Sum('total_bs')
        )['total'] or Decimal('0.00')
        
        day_expenses_usd = Expense.objects.filter(date=current_date).aggregate(
            total=Sum('amount_usd')  # ⭐ CORREGIDO: Sumar en USD
        )['total'] or Decimal('0.00')

        # ⭐ CORREGIDO: Convertir gastos USD a Bs para el gráfico
        day_expenses_bs = day_expenses_usd * (current_rate.bs_to_usd if current_rate else Decimal('1.00'))

        day_profit = day_sales - day_purchases - day_expenses_bs  # ⭐ CORREGIDO: Restar Bs
        
        daily_profits.append({
            'date': current_date.strftime('%d/%m'),
            'sales': float(day_sales),
            'purchases': float(day_purchases),
            'expenses': float(day_expenses_bs),  # ⭐ CORREGIDO: Usar Bs
            'profit': float(day_profit),
        })
        
        current_date += timedelta(days=1)
    
    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'total_sales_bs': total_sales_bs,
        'total_sales_usd': total_sales_usd,
        'total_purchases_bs': total_purchases_bs,
        'total_purchases_usd': total_purchases_usd,
        'total_expenses': total_expenses_bs,  # ⭐ CORREGIDO: En Bs
        'total_expenses_usd': total_expenses_usd,  # ⭐ NUEVO: En USD
        'gross_profit_bs': gross_profit_bs,
        'gross_profit_usd': gross_profit_usd,
        'net_profit_bs': net_profit_bs,
        # ⭐ NUEVO: Ganancias REALES calculadas por producto
        'real_profit_usd': real_profit_usd,
        'real_profit_bs': real_profit_bs,
        'net_profit_real_bs': net_profit_real_bs,
        'net_profit_real_usd': net_profit_real_usd,  # ⭐ NUEVO: Ganancia neta real en USD
        'daily_profits': daily_profits,
        'sales_count': sales_data['sales_count'],
        'purchases_count': purchases_data['purchases_count'],
        'expenses_count': expenses_data['expenses_count'],
    }

    return render(request, 'finances/profits_report.html', context)

@login_required
def product_profitability_report(request):
    """Vista para el reporte de rentabilidad por producto"""
    form = ReportFilterForm(request.GET or None)

    # Obtener fechas del formulario
    if form.is_valid():
        start_date, end_date = _get_date_range(form.cleaned_data)
    else:
        # Por defecto, este mes
        today = date.today()
        start_date = today.replace(day=1)
        end_date = today

    # Obtener todos los ítems vendidos en el período
    sale_items = SaleItem.objects.filter(
        sale__date__date__gte=start_date,
        sale__date__lte=end_date,
        product__isnull=False
    ).select_related('product')

    # Calcular rentabilidad por producto
    products_profitability = {}

    for item in sale_items:
        # ⭐ VALIDACIÓN: Saltar si no hay producto
        if not item.product:
            continue

        product_id = item.product.id

        if product_id not in products_profitability:
            products_profitability[product_id] = {
                'product': item.product,
                'total_quantity_sold': Decimal('0.00'),
                'total_revenue_usd': Decimal('0.00'),
                'total_cost_usd': Decimal('0.00'),
                'total_profit_usd': Decimal('0.00'),
                'sales_count': 0,
            }

        # Calcular métricas
        quantity = item.quantity
        # ⭐ VALIDACIÓN: Manejar valores None defensivamente
        sale_price = item.price_usd or Decimal('0.00')
        purchase_price = item.product.purchase_price_usd or Decimal('0.00')

        revenue = sale_price * quantity
        cost = purchase_price * quantity
        profit = revenue - cost

        products_profitability[product_id]['total_quantity_sold'] += quantity
        products_profitability[product_id]['total_revenue_usd'] += revenue
        products_profitability[product_id]['total_cost_usd'] += cost
        products_profitability[product_id]['total_profit_usd'] += profit
        products_profitability[product_id]['sales_count'] += 1

    # Convertir a lista y calcular métricas adicionales
    products_list = []
    for data in products_profitability.values():
        # Calcular margen de ganancia porcentual
        if data['total_revenue_usd'] > 0:
            profit_margin = (data['total_profit_usd'] / data['total_revenue_usd']) * 100
        else:
            profit_margin = Decimal('0.00')

        products_list.append({
            'product': data['product'],
            'total_quantity_sold': data['total_quantity_sold'],
            'total_revenue_usd': data['total_revenue_usd'],
            'total_cost_usd': data['total_cost_usd'],
            'total_profit_usd': data['total_profit_usd'],
            'profit_margin': profit_margin,
            'sales_count': data['sales_count'],
        })

    # Ordenar por diferentes criterios
    sort_by = request.GET.get('sort_by', 'profit')  # profit, revenue, quantity, margin

    if sort_by == 'revenue':
        products_list.sort(key=lambda x: x['total_revenue_usd'], reverse=True)
    elif sort_by == 'quantity':
        products_list.sort(key=lambda x: x['total_quantity_sold'], reverse=True)
    elif sort_by == 'margin':
        products_list.sort(key=lambda x: x['profit_margin'], reverse=True)
    else:  # profit (por defecto)
        products_list.sort(key=lambda x: x['total_profit_usd'], reverse=True)

    # Paginar
    paginator = Paginator(products_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calcular totales
    total_revenue = sum(p['total_revenue_usd'] for p in products_list)
    total_cost = sum(p['total_cost_usd'] for p in products_list)
    total_profit = sum(p['total_profit_usd'] for p in products_list)
    total_items_sold = sum(p['total_quantity_sold'] for p in products_list)

    context = {
        'form': form,
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'total_items_sold': total_items_sold,
        'sort_by': sort_by,
    }

    return render(request, 'finances/product_profitability_report.html', context)

# ============================================================================
# GESTIÓN DE GASTOS
# ============================================================================

@login_required
def expense_list(request):
    """Vista para listar gastos"""
    # Filtros
    category = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Consulta base
    expenses = Expense.objects.all()
    
    # Aplicar filtros
    if category:
        expenses = expenses.filter(category=category)
    
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    
    if end_date:
        expenses = expenses.filter(date__lte=end_date)
    
    # Ordenar y paginar
    expenses = expenses.order_by('-date')
    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular total
    total = expenses.aggregate(total=Sum('amount_bs'))['total'] or Decimal('0.00')
    
    # Categorías para el filtro
    categories = Expense.EXPENSE_CATEGORIES
    
    return render(request, 'finances/expense_list.html', {
        'page_obj': page_obj,
        'total': total,
        'categories': categories,
        'selected_category': category,
        'start_date': start_date,
        'end_date': end_date,
    })

@login_required
def expense_detail(request, pk):
    """Vista para ver detalles de un gasto"""
    expense = get_object_or_404(Expense, pk=pk)
    receipts = expense.receipts.all()
    
    return render(request, 'finances/expense_detail.html', {
        'expense': expense,
        'receipts': receipts,
    })

@login_required
def expense_create(request):
    """Vista para crear un nuevo gasto"""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        formset = ExpenseReceiptFormset(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                expense = form.save()
                formset.instance = expense
                formset.save()
                
                messages.success(request, f'Gasto "{expense.description}" registrado exitosamente.')
                return redirect('finances:expense_detail', pk=expense.pk)
    else:
        form = ExpenseForm(user=request.user)
        formset = ExpenseReceiptFormset()

    # Pasar tasa de cambio actual para mostrar USD
    from utils.models import ExchangeRate
    current_rate = ExchangeRate.get_latest_rate()

    return render(request, 'finances/expense_form.html', {
        'form': form,
        'formset': formset,
        'current_rate': current_rate,
        'title': 'Registrar Nuevo Gasto'
    })

@login_required
def expense_update(request, pk):
    """Vista para actualizar un gasto"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        formset = ExpenseReceiptFormset(request.POST, request.FILES, instance=expense)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                expense = form.save()
                formset.save()
                
                messages.success(request, f'Gasto "{expense.description}" actualizado exitosamente.')
                return redirect('finances:expense_detail', pk=expense.pk)
    else:
        form = ExpenseForm(instance=expense, user=request.user)
        formset = ExpenseReceiptFormset(instance=expense)

    # Pasar tasa de cambio actual para mostrar USD
    from utils.models import ExchangeRate
    current_rate = ExchangeRate.get_latest_rate()

    return render(request, 'finances/expense_form.html', {
        'form': form,
        'formset': formset,
        'expense': expense,
        'current_rate': current_rate,
        'title': 'Editar Gasto'
    })

@admin_required
def expense_delete(request, pk):
    """Vista para eliminar un gasto"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        expense_description = expense.description
        expense.delete()
        messages.success(request, f'Gasto "{expense_description}" eliminado exitosamente.')
        return redirect('finances:expense_list')
    
    return render(request, 'finances/expense_confirm_delete.html', {
        'expense': expense
    })

# ============================================================================
# CIERRE DIARIO
# ============================================================================

@login_required
def daily_close_list(request):
    """Vista para listar cierres diarios"""
    closes = DailyClose.objects.all().order_by('-date')
    
    paginator = Paginator(closes, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'finances/daily_close_list.html', {
        'page_obj': page_obj,
    })

@login_required
def daily_close_detail(request, pk):
    """Vista para ver detalles de un cierre diario"""
    close = get_object_or_404(DailyClose, pk=pk)
    
    # Obtener detalles del día
    day_sales = Sale.objects.filter(date__date=close.date)
    day_expenses = Expense.objects.filter(date=close.date)
    
    return render(request, 'finances/daily_close_detail.html', {
        'close': close,
        'day_sales': day_sales,
        'day_expenses': day_expenses,
    })

@login_required
def daily_close_create(request):
    """Vista para crear un cierre diario"""
    if request.method == 'POST':
        form = DailyCloseForm(request.POST, user=request.user)

        if form.is_valid():
            close_date = form.cleaned_data['date']

            # ⭐ CORREGIDO: Usar transacción atómica para prevenir race conditions
            try:
                with transaction.atomic():
                    # Verificar que no exista un cierre para esta fecha
                    if DailyClose.objects.filter(date=close_date).exists():
                        messages.error(request, f'Ya existe un cierre para la fecha {close_date.strftime("%d/%m/%Y")}.')
                        return redirect('finances:daily_close_create')

                    # Calcular métricas del día
                    day_sales = Sale.objects.filter(date__date=close_date)
                    sales_count = day_sales.count()
                    sales_total_bs = day_sales.aggregate(total=Sum('total_bs'))['total'] or Decimal('0.00')

                    day_expenses = Expense.objects.filter(date=close_date)
                    expenses_total_bs = day_expenses.aggregate(total=Sum('amount_bs'))['total'] or Decimal('0.00')

                    profit_bs = sales_total_bs - expenses_total_bs

                    # Crear el cierre
                    close = form.save(commit=False)
                    close.sales_count = sales_count
                    close.sales_total_bs = sales_total_bs
                    close.expenses_total_bs = expenses_total_bs
                    close.profit_bs = profit_bs
                    close.closed_by = request.user
                    close.save()

                    messages.success(request, f'Cierre del {close_date.strftime("%d/%m/%Y")} realizado exitosamente.')
                    return redirect('finances:daily_close_detail', pk=close.pk)
            except Exception as e:
                messages.error(request, f'Error al crear el cierre: {str(e)}')
                return redirect('finances:daily_close_create')
    else:
        form = DailyCloseForm(user=request.user)
    
    # Obtener datos del día para mostrar en el formulario
    today = date.today()
    today_sales = Sale.objects.filter(date__date=today)
    today_sales_count = today_sales.count()
    today_sales_total = today_sales.aggregate(total=Sum('total_bs'))['total'] or Decimal('0.00')
    
    today_expenses = Expense.objects.filter(date=today)
    today_expenses_total = today_expenses.aggregate(total=Sum('amount_bs'))['total'] or Decimal('0.00')
    
    today_profit = today_sales_total - today_expenses_total
    
    return render(request, 'finances/daily_close_form.html', {
        'form': form,
        'today_sales_count': today_sales_count,
        'today_sales_total': today_sales_total,
        'today_expenses_total': today_expenses_total,
        'today_profit': today_profit,
        'title': 'Realizar Cierre Diario'
    })

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_date_range(form_data):
    """Helper para obtener rango de fechas desde el formulario"""
    period = form_data.get('period')
    today = date.today()
    
    if period == 'today':
        return today, today
    elif period == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period == 'this_week':
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == 'last_week':
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return start, end
    elif period == 'this_month':
        start = today.replace(day=1)
        return start, today
    elif period == 'last_month':
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    elif period == 'this_year':
        start = today.replace(month=1, day=1)
        return start, today
    elif period == 'custom':
        return form_data.get('start_date'), form_data.get('end_date')
    
    return None, None