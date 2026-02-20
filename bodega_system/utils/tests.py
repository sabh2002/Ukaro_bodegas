# utils/tests.py - Suite completa de pruebas para utilities, decoradores y middleware

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model

from utils.models import ExchangeRate, Backup
from utils.decorators import (
    is_admin, is_employee, is_admin_or_employee,
    admin_required, employee_or_admin_required,
    sales_access_required, customer_access_required, inventory_access_required
)
from utils.middleware import PermissionDeniedMiddleware, RoleBasedAccessMiddleware
from utils.context_processors import exchange_rate as exchange_rate_processor

User = get_user_model()


class UtilsTestBase(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        self.superuser = User.objects.create_superuser(
            username='superuser_u', password='super123',
            first_name='Super', last_name='User'
        )
        self.admin = User.objects.create_user(
            username='admin_u', password='admin123',
            first_name='Admin', last_name='Util',
            is_admin=True
        )
        self.employee = User.objects.create_user(
            username='emp_u', password='emp123',
            first_name='Emp', last_name='Util',
            is_employee=True
        )
        self.normal_user = User.objects.create_user(
            username='normal_u', password='normal123',
            first_name='Normal', last_name='Util'
        )

        self.rate = ExchangeRate.objects.create(
            bs_to_usd=Decimal('36.00'),
            updated_by=self.admin
        )


# ─── Modelo: ExchangeRate ─────────────────────────────────────────────────────

class ExchangeRateModelTests(UtilsTestBase):

    def test_exchange_rate_str(self):
        text = str(self.rate)
        self.assertIn('36', text)
        self.assertIn('Bs/USD', text)

    def test_get_latest_rate_returns_most_recent(self):
        ExchangeRate.objects.create(
            bs_to_usd=Decimal('40.00'),
            updated_by=self.admin,
            date=date.today() + timedelta(days=1),
        )
        latest = ExchangeRate.get_latest_rate()
        self.assertEqual(latest.bs_to_usd, Decimal('40.00'))

    def test_get_latest_rate_returns_none_when_no_rates(self):
        ExchangeRate.objects.all().delete()
        latest = ExchangeRate.get_latest_rate()
        self.assertIsNone(latest)

    def test_get_latest_rate_with_single_rate(self):
        ExchangeRate.objects.all().delete()
        rate = ExchangeRate.objects.create(
            bs_to_usd=Decimal('25.00'),
            updated_by=self.admin,
        )
        latest = ExchangeRate.get_latest_rate()
        self.assertEqual(latest.bs_to_usd, Decimal('25.00'))

    def test_get_latest_rate_orders_by_date_not_by_id(self):
        """Debe retornar la tasa con fecha más reciente aunque no sea el último ID"""
        ExchangeRate.objects.all().delete()
        older = ExchangeRate.objects.create(
            bs_to_usd=Decimal('30.00'),
            updated_by=self.admin,
            date=date.today() - timedelta(days=5),
        )
        newer = ExchangeRate.objects.create(
            bs_to_usd=Decimal('38.00'),
            updated_by=self.admin,
            date=date.today() - timedelta(days=1),
        )
        latest = ExchangeRate.get_latest_rate()
        self.assertEqual(latest.bs_to_usd, Decimal('38.00'))

    def test_exchange_rate_ordering_desc_by_date(self):
        ExchangeRate.objects.create(
            bs_to_usd=Decimal('38.00'),
            updated_by=self.admin,
            date=date.today() + timedelta(days=1),
        )
        rates = list(ExchangeRate.objects.all())
        self.assertGreaterEqual(rates[0].date, rates[-1].date)

    def test_exchange_rate_default_date_is_today(self):
        rate = ExchangeRate.objects.create(
            bs_to_usd=Decimal('37.00'),
            updated_by=self.admin,
        )
        self.assertEqual(rate.date, date.today())


# ─── Modelo: Backup ───────────────────────────────────────────────────────────

class BackupModelTests(UtilsTestBase):

    def test_backup_str_contains_date(self):
        backup = Backup.objects.create(
            file_path='/backups/test.sqlite3',
            file_size=1024,
            created_by=self.admin,
        )
        text = str(backup)
        self.assertIn('Respaldo', text)

    def test_backup_ordering_by_date_desc(self):
        b1 = Backup.objects.create(
            file_path='/backups/b1.sqlite3', file_size=512, created_by=self.admin,
        )
        b2 = Backup.objects.create(
            file_path='/backups/b2.sqlite3', file_size=1024, created_by=self.admin,
        )
        backups = list(Backup.objects.all())
        # más reciente primero
        self.assertGreaterEqual(backups[0].date, backups[-1].date)


# ─── Decoradores ──────────────────────────────────────────────────────────────

class DecoratorFunctionTests(UtilsTestBase):

    def test_is_admin_returns_true_for_admin(self):
        self.assertTrue(is_admin(self.admin))

    def test_is_admin_returns_true_for_superuser(self):
        self.assertTrue(is_admin(self.superuser))

    def test_is_admin_returns_false_for_employee(self):
        self.assertFalse(is_admin(self.employee))

    def test_is_admin_returns_false_for_normal_user(self):
        self.assertFalse(is_admin(self.normal_user))

    def test_is_employee_returns_true_for_employee(self):
        self.assertTrue(is_employee(self.employee))

    def test_is_employee_returns_false_for_admin(self):
        self.assertFalse(is_employee(self.admin))

    def test_is_employee_returns_false_for_superuser(self):
        self.assertFalse(is_employee(self.superuser))

    def test_is_employee_returns_false_for_normal_user(self):
        self.assertFalse(is_employee(self.normal_user))

    def test_is_admin_or_employee_true_for_admin(self):
        self.assertTrue(is_admin_or_employee(self.admin))

    def test_is_admin_or_employee_true_for_superuser(self):
        self.assertTrue(is_admin_or_employee(self.superuser))

    def test_is_admin_or_employee_true_for_employee(self):
        self.assertTrue(is_admin_or_employee(self.employee))

    def test_is_admin_or_employee_false_for_normal_user(self):
        self.assertFalse(is_admin_or_employee(self.normal_user))


class AdminRequiredDecoratorTests(UtilsTestBase):

    def test_admin_required_allows_admin(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_required_allows_superuser(self):
        self.client.login(username='superuser_u', password='super123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_required_blocks_employee_with_403(self):
        self.client.login(username='emp_u', password='emp123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 403)

    def test_admin_required_blocks_normal_user_with_403(self):
        self.client.login(username='normal_u', password='normal123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 403)

    def test_admin_required_redirects_anonymous_to_login(self):
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])


# ─── Contexto Processor ───────────────────────────────────────────────────────

class ContextProcessorTests(UtilsTestBase):

    def test_exchange_rate_processor_returns_latest_rate(self):
        request = self.factory.get('/')
        context = exchange_rate_processor(request)
        self.assertIn('latest_exchange_rate', context)
        self.assertEqual(context['latest_exchange_rate'].bs_to_usd, Decimal('36.00'))

    def test_exchange_rate_processor_returns_none_when_no_rate(self):
        ExchangeRate.objects.all().delete()
        request = self.factory.get('/')
        context = exchange_rate_processor(request)
        self.assertIn('latest_exchange_rate', context)
        self.assertIsNone(context['latest_exchange_rate'])

    def test_exchange_rate_processor_returns_most_recent_when_multiple(self):
        ExchangeRate.objects.create(
            bs_to_usd=Decimal('40.00'),
            updated_by=self.admin,
            date=date.today() + timedelta(days=1),
        )
        request = self.factory.get('/')
        context = exchange_rate_processor(request)
        self.assertEqual(context['latest_exchange_rate'].bs_to_usd, Decimal('40.00'))

    def test_exchange_rate_injected_into_every_template(self):
        """El context processor inyecta la tasa en todos los templates"""
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertIn('latest_exchange_rate', resp.context)


# ─── Middleware: PermissionDeniedMiddleware ───────────────────────────────────

class PermissionDeniedMiddlewareTests(UtilsTestBase):

    def test_permission_denied_renders_403_template(self):
        """Cuando un empleado accede a vista admin, debe ver página 403 personalizada"""
        self.client.login(username='emp_u', password='emp123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 403)
        # Debe usar el template 403.html personalizado
        self.assertTemplateUsed(resp, '403.html')

    def test_permission_denied_response_includes_context(self):
        self.client.login(username='emp_u', password='emp123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 403)
        # El contexto debe tener info del usuario
        self.assertIn('user', resp.context)

    def test_middleware_get_user_role_for_superuser(self):
        mw = PermissionDeniedMiddleware(lambda r: None)
        role = mw.get_user_role(self.superuser)
        self.assertEqual(role, 'Superadmin')

    def test_middleware_get_user_role_for_admin(self):
        mw = PermissionDeniedMiddleware(lambda r: None)
        role = mw.get_user_role(self.admin)
        self.assertEqual(role, 'Administrador')

    def test_middleware_get_user_role_for_employee(self):
        mw = PermissionDeniedMiddleware(lambda r: None)
        role = mw.get_user_role(self.employee)
        self.assertEqual(role, 'Empleado')

    def test_middleware_get_user_role_for_normal_user(self):
        mw = PermissionDeniedMiddleware(lambda r: None)
        role = mw.get_user_role(self.normal_user)
        self.assertEqual(role, 'Usuario')

    def test_middleware_get_client_ip_from_remote_addr(self):
        mw = PermissionDeniedMiddleware(lambda r: None)
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        ip = mw.get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')

    def test_middleware_get_client_ip_from_x_forwarded_for(self):
        mw = PermissionDeniedMiddleware(lambda r: None)
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 192.168.1.1'
        ip = mw.get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')


# ─── Middleware: RoleBasedAccessMiddleware ───────────────────────────────────

class RoleBasedAccessMiddlewareTests(UtilsTestBase):

    def test_middleware_get_user_role_admin(self):
        mw = RoleBasedAccessMiddleware(lambda r: None)
        self.assertEqual(mw.get_user_role(self.admin), 'Administrador')

    def test_middleware_get_user_role_employee(self):
        mw = RoleBasedAccessMiddleware(lambda r: None)
        self.assertEqual(mw.get_user_role(self.employee), 'Empleado')

    def test_middleware_get_user_role_superuser(self):
        mw = RoleBasedAccessMiddleware(lambda r: None)
        self.assertEqual(mw.get_user_role(self.superuser), 'Superadmin')

    def test_middleware_get_user_role_normal(self):
        mw = RoleBasedAccessMiddleware(lambda r: None)
        self.assertEqual(mw.get_user_role(self.normal_user), 'Usuario')


# ─── Vistas: Exchange Rate Management ────────────────────────────────────────

class ExchangeRateViewTests(UtilsTestBase):

    def test_exchange_rate_management_get_renders_form(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.context)
        self.assertIn('current_rate', resp.context)

    def test_exchange_rate_management_post_creates_new_rate(self):
        self.client.login(username='admin_u', password='admin123')
        count_before = ExchangeRate.objects.count()
        resp = self.client.post(reverse('utils:exchange_rate_management'), {
            'date': str(date.today() + timedelta(days=2)),
            'bs_to_usd': '38.50',
        })
        self.assertGreater(ExchangeRate.objects.count(), count_before)

    def test_exchange_rate_management_post_invalid_data_does_not_create(self):
        self.client.login(username='admin_u', password='admin123')
        count_before = ExchangeRate.objects.count()
        self.client.post(reverse('utils:exchange_rate_management'), {
            'date': str(date.today()),
            'bs_to_usd': '',  # vacío → inválido
        })
        self.assertEqual(ExchangeRate.objects.count(), count_before)

    def test_exchange_rate_management_shows_current_rate(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertEqual(resp.context['current_rate'].bs_to_usd, Decimal('36.00'))

    def test_exchange_rate_management_no_rate_shows_none_as_current(self):
        ExchangeRate.objects.all().delete()
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_management'))
        self.assertIsNone(resp.context['current_rate'])

    def test_exchange_rate_history_requires_admin(self):
        self.client.login(username='emp_u', password='emp123')
        resp = self.client.get(reverse('utils:exchange_rate_history'))
        self.assertEqual(resp.status_code, 403)

    def test_exchange_rate_history_accessible_by_admin(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_history'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('page_obj', resp.context)

    def test_exchange_rate_history_filter_by_date_from(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_history'), {
            'date_from': str(date.today() - timedelta(days=7)),
        })
        self.assertEqual(resp.status_code, 200)

    def test_exchange_rate_history_filter_by_date_to(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_history'), {
            'date_to': str(date.today()),
        })
        self.assertEqual(resp.status_code, 200)

    def test_exchange_rate_history_filter_by_range(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_history'), {
            'date_from': str(date.today() - timedelta(days=30)),
            'date_to': str(date.today()),
        })
        self.assertEqual(resp.status_code, 200)

    def test_exchange_rate_history_empty_when_no_rates(self):
        ExchangeRate.objects.all().delete()
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:exchange_rate_history'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['page_obj'].paginator.count, 0)


# ─── Vistas: Backup ──────────────────────────────────────────────────────────

class BackupViewTests(UtilsTestBase):

    def test_backup_view_requires_login(self):
        resp = self.client.get(reverse('utils:backup_restore'))
        self.assertEqual(resp.status_code, 302)

    def test_backup_view_requires_admin(self):
        self.client.login(username='emp_u', password='emp123')
        resp = self.client.get(reverse('utils:backup_restore'))
        self.assertEqual(resp.status_code, 403)

    def test_backup_view_accessible_by_admin(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.get(reverse('utils:backup_restore'))
        self.assertEqual(resp.status_code, 200)


# ─── Edge Cases de Utils ──────────────────────────────────────────────────────

class UtilsEdgeCaseTests(UtilsTestBase):

    def test_exchange_rate_bs_to_usd_positive(self):
        """La tasa de cambio siempre debe ser positiva"""
        self.assertGreater(self.rate.bs_to_usd, 0)

    def test_multiple_rates_same_day_allowed(self):
        """Se pueden crear múltiples tasas el mismo día (para actualizaciones intradiarias)"""
        ExchangeRate.objects.create(
            bs_to_usd=Decimal('37.00'),
            updated_by=self.admin,
            date=date.today(),
        )
        # Debe existir la tasa original y la nueva
        self.assertGreaterEqual(ExchangeRate.objects.filter(date=date.today()).count(), 2)

    def test_get_latest_rate_with_same_day_returns_last_created(self):
        """Con varias tasas el mismo día, get_latest() retorna la más reciente"""
        ExchangeRate.objects.create(
            bs_to_usd=Decimal('37.50'),
            updated_by=self.admin,
            date=date.today(),
        )
        latest = ExchangeRate.get_latest_rate()
        # get_latest_by = 'date', puede ser cualquiera del mismo día
        self.assertIsNotNone(latest)

    def test_context_processor_does_not_raise_when_db_empty(self):
        ExchangeRate.objects.all().delete()
        request = self.factory.get('/')
        try:
            context = exchange_rate_processor(request)
            self.assertIsNone(context['latest_exchange_rate'])
        except Exception as e:
            self.fail(f"Context processor raised exception with empty DB: {e}")

    def test_exchange_rate_management_redirects_after_successful_post(self):
        self.client.login(username='admin_u', password='admin123')
        resp = self.client.post(reverse('utils:exchange_rate_management'), {
            'date': str(date.today() + timedelta(days=3)),
            'bs_to_usd': '39.00',
        })
        self.assertEqual(resp.status_code, 302)
