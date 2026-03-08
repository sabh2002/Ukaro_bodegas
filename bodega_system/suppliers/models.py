# suppliers/models.py

from django.db import models
from django.urls import reverse
from inventory.models import Product

class Supplier(models.Model):
    """Modelo para los proveedores"""
    name = models.CharField(
        max_length=100,
        verbose_name="Nombre"
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Persona de Contacto"
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
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('suppliers:supplier_detail', args=[str(self.id)])

class SupplierOrder(models.Model):
    """Modelo para órdenes de compra a proveedores"""
    ORDER_STATUS = (
        ('pending', 'Pendiente'),
        ('received', 'Recibido'),
        ('cancelled', 'Cancelado'),
    )
    
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Proveedor"
    )
    order_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Orden"
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS,
        default='pending',
        verbose_name="Estado"
    )
    received_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Recepción"
    )
    total_usd = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=0,
        verbose_name="Total (USD)"
    )
    total_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=0,
        verbose_name="Total (Bs)"
    )
    exchange_rate_used = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=1,
        verbose_name="Tasa de Cambio Utilizada",
        help_text="Tasa Bs/USD utilizada en esta orden"
    )
    paid = models.BooleanField(
        default=False,
        verbose_name="Pagado",
        help_text="Marca manual de orden completamente pagada"
    )
    paid_amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Monto Pagado (USD)",
        help_text="Total pagado hasta ahora en USD"
    )
    paid_amount_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Monto Pagado (Bs)",
        help_text="Total pagado hasta ahora en Bs"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='supplier_orders',
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Orden de Proveedor"
        verbose_name_plural = "Órdenes de Proveedores"
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['supplier', 'status'], name='order_supplier_status_idx'),
            models.Index(fields=['status', '-order_date'], name='order_status_date_idx'),
            models.Index(fields=['paid', '-order_date'], name='order_paid_date_idx'),
        ]
    
    def __str__(self):
        supplier_name = self.supplier.name if hasattr(self, 'supplier') and self.supplier else "Sin proveedor"
        return f"Orden #{self.id if self.id else 'Nueva'} - {supplier_name}"
    
    def get_absolute_url(self):
        return reverse('suppliers:order_detail', args=[str(self.id)])

    def calculate_total_usd(self):
        """Calcula el total en USD sumando todos los items"""
        return sum(item.subtotal_usd for item in self.items.all())

    def calculate_total_bs(self):
        """Calcula el total en Bs sumando todos los items (con precio histórico)"""
        return sum(item.subtotal_bs for item in self.items.all())

    def get_current_total_bs(self):
        """Calcula el total actual en Bs con la tasa de cambio actual"""
        from utils.models import ExchangeRate
        from decimal import Decimal

        latest_rate = ExchangeRate.get_latest_rate()
        if latest_rate:
            return self.calculate_total_usd() * latest_rate.bs_to_usd
        return Decimal('0.00')

    def update_totals(self, save=True):
        """
        Recalcula y actualiza los totales de la orden

        Args:
            save (bool): Si True, guarda los cambios en la base de datos

        Returns:
            self: La instancia actualizada para encadenar métodos

        Raises:
            ValueError: Si no hay tasa de cambio configurada
        """
        from utils.models import ExchangeRate

        self.total_usd = self.calculate_total_usd()

        latest_rate = ExchangeRate.get_latest_rate()
        if not latest_rate:
            raise ValueError("No hay tasa de cambio configurada")

        self.total_bs = self.total_usd * latest_rate.bs_to_usd
        self.exchange_rate_used = latest_rate.bs_to_usd

        if save:
            self.save()

        return self

    @property
    def price_difference_bs(self):
        """Diferencia entre precio histórico y precio actual en Bs"""
        return self.get_current_total_bs() - self.total_bs

    @property
    def exchange_rate_changed(self):
        """Verifica si la tasa de cambio ha cambiado desde la creación de la orden"""
        from utils.models import ExchangeRate
        from decimal import Decimal

        latest_rate = ExchangeRate.get_latest_rate()
        if not latest_rate:
            return False

        return abs(self.exchange_rate_used - latest_rate.bs_to_usd) > Decimal('0.01')

    @property
    def outstanding_balance_usd(self):
        """Saldo pendiente por pagar en USD"""
        from decimal import Decimal
        return max(self.total_usd - self.paid_amount_usd, Decimal('0'))

    @property
    def outstanding_balance_bs(self):
        """Saldo pendiente por pagar en Bs"""
        from decimal import Decimal
        return max(self.total_bs - self.paid_amount_bs, Decimal('0'))

    @property
    def payment_status(self):
        """Estado de pago de la orden"""
        from decimal import Decimal

        if self.paid_amount_usd >= self.total_usd:
            return 'paid'  # Completamente pagado
        elif self.paid_amount_usd > Decimal('0'):
            return 'partial'  # Pago parcial
        else:
            return 'unpaid'  # Sin pagar

    @property
    def payment_status_display(self):
        """Texto legible del estado de pago"""
        statuses = {
            'paid': 'Pagado',
            'partial': 'Pago Parcial',
            'unpaid': 'Sin Pagar'
        }
        return statuses.get(self.payment_status, 'Desconocido')

    def update_payment_totals(self):
        """Actualiza los totales pagados basándose en los pagos registrados"""
        from decimal import Decimal

        payments = self.payments.all()
        self.paid_amount_usd = sum(p.amount_usd for p in payments) or Decimal('0')
        self.paid_amount_bs = sum(p.amount_bs for p in payments) or Decimal('0')

        # Actualizar flag 'paid' si está completamente pagado
        self.paid = (self.paid_amount_usd >= self.total_usd)

        self.save()
        return self

class SupplierOrderItem(models.Model):
    """Modelo para ítems de órdenes de compra"""
    order = models.ForeignKey(
        SupplierOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Orden"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='supplier_order_items',
        verbose_name="Producto"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Cantidad"
    )
    price_usd = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=0,
        verbose_name="Precio (USD)"
    )
    price_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Precio (Bs)",
        help_text="Se calcula automáticamente basado en USD y tasa de cambio"
    )
    selling_price_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio de Venta (USD)",
        help_text="Precio de venta sugerido al recibir la orden"
    )

    class Meta:
        verbose_name = "Ítem de Orden"
        verbose_name_plural = "Ítems de Órdenes"
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def save(self, *args, **kwargs):
        """Calcular precio en Bs automáticamente antes de guardar"""
        if self.price_usd:
            from utils.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if not latest_rate:
                raise ValueError(
                    "No hay tasa de cambio configurada. "
                    "Configure una tasa en el sistema antes de crear órdenes de compra."
                )
            self.price_bs = self.price_usd * latest_rate.bs_to_usd
        super().save(*args, **kwargs)
    
    @property
    def subtotal_usd(self):
        """Calcula el subtotal en USD"""
        return self.quantity * self.price_usd
    
    @property
    def subtotal_bs(self):
        """Calcula el subtotal en Bs"""
        return self.quantity * self.price_bs
    
    @property
    def subtotal(self):
        """Alias para subtotal_bs (compatibilidad)"""
        return self.subtotal_bs

    def get_current_price_bs(self):
        """Calcula el precio actual en Bs con la tasa de cambio actual"""
        from utils.models import ExchangeRate
        from decimal import Decimal

        latest_rate = ExchangeRate.get_latest_rate()
        if latest_rate:
            return self.price_usd * latest_rate.bs_to_usd
        return Decimal('0.00')

    @property
    def current_subtotal_bs(self):
        """Calcula el subtotal actual en Bs con la tasa de cambio actual"""
        return self.quantity * self.get_current_price_bs()


class SupplierPayment(models.Model):
    """Modelo para registrar pagos a proveedores"""

    PAYMENT_METHODS = (
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia'),
        ('check', 'Cheque'),
        ('card', 'Tarjeta'),
        ('other', 'Otro'),
    )

    order = models.ForeignKey(
        SupplierOrder,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Orden"
    )
    amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto (USD)"
    )
    amount_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto (Bs)"
    )
    exchange_rate_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Tasa de Cambio Utilizada",
        help_text="Tasa Bs/USD utilizada en este pago"
    )
    payment_date = models.DateTimeField(
        verbose_name="Fecha de Pago"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash',
        verbose_name="Método de Pago"
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Referencia",
        help_text="Número de cheque, referencia de transferencia, etc."
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='supplier_payments',
        verbose_name="Registrado por"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el"
    )

    class Meta:
        verbose_name = "Pago a Proveedor"
        verbose_name_plural = "Pagos a Proveedores"
        ordering = ['-payment_date']

    def __str__(self):
        return f"Pago ${self.amount_usd} USD - Orden #{self.order.id}"

    def save(self, *args, **kwargs):
        """Calcular monto en Bs automáticamente antes de guardar"""
        if self.amount_usd and not self.amount_bs:
            from utils.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if not latest_rate:
                raise ValueError(
                    "No hay tasa de cambio configurada. "
                    "Configure una tasa antes de registrar pagos."
                )
            self.exchange_rate_used = latest_rate.bs_to_usd
            self.amount_bs = self.amount_usd * latest_rate.bs_to_usd

        super().save(*args, **kwargs)

        # Actualizar totales de la orden
        self.order.update_payment_totals()

    def delete(self, *args, **kwargs):
        """Actualizar totales de la orden al eliminar un pago"""
        order = self.order
        super().delete(*args, **kwargs)
        order.update_payment_totals()

    def get_absolute_url(self):
        return reverse('suppliers:payment_detail', args=[str(self.id)])