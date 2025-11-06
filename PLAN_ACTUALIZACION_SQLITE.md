# 🔄 PLAN DE ACTUALIZACIÓN PARA PRODUCCIÓN (SQLite)

## 📋 Resumen Ejecutivo

**Base de Datos:** SQLite (archivo `db.sqlite3`)

**Ventaja:** ✅ **SUPER SIMPLE** - Solo necesitas copiar un archivo

**Tiempo de Downtime:** 5-10 minutos

**Riesgo:** 🟢 **MUY BAJO** con backup del archivo

---

## 🎯 Diferencia Clave con SQLite

Con SQLite, el backup es **TAN SIMPLE** como copiar un archivo:

```bash
# Backup = Copiar archivo
cp db.sqlite3 db.sqlite3.backup

# Restaurar = Reemplazar archivo
cp db.sqlite3.backup db.sqlite3
```

**No necesitas:**
- ❌ El módulo de respaldo web
- ❌ Comandos complejos de base de datos
- ❌ Herramientas adicionales

---

## 📍 Ubicación del Archivo SQLite

En tu proyecto Django, el archivo `db.sqlite3` está en:

```
/ruta/a/tu/proyecto/bodega_system/db.sqlite3

Ejemplo:
/home/usuario/bodega_system/db.sqlite3
O
/var/www/bodega_system/db.sqlite3
```

**¿Cómo encontrarlo?**

```bash
# Opción 1: Buscar desde raíz del proyecto
cd /ruta/a/bodega_system
ls -lh db.sqlite3

# Opción 2: Buscar en todo el servidor
find /home -name "db.sqlite3" -type f 2>/dev/null

# Opción 3: Ver configuración de Django
grep -r "sqlite3" bodega_system/settings.py
```

En `settings.py` verás algo como:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # ← Ubicación del archivo
    }
}
```

---

## 🛡️ PLAN DE ACTUALIZACIÓN COMPLETO

### ⏰ **Tiempo Total Estimado: 5-10 minutos**

---

## 📝 PASO A PASO (Sigue este orden)

### **PASO 1: Preparación (2 minutos)**

#### 1.1. Conectarte al Servidor
```bash
# SSH a tu servidor de producción
ssh usuario@tu-servidor.com
```

#### 1.2. Ir a la Carpeta del Proyecto
```bash
cd /ruta/a/tu/proyecto/bodega_system

# Verificar que estás en la carpeta correcta
ls -la
# Debes ver: db.sqlite3, manage.py, carpeta bodega_system/
```

#### 1.3. Verificar Estado Actual
```bash
# Ver branch actual
git branch

# Ver si hay cambios pendientes
git status

# Ver último commit
git log -1
```

---

### **PASO 2: BACKUP (1 minuto) - CRÍTICO**

#### 2.1. Detener el Servidor
```bash
# Opción A: Si usas systemd/gunicorn
sudo systemctl stop gunicorn

# Opción B: Si usas supervisor
sudo supervisorctl stop bodega

# Opción C: Si usas screen/tmux
# Ir a la sesión y hacer Ctrl+C

# Opción D: Si usas runserver en background
pkill -f "python.*manage.py runserver"
```

**¿Por qué detener?** Para asegurar que no haya escrituras al archivo mientras lo copias.

#### 2.2. Crear Backup del Archivo SQLite
```bash
# Backup con fecha y hora
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)

# Ejemplo de resultado:
# db.sqlite3.backup_20251106_153045

# Verificar que se creó
ls -lh db.sqlite3*

# Deberías ver algo como:
# -rw-r--r-- 1 user user 2.5M Nov  6 15:30 db.sqlite3
# -rw-r--r-- 1 user user 2.5M Nov  6 15:30 db.sqlite3.backup_20251106_153045
```

#### 2.3. Copiar Backup a Lugar Seguro
```bash
# Crear carpeta de backups si no existe
mkdir -p ~/backups_bodega

# Copiar backup ahí
cp db.sqlite3.backup_$(date +%Y%m%d_%H%M%S) ~/backups_bodega/

# OPCIONAL: Descargar a tu computadora local
# Desde tu computadora local (nueva terminal):
scp usuario@servidor:/ruta/al/backup/db.sqlite3.backup_* ~/Descargas/
```

---

### **PASO 3: Actualizar Código (2 minutos)**

#### 3.1. Actualizar con Git
```bash
# Fetch últimos cambios
git fetch origin

# Cambiar a la rama con las actualizaciones
git checkout claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5

# Actualizar código
git pull origin claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5

# Verificar que actualizó correctamente
git log -1
# Debes ver el commit más reciente (072d4bb o similar)
```

#### 3.2. Activar Virtual Environment (si usas uno)
```bash
# Si usas virtualenv
source venv/bin/activate

# O si usas otro nombre
source env/bin/activate
```

---

### **PASO 4: Aplicar Migraciones (1 minuto)**

#### 4.1. Ejecutar Migraciones
```bash
python manage.py migrate

# Esperado (output):
# Running migrations:
#   Applying customers.0003_add_usd_fields_to_credits... OK
#   Applying customers.0004_add_payment_method_to_credit_payment... OK
#   Applying finances.0003_expense_add_usd_fields... OK
#   Applying sales.0002_sale_mobile_reference_sale_payment_method... OK
```

**Si ves errores:**
```bash
# NO CONTINUAR - restaurar backup
cp db.sqlite3.backup_[timestamp] db.sqlite3

# Investigar el error antes de reintentar
```

#### 4.2. Verificar Estado de Migraciones
```bash
python manage.py showmigrations

# Todas deben tener [X] marcadas
```

---

### **PASO 5: Archivos Estáticos (30 segundos)**

```bash
python manage.py collectstatic --noinput

# Esto actualiza CSS/JS si hubo cambios en templates
```

---

### **PASO 6: Reiniciar Servidor (30 segundos)**

```bash
# Opción A: systemd/gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn

# Opción B: supervisor
sudo supervisorctl start bodega
sudo supervisorctl status

# Opción C: screen/tmux
screen -S bodega
python manage.py runserver 0.0.0.0:8000

# Opción D: runserver directo (solo para pruebas)
python manage.py runserver 0.0.0.0:8000 &
```

---

### **PASO 7: Verificación (3 minutos) - CRÍTICO**

#### 7.1. Verificar que el Servidor Arrancó
```bash
# Verificar que el proceso está corriendo
ps aux | grep -i gunicorn
# O
ps aux | grep -i "manage.py runserver"

# Verificar que escucha en el puerto
netstat -tulpn | grep 8000
# O
ss -tulpn | grep 8000
```

#### 7.2. Verificar en el Navegador

**Abrir:** `http://tu-dominio.com` o `http://ip-servidor:8000`

**Checklist de Verificación:**

| Prueba | URL | Qué Verificar | ✓ |
|--------|-----|---------------|---|
| **Login** | `/accounts/login/` | Puedes iniciar sesión | [ ] |
| **Dashboard Finanzas** | `/finances/dashboard/` | Muestra USD primero | [ ] |
| **Dashboard Híbrido** | `/finances/dashboard/` | Muestra "Vendido vs Cobrado" | [ ] |
| **Lista Clientes** | `/customers/customer_list/` | Muestra USD en lugar de Bs | [ ] |
| **Crear Venta** | `/sales/sale_create/` | Puedes crear venta | [ ] |
| **Crédito Existente** | `/customers/credits/` | Ver un crédito funciona | [ ] |
| **Pagar Crédito** | `/customers/credit/X/pay/` | Campo referencia móvil aparece | [ ] |
| **Reporte Ganancias** | `/finances/profits_report/` | Muestra USD primero | [ ] |

#### 7.3. Probar Funcionalidad Crítica

**Test 1: Crear Venta de Contado**
1. Ir a Nueva Venta
2. Agregar producto
3. Seleccionar "Efectivo" como método de pago
4. Completar venta
5. ✅ Debe aparecer en dashboard con USD

**Test 2: Registrar Pago de Crédito**
1. Ir a un crédito pendiente
2. Clic "Registrar Pago"
3. Seleccionar "Pago Móvil"
4. ✅ Debe aparecer campo "Referencia"
5. Ingresar monto exacto de la deuda
6. ✅ Debe registrarse sin error

**Test 3: Ver Dashboard Híbrido**
1. Ir a Dashboard de Finanzas
2. ✅ Debe verse sección "Flujo de Caja Hoy"
3. ✅ Debe mostrar "Total Vendido", "Total Cobrado", "Pendiente"

---

### **PASO 8: Backup POST-Actualización (1 minuto)**

```bash
# Crear nuevo backup CON los campos USD
cp db.sqlite3 db.sqlite3.backup_post_update_$(date +%Y%m%d_%H%M%S)

# Copiar a carpeta segura
cp db.sqlite3.backup_post_update_* ~/backups_bodega/

# Este es ahora tu backup PRINCIPAL para futuras restauraciones
```

---

### **PASO 9: (Opcional) Actualizar USD Históricos**

Si tienes datos viejos con `amount_usd = 0`, puedes calcularlos:

```bash
# Crear script temporal
cat > update_historical_usd.py << 'EOF'
from customers.models import CustomerCredit, CreditPayment
from finances.models import Expense
from utils.models import ExchangeRate
from decimal import Decimal

# Obtener tasa de cambio
rate_obj = ExchangeRate.objects.first()
if not rate_obj:
    print("⚠️  No hay tasa de cambio configurada")
    exit(1)

rate = rate_obj.bs_to_usd
print(f"📊 Usando tasa de cambio: {rate} Bs/USD")

# Actualizar CustomerCredit
credits = CustomerCredit.objects.filter(amount_usd=Decimal('0.00'))
count = 0
for credit in credits:
    if credit.amount_bs > 0:
        credit.amount_usd = credit.amount_bs / rate
        credit.exchange_rate_used = rate
        credit.save()
        count += 1
print(f"✅ Actualizados {count} créditos")

# Actualizar CreditPayment
payments = CreditPayment.objects.filter(amount_usd=Decimal('0.00'))
count = 0
for payment in payments:
    if payment.amount_bs > 0:
        payment.amount_usd = payment.amount_bs / rate
        payment.exchange_rate_used = rate
        payment.save()
        count += 1
print(f"✅ Actualizados {count} pagos")

# Actualizar Expense
expenses = Expense.objects.filter(amount_usd=Decimal('0.00'))
count = 0
for expense in expenses:
    if expense.amount_bs > 0:
        expense.amount_usd = expense.amount_bs / rate
        expense.exchange_rate_used = rate
        expense.save()
        count += 1
print(f"✅ Actualizados {count} gastos")

print("🎉 Actualización completa!")
EOF

# Ejecutar script
python manage.py shell < update_historical_usd.py

# Eliminar script temporal
rm update_historical_usd.py
```

---

## 🚨 PLAN DE ROLLBACK (Si algo sale mal)

### **Escenario 1: Error en Migraciones**

```bash
# 1. NO PANIC - El backup existe
# 2. Restaurar backup
cp db.sqlite3.backup_[timestamp] db.sqlite3

# 3. Volver código a versión anterior
git checkout main
# O el branch que usabas antes

# 4. Reiniciar servidor
sudo systemctl restart gunicorn

# 5. Verificar que funciona
# Abrir navegador y probar
```

### **Escenario 2: Servidor No Arranca**

```bash
# 1. Ver logs
# Si usas gunicorn:
sudo journalctl -u gunicorn -f

# Si usas runserver:
python manage.py runserver
# Ver errores en pantalla

# 2. Identificar error
# Común: ModuleNotFoundError, ImportError

# 3. Si no puedes arreglar rápido:
# → Restaurar backup (ver Escenario 1)
```

### **Escenario 3: Todo Funciona Pero Datos Se Ven Mal**

```bash
# Si solo es visual (USD mostrando 0):
# 1. NO RESTAURAR - El sistema funciona
# 2. Ejecutar script de actualización USD históricos (Paso 9)
# 3. Refrescar navegador

# Si es error funcional:
# → Restaurar backup (ver Escenario 1)
```

---

## 📊 Tabla de Tiempos

| Paso | Tiempo | Acumulado | ¿Crítico? |
|------|--------|-----------|-----------|
| 1. Preparación | 2 min | 2 min | No |
| 2. Backup | 1 min | 3 min | **SÍ** ⚠️ |
| 3. Actualizar código | 2 min | 5 min | No |
| 4. Migraciones | 1 min | 6 min | **SÍ** ⚠️ |
| 5. Archivos estáticos | 30 seg | 6.5 min | No |
| 6. Reiniciar | 30 seg | 7 min | No |
| 7. Verificar | 3 min | 10 min | **SÍ** ⚠️ |
| 8. Backup post | 1 min | 11 min | **SÍ** ⚠️ |
| 9. USD históricos (opcional) | 2 min | 13 min | No |

**Downtime Real:** 5-7 minutos (Paso 2 hasta Paso 6)

---

## ✅ Checklist de Pre-Vuelo

Antes de empezar, verifica:

- [ ] Tienes acceso SSH al servidor
- [ ] Sabes ubicación del archivo `db.sqlite3`
- [ ] Sabes cómo detener/iniciar el servidor
- [ ] Tienes espacio en disco (al menos 10MB para backup)
- [ ] Tienes este documento abierto durante el proceso
- [ ] Es horario de bajo tráfico (opcional pero recomendado)
- [ ] Has notificado a usuarios (opcional)

---

## 🎯 Comandos en Secuencia (Copiar y Pegar)

```bash
# ============================================
# COPIAR ESTO COMPLETO (ajustar rutas)
# ============================================

# 1. Ir a carpeta proyecto
cd /ruta/a/bodega_system

# 2. Detener servidor
sudo systemctl stop gunicorn

# 3. BACKUP (CRÍTICO)
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)
mkdir -p ~/backups_bodega
cp db.sqlite3.backup_* ~/backups_bodega/
ls -lh db.sqlite3*

# 4. Actualizar código
git fetch origin
git checkout claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5
git pull origin claude/analyze-finance-credits-module-011CUjhqPBMiKE3tTj2XABH5

# 5. Activar virtual env (si usas)
source venv/bin/activate

# 6. Migrar
python manage.py migrate

# 7. Archivos estáticos
python manage.py collectstatic --noinput

# 8. Reiniciar servidor
sudo systemctl start gunicorn
sudo systemctl status gunicorn

# 9. Verificar proceso
ps aux | grep gunicorn

# 10. Backup POST
cp db.sqlite3 db.sqlite3.backup_post_update_$(date +%Y%m%d_%H%M%S)
cp db.sqlite3.backup_post_update_* ~/backups_bodega/

# 11. Ver backups creados
ls -lh ~/backups_bodega/

echo "✅ Actualización completa! Ahora verifica en el navegador"
```

---

## 💾 Gestión de Backups

### **Estructura Recomendada**

```
~/backups_bodega/
├── db.sqlite3.backup_20251106_150000  ← Pre-actualización
├── db.sqlite3.backup_post_update_20251106_151000  ← Post-actualización (USAR ESTE)
├── db.sqlite3.backup_20251107_080000  ← Backup diario siguiente
└── db.sqlite3.backup_semanal_20251110  ← Backup semanal
```

### **Automatizar Backups Diarios (Recomendado)**

```bash
# Crear script de backup
cat > ~/backup_bodega_daily.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups_bodega
PROJECT_DIR=/ruta/a/bodega_system
DB_FILE=$PROJECT_DIR/db.sqlite3

# Crear carpeta si no existe
mkdir -p $BACKUP_DIR

# Backup con fecha
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp $DB_FILE $BACKUP_DIR/db.sqlite3.backup_$TIMESTAMP

# Mantener solo últimos 7 días
find $BACKUP_DIR -name "db.sqlite3.backup_*" -mtime +7 -delete

# Log
echo "$(date): Backup creado - db.sqlite3.backup_$TIMESTAMP" >> $BACKUP_DIR/backup.log
EOF

# Dar permisos
chmod +x ~/backup_bodega_daily.sh

# Agregar a crontab (diario a las 3 AM)
crontab -e
# Agregar esta línea:
0 3 * * * ~/backup_bodega_daily.sh
```

---

## 📱 Notificación a Usuarios (Template)

**Mensaje sugerido para enviar antes:**

```
🔧 Mantenimiento Programado

Estimados usuarios,

El sistema estará en mantenimiento el [DÍA] de [HORA] a [HORA] (aprox. 10 minutos).

Durante este tiempo:
❌ No podrán acceder al sistema
✅ Después: Mejoras en dashboard financiero y módulo de créditos

Nuevas funciones disponibles después del mantenimiento:
💰 Dashboard con flujo de caja real (Vendido vs Cobrado)
💵 Sistema completo en USD como moneda principal
📱 Campo de referencia para pagos móviles
✅ Mejoras en validación de pagos

Gracias por su comprensión.
```

---

## 🎓 Lecciones Aprendidas - SQLite en Producción

### **Ventajas de SQLite**
✅ Backup super simple (solo copiar archivo)
✅ No requiere configuración de base de datos
✅ Perfecto para proyectos pequeños/medianos
✅ Rollback instantáneo

### **Limitaciones a Considerar**
⚠️ No soporta múltiples escrituras concurrentes
⚠️ Puede tener problemas con muchos usuarios simultáneos
⚠️ Archivo puede corromperse si servidor se apaga abruptamente

### **Cuándo Migrar a PostgreSQL/MySQL**
Si tienes:
- Más de 50 usuarios concurrentes
- Más de 100,000 registros en DB
- Necesitas replicación/alta disponibilidad
- Múltiples servidores de aplicación

---

## 📞 Soporte Durante Actualización

**Si encuentras problemas:**

1. **NO ENTRAR EN PÁNICO** - Tienes backup
2. **Revisar logs** (ver Escenario 2)
3. **Si no puedes resolver en 5 min** → Restaurar backup
4. **Documentar el error** para analizarlo después

---

## 🎉 Resultado Esperado

Después de la actualización, tendrás:

✅ Sistema funcionando normalmente
✅ Dashboard mostrando USD como moneda principal
✅ Dashboard Híbrido mostrando "Vendido vs Cobrado"
✅ Formularios de créditos con campo de referencia móvil
✅ Lista de clientes mostrando USD
✅ Dos backups: pre-actualización y post-actualización
✅ Sistema más robusto y preciso

---

**¿Listo para actualizar? 🚀**

Sigue los pasos en orden y todo saldrá bien. Tienes backup y plan de rollback completo.
