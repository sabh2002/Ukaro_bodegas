# inventory/admin.py

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Category, Product, InventoryAdjustment

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'barcode', 'category', 'purchase_price_bs', 
                    'selling_price_bs', 'stock', 'stock_status', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'barcode', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'barcode', 'category', 'description', 'image')
        }),
        ('Precios', {
            'fields': ('purchase_price_bs', 'selling_price_bs')
        }),
        ('Inventario', {
            'fields': ('stock', 'min_stock', 'is_active')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('product', 'adjustment_type', 'quantity', 
                    'previous_stock', 'new_stock', 'adjusted_by', 'adjusted_at')
    list_filter = ('adjustment_type', 'adjusted_by', 'adjusted_at')
    search_fields = ('product__name', 'reason')
    readonly_fields = ('adjusted_at',)