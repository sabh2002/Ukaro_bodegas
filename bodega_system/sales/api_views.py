# sales/api_views.py - API CON RESTRICCIONES DE ROLES

import json
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied

from .models import Sale, SaleItem
from inventory.models import Product, InventoryAdjustment, ProductCombo
from customers.models import Customer, CustomerCredit
from utils.decorators import sales_access_required

@require_POST
@sales_access_required
def create_sale_api(request):
    """API para crear ventas - Solo empleados y administradores"""
    try:
        data = json.loads(request.body)
        
        if not data.get('items'):
            return JsonResponse({'error': 'No hay productos en la venta'}, status=400)
        
        # Obtener cliente si se especificó
        customer = None
        if data.get('customer_id'):
            customer = get_object_or_404(Customer, pk=data['customer_id'])
        
        with transaction.atomic():
            # Crear venta
            sale = Sale.objects.create(
                customer=customer,
                user=request.user,  # La venta siempre se asigna al usuario actual
                total_bs=Decimal(str(data.get('total_bs', 0))),
                is_credit=data.get('is_credit', False),
                notes=data.get('notes', '')
            )
            
            # Procesar ítems de venta
            for item_data in data['items']:
                if item_data.get('is_combo', False):
                    # Procesar venta de combo
                    result = process_combo_sale(sale, item_data, request.user)
                    if not result['success']:
                        transaction.set_rollback(True)
                        return JsonResponse({'error': result['error']}, status=400)
                else:
                    # Procesar venta normal (incluyendo por peso)
                    result = process_regular_sale(sale, item_data, request.user)
                    if not result['success']:
                        transaction.set_rollback(True)
                        return JsonResponse({'error': result['error']}, status=400)
            
            # Si es venta a crédito, crear el registro de crédito
            if sale.is_credit and customer:
                from datetime import datetime, timedelta
                due_date = datetime.now().date() + timedelta(days=30)  # 30 días por defecto
                
                CustomerCredit.objects.create(
                    customer=customer,
                    sale=sale,
                    amount_bs=sale.total_bs,
                    date_due=due_date,
                    notes=f'Crédito por venta #{sale.id}'
                )
            
            return JsonResponse({
                'id': sale.id,
                'message': 'Venta creada exitosamente',
                'user': request.user.get_full_name() or request.user.username
            })
            
    except PermissionDenied:
        return JsonResponse({'error': 'No tienes permisos para crear ventas'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def process_regular_sale(sale, item_data, user):
    """Procesa venta regular (por unidad o peso)"""
    try:
        product = get_object_or_404(Product, pk=item_data['product_id'])
        
        # Convertir cantidad a Decimal para manejar decimales correctamente
        try:
            if isinstance(item_data['quantity'], str):
                quantity_str = item_data['quantity'].replace(',', '.')
            else:
                quantity_str = str(item_data['quantity'])
            
            quantity = Decimal(quantity_str)
            
        except (InvalidOperation, ValueError) as e:
            return {
                'success': False,
                'error': f'Cantidad inválida para {product.name}: {item_data["quantity"]}'
            }
        
        # Validar que la cantidad sea positiva
        if quantity <= 0:
            return {
                'success': False,
                'error': f'La cantidad debe ser mayor que 0 para {product.name}'
            }
        
        # Validar stock (considerando decimales para peso)
        if product.stock < quantity:
            return {
                'success': False,
                'error': f'Stock insuficiente para {product.name}. '
                        f'Disponible: {product.stock} {product.unit_display}, '
                        f'Requerido: {quantity} {product.unit_display}'
            }
        
        # Calcular precio (considerar precios al mayor)
        unit_price = product.get_price_for_quantity(quantity)
        
        # Crear ítem de venta
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            price_bs=unit_price
        )
        
        # Actualizar inventario
        previous_stock = product.stock
        product.stock -= quantity
        product.save()
        
        # Registrar ajuste de inventario
        adjustment = InventoryAdjustment.objects.create(
            product=product,
            adjustment_type='remove',
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=product.stock,
            reason=f'Venta #{sale.id} - {user.get_full_name() or user.username}',
            adjusted_by=user
        )
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def process_combo_sale(sale, item_data, user):
    """Procesa venta de combo"""
    try:
        combo = get_object_or_404(ProductCombo, pk=item_data['combo_id'])
        
        # Convertir cantidad de combo a entero (los combos se venden por unidades enteras)
        try:
            combo_quantity = int(item_data.get('combo_quantity', 1))
        except (ValueError, TypeError):
            return {
                'success': False,
                'error': f'Cantidad de combo inválida: {item_data.get("combo_quantity", 1)}'
            }
        
        if combo_quantity <= 0:
            return {
                'success': False,
                'error': 'La cantidad de combo debe ser mayor que 0'
            }
        
        # Validar stock para todos los productos del combo
        for combo_item in combo.items.all():
            required_quantity = combo_item.quantity * combo_quantity
            if combo_item.product.stock < required_quantity:
                return {
                    'success': False,
                    'error': f'Stock insuficiente para {combo_item.product.name} '
                            f'(necesario para combo {combo.name}). '
                            f'Disponible: {combo_item.product.stock}, '
                            f'Requerido: {required_quantity}'
                }
        
        # Crear ítem de venta para el combo
        SaleItem.objects.create(
            sale=sale,
            combo=combo,
            quantity=combo_quantity,
            price_bs=combo.combo_price_bs
        )
        
        # Actualizar inventario para cada producto del combo
        for combo_item in combo.items.all():
            product = combo_item.product
            quantity_to_remove = combo_item.quantity * combo_quantity
            
            previous_stock = product.stock
            product.stock -= quantity_to_remove
            product.save()
            
            # Registrar ajuste de inventario
            InventoryAdjustment.objects.create(
                product=product,
                adjustment_type='remove',
                quantity=quantity_to_remove,
                previous_stock=previous_stock,
                new_stock=product.stock,
                reason=f'Venta combo #{sale.id} - {combo.name} - {user.get_full_name() or user.username}',
                adjusted_by=user
            )
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}