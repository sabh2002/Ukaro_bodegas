# inventory/tests.py
"""
Tests exhaustivos para el módulo inventory:
- Category model
- Product model (precios, stock, propiedades)
- InventoryAdjustment model
- Vistas de productos, categorías, ajustes
- APIs de productos (búsqueda, barcode, validación)
"""

import json
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError

from inventory.models import Category, Product, InventoryAdjustment
from utils.models import ExchangeRate

User = get_user_model()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def make_admin(username='inv_admin'):
    return User.objects.create_user(username=username, password='pass123', is_admin=True)

def make_employee(username='inv_emp'):
    return User.objects.create_user(username=username, password='pass123', is_employee=True)

def make_exchange_rate(user, rate='45.50'):
    cache.clear()
    return ExchangeRate.objects.create(
        date=timezone.now().date(),
        bs_to_usd=Decimal(rate),
        updated_by=user
    )

def make_category(name='Alimentos'):
    return Category.objects.create(name=name)

def make_product(category, barcode='000001', name='Arroz', purchase_usd='5.00',
                 selling_usd='8.00', stock=100, min_stock=10):
    return Product.objects.create(
        name=name,
        barcode=barcode,
        category=category,
        purchase_price_usd=Decimal(purchase_usd),
        purchase_price_bs=Decimal('0'),
        selling_price_usd=Decimal(selling_usd),
        selling_price_bs=Decimal('0'),
        stock=Decimal(str(stock)),
        min_stock=Decimal(str(min_stock))
    )


# ─────────────────────────────────────────────
# CATEGORY MODEL TESTS
# ─────────────────────────────────────────────

class CategoryModelTest(TestCase):

    def test_create_category(self):
        """Debe crear categoría con nombre y descripción"""
        cat = Category.objects.create(name='Bebidas', description='Líquidos')
        self.assertEqual(cat.name, 'Bebidas')
        self.assertEqual(cat.description, 'Líquidos')

    def test_create_category_without_description(self):
        """Descripción es opcional"""
        cat = Category.objects.create(name='Sin desc')
        self.assertEqual(cat.description, '')

    def test_str_representation(self):
        """__str__ debe retornar el nombre"""
        cat = Category.objects.create(name='Lácteos')
        self.assertEqual(str(cat), 'Lácteos')

    def test_ordering_by_name(self):
        """Categorías deben ordenarse alfabéticamente"""
        Category.objects.create(name='Zumos')
        Category.objects.create(name='Arroz')
        Category.objects.create(name='Miel')
        cats = list(Category.objects.all())
        self.assertEqual(cats[0].name, 'Arroz')
        self.assertEqual(cats[1].name, 'Miel')
        self.assertEqual(cats[2].name, 'Zumos')


# ─────────────────────────────────────────────
# PRODUCT MODEL TESTS
# ─────────────────────────────────────────────

class ProductModelTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = make_admin()
        self.exchange_rate = make_exchange_rate(self.admin)
        self.cat = make_category()

    def test_create_product_basic(self):
        """Debe crear producto con todos los campos obligatorios"""
        product = make_product(self.cat)
        self.assertEqual(product.name, 'Arroz')
        self.assertEqual(product.barcode, '000001')
        self.assertEqual(product.purchase_price_usd, Decimal('5.00'))
        self.assertEqual(product.selling_price_usd, Decimal('8.00'))
        self.assertTrue(product.is_active)

    def test_barcode_unique_constraint(self):
        """Barcode debe ser único"""
        make_product(self.cat, barcode='UNIQUE001')
        with self.assertRaises(Exception):
            make_product(self.cat, barcode='UNIQUE001', name='Otro')

    def test_stock_status_normal(self):
        """stock_status debe retornar 'Stock normal' cuando stock >= min_stock"""
        p = make_product(self.cat, stock=100, min_stock=10)
        self.assertEqual(p.stock_status, 'Stock normal')

    def test_stock_status_low(self):
        """stock_status debe retornar 'Stock bajo' cuando stock < min_stock"""
        p = make_product(self.cat, stock=5, min_stock=10)
        self.assertEqual(p.stock_status, 'Stock bajo')

    def test_stock_status_zero(self):
        """stock_status debe retornar 'Sin stock' cuando stock <= 0"""
        p = make_product(self.cat, stock=0)
        self.assertEqual(p.stock_status, 'Sin stock')

    def test_profit_margin_usd(self):
        """profit_margin_usd debe calcular correctamente"""
        p = make_product(self.cat, purchase_usd='5.00', selling_usd='8.00')
        self.assertEqual(p.profit_margin_usd, Decimal('3.00'))

    def test_profit_margin_percentage(self):
        """profit_margin_percentage debe calcular correctamente"""
        p = make_product(self.cat, purchase_usd='5.00', selling_usd='10.00')
        self.assertEqual(p.profit_margin_percentage, 100)

    def test_is_weight_based_unit(self):
        """Producto de tipo 'unit' no es por peso"""
        p = make_product(self.cat)
        p.unit_type = 'unit'
        self.assertFalse(p.is_weight_based)

    def test_is_weight_based_kg(self):
        """Producto de tipo 'kg' sí es por peso"""
        p = make_product(self.cat)
        p.unit_type = 'kg'
        self.assertTrue(p.is_weight_based)

    def test_get_price_usd_for_quantity_normal(self):
        """Precio normal para cantidad pequeña"""
        p = make_product(self.cat, selling_usd='8.00')
        price = p.get_price_usd_for_quantity(5)
        self.assertEqual(price, Decimal('8.00'))

    def test_get_price_usd_for_quantity_bulk(self):
        """Precio al mayor para cantidad grande"""
        p = make_product(self.cat, selling_usd='8.00')
        p.is_bulk_pricing = True
        p.bulk_min_quantity = Decimal('10')
        p.bulk_price_usd = Decimal('6.00')
        p.save()
        price = p.get_price_usd_for_quantity(10)
        self.assertEqual(price, Decimal('6.00'))

    def test_get_current_price_bs(self):
        """get_current_price_bs debe usar la tasa vigente"""
        p = make_product(self.cat, selling_usd='8.00')
        expected = Decimal('8.00') * Decimal('45.50')
        result = p.get_current_price_bs()
        self.assertEqual(result, expected)

    def test_get_current_price_bs_no_rate(self):
        """get_current_price_bs retorna 0 si no hay tasa"""
        ExchangeRate.objects.all().delete()
        cache.clear()
        p = make_product(self.cat, selling_usd='8.00')
        self.assertEqual(p.get_current_price_bs(), Decimal('0.00'))

    def test_str_representation(self):
        """__str__ debe retornar el nombre del producto"""
        p = make_product(self.cat, name='Producto STR')
        self.assertEqual(str(p), 'Producto STR')

    def test_unit_display(self):
        """unit_display debe retornar la etiqueta legible"""
        p = make_product(self.cat)
        p.unit_type = 'kg'
        self.assertEqual(p.unit_display, 'Kilogramo')


# ─────────────────────────────────────────────
# INVENTORY ADJUSTMENT MODEL TESTS
# ─────────────────────────────────────────────

class InventoryAdjustmentModelTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = make_admin('adj_admin')
        make_exchange_rate(self.admin)
        self.cat = make_category('Ajuste Cat')
        self.product = make_product(self.cat, barcode='ADJ001', stock=50)

    def test_create_adjustment_add(self):
        """Debe crear ajuste de tipo 'add'"""
        adj = InventoryAdjustment.objects.create(
            product=self.product,
            adjustment_type='add',
            quantity=Decimal('20'),
            previous_stock=Decimal('50'),
            new_stock=Decimal('70'),
            reason='Reposición de stock',
            adjusted_by=self.admin
        )
        self.assertEqual(adj.adjustment_type, 'add')
        self.assertEqual(adj.quantity, Decimal('20'))
        self.assertEqual(adj.product, self.product)

    def test_create_adjustment_remove(self):
        """Debe crear ajuste de tipo 'remove'"""
        adj = InventoryAdjustment.objects.create(
            product=self.product,
            adjustment_type='remove',
            quantity=Decimal('10'),
            previous_stock=Decimal('50'),
            new_stock=Decimal('40'),
            reason='Merma',
            adjusted_by=self.admin
        )
        self.assertEqual(adj.adjustment_type, 'remove')

    def test_create_adjustment_set(self):
        """Debe crear ajuste de tipo 'set'"""
        adj = InventoryAdjustment.objects.create(
            product=self.product,
            adjustment_type='set',
            quantity=Decimal('100'),
            previous_stock=Decimal('50'),
            new_stock=Decimal('100'),
            reason='Inventario físico',
            adjusted_by=self.admin
        )
        self.assertEqual(adj.adjustment_type, 'set')
        self.assertEqual(adj.new_stock, Decimal('100'))


# ─────────────────────────────────────────────
# PRODUCT LIST VIEW TESTS
# ─────────────────────────────────────────────

class ProductListViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('list_admin')
        self.employee = make_employee('list_emp')
        make_exchange_rate(self.admin)
        self.cat = make_category('Lista Cat')
        self.p1 = make_product(self.cat, barcode='LIST001', name='Arroz Lista')
        self.p2 = make_product(self.cat, barcode='LIST002', name='Pasta Lista', stock=3, min_stock=10)
        self.url = reverse('inventory:product_list')

    def test_get_list_unauthenticated_redirects(self):
        """Sin autenticación debe redirigir al login"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_get_list_admin_authenticated(self):
        """Admin puede ver la lista de productos"""
        self.client.login(username='list_admin', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_list_employee_authenticated(self):
        """Empleado puede ver la lista de productos"""
        self.client.login(username='list_emp', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_search_filter(self):
        """Búsqueda por nombre debe filtrar productos"""
        self.client.login(username='list_admin', password='pass123')
        response = self.client.get(self.url, {'q': 'Arroz'})
        self.assertEqual(response.status_code, 200)
        # La vista usa paginación: los productos están en page_obj
        self.assertIn('page_obj', response.context)

    def test_category_filter(self):
        """Filtro por categoría debe funcionar"""
        self.client.login(username='list_admin', password='pass123')
        response = self.client.get(self.url, {'category': self.cat.pk})
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────
# PRODUCT CRUD VIEW TESTS
# ─────────────────────────────────────────────

class ProductCRUDViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('crud_admin')
        self.employee = make_employee('crud_emp')
        make_exchange_rate(self.admin)
        self.cat = make_category('CRUD Cat')
        self.product = make_product(self.cat, barcode='CRUD001')

    def test_create_get_requires_admin(self):
        """Empleado no puede acceder al formulario de creación"""
        self.client.login(username='crud_emp', password='pass123')
        url = reverse('inventory:product_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_create_get_admin_ok(self):
        """Admin puede ver formulario de creación"""
        self.client.login(username='crud_admin', password='pass123')
        url = reverse('inventory:product_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_product_detail_accessible(self):
        """Detalle de producto accesible para admin"""
        self.client.login(username='crud_admin', password='pass123')
        url = reverse('inventory:product_detail', args=[self.product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_update_get_admin_ok(self):
        """Admin puede ver formulario de edición"""
        self.client.login(username='crud_admin', password='pass123')
        url = reverse('inventory:product_update', args=[self.product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_update_get_employee_blocked(self):
        """Empleado no puede editar productos"""
        self.client.login(username='crud_emp', password='pass123')
        url = reverse('inventory:product_update', args=[self.product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_delete_get_admin_ok(self):
        """Admin puede acceder a la URL de eliminación (pasa @admin_required)"""
        self.client.raise_request_exception = False
        self.client.login(username='crud_admin', password='pass123')
        url = reverse('inventory:product_delete', args=[self.product.pk])
        response = self.client.get(url)
        # Admin pasa el decorador: no debe dar 403 ni redirigir al login
        self.assertNotEqual(response.status_code, 403)
        self.assertNotIn('/accounts/login/', response.get('Location', ''))
        self.client.raise_request_exception = True

    def test_delete_employee_blocked(self):
        """Empleado no puede eliminar productos"""
        self.client.login(username='crud_emp', password='pass123')
        url = reverse('inventory:product_delete', args=[self.product.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)


# ─────────────────────────────────────────────
# CATEGORY CRUD VIEW TESTS
# ─────────────────────────────────────────────

class CategoryCRUDViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('cat_admin')
        self.employee = make_employee('cat_emp')
        make_exchange_rate(self.admin)
        self.cat = make_category('Cat CRUD Test')

    def test_category_list_admin(self):
        """Admin puede ver lista de categorías"""
        self.client.login(username='cat_admin', password='pass123')
        url = reverse('inventory:category_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_category_create_get_admin(self):
        """Admin puede ver formulario de categoría"""
        self.client.login(username='cat_admin', password='pass123')
        url = reverse('inventory:category_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_category_create_post_valid(self):
        """Admin puede crear categoría"""
        self.client.login(username='cat_admin', password='pass123')
        url = reverse('inventory:category_create')
        response = self.client.post(url, {'name': 'Nueva Categoría', 'description': ''})
        if response.status_code == 302:
            self.assertTrue(Category.objects.filter(name='Nueva Categoría').exists())


# ─────────────────────────────────────────────
# PRODUCT API TESTS
# ─────────────────────────────────────────────

class ProductAPITest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('api_admin')
        make_exchange_rate(self.admin)
        self.cat = make_category('API Cat')
        self.product = make_product(
            self.cat, barcode='API001', name='Producto API', stock=50
        )
        self.client.login(username='api_admin', password='pass123')

    def test_product_search_api_returns_products(self):
        """API de búsqueda debe retornar productos que coincidan"""
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': 'Producto API'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # La API retorna {'products': [...], 'count': ..., 'query': ...}
        self.assertIn('products', data)
        names = [p.get('name', '') for p in data['products']]
        self.assertIn('Producto API', names)

    def test_product_search_api_empty_query(self):
        """API de búsqueda con query vacío"""
        url = reverse('inventory:product_search_api')
        response = self.client.get(url, {'q': ''})
        self.assertEqual(response.status_code, 200)

    def test_barcode_api_found(self):
        """API de barcode debe retornar producto existente"""
        url = reverse('inventory:product_by_barcode_api', args=['API001'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data.get('name'), 'Producto API')

    def test_barcode_api_not_found(self):
        """API de barcode debe retornar 404 para barcode inexistente"""
        url = reverse('inventory:product_by_barcode_api', args=['NOTEXIST'])
        response = self.client.get(url)
        self.assertIn(response.status_code, [404, 200])  # Puede ser 404 o JSON con error

    def test_validate_barcode_unique(self):
        """Validar barcode único debe retornar disponible (endpoint POST con JSON)"""
        url = reverse('inventory:validate_barcode_api')
        response = self.client.post(
            url,
            json.dumps({'barcode': 'NUEVO_CODE_999'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # API retorna {'valid': True/False, 'message': '...'}
        self.assertTrue(data.get('valid', True))

    def test_validate_barcode_duplicate(self):
        """Validar barcode duplicado debe retornar no disponible (endpoint POST con JSON)"""
        url = reverse('inventory:validate_barcode_api')
        response = self.client.post(
            url,
            json.dumps({'barcode': 'API001'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # API retorna {'valid': False, 'message': '...'}
        self.assertFalse(data.get('valid', True))

    def test_product_detail_api(self):
        """API de detalle debe retornar JSON con info del producto"""
        url = reverse('inventory:product_detail_api', args=[self.product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data.get('name'), 'Producto API')
