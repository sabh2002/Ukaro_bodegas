# finances/admin.py

from django.contrib import admin
from .models import Expense, DailyClose

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'description', 'amount_bs', 'date', 'created_by')
    list_filter = ('category', 'date')
    search_fields = ('description', 'receipt_number', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Información Básica', {
            'fields': ('category', 'description', 'amount_bs', 'date')
        }),
        ('Información Adicional', {
            'fields': ('receipt_number', 'notes', 'created_by')
        }),
        ('Metadatos', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(DailyClose)
class DailyCloseAdmin(admin.ModelAdmin):
    list_display = ('date', 'sales_count', 'sales_total_bs', 'expenses_total_bs', 'profit_bs', 'closed_by')
    list_filter = ('date', 'closed_by')
    search_fields = ('notes',)
    date_hierarchy = 'date'
    readonly_fields = ('closed_at',)
    fieldsets = (
        ('Información de Ventas', {
            'fields': ('date', 'sales_count', 'sales_total_bs')
        }),
        ('Información Financiera', {
            'fields': ('expenses_total_bs', 'profit_bs')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'closed_by', 'closed_at')
        }),
    )