"""
Filtros de template para formatear cantidades monetarias.

Uso:
    {% load formato_bs %}
    {{ valor|miles }}          → "1.250,75"  (punto miles, coma decimal)
    {{ valor|miles_usd }}      → "1.250,75"  (igual, útil para USD)
"""

from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def miles(value, decimals=2):
    """
    Formatea un número con punto como separador de miles y coma como decimal.
    Ejemplo: 1250.75 → "1.250,75"
    """
    try:
        value = Decimal(str(value))
        # Redondear a los decimales indicados
        value = round(value, int(decimals))
        # Formatear con 2 decimales fijos
        formatted = f"{value:,.{int(decimals)}f}"
        # Convertir formato anglosajón (1,250.75) → venezolano (1.250,75)
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    except (InvalidOperation, TypeError, ValueError):
        return value


@register.filter
def miles_usd(value):
    """
    Igual que miles pero siempre con 2 decimales. Para montos USD.
    Ejemplo: 1250.75 → "1.250,75"
    """
    return miles(value, 2)
