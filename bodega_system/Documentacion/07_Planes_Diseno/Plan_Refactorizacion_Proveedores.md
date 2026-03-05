# 🔧 PLAN DE REFACTORIZACIÓN - Módulo de Proveedores

**Fecha:** 2026-02-24
**Proyecto:** Sistema Ukaro Bodegas
**Módulo:** `suppliers/` (Proveedores y Órdenes de Compra)
**Estado:** 📋 PLANIFICADO - Listo para ejecutar

---

## 📊 RESUMEN EJECUTIVO

### Problemas Identificados: 14
- 🔴 Críticos: 2
- 🟠 Alta prioridad: 2
- 🟡 Media prioridad: 3
- 🔵 Baja prioridad: 7

### Tiempo Total Estimado: 12-17 horas
- Fase 1 (URGENTE): 1-2 horas ⚡
- Fase 2 (Corto plazo): 3-4 horas
- Fase 3 (Medio plazo): 6-8 horas
- Fase 4 (Largo plazo): 2-3 horas

### Archivos a Modificar: 4
- `suppliers/models.py`
- `suppliers/views.py`
- `suppliers/forms.py`
- `suppliers/tests.py` (nuevo/actualizar)

---

## 🎯 FASE 1: CRÍTICO (URGENTE)

**Duración:** 1-2 horas
**Prioridad:** 🔴 CRÍTICA - Hacer AHORA
**Objetivo:** Eliminar riesgos financieros inmediatos

### 1.1. Eliminar Fallback Peligroso de Tasa de Cambio

**Problema:** `suppliers/models.py:182` usa fallback de 7.0 Bs/USD

**Archivos a modificar:**
- `suppliers/models.py` (línea 174-183)

**Cambios:**
```python
# ANTES (suppliers/models.py:174-183)
def save(self, *args, **kwargs):
    """Calcular precio en Bs automáticamente antes de guardar"""
    if self.price_usd:
        from utils.models import ExchangeRate
        latest_rate = ExchangeRate.get_latest_rate()
        if latest_rate:
            self.price_bs = self.price_usd * latest_rate.bs_to_usd
        else:
            self.price_bs = self.price_usd * 7.0  # ⚠️ Fallback rate
    super().save(*args, **kwargs)

# DESPUÉS
def save(self, *args, **kwargs):
    """Calcular precio en Bs automáticamente antes de guardar"""
    if self.price_usd:
        from utils.models import ExchangeRate
        latest_rate = ExchangeRate.get_latest_rate()
        if not latest_rate:
            raise ValueError(
                "No hay tasa de cambio configurada. "
                "Configure una tasa en el sistema antes de crear órdenes de compra."
            )
        self.price_bs = self.price_usd * latest_rate.bs_to_usd
    super().save(*args, **kwargs)
```

**Tests a crear:**
```python
# suppliers/tests.py
def test_supplier_order_item_without_exchange_rate_raises_error():
    """Debe fallar si no hay tasa de cambio configurada"""
    ExchangeRate.objects.all().delete()

    item = SupplierOrderItem(
        order=order,
        product=product,
        quantity=10,
        price_usd=Decimal('5.00')
    )

    with pytest.raises(ValueError, match="No hay tasa de cambio"):
        item.save()
```

### 1.2. Agregar Métodos Dinámicos de Cálculo

**Problema:** No existen métodos para calcular precios/totales con tasa actual

**Archivos a modificar:**
- `suppliers/models.py` (agregar métodos)

**Cambios:**

```python
# suppliers/models.py - Agregar a SupplierOrderItem (después de línea 198)

def get_current_price_bs(self):
    """Calcula el precio actual en Bs con la tasa de cambio actual"""
    from utils.models import ExchangeRate

    latest_rate = ExchangeRate.get_latest_rate()
    if latest_rate:
        return self.price_usd * latest_rate.bs_to_usd
    return Decimal('0.00')

@property
def current_subtotal_bs(self):
    """Calcula el subtotal actual en Bs con la tasa de cambio actual"""
    return self.quantity * self.get_current_price_bs()


# suppliers/models.py - Agregar a SupplierOrder (después de línea 132)

def calculate_total_usd(self):
    """Calcula el total en USD sumando todos los items"""
    return sum(item.subtotal_usd for item in self.items.all())

def calculate_total_bs(self):
    """Calcula el total en Bs sumando todos los items (con precio histórico)"""
    return sum(item.subtotal_bs for item in self.items.all())

def get_current_total_bs(self):
    """Calcula el total actual en Bs con la tasa de cambio actual"""
    from utils.models import ExchangeRate

    latest_rate = ExchangeRate.get_latest_rate()
    if latest_rate:
        return self.calculate_total_usd() * latest_rate.bs_to_usd
    return Decimal('0.00')

def update_totals(self, save=True):
    """Recalcula y actualiza los totales de la orden"""
    from utils.models import ExchangeRate

    self.total_usd = self.calculate_total_usd()

    latest_rate = ExchangeRate.get_latest_rate()
    if not latest_rate:
        raise ValueError("No hay tasa de cambio configurada")

    self.total_bs = self.total_usd * latest_rate.bs_to_usd
    self.exchange_rate_used = latest_rate.bs_to_usd

    if save:
        self.save()

    return self

@property
def price_difference_bs(self):
    """Diferencia entre precio histórico y precio actual en Bs"""
    return self.get_current_total_bs() - self.total_bs

@property
def exchange_rate_changed(self):
    """Verifica si la tasa de cambio ha cambiado desde la creación de la orden"""
    from utils.models import ExchangeRate

    latest_rate = ExchangeRate.get_latest_rate()
    if not latest_rate:
        return False

    return abs(self.exchange_rate_used - latest_rate.bs_to_usd) > Decimal('0.01')
```

**Tests a crear:**
```python
# suppliers/tests.py
def test_supplier_order_item_get_current_price_bs():
    """Debe calcular precio en Bs con tasa actual"""
    # Crear tasa de 45.50
    rate = ExchangeRate.objects.create(bs_to_usd=Decimal('45.50'), ...)

    item = SupplierOrderItem.objects.create(
        price_usd=Decimal('10.00'),
        ...
    )

    assert item.get_current_price_bs() == Decimal('455.00')

    # Cambiar tasa
    ExchangeRate.objects.create(bs_to_usd=Decimal('50.00'), ...)

    # Precio histórico no cambia
    assert item.price_bs == Decimal('455.00')
    # Precio actual sí cambia
    assert item.get_current_price_bs() == Decimal('500.00')

def test_supplier_order_update_totals():
    """Debe actualizar totales correctamente"""
    order = SupplierOrder.objects.create(...)
    SupplierOrderItem.objects.create(
        order=order,
        quantity=5,
        price_usd=Decimal('10.00')
    )

    order.update_totals()

    assert order.total_usd == Decimal('50.00')
    assert order.total_bs == Decimal('2275.00')  # 50 * 45.50
```

### 1.3. Eliminar Logs de Debug en Producción

**Problema:** 40+ líneas de `print()` en código de producción

**Archivos a modificar:**
- `suppliers/views.py` (líneas 221-278, 298-351, etc.)
- `suppliers/forms.py` (líneas 191-230)

**Estrategia:**
1. Configurar logging estructurado
2. Reemplazar `print()` por `logger.info/debug/error()`
3. Eliminar prints innecesarios
4. Mantener solo logs importantes con nivel apropiado

**Cambios:**

```python
# suppliers/views.py - Agregar al inicio del archivo (después de imports)
import logging

logger = logging.getLogger(__name__)

# ANTES (líneas 221-278)
print("===== ORDER CREATE POST REQUEST =====")
print("POST data:", dict(request.POST))
print("Form valid:", form.is_valid())
print("Form errors:", form.errors)
# ... 40+ líneas más

# DESPUÉS
logger.debug("Processing order creation", extra={
    'form_valid': form.is_valid(),
    'supplier_id': request.POST.get('supplier'),
})

if not form.is_valid():
    logger.warning("Order form validation failed", extra={
        'errors': form.errors,
        'user_id': request.user.id,
    })

# ANTES (líneas 298-351)
print("💾 Saving main order...")
print(f"✅ Order saved with ID: {order.id}")
print("🆕 Creating new product...")
# ... 20+ líneas más

# DESPUÉS
logger.info("Order saved successfully", extra={
    'order_id': order.id,
    'total_usd': float(order.total_usd),
    'supplier_id': order.supplier_id,
})

if form_item.cleaned_data.get('is_new_product'):
    logger.info("Creating new product from order", extra={
        'order_id': order.id,
        'product_name': form_item.cleaned_data['new_product_name'],
    })
```

```python
# suppliers/forms.py - Agregar al inicio
import logging

logger = logging.getLogger(__name__)

# ANTES (líneas 191-230)
print(f"🔍 FORM VALIDATION DEBUG:")
print(f"  is_new_product: {is_new_product}")
print(f"  product: {product}")
# ... 15+ líneas más

# DESPUÉS
logger.debug("Validating order item form", extra={
    'is_new_product': is_new_product,
    'has_product': product is not None,
})

if is_new_product:
    logger.debug("Processing new product creation", extra={
        'barcode': cleaned_data.get('new_product_barcode'),
        'name': cleaned_data.get('new_product_name'),
    })
```

**Eliminar completamente:**
- Emojis en logs (🔍, ✅, ❌, 💾, etc.) → usar niveles de log
- Líneas separadoras (`=====`) → innecesarias con logging estructurado
- Debug de estructura de datos completas → usar logger.debug solo cuando sea necesario

**Configurar en settings.py:**
```python
# bodega_system/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/suppliers.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'suppliers': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

## 🛠️ FASE 2: CORTO PLAZO

**Duración:** 3-4 horas
**Prioridad:** 🟠 ALTA
**Objetivo:** Eliminar duplicación y mejorar validaciones

### 2.1. Centralizar Validación de Tasa de Cambio

**Problema:** Validación duplicada en 3 lugares

**Archivos a crear/modificar:**
- `utils/decorators.py` (agregar decorator)
- `suppliers/views.py` (usar decorator)

**Cambios:**

```python
# utils/decorators.py - Agregar nuevo decorator
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def require_exchange_rate(redirect_url='utils:exchange_rate_dashboard'):
    """
    Decorator para vistas que requieren tasa de cambio configurada

    Usage:
        @login_required
        @require_exchange_rate()
        def order_create(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from utils.models import ExchangeRate

            rate = ExchangeRate.get_latest_rate()
            if not rate:
                messages.error(
                    request,
                    'No se ha configurado una tasa de cambio. '
                    'Configure una tasa antes de realizar esta operación.'
                )
                return redirect(redirect_url)

            # Pasar la tasa como argumento para evitar llamarla de nuevo
            return view_func(request, *args, exchange_rate=rate, **kwargs)
        return wrapper
    return decorator
```

```python
# suppliers/views.py - Aplicar decorator

# ANTES
@login_required
def order_create(request):
    if request.method == 'POST':
        # ...
        # Obtener tasa de cambio actual
        from utils.models import ExchangeRate
        exchange_rate = ExchangeRate.get_latest_rate()

        if not exchange_rate:
            messages.error(request, 'No se ha configurado una tasa de cambio...')
            return redirect('suppliers:order_create')
        # ...

# DESPUÉS
@login_required
@require_exchange_rate()
def order_create(request, exchange_rate=None):  # ← exchange_rate inyectado por decorator
    if request.method == 'POST':
        # ...
        # exchange_rate ya está disponible
        # ...
```

**Aplicar decorator a:**
- `order_create` (línea 218)
- `order_update` (línea 389)

**Eliminar código duplicado:**
- Líneas 288-293 en `order_create`
- Líneas 403-409 en `order_update`

### 2.2. Unificar Lógica de Recepción de Órdenes

**Problema:** `order_receive()` y `_process_received_order()` hacen lo mismo

**Archivos a modificar:**
- `suppliers/views.py` (refactorizar funciones)

**Estrategia:**
1. Mantener `_process_received_order()` como función principal
2. Simplificar `order_receive()` para que delegue
3. Unificar parámetros (`update_prices`)

**Cambios:**

```python
# suppliers/views.py - Refactorizar _process_received_order

def _process_received_order(order, user, update_prices=True, notes=''):
    """
    Helper para procesar una orden recibida y actualizar inventario

    Args:
        order: SupplierOrder a procesar
        user: Usuario que recibe la orden
        update_prices: Si True, actualiza precios de compra de productos
        notes: Notas adicionales para los ajustes de inventario

    Returns:
        dict: Resumen de la operación con contadores y errores

    Raises:
        ValueError: Si la orden ya fue recibida o hay errores de validación
    """
    from decimal import Decimal
    from django.utils import timezone

    # Validar que la orden no esté recibida
    if order.status == 'received':
        raise ValueError(f"La orden #{order.id} ya fue recibida")

    # Marcar como recibida
    order.status = 'received'
    order.received_date = timezone.now()
    order.save()

    # Contadores para resumen
    summary = {
        'updated_products': [],
        'total_items_received': Decimal('0'),
        'errors': []
    }

    # Procesar cada ítem de la orden
    for item in order.items.all():
        try:
            product = item.product
            previous_stock = product.stock

            # Validar cantidad positiva
            quantity_to_add = Decimal(str(item.quantity))
            if quantity_to_add <= 0:
                logger.warning(
                    f"Cantidad no positiva en orden {order.id}, item {item.id}: {quantity_to_add}"
                )
                summary['errors'].append(f"Cantidad inválida para {product.name}")
                continue

            summary['total_items_received'] += quantity_to_add

            # Actualizar stock
            product.stock = previous_stock + quantity_to_add

            # Actualizar precios si se solicitó
            if update_prices:
                product.purchase_price_usd = item.price_usd
                product.purchase_price_bs = item.price_bs

            product.save()

            summary['updated_products'].append({
                'name': product.name,
                'quantity': quantity_to_add,
                'previous_stock': previous_stock,
                'new_stock': product.stock
            })

            # Registrar ajuste de inventario
            reason = f'Recepción orden #{order.id}'
            if notes:
                reason += f' - {notes}'

            InventoryAdjustment.objects.create(
                product=product,
                adjustment_type='add',
                quantity=quantity_to_add,
                previous_stock=previous_stock,
                new_stock=product.stock,
                reason=reason,
                adjusted_by=user
            )

            logger.info(
                f"Product updated from order reception",
                extra={
                    'order_id': order.id,
                    'product_id': product.id,
                    'quantity_added': float(quantity_to_add),
                    'new_stock': float(product.stock),
                }
            )

        except Exception as e:
            logger.error(
                f"Error processing item in order reception",
                exc_info=True,
                extra={
                    'order_id': order.id,
                    'item_id': item.id,
                    'product_id': product.id if product else None,
                }
            )
            summary['errors'].append(f"Error en {product.name}: {str(e)}")

    return summary


# suppliers/views.py - Simplificar order_receive

@login_required
def order_receive(request, pk):
    """Vista para recibir una orden de compra"""
    order = get_object_or_404(SupplierOrder, pk=pk)

    if order.status == 'received':
        messages.error(request, 'Esta orden ya ha sido recibida.')
        return redirect('suppliers:order_detail', pk=order.pk)

    if request.method == 'POST':
        form = ReceiveOrderForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Procesar orden usando la función unificada
                    summary = _process_received_order(
                        order=order,
                        user=request.user,
                        update_prices=form.cleaned_data.get('update_prices', True),
                        notes=form.cleaned_data.get('notes', '').strip()
                    )

                    # Mensaje de éxito
                    product_names = [p['name'] for p in summary['updated_products'][:3]]
                    products_summary = ', '.join(product_names)
                    if len(summary['updated_products']) > 3:
                        products_summary += f' y {len(summary["updated_products"]) - 3} más'

                    messages.success(
                        request,
                        f'Orden #{order.id} recibida exitosamente. '
                        f'Productos actualizados: {products_summary}. '
                        f'Total ítems: {summary["total_items_received"]}. '
                        f'Valor: ${order.total_usd} (Bs {order.total_bs})'
                    )

                    # Advertencias si hubo errores
                    if summary['errors']:
                        for error in summary['errors']:
                            messages.warning(request, error)

                    return redirect('suppliers:order_detail', pk=order.pk)

            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.error(
                    f"Error receiving order",
                    exc_info=True,
                    extra={'order_id': order.id, 'user_id': request.user.id}
                )
                messages.error(request, f'Error al recibir la orden: {str(e)}')
    else:
        form = ReceiveOrderForm()

    # Información para el template
    items = order.items.all().select_related('product')

    context = {
        'form': form,
        'order': order,
        'items': items,
        'title': f'Recibir Orden #{order.id}',
        'total_items_count': items.count(),
        'total_products_quantity': sum(item.quantity for item in items),
    }

    return render(request, 'suppliers/order_receive.html', context)
```

**Actualizar llamada en order_create:**

```python
# suppliers/views.py:336-341
# ANTES
if order.status == 'received':
    print("🔄 Order marked as received - updating inventory...")
    _process_received_order(order, request.user)
    messages.success(request, f'Orden de compra #{order.id} creada y recibida exitosamente...')

# DESPUÉS
if order.status == 'received':
    summary = _process_received_order(
        order=order,
        user=request.user,
        update_prices=True,
        notes='Auto-recepción al crear orden'
    )

    if summary['errors']:
        messages.warning(request, f"Orden recibida con advertencias: {'; '.join(summary['errors'])}")
    else:
        messages.success(
            request,
            f'Orden #{order.id} creada y recibida exitosamente. '
            f'Inventario actualizado: {len(summary["updated_products"])} productos.'
        )
```

### 2.3. Limpiar Imports Duplicados

**Problema:** Imports repetidos en líneas 3-12 y 17-24

**Archivos a modificar:**
- `suppliers/views.py`

**Cambios:**

```python
# suppliers/views.py - ANTES (líneas 1-25)
# suppliers/views.py

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Supplier, SupplierOrder, SupplierOrderItem
from .forms import SupplierOrderForm, SupplierOrderItemFormset, ReceiveOrderForm
from inventory.models import Product, InventoryAdjustment
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Supplier
from .forms import SupplierForm
from utils.decorators import admin_required

# DESPUÉS (organizado y sin duplicados)
# suppliers/views.py

# Python standard library
import logging
from decimal import Decimal

# Django core
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Django DB
from django.db import transaction
from django.db.models import Sum, Q
from django.core.paginator import Paginator

# Local imports
from .models import Supplier, SupplierOrder, SupplierOrderItem
from .forms import (
    SupplierForm,
    SupplierOrderForm,
    SupplierOrderItemFormset,
    ReceiveOrderForm
)
from inventory.models import Product, InventoryAdjustment, Category
from utils.decorators import admin_required, require_exchange_rate
from utils.models import ExchangeRate

# Logger
logger = logging.getLogger(__name__)
```

### 2.4. Agregar Validación de Stock Negativo

**Problema:** No se valida que la cantidad sea positiva al recibir

**Archivos a modificar:**
- `suppliers/forms.py` (ya tiene validación, mejorar)
- `suppliers/views.py` (agregar validación adicional)

**Cambios:**

```python
# suppliers/forms.py - Mejorar clean_quantity (líneas 137-161)

def clean_quantity(self):
    """Validar cantidad como decimal"""
    quantity = self.cleaned_data.get('quantity')

    if quantity is None:
        raise forms.ValidationError("La cantidad es requerida.")

    try:
        if isinstance(quantity, str):
            quantity = quantity.replace(',', '.')

        quantity_decimal = Decimal(str(quantity))

        if quantity_decimal <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")

        # ✅ AGREGAR: Validar máximo razonable
        if quantity_decimal > Decimal('100000'):
            raise forms.ValidationError(
                "La cantidad parece demasiado grande (máximo: 100,000). "
                "Verifique el valor ingresado."
            )

        # Validar máximo 2 decimales
        if quantity_decimal.as_tuple().exponent < -2:
            raise forms.ValidationError("La cantidad no puede tener más de 2 decimales.")

        return quantity_decimal

    except (InvalidOperation, ValueError):
        raise forms.ValidationError("La cantidad debe ser un número válido.")
```

La validación adicional en `_process_received_order()` ya está incluida en la sección 2.2.

---

## 🏗️ FASE 3: MEDIO PLAZO

**Duración:** 6-8 horas
**Prioridad:** 🟡 MEDIA
**Objetivo:** Implementar funcionalidades faltantes

### 3.1. Implementar Sistema de Pagos a Proveedores

**Problema:** Campo `paid` existe pero no tiene funcionalidad

**Archivos a crear/modificar:**
- `suppliers/models.py` (nuevo modelo `SupplierPayment`)
- `suppliers/views.py` (nuevas vistas)
- `suppliers/forms.py` (nuevo formulario)
- `suppliers/urls.py` (nuevas rutas)
- `templates/suppliers/` (nuevos templates)

**Paso 1: Crear modelo**

```python
# suppliers/models.py - Agregar nuevo modelo después de SupplierOrderItem

class SupplierPayment(models.Model):
    """Modelo para pagos a proveedores"""
    PAYMENT_METHODS = (
        ('cash_bs', 'Efectivo Bs'),
        ('cash_usd', 'Efectivo USD'),
        ('transfer_bs', 'Transferencia Bs'),
        ('transfer_usd', 'Transferencia USD'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    )

    order = models.ForeignKey(
        SupplierOrder,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Orden"
    )
    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Pago"
    )
    amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto (USD)"
    )
    amount_bs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Monto (Bs)"
    )
    exchange_rate_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1,
        verbose_name="Tasa Utilizada"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        verbose_name="Método de Pago"
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Referencia/Número"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    registered_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='supplier_payments',
        verbose_name="Registrado por"
    )

    class Meta:
        verbose_name = "Pago a Proveedor"
        verbose_name_plural = "Pagos a Proveedores"
        ordering = ['-payment_date']

    def __str__(self):
        return f"Pago ${self.amount_usd} - Orden #{self.order_id}"

    def save(self, *args, **kwargs):
        """Calcular monto en Bs si no está establecido"""
        if not self.amount_bs and self.amount_usd:
            from utils.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate:
                self.amount_bs = self.amount_usd * latest_rate.bs_to_usd
                self.exchange_rate_used = latest_rate.bs_to_usd

        super().save(*args, **kwargs)

        # Actualizar estado de pago de la orden
        self.order.update_payment_status()


# suppliers/models.py - Agregar propiedades a SupplierOrder

@property
def total_paid_usd(self):
    """Suma de pagos realizados en USD"""
    from django.db.models import Sum
    total = self.payments.aggregate(total=Sum('amount_usd'))['total']
    return total or Decimal('0.00')

@property
def total_paid_bs(self):
    """Suma de pagos realizados en Bs"""
    from django.db.models import Sum
    total = self.payments.aggregate(total=Sum('amount_bs'))['total']
    return total or Decimal('0.00')

@property
def pending_payment_usd(self):
    """Monto pendiente de pago en USD"""
    return self.total_usd - self.total_paid_usd

@property
def pending_payment_bs(self):
    """Monto pendiente de pago en Bs (histórico)"""
    return self.total_bs - self.total_paid_bs

@property
def is_fully_paid(self):
    """Verifica si la orden está completamente pagada"""
    return self.total_paid_usd >= self.total_usd

@property
def payment_percentage(self):
    """Porcentaje pagado de la orden"""
    if self.total_usd == 0:
        return Decimal('0.00')
    return (self.total_paid_usd / self.total_usd) * 100

def update_payment_status(self):
    """Actualiza el campo 'paid' basándose en los pagos registrados"""
    self.paid = self.is_fully_paid
    self.save(update_fields=['paid'])
```

**Paso 2: Migración**

```bash
python manage.py makemigrations suppliers
python manage.py migrate suppliers
```

**Paso 3: Crear formulario**

```python
# suppliers/forms.py - Agregar al final

class SupplierPaymentForm(forms.ModelForm):
    """Formulario para registrar pagos a proveedores"""

    class Meta:
        model = SupplierPayment
        fields = ['amount_usd', 'payment_method', 'reference', 'notes']
        widgets = {
            'amount_usd': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order

        if order:
            # Establecer máximo como el monto pendiente
            max_amount = order.pending_payment_usd
            self.fields['amount_usd'].widget.attrs['max'] = str(max_amount)
            self.fields['amount_usd'].help_text = f'Pendiente: ${max_amount}'

    def clean_amount_usd(self):
        amount = self.cleaned_data.get('amount_usd')

        if amount <= 0:
            raise forms.ValidationError("El monto debe ser mayor a cero.")

        if self.order and amount > self.order.pending_payment_usd:
            raise forms.ValidationError(
                f"El monto excede el pendiente de pago (${self.order.pending_payment_usd})."
            )

        return amount
```

**Paso 4: Crear vistas**

```python
# suppliers/views.py - Agregar nuevas vistas

@login_required
def payment_create(request, order_pk):
    """Vista para registrar un pago a proveedor"""
    order = get_object_or_404(SupplierOrder, pk=order_pk)

    if order.is_fully_paid:
        messages.info(request, 'Esta orden ya está completamente pagada.')
        return redirect('suppliers:order_detail', pk=order.pk)

    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST, order=order)

        if form.is_valid():
            payment = form.save(commit=False)
            payment.order = order
            payment.registered_by = request.user
            payment.save()

            messages.success(
                request,
                f'Pago de ${payment.amount_usd} registrado exitosamente. '
                f'Pendiente: ${order.pending_payment_usd}'
            )
            return redirect('suppliers:order_detail', pk=order.pk)
    else:
        form = SupplierPaymentForm(order=order)

    return render(request, 'suppliers/payment_form.html', {
        'form': form,
        'order': order,
        'title': f'Registrar Pago - Orden #{order.id}'
    })

@login_required
def payment_list(request):
    """Vista para listar todos los pagos"""
    payments = SupplierPayment.objects.select_related(
        'order', 'order__supplier', 'registered_by'
    ).order_by('-payment_date')

    # Filtros
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        payments = payments.filter(order__supplier_id=supplier_id)

    # Paginación
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Estadísticas
    from django.db.models import Sum
    stats = {
        'total_paid_usd': payments.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0,
        'total_paid_bs': payments.aggregate(Sum('amount_bs'))['amount_bs__sum'] or 0,
    }

    return render(request, 'suppliers/payment_list.html', {
        'page_obj': page_obj,
        'stats': stats,
    })

@admin_required
def payment_delete(request, pk):
    """Vista para eliminar un pago"""
    payment = get_object_or_404(SupplierPayment, pk=pk)
    order = payment.order

    if request.method == 'POST':
        payment.delete()
        order.update_payment_status()
        messages.success(request, 'Pago eliminado exitosamente.')
        return redirect('suppliers:order_detail', pk=order.pk)

    return render(request, 'suppliers/payment_confirm_delete.html', {
        'payment': payment
    })
```

**Paso 5: Agregar rutas**

```python
# suppliers/urls.py - Agregar rutas

urlpatterns = [
    # ... rutas existentes ...

    # Pagos
    path('orders/<int:order_pk>/payments/add/', views.payment_create, name='payment_create'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
]
```

**Templates necesarios:**
- `templates/suppliers/payment_form.html`
- `templates/suppliers/payment_list.html`
- `templates/suppliers/payment_confirm_delete.html`
- Actualizar `templates/suppliers/order_detail.html` para mostrar pagos

### 3.2. Refactorizar Creación de Productos

**Problema:** Función `_create_product_from_form()` muy compleja (47 líneas)

**Archivos a crear/modificar:**
- `inventory/services.py` (NUEVO - crear service layer)
- `suppliers/views.py` (simplificar función)

**Paso 1: Crear service layer**

```python
# inventory/services.py (NUEVO ARCHIVO)

"""
Capa de servicios para operaciones complejas con productos
"""

import logging
from decimal import Decimal
from django.db import transaction
from .models import Product, Category

logger = logging.getLogger(__name__)


class ProductService:
    """Servicio para operaciones complejas con productos"""

    @staticmethod
    def create_from_supplier_order(data, exchange_rate):
        """
        Crea un producto nuevo desde una orden de compra

        Args:
            data (dict): Datos del producto con las siguientes claves:
                - name (str): Nombre del producto
                - barcode (str): Código de barras
                - category (Category): Categoría del producto
                - unit_type (str, optional): Tipo de unidad (default: 'unit')
                - description (str, optional): Descripción
                - purchase_price_usd (Decimal): Precio de compra en USD
                - selling_price_usd (Decimal): Precio de venta en USD
                - min_stock (Decimal, optional): Stock mínimo (default: 5)
            exchange_rate (ExchangeRate): Tasa de cambio a usar

        Returns:
            Product: El producto creado

        Raises:
            ValueError: Si faltan campos requeridos o el código de barras existe
        """
        # Validar campos requeridos
        required_fields = ['name', 'barcode', 'category', 'purchase_price_usd', 'selling_price_usd']
        missing = [f for f in required_fields if not data.get(f)]

        if missing:
            raise ValueError(f"Campos requeridos faltantes: {', '.join(missing)}")

        # Validar que category sea una instancia de Category
        if not isinstance(data['category'], Category):
            raise ValueError("El campo 'category' debe ser una instancia de Category")

        # Validar código de barras único
        if Product.objects.filter(barcode=data['barcode']).exists():
            raise ValueError(f"Ya existe un producto con el código de barras {data['barcode']}")

        # Validar precios positivos
        if data['purchase_price_usd'] <= 0:
            raise ValueError("El precio de compra debe ser mayor a cero")

        if data['selling_price_usd'] <= 0:
            raise ValueError("El precio de venta debe ser mayor a cero")

        # Crear producto
        try:
            product = Product.objects.create(
                name=data['name'],
                barcode=data['barcode'],
                category=data['category'],
                unit_type=data.get('unit_type', 'unit'),
                description=data.get('description', ''),
                purchase_price_usd=data['purchase_price_usd'],
                selling_price_usd=data['selling_price_usd'],
                stock=0,  # Inicialmente en 0, se actualizará al recibir la orden
                min_stock=data.get('min_stock', Decimal('5')),
                is_active=True
            )

            logger.info(
                "Product created from supplier order",
                extra={
                    'product_id': product.id,
                    'name': product.name,
                    'barcode': product.barcode,
                    'category_id': product.category_id,
                }
            )

            return product

        except Exception as e:
            logger.error(
                "Failed to create product from supplier order",
                exc_info=True,
                extra={'data': data}
            )
            raise ValueError(f"Error al crear producto: {str(e)}")

    @staticmethod
    def update_purchase_price(product, price_usd, exchange_rate):
        """
        Actualiza el precio de compra de un producto

        Args:
            product (Product): Producto a actualizar
            price_usd (Decimal): Nuevo precio de compra en USD
            exchange_rate (ExchangeRate): Tasa de cambio a usar
        """
        product.purchase_price_usd = price_usd
        product.purchase_price_bs = price_usd * exchange_rate.bs_to_usd
        product.save(update_fields=['purchase_price_usd', 'purchase_price_bs'])

        logger.info(
            "Product purchase price updated",
            extra={
                'product_id': product.id,
                'new_price_usd': float(price_usd),
                'exchange_rate': float(exchange_rate.bs_to_usd),
            }
        )
```

**Paso 2: Simplificar función en views**

```python
# suppliers/views.py - Refactorizar _create_product_from_form

def _create_product_from_form(form, exchange_rate):
    """
    Helper para crear producto desde formulario de orden

    Args:
        form: SupplierOrderItemForm con datos validados
        exchange_rate: Tasa de cambio actual

    Returns:
        Product: El producto creado

    Raises:
        ValueError: Si hay errores en la creación
    """
    from inventory.services import ProductService

    data = {
        'name': form.cleaned_data['new_product_name'],
        'barcode': form.cleaned_data['new_product_barcode'],
        'category': form.cleaned_data['new_product_category'],
        'unit_type': form.cleaned_data.get('new_product_unit_type', 'unit'),
        'description': form.cleaned_data.get('new_product_description', ''),
        'purchase_price_usd': form.cleaned_data['price_usd'],
        'selling_price_usd': form.cleaned_data['new_product_selling_price_usd'],
        'min_stock': form.cleaned_data.get('new_product_min_stock', Decimal('5')),
    }

    return ProductService.create_from_supplier_order(data, exchange_rate)
```

### 3.3. Agregar Método `update_totals()` en Vistas

**Problema:** Cálculo de totales duplicado en `order_create` y `order_update`

**Archivos a modificar:**
- `suppliers/views.py`

**Cambios:**

```python
# suppliers/views.py - Simplificar order_create (líneas 319-331)

# ANTES
# Calcular totales
total_usd = 0
for form_item in formset.forms:
    if form_item.cleaned_data and not form_item.cleaned_data.get('DELETE', False):
        quantity = form_item.cleaned_data.get('quantity', 0)
        price_usd = form_item.cleaned_data.get('price_usd', 0)
        total_usd += quantity * price_usd

# Actualizar totales y tasa
order.total_usd = total_usd
order.total_bs = total_usd * exchange_rate.bs_to_usd
order.exchange_rate_used = exchange_rate.bs_to_usd
order.save()

# DESPUÉS
# Actualizar totales usando el método del modelo
order.update_totals()
```

Aplicar el mismo cambio en `order_update()` (líneas 427-439).

---

## 🔍 FASE 4: LARGO PLAZO

**Duración:** 2-3 horas
**Prioridad:** 🔵 BAJA
**Objetivo:** Mejoras de UX y pulido

### 4.1. Mejorar Formset de Items

**Problema:** Solo muestra 1 fila vacía para agregar productos

**Archivos a modificar:**
- `suppliers/forms.py`
- `templates/suppliers/order_form.html` (agregar JavaScript)

**Cambios:**

```python
# suppliers/forms.py - Línea 234-240

# ANTES
SupplierOrderItemFormset = inlineformset_factory(
    SupplierOrder,
    SupplierOrderItem,
    form=SupplierOrderItemForm,
    extra=1,  # ← Solo 1 fila
    can_delete=True
)

# DESPUÉS
SupplierOrderItemFormset = inlineformset_factory(
    SupplierOrder,
    SupplierOrderItem,
    form=SupplierOrderItemForm,
    extra=3,  # ← 3 filas iniciales
    can_delete=True,
    min_num=1,  # Al menos 1 item requerido
    validate_min=True,
)
```

**Agregar JavaScript para agregar filas dinámicamente:**

```javascript
// templates/suppliers/order_form.html - Agregar al final

<script>
// Función para agregar más filas de productos dinámicamente
function addOrderItemRow() {
    const formsetContainer = document.getElementById('order-items-formset');
    const totalForms = document.getElementById('id_items-TOTAL_FORMS');
    const formIndex = parseInt(totalForms.value);

    // Clonar la última fila y actualizar índices
    const lastRow = formsetContainer.querySelector('.order-item-row:last-child');
    const newRow = lastRow.cloneNode(true);

    // Limpiar valores
    newRow.querySelectorAll('input, select, textarea').forEach(input => {
        const name = input.getAttribute('name');
        if (name) {
            input.setAttribute('name', name.replace(/items-\d+/, `items-${formIndex}`));
            input.setAttribute('id', `id_${name.replace(/items-\d+/, `items-${formIndex}`)}`);

            if (input.type === 'checkbox') {
                input.checked = false;
            } else {
                input.value = '';
            }
        }
    });

    formsetContainer.appendChild(newRow);
    totalForms.value = formIndex + 1;
}

// Botón para agregar fila
document.getElementById('add-item-btn').addEventListener('click', addOrderItemRow);
</script>
```

### 4.2. Mejorar Método `__str__` de SupplierOrderItem

**Problema:** Falla si product es None

**Archivos a modificar:**
- `suppliers/models.py:171-172`

**Cambios:**

```python
# suppliers/models.py - SupplierOrderItem

# ANTES
def __str__(self):
    return f"{self.quantity} x {self.product.name}"

# DESPUÉS
def __str__(self):
    product_name = self.product.name if self.product else "[Producto eliminado]"
    order_id = self.order_id if self.order_id else "Nueva orden"
    return f"#{order_id}: {self.quantity} x {product_name}"
```

### 4.3. Deprecar Campo `selling_price_bs`

**Problema:** Se crea innecesariamente en productos nuevos

**Archivos a modificar:**
- `suppliers/views.py:675` (en `_create_product_from_form`)
- `inventory/services.py` (ya no lo establece en la refactorización)

**Cambios:**

Ya está solucionado en la refactorización de Fase 3.2. El `ProductService.create_from_supplier_order()` NO establece `selling_price_bs`, dejándolo en su valor default de 0.

**Nota:** Eliminar completamente el campo requiere una migración que afectaría todo el sistema. Esto se manejará en una refactorización futura más amplia.

### 4.4. Eliminar Código Obsoleto

**Problema:** `hasattr(product, 'purchase_price_usd')` innecesario

**Archivos a modificar:**
- Ya eliminado en la refactorización de Fase 2.2 (`_process_received_order`)

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Fase 1 (URGENTE) - 1-2 horas

- [ ] 1.1. Eliminar fallback de tasa 7.0
  - [ ] Modificar `SupplierOrderItem.save()`
  - [ ] Crear test de validación

- [ ] 1.2. Agregar métodos dinámicos
  - [ ] `SupplierOrderItem.get_current_price_bs()`
  - [ ] `SupplierOrderItem.current_subtotal_bs`
  - [ ] `SupplierOrder.calculate_total_usd()`
  - [ ] `SupplierOrder.get_current_total_bs()`
  - [ ] `SupplierOrder.update_totals()`
  - [ ] `SupplierOrder.price_difference_bs`
  - [ ] `SupplierOrder.exchange_rate_changed`
  - [ ] Crear tests

- [ ] 1.3. Eliminar logs de debug
  - [ ] Configurar logging en settings
  - [ ] Reemplazar prints en views.py
  - [ ] Reemplazar prints en forms.py
  - [ ] Eliminar emojis y decoraciones

### Fase 2 (Corto Plazo) - 3-4 horas

- [ ] 2.1. Centralizar validación de tasa
  - [ ] Crear decorator `@require_exchange_rate()`
  - [ ] Aplicar a `order_create`
  - [ ] Aplicar a `order_update`
  - [ ] Eliminar código duplicado

- [ ] 2.2. Unificar lógica de recepción
  - [ ] Refactorizar `_process_received_order()`
  - [ ] Simplificar `order_receive()`
  - [ ] Actualizar llamada en `order_create()`
  - [ ] Crear tests

- [ ] 2.3. Limpiar imports
  - [ ] Eliminar duplicados
  - [ ] Organizar por categorías

- [ ] 2.4. Validación de stock negativo
  - [ ] Mejorar `clean_quantity()` en forms
  - [ ] Validación ya incluida en 2.2

### Fase 3 (Medio Plazo) - 6-8 horas

- [ ] 3.1. Sistema de pagos a proveedores
  - [ ] Crear modelo `SupplierPayment`
  - [ ] Agregar propiedades a `SupplierOrder`
  - [ ] Crear migración
  - [ ] Crear formulario
  - [ ] Crear vistas
  - [ ] Agregar rutas
  - [ ] Crear templates
  - [ ] Crear tests

- [ ] 3.2. Refactorizar creación de productos
  - [ ] Crear `inventory/services.py`
  - [ ] Implementar `ProductService`
  - [ ] Simplificar `_create_product_from_form()`
  - [ ] Crear tests

- [ ] 3.3. Simplificar cálculo de totales
  - [ ] Usar `update_totals()` en `order_create`
  - [ ] Usar `update_totals()` en `order_update`

### Fase 4 (Largo Plazo) - 2-3 horas

- [ ] 4.1. Mejorar formset
  - [ ] Cambiar `extra=3`
  - [ ] Agregar `min_num=1`
  - [ ] Implementar JavaScript para agregar filas

- [ ] 4.2. Mejorar `__str__`
  - [ ] Manejar product None

- [ ] 4.3. Campo `selling_price_bs`
  - [ ] Ya solucionado en 3.2

- [ ] 4.4. Código obsoleto
  - [ ] Ya solucionado en 2.2

---

## 🧪 ESTRATEGIA DE TESTING

### Tests Mínimos Requeridos por Fase

**Fase 1:**
- Test de exception sin tasa de cambio
- Tests de métodos dinámicos (get_current_price_bs, update_totals)
- Total: ~5 tests

**Fase 2:**
- Tests de decorator require_exchange_rate
- Tests de _process_received_order unificado
- Tests de validación de cantidad
- Total: ~8 tests

**Fase 3:**
- Tests de modelo SupplierPayment
- Tests de propiedades de pago en SupplierOrder
- Tests de vistas de pago
- Tests de ProductService
- Total: ~15 tests

**Fase 4:**
- Tests de formset con validaciones
- Total: ~3 tests

**Total de tests nuevos:** ~31 tests

---

## 📝 NOTAS FINALES

### Dependencias entre Fases

- Fase 2 depende de Fase 1 (usa métodos dinámicos)
- Fase 3 es independiente (puede hacerse en paralelo)
- Fase 4 es independiente

### Riesgos

1. **Fase 1.1 (Tasa de cambio):** Puede romper órdenes en proceso si no hay tasa configurada
   - Mitigación: Verificar que existe tasa antes de desplegar

2. **Fase 3.1 (Pagos):** Requiere migración de DB
   - Mitigación: Hacer backup antes de migrar

### Siguientes Pasos Después de Esta Refactorización

1. Actualizar templates para mostrar precios históricos vs actuales
2. Crear reportes de cuentas por pagar
3. Dashboard de proveedores con estadísticas
4. Integración con sistema de tasas automáticas (del plan general)

---

**Última actualización:** 2026-02-24
**Estado:** 📋 LISTO PARA EJECUTAR
**Inicio:** FASE 1 - Inmediatamente después de aprobar este plan
