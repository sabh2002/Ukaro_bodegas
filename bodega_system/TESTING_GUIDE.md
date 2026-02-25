# Testing Guide - Ukaro Bodegas Sistema

## Setup

### 1. Install Testing Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **pytest**: Modern testing framework
- **pytest-django**: Django integration for pytest
- **pytest-cov**: Code coverage reporting
- **factory-boy**: Test data generation
- **freezegun**: Time mocking for tests
- **django-test-plus**: Django testing helpers

### 2. Configuration Files

The following files have been created for testing:

- `pytest.ini`: Pytest configuration and settings
- `conftest.py`: Global fixtures and test helpers
- `factories.py`: Factory Boy factories for generating test data

## Running Tests

### Run All Tests

```bash
cd bodega_system
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=. --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Tests

```bash
# Run tests in specific app
pytest utils/

# Run specific test class
pytest utils/tests.py::TestExchangeRate

# Run specific test method
pytest utils/tests.py::TestExchangeRate::test_get_latest_rate_returns_none_when_no_rates

# Run tests with specific marker
pytest -m critical  # Run only critical tests
pytest -m models    # Run only model tests
```

### Run Tests in Parallel (faster)

Install pytest-xdist:
```bash
pip install pytest-xdist
```

Run tests in parallel:
```bash
pytest -n auto  # Use all CPU cores
pytest -n 4     # Use 4 processes
```

## Test Markers

Tests are organized with markers for easy filtering:

- `@pytest.mark.critical`: Critical financial logic tests (must always pass)
- `@pytest.mark.models`: Model tests
- `@pytest.mark.views`: View integration tests
- `@pytest.mark.api`: API endpoint tests
- `@pytest.mark.permissions`: Permission and access control tests
- `@pytest.mark.slow`: Slow running tests
- `@pytest.mark.integration`: Integration tests spanning multiple apps

Example:
```python
@pytest.mark.critical
@pytest.mark.models
def test_exchange_rate_validation():
    # Critical test for exchange rate model
    pass
```

## Using Fixtures

### Available Fixtures (from conftest.py)

**User Fixtures:**
- `admin_user`: Admin user with all permissions
- `employee_user`: Employee user
- `regular_user`: Regular user (viewer only)

**Exchange Rate Fixtures:**
- `exchange_rate`: Current valid exchange rate
- `old_exchange_rate`: Exchange rate from 3 days ago

**Product Fixtures:**
- `category`: Product category
- `product`: Basic product
- `product_with_bulk_pricing`: Product with wholesale pricing

**Customer Fixtures:**
- `customer`: Basic customer
- `customer_with_credit`: Customer with existing credit

**Other Fixtures:**
- `supplier`: Supplier
- `supplier_order`: Supplier order
- `sale`: Basic sale
- `expense`: Expense record

**Client Fixtures:**
- `api_client`: Django test client
- `authenticated_client`: Client authenticated as admin
- `employee_client`: Client authenticated as employee

### Example Usage

```python
import pytest
from decimal import Decimal

@pytest.mark.django_db
def test_product_profit_margin(product):
    """Test using product fixture"""
    assert product.purchase_price_usd == Decimal('10.00')
    assert product.selling_price_usd == Decimal('15.00')
    assert product.profit_margin_usd == Decimal('5.00')

def test_authenticated_request(authenticated_client):
    """Test with authenticated client"""
    response = authenticated_client.get('/finances/dashboard/')
    assert response.status_code == 200
```

## Using Factories

Factories allow you to generate realistic test data quickly:

```python
from factories import ProductFactory, CustomerFactory, SaleFactory
from decimal import Decimal

def test_with_factories():
    # Create multiple products easily
    products = ProductFactory.create_batch(10)

    # Create product with specific attributes
    expensive_product = ProductFactory(
        selling_price_usd=Decimal('1000.00')
    )

    # Create related objects
    customer = CustomerFactory()
    sale = SaleFactory(customer=customer)

    # Use build() for unsaved objects (faster for validation tests)
    unsaved_product = ProductFactory.build()
```

## Test Structure

### Organize Tests by App

Each app has its own `tests.py`:

```
bodega_system/
├── utils/tests.py           # Exchange rate, utilities
├── inventory/tests.py       # Products, categories, inventory
├── sales/tests.py           # Sales, sale items
├── customers/tests.py       # Customers, credits, payments
├── suppliers/tests.py       # Suppliers, orders
├── finances/tests.py        # Expenses, reports, daily close
└── accounts/tests.py        # Users, permissions
```

### Test Class Organization

Group related tests in classes:

```python
class TestExchangeRate:
    """Tests for ExchangeRate model"""

    def test_get_latest_rate(self):
        pass

    def test_rate_ordering(self):
        pass

class TestExchangeRateValidation:
    """Tests for exchange rate validation"""

    def test_missing_rate_raises_error(self):
        pass
```

## Writing Good Tests

### 1. Follow AAA Pattern

```python
def test_sale_calculates_total(product, customer, admin_user):
    # Arrange: Set up test data
    sale = Sale.objects.create(
        customer=customer,
        user=admin_user,
        ...
    )

    # Act: Perform the action
    total = sale.calculate_total()

    # Assert: Verify the result
    assert total == Decimal('100.00')
```

### 2. Test One Thing Per Test

```python
# Good: One assertion
def test_product_profit_margin():
    product = ProductFactory(
        purchase_price_usd=Decimal('10.00'),
        selling_price_usd=Decimal('15.00')
    )
    assert product.profit_margin_usd == Decimal('5.00')

# Bad: Multiple unrelated assertions
def test_product():
    product = ProductFactory()
    assert product.name  # Name exists
    assert product.stock > 0  # Has stock
    assert product.is_active  # Is active
    # These should be separate tests
```

### 3. Use Descriptive Names

```python
# Good names
def test_sale_without_exchange_rate_raises_error():
    pass

def test_customer_credit_exceeds_limit_rejected():
    pass

# Bad names
def test_sale():
    pass

def test_error():
    pass
```

### 4. Mark Critical Tests

```python
@pytest.mark.critical
def test_exchange_rate_fallback_removed():
    """CRITICAL: Ensures no silent fallback on missing exchange rate"""
    ExchangeRate.objects.all().delete()

    with pytest.raises(ValueError):
        # Should fail, not use fallback
        item = SupplierOrderItem(...)
        item.save()
```

## Coverage Goals

### Target: >80% Coverage

```bash
pytest --cov=. --cov-report=term-missing --cov-fail-under=80
```

### Priority Coverage Areas

1. **Critical Financial Logic** (100% coverage required)
   - Exchange rate calculations
   - Profit calculations
   - Credit limit validation
   - Price conversions

2. **Business Logic** (>90% coverage)
   - Product pricing (regular + bulk)
   - Inventory adjustments
   - Sales processing
   - Credit management

3. **Views and APIs** (>80% coverage)
   - Happy paths
   - Error handling
   - Permission checks
   - Edge cases

### Excluded from Coverage

- Migrations (`*/migrations/*`)
- Test files themselves
- Admin customizations (low risk)
- Management commands (tested manually)

## CI/CD Integration

Tests run automatically on:

- **Pull Request**: Run full test suite
- **Push to main**: Run tests + deploy if passing
- **Nightly**: Run all tests including slow tests

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'factories'"

**Solution**: Run pytest from the `bodega_system` directory:
```bash
cd Ukaro_bodegas/bodega_system
pytest
```

### Issue: "Database access not allowed"

**Solution**: Add `@pytest.mark.django_db` decorator:
```python
@pytest.mark.django_db
def test_my_test():
    pass
```

Or use it at module level:
```python
pytestmark = pytest.mark.django_db
```

### Issue: Tests pass locally but fail in CI

**Solution**: Check for:
1. Hardcoded dates (use `freezegun` or fixtures)
2. Database state dependencies
3. File system dependencies
4. Timezone issues

## Test Data Best Practices

### 1. Use Factories for Complex Objects

```python
# Good: Use factory
product = ProductFactory()

# Bad: Manual creation (tedious)
category = Category.objects.create(name='Test')
product = Product.objects.create(
    name='Test Product',
    barcode='123',
    category=category,
    # ... many more fields
)
```

### 2. Use Fixtures for Shared Setup

```python
# Good: Reusable fixture
@pytest.fixture
def sale_with_items(sale, product):
    SaleItem.objects.create(
        sale=sale,
        product=product,
        quantity=5
    )
    return sale

def test_sale_total(sale_with_items):
    assert sale_with_items.total_usd > 0
```

### 3. Isolate Tests

Each test should be independent:

```python
# Good: Fresh data per test
def test_customer_credit(customer):
    customer.credit_limit_usd = Decimal('100.00')
    customer.save()
    # Test doesn't affect other tests

# Bad: Shared state
GLOBAL_CUSTOMER = CustomerFactory()  # Don't do this!
```

## Next Steps

1. ✅ Testing infrastructure set up
2. ⏭️ Write tests for all models (Task #7)
3. ⏭️ Write integration tests for views (Task #8)
4. ⏭️ Achieve >80% coverage
5. ⏭️ Set up CI/CD for automated testing

---

**Documentation Version:** 1.0
**Last Updated:** 2026-02-24
**Maintainer:** Development Team
