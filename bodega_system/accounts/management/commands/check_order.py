# suppliers/management/commands/check_supplier_orders.py

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from suppliers.models import SupplierOrder, SupplierOrderItem
from inventory.models import InventoryAdjustment
from utils.models import ExchangeRate

class Command(BaseCommand):
    help = 'Diagnostica y repara problemas en órdenes de proveedores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Reparar problemas encontrados automáticamente',
        )
        parser.add_argument(
            '--order-id',
            type=int,
            help='Diagnosticar orden específica por ID',
        )

    def handle(self, *args, **options):
        self.stdout.write('Diagnóstico de órdenes de proveedores iniciado...\n')
        
        if options['order_id']:
            self.diagnose_single_order(options['order_id'], options['fix'])
        else:
            self.diagnose_all_orders(options['fix'])

    def diagnose_single_order(self, order_id, fix=False):
        """Diagnostica una orden específica"""
        try:
            order = SupplierOrder.objects.get(id=order_id)
            self.stdout.write(f'Diagnosticando orden #{order.id} - {order.supplier.name}\n')
            
            # Verificar datos básicos
            issues = self.check_order_data(order)
            
            # Verificar cálculos
            calc_issues = self.check_order_calculations(order)
            issues.extend(calc_issues)
            
            # Verificar ajustes de inventario
            inv_issues = self.check_inventory_adjustments(order)
            issues.extend(inv_issues)
            
            if issues:
                self.stdout.write(self.style.WARNING(f'Problemas encontrados: {len(issues)}'))
                for issue in issues:
                    self.stdout.write(f'  - {issue}')
                
                if fix:
                    self.fix_order_issues(order, issues)
            else:
                self.stdout.write(self.style.SUCCESS('Orden sin problemas detectados'))
                
        except SupplierOrder.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Orden #{order_id} no encontrada'))

    def diagnose_all_orders(self, fix=False):
        """Diagnostica todas las órdenes"""
        
        # 1. Verificar configuración del sistema
        self.stdout.write('1. Verificando configuración del sistema...')
        exchange_rate = ExchangeRate.get_latest_rate()
        if not exchange_rate:
            self.stdout.write(self.style.WARNING('Sin tasa de cambio configurada'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Tasa actual: {exchange_rate.bs_to_usd} Bs/USD'))
        
        # 2. Órdenes con totales incorrectos
        self.stdout.write('\n2. Verificando totales de órdenes...')
        problematic_orders = []
        
        for order in SupplierOrder.objects.all():
            issues = self.check_order_calculations(order)
            if issues:
                problematic_orders.append((order, issues))
        
        if problematic_orders:
            self.stdout.write(self.style.WARNING(f'Órdenes con problemas: {len(problematic_orders)}'))
            for order, issues in problematic_orders[:5]:  # Mostrar solo primeras 5
                self.stdout.write(f'  Orden #{order.id}: {", ".join(issues)}')
            
            if fix:
                self.fix_multiple_orders(problematic_orders)
        else:
            self.stdout.write(self.style.SUCCESS('Todos los cálculos correctos'))
        
        # 3. Órdenes recibidas sin ajustes
        self.stdout.write('\n3. Verificando ajustes de inventario...')
        received_orders = SupplierOrder.objects.filter(status='received')
        orders_without_adjustments = []
        
        for order in received_orders:
            if not self.has_inventory_adjustments(order):
                orders_without_adjustments.append(order)
        
        if orders_without_adjustments:
            self.stdout.write(
                self.style.WARNING(f'Órdenes recibidas sin ajustes: {len(orders_without_adjustments)}')
            )
            if fix:
                self.create_missing_adjustments(orders_without_adjustments)
        else:
            self.stdout.write(self.style.SUCCESS('Todos los ajustes de inventario correctos'))
        
        self.stdout.write('\nDiagnóstico completado.')

    def check_order_data(self, order):
        """Verifica datos básicos de una orden"""
        issues = []
        
        if order.total_usd <= 0 and order.status != 'cancelled':
            issues.append('Total USD es 0 o negativo')
        
        if order.total_bs <= 0 and order.status != 'cancelled':
            issues.append('Total Bs es 0 o negativo')
        
        if order.exchange_rate_used <= 0:
            issues.append('Tasa de cambio inválida')
        
        if not order.items.exists():
            issues.append('Orden sin ítems')
        
        return issues

    def check_order_calculations(self, order):
        """Verifica cálculos de totales"""
        issues = []
        
        # Calcular totales reales
        real_total_usd = Decimal('0')
        real_total_bs = Decimal('0')
        
        for item in order.items.all():
            real_total_usd += item.quantity * item.price_usd
            real_total_bs += item.quantity * item.price_bs
        
        # Verificar discrepancias (tolerancia de 0.01)
        if abs(order.total_usd - real_total_usd) > Decimal('0.01'):
            issues.append(f'Total USD incorrecto: {order.total_usd} vs {real_total_usd}')
        
        if abs(order.total_bs - real_total_bs) > Decimal('0.01'):
            issues.append(f'Total Bs incorrecto: {order.total_bs} vs {real_total_bs}')
        
        # Verificar conversión USD → Bs
        expected_bs = real_total_usd * order.exchange_rate_used
        if abs(real_total_bs - expected_bs) > Decimal('0.01'):
            issues.append(f'Conversión USD→Bs incorrecta: {real_total_bs} vs {expected_bs}')
        
        return issues

    def check_inventory_adjustments(self, order):
        """Verifica ajustes de inventario para una orden"""
        issues = []
        
        if order.status == 'received':
            if not self.has_inventory_adjustments(order):
                issues.append('Orden recibida sin ajustes de inventario')
            else:
                # Verificar que coincida el número de ajustes con ítems
                adjustments_count = InventoryAdjustment.objects.filter(
                    reason__contains=f'orden #{order.id}'
                ).count()
                items_count = order.items.count()
                
                if adjustments_count != items_count:
                    issues.append(f'Ajustes inconsistentes: {adjustments_count} vs {items_count} ítems')
        
        return issues

    def has_inventory_adjustments(self, order):
        """Verifica si una orden tiene ajustes de inventario"""
        return InventoryAdjustment.objects.filter(
            reason__contains=f'orden #{order.id}'
        ).exists()

    def fix_order_issues(self, order, issues):
        """Corrige problemas de una orden específica"""
        self.stdout.write(f'Corrigiendo orden #{order.id}...')
        
        # Recalcular totales
        total_usd = Decimal('0')
        total_bs = Decimal('0')
        
        for item in order.items.all():
            total_usd += item.quantity * item.price_usd
            total_bs += item.quantity * item.price_bs
        
        if total_usd > 0:
            order.total_usd = total_usd
            order.total_bs = total_bs
            order.save()
            self.stdout.write(f'  Totales corregidos: ${total_usd} / Bs {total_bs}')

    def fix_multiple_orders(self, problematic_orders):
        """Corrige múltiples órdenes"""
        self.stdout.write('Corrigiendo órdenes problemáticas...')
        
        fixed_count = 0
        for order, issues in problematic_orders:
            self.fix_order_issues(order, issues)
            fixed_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'{fixed_count} órdenes corregidas'))

    def create_missing_adjustments(self, orders):
        """Crea ajustes de inventario faltantes"""
        self.stdout.write('Creando ajustes de inventario faltantes...')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        system_user = User.objects.filter(is_superuser=True).first()
        
        if not system_user:
            self.stdout.write(self.style.ERROR('No hay usuario administrador para crear ajustes'))
            return
        
        created_count = 0
        for order in orders:
            for item in order.items.all():
                InventoryAdjustment.objects.create(
                    product=item.product,
                    adjustment_type='add',
                    quantity=item.quantity,
                    previous_stock=item.product.stock - item.quantity,
                    new_stock=item.product.stock,
                    reason=f'Recepción orden #{order.id} (ajuste retroactivo)',
                    adjusted_by=system_user
                )
                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'{created_count} ajustes creados'))