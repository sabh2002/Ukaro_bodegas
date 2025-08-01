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
        verbose_name="Límite de Crédito (Bs)"
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
        """Calcula el total de crédito utilizado"""
        from django.db.models import Sum
        total = self.credits.filter(is_paid=False).aggregate(Sum('amount_bs'))
        return total['amount_bs__sum'] or 0
    
    @property
    def available_credit(self):
        """Calcula el crédito disponible"""
        return self.credit_limit_bs - self.total_credit_used

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
    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Pago"
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
    
    class Meta:
        verbose_name = "Pago de Crédito"
        verbose_name_plural = "Pagos de Créditos"
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Pago de {self.amount_bs} Bs - {self.payment_date.strftime('%d/%m/%Y')}"