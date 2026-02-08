from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal


from .models import *
from .serializers import *
from .filters import *







class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'name']
    ordering= ['code']

    def get_queryset(self):
        return Currency.objects.filter(is_active=True)
    

    @action(detail=False, methods=['post'])
    def convert(self, request):
        serializer = CurrencyConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data['amount']
        from_currency_code =serializer.validated_data['from_currency']
        to_currency_code =serializer.validated_data['to_currency']


        try:
            from_currency = Currency.objects.get(code=from_currency_code)
            to_currency = Currency.objects.get(code=to_currency_code)
        except Currency.DoesNotExist:
            return Response({'error': "Invalid currency code"}, status=status.HTTP_400_BAD_REQUEST)
        

        converted_amount = ExchangeRate.convert(amount, from_currency, to_currency)

        if converted_amount is None:
            return Response({
                'error': f"No exchange rate found for {from_currency_code} to {to_currency_code}"
            }, status=status.HTTP_404_NOT_FOUND)
        
        rate = ExchangeRate.get_latest_rate(from_currency, to_currency)

        return Response({
            'amount': amount,
            'from_currency': from_currency, 
            'to_currency': to_currency,
            'converted_amount': converted_amount,
            'exchange_rate': rate,
            'date': timezone.now().date()
        
        })


class ExchangeRateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_filed = ['from_currency', 'to_currency', 'date']
    ordering = ['-date']


    def get_queryset(self):
        return ExchangeRate.objects.all()
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        base_currency_code = request.query_params.get('base_currency', request.user.default_currency)

        try: 
            base_currency = Currency.objects.get(code=base_currency_code)
        except Currency.DoesNotExist:
            return Response({
                'error': "Invalid currency code",
            }, status=status.HTTP_400_BAD_REQUEST)
        
        currencies = Currency.objects.filter(is_active=True).exclude(code=base_currency_code)
        rates ={}
        for currency in currencies:
            rate = ExchangeRate.get_latest_rate(base_currency, currency)
            if rate:
                rates[currency.code] = float(rate)
        
        return Response({
            'base_currency': base_currency_code,
            'rates': rates,
            'date': timezone.now().date()
        })









class CardTypeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CardTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        return CardType.objects.filter(is_active=True)




class CardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user's cards.
    
    Endpoints:
    - GET /api/cards/cards/ - List user's cards
    - POST /api/cards/cards/ - Create new card
    - GET /api/cards/cards/{id}/ - Get specific card
    - PUT/PATCH /api/cards/cards/{id}/ - Update card
    - DELETE /api/cards/cards/{id}/ - Delete card
    - POST /api/cards/cards/{id}/set_default/ - Set as default card
    - POST /api/cards/cards/{id}/update_balance/ - Manually adjust balance
    - GET /api/cards/cards/total_balance/ - Get total balance across all cards
    - GET /api/cards/cards/statistics/ - Get card statistics
    """

    permission_classes = [IsAuthenticated]
    filter_backends=[DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CardFilter
    search_fields =['card_name', 'bank_name', 'card_number_last4']
    ordering_fields = ['created_at', 'balance', 'card_name']
    ordering = ['-is_default', '-created_at']


    def get_queryset(self):
        return Card.objects.filter(user=self.request.user).select_related('card_type', 'currency')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CardCreateSerializer
        elif self.action == 'retrieve':
            return CardDetailSerializer
        return CardSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        card = self.get_object()

        if card.transaction.exists():
            return Response({
                'error': 'Cannot delete card with existing transactions',
                'suggestion': 'Set card status to inactive instead'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        active_cards = self.get_queryset().filter(status='active')
        if active_cards.count() == 1 and card.status == 'active':
            return Response({
                'error': 'Cannot delete your only active card'
            }, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)
    

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        card = self.get_object()
        if card.status != 'active':
            return Response({
                'error': "Only active cards can be set as default"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        
        card.is_default = True
        card.save()
        return Response({
            'message': f"{card.card_name} is now your default card",
            'card': CardSerializer(card).data
        })
    
    @action(detail=True, methods=['post'])
    def update_balance(self, request, pk=None):
        card = self.get_object()
        serializer = CardBalanceUpdateSerializer(data =request.data)
        serializer.is_valid(raise_exception=True)
        old_balance = card.balance
        new_balance = serializer.validated_data['new_balance']
        reason = serializer.validated_data.get('reason', 'Manul balance adjustment')

        card.balance = new_balance
        card.save()

        return Response({
            'message': 'Balance updated successfully',
            'old_balance': old_balance,
            'new_balance': new_balance,
            'difference': new_balance - old_balance,
            'reason': reason,
            'card': CardSerializer(card).data
        })
    
    @action(detail=False, methods=['get'])
    def total_balance(self, request):
        user= request.user
        cards = self.get_queryset().filter(status='active')

        try:
            default_currency = Currency.objects.get(code=user.default_currency)
        except Currency.DoesNotExist:
            return Response({
                'error': 'Invalid defeault currency'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        total_balance = Decimal('0')
        cards_breakdown = []
        for c in cards:
            balance_in_default =c.get_balance_in_currency(default_currency)

            if balance_in_default is None:
                balance_in_default = c.balance
            
            total_balance += balance_in_default

            cards_breakdown.append({
                'card_id': c.id,
                'card_name': c.card_name,
                'card_type': c.card_type.name,
                'balance': c.balance,
                'currency': c.currency.code,
                'balance_in_default_currency': balance_in_default

            })

        return Response({
            'total_balance': total_balance,
            'currency': user.default_currency,
            'cards_count': cards.count(),
            'cards_breakdown': cards_breakdown
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        user = request.user
        cards = self.get_queryset()
        try:
        
            default_currency =Currency.objects.get(code=user.default_currency)
        
        except Currency.DoesNotExist:
            return Response({
                'error': 'Invalid default currency'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        total_cards = cards.count()
        active_cards = cards.filter(status='active').count()
        inactive_cards = cards.filter(status='inactive').count()
        blocked_cards = cards.filter(status='blocked').count()

        total_balance = Decimal('0')
        for card in cards.filter(status='active'):
            balance_in_default = card.get_balance_in_currency(default_currency)
            if balance_in_default:
                total_balance += balance_in_default
        
        bytype = cards.values('card_type__name').annotate(count = Sum('id'))

        bycurrency = []
        for crncy in Currency.objects.filter(is_active=True):
            cards_in_currency = cards.filter(currency =crncy, status='active')
            if cards_in_currency.exists():
                total = sum(card.balance for card in cards_in_currency)
                bycurrency.append({
                    'currency': crncy.code,
                    'currency_name': crncy.name,
                    'cards_count': cards_in_currency.count(),
                    'total_balance': total
                })
        
        return Response({
            'total_cards': total_cards,
            'active_cards': active_cards,
            'inactive_cards': inactive_cards,
            'blocked_cards': blocked_cards,
            'total_balance': total_balance,
            'currency': user.default_currency,
            'by_type': list(bytype),
            'by_currency': bycurrency


        })
    
    @action(detail=True, methods=['get'])
    def transaction_summary(self, request, pk=None):
        from apps.transactions.models import Transaction
        from datetime import datetime, timedelta

        card = self.get_object()

        
        start_date=request.query_params.get('start_date')
        end_date=request.query_params.get('end_date')

        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()

        else:
            today = timezone.now().date()
            start = today.replace(day=1)
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end = timezone.now().date()

        transactions= Transaction.objects.filter(card= card, date__gte=start, date__lte=end)
        total_income = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')

        total_expense = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return Response({
            'card': CardSerializer(card).data,
            'period': {
                'start': start,
                'end': end
            }, 
            'total_income': total_income,
            'total_expense': total_expense,
            'net': total_income -total_expense,
            'transaction_count': transactions.count(),
            'currency': card.currency.code
        })
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        card =self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['active', 'inactive', 'blocked']:
            return Response({
                'error': 'Invalid status. Must be: active, inactive, or blocked'
            }, status=status.HTTP_400_BAD_REQUEST)
        if new_status in ['inactive', 'blocked'] and card.is_default:
            card.is_default =False
        
        old_status = card.status
        card.status = new_status
        card.save()

        return Response({
            'message': f"Card status changed from {old_status} to {new_status}",
            'card': CardSerializer(card).data 
        })
    



    