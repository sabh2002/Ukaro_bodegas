# inventory/models.py - PRODUCTOS CON PRECIOS EN USD

from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords
from decimal import Decimal


class Category(models.Model):
    """Modelo para categorías de productos"""
    name = models.CharField(max_length=100, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Modelo para productos con precios en USD"""
    
    UNIT_TYPES = (
        ('unit', 'Unidad'),
        ('kg', 'Kilogramo'),
        ('gram', 'Gramo'), 
        ('liter', 'Litro'),
        ('ml', 'Mililitro'),
    )
    
    name = models.CharField(max_length=200, verbose_name="Nombre")
    barcode = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Código de Barras"
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Categoría"
    )
    description = models.TextField(blank=True, verbose_name="Descripción")
    image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True,
        verbose_name="Imagen"
    )
    unit_type = models.CharField(
        max_length=10, 
        choices=UNIT_TYPES, 
        default='unit',
        verbose_name="Tipo de Unidad"
    )
    
    # ⭐ CAMBIO PRINCIPAL: Precios en USD
    purchase_price_usd = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Precio de Compra (USD)"
    )
    selling_price_usd = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Precio de Venta (USD)"
    )
    
    # Inventario
    stock = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        default=0,
        verbose_name="Stock"
    )
    min_stock = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        default=5,
        verbose_name="Stock Mínimo"
    )
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
    # Precios al mayor (en USD también)
    is_bulk_pricing = models.BooleanField(
        default=False,
        verbose_name="Precio al Mayor"
    )
    bulk_min_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cantidad Mínima al Mayor"
    )
    bulk_price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio al Mayor (USD)"
    )
    
    # Historial para auditoría
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('inventory:product_detail', args=[str(self.id)])
    
    @property
    def stock_status(self):
        """Devuelve el estado del stock"""
        if self.stock <= 0:
            return "Sin stock"
        elif self.stock < self.min_stock:
            return "Stock bajo"
        else:
            return "Stock normal"
    
    @property
    def profit_margin_usd(self):
        """Calcular margen de ganancia en USD"""
        if self.purchase_price_usd > 0:
            return self.selling_price_usd - self.purchase_price_usd
        return 0
    
    @property
    def profit_margin_percentage(self):
        """Calcular porcentaje de margen de ganancia"""
        if self.purchase_price_usd > 0:
            return (self.profit_margin_usd / self.purchase_price_usd) * 100
        return 0
    
    @property
    def unit_display(self):
        """Retorna la unidad para mostrar"""
        return dict(self.UNIT_TYPES)[self.unit_type]
    
    @property
    def is_weight_based(self):
        """Verifica si el producto se vende por peso o volumen variable"""
        return self.unit_type in ['kg', 'gram', 'liter', 'ml']
    
    def get_price_usd_for_quantity(self, quantity):
        """Calcula precio USD según cantidad (considera precios al mayor)"""
        if self.is_bulk_pricing and self.bulk_min_quantity and quantity >= self.bulk_min_quantity:
            return self.bulk_price_usd
        return self.selling_price_usd
    
    def get_price_bs_for_quantity(self, quantity, exchange_rate):
        """Calcula precio en Bs basado en USD y tasa de cambio"""
        price_usd = self.get_price_usd_for_quantity(quantity)
        return price_usd * exchange_rate
    
    def get_current_price_bs(self):
        """Obtiene precio actual en Bs usando la tasa de cambio más reciente"""
        from utils.models import ExchangeRate
        
        latest_rate = ExchangeRate.get_latest_rate()
        if latest_rate:
            return self.selling_price_usd * latest_rate.bs_to_usd
        return Decimal('0.00')
    
    def get_current_purchase_price_bs(self):
        """Obtiene precio de compra actual en Bs"""
        from utils.models import ExchangeRate
        
        latest_rate = ExchangeRate.get_latest_rate()
        if latest_rate:
            return self.purchase_price_usd * latest_rate.bs_to_usd
        return Decimal('0.00')


class InventoryAdjustment(models.Model):
    """Ajuste de inventario"""
    ADJUSTMENT_TYPES = (
        ('add', 'Agregar'),
        ('remove', 'Eliminar'),
        ('set', 'Establecer')
    )
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='adjustments',
        verbose_name="Producto"
    )
    adjustment_type = models.CharField(
        max_length=10, 
        choices=ADJUSTMENT_TYPES,
        verbose_name="Tipo de Ajuste"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Cantidad"
    )
    previous_stock = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Stock Previo"
    )
    new_stock = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        verbose_name="Nuevo Stock"
    )
    reason = models.TextField(verbose_name="Razón")
    adjusted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='inventory_adjustments',
        verbose_name="Ajustado por"
    )
    adjusted_at = models.DateTimeField(auto_now_add=True, verbose_name="Ajustado el")
    
    class Meta:
        verbose_name = "Ajuste de Inventario"
        verbose_name_plural = "Ajustes de Inventario"
        ordering = ['-adjusted_at']
    
    def __str__(self):
        return f"{self.get_adjustment_type_display()} - {self.product.name} - {self.quantity}"


class ProductCombo(models.Model):
    """Modelo para combos de productos - PENDIENTE PARA DESPUÉS"""
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre del Combo"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    # TODO: Cambiar a USD después
    combo_price_bs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio del Combo (Bs)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    
    class Meta:
        verbose_name = "Combo de Productos"
        verbose_name_plural = "Combos de Productos"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ComboItem(models.Model):
    """Ítems que componen un combo - PENDIENTE PARA DESPUÉS"""
    combo = models.ForeignKey(
        ProductCombo,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Combo"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Producto"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name="Cantidad"
    )
    
    class Meta:
        verbose_name = "Ítem de Combo"
        verbose_name_plural = "Ítems de Combo"
        unique_together = ['combo', 'product']
    
    def __str__(self):
        return f"{self.combo.name} - {self.product.name} ({self.quantity})"