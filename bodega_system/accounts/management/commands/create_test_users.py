# accounts/management/commands/create_test_users.py

from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Crear usuarios de prueba con diferentes roles'

    def handle(self, *args, **options):
        # Crear superusuario si no existe
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_user(
                username='Leida',
                email='leida@gmail.com',
                password='..LeidaBodega2025..',
                first_name='Administrador',
                last_name='Principal',
                is_admin=True,
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Administrador creado: {admin.username} / admin123')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ Usuario admin ya existe')
            )

        # Crear empleado si no existe
        if not User.objects.filter(username='empleado').exists():
            employee = User.objects.create_user(
                username='Miguel',
                email='empleado@bodega.com',
                password='BodegaEmpleadoMiguel2025',
                first_name='Miguel',
                last_name='Ventas',
                is_employee=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Empleado creado: {employee.username} / empleado123')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ Usuario empleado ya existe')
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ USUARIOS DE PRUEBA DISPONIBLES:'))
        self.stdout.write('')
        self.stdout.write('👑 ADMINISTRADOR:')
        self.stdout.write('   Usuario: admin')
        self.stdout.write('   Contraseña: admin123')
        self.stdout.write('   Permisos: Acceso completo al sistema')
        self.stdout.write('')
        self.stdout.write('👤 EMPLEADO:')
        self.stdout.write('   Usuario: empleado')
        self.stdout.write('   Contraseña: empleado123')
        self.stdout.write('   Permisos: Solo ventas y clientes')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ ¡Listo para probar el sistema de roles!'))
        self.stdout.write('')
        self.stdout.write('🔐 PRUEBAS RECOMENDADAS:')
        self.stdout.write('1. Acceder como admin: debería ver todo')
        self.stdout.write('2. Acceder como empleado: solo ventas y clientes')
        self.stdout.write('3. Como empleado, intentar acceder a /inventory/ - debería dar error 403')
        self.stdout.write('4. Como empleado, intentar acceder a /admin/ - debería dar error 403')