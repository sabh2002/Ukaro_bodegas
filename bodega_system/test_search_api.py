#!/usr/bin/env python
"""
Script de diagnóstico para verificar las APIs de búsqueda de productos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bodega_system.settings')
django.setup()

from django.urls import reverse, resolve
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from inventory.api_views import product_search_api, product_by_barcode_api
from utils.api_views import product_by_barcode
from inventory.models import Product

User = get_user_model()

def test_urls():
    """Verificar que las URLs estén configuradas correctamente"""
    print("=" * 60)
    print("VERIFICACIÓN DE URLS")
    print("=" * 60)

    urls_to_test = [
        '/api/products/search/',
        '/api/products/barcode/123456/',
        '/api/products/1/',
        '/api/customers/search/',
        '/api/combos/search/',
    ]

    for url in urls_to_test:
        try:
            match = resolve(url)
            print(f"✅ {url}")
            print(f"   → View: {match.view_name}")
            print(f"   → Function: {match.func.__name__}")
        except Exception as e:
            print(f"❌ {url}")
            print(f"   → Error: {e}")
        print()

def test_product_search():
    """Verificar que la búsqueda de productos funcione"""
    print("=" * 60)
    print("VERIFICACIÓN DE BÚSQUEDA DE PRODUCTOS")
    print("=" * 60)

    # Crear un usuario de prueba
    user = User.objects.first()
    if not user:
        print("❌ No hay usuarios en el sistema")
        return

    # Crear una petición simulada
    factory = RequestFactory()
    request = factory.get('/api/products/search/', {'q': 'test', 'limit': 10})
    request.user = user

    try:
        response = product_search_api(request)
        print(f"✅ API de búsqueda responde")
        print(f"   → Status: {response.status_code}")
        print(f"   → Content-Type: {response.get('Content-Type')}")

        import json
        data = json.loads(response.content)
        print(f"   → Productos encontrados: {data.get('count', 0)}")

    except Exception as e:
        print(f"❌ Error en búsqueda")
        print(f"   → {e}")

def test_product_by_barcode():
    """Verificar que la búsqueda por barcode funcione"""
    print("=" * 60)
    print("VERIFICACIÓN DE BÚSQUEDA POR CÓDIGO DE BARRAS")
    print("=" * 60)

    # Buscar un producto real
    product = Product.objects.filter(is_active=True).first()

    if not product:
        print("❌ No hay productos activos en el sistema")
        return

    print(f"Producto de prueba: {product.name} ({product.barcode})")

    user = User.objects.first()
    factory = RequestFactory()

    # Probar la API de utils
    request = factory.get(f'/api/products/barcode/{product.barcode}/')
    request.user = user

    try:
        response = product_by_barcode(request, product.barcode)
        print(f"✅ utils.api_views.product_by_barcode responde")
        print(f"   → Status: {response.status_code}")

        import json
        data = json.loads(response.content)
        print(f"   → Producto: {data.get('name')}")
        print(f"   → Precio BS: {data.get('selling_price_bs')}")

    except Exception as e:
        print(f"❌ Error en búsqueda por barcode (utils)")
        print(f"   → {e}")

    # Probar la API de inventory
    try:
        response = product_by_barcode_api(request, product.barcode)
        print(f"✅ inventory.api_views.product_by_barcode_api responde")
        print(f"   → Status: {response.status_code}")

    except Exception as e:
        print(f"❌ Error en búsqueda por barcode (inventory)")
        print(f"   → {e}")

def test_products_exist():
    """Verificar que haya productos en el sistema"""
    print("=" * 60)
    print("VERIFICACIÓN DE DATOS")
    print("=" * 60)

    total = Product.objects.count()
    active = Product.objects.filter(is_active=True).count()
    with_stock = Product.objects.filter(is_active=True, stock__gt=0).count()

    print(f"Total de productos: {total}")
    print(f"Productos activos: {active}")
    print(f"Productos con stock: {with_stock}")
    print()

    if active > 0:
        print("Primeros 5 productos activos:")
        for p in Product.objects.filter(is_active=True)[:5]:
            print(f"  - {p.name} ({p.barcode}) - Stock: {p.stock}")
    else:
        print("❌ No hay productos activos")

if __name__ == '__main__':
    test_products_exist()
    print()
    test_urls()
    print()
    test_product_search()
    print()
    test_product_by_barcode()
    print()
    print("=" * 60)
    print("VERIFICACIÓN COMPLETA")
    print("=" * 60)
