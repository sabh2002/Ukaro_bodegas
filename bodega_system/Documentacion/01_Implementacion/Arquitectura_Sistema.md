# 🏗️ Arquitectura del Sistema - Ukaro Bodegas

## Visión General

Sistema de gestión de bodega con enfoque en control de inventario, ventas, y gestión multi-moneda (USD/Bs).

---

## 📐 Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  Tailwind CSS + Alpine.js + Django Templates               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     DJANGO VIEWS                            │
│  Lógica de presentación y routing                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   SERVICE LAYER                             │
│  ProductService, PaymentService (lógica de negocio)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   DJANGO MODELS (ORM)                       │
│  Product, Supplier, Sale, Customer, etc.                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    POSTGRESQL                               │
│  Base de datos con índices optimizados                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Módulos del Sistema

### 1. **accounts** - Gestión de Usuarios
**Responsabilidad:** Autenticación, permisos, perfiles

```python
models/
├── CustomUser (extends AbstractUser)
│   ├── is_admin: BooleanField
│   ├── is_active: BooleanField
│   └── custom fields...
```

**Características:**
- Login/Logout
- Permisos por rol (admin/empleado)
- Perfiles de usuario

---

### 2. **inventory** - Inventario y Productos
**Responsabilidad:** Gestión de productos, categorías, stock

```python
models/
├── Category
│   └── name, description
├── Product
│   ├── name, barcode, category
│   ├── purchase_price_usd/bs
│   ├── selling_price_usd/bs
│   ├── stock, min_stock
│   └── is_active, created_at
└── HistoricalProduct (simple-history)
```

**Service Layer:**
```python
inventory/services.py
└── ProductService
    ├── validate_product_data()
    ├── calculate_price_bs()
    ├── create_product()
    ├── update_product_prices()
    └── bulk_update_prices()
```

**Características:**
- CRUD de productos
- Control de stock
- Alertas de stock mínimo
- Historial de cambios
- Conversión automática USD/Bs
- Bulk operations

**Optimizaciones:**
```python
# Índices de base de datos
indexes = [
    Index(fields=['category', 'is_active']),
    Index(fields=['is_active', '-created_at']),
    Index(fields=['barcode']),
]
```

---

### 3. **suppliers** - Proveedores y Órdenes
**Responsabilidad:** Gestión de proveedores, órdenes de compra, pagos

```python
models/
├── Supplier
│   ├── name, contact_person
│   ├── phone, email, address
│   └── is_active
├── SupplierOrder
│   ├── supplier, order_date, status
│   ├── total_usd/bs, exchange_rate_used
│   ├── paid_amount_usd/bs (FASE 3.1)
│   ├── paid: BooleanField
│   └── notes
├── SupplierOrderItem
│   ├── order, product
│   ├── quantity
│   └── price_usd/bs
└── SupplierPayment (FASE 3.1)
    ├── order, amount_usd/bs
    ├── exchange_rate_used
    ├── payment_date, payment_method
    ├── reference
    └── created_by
```

**Características:**
- CRUD de proveedores
- Creación de órdenes de compra
- Recepción de mercancía (actualiza stock)
- **Sistema de pagos completo:**
  - Pagos parciales y totales
  - Conversión USD/Bs automática
  - Historial de pagos
  - Estados: unpaid/partial/paid
  - Cálculo automático de saldo pendiente

**Propiedades Computadas:**
```python
@property
def payment_status(self):
    if self.paid_amount_usd >= self.total_usd:
        return 'paid'
    elif self.paid_amount_usd > 0:
        return 'partial'
    return 'unpaid'

@property
def outstanding_balance_usd(self):
    return max(self.total_usd - self.paid_amount_usd, Decimal('0'))
```

**Optimizaciones:**
```python
# Índices
indexes = [
    Index(fields=['supplier', 'status']),
    Index(fields=['status', '-order_date']),
    Index(fields=['paid', '-order_date']),
]

# Query optimization
orders = SupplierOrder.objects.select_related(
    'supplier', 'created_by'
).prefetch_related(
    'items__product', 'payments__created_by'
)
```

---

### 4. **sales** - Ventas
**Responsabilidad:** Transacciones de venta, créditos

```python
models/
├── Sale
│   ├── customer, user, date
│   ├── total_usd/bs, exchange_rate_used
│   ├── is_credit, payment_method
│   └── mobile_reference
└── SaleItem
    ├── sale, product
    ├── quantity
    └── price_usd/bs
```

**Características:**
- Ventas de contado y crédito
- Múltiples métodos de pago
- Actualización automática de stock
- Validación de límites de crédito

**Optimizaciones:**
```python
indexes = [
    Index(fields=['customer', '-date']),
    Index(fields=['user', '-date']),
    Index(fields=['is_credit', '-date']),
    Index(fields=['-date']),
]
```

---

### 5. **customers** - Clientes
**Responsabilidad:** Gestión de clientes, créditos

```python
models/
├── Customer
│   ├── name, phone, email
│   ├── credit_limit_usd/bs
│   ├── current_debt_usd/bs
│   └── is_active
├── CustomerCredit
│   ├── customer, sale
│   ├── amount_usd/bs
│   ├── paid_amount_usd/bs
│   └── is_paid
└── CreditPayment
    ├── credit
    ├── amount_usd/bs
    ├── payment_date, payment_method
    └── reference
```

**Características:**
- CRUD de clientes
- Límites de crédito configurables
- Historial de créditos
- Pagos de créditos
- Alertas de deuda

---

### 6. **finances** - Finanzas
**Responsabilidad:** Gastos, ingresos, reportes

```python
models/
├── ExpenseCategory
│   └── name, description
├── Expense
│   ├── category, description
│   ├── amount_usd/bs
│   ├── date, payment_method
│   └── created_by
└── ExpenseReceipt
    ├── expense
    └── image
```

**Características:**
- Registro de gastos
- Categorización
- Recibos/comprobantes
- Reportes financieros

---

### 7. **utils** - Utilidades
**Responsabilidad:** Funciones compartidas, tasa de cambio

```python
models/
└── ExchangeRate
    ├── date
    ├── bs_to_usd
    ├── updated_by
    └── notes
```

**Características:**
- Gestión de tasa de cambio
- **Caché optimizado (FASE 3.3):**
  ```python
  @classmethod
  def get_latest_rate(cls):
      cache_key = 'exchange_rate_latest'
      cached = cache.get(cache_key)
      if cached:
          return cached

      rate = cls.objects.latest('date')
      cache.set(cache_key, rate, 3600)  # 1 hora
      return rate
  ```
- Invalidación automática al guardar/eliminar
- Historial de tasas

---

## 🔄 Flujos de Datos Principales

### Flujo 1: Orden de Compra a Proveedor

```
1. Crear Orden
   ├─> Seleccionar proveedor
   ├─> Agregar productos (con precios USD)
   ├─> Calcular total USD
   └─> Convertir a Bs con tasa actual

2. Recibir Mercancía
   ├─> Marcar orden como "recibida"
   ├─> Actualizar stock de productos
   └─> Generar movimiento de inventario

3. Registrar Pago (FASE 3.1)
   ├─> Ingresar monto USD
   ├─> Convertir automáticamente a Bs
   ├─> Actualizar totales de orden
   ├─> Actualizar estado (unpaid→partial→paid)
   └─> Guardar en historial
```

### Flujo 2: Venta a Cliente

```
1. Crear Venta
   ├─> Seleccionar cliente
   ├─> Escanear/buscar productos
   ├─> Calcular total USD
   ├─> Convertir a Bs
   └─> Verificar límite de crédito (si aplica)

2. Procesar Pago
   ├─> Contado: Registrar método de pago
   └─> Crédito: Crear registro de deuda

3. Actualizar Stock
   ├─> Reducir stock de cada producto
   └─> Verificar stock mínimo
```

### Flujo 3: Actualización de Tasa de Cambio

```
1. Administrador actualiza tasa
   ├─> Ingresar nueva tasa Bs/USD
   ├─> Guardar con fecha
   └─> Cache.clear() automático

2. Sistema actualiza precios
   ├─> ProductService.bulk_update_prices()
   ├─> Recalcular todos los precios Bs
   └─> Mantener precios USD intactos
```

---

## 🎯 Patrones de Diseño Utilizados

### 1. **Service Layer Pattern**
Centraliza lógica de negocio fuera de views y models.

```python
# inventory/services.py
class ProductService:
    @staticmethod
    def create_product(name, barcode, category, ...):
        # Validaciones
        data = ProductService.validate_product_data({...})

        # Cálculos
        price_bs = ProductService.calculate_price_bs(price_usd)

        # Persistencia
        product = Product.objects.create(...)

        # Logging
        logger.info("Product created", extra={...})

        return product
```

**Ventajas:**
- Reusabilidad (usa en views, management commands, tests)
- Testeable independientemente
- Lógica centralizada

### 2. **Repository Pattern (Django ORM)**
Django ORM actúa como repository pattern.

```python
# Abstracción de acceso a datos
products = Product.objects.filter(is_active=True)
```

### 3. **Observer Pattern (Django Signals)**
Aunque no implementado extensivamente aún, se usa para:

```python
# Ejemplo: Post-save signal
@receiver(post_save, sender=ExchangeRate)
def invalidate_cache(sender, instance, **kwargs):
    cache.delete('exchange_rate_latest')
```

### 4. **Strategy Pattern (Payment Methods)**
Múltiples estrategias de pago.

```python
PAYMENT_METHODS = [
    ('cash', 'Efectivo'),
    ('transfer', 'Transferencia'),
    ('card', 'Tarjeta'),
    ('mobile', 'Pago Móvil'),
]
```

---

## 🔐 Seguridad

### Autenticación y Autorización
```python
# Decoradores de permiso
@login_required
@admin_required
def sensitive_view(request):
    ...
```

### Validaciones
- Input validation en forms
- Model-level constraints
- Service layer validation

### Transacciones Atómicas
```python
from django.db import transaction

@transaction.atomic
def critical_operation():
    # Todo o nada
    ...
```

### SQL Injection Protection
Django ORM previene automáticamente.

---

## 📊 Optimizaciones Implementadas (FASE 3.3)

### 1. Índices de Base de Datos
10 índices compuestos en modelos críticos:
- Product: 3 índices
- SupplierOrder: 3 índices
- Sale: 4 índices

### 2. Query Optimization
```python
# ❌ Antes (N+1 problem)
orders = SupplierOrder.objects.all()
for order in orders:
    print(order.supplier.name)  # Query por cada orden

# ✅ Después
orders = SupplierOrder.objects.select_related('supplier')
for order in orders:
    print(order.supplier.name)  # 1 query total
```

### 3. Caching
```python
# ExchangeRate cacheado 1 hora
# 100+ queries/página → 1 query/hora = 99% reducción
```

### 4. Prefetch Related
```python
order = SupplierOrder.objects.prefetch_related(
    'items__product',
    'payments__created_by'
).get(pk=1)
```

**Resultados:**
- Lista de órdenes: 41 queries → 1 query (97.6% reducción)
- Detalle de orden: 17 queries → 4 queries (76.5% reducción)
- Tasa de cambio: 100+ queries → 1 query (99% reducción)

---

## 🧪 Testing

### Estructura de Tests
```
tests/
├── test_models.py        # Unit tests de modelos
├── test_views.py         # Integration tests de views
├── test_services.py      # Unit tests de service layer
└── test_performance.py   # Performance/benchmark tests
```

### Cobertura
- **suppliers/tests_payment.py**: 12 tests (pagos)
- **inventory/tests_service.py**: 14 tests (service layer)
- **utils/tests_performance.py**: 10 tests (optimizaciones)

---

## 📈 Métricas y Monitoreo

### Queries por Página
```python
# Django Debug Toolbar
# Muestra número de queries, tiempo, duplicados
```

### Cache Hit Rate
```python
# LocMemCache stats
cache_hits / (cache_hits + cache_misses)
```

### Performance Benchmarks
- Tiempo de carga de página
- Queries por operación
- Memoria utilizada

---

## 🚀 Escalabilidad

### Horizontal Scaling
- Stateless views
- Cache compartido (migrar a Redis)
- CDN para archivos estáticos

### Vertical Scaling
- Índices de BD optimizados
- Connection pooling
- Query optimization

### Future Improvements
- [ ] Celery para tareas asíncronas
- [ ] Redis para caché distribuido
- [ ] CDN para static files
- [ ] Docker para deployment
- [ ] Load balancing

---

## 📚 Referencias

- **Django Docs:** https://docs.djangoproject.com/
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **Tailwind CSS:** https://tailwindcss.com/docs

---

**Última actualización:** 2026-02-25
**Versión:** 1.0
