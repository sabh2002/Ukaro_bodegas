# suppliers/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import Supplier, SupplierOrder, SupplierOrderItem
from inventory.models import Product

class SupplierForm(forms.ModelForm):
    """Formulario para proveedores"""
    
    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_person', 'phone', 'email', 
            'address', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

class SupplierOrderForm(forms.ModelForm):
    """Formulario para órdenes de compra a proveedores"""
    
    class Meta:
        model = SupplierOrder
        fields = ['supplier', 'status', 'notes', 'paid']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar solo proveedores activos
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)
    
    def save(self, commit=True):
        order = super().save(commit=False)
        
        if not order.pk:  # Solo para nuevas órdenes
            order.created_by = self.user
        
        if commit:
            order.save()
        
        return order

class SupplierOrderItemForm(forms.ModelForm):
    """Formulario para ítems de órdenes de compra"""
    
    class Meta:
        model = SupplierOrderItem
        fields = ['product', 'quantity', 'price_bs']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'price_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo productos activos
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
    
    def clean_quantity(self):
        """Validar cantidad"""
        quantity = self.cleaned_data.get('quantity')
        
        if quantity <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")
        
        return quantity
    
    def clean_price_bs(self):
        """Validar precio"""
        price = self.cleaned_data.get('price_bs')
        
        if price <= 0:
            raise forms.ValidationError("El precio debe ser mayor a cero.")
        
        return price

# Formset para ítems de órdenes de compra
SupplierOrderItemFormset = inlineformset_factory(
    SupplierOrder, 
    SupplierOrderItem,
    form=SupplierOrderItemForm,
    extra=1,
    can_delete=True
)

class ReceiveOrderForm(forms.Form):
    """Formulario para recibir una orden de compra"""
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        label="Notas de recepción"
    )
    update_prices = forms.BooleanField(
        required=False,
        initial=True,
        label="Actualizar precios de compra de los productos"
    )