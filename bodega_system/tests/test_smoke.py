# tests/test_smoke.py
"""
CAPA 1 — SMOKE TEST
===================
Verifica que NINGUNA URL del sistema retorne HTTP 500.

Detecta automáticamente:
  - Templates rotos o con ruta incorrecta   ({% extends 'base.html' %} vs 'base/base.html')
  - Formularios con model=None              (ValueError: ModelForm has no model class specified)
  - Views con ImportError o AttributeError
  - Cualquier excepción no controlada en una vista

Uso:
  python3 manage.py test tests.test_smoke --verbosity=2

Los resultados muestran "ok" o el URL exacto donde ocurrió el 500.
"""

from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from inventory.models import Category, Product, ProductCombo
from suppliers.models import Supplier, SupplierOrder, SupplierOrderItem, SupplierPayment
from customers.models import Customer, CustomerCredit
from sales.models import Sale, SaleItem
from finances.models import Expense, DailyClose
from utils.models import ExchangeRate

User = get_user_model()


class SmokeTest(TestCase):
    """
    Prueba que ninguna URL del sistema retorne HTTP 500.

    Cada método test_* cubre una URL o grupo de URLs relacionadas.
    Si el test falla, el mensaje indica exactamente qué URL causó el 500.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Crea datos de prueba mínimos para que todas las URLs tengan
        objetos reales a los que apuntar.
        """
        # ── Usuarios ──────────────────────────────────────────────
        cls.admin = User.objects.create_user(
            username='smoke_admin', password='smoke123', is_admin=True
        )
        cls.employee = User.objects.create_user(
            username='smoke_emp', password='smoke123', is_employee=True
        )

        # ── Tasa de cambio ────────────────────────────────────────
        cls.rate = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=cls.admin,
        )

        # ── Inventario ────────────────────────────────────────────
        cls.category = Category.objects.create(name='Smoke Cat')
        cls.product = Product.objects.create(
            name='Smoke Product',
            barcode='SMOKE001',
            category=cls.category,
            purchase_price_usd=Decimal('10.00'),
            purchase_price_bs=Decimal('455.00'),
            selling_price_usd=Decimal('15.00'),
            selling_price_bs=Decimal('682.50'),
            stock=Decimal('100'),
            min_stock=Decimal('5'),
        )
        cls.combo = ProductCombo.objects.create(
            name='Smoke Combo',
            combo_price_bs=Decimal('100.00'),
            is_active=True,
        )

        # ── Proveedores ───────────────────────────────────────────
        cls.supplier = Supplier.objects.create(
            name='Smoke Supplier', is_active=True
        )
        cls.order = SupplierOrder.objects.create(
            supplier=cls.supplier,
            status='pending',
            total_usd=Decimal('100.00'),
            total_bs=Decimal('4550.00'),
            exchange_rate_used=Decimal('45.50'),
            created_by=cls.admin,
        )
        SupplierOrderItem.objects.create(
            order=cls.order,
            product=cls.product,
            quantity=Decimal('10'),
            price_usd=Decimal('10.00'),
            price_bs=Decimal('455.00'),
        )
        cls.payment = SupplierPayment.objects.create(
            order=cls.order,
            amount_usd=Decimal('30.00'),
            payment_date=timezone.now(),
            payment_method='transfer',
            created_by=cls.admin,
        )

        # ── Clientes ──────────────────────────────────────────────
        cls.customer = Customer.objects.create(
            name='Smoke Customer',
            phone='0414000000',
            credit_limit_usd=Decimal('500.00'),
        )

        # ── Venta en efectivo ─────────────────────────────────────
        cls.sale = Sale.objects.create(
            user=cls.admin,
            payment_method='cash',
            total_usd=Decimal('15.00'),
            total_bs=Decimal('682.50'),
            exchange_rate_used=Decimal('45.50'),
            is_credit=False,
        )
        SaleItem.objects.create(
            sale=cls.sale,
            product=cls.product,
            quantity=Decimal('1'),
            price_usd=Decimal('15.00'),
            price_bs=Decimal('682.50'),
        )

        # ── Venta a crédito + CustomerCredit ──────────────────────
        cls.credit_sale = Sale.objects.create(
            user=cls.admin,
            customer=cls.customer,
            payment_method='cash',
            total_usd=Decimal('100.00'),
            total_bs=Decimal('4550.00'),
            exchange_rate_used=Decimal('45.50'),
            is_credit=True,
        )
        cls.credit = CustomerCredit.objects.create(
            customer=cls.customer,
            sale=cls.credit_sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('4550.00'),
            exchange_rate_used=Decimal('45.50'),
            date_due=timezone.now().date() + timedelta(days=30),
        )

        # ── Finanzas ──────────────────────────────────────────────
        cls.expense = Expense.objects.create(
            category='other',
            description='Smoke Expense',
            amount_usd=Decimal('20.00'),
            amount_bs=Decimal('910.00'),
            exchange_rate_used=Decimal('45.50'),
            date=timezone.now().date(),
            created_by=cls.admin,
        )
        cls.daily_close = DailyClose.objects.create(
            date=timezone.now().date(),
            sales_count=1,
            sales_total_bs=Decimal('682.50'),
            expenses_total_bs=Decimal('910.00'),
            profit_bs=Decimal('-227.50'),
            closed_by=cls.admin,
        )

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.client.login(username='smoke_admin', password='smoke123')

    # ──────────────────────────────────────────────────────────────
    # Helper central
    # ──────────────────────────────────────────────────────────────

    def _get(self, url_name, kwargs=None, qs=''):
        """
        Hace GET a la URL y verifica que no retorne 500.
        Retorna el response para aserciones adicionales.
        """
        url = reverse(url_name, kwargs=kwargs or {}) + qs
        self.client.raise_request_exception = False
        response = self.client.get(url)
        self.assertNotEqual(
            response.status_code, 500,
            f"\n⛔ HTTP 500 en {url}\n"
            f"   View: {url_name}\n"
            f"   Esto indica un error no controlado en la vista o template.\n"
        )
        return response

    # ──────────────────────────────────────────────────────────────
    # Dashboard
    # ──────────────────────────────────────────────────────────────

    def test_dashboard(self):
        self._get('dashboard')

    # ──────────────────────────────────────────────────────────────
    # Accounts
    # ──────────────────────────────────────────────────────────────

    def test_accounts_profile(self):
        self._get('accounts:profile')

    def test_accounts_user_list(self):
        self._get('accounts:user_list')

    def test_accounts_user_create(self):
        self._get('accounts:user_create')

    def test_accounts_user_update(self):
        self._get('accounts:user_update', {'pk': self.admin.pk})

    def test_accounts_user_delete(self):
        self._get('accounts:user_delete', {'pk': self.employee.pk})

    # ──────────────────────────────────────────────────────────────
    # Inventory — Productos
    # ──────────────────────────────────────────────────────────────

    def test_inventory_product_list(self):
        self._get('inventory:product_list')

    def test_inventory_product_list_search(self):
        self._get('inventory:product_list', qs='?q=smoke')

    def test_inventory_product_list_filter_low(self):
        self._get('inventory:product_list', qs='?stock=low')

    def test_inventory_product_create(self):
        self._get('inventory:product_create')

    def test_inventory_product_detail(self):
        self._get('inventory:product_detail', {'pk': self.product.pk})

    def test_inventory_product_update(self):
        self._get('inventory:product_update', {'pk': self.product.pk})

    def test_inventory_product_delete(self):
        self._get('inventory:product_delete', {'pk': self.product.pk})

    # ──────────────────────────────────────────────────────────────
    # Inventory — Categorías
    # ──────────────────────────────────────────────────────────────

    def test_inventory_category_list(self):
        self._get('inventory:category_list')

    def test_inventory_category_create(self):
        self._get('inventory:category_create')

    def test_inventory_category_detail(self):
        self._get('inventory:category_detail', {'pk': self.category.pk})

    def test_inventory_category_update(self):
        self._get('inventory:category_update', {'pk': self.category.pk})

    def test_inventory_category_delete(self):
        self._get('inventory:category_delete', {'pk': self.category.pk})

    # ──────────────────────────────────────────────────────────────
    # Inventory — Ajustes y Combos
    # ──────────────────────────────────────────────────────────────

    def test_inventory_adjustment_list(self):
        self._get('inventory:adjustment_list')

    def test_inventory_adjustment_create(self):
        self._get('inventory:adjustment_create')

    def test_inventory_combo_list(self):
        self._get('inventory:combo_list')

    def test_inventory_combo_create(self):
        self._get('inventory:combo_create')

    def test_inventory_combo_detail(self):
        self._get('inventory:combo_detail', {'pk': self.combo.pk})

    def test_inventory_combo_update(self):
        self._get('inventory:combo_update', {'pk': self.combo.pk})

    def test_inventory_combo_delete(self):
        self._get('inventory:combo_delete', {'pk': self.combo.pk})

    # ──────────────────────────────────────────────────────────────
    # Inventory — APIs
    # ──────────────────────────────────────────────────────────────

    def test_api_product_detail(self):
        self._get('inventory:product_detail_api', {'pk': self.product.pk})

    def test_api_product_search(self):
        self._get('inventory:product_search_api', qs='?q=smoke')

    def test_api_product_by_barcode(self):
        self._get('inventory:product_by_barcode_api', {'barcode': self.product.barcode})

    def test_api_product_suggestions(self):
        self._get('inventory:product_suggestions_api', qs='?q=smoke')

    def test_api_product_stock_summary(self):
        self._get('inventory:product_stock_summary_api')

    def test_api_categories_list(self):
        self._get('inventory:categories_list_api')

    def test_api_combo_search(self):
        self._get('inventory:combo_search_api', qs='?q=smoke')

    # ──────────────────────────────────────────────────────────────
    # Customers
    # ──────────────────────────────────────────────────────────────

    def test_customers_list(self):
        self._get('customers:customer_list')

    def test_customers_list_search(self):
        self._get('customers:customer_list', qs='?q=smoke')

    def test_customers_create(self):
        self._get('customers:customer_create')

    def test_customers_detail(self):
        self._get('customers:customer_detail', {'pk': self.customer.pk})

    def test_customers_update(self):
        self._get('customers:customer_update', {'pk': self.customer.pk})

    def test_customers_delete(self):
        self._get('customers:customer_delete', {'pk': self.customer.pk})

    def test_customers_credit_list(self):
        self._get('customers:credit_list')

    def test_customers_credit_create(self):
        self._get('customers:credit_create')

    def test_customers_credit_detail(self):
        self._get('customers:credit_detail', {'pk': self.credit.pk})

    def test_customers_credit_payment_form(self):
        """Formulario para registrar pago de crédito."""
        self._get('customers:credit_payment', {'pk': self.credit.pk})

    # ──────────────────────────────────────────────────────────────
    # Sales
    # ──────────────────────────────────────────────────────────────

    def test_sales_list(self):
        self._get('sales:sale_list')

    def test_sales_list_search(self):
        self._get('sales:sale_list', qs='?q=smoke')

    def test_sales_create_form(self):
        self._get('sales:sale_create')

    def test_sales_detail(self):
        self._get('sales:sale_detail', {'pk': self.sale.pk})

    def test_sales_receipt(self):
        self._get('sales:sale_receipt', {'pk': self.sale.pk})

    # ──────────────────────────────────────────────────────────────
    # Suppliers — Proveedores
    # ──────────────────────────────────────────────────────────────

    def test_suppliers_list(self):
        self._get('suppliers:supplier_list')

    def test_suppliers_create(self):
        self._get('suppliers:supplier_create')

    def test_suppliers_detail(self):
        self._get('suppliers:supplier_detail', {'pk': self.supplier.pk})

    def test_suppliers_update(self):
        self._get('suppliers:supplier_update', {'pk': self.supplier.pk})

    def test_suppliers_delete(self):
        self._get('suppliers:supplier_delete', {'pk': self.supplier.pk})

    # ──────────────────────────────────────────────────────────────
    # Suppliers — Órdenes
    # ──────────────────────────────────────────────────────────────

    def test_suppliers_order_list(self):
        self._get('suppliers:order_list')

    def test_suppliers_order_create(self):
        self._get('suppliers:order_create')

    def test_suppliers_order_detail(self):
        self._get('suppliers:order_detail', {'pk': self.order.pk})

    def test_suppliers_order_update(self):
        self._get('suppliers:order_update', {'pk': self.order.pk})

    def test_suppliers_order_receive(self):
        self._get('suppliers:order_receive', {'pk': self.order.pk})

    # ──────────────────────────────────────────────────────────────
    # Suppliers — Pagos  ⚠️ Aquí detectamos el bug original
    # ──────────────────────────────────────────────────────────────

    def test_suppliers_payment_create_form(self):
        """
        ⚠️ CRÍTICO: Este test hubiera detectado el bug original.
        GET al formulario de pago falla si SupplierPaymentForm.Meta.model = None.
        """
        self._get('suppliers:payment_create', {'order_id': self.order.pk})

    def test_suppliers_payment_list(self):
        self._get('suppliers:payment_list', {'order_id': self.order.pk})

    # ──────────────────────────────────────────────────────────────
    # Suppliers — API
    # ──────────────────────────────────────────────────────────────

    def test_suppliers_product_lookup_found(self):
        self._get('suppliers:product_lookup_api', {'barcode': self.product.barcode})

    def test_suppliers_product_lookup_not_found(self):
        self._get('suppliers:product_lookup_api', {'barcode': 'NOEXISTE999'})

    # ──────────────────────────────────────────────────────────────
    # Finances
    # ──────────────────────────────────────────────────────────────

    def test_finances_dashboard(self):
        self._get('finances:dashboard')

    def test_finances_sales_report(self):
        self._get('finances:sales_report')

    def test_finances_purchases_report(self):
        self._get('finances:purchases_report')

    def test_finances_profits_report(self):
        self._get('finances:profits_report')

    def test_finances_product_profitability(self):
        self._get('finances:product_profitability_report')

    def test_finances_expense_list(self):
        self._get('finances:expense_list')

    def test_finances_expense_create(self):
        self._get('finances:expense_create')

    def test_finances_expense_detail(self):
        self._get('finances:expense_detail', {'pk': self.expense.pk})

    def test_finances_expense_update(self):
        self._get('finances:expense_update', {'pk': self.expense.pk})

    def test_finances_expense_delete(self):
        self._get('finances:expense_delete', {'pk': self.expense.pk})

    def test_finances_daily_close_list(self):
        self._get('finances:daily_close_list')

    def test_finances_daily_close_create(self):
        self._get('finances:daily_close_create')

    def test_finances_daily_close_detail(self):
        self._get('finances:daily_close_detail', {'pk': self.daily_close.pk})

    # ──────────────────────────────────────────────────────────────
    # Utils
    # ──────────────────────────────────────────────────────────────

    def test_utils_exchange_rate(self):
        self._get('utils:exchange_rate_management')

    def test_utils_exchange_rate_history(self):
        self._get('utils:exchange_rate_history')

    def test_utils_backup_index(self):
        self._get('utils:backup_index')

    # ──────────────────────────────────────────────────────────────
    # Analytics / Stats
    # ──────────────────────────────────────────────────────────────

    def test_dashboard_analytics(self):
        self._get('dashboard_analytics')

    def test_my_stats(self):
        self._get('my_stats')

    # ──────────────────────────────────────────────────────────────
    # Performance
    # ──────────────────────────────────────────────────────────────

    def test_performance_dashboard(self):
        self._get('performance:dashboard')
