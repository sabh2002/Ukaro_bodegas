# sales/tests.py - Comprehensive test suite for the sales app

from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from inventory.models import Category, Product, ProductCombo
from sales.models import Sale, SaleItem
from utils.models import ExchangeRate


class SalesTestSetUpMixin:
    """
    Shared setUp logic for all sales test classes.
    Creates users, a customer, a category, products, a combo,
    an exchange rate, and sample sales with items.
    """

    def setUp(self):
        # ── Users ──────────────────────────────────────────────
        self.admin_user = User.objects.create_user(
            username='admin_user',
            password='testpass123',
            is_admin=True,
            is_employee=False,
        )
        self.employee1 = User.objects.create_user(
            username='employee1',
            password='testpass123',
            is_admin=False,
            is_employee=True,
            first_name='Juan',
            last_name='Perez',
        )
        self.employee2 = User.objects.create_user(
            username='employee2',
            password='testpass123',
            is_admin=False,
            is_employee=True,
        )
        self.normal_user = User.objects.create_user(
            username='normal_user',
            password='testpass123',
            is_admin=False,
            is_employee=False,
        )

        # ── Customer ──────────────────────────────────────────
        self.customer = Customer.objects.create(
            name='Cliente Test',
            phone='04121234567',
        )

        # ── Category & Products ───────────────────────────────
        self.category = Category.objects.create(
            name='Bebidas',
            description='Bebidas varias',
        )
        self.product1 = Product.objects.create(
            name='Coca Cola 2L',
            barcode='111111111111',
            category=self.category,
            purchase_price_usd=Decimal('1.00'),
            selling_price_usd=Decimal('1.50'),
            stock=Decimal('100.000'),
        )
        self.product2 = Product.objects.create(
            name='Pepsi 2L',
            barcode='222222222222',
            category=self.category,
            purchase_price_usd=Decimal('0.90'),
            selling_price_usd=Decimal('1.40'),
            stock=Decimal('50.000'),
        )

        # ── Combo ─────────────────────────────────────────────
        self.combo = ProductCombo.objects.create(
            name='Combo Refrescos',
            description='Combo de prueba',
            combo_price_bs=Decimal('80.00'),
        )

        # ── Exchange Rate ─────────────────────────────────────
        self.exchange_rate = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('36.50'),
            updated_by=self.admin_user,
        )

        # ── Sales ─────────────────────────────────────────────
        # Sale 1: employee1, cash, with customer
        self.sale_emp1_cash = Sale.objects.create(
            customer=self.customer,
            user=self.employee1,
            total_bs=Decimal('150.00'),
            total_usd=Decimal('4.11'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
            is_credit=False,
            notes='Venta de prueba efectivo',
        )
        SaleItem.objects.create(
            sale=self.sale_emp1_cash,
            product=self.product1,
            quantity=Decimal('2.000'),
            price_bs=Decimal('54.75'),
            price_usd=Decimal('1.50'),
        )
        SaleItem.objects.create(
            sale=self.sale_emp1_cash,
            product=self.product2,
            quantity=Decimal('1.000'),
            price_bs=Decimal('40.50'),
            price_usd=Decimal('1.11'),
        )

        # Sale 2: employee1, card, credit
        self.sale_emp1_card = Sale.objects.create(
            customer=self.customer,
            user=self.employee1,
            total_bs=Decimal('200.00'),
            total_usd=Decimal('5.48'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='card',
            is_credit=True,
            notes='Venta credito con tarjeta',
        )
        SaleItem.objects.create(
            sale=self.sale_emp1_card,
            product=self.product1,
            quantity=Decimal('3.000'),
            price_bs=Decimal('54.75'),
            price_usd=Decimal('1.50'),
        )

        # Sale 3: employee2, mobile, with reference
        self.sale_emp2_mobile = Sale.objects.create(
            customer=self.customer,
            user=self.employee2,
            total_bs=Decimal('100.00'),
            total_usd=Decimal('2.74'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='mobile',
            mobile_reference='REF123456',
            is_credit=False,
            notes='Pago movil',
        )
        SaleItem.objects.create(
            sale=self.sale_emp2_mobile,
            product=self.product2,
            quantity=Decimal('2.000'),
            price_bs=Decimal('50.00'),
            price_usd=Decimal('1.37'),
        )

        # Sale 4: employee1, no customer (cash sale)
        self.sale_no_customer = Sale.objects.create(
            customer=None,
            user=self.employee1,
            total_bs=Decimal('50.00'),
            total_usd=Decimal('1.37'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
            is_credit=False,
        )

        # Sale 5: employee1, combo item
        self.sale_with_combo = Sale.objects.create(
            customer=self.customer,
            user=self.employee1,
            total_bs=Decimal('80.00'),
            total_usd=Decimal('2.19'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
            is_credit=False,
        )
        self.combo_item = SaleItem.objects.create(
            sale=self.sale_with_combo,
            product=None,
            combo=self.combo,
            quantity=Decimal('1.000'),
            price_bs=Decimal('80.00'),
            price_usd=Decimal('2.19'),
        )

        # ── Client ────────────────────────────────────────────
        self.client = Client()


# ═══════════════════════════════════════════════════════════════
#  1. MODEL TESTS
# ═══════════════════════════════════════════════════════════════

class SaleModelTest(SalesTestSetUpMixin, TestCase):
    """Tests for the Sale model."""

    # ── __str__ ───────────────────────────────────────────────

    def test_str_representation(self):
        """Sale __str__ returns 'Venta #<id> - <date formatted>'."""
        sale = self.sale_emp1_cash
        expected = f"Venta #{sale.id} - {sale.date.strftime('%d/%m/%Y %H:%M')}"
        self.assertEqual(str(sale), expected)

    # ── get_absolute_url ──────────────────────────────────────

    def test_get_absolute_url(self):
        """get_absolute_url returns the correct detail URL."""
        sale = self.sale_emp1_cash
        expected_url = reverse('sales:sale_detail', args=[sale.id])
        self.assertEqual(sale.get_absolute_url(), expected_url)

    # ── item_count ────────────────────────────────────────────

    def test_item_count_with_multiple_items(self):
        """item_count sums the quantities of all items in the sale."""
        # sale_emp1_cash has items with quantity 2 + 1 = 3
        self.assertEqual(self.sale_emp1_cash.item_count, Decimal('3.000'))

    def test_item_count_single_item(self):
        """item_count works correctly with a single item."""
        # sale_emp2_mobile has one item with quantity 2
        self.assertEqual(self.sale_emp2_mobile.item_count, Decimal('2.000'))

    def test_item_count_no_items_returns_zero(self):
        """item_count returns 0 when the sale has no items."""
        # sale_no_customer was created with no items
        self.assertEqual(self.sale_no_customer.item_count, 0)

    # ── Payment method icons ──────────────────────────────────

    def test_payment_method_icon_cash(self):
        """Cash payment returns the cash emoji icon."""
        self.assertEqual(
            self.sale_emp1_cash.get_payment_method_icon(), '\U0001f4b5'
        )

    def test_payment_method_icon_card(self):
        """Card payment returns the card emoji icon."""
        self.assertEqual(
            self.sale_emp1_card.get_payment_method_icon(), '\U0001f4b3'
        )

    def test_payment_method_icon_mobile(self):
        """Mobile payment returns the mobile emoji icon."""
        self.assertEqual(
            self.sale_emp2_mobile.get_payment_method_icon(), '\U0001f4f1'
        )

    def test_payment_method_icon_unknown_returns_default(self):
        """An unknown payment method returns the default money bag icon."""
        sale = self.sale_emp1_cash
        sale.payment_method = 'crypto'
        self.assertEqual(sale.get_payment_method_icon(), '\U0001f4b0')

    # ── Payment display with icon ─────────────────────────────

    def test_payment_display_cash(self):
        """Cash display: icon + 'Efectivo'."""
        display = self.sale_emp1_cash.get_payment_method_display_with_icon()
        self.assertIn('Efectivo', display)
        self.assertIn('\U0001f4b5', display)

    def test_payment_display_card(self):
        """Card display: icon + 'Punto de Venta'."""
        display = self.sale_emp1_card.get_payment_method_display_with_icon()
        self.assertIn('Punto de Venta', display)
        self.assertIn('\U0001f4b3', display)

    def test_payment_display_mobile_with_reference(self):
        """Mobile display with reference includes (Ref: ...)."""
        display = self.sale_emp2_mobile.get_payment_method_display_with_icon()
        self.assertIn('Pago M\u00f3vil', display)
        self.assertIn('\U0001f4f1', display)
        self.assertIn('Ref: REF123456', display)

    def test_payment_display_mobile_without_reference(self):
        """Mobile display without reference does NOT include '(Ref:'."""
        sale = Sale.objects.create(
            customer=self.customer,
            user=self.employee1,
            total_bs=Decimal('10.00'),
            total_usd=Decimal('0.27'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='mobile',
            mobile_reference='',
        )
        display = sale.get_payment_method_display_with_icon()
        self.assertNotIn('Ref:', display)
        self.assertIn('Pago M\u00f3vil', display)

    # ── Meta ordering ─────────────────────────────────────────

    def test_default_ordering_is_newest_first(self):
        """Sales are ordered by -date (newest first) by default."""
        sales = list(Sale.objects.all())
        for i in range(len(sales) - 1):
            self.assertGreaterEqual(sales[i].date, sales[i + 1].date)


class SaleItemModelTest(SalesTestSetUpMixin, TestCase):
    """Tests for the SaleItem model."""

    # ── subtotals ─────────────────────────────────────────────

    def test_subtotal_bs(self):
        """subtotal_bs equals quantity * price_bs."""
        item = self.sale_emp1_cash.items.first()
        expected = item.quantity * item.price_bs
        self.assertEqual(item.subtotal_bs, expected)

    def test_subtotal_usd(self):
        """subtotal_usd equals quantity * price_usd."""
        item = self.sale_emp1_cash.items.first()
        expected = item.quantity * item.price_usd
        self.assertEqual(item.subtotal_usd, expected)

    def test_subtotal_alias(self):
        """subtotal property is an alias for subtotal_bs."""
        item = self.sale_emp1_cash.items.first()
        self.assertEqual(item.subtotal, item.subtotal_bs)

    # ── __str__ ───────────────────────────────────────────────

    def test_str_product_item(self):
        """SaleItem __str__ for a product item shows product name and quantity."""
        item = self.sale_emp1_cash.items.filter(product=self.product1).first()
        expected = f"{self.product1.name} - {item.quantity}"
        self.assertEqual(str(item), expected)

    def test_str_combo_item(self):
        """SaleItem __str__ for a combo item shows 'COMBO: <name>' and quantity."""
        item = self.combo_item
        expected = f"COMBO: {self.combo.name} - {item.quantity}"
        self.assertEqual(str(item), expected)

    # ── Meta ordering ─────────────────────────────────────────

    def test_items_ordered_by_id(self):
        """SaleItems are ordered by id by default."""
        items = list(self.sale_emp1_cash.items.all())
        for i in range(len(items) - 1):
            self.assertLess(items[i].id, items[i + 1].id)


# ═══════════════════════════════════════════════════════════════
#  2. VIEW TESTS - ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════

class SaleViewAccessControlTest(SalesTestSetUpMixin, TestCase):
    """Tests for access control on all sales views."""

    # ── Anonymous user redirects to login ─────────────────────

    def test_anonymous_redirected_from_sale_list(self):
        """Anonymous users are redirected to login from sale_list."""
        response = self.client.get(reverse('sales:sale_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_anonymous_redirected_from_sale_create(self):
        """Anonymous users are redirected to login from sale_create."""
        response = self.client.get(reverse('sales:sale_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_anonymous_redirected_from_sale_detail(self):
        """Anonymous users are redirected to login from sale_detail."""
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_anonymous_redirected_from_sale_receipt(self):
        """Anonymous users are redirected to login from sale_receipt."""
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    # ── Normal user gets 403 ──────────────────────────────────

    def test_normal_user_forbidden_sale_list(self):
        """A user with no role gets 403 on sale_list."""
        self.client.login(username='normal_user', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertEqual(response.status_code, 403)

    def test_normal_user_forbidden_sale_create(self):
        """A user with no role gets 403 on sale_create."""
        self.client.login(username='normal_user', password='testpass123')
        response = self.client.get(reverse('sales:sale_create'))
        self.assertEqual(response.status_code, 403)

    def test_normal_user_forbidden_sale_detail(self):
        """A user with no role gets 403 on sale_detail."""
        self.client.login(username='normal_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_normal_user_forbidden_sale_receipt(self):
        """A user with no role gets 403 on sale_receipt."""
        self.client.login(username='normal_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 403)

    # ── Employee is allowed ───────────────────────────────────

    def test_employee_can_access_sale_list(self):
        """An employee gets 200 on sale_list."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertEqual(response.status_code, 200)

    def test_employee_can_access_sale_create(self):
        """An employee gets 200 on sale_create."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(reverse('sales:sale_create'))
        self.assertEqual(response.status_code, 200)

    def test_employee_can_access_own_sale_detail(self):
        """An employee gets 200 on the detail of their own sale."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 200)

    # ── Admin is allowed ──────────────────────────────────────

    def test_admin_can_access_sale_list(self):
        """An admin gets 200 on sale_list."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_sale_create(self):
        """An admin gets 200 on sale_create."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(reverse('sales:sale_create'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_any_sale_detail(self):
        """An admin gets 200 on any sale's detail, even another user's."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_any_sale_receipt(self):
        """An admin gets 200 (PDF) on any sale's receipt."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')


# ═══════════════════════════════════════════════════════════════
#  3. VIEW TESTS - SALE LIST FILTERING & VISIBILITY
# ═══════════════════════════════════════════════════════════════

class SaleListViewTest(SalesTestSetUpMixin, TestCase):
    """Tests for sale_list view filtering and role-based visibility."""

    # ── Employee sees only own sales ──────────────────────────

    def test_employee_sees_only_own_sales(self):
        """Employee1 sees only their own sales, not employee2's."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        page_obj = response.context['page_obj']
        sale_ids = [s.id for s in page_obj]

        # employee1 owns: sale_emp1_cash, sale_emp1_card,
        #                 sale_no_customer, sale_with_combo
        self.assertIn(self.sale_emp1_cash.id, sale_ids)
        self.assertIn(self.sale_emp1_card.id, sale_ids)
        self.assertIn(self.sale_no_customer.id, sale_ids)
        self.assertIn(self.sale_with_combo.id, sale_ids)
        # employee2's sale must NOT appear
        self.assertNotIn(self.sale_emp2_mobile.id, sale_ids)

    def test_employee2_sees_only_own_sales(self):
        """Employee2 sees only their own sale."""
        self.client.login(username='employee2', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        page_obj = response.context['page_obj']
        sale_ids = [s.id for s in page_obj]

        self.assertIn(self.sale_emp2_mobile.id, sale_ids)
        self.assertNotIn(self.sale_emp1_cash.id, sale_ids)
        self.assertNotIn(self.sale_emp1_card.id, sale_ids)

    # ── Admin sees all sales ──────────────────────────────────

    def test_admin_sees_all_sales(self):
        """Admin can see every sale from all employees."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        sales_count = response.context['sales_count']
        self.assertEqual(sales_count, Sale.objects.count())

    def test_admin_context_is_admin_flag(self):
        """Admin gets is_admin=True in context."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertTrue(response.context['is_admin'])

    def test_employee_context_is_admin_flag_false(self):
        """Employee gets is_admin=False in context."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertFalse(response.context['is_admin'])

    # ── Search filter (q) ────────────────────────────────────

    def test_search_by_customer_name(self):
        """Searching by customer name returns matching sales."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_list'), {'q': 'Cliente Test'}
        )
        page_obj = response.context['page_obj']
        for sale in page_obj:
            self.assertIsNotNone(sale.customer)

    def test_search_by_employee_username(self):
        """Searching by employee username filters correctly."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_list'), {'q': 'employee2'}
        )
        page_obj = response.context['page_obj']
        sale_ids = [s.id for s in page_obj]
        self.assertIn(self.sale_emp2_mobile.id, sale_ids)
        self.assertNotIn(self.sale_emp1_cash.id, sale_ids)

    def test_search_by_notes(self):
        """Searching by text in notes filters correctly."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_list'), {'q': 'Pago movil'}
        )
        page_obj = response.context['page_obj']
        sale_ids = [s.id for s in page_obj]
        self.assertIn(self.sale_emp2_mobile.id, sale_ids)

    def test_search_by_sale_id(self):
        """Searching by sale ID returns the matching sale."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_list'), {'q': str(self.sale_emp1_cash.id)}
        )
        page_obj = response.context['page_obj']
        sale_ids = [s.id for s in page_obj]
        self.assertIn(self.sale_emp1_cash.id, sale_ids)

    def test_search_by_employee_first_name(self):
        """Searching by employee first name filters correctly."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_list'), {'q': 'Juan'}
        )
        page_obj = response.context['page_obj']
        for sale in page_obj:
            self.assertEqual(sale.user, self.employee1)

    # ── Credit filter ─────────────────────────────────────────

    def test_credit_filter_credit(self):
        """credit_filter=credit returns only credit sales."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_list'), {'credit_filter': 'credit'}
        )
        page_obj = response.context['page_obj']
        for sale in page_obj:
            self.assertTrue(sale.is_credit)

    def test_credit_filter_cash(self):
        """credit_filter=cash returns only non-credit sales."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_list'), {'credit_filter': 'cash'}
        )
        page_obj = response.context['page_obj']
        for sale in page_obj:
            self.assertFalse(sale.is_credit)

    # ── Date filters ──────────────────────────────────────────

    def test_date_from_filter(self):
        """date_from filter excludes sales before the given date."""
        self.client.login(username='admin_user', password='testpass123')
        tomorrow = (timezone.now() + timedelta(days=1)).date().isoformat()
        response = self.client.get(
            reverse('sales:sale_list'), {'date_from': tomorrow}
        )
        self.assertEqual(response.context['sales_count'], 0)

    def test_date_to_filter(self):
        """date_to filter excludes sales after the given date."""
        self.client.login(username='admin_user', password='testpass123')
        yesterday = (timezone.now() - timedelta(days=1)).date().isoformat()
        response = self.client.get(
            reverse('sales:sale_list'), {'date_to': yesterday}
        )
        self.assertEqual(response.context['sales_count'], 0)

    def test_date_range_includes_today(self):
        """A date range covering today includes today's sales."""
        self.client.login(username='admin_user', password='testpass123')
        today = timezone.now().date().isoformat()
        response = self.client.get(
            reverse('sales:sale_list'),
            {'date_from': today, 'date_to': today},
        )
        self.assertEqual(response.context['sales_count'], Sale.objects.count())

    # ── Totals in context ─────────────────────────────────────

    def test_totals_in_context(self):
        """sale_list provides total_sales and sales_count in context."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertIn('total_sales', response.context)
        self.assertIn('sales_count', response.context)
        self.assertIn('average_sale', response.context)
        self.assertEqual(
            response.context['sales_count'], Sale.objects.count()
        )

    # ── Pagination ────────────────────────────────────────────

    def test_pagination_context(self):
        """sale_list includes a page_obj for pagination."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertIn('page_obj', response.context)


# ═══════════════════════════════════════════════════════════════
#  4. VIEW TESTS - SALE DETAIL
# ═══════════════════════════════════════════════════════════════

class SaleDetailViewTest(SalesTestSetUpMixin, TestCase):
    """Tests for the sale_detail view."""

    def test_employee_sees_own_sale_detail(self):
        """Employee gets 200 when viewing their own sale."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sale'], self.sale_emp1_cash)

    def test_employee_forbidden_from_other_employee_sale(self):
        """Employee gets 403 when viewing another employee's sale."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_sees_any_sale_detail(self):
        """Admin gets 200 when viewing any employee's sale."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sale'], self.sale_emp2_mobile)

    def test_detail_context_includes_items(self):
        """sale_detail context includes the sale's items."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp1_cash.pk])
        )
        items_in_context = list(response.context['items'])
        items_in_db = list(self.sale_emp1_cash.items.all())
        self.assertEqual(items_in_context, items_in_db)

    def test_detail_nonexistent_sale_returns_404(self):
        """Requesting a non-existent sale PK returns 404."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[99999])
        )
        self.assertEqual(response.status_code, 404)


# ═══════════════════════════════════════════════════════════════
#  5. VIEW TESTS - SALE CREATE
# ═══════════════════════════════════════════════════════════════

class SaleCreateViewTest(SalesTestSetUpMixin, TestCase):
    """Tests for the sale_create view."""

    def test_create_view_provides_exchange_rate_in_context(self):
        """sale_create context includes data_for_js with the exchange rate."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(reverse('sales:sale_create'))
        self.assertEqual(response.status_code, 200)
        data_for_js = response.context['data_for_js']
        self.assertIn('exchangeRate', data_for_js)
        self.assertEqual(data_for_js['exchangeRate'], float(Decimal('36.50')))

    def test_create_view_provides_latest_exchange_rate_object(self):
        """sale_create context includes the latest_exchange_rate object."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(reverse('sales:sale_create'))
        self.assertEqual(
            response.context['latest_exchange_rate'], self.exchange_rate
        )

    def test_create_view_no_exchange_rate_defaults_to_one(self):
        """When no exchange rate exists, data_for_js uses 1.0 as default."""
        ExchangeRate.objects.all().delete()
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(reverse('sales:sale_create'))
        data_for_js = response.context['data_for_js']
        self.assertEqual(data_for_js['exchangeRate'], 1.0)


# ═══════════════════════════════════════════════════════════════
#  6. VIEW TESTS - SALE RECEIPT
# ═══════════════════════════════════════════════════════════════

class SaleReceiptViewTest(SalesTestSetUpMixin, TestCase):
    """Tests for the sale_receipt view (PDF generation)."""

    def test_receipt_returns_pdf_content_type(self):
        """sale_receipt returns a response with application/pdf content type."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_receipt_content_disposition(self):
        """sale_receipt sets Content-Disposition with the sale ID."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp1_cash.pk])
        )
        expected_filename = f'recibo_venta_{self.sale_emp1_cash.id}.pdf'
        self.assertIn(expected_filename, response['Content-Disposition'])

    def test_receipt_employee_forbidden_for_other_sale(self):
        """Employee gets 403 when requesting receipt for another's sale."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_receipt_admin_can_generate_any(self):
        """Admin can generate receipt for any sale."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')


# ═══════════════════════════════════════════════════════════════
#  7. EDGE CASES
# ═══════════════════════════════════════════════════════════════

class SaleEdgeCasesTest(SalesTestSetUpMixin, TestCase):
    """Tests for edge cases in the sales app."""

    def test_sale_with_no_customer(self):
        """A sale with customer=None is valid (cash sale, consumidor final)."""
        sale = self.sale_no_customer
        self.assertIsNone(sale.customer)
        # __str__ should still work
        self.assertIn(f'Venta #{sale.id}', str(sale))

    def test_sale_no_exchange_rate_create_view(self):
        """sale_create works even when no ExchangeRate records exist."""
        ExchangeRate.objects.all().delete()
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(reverse('sales:sale_create'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['data_for_js']['exchangeRate'], 1.0)

    def test_item_count_returns_zero_for_empty_sale(self):
        """A sale with no items has item_count == 0."""
        sale = Sale.objects.create(
            customer=None,
            user=self.employee1,
            total_bs=Decimal('0.00'),
            total_usd=Decimal('0.00'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
        )
        self.assertEqual(sale.item_count, 0)

    def test_subtotal_with_fractional_quantity(self):
        """Subtotals are correct when quantity is fractional (e.g. 0.500 kg)."""
        item = SaleItem.objects.create(
            sale=self.sale_no_customer,
            product=self.product1,
            quantity=Decimal('0.500'),
            price_bs=Decimal('100.00'),
            price_usd=Decimal('2.74'),
        )
        self.assertEqual(item.subtotal_bs, Decimal('50.000'))
        self.assertEqual(item.subtotal_usd, Decimal('1.370'))

    def test_sale_with_zero_total(self):
        """A sale with zero totals can be created (e.g. promotional)."""
        sale = Sale.objects.create(
            customer=self.customer,
            user=self.employee1,
            total_bs=Decimal('0.00'),
            total_usd=Decimal('0.00'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
        )
        self.assertEqual(sale.total_bs, Decimal('0.00'))
        self.assertEqual(sale.total_usd, Decimal('0.00'))

    def test_mobile_reference_null(self):
        """A sale with mobile_reference=None works correctly."""
        sale = Sale.objects.create(
            customer=None,
            user=self.employee1,
            total_bs=Decimal('10.00'),
            total_usd=Decimal('0.27'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='mobile',
            mobile_reference=None,
        )
        display = sale.get_payment_method_display_with_icon()
        self.assertNotIn('Ref:', display)

    def test_sale_list_empty_for_new_employee(self):
        """A new employee with no sales sees an empty list."""
        new_emp = User.objects.create_user(
            username='new_employee',
            password='testpass123',
            is_employee=True,
        )
        self.client.login(username='new_employee', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertEqual(response.context['sales_count'], 0)
        self.assertEqual(len(response.context['page_obj'].object_list), 0)


# ═══════════════════════════════════════════════════════════════
#  8. SECURITY TESTS
# ═══════════════════════════════════════════════════════════════

class SaleSecurityTest(SalesTestSetUpMixin, TestCase):
    """Security-focused tests for the sales app."""

    def test_employee_cannot_see_other_employee_sale_detail(self):
        """Employee1 gets 403 when accessing employee2's sale detail."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_see_other_employee_sale_receipt(self):
        """Employee1 gets 403 when accessing employee2's sale receipt."""
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_employee2_cannot_see_employee1_sale_detail(self):
        """Employee2 gets 403 when accessing employee1's sale detail."""
        self.client.login(username='employee2', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_employee2_cannot_see_employee1_sale_receipt(self):
        """Employee2 gets 403 when accessing employee1's sale receipt."""
        self.client.login(username='employee2', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_receipt', args=[self.sale_emp1_cash.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_access_any_view(self):
        """A user with no admin/employee flags gets 403 on all views."""
        self.client.login(username='normal_user', password='testpass123')
        urls = [
            reverse('sales:sale_list'),
            reverse('sales:sale_create'),
            reverse('sales:sale_detail', args=[self.sale_emp1_cash.pk]),
            reverse('sales:sale_receipt', args=[self.sale_emp1_cash.pk]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                403,
                f"Expected 403 for normal_user at {url}, got {response.status_code}",
            )

    def test_employee_list_never_leaks_other_employees_sales(self):
        """
        Even with search filters, employee1 cannot see employee2's sales.
        """
        self.client.login(username='employee1', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_list'), {'q': 'employee2'}
        )
        page_obj = response.context['page_obj']
        sale_ids = [s.id for s in page_obj]
        self.assertNotIn(self.sale_emp2_mobile.id, sale_ids)

    def test_superuser_has_admin_access(self):
        """A superuser can access all sales like an admin."""
        superuser = User.objects.create_superuser(
            username='superadmin',
            password='testpass123',
        )
        self.client.login(username='superadmin', password='testpass123')
        response = self.client.get(reverse('sales:sale_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_admin'])
        self.assertEqual(
            response.context['sales_count'], Sale.objects.count()
        )

    def test_superuser_can_view_any_sale_detail(self):
        """A superuser can view the detail of any sale."""
        superuser = User.objects.create_superuser(
            username='superadmin2',
            password='testpass123',
        )
        self.client.login(username='superadmin2', password='testpass123')
        response = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp2_mobile.pk])
        )
        self.assertEqual(response.status_code, 200)


# ═══════════════════════════════════════════════════════════════
#  9. URL CONFIGURATION TESTS
# ═══════════════════════════════════════════════════════════════

class SaleURLTest(TestCase):
    """Tests for the sales URL configuration."""

    def test_sale_list_url_resolves(self):
        """The sale_list URL resolves correctly."""
        url = reverse('sales:sale_list')
        self.assertEqual(url, '/sales/')

    def test_sale_create_url_resolves(self):
        """The sale_create URL resolves correctly."""
        url = reverse('sales:sale_create')
        self.assertEqual(url, '/sales/new/')

    def test_sale_detail_url_resolves(self):
        """The sale_detail URL resolves correctly with a PK."""
        url = reverse('sales:sale_detail', args=[1])
        self.assertEqual(url, '/sales/1/')

    def test_sale_receipt_url_resolves(self):
        """The sale_receipt URL resolves correctly with a PK."""
        url = reverse('sales:sale_receipt', args=[1])
        self.assertEqual(url, '/sales/1/receipt/')
