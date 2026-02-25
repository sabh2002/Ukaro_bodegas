# accounts/tests.py - Tests para modelos y permisos de usuarios

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test import RequestFactory

from utils.decorators import (
    is_admin, is_employee, is_admin_or_employee,
    admin_required, employee_or_admin_required, sales_access_required
)
from factories import AdminUserFactory, EmployeeUserFactory, UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


# ============================================================================
# TESTS DE MODELO USER
# ============================================================================

class TestUserCreacion:
    """Tests para creación del modelo User"""

    def test_crear_usuario_basico(self):
        """Crear usuario sin roles especiales"""
        user = User.objects.create_user(
            username='usuario1',
            email='usuario1@test.com',
            password='password123'
        )

        assert user.username == 'usuario1'
        assert user.email == 'usuario1@test.com'
        assert user.is_admin is False
        assert user.is_employee is False
        assert user.is_superuser is False

    def test_crear_usuario_admin(self):
        """Crear usuario con rol de administrador"""
        user = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='password123',
            is_admin=True
        )

        assert user.is_admin is True
        assert user.is_employee is False
        assert user.is_superuser is False

    def test_crear_usuario_employee(self):
        """Crear usuario con rol de empleado"""
        user = User.objects.create_user(
            username='empleado1',
            email='empleado@test.com',
            password='password123',
            is_employee=True
        )

        assert user.is_admin is False
        assert user.is_employee is True
        assert user.is_superuser is False

    def test_crear_superuser(self):
        """Crear superusuario"""
        user = User.objects.create_superuser(
            username='superadmin',
            email='super@test.com',
            password='password123'
        )

        assert user.is_superuser is True
        assert user.is_staff is True

    def test_usuario_string_representation(self):
        """Test del método __str__"""
        user = User.objects.create_user(
            username='testuser',
            password='password123'
        )

        assert str(user) == 'testuser'


class TestUserRoles:
    """Tests para propiedad role del usuario"""

    def test_role_superadmin(self):
        """Superusuario debe tener rol 'Superadmin'"""
        user = User.objects.create_superuser(
            username='super',
            password='password123'
        )

        assert user.role == 'Superadmin'

    def test_role_administrador(self):
        """Usuario con is_admin=True debe tener rol 'Administrador'"""
        user = User.objects.create_user(
            username='admin',
            password='password123',
            is_admin=True
        )

        assert user.role == 'Administrador'

    def test_role_empleado(self):
        """Usuario con is_employee=True debe tener rol 'Empleado'"""
        user = User.objects.create_user(
            username='empleado',
            password='password123',
            is_employee=True
        )

        assert user.role == 'Empleado'

    def test_role_usuario_basico(self):
        """Usuario sin roles especiales debe tener rol 'Usuario'"""
        user = User.objects.create_user(
            username='usuario',
            password='password123'
        )

        assert user.role == 'Usuario'

    def test_admin_y_employee_priority(self):
        """Si usuario tiene ambos roles, admin tiene prioridad"""
        user = User.objects.create_user(
            username='multi',
            password='password123',
            is_admin=True,
            is_employee=True
        )

        # Admin tiene prioridad sobre empleado
        assert user.role == 'Administrador'


class TestUserFactories:
    """Tests para verificar que las factories funcionan correctamente"""

    def test_admin_user_factory(self):
        """AdminUserFactory debe crear usuario administrador"""
        admin = AdminUserFactory()

        assert admin.is_admin is True
        assert admin.is_superuser is False

    def test_employee_user_factory(self):
        """EmployeeUserFactory debe crear usuario empleado"""
        employee = EmployeeUserFactory()

        assert admin.is_employee is True
        assert employee.is_admin is False

    def test_user_factory(self):
        """UserFactory debe crear usuario básico"""
        user = UserFactory()

        assert user.is_admin is False
        assert user.is_employee is False


# ============================================================================
# TESTS DE FUNCIONES DE VERIFICACIÓN
# ============================================================================

class TestFuncionesVerificacion:
    """Tests para funciones is_admin, is_employee, is_admin_or_employee"""

    def test_is_admin_con_usuario_admin(self):
        """is_admin debe retornar True para usuarios administradores"""
        admin = AdminUserFactory()
        assert is_admin(admin) is True

    def test_is_admin_con_superuser(self):
        """is_admin debe retornar True para superusuarios"""
        superuser = User.objects.create_superuser(
            username='super',
            password='password123'
        )
        assert is_admin(superuser) is True

    def test_is_admin_con_usuario_basico(self):
        """is_admin debe retornar False para usuarios sin rol de admin"""
        user = UserFactory()
        assert is_admin(user) is False

    def test_is_admin_con_usuario_no_autenticado(self):
        """is_admin debe retornar False para usuarios no autenticados"""
        user = User()  # Usuario sin guardar (no autenticado)
        assert is_admin(user) is False

    def test_is_employee_con_empleado(self):
        """is_employee debe retornar True para empleados"""
        employee = EmployeeUserFactory()
        assert is_employee(employee) is True

    def test_is_employee_con_usuario_no_empleado(self):
        """is_employee debe retornar False para no empleados"""
        user = UserFactory()
        assert is_employee(user) is False

    def test_is_admin_or_employee_con_admin(self):
        """is_admin_or_employee debe retornar True para admin"""
        admin = AdminUserFactory()
        assert is_admin_or_employee(admin) is True

    def test_is_admin_or_employee_con_employee(self):
        """is_admin_or_employee debe retornar True para empleado"""
        employee = EmployeeUserFactory()
        assert is_admin_or_employee(employee) is True

    def test_is_admin_or_employee_con_superuser(self):
        """is_admin_or_employee debe retornar True para superuser"""
        superuser = User.objects.create_superuser(
            username='super',
            password='password123'
        )
        assert is_admin_or_employee(superuser) is True

    def test_is_admin_or_employee_con_usuario_basico(self):
        """is_admin_or_employee debe retornar False para usuario básico"""
        user = UserFactory()
        assert is_admin_or_employee(user) is False


# ============================================================================
# TESTS DE DECORADORES DE PERMISOS
# ============================================================================

class TestDecoradoresPermisos:
    """Tests para decoradores de permisos"""

    def setup_method(self):
        """Setup para cada test - crear factory de requests"""
        self.factory = RequestFactory()

    def crear_vista_dummy(self):
        """Crear una vista dummy para testing"""
        def vista_dummy(request):
            return "Vista ejecutada"
        return vista_dummy

    def test_admin_required_permite_admin(self):
        """admin_required debe permitir acceso a administradores"""
        admin = AdminUserFactory()
        request = self.factory.get('/test/')
        request.user = admin

        vista = self.crear_vista_dummy()
        vista_decorada = admin_required(vista)

        resultado = vista_decorada(request)
        assert resultado == "Vista ejecutada"

    def test_admin_required_permite_superuser(self):
        """admin_required debe permitir acceso a superusuarios"""
        superuser = User.objects.create_superuser(
            username='super',
            password='password123'
        )
        request = self.factory.get('/test/')
        request.user = superuser

        vista = self.crear_vista_dummy()
        vista_decorada = admin_required(vista)

        resultado = vista_decorada(request)
        assert resultado == "Vista ejecutada"

    def test_admin_required_bloquea_empleado(self):
        """admin_required debe bloquear acceso a empleados"""
        employee = EmployeeUserFactory()
        request = self.factory.get('/test/')
        request.user = employee

        vista = self.crear_vista_dummy()
        vista_decorada = admin_required(vista)

        with pytest.raises(PermissionDenied, match="Solo los administradores"):
            vista_decorada(request)

    def test_admin_required_bloquea_usuario_basico(self):
        """admin_required debe bloquear acceso a usuarios básicos"""
        user = UserFactory()
        request = self.factory.get('/test/')
        request.user = user

        vista = self.crear_vista_dummy()
        vista_decorada = admin_required(vista)

        with pytest.raises(PermissionDenied):
            vista_decorada(request)

    def test_employee_or_admin_required_permite_admin(self):
        """employee_or_admin_required debe permitir acceso a admins"""
        admin = AdminUserFactory()
        request = self.factory.get('/test/')
        request.user = admin

        vista = self.crear_vista_dummy()
        vista_decorada = employee_or_admin_required(vista)

        resultado = vista_decorada(request)
        assert resultado == "Vista ejecutada"

    def test_employee_or_admin_required_permite_empleado(self):
        """employee_or_admin_required debe permitir acceso a empleados"""
        employee = EmployeeUserFactory()
        request = self.factory.get('/test/')
        request.user = employee

        vista = self.crear_vista_dummy()
        vista_decorada = employee_or_admin_required(vista)

        resultado = vista_decorada(request)
        assert resultado == "Vista ejecutada"

    def test_employee_or_admin_required_bloquea_usuario_basico(self):
        """employee_or_admin_required debe bloquear usuarios básicos"""
        user = UserFactory()
        request = self.factory.get('/test/')
        request.user = user

        vista = self.crear_vista_dummy()
        vista_decorada = employee_or_admin_required(vista)

        with pytest.raises(PermissionDenied, match="No tienes permisos"):
            vista_decorada(request)

    def test_sales_access_required_permite_admin(self):
        """sales_access_required debe permitir acceso a admins"""
        admin = AdminUserFactory()
        request = self.factory.get('/test/')
        request.user = admin

        vista = self.crear_vista_dummy()
        vista_decorada = sales_access_required(vista)

        resultado = vista_decorada(request)
        assert resultado == "Vista ejecutada"

    def test_sales_access_required_permite_empleado(self):
        """sales_access_required debe permitir acceso a empleados"""
        employee = EmployeeUserFactory()
        request = self.factory.get('/test/')
        request.user = employee

        vista = self.crear_vista_dummy()
        vista_decorada = sales_access_required(vista)

        resultado = vista_decorada(request)
        assert resultado == "Vista ejecutada"

    def test_sales_access_required_bloquea_usuario_basico(self):
        """sales_access_required debe bloquear usuarios sin permisos"""
        user = UserFactory()
        request = self.factory.get('/test/')
        request.user = user

        vista = self.crear_vista_dummy()
        vista_decorada = sales_access_required(vista)

        with pytest.raises(PermissionDenied, match="módulo de ventas"):
            vista_decorada(request)


# ============================================================================
# TESTS DE AUTENTICACIÓN
# ============================================================================

class TestAutenticacion:
    """Tests para funcionalidad de autenticación"""

    def test_usuario_puede_cambiar_password(self):
        """Usuario debe poder cambiar su contraseña"""
        user = UserFactory()
        old_password = user.password

        user.set_password('nueva_password_segura')
        user.save()

        # Password debe haber cambiado (hasheada)
        assert user.password != old_password
        assert user.check_password('nueva_password_segura') is True

    def test_usuario_password_es_hasheada(self):
        """Contraseña debe estar hasheada, no en texto plano"""
        user = User.objects.create_user(
            username='testuser',
            password='password123'
        )

        # La contraseña NO debe estar en texto plano
        assert user.password != 'password123'
        # Pero check_password debe funcionar
        assert user.check_password('password123') is True

    def test_check_password_con_password_incorrecta(self):
        """check_password debe retornar False con password incorrecta"""
        user = UserFactory()

        assert user.check_password('password_incorrecta') is False
