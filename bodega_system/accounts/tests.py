from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model

from accounts.forms import UserForm, UserUpdateForm, ProfileForm

User = get_user_model()


class UserFactoryMixin:
    """Mixin providing helper methods for creating users with different roles."""

    def create_superadmin(self, **kwargs):
        defaults = {
            'username': 'superadmin',
            'password': 'TestPass123!',
            'first_name': 'Super',
            'last_name': 'Admin',
            'email': 'superadmin@test.com',
            'is_superuser': True,
            'is_staff': True,
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        return User.objects.create_user(password=password, **defaults)

    def create_admin(self, **kwargs):
        defaults = {
            'username': 'admin',
            'password': 'TestPass123!',
            'first_name': 'Admin',
            'last_name': 'User',
            'email': 'admin@test.com',
            'is_admin': True,
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        return User.objects.create_user(password=password, **defaults)

    def create_employee(self, **kwargs):
        defaults = {
            'username': 'employee',
            'password': 'TestPass123!',
            'first_name': 'Employee',
            'last_name': 'User',
            'email': 'employee@test.com',
            'is_employee': True,
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        return User.objects.create_user(password=password, **defaults)

    def create_normal_user(self, **kwargs):
        defaults = {
            'username': 'normaluser',
            'password': 'TestPass123!',
            'first_name': 'Normal',
            'last_name': 'User',
            'email': 'normal@test.com',
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        return User.objects.create_user(password=password, **defaults)


# ---------------------------------------------------------------------------
# MODEL TESTS
# ---------------------------------------------------------------------------

class UserModelTests(UserFactoryMixin, TestCase):
    """Tests for the custom User model, including the role property."""

    def test_str_returns_username(self):
        user = self.create_normal_user(username='johndoe')
        self.assertEqual(str(user), 'johndoe')

    def test_role_superadmin(self):
        user = self.create_superadmin()
        self.assertEqual(user.role, 'Superadmin')

    def test_role_administrador(self):
        user = self.create_admin()
        self.assertEqual(user.role, 'Administrador')

    def test_role_empleado(self):
        user = self.create_employee()
        self.assertEqual(user.role, 'Empleado')

    def test_role_usuario(self):
        user = self.create_normal_user()
        self.assertEqual(user.role, 'Usuario')

    def test_superuser_flag_takes_priority_over_is_admin(self):
        """When both is_superuser and is_admin are True, role is Superadmin."""
        user = self.create_superadmin(is_admin=True)
        self.assertEqual(user.role, 'Superadmin')

    def test_superuser_flag_takes_priority_over_is_employee(self):
        """When both is_superuser and is_employee are True, role is Superadmin."""
        user = self.create_superadmin(is_employee=True)
        self.assertEqual(user.role, 'Superadmin')

    def test_is_admin_takes_priority_over_is_employee(self):
        """When both is_admin and is_employee are True, role is Administrador."""
        user = self.create_admin(is_employee=True)
        self.assertEqual(user.role, 'Administrador')

    def test_default_flags_are_false(self):
        user = User.objects.create_user(username='default', password='TestPass123!')
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_employee)
        self.assertFalse(user.is_superuser)

    def test_verbose_name(self):
        self.assertEqual(User._meta.verbose_name, 'Usuario')

    def test_verbose_name_plural(self):
        self.assertEqual(User._meta.verbose_name_plural, 'Usuarios')


# ---------------------------------------------------------------------------
# FORM TESTS
# ---------------------------------------------------------------------------

class UserFormTests(TestCase):
    """Tests for the UserForm (user creation form)."""

    def get_valid_data(self, **overrides):
        data = {
            'username': 'newuser',
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'new@test.com',
            'password1': 'Str0ngP@ss!',
            'password2': 'Str0ngP@ss!',
            'is_admin': False,
            'is_employee': False,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = UserForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form_saves_user(self):
        form = UserForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.first_name, 'First')
        self.assertEqual(user.last_name, 'Last')

    def test_first_name_required(self):
        form = UserForm(data=self.get_valid_data(first_name=''))
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_last_name_required(self):
        form = UserForm(data=self.get_valid_data(last_name=''))
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)

    def test_email_optional(self):
        form = UserForm(data=self.get_valid_data(email=''))
        self.assertTrue(form.is_valid(), form.errors)

    def test_username_required(self):
        form = UserForm(data=self.get_valid_data(username=''))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_password_mismatch(self):
        form = UserForm(data=self.get_valid_data(password2='DifferentPass!'))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_missing_password1(self):
        form = UserForm(data=self.get_valid_data(password1=''))
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_missing_password2(self):
        form = UserForm(data=self.get_valid_data(password2=''))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_duplicate_username(self):
        User.objects.create_user(username='newuser', password='TestPass123!')
        form = UserForm(data=self.get_valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_can_create_admin_user(self):
        form = UserForm(data=self.get_valid_data(is_admin=True))
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.is_admin)

    def test_can_create_employee_user(self):
        form = UserForm(data=self.get_valid_data(is_employee=True))
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.is_employee)

    def test_form_fields_match_expected(self):
        form = UserForm()
        expected_fields = [
            'username', 'first_name', 'last_name', 'email',
            'is_admin', 'is_employee', 'password1', 'password2',
        ]
        self.assertEqual(list(form.fields.keys()), expected_fields)

    def test_common_password_rejected(self):
        form = UserForm(data=self.get_valid_data(
            password1='password123', password2='password123'
        ))
        self.assertFalse(form.is_valid())

    def test_numeric_password_rejected(self):
        form = UserForm(data=self.get_valid_data(
            password1='12345678', password2='12345678'
        ))
        self.assertFalse(form.is_valid())

    def test_short_password_rejected(self):
        form = UserForm(data=self.get_valid_data(
            password1='Ab1!', password2='Ab1!'
        ))
        self.assertFalse(form.is_valid())

    def test_widget_classes(self):
        form = UserForm()
        self.assertIn('form-input', form.fields['username'].widget.attrs.get('class', ''))
        self.assertIn('form-input', form.fields['first_name'].widget.attrs.get('class', ''))
        self.assertIn('form-input', form.fields['last_name'].widget.attrs.get('class', ''))
        self.assertIn('form-input', form.fields['email'].widget.attrs.get('class', ''))


class UserUpdateFormTests(UserFactoryMixin, TestCase):
    """Tests for the UserUpdateForm (edit user, no password change)."""

    def setUp(self):
        self.user = self.create_normal_user()

    def test_valid_update(self):
        form = UserUpdateForm(
            data={
                'username': 'normaluser',
                'first_name': 'Updated',
                'last_name': 'Name',
                'email': 'updated@test.com',
                'is_admin': False,
                'is_employee': False,
                'is_active': True,
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.first_name, 'Updated')

    def test_can_deactivate_user(self):
        form = UserUpdateForm(
            data={
                'username': 'normaluser',
                'first_name': 'Normal',
                'last_name': 'User',
                'email': 'normal@test.com',
                'is_admin': False,
                'is_employee': False,
                'is_active': False,
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertFalse(user.is_active)

    def test_can_promote_to_admin(self):
        form = UserUpdateForm(
            data={
                'username': 'normaluser',
                'first_name': 'Normal',
                'last_name': 'User',
                'email': '',
                'is_admin': True,
                'is_employee': False,
                'is_active': True,
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.is_admin)
        self.assertEqual(user.role, 'Administrador')

    def test_can_promote_to_employee(self):
        form = UserUpdateForm(
            data={
                'username': 'normaluser',
                'first_name': 'Normal',
                'last_name': 'User',
                'email': '',
                'is_admin': False,
                'is_employee': True,
                'is_active': True,
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.is_employee)

    def test_form_fields_match_expected(self):
        form = UserUpdateForm()
        expected_fields = [
            'username', 'first_name', 'last_name', 'email',
            'is_admin', 'is_employee', 'is_active',
        ]
        self.assertEqual(list(form.fields.keys()), expected_fields)

    def test_no_password_field(self):
        form = UserUpdateForm()
        self.assertNotIn('password1', form.fields)
        self.assertNotIn('password2', form.fields)
        self.assertNotIn('password', form.fields)

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='taken', password='TestPass123!')
        form = UserUpdateForm(
            data={
                'username': 'taken',
                'first_name': 'Normal',
                'last_name': 'User',
                'email': '',
                'is_admin': False,
                'is_employee': False,
                'is_active': True,
            },
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_same_username_accepted_for_same_user(self):
        form = UserUpdateForm(
            data={
                'username': 'normaluser',
                'first_name': 'Normal',
                'last_name': 'User',
                'email': '',
                'is_admin': False,
                'is_employee': False,
                'is_active': True,
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)


class ProfileFormTests(UserFactoryMixin, TestCase):
    """Tests for the ProfileForm (self-service profile editing)."""

    def setUp(self):
        self.user = self.create_normal_user()

    def test_valid_profile_update(self):
        form = ProfileForm(
            data={
                'first_name': 'NewFirst',
                'last_name': 'NewLast',
                'email': 'newemail@test.com',
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.first_name, 'NewFirst')
        self.assertEqual(user.last_name, 'NewLast')
        self.assertEqual(user.email, 'newemail@test.com')

    def test_email_optional_in_profile(self):
        form = ProfileForm(
            data={
                'first_name': 'NewFirst',
                'last_name': 'NewLast',
                'email': '',
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_profile_form_fields(self):
        form = ProfileForm()
        self.assertEqual(list(form.fields.keys()), ['first_name', 'last_name', 'email'])

    def test_profile_form_cannot_change_admin_flag(self):
        """ProfileForm does not expose is_admin, preventing privilege escalation."""
        self.assertNotIn('is_admin', ProfileForm().fields)

    def test_profile_form_cannot_change_employee_flag(self):
        """ProfileForm does not expose is_employee."""
        self.assertNotIn('is_employee', ProfileForm().fields)

    def test_profile_form_cannot_change_is_active(self):
        """ProfileForm does not expose is_active."""
        self.assertNotIn('is_active', ProfileForm().fields)

    def test_profile_form_cannot_change_username(self):
        """ProfileForm does not expose username."""
        self.assertNotIn('username', ProfileForm().fields)


# ---------------------------------------------------------------------------
# VIEW TESTS
# ---------------------------------------------------------------------------

class ViewTestBase(UserFactoryMixin, TestCase):
    """Base class for view tests providing login helpers."""

    LOGIN_URL = '/accounts/login/'

    def setUp(self):
        self.client = Client()
        self.superadmin = self.create_superadmin()
        self.admin = self.create_admin()
        self.employee = self.create_employee()
        self.normal_user = self.create_normal_user()

    def login_as(self, user, password='TestPass123!'):
        result = self.client.login(username=user.username, password=password)
        self.assertTrue(result, f'Login failed for {user.username}')

    def assert_redirects_to_login(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.startswith(self.LOGIN_URL),
            f'Expected redirect to {self.LOGIN_URL}, got {response.url}',
        )


class ProfileViewTests(ViewTestBase):
    """Tests for the profile view (login required, all authenticated users)."""

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assert_redirects_to_login(response)

    def test_normal_user_can_access_profile(self):
        self.login_as(self.normal_user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_employee_can_access_profile(self):
        self.login_as(self.employee)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_profile(self):
        self.login_as(self.admin)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_superadmin_can_access_profile(self):
        self.login_as(self.superadmin)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_get_renders_form(self):
        self.login_as(self.normal_user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], ProfileForm)

    def test_profile_form_prepopulated(self):
        self.login_as(self.normal_user)
        response = self.client.get(reverse('accounts:profile'))
        form = response.context['form']
        self.assertEqual(form.initial.get('first_name') or form.instance.first_name, 'Normal')

    def test_profile_post_updates_name(self):
        self.login_as(self.normal_user)
        response = self.client.post(
            reverse('accounts:profile'),
            data={
                'first_name': 'UpdatedFirst',
                'last_name': 'UpdatedLast',
                'email': 'updated@test.com',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.first_name, 'UpdatedFirst')
        self.assertEqual(self.normal_user.last_name, 'UpdatedLast')
        self.assertEqual(self.normal_user.email, 'updated@test.com')

    def test_profile_post_redirects_to_profile(self):
        self.login_as(self.normal_user)
        response = self.client.post(
            reverse('accounts:profile'),
            data={
                'first_name': 'UpdatedFirst',
                'last_name': 'UpdatedLast',
                'email': '',
            },
        )
        self.assertRedirects(response, reverse('accounts:profile'))

    def test_profile_post_shows_success_message(self):
        self.login_as(self.normal_user)
        response = self.client.post(
            reverse('accounts:profile'),
            data={
                'first_name': 'UpdatedFirst',
                'last_name': 'UpdatedLast',
                'email': '',
            },
            follow=True,
        )
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertIn('actualizado', str(messages_list[0]).lower())


class UserListViewTests(ViewTestBase):
    """Tests for the user list view (admin only)."""

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('accounts:user_list'))
        self.assert_redirects_to_login(response)

    def test_normal_user_denied(self):
        self.login_as(self.normal_user)
        response = self.client.get(reverse('accounts:user_list'))
        self.assert_redirects_to_login(response)

    def test_employee_denied(self):
        self.login_as(self.employee)
        response = self.client.get(reverse('accounts:user_list'))
        self.assert_redirects_to_login(response)

    def test_admin_can_access(self):
        self.login_as(self.admin)
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)

    def test_superadmin_can_access(self):
        self.login_as(self.superadmin)
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)

    def test_user_list_contains_all_users(self):
        self.login_as(self.admin)
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)
        users_in_context = response.context['users']
        self.assertEqual(users_in_context.count(), User.objects.count())

    def test_user_list_ordered_by_username(self):
        self.login_as(self.admin)
        response = self.client.get(reverse('accounts:user_list'))
        users = list(response.context['users'].values_list('username', flat=True))
        self.assertEqual(users, sorted(users))


class UserCreateViewTests(ViewTestBase):
    """Tests for the user creation view (admin only)."""

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('accounts:user_create'))
        self.assert_redirects_to_login(response)

    def test_normal_user_denied(self):
        self.login_as(self.normal_user)
        response = self.client.get(reverse('accounts:user_create'))
        self.assert_redirects_to_login(response)

    def test_employee_denied(self):
        self.login_as(self.employee)
        response = self.client.get(reverse('accounts:user_create'))
        self.assert_redirects_to_login(response)

    def test_admin_can_access_create_form(self):
        self.login_as(self.admin)
        response = self.client.get(reverse('accounts:user_create'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], UserForm)

    def test_superadmin_can_access_create_form(self):
        self.login_as(self.superadmin)
        response = self.client.get(reverse('accounts:user_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_form_context_has_title(self):
        self.login_as(self.admin)
        response = self.client.get(reverse('accounts:user_create'))
        self.assertEqual(response.context['title'], 'Crear Usuario')

    def test_admin_can_create_user(self):
        self.login_as(self.admin)
        initial_count = User.objects.count()
        response = self.client.post(
            reverse('accounts:user_create'),
            data={
                'username': 'brandnew',
                'first_name': 'Brand',
                'last_name': 'New',
                'email': 'brandnew@test.com',
                'password1': 'Str0ngP@ss!',
                'password2': 'Str0ngP@ss!',
                'is_admin': False,
                'is_employee': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), initial_count + 1)
        new_user = User.objects.get(username='brandnew')
        self.assertTrue(new_user.is_employee)
        self.assertFalse(new_user.is_admin)

    def test_create_user_redirects_to_user_list(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_create'),
            data={
                'username': 'brandnew',
                'first_name': 'Brand',
                'last_name': 'New',
                'email': '',
                'password1': 'Str0ngP@ss!',
                'password2': 'Str0ngP@ss!',
                'is_admin': False,
                'is_employee': False,
            },
        )
        self.assertRedirects(response, reverse('accounts:user_list'))

    def test_create_user_shows_success_message(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_create'),
            data={
                'username': 'brandnew',
                'first_name': 'Brand',
                'last_name': 'New',
                'email': '',
                'password1': 'Str0ngP@ss!',
                'password2': 'Str0ngP@ss!',
                'is_admin': False,
                'is_employee': False,
            },
            follow=True,
        )
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertIn('creado', str(messages_list[0]).lower())

    def test_create_user_invalid_data_renders_form(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_create'),
            data={
                'username': '',
                'first_name': '',
                'last_name': '',
                'email': '',
                'password1': '',
                'password2': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_valid())

    def test_employee_cannot_create_user_via_post(self):
        self.login_as(self.employee)
        initial_count = User.objects.count()
        response = self.client.post(
            reverse('accounts:user_create'),
            data={
                'username': 'hacked',
                'first_name': 'Hacked',
                'last_name': 'User',
                'email': '',
                'password1': 'Str0ngP@ss!',
                'password2': 'Str0ngP@ss!',
            },
        )
        self.assert_redirects_to_login(response)
        self.assertEqual(User.objects.count(), initial_count)


class UserUpdateViewTests(ViewTestBase):
    """Tests for the user update view (admin only)."""

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk})
        )
        self.assert_redirects_to_login(response)

    def test_normal_user_denied(self):
        self.login_as(self.normal_user)
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk})
        )
        self.assert_redirects_to_login(response)

    def test_employee_denied(self):
        self.login_as(self.employee)
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': self.normal_user.pk})
        )
        self.assert_redirects_to_login(response)

    def test_admin_can_access_update_form(self):
        self.login_as(self.admin)
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], UserUpdateForm)

    def test_superadmin_can_access_update_form(self):
        self.login_as(self.superadmin)
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_form_context_has_title(self):
        self.login_as(self.admin)
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.context['title'], 'Editar Usuario')

    def test_update_form_context_has_user_obj(self):
        self.login_as(self.admin)
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.context['user_obj'], self.employee)

    def test_admin_can_update_user(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk}),
            data={
                'username': 'employee',
                'first_name': 'UpdatedEmployee',
                'last_name': 'UpdatedLast',
                'email': 'emp_updated@test.com',
                'is_admin': False,
                'is_employee': True,
                'is_active': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.first_name, 'UpdatedEmployee')
        self.assertEqual(self.employee.email, 'emp_updated@test.com')

    def test_update_redirects_to_user_list(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk}),
            data={
                'username': 'employee',
                'first_name': 'Employee',
                'last_name': 'User',
                'email': '',
                'is_admin': False,
                'is_employee': True,
                'is_active': True,
            },
        )
        self.assertRedirects(response, reverse('accounts:user_list'))

    def test_update_shows_success_message(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk}),
            data={
                'username': 'employee',
                'first_name': 'Employee',
                'last_name': 'User',
                'email': '',
                'is_admin': False,
                'is_employee': True,
                'is_active': True,
            },
            follow=True,
        )
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertIn('actualizado', str(messages_list[0]).lower())

    def test_update_nonexistent_user_returns_404(self):
        self.login_as(self.admin)
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_employee_cannot_update_user_via_post(self):
        self.login_as(self.employee)
        original_name = self.normal_user.first_name
        response = self.client.post(
            reverse('accounts:user_update', kwargs={'pk': self.normal_user.pk}),
            data={
                'username': 'normaluser',
                'first_name': 'Hacked',
                'last_name': 'User',
                'email': '',
                'is_admin': True,
                'is_employee': False,
                'is_active': True,
            },
        )
        self.assert_redirects_to_login(response)
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.first_name, original_name)


class UserDeleteViewTests(ViewTestBase):
    """Tests for the user delete view (admin only, POST to confirm)."""

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(
            reverse('accounts:user_delete', kwargs={'pk': self.employee.pk})
        )
        self.assert_redirects_to_login(response)

    def test_normal_user_denied(self):
        self.login_as(self.normal_user)
        response = self.client.get(
            reverse('accounts:user_delete', kwargs={'pk': self.employee.pk})
        )
        self.assert_redirects_to_login(response)

    def test_employee_denied(self):
        self.login_as(self.employee)
        response = self.client.get(
            reverse('accounts:user_delete', kwargs={'pk': self.normal_user.pk})
        )
        self.assert_redirects_to_login(response)

    def test_admin_can_access_delete_confirmation(self):
        self.login_as(self.admin)
        response = self.client.get(
            reverse('accounts:user_delete', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user_obj'], self.employee)

    def test_superadmin_can_access_delete_confirmation(self):
        self.login_as(self.superadmin)
        response = self.client.get(
            reverse('accounts:user_delete', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_delete_user(self):
        self.login_as(self.admin)
        target_pk = self.normal_user.pk
        initial_count = User.objects.count()
        response = self.client.post(
            reverse('accounts:user_delete', kwargs={'pk': target_pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), initial_count - 1)
        self.assertFalse(User.objects.filter(pk=target_pk).exists())

    def test_delete_redirects_to_user_list(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_delete', kwargs={'pk': self.normal_user.pk})
        )
        self.assertRedirects(response, reverse('accounts:user_list'))

    def test_delete_shows_success_message(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_delete', kwargs={'pk': self.normal_user.pk}),
            follow=True,
        )
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertIn('eliminado', str(messages_list[0]).lower())

    def test_get_request_does_not_delete(self):
        self.login_as(self.admin)
        initial_count = User.objects.count()
        self.client.get(
            reverse('accounts:user_delete', kwargs={'pk': self.normal_user.pk})
        )
        self.assertEqual(User.objects.count(), initial_count)

    def test_delete_nonexistent_user_returns_404(self):
        self.login_as(self.admin)
        response = self.client.post(
            reverse('accounts:user_delete', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_employee_cannot_delete_user_via_post(self):
        self.login_as(self.employee)
        target_pk = self.normal_user.pk
        initial_count = User.objects.count()
        response = self.client.post(
            reverse('accounts:user_delete', kwargs={'pk': target_pk})
        )
        self.assert_redirects_to_login(response)
        self.assertEqual(User.objects.count(), initial_count)


class CustomLogoutViewTests(ViewTestBase):
    """Tests for the custom logout view."""

    def test_logout_redirects_to_login(self):
        self.login_as(self.normal_user)
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/accounts/login/')

    def test_logout_clears_session(self):
        self.login_as(self.normal_user)
        self.client.get(reverse('accounts:logout'))
        # After logout, accessing a protected view should redirect to login
        response = self.client.get(reverse('accounts:profile'))
        self.assert_redirects_to_login(response)

    def test_logout_works_for_admin(self):
        self.login_as(self.admin)
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/accounts/login/')

    def test_anonymous_logout_still_redirects(self):
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/accounts/login/')


class LoginViewTests(ViewTestBase):
    """Tests for the login view (Django's built-in LoginView)."""

    def test_login_page_accessible(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            reverse('accounts:login'),
            data={'username': 'normaluser', 'password': 'TestPass123!'},
        )
        # Successful login redirects (to LOGIN_REDIRECT_URL or 'next')
        self.assertEqual(response.status_code, 302)

    def test_login_with_invalid_credentials(self):
        response = self.client.post(
            reverse('accounts:login'),
            data={'username': 'normaluser', 'password': 'WrongPassword!'},
        )
        # Failed login re-renders the form (200)
        self.assertEqual(response.status_code, 200)

    def test_login_inactive_user_rejected(self):
        self.normal_user.is_active = False
        self.normal_user.save()
        response = self.client.post(
            reverse('accounts:login'),
            data={'username': 'normaluser', 'password': 'TestPass123!'},
        )
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# URL RESOLUTION TESTS
# ---------------------------------------------------------------------------

class URLTests(TestCase):
    """Tests that URL patterns resolve to the correct views."""

    def test_login_url_resolves(self):
        resolver = resolve('/accounts/login/')
        self.assertEqual(resolver.url_name, 'login')

    def test_logout_url_resolves(self):
        resolver = resolve('/accounts/logout/')
        self.assertEqual(resolver.url_name, 'logout')

    def test_profile_url_resolves(self):
        resolver = resolve('/accounts/profile/')
        self.assertEqual(resolver.url_name, 'profile')

    def test_user_list_url_resolves(self):
        resolver = resolve('/accounts/users/')
        self.assertEqual(resolver.url_name, 'user_list')

    def test_user_create_url_resolves(self):
        resolver = resolve('/accounts/users/add/')
        self.assertEqual(resolver.url_name, 'user_create')

    def test_user_update_url_resolves(self):
        resolver = resolve('/accounts/users/1/edit/')
        self.assertEqual(resolver.url_name, 'user_update')

    def test_user_delete_url_resolves(self):
        resolver = resolve('/accounts/users/1/delete/')
        self.assertEqual(resolver.url_name, 'user_delete')

    def test_url_namespace(self):
        url = reverse('accounts:login')
        self.assertEqual(url, '/accounts/login/')

    def test_user_update_url_accepts_int_pk(self):
        url = reverse('accounts:user_update', kwargs={'pk': 42})
        self.assertEqual(url, '/accounts/users/42/edit/')

    def test_user_delete_url_accepts_int_pk(self):
        url = reverse('accounts:user_delete', kwargs={'pk': 42})
        self.assertEqual(url, '/accounts/users/42/delete/')


# ---------------------------------------------------------------------------
# SECURITY TESTS
# ---------------------------------------------------------------------------

class SecurityTests(ViewTestBase):
    """Tests for CSRF protection and unauthorized access patterns."""

    def test_csrf_token_present_in_login_form(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_csrf_token_present_in_profile_form(self):
        self.login_as(self.normal_user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_csrf_token_present_in_user_create_form(self):
        self.login_as(self.admin)
        response = self.client.get(reverse('accounts:user_create'))
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_csrf_token_present_in_user_update_form(self):
        self.login_as(self.admin)
        response = self.client.get(
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk})
        )
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_csrf_token_present_in_user_delete_form(self):
        self.login_as(self.admin)
        response = self.client.get(
            reverse('accounts:user_delete', kwargs={'pk': self.employee.pk})
        )
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_post_without_csrf_token_rejected(self):
        """POST requests without CSRF token are rejected (403)."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='admin', password='TestPass123!')
        response = csrf_client.post(
            reverse('accounts:user_create'),
            data={
                'username': 'csrftest',
                'first_name': 'CSRF',
                'last_name': 'Test',
                'email': '',
                'password1': 'Str0ngP@ss!',
                'password2': 'Str0ngP@ss!',
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_profile_form_ignores_injected_is_admin(self):
        """Submitting is_admin via profile form does not escalate privileges."""
        self.login_as(self.normal_user)
        self.client.post(
            reverse('accounts:profile'),
            data={
                'first_name': 'Attacker',
                'last_name': 'Evil',
                'email': 'evil@test.com',
                'is_admin': True,
            },
        )
        self.normal_user.refresh_from_db()
        self.assertFalse(self.normal_user.is_admin)

    def test_profile_form_ignores_injected_is_superuser(self):
        """Submitting is_superuser via profile form does not escalate privileges."""
        self.login_as(self.normal_user)
        self.client.post(
            reverse('accounts:profile'),
            data={
                'first_name': 'Attacker',
                'last_name': 'Evil',
                'email': 'evil@test.com',
                'is_superuser': True,
            },
        )
        self.normal_user.refresh_from_db()
        self.assertFalse(self.normal_user.is_superuser)

    def test_profile_form_ignores_injected_is_staff(self):
        """Submitting is_staff via profile form does not escalate privileges."""
        self.login_as(self.normal_user)
        self.client.post(
            reverse('accounts:profile'),
            data={
                'first_name': 'Attacker',
                'last_name': 'Evil',
                'email': 'evil@test.com',
                'is_staff': True,
            },
        )
        self.normal_user.refresh_from_db()
        self.assertFalse(self.normal_user.is_staff)

    def test_admin_views_all_require_authentication(self):
        """All admin-only URLs redirect unauthenticated users to login."""
        admin_urls = [
            reverse('accounts:user_list'),
            reverse('accounts:user_create'),
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk}),
            reverse('accounts:user_delete', kwargs={'pk': self.employee.pk}),
        ]
        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 302,
                f'Expected 302 for anonymous GET {url}, got {response.status_code}',
            )
            self.assertTrue(
                response.url.startswith(self.LOGIN_URL),
                f'Expected redirect to login for {url}, got {response.url}',
            )

    def test_admin_views_deny_normal_users(self):
        """All admin-only URLs deny access to normal (non-admin) users."""
        self.login_as(self.normal_user)
        admin_urls = [
            reverse('accounts:user_list'),
            reverse('accounts:user_create'),
            reverse('accounts:user_update', kwargs={'pk': self.employee.pk}),
            reverse('accounts:user_delete', kwargs={'pk': self.employee.pk}),
        ]
        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 302,
                f'Expected 302 for normal user GET {url}, got {response.status_code}',
            )

    def test_admin_views_deny_employees(self):
        """All admin-only URLs deny access to employees."""
        self.login_as(self.employee)
        admin_urls = [
            reverse('accounts:user_list'),
            reverse('accounts:user_create'),
            reverse('accounts:user_update', kwargs={'pk': self.normal_user.pk}),
            reverse('accounts:user_delete', kwargs={'pk': self.normal_user.pk}),
        ]
        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 302,
                f'Expected 302 for employee GET {url}, got {response.status_code}',
            )
