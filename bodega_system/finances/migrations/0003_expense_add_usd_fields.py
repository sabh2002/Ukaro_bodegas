# Generated manually - Add USD fields to Expense model

from django.db import migrations, models
from decimal import Decimal


def populate_usd_fields(apps, schema_editor):
    """Poblar campos USD para gastos existentes usando tasa actual"""
    Expense = apps.get_model('finances', 'Expense')
    ExchangeRate = apps.get_model('utils', 'ExchangeRate')

    # Obtener tasa de cambio más reciente
    try:
        latest_rate = ExchangeRate.objects.latest('date')
        rate = latest_rate.bs_to_usd
    except ExchangeRate.DoesNotExist:
        # Fallback si no hay tasa configurada
        rate = Decimal('36.00')

    # Actualizar todos los gastos existentes
    for expense in Expense.objects.all():
        expense.exchange_rate_used = rate
        expense.amount_usd = expense.amount_bs / rate
        expense.save()


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0002_alter_expense_category_expensereceipt'),
        ('utils', '0001_initial'),  # Dependencia de ExchangeRate
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='amount_usd',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
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
                default=36.00,
                help_text='Tasa Bs/USD utilizada al registrar el gasto',
                max_digits=12,
                verbose_name='Tasa de Cambio Utilizada'
            ),
            preserve_default=False,
        ),
        # Poblar datos para registros existentes
        migrations.RunPython(populate_usd_fields, reverse_code=migrations.RunPython.noop),
    ]
