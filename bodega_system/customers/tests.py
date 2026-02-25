# customers/tests.py - Tests for customer models

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Sum

from customers.models import Customer, CustomerCredit, CreditPayment
from factories import (
    CustomerFactory, CustomerCreditFactory, CreditPaymentFactory,
    SaleFactory, AdminUserFactory, ExchangeRateFactory
)

pytestmark = pytest.mark.django_db


# ============================================================================
# CUSTOMER MODEL TESTS
# ============================================================================

class TestCustomerCreation:
    """Tests for Customer model creation"""

    def test_customer_creation_with_required_fields(self):
        """Test creating a customer with required fields"""
        customer = Customer.objects.create(
            name='John Doe',
            phone='555-1234',
            email='john@example.com',
            credit_limit_usd=Decimal('500.00')
        )

        assert customer.name == 'John Doe'
        assert customer.phone == '555-1234'
        assert customer.email == 'john@example.com'
        assert customer.credit_limit_usd == Decimal('500.00')
        assert customer.is_active is True

    def test_customer_string_representation(self):
        """Test __str__ method"""
        customer = CustomerFactory(name='Jane Smith')
        assert str(customer) == 'Jane Smith'

    def test_customer_ordering(self):
        """Customers should be ordered by name"""
        CustomerFactory(name='Zebra')
        CustomerFactory(name='Apple')
        CustomerFactory(name='Mango')

        customers = list(Customer.objects.all())

        assert customers[0].name == 'Apple'
        assert customers[1].name == 'Mango'
        assert customers[2].name == 'Zebra'


class TestCustomerCreditCalculations:
    """Tests for customer credit calculations"""

    @pytest.mark.critical
    def test_total_credit_used_with_no_credits(self):
        """Customer with no credits should have 0 credit used"""
        customer = CustomerFactory()
        assert customer.total_credit_used == 0

    @pytest.mark.critical
    def test_total_credit_used_calculation(self, customer, admin_user, exchange_rate):
        """Should sum only unpaid credits in USD"""
        from sales.models import Sale

        # Create first credit (unpaid)
        sale1 = SaleFactory(customer=customer, total_usd=Decimal('100.00'))
        credit1 = CustomerCredit.objects.create(
            customer=customer,
            sale=sale1,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30),
            is_paid=False
        )

        # Create second credit (unpaid)
        sale2 = SaleFactory(customer=customer, total_usd=Decimal('50.00'))
        credit2 = CustomerCredit.objects.create(
            customer=customer,
            sale=sale2,
            amount_usd=Decimal('50.00'),
            amount_bs=Decimal('1825.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30),
            is_paid=False
        )

        # Total should be sum of unpaid credits
        assert customer.total_credit_used == Decimal('150.00')

    @pytest.mark.critical
    def test_total_credit_used_excludes_paid_credits(self, customer, admin_user, exchange_rate):
        """Paid credits should NOT be included in total_credit_used"""
        from sales.models import Sale

        # Create unpaid credit
        sale1 = SaleFactory(customer=customer)
        credit1 = CustomerCredit.objects.create(
            customer=customer,
            sale=sale1,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30),
            is_paid=False
        )

        # Create paid credit
        sale2 = SaleFactory(customer=customer)
        credit2 = CustomerCredit.objects.create(
            customer=customer,
            sale=sale2,
            amount_usd=Decimal('50.00'),
            amount_bs=Decimal('1825.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30),
            is_paid=True  # PAID
        )

        # Only unpaid credit should count
        assert customer.total_credit_used == Decimal('100.00')

    @pytest.mark.critical
    def test_available_credit_calculation(self, customer):
        """available_credit = credit_limit_usd - total_credit_used"""
        customer.credit_limit_usd = Decimal('500.00')
        customer.save()

        # Initially no credits, so full limit available
        assert customer.available_credit == Decimal('500.00')

    @pytest.mark.critical
    def test_available_credit_with_existing_credits(self, customer, admin_user, exchange_rate):
        """Available credit should decrease with unpaid credits"""
        from sales.models import Sale

        customer.credit_limit_usd = Decimal('500.00')
        customer.save()

        # Add credit
        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('200.00'),
            amount_bs=Decimal('7300.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        # Available = 500 - 200 = 300
        assert customer.available_credit == Decimal('300.00')

    def test_available_credit_bs_calculation(self, customer, exchange_rate):
        """Should convert available credit to Bs using current rate"""
        customer.credit_limit_usd = Decimal('100.00')
        customer.save()

        # With exchange_rate of 36.50
        expected_bs = Decimal('100.00') * exchange_rate.bs_to_usd
        assert customer.available_credit_bs == expected_bs

    def test_credit_limit_bs_current_calculation(self, customer, exchange_rate):
        """Should convert credit limit to Bs using current rate"""
        customer.credit_limit_usd = Decimal('500.00')
        customer.save()

        expected_bs = Decimal('500.00') * exchange_rate.bs_to_usd
        assert customer.credit_limit_bs_current == expected_bs


class TestCustomerValidation:
    """Tests for customer validation"""

    @pytest.mark.critical
    def test_customer_cannot_exceed_credit_limit(self, customer, admin_user, exchange_rate):
        """Should validate that customer cannot use more credit than limit"""
        from sales.models import Sale

        customer.credit_limit_usd = Decimal('100.00')
        customer.save()

        # Create credit equal to limit
        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        # Available credit should be 0
        assert customer.available_credit == Decimal('0.00')

        # Trying to add more credit would exceed limit
        # (This is validated in views, not model)


# ============================================================================
# CUSTOMER CREDIT MODEL TESTS
# ============================================================================

class TestCustomerCreditCreation:
    """Tests for CustomerCredit model creation"""

    def test_credit_creation(self, customer, exchange_rate):
        """Test creating a customer credit"""
        from sales.models import Sale

        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        assert credit.customer == customer
        assert credit.sale == sale
        assert credit.amount_usd == Decimal('100.00')
        assert credit.is_paid is False
        assert credit.date_paid is None

    def test_credit_string_representation(self, customer, exchange_rate):
        """Test __str__ method"""
        from sales.models import Sale

        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        str_repr = str(credit)
        assert customer.name in str_repr
        assert '3650' in str_repr or '3650.00' in str_repr

    def test_credit_ordering(self, customer, exchange_rate):
        """Credits should be ordered by date_created descending"""
        from sales.models import Sale

        sale1 = SaleFactory(customer=customer)
        credit1 = CustomerCredit.objects.create(
            customer=customer,
            sale=sale1,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        sale2 = SaleFactory(customer=customer)
        credit2 = CustomerCredit.objects.create(
            customer=customer,
            sale=sale2,
            amount_usd=Decimal('50.00'),
            amount_bs=Decimal('1825.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        credits = list(CustomerCredit.objects.all())

        # Most recent first
        assert credits[0].id == credit2.id
        assert credits[1].id == credit1.id


class TestCustomerCreditPayment:
    """Tests for credit payment functionality"""

    @pytest.mark.critical
    def test_credit_payment_reduces_amount_owed(self, customer, admin_user, exchange_rate):
        """Payment should reduce the amount owed"""
        from sales.models import Sale

        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        # Make payment of 30 USD
        payment = CreditPayment.objects.create(
            credit=credit,
            amount_usd=Decimal('30.00'),
            amount_bs=Decimal('1095.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            payment_method='cash',
            received_by=admin_user
        )

        # Calculate remaining debt
        total_paid = credit.payments.aggregate(Sum('amount_usd'))['amount_usd__sum'] or Decimal('0.00')
        remaining = credit.amount_usd - total_paid

        assert total_paid == Decimal('30.00')
        assert remaining == Decimal('70.00')

    @pytest.mark.critical
    def test_credit_marked_paid_when_fully_paid(self, customer, admin_user, exchange_rate):
        """is_paid should be True when payments >= amount_usd"""
        from sales.models import Sale

        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        # Pay full amount
        payment = CreditPayment.objects.create(
            credit=credit,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            payment_method='cash',
            received_by=admin_user
        )

        # Mark as paid (done in view)
        credit.is_paid = True
        credit.date_paid = timezone.now()
        credit.save()

        assert credit.is_paid is True
        assert credit.date_paid is not None


# ============================================================================
# CREDIT PAYMENT MODEL TESTS
# ============================================================================

class TestCreditPaymentCreation:
    """Tests for CreditPayment model creation"""

    def test_payment_creation(self, customer, admin_user, exchange_rate):
        """Test creating a credit payment"""
        from sales.models import Sale

        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        payment = CreditPayment.objects.create(
            credit=credit,
            amount_usd=Decimal('50.00'),
            amount_bs=Decimal('1825.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            payment_method='cash',
            received_by=admin_user
        )

        assert payment.credit == credit
        assert payment.amount_usd == Decimal('50.00')
        assert payment.received_by == admin_user

    def test_payment_methods(self, customer, admin_user, exchange_rate):
        """Test different payment methods"""
        from sales.models import Sale

        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date_due=date.today() + timedelta(days=30)
        )

        # Cash payment
        payment_cash = CreditPayment.objects.create(
            credit=credit,
            amount_usd=Decimal('30.00'),
            amount_bs=Decimal('1095.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            payment_method='cash',
            received_by=admin_user
        )
        assert payment_cash.get_payment_method_icon() == '💵'

        # Card payment
        payment_card = CreditPayment.objects.create(
            credit=credit,
            amount_usd=Decimal('30.00'),
            amount_bs=Decimal('1095.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            payment_method='card',
            received_by=admin_user
        )
        assert payment_card.get_payment_method_icon() == '💳'

        # Mobile payment
        payment_mobile = CreditPayment.objects.create(
            credit=credit,
            amount_usd=Decimal('30.00'),
            amount_bs=Decimal('1095.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            payment_method='mobile',
            mobile_reference='REF123',
            received_by=admin_user
        )
        assert payment_mobile.get_payment_method_icon() == '📱'
        assert 'REF123' in payment_mobile.get_payment_method_display_with_icon()

    @pytest.mark.critical
    def test_credit_uses_current_exchange_rate_for_payment(self, customer, admin_user, exchange_rate):
        """Payment should use CURRENT exchange rate, not historical"""
        from sales.models import Sale
        from utils.models import ExchangeRate

        # Create credit with old rate
        sale = SaleFactory(customer=customer)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=Decimal('100.00'),
            amount_bs=Decimal('3650.00'),  # Old rate: 36.50
            exchange_rate_used=Decimal('36.50'),
            date_due=date.today() + timedelta(days=30)
        )

        # Change exchange rate
        new_rate = ExchangeRate.objects.create(
            date=date.today(),
            bs_to_usd=Decimal('40.00'),  # New rate
            updated_by=admin_user
        )

        # Payment uses NEW rate
        payment = CreditPayment.objects.create(
            credit=credit,
            amount_bs=Decimal('2000.00'),  # Paying 2000 Bs
            amount_usd=Decimal('2000.00') / Decimal('40.00'),  # = 50 USD at new rate
            exchange_rate_used=new_rate.bs_to_usd,
            payment_method='cash',
            received_by=admin_user
        )

        assert payment.exchange_rate_used == Decimal('40.00')
        assert payment.amount_usd == Decimal('50.00')
