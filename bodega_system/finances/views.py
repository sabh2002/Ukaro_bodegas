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
    today_sales_count = today_sales.count()
    
    today_expenses = Expense.objects.filter(date=today)
    today_expenses_total = today_expenses.aggregate(total=Sum('amount_bs'))['total'] or Decimal('0.00')
    
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
    month_expenses_total = month_expenses.aggregate(total=Sum('amount_bs'))['total'] or Decimal('0.00')
    
    # Calcular ganancia bruta del mes (ventas - compras)
    gross_profit_bs = month_sales_total_bs - month_purchases_total_bs
    gross_profit_usd = month_sales_total_usd - month_purchases_total_usd
    
    # Calcular ganancia neta del mes (ganancia bruta - gastos)
    net_profit_bs = gross_profit_bs - month_expenses_total
    
    # Productos más vendidos este mes
    top_products = SaleItem.objects.filter(
        sale__date__date__gte=this_month_start,
        sale__date__date__lte=today
    ).values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum(F('quantity') * F('price_bs'))
    ).order_by('-total_quantity')[:10]
    
    # Gastos por categoría este mes
    expenses_by_category = month_expenses.values(
        'category'
    ).annotate(
        total=Sum('amount_bs'),
        count=Count('id')
    ).order_by('-total')
    
    # Tasa de cambio actual
    current_rate = ExchangeRate.get_latest_rate()
    
    context = {
        'today_sales_count': today_sales_count,
        'today_sales_total_bs': today_sales_total_bs,
        'today_expenses_total': today_expenses_total,
        'today_profit': today_sales_total_bs - today_expenses_total,
        
        'month_sales_total_bs': month_sales_total_bs,
        'month_sales_total_usd': month_sales_total_usd,
        'month_purchases_total_bs': month_purchases_total_bs,
        'month_purchases_total_usd': month_purchases_total_usd,
        'month_expenses_total': month_expenses_total,
        'gross_profit_bs': gross_profit_bs,
        'gross_profit_usd': gross_profit_usd,
        'net_profit_bs': net_profit_bs,
        
        'top_products': top_products,
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
    """Vista para el reporte de ganancias"""
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
        total_expenses=Sum('amount_bs'),
        expenses_count=Count('id')
    )
    
    # Calcular ganancias
    total_sales_bs = sales_data['total_sales_bs'] or Decimal('0.00')
    total_sales_usd = sales_data['total_sales_usd'] or Decimal('0.00')
    total_purchases_bs = purchases_data['total_purchases_bs'] or Decimal('0.00')
    total_purchases_usd = purchases_data['total_purchases_usd'] or Decimal('0.00')
    total_expenses = expenses_data['total_expenses'] or Decimal('0.00')
    
    gross_profit_bs = total_sales_bs - total_purchases_bs
    gross_profit_usd = total_sales_usd - total_purchases_usd
    net_profit_bs = gross_profit_bs - total_expenses
    
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
        
        day_expenses = Expense.objects.filter(date=current_date).aggregate(
            total=Sum('amount_bs')
        )['total'] or Decimal('0.00')
        
        day_profit = day_sales - day_purchases - day_expenses
        
        daily_profits.append({
            'date': current_date.strftime('%d/%m'),
            'sales': float(day_sales),
            'purchases': float(day_purchases),
            'expenses': float(day_expenses),
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
        'total_expenses': total_expenses,
        'gross_profit_bs': gross_profit_bs,
        'gross_profit_usd': gross_profit_usd,
        'net_profit_bs': net_profit_bs,
        'daily_profits': daily_profits,
        'sales_count': sales_data['sales_count'],
        'purchases_count': purchases_data['purchases_count'],
        'expenses_count': expenses_data['expenses_count'],
    }
    
    return render(request, 'finances/profits_report.html', context)

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
    
    return render(request, 'finances/expense_form.html', {
        'form': form,
        'formset': formset,
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
    
    return render(request, 'finances/expense_form.html', {
        'form': form,
        'formset': formset,
        'expense': expense,
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