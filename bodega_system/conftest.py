# conftest.py - Global pytest fixtures

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True,
        role='admin'
    )


@pytest.fixture
def employee_user(db):
    """Create an employee user"""
    return User.objects.create_user(
        username='employee',
        email='employee@test.com',
        password='testpass123',
        is_staff=True,
        role='employee'
    )


@pytest.fixture
def regular_user(db):
    """Create a regular user with no special permissions"""
    return User.objects.create_user(
        username='user',
        email='user@test.com',
        password='testpass123',
        role='viewer'
    )


@pytest.fixture
def exchange_rate(db, admin_user):
    """Create a valid exchange rate"""
    from utils.models import ExchangeRate
    return ExchangeRate.objects.create(
        date=date.today(),
        bs_to_usd=Decimal('36.50'),
        updated_by=admin_user
    )


@pytest.fixture
def old_exchange_rate(db, admin_user):
    """Create an old exchange rate (3 days ago)"""
    from utils.models import ExchangeRate
    return ExchangeRate.objects.create(
        date=date.today() - timedelta(days=3),
        bs_to_usd=Decimal('35.00'),
        updated_by=admin_user
    )


@pytest.fixture
def category(db):
    """Create a product category"""
    from inventory.models import Category
    return Category.objects.create(
        name='Test Category',
        description='A test category'
    )


@pytest.fixture
def product(db, category):
    """Create a basic product"""
    from inventory.models import Product
    return Product.objects.create(
        name='Test Product',
        barcode='12345',
        category=category,
        purchase_price_usd=Decimal('10.00'),
        selling_price_usd=Decimal('15.00'),
        stock=Decimal('100.00'),
        min_stock=Decimal('10.00'),
        unit_type='unit'
    )


@pytest.fixture
def product_with_bulk_pricing(db, category):
    """Create a product with bulk pricing"""
    from inventory.models import Product
    return Product.objects.create(
        name='Bulk Product',
        barcode='54321',
        category=category,
        purchase_price_usd=Decimal('5.00'),
        selling_price_usd=Decimal('8.00'),
        bulk_price_usd=Decimal('7.00'),
        bulk_min_quantity=Decimal('10.00'),
        is_bulk_pricing=True,
        stock=Decimal('200.00'),
        min_stock=Decimal('20.00'),
        unit_type='unit'
    )


@pytest.fixture
def customer(db):
    """Create a customer"""
    from customers.models import Customer
    return Customer.objects.create(
        name='Test Customer',
        email='customer@test.com',
        phone='555-1234',
        credit_limit_usd=Decimal('500.00')
    )


@pytest.fixture
def customer_with_credit(db, customer, admin_user, exchange_rate):
    """Create a customer with existing credit"""
    from customers.models import CustomerCredit
    from sales.models import Sale

    # Create a sale
    sale = Sale.objects.create(
        customer=customer,
        user=admin_user,
        total_usd=Decimal('100.00'),
        total_bs=Decimal('3650.00'),
        exchange_rate_used=exchange_rate.bs_to_usd,
        is_credit=True
    )

    # Create credit
    credit = CustomerCredit.objects.create(
        customer=customer,
        sale=sale,
        amount_usd=Decimal('100.00'),
        amount_bs=Decimal('3650.00'),
        exchange_rate_used=exchange_rate.bs_to_usd,
        date_due=date.today() + timedelta(days=30)
    )

    return customer


@pytest.fixture
def supplier(db):
    """Create a supplier"""
    from suppliers.models import Supplier
    return Supplier.objects.create(
        name='Test Supplier',
        contact_person='John Doe',
        email='supplier@test.com',
        phone='555-5678'
    )


@pytest.fixture
def supplier_order(db, supplier, admin_user, exchange_rate):
    """Create a supplier order"""
    from suppliers.models import SupplierOrder
    return SupplierOrder.objects.create(
        supplier=supplier,
        total_usd=Decimal('500.00'),
        total_bs=Decimal('18250.00'),
        exchange_rate_used=exchange_rate.bs_to_usd,
        created_by=admin_user,
        status='pending'
    )


@pytest.fixture
def sale(db, customer, admin_user, exchange_rate):
    """Create a basic sale"""
    from sales.models import Sale
    return Sale.objects.create(
        customer=customer,
        user=admin_user,
        total_usd=Decimal('50.00'),
        total_bs=Decimal('1825.00'),
        exchange_rate_used=exchange_rate.bs_to_usd,
        is_credit=False,
        payment_method='cash'
    )


@pytest.fixture
def expense(db, admin_user):
    """Create an expense"""
    from finances.models import Expense
    return Expense.objects.create(
        description='Test Expense',
        amount_usd=Decimal('25.00'),
        category='utilities',
        date=date.today(),
        created_by=admin_user
    )


@pytest.fixture
def api_client():
    """Return Django test client"""
    from django.test.client import Client
    return Client()


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Return authenticated client"""
    api_client.force_login(admin_user)
    return api_client


@pytest.fixture
def employee_client(api_client, employee_user):
    """Return client authenticated as employee"""
    api_client.force_login(employee_user)
    return api_client


# Markers for test organization
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "critical: Critical financial logic tests"
    )
    config.addinivalue_line(
        "markers", "models: Model tests"
    )
    config.addinivalue_line(
        "markers", "views: View integration tests"
    )
    config.addinivalue_line(
        "markers", "api: API endpoint tests"
    )
    config.addinivalue_line(
        "markers", "permissions: Permission and access control tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
