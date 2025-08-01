# sales/admin.py

from django.contrib import admin
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('subtotal',)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'customer', 'user', 'total_bs', 'is_credit', 'item_count')
    list_filter = ('date', 'is_credit', 'user')
    search_fields = ('id', 'customer__name', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('date',)
    inlines = [SaleItemInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('date', 'user', 'customer', 'is_credit')
        }),
        ('Detalles Financieros', {
            'fields': ('total_bs', 'notes')
        }),
    )

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'price_bs', 'subtotal')
    list_filter = ('sale__date',)
    search_fields = ('product__name', 'sale__id')