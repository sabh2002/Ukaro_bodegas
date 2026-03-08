# finances/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import Expense, ExpenseReceipt, DailyClose
from datetime import date
from accounts.models import User
from sales.models import Sale
from suppliers.models import Supplier
from inventory.models import Category

class ExpenseForm(forms.ModelForm):
    """Formulario para gastos"""
    
    class Meta:
        model = Expense
        fields = [
            'category', 'description', 'amount_bs', 'date', 
            'receipt_number', 'notes'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-input'}),
            'amount_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Establecer fecha actual por defecto
        if not self.instance.pk:
            self.fields['date'].initial = date.today()
    
    def clean_amount_bs(self):
        """Validar que el monto sea positivo"""
        amount = self.cleaned_data.get('amount_bs')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return amount

    def save(self, commit=True):
        expense = super().save(commit=False)

        if not expense.pk:  # Solo para nuevos gastos
            if not self.user:
                raise forms.ValidationError('Usuario es requerido para crear un gasto.')
            expense.created_by = self.user

            # ⭐ NUEVO: Calcular USD y guardar tasa de cambio utilizada
            from utils.models import ExchangeRate
            current_rate = ExchangeRate.get_latest_rate()
            if current_rate:
                expense.exchange_rate_used = current_rate.bs_to_usd
                expense.amount_usd = expense.amount_bs / current_rate.bs_to_usd
            else:
                # Fallback si no hay tasa configurada
                from decimal import Decimal
                expense.exchange_rate_used = Decimal('36.00')
                expense.amount_usd = expense.amount_bs / Decimal('36.00')

        if commit:
            expense.save()

        return expense

class ExpenseReceiptForm(forms.ModelForm):
    """Formulario para comprobantes de gastos"""
    
    class Meta:
        model = ExpenseReceipt
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-input', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'description': forms.TextInput(attrs={'class': 'form-input'}),
        }

# Formset para comprobantes de gastos
ExpenseReceiptFormset = inlineformset_factory(
    Expense,
    ExpenseReceipt,
    form=ExpenseReceiptForm,
    extra=1,
    can_delete=True
)

class DailyCloseForm(forms.ModelForm):
    """Formulario para cierre diario"""
    
    class Meta:
        model = DailyClose
        fields = ['date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Establecer fecha actual por defecto
        if not self.instance.pk:
            self.fields['date'].initial = date.today()

class ReportFilterForm(forms.Form):
    """Formulario para filtros de reportes"""
    PERIOD_CHOICES = (
        ('today', 'Hoy'),
        ('yesterday', 'Ayer'),
        ('this_week', 'Esta Semana'),
        ('last_week', 'Semana Pasada'),
        ('this_month', 'Este Mes'),
        ('last_month', 'Mes Pasado'),
        ('this_year', 'Este Año'),
        ('custom', 'Personalizado'),
    )
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        initial='this_month',
        label="Período",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        label="Fecha de inicio",
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        label="Fecha de fin",
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('period')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if period == 'custom':
            if not start_date:
                raise forms.ValidationError('Fecha de inicio es requerida para período personalizado.')
            if not end_date:
                raise forms.ValidationError('Fecha de fin es requerida para período personalizado.')
            if start_date > end_date:
                raise forms.ValidationError('La fecha de inicio no puede ser mayor a la fecha de fin.')

        return cleaned_data


class SalesReportFilterForm(ReportFilterForm):
    """Filtros extendidos para reporte de ventas"""
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        label="Empleado",
        empty_label="Todos",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_method = forms.ChoiceField(
        choices=[('', 'Todos')] + list(Sale.PAYMENT_METHODS) + [('credit', 'Crédito')],
        required=False,
        label="Método de Pago",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class PurchasesReportFilterForm(ReportFilterForm):
    """Filtros extendidos para reporte de compras"""
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        required=False,
        label="Proveedor",
        empty_label="Todos",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_status = forms.ChoiceField(
        choices=[('', 'Todos'), ('paid', 'Pagado'), ('unpaid', 'Pendiente')],
        required=False,
        label="Estado de Pago",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class InventoryFilterForm(forms.Form):
    """Filtros para reporte de inventario"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="Categoría",
        empty_label="Todas",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    stock_status = forms.ChoiceField(
        choices=[('', 'Todos'), ('normal', 'Normal'), ('low', 'Bajo'), ('out', 'Sin stock')],
        required=False,
        label="Estado de Stock",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sort_by = forms.ChoiceField(
        choices=[('name', 'Nombre'), ('stock', 'Stock'), ('value', 'Valor en inventario'), ('category', 'Categoría')],
        required=False,
        label="Ordenar por",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class CreditsReportFilterForm(ReportFilterForm):
    """Filtros para reporte de cuentas por cobrar"""
    credit_status = forms.ChoiceField(
        choices=[('pending', 'Pendientes'), ('overdue', 'Vencidos'), ('paid', 'Pagados'), ('all', 'Todos')],
        initial='pending',
        required=False,
        label="Estado del Crédito",
        widget=forms.Select(attrs={'class': 'form-select'})
    )