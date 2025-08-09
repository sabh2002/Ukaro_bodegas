# utils/middleware.py - MIDDLEWARE SIMPLIFICADO SIN IMPORTACIONES CIRCULARES

from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.http import HttpResponseForbidden
import logging

logger = logging.getLogger(__name__)

class PermissionDeniedMiddleware:
    """
    Middleware para manejar excepciones de PermissionDenied de manera personalizada
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Procesa excepciones de PermissionDenied y las maneja de manera personalizada
        """
        if isinstance(exception, PermissionDenied):
            # Log del intento de acceso no autorizado
            logger.warning(
                f"Acceso denegado para usuario {request.user.username if request.user.is_authenticated else 'Anónimo'} "
                f"en la URL: {request.path} "
                f"Método: {request.method} "
                f"IP: {self.get_client_ip(request)}"
            )
            
            # Renderizar página personalizada de error 403
            context = {
                'user': request.user,
                'exception_message': str(exception),
                'requested_path': request.path,
                'user_role': self.get_user_role(request.user) if request.user.is_authenticated else 'No autenticado'
            }
            
            return render(request, '403.html', context, status=403)
        
        # Si no es PermissionDenied, dejar que Django maneje la excepción
        return None
    
    def get_client_ip(self, request):
        """Obtiene la IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_user_role(self, user):
        """Obtiene el rol del usuario sin importaciones circulares"""
        if hasattr(user, 'role'):
            return user.role
        elif getattr(user, 'is_superuser', False):
            return 'Superadmin'
        elif getattr(user, 'is_admin', False):
            return 'Administrador'
        elif getattr(user, 'is_employee', False):
            return 'Empleado'
        else:
            return 'Usuario'

class RoleBasedAccessMiddleware:
    """
    Middleware para logging y auditoría de accesos por roles
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs que requieren permisos especiales
        self.admin_only_paths = [
            '/inventory/',
            '/suppliers/',
            '/finances/',
            '/admin/',
            '/accounts/users/',
        ]
        
        self.employee_access_paths = [
            '/sales/',
            '/customers/',
        ]

    def __call__(self, request):
        # Antes de procesar la vista
        self.log_access_attempt(request)
        
        response = self.get_response(request)
        
        # Después de procesar la vista
        return response

    def log_access_attempt(self, request):
        """
        Log de intentos de acceso para auditoría
        """
        if request.user.is_authenticated:
            user_role = self.get_user_role(request.user)
            path = request.path
            
            # Determinar si la ruta requiere permisos especiales
            requires_admin = any(path.startswith(admin_path) for admin_path in self.admin_only_paths)
            
            is_admin = getattr(request.user, 'is_admin', False) or getattr(request.user, 'is_superuser', False)
            
            if requires_admin and not is_admin:
                logger.info(
                    f"Intento de acceso de {user_role} a ruta de admin: "
                    f"Usuario: {request.user.username} "
                    f"Ruta: {path} "
                    f"IP: {self.get_client_ip(request)}"
                )
            
            # Log de accesos exitosos para empleados
            elif any(path.startswith(emp_path) for emp_path in self.employee_access_paths):
                logger.debug(
                    f"Acceso de {user_role}: "
                    f"Usuario: {request.user.username} "
                    f"Ruta: {path}"
                )
    
    def get_client_ip(self, request):
        """Obtiene la IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_user_role(self, user):
        """Obtiene el rol del usuario sin importaciones circulares"""
        if hasattr(user, 'role'):
            return user.role
        elif getattr(user, 'is_superuser', False):
            return 'Superadmin'
        elif getattr(user, 'is_admin', False):
            return 'Administrador'
        elif getattr(user, 'is_employee', False):
            return 'Empleado'
        else:
            return 'Usuario'

# Handler personalizado para errores 403
def custom_permission_denied_view(request, exception=None):
    """
    Vista personalizada para errores 403 - Permission Denied
    """
    context = {
        'user': request.user,
        'exception_message': str(exception) if exception else 'Acceso denegado',
        'requested_path': request.path,
        'user_role': request.user.role if hasattr(request.user, 'role') and request.user.is_authenticated else 'No autenticado'
    }
    
    return render(request, '403.html', context, status=403)