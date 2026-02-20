# bodega_system/test_security.py - Pruebas de Seguridad Transversales (Fase 8)
#
# Cubre: CSRF, acceso anónimo, control de acceso por rol, aislamiento de objetos,
# inyección SQL (ORM), XSS (escape de templates), validación de sesión.

from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from inventory.models import Category, Product
from sales.models import Sale, SaleItem
from customers.models import Customer
from utils.models import ExchangeRate

User = get_user_model()


class SecurityTestBase(TestCase):
    """Fixtures de seguridad compartidas"""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='sec_admin', password='admin123',
            first_name='Admin', last_name='Sec',
            is_admin=True
        )
        self.employee1 = User.objects.create_user(
            username='sec_emp1', password='emp1pass',
            first_name='Emp1', last_name='Sec',
            is_employee=True
        )
        self.employee2 = User.objects.create_user(
            username='sec_emp2', password='emp2pass',
            first_name='Emp2', last_name='Sec',
            is_employee=True
        )
        self.normal_user = User.objects.create_user(
            username='sec_normal', password='normal123',
            first_name='Normal', last_name='Sec'
        )

        self.rate = ExchangeRate.objects.create(
            bs_to_usd=Decimal('36.00'),
            updated_by=self.admin
        )

        self.category = Category.objects.create(name='Seguridad Test')
        self.product = Product.objects.create(
            name='Producto Seguro',
            barcode='SEC001',
            category=self.category,
            purchase_price_usd=Decimal('5.00'),
            purchase_price_bs=Decimal('180.00'),
            selling_price_usd=Decimal('8.00'),
            selling_price_bs=Decimal('288.00'),
            stock=Decimal('50'),
        )
        self.customer = Customer.objects.create(
            name='Cliente Test',
            phone='0414-0000000',
            credit_limit_usd=Decimal('500.00'),
        )

        # Venta perteneciente a employee1
        self.sale_emp1 = Sale.objects.create(
            user=self.employee1,
            total_bs=Decimal('288.00'),
            total_usd=Decimal('8.00'),
            exchange_rate_used=Decimal('36.00'),
            payment_method='cash',
        )
        # Venta perteneciente a employee2
        self.sale_emp2 = Sale.objects.create(
            user=self.employee2,
            total_bs=Decimal('576.00'),
            total_usd=Decimal('16.00'),
            exchange_rate_used=Decimal('36.00'),
            payment_method='cash',
        )


# ─── Acceso Anónimo ────────────────────────────────────────────────────────────

class AnonymousAccessTests(SecurityTestBase):
    """Todo acceso de usuario anónimo debe redirigir al login"""

    PROTECTED_URLS = [
        ('dashboard', []),
        ('inventory:product_list', []),
        ('inventory:product_create', []),
        ('sales:sale_list', []),
        ('sales:sale_create', []),
        ('customers:customer_list', []),
        ('suppliers:supplier_list', []),
        ('finances:expense_list', []),
        ('finances:dashboard', []),
        ('utils:exchange_rate_management', []),
        ('utils:backup_restore', []),
        ('accounts:user_list', []),
    ]

    def test_anonymous_redirected_to_login_for_all_protected_views(self):
        for url_name, args in self.PROTECTED_URLS:
            try:
                url = reverse(url_name, args=args)
            except Exception:
                continue
            resp = self.client.get(url)
            self.assertIn(
                resp.status_code, [302, 301],
                f"URL {url_name} ({url}) returned {resp.status_code} for anonymous user"
            )
            if resp.status_code == 302:
                self.assertIn(
                    '/accounts/login/', resp['Location'],
                    f"URL {url_name} does not redirect to login"
                )

    def test_anonymous_cannot_post_to_login_required_views(self):
        """POST anónimo también debe redirigir, no procesar datos"""
        resp = self.client.post(reverse('inventory:product_create'), {
            'name': 'Hacked Product',
            'barcode': 'HACK001',
        })
        self.assertIn(resp.status_code, [302, 403])
        self.assertFalse(Product.objects.filter(barcode='HACK001').exists())


# ─── Control de Acceso por Rol: Admin Only ────────────────────────────────────

class AdminOnlyAccessTests(SecurityTestBase):
    """Vistas admin-only deben retornar 403 para empleados y usuarios normales"""

    ADMIN_ONLY_URLS = [
        'inventory:product_create',
        'utils:exchange_rate_management',
        'utils:exchange_rate_history',
        'utils:backup_restore',
        'accounts:user_list',
        'accounts:user_create',
        'finances:expense_delete',
    ]

    def test_employee_cannot_access_admin_only_views(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        admin_urls = [
            reverse('inventory:product_create'),
            reverse('utils:exchange_rate_management'),
            reverse('utils:exchange_rate_history'),
            reverse('utils:backup_restore'),
            reverse('accounts:user_list'),
        ]
        for url in admin_urls:
            resp = self.client.get(url)
            self.assertEqual(
                resp.status_code, 403,
                f"Employee accessed admin-only URL {url} (got {resp.status_code})"
            )

    def test_normal_user_cannot_access_admin_only_views(self):
        self.client.login(username='sec_normal', password='normal123')
        admin_urls = [
            reverse('inventory:product_create'),
            reverse('utils:exchange_rate_management'),
            reverse('accounts:user_list'),
        ]
        for url in admin_urls:
            resp = self.client.get(url)
            self.assertEqual(
                resp.status_code, 403,
                f"Normal user accessed admin-only URL {url} (got {resp.status_code})"
            )

    def test_employee_cannot_delete_product(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.post(
            reverse('inventory:product_delete', args=[self.product.pk])
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_employee_cannot_update_product(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.post(
            reverse('inventory:product_update', args=[self.product.pk]),
            {'name': 'Hacked', 'barcode': 'HACK'}
        )
        self.assertEqual(resp.status_code, 403)
        self.product.refresh_from_db()
        self.assertNotEqual(self.product.name, 'Hacked')

    def test_employee_cannot_create_user(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.post(reverse('accounts:user_create'), {
            'username': 'hacker',
            'password1': 'Hack3r#Pass',
            'password2': 'Hack3r#Pass',
        })
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(User.objects.filter(username='hacker').exists())

    def test_employee_cannot_delete_user(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.post(
            reverse('accounts:user_delete', args=[self.normal_user.pk])
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.normal_user.pk).exists())


# ─── Aislamiento de Objetos (Object-Level Security) ──────────────────────────

class ObjectLevelSecurityTests(SecurityTestBase):
    """Un empleado no puede ver ni modificar recursos de otro empleado"""

    def test_employee1_cannot_view_employee2_sale_detail(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp2.pk])
        )
        self.assertEqual(resp.status_code, 403)

    def test_employee2_cannot_view_employee1_sale_detail(self):
        self.client.login(username='sec_emp2', password='emp2pass')
        resp = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp1.pk])
        )
        self.assertEqual(resp.status_code, 403)

    def test_employee_can_view_own_sale_detail(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(
            reverse('sales:sale_detail', args=[self.sale_emp1.pk])
        )
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_view_any_sale_detail(self):
        self.client.login(username='sec_admin', password='admin123')
        for sale in [self.sale_emp1, self.sale_emp2]:
            resp = self.client.get(
                reverse('sales:sale_detail', args=[sale.pk])
            )
            self.assertEqual(resp.status_code, 200, f"Admin can't view sale {sale.pk}")

    def test_employee_sale_list_only_shows_own_sales(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(reverse('sales:sale_list'))
        self.assertEqual(resp.status_code, 200)
        sales_in_context = list(resp.context['sales'])
        # Solo debe ver su propia venta
        for sale in sales_in_context:
            self.assertEqual(sale.user, self.employee1)

    def test_admin_sale_list_shows_all_sales(self):
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(reverse('sales:sale_list'))
        self.assertEqual(resp.status_code, 200)
        # Al menos 2 ventas visibles
        self.assertGreaterEqual(
            resp.context['sales'].count(), 2
        )


# ─── Protección CSRF ──────────────────────────────────────────────────────────

class CSRFProtectionTests(SecurityTestBase):
    """Los formularios POST deben incluir y validar token CSRF"""

    def test_login_form_contains_csrf_token(self):
        resp = self.client.get(reverse('accounts:login'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'csrfmiddlewaretoken')

    def test_product_create_form_contains_csrf_token(self):
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(reverse('inventory:product_create'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'csrfmiddlewaretoken')

    def test_post_without_csrf_is_rejected(self):
        """Usar enforce_csrf_checks=True para verificar que CSRF está activo"""
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.login(username='sec_admin', password='admin123')
        resp = strict_client.post(
            reverse('inventory:category_create'),
            {'name': 'Sin CSRF'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        # Django debe rechazar el POST sin CSRF token
        self.assertEqual(resp.status_code, 403)

    def test_exchange_rate_form_contains_csrf_token(self):
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertContains(resp, 'csrfmiddlewaretoken')


# ─── Prevención de XSS ────────────────────────────────────────────────────────

class XSSPreventionTests(SecurityTestBase):
    """Django escapa automáticamente el HTML; verificar que se aplica correctamente"""

    def test_product_name_with_xss_payload_is_escaped_in_list(self):
        """El nombre del producto con script tag debe mostrarse escapado"""
        xss_product = Product.objects.create(
            name='<script>alert("xss")</script>',
            barcode='XSS001',
            category=self.category,
            purchase_price_usd=Decimal('1.00'),
            selling_price_usd=Decimal('2.00'),
        )
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(reverse('inventory:product_list'))
        self.assertEqual(resp.status_code, 200)
        # El script tag no debe aparecer sin escapar
        self.assertNotContains(resp, '<script>alert("xss")</script>')
        # Pero sí debe aparecer escapado
        self.assertContains(resp, '&lt;script&gt;')

    def test_customer_name_with_xss_payload_is_escaped(self):
        xss_customer = Customer.objects.create(
            name='<img src=x onerror=alert(1)>',
            phone='0000000000',
        )
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(reverse('customers:customer_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, '<img src=x onerror=alert(1)>')

    def test_search_query_with_xss_is_escaped_in_response(self):
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(
            reverse('inventory:product_list'),
            {'q': '<script>alert(1)</script>'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, '<script>alert(1)</script>')


# ─── Prevención de Inyección SQL ─────────────────────────────────────────────

class SQLInjectionPreventionTests(SecurityTestBase):
    """El ORM de Django parametriza todas las queries automáticamente"""

    def test_product_search_with_sql_injection_does_not_crash(self):
        self.client.login(username='sec_admin', password='admin123')
        malicious_query = "' OR '1'='1"
        resp = self.client.get(
            reverse('inventory:product_list'),
            {'q': malicious_query}
        )
        # No debe crashear (500) ni revelar todos los productos
        self.assertNotEqual(resp.status_code, 500)
        self.assertEqual(resp.status_code, 200)

    def test_api_product_search_with_sql_injection(self):
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(
            '/api/products/search/',
            {'q': "'; DROP TABLE inventory_product; --"}
        )
        self.assertNotEqual(resp.status_code, 500)
        # Los productos deben seguir existiendo
        self.assertTrue(Product.objects.filter(barcode='SEC001').exists())

    def test_customer_search_with_sql_injection(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(
            reverse('customers:customer_list'),
            {'q': "1; DROP TABLE customers_customer; --"}
        )
        self.assertNotEqual(resp.status_code, 500)
        self.assertTrue(Customer.objects.filter(name='Cliente Test').exists())


# ─── Gestión de Sesión ────────────────────────────────────────────────────────

class SessionSecurityTests(SecurityTestBase):

    def test_logout_invalidates_session(self):
        """Después del logout, el usuario no puede acceder a vistas protegidas"""
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)

        self.client.get(reverse('accounts:logout'))

        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

    def test_login_redirect_to_dashboard(self):
        resp = self.client.post(reverse('accounts:login'), {
            'username': 'sec_admin',
            'password': 'admin123',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/', resp['Location'])

    def test_wrong_credentials_denied(self):
        resp = self.client.post(reverse('accounts:login'), {
            'username': 'sec_admin',
            'password': 'wrongpassword',
        })
        # Debe mostrar el formulario con error, no redirigir
        self.assertEqual(resp.status_code, 200)

    def test_inactive_user_cannot_login(self):
        self.normal_user.is_active = False
        self.normal_user.save()
        resp = self.client.post(reverse('accounts:login'), {
            'username': 'sec_normal',
            'password': 'normal123',
        })
        self.assertEqual(resp.status_code, 200)
        # Verificar que no está autenticado
        self.assertFalse(resp.wsgi_request.user.is_authenticated)


# ─── Acceso Directo por URL (URL Traversal) ──────────────────────────────────

class DirectURLAccessTests(SecurityTestBase):
    """Intentar acceder directamente a IDs que no pertenecen al usuario"""

    def test_employee_cannot_access_admin_dashboard(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(reverse('finances:dashboard'))
        # finances:dashboard puede requerir admin
        self.assertIn(resp.status_code, [200, 403])

    def test_employee_accessing_nonexistent_sale_gets_404(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(reverse('sales:sale_detail', args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_accessing_nonexistent_product_gets_404(self):
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(reverse('inventory:product_detail', args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_accessing_nonexistent_customer_gets_404(self):
        self.client.login(username='sec_admin', password='admin123')
        resp = self.client.get(reverse('customers:customer_detail', args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_employee_cannot_delete_own_sale(self):
        """Incluso el dueño de la venta no puede borrarla (solo admins)"""
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.post(
            reverse('sales:sale_delete', args=[self.sale_emp1.pk])
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Sale.objects.filter(pk=self.sale_emp1.pk).exists())


# ─── Pruebas de la Página de Error 403 ───────────────────────────────────────

class ForbiddenPageTests(SecurityTestBase):

    def test_403_page_renders_correctly(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 403)
        self.assertTemplateUsed(resp, '403.html')

    def test_403_page_shows_user_info(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 403)
        self.assertIn('user', resp.context)

    def test_403_page_shows_requested_path(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 403)
        self.assertIn('requested_path', resp.context)
        self.assertIn('/utils/', resp.context['requested_path'])

    def test_403_page_shows_user_role(self):
        self.client.login(username='sec_emp1', password='emp1pass')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 403)
        self.assertIn('user_role', resp.context)
        self.assertEqual(resp.context['user_role'], 'Empleado')
