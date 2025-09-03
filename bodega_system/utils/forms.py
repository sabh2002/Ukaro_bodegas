# utils/forms.py - FORMULARIO PARA TASA DE CAMBIO

from django import forms
from django.utils import timezone
from .models import ExchangeRate


class ExchangeRateForm(forms.ModelForm):
    """Formulario para actualizar la tasa de cambio"""
    
    class Meta:
        model = ExchangeRate
        fields = ['date', 'bs_to_usd']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-white text-gray-900',
            }),
            'bs_to_usd': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-white text-gray-900',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Ej: 154.50'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Establecer fecha de hoy por defecto
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()
        
        # Personalizar labels
        self.fields['date'].label = 'Fecha'
        self.fields['bs_to_usd'].label = 'Tasa de Cambio (Bs por 1 USD)'
        
        # Help text
        self.fields['bs_to_usd'].help_text = 'Ejemplo: Si 1 USD = 154.50 Bs, ingrese 154.50'
    
    def clean_bs_to_usd(self):
        """Validar que la tasa sea positiva y razonable"""
        rate = self.cleaned_data.get('bs_to_usd')
        
        if rate <= 0:
            raise forms.ValidationError("La tasa de cambio debe ser mayor que cero.")
        
        if rate < 1:
            raise forms.ValidationError("La tasa de cambio parece demasiado baja. Verifique el valor.")
        
        if rate > 1000000:
            raise forms.ValidationError("La tasa de cambio parece demasiado alta. Verifique el valor.")
        
        return rate
    
    def clean_date(self):
        """Validar que la fecha no sea futura"""
        date = self.cleaned_data.get('date')
        today = timezone.now().date()
        
        if date > today:
            raise forms.ValidationError("No se puede establecer una tasa de cambio para fechas futuras.")
        
        return date
    
    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        
        if date:
            # Verificar si ya existe una tasa para esta fecha
            existing_rate = ExchangeRate.objects.filter(date=date).first()
            if existing_rate and (not self.instance.pk or existing_rate.pk != self.instance.pk):
                # Si existe, advertir al usuario (pero permitir la actualización)
                self.add_error('date', 
                    f'Ya existe una tasa de cambio para {date.strftime("%d/%m/%Y")} '
                    f'({existing_rate.bs_to_usd} Bs/USD). Se sobrescribirá si continúa.'
                )
        
        return cleaned_data