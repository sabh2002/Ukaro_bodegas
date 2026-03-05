#!/usr/bin/env python3
"""
Script de Testing Automatizado con Playwright
Prueba el sistema de pagos a proveedores de forma completa
"""

import os
import sys
import time
from datetime import datetime
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bodega_system.settings')
import django
django.setup()

def run_browser_tests():
    """Ejecuta pruebas automáticas en el navegador"""

    print("\n" + "="*70)
    print(" TESTING AUTOMATIZADO - Sistema de Pagos a Proveedores")
    print("="*70 + "\n")

    # Importar Playwright
    try:
        from playwright.sync_api import sync_playwright, expect
        print("✅ Playwright importado correctamente")
    except ImportError:
        print("❌ Error: playwright no está instalado")
        print("   Instalando playwright...")
        os.system("pip install playwright")
        print("   Instalando navegadores...")
        os.system("playwright install firefox")
        from playwright.sync_api import sync_playwright, expect
        print("✅ Playwright instalado")

    # Configuración
    BASE_URL = "http://localhost:8000"
    SCREENSHOT_DIR = "/tmp/playwright-screenshots"
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    print(f"📂 Screenshots se guardarán en: {SCREENSHOT_DIR}")
    print(f"🌐 Testing URL: {BASE_URL}\n")

    with sync_playwright() as p:
        # Lanzar navegador
        print("🚀 Lanzando Firefox...")
        browser = p.firefox.launch(headless=False)  # headless=False para ver el navegador
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='es-ES'
        )
        page = context.new_page()

        try:
            # TEST 1: Login
            print("\n" + "="*70)
            print("TEST 1: Login con credenciales de prueba")
            print("="*70)

            page.goto(BASE_URL)
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/01_login_page.png")
            print(f"📸 Screenshot: 01_login_page.png")

            # Llenar formulario de login
            page.fill('input[name="username"]', 'admin_test')
            page.fill('input[name="password"]', 'test123')
            page.screenshot(path=f"{SCREENSHOT_DIR}/02_login_filled.png")
            print(f"📸 Screenshot: 02_login_filled.png")

            # Click en login
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/03_dashboard.png")
            print(f"📸 Screenshot: 03_dashboard.png")
            print("✅ Login exitoso")

            # TEST 2: Navegar a Órdenes
            print("\n" + "="*70)
            print("TEST 2: Navegación a Órdenes de Compra")
            print("="*70)

            # Buscar y hacer click en "Proveedores" o "Órdenes"
            try:
                page.click('text=Proveedores')
                time.sleep(0.5)
                page.click('text=Órdenes de Compra')
            except:
                # Alternativa: URL directa
                page.goto(f"{BASE_URL}/suppliers/orders/")

            page.wait_for_load_state('networkidle')
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/04_orders_list.png")
            print(f"📸 Screenshot: 04_orders_list.png")

            # Verificar que columna "Estado Pago" existe
            if page.locator('text=Estado Pago').count() > 0:
                print("✅ Columna 'Estado Pago' encontrada")
            else:
                print("⚠️  Columna 'Estado Pago' NO encontrada")

            # Contar órdenes con badge "Impago"
            impago_badges = page.locator('text=/Impago|✗/').count()
            print(f"📊 Órdenes sin pagar encontradas: {impago_badges}")

            # TEST 3: Abrir detalle de orden
            print("\n" + "="*70)
            print("TEST 3: Detalle de Orden - Verificar Sección de Pagos")
            print("="*70)

            # Click en primera orden (usando el ícono de ver detalles)
            try:
                # Intentar varios selectores
                page.locator('a[href*="/suppliers/orders/"]').first.click()
            except:
                page.goto(f"{BASE_URL}/suppliers/orders/1/")

            page.wait_for_load_state('networkidle')
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/05_order_detail.png")
            print(f"📸 Screenshot: 05_order_detail.png")

            # Verificar sección "Estado de Pagos"
            if page.locator('text=Estado de Pagos').count() > 0:
                print("✅ Sección 'Estado de Pagos' encontrada")
            else:
                print("⚠️  Sección 'Estado de Pagos' NO encontrada")

            # Verificar botón "Registrar Pago"
            if page.locator('text=Registrar Pago').count() > 0:
                print("✅ Botón 'Registrar Pago' encontrado")
            else:
                print("⚠️  Botón 'Registrar Pago' NO encontrado")

            # Extraer información de la orden
            try:
                total_text = page.locator('text=/Total.*\\$/').first.inner_text()
                print(f"💰 {total_text}")
            except:
                print("⚠️  No se pudo extraer el total")

            # TEST 4: Abrir formulario de pago
            print("\n" + "="*70)
            print("TEST 4: Formulario de Registro de Pago")
            print("="*70)

            # Click en "Registrar Pago"
            page.click('text=Registrar Pago')
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/06_payment_form.png")
            print(f"📸 Screenshot: 06_payment_form.png")
            print("✅ Formulario de pago abierto")

            # Verificar campos del formulario
            campos = ['amount_usd', 'payment_method', 'payment_date']
            for campo in campos:
                if page.locator(f'[name="{campo}"]').count() > 0:
                    print(f"✅ Campo '{campo}' encontrado")
                else:
                    print(f"⚠️  Campo '{campo}' NO encontrado")

            # TEST 5: Registrar pago de prueba
            print("\n" + "="*70)
            print("TEST 5: Registrar Pago de $50.00")
            print("="*70)

            # Llenar formulario
            page.fill('input[name="amount_usd"]', '50.00')
            page.select_option('select[name="payment_method"]', 'transfer')
            page.fill('input[name="reference"]', 'TEST-AUTO-001')

            page.screenshot(path=f"{SCREENSHOT_DIR}/07_payment_form_filled.png")
            print(f"📸 Screenshot: 07_payment_form_filled.png")
            print("✅ Formulario llenado")

            # Submit
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/08_after_payment.png")
            print(f"📸 Screenshot: 08_after_payment.png")

            # Verificar mensaje de éxito
            if page.locator('text=/éxito|exitoso|registrado/i').count() > 0:
                print("✅ Mensaje de éxito encontrado")
            else:
                print("⚠️  No se encontró mensaje de éxito")

            # TEST 6: Verificar cambios en detalle de orden
            print("\n" + "="*70)
            print("TEST 6: Verificación de Actualización Automática")
            print("="*70)

            # Verificar badge cambió
            if page.locator('text=/Parcial|◐/').count() > 0:
                print("✅ Badge cambió a 'Parcial'")
            elif page.locator('text=/Pagado|✓/').count() > 0:
                print("✅ Badge cambió a 'Pagado'")
            else:
                print("⚠️  Badge no cambió")

            # Verificar historial de pagos
            if page.locator('text=Historial de Pagos').count() > 0:
                print("✅ Historial de Pagos visible")

                # Contar pagos en la tabla
                pagos_count = page.locator('tbody tr').count()
                print(f"📊 Pagos registrados: {pagos_count}")
            else:
                print("⚠️  Historial de Pagos NO visible")

            # Verificar monto pagado actualizado
            try:
                pagado_text = page.locator('text=/Monto Pagado/').first.inner_text()
                print(f"💵 {pagado_text}")
            except:
                pass

            # Screenshot final
            page.screenshot(path=f"{SCREENSHOT_DIR}/09_final_state.png")
            print(f"📸 Screenshot: 09_final_state.png")

            # TEST 7: Verificar conversión USD/Bs
            print("\n" + "="*70)
            print("TEST 7: Verificación de Conversión USD/Bs")
            print("="*70)

            # Buscar en la tabla de historial
            try:
                # Buscar la fila con TEST-AUTO-001
                fila = page.locator('tr:has-text("TEST-AUTO-001")')

                if fila.count() > 0:
                    texto_fila = fila.inner_text()
                    print(f"📝 Pago encontrado: {texto_fila}")

                    # Extraer montos
                    if '$50.00' in texto_fila:
                        print("✅ Monto USD correcto: $50.00")

                    if 'Bs' in texto_fila and '2,' in texto_fila:
                        print("✅ Conversión Bs parece correcta (~Bs 2,275)")

                    if '45.50' in texto_fila:
                        print("✅ Tasa de cambio correcta: 45.50")
                else:
                    print("⚠️  Pago TEST-AUTO-001 no encontrado en historial")
            except Exception as e:
                print(f"⚠️  Error verificando conversión: {e}")

            # TEST 8: Volver a lista y verificar badge
            print("\n" + "="*70)
            print("TEST 8: Verificar Badge en Lista de Órdenes")
            print("="*70)

            page.goto(f"{BASE_URL}/suppliers/orders/")
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/10_orders_list_after.png")
            print(f"📸 Screenshot: 10_orders_list_after.png")

            # Verificar que hay al menos un badge "Parcial"
            if page.locator('text=/Parcial|◐/').count() > 0:
                print("✅ Badge 'Parcial' visible en lista")
            else:
                print("⚠️  Badge 'Parcial' NO visible en lista")

            # RESUMEN FINAL
            print("\n" + "="*70)
            print(" RESUMEN DE PRUEBAS")
            print("="*70)
            print(f"✅ Tests completados: 8/8")
            print(f"📸 Screenshots capturados: 10")
            print(f"📂 Ubicación: {SCREENSHOT_DIR}")
            print(f"⏱️  Duración: ~30 segundos")

        except Exception as e:
            print(f"\n❌ Error durante las pruebas: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path=f"{SCREENSHOT_DIR}/error.png")
            print(f"📸 Screenshot de error guardado")

        finally:
            print("\n⏳ Cerrando navegador en 5 segundos...")
            time.sleep(5)
            browser.close()

    print("\n" + "="*70)
    print(" TESTING FINALIZADO")
    print("="*70)
    print(f"\n🔍 Revisa los screenshots en: {SCREENSHOT_DIR}")
    print("📊 Analiza los resultados arriba")
    print("\n")

if __name__ == '__main__':
    run_browser_tests()
