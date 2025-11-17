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