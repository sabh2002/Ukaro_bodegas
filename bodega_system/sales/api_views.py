# sales/api_views.py

import json
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Sale, SaleItem
from inventory.models import Product, InventoryAdjustment
from customers.models import Customer, CustomerCredit

@require_POST
@login_required
def create_sale_api(request):
    """API para crear una venta"""
    try:
        data = json.loads(request.body)
        
        # Validar datos
        if not data.get('items'):
            return JsonResponse({'error': 'No hay productos en la venta'}, status=400)
        
        # Obtener cliente si se especificó
        customer = None
        if data.get('customer_id'):
            customer = get_object_or_404(Customer, pk=data['customer_id'])
            
            # Validar crédito si es venta a crédito
            if data.get('is_credit'):
                total_bs = Decimal(str(data.get('total_bs', 0)))
                
                if customer.available_credit < total_bs:
                    return JsonResponse({
                        'error': f'El cliente no tiene suficiente crédito disponible. '
                                f'Disponible: Bs {customer.available_credit}, Requerido: Bs {total_bs}'
                    }, status=400)
        
        # Crear venta en una transacción
        with transaction.atomic():
            # Crear venta
            sale = Sale.objects.create(
                customer=customer,
                user=request.user,
                total_bs=data.get('total_bs', 0),
                is_credit=data.get('is_credit', False),
                notes=data.get('notes', '')
            )
            
            # Crear ítems de venta y actualizar inventario
            for item_data in data['items']:
                product = get_object_or_404(Product, pk=item_data['product_id'])
                quantity = int(item_data['quantity'])
                
                # Validar stock
                if product.stock < quantity:
                    # Hacer rollback de la transacción
                    transaction.set_rollback(True)
                    return JsonResponse({
                        'error': f'Stock insuficiente para {product.name}. '
                                f'Disponible: {product.stock}, Requerido: {quantity}'
                    }, status=400)
                
                # Crear ítem de venta
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    price_bs=item_data['price_bs']
                )
                
                # Actualizar inventario
                previous_stock = product.stock
                product.stock -= quantity
                product.save()
                
                # Registrar ajuste de inventario
                InventoryAdjustment.objects.create(
                    product=product,
                    adjustment_type='remove',
                    quantity=quantity,
                    previous_stock=previous_stock,
                    new_stock=product.stock,
                    reason=f'Venta #{sale.id}',
                    adjusted_by=request.user
                )
            
            # Crear crédito si es venta a crédito
            if sale.is_credit and customer:
                # Fecha de vencimiento (30 días por defecto)
                from datetime import date, timedelta
                due_date = date.today() + timedelta(days=30)
                
                CustomerCredit.objects.create(
                    customer=customer,
                    sale=sale,
                    amount_bs=sale.total_bs,
                    date_due=due_date
                )
            
            return JsonResponse({
                'id': sale.id,
                'message': 'Venta creada exitosamente'
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)