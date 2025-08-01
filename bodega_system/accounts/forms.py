# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserForm(UserCreationForm):
    """Formulario para crear usuarios"""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 
                  'is_admin', 'is_employee', 'password1', 'password2']
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer algunos campos opcionales
        self.fields['email'].required = False
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

class UserUpdateForm(forms.ModelForm):
    """Formulario para actualizar usuarios (sin cambiar password)"""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_admin', 'is_employee', 'is_active']
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }

class ProfileForm(forms.ModelForm):
    """Formulario para que el usuario edite su propio perfil"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }