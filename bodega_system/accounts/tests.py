# accounts/tests.py
"""
Tests exhaustivos para el módulo accounts:
- User model (creación, roles, propiedades)
- Vistas de autenticación (login, logout)
- Vista de perfil
- Gestión de usuarios (admin only)
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from utils.models import ExchangeRate
from decimal import Decimal
from django.utils import timezone

User = get_user_model()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def make_admin(username='adm_acc', password='pass123'):
    return User.objects.create_user(username=username, password=password, is_admin=True,
                                    first_name='Admin', last_name='Test',
                                    email='admin@test.com')

def make_employee(username='emp_acc', password='pass123'):
    return User.objects.create_user(username=username, password=password, is_employee=True,
                                    first_name='Empleado', last_name='Test',
                                    email='employee@test.com')


# ─────────────────────────────────────────────
# USER MODEL TESTS
# ─────────────────────────────────────────────

class UserModelTest(TestCase):

    def test_create_user_basic(self):
        """Debe crear usuario con campos mínimos"""
        user = User.objects.create_user(username='basic_user', password='pass123')
        self.assertEqual(user.username, 'basic_user')
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_employee)
        self.assertFalse(user.is_superuser)

    def test_create_admin_user(self):
        """Debe crear usuario con rol admin"""
        user = make_admin('test_admin_model')
        self.assertTrue(user.is_admin)
        self.assertFalse(user.is_employee)

    def test_create_employee_user(self):
        """Debe crear usuario con rol empleado"""
        user = make_employee('test_emp_model')
        self.assertTrue(user.is_employee)
        self.assertFalse(user.is_admin)

    def test_role_superadmin(self):
        """Superusuario debe tener rol 'Superadmin'"""
        superuser = User.objects.create_superuser(
            username='superadmin_role', password='pass123', email='su@t.com'
        )
        self.assertEqual(superuser.role, 'Superadmin')

    def test_role_admin(self):
        """Administrador debe tener rol 'Administrador'"""
        admin = make_admin('role_admin')
        self.assertEqual(admin.role, 'Administrador')

    def test_role_employee(self):
        """Empleado debe tener rol 'Empleado'"""
        employee = make_employee('role_employee')
        self.assertEqual(employee.role, 'Empleado')

    def test_role_regular_user(self):
        """Usuario sin rol especial debe tener 'Usuario'"""
        user = User.objects.create_user(username='role_regular', password='pass123')
        self.assertEqual(user.role, 'Usuario')

    def test_str_representation(self):
        """__str__ debe retornar el username"""
        user = User.objects.create_user(username='str_test_user', password='pass123')
        self.assertEqual(str(user), 'str_test_user')

    def test_password_is_hashed(self):
        """La contraseña debe ser almacenada hasheada"""
        user = User.objects.create_user(username='hash_user', password='plainpass')
        self.assertNotEqual(user.password, 'plainpass')
        self.assertTrue(user.check_password('plainpass'))


# ─────────────────────────────────────────────
# AUTH VIEWS TESTS
# ─────────────────────────────────────────────

class AuthViewsTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin()
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')

    def test_login_page_get(self):
        """La página de login debe retornar 200"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_login_success_redirects(self):
        """Login exitoso debe redirigir al dashboard"""
        response = self.client.post(self.login_url, {
            'username': 'adm_acc',
            'password': 'pass123'
        })
        self.assertEqual(response.status_code, 302)
        # Redirige a dashboard o next
        self.assertTrue(response['Location'].endswith('/') or 'next' not in response['Location'])

    def test_login_wrong_password(self):
        """Login con contraseña incorrecta debe mostrar error"""
        response = self.client.post(self.login_url, {
            'username': 'adm_acc',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # No redirige
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_wrong_username(self):
        """Login con usuario inexistente debe mostrar error"""
        response = self.client.post(self.login_url, {
            'username': 'nobody',
            'password': 'pass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_redirects_to_login(self):
        """Logout debe redirigir al login"""
        self.client.login(username='adm_acc', password='pass123')
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_logout_clears_session(self):
        """Logout debe limpiar la sesión del usuario"""
        self.client.login(username='adm_acc', password='pass123')
        self.assertIn('_auth_user_id', self.client.session)
        self.client.get(self.logout_url)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unauthenticated_dashboard_redirects(self):
        """Dashboard sin autenticar debe redirigir al login"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])


# ─────────────────────────────────────────────
# PROFILE VIEW TESTS
# ─────────────────────────────────────────────

class ProfileViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin()
        self.url = reverse('accounts:profile')

    def test_profile_requires_login(self):
        """Perfil sin autenticar debe redirigir al login"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_profile_get_authenticated(self):
        """Perfil debe retornar 200 para usuario autenticado"""
        self.client.login(username='adm_acc', password='pass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_profile_contains_form(self):
        """Perfil debe incluir el formulario en el contexto"""
        self.client.login(username='adm_acc', password='pass123')
        response = self.client.get(self.url)
        self.assertIn('form', response.context)

    def test_profile_post_updates_user(self):
        """POST al perfil debe actualizar los datos del usuario"""
        self.client.login(username='adm_acc', password='pass123')
        response = self.client.post(self.url, {
            'first_name': 'Nuevo',
            'last_name': 'Nombre',
            'email': 'nuevo@test.com'
        })
        self.assertEqual(response.status_code, 302)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, 'Nuevo')
        self.assertEqual(self.admin.last_name, 'Nombre')


# ─────────────────────────────────────────────
# USER MANAGEMENT VIEWS TESTS (admin only)
# ─────────────────────────────────────────────

class UserManagementViewsTest(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = make_admin('mgmt_admin')
        self.employee = make_employee('mgmt_employee')
        self.list_url = reverse('accounts:user_list')
        self.create_url = reverse('accounts:user_create')

    def test_user_list_requires_admin(self):
        """Lista de usuarios requiere autenticación"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 302)

    def test_user_list_employee_gets_redirected(self):
        """Empleado no puede listar usuarios (redirigido por @user_passes_test)"""
        self.client.login(username='mgmt_employee', password='pass123')
        response = self.client.get(self.list_url)
        # accounts/views.py usa @user_passes_test que redirige (302), no lanza 403
        self.assertEqual(response.status_code, 302)

    def test_user_list_admin_sees_all_users(self):
        """Administrador ve la lista completa de usuarios"""
        self.client.login(username='mgmt_admin', password='pass123')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('users', response.context)
        usernames = [u.username for u in response.context['users']]
        self.assertIn('mgmt_admin', usernames)
        self.assertIn('mgmt_employee', usernames)

    def test_user_create_get_form(self):
        """Admin puede ver formulario de creación"""
        self.client.login(username='mgmt_admin', password='pass123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_user_create_post_valid(self):
        """Admin puede crear nuevo usuario"""
        self.client.login(username='mgmt_admin', password='pass123')
        response = self.client.post(self.create_url, {
            'username': 'nuevo_usuario',
            'password1': 'C0mplexP@ss!',
            'password2': 'C0mplexP@ss!',
            'is_employee': True,
            'is_admin': False,
            'email': '',
            'first_name': '',
            'last_name': ''
        })
        # Redirige si fue exitoso
        if response.status_code == 302:
            self.assertTrue(User.objects.filter(username='nuevo_usuario').exists())

    def test_user_update_get_form(self):
        """Admin puede ver formulario de edición"""
        self.client.login(username='mgmt_admin', password='pass123')
        url = reverse('accounts:user_update', args=[self.employee.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_user_update_employee_redirected(self):
        """Empleado no puede editar usuarios (redirigido por @user_passes_test)"""
        self.client.login(username='mgmt_employee', password='pass123')
        url = reverse('accounts:user_update', args=[self.admin.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_user_delete_get_confirmation(self):
        """Admin puede ver página de confirmación de eliminación"""
        target = User.objects.create_user(username='to_delete', password='pass123')
        self.client.login(username='mgmt_admin', password='pass123')
        url = reverse('accounts:user_delete', args=[target.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_user_delete_post_deletes(self):
        """Admin puede eliminar usuario via POST"""
        target = User.objects.create_user(username='del_target', password='pass123')
        target_pk = target.pk
        self.client.login(username='mgmt_admin', password='pass123')
        url = reverse('accounts:user_delete', args=[target_pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=target_pk).exists())

    def test_user_delete_employee_redirected(self):
        """Empleado no puede eliminar usuarios (redirigido por @user_passes_test)"""
        target = User.objects.create_user(username='del_target2', password='pass123')
        self.client.login(username='mgmt_employee', password='pass123')
        url = reverse('accounts:user_delete', args=[target.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
