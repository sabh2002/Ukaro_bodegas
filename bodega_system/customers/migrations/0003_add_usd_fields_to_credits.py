# Generated manually - Add USD fields to Customer, CustomerCredit and CreditPayment models

from django.db import migrations, models
from decimal import Decimal


def populate_customer_credit_usd_fields(apps, schema_editor):
    """Poblar campos USD para créditos y clientes existentes"""
    Customer = apps.get_model('customers', 'Customer')
    CustomerCredit = apps.get_model('customers', 'CustomerCredit')
    CreditPayment = apps.get_model('customers', 'CreditPayment')
    ExchangeRate = apps.get_model('utils', 'ExchangeRate')

    # Obtener tasa de cambio más reciente
    try:
        latest_rate = ExchangeRate.objects.latest('created_at')
        rate = latest_rate.bs_to_usd
    except ExchangeRate.DoesNotExist:
        # Fallback si no hay tasa configurada
        rate = Decimal('36.00')

    # 1. Actualizar clientes: convertir credit_limit_bs a credit_limit_usd
    for customer in Customer.objects.all():
        if customer.credit_limit_bs > 0:
            customer.credit_limit_usd = customer.credit_limit_bs / rate
        else:
            customer.credit_limit_usd = Decimal('0.00')
        customer.save()

    # 2. Actualizar créditos: intentar obtener datos de la venta asociada
    for credit in CustomerCredit.objects.all():
        if credit.sale:
            # Si tiene venta asociada, usar los datos de la venta
            credit.amount_usd = credit.sale.total_usd
            credit.exchange_rate_used = credit.sale.exchange_rate_used
        else:
            # Fallback: calcular con tasa actual
            credit.amount_usd = credit.amount_bs / rate
            credit.exchange_rate_used = rate
        credit.save()

    # 3. Actualizar pagos: calcular USD con tasa actual
    for payment in CreditPayment.objects.all():
        payment.amount_usd = payment.amount_bs / rate
        payment.exchange_rate_used = rate
        payment.save()


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0002_initial'),
        ('utils', '0001_initial'),  # Dependencia de ExchangeRate
        ('sales', '0001_initial'),  # Dependencia de Sale
    ]

    operations = [
        # 1. CustomerCredit - Agregar campos USD
        migrations.AddField(
            model_name='customercredit',
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
            model_name='customercredit',
            name='exchange_rate_used',
            field=models.DecimalField(
                decimal_places=2,
                default=36.00,
                help_text='Tasa Bs/USD utilizada al crear el crédito',
                max_digits=12,
                verbose_name='Tasa de Cambio Utilizada'
            ),
            preserve_default=False,
        ),

        # 2. CreditPayment - Agregar campos USD
        migrations.AddField(
            model_name='creditpayment',
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
            model_name='creditpayment',
            name='exchange_rate_used',
            field=models.DecimalField(
                decimal_places=2,
                default=36.00,
                help_text='Tasa Bs/USD utilizada al momento del pago',
                max_digits=12,
                verbose_name='Tasa de Cambio Utilizada'
            ),
            preserve_default=False,
        ),

        # 3. Customer - Agregar credit_limit_usd
        migrations.AddField(
            model_name='customer',
            name='credit_limit_usd',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Límite principal en USD',
                max_digits=12,
                verbose_name='Límite de Crédito (USD)'
            ),
        ),

        # 4. Customer - Actualizar help_text de credit_limit_bs
        migrations.AlterField(
            model_name='customer',
            name='credit_limit_bs',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Límite en Bs (deprecado, usar credit_limit_usd)',
                max_digits=12,
                verbose_name='Límite de Crédito (Bs)'
            ),
        ),

        # 5. Poblar datos para registros existentes
        migrations.RunPython(
            populate_customer_credit_usd_fields,
            reverse_code=migrations.RunPython.noop
        ),
    ]
