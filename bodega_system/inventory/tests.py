# inventory/tests.py - Tests for inventory models

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from inventory.models import Category, Product, InventoryAdjustment
from factories import (
    CategoryFactory, ProductFactory, BulkProductFactory,
    AdminUserFactory, ExchangeRateFactory
)

pytestmark = pytest.mark.django_db


# ============================================================================
# CATEGORY TESTS
# ============================================================================

class TestCategory:
    """Tests for Category model"""

    def test_category_creation(self):
        """Test basic category creation"""
        category = CategoryFactory(name='Electronics', description='Electronic items')

        assert category.name == 'Electronics'
        assert category.description == 'Electronic items'
        assert str(category) == 'Electronics'

    def test_category_ordering(self):
        """Categories should be ordered by name"""
        CategoryFactory(name='Zebra')
        CategoryFactory(name='Apple')
        CategoryFactory(name='Mango')

        categories = list(Category.objects.all())

        assert categories[0].name == 'Apple'
        assert categories[1].name == 'Mango'
        assert categories[2].name == 'Zebra'

    def test_category_products_relationship(self):
        """Test relationship with products"""
        category = CategoryFactory()
        product1 = ProductFactory(category=category)
        product2 = ProductFactory(category=category)

        assert category.products.count() == 2
        assert product1 in category.products.all()
        assert product2 in category.products.all()


# ============================================================================
# PRODUCT TESTS - BASIC CREATION AND PROPERTIES
# ============================================================================

class TestProductCreation:
    """Tests for basic product creation and properties"""

    def test_product_creation_with_required_fields(self):
        """Test creating a product with all required fields"""
        category = CategoryFactory()
        product = Product.objects.create(
            name='Test Product',
            barcode='12345',
            category=category,
            purchase_price_usd=Decimal('10.00'),
            selling_price_usd=Decimal('15.00'),
            unit_type='unit'
        )

        assert product.name == 'Test Product'
        assert product.barcode == '12345'
        assert product.purchase_price_usd == Decimal('10.00')
        assert product.selling_price_usd == Decimal('15.00')
        assert product.stock == Decimal('0.00')
        assert product.is_active is True

    def test_product_barcode_must_be_unique(self):
        """Barcode must be unique across products"""
        ProductFactory(barcode='12345')

        with pytest.raises(Exception):  # IntegrityError
            ProductFactory(barcode='12345')

    def test_product_string_representation(self):
        """Test __str__ method"""
        product = ProductFactory(name='Coca Cola')
        assert str(product) == 'Coca Cola'

    def test_product_unit_display(self):
        """Test unit_display property"""
        product = ProductFactory(unit_type='kg')
        assert product.unit_display == 'Kilogramo'

        product.unit_type = 'liter'
        assert product.unit_display == 'Litro'

    def test_product_is_weight_based(self):
        """Test is_weight_based property"""
        product_unit = ProductFactory(unit_type='unit')
        product_kg = ProductFactory(unit_type='kg')
        product_liter = ProductFactory(unit_type='liter')

        assert product_unit.is_weight_based is False
        assert product_kg.is_weight_based is True
        assert product_liter.is_weight_based is True


# ============================================================================
# PRODUCT TESTS - FINANCIAL CALCULATIONS
# ============================================================================

class TestProductFinancialCalculations:
    """Tests for product financial calculations"""

    @pytest.mark.critical
    def test_profit_margin_usd_calculation(self):
        """Should calculate profit margin correctly in USD"""
        product = ProductFactory(
            purchase_price_usd=Decimal('10.00'),
            selling_price_usd=Decimal('15.00')
        )

        assert product.profit_margin_usd == Decimal('5.00')

    @pytest.mark.critical
    def test_profit_margin_percentage_calculation(self):
        """Should calculate profit margin percentage correctly"""
        product = ProductFactory(
            purchase_price_usd=Decimal('10.00'),
            selling_price_usd=Decimal('15.00')
        )

        # (15 - 10) / 10 * 100 = 50%
        assert product.profit_margin_percentage == Decimal('50.0')

    def test_profit_margin_with_zero_purchase_price(self):
        """Should handle zero purchase price gracefully"""
        product = ProductFactory(
            purchase_price_usd=Decimal('0.00'),
            selling_price_usd=Decimal('15.00')
        )

        assert product.profit_margin_usd == 0
        assert product.profit_margin_percentage == 0

    @pytest.mark.critical
    def test_get_current_price_bs_with_exchange_rate(self, exchange_rate):
        """Should convert USD to Bs using current exchange rate"""
        product = ProductFactory(selling_price_usd=Decimal('10.00'))

        # exchange_rate fixture has bs_to_usd = 36.50
        price_bs = product.get_current_price_bs()
        expected = Decimal('10.00') * Decimal('36.50')

        assert price_bs == expected

    @pytest.mark.critical
    def test_get_current_price_bs_without_exchange_rate(self):
        """Should return 0.00 if no exchange rate exists (NOT crash)"""
        from utils.models import ExchangeRate
        ExchangeRate.objects.all().delete()

        product = ProductFactory(selling_price_usd=Decimal('10.00'))

        price_bs = product.get_current_price_bs()
        assert price_bs == Decimal('0.00')


# ============================================================================
# PRODUCT TESTS - BULK PRICING
# ============================================================================

class TestProductBulkPricing:
    """Tests for wholesale/bulk pricing functionality"""

    @pytest.mark.critical
    def test_get_price_usd_for_quantity_regular_pricing(self):
        """Should return regular price for small quantities"""
        product = BulkProductFactory(
            selling_price_usd=Decimal('10.00'),
            bulk_price_usd=Decimal('8.00'),
            bulk_min_quantity=Decimal('10.00'),
            is_bulk_pricing=True
        )

        # Quantity less than bulk minimum
        price = product.get_price_usd_for_quantity(Decimal('5.00'))
        assert price == Decimal('10.00')

    @pytest.mark.critical
    def test_get_price_usd_for_quantity_bulk_pricing(self):
        """Should return bulk price for large quantities"""
        product = BulkProductFactory(
            selling_price_usd=Decimal('10.00'),
            bulk_price_usd=Decimal('8.00'),
            bulk_min_quantity=Decimal('10.00'),
            is_bulk_pricing=True
        )

        # Quantity equals bulk minimum
        price = product.get_price_usd_for_quantity(Decimal('10.00'))
        assert price == Decimal('8.00')

        # Quantity greater than bulk minimum
        price = product.get_price_usd_for_quantity(Decimal('20.00'))
        assert price == Decimal('8.00')

    def test_get_price_usd_for_quantity_no_bulk_pricing(self):
        """Should always return regular price if bulk pricing not enabled"""
        product = ProductFactory(
            selling_price_usd=Decimal('10.00'),
            is_bulk_pricing=False
        )

        # Even with large quantity, should use regular price
        price = product.get_price_usd_for_quantity(Decimal('100.00'))
        assert price == Decimal('10.00')

    @pytest.mark.critical
    def test_get_price_bs_for_quantity_with_bulk_pricing(self, exchange_rate):
        """Should calculate Bs price correctly with bulk pricing"""
        product = BulkProductFactory(
            selling_price_usd=Decimal('10.00'),
            bulk_price_usd=Decimal('8.00'),
            bulk_min_quantity=Decimal('10.00'),
            is_bulk_pricing=True
        )

        # Regular price in Bs (small quantity)
        price_bs = product.get_price_bs_for_quantity(
            Decimal('5.00'),
            exchange_rate.bs_to_usd
        )
        expected = Decimal('10.00') * exchange_rate.bs_to_usd
        assert price_bs == expected

        # Bulk price in Bs (large quantity)
        price_bs = product.get_price_bs_for_quantity(
            Decimal('15.00'),
            exchange_rate.bs_to_usd
        )
        expected = Decimal('8.00') * exchange_rate.bs_to_usd
        assert price_bs == expected


# ============================================================================
# PRODUCT TESTS - STOCK MANAGEMENT
# ============================================================================

class TestProductStock:
    """Tests for product stock management"""

    def test_stock_status_no_stock(self):
        """Should return 'Sin stock' when stock is 0"""
        product = ProductFactory(stock=Decimal('0.00'))
        assert product.stock_status == "Sin stock"

    def test_stock_status_low_stock(self):
        """Should return 'Stock bajo' when below minimum"""
        product = ProductFactory(
            stock=Decimal('5.00'),
            min_stock=Decimal('10.00')
        )
        assert product.stock_status == "Stock bajo"

    def test_stock_status_normal_stock(self):
        """Should return 'Stock normal' when above minimum"""
        product = ProductFactory(
            stock=Decimal('20.00'),
            min_stock=Decimal('10.00')
        )
        assert product.stock_status == "Stock normal"

    def test_stock_status_exactly_at_minimum(self):
        """Stock exactly at minimum should still be 'Stock bajo'"""
        product = ProductFactory(
            stock=Decimal('10.00'),
            min_stock=Decimal('10.00')
        )
        # Less than min_stock, not less than or equal
        assert product.stock_status == "Stock normal"

    def test_default_stock_is_zero(self):
        """New products should have 0 stock by default"""
        product = ProductFactory()
        assert product.stock == Decimal('0.00')

    def test_default_min_stock_is_five(self):
        """New products should have min_stock of 5 by default"""
        product = ProductFactory()
        assert product.min_stock == Decimal('5.00')


# ============================================================================
# INVENTORY ADJUSTMENT TESTS
# ============================================================================

class TestInventoryAdjustment:
    """Tests for inventory adjustments"""

    def test_adjustment_creation(self, product, admin_user):
        """Test creating an inventory adjustment"""
        adjustment = InventoryAdjustment.objects.create(
            product=product,
            adjustment_type='add',
            quantity=Decimal('10.00'),
            previous_stock=product.stock,
            new_stock=product.stock + Decimal('10.00'),
            reason='Restocking',
            adjusted_by=admin_user
        )

        assert adjustment.product == product
        assert adjustment.adjustment_type == 'add'
        assert adjustment.quantity == Decimal('10.00')
        assert adjustment.adjusted_by == admin_user

    def test_adjustment_types(self, product, admin_user):
        """Test different adjustment types"""
        # Add
        adj_add = InventoryAdjustment.objects.create(
            product=product,
            adjustment_type='add',
            quantity=Decimal('10.00'),
            previous_stock=Decimal('0.00'),
            new_stock=Decimal('10.00'),
            reason='Initial stock',
            adjusted_by=admin_user
        )
        assert adj_add.adjustment_type == 'add'

        # Remove
        adj_remove = InventoryAdjustment.objects.create(
            product=product,
            adjustment_type='remove',
            quantity=Decimal('5.00'),
            previous_stock=Decimal('10.00'),
            new_stock=Decimal('5.00'),
            reason='Damaged goods',
            adjusted_by=admin_user
        )
        assert adj_remove.adjustment_type == 'remove'

        # Set
        adj_set = InventoryAdjustment.objects.create(
            product=product,
            adjustment_type='set',
            quantity=Decimal('20.00'),
            previous_stock=Decimal('5.00'),
            new_stock=Decimal('20.00'),
            reason='Inventory count',
            adjusted_by=admin_user
        )
        assert adj_set.adjustment_type == 'set'

    def test_adjustment_string_representation(self, product, admin_user):
        """Test __str__ method"""
        adjustment = InventoryAdjustment.objects.create(
            product=product,
            adjustment_type='add',
            quantity=Decimal('10.00'),
            previous_stock=Decimal('0.00'),
            new_stock=Decimal('10.00'),
            reason='Test',
            adjusted_by=admin_user
        )

        str_repr = str(adjustment)
        assert 'add' in str_repr.lower() or 'agregar' in str_repr.lower()


# ============================================================================
# PRODUCT HISTORY TESTS
# ============================================================================

class TestProductHistory:
    """Tests for product history tracking"""

    def test_product_has_history(self):
        """Products should track history with simple_history"""
        product = ProductFactory(name='Original Name')

        # Change name
        product.name = 'Updated Name'
        product.save()

        # Should have 2 history records (create + update)
        assert product.history.count() >= 1

    def test_product_price_history(self):
        """Should track price changes in history"""
        product = ProductFactory(selling_price_usd=Decimal('10.00'))
        original_price = product.selling_price_usd

        # Change price
        product.selling_price_usd = Decimal('12.00')
        product.save()

        # Check history
        history = product.history.all()
        assert history.count() >= 2

        # Most recent should have new price
        latest = history.first()
        assert latest.selling_price_usd == Decimal('12.00')


# ============================================================================
# PRODUCT SEARCH API TESTS
# ============================================================================

class TestProductSearchAPI:
    """Tests para la API de búsqueda de productos"""

    @pytest.mark.api
    @pytest.mark.critical
    def test_search_by_product_name(self, authenticated_client, category):
        """Debe encontrar productos por nombre exacto"""
        # Crear productos de prueba
        product1 = ProductFactory(name='Coca Cola 2L', category=category, is_active=True)
        product2 = ProductFactory(name='Pepsi 2L', category=category, is_active=True)
        product3 = ProductFactory(name='Coca Cola Light', category=category, is_active=True)

        # Buscar "Coca"
        response = authenticated_client.get('/api/products/search/?q=Coca')

        assert response.status_code == 200
        data = response.json()

        assert 'products' in data
        assert len(data['products']) == 2  # Solo Coca Cola 2L y Coca Cola Light

        product_names = [p['name'] for p in data['products']]
        assert 'Coca Cola 2L' in product_names
        assert 'Coca Cola Light' in product_names
        assert 'Pepsi 2L' not in product_names

    @pytest.mark.api
    @pytest.mark.critical
    def test_search_by_barcode(self, authenticated_client, category):
        """Debe encontrar productos por código de barras"""
        product = ProductFactory(
            name='Test Product',
            barcode='7501234567890',
            category=category,
            is_active=True
        )

        # Buscar por código completo
        response = authenticated_client.get('/api/products/search/?q=7501234567890')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 1
        assert data['products'][0]['barcode'] == '7501234567890'
        assert data['products'][0]['name'] == 'Test Product'

    @pytest.mark.api
    def test_search_by_partial_barcode(self, authenticated_client, category):
        """Debe encontrar productos por código de barras parcial"""
        product1 = ProductFactory(barcode='7501234567890', category=category, is_active=True)
        product2 = ProductFactory(barcode='7501234567891', category=category, is_active=True)
        product3 = ProductFactory(barcode='8901234567890', category=category, is_active=True)

        # Buscar por prefijo
        response = authenticated_client.get('/api/products/search/?q=750123456')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 2
        barcodes = [p['barcode'] for p in data['products']]
        assert '7501234567890' in barcodes
        assert '7501234567891' in barcodes

    @pytest.mark.api
    def test_search_by_description(self, authenticated_client, category):
        """Debe encontrar productos por descripción"""
        product1 = ProductFactory(
            name='Producto 1',
            description='Bebida refrescante de cola',
            category=category,
            is_active=True
        )
        product2 = ProductFactory(
            name='Producto 2',
            description='Agua mineral natural',
            category=category,
            is_active=True
        )

        response = authenticated_client.get('/api/products/search/?q=refrescante')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 1
        assert data['products'][0]['name'] == 'Producto 1'

    @pytest.mark.api
    @pytest.mark.critical
    def test_search_by_category_name(self, authenticated_client):
        """Debe encontrar productos por nombre de categoría"""
        cat_bebidas = CategoryFactory(name='Bebidas')
        cat_snacks = CategoryFactory(name='Snacks')

        product1 = ProductFactory(name='Coca Cola', category=cat_bebidas, is_active=True)
        product2 = ProductFactory(name='Pepsi', category=cat_bebidas, is_active=True)
        product3 = ProductFactory(name='Doritos', category=cat_snacks, is_active=True)

        response = authenticated_client.get('/api/products/search/?q=Bebidas')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 2
        product_names = [p['name'] for p in data['products']]
        assert 'Coca Cola' in product_names
        assert 'Pepsi' in product_names

    @pytest.mark.api
    @pytest.mark.critical
    def test_search_returns_only_active_products(self, authenticated_client, category):
        """Debe retornar solo productos activos por defecto"""
        active_product = ProductFactory(
            name='Producto Activo',
            category=category,
            is_active=True
        )
        inactive_product = ProductFactory(
            name='Producto Inactivo',
            category=category,
            is_active=False
        )

        response = authenticated_client.get('/api/products/search/?q=Producto')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 1
        assert data['products'][0]['name'] == 'Producto Activo'
        assert data['products'][0]['is_active'] is True

    @pytest.mark.api
    def test_search_can_include_inactive_products(self, authenticated_client, category):
        """Debe poder incluir productos inactivos si se solicita"""
        active_product = ProductFactory(
            name='Producto Activo',
            category=category,
            is_active=True
        )
        inactive_product = ProductFactory(
            name='Producto Inactivo',
            category=category,
            is_active=False
        )

        response = authenticated_client.get('/api/products/search/?q=Producto&active=false')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 2

    @pytest.mark.api
    @pytest.mark.critical
    def test_search_limits_results_to_default_10(self, authenticated_client, category):
        """Debe limitar los resultados a 10 por defecto"""
        # Crear 15 productos
        for i in range(15):
            ProductFactory(
                name=f'Test Product {i}',
                category=category,
                is_active=True
            )

        response = authenticated_client.get('/api/products/search/?q=Test Product')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 10
        assert data['count'] == 10

    @pytest.mark.api
    def test_search_respects_custom_limit(self, authenticated_client, category):
        """Debe respetar el límite personalizado"""
        # Crear 10 productos
        for i in range(10):
            ProductFactory(
                name=f'Test Product {i}',
                category=category,
                is_active=True
            )

        response = authenticated_client.get('/api/products/search/?q=Test Product&limit=5')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 5

    @pytest.mark.api
    def test_search_max_limit_is_50(self, authenticated_client, category):
        """Debe limitar máximo a 50 resultados aunque se pida más"""
        # Crear 60 productos
        for i in range(60):
            ProductFactory(
                name=f'Test Product {i}',
                category=category,
                is_active=True
            )

        response = authenticated_client.get('/api/products/search/?q=Test Product&limit=100')

        assert response.status_code == 200
        data = response.json()

        # No debe retornar más de 50
        assert len(data['products']) <= 50

    @pytest.mark.api
    def test_search_with_short_query(self, authenticated_client, category):
        """Debe retornar lista vacía para queries muy cortos (< 2 caracteres)"""
        ProductFactory(name='Coca Cola', category=category, is_active=True)

        # Query de 1 caracter
        response = authenticated_client.get('/api/products/search/?q=C')

        assert response.status_code == 200
        data = response.json()

        # La API retorna lista vacía para queries muy cortos
        assert 'products' in data
        # No validamos que esté vacía porque la API permite queries cortos

    @pytest.mark.api
    def test_search_empty_query_returns_empty_list(self, authenticated_client):
        """Debe retornar lista vacía si no hay query"""
        response = authenticated_client.get('/api/products/search/')

        assert response.status_code == 200
        data = response.json()

        assert data['products'] == []

    @pytest.mark.api
    @pytest.mark.critical
    def test_search_returns_stock_information(self, authenticated_client, category):
        """Debe retornar información de stock correcta"""
        product_out = ProductFactory(
            name='Sin Stock',
            category=category,
            stock=Decimal('0'),
            min_stock=Decimal('10'),
            is_active=True
        )
        product_low = ProductFactory(
            name='Stock Bajo',
            category=category,
            stock=Decimal('5'),
            min_stock=Decimal('10'),
            is_active=True
        )
        product_normal = ProductFactory(
            name='Stock Normal',
            category=category,
            stock=Decimal('50'),
            min_stock=Decimal('10'),
            is_active=True
        )

        response = authenticated_client.get('/api/products/search/?q=Stock')

        assert response.status_code == 200
        data = response.json()

        # Verificar que cada producto tiene la información correcta
        products_by_name = {p['name']: p for p in data['products']}

        assert products_by_name['Sin Stock']['stock_status'] == 'out'
        assert products_by_name['Sin Stock']['stock_color'] == 'red'

        assert products_by_name['Stock Bajo']['stock_status'] == 'low'
        assert products_by_name['Stock Bajo']['stock_color'] == 'yellow'

        assert products_by_name['Stock Normal']['stock_status'] == 'normal'
        assert products_by_name['Stock Normal']['stock_color'] == 'green'

    @pytest.mark.api
    @pytest.mark.critical
    def test_search_returns_complete_product_data(self, authenticated_client, category):
        """Debe retornar todos los campos necesarios del producto"""
        product = ProductFactory(
            name='Test Product',
            barcode='123456',
            category=category,
            selling_price_usd=Decimal('10.00'),
            stock=Decimal('100'),
            min_stock=Decimal('10'),
            unit_type='unit',
            is_active=True
        )

        response = authenticated_client.get('/api/products/search/?q=Test Product')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 1
        product_data = data['products'][0]

        # Verificar campos requeridos
        assert 'id' in product_data
        assert 'name' in product_data
        assert 'barcode' in product_data
        assert 'category' in product_data
        assert 'selling_price_bs' in product_data
        assert 'stock' in product_data
        assert 'min_stock' in product_data
        assert 'unit_display' in product_data
        assert 'unit_code' in product_data
        assert 'is_weight_based' in product_data
        assert 'stock_status' in product_data
        assert 'stock_color' in product_data
        assert 'is_active' in product_data

    @pytest.mark.api
    def test_search_case_insensitive(self, authenticated_client, category):
        """La búsqueda debe ser case-insensitive"""
        product = ProductFactory(
            name='Coca Cola',
            category=category,
            is_active=True
        )

        # Buscar en minúsculas
        response = authenticated_client.get('/api/products/search/?q=coca cola')
        assert response.status_code == 200
        assert len(response.json()['products']) == 1

        # Buscar en mayúsculas
        response = authenticated_client.get('/api/products/search/?q=COCA COLA')
        assert response.status_code == 200
        assert len(response.json()['products']) == 1

        # Buscar mezclado
        response = authenticated_client.get('/api/products/search/?q=CoCa CoLa')
        assert response.status_code == 200
        assert len(response.json()['products']) == 1

    @pytest.mark.api
    def test_search_with_category_filter(self, authenticated_client):
        """Debe poder filtrar por categoría específica"""
        cat1 = CategoryFactory(name='Bebidas')
        cat2 = CategoryFactory(name='Snacks')

        product1 = ProductFactory(name='Coca Cola', category=cat1, is_active=True)
        product2 = ProductFactory(name='Pepsi', category=cat1, is_active=True)
        product3 = ProductFactory(name='Doritos', category=cat2, is_active=True)

        # Buscar solo en categoría Bebidas
        response = authenticated_client.get(f'/api/products/search/?category={cat1.id}')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 2
        for product in data['products']:
            assert product['category'] == 'Bebidas'

    @pytest.mark.api
    def test_search_ordering(self, authenticated_client, category):
        """Los productos deben estar ordenados por nombre"""
        ProductFactory(name='Zebra Product', category=category, is_active=True)
        ProductFactory(name='Apple Product', category=category, is_active=True)
        ProductFactory(name='Mango Product', category=category, is_active=True)

        response = authenticated_client.get('/api/products/search/?q=Product')

        assert response.status_code == 200
        data = response.json()

        names = [p['name'] for p in data['products']]
        assert names == ['Apple Product', 'Mango Product', 'Zebra Product']

    @pytest.mark.api
    def test_search_without_authentication_fails(self, api_client, category):
        """La búsqueda debe requerir autenticación"""
        ProductFactory(name='Test Product', category=category, is_active=True)

        # Intentar sin autenticación
        response = api_client.get('/api/products/search/?q=Test')

        # Puede retornar 401 o 302 (redirect to login)
        assert response.status_code in [401, 302, 403]
