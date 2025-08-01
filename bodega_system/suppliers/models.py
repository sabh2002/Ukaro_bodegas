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
    total_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Total (Bs)"
    )
    paid = models.BooleanField(
        default=False,
        verbose_name="Pagado"
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
    
    def __str__(self):
        return f"Orden #{self.id} - {self.supplier.name}"
    
    def get_absolute_url(self):
        return reverse('suppliers:order_detail', args=[str(self.id)])

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
    quantity = models.IntegerField(
        verbose_name="Cantidad"
    )
    price_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Precio (Bs)"
    )
    
    class Meta:
        verbose_name = "Ítem de Orden"
        verbose_name_plural = "Ítems de Órdenes"
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def subtotal(self):
        """Calcula el subtotal del ítem"""
        return self.quantity * self.price_bs