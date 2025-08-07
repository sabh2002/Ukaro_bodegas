# inventory/admin.py - Admin actualizado

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Category, Product, InventoryAdjustment, ProductCombo, ComboItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'barcode', 'category', 'unit_type', 'purchase_price_bs', 
                    'selling_price_bs', 'stock', 'stock_status', 'is_active')
    list_filter = ('category', 'unit_type', 'is_active', 'is_bulk_pricing')
    search_fields = ('name', 'barcode', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'barcode', 'category', 'description', 'image', 'unit_type')
        }),
        ('Precios', {
            'fields': ('purchase_price_bs', 'selling_price_bs')
        }),
        ('Inventario', {
            'fields': ('stock', 'min_stock', 'is_active')
        }),
        ('Precios al Mayor', {
            'fields': ('is_bulk_pricing', 'bulk_min_quantity', 'bulk_price_bs'),
            'classes': ('collapse',)
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

# NUEVOS ADMIN PARA COMBOS

class ComboItemInline(admin.TabularInline):
    model = ComboItem
    extra = 1
    autocomplete_fields = ['product']

@admin.register(ProductCombo)
class ProductComboAdmin(admin.ModelAdmin):
    list_display = ('name', 'combo_price_bs', 'total_individual_price', 
                    'savings_amount', 'savings_percentage', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'total_individual_price', 'savings_amount', 'savings_percentage')
    inlines = [ComboItemInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'combo_price_bs', 'is_active')
        }),
        ('Análisis Financiero', {
            'fields': ('total_individual_price', 'savings_amount', 'savings_percentage'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ComboItem)
class ComboItemAdmin(admin.ModelAdmin):
    list_display = ('combo', 'product', 'quantity', 'product_unit_type')
    list_filter = ('combo', 'product__category', 'product__unit_type')
    search_fields = ('combo__name', 'product__name')
    autocomplete_fields = ['combo', 'product']
    
    def product_unit_type(self, obj):
        return obj.product.get_unit_type_display()
    product_unit_type.short_description = 'Unidad'