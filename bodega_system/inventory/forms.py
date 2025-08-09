# inventory/forms.py - Formulario de ajuste corregido

from django import forms
from decimal import Decimal, InvalidOperation
from django.db import transaction
from .models import Category, Product, InventoryAdjustment, ProductCombo, ComboItem

class InventoryAdjustmentForm(forms.ModelForm):
    """Formulario para ajustes de inventario"""
    
    class Meta:
        model = InventoryAdjustment
        fields = ['product', 'adjustment_type', 'quantity', 'reason']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'adjustment_type': forms.Select(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.001',
                'min': '0.001'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Solo productos activos
        self.fields['product'].queryset = Product.objects.filter(is_active=True).order_by('name')
    
    def clean_quantity(self):
        """Validar que la cantidad sea un decimal válido"""
        quantity = self.cleaned_data.get('quantity')
        
        if quantity is None:
            raise forms.ValidationError("La cantidad es requerida.")
        
        try:
            # Asegurar que es un Decimal válido
            quantity_decimal = Decimal(str(quantity))
            
            if quantity_decimal <= 0:
                raise forms.ValidationError("La cantidad debe ser mayor que 0.")
            
            return quantity_decimal
            
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Ingrese una cantidad válida.")
    
    def clean(self):
        """Validación general del formulario"""
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        adjustment_type = cleaned_data.get('adjustment_type')
        quantity = cleaned_data.get('quantity')
        
        if product and adjustment_type and quantity:
            # Verificar stock suficiente para remover
            if adjustment_type == 'remove' and product.stock < quantity:
                raise forms.ValidationError(
                    f"No hay suficiente stock para remover {quantity} {product.unit_display}. "
                    f"Stock actual: {product.stock} {product.unit_display}"
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Guardar el ajuste y actualizar el stock del producto"""
        if not self.user:
            raise forms.ValidationError("Usuario requerido para el ajuste.")
        
        adjustment = super().save(commit=False)
        adjustment.adjusted_by = self.user
        
        product = adjustment.product
        quantity = adjustment.quantity
        adjustment_type = adjustment.adjustment_type
        
        # Guardar stock previo
        adjustment.previous_stock = product.stock
        
        # Calcular nuevo stock
        if adjustment_type == 'add':
            new_stock = product.stock + quantity
        elif adjustment_type == 'remove':
            new_stock = product.stock - quantity
            if new_stock < 0:
                raise forms.ValidationError("El stock no puede ser negativo.")
        elif adjustment_type == 'set':
            new_stock = quantity
        
        adjustment.new_stock = new_stock
        
        if commit:
            with transaction.atomic():
                # Actualizar stock del producto
                product.stock = new_stock
                product.save()
                
                # Guardar ajuste
                adjustment.save()
        
        return adjustment


# Resto de formularios (ProductForm, CategoryForm, etc.) sin cambios significativos
class ProductForm(forms.ModelForm):
    """Formulario para productos"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'barcode', 'category', 'unit_type', 'description', 'image',
            'purchase_price_bs', 'selling_price_bs', 'min_stock', 'is_active',
            'is_bulk_pricing', 'bulk_min_quantity', 'bulk_price_bs'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'category': forms.Select(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'unit_type': forms.Select(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'description': forms.Textarea(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'rows': 3
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md'
            }),
            'purchase_price_bs': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.01'
            }),
            'selling_price_bs': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.01'
            }),
            'min_stock': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.001',
                'min': '0'
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
                'min': '0'
            }),
            'bulk_price_bs': forms.NumberInput(attrs={
                'class': 'shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md',
                'step': '0.01'
            }),
        }

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
ComboItemFormset = forms.inlineformset_factory(
    ProductCombo, 
    ComboItem,
    form=ComboItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)