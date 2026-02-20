# suppliers/tests.py - Suite completa de pruebas para el módulo de proveedores

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from suppliers.models import Supplier, SupplierOrder, SupplierOrderItem
from inventory.models import Category, Product, InventoryAdjustment
from utils.models import ExchangeRate

User = get_user_model()


class SupplierTestBase(TestCase):
    """Base con fixtures comunes para todos los tests de suppliers"""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_sup', password='admin123',
            first_name='Admin', last_name='Test',
            is_admin=True
        )
        self.employee = User.objects.create_user(
            username='emp_sup', password='emp123',
            first_name='Emp', last_name='Test',
            is_employee=True
        )
        self.normal_user = User.objects.create_user(
            username='normal_sup', password='normal123',
            first_name='Normal', last_name='Test'
        )

        self.rate = ExchangeRate.objects.create(
            bs_to_usd=Decimal('36.00'),
            updated_by=self.admin
        )

        self.category = Category.objects.create(name='Alimentos')
        self.product = Product.objects.create(
            name='Arroz 1kg',
            barcode='7700001',
            category=self.category,
            purchase_price_usd=Decimal('1.50'),
            purchase_price_bs=Decimal('54.00'),
            selling_price_usd=Decimal('2.00'),
            selling_price_bs=Decimal('72.00'),
            stock=Decimal('100'),
        )

        self.supplier = Supplier.objects.create(
            name='Distribuidora Nacional',
            contact_person='Juan Pérez',
            phone='0414-1234567',
            email='juan@dist.com',
        )

        self.order = SupplierOrder.objects.create(
            supplier=self.supplier,
            status='pending',
            total_usd=Decimal('150.00'),
            total_bs=Decimal('5400.00'),
            exchange_rate_used=Decimal('36.00'),
            created_by=self.admin,
        )
        self.order_item = SupplierOrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('100'),
            price_usd=Decimal('1.50'),
        )


# ─── Modelo: Supplier ─────────────────────────────────────────────────────────

class SupplierModelTests(SupplierTestBase):

    def test_supplier_str(self):
        self.assertEqual(str(self.supplier), 'Distribuidora Nacional')

    def test_supplier_get_absolute_url(self):
        url = self.supplier.get_absolute_url()
        self.assertIn(str(self.supplier.pk), url)

    def test_supplier_is_active_default_true(self):
        s = Supplier.objects.create(name='Nuevo')
        self.assertTrue(s.is_active)

    def test_supplier_ordering_by_name(self):
        Supplier.objects.create(name='AAA Distribuidora')
        suppliers = list(Supplier.objects.all())
        self.assertEqual(suppliers[0].name, 'AAA Distribuidora')


# ─── Modelo: SupplierOrder ────────────────────────────────────────────────────

class SupplierOrderModelTests(SupplierTestBase):

    def test_order_str_contains_id_and_supplier(self):
        text = str(self.order)
        self.assertIn(str(self.order.id), text)
        self.assertIn('Distribuidora Nacional', text)

    def test_order_default_status_is_pending(self):
        order = SupplierOrder.objects.create(
            supplier=self.supplier,
            created_by=self.admin,
        )
        self.assertEqual(order.status, 'pending')

    def test_order_get_absolute_url(self):
        url = self.order.get_absolute_url()
        self.assertIn(str(self.order.pk), url)

    def test_order_default_exchange_rate_is_1(self):
        order = SupplierOrder.objects.create(
            supplier=self.supplier,
            created_by=self.admin,
        )
        self.assertEqual(order.exchange_rate_used, Decimal('1'))


# ─── Modelo: SupplierOrderItem ────────────────────────────────────────────────

class SupplierOrderItemModelTests(SupplierTestBase):

    def test_item_str(self):
        text = str(self.order_item)
        self.assertIn('Arroz', text)
        self.assertIn('100', text)

    def test_item_subtotal_usd(self):
        # 100 * 1.50 = 150.00
        self.assertEqual(self.order_item.subtotal_usd, Decimal('150.00'))

    def test_item_subtotal_bs(self):
        # price_bs auto-calculado: 1.50 * 36.00 = 54.00; subtotal = 100 * 54.00 = 5400.00
        self.assertEqual(self.order_item.subtotal_bs, Decimal('5400.00'))

    def test_item_subtotal_alias_equals_subtotal_bs(self):
        self.assertEqual(self.order_item.subtotal, self.order_item.subtotal_bs)

    def test_item_auto_calculates_price_bs_on_save_with_rate(self):
        item = SupplierOrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('10'),
            price_usd=Decimal('2.00'),
        )
        # 2.00 * 36.00 = 72.00
        self.assertEqual(item.price_bs, Decimal('72.00'))

    def test_item_price_bs_uses_fallback_7_when_no_rate(self):
        ExchangeRate.objects.all().delete()
        item = SupplierOrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('5'),
            price_usd=Decimal('10.00'),
        )
        # fallback 7.0: 10.00 * 7.0 = 70.0
        self.assertEqual(item.price_bs, Decimal('70.0'))

    def test_item_price_bs_not_calculated_when_price_usd_is_zero(self):
        item = SupplierOrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('5'),
            price_usd=Decimal('0'),
        )
        self.assertEqual(item.price_bs, Decimal('0'))


# ─── Vistas: Acceso ───────────────────────────────────────────────────────────

class SupplierViewAccessTests(SupplierTestBase):

    def test_supplier_list_requires_login(self):
        resp = self.client.get(reverse('suppliers:supplier_list'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

    def test_supplier_list_accessible_by_employee(self):
        # NOTA: solo usa @login_required, no @admin_required (potencial bug de seguridad)
        self.client.login(username='emp_sup', password='emp123')
        resp = self.client.get(reverse('suppliers:supplier_list'))
        self.assertEqual(resp.status_code, 200)

    def test_supplier_list_accessible_by_admin(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:supplier_list'))
        self.assertEqual(resp.status_code, 200)

    def test_supplier_detail_requires_login(self):
        resp = self.client.get(reverse('suppliers:supplier_detail', args=[self.supplier.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_supplier_detail_shows_supplier_name(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:supplier_detail', args=[self.supplier.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Distribuidora Nacional')

    def test_order_cancel_requires_admin_not_employee(self):
        self.client.login(username='emp_sup', password='emp123')
        resp = self.client.post(reverse('suppliers:order_cancel', args=[self.order.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_redirected_from_all_supplier_urls(self):
        urls = [
            reverse('suppliers:supplier_list'),
            reverse('suppliers:supplier_detail', args=[self.supplier.pk]),
            reverse('suppliers:supplier_create'),
            reverse('suppliers:order_list'),
            reverse('suppliers:order_detail', args=[self.order.pk]),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f"{url} no redirige anónimos")
            self.assertIn('/accounts/login/', resp['Location'])


# ─── Vistas: CRUD de Proveedor ────────────────────────────────────────────────

class SupplierCRUDTests(SupplierTestBase):

    def test_create_supplier_get_renders_form(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:supplier_create'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.context)

    def test_create_supplier_post_valid(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.post(reverse('suppliers:supplier_create'), {
            'name': 'Nuevo Proveedor SA',
            'contact_person': 'María García',
            'phone': '0212-5551234',
            'email': 'maria@nuevo.com',
            'is_active': True,
        })
        self.assertTrue(Supplier.objects.filter(name='Nuevo Proveedor SA').exists())
        self.assertEqual(resp.status_code, 302)

    def test_create_supplier_post_empty_name_fails(self):
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(reverse('suppliers:supplier_create'), {'name': ''})
        self.assertFalse(Supplier.objects.filter(name='').exists())

    def test_update_supplier_changes_name(self):
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(
            reverse('suppliers:supplier_update', args=[self.supplier.pk]),
            {'name': 'Dist. Actualizada', 'is_active': True}
        )
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.name, 'Dist. Actualizada')

    def test_delete_supplier_blocked_if_has_orders(self):
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(reverse('suppliers:supplier_delete', args=[self.supplier.pk]))
        # El proveedor tiene self.order, no debe borrarse
        self.assertTrue(Supplier.objects.filter(pk=self.supplier.pk).exists())

    def test_delete_supplier_succeeds_without_orders(self):
        new_s = Supplier.objects.create(name='Sin Ordenes')
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(reverse('suppliers:supplier_delete', args=[new_s.pk]))
        self.assertFalse(Supplier.objects.filter(pk=new_s.pk).exists())


# ─── Vistas: Recepción de Órdenes ────────────────────────────────────────────

class OrderReceiveTests(SupplierTestBase):

    def test_order_receive_requires_login(self):
        resp = self.client.get(reverse('suppliers:order_receive', args=[self.order.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_order_receive_get_shows_form(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:order_receive', args=[self.order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.context)

    def test_order_receive_post_updates_stock(self):
        initial_stock = self.product.stock  # 100
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(
            reverse('suppliers:order_receive', args=[self.order.pk]),
            {'update_prices': False, 'notes': ''}
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock + self.order_item.quantity)

    def test_order_receive_post_changes_status(self):
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(
            reverse('suppliers:order_receive', args=[self.order.pk]),
            {'update_prices': False, 'notes': ''}
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'received')

    def test_order_receive_creates_inventory_adjustment(self):
        count_before = InventoryAdjustment.objects.count()
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(
            reverse('suppliers:order_receive', args=[self.order.pk]),
            {'update_prices': False, 'notes': ''}
        )
        self.assertGreater(InventoryAdjustment.objects.count(), count_before)

    def test_order_receive_with_update_prices_updates_purchase_price(self):
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(
            reverse('suppliers:order_receive', args=[self.order.pk]),
            {'update_prices': True, 'notes': ''}
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.purchase_price_usd, self.order_item.price_usd)

    def test_already_received_order_cannot_be_received_again(self):
        self.order.status = 'received'
        self.order.save()
        stock_before = self.product.stock
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(
            reverse('suppliers:order_receive', args=[self.order.pk]),
            {'update_prices': False}
        )
        self.product.refresh_from_db()
        # Stock no debe cambiar si la orden ya fue recibida
        self.assertEqual(self.product.stock, stock_before)


# ─── Vistas: Cancelación de Órdenes ──────────────────────────────────────────

class OrderCancelTests(SupplierTestBase):

    def test_cancel_order_by_admin_succeeds(self):
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(reverse('suppliers:order_cancel', args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')

    def test_cancel_received_order_fails(self):
        self.order.status = 'received'
        self.order.save()
        self.client.login(username='admin_sup', password='admin123')
        self.client.post(reverse('suppliers:order_cancel', args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'received')

    def test_cancel_order_get_shows_confirmation_page(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:order_cancel', args=[self.order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('order', resp.context)


# ─── Vistas: Lista y Filtros de Órdenes ──────────────────────────────────────

class OrderListFilterTests(SupplierTestBase):

    def test_order_list_filter_by_supplier(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(
            reverse('suppliers:order_list'),
            {'supplier': self.supplier.pk}
        )
        self.assertEqual(resp.status_code, 200)

    def test_order_list_filter_by_status_pending(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:order_list'), {'status': 'pending'})
        self.assertEqual(resp.status_code, 200)

    def test_order_list_filter_by_status_received(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:order_list'), {'status': 'received'})
        self.assertEqual(resp.status_code, 200)

    def test_order_detail_shows_calculated_totals(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:order_detail', args=[self.order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total_usd', resp.context)
        self.assertIn('total_bs', resp.context)
        # 100 * 1.50 = 150.00
        self.assertEqual(resp.context['total_usd'], Decimal('150.00'))


# ─── Edge Cases ───────────────────────────────────────────────────────────────

class SupplierEdgeCaseTests(SupplierTestBase):

    def test_order_receive_without_exchange_rate_does_not_crash(self):
        ExchangeRate.objects.all().delete()
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.post(
            reverse('suppliers:order_receive', args=[self.order.pk]),
            {'update_prices': False, 'notes': ''}
        )
        self.assertNotEqual(resp.status_code, 500)

    def test_supplier_search_returns_matching(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:supplier_list'), {'q': 'Nacional'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Distribuidora Nacional')

    def test_supplier_search_no_results_does_not_crash(self):
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:supplier_list'), {'q': 'XYZNoExiste'})
        self.assertEqual(resp.status_code, 200)

    def test_update_received_order_redirects_with_error(self):
        self.order.status = 'received'
        self.order.save()
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.post(
            reverse('suppliers:order_update', args=[self.order.pk]),
            {'supplier': self.supplier.pk}
        )
        # Debe redirigir con mensaje de error, no actualizar
        self.assertEqual(resp.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'received')

    def test_item_price_bs_recalculated_when_rate_changes(self):
        # Cambiar la tasa
        ExchangeRate.objects.create(bs_to_usd=Decimal('40.00'), updated_by=self.admin)
        new_item = SupplierOrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('1'),
            price_usd=Decimal('10.00'),
        )
        # 10.00 * 40.00 = 400.00
        self.assertEqual(new_item.price_bs, Decimal('400.00'))

    def test_order_create_get_without_exchange_rate_shows_error_context(self):
        ExchangeRate.objects.all().delete()
        self.client.login(username='admin_sup', password='admin123')
        resp = self.client.get(reverse('suppliers:order_create'))
        self.assertEqual(resp.status_code, 200)
        # current_exchange_rate debería ser None
        self.assertIsNone(resp.context.get('current_exchange_rate'))
