#!/usr/bin/env python3
"""
Script para crear datos de prueba completos para el sistema de bodega
Incluye: usuarios, tasa de cambio, categorías, productos, proveedores, clientes y órdenes
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bodega_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from utils.models import ExchangeRate
from inventory.models import Category, Product
from suppliers.models import Supplier, SupplierOrder, SupplierOrderItem
from customers.models import Customer

User = get_user_model()

def create_test_data():
    print("\n" + "="*60)
    print(" CREANDO DATOS DE PRUEBA - Sistema Ukaro Bodegas")
    print("="*60 + "\n")

    # 1. USUARIOS
    print("📋 Creando usuarios...")
    admin, created = User.objects.get_or_create(
        username='admin_test',
        defaults={
            'email': 'admin@test.com',
            'is_admin': True,
            'is_superuser': True,
            'is_staff': True,
            'first_name': 'Admin',
            'last_name': 'Sistema'
        }
    )
    if created:
        admin.set_password('test123')
        admin.save()
        print(f"  ✅ Admin creado: {admin.username} / test123")
    else:
        print(f"  ℹ️  Admin ya existe: {admin.username}")

    empleado, created = User.objects.get_or_create(
        username='vendedor1',
        defaults={
            'email': 'vendedor1@test.com',
            'is_admin': False,
            'is_superuser': False,
            'is_staff': False,
            'first_name': 'Juan',
            'last_name': 'Vendedor'
        }
    )
    if created:
        empleado.set_password('test123')
        empleado.save()
        print(f"  ✅ Empleado creado: {empleado.username} / test123")
    else:
        print(f"  ℹ️  Empleado ya existe: {empleado.username}")

    # 2. TASA DE CAMBIO
    print("\n💱 Creando tasa de cambio...")
    rate, created = ExchangeRate.objects.get_or_create(
        date=timezone.now().date(),
        defaults={
            'bs_to_usd': Decimal('45.50'),
            'updated_by': admin
        }
    )
    if created:
        print(f"  ✅ Tasa creada: {rate.bs_to_usd} Bs/USD para {rate.date}")
    else:
        print(f"  ℹ️  Tasa ya existe: {rate.bs_to_usd} Bs/USD")

    # 3. CATEGORÍAS
    print("\n📁 Creando categorías...")
    categorias_data = [
        'Alimentos',
        'Bebidas',
        'Limpieza',
        'Higiene Personal',
        'Snacks'
    ]

    categorias = {}
    for nombre in categorias_data:
        cat, created = Category.objects.get_or_create(name=nombre)
        categorias[nombre] = cat
        if created:
            print(f"  ✅ Categoría creada: {nombre}")
        else:
            print(f"  ℹ️  Categoría ya existe: {nombre}")

    # 4. PRODUCTOS
    print("\n📦 Creando productos...")
    productos_data = [
        # (nombre, barcode, categoría, precio_compra, precio_venta, stock)
        ('Arroz Diana 1kg', '7501234567890', 'Alimentos', '2.50', '3.50', 100),
        ('Aceite Goya 1L', '7501234567891', 'Alimentos', '3.00', '4.50', 80),
        ('Azúcar Blanca 1kg', '7501234567892', 'Alimentos', '1.50', '2.00', 150),
        ('Pasta La Muñeca 500g', '7501234567893', 'Alimentos', '1.20', '1.80', 200),
        ('Harina PAN 1kg', '7501234567894', 'Alimentos', '2.00', '3.00', 120),
        ('Coca Cola 2L', '7501234567895', 'Bebidas', '1.80', '2.50', 50),
        ('Agua Mineral 1.5L', '7501234567896', 'Bebidas', '0.50', '0.80', 300),
        ('Jugo Hit 1L', '7501234567897', 'Bebidas', '1.20', '1.80', 60),
        ('Detergente Ace 1kg', '7501234567898', 'Limpieza', '3.50', '5.00', 40),
        ('Cloro 1L', '7501234567899', 'Limpieza', '1.00', '1.50', 80),
        ('Jabón de Baño', '7501234567900', 'Higiene Personal', '0.80', '1.20', 150),
        ('Pasta Dental', '7501234567901', 'Higiene Personal', '2.00', '3.00', 100),
        ('Papel Higiénico 4un', '7501234567902', 'Higiene Personal', '2.50', '3.50', 60),
        ('Doritos 150g', '7501234567903', 'Snacks', '1.50', '2.20', 80),
        ('Pepitos 40g', '7501234567904', 'Snacks', '0.50', '0.80', 200),
    ]

    productos = {}
    for nombre, barcode, cat_nombre, p_compra, p_venta, stock in productos_data:
        prod, created = Product.objects.get_or_create(
            barcode=barcode,
            defaults={
                'name': nombre,
                'category': categorias[cat_nombre],
                'purchase_price_usd': Decimal(p_compra),
                'purchase_price_bs': Decimal(p_compra) * rate.bs_to_usd,
                'selling_price_usd': Decimal(p_venta),
                'selling_price_bs': Decimal(p_venta) * rate.bs_to_usd,
                'stock': stock,
                'min_stock': 10
            }
        )
        productos[nombre] = prod
        if created:
            print(f"  ✅ Producto creado: {nombre} (${p_venta})")
        else:
            print(f"  ℹ️  Producto ya existe: {nombre}")

    # 5. PROVEEDORES
    print("\n🏢 Creando proveedores...")
    proveedores_data = [
        ('Distribuidora Central C.A.', 'Carlos Rodríguez', '0414-1234567', 'carlos@distribuidora.com'),
        ('Alimentos del Valle', 'María González', '0424-9876543', 'maria@alimentosdelvalle.com'),
        ('Productos La Montaña', 'José Pérez', '0412-5555555', 'jose@lamontana.com'),
    ]

    proveedores = {}
    for nombre, contacto, telefono, email in proveedores_data:
        prov, created = Supplier.objects.get_or_create(
            name=nombre,
            defaults={
                'contact_person': contacto,
                'phone': telefono,
                'email': email,
                'is_active': True
            }
        )
        proveedores[nombre] = prov
        if created:
            print(f"  ✅ Proveedor creado: {nombre}")
        else:
            print(f"  ℹ️  Proveedor ya existe: {nombre}")

    # 6. CLIENTES
    print("\n👥 Creando clientes...")
    clientes_data = [
        ('Roberto Martínez', '0414-1111111', '500.00'),
        ('Ana Silva', '0424-2222222', '300.00'),
        ('Luis Hernández', '0412-3333333', '1000.00'),
    ]

    clientes = {}
    for nombre, telefono, limite in clientes_data:
        cliente, created = Customer.objects.get_or_create(
            phone=telefono,
            defaults={
                'name': nombre,
                'credit_limit_usd': Decimal(limite),
                'is_active': True
            }
        )
        clientes[nombre] = cliente
        if created:
            print(f"  ✅ Cliente creado: {nombre} (Límite: ${limite})")
        else:
            print(f"  ℹ️  Cliente ya existe: {nombre}")

    # 7. ÓRDENES DE COMPRA
    print("\n📝 Creando órdenes de compra...")

    # Orden 1: Pendiente, sin pagar
    orden1, created = SupplierOrder.objects.get_or_create(
        id=1,
        defaults={
            'supplier': proveedores['Distribuidora Central C.A.'],
            'order_date': timezone.now() - timedelta(days=5),
            'status': 'pending',
            'notes': 'Orden de prueba pendiente',
            'exchange_rate_used': rate.bs_to_usd,
            'created_by': admin,
            'total_usd': Decimal('0'),
            'total_bs': Decimal('0')
        }
    )

    if created:
        # Items de la orden 1
        items_orden1 = [
            (productos['Arroz Diana 1kg'], 50, Decimal('2.50')),
            (productos['Aceite Goya 1L'], 30, Decimal('3.00')),
            (productos['Azúcar Blanca 1kg'], 40, Decimal('1.50')),
        ]

        total_usd = Decimal('0')
        total_bs = Decimal('0')

        for producto, cantidad, precio in items_orden1:
            item = SupplierOrderItem.objects.create(
                order=orden1,
                product=producto,
                quantity=cantidad,
                price_usd=precio,
                price_bs=precio * rate.bs_to_usd
            )
            total_usd += item.subtotal_usd
            total_bs += item.subtotal_bs

        orden1.total_usd = total_usd
        orden1.total_bs = total_bs
        orden1.save()

        print(f"  ✅ Orden #1 creada: ${total_usd} USD (Pendiente, Sin Pagar)")
    else:
        print(f"  ℹ️  Orden #1 ya existe")

    # Orden 2: Recibida, con pago parcial
    orden2, created = SupplierOrder.objects.get_or_create(
        id=2,
        defaults={
            'supplier': proveedores['Alimentos del Valle'],
            'order_date': timezone.now() - timedelta(days=3),
            'status': 'received',
            'received_date': timezone.now() - timedelta(days=2),
            'notes': 'Orden recibida, pago parcial',
            'exchange_rate_used': rate.bs_to_usd,
            'created_by': admin,
            'total_usd': Decimal('0'),
            'total_bs': Decimal('0')
        }
    )

    if created:
        # Items de la orden 2
        items_orden2 = [
            (productos['Coca Cola 2L'], 30, Decimal('1.80')),
            (productos['Agua Mineral 1.5L'], 100, Decimal('0.50')),
            (productos['Jugo Hit 1L'], 40, Decimal('1.20')),
        ]

        total_usd = Decimal('0')
        total_bs = Decimal('0')

        for producto, cantidad, precio in items_orden2:
            item = SupplierOrderItem.objects.create(
                order=orden2,
                product=producto,
                quantity=cantidad,
                price_usd=precio,
                price_bs=precio * rate.bs_to_usd
            )
            total_usd += item.subtotal_usd
            total_bs += item.subtotal_bs

        orden2.total_usd = total_usd
        orden2.total_bs = total_bs
        orden2.save()

        print(f"  ✅ Orden #2 creada: ${total_usd} USD (Recibida, Para pago parcial)")
    else:
        print(f"  ℹ️  Orden #2 ya existe")

    # Orden 3: Recibida, sin pagar
    orden3, created = SupplierOrder.objects.get_or_create(
        id=3,
        defaults={
            'supplier': proveedores['Productos La Montaña'],
            'order_date': timezone.now() - timedelta(days=7),
            'status': 'received',
            'received_date': timezone.now() - timedelta(days=6),
            'notes': 'Orden pequeña de prueba',
            'exchange_rate_used': rate.bs_to_usd,
            'created_by': admin,
            'total_usd': Decimal('0'),
            'total_bs': Decimal('0')
        }
    )

    if created:
        # Items de la orden 3
        items_orden3 = [
            (productos['Detergente Ace 1kg'], 20, Decimal('3.50')),
            (productos['Cloro 1L'], 30, Decimal('1.00')),
        ]

        total_usd = Decimal('0')
        total_bs = Decimal('0')

        for producto, cantidad, precio in items_orden3:
            item = SupplierOrderItem.objects.create(
                order=orden3,
                product=producto,
                quantity=cantidad,
                price_usd=precio,
                price_bs=precio * rate.bs_to_usd
            )
            total_usd += item.subtotal_usd
            total_bs += item.subtotal_bs

        orden3.total_usd = total_usd
        orden3.total_bs = total_bs
        orden3.save()

        print(f"  ✅ Orden #3 creada: ${total_usd} USD (Recibida, Sin Pagar)")
    else:
        print(f"  ℹ️  Orden #3 ya existe")

    # RESUMEN
    print("\n" + "="*60)
    print(" RESUMEN DE DATOS CREADOS")
    print("="*60)
    print(f"  👤 Usuarios: {User.objects.count()}")
    print(f"  💱 Tasas de cambio: {ExchangeRate.objects.count()}")
    print(f"  📁 Categorías: {Category.objects.count()}")
    print(f"  📦 Productos: {Product.objects.count()}")
    print(f"  🏢 Proveedores: {Supplier.objects.count()}")
    print(f"  👥 Clientes: {Customer.objects.count()}")
    print(f"  📝 Órdenes de compra: {SupplierOrder.objects.count()}")

    print("\n" + "="*60)
    print(" CREDENCIALES DE ACCESO")
    print("="*60)
    print("  👨‍💼 Administrador:")
    print("     Usuario: admin_test")
    print("     Password: test123")
    print("\n  👤 Vendedor:")
    print("     Usuario: vendedor1")
    print("     Password: test123")

    print("\n" + "="*60)
    print(" DATOS DE PRUEBA LISTOS")
    print("="*60)
    print("\n🚀 Puedes iniciar el servidor con:")
    print("   python3 manage.py runserver\n")
    print("🌐 Y acceder a: http://localhost:8000\n")

    print("📝 ESCENARIOS DE PRUEBA DISPONIBLES:")
    print("   • Orden #1: Pendiente de recibir, sin pagos")
    print("   • Orden #2: Recibida, lista para pago parcial")
    print("   • Orden #3: Recibida, lista para pago completo\n")

if __name__ == '__main__':
    try:
        create_test_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
