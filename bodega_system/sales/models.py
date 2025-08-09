# sales/models.py - Modelo SaleItem corregido

from django.db import models
from django.urls import reverse
from inventory.models import Product

class Sale(models.Model):
    """Modelo para las ventas"""
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
    total_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Total (Bs)"
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
    # NUEVO: Referencias para combos
    combo = models.ForeignKey(
        'inventory.ProductCombo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='combo_sales',  # Cambiado para evitar conflictos
        verbose_name="Combo"
    )
    # CORREGIDO: Cantidad ahora decimal para peso
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name="Cantidad"
    )
    price_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Precio (Bs)"
    )
    
    class Meta:
        verbose_name = "Ítem de Venta"
        verbose_name_plural = "Ítems de Venta"
    
    def __str__(self):
        if self.is_combo_sale:
            return f"{self.quantity} x COMBO: {self.combo.name}"
        else:
            return f"{self.quantity} x {self.product.name}"
    
    @property
    def subtotal(self):
        """Calcula el subtotal del ítem"""
        return self.quantity * self.price_bs
    
    @property
    def is_combo_sale(self):
        """Verifica si es venta de combo"""
        return self.combo is not None
    
    @property
    def item_description(self):
        """Descripción del ítem vendido"""
        if self.is_combo_sale:
            return f"COMBO: {self.combo.name}"
        else:
            unit = self.product.unit_display if self.product.unit_type != 'unit' else ''
            return f"{self.product.name} ({self.quantity} {unit})"