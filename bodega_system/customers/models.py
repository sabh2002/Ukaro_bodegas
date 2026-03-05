# customers/models.py

from django.db import models
from django.urls import reverse

class Customer(models.Model):
    """Modelo para los clientes"""
    name = models.CharField(
        max_length=100,
        verbose_name="Nombre"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Teléfono"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email"
    )
    address = models.TextField(
        blank=True,
        verbose_name="Dirección"
    )
    credit_limit_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Límite de Crédito (Bs)",
        help_text="Límite en Bs (deprecado, usar credit_limit_usd)"
    )
    credit_limit_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Límite de Crédito (USD)",
        help_text="Límite principal en USD"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado el"
    )
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('customers:customer_detail', args=[str(self.id)])
    
    @property
    def total_credit_used(self):
        """Calcula el total de crédito utilizado en USD"""
        from django.db.models import Sum
        total = self.credits.filter(is_paid=False).aggregate(Sum('amount_usd'))
        return total['amount_usd__sum'] or 0

    @property
    def total_credit_used_bs(self):
        """Calcula el total de crédito utilizado en Bs (para compatibilidad)"""
        from django.db.models import Sum
        total = self.credits.filter(is_paid=False).aggregate(Sum('amount_bs'))
        return total['amount_bs__sum'] or 0

    @property
    def available_credit(self):
        """Calcula el crédito disponible en USD"""
        return self.credit_limit_usd - self.total_credit_used

    @property
    def available_credit_bs(self):
        """Calcula el crédito disponible en Bs a tasa actual"""
        from utils.models import ExchangeRate
        rate = ExchangeRate.get_latest_rate()
        if rate:
            return self.available_credit * rate.bs_to_usd
        return 0

    @property
    def credit_limit_bs_current(self):
        """Límite en Bs a tasa actual"""
        from utils.models import ExchangeRate
        rate = ExchangeRate.get_latest_rate()
        if rate:
            return self.credit_limit_usd * rate.bs_to_usd
        return 0

class CustomerCredit(models.Model):
    """Modelo para los créditos de clientes"""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='credits',
        verbose_name="Cliente"
    )
    sale = models.OneToOneField(
        'sales.Sale',
        on_delete=models.PROTECT,
        related_name='credit',
        verbose_name="Venta"
    )
    amount_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto (Bs)"
    )
    amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto (USD)"
    )
    exchange_rate_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Tasa de Cambio Utilizada",
        help_text="Tasa Bs/USD utilizada al crear el crédito"
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    date_due = models.DateField(
        verbose_name="Fecha de Vencimiento"
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name="Pagado"
    )
    date_paid = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Pago"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    
    class Meta:
        verbose_name = "Crédito de Cliente"
        verbose_name_plural = "Créditos de Clientes"
        ordering = ['-date_created']
    
    def __str__(self):
        return f"Crédito de {self.customer.name} - {self.amount_bs} Bs"
    
    def get_absolute_url(self):
        return reverse('customers:credit_detail', args=[str(self.id)])

class CreditPayment(models.Model):
    """Modelo para los pagos de créditos"""

    PAYMENT_METHODS = (
        ('cash', 'Efectivo'),
        ('card', 'Punto de Venta'),
        ('mobile', 'Pago Móvil'),
    )

    credit = models.ForeignKey(
        CustomerCredit,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Crédito"
    )
    amount_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto (Bs)"
    )
    amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto (USD)"
    )
    exchange_rate_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Tasa de Cambio Utilizada",
        help_text="Tasa Bs/USD utilizada al momento del pago"
    )
    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Pago"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash',
        verbose_name="Método de Pago"
    )
    mobile_reference = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Referencia de Pago Móvil"
    )
    received_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='credit_payments',
        verbose_name="Recibido por"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    general_payment = models.ForeignKey(
        'CustomerGeneralPayment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='credit_payments',
        verbose_name="Pago General Origen",
        help_text="Generado automáticamente por un pago general"
    )

    class Meta:
        verbose_name = "Pago de Crédito"
        verbose_name_plural = "Pagos de Créditos"
        ordering = ['-payment_date']

    def __str__(self):
        return f"Pago de {self.amount_bs} Bs - {self.payment_date.strftime('%d/%m/%Y')}"

    def get_payment_method_icon(self):
        """Retorna el icono del método de pago"""
        icons = {
            'cash': '💵',
            'card': '💳',
            'mobile': '📱'
        }
        return icons.get(self.payment_method, '💰')

    def get_payment_method_display_with_icon(self):
        """Retorna el método de pago con icono"""
        icon = self.get_payment_method_icon()
        display = self.get_payment_method_display()
        if self.payment_method == 'mobile' and self.mobile_reference:
            return f"{icon} {display} (Ref: {self.mobile_reference})"
        return f"{icon} {display}"


class CustomerGeneralPayment(models.Model):
    PAYMENT_METHODS = (
        ('card', 'Punto de Venta'),
        ('cash', 'Efectivo'),
        ('mobile', 'Pago Móvil'),
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name='general_payments', verbose_name="Cliente"
    )
    amount_bs = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto (Bs)")
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto (USD)")
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=2,
        verbose_name="Tasa Utilizada")
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS,
        default='cash', verbose_name="Método de Pago")
    mobile_reference = models.CharField(max_length=50, blank=True, null=True,
        verbose_name="Referencia Pago Móvil")
    received_by = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT,
        related_name='general_payments_received', verbose_name="Recibido por"
    )
    notes = models.TextField(blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Pago General de Cliente"
        verbose_name_plural = "Pagos Generales de Clientes"
        ordering = ['-payment_date']

    def __str__(self):
        return f"Pago general {self.customer.name} - ${self.amount_usd} ({self.payment_date.strftime('%d/%m/%Y')})"