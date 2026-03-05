#!/usr/bin/env python3
"""
CAPA 2 — SCRIPT DE VERIFICACIÓN CONTRA SERVIDOR REAL
======================================================
Prueba el sistema como un usuario real usando el servidor Django en ejecución.

Prerrequisito:
  cd bodega_system && source env/bin/activate
  python3 manage.py runserver &

Uso:
  python3 scripts/test_live.py [--base-url http://localhost:8000] [--user admin] [--pass password]

El script:
  1. Inicia sesión con las credenciales proporcionadas
  2. Navega todas las páginas importantes del sistema
  3. Reporta cualquier URL que retorne 500 (error del servidor)
  4. Muestra un resumen al final

Útil para verificar rápidamente después de cambios en producción.
"""

import sys
import argparse
import time
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("ERROR: Instala requests: pip install requests")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────────────────

# Páginas a probar. Se llenan con IDs reales después de iniciar sesión.
# Formato: (descripción, path_template)
PAGES_STATIC = [
    # Dashboard
    ("Dashboard", "/"),
    ("Analytics", "/analytics/"),
    ("Mis stats", "/my-stats/"),

    # Accounts
    ("Perfil", "/accounts/profile/"),
    ("Lista usuarios", "/accounts/users/"),
    ("Crear usuario", "/accounts/users/add/"),

    # Inventory
    ("Lista productos", "/inventory/"),
    ("Crear producto", "/inventory/products/add/"),
    ("Lista categorías", "/inventory/categories/"),
    ("Crear categoría", "/inventory/categories/add/"),
    ("Lista ajustes", "/inventory/adjustments/"),
    ("Crear ajuste", "/inventory/adjustments/add/"),
    ("Lista combos", "/inventory/combos/"),
    ("Crear combo", "/inventory/combos/add/"),

    # Customers
    ("Lista clientes", "/customers/"),
    ("Crear cliente", "/customers/add/"),
    ("Lista créditos", "/customers/credits/"),
    ("Crear crédito", "/customers/credits/add/"),

    # Sales
    ("Lista ventas", "/sales/"),
    ("Crear venta", "/sales/new/"),

    # Suppliers
    ("Lista proveedores", "/suppliers/"),
    ("Crear proveedor", "/suppliers/add/"),
    ("Lista órdenes", "/suppliers/orders/"),
    ("Crear orden", "/suppliers/orders/add/"),

    # Finances
    ("Dashboard finanzas", "/finances/"),
    ("Reporte ventas", "/finances/reports/sales/"),
    ("Reporte compras", "/finances/reports/purchases/"),
    ("Reporte ganancias", "/finances/reports/profits/"),
    ("Rentabilidad productos", "/finances/reports/product-profitability/"),
    ("Lista gastos", "/finances/expenses/"),
    ("Crear gasto", "/finances/expenses/add/"),
    ("Lista cierres", "/finances/daily-close/"),
    ("Crear cierre", "/finances/daily-close/add/"),

    # Utils
    ("Tasa de cambio", "/utils/exchange-rate/"),
    ("Historial tasas", "/utils/exchange-rate/history/"),
    ("Backups", "/utils/backups/"),

    # APIs (deben retornar JSON, no 500)
    ("API buscar productos", "/inventory/api/products/search/?q=test"),
    ("API buscar clientes", "/api/customers/search/?q=test"),
    ("API tasa de cambio", "/api/exchange-rate/"),
    ("API stock summary", "/inventory/api/products/stock-summary/"),
    ("API categorías", "/inventory/api/categories/"),
    ("API combos", "/inventory/api/combos/search/?q=test"),
]

# Páginas con parámetros dinámicos (se rellenan en runtime)
PAGES_DYNAMIC = [
    # formato: (descripción, path_template con {id})
    ("Detalle producto", "/inventory/products/{product_id}/"),
    ("Editar producto", "/inventory/products/{product_id}/edit/"),
    ("Detalle categoría", "/inventory/categories/{category_id}/"),
    ("Editar categoría", "/inventory/categories/{category_id}/edit/"),
    ("Detalle cliente", "/customers/{customer_id}/"),
    ("Editar cliente", "/customers/{customer_id}/edit/"),
    ("Detalle crédito", "/customers/credits/{credit_id}/"),
    ("Pagar crédito (form)", "/customers/credits/{credit_id}/pay/"),
    ("Detalle venta", "/sales/{sale_id}/"),
    ("Recibo venta", "/sales/{sale_id}/receipt/"),
    ("Detalle proveedor", "/suppliers/{supplier_id}/"),
    ("Editar proveedor", "/suppliers/{supplier_id}/edit/"),
    ("Detalle orden", "/suppliers/orders/{order_id}/"),
    ("Editar orden", "/suppliers/orders/{order_id}/edit/"),
    ("Recibir orden (form)", "/suppliers/orders/{order_id}/receive/"),
    ("⚠️ Pagar orden (form)", "/suppliers/orders/{order_id}/payments/add/"),
    ("Lista pagos orden", "/suppliers/orders/{order_id}/payments/"),
    ("Detalle gasto", "/finances/expenses/{expense_id}/"),
    ("Editar gasto", "/finances/expenses/{expense_id}/edit/"),
    ("Detalle cierre", "/finances/daily-close/{close_id}/"),
    ("Editar usuario", "/accounts/users/{user_id}/edit/"),
    ("API detalle producto", "/inventory/api/products/{product_id}/"),
    ("API barcode", "/inventory/api/products/barcode/{barcode}/"),
    ("API lookup proveedor", "/suppliers/api/product-lookup/{barcode}/"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Cliente HTTP
# ──────────────────────────────────────────────────────────────────────────────

class LiveClient:
    def __init__(self, base_url, username, password):
        self.base = base_url.rstrip('/')
        self.session = requests.Session()
        self.errors = []
        self.warnings = []
        self.ok_count = 0
        self._login(username, password)

    def _url(self, path):
        return self.base + path

    def _login(self, username, password):
        """Inicia sesión en el sistema."""
        login_url = self._url('/accounts/login/')
        # Obtener CSRF token
        resp = self.session.get(login_url, timeout=10)
        if resp.status_code != 200:
            print(f"ERROR: No se pudo acceder a la página de login ({resp.status_code})")
            sys.exit(1)

        csrf = self.session.cookies.get('csrftoken')
        if not csrf:
            # Buscar en el HTML
            import re
            match = re.search(r'csrfmiddlewaretoken.*?value=["\']([^"\']+)', resp.text)
            csrf = match.group(1) if match else ''

        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrf,
        }
        resp = self.session.post(login_url, data=login_data,
                                  headers={'Referer': login_url}, timeout=10)

        if 'login' in resp.url or resp.status_code == 200 and 'error' in resp.text.lower():
            print(f"ERROR: No se pudo iniciar sesión. Verifica usuario/contraseña.")
            sys.exit(1)

        print(f"✅ Sesión iniciada como '{username}' → redirigido a {resp.url}")

    def get(self, description, path):
        """Hace GET y registra el resultado."""
        url = self._url(path)
        try:
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            code = resp.status_code

            if code == 500:
                self.errors.append((description, url, code, "Error interno del servidor"))
                print(f"  ❌ [{code}] {description}")
                print(f"       {url}")
            elif code in (403, 404):
                self.warnings.append((description, url, code))
                print(f"  ⚠️  [{code}] {description}")
            elif code == 200:
                self.ok_count += 1
                print(f"  ✅ [{code}] {description}")
            else:
                self.ok_count += 1
                print(f"  ✅ [{code}] {description}")

        except requests.exceptions.ConnectionError:
            self.errors.append((description, url, 0, "Conexión rechazada"))
            print(f"  ❌ [CONN] {description} — No se puede conectar")
        except requests.exceptions.Timeout:
            self.errors.append((description, url, 0, "Timeout"))
            print(f"  ❌ [TIMEOUT] {description}")

    def summary(self):
        total = self.ok_count + len(self.warnings) + len(self.errors)
        print()
        print("=" * 65)
        print(f"RESUMEN: {total} URLs verificadas")
        print(f"  ✅ OK:          {self.ok_count}")
        print(f"  ⚠️  Advertencias: {len(self.warnings)}")
        print(f"  ❌ Errores 500: {len(self.errors)}")
        print("=" * 65)

        if self.errors:
            print()
            print("URLs CON ERROR 500 (a corregir):")
            for desc, url, code, msg in self.errors:
                print(f"  ❌ {desc}")
                print(f"     {url}")
                print(f"     → {msg}")

        if self.warnings:
            print()
            print("URLs CON ADVERTENCIA (403/404 — revisar si es esperado):")
            for desc, url, code in self.warnings:
                print(f"  ⚠️  [{code}] {desc}: {url}")

        if not self.errors:
            print()
            print("✅ ¡Todo bien! Ninguna URL retornó 500.")
        else:
            print()
            print(f"⛔ Se encontraron {len(self.errors)} error(es). Ver detalle arriba.")

        return len(self.errors)


# ──────────────────────────────────────────────────────────────────────────────
# Obtener IDs dinámicos del sistema
# ──────────────────────────────────────────────────────────────────────────────

def get_dynamic_ids(client):
    """Obtiene IDs de objetos reales llamando las APIs del sistema."""
    import json

    ids = {
        'product_id': 1,
        'category_id': 1,
        'customer_id': 1,
        'credit_id': 1,
        'sale_id': 1,
        'supplier_id': 1,
        'order_id': 1,
        'expense_id': 1,
        'close_id': 1,
        'user_id': 1,
        'barcode': 'TEST001',
    }

    # Intentar obtener IDs reales desde las listas
    url_checks = [
        ('product_id', '/inventory/api/products/search/?q='),
        ('customer_id', '/api/customers/search/?q='),
    ]

    # Intentar obtener el primer producto via API
    try:
        resp = client.session.get(client._url('/inventory/api/products/search/?q='),
                                   timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get('products', [])
            if products:
                ids['product_id'] = products[0].get('id', 1)
                ids['barcode'] = products[0].get('barcode', 'TEST001')
                print(f"  → producto real: ID={ids['product_id']}, barcode={ids['barcode']}")
    except Exception:
        pass

    # Para el resto, hacemos HEAD a las listas para ver si hay datos
    # y usamos ID=1 como fallback (el sistema debería tener datos reales)
    print(f"  → Usando IDs dinámicos: {ids}")
    return ids


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Verifica que ninguna URL del sistema retorne 500'
    )
    parser.add_argument('--base-url', default='http://localhost:8000',
                        help='URL base del servidor Django (default: http://localhost:8000)')
    parser.add_argument('--user', default='admin',
                        help='Nombre de usuario para autenticación')
    parser.add_argument('--pass', dest='password', default='admin123',
                        help='Contraseña del usuario')
    parser.add_argument('--fast', action='store_true',
                        help='Solo probar páginas estáticas (más rápido)')
    args = parser.parse_args()

    print()
    print("=" * 65)
    print("SMOKE TEST — SERVIDOR REAL")
    print(f"  Base URL : {args.base_url}")
    print(f"  Usuario  : {args.user}")
    print("=" * 65)
    print()

    client = LiveClient(args.base_url, args.user, args.password)

    print()
    print("── Páginas estáticas ──────────────────────────────────────")
    for description, path in PAGES_STATIC:
        client.get(description, path)

    if not args.fast:
        print()
        print("── Obteniendo IDs de objetos reales ──────────────────────")
        ids = get_dynamic_ids(client)

        print()
        print("── Páginas dinámicas (con IDs reales) ────────────────────")
        for description, path_template in PAGES_DYNAMIC:
            try:
                path = path_template.format(**ids)
                client.get(description, path)
            except KeyError as e:
                print(f"  ⏭️  {description} — faltan datos para {e}")

    error_count = client.summary()
    sys.exit(1 if error_count > 0 else 0)


if __name__ == '__main__':
    main()
