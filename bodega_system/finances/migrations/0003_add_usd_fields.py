# Generated manually for USD currency support

from django.db import migrations, models
from decimal import Decimal


def convert_existing_expenses_to_usd(apps, schema_editor):
    """
    Migración de datos: Convertir gastos existentes de Bs a USD
    usando la tasa de cambio de la fecha del gasto
    """
    Expense = apps.get_model('finances', 'Expense')
    ExchangeRate = apps.get_model('utils', 'ExchangeRate')

    for expense in Expense.objects.all():
        # Intentar obtener la tasa de cambio de la fecha del gasto
        try:
            rate = ExchangeRate.objects.filter(
                date__lte=expense.date
            ).order_by('-date').first()

            if rate:
                # Convertir de Bs a USD: amount_usd = amount_bs / rate.bs_to_usd
                expense.amount_usd = expense.amount_bs / rate.bs_to_usd
                expense.exchange_rate_used = rate.bs_to_usd
            else:
                # Si no hay tasa, usar una tasa por defecto de 36.00 (aproximada)
                default_rate = Decimal('36.00')
                expense.amount_usd = expense.amount_bs / default_rate
                expense.exchange_rate_used = default_rate

            expense.save()

        except Exception as e:
            # Si falla, usar tasa por defecto
            default_rate = Decimal('36.00')
            expense.amount_usd = expense.amount_bs / default_rate
            expense.exchange_rate_used = default_rate
            expense.save()


def convert_existing_daily_closes_to_usd(apps, schema_editor):
    """
    Migración de datos: Convertir cierres diarios existentes de Bs a USD
    """
    DailyClose = apps.get_model('finances', 'DailyClose')
    ExchangeRate = apps.get_model('utils', 'ExchangeRate')

    for close in DailyClose.objects.all():
        # Intentar obtener la tasa de cambio de la fecha del cierre
        try:
            rate = ExchangeRate.objects.filter(
                date__lte=close.date
            ).order_by('-date').first()

            if rate:
                bs_to_usd = rate.bs_to_usd
            else:
                # Tasa por defecto
                bs_to_usd = Decimal('36.00')

            # Convertir de Bs a USD
            close.sales_total_usd = close.sales_total_bs / bs_to_usd
            close.expenses_total_usd = close.expenses_total_bs / bs_to_usd

            # Para ganancias antiguas, usar el método simplificado
            # (no podemos recalcular la ganancia real sin los datos históricos)
            close.real_profit_usd = close.profit_bs / bs_to_usd
            close.net_profit_usd = close.real_profit_usd  # Misma que real porque ya incluía gastos
            close.exchange_rate_used = bs_to_usd

            close.save()

        except Exception as e:
            # Si falla, usar tasa por defecto
            default_rate = Decimal('36.00')
            close.sales_total_usd = close.sales_total_bs / default_rate
            close.expenses_total_usd = close.expenses_total_bs / default_rate
            close.real_profit_usd = close.profit_bs / default_rate
            close.net_profit_usd = close.real_profit_usd
            close.exchange_rate_used = default_rate
            close.save()


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0002_alter_expense_category_expensereceipt'),
        ('utils', '0001_initial'),  # Necesitamos ExchangeRate
    ]

    operations = [
        # ====================
        # EXPENSE MODEL
        # ====================

        # Agregar campos USD al modelo Expense
        migrations.AddField(
            model_name='expense',
            name='amount_usd',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                help_text='Monto en dólares estadounidenses',
                max_digits=12,
                verbose_name='Monto (USD)'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='expense',
            name='exchange_rate_used',
            field=models.DecimalField(
                decimal_places=2,
                default=1.00,
                help_text='Tasa de cambio al momento de registrar el gasto',
                max_digits=10,
                verbose_name='Tasa de Cambio Usada'
            ),
        ),

        # Modificar campo amount_bs para agregar help_text
        migrations.AlterField(
            model_name='expense',
            name='amount_bs',
            field=models.DecimalField(
                decimal_places=2,
                help_text='Monto en bolívares (conversión automática)',
                max_digits=12,
                verbose_name='Monto (Bs)'
            ),
        ),

        # ====================
        # DAILY CLOSE MODEL
        # ====================

        # Agregar campos USD al modelo DailyClose
        migrations.AddField(
            model_name='dailyclose',
            name='sales_total_usd',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                help_text='Total de ventas en dólares',
                max_digits=12,
                verbose_name='Total Ventas (USD)'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dailyclose',
            name='expenses_total_usd',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                help_text='Total de gastos en dólares',
                max_digits=12,
                verbose_name='Total Gastos (USD)'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dailyclose',
            name='real_profit_usd',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                help_text='Ganancia calculada: (precio_venta - precio_compra) × cantidad',
                max_digits=12,
                verbose_name='Ganancia Real (USD)'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dailyclose',
            name='net_profit_usd',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                help_text='Ganancia real menos gastos',
                max_digits=12,
                verbose_name='Ganancia Neta (USD)'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dailyclose',
            name='exchange_rate_used',
            field=models.DecimalField(
                decimal_places=2,
                default=1.00,
                help_text='Tasa Bs/USD usada para el cierre',
                max_digits=10,
                verbose_name='Tasa de Cambio'
            ),
        ),

        # Modificar campos existentes para agregar help_text
        migrations.AlterField(
            model_name='dailyclose',
            name='sales_total_bs',
            field=models.DecimalField(
                decimal_places=2,
                help_text='Total de ventas en bolívares',
                max_digits=12,
                verbose_name='Total Ventas (Bs)'
            ),
        ),
        migrations.AlterField(
            model_name='dailyclose',
            name='expenses_total_bs',
            field=models.DecimalField(
                decimal_places=2,
                help_text='Total de gastos en bolívares',
                max_digits=12,
                verbose_name='Total Gastos (Bs)'
            ),
        ),
        migrations.AlterField(
            model_name='dailyclose',
            name='profit_bs',
            field=models.DecimalField(
                decimal_places=2,
                help_text='Ganancia en bolívares (referencia)',
                max_digits=12,
                verbose_name='Ganancia (Bs)'
            ),
        ),

        # ====================
        # DATA MIGRATION
        # ====================

        # Convertir gastos existentes de Bs a USD
        migrations.RunPython(
            convert_existing_expenses_to_usd,
            reverse_code=migrations.RunPython.noop
        ),

        # Convertir cierres diarios existentes de Bs a USD
        migrations.RunPython(
            convert_existing_daily_closes_to_usd,
            reverse_code=migrations.RunPython.noop
        ),
    ]
