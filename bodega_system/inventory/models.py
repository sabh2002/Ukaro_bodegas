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
    """Producto en inventario"""
    name = models.CharField(max_length=100, verbose_name="Nombre")
    barcode = models.CharField(max_length=50, unique=True, verbose_name="Código de Barras")
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
    stock = models.IntegerField(default=0, verbose_name="Stock Actual")
    min_stock = models.IntegerField(default=5, verbose_name="Stock Mínimo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
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
    quantity = models.IntegerField(verbose_name="Cantidad")
    previous_stock = models.IntegerField(verbose_name="Stock Previo")
    new_stock = models.IntegerField(verbose_name="Nuevo Stock")
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