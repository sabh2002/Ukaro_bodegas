from .models import ExchangeRate

def exchange_rate(request):
    """
    Agrega la tasa de cambio más reciente al contexto de todas las plantillas
    """
    latest_rate = ExchangeRate.get_latest_rate()
    
    return {
        'latest_exchange_rate': latest_rate,
    }