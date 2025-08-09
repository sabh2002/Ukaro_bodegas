# customers/views.py - CON RESTRICCIONES DE ROLES

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, F, Q
from django.core.paginator import Paginator

from .models import Customer, CustomerCredit, CreditPayment
from .forms import CustomerForm, CreditForm, CreditPaymentForm
from sales.models import Sale
from utils.decorators import admin_required, employee_or_admin_required, customer_access_required

@customer_access_required
def customer_list(request):
    """Vista para listar clientes - Empleados y Administradores"""
    # Filtros
    search_query = request.GET.get('q')
    credit_filter = request.GET.get('credit')
    
    # Consulta base
    customers = Customer.objects.all()
    
    # Aplicar filtros
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if credit_filter == 'with_credit':
        customers = customers.filter(credit_limit_bs__gt=0)
    elif credit_filter == 'with_pending':
        customers_with_pending = CustomerCredit.objects.filter(
            is_paid=False
        ).values_list('customer_id', flat=True).distinct()
        
        customers = customers.filter(id__in=customers_with_pending)
    
    # Ordenar
    customers = customers.order_by('name')
    
    # Paginación
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'customers/customer_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'credit_filter': credit_filter,
        'is_admin': request.user.is_admin or request.user.is_superuser,
    })

@customer_access_required
def customer_detail(request, pk):
    """Vista para ver detalles de un cliente - Empleados y Administradores"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Obtener créditos
    credits = customer.credits.all().order_by('-date_created')
    
    # Obtener historial de ventas
    sales = Sale.objects.filter(customer=customer).order_by('-date')[:10]
    
    # Si es empleado, solo mostrar sus propias ventas
    if not (request.user.is_admin or request.user.is_superuser):
        sales = sales.filter(user=request.user)
    
    return render(request, 'customers/customer_detail.html', {
        'customer': customer,
        'credits': credits,
        'sales': sales,
        'is_admin': request.user.is_admin or request.user.is_superuser,
    })

@customer_access_required
def customer_create(request):
    """Vista para crear un nuevo cliente - Empleados y Administradores"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Cliente "{customer.name}" creado exitosamente.')
            return redirect('customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    return render(request, 'customers/customer_form.html', {
        'form': form,
        'title': 'Nuevo Cliente'
    })

@customer_access_required
def customer_update(request, pk):
    """Vista para actualizar un cliente - Empleados y Administradores"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente "{customer.name}" actualizado exitosamente.')
            return redirect('customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'customers/customer_form.html', {
        'form': form,
        'customer': customer,
        'title': 'Editar Cliente'
    })

@admin_required
def customer_delete(request, pk):
    """Vista para eliminar un cliente - Solo Administradores"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Verificar si hay ventas o créditos asociados
    if Sale.objects.filter(customer=customer).exists() or CustomerCredit.objects.filter(customer=customer).exists():
        messages.error(
            request, 
            f'No se puede eliminar el cliente "{customer.name}" porque tiene ventas o créditos asociados.'
        )
        return redirect('customers:customer_detail', pk=customer.pk)
    
    if request.method == 'POST':
        customer_name = customer.name
        customer.delete()
        messages.success(request, f'Cliente "{customer_name}" eliminado exitosamente.')
        return redirect('customers:customer_list')
    
    return render(request, 'customers/customer_confirm_delete.html', {
        'customer': customer
    })

@admin_required
def credit_list(request):
    """Vista para listar créditos de clientes - Solo Administradores"""
    # Filtros
    customer_id = request.GET.get('customer')
    status = request.GET.get('status')
    
    # Consulta base
    credits = CustomerCredit.objects.all()
    
    # Aplicar filtros
    if customer_id:
        credits = credits.filter(customer_id=customer_id)
    
    if status == 'pending':
        credits = credits.filter(is_paid=False)
    elif status == 'paid':
        credits = credits.filter(is_paid=True)
    elif status == 'overdue':
        today = timezone.now().date()
        credits = credits.filter(is_paid=False, date_due__lt=today)
    
    # Ordenar
    credits = credits.order_by('-date_created')
    
    # Paginación
    paginator = Paginator(credits, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener clientes para el filtro
    customers = Customer.objects.filter(
        is_active=True
    ).order_by('name')
    
    return render(request, 'customers/credit_list.html', {
        'page_obj': page_obj,
        'customers': customers,
        'selected_customer': int(customer_id) if customer_id else None,
        'status': status,
    })

@admin_required
def credit_detail(request, pk):
    """Vista para ver detalles de un crédito - Solo Administradores"""
    credit = get_object_or_404(CustomerCredit, pk=pk)
    
    # Obtener pagos
    payments = credit.payments.all().order_by('-payment_date')
    
    # Calcular saldo pendiente
    total_paid = payments.aggregate(total=Sum('amount_bs'))['total'] or 0
    pending_amount = credit.amount_bs - total_paid
    
    return render(request, 'customers/credit_detail.html', {
        'credit': credit,
        'payments': payments,
        'total_paid': total_paid,
        'pending_amount': pending_amount,
    })

@admin_required
def credit_create(request):
    """Vista para crear un nuevo crédito - Solo Administradores"""
    if request.method == 'POST':
        form = CreditForm(request.POST)
        if form.is_valid():
            credit = form.save(commit=False)
            credit.save()
            messages.success(request, f'Crédito creado exitosamente para {credit.customer.name}.')
            return redirect('customers:credit_detail', pk=credit.pk)
    else:
        customer_id = request.GET.get('customer')
        initial = {}
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                initial['customer'] = customer
            except Customer.DoesNotExist:
                pass
        
        form = CreditForm(initial=initial)
    
    return render(request, 'customers/credit_form.html', {
        'form': form,
        'title': 'Nuevo Crédito'
    })

@customer_access_required
def credit_payment(request, pk):
    """Vista para registrar pago de un crédito - Empleados y Administradores"""
    credit = get_object_or_404(CustomerCredit, pk=pk)
    
    # Verificar si el crédito ya está pagado
    if credit.is_paid:
        messages.error(request, 'Este crédito ya está completamente pagado.')
        return redirect('customers:credit_detail', pk=credit.pk)
    
    if request.method == 'POST':
        form = CreditPaymentForm(request.POST, credit=credit)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.credit = credit
            payment.received_by = request.user
            payment.save()
            
            # Calcular si el crédito está pagado completamente
            total_paid = credit.payments.aggregate(total=Sum('amount_bs'))['total'] or 0
            if total_paid >= credit.amount_bs:
                credit.is_paid = True
                credit.date_paid = timezone.now()
                credit.save()
                messages.success(request, 'Crédito pagado completamente.')
            else:
                messages.success(request, 'Pago registrado exitosamente.')
            
            return redirect('customers:customer_detail', pk=credit.customer.pk)
    else:
        form = CreditPaymentForm(credit=credit)
    
    # Calcular saldo pendiente
    total_paid = credit.payments.aggregate(total=Sum('amount_bs'))['total'] or 0
    pending_amount = credit.amount_bs - total_paid
    
    return render(request, 'customers/credit_payment.html', {
        'form': form,
        'credit': credit,
        'total_paid': total_paid,
        'pending_amount': pending_amount,
        'title': 'Registrar Pago'
    })