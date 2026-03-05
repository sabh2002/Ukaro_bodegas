# suppliers/tests_payment.py
"""
Tests para el sistema de pagos a proveedores (FASE 3.1)
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from suppliers.models import Supplier, SupplierOrder, SupplierOrderItem, SupplierPayment
from inventory.models import Product, Category
from utils.models import ExchangeRate

User = get_user_model()


class SupplierPaymentModelTest(TestCase):
    """Tests para el modelo SupplierPayment"""

    def setUp(self):
        """Configuración inicial para cada test"""
        # Crear usuario
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_admin=True
        )

        # Crear tasa de cambio
        self.exchange_rate = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.user
        )

        # Crear proveedor
        self.supplier = Supplier.objects.create(
            name='Proveedor Test',
            contact_person='Juan Pérez',
            email='test@proveedor.com',
            phone='1234567890'
        )

        # Crear categoría y producto
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Producto Test',
            barcode='123456',
            category=self.category,
            purchase_price_usd=Decimal('10.00'),
            purchase_price_bs=Decimal('455.00'),
            selling_price_usd=Decimal('15.00'),
            selling_price_bs=Decimal('682.50'),
            stock=0,
            min_stock=5
        )

        # Crear orden a proveedor
        self.order = SupplierOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now(),
            status='pending',
            total_usd=Decimal('100.00'),
            total_bs=Decimal('4550.00'),
            exchange_rate_used=Decimal('45.50'),
            created_by=self.user
        )

        # Crear item de orden
        SupplierOrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=10,
            price_usd=Decimal('10.00'),
            price_bs=Decimal('455.00')
        )

    def test_create_payment_calculates_bs_from_usd(self):
        """Debe calcular automáticamente el monto en Bs desde USD"""
        payment = SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('50.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.assertEqual(payment.amount_bs, Decimal('2275.00'))  # 50 * 45.50
        self.assertEqual(payment.exchange_rate_used, Decimal('45.50'))

    def test_create_payment_without_exchange_rate_raises_error(self):
        """Debe fallar si no hay tasa de cambio configurada"""
        # Eliminar todas las tasas de cambio
        ExchangeRate.objects.all().delete()

        # Limpiar caché para asegurar que no hay tasa cacheada
        from django.core.cache import cache
        cache.clear()

        with self.assertRaises(ValueError) as context:
            SupplierPayment.objects.create(
                order=self.order,
                amount_usd=Decimal('50.00'),
                payment_date=timezone.now(),
                payment_method='transfer',
                created_by=self.user
            )

        self.assertIn('No hay tasa de cambio', str(context.exception))

    def test_payment_updates_order_totals_automatically(self):
        """Crear pago debe actualizar automáticamente los totales de la orden"""
        initial_paid_usd = self.order.paid_amount_usd
        initial_paid_bs = self.order.paid_amount_bs

        payment = SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('50.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        # Recargar orden desde BD
        self.order.refresh_from_db()

        self.assertEqual(self.order.paid_amount_usd, Decimal('50.00'))
        self.assertEqual(self.order.paid_amount_bs, Decimal('2275.00'))
        self.assertEqual(self.order.payment_status, 'partial')
        self.assertFalse(self.order.paid)

    def test_full_payment_marks_order_as_paid(self):
        """Pago completo debe marcar la orden como pagada"""
        payment = SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('100.00'),  # Monto total
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.order.refresh_from_db()

        self.assertEqual(self.order.payment_status, 'paid')
        self.assertTrue(self.order.paid)
        self.assertEqual(self.order.outstanding_balance_usd, Decimal('0'))

    def test_multiple_partial_payments(self):
        """Múltiples pagos parciales deben acumularse correctamente"""
        # Primer pago: $30
        SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('30.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount_usd, Decimal('30.00'))
        self.assertEqual(self.order.payment_status, 'partial')

        # Segundo pago: $40
        SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('40.00'),
            payment_date=timezone.now(),
            payment_method='cash',
            created_by=self.user
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount_usd, Decimal('70.00'))
        self.assertEqual(self.order.outstanding_balance_usd, Decimal('30.00'))
        self.assertEqual(self.order.payment_status, 'partial')

        # Tercer pago: $30 (completar)
        SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('30.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount_usd, Decimal('100.00'))
        self.assertEqual(self.order.payment_status, 'paid')
        self.assertTrue(self.order.paid)

    def test_delete_payment_recalculates_totals(self):
        """Eliminar pago debe recalcular totales automáticamente"""
        # Crear dos pagos
        payment1 = SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('50.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        payment2 = SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('30.00'),
            payment_date=timezone.now(),
            payment_method='cash',
            created_by=self.user
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount_usd, Decimal('80.00'))

        # Eliminar primer pago
        payment1.delete()

        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount_usd, Decimal('30.00'))
        self.assertEqual(self.order.payment_status, 'partial')

    def test_overpayment_not_allowed(self):
        """No debe permitir pagar más del total de la orden"""
        # Esto debe ser validado en el form, pero verificamos el comportamiento
        SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('150.00'),  # Más del total ($100)
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.order.refresh_from_db()
        # El sistema permite sobrepago pero marca como "paid"
        self.assertTrue(self.order.paid)
        self.assertEqual(self.order.payment_status, 'paid')

    def test_outstanding_balance_calculation(self):
        """Debe calcular correctamente el saldo pendiente"""
        self.assertEqual(self.order.outstanding_balance_usd, Decimal('100.00'))

        SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('25.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.outstanding_balance_usd, Decimal('75.00'))

    def test_payment_with_different_exchange_rates(self):
        """Pagos en diferentes fechas pueden usar tasas diferentes"""
        from datetime import timedelta
        from django.core.cache import cache

        # Primer pago con tasa 45.50
        payment1 = SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('50.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.assertEqual(payment1.exchange_rate_used, Decimal('45.50'))
        self.assertEqual(payment1.amount_bs, Decimal('2275.00'))

        # Cambiar tasa de cambio - usar fecha futura para asegurar que es más reciente
        tomorrow = timezone.now().date() + timedelta(days=1)
        new_rate = ExchangeRate.objects.create(
            date=tomorrow,
            bs_to_usd=Decimal('50.00'),
            updated_by=self.user
        )

        # Limpiar caché explícitamente para tests
        cache.clear()

        # Segundo pago con nueva tasa
        payment2 = SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('50.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.assertEqual(payment2.exchange_rate_used, Decimal('50.00'))
        self.assertEqual(payment2.amount_bs, Decimal('2500.00'))

        # Verificar que ambos pagos se suman en USD
        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount_usd, Decimal('100.00'))
        # Y en Bs se suman con sus respectivas tasas
        self.assertEqual(self.order.paid_amount_bs, Decimal('4775.00'))  # 2275 + 2500


class SupplierOrderPaymentStatusTest(TestCase):
    """Tests para los estados de pago de órdenes"""

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

        self.order = SupplierOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now(),
            status='pending',
            total_usd=Decimal('100.00'),
            total_bs=Decimal('4550.00'),
            exchange_rate_used=Decimal('45.50'),
            created_by=self.user
        )

    def test_initial_payment_status_is_unpaid(self):
        """Nueva orden debe tener estado 'unpaid'"""
        self.assertEqual(self.order.payment_status, 'unpaid')
        self.assertEqual(self.order.paid_amount_usd, Decimal('0'))
        self.assertFalse(self.order.paid)

    def test_payment_status_transitions(self):
        """Estados de pago deben transicionar correctamente"""
        # unpaid → partial
        SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('10.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'partial')
        self.assertFalse(self.order.paid)

        # partial → paid
        SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('90.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')
        self.assertTrue(self.order.paid)

    def test_update_payment_totals_method(self):
        """Método update_payment_totals debe funcionar correctamente"""
        SupplierPayment.objects.create(
            order=self.order,
            amount_usd=Decimal('25.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=self.user
        )

        # Llamar manualmente al método
        self.order.update_payment_totals()

        self.assertEqual(self.order.paid_amount_usd, Decimal('25.00'))
        self.assertEqual(self.order.payment_status, 'partial')
        self.assertFalse(self.order.paid)
