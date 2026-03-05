# ✅ FASE 3.2 COMPLETADA - Service Layer para Productos

**Fecha:** 2026-02-24
**Estado:** ✅ COMPLETADA
**Duración:** ~1 hora

---

## 📊 RESUMEN DE CAMBIOS

### Archivos Creados: 1
1. `inventory/services.py` (nuevo Service Layer completo)

### Archivos Modificados: 1
1. `suppliers/views.py` (refactorizado para usar servicio)

### Líneas de Código:
- **Agregadas:** ~380 líneas (service layer completo)
- **Eliminadas:** ~45 líneas (lógica movida a servicio)
- **Modificadas:** ~5 líneas (llamadas actualizadas)
- **Total neto:** +335 líneas (nueva capa de servicio)

---

## 🎯 FUNCIONALIDAD IMPLEMENTADA

### 1. Clase `ProductService`

**Archivo:** `inventory/services.py`

Service Layer completo para centralizar toda la lógica de negocio relacionada con productos.

#### **Beneficios del Service Layer:**
✅ **Separación de responsabilidades** - Lógica de negocio separada de vistas
✅ **Reutilización** - Mismo código en suppliers, sales, inventory
✅ **Testabilidad** - Fácil de testear sin HTTP requests
✅ **Consistencia** - Validaciones y cálculos uniformes
✅ **Mantenibilidad** - Un solo lugar para modificar lógica

---

### 2. Método: `validate_product_data()`

**Ubicación:** `inventory/services.py:20-100`

Valida datos de producto antes de crear/actualizar.

```python
@staticmethod
def validate_product_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida datos de producto antes de crear/actualizar

    Args:
        data: Diccionario con datos del producto

    Returns:
        Dict con datos validados

    Raises:
        ValueError: Si algún dato es inválido
    """
```

**Validaciones implementadas:**

1. **Campos requeridos:**
   - `name` - Nombre del producto
   - `barcode` - Código de barras
   - `category` - Categoría

2. **Barcode único:**
   - Verifica que no exista otro producto con el mismo código
   - Excluye el producto actual si se está editando

3. **Precios positivos:**
   - `purchase_price_usd` > 0
   - `selling_price_usd` > 0

4. **Advertencia de margen negativo:**
   - Si `selling_price < purchase_price`
   - No falla, solo registra warning en logs

5. **Stock válido:**
   - `stock >= 0`
   - `min_stock >= 0`

**Ejemplo de uso:**
```python
from inventory.services import ProductService

data = {
    'name': 'Arroz Diana 1kg',
    'barcode': '7702012345678',
    'category': category_obj,
    'purchase_price_usd': 2.50,
    'selling_price_usd': 3.00,
    'stock': 100,
    'min_stock': 10,
}

# Valida y retorna datos validados o lanza ValueError
validated_data = ProductService.validate_product_data(data)
```

---

### 3. Método: `calculate_price_bs()`

**Ubicación:** `inventory/services.py:102-125`

Calcula precio en Bs a partir de precio en USD.

```python
@staticmethod
def calculate_price_bs(price_usd: Decimal, exchange_rate=None) -> Decimal:
    """
    Calcula precio en Bs a partir de precio en USD

    Args:
        price_usd: Precio en USD
        exchange_rate: Objeto ExchangeRate o None para usar la tasa actual

    Returns:
        Precio en Bs

    Raises:
        ValueError: Si no hay tasa de cambio configurada
    """
```

**Características:**
- ✅ Usa tasa actual si no se especifica
- ✅ Lanza error si no hay tasa configurada
- ✅ Retorna Decimal (nunca float)
- ✅ Reutilizable en cualquier módulo

**Ejemplo:**
```python
from decimal import Decimal
from inventory.services import ProductService

price_usd = Decimal('2.50')
price_bs = ProductService.calculate_price_bs(price_usd)
# Retorna: Decimal('113.75') (si tasa es 45.50)
```

---

### 4. Método: `create_product()` ⭐

**Ubicación:** `inventory/services.py:127-209`

**Método principal** para crear productos con todas las validaciones y cálculos.

```python
@staticmethod
@transaction.atomic
def create_product(
    name: str,
    barcode: str,
    category,
    purchase_price_usd: Decimal,
    selling_price_usd: Decimal,
    unit_type: str = 'unit',
    description: str = '',
    stock: Decimal = Decimal('0'),
    min_stock: Decimal = Decimal('5'),
    is_active: bool = True,
    exchange_rate=None,
    created_by=None
):
    """
    Crea un nuevo producto con validaciones y cálculos automáticos

    Returns:
        Product: Instancia del producto creado

    Raises:
        ValueError: Si los datos son inválidos o no hay tasa de cambio
    """
```

**Proceso:**
1. ✅ Valida todos los datos con `validate_product_data()`
2. ✅ Calcula `purchase_price_bs` automáticamente
3. ✅ Calcula `selling_price_bs` automáticamente
4. ✅ Crea el producto en transacción atómica
5. ✅ Registra en logs con metadata
6. ✅ Retorna instancia del producto

**Ejemplo de uso:**
```python
from decimal import Decimal
from inventory.services import ProductService
from inventory.models import Category

category = Category.objects.get(name='Abarrotes')

product = ProductService.create_product(
    name='Arroz Diana 1kg',
    barcode='7702012345678',
    category=category,
    purchase_price_usd=Decimal('2.50'),
    selling_price_usd=Decimal('3.00'),
    unit_type='unit',
    description='Arroz blanco premium',
    stock=Decimal('100'),
    min_stock=Decimal('10'),
    created_by=request.user
)
```

---

### 5. Método: `create_product_from_order_form()`

**Ubicación:** `inventory/services.py:211-269`

Función de conveniencia específica para crear productos desde formularios de órdenes de compra.

```python
@staticmethod
@transaction.atomic
def create_product_from_order_form(form, exchange_rate, created_by=None):
    """
    Crea un producto desde un formulario de orden de compra

    Esta es una función de conveniencia que extrae los datos del formulario
    y llama a create_product().

    Args:
        form: Formulario con cleaned_data que contiene campos new_product_*
        exchange_rate: ExchangeRate a usar para conversión
        created_by: Usuario que crea el producto

    Returns:
        Product: Instancia del producto creado
    """
```

**Proceso:**
1. ✅ Extrae datos del formulario (campos `new_product_*`)
2. ✅ Valida que haya categoría
3. ✅ Llama a `create_product()` con los datos extraídos
4. ✅ Stock inicial en 0 (se actualiza al recibir orden)
5. ✅ Registra en logs con fuente 'supplier_order'

**Uso en suppliers/views.py:**
```python
from inventory.services import ProductService

# En order_create() o order_update()
if form_item.cleaned_data.get('is_new_product'):
    new_product = ProductService.create_product_from_order_form(
        form=form_item,
        exchange_rate=exchange_rate,
        created_by=request.user
    )
    form_item.instance.product = new_product
```

---

### 6. Método: `update_product_prices()`

**Ubicación:** `inventory/services.py:271-305`

Actualiza los precios en Bs de un producto usando una tasa de cambio.

```python
@staticmethod
@transaction.atomic
def update_product_prices(product, exchange_rate=None):
    """
    Actualiza los precios en Bs de un producto usando la tasa de cambio

    Args:
        product: Instancia de Product
        exchange_rate: ExchangeRate a usar (default: tasa actual)

    Returns:
        Product: Producto actualizado
    """
```

**Características:**
- ✅ Usa tasa actual si no se especifica
- ✅ Registra precios antiguos y nuevos en logs
- ✅ Guarda automáticamente el producto
- ✅ Retorna el producto actualizado

**Ejemplo:**
```python
from inventory.services import ProductService
from inventory.models import Product

product = Product.objects.get(barcode='7702012345678')

# Actualizar con tasa actual
ProductService.update_product_prices(product)

# Actualizar con tasa específica
from utils.models import ExchangeRate
rate = ExchangeRate.objects.get(date='2026-02-24')
ProductService.update_product_prices(product, exchange_rate=rate)
```

---

### 7. Método: `bulk_update_prices()`

**Ubicación:** `inventory/services.py:307-346`

Actualiza los precios en Bs de múltiples productos en batch.

```python
@staticmethod
def bulk_update_prices(queryset=None, exchange_rate=None):
    """
    Actualiza los precios en Bs de múltiples productos

    Args:
        queryset: QuerySet de productos (default: todos los productos activos)
        exchange_rate: ExchangeRate a usar (default: tasa actual)

    Returns:
        int: Cantidad de productos actualizados
    """
```

**Características:**
- ✅ Usa transacción atómica para consistencia
- ✅ Default: actualiza todos los productos activos
- ✅ Retorna cantidad de productos actualizados
- ✅ Logging de operación bulk

**Ejemplo de uso:**
```python
from inventory.services import ProductService
from inventory.models import Product

# Actualizar todos los productos activos
count = ProductService.bulk_update_prices()
print(f"Actualizados {count} productos")

# Actualizar solo productos de una categoría
from inventory.models import Category
category = Category.objects.get(name='Abarrotes')
products = Product.objects.filter(category=category, is_active=True)
count = ProductService.bulk_update_prices(queryset=products)
```

**Caso de uso práctico:**
```python
# Command para actualizar todos los precios cuando cambia la tasa
# management/commands/update_all_prices.py

from django.core.management.base import BaseCommand
from inventory.services import ProductService

class Command(BaseCommand):
    help = 'Actualiza precios en Bs de todos los productos'

    def handle(self, *args, **options):
        count = ProductService.bulk_update_prices()
        self.stdout.write(
            self.style.SUCCESS(f'✅ {count} productos actualizados')
        )
```

---

## 🔄 REFACTORIZACIÓN EN `suppliers/views.py`

### Función `_create_product_from_form()` Simplificada

**ANTES** (45 líneas):
```python
def _create_product_from_form(form, exchange_rate):
    """Helper para crear un producto nuevo desde el formulario"""
    from inventory.models import Product, Category

    try:
        selling_price_usd = form.cleaned_data['new_product_selling_price_usd']
        purchase_price_usd = form.cleaned_data['price_usd']
        category = form.cleaned_data['new_product_category']

        if not category:
            raise ValueError("Categoría es requerida")

        description = form.cleaned_data.get('new_product_description', '')

        product = Product.objects.create(
            name=form.cleaned_data['new_product_name'],
            barcode=form.cleaned_data['new_product_barcode'],
            category=category,
            unit_type=form.cleaned_data.get('new_product_unit_type', 'unit'),
            description=description,
            purchase_price_usd=purchase_price_usd,
            purchase_price_bs=purchase_price_usd * exchange_rate.bs_to_usd,
            selling_price_usd=selling_price_usd,
            selling_price_bs=selling_price_usd * exchange_rate.bs_to_usd,
            stock=0,
            min_stock=form.cleaned_data.get('new_product_min_stock', 5),
            is_active=True
        )

        logger.info("Product created from supplier order form", extra={
            'product_id': product.id,
            'product_name': product.name,
            'barcode': product.barcode,
            'category_id': category.id,
        })

        return product

    except Exception as e:
        logger.error("Failed to create product from form", exc_info=True, extra={
            'form_data': {k: str(v) for k, v in form.cleaned_data.items() if k.startswith('new_product')},
        })
        raise
```

**DESPUÉS** (10 líneas):
```python
def _create_product_from_form(form, exchange_rate, created_by=None):
    """
    Helper para crear un producto nuevo desde el formulario

    DEPRECATED: Esta función ahora delega al ProductService.
    Se mantiene por compatibilidad pero usa el service layer internamente.
    """
    from inventory.services import ProductService

    return ProductService.create_product_from_order_form(
        form=form,
        exchange_rate=exchange_rate,
        created_by=created_by
    )
```

**Mejoras:**
- ✅ **78% menos código** (45 → 10 líneas)
- ✅ **Delegación clara** al service layer
- ✅ **Validaciones centralizadas** reutilizables
- ✅ **Logging consistente** desde el servicio
- ✅ **Parámetro created_by** agregado

### Llamadas Actualizadas

**Ubicaciones:** `suppliers/views.py:273` y `suppliers/views.py:382`

**ANTES:**
```python
new_product = _create_product_from_form(form_item, exchange_rate)
```

**DESPUÉS:**
```python
new_product = _create_product_from_form(form_item, exchange_rate, request.user)
```

**Beneficio:**
- ✅ Ahora se registra **quién creó el producto**

---

## 🎯 BENEFICIOS DEL SERVICE LAYER

### 1. Reutilización de Código

**Antes:** Lógica duplicada en múltiples lugares
**Ahora:** Un solo lugar para crear productos

```python
# Desde suppliers (orden de compra)
from inventory.services import ProductService
product = ProductService.create_product_from_order_form(...)

# Desde inventory (creación manual)
from inventory.services import ProductService
product = ProductService.create_product(...)

# Desde sales (venta con producto nuevo - futuro)
from inventory.services import ProductService
product = ProductService.create_product(...)
```

### 2. Validaciones Consistentes

Todos los módulos usan las **mismas validaciones**:
- ✅ Barcode único
- ✅ Precios positivos
- ✅ Campos requeridos
- ✅ Stock no negativo

### 3. Testabilidad

**Service Layer es más fácil de testear:**

```python
# test_product_service.py
from inventory.services import ProductService
from decimal import Decimal

def test_create_product_with_valid_data():
    product = ProductService.create_product(
        name='Test Product',
        barcode='1234567890',
        category=category,
        purchase_price_usd=Decimal('10.00'),
        selling_price_usd=Decimal('15.00')
    )
    assert product.id is not None
    assert product.purchase_price_bs > 0

def test_create_product_without_exchange_rate_raises_error():
    ExchangeRate.objects.all().delete()  # Sin tasa

    with pytest.raises(ValueError, match="No hay tasa de cambio"):
        ProductService.create_product(...)

def test_validate_product_data_rejects_duplicate_barcode():
    with pytest.raises(ValueError, match="Ya existe un producto"):
        ProductService.validate_product_data({
            'barcode': existing_product.barcode,
            ...
        })
```

### 4. Mantenibilidad

**Un solo lugar para cambiar lógica:**

Si necesitas agregar validación:
```python
# inventory/services.py
def validate_product_data(data):
    # ... validaciones existentes ...

    # ✅ NUEVO: Validar precio de venta mínimo
    if data.get('selling_price_usd'):
        if data['selling_price_usd'] < Decimal('0.10'):
            errors.append("Precio de venta debe ser >= $0.10 USD")
```

**Cambio se aplica automáticamente en:**
- Suppliers (órdenes de compra)
- Inventory (creación manual)
- Sales (futuro)
- API (futuro)

### 5. Separación de Responsabilidades

**Arquitectura en capas:**

```
┌─────────────────────────────────────┐
│         VIEWS (HTTP Layer)          │  ← suppliers/views.py
│  - Maneja requests/responses        │
│  - Validación de forms              │
│  - Permisos y autenticación         │
└─────────────────┬───────────────────┘
                  │
                  ↓
┌─────────────────────────────────────┐
│      SERVICES (Business Logic)      │  ← inventory/services.py
│  - Validaciones de negocio          │  ✅ NUEVA CAPA
│  - Cálculos y transformaciones      │
│  - Operaciones complejas            │
└─────────────────┬───────────────────┘
                  │
                  ↓
┌─────────────────────────────────────┐
│       MODELS (Data Layer)           │  ← inventory/models.py
│  - Definición de esquema            │
│  - Propiedades calculadas           │
│  - Relaciones                       │
└─────────────────────────────────────┘
```

---

## 📋 CASOS DE USO

### Caso 1: Crear Producto desde Orden de Compra

```python
# suppliers/views.py - order_create()
from inventory.services import ProductService

if form_item.cleaned_data.get('is_new_product'):
    new_product = ProductService.create_product_from_order_form(
        form=form_item,
        exchange_rate=exchange_rate,
        created_by=request.user
    )
    form_item.instance.product = new_product
```

### Caso 2: Crear Producto Manualmente (inventory)

```python
# inventory/views.py - product_create()
from inventory.services import ProductService
from decimal import Decimal

try:
    product = ProductService.create_product(
        name=form.cleaned_data['name'],
        barcode=form.cleaned_data['barcode'],
        category=form.cleaned_data['category'],
        purchase_price_usd=form.cleaned_data['purchase_price_usd'],
        selling_price_usd=form.cleaned_data['selling_price_usd'],
        unit_type=form.cleaned_data['unit_type'],
        description=form.cleaned_data.get('description', ''),
        stock=form.cleaned_data.get('stock', Decimal('0')),
        min_stock=form.cleaned_data.get('min_stock', Decimal('5')),
        created_by=request.user
    )
    messages.success(request, f"Producto '{product.name}' creado exitosamente")
except ValueError as e:
    messages.error(request, str(e))
```

### Caso 3: Actualizar Todos los Precios (Command)

```python
# management/commands/update_prices.py
from django.core.management.base import BaseCommand
from inventory.services import ProductService

class Command(BaseCommand):
    def handle(self, *args, **options):
        count = ProductService.bulk_update_prices()
        self.stdout.write(
            self.style.SUCCESS(f'✅ Actualizados {count} productos')
        )
```

### Caso 4: API para Crear Producto (Futuro)

```python
# api/views.py
from rest_framework.decorators import api_view
from inventory.services import ProductService
from decimal import Decimal

@api_view(['POST'])
def create_product_api(request):
    try:
        product = ProductService.create_product(
            name=request.data['name'],
            barcode=request.data['barcode'],
            category=Category.objects.get(id=request.data['category_id']),
            purchase_price_usd=Decimal(request.data['purchase_price_usd']),
            selling_price_usd=Decimal(request.data['selling_price_usd']),
            created_by=request.user
        )
        return Response({'id': product.id, 'name': product.name}, status=201)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
```

---

## 🧪 TESTS PENDIENTES

**Archivo a crear:** `inventory/tests/test_product_service.py`

**Tests a implementar:**

### Validación
1. `test_validate_product_data_with_valid_data()`
2. `test_validate_product_data_missing_required_fields()`
3. `test_validate_product_data_duplicate_barcode()`
4. `test_validate_product_data_negative_prices()`
5. `test_validate_product_data_negative_stock()`
6. `test_validate_product_data_warns_on_negative_margin()`

### Creación
7. `test_create_product_with_all_fields()`
8. `test_create_product_with_defaults()`
9. `test_create_product_without_exchange_rate_raises_error()`
10. `test_create_product_calculates_bs_prices()`
11. `test_create_product_logs_creation()`

### Actualización
12. `test_update_product_prices_with_current_rate()`
13. `test_update_product_prices_with_specific_rate()`
14. `test_update_product_prices_logs_changes()`
15. `test_bulk_update_prices_updates_all_active()`
16. `test_bulk_update_prices_with_custom_queryset()`
17. `test_bulk_update_prices_returns_count()`

### Formularios
18. `test_create_product_from_order_form_with_valid_data()`
19. `test_create_product_from_order_form_without_category_raises_error()`
20. `test_create_product_from_order_form_sets_stock_to_zero()`

---

## 📋 PRÓXIMOS PASOS

### Inmediato (Opcional):
1. **Crear tests** para `ProductService` (archivo de tests arriba)
2. **Refactorizar `inventory/views.py`** para usar el servicio
3. **Documentar API** del service layer

### FASE 3.3: Optimizaciones de Base de Datos (1-2 horas):
1. Agregar índices para consultas frecuentes:
   - `Product.barcode` (único, ya existe pero verificar)
   - `Product.category` + `is_active`
   - `SupplierOrder.supplier` + `status`
   - `Sale.customer` + `created_at`

2. Optimizar queries con `select_related()`:
   - En `order_detail`: cargar supplier, items, products
   - En `sale_detail`: cargar customer, items, products
   - En listas con paginación

3. Implementar caché para tasas de cambio:
   - Cachear `ExchangeRate.get_latest_rate()` por 1 hora
   - Invalidar al crear nueva tasa

---

## ✅ ESTADO FINAL

**FASE 3.2: COMPLETADA ✅**

- [x] Crear `inventory/services.py` con `ProductService`
- [x] Implementar `validate_product_data()`
- [x] Implementar `create_product()`
- [x] Implementar `create_product_from_order_form()`
- [x] Implementar `update_product_prices()`
- [x] Implementar `bulk_update_prices()`
- [x] Refactorizar `suppliers/views.py` para usar servicio
- [x] Agregar parámetro `created_by` a llamadas

**Archivos listos para commit:**
- `inventory/services.py`
- `suppliers/views.py`

**Comando Git:**
```bash
git add inventory/services.py suppliers/views.py
git commit -m "Feature: Service Layer para productos

NUEVO: inventory/services.py con ProductService
- Métodos: create_product(), validate_product_data()
- Métodos: update_product_prices(), bulk_update_prices()
- create_product_from_order_form() para órdenes

REFACTORIZACIÓN:
- suppliers/views.py usa ProductService
- _create_product_from_form() simplificada (45 → 10 líneas)
- Validaciones centralizadas y reutilizables

BENEFICIOS:
- Separación de responsabilidades (Service Layer)
- Lógica de negocio reutilizable
- Más fácil de testear
- Consistencia en todo el sistema

+335 líneas | Service Layer completo"
```

---

**Completada:** 2026-02-24
**Duración:** ~1 hora
**Líneas agregadas:** +335 líneas
**Próxima tarea:** FASE 3.3 - Optimizaciones de Base de Datos
