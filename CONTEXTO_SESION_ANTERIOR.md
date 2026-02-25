# Contexto de Sesión Anterior - Sistema Bodega Ukaro

**Proyecto:** Sistema de gestión de bodega con ventas, inventario, finanzas
**Ubicación:** `/home/sabh/Documentos/Smart/Smart_Abastos/Ukaro_bodegas/bodega_system/`
**Stack:** Django 5.2.6 + Python 3.13 + PostgreSQL + Alpine.js
**Usuario:** sabh (Debian)

---

## Estado Actual del Sistema

### Estructura de Apps Django

```
bodega_system/
├── accounts/          # Autenticación, permisos por rol
├── inventory/         # Productos, categorías, ajustes, combos
├── sales/             # Ventas con Alpine.js, búsqueda de productos
├── customers/         # Clientes
├── suppliers/         # Proveedores
├── finances/          # Dashboard financiero, gastos, reportes
└── utils/             # Tasas de cambio, APIs consolidadas
```

### URLs principales

```python
# bodega_system/urls.py
path('api/', include('utils.api_urls'))  # APIs consolidadas

# utils/api_urls.py (ACTUALIZADO)
path('products/search/', inventory_api_views.product_search_api)
path('products/barcode/<str:barcode>/', api_views.product_by_barcode)
path('products/<int:pk>/', inventory_api_views.product_detail_api)
path('customers/search/', api_views.customer_search)
path('combos/search/', inventory_api_views.combo_search_api)
```

---

## Problemas Resueltos en Esta Sesión

### 1. Error NoReverseMatch en `/sales/new/`

**Error:**
```
NoReverseMatch: Reverse for 'finance_dashboard' not found
Location: sales/views.py:128
```

**Causa:** En `finances/urls.py` el name es `'dashboard'`, no `'finance_dashboard'`

**Fix aplicado:**
```python
# sales/views.py:128
# ANTES:
return redirect('finances:finance_dashboard')
# DESPUÉS:
return redirect('finances:dashboard')
```

**Archivo modificado:** `sales/views.py`

---

### 2. Búsqueda de Productos No Funciona en Nueva Venta

**Síntoma:** El input de búsqueda en `/sales/new/` no muestra resultados

**Análisis del flujo:**

```
Usuario escribe → Alpine.js (@input="searchProducts")
    → fetch('/api/products/search/?q=...')
    → ❌ 404 Not Found (ruta no existía)
```

**Template:** `templates/sales/sale_form.html`
- Alpine.js app: `salesApp`
- Función: `searchProducts()` (línea 458)
- Hace fetch a: `/api/products/search/` (línea 480)

**Causa raíz:** Las rutas API estaban comentadas en `utils/api_urls.py`:

```python
# ANTES (líneas 13-14):
# path('products/<int:pk>/', include('inventory.urls', namespace='inventory-api')),
# path('products/search/', include('inventory.urls', namespace='inventory-search')),
```

**Fix aplicado:**

```python
# utils/api_urls.py
from inventory import api_views as inventory_api_views

urlpatterns = [
    # ... rutas existentes ...

    # Inventory APIs (búsqueda de productos) - AGREGADO
    path('products/search/', inventory_api_views.product_search_api, name='product_search_api'),
    path('products/<int:pk>/', inventory_api_views.product_detail_api, name='product_detail_api'),
    path('combos/search/', inventory_api_views.combo_search_api, name='combo_search_api'),
]
```

**Archivos modificados:**
1. `utils/api_urls.py` - Habilitado rutas API
2. Creado `test_search_api.py` - Script de diagnóstico (no ejecutado aún)

---

## Verificación Pendiente

### Estado actual: NECESITA TESTING MANUAL

**El usuario debe hacer:**

1. **Recargar el servidor Django** (si no usa runserver auto-reload):
   ```bash
   cd /home/sabh/Documentos/Smart/Smart_Abastos/Ukaro_bodegas/bodega_system
   source env/bin/activate
   python manage.py runserver
   ```

2. **Abrir navegador:**
   ```
   http://127.0.0.1:8000/sales/new/
   ```

3. **Abrir DevTools (F12):**
   - Tab "Console" → ver errores JavaScript
   - Tab "Network" → filtrar por "search" → ver si `/api/products/search/` responde 200 OK

4. **Probar búsqueda:**
   - Escribir en el input "Buscar Producto"
   - Debe aparecer dropdown con resultados
   - Si falla: copiar errores de Console

### Endpoints que deben funcionar:

```bash
# Test manual desde terminal:
curl "http://127.0.0.1:8000/api/products/search/?q=test&limit=10"
# Respuesta esperada: {"products": [...], "count": X}

curl "http://127.0.0.1:8000/api/customers/search/?q=juan"
# Respuesta esperada: {"customers": [...]}
```

---

## Código Relevante para Debugging

### API de búsqueda de productos

**Ubicación:** `inventory/api_views.py:88-169`

**Función:** `product_search_api(request)`

**Decoradores:**
- `@api_view(['GET'])`
- `@permission_classes([IsAuthenticated])`

**Parámetros GET:**
- `q` (query string, mínimo 2 caracteres)
- `limit` (default 10, max 50)
- `active` (default 'true')
- `category` (opcional)
- `stock` (opcional: 'low', 'out', 'normal')

**Respuesta:**
```json
{
  "products": [
    {
      "id": 1,
      "name": "Producto X",
      "barcode": "123456",
      "category": "Categoría",
      "selling_price_bs": 10.50,
      "stock": 100.0,
      "min_stock": 10.0,
      "unit_display": "Unidad",
      "unit_code": "unit",
      "is_weight_based": false,
      "stock_status": "normal",
      "stock_color": "green",
      "image": "/media/...",
      "is_active": true
    }
  ],
  "count": 1,
  "query": "test"
}
```

### JavaScript Alpine.js en template

**Ubicación:** `templates/sales/sale_form.html:458-498`

**Función crítica:**
```javascript
async searchProducts() {
    const query = this.productSearch.trim();

    if (query.length < 2) return;  // Requiere mínimo 2 caracteres

    clearTimeout(this.searchTimeout);

    this.searchTimeout = setTimeout(async () => {
        const response = await fetch(
            `/api/products/search/?q=${encodeURIComponent(query)}&limit=10`
        );

        const data = await response.json();
        this.productResults = data.products || [];
        this.showProductDropdown = this.productResults.length > 0;
    }, 300); // Debounce 300ms
}
```

**Variables Alpine:**
- `productSearch` (string) - Texto del input
- `productResults` (array) - Productos encontrados
- `showProductDropdown` (boolean) - Mostrar dropdown
- `productSelectedIndex` (int) - Navegación por teclado

---

## Arquitectura de la Búsqueda

```
┌─────────────────────────────────────────────────────────┐
│  Template: sale_form.html                               │
│  <input x-model="productSearch" @input="searchProducts">│
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Alpine.js: searchProducts()                            │
│  - Debounce 300ms                                       │
│  - Mínimo 2 caracteres                                  │
│  - fetch('/api/products/search/?q=...')                 │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Django URL: /api/products/search/                      │
│  → bodega_system/urls.py                                │
│     → path('api/', include('utils.api_urls'))           │
│       → utils/api_urls.py                               │
│         → path('products/search/',                      │
│                inventory_api_views.product_search_api)  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  inventory/api_views.py:88                              │
│  @api_view(['GET'])                                     │
│  @permission_classes([IsAuthenticated])                │
│  def product_search_api(request):                       │
│      - Query con Q() para name/barcode/description      │
│      - Filtros: active, category, stock                 │
│      - Order by: name, -stock                           │
│      - Limit: min(request.limit, 50)                    │
│      - Return: JsonResponse({'products': [...]})        │
└─────────────────────────────────────────────────────────┘
```

---

## Settings Relevantes

**REST Framework:**
```python
# bodega_system/settings.py
INSTALLED_APPS = [
    'rest_framework',  # línea 27
    # ...
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # línea 162
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',  # línea 165
    ],
}
```

**IMPORTANTE:** Las APIs requieren autenticación. El usuario debe estar logueado.

---

## Posibles Errores Restantes

### 1. Usuario no autenticado
```json
{"detail": "Authentication credentials were not provided."}
```
**Fix:** Asegurar que el usuario esté logueado antes de `/sales/new/`

### 2. CSRF Token
Si usa POST sin CSRF token:
```json
{"detail": "CSRF Failed: CSRF token missing or incorrect."}
```
**Fix:** Template ya tiene `{% csrf_token %}` en línea 54

### 3. No hay productos en BD
```json
{"products": [], "count": 0, "query": "test"}
```
**Fix:** Crear productos desde `/inventory/products/add/`

### 4. Permisos de DRF
Si el decorador `@permission_classes([IsAuthenticated])` falla:
```json
{"detail": "You do not have permission to perform this action."}
```
**Fix:** Verificar que el usuario tenga sesión activa

---

## Script de Diagnóstico Creado

**Archivo:** `test_search_api.py` (en raíz del proyecto)

**Uso:**
```bash
cd /home/sabh/Documentos/Smart/Smart_Abastos/Ukaro_bodegas/bodega_system
source env/bin/activate
python test_search_api.py
```

**Qué hace:**
1. ✅ Verifica que las URLs estén registradas
2. ✅ Verifica que haya productos en la BD
3. ✅ Simula request a `product_search_api()`
4. ✅ Simula request a `product_by_barcode()`
5. ✅ Muestra diagnóstico completo

**Nota:** No se ejecutó porque el env no estaba activado y el usuario canceló.

---

## Resumen para Próxima Sesión

### Estado del Sistema: 🟡 PARCIALMENTE FUNCIONAL

**✅ Completado:**
- Fix URL reverse error (finance_dashboard → dashboard)
- Rutas API habilitadas en utils/api_urls.py
- Script de diagnóstico creado

**⏸️ Pendiente verificación:**
- Probar búsqueda de productos en navegador
- Ejecutar script de diagnóstico
- Verificar que los productos se agreguen al carrito correctamente

**🔍 Siguiente paso recomendado:**
1. Ejecutar `python manage.py runserver`
2. Abrir `/sales/new/` en navegador
3. F12 → Console y Network
4. Intentar buscar un producto
5. Si falla: copiar errores exactos de Console

### Archivos Modificados en Esta Sesión

```
sales/views.py                  ← Fix redirect finance_dashboard → dashboard
utils/api_urls.py               ← Habilitado rutas de inventory APIs
test_search_api.py              ← Creado script diagnóstico (nuevo archivo)
```

### Comando Git para Commit (si funciona todo):

```bash
git add sales/views.py utils/api_urls.py
git commit -m "Fix: búsqueda de productos en nueva venta

- Corregido redirect a finances:dashboard (era finance_dashboard)
- Habilitadas rutas API de inventory en utils/api_urls.py
- Agregado product_search_api, product_detail_api, combo_search_api

Las búsquedas ahora responden en /api/products/search/"
```

---

## Información de Contexto Adicional

### Servidor de Desarrollo

```bash
# Working directory
cd /home/sabh/Documentos/Smart/Smart_Abastos/Ukaro_bodegas/bodega_system

# Virtual env
source env/bin/activate

# Runserver
python manage.py runserver  # → http://127.0.0.1:8000
```

### Acceso Admin

```
URL: http://127.0.0.1:8000/admin/
Usuario: (el que creó el usuario con createsuperuser)
```

### Crear Productos de Prueba

Si no hay productos:
```
1. Admin → Inventory → Categories → Agregar categoría
2. Admin → Inventory → Products → Agregar producto
   - Nombre: "Producto Test"
   - Barcode: "123456789"
   - Precio: 10.00
   - Stock: 100
   - Is active: ✓
```

### Verificar Tasa de Cambio

La búsqueda usa precios en BS, que se calculan desde USD usando tasa de cambio:

```
Admin → Utils → Exchange Rates → Verificar que exista al menos una
```

Si no existe: `/sales/new/` mostrará error al intentar cargar.

---

## Comunicación Inter-IA

**Para el próximo Claude:**

- Usuario cambió de chat por error
- Este proyecto NO es SmartSolutions (landing page Django)
- Este proyecto ES Sistema de Bodega (inventario + ventas)
- La búsqueda de productos está **teóricamente arreglada** pero **sin testing manual**
- El usuario usa Debian, Python 3.13, tiene dos proyectos en paralelo
- Path completo proyecto: `/home/sabh/Documentos/Smart/Smart_Abastos/Ukaro_bodegas/bodega_system/`
- Path otro proyecto: `/home/sabh/Documentos/Smart Solutions/smartsolutions/`

**Estado emocional del usuario:** Ligeramente frustrado porque se cambió de chat y perdió contexto. Necesita que todo funcione para poder continuar.

**Prioridad inmediata:** Hacer que la búsqueda de productos funcione. Es crítico para el flujo de ventas.

**Técnica recomendada:** Pedirle screenshots de DevTools Console + Network si reporta errores. Es la forma más rápida de diagnosticar sin acceso directo al navegador.
