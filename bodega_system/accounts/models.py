from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Modelo de usuario personalizado con roles específicos para el sistema
    """
    is_admin = models.BooleanField(default=False)
    is_employee = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return self.username
    
    @property
    def role(self):
        if self.is_superuser:
            return 'Superadmin'
        elif self.is_admin:
            return 'Administrador'
        elif self.is_employee:
            return 'Empleado'
        else:
            return 'Usuario'