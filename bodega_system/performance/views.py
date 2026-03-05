# performance/views.py

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.shortcuts import render

from finances.forms import ReportFilterForm
from utils.decorators import admin_required
from utils.models import ExchangeRate


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_user_stats(start_date, end_date):
    """Retorna estadísticas de ventas por usuario para el rango dado."""
    from sales.models import Sale, SaleItem

    money_field = DecimalField(max_digits=15, decimal_places=2)

    # Query 1: ventas por usuario
    sales_by_user = (
        Sale.objects.filter(date__date__gte=start_date, date__date__lte=end_date)
        .values('user__id', 'user__username')
        .annotate(
            sales_count=Count('id'),
            total_usd=Sum('total_usd'),
            total_bs=Sum('total_bs'),
        )
        .order_by('-total_usd')
    )

    # Query 2: COGS + revenue por usuario
    item_stats = (
        SaleItem.objects
        .filter(
            sale__date__date__gte=start_date,
            sale__date__date__lte=end_date,
            product__isnull=False,
        )
        .values('sale__user_id')
        .annotate(
            total_revenue=Sum(
                ExpressionWrapper(F('price_usd') * F('quantity'), output_field=money_field)
            ),
            total_cogs=Sum(
                ExpressionWrapper(
                    F('product__purchase_price_usd') * F('quantity'),
                    output_field=money_field,
                )
            ),
        )
    )

    item_dict = {row['sale__user_id']: row for row in item_stats}

    result = []
    for row in sales_by_user:
        uid = row['user__id']
        items = item_dict.get(uid, {})
        revenue = items.get('total_revenue') or Decimal('0')
        cogs = items.get('total_cogs') or Decimal('0')
        result.append({
            'user_id': uid,
            'username': row['user__username'],
            'sales_count': row['sales_count'],
            'total_usd': row['total_usd'] or Decimal('0'),
            'total_bs': row['total_bs'] or Decimal('0'),
            'gross_profit_usd': revenue - cogs,
        })

    return result


def _get_date_range(form_data):
    """Helper para obtener rango de fechas desde el formulario de filtros."""
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


# ============================================================================
# VISTAS
# ============================================================================

@admin_required
def performance_dashboard(request):
    """Dashboard de rendimiento por usuario — solo administradores."""
    today = date.today()
    month_start = today.replace(day=1)

    # Paneles fijos: HOY y ESTE MES
    today_stats = _get_user_stats(today, today)
    month_stats = _get_user_stats(month_start, today)

    # Filtro por período (GET)
    form = ReportFilterForm(request.GET or None, initial={'period': 'this_month'})
    if form.is_valid():
        start_date, end_date = _get_date_range(form.cleaned_data)
    else:
        start_date, end_date = month_start, today

    period_stats = _get_user_stats(start_date, end_date)

    # Datos para Chart.js (período filtrado)
    chart_labels = [s['username'] for s in period_stats]
    chart_values_usd = [float(s['total_usd']) for s in period_stats]
    chart_values_profit = [float(s['gross_profit_usd']) for s in period_stats]

    # Tasa de cambio actual
    current_rate = ExchangeRate.get_latest_rate()

    context = {
        'today_stats': today_stats,
        'month_stats': month_stats,
        'period_stats': period_stats,
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'chart_labels': chart_labels,
        'chart_values_usd': chart_values_usd,
        'chart_values_profit': chart_values_profit,
        'current_rate': current_rate,
        'current_month': today.strftime('%B %Y'),
        'today': today,
    }

    return render(request, 'performance/dashboard.html', context)
