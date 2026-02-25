# Ejemplos de Tests - Búsqueda de Productos

Este documento muestra ejemplos concretos de los tests más importantes para entender cómo funcionan.

---

## 📋 Tabla de Contenidos
1. [Tests de API de Búsqueda](#tests-de-api-de-búsqueda)
2. [Tests del Formulario](#tests-del-formulario)
3. [Tests de Integración](#tests-de-integración)
4. [Tests de Casos Extremos](#tests-de-casos-extremos)

---

## Tests de API de Búsqueda

### Ejemplo 1: Búsqueda por Nombre de Producto

**Archivo**: `inventory/tests.py`
**Línea**: ~418

```python
@pytest.mark.api
@pytest.mark.critical
def test_search_by_product_name(self, authenticated_client, category):
    """Debe encontrar productos por nombre exacto"""
    # ARRANGE: Crear productos de prueba
    product1 = ProductFactory(
        name='Coca Cola 2L',
        category=category,
        is_active=True
    )
    product2 = ProductFactory(
        name='Pepsi 2L',
        category=category,
        is_active=True
    )
    product3 = ProductFactory(
        name='Coca Cola Light',
        category=category,
        is_active=True
    )

    # ACT: Buscar "Coca"
    response = authenticated_client.get('/api/products/search/?q=Coca')

    # ASSERT: Verificar resultados
    assert response.status_code == 200
    data = response.json()

    assert 'products' in data
    assert len(data['products']) == 2  # Solo Coca Cola 2L y Coca Cola Light

    product_names = [p['name'] for p in data['products']]
    assert 'Coca Cola 2L' in product_names
    assert 'Coca Cola Light' in product_names
    assert 'Pepsi 2L' not in product_names
```

**Qué valida:**
- ✅ La API busca correctamente por nombre
- ✅ Retorna solo productos que coinciden con el query
- ✅ La búsqueda es parcial (encuentra "Coca Cola" buscando "Coca")
- ✅ Excluye productos que no coinciden

---

### Ejemplo 2: Búsqueda por Código de Barras

**Archivo**: `inventory/tests.py`
**Línea**: ~447

```python
@pytest.mark.api
@pytest.mark.critical
def test_search_by_barcode(self, authenticated_client, category):
    """Debe encontrar productos por código de barras"""
    # ARRANGE: Crear producto con código de barras específico
    product = ProductFactory(
        name='Test Product',
        barcode='7501234567890',
        category=category,
        is_active=True
    )

    # ACT: Buscar por código completo
    response = authenticated_client.get('/api/products/search/?q=7501234567890')

    # ASSERT: Verificar que encontró el producto correcto
    assert response.status_code == 200
    data = response.json()

    assert len(data['products']) == 1
    assert data['products'][0]['barcode'] == '7501234567890'
    assert data['products'][0]['name'] == 'Test Product'
```

**Qué valida:**
- ✅ Búsqueda por código de barras funciona
- ✅ Encuentra el producto exacto
- ✅ Esencial para escáneres de código de barras

---

### Ejemplo 3: Solo Productos Activos

**Archivo**: `inventory/tests.py`
**Línea**: ~517

```python
@pytest.mark.api
@pytest.mark.critical
def test_search_returns_only_active_products(self, authenticated_client, category):
    """Debe retornar solo productos activos por defecto"""
    # ARRANGE: Crear un producto activo y uno inactivo
    active_product = ProductFactory(
        name='Producto Activo',
        category=category,
        is_active=True
    )
    inactive_product = ProductFactory(
        name='Producto Inactivo',
        category=category,
        is_active=False
    )

    # ACT: Buscar "Producto" (sin especificar active=false)
    response = authenticated_client.get('/api/products/search/?q=Producto')

    # ASSERT: Solo debe retornar el activo
    assert response.status_code == 200
    data = response.json()

    assert len(data['products']) == 1
    assert data['products'][0]['name'] == 'Producto Activo'
    assert data['products'][0]['is_active'] is True
```

**Qué valida:**
- ✅ Por defecto solo muestra productos activos
- ✅ No confunde a los usuarios con productos descontinuados
- ✅ Comportamiento predecible

---

### Ejemplo 4: Límite de Resultados

**Archivo**: `inventory/tests.py`
**Línea**: ~555

```python
@pytest.mark.api
@pytest.mark.critical
def test_search_limits_results_to_default_10(self, authenticated_client, category):
    """Debe limitar los resultados a 10 por defecto"""
    # ARRANGE: Crear 15 productos
    for i in range(15):
        ProductFactory(
            name=f'Test Product {i}',
            category=category,
            is_active=True
        )

    # ACT: Buscar sin especificar límite
    response = authenticated_client.get('/api/products/search/?q=Test Product')

    # ASSERT: Debe retornar máximo 10
    assert response.status_code == 200
    data = response.json()

    assert len(data['products']) == 10
    assert data['count'] == 10
```

**Qué valida:**
- ✅ Límite por defecto de 10 resultados
- ✅ Previene saturar el dropdown del frontend
- ✅ Mejora el rendimiento

---

### Ejemplo 5: Información de Stock Completa

**Archivo**: `inventory/tests.py`
**Línea**: ~617

```python
@pytest.mark.api
@pytest.mark.critical
def test_search_returns_stock_information(self, authenticated_client, category):
    """Debe retornar información de stock correcta"""
    # ARRANGE: Crear productos con diferentes niveles de stock
    product_out = ProductFactory(
        name='Sin Stock',
        category=category,
        stock=Decimal('0'),
        min_stock=Decimal('10'),
        is_active=True
    )
    product_low = ProductFactory(
        name='Stock Bajo',
        category=category,
        stock=Decimal('5'),
        min_stock=Decimal('10'),
        is_active=True
    )
    product_normal = ProductFactory(
        name='Stock Normal',
        category=category,
        stock=Decimal('50'),
        min_stock=Decimal('10'),
        is_active=True
    )

    # ACT: Buscar todos los productos
    response = authenticated_client.get('/api/products/search/?q=Stock')

    # ASSERT: Verificar información de stock para cada uno
    assert response.status_code == 200
    data = response.json()

    products_by_name = {p['name']: p for p in data['products']}

    # Sin stock
    assert products_by_name['Sin Stock']['stock_status'] == 'out'
    assert products_by_name['Sin Stock']['stock_color'] == 'red'

    # Stock bajo
    assert products_by_name['Stock Bajo']['stock_status'] == 'low'
    assert products_by_name['Stock Bajo']['stock_color'] == 'yellow'

    # Stock normal
    assert products_by_name['Stock Normal']['stock_status'] == 'normal'
    assert products_by_name['Stock Normal']['stock_color'] == 'green'
```

**Qué valida:**
- ✅ Información de stock precisa para cada producto
- ✅ Estados: 'out', 'low', 'normal'
- ✅ Colores visuales: 'red', 'yellow', 'green'
- ✅ Esencial para alertar al vendedor sobre stock bajo

---

## Tests del Formulario

### Ejemplo 6: Input de Búsqueda Presente

**Archivo**: `sales/tests.py`
**Línea**: ~459

```python
@pytest.mark.views
@pytest.mark.critical
def test_sale_form_has_product_search_input(self, authenticated_client):
    """El formulario debe tener el input de búsqueda de productos"""
    # ACT: Cargar el formulario de venta
    response = authenticated_client.get('/sales/new/')

    # ASSERT: Verificar que tiene el input de búsqueda
    assert response.status_code == 200
    content = response.content.decode('utf-8')

    # Verificar que existe el input de búsqueda
    assert 'id="product_search"' in content
    assert 'Buscar Producto' in content
```

**Qué valida:**
- ✅ El input de búsqueda está presente en el HTML
- ✅ El formulario carga correctamente
- ✅ La funcionalidad está disponible para el usuario

---

### Ejemplo 7: Alpine.js Configurado

**Archivo**: `sales/tests.py`
**Línea**: ~505

```python
@pytest.mark.views
def test_sale_form_includes_alpine_js(self, authenticated_client):
    """El formulario debe incluir Alpine.js para funcionalidad interactiva"""
    # ACT: Cargar formulario
    response = authenticated_client.get('/sales/new/')

    # ASSERT: Verificar Alpine.js
    assert response.status_code == 200
    content = response.content.decode('utf-8')

    # Verificar que usa Alpine.js
    assert 'x-data' in content
    assert 'salesApp' in content
```

**Qué valida:**
- ✅ Alpine.js está configurado
- ✅ El componente `salesApp` está inicializado
- ✅ La interactividad del formulario funciona

---

## Tests de Integración

### Ejemplo 8: Búsqueda Funcional desde el Formulario

**Archivo**: `sales/tests.py`
**Línea**: ~548

```python
@pytest.mark.integration
@pytest.mark.critical
def test_can_search_products_from_form(self, authenticated_client, category):
    """Debe poder buscar productos desde el formulario"""
    # ARRANGE: Crear producto
    product1 = ProductFactory(
        name='Coca Cola 2L',
        barcode='7501234567890',
        category=category,
        selling_price_usd=Decimal('2.50'),
        stock=Decimal('100'),
        is_active=True
    )

    # ACT: Simular búsqueda desde el formulario
    response = authenticated_client.get('/api/products/search/?q=Coca')

    # ASSERT: Verificar que la búsqueda funciona
    assert response.status_code == 200
    data = response.json()

    assert len(data['products']) == 1
    assert data['products'][0]['name'] == 'Coca Cola 2L'
    assert data['products'][0]['barcode'] == '7501234567890'
```

**Qué valida:**
- ✅ Integración formulario ↔ API funciona
- ✅ Los datos son correctos
- ✅ El flujo completo de búsqueda está operativo

---

### Ejemplo 9: Agregar al Carrito Reduce Stock

**Archivo**: `sales/tests.py`
**Línea**: ~687

```python
@pytest.mark.integration
def test_add_product_reduces_stock(self, authenticated_client, product, customer, exchange_rate):
    """Agregar producto a venta debe reducir el stock"""
    # ARRANGE: Guardar stock inicial
    initial_stock = product.stock

    # Preparar datos de venta
    sale_data = {
        'items': [
            {
                'product_id': product.id,
                'quantity': 5,
                'price_bs': float(product.selling_price_bs)
            }
        ],
        'customer_id': customer.id,
        'is_credit': False,
        'payment_method': 'cash',
        'total_bs': float(product.selling_price_bs) * 5
    }

    # ACT: Crear la venta
    response = authenticated_client.post(
        '/sales/api/create/',
        data=sale_data,
        content_type='application/json'
    )

    # ASSERT: Verificar que se creó y redujo el stock
    assert response.status_code == 200

    product.refresh_from_db()
    assert product.stock == initial_stock - Decimal('5')
```

**Qué valida:**
- ✅ Crear una venta reduce el stock automáticamente
- ✅ La cantidad descontada es exacta
- ✅ Lógica de negocio funciona correctamente

---

### Ejemplo 10: Validación de Stock Insuficiente

**Archivo**: `sales/tests.py`
**Línea**: ~715

```python
@pytest.mark.integration
@pytest.mark.critical
def test_cannot_add_more_than_available_stock(self, authenticated_client, customer, exchange_rate):
    """No debe poder agregar más productos que el stock disponible"""
    # ARRANGE: Crear producto con stock limitado
    from factories import ProductFactory
    product = ProductFactory(stock=Decimal('10'))

    # Preparar venta con cantidad mayor al stock
    sale_data = {
        'items': [
            {
                'product_id': product.id,
                'quantity': 15,  # ⚠️ Más que el stock disponible
                'price_bs': float(product.selling_price_bs)
            }
        ],
        'customer_id': customer.id,
        'is_credit': False,
        'payment_method': 'cash',
        'total_bs': float(product.selling_price_bs) * 15
    }

    # ACT: Intentar crear la venta
    response = authenticated_client.post(
        '/sales/api/create/',
        data=sale_data,
        content_type='application/json'
    )

    # ASSERT: Debe rechazar la venta
    assert response.status_code in [400, 422]
```

**Qué valida:**
- ✅ No se pueden vender más productos del stock disponible
- ✅ Validación de negocio crítica funciona
- ✅ Previene errores de inventario

---

## Tests de Casos Extremos

### Ejemplo 11: Venta a Crédito Requiere Cliente

**Archivo**: `sales/tests.py`
**Línea**: ~828

```python
@pytest.mark.integration
@pytest.mark.critical
def test_credit_sale_requires_customer(self, authenticated_client, product, exchange_rate):
    """Venta a crédito debe requerir un cliente"""
    # ARRANGE: Preparar venta a crédito SIN cliente
    sale_data = {
        'items': [
            {
                'product_id': product.id,
                'quantity': 2,
                'price_bs': float(product.selling_price_bs)
            }
        ],
        'customer_id': None,  # ⚠️ Sin cliente
        'is_credit': True,    # ⚠️ Pero es a crédito
        'payment_method': 'cash',
        'total_bs': float(product.selling_price_bs) * 2
    }

    # ACT: Intentar crear venta
    response = authenticated_client.post(
        '/sales/api/create/',
        data=sale_data,
        content_type='application/json'
    )

    # ASSERT: Debe rechazar la venta
    assert response.status_code in [400, 422]
```

**Qué valida:**
- ✅ No se pueden hacer ventas a crédito sin cliente
- ✅ Regla de negocio crucial
- ✅ Previene problemas de cobro

---

### Ejemplo 12: Productos por Peso Aceptan Decimales

**Archivo**: `sales/tests.py`
**Línea**: ~852

```python
@pytest.mark.integration
def test_weight_based_products_allow_decimals(self, authenticated_client, customer, exchange_rate):
    """Productos por peso deben permitir cantidades decimales"""
    # ARRANGE: Crear producto por peso (kg)
    from factories import ProductFactory
    product = ProductFactory(
        unit_type='kg',
        stock=Decimal('50.00')
    )

    # Preparar venta con cantidad decimal
    sale_data = {
        'items': [
            {
                'product_id': product.id,
                'quantity': 2.5,  # ✅ Cantidad decimal: 2.5 kg
                'price_bs': float(product.selling_price_bs)
            }
        ],
        'customer_id': customer.id,
        'is_credit': False,
        'payment_method': 'cash',
        'total_bs': float(product.selling_price_bs) * 2.5
    }

    # ACT: Crear venta
    response = authenticated_client.post(
        '/sales/api/create/',
        data=sale_data,
        content_type='application/json'
    )

    # ASSERT: Debe aceptar la venta y reducir stock correctamente
    assert response.status_code == 200

    product.refresh_from_db()
    assert product.stock == Decimal('47.50')  # 50 - 2.5 = 47.5
```

**Qué valida:**
- ✅ Productos por peso (kg, litros) aceptan decimales
- ✅ El stock se reduce correctamente con decimales
- ✅ Flexibilidad para diferentes tipos de productos

---

## 🎯 Resumen de Ejemplos

| Ejemplo | Test | Tipo | Criticidad | Línea |
|---------|------|------|------------|-------|
| 1 | Búsqueda por nombre | API | ⭐ Critical | ~418 |
| 2 | Búsqueda por barcode | API | ⭐ Critical | ~447 |
| 3 | Solo productos activos | API | ⭐ Critical | ~517 |
| 4 | Límite de resultados | API | ⭐ Critical | ~555 |
| 5 | Info de stock | API | ⭐ Critical | ~617 |
| 6 | Input presente | View | ⭐ Critical | ~459 |
| 7 | Alpine.js config | View | Normal | ~505 |
| 8 | Búsqueda funcional | Integration | ⭐ Critical | ~548 |
| 9 | Reduce stock | Integration | Normal | ~687 |
| 10 | Validación stock | Integration | ⭐ Critical | ~715 |
| 11 | Crédito requiere cliente | Edge Case | ⭐ Critical | ~828 |
| 12 | Decimales en peso | Edge Case | Normal | ~852 |

---

## 💡 Cómo Usar Estos Ejemplos

### Ejecutar un ejemplo específico:
```bash
# Ejemplo 1: Búsqueda por nombre
pytest inventory/tests.py::TestProductSearchAPI::test_search_by_product_name -v

# Ejemplo 8: Búsqueda desde formulario
pytest sales/tests.py::TestSaleFormProductSearch::test_can_search_products_from_form -v

# Ejemplo 10: Validación de stock
pytest sales/tests.py::TestSaleFormProductAddition::test_cannot_add_more_than_available_stock -v
```

### Modificar un ejemplo:
1. Abre el archivo (`inventory/tests.py` o `sales/tests.py`)
2. Busca el número de línea indicado
3. Modifica el test según tus necesidades
4. Ejecuta el test para verificar

### Crear un test similar:
```python
@pytest.mark.api
@pytest.mark.critical
def test_tu_nuevo_test(self, authenticated_client, category):
    """Descripción clara de qué valida"""
    # ARRANGE: Preparar datos
    producto = ProductFactory(name='Mi Producto', category=category)

    # ACT: Ejecutar acción
    response = authenticated_client.get('/api/products/search/?q=Mi')

    # ASSERT: Verificar resultado
    assert response.status_code == 200
    assert len(response.json()['products']) == 1
```

---

**Actualizado**: 2026-02-24
**Total de ejemplos**: 12
**Archivos**: inventory/tests.py, sales/tests.py
