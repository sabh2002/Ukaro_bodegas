from django.http import JsonResponse
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Customer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_search_api(request):
    """API para buscar clientes en el formulario de ventas"""
    try:
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 10)), 20)
        
        if not query or len(query) < 2:
            return JsonResponse({'customers': []})
            
        customers = Customer.objects.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        ).order_by('name')[:limit]
        
        results = []
        for customer in customers:
            results.append({
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone or '',
                'email': customer.email or '',
            })
        
        return JsonResponse({
            'customers': results,
            'count': len(results)
        })
        
    except Exception as e:
        return JsonResponse(
            {'error': f'Error en la búsqueda: {str(e)}'}, 
            status=500
        )