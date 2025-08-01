# utils/models.py

from django.db import models
from django.utils import timezone

class ExchangeRate(models.Model):
    """Modelo para la tasa de cambio Bs/USD"""
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    bs_to_usd = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Tasa Bs/USD"
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='exchange_rates',
        verbose_name="Actualizado por"
    )
    
    class Meta:
        verbose_name = "Tasa de Cambio"
        verbose_name_plural = "Tasas de Cambio"
        ordering = ['-date']
        get_latest_by = 'date'
    
    def __str__(self):
        return f"{self.date}: {self.bs_to_usd} Bs/USD"
    
    @classmethod
    def get_latest_rate(cls):
        """Obtiene la tasa de cambio más reciente"""
        try:
            return cls.objects.latest()
        except cls.DoesNotExist:
            return None


class Backup(models.Model):
    """Modelo para los respaldos de la base de datos"""
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    file_path = models.CharField(max_length=255, verbose_name="Ruta del Archivo")
    file_size = models.PositiveIntegerField(verbose_name="Tamaño (KB)")
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='backups',
        verbose_name="Creado por"
    )
    notes = models.TextField(blank=True, verbose_name="Notas")
    
    class Meta:
        verbose_name = "Respaldo"
        verbose_name_plural = "Respaldos"
        ordering = ['-date']
    
    def __str__(self):
        return f"Respaldo del {self.date}"