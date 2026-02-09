import django_filters
from .models import Budget


class BudgetFilter(django_filters.FilterSet):


    amount_min = django_filters.NumberFilter(field_name = 'amount', lookup_expr = 'gte')
    amount_max = django_filters.NumberFilter(field_name = 'amount', lookup_expr = 'lte')
    
    currency_code = django_filters.CharFilter(field_name = 'currency__code', lookup_expr = 'iexact')
    
    class Meta:
        model = Budget
        fields = {
            'period': ['exact'],
            'category': ['exact'],
            'currency': ['exact'],
        }