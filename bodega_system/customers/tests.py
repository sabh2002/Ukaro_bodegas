"""
Comprehensive tests for the customers app.

Covers:
- Customer, CustomerCredit, CreditPayment model tests
- Property calculations (total_credit_used, available_credit, etc.)
- CustomerForm, CreditForm, CreditPaymentForm validations
- View access control (@customer_access_required, @admin_required)
- Credit payment flow (partial payments, full payments, marking as paid)
- Edge cases: no exchange rate, fallback rates, delete protection
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from customers.models import Customer, CustomerCredit, CreditPayment
from customers.forms import CustomerForm, CreditForm, CreditPaymentForm
from inventory.models import Category, Product
from sales.models import Sale
from utils.models import ExchangeRate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class CustomerTestMixin:
    """Shared setup for customer tests."""

    def _create_admin(self, username='admin', password='testpass123'):
        return User.objects.create_user(
            username=username,
            password=password,
            is_admin=True,
            is_employee=False,
        )

    def _create_employee(self, username='employee', password='testpass123'):
        return User.objects.create_user(
            username=username,
            password=password,
            is_admin=False,
            is_employee=True,
        )

    def _create_regular_user(self, username='regular', password='testpass123'):
        return User.objects.create_user(
            username=username,
            password=password,
            is_admin=False,
            is_employee=False,
        )

    def _create_exchange_rate(self, rate=Decimal('36.50'), user=None):
        if user is None:
            user = self._create_admin(username='rate_admin')
        return ExchangeRate.objects.create(
            date=date.today(),
            bs_to_usd=rate,
            updated_by=user,
        )

    def _create_customer(self, **kwargs):
        defaults = {
            'name': 'Juan Perez',
            'phone': '04141234567',
            'email': 'juan@example.com',
            'address': 'Caracas',
            'credit_limit_usd': Decimal('100.00'),
            'is_active': True,
        }
        defaults.update(kwargs)
        return Customer.objects.create(**defaults)

    def _create_sale(self, customer, user, total_usd=Decimal('50.00'),
                     rate=Decimal('36.50')):
        return Sale.objects.create(
            customer=customer,
            user=user,
            total_bs=total_usd * rate,
            total_usd=total_usd,
            exchange_rate_used=rate,
            payment_method='cash',
            is_credit=True,
        )

    def _create_credit(self, customer, sale, amount_usd=Decimal('50.00'),
                       rate=Decimal('36.50'), date_due=None):
        if date_due is None:
            date_due = date.today() + timedelta(days=30)
        return CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_bs=amount_usd * rate,
            amount_usd=amount_usd,
            exchange_rate_used=rate,
            date_due=date_due,
        )


# =====================================================================
# MODEL TESTS
# =====================================================================

class CustomerModelTest(CustomerTestMixin, TestCase):
    """Tests for the Customer model."""

    def test_str_representation(self):
        customer = self._create_customer(name='Maria Lopez')
        self.assertEqual(str(customer), 'Maria Lopez')

    def test_get_absolute_url(self):
        customer = self._create_customer()
        expected = reverse('customers:customer_detail', args=[customer.pk])
        self.assertEqual(customer.get_absolute_url(), expected)

    def test_default_ordering_by_name(self):
        self._create_customer(name='Zara')
        self._create_customer(name='Ana', email='ana@example.com')
        customers = list(Customer.objects.values_list('name', flat=True))
        self.assertEqual(customers, ['Ana', 'Zara'])

    def test_default_field_values(self):
        customer = Customer.objects.create(name='Test')
        self.assertEqual(customer.credit_limit_bs, 0)
        self.assertEqual(customer.credit_limit_usd, 0)
        self.assertTrue(customer.is_active)

    # -- total_credit_used (USD) --

    def test_total_credit_used_no_credits(self):
        customer = self._create_customer()
        self.assertEqual(customer.total_credit_used, 0)

    def test_total_credit_used_with_unpaid_credits(self):
        admin = self._create_admin()
        customer = self._create_customer()
        sale1 = self._create_sale(customer, admin, total_usd=Decimal('30.00'))
        sale2 = self._create_sale(customer, admin, total_usd=Decimal('20.00'))
        self._create_credit(customer, sale1, amount_usd=Decimal('30.00'))
        self._create_credit(customer, sale2, amount_usd=Decimal('20.00'))
        self.assertEqual(customer.total_credit_used, Decimal('50.00'))

    def test_total_credit_used_excludes_paid_credits(self):
        admin = self._create_admin()
        customer = self._create_customer()
        sale1 = self._create_sale(customer, admin, total_usd=Decimal('30.00'))
        sale2 = self._create_sale(customer, admin, total_usd=Decimal('20.00'))
        credit1 = self._create_credit(customer, sale1, amount_usd=Decimal('30.00'))
        self._create_credit(customer, sale2, amount_usd=Decimal('20.00'))
        credit1.is_paid = True
        credit1.date_paid = timezone.now()
        credit1.save()
        self.assertEqual(customer.total_credit_used, Decimal('20.00'))

    # -- total_credit_used_bs --

    def test_total_credit_used_bs(self):
        admin = self._create_admin()
        customer = self._create_customer()
        rate = Decimal('36.50')
        sale = self._create_sale(customer, admin, total_usd=Decimal('50.00'), rate=rate)
        self._create_credit(customer, sale, amount_usd=Decimal('50.00'), rate=rate)
        expected_bs = Decimal('50.00') * rate
        self.assertEqual(customer.total_credit_used_bs, expected_bs)

    # -- available_credit --

    def test_available_credit_no_usage(self):
        customer = self._create_customer(credit_limit_usd=Decimal('100.00'))
        self.assertEqual(customer.available_credit, Decimal('100.00'))

    def test_available_credit_with_usage(self):
        admin = self._create_admin()
        customer = self._create_customer(credit_limit_usd=Decimal('100.00'))
        sale = self._create_sale(customer, admin, total_usd=Decimal('40.00'))
        self._create_credit(customer, sale, amount_usd=Decimal('40.00'))
        self.assertEqual(customer.available_credit, Decimal('60.00'))

    def test_available_credit_negative_when_over_limit(self):
        """If credit used exceeds limit, available_credit is negative."""
        admin = self._create_admin()
        customer = self._create_customer(credit_limit_usd=Decimal('50.00'))
        sale = self._create_sale(customer, admin, total_usd=Decimal('70.00'))
        self._create_credit(customer, sale, amount_usd=Decimal('70.00'))
        self.assertEqual(customer.available_credit, Decimal('-20.00'))

    # -- available_credit_bs --

    def test_available_credit_bs_with_rate(self):
        admin = self._create_admin()
        rate_obj = self._create_exchange_rate(rate=Decimal('40.00'), user=admin)
        customer = self._create_customer(credit_limit_usd=Decimal('100.00'))
        # available_credit = 100, * 40 = 4000
        self.assertEqual(customer.available_credit_bs, Decimal('100.00') * Decimal('40.00'))

    def test_available_credit_bs_no_rate_returns_zero(self):
        customer = self._create_customer(credit_limit_usd=Decimal('100.00'))
        # No exchange rate in DB
        self.assertEqual(customer.available_credit_bs, 0)

    # -- credit_limit_bs_current --

    def test_credit_limit_bs_current_with_rate(self):
        admin = self._create_admin()
        self._create_exchange_rate(rate=Decimal('38.00'), user=admin)
        customer = self._create_customer(credit_limit_usd=Decimal('100.00'))
        self.assertEqual(customer.credit_limit_bs_current, Decimal('100.00') * Decimal('38.00'))

    def test_credit_limit_bs_current_no_rate(self):
        customer = self._create_customer(credit_limit_usd=Decimal('100.00'))
        self.assertEqual(customer.credit_limit_bs_current, 0)


class CustomerCreditModelTest(CustomerTestMixin, TestCase):
    """Tests for the CustomerCredit model."""

    def setUp(self):
        self.admin = self._create_admin()
        self.customer = self._create_customer()
        self.sale = self._create_sale(self.customer, self.admin)
        self.credit = self._create_credit(self.customer, self.sale)

    def test_str_representation(self):
        expected = f"Crédito de {self.customer.name} - {self.credit.amount_bs} Bs"
        self.assertEqual(str(self.credit), expected)

    def test_get_absolute_url(self):
        expected = reverse('customers:credit_detail', args=[self.credit.pk])
        self.assertEqual(self.credit.get_absolute_url(), expected)

    def test_default_is_paid_false(self):
        self.assertFalse(self.credit.is_paid)

    def test_default_ordering_by_date_created_descending(self):
        sale2 = self._create_sale(self.customer, self.admin, total_usd=Decimal('10.00'))
        credit2 = self._create_credit(self.customer, sale2, amount_usd=Decimal('10.00'))
        credits = list(CustomerCredit.objects.all())
        # Most recent first
        self.assertEqual(credits[0], credit2)

    def test_customer_protect_on_delete(self):
        """Cannot delete customer with credits due to PROTECT."""
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.customer.delete()


class CreditPaymentModelTest(CustomerTestMixin, TestCase):
    """Tests for the CreditPayment model."""

    def setUp(self):
        self.admin = self._create_admin()
        self.customer = self._create_customer()
        self.sale = self._create_sale(self.customer, self.admin)
        self.credit = self._create_credit(self.customer, self.sale)
        self.payment = CreditPayment.objects.create(
            credit=self.credit,
            amount_bs=Decimal('500.00'),
            amount_usd=Decimal('13.70'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
            received_by=self.admin,
        )

    def test_str_representation(self):
        result = str(self.payment)
        self.assertIn('500.00', result)
        self.assertIn('Bs', result)

    def test_get_payment_method_icon_cash(self):
        self.payment.payment_method = 'cash'
        self.assertIn('cash', self.payment.payment_method)
        icon = self.payment.get_payment_method_icon()
        self.assertIsNotNone(icon)

    def test_get_payment_method_icon_card(self):
        self.payment.payment_method = 'card'
        icon = self.payment.get_payment_method_icon()
        self.assertIsNotNone(icon)

    def test_get_payment_method_icon_mobile(self):
        self.payment.payment_method = 'mobile'
        icon = self.payment.get_payment_method_icon()
        self.assertIsNotNone(icon)

    def test_get_payment_method_icon_unknown_fallback(self):
        self.payment.payment_method = 'bitcoin'
        icon = self.payment.get_payment_method_icon()
        self.assertIsNotNone(icon)

    def test_get_payment_method_display_with_icon_cash(self):
        self.payment.payment_method = 'cash'
        display = self.payment.get_payment_method_display_with_icon()
        self.assertIn('Efectivo', display)

    def test_get_payment_method_display_with_icon_mobile_with_ref(self):
        self.payment.payment_method = 'mobile'
        self.payment.mobile_reference = 'REF12345'
        display = self.payment.get_payment_method_display_with_icon()
        self.assertIn('Ref: REF12345', display)

    def test_get_payment_method_display_with_icon_mobile_no_ref(self):
        self.payment.payment_method = 'mobile'
        self.payment.mobile_reference = ''
        display = self.payment.get_payment_method_display_with_icon()
        self.assertNotIn('Ref:', display)

    def test_default_ordering_by_payment_date_descending(self):
        payment2 = CreditPayment.objects.create(
            credit=self.credit,
            amount_bs=Decimal('100.00'),
            amount_usd=Decimal('2.74'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='card',
            received_by=self.admin,
        )
        payments = list(CreditPayment.objects.all())
        self.assertEqual(payments[0], payment2)


# =====================================================================
# FORM TESTS
# =====================================================================

class CustomerFormTest(CustomerTestMixin, TestCase):
    """Tests for CustomerForm."""

    def test_valid_form(self):
        data = {
            'name': 'Test Customer',
            'phone': '04141234567',
            'email': 'test@example.com',
            'address': 'Av. Principal',
            'credit_limit_usd': '100.00',
            'notes': 'VIP customer',
            'is_active': True,
        }
        form = CustomerForm(data=data)
        self.assertTrue(form.is_valid())

    def test_name_required(self):
        form = CustomerForm(data={'name': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_optional_fields(self):
        form = CustomerForm(data={
            'name': 'Minimal Customer',
            'credit_limit_usd': '0',
        })
        self.assertTrue(form.is_valid())

    def test_form_fields_match_expected(self):
        form = CustomerForm()
        expected_fields = {'name', 'phone', 'email', 'address',
                           'credit_limit_usd', 'notes', 'is_active'}
        self.assertEqual(set(form.fields.keys()), expected_fields)

    def test_invalid_email_rejected(self):
        form = CustomerForm(data={
            'name': 'Test',
            'email': 'not-an-email',
            'credit_limit_usd': '0',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class CreditFormTest(CustomerTestMixin, TestCase):
    """Tests for CreditForm."""

    def setUp(self):
        self.admin = self._create_admin()
        self.rate = self._create_exchange_rate(rate=Decimal('36.50'), user=self.admin)
        self.customer = self._create_customer(credit_limit_usd=Decimal('100.00'))

    def test_customer_queryset_filters_active_with_credit(self):
        """Only active customers with credit_limit_usd > 0 appear."""
        inactive = self._create_customer(
            name='Inactive', is_active=False, email='inactive@test.com',
            credit_limit_usd=Decimal('50.00'),
        )
        no_credit = self._create_customer(
            name='NoCred', email='nocred@test.com',
            credit_limit_usd=Decimal('0.00'),
        )
        form = CreditForm()
        qs = form.fields['customer'].queryset
        self.assertIn(self.customer, qs)
        self.assertNotIn(inactive, qs)
        self.assertNotIn(no_credit, qs)

    def test_default_date_due_30_days(self):
        form = CreditForm()
        expected_date = (timezone.now() + timedelta(days=30)).date()
        self.assertEqual(form.initial.get('date_due'), expected_date)

    def test_amount_exceeds_available_credit_rejected(self):
        """If amount_bs converts to more USD than available credit, form is invalid."""
        # Customer has $100 available. At rate 36.50, $100 = 3650 Bs
        # Try 4000 Bs = ~$109.59 -> exceeds $100
        data = {
            'customer': self.customer.pk,
            'amount_bs': '4000.00',
            'date_due': (date.today() + timedelta(days=30)).isoformat(),
        }
        form = CreditForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount_bs', form.errors)

    def test_amount_within_available_credit_accepted(self):
        """Amount that converts to less than available credit is valid."""
        # $50 at rate 36.50 = 1825 Bs
        data = {
            'customer': self.customer.pk,
            'amount_bs': '1825.00',
            'date_due': (date.today() + timedelta(days=30)).isoformat(),
        }
        form = CreditForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_validation_considers_existing_credits(self):
        """Available credit is reduced by existing unpaid credits."""
        sale = self._create_sale(self.customer, self.admin, total_usd=Decimal('80.00'))
        self._create_credit(self.customer, sale, amount_usd=Decimal('80.00'))
        # Now available = 100 - 80 = $20. At 36.50, $20 = 730 Bs.
        # Try 800 Bs = ~$21.92 -> exceeds $20
        data = {
            'customer': self.customer.pk,
            'amount_bs': '800.00',
            'date_due': (date.today() + timedelta(days=30)).isoformat(),
        }
        form = CreditForm(data=data)
        self.assertFalse(form.is_valid())


class CreditPaymentFormTest(CustomerTestMixin, TestCase):
    """Tests for CreditPaymentForm."""

    def setUp(self):
        self.admin = self._create_admin()
        self.rate = self._create_exchange_rate(rate=Decimal('36.50'), user=self.admin)
        self.customer = self._create_customer(credit_limit_usd=Decimal('200.00'))
        self.sale = self._create_sale(
            self.customer, self.admin, total_usd=Decimal('100.00'),
            rate=Decimal('36.50'),
        )
        self.credit = self._create_credit(
            self.customer, self.sale, amount_usd=Decimal('100.00'),
            rate=Decimal('36.50'),
        )

    def test_valid_payment(self):
        data = {
            'amount_bs': '1825.00',  # $50 at rate 36.50
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertTrue(form.is_valid(), form.errors)

    def test_amount_zero_rejected(self):
        data = {
            'amount_bs': '0',
            'payment_method': 'cash',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertFalse(form.is_valid())
        self.assertIn('amount_bs', form.errors)

    def test_negative_amount_rejected(self):
        data = {
            'amount_bs': '-100',
            'payment_method': 'cash',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertFalse(form.is_valid())
        self.assertIn('amount_bs', form.errors)

    def test_amount_exceeds_pending_rejected(self):
        """Payment amount in USD (converted from Bs) must not exceed pending USD."""
        # Credit is $100 at rate 36.50 -> 3650 Bs.  Trying 4000 Bs = $109.59
        data = {
            'amount_bs': '4000.00',
            'payment_method': 'cash',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertFalse(form.is_valid())
        self.assertIn('amount_bs', form.errors)

    def test_exact_pending_amount_accepted(self):
        """Paying exactly the pending amount should be valid."""
        # $100 at 36.50 = 3650 Bs
        data = {
            'amount_bs': '3650.00',
            'payment_method': 'cash',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertTrue(form.is_valid(), form.errors)

    def test_tolerance_allows_small_excess(self):
        """0.01 USD tolerance: slightly over should still pass."""
        # $100 pending. Try 3650.36 Bs -> $100.0098... which is < $100.01 threshold
        data = {
            'amount_bs': '3650.36',
            'payment_method': 'cash',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertTrue(form.is_valid(), form.errors)

    def test_mobile_reference_required_for_mobile_payment(self):
        data = {
            'amount_bs': '500.00',
            'payment_method': 'mobile',
            'mobile_reference': '',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertFalse(form.is_valid())
        self.assertIn('mobile_reference', form.errors)

    def test_mobile_reference_not_required_for_cash(self):
        data = {
            'amount_bs': '500.00',
            'payment_method': 'cash',
            'mobile_reference': '',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertTrue(form.is_valid(), form.errors)

    def test_mobile_reference_not_required_for_card(self):
        data = {
            'amount_bs': '500.00',
            'payment_method': 'card',
            'mobile_reference': '',
        }
        form = CreditPaymentForm(data=data, credit=self.credit)
        self.assertTrue(form.is_valid(), form.errors)

    def test_partial_payment_reduces_pending(self):
        """After a partial payment, the next form's max should reflect remaining."""
        CreditPayment.objects.create(
            credit=self.credit,
            amount_bs=Decimal('1825.00'),
            amount_usd=Decimal('50.00'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
            received_by=self.admin,
        )
        # Remaining: $50. At 36.50 = 1825 Bs.
        form = CreditPaymentForm(credit=self.credit)
        initial_amount = form.fields['amount_bs'].initial
        self.assertAlmostEqual(float(initial_amount), 1825.00, places=0)

    def test_form_without_credit_kwarg(self):
        """Form should still work when credit is None (no pre-population)."""
        data = {
            'amount_bs': '100.00',
            'payment_method': 'cash',
        }
        form = CreditPaymentForm(data=data, credit=None)
        self.assertTrue(form.is_valid(), form.errors)

    def test_fallback_rate_when_no_exchange_rate(self):
        """When no exchange rate exists, form uses fallback rate 36.00."""
        ExchangeRate.objects.all().delete()
        form = CreditPaymentForm(credit=self.credit)
        # Pending: $100 * 36.00 = 3600 Bs
        initial_amount = form.fields['amount_bs'].initial
        self.assertAlmostEqual(float(initial_amount), 3600.00, places=0)


# =====================================================================
# VIEW TESTS
# =====================================================================

class CustomerViewAccessTest(CustomerTestMixin, TestCase):
    """Tests for customer view access control."""

    def setUp(self):
        self.client = Client()
        self.admin = self._create_admin()
        self.employee = self._create_employee()
        self.regular = self._create_regular_user()
        self.customer = self._create_customer()

    # -- Unauthenticated access -> redirect to login --

    def test_customer_list_requires_login(self):
        resp = self.client.get(reverse('customers:customer_list'))
        self.assertNotEqual(resp.status_code, 200)

    def test_customer_detail_requires_login(self):
        resp = self.client.get(
            reverse('customers:customer_detail', args=[self.customer.pk]))
        self.assertNotEqual(resp.status_code, 200)

    # -- Regular user (not admin, not employee) -> 403 --

    def test_regular_user_denied_customer_list(self):
        self.client.login(username='regular', password='testpass123')
        resp = self.client.get(reverse('customers:customer_list'))
        self.assertEqual(resp.status_code, 403)

    def test_regular_user_denied_customer_create(self):
        self.client.login(username='regular', password='testpass123')
        resp = self.client.get(reverse('customers:customer_create'))
        self.assertEqual(resp.status_code, 403)

    # -- Employee access (customer_access_required) --

    def test_employee_can_access_customer_list(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(reverse('customers:customer_list'))
        self.assertEqual(resp.status_code, 200)

    def test_employee_can_access_customer_detail(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(
            reverse('customers:customer_detail', args=[self.customer.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_employee_can_access_customer_create(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(reverse('customers:customer_create'))
        self.assertEqual(resp.status_code, 200)

    def test_employee_can_access_customer_update(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(
            reverse('customers:customer_update', args=[self.customer.pk]))
        self.assertEqual(resp.status_code, 200)

    # -- Admin access --

    def test_admin_can_access_customer_list(self):
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(reverse('customers:customer_list'))
        self.assertEqual(resp.status_code, 200)

    # -- customer_delete is @admin_required --

    def test_employee_denied_customer_delete(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(
            reverse('customers:customer_delete', args=[self.customer.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_customer_delete(self):
        # Customer has no sales or credits, so delete view should render
        customer_no_deps = self._create_customer(
            name='NoDeps', email='nodeps@test.com')
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:customer_delete', args=[customer_no_deps.pk]))
        self.assertEqual(resp.status_code, 200)

    # -- credit_list is @admin_required --

    def test_employee_denied_credit_list(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(reverse('customers:credit_list'))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_credit_list(self):
        self.client.login(username='admin', password='testpass123')
        self._create_exchange_rate(user=self.admin)
        resp = self.client.get(reverse('customers:credit_list'))
        self.assertEqual(resp.status_code, 200)


class CustomerCRUDViewTest(CustomerTestMixin, TestCase):
    """Tests for customer CRUD operations via views."""

    def setUp(self):
        self.client = Client()
        self.admin = self._create_admin()
        self.client.login(username='admin', password='testpass123')

    def test_create_customer_via_post(self):
        data = {
            'name': 'New Customer',
            'phone': '04161234567',
            'email': 'new@test.com',
            'address': 'Maracaibo',
            'credit_limit_usd': '200.00',
            'notes': '',
            'is_active': True,
        }
        resp = self.client.post(reverse('customers:customer_create'), data)
        self.assertEqual(resp.status_code, 302)  # redirect on success
        self.assertTrue(Customer.objects.filter(name='New Customer').exists())

    def test_update_customer_via_post(self):
        customer = self._create_customer()
        data = {
            'name': 'Updated Name',
            'phone': customer.phone,
            'email': customer.email,
            'address': customer.address,
            'credit_limit_usd': '150.00',
            'notes': 'Updated',
            'is_active': True,
        }
        resp = self.client.post(
            reverse('customers:customer_update', args=[customer.pk]), data)
        self.assertEqual(resp.status_code, 302)
        customer.refresh_from_db()
        self.assertEqual(customer.name, 'Updated Name')
        self.assertEqual(customer.credit_limit_usd, Decimal('150.00'))

    def test_delete_customer_no_dependencies(self):
        customer = self._create_customer(name='Deletable', email='del@test.com')
        resp = self.client.post(
            reverse('customers:customer_delete', args=[customer.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Customer.objects.filter(pk=customer.pk).exists())

    def test_delete_customer_with_sales_blocked(self):
        """Customer with associated sales cannot be deleted."""
        customer = self._create_customer(name='HasSales', email='sales@test.com')
        Sale.objects.create(
            customer=customer,
            user=self.admin,
            total_bs=Decimal('100.00'),
            total_usd=Decimal('2.74'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
        )
        resp = self.client.post(
            reverse('customers:customer_delete', args=[customer.pk]))
        # Should redirect back (not actually delete)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Customer.objects.filter(pk=customer.pk).exists())

    def test_delete_customer_with_credits_blocked(self):
        """Customer with associated credits cannot be deleted."""
        customer = self._create_customer(name='HasCredit', email='credit@test.com')
        sale = self._create_sale(customer, self.admin)
        self._create_credit(customer, sale)
        resp = self.client.post(
            reverse('customers:customer_delete', args=[customer.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Customer.objects.filter(pk=customer.pk).exists())


class CustomerListFilterTest(CustomerTestMixin, TestCase):
    """Tests for customer_list view filtering and pagination."""

    def setUp(self):
        self.client = Client()
        self.admin = self._create_admin()
        self.client.login(username='admin', password='testpass123')
        self.c1 = self._create_customer(name='Alpha', email='alpha@test.com')
        self.c2 = self._create_customer(
            name='Beta', email='beta@test.com',
            credit_limit_usd=Decimal('0.00'))

    def test_search_filter(self):
        resp = self.client.get(reverse('customers:customer_list'), {'q': 'Alpha'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Alpha')

    def test_credit_filter_with_credit(self):
        resp = self.client.get(
            reverse('customers:customer_list'), {'credit': 'with_credit'})
        self.assertEqual(resp.status_code, 200)

    def test_credit_filter_with_pending(self):
        # Create a pending credit for c1
        sale = self._create_sale(self.c1, self.admin)
        self._create_credit(self.c1, sale)
        resp = self.client.get(
            reverse('customers:customer_list'), {'credit': 'with_pending'})
        self.assertEqual(resp.status_code, 200)


class CreditListViewTest(CustomerTestMixin, TestCase):
    """Tests for credit_list view."""

    def setUp(self):
        self.client = Client()
        self.admin = self._create_admin()
        self.rate = self._create_exchange_rate(rate=Decimal('36.50'), user=self.admin)
        self.customer = self._create_customer()
        self.sale = self._create_sale(self.customer, self.admin)
        self.credit = self._create_credit(self.customer, self.sale)
        self.client.login(username='admin', password='testpass123')

    def test_credit_list_renders(self):
        resp = self.client.get(reverse('customers:credit_list'))
        self.assertEqual(resp.status_code, 200)

    def test_credit_list_filter_by_status_pending(self):
        resp = self.client.get(
            reverse('customers:credit_list'), {'status': 'pending'})
        self.assertEqual(resp.status_code, 200)

    def test_credit_list_filter_by_status_paid(self):
        resp = self.client.get(
            reverse('customers:credit_list'), {'status': 'paid'})
        self.assertEqual(resp.status_code, 200)

    def test_credit_list_filter_by_customer(self):
        resp = self.client.get(
            reverse('customers:credit_list'),
            {'customer': self.customer.pk})
        self.assertEqual(resp.status_code, 200)

    def test_credit_list_calculates_current_bs_amounts(self):
        """credit_list annotates amount_bs_current and pending_amount_bs_current."""
        resp = self.client.get(reverse('customers:credit_list'))
        page_obj = resp.context['page_obj']
        for credit in page_obj:
            self.assertTrue(hasattr(credit, 'amount_bs_current'))
            self.assertTrue(hasattr(credit, 'pending_amount_bs_current'))

    def test_credit_list_fallback_rate_when_no_rate(self):
        """When no exchange rate exists, fallback rate 36.00 is used."""
        ExchangeRate.objects.all().delete()
        resp = self.client.get(reverse('customers:credit_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['current_rate'])


class CreditDetailViewTest(CustomerTestMixin, TestCase):
    """Tests for credit_detail view."""

    def setUp(self):
        self.client = Client()
        self.admin = self._create_admin()
        self.employee = self._create_employee()
        self.rate = self._create_exchange_rate(rate=Decimal('36.50'), user=self.admin)
        self.customer = self._create_customer()
        self.sale = self._create_sale(self.customer, self.admin)
        self.credit = self._create_credit(self.customer, self.sale)

    def test_admin_can_view_credit_detail(self):
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_detail', args=[self.credit.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_employee_can_view_credit_detail(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_detail', args=[self.credit.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_context_contains_pending_amounts(self):
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_detail', args=[self.credit.pk]))
        self.assertIn('pending_amount_usd', resp.context)
        self.assertIn('pending_amount_bs_current', resp.context)
        self.assertIn('total_paid_usd', resp.context)

    def test_pending_amount_usd_full_credit(self):
        """With no payments, pending equals full credit amount_usd."""
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_detail', args=[self.credit.pk]))
        self.assertEqual(resp.context['pending_amount_usd'], self.credit.amount_usd)

    def test_pending_amount_after_partial_payment(self):
        """After a partial payment, pending amount is reduced."""
        CreditPayment.objects.create(
            credit=self.credit,
            amount_bs=Decimal('1825.00'),
            amount_usd=Decimal('50.00'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
            received_by=self.admin,
        )
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_detail', args=[self.credit.pk]))
        self.assertEqual(resp.context['pending_amount_usd'], Decimal('50.00'))

    def test_credit_detail_no_rate_uses_fallback(self):
        """When no exchange rate exists, fallback 36.00 is used for Bs calculations."""
        ExchangeRate.objects.all().delete()
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_detail', args=[self.credit.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['current_rate'])
        # Pending Bs should use fallback 36.00
        expected_bs = round(self.credit.amount_usd * Decimal('36.00'), 2)
        self.assertEqual(resp.context['pending_amount_bs_current'], expected_bs)


# =====================================================================
# CREDIT PAYMENT FLOW TESTS
# =====================================================================

class CreditPaymentViewTest(CustomerTestMixin, TestCase):
    """Tests for the credit_payment view and payment flow."""

    def setUp(self):
        self.client = Client()
        self.admin = self._create_admin()
        self.employee = self._create_employee()
        self.rate = self._create_exchange_rate(rate=Decimal('36.50'), user=self.admin)
        self.customer = self._create_customer(credit_limit_usd=Decimal('200.00'))
        self.sale = self._create_sale(
            self.customer, self.admin, total_usd=Decimal('100.00'))
        self.credit = self._create_credit(
            self.customer, self.sale, amount_usd=Decimal('100.00'))

    def test_employee_can_access_payment_form(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_payment', args=[self.credit.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_access_payment_form(self):
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_payment', args=[self.credit.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_regular_user_denied_payment_form(self):
        self.client.login(username='regular', password='testpass123')
        regular = self._create_regular_user()
        resp = self.client.get(
            reverse('customers:credit_payment', args=[self.credit.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_payment_form_context(self):
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_payment', args=[self.credit.pk]))
        self.assertIn('pending_amount_usd', resp.context)
        self.assertIn('pending_amount_bs', resp.context)
        self.assertIn('form', resp.context)

    def test_partial_payment_creates_payment_record(self):
        self.client.login(username='admin', password='testpass123')
        data = {
            'amount_bs': '1825.00',  # $50
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': 'Partial payment',
        }
        resp = self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CreditPayment.objects.count(), 1)
        payment = CreditPayment.objects.first()
        self.assertEqual(payment.credit, self.credit)
        self.assertEqual(payment.amount_bs, Decimal('1825.00'))
        self.assertEqual(payment.received_by, self.admin)

    def test_partial_payment_does_not_mark_credit_paid(self):
        self.client.login(username='admin', password='testpass123')
        data = {
            'amount_bs': '1825.00',  # $50 out of $100
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        }
        self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]), data)
        self.credit.refresh_from_db()
        self.assertFalse(self.credit.is_paid)

    def test_full_payment_marks_credit_as_paid(self):
        self.client.login(username='admin', password='testpass123')
        data = {
            'amount_bs': '3650.00',  # $100 (full amount)
            'payment_method': 'card',
            'mobile_reference': '',
            'notes': '',
        }
        self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]), data)
        self.credit.refresh_from_db()
        self.assertTrue(self.credit.is_paid)
        self.assertIsNotNone(self.credit.date_paid)

    def test_multiple_partial_payments_then_full(self):
        """Two partial payments that total the credit should mark it as paid."""
        self.client.login(username='admin', password='testpass123')
        # First payment: $50
        self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]),
            {
                'amount_bs': '1825.00',
                'payment_method': 'cash',
                'mobile_reference': '',
                'notes': '',
            },
        )
        self.credit.refresh_from_db()
        self.assertFalse(self.credit.is_paid)

        # Second payment: remaining $50
        self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]),
            {
                'amount_bs': '1825.00',
                'payment_method': 'cash',
                'mobile_reference': '',
                'notes': '',
            },
        )
        self.credit.refresh_from_db()
        self.assertTrue(self.credit.is_paid)

    def test_payment_on_already_paid_credit_rejected(self):
        """Attempting to pay an already paid credit redirects with error."""
        self.credit.is_paid = True
        self.credit.date_paid = timezone.now()
        self.credit.save()
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:credit_payment', args=[self.credit.pk]))
        self.assertEqual(resp.status_code, 302)  # redirect

    def test_payment_uses_current_exchange_rate(self):
        """Payment should use the current exchange rate, not the credit's original."""
        # Change the rate
        new_rate = ExchangeRate.objects.create(
            date=date.today(),
            bs_to_usd=Decimal('40.00'),
            updated_by=self.admin,
        )
        self.client.login(username='admin', password='testpass123')
        data = {
            'amount_bs': '2000.00',  # At rate 40, this is $50
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        }
        self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]), data)
        payment = CreditPayment.objects.first()
        self.assertEqual(payment.exchange_rate_used, Decimal('40.00'))
        self.assertEqual(payment.amount_usd, Decimal('2000.00') / Decimal('40.00'))

    def test_payment_fallback_rate_when_no_exchange_rate(self):
        """When no exchange rate exists, fallback 36.00 is used."""
        ExchangeRate.objects.all().delete()
        self.client.login(username='admin', password='testpass123')
        data = {
            'amount_bs': '1800.00',  # At fallback 36, this is $50
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        }
        # The form itself will use fallback rate for validation
        # Need to also handle that the form validation uses fallback
        resp = self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]), data)
        self.assertEqual(resp.status_code, 302)
        payment = CreditPayment.objects.first()
        self.assertEqual(payment.exchange_rate_used, Decimal('36.00'))

    def test_mobile_payment_with_reference(self):
        self.client.login(username='admin', password='testpass123')
        data = {
            'amount_bs': '1825.00',
            'payment_method': 'mobile',
            'mobile_reference': 'MOV123456',
            'notes': '',
        }
        resp = self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]), data)
        self.assertEqual(resp.status_code, 302)
        payment = CreditPayment.objects.first()
        self.assertEqual(payment.payment_method, 'mobile')
        self.assertEqual(payment.mobile_reference, 'MOV123456')

    def test_mobile_payment_without_reference_rejected(self):
        self.client.login(username='admin', password='testpass123')
        data = {
            'amount_bs': '1825.00',
            'payment_method': 'mobile',
            'mobile_reference': '',
            'notes': '',
        }
        resp = self.client.post(
            reverse('customers:credit_payment', args=[self.credit.pk]), data)
        # Should re-render form (not redirect)
        self.assertEqual(resp.status_code, 200)


class CreditPaymentUpdatesAvailableCreditTest(CustomerTestMixin, TestCase):
    """Test that paying a credit updates customer's available credit."""

    def setUp(self):
        self.admin = self._create_admin()
        self._create_exchange_rate(rate=Decimal('36.50'), user=self.admin)
        self.customer = self._create_customer(credit_limit_usd=Decimal('100.00'))
        self.sale = self._create_sale(
            self.customer, self.admin, total_usd=Decimal('60.00'))
        self.credit = self._create_credit(
            self.customer, self.sale, amount_usd=Decimal('60.00'))

    def test_available_credit_before_payment(self):
        self.assertEqual(self.customer.available_credit, Decimal('40.00'))

    def test_available_credit_restored_after_full_payment(self):
        self.credit.is_paid = True
        self.credit.save()
        # Paid credits are excluded from total_credit_used
        self.assertEqual(self.customer.available_credit, Decimal('100.00'))

    def test_available_credit_unchanged_after_partial_payment(self):
        """Partial payment doesn't change is_paid, so available_credit stays same."""
        CreditPayment.objects.create(
            credit=self.credit,
            amount_bs=Decimal('1000.00'),
            amount_usd=Decimal('27.40'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
            received_by=self.admin,
        )
        # Credit is still unpaid, so total_credit_used still includes it
        self.assertEqual(self.customer.available_credit, Decimal('40.00'))


class CustomerDetailViewEmployeeFilterTest(CustomerTestMixin, TestCase):
    """Test that employee sees only their own sales in customer_detail."""

    def setUp(self):
        self.client = Client()
        self.admin = self._create_admin()
        self.employee = self._create_employee()
        self.customer = self._create_customer()
        # Admin's sale
        Sale.objects.create(
            customer=self.customer,
            user=self.admin,
            total_bs=Decimal('100.00'),
            total_usd=Decimal('2.74'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='cash',
        )
        # Employee's sale
        Sale.objects.create(
            customer=self.customer,
            user=self.employee,
            total_bs=Decimal('200.00'),
            total_usd=Decimal('5.48'),
            exchange_rate_used=Decimal('36.50'),
            payment_method='card',
        )

    def test_admin_sees_all_sales(self):
        self.client.login(username='admin', password='testpass123')
        resp = self.client.get(
            reverse('customers:customer_detail', args=[self.customer.pk]))
        sales = resp.context['sales']
        self.assertEqual(len(sales), 2)

    def test_employee_sees_only_own_sales(self):
        self.client.login(username='employee', password='testpass123')
        resp = self.client.get(
            reverse('customers:customer_detail', args=[self.customer.pk]))
        sales = resp.context['sales']
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0].user, self.employee)
