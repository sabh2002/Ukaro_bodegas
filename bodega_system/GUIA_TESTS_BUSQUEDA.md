# Guía de Tests - Funcionalidad de Búsqueda de Productos

## 🚀 Inicio Rápido

### Ejecutar todos los tests de búsqueda
```bash
./run_search_tests.sh all
```

### Ejecutar solo tests críticos
```bash
./run_search_tests.sh critical
```

### Ejecutar con reporte de cobertura
```bash
./run_search_tests.sh coverage
```

---

## 📚 Categorías de Tests

### 1. Tests de API (21 tests)
Validan el endpoint `/api/products/search/` que usa el formulario

```bash
./run_search_tests.sh api
```

**Qué validan:**
- ✅ Búsqueda por nombre, código de barras, descripción, categoría
- ✅ Filtrado de productos activos/inactivos
- ✅ Límites de resultados (10 por defecto, máx 50)
- ✅ Información de stock y precios
- ✅ Autenticación requerida

**Ejemplo de test:**
```python
def test_search_by_product_name(self, authenticated_client, category):
    """Debe encontrar productos por nombre exacto"""
    product = ProductFactory(name='Coca Cola 2L', category=category)

    response = authenticated_client.get('/api/products/search/?q=Coca')

    assert response.status_code == 200
    assert len(response.json()['products']) == 1
```

---

### 2. Tests del Formulario (9 tests)
Validan que el HTML del formulario tenga todos los elementos necesarios

```bash
./run_search_tests.sh form
```

**Qué validan:**
- ✅ Input de búsqueda presente
- ✅ Selector de método de pago
- ✅ Checkbox de crédito
- ✅ Botón de completar venta
- ✅ Alpine.js configurado
- ✅ Exchange rate pasado al JS

**Ejemplo de test:**
```python
def test_sale_form_has_product_search_input(self, authenticated_client):
    """El formulario debe tener el input de búsqueda de productos"""
    response = authenticated_client.get('/sales/new/')

    assert response.status_code == 200
    assert 'id="product_search"' in response.content.decode('utf-8')
```

---

### 3. Tests de Integración (9 tests)
Validan el flujo completo: búsqueda → selección → agregar al carrito → crear venta

```bash
./run_search_tests.sh integration
```

**Qué validan:**
- ✅ Agregar productos al carrito reduce stock
- ✅ Validación de stock disponible
- ✅ Productos por peso aceptan decimales
- ✅ Venta a crédito requiere cliente
- ✅ Múltiples productos en una venta

**Ejemplo de test:**
```python
def test_add_product_reduces_stock(self, authenticated_client, product, customer):
    """Agregar producto a venta debe reducir el stock"""
    initial_stock = product.stock

    sale_data = {
        'items': [{'product_id': product.id, 'quantity': 5, ...}],
        'customer_id': customer.id,
        'payment_method': 'cash',
        ...
    }

    response = authenticated_client.post('/sales/api/create/', ...)

    product.refresh_from_db()
    assert product.stock == initial_stock - Decimal('5')
```

---

## 🎯 Tests Críticos

Estos tests validan la lógica de negocio más importante:

```bash
./run_search_tests.sh critical
```

### Tests críticos de API (8 tests)
- `test_search_by_product_name` - Búsqueda básica funcional
- `test_search_by_barcode` - Escaneo de códigos de barras
- `test_search_by_category_name` - Búsqueda por categoría
- `test_search_returns_only_active_products` - Solo productos activos
- `test_search_limits_results_to_default_10` - Límite de resultados
- `test_search_returns_stock_information` - Info de stock correcta
- `test_search_returns_complete_product_data` - Estructura completa

### Tests críticos de integración (6 tests)
- `test_sale_form_has_product_search_input` - Input presente
- `test_can_search_products_from_form` - Búsqueda funcional
- `test_add_product_to_cart_via_api` - Crear venta exitosa
- `test_cannot_add_more_than_available_stock` - Validación de stock
- `test_credit_sale_requires_customer` - Validación de crédito

---

## 📊 Reporte de Cobertura

Generar reporte HTML con cobertura detallada:

```bash
./run_search_tests.sh coverage
```

Esto genera:
- Reporte en terminal con líneas faltantes
- Reporte HTML en `htmlcov/index.html`
- Cobertura específica de `inventory/api_views.py` y `sales/`

**Abrir reporte:**
```bash
firefox htmlcov/index.html  # Linux
open htmlcov/index.html     # macOS
start htmlcov/index.html    # Windows
```

---

## 🔍 Tests Específicos

### Ejecutar un test individual
```bash
pytest inventory/tests.py::TestProductSearchAPI::test_search_by_product_name -v
```

### Ejecutar tests con palabra clave
```bash
pytest -k "search" -v
pytest -k "barcode" -v
pytest -k "stock" -v
```

### Ejecutar con más detalle en fallos
```bash
pytest inventory/tests.py::TestProductSearchAPI -v --tb=long
```

### Ejecutar en modo verbose con prints
```bash
pytest inventory/tests.py::TestProductSearchAPI -v -s
```

---

## 🐛 Debugging

### Ver output de print statements
```bash
pytest inventory/tests.py::TestProductSearchAPI::test_search_by_product_name -v -s
```

### Ver variables locales en fallos
```bash
pytest inventory/tests.py::TestProductSearchAPI -v --tb=long --showlocals
```

### Parar en el primer fallo
```bash
pytest inventory/tests.py::TestProductSearchAPI -x
```

### Ejecutar solo tests que fallaron anteriormente
```bash
pytest --lf  # last failed
```

---

## 📝 Estructura de los Tests

### Tests de API (`inventory/tests.py`)
```
TestProductSearchAPI/
├── Búsqueda por criterios (5 tests)
│   ├── test_search_by_product_name
│   ├── test_search_by_barcode
│   ├── test_search_by_partial_barcode
│   ├── test_search_by_description
│   └── test_search_by_category_name
├── Filtrado (3 tests)
│   ├── test_search_returns_only_active_products
│   ├── test_search_can_include_inactive_products
│   └── test_search_with_category_filter
├── Límites (3 tests)
│   ├── test_search_limits_results_to_default_10
│   ├── test_search_respects_custom_limit
│   └── test_search_max_limit_is_50
├── Validación (3 tests)
│   ├── test_search_with_short_query
│   ├── test_search_empty_query_returns_empty_list
│   └── test_search_case_insensitive
├── Stock (1 test)
│   └── test_search_returns_stock_information
├── Estructura (1 test)
│   └── test_search_returns_complete_product_data
├── Ordenamiento (1 test)
│   └── test_search_ordering
└── Seguridad (1 test)
    └── test_search_without_authentication_fails
```

### Tests de Integración (`sales/tests.py`)
```
TestSaleFormView/ (9 tests)
├── test_sale_form_loads_successfully
├── test_sale_form_requires_authentication
├── test_sale_form_has_product_search_input ⭐
├── test_sale_form_has_customer_search_input
├── test_sale_form_has_payment_method_select
├── test_sale_form_has_credit_checkbox
├── test_sale_form_has_complete_button
├── test_sale_form_includes_alpine_js
└── test_sale_form_passes_exchange_rate_to_js

TestSaleFormProductSearch/ (5 tests)
├── test_can_search_products_from_form ⭐
├── test_search_shows_product_price_in_bs
├── test_search_shows_stock_status
├── test_search_excludes_out_of_stock_products_display
└── test_barcode_search_exact_match

TestSaleFormProductAddition/ (5 tests)
├── test_add_product_to_cart_via_api ⭐
├── test_add_product_reduces_stock
├── test_cannot_add_more_than_available_stock ⭐
├── test_add_multiple_products_to_sale
└── (más tests...)

TestSaleFormEdgeCases/ (4 tests)
├── test_sale_without_customer_is_anonymous
├── test_credit_sale_requires_customer ⭐
├── test_weight_based_products_allow_decimals
└── (más tests...)
```

---

## 🔧 Fixtures Utilizadas

Los tests usan fixtures de `conftest.py`:

### Usuarios
- `admin_user` - Usuario administrador
- `employee_user` - Usuario empleado
- `authenticated_client` - Cliente web autenticado

### Productos
- `category` - Categoría de productos
- `product` - Producto básico con stock
- `product_with_bulk_pricing` - Producto con precio mayorista

### Finanzas
- `exchange_rate` - Tasa de cambio actual (36.50 Bs/USD)
- `customer` - Cliente con límite de crédito

### API
- `api_client` - Cliente web sin autenticar

**Ejemplo de uso:**
```python
def test_example(self, authenticated_client, product, customer):
    # authenticated_client ya está logueado
    # product ya existe en la BD
    # customer ya existe en la BD

    response = authenticated_client.get(f'/api/products/{product.id}/')
    assert response.status_code == 200
```

---

## 🎨 Markers de Pytest

Los tests están organizados con markers:

```python
@pytest.mark.api          # Tests de endpoints API
@pytest.mark.critical     # Tests críticos de negocio
@pytest.mark.views        # Tests de templates/vistas
@pytest.mark.integration  # Tests de integración completa
```

### Ejecutar por marker
```bash
pytest -m api -v              # Solo tests de API
pytest -m critical -v          # Solo tests críticos
pytest -m views -v             # Solo tests de vistas
pytest -m integration -v       # Solo tests de integración
```

### Combinar markers
```bash
pytest -m "api and critical" -v
pytest -m "not integration" -v
```

---

## ✅ Checklist Antes de Commit

1. ✅ Ejecutar tests críticos
   ```bash
   ./run_search_tests.sh critical
   ```

2. ✅ Verificar cobertura > 80%
   ```bash
   ./run_search_tests.sh coverage
   ```

3. ✅ Todos los tests pasan
   ```bash
   ./run_search_tests.sh all
   ```

4. ✅ No hay warnings importantes
   ```bash
   pytest -v --strict-markers
   ```

---

## 🚨 Troubleshooting

### Error: pytest no encontrado
```bash
pip install pytest pytest-django pytest-cov
```

### Error: ModuleNotFoundError
```bash
# Asegúrate de estar en el directorio correcto
cd /path/to/bodega_system

# O configura PYTHONPATH
export PYTHONPATH=/path/to/bodega_system:$PYTHONPATH
```

### Tests fallan por base de datos
```bash
# Crear migraciones
python manage.py makemigrations
python manage.py migrate

# O ejecutar con --create-db
pytest --create-db
```

### Tests muy lentos
```bash
# Ejecutar en paralelo
pytest -n auto

# O solo tests rápidos
pytest -m "not slow"
```

---

## 📚 Recursos Adicionales

- **Documentación de pytest**: https://docs.pytest.org/
- **pytest-django**: https://pytest-django.readthedocs.io/
- **Factory Boy**: https://factoryboy.readthedocs.io/
- **Resumen completo**: Ver `TESTS_RESUMEN_BUSQUEDA_PRODUCTOS.md`

---

## 💡 Tips de Testing

### 1. Usa fixtures para datos repetitivos
```python
@pytest.fixture
def product_with_low_stock(db, category):
    return ProductFactory(
        category=category,
        stock=Decimal('3'),
        min_stock=Decimal('10')
    )
```

### 2. Nombra tests descriptivamente
```python
# ❌ Mal
def test_search():
    ...

# ✅ Bien
def test_search_by_barcode_returns_exact_match():
    ...
```

### 3. Un assert por concepto
```python
# ✅ Bien
response = client.get('/api/products/search/?q=Coca')
assert response.status_code == 200

data = response.json()
assert len(data['products']) == 1
assert data['products'][0]['name'] == 'Coca Cola'
```

### 4. Usa markers para organizar
```python
@pytest.mark.critical
@pytest.mark.api
def test_important_api_behavior():
    ...
```

---

**Actualizado**: 2026-02-24
**Versión**: 1.0
**Total de tests**: 28 nuevos tests de búsqueda
