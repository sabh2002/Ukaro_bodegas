# utils/templatetags/math_filters.py

from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def div(value, divisor):
    """
    Divide el valor por el divisor.
    Uso: {{ numero|div:divisor }}
    """
    try:
        # Convertir a Decimal para mayor precisión
        value = Decimal(str(value))
        divisor = Decimal(str(divisor))
        
        if divisor == 0:
            return 0
            
        result = value / divisor
        return float(result)
        
    except (ValueError, InvalidOperation, TypeError):
        return 0

@register.filter
def multiply(value, multiplier):
    """
    Multiplica el valor por el multiplicador.
    Uso: {{ numero|multiply:multiplicador }}
    """
    try:
        value = Decimal(str(value))
        multiplier = Decimal(str(multiplier))
        
        result = value * multiplier
        return float(result)
        
    except (ValueError, InvalidOperation, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """
    Calcula el porcentaje del valor respecto al total.
    Uso: {{ valor|percentage:total }}
    """
    try:
        value = Decimal(str(value))
        total = Decimal(str(total))
        
        if total == 0:
            return 0
            
        result = (value / total) * 100
        return float(result)
        
    except (ValueError, InvalidOperation, TypeError):
        return 0

@register.filter
def add_decimal(value, amount):
    """
    Suma un valor decimal al número.
    Uso: {{ numero|add_decimal:cantidad }}
    """
    try:
        value = Decimal(str(value))
        amount = Decimal(str(amount))
        
        result = value + amount
        return float(result)
        
    except (ValueError, InvalidOperation, TypeError):
        return 0

@register.filter
def subtract(value, amount):
    """
    Resta un valor del número.
    Uso: {{ numero|subtract:cantidad }}
    """
    try:
        value = Decimal(str(value))
        amount = Decimal(str(amount))
        
        result = value - amount
        return float(result)
        
    except (ValueError, InvalidOperation, TypeError):
        return 0