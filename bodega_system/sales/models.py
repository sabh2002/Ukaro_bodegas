# sales/models.py - ACTUALIZADO CON MÉTODOS DE PAGO + USD

from django.db import models
from django.urls import reverse
from inventory.models import Product

class Sale(models.Model):
    """Modelo para las ventas"""
    
    PAYMENT_METHODS = (
        ('cash', 'Efectivo'),
        ('card', 'Punto de Venta'),
        ('mobile', 'Pago Móvil'),
    )
    
    customer = models.ForeignKey(
        'customers.Customer', 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='sales',
        verbose_name="Cliente"
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name="Usuario"
    )
    date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )
    
    # Total en Bs para mostrar en interfaz
    total_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Total (Bs)"
    )
    
    # Total en USD y tasa utilizada para historial
    total_usd = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Total (USD)"
    )
    exchange_rate_used = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Tasa de Cambio Utilizada",
        help_text="Tasa Bs/USD utilizada en esta venta"
    )
    
    # NUEVO: Métodos de pago
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
    
    is_credit = models.BooleanField(
        default=False,
        verbose_name="Es Crédito"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    
    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-date']
    
    def __str__(self):
        return f"Venta #{self.id} - {self.date.strftime('%d/%m/%Y %H:%M')}"
    
    def get_absolute_url(self):
        return reverse('sales:sale_detail', args=[str(self.id)])
    
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
    
    @property
    def item_count(self):
        """Devuelve la cantidad de ítems en la venta"""
        return self.items.aggregate(models.Sum('quantity'))['quantity__sum'] or 0


class SaleItem(models.Model):
    """Modelo para los ítems de una venta"""
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Venta"
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name="Producto",
        null=True,
        blank=True
    )
    combo = models.ForeignKey(
        'inventory.ProductCombo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='combo_sales',
        verbose_name="Combo"
    )
    
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        verbose_name="Cantidad"
    )
    
    # Precio en Bs para mostrar en recibos
    price_bs = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Precio Unitario (Bs)"
    )
    
    # Precio en USD para historial
    price_usd = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Precio Unitario (USD)"
    )
    
    class Meta:
        verbose_name = "Ítem de Venta"
        verbose_name_plural = "Ítems de Venta"
        ordering = ['id']
    
    def __str__(self):
        product_name = self.product.name if self.product else f"COMBO: {self.combo.name}"
        return f"{product_name} - {self.quantity}"
    
    @property
    def subtotal_bs(self):
        """Subtotal en bolívares"""
        return self.quantity * self.price_bs
    
    @property
    def subtotal_usd(self):
        """Subtotal en dólares"""
        return self.quantity * self.price_usd
    
    # Mantener compatibilidad con templates existentes
    @property
    def subtotal(self):
        """Alias para subtotal_bs (compatibilidad)"""
        return self.subtotal_bs