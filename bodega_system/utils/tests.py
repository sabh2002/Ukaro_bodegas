# utils/tests.py - Tests for utility models and functions

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from utils.models import ExchangeRate
from factories import AdminUserFactory, ExchangeRateFactory

pytestmark = pytest.mark.django_db


class TestExchangeRate:
    """Tests for ExchangeRate model"""

    @pytest.mark.critical
    def test_get_latest_rate_returns_most_recent(self, admin_user):
        """Should return the most recent exchange rate by date"""
        # Create rates on different dates
        old_rate = ExchangeRate.objects.create(
            date=date.today() - timedelta(days=2),
            bs_to_usd=Decimal('35.00'),
            updated_by=admin_user
        )
        older_rate = ExchangeRate.objects.create(
            date=date.today() - timedelta(days=3),
            bs_to_usd=Decimal('34.00'),
            updated_by=admin_user
        )
        current_rate = ExchangeRate.objects.create(
            date=date.today(),
            bs_to_usd=Decimal('36.50'),
            updated_by=admin_user
        )

        latest = ExchangeRate.get_latest_rate()

        assert latest.id == current_rate.id
        assert latest.bs_to_usd == Decimal('36.50')

    @pytest.mark.critical
    def test_get_latest_rate_returns_none_when_no_rates(self):
        """Should return None if no exchange rates exist (NOT a fallback)"""
        # Ensure no rates exist
        ExchangeRate.objects.all().delete()

        latest = ExchangeRate.get_latest_rate()

        assert latest is None

    def test_multiple_rates_same_day_returns_latest_created(self, admin_user):
        """If multiple rates on same day, return the most recently created"""
        today = date.today()

        # Create multiple rates on same day
        first = ExchangeRate.objects.create(
            date=today,
            bs_to_usd=Decimal('36.00'),
            updated_by=admin_user
        )
        second = ExchangeRate.objects.create(
            date=today,
            bs_to_usd=Decimal('36.50'),
            updated_by=admin_user
        )

        latest = ExchangeRate.get_latest_rate()

        # Should get the most recently created
        assert latest.id == second.id
        assert latest.bs_to_usd == Decimal('36.50')

    def test_exchange_rate_string_representation(self, exchange_rate):
        """Test __str__ method"""
        expected = f"{exchange_rate.date}: {exchange_rate.bs_to_usd} Bs/USD"
        assert str(exchange_rate) == expected

    def test_exchange_rate_ordering(self, admin_user):
        """Rates should be ordered by date descending (newest first)"""
        rate1 = ExchangeRate.objects.create(
            date=date.today() - timedelta(days=2),
            bs_to_usd=Decimal('35.00'),
            updated_by=admin_user
        )
        rate2 = ExchangeRate.objects.create(
            date=date.today(),
            bs_to_usd=Decimal('36.50'),
            updated_by=admin_user
        )

        rates = list(ExchangeRate.objects.all())

        assert rates[0].id == rate2.id  # Most recent first
        assert rates[1].id == rate1.id


class TestExchangeRateValidation:
    """Tests for exchange rate validation in models"""

    @pytest.mark.critical
    def test_supplier_order_item_without_exchange_rate_raises_error(self, product, supplier, admin_user):
        """CRITICAL: Must fail if no exchange rate configured (not use fallback)"""
        from suppliers.models import SupplierOrder, SupplierOrderItem

        # Ensure no exchange rates exist
        ExchangeRate.objects.all().delete()

        # Create order
        order = SupplierOrder.objects.create(
            supplier=supplier,
            created_by=admin_user
        )

        # Try to create item - should raise ValueError
        item = SupplierOrderItem(
            order=order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('10.00')
        )

        with pytest.raises(ValueError, match="No hay tasa de cambio configurada"):
            item.save()

    @pytest.mark.critical
    def test_supplier_order_item_with_exchange_rate_succeeds(
        self, product, supplier, admin_user, exchange_rate
    ):
        """Should successfully create item when exchange rate exists"""
        from suppliers.models import SupplierOrder, SupplierOrderItem

        order = SupplierOrder.objects.create(
            supplier=supplier,
            created_by=admin_user
        )

        item = SupplierOrderItem.objects.create(
            order=order,
            product=product,
            quantity=Decimal('10.00'),
            price_usd=Decimal('10.00')
        )

        # Should calculate price_bs automatically
        expected_price_bs = Decimal('10.00') * exchange_rate.bs_to_usd
        assert item.price_bs == expected_price_bs

    def test_supplier_order_item_calculates_subtotals(self, product, supplier, admin_user, exchange_rate):
        """Test subtotal calculations"""
        from suppliers.models import SupplierOrder, SupplierOrderItem

        order = SupplierOrder.objects.create(
            supplier=supplier,
            created_by=admin_user
        )

        item = SupplierOrderItem.objects.create(
            order=order,
            product=product,
            quantity=Decimal('5.00'),
            price_usd=Decimal('10.00')
        )

        assert item.subtotal_usd == Decimal('50.00')
        expected_subtotal_bs = Decimal('5.00') * item.price_bs
        assert item.subtotal_bs == expected_subtotal_bs


class TestBackupModel:
    """Tests for Backup model"""

    def test_backup_creation(self, admin_user):
        """Test creating a backup record"""
        from utils.models import Backup

        backup = Backup.objects.create(
            file_path='/backups/test_backup.sql.gz',
            file_size=1024,  # 1KB
            created_by=admin_user,
            notes='Test backup'
        )

        assert backup.file_path == '/backups/test_backup.sql.gz'
        assert backup.file_size == 1024
        assert backup.created_by == admin_user

    def test_backup_string_representation(self, admin_user):
        """Test __str__ method"""
        from utils.models import Backup

        backup = Backup.objects.create(
            file_path='/backups/test.sql.gz',
            file_size=1024,
            created_by=admin_user
        )

        assert str(backup).startswith('Respaldo del ')

    def test_backup_ordering(self, admin_user):
        """Backups should be ordered by date descending"""
        from utils.models import Backup
        from django.utils import timezone
        from datetime import timedelta

        # Create backups with different dates
        old_time = timezone.now() - timedelta(days=1)
        backup1 = Backup.objects.create(
            file_path='/backups/old.sql.gz',
            file_size=1024,
            created_by=admin_user
        )
        backup1.date = old_time
        backup1.save()

        backup2 = Backup.objects.create(
            file_path='/backups/new.sql.gz',
            file_size=2048,
            created_by=admin_user
        )

        backups = list(Backup.objects.all())

        assert backups[0].id == backup2.id  # Most recent first
        assert backups[1].id == backup1.id
