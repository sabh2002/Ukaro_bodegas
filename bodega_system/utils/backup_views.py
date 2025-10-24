# utils/backup_views.py

import os
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core import serializers
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import datetime

from utils.decorators import admin_required
from inventory.models import Category, Product, InventoryAdjustment, ProductCombo, ComboItem
from sales.models import Sale, SaleItem
from customers.models import Customer, CustomerCredit, CreditPayment
from suppliers.models import Supplier, SupplierOrder, SupplierOrderItem
from accounts.models import User

# Lista de modelos a respaldar en orden (respetando dependencias)
BACKUP_MODELS = [
    ('accounts', User),
    ('inventory', Category),
    ('customers', Customer),
    ('suppliers', Supplier),
    ('inventory', Product),
    ('inventory', ProductCombo),
    ('inventory', ComboItem),
    ('suppliers', SupplierOrder),
    ('suppliers', SupplierOrderItem),
    ('inventory', InventoryAdjustment),
    ('sales', Sale),
    ('sales', SaleItem),
    ('customers', CustomerCredit),
    ('customers', CreditPayment),
]

@admin_required
def backup_index(request):
    """Vista principal del módulo de respaldos"""
    # Crear directorio de respaldos si no existe
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Listar archivos de respaldo existentes
    backups = []
    
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                try:
                    file_stats = os.stat(filepath)
                    backups.append({
                        'filename': filename,
                        'size': file_stats.st_size,
                        'size_mb': round(file_stats.st_size / (1024 * 1024), 2),
                        'date': datetime.fromtimestamp(file_stats.st_mtime),
                    })
                except Exception:
                    continue
    
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    return render(request, 'utils/backup_index.html', {
        'backups': backups,
    })

@admin_required
def backup_create(request):
    """Crear un respaldo completo de la base de datos"""
    try:
        # Crear directorio de respaldos si no existe
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nombre del archivo con timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.json'
        filepath = os.path.join(backup_dir, filename)
        
        # Recopilar todos los datos
        backup_data = {
            'version': '1.0',
            'created_at': timezone.now().isoformat(),
            'created_by': request.user.username,
            'data': []
        }
        
        for app_label, model in BACKUP_MODELS:
            try:
                objects = model.objects.all()
                count = objects.count()
                
                if count > 0:
                    serialized = serializers.serialize(
                        'json', 
                        objects,
                        use_natural_foreign_keys=False,
                        use_natural_primary_keys=False
                    )
                    data = json.loads(serialized)
                    
                    # Agregar metadatos
                    for obj in data:
                        obj['_meta'] = {
                            'app_label': app_label,
                            'model_name': model.__name__
                        }
                    
                    backup_data['data'].extend(data)
                    
            except Exception as e:
                messages.warning(request, f'Error al respaldar {model.__name__}: {str(e)}')
                continue
        
        # Guardar archivo
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        messages.success(
            request, 
            f'✅ Respaldo creado exitosamente: {filename} ({len(backup_data["data"])} objetos)'
        )
        return redirect('utils:backup_index')
        
    except Exception as e:
        messages.error(request, f'❌ Error al crear respaldo: {str(e)}')
        return redirect('utils:backup_index')

@admin_required
def backup_download(request, filename):
    """Descargar un archivo de respaldo"""
    try:
        # Validar nombre de archivo (seguridad)
        if not filename.endswith('.json') or '/' in filename or '\\' in filename:
            messages.error(request, 'Nombre de archivo inválido')
            return redirect('utils:backup_index')
        
        filepath = os.path.join(settings.BASE_DIR, 'backups', filename)
        
        if not os.path.exists(filepath):
            messages.error(request, 'El archivo de respaldo no existe')
            return redirect('utils:backup_index')
        
        with open(filepath, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except Exception as e:
        messages.error(request, f'Error al descargar respaldo: {str(e)}')
        return redirect('utils:backup_index')

@admin_required
def backup_delete(request, filename):
    """Eliminar un archivo de respaldo"""
    if request.method != 'POST':
        return redirect('utils:backup_index')
    
    try:
        # Validar nombre de archivo (seguridad)
        if not filename.endswith('.json') or '/' in filename or '\\' in filename:
            messages.error(request, 'Nombre de archivo inválido')
            return redirect('utils:backup_index')
        
        filepath = os.path.join(settings.BASE_DIR, 'backups', filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            messages.success(request, f'✅ Respaldo "{filename}" eliminado exitosamente')
        else:
            messages.error(request, 'El archivo de respaldo no existe')
            
    except Exception as e:
        messages.error(request, f'❌ Error al eliminar respaldo: {str(e)}')
    
    return redirect('utils:backup_index')

@admin_required
def backup_restore(request):
    """Restaurar base de datos desde un archivo JSON"""
    if request.method != 'POST':
        return redirect('utils:backup_index')
    
    uploaded_file = request.FILES.get('backup_file')
    
    if not uploaded_file:
        messages.error(request, 'Debe seleccionar un archivo de respaldo')
        return redirect('utils:backup_index')
    
    if not uploaded_file.name.endswith('.json'):
        messages.error(request, 'El archivo debe ser formato JSON')
        return redirect('utils:backup_index')
    
    try:
        # Leer el archivo
        content = uploaded_file.read().decode('utf-8')
        backup_data = json.loads(content)
        
        # Validar estructura básica
        if isinstance(backup_data, dict) and 'data' in backup_data:
            # Formato nuevo con metadata
            objects_data = backup_data['data']
        elif isinstance(backup_data, list):
            # Formato antiguo (lista directa)
            objects_data = backup_data
        else:
            messages.error(request, 'Formato de respaldo inválido')
            return redirect('utils:backup_index')
        
        # Iniciar transacción
        with transaction.atomic():
            # ORDEN CRÍTICO: Eliminar en orden correcto para respetar dependencias
            # Primero eliminar los modelos que dependen de otros
            
            # 1. Eliminar pagos de crédito (dependen de CustomerCredit)
            CreditPayment.objects.all().delete()
            
            # 2. Eliminar créditos de clientes (dependen de Sale)
            CustomerCredit.objects.all().delete()
            
            # 3. Eliminar items de venta (dependen de Sale y Product)
            SaleItem.objects.all().delete()
            
            # 4. Eliminar ventas (dependen de Customer y User)
            Sale.objects.all().delete()
            
            # 5. Eliminar items de órdenes de proveedores
            SupplierOrderItem.objects.all().delete()
            
            # 6. Eliminar órdenes de proveedores
            SupplierOrder.objects.all().delete()
            
            # 7. Eliminar ajustes de inventario (dependen de Product)
            InventoryAdjustment.objects.all().delete()
            
            # 8. Eliminar items de combos (dependen de ProductCombo y Product)
            ComboItem.objects.all().delete()
            
            # 9. Eliminar combos
            ProductCombo.objects.all().delete()
            
            # 10. Eliminar productos (dependen de Category)
            Product.objects.all().delete()
            
            # 11. Eliminar proveedores
            Supplier.objects.all().delete()
            
            # 12. Eliminar clientes
            Customer.objects.all().delete()
            
            # 13. Eliminar categorías
            Category.objects.all().delete()
            
            # 14. Eliminar usuarios (excepto superusuarios)
            User.objects.filter(is_superuser=False).delete()
            
            # Restaurar datos
            restored_count = 0
            errors = []
            
            # Agrupar por modelo
            models_data = {}
            for obj in objects_data:
                meta = obj.get('_meta', {})
                app_label = meta.get('app_label', '')
                model_name = meta.get('model_name', '')
                model_key = f"{app_label}.{model_name}"
                
                if model_key not in models_data:
                    models_data[model_key] = []
                
                # Remover metadatos antes de deserializar
                obj.pop('_meta', None)
                models_data[model_key].append(obj)
            
            # Restaurar en orden correcto
            for app_label, model in BACKUP_MODELS:
                model_key = f"{app_label}.{model.__name__}"
                
                if model_key in models_data:
                    try:
                        # Serializar de vuelta a JSON string
                        data_json = json.dumps(models_data[model_key])
                        
                        # Deserializar y guardar
                        for obj in serializers.deserialize('json', data_json):
                            obj.save()
                            restored_count += 1
                    except Exception as e:
                        errors.append(f'{model.__name__}: {str(e)}')
                        continue
        
        if errors:
            messages.warning(
                request, 
                f'⚠️ Respaldo restaurado con errores. {restored_count} objetos restaurados. Errores: {", ".join(errors[:3])}'
            )
        else:
            messages.success(
                request, 
                f'✅ Respaldo restaurado exitosamente. {restored_count} objetos restaurados.'
            )
        
    except json.JSONDecodeError:
        messages.error(request, '❌ Error al leer el archivo JSON. Formato inválido.')
    except Exception as e:
        messages.error(request, f'❌ Error al restaurar respaldo: {str(e)}')
    
    return redirect('utils:backup_index')