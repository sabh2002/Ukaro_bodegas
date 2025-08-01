# inventory/forms.py

from django import forms
from .models import Category, Product, InventoryAdjustment

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
    """Formulario para productos"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'barcode', 'category', 'description', 'image',
            'purchase_price_bs', 'selling_price_bs', 'min_stock', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'barcode': forms.TextInput(attrs={'class': 'form-input'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'purchase_price_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'selling_price_bs': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-input'}),
        }
    
    def clean_barcode(self):
        """Validar código de barras único"""
        barcode = self.cleaned_data.get('barcode')
        instance = getattr(self, 'instance', None)
        
        # Verificar si existe otro producto con el mismo código de barras
        if Product.objects.filter(barcode=barcode).exclude(pk=instance.pk if instance.pk else None).exists():
            raise forms.ValidationError("Ya existe un producto con este código de barras.")
        
        return barcode
    
    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        purchase_price = cleaned_data.get('purchase_price_bs')
        selling_price = cleaned_data.get('selling_price_bs')
        
        # Validar que el precio de venta sea mayor al precio de compra
        if purchase_price and selling_price and selling_price < purchase_price:
            self.add_error('selling_price_bs', "El precio de venta debe ser mayor o igual al precio de compra.")
        
        return cleaned_data

class InventoryAdjustmentForm(forms.ModelForm):
    """Formulario para ajustes de inventario"""
    
    class Meta:
        model = InventoryAdjustment
        fields = ['product', 'adjustment_type', 'quantity', 'reason']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'adjustment_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
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
    
    def save(self, commit=True):
        """Guardar ajuste de inventario y actualizar stock del producto"""
        adjustment = super().save(commit=False)
        
        product = adjustment.product
        adjustment_type = adjustment.adjustment_type
        quantity = adjustment.quantity
        
        # Establecer usuario que realiza el ajuste
        adjustment.adjusted_by = self.user
        
        # Guardar stock previo
        adjustment.previous_stock = product.stock
        
        # Actualizar stock según tipo de ajuste
        if adjustment_type == 'add':
            product.stock += quantity
        elif adjustment_type == 'remove':
            # Validar que haya suficiente stock
            if product.stock < quantity:
                raise forms.ValidationError(f"Stock insuficiente. Disponible: {product.stock}, Solicitado: {quantity}")
            product.stock -= quantity
        elif adjustment_type == 'set':
            product.stock = quantity
        
        # Guardar nuevo stock
        adjustment.new_stock = product.stock
        
        if commit:
            product.save()
            adjustment.save()
        
        return adjustment