import django_filters
from .models import Card


class CardFilter(django_filters.FilterSet):
    """
    Filter for cards.
    
    Usage examples:
    - ?status=active
    - ?card_type=1
    - ?currency=UZS
    - ?is_default=true
    - ?balance_min=1000000
    """
    
    # Balance filters
    balance_min = django_filters.NumberFilter(field_name='balance', lookup_expr='gte')
    balance_max = django_filters.NumberFilter(field_name='balance', lookup_expr='lte')
    
    # Currency filter by code
    currency_code = django_filters.CharFilter(field_name='currency__code', lookup_expr='iexact')
    
    class Meta:
        model = Card
        fields = {
            'status': ['exact'],
            'card_type': ['exact'],
            'currency': ['exact'],
            'is_default': ['exact'],
            'bank_name': ['icontains'],
        }