# finances/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import Expense, ExpenseReceipt, DailyClose
from datetime import date

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
    
    def save(self, commit=True):
        expense = super().save(commit=False)
        
        if not expense.pk:  # Solo para nuevos gastos
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