from django import forms
from django.forms import inlineformset_factory
from .models import Category, Product, InventoryAdjustment, ProductCombo, ComboItem

class CategoryForm(forms.ModelForm):
    """Formulario para categorías de productos"""
    
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

class ProductForm(forms.ModelForm):
    """Formulario mejorado para productos con peso y combos"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'barcode', 'category', 'description', 'image',
            'unit_type', 'purchase_price_bs', 'selling_price_bs', 
            'min_stock', 'is_bulk_pricing', 'bulk_min_quantity', 
            'bulk_price_bs', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'barcode': forms.TextInput(attrs={'class': 'form-input'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'unit_type': forms.Select(attrs={'class': 'form-select'}),
            'purchase_price_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'selling_price_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001'}),
            'bulk_min_quantity': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001'}),
            'bulk_price_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Hacer campos de precio al mayor opcionales inicialmente
        self.fields['bulk_min_quantity'].required = False
        self.fields['bulk_price_bs'].required = False
    
    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        purchase_price = cleaned_data.get('purchase_price_bs')
        selling_price = cleaned_data.get('selling_price_bs')
        is_bulk_pricing = cleaned_data.get('is_bulk_pricing')
        bulk_min_quantity = cleaned_data.get('bulk_min_quantity')
        bulk_price_bs = cleaned_data.get('bulk_price_bs')
        
        # Validar que el precio de venta sea mayor al precio de compra
        if purchase_price and selling_price and selling_price < purchase_price:
            self.add_error('selling_price_bs', "El precio de venta debe ser mayor o igual al precio de compra.")
        
        # Validar campos de precio al mayor si está habilitado
        if is_bulk_pricing:
            if not bulk_min_quantity:
                self.add_error('bulk_min_quantity', "Debe especificar la cantidad mínima para precio al mayor.")
            if not bulk_price_bs:
                self.add_error('bulk_price_bs', "Debe especificar el precio al mayor.")
            
            # Validar que precio al mayor sea menor que precio normal
            if bulk_price_bs and selling_price and bulk_price_bs >= selling_price:
                self.add_error('bulk_price_bs', "El precio al mayor debe ser menor que el precio normal.")
        
        return cleaned_data

class InventoryAdjustmentForm(forms.ModelForm):
    """Formulario mejorado para ajustes de inventario con decimales"""
    
    class Meta:
        model = InventoryAdjustment
        fields = ['product', 'adjustment_type', 'quantity', 'reason']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'adjustment_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001', 'min': '0.001'}),
            'reason': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_quantity(self):
        """Validar cantidad"""
        quantity = self.cleaned_data.get('quantity')
        
        if quantity <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")
        
        return quantity

# NUEVOS FORMULARIOS PARA COMBOS

class ProductComboForm(forms.ModelForm):
    """Formulario para crear combos de productos"""
    
    class Meta:
        model = ProductCombo
        fields = ['name', 'description', 'combo_price_bs', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'combo_price_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }

class ComboItemForm(forms.ModelForm):
    """Formulario para ítems de combo"""
    
    class Meta:
        model = ComboItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001', 'min': '0.001'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo productos activos
        self.fields['product'].queryset = Product.objects.filter(is_active=True)

# Formset para manejo de ítems de combo
ComboItemFormset = inlineformset_factory(
    ProductCombo, 
    ComboItem,
    form=ComboItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)