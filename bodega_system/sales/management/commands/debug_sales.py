# sales/management/commands/debug_sales.py

from django.core.management.base import BaseCommand
from django.db import connection
from sales.models import Sale, SaleItem
from inventory.models import Product

class Command(BaseCommand):
    help = 'Debug ventas para verificar cantidades decimales'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        self.stdout.write(
            self.style.SUCCESS('DEBUGGING VENTAS CON CANTIDADES DECIMALES')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )

        # Verificar estructura de la tabla
        self.check_table_structure()
        
        # Verificar ventas recientes
        self.check_recent_sales()
        
        # Crear venta de prueba
        self.create_test_sale()

    def check_table_structure(self):
        """Verificar la estructura de la tabla SaleItem"""
        self.stdout.write(
            self.style.WARNING("\n🔍 VERIFICANDO ESTRUCTURA DE LA TABLA sales_saleitem")
        )
        
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(sales_saleitem);")
            columns = cursor.fetchall()
            
            self.stdout.write("\nColumnas de la tabla:")
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                if col_name == 'quantity':
                    style = self.style.SUCCESS if 'DECIMAL' in col_type else self.style.ERROR
                    self.stdout.write(
                        style(f"  • {col_name}: {col_type}")
                    )
                else:
                    self.stdout.write(f"  • {col_name}: {col_type}")

    def check_recent_sales(self):
        """Verificar ventas recientes con cantidades decimales"""
        self.stdout.write(
            self.style.WARNING("\n📊 VERIFICANDO VENTAS RECIENTES")
        )
        
        recent_sales = Sale.objects.all().order_by('-date')[:5]
        
        if not recent_sales:
            self.stdout.write("No hay ventas registradas")
            return
            
        for sale in recent_sales:
            self.stdout.write(f"\n🧾 Venta #{sale.id} - {sale.date.strftime('%d/%m/%Y %H:%M')}")
            items = sale.items.all()
            
            for item in items:
                # Obtener el valor raw de la base de datos
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT quantity FROM sales_saleitem WHERE id = %s", 
                        [item.id]
                    )
                    raw_quantity = cursor.fetchone()[0]
                
                style = self.style.SUCCESS if '.' in str(raw_quantity) else self.style.WARNING
                
                self.stdout.write(
                    style(f"  • {item.product.name if item.product else 'COMBO'}: "
                          f"Cantidad={raw_quantity} (tipo: {type(raw_quantity)}) "
                          f"Precio=Bs {item.price_bs}")
                )

    def create_test_sale(self):
        """Crear una venta de prueba con cantidades decimales"""
        self.stdout.write(
            self.style.WARNING("\n🧪 CREANDO VENTA DE PRUEBA CON CANTIDADES DECIMALES")
        )
        
        # Buscar un producto por peso
        product = Product.objects.filter(
            is_active=True, 
            unit_type__in=['kg', 'gram']
        ).first()
        
        if not product:
            self.stdout.write(
                self.style.ERROR("❌ No hay productos por peso disponibles")
            )
            return
        
        from django.contrib.auth import get_user_model
        from decimal import Decimal
        
        User = get_user_model()
        user = User.objects.first()
        
        if not user:
            self.stdout.write(
                self.style.ERROR("❌ No hay usuarios disponibles")
            )
            return
        
        # Crear venta de prueba
        test_quantities = [
            Decimal('0.25'),
            Decimal('1.75'), 
            Decimal('0.001'),
            Decimal('10.500')
        ]
        
        for qty in test_quantities:
            if product.stock >= qty:
                try:
                    sale = Sale.objects.create(
                        user=user,
                        total_bs=qty * product.selling_price_bs,
                        notes=f"Venta de prueba - {qty} {product.unit_type}"
                    )
                    
                    sale_item = SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=qty,
                        price_bs=product.selling_price_bs
                    )
                    
                    # Verificar que se guardó correctamente
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT quantity FROM sales_saleitem WHERE id = %s", 
                            [sale_item.id]
                        )
                        saved_quantity = cursor.fetchone()[0]
                    
                    if str(saved_quantity) == str(qty):
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Venta #{sale.id}: {qty} {product.unit_type} guardado correctamente como {saved_quantity}")
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f"❌ Venta #{sale.id}: {qty} se guardó como {saved_quantity}")
                        )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Error creando venta con {qty}: {e}")
                    )
                break
        
        self.stdout.write(
            self.style.SUCCESS(f"\n{'='*60}")
        )
        self.stdout.write("Para verificar manualmente:")
        self.stdout.write("python manage.py shell")
        self.stdout.write(">>> from sales.models import SaleItem")
        self.stdout.write(">>> SaleItem.objects.last().quantity")