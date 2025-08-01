# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    """Admin personalizado para modelo de usuario"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('is_admin', 'is_employee', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Roles', {'fields': ('is_admin', 'is_employee')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Roles', {'fields': ('is_admin', 'is_employee')}),
    )

admin.site.register(User, CustomUserAdmin)