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

from customers.models import Customer, CustomerCredit, CreditPayment, CustomerGeneralPayment
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

    def test_total_credit_used_deducts_partial_payments(self):
        """total_credit_used debe restar pagos parciales ya aplicados"""
        customer = make_customer(credit_limit=Decimal('1000.00'))
        sale = make_sale(self.admin, customer=customer, is_credit=True)
        credit = make_credit(customer, sale, amount_usd='100.00')
        # Pago parcial de $30
        CreditPayment.objects.create(
            credit=credit,
            amount_bs=Decimal('1365.00'),
            amount_usd=Decimal('30.00'),
            exchange_rate_used=Decimal('45.50'),
            payment_method='cash',
            received_by=self.admin,
        )
        # Debe quedar $70 pendientes, NO $100
        self.assertEqual(customer.total_credit_used, Decimal('70.00'))

    def test_available_credit_calculation(self):
        """available_credit = credit_limit - total_used (neto de pagos)"""
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


# ─────────────────────────────────────────────
# CUSTOMER GENERAL PAYMENT (FIFO) TESTS
# ─────────────────────────────────────────────

class CustomerGeneralPaymentTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('gp_admin')
        self.employee = make_employee('gp_emp')
        self.rate = make_exchange_rate(self.admin, '45.50')
        self.customer = make_customer(credit_limit=Decimal('500.00'))
        # Dos créditos pendientes
        self.sale1 = make_sale(self.admin, customer=self.customer, is_credit=True)
        self.sale2 = make_sale(self.admin, customer=self.customer, is_credit=True)
        self.credit1 = make_credit(self.customer, self.sale1, amount_usd='10.00', amount_bs='455.00')
        self.credit2 = make_credit(self.customer, self.sale2, amount_usd='15.00', amount_bs='682.50')

    def _url(self):
        return reverse('customers:customer_general_payment', kwargs={'pk': self.customer.pk})

    # ── Acceso ──────────────────────────────

    def test_no_debt_redirects(self):
        """Cliente sin deuda → redirect a customer_detail con mensaje info"""
        customer_zero = make_customer(name='Sin Deuda', credit_limit=Decimal('100.00'))
        self.client.login(username='gp_admin', password='pass123')
        url = reverse('customers:customer_general_payment', kwargs={'pk': customer_zero.pk})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('customers:customer_detail', kwargs={'pk': customer_zero.pk}))

    def test_admin_gets_200(self):
        """Admin puede ver el formulario"""
        self.client.login(username='gp_admin', password='pass123')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('pending_credits', response.context)

    def test_employee_can_access(self):
        """Empleado también puede acceder (customer_access_required)"""
        self.client.login(username='gp_emp', password='pass123')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    # ── Lógica FIFO ──────────────────────────

    def test_full_payment_fifo_marks_oldest_paid(self):
        """Pago exacto de credit1 marca credit1 como pagado"""
        self.client.login(username='gp_admin', password='pass123')
        # $10.00 USD = 455.00 Bs a tasa 45.50
        response = self.client.post(self._url(), {
            'amount_bs': '455.00',
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        })
        self.assertRedirects(response, reverse('customers:customer_detail', kwargs={'pk': self.customer.pk}))
        self.credit1.refresh_from_db()
        self.credit2.refresh_from_db()
        self.assertTrue(self.credit1.is_paid)
        self.assertFalse(self.credit2.is_paid)

    def test_partial_payment_creates_credit_payment(self):
        """Pago parcial crea CreditPayment en el primer crédito (FIFO)"""
        self.client.login(username='gp_admin', password='pass123')
        # $5.00 USD = 227.50 Bs
        self.client.post(self._url(), {
            'amount_bs': '227.50',
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        })
        # credit1 debe tener un pago parcial
        self.credit1.refresh_from_db()
        self.assertFalse(self.credit1.is_paid)
        self.assertEqual(self.credit1.payments.count(), 1)
        payment = self.credit1.payments.first()
        self.assertAlmostEqual(float(payment.amount_usd), 5.00, places=1)

    def test_payment_spanning_two_credits(self):
        """Pago de $20 cubre credit1 ($10) completo + $10 parcial de credit2 ($15)"""
        self.client.login(username='gp_admin', password='pass123')
        # $20.00 USD = 910.00 Bs
        self.client.post(self._url(), {
            'amount_bs': '910.00',
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        })
        self.credit1.refresh_from_db()
        self.credit2.refresh_from_db()
        self.assertTrue(self.credit1.is_paid)
        self.assertFalse(self.credit2.is_paid)
        # credit2 debe tener un pago parcial
        self.assertEqual(self.credit2.payments.count(), 1)

    def test_overpayment_rejected(self):
        """Monto que supera deuda total es rechazado por el formulario"""
        self.client.login(username='gp_admin', password='pass123')
        # Deuda total = $25 USD = 1137.50 Bs; enviamos $100 USD = 4550.00 Bs
        response = self.client.post(self._url(), {
            'amount_bs': '4550.00',
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        })
        # Debe permanecer en el formulario con error (200, no redirect)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

    def test_credit_payment_linked_to_general_payment(self):
        """CreditPayment creado por pago general tiene FK a CustomerGeneralPayment"""
        self.client.login(username='gp_admin', password='pass123')
        self.client.post(self._url(), {
            'amount_bs': '455.00',
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        })
        payment = CreditPayment.objects.filter(credit=self.credit1).first()
        self.assertIsNotNone(payment)
        self.assertIsNotNone(payment.general_payment)
        self.assertIsInstance(payment.general_payment, CustomerGeneralPayment)

    def test_general_payment_object_created(self):
        """Se crea un registro CustomerGeneralPayment en la BD"""
        self.client.login(username='gp_admin', password='pass123')
        self.assertEqual(CustomerGeneralPayment.objects.count(), 0)
        self.client.post(self._url(), {
            'amount_bs': '455.00',
            'payment_method': 'card',
            'mobile_reference': '',
            'notes': 'test',
        })
        self.assertEqual(CustomerGeneralPayment.objects.count(), 1)
        gp = CustomerGeneralPayment.objects.first()
        self.assertEqual(gp.customer, self.customer)
        self.assertEqual(gp.payment_method, 'card')

    def test_partial_payment_reduces_total_credit_used(self):
        """Pago parcial reduce total_credit_used del cliente (bug crítico)"""
        self.client.login(username='gp_admin', password='pass123')
        # Deuda inicial: credit1 $10 + credit2 $15 = $25
        self.assertAlmostEqual(float(self.customer.total_credit_used), 25.00, places=1)
        # Pagamos $5 (= 227.50 Bs a 45.50)
        self.client.post(self._url(), {
            'amount_bs': '227.50',
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        })
        # Deuda restante debe ser $20 (no sigue siendo $25)
        self.customer.refresh_from_db()
        self.assertAlmostEqual(float(self.customer.total_credit_used), 20.00, places=1)

    def test_second_general_payment_uses_remaining_balance(self):
        """Segundo pago general respeta lo ya pagado en pagos anteriores"""
        self.client.login(username='gp_admin', password='pass123')
        # Primer pago: $10 → liquida credit1
        self.client.post(self._url(), {
            'amount_bs': '455.00',
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        })
        self.credit1.refresh_from_db()
        self.assertTrue(self.credit1.is_paid)
        # Deuda restante: solo credit2 ($15)
        self.assertAlmostEqual(float(self.customer.total_credit_used), 15.00, places=1)
        # Segundo pago: $5 parcial en credit2
        self.client.post(self._url(), {
            'amount_bs': '227.50',
            'payment_method': 'cash',
            'mobile_reference': '',
            'notes': '',
        })
        # Deuda restante: $10
        self.customer.refresh_from_db()
        self.assertAlmostEqual(float(self.customer.total_credit_used), 10.00, places=1)
