# finances/models.py

from django.db import models
from django.urls import reverse

class Expense(models.Model):
    """Modelo para gastos adicionales (no relacionados a compras de productos)"""
    EXPENSE_CATEGORIES = (
        ('rent', 'Alquiler'),
        ('utilities', 'Servicios'),
        ('salaries', 'Salarios'),
        ('maintenance', 'Mantenimiento'),
        ('taxes', 'Impuestos'),
        ('other', 'Otros'),
    )
    
    category = models.CharField(
        max_length=20,
        choices=EXPENSE_CATEGORIES,
        verbose_name="Categoría"
    )
    description = models.CharField(
        max_length=255,
        verbose_name="Descripción"
    )
    amount_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Monto (Bs)"
    )
    date = models.DateField(
        verbose_name="Fecha"
    )
    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Número de Recibo"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name="Creado por"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el"
    )
    
    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.description} - {self.amount_bs} Bs"

class DailyClose(models.Model):
    """Modelo para cierre diario"""
    date = models.DateField(
        unique=True,
        verbose_name="Fecha"
    )
    sales_count = models.IntegerField(
        verbose_name="Cantidad de Ventas"
    )
    sales_total_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Total Ventas (Bs)"
    )
    expenses_total_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Total Gastos (Bs)"
    )
    profit_bs = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Ganancia (Bs)"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    closed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='daily_closes',
        verbose_name="Cerrado por"
    )
    closed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Cerrado el"
    )
    
    class Meta:
        verbose_name = "Cierre Diario"
        verbose_name_plural = "Cierres Diarios"
        ordering = ['-date']
    
    def __str__(self):
        return f"Cierre del {self.date.strftime('%d/%m/%Y')}"