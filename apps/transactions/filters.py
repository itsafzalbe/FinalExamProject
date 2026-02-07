import django_filters
from .models import Transaction


class TransactionFilter(django_filters.FilterSet):
    """
    Filter for transactions.
    
    Usage examples:
    - ?type=expense
    - ?category=1
    - ?card=2
    - ?date_after=2025-01-01&date_before=2025-12-31
    - ?amount_min=100000&amount_max=500000
    - ?search=grocery
    """
    
    # Date filters
    date_after = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_before = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    
    # Amount filters
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    
    # Amount in user currency filters
    amount_in_user_currency_min = django_filters.NumberFilter(
        field_name='amount_in_user_currency', 
        lookup_expr='gte'
    )
    amount_in_user_currency_max = django_filters.NumberFilter(
        field_name='amount_in_user_currency', 
        lookup_expr='lte'
    )
    
    class Meta:
        model = Transaction
        fields = {
            'type': ['exact'],
            'category': ['exact'],
            'card': ['exact'],
            'date': ['exact', 'year', 'month', 'day'],
        }