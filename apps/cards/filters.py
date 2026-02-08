import django_filters
from .models import Card


class CardFilter(django_filters.FilterSet):
    balance_min = django_filters.NumberFilter(field_name='balance', lookup_expr='gte')
    balance_max = django_filters.NumberFilter(field_name='balance', lookup_expr='lte')



    currency_code = django_filters.CharFilter(field_name='currency__code', lookup_expr='iexact')





    class Meta:
        model  = Card
        fields = {
            'status': ['exact'],
            'card_type': ['exact'],
            'currency': ['exact'],
            'is_default': ['exact'],
            'bank_name': ['icontains'],
        }