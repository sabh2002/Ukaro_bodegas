# inventory/api_views.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import Product

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_detail_api(request, pk):
    """API para obtener detalles de un producto"""
    product = get_object_or_404(Product, pk=pk)
    
    data = {
        'id': product.id,
        'name': product.name,
        'barcode': product.barcode,
        'category_id': product.category_id,
        'category_name': product.category.name,
        'description': product.description,
        'purchase_price_bs': float(product.purchase_price_bs),
        'selling_price_bs': float(product.selling_price_bs),
        'stock': product.stock,
        'min_stock': product.min_stock,
        'is_active': product.is_active,
        'image': product.image.url if product.image else None,
    }
    
    return JsonResponse(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_search_api(request):
    """API para buscar productos"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'products': []})
    
    # Buscar productos que coincidan con el término de búsqueda
    products = Product.objects.filter(
        name__icontains=query
    ).filter(
        is_active=True
    )[:10]  # Limitar a 10 resultados
    
    # Formatear resultados
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'barcode': product.barcode,
            'category': product.category.name,
            'selling_price_bs': float(product.selling_price_bs),
            'stock': product.stock,
        })
    
    return JsonResponse({'products': results})