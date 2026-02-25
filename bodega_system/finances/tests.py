# finances/tests.py - Tests para modelos de finanzas

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile

from finances.models import Expense, ExpenseReceipt, DailyClose
from factories import (
    ExpenseFactory, ExpenseReceiptFactory, DailyCloseFactory,
    AdminUserFactory, ExchangeRateFactory
)

pytestmark = pytest.mark.django_db


# ============================================================================
# TESTS DE MODELO EXPENSE
# ============================================================================

class TestExpenseCreacion:
    """Tests para creación del modelo Expense"""

    def test_crear_gasto_con_campos_requeridos(self, admin_user, exchange_rate):
        """Crear gasto con campos básicos"""
        expense = Expense.objects.create(
            category='salaries',
            description='Pago de nómina',
            amount_bs=Decimal('3650.00'),
            amount_usd=Decimal('100.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        assert expense.category == 'salaries'
        assert expense.description == 'Pago de nómina'
        assert expense.amount_bs == Decimal('3650.00')
        assert expense.amount_usd == Decimal('100.00')
        assert expense.exchange_rate_used == exchange_rate.bs_to_usd

    def test_gasto_string_representation(self, admin_user, exchange_rate):
        """Test del método __str__"""
        expense = Expense.objects.create(
            category='rent',
            description='Alquiler local',
            amount_bs=Decimal('7300.00'),
            amount_usd=Decimal('200.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        str_repr = str(expense)
        assert 'Alquiler' in str_repr  # get_category_display()
        assert 'Alquiler local' in str_repr
        assert '7300' in str_repr or '7300.00' in str_repr

    def test_gastos_ordenados_por_fecha_descendente(self, admin_user, exchange_rate):
        """Los gastos deben ordenarse por fecha descendente (más reciente primero)"""
        expense1 = Expense.objects.create(
            category='utilities',
            description='Gasto antiguo',
            amount_bs=Decimal('1000.00'),
            amount_usd=Decimal('27.40'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today() - timedelta(days=5),
            created_by=admin_user
        )

        expense2 = Expense.objects.create(
            category='utilities',
            description='Gasto reciente',
            amount_bs=Decimal('1000.00'),
            amount_usd=Decimal('27.40'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        expenses = list(Expense.objects.all())

        # El más reciente primero
        assert expenses[0].id == expense2.id
        assert expenses[1].id == expense1.id


class TestExpenseCategorias:
    """Tests para categorías de gastos"""

    def test_categorias_disponibles(self, admin_user, exchange_rate):
        """Test de todas las categorías de gastos"""
        categorias = [
            'salaries', 'repairs', 'improvements', 'supplies',
            'rent', 'utilities', 'maintenance', 'taxes', 'other'
        ]

        for categoria in categorias:
            expense = Expense.objects.create(
                category=categoria,
                description=f'Gasto de {categoria}',
                amount_bs=Decimal('1000.00'),
                amount_usd=Decimal('27.40'),
                exchange_rate_used=exchange_rate.bs_to_usd,
                date=date.today(),
                created_by=admin_user
            )
            assert expense.category == categoria

    def test_get_category_display(self, admin_user, exchange_rate):
        """Test de nombres legibles de categorías"""
        expense = Expense.objects.create(
            category='salaries',
            description='Pago',
            amount_bs=Decimal('1000.00'),
            amount_usd=Decimal('27.40'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        assert expense.get_category_display() == 'Sueldos de Empleados'


class TestExpenseExchangeRate:
    """Tests para manejo de tasa de cambio en gastos"""

    @pytest.mark.critical
    def test_gasto_captura_tasa_de_cambio(self, admin_user, exchange_rate):
        """Gasto debe capturar y almacenar la tasa de cambio usada"""
        expense = Expense.objects.create(
            category='utilities',
            description='Luz',
            amount_bs=Decimal('1825.00'),
            amount_usd=Decimal('50.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        assert expense.exchange_rate_used == exchange_rate.bs_to_usd
        assert expense.amount_bs == expense.amount_usd * exchange_rate.bs_to_usd

    @pytest.mark.critical
    def test_gasto_montos_coinciden_con_tasa(self, admin_user, exchange_rate):
        """Monto Bs debe igualar Monto USD × Tasa de Cambio"""
        amount_usd = Decimal('75.00')
        expected_bs = amount_usd * exchange_rate.bs_to_usd

        expense = Expense.objects.create(
            category='repairs',
            description='Reparación',
            amount_bs=expected_bs,
            amount_usd=amount_usd,
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        assert expense.amount_bs == expected_bs

    @pytest.mark.critical
    def test_gasto_mantiene_tasa_historica(self, admin_user, exchange_rate):
        """Gasto debe mantener tasa histórica aunque cambie la tasa actual"""
        from utils.models import ExchangeRate

        # Crear gasto con tasa actual
        expense = Expense.objects.create(
            category='supplies',
            description='Materiales',
            amount_bs=Decimal('3650.00'),
            amount_usd=Decimal('100.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,  # 36.50
            date=date.today(),
            created_by=admin_user
        )

        tasa_original = expense.exchange_rate_used

        # Cambiar tasa de cambio del sistema
        ExchangeRate.objects.create(
            date=date.today() + timedelta(days=1),
            bs_to_usd=Decimal('40.00'),  # Nueva tasa
            updated_by=admin_user
        )

        # Gasto debe mantener tasa original
        expense.refresh_from_db()
        assert expense.exchange_rate_used == tasa_original
        assert expense.exchange_rate_used == Decimal('36.50')


class TestExpenseCamposOpcionales:
    """Tests para campos opcionales de gastos"""

    def test_gasto_con_numero_de_recibo(self, admin_user, exchange_rate):
        """Gasto puede tener número de recibo"""
        expense = Expense.objects.create(
            category='utilities',
            description='Internet',
            amount_bs=Decimal('1000.00'),
            amount_usd=Decimal('27.40'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            receipt_number='REC-2024-001',
            created_by=admin_user
        )

        assert expense.receipt_number == 'REC-2024-001'

    def test_gasto_sin_numero_de_recibo(self, admin_user, exchange_rate):
        """Número de recibo es opcional"""
        expense = Expense.objects.create(
            category='other',
            description='Varios',
            amount_bs=Decimal('500.00'),
            amount_usd=Decimal('13.70'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        assert expense.receipt_number == ''

    def test_gasto_con_notas(self, admin_user, exchange_rate):
        """Gasto puede tener notas adicionales"""
        expense = Expense.objects.create(
            category='maintenance',
            description='Mantenimiento',
            amount_bs=Decimal('2000.00'),
            amount_usd=Decimal('54.79'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            notes='Mantenimiento preventivo de equipos',
            created_by=admin_user
        )

        assert expense.notes == 'Mantenimiento preventivo de equipos'


class TestExpenseRelaciones:
    """Tests para relaciones del modelo Expense"""

    def test_gasto_relacionado_con_usuario(self, admin_user, exchange_rate):
        """Gasto debe estar relacionado con usuario que lo creó"""
        expense = Expense.objects.create(
            category='taxes',
            description='Impuestos',
            amount_bs=Decimal('5000.00'),
            amount_usd=Decimal('137.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        assert expense.created_by == admin_user
        assert expense in admin_user.expenses.all()

    def test_gasto_con_multiples_comprobantes(self, admin_user, exchange_rate):
        """Un gasto puede tener múltiples comprobantes"""
        expense = Expense.objects.create(
            category='repairs',
            description='Reparaciones varias',
            amount_bs=Decimal('3000.00'),
            amount_usd=Decimal('82.19'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        # Crear comprobantes
        receipt1 = ExpenseReceipt.objects.create(
            expense=expense,
            file=SimpleUploadedFile('recibo1.pdf', b'contenido'),
            description='Factura 1'
        )

        receipt2 = ExpenseReceipt.objects.create(
            expense=expense,
            file=SimpleUploadedFile('recibo2.pdf', b'contenido'),
            description='Factura 2'
        )

        assert expense.receipts.count() == 2
        assert receipt1 in expense.receipts.all()
        assert receipt2 in expense.receipts.all()


# ============================================================================
# TESTS DE MODELO EXPENSE RECEIPT
# ============================================================================

class TestExpenseReceiptCreacion:
    """Tests para creación del modelo ExpenseReceipt"""

    def test_crear_comprobante(self, admin_user, exchange_rate):
        """Crear comprobante de gasto"""
        expense = Expense.objects.create(
            category='utilities',
            description='Agua',
            amount_bs=Decimal('500.00'),
            amount_usd=Decimal('13.70'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        receipt = ExpenseReceipt.objects.create(
            expense=expense,
            file=SimpleUploadedFile('factura.pdf', b'contenido del archivo'),
            description='Factura de agua'
        )

        assert receipt.expense == expense
        assert receipt.description == 'Factura de agua'
        assert receipt.file.name.endswith('.pdf')

    def test_comprobante_string_representation(self, admin_user, exchange_rate):
        """Test del método __str__"""
        expense = Expense.objects.create(
            category='rent',
            description='Alquiler',
            amount_bs=Decimal('7300.00'),
            amount_usd=Decimal('200.00'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        receipt = ExpenseReceipt.objects.create(
            expense=expense,
            file=SimpleUploadedFile('contrato.pdf', b'contenido')
        )

        str_repr = str(receipt)
        assert 'Comprobante' in str_repr
        assert 'Alquiler' in str_repr

    def test_comprobantes_ordenados_por_fecha_descendente(self, admin_user, exchange_rate):
        """Comprobantes deben ordenarse por uploaded_at descendente"""
        expense = Expense.objects.create(
            category='supplies',
            description='Materiales',
            amount_bs=Decimal('1000.00'),
            amount_usd=Decimal('27.40'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        receipt1 = ExpenseReceipt.objects.create(
            expense=expense,
            file=SimpleUploadedFile('file1.pdf', b'contenido')
        )

        receipt2 = ExpenseReceipt.objects.create(
            expense=expense,
            file=SimpleUploadedFile('file2.pdf', b'contenido')
        )

        receipts = list(ExpenseReceipt.objects.all())

        # Más reciente primero
        assert receipts[0].id == receipt2.id
        assert receipts[1].id == receipt1.id

    def test_comprobante_sin_descripcion(self, admin_user, exchange_rate):
        """Descripción del comprobante es opcional"""
        expense = Expense.objects.create(
            category='other',
            description='Otros',
            amount_bs=Decimal('500.00'),
            amount_usd=Decimal('13.70'),
            exchange_rate_used=exchange_rate.bs_to_usd,
            date=date.today(),
            created_by=admin_user
        )

        receipt = ExpenseReceipt.objects.create(
            expense=expense,
            file=SimpleUploadedFile('archivo.pdf', b'contenido')
        )

        assert receipt.description == ''


# ============================================================================
# TESTS DE MODELO DAILY CLOSE
# ============================================================================

class TestDailyCloseCreacion:
    """Tests para creación del modelo DailyClose"""

    def test_crear_cierre_diario(self, admin_user):
        """Crear cierre diario con campos básicos"""
        close = DailyClose.objects.create(
            date=date.today(),
            sales_count=15,
            sales_total_bs=Decimal('50000.00'),
            expenses_total_bs=Decimal('10000.00'),
            profit_bs=Decimal('40000.00'),
            closed_by=admin_user
        )

        assert close.date == date.today()
        assert close.sales_count == 15
        assert close.sales_total_bs == Decimal('50000.00')
        assert close.expenses_total_bs == Decimal('10000.00')
        assert close.profit_bs == Decimal('40000.00')

    def test_cierre_string_representation(self, admin_user):
        """Test del método __str__"""
        close = DailyClose.objects.create(
            date=date(2024, 3, 15),
            sales_count=10,
            sales_total_bs=Decimal('30000.00'),
            expenses_total_bs=Decimal('5000.00'),
            profit_bs=Decimal('25000.00'),
            closed_by=admin_user
        )

        str_repr = str(close)
        assert 'Cierre' in str_repr
        assert '15/03/2024' in str_repr

    def test_cierres_ordenados_por_fecha_descendente(self, admin_user):
        """Cierres deben ordenarse por fecha descendente"""
        close1 = DailyClose.objects.create(
            date=date.today() - timedelta(days=5),
            sales_count=10,
            sales_total_bs=Decimal('20000.00'),
            expenses_total_bs=Decimal('5000.00'),
            profit_bs=Decimal('15000.00'),
            closed_by=admin_user
        )

        close2 = DailyClose.objects.create(
            date=date.today(),
            sales_count=15,
            sales_total_bs=Decimal('30000.00'),
            expenses_total_bs=Decimal('7000.00'),
            profit_bs=Decimal('23000.00'),
            closed_by=admin_user
        )

        closes = list(DailyClose.objects.all())

        # Más reciente primero
        assert closes[0].id == close2.id
        assert closes[1].id == close1.id


class TestDailyCloseValidacion:
    """Tests para validación del modelo DailyClose"""

    @pytest.mark.critical
    def test_fecha_debe_ser_unique(self, admin_user):
        """No se puede crear dos cierres para la misma fecha"""
        DailyClose.objects.create(
            date=date.today(),
            sales_count=10,
            sales_total_bs=Decimal('20000.00'),
            expenses_total_bs=Decimal('5000.00'),
            profit_bs=Decimal('15000.00'),
            closed_by=admin_user
        )

        # Intentar crear otro cierre para la misma fecha debe fallar
        with pytest.raises(IntegrityError):
            DailyClose.objects.create(
                date=date.today(),
                sales_count=5,
                sales_total_bs=Decimal('10000.00'),
                expenses_total_bs=Decimal('2000.00'),
                profit_bs=Decimal('8000.00'),
                closed_by=admin_user
            )

    def test_puede_haber_cierres_en_fechas_diferentes(self, admin_user):
        """Puede haber múltiples cierres en fechas diferentes"""
        close1 = DailyClose.objects.create(
            date=date.today() - timedelta(days=1),
            sales_count=10,
            sales_total_bs=Decimal('20000.00'),
            expenses_total_bs=Decimal('5000.00'),
            profit_bs=Decimal('15000.00'),
            closed_by=admin_user
        )

        close2 = DailyClose.objects.create(
            date=date.today(),
            sales_count=15,
            sales_total_bs=Decimal('30000.00'),
            expenses_total_bs=Decimal('7000.00'),
            profit_bs=Decimal('23000.00'),
            closed_by=admin_user
        )

        assert DailyClose.objects.count() == 2


class TestDailyCloseCalculos:
    """Tests para cálculos del cierre diario"""

    @pytest.mark.critical
    def test_ganancia_es_ventas_menos_gastos(self, admin_user):
        """Ganancia = Ventas - Gastos"""
        sales_total = Decimal('50000.00')
        expenses_total = Decimal('12000.00')
        expected_profit = sales_total - expenses_total

        close = DailyClose.objects.create(
            date=date.today(),
            sales_count=20,
            sales_total_bs=sales_total,
            expenses_total_bs=expenses_total,
            profit_bs=expected_profit,
            closed_by=admin_user
        )

        assert close.profit_bs == Decimal('38000.00')

    def test_cierre_con_cero_ventas(self, admin_user):
        """Cierre puede tener cero ventas (día sin actividad)"""
        close = DailyClose.objects.create(
            date=date.today(),
            sales_count=0,
            sales_total_bs=Decimal('0.00'),
            expenses_total_bs=Decimal('5000.00'),
            profit_bs=Decimal('-5000.00'),  # Pérdida
            closed_by=admin_user
        )

        assert close.sales_count == 0
        assert close.profit_bs == Decimal('-5000.00')

    def test_cierre_con_cero_gastos(self, admin_user):
        """Cierre puede tener cero gastos"""
        close = DailyClose.objects.create(
            date=date.today(),
            sales_count=10,
            sales_total_bs=Decimal('20000.00'),
            expenses_total_bs=Decimal('0.00'),
            profit_bs=Decimal('20000.00'),
            closed_by=admin_user
        )

        assert close.expenses_total_bs == Decimal('0.00')
        assert close.profit_bs == close.sales_total_bs


class TestDailyCloseRelaciones:
    """Tests para relaciones del modelo DailyClose"""

    def test_cierre_relacionado_con_usuario(self, admin_user):
        """Cierre debe estar relacionado con usuario que lo cerró"""
        close = DailyClose.objects.create(
            date=date.today(),
            sales_count=10,
            sales_total_bs=Decimal('20000.00'),
            expenses_total_bs=Decimal('5000.00'),
            profit_bs=Decimal('15000.00'),
            closed_by=admin_user
        )

        assert close.closed_by == admin_user
        assert close in admin_user.daily_closes.all()

    def test_cierre_con_notas(self, admin_user):
        """Cierre puede tener notas opcionales"""
        close = DailyClose.objects.create(
            date=date.today(),
            sales_count=10,
            sales_total_bs=Decimal('20000.00'),
            expenses_total_bs=Decimal('5000.00'),
            profit_bs=Decimal('15000.00'),
            notes='Día de buenas ventas, sin incidentes',
            closed_by=admin_user
        )

        assert close.notes == 'Día de buenas ventas, sin incidentes'

    def test_cierre_sin_notas(self, admin_user):
        """Notas del cierre son opcionales"""
        close = DailyClose.objects.create(
            date=date.today(),
            sales_count=5,
            sales_total_bs=Decimal('10000.00'),
            expenses_total_bs=Decimal('2000.00'),
            profit_bs=Decimal('8000.00'),
            closed_by=admin_user
        )

        assert close.notes == ''
