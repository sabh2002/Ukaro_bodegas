# suppliers/forms.py

import logging
from decimal import Decimal, InvalidOperation
from django import forms
from django.forms import inlineformset_factory
from .models import Supplier, SupplierOrder, SupplierOrderItem, SupplierPayment
from inventory.models import Product

logger = logging.getLogger(__name__)

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
            # ✅ CAMBIAR: Permitir decimales en cantidad
            'quantity': forms.NumberInput(attrs={
                'class': 'form-input', 
                'min': '0.01',
                'step': '0.01'  # ← AGREGAR/MODIFICAR ESTO
            }),
            'price_usd': forms.NumberInput(attrs={
                'class': 'form-input', 
                'step': '0.01'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo productos activos
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        
        # ✅ SOLUCIÓN: Hacer el campo product no requerido
        # La validación real se hace en clean() que maneja productos nuevos
        self.fields['product'].required = False
        
        # Cargar categorías para productos nuevos
        from inventory.models import Category
        self.fields['new_product_category'].queryset = Category.objects.all().order_by('name')
    
    def clean_quantity(self):
        """Validar cantidad como decimal"""
        quantity = self.cleaned_data.get('quantity')

        if quantity is None:
            raise forms.ValidationError("La cantidad es requerida.")

        try:
            if isinstance(quantity, str):
                quantity = quantity.replace(',', '.')

            quantity_decimal = Decimal(str(quantity))

            # Validar que sea positivo
            if quantity_decimal <= 0:
                raise forms.ValidationError("La cantidad debe ser mayor a cero.")

            # Validar cantidad máxima
            if quantity_decimal > Decimal('100000'):
                raise forms.ValidationError(
                    "La cantidad no puede exceder 100,000 unidades. "
                    "Para cantidades mayores, cree múltiples órdenes."
                )

            # Validar máximo 2 decimales
            if quantity_decimal.as_tuple().exponent < -2:
                raise forms.ValidationError("La cantidad no puede tener más de 2 decimales.")

            return quantity_decimal

        except (InvalidOperation, ValueError):
            raise forms.ValidationError("La cantidad debe ser un número válido.")
    
    def clean_price_usd(self):
        """Validar precio en USD"""
        price = self.cleaned_data.get('price_usd')

        if price is None:
            raise forms.ValidationError("El precio es requerido.")

        try:
            if isinstance(price, str):
                price = price.replace(',', '.')

            price_decimal = Decimal(str(price))

            # Validar que sea positivo
            if price_decimal <= 0:
                raise forms.ValidationError("El precio debe ser mayor a cero.")

            # Validar precio máximo
            if price_decimal > Decimal('1000000'):
                raise forms.ValidationError(
                    "El precio no puede exceder $1,000,000 USD. "
                    "Verifique el precio ingresado."
                )

            return price_decimal

        except (InvalidOperation, ValueError):
            raise forms.ValidationError("El precio debe ser un número válido.")
        
    def clean(self):
        """Validación personalizada para productos nuevos"""
        cleaned_data = super().clean()
        is_new_product = cleaned_data.get('is_new_product')
        product = cleaned_data.get('product')

        logger.debug("Validating order item form", extra={
            'is_new_product': is_new_product,
            'has_product': product is not None,
        })

        if is_new_product:
            # Validar campos requeridos para productos nuevos
            required_fields = ['new_product_name', 'new_product_barcode', 'new_product_category', 'new_product_selling_price_usd']
            missing_fields = []

            for field in required_fields:
                if not cleaned_data.get(field):
                    missing_fields.append(field)

            if missing_fields:
                field_labels = [self.fields[field].label for field in missing_fields]
                logger.warning("New product validation failed: missing fields", extra={
                    'missing_fields': missing_fields,
                })
                raise forms.ValidationError(f'Campos requeridos para productos nuevos: {", ".join(field_labels)}.')

            # Validar que el código de barras no exista
            barcode = cleaned_data.get('new_product_barcode')
            if barcode and Product.objects.filter(barcode=barcode).exists():
                logger.warning("Duplicate barcode detected", extra={'barcode': barcode})
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


class SupplierPaymentForm(forms.ModelForm):
    """Formulario para registrar pagos a proveedores"""

    class Meta:
        model = SupplierPayment
        fields = ['amount_usd', 'payment_date', 'payment_method', 'reference', 'notes']
        widgets = {
            'amount_usd': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01'
            }),
            'payment_date': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Configurar fecha inicial como ahora
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['payment_date'].initial = timezone.now()

    def clean_amount_usd(self):
        """Validar que el monto sea positivo y no exceda el saldo pendiente"""
        amount = self.cleaned_data.get('amount_usd')

        if amount is None:
            raise forms.ValidationError("El monto es requerido.")

        if amount <= 0:
            raise forms.ValidationError("El monto debe ser mayor a cero.")

        # Validar que no exceda el saldo pendiente
        if self.order:
            outstanding = self.order.outstanding_balance_usd
            if amount > outstanding:
                raise forms.ValidationError(
                    f"El monto (${amount}) excede el saldo pendiente (${outstanding}). "
                    "Verifique el monto ingresado."
                )

        return amount

    def save(self, commit=True):
        payment = super().save(commit=False)

        if self.order:
            payment.order = self.order

        if self.user:
            payment.created_by = self.user

        if commit:
            payment.save()

        return payment