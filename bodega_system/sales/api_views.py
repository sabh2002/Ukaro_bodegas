# sales/api_views.py - API corregida para soporte de decimales

import json
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Sale, SaleItem
from inventory.models import Product, InventoryAdjustment, ProductCombo
from customers.models import Customer, CustomerCredit

@require_POST
@login_required
def create_sale_api(request):
    """API mejorada para crear ventas con peso y combos"""
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
                user=request.user,
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
            
            return JsonResponse({
                'id': sale.id,
                'message': 'Venta creada exitosamente'
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def process_regular_sale(sale, item_data, user):
    """Procesa venta regular (por unidad o peso)"""
    try:
        product = get_object_or_404(Product, pk=item_data['product_id'])
        
        # DEBUGGING: Mostrar datos recibidos
        print(f"=== PROCESANDO VENTA REGULAR ===")
        print(f"Producto: {product.name}")
        print(f"Datos recibidos: {item_data}")
        print(f"Cantidad recibida (raw): {repr(item_data['quantity'])}")
        print(f"Tipo de cantidad: {type(item_data['quantity'])}")
        
        # Convertir cantidad a Decimal para manejar decimales correctamente
        try:
            # Asegurar que convertimos correctamente sin importar el tipo
            if isinstance(item_data['quantity'], str):
                quantity_str = item_data['quantity'].replace(',', '.')
            else:
                quantity_str = str(item_data['quantity'])
            
            quantity = Decimal(quantity_str)
            print(f"Cantidad convertida a Decimal: {quantity}")
            
        except (InvalidOperation, ValueError) as e:
            print(f"Error al convertir cantidad: {e}")
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
        
        print(f"Creando SaleItem con cantidad: {quantity} (tipo: {type(quantity)})")
        
        # Crear ítem de venta
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            price_bs=unit_price
        )
        
        print(f"SaleItem creado con ID: {sale_item.id}, cantidad guardada: {sale_item.quantity}")
        
        # Actualizar inventario
        previous_stock = product.stock
        product.stock -= quantity
        product.save()
        
        print(f"Stock actualizado: {previous_stock} -> {product.stock}")
        
        # Registrar ajuste de inventario
        adjustment = InventoryAdjustment.objects.create(
            product=product,
            adjustment_type='remove',
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=product.stock,
            reason=f'Venta #{sale.id}',
            adjusted_by=user
        )
        
        print(f"Ajuste creado con cantidad: {adjustment.quantity}")
        print(f"=== FIN PROCESAMIENTO ===")
        
        return {'success': True}
        
    except Exception as e:
        print(f"Error en process_regular_sale: {e}")
        import traceback
        traceback.print_exc()
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
                reason=f'Venta combo #{sale.id} - {combo.name}',
                adjusted_by=user
            )
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}