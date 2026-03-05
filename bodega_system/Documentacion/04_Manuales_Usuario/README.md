# 📖 Manuales de Usuario

Guías de uso del sistema para usuarios finales y administradores.

---

## 📄 Documentos Disponibles

### [Manual del Sistema de Pagos a Proveedores](Manual_Sistema_Pagos_Proveedores.md)
**Descripción:** Guía completa para usar el sistema de pagos a proveedores.

**Contenido:**
- Cómo registrar pagos
- Ver historial de pagos
- Estados de pago (unpaid/partial/paid)
- Conversión automática USD/Bs
- Eliminar pagos
- Escenarios de uso
- Troubleshooting

**Destinatarios:** Administradores, Personal de cuentas por pagar

**Cuándo leer:** Al necesitar registrar o gestionar pagos a proveedores.

---

## 👥 Roles del Sistema

### 👨‍💼 Administrador
**Permisos:**
- ✅ Gestión completa de usuarios
- ✅ Configuración de tasa de cambio
- ✅ Gestión de productos, categorías
- ✅ Gestión de proveedores y clientes
- ✅ Crear y gestionar órdenes
- ✅ Registrar y eliminar pagos
- ✅ Ver todos los reportes
- ✅ Gestión de gastos

**Acceso:** Panel de administración completo

### 👤 Empleado/Vendedor
**Permisos:**
- ✅ Realizar ventas
- ✅ Ver inventario
- ✅ Ver clientes
- ✅ Ver historial de ventas propias
- ❌ No puede eliminar pagos
- ❌ No puede cambiar tasa de cambio
- ❌ No puede eliminar órdenes

**Acceso:** Panel limitado a funciones de venta

---

## 📚 Módulos del Sistema

### 1. 📦 Inventario

**Funciones principales:**
- Ver lista de productos
- Buscar productos por nombre/código de barras
- Ver detalles de producto (stock, precios, categoría)
- Alertas de stock bajo

**Acceso:**
```
Inicio → Inventario → Productos
```

**Usuarios:** Todos los roles

---

### 2. 🏢 Proveedores

**Funciones principales:**
- Lista de proveedores
- Ver información de contacto
- Historial de órdenes por proveedor

**Acceso:**
```
Inicio → Proveedores → Lista de Proveedores
```

**Usuarios:** Administradores, Personal de compras

#### Órdenes de Compra

**Funciones:**
- Crear nueva orden de compra
- Agregar productos a orden
- Recibir mercancía
- Registrar pagos (ver manual específico)
- Ver historial de pagos

**Flujo típico:**
```
1. Crear Orden → 2. Recibir Mercancía → 3. Registrar Pagos
```

**Acceso:**
```
Inicio → Proveedores → Órdenes de Compra
```

---

### 3. 💰 Ventas

**Funciones principales:**
- Registrar venta de contado
- Registrar venta a crédito
- Seleccionar productos
- Aplicar descuentos
- Ver historial de ventas

**Flujo de venta:**
```
1. Nueva Venta
2. Seleccionar cliente (opcional)
3. Escanear/buscar productos
4. Ajustar cantidades
5. Seleccionar método de pago
6. Confirmar venta
```

**Acceso:**
```
Inicio → Ventas → Nueva Venta
Inicio → Ventas → Historial
```

**Usuarios:** Vendedores, Administradores

---

### 4. 👥 Clientes

**Funciones principales:**
- Lista de clientes
- Ver créditos activos
- Historial de compras
- Registrar pagos de créditos

**Gestión de créditos:**
- Ver límite de crédito
- Ver deuda actual
- Registrar abonos
- Historial de pagos

**Acceso:**
```
Inicio → Clientes → Lista
Inicio → Clientes → Créditos
```

**Usuarios:** Todos los roles (ver), Administradores (modificar)

---

### 5. 💵 Finanzas

**Funciones principales:**
- Registrar gastos
- Categorías de gastos
- Subir comprobantes
- Reportes de gastos

**Acceso:**
```
Inicio → Finanzas → Gastos
Inicio → Finanzas → Reportes
```

**Usuarios:** Administradores

---

### 6. 💱 Tasa de Cambio

**Funciones:**
- Ver tasa actual
- Actualizar tasa
- Historial de tasas

**⚠️ Importante:**
- La tasa afecta TODOS los precios en Bs
- Solo administradores pueden modificar
- Se recomienda actualizar diariamente

**Acceso:**
```
Inicio → Administración → Tasa de Cambio
```

**Usuarios:** Solo Administradores

---

## 🎯 Tareas Comunes

### Tarea: Registrar una Venta

**Pasos:**
1. Click en "Ventas" → "Nueva Venta"
2. Seleccionar cliente (opcional)
3. Escanear código de barras o buscar producto
4. Ajustar cantidad si necesario
5. Repetir para más productos
6. Verificar total
7. Seleccionar método de pago:
   - Contado: Elegir efectivo/tarjeta/transferencia/móvil
   - Crédito: Sistema verifica límite automáticamente
8. Click "Confirmar Venta"
9. Imprimir factura (opcional)

**Tiempo estimado:** 2-3 minutos

---

### Tarea: Crear Orden de Compra

**Pasos:**
1. Click en "Proveedores" → "Órdenes" → "Nueva Orden"
2. Seleccionar proveedor
3. Agregar productos:
   - Buscar producto o crear nuevo
   - Ingresar cantidad
   - Ingresar precio USD
   - Sistema calcula Bs automáticamente
4. Agregar más productos si necesario
5. Verificar total
6. Agregar notas (opcional)
7. Click "Crear Orden"

**Estado inicial:** Pendiente

**Tiempo estimado:** 5-10 minutos

---

### Tarea: Recibir Mercancía

**Pasos:**
1. Ir a "Proveedores" → "Órdenes"
2. Click en orden "Pendiente"
3. Verificar productos recibidos
4. Click "Recibir Orden"
5. Confirmar

**Resultado:**
- ✅ Stock de productos actualizado
- ✅ Estado cambia a "Recibida"
- ⏳ Lista para registrar pagos

**Tiempo estimado:** 2 minutos

---

### Tarea: Registrar Pago a Proveedor

**Pasos:** Ver [Manual del Sistema de Pagos](Manual_Sistema_Pagos_Proveedores.md)

**Resumen:**
1. Abrir orden
2. Click "Registrar Pago"
3. Ingresar monto USD
4. Seleccionar método
5. Agregar referencia (opcional)
6. Confirmar

**Tiempo estimado:** 1-2 minutos

---

### Tarea: Actualizar Tasa de Cambio

**Pasos:**
1. Ir a "Administración" → "Tasa de Cambio"
2. Click "Nueva Tasa"
3. Ingresar tasa Bs/USD (ej: 45.50)
4. Agregar notas (opcional): "Tasa BCV del día X"
5. Click "Guardar"

**Resultado:**
- ✅ Nueva tasa activa
- ✅ Precios Bs se actualizan automáticamente
- ✅ Precios USD permanecen igual

**⚠️ Importante:** Hacer esto AL INICIO del día.

**Tiempo estimado:** 30 segundos

---

## ❓ Preguntas Frecuentes (FAQ)

### ¿Puedo cambiar precios en Bs directamente?

**No.** Los precios en Bs se calculan automáticamente desde USD usando la tasa de cambio. Solo modifica el precio USD.

---

### ¿Qué pasa si elimino un pago por error?

**Administradores pueden eliminar pagos.** El sistema recalcula automáticamente los totales. Si necesitas restaurar, debes registrar el pago nuevamente.

---

### ¿Puedo hacer un pago mayor al saldo pendiente?

**No.** El sistema valida que el monto no exceda el saldo pendiente para evitar sobrepagos.

---

### ¿Cómo veo el historial de cambios de un producto?

Ir a "Inventario" → Click en producto → Tab "Historial"

---

### ¿Puedo cancelar una venta ya realizada?

**Solo administradores.** Las ventas no se pueden "eliminar" pero se puede crear una venta de devolución (con cantidades negativas).

---

### ¿Qué pasa si vendo un producto sin stock?

El sistema **NO permite** vender productos con stock 0 o insuficiente. Debes recibir mercancía primero.

---

## 🐛 Problemas Comunes

### Problema: "No hay tasa de cambio configurada"

**Causa:** No existe una tasa de cambio activa

**Solución:**
1. Contactar administrador
2. Administrador debe ir a "Administración" → "Tasa de Cambio"
3. Crear nueva tasa

---

### Problema: "El cliente excede su límite de crédito"

**Causa:** La venta haría que el cliente supere su límite

**Solución:**
- Opción 1: Cliente debe pagar parte de su deuda
- Opción 2: Administrador aumenta límite de crédito
- Opción 3: Realizar venta de contado

---

### Problema: "Stock insuficiente"

**Causa:** No hay suficiente stock del producto

**Solución:**
1. Verificar stock actual
2. Ajustar cantidad en venta
3. O crear orden de compra para reabastecer

---

### Problema: No puedo ver el botón "Registrar Pago"

**Causa:** Ya pagaste el total de la orden

**Solución:** Verificar en sección "Estado de Pagos" si ya está marcado como "Pagado" 🟢

---

## 📞 Soporte

### Contacto Técnico
- **Email:** soporte@ukaro.com
- **Teléfono:** +XX XXXX-XXXX
- **Horario:** Lun-Vie 8am-6pm

### Reportar Problemas
1. Tomar screenshot del error
2. Anotar pasos para reproducir
3. Enviar a soporte técnico

### Solicitar Nuevas Funciones
Contactar a administrador del sistema para evaluar viabilidad.

---

## 📚 Recursos Adicionales

- [Manual de Pagos a Proveedores](Manual_Sistema_Pagos_Proveedores.md)
- [Video tutoriales](#) (próximamente)
- [Glosario de términos](#) (próximamente)

---

**Última actualización:** 2026-02-25
**Versión del manual:** 1.0
**Aplica a versión del sistema:** 1.0.0
