# ⚙️ Documentación de Configuración

Guías de instalación, configuración y setup del sistema.

---

## 📄 Documentos Disponibles

### [Setup Testing con Playwright](Setup_Testing_Playwright.md)
**Descripción:** Configuración completa de entorno de testing con Playwright MCP.

**Contenido:**
- Configuración de Playwright MCP
- Datos de prueba
- Credenciales de acceso
- Scripts de testing
- Comandos útiles
- Troubleshooting

**Cuándo leer:** Al configurar entorno de testing o debugging de tests.

---

## 🚀 Instalación Rápida

### Requisitos Previos

```bash
# Sistema
- Python 3.13+
- PostgreSQL 14+
- Node.js 18+ (opcional, para Playwright)
- Git

# Linux (Debian/Ubuntu)
sudo apt update
sudo apt install python3 python3-pip python3-venv postgresql
```

### Setup Básico

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
# Editar bodega_system/settings.py con tus credenciales de PostgreSQL

# 5. Migraciones
python3 manage.py migrate

# 6. Crear superusuario
python3 manage.py createsuperuser

# 7. Datos de prueba (opcional)
python3 create_test_data.py

# 8. Iniciar servidor
python3 manage.py runserver
```

### Acceso

- **URL:** http://localhost:8000
- **Admin:** http://localhost:8000/admin/
- **Usuario de prueba:** admin_test / test123

---

## 🔧 Configuración Avanzada

### Variables de Entorno

Crear archivo `.env` en la raíz:

```bash
# .env
DEBUG=True
SECRET_KEY=tu-secret-key-super-secreta-aqui
DATABASE_URL=postgresql://usuario:password@localhost/bodega_db
ALLOWED_HOSTS=localhost,127.0.0.1,tu-dominio.com

# Email (opcional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-password

# Cache (opcional - Redis)
REDIS_URL=redis://localhost:6379/0
```

### Configurar PostgreSQL

```bash
# 1. Crear usuario
sudo -u postgres createuser -P bodega_user

# 2. Crear base de datos
sudo -u postgres createdb -O bodega_user bodega_db

# 3. Configurar en settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bodega_db',
        'USER': 'bodega_user',
        'PASSWORD': 'tu-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Configurar Cache (Redis - Opcional)

```bash
# 1. Instalar Redis
sudo apt install redis-server

# 2. Instalar cliente Python
pip install redis django-redis

# 3. Configurar en settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

---

## 🧪 Configuración de Testing

### Playwright (Testing de Browser)

```bash
# 1. Instalar Playwright
pip install playwright

# 2. Instalar navegadores
playwright install firefox

# 3. Configurar Claude Code MCP
# Ver: Setup_Testing_Playwright.md
```

### Coverage (Cobertura de Tests)

```bash
# 1. Instalar coverage
pip install coverage

# 2. Ejecutar con coverage
coverage run --source='.' manage.py test

# 3. Ver reporte
coverage report

# 4. Generar HTML
coverage html
# Ver en: htmlcov/index.html
```

### Django Debug Toolbar

```bash
# 1. Instalar
pip install django-debug-toolbar

# 2. Agregar a INSTALLED_APPS
INSTALLED_APPS = [
    ...
    'debug_toolbar',
]

# 3. Agregar middleware
MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    ...
]

# 4. Configurar IPs permitidas
INTERNAL_IPS = ['127.0.0.1']
```

---

## 🐳 Docker (Opcional)

### Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN apt-update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: bodega_db
      POSTGRES_USER: bodega_user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://bodega_user:password@db/bodega_db

volumes:
  postgres_data:
```

### Comandos Docker

```bash
# Construir
docker-compose build

# Iniciar
docker-compose up

# Migraciones
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Detener
docker-compose down
```

---

## 📝 Archivos de Configuración Importantes

### settings.py
```python
# Configuración principal de Django
- DATABASES
- INSTALLED_APPS
- MIDDLEWARE
- STATIC_FILES
- CACHE
- LOGGING
```

### urls.py
```python
# Routing principal
- Admin
- API endpoints
- App routes
```

### requirements.txt
```
# Dependencias Python
Django==5.2.6
psycopg2-binary==2.9.x
...
```

### .gitignore
```
# Archivos a ignorar
env/
*.pyc
__pycache__/
db.sqlite3
.env
staticfiles/
media/
```

---

## 🔍 Verificación de Configuración

### Checklist Post-Instalación

```bash
# ✅ Entorno virtual activado
which python  # Debe mostrar ruta con /env/

# ✅ Base de datos conectada
python3 manage.py dbshell
\q

# ✅ Migraciones aplicadas
python3 manage.py showmigrations

# ✅ Archivos estáticos
python3 manage.py collectstatic

# ✅ Tests funcionan
python3 manage.py test

# ✅ Servidor inicia
python3 manage.py runserver
```

### Comandos de Diagnóstico

```bash
# Ver configuración de Django
python3 manage.py diffsettings

# Verificar problemas
python3 manage.py check

# Ver migraciones pendientes
python3 manage.py showmigrations --plan

# Ver información del sistema
python3 manage.py --version
python3 --version
psql --version
```

---

## 🐛 Troubleshooting Común

### Error: ModuleNotFoundError

**Problema:** `ModuleNotFoundError: No module named 'django'`

**Solución:**
```bash
# Activar entorno virtual
source env/bin/activate

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: Database Connection

**Problema:** `django.db.utils.OperationalError: could not connect to server`

**Solución:**
```bash
# Verificar PostgreSQL corriendo
sudo systemctl status postgresql

# Iniciar si está detenido
sudo systemctl start postgresql

# Verificar credenciales en settings.py
```

### Error: Static Files

**Problema:** `StaticFilesNotFound`

**Solución:**
```bash
# Recolectar archivos estáticos
python3 manage.py collectstatic --no-input
```

### Error: Migrations

**Problema:** `django.db.migrations.exceptions.InconsistentMigrationHistory`

**Solución:**
```bash
# Opción 1: Revertir y re-aplicar
python3 manage.py migrate <app> zero
python3 manage.py migrate

# Opción 2: Fake (si los cambios ya están en BD)
python3 manage.py migrate --fake <app> <migration>
```

---

## 📚 Referencias

- [Django Settings Reference](https://docs.djangoproject.com/en/stable/ref/settings/)
- [PostgreSQL Setup](https://www.postgresql.org/docs/)
- [Docker Django](https://docs.docker.com/samples/django/)
- [Playwright Docs](https://playwright.dev/python/)

---

**Última actualización:** 2026-02-25
**Versión de Django:** 5.2.6
**Python requerido:** 3.13+
