# customers/admin.py

from django.contrib import admin
from .models import Customer, CustomerCredit, CreditPayment

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'credit_limit_bs', 'total_credit_used', 'available_credit', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at', 'total_credit_used', 'available_credit')
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'phone', 'email', 'address')
        }),
        ('Crédito', {
            'fields': ('credit_limit_bs', 'total_credit_used', 'available_credit')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'is_active')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class CreditPaymentInline(admin.TabularInline):
    model = CreditPayment
    extra = 0

@admin.register(CustomerCredit)
class CustomerCreditAdmin(admin.ModelAdmin):
    list_display = ('customer', 'sale', 'amount_bs', 'date_created', 'date_due', 'is_paid', 'date_paid')
    list_filter = ('is_paid', 'date_created', 'date_due')
    search_fields = ('customer__name', 'notes')
    readonly_fields = ('date_created',)
    inlines = [CreditPaymentInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('customer', 'sale', 'amount_bs', 'date_created', 'date_due')
        }),
        ('Estado', {
            'fields': ('is_paid', 'date_paid')
        }),
        ('Información Adicional', {
            'fields': ('notes',)
        }),
    )

@admin.register(CreditPayment)
class CreditPaymentAdmin(admin.ModelAdmin):
    list_display = ('credit', 'amount_bs', 'payment_date', 'received_by')
    list_filter = ('payment_date', 'received_by')
    search_fields = ('credit__customer__name', 'notes')
    readonly_fields = ('payment_date',)