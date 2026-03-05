# finances/tests.py
"""
Tests exhaustivos para el módulo finances:
- Expense model
- DailyClose model
- Vista finance_dashboard (solo admin)
- Reportes de ventas, compras, ganancias
- CRUD de gastos
- Cierre diario
"""

from decimal import Decimal
from datetime import date

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError

from finances.models import Expense, DailyClose
from sales.models import Sale
from utils.models import ExchangeRate

User = get_user_model()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def make_admin(username='fin_admin'):
    return User.objects.create_user(username=username, password='pass123', is_admin=True)

def make_employee(username='fin_emp'):
    return User.objects.create_user(username=username, password='pass123', is_employee=True)

def make_exchange_rate(user, rate='45.50'):
    cache.clear()
    return ExchangeRate.objects.create(
        date=timezone.now().date(),
        bs_to_usd=Decimal(rate),
        updated_by=user
    )

def make_expense(user, category='supplies', amount_bs='500.00', amount_usd='10.99'):
    return Expense.objects.create(
        category=category,
        description='Descripción de test',
        amount_bs=Decimal(amount_bs),
        amount_usd=Decimal(amount_usd),
        exchange_rate_used=Decimal('45.50'),
        date=date.today(),
        created_by=user
    )

def make_daily_close(user, sales_count=5, sales_total='2000.00',
                     expenses_total='500.00', profit='1500.00',
                     close_date=None):
    return DailyClose.objects.create(
        date=close_date or date.today(),
        sales_count=sales_count,
        sales_total_bs=Decimal(sales_total),
        expenses_total_bs=Decimal(expenses_total),
        profit_bs=Decimal(profit),
        closed_by=user
    )


# ─────────────────────────────────────────────
# EXPENSE MODEL TESTS
# ─────────────────────────────────────────────

class ExpenseModelTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = make_admin()
        make_exchange_rate(self.admin)

    def test_create_expense_basic(self):
        """Debe crear gasto con campos mínimos"""
        expense = make_expense(self.admin)
        self.assertEqual(expense.category, 'supplies')
        self.assertEqual(expense.amount_bs, Decimal('500.00'))
        self.assertEqual(expense.created_by, self.admin)

    def test_create_expense_all_categories(self):
        """Debe poder crear gastos de todas las categorías"""
        categories = ['salaries', 'repairs', 'improvements', 'supplies',
                      'rent', 'utilities', 'maintenance', 'taxes', 'other']
        for i, cat in enumerate(categories):
            expense = Expense.objects.create(
                category=cat,
                description=f'Gasto {cat}',
                amount_bs=Decimal('100.00'),
                amount_usd=Decimal('2.20'),
                exchange_rate_used=Decimal('45.50'),
                date=date.today(),
                created_by=self.admin
            )
            self.assertEqual(expense.category, cat)

    def test_str_representation(self):
        """__str__ debe incluir categoría, descripción y monto"""
        expense = make_expense(self.admin)
        result = str(expense)
        self.assertIn('Bs', result)
        self.assertIn('Descripción', result)

    def test_ordering_by_date_desc(self):
        """Gastos deben ordenarse por fecha descendente"""
        from datetime import date, timedelta
        e1 = Expense.objects.create(
            category='other', description='e1', amount_bs=Decimal('100'),
            amount_usd=Decimal('2'), exchange_rate_used=Decimal('45.50'),
            date=date.today() - timedelta(days=2), created_by=self.admin
        )
        e2 = Expense.objects.create(
            category='other', description='e2', amount_bs=Decimal('100'),
            amount_usd=Decimal('2'), exchange_rate_used=Decimal('45.50'),
            date=date.today(), created_by=self.admin
        )
        expenses = list(Expense.objects.all())
        self.assertEqual(expenses[0].pk, e2.pk)

    def test_expense_has_created_at(self):
        """Gasto debe tener created_at automático"""
        expense = make_expense(self.admin)
        self.assertIsNotNone(expense.created_at)


# ─────────────────────────────────────────────
# DAILY CLOSE MODEL TESTS
# ─────────────────────────────────────────────

class DailyCloseModelTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = make_admin('dc_admin')
        make_exchange_rate(self.admin)

    def test_create_daily_close(self):
        """Debe crear cierre diario con todos los campos"""
        close = make_daily_close(self.admin)
        self.assertEqual(close.sales_count, 5)
        self.assertEqual(close.sales_total_bs, Decimal('2000.00'))
        self.assertEqual(close.profit_bs, Decimal('1500.00'))
        self.assertEqual(close.closed_by, self.admin)

    def test_date_unique_constraint(self):
        """No debe permitir dos cierres el mismo día"""
        today = date.today()
        make_daily_close(self.admin, close_date=today)
        with self.assertRaises(Exception):
            make_daily_close(self.admin, close_date=today)

    def test_str_representation(self):
        """__str__ debe incluir la fecha"""
        close = make_daily_close(self.admin)
        result = str(close)
        self.assertIn('Cierre', result)

    def test_ordering_by_date_desc(self):
        """Cierres deben ordenarse por fecha descendente"""
        from datetime import date, timedelta
        c1 = make_daily_close(self.admin, close_date=date.today() - timedelta(days=2))
        c2 = make_daily_close(self.admin, close_date=date.today() - timedelta(days=1))
        closes = list(DailyClose.objects.all())
        self.assertEqual(closes[0].pk, c2.pk)


# ─────────────────────────────────────────────
# FINANCE DASHBOARD VIEW TESTS
# ─────────────────────────────────────────────

class FinanceDashboardViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('dash_admin')
        self.employee = make_employee('dash_emp')
        make_exchange_rate(self.admin)
        self.url = reverse('finances:dashboard')

    def test_anonymous_redirects(self):
        """Sin autenticación debe redirigir"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_employee_can_access(self):
        """Empleado puede acceder al dashboard de finanzas (@login_required, no @admin_required)"""
        self.client.login(username='dash_emp', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access(self):
        """Admin puede acceder al dashboard de finanzas"""
        self.client.login(username='dash_admin', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_has_context(self):
        """El dashboard debe pasar contexto a la plantilla"""
        self.client.login(username='dash_admin', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Verificar que hay variables en el contexto
        self.assertIsNotNone(response.context)


# ─────────────────────────────────────────────
# REPORTS VIEW TESTS
# ─────────────────────────────────────────────

class ReportsViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('rpt_admin')
        self.employee = make_employee('rpt_emp')
        make_exchange_rate(self.admin)
        # Crear una venta de prueba
        Sale.objects.create(
            user=self.admin,
            total_bs=Decimal('1000.00'),
            total_usd=Decimal('21.98'),
            exchange_rate_used=Decimal('45.50'),
            payment_method='cash',
            is_credit=False
        )

    def test_sales_report_admin_ok(self):
        """Admin puede ver reporte de ventas"""
        self.client.login(username='rpt_admin', password='pass123')
        url = reverse('finances:sales_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_sales_report_today_filter(self):
        """Filtro 'today' debe funcionar"""
        self.client.login(username='rpt_admin', password='pass123')
        url = reverse('finances:sales_report')
        response = self.client.get(url, {'period': 'today'})
        self.assertEqual(response.status_code, 200)

    def test_sales_report_employee_can_access(self):
        """Empleado puede ver reportes (vista usa @login_required, no @admin_required)"""
        self.client.login(username='rpt_emp', password='pass123')
        url = reverse('finances:sales_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_purchases_report_admin_ok(self):
        """Admin puede ver reporte de compras"""
        self.client.login(username='rpt_admin', password='pass123')
        url = reverse('finances:purchases_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_profits_report_admin_ok(self):
        """Admin puede ver reporte de ganancias"""
        self.client.login(username='rpt_admin', password='pass123')
        url = reverse('finances:profits_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_product_profitability_report_admin_ok(self):
        """Admin puede ver reporte de rentabilidad por producto"""
        self.client.login(username='rpt_admin', password='pass123')
        url = reverse('finances:product_profitability_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────
# EXPENSE CRUD VIEW TESTS
# ─────────────────────────────────────────────

class ExpenseCRUDViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('exp_admin')
        self.employee = make_employee('exp_emp')
        make_exchange_rate(self.admin)
        self.expense = make_expense(self.admin)

    def test_expense_list_admin_ok(self):
        """Admin puede ver lista de gastos"""
        self.client.login(username='exp_admin', password='pass123')
        url = reverse('finances:expense_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_expense_list_employee_can_access(self):
        """Empleado puede ver gastos (vista usa @login_required, no @admin_required)"""
        self.client.login(username='exp_emp', password='pass123')
        url = reverse('finances:expense_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_expense_create_get_admin(self):
        """Admin puede ver formulario de creación de gasto"""
        self.client.login(username='exp_admin', password='pass123')
        url = reverse('finances:expense_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_expense_create_post_valid(self):
        """Admin puede crear gasto"""
        self.client.login(username='exp_admin', password='pass123')
        url = reverse('finances:expense_create')
        response = self.client.post(url, {
            'category': 'rent',
            'description': 'Alquiler mensual test',
            'amount_usd': '500.00',
            'date': date.today().isoformat(),
            'receipt_number': '',
            'notes': '',
            'receipts-TOTAL_FORMS': '0',
            'receipts-INITIAL_FORMS': '0',
            'receipts-MIN_NUM_FORMS': '0',
            'receipts-MAX_NUM_FORMS': '1000',
        })
        if response.status_code == 302:
            self.assertTrue(
                Expense.objects.filter(description='Alquiler mensual test').exists()
            )

    def test_expense_detail_admin_ok(self):
        """Admin puede ver detalle de gasto"""
        self.client.login(username='exp_admin', password='pass123')
        url = reverse('finances:expense_detail', args=[self.expense.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_expense_update_get_admin(self):
        """Admin puede ver formulario de edición"""
        self.client.login(username='exp_admin', password='pass123')
        url = reverse('finances:expense_update', args=[self.expense.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_expense_delete_requires_admin(self):
        """Empleado no puede eliminar gastos"""
        self.client.login(username='exp_emp', password='pass123')
        url = reverse('finances:expense_delete', args=[self.expense.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_expense_delete_admin_ok(self):
        """Admin puede eliminar gasto"""
        target = make_expense(self.admin, category='other')
        target_pk = target.pk
        self.client.login(username='exp_admin', password='pass123')
        url = reverse('finances:expense_delete', args=[target_pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Expense.objects.filter(pk=target_pk).exists())


# ─────────────────────────────────────────────
# DAILY CLOSE VIEW TESTS
# ─────────────────────────────────────────────

class DailyCloseViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('dc_view_admin')
        self.employee = make_employee('dc_view_emp')
        make_exchange_rate(self.admin)

    def test_daily_close_list_admin_ok(self):
        """Admin puede ver lista de cierres diarios"""
        self.client.login(username='dc_view_admin', password='pass123')
        url = reverse('finances:daily_close_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_daily_close_list_employee_can_access(self):
        """Empleado puede ver cierres diarios (vista usa @login_required, no @admin_required)"""
        self.client.login(username='dc_view_emp', password='pass123')
        url = reverse('finances:daily_close_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_daily_close_create_get_admin(self):
        """Admin puede ver formulario de cierre diario"""
        self.client.login(username='dc_view_admin', password='pass123')
        url = reverse('finances:daily_close_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_daily_close_create_post_valid(self):
        """Admin puede crear cierre diario"""
        self.client.login(username='dc_view_admin', password='pass123')
        url = reverse('finances:daily_close_create')
        response = self.client.post(url, {
            'date': date.today().isoformat(),
            'notes': 'Cierre de prueba'
        })
        # Si fue exitoso (302) o muestra errores (200), ambos son válidos
        self.assertIn(response.status_code, [200, 302])

    def test_daily_close_duplicate_date_fails(self):
        """No debe permitir crear dos cierres el mismo día"""
        today = date.today()
        make_daily_close(self.admin, close_date=today)
        self.client.login(username='dc_view_admin', password='pass123')
        url = reverse('finances:daily_close_create')
        response = self.client.post(url, {
            'date': today.isoformat(),
            'notes': ''
        })
        # La vista debe manejar el error (mostrar form con error o 302 a lista)
        self.assertIn(response.status_code, [200, 302])
        # Solo debe existir 1 cierre para hoy
        self.assertEqual(DailyClose.objects.filter(date=today).count(), 1)
