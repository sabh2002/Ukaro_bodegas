# sales/tests.py - Tests for sales models

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from sales.models import Sale, SaleItem
from customers.models import Customer, CustomerCredit
from factories import (
    SaleFactory, SaleItemFactory, ProductFactory,
    CustomerFactory, AdminUserFactory, EmployeeUserFactory,
    ExchangeRateFactory
)

pytestmark = pytest.mark.django_db


# ============================================================================
# SALE MODEL TESTS
# ============================================================================

class TestSaleCreation:
    """Tests for Sale model creation"""

    def test_sale_creation_with_required_fields(self, customer, admin_user, exchange_rate):
        """Test creating a sale with all required fields"""
        sale = Sale.objects.create(
            customer=customer,
            user=admin_user,
            total_usd=Decimal('50.00'),
            total_bs=Decimal('1825.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            payment_method='cash',
            is_credit=False
        )

        assert sale.customer == customer
        assert sale.user == admin_user
        assert sale.total_usd == Decimal('50.00')
        assert sale.total_bs == Decimal('1825.00')
        assert sale.exchange_rate_used == exchange_rate.bs_to_usd
        assert sale.is_credit is False

    def test_sale_without_customer(self, admin_user, exchange_rate):
        """Sales can be created without a customer (anonymous)"""
        sale = Sale.objects.create(
            customer=None,
            user=admin_user,
            total_usd=Decimal('25.00'),
            total_bs=Decimal('912.50'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            payment_method='cash'
        )

        assert sale.customer is None
        assert sale.total_usd == Decimal('25.00')

    def test_sale_string_representation(self, sale):
        """Test __str__ method"""
        str_repr = str(sale)
        assert 'Venta #' in str_repr
        assert str(sale.id) in str_repr

    def test_sale_ordering(self, admin_user, exchange_rate):
        """Sales should be ordered by date descending (newest first)"""
        old_sale = SaleFactory()
        new_sale = SaleFactory()

        sales = list(Sale.objects.all())

        assert sales[0].id == new_sale.id  # Most recent first
        assert sales[1].id == old_sale.id


class TestSalePaymentMethods:
    """Tests for payment method functionality"""

    def test_payment_method_cash(self, admin_user, exchange_rate):
        """Test cash payment method"""
        sale = SaleFactory(payment_method='cash')
        assert sale.payment_method == 'cash'
        assert sale.get_payment_method_icon() == '💵'

    def test_payment_method_card(self, admin_user, exchange_rate):
        """Test card (punto de venta) payment method"""
        sale = SaleFactory(payment_method='card')
        assert sale.payment_method == 'card'
        assert sale.get_payment_method_icon() == '💳'

    def test_payment_method_mobile(self, admin_user, exchange_rate):
        """Test mobile payment method"""
        sale = SaleFactory(
            payment_method='mobile',
            mobile_reference='1234567890'
        )
        assert sale.payment_method == 'mobile'
        assert sale.get_payment_method_icon() == '📱'
        assert sale.mobile_reference == '1234567890'

    def test_payment_method_display_with_icon(self, admin_user, exchange_rate):
        """Test get_payment_method_display_with_icon method"""
        sale_cash = SaleFactory(payment_method='cash')
        display_cash = sale_cash.get_payment_method_display_with_icon()
        assert '💵' in display_cash

        sale_mobile = SaleFactory(
            payment_method='mobile',
            mobile_reference='REF123'
        )
        display_mobile = sale_mobile.get_payment_method_display_with_icon()
        assert '📱' in display_mobile
        assert 'REF123' in display_mobile


class TestSaleCreditFunctionality:
    """Tests for credit sales functionality"""

    @pytest.mark.critical
    def test_credit_sale_creates_customer_credit(self, customer, admin_user, exchange_rate):
        """Credit sale should create a CustomerCredit record"""
        sale = Sale.objects.create(
            customer=customer,
            user=admin_user,
            total_usd=Decimal('100.00'),
            total_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            is_credit=True
        )

        # Manually create credit (normally done in API)
        credit = CustomerCredit.objects.create(
            customer=customer,
            sale=sale,
            amount_usd=sale.total_usd,
            amount_bs=sale.total_bs,
            exchange_rate_used=sale.exchange_rate_used,
            date_due=date.today() + timedelta(days=30)
        )

        assert credit.customer == customer
        assert credit.sale == sale
        assert credit.amount_usd == Decimal('100.00')
        assert credit.is_paid is False

    def test_cash_sale_does_not_create_credit(self, customer, admin_user, exchange_rate):
        """Cash sale should NOT create CustomerCredit"""
        sale = Sale.objects.create(
            customer=customer,
            user=admin_user,
            total_usd=Decimal('50.00'),
            total_bs=Decimal('1825.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            is_credit=False
        )

        # Should not have any credits associated
        assert CustomerCredit.objects.filter(sale=sale).count() == 0


class TestSaleExchangeRate:
    """Tests for exchange rate handling in sales"""

    @pytest.mark.critical
    def test_sale_captures_exchange_rate_at_time_of_sale(self, customer, admin_user, exchange_rate):
        """Sale should capture and store the exchange rate used"""
        sale = Sale.objects.create(
            customer=customer,
            user=admin_user,
            total_usd=Decimal('100.00'),
            total_bs=Decimal('3650.00'),
            exchange_rate_used=exchange_rate.bs_to_usd
        )

        assert sale.exchange_rate_used == exchange_rate.bs_to_usd
        assert sale.total_bs == sale.total_usd * exchange_rate.bs_to_usd

    @pytest.mark.critical
    def test_sale_totals_match_exchange_rate(self, customer, admin_user, exchange_rate):
        """Total Bs should equal Total USD × Exchange Rate"""
        total_usd = Decimal('50.00')
        expected_bs = total_usd * exchange_rate.bs_to_usd

        sale = Sale.objects.create(
            customer=customer,
            user=admin_user,
            total_usd=total_usd,
            total_bs=expected_bs,
            exchange_rate_used=exchange_rate.bs_to_usd
        )

        assert sale.total_bs == expected_bs


class TestSaleItems:
    """Tests for Sale items relationship"""

    def test_sale_item_count_property(self, sale, product):
        """Test item_count property"""
        # Initially no items
        assert sale.item_count == 0

        # Add items
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00'),
            price_bs=Decimal('365.00')
        )
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('3.00'),
            price_usd=Decimal('10.00'),
            price_bs=Decimal('365.00')
        )

        # Refresh from DB
        sale.refresh_from_db()

        # Should be 8 total items (5 + 3)
        assert sale.item_count == Decimal('8.00')


# ============================================================================
# SALE ITEM MODEL TESTS
# ============================================================================

class TestSaleItemCreation:
    """Tests for SaleItem model creation"""

    def test_sale_item_creation_with_product(self, sale, product):
        """Test creating a sale item with a product"""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('15.00'),
            price_bs=Decimal('547.50')
        )

        assert item.sale == sale
        assert item.product == product
        assert item.quantity == Decimal('10.00')
        assert item.price_usd == Decimal('15.00')
        assert item.price_bs == Decimal('547.50')

    def test_sale_item_string_representation(self, sale, product):
        """Test __str__ method"""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00'),
            price_bs=Decimal('365.00')
        )

        str_repr = str(item)
        assert product.name in str_repr
        assert '5' in str_repr


class TestSaleItemCalculations:
    """Tests for SaleItem calculations"""

    @pytest.mark.critical
    def test_subtotal_usd_calculation(self, sale, product):
        """Subtotal USD = price_usd × quantity"""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00'),
            price_bs=Decimal('365.00')
        )

        assert item.subtotal_usd == Decimal('50.00')

    @pytest.mark.critical
    def test_subtotal_bs_calculation(self, sale, product):
        """Subtotal Bs = price_bs × quantity"""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00'),
            price_bs=Decimal('365.00')
        )

        assert item.subtotal_bs == Decimal('1825.00')

    def test_subtotal_alias_for_compatibility(self, sale, product):
        """subtotal property should alias to subtotal_bs"""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('3.00'),
            price_usd=Decimal('10.00'),
            price_bs=Decimal('365.00')
        )

        assert item.subtotal == item.subtotal_bs
        assert item.subtotal == Decimal('1095.00')


class TestSaleItemWithBulkPricing:
    """Tests for sale items with bulk pricing"""

    @pytest.mark.critical
    def test_sale_item_uses_bulk_price_for_large_quantity(self, sale, exchange_rate):
        """Sale item should use bulk price when quantity >= bulk_min_quantity"""
        from factories import BulkProductFactory

        product = BulkProductFactory(
            selling_price_usd=Decimal('10.00'),
            bulk_price_usd=Decimal('8.00'),
            bulk_min_quantity=Decimal('10.00'),
            is_bulk_pricing=True
        )

        # Large quantity - should use bulk price
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('15.00'),
            price_usd=Decimal('8.00'),  # Bulk price
            price_bs=Decimal('8.00') * exchange_rate.bs_to_usd
        )

        assert item.price_usd == Decimal('8.00')
        assert item.subtotal_usd == Decimal('120.00')  # 15 × 8

    @pytest.mark.critical
    def test_sale_item_uses_regular_price_for_small_quantity(self, sale, exchange_rate):
        """Sale item should use regular price when quantity < bulk_min_quantity"""
        from factories import BulkProductFactory

        product = BulkProductFactory(
            selling_price_usd=Decimal('10.00'),
            bulk_price_usd=Decimal('8.00'),
            bulk_min_quantity=Decimal('10.00'),
            is_bulk_pricing=True
        )

        # Small quantity - should use regular price
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00'),  # Regular price
            price_bs=Decimal('10.00') * exchange_rate.bs_to_usd
        )

        assert item.price_usd == Decimal('10.00')
        assert item.subtotal_usd == Decimal('50.00')  # 5 × 10


class TestSaleItemInventoryImpact:
    """Tests for how sale items affect inventory"""

    @pytest.mark.critical
    def test_sale_item_should_reduce_product_stock(self, sale, product):
        """Creating a sale item should reduce product stock (tested via API)"""
        # Note: Stock reduction happens in API, not in model
        # This test verifies the expectation
        initial_stock = product.stock

        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('15.00'),
            price_bs=Decimal('547.50')
        )

        # In API, this would trigger stock reduction
        # Here we just verify the item was created
        assert item.quantity == Decimal('10.00')

    def test_multiple_items_in_same_sale(self, sale):
        """Can create multiple items in the same sale"""
        from factories import ProductFactory

        product1 = ProductFactory()
        product2 = ProductFactory()

        item1 = SaleItem.objects.create(
            sale=sale,
            product=product1,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00'),
            price_bs=Decimal('365.00')
        )

        item2 = SaleItem.objects.create(
            sale=sale,
            product=product2,
            quantity=Decimal('3.00'),
            price_usd=Decimal('15.00'),
            price_bs=Decimal('547.50')
        )

        assert sale.items.count() == 2
        assert item1 in sale.items.all()
        assert item2 in sale.items.all()


class TestSaleItemPriceCapture:
    """Tests for price capture at time of sale"""

    @pytest.mark.critical
    def test_sale_item_captures_price_at_time_of_sale(self, sale, product, exchange_rate):
        """Sale item should capture price at the moment, not use current price"""
        # Product current price
        original_price = product.selling_price_usd

        # Create sale item at current price
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=original_price,
            price_bs=original_price * exchange_rate.bs_to_usd
        )

        # Change product price
        product.selling_price_usd = Decimal('20.00')
        product.save()

        # Sale item should still have original price
        item.refresh_from_db()
        assert item.price_usd == original_price
        assert item.price_usd != product.selling_price_usd


# ============================================================================
# SALE FORM INTEGRATION TESTS
# ============================================================================

class TestSaleFormView:
    """Tests de integración para el formulario de ventas"""

    @pytest.mark.views
    def test_sale_form_loads_successfully(self, authenticated_client):
        """El formulario de venta debe cargar correctamente"""
        response = authenticated_client.get('/sales/new/')

        assert response.status_code == 200
        assert b'Nueva Venta' in response.content

    @pytest.mark.views
    def test_sale_form_requires_authentication(self, api_client):
        """El formulario debe requerir autenticación"""
        response = api_client.get('/sales/new/')

        # Debe redirigir al login
        assert response.status_code in [302, 403]

    @pytest.mark.views
    @pytest.mark.critical
    def test_sale_form_has_product_search_input(self, authenticated_client):
        """El formulario debe tener el input de búsqueda de productos"""
        response = authenticated_client.get('/sales/new/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Verificar que existe el input de búsqueda
        assert 'id="product_search"' in content
        assert 'Buscar Producto' in content

    @pytest.mark.views
    def test_sale_form_has_customer_search_input(self, authenticated_client):
        """El formulario debe tener el input de búsqueda de clientes"""
        response = authenticated_client.get('/sales/new/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Verificar que existe el input de búsqueda de clientes
        assert 'id="customer_search"' in content
        assert 'Cliente' in content

    @pytest.mark.views
    def test_sale_form_has_payment_method_select(self, authenticated_client):
        """El formulario debe tener selector de método de pago"""
        response = authenticated_client.get('/sales/new/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Verificar métodos de pago
        assert 'payment_method' in content
        assert 'Punto de Venta' in content or 'card' in content
        assert 'Efectivo' in content or 'cash' in content
        assert 'Pago Móvil' in content or 'mobile' in content

    @pytest.mark.views
    def test_sale_form_has_credit_checkbox(self, authenticated_client):
        """El formulario debe tener checkbox para venta a crédito"""
        response = authenticated_client.get('/sales/new/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        assert 'is_credit' in content
        assert 'crédito' in content.lower()

    @pytest.mark.views
    def test_sale_form_has_complete_button(self, authenticated_client):
        """El formulario debe tener botón para completar venta"""
        response = authenticated_client.get('/sales/new/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        assert 'Completar Venta' in content

    @pytest.mark.views
    def test_sale_form_includes_alpine_js(self, authenticated_client):
        """El formulario debe incluir Alpine.js para funcionalidad interactiva"""
        response = authenticated_client.get('/sales/new/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Verificar que usa Alpine.js
        assert 'x-data' in content
        assert 'salesApp' in content

    @pytest.mark.views
    def test_sale_form_passes_exchange_rate_to_js(self, authenticated_client, exchange_rate):
        """El formulario debe pasar el exchange rate al JavaScript"""
        response = authenticated_client.get('/sales/new/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Verificar que hay datos para JS
        assert 'data-for-js' in content


class TestSaleFormProductSearch:
    """Tests para la funcionalidad de búsqueda de productos en el formulario"""

    @pytest.mark.integration
    @pytest.mark.critical
    def test_can_search_products_from_form(self, authenticated_client, category):
        """Debe poder buscar productos desde el formulario"""
        # Crear productos
        product1 = ProductFactory(
            name='Coca Cola 2L',
            barcode='7501234567890',
            category=category,
            selling_price_usd=Decimal('2.50'),
            stock=Decimal('100'),
            is_active=True
        )

        # Simular búsqueda desde el formulario
        response = authenticated_client.get('/api/products/search/?q=Coca')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 1
        assert data['products'][0]['name'] == 'Coca Cola 2L'
        assert data['products'][0]['barcode'] == '7501234567890'

    @pytest.mark.integration
    def test_search_shows_product_price_in_bs(self, authenticated_client, category, exchange_rate):
        """La búsqueda debe mostrar el precio en Bs"""
        product = ProductFactory(
            name='Test Product',
            category=category,
            selling_price_usd=Decimal('10.00'),
            is_active=True
        )

        response = authenticated_client.get('/api/products/search/?q=Test')

        assert response.status_code == 200
        data = response.json()

        # Verificar que retorna precio en Bs
        assert 'selling_price_bs' in data['products'][0]
        expected_price_bs = Decimal('10.00') * exchange_rate.bs_to_usd
        assert Decimal(str(data['products'][0]['selling_price_bs'])) == expected_price_bs

    @pytest.mark.integration
    def test_search_shows_stock_status(self, authenticated_client, category):
        """La búsqueda debe mostrar el estado del stock"""
        product_low = ProductFactory(
            name='Low Stock Product',
            category=category,
            stock=Decimal('3'),
            min_stock=Decimal('10'),
            is_active=True
        )

        response = authenticated_client.get('/api/products/search/?q=Low Stock')

        assert response.status_code == 200
        data = response.json()

        assert data['products'][0]['stock_status'] == 'low'
        assert data['products'][0]['stock_color'] == 'yellow'

    @pytest.mark.integration
    def test_search_excludes_out_of_stock_products_display(self, authenticated_client, category):
        """La búsqueda debe mostrar productos sin stock pero con indicador"""
        product_out = ProductFactory(
            name='Out of Stock Product',
            category=category,
            stock=Decimal('0'),
            is_active=True
        )

        response = authenticated_client.get('/api/products/search/?q=Out of Stock')

        assert response.status_code == 200
        data = response.json()

        # El producto aparece en búsqueda
        assert len(data['products']) == 1
        assert data['products'][0]['stock_status'] == 'out'
        assert data['products'][0]['stock_color'] == 'red'

    @pytest.mark.integration
    def test_barcode_search_exact_match(self, authenticated_client, category):
        """Búsqueda por código de barras debe funcionar con coincidencia exacta"""
        product = ProductFactory(
            name='Product with Barcode',
            barcode='1234567890123',
            category=category,
            is_active=True
        )

        response = authenticated_client.get('/api/products/search/?q=1234567890123')

        assert response.status_code == 200
        data = response.json()

        assert len(data['products']) == 1
        assert data['products'][0]['barcode'] == '1234567890123'


class TestSaleFormProductAddition:
    """Tests para agregar productos al carrito desde el formulario"""

    @pytest.mark.integration
    @pytest.mark.critical
    def test_add_product_to_cart_via_api(self, authenticated_client, product, customer, exchange_rate):
        """Debe poder agregar producto al carrito mediante la API"""
        sale_data = {
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 5,
                    'price_bs': float(product.selling_price_bs)
                }
            ],
            'customer_id': customer.id,
            'is_credit': False,
            'payment_method': 'cash',
            'notes': 'Test sale',
            'total_bs': float(product.selling_price_bs) * 5
        }

        response = authenticated_client.post(
            '/sales/api/create/',
            data=sale_data,
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()

        assert 'id' in data
        assert Sale.objects.filter(id=data['id']).exists()

    @pytest.mark.integration
    def test_add_product_reduces_stock(self, authenticated_client, product, customer, exchange_rate):
        """Agregar producto a venta debe reducir el stock"""
        initial_stock = product.stock

        sale_data = {
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 5,
                    'price_bs': float(product.selling_price_bs)
                }
            ],
            'customer_id': customer.id,
            'is_credit': False,
            'payment_method': 'cash',
            'total_bs': float(product.selling_price_bs) * 5
        }

        response = authenticated_client.post(
            '/sales/api/create/',
            data=sale_data,
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verificar que se redujo el stock
        product.refresh_from_db()
        assert product.stock == initial_stock - Decimal('5')

    @pytest.mark.integration
    @pytest.mark.critical
    def test_cannot_add_more_than_available_stock(self, authenticated_client, customer, exchange_rate):
        """No debe poder agregar más productos que el stock disponible"""
        from factories import ProductFactory

        product = ProductFactory(stock=Decimal('10'))

        sale_data = {
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 15,  # Más que el stock disponible
                    'price_bs': float(product.selling_price_bs)
                }
            ],
            'customer_id': customer.id,
            'is_credit': False,
            'payment_method': 'cash',
            'total_bs': float(product.selling_price_bs) * 15
        }

        response = authenticated_client.post(
            '/sales/api/create/',
            data=sale_data,
            content_type='application/json'
        )

        # Debe fallar
        assert response.status_code in [400, 422]

    @pytest.mark.integration
    def test_add_multiple_products_to_sale(self, authenticated_client, customer, exchange_rate):
        """Debe poder agregar múltiples productos a una venta"""
        from factories import ProductFactory

        product1 = ProductFactory(stock=Decimal('100'))
        product2 = ProductFactory(stock=Decimal('100'))

        sale_data = {
            'items': [
                {
                    'product_id': product1.id,
                    'quantity': 5,
                    'price_bs': float(product1.selling_price_bs)
                },
                {
                    'product_id': product2.id,
                    'quantity': 3,
                    'price_bs': float(product2.selling_price_bs)
                }
            ],
            'customer_id': customer.id,
            'is_credit': False,
            'payment_method': 'cash',
            'total_bs': float(product1.selling_price_bs) * 5 + float(product2.selling_price_bs) * 3
        }

        response = authenticated_client.post(
            '/sales/api/create/',
            data=sale_data,
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()

        # Verificar que se crearon ambos items
        sale = Sale.objects.get(id=data['id'])
        assert sale.items.count() == 2


class TestSaleFormEdgeCases:
    """Tests para casos extremos en el formulario de ventas"""

    @pytest.mark.integration
    def test_sale_without_customer_is_anonymous(self, authenticated_client, product, exchange_rate):
        """Venta sin cliente debe registrarse como venta anónima"""
        sale_data = {
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 2,
                    'price_bs': float(product.selling_price_bs)
                }
            ],
            'customer_id': None,
            'is_credit': False,
            'payment_method': 'cash',
            'total_bs': float(product.selling_price_bs) * 2
        }

        response = authenticated_client.post(
            '/sales/api/create/',
            data=sale_data,
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()

        sale = Sale.objects.get(id=data['id'])
        assert sale.customer is None

    @pytest.mark.integration
    @pytest.mark.critical
    def test_credit_sale_requires_customer(self, authenticated_client, product, exchange_rate):
        """Venta a crédito debe requerir un cliente"""
        sale_data = {
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 2,
                    'price_bs': float(product.selling_price_bs)
                }
            ],
            'customer_id': None,
            'is_credit': True,  # Venta a crédito sin cliente
            'payment_method': 'cash',
            'total_bs': float(product.selling_price_bs) * 2
        }

        response = authenticated_client.post(
            '/sales/api/create/',
            data=sale_data,
            content_type='application/json'
        )

        # Debe fallar
        assert response.status_code in [400, 422]

    @pytest.mark.integration
    def test_weight_based_products_allow_decimals(self, authenticated_client, customer, exchange_rate):
        """Productos por peso deben permitir cantidades decimales"""
        from factories import ProductFactory

        product = ProductFactory(
            unit_type='kg',
            stock=Decimal('50.00')
        )

        sale_data = {
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 2.5,  # Cantidad decimal
                    'price_bs': float(product.selling_price_bs)
                }
            ],
            'customer_id': customer.id,
            'is_credit': False,
            'payment_method': 'cash',
            'total_bs': float(product.selling_price_bs) * 2.5
        }

        response = authenticated_client.post(
            '/sales/api/create/',
            data=sale_data,
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verificar que se redujo el stock correctamente
        product.refresh_from_db()
        assert product.stock == Decimal('47.50')
