# suppliers/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import transaction
from django.core.paginator import Paginator

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
    
    # Calcular total
    total = sum(item.quantity * item.price_bs for item in items)
    
    return render(request, 'suppliers/order_detail.html', {
        'order': order,
        'items': items,
        'total': total,
    })

@login_required
def order_create(request):
    """Vista para crear una nueva orden de compra"""
    if request.method == 'POST':
        form = SupplierOrderForm(request.POST, user=request.user)
        formset = SupplierOrderItemFormset(request.POST)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Guardar orden
                order = form.save()
                
                # Guardar ítems de la orden
                formset.instance = order
                formset.save()
                
                # Calcular total
                total_bs = 0
                for form in formset.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        quantity = form.cleaned_data.get('quantity', 0)
                        price_bs = form.cleaned_data.get('price_bs', 0)
                        total_bs += quantity * price_bs
                
                # Actualizar total
                order.total_bs = total_bs
                order.save()
                
                messages.success(request, 'Orden de compra creada exitosamente.')
                return redirect('suppliers:order_detail', pk=order.pk)
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
    
    return render(request, 'suppliers/order_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Nueva Orden de Compra'
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
            with transaction.atomic():
                # Guardar orden
                order = form.save()
                
                # Guardar ítems de la orden
                formset.save()
                
                # Calcular total
                total_bs = 0
                for form in formset.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        quantity = form.cleaned_data.get('quantity', 0)
                        price_bs = form.cleaned_data.get('price_bs', 0)
                        total_bs += quantity * price_bs
                
                # Actualizar total
                order.total_bs = total_bs
                order.save()
                
                messages.success(request, 'Orden de compra actualizada exitosamente.')
                return redirect('suppliers:order_detail', pk=order.pk)
    else:
        form = SupplierOrderForm(instance=order, user=request.user)
        formset = SupplierOrderItemFormset(instance=order)
    
    return render(request, 'suppliers/order_form.html', {
        'form': form,
        'formset': formset,
        'order': order,
        'title': 'Editar Orden de Compra'
    })

@login_required
def order_receive(request, pk):
    """Vista para recibir una orden de compra"""
    order = get_object_or_404(SupplierOrder, pk=pk)
    
    # No permitir recibir órdenes ya recibidas
    if order.status == 'received':
        messages.error(request, 'Esta orden ya ha sido recibida.')
        return redirect('suppliers:order_detail', pk=order.pk)
    
    if request.method == 'POST':
        form = ReceiveOrderForm(request.POST)
        
        if form.is_valid():
            with transaction.atomic():
                # Actualizar estado de la orden
                order.status = 'received'
                order.received_date = timezone.now()
                order.save()
                
                # Actualizar inventario
                update_prices = form.cleaned_data.get('update_prices', False)
                notes = form.cleaned_data.get('notes', '')
                
                # Procesar cada ítem de la orden
                for item in order.items.all():
                    product = item.product
                    previous_stock = product.stock
                    
                    # Actualizar stock
                    product.stock += item.quantity
                    
                    # Actualizar precio de compra si se solicitó
                    if update_prices:
                        product.purchase_price_bs = item.price_bs
                    
                    product.save()
                    
                    # Registrar ajuste de inventario
                    InventoryAdjustment.objects.create(
                        product=product,
                        adjustment_type='add',
                        quantity=item.quantity,
                        previous_stock=previous_stock,
                        new_stock=product.stock,
                        reason=f'Recepción de orden #{order.id} - {notes}',
                        adjusted_by=request.user
                    )
                
                messages.success(request, 'Orden de compra recibida exitosamente.')
                return redirect('suppliers:order_detail', pk=order.pk)
    else:
        form = ReceiveOrderForm()
    
    # Obtener ítems de la orden
    items = order.items.all().select_related('product')
    
    return render(request, 'suppliers/order_receive.html', {
        'form': form,
        'order': order,
        'items': items,
        'title': 'Recibir Orden de Compra'
    })

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