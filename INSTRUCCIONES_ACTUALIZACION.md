# 📥 INSTRUCCIONES: Cómo Actualizar Tu Proyecto Local

**Fecha:** 2025-11-06
**Branch:** `claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5`
**Estado:** ✅ Correcciones críticas del módulo de créditos completadas

---

## 🎯 ¿QUÉ SE CORRIGIÓ?

He solucionado **6 problemas críticos** en el módulo de créditos:

1. ✅ **Créditos ahora SE MARCAN como PAGADOS** correctamente
2. ✅ **Formulario de cliente muestra límite de crédito en USD**
3. ✅ **Filtros funcionan correctamente con USD**
4. ✅ **Comparaciones Decimal precisas** (sin problemas de redondeo)
5. ✅ **Templates muestran USD como moneda principal**
6. ✅ **Mensajes claros** sobre saldo pendiente en USD

**Detalle completo en:** `ANALISIS_CRITICO_CREDITOS.md`

---

## 📋 PASO A PASO: Actualizar Tu Proyecto

### **PASO 1: Hacer Backup de Tu Base de Datos**

⚠️ **MUY IMPORTANTE:** Antes de actualizar, haz un backup:

```bash
# Si usas SQLite:
cp db.sqlite3 db.sqlite3.backup

# Si usas PostgreSQL:
pg_dump nombre_bd > backup_$(date +%Y%m%d_%H%M%S).sql

# Si usas MySQL:
mysqldump nombre_bd > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

### **PASO 2: Descargar Los Cambios**

Abre tu terminal en la carpeta del proyecto y ejecuta:

```bash
# 1. Ver tu branch actual
git branch

# 2. Si NO estás en claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5, cámbiate
git checkout claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5

# 3. Descargar los últimos cambios
git pull origin claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5
```

**Deberías ver algo así:**
```
remote: Counting objects: 10, done.
remote: Compressing objects: 100% (8/8), done.
remote: Total 10 (delta 5), reused 0 (delta 0)
Unpacking objects: 100% (10/10), done.
From http://...
   f67b19a..8b3c550  claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5 -> origin/claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5
Updating f67b19a..8b3c550
Fast-forward
 ANALISIS_CRITICO_CREDITOS.md                           | 396 +++++++++++++++++++
 bodega_system/customers/views.py                       |  24 +-
 bodega_system/templates/customers/customer_form.html   |  28 +-
 3 files changed, 420 insertions(+), 28 deletions(-)
```

---

### **PASO 3: Verificar Archivos Actualizados**

```bash
# Ver qué cambió
git log -1 --stat

# Deberías ver:
# - ANALISIS_CRITICO_CREDITOS.md (nuevo)
# - bodega_system/customers/views.py (modificado)
# - bodega_system/templates/customers/customer_form.html (modificado)
```

---

### **PASO 4: Reiniciar el Servidor**

```bash
# Si el servidor está corriendo, detenlo (Ctrl+C)

# Luego reinicia
python manage.py runserver

# O si usas un entorno virtual:
# Windows:
venv\Scripts\activate
python manage.py runserver

# Linux/Mac:
source venv/bin/activate
python manage.py runserver
```

---

## ✅ VERIFICACIÓN: Probar Que Todo Funciona

### **Test 1: Crear Nuevo Cliente con Límite USD**

1. Ve a: **Clientes → Nuevo Cliente**
2. ✅ **AHORA DEBERÍA APARECER:** Campo "Límite de Crédito (USD)"
3. Ingresa un monto, ejemplo: `100`
4. Guarda el cliente
5. ✅ **VERIFICAR:** En el detalle del cliente, debería mostrar:
   - Límite: `$100.00 USD`
   - Usado: `$0.00 USD`
   - Disponible: `$100.00 USD`

---

### **Test 2: Editar Cliente Existente**

1. Ve a: **Clientes → [Selecciona un cliente] → Editar**
2. ✅ **VERIFICAR:** Campo "Límite de Crédito (USD)" está visible
3. ✅ **VERIFICAR:** Campos "Crédito Utilizado" y "Disponible" muestran USD

---

### **Test 3: Pagar Crédito Completo**

1. Ve a un crédito pendiente
2. Haz clic en "Registrar Pago"
3. Paga el **100%** del monto
4. Guarda el pago
5. ✅ **VERIFICAR:** Mensaje dice "Crédito pagado completamente."
6. Ve a: **Clientes → Créditos**
7. ✅ **VERIFICAR:** El crédito ahora muestra estado **"Pagado"** ✅ (NO "Pendiente")

---

### **Test 4: Pago Parcial**

1. Crea un nuevo crédito de $100 USD
2. Registra un pago de solo $30 USD
3. ✅ **VERIFICAR:** Mensaje dice "Pago registrado exitosamente. Saldo pendiente: $70.00 USD"
4. Ve al detalle del crédito
5. ✅ **VERIFICAR:**
   - Total: `$100.00 USD`
   - Pagado: `$30.00 USD`
   - Pendiente: `$70.00 USD`
6. Ve a: **Clientes → Créditos**
7. ✅ **VERIFICAR:** Estado sigue siendo **"Pendiente"** ⏳ (correcto)

---

### **Test 5: Completar Pago Parcial**

Continuando del test anterior:

1. Registra otro pago de $70 USD (el saldo restante)
2. ✅ **VERIFICAR:** Mensaje dice "Crédito pagado completamente."
3. Ve a: **Clientes → Créditos**
4. ✅ **VERIFICAR:** Ahora el crédito está en estado **"Pagado"** ✅

---

## 🔍 SOLUCIÓN DE PROBLEMAS

### ❌ Problema: "No aparece el campo de límite de crédito"

**Causa:** El navegador tiene caché del template antiguo.

**Solución:**
```bash
# 1. Detén el servidor (Ctrl+C)

# 2. Limpia caché de Django
python manage.py collectstatic --clear --noinput

# 3. Reinicia el servidor
python manage.py runserver

# 4. En el navegador:
# - Presiona Ctrl+Shift+R (forzar recarga sin caché)
# - O abre una ventana de incógnito
```

---

### ❌ Problema: "Los créditos siguen apareciendo como pendientes"

**Causa:** Datos antiguos en la base de datos antes de la corrección.

**Solución:** Necesitas re-guardar los créditos afectados.

**Opción A - Por la interfaz:**
1. Ve al detalle de cada crédito problemático
2. Si el saldo pendiente es $0.00
3. Edita el crédito (sin cambiar nada)
4. Guarda
5. El campo `is_paid` se actualizará

**Opción B - Por Django shell:**
```bash
python manage.py shell
```

Luego ejecuta:
```python
from customers.models import CustomerCredit
from decimal import Decimal
from django.db.models import Sum

# Encontrar créditos que deberían estar pagados pero no lo están
for credit in CustomerCredit.objects.filter(is_paid=False):
    total_paid = credit.payments.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    total_paid_rounded = round(total_paid, 2)
    credit_amount_rounded = round(credit.amount_usd, 2)

    if total_paid_rounded >= credit_amount_rounded:
        credit.is_paid = True
        from django.utils import timezone
        credit.date_paid = timezone.now()
        credit.save()
        print(f"✅ Crédito #{credit.id} marcado como pagado")

print("✅ Proceso completado")
```

Sal del shell:
```python
exit()
```

---

### ❌ Problema: "Clientes tienen límite negativo"

**Diagnóstico:** Ejecuta esto en Django shell:

```python
python manage.py shell
```

```python
from customers.models import Customer

# Ver clientes con límite negativo o inválido
clientes_problema = Customer.objects.filter(credit_limit_usd__lt=0)
for c in clientes_problema:
    print(f"Cliente: {c.name}, Límite USD: {c.credit_limit_usd}")

# Ver clientes que exceden su límite
from django.db.models import Sum

for c in Customer.objects.all():
    usado = c.credits.filter(is_paid=False).aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    if usado > c.credit_limit_usd:
        print(f"⚠️ {c.name}: Límite ${c.credit_limit_usd}, Usado ${usado}")
```

**Corrección:** Ajusta manualmente los límites en la interfaz admin o por shell.

---

## 📊 DIFERENCIAS ANTES vs DESPUÉS

### **ANTES (Con Problemas):**
```
Problema 1: Pagas crédito completo → Sigue mostrando "Pendiente" ❌
Problema 2: Formulario cliente → Campo límite NO aparece ❌
Problema 3: Lista clientes → Filtro USD no funciona ❌
Problema 4: Comparaciones Decimal → Errores de redondeo ❌
Problema 5: Templates → Muestran Bs en lugar de USD ❌
```

### **AHORA (Corregido):**
```
✅ Pagas crédito completo → Cambia a "Pagado" inmediatamente
✅ Formulario cliente → Campo "Límite de Crédito (USD)" visible
✅ Lista clientes → Filtro USD funciona correctamente
✅ Comparaciones Decimal → Precisión exacta a 2 decimales
✅ Templates → USD como moneda principal, Bs secundario
✅ Mensajes claros sobre saldo pendiente en USD
```

---

## 📝 PRÓXIMOS PASOS

Una vez que verifiques que TODO funciona correctamente, me avisas y continuamos con:

### **Pendiente 1: Sistema Híbrido Dashboard (Opción C)**
- Mostrar "Total Vendido" vs "Total Cobrado"
- Separar ventas a contado de ventas a crédito
- Vista clara del flujo de caja

### **Pendiente 2: Módulo Finanzas TODO en USD**
- Dashboard: Mostrar USD principal
- Profits Report: Ganancias en USD
- Todos los reportes consistentes

---

## ❓ SI TIENES PROBLEMAS

1. **Revisa los logs del servidor:**
   ```bash
   # Busca errores en la terminal donde corre el servidor
   ```

2. **Verifica la migración:**
   ```bash
   python manage.py showmigrations customers

   # Debe mostrar:
   # [X] 0001_initial
   # [X] 0002_initial
   # [X] 0003_add_usd_fields_to_credits
   # [X] 0004_add_payment_method_to_credit_payment
   ```

3. **Si hay errores, contáctame con:**
   - Captura de pantalla del error
   - Comando que ejecutaste
   - Líneas relevantes del log

---

## 🎉 CONFIRMACIÓN FINAL

Una vez que hayas probado TODO y funcione correctamente, responde:

1. ✅ "Los créditos ahora se marcan como pagados"
2. ✅ "El formulario de cliente muestra el límite en USD"
3. ✅ "Los pagos parciales muestran saldo pendiente correcto"

Luego continuamos con los **Problemas 2 y 4** (Dashboard Híbrido + Finanzas en USD).

---

**¡IMPORTANTE!** Si encuentras CUALQUIER problema durante las pruebas, avísame INMEDIATAMENTE antes de continuar.

---

**FIN DE LAS INSTRUCCIONES**
