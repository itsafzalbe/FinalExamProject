from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal

from .models import Currency, ExchangeRate, CardType, Card
from .serializers import (
    CurrencySerializer,
    ExchangeRateSerializer,
    CardTypeSerializer,
    CardSerializer,
    CardCreateSerializer,
    CardDetailSerializer,
    CardBalanceUpdateSerializer,
    CurrencyConversionSerializer,
)
from .filters import CardFilter


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for currencies (read-only).
    
    Endpoints:
    - GET /api/cards/currencies/ - List all active currencies
    - GET /api/cards/currencies/{id}/ - Get specific currency
    - GET /api/cards/currencies/convert/ - Convert between currencies
    """
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'name']
    ordering = ['code']
    
    def get_queryset(self):
        """Return only active currencies"""
        return Currency.objects.filter(is_active=True)
    
    @action(detail=False, methods=['post'])
    def convert(self, request):
        """
        Convert amount between currencies.
        
        POST /api/cards/currencies/convert/
        {
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "UZS"
        }
        
        Response:
        {
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "UZS",
            "converted_amount": 1265000,
            "exchange_rate": 12650.0,
            "date": "2025-02-07"
        }
        """
        serializer = CurrencyConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        from_currency_code = serializer.validated_data['from_currency']
        to_currency_code = serializer.validated_data['to_currency']
        
        try:
            from_currency = Currency.objects.get(code=from_currency_code)
            to_currency = Currency.objects.get(code=to_currency_code)
        except Currency.DoesNotExist:
            return Response(
                {'error': 'Invalid currency code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert
        converted_amount = ExchangeRate.convert(amount, from_currency, to_currency)
        
        if converted_amount is None:
            return Response(
                {'error': f'No exchange rate found for {from_currency_code} to {to_currency_code}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the rate used
        rate = ExchangeRate.get_latest_rate(from_currency, to_currency)
        
        return Response({
            'amount': amount,
            'from_currency': from_currency_code,
            'to_currency': to_currency_code,
            'converted_amount': converted_amount,
            'exchange_rate': rate,
            'date': timezone.now().date()
        })


class ExchangeRateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for exchange rates (read-only for users).
    Admins can add/update rates via admin panel.
    
    Endpoints:
    - GET /api/cards/exchange-rates/ - List all exchange rates
    - GET /api/cards/exchange-rates/{id}/ - Get specific rate
    - GET /api/cards/exchange-rates/latest/ - Get latest rates
    """
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['from_currency', 'to_currency', 'date']
    ordering = ['-date']
    
    def get_queryset(self):
        return ExchangeRate.objects.all()
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Get latest exchange rates.
        Optional query param: base_currency (default: user's default currency)
        
        GET /api/cards/exchange-rates/latest/?base_currency=USD
        
        Response:
        {
            "base_currency": "USD",
            "rates": {
                "UZS": 12650.0,
                "EUR": 0.92,
                "RUB": 91.5
            },
            "date": "2025-02-07"
        }
        """
        base_currency_code = request.query_params.get(
            'base_currency',
            request.user.default_currency
        )
        
        try:
            base_currency = Currency.objects.get(code=base_currency_code)
        except Currency.DoesNotExist:
            return Response(
                {'error': 'Invalid currency code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all active currencies
        currencies = Currency.objects.filter(is_active=True).exclude(
            code=base_currency_code
        )
        
        rates = {}
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
    """
    ViewSet for card types (read-only).
    
    Endpoints:
    - GET /api/cards/card-types/ - List all card types
    - GET /api/cards/card-types/{id}/ - Get specific card type
    """
    serializer_class = CardTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering = ['name']
    
    def get_queryset(self):
        """Return only active card types"""
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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CardFilter
    search_fields = ['card_name', 'bank_name', 'card_number_last4']
    ordering_fields = ['created_at', 'balance', 'card_name']
    ordering = ['-is_default', '-created_at']
    
    def get_queryset(self):
        """Return only user's cards"""
        return Card.objects.filter(user=self.request.user).select_related(
            'card_type', 'currency'
        )
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CardCreateSerializer
        elif self.action == 'retrieve':
            return CardDetailSerializer
        return CardSerializer
    
    def perform_create(self, serializer):
        """Set user when creating card"""
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Delete card with validation"""
        card = self.get_object()
        
        # Check if card has transactions
        if card.transactions.exists():
            return Response(
                {
                    'error': 'Cannot delete card with existing transactions',
                    'suggestion': 'Set card status to inactive instead'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if it's the only active card
        active_cards = self.get_queryset().filter(status='active')
        if active_cards.count() == 1 and card.status == 'active':
            return Response(
                {'error': 'Cannot delete your only active card'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        Set card as default.
        
        POST /api/cards/cards/{id}/set_default/
        """
        card = self.get_object()
        
        if card.status != 'active':
            return Response(
                {'error': 'Only active cards can be set as default'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set as default (model's save method handles removing default from others)
        card.is_default = True
        card.save()
        
        return Response({
            'message': f'{card.card_name} is now your default card',
            'card': CardSerializer(card).data
        })
    
    @action(detail=True, methods=['post'])
    def update_balance(self, request, pk=None):
        """
        Manually adjust card balance.
        Used for corrections or initial setup.
        
        POST /api/cards/cards/{id}/update_balance/
        {
            "new_balance": 5000000,
            "reason": "Correction - added cash deposit"
        }
        """
        card = self.get_object()
        serializer = CardBalanceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        old_balance = card.balance
        new_balance = serializer.validated_data['new_balance']
        reason = serializer.validated_data.get('reason', 'Manual balance adjustment')
        
        card.balance = new_balance
        card.save()
        
        # Optionally create a transaction to track this adjustment
        # (You can add this if you want audit trail)
        
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
        """
        Get total balance across all active cards in user's default currency.
        
        GET /api/cards/cards/total_balance/
        
        Response:
        {
            "total_balance": 25000000,
            "currency": "UZS",
            "cards_breakdown": [
                {
                    "card_name": "My Humo",
                    "balance": 5000000,
                    "currency": "UZS",
                    "balance_in_default_currency": 5000000
                },
                {
                    "card_name": "Visa Savings",
                    "balance": 500,
                    "currency": "USD",
                    "balance_in_default_currency": 6325000
                }
            ]
        }
        """
        user = request.user
        cards = self.get_queryset().filter(status='active')
        
        # Get user's default currency
        try:
            default_currency = Currency.objects.get(code=user.default_currency)
        except Currency.DoesNotExist:
            return Response(
                {'error': 'Invalid default currency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        total_balance = Decimal('0')
        cards_breakdown = []
        
        for card in cards:
            balance_in_default = card.get_balance_in_currency(default_currency)
            
            if balance_in_default is None:
                # No exchange rate found, use original amount
                balance_in_default = card.balance
            
            total_balance += balance_in_default
            
            cards_breakdown.append({
                'card_id': card.id,
                'card_name': card.card_name,
                'card_type': card.card_type.name,
                'balance': card.balance,
                'currency': card.currency.code,
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
        """
        Get card statistics.
        
        GET /api/cards/cards/statistics/
        
        Response:
        {
            "total_cards": 3,
            "active_cards": 2,
            "total_balance": 25000000,
            "currency": "UZS",
            "by_type": [...],
            "by_currency": [...]
        }
        """
        user = request.user
        cards = self.get_queryset()
        
        # Get user's default currency
        try:
            default_currency = Currency.objects.get(code=user.default_currency)
        except Currency.DoesNotExist:
            return Response(
                {'error': 'Invalid default currency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Count by status
        total_cards = cards.count()
        active_cards = cards.filter(status='active').count()
        inactive_cards = cards.filter(status='inactive').count()
        blocked_cards = cards.filter(status='blocked').count()
        
        # Calculate total balance
        total_balance = Decimal('0')
        for card in cards.filter(status='active'):
            balance_in_default = card.get_balance_in_currency(default_currency)
            if balance_in_default:
                total_balance += balance_in_default
        
        # Group by card type
        by_type = cards.values('card_type__name').annotate(
            count=Sum('id')
        )
        
        # Group by currency
        by_currency = []
        for currency in Currency.objects.filter(is_active=True):
            cards_in_currency = cards.filter(currency=currency, status='active')
            if cards_in_currency.exists():
                total = sum(card.balance for card in cards_in_currency)
                by_currency.append({
                    'currency': currency.code,
                    'currency_name': currency.name,
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
            'by_type': list(by_type),
            'by_currency': by_currency
        })
    
    @action(detail=True, methods=['get'])
    def transaction_summary(self, request, pk=None):
        """
        Get transaction summary for a specific card.
        
        GET /api/cards/cards/{id}/transaction_summary/
        Query params: start_date, end_date
        
        Response:
        {
            "card": {...},
            "period": {
                "start": "2025-01-01",
                "end": "2025-02-07"
            },
            "total_income": 8000000,
            "total_expense": 2500000,
            "net": 5500000,
            "transaction_count": 45
        }
        """
        from transactions.models import Transaction
        from datetime import datetime, timedelta
        
        card = self.get_object()
        
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            # Default to current month
            today = timezone.now().date()
            start = today.replace(day=1)
        
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end = timezone.now().date()
        
        # Get transactions
        transactions = Transaction.objects.filter(
            card=card,
            date__gte=start,
            date__lte=end
        )
        
        total_income = transactions.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        total_expense = transactions.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        return Response({
            'card': CardSerializer(card).data,
            'period': {
                'start': start,
                'end': end
            },
            'total_income': total_income,
            'total_expense': total_expense,
            'net': total_income - total_expense,
            'transaction_count': transactions.count(),
            'currency': card.currency.code
        })
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """
        Change card status (active/inactive/blocked).
        
        POST /api/cards/cards/{id}/change_status/
        {
            "status": "inactive"
        }
        """
        card = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in ['active', 'inactive', 'blocked']:
            return Response(
                {'error': 'Invalid status. Must be: active, inactive, or blocked'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If setting to inactive/blocked, remove default status
        if new_status in ['inactive', 'blocked'] and card.is_default:
            card.is_default = False
        
        old_status = card.status
        card.status = new_status
        card.save()
        
        return Response({
            'message': f'Card status changed from {old_status} to {new_status}',
            'card': CardSerializer(card).data
        })