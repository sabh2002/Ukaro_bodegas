# inventory/forms.py - FORMULARIO DE PRODUCTOS EN USD

from django import forms
from django.forms import inlineformset_factory
from django.db import transaction
from decimal import Decimal, InvalidOperation

from .models import Category, Product, InventoryAdjustment, ProductCombo, ComboItem


class ProductForm(forms.ModelForm):
    """Formulario para productos con precios en USD"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'barcode', 'category', 'unit_type', 'description', 'image',
            # ⭐ CAMBIO: Solo campos USD
            'purchase_price_usd', 'selling_price_usd', 'min_stock', 'is_active',
            # Precios al mayor en USD (pendiente de implementar)
            'is_bulk_pricing', 'bulk_min_quantity', 'bulk_price_usd'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'placeholder': 'Nombre del producto'
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'placeholder': 'Código de barras'
            }),
            'category': forms.Select(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'unit_type': forms.Select(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'description': forms.Textarea(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'rows': 3,
                'placeholder': 'Descripción del producto...'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            # ⭐ PRECIOS EN USD
            'purchase_price_usd': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'selling_price_usd': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'min_stock': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.001',
                'min': '0',
                'placeholder': '5.000'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'is_bulk_pricing': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'bulk_min_quantity': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.001',
                'min': '0',
                'placeholder': '0.000'
            }),
            'bulk_price_usd': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar labels
        self.fields['purchase_price_usd'].label = 'Precio de Compra (USD)'
        self.fields['selling_price_usd'].label = 'Precio de Venta (USD)'
        self.fields['bulk_price_usd'].label = 'Precio al Mayor (USD)'
        
        # Help text
        self.fields['purchase_price_usd'].help_text = 'Precio de compra en dólares estadounidenses'
        self.fields['selling_price_usd'].help_text = 'Precio de venta en dólares estadounidenses'
        
        # Hacer algunos campos requeridos
        self.fields['category'].required = True
        self.fields['purchase_price_usd'].required = True
        self.fields['selling_price_usd'].required = True
    
    def clean_purchase_price_usd(self):
        """Validar precio de compra"""
        price = self.cleaned_data.get('purchase_price_usd')
        
        if price is None:
            raise forms.ValidationError("El precio de compra es requerido.")
        
        if price <= 0:
            raise forms.ValidationError("El precio de compra debe ser mayor que cero.")
        
        return price
    
    def clean_selling_price_usd(self):
        """Validar precio de venta"""
        price = self.cleaned_data.get('selling_price_usd')
        
        if price is None:
            raise forms.ValidationError("El precio de venta es requerido.")
        
        if price <= 0:
            raise forms.ValidationError("El precio de venta debe ser mayor que cero.")
        
        return price
    
    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        purchase_price = cleaned_data.get('purchase_price_usd')
        selling_price = cleaned_data.get('selling_price_usd')
        bulk_price = cleaned_data.get('bulk_price_usd')
        is_bulk_pricing = cleaned_data.get('is_bulk_pricing')
        bulk_min_quantity = cleaned_data.get('bulk_min_quantity')
        
        # Validar que precio de venta sea mayor que precio de compra
        if purchase_price and selling_price:
            if selling_price <= purchase_price:
                self.add_error('selling_price_usd', 
                    'El precio de venta debe ser mayor que el precio de compra.')
        
        # Validar precios al mayor
        if is_bulk_pricing:
            if not bulk_min_quantity or bulk_min_quantity <= 0:
                self.add_error('bulk_min_quantity', 
                    'La cantidad mínima es requerida para precios al mayor.')
            
            if not bulk_price or bulk_price <= 0:
                self.add_error('bulk_price_usd', 
                    'El precio al mayor es requerido.')
            
            if selling_price and bulk_price and bulk_price >= selling_price:
                self.add_error('bulk_price_usd', 
                    'El precio al mayor debe ser menor que el precio regular.')
        
        return cleaned_data


class CategoryForm(forms.ModelForm):
    """Formulario para categorías"""
    
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'description': forms.Textarea(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'rows': 3
            }),
        }


class InventoryAdjustmentForm(forms.ModelForm):
    """Formulario para ajustes de inventario"""
    
    class Meta:
        model = InventoryAdjustment
        fields = ['product', 'adjustment_type', 'quantity', 'reason']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'adjustment_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-input', 
                'step': '0.001', 
                'min': '0.001'
            }),
            'reason': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar solo productos activos
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
    
    def clean_quantity(self):
        """Validar cantidad"""
        quantity = self.cleaned_data.get('quantity')
        adjustment_type = self.cleaned_data.get('adjustment_type')
        product = self.cleaned_data.get('product')
        
        if quantity <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")
        
        # Validar que no se quite más stock del disponible
        if adjustment_type == 'remove' and product:
            if quantity > product.stock:
                raise forms.ValidationError(
                    f"No se puede quitar más stock del disponible. "
                    f"Stock actual: {product.stock}"
                )
        
        return quantity
    
    def save(self, commit=True):
        adjustment = super().save(commit=False)
        adjustment.adjusted_by = self.user
        
        # Calcular nuevo stock
        product = adjustment.product
        adjustment.previous_stock = product.stock
        
        if adjustment.adjustment_type == 'add':
            new_stock = product.stock + adjustment.quantity
        elif adjustment.adjustment_type == 'remove':
            new_stock = product.stock - adjustment.quantity
        elif adjustment.adjustment_type == 'set':
            new_stock = adjustment.quantity
        
        adjustment.new_stock = new_stock
        
        if commit:
            with transaction.atomic():
                # Actualizar stock del producto
                product.stock = new_stock
                product.save()
                
                # Guardar ajuste
                adjustment.save()
        
        return adjustment


# FORMULARIOS PARA COMBOS (Pendiente - mantener por compatibilidad)

class ProductComboForm(forms.ModelForm):
    """Formulario para crear combos de productos - PENDIENTE"""
    
    class Meta:
        model = ProductCombo
        fields = ['name', 'description', 'combo_price_bs', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'combo_price_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }


class ComboItemForm(forms.ModelForm):
    """Formulario para ítems de combo - PENDIENTE"""
    
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
ComboItemFormset = forms.inlineformset_factory(
    ProductCombo, 
    ComboItem,
    form=ComboItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)