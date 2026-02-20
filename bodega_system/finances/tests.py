# finances/tests.py - Suite completa de pruebas para el módulo de finanzas

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from finances.models import Expense, ExpenseReceipt, DailyClose
from finances.forms import ExpenseForm, DailyCloseForm, ReportFilterForm
from utils.models import ExchangeRate

User = get_user_model()


class FinanceTestBase(TestCase):
    """Base con fixtures comunes para todos los tests de finances"""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_fin', password='admin123',
            first_name='Admin', last_name='Fin',
            is_admin=True
        )
        self.employee = User.objects.create_user(
            username='emp_fin', password='emp123',
            first_name='Emp', last_name='Fin',
            is_employee=True
        )
        self.normal_user = User.objects.create_user(
            username='normal_fin', password='normal123',
            first_name='Normal', last_name='Fin'
        )

        self.rate = ExchangeRate.objects.create(
            bs_to_usd=Decimal('36.00'),
            updated_by=self.admin
        )

        self.expense = Expense.objects.create(
            category='rent',
            description='Alquiler del mes de enero',
            amount_bs=Decimal('5000.00'),
            amount_usd=Decimal('138.89'),
            exchange_rate_used=Decimal('36.00'),
            date=date.today(),
            created_by=self.admin,
        )

        self.daily_close = DailyClose.objects.create(
            date=date.today() - timedelta(days=1),
            sales_count=10,
            sales_total_bs=Decimal('50000.00'),
            expenses_total_bs=Decimal('5000.00'),
            profit_bs=Decimal('45000.00'),
            closed_by=self.admin,
        )


# ─── Modelos ──────────────────────────────────────────────────────────────────

class ExpenseModelTests(FinanceTestBase):

    def test_expense_str(self):
        text = str(self.expense)
        self.assertIn('Alquiler', text)
        self.assertIn('5000', text)

    def test_expense_get_absolute_url(self):
        url = self.expense.get_absolute_url()
        self.assertIn(str(self.expense.pk), url)

    def test_expense_category_choices(self):
        categories = [c[0] for c in Expense.EXPENSE_CATEGORIES]
        for cat in ['salaries', 'repairs', 'improvements', 'supplies',
                    'rent', 'utilities', 'maintenance', 'taxes', 'other']:
            self.assertIn(cat, categories)

    def test_expense_ordering_by_date_desc(self):
        expense2 = Expense.objects.create(
            category='other',
            description='Gasto antiguo',
            amount_bs=Decimal('100.00'),
            amount_usd=Decimal('2.78'),
            exchange_rate_used=Decimal('36.00'),
            date=date.today() - timedelta(days=5),
            created_by=self.admin,
        )
        expenses = list(Expense.objects.all())
        # El más reciente debe aparecer primero
        self.assertGreaterEqual(expenses[0].date, expenses[-1].date)

    def test_expense_each_category_display(self):
        """Cada categoría tiene su display correcto"""
        expense = Expense.objects.create(
            category='salaries',
            description='Sueldo enero',
            amount_bs=Decimal('10000.00'),
            amount_usd=Decimal('277.78'),
            exchange_rate_used=Decimal('36.00'),
            date=date.today(),
            created_by=self.admin,
        )
        self.assertEqual(expense.get_category_display(), 'Sueldos de Empleados')


class DailyCloseModelTests(FinanceTestBase):

    def test_daily_close_str(self):
        text = str(self.daily_close)
        self.assertIn('Cierre', text)

    def test_daily_close_unique_date(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            DailyClose.objects.create(
                date=self.daily_close.date,  # misma fecha → debe fallar
                sales_count=5,
                sales_total_bs=Decimal('1000.00'),
                expenses_total_bs=Decimal('100.00'),
                profit_bs=Decimal('900.00'),
                closed_by=self.admin,
            )

    def test_daily_close_profit_calculation_stored(self):
        # profit_bs se almacena tal como se envía
        self.assertEqual(self.daily_close.profit_bs, Decimal('45000.00'))

    def test_daily_close_ordering_by_date_desc(self):
        DailyClose.objects.create(
            date=date.today() - timedelta(days=10),
            sales_count=5,
            sales_total_bs=Decimal('10000.00'),
            expenses_total_bs=Decimal('1000.00'),
            profit_bs=Decimal('9000.00'),
            closed_by=self.admin,
        )
        closes = list(DailyClose.objects.all())
        self.assertGreaterEqual(closes[0].date, closes[-1].date)


class ExpenseReceiptModelTests(FinanceTestBase):

    def test_expense_receipt_str(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        receipt = ExpenseReceipt.objects.create(
            expense=self.expense,
            file=SimpleUploadedFile('test.pdf', b'PDF content', content_type='application/pdf'),
            description='Recibo de alquiler',
        )
        text = str(receipt)
        self.assertIn('Comprobante', text)
        self.assertIn('Alquiler', text)


# ─── Formularios ──────────────────────────────────────────────────────────────

class ExpenseFormTests(FinanceTestBase):

    def _valid_data(self):
        return {
            'category': 'rent',
            'description': 'Alquiler febrero',
            'amount_bs': '3600.00',
            'date': str(date.today()),
            'receipt_number': 'REC-001',
            'notes': '',
        }

    def test_expense_form_valid_data(self):
        form = ExpenseForm(data=self._valid_data(), user=self.admin)
        self.assertTrue(form.is_valid(), form.errors)

    def test_expense_form_amount_zero_invalid(self):
        data = self._valid_data()
        data['amount_bs'] = '0'
        form = ExpenseForm(data=data, user=self.admin)
        self.assertFalse(form.is_valid())
        self.assertIn('amount_bs', form.errors)

    def test_expense_form_negative_amount_invalid(self):
        data = self._valid_data()
        data['amount_bs'] = '-500.00'
        form = ExpenseForm(data=data, user=self.admin)
        self.assertFalse(form.is_valid())
        self.assertIn('amount_bs', form.errors)

    def test_expense_form_missing_description_invalid(self):
        data = self._valid_data()
        data['description'] = ''
        form = ExpenseForm(data=data, user=self.admin)
        self.assertFalse(form.is_valid())

    def test_expense_form_save_sets_created_by(self):
        form = ExpenseForm(data=self._valid_data(), user=self.admin)
        self.assertTrue(form.is_valid())
        expense = form.save()
        self.assertEqual(expense.created_by, self.admin)

    def test_expense_form_save_calculates_amount_usd_from_rate(self):
        form = ExpenseForm(data=self._valid_data(), user=self.admin)
        self.assertTrue(form.is_valid())
        expense = form.save()
        # 3600 / 36.00 = 100.00
        self.assertAlmostEqual(float(expense.amount_usd), 100.00, places=1)

    def test_expense_form_save_stores_exchange_rate_used(self):
        form = ExpenseForm(data=self._valid_data(), user=self.admin)
        self.assertTrue(form.is_valid())
        expense = form.save()
        self.assertEqual(expense.exchange_rate_used, Decimal('36.00'))

    def test_expense_form_saves_with_fallback_rate_when_no_rate(self):
        ExchangeRate.objects.all().delete()
        form = ExpenseForm(data=self._valid_data(), user=self.admin)
        self.assertTrue(form.is_valid())
        expense = form.save()
        # Fallback 36.00: 3600 / 36.00 = 100.00
        self.assertIsNotNone(expense.amount_usd)
        self.assertGreater(expense.amount_usd, 0)

    def test_expense_form_default_date_is_today(self):
        form = ExpenseForm(user=self.admin)
        self.assertEqual(form.fields['date'].initial, date.today())


class DailyCloseFormTests(FinanceTestBase):

    def test_daily_close_form_valid(self):
        form = DailyCloseForm(
            data={'date': str(date.today() + timedelta(days=1)), 'notes': 'Cierre normal'},
            user=self.admin
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_daily_close_form_missing_date_invalid(self):
        form = DailyCloseForm(data={'notes': 'Sin fecha'}, user=self.admin)
        self.assertFalse(form.is_valid())

    def test_daily_close_form_default_date_is_today(self):
        form = DailyCloseForm(user=self.admin)
        self.assertEqual(form.fields['date'].initial, date.today())


class ReportFilterFormTests(FinanceTestBase):

    def test_report_filter_valid_preset_period(self):
        form = ReportFilterForm(data={'period': 'this_month'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_report_filter_custom_period_requires_start_date(self):
        form = ReportFilterForm(data={'period': 'custom', 'end_date': str(date.today())})
        self.assertFalse(form.is_valid())

    def test_report_filter_custom_period_requires_end_date(self):
        form = ReportFilterForm(data={'period': 'custom', 'start_date': str(date.today())})
        self.assertFalse(form.is_valid())

    def test_report_filter_custom_period_start_after_end_invalid(self):
        form = ReportFilterForm(data={
            'period': 'custom',
            'start_date': str(date.today()),
            'end_date': str(date.today() - timedelta(days=1)),
        })
        self.assertFalse(form.is_valid())

    def test_report_filter_custom_period_valid(self):
        form = ReportFilterForm(data={
            'period': 'custom',
            'start_date': str(date.today() - timedelta(days=30)),
            'end_date': str(date.today()),
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_all_period_choices_are_valid(self):
        for period_key, _ in ReportFilterForm.PERIOD_CHOICES:
            if period_key != 'custom':
                form = ReportFilterForm(data={'period': period_key})
                self.assertTrue(form.is_valid(), f"Period '{period_key}' failed: {form.errors}")


# ─── Vistas: Acceso ───────────────────────────────────────────────────────────

class FinanceViewAccessTests(FinanceTestBase):

    def test_expense_list_requires_login(self):
        resp = self.client.get(reverse('finances:expense_list'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

    def test_expense_list_accessible_by_admin(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:expense_list'))
        self.assertEqual(resp.status_code, 200)

    def test_expense_list_accessible_by_employee(self):
        self.client.login(username='emp_fin', password='emp123')
        resp = self.client.get(reverse('finances:expense_list'))
        self.assertEqual(resp.status_code, 200)

    def test_expense_delete_requires_admin(self):
        self.client.login(username='emp_fin', password='emp123')
        resp = self.client.post(
            reverse('finances:expense_delete', args=[self.expense.pk])
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Expense.objects.filter(pk=self.expense.pk).exists())

    def test_expense_delete_by_admin_succeeds(self):
        self.client.login(username='admin_fin', password='admin123')
        self.client.post(reverse('finances:expense_delete', args=[self.expense.pk]))
        self.assertFalse(Expense.objects.filter(pk=self.expense.pk).exists())

    def test_daily_close_list_requires_login(self):
        resp = self.client.get(reverse('finances:daily_close_list'))
        self.assertEqual(resp.status_code, 302)

    def test_daily_close_list_accessible_when_logged_in(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:daily_close_list'))
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_cannot_access_finance_views(self):
        urls = [
            reverse('finances:expense_list'),
            reverse('finances:expense_create'),
            reverse('finances:daily_close_list'),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f"{url} no redirige anónimos")


# ─── Vistas: CRUD de Gastos ───────────────────────────────────────────────────

class ExpenseCRUDTests(FinanceTestBase):

    def test_expense_create_get_renders_form(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:expense_create'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.context)

    def test_expense_create_post_valid(self):
        self.client.login(username='admin_fin', password='admin123')
        count_before = Expense.objects.count()
        resp = self.client.post(reverse('finances:expense_create'), {
            'category': 'utilities',
            'description': 'Servicio de luz',
            'amount_bs': '720.00',
            'date': str(date.today()),
            'receipt_number': '',
            'notes': '',
        })
        self.assertGreater(Expense.objects.count(), count_before)

    def test_expense_create_post_zero_amount_fails(self):
        self.client.login(username='admin_fin', password='admin123')
        count_before = Expense.objects.count()
        self.client.post(reverse('finances:expense_create'), {
            'category': 'other',
            'description': 'Gasto inválido',
            'amount_bs': '0',
            'date': str(date.today()),
        })
        self.assertEqual(Expense.objects.count(), count_before)

    def test_expense_detail_shows_data(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:expense_detail', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Alquiler')

    def test_expense_update_get_renders_form_with_data(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:expense_update', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.context)


# ─── Vistas: Cierre Diario ────────────────────────────────────────────────────

class DailyCloseViewTests(FinanceTestBase):

    def test_daily_close_detail_shows_data(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:daily_close_detail', args=[self.daily_close.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('daily_close', resp.context)

    def test_daily_close_create_get_renders_form(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:daily_close_create'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.context)

    def test_daily_close_duplicate_date_rejected(self):
        """No se puede crear dos cierres para la misma fecha"""
        self.client.login(username='admin_fin', password='admin123')
        count_before = DailyClose.objects.count()
        self.client.post(reverse('finances:daily_close_create'), {
            'date': str(self.daily_close.date),  # fecha ya usada
            'notes': 'Duplicado',
        })
        self.assertEqual(DailyClose.objects.count(), count_before)

    def test_daily_close_list_shows_closes(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:daily_close_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('page_obj', resp.context)


# ─── Vistas: Reportes ─────────────────────────────────────────────────────────

class ReportViewTests(FinanceTestBase):

    def test_sales_report_requires_login(self):
        resp = self.client.get(reverse('finances:sales_report'))
        self.assertEqual(resp.status_code, 302)

    def test_sales_report_accessible_when_logged_in(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:sales_report'))
        self.assertEqual(resp.status_code, 200)

    def test_purchases_report_accessible(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:purchases_report'))
        self.assertEqual(resp.status_code, 200)

    def test_profits_report_accessible(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:profits_report'))
        self.assertEqual(resp.status_code, 200)

    def test_product_profitability_report_accessible(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:product_profitability_report'))
        self.assertEqual(resp.status_code, 200)

    def test_reports_with_custom_period_filter(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:sales_report'), {
            'period': 'custom',
            'start_date': str(date.today() - timedelta(days=30)),
            'end_date': str(date.today()),
        })
        self.assertEqual(resp.status_code, 200)

    def test_reports_with_today_period(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:sales_report'), {'period': 'today'})
        self.assertEqual(resp.status_code, 200)

    def test_reports_with_this_month_period(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:sales_report'), {'period': 'this_month'})
        self.assertEqual(resp.status_code, 200)


# ─── Vistas: Dashboard de Finanzas ───────────────────────────────────────────

class FinanceDashboardTests(FinanceTestBase):

    def test_finance_dashboard_requires_login(self):
        resp = self.client.get(reverse('finances:dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_finance_dashboard_accessible_by_admin(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_finance_dashboard_without_exchange_rate_does_not_crash(self):
        ExchangeRate.objects.all().delete()
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:dashboard'))
        self.assertNotEqual(resp.status_code, 500)

    def test_finance_dashboard_without_any_data_does_not_crash(self):
        """Dashboard con BD vacía no debe fallar"""
        Expense.objects.all().delete()
        DailyClose.objects.all().delete()
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:dashboard'))
        self.assertNotEqual(resp.status_code, 500)


# ─── Edge Cases ───────────────────────────────────────────────────────────────

class FinanceEdgeCaseTests(FinanceTestBase):

    def test_expense_list_filter_by_category(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:expense_list'), {'category': 'rent'})
        self.assertEqual(resp.status_code, 200)

    def test_expense_list_filter_by_date_range(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:expense_list'), {
            'date_from': str(date.today() - timedelta(days=7)),
            'date_to': str(date.today()),
        })
        self.assertEqual(resp.status_code, 200)

    def test_expense_amount_usd_calculated_correctly_for_each_category(self):
        for cat_key, _ in Expense.EXPENSE_CATEGORIES:
            expense = Expense.objects.create(
                category=cat_key,
                description=f'Gasto {cat_key}',
                amount_bs=Decimal('360.00'),
                amount_usd=Decimal('10.00'),
                exchange_rate_used=Decimal('36.00'),
                date=date.today(),
                created_by=self.admin,
            )
            self.assertIsNotNone(expense.pk)
            self.assertEqual(expense.category, cat_key)

    def test_nonexistent_expense_returns_404(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:expense_detail', args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_daily_close_returns_404(self):
        self.client.login(username='admin_fin', password='admin123')
        resp = self.client.get(reverse('finances:daily_close_detail', args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_expense_form_with_unicode_characters_in_description(self):
        """Descripción con caracteres especiales venezolanos"""
        form = ExpenseForm(data={
            'category': 'other',
            'description': 'Pago de señor Martínez ñoño',
            'amount_bs': '500.00',
            'date': str(date.today()),
        }, user=self.admin)
        self.assertTrue(form.is_valid(), form.errors)
