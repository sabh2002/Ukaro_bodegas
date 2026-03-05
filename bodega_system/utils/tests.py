# utils/tests.py
"""
Tests exhaustivos para el módulo utils:
- ExchangeRate model (get_latest_rate, caché)
- Decoradores de permisos (admin_required, employee_or_admin_required, etc.)
"""

from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from utils.models import ExchangeRate
from utils.decorators import is_admin, is_employee, is_admin_or_employee

User = get_user_model()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def make_admin(username='admin_utils'):
    return User.objects.create_user(username=username, password='pass123', is_admin=True)

def make_employee(username='employee_utils'):
    return User.objects.create_user(username=username, password='pass123', is_employee=True)

def make_exchange_rate(user, rate='45.50', days_offset=0):
    date = timezone.now().date() + timedelta(days=days_offset)
    return ExchangeRate.objects.create(
        date=date,
        bs_to_usd=Decimal(rate),
        updated_by=user
    )


# ─────────────────────────────────────────────
# EXCHANGE RATE MODEL TESTS
# ─────────────────────────────────────────────

class ExchangeRateModelTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = make_admin()

    def test_create_exchange_rate(self):
        """Debe crear una tasa con todos sus campos"""
        rate = ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.admin
        )
        self.assertEqual(rate.bs_to_usd, Decimal('45.50'))
        self.assertEqual(rate.updated_by, self.admin)
        self.assertIsNotNone(rate.date)

    def test_str_format(self):
        """__str__ debe mostrar fecha y tasa"""
        rate = make_exchange_rate(self.admin)
        resultado = str(rate)
        self.assertIn('45.50', resultado)

    def test_get_latest_rate_returns_most_recent(self):
        """get_latest_rate debe retornar la tasa más reciente"""
        make_exchange_rate(self.admin, '40.00', days_offset=-1)
        cache.clear()
        make_exchange_rate(self.admin, '50.00', days_offset=0)
        cache.clear()
        latest = ExchangeRate.get_latest_rate()
        self.assertEqual(latest.bs_to_usd, Decimal('50.00'))

    def test_get_latest_rate_returns_none_when_empty(self):
        """get_latest_rate debe retornar None cuando no hay tasas"""
        ExchangeRate.objects.all().delete()
        cache.clear()
        result = ExchangeRate.get_latest_rate()
        self.assertIsNone(result)

    def test_get_latest_rate_caches_result(self):
        """get_latest_rate debe almacenar el resultado en caché"""
        make_exchange_rate(self.admin, '45.50')
        cache.clear()
        ExchangeRate.get_latest_rate()
        cached = cache.get('exchange_rate_latest')
        self.assertIsNotNone(cached)
        self.assertEqual(cached.bs_to_usd, Decimal('45.50'))

    def test_save_invalidates_cache(self):
        """Guardar una nueva tasa debe invalidar el caché"""
        make_exchange_rate(self.admin, '45.00')
        cache.clear()
        ExchangeRate.get_latest_rate()  # poblar caché
        # Crear nueva tasa (el save() invalida el caché)
        make_exchange_rate(self.admin, '55.00', days_offset=1)
        cached = cache.get('exchange_rate_latest')
        self.assertIsNone(cached)  # caché invalidado

    def test_delete_invalidates_cache(self):
        """Eliminar una tasa debe invalidar el caché"""
        rate = make_exchange_rate(self.admin, '45.50')
        cache.clear()
        ExchangeRate.get_latest_rate()  # poblar caché
        rate.delete()
        cached = cache.get('exchange_rate_latest')
        self.assertIsNone(cached)  # caché invalidado

    def test_get_latest_rate_returns_correct_after_cache_miss(self):
        """Tras limpiar caché, get_latest_rate debe consultar BD"""
        r1 = make_exchange_rate(self.admin, '45.00', days_offset=-1)
        cache.clear()
        r2 = make_exchange_rate(self.admin, '60.00', days_offset=0)
        cache.clear()
        latest = ExchangeRate.get_latest_rate()
        self.assertEqual(latest.bs_to_usd, Decimal('60.00'))

    def test_ordering_most_recent_first(self):
        """Las tasas deben ordenarse por fecha descendente"""
        make_exchange_rate(self.admin, '40.00', days_offset=-2)
        cache.clear()
        make_exchange_rate(self.admin, '50.00', days_offset=-1)
        cache.clear()
        make_exchange_rate(self.admin, '60.00', days_offset=0)
        cache.clear()
        rates = list(ExchangeRate.objects.all())
        self.assertEqual(rates[0].bs_to_usd, Decimal('60.00'))
        self.assertEqual(rates[1].bs_to_usd, Decimal('50.00'))
        self.assertEqual(rates[2].bs_to_usd, Decimal('40.00'))


# ─────────────────────────────────────────────
# DECORATOR HELPER FUNCTIONS TESTS
# ─────────────────────────────────────────────

class DecoratorHelperFunctionsTest(TestCase):

    def setUp(self):
        self.admin = make_admin('dec_admin')
        self.employee = make_employee('dec_employee')
        self.regular = User.objects.create_user(username='dec_regular', password='pass123')
        self.superuser = User.objects.create_superuser(
            username='dec_super', password='pass123', email='s@t.com'
        )

    def test_is_admin_true_for_admin(self):
        self.assertTrue(is_admin(self.admin))

    def test_is_admin_true_for_superuser(self):
        self.assertTrue(is_admin(self.superuser))

    def test_is_admin_false_for_employee(self):
        self.assertFalse(is_admin(self.employee))

    def test_is_admin_false_for_regular(self):
        self.assertFalse(is_admin(self.regular))

    def test_is_employee_true_for_employee(self):
        self.assertTrue(is_employee(self.employee))

    def test_is_employee_false_for_admin(self):
        self.assertFalse(is_employee(self.admin))

    def test_is_admin_or_employee_true_for_admin(self):
        self.assertTrue(is_admin_or_employee(self.admin))

    def test_is_admin_or_employee_true_for_employee(self):
        self.assertTrue(is_admin_or_employee(self.employee))

    def test_is_admin_or_employee_false_for_regular(self):
        self.assertFalse(is_admin_or_employee(self.regular))


# ─────────────────────────────────────────────
# DECORATOR VIEW BEHAVIOR TESTS
# ─────────────────────────────────────────────

class AdminRequiredDecoratorTest(TestCase):
    """
    Prueba @admin_required (utils/decorators.py) en vistas de inventario.
    Este decorador lanza PermissionDenied (403) para usuarios no admin.
    Nota: accounts/views.py usa @user_passes_test (redirige 302, no lanza 403).
    """

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('view_admin')
        self.employee = make_employee('view_employee')
        self.regular = User.objects.create_user(username='view_regular', password='pass123')
        make_exchange_rate(self.admin)
        # product_create usa @admin_required de utils/decorators.py → 403 para no-admin
        self.url = reverse('inventory:product_create')

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_employee_gets_403(self):
        self.client.login(username='view_employee', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_regular_user_gets_403(self):
        self.client.login(username='view_regular', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access(self):
        self.client.login(username='view_admin', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class SalesAccessDecoratorTest(TestCase):
    """Prueba @sales_access_required en sale_list"""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('sale_admin_dec')
        self.employee = make_employee('sale_emp_dec')
        self.regular = User.objects.create_user(username='sale_reg_dec', password='pass123')
        ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.admin
        )
        self.url = reverse('sales:sale_list')

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_employee_can_access(self):
        self.client.login(username='sale_emp_dec', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access(self):
        self.client.login(username='sale_admin_dec', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_gets_403(self):
        self.client.login(username='sale_reg_dec', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
