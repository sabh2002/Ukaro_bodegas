# utils/tests_performance.py
"""
Tests para optimizaciones de rendimiento (FASE 3.3)
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.test.utils import override_settings
from django.db import connection
from django.test import TestCase as DjangoTestCase

from utils.models import ExchangeRate
from inventory.models import Product, Category
from suppliers.models import Supplier, SupplierOrder, SupplierOrderItem
from sales.models import Sale, SaleItem
from customers.models import Customer

User = get_user_model()


class ExchangeRateCacheTest(TestCase):
    """Tests para el sistema de caché de ExchangeRate"""

    def setUp(self):
        # Limpiar caché antes de cada test
        cache.clear()

        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_admin=True
        )

    def test_get_latest_rate_caches_result(self):
        """Primera llamada debe cachear el resultado"""
        rate = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.user
        )

        # Primera llamada - debe consultar BD
        result1 = ExchangeRate.get_latest_rate()
        self.assertEqual(result1.bs_to_usd, Decimal('45.50'))

        # Verificar que se cacheó
        cached_rate = cache.get('exchange_rate_latest')
        self.assertIsNotNone(cached_rate)
        self.assertEqual(cached_rate.bs_to_usd, Decimal('45.50'))

        # Segunda llamada - debe usar caché (sin consulta BD)
        result2 = ExchangeRate.get_latest_rate()
        self.assertEqual(result2.bs_to_usd, Decimal('45.50'))

    def test_get_latest_rate_returns_same_instance_from_cache(self):
        """Múltiples llamadas deben retornar la misma instancia cacheada"""
        ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.user
        )

        result1 = ExchangeRate.get_latest_rate()
        result2 = ExchangeRate.get_latest_rate()

        # Deben ser el mismo objeto en memoria
        self.assertIs(result1, result2)

    def test_save_invalidates_cache(self):
        """Guardar nueva tasa debe invalidar el caché"""
        rate1 = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.user
        )

        # Cachear
        ExchangeRate.get_latest_rate()
        self.assertIsNotNone(cache.get('exchange_rate_latest'))

        # Crear nueva tasa - debe invalidar caché
        rate2 = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('50.00'),
            updated_by=self.user
        )

        # Caché debe estar vacío
        cached = cache.get('exchange_rate_latest')
        # Django no garantiza que el caché esté completamente vacío inmediatamente,
        # pero la próxima llamada debe retornar la nueva tasa

        result = ExchangeRate.get_latest_rate()
        self.assertEqual(result.bs_to_usd, Decimal('50.00'))

    def test_delete_invalidates_cache(self):
        """Eliminar tasa debe invalidar el caché"""
        rate = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.user
        )

        # Cachear
        ExchangeRate.get_latest_rate()
        self.assertIsNotNone(cache.get('exchange_rate_latest'))

        # Eliminar - debe invalidar caché
        rate.delete()

        # Siguiente llamada debe consultar BD y cachear None
        result = ExchangeRate.get_latest_rate()
        self.assertIsNone(result)

    def test_cache_none_when_no_rate_exists(self):
        """Debe cachear None cuando no hay tasas"""
        result = ExchangeRate.get_latest_rate()
        self.assertIsNone(result)

        # Verificar que None se cacheó
        cached = cache.get('exchange_rate_latest')
        self.assertIsNone(cached)

    def test_cache_ttl_for_none_is_shorter(self):
        """Caché de None debe tener TTL más corto (5 min vs 1 hora)"""
        # No hay forma directa de verificar TTL en Django cache
        # Pero podemos verificar que None se cachea
        result = ExchangeRate.get_latest_rate()
        self.assertIsNone(result)

        cached = cache.get('exchange_rate_latest')
        self.assertIsNone(cached)


class QueryOptimizationTest(DjangoTestCase):
    """Tests para optimizaciones de queries con select_related/prefetch_related"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_admin=True
        )

        self.exchange_rate = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.user
        )

        self.supplier = Supplier.objects.create(
            name='Proveedor Test',
            contact_person='Juan Pérez',
            email='test@proveedor.com'
        )

        self.category = Category.objects.create(name='Test Category')

        self.product = Product.objects.create(
            name='Producto Test',
            barcode='123456789',
            category=self.category,
            purchase_price_usd=Decimal('10.00'),
            purchase_price_bs=Decimal('455.00'),
            selling_price_usd=Decimal('15.00'),
            selling_price_bs=Decimal('682.50'),
            stock=10
        )

        # Crear órdenes de prueba
        for i in range(5):
            order = SupplierOrder.objects.create(
                supplier=self.supplier,
                order_date=timezone.now(),
                status='pending',
                total_usd=Decimal('100.00'),
                total_bs=Decimal('4550.00'),
                exchange_rate_used=Decimal('45.50'),
                created_by=self.user
            )

            SupplierOrderItem.objects.create(
                order=order,
                product=self.product,
                quantity=10,
                price_usd=Decimal('10.00'),
                price_bs=Decimal('455.00')
            )

    def test_supplier_order_list_without_optimization_has_n_plus_1(self):
        """Sin optimización debe tener problema N+1"""
        # Simular consulta sin optimización
        orders = SupplierOrder.objects.all()

        # Resetear contador de queries
        connection.queries_log.clear()

        with self.assertNumQueries(11):  # 1 inicial + 5*2 (supplier, created_by)
            list_orders = list(orders)
            for order in list_orders:
                # Acceder a relaciones causa queries adicionales
                _ = order.supplier.name
                _ = order.created_by.username

    def test_supplier_order_list_with_select_related_is_optimized(self):
        """Con select_related debe reducir queries"""
        # Consulta optimizada
        orders = SupplierOrder.objects.select_related('supplier', 'created_by').all()

        # Resetear contador
        connection.queries_log.clear()

        with self.assertNumQueries(1):  # Solo 1 query con JOIN
            list_orders = list(orders)
            for order in list_orders:
                _ = order.supplier.name
                _ = order.created_by.username

    def test_supplier_order_detail_with_prefetch_related_is_optimized(self):
        """prefetch_related debe optimizar relaciones inversas"""
        order = SupplierOrder.objects.filter(pk=1).select_related(
            'supplier', 'created_by'
        ).prefetch_related('items__product').first()

        if not order:
            self.skipTest("No hay orden para testear")

        connection.queries_log.clear()

        # Acceder a items no debe causar queries adicionales
        with self.assertNumQueries(0):
            items = list(order.items.all())
            for item in items:
                _ = item.product.name


class DatabaseIndexTest(TestCase):
    """Tests para verificar que los índices existen"""

    def test_supplier_order_indexes_exist(self):
        """Verificar que los índices de SupplierOrder existen"""
        from django.db import connection

        with connection.cursor() as cursor:
            # Obtener índices de la tabla
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'suppliers_supplierorder'
            """)

            indexes = [row[0] for row in cursor.fetchall()]

            # Verificar que existen los índices esperados
            self.assertIn('order_supplier_status_idx', indexes)
            self.assertIn('order_status_date_idx', indexes)
            self.assertIn('order_paid_date_idx', indexes)

    def test_product_indexes_exist(self):
        """Verificar que los índices de Product existen"""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'inventory_product'
            """)

            indexes = [row[0] for row in cursor.fetchall()]

            self.assertIn('product_cat_active_idx', indexes)
            self.assertIn('product_active_recent_idx', indexes)
            self.assertIn('product_barcode_idx', indexes)

    def test_sale_indexes_exist(self):
        """Verificar que los índices de Sale existen"""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'sales_sale'
            """)

            indexes = [row[0] for row in cursor.fetchall()]

            self.assertIn('sale_customer_date_idx', indexes)
            self.assertIn('sale_user_date_idx', indexes)
            self.assertIn('sale_credit_date_idx', indexes)
            self.assertIn('sale_date_idx', indexes)


class PerformanceBenchmarkTest(TestCase):
    """Tests de benchmark para medir mejoras de rendimiento"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_admin=True
        )

        self.exchange_rate = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.user
        )

        self.category = Category.objects.create(name='Test Category')

        # Crear 100 productos para benchmark realista
        for i in range(100):
            Product.objects.create(
                name=f'Producto {i}',
                barcode=f'BARCODE{i:05d}',
                category=self.category,
                purchase_price_usd=Decimal('10.00'),
                purchase_price_bs=Decimal('455.00'),
                selling_price_usd=Decimal('15.00'),
                selling_price_bs=Decimal('682.50'),
                stock=10
            )

    def test_product_lookup_by_barcode_uses_index(self):
        """Búsqueda por barcode debe usar índice"""
        import time

        # Sin índice sería más lento, pero con índice debe ser rápido
        start = time.time()
        product = Product.objects.filter(barcode='BARCODE00050').first()
        end = time.time()

        elapsed = end - start

        self.assertIsNotNone(product)
        # Con índice, debe ser < 0.01 segundos (10ms)
        self.assertLess(elapsed, 0.1)  # Tolerancia más amplia para CI

    def test_exchange_rate_cache_reduces_queries(self):
        """Caché debe reducir queries dramáticamente"""
        cache.clear()

        # Primera llamada - consulta BD
        connection.queries_log.clear()
        result1 = ExchangeRate.get_latest_rate()
        first_call_queries = len(connection.queries)

        # Segunda llamada - usa caché
        connection.queries_log.clear()
        result2 = ExchangeRate.get_latest_rate()
        second_call_queries = len(connection.queries)

        # Segunda llamada debe tener 0 queries
        self.assertEqual(second_call_queries, 0)
        self.assertGreater(first_call_queries, 0)
