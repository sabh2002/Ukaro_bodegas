# finances/models.py

from django.db import models
from django.urls import reverse

class Expense(models.Model):
    """Modelo para gastos adicionales (no relacionados a compras de productos)"""
    EXPENSE_CATEGORIES = (
        ('salaries', 'Sueldos de Empleados'),
        ('repairs', 'Reparaciones'),
        ('improvements', 'Mejoras en la Bodega'),
        ('supplies', 'Materiales de Trabajo'),
        ('rent', 'Alquiler'),
        ('utilities', 'Servicios (Luz, Agua, Internet)'),
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
    amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto (USD)"
    )
    exchange_rate_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Tasa de Cambio Utilizada",
        help_text="Tasa Bs/USD utilizada al registrar el gasto"
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
    
    def get_absolute_url(self):
        return reverse('finances:expense_detail', args=[str(self.id)])

class ExpenseReceipt(models.Model):
    """Modelo para comprobantes de gastos"""
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name="Gasto"
    )
    file = models.FileField(
        upload_to='expense_receipts/%Y/%m/',
        verbose_name="Archivo"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Descripción"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Subido el"
    )
    
    class Meta:
        verbose_name = "Comprobante de Gasto"
        verbose_name_plural = "Comprobantes de Gastos"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Comprobante - {self.expense.description}"

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