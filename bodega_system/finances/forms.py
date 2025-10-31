# finances/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import Expense, ExpenseReceipt, DailyClose
from utils.models import ExchangeRate
from datetime import date
from decimal import Decimal

class ExpenseForm(forms.ModelForm):
    """Formulario para gastos con soporte para USD y Bs"""

    class Meta:
        model = Expense
        fields = [
            'category', 'description', 'amount_usd', 'amount_bs', 'date',
            'receipt_number', 'notes'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-input'}),
            'amount_usd': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'placeholder': 'Ingrese monto en USD',
                'id': 'id_amount_usd'
            }),
            'amount_bs': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'placeholder': 'Ingrese monto en Bs',
                'id': 'id_amount_bs'
            }),
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

        # Hacer los campos opcionales individualmente (al menos uno debe tener valor)
        self.fields['amount_usd'].required = False
        self.fields['amount_bs'].required = False

        # Agregar help text
        self.fields['amount_usd'].help_text = 'USD es la moneda principal'
        self.fields['amount_bs'].help_text = 'Se convertirá automáticamente si ingresa USD'

    def clean(self):
        """Validación y conversión automática entre USD y Bs"""
        cleaned_data = super().clean()
        amount_usd = cleaned_data.get('amount_usd')
        amount_bs = cleaned_data.get('amount_bs')
        expense_date = cleaned_data.get('date') or date.today()

        # Al menos uno debe tener valor
        if not amount_usd and not amount_bs:
            raise forms.ValidationError('Debe ingresar el monto en USD o en Bs.')

        # Obtener tasa de cambio
        exchange_rate = ExchangeRate.get_latest_rate()
        if not exchange_rate:
            raise forms.ValidationError('No hay tasa de cambio configurada. Por favor configure una tasa de cambio primero.')

        rate = exchange_rate.bs_to_usd

        # Si solo ingresó USD, calcular Bs
        if amount_usd and not amount_bs:
            if amount_usd <= 0:
                raise forms.ValidationError({'amount_usd': 'El monto en USD debe ser mayor a cero.'})
            cleaned_data['amount_bs'] = amount_usd * rate
            cleaned_data['exchange_rate_used'] = rate

        # Si solo ingresó Bs, calcular USD
        elif amount_bs and not amount_usd:
            if amount_bs <= 0:
                raise forms.ValidationError({'amount_bs': 'El monto en Bs debe ser mayor a cero.'})
            cleaned_data['amount_usd'] = amount_bs / rate
            cleaned_data['exchange_rate_used'] = rate

        # Si ingresó ambos, validar que sean positivos y guardar tasa
        else:
            if amount_usd <= 0:
                raise forms.ValidationError({'amount_usd': 'El monto en USD debe ser mayor a cero.'})
            if amount_bs <= 0:
                raise forms.ValidationError({'amount_bs': 'El monto en Bs debe ser mayor a cero.'})
            cleaned_data['exchange_rate_used'] = rate

        return cleaned_data

    def save(self, commit=True):
        expense = super().save(commit=False)

        # Asignar tasa de cambio
        if hasattr(self, 'cleaned_data'):
            expense.exchange_rate_used = self.cleaned_data.get('exchange_rate_used', Decimal('1.00'))

        if not expense.pk:  # Solo para nuevos gastos
            if not self.user:
                raise forms.ValidationError('Usuario es requerido para crear un gasto.')
            expense.created_by = self.user

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