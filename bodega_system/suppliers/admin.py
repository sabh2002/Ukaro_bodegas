# suppliers/admin.py

from django.contrib import admin
from .models import Supplier, SupplierOrder, SupplierOrderItem, SupplierPayment

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'contact_person', 'phone', 'email', 'address')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'is_active')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class SupplierOrderItemInline(admin.TabularInline):
    model = SupplierOrderItem
    extra = 0
    readonly_fields = ('subtotal',)

@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'order_date', 'status', 'total_usd', 'payment_status_display', 'outstanding_balance_usd')
    list_filter = ('status', 'paid', 'order_date')
    search_fields = ('supplier__name', 'notes')
    date_hierarchy = 'order_date'
    readonly_fields = ('order_date', 'paid_amount_usd', 'paid_amount_bs', 'outstanding_balance_usd', 'payment_status_display')
    inlines = [SupplierOrderItemInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('supplier', 'order_date', 'status', 'received_date')
        }),
        ('Detalles Financieros', {
            'fields': ('total_usd', 'total_bs', 'exchange_rate_used')
        }),
        ('Estado de Pagos', {
            'fields': ('paid_amount_usd', 'paid_amount_bs', 'outstanding_balance_usd', 'payment_status_display', 'paid')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'created_by')
        }),
    )

@admin.register(SupplierOrderItem)
class SupplierOrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price_bs', 'subtotal')
    list_filter = ('order__supplier', 'order__order_date')
    search_fields = ('product__name', 'order__id')


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount_usd', 'payment_date', 'payment_method', 'created_by')
    list_filter = ('payment_method', 'payment_date', 'created_by')
    search_fields = ('order__id', 'order__supplier__name', 'reference', 'notes')
    date_hierarchy = 'payment_date'
    readonly_fields = ('created_at', 'amount_bs', 'exchange_rate_used')
    fieldsets = (
        ('Información del Pago', {
            'fields': ('order', 'amount_usd', 'amount_bs', 'exchange_rate_used', 'payment_date', 'payment_method', 'reference')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'created_by', 'created_at')
        }),
    )