# accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import User
from .forms import UserForm, UserUpdateForm, ProfileForm
from django.contrib.auth import logout
from django.shortcuts import redirect
def is_admin(user):
    """Verifica si el usuario es administrador"""
    return user.is_admin or user.is_superuser

@login_required
def profile_view(request):
    """Vista para ver y actualizar el perfil del usuario"""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {
        'form': form
    })

@login_required
@user_passes_test(is_admin)
def user_list(request):
    """Vista para listar usuarios (solo admin)"""
    users = User.objects.all().order_by('username')
    return render(request, 'accounts/user_list.html', {
        'users': users
    })

@login_required
@user_passes_test(is_admin)
def user_create(request):
    """Vista para crear un nuevo usuario (solo admin)"""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado correctamente')
            return redirect('accounts:user_list')
    else:
        form = UserForm()
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Crear Usuario'
    })

@login_required
@user_passes_test(is_admin)
def user_update(request, pk):
    """Vista para actualizar un usuario (solo admin)"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario actualizado correctamente')
            return redirect('accounts:user_list')
    else:
        form = UserUpdateForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Editar Usuario',
        'user_obj': user
    })

@login_required
@user_passes_test(is_admin)
def user_delete(request, pk):
    """Vista para eliminar un usuario (solo admin)"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'Usuario eliminado correctamente')
        return redirect('accounts:user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {
        'user_obj': user
    })
def custom_logout(request):
    """Vista de logout personalizada que redirige inmediatamente"""
    logout(request)
    return redirect('/accounts/login/')