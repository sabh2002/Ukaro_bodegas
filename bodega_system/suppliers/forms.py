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
            'supplier': forms.Select(attrs={'class': 'po-input'}),
            'status': forms.Select(attrs={'class': 'po-input'}),
            'notes': forms.Textarea(attrs={'class': 'po-input', 'rows': 3}),
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
    
    # Campos adicionales para crear productos nuevos
    is_new_product = forms.BooleanField(
        required=False,
        label="¿Es un producto nuevo?",
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    new_product_name = forms.CharField(
        required=False,
        max_length=200,
        label="Nombre del producto",
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    new_product_barcode = forms.CharField(
        required=False,
        max_length=50,
        label="Código de barras",
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    new_product_category = forms.ModelChoiceField(
        required=False,
        queryset=None,
        label="Categoría",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    new_product_unit_type = forms.ChoiceField(
        required=False,
        choices=Product.UNIT_TYPES,
        label="Tipo de unidad",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    new_product_selling_price_usd = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        label="Precio de venta (USD)",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'})
    )
    new_product_min_stock = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=3,
        initial=5,
        label="Stock mínimo",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001'})
    )
    
    class Meta:
        model = SupplierOrderItem
        fields = ['product', 'quantity', 'price_usd']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'price_usd': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo productos activos
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        
        # Cargar categorías para productos nuevos
        from inventory.models import Category
        self.fields['new_product_category'].queryset = Category.objects.all().order_by('name')
    
    def clean_quantity(self):
        """Validar cantidad"""
        quantity = self.cleaned_data.get('quantity')
        
        if quantity <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")
        
        return quantity
    
    def clean_price_usd(self):
        """Validar precio en USD"""
        price = self.cleaned_data.get('price_usd')
        
        if price <= 0:
            raise forms.ValidationError("El precio debe ser mayor a cero.")
        
        return price
    
    def clean(self):
        """Validación personalizada para productos nuevos"""
        cleaned_data = super().clean()
        is_new_product = cleaned_data.get('is_new_product')
        product = cleaned_data.get('product')
        
        if is_new_product:
            # Validar campos requeridos para productos nuevos
            required_fields = ['new_product_name', 'new_product_barcode', 'new_product_category', 'new_product_selling_price_usd']
            
            for field in required_fields:
                if not cleaned_data.get(field):
                    field_label = self.fields[field].label
                    raise forms.ValidationError(f'{field_label} es requerido para productos nuevos.')
            
            # Validar que el código de barras no exista
            barcode = cleaned_data.get('new_product_barcode')
            if barcode and Product.objects.filter(barcode=barcode).exists():
                raise forms.ValidationError(f'Ya existe un producto con el código de barras {barcode}.')
            
            # Limpiar el campo product si es nuevo producto
            cleaned_data['product'] = None
            
        elif not product:
            # Si no es producto nuevo, debe seleccionar uno existente
            raise forms.ValidationError('Debe seleccionar un producto existente o marcar como producto nuevo.')
        
        return cleaned_data

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