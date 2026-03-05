# Generated manually on 2026-02-24

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('suppliers', '0005_alter_supplierorderitem_price_bs'),
    ]

    operations = [
        # Agregar campos de pago a SupplierOrder
        migrations.AddField(
            model_name='supplierorder',
            name='paid_amount_usd',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Total pagado hasta ahora en USD', max_digits=12, verbose_name='Monto Pagado (USD)'),
        ),
        migrations.AddField(
            model_name='supplierorder',
            name='paid_amount_bs',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Total pagado hasta ahora en Bs', max_digits=12, verbose_name='Monto Pagado (Bs)'),
        ),
        migrations.AlterField(
            model_name='supplierorder',
            name='paid',
            field=models.BooleanField(default=False, help_text='Marca manual de orden completamente pagada', verbose_name='Pagado'),
        ),
        # Crear modelo SupplierPayment
        migrations.CreateModel(
            name='SupplierPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_usd', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Monto (USD)')),
                ('amount_bs', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Monto (Bs)')),
                ('exchange_rate_used', models.DecimalField(decimal_places=2, help_text='Tasa Bs/USD utilizada en este pago', max_digits=12, verbose_name='Tasa de Cambio Utilizada')),
                ('payment_date', models.DateTimeField(verbose_name='Fecha de Pago')),
                ('payment_method', models.CharField(choices=[('cash', 'Efectivo'), ('transfer', 'Transferencia'), ('check', 'Cheque'), ('card', 'Tarjeta'), ('other', 'Otro')], default='cash', max_length=20, verbose_name='Método de Pago')),
                ('reference', models.CharField(blank=True, help_text='Número de cheque, referencia de transferencia, etc.', max_length=100, verbose_name='Referencia')),
                ('notes', models.TextField(blank=True, verbose_name='Notas')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creado el')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='supplier_payments', to=settings.AUTH_USER_MODEL, verbose_name='Registrado por')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='suppliers.supplierorder', verbose_name='Orden')),
            ],
            options={
                'verbose_name': 'Pago a Proveedor',
                'verbose_name_plural': 'Pagos a Proveedores',
                'ordering': ['-payment_date'],
            },
        ),
    ]
