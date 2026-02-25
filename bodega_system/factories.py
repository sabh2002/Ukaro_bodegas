# factories.py - Factory Boy factories for generating test data

import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating test users"""
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_staff = False
    is_superuser = False
    role = 'viewer'


class AdminUserFactory(UserFactory):
    """Factory for admin users"""
    is_staff = True
    is_superuser = True
    role = 'admin'


class EmployeeUserFactory(UserFactory):
    """Factory for employee users"""
    is_staff = True
    role = 'employee'


class ExchangeRateFactory(DjangoModelFactory):
    """Factory for exchange rates"""
    class Meta:
        model = 'utils.ExchangeRate'

    date = factory.LazyFunction(date.today)
    bs_to_usd = Decimal('36.50')
    updated_by = factory.SubFactory(AdminUserFactory)


class CategoryFactory(DjangoModelFactory):
    """Factory for product categories"""
    class Meta:
        model = 'inventory.Category'

    name = factory.Sequence(lambda n: f'Category {n}')
    description = factory.Faker('text', max_nb_chars=100)


class ProductFactory(DjangoModelFactory):
    """Factory for products"""
    class Meta:
        model = 'inventory.Product'

    name = factory.Sequence(lambda n: f'Product {n}')
    barcode = factory.Sequence(lambda n: f'{1000000 + n}')
    category = factory.SubFactory(CategoryFactory)
    purchase_price_usd = Decimal('10.00')
    selling_price_usd = Decimal('15.00')
    stock = Decimal('100.00')
    min_stock = Decimal('10.00')
    unit_type = 'unit'
    is_active = True


class BulkProductFactory(ProductFactory):
    """Factory for products with bulk pricing"""
    is_bulk_pricing = True
    bulk_min_quantity = Decimal('10.00')
    bulk_price_usd = Decimal('12.00')


class CustomerFactory(DjangoModelFactory):
    """Factory for customers"""
    class Meta:
        model = 'customers.Customer'

    name = factory.Sequence(lambda n: f'Customer {n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.name.lower().replace(" ", "")}@test.com')
    phone = factory.Faker('phone_number')
    credit_limit_usd = Decimal('500.00')
    is_active = True


class SupplierFactory(DjangoModelFactory):
    """Factory for suppliers"""
    class Meta:
        model = 'suppliers.Supplier'

    name = factory.Sequence(lambda n: f'Supplier {n}')
    contact_person = factory.Faker('name')
    email = factory.LazyAttribute(lambda obj: f'{obj.name.lower().replace(" ", "")}@test.com')
    phone = factory.Faker('phone_number')
    is_active = True


class SaleFactory(DjangoModelFactory):
    """Factory for sales"""
    class Meta:
        model = 'sales.Sale'

    customer = factory.SubFactory(CustomerFactory)
    user = factory.SubFactory(EmployeeUserFactory)
    total_usd = Decimal('50.00')
    total_bs = Decimal('1825.00')
    exchange_rate_used = Decimal('36.50')
    is_credit = False
    payment_method = 'cash'


class SaleItemFactory(DjangoModelFactory):
    """Factory for sale items"""
    class Meta:
        model = 'sales.SaleItem'

    sale = factory.SubFactory(SaleFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = Decimal('5.00')
    price_usd = Decimal('15.00')
    price_bs = Decimal('547.50')


class CustomerCreditFactory(DjangoModelFactory):
    """Factory for customer credits"""
    class Meta:
        model = 'customers.CustomerCredit'

    customer = factory.SubFactory(CustomerFactory)
    sale = factory.SubFactory(SaleFactory)
    amount_usd = Decimal('100.00')
    amount_bs = Decimal('3650.00')
    exchange_rate_used = Decimal('36.50')
    date_due = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    is_paid = False


class CreditPaymentFactory(DjangoModelFactory):
    """Factory for credit payments"""
    class Meta:
        model = 'customers.CreditPayment'

    credit = factory.SubFactory(CustomerCreditFactory)
    amount_bs = Decimal('1000.00')
    amount_usd = Decimal('27.40')
    exchange_rate_used = Decimal('36.50')
    payment_method = 'cash'
    received_by = factory.SubFactory(EmployeeUserFactory)


class SupplierOrderFactory(DjangoModelFactory):
    """Factory for supplier orders"""
    class Meta:
        model = 'suppliers.SupplierOrder'

    supplier = factory.SubFactory(SupplierFactory)
    total_usd = Decimal('500.00')
    total_bs = Decimal('18250.00')
    exchange_rate_used = Decimal('36.50')
    status = 'pending'
    created_by = factory.SubFactory(AdminUserFactory)


class SupplierOrderItemFactory(DjangoModelFactory):
    """Factory for supplier order items"""
    class Meta:
        model = 'suppliers.SupplierOrderItem'

    order = factory.SubFactory(SupplierOrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = Decimal('20.00')
    price_usd = Decimal('10.00')
    price_bs = Decimal('365.00')


class ExpenseFactory(DjangoModelFactory):
    """Factory for expenses"""
    class Meta:
        model = 'finances.Expense'

    description = factory.Faker('sentence')
    amount_usd = Decimal('25.00')
    category = 'utilities'
    date = factory.LazyFunction(date.today)
    created_by = factory.SubFactory(AdminUserFactory)


class InventoryAdjustmentFactory(DjangoModelFactory):
    """Factory for inventory adjustments"""
    class Meta:
        model = 'inventory.InventoryAdjustment'

    product = factory.SubFactory(ProductFactory)
    adjustment_type = 'add'
    quantity = Decimal('10.00')
    previous_stock = Decimal('100.00')
    new_stock = Decimal('110.00')
    reason = 'Test adjustment'
    adjusted_by = factory.SubFactory(AdminUserFactory)


class DailyCloseFactory(DjangoModelFactory):
    """Factory for daily closes"""
    class Meta:
        model = 'finances.DailyClose'

    date = factory.LazyFunction(date.today)
    sales_count = 10
    sales_total_bs = Decimal('5000.00')
    expenses_total_bs = Decimal('500.00')
    profit_bs = Decimal('4500.00')
    closed_by = factory.SubFactory(AdminUserFactory)
    notes = factory.Faker('text', max_nb_chars=200)
