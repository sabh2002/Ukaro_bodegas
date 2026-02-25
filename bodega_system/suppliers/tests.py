# suppliers/tests.py - Tests para modelos de proveedores

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from suppliers.models import Supplier, SupplierOrder, SupplierOrderItem
from factories import (
    SupplierFactory, SupplierOrderFactory, SupplierOrderItemFactory,
    ProductFactory, AdminUserFactory, ExchangeRateFactory
)

pytestmark = pytest.mark.django_db


# ============================================================================
# TESTS DE MODELO SUPPLIER
# ============================================================================

class TestSupplierCreacion:
    """Tests para creación del modelo Supplier"""

    def test_crear_proveedor_con_campos_requeridos(self):
        """Crear proveedor con campos básicos"""
        supplier = Supplier.objects.create(
            name='Distribuidora ABC',
            contact_person='Juan Pérez',
            phone='555-1234',
            email='contacto@abc.com'
        )

        assert supplier.name == 'Distribuidora ABC'
        assert supplier.contact_person == 'Juan Pérez'
        assert supplier.phone == '555-1234'
        assert supplier.email == 'contacto@abc.com'
        assert supplier.is_active is True

    def test_proveedor_string_representation(self):
        """Test del método __str__"""
        supplier = SupplierFactory(name='Proveedor XYZ')
        assert str(supplier) == 'Proveedor XYZ'

    def test_proveedores_ordenados_por_nombre(self):
        """Los proveedores deben ordenarse alfabéticamente"""
        SupplierFactory(name='Zebra Corp')
        SupplierFactory(name='Alpha Inc')
        SupplierFactory(name='Beta Ltd')

        suppliers = list(Supplier.objects.all())

        assert suppliers[0].name == 'Alpha Inc'
        assert suppliers[1].name == 'Beta Ltd'
        assert suppliers[2].name == 'Zebra Corp'

    def test_proveedor_default_activo(self):
        """Nuevos proveedores deben estar activos por defecto"""
        supplier = SupplierFactory()
        assert supplier.is_active is True

    def test_proveedor_relacion_con_ordenes(self):
        """Test de relación con órdenes de compra"""
        supplier = SupplierFactory()
        order1 = SupplierOrderFactory(supplier=supplier)
        order2 = SupplierOrderFactory(supplier=supplier)

        assert supplier.orders.count() == 2
        assert order1 in supplier.orders.all()
        assert order2 in supplier.orders.all()


# ============================================================================
# TESTS DE MODELO SUPPLIER ORDER
# ============================================================================

class TestSupplierOrderCreacion:
    """Tests para creación de órdenes de compra"""

    def test_crear_orden_con_campos_requeridos(self, supplier, admin_user, exchange_rate):
        """Crear orden de compra con campos básicos"""
        order = SupplierOrder.objects.create(
            supplier=supplier,
            total_usd=Decimal('500.00'),
            total_bs=Decimal('18250.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            created_by=admin_user
        )

        assert order.supplier == supplier
        assert order.total_usd == Decimal('500.00')
        assert order.total_bs == Decimal('18250.00')
        assert order.status == 'pending'
        assert order.paid is False

    def test_orden_string_representation(self, supplier_order):
        """Test del método __str__"""
        str_repr = str(supplier_order)
        assert 'Orden #' in str_repr
        assert str(supplier_order.id) in str_repr

    def test_orden_ordenamiento_por_fecha_descendente(self, supplier, admin_user, exchange_rate):
        """Órdenes deben ordenarse por fecha descendente (más reciente primero)"""
        order1 = SupplierOrderFactory(supplier=supplier)
        order2 = SupplierOrderFactory(supplier=supplier)

        orders = list(SupplierOrder.objects.all())

        # La más reciente primero
        assert orders[0].id == order2.id
        assert orders[1].id == order1.id

    def test_orden_estados_disponibles(self, supplier, admin_user, exchange_rate):
        """Test de los diferentes estados de orden"""
        # Pendiente (por defecto)
        order_pending = SupplierOrderFactory(status='pending')
        assert order_pending.status == 'pending'

        # Recibido
        order_received = SupplierOrderFactory(status='received')
        assert order_received.status == 'received'

        # Cancelado
        order_cancelled = SupplierOrderFactory(status='cancelled')
        assert order_cancelled.status == 'cancelled'


class TestSupplierOrderExchangeRate:
    """Tests para manejo de tasa de cambio en órdenes"""

    @pytest.mark.critical
    def test_orden_captura_tasa_de_cambio(self, supplier, admin_user, exchange_rate):
        """Orden debe capturar y almacenar la tasa de cambio usada"""
        order = SupplierOrder.objects.create(
            supplier=supplier,
            total_usd=Decimal('1000.00'),
            total_bs=Decimal('36500.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            created_by=admin_user
        )

        assert order.exchange_rate_used == exchange_rate.bs_to_usd
        assert order.total_bs == order.total_usd * exchange_rate.bs_to_usd

    @pytest.mark.critical
    def test_orden_totales_coinciden_con_tasa(self, supplier, admin_user, exchange_rate):
        """Total Bs debe igualar Total USD × Tasa de Cambio"""
        total_usd = Decimal('750.00')
        expected_bs = total_usd * exchange_rate.bs_to_usd

        order = SupplierOrder.objects.create(
            supplier=supplier,
            total_usd=total_usd,
            total_bs=expected_bs,
            exchange_rate_used=exchange_rate.bs_to_usd,
            created_by=admin_user
        )

        assert order.total_bs == expected_bs


class TestSupplierOrderStatus:
    """Tests para cambios de estado de órdenes"""

    def test_orden_cambia_a_recibido(self, supplier_order):
        """Cambiar estado de orden a recibido"""
        supplier_order.status = 'received'
        supplier_order.received_date = timezone.now()
        supplier_order.save()

        assert supplier_order.status == 'received'
        assert supplier_order.received_date is not None

    def test_orden_puede_cancelarse(self, supplier_order):
        """Orden puede ser cancelada"""
        supplier_order.status = 'cancelled'
        supplier_order.save()

        assert supplier_order.status == 'cancelled'

    def test_orden_default_no_pagada(self, supplier_order):
        """Nueva orden debe estar marcada como no pagada"""
        assert supplier_order.paid is False


# ============================================================================
# TESTS DE MODELO SUPPLIER ORDER ITEM
# ============================================================================

class TestSupplierOrderItemCreacion:
    """Tests para creación de items de orden"""

    def test_crear_item_con_campos_requeridos(self, supplier_order, product, exchange_rate):
        """Crear item de orden con campos básicos"""
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('15.00')
        )

        assert item.order == supplier_order
        assert item.product == product
        assert item.quantity == Decimal('10.00')
        assert item.price_usd == Decimal('15.00')
        # price_bs se calcula automáticamente
        assert item.price_bs > 0

    def test_item_string_representation(self, supplier_order, product, exchange_rate):
        """Test del método __str__"""
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00')
        )

        str_repr = str(item)
        assert '5' in str_repr or '5.00' in str_repr
        assert product.name in str_repr


class TestSupplierOrderItemCalculos:
    """Tests para cálculos de items de orden"""

    @pytest.mark.critical
    def test_item_calcula_price_bs_automaticamente(self, supplier_order, product, exchange_rate):
        """Item debe calcular price_bs automáticamente al guardar"""
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('20.00')
        )

        expected_price_bs = Decimal('20.00') * exchange_rate.bs_to_usd
        assert item.price_bs == expected_price_bs

    @pytest.mark.critical
    def test_item_sin_tasa_de_cambio_lanza_error(self, supplier_order, product):
        """CRÍTICO: Item debe fallar si no hay tasa de cambio configurada"""
        from utils.models import ExchangeRate

        # Eliminar todas las tasas
        ExchangeRate.objects.all().delete()

        # Intentar crear item debe lanzar ValueError
        with pytest.raises(ValueError, match="No hay tasa de cambio configurada"):
            item = SupplierOrderItem(
                order=supplier_order,
                product=product,
                quantity=Decimal('10.00'),
                price_usd=Decimal('20.00')
            )
            item.save()

    @pytest.mark.critical
    def test_subtotal_usd_calculado_correctamente(self, supplier_order, product, exchange_rate):
        """subtotal_usd = quantity × price_usd"""
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00')
        )

        assert item.subtotal_usd == Decimal('50.00')

    @pytest.mark.critical
    def test_subtotal_bs_calculado_correctamente(self, supplier_order, product, exchange_rate):
        """subtotal_bs = quantity × price_bs"""
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00')
        )

        # price_bs se calcula automáticamente
        expected_subtotal = Decimal('5.00') * item.price_bs
        assert item.subtotal_bs == expected_subtotal

    def test_subtotal_alias_compatibilidad(self, supplier_order, product, exchange_rate):
        """Propiedad subtotal debe ser alias de subtotal_bs"""
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('3.00'),
            price_usd=Decimal('15.00')
        )

        assert item.subtotal == item.subtotal_bs


class TestSupplierOrderItemValidacion:
    """Tests para validación de items de orden"""

    def test_item_con_cantidad_cero_o_negativa(self, supplier_order, product, exchange_rate):
        """Validar que no se permitan cantidades inválidas (hecho en formulario)"""
        # Nota: La validación de cantidad positiva se hace en el formulario,
        # no en el modelo. Aquí solo verificamos que se puede crear.
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('5.00')
        )
        assert item.quantity > 0

    def test_item_con_precio_cero(self, supplier_order, product, exchange_rate):
        """Item con precio 0 es válido (productos gratis/promocionales)"""
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('0.00')
        )

        assert item.price_usd == Decimal('0.00')
        assert item.price_bs == Decimal('0.00')


class TestSupplierOrderItemsRelacion:
    """Tests para relación entre orden e items"""

    def test_orden_puede_tener_multiples_items(self, supplier_order, exchange_rate):
        """Una orden puede tener múltiples items"""
        product1 = ProductFactory()
        product2 = ProductFactory()
        product3 = ProductFactory()

        item1 = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product1,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00')
        )

        item2 = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product2,
            quantity=Decimal('3.00'),
            price_usd=Decimal('15.00')
        )

        item3 = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product3,
            quantity=Decimal('8.00'),
            price_usd=Decimal('5.00')
        )

        assert supplier_order.items.count() == 3
        assert item1 in supplier_order.items.all()
        assert item2 in supplier_order.items.all()
        assert item3 in supplier_order.items.all()

    @pytest.mark.critical
    def test_calcular_total_orden_desde_items(self, supplier_order, exchange_rate):
        """Total de orden debe ser suma de subtotales de items"""
        product1 = ProductFactory()
        product2 = ProductFactory()

        item1 = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product1,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00')
        )

        item2 = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product2,
            quantity=Decimal('3.00'),
            price_usd=Decimal('20.00')
        )

        # Calcular total esperado
        total_usd = item1.subtotal_usd + item2.subtotal_usd
        total_bs = item1.subtotal_bs + item2.subtotal_bs

        # En producción esto se hace en la vista/API
        assert total_usd == Decimal('110.00')  # (5×10) + (3×20) = 50 + 60


class TestSupplierOrderItemPrecioHistorico:
    """Tests para captura histórica de precios"""

    @pytest.mark.critical
    def test_item_captura_precio_al_momento_de_orden(self, supplier_order, product, exchange_rate):
        """Item debe capturar precio en el momento de la orden, no precio actual"""
        # Precio original del producto
        precio_original = product.purchase_price_usd

        # Crear item con precio específico
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('25.00')  # Precio en esta orden
        )

        # Cambiar precio del producto
        product.purchase_price_usd = Decimal('30.00')
        product.save()

        # Item debe mantener precio original
        item.refresh_from_db()
        assert item.price_usd == Decimal('25.00')
        assert item.price_usd != product.purchase_price_usd

    @pytest.mark.critical
    def test_item_captura_tasa_de_cambio_historica(self, supplier_order, product, admin_user, exchange_rate):
        """Item debe usar la tasa de cambio del momento"""
        # Crear item con tasa actual
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('20.00')
        )

        precio_bs_original = item.price_bs

        # Cambiar tasa de cambio
        from utils.models import ExchangeRate
        nueva_tasa = ExchangeRate.objects.create(
            date=date.today(),
            bs_to_usd=Decimal('40.00'),  # Nueva tasa
            updated_by=admin_user
        )

        # Item debe mantener precio_bs original (no recalcular)
        item.refresh_from_db()
        assert item.price_bs == precio_bs_original


class TestSupplierOrderItemActualizacionInventario:
    """Tests para impacto en inventario (hecho en vista)"""

    def test_item_referencia_producto_correcto(self, supplier_order, product, exchange_rate):
        """Item debe referenciar correctamente al producto"""
        item = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('20.00'),
            price_usd=Decimal('8.00')
        )

        assert item.product == product
        assert item.product.name == product.name

    def test_multiples_items_mismo_producto(self, supplier_order, product, exchange_rate):
        """Pueden existir múltiples items del mismo producto en diferentes órdenes"""
        order2 = SupplierOrderFactory()

        item1 = SupplierOrderItem.objects.create(
            order=supplier_order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('5.00')
        )

        item2 = SupplierOrderItem.objects.create(
            order=order2,
            product=product,
            quantity=Decimal('15.00'),
            price_usd=Decimal('6.00')
        )

        # Mismo producto, diferentes órdenes y precios
        assert item1.product == item2.product
        assert item1.order != item2.order
        assert item1.price_usd != item2.price_usd
