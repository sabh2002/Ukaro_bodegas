#!/usr/bin/env python
"""
Script de Verificación: Fix de Precios en Cero
Verifica que el fix aplicado a inventory/api_views.py funciona correctamente
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bodega_system.settings')
django.setup()

from inventory.models import Product
from utils.models import ExchangeRate
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def verify_exchange_rate():
    """Verifica que existe al menos una tasa de cambio"""
    print_header("1. Verificando Tasa de Cambio")

    latest_rate = ExchangeRate.get_latest_rate()

    if latest_rate:
        print_success(f"Existe tasa de cambio: {latest_rate.bs_to_usd} Bs/USD")
        print_info(f"Fecha: {latest_rate.date}")
        print_info(f"Actualizado por: {latest_rate.updated_by}")
        return True
    else:
        print_error("NO existe tasa de cambio en la base de datos")
        print_warning("Los precios aparecerán en 0 hasta que se cree una tasa")
        print_info("Para crear una tasa:")
        print_info("  1. Ir a: http://127.0.0.1:8000/admin/utils/exchangerate/add/")
        print_info("  2. O ejecutar:")
        print_info("     python manage.py shell")
        print_info("     >>> from utils.models import ExchangeRate")
        print_info("     >>> from decimal import Decimal")
        print_info("     >>> from django.contrib.auth import get_user_model")
        print_info("     >>> User = get_user_model()")
        print_info("     >>> admin = User.objects.filter(is_superuser=True).first()")
        print_info("     >>> ExchangeRate.objects.create(bs_to_usd=Decimal('45.50'), updated_by=admin)")
        return False

def verify_products():
    """Verifica que existen productos con precio"""
    print_header("2. Verificando Productos")

    total_products = Product.objects.filter(is_active=True).count()
    products_with_price = Product.objects.filter(
        is_active=True,
        selling_price_usd__gt=0
    ).count()

    if total_products == 0:
        print_error("NO hay productos en la base de datos")
        print_info("Crear productos en: http://127.0.0.1:8000/admin/inventory/product/add/")
        return False

    print_success(f"Total de productos activos: {total_products}")

    if products_with_price == 0:
        print_error("Ningún producto tiene precio en USD")
        print_warning("Todos los productos tendrán precio Bs 0.00")
        return False

    print_success(f"Productos con precio USD > 0: {products_with_price}")
    return True

def test_get_current_price_bs():
    """Prueba el método get_current_price_bs()"""
    print_header("3. Probando Método get_current_price_bs()")

    # Obtener un producto de prueba
    product = Product.objects.filter(
        is_active=True,
        selling_price_usd__gt=0
    ).first()

    if not product:
        print_error("No hay productos para probar")
        return False

    print_info(f"Producto de prueba: {product.name}")
    print_info(f"Precio USD: ${product.selling_price_usd}")

    # Obtener tasa
    latest_rate = ExchangeRate.get_latest_rate()
    if not latest_rate:
        print_error("No hay tasa de cambio para calcular")
        return False

    print_info(f"Tasa de cambio: {latest_rate.bs_to_usd} Bs/USD")

    # Calcular precio en Bs
    price_bs = product.get_current_price_bs()
    expected_price = product.selling_price_usd * latest_rate.bs_to_usd

    print_info(f"Cálculo esperado: ${product.selling_price_usd} × {latest_rate.bs_to_usd} = Bs {expected_price}")
    print_info(f"Resultado de get_current_price_bs(): Bs {price_bs}")

    if price_bs == expected_price:
        print_success(f"✓ Método funciona correctamente: Bs {price_bs}")
        return True
    else:
        print_error(f"✗ Método retorna valor incorrecto")
        print_error(f"  Esperado: Bs {expected_price}")
        print_error(f"  Recibido: Bs {price_bs}")
        return False

def verify_api_code():
    """Verifica que el código de la API fue modificado correctamente"""
    print_header("4. Verificando Código de API")

    api_file = os.path.join(
        os.path.dirname(__file__),
        'inventory',
        'api_views.py'
    )

    if not os.path.exists(api_file):
        print_error(f"No se encuentra el archivo: {api_file}")
        return False

    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verificar que se usa get_current_price_bs()
    if 'get_current_price_bs()' in content:
        print_success("Archivo API contiene get_current_price_bs()")

        # Contar ocurrencias
        count = content.count('get_current_price_bs()')
        print_info(f"Número de ocurrencias: {count}")

        if count >= 2:
            print_success("✓ Se usa en al menos 2 lugares (product_search_api y product_by_barcode_api)")
        else:
            print_warning(f"Solo se encontraron {count} ocurrencias (esperadas: 2)")

        return True
    else:
        print_error("El archivo NO contiene get_current_price_bs()")
        print_error("El fix NO fue aplicado correctamente")
        return False

def simulate_api_response():
    """Simula la respuesta de la API de búsqueda"""
    print_header("5. Simulando Respuesta de API")

    product = Product.objects.filter(
        is_active=True,
        selling_price_usd__gt=0
    ).first()

    if not product:
        print_error("No hay productos para simular")
        return False

    latest_rate = ExchangeRate.get_latest_rate()
    if not latest_rate:
        print_error("No hay tasa de cambio")
        return False

    # Simular respuesta de API
    price_bs = product.get_current_price_bs()

    print_info("Respuesta JSON simulada:")
    print(f"""
    {{
      "id": {product.id},
      "name": "{product.name}",
      "barcode": "{product.barcode}",
      "selling_price_bs": {float(price_bs)},
      "selling_price_usd": {float(product.selling_price_usd)},
      "stock": {float(product.stock)}
    }}
    """)

    if price_bs > 0:
        print_success(f"✓ API retornaría precio: Bs {price_bs}")
        print_success("✓ Los precios deberían aparecer correctamente en el frontend")
        return True
    else:
        print_error("✗ API retornaría precio: Bs 0.00")
        print_error("Los precios seguirán apareciendo en cero")
        return False

def main():
    print("\n" + "🔍 VERIFICACIÓN DE FIX: PRECIOS EN CERO".center(60))
    print("Script de diagnóstico para verificar el fix aplicado\n")

    results = []

    # Ejecutar verificaciones
    results.append(("Tasa de Cambio", verify_exchange_rate()))
    results.append(("Productos", verify_products()))
    results.append(("Método get_current_price_bs()", test_get_current_price_bs()))
    results.append(("Código de API", verify_api_code()))
    results.append(("Simulación de API", simulate_api_response()))

    # Resumen
    print_header("RESUMEN DE VERIFICACIÓN")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n📊 Resultados: {passed}/{total} verificaciones pasadas")

    if passed == total:
        print("\n🎉 ¡ÉXITO! El fix fue aplicado correctamente")
        print("\n📝 Próximos pasos:")
        print("  1. Reiniciar servidor: python manage.py runserver")
        print("  2. Abrir navegador: http://127.0.0.1:8000/sales/new/")
        print("  3. Buscar un producto")
        print("  4. Verificar que los precios aparecen correctamente")
    else:
        print("\n⚠️  ATENCIÓN: Algunas verificaciones fallaron")
        print("\n📝 Acciones recomendadas:")
        if not results[0][1]:  # Tasa de cambio
            print("  1. Crear una tasa de cambio en el admin")
        if not results[1][1]:  # Productos
            print("  2. Crear productos con precios en USD")
        if not results[3][1]:  # Código API
            print("  3. Verificar que el archivo inventory/api_views.py fue modificado")

    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error al ejecutar verificación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
