# performance/tests.py
"""
Tests para el módulo de rendimiento por usuario.
"""

from decimal import Decimal
from datetime import date

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from sales.models import Sale
from utils.models import ExchangeRate

User = get_user_model()

URL = reverse('performance:dashboard')


class PerformanceDashboardAccessTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(
            username='perf_admin', password='pass123', is_admin=True
        )
        self.employee = User.objects.create_user(
            username='perf_emp', password='pass123', is_employee=True
        )
        ExchangeRate.objects.create(
            date=timezone.now().date(),
            bs_to_usd=Decimal('45.50'),
            updated_by=self.admin,
        )
        self.client = Client()

    def test_unauthenticated_redirects(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_employee_gets_403(self):
        self.client.login(username='perf_emp', password='pass123')
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 403)

    def test_admin_gets_200(self):
        self.client.login(username='perf_admin', password='pass123')
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)

    def test_context_has_required_keys(self):
        self.client.login(username='perf_admin', password='pass123')
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        for key in ('today_stats', 'month_stats', 'period_stats', 'form'):
            self.assertIn(key, response.context, f"Falta '{key}' en el contexto")

    def test_user_stats_no_sales(self):
        """Cuando no hay ventas, los paneles retornan listas vacías."""
        self.client.login(username='perf_admin', password='pass123')
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['today_stats']), [])

    def test_user_stats_with_sales(self):
        """Cuando hay ventas, aparecen en today_stats."""
        Sale.objects.create(
            user=self.admin,
            total_usd=Decimal('100.00'),
            total_bs=Decimal('4550.00'),
            exchange_rate_used=Decimal('45.50'),
            payment_method='cash',
        )
        self.client.login(username='perf_admin', password='pass123')
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        stats = response.context['today_stats']
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]['username'], 'perf_admin')
        self.assertEqual(stats[0]['sales_count'], 1)
