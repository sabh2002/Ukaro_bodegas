# 📘 GUÍA: Cómo Registrar Pagos de Créditos de Clientes

---

## 🎯 RESPUESTA RÁPIDA

**Pregunta:** ¿Cómo cancelo la deuda de un cliente?

**Respuesta:** Hay **3 formas** de acceder al formulario de pago:

1. **Desde el detalle del cliente** → Botón "💵" en la tabla de créditos
2. **Desde el detalle del crédito** → Botón verde "Registrar Pago"
3. **Desde la lista de créditos** → Botón "💵" en cada fila

---

## 📍 FLUJO COMPLETO: Paso a Paso

### PASO 1: Localizar el Crédito a Pagar

#### **Opción A: Desde el Cliente**

```
1. Ve a: Clientes → Lista de Clientes
2. Busca al cliente por nombre o busca "Clientes con Deudas"
3. Haz clic en el nombre del cliente
4. Verás la sección "Créditos Activos"
```

En la tabla de créditos activos verás algo así:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ CRÉDITOS ACTIVOS                                                         │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ Fecha    │ Venta #  │ Total    │ Pagado   │ Pendiente│ Acciones        │
├──────────┼──────────┼──────────┼──────────┼──────────┼─────────────────┤
│ 03/11/25 │ #1234    │ $50 USD  │ $0 USD   │ $50 USD  │ 👁️ 💵         │
│          │          │ Bs 1800  │ Bs 0     │ Bs 1800  │ Ver  Pagar     │
└──────────┴──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

**Haz clic en el ícono 💵 (dinero) para registrar un pago.**

---

#### **Opción B: Desde la Lista de Créditos**

```
1. Ve a: Clientes → Créditos
2. Verás TODOS los créditos del sistema
3. Filtra por "Pendientes" o busca por cliente
```

Verás una tabla similar:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LISTA DE CRÉDITOS                                                        │
├──────────┬──────────────┬──────────┬──────────┬──────────┬─────────────┤
│ Cliente  │ Fecha        │ Monto    │ Pagado   │ Estado   │ Acciones    │
├──────────┼──────────────┼──────────┼──────────┼──────────┼─────────────┤
│ Juan P.  │ 03/11/25     │ $50 USD  │ $0 USD   │ Pendiente│ 👁️ 💵     │
│          │              │ Bs 1800  │ Bs 0     │          │ Ver  Pagar │
└──────────┴──────────────┴──────────┴──────────┴──────────┴─────────────┘
```

**Haz clic en 💵 para pagar.**

---

#### **Opción C: Desde el Detalle del Crédito**

```
1. Desde cualquiera de las opciones anteriores, haz clic en 👁️ (Ver)
2. Esto te lleva a la vista detallada del crédito
3. En la parte superior derecha verás un botón verde "Registrar Pago"
```

---

### PASO 2: Rellenar el Formulario de Pago

Al hacer clic en cualquiera de los botones de pago, verás este formulario:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ REGISTRAR PAGO DE CRÉDITO                                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ 💡 RESUMEN DEL CRÉDITO                                                  │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Monto Total:      $50.00 USD (Bs 1,800.00)                         │ │
│ │ Pagado:           $0.00 USD (Bs 0.00)                              │ │
│ │ PENDIENTE:        $50.00 USD (Bs 1,800.00)    ← LO QUE FALTA      │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ 💰 MONTO A PAGAR (Bs) *                                                 │
│ ┌──────────────────────────────────────────────────────────────────┐   │
│ │ Bs [ 1800.00 ]                                       ← EDITABLE   │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ 📌 BOTONES RÁPIDOS:                                                     │
│ [ 100% ] [ 75% ] [ 50% ] [ 25% ] [ 10% ]      ← CLIC PARA AUTOCOMPLETAR│
│                                                                          │
│ Equivalente: $50.00 USD (Tasa: 36.00)         ← SE CALCULA AUTO        │
│                                                                          │
│ 💳 MÉTODO DE PAGO *                            ← ¡NUEVO!                │
│ ┌──────────────────────────────────────────────────────────────────┐   │
│ │ [v] 💵 Efectivo      ▼                                            │   │
│ │     💳 Punto de Venta                                             │   │
│ │     📱 Pago Móvil                                                 │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ 📱 REFERENCIA DE PAGO MÓVIL (si elegiste Pago Móvil)                   │
│ ┌──────────────────────────────────────────────────────────────────┐   │
│ │ [ 0123456789 ]                              ← SOLO SI ES MÓVIL   │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ 📝 NOTAS (Opcional)                                                     │
│ ┌──────────────────────────────────────────────────────────────────┐   │
│ │ [ Cliente pagó con billete de $100... ]                          │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ [ Cancelar ]                           [ 💾 REGISTRAR PAGO ]            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### PASO 3: Llenar los Campos

#### 1️⃣ **Monto a Pagar (Bs)** - OBLIGATORIO

Tienes 3 formas de ingresar el monto:

**A) Botones Rápidos (Recomendado):**
- **100%** → Pago completo ($50 USD)
- **75%** → $37.50 USD
- **50%** → $25 USD (pago parcial)
- **25%** → $12.50 USD
- **10%** → $5 USD

Al hacer clic en cualquier botón, el campo se llena automáticamente.

**B) Escribir Manualmente:**
```
Ingresa: 1800
Verás: "Equivalente: $50.00 USD"
```

**C) Pago Parcial:**
```
Si el cliente solo paga $20 USD:
Ingresa: 720  (20 USD × 36 = 720 Bs)
El sistema validará que no exceda el saldo pendiente
```

#### 2️⃣ **Método de Pago** - OBLIGATORIO (¡NUEVO!)

Selecciona cómo pagó el cliente:

```
💵 Efectivo        → Cliente pagó en efectivo
💳 Punto de Venta  → Cliente pagó con tarjeta (punto)
📱 Pago Móvil      → Cliente pagó por transferencia
```

#### 3️⃣ **Referencia de Pago Móvil** - CONDICIONAL

**Solo aparece si seleccionaste "Pago Móvil".**

Ejemplo:
```
📱 Pago Móvil seleccionado
┌────────────────────────────────────────┐
│ Referencia: [ 0123456789 ] *          │
└────────────────────────────────────────┘
```

Si no ingresas la referencia, verás error:
❌ "La referencia es requerida para pagos móviles."

#### 4️⃣ **Notas** - OPCIONAL

Puedes agregar información adicional:
```
Ejemplos:
- "Cliente pagó con billete de $100, cambio: $50"
- "Pago parcial acordado con gerente"
- "Última cuota del crédito"
```

---

### PASO 4: Guardar el Pago

Haz clic en **"REGISTRAR PAGO"** (botón verde).

El sistema hará:

1. ✅ **Validar** que el monto no exceda el saldo pendiente
2. ✅ **Calcular** el equivalente en USD automáticamente
3. ✅ **Guardar** la tasa de cambio usada en ese momento
4. ✅ **Guardar** el método de pago seleccionado
5. ✅ **Actualizar** el estado del crédito

---

### PASO 5: Resultado

#### Si el pago fue COMPLETO (100%):

```
✅ Crédito pagado completamente.

El crédito cambia a estado: PAGADO ✅
Ya no aparecerá en "Créditos Activos"
Se moverá a "Historial de Créditos"
```

#### Si el pago fue PARCIAL:

```
✅ Pago registrado exitosamente.

Crédito sigue en estado: PENDIENTE ⏳
Nuevo saldo pendiente: $30 USD (si pagó $20)
Cliente puede seguir pagando hasta completar
```

---

## 🔍 EJEMPLO PRÁCTICO COMPLETO

### Caso Real: Juan Pérez debe $50 USD

```
SITUACIÓN INICIAL:
─────────────────────────────────────────────────
Cliente:        Juan Pérez
Crédito Total:  $50.00 USD (Bs 1,800 a tasa 36)
Pagado:         $0.00 USD
Pendiente:      $50.00 USD
Estado:         ⏳ PENDIENTE
```

---

### **Escenario 1: Pago Total en Efectivo**

```
PASO 1: Juan viene y paga todo
PASO 2: Vas a: Clientes → Juan Pérez → Clic en 💵

FORMULARIO:
┌──────────────────────────────────────────────┐
│ Monto:       [ 1800 ] Bs  → Clic en [100%]  │
│ Método:      [💵 Efectivo]                  │
│ Referencia:  (no aplica)                     │
│ Notas:       "Pago completo"                 │
└──────────────────────────────────────────────┘

RESULTADO:
✅ Crédito pagado completamente
Estado:        ✅ PAGADO
Pendiente:     $0.00 USD
```

---

### **Escenario 2: Pago Parcial por Pago Móvil**

```
PASO 1: Juan solo paga $20 USD (Bs 720)
PASO 2: Vas a: Clientes → Juan Pérez → Clic en 💵

FORMULARIO:
┌──────────────────────────────────────────────┐
│ Monto:       [ 720 ] Bs  → Manual           │
│ Método:      [📱 Pago Móvil]                │
│ Referencia:  [ 0123456789 ] ← OBLIGATORIO   │
│ Notas:       "Abono parcial, resto próxima" │
└──────────────────────────────────────────────┘

RESULTADO:
✅ Pago registrado exitosamente
Estado:        ⏳ PENDIENTE
Pagado:        $20.00 USD
Pendiente:     $30.00 USD ← Falta esto
```

Juan puede volver después y pagar los $30 restantes.

---

### **Escenario 3: Múltiples Pagos Hasta Completar**

```
PAGO 1 (Día 1):
   Monto:    $20 USD (Bs 720)
   Método:   💵 Efectivo
   Estado:   ⏳ PENDIENTE
   Falta:    $30 USD

PAGO 2 (Día 5):
   Monto:    $15 USD (Bs 540)
   Método:   💳 Punto
   Estado:   ⏳ PENDIENTE
   Falta:    $15 USD

PAGO 3 (Día 10):
   Monto:    $15 USD (Bs 540)
   Método:   📱 Pago Móvil
   Ref:      0987654321
   Estado:   ✅ PAGADO
   Falta:    $0 USD ← ¡COMPLETADO!
```

---

## 📊 VISUALIZACIÓN EN EL SISTEMA

### Vista del Cliente (customer_detail.html):

```
┌────────────────────────────────────────────────────────────────────┐
│ 👤 JUAN PÉREZ                                                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 💳 INFORMACIÓN DE CRÉDITO                                          │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ Límite:         $100.00 USD (Bs 3,600)                       │  │
│ │ Usado:          $50.00 USD                                   │  │
│ │ Disponible:     $50.00 USD    ← PUEDE SEGUIR COMPRANDO      │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│ 📋 CRÉDITOS ACTIVOS (1)                                            │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ Venta #1234 │ $50 USD │ Pagado: $20 │ Falta: $30 │ 👁️ 💵   │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                     ↑                               │
│                              CLIC AQUÍ PARA PAGAR                  │
└────────────────────────────────────────────────────────────────────┘
```

---

### Vista del Crédito (credit_detail.html):

```
┌────────────────────────────────────────────────────────────────────┐
│ 💰 DETALLE DEL CRÉDITO #123                                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ Cliente: Juan Pérez                          [ 💾 Registrar Pago ] │
│ Venta: #1234                                     ↑                 │
│ Fecha: 03/11/2025                         BOTÓN VERDE AQUÍ        │
│                                                                     │
│ 💵 MONTO                                                           │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ Total:      $50.00 USD (Bs 1,800)                            │  │
│ │ Pagado:     $20.00 USD (Bs 720)                              │  │
│ │ Pendiente:  $30.00 USD (Bs 1,080)   ← LO QUE FALTA          │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│ 📜 HISTORIAL DE PAGOS (1)                                          │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ 01/11/25 │ $20 USD │ 💵 Efectivo │ Juan pagó inicial       │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│                                                                     │
│                           [ 💾 Registrar Pago ]                    │
│                                  ↑                                 │
│                         TAMBIÉN AQUÍ ABAJO                         │
└────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ CARACTERÍSTICAS TÉCNICAS

### ✅ Lo que el sistema hace AUTOMÁTICAMENTE:

1. **Cálculo USD**: Convierte Bs → USD usando tasa actual
2. **Validación**: No permite pagar más del saldo pendiente
3. **Tasa Histórica**: Guarda la tasa usada en cada pago
4. **Estado**: Actualiza a "PAGADO" cuando se completa
5. **Método de Pago**: Guarda cómo pagó el cliente
6. **Suma de Pagos**: Acumula todos los pagos parciales
7. **Auditoría**: Registra quién recibió el pago (usuario actual)

### 📝 Campos Guardados en la Base de Datos:

```python
CreditPayment:
    credit            # Relación al crédito
    amount_bs         # 720
    amount_usd        # 20.00
    exchange_rate_used # 36.00
    payment_method    # 'cash', 'card', o 'mobile'
    mobile_reference  # '0123456789' (si es móvil)
    payment_date      # 2025-11-04 14:30:00
    received_by       # Usuario que registró el pago
    notes             # Nota opcional
```

---

## 🚨 ERRORES COMUNES Y SOLUCIONES

### Error 1: "El monto excede el saldo pendiente"

```
❌ PROBLEMA:
Intentas pagar $60 USD pero solo debe $50 USD

✅ SOLUCIÓN:
Verifica el saldo pendiente en el resumen
Ingresa un monto menor o igual al pendiente
```

### Error 2: "La referencia es requerida para pagos móviles"

```
❌ PROBLEMA:
Seleccionaste "Pago Móvil" pero no pusiste referencia

✅ SOLUCIÓN:
Ingresa el número de referencia de la transferencia
O cambia el método de pago a Efectivo/Punto
```

### Error 3: No veo el botón de pagar

```
❌ PROBLEMA:
El crédito ya está PAGADO

✅ SOLUCIÓN:
Si el crédito muestra ✅ PAGADO, ya no se puede pagar más
Verifica en el historial de pagos que todo esté correcto
```

---

## 🎓 PREGUNTAS FRECUENTES

### ❓ ¿Puedo eliminar un pago registrado por error?

Actualmente NO hay opción de eliminar pagos desde la interfaz.
Debes contactar al administrador del sistema.

### ❓ ¿Qué pasa si cambio la tasa de cambio después de crear el crédito?

Cada pago usa la tasa de cambio ACTUAL en el momento del pago.
El crédito original mantiene su tasa histórica.
Esto es correcto y permite reflejar la realidad económica.

### ❓ ¿Puedo hacer un pago mayor al saldo pendiente?

NO. El sistema validará y mostrará error.
Solo puedes pagar hasta el monto pendiente exacto.

### ❓ ¿Cómo sé qué método de pago usó el cliente en cada pago?

Ve al detalle del crédito y mira el "Historial de Pagos".
Cada pago muestra su método con icono (💵, 💳, 📱).

---

## 📸 UBICACIONES DE LOS BOTONES DE PAGO

### 1. **customer_detail.html** (Detalle del Cliente)
```
Ruta: Clientes → [Nombre del Cliente]
Ubicación: Tabla "Créditos Activos" → Columna "Acciones" → Ícono 💵
```

### 2. **credit_detail.html** (Detalle del Crédito)
```
Ruta: Clientes → Créditos → [Ver crédito]
Ubicación:
   - Superior derecha: Botón verde "Registrar Pago"
   - Inferior: Botón verde "Registrar Pago"
```

### 3. **credit_list.html** (Lista de Créditos)
```
Ruta: Clientes → Créditos
Ubicación: Tabla de créditos → Columna "Acciones" → Ícono 💵
```

---

## 🎯 RESUMEN EJECUTIVO

### Para registrar un pago de crédito:

1. **Encuentra el crédito** (desde cliente, lista, o detalle)
2. **Haz clic en 💵** o botón "Registrar Pago"
3. **Llena el formulario**:
   - Monto en Bs (usa botones rápidos)
   - Método de pago (Efectivo/Punto/Móvil)
   - Referencia (solo si es Pago Móvil)
   - Notas opcionales
4. **Guarda** → Sistema calcula USD automáticamente
5. **Listo** → Crédito actualizado

### El sistema es inteligente:
- ✅ Acepta pagos parciales
- ✅ Acumula múltiples pagos
- ✅ Calcula USD automáticamente
- ✅ Valida que no pagues de más
- ✅ Guarda método de pago usado
- ✅ Marca como PAGADO cuando se completa

---

**FIN DE LA GUÍA** 📘
