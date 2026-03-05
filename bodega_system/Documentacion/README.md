# 📚 Documentación - Sistema Ukaro Bodegas

**Versión del Sistema:** 1.0.0
**Framework:** Django 5.2.6
**Python:** 3.13
**Base de Datos:** PostgreSQL
**Última actualización:** 2026-02-25

---

## 📖 Índice General

### [01. Implementación](/01_Implementacion/)
Documentación técnica de características implementadas

- **[Sistema de Pagos, Service Layer y Optimizaciones (FASE 3)](/01_Implementacion/FASE3_Sistema_Pagos_ServiceLayer_Optimizaciones.md)**
  - Sistema completo de pagos a proveedores
  - Service Layer para productos
  - Optimizaciones de base de datos (índices, caché, queries)
  - Métricas de rendimiento
  - 2,729 líneas de código agregadas

### [02. Testing](/02_Testing/)
Resultados de pruebas y cobertura

- **[Resultados Tests FASE 3](/02_Testing/Resultados_Tests_FASE3.md)**
  - 32/36 tests pasando (89% de cobertura crítica)
  - Tests de sistema de pagos (12/12 ✅)
  - Tests de service layer (14/14 ✅)
  - Tests de optimizaciones (6/10)

### [03. Configuración](/03_Configuracion/)
Guías de instalación y configuración

- **[Setup Testing con Playwright](/03_Configuracion/Setup_Testing_Playwright.md)**
  - Configuración de Playwright MCP
  - Datos de prueba
  - Comandos útiles
  - Troubleshooting

### [04. Manuales de Usuario](/04_Manuales_Usuario/)
Guías de uso del sistema

- **[Manual Sistema de Pagos a Proveedores](/04_Manuales_Usuario/Manual_Sistema_Pagos_Proveedores.md)**
  - Cómo registrar pagos
  - Estados de pago (unpaid/partial/paid)
  - Conversión USD/Bs automática
  - Escenarios de prueba

---

## 🚀 Inicio Rápido

### Instalación

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd bodega_system

# 2. Crear entorno virtual
python3 -m venv env
source env/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar base de datos
python3 manage.py migrate

# 5. Crear superusuario
python3 manage.py createsuperuser

# 6. Iniciar servidor
python3 manage.py runserver
```

### Datos de Prueba

```bash
python3 create_test_data.py
```

**Credenciales de prueba:**
- Usuario: `admin_test`
- Password: `test123`

---

## 📊 Arquitectura del Sistema

### Módulos Principales

```
bodega_system/
├── accounts/          # Gestión de usuarios y autenticación
├── inventory/         # Inventario y productos
├── suppliers/         # Proveedores y órdenes de compra
├── sales/            # Ventas y transacciones
├── customers/        # Clientes y créditos
├── finances/         # Finanzas y gastos
└── utils/            # Utilidades (tasa de cambio, etc)
```

### Tecnologías Clave

- **Backend:** Django 5.2.6
- **Base de Datos:** PostgreSQL con optimizaciones
- **Frontend:** Tailwind CSS + Alpine.js
- **Testing:** Django TestCase + Playwright
- **Cache:** Django LocMemCache

---

## 🎯 Características Principales

### ✅ Implementadas

1. **Sistema Multi-Moneda (USD/Bs)**
   - Tasa de cambio configurable
   - Conversión automática
   - Historial de tasas

2. **Gestión de Inventario**
   - Productos con categorías
   - Control de stock
   - Alertas de stock mínimo
   - Service Layer centralizado

3. **Órdenes a Proveedores**
   - Creación y gestión de órdenes
   - Recepción de mercancía
   - Sistema de pagos completo
   - Pagos parciales y totales
   - Historial de pagos

4. **Sistema de Ventas**
   - Ventas de contado y crédito
   - Límites de crédito por cliente
   - Pagos de créditos
   - Historial de transacciones

5. **Optimizaciones de Rendimiento**
   - 10 índices de base de datos
   - Caché de tasa de cambio (99% reducción queries)
   - Query optimization (80-97% reducción)
   - Select_related y Prefetch_related

### 🚧 En Desarrollo

- Reportes financieros avanzados
- Dashboard con métricas
- Integración con APIs de tasa de cambio
- Sistema de notificaciones

---

## 📈 Métricas de Rendimiento

| Operación | Antes | Después | Mejora |
|-----------|-------|---------|--------|
| Lista de órdenes (20 items) | 41 queries | 1 query | **97.6%** ⚡ |
| Detalle de orden | 17 queries | 4 queries | **76.5%** ⚡ |
| Obtener tasa de cambio | 1 query/call | 1 query/hora | **99%** ⚡ |
| Tiempo de carga promedio | ~2.5s | ~0.5s | **80%** ⚡ |

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
python3 manage.py test

# Solo tests de pagos
python3 manage.py test suppliers.tests_payment

# Solo tests de service layer
python3 manage.py test inventory.tests_service

# Con verbosidad
python3 manage.py test --verbosity=2
```

### Cobertura Actual

- **Sistema de Pagos:** 12/12 tests ✅ (100%)
- **Service Layer:** 14/14 tests ✅ (100%)
- **Optimizaciones:** 6/10 tests ✅ (60%)
- **Total:** 32/36 tests ✅ (89%)

---

## 🔧 Configuración de Desarrollo

### Variables de Entorno

```bash
# .env
DEBUG=True
SECRET_KEY=<tu-secret-key>
DATABASE_URL=postgresql://user:pass@localhost/dbname
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Debugging

```bash
# Activar debug toolbar
pip install django-debug-toolbar

# Ver queries SQL en consola
python3 manage.py runserver --verbosity=2
```

---

## 📝 Convenciones de Código

### Estilo Python
- PEP 8 compliance
- Docstrings en todas las funciones públicas
- Type hints donde sea apropiado

### Commits
```
formato: <tipo>(<scope>): <mensaje>

tipos:
- feat: Nueva característica
- fix: Corrección de bug
- docs: Cambios en documentación
- test: Agregar/modificar tests
- refactor: Refactorización sin cambio funcional
- perf: Mejoras de rendimiento
```

### Testing
- Tests para toda lógica de negocio crítica
- Coverage mínimo: 80%
- Tests de integración para flujos completos

---

## 🐛 Troubleshooting

### Problema: ModuleNotFoundError
```bash
# Solución: Activar entorno virtual
source env/bin/activate
```

### Problema: No hay tasa de cambio configurada
```bash
# Solución: Crear tasa desde admin o shell
python3 manage.py shell
>>> from utils.models import ExchangeRate
>>> from decimal import Decimal
>>> ExchangeRate.objects.create(bs_to_usd=Decimal('45.50'))
```

### Problema: Tests fallan por caché
```bash
# Solución: Limpiar caché
python3 manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

---

## 👥 Contribuir

### Workflow

1. Fork del repositorio
2. Crear branch: `git checkout -b feature/nueva-caracteristica`
3. Hacer cambios y commit
4. Push: `git push origin feature/nueva-caracteristica`
5. Crear Pull Request

### Antes de PR

- ✅ Tests pasan
- ✅ Código sigue convenciones
- ✅ Documentación actualizada
- ✅ Sin conflictos con main

---

## 📞 Contacto y Soporte

**Proyecto:** Sistema Ukaro Bodegas
**Repositorio:** <repo-url>
**Documentación:** `/Documentacion/`

---

## 📄 Licencia

[Especificar licencia del proyecto]

---

**Última actualización:** 2026-02-25
**Versión de documentación:** 1.0
