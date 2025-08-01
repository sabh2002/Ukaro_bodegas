# utils/admin.py

from django.contrib import admin
from .models import ExchangeRate, Backup

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('date', 'bs_to_usd', 'updated_by')
    date_hierarchy = 'date'
    list_filter = ('date',)
    search_fields = ('updated_by__username',)

@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ('date', 'file_path', 'file_size', 'created_by')
    list_filter = ('date', 'created_by')
    search_fields = ('notes',)
    readonly_fields = ('date',)