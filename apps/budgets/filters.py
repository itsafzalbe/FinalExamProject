import django_filters
from .models import Budget


class BudgetFilter(django_filters.FilterSet):
    """
    Filter for budgets.
    
    Usage examples:
    - ?is_active=true
    - ?period=monthly
    - ?category=1
    - ?amount_min=1000000
    """
    
    # Amount filters
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    
    # Currency filter by code
    currency_code = django_filters.CharFilter(field_name='currency__code', lookup_expr='iexact')
    
    class Meta:
        model = Budget
        fields = {
            'is_active': ['exact'],
            'period': ['exact'],
            'category': ['exact'],
            'currency': ['exact'],
        }