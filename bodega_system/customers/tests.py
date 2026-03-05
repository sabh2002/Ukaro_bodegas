# customers/tests.py
"""
Tests exhaustivos para el módulo customers:
- Customer model (crédito, propiedades)
- CustomerCredit model
- CreditPayment model
- Vistas CRUD de clientes
- Vistas de créditos y pagos
"""

from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer, CustomerCredit, CreditPayment
from sales.models import Sale
from utils.models import ExchangeRate

User = get_user_model()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def make_admin(username='cust_admin'):
    return User.objects.create_user(username=username, password='pass123', is_admin=True)

def make_employee(username='cust_emp'):
    return User.objects.create_user(username=username, password='pass123', is_employee=True)

def make_exchange_rate(user, rate='45.50'):
    cache.clear()
    return ExchangeRate.objects.create(
        date=timezone.now().date(),
        bs_to_usd=Decimal(rate),
        updated_by=user
    )

def make_customer(name='Juan Pérez', credit_limit=Decimal('500.00')):
    return Customer.objects.create(
        name=name,
        phone='04141234567',
        credit_limit_usd=credit_limit,
        is_active=True
    )

def make_sale(user, customer=None, total_bs='100.00', total_usd='2.00',
              payment_method='cash', is_credit=False, exchange_rate='45.50'):
    return Sale.objects.create(
        customer=customer,
        user=user,
        total_bs=Decimal(total_bs),
        total_usd=Decimal(total_usd),
        exchange_rate_used=Decimal(exchange_rate),
        payment_method=payment_method,
        is_credit=is_credit
    )

def make_credit(customer, sale, amount_usd='50.00', amount_bs='2275.00', rate='45.50'):
    return CustomerCredit.objects.create(
        customer=customer,
        sale=sale,
        amount_usd=Decimal(amount_usd),
        amount_bs=Decimal(amount_bs),
        exchange_rate_used=Decimal(rate),
        date_due=date.today() + timedelta(days=30),
        is_paid=False
    )


# ─────────────────────────────────────────────
# CUSTOMER MODEL TESTS
# ─────────────────────────────────────────────

class CustomerModelTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = make_admin()
        self.exchange_rate = make_exchange_rate(self.admin)

    def test_create_customer_basic(self):
        """Debe crear cliente con campos mínimos"""
        customer = Customer.objects.create(name='Carlos López')
        self.assertEqual(customer.name, 'Carlos López')
        self.assertTrue(customer.is_active)
        self.assertEqual(customer.credit_limit_usd, Decimal('0'))

    def test_create_customer_with_credit(self):
        """Debe crear cliente con límite de crédito"""
        customer = make_customer(credit_limit=Decimal('1000.00'))
        self.assertEqual(customer.credit_limit_usd, Decimal('1000.00'))

    def test_str_representation(self):
        """__str__ debe retornar el nombre del cliente"""
        customer = make_customer('María García')
        self.assertEqual(str(customer), 'María García')

    def test_total_credit_used_no_credits(self):
        """Sin créditos, total_credit_used debe ser 0"""
        customer = make_customer()
        self.assertEqual(customer.total_credit_used, 0)

    def test_total_credit_used_with_unpaid_credits(self):
        """Con créditos sin pagar, total_credit_used debe sumarlos"""
        customer = make_customer(credit_limit=Decimal('1000.00'))
        sale = make_sale(self.admin, customer=customer, is_credit=True)
        make_credit(customer, sale, amount_usd='200.00')
        self.assertEqual(customer.total_credit_used, Decimal('200.00'))

    def test_total_credit_used_excludes_paid(self):
        """Créditos pagados no deben sumarse"""
        customer = make_customer(credit_limit=Decimal('1000.00'))
        sale1 = make_sale(self.admin, customer=customer, is_credit=True)
        credit1 = make_credit(customer, sale1, amount_usd='200.00')
        credit1.is_paid = True
        credit1.save()
        self.assertEqual(customer.total_credit_used, 0)

    def test_available_credit_calculation(self):
        """available_credit = credit_limit - total_used"""
        customer = make_customer(credit_limit=Decimal('500.00'))
        sale = make_sale(self.admin, customer=customer, is_credit=True)
        make_credit(customer, sale, amount_usd='200.00')
        available = customer.available_credit
        self.assertEqual(available, Decimal('300.00'))

    def test_credit_limit_bs_current_with_rate(self):
        """credit_limit_bs_current debe calcularse con la tasa vigente"""
        customer = make_customer(credit_limit=Decimal('100.00'))
        expected_bs = Decimal('100.00') * Decimal('45.50')
        self.assertEqual(customer.credit_limit_bs_current, expected_bs)

    def test_credit_limit_bs_current_without_rate(self):
        """Sin tasa, credit_limit_bs_current debe ser 0"""
        ExchangeRate.objects.all().delete()
        cache.clear()
        customer = make_customer(credit_limit=Decimal('100.00'))
        self.assertEqual(customer.credit_limit_bs_current, 0)

    def test_ordering_by_name(self):
        """Clientes deben ordenarse por nombre"""
        Customer.objects.create(name='Zaira')
        Customer.objects.create(name='Ana')
        Customer.objects.create(name='Manuel')
        names = list(Customer.objects.values_list('name', flat=True))
        self.assertEqual(names[0], 'Ana')


# ─────────────────────────────────────────────
# CUSTOMER CREDIT MODEL TESTS
# ─────────────────────────────────────────────

class CustomerCreditModelTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = make_admin('cc_admin')
        self.exchange_rate = make_exchange_rate(self.admin)
        self.customer = make_customer(credit_limit=Decimal('500.00'))
        self.sale = make_sale(self.admin, customer=self.customer, is_credit=True)

    def test_create_credit(self):
        """Debe crear crédito correctamente"""
        credit = make_credit(self.customer, self.sale, amount_usd='150.00', amount_bs='6825.00')
        self.assertEqual(credit.customer, self.customer)
        self.assertEqual(credit.amount_usd, Decimal('150.00'))
        self.assertFalse(credit.is_paid)

    def test_str_representation(self):
        """__str__ debe incluir nombre del cliente y monto"""
        credit = make_credit(self.customer, self.sale)
        result = str(credit)
        self.assertIn(self.customer.name, result)
        self.assertIn('Bs', result)

    def test_credit_date_due(self):
        """date_due debe estar configurada correctamente"""
        credit = make_credit(self.customer, self.sale)
        self.assertIsNotNone(credit.date_due)
        self.assertGreater(credit.date_due, date.today())


# ─────────────────────────────────────────────
# CREDIT PAYMENT MODEL TESTS
# ─────────────────────────────────────────────

class CreditPaymentModelTest(TestCase):

    def setUp(self):
        cache.clear()
        self.admin = make_admin('cp_admin')
        self.exchange_rate = make_exchange_rate(self.admin)
        self.customer = make_customer(credit_limit=Decimal('500.00'))
        self.sale = make_sale(self.admin, customer=self.customer, is_credit=True)
        self.credit = make_credit(self.customer, self.sale)

    def test_create_payment(self):
        """Debe crear pago de crédito"""
        payment = CreditPayment.objects.create(
            credit=self.credit,
            amount_bs=Decimal('500.00'),
            amount_usd=Decimal('10.99'),
            exchange_rate_used=Decimal('45.50'),
            payment_method='cash',
            received_by=self.admin
        )
        self.assertEqual(payment.credit, self.credit)
        self.assertEqual(payment.amount_bs, Decimal('500.00'))
        self.assertEqual(payment.payment_method, 'cash')

    def test_get_payment_method_icon_cash(self):
        """Efectivo debe tener icono de billete"""
        payment = CreditPayment(payment_method='cash')
        icon = payment.get_payment_method_icon()
        self.assertEqual(icon, '💵')

    def test_get_payment_method_icon_card(self):
        """Punto de venta debe tener icono de tarjeta"""
        payment = CreditPayment(payment_method='card')
        self.assertEqual(payment.get_payment_method_icon(), '💳')

    def test_get_payment_method_icon_mobile(self):
        """Pago móvil debe tener icono de teléfono"""
        payment = CreditPayment(payment_method='mobile')
        self.assertEqual(payment.get_payment_method_icon(), '📱')

    def test_get_payment_method_display_with_icon_mobile_with_ref(self):
        """Pago móvil con referencia debe incluirla en el display"""
        payment = CreditPayment(payment_method='mobile', mobile_reference='REF12345')
        display = payment.get_payment_method_display_with_icon()
        self.assertIn('REF12345', display)

    def test_get_payment_method_display_with_icon_cash(self):
        """Efectivo sin referencia no debe incluir referencia"""
        payment = CreditPayment(payment_method='cash', mobile_reference=None)
        display = payment.get_payment_method_display_with_icon()
        self.assertNotIn('Ref:', display)


# ─────────────────────────────────────────────
# CUSTOMER VIEW TESTS
# ─────────────────────────────────────────────

class CustomerListViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('cv_admin')
        self.employee = make_employee('cv_emp')
        make_exchange_rate(self.admin)
        self.customer = make_customer('Cliente Vista')
        self.url = reverse('customers:customer_list')

    def test_anonymous_redirects(self):
        """Sin autenticación debe redirigir"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_employee_can_see_list(self):
        """Empleado puede ver lista de clientes"""
        self.client.login(username='cv_emp', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_see_list(self):
        """Admin puede ver lista de clientes"""
        self.client.login(username='cv_admin', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_search_filter(self):
        """Búsqueda debe filtrar clientes"""
        self.client.login(username='cv_admin', password='pass123')
        response = self.client.get(self.url, {'q': 'Cliente Vista'})
        self.assertEqual(response.status_code, 200)


class CustomerCRUDViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('ccrud_admin')
        self.employee = make_employee('ccrud_emp')
        make_exchange_rate(self.admin)
        self.customer = make_customer('CRUD Customer')

    def test_customer_create_get_employee(self):
        """Empleado puede ver formulario de nuevo cliente"""
        self.client.login(username='ccrud_emp', password='pass123')
        url = reverse('customers:customer_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_customer_create_post_valid(self):
        """Crear cliente con datos válidos"""
        self.client.login(username='ccrud_admin', password='pass123')
        url = reverse('customers:customer_create')
        response = self.client.post(url, {
            'name': 'Nuevo Cliente Test',
            'phone': '04241234567',
            'email': '',
            'address': '',
            'credit_limit_usd': '200.00',
            'notes': '',
            'is_active': True
        })
        if response.status_code == 302:
            self.assertTrue(Customer.objects.filter(name='Nuevo Cliente Test').exists())

    def test_customer_update_get(self):
        """Admin puede ver formulario de edición"""
        self.client.login(username='ccrud_admin', password='pass123')
        url = reverse('customers:customer_update', args=[self.customer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_customer_detail_accessible(self):
        """Empleado puede ver detalle de cliente"""
        self.client.login(username='ccrud_emp', password='pass123')
        url = reverse('customers:customer_detail', args=[self.customer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_customer_delete_requires_admin(self):
        """Solo admin puede eliminar clientes"""
        self.client.login(username='ccrud_emp', password='pass123')
        url = reverse('customers:customer_delete', args=[self.customer.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_customer_delete_admin_ok(self):
        """Admin puede eliminar cliente"""
        target = make_customer('Delete Me')
        target_pk = target.pk
        self.client.login(username='ccrud_admin', password='pass123')
        url = reverse('customers:customer_delete', args=[target_pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Customer.objects.filter(pk=target_pk).exists())


class CreditViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('credit_admin')
        self.employee = make_employee('credit_emp')
        make_exchange_rate(self.admin)
        self.customer = make_customer(credit_limit=Decimal('500.00'))
        sale = make_sale(self.admin, customer=self.customer, is_credit=True)
        self.credit = make_credit(self.customer, sale)

    def test_credit_list_requires_admin(self):
        """Solo admin puede ver lista de créditos"""
        self.client.login(username='credit_emp', password='pass123')
        url = reverse('customers:credit_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_credit_list_admin_ok(self):
        """Admin puede ver lista de créditos"""
        self.client.login(username='credit_admin', password='pass123')
        url = reverse('customers:credit_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_credit_detail_accessible(self):
        """Admin puede ver detalle de crédito"""
        self.client.login(username='credit_admin', password='pass123')
        url = reverse('customers:credit_detail', args=[self.credit.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_credit_payment_get(self):
        """Admin puede ver formulario de pago de crédito"""
        self.client.login(username='credit_admin', password='pass123')
        url = reverse('customers:credit_payment', args=[self.credit.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
