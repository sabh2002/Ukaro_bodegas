from django.db import models

# Create your models here.
# inventory/models.py

from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

class Category(models.Model):
    """Categoría de productos"""
    name = models.CharField(max_length=50, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('inventory:category_detail', args=[str(self.id)])

class Product(models.Model):
    UNIT_TYPES = (
        ('unit', 'Unidad'),
        ('kg', 'Kilogramo'),
        ('gram', 'Gramo'),
        ('liter', 'Litro'),
        ('ml', 'Mililitro'),
    )
    """Producto en inventario"""
    name = models.CharField(max_length=100, verbose_name="Nombre")
    barcode = models.CharField(max_length=50, unique=True, verbose_name="Código de Barras")
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='products',
        verbose_name="Categoría"
    )
    unit_type = models.CharField(
        max_length=10,
        choices=UNIT_TYPES,
        default='unit',
        verbose_name="Tipo de Unidad"
    )
    description = models.TextField(blank=True, verbose_name="Descripción")
    image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True,
        verbose_name="Imagen"
    )
    purchase_price_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Precio de Compra (Bs)"
    )
    selling_price_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Precio de Venta (Bs)"
    )
    stock = models.DecimalField(
        max_digits=10, 
        decimal_places=2,  # Permite 0.001 kg precision
        default=0,
        verbose_name="Stock Actual"
    )
    
    min_stock = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=5,
        verbose_name="Stock Mínimo"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
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
    
    bulk_price_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio al Mayor (Bs)"
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
    def profit_margin_bs(self):
        """Calcular margen de ganancia en Bs"""
        if self.purchase_price_bs > 0:
            return self.selling_price_bs - self.purchase_price_bs
        return 0
    
    @property
    def profit_margin_percentage(self):
        """Calcular porcentaje de margen de ganancia"""
        if self.purchase_price_bs > 0:
            return (self.profit_margin_bs / self.purchase_price_bs) * 100
        return 0
    
    @property
    def unit_display(self):
        """Retorna la unidad para mostrar"""
        return dict(self.UNIT_TYPES)[self.unit_type]
    
    @property
    def is_weight_based(self):
        """Verifica si el producto se vende por peso o volumen variable"""
        return self.unit_type in ['kg', 'gram', 'liter', 'ml']
    
    def get_price_for_quantity(self, quantity):
        """Calcula precio según cantidad (considera precios al mayor)"""
        if self.is_bulk_pricing and self.bulk_min_quantity and quantity >= self.bulk_min_quantity:
            return self.bulk_price_bs
        return self.selling_price_bs

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
    # CORREGIDO: Cambiar de IntegerField a DecimalField para soporte de decimales
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
    """Modelo para combos de productos"""
    name = models.CharField(
        max_length=100,
        verbose_name="Nombre del Combo"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    combo_price_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio del Combo (Bs)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el"
    )
    
    class Meta:
        verbose_name = "Combo de Productos"
        verbose_name_plural = "Combos de Productos"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - Bs {self.combo_price_bs}"
    
    @property
    def total_individual_price(self):
        """Calcula precio total si se compraran individualmente"""
        total = 0
        for item in self.items.all():
            total += item.product.selling_price_bs * item.quantity
        return total
    
    @property
    def savings_amount(self):
        """Calcula cuánto se ahorra con el combo"""
        return self.total_individual_price - self.combo_price_bs
    
    @property
    def savings_percentage(self):
        """Calcula porcentaje de ahorro"""
        if self.total_individual_price > 0:
            return (self.savings_amount / self.total_individual_price) * 100
        return 0

class ComboItem(models.Model):
    """Ítems que componen un combo"""
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
        decimal_places=2,
        verbose_name="Cantidad"
    )
    
    class Meta:
        verbose_name = "Ítem de Combo"
        verbose_name_plural = "Ítems de Combo"
        unique_together = ['combo', 'product']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"