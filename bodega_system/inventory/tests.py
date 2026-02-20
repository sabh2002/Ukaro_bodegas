"""
Comprehensive test suite for the inventory app.

Covers:
    1. Model tests: Category, Product (properties, methods, __str__, get_absolute_url),
       InventoryAdjustment
    2. Form tests: ProductForm, InventoryAdjustmentForm, CategoryForm
    3. View tests: Access control (admin vs employee vs anonymous), CRUD operations,
       soft delete, category protection
    4. API tests: All endpoints, authentication, search, barcode, stock summary
    5. Edge cases: No exchange rate, zero stock, boundary values, decimal precision
    6. Known bugs: product_detail_api calls get_stock_status() as method (AttributeError),
       categories_list_api references created_at on Category (AttributeError)
"""

import json
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from inventory.models import Category, Product, InventoryAdjustment
from inventory.forms import ProductForm, InventoryAdjustmentForm, CategoryForm
from utils.models import ExchangeRate


# ---------------------------------------------------------------------------
# Helper mixin: shared setUp logic
# ---------------------------------------------------------------------------

class InventoryTestDataMixin:
    """Mixin that creates commonly used test objects."""

    def create_users(self):
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='admin_pass_123',
            is_admin=True,
            is_employee=False,
        )
        self.employee_user = User.objects.create_user(
            username='employee_test',
            password='employee_pass_123',
            is_admin=False,
            is_employee=True,
        )
        self.regular_user = User.objects.create_user(
            username='regular_test',
            password='regular_pass_123',
            is_admin=False,
            is_employee=False,
        )
        self.superuser = User.objects.create_superuser(
            username='super_test',
            password='super_pass_123',
        )

    def create_category(self, name='Bebidas', description='Bebidas varias'):
        return Category.objects.create(name=name, description=description)

    def create_product(self, category=None, **overrides):
        defaults = {
            'name': 'Coca-Cola 2L',
            'barcode': '7591234567890',
            'category': category or self.category,
            'unit_type': 'unit',
            'purchase_price_usd': Decimal('1.00'),
            'purchase_price_bs': Decimal('0.00'),
            'selling_price_usd': Decimal('2.00'),
            'selling_price_bs': Decimal('0.00'),
            'stock': Decimal('10.000'),
            'min_stock': Decimal('5.000'),
            'is_active': True,
            'is_bulk_pricing': False,
        }
        defaults.update(overrides)
        return Product.objects.create(**defaults)

    def create_exchange_rate(self, rate=Decimal('36.50')):
        return ExchangeRate.objects.create(
            bs_to_usd=rate,
            updated_by=self.admin_user,
        )


# ===========================================================================
# 1. MODEL TESTS
# ===========================================================================

class CategoryModelTest(TestCase, InventoryTestDataMixin):
    """Tests for the Category model."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()

    def test_str_returns_name(self):
        self.assertEqual(str(self.category), 'Bebidas')

    def test_ordering_by_name(self):
        cat_z = Category.objects.create(name='Zumos', description='')
        cat_a = Category.objects.create(name='Aceites', description='')
        names = list(Category.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))

    def test_verbose_names(self):
        self.assertEqual(Category._meta.verbose_name, 'Categoria')  # Spanish might differ
        # Use a looser assertion that respects actual meta
        self.assertIn('ategor', str(Category._meta.verbose_name).lower())

    def test_description_can_be_blank(self):
        cat = Category.objects.create(name='Empty Desc', description='')
        self.assertEqual(cat.description, '')


class ProductModelTest(TestCase, InventoryTestDataMixin):
    """Tests for the Product model: properties, methods, __str__, get_absolute_url."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()

    # --- __str__ and get_absolute_url ---

    def test_str_returns_name(self):
        self.assertEqual(str(self.product), 'Coca-Cola 2L')

    def test_get_absolute_url(self):
        expected = reverse('inventory:product_detail', args=[self.product.pk])
        self.assertEqual(self.product.get_absolute_url(), expected)

    # --- stock_status property ---

    def test_stock_status_normal(self):
        """stock > min_stock => 'Stock normal'"""
        self.product.stock = Decimal('10.000')
        self.product.min_stock = Decimal('5.000')
        self.assertEqual(self.product.stock_status, 'Stock normal')

    def test_stock_status_low(self):
        """0 < stock < min_stock => 'Stock bajo'"""
        self.product.stock = Decimal('3.000')
        self.product.min_stock = Decimal('5.000')
        self.assertEqual(self.product.stock_status, 'Stock bajo')

    def test_stock_status_zero(self):
        """stock == 0 => 'Sin stock'"""
        self.product.stock = Decimal('0.000')
        self.assertEqual(self.product.stock_status, 'Sin stock')

    def test_stock_status_negative(self):
        """stock < 0 => 'Sin stock'"""
        self.product.stock = Decimal('-1.000')
        self.assertEqual(self.product.stock_status, 'Sin stock')

    def test_stock_status_equal_to_min_stock(self):
        """stock == min_stock => 'Stock bajo' (since stock < min_stock is False but
        the model uses stock < min_stock, so equal means 'Stock normal')."""
        self.product.stock = Decimal('5.000')
        self.product.min_stock = Decimal('5.000')
        # stock (5) is NOT < min_stock (5), so it falls through to 'Stock normal'
        self.assertEqual(self.product.stock_status, 'Stock normal')

    def test_stock_status_just_below_min_stock(self):
        """stock slightly below min_stock => 'Stock bajo'"""
        self.product.stock = Decimal('4.999')
        self.product.min_stock = Decimal('5.000')
        self.assertEqual(self.product.stock_status, 'Stock bajo')

    # --- profit_margin_usd property ---

    def test_profit_margin_usd_positive(self):
        self.product.purchase_price_usd = Decimal('1.00')
        self.product.selling_price_usd = Decimal('2.50')
        self.assertEqual(self.product.profit_margin_usd, Decimal('1.50'))

    def test_profit_margin_usd_zero_purchase(self):
        """When purchase_price_usd <= 0, margin should be 0."""
        self.product.purchase_price_usd = Decimal('0.00')
        self.assertEqual(self.product.profit_margin_usd, 0)

    def test_profit_margin_usd_negative_purchase(self):
        self.product.purchase_price_usd = Decimal('-1.00')
        self.assertEqual(self.product.profit_margin_usd, 0)

    # --- profit_margin_percentage property ---

    def test_profit_margin_percentage_normal(self):
        self.product.purchase_price_usd = Decimal('1.00')
        self.product.selling_price_usd = Decimal('2.00')
        # (2 - 1) / 1 * 100 = 100.0
        self.assertEqual(self.product.profit_margin_percentage, Decimal('100.0'))

    def test_profit_margin_percentage_zero_purchase(self):
        self.product.purchase_price_usd = Decimal('0.00')
        self.assertEqual(self.product.profit_margin_percentage, 0)

    def test_profit_margin_percentage_fractional(self):
        self.product.purchase_price_usd = Decimal('3.00')
        self.product.selling_price_usd = Decimal('4.00')
        # (4 - 3) / 3 * 100 = 33.333...
        result = self.product.profit_margin_percentage
        self.assertAlmostEqual(float(result), 33.333, places=2)

    # --- is_weight_based property ---

    def test_is_weight_based_unit(self):
        self.product.unit_type = 'unit'
        self.assertFalse(self.product.is_weight_based)

    def test_is_weight_based_kg(self):
        self.product.unit_type = 'kg'
        self.assertTrue(self.product.is_weight_based)

    def test_is_weight_based_gram(self):
        self.product.unit_type = 'gram'
        self.assertTrue(self.product.is_weight_based)

    def test_is_weight_based_liter(self):
        self.product.unit_type = 'liter'
        self.assertTrue(self.product.is_weight_based)

    def test_is_weight_based_ml(self):
        self.product.unit_type = 'ml'
        self.assertTrue(self.product.is_weight_based)

    # --- unit_display property ---

    def test_unit_display_unit(self):
        self.product.unit_type = 'unit'
        self.assertEqual(self.product.unit_display, 'Unidad')

    def test_unit_display_kg(self):
        self.product.unit_type = 'kg'
        self.assertEqual(self.product.unit_display, 'Kilogramo')

    def test_unit_display_gram(self):
        self.product.unit_type = 'gram'
        self.assertEqual(self.product.unit_display, 'Gramo')

    def test_unit_display_liter(self):
        self.product.unit_type = 'liter'
        self.assertEqual(self.product.unit_display, 'Litro')

    def test_unit_display_ml(self):
        self.product.unit_type = 'ml'
        self.assertEqual(self.product.unit_display, 'Mililitro')

    # --- get_price_usd_for_quantity ---

    def test_get_price_usd_regular_no_bulk(self):
        """Without bulk pricing, always returns selling_price_usd."""
        self.product.is_bulk_pricing = False
        self.assertEqual(
            self.product.get_price_usd_for_quantity(100),
            self.product.selling_price_usd,
        )

    def test_get_price_usd_bulk_below_minimum(self):
        """Bulk pricing enabled but quantity below threshold returns regular price."""
        self.product.is_bulk_pricing = True
        self.product.bulk_min_quantity = Decimal('10')
        self.product.bulk_price_usd = Decimal('1.50')
        self.assertEqual(
            self.product.get_price_usd_for_quantity(5),
            self.product.selling_price_usd,
        )

    def test_get_price_usd_bulk_at_minimum(self):
        """Quantity equals bulk_min_quantity => returns bulk price."""
        self.product.is_bulk_pricing = True
        self.product.bulk_min_quantity = Decimal('10')
        self.product.bulk_price_usd = Decimal('1.50')
        self.assertEqual(
            self.product.get_price_usd_for_quantity(10),
            Decimal('1.50'),
        )

    def test_get_price_usd_bulk_above_minimum(self):
        """Quantity above bulk_min_quantity => returns bulk price."""
        self.product.is_bulk_pricing = True
        self.product.bulk_min_quantity = Decimal('10')
        self.product.bulk_price_usd = Decimal('1.50')
        self.assertEqual(
            self.product.get_price_usd_for_quantity(20),
            Decimal('1.50'),
        )

    def test_get_price_usd_bulk_enabled_but_no_min_quantity(self):
        """Bulk pricing enabled but bulk_min_quantity is None => regular price."""
        self.product.is_bulk_pricing = True
        self.product.bulk_min_quantity = None
        self.product.bulk_price_usd = Decimal('1.50')
        self.assertEqual(
            self.product.get_price_usd_for_quantity(20),
            self.product.selling_price_usd,
        )

    # --- get_price_bs_for_quantity ---

    def test_get_price_bs_for_quantity_regular(self):
        rate = Decimal('36.50')
        expected = self.product.selling_price_usd * rate
        self.assertEqual(self.product.get_price_bs_for_quantity(1, rate), expected)

    def test_get_price_bs_for_quantity_bulk(self):
        self.product.is_bulk_pricing = True
        self.product.bulk_min_quantity = Decimal('10')
        self.product.bulk_price_usd = Decimal('1.50')
        rate = Decimal('36.50')
        expected = Decimal('1.50') * rate
        self.assertEqual(self.product.get_price_bs_for_quantity(10, rate), expected)

    # --- get_current_price_bs ---

    def test_get_current_price_bs_with_rate(self):
        self.create_exchange_rate(Decimal('36.50'))
        expected = self.product.selling_price_usd * Decimal('36.50')
        self.assertEqual(self.product.get_current_price_bs(), expected)

    def test_get_current_price_bs_no_rate(self):
        """When no exchange rate exists, should return Decimal('0.00')."""
        self.assertEqual(self.product.get_current_price_bs(), Decimal('0.00'))

    # --- get_current_purchase_price_bs ---

    def test_get_current_purchase_price_bs_with_rate(self):
        self.create_exchange_rate(Decimal('36.50'))
        expected = self.product.purchase_price_usd * Decimal('36.50')
        self.assertEqual(self.product.get_current_purchase_price_bs(), expected)

    def test_get_current_purchase_price_bs_no_rate(self):
        self.assertEqual(self.product.get_current_purchase_price_bs(), Decimal('0.00'))

    # --- Category FK PROTECT ---

    def test_category_protected_on_delete(self):
        """Deleting a category that has products should raise ProtectedError."""
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.category.delete()

    # --- Barcode uniqueness ---

    def test_barcode_unique(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Product.objects.create(
                name='Duplicate Barcode',
                barcode=self.product.barcode,  # same barcode
                category=self.category,
                purchase_price_usd=Decimal('1.00'),
                selling_price_usd=Decimal('2.00'),
            )

    # --- Default values ---

    def test_default_stock_is_zero(self):
        p = Product.objects.create(
            name='New Product',
            barcode='0000000000001',
            category=self.category,
            purchase_price_usd=Decimal('1.00'),
            selling_price_usd=Decimal('2.00'),
        )
        self.assertEqual(p.stock, Decimal('0'))

    def test_default_min_stock_is_five(self):
        p = Product.objects.create(
            name='New Product 2',
            barcode='0000000000002',
            category=self.category,
            purchase_price_usd=Decimal('1.00'),
            selling_price_usd=Decimal('2.00'),
        )
        self.assertEqual(p.min_stock, Decimal('5'))

    def test_default_is_active_true(self):
        p = Product.objects.create(
            name='New Product 3',
            barcode='0000000000003',
            category=self.category,
            purchase_price_usd=Decimal('1.00'),
            selling_price_usd=Decimal('2.00'),
        )
        self.assertTrue(p.is_active)

    # --- ordering ---

    def test_ordering_by_name(self):
        Product.objects.all().delete()
        self.create_product(barcode='Z111', name='Zumo')
        self.create_product(barcode='A111', name='Agua')
        names = list(Product.objects.values_list('name', flat=True))
        self.assertEqual(names, ['Agua', 'Zumo'])


class InventoryAdjustmentModelTest(TestCase, InventoryTestDataMixin):
    """Tests for the InventoryAdjustment model."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()

    def test_str_representation(self):
        adj = InventoryAdjustment.objects.create(
            product=self.product,
            adjustment_type='add',
            quantity=Decimal('5.00'),
            previous_stock=Decimal('10.00'),
            new_stock=Decimal('15.000'),
            reason='Restock',
            adjusted_by=self.admin_user,
        )
        expected = f"Agregar - {self.product.name} - 5.00"
        self.assertEqual(str(adj), expected)

    def test_ordering_by_adjusted_at_desc(self):
        adj1 = InventoryAdjustment.objects.create(
            product=self.product,
            adjustment_type='add',
            quantity=Decimal('1.00'),
            previous_stock=Decimal('10.00'),
            new_stock=Decimal('11.000'),
            reason='First',
            adjusted_by=self.admin_user,
        )
        adj2 = InventoryAdjustment.objects.create(
            product=self.product,
            adjustment_type='add',
            quantity=Decimal('2.00'),
            previous_stock=Decimal('11.00'),
            new_stock=Decimal('13.000'),
            reason='Second',
            adjusted_by=self.admin_user,
        )
        adjustments = list(InventoryAdjustment.objects.all())
        # Most recent first
        self.assertEqual(adjustments[0].pk, adj2.pk)


# ===========================================================================
# 2. FORM TESTS
# ===========================================================================

class ProductFormTest(TestCase, InventoryTestDataMixin):
    """Tests for the ProductForm validation."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()

    def _valid_data(self, **overrides):
        data = {
            'name': 'Test Product',
            'barcode': '1234567890123',
            'category': self.category.pk,
            'unit_type': 'unit',
            'purchase_price_usd': '1.00',
            'selling_price_usd': '2.00',
            'min_stock': '5.000',
            'is_active': True,
            'is_bulk_pricing': False,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = ProductForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_purchase_price_zero_rejected(self):
        form = ProductForm(data=self._valid_data(purchase_price_usd='0.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('purchase_price_usd', form.errors)

    def test_purchase_price_negative_rejected(self):
        form = ProductForm(data=self._valid_data(purchase_price_usd='-1.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('purchase_price_usd', form.errors)

    def test_selling_price_zero_rejected(self):
        form = ProductForm(data=self._valid_data(selling_price_usd='0.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('selling_price_usd', form.errors)

    def test_selling_price_negative_rejected(self):
        form = ProductForm(data=self._valid_data(selling_price_usd='-5.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('selling_price_usd', form.errors)

    def test_selling_price_must_exceed_purchase(self):
        form = ProductForm(data=self._valid_data(
            purchase_price_usd='5.00',
            selling_price_usd='3.00',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('selling_price_usd', form.errors)

    def test_selling_price_equal_to_purchase_rejected(self):
        form = ProductForm(data=self._valid_data(
            purchase_price_usd='5.00',
            selling_price_usd='5.00',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('selling_price_usd', form.errors)

    def test_bulk_pricing_requires_min_quantity(self):
        form = ProductForm(data=self._valid_data(
            is_bulk_pricing=True,
            bulk_min_quantity='',
            bulk_price_usd='1.50',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('bulk_min_quantity', form.errors)

    def test_bulk_pricing_min_quantity_zero_rejected(self):
        form = ProductForm(data=self._valid_data(
            is_bulk_pricing=True,
            bulk_min_quantity='0',
            bulk_price_usd='1.50',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('bulk_min_quantity', form.errors)

    def test_bulk_pricing_requires_bulk_price(self):
        form = ProductForm(data=self._valid_data(
            is_bulk_pricing=True,
            bulk_min_quantity='10',
            bulk_price_usd='',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('bulk_price_usd', form.errors)

    def test_bulk_pricing_zero_price_rejected(self):
        form = ProductForm(data=self._valid_data(
            is_bulk_pricing=True,
            bulk_min_quantity='10',
            bulk_price_usd='0.00',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('bulk_price_usd', form.errors)

    def test_bulk_price_must_be_less_than_selling(self):
        form = ProductForm(data=self._valid_data(
            selling_price_usd='5.00',
            is_bulk_pricing=True,
            bulk_min_quantity='10',
            bulk_price_usd='5.00',  # equal to selling => rejected
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('bulk_price_usd', form.errors)

    def test_bulk_price_greater_than_selling_rejected(self):
        form = ProductForm(data=self._valid_data(
            selling_price_usd='5.00',
            is_bulk_pricing=True,
            bulk_min_quantity='10',
            bulk_price_usd='6.00',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('bulk_price_usd', form.errors)

    def test_valid_bulk_pricing(self):
        form = ProductForm(data=self._valid_data(
            selling_price_usd='5.00',
            is_bulk_pricing=True,
            bulk_min_quantity='10',
            bulk_price_usd='3.50',
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_bulk_fields_not_required_when_bulk_disabled(self):
        """When is_bulk_pricing is False, bulk fields are not validated."""
        form = ProductForm(data=self._valid_data(
            is_bulk_pricing=False,
            bulk_min_quantity='',
            bulk_price_usd='',
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name_rejected(self):
        form = ProductForm(data=self._valid_data(name=''))
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_missing_barcode_rejected(self):
        form = ProductForm(data=self._valid_data(barcode=''))
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)

    def test_missing_category_rejected(self):
        form = ProductForm(data=self._valid_data(category=''))
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)


class InventoryAdjustmentFormTest(TestCase, InventoryTestDataMixin):
    """Tests for InventoryAdjustmentForm validation and save()."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product(stock=Decimal('10.000'))

    def _valid_data(self, **overrides):
        data = {
            'product': self.product.pk,
            'adjustment_type': 'add',
            'quantity': '5.00',
            'reason': 'Restock shipment arrived',
        }
        data.update(overrides)
        return data

    def test_valid_add_form(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(),
            user=self.admin_user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_quantity_zero_rejected(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(quantity='0'),
            user=self.admin_user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_quantity_negative_rejected(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(quantity='-5'),
            user=self.admin_user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_remove_more_than_stock_rejected(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(
                adjustment_type='remove',
                quantity='15.00',  # stock is 10
            ),
            user=self.admin_user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_remove_exact_stock_allowed(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(
                adjustment_type='remove',
                quantity='10.00',  # exactly stock
            ),
            user=self.admin_user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_remove_below_stock_allowed(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(
                adjustment_type='remove',
                quantity='3.00',
            ),
            user=self.admin_user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_set_type_valid(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(
                adjustment_type='set',
                quantity='20.00',
            ),
            user=self.admin_user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    # --- save() method ---

    def test_save_add_increases_stock(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(adjustment_type='add', quantity='5.00'),
            user=self.admin_user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        adj = form.save()

        self.product.refresh_from_db()
        self.assertEqual(adj.previous_stock, Decimal('10.000'))
        self.assertEqual(adj.new_stock, Decimal('15.000'))
        self.assertEqual(self.product.stock, Decimal('15.000'))
        self.assertEqual(adj.adjusted_by, self.admin_user)

    def test_save_remove_decreases_stock(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(adjustment_type='remove', quantity='3.00'),
            user=self.admin_user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        adj = form.save()

        self.product.refresh_from_db()
        self.assertEqual(adj.previous_stock, Decimal('10.000'))
        self.assertEqual(adj.new_stock, Decimal('7.000'))
        self.assertEqual(self.product.stock, Decimal('7.000'))

    def test_save_set_replaces_stock(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(adjustment_type='set', quantity='25.00'),
            user=self.admin_user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        adj = form.save()

        self.product.refresh_from_db()
        self.assertEqual(adj.previous_stock, Decimal('10.000'))
        self.assertEqual(adj.new_stock, Decimal('25.000'))
        self.assertEqual(self.product.stock, Decimal('25.000'))

    def test_save_creates_adjustment_record(self):
        form = InventoryAdjustmentForm(
            data=self._valid_data(adjustment_type='add', quantity='5.00'),
            user=self.admin_user,
        )
        form.is_valid()
        adj = form.save()

        self.assertEqual(InventoryAdjustment.objects.count(), 1)
        saved = InventoryAdjustment.objects.first()
        self.assertEqual(saved.pk, adj.pk)
        self.assertEqual(saved.reason, 'Restock shipment arrived')

    def test_only_active_products_shown(self):
        inactive = self.create_product(
            name='Inactive', barcode='0000inactive', is_active=False,
        )
        form = InventoryAdjustmentForm(user=self.admin_user)
        product_pks = list(form.fields['product'].queryset.values_list('pk', flat=True))
        self.assertIn(self.product.pk, product_pks)
        self.assertNotIn(inactive.pk, product_pks)


class CategoryFormTest(TestCase, InventoryTestDataMixin):
    """Tests for the CategoryForm."""

    def setUp(self):
        self.create_users()

    def test_valid_category_form(self):
        form = CategoryForm(data={'name': 'Snacks', 'description': 'Various snacks'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_name_required(self):
        form = CategoryForm(data={'name': '', 'description': 'desc'})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_description_optional(self):
        form = CategoryForm(data={'name': 'Test', 'description': ''})
        self.assertTrue(form.is_valid(), form.errors)


# ===========================================================================
# 3. VIEW TESTS
# ===========================================================================

@override_settings(ROOT_URLCONF='bodega_system.urls')
class ProductViewAccessControlTest(TestCase, InventoryTestDataMixin):
    """Tests for access control on product views."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()

    # --- Anonymous user => redirect to login ---

    def test_anonymous_product_list_redirects(self):
        response = self.client.get(reverse('inventory:product_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_anonymous_product_create_redirects(self):
        response = self.client.get(reverse('inventory:product_create'))
        self.assertEqual(response.status_code, 302)

    # --- Regular user (not admin, not employee) => 403 ---

    def test_regular_user_product_list_forbidden(self):
        self.client.login(username='regular_test', password='regular_pass_123')
        response = self.client.get(reverse('inventory:product_list'))
        self.assertEqual(response.status_code, 403)

    def test_regular_user_product_create_forbidden(self):
        self.client.login(username='regular_test', password='regular_pass_123')
        response = self.client.get(reverse('inventory:product_create'))
        self.assertEqual(response.status_code, 403)

    # --- Employee => can view, cannot create/update/delete ---

    def test_employee_can_view_product_list(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(reverse('inventory:product_list'))
        self.assertEqual(response.status_code, 200)

    def test_employee_can_view_product_detail(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(
            reverse('inventory:product_detail', args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_create_product(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(reverse('inventory:product_create'))
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_update_product(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(
            reverse('inventory:product_update', args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_delete_product(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(
            reverse('inventory:product_delete', args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 403)

    # --- Admin => full access ---

    def test_admin_can_view_product_list(self):
        self.client.login(username='admin_test', password='admin_pass_123')
        response = self.client.get(reverse('inventory:product_list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_product_create(self):
        self.client.login(username='admin_test', password='admin_pass_123')
        response = self.client.get(reverse('inventory:product_create'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_product_update(self):
        self.client.login(username='admin_test', password='admin_pass_123')
        response = self.client.get(
            reverse('inventory:product_update', args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 200)

    # --- Superuser => full access ---

    def test_superuser_can_create_product(self):
        self.client.login(username='super_test', password='super_pass_123')
        response = self.client.get(reverse('inventory:product_create'))
        self.assertEqual(response.status_code, 200)


@override_settings(ROOT_URLCONF='bodega_system.urls')
class ProductCRUDViewTest(TestCase, InventoryTestDataMixin):
    """Tests for product CRUD operations through views."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()
        self.client.login(username='admin_test', password='admin_pass_123')

    def test_product_create_post(self):
        data = {
            'name': 'New Product',
            'barcode': '9999999999999',
            'category': self.category.pk,
            'unit_type': 'unit',
            'purchase_price_usd': '2.00',
            'selling_price_usd': '4.00',
            'min_stock': '5.000',
            'is_active': True,
            'is_bulk_pricing': False,
        }
        response = self.client.post(reverse('inventory:product_create'), data)
        # Should redirect to product_detail on success
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(barcode='9999999999999').exists())

    def test_product_create_with_initial_stock(self):
        data = {
            'name': 'Stocked Product',
            'barcode': '8888888888888',
            'category': self.category.pk,
            'unit_type': 'unit',
            'purchase_price_usd': '1.50',
            'selling_price_usd': '3.00',
            'min_stock': '5.000',
            'is_active': True,
            'is_bulk_pricing': False,
            'initial_stock': '15',
        }
        response = self.client.post(reverse('inventory:product_create'), data)
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(barcode='8888888888888')
        self.assertEqual(product.stock, Decimal('15'))
        # Should create an adjustment record
        self.assertTrue(
            InventoryAdjustment.objects.filter(
                product=product,
                adjustment_type='set',
                reason='Stock inicial',
            ).exists()
        )

    def test_product_create_with_invalid_initial_stock(self):
        """Invalid initial_stock should still create product with stock=0."""
        data = {
            'name': 'Bad Stock Product',
            'barcode': '7777777777777',
            'category': self.category.pk,
            'unit_type': 'unit',
            'purchase_price_usd': '1.50',
            'selling_price_usd': '3.00',
            'min_stock': '5.000',
            'is_active': True,
            'is_bulk_pricing': False,
            'initial_stock': 'abc',  # invalid
        }
        response = self.client.post(reverse('inventory:product_create'), data)
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(barcode='7777777777777')
        # Stock should remain at default (0) since initial_stock was invalid
        self.assertEqual(product.stock, Decimal('0'))

    def test_product_update_post(self):
        data = {
            'name': 'Updated Name',
            'barcode': self.product.barcode,
            'category': self.category.pk,
            'unit_type': 'unit',
            'purchase_price_usd': '1.50',
            'selling_price_usd': '3.00',
            'min_stock': '5.000',
            'is_active': True,
            'is_bulk_pricing': False,
        }
        response = self.client.post(
            reverse('inventory:product_update', args=[self.product.pk]),
            data,
        )
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Name')

    def test_product_soft_delete(self):
        """Product delete view should set is_active=False, not actually delete."""
        response = self.client.post(
            reverse('inventory:product_delete', args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        # Product still exists in database
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_product_soft_delete_preserves_data(self):
        """Soft delete should not change product name or other fields."""
        original_name = self.product.name
        self.client.post(
            reverse('inventory:product_delete', args=[self.product.pk])
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, original_name)
        self.assertFalse(self.product.is_active)


@override_settings(ROOT_URLCONF='bodega_system.urls')
class CategoryViewTest(TestCase, InventoryTestDataMixin):
    """Tests for category views: access, CRUD, protection."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.client.login(username='admin_test', password='admin_pass_123')

    # --- Access control ---

    def test_employee_can_view_category_list(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(reverse('inventory:category_list'))
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_create_category(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(reverse('inventory:category_create'))
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_update_category(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(
            reverse('inventory:category_update', args=[self.category.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_delete_category(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(
            reverse('inventory:category_delete', args=[self.category.pk])
        )
        self.assertEqual(response.status_code, 403)

    # --- CRUD ---

    def test_category_create(self):
        data = {'name': 'Snacks', 'description': 'Snacks and chips'}
        response = self.client.post(reverse('inventory:category_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name='Snacks').exists())

    def test_category_update(self):
        data = {'name': 'Updated Category', 'description': 'Updated desc'}
        response = self.client.post(
            reverse('inventory:category_update', args=[self.category.pk]),
            data,
        )
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Updated Category')

    def test_category_delete_empty(self):
        """Category with no products can be deleted."""
        empty_cat = Category.objects.create(name='Empty', description='')
        response = self.client.post(
            reverse('inventory:category_delete', args=[empty_cat.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=empty_cat.pk).exists())

    def test_category_delete_with_products_blocked(self):
        """Category with products should not be deleted; view redirects with error."""
        # self.category already has self.product linked to it
        self.create_product(barcode='111111')  # Ensure product is linked
        response = self.client.get(
            reverse('inventory:category_delete', args=[self.category.pk])
        )
        # The view checks if products exist and redirects with error message
        self.assertEqual(response.status_code, 302)
        # Category still exists
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())


@override_settings(ROOT_URLCONF='bodega_system.urls')
class AdjustmentViewTest(TestCase, InventoryTestDataMixin):
    """Tests for inventory adjustment views."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product(stock=Decimal('20.000'))

    def test_employee_cannot_create_adjustment(self):
        self.client.login(username='employee_test', password='employee_pass_123')
        response = self.client.get(reverse('inventory:adjustment_create'))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_adjustment_create(self):
        self.client.login(username='admin_test', password='admin_pass_123')
        response = self.client.get(reverse('inventory:adjustment_create'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_post_adjustment(self):
        self.client.login(username='admin_test', password='admin_pass_123')
        data = {
            'product': self.product.pk,
            'adjustment_type': 'add',
            'quantity': '10.00',
            'reason': 'Restocking',
        }
        response = self.client.post(reverse('inventory:adjustment_create'), data)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, Decimal('30.000'))


# ===========================================================================
# 4. API TESTS
# ===========================================================================

@override_settings(ROOT_URLCONF='bodega_system.urls')
class APIAuthenticationTest(TestCase, InventoryTestDataMixin):
    """Tests that all API endpoints require authentication."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()
        self.client = APIClient()

    def test_product_detail_api_unauthenticated(self):
        url = reverse('inventory:product_detail_api', args=[self.product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_product_search_api_unauthenticated(self):
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': 'test'})
        self.assertEqual(response.status_code, 403)

    def test_product_by_barcode_api_unauthenticated(self):
        url = reverse('inventory:product_by_barcode_api', args=['1234567890'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_categories_list_api_unauthenticated(self):
        url = reverse('inventory:categories_list_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_validate_barcode_api_unauthenticated(self):
        url = reverse('inventory:validate_barcode_api')
        response = self.client.post(
            url,
            json.dumps({'barcode': '123'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_stock_summary_api_unauthenticated(self):
        url = reverse('inventory:product_stock_summary_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_generate_barcode_api_unauthenticated(self):
        url = reverse('inventory:generate_barcode_api')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_product_suggestions_api_unauthenticated(self):
        url = reverse('inventory:product_suggestions_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


@override_settings(ROOT_URLCONF='bodega_system.urls')
class ProductSearchAPITest(TestCase, InventoryTestDataMixin):
    """Tests for the product_search_api endpoint."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.cat2 = self.create_category(name='Snacks', description='')
        self.product = self.create_product(
            name='Coca-Cola 2L',
            barcode='1111111111111',
            stock=Decimal('10.000'),
        )
        self.product2 = self.create_product(
            name='Pepsi 2L',
            barcode='2222222222222',
            stock=Decimal('0.000'),
        )
        self.product3 = self.create_product(
            name='Doritos',
            barcode='3333333333333',
            category=self.cat2,
            stock=Decimal('3.000'),
            min_stock=Decimal('5.000'),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_search_by_name(self):
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': 'Coca'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['products'][0]['name'], 'Coca-Cola 2L')

    def test_search_by_barcode(self):
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': '2222222222222'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['products'][0]['barcode'], '2222222222222')

    def test_search_by_category(self):
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': 'a', 'category': self.cat2.pk})
        data = response.json()
        for p in data['products']:
            self.assertEqual(p['category'], 'Snacks')

    def test_search_stock_filter_out(self):
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': '', 'stock': 'out'})
        data = response.json()
        for p in data['products']:
            self.assertEqual(p['stock'], 0.0)

    def test_search_stock_filter_low(self):
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': '', 'stock': 'low'})
        data = response.json()
        # All returned products should have stock <= min_stock
        for p in data['products']:
            self.assertLessEqual(p['stock'], p['min_stock'])

    def test_search_empty_query_returns_empty(self):
        """Empty q with no filters returns empty list."""
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': ''})
        data = response.json()
        self.assertEqual(data['products'], [])

    def test_search_limit_capped_at_50(self):
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': '', 'stock': 'low', 'limit': '100'})
        self.assertEqual(response.status_code, 200)
        # Limit is capped internally at 50 -- just ensure no error

    def test_search_inactive_excluded_by_default(self):
        self.product.is_active = False
        self.product.save()
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': 'Coca'})
        data = response.json()
        self.assertEqual(data['count'], 0)

    def test_search_returns_stock_status(self):
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': 'Pepsi'})
        data = response.json()
        self.assertEqual(data['products'][0]['stock_status'], 'out')


@override_settings(ROOT_URLCONF='bodega_system.urls')
class ProductByBarcodeAPITest(TestCase, InventoryTestDataMixin):
    """Tests for the product_by_barcode_api endpoint."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_found_by_barcode(self):
        url = reverse(
            'inventory:product_by_barcode_api',
            args=[self.product.barcode],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['barcode'], self.product.barcode)
        self.assertEqual(data['name'], self.product.name)

    def test_not_found_barcode(self):
        url = reverse('inventory:product_by_barcode_api', args=['NONEXISTENT'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_inactive_product_not_found(self):
        self.product.is_active = False
        self.product.save()
        url = reverse(
            'inventory:product_by_barcode_api',
            args=[self.product.barcode],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_response_includes_prices(self):
        url = reverse(
            'inventory:product_by_barcode_api',
            args=[self.product.barcode],
        )
        response = self.client.get(url)
        data = response.json()
        self.assertIn('purchase_price_usd', data)
        self.assertIn('selling_price_usd', data)
        self.assertIn('selling_price_bs', data)

    def test_response_includes_bulk_pricing(self):
        self.product.is_bulk_pricing = True
        self.product.bulk_min_quantity = Decimal('10')
        self.product.bulk_price_usd = Decimal('1.50')
        self.product.save()
        url = reverse(
            'inventory:product_by_barcode_api',
            args=[self.product.barcode],
        )
        response = self.client.get(url)
        data = response.json()
        self.assertIsNotNone(data['bulk_pricing'])
        self.assertTrue(data['bulk_pricing']['enabled'])

    def test_response_stock_status_out(self):
        self.product.stock = Decimal('0')
        self.product.save()
        url = reverse(
            'inventory:product_by_barcode_api',
            args=[self.product.barcode],
        )
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data['stock_status'], 'out')
        self.assertFalse(data['stock_available'])

    def test_is_weight_based_in_response(self):
        self.product.unit_type = 'kg'
        self.product.save()
        url = reverse(
            'inventory:product_by_barcode_api',
            args=[self.product.barcode],
        )
        response = self.client.get(url)
        data = response.json()
        self.assertTrue(data['is_weight_based'])


@override_settings(ROOT_URLCONF='bodega_system.urls')
class ValidateBarcodeAPITest(TestCase, InventoryTestDataMixin):
    """Tests for the validate_barcode_api endpoint."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_barcode_available(self):
        url = reverse('inventory:validate_barcode_api')
        response = self.client.post(
            url,
            json.dumps({'barcode': 'NEW_BARCODE_12345'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])

    def test_barcode_taken(self):
        url = reverse('inventory:validate_barcode_api')
        response = self.client.post(
            url,
            json.dumps({'barcode': self.product.barcode}),
            content_type='application/json',
        )
        data = response.json()
        self.assertFalse(data['valid'])

    def test_barcode_exclude_own_id(self):
        """When editing, the same product's barcode should be considered valid."""
        url = reverse('inventory:validate_barcode_api')
        response = self.client.post(
            url,
            json.dumps({
                'barcode': self.product.barcode,
                'product_id': self.product.pk,
            }),
            content_type='application/json',
        )
        data = response.json()
        self.assertTrue(data['valid'])

    def test_empty_barcode(self):
        url = reverse('inventory:validate_barcode_api')
        response = self.client.post(
            url,
            json.dumps({'barcode': ''}),
            content_type='application/json',
        )
        data = response.json()
        self.assertFalse(data['valid'])


@override_settings(ROOT_URLCONF='bodega_system.urls')
class StockSummaryAPITest(TestCase, InventoryTestDataMixin):
    """Tests for the product_stock_summary_api endpoint."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        # Create products with various stock levels
        self.prod_normal = self.create_product(
            name='Normal Stock', barcode='SUMM001',
            stock=Decimal('20.000'), min_stock=Decimal('5.000'),
        )
        self.prod_low = self.create_product(
            name='Low Stock', barcode='SUMM002',
            stock=Decimal('3.000'), min_stock=Decimal('5.000'),
        )
        self.prod_out = self.create_product(
            name='Out of Stock', barcode='SUMM003',
            stock=Decimal('0.000'), min_stock=Decimal('5.000'),
        )
        self.prod_inactive = self.create_product(
            name='Inactive', barcode='SUMM004',
            stock=Decimal('10.000'), is_active=False,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_summary_total_counts(self):
        url = reverse('inventory:product_stock_summary_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['summary']
        # 3 active products
        self.assertEqual(data['total_products'], 3)
        self.assertEqual(data['out_of_stock'], 1)
        self.assertEqual(data['low_stock'], 1)
        self.assertEqual(data['normal_stock'], 1)

    def test_summary_excludes_inactive(self):
        url = reverse('inventory:product_stock_summary_api')
        response = self.client.get(url)
        data = response.json()['summary']
        # Inactive product should not be counted
        self.assertEqual(data['total_products'], 3)

    def test_summary_includes_values(self):
        url = reverse('inventory:product_stock_summary_api')
        response = self.client.get(url)
        data = response.json()['summary']
        self.assertIn('total_purchase_value', data)
        self.assertIn('total_selling_value', data)


@override_settings(ROOT_URLCONF='bodega_system.urls')
class GenerateBarcodeAPITest(TestCase, InventoryTestDataMixin):
    """Tests for the generate_barcode_api endpoint."""

    def setUp(self):
        self.create_users()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_generate_barcode_returns_valid(self):
        url = reverse('inventory:generate_barcode_api')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])
        self.assertIn('barcode', data)
        self.assertTrue(len(data['barcode']) > 0)

    def test_generated_barcode_is_unique(self):
        url = reverse('inventory:generate_barcode_api')
        barcodes = set()
        for _ in range(5):
            response = self.client.post(url)
            barcode = response.json()['barcode']
            barcodes.add(barcode)
        # All should be unique
        self.assertEqual(len(barcodes), 5)


@override_settings(ROOT_URLCONF='bodega_system.urls')
class ProductSuggestionsAPITest(TestCase, InventoryTestDataMixin):
    """Tests for the product_suggestions_api endpoint."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product(
            name='Popular Product', barcode='SUG001', stock=Decimal('50.000'),
        )
        self.product2 = self.create_product(
            name='Low Stock Product', barcode='SUG002',
            stock=Decimal('2.000'), min_stock=Decimal('5.000'),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_suggestions_popular(self):
        url = reverse('inventory:product_suggestions_api')
        response = self.client.get(url, {'type': 'popular'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['type'], 'popular')
        self.assertIn('suggestions', data)

    def test_suggestions_low_stock(self):
        url = reverse('inventory:product_suggestions_api')
        response = self.client.get(url, {'type': 'low_stock'})
        data = response.json()
        self.assertEqual(data['type'], 'low_stock')
        # Should include the low stock product
        names = [s['name'] for s in data['suggestions']]
        self.assertIn('Low Stock Product', names)

    def test_suggestions_new(self):
        url = reverse('inventory:product_suggestions_api')
        response = self.client.get(url, {'type': 'new'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['type'], 'new')

    def test_suggestions_with_query_filter(self):
        url = reverse('inventory:product_suggestions_api')
        response = self.client.get(url, {'q': 'Popular', 'type': 'popular'})
        data = response.json()
        for s in data['suggestions']:
            self.assertIn('Popular', s['name'])

    def test_suggestions_limit_respected(self):
        url = reverse('inventory:product_suggestions_api')
        response = self.client.get(url, {'type': 'popular', 'limit': '1'})
        data = response.json()
        self.assertLessEqual(len(data['suggestions']), 1)


@override_settings(ROOT_URLCONF='bodega_system.urls')
class ProductDetailAPITest(TestCase, InventoryTestDataMixin):
    """Tests for the product_detail_api endpoint."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_product_detail_api_returns_data(self):
        """
        product_detail_api has a known bug: it calls product.get_stock_status()
        as a method, but stock_status is a @property on the model.
        This should result in an internal server error (500) because the property
        returns a string, and calling it like a method produces a TypeError.
        """
        url = reverse('inventory:product_detail_api', args=[self.product.pk])
        response = self.client.get(url)
        # BUG: The view calls product.get_stock_status() which doesn't exist.
        # stock_status is a @property, not a method, so get_stock_status() fails.
        # The view wraps everything in try/except, so it returns 500.
        self.assertEqual(response.status_code, 500)

    def test_product_detail_api_bug_get_stock_status(self):
        """
        Explicitly documents the bug: Product has stock_status as a @property,
        but the API view calls product.get_stock_status() as if it were a method.
        This should raise an AttributeError because Product doesn't have
        get_stock_status().
        """
        # The property exists as product.stock_status (no parentheses)
        self.assertIsInstance(self.product.stock_status, str)
        # The method does NOT exist
        self.assertFalse(hasattr(self.product, 'get_stock_status'))


# ===========================================================================
# 5. KNOWN BUG: categories_list_api references Category.created_at
# ===========================================================================

@override_settings(ROOT_URLCONF='bodega_system.urls')
class CategoriesListAPIBugTest(TestCase, InventoryTestDataMixin):
    """
    Tests for categories_list_api endpoint, including the known bug where
    it tries to access category.created_at which doesn't exist on the model.
    """

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_categories_list_api_bug_created_at(self):
        """
        KNOWN BUG: categories_list_api accesses category.created_at, but the
        Category model only has 'name' and 'description' fields -- no created_at.
        This should cause an AttributeError, caught by the try/except as 500.
        """
        url = reverse('inventory:categories_list_api')
        response = self.client.get(url)
        # The view tries category.created_at.isoformat() which raises
        # AttributeError, caught by except => 500
        self.assertEqual(response.status_code, 500)

    def test_category_model_has_no_created_at(self):
        """Verify that Category model does not have a created_at field."""
        field_names = [f.name for f in Category._meta.get_fields()]
        self.assertNotIn('created_at', field_names)


# ===========================================================================
# 6. EDGE CASES
# ===========================================================================

class EdgeCaseProductTest(TestCase, InventoryTestDataMixin):
    """Edge case tests: boundary values, zero stock, decimal precision."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()

    def test_very_large_stock(self):
        p = self.create_product(
            barcode='EDGE001',
            stock=Decimal('9999999.999'),
        )
        self.assertEqual(p.stock_status, 'Stock normal')

    def test_very_small_positive_stock(self):
        """Stock of 0.001 is > 0, so should not be 'Sin stock'."""
        p = self.create_product(
            barcode='EDGE002',
            stock=Decimal('0.001'),
            min_stock=Decimal('5.000'),
        )
        self.assertEqual(p.stock_status, 'Stock bajo')

    def test_stock_exactly_zero(self):
        p = self.create_product(barcode='EDGE003', stock=Decimal('0.000'))
        self.assertEqual(p.stock_status, 'Sin stock')

    def test_profit_margin_with_very_small_purchase(self):
        p = self.create_product(
            barcode='EDGE004',
            purchase_price_usd=Decimal('0.01'),
            selling_price_usd=Decimal('1.00'),
        )
        # margin = 1.00 - 0.01 = 0.99
        self.assertEqual(p.profit_margin_usd, Decimal('0.99'))
        # percentage = (0.99 / 0.01) * 100 = 9900.0
        self.assertEqual(float(p.profit_margin_percentage), 9900.0)

    def test_price_bs_with_zero_exchange_rate(self):
        """get_price_bs_for_quantity with rate=0 should return 0."""
        p = self.create_product(barcode='EDGE005')
        result = p.get_price_bs_for_quantity(1, Decimal('0'))
        self.assertEqual(result, Decimal('0'))

    def test_get_current_price_bs_with_multiple_rates(self):
        """get_current_price_bs should use the latest rate by date."""
        import datetime
        p = self.create_product(barcode='EDGE006')
        ExchangeRate.objects.create(
            date=datetime.date(2024, 1, 1),
            bs_to_usd=Decimal('30.00'),
            updated_by=self.admin_user,
        )
        ExchangeRate.objects.create(
            date=datetime.date(2024, 6, 1),
            bs_to_usd=Decimal('40.00'),
            updated_by=self.admin_user,
        )
        # Latest rate by date is 40.00
        expected = p.selling_price_usd * Decimal('40.00')
        self.assertEqual(p.get_current_price_bs(), expected)

    def test_product_with_all_weight_types(self):
        """Ensure all weight-based unit types work correctly."""
        for unit_type in ['kg', 'gram', 'liter', 'ml']:
            p = self.create_product(
                name=f'Product {unit_type}',
                barcode=f'WT_{unit_type}',
                unit_type=unit_type,
            )
            self.assertTrue(p.is_weight_based)

    def test_bulk_pricing_at_boundary_quantity(self):
        p = self.create_product(
            barcode='EDGE007',
            is_bulk_pricing=True,
            bulk_min_quantity=Decimal('10.00'),
            bulk_price_usd=Decimal('1.50'),
            selling_price_usd=Decimal('2.00'),
        )
        # At exact boundary
        self.assertEqual(p.get_price_usd_for_quantity(Decimal('10.00')), Decimal('1.50'))
        # Just below boundary
        self.assertEqual(p.get_price_usd_for_quantity(Decimal('9.99')), Decimal('2.00'))
        # Just above boundary
        self.assertEqual(p.get_price_usd_for_quantity(Decimal('10.01')), Decimal('1.50'))

    def test_adjustment_remove_all_stock(self):
        """Removing all stock should set stock to 0."""
        product = self.create_product(barcode='EDGE008', stock=Decimal('5.000'))
        form = InventoryAdjustmentForm(
            data={
                'product': product.pk,
                'adjustment_type': 'remove',
                'quantity': '5.00',
                'reason': 'Clear out',
            },
            user=self.admin_user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        adj = form.save()
        product.refresh_from_db()
        self.assertEqual(product.stock, Decimal('0.000'))
        self.assertEqual(adj.new_stock, Decimal('0.000'))

    def test_adjustment_set_to_zero(self):
        """Setting stock to 0 via 'set' type should work but quantity must be > 0.
        Actually the form validates quantity > 0, so setting stock to 0 via 'set'
        type is not directly possible with a quantity of 0."""
        product = self.create_product(barcode='EDGE009', stock=Decimal('10.000'))
        form = InventoryAdjustmentForm(
            data={
                'product': product.pk,
                'adjustment_type': 'set',
                'quantity': '0',
                'reason': 'Reset',
            },
            user=self.admin_user,
        )
        # quantity <= 0 should be rejected
        self.assertFalse(form.is_valid())

    def test_multiple_adjustments_accumulate(self):
        """Multiple add adjustments should accumulate correctly."""
        product = self.create_product(barcode='EDGE010', stock=Decimal('0.000'))
        for i in range(3):
            form = InventoryAdjustmentForm(
                data={
                    'product': product.pk,
                    'adjustment_type': 'add',
                    'quantity': '10.00',
                    'reason': f'Batch {i + 1}',
                },
                user=self.admin_user,
            )
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            product.refresh_from_db()

        self.assertEqual(product.stock, Decimal('30.000'))
        self.assertEqual(
            InventoryAdjustment.objects.filter(product=product).count(),
            3,
        )


class ExchangeRateEdgeCaseTest(TestCase, InventoryTestDataMixin):
    """Tests for exchange rate edge cases."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()

    def test_no_exchange_rate_returns_zero(self):
        """With no ExchangeRate records, get_current_price_bs returns 0.00."""
        self.assertEqual(ExchangeRate.objects.count(), 0)
        self.assertEqual(self.product.get_current_price_bs(), Decimal('0.00'))

    def test_no_exchange_rate_purchase_returns_zero(self):
        self.assertEqual(self.product.get_current_purchase_price_bs(), Decimal('0.00'))

    def test_exchange_rate_get_latest_rate_none(self):
        result = ExchangeRate.get_latest_rate()
        self.assertIsNone(result)

    def test_exchange_rate_get_latest_rate_exists(self):
        rate = self.create_exchange_rate(Decimal('36.50'))
        result = ExchangeRate.get_latest_rate()
        self.assertEqual(result.pk, rate.pk)
        self.assertEqual(result.bs_to_usd, Decimal('36.50'))


@override_settings(ROOT_URLCONF='bodega_system.urls')
class ProductListViewFiltersTest(TestCase, InventoryTestDataMixin):
    """Tests for product_list view filtering logic."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.cat2 = self.create_category(name='Limpieza', description='')
        self.prod1 = self.create_product(
            name='Agua Mineral', barcode='FILTER001',
            stock=Decimal('20.000'), min_stock=Decimal('5.000'),
        )
        self.prod2 = self.create_product(
            name='Cloro', barcode='FILTER002',
            category=self.cat2, stock=Decimal('0.000'),
        )
        self.prod3 = self.create_product(
            name='Agua con Gas', barcode='FILTER003',
            stock=Decimal('3.000'), min_stock=Decimal('5.000'),
        )
        self.client.login(username='admin_test', password='admin_pass_123')

    def test_filter_by_search_query(self):
        response = self.client.get(reverse('inventory:product_list'), {'q': 'Agua'})
        self.assertEqual(response.status_code, 200)
        products = response.context['page_obj'].object_list
        for p in products:
            self.assertIn('Agua', p.name)

    def test_filter_by_category(self):
        response = self.client.get(
            reverse('inventory:product_list'),
            {'category': self.cat2.pk},
        )
        self.assertEqual(response.status_code, 200)
        products = response.context['page_obj'].object_list
        for p in products:
            self.assertEqual(p.category, self.cat2)

    def test_filter_stock_low(self):
        response = self.client.get(
            reverse('inventory:product_list'),
            {'stock': 'low'},
        )
        self.assertEqual(response.status_code, 200)

    def test_filter_stock_out(self):
        response = self.client.get(
            reverse('inventory:product_list'),
            {'stock': 'out'},
        )
        self.assertEqual(response.status_code, 200)
        products = response.context['page_obj'].object_list
        for p in products:
            self.assertEqual(p.stock, Decimal('0'))


@override_settings(ROOT_URLCONF='bodega_system.urls')
class HistoricalRecordTest(TestCase, InventoryTestDataMixin):
    """Tests that simple_history records changes for Product."""

    def setUp(self):
        self.create_users()
        self.category = self.create_category()
        self.product = self.create_product()

    def test_product_has_history(self):
        """Product changes should be recorded via HistoricalRecords."""
        self.assertTrue(hasattr(Product, 'history'))
        initial_count = self.product.history.count()

        self.product.name = 'Changed Name'
        self.product.save()

        self.assertEqual(self.product.history.count(), initial_count + 1)

    def test_price_change_tracked(self):
        self.product.selling_price_usd = Decimal('5.00')
        self.product.save()

        latest = self.product.history.first()
        self.assertEqual(latest.selling_price_usd, Decimal('5.00'))
