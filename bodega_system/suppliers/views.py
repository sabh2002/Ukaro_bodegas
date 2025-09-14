# suppliers/views.py

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Supplier, SupplierOrder, SupplierOrderItem
from .forms import SupplierForm, SupplierOrderForm, SupplierOrderItemFormset, ReceiveOrderForm
from inventory.models import Product, InventoryAdjustment
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Supplier
from .forms import SupplierForm
from utils.decorators import admin_required

@login_required
def supplier_list(request):
    """Vista para listar proveedores"""
    # Filtros
    search_query = request.GET.get('q')
    
    # Consulta base
    suppliers = Supplier.objects.all()
    
    # Aplicar filtros
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Ordenar
    suppliers = suppliers.order_by('name')
    
    # Paginación
    paginator = Paginator(suppliers, 20)  # 20 proveedores por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'suppliers/supplier_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })

@login_required
def supplier_detail(request, pk):
    """Vista para ver detalles de un proveedor"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # Obtener órdenes de compra
    orders = supplier.orders.all().order_by('-order_date')[:10]
    
    # Obtener productos suministrados por este proveedor
    product_data = []
    if orders.exists():
        # Obtener los productos más recientes que se han pedido a este proveedor
        products_ordered = SupplierOrderItem.objects.filter(
            order__supplier=supplier
        ).values('product').annotate(
            total_ordered=Sum('quantity')
        ).order_by('-total_ordered')[:10]
        
        for item in products_ordered:
            try:
                product = Product.objects.get(pk=item['product'])
                # Obtener el último precio de compra de este producto a este proveedor
                last_order_item = SupplierOrderItem.objects.filter(
                    order__supplier=supplier,
                    product=product
                ).order_by('-order__order_date').first()
                
                last_price = last_order_item.price_bs if last_order_item else 0
                
                product_data.append({
                    'product': product,
                    'total_ordered': item['total_ordered'],
                    'last_price': last_price
                })
            except Product.DoesNotExist:
                pass
    
    return render(request, 'suppliers/supplier_detail.html', {
        'supplier': supplier,
        'orders': orders,
        'product_data': product_data,
    })

@login_required
def supplier_create(request):
    """Vista para crear un nuevo proveedor"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Proveedor "{supplier.name}" creado exitosamente.')
            return redirect('suppliers:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm()
    
    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'title': 'Nuevo Proveedor'
    })

@login_required
def supplier_update(request, pk):
    """Vista para actualizar un proveedor"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{supplier.name}" actualizado exitosamente.')
            return redirect('suppliers:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'title': 'Editar Proveedor'
    })

@login_required
def supplier_delete(request, pk):
    """Vista para eliminar un proveedor"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # Verificar si hay órdenes asociadas
    if SupplierOrder.objects.filter(supplier=supplier).exists():
        messages.error(
            request, 
            f'No se puede eliminar el proveedor "{supplier.name}" porque tiene órdenes asociadas.'
        )
        return redirect('suppliers:supplier_detail', pk=supplier.pk)
    
    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f'Proveedor "{supplier_name}" eliminado exitosamente.')
        return redirect('suppliers:supplier_list')
    
    return render(request, 'suppliers/supplier_confirm_delete.html', {
        'supplier': supplier
    })

@login_required
def order_list(request):
    """Vista para listar órdenes de compra"""
    # Filtros
    supplier_id = request.GET.get('supplier')
    status = request.GET.get('status')
    
    # Consulta base
    orders = SupplierOrder.objects.all()
    
    # Aplicar filtros
    if supplier_id:
        orders = orders.filter(supplier_id=supplier_id)
    
    if status:
        orders = orders.filter(status=status)
    
    # Ordenar
    orders = orders.order_by('-order_date')
    
    # Paginación
    paginator = Paginator(orders, 20)  # 20 órdenes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener proveedores para el filtro
    suppliers = Supplier.objects.filter(
        is_active=True
    ).order_by('name')
    
    return render(request, 'suppliers/order_list.html', {
        'page_obj': page_obj,
        'suppliers': suppliers,
        'selected_supplier': int(supplier_id) if supplier_id else None,
        'status': status,
    })

@login_required
def order_detail(request, pk):
    """Vista para ver detalles de una orden"""
    order = get_object_or_404(SupplierOrder, pk=pk)
    
    # Obtener ítems de la orden
    items = order.items.all().select_related('product')
    
    # Calcular totales
    total_usd = sum(item.quantity * item.price_usd for item in items)
    total_bs = sum(item.quantity * item.price_bs for item in items)
    
    return render(request, 'suppliers/order_detail.html', {
        'order': order,
        'items': items,
        'total_usd': total_usd,
        'total_bs': total_bs,
    })

@login_required
def order_create(request):
    """Vista para crear una nueva orden de compra"""
    if request.method == 'POST':
        print("===== ORDER CREATE POST REQUEST =====")
        print("POST data:", dict(request.POST))
        print("=====================================")
        
        form = SupplierOrderForm(request.POST, user=request.user)
        formset = SupplierOrderItemFormset(request.POST)
        
        print("Form valid:", form.is_valid())
        print("Form errors:", form.errors)
        print("Formset valid:", formset.is_valid())
        print("Formset errors:", formset.errors)
        print("Formset non_form_errors:", formset.non_form_errors())
        
        if form.is_valid() and formset.is_valid():
            # Obtener tasa de cambio actual
            from utils.models import ExchangeRate
            exchange_rate = ExchangeRate.get_latest_rate()
            
            if not exchange_rate:
                messages.error(request, 'No se ha configurado una tasa de cambio. Configure la tasa antes de crear órdenes.')
                return redirect('suppliers:order_create')
            
            with transaction.atomic():
                # Guardar orden
                order = form.save()
                
                # Procesar y guardar ítems de la orden
                formset.instance = order
                
                # Crear productos nuevos antes de guardar el formset
                for form in formset.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        if form.cleaned_data.get('is_new_product'):
                            # Crear el producto nuevo
                            new_product = _create_product_from_form(form, exchange_rate)
                            form.instance.product = new_product
                
                formset.save()
                
                # Calcular totales
                total_usd = 0
                for form in formset.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        quantity = form.cleaned_data.get('quantity', 0)
                        price_usd = form.cleaned_data.get('price_usd', 0)
                        total_usd += quantity * price_usd
                
                # Actualizar totales y tasa
                order.total_usd = total_usd
                order.total_bs = total_usd * exchange_rate.bs_to_usd
                order.exchange_rate_used = exchange_rate.bs_to_usd
                order.save()
                
                messages.success(request, 'Orden de compra creada exitosamente.')
                return redirect('suppliers:order_detail', pk=order.pk)
        else:
            # Formulario o formset inválido
            print("===== FORM/FORMSET INVALID =====")
            messages.error(request, 'Error en el formulario. Revise los datos.')
    else:
        # Pre-seleccionar proveedor si se pasa por URL
        supplier_id = request.GET.get('supplier')
        initial = {}
        if supplier_id:
            try:
                supplier = Supplier.objects.get(pk=supplier_id)
                initial['supplier'] = supplier
            except Supplier.DoesNotExist:
                pass
        
        form = SupplierOrderForm(initial=initial, user=request.user)
        formset = SupplierOrderItemFormset()
    
    # Obtener tasa de cambio para mostrar en el template
    from utils.models import ExchangeRate
    from inventory.models import Category, Product
    current_rate = ExchangeRate.get_latest_rate()
    
    # Obtener categorías y opciones de unidad
    categories = Category.objects.all().order_by('name')
    unit_choices = Product.UNIT_TYPES
    
    return render(request, 'suppliers/order_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Nueva Orden de Compra',
        'current_exchange_rate': current_rate,
        'categories': categories,
        'unit_choices': unit_choices,
    })

@login_required
def order_update(request, pk):
    """Vista para actualizar una orden de compra"""
    order = get_object_or_404(SupplierOrder, pk=pk)
    
    # No permitir editar órdenes recibidas
    if order.status == 'received':
        messages.error(request, 'No se puede editar una orden que ya ha sido recibida.')
        return redirect('suppliers:order_detail', pk=order.pk)
    
    if request.method == 'POST':
        form = SupplierOrderForm(request.POST, instance=order, user=request.user)
        formset = SupplierOrderItemFormset(request.POST, instance=order)
        
        if form.is_valid() and formset.is_valid():
            # Obtener tasa de cambio actual
            from utils.models import ExchangeRate
            exchange_rate = ExchangeRate.get_latest_rate()
            
            if not exchange_rate:
                messages.error(request, 'No se ha configurado una tasa de cambio. Configure la tasa antes de actualizar órdenes.')
                return redirect('suppliers:order_detail', pk=order.pk)
            
            with transaction.atomic():
                # Guardar orden
                order = form.save()
                
                # Procesar y guardar ítems de la orden
                # Crear productos nuevos antes de guardar el formset
                for form in formset.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        if form.cleaned_data.get('is_new_product'):
                            # Crear el producto nuevo
                            new_product = _create_product_from_form(form, exchange_rate)
                            form.instance.product = new_product
                
                # Guardar ítems de la orden
                formset.save()
                
                # Calcular totales
                total_usd = 0
                for form in formset.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        quantity = form.cleaned_data.get('quantity', 0)
                        price_usd = form.cleaned_data.get('price_usd', 0)
                        total_usd += quantity * price_usd
                
                # Actualizar totales y tasa
                order.total_usd = total_usd
                order.total_bs = total_usd * exchange_rate.bs_to_usd
                order.exchange_rate_used = exchange_rate.bs_to_usd
                order.save()
                
                messages.success(request, 'Orden de compra actualizada exitosamente.')
                return redirect('suppliers:order_detail', pk=order.pk)
    else:
        form = SupplierOrderForm(instance=order, user=request.user)
        formset = SupplierOrderItemFormset(instance=order)
    
    # Obtener tasa de cambio para mostrar en el template
    from utils.models import ExchangeRate
    from inventory.models import Category, Product
    current_rate = ExchangeRate.get_latest_rate()
    
    # Obtener categorías y opciones de unidad
    categories = Category.objects.all().order_by('name')
    unit_choices = Product.UNIT_TYPES
    
    return render(request, 'suppliers/order_form.html', {
        'form': form,
        'formset': formset,
        'order': order,
        'title': 'Editar Orden de Compra',
        'current_exchange_rate': current_rate,
        'categories': categories,
        'unit_choices': unit_choices,
    })

@login_required
def order_receive(request, pk):
    """Vista para recibir una orden de compra - CORREGIDA"""
    order = get_object_or_404(SupplierOrder, pk=pk)
    
    if order.status == 'received':
        messages.error(request, 'Esta orden ya ha sido recibida.')
        return redirect('suppliers:order_detail', pk=order.pk)
    
    if request.method == 'POST':
        form = ReceiveOrderForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Actualizar estado de la orden
                    order.status = 'received'
                    order.received_date = timezone.now()
                    order.save()
                    
                    # Obtener datos del formulario
                    update_prices = form.cleaned_data.get('update_prices', False)
                    notes = form.cleaned_data.get('notes', '').strip()
                    
                    # Contadores para el mensaje de confirmación
                    updated_products = []
                    total_items_received = Decimal('0')
                    
                    # Procesar cada ítem de la orden
                    for item in order.items.all():
                        product = item.product
                        previous_stock = product.stock
                        
                        # ✅ CORRECCIÓN CRÍTICA: Asegurar que quantity sea Decimal
                        quantity_to_add = Decimal(str(item.quantity))
                        total_items_received += quantity_to_add
                        
                        # Actualizar stock (ambos son Decimal ahora)
                        product.stock = previous_stock + quantity_to_add
                        
                        # Actualizar precios si se solicitó
                        if update_prices:
                            # Verificar si el producto tiene campos USD
                            if hasattr(product, 'purchase_price_usd'):
                                product.purchase_price_usd = item.price_usd
                            
                            # Actualizar precio en Bs
                            product.purchase_price_bs = item.price_bs
                        
                        product.save()
                        updated_products.append({
                            'name': product.name,
                            'quantity': quantity_to_add,
                            'previous_stock': previous_stock,
                            'new_stock': product.stock
                        })
                        
                        # ✅ REGISTRAR AJUSTE DE INVENTARIO
                        InventoryAdjustment.objects.create(
                            product=product,
                            adjustment_type='add',
                            quantity=quantity_to_add,
                            previous_stock=previous_stock,
                            new_stock=product.stock,
                            reason=f'Recepción orden #{order.id}' + (f' - {notes}' if notes else ''),
                            adjusted_by=request.user
                        )
                    
                    # ✅ MENSAJE DE ÉXITO DETALLADO
                    product_names = [p['name'] for p in updated_products[:3]]
                    products_summary = ', '.join(product_names)
                    if len(updated_products) > 3:
                        products_summary += f' y {len(updated_products) - 3} más'
                    
                    messages.success(
                        request,
                        f'Orden #{order.id} recibida exitosamente. '
                        f'Productos actualizados: {products_summary}. '
                        f'Total ítems: {total_items_received}. '
                        f'Valor: ${order.total_usd} (Bs {order.total_bs})'
                    )
                    
                    return redirect('suppliers:order_detail', pk=order.pk)
                    
            except Exception as e:
                # Log del error para debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error en order_receive orden #{order.id}: {str(e)}")
                
                messages.error(request, f'Error al recibir la orden: {str(e)}')
                
    else:
        form = ReceiveOrderForm()
    
    # Obtener ítems de la orden con información adicional
    items = order.items.all().select_related('product')
    
    # Información adicional para el template
    context = {
        'form': form,
        'order': order,
        'items': items,
        'title': f'Recibir Orden #{order.id}',
        'total_items_count': items.count(),
        'total_products_quantity': sum(item.quantity for item in items),
        'estimated_new_total': sum(item.product.stock + item.quantity for item in items),
    }
    
    return render(request, 'suppliers/order_receive.html', context)

@admin_required
def order_cancel(request, pk):
    """Vista para cancelar una orden de compra"""
    order = get_object_or_404(SupplierOrder, pk=pk)
    
    # No permitir cancelar órdenes recibidas
    if order.status == 'received':
        messages.error(request, 'No se puede cancelar una orden que ya ha sido recibida.')
        return redirect('suppliers:order_detail', pk=order.pk)
    
    if request.method == 'POST':
        # Actualizar estado de la orden
        order.status = 'cancelled'
        order.save()
        
        messages.success(request, 'Orden de compra cancelada exitosamente.')
        return redirect('suppliers:order_detail', pk=order.pk)
    
    return render(request, 'suppliers/order_confirm_cancel.html', {
        'order': order
    })

def _create_product_from_form(form, exchange_rate):
    """Helper para crear un producto nuevo desde el formulario"""
    from inventory.models import Product
    
    selling_price_usd = form.cleaned_data['new_product_selling_price_usd']
    purchase_price_usd = form.cleaned_data['price_usd']
    
    product = Product.objects.create(
        name=form.cleaned_data['new_product_name'],
        barcode=form.cleaned_data['new_product_barcode'],
        category=form.cleaned_data['new_product_category'],
        unit_type=form.cleaned_data.get('new_product_unit_type', 'unit'),
        purchase_price_usd=purchase_price_usd,
        purchase_price_bs=purchase_price_usd * exchange_rate.bs_to_usd,
        selling_price_usd=selling_price_usd,
        selling_price_bs=selling_price_usd * exchange_rate.bs_to_usd,
        stock=0,  # Inicialmente en 0, se actualizará al recibir la orden
        min_stock=form.cleaned_data.get('new_product_min_stock', 5),
        is_active=True
    )
    
    return product


@login_required
def product_lookup_api(request, barcode):
    """API endpoint para buscar productos por código de barras"""
    try:
        product = Product.objects.get(barcode=barcode, is_active=True)
        
        return JsonResponse({
            'exists': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'barcode': product.barcode,
                'category': product.category,
                'unit_type': product.unit_type,
                'purchase_price_usd': str(product.purchase_price_usd),
                'selling_price_usd': str(product.selling_price_usd),
                'stock': product.stock,
                'min_stock': product.min_stock,
            }
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'exists': False,
            'product': None
        })