# utils/decorators.py - DECORADORES DE PERMISOS CORREGIDO

from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

def is_admin(user):
    """Verifica si el usuario es administrador"""
    return user.is_authenticated and (user.is_admin or user.is_superuser)

def is_employee(user):
    """Verifica si el usuario es empleado"""
    return user.is_authenticated and user.is_employee

def is_admin_or_employee(user):
    """Verifica si el usuario es administrador o empleado"""
    return user.is_authenticated and (user.is_admin or user.is_superuser or user.is_employee)

def admin_required(view_func):
    """Decorador que requiere que el usuario sea administrador"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Solo los administradores pueden acceder a esta página.")
        return view_func(request, *args, **kwargs)
    return wrapper

def employee_or_admin_required(view_func):
    """Decorador que requiere que el usuario sea empleado o administrador"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin_or_employee(request.user):
            raise PermissionDenied("No tienes permisos para acceder a esta página.")
        return view_func(request, *args, **kwargs)
    return wrapper

def sales_access_required(view_func):
    """Decorador para acceso a ventas (empleados y administradores)"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin_or_employee(request.user):
            raise PermissionDenied("No tienes permisos para acceder al módulo de ventas.")
        return view_func(request, *args, **kwargs)
    return wrapper

def customer_access_required(view_func):
    """Decorador para acceso a clientes (empleados y administradores)"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin_or_employee(request.user):
            raise PermissionDenied("No tienes permisos para acceder al módulo de clientes.")
        return view_func(request, *args, **kwargs)
    return wrapper

def inventory_access_required(view_func):
    """Decorador para acceso de solo lectura al inventario (empleados y administradores)"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin_or_employee(request.user):
            raise PermissionDenied("No tienes permisos para acceder al módulo de inventario.")
        return view_func(request, *args, **kwargs)
    return wrapper

def require_exchange_rate(redirect_url='utils:exchange_rate_dashboard'):
    """
    Decorador para vistas que requieren tasa de cambio configurada

    Verifica que exista al menos una tasa de cambio en el sistema antes de
    ejecutar la vista. Si no existe, redirige al usuario con un mensaje de error.

    Args:
        redirect_url (str): URL a la que redirigir si no hay tasa (default: dashboard de tasas)

    Usage:
        @login_required
        @require_exchange_rate()
        def order_create(request, exchange_rate=None):
            # exchange_rate está disponible como parámetro
            ...

        # O con URL personalizada:
        @require_exchange_rate(redirect_url='suppliers:order_list')
        def order_create(request, exchange_rate=None):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.contrib import messages
            from utils.models import ExchangeRate

            rate = ExchangeRate.get_latest_rate()
            if not rate:
                messages.error(
                    request,
                    'No se ha configurado una tasa de cambio. '
                    'Configure una tasa antes de realizar esta operación.'
                )
                return redirect(redirect_url)

            # Inyectar la tasa como parámetro para evitar llamarla de nuevo en la vista
            kwargs['exchange_rate'] = rate
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator