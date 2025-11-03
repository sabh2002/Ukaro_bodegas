# customers/forms.py

from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Customer, CustomerCredit, CreditPayment

class CustomerForm(forms.ModelForm):
    """Formulario para clientes"""
    
    class Meta:
        model = Customer
        fields = [
            'name', 'phone', 'email', 'address', 
            'credit_limit_bs', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'credit_limit_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

class CreditForm(forms.ModelForm):
    """Formulario para créditos de clientes"""
    
    class Meta:
        model = CustomerCredit
        fields = ['customer', 'amount_bs', 'date_due', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'amount_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'date_due': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Establecer fecha de vencimiento por defecto (30 días)
        if not self.instance.pk and not self.initial.get('date_due'):
            self.initial['date_due'] = (timezone.now() + timedelta(days=30)).date()
        
        # Filtrar solo clientes con crédito disponible
        self.fields['customer'].queryset = Customer.objects.filter(
            is_active=True, 
            credit_limit_bs__gt=0
        )
    
    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        amount_bs = cleaned_data.get('amount_bs')
        
        if customer and amount_bs:
            # Validar límite de crédito disponible
            if not self.instance.pk:  # Solo para nuevos créditos
                available_credit = customer.available_credit
                if amount_bs > available_credit:
                    self.add_error('amount_bs', 
                        f'El monto excede el crédito disponible. '
                        f'Disponible: {available_credit} Bs')
        
        return cleaned_data

class CreditPaymentForm(forms.ModelForm):
    """Formulario para pagos de créditos"""
    
    class Meta:
        model = CreditPayment
        fields = ['amount_bs', 'notes']
        widgets = {
            'amount_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
    
    def __init__(self, *args, credit=None, **kwargs):
        self.credit = credit
        super().__init__(*args, **kwargs)

        if credit:
            # ⭐ CORREGIDO: Calcular monto pendiente en USD
            from django.db.models import Sum
            total_paid_usd = credit.payments.aggregate(total=Sum('amount_usd'))['total'] or 0
            pending_amount_usd = credit.amount_usd - total_paid_usd

            # Calcular en Bs (para backward compatibility)
            total_paid_bs = credit.payments.aggregate(total=Sum('amount_bs'))['total'] or 0
            pending_amount_bs = credit.amount_bs - total_paid_bs

            self.fields['amount_bs'].initial = pending_amount_bs
            self.fields['amount_bs'].widget.attrs['max'] = pending_amount_bs

            # ⭐ NUEVO: Agregar help_text con información USD
            from utils.models import ExchangeRate
            current_rate = ExchangeRate.get_latest_rate()
            if current_rate:
                equivalent_usd = pending_amount_bs / current_rate.bs_to_usd
                self.fields['amount_bs'].help_text = (
                    f'Pendiente: ${pending_amount_usd:.2f} USD '
                    f'(Bs {pending_amount_bs:.2f} a tasa actual {current_rate.bs_to_usd}). '
                    f'Ingrese monto en Bs, se calculará USD automáticamente.'
                )
    
    def clean_amount_bs(self):
        """Validar monto de pago"""
        amount = self.cleaned_data.get('amount_bs')

        if amount <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')

        if self.credit:
            # ⭐ CORREGIDO: Calcular monto pendiente usando USD (más preciso)
            from django.db.models import Sum
            total_paid_usd = self.credit.payments.aggregate(total=Sum('amount_usd'))['total'] or 0
            pending_amount_usd = self.credit.amount_usd - total_paid_usd

            # Convertir monto ingresado a USD para validar
            from utils.models import ExchangeRate
            current_rate = ExchangeRate.get_latest_rate()
            if current_rate:
                amount_usd = amount / current_rate.bs_to_usd
                if amount_usd > pending_amount_usd:
                    raise forms.ValidationError(
                        f'El monto excede el saldo pendiente (${pending_amount_usd:.2f} USD).')

        return amount